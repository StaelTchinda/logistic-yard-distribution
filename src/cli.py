"""Command-line entry point: an interactive dialogue, plus headless subcommands.

No arguments        -> interactive picker (rich + questionary).
--list              -> list available yards / datasets / strategies.
--run    --yard K --dataset K --strategy K [--view]
--compare --yard K --dataset K
--data DIR          -> override the data/ directory for any of the above.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from src.loaders import load_containers, load_strategy, load_yard
from src.loaders.catalog import (
    CatalogEntry,
    find,
    scan_containers,
    scan_strategies,
    scan_yards,
)
from src.loaders.paths import data_root
from src.models.strategy import evaluate, evaluate_all
from src.services.scoring.ranking import rank_strategies
from src.summary import summarize_containers
from src.view import (
    animate_fill,
    render_ranking,
    render_report,
    render_score,
    render_strategy,
    render_summary,
    render_yard,
)

console = Console()


def _catalogs(root):
    return scan_yards(root), scan_containers(root), scan_strategies(root)


def _resolve(entries: list[CatalogEntry], key: str, kind: str) -> CatalogEntry | None:
    entry = find(entries, key)
    if entry is None:
        options = ", ".join(e.key for e in entries) or "(none)"
        console.print(f"[red]Unknown {kind} '{key}'.[/red] Available: {options}")
    return entry


# ----------------------------------------------------------------- headless
def cmd_list(root) -> int:
    yards, datasets, strategies = _catalogs(root)
    for heading, entries in (
        ("Yards", yards),
        ("Datasets", datasets),
        ("Strategies", strategies),
    ):
        console.print(f"[bold]{heading}[/bold]")
        if not entries:
            console.print("  [dim](none)[/dim]")
        for entry in entries:
            desc = f" — {entry.description}" if entry.description else ""
            console.print(f"  [cyan]{entry.key}[/cyan]  ({entry.label}){desc}")
    return 0


def cmd_run(root, yard_key, dataset_key, strategy_key, view: bool, animate: bool) -> int:
    yards, datasets, strategies = _catalogs(root)
    ye = _resolve(yards, yard_key, "yard")
    de = _resolve(datasets, dataset_key, "dataset")
    se = _resolve(strategies, strategy_key, "strategy")
    if not (ye and de and se):
        return 2

    yard = load_yard(ye.path)
    containers = load_containers(de.path)
    strategy = load_strategy(se.path)
    console.print(
        f"[bold]{strategy.name}[/bold] on [bold]{ye.label}[/bold] "
        f"with [bold]{de.key}[/bold] ({len(containers)} containers)"
    )
    if view:
        console.print(render_strategy(strategy))
    if view and not animate:
        console.print(render_yard(yard, None, title="START (empty)"))
    result = evaluate(strategy, yard, containers)
    if animate:
        animate_fill(yard, result, title=f"Filling — {strategy.name}", console=console)
    elif view:
        console.print(render_yard(yard, result, title="END (filled)"))
    console.print(render_score(result.score, title=f"Score — {strategy.name}"))
    if result.unplaced:
        console.print(f"[yellow]{len(result.unplaced)} containers unplaced[/yellow]")
    return 0


def cmd_compare(root, yard_key, dataset_key) -> int:
    yards, datasets, strategies = _catalogs(root)
    ye = _resolve(yards, yard_key, "yard")
    de = _resolve(datasets, dataset_key, "dataset")
    if not (ye and de):
        return 2
    if not strategies:
        console.print("[red]No strategies found in data/strategies.[/red]")
        return 2
    yard = load_yard(ye.path)
    containers = load_containers(de.path)
    results = evaluate_all(yard, containers, [load_strategy(s.path) for s in strategies])
    console.print(render_report(results))
    console.print(render_ranking(rank_strategies(results)))
    return 0


# -------------------------------------------------------------- interactive
def _select(message: str, entries: list[CatalogEntry]):
    import questionary

    choices = [
        questionary.Choice(
            title=f"{e.label} ({e.key})" + (f" — {e.description}" if e.description else ""),
            value=e,
        )
        for e in entries
    ]
    return questionary.select(message, choices=choices).ask()  # None on Ctrl-C


def run_interactive(root) -> int:
    import questionary

    if not sys.stdin.isatty():
        console.print(
            "[yellow]Interactive mode needs a terminal. "
            "Use --list, --run or --compare instead.[/yellow]"
        )
        return 2

    yards, datasets, strategies = _catalogs(root)
    if not (yards and datasets and strategies):
        console.print("[red]data/ must contain yards, datasets and strategies.[/red]")
        return 2

    yard_entry = _select("Select a yard:", yards)
    if yard_entry is None:
        return 0
    yard = load_yard(yard_entry.path)
    console.print(
        f"[green]{yard_entry.label}[/green] — {yard.get_stock_capacity()} slots, "
        f"{len(yard.blocks)} blocks"
    )
    if questionary.confirm("Pretty-view this yard?", default=True).ask():
        console.print(render_yard(yard, None, title=yard_entry.label))

    dataset_entry = _select("Select a container dataset:", datasets)
    if dataset_entry is None:
        return 0
    containers = load_containers(dataset_entry.path)
    if questionary.confirm("View a summary of it?", default=True).ask():
        console.print(render_summary(summarize_containers(containers)))

    while True:
        strategy_entry = _select("Select a strategy to run:", strategies)
        if strategy_entry is None:
            return 0
        strategy = load_strategy(strategy_entry.path)
        if questionary.confirm("View the strategy's rules?", default=True).ask():
            console.print(render_strategy(strategy))
        result = evaluate(strategy, yard, containers)
        if questionary.confirm("Animate the yard filling up?", default=True).ask():
            animate_fill(yard, result, title=f"Filling — {strategy.name}", console=console)
        else:
            console.print(render_yard(yard, None, title="START (empty)"))
            console.print(render_yard(yard, result, title=f"END — {strategy.name}"))
        console.print(render_score(result.score, title=f"Score — {strategy.name}"))
        if result.unplaced:
            console.print(f"[yellow]{len(result.unplaced)} containers unplaced[/yellow]")

        action = questionary.select(
            "Now what?",
            choices=["Run another strategy", "Compare all strategies", "Quit"],
        ).ask()
        if action == "Compare all strategies":
            results = evaluate_all(
                yard, containers, [load_strategy(s.path) for s in strategies]
            )
            console.print(render_report(results))
            console.print(render_ranking(rank_strategies(results)))
            if not questionary.confirm("Run another strategy?", default=False).ask():
                return 0
        elif action != "Run another strategy":
            return 0


# --------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="yard", description="Rule-based container yard distribution."
    )
    parser.add_argument("--data", help="path to the data/ directory")
    parser.add_argument("--list", action="store_true", help="list yards/datasets/strategies")
    parser.add_argument("--run", action="store_true", help="run one strategy headlessly")
    parser.add_argument("--compare", action="store_true", help="run all strategies and compare")
    parser.add_argument("--yard")
    parser.add_argument("--dataset")
    parser.add_argument("--strategy")
    parser.add_argument("--view", action="store_true", help="render START/END yard grids")
    parser.add_argument(
        "--animate", action="store_true", help="animate the yard filling up (with --run)"
    )
    args = parser.parse_args(argv)

    try:
        root = data_root(args.data)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2

    if args.list:
        return cmd_list(root)
    if args.run:
        missing = [n for n in ("yard", "dataset", "strategy") if not getattr(args, n)]
        if missing:
            console.print(f"[red]--run needs --{', --'.join(missing)}[/red]")
            return 2
        return cmd_run(root, args.yard, args.dataset, args.strategy, args.view, args.animate)
    if args.compare:
        if not (args.yard and args.dataset):
            console.print("[red]--compare needs --yard and --dataset[/red]")
            return 2
        return cmd_compare(root, args.yard, args.dataset)
    return run_interactive(root)
