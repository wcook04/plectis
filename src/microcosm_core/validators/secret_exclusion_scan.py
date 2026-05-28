from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from microcosm_core.receipts import base_receipt, write_receipt
from microcosm_core.secret_exclusion_scan import PASS, load_forbidden_classes, scan_paths


SKIP_DIRS = {
    ".git",
    ".microcosm",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "microcosm-substrate",
    "node_modules",
}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo"}


def _is_local_residue(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts = rel.parts
    return (
        any(part in SKIP_DIRS for part in parts)
        or any(part.endswith(".egg-info") for part in parts)
        or path.suffix in SKIP_FILE_SUFFIXES
        or path.name == ".DS_Store"
    )


def _iter_scan_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _is_local_residue(current / dirname, root)
        ]
        for filename in filenames:
            path = current / filename
            if not _is_local_residue(path, root):
                paths.append(path)
    return paths


def validate_scan(root: str | Path, policy: str | Path | None = None) -> dict[str, Any]:
    root_path = Path(root)
    policy_path = (
        Path(policy)
        if policy is not None
        else root_path / "core/private_state_forbidden_classes.json"
    )
    forbidden_classes = load_forbidden_classes(policy_path)
    scan = scan_paths(
        _iter_scan_paths(root_path),
        forbidden_classes=forbidden_classes,
        display_root=root_path,
    )
    receipt = base_receipt("secret_exclusion_scan", "first_wave")
    receipt.update(
        {
            "status": PASS if scan["status"] == PASS else scan["status"],
            "secret_exclusion_scan": scan,
            "receipt_paths": ["receipts/first_wave/secret_exclusion_scan.json"],
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
