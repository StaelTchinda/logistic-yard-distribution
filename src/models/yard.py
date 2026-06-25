"""Physical yard: blocks, slots, and the yard composite.

A block is a 3D grid addressed by ``(column, row, layer)``; a slot's *global* coordinate is
the block's ground ``bottom_left_corner`` (2D) offset by ``column->x, row->y`` with the
stacking tier as ``z``. A vertical stack is a fixed ``(block, column, row)`` across layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from .geometry import Coordinate2D, Coordinate3D


@dataclass(eq=False)
class YardBlock:
    """A rectangular block of storage slots (identity-based so it can key a Slot)."""

    columns_count: int
    rows_count: int
    layers_count: int
    bottom_left_corner: Coordinate2D
    name: str = "block"

    def get_stock_capacity(self) -> int:
        return self.columns_count * self.rows_count * self.layers_count

    def slots(self) -> Iterator["Slot"]:
        for column in range(self.columns_count):
            for row in range(self.rows_count):
                for layer in range(self.layers_count):
                    yield Slot(self, column, row, layer)


@dataclass(frozen=True)
class Slot:
    """One cell of a block. Frozen + hashable so it can key the occupancy map."""

    block: YardBlock
    column: int
    row: int
    layer: int

    @property
    def global_coord(self) -> Coordinate3D:
        corner = self.block.bottom_left_corner
        return Coordinate3D(corner.x + self.column, corner.y + self.row, self.layer)

    @property
    def stack_key(self) -> tuple[int, int, int]:
        """Identifies the vertical stack this slot belongs to (block, column, row)."""
        return (id(self.block), self.column, self.row)

    def __str__(self) -> str:
        return f"{self.block.name}[c{self.column},r{self.row},l{self.layer}]"


@dataclass
class Yard:
    """The whole storage yard: a composition of blocks."""

    blocks: list[YardBlock] = field(default_factory=list)

    def get_stock_capacity(self) -> int:
        return sum(block.get_stock_capacity() for block in self.blocks)

    def slots(self) -> Iterator[Slot]:
        for block in self.blocks:
            yield from block.slots()

    def slot_index(self) -> dict[Coordinate3D, Slot]:
        """Map each slot's global coordinate to its Slot (assumes blocks don't overlap)."""
        index: dict[Coordinate3D, Slot] = {}
        for slot in self.slots():
            index[slot.global_coord] = slot
        return index
