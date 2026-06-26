"""Enums for filter criteria and placement rules."""

from __future__ import annotations

from enum import Enum

from src.models.container import Container


class ContainerFilterableAttribute(Enum):
    """The container fields a ``FilterCriterion`` may key on.

    Each value is the matching attribute name on :class:`~src.models.container.Container`.
    ``input_*`` / ``output_*`` fields describe the inbound / outbound transport.
    """

    SIZE = "size"
    TYPE = "type"
    STATUS = "status"
    WEIGHT = "weight"
    INBOUND_MODE = "inbound_mode"
    OUTBOUND_MODE = "outbound_mode"
    DIRECTION = "direction"
    SERVICE = "service"
    INPUT_NAME = "input_name"
    INPUT_CARRIER = "input_carrier"
    INPUT_LINER = "input_liner"
    OUTPUT_NAME = "output_name"
    OUTPUT_CARRIER = "output_carrier"
    OUTPUT_LINER = "output_liner"

    def value_for(self, container: Container) -> str:
        """The container's value for this attribute as a comparable string
        (empty string when the field is ``None``)."""
        values = self.values_for(container)
        if not values:
            return ""
        return next(iter(values))

    def values_for(self, container: Container) -> frozenset[str]:
        """Normalized comparable values for this attribute (lowercase strings)."""
        raw = getattr(container, self.value)
        if self is ContainerFilterableAttribute.TYPE:
            return frozenset(t.value for t in raw)
        if self is ContainerFilterableAttribute.SERVICE:
            return frozenset(s.value for s in raw)
        if raw is None:
            return frozenset()
        if self is ContainerFilterableAttribute.SIZE:
            return frozenset({str(raw)})
        if self is ContainerFilterableAttribute.WEIGHT:
            return frozenset({raw.name.lower()})
        if isinstance(raw, str):
            return frozenset({raw.strip().lower()})
        return frozenset({raw.value})


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
