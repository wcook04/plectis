"""Delegates `python -m microcosm_core` to the Plectis CLI."""
from __future__ import annotations

from microcosm_core.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
