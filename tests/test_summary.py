from src.models import Container, ContainerService, ContainerType
from src.summary import summarize_containers


def test_counts_sum_to_total():
    conts = [
        Container(id=str(i), type=ContainerType.DRY if i % 2 else ContainerType.REEFER)
        for i in range(6)
    ]
    summary = summarize_containers(conts)
    assert summary.total == 6
    assert sum(summary.by_type.values()) == 6
    assert sum(summary.by_direction.values()) == 6
    assert summary.by_type["reefer"] == 3


def test_service_counts():
    conts = [Container(id="a", service=ContainerService.WASHING), Container(id="b")]
    summary = summarize_containers(conts)
    assert summary.by_service["washing"] == 1
    assert summary.by_service["none"] == 1
