#!/usr/bin/env python3
"""
Implements scripts build code lens spine attestation for the public Plectis package.

Callers enter through `build_attestation` and `main`; dependencies include `argparse`,
`json`, `pathlib`, and `typing`. Importing it does not authorize release work or hidden
private-state access; those effects live behind explicit calls.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_snapshot(path: Path) -> dict[str, Any]:
    """
    Load load snapshot for `scripts.build_code_lens_spine_attestation`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    if not path.is_file():
        raise SystemExit(f"2: snapshot not found: {path}")
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise SystemExit(f"2: snapshot unparseable: {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"2: snapshot is not a JSON object: {path}")
    return data


def _coverage(snapshot: dict[str, Any]) -> dict[str, Any]:
    """
    Return coverage for the scripts build code lens spine attestation flow.

    Inputs are `snapshot`; notable helpers are `get`.
    """
    cov = snapshot.get("self_description_coverage")
    return cov if isinstance(cov, dict) else {}


def _source_bodies_exported(snapshot: dict[str, Any]) -> bool:
    """
    Return whether source bodies exported holds for the scripts build code lens spine
    attestation flow.

    The result is derived from `snapshot` with `get`; failing evidence is returned or raised
    exactly where the body says so.
    """
    queue = snapshot.get("authoring_queue")
    rows = queue.get("queue_rows", []) if isinstance(queue, dict) else []
    return any(bool(r.get("source_bodies_exported")) for r in rows if isinstance(r, dict))


def _band_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, int]]:
    """
    Derive band delta without touching module import state.

    Inputs are `before` and `after`; notable helpers are `get`.
    """
    b = before.get("quality_band_counts", {}) or {}
    a = after.get("quality_band_counts", {}) or {}
    tiers = sorted(set(b) | set(a))
    return {t: {"before": int(b.get(t, 0)), "after": int(a.get(t, 0)), "delta": int(a.get(t, 0)) - int(b.get(t, 0))} for t in tiers}


def build_attestation(
    before: dict[str, Any],
    after: dict[str, Any],
    head_before: str,
    head_after: str,
    touched_paths: list[str],
    proof_commands: list[str],
) -> dict[str, Any]:
    """
    Serialize the local value into the scripts build code lens spine attestation payload
    shape.

    The returned mapping uses the key names consumed by downstream receipts, cards, or
    tests.
    """
    if _source_bodies_exported(before) or _source_bodies_exported(after):
        raise SystemExit("3: refusing to attest — a snapshot reports source_bodies_exported=true")
    cb, ca = _coverage(before), _coverage(after)
    queue_before = (before.get("authoring_queue", {}) or {}).get("by_batch_counts", {})
    queue_after = (after.get("authoring_queue", {}) or {}).get("by_batch_counts", {})
    return {
        "schema_version": "microcosm_code_lens_spine_attestation_v1",
        "subject": {
            "repo": "microcosm-substrate",
            "head_before": head_before,
            "head_after": head_after,
            "touched_paths": sorted(touched_paths),
            "touched_path_count": len(touched_paths),
        },
        "predicate": {
            "queue_by_batch_before": queue_before,
            "queue_by_batch_after": queue_after,
            "real_coverage_ratio_before": cb.get("real_coverage_ratio"),
            "real_coverage_ratio_after": ca.get("real_coverage_ratio"),
            "release_critical_coverage_before": (cb.get("release_critical_coverage", {}) or {}).get("ratio"),
            "release_critical_coverage_after": (ca.get("release_critical_coverage", {}) or {}).get("ratio"),
            "quality_band_delta": _band_delta(cb, ca),
            "custody_classification_after": (after.get("authoring_queue", {}) or {}).get("custody_classification"),
            "specificity_v3_after": ca.get("specificity_v3"),
            "source_bodies_exported": False,
            "proof_commands": proof_commands,
        },
        "authority_ceiling": {
            "release_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_body_export_authorized": False,
            "private_root_equivalence_authorized": False,
            "whole_system_correctness_authorized": False,
        },
        "non_goals": [
            "not release approval",
            "not source-body export",
            "not static-analysis correctness",
            "not whole-system correctness",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """
    Run `scripts.build_code_lens_spine_attestation` as a command-line entry point.

    The command parses argv, calls this module's builders or validators, and returns the
    status code used by the process wrapper.
    """
    parser = argparse.ArgumentParser(description="Build the code-lens release-spine attestation receipt.")
    parser.add_argument("--before", required=True, type=Path, help="python-lens --full snapshot before the wave")
    parser.add_argument("--after", required=True, type=Path, help="python-lens --full snapshot after the wave")
    parser.add_argument("--head-before", required=True)
    parser.add_argument("--head-after", required=True)
    parser.add_argument("--touched-paths", required=True, type=Path, help="newline-delimited list of touched paths")
    parser.add_argument("--proof-command", action="append", default=[], help="repeatable proof command string")
    parser.add_argument("--out", type=Path, default=Path("receipts/code_lens/code_lens_spine_attestation_v1.json"))
    args = parser.parse_args(argv)

    before = _load_snapshot(args.before)
    after = _load_snapshot(args.after)
    touched = [ln.strip() for ln in args.touched_paths.read_text().splitlines() if ln.strip()]
    attestation = build_attestation(
        before, after, args.head_before, args.head_after, touched, args.proof_command
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
