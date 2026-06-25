"""Rich rendering of yards, dataset summaries, scores, and comparisons."""

from __future__ import annotations

import os
import time

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from src.models.scoring.result import EvaluationResult, EvaluationResultScore
from src.models.yard import Yard
from src.summary import ContainerSummary

_BG_BLUE = "#6f93c4"  # the yard ground / driving lanes
_OLIVE = "#a7a13c"  # a block (empty)
_GREEN = "#4c9d4c"  # a block (full)

# How dark a completely full block gets: 1.0 keeps full brightness, lower = darker.
_FULL_DIM = 0.45


def _block_color(ratio: float) -> str:
    """Empty -> full: shift olive to green, then darken as it fills.

    The hue moves olive (empty) -> green, and brightness scales down from 1.0
    toward ``_FULL_DIM`` so a fuller block reads as a deeper, darker green."""
    ratio = max(0.0, min(1.0, ratio))
    a = (0xA7, 0xA1, 0x3C)
    b = (0x4C, 0x9D, 0x4C)
    dim = 1.0 - (1.0 - _FULL_DIM) * ratio
    rgb = tuple(round((a[i] + (b[i] - a[i]) * ratio) * dim) for i in range(3))
    return "#%02x%02x%02x" % rgb


def _short(text: str, width: int) -> str:
    """Fit a label into ``width`` chars: full name, else its last token, else truncated."""
    if len(text) <= width:
        return text
    token = text.split()[-1] if text.split() else text  # "Block 12" -> "12"
    if len(token) <= width:
        return token
    return text[:width]


