"""Import, score, and round-trip an explicit container distribution."""

from __future__ import annotations

from src.loaders.distribution import DistributionLoadResult, load_distribution
from src.models.distribution import Distribution
from src.models.geometry import Coordinate2D
from src.models.strategy import evaluate
from src.models.strategy.filter_rule import FilterRule
from src.models.strategy.strategy import Strategy
from src.models.yard import Slot, Yard, YardBlock
from src.services.distribution import (
    aggregate_by_block,
    distribution_from_result,
    score_distribution,
    write_distribution,
)
from tests.factories import make_container


def _yard() -> Yard:
    return Yard(
        [
            YardBlock(2, 2, 2, Coordinate2D(0, 0), name="Block 1"),
            YardBlock(2, 2, 2, Coordinate2D(10, 0), name="Block 2"),
        ]
    )


def test_round_trip_matches_strategy_run(tmp_path):
    yard = _yard()
    containers = [make_container(id=f"C{i}") for i in range(6)]
    strategy = Strategy("catch-all", "", [FilterRule(description="all", sort_order=1)])
    original = evaluate(strategy, yard, containers)

    path = tmp_path / "dist.csv"
    write_distribution(path, distribution_from_result(original))
    loaded = load_distribution(path, yard, containers)
    rescored = score_distribution(loaded.distribution, containers)

    assert isinstance(loaded, DistributionLoadResult)
    assert isinstance(loaded.distribution, Distribution)
    assert not loaded.issues
    assert len(loaded.distribution.placement) == len(original.containers)
    assert rescored.score.rehandles_count == original.score.rehandles_count
    assert rescored.score.transport_distance == original.score.transport_distance
    assert rescored.score.yard_distribution == original.score.yard_distribution
    assert rescored.score.unplaced_count == original.score.unplaced_count


def test_score_hand_built_distribution():
    yard = _yard()
    a, b = make_container(id="A"), make_container(id="B")
    block = yard.blocks[0]
    dist = Distribution(yard, [(a, Slot(block, 0, 0, 0)), (b, Slot(block, 1, 0, 0))], unplaced=[])
    result = score_distribution(dist, [a, b])
    assert result.score.unplaced_count == 0
    assert len(result.containers) == 2


def test_unknown_id_and_block_recorded(tmp_path):
    yard = _yard()
    containers = [make_container(id="C0"), make_container(id="C1")]
    path = tmp_path / "d.csv"
    path.write_text(
        "container_id,block,column,row,layer\n"
        "C0,Block 1,0,0,0\n"
        "GHOST,Block 1,1,0,0\n"  # unknown container id
        "C1,Block 9,0,0,0\n"  # unknown block
    )
    loaded = load_distribution(path, yard, containers)
    assert any("unknown container" in i for i in loaded.issues)
    assert any("unknown block" in i for i in loaded.issues)
    assert {c.id for c in loaded.distribution.unplaced} == {"C1"}
    assert len(loaded.distribution.placement) == 1


def test_out_of_range_and_duplicate_slot(tmp_path):
    yard = _yard()
    containers = [make_container(id="A"), make_container(id="B"), make_container(id="C")]
    path = tmp_path / "d.csv"
    path.write_text(
        "container_id,block,column,row,layer\n"
        "A,Block 1,0,0,0\n"
        "B,Block 1,0,0,0\n"  # duplicate slot -> skipped
        "C,Block 1,5,0,0\n"  # column out of range -> skipped
    )
    loaded = load_distribution(path, yard, containers)
    assert any("already occupied" in i for i in loaded.issues)
    assert any("out of range" in i for i in loaded.issues)
    assert len(loaded.distribution.placement) == 1
    assert {c.id for c in loaded.distribution.unplaced} == {"B", "C"}


def test_unplaced_drives_punishment(tmp_path):
    yard = _yard()
    containers = [make_container(id=f"C{i}") for i in range(4)]
    path = tmp_path / "d.csv"
    path.write_text("container_id,block,column,row,layer\nC0,Block 1,0,0,0\n")
    loaded = load_distribution(path, yard, containers)
    result = score_distribution(loaded.distribution, containers)
    assert len(loaded.distribution.unplaced) == 3
    assert result.score.unplaced_count == 3


def test_floating_cell_warned(tmp_path):
    yard = _yard()
    containers = [make_container(id="top")]
    path = tmp_path / "d.csv"
    path.write_text("container_id,block,column,row,layer\ntop,Block 1,0,0,1\n")  # layer 1, nothing below
    loaded = load_distribution(path, yard, containers)
    assert any("floating" in i for i in loaded.issues)


def test_aggregate_by_block(tmp_path):
    yard = _yard()
    containers = [make_container(id=f"C{i}") for i in range(3)]
    path = tmp_path / "d.csv"
    path.write_text(
        "container_id,block,column,row,layer\n"
        "C0,Block 1,0,0,0\n"
        "C1,Block 1,1,0,0\n"
        "C2,Block 2,0,0,0\n"
    )
    loaded = load_distribution(path, yard, containers)
    result = score_distribution(loaded.distribution, containers)
    stats = {s.name: s for s in aggregate_by_block(result)}
    assert stats["Block 1"].count == 2
    assert stats["Block 2"].count == 1
