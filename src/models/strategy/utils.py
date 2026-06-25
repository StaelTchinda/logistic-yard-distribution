"""Helper value objects for placement rules: Region, Skip, Stacking."""

from __future__ import annotations

from dataclasses import dataclass

from src.models.strategy.enum import Axis, StackStart


@dataclass(frozen=True)
class Region:
    """Inclusive global-coordinate ranges; ``None`` bound = clip to the yard's extent."""

    x: tuple[int | None, int | None] = (None, None)
    y: tuple[int | None, int | None] = (None, None)
    z: tuple[int | None, int | None] = (None, None)


@dataclass(frozen=True)
class Skip:
    x: int = 0  # empty columns to leave between filled ones (0 = fill all)
    y: int = 0


@dataclass(frozen=True)
class Stacking:
    start: StackStart = StackStart.BOTTOM_LEFT
    order: tuple[Axis, Axis, Axis] = (Axis.X, Axis.Y, Axis.Z)  # outermost first
