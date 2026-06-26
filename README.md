# Logistic Yard Distribution

A Python model of the **container-terminal yard storage-allocation** problem: given a yard
and a set of incoming containers, decide *where each container goes* — and compare
strategies by a score. Placement is driven by **declarative rules** (the shape of a real
yard-planning rule editor), so strategies are **data you edit**, not code.

## How it works

A **strategy** is an ordered list of **rules**. Each rule says:

> *Containers matching these **conditions** go into this **region** of the yard, filled from
> a **start** corner in a given axis **order**, leaving **skip** gaps, with these **options**.*

The engine routes each container to the **first rule (by `sort_order`) whose conditions
match**, then fills that rule's region bottom-up so stacks stay supported. The placement is
scored on three metrics, all **minimized**:

| metric | meaning |
| --- | --- |
| `rehandles` | reshuffles to dig out an earlier-retrieved box buried under a later one (retrieval order = dataset order) |
| `transport_distance` | Manhattan distance from each slot to its outbound access point (quay / rail / gate) |
| `manual_sort_effort` | load-group mixing within stacks |

`get_score()` is a weighted sum (weights in
[`src/models/scoring/weights.py`](src/models/scoring/weights.py)); lower is better. The
driver runs every strategy on the same yard + containers and picks the lowest.

A **condition** is a `FilterCriterion`: an attribute from `ContainerFilterableAttribute`
(`size`, `type`, `status`, `weight`, `inbound_mode`, `outbound_mode`, `direction`,
`service`, `input_vessel`, `output_vessel`) tested against one or more allowed values
(membership).

## Layout

```
src/
  models/      Coordinate2D/3D, Container, TransportVessel, YardBlock, Slot, Yard, enums
    strategy/  ContainerFilterableAttribute, FilterCriterion, FilterRule, Strategy
    scoring/   weights, access points, result objects
  services/    placement engine (filter/) and scoring metrics (scoring/)
  loaders/     load yards/containers/strategies + data discovery + catalog
  view/        rich rendering (yard grids, summary, score, comparison)
  summary.py   dataset statistics
  cli.py       interactive + headless entry point
data/
  yards/       *.yaml or *.csv   (blocks: columns/rows/layers + bottom_left_corner x,y)
  containers/  *.csv             (one row per container; optional flattened vessel columns)
  strategies/  *.yaml            (rule-sets)
main.py · tests/ · pyproject.toml
```

Imports are rooted at the repo with a `src.` prefix (e.g. `from src.models.yard import Yard`).
There is no installable package — `src/` is simply the source root.

## Setup (uv)

[uv](https://docs.astral.sh/uv/) manages the virtual environment and dependencies
(`pyyaml`, `rich`, `questionary`). The project itself is **not** installed
(`tool.uv.package = false` in `pyproject.toml`).

```bash
brew install uv            # or: curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync                    # create .venv and install dependencies
```

## Run

```bash
uv run python main.py                          # interactive dialogue
uv run python main.py --list                   # list yards / datasets / strategies
uv run python main.py --run --yard small --dataset simple_test_data --strategy quay_proximity --view
uv run python main.py --compare --yard small --dataset simple_test_data
uv run pytest                                  # run the tests
```

Interactive mode lets you pick a yard (and pretty-view it), pick a dataset (and view a
summary), then pick a strategy and see the **START** (empty yard), the **END** (filled), and
the score. `--list` / `--run` / `--compare` are headless (no terminal required).

Bundled strategies to compare: `first_fit` (baseline), `quay_proximity` (route by outbound
mode), `retrieval_order` (group by direction, weight-relevant stacking).

## Add your own data

Drop a file into the matching `data/` folder — it appears in the menus automatically.

**A yard** (`data/yards/<name>.yaml`, or a `.csv` with columns `name, columns, rows,
layers, bottom_left_corner_x, bottom_left_corner_y`):
```yaml
name: "My yard"
yard:
  blocks:
    - {name: "A", columns: 10, rows: 6, layers: 4, bottom_left_corner: {x: 0, y: 0}}
```

**A dataset** (`data/containers/<name>.csv`) — header columns: `id,size,type,status,weight,
inbound_mode,outbound_mode,direction,service,input_vessel,output_vessel`
(`type` and `service` accept comma-separated values, e.g. `dry,reefer` or
`seal,customs`; `weight` accepts
`light/medium/heavy` or `1/2/3`; vessels by name).

**A strategy** (`data/strategies/<name>.yaml`) — a rule-set:
```yaml
name: "My strategy"
rules:
  - description: "Sea exports near the quay"
    sort_order: 10
    conditions:
      - {attribute: outbound_mode, values: [deep_sea, feeder]}
      - {attribute: direction, values: [export]}
    region: {x: [10, 40], y: [0, 2], z: [0, 4]}        # global coords; null bound = clip to yard
    skip: {x: 0, y: 0}
    stacking: {start: bottom_left, order: [z, x, y]}    # z outermost = spread before stacking
    options: [weight_relevant]                          # heavier containers on lower tiers
  - {description: "catch-all", sort_order: 9999}        # no conditions = matches anything
```

Rule fields mirror the editor: `conditions`, `region` (X/Y/Z global ranges), `skip`,
`stacking` (`start`: `bottom_left` / `bottom_right` / `top_left` / `top_right`; `order`: a
permutation of `x`/`y`/`z`, outermost first), `options` (`weight_relevant`), and `sort_order`
(lowest wins).
