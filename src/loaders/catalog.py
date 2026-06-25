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
