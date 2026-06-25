"""Container and transport-vessel domain entities."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import (
    ContainerService,
    ContainerStatus,
    ContainerType,
    ContainerWeight,
    Direction,
    TransportMode,
)


@dataclass
class TransportVessel:
    name: str
    carrier: str = ""
    liner: str = ""
    service: str = ""

    def __str__(self) -> str:
        return self.name


@dataclass(eq=False)
class Container:
    """A single container. ``eq=False`` keeps identity-based equality/hashing so the
    same object can be an occupancy value and be matched by identity later."""

    id: str
    size: int = 20  # TEU length, e.g. 20 or 40 ft
    type: ContainerType = ContainerType.DRY
    status: ContainerStatus = ContainerStatus.FULL
    weight: ContainerWeight = ContainerWeight.MEDIUM
    inbound_mode: TransportMode = TransportMode.DEEP_SEA
    outbound_mode: TransportMode = TransportMode.TRUCK
    direction: Direction = Direction.IMPORT
    service: ContainerService | None = None
    input_vessel: TransportVessel | None = None
    output_vessel: TransportVessel | None = None

    def outbound_group(self) -> str:
        """The load group this container leaves with: its vessel, else its mode."""
        if self.output_vessel is not None:
            return f"vessel:{self.output_vessel.name}"
        return f"mode:{self.outbound_mode.value}"

    def __str__(self) -> str:
        return f"Container({self.id})"
