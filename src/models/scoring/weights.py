"""Score weights. The total score is a weighted sum; lower is better."""

from __future__ import annotations

from dataclasses import dataclass

# Module-level defaults (tune to express priorities).
W_REHANDLE = 10.0
W_DISTANCE = 1.0
W_SORT = 5.0
W_UNPLACED = 1000.0  # a container that cannot be placed is heavily penalized
W_BALANCE = 1.0


@dataclass(frozen=True)
class ScoreWeights:
    rehandle: float = W_REHANDLE
    distance: float = W_DISTANCE
    sort: float = W_SORT
    unplaced: float = W_UNPLACED
    balance: float = W_BALANCE


DEFAULT_WEIGHTS = ScoreWeights()
