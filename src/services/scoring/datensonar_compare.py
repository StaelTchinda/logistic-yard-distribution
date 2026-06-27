"""Compare this engine's scoring against the original datensonar reference scorings.

Loads the reference CSV scraped from datensonar, matches it to locally evaluated
strategies by name, and reports per-metric rank-correlation, the rehandles
zero-match count, and the overall ranking correlation. Used both as a regression
guard (see ``tests/test_datensonar_alignment.py``) and as a calibration tool:

    uv run python -m src.services.scoring.datensonar_compare
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from src.models.scoring.result import EvaluationResult
from src.models.strategy.strategy import Strategy
from src.services.scoring.ranking import rank_strategies

# Reference scorings live under the (git-ignored) private/ tree at repo root.
DEFAULT_REFERENCE = "private/data/scorings/ys-kq34f-datensonar-de-2026-06-26.csv"


def normalize_name(name: str) -> str:
    """Canonical key for matching local strategy ``name:`` to the CSV ``strategy``."""
    return re.sub(r"[\s_]+", "_", name.strip().lower())


def load_reference(csv_path: str | Path) -> dict[str, dict[str, float | None]]:
    """Parse the datensonar reference CSV, keyed by normalized strategy name.

    Values are floats; blank cells (e.g. yard_distribution for strategies that
    place nothing) become ``None``.
    """
    def num(value: str) -> float | None:
        value = (value or "").strip()
        return float(value) if value else None

    reference: dict[str, dict[str, float | None]] = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            reference[normalize_name(row["strategy"])] = {
                "total_rank": num(row["total_rank"]),
                "rehandles": num(row["rehandles_value"]),
                "distance": num(row["distance_value"]),
                "yard_distribution": num(row["yard_distribution_value"]),
                "punishment": num(row["punishment_value"]),
            }
    return reference


def _rank_vector(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for rank, idx in enumerate(order):
        ranks[idx] = float(rank)
    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 2:
        return float("nan")
    mean_a, mean_b = sum(a) / n, sum(b) / n
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    var_a = sum((x - mean_a) ** 2 for x in a) ** 0.5
    var_b = sum((x - mean_b) ** 2 for x in b) ** 0.5
    return cov / (var_a * var_b) if var_a and var_b else float("nan")


def spearman(a: list[float], b: list[float]) -> float:
    """Spearman rank-correlation (Pearson over ranks); no external dependency."""
    return _pearson(_rank_vector(a), _rank_vector(b))


@dataclass
class ComparisonReport:
    matched: int
    unmatched: list[str]
    rehandles_zero_total: int  # strategies the original scores at 0 rehandles
    rehandles_zero_match: int  # of those, how many the engine also scores at 0
    rehandles_rho: float
    distance_rho: float
    yard_rho: float
    punishment_rho: float
    ranking_rho: float


def compare(
    results: list[tuple[Strategy, EvaluationResult]],
    reference: dict[str, dict[str, float | None]],
) -> ComparisonReport:
    """Correlate evaluated ``results`` against the datensonar ``reference``."""
    matched: list[tuple[Strategy, EvaluationResult, dict[str, float | None]]] = []
    unmatched: list[str] = []
    for strategy, result in results:
        ref = reference.get(normalize_name(strategy.name))
        if ref is None:
            unmatched.append(strategy.name)
        else:
            matched.append((strategy, result, ref))

    own_re, orig_re = [], []
    own_di, orig_di = [], []
    own_ya, orig_ya = [], []
    own_pu, orig_pu = [], []
    zero_total = zero_match = 0
    for _, result, ref in matched:
        score = result.score
        if ref["rehandles"] is not None:
            own_re.append(float(score.rehandles_count))
            orig_re.append(ref["rehandles"])
            if ref["rehandles"] == 0:
                zero_total += 1
                if score.rehandles_count == 0:
                    zero_match += 1
        if ref["distance"] is not None:
            own_di.append(score.transport_distance)
            orig_di.append(ref["distance"])
        if ref["yard_distribution"] is not None:
            own_ya.append(score.yard_distribution)
            orig_ya.append(ref["yard_distribution"])
        if ref["punishment"] is not None:
            own_pu.append(float(score.unplaced_count))
            orig_pu.append(ref["punishment"])

    # Ranking correlation: rank the matched subset our way, compare to datensonar's
    # total_rank over the same subset.
    rankings = rank_strategies([(s, r) for s, r, _ in matched])
    own_rank_by_name = {rk.strategy.name: float(rk.total_rank) for rk in rankings}
    own_rank, orig_rank = [], []
    for strategy, _, ref in matched:
        if ref["total_rank"] is not None:
            own_rank.append(own_rank_by_name[strategy.name])
            orig_rank.append(ref["total_rank"])

    return ComparisonReport(
        matched=len(matched),
        unmatched=unmatched,
        rehandles_zero_total=zero_total,
        rehandles_zero_match=zero_match,
        rehandles_rho=spearman(own_re, orig_re),
        distance_rho=spearman(own_di, orig_di),
        yard_rho=spearman(own_ya, orig_ya),
        punishment_rho=spearman(own_pu, orig_pu),
        ranking_rho=spearman(own_rank, orig_rank),
    )


def format_report(report: ComparisonReport) -> str:
    lines = [
        f"matched strategies : {report.matched}  (unmatched: {len(report.unmatched)})",
        f"rehandles zero-match: {report.rehandles_zero_match}/{report.rehandles_zero_total}"
        " (exact-zero agreement)",
        "rank-correlation (Spearman) vs datensonar:",
        f"  overall ranking  : {report.ranking_rho:+.3f}",
        f"  rehandles        : {report.rehandles_rho:+.3f}",
        f"  distance         : {report.distance_rho:+.3f}",
        f"  yard_distribution: {report.yard_rho:+.3f}",
        f"  punishment       : {report.punishment_rho:+.3f}",
    ]
    if report.unmatched:
        lines.append("unmatched local strategies: " + ", ".join(report.unmatched))
    return "\n".join(lines)


@dataclass
class ComparisonRow:
    strategy: str
    orig_rank: float | None
    own_rehandles: float
    orig_rehandles: float | None
    own_distance: float
    orig_distance: float | None
    own_yard: float
    orig_yard: float | None
    own_punishment: float
    orig_punishment: float | None


def comparison_rows(
    results: list[tuple[Strategy, EvaluationResult]],
    reference: dict[str, dict[str, float | None]],
) -> list[ComparisonRow]:
    """Per-strategy own-vs-reference scores, sorted by the original total_rank."""
    rows: list[ComparisonRow] = []
    for strategy, result in results:
        ref = reference.get(normalize_name(strategy.name))
        if ref is None:
            continue
        score = result.score
        rows.append(
            ComparisonRow(
                strategy=strategy.name,
                orig_rank=ref["total_rank"],
                own_rehandles=float(score.rehandles_count),
                orig_rehandles=ref["rehandles"],
                own_distance=score.transport_distance,
                orig_distance=ref["distance"],
                own_yard=score.yard_distribution,
                orig_yard=ref["yard_distribution"],
                own_punishment=float(score.unplaced_count),
                orig_punishment=ref["punishment"],
            )
        )
    rows.sort(key=lambda row: (row.orig_rank is None, row.orig_rank or 0.0))
    return rows


def render_detail(rows: list[ComparisonRow]) -> None:
    """Print a rich side-by-side table (own vs datensonar) for each strategy."""
    from rich.console import Console
    from rich.table import Table

    def i(value: float | None) -> str:
        return "-" if value is None else f"{value:,.0f}"

    def m(value: float | None) -> str:
        return "-" if value is None else f"{value / 1e6:.2f}"

    table = Table(title="Per-strategy scores: own vs datensonar (DS)")
    table.add_column("DS\nrank", justify="right")
    table.add_column("strategy", overflow="fold")
    table.add_column("reh\nown", justify="right")
    table.add_column("reh\nDS", justify="right")
    table.add_column("dist own\n(M)", justify="right")
    table.add_column("dist DS\n(M)", justify="right")
    table.add_column("yard\nown", justify="right")
    table.add_column("yard\nDS", justify="right")
    table.add_column("pun\nown", justify="right")
    table.add_column("pun\nDS", justify="right")
    for row in rows:
        table.add_row(
            i(row.orig_rank),
            row.strategy,
            i(row.own_rehandles),
            i(row.orig_rehandles),
            m(row.own_distance),
            m(row.orig_distance),
            i(row.own_yard),
            i(row.orig_yard),
            i(row.own_punishment),
            i(row.orig_punishment),
        )
    Console().print(table)


def load_results_and_reference(
    reference_path: str | Path = DEFAULT_REFERENCE,
) -> tuple[list[tuple[Strategy, EvaluationResult]], dict[str, dict[str, float | None]]]:
    """Evaluate every datensonar strategy on master_update; return (results, reference)."""
    from src.loaders import load_containers, load_strategy, load_yard
    from src.loaders.catalog import scan_strategies
    from src.loaders.paths import data_root
    from src.services.filter.engine import evaluate_all

    root = data_root()
    yard = load_yard(root / "yards" / "datensonar.csv")
    containers = load_containers(root / "containers" / "master_update.csv")
    strategies = [load_strategy(entry.path) for entry in scan_strategies(root)]
    results = evaluate_all(yard, containers, strategies)

    path = Path(reference_path)
    if not path.is_absolute():
        path = root.parent / path
    return results, load_reference(path)


def run_default(reference_path: str | Path = DEFAULT_REFERENCE) -> ComparisonReport:
    """Evaluate every datensonar strategy on master_update and compare to reference."""
    results, reference = load_results_and_reference(reference_path)
    return compare(results, reference)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare engine scoring against the datensonar reference."
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="print a per-strategy own-vs-datensonar score table",
    )
    parser.add_argument("--reference", default=DEFAULT_REFERENCE)
    args = parser.parse_args()

    results, reference = load_results_and_reference(args.reference)
    print(format_report(compare(results, reference)))
    if args.detail:
        print()
        render_detail(comparison_rows(results, reference))
