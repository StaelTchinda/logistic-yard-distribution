"""The placement engine: interpret a strategy's rules to place containers in a yard.

For each container it finds the first matching rule (by ``sort_order``); the rule's matched
containers are then assigned to the rule's region in fill order (start corner + axis order +
skip), bottom-up so stacks stay supported. The result is scored.
"""

from __future__ import annotations

from typing import Iterator

from src.models.container import Container
from src.models.geometry import Coordinate3D
from src.models.scoring.access import AccessPoints
from src.models.scoring.result import EvaluationResult
from src.models.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights
from src.models.strategy.enum import Axis, StackStart
from src.models.strategy.filter_rule import FilterRule
from src.models.strategy.strategy import Strategy
from src.models.yard import Slot, Yard
from src.services.scoring.metrics import score_placement

Bounds = tuple[int, int, int, int, int, int]  # min_x, max_x, min_y, max_y, min_z, max_z


def _bounds(index: dict[Coordinate3D, Slot]) -> Bounds:
    xs = [c.x for c in index]
    ys = [c.y for c in index]
    zs = [c.z for c in index]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _axis_positions(
    rng: tuple[int | None, int | None], lo_default: int, hi_default: int,
    descending: bool, step: int,
) -> list[int]:
    lo, hi = rng
    lo = lo_default if lo is None else max(lo, lo_default)
    hi = hi_default if hi is None else min(hi, hi_default)
    if lo > hi:
        return []
    positions = list(range(lo, hi + 1))
    if descending:
        positions.reverse()
    return positions[::step]  # step = skip + 1 (>= 1)


def slot_sequence(
    rule: FilterRule, index: dict[Coordinate3D, Slot], bounds: Bounds
) -> Iterator[Slot]:
    """Yield the rule region's existing slots in fill order (start corner, axis nesting,
    skip; Z always ascending for support)."""
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    start = rule.stacking.start
    x_desc = start in (StackStart.BOTTOM_RIGHT, StackStart.TOP_RIGHT)
    y_desc = start in (StackStart.TOP_LEFT, StackStart.TOP_RIGHT)

    values = {
        Axis.X: _axis_positions(rule.region.x, min_x, max_x, x_desc, rule.skip.x + 1),
        Axis.Y: _axis_positions(rule.region.y, min_y, max_y, y_desc, rule.skip.y + 1),
        Axis.Z: _axis_positions(rule.region.z, min_z, max_z, False, 1),
    }
    outer, mid, inner = rule.stacking.order
    for ov in values[outer]:
        for mv in values[mid]:
            for iv in values[inner]:
                coord = Coordinate3D(**{outer.value: ov, mid.value: mv, inner.value: iv})
                slot = index.get(coord)
                if slot is not None:
                    yield slot


def _is_supported(slot: Slot, occupancy: dict[Slot, Container]) -> bool:
    if slot.layer == 0:
        return True
    below = Slot(slot.block, slot.column, slot.row, slot.layer - 1)
    return below in occupancy


def _next_free_supported(
    seq: Iterator[Slot], occupancy: dict[Slot, Container]
) -> Slot | None:
    for slot in seq:
        if slot not in occupancy and _is_supported(slot, occupancy):
            return slot
    return None


def _order_members(members: list[Container], rule: FilterRule) -> list[Container]:
    if not rule.weight_relevant:
        return list(members)
    # Heaviest first (so heavy land on lower tiers); stable, so input order breaks ties.
    return sorted(members, key=lambda c: int(c.weight), reverse=True)


def evaluate(
    strategy: Strategy,
    yard: Yard,
    containers: list[Container],
    *,
    access: AccessPoints | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EvaluationResult:
    access = access or AccessPoints.default_for(yard)
    index = yard.slot_index()

    placement: list[tuple[Container, Slot]] = []
    placed: list[Container] = []
    coords: list[Coordinate3D] = []
    unplaced: list[Container] = []

    if not index:
        score = score_placement([], access, len(containers), weights, order=containers)
        return EvaluationResult(yard, [], [], score, list(containers))

    bounds = _bounds(index)
    rules = strategy.sorted_rules()
    occupancy: dict[Slot, Container] = {}

    # Group each container under the first rule it matches.
    groups: dict[int, list[Container]] = {}
    for container in containers:
        matched = next((i for i, r in enumerate(rules) if r.matches(container)), None)
        if matched is None:
            unplaced.append(container)
        else:
            groups.setdefault(matched, []).append(container)

    # Fill each rule's region with its members (rules in sort_order).
    for i, rule in enumerate(rules):
        members = groups.get(i)
        if not members:
            continue
        seq = slot_sequence(rule, index, bounds)
        for container in _order_members(members, rule):
            slot = _next_free_supported(seq, occupancy)
            if slot is None:
                unplaced.append(container)
                continue
            occupancy[slot] = container
            placement.append((container, slot))
            placed.append(container)
            coords.append(slot.global_coord)

    score = score_placement(placement, access, len(unplaced), weights, order=containers)
    return EvaluationResult(yard, placed, coords, score, unplaced)


def evaluate_all(
    yard: Yard,
    containers: list[Container],
    strategies: list[Strategy],
    *,
    access: AccessPoints | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> list[tuple[Strategy, EvaluationResult]]:
    return [
        (s, evaluate(s, yard, containers, access=access, weights=weights))
        for s in strategies
    ]


def find_best(
    yard: Yard,
    containers: list[Container],
    strategies: list[Strategy],
    *,
    access: AccessPoints | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> tuple[Strategy, EvaluationResult]:
    results = evaluate_all(yard, containers, strategies, access=access, weights=weights)
    return min(results, key=lambda sr: sr[1].score.get_score())


def report(results: list[tuple[Strategy, EvaluationResult]]) -> str:
    """Plain-text comparison table (a rich version lives in view/)."""
    header = (
        f"{'Strategy':<22}{'rehandles':>10}{'distance':>10}"
        f"{'sort':>6}{'unplaced':>9}{'TOTAL':>9}"
    )
    lines = [header, "-" * len(header)]
    best = min((r.score.get_score() for _, r in results), default=None)
    for strategy, result in results:
        sc = result.score
        total = sc.get_score()
        mark = "  <- best" if total == best else ""
        lines.append(
            f"{strategy.name:<22}{sc.rehandles_count:>10}"
            f"{sc.transport_distance:>10.0f}{sc.manual_sort_effort:>6}"
            f"{sc.unplaced_count:>9}{total:>9}{mark}"
        )
    return "\n".join(lines)
