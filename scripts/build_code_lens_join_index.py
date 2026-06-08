#!/usr/bin/env python3
"""Build the code-lens join index: a source-body-free semantic property graph.

The join index is the intermediate representation the Comprehension Plane queries.
It joins what python-lens knows about source symbols (atom coverage, specificity_v3
bands, source class) to what the organ registry knows about organs (runner module,
governing validator command, generated receipts, evidence class, authority ceiling).
It is a semantic/provenance/navigation graph -- NOT a static-analysis control-flow
or data-flow graph -- and it never exports docstring prose or source bodies.

- Teleology: turn the populated code-lens atoms + specificity scores + organ
  registry into a typed node/edge graph a cold agent can query by organ instead
  of rereading the repo.
- Guarantee: given a python-lens --full snapshot and core/organ_registry.json,
  writes a microcosm_code_lens_join_index_v0 JSON of organ + source_file nodes,
  implemented_by_runner / emits_receipt edges, per-organ + per-file specificity
  rollups, and a non-authorizing ceiling; source_bodies_exported is always false.
- Fails: SystemExit(2) when a required input is missing/unparseable; SystemExit(3)
  if the lens snapshot reports any source-body export (refuses to join a leaky run).
- Reads: the --lens snapshot and the --registry organ registry.
- Writes: the --out join index (default receipts/code_lens/code_lens_join_index_v0.json).
- Non-goal: does not authorize release, source-body export, static-analysis
  correctness, or whole-system correctness; it is a navigation read-model only.
- When-needed: run after python-lens/specificity_v3 to refresh the comprehension IR.
- Escalates-to: project_substrate.py (python-lens) and core/organ_registry.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

COUPLING_ZONE_MARKERS = ("/organs/", "/macro_tools/", "/engine_room/")


def _load_json(path: Path, label: str) -> Any:
    """Parse a required JSON input or stop with a typed error.

    - Teleology: the one validated reader for the builder's two inputs.
    - Guarantee: returns the parsed JSON value when the file exists and parses.
    - Fails: SystemExit(2) when the path is missing or the body is not JSON.
    - Reads: the file at ``path``.
    - Writes: None.
    """
    if not path.is_file():
        raise SystemExit(f"2: {label} not found: {path}")
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise SystemExit(f"2: {label} unparseable: {path}: {exc}")


def _capsule_rows(lens: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the symbol capsule rows from a python-lens snapshot.

    - Teleology: isolate the one snapshot field the join index consumes.
    - Guarantee: returns the list at ``symbol_capsule_rows`` or [] when absent.
    - Fails: never raises; a non-list value yields [].
    - Reads: the in-memory snapshot only.
    """
    rows = lens.get("symbol_capsule_rows")
    return rows if isinstance(rows, list) else []


def _custody_basis(path: str) -> str:
    """Classify a source file's custody basis from its path.

    - Teleology: tell a reader whether an organ's runner code is owned or an
      exact-copy macro body (which must not be authored locally).
    - Guarantee: returns "directory_coupling_marker" for organs/macro_tools/
      engine_room exact-copy zones, else "owned".
    - Fails: never raises (substring test).
    - Reads: only the supplied path string.
    """
    return (
        "directory_coupling_marker"
        if any(marker in path for marker in COUPLING_ZONE_MARKERS)
        else "owned"
    )


