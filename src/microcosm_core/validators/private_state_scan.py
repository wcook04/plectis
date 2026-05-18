from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import base_receipt, write_receipt


SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv"}


def _iter_scan_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            paths.append(path)
    return paths


def validate_scan(root: str | Path, policy: str | Path | None = None) -> dict[str, Any]:
    root_path = Path(root)
    policy_path = Path(policy) if policy is not None else root_path / "core/private_state_forbidden_classes.json"
    forbidden_classes = load_forbidden_classes(policy_path)
    scan = scan_paths(_iter_scan_paths(root_path), forbidden_classes=forbidden_classes)
    receipt = base_receipt("private_state_scan", "first_wave")
    receipt.update(
        {
            "status": PASS if scan["status"] == PASS else scan["status"],
            "private_state_scan": scan,
            "receipt_paths": ["receipts/first_wave/private_state_scan.json"],
        }
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy")
    args = parser.parse_args(argv)

    receipt = validate_scan(args.root, args.policy)
    write_receipt(args.out, receipt)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
