"""Enums for filter criteria and placement rules."""

from __future__ import annotations

from enum import Enum

from src.models.container import Container


class ContainerFilterableAttribute(Enum):
    """The container fields a ``FilterCriterion`` may key on. Each value is the matching
    attribute name on :class:`~src.models.container.Container`."""

    SIZE = "size"
    TYPE = "type"
    STATUS = "status"
    WEIGHT = "weight"
    INBOUND_MODE = "inbound_mode"
    OUTBOUND_MODE = "outbound_mode"
    DIRECTION = "direction"
    SERVICE = "service"
    INPUT_VESSEL = "input_vessel"
    OUTPUT_VESSEL = "output_vessel"

    def value_for(self, container: Container) -> str:
        """The container's value for this attribute as a comparable string
        (empty string when the field is ``None``)."""
        raw = getattr(container, self.value)
        if raw is None:
            return ""
        if self is ContainerFilterableAttribute.SIZE:
            return str(raw)  # int -> "20" / "40"
        if self is ContainerFilterableAttribute.WEIGHT:
            return raw.name.lower()  # IntEnum -> "light" / "medium" / "heavy"
        if self in (
            ContainerFilterableAttribute.INPUT_VESSEL,
            ContainerFilterableAttribute.OUTPUT_VESSEL,
        ):
            return raw.name  # TransportVessel -> its name
        return raw.value  # string-valued enums (type/status/mode/direction/service)


class Axis(Enum):
    X = "x"
    Y = "y"
    Z = "z"


class StackStart(Enum):
    """Corner of the X/Y plane to start filling from (Z always fills ground-up)."""

    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"


class RuleOption(Enum):
    WEIGHT_RELEVANT = "weight_relevant"  # place heavier containers on lower tiers
