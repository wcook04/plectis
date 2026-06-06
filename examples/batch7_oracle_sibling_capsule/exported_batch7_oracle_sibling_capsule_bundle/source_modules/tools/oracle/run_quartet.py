"""
[PURPOSE]
- Teleology: Provide a bounded operator surface for repairing the canonical Oracle quartet that Evolve consumes.
- Mechanism: Inspect canonical artifacts and legacy source-node outputs, optionally materialize safe aliases, and optionally resume the Oracle engine at the missing quartet target.

[INTERFACE]
- CLI: `--subject-run <path-or-id> --truth-run <path-or-id> --plan|--materialize-aliases|--run-missing`.
- Outputs: JSON repair plan or run receipt.
- Exports: build_quartet_repair_plan, materialize_missing_aliases, run_missing_quartet.

[CONSTRAINTS]
- `--plan` and `--materialize-aliases` are deterministic local filesystem operations.
- `--run-missing` may invoke bridge-backed Oracle reasoning through GodModeEngine; keep it explicit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

QUARTET = [
    {
        "canonical_artifact_id": "prediction_reconciliation",
        "source_node_id": "oracle_truth_diff_equity",
        "runner_target_id": "oracle_truth_diff_equity",
    },
    {
        "canonical_artifact_id": "realized_hindsight_brief",
        "source_node_id": "oracle_truth_map",
        "runner_target_id": "oracle_truth_map",
    },
    {
        "canonical_artifact_id": "cp2_critique",
        "source_node_id": "oracle_attribution_map",
        "runner_target_id": "oracle_attribution_map",
    },
    {
        "canonical_artifact_id": "ideal_cp2",
        "source_node_id": "oracle_cp2_emitter",
        "runner_target_id": "oracle_cp2_emitter",
    },
]


def _resolve_run_dir(token: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    raw = Path(str(token))
    candidates = [
        raw,
        repo_root / raw,
        repo_root / "state" / "runs" / str(token),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"run directory does not exist: {token}")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def build_quartet_repair_plan(
    subject_run: str | Path,
    truth_run: str | Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> Dict[str, Any]:
    subject_run_dir = _resolve_run_dir(subject_run, repo_root=repo_root)
    truth_run_dir = _resolve_run_dir(truth_run, repo_root=repo_root)
    artifacts_dir = truth_run_dir / "artifacts"
    entries: list[dict[str, Any]] = []
    repair_actions: list[dict[str, Any]] = []
    missing_canonical: list[str] = []
    missing_source_nodes: list[str] = []
    aliasable: list[str] = []

    for spec in QUARTET:
        canonical_id = spec["canonical_artifact_id"]
        source_id = spec["source_node_id"]
        runner_target = spec["runner_target_id"]
        canonical_path = artifacts_dir / f"{canonical_id}.json"
        source_path = artifacts_dir / f"{source_id}.json"
        canonical_exists = canonical_path.exists()
        source_exists = source_path.exists()
        status = "canonical_present"
        if not canonical_exists and source_exists:
            status = "alias_source_present"
            missing_canonical.append(canonical_id)
            aliasable.append(canonical_id)
            repair_actions.append(
                {
                    "action_kind": "materialize_alias",
                    "canonical_artifact_id": canonical_id,
                    "source_node_id": source_id,
                    "command": (
                        f'./repo-python tools/oracle/run_quartet.py --subject-run "{subject_run_dir}" '
                        f'--truth-run "{truth_run_dir}" --materialize-aliases'
                    ),
                }
            )
        elif not canonical_exists:
            status = "missing_source"
            missing_canonical.append(canonical_id)
            missing_source_nodes.append(source_id)
            repair_actions.append(
                {
                    "action_kind": "run_oracle_node",
                    "canonical_artifact_id": canonical_id,
                    "source_node_id": source_id,
                    "runner_target_id": runner_target,
                    "command": (
                        f'./repo-python tools/oracle/run_quartet.py --subject-run "{subject_run_dir}" '
                        f'--truth-run "{truth_run_dir}" --run-missing --target {runner_target}'
                    ),
                }
            )

        entries.append(
            {
                "canonical_artifact_id": canonical_id,
                "source_node_id": source_id,
                "runner_target_id": runner_target,
                "status": status,
                "canonical_path": str(canonical_path),
                "source_path": str(source_path),
                "canonical_exists": canonical_exists,
                "source_exists": source_exists,
            }
        )

    deepest_missing_target = None
    if missing_source_nodes:
        source_order = [str(item["source_node_id"]) for item in QUARTET]
        deepest_missing_target = max(
            missing_source_nodes,
            key=lambda item: source_order.index(item) if item in source_order else -1,
        )

    readiness_status = "READY"
    if missing_source_nodes:
        readiness_status = "BLOCKED"
    elif missing_canonical:
        readiness_status = "DEGRADED"

    return {
        "kind": "oracle_quartet_repair_plan",
        "schema_version": "1.0",
        "subject_run_id": subject_run_dir.name,
        "truth_run_id": truth_run_dir.name,
        "readiness": {
            "status": readiness_status,
            "missing_canonical_artifacts": missing_canonical,
            "aliasable_artifacts": aliasable,
            "missing_source_nodes": missing_source_nodes,
            "deepest_missing_target": deepest_missing_target,
        },
        "artifacts": entries,
        "repair_actions": repair_actions,
    }


def materialize_missing_aliases(
    subject_run: str | Path,
    truth_run: str | Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> Dict[str, Any]:
    plan = build_quartet_repair_plan(subject_run, truth_run, repo_root=repo_root)
    truth_run_dir = _resolve_run_dir(truth_run, repo_root=repo_root)
    written: list[str] = []
    skipped: list[dict[str, Any]] = []

    for entry in plan["artifacts"]:
        if entry["status"] != "alias_source_present":
            continue
        source_path = Path(entry["source_path"])
        canonical_path = Path(entry["canonical_path"])
        payload = _read_json(source_path)
        if payload is None:
            skipped.append(
                {
                    "canonical_artifact_id": entry["canonical_artifact_id"],
                    "source_node_id": entry["source_node_id"],
                    "reason": "source artifact is unreadable",
                }
            )
            continue
        metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {})
        metadata["artifact_alias_of"] = entry["source_node_id"]
        metadata["canonical_artifact_id"] = entry["canonical_artifact_id"]
        alias_payload = {
            **payload,
            "id": entry["canonical_artifact_id"],
            "metadata": metadata,
        }
        tmp_path = canonical_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(alias_payload, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(canonical_path)
        written.append(str(canonical_path))

    return {
        "kind": "oracle_quartet_alias_materialization_receipt",
        "schema_version": "1.0",
        "subject_run_id": plan["subject_run_id"],
        "truth_run_id": truth_run_dir.name,
        "written_paths": written,
        "skipped": skipped,
        "post_plan": build_quartet_repair_plan(subject_run, truth_run, repo_root=repo_root),
    }


def run_missing_quartet(
    subject_run: str | Path,
    truth_run: str | Path,
    *,
    target: str = "oracle_cp2_emitter",
    repo_root: Path = REPO_ROOT,
) -> Dict[str, Any]:
    from system.core.engine import GodModeEngine
    from system.lib.types import ExecutionMode, RunMode

    subject_run_dir = _resolve_run_dir(subject_run, repo_root=repo_root)
    truth_run_dir = _resolve_run_dir(truth_run, repo_root=repo_root)
    valid_targets = {str(item["source_node_id"]) for item in QUARTET}
    if target not in valid_targets:
        raise ValueError(f"target must be one of {sorted(valid_targets)}")

    engine = GodModeEngine(
        run_id=truth_run_dir.name,
        run_mode=RunMode.RESUME,
        execution_mode=ExecutionMode.RUNTIME,
        subject_group="oracle",
        root_dir=str(repo_root),
        oracle_subject_run_dir=str(subject_run_dir),
        oracle_truth_run_dir=str(truth_run_dir),
    )
    engine.run(target)
    return {
        "kind": "oracle_quartet_run_receipt",
        "schema_version": "1.0",
        "subject_run_id": subject_run_dir.name,
        "truth_run_id": truth_run_dir.name,
        "target": target,
        "post_plan": build_quartet_repair_plan(subject_run_dir, truth_run_dir, repo_root=repo_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or run Oracle quartet repair for Evolve readiness.")
    parser.add_argument("--subject-run", required=True, help="Subject Lab run id or directory.")
    parser.add_argument("--truth-run", required=True, help="Oracle/truth run id or directory.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Print repair plan only.")
    mode.add_argument("--materialize-aliases", action="store_true", help="Write canonical aliases for existing source-node artifacts.")
    mode.add_argument("--run-missing", action="store_true", help="Resume the Oracle engine at the selected missing quartet node.")
    parser.add_argument("--target", default="oracle_cp2_emitter", help="Oracle source node target for --run-missing.")
    args = parser.parse_args()

    try:
        if args.materialize_aliases:
            payload = materialize_missing_aliases(args.subject_run, args.truth_run)
        elif args.run_missing:
            payload = run_missing_quartet(args.subject_run, args.truth_run, target=args.target)
        else:
            payload = build_quartet_repair_plan(args.subject_run, args.truth_run)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
