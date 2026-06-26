from src.models import Coordinate2D, YardBlock
from src.models.scoring import (
    W_DISTANCE,
    W_REHANDLE,
    W_SORT,
    EvaluationResultScore,
    ScoreWeights,
    rehandles_count,
)
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
    weights = ScoreWeights(rehandle=1, distance=0, sort=0, unplaced=0)
    score = EvaluationResultScore(rehandles_count=3, transport_distance=99, weights=weights)
    assert score.get_score() == 3
