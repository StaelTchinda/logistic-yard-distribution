"""Summarize a container dataset into counts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.models.container import Container

_EMPTY = "(none)"


def _count_text(values: list[str]) -> dict[str, int]:
    return dict(Counter(value or _EMPTY for value in values))


@dataclass
class ContainerSummary:
    total: int
    by_type: dict[str, int]
    by_size: dict[int, int]
    by_status: dict[str, int]
    by_weight: dict[str, int]
    by_direction: dict[str, int]
    by_service: dict[str, int]
    by_inbound_mode: dict[str, int]
    by_outbound_mode: dict[str, int]
    by_input_name: dict[str, int]
    by_input_carrier: dict[str, int]
    by_input_liner: dict[str, int]
    by_output_name: dict[str, int]
    by_output_carrier: dict[str, int]
    by_output_liner: dict[str, int]


def summarize_containers(containers: list[Container]) -> ContainerSummary:
    return ContainerSummary(
        total=len(containers),
        by_type=dict(Counter(t.value for c in containers for t in c.type)),
        by_size=dict(Counter(c.size for c in containers)),
        by_status=dict(Counter(c.status.value for c in containers)),
        by_weight=dict(Counter(c.weight.name.lower() for c in containers)),
        by_direction=dict(Counter(c.direction.value for c in containers)),
        by_service=dict(Counter(s.value for c in containers for s in c.service)),
        by_inbound_mode=dict(Counter(c.inbound_mode.value for c in containers)),
        by_outbound_mode=dict(Counter(c.outbound_mode.value for c in containers)),
        by_input_name=_count_text([c.input_name for c in containers]),
        by_input_carrier=_count_text([c.input_carrier for c in containers]),
        by_input_liner=_count_text([c.input_liner for c in containers]),
        by_output_name=_count_text([c.output_name for c in containers]),
        by_output_carrier=_count_text([c.output_carrier for c in containers]),
        by_output_liner=_count_text([c.output_liner for c in containers]),
    )
