"""Access points a container is carried to when it leaves the yard."""

from __future__ import annotations

from dataclasses import dataclass

from src.models.enums import TransportMode
from src.models.geometry import Coordinate3D
from src.models.yard import Yard

@dataclass
class AccessPoints:
    quay: Coordinate3D  # seaside: deep sea / feeder
    rail: Coordinate3D  # rail head
    gate: Coordinate3D  # landside gate: truck

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
            quay=Coordinate3D(min_x, min_y, 0),
            rail=Coordinate3D(min_x, max_y, 0),
            gate=Coordinate3D(max_x, max_y, 0),
        )

    def for_mode(self, mode: TransportMode) -> Coordinate3D:
        if mode in (TransportMode.DEEP_SEA, TransportMode.FEEDER):
            return self.quay
        if mode is TransportMode.RAIL:
            return self.rail
        return self.gate  # TRUCK
