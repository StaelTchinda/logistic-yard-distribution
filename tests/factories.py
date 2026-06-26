"""Test helpers for building domain objects with sensible defaults."""

from __future__ import annotations

from src.models.container import Container
from src.models.enums import (
    ContainerService,
    ContainerStatus,
    ContainerType,
    ContainerWeight,
    Direction,
    TransportMode,
)


def make_container(
    *,
    id: str = "C",
    size: int = 20,
    type: ContainerType | list[ContainerType] = ContainerType.DRY,
    status: ContainerStatus = ContainerStatus.FULL,
    weight: ContainerWeight = ContainerWeight.MEDIUM,
    inbound_mode: TransportMode = TransportMode.DEEP_SEA,
    outbound_mode: TransportMode = TransportMode.TRUCK,
    direction: Direction = Direction.IMPORT,
    service: ContainerService | list[ContainerService] | None = None,
    input_name: str = "",
    input_carrier: str = "",
    input_liner: str = "",
    output_name: str = "",
    output_carrier: str = "",
    output_liner: str = "",
) -> Container:
    return Container(
        id=id,
        size=size,
        type=[type] if isinstance(type, ContainerType) else list(type),
        status=status,
        weight=weight,
        inbound_mode=inbound_mode,
        outbound_mode=outbound_mode,
        direction=direction,
        service=(
            []
            if service is None
            else [service]
            if isinstance(service, ContainerService)
            else list(service)
        ),
        input_name=input_name,
        input_carrier=input_carrier,
        input_liner=input_liner,
        output_name=output_name,
        output_carrier=output_carrier,
        output_liner=output_liner,
    )
