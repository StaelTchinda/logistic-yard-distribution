"""FilterRule — the rule editor's rule.

A rule says: *containers matching these `conditions` go into this `region` of the yard,
filled from `stacking.start` in `stacking.order`, leaving `skip` gaps, with these
`options`.* Rules are ranked by `sort_order` (lowest first).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models.container import Container
from src.models.strategy.enum import RuleOption
from src.models.strategy.filter_criterion import FilterCriterion
from src.models.strategy.utils import Region, Skip, Stacking


@dataclass
class FilterRule:
    description: str = ""
    sort_order: int = 0
    conditions: tuple[FilterCriterion, ...] = ()
    region: Region = field(default_factory=Region)
    skip: Skip = field(default_factory=Skip)
    stacking: Stacking = field(default_factory=Stacking)
    options: frozenset[RuleOption] = frozenset()

    def matches(self, container: Container) -> bool:
        """True if every condition holds (no conditions ⇒ catch-all)."""
        return all(cond.matches(container) for cond in self.conditions)

    @property
    def weight_relevant(self) -> bool:
        return RuleOption.WEIGHT_RELEVANT in self.options
