"""A container distribution: an explicit placement of containers onto yard slots.

Independent of any strategy -- this is the *outcome* (which container sits in which slot), which
the scorer measures directly. A ``Distribution`` is produced by loading a distribution file
(``src.loaders.distribution``), by converting a strategy's ``EvaluationResult``
(``src.services.distribution.distribution_from_result``), or by a generator. The loader wraps it
in a ``DistributionLoadResult`` to also carry any parse ``issues``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models.container import Container
from src.models.yard import Slot, Yard

Placement = list[tuple[Container, Slot]]


@dataclass
class Distribution:
    """Where each container sits on the yard, plus the containers left unplaced."""

    yard: Yard
    placement: Placement = field(default_factory=list)
    unplaced: list[Container] = field(default_factory=list)

    @property
    def placed(self) -> list[Container]:
        return [container for container, _ in self.placement]
