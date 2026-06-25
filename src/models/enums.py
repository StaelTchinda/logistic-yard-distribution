"""Categorical attributes of containers and transport, modeled as enums.

``ContainerWeight`` is an :class:`enum.IntEnum` so weights compare directly
(``LIGHT < MEDIUM < HEAVY``).
"""

from __future__ import annotations

from enum import Enum, IntEnum


class ContainerType(Enum):
    DRY = "dry"
    REEFER = "reefer"
    HAZARDOUS = "hazardous"


class ContainerStatus(Enum):
    EMPTY = "empty"
    FULL = "full"


class ContainerWeight(IntEnum):
    """Ordered so heavier > lighter."""

    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3


class ContainerService(Enum):
    WASHING = "washing"
    SEAL = "seal"
    CUSTOMS = "customs"
    STRIP = "strip"
    STUFF = "stuff"


class TransportMode(Enum):
    DEEP_SEA = "deep_sea"
    FEEDER = "feeder"
    RAIL = "rail"
    TRUCK = "truck"


class Direction(Enum):
    IMPORT = "import"
    EXPORT = "export"
    WATERSIDE_TRANSSHIPMENT = "waterside_transshipment"
    LANDSIDE_TRANSSHIPMENT = "landside_transshipment"
