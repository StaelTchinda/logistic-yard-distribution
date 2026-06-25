"""Coordinate value objects for the yard's integer coordinate system."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate2D:
    """A ground-plane position (x, y) — e.g. a block's bottom-left corner."""

    x: int
    y: int

    def manhattan(self, other: "Coordinate2D") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"


@dataclass(frozen=True)
class Coordinate3D:
    """A slot position (x, y, z) — column/row on the ground plus stacking tier."""

    x: int
    y: int
    z: int

    def manhattan(self, other: "Coordinate3D") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)

    def __str__(self) -> str:
        return f"({self.x}, {self.y}, {self.z})"
