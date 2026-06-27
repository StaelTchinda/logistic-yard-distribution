"""Command-line entry point: an interactive dialogue, plus headless subcommands.

No arguments        -> interactive picker (rich + questionary).
--list              -> list available yards / datasets / strategies.
--run    --yard K --dataset K --strategy K [--view] [--export-distribution FILE]
--compare --yard K --dataset K
--score-distribution FILE --yard K --dataset K [--view]
--data DIR          -> override the data/ directory for any of the above.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from src.loaders import load_containers, load_distribution, load_strategy, load_yard
from src.loaders.catalog import (
    CatalogEntry,
    find,
    scan_containers,
    scan_distributions,
    scan_strategies,
    scan_yards,
)
from src.loaders.paths import data_root
from src.models.strategy import evaluate, evaluate_all
from src.services.distribution import (
    aggregate_by_block,
    distribution_from_result,
    score_distribution,
    write_distribution,
)
from src.services.scoring.ranking import rank_strategies
from src.summary import summarize_containers
from src.view import (
    animate_fill,
    render_distribution_summary,
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
        ("Distributions", scan_distributions(root)),
    ):
        console.print(f"[bold]{heading}[/bold]")
        if not entries:
            console.print("  [dim](none)[/dim]")
        for entry in entries:
            desc = f" — {entry.description}" if entry.description else ""
            console.print(f"  [cyan]{entry.key}[/cyan]  ({entry.label}){desc}")
    return 0


def cmd_run(
    root, yard_key, dataset_key, strategy_key, view: bool, animate: bool, export: str | None = None
) -> int:
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
    console.print(render_distribution_summary(aggregate_by_block(result)))
    if result.unplaced:
        console.print(f"[yellow]{len(result.unplaced)} containers unplaced[/yellow]")
    if export:
        write_distribution(export, distribution_from_result(result))
        console.print(f"[green]Distribution exported to {export}[/green]")
    return 0


def _report_issues(issues: list[str], *, limit: int = 20) -> None:
    if not issues:
        return
    console.print(f"[red]{len(issues)} issue(s):[/red]")
    for issue in issues[:limit]:
        console.print(f"  [red]! {issue}[/red]")
    if len(issues) > limit:
        console.print(f"  [red]… and {len(issues) - limit} more[/red]")


def cmd_score_distribution(root, dist_path, yard_key, dataset_key, view: bool) -> int:
    yards, datasets, _ = _catalogs(root)
    ye = _resolve(yards, yard_key, "yard")
    de = _resolve(datasets, dataset_key, "dataset")
    if not (ye and de):
        return 2

    yard = load_yard(ye.path)
    containers = load_containers(de.path)
    loaded = load_distribution(dist_path, yard, containers)
    result = score_distribution(loaded.distribution, containers)
    console.print(
        f"[bold]{dist_path}[/bold] on [bold]{ye.label}[/bold] "
        f"with [bold]{de.key}[/bold] ({len(containers)} containers, "
        f"{len(loaded.distribution.placement)} placed)"
    )
    if view:
        console.print(render_yard(yard, result, title="Distribution"))
        console.print(render_distribution_summary(aggregate_by_block(result)))
    console.print(render_score(result.score, title="Score — distribution"))
    if loaded.distribution.unplaced:
        console.print(f"[yellow]{len(loaded.distribution.unplaced)} containers unplaced[/yellow]")
    _report_issues(loaded.issues)
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


def _interactive_strategies(root, yard, yard_key, dataset_key, containers, strategies) -> None:
    import questionary

    while True:
        strategy_entry = _select("Select a strategy to run:", strategies)
        if strategy_entry is None:
            return
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
        console.print(render_distribution_summary(aggregate_by_block(result)))
        if result.unplaced:
            console.print(f"[yellow]{len(result.unplaced)} containers unplaced[/yellow]")

        if questionary.confirm("Save this distribution to a file?", default=False).ask():
            name = f"{yard_key}___{dataset_key}___{strategy_entry.key}.csv"
            path = root / "distributions" / name
            write_distribution(path, distribution_from_result(result))
            console.print(f"[green]Saved distribution to {path}[/green]")

        action = questionary.select(
            "Now what?",
            choices=["Run another strategy", "Compare all strategies", "Back to menu"],
        ).ask()
        if action == "Compare all strategies":
            results = evaluate_all(yard, containers, [load_strategy(s.path) for s in strategies])
            console.print(render_report(results))
            console.print(render_ranking(rank_strategies(results)))
        elif action != "Run another strategy":
            return


def _interactive_distributions(root, yard, yard_key, dataset_key, containers) -> None:
    import questionary

    matching = [
        d
        for d in scan_distributions(root)
        if d.extra.get("yard") == yard_key and d.extra.get("dataset") == dataset_key
    ]
    if not matching:
        console.print(
            f"[yellow]No distributions for '{yard_key}' + '{dataset_key}'. Name files "
            f"data/distributions/{yard_key}___{dataset_key}___<id>.csv[/yellow]"
        )
        return
    while True:
        entry = _select("Select a distribution:", matching)
        if entry is None:
            return
        loaded = load_distribution(entry.path, yard, containers)
        result = score_distribution(loaded.distribution, containers)
        console.print(render_yard(yard, result, title=f"Distribution — {entry.key}"))
        console.print(render_distribution_summary(aggregate_by_block(result)))
        console.print(render_score(result.score, title=f"Score — {entry.key}"))
        if loaded.distribution.unplaced:
            console.print(
                f"[yellow]{len(loaded.distribution.unplaced)} containers unplaced[/yellow]"
            )
        _report_issues(loaded.issues)
        action = questionary.select(
            "Now what?", choices=["View another distribution", "Back to menu"]
        ).ask()
        if action != "View another distribution":
            return


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
        mode = questionary.select(
            "What would you like to evaluate?",
            choices=["Strategies", "Distributions", "Quit"],
        ).ask()
        if mode == "Strategies":
            _interactive_strategies(
                root, yard, yard_entry.key, dataset_entry.key, containers, strategies
            )
        elif mode == "Distributions":
            _interactive_distributions(
                root, yard, yard_entry.key, dataset_entry.key, containers
            )
        else:
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
    parser.add_argument(
        "--score-distribution",
        metavar="FILE",
        help="score a per-container distribution CSV (needs --yard and --dataset)",
    )
    parser.add_argument(
        "--export-distribution",
        metavar="FILE",
        help="with --run, export the resulting placement to FILE",
    )
    args = parser.parse_args(argv)

    try:
        root = data_root(args.data)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2

    if args.list:
        return cmd_list(root)
    if args.score_distribution:
        if not (args.yard and args.dataset):
            console.print("[red]--score-distribution needs --yard and --dataset[/red]")
            return 2
        return cmd_score_distribution(
            root, args.score_distribution, args.yard, args.dataset, args.view
        )
    if args.run:
        missing = [n for n in ("yard", "dataset", "strategy") if not getattr(args, n)]
        if missing:
            console.print(f"[red]--run needs --{', --'.join(missing)}[/red]")
            return 2
        return cmd_run(
            root,
            args.yard,
            args.dataset,
            args.strategy,
            args.view,
            args.animate,
            args.export_distribution,
        )
    if args.compare:
        if not (args.yard and args.dataset):
            console.print("[red]--compare needs --yard and --dataset[/red]")
            return 2
        return cmd_compare(root, args.yard, args.dataset)
    return run_interactive(root)
