"""Scoring data models: weights, access points, and result objects.

The metric *functions* live in ``src.services.scoring.metrics`` (services depend on
models, not the reverse) -- import them from there, not from this package.
"""

from .access import AccessPoints
from .result import EvaluationResult, EvaluationResultScore
from .weights import (
    DEFAULT_WEIGHTS,
    W_BALANCE,
    W_DISTANCE,
    W_REHANDLE,
    W_SORT,
    W_UNPLACED,
    ScoreWeights,
)

__all__ = [
    "AccessPoints",
    "EvaluationResult",
    "EvaluationResultScore",
    "ScoreWeights",
    "DEFAULT_WEIGHTS",
    "W_REHANDLE",
    "W_DISTANCE",
    "W_SORT",
    "W_UNPLACED",
    "W_BALANCE",
]
