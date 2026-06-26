"""A placement-rule condition: an attribute compared against allowed values.

This is the "Conditions" row from the rule editor — an ``(attribute, value[s])`` pair. A
container satisfies it if its value for that attribute is among the allowed values
(single value = equality; several = membership, e.g. ``direction in {export, transshipment}``).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.models.container import Container
from src.models.strategy.enum import ContainerFilterableAttribute


@dataclass(frozen=True)
class FilterCriterion:
    attribute: ContainerFilterableAttribute
    values: tuple[str, ...]

    def matches(self, container: Container) -> bool:
        actuals = self.attribute.values_for(container)
        return bool(actuals & self._normalized)

    @property
    def _normalized(self) -> frozenset[str]:
        return frozenset(value.strip().lower() for value in self.values)

    def __str__(self) -> str:
        return f"{self.attribute.value} in {{{', '.join(self.values)}}}"


# FIXME: Maybe use later
# class FilterDoNotMixCriterion:
#     attribute: ContainerFilterableAttribute
#     value: Any
