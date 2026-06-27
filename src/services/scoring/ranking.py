"""Datensonar-style rank aggregation over strategy comparison results.

Each metric is ranked 1..N across all strategies (lower value = better rank).
The overall ``total_rank`` is the rank of the sum of the four per-metric ranks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.models.scoring.result import EvaluationResult
from src.models.strategy.strategy import Strategy

MetricAccessor = Callable[[EvaluationResult], float]


@dataclass(frozen=True)
class StrategyRanking:
    strategy: Strategy
    result: EvaluationResult
    rehandles_value: float
    distance_value: float
    yard_distribution_value: float
    punishment_value: float
    rehandles_rank: int
    distance_rank: int
    yard_distribution_rank: int
    punishment_rank: int
    rank_sum: int
    total_rank: int


def _ordinal_ranks(values: list[tuple[float, int]]) -> list[int]:
    """Assign dense ordinal ranks 1..N; ties broken by original index."""
    ordered = sorted(range(len(values)), key=lambda i: (values[i][0], values[i][1]))
    ranks = [0] * len(values)
    for rank, idx in enumerate(ordered, start=1):
        ranks[idx] = rank
    return ranks


def _assign_metric_ranks(
    results: list[tuple[Strategy, EvaluationResult]],
    accessor: MetricAccessor,
) -> list[int]:
    values = [(accessor(result), index) for index, (_, result) in enumerate(results)]
    return _ordinal_ranks(values)


def rank_strategies(
    results: list[tuple[Strategy, EvaluationResult]],
) -> list[StrategyRanking]:
    """Rank strategies datensonar-style and return rows sorted by ``total_rank``."""
    if not results:
        return []

    rehandles_ranks = _assign_metric_ranks(results, lambda r: float(r.score.rehandles_count))
    distance_ranks = _assign_metric_ranks(results, lambda r: r.score.transport_distance)
    yard_ranks = _assign_metric_ranks(
        results, lambda r: r.score.yard_distribution
    )
    punishment_ranks = _assign_metric_ranks(
        results, lambda r: float(r.score.unplaced_count)
    )

    rank_sums = [
        rehandles_ranks[i]
        + distance_ranks[i]
        + yard_ranks[i]
        + punishment_ranks[i]
        for i in range(len(results))
    ]
    total_ranks = _ordinal_ranks([(float(rank_sum), index) for index, rank_sum in enumerate(rank_sums)])

    rankings = [
        StrategyRanking(
            strategy=strategy,
            result=result,
            rehandles_value=float(result.score.rehandles_count),
            distance_value=result.score.transport_distance,
            yard_distribution_value=result.score.yard_distribution,
            punishment_value=float(result.score.unplaced_count),
            rehandles_rank=rehandles_ranks[index],
            distance_rank=distance_ranks[index],
            yard_distribution_rank=yard_ranks[index],
            punishment_rank=punishment_ranks[index],
            rank_sum=rank_sums[index],
            total_rank=total_ranks[index],
        )
        for index, (strategy, result) in enumerate(results)
    ]
    return sorted(rankings, key=lambda row: (row.total_rank, row.rank_sum))
