#!/usr/bin/env python3
"""Build the code-lens release-spine attestation receipt.

- Teleology: turn a code-lens population wave into a verifiable, provenance-bearing
  proof receipt (subject + predicate + authority ceiling), so a public reader can
  confirm what became self-describing, by how much, and under what bounds without
  re-running the campaign.
- Guarantee: given two ``python-lens --full`` snapshots and git refs, writes a
  ``microcosm_code_lens_spine_attestation_v1`` JSON whose predicate carries the
  queue/coverage/quality-band deltas, the source-body-export safety assertion, the
  custody-basis summary, the proof commands, and an explicit non-authorizing ceiling.
- Fails: raises SystemExit(2) if a snapshot path is missing/unparseable; raises
  SystemExit(3) if either snapshot reports source_bodies_exported=true (refuses to
  attest a leaky run).
- Reads: the --before / --after lens snapshot JSON files and the --touched-paths file.
- Writes: the --out receipt (default receipts/code_lens/code_lens_spine_attestation_v1.json).
- Non-goal: does not authorize release, publication, provider calls, source-body
  export, private-root equivalence, or whole-system correctness; it only attests a
  bounded code-lens coverage delta.
- When-needed: run after a release-spine closure/population wave has landed, to emit
  its proof receipt.
- Escalates-to: microcosm-substrate/src/microcosm_core/project_substrate.py
  (self_description_coverage / authoring_queue) for the underlying read model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_snapshot(path: Path) -> dict[str, Any]:
    """Parse a python-lens --full snapshot JSON into a dict.

    - Teleology: provide the single, validated entry point for reading a lens
      snapshot so every downstream extractor works on a known-good mapping.
    - Guarantee: returns the parsed top-level object when the file exists and is
      valid JSON object.
    - Fails: SystemExit(2) when the path is missing or the body is not parseable JSON.
    - Reads: the snapshot file at ``path``.
    - Writes: None.
    - Escalates-to: the caller's --before / --after arguments.
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
    """Extract the self_description_coverage block from a snapshot.

    - Teleology: isolate the coverage read model so the predicate builder does not
      reach into snapshot internals in more than one place.
    - Guarantee: returns the ``self_description_coverage`` mapping, or an empty dict
      when absent (a snapshot that predates coverage v2).
    - Fails: never raises; a missing key yields {}.
    - Reads: the in-memory snapshot only.
    - Writes: None.
    """
    cov = snapshot.get("self_description_coverage")
    return cov if isinstance(cov, dict) else {}


def _source_bodies_exported(snapshot: dict[str, Any]) -> bool:
    """Report whether a snapshot's queue rows leak source bodies.

    - Teleology: make the source-body safety boundary a first-class, checkable
      predicate so the attestation refuses to certify a leaky run.
    - Guarantee: returns True iff any authoring-queue row sets
      source_bodies_exported=true; otherwise False (the safe case).
    - Fails: never raises; absent queue/rows are treated as not-exported (False).
    - Reads: snapshot.authoring_queue.queue_rows only.
    - Writes: None.
    - Non-goal: does not itself authorize publication; it only attests the read-model boundary.
    """
    queue = snapshot.get("authoring_queue")
    rows = queue.get("queue_rows", []) if isinstance(queue, dict) else []
    return any(bool(r.get("source_bodies_exported")) for r in rows if isinstance(r, dict))


def _band_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Compute the per-quality-tier before/after/delta table.

    - Teleology: surface the un-gameable signal — that real-coverage tiers rose
      while authored_bare did not inflate — as an explicit, auditable delta.
    - Guarantee: returns a mapping tier -> {before, after, delta} over the union of
      both snapshots' quality_band_counts keys.
    - Fails: never raises; missing tiers default to 0 on either side.
    - Reads: the two coverage blocks' quality_band_counts only.
    - Writes: None.
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
    """Assemble the attestation receipt object from before/after snapshots.

    - Teleology: compose the full subject+predicate+ceiling proof object that the
      release-spine closure wave produces, in one deterministic place.
    - Guarantee: returns a microcosm_code_lens_spine_attestation_v1 dict whose
      predicate carries queue/coverage/band deltas, the source-body assertion (false
      on both sides), the custody-basis summary, and a fully non-authorizing ceiling.
    - Fails: SystemExit(3) when either snapshot reports source_bodies_exported=true.
    - Reads: the two in-memory snapshots only.
    - Writes: None (pure assembly; the caller persists it).
    - Non-goal: does not authorize release; sets every authorization flag to false.
    - Escalates-to: _load_snapshot / _coverage / _band_delta for field provenance.
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
    """CLI entry point: read snapshots + refs, write the attestation receipt.

    - Teleology: expose attestation building as a re-runnable command so each
      closure/population wave can emit its receipt the same way.
    - Guarantee: writes the receipt JSON to --out and returns 0 on success.
    - Fails: SystemExit(2) on snapshot load errors; SystemExit(3) on a source-body
      leak; argparse exits non-zero on missing required arguments.
    - Reads: --before, --after, --touched-paths.
    - Writes: the --out receipt file (parent dirs created).
    - When-needed: invoke from the wave's proof loop after the source commit lands.
    - Escalates-to: build_attestation for the receipt shape.
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
