"""Container domain entity."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    ContainerService,
    ContainerStatus,
    ContainerType,
    ContainerWeight,
    Direction,
    TransportMode,
)


@dataclass(eq=False)
class Container:
    """A single container. ``eq=False`` keeps identity-based equality/hashing so the
    same object can be an occupancy value and be matched by identity later."""

    id: str
    size: int  # TEU length, e.g. 20 or 40 ft
    type: list[ContainerType]
    status: ContainerStatus
    weight: ContainerWeight
    inbound_mode: TransportMode
    outbound_mode: TransportMode
    direction: Direction
    service: list[ContainerService]
    # Inbound transport (vessel) attributes
    input_name: str = ""
    input_carrier: str = ""
    input_liner: str = ""
    # Outbound transport (vessel) attributes
    output_name: str = ""
    output_carrier: str = ""
    output_liner: str = ""

    def outbound_group(self) -> str:
        """The load group this container leaves with: its outbound transport, else its mode."""
        if self.output_name:
            return f"transport:{self.output_name}"
        return f"mode:{self.outbound_mode.value}"

    def __str__(self) -> str:
        return f"Container({self.id})"
