"""
[PURPOSE]
- Teleology: Orchestrate the refinement "Evolve" pipeline from paired subject/truth runs through bridge analysis, dossier patch generation, optional patch application, and learning-ledger append.
- Mechanism: Load Oracle and Lab artifacts, build prompts from refinement node instructions, dispatch them through the bridge, parse JSON payloads, send patch ops to version_committer, and persist the run's local debug artifacts.

[INTERFACE]
- Exports: run_evolve, main.
- Reads: subject/truth run `artifacts/*.json`, codex/nodes/refinement/{delta_analyzer,dossier_updater}.json.
- Writes: tools/refinement/_last_delta_response.txt on parse failure, tools/refinement/_last_delta_report.json, tools/refinement/_last_patch_payload.json, truth-run artifacts/evolve_*.json, codex/substrate/dossiers/learning_ledger.jsonl, and allowlisted dossiers indirectly through tools.refinement.version_committer when live apply is enabled.

[FLOW]
- Load Oracle truth artifacts and Lab CP2 from the paired runs.
- Build the delta_analyzer prompt and optionally dispatch it through the bridge.
- Persist the parsed delta report and, when deltas exist, build and dispatch the dossier_updater prompt.
- Preview or apply patch ops through version_committer and append a learning-ledger entry.

[DEPENDENCIES]
- Python stdlib: argparse, json, logging, pathlib, sys, typing.
- Internal: system.core.bridge.ask_ai via _dispatch_to_bridge.
- Internal: tools.refinement.version_committer.VersionCommitter via _apply_patches.

[CONSTRAINTS]
- Bridge use is optional; non-bridge mode returns a synthetic AVAILABLE delta report and skips LLM analysis.
- Dossier mutations stay confined to DOSSIER_ALLOWLIST and route through VersionCommitter.
- Debug payloads are persisted inside tools/refinement for later inspection when parsing or patch generation fails.
- When-needed: Open when a refinement pass needs the end-to-end runner that turns paired subject/truth runs into delta reports, dossier patch payloads, and optional dossier commits.
- Escalates-to: tools/refinement/version_committer.py::VersionCommitter.commit; tools/refinement/__init__.py
- Navigation-group: diff_refinement
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOSSIER_DIR = REPO_ROOT / "codex" / "substrate" / "dossiers"
LEARNING_LEDGER = DOSSIER_DIR / "learning_ledger.jsonl"
DELTA_NODE = REPO_ROOT / "codex" / "nodes" / "refinement" / "delta_analyzer.json"
UPDATER_NODE = REPO_ROOT / "codex" / "nodes" / "refinement" / "dossier_updater.json"

# Canonical Oracle artifact ids, with legacy node ids kept as read fallbacks.
ORACLE_ARTIFACTS: List[Tuple[str, Tuple[str, ...]]] = [
    ("prediction_reconciliation", ("prediction_reconciliation", "oracle_truth_diff_equity")),
    ("realized_hindsight_brief", ("realized_hindsight_brief", "oracle_truth_map")),
    ("cp2_critique", ("cp2_critique", "oracle_attribution_map")),
    ("ideal_cp2", ("ideal_cp2", "oracle_cp2_emitter")),
]
LAB_CP2_ARTIFACT = "lab_director"


DOSSIER_ALLOWLIST = {
    "codex/substrate/dossiers/stock.json",
    "codex/substrate/dossiers/etf.json",
    "codex/substrate/dossiers/macro.json",
    "codex/substrate/dossiers/oracle_error_taxonomy.json",
}


def _load_artifact(run_dir: Path, artifact_name: str) -> Optional[Dict[str, Any]]:
    """Load a JSON artifact from a run's artifacts directory."""
    path = run_dir / "artifacts" / f"{artifact_name}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load artifact %s: %s", path, e)
        return None


def _load_first_artifact(
    run_dir: Path,
    artifact_names: Sequence[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Path]]:
    """Load the first available artifact from a canonical/legacy candidate list."""
    for artifact_name in artifact_names:
        path = run_dir / "artifacts" / f"{artifact_name}.json"
        if not path.exists():
            continue
        data = _load_artifact(run_dir, artifact_name)
        if data is not None:
            return data, artifact_name, path
    return None, None, None


