from __future__ import annotations

import argparse
from collections.abc import Iterator
import os
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import base_receipt, write_receipt


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
    """Classify a path as local build/tooling residue that the scan must skip.

    - Teleology: protects the private-state scan's signal from being diluted by build/VCS noise, keeping the public-safety verdict focused on real source under `root`.
    - Guarantee: returns True iff any path part is in SKIP_DIRS, any part ends with `.egg-info`, the suffix is in SKIP_FILE_SUFFIXES (`.pyc`/`.pyo`), or the basename is `.DS_Store`; otherwise False (path computed relative to `root`, falling back to the absolute path on ValueError).
    - Fails: None (pure boolean predicate; relative_to ValueError is caught and the unrelativized path is classified instead).
    - Reads: SKIP_DIRS / SKIP_FILE_SUFFIXES module constants and the path components only.
    - Writes: None
    - When-needed: inspect when deciding why a file was or was not included in the private-state scan walk.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
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


def _iter_scan_paths(root: Path) -> Iterator[Path]:
    """Yield every non-residue path under `root` for the private-state scan.

    - Teleology: protects the completeness of the public-safety scan corpus, ensuring no real source file is silently dropped while build/VCS residue is pruned.
    - Guarantee: walks `root` via os.walk, prunes dirnames where `_is_local_residue` is True, and yields each remaining file path that is not `_is_local_residue`; emits paths only, never file contents.
    - Fails: None (generator; os.walk over a missing/empty `root` simply yields nothing rather than raising).
    - Reads: filesystem tree under `root` (directory/file names only at this stage).
    - Writes: None
    - When-needed: inspect to reproduce exactly which files `validate_scan` fed to the scanner.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
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
                yield path


def validate_scan(root: str | Path, policy: str | Path | None = None) -> dict[str, Any]:
    """Scan `root` for forbidden private-state classes and build a verdict receipt.

    - Teleology: protects the public-safe claim that exported substrate carries no forbidden private-state material, guarding against leaking declared private classes into a public export.
    - Guarantee: returns a `base_receipt("private_state_scan", "first_wave")` dict whose `status` mirrors `scan["status"]` (PASS only when the scan found no blocking hit) and carries the full `private_state_scan` findings plus `receipt_paths`.
    - Fails: missing/non-JSON policy -> `load_forbidden_classes` raises (read_json_strict error / ValueError "policy must be a JSON object"); forbidden material in a scanned file -> receipt `status` is a non-PASS `blocked_*` code (e.g. blocked_private_state / blocked_public_write_attempt / blocked_case_review_required).
    - Reads: `<root>/core/private_state_forbidden_classes.json` policy (or explicit `policy`) and every non-residue file under `root`.
    - Writes: None (returns receipt in-memory; persistence is the caller's job).
    - When-needed: trust before treating `root` as a clean public export; inspect the `private_state_scan` hits when status is non-PASS.
    - Escalates-to: `microcosm_core.private_state_scan.scan_paths` (status derivation) and `receipts/first_wave/private_state_scan.json`.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness; it is not a complete secret scan and does not certify absence of secrets.
    """
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
    """CLI entrypoint: run the private-state scan and persist its receipt.

    - Teleology: protects the private-state-scan gate as a runnable check, turning the scan verdict into a persisted receipt and a process exit code for CI/release tooling.
    - Guarantee: parses required `--root`/`--out` (optional `--policy`), calls `validate_scan`, writes the receipt to `--out` via `write_receipt`, and returns 0 iff `receipt["status"] == PASS` else 1.
    - Fails: missing required `--root`/`--out` -> argparse SystemExit(2); bad/non-JSON policy -> propagates `load_forbidden_classes` error; forbidden material found -> returns exit code 1 (non-PASS status persisted to the receipt).
    - Reads: CLI argv, the forbidden-class policy, and files under `--root`.
    - Writes: `--out` receipt JSON (via `write_receipt`).
    - When-needed: invoke as the release/CI private-state gate; trust the exit code as the pass/block signal.
    - Escalates-to: `validate_scan` (verdict) and the `--out` receipt file.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness; exit 0 means no forbidden-class hit, not certified secret-free.
    """
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
