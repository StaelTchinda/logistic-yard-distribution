"""Access points a container is carried to when it leaves the yard.

An access can be a single ``PointAccess`` (a gate/rail head at one spot) or an ``EdgeAccess`` -- a
quay that runs along a horizontal edge and is reachable at any x (so the travel distance is just the
vertical gap to that edge). ``AccessPoints.distance(mode, coord)`` is what scoring uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from src.models.enums import TransportMode
from src.models.geometry import Coordinate3D
from src.models.yard import Yard


@dataclass(frozen=True)
class PointAccess:
    """A gate/rail head at a single coordinate."""

    coord: Coordinate3D

    def distance_to(self, coord: Coordinate3D) -> float:
        return coord.manhattan(self.coord)

    @property
    def point(self) -> Coordinate3D:
        return self.coord


@dataclass(frozen=True)
class EdgeAccess:
    """A quay/exit running along the horizontal edge ``y`` (reachable at any x)."""

    y: int

    def distance_to(self, coord: Coordinate3D) -> float:
        return abs(coord.y - self.y) + abs(coord.z)

    @property
    def point(self) -> Coordinate3D:
        return Coordinate3D(0, self.y, 0)


Access = Union[PointAccess, EdgeAccess]


@dataclass
class AccessPoints:
    quay: Access  # seaside: deep sea / feeder
    rail: Access  # rail head
    gate: Access  # landside gate: truck

    def for_access(self, mode: TransportMode) -> Access:
        if mode in (TransportMode.DEEP_SEA, TransportMode.FEEDER):
            return self.quay
        if mode is TransportMode.RAIL:
            return self.rail
        return self.gate  # TRUCK

    def distance(self, mode: TransportMode, coord: Coordinate3D) -> float:
        """Travel distance from ``coord`` to the access for ``mode`` (used by scoring)."""
        return self.for_access(mode).distance_to(coord)

    def for_mode(self, mode: TransportMode) -> Coordinate3D:
        """A representative point for the mode (for heuristics; scoring uses ``distance``)."""
        return self.for_access(mode).point

    @classmethod
    def default_for(cls, yard: Yard) -> "AccessPoints":
        """Derive simple corner reference points from the yard's bounding box."""
        xs: list[int] = []
        ys: list[int] = []
        for block in yard.blocks:
            corner = block.bottom_left_corner
            xs += [corner.x, corner.x + block.columns_count]
            ys += [corner.y, corner.y + block.rows_count]
        min_x, max_x = (min(xs), max(xs)) if xs else (0, 0)
        min_y, max_y = (min(ys), max(ys)) if ys else (0, 0)
        return cls(
            quay=PointAccess(Coordinate3D(min_x, min_y, 0)),
            rail=PointAccess(Coordinate3D(min_x, max_y, 0)),
            gate=PointAccess(Coordinate3D(max_x, max_y, 0)),
        )

    @classmethod
    def datensonar(cls, yard: Yard, *, truck: str = "top_right") -> "AccessPoints":
        """Experimental datensonar geometry: sea = the bottom edge (near blocks 1, 2, 9);
        rail near block 7 (top-left). ``truck`` selects where the truck gate sits:
        ``"top_right"`` (block 12), ``"block7"`` (landside with rail), or ``"bottom"`` (the quay).
        """
        min_y = min(b.bottom_left_corner.y for b in yard.blocks)

        def centroid(name: str) -> Coordinate3D:
            block = next(b for b in yard.blocks if b.name == name)
            return Coordinate3D(
                block.bottom_left_corner.x + block.columns_count // 2,
                block.bottom_left_corner.y + block.rows_count // 2,
                0,
            )

        quay = EdgeAccess(min_y)
        rail = PointAccess(centroid("Block 7"))
        if truck == "block7":
            gate: Access = rail
        elif truck == "bottom":
            gate = quay
        else:  # "top_right"
            gate = PointAccess(centroid("Block 12"))
        return cls(quay=quay, rail=rail, gate=gate)
