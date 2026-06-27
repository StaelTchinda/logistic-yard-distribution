"""Load an explicit container distribution (a placement) from a CSV file.

A distribution file is per-container and block-local::

    container_id,block,column,row,layer
    NGWV5268385,Block 1,0,0,0
    ADHV1142373,Block 1,0,0,1

``column``/``row``/``layer`` are 0-based local indices into the named block; this maps 1:1 to the
engine's ``Slot`` (note it differs from the strategy YAML's 1-based ``z`` tier). A container in the
dataset but absent from the file is treated as unplaced. Validation never raises: problems are
collected in ``DistributionLoadResult.issues`` and the offending row is skipped.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from src.models.container import Container
from src.models.distribution import Distribution, Placement
from src.models.yard import Slot, Yard


@dataclass
class DistributionLoadResult:
    """A loaded ``Distribution`` plus any non-fatal parse ``issues``."""

    distribution: Distribution
    issues: list[str] = field(default_factory=list)


def load_distribution(
    path: str | Path, yard: Yard, containers: list[Container]
) -> DistributionLoadResult:
    """Parse a per-container distribution CSV into a ``Distribution`` against ``yard``."""
    blocks = {block.name: block for block in yard.blocks}
    by_id = {container.id: container for container in containers}

    placement: Placement = []
    issues: list[str] = []
    occupied: set[Slot] = set()
    placed_ids: set[str] = set()

    with open(path, newline="") as handle:
        for lineno, row in enumerate(csv.DictReader(handle), start=2):
            cid = (row.get("container_id") or "").strip()
            bname = (row.get("block") or "").strip()
            container = by_id.get(cid)
            block = blocks.get(bname)
            if container is None:
                issues.append(f"line {lineno}: unknown container id {cid!r}")
                continue
            if block is None:
                issues.append(f"line {lineno}: unknown block {bname!r}")
                continue
            try:
                col, r, layer = int(row["column"]), int(row["row"]), int(row["layer"])
            except (KeyError, TypeError, ValueError):
                issues.append(f"line {lineno}: bad/missing column/row/layer for {cid!r}")
                continue
            if not (
                0 <= col < block.columns_count
                and 0 <= r < block.rows_count
                and 0 <= layer < block.layers_count
            ):
                issues.append(
                    f"line {lineno}: cell ({col},{r},{layer}) out of range for {bname!r}"
                )
                continue
            if cid in placed_ids:
                issues.append(f"line {lineno}: container {cid!r} placed more than once (skipped)")
                continue
            slot = Slot(block, col, r, layer)
            if slot in occupied:
                issues.append(f"line {lineno}: slot {slot} already occupied (skipped)")
                continue
            occupied.add(slot)
            placed_ids.add(cid)
            placement.append((container, slot))

    # Physical sanity: a placed cell above ground needs the cell directly below it occupied.
    for _, slot in placement:
        if slot.layer > 0 and Slot(slot.block, slot.column, slot.row, slot.layer - 1) not in occupied:
            issues.append(f"unsupported (floating) cell at {slot}")

    unplaced = [container for container in containers if container.id not in placed_ids]
    return DistributionLoadResult(Distribution(yard, placement, unplaced), issues)
