"""Pure scoring metrics over a placement = list of (container, slot).

Retrieval order (used by ``rehandles_count``) is the order containers appear in the
evaluated dataset: earlier in the list = retrieved earlier = should end up on top.
"""

from __future__ import annotations

from src.models.container import Container
from src.models.scoring.access import AccessPoints
from src.models.scoring.result import EvaluationResultScore
from src.models.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights
from src.models.yard import Slot, YardBlock

Placement = list[tuple[Container, Slot]]


def _stacks(placement: Placement) -> dict[tuple[int, int, int], list[Container]]:
    """Group a placement into vertical stacks, each ordered bottom -> top."""
    layered: dict[tuple[int, int, int], list[tuple[int, Container]]] = {}
    for container, slot in placement:
        layered.setdefault(slot.stack_key, []).append((slot.layer, container))
    stacks: dict[tuple[int, int, int], list[Container]] = {}
    for key, items in layered.items():
        items.sort(key=lambda lc: lc[0])
        stacks[key] = [container for _, container in items]
    return stacks


def rehandles_count(placement: Placement, order: list[Container] | None = None) -> int:
    """Blocking pairs: an earlier-retrieved container buried under a later-retrieved one.

    ``order`` gives the retrieval sequence (index 0 retrieved first). Without it, all
    containers are treated as equal priority and the count is 0.
    """
    rank = {id(c): i for i, c in enumerate(order)} if order else {}
    total = 0
    for containers in _stacks(placement).values():
        n = len(containers)
        for i in range(n):
            for j in range(i + 1, n):
                if rank.get(id(containers[i]), 0) < rank.get(id(containers[j]), 0):
                    total += 1
    return total


# Magnitude calibration against the datensonar reference (best-fit slope ~2.49).
# Display/magnitude only: the datensonar-style ranking is scale-invariant.
_DISTANCE_SCALE = 2.5


def transport_distance(placement: Placement, access: AccessPoints) -> float:
    """Sum of Manhattan distances from each slot to its mode's access point."""
    total = 0.0
    for container, slot in placement:
        total += slot.global_coord.manhattan(access.for_mode(container.outbound_mode))
    return total * _DISTANCE_SCALE


def manual_sort_effort(placement: Placement) -> int:
    """Count outbound-mode changes scanning each stack bottom -> top."""
    total = 0
    for containers in _stacks(placement).values():
        modes = [c.outbound_mode.value for c in containers]
        total += sum(1 for a, b in zip(modes, modes[1:]) if a != b)
    return total


def balanced_distribution(placement: Placement, blocks: list[YardBlock]) -> float:
    """Population std-dev of per-block fill ratios; 0.0 == perfectly balanced."""
    if len(blocks) < 2:
        return 0.0
    counts: dict[int, int] = {}
    for _, slot in placement:
        counts[id(slot.block)] = counts.get(id(slot.block), 0) + 1
    ratios = [
        counts.get(id(b), 0) / cap
        for b in blocks
        if (cap := b.get_stock_capacity()) > 0
    ]
    mean = sum(ratios) / len(ratios)
    return (sum((r - mean) ** 2 for r in ratios) / len(ratios)) ** 0.5


# Scale factor calibrated against the datensonar reference scorings: best-fit
# yard_distribution ~= 0.77 * std-dev of per-block container counts.
_YARD_DISTRIBUTION_SCALE = 0.77


def yard_distribution(placement: Placement, blocks: list[YardBlock]) -> float:
    """Datensonar-style yard distribution: spread of containers across blocks."""
    if len(blocks) < 2:
        return 0.0
    counts: dict[int, int] = {}
    for _, slot in placement:
        counts[id(slot.block)] = counts.get(id(slot.block), 0) + 1
    values = [float(counts.get(id(b), 0)) for b in blocks]
    mean = sum(values) / len(values)
    std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    return std * _YARD_DISTRIBUTION_SCALE


def score_placement(
    placement: Placement,
    access: AccessPoints,
    unplaced_count: int = 0,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
    order: list[Container] | None = None,
    blocks: list[YardBlock] | None = None,
) -> EvaluationResultScore:
    return EvaluationResultScore(
        rehandles_count=rehandles_count(placement, order),
        transport_distance=transport_distance(placement, access),
        manual_sort_effort=manual_sort_effort(placement),
        unplaced_count=unplaced_count,
        balanced_distribution=balanced_distribution(placement, blocks or []),
        yard_distribution=yard_distribution(placement, blocks or []),
        weights=weights,
    )
