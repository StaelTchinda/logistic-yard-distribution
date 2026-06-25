"""A strategy = a named, ordered set of placement rules (a "rule-set")."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models.container import Container
from src.models.strategy.filter_rule import FilterRule


@dataclass
class Strategy:
    name: str
    description: str = ""
    rules: list[FilterRule] = field(default_factory=list)

    def sorted_rules(self) -> list[FilterRule]:
        return sorted(self.rules, key=lambda rule: rule.sort_order)

    def rule_for(self, container: Container) -> FilterRule | None:
        """The first rule (by sort_order) whose conditions match the container."""
        for rule in self.sorted_rules():
            if rule.matches(container):
                return rule
        return None
