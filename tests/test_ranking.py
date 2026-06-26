from src.models import Yard
from src.models.scoring.result import EvaluationResult, EvaluationResultScore
from src.models.strategy import Strategy
from src.services.scoring.ranking import rank_strategies


def _result(
    name: str,
    *,
    rehandles: int = 0,
    distance: float = 0.0,
    balance: float = 0.0,
    unplaced: int = 0,
) -> tuple[Strategy, EvaluationResult]:
    strategy = Strategy(name, "")
    score = EvaluationResultScore(
        rehandles_count=rehandles,
        transport_distance=distance,
        balanced_distribution=balance,
        unplaced_count=unplaced,
    )
    result = EvaluationResult(Yard([]), [], [], score)
    return strategy, result


def test_rank_strategies_assigns_per_metric_ranks_and_total():
    results = [
        _result("A", rehandles=0, distance=100.0, balance=1.0, unplaced=0),
        _result("B", rehandles=0, distance=50.0, balance=2.0, unplaced=0),
        _result("C", rehandles=5, distance=50.0, balance=0.5, unplaced=10),
    ]
    rankings = {row.strategy.name: row for row in rank_strategies(results)}

    assert rankings["A"].rehandles_rank == 1
    assert rankings["B"].rehandles_rank == 2
    assert rankings["C"].rehandles_rank == 3

    assert rankings["B"].distance_rank == 1
    assert rankings["C"].distance_rank == 2
    assert rankings["A"].distance_rank == 3

    assert rankings["C"].yard_distribution_rank == 1
    assert rankings["A"].yard_distribution_rank == 2
    assert rankings["B"].yard_distribution_rank == 3

    assert rankings["A"].punishment_rank == 1
    assert rankings["B"].punishment_rank == 2
    assert rankings["C"].punishment_rank == 3

    assert rankings["A"].rank_sum == 7
    assert rankings["B"].rank_sum == 8
    assert rankings["C"].rank_sum == 9

    assert rankings["A"].total_rank == 1
    assert rankings["B"].total_rank == 2
    assert rankings["C"].total_rank == 3


def test_rank_strategies_breaks_ties_by_input_order():
    results = [
        _result("first", distance=10.0),
        _result("second", distance=10.0),
    ]
    rankings = {row.strategy.name: row for row in rank_strategies(results)}

    assert rankings["first"].distance_rank == 1
    assert rankings["second"].distance_rank == 2
    assert rankings["first"].total_rank == 1
    assert rankings["second"].total_rank == 2


def test_rank_strategies_returns_sorted_by_total_rank():
    results = [
        _result("worst", rehandles=10, distance=100.0, balance=5.0, unplaced=5),
        _result("best", rehandles=0, distance=10.0, balance=0.1, unplaced=0),
        _result("middle", rehandles=2, distance=50.0, balance=1.0, unplaced=1),
    ]
    ordered = rank_strategies(results)

    assert [row.strategy.name for row in ordered] == ["best", "middle", "worst"]
    assert [row.total_rank for row in ordered] == [1, 2, 3]
