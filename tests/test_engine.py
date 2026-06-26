from src.models import (
    Coordinate2D,
    Coordinate3D,
    Direction,
    TransportMode,
    Yard,
    YardBlock,
)
from src.models.strategy import (
    ContainerFilterableAttribute as Attr,
)
from src.models.strategy import (
    FilterCriterion,
    FilterRule,
    Region,
    Strategy,
    evaluate,
    find_best,
)
from tests.factories import make_container


def _yard():
    return Yard([YardBlock(3, 3, 3, Coordinate2D(0, 0), "A")])


def _containers():
    exports = [
        make_container(
            id=f"E{i}",
            outbound_mode=TransportMode.DEEP_SEA,
            direction=Direction.EXPORT,
        )
        for i in range(3)
    ]
    imports = [
        make_container(
            id=f"I{i}",
            outbound_mode=TransportMode.TRUCK,
            direction=Direction.IMPORT,
        )
        for i in range(3)
    ]
    return exports, imports


def test_conditions_route_to_region_and_keep_support():
    exports, imports = _containers()
    strategy = Strategy("s", "", [
        FilterRule(description="sea", sort_order=10,
                   conditions=(FilterCriterion(Attr.OUTBOUND_MODE, ("deep_sea",)),),
                   region=Region(x=(0, 0))),
        FilterRule(description="catch-all", sort_order=99),
    ])
    result = evaluate(strategy, _yard(), exports + imports)

    assert len(result.containers) == 6 and not result.unplaced
    for container in exports:  # sea rule forces column x == 0
        assert result.coord_of(container).x == 0
    placed = {result.coord_of(c) for c in result.containers}
    for coord in placed:  # nothing floats
        assert coord.z == 0 or Coordinate3D(coord.x, coord.y, coord.z - 1) in placed


def test_unmatched_without_catchall_is_unplaced():
    exports, imports = _containers()
    strategy = Strategy("s", "", [
        FilterRule(description="sea only", sort_order=10,
                   conditions=(FilterCriterion(Attr.OUTBOUND_MODE, ("deep_sea",)),)),
    ])
    result = evaluate(strategy, _yard(), exports + imports)
    assert len(result.containers) == 3  # exports only
    assert len(result.unplaced) == 3  # imports match no rule


def test_find_best_picks_lower_score():
    exports, imports = _containers()
    good = Strategy("good", "", [FilterRule(sort_order=1)])  # catch-all places everything
    bad = Strategy("bad", "", [FilterRule(sort_order=1, region=Region(x=(999, 999)))])
    best, _ = find_best(_yard(), exports + imports, [good, bad])
    assert best.name == "good"
