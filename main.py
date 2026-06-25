"""Entry point for the yard distribution app.

    python main.py                 # interactive dialogue
    python main.py --list          # list yards / datasets / strategies
    python main.py --run --yard main --dataset mixed --strategy quay_proximity --view
    python main.py --compare --yard main --dataset mixed
"""

import sys
from pathlib import Path

# Put the repo root on sys.path so `import src...` resolves when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
