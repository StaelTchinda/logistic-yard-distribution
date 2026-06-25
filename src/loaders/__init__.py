"""Load yards, container datasets, and strategies from the ``data/`` directory."""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from src.models.container import Container, TransportVessel
from src.models.enums import (
    ContainerService,
    ContainerStatus,
    ContainerType,
    ContainerWeight,
    Direction,
    TransportMode,
)
from src.models.strategy.enum import (
    Axis,
    ContainerFilterableAttribute,
    RuleOption,
    StackStart,
)
from src.models.strategy.filter_rule import FilterRule
from src.models.strategy.filter_criterion import FilterCriterion
from src.models.strategy.strategy import Strategy
from src.models.strategy.utils import Region, Skip, Stacking
from src.models.geometry import Coordinate2D
from src.models.yard import Yard, YardBlock

__all__ = ["load_yard", "load_containers", "load_strategy"]


# --------------------------------------------------------------------- yards
def _load_yard_yaml(path: Path) -> Yard:
    data = yaml.safe_load(path.read_text()) or {}
    blocks = []
    for raw in data.get("yard", {}).get("blocks", []):
        corner = raw["bottom_left_corner"]
        blocks.append(
            YardBlock(
                columns_count=int(raw["columns"]),
                rows_count=int(raw["rows"]),
                layers_count=int(raw["layers"]),
                bottom_left_corner=Coordinate2D(int(corner["x"]), int(corner["y"])),
                name=str(raw.get("name", "block")),
            )
        )
    return Yard(blocks)


def _load_yard_csv(path: Path) -> Yard:
    blocks = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            blocks.append(
                YardBlock(
                    columns_count=int(row["columns"]),
                    rows_count=int(row["rows"]),
                    layers_count=int(row["layers"]),
                    bottom_left_corner=Coordinate2D(
                        int(row["bottom_left_corner_x"]),
                        int(row["bottom_left_corner_y"]),
                    ),
                    name=str(row.get("name", "block")),
                )
            )
    return Yard(blocks)


def load_yard(path: str | Path) -> Yard:
    """Parse a yard from YAML (``yard.blocks[].{name, columns, rows, layers,
    bottom_left_corner:{x,y}}``) or CSV (columns ``name, columns, rows, layers,
    bottom_left_corner_x, bottom_left_corner_y``)."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return _load_yard_csv(path)
    return _load_yard_yaml(path)


# ---------------------------------------------------------------- containers
def _enum(enum_cls, value, default):
    value = (value or "").strip().lower()
    return enum_cls(value) if value else default


def _weight(value: str | None) -> ContainerWeight:
    value = (value or "").strip()
    if not value:
        return ContainerWeight.MEDIUM
    return ContainerWeight[value.upper()] if value.isalpha() else ContainerWeight(int(value))


def load_containers(path: str | Path) -> list[Container]:
    """Parse a container CSV into Container objects (vessels are shared by name)."""
    vessels: dict[str, TransportVessel] = {}

    def vessel(name: str | None) -> TransportVessel | None:
        name = (name or "").strip()
        if not name:
            return None
        return vessels.setdefault(name, TransportVessel(name))

    containers: list[Container] = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            containers.append(
                Container(
                    id=row["id"].strip(),
                    size=int((row.get("size") or "20").strip()),
                    type=_enum(ContainerType, row.get("type"), ContainerType.DRY),
                    status=_enum(ContainerStatus, row.get("status"), ContainerStatus.FULL),
                    weight=_weight(row.get("weight")),
                    inbound_mode=_enum(
                        TransportMode, row.get("inbound_mode"), TransportMode.DEEP_SEA
                    ),
                    outbound_mode=_enum(
                        TransportMode, row.get("outbound_mode"), TransportMode.TRUCK
                    ),
                    direction=_enum(Direction, row.get("direction"), Direction.IMPORT),
                    service=_enum(ContainerService, row.get("service"), None),
                    input_vessel=vessel(row.get("input_vessel")),
                    output_vessel=vessel(row.get("output_vessel")),
                )
            )
    return containers


# --------------------------------------------------------------- strategies
def _values(value) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return (str(value),)


def _range(value) -> tuple[int | None, int | None]:
    if not value:
        return (None, None)
    lo, hi = value
    return (lo, hi)


def _stacking(raw: dict) -> Stacking:
    start = StackStart(str(raw.get("start", "bottom_left")))
    order_axes = [Axis(str(a)) for a in raw.get("order", ["x", "y", "z"])]
    for axis in (Axis.X, Axis.Y, Axis.Z):  # ensure all three axes are present
        if axis not in order_axes:
            order_axes.append(axis)
    return Stacking(start=start, order=tuple(order_axes[:3]))


def _rule(raw: dict) -> FilterRule:
    conditions = tuple(
        FilterCriterion(
            ContainerFilterableAttribute(cond["attribute"]),
            _values(cond.get("values", cond.get("value"))),
        )
        for cond in raw.get("conditions", [])
    )
    region_raw = raw.get("region") or {}
    skip_raw = raw.get("skip") or {}
    return FilterRule(
        description=str(raw.get("description", "")),
        sort_order=int(raw.get("sort_order", 0)),
        conditions=conditions,
        region=Region(
            x=_range(region_raw.get("x")),
            y=_range(region_raw.get("y")),
            z=_range(region_raw.get("z")),
        ),
        skip=Skip(x=int(skip_raw.get("x", 0)), y=int(skip_raw.get("y", 0))),
        stacking=_stacking(raw.get("stacking") or {}),
        options=frozenset(RuleOption(str(o)) for o in raw.get("options", [])),
    )


def load_strategy(path: str | Path) -> Strategy:
    """Parse a strategy (rule-set) YAML into a Strategy of FilterRules."""
    data = yaml.safe_load(Path(path).read_text()) or {}
    rules = [_rule(raw) for raw in data.get("rules", [])]
    return Strategy(
        name=str(data.get("name", Path(path).stem)),
        description=str(data.get("description", "")),
        rules=rules,
    )
