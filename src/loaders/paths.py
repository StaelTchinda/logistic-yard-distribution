"""Locate the editable ``data/`` directory at runtime."""

from __future__ import annotations

import os
from pathlib import Path


def data_root(override: str | os.PathLike[str] | None = None) -> Path:
    """First existing of: ``override``, ``$YARD_DATA_DIR``, repo-root ``data/``, ``./data``."""
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    env = os.environ.get("YARD_DATA_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(Path(__file__).resolve().parents[2] / "data")  # src/loaders/ -> root
    candidates.append(Path.cwd() / "data")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "data/ directory not found; searched: "
        + ", ".join(str(c) for c in candidates)
    )