def render_yard(
    yard: Yard,
    result: EvaluationResult | None = None,
    *,
    title: str = "Yard",
    max_width: int | None = None,
):
    """A top-down site plan: each block is a rectangle placed by its real (x, y) coords on
    the yard ground. With a result, blocks shade olive->green by fill and show a count."""
    blocks = yard.blocks
    if not blocks:
        return Panel(Text("(empty yard)"), title=title, border_style="#2b3a55")

    if max_width is None:
        max_width = max(40, Console().size.width - 4)

    min_x = min(b.bottom_left_corner.x for b in blocks)
    max_x = max(b.bottom_left_corner.x + b.columns_count for b in blocks)
    min_y = min(b.bottom_left_corner.y for b in blocks)
    max_y = max(b.bottom_left_corner.y + b.rows_count for b in blocks)
    span_x = max(1, max_x - min_x)
    span_y = max(1, max_y - min_y)

    width = min(max_width, max(span_x, 40))
    # halve the vertical scale because terminal cells are ~twice as tall as wide
    height = max(6, min(34, round(width * span_y / span_x / 2)))
    sx = width / span_x
    sy = height / span_y

    char = [[" "] * width for _ in range(height)]
    bg = [[_BG_BLUE] * width for _ in range(height)]
    fg: list[list[str | None]] = [[None] * width for _ in range(height)]

    fills: dict[int, int] = {}
    if result is not None:
        index = yard.slot_index()
        for coord in result.container_coords:
            slot = index.get(coord)
            if slot is not None:
                fills[id(slot.block)] = fills.get(id(slot.block), 0) + 1

    def to_col(x: int) -> int:
        return max(0, min(width, round((x - min_x) * sx)))

    def to_row(y: int) -> int:  # y grows upward -> small row index
        return max(0, min(height, round((max_y - y) * sy)))

    for block in blocks:
        x0 = block.bottom_left_corner.x
        y0 = block.bottom_left_corner.y
        c0, c1 = to_col(x0), max(to_col(x0 + block.columns_count), to_col(x0) + 1)
        r0, r1 = to_row(y0 + block.rows_count), max(to_row(y0), to_row(y0 + block.rows_count) + 1)
        c1, r1 = min(c1, width), min(r1, height)

        if result is not None:
            cap = block.get_stock_capacity()
            color = _block_color(fills.get(id(block), 0) / cap if cap else 0.0)
        else:
            color = _OLIVE
        for r in range(r0, r1):
            for c in range(c0, c1):
                bg[r][c] = color

        cell_w = c1 - c0
        lines = [block.name]
        if result is not None and (r1 - r0) >= 2:
            lines.append(f"{fills.get(id(block), 0)}/{block.get_stock_capacity()}")
        top = r0 + max(0, (r1 - r0 - len(lines)) // 2)
        for li, raw in enumerate(lines):
            rr = top + li
            if not (r0 <= rr < r1):
                continue
            label = _short(raw, cell_w)
            start = c0 + max(0, (cell_w - len(label)) // 2)
            for i, ch in enumerate(label):
                cc = start + i
                if c0 <= cc < c1:
                    char[rr][cc] = ch
                    fg[rr][cc] = "white"

    body = Text()
    for r in range(height):
        for c in range(width):
            body.append(char[r][c], style=Style(color=fg[r][c], bgcolor=bg[r][c]))
        if r != height - 1:
            body.append("\n")

    panel = Panel(body, title=title, border_style="#2b3a55", expand=False)
    if result is None:
        return panel
    legend = Text("olive = empty   →   dark green = full", style="dim")
    return Group(panel, legend)


class _PartialResult:
    """A stand-in for ``EvaluationResult`` that exposes only the first ``n`` placements,
    which is all ``render_yard`` reads. Lets us replay a fill frame-by-frame for free."""

    def __init__(self, full: EvaluationResult, n: int):
        self._full = full
        self.container_coords = full.container_coords[:n]


# Animation defaults, overridable per call or via env vars (env wins only when the
# caller doesn't pass an explicit value). The frame cap is what keeps an 8k-container
# fill fast: we draw at most this many frames no matter how many containers there are.
_ANIM_FPS = 24.0  # YARD_ANIM_FPS
_ANIM_MAX_FRAMES = 60  # YARD_ANIM_FRAMES — cap on total frames (0 / "none" = uncapped)


def _env_float(name: str, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    if raw.strip().lower() in ("none", "off", "0"):
        return 0
    try:
        return int(float(raw))
    except ValueError:
        return default


def animate_fill(
    yard: Yard,
    result: EvaluationResult,
    *,
    title: str = "Filling yard",
    fps: float | None = None,
    step: int | None = None,
    max_frames: int | None = None,
    console: Console | None = None,
):
    """Animate the yard filling up, revealing one batch of containers per frame.

    Containers in ``result`` are stored in placement order, so revealing them
    progressively replays exactly how the chosen strategy filled the yard. The final
    frame is the same picture ``render_yard(yard, result)`` would draw.

    Speed is bounded by frame *count*, not container count: for a big fill we batch
    many containers into each of at most ``max_frames`` frames, so 8k containers
    animates as fast as 80. Tunables (explicit arg wins, else env var, else default):

    * ``fps`` / ``YARD_ANIM_FPS`` — frames per second.
    * ``max_frames`` / ``YARD_ANIM_FRAMES`` — cap on total frames (0 = uncapped).
    * ``step`` / ``YARD_ANIM_STEP`` — containers revealed per frame; overrides the
      cap when set (use 1 for the old one-per-frame behaviour).
    """
    console = console or Console()
    total = len(result.container_coords)

    fps = _env_float("YARD_ANIM_FPS", _ANIM_FPS) if fps is None else fps
    max_frames = (
        _env_int("YARD_ANIM_FRAMES", _ANIM_MAX_FRAMES) if max_frames is None else max_frames
    )
    if step is None:
        step = _env_int("YARD_ANIM_STEP", 0)  # 0 -> derive from the frame cap

    # Pick a step so we draw at most ``max_frames`` frames, unless step was forced.
    if step <= 0:
        step = 1 if max_frames <= 0 else max(1, -(-total // max_frames))  # ceil div

    delay = 1.0 / fps if fps and fps > 0 else 0.0

    # frame counts: 0 (empty), step, 2*step, ..., total
    counts = list(range(0, total, step))
    if not counts or counts[-1] != total:
        counts.append(total)

    def frame(n: int):
        partial = _PartialResult(result, n)
        return render_yard(yard, partial, title=f"{title} — {n}/{total}")

    with Live(
        frame(0), console=console, refresh_per_second=max(1.0, fps), transient=False
    ) as live:
        for n in counts:
            live.update(frame(n))
            if delay and n != total:
                time.sleep(delay)
    return result


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
