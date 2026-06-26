"""Pure scoring metrics over a placement = list of (container, slot).

Retrieval order (used by ``rehandles_count``) is the order containers appear in the
evaluated dataset: earlier in the list = retrieved earlier = should end up on top.
"""

from __future__ import annotations

from src.models.container import Container
from src.models.scoring.access import AccessPoints
from src.models.scoring.result import EvaluationResultScore
from src.models.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights
from src.models.yard import Slot

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


def transport_distance(placement: Placement, access: AccessPoints) -> float:
    """Sum of Manhattan distances from each slot to its mode's access point."""
    total = 0.0
    for container, slot in placement:
        total += slot.global_coord.manhattan(access.for_mode(container.outbound_mode))
    return total


def manual_sort_effort(placement: Placement) -> int:
    """Count load-group changes scanning each stack bottom -> top."""
    total = 0
    for containers in _stacks(placement).values():
        groups = [c.outbound_group() for c in containers]
        total += sum(1 for a, b in zip(groups, groups[1:]) if a != b)
    return total


def score_placement(
    placement: Placement,
    access: AccessPoints,
    unplaced_count: int = 0,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
    order: list[Container] | None = None,
) -> EvaluationResultScore:
    return EvaluationResultScore(
        rehandles_count=rehandles_count(placement, order),
        transport_distance=transport_distance(placement, access),
        manual_sort_effort=manual_sort_effort(placement),
        unplaced_count=unplaced_count,
        weights=weights,
    )