def _artifact_data(artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the payload data for engine envelopes or raw artifact dicts."""
    if not isinstance(artifact, dict):
        return {}
    data = artifact.get("data")
    if isinstance(data, dict):
        return data
    return artifact


def _extract_feed_health(prediction_reconciliation: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract feed-health readiness from the prediction reconciliation artifact."""
    data = _artifact_data(prediction_reconciliation)
    feed_health = data.get("feed_health")
    if isinstance(feed_health, dict):
        return feed_health
    return None


def _load_feed_readiness_summary(run_dir: Path) -> Dict[str, Any]:
    """Load the pre-Lab/feed-run readiness summary when a run provides one."""
    path = run_dir / "artifacts" / "feed_readiness_summary.json"
    if not path.exists():
        return {
            "present": False,
            "ready": None,
            "path": str(path),
            "target_count": 0,
            "status_counts": {},
            "blocker_count": 0,
            "blockers": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "present": True,
            "ready": None,
            "path": str(path),
            "target_count": 0,
            "status_counts": {"unreadable": 1},
            "blocker_count": 1,
            "blockers": [{"node_id": "feed_readiness_summary", "status": "unreadable", "reason": "artifact unreadable"}],
        }
    if not isinstance(payload, dict):
        return {
            "present": True,
            "ready": None,
            "path": str(path),
            "target_count": 0,
            "status_counts": {"invalid": 1},
            "blocker_count": 1,
            "blockers": [{"node_id": "feed_readiness_summary", "status": "invalid", "reason": "artifact is not an object"}],
        }
    blockers = [item for item in payload.get("blockers") or [] if isinstance(item, dict)]
    ready = payload.get("ready")
    return {
        "present": True,
        "ready": ready if isinstance(ready, bool) else None,
        "path": str(path),
        "target_count": int(payload.get("target_count") or 0),
        "status_counts": dict(payload.get("status_counts") or {}),
        "blocker_count": len(blockers),
        "blockers": blockers[:5],
    }


def _feed_readiness_messages(label: str, summary: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Return blocking reasons / warnings for an explicit feed-readiness surface."""
    if not summary.get("present"):
        return [], []
    ready = summary.get("ready")
    if ready is True:
        return [], []

    blockers = summary.get("blockers") if isinstance(summary.get("blockers"), list) else []
    details: List[str] = []
    for blocker in blockers[:3]:
        if not isinstance(blocker, dict):
            continue
        node_id = str(blocker.get("node_id") or "unknown_feed").strip()
        status = str(blocker.get("status") or "unknown").strip()
        reason = str(blocker.get("reason") or "").strip()
        detail = f"{node_id}={status}"
        if reason:
            detail += f" ({reason})"
        details.append(detail)

    if ready is False:
        reason = f"{label} feed_readiness_summary has blockers"
        if details:
            reason += ": " + "; ".join(details)
        return [reason], []

    warning = f"{label} feed_readiness_summary is present but has unknown ready status"
    if details:
        warning += ": " + "; ".join(details)
    return [], [warning]


def _load_oracle_artifacts(truth_run_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Load the Oracle artifact quartet and summarize readiness for Evolve."""
    oracle_artifacts: Dict[str, Any] = {}
    manifest: Dict[str, Any] = {
        "truth_run_id": truth_run_dir.name,
        "artifacts": [],
        "missing_artifacts": [],
        "feed_health": None,
    }

    for canonical_id, candidates in ORACLE_ARTIFACTS:
        data, source_id, source_path = _load_first_artifact(truth_run_dir, candidates)
        oracle_artifacts[canonical_id] = data
        entry: Dict[str, Any] = {
            "artifact_id": canonical_id,
            "candidate_artifact_ids": list(candidates),
            "status": "loaded" if data is not None else "missing",
        }
        if source_id and source_path:
            entry["source_artifact_id"] = source_id
            entry["source_path"] = str(source_path)
        else:
            manifest["missing_artifacts"].append(canonical_id)

        if canonical_id == "prediction_reconciliation":
            feed_health = _extract_feed_health(data)
            if feed_health:
                entry["feed_health_status"] = feed_health.get("status", "UNKNOWN")
                manifest["feed_health"] = feed_health
            elif data is not None:
                entry["feed_health_status"] = "UNKNOWN"

        manifest["artifacts"].append(entry)

    readiness = _oracle_input_readiness(manifest)
    manifest["readiness_status"] = readiness["status"]
    return oracle_artifacts, manifest, readiness


def _load_evolve_inputs(
    subject_run_dir: Path,
    truth_run_dir: Path,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """Load Lab/Oracle inputs and classify whether Evolve can safely learn."""
    oracle_artifacts, manifest, readiness = _load_oracle_artifacts(truth_run_dir)
    readiness = {
        "status": readiness.get("status", "UNKNOWN"),
        "blocking_reasons": list(readiness.get("blocking_reasons") or []),
        "warnings": list(readiness.get("warnings") or []),
    }

    lab_cp2 = _load_artifact(subject_run_dir, LAB_CP2_ARTIFACT)
    manifest["subject_run_id"] = subject_run_dir.name
    manifest["subject_feed_readiness"] = _load_feed_readiness_summary(subject_run_dir)
    manifest["truth_feed_readiness"] = _load_feed_readiness_summary(truth_run_dir)
    manifest["lab_cp2"] = {
        "artifact_id": LAB_CP2_ARTIFACT,
        "status": "loaded" if lab_cp2 is not None else "missing",
        "source_path": str(subject_run_dir / "artifacts" / f"{LAB_CP2_ARTIFACT}.json"),
    }
    if lab_cp2 is None:
        readiness["blocking_reasons"].append("missing required Lab CP2 artifact: lab_director")

    for label, key in (
        ("subject", "subject_feed_readiness"),
        ("truth", "truth_feed_readiness"),
    ):
        blocking, warnings = _feed_readiness_messages(label, manifest[key])
        readiness["blocking_reasons"].extend(blocking)
        readiness["warnings"].extend(warnings)

    if readiness["blocking_reasons"]:
        readiness["status"] = "BLOCKED"
    elif readiness["warnings"]:
        readiness["status"] = "DEGRADED"
    else:
        readiness["status"] = "READY"
    manifest["readiness_status"] = readiness["status"]
    return oracle_artifacts, lab_cp2, manifest, readiness


def build_input_readiness_payload(subject_run_dir: Path, truth_run_dir: Path) -> Dict[str, Any]:
    """Build a JSON-serializable input-readiness payload for Station and CLI checks."""
    _, _, manifest, readiness = _load_evolve_inputs(subject_run_dir, truth_run_dir)
    payload = {
        "kind": "evolve_input_readiness",
        "schema_version": "1.0",
        "subject_run_id": subject_run_dir.name,
        "truth_run_id": truth_run_dir.name,
        "readiness": readiness,
        "manifest": manifest,
    }
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from tools.oracle.run_quartet import build_quartet_repair_plan

        payload["oracle_repair_plan"] = build_quartet_repair_plan(subject_run_dir, truth_run_dir)
    except Exception as exc:
        payload["oracle_repair_plan"] = {
            "kind": "oracle_quartet_repair_plan",
            "schema_version": "1.0",
            "readiness": {"status": "UNKNOWN"},
            "repair_actions": [],
            "error": str(exc),
        }
    return payload


def _oracle_input_readiness(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Classify whether Oracle artifacts are safe for Evolve learning."""
    missing = [str(item) for item in manifest.get("missing_artifacts", [])]
    feed_health = manifest.get("feed_health")
    blocking_reasons: List[str] = []
    warnings: List[str] = []

    if missing:
        blocking_reasons.append(
            "missing required Oracle artifacts: " + ", ".join(missing)
        )

    if isinstance(feed_health, dict):
        feed_status = str(feed_health.get("status") or "UNKNOWN").upper()
        diagnostics = [
            str(item)
            for item in feed_health.get("diagnostics", [])
            if item
        ]
        if feed_status == "BLOCKED":
            reason = "prediction_reconciliation.feed_health is BLOCKED"
            if diagnostics:
                reason += ": " + "; ".join(diagnostics)
            blocking_reasons.append(reason)
        elif feed_status == "DEGRADED":
            warning = "prediction_reconciliation.feed_health is DEGRADED"
            if diagnostics:
                warning += ": " + "; ".join(diagnostics)
            warnings.append(warning)
        elif feed_status != "READY":
            warnings.append(
                "prediction_reconciliation.feed_health status is "
                f"{feed_status}; treat target grading cautiously"
            )
    elif "prediction_reconciliation" not in missing:
        warnings.append(
            "prediction_reconciliation.feed_health is missing; cannot separate feed coverage from target performance"
        )

    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict) or artifact.get("status") != "loaded":
            continue
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        source_id = str(artifact.get("source_artifact_id") or artifact_id).strip()
        if artifact_id and source_id and source_id != artifact_id:
            warnings.append(
                f"{artifact_id} loaded from legacy alias {source_id}; prefer canonical artifact output"
            )

    if blocking_reasons:
        status = "BLOCKED"
    elif warnings:
        status = "DEGRADED"
    else:
        status = "READY"

    return {
        "status": status,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
    }


def _load_node_instruction(node_path: Path) -> str:
    """Load a node's instruction field."""
    with open(node_path, "r", encoding="utf-8") as f:
        node = json.load(f)
    return node.get("instruction", "")


def _build_delta_prompt(
    oracle_artifacts: Dict[str, Any],
    lab_cp2: Optional[Dict[str, Any]],
    subject_run_id: str,
    truth_run_id: str,
    oracle_input_manifest: Optional[Dict[str, Any]] = None,
    oracle_input_readiness: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the delta_analyzer prompt with Oracle outputs injected."""
    instruction = _load_node_instruction(DELTA_NODE)

    # Inject Oracle artifacts as context
    context_parts = [instruction]

    if oracle_input_readiness is not None:
        context_parts.append("\n\n=== ORACLE INPUT READINESS ===\n")
        context_parts.append(json.dumps(oracle_input_readiness, indent=2, ensure_ascii=False))

    if oracle_input_manifest is not None:
        context_parts.append("\n\n=== ORACLE INPUT MANIFEST ===\n")
        context_parts.append(json.dumps(oracle_input_manifest, indent=2, ensure_ascii=False)[:12000])

    context_parts.append("\n\n=== ORACLE ARTIFACTS ===\n")

    for name, data in oracle_artifacts.items():
        if data is not None:
            context_parts.append(f"\n--- {name} ---\n")
            context_parts.append(json.dumps(data, indent=2, ensure_ascii=False)[:30000])

    if lab_cp2:
        context_parts.append("\n--- lab_cp2 (Lab Director Output) ---\n")
        context_parts.append(json.dumps(lab_cp2, indent=2, ensure_ascii=False)[:15000])

    context_parts.append(f"\n\nrun_pair: subject={subject_run_id}, truth={truth_run_id}")

    return "\n".join(context_parts)


def _build_updater_prompt(delta_report: Dict[str, Any]) -> str:
    """Build the dossier_updater prompt with delta report injected."""
    instruction = _load_node_instruction(UPDATER_NODE)
    return f"{instruction}\n\n=== DELTA REPORT ===\n{json.dumps(delta_report, indent=2, ensure_ascii=False)}"


def _dispatch_to_bridge(prompt: str, provider: str = "chatgpt") -> Optional[str]:
    """Dispatch a prompt to the bridge and return the response text."""
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from system.core import bridge as bridge_mod

        config = {"targets": {"chatgpt": "https://chatgpt.com", "gemini": "https://gemini.google.com"}}
        response = bridge_mod.ask_ai(prompt, config=config)
        if not response or not response.strip():
            logger.warning("Bridge returned empty response")
            return None
        return response
    except Exception as e:
        logger.error("Bridge dispatch failed: %s", e)
        return None


def _parse_json_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from a bridge response that may contain markdown fences."""
    text = response.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown fences
    import re
    match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding the first { ... } block
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start:i + 1])
                    except json.JSONDecodeError:
                        break

    return None


def _apply_patches(
    patch_payload: Dict[str, Any],
    run_id: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Apply dossier patches via version_committer."""
    from tools.refinement.version_committer import VersionCommitter

    committer = VersionCommitter(repo_root=REPO_ROOT)
    results = {"lanes": {}, "total_applied": 0, "total_skipped": 0}

    lanes = patch_payload.get("lanes", {})
    for lane_name, lane_data in lanes.items():
        ops = lane_data.get("ops", [])
        dossier_path = lane_data.get("dossier_path", "")

        if not ops:
            results["lanes"][lane_name] = {"status": "skipped", "reason": "no ops"}
            continue

        # Validate dossier path against allowlist
        if dossier_path and dossier_path not in DOSSIER_ALLOWLIST:
            results["lanes"][lane_name] = {"status": "rejected", "reason": f"dossier_path not in allowlist: {dossier_path}"}
            continue

        if dry_run:
            results["lanes"][lane_name] = {
                "status": "dry_run",
                "ops_count": len(ops),
                "dossier_path": dossier_path,
                "ops_preview": ops[:3],
            }
            continue

        try:
            result = committer.commit(
                ops=ops,
                dossier_path=dossier_path,
                run_id=run_id,
                lane=lane_name,
                observation_report_path=f"evolve_run_{run_id}",
            )
            applied = len(result.get("applied_ops", []))
            skipped = len(result.get("skipped_ops", []))
            results["lanes"][lane_name] = {
                "status": "applied",
                "applied": applied,
                "skipped": skipped,
                "commit_hash": result.get("commit_hash", "NO_GIT"),
            }
            results["total_applied"] += applied
            results["total_skipped"] += skipped
        except Exception as e:
            results["lanes"][lane_name] = {"status": "error", "error": str(e)}

    return results


def _append_learning_ledger(
    delta_report: Dict[str, Any],
    patch_results: Dict[str, Any],
    oracle_input_readiness: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a learning entry to the ledger."""
    from datetime import datetime, timezone
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_pair": delta_report.get("run_pair", {}),
        "root_failure_mode": delta_report.get("pattern_summary", {}).get("root_failure_mode", "UNKNOWN"),
        "error_class_distribution": delta_report.get("pattern_summary", {}).get("error_class_distribution", {}),
        "dossier_ops_applied": patch_results.get("total_applied", 0),
        "dossier_ops_skipped": patch_results.get("total_skipped", 0),
        "doctrine_flags_raised": [
            f.get("flag_type", "unknown") for f in delta_report.get("doctrine_flags", [])
        ],
        "learning_entries": delta_report.get("learning_entries", []),
    }
    if oracle_input_readiness is not None:
        entry["oracle_input_readiness"] = oracle_input_readiness

    LEARNING_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARNING_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info("Appended learning ledger entry for run pair %s", entry["run_pair"])


def _compact_apply_results(apply_results: Dict[str, Any]) -> Dict[str, Any]:
    """Return the apply-result subset safe to embed in a run-scoped artifact."""
    lane_statuses: Dict[str, str] = {}
    lanes = apply_results.get("lanes")
    if isinstance(lanes, dict):
        for lane_name, lane_result in lanes.items():
            if isinstance(lane_result, dict):
                lane_statuses[str(lane_name)] = str(lane_result.get("status") or "unknown")
    return {
        "total_applied": int(apply_results.get("total_applied") or 0),
        "total_skipped": int(apply_results.get("total_skipped") or 0),
        "lane_statuses": lane_statuses,
    }


def _write_run_scoped_artifact(
    run_dir: Path,
    artifact_id: str,
    data: Dict[str, Any],
    *,
    metadata: Optional[Dict[str, Any]] = None,
    status: str = "success",
) -> Path:
    """Persist a durable Evolve artifact beside the truth run artifacts."""
    from datetime import datetime, timezone

    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"{artifact_id}.json"
    envelope = {
        "id": artifact_id,
        "status": status,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        },
        "data": data,
    }
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)
    return path


def _persist_run_scoped_evolve_artifacts(
    *,
    subject_run_dir: Path,
    truth_run_dir: Path,
    provider: str,
    use_bridge: bool,
    dry_run: bool,
    auto_apply: bool,
    apply_mode: str,
    oracle_input_manifest: Dict[str, Any],
    oracle_input_readiness: Dict[str, Any],
    delta_report: Dict[str, Any],
    patch_payload: Dict[str, Any],
    apply_results: Dict[str, Any],
    delta_path: Path,
    patch_path: Path,
) -> Dict[str, str]:
    """Write the successful Evolve run outputs into the paired truth run."""
    metadata: Dict[str, Any] = {
        "schema_version": "evolve_run_artifact.v1",
        "source": "tools/refinement/run_evolve.py",
        "subject_run_id": subject_run_dir.name,
        "truth_run_id": truth_run_dir.name,
        "provider": provider if use_bridge else None,
        "bridge": bool(use_bridge),
        "dry_run": bool(dry_run),
        "auto_apply": bool(auto_apply),
        "apply_mode": apply_mode,
        "latest_delta_path": str(delta_path),
        "latest_patch_path": str(patch_path),
    }
    paths = {
        "evolve_input_readiness": _write_run_scoped_artifact(
            truth_run_dir,
            "evolve_input_readiness",
            {
                "readiness": oracle_input_readiness,
                "manifest": oracle_input_manifest,
            },
            metadata=metadata,
        ),
        "evolve_delta_report": _write_run_scoped_artifact(
            truth_run_dir,
            "evolve_delta_report",
            delta_report,
            metadata=metadata,
        ),
        "evolve_patch_payload": _write_run_scoped_artifact(
            truth_run_dir,
            "evolve_patch_payload",
            patch_payload,
            metadata={
                **metadata,
                "apply_results": _compact_apply_results(apply_results),
            },
        ),
    }
    return {artifact_id: str(path) for artifact_id, path in paths.items()}


def run_evolve(
    subject_run_dir: Path,
    truth_run_dir: Path,
    provider: str = "chatgpt",
    use_bridge: bool = True,
    dry_run: bool = True,
    auto_apply: bool = False,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Execute the full Evolve refinement pass for one subject/truth run pair.
    - Mechanism: Load paired artifacts, run delta analysis, optionally run dossier patch synthesis, preview or apply patch ops, and append the learning ledger.
    - Reads: subject_run_dir/artifacts, truth_run_dir/artifacts, refinement node instructions, and bridge responses when use_bridge is enabled.
    - Writes: _last_delta_response.txt on parse failure, _last_delta_report.json, _last_patch_payload.json, truth-run artifacts/evolve_*.json, learning_ledger.jsonl, and allowlisted dossier JSON files indirectly when auto_apply and live mode are both enabled.
    - Guarantee: Returns a summary dict containing either an `error` key or the completed delta_report, patch_payload, apply_results, delta_path, patch_path, and run_artifact_paths surfaces.
    - Fails: Does not raise for normal bridge or parse failures; those cases return structured `error` payloads for the caller.
    - When-needed: Open when you need the exact control flow and write surfaces for an Evolve run instead of inspecting the helper functions individually.
    - Escalates-to: tools/refinement/version_committer.py::VersionCommitter.commit; tools/refinement/__init__.py
    - Navigation-group: diff_refinement
    """
    print(f"\n{'='*60}")
    print(f"  EVOLVE PIPELINE")
    print(f"  Subject: {subject_run_dir.name}")
    print(f"  Truth:   {truth_run_dir.name}")
    print(f"  Bridge:  {provider if use_bridge else 'disabled'}")
    print(f"  Mode:    {'dry-run' if dry_run else 'live'}")
    print(f"{'='*60}\n")

    # 1. Load Oracle artifacts
    print("[1/6] Loading Oracle artifacts...")
    oracle_artifacts, lab_cp2, oracle_input_manifest, oracle_input_readiness = _load_evolve_inputs(
        subject_run_dir,
        truth_run_dir,
    )
    missing = oracle_input_manifest.get("missing_artifacts", [])

    if missing:
        print(f"  WARNING: Missing Oracle artifacts: {missing}")
        if len(missing) == len(ORACLE_ARTIFACTS):
            print("  ERROR: No Oracle artifacts found. Cannot run Evolve.")
            return {
                "error": "no_oracle_artifacts",
                "missing": missing,
                "oracle_input_manifest": oracle_input_manifest,
                "oracle_input_readiness": oracle_input_readiness,
            }

    for entry in oracle_input_manifest.get("artifacts", []):
        name = entry.get("artifact_id", "unknown")
        status = entry.get("status", "unknown")
        source = entry.get("source_artifact_id")
        suffix = f" via {source}" if source and source != name else ""
        print(f"  {name}: {status}{suffix}")

    feed_health = oracle_input_manifest.get("feed_health")
    if isinstance(feed_health, dict):
        print(f"  feed_health: {feed_health.get('status', 'UNKNOWN')}")
    print(f"  oracle_input_readiness: {oracle_input_readiness.get('status', 'UNKNOWN')}")
    for warning in oracle_input_readiness.get("warnings", []):
        print(f"  WARNING: {warning}")

    # 2. Load Lab CP2
    print("\n[2/6] Loading Lab CP2...")
    print(f"  lab_director: {'loaded' if lab_cp2 else 'MISSING'}")
    if oracle_input_readiness.get("status") == "BLOCKED":
        print("  ERROR: Evolve inputs are not ready.")
        for reason in oracle_input_readiness.get("blocking_reasons", []):
            print(f"  - {reason}")
        return {
            "error": "evolve_inputs_not_ready",
            "oracle_input_manifest": oracle_input_manifest,
            "oracle_input_readiness": oracle_input_readiness,
        }

    subject_run_id = subject_run_dir.name
    truth_run_id = truth_run_dir.name

    # 3. Build and dispatch delta_analyzer
    print("\n[3/6] Running delta_analyzer...")
    delta_prompt = _build_delta_prompt(
        oracle_artifacts,
        lab_cp2,
        subject_run_id,
        truth_run_id,
        oracle_input_manifest=oracle_input_manifest,
        oracle_input_readiness=oracle_input_readiness,
    )
    print(f"  Prompt size: {len(delta_prompt):,} chars")

    if use_bridge:
        delta_response = _dispatch_to_bridge(delta_prompt, provider=provider)
        if not delta_response:
            return {"error": "delta_analyzer_dispatch_failed"}
        delta_report = _parse_json_response(delta_response)
        if not delta_report:
            print(f"  ERROR: Could not parse delta_analyzer response as JSON")
            # Save raw response for debugging
            debug_path = REPO_ROOT / "tools" / "refinement" / "_last_delta_response.txt"
            debug_path.write_text(delta_response[:10000], encoding="utf-8")
            return {"error": "delta_analyzer_parse_failed", "debug_path": str(debug_path)}
    else:
        print("  SKIPPED (bridge disabled)")
        delta_report = {
            "status": "AVAILABLE",
            "run_pair": {"subject_run_id": subject_run_id, "truth_run_id": truth_run_id},
            "pattern_summary": {"root_failure_mode": "UNKNOWN", "error_class_distribution": {}, "directional_accuracy": {}, "regime_classification": "unknown", "systematic_patterns": []},
            "dossier_deltas": [],
            "doctrine_flags": [],
            "learning_entries": ["Evolve ran without bridge; no analysis performed."],
        }

    print(f"  Delta report status: {delta_report.get('status', 'UNKNOWN')}")
    print(f"  Dossier deltas: {len(delta_report.get('dossier_deltas', []))}")
    print(f"  Doctrine flags: {len(delta_report.get('doctrine_flags', []))}")

    # Save delta report
    delta_path = REPO_ROOT / "tools" / "refinement" / "_last_delta_report.json"
    with open(delta_path, "w", encoding="utf-8") as f:
        json.dump(delta_report, f, indent=2, ensure_ascii=False)
    print(f"  Saved to: {delta_path}")

    # 4. Build and dispatch dossier_updater
    print("\n[4/6] Running dossier_updater...")
    if delta_report.get("dossier_deltas"):
        updater_prompt = _build_updater_prompt(delta_report)
        print(f"  Prompt size: {len(updater_prompt):,} chars")

        if use_bridge:
            updater_response = _dispatch_to_bridge(updater_prompt, provider=provider)
            if not updater_response:
                return {"error": "dossier_updater_dispatch_failed", "delta_report": delta_report}
            patch_payload = _parse_json_response(updater_response)
            if not patch_payload:
                print(f"  ERROR: Could not parse dossier_updater response as JSON")
                return {"error": "dossier_updater_parse_failed", "delta_report": delta_report}
        else:
            patch_payload = {"lanes": {}, "total_ops": 0, "summary": "No bridge"}
    else:
        print("  SKIPPED (no dossier deltas to process)")
        patch_payload = {"lanes": {}, "total_ops": 0, "summary": "No deltas"}

    print(f"  Total ops: {patch_payload.get('total_ops', 0)}")

    # Save patch payload
    patch_path = REPO_ROOT / "tools" / "refinement" / "_last_patch_payload.json"
    with open(patch_path, "w", encoding="utf-8") as f:
        json.dump(patch_payload, f, indent=2, ensure_ascii=False)

    # 5. Apply patches
    print("\n[5/6] Applying patches...")
    apply_mode = "live" if auto_apply and not dry_run else "dry-run"
    print(f"  Mode: {apply_mode}")

    apply_results = _apply_patches(
        patch_payload,
        run_id=f"{subject_run_id}_evolve",
        dry_run=(dry_run or not auto_apply),
    )

    for lane, result in apply_results.get("lanes", {}).items():
        print(f"  {lane}: {result.get('status', 'unknown')}")

    # 6. Learning ledger
    print("\n[6/6] Updating learning ledger...")
    _append_learning_ledger(delta_report, apply_results, oracle_input_readiness)
    print(f"  Appended to {LEARNING_LEDGER}")
    run_artifact_paths = _persist_run_scoped_evolve_artifacts(
        subject_run_dir=subject_run_dir,
        truth_run_dir=truth_run_dir,
        provider=provider,
        use_bridge=use_bridge,
        dry_run=dry_run,
        auto_apply=auto_apply,
        apply_mode=apply_mode,
        oracle_input_manifest=oracle_input_manifest,
        oracle_input_readiness=oracle_input_readiness,
        delta_report=delta_report,
        patch_payload=patch_payload,
        apply_results=apply_results,
        delta_path=delta_path,
        patch_path=patch_path,
    )
    print(f"  Run artifacts: {', '.join(run_artifact_paths.values())}")

    summary = {
        "status": "completed",
        "oracle_input_manifest": oracle_input_manifest,
        "oracle_input_readiness": oracle_input_readiness,
        "delta_report": delta_report,
        "patch_payload": patch_payload,
        "apply_results": apply_results,
        "delta_path": str(delta_path),
        "patch_path": str(patch_path),
        "run_artifact_paths": run_artifact_paths,
    }

    print(f"\n{'='*60}")
    print(f"  EVOLVE COMPLETE")
    print(f"  Root failure mode: {delta_report.get('pattern_summary', {}).get('root_failure_mode', 'N/A')}")
    print(f"  Learning entries: {len(delta_report.get('learning_entries', []))}")
    print(f"  Doctrine flags: {len(delta_report.get('doctrine_flags', []))}")
    print(f"  Dossier ops: {apply_results.get('total_applied', 0)} applied, {apply_results.get('total_skipped', 0)} skipped")
    print(f"{'='*60}\n")

    return summary


def main():
    """
    [ACTION]
    - Teleology: Provide the CLI entrypoint for running the Evolve pipeline from a shell invocation.
    - Mechanism: Parse flags, validate subject/truth run paths, configure logging, call run_evolve(), and exit non-zero when the returned payload carries an error.
    - Reads: argparse CLI flags and the filesystem paths supplied by the caller.
    - Writes: Process exit status and stdout/stderr messaging; delegates all durable artifact writes to run_evolve().
    - Guarantee: Exits with status 1 when required run paths are missing or when run_evolve() reports an error.
    - Fails: None directly; operational failures are surfaced through explicit sys.exit(1) paths.
    - When-needed: Open when tracing how shell flags map onto run_evolve() parameters or why the CLI returned a failing exit code.
    - Escalates-to: tools/refinement/run_evolve.py::run_evolve
    """
    parser = argparse.ArgumentParser(description="Run the Evolve learning pipeline")
    parser.add_argument("--subject-run", required=True, help="Path to subject Lab run directory")
    parser.add_argument("--truth-run", required=True, help="Path to paired truth Oracle run directory")
    parser.add_argument("--bridge", action="store_true", help="Use bridge for LLM dispatch")
    parser.add_argument("--provider", default="chatgpt", help="Bridge provider (default: chatgpt)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview patches without applying (default)")
    parser.add_argument("--live", action="store_true", help="Apply patches for real")
    parser.add_argument("--auto-apply", action="store_true", help="Skip proof/approval gate and apply patches directly")
    parser.add_argument("--input-check", action="store_true", help="Only validate Evolve input readiness and print JSON")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    subject = Path(args.subject_run).resolve()
    truth = Path(args.truth_run).resolve()

    if not subject.exists():
        print(f"ERROR: Subject run not found: {subject}")
        sys.exit(1)
    if not truth.exists():
        print(f"ERROR: Truth run not found: {truth}")
        sys.exit(1)

    if args.input_check:
        payload = build_input_readiness_payload(subject, truth)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        sys.exit(1 if payload.get("readiness", {}).get("status") == "BLOCKED" else 0)

    result = run_evolve(
        subject_run_dir=subject,
        truth_run_dir=truth,
        provider=args.provider,
        use_bridge=args.bridge,
        dry_run=not args.live,
        auto_apply=args.auto_apply,
    )

    if result.get("error"):
        print(f"\nEVOLVE FAILED: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
