from collections import Counter

import pytest

from src.loaders import load_containers, load_strategy, load_yard
from src.loaders.paths import data_root
from src.models.strategy import evaluate
from src.services.scoring.datensonar_compare import DEFAULT_REFERENCE, run_default


def test_scoring_correlates_with_datensonar_reference():
    """Goal-level guard: identical where the original is 0, similar where it is high.

    The datensonar reference lives under the git-ignored private/ tree, so skip
    when it is absent (e.g. CI without that data).
    """
    reference = data_root().parent / DEFAULT_REFERENCE
    if not reference.is_file():
        pytest.skip(f"datensonar reference not available: {reference}")

    report = run_default()

    # Identical where the original is 0: every original zero-rehandles strategy
    # must also score exactly 0 rehandles here.
    assert report.rehandles_zero_total > 0
    assert report.rehandles_zero_match == report.rehandles_zero_total

    # Similar where the original is high: strong rank-correlation overall.
    assert report.ranking_rho > 0.6
    assert report.yard_rho > 0.8
    assert report.punishment_rho > 0.8


def test_status_stacking_spreads_full_containers_across_blocks():
    yard = load_yard(data_root() / "yards" / "datensonar.csv")
    containers = load_containers(data_root() / "containers" / "master_update.csv")
    strategy = load_strategy(
        data_root()
        / "strategies"
        / "einflussanalyse-master-update-status-stacking_2997.yaml"
    )

    result = evaluate(strategy, yard, containers)
    index = yard.slot_index()

    full_blocks = {
        index[coord].block.name
        for container, coord in zip(result.containers, result.container_coords)
        if container.status.value == "full"
    }

    assert {"Block 1", "Block 3", "Block 5", "Block 7"}.issubset(full_blocks)
    assert Counter(
        index[coord].block.name
        for container, coord in zip(result.containers, result.container_coords)
        if container.status.value == "full"
    )["Block 1"] < 17_000