def _file_rollups(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate capsule rows into per-source-file specificity rollups.

    - Teleology: compress the flat capsule list into one node per source file
      carrying its atom coverage and specificity bands.
    - Guarantee: returns path -> {source_class, custody_basis, symbol_count,
      real_coverage, body_specific, generic_unique, has_non_goal}; counts only,
      no prose.
    - Fails: never raises; rows missing fields default to zero/empty.
    - Reads: the in-memory capsule rows only.
    """
    files: dict[str, dict[str, Any]] = {}
    for row in rows:
        path = str(row.get("path") or "")
        if not path:
            continue
        bucket = files.setdefault(
            path,
            {
                "source_class": row.get("source_class"),
                "custody_basis": _custody_basis(path),
                "symbol_count": 0,
                "real_coverage": 0,
                "body_specific": 0,
                "generic_unique": 0,
                "has_non_goal": 0,
            },
        )
        bucket["symbol_count"] += 1
        if row.get("is_real_coverage"):
            bucket["real_coverage"] += 1
            specificity = row.get("atom_specificity")
            if specificity == "body_specific":
                bucket["body_specific"] += 1
            elif specificity == "generic_unique":
                bucket["generic_unique"] += 1
            if row.get("atom_has_non_goal"):
                bucket["has_non_goal"] += 1
    return files


def _runner_source_ref(runner: str | None) -> str | None:
    """Resolve an organ runner's dotted module to a repo-relative source path.

    - Teleology: bridge the organ registry's dotted runner to the file the lens
      indexes, so organs can be joined to their code.
    - Guarantee: returns "src/<dotted/with/slashes>.py" for a microcosm_core.*
      runner; None when the runner is empty or not a microcosm_core module.
    - Fails: never raises (string shaping only).
    - Reads: only the supplied runner string.
    """
    if not runner or not runner.startswith("microcosm_core."):
        return None
    return "src/" + runner.replace(".", "/") + ".py"


def build_join_index(
    lens: dict[str, Any], registry: dict[str, Any]
) -> dict[str, Any]:
    """Assemble the join index from a lens snapshot and the organ registry.

    - Teleology: the composition root that turns code-lens + organ registry into
      the Comprehension Plane's queryable IR.
    - Guarantee: returns a microcosm_code_lens_join_index_v0 dict with organ and
      source_file nodes, implemented_by_runner/emits_receipt edges, rollups, and a
      non-authorizing ceiling; export_band is presence_only and
      source_bodies_exported is False.
    - Fails: SystemExit(3) if the lens snapshot reports a source-body export.
    - Reads: the two in-memory inputs only.
    - Non-goal: does not authorize release or source-body export; navigation only.
    - Escalates-to: _file_rollups / _runner_source_ref for field provenance.
    """
    boundary = lens.get("payload_boundary", {})
    if isinstance(boundary, dict) and boundary.get("source_bodies_exported"):
        raise SystemExit("3: refusing to join a lens snapshot that exports source bodies")
    files = _file_rollups(_capsule_rows(lens))
    organs = registry.get("implemented_organs", [])
    organ_nodes: list[dict[str, Any]] = []
    source_file_paths: set[str] = set()
    edges: list[dict[str, Any]] = []
    resolved = 0
    for organ in organs:
        if not isinstance(organ, dict):
            continue
        organ_id = str(organ.get("organ_id") or "")
        runner = organ.get("runner")
        runner_ref = _runner_source_ref(runner)
        file_roll = files.get(runner_ref) if runner_ref else None
        if file_roll is not None:
            resolved += 1
            source_file_paths.add(runner_ref)
            edges.append(
                {
                    "from_type": "organ",
                    "from": organ_id,
                    "to_type": "source_file",
                    "to": runner_ref,
                    "kind": "implemented_by_runner",
                }
            )
        receipts = organ.get("generated_receipts") or []
        for receipt in receipts:
            edges.append(
                {
                    "from_type": "organ",
                    "from": organ_id,
                    "to_type": "receipt",
                    "to": str(receipt),
                    "kind": "emits_receipt",
                }
            )
        organ_nodes.append(
            {
                "organ_id": organ_id,
                "evidence_class": organ.get("evidence_class"),
                "evidence_strength_rank": organ.get("evidence_strength_rank"),
                "truth_accounting_bucket": organ.get("truth_accounting_bucket"),
                "real_substrate_disposition": organ.get("real_substrate_disposition"),
                "claim_ceiling": organ.get("claim_ceiling"),
                "status": organ.get("status"),
                "runner_module": runner,
                "runner_source_ref": runner_ref,
                "runner_source_resolved": file_roll is not None,
                "runner_custody_basis": (file_roll or {}).get("custody_basis"),
                "runner_specificity": (
                    {
                        "real_coverage": file_roll.get("real_coverage", 0),
                        "body_specific": file_roll.get("body_specific", 0),
                        "generic_unique": file_roll.get("generic_unique", 0),
                    }
                    if file_roll
                    else None
                ),
                "validator_command": organ.get("validator_command"),
                "receipt_count": len(receipts),
                "authority_receipt": organ.get("current_authority_receipt"),
            }
        )
    source_file_nodes = [
        {"path": path, **files[path]} for path in sorted(source_file_paths)
    ]
    custody_split: dict[str, int] = {}
    for node in source_file_nodes:
        basis = str(node.get("custody_basis") or "unknown")
        custody_split[basis] = custody_split.get(basis, 0) + 1
    return {
        "schema_version": "microcosm_code_lens_join_index_v0",
        "export_band": "presence_only",
        "source_bodies_exported": False,
        "generated_from": {
            "python_lens": "python-lens --full symbol_capsule_rows + specificity_v3",
            "organ_registry": "core/organ_registry.json::implemented_organs",
        },
        "nodes": {
            "organ": organ_nodes,
            "source_file": source_file_nodes,
        },
        "edges": edges,
        "rollup": {
            "organ_count": len(organ_nodes),
            "organs_with_resolved_runner_source": resolved,
            "source_file_node_count": len(source_file_nodes),
            "edge_count": len(edges),
            "runner_custody_split": custody_split,
        },
        "authority_ceiling": {
            "release_authorized": False,
            "source_body_export_authorized": False,
            "static_analysis_authority": False,
            "whole_system_correctness_authorized": False,
        },
        "non_goals": [
            "not a control-flow / data-flow graph",
            "not source-body export",
            "not release approval",
            "not whole-system correctness",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: read a lens snapshot + organ registry, write the join index.

    - Teleology: expose join-index building as a re-runnable command for the
      Comprehension Plane refresh.
    - Guarantee: writes the join index JSON to --out and returns 0 on success.
    - Fails: SystemExit(2) on input load errors; SystemExit(3) on a source-body
      leak; argparse exits non-zero on missing required arguments.
    - Reads: --lens, --registry.
    - Writes: the --out join index (parent dirs created).
    - Escalates-to: build_join_index for the graph shape.
    """
    parser = argparse.ArgumentParser(description="Build the code-lens join index v0.")
    parser.add_argument("--lens", required=True, type=Path, help="python-lens --full snapshot JSON")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("core/organ_registry.json"),
        help="organ registry JSON",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("receipts/code_lens/code_lens_join_index_v0.json"),
    )
    args = parser.parse_args(argv)
    lens = _load_json(args.lens, "lens snapshot")
    registry = _load_json(args.registry, "organ registry")
    if not isinstance(lens, dict) or not isinstance(registry, dict):
        raise SystemExit("2: lens and registry must both be JSON objects")
    index = build_join_index(lens, registry)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    print(
        f"wrote {args.out}: {index['rollup']['organ_count']} organs, "
        f"{index['rollup']['organs_with_resolved_runner_source']} runner-resolved, "
        f"{index['rollup']['edge_count']} edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
