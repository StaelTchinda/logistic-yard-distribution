from src.models import ContainerService, ContainerType, ContainerWeight, Direction
from src.models.strategy import ContainerFilterableAttribute as Attr
from src.models.strategy import FilterCriterion
from tests.factories import make_container


def test_size_equality_and_direction_membership():
    c = make_container(id="C", size=40, direction=Direction.EXPORT)
    assert FilterCriterion(Attr.SIZE, ("40",)).matches(c)
    assert not FilterCriterion(Attr.SIZE, ("20",)).matches(c)
    assert FilterCriterion(Attr.DIRECTION, ("export", "waterside_transshipment")).matches(c)


def test_weight_and_service():
    c = make_container(id="C", weight=ContainerWeight.HEAVY, service=ContainerService.CUSTOMS)
    assert FilterCriterion(Attr.WEIGHT, ("heavy",)).matches(c)
    assert FilterCriterion(Attr.SERVICE, ("customs",)).matches(c)
    assert not FilterCriterion(Attr.SERVICE, ("washing",)).matches(make_container(id="N"))


def test_service_filter_single_and_multi():
    washing = make_container(id="W", service=ContainerService.WASHING)
    multi = make_container(
        id="M", service=[ContainerService.SEAL, ContainerService.CUSTOMS]
    )
    assert FilterCriterion(Attr.SERVICE, ("washing",)).matches(washing)
    assert not FilterCriterion(Attr.SERVICE, ("customs",)).matches(washing)
    assert FilterCriterion(Attr.SERVICE, ("customs",)).matches(multi)
    assert FilterCriterion(Attr.SERVICE, ("seal", "stuff")).matches(multi)
    assert not FilterCriterion(Attr.SERVICE, ("washing",)).matches(multi)
    assert not FilterCriterion(Attr.SERVICE, ("customs",)).matches(make_container(id="N"))


def test_type_filter_single_and_multi():
    dry = make_container(id="D", type=ContainerType.DRY)
    multi = make_container(id="M", type=[ContainerType.DRY, ContainerType.REEFER])
    assert FilterCriterion(Attr.TYPE, ("dry",)).matches(dry)
    assert not FilterCriterion(Attr.TYPE, ("reefer",)).matches(dry)
    assert FilterCriterion(Attr.TYPE, ("reefer",)).matches(multi)
    assert FilterCriterion(Attr.TYPE, ("dry", "hazardous")).matches(multi)
    assert not FilterCriterion(Attr.TYPE, ("tank",)).matches(multi)


def test_output_transport_subattributes_and_missing():
    c = make_container(
        id="C",
        output_name="Ever-Given",
        output_carrier="Evergreen",
        output_liner="EGL",
    )
    assert FilterCriterion(Attr.OUTPUT_NAME, ("ever-given",)).matches(c)  # case-insensitive
    assert FilterCriterion(Attr.OUTPUT_CARRIER, ("evergreen",)).matches(c)
    assert FilterCriterion(Attr.OUTPUT_LINER, ("egl",)).matches(c)
    assert not FilterCriterion(Attr.OUTPUT_NAME, ("maersk",)).matches(c)
    assert not FilterCriterion(Attr.OUTPUT_CARRIER, ("maersk",)).matches(c)
    missing = make_container(id="N")
    assert not FilterCriterion(Attr.OUTPUT_NAME, ("ever-given",)).matches(missing)
