"""Score and result objects produced by the engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models.container import Container
from src.models.geometry import Coordinate3D
from src.models.yard import Yard

from .weights import DEFAULT_WEIGHTS, ScoreWeights


@dataclass
class EvaluationResultScore:
    rehandles_count: int = 0
    transport_distance: float = 0.0
    manual_sort_effort: int = 0
    unplaced_count: int = 0
    weights: ScoreWeights = field(default=DEFAULT_WEIGHTS)  # frozen -> safe shared default

    def get_score(self) -> int:
        w = self.weights
        total = (
            w.rehandle * self.rehandles_count
            + w.distance * self.transport_distance
            + w.sort * self.manual_sort_effort
            + w.unplaced * self.unplaced_count
        )
        return round(total)


@dataclass
class EvaluationResult:
    """``containers`` and ``container_coords`` are parallel arrays:
    ``containers[i]`` is placed at ``container_coords[i]``."""

    yard: Yard
    containers: list[Container]
    container_coords: list[Coordinate3D]
    score: EvaluationResultScore
    unplaced: list[Container] = field(default_factory=list)

    def coord_of(self, container: Container) -> Coordinate3D | None:
        for placed, coord in zip(self.containers, self.container_coords):
            if placed is container:
                return coord
        return None
