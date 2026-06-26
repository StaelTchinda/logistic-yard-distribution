from src.models import ContainerService, ContainerType
from src.summary import summarize_containers
from tests.factories import make_container


def test_counts_sum_to_total():
    conts = [
        make_container(id=str(i), type=ContainerType.DRY if i % 2 else ContainerType.REEFER)
        for i in range(6)
    ]
    summary = summarize_containers(conts)
    assert summary.total == 6
    assert sum(summary.by_type.values()) == 6
    assert sum(summary.by_direction.values()) == 6
    assert summary.by_type["reefer"] == 3


def test_multi_type_counts_each_type():
    conts = [make_container(id="multi", type=[ContainerType.DRY, ContainerType.REEFER])]
    summary = summarize_containers(conts)
    assert summary.total == 1
    assert summary.by_type["dry"] == 1
    assert summary.by_type["reefer"] == 1
    assert sum(summary.by_type.values()) == 2


def test_multi_service_counts_each_service():
    conts = [
        make_container(
            id="multi",
            service=[ContainerService.SEAL, ContainerService.CUSTOMS],
        )
    ]
    summary = summarize_containers(conts)
    assert summary.total == 1
    assert summary.by_service["seal"] == 1
    assert summary.by_service["customs"] == 1
    assert sum(summary.by_service.values()) == 2


def test_service_counts():
    conts = [make_container(id="a", service=ContainerService.WASHING), make_container(id="b")]
    summary = summarize_containers(conts)
    assert summary.by_service["washing"] == 1
    assert "none" not in summary.by_service
    assert sum(summary.by_service.values()) == 1
