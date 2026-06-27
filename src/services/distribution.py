"""Score, convert, and export a container ``Distribution``.

Bridges a ``Distribution`` (an explicit placement, see ``src.models.distribution``) to the existing
scoring so metrics are computed identically to a strategy run, converts a strategy's
``EvaluationResult`` into a ``Distribution`` (for export), and writes one out in the per-container,
block-local CSV format -- enabling a strategy-run -> export -> re-score round-trip.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src.models.container import Container
from src.models.distribution import Distribution
from src.models.scoring.access import AccessPoints
from src.models.scoring.result import EvaluationResult
from src.models.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights
from src.services.scoring.metrics import score_placement


def score_distribution(
    distribution: Distribution,
    containers: list[Container],
    *,
    access: AccessPoints | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EvaluationResult:
    """Score a ``Distribution``, reusing the engine's metrics verbatim.

    ``containers`` is the full dataset (its order is the retrieval order used by rehandles);
    ``distribution.unplaced`` drives the punishment metric.
    """
    yard = distribution.yard
    access = access or AccessPoints.default_for(yard)
    coords = [slot.global_coord for _, slot in distribution.placement]
    score = score_placement(
        distribution.placement,
        access,
        len(distribution.unplaced),
        weights,
        order=containers,
        blocks=yard.blocks,
    )
    return EvaluationResult(yard, distribution.placed, coords, score, distribution.unplaced)


def distribution_from_result(result: EvaluationResult) -> Distribution:
    """Convert a scored ``EvaluationResult`` back into a ``Distribution`` (slots from coords)."""
    index = result.yard.slot_index()
    placement = [
        (container, index[coord])
        for container, coord in zip(result.containers, result.container_coords)
        if coord in index
    ]
    return Distribution(result.yard, placement, list(result.unplaced))


def write_distribution(path: str | Path, distribution: Distribution) -> None:
    """Export a ``Distribution`` as a per-container, block-local CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["container_id", "block", "column", "row", "layer"])
        for container, slot in distribution.placement:
            writer.writerow([container.id, slot.block.name, slot.column, slot.row, slot.layer])


@dataclass
class BlockStat:
    name: str
    count: int
    capacity: int
    fill_ratio: float
    by_outbound_mode: dict[str, int] = field(default_factory=dict)


def aggregate_by_block(result: EvaluationResult) -> list[BlockStat]:
    """Per-block counts / fill ratio / outbound-mode mix for the aggregated view."""
    index = result.yard.slot_index()
    members: dict[str, list[Container]] = {block.name: [] for block in result.yard.blocks}
    for container, coord in zip(result.containers, result.container_coords):
        slot = index.get(coord)
        if slot is not None:
            members[slot.block.name].append(container)
    stats: list[BlockStat] = []
    for block in result.yard.blocks:
        placed = members[block.name]
        capacity = block.get_stock_capacity()
        stats.append(
            BlockStat(
                name=block.name,
                count=len(placed),
                capacity=capacity,
                fill_ratio=(len(placed) / capacity if capacity else 0.0),
                by_outbound_mode=dict(Counter(c.outbound_mode.value for c in placed)),
            )
        )
    return stats
