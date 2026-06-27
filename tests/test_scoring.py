from src.models import Coordinate2D, YardBlock
from src.models.scoring import (
    W_BALANCE,
    W_DISTANCE,
    W_REHANDLE,
    W_SORT,
    EvaluationResultScore,
    ScoreWeights,
)
from src.services.scoring import balanced_distribution, rehandles_count
from src.models.yard import Slot
from tests.factories import make_container


def test_rehandles_counts_buried_early_retrieved():
    block = YardBlock(1, 1, 3, Coordinate2D(0, 0))
    early = make_container(id="early")
    late = make_container(id="late")
    order = [early, late]  # 'early' is retrieved first

    buried = [(early, Slot(block, 0, 0, 0)), (late, Slot(block, 0, 0, 1))]
    assert rehandles_count(buried, order) == 1  # early buried under late

    good = [(late, Slot(block, 0, 0, 0)), (early, Slot(block, 0, 0, 1))]
    assert rehandles_count(good, order) == 0  # earliest on top

    assert rehandles_count(buried) == 0  # no retrieval order -> no blocking


def test_get_score_default_weighted_sum():
    score = EvaluationResultScore(
        rehandles_count=2, transport_distance=10.0, manual_sort_effort=1
    )
    assert score.get_score() == round(W_REHANDLE * 2 + W_DISTANCE * 10.0 + W_SORT * 1)


def test_get_score_with_custom_weights():
    weights = ScoreWeights(rehandle=1, distance=0, sort=0, unplaced=0, balance=0)
    score = EvaluationResultScore(rehandles_count=3, transport_distance=99, weights=weights)
    assert score.get_score() == 3


def test_get_score_includes_balanced_distribution():
    score = EvaluationResultScore(balanced_distribution=0.5)
    assert score.get_score() == round(W_BALANCE * 0.5)


def test_balanced_distribution():
    block_a = YardBlock(2, 2, 1, Coordinate2D(0, 0), "A")
    block_b = YardBlock(2, 2, 1, Coordinate2D(10, 0), "B")
    blocks = [block_a, block_b]
    capacity = block_a.get_stock_capacity()  # 4 per block

    # Single block yard -> no imbalance metric
    single_block = [block_a]
    concentrated = [
        (make_container(id=f"c{i}"), Slot(block_a, i % 2, i // 2, 0))
        for i in range(capacity)
    ]
    assert balanced_distribution(concentrated, single_block) == 0.0

    # All containers in block A, block B empty -> high imbalance
    assert balanced_distribution(concentrated, blocks) > 0.0

    # Split evenly across both blocks -> perfectly balanced
    spread = [
        (make_container(id=f"a{i}"), Slot(block_a, i % 2, i // 2, 0))
        for i in range(capacity // 2)
    ] + [
        (make_container(id=f"b{i}"), Slot(block_b, i % 2, i // 2, 0))
        for i in range(capacity // 2)
    ]
    assert balanced_distribution(spread, blocks) == 0.0
    assert balanced_distribution(spread, blocks) < balanced_distribution(concentrated, blocks)
