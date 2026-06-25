from src.models import (
    Container,
    ContainerService,
    ContainerWeight,
    Direction,
    TransportVessel,
)
from src.models.strategy import ContainerFilterableAttribute as Attr
from src.models.strategy import FilterCriterion


def test_size_equality_and_direction_membership():
    c = Container(id="C", size=40, direction=Direction.EXPORT)
    assert FilterCriterion(Attr.SIZE, ("40",)).matches(c)
    assert not FilterCriterion(Attr.SIZE, ("20",)).matches(c)
    assert FilterCriterion(Attr.DIRECTION, ("export", "waterside_transshipment")).matches(c)


def test_weight_and_service():
    c = Container(id="C", weight=ContainerWeight.HEAVY, service=ContainerService.CUSTOMS)
    assert FilterCriterion(Attr.WEIGHT, ("heavy",)).matches(c)
    assert FilterCriterion(Attr.SERVICE, ("customs",)).matches(c)
    assert not FilterCriterion(Attr.SERVICE, ("washing",)).matches(Container(id="N"))


def test_output_vessel_name_and_missing():
    c = Container(id="C", output_vessel=TransportVessel("Ever-Given"))
    assert FilterCriterion(Attr.OUTPUT_VESSEL, ("ever-given",)).matches(c)  # case-insensitive
    assert not FilterCriterion(Attr.OUTPUT_VESSEL, ("maersk",)).matches(c)
    assert not FilterCriterion(Attr.OUTPUT_VESSEL, ("ever-given",)).matches(Container(id="N"))
