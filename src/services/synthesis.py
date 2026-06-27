"""Synthesize a strategy from the dataset by inverse design.

Instead of searching strategy-space, compute a *target distribution* -- which
attribute-group goes to which yard region -- then serialize it to a Strategy.

v1 splits containers by ``outbound_mode`` (the attribute that drives transport
distance: each mode has a fixed access point) and greedily assigns whole blocks
to groups, nearest access point first. This minimizes distance and unplaced;
balance and rehandles are secondary (see the chosen objective in
[[datensonar-scoring-alignment]]).

Run a demo (synthesize, then rank it against the existing strategies):

    uv run python -m src.services.synthesis
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.models.container import Container
from src.models.enums import TransportMode
from src.models.geometry import Coordinate3D
from src.models.scoring.access import AccessPoints
from src.models.strategy.enum import ContainerFilterableAttribute
from src.models.strategy.filter_criterion import FilterCriterion
from src.models.strategy.filter_rule import FilterRule
from src.models.strategy.strategy import Strategy
from src.models.strategy.utils import Region
from src.models.yard import Yard, YardBlock


def _centroid(block: YardBlock) -> Coordinate3D:
    corner = block.bottom_left_corner
    return Coordinate3D(
        corner.x + block.columns_count // 2, corner.y + block.rows_count // 2, 0
    )


def _layers(block: YardBlock, max_layers: int | None) -> int:
    return block.layers_count if max_layers is None else min(max_layers, block.layers_count)


def _extent(block: YardBlock, layers: int) -> Region:
    corner = block.bottom_left_corner
    return Region(
        x=(corner.x, corner.x + block.columns_count - 1),
        y=(corner.y, corner.y + block.rows_count - 1),
        z=(0, layers - 1),
    )


@dataclass
class BlockAssignment:
    mode: TransportMode
    block: YardBlock
    cost: float  # Manhattan distance: block centroid -> the mode's access point
    capacity: int


def target_assignment(
    yard: Yard, containers: list[Container], *, max_layers: int | None = None
) -> list[BlockAssignment]:
    """The target distribution: assign whole blocks to outbound-mode groups.

    Greedy min-cost: repeatedly give the cheapest (mode, block) pair to a mode
    that still needs capacity. Any leftover block goes to the most
    over-subscribed mode so yard capacity isn't wasted.
    """
    access = AccessPoints.default_for(yard)
    remaining = dict(Counter(c.outbound_mode for c in containers))

    def cap(block: YardBlock) -> int:
        return block.columns_count * block.rows_count * _layers(block, max_layers)

    candidates = sorted(
        (
            (_centroid(b).manhattan(access.for_mode(m)), m, b)
            for m in remaining
            for b in yard.blocks
        ),
        key=lambda triple: triple[0],
    )
    owned: dict[int, BlockAssignment] = {}
    for cost, mode, block in candidates:
        if id(block) in owned or remaining.get(mode, 0) <= 0:
            continue
        owned[id(block)] = BlockAssignment(mode, block, cost, cap(block))
        remaining[mode] -= cap(block)

    for block in yard.blocks:
        if id(block) in owned or not remaining:
            continue
        mode = max(remaining, key=lambda m: remaining[m])
        cost = _centroid(block).manhattan(access.for_mode(mode))
        owned[id(block)] = BlockAssignment(mode, block, cost, cap(block))
        remaining[mode] -= cap(block)

    return sorted(owned.values(), key=lambda a: (a.mode.value, a.cost))


def assignment_to_strategy(
    assignment: list[BlockAssignment],
    *,
    name: str = "Synthesized",
    max_layers: int | None = None,
) -> Strategy:
    """Serialize a target assignment into a Strategy (one rule per block).

    Rules sharing a mode have identical conditions, so the engine merges them
    into a sort-order chain and spills that mode across its blocks nearest-first.
    """
    rules = [
        FilterRule(
            description=f"{a.mode.value} -> {a.block.name}",
            sort_order=order,
            conditions=(
                FilterCriterion(ContainerFilterableAttribute.OUTBOUND_MODE, (a.mode.value,)),
            ),
            region=_extent(a.block, _layers(a.block, max_layers)),
        )
        for order, a in enumerate(assignment, start=1)
    ]
    return Strategy(
        name=name,
        description="Synthesized from the dataset by inverse design.",
        rules=rules,
    )


def synthesize(
    yard: Yard,
    containers: list[Container],
    *,
    max_layers: int | None = None,
    name: str = "Synthesized",
) -> Strategy:
    """Inverse-design a Strategy: target distribution -> rules."""
    assignment = target_assignment(yard, containers, max_layers=max_layers)
    return assignment_to_strategy(assignment, name=name, max_layers=max_layers)


if __name__ == "__main__":
    from src.loaders import load_containers, load_strategy, load_yard
    from src.loaders.catalog import scan_strategies
    from src.loaders.paths import data_root
    from src.services.filter.engine import evaluate, evaluate_all
    from src.services.scoring.ranking import rank_strategies

    root = data_root()
    yard = load_yard(root / "yards" / "datensonar.csv")
    containers = load_containers(root / "containers" / "master_update.csv")
    existing = [load_strategy(e.path) for e in scan_strategies(root)]

    for label, max_layers in (("single-layer", 1), ("stacked (5)", None)):
        synth = synthesize(yard, containers, max_layers=max_layers, name=f"Synthesized [{label}]")
        score = evaluate(synth, yard, containers).score
        ranked = rank_strategies(evaluate_all(yard, containers, existing + [synth]))
        row = next(r for r in ranked if r.strategy is synth)
        print(f"\n=== {label}: {len(synth.rules)} rules ===")
        print(
            f"  rehandles={score.rehandles_count:,}  distance={score.transport_distance:,.0f}"
            f"  yard={score.yard_distribution:.1f}  unplaced={score.unplaced_count:,}"
        )
        print(f"  rank among {len(ranked)} strategies: #{row.total_rank}")
