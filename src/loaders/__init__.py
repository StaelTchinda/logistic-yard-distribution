"""Load yards, container datasets, and strategies from the ``data/`` directory."""

from __future__ import annotations

import csv
import warnings
from pathlib import Path

import yaml

from src.models.container import Container
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

from src.loaders.distribution import DistributionLoadResult, load_distribution

__all__ = [
    "load_yard",
    "load_containers",
    "load_strategy",
    "load_distribution",
    "DistributionLoadResult",
]


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
def _cell(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _parse_required_enum(enum_cls, raw: str, field_name: str):
    if not raw:
        return None
    try:
        return enum_cls(raw.lower())
    except ValueError:
        warnings.warn(
            f"Skipping row: invalid {field_name} {raw!r}",
            stacklevel=3,
        )
        return None


def _parse_optional_enum(enum_cls, raw: str, field_name: str):
    if not raw:
        return None
    try:
        return enum_cls(raw.lower())
    except ValueError:
        warnings.warn(
            f"Skipping row: invalid {field_name} {raw!r}",
            stacklevel=3,
        )
        return None


def _parse_weight(raw: str) -> ContainerWeight | None:
    if not raw:
        return None
    try:
        return ContainerWeight[raw.upper()] if raw.isalpha() else ContainerWeight(int(raw))
    except (KeyError, ValueError):
        warnings.warn(f"Skipping row: invalid weight {raw!r}", stacklevel=3)
        return None


def _parse_types(raw: str) -> list[ContainerType] | None:
    if not raw:
        return None
    types: list[ContainerType] = []
    seen: set[ContainerType] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            parsed = ContainerType(token.lower())
        except ValueError:
            warnings.warn(
                f"Skipping row: invalid type {token!r}",
                stacklevel=3,
            )
            return None
        if parsed not in seen:
            seen.add(parsed)
            types.append(parsed)
    if not types:
        return None
    return types


def _parse_services(raw: str) -> list[ContainerService] | None:
    if not raw:
        return []
    services: list[ContainerService] = []
    seen: set[ContainerService] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            parsed = ContainerService(token.lower())
        except ValueError:
            warnings.warn(
                f"Skipping row: invalid service {token!r}",
                stacklevel=3,
            )
            return None
        if parsed not in seen:
            seen.add(parsed)
            services.append(parsed)
    return services


def _parse_size(raw: str) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        warnings.warn(f"Skipping row: invalid size {raw!r}", stacklevel=3)
        return None


def _parse_transport(prefix: str, row: dict[str, str]) -> tuple[str, str, str, str] | None:
    """Parse inbound/outbound transport columns (CSV still uses ``{prefix}_vessel*`` headers)."""
    name = _cell(row, f"{prefix}_vessel")
    carrier = _cell(row, f"{prefix}_vessel_carrier")
    liner = _cell(row, f"{prefix}_vessel_liner")
    line = _cell(row, f"{prefix}_vessel_service")
    if not any((name, carrier, liner, line)):
        return None
    if not name:
        warnings.warn(
            f"Skipping row {_cell(row, 'id')!r}: {prefix}_vessel name required "
            f"when other {prefix}_vessel_* columns are set",
            stacklevel=3,
        )
        return None
    return name, carrier, liner, line


def _parse_container_row(row: dict[str, str]) -> Container | None:
    row_id = _cell(row, "id")
    if not row_id:
        warnings.warn("Skipping row: missing id", stacklevel=3)
        return None

    size = _parse_size(_cell(row, "size"))
    if size is None:
        warnings.warn(f"Skipping row {row_id!r}: missing or invalid size", stacklevel=3)
        return None

    types = _parse_types(_cell(row, "type"))
    if types is None:
        if _cell(row, "type"):
            return None
        warnings.warn(f"Skipping row {row_id!r}: missing type", stacklevel=3)
        return None

    status = _parse_required_enum(ContainerStatus, _cell(row, "status"), "status")
    if status is None:
        if _cell(row, "status"):
            return None
        warnings.warn(f"Skipping row {row_id!r}: missing status", stacklevel=3)
        return None

    weight = _parse_weight(_cell(row, "weight"))
    if weight is None:
        warnings.warn(f"Skipping row {row_id!r}: missing or invalid weight", stacklevel=3)
        return None

    inbound_mode = _parse_required_enum(
        TransportMode, _cell(row, "inbound_mode"), "inbound_mode"
    )
    if inbound_mode is None:
        if _cell(row, "inbound_mode"):
            return None
        warnings.warn(f"Skipping row {row_id!r}: missing inbound_mode", stacklevel=3)
        return None

    outbound_mode = _parse_required_enum(
        TransportMode, _cell(row, "outbound_mode"), "outbound_mode"
    )
    if outbound_mode is None:
        if _cell(row, "outbound_mode"):
            return None
        warnings.warn(f"Skipping row {row_id!r}: missing outbound_mode", stacklevel=3)
        return None

    direction = _parse_required_enum(Direction, _cell(row, "direction"), "direction")
    if direction is None:
        if _cell(row, "direction"):
            return None
        warnings.warn(f"Skipping row {row_id!r}: missing direction", stacklevel=3)
        return None

    services = _parse_services(_cell(row, "service"))
    if services is None:
        return None

    input_transport = _parse_transport("input", row)
    if input_transport is None and any(
        _cell(row, k)
        for k in (
            "input_vessel",
            "input_vessel_carrier",
            "input_vessel_liner",
            "input_vessel_service",
        )
    ):
        return None

    output_transport = _parse_transport("output", row)
    if output_transport is None and any(
        _cell(row, k)
        for k in (
            "output_vessel",
            "output_vessel_carrier",
            "output_vessel_liner",
            "output_vessel_service",
        )
    ):
        return None

    input_name, input_carrier, input_liner, input_line = input_transport or ("", "", "", "")
    output_name, output_carrier, output_liner, output_line = output_transport or (
        "",
        "",
        "",
        "",
    )

    return Container(
        id=row_id,
        size=size,
        type=types,
        status=status,
        weight=weight,
        inbound_mode=inbound_mode,
        outbound_mode=outbound_mode,
        direction=direction,
        service=services,
        input_name=input_name,
        input_carrier=input_carrier,
        input_liner=input_liner,
        output_name=output_name,
        output_carrier=output_carrier,
        output_liner=output_liner,
    )


def load_containers(path: str | Path) -> list[Container]:
    """Parse a container CSV into Container objects."""
    containers: list[Container] = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            container = _parse_container_row(row)
            if container is not None:
                containers.append(container)
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


def _z_range(value) -> tuple[int | None, int | None]:
    """Convert datensonar 1-based layer bounds to engine 0-based layers.

    datensonar's ground tier is ``1``; engine layers start at ``0``. A single-tier
    rule ``z:[1,1]`` means the ground layer only (``(0, 0)``) and is NOT expanded to
    the full stack height -- expanding it forces phantom stacking that inflates
    rehandles and over-places containers vs the reference. ``None`` bounds are
    preserved (clip to yard extent).
    """
    lo, hi = _range(value)
    if lo is None and hi is None:
        return (None, None)
    if lo is not None:
        lo -= 1
    if hi is not None:
        hi -= 1
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
            z=_z_range(region_raw.get("z")),
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
