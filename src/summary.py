"""Summarize a container dataset into counts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.models.container import Container


@dataclass
class ContainerSummary:
    total: int
    by_type: dict[str, int]
    by_size: dict[int, int]
    by_status: dict[str, int]
    by_weight: dict[str, int]
    by_direction: dict[str, int]
    by_service: dict[str, int]
    by_outbound_group: dict[str, int]


def summarize_containers(containers: list[Container]) -> ContainerSummary:
    return ContainerSummary(
        total=len(containers),
        by_type=dict(Counter(c.type.value for c in containers)),
        by_size=dict(Counter(c.size for c in containers)),
        by_status=dict(Counter(c.status.value for c in containers)),
        by_weight=dict(Counter(c.weight.name.lower() for c in containers)),
        by_direction=dict(Counter(c.direction.value for c in containers)),
        by_service=dict(
            Counter(c.service.value if c.service else "none" for c in containers)
        ),
        by_outbound_group=dict(Counter(c.outbound_group() for c in containers)),
    )
