from src.models import Coordinate2D, Coordinate3D, Yard, YardBlock


def test_block_capacity_and_slot_count():
    block = YardBlock(3, 4, 5, Coordinate2D(0, 0))
    assert block.get_stock_capacity() == 60
    assert len(list(block.slots())) == 60


def test_yard_capacity_and_index_size():
    yard = Yard(
        [YardBlock(2, 2, 2, Coordinate2D(0, 0)), YardBlock(3, 3, 3, Coordinate2D(10, 0))]
    )
    assert yard.get_stock_capacity() == 8 + 27
    assert len(yard.slot_index()) == 35


def test_slot_global_coordinate_offsets_from_corner():
    block = YardBlock(2, 2, 2, Coordinate2D(10, 5), name="B")
    slot = next(s for s in block.slots() if (s.column, s.row, s.layer) == (1, 1, 1))
    assert slot.global_coord == Coordinate3D(11, 6, 1)
