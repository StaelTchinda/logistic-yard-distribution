from src.loaders import _weight, load_containers, load_strategy, load_yard
from src.loaders.paths import data_root
from src.models import ContainerWeight
from src.models.strategy import RuleOption


def test_load_yard_yaml_matches_schema():
    yard = load_yard(data_root() / "yards" / "main.yaml")
    assert len(yard.blocks) == 12
    b1 = yard.blocks[0]
    assert (b1.columns_count, b1.rows_count, b1.layers_count) == (50, 10, 5)
    assert (b1.bottom_left_corner.x, b1.bottom_left_corner.y) == (20, 20)
    assert yard.get_stock_capacity() == 3155


def test_load_yard_csv():
    yard = load_yard(data_root() / "yards" / "compact.csv")
    assert len(yard.blocks) == 3
    assert yard.blocks[0].bottom_left_corner.x == 0
    assert yard.get_stock_capacity() == 4 * 4 * 4 + 4 * 4 * 4 + 6 * 6 * 3  # 236


def test_weight_accepts_name_or_int():
    assert _weight("heavy") == ContainerWeight.HEAVY
    assert _weight("3") == ContainerWeight.HEAVY
    assert _weight("") == ContainerWeight.MEDIUM


def test_load_containers_parsing_and_shared_vessels():
    conts = load_containers(data_root() / "containers" / "mixed.csv")
    assert len(conts) == 18
    by_id = {c.id: c for c in conts}
    assert by_id["EXP-EVER-0"].weight == ContainerWeight.HEAVY
    # both EXP-EVER boxes reference the same TransportVessel object
    assert by_id["EXP-EVER-0"].output_vessel is by_id["EXP-EVER-1"].output_vessel


def test_load_strategy_rules():
    strategy = load_strategy(data_root() / "strategies" / "quay_proximity.yaml")
    assert len(strategy.rules) == 4
    sea = strategy.sorted_rules()[0]
    assert sea.conditions[0].attribute.value == "outbound_mode"
    assert "deep_sea" in sea.conditions[0].values
    assert sea.region.x == (10, 40)
    assert RuleOption.WEIGHT_RELEVANT in sea.options
