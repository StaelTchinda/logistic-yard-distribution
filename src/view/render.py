"""Rich rendering of yards, dataset summaries, scores, and comparisons."""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.models.scoring.result import EvaluationResult, EvaluationResultScore
from src.models.yard import Yard
from src.summary import ContainerSummary


def render_yard(yard: Yard, result: EvaluationResult | None = None, *, title: str = "Yard"):
    """Per-block footprint grids: each cell is the stack height at that (column, row)."""
    index = yard.slot_index()
    heights: dict[tuple[int, int, int], int] = {}
    if result is not None:
        for coord in result.container_coords:
            slot = index.get(coord)
            if slot is not None:
                key = (id(slot.block), slot.column, slot.row)
                heights[key] = heights.get(key, 0) + 1

    panels = []
    for block in yard.blocks:
        grid = Text()
        for row in range(block.rows_count - 1, -1, -1):  # row 0 at the bottom
            for col in range(block.columns_count):
                height = heights.get((id(block), col, row), 0)
                if height == 0:
                    grid.append("·", style="grey37")
                else:
                    full = height >= block.layers_count
                    glyph = str(height) if height < 10 else "+"
                    grid.append(glyph, style="bold yellow" if full else "green")
            grid.append("\n")
        filled = sum(v for (bid, _, _), v in heights.items() if bid == id(block))
        grid.append(f"{filled}/{block.get_stock_capacity()} slots", style="dim")
        panels.append(Panel(grid, title=block.name, expand=False))

    legend = Text("· empty   digit = stack height   + = 10+", style="dim")
    return Group(Text(title, style="bold"), legend, Columns(panels))


def render_summary(summary: ContainerSummary):
    table = Table(title=f"Dataset summary — {summary.total} containers")
    table.add_column("attribute")
    table.add_column("breakdown")

    def fmt(counts: dict) -> str:
        return ", ".join(f"{k}={v}" for k, v in counts.items())

    table.add_row("type", fmt(summary.by_type))
    table.add_row("size", fmt(summary.by_size))
    table.add_row("status", fmt(summary.by_status))
    table.add_row("weight", fmt(summary.by_weight))
    table.add_row("direction", fmt(summary.by_direction))
    table.add_row("service", fmt(summary.by_service))
    table.add_row("outbound group", fmt(summary.by_outbound_group))
    return table


def render_score(score: EvaluationResultScore, *, title: str = "Score"):
    table = Table(title=title)
    table.add_column("metric")
    table.add_column("value", justify="right")
    table.add_row("rehandles", str(score.rehandles_count))
    table.add_row("transport distance", f"{score.transport_distance:.0f}")
    table.add_row("manual sort effort", str(score.manual_sort_effort))
    table.add_row("unplaced", str(score.unplaced_count))
    table.add_row("[bold]TOTAL (lower = better)[/bold]", f"[bold]{score.get_score()}[/bold]")
    return table


def render_report(results: list[tuple[object, EvaluationResult]]):
    table = Table(title="Strategy comparison (lower score = better)")
    table.add_column("strategy")
    for col in ("rehandles", "distance", "sort", "unplaced", "TOTAL"):
        table.add_column(col, justify="right")
    best = min((r.score.get_score() for _, r in results), default=None)
    for strategy, result in results:
        sc = result.score
        total = sc.get_score()
        name = f"{strategy.name} ★" if total == best else strategy.name
        table.add_row(
            name, str(sc.rehandles_count), f"{sc.transport_distance:.0f}",
            str(sc.manual_sort_effort), str(sc.unplaced_count), str(total),
        )
    return table
