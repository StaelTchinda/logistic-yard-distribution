import warnings

from src.loaders import _parse_container_row, _parse_weight, load_containers, load_strategy, load_yard
from src.loaders.paths import data_root
from src.models import ContainerService, ContainerType, ContainerWeight


def test_load_yard_yaml_matches_schema():
    yard = load_yard(data_root() / "yards" / "small.yaml")
    assert len(yard.blocks) == 3
    b1 = yard.blocks[0]
    assert (b1.columns_count, b1.rows_count, b1.layers_count) == (4, 3, 3)
    assert (b1.bottom_left_corner.x, b1.bottom_left_corner.y) == (0, 0)
    assert yard.get_stock_capacity() == 99


def test_load_yard_csv():
    yard = load_yard(data_root() / "yards" / "datensonar.csv")
    assert len(yard.blocks) == 12
    assert yard.blocks[0].bottom_left_corner.x == 20
    assert yard.get_stock_capacity() == 36000


def test_weight_accepts_name_or_int():
    assert _parse_weight("heavy") == ContainerWeight.HEAVY
    assert _parse_weight("3") == ContainerWeight.HEAVY
    assert _parse_weight("") is None


def test_load_containers_parsing_and_shared_output_name():
    conts = load_containers(data_root() / "containers" / "simple_test_data.csv")
    assert len(conts) == 15
    by_id = {c.id: c for c in conts}
    assert by_id["VBPQ9182813"].weight == ContainerWeight.HEAVY
    assert by_id["MNGH2851746"].output_name == by_id["WRUE4412898"].output_name == "Jim Wonder"


def test_load_containers_parses_comma_separated_types():
    row = {
        "id": "MULTI",
        "size": "20",
        "type": "dry, reefer",
        "status": "full",
        "weight": "medium",
        "inbound_mode": "truck",
        "outbound_mode": "truck",
        "direction": "import",
    }
    container = _parse_container_row(row)
    assert container is not None
    assert container.type == [ContainerType.DRY, ContainerType.REEFER]


def test_load_containers_skips_invalid_row_with_warning():
    row = {
        "id": "BAD",
        "size": "20",
        "type": "",
        "status": "full",
        "weight": "light",
        "inbound_mode": "truck",
        "outbound_mode": "truck",
        "direction": "import",
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert _parse_container_row(row) is None
    assert any("missing type" in str(w.message) for w in caught)


def test_load_containers_parses_comma_separated_services():
    row = {
        "id": "MULTI",
        "size": "20",
        "type": "dry",
        "status": "full",
        "weight": "medium",
        "inbound_mode": "truck",
        "outbound_mode": "truck",
        "direction": "import",
        "service": "seal, customs",
    }
    container = _parse_container_row(row)
    assert container is not None
    assert container.service == [ContainerService.SEAL, ContainerService.CUSTOMS]


def test_load_containers_optional_service_and_transport():
    row = {
        "id": "OK",
        "size": "20",
        "type": "dry",
        "status": "full",
        "weight": "medium",
        "inbound_mode": "truck",
        "outbound_mode": "truck",
        "direction": "import",
        "service": "",
        "input_vessel": "",
        "output_vessel": "",
    }
    container = _parse_container_row(row)
    assert container is not None
    assert container.service == []
    assert container.input_name == ""
    assert container.output_name == ""


def test_load_containers_flattened_transport_columns():
    row = {
        "id": "V1",
        "size": "40",
        "type": "dry",
        "status": "full",
        "weight": "heavy",
        "inbound_mode": "deep_sea",
        "outbound_mode": "deep_sea",
        "direction": "export",
        "output_vessel": "Ever-Given",
        "output_vessel_carrier": "Evergreen",
        "output_vessel_liner": "EGL",
        "output_vessel_service": "FE1",
    }
    container = _parse_container_row(row)
    assert container is not None
    assert container.output_name == "Ever-Given"
    assert container.output_carrier == "Evergreen"
    assert container.output_liner == "EGL"


def test_load_strategy_rules():
    strategy = load_strategy(
        data_root()
        / "strategies"
        / "2-strategie-advanced-allgemein-umschlag-fluss-v1-5-makuetche_2881.yaml"
    )
    assert len(strategy.rules) == 16
    # Datensonar z:[1,1] is the ground tier only (0-based (0, 0)), not expanded to 5 tiers.
    assert strategy.rules[0].region.z == (0, 0)
    assert strategy.rules[0].conditions[0].attribute.value == "inbound_mode"
