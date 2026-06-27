"""Scan the data/ subdirectories and present friendly menu entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class CatalogEntry:
    key: str  # filename stem — stable selector for --yard/--dataset/--strategy
    label: str
    path: Path
    kind: str  # "yard" | "containers" | "strategy"
    description: str = ""
    extra: dict = field(default_factory=dict)


def _yaml_meta(path: Path) -> tuple[str, str]:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        data = {}
    return str(data.get("name", path.stem)), str(data.get("description", ""))


def scan_yards(root: Path) -> list[CatalogEntry]:
    entries = []
    for path in sorted((root / "yards").iterdir()):
        suffix = path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            label, desc = _yaml_meta(path)
            entries.append(CatalogEntry(path.stem, label, path, "yard", desc))
        elif suffix == ".csv":
            entries.append(CatalogEntry(path.stem, path.stem, path, "yard", "CSV yard"))
    return entries


def scan_strategies(root: Path) -> list[CatalogEntry]:
    entries = []
    for path in sorted((root / "strategies").glob("*.y*ml")):
        label, desc = _yaml_meta(path)
        entries.append(CatalogEntry(path.stem, label, path, "strategy", desc))
    return entries


def scan_distributions(root: Path) -> list[CatalogEntry]:
    """Discover distribution CSVs named ``<yard>___<dataset>[___<id>].csv``.

    The ``___``-separated stem identifies which yard and dataset a distribution belongs to (and an
    optional strategy/label id); the parsed parts land in ``entry.extra`` for filtering.
    """
    entries: list[CatalogEntry] = []
    dist_dir = root / "distributions"
    if not dist_dir.is_dir():
        return entries
    for path in sorted(dist_dir.glob("*.csv")):
        parts = path.stem.split("___")
        yard = parts[0] if len(parts) >= 1 else ""
        dataset = parts[1] if len(parts) >= 2 else ""
        ident = parts[2] if len(parts) >= 3 else ""
        description = " / ".join(p for p in (yard, dataset, ident) if p)
        entries.append(
            CatalogEntry(
                path.stem,
                ident or "(base)",
                path,
                "distribution",
                description,
                {"yard": yard, "dataset": dataset, "strategy": ident},
            )
        )
    return entries


def scan_containers(root: Path) -> list[CatalogEntry]:
    entries = []
    for path in sorted((root / "containers").glob("*.csv")):
        rows = max(0, sum(1 for _ in path.open()) - 1)  # minus header
        entries.append(
            CatalogEntry(
                path.stem, path.stem, path, "containers",
                f"{rows} containers", {"rows": rows},
            )
        )
    return entries


def find(entries: list[CatalogEntry], key: str) -> CatalogEntry | None:
    return next((entry for entry in entries if entry.key == key), None)
