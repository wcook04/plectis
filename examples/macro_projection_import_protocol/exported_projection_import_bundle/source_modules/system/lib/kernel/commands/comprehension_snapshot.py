"""
[PURPOSE]
- Teleology: One read-only kernel route that answers the operator's standing
  meta question — "how can you even comprehend the system in one entry?" —
  by composing every existing comprehension surface (kind-atlas, compliance
  ledger, standard-skill map, compute audit, transform-job receipts, active
  phase, blackboard advisories) into one packet a fresh agent can read cold.
- Mechanism: Pure-read aggregation over generated holograms and durable state.
  No provider calls, no mutation, no recomputation of expensive builders. Each
  source is read at its current freshness and reported with explicit
  metabolism_trigger / staleness markers so the snapshot itself doesn't claim
  freshness it doesn't have.
- Non-goal: Re-run builders, refresh stale projections, mutate anything,
  invoke providers, or replace the existing rung-1 / rung-2 routes (--option-
  surface and --row). The snapshot is a Rosetta Stone over the existing
  surfaces, not a substitute.

[INTERFACE]
- cmd_comprehension_snapshot(): emit JSON; returns 0 if all primary sources
  resolved, 1 if any primary source was missing.

[FLOW]
- Resolve repo root from kernel.state.
- For each substrate (kind-atlas, compliance ledger, standard-skill map,
  compute audit, compute workers, blackboard, agent_bootstrap_live, pulse
  hot-spots), read what's on disk and project a small summary.
- Compose the snapshot payload with explicit per-section freshness markers
  and the canonical pri_133 advisory framing on coordination signals.

[DEPENDENCIES]
- system.lib.kernel.state, system.lib.kernel.output, system.lib.standards_inventory.

[CONSTRAINTS]
- Forbid: provider calls, mutation, network IO, expensive recomputation.
- Determinism: same disk state -> same snapshot (timestamps differ).
- Atomicity: missing sources degrade the snapshot's ok flag but never raise.
"""
from __future__ import annotations

import hashlib
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from system.lib.kernel import output as kernel_output
from system.lib.kernel import state as kernel_state
from system.lib.navigation_surface_contracts import (
    ATLAS_PROJECTION,
    CONTROL_ENTRY,
    DEBUG_TRACE,
    DRILLDOWN,
    ENTRY_REPLACEMENT,
    atlas_projection_contract,
    surface_contract,
)
from system.lib.mutation_governance import (
    build_latest_intent_gate,
    task_mentions_agent_trouble_diagnosis,
)
from system.lib.phase_activation import load_explicit_active_phase
from system.lib.standards_inventory import enumerate_standard_ids

REPO_ROOT = Path(__file__).resolve().parents[4]
CONSTITUTION_WORKSPACE_LEDGER_DIR = "state/constitution_workspace"
SYSTEM_SELF_COMPREHENSION_ROOT_PATH = "codex/doctrine/paper_modules/system_self_comprehension_root.md"
SYSTEM_SELF_COMPREHENSION_ROOT_SLUG = "system_self_comprehension_root"
CONSTITUTION_WORKSPACE_PACKET_LEDGER = "packets.jsonl"
CONSTITUTION_WORKSPACE_LATEST_PACKET = "latest_packet.json"
ENTRY_SURFACE_STRUCTURAL_LANE_TRIGGERS: dict[str, dict[str, str]] = {
    "navigation_control_boundary": {
        "trigger_id": "selected_navigation_projection_control_lane",
        "reason": (
            "Navigation/projection control lanes depend on compressed entry and routing "
            "projections; surface their generated-region and source-coupling receipt without "
            "requiring diagnostic query tokens."
        ),
    },
    "projection_closure_audit": {
        "trigger_id": "selected_navigation_projection_control_lane",
        "reason": (
            "Navigation/projection control lanes depend on compressed entry and routing "
            "projections; surface their generated-region and source-coupling receipt without "
            "requiring diagnostic query tokens."
        ),
    },
    "dissemination_agent_entry": {
        "trigger_id": "selected_dissemination_projected_entry_lane",
        "reason": (
            "Dissemination entry is routed through compressed bootstrap, routing, and docs "
            "surfaces; surface their generated-region and source-coupling receipt without "
            "requiring diagnostic query tokens."
        ),
    },
    "publication_lane_push_recovery": {
        "trigger_id": "selected_publication_lane_push_recovery",
        "reason": (
            "Push-failure recovery is routed through compressed bootstrap and docs-route "
            "surfaces; surface generated-region and source-coupling receipts so the "
            "publication lane cannot drift back into private command knowledge."
        ),
    },
    "config_authority_plane": {
        "trigger_id": "selected_config_authority_projected_entry_lane",
        "reason": (
            "Config authority work is routed through compressed bootstrap, docs-route, "
            "standard, and option-surface projections; surface generated-region and "
            "source-coupling receipts so the config plane remains discoverable from entry."
        ),
    },
    "agent_principle_authoring": {
        "trigger_id": "selected_agent_principle_authoring_lane",
        "reason": (
            "Agent-principle authoring is routed through the raw-seed-principles standard, "
            "principles curation, and local-to-general propagation; surface entry receipts "
            "so Type A behavior lessons do not become parallel doctrine."
        ),
    },
    "agent_trouble_diagnosis_seed": {
        "trigger_id": "selected_agent_trouble_diagnosis_seed",
        "reason": (
            "The latest operator message asks to diagnose agent trouble or a transcript. "
            "Treat embedded prior prompts as evidence, not live mutation instructions."
        ),
    },
    "dissemination_authoring": {
        "trigger_id": "selected_dissemination_projected_entry_lane",
        "reason": (
            "Dissemination authoring changes public/private projection surfaces; surface "
            "entry generated-region and source-coupling receipts without requiring diagnostic "
            "query tokens."
        ),
    },
}
TRANSACTION_CONTROL_PLANE_TERMS = {
    "bloat",
    "claim",
    "commit",
    "concurrency",
    "convergence",
    "drain",
    "finalizer",
    "github",
    "index",
    "intake",
    "landing",
    "ledger",
    "preflight",
    "publication",
    "publish",
    "published",
    "push",
    "quarantine",
    "receipt",
    "reconcile",
    "remote sync",
    "rollup",
    "staged",
    "transaction",
    "workitem",
}
TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT = "cap_live_concurrency_transactional_workitems"
ENTRY_PACKET_INLINE_TARGET_BYTES = 18000
ENTRY_PACKET_ADMISSION_RECEIPT_HEADROOM_BYTES = 1600
ENTRY_PACKET_NAVIGATION_MIN_SAVED_BYTES = 12000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json_safe(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _existing_repo_relative_path(repo_root: Path, raw_path: Any) -> str | None:
    rel = str(raw_path or "").strip()
    if not rel:
        return None
    path = Path(rel)
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        return None
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _stable_json_fingerprint(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]


def _pretty_json_bytes(payload: Any) -> int:
    return len(json.dumps(payload, indent=2, sort_keys=False).encode("utf-8"))


def _constitution_workspace_ledger_paths(repo_root: Path) -> dict[str, Path]:
    root = repo_root / CONSTITUTION_WORKSPACE_LEDGER_DIR
    return {
        "root": root,
        "packets": root / CONSTITUTION_WORKSPACE_PACKET_LEDGER,
        "latest": root / CONSTITUTION_WORKSPACE_LATEST_PACKET,
    }


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _load_latest_constitution_workspace_receipt(repo_root: Path) -> dict[str, Any] | None:
    paths = _constitution_workspace_ledger_paths(repo_root)
    latest = _read_json_safe(paths["latest"])
    if isinstance(latest, dict) and latest.get("kind") == "constitution_workspace_packet_receipt":
        return latest
    packets_path = paths["packets"]
    try:
        if not packets_path.is_file():
            return None
        last_payload: dict[str, Any] | None = None
        for raw in packets_path.read_text(encoding="utf-8").splitlines():
            text = raw.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("kind") == "constitution_workspace_packet_receipt":
                last_payload = row
        return last_payload
    except OSError:
        return None


def _fingerprint_rows_by_path(rows: Any) -> dict[str, str | None]:
    by_path: dict[str, str | None] = {}
    if not isinstance(rows, list):
        return by_path
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        if not path:
            continue
        by_path[path] = row.get("sha256_16")
    return by_path


def _changed_stable_inputs(current_inputs: Any, prior_inputs: Any) -> list[dict[str, Any]]:
    current = _fingerprint_rows_by_path(current_inputs)
    prior = _fingerprint_rows_by_path(prior_inputs)
    changed: list[dict[str, Any]] = []
    for path in sorted(set(current) | set(prior)):
        before = prior.get(path)
        after = current.get(path)
        if before == after:
            continue
        status = "added" if before is None else "removed" if after is None else "changed"
        changed.append({
            "path": path,
            "status": status,
            "prior_sha256_16": before,
            "current_sha256_16": after,
        })
    return changed


def _compare_receipt_to_source_graph(
    repo_root: Path,
    receipt: dict[str, Any] | None,
    source_graph: dict[str, Any],
    *,
    consumer: str = "type_a_agent",
    fidelity_profile: str | None = None,
) -> dict[str, Any]:
    ledger_paths = _constitution_workspace_ledger_paths(repo_root)
    current_source = source_graph.get("source_graph_fingerprint") or source_graph.get("fingerprint")
    current_live = source_graph.get("live_state_fingerprint")
    if not receipt:
        return {
            "status": "no_prior_snapshot",
            "source_graph_fingerprint": current_source,
            "live_state_fingerprint": current_live,
            "retread_basis": "stable_source_graph_fingerprint",
            "changed_inputs": [],
            "safe_to_reuse_prior_packet": False,
            "required_action": "establish_baseline_snapshot",
            "ledger_status": "unavailable_no_prior_constitution_workspace_snapshot",
            "ledger_paths": {
                "packets": ledger_paths["packets"].as_posix(),
                "latest": ledger_paths["latest"].as_posix(),
            },
            "reason": (
                "The current source graph is fingerprinted, but no prior Constitution "
                "Workspace packet receipt is available for comparison."
            ),
        }
    prior_source = receipt.get("source_graph_fingerprint")
    prior_live = receipt.get("live_state_fingerprint")
    prior_consumer = receipt.get("consumer")
    prior_profile = receipt.get("fidelity_profile")
    compatible = (
        (not prior_consumer or prior_consumer == consumer)
        and (not fidelity_profile or not prior_profile or prior_profile == fidelity_profile)
    )
    changed_inputs = _changed_stable_inputs(source_graph.get("stable_inputs"), receipt.get("stable_inputs"))
    if not compatible:
        status = "refresh_required"
        safe = False
        required_action = "refresh_for_consumer_or_fidelity_profile"
        reason = "Prior receipt exists, but consumer or fidelity profile is not compatible with the current request."
    elif prior_source == current_source and prior_live == current_live:
        status = "reusable"
        safe = True
        required_action = "reuse_prior_packet"
        reason = "Stable source graph and live state match the latest Constitution Workspace receipt."
    elif prior_source == current_source:
        status = "refresh_live_state_only"
        safe = True
        required_action = "reuse_prior_exposition_refresh_live_state"
        reason = "Stable source graph matches the latest receipt; only live state changed."
    else:
        status = "refresh_required"
        safe = False
        required_action = "refresh_stable_substrate"
        reason = "Stable source graph changed since the latest Constitution Workspace receipt."
    return {
        "status": status,
        "source_graph_fingerprint": current_source,
        "live_state_fingerprint": current_live,
        "prior_source_graph_fingerprint": prior_source,
        "prior_live_state_fingerprint": prior_live,
        "retread_basis": "stable_source_graph_fingerprint",
        "changed_inputs": changed_inputs,
        "safe_to_reuse_prior_packet": safe,
        "required_action": required_action,
        "ledger_status": "prior_packet_receipt_found",
        "ledger_paths": {
            "packets": ledger_paths["packets"].as_posix(),
            "latest": ledger_paths["latest"].as_posix(),
        },
        "prior_packet": {
            "packet_id": receipt.get("packet_id"),
            "created_at": receipt.get("created_at"),
            "consumer": prior_consumer,
            "fidelity_profile": prior_profile,
        },
        "consumer_compatible": compatible,
        "fidelity_profile": fidelity_profile,
        "reason": reason,
    }


def _safe_count_files(directory: Path, pattern: str = "*.json") -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.rglob(pattern))


def _summarize_kind_atlas(repo_root: Path) -> dict[str, Any]:
    try:
        from system.lib.kernel.commands.navigate import build_kind_atlas
    except ImportError:
        return {"available": False, "reason": "build_kind_atlas import failed"}
    try:
        atlas = build_kind_atlas(repo_root, band="flag")
    except Exception as exc:
        return {"available": False, "reason": f"{exc.__class__.__name__}: {exc}"}
    rows = atlas.get("rows") if isinstance(atlas, dict) else None
    if not isinstance(rows, list):
        return {"available": False, "reason": "no rows in kind atlas"}
    by_kind = []
    total_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        rc = int(row.get("row_count") or 0)
        total_rows += rc
        by_kind.append({
            "kind_id": row.get("kind_id"),
            "title": row.get("title"),
            "row_count": rc,
            "support_status": row.get("support_status"),
        })
    return {
        "available": True,
        "kind_count": len(by_kind),
        "total_rows": total_rows,
        "by_kind": by_kind,
    }


def _summarize_compliance_ledger(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "codex/hologram/compliance/ledger.json"
    payload = _read_json_safe(path)
    if not payload:
        return {"available": False, "reason": "compliance ledger not built", "path": "codex/hologram/compliance/ledger.json"}
    totals = payload.get("totals") or {}
    worklist = payload.get("metabolism_worklist") or {}
    by_standard = payload.get("by_standard") or []
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "scanned_standards": totals.get("scanned_standards"),
        "standards_total": totals.get("standards_total"),
        "standards_pending_coverage": totals.get("standards_pending_coverage"),
        "average_known_compliance_rate": totals.get("average_known_compliance_rate"),
        "ready_now_count": len(worklist.get("ready_now") or []),
        "deferred_count": len(worklist.get("deferred_until_scanner_authored") or []),
        "ready_now": worklist.get("ready_now") or [],
        "by_standard_summary": [
            {
                "standard_id": row.get("standard_id"),
                "compliance_rate": row.get("compliance_rate"),
                "noncompliant_artifact_count": row.get("noncompliant_artifact_count"),
                "metabolism_trigger_state": row.get("metabolism_trigger_state"),
            }
            for row in by_standard if isinstance(row, dict)
        ],
    }


def _summarize_standard_skill_map(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "codex/hologram/skills/standard_skill_map.json"
    payload = _read_json_safe(path)
    if not payload:
        return {"available": False, "reason": "standard-skill map not built", "path": "codex/hologram/skills/standard_skill_map.json"}
    totals = payload.get("totals") or {}
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "standards_total": totals.get("standards_total"),
        "paired_explicit": totals.get("paired_explicit"),
        "tool_only_no_skill_required": totals.get("tool_only_no_skill_required"),
        "missing_authoring_skill": totals.get("missing_authoring_skill"),
        "skills_with_governing_standard_ids": totals.get("skills_with_governing_standard_ids"),
        "skills_total_inventoried": totals.get("skills_total_inventoried"),
    }


def _summarize_compute_audit(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "codex/hologram/compute/audit.json"
    payload = _read_json_safe(path)
    if not payload:
        return {"available": False, "reason": "compute audit not built"}
    summary = payload.get("summary") or {}
    by_severity = summary.get("by_severity") or {}
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "finding_count": summary.get("finding_count"),
        "by_severity": by_severity,
        "model_row_count": summary.get("model_row_count"),
        "provider_count": summary.get("provider_count"),
        "route_preview_count": summary.get("route_preview_count"),
    }


def _summarize_compute_workers(repo_root: Path) -> dict[str, Any]:
    cw = repo_root / "state/compute_workers"
    receipts = cw / "receipts"
    row_patches = cw / "row_patches"
    transform_jobs = cw / "transform_jobs"
    return {
        "available": cw.is_dir(),
        "receipts_count": _safe_count_files(receipts),
        "row_patches_count": _safe_count_files(row_patches),
        "transform_jobs_count": _safe_count_files(transform_jobs),
        "state_root": "state/compute_workers",
    }


def _summarize_active_phase(repo_root: Path) -> dict[str, Any]:
    live = repo_root / "codex/doctrine/agent_bootstrap_live.json"
    payload = _read_json_safe(live)
    live_bindings = (payload or {}).get("live_bindings") if isinstance(payload, dict) else {}
    pipeline = (payload or {}).get("pipeline") if isinstance(payload, dict) else {}
    actor = (payload or {}).get("actor") if isinstance(payload, dict) else {}
    directive = (payload or {}).get("directive") if isinstance(payload, dict) else {}
    live_source = live_bindings if isinstance(live_bindings, dict) else pipeline if isinstance(pipeline, dict) else {}
    explicit = load_explicit_active_phase(repo_root) or {}
    phase_index = _read_json_safe(repo_root / "codex/derived/phase_index.json") or {}
    active_lanes = _read_json_safe(repo_root / _ACTIVE_LANES_PATH) or {}

    # Constitutional rule: latest explicit phase_family.json activation wins.
    # Stale projections (agent_bootstrap_live.json, active_lanes.json, phase_index.json)
    # may enrich runtime fields but must not override the family-marker activation.
    active_phase_id = (
        explicit.get("phase_id")
        or live_source.get("active_phase_id")
        or active_lanes.get("active_phase_anchor")
        or phase_index.get("active_phase_id")
    )
    active_phase_number = (
        explicit.get("phase_number")
        or live_source.get("active_phase_number")
        or phase_index.get("active_phase_number")
    )
    active_phase_title = (
        explicit.get("phase_title")
        or live_source.get("active_phase_title")
        or active_lanes.get("active_phase_title")
    )
    active_phase_dir = explicit.get("phase_dir") or live_source.get("active_phase_dir")
    source_order = [
        "phase_activation.load_explicit_active_phase",
        "agent_bootstrap_live.json::live_bindings",
        "state/phase_lanes/active_lanes.json::active_phase_anchor",
        "codex/derived/phase_index.json",
    ]
    resolved_from = None
    if explicit.get("phase_id"):
        resolved_from = source_order[0]
    elif live_source.get("active_phase_id"):
        resolved_from = source_order[1]
    elif active_lanes.get("active_phase_anchor"):
        resolved_from = source_order[2]
    elif phase_index.get("active_phase_id"):
        resolved_from = source_order[3]

    if not payload and not explicit and not active_lanes and not phase_index:
        return {
            "available": False,
            "reason": "no active phase sources available",
            "resolution_sources_checked": source_order,
        }
    active_directive_path = _existing_repo_relative_path(
        repo_root,
        live_source.get("active_directive_path")
        or (directive.get("path") if isinstance(directive, dict) else None),
    )

    return {
        "available": True,
        "active_phase_id": active_phase_id,
        "active_phase_number": active_phase_number,
        "active_phase_title": active_phase_title,
        "active_phase_dir": active_phase_dir,
        "factory_state": {
            "role": live_source.get("factory_state_role"),
            "freshness": live_source.get("factory_state_freshness"),
            "live": live_source.get("factory_state_live"),
            "stage": live_source.get("factory_stage") if live_source.get("factory_state_live") else None,
            "last_run": live_source.get("factory_last_run"),
        },
        "actor_id": actor.get("actor_id") if isinstance(actor, dict) else None,
        "actor_role": actor.get("role") if isinstance(actor, dict) else None,
        "active_directive_path": active_directive_path,
        "resolved_from": resolved_from,
        "resolution_sources_checked": source_order,
    }


def _summarize_blackboard_advisory(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Per pri_133, treat the blackboard's coordination signals as
      advisory by default. The snapshot reports collision count and stale
      fingerprint count as observations, NOT as locks; agents should verify
      session liveness before treating any "claimed" path as a current lock.
    """
    bb = repo_root / "state/metabolism/blackboard.md"
    if not bb.is_file():
        return {
            "available": False,
            "reason": "blackboard.md not generated",
            "advisory_note": "see pri_133 ceremony_friction_audit; coordination ceremony is advisory by default.",
        }
    try:
        text = bb.read_text(encoding="utf-8")
    except OSError:
        return {"available": False, "reason": "blackboard read failed"}
    lines = text.splitlines()
    advisory_section_start = None
    for idx, line in enumerate(lines):
        if line.startswith("## Files touched by recent sessions") or line.startswith("## Do not duplicate"):
            advisory_section_start = idx
            break
    advisory_count = 0
    if advisory_section_start is not None:
        for line in lines[advisory_section_start + 1:]:
            if line.startswith("##"):
                break
            if line.startswith("- ") and "no recent overlaps" not in line and "no active collisions" not in line:
                advisory_count += 1
    active_agent_count = sum(1 for line in lines if line.startswith("- `claude:") or line.startswith("- `codex:"))
    return {
        "available": True,
        "advisory_collision_count": advisory_count,
        "active_agent_count_advisory": active_agent_count,
        "advisory_note": (
            "Per pri_133 ceremony_friction_audit: this is ADVISORY only. Verify session liveness "
            "via claim_expires_at before treating any path as locked. Stale 4h-old fingerprints "
            "have historically been misread as concurrent active sessions; the deep-cause TTL "
            "fix (system/lib/metabolism_store.py blackboard_claim_ttl_seconds 14400 -> 600) "
            "shipped 2026-04-28."
        ),
    }


def _ceremony_budget_for_action(
    *,
    action_kind: str,
    command: str = "",
    write_paths: list[str] | None = None,
    mutation: bool = False,
    live_effect: bool = False,
    autonomous_effect: bool = False,
    provider_effect: bool = False,
    private_payload_effect: bool = False,
    lifecycle_effect: bool = False,
    source_promotion_effect: bool = False,
    preview_only: bool = False,
    risk_hints: list[str] | None = None,
    performed_steps: list[str] | None = None,
) -> dict[str, Any]:
    def _repo_rel(path: str) -> str:
        text = str(path or "").strip()
        if not text:
            return ""
        try:
            path_obj = Path(text).expanduser()
            if path_obj.is_absolute():
                try:
                    text = path_obj.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
                except ValueError:
                    text = path_obj.as_posix()
        except (OSError, RuntimeError, ValueError):
            pass
        return text.replace("\\", "/").removeprefix("./").lower()

    paths = [_repo_rel(str(path)) for path in (write_paths or []) if str(path or "").strip()]
    hints = [str(hint) for hint in (risk_hints or []) if str(hint or "").strip()]
    haystack = " ".join([action_kind, command, *paths, *hints]).lower()
    risk_factors: list[str] = []
    effect_kinds: list[str] = []
    score = 0

    if mutation:
        score += 2
        risk_factors.append("mutation_requested")
        effect_kinds.append("source_mutation")
    if paths:
        score += 1
        risk_factors.append("write_scope_declared")

    authority_prefixes = (
        "agents.md",
        "agents.override.md",
        "claude.md",
        "codex.md",
        "kernel.py",
        "codex/standards/",
        "codex/doctrine/",
        "system/lib/kernel",
        "system/lib/seed_pipeline_controller.py",
        "system/lib/campaign_router.py",
        "tools/meta/control/",
        "tools/meta/factory/work_ledger.py",
    )
    if any(path.lower().startswith(authority_prefixes) for path in paths):
        score += 4
        risk_factors.append("authority_surface_write")
        effect_kinds.append("authority_surface_change")
    if any(path.lower().endswith(".py") for path in paths):
        score += 2
        risk_factors.append("runtime_source_write")
        effect_kinds.append("runtime_source_change")
    if any(path.lower().endswith(".md") for path in paths) and not any(
        path.lower().startswith(("codex/doctrine/", "agents", "claude.md", "codex.md"))
        for path in paths
    ):
        score = max(1, score - 1)
        risk_factors.append("docs_only_or_note_write")
        effect_kinds.append("docs_or_note_write")
    lifecycle_hint = "phase-assimilate" in haystack or "phase_step" in haystack or "phase-step" in haystack
    if lifecycle_effect or (lifecycle_hint and not preview_only):
        score += 3
        risk_factors.append("phase_lifecycle_change")
        effect_kinds.append("phase_lifecycle_effect")
    autonomous_hint = (
        "reaction" in haystack
        or "metabolismd" in haystack
        or "launchd" in haystack
        or "daemon" in haystack
    )
    if autonomous_effect or (autonomous_hint and not preview_only):
        score += 4
        risk_factors.append("autonomous_runtime_or_runner")
        effect_kinds.append("autonomous_runtime_effect")
    if provider_effect or private_payload_effect or "provider" in haystack or "paid" in haystack or "private_payload" in haystack:
        score += 2
        risk_factors.append("provider_or_private_payload_boundary")
        if provider_effect or "provider" in haystack or "paid" in haystack:
            effect_kinds.append("provider_effect")
        if private_payload_effect or "private_payload" in haystack:
            effect_kinds.append("private_payload_effect")
    if live_effect:
        score += 2
        risk_factors.append("live_effect")
        effect_kinds.append("live_effect")
    if source_promotion_effect:
        score += 3
        risk_factors.append("source_promotion_effect")
        effect_kinds.append("source_promotion_effect")
    if "dirty_tree_broad" in hints:
        score += 2
        risk_factors.append("broad_dirty_tree_context")
    if "lifecycle_disagreement" in hints:
        score += 2
        risk_factors.append("lifecycle_state_disagreement")

    read_only = (
        not mutation
        and not paths
        and not live_effect
        and not autonomous_effect
        and not provider_effect
        and not private_payload_effect
        and not lifecycle_effect
        and not source_promotion_effect
        and not lifecycle_hint
        and not autonomous_hint
        and action_kind in {
        "phase_continue",
        "compliance_ready_work",
        "standard_skill_pairing_gap",
        "rung_1_drilldown",
        "rung_2_drilldown",
        }
    )
    if read_only:
        tier = "tier_0_observe_only"
        score = 0
        risk_factors = ["read_only_navigation"]
        effect_kinds = ["read_only_navigation"]
        required_steps = ["run_command_or_read_packet"]
        skippable_steps = ["claim", "lease", "broad_tests", "receipt", "closeout"]
        required_proof = ["command_output_or_snapshot_section"]
        claim_policy = "none"
        test_policy = "none"
        receipt_policy = "none"
        approval_policy = "none"
        rollback = "not_applicable_read_only"
    elif "autonomous_runtime_or_runner" in risk_factors:
        tier = "tier_4_critical_autonomy"
        required_steps = [
            "full_claim",
            "human_or_controller_approval",
            "dry_run_or_preview",
            "stop_condition",
            "runtime_monitoring",
            "post_run_receipt",
        ]
        skippable_steps = []
        required_proof = ["approval_record", "stop_or_rollback_command", "runtime_ledger_row", "post_run_status"]
        claim_policy = "required"
        test_policy = "targeted_plus_runtime_smoke"
        receipt_policy = "required"
        approval_policy = "required_before_live"
        rollback = "explicit_stop_flag_or_daemon_disable_path_required"
    elif "phase_lifecycle_change" in risk_factors or score >= 6:
        tier = "tier_3_high_authority"
        required_steps = [
            "target_scope_claim",
            "dirty_tree_ownership_check",
            "targeted_tests",
            "adjacent_route_validation",
            "receipt_or_checkpoint",
            "local_to_general_closeout",
        ]
        skippable_steps = ["full_observe_plan_unless_needed"]
        required_proof = ["targeted_test_output", "route_or_lifecycle_state", "diff_or_receipt"]
        claim_policy = "required_for_mutation"
        test_policy = "targeted_plus_adjacent"
        receipt_policy = "required"
        approval_policy = "preview_or_controller_gate_for_live_lifecycle_changes"
        rollback = "name_recovery_command_or_revert_scope_before_live"
    elif score >= 3:
        tier = "tier_2_normal_bounded"
        required_steps = ["targeted_context_check", "targeted_tests_or_cli_validation", "diff_review"]
        skippable_steps = ["full_cold_start_bootstrap", "broad_test_suite", "full_governance_closeout"]
        required_proof = ["targeted_validation_output", "bounded_diff"]
        claim_policy = "claim_if_work_ledger_or_campaign_expects_mutation"
        test_policy = "affected_surface_only"
        receipt_policy = "commit_or_short_receipt"
        approval_policy = "none_unless_write_guard_blocks"
        rollback = "local_revert_of_touched_paths"
    else:
        tier = "tier_1_standard_low"
        required_steps = ["targeted_validation", "diff_check"]
        skippable_steps = ["claim", "lease", "broad_tests", "full_closeout"]
        required_proof = ["targeted_validation_output"]
        claim_policy = "optional_unless_collision"
        test_policy = "single_targeted_check"
        receipt_policy = "commit_message_or_short_note"
        approval_policy = "none"
        rollback = "simple_local_revert"

    performed = [str(step) for step in (performed_steps or []) if str(step or "").strip()]
    missing = [step for step in required_steps if step not in performed]
    return {
        "schema_version": "ceremony_budget_v0",
        "classifier_version": "ceremony_budget_heuristic_v0",
        "tier": tier,
        "risk_score": score,
        "risk_factors": risk_factors,
        "effect_kinds": list(dict.fromkeys(effect_kinds)),
        "required_steps": required_steps,
        "performed_steps": performed,
        "missing_steps": missing,
        "skippable_steps": skippable_steps,
        "required_proof": required_proof,
        "claim_policy": claim_policy,
        "test_policy": test_policy,
        "receipt_policy": receipt_policy,
        "approval_policy": approval_policy,
        "rollback_or_recovery": rollback,
        "source_refs": [
            "codex/standards/std_apply.json::target_routing.trust_tiers",
            "codex/standards/std_agent_entry_surface.json::common_sense_helpfulness_floor",
            "codex/doctrine/paper_modules/workitem_spine_operating_practice.md::Claim",
            "tools/meta/control/reactions_engine.py",
        ],
    }


def _entry_route_lease(
    *,
    task_text: str,
    selected_lane: dict[str, Any],
    next_action: dict[str, Any],
    active_phase: dict[str, Any],
    python_target_resolution: dict[str, Any],
    navigation_index_spine: dict[str, Any] | None,
) -> dict[str, Any]:
    known_paths: list[str] = []
    for row in python_target_resolution.get("files") or []:
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            known_paths.append(row["path"])
    for row in python_target_resolution.get("scopes") or []:
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            known_paths.append(row["path"])
    known_paths = list(dict.fromkeys(path for path in known_paths if path))

    currentness = (
        navigation_index_spine.get("currentness")
        if isinstance(navigation_index_spine, dict) and isinstance(navigation_index_spine.get("currentness"), dict)
        else {}
    )
    source_coupling = (
        navigation_index_spine.get("source_coupling")
        if isinstance(navigation_index_spine, dict) and isinstance(navigation_index_spine.get("source_coupling"), dict)
        else {}
    )

    task_hash = _stable_json_fingerprint({"task": task_text})[:12]
    lane_id = str(selected_lane.get("lane_id") or "unknown")
    lease_id = f"entry:{lane_id}:{task_hash}"
    return {
        "schema_version": "route_lease_v0",
        "lease_id": lease_id,
        "issued_by": "kernel.entry_packet",
        "mode_contract": "control_plane_handoff_to_data_plane_execution",
        "task_hash": task_hash,
        "selected_lane_id": lane_id,
        "route_reason": selected_lane.get("reason"),
        "known_authority_surfaces": [
            "codex/standards/std_agent_entry_surface.json::common_sense_helpfulness_floor.kernel_reliance_calibration",
            "codex/doctrine/agent_bootstrap.json::kernel_reliance_calibration",
        ],
        "known_paths": known_paths[:8],
        "permitted_direct_actions": [
            "read_known_paths",
            "rg_known_scope",
            "git_status_or_diff_for_owned_paths",
            "help_output_for_named_commands",
            "py_compile_named_python_files",
            "focused_pytest_or_builder_check",
            "import_profile_named_kernel_route",
            "scoped_patch_owned_paths",
        ],
        "requires_kernel_when": [
            "authority_surface_unknown",
            "freshness_or_source_coupling_blocks_decision",
            "route_or_artifact_kind_unknown",
            "active_phase_or_runtime_state_needed",
            "mutation_blast_radius_expands",
            "bounded_cross_kind_context_needed",
            "exact_refresh_or_projection_rebuild_needed",
        ],
        "do_not_call_kernel_for": [
            "grep_or_string_search_inside_known_scope",
            "direct_file_read_for_known_path",
            "git_status_or_diff",
            "test_or_py_compile_result",
            "command_help_output",
            "import_offender_check",
            "obvious_reversible_scoped_edit",
        ],
        "return_to_kernel_when": [
            "next_action_command_no_longer_matches_task",
            "selected_lane_changes_or_conflicts_with_evidence",
            "new_path_or_write_scope_crosses_authority_boundary",
            "projection_currentness_is_stale_and_the_decision_depends_on_it",
            "workitem_or_active_phase_state_changes_materially",
        ],
        "invalidation_inputs": {
            "active_phase_id": active_phase.get("phase_id"),
            "next_action_command": next_action.get("command"),
            "python_target_resolution_status": python_target_resolution.get("status"),
            "navigation_index_currentness": currentness.get("status"),
            "navigation_index_source_coupling": source_coupling.get("status"),
        },
        "budget": {
            "max_kernel_calls_before_direct_action": 1,
            "second_kernel_call_requires_kernel_shaped_reason": True,
            "direct_action_first_for_known_path_questions": True,
        },
        "diagnostics": {
            "kernel_call_reason": "route",
            "kernel_call_budget_status": "entry_lease_issued",
            "process_audit_signal_candidate": "second_kernel_call_before_direct_action",
        },
    }


def _suppress_python_unresolved_for_selected_workitem(
    python_target_resolution: dict[str, Any],
    selected_workitem: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(selected_workitem, dict):
        return dict(python_target_resolution)
    work_item_id = str(selected_workitem.get("id") or "").strip()
    if not work_item_id:
        return dict(python_target_resolution)

    unresolved = [
        row
        for row in list(python_target_resolution.get("unresolved") or [])
        if isinstance(row, dict)
    ]
    if not unresolved:
        return dict(python_target_resolution)

    kept: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for row in unresolved:
        if str(row.get("kind") or "") == "python_scope" and str(row.get("id") or "") == work_item_id:
            suppressed.append(dict(row))
            continue
        kept.append(dict(row))
    if not suppressed:
        return dict(python_target_resolution)

    out = dict(python_target_resolution)
    out["unresolved"] = kept
    detected = (
        dict(python_target_resolution.get("detected") or {})
        if isinstance(python_target_resolution.get("detected"), dict)
        else {}
    )
    if isinstance(detected.get("symbol_names"), list):
        detected["symbol_names"] = [
            str(item)
            for item in detected.get("symbol_names") or []
            if str(item) != work_item_id
        ]
    out["detected"] = detected
    out["suppressed_by_selected_workitem"] = [
        {
            "id": str(row.get("id") or ""),
            "reason": "entry_selected_exact_task_ledger_workitem",
        }
        for row in suppressed
    ]
    if not out.get("files") and not out.get("scopes") and not kept:
        out["status"] = "no_python_target"
    elif kept:
        out["status"] = "unresolved"
    else:
        out["status"] = "resolved"
    return out


def _compact_entry_navigation_index_spine(
    navigation_index_spine: dict[str, Any] | None,
    *,
    task_text: str,
    context_budget: int,
) -> dict[str, Any] | None:
    """Return the entry-facing control handoff for the navigation index."""
    if not isinstance(navigation_index_spine, dict):
        return None

    def pick(payload: Any, keys: tuple[str, ...]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        return {
            key: payload.get(key)
            for key in keys
            if payload.get(key) not in (None, "", [], {})
        }

    def compact_opening(row: Any) -> dict[str, Any] | None:
        compact = pick(
            row,
            (
                "kind_id",
                "title",
                "command",
                "surface_role",
                "allowed_after",
                "reason",
                "matched_intent_id",
                "gap_count",
            ),
        )
        return compact or None

    def compact_step(row: Any) -> dict[str, Any] | None:
        compact = pick(
            row,
            (
                "step_id",
                "order",
                "command",
                "surface_role",
                "kind_id",
                "allowed_after",
                "required",
            ),
        )
        proof = row.get("proof") if isinstance(row, dict) and isinstance(row.get("proof"), dict) else {}
        if proof:
            compact["proof"] = pick(proof, ("emits", "success_check"))
        return compact or None

    def compact_group(row: Any) -> dict[str, Any] | None:
        compact = pick(
            row,
            (
                "group_id",
                "label",
                "kind_count",
                "row_level_gap_count",
                "coverage_status",
                "entry_policy",
            ),
        )
        if isinstance(row, dict):
            top_gap_kind_ids = list(row.get("top_gap_kind_ids") or [])[:4]
            if top_gap_kind_ids:
                compact["top_gap_kind_ids"] = top_gap_kind_ids
            openings = [
                item
                for item in (compact_opening(opening) for opening in list(row.get("recommended_openings") or [])[:1])
                if item
            ]
            if openings:
                compact["recommended_openings"] = openings
        return compact or None

    def compact_gap(row: Any) -> dict[str, Any] | None:
        return pick(
            row,
            (
                "kind_id",
                "entity_id",
                "title",
                "gap_count",
                "atlas_materialization_status",
                "support_status",
                "source_drilldown_command",
                "atlas_card_command",
            ),
        ) or None

    task_arg = shlex.quote(task_text) if task_text else "<task>"
    context_pack_command = (
        f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if task_text
        else "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000"
    )
    route_digest = (
        navigation_index_spine.get("route_digest")
        if isinstance(navigation_index_spine.get("route_digest"), dict)
        else {}
    )
    coverage_receipt = (
        navigation_index_spine.get("coverage_closure_receipt")
        if isinstance(navigation_index_spine.get("coverage_closure_receipt"), dict)
        else {}
    )
    kind_group_rollup = (
        navigation_index_spine.get("kind_group_rollup")
        if isinstance(navigation_index_spine.get("kind_group_rollup"), dict)
        else {}
    )
    entry_intent_openings = (
        navigation_index_spine.get("entry_intent_openings")
        if isinstance(navigation_index_spine.get("entry_intent_openings"), dict)
        else {}
    )
    task_conditioned = (
        entry_intent_openings.get("task_conditioned")
        if isinstance(entry_intent_openings.get("task_conditioned"), dict)
        else {}
    )
    reentry_receipt = (
        task_conditioned.get("reentry_receipt")
        if isinstance(task_conditioned.get("reentry_receipt"), dict)
        else {}
    )
    matched_intent_ids = (
        list(task_conditioned.get("matched_intent_ids") or [])
        or list(reentry_receipt.get("matched_intent_ids") or [])
    )
    source_coupling = (
        navigation_index_spine.get("source_coupling")
        if isinstance(navigation_index_spine.get("source_coupling"), dict)
        else {}
    )
    changed_sources = list(source_coupling.get("changed_sources") or [])
    compact_source_coupling = pick(
        source_coupling,
        (
            "status",
            "changed_source_count",
            "safe_to_commit_generated_outputs_without_sources",
            "reason",
        ),
    )
    if changed_sources:
        compact_source_coupling["changed_sources"] = [
            pick(row, ("source_id", "path", "current_count", "previous_count"))
            for row in changed_sources[:4]
            if isinstance(row, dict)
        ]
        compact_source_coupling["changed_sources_omitted"] = max(0, len(changed_sources) - 4)

    selected_openings = [
        item
        for item in (
            compact_opening(opening)
            for opening in list(task_conditioned.get("selected_openings") or [])[:2]
        )
        if item
    ]
    selected_opening_kind_ids = [
        str(opening.get("kind_id") or "")
        for opening in list(task_conditioned.get("selected_openings") or [])[:5]
        if isinstance(opening, dict) and str(opening.get("kind_id") or "").strip()
    ]
    handoff_sequence = [
        item
        for item in (
            compact_step(step)
            for step in list(task_conditioned.get("handoff_sequence") or [])[:3]
        )
        if item
    ]
    groups = [
        item
        for item in (compact_group(group) for group in list(kind_group_rollup.get("groups") or [])[:2])
        if item
    ]
    top_projection_gaps = [
        item
        for item in (
            compact_gap(row)
            for row in list(navigation_index_spine.get("top_projection_gaps") or [])[:3]
        )
        if item
    ]
    legal_drilldowns = list(navigation_index_spine.get("legal_drilldowns") or [])[:3]
    coverage_matrix_command = coverage_receipt.get("matrix_command")
    evidence_drilldowns = [
        {
            "command": context_pack_command,
            "surface_role": CONTROL_ENTRY,
            "reason": "Fetch the bounded evidence packet after the entry handoff.",
        },
        {
            "command": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
            "surface_role": ATLAS_PROJECTION,
            "reason": "Browse System Atlas clusters after entry/context selects atlas orientation.",
        },
        {
            "command": "./repo-python kernel.py --paper-module system_self_comprehension_root",
            "surface_role": DRILLDOWN,
            "reason": "Open the self-comprehension authority root when the task needs prose evidence.",
        },
    ]
    if coverage_matrix_command:
        evidence_drilldowns.append(
            {
                "command": coverage_matrix_command,
                "surface_role": CONTROL_ENTRY,
                "reason": "Audit behavior-watch closure without expanding the entry packet.",
            }
        )

    return {
        "schema_version": "navigation_index_spine_entry_handoff_v0",
        "source_schema_version": navigation_index_spine.get("schema_version"),
        "surface_role": navigation_index_spine.get("surface_role"),
        "authority_posture": navigation_index_spine.get("authority_posture"),
        "available": navigation_index_spine.get("available"),
        "output_profile": "entry_control_handoff_compact",
        "summary": pick(
            navigation_index_spine.get("summary"),
            (
                "artifact_kind_count",
                "total_browsable_row_count",
                "system_atlas_entity_count",
                "row_level_projection_gap_count",
                "coverage_surface_available_count",
                "coverage_surface_resolution_kind_count",
                "kind_atlas_coverage_surface_available_count",
                "standard_type_plane_resolved_surface_count",
                "coverage_surface_gap_count",
                "coverage_closure_status",
                "high_cardinality_kind_count",
                "high_cardinality_clustered_count",
                "kind_group_count",
                "entry_intent_count",
                "task_conditioned_opening_count",
                "top_gap_group_id",
            ),
        ),
        "route_digest": pick(
            route_digest,
            (
                "schema_version",
                "kind_atlas_available",
                "entry_visible_kind_count",
                "coverage_surface_available_count",
                "coverage_surface_gap_count",
                "high_cardinality_cluster_gap_count",
                "control_entry_allowed_kind_count",
                "first_contact_policy",
            ),
        ),
        "coverage_closure": pick(
            coverage_receipt,
            (
                "schema_version",
                "status",
                "coverage_surface_available_count",
                "coverage_surface_resolution_kind_count",
                "kind_atlas_coverage_surface_available_count",
                "standard_type_plane_resolved_surface_count",
                "coverage_surface_resolution_sources",
                "coverage_surface_gap_count",
                "high_cardinality_cluster_gap_count",
                "control_entry_allowed_kind_count",
                "coverage_count_policy",
                "coverage_is_not_permission",
                "behavior_watch_status",
                "matrix_command",
                "watch_row_selector",
                "watch_closure_success_check",
            ),
        ),
        "kind_group_summary": {
            "schema_version": kind_group_rollup.get("schema_version"),
            "group_count": kind_group_rollup.get("group_count"),
            "top_groups": groups,
        },
        "task_conditioned_openings": {
            "matched_intent_ids": matched_intent_ids[:4],
            "first_opening": compact_opening(task_conditioned.get("first_opening")),
            "selected_openings": selected_openings,
            "selected_opening_kind_ids": selected_opening_kind_ids,
            "selected_opening_count": task_conditioned.get("selected_opening_count"),
            "handoff_sequence": handoff_sequence,
            "reentry_receipt": pick(
                reentry_receipt,
                (
                    "schema_version",
                    "status",
                    "task_bound",
                    "first_kind_id",
                    "first_command",
                    "handoff_step_count",
                ),
            ),
        },
        "top_projection_gaps": top_projection_gaps,
        "legal_drilldowns": legal_drilldowns,
        "entry_policy": navigation_index_spine.get("entry_policy"),
        "currentness": navigation_index_spine.get("currentness"),
        "source_coupling": compact_source_coupling,
        "source_refs": list(navigation_index_spine.get("source_refs") or [])[:4],
        "evidence_drilldowns": evidence_drilldowns,
        "omission_receipt": {
            "omitted": [
                "full kind_group_rollup.groups",
                "full entry_intent_openings catalog",
                "coverage_closure_receipt.watch_drilldown_sequence",
                "coverage_closure_receipt.coverage_watch_snapshot",
                "full SystemAtlas changed source rows after first 4",
            ],
            "reason": (
                "Entry is a compact control handoff; evidence belongs in context-pack, "
                "option surfaces, or explicit drilldowns."
            ),
            "context_pack_command": context_pack_command,
            "system_atlas_cluster_command": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
            "system_self_comprehension_root_command": "./repo-python kernel.py --paper-module system_self_comprehension_root",
        },
    }


def _compact_entry_opening(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    keys = (
        "kind_id",
        "title",
        "command",
        "surface_role",
        "allowed_after",
        "reason",
        "matched_intent_id",
        "gap_count",
    )
    compact = {key: row.get(key) for key in keys if row.get(key) not in (None, "", [], {})}
    return compact or None


def _compact_entry_navigation_index_spine_for_admission(
    navigation_index_spine: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(navigation_index_spine, dict):
        return None

    compact = dict(navigation_index_spine)
    task_openings = compact.get("task_conditioned_openings")
    if isinstance(task_openings, dict):
        selected_openings = [
            row
            for row in (
                _compact_entry_opening(opening)
                for opening in list(task_openings.get("selected_openings") or [])[:2]
            )
            if row
        ]
        omitted = list(task_openings.get("omitted_for_entry_admission") or [])
        if task_openings.get("handoff_sequence"):
            omitted.append("task_conditioned_openings.handoff_sequence")
        compact["task_conditioned_openings"] = {
            "matched_intent_ids": list(task_openings.get("matched_intent_ids") or [])[:4],
            "first_opening": _compact_entry_opening(task_openings.get("first_opening")),
            "selected_openings": selected_openings,
            "selected_opening_kind_ids": list(task_openings.get("selected_opening_kind_ids") or [])[:5],
            "selected_opening_count": (
                task_openings.get("selected_opening_count")
                or len(task_openings.get("selected_openings") or [])
            ),
            "reentry_receipt": task_openings.get("reentry_receipt"),
            "omitted_for_entry_admission": omitted,
        }

    kind_summary = compact.get("kind_group_summary")
    if isinstance(kind_summary, dict):
        top_groups = []
        for group in list(kind_summary.get("top_groups") or [])[:2]:
            if not isinstance(group, dict):
                continue
            top_groups.append(
                {
                    key: group.get(key)
                    for key in (
                        "group_id",
                        "label",
                        "kind_count",
                        "row_level_gap_count",
                        "coverage_status",
                        "entry_policy",
                        "top_gap_kind_ids",
                    )
                    if group.get(key) not in (None, "", [], {})
                }
            )
        compact["kind_group_summary"] = {
            "schema_version": kind_summary.get("schema_version"),
            "group_count": kind_summary.get("group_count"),
            "top_groups": top_groups,
            "omitted_for_entry_admission": [
                "top_groups[].recommended_openings",
                "full group list after first 2",
            ],
        }

    if isinstance(compact.get("coverage_closure"), dict):
        coverage = compact["coverage_closure"]
        compact["coverage_closure"] = {
            key: coverage.get(key)
            for key in (
                "schema_version",
                "status",
                "coverage_surface_available_count",
                "coverage_surface_gap_count",
                "coverage_count_policy",
                "coverage_is_not_permission",
                "behavior_watch_status",
                "matrix_command",
                "watch_row_selector",
                "watch_closure_success_check",
            )
            if coverage.get(key) not in (None, "", [], {})
        }

    evidence_drilldowns = list(compact.get("evidence_drilldowns") or [])
    if evidence_drilldowns:
        compact["evidence_drilldowns"] = evidence_drilldowns[:2]
        compact["evidence_drilldowns_omitted_for_entry_admission"] = max(
            0, len(evidence_drilldowns) - 2
        )
    compact["admission_trimmed_for_entry_packet"] = True
    omission = compact.get("omission_receipt")
    if isinstance(omission, dict):
        omitted = list(omission.get("omitted") or [])
        omitted.extend(
            [
                "entry admission trim: task_conditioned handoff sequence",
                "entry admission trim: repeated group recommended openings",
                "entry admission trim: extra evidence drilldowns",
            ]
        )
        compact["omission_receipt"] = {
            **omission,
            "omitted": omitted,
            "entry_admission_reason": (
                "Default --entry exceeded the inline target; non-decisive index detail "
                "stays behind context-pack and option-surface drilldowns."
            ),
        }
    return compact


def _hard_compact_entry_navigation_index_spine_for_admission(
    navigation_index_spine: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(navigation_index_spine, dict):
        return None
    task_openings = (
        navigation_index_spine.get("task_conditioned_openings")
        if isinstance(navigation_index_spine.get("task_conditioned_openings"), dict)
        else {}
    )
    summary = (
        navigation_index_spine.get("summary")
        if isinstance(navigation_index_spine.get("summary"), dict)
        else {}
    )
    gaps = [
        {
            key: row.get(key)
            for key in ("kind_id", "gap_count", "source_drilldown_command")
            if isinstance(row, dict) and row.get(key) not in (None, "", [], {})
        }
        for row in list(navigation_index_spine.get("top_projection_gaps") or [])[:1]
        if isinstance(row, dict)
    ]
    first_opening = _compact_entry_opening(task_openings.get("first_opening"))
    if isinstance(first_opening, dict):
        first_opening = {
            key: first_opening.get(key)
            for key in ("kind_id", "title", "command", "surface_role", "matched_intent_id")
            if first_opening.get(key) not in (None, "", [], {})
        }
    reentry_receipt = (
        task_openings.get("reentry_receipt")
        if isinstance(task_openings.get("reentry_receipt"), dict)
        else {}
    )
    currentness = (
        navigation_index_spine.get("currentness")
        if isinstance(navigation_index_spine.get("currentness"), dict)
        else {}
    )
    source_coupling = (
        navigation_index_spine.get("source_coupling")
        if isinstance(navigation_index_spine.get("source_coupling"), dict)
        else {}
    )
    return {
        "schema_version": navigation_index_spine.get("schema_version"),
        "source_schema_version": navigation_index_spine.get("source_schema_version"),
        "surface_role": navigation_index_spine.get("surface_role"),
        "authority_posture": navigation_index_spine.get("authority_posture"),
        "available": navigation_index_spine.get("available"),
        "output_profile": "entry_control_handoff_handle",
        "summary": {
            key: summary.get(key)
            for key in (
                "artifact_kind_count",
                "row_level_projection_gap_count",
                "coverage_surface_available_count",
                "coverage_surface_gap_count",
                "high_cardinality_kind_count",
                "task_conditioned_opening_count",
            )
            if summary.get(key) not in (None, "", [], {})
        },
        "task_conditioned_openings": {
            "matched_intent_ids": list(task_openings.get("matched_intent_ids") or [])[:4],
            "first_opening": first_opening,
            "selected_opening_kind_ids": list(task_openings.get("selected_opening_kind_ids") or [])[:5],
            "selected_opening_count": task_openings.get("selected_opening_count"),
            "reentry_receipt": {
                key: reentry_receipt.get(key)
                for key in ("status", "first_kind_id", "first_command")
                if reentry_receipt.get(key) not in (None, "", [], {})
            },
        },
        "top_projection_gaps": gaps,
        "entry_policy": {
            key: (navigation_index_spine.get("entry_policy") or {}).get(key)
            for key in ("cold_start_control_entry", "atlas_as_control_entry")
            if isinstance(navigation_index_spine.get("entry_policy"), dict)
            and (navigation_index_spine.get("entry_policy") or {}).get(key) not in (None, "", [], {})
        },
        "currentness": {
            key: currentness.get(key)
            for key in (
                "status",
                "source_coupling_status",
                "safe_to_commit_generated_outputs_without_sources",
                "freshness_command",
            )
            if currentness.get(key) not in (None, "", [], {})
        },
        "source_coupling": {
            key: source_coupling.get(key)
            for key in (
                "status",
                "changed_source_count",
                "safe_to_commit_generated_outputs_without_sources",
            )
            if source_coupling.get(key) not in (None, "", [], {})
        },
        "evidence_drilldowns": [
            {
                "command": "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
                "surface_role": CONTROL_ENTRY,
                "reason": "Open full index evidence.",
            },
            {
                "command": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                "surface_role": ATLAS_PROJECTION,
                "reason": "Browse Atlas clusters.",
            },
        ],
        "omission_receipt": {
            "omitted": [
                "route_digest",
                "coverage_closure details",
                "kind_group_summary",
                "task_conditioned handoff sequence",
                "legal_drilldowns after the first evidence routes",
                "full top_projection_gaps",
            ],
            "reason": (
                "Hard entry-admission handle: choose the first legal action and keep drilldowns."
            ),
            "drilldown": "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
        },
        "admission_trimmed_for_entry_packet": True,
        "hard_ceiling_handle_compacted": True,
    }


def _hard_compact_agent_operating_packet_for_admission(
    packet: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(packet, dict):
        return packet
    metrics = packet.get("metrics") if isinstance(packet.get("metrics"), dict) else {}
    compact = {
        key: packet.get(key)
        for key in (
            "kind",
            "schema_version",
            "status",
            "source_ref",
            "authority_posture",
            "global_principle_ids",
            "agent_principle_ids",
            "route",
            "agent_principles_route",
        )
        if packet.get(key) not in (None, "", [], {})
    }
    compact["metrics"] = {
        key: metrics.get(key)
        for key in ("entry_strip_bytes", "global_runtime_capsule_bytes", "compact_full_packet_bytes")
        if metrics.get(key) not in (None, "", [], {})
    }
    compact["omission_receipt"] = {
        "omitted": [
            "principle prose",
            "candidate axiom policy prose",
            "non-routing metric counters",
        ],
        "reason": "Hard entry admission keeps ids and owner routes; full operating packet is a drilldown.",
        "drilldown": packet.get("route"),
    }
    compact["trimmed_for_entry_admission"] = True
    compact["hard_ceiling_handle_compacted"] = True
    return compact


def _hard_compact_agent_principle_lens_for_admission(
    lens: dict[str, Any] | None,
    *,
    preserve_capture_reflex: bool = False,
) -> dict[str, Any] | None:
    if not isinstance(lens, dict):
        return lens
    invocation = lens.get("invocation") if isinstance(lens.get("invocation"), dict) else {}
    compact = {
        key: lens.get(key)
        for key in (
            "kind",
            "schema_version",
            "authority_posture",
            "status",
            "recognized_situation",
            "selected_lane_id",
            "selected_ids",
        )
        if lens.get(key) not in (None, "", [], {})
    }
    compact.update(
        {
            "row_count": len(lens.get("rows") or []),
            "invocation": {
                key: invocation.get(key)
                for key in ("selected_principle_cards", "agent_operating_packet")
                if invocation.get(key) not in (None, "", [], {})
            },
            "omission_receipt": {
                "omitted": [
                    "row cards; selected_ids carries the inline handle",
                    "row flags",
                    "scope ids",
                    "capture-reflex detail",
                    "authoring lane handles",
                ],
                "reason": (
                    "Hard entry admission keeps selected principle ids and card routes; "
                    "principle prose remains behind the selected card drilldown."
                ),
                "drilldown": invocation.get("selected_principle_cards"),
            },
            "trimmed_for_entry_admission": True,
            "hard_ceiling_handle_compacted": True,
        }
    )
    if preserve_capture_reflex and isinstance(lens.get("capture_reflex"), dict):
        compact["capture_reflex"] = lens.get("capture_reflex")
    return compact


def _hard_compact_entry_surface_diagnostics_for_admission(
    diagnostics: dict[str, Any] | None,
    *,
    preserve_observed_state: bool = False,
) -> dict[str, Any] | None:
    if not isinstance(diagnostics, dict):
        return diagnostics
    rows: list[dict[str, Any]] = []
    for row in list(diagnostics.get("rows") or []):
        if not isinstance(row, dict):
            continue
        target_surfaces = list(row.get("target_surfaces") or [])
        observed = row.get("observed_state") if isinstance(row.get("observed_state"), dict) else {}
        rows.append(
            {
                "diagnostic_id": row.get("diagnostic_id"),
                "severity": row.get("severity"),
                "is_hard_gate": row.get("is_hard_gate"),
                "target_surface_count": len(target_surfaces),
                "checker_module_ref": row.get("checker_module_ref"),
                "drilldown": (
                    "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py "
                    "&& ./repo-python tools/meta/factory/build_routing_projection.py --check"
                ),
            }
        )
        if preserve_observed_state:
            rows[-1]["observed_state"] = {
                key: observed.get(key)
                for key in (
                    "content_sync_mode",
                    "renderer_content_sync_deferred",
                    "generated_regions_match",
                    "generated_regions_match_status",
                    "generated_region_landing_safe",
                    "generated_region_landing_safe_status",
                )
                if key in observed
            }
    structural_triggers = []
    for trigger in list(diagnostics.get("structural_triggers") or [])[:2]:
        if not isinstance(trigger, dict):
            continue
        structural_triggers.append(
            {
                key: trigger.get(key)
                for key in ("trigger_id", "recognized_situation", "selected_lane_id")
                if trigger.get(key) not in (None, "", [], {})
            }
        )
    return {
        "triggered": diagnostics.get("triggered"),
        "matched_triggers": diagnostics.get("matched_triggers") or [],
        "matched_autonomy_phrases": diagnostics.get("matched_autonomy_phrases") or [],
        "trigger_source": diagnostics.get("trigger_source"),
        "severity_default": diagnostics.get("severity_default"),
        "non_blocking": diagnostics.get("non_blocking"),
        "diagnostic_family": diagnostics.get("diagnostic_family"),
        "structural_triggers": structural_triggers,
        "rows": rows,
        "count": len(rows),
        "trimmed_for_entry_admission": True,
        "hard_ceiling_handle_compacted": True,
        "omission_receipt": {
            "omitted": [
                "recommended_action prose",
                "observed_state detail",
                "governing standard refs",
                "target surface names",
                "candidate-pressure relationship prose",
            ],
            "reason": "Hard entry admission keeps diagnostic ids, gate posture, and checker routes.",
            "drilldown": (
                "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py "
                "&& ./repo-python tools/meta/factory/build_routing_projection.py --check"
            ),
        },
    }


def _compact_entry_surface_diagnostics_for_admission(
    diagnostics: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(diagnostics, dict):
        return diagnostics
    rows: list[dict[str, Any]] = []
    for row in list(diagnostics.get("rows") or []):
        if not isinstance(row, dict):
            continue
        observed = row.get("observed_state") if isinstance(row.get("observed_state"), dict) else {}
        rows.append(
            {
                key: row.get(key)
                for key in (
                    "diagnostic_id",
                    "target_surfaces",
                    "severity",
                    "recommended_action",
                    "governing_standard_ref",
                    "checker_module_ref",
                    "is_hard_gate",
                )
                if row.get(key) not in (None, "", [], {})
            }
            | {
                "observed_state": {
                    key: observed.get(key)
                    for key in (
                        "generated_region_marker_balance_ok",
                        "generated_regions_match_status",
                        "generated_region_landing_safe_status",
                        "renderer_content_sync",
                        "renderer_content_sync_deferred",
                        "content_sync_mode",
                    )
                    if observed.get(key) not in (None, "", [], {})
                },
                "omission_receipt": {
                    "omitted": [
                        "full marker findings",
                        "full renderer content check",
                        "full source worktree path list",
                    ],
                    "reason": (
                        "Entry packet admission keeps diagnostic routing and safety posture; "
                        "full evidence belongs in the deeper checker."
                    ),
                    "drilldown": (
                        "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py "
                        "&& ./repo-python tools/meta/factory/build_routing_projection.py --check"
                    ),
                },
            }
        )
    compact = {
        key: diagnostics.get(key)
        for key in (
            "triggered",
            "matched_triggers",
            "matched_autonomy_phrases",
            "structural_triggers",
            "trigger_source",
            "severity_default",
            "non_blocking",
            "non_blocking_warning",
            "source_module",
            "underlying_checker",
            "diagnostic_family",
            "diagnostic_family_owner_cap",
            "candidate_pressure_refs",
        )
        if diagnostics.get(key) not in (None, "", [], {})
    }
    for key in ("matched_triggers", "matched_autonomy_phrases"):
        if key in diagnostics and key not in compact:
            compact[key] = diagnostics.get(key)
    compact.update(
        {
            "rows": rows,
            "count": len(rows),
            "trimmed_for_entry_admission": True,
            "omission_receipt": {
                "omitted": [
                    "full entry_surface_diagnostics row observed_state",
                    "candidate_pressure_relationship prose",
                ],
                "reason": (
                    "Default --entry exceeded the inline target; compact diagnostics carry "
                    "row ids, hard-gate posture, and checker routes."
                ),
                "drilldown": (
                    "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py "
                    "&& ./repo-python tools/meta/factory/build_routing_projection.py --check"
                ),
            },
        }
    )
    return compact


def _compact_entry_workitem_handoff_for_admission(
    workitem: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(workitem, dict):
        return workitem
    dependency = workitem.get("dependency_status")
    compact = {
        key: workitem.get(key)
        for key in (
            "id",
            "title",
            "rank",
            "state",
            "work_item_type",
            "statement_snippet",
            "drilldown_command",
            "source_view",
            "dependency_summary",
        )
        if workitem.get(key) not in (None, "", [], {})
    }
    if isinstance(dependency, dict):
        compact["dependency_status"] = {
            key: dependency.get(key)
            for key in (
                "schedulable",
                "hard_dep_count",
                "unsatisfied_dep_ids",
                "dangling_dep_ids",
                "downstream_unlock_ids",
            )
            if dependency.get(key) not in (None, "", [], {})
        }
        compact["dependency_status"]["edge_details_omitted_for_entry_admission"] = True
    compact["omission_receipt"] = {
        "omitted": [
            "dependency_status.downstream_unlock_edges",
            "dependency_status.upstream_dependency_edges",
            "dependency_status.dependency_states",
            "dependency_status.anomaly_refs",
        ],
        "reason": (
            "Default --entry needs the schedulable handle and drilldown, not the full "
            "dependency neighborhood."
        ),
        "drilldown": compact.get("drilldown_command"),
    }
    return compact


def _hard_compact_entry_workitem_handoff_for_admission(
    workitem: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(workitem, dict):
        return workitem
    dependency = workitem.get("dependency_status")
    compact = {
        key: workitem.get(key)
        for key in (
            "id",
            "title",
            "rank",
            "state",
            "work_item_type",
            "drilldown_command",
        )
        if workitem.get(key) not in (None, "", [], {})
    }
    if isinstance(dependency, dict):
        compact["dependency_status"] = {
            key: dependency.get(key)
            for key in ("schedulable", "hard_dep_count")
            if dependency.get(key) not in (None, "", [], {})
        }
        compact["dependency_status"]["edge_details_omitted_for_entry_admission"] = True
    compact["omission_receipt"] = {
        "omitted": ["dependency edge detail", "source view", "statement snippet"],
        "drilldown": compact.get("drilldown_command"),
    }
    compact["hard_ceiling_handle_compacted"] = True
    return compact


def _compact_closeout_git_state_for_admission(
    closeout_git_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(closeout_git_state, dict):
        return closeout_git_state
    publication = (
        closeout_git_state.get("publication")
        if isinstance(closeout_git_state.get("publication"), dict)
        else {}
    )
    worktrees = (
        closeout_git_state.get("worktrees")
        if isinstance(closeout_git_state.get("worktrees"), dict)
        else {}
    )
    compact = {
        key: closeout_git_state.get(key)
        for key in (
            "schema",
            "source_schema",
            "status",
            "reason",
            "dirty_total",
            "staged_total",
            "ahead",
            "behind",
            "worktree_leases_clear",
            "closeout_ready",
            "clean_closeout_ready",
            "scoped_work_allowed",
        )
        if closeout_git_state.get(key) not in (None, "", [], {})
    }
    if isinstance(closeout_git_state.get("scoped_work_gate"), dict):
        gate = closeout_git_state["scoped_work_gate"]
        compact["scoped_work_gate"] = {
            key: gate.get(key)
            for key in (
                "status",
                "reason",
                "scoped_work_allowed",
                "normal_git_commit_allowed",
                "private_index_scoped_commit_allowed",
                "global_dirty_tree_blocks_scoped_work",
                "shared_index_blocks_private_index_scoped_commit",
                "required_lane",
                "mission_preflight_required",
                "policy",
            )
            if gate.get(key) not in (None, "", [], {})
        }
    compact["publication"] = {
        key: publication.get(key)
        for key in ("status", "reason", "audit_command")
        if publication.get(key) not in (None, "", [], {})
    }
    worktree_decision_keys = (
        "status",
        "reason",
        "linked_count",
        "dirty_linked_count",
        "dirty_status",
        "dirty_status_known",
        "dirty_unknown_count",
        "dirty_status_not_checked_count",
    )
    compact["worktrees"] = {
        key: worktrees.get(key)
        for key in worktree_decision_keys
        if worktrees.get(key) not in (None, "", [], {})
    }
    compact["recommended_lane"] = closeout_git_state.get("recommended_lane") or {}
    compact["drilldowns"] = closeout_git_state.get("drilldowns") or {}
    compact["trimmed_for_entry_admission"] = True
    compact["omission_receipt"] = {
        "omitted": ["conditions", "observed", "full linked worktree details"],
        "reason": "Entry admission keeps closeout decision fields and drilldowns only.",
        "drilldown": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions",
    }
    return compact


def _hard_compact_closeout_git_state_for_admission(
    closeout_git_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(closeout_git_state, dict):
        return closeout_git_state
    publication = (
        closeout_git_state.get("publication")
        if isinstance(closeout_git_state.get("publication"), dict)
        else {}
    )
    worktrees = (
        closeout_git_state.get("worktrees")
        if isinstance(closeout_git_state.get("worktrees"), dict)
        else {}
    )
    drilldowns = (
        closeout_git_state.get("drilldowns")
        if isinstance(closeout_git_state.get("drilldowns"), dict)
        else {}
    )
    return {
        "schema": closeout_git_state.get("schema"),
        "status": closeout_git_state.get("status"),
        "reason": closeout_git_state.get("reason"),
        "dirty_total": closeout_git_state.get("dirty_total"),
        "staged_total": closeout_git_state.get("staged_total"),
        "ahead": closeout_git_state.get("ahead"),
        "behind": closeout_git_state.get("behind"),
        "closeout_ready": closeout_git_state.get("closeout_ready"),
        "clean_closeout_ready": closeout_git_state.get("clean_closeout_ready"),
        "scoped_work_allowed": closeout_git_state.get("scoped_work_allowed"),
        "scoped_work_gate": {
            key: closeout_git_state.get("scoped_work_gate", {}).get(key)
            for key in (
                "status",
                "reason",
                "scoped_work_allowed",
                "private_index_scoped_commit_allowed",
                "global_dirty_tree_blocks_scoped_work",
                "required_lane",
            )
            if isinstance(closeout_git_state.get("scoped_work_gate"), dict)
            and closeout_git_state.get("scoped_work_gate", {}).get(key)
            not in (None, "", [], {})
        },
        "publication": {
            key: publication.get(key)
            for key in ("status", "audit_command")
            if publication.get(key) not in (None, "", [], {})
        },
        "worktrees": {
            key: worktrees.get(key)
            for key in (
                "status",
                "linked_count",
                "dirty_linked_count",
                "dirty_status",
                "dirty_status_known",
                "dirty_unknown_count",
                "dirty_status_not_checked_count",
            )
            if worktrees.get(key) not in (None, "", [], {})
        },
        "recommended_lane": closeout_git_state.get("recommended_lane") or {},
        "drilldowns": {
            key: drilldowns.get(key)
            for key in ("closeout_conditions", "push_audit", "mission_preflight")
            if drilldowns.get(key) not in (None, "", [], {})
        },
        "trimmed_for_entry_admission": True,
        "hard_ceiling_handle_compacted": True,
        "omission_receipt": {
            "omitted": [
                "worktree lease detail",
                "full drilldown map",
                "conditions",
                "observed",
            ],
            "reason": "Hard entry admission keeps closeout decision fields and owner status routes.",
            "drilldown": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions",
        },
    }


def _compact_route_lease_for_admission(route_lease: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(route_lease, dict):
        return route_lease

    def bounded_list(key: str, *, keep: int = 3) -> tuple[list[Any], int]:
        rows = list(route_lease.get(key) or [])
        return rows[:keep], max(0, len(rows) - keep)

    permitted_direct_actions = list(route_lease.get("permitted_direct_actions") or [])
    requires_kernel_when, requires_omitted = bounded_list("requires_kernel_when")
    do_not_call_kernel_for, do_not_omitted = bounded_list("do_not_call_kernel_for")
    return_to_kernel_when, return_omitted = bounded_list("return_to_kernel_when")

    compact = {
        key: route_lease.get(key)
        for key in (
            "schema_version",
            "lease_id",
            "issued_by",
            "mode_contract",
            "task_hash",
            "selected_lane_id",
            "route_reason",
            "known_paths",
            "invalidation_inputs",
            "budget",
            "diagnostics",
        )
        if route_lease.get(key) not in (None, "", [], {})
    }
    compact["permitted_direct_actions"] = permitted_direct_actions
    compact["requires_kernel_when"] = requires_kernel_when
    compact["do_not_call_kernel_for"] = do_not_call_kernel_for
    compact["return_to_kernel_when"] = return_to_kernel_when
    compact["policy_counts"] = {
        "known_authority_surfaces": len(route_lease.get("known_authority_surfaces") or []),
        "permitted_direct_actions": len(permitted_direct_actions),
        "requires_kernel_when": len(route_lease.get("requires_kernel_when") or []),
        "do_not_call_kernel_for": len(route_lease.get("do_not_call_kernel_for") or []),
        "return_to_kernel_when": len(route_lease.get("return_to_kernel_when") or []),
    }
    compact["omission_receipt"] = {
        "omitted": [
            "known_authority_surfaces",
            f"requires_kernel_when tail ({requires_omitted})",
            f"do_not_call_kernel_for tail ({do_not_omitted})",
            f"return_to_kernel_when tail ({return_omitted})",
        ],
        "reason": "Entry admission keeps direct-action permissions and a policy head; full lease policy remains source-owned.",
        "drilldown": "./repo-python kernel.py --entry \"<task>\" --context-budget 20000",
    }
    compact["trimmed_for_entry_admission"] = True
    return compact


def _hard_compact_route_lease_for_admission(route_lease: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(route_lease, dict):
        return route_lease
    budget = route_lease.get("budget") if isinstance(route_lease.get("budget"), dict) else {}
    invalidation_inputs = (
        route_lease.get("invalidation_inputs")
        if isinstance(route_lease.get("invalidation_inputs"), dict)
        else {}
    )
    permitted_direct_actions = list(route_lease.get("permitted_direct_actions") or [])
    requires_kernel_when = list(route_lease.get("requires_kernel_when") or [])
    do_not_call_kernel_for = list(route_lease.get("do_not_call_kernel_for") or [])
    return {
        "schema_version": route_lease.get("schema_version"),
        "issued_by": route_lease.get("issued_by"),
        "mode_contract": route_lease.get("mode_contract"),
        "selected_lane_id": route_lease.get("selected_lane_id"),
        "invalidation_inputs": {
            key: invalidation_inputs.get(key)
            for key in (
                "active_phase_id",
                "python_target_resolution_status",
                "navigation_index_currentness",
                "navigation_index_source_coupling",
            )
            if invalidation_inputs.get(key) not in (None, "", [], {})
        },
        "budget": {
            key: budget.get(key)
            for key in (
                "max_kernel_calls_before_direct_action",
                "second_kernel_call_requires_kernel_shaped_reason",
                "direct_action_first_for_known_path_questions",
            )
            if budget.get(key) not in (None, "", [], {})
        },
        "permitted_direct_actions": permitted_direct_actions,
        "requires_kernel_when": requires_kernel_when[:3],
        "do_not_call_kernel_for": do_not_call_kernel_for[:3],
        "policy_counts": {
            "permitted_direct_actions": len(permitted_direct_actions),
            "requires_kernel_when": len(route_lease.get("requires_kernel_when") or []),
            "do_not_call_kernel_for": len(route_lease.get("do_not_call_kernel_for") or []),
            "return_to_kernel_when": len(route_lease.get("return_to_kernel_when") or []),
        },
        "omission_receipt": {
            "omitted": [
                "known authority surfaces",
                "next action command",
                "requires/do_not/return policy prose",
            ],
            "reason": (
                "Hard entry admission keeps the selected lane, direct-action affordance, "
                "and policy counts; detailed lease policy remains behind the entry drilldown."
            ),
            "drilldown": "./repo-python kernel.py --entry \"<task>\" --context-budget 20000",
        },
        "trimmed_for_entry_admission": True,
        "hard_ceiling_handle_compacted": True,
    }


def _compact_agent_operating_packet_for_admission(
    packet: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(packet, dict):
        return packet
    metrics = packet.get("metrics") if isinstance(packet.get("metrics"), dict) else {}
    return {
        key: packet.get(key)
        for key in (
            "kind",
            "schema_version",
            "status",
            "source_ref",
            "authority_posture",
            "global_principle_ids",
            "agent_principle_ids",
            "candidate_axiom_policy",
            "route",
            "agent_principles_route",
        )
        if packet.get(key) not in (None, "", [], {})
    } | {
        "metrics": {
            key: metrics.get(key)
            for key in (
                "global_principle_count",
                "agent_principle_count",
                "frequent_principle_count",
                "axiom_candidate_glance_count",
                "entry_strip_bytes",
                "global_runtime_capsule_bytes",
                "compact_full_packet_bytes",
            )
            if metrics.get(key) not in (None, "", [], {})
        },
        "omission_receipt": {
            "omitted": ["global_principles[].flag", "global_principles[].tiny"],
            "reason": (
                "Entry admission keeps principle ids and routes; principle text belongs in "
                "the agent-operating-packet card route."
            ),
            "drilldown": packet.get("route"),
        },
        "trimmed_for_entry_admission": True,
    }


def _hard_compact_allowed_drilldowns_for_admission(rows: Any) -> list[dict[str, Any]]:
    compact_rows: list[dict[str, Any]] = []
    for row in list(rows or [])[:5]:
        if not isinstance(row, dict):
            continue
        compact_rows.append(
            {
                key: row.get(key)
                for key in ("command", "surface_role")
                if row.get(key) not in (None, "", [], {})
            }
        )
    return compact_rows


def _compact_agent_principle_lens_for_admission(
    lens: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(lens, dict):
        return lens
    rows: list[dict[str, Any]] = []
    for row in list(lens.get("rows") or []):
        if not isinstance(row, dict):
            continue
        compact_row = {
            key: row.get(key)
            for key in ("id", "title", "scope_id", "why_selected", "route")
            if row.get(key) not in (None, "", [], {})
        }
        flag = str(row.get("flag") or "").strip()
        if flag:
            compact_row["flag"] = flag[:180] + ("..." if len(flag) > 180 else "")
        rows.append(compact_row)
    invocation = lens.get("invocation") if isinstance(lens.get("invocation"), dict) else {}
    compact = {
        key: lens.get(key)
        for key in (
            "kind",
            "schema_version",
            "artifact_role",
            "runtime_doctrine_type",
            "authority_posture",
            "status",
            "recognized_situation",
            "selected_lane_id",
            "selected_ids",
        )
        if lens.get(key) not in (None, "", [], {})
    } | {
        "rows": rows,
        "invocation": {
            key: invocation.get(key)
            for key in (
                "all_agent_principles",
                "selected_principle_cards",
                "authoring_lane",
                "agent_operating_packet",
            )
            if invocation.get(key) not in (None, "", [], {})
        },
        "omission_receipt": {
            "omitted": [
                "capture_reflex details",
                "unifies_with references",
                "full principle tests and evidence refs",
            ],
            "reason": (
                "Entry admission keeps the task-conditioned principle lens and selected card routes; "
                "authoring/capture detail belongs in the principle drilldown."
            ),
            "drilldown": lens.get("invocation", {}).get("selected_principle_cards")
            if isinstance(lens.get("invocation"), dict)
            else None,
        },
        "trimmed_for_entry_admission": True,
    }
    if isinstance(lens.get("capture_reflex"), dict):
        compact["capture_reflex"] = lens.get("capture_reflex")
    return compact


def _compact_candidate_runtime_pressure_for_admission(
    pressure: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(pressure, dict):
        return pressure
    rows = [row for row in list(pressure.get("rows") or []) if isinstance(row, dict)]
    suppressed_rows = [
        row for row in list(pressure.get("suppressed_rows") or []) if isinstance(row, dict)
    ]
    return {
        key: pressure.get(key)
        for key in (
            "count",
            "suppressed_count",
            "filter_policy",
            "contract_ref",
            "source_standard",
            "non_law_warning",
            "match_strategy",
            "match_strategy_ref",
        )
        if pressure.get(key) not in (None, "", [], {})
    } | {
        "rows": rows[:3],
        "rows_omitted_for_entry_admission": max(0, len(rows) - 3),
        "suppressed_rows": suppressed_rows[:5],
        "suppressed_rows_omitted_for_entry_admission": max(0, len(suppressed_rows) - 5),
        "suppressed_surface_reasons": pressure.get("suppressed_surface_reasons") or [],
        "evidence_surface_reasons": pressure.get("evidence_surface_reasons") or [],
        "omission_receipt": {
            "omitted": [
                "emitted_surface_reasons",
            ],
            "reason": (
                "Entry admission keeps whether candidate-runtime pressure exists; "
                "matching mechanics belong in the governing standard."
            ),
            "drilldown": "codex/standards/std_agent_entry_surface.json::candidate_runtime_pressure_contract",
        },
        "trimmed_for_entry_admission": True,
    }


def _hard_compact_candidate_runtime_pressure_for_admission(
    pressure: dict[str, Any] | None,
    *,
    preserve_suppressed_rows: bool = False,
) -> dict[str, Any] | None:
    if not isinstance(pressure, dict):
        return pressure
    if int(pressure.get("count") or 0) > 0 or (
        preserve_suppressed_rows and int(pressure.get("suppressed_count") or 0) > 0
    ):
        return _compact_candidate_runtime_pressure_for_admission(pressure)
    rows = [row for row in list(pressure.get("rows") or []) if isinstance(row, dict)]
    compact_rows = [
        {
            key: row.get(key)
            for key in ("id", "slug", "surface_reason", "route")
            if row.get(key) not in (None, "", [], {})
        }
        for row in rows[:1]
    ]
    compact = {
        "count": pressure.get("count", 0),
        "suppressed_count": pressure.get("suppressed_count", 0),
        "filter_policy": pressure.get("filter_policy"),
        "contract_ref": pressure.get("contract_ref"),
        "omission_receipt": {
            "omitted": ["candidate row detail", "suppression reason lists", "policy prose"],
            "reason": "Hard entry admission keeps candidate pressure presence and route handles only.",
            "drilldown": "codex/standards/std_agent_entry_surface.json::candidate_runtime_pressure_contract",
        },
        "trimmed_for_entry_admission": True,
        "hard_ceiling_handle_compacted": True,
    }
    if compact_rows:
        compact["rows"] = compact_rows
        compact["rows_omitted_for_entry_admission"] = max(0, len(rows) - len(compact_rows))
    else:
        compact["rows"] = []
    return compact


def _compact_active_phase_for_admission(active_phase: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(active_phase, dict):
        return active_phase
    return {
        key: active_phase.get(key)
        for key in (
            "available",
            "active_phase_id",
            "active_phase_number",
            "active_phase_title",
            "active_directive_path",
            "resolved_from",
        )
        if active_phase.get(key) not in (None, "", [], {})
    } | {
        "omission_receipt": {
            "omitted": ["active_phase_dir", "resolution_sources_checked", "actor runtime fields"],
            "reason": "Entry admission keeps the active phase handle; full phase packet is the drilldown.",
            "drilldown": "./repo-python kernel.py --phase",
        },
        "trimmed_for_entry_admission": True,
    }


def _hard_compact_active_phase_for_admission(active_phase: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(active_phase, dict):
        return active_phase
    return {
        key: active_phase.get(key)
        for key in ("available", "active_phase_id", "active_phase_number")
        if active_phase.get(key) not in (None, "", [], {})
    } | {
        "omission_receipt": {
            "omitted": ["active phase title", "directive path", "resolution detail"],
            "drilldown": "./repo-python kernel.py --phase",
        },
        "trimmed_for_entry_admission": True,
        "hard_ceiling_handle_compacted": True,
    }


def _hard_compact_transaction_control_plane_for_admission(
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return payload
    return {
        "schema": payload.get("schema") or "transaction_control_plane_summary_v0",
        "status": payload.get("status"),
        "target_id": payload.get("target_id"),
        "next_action": payload.get("next_action"),
        "omission_receipt": {
            "omitted": [
                "per-subplane quarantine cards",
                "workspace bloat detail",
                "push gate detail",
                "alternate drilldown commands",
            ],
            "reason": "Entry admission keeps the transaction drilldown handle; control summary carries the full packet.",
            "drilldown": payload.get("next_action")
            or "./repo-python tools/meta/control/mission_transaction_preflight.py --control-summary",
        },
        "trimmed_for_entry_admission": True,
        "hard_ceiling_handle_compacted": True,
    }


def _hard_compact_active_execution_constellation_for_admission(
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return payload
    priority = payload.get("work_priority") if isinstance(payload.get("work_priority"), dict) else {}
    lanes = priority.get("lanes") if isinstance(priority.get("lanes"), list) else []
    compact_lanes: list[dict[str, Any]] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        rows = lane.get("rows") if isinstance(lane.get("rows"), list) else []
        first_row = rows[0] if rows and isinstance(rows[0], dict) else None
        compact_lane = {
            "lane_id": lane.get("lane_id"),
            "label": lane.get("label"),
            "executable_now": lane.get("executable_now"),
            "blocked": lane.get("blocked"),
        }
        if first_row:
            compact_lane["top"] = {
                key: first_row.get(key)
                for key in ("id", "rank", "state", "schedulable", "pressure")
                if first_row.get(key) not in (None, "", [], {})
            }
        compact_lanes.append(compact_lane)

    live_sessions = (
        payload.get("live_sessions") if isinstance(payload.get("live_sessions"), dict) else {}
    )
    awareness_cards = (
        live_sessions.get("awareness_cards")
        if isinstance(live_sessions.get("awareness_cards"), list)
        else []
    )
    compact_awareness_cards = []
    for card in awareness_cards[:2]:
        if not isinstance(card, dict):
            continue
        compact_awareness_cards.append(
            {
                key: card.get(key)
                for key in (
                    "session_id",
                    "actor",
                    "freshness_state",
                    "pass_state",
                    "current_pass_line",
                    "last_pass_result_line",
                    "source",
                )
                if card.get(key) not in (None, "", [], {})
            }
        )
    claim_topology = (
        live_sessions.get("claim_topology")
        if isinstance(live_sessions.get("claim_topology"), dict)
        else {}
    )
    demotion_guard = (
        payload.get("demotion_guard") if isinstance(payload.get("demotion_guard"), dict) else {}
    )
    blocker_topology = (
        demotion_guard.get("blocker_topology")
        if isinstance(demotion_guard.get("blocker_topology"), dict)
        else {}
    )
    compact_topology_keys = (
        "schema_version",
        "authority_posture",
        "source_path",
        "claim_count",
        "session_count",
        "bucket_counts",
    )
    return {
        "kind": payload.get("kind") or "active_execution_constellation",
        "schema_version": payload.get("schema_version") or "active_execution_constellation_v0",
        "view_profile": "entry_admission_hard_compact",
        "declared_anchor": {
            key: (payload.get("declared_anchor") or {}).get(key)
            for key in ("phase_id", "runtime_state", "status")
            if isinstance(payload.get("declared_anchor"), dict)
            and (payload.get("declared_anchor") or {}).get(key) not in (None, "", [], {})
        },
        "projection_freshness_status": (
            (payload.get("projection_freshness") or {}).get("status")
            if isinstance(payload.get("projection_freshness"), dict)
            else None
        ),
        "projection_freshness": {
            "status": (payload.get("projection_freshness") or {}).get("status"),
            "generated_at": (payload.get("projection_freshness") or {}).get("generated_at"),
        }
        if isinstance(payload.get("projection_freshness"), dict)
        else {},
        "work_priority": {
            "schema_version": priority.get("schema_version")
            or "task_ledger_priority_constellation_v1",
            "view_counts": priority.get("view_counts") if isinstance(priority, dict) else {},
            "lane_contract": priority.get("lane_contract") if isinstance(priority, dict) else {},
            "lanes": compact_lanes,
            "drilldown": "./repo-python kernel.py --pulse",
        },
        "live_sessions": {
            "counts": live_sessions.get("counts") if isinstance(live_sessions, dict) else {},
            "awareness_cards": compact_awareness_cards,
            "claim_topology_summary": {
                key: claim_topology.get(key)
                for key in compact_topology_keys
                if claim_topology.get(key) not in (None, "", [], {})
            },
        },
        "demotion_guard": {
            "status": demotion_guard.get("status"),
            "closeable": demotion_guard.get("closeable"),
            "blocker_count": demotion_guard.get("blocker_count"),
            "blocker_topology": {
                key: blocker_topology.get(key)
                for key in compact_topology_keys
                if blocker_topology.get(key) not in (None, "", [], {})
            },
            "recommended_lane": demotion_guard.get("recommended_lane"),
        },
        "omission_receipt": {
            "omitted": [
                "session rows",
                "live campaign titles",
                "awareness cards beyond first two",
                "demotion topology",
                "dependency edge lists",
                "rows beyond first pressure handle per lane",
            ],
            "reason": "Active-execution entry admission keeps scheduler lanes and counts; pulse/full projection carries topology.",
            "drilldown": "./repo-python kernel.py --pulse",
        },
        "trimmed_for_entry_admission": True,
        "hard_ceiling_handle_compacted": True,
    }


def _entry_packet_section_sizes(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"section": key, "bytes": _pretty_json_bytes(value)}
        for key, value in packet.items()
    ]
    return sorted(rows, key=lambda row: int(row["bytes"]), reverse=True)


def _entry_admission_task_requests_full_diagnostics(task_text: str | None) -> bool:
    lowered = str(task_text or "").lower()
    return any(
        term in lowered
        for term in (
            "entry_surface_diagnostics",
            "entry diagnostics",
            "generated region",
            "generated-region",
            "renderer content",
            "bootstrap projection",
            "routing projection",
            "projection checker",
        )
    )


def _apply_entry_hard_compaction_steps(
    packet: dict[str, Any],
    *,
    hard_target_bytes: int,
    hard_compacted_sections: list[str],
    preserve_capture_reflex: bool = False,
    preserve_observed_state: bool = False,
    preserve_suppressed_rows: bool = False,
) -> None:
    steps: list[tuple[str, Callable[[Any], Any]]] = [
        ("active_execution_constellation", _hard_compact_active_execution_constellation_for_admission),
        ("transaction_control_plane", _hard_compact_transaction_control_plane_for_admission),
        (
            "agent_principle_lens",
            lambda value: _hard_compact_agent_principle_lens_for_admission(
                value,
                preserve_capture_reflex=preserve_capture_reflex,
            ),
        ),
        (
            "entry_surface_diagnostics",
            lambda value: _hard_compact_entry_surface_diagnostics_for_admission(
                value,
                preserve_observed_state=preserve_observed_state,
            ),
        ),
        ("route_lease", _hard_compact_route_lease_for_admission),
        ("closeout_git_state", _hard_compact_closeout_git_state_for_admission),
        ("agent_operating_packet", _hard_compact_agent_operating_packet_for_admission),
        ("active_phase", _hard_compact_active_phase_for_admission),
        (
            "candidate_runtime_pressure",
            lambda value: _hard_compact_candidate_runtime_pressure_for_admission(
                value,
                preserve_suppressed_rows=preserve_suppressed_rows,
            ),
        ),
        ("top_schedulable_workitem", _hard_compact_entry_workitem_handoff_for_admission),
        ("top_ready_workitem", _hard_compact_entry_workitem_handoff_for_admission),
        ("allowed_drilldowns", _hard_compact_allowed_drilldowns_for_admission),
    ]
    for section, compact_value in steps:
        if _pretty_json_bytes(packet) <= hard_target_bytes:
            break
        if packet.get(section) is None:
            continue
        before_section_bytes = _pretty_json_bytes(packet.get(section))
        packet[section] = compact_value(packet.get(section))
        after_section_bytes = _pretty_json_bytes(packet.get(section))
        if after_section_bytes < before_section_bytes and section not in hard_compacted_sections:
            hard_compacted_sections.append(section)


def _compact_entry_section_receipts_for_inline_target(packet: dict[str, Any]) -> list[str]:
    compacted_sections: list[str] = []
    receipt_sections = (
        "navigation_index_spine",
        "entry_surface_diagnostics",
        "route_lease",
        "closeout_git_state",
        "agent_operating_packet",
        "agent_principle_lens",
        "candidate_runtime_pressure",
        "top_schedulable_workitem",
        "top_ready_workitem",
    )
    for section in receipt_sections:
        if _pretty_json_bytes(packet) <= ENTRY_PACKET_INLINE_TARGET_BYTES:
            break
        value = packet.get(section)
        if not isinstance(value, dict):
            continue
        receipt = value.get("omission_receipt")
        if not isinstance(receipt, dict):
            continue
        before_section_bytes = _pretty_json_bytes(value)
        compact_receipt = {
            key: receipt.get(key)
            for key in ("drilldown",)
            if receipt.get(key) not in (None, "", [], {})
        }
        compact_receipt["reason"] = "Details omitted to keep --entry under its inline target."
        value["omission_receipt"] = compact_receipt
        after_section_bytes = _pretty_json_bytes(value)
        if after_section_bytes < before_section_bytes:
            compacted_sections.append(section)
    return compacted_sections


def _apply_entry_payload_admission(
    packet: dict[str, Any],
    *,
    context_budget: int,
    task_text: str | None = None,
) -> dict[str, Any]:
    before_bytes = _pretty_json_bytes(packet)
    if before_bytes <= ENTRY_PACKET_INLINE_TARGET_BYTES:
        packet["entry_payload_admission"] = {
            "schema_version": "entry_payload_admission_v0",
            "status": "within_inline_target",
            "inline_target_bytes": ENTRY_PACKET_INLINE_TARGET_BYTES,
            "output_bytes": before_bytes,
            "context_budget": context_budget,
        }
        return packet

    before_top_sections = _entry_packet_section_sizes(packet)[:5]
    selected_lane = packet.get("selected_lane")
    selected_lane_id = (
        selected_lane.get("lane_id") if isinstance(selected_lane, dict) else None
    )
    full_diagnostics_requested = _entry_admission_task_requests_full_diagnostics(task_text)
    hard_compacted_sections: list[str] = []

    if packet.get("top_schedulable_workitem") is not None:
        packet["top_schedulable_workitem"] = _compact_entry_workitem_handoff_for_admission(
            packet.get("top_schedulable_workitem")
        )
    packet["active_phase"] = _compact_active_phase_for_admission(packet.get("active_phase"))
    packet["agent_operating_packet"] = _compact_agent_operating_packet_for_admission(
        packet.get("agent_operating_packet")
    )
    packet["agent_principle_lens"] = _compact_agent_principle_lens_for_admission(
        packet.get("agent_principle_lens")
    )
    packet["candidate_runtime_pressure"] = _compact_candidate_runtime_pressure_for_admission(
        packet.get("candidate_runtime_pressure")
    )
    packet["closeout_git_state"] = _compact_closeout_git_state_for_admission(
        packet.get("closeout_git_state")
    )
    packet["route_lease"] = _compact_route_lease_for_admission(packet.get("route_lease"))
    if selected_lane_id == "navigation_enforcement":
        packet["navigation_index_spine"] = _compact_entry_navigation_index_spine_for_admission(
            packet.get("navigation_index_spine")
        )
        if not full_diagnostics_requested:
            packet["entry_surface_diagnostics"] = _compact_entry_surface_diagnostics_for_admission(
                packet.get("entry_surface_diagnostics")
            )
        current_bytes = _pretty_json_bytes(packet)
        if (
            current_bytes
            > ENTRY_PACKET_INLINE_TARGET_BYTES - ENTRY_PACKET_ADMISSION_RECEIPT_HEADROOM_BYTES
            or before_bytes - current_bytes < ENTRY_PACKET_NAVIGATION_MIN_SAVED_BYTES
        ):
            packet["navigation_index_spine"] = (
                _hard_compact_entry_navigation_index_spine_for_admission(
                    packet.get("navigation_index_spine")
                )
            )
            hard_compacted_sections.append("navigation_index_spine")

        hard_target_bytes = ENTRY_PACKET_INLINE_TARGET_BYTES - ENTRY_PACKET_ADMISSION_RECEIPT_HEADROOM_BYTES
        if not full_diagnostics_requested:
            _apply_entry_hard_compaction_steps(
                packet,
                hard_target_bytes=hard_target_bytes,
                hard_compacted_sections=hard_compacted_sections,
            )

    if selected_lane_id != "navigation_enforcement":
        hard_target_bytes = ENTRY_PACKET_INLINE_TARGET_BYTES - ENTRY_PACKET_ADMISSION_RECEIPT_HEADROOM_BYTES
        if not full_diagnostics_requested:
            _apply_entry_hard_compaction_steps(
                packet,
                hard_target_bytes=hard_target_bytes,
                hard_compacted_sections=hard_compacted_sections,
                preserve_capture_reflex=selected_lane_id == "agent_principle_authoring",
                preserve_observed_state=True,
                preserve_suppressed_rows=selected_lane_id != "active_execution_constellation",
            )

    after_bytes_without_receipt = _pretty_json_bytes(packet)
    packet["entry_payload_admission"] = {
        "schema_version": "entry_payload_admission_v0",
        "status": "pending_receipt_accounting",
        "inline_target_bytes": ENTRY_PACKET_INLINE_TARGET_BYTES,
        "context_budget": context_budget,
        "before_bytes": before_bytes,
        "after_bytes_without_receipt": after_bytes_without_receipt,
        "top_sections_before": before_top_sections[:3],
        "top_sections_after": _entry_packet_section_sizes(packet)[:3],
        "preserved_non_negotiable_fields": [
            "banned_routes",
            "route_lease.permitted_direct_actions",
            "ceremony_budget.required_proof",
            "surface_contract",
            "navigation_index_spine.currentness",
            "navigation_index_spine.source_coupling",
            "navigation_index_spine.omission_receipt",
        ],
        "owner_surface": "system/lib/kernel/commands/comprehension_snapshot.py::build_entry_packet",
    }
    if hard_compacted_sections:
        packet["entry_payload_admission"]["hard_compacted_sections"] = hard_compacted_sections
    if _pretty_json_bytes(packet) > ENTRY_PACKET_INLINE_TARGET_BYTES and hard_compacted_sections:
        packet["entry_payload_admission"] = {
            "schema_version": "entry_payload_admission_v0",
            "status": "pending_compact_receipt_accounting",
            "inline_target_bytes": ENTRY_PACKET_INLINE_TARGET_BYTES,
            "before_bytes": before_bytes,
            "hard_compacted_section_count": len(hard_compacted_sections),
        }

    def refresh_admission_size() -> None:
        for _ in range(3):
            output_bytes = _pretty_json_bytes(packet)
            packet["entry_payload_admission"].update(
                {
                    "status": (
                        "trimmed"
                        if output_bytes <= ENTRY_PACKET_INLINE_TARGET_BYTES
                        and output_bytes < before_bytes
                        else "trimmed_over_inline_target"
                        if output_bytes < before_bytes
                        else "over_target_untrimmed"
                    ),
                    "output_bytes": output_bytes,
                    "after_bytes": output_bytes,
                    "saved_bytes": before_bytes - output_bytes,
                }
            )

    refresh_admission_size()
    if (
        packet["entry_payload_admission"]["status"] == "trimmed_over_inline_target"
        and hard_compacted_sections
        and not full_diagnostics_requested
    ):
        post_receipt_compacted_sections = _compact_entry_section_receipts_for_inline_target(packet)
        if post_receipt_compacted_sections:
            packet["entry_payload_admission"][
                "post_receipt_compacted_section_count"
            ] = len(post_receipt_compacted_sections)
            refresh_admission_size()
            if packet["entry_payload_admission"]["status"] == "trimmed_over_inline_target":
                packet["entry_payload_admission"].pop(
                    "post_receipt_compacted_section_count",
                    None,
                )
                refresh_admission_size()
    return packet


def classify_patch_ceremony(
    write_paths: list[str],
    *,
    command: str = "",
    performed_steps: list[str] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Let closeout and tests self-apply the same ceremony classifier
      to the patch being performed, instead of leaving ceremony as advice for
      future actions only.
    """
    return _ceremony_budget_for_action(
        action_kind="patch_self_application",
        command=command,
        write_paths=write_paths,
        mutation=True,
        performed_steps=performed_steps,
    )


def _next_action(
    *,
    kind: str,
    command: str,
    rationale: str,
    write_paths: list[str] | None = None,
    mutation: bool = False,
    live_effect: bool = False,
    autonomous_effect: bool = False,
    provider_effect: bool = False,
    private_payload_effect: bool = False,
    lifecycle_effect: bool = False,
    source_promotion_effect: bool = False,
    preview_only: bool = False,
    risk_hints: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "command": command,
        "rationale": rationale,
        "write_paths": write_paths or [],
        "ceremony_budget": _ceremony_budget_for_action(
            action_kind=kind,
            command=command,
            write_paths=write_paths,
            mutation=mutation,
            live_effect=live_effect,
            autonomous_effect=autonomous_effect,
            provider_effect=provider_effect,
            private_payload_effect=private_payload_effect,
            lifecycle_effect=lifecycle_effect,
            source_promotion_effect=source_promotion_effect,
            preview_only=preview_only,
            risk_hints=risk_hints,
        ),
    }


def _next_actions(active_phase: dict[str, Any], compliance: dict[str, Any], skill_map: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if active_phase.get("active_phase_id"):
        actions.append(_next_action(
            kind="phase_continue",
            command=f"./repo-python kernel.py --phase {active_phase['active_phase_id']}",
            rationale="Inspect the active phase wave and next bounded step.",
        ))
    if compliance.get("ready_now_count", 0) > 0:
        actions.append(_next_action(
            kind="compliance_ready_work",
            command="./repo-python kernel.py --row standards:std_compute_provider --band card",
            rationale=f"{compliance['ready_now_count']} compliance worklist entries are ready_now per the metabolism ledger.",
        ))
    if skill_map.get("missing_authoring_skill", 0) > 0:
        actions.append(_next_action(
            kind="standard_skill_pairing_gap",
            command="./repo-python tools/meta/factory/build_standard_skill_map.py --report",
            rationale=f"{skill_map['missing_authoring_skill']} standards still lack a paired authoring skill.",
        ))
    actions.append(_next_action(
        kind="rung_1_drilldown",
        command="./repo-python kernel.py --kind-atlas --band flag",
        rationale="Browse the rung-0 atlas of artifact kinds before keyword routing.",
    ))
    actions.append(_next_action(
        kind="rung_2_drilldown",
        command="./repo-python kernel.py --row <kind_id>:<row_id> --band flag",
        rationale="Generic per-row drilldown (e.g. --row standards:std_compute_provider --band card).",
    ))
    return actions


_ACTIVE_LANES_PATH = "state/phase_lanes/active_lanes.json"
_BRIDGE_WINDOW_IDENTITY_PATH = "state/bridge_windows/window_identity.json"
_REACTIONS_YAML_PATH = "reactions.yaml"
_STANDARD_SKILL_PAIRING_PACKET_ROOT = "state/meta_missions/standard_skill_pairing"
_COMPLIANCE_AUTOCURE_PACKET_ROOT = "state/meta_missions/compliance_autocure"


def _enumerate_reactions_yaml(repo_root: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Walk reactions.yaml and return per-reaction metadata
      (reaction_id, source.kind, enabled_by_default, action.operation_id) so
      the snapshot can cross-check engine support without depending on YAML
      libs. Tolerates missing PyYAML by falling back to a minimal text
      scanner that handles the file's regular shape.
    """
    path = repo_root / _REACTIONS_YAML_PATH
    if not path.is_file():
        return []
    try:
        import yaml  # type: ignore
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        reactions = payload.get("reactions") or []
        return [r for r in reactions if isinstance(r, dict)]
    except Exception:
        rows: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        in_source = False
        in_action = False
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.rstrip()
                if line.startswith("  - reaction_id:"):
                    if current:
                        rows.append(current)
                    current = {"reaction_id": line.split(":", 1)[1].strip(), "source": {}, "action": {}}
                    in_source = False
                    in_action = False
                    continue
                if not current:
                    continue
                if line.startswith("    source:"):
                    in_source, in_action = True, False
                    continue
                if line.startswith("    action:"):
                    in_source, in_action = False, True
                    continue
                if line.startswith("    ") and not line.startswith("      "):
                    in_source = False
                    in_action = False
                if in_source and line.startswith("      kind:"):
                    current["source"]["kind"] = line.split(":", 1)[1].strip()
                if in_action and line.startswith("      operation_id:"):
                    current["action"]["operation_id"] = line.split(":", 1)[1].strip()
                if line.startswith("    enabled_by_default:"):
                    current["enabled_by_default"] = line.split(":", 1)[1].strip() == "true"
            if current:
                rows.append(current)
        except OSError:
            return []
        return rows


def _read_reactions_ledger_tail(repo_root: Path, *, limit: int = 200) -> list[dict[str, Any]]:
    """Wave_004B2: tail the reactions ledger so the snapshot can surface fires."""
    path = repo_root / "tools/meta/control/reactions_ledger.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            tail_block = fh.readlines()[-limit:]
    except OSError:
        return []
    for line in tail_block:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _summarize_latest_reaction_fires(
    repo_root: Path,
    *,
    reaction_ids: tuple[str, ...] = ("standard_skill_gap_high", "compliance_coverage_low"),
    fire_kinds: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Bind the latest fire rows from the reactions ledger for the target
    reaction ids. fire_kinds restricts which ledger kinds count (Wave_004B3:
    manual proof rows are kind=reaction_fired_manual_proof; daemon/tick rows
    are kind=reaction_fired). Defaults to both."""
    if fire_kinds is None:
        fire_kinds_set = {"reaction_fired_manual_proof", "reaction_fired"}
    else:
        fire_kinds_set = set(fire_kinds)
    rows = _read_reactions_ledger_tail(repo_root, limit=400)
    by_reaction: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("kind") or "") not in fire_kinds_set:
            continue
        rid = str(row.get("reaction_id") or "")
        if rid not in reaction_ids:
            continue
        prior = by_reaction.get(rid)
        if not prior or str(row.get("recorded_at") or "") > str(prior.get("recorded_at") or ""):
            by_reaction[rid] = row
    fires: list[dict[str, Any]] = []
    for rid in reaction_ids:
        latest = by_reaction.get(rid)
        if not latest:
            fires.append({"reaction_id": rid, "fired": False, "advisory_note": "no matching fire on disk yet"})
            continue
        fires.append({
            "reaction_id": rid,
            "fired": True,
            "kind": latest.get("kind"),
            "recorded_at": latest.get("recorded_at"),
            "event_id": latest.get("event_id"),
            "operation_id": latest.get("operation_id"),
            "signal_digest": latest.get("signal_digest"),
            "ledger_fingerprint": latest.get("ledger_fingerprint"),
            "returncode": latest.get("returncode"),
            "written": latest.get("written") or [],
            "mutation_policy": latest.get("mutation_policy"),
            "promotion_state": latest.get("promotion_state"),
        })
    return fires


def _summarize_dedupe_state(repo_root: Path) -> dict[str, Any]:
    """Wave_004B3: read reactions_state runtime entries and check that the
    target reactions' last_fired_signal_digest matches the current live signal
    digest. If both match, dedupe_state_closed=true (the daemon will not
    re-fire identical material)."""
    target_reactions = ("standard_skill_gap_high", "compliance_coverage_low")
    state_path = repo_root / "tools/meta/control/reactions_state.json"
    state_payload = _read_json_safe(state_path) or {}
    # Reactions state schema_version=reactions_state_v2 stores per-reaction
    # runtime entries under per_reaction (not reactions). Tolerate both keys
    # so the snapshot survives a future schema rename.
    runtime = state_payload.get("per_reaction") or state_payload.get("reactions") or {}
    if not isinstance(runtime, dict):
        runtime = {}
    digests_now: dict[str, str | None] = {}
    try:
        from system.lib.compliance_reaction_signals import (
            build_compliance_coverage_signal,
            build_standard_skill_gap_signal,
        )
        digests_now["standard_skill_gap_high"] = str(
            build_standard_skill_gap_signal(repo_root).get("digest") or ""
        ) or None
        digests_now["compliance_coverage_low"] = str(
            build_compliance_coverage_signal(repo_root).get("digest") or ""
        ) or None
    except Exception:
        digests_now = {}
    per_reaction: dict[str, dict[str, Any]] = {}
    closed_per_reaction: list[bool] = []
    for rid in target_reactions:
        entry = runtime.get(rid) if isinstance(runtime.get(rid), dict) else {}
        last_digest = str(entry.get("last_fired_signal_digest") or "") if entry else ""
        cooldown_until = str(entry.get("cooldown_until") or "") if entry else ""
        live_digest = digests_now.get(rid)
        digest_match = bool(last_digest) and bool(live_digest) and last_digest == live_digest
        closed = digest_match or bool(cooldown_until)
        per_reaction[rid] = {
            "last_fired_signal_digest": last_digest or None,
            "live_signal_digest": live_digest,
            "digest_match": digest_match,
            "cooldown_until": cooldown_until or None,
            "closed": closed,
            "last_result": entry.get("last_result"),
        }
        closed_per_reaction.append(closed)
    return {
        "per_reaction": per_reaction,
        "all_closed": bool(closed_per_reaction) and all(closed_per_reaction),
    }


def _summarize_latest_campaign_packets(repo_root: Path) -> dict[str, Any]:
    """Wave_004B2: locate the newest campaign_packet.json under each lane root."""
    out: dict[str, Any] = {}
    for lane, rel in (
        ("standard_skill_pairing", "state/meta_missions/standard_skill_pairing"),
        ("compliance_autocure", "state/meta_missions/compliance_autocure"),
    ):
        root = repo_root / rel
        if not root.is_dir():
            out[lane] = None
            continue
        candidates = sorted(
            root.rglob("campaign_packet.json"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0.0,
            reverse=True,
        )
        if not candidates:
            out[lane] = None
            continue
        out[lane] = candidates[0].relative_to(repo_root).as_posix()
    return out


def _summarize_reaction_metabolism(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Wave_004B reaction-metabolism observability. Cross-check
      reactions.yaml against the engine's supported source kinds, surface
      enabled-but-unloadable reactions as drift, and report the latest
      signal digests + campaign packet roots.
    """
    try:
        from tools.meta.control.reactions_engine import supported_source_kinds
        supported = list(supported_source_kinds())
    except Exception as exc:
        supported = []
        supported_error = f"{exc.__class__.__name__}: {exc}"
    else:
        supported_error = None

    reactions = _enumerate_reactions_yaml(repo_root)
    enabled_reactions: list[str] = []
    enabled_but_unsupported: list[dict[str, str]] = []
    disabled_authored: list[dict[str, str]] = []
    for r in reactions:
        rid = str(r.get("reaction_id") or "")
        kind = str((r.get("source") or {}).get("kind") or "")
        enabled = bool(r.get("enabled_by_default"))
        if enabled and rid:
            enabled_reactions.append(rid)
            if supported and kind not in supported:
                enabled_but_unsupported.append({"reaction_id": rid, "source_kind": kind})
        elif rid and not enabled:
            disabled_authored.append({"reaction_id": rid, "source_kind": kind})

    latest_digests: dict[str, str | None] = {}
    try:
        from system.lib.compliance_reaction_signals import (
            build_compliance_coverage_signal,
            build_standard_skill_gap_signal,
        )
        latest_digests["standard_skill_gap_signal"] = str(
            build_standard_skill_gap_signal(repo_root).get("digest") or ""
        ) or None
        latest_digests["compliance_coverage_signal"] = str(
            build_compliance_coverage_signal(repo_root).get("digest") or ""
        ) or None
    except Exception:
        pass

    def _packet_count(rel: str) -> int:
        root = repo_root / rel
        if not root.is_dir():
            return 0
        return sum(1 for _ in root.rglob("campaign_packet.json"))

    latest_fires = _summarize_latest_reaction_fires(repo_root)
    manual_proof_fires = _summarize_latest_reaction_fires(
        repo_root, fire_kinds=("reaction_fired_manual_proof",)
    )
    daemon_fires = _summarize_latest_reaction_fires(
        repo_root, fire_kinds=("reaction_fired",)
    )
    latest_packets = _summarize_latest_campaign_packets(repo_root)
    dedupe_state = _summarize_dedupe_state(repo_root)
    engine_path_proof_seen = bool(manual_proof_fires) and all(
        f.get("fired") for f in manual_proof_fires
    )
    daemon_autonomous_proof_seen = bool(daemon_fires) and all(
        f.get("fired") for f in daemon_fires
    )
    dedupe_state_closed = bool(dedupe_state.get("all_closed"))
    reaction_proof = {
        "engine_path_proof_seen": engine_path_proof_seen,
        "daemon_autonomous_proof_seen": daemon_autonomous_proof_seen,
        "dedupe_state_closed": dedupe_state_closed,
        "manual_proof_fires": manual_proof_fires,
        "daemon_fires": daemon_fires,
        "dedupe_state": dedupe_state,
        "rule": (
            "engine_path_proof_seen requires reaction_fired_manual_proof rows "
            "(targeted helper reused engine semantics). "
            "daemon_autonomous_proof_seen requires reaction_fired rows "
            "(real daemon/tick path executed). "
            "dedupe_state_closed requires runtime state shows last_fired_signal_digest "
            "matching the current live signal digest OR cooldown_until populated, "
            "so a re-evaluation will not repeat-fire the same digest."
        ),
    }
    return {
        "supported_source_kinds": supported,
        "supported_source_kinds_error": supported_error,
        "enabled_reactions": enabled_reactions,
        "enabled_but_unsupported": enabled_but_unsupported,
        "disabled_authored": disabled_authored,
        "latest_signal_digests": latest_digests,
        "latest_reaction_fires": latest_fires,
        "latest_campaign_packets": latest_packets,
        "reaction_proof": reaction_proof,
        "autonomous_proof_seen": daemon_autonomous_proof_seen and dedupe_state_closed,
        "campaign_packet_roots": [
            _STANDARD_SKILL_PAIRING_PACKET_ROOT,
            _COMPLIANCE_AUTOCURE_PACKET_ROOT,
        ],
        "campaign_packet_counts": {
            _STANDARD_SKILL_PAIRING_PACKET_ROOT: _packet_count(_STANDARD_SKILL_PAIRING_PACKET_ROOT),
            _COMPLIANCE_AUTOCURE_PACKET_ROOT: _packet_count(_COMPLIANCE_AUTOCURE_PACKET_ROOT),
        },
        "mutation_policy": "candidate_packet_only",
        "rule": (
            "Wave_004B reaction metabolism: signal kinds are loaded by "
            "tools/meta/control/reactions_engine.py::_load_source_signal; "
            "campaign builders write only candidate packets (promotion_state: "
            "draft, mutation_policy: candidate_packet_only) under the listed "
            "roots; controller (Type A) owns promotion. Per pri_133, this "
            "section is for visibility, not coordination veto."
        ),
    }


def _summarize_active_phase_lanes(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Wave_004C deposit. The repo's phase model carries one
      active_phase, but the runtime now has multiple concurrent lanes. This
      section reads state/phase_lanes/active_lanes.json (deposit-only
      authority surface) so the snapshot can name lane plurality without
      blowing up the existing phase machinery.
    """
    payload = _read_json_safe(repo_root / _ACTIVE_LANES_PATH)
    if not payload:
        return {
            "available": False,
            "reason": "active lanes deposit not yet authored",
            "path": _ACTIVE_LANES_PATH,
            "advisory_note": (
                "Wave_004C deposit-only artifact; the operator's nonlinear "
                "subphase observation lives here. See pri_133."
            ),
        }
    return {
        "available": True,
        "active_phase_anchor": payload.get("active_phase_anchor"),
        "lanes": payload.get("lanes") or [],
        "generated_at": payload.get("generated_at"),
    }


def _summarize_bridge_windows(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Wave_004C operator-bridge identity plane. The producer owns
      the typed artifact shape and summary rules; the comprehension snapshot
      reads that state without probing CDP or mutating browser surfaces.
    """
    try:
        from system.lib.bridge_window_identity import summarize_bridge_window_identity
    except Exception as exc:
        return {
            "available": False,
            "reason": f"bridge_window_identity import failed: {exc.__class__.__name__}: {exc}",
            "path": _BRIDGE_WINDOW_IDENTITY_PATH,
        }
    return summarize_bridge_window_identity(repo_root)


def _summarize_generated_artifact_surfaces(repo_root: Path, kind_atlas_summary: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Confirm the four Wave_003B generated-artifact kinds
      (transform_job_receipts, row_patches, compliance_ledger,
      standard_skill_map) are reachable through both --option-surface and
      --row, so the comprehension snapshot proves the russian-doll drilldown
      is complete from kind atlas to per-row card.
    """
    expected = ("transform_job_receipts", "row_patches", "compliance_ledger", "standard_skill_map")
    by_kind = kind_atlas_summary.get("by_kind") or []
    found_ids = {str(row.get("kind_id") or "") for row in by_kind if isinstance(row, dict)}
    available = {kid: kid in found_ids for kid in expected}
    return {
        "kind_ids": list(expected),
        "all_available": all(available.values()),
        "per_kind_available": available,
        "rule": (
            "These four kinds are exposed via "
            "system/lib/kernel/commands/generated_artifact_surfaces.py and "
            "registered in kind_atlas + standard_option_surface; both "
            "--option-surface <kind> --band flag and --row <kind>:<id> --band card "
            "should resolve."
        ),
    }


def build_comprehension_snapshot(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compose the unified comprehension snapshot payload. Pure
      read; never mutates state.
    """
    standards_total_inventory = len(enumerate_standard_ids(repo_root))
    kind_atlas = _summarize_kind_atlas(repo_root)
    compliance = _summarize_compliance_ledger(repo_root)
    skill_map = _summarize_standard_skill_map(repo_root)
    compute_audit = _summarize_compute_audit(repo_root)
    compute_workers = _summarize_compute_workers(repo_root)
    active_phase = _summarize_active_phase(repo_root)
    advisory = _summarize_blackboard_advisory(repo_root)
    generated_artifact_surfaces = _summarize_generated_artifact_surfaces(repo_root, kind_atlas)
    reaction_metabolism = _summarize_reaction_metabolism(repo_root)
    active_phase_lanes = _summarize_active_phase_lanes(repo_root)
    bridge_windows = _summarize_bridge_windows(repo_root)

    primary_sources_ok = all([
        kind_atlas.get("available"),
        compliance.get("available"),
        skill_map.get("available"),
        compute_audit.get("available"),
        compute_workers.get("available"),
        active_phase.get("available"),
    ])

    drift_findings: list[dict[str, str]] = []
    sm_total = skill_map.get("standards_total")
    if isinstance(sm_total, int) and sm_total != standards_total_inventory:
        drift_findings.append({
            "kind": "standards_total_disagreement",
            "summary": (
                f"standard-skill map reports standards_total={sm_total} but "
                f"enumerate_standard_ids returns {standards_total_inventory}; "
                "rebuild build_standard_skill_map.py to refresh."
            ),
        })
    cl_total = compliance.get("standards_total")
    if isinstance(cl_total, int) and cl_total != standards_total_inventory:
        drift_findings.append({
            "kind": "compliance_ledger_total_disagreement",
            "summary": (
                f"compliance ledger reports standards_total={cl_total} but "
                f"enumerate_standard_ids returns {standards_total_inventory}; "
                "rebuild build_compliance_ledger.py to refresh."
            ),
        })
    try:
        from system.lib.bridge_window_identity import bridge_window_drift_findings
        drift_findings.extend(bridge_window_drift_findings(bridge_windows))
    except Exception as exc:
        drift_findings.append({
            "kind": "bridge_window_identity_drift_check_failed",
            "summary": f"bridge window drift check failed: {exc.__class__.__name__}: {exc}",
        })

    return {
        "kind": "kernel.comprehension_snapshot",
        "schema_version": "comprehension_snapshot_v1",
        "generated_at": _utc_now(),
        "ok": primary_sources_ok,
        "active_phase": active_phase,
        "kind_atlas": kind_atlas,
        "compliance_ledger": compliance,
        "standard_skill_map": skill_map,
        "compute_audit": compute_audit,
        "compute_workers": compute_workers,
        "standards_inventory": {
            "standards_total": standards_total_inventory,
            "source": "system/lib/standards_inventory.py::enumerate_standard_ids",
            "rule": "Single substrate fact; builders MUST use this helper rather than carry hardcoded totals (pri_133).",
        },
        "blackboard_advisory": advisory,
        "generated_artifact_surfaces": generated_artifact_surfaces,
        "reaction_metabolism": reaction_metabolism,
        "active_phase_lanes": active_phase_lanes,
        "bridge_windows": bridge_windows,
        "drift_findings": drift_findings,
        "next_actions": _next_actions(active_phase, compliance, skill_map),
        "ceremony_budget_policy": {
            "schema_version": "ceremony_budget_policy_v0",
            "classifier_version": "ceremony_budget_heuristic_v0",
            "rule": (
                "Next-action packets carry a ceremony_budget computed from semantic blast radius, "
                "authority weight, reversibility, lifecycle coupling, and autonomy exposure; file "
                "count alone is not a risk metric."
            ),
            "self_application_helper": "system/lib/kernel/commands/comprehension_snapshot.py::classify_patch_ceremony",
            "tiers": [
                "tier_0_observe_only",
                "tier_1_standard_low",
                "tier_2_normal_bounded",
                "tier_3_high_authority",
                "tier_4_critical_autonomy",
            ],
            "projection_source": "system/lib/kernel/commands/comprehension_snapshot.py::_ceremony_budget_for_action",
            "source_refs": [
                "codex/standards/std_apply.json::target_routing.trust_tiers",
                "codex/standards/std_agent_entry_surface.json::common_sense_helpfulness_floor",
                "codex/doctrine/paper_modules/workitem_spine_operating_practice.md",
            ],
        },
        "operating_discipline": {
            "rule": "Coordination ceremony is advisory by default. Verify session liveness before deferring; find the deep cause if a signal looks load-bearing but isn't.",
            "principle_ref": "pri_133",
            "skill_ref": "codex/doctrine/skills/doctrine/ceremony_friction_audit.md",
            "why_in_snapshot": (
                "Surfaced in every comprehension snapshot so future agents reading the system "
                "in one entry inherit the discipline from disk, not from chat archaeology."
            ),
        },
        "non_goals": [
            "Does not run providers or mutate substrate.",
            "Does not refresh stale builders; if a section is missing, it reports the gap rather than rebuilding.",
            "Does not replace --option-surface or --row; it composes them into one packet.",
        ],
    }


def _vantage_limits(band: str) -> tuple[str, dict[str, int], list[str]]:
    normalized = str(band or "flag").strip().lower()
    warnings: list[str] = []
    if normalized not in {"flag", "card", "context"}:
        warnings.append(f"Unsupported vantage band {normalized!r}; using flag limits.")
        normalized = "flag"
    if normalized == "context":
        return normalized, {"clusters": 10, "frontier": 8, "raw_seed_tail": 12}, warnings
    if normalized == "card":
        return normalized, {"clusters": 6, "frontier": 5, "raw_seed_tail": 8}, warnings
    return normalized, {"clusters": 3, "frontier": 3, "raw_seed_tail": 5}, warnings


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _truncate(value: Any, *, limit: int = 360) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


_TASK_LEDGER_WORK_SPINE_BUCKETS: tuple[dict[str, Any], ...] = (
    {
        "bucket_id": "top_ready",
        "label": "Top ready work",
        "description": "Ready and schedulable WorkItems ordered by Task Ledger rank views.",
        "source_views": ("schedulable_by_rank", "ready_by_rank"),
    },
    {
        "bucket_id": "active_wip",
        "label": "Active WIP",
        "description": "Claimed or in-flight WorkItems that already have active work pressure.",
        "source_views": ("active_wip",),
    },
    {
        "bucket_id": "bridge_assignable",
        "label": "Bridge packets",
        "description": "Bridge-shaped WorkItems that need packet, provenance, and authority boundaries before automation.",
        "source_views": ("bridge_assignable",),
    },
    {
        "bucket_id": "blockers",
        "label": "Blockers",
        "description": "Explicitly blocked or dependency-blocked WorkItems.",
        "source_views": ("blocked", "dependency_blocked"),
    },
    {
        "bucket_id": "signoff_needs",
        "label": "Sign-off needs",
        "description": "WorkItems waiting on review, sign-off, or propagation closeout.",
        "source_views": ("needs_signoff", "propagation_needed"),
    },
)


def _task_ledger_view_items(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = (payload or {}).get("items") or (payload or {}).get("rows") or []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _task_ledger_view_payload(repo_root: Path, view_id: str) -> dict[str, Any] | None:
    return _read_json_safe(repo_root / "state" / "task_ledger" / "views" / f"{view_id}.json")


def _task_ledger_drilldown_command(work_item_id: str | None = None) -> str:
    if work_item_id:
        safe_id = shlex.quote(work_item_id)
        return f"./repo-python kernel.py --option-surface task_ledger --band card --ids {safe_id}"
    return "./repo-python kernel.py --option-surface task_ledger --band cluster_flag"


def _compact_task_ledger_dependency_edge(edge: Any) -> dict[str, Any] | None:
    if not isinstance(edge, dict):
        return None
    edge_id = str(edge.get("id") or "").strip()
    if not edge_id:
        return None
    compact: dict[str, Any] = {
        "id": edge_id,
        "title": edge.get("title"),
        "state": edge.get("state"),
        "rank": edge.get("rank"),
        "relationship": edge.get("relationship"),
    }
    for key in (
        "satisfied",
        "reason",
        "waiting_on_this",
        "downstream_schedulable",
        "unlock_status",
    ):
        value = edge.get(key)
        if value is not None:
            compact[key] = value
    if isinstance(edge.get("downstream_unsatisfied_dep_ids"), list):
        compact["downstream_unsatisfied_dep_ids"] = list(edge["downstream_unsatisfied_dep_ids"][:4])
    return compact


def _compact_task_ledger_dependency_edges(edges: Any, *, limit: int = 3) -> list[dict[str, Any]]:
    if not isinstance(edges, list):
        return []
    compact: list[dict[str, Any]] = []
    for edge in edges:
        row = _compact_task_ledger_dependency_edge(edge)
        if row:
            compact.append(row)
        if len(compact) >= limit:
            break
    return compact


def _task_ledger_contract_status(item: dict[str, Any]) -> dict[str, Any]:
    projection = (
        item.get("projection_completeness")
        if isinstance(item.get("projection_completeness"), dict)
        else {}
    )
    projected_fields = (
        ("completion_contract", "has_completion_contract"),
        ("integration_contract", "has_integration_contract"),
        ("satisfaction_contract", "has_satisfaction_contract"),
    )
    explicit_missing = item.get("missing_contracts")
    if isinstance(explicit_missing, list):
        missing_contracts = [
            str(value).strip()
            for value in explicit_missing
            if str(value).strip()
        ][:6]
    else:
        missing_contracts = [
            label
            for label, projection_key in projected_fields
            if not bool(projection.get(projection_key))
        ]
    return {
        "has_completion_contract": bool(projection.get("has_completion_contract")),
        "has_integration_contract": bool(projection.get("has_integration_contract")),
        "has_satisfaction_contract": bool(projection.get("has_satisfaction_contract")),
        "has_authority": bool(projection.get("has_authority")),
        "exact_surfaces_grounded": bool(projection.get("exact_surfaces_grounded")),
        "missing_contracts": missing_contracts,
    }


def _compact_task_ledger_work_item(item: dict[str, Any], *, source_view: str) -> dict[str, Any]:
    work_item_id = str(item.get("id") or "").strip() or None
    completion = item.get("completion") if isinstance(item.get("completion"), dict) else {}
    projection = (
        item.get("projection_completeness")
        if isinstance(item.get("projection_completeness"), dict)
        else {}
    )
    dependency = item.get("dependency_status") if isinstance(item.get("dependency_status"), dict) else {}
    return {
        "id": work_item_id,
        "title": item.get("title"),
        "state": item.get("state") or item.get("status"),
        "work_item_type": item.get("work_item_type") or item.get("candidate_work_item_type"),
        "rank": item.get("rank"),
        "recommended_action": item.get("recommended_action"),
        "contract_status": _task_ledger_contract_status(item),
        "source_views": [source_view],
        "signoff_required": bool(completion.get("signoff_required") or projection.get("needs_signoff")),
        "dependency_status": {
            "schedulable": dependency.get("schedulable"),
            "hard_dep_count": _as_int(dependency.get("hard_dep_count")),
            "unsatisfied_dep_count": len(dependency.get("unsatisfied_dep_ids") or []),
            "dangling_dep_count": len(dependency.get("dangling_dep_ids") or []),
            "downstream_unlock_count": len(dependency.get("downstream_unlock_ids") or []),
            "upstream_dependency_edges": _compact_task_ledger_dependency_edges(
                dependency.get("upstream_dependency_edges") or dependency.get("dependency_states")
            ),
            "downstream_unlock_edges": _compact_task_ledger_dependency_edges(
                dependency.get("downstream_unlock_edges")
            ),
        },
        "drilldown_command": _task_ledger_drilldown_command(work_item_id),
    }


def _work_spine_bucket(repo_root: Path, spec: dict[str, Any], *, limit: int) -> dict[str, Any]:
    source_views = [str(view) for view in spec.get("source_views") or []]
    view_counts: dict[str, int] = {}
    items_by_id: dict[str, dict[str, Any]] = {}
    anonymous_index = 0
    for view_id in source_views:
        items = _task_ledger_view_items(_task_ledger_view_payload(repo_root, view_id))
        view_counts[view_id] = len(items)
        for item in items:
            work_item_id = str(item.get("id") or "").strip()
            if not work_item_id:
                anonymous_index += 1
                work_item_id = f"{view_id}:anonymous:{anonymous_index}"
            if work_item_id in items_by_id:
                source_view_list = items_by_id[work_item_id].setdefault("source_views", [])
                if isinstance(source_view_list, list) and view_id not in source_view_list:
                    source_view_list.append(view_id)
                continue
            items_by_id[work_item_id] = _compact_task_ledger_work_item(item, source_view=view_id)
    items = list(items_by_id.values())
    return {
        "bucket_id": spec.get("bucket_id"),
        "label": spec.get("label"),
        "description": spec.get("description"),
        "count": len(items),
        "source_views": source_views,
        "source_view_counts": view_counts,
        "sample_items": items[:limit],
        "omission_receipt": {
            "omitted_count": max(0, len(items) - limit),
            "sample_limit": limit,
            "reason": "Vantage work_spine shows bounded samples only; Task Ledger views and card drilldowns remain authority.",
            "drilldown_command": _task_ledger_drilldown_command(),
        },
    }


def _find_phase_queue_row(queue: dict[str, Any], work_item_id: str) -> dict[str, Any] | None:
    for key in ("ordered_execution_queue", "candidate_inventory", "items", "rows"):
        rows = queue.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and str(row.get("work_item_id") or row.get("id") or "") == work_item_id:
                return row
    return None


def _task_ledger_work_item_by_id(repo_root: Path, work_item_id: str) -> dict[str, Any]:
    ledger = _read_json_safe(repo_root / "state" / "task_ledger" / "ledger.json")
    rows = ledger.get("work_items") if isinstance(ledger, dict) else []
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, dict) and str(row.get("id") or "").strip() == work_item_id:
            return row
    return {}


def _work_spine_current_next(repo_root: Path, snapshot: dict[str, Any]) -> dict[str, Any] | None:
    active_phase = snapshot.get("active_phase") if isinstance(snapshot.get("active_phase"), dict) else {}
    active_phase_dir = str(active_phase.get("active_phase_dir") or "").strip()
    if not active_phase_dir:
        return None
    queue_rel = Path(active_phase_dir) / "frontend_demo_readiness_queue.json"
    queue = _read_json_safe(repo_root / queue_rel)
    if not queue:
        return None
    work_item_id = str(queue.get("current_next") or "").strip()
    if not work_item_id:
        return None
    row = _find_phase_queue_row(queue, work_item_id) or {}
    ledger_item = _task_ledger_work_item_by_id(repo_root, work_item_id)
    contract_status = _task_ledger_contract_status(ledger_item) if ledger_item else {}
    return {
        "id": work_item_id,
        "title": row.get("title") or ledger_item.get("title"),
        "state": ledger_item.get("state") or row.get("state"),
        "work_item_type": ledger_item.get("work_item_type") or row.get("work_item_type"),
        "candidate_work_item_type": ledger_item.get("candidate_work_item_type")
        or row.get("candidate_work_item_type"),
        "sequence": row.get("sequence"),
        "recommended_action": ledger_item.get("recommended_action") or row.get("recommended_action"),
        "contract_status": contract_status,
        "missing_contracts": contract_status.get("missing_contracts") or [],
        "source_ref": queue_rel.as_posix(),
        "drilldown_command": _task_ledger_drilldown_command(work_item_id),
    }


def _summarize_task_ledger_work_spine(
    repo_root: Path,
    snapshot: dict[str, Any],
    *,
    limit: int,
) -> dict[str, Any]:
    buckets = {
        str(spec["bucket_id"]): _work_spine_bucket(repo_root, spec, limit=limit)
        for spec in _TASK_LEDGER_WORK_SPINE_BUCKETS
    }
    return {
        "kind": "task_ledger_work_spine_v1",
        "authority": "state/task_ledger/events.jsonl + state/task_ledger/ledger.json + state/task_ledger/views/*.json",
        "mutation_boundary": "read_only_synthesis_existing_task_ledger_writers_remain_authority",
        "current_next": _work_spine_current_next(repo_root, snapshot),
        "buckets": buckets,
        "totals": {
            bucket_id: _as_int(bucket.get("count"))
            for bucket_id, bucket in buckets.items()
        },
        "omission_policy": "Bounded samples only; source views and card drilldowns remain authority.",
        "source_refs": [
            "state/task_ledger/events.jsonl",
            "state/task_ledger/ledger.json",
            "state/task_ledger/views/schedulable_by_rank.json",
            "state/task_ledger/views/ready_by_rank.json",
            "state/task_ledger/views/active_wip.json",
            "state/task_ledger/views/bridge_assignable.json",
            "state/task_ledger/views/blocked.json",
            "state/task_ledger/views/dependency_blocked.json",
            "state/task_ledger/views/needs_signoff.json",
            "state/task_ledger/views/propagation_needed.json",
        ],
        "drilldown_command": _task_ledger_drilldown_command(),
    }


def _kind_rows(kind_atlas: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = kind_atlas.get("by_kind") if isinstance(kind_atlas, dict) else []
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        kind_id = str(row.get("kind_id") or "")
        if kind_id:
            out[kind_id] = row
    return out


def _lattice_group(rows_by_kind: dict[str, dict[str, Any]], kind_ids: tuple[str, ...]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for kind_id in kind_ids:
        row = rows_by_kind.get(kind_id)
        if not row:
            continue
        rows.append({
            "kind_id": kind_id,
            "title": row.get("title"),
            "row_count": _as_int(row.get("row_count")),
        })
    return {
        "total_rows": sum(_as_int(row.get("row_count")) for row in rows),
        "kinds": rows,
    }


def _summarize_lattice_vantage(kind_atlas: dict[str, Any]) -> dict[str, Any]:
    rows_by_kind = _kind_rows(kind_atlas)
    return {
        "available": bool(kind_atlas.get("available")),
        "kind_count": kind_atlas.get("kind_count"),
        "total_rows": kind_atlas.get("total_rows"),
        "groups": {
            "doctrine_gradient": _lattice_group(rows_by_kind, (
                "axiom_candidates",
                "principles",
                "concepts",
                "mechanisms",
                "paper_modules",
                "standards",
                "skills",
            )),
            "operator_voice": _lattice_group(rows_by_kind, (
                "raw_seed_shards",
                "axiom_candidates",
            )),
            "external_substrate": _lattice_group(rows_by_kind, (
                "annex_patterns",
                "annex_distillation_patterns",
                "github_import_candidates",
            )),
            "code": _lattice_group(rows_by_kind, (
                "python_files",
                "python_scopes",
                "frontend_views",
                "frontend_components",
            )),
            "debt": _lattice_group(rows_by_kind, (
                "artifact_projection_debt",
                "skill_compression_debt",
                "standard_projection_gaps",
                "compliance_ledger",
            )),
        },
    }


def _project_cluster_row(row: dict[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for key in (
        "cluster_id",
        "row_id",
        "shard_id",
        "title",
        "label",
        "count",
        "claim",
        "top_ids",
        "adoption_status_counts",
        "authored_artifact_count",
        "primary_idea_group_id",
        "sibling_shard_count",
        "status",
    ):
        value = row.get(key)
        if value not in (None, "", [], {}):
            projected[key] = value
    return projected


def _summarize_option_surface_rollup(
    repo_root: Path,
    artifact_kind: str,
    *,
    limit: int,
) -> dict[str, Any]:
    try:
        from system.lib.standard_option_surface import build_option_surface
    except Exception as exc:
        return {
            "available": False,
            "artifact_kind": artifact_kind,
            "reason": f"build_option_surface import failed: {exc.__class__.__name__}: {exc}",
        }

    attempts: list[dict[str, Any]] = []
    selected_payload: dict[str, Any] | None = None
    for surface_band in ("cluster_flag", "flag"):
        try:
            payload = build_option_surface(repo_root, artifact_kind, band=surface_band)
        except Exception as exc:
            attempts.append({
                "band": surface_band,
                "profile_status": "error",
                "reason": f"{exc.__class__.__name__}: {exc}",
            })
            continue
        attempts.append({
            "band": surface_band,
            "profile_status": payload.get("profile_status"),
            "row_count": (payload.get("summary") or {}).get("row_count"),
        })
        if payload.get("profile_status") == "supported":
            selected_payload = payload
            break

    if selected_payload is None:
        return {
            "available": False,
            "artifact_kind": artifact_kind,
            "attempts": attempts,
            "reason": "no supported cluster_flag or flag projection",
            "drilldown_command": f"./repo-python kernel.py --option-surface {artifact_kind} --band cluster_flag",
        }

    summary = selected_payload.get("summary") or {}
    rows = selected_payload.get("rows") if isinstance(selected_payload.get("rows"), list) else []
    surface_band = str(selected_payload.get("band") or "")
    clustered = surface_band == "cluster_flag"
    return {
        "available": True,
        "artifact_kind": artifact_kind,
        "surface_band": surface_band,
        "clustered": clustered,
        "row_count": summary.get("row_count", len(rows)),
        "total_available": summary.get("total_available", summary.get("row_count", len(rows))),
        "entries": [_project_cluster_row(row) for row in rows[:limit] if isinstance(row, dict)],
        "attempts": attempts,
        "fallback_reason": None if clustered else "cluster_flag unavailable; using bounded flag entries",
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface {artifact_kind} --band {surface_band}"
        ),
    }


def _summarize_cluster_rollups(repo_root: Path, *, limit: int) -> dict[str, Any]:
    return {
        kind: _summarize_option_surface_rollup(repo_root, kind, limit=limit)
        for kind in (
            "paper_modules",
            "principles",
            "annex_patterns",
            "annex_distillation_patterns",
            "raw_seed_shards",
        )
    }


def _summarize_prime_directive_vibe(repo_root: Path) -> dict[str, Any]:
    rel = "codex/doctrine/paper_modules/prime_directives.md"
    path = repo_root / rel
    if not path.is_file():
        return {"available": False, "source_ref": rel, "reason": "prime directives module missing"}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {"available": False, "source_ref": rel, "reason": f"read failed: {exc}"}
    start_idx = None
    for idx, raw in enumerate(lines):
        if raw.strip() == "## D1 — Extract operator intent, preserve voice pressure":
            start_idx = idx
            break
    if start_idx is None:
        return {"available": False, "source_ref": rel, "reason": "D1 section not found"}

    rules_idx = None
    for idx in range(start_idx, len(lines)):
        if lines[idx].strip() == "**Operational rules.**":
            rules_idx = idx
            break
    if rules_idx is None:
        return {
            "available": False,
            "source_ref": f"{rel}:{start_idx + 1}",
            "reason": "D1 operational rules not found",
        }

    window: list[dict[str, Any]] = []
    for idx, raw in enumerate(lines[rules_idx + 1:], start=rules_idx + 2):
        text = raw.strip()
        if not text:
            continue
        if text.startswith("## "):
            break
        if len(text) >= 2 and text[0].isdigit() and text[1] == ".":
            window.append({"line": idx, "text": text})
            if len(window) >= 5:
                break
    return {
        "available": bool(window),
        "source_ref": f"{rel}:{window[0]['line'] if window else rules_idx + 1}",
        "refresh_posture": "static_doctrine_window_subject_to_raw_seed_refresh",
        "sentence_count": len(window),
        "lines": window,
    }


def _summarize_constitution_identity(repo_root: Path) -> dict[str, Any]:
    rel = SYSTEM_SELF_COMPREHENSION_ROOT_PATH
    path = repo_root / rel
    if not path.is_file():
        return {"available": False, "source_ref": rel, "reason": "system self-comprehension root module missing"}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {"available": False, "source_ref": rel, "reason": f"read failed: {exc}"}

    tldr_idx = None
    for idx, raw in enumerate(lines):
        if raw.strip() == "## TLDR (compressed view)":
            tldr_idx = idx
            break
    if tldr_idx is None:
        return {"available": False, "source_ref": rel, "reason": "TLDR section not found"}

    paragraph: list[str] = []
    start_line = tldr_idx + 1
    for idx, raw in enumerate(lines[tldr_idx + 1 :], start=tldr_idx + 2):
        text = raw.strip()
        if not text:
            if paragraph:
                break
            continue
        if text.startswith("## "):
            break
        if not paragraph:
            start_line = idx
        paragraph.append(text)
    identity_claim = " ".join(paragraph).strip()
    if ". " in identity_claim:
        identity_claim = identity_claim.split(". ", 1)[0].rstrip() + "."
    identity_claim = _truncate(identity_claim, limit=520)
    return {
        "available": bool(identity_claim),
        "source_ref": f"{rel}:{start_line}",
        "root_source": rel,
        "projection_role": "system_self_comprehension_packet_root",
        "identity_claim": identity_claim,
        "refresh_posture": "authored_root_contract_projected_into_live_vantage_and_packet_profiles",
        "fidelity_mode": "identity_claim",
        "sentence_count": 1 if identity_claim else 0,
        "lines": [{"line": start_line, "text": f"1. {identity_claim}"}] if identity_claim else [],
        "drilldown_command": "./repo-python kernel.py --paper-module system_self_comprehension_root",
        "aliases": [
            "system_self_comprehension_packet",
            "constitution_workspace",
            "what_am_i",
            "system_self_description",
        ],
    }


def _hash_rel_file(repo_root: Path, rel: str) -> dict[str, Any]:
    path = repo_root / rel
    if not path.is_file():
        return {"path": rel, "status": "missing"}
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"path": rel, "status": "unreadable", "reason": str(exc)}
    return {
        "path": rel,
        "status": "available",
        "sha256_16": hashlib.sha256(data).hexdigest()[:16],
        "bytes": len(data),
    }


def _build_constitution_source_graph(repo_root: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    static_inputs = [
        "codex/doctrine/paper_modules/system_self_comprehension_root.md",
        "codex/doctrine/paper_modules/system_constitution_seed.md",
        "codex/doctrine/paper_modules/system_self_comprehension_spine.md",
        "codex/doctrine/paper_modules/prompt_shelf_uppropagation_ledger.md",
        "codex/doctrine/paper_modules/operational_work_item_spine.md",
        "codex/doctrine/paper_modules/local_to_general_propagation.md",
        "codex/doctrine/skills/doctrine/local_to_general_propagation.md",
        "codex/doctrine/paper_modules/_index.json",
        "codex/doctrine/documentation_theory_index.json",
        "codex/doctrine/compression_profiles.json",
        "codex/standards/std_constitution_workspace.json",
        "state/system_atlas/system_packet_status.json",
        "state/system_atlas/type_b_grounding_packet_status.json",
        "codex/standards/std_system_term.json",
        "codex/standards/std_prompt_ledger.json",
        "codex/standards/std_self_model.json",
        "codex/standards/std_agent_entry_surface.json",
        "codex/standards/std_paper_module.json",
        "system/lib/prompt_ledger_events.py",
        "tools/meta/observability/prompt_ledger.py",
        "tools/meta/observability/prompt_shelf_uppropagation_index.py",
        "tools/meta/observability/prompt_shelf_uppropagation_digest.py",
    ]
    inputs = [_hash_rel_file(repo_root, rel) for rel in static_inputs]
    active_phase = snapshot.get("active_phase") if isinstance(snapshot.get("active_phase"), dict) else {}
    dynamic_inputs = [
        {
            "id": "active_phase",
            "status": "available" if active_phase.get("active_phase_id") else "missing",
            "value": active_phase.get("active_phase_id"),
        },
        {
            "id": "comprehension_snapshot",
            "status": "available" if snapshot.get("schema_version") else "missing",
            "schema_version": snapshot.get("schema_version"),
        },
    ]
    stable_fingerprint_payload = {
        "static": [
            {key: row.get(key) for key in ("path", "status", "sha256_16")}
            for row in inputs
        ]
    }
    live_state_fingerprint_payload = {
        "dynamic": dynamic_inputs,
    }
    source_graph_fingerprint = hashlib.sha256(
        json.dumps(stable_fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    live_state_fingerprint = hashlib.sha256(
        json.dumps(live_state_fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return {
        "fingerprint": source_graph_fingerprint,
        "source_graph_fingerprint": source_graph_fingerprint,
        "live_state_fingerprint": live_state_fingerprint,
        "algorithm": "sha256_24_over_selected_stable_constitution_workspace_sources",
        "live_state_algorithm": "sha256_24_over_selected_live_constitution_workspace_state",
        "inputs": inputs,
        "stable_inputs": inputs,
        "dynamic_inputs": dynamic_inputs,
        "live_state_inputs": dynamic_inputs,
        "missing_inputs": [row["path"] for row in inputs if row.get("status") != "available"],
        "selection_policy": "stable_source_graph_for_constitution_workspace_packet_v0",
        "fingerprint_policy": {
            "source_graph_fingerprint": "stable doctrine, standard, paper-module, route, and propagation source files only",
            "live_state_fingerprint": "active phase, runtime posture, and transient work-state inputs",
            "retread_law": "Do not retread unchanged stable substrate; inspect live_state_fingerprint separately for current posture churn.",
        },
    }


def _build_retread_guard(
    repo_root: Path,
    source_graph: dict[str, Any],
    *,
    consumer: str = "type_a_agent",
    fidelity_profile: str | None = None,
) -> dict[str, Any]:
    latest_receipt = _load_latest_constitution_workspace_receipt(repo_root)
    guard = _compare_receipt_to_source_graph(
        repo_root,
        latest_receipt,
        source_graph,
        consumer=consumer,
        fidelity_profile=fidelity_profile,
    )
    guard.update({
        "retread_ledger_workitem_candidate": {
            "workitem_id": "candidate_constitution_workspace_retread_ledger",
            "title": "Constitution Workspace prior-packet ledger",
            "reason": "No existing ledger was found that compares prior kernel.what_am_i packets by stable source_graph_fingerprint and separate live_state_fingerprint.",
            "must_not": "Do not make read-only --what-am-i silently write persistence.",
            "next_evidence": [
                "Decide whether the ledger belongs under state/constitution_workspace/, Prompt Ledger, Work Ledger, or navigation trace replay.",
                "Prove reusable only after comparing a prior equivalent packet with the same stable source_graph_fingerprint and compatible consumer/fidelity profile.",
            ],
        },
        "fingerprint_policy": (
            "Stable substrate and live-state churn are separated so ordinary active-phase "
            "or frontier movement does not force doctrine re-derivation."
        ),
        "read_only_default": True,
    })
    if latest_receipt:
        guard["retread_ledger_workitem_candidate"]["status"] = "satisfied_by_latest_packet_receipt"
    return guard


def _summarize_prompt_adoption_posture(repo_root: Path) -> dict[str, Any]:
    digest_rel = "state/prompt_shelf/uppropagation_digest.json"
    prompt_ledger_rel = "state/prompt_ledger/views/adoption_posture.json"
    digest_path = repo_root / digest_rel
    prompt_ledger_path = repo_root / prompt_ledger_rel
    states = [
        "captured",
        "indexed",
        "digested",
        "selected_for_adoption",
        "bound_to_workitem",
        "mutated_owner_surface",
        "validated",
        "projected_to_entry",
        "observed_in_future_run",
        "explicit_noop",
    ]
    empty_counts = {f"{state}_count": 0 for state in states}
    posture: dict[str, Any] = {
        "status": "unavailable",
        "owner": "codex/standards/std_prompt_ledger.json::adoption_state_machine",
        "source": digest_rel,
        "state_counts": dict(empty_counts),
        "known_distinctions": [
            "captured != adopted",
            "adopted != projected",
            "projected != observed",
            "receipt_count != candidate_count",
        ],
        "next": "Run the prompt-shelf digest/index builders, then bind selected prompt lessons to WorkItems, owner surfaces, or explicit no-op records.",
    }

    def merge_prompt_ledger_posture(target: dict[str, Any]) -> dict[str, Any]:
        if not prompt_ledger_path.is_file():
            return target
        try:
            ledger_posture = json.loads(prompt_ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return target
        if not isinstance(ledger_posture, dict):
            return target
        ledger_counts = (
            ledger_posture.get("candidate_milestone_counts")
            if isinstance(ledger_posture.get("candidate_milestone_counts"), dict)
            else ledger_posture.get("state_counts")
            if isinstance(ledger_posture.get("state_counts"), dict)
            else {}
        )
        merged_counts = dict(target.get("state_counts") or empty_counts)
        for state in (
            "selected_for_adoption",
            "bound_to_workitem",
            "mutated_owner_surface",
            "validated",
            "projected_to_entry",
            "observed_in_future_run",
            "explicit_noop",
        ):
            merged_counts[f"{state}_count"] = int(ledger_counts.get(f"{state}_count") or 0)
        target.update({
            "state_counts": merged_counts,
            "prompt_ledger_source": prompt_ledger_rel,
            "prompt_ledger_receipt_count": ledger_posture.get("receipt_count", 0),
            "prompt_ledger_candidate_count": ledger_posture.get("candidate_count", 0),
            "candidate_current_state_counts": ledger_posture.get("candidate_current_state_counts", {}),
            "candidate_milestone_counts": ledger_posture.get("candidate_milestone_counts", ledger_counts),
            "receipt_state_counts": ledger_posture.get("receipt_state_counts", {}),
            "adopted_count": ledger_posture.get("adopted_count", target.get("adopted_count", 0)),
            "behavior_projection_count": ledger_posture.get(
                "behavior_projection_count",
                target.get("behavior_projection_count", 0),
            ),
        })
        return target

    if not digest_path.is_file():
        posture["reason"] = "prompt shelf up-propagation digest missing"
        return merge_prompt_ledger_posture(posture)
    try:
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        posture["reason"] = f"prompt shelf up-propagation digest unreadable: {exc}"
        return merge_prompt_ledger_posture(posture)

    meta = digest.get("__meta") if isinstance(digest.get("__meta"), dict) else {}
    digest_posture = digest.get("prompt_adoption_posture") if isinstance(digest.get("prompt_adoption_posture"), dict) else {}
    if digest_posture:
        counts = digest_posture.get("state_counts") if isinstance(digest_posture.get("state_counts"), dict) else {}
        posture.update({
            "status": digest_posture.get("status") or "partial",
            "generated_at": meta.get("generated_at"),
            "source_schema_version": meta.get("schema_version"),
            "state_counts": {**empty_counts, **counts},
            "captured_count": digest_posture.get("captured_count", counts.get("captured_count", 0)),
            "indexed_count": digest_posture.get("indexed_count", counts.get("indexed_count", 0)),
            "digested_count": digest_posture.get("digested_count", counts.get("digested_count", 0)),
            "adopted_count": digest_posture.get("adopted_count", 0),
            "behavior_projection_count": digest_posture.get("behavior_projection_count", 0),
            "prompt_ledger_receipt_count": digest_posture.get("prompt_ledger_receipt_count", 0),
            "prompt_ledger_candidate_count": digest_posture.get("prompt_ledger_candidate_count", 0),
            "candidate_current_state_counts": digest_posture.get("candidate_current_state_counts", {}),
            "candidate_milestone_counts": digest_posture.get("candidate_milestone_counts", {}),
            "receipt_state_counts": digest_posture.get("receipt_state_counts", {}),
            "latest_slots": sorted((digest.get("latest_v3_by_slot") or {}).keys())
            if isinstance(digest.get("latest_v3_by_slot"), dict)
            else [],
            "rule": (
                "Prompt Shelf capture/index/digest is evidence of observed insight; "
                "behavior change requires Prompt Ledger adoption plus an owner-surface mutation, validation, "
                "entry projection, or explicit no-op."
            ),
        })
        return merge_prompt_ledger_posture(posture)

    candidate_rows = digest.get("candidate_rows")
    candidates = candidate_rows if isinstance(candidate_rows, list) else []
    counts = dict(empty_counts)
    counts["captured_count"] = int(meta.get("record_count") or 0)
    counts["indexed_count"] = int(meta.get("record_count") or 0)
    counts["digested_count"] = int(meta.get("candidate_count") or len(candidates))

    for row in candidates:
        if not isinstance(row, dict):
            continue
        state = row.get("adoption_state")
        if state in states and state not in {"captured", "indexed", "digested"}:
            counts[f"{state}_count"] += 1

    adopted_total = sum(
        counts[f"{state}_count"]
        for state in (
            "selected_for_adoption",
            "bound_to_workitem",
            "mutated_owner_surface",
            "validated",
            "projected_to_entry",
            "observed_in_future_run",
            "explicit_noop",
        )
    )
    projection_total = counts["projected_to_entry_count"] + counts["observed_in_future_run_count"]
    posture.update({
        "status": "partial" if counts["digested_count"] or counts["captured_count"] else "empty",
        "generated_at": meta.get("generated_at"),
        "source_schema_version": meta.get("schema_version"),
        "state_counts": counts,
        "captured_count": counts["captured_count"],
        "indexed_count": counts["indexed_count"],
        "digested_count": counts["digested_count"],
        "adopted_count": adopted_total,
        "behavior_projection_count": projection_total,
        "latest_slots": sorted((digest.get("latest_v3_by_slot") or {}).keys())
        if isinstance(digest.get("latest_v3_by_slot"), dict)
        else [],
        "rule": (
            "Prompt Shelf capture/index/digest is evidence of observed insight; "
            "behavior change requires Prompt Ledger adoption plus an owner-surface mutation, validation, "
            "entry projection, or explicit no-op."
        ),
    })
    return merge_prompt_ledger_posture(posture)


def _build_propagation_graph(
    repo_root: Path,
    source_graph: dict[str, Any],
    retread_guard: dict[str, Any],
) -> dict[str, Any]:
    allowed_verbs = [
        "emits",
        "interprets",
        "requests_evidence",
        "verifies",
        "mutates",
        "validates",
        "binds_status",
        "up_propagates",
        "shapes_behavior",
        "prevents",
        "broadcasts",
    ]
    adoption_posture = _summarize_prompt_adoption_posture(repo_root)
    return {
        "status": "partial",
        "question_answered": "How does operator intent become future agent behavior?",
        "root_claim": (
            "Chat understanding is not system learning until Type A binds it to a prompt, "
            "standard, WorkItem, runtime, doctrine, route, test, or explicit no-op record."
        ),
        "source_graph_fingerprint": source_graph.get("fingerprint"),
        "live_state_fingerprint": source_graph.get("live_state_fingerprint"),
        "retread_guard_ref": "retread_guard",
        "governed_by": {
            "propagation_contract": "codex/standards/std_constitution_workspace.json::propagation_contract",
            "edge_shape": "codex/standards/std_navigation_contract.json::edge_row_shape",
            "term_relationships": "codex/standards/std_system_term.json::relationships",
            "prompt_provenance": "codex/standards/std_prompt_ledger.json",
        },
        "verb_policy": {
            "status": "candidate_vocabulary_bound_to_std_constitution_workspace",
            "allowed_verbs": allowed_verbs,
            "rule": "Runtime propagation_graph.edges must use only allowed_verbs until a deeper system-term or edge-vocabulary migration owns them.",
        },
        "prompt_behavior_projection": {
            "status": "partial",
            "adoption_state_owner": "codex/standards/std_prompt_ledger.json::adoption_state_machine",
            "adoption_state_summary": adoption_posture,
            "owner_surfaces": [
                "tools/meta/observability/prompt_shelf_chatgpt_observer.py",
                "tools/meta/observability/prompt_shelf_uppropagation_index.py",
                "tools/meta/observability/prompt_shelf_uppropagation_digest.py",
                "tools/meta/observability/prompt_ledger.py",
                "system/lib/prompt_ledger_events.py",
                "codex/standards/std_prompt_ledger.json",
            ],
            "current_behavior": (
                "Prompt Shelf captures Type B prompt/response telemetry and up-propagation fields; "
                "Prompt Ledger can adopt selected traces as durable provenance and link them to WorkItems."
            ),
            "missing_edge": (
                "No evidence yet that every prompt lesson automatically mutates AGENTS/CODEX/CLAUDE, "
                "skills, standards, or runtime prompts; Type A must bind selected lessons to an owning artifact or explicit no-op."
            ),
        },
        "nodes": [
            {"id": "operator_voice", "role": "source_pressure", "stable_ref": "system_terms:operator_voice"},
            {"id": "high_class_type_b", "role": "prefrontal_interpreter", "stable_ref": "system_terms:type_b"},
            {"id": "ask_type_a", "role": "evidence_request_or_action_contour"},
            {"id": "type_a_agent", "role": "substrate_actor", "stable_ref": "system_terms:type_a"},
            {"id": "prompt_shelf", "role": "future_behavior_source", "stable_ref": "paper_modules:prompt_shelf_uppropagation_ledger"},
            {"id": "workitem_spine", "role": "intention_to_action_binding", "stable_ref": "paper_modules:operational_work_item_spine"},
            {"id": "standards", "role": "artifact_law", "stable_ref": "standards:std_constitution_workspace"},
            {"id": "local_to_general_propagation", "role": "lesson_upward_binding", "stable_ref": "paper_modules:local_to_general_propagation"},
            {"id": "validation", "role": "proof_that_mutation_landed"},
            {"id": "retread_guard", "role": "unchanged_substrate_reuse_policy"},
            {"id": "constitution_workspace", "role": "global_self_broadcast", "stable_ref": "standards:std_constitution_workspace"},
        ],
        "edges": [
            {"subject": "operator_voice", "verb": "emits", "object": "intent_pressure"},
            {"subject": "high_class_type_b", "verb": "interprets", "object": "intent_pressure"},
            {"subject": "high_class_type_b", "verb": "requests_evidence", "object": "ask_type_a_or_workitem_contour"},
            {"subject": "type_a_agent", "verb": "verifies", "object": "local_substrate"},
            {"subject": "type_a_agent", "verb": "mutates", "object": "prompt_shelf_or_standard_or_runtime_or_docs_route"},
            {"subject": "validation", "verb": "validates", "object": "mutation_behavior"},
            {"subject": "prompt_shelf", "verb": "shapes_behavior", "object": "future_agent"},
            {"subject": "workitem_spine", "verb": "binds_status", "object": "intention_to_action_and_proof"},
            {"subject": "local_to_general_propagation", "verb": "up_propagates", "object": "reusable_system_lesson"},
            {"subject": "retread_guard", "verb": "prevents", "object": "repeated_discovery_when_stable_substrate_unchanged"},
            {"subject": "constitution_workspace", "verb": "broadcasts", "object": "current_self_model_and_next_legal_edges"},
        ],
        "source_refs": [
            {"id": "paper_modules:prompt_shelf_uppropagation_ledger", "path": "codex/doctrine/paper_modules/prompt_shelf_uppropagation_ledger.md"},
            {"id": "paper_modules:operational_work_item_spine", "path": "codex/doctrine/paper_modules/operational_work_item_spine.md"},
            {"id": "paper_modules:local_to_general_propagation", "path": "codex/doctrine/paper_modules/local_to_general_propagation.md"},
            {"id": "skills:local_to_general_propagation", "path": "codex/doctrine/skills/doctrine/local_to_general_propagation.md"},
            {"id": "standards:std_constitution_workspace", "path": "codex/standards/std_constitution_workspace.json"},
            {"id": "standards:std_system_term", "path": "codex/standards/std_system_term.json"},
            {"id": "standards:std_prompt_ledger", "path": "codex/standards/std_prompt_ledger.json"},
            {"id": "runtime:prompt_ledger_events", "path": "system/lib/prompt_ledger_events.py"},
            {"id": "tools:prompt_ledger", "path": "tools/meta/observability/prompt_ledger.py"},
            {"id": "tools:prompt_shelf_uppropagation_index", "path": "tools/meta/observability/prompt_shelf_uppropagation_index.py"},
            {"id": "tools:prompt_shelf_uppropagation_digest", "path": "tools/meta/observability/prompt_shelf_uppropagation_digest.py"},
        ],
        "next_legal_edges": [
            "./repo-python kernel.py --constitution-workspace-replay latest",
            "./repo-python kernel.py --docs-route \"prompt shelf\"",
            "./repo-python kernel.py --docs-route \"WorkItem spine\"",
            "./repo-python kernel.py --docs-route \"operator intent propagation\"",
            "./repo-python kernel.py --row standards:std_constitution_workspace --band card",
        ],
        "gaps": [
            "replay gate must be surfaced before full self-description retread in constitution-facing entry routes",
            "system_terms flag projection still weakly summarizes propagation terms",
            "prompt-shelf up-propagation and Prompt Ledger can preserve Type B lessons, but no single persistent causal ledger spans every Type B to Type A mutation yet",
        ],
        "retread_posture": {
            "status": retread_guard.get("status"),
            "required_action": retread_guard.get("required_action"),
            "basis": retread_guard.get("retread_basis"),
            "workitem_candidate": retread_guard.get("retread_ledger_workitem_candidate"),
        },
    }


def _build_constitution_workspace(
    *,
    band: str,
    snapshot: dict[str, Any],
    identity: dict[str, Any],
    source_graph: dict[str, Any],
    retread_guard: dict[str, Any],
    propagation_graph: dict[str, Any],
) -> dict[str, Any]:
    active_phase = snapshot.get("active_phase") if isinstance(snapshot.get("active_phase"), dict) else {}
    return {
        "status": "compiler_bound_without_persistence",
        "standard": "codex/standards/std_constitution_workspace.json",
        "surface_family_id": "system_self_comprehension_packet",
        "root_slug": SYSTEM_SELF_COMPREHENSION_ROOT_SLUG,
        "root_source": identity.get("root_source") or SYSTEM_SELF_COMPREHENSION_ROOT_PATH,
        "identity_claim": identity.get("identity_claim"),
        "fidelity_profile": {
            "selected_band": band,
            "selection_law": "minimum_sufficient_self_description_under_declared_consumer_purpose_budget_freshness_and_authority_need",
            "modes": [
                "name",
                "identity_claim",
                "orientation_capsule",
                "exposition_brief",
                "control_packet",
                "workspace_packet",
                "evidence_graph",
                "debug_trace",
            ],
            "not_law": "fixed_sentence_counts",
        },
        "current_state": {
            "active_phase_id": active_phase.get("active_phase_id"),
            "active_phase_title": active_phase.get("title"),
        },
        "attention_frame": {
            "selected_surface": "vantage",
            "band": band,
            "role": CONTROL_ENTRY,
            "rule": "Atlas may inform control; atlas must not be control.",
        },
        "active_intention": "describe_and_route_the_system_from_self_comprehension_root_without_rederiving_unchanged_substrate",
        "selected_paper_module_neighborhood": [
            "system_self_comprehension_root",
            "system_constitution_seed",
            "system_self_comprehension_spine",
            "prompt_shelf_uppropagation_ledger",
            "operational_work_item_spine",
            "local_to_general_propagation",
            "agent_self_observability_plane",
            "workingness_instrument",
            "navigation_hologram_theory",
        ],
        "selected_doctrine_neighborhood": [
            "pri_011",
            "pri_049",
            "pri_111",
            "con_001",
            "con_024",
            "con_018",
        ],
        "selected_standards": [
            "std_constitution_workspace",
            "std_system_term",
            "std_self_model",
            "std_agent_entry_surface",
            "std_paper_module",
            "std_navigation_contract",
            "std_raw_seed_compressed_projection",
        ],
        "selected_runtime_surfaces": [
            {
                "surface_id": "constitution_workspace_replay",
                "command": "./repo-python kernel.py --constitution-workspace-replay latest",
                "surface_role": CONTROL_ENTRY,
                "first_move_rule": "Check prior receipt reuse before recompiling stable self-description.",
            },
            {
                "surface_id": "what_am_i",
                "command": "./repo-python kernel.py --what-am-i \"<task>\" --context-budget 12000",
                "surface_role": CONTROL_ENTRY,
                "allowed_after": "constitution_workspace_replay reports no_prior_snapshot, refresh_live_state_only, or refresh_required",
            },
            {
                "surface_id": "vantage",
                "command": "./repo-python kernel.py --vantage --band card",
                "surface_role": CONTROL_ENTRY,
            },
            {
                "surface_id": "paper_modules",
                "command": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
                "surface_role": ATLAS_PROJECTION,
                "allowed_after": "constitution_workspace_selected_paper_module_neighborhood",
            },
        ],
        "authority_stack": [
            {
                "role": "source_authority",
                "artifact": "raw seed, doctrine graph, standards, WorkItems, receipts, generated sidecars, and live kernel/build outputs",
            },
            {"role": "root_contract", "artifact": SYSTEM_SELF_COMPREHENSION_ROOT_PATH},
            {"role": "profile_registry", "artifact": "codex/doctrine/compression_profiles.json"},
            {"role": "standard", "artifact": "codex/standards/std_constitution_workspace.json"},
            {"role": "compiler", "artifact": "system/lib/kernel/commands/comprehension_snapshot.py::build_what_am_i"},
            {"role": "projection", "artifact": "kernel.py --what-am-i / --vantage"},
            {"role": "drilldown", "artifact": "paper modules, standards, docs-route, debug traces"},
        ],
        "freshness_vector": source_graph,
        "source_graph_fingerprint": source_graph.get("fingerprint"),
        "live_state_fingerprint": source_graph.get("live_state_fingerprint"),
        "retread_guard": retread_guard,
        "propagation_graph": propagation_graph,
        "belief_or_workingness_posture": {
            "status": "provisional_until_replay_gate_and_prompt_adoption_are_entry_visible",
            "proof_surface": "workingness_instrument",
            "claim": "Current packet can prove source selection, fingerprint boundaries, and receipt replay posture; prompt behavior change remains partial until adoption reaches projected or observed entry behavior.",
        },
        "next_legal_edges": [
            "./repo-python kernel.py --constitution-workspace-replay latest",
            "./repo-python kernel.py --paper-module system_self_comprehension_root",
            "./repo-python kernel.py --row compression_profiles:ai_workflow_system_packet_v1 --band card",
            "./repo-python kernel.py --row compression_profiles:type_b_external_grounding_v1 --band card",
            "./repo-python kernel.py --row standards:std_constitution_workspace --band card",
            "./repo-python kernel.py --docs-route \"what am I\"",
            "./repo-python kernel.py --docs-route \"prompt shelf\"",
            "./repo-python kernel.py --docs-route \"WorkItem spine\"",
            "./repo-python kernel.py --docs-route \"operator intent propagation\"",
        ],
        "omission_receipts": [
            {
                "omitted": "full paper-module bodies",
                "why": "bounded first-contact packet",
                "recover_with": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            },
            {
                "omitted": "debug ranking internals",
                "why": "DEBUG_TRACE only",
                "recover_with": "./repo-python kernel.py --skill-find \"<query>\" --debug",
            },
        ],
        "debug_drilldowns": [
            {
                "surface_id": "comprehension_snapshot",
                "command": "./repo-python kernel.py --comprehension-snapshot",
                "surface_role": DRILLDOWN,
            }
        ],
        "ui_projection_hint": {
            "target": "Station Vantage / future Constitution lens",
            "api_surface": "GET /api/world-model/vantage now carries constitution_workspace; future /api/constitution can alias it.",
        },
        "injection_payload_hint": {
            "target_consumers": ["high_class_type_b", "bridge_worker", "external_reviewer"],
            "safe_contents": [
                "identity_claim",
                "major subsystem map",
                "authority hierarchy",
                "current state summary",
                "ASK_TYPE_A evidence protocol",
                "retread_guard status",
                "propagation_graph",
            ],
            "forbidden_contents": [
                "raw transcript",
                "secrets",
                "unbounded file lists",
                "debug ranking internals",
            ],
        },
    }


def _resolve_raw_seed_path(repo_root: Path) -> Path | None:
    preferred = repo_root / "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.md"
    if preferred.is_file():
        return preferred
    obsidian_root = repo_root / "obsidian"
    if not obsidian_root.is_dir():
        return None
    candidates = [path for path in obsidian_root.rglob("raw_seed.md") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _summarize_raw_seed_tail(repo_root: Path, *, limit: int) -> dict[str, Any]:
    path = _resolve_raw_seed_path(repo_root)
    if path is None:
        return {"available": False, "reason": "raw_seed.md not found"}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {
            "available": False,
            "source_ref": path.relative_to(repo_root).as_posix(),
            "reason": f"read failed: {exc}",
        }
    nonempty: list[dict[str, Any]] = []
    for idx, raw in enumerate(lines, start=1):
        text = raw.strip()
        if text:
            nonempty.append({"line": idx, "text": _truncate(text, limit=420)})
    return {
        "available": True,
        "source_ref": path.relative_to(repo_root).as_posix(),
        "line_count": len(lines),
        "tail_line_count": min(limit, len(nonempty)),
        "tail": nonempty[-limit:],
        "mutation_policy": "read_only_tail_summary_not_raw_seed_edit",
    }


def _summarize_recent_frontier(repo_root: Path, *, limit: int) -> dict[str, Any]:
    try:
        from system.lib.kernel_navigation import KernelNavigation
    except Exception as exc:
        return {"available": False, "reason": f"KernelNavigation import failed: {exc.__class__.__name__}: {exc}"}
    try:
        result = KernelNavigation(repo_root).build_frontier(limit)
    except Exception as exc:
        return {"available": False, "reason": f"frontier build failed: {exc.__class__.__name__}: {exc}"}
    payload = result.payload if isinstance(result.payload, dict) else {}
    entries = payload.get("recent_markdown") if isinstance(payload.get("recent_markdown"), list) else []
    return {
        "available": True,
        "summary": payload.get("summary") or {},
        "entries": [
            {
                "path": row.get("path"),
                "title": row.get("title"),
                "modified_at": row.get("modified_at"),
                "first_line": _truncate(row.get("first_line"), limit=240),
                "last_line": _truncate(row.get("last_line"), limit=240),
                "signals": row.get("signals") or [],
            }
            for row in entries[:limit] if isinstance(row, dict)
        ],
        "warnings": list(getattr(result, "warnings", []) or [])[:3],
        "drilldown_command": f"./repo-python kernel.py --frontier {limit}",
    }


def _summarize_operator_voice(repo_root: Path, *, frontier_limit: int, raw_seed_tail_limit: int) -> dict[str, Any]:
    frontier = _summarize_recent_frontier(repo_root, limit=frontier_limit)
    raw_seed_tail = _summarize_raw_seed_tail(repo_root, limit=raw_seed_tail_limit)
    gesture_evidence: dict[str, Any] | None = None
    if raw_seed_tail.get("available") and raw_seed_tail.get("tail"):
        newest_tail = raw_seed_tail["tail"][-1]
        gesture_evidence = {
            "source": "raw_seed_tail",
            "path": raw_seed_tail.get("source_ref"),
            "line": newest_tail.get("line"),
            "last_line": newest_tail.get("text"),
        }
    elif frontier.get("available") and frontier.get("entries"):
        newest = next(
            (
                row for row in frontier["entries"]
                if str(row.get("path") or "").startswith("obsidian/")
            ),
            frontier["entries"][0],
        )
        gesture_evidence = {
            "source": "recent_markdown_frontier",
            "path": newest.get("path"),
            "title": newest.get("title"),
            "last_line": newest.get("last_line"),
        }
    return {
        "vibe": _summarize_prime_directive_vibe(repo_root),
        "active_operator_gesture": {
            "status": "partial_projection",
            "evidence": gesture_evidence,
            "limitation": "Kernel projection can read disk frontier/raw-seed tail, not live chat prompts.",
        },
        "recent_markdown_frontier": frontier,
        "raw_seed_tail": raw_seed_tail,
    }


def _row_count(rows_by_kind: dict[str, dict[str, Any]], kind_id: str) -> int:
    return _as_int((rows_by_kind.get(kind_id) or {}).get("row_count"))


def _summarize_open_tensions(
    snapshot: dict[str, Any],
    rows_by_kind: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    tensions: list[dict[str, Any]] = []
    active_phase = snapshot.get("active_phase") if isinstance(snapshot.get("active_phase"), dict) else {}
    if not active_phase.get("active_phase_id"):
        tensions.append({
            "kind": "active_phase_unset",
            "severity": "medium",
            "summary": "Active phase id is absent in the comprehension snapshot.",
            "next": "./repo-python kernel.py --pulse",
        })
    for finding in (snapshot.get("drift_findings") or [])[:3]:
        if isinstance(finding, dict):
            tensions.append({
                "kind": finding.get("kind") or "drift_finding",
                "severity": "medium",
                "summary": finding.get("summary"),
                "next": "./repo-python kernel.py --comprehension-snapshot",
            })
    artifact_debt = _row_count(rows_by_kind, "artifact_projection_debt")
    if artifact_debt:
        tensions.append({
            "kind": "artifact_projection_debt",
            "severity": "medium",
            "summary": f"{artifact_debt} artifact projection debt row(s) are present.",
            "next": "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
            "surface_role": ATLAS_PROJECTION,
            "first_contact_allowed": False,
            "allowed_after": "entry_packet_selected_projection_debt_lane",
        })
    skill_debt = _row_count(rows_by_kind, "skill_compression_debt")
    if skill_debt:
        tensions.append({
            "kind": "skill_compression_debt",
            "severity": "low",
            "summary": f"{skill_debt} skill compression debt row(s) remain.",
            "next": "./repo-python kernel.py --option-surface skill_compression_debt --band flag",
            "surface_role": ATLAS_PROJECTION,
            "first_contact_allowed": False,
            "allowed_after": "entry_packet_selected_skill_debt_lane",
        })
    return tensions[:6]


def _rank_where_to_act_now(
    snapshot: dict[str, Any],
    rows_by_kind: dict[str, dict[str, Any]],
    work_spine: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    active_phase = snapshot.get("active_phase") if isinstance(snapshot.get("active_phase"), dict) else {}
    if active_phase.get("active_phase_id"):
        actions.append({
            "priority": 90,
            "kind": "active_phase_continue",
            "command": f"./repo-python kernel.py --phase {active_phase['active_phase_id']}",
            "surface_role": CONTROL_ENTRY,
            "first_contact_allowed": True,
            "reason": "Active phase is the current control plane anchor.",
        })
    else:
        actions.append({
            "priority": 88,
            "kind": "recover_control_anchor",
            "command": "./repo-python kernel.py --pulse",
            "surface_role": CONTROL_ENTRY,
            "first_contact_allowed": True,
            "reason": "No active phase id is present; recover live control state before broad work.",
        })
    if work_spine:
        totals = work_spine.get("totals") if isinstance(work_spine.get("totals"), dict) else {}
        ready = _as_int(totals.get("top_ready"))
        active = _as_int(totals.get("active_wip"))
        blockers = _as_int(totals.get("blockers"))
        signoff = _as_int(totals.get("signoff_needs"))
        if any((ready, active, blockers, signoff)):
            actions.append({
                "priority": 86,
                "kind": "task_ledger_work_spine_pressure",
                "command": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                "surface_role": ATLAS_PROJECTION,
                "first_contact_allowed": False,
                "allowed_after": "entry_packet_selected_task_ledger_lane",
                "reason": (
                    "Task Ledger pressure is available in work_spine: "
                    f"{ready} ready/schedulable, {active} active WIP, "
                    f"{blockers} blockers, {signoff} sign-off needs."
                ),
            })
    artifact_debt = _row_count(rows_by_kind, "artifact_projection_debt")
    if artifact_debt:
        actions.append({
            "priority": 84,
            "kind": "transaction_and_projection_debt",
            "command": "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
            "surface_role": ATLAS_PROJECTION,
            "first_contact_allowed": False,
            "allowed_after": "entry_packet_selected_projection_debt_lane",
            "reason": f"{artifact_debt} artifact projection debt row(s) can guide the next repair without new substrate.",
        })
    compliance = snapshot.get("compliance_ledger") if isinstance(snapshot.get("compliance_ledger"), dict) else {}
    ready_now = _as_int(compliance.get("ready_now_count"))
    if ready_now:
        actions.append({
            "priority": 80,
            "kind": "ready_compliance_campaigns",
            "command": "./repo-python kernel.py --option-surface compliance_ledger --band flag",
            "surface_role": ATLAS_PROJECTION,
            "first_contact_allowed": False,
            "allowed_after": "entry_packet_selected_compliance_lane",
            "reason": f"{ready_now} compliance worklist item(s) are ready now.",
        })
    skill_debt = _row_count(rows_by_kind, "skill_compression_debt")
    if skill_debt:
        actions.append({
            "priority": 72,
            "kind": "skill_compression_passports",
            "command": "./repo-python kernel.py --option-surface skill_compression_debt --band flag",
            "surface_role": ATLAS_PROJECTION,
            "first_contact_allowed": False,
            "allowed_after": "entry_packet_selected_skill_debt_lane",
            "reason": f"{skill_debt} skill rows still lack full compressed passports.",
        })
    actions.append({
        "priority": 60,
        "kind": "cold_agent_entry",
        "command": "./repo-python kernel.py --vantage --band card",
        "surface_role": CONTROL_ENTRY,
        "first_contact_allowed": True,
        "reason": "Use this composer as the one-packet first read before row drilldown.",
    })
    return sorted(actions, key=lambda row: -int(row.get("priority") or 0))[:5]


def build_vantage(repo_root: Path, *, band: str = "flag") -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compose the live "vantage" packet: a bounded view over the
      system identity, current state, lattice counts, cluster rollups, operator
      voice hints, open tensions, and where-to-act-now routing.
    - Mechanism: Pure projection over build_comprehension_snapshot plus
      existing option surfaces and frontier/raw-seed reads. It creates no new
      public kind and does not mutate substrate.
    """
    normalized_band, limits, warnings = _vantage_limits(band)
    snapshot = build_comprehension_snapshot(repo_root)
    kind_atlas = snapshot.get("kind_atlas") if isinstance(snapshot.get("kind_atlas"), dict) else {}
    rows_by_kind = _kind_rows(kind_atlas)
    lattice = _summarize_lattice_vantage(kind_atlas)
    cluster_rollups = _summarize_cluster_rollups(repo_root, limit=limits["clusters"])
    operator_voice = _summarize_operator_voice(
        repo_root,
        frontier_limit=limits["frontier"],
        raw_seed_tail_limit=limits["raw_seed_tail"],
    )
    system_identity = _summarize_constitution_identity(repo_root)
    source_graph = _build_constitution_source_graph(repo_root, snapshot)
    retread_guard = _build_retread_guard(repo_root, source_graph, fidelity_profile=normalized_band)
    propagation_graph = _build_propagation_graph(repo_root, source_graph, retread_guard)
    constitution_workspace = _build_constitution_workspace(
        band=normalized_band,
        snapshot=snapshot,
        identity=system_identity,
        source_graph=source_graph,
        retread_guard=retread_guard,
        propagation_graph=propagation_graph,
    )
    work_spine = _summarize_task_ledger_work_spine(
        repo_root,
        snapshot,
        limit=limits["clusters"],
    )
    open_tensions = _summarize_open_tensions(snapshot, rows_by_kind)
    return {
        "kind": "kernel.vantage",
        "schema_version": "vantage_v0",
        "surface_role": CONTROL_ENTRY,
        "first_contact_allowed": True,
        "generated_at": _utc_now(),
        "band": normalized_band,
        "ok": bool(lattice.get("available")),
        "status": "ok" if snapshot.get("ok") else "degraded_source_snapshot",
        "profile_status": "supported",
        "source_snapshot": {
            "kind": snapshot.get("kind"),
            "schema_version": snapshot.get("schema_version"),
            "generated_at": snapshot.get("generated_at"),
            "ok": snapshot.get("ok"),
        },
        "system_identity": system_identity,
        "constitution_workspace": constitution_workspace,
        "source_graph_fingerprint": source_graph.get("fingerprint"),
        "live_state_fingerprint": source_graph.get("live_state_fingerprint"),
        "retread_guard": retread_guard,
        "propagation_graph": propagation_graph,
        "current_state": {
            "active_phase": snapshot.get("active_phase"),
            "blackboard_advisory": snapshot.get("blackboard_advisory"),
            "recent_frontier": operator_voice.get("recent_markdown_frontier"),
        },
        "provider_capacity": {
            "compute_audit": snapshot.get("compute_audit"),
            "compute_workers": snapshot.get("compute_workers"),
        },
        "lattice": lattice,
        "cluster_rollups": cluster_rollups,
        "work_spine": work_spine,
        "operator_voice": operator_voice,
        "open_tensions": open_tensions,
        "where_to_act_now": _rank_where_to_act_now(snapshot, rows_by_kind, work_spine),
        "frontier_delta": {
            "status": retread_guard.get("status"),
            "source_graph_fingerprint": retread_guard.get("source_graph_fingerprint"),
            "reason": retread_guard.get("reason"),
            "retread_guard_ref": "retread_guard",
        },
        "kind_policy": {
            "new_public_kind_created": False,
            "receiver": "kernel projection composer over comprehension_snapshot and option_surface",
            "kind_atlas_kind_count": kind_atlas.get("kind_count"),
        },
        "surface_contract": surface_contract(
            surface_id="vantage",
            command="./repo-python kernel.py --vantage --band card",
            surface_role=CONTROL_ENTRY,
            authority_plane="control",
            first_contact_allowed=True,
            replacement=ENTRY_REPLACEMENT,
            allowed_callers=["agent_first_contact", "normal_task_entry", "entry_packet"],
            banned_callers=[],
            default_output_policy={
                "emits": "bounded_live_control_packet_plus_labeled_atlas_drilldowns",
                "debug_fields": "hidden",
            },
        ),
        "commands_composed": [
            "./repo-python kernel.py --comprehension-snapshot",
            "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            "./repo-python kernel.py --option-surface principles --band cluster_flag",
            "./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
            "./repo-python kernel.py --option-surface annex_distillation_patterns --band cluster_flag",
            "./repo-python kernel.py --option-surface raw_seed_shards --band flag",
            "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            f"./repo-python kernel.py --frontier {limits['frontier']}",
        ],
        "warnings": warnings,
        "non_goals": [
            "Does not install annex runtime code or create a graph-memory subsystem.",
            "Does not create a new option-surface kind.",
            "Does not mutate raw_seed, prompt shelf, or live pipeline state.",
        ],
    }


def build_what_am_i(
    repo_root: Path,
    *,
    task: str | None = None,
    band: str = "card",
    context_budget: int = 12000,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compile the constitution workspace as the explicit
      first-contact answer to "what am I?" for agents, Type B injection,
      bridge workers, and human exposition.
    - Mechanism: Reuse the live Vantage chassis, then stamp the task,
      budget, and constitution-workspace surface contract onto the packet.
    """
    task_text = str(task or "").strip()
    payload = build_vantage(repo_root, band=band)
    command = (
        f"./repo-python kernel.py --what-am-i {shlex.quote(task_text)} --context-budget {context_budget}"
        if task_text
        else "./repo-python kernel.py --what-am-i --context-budget 12000"
    )
    payload.update({
        "kind": "kernel.what_am_i",
        "schema_version": "constitution_workspace_packet_v0",
        "task": task_text,
        "context_budget": context_budget,
        "compiled_from": {
            "kind": "kernel.vantage",
            "schema_version": "vantage_v0",
            "surface_id": "vantage",
        },
        "surface_contract": surface_contract(
            surface_id="what_am_i",
            command=command,
            surface_role=CONTROL_ENTRY,
            authority_plane="control",
            first_contact_allowed=True,
            replacement=ENTRY_REPLACEMENT,
            allowed_callers=[
                "agent_first_contact",
                "type_b_injection",
                "bridge_worker_injection",
                "operator_exposition",
                "docs_entry",
            ],
            banned_callers=[],
            default_output_policy={
                "emits": "budgeted_self_comprehension_packet_family_entry",
                "debug_fields": "hidden",
            },
        ),
    })
    workspace = payload.get("constitution_workspace") if isinstance(payload.get("constitution_workspace"), dict) else {}
    workspace["requested_task"] = task_text
    workspace["requested_budget"] = context_budget
    payload["constitution_workspace"] = workspace
    return payload


def _build_constitution_workspace_receipt(
    repo_root: Path,
    packet: dict[str, Any],
    *,
    consumer: str = "type_a_agent",
) -> dict[str, Any]:
    workspace = packet.get("constitution_workspace") if isinstance(packet.get("constitution_workspace"), dict) else {}
    freshness = workspace.get("freshness_vector") if isinstance(workspace.get("freshness_vector"), dict) else {}
    propagation_graph = packet.get("propagation_graph") if isinstance(packet.get("propagation_graph"), dict) else {}
    created_at = _utc_now()
    source_fingerprint = packet.get("source_graph_fingerprint")
    live_fingerprint = packet.get("live_state_fingerprint")
    packet_id = "cwp_{stamp}_{source}_{live}".format(
        stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        source=str(source_fingerprint or "nosource")[:8],
        live=str(live_fingerprint or "nolive")[:8],
    )
    runtime_surfaces = []
    for row in workspace.get("selected_runtime_surfaces") or []:
        if isinstance(row, dict):
            runtime_surfaces.append({
                "surface_id": row.get("surface_id"),
                "command": row.get("command"),
                "surface_role": row.get("surface_role"),
            })
    receipt = {
        "kind": "constitution_workspace_packet_receipt",
        "schema_version": "constitution_workspace_packet_receipt_v0",
        "packet_id": packet_id,
        "created_at": created_at,
        "task": packet.get("task") or workspace.get("requested_task") or "",
        "consumer": consumer,
        "fidelity_profile": (workspace.get("fidelity_profile") or {}).get("selected_band") or packet.get("band"),
        "context_budget": packet.get("context_budget") or workspace.get("requested_budget"),
        "source_graph_fingerprint": source_fingerprint,
        "live_state_fingerprint": live_fingerprint,
        "stable_inputs": [
            {key: row.get(key) for key in ("path", "status", "sha256_16")}
            for row in (freshness.get("stable_inputs") or freshness.get("inputs") or [])
            if isinstance(row, dict)
        ],
        "live_inputs": freshness.get("live_state_inputs") or freshness.get("dynamic_inputs") or [],
        "propagation_graph_fingerprint": _stable_json_fingerprint({
            "nodes": propagation_graph.get("nodes") or [],
            "edges": propagation_graph.get("edges") or [],
            "verb_policy": propagation_graph.get("verb_policy") or {},
            "source_refs": propagation_graph.get("source_refs") or [],
        }),
        "selected_neighborhood": {
            "paper_modules": workspace.get("selected_paper_module_neighborhood") or [],
            "standards": workspace.get("selected_standards") or [],
            "doctrine": workspace.get("selected_doctrine_neighborhood") or [],
            "runtime_surfaces": runtime_surfaces,
        },
        "omission_receipts": workspace.get("omission_receipts") or [],
        "next_legal_edges": workspace.get("next_legal_edges") or [],
        "validation": {
            "status": "record_command_does_not_validate",
            "tests": [],
            "smokes": [],
            "entrypoint_health": "not_run_by_record_command",
        },
        "reuse_policy": {
            "safe_to_reuse_when": "same source_graph_fingerprint and compatible consumer/fidelity_profile",
            "refresh_live_state_when": "live_state_fingerprint differs but source_graph_fingerprint matches",
            "refresh_stable_substrate_when": "source_graph_fingerprint differs",
        },
        "source_packet": {
            "kind": packet.get("kind"),
            "schema_version": packet.get("schema_version"),
        },
        "ledger_owner": {
            "paths": {
                key: value.relative_to(repo_root).as_posix()
                for key, value in _constitution_workspace_ledger_paths(repo_root).items()
                if key != "root"
            },
            "write_surface": "kernel.py --what-am-i-record",
            "replay_surface": "kernel.py --constitution-workspace-replay latest",
        },
    }
    return receipt


def write_constitution_workspace_receipt(repo_root: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    paths = _constitution_workspace_ledger_paths(repo_root)
    paths["root"].mkdir(parents=True, exist_ok=True)
    with paths["packets"].open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
    _write_json_atomic(paths["latest"], receipt)
    return {
        "packets_path": paths["packets"].relative_to(repo_root).as_posix(),
        "latest_path": paths["latest"].relative_to(repo_root).as_posix(),
    }


def build_what_am_i_record(
    repo_root: Path,
    *,
    task: str | None = None,
    band: str = "card",
    context_budget: int = 12000,
    consumer: str = "type_a_agent",
) -> dict[str, Any]:
    packet = build_what_am_i(repo_root, task=task, band=band, context_budget=context_budget)
    receipt = _build_constitution_workspace_receipt(repo_root, packet, consumer=consumer)
    written = write_constitution_workspace_receipt(repo_root, receipt)
    return {
        "kind": "kernel.constitution_workspace.record",
        "schema_version": "constitution_workspace_record_v0",
        "surface_role": CONTROL_ENTRY,
        "first_contact_allowed": False,
        "generated_at": _utc_now(),
        "mutation": "wrote_constitution_workspace_packet_receipt",
        "write_surface": "kernel.py --what-am-i-record",
        "read_only_compiler": "kernel.py --what-am-i",
        "receipt": receipt,
        "written": written,
        "replay_command": "./repo-python kernel.py --constitution-workspace-replay latest",
        "packet_summary": {
            "kind": packet.get("kind"),
            "schema_version": packet.get("schema_version"),
            "source_graph_fingerprint": packet.get("source_graph_fingerprint"),
            "live_state_fingerprint": packet.get("live_state_fingerprint"),
            "retread_guard_status_before_record": (packet.get("retread_guard") or {}).get("status"),
        },
    }


def build_constitution_workspace_replay(
    repo_root: Path,
    selector: str | None = "latest",
    *,
    band: str | None = None,
    context_budget: int = 12000,
    consumer: str = "type_a_agent",
) -> dict[str, Any]:
    requested_selector = selector or "latest"
    if requested_selector != "latest":
        return {
            "kind": "kernel.constitution_workspace.replay",
            "schema_version": "constitution_workspace_replay_v0",
            "status": "unsupported_selector",
            "selector": requested_selector,
            "supported_selectors": ["latest"],
        }
    receipt = _load_latest_constitution_workspace_receipt(repo_root)
    replay_band = band
    if (not replay_band or replay_band == "flag") and isinstance(receipt, dict):
        replay_band = str(receipt.get("fidelity_profile") or "card")
    replay_band = replay_band or "card"
    task = receipt.get("task") if isinstance(receipt, dict) else "constitution workspace replay"
    current_packet = build_what_am_i(repo_root, task=task, band=replay_band, context_budget=context_budget)
    current_workspace = (
        current_packet.get("constitution_workspace")
        if isinstance(current_packet.get("constitution_workspace"), dict)
        else {}
    )
    current_source_graph = (
        current_workspace.get("freshness_vector")
        if isinstance(current_workspace.get("freshness_vector"), dict)
        else {}
    )
    comparison = _compare_receipt_to_source_graph(
        repo_root,
        receipt,
        current_source_graph,
        consumer=consumer,
        fidelity_profile=replay_band,
    )
    return {
        "kind": "kernel.constitution_workspace.replay",
        "schema_version": "constitution_workspace_replay_v0",
        "generated_at": _utc_now(),
        "selector": "latest",
        "status": comparison["status"],
        "safe_to_reuse_prior_packet": comparison["safe_to_reuse_prior_packet"],
        "required_action": comparison["required_action"],
        "comparison": comparison,
        "current_packet": {
            "kind": current_packet.get("kind"),
            "schema_version": current_packet.get("schema_version"),
            "task": current_packet.get("task"),
            "band": replay_band,
            "source_graph_fingerprint": current_packet.get("source_graph_fingerprint"),
            "live_state_fingerprint": current_packet.get("live_state_fingerprint"),
        },
        "prior_packet": comparison.get("prior_packet"),
        "reuse_policy": {
            "source_graph_fingerprint": "decides whether stable theory/exposition must be re-derived",
            "live_state_fingerprint": "decides whether current posture must be refreshed",
        },
        "ledger_paths": comparison.get("ledger_paths"),
    }


def _task_mentions_navigation(task: str) -> bool:
    text = task.casefold()
    tokens = (
        "atlas",
        "entry",
        "first-contact",
        "first contact",
        "navigation",
        "route",
        "routing",
        "skill-find",
        "skill find",
        "surface",
        "debug",
        "score",
        "matched_on",
        "token_overlap",
        "coverage",
        "command path economy",
        "command-path economy",
        "command economy",
        "command paths",
        "slow command",
        "slow commands",
        "command substrate",
        "command fast path",
        "command-substrate",
        "command cache",
        "command profile",
        "command spans",
        "command surface inventory",
        "command buffering",
        "command stampede",
        "process bottlenecks",
        "process-bottlenecks",
        "process diagnostics",
        "process diagnostic",
        "advisory process rows",
        "stale diagnostic",
        "stale diagnostics",
        "stale cache",
        "output bytes",
        "wait tax",
        "kernel pulse",
        "slow pulse",
        "pulse latency",
        "pulse hot path",
        "pulse hot-path",
        "kernel hot path",
        "kernel hot-path",
        "kernel bootstrap",
        "bootstrap efficiency",
        "bootstrap latency",
        "kernel surface speed",
        "entry surface performance",
        "navigation metabolism speed",
        "concurrent agents running commands",
        "mac crash from commands",
        "metabolism profile",
        "singleflight",
        "buffered command",
    )
    if any(token in text for token in tokens):
        return True
    projected_terms = _projected_situation_match_terms(
        REPO_ROOT,
        situation_id="navigation_enforcement",
        route_id="sit_navigation_enforcement",
    )
    return any(term in text for term in projected_terms)


def _task_mentions_navigation_repair(task: str | None) -> bool:
    """Detect navigation/agent-entry repair pressure under imperative wording.

    Generic imperative authoring should still route to the WorkItem spine, but
    an imperative complaint about the navigation layer itself ("fix broken agent
    entry", "dogfood the autonomous seed", "why is the atlas not used") belongs
    on the navigation-control lane. This predicate is intentionally phrase-led:
    single words like "surface" or "entry" are too broad to override authoring.
    """
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").split())
    if not text:
        return False
    phrases = (
        "agent entry",
        "agent entrypoint",
        "entrypoint",
        "entry surface",
        "entry surfaces",
        "first contact",
        "navigation layer",
        "real navigation layer",
        "navigation surface",
        "navigation surfaces",
        "route behavior",
        "route failure",
        "routing failure",
        "broken route",
        "broken routing",
        "broken agent entry",
        "kind atlas",
        "option surface",
        "coverage enforcement",
        "coverage matrix",
        "process audit",
        "navigation metabolism",
        "dogfood",
        "system comprehension",
        "navigation system",
        "type plane",
        "type routing",
        "standards type",
        "standards owned type",
        "annex logic transfer",
        "annex logic to standards",
        "annex integration",
        "standards adaptation lanes",
        "coverage atlas",
    )
    if any(phrase in text for phrase in phrases):
        return True
    projected_terms = _projected_situation_match_terms(
        REPO_ROOT,
        situation_id="navigation_enforcement",
        route_id="sit_navigation_enforcement",
    )
    return any(term in text for term in projected_terms)


def _task_mentions_organisation_control_plane(task: str | None) -> bool:
    """Detect requests to improve whole-system organisation/read-model routing."""
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").split())
    if not text:
        return False
    phrases = (
        "system organisation",
        "system organization",
        "improve organisation",
        "improve organization",
        "organisation control plane",
        "organization control plane",
        "organisational control plane",
        "organizational control plane",
        "without leaf cleanup",
        "not leaf cleanup",
        "not leaf repair",
        "stop leaf work",
        "avoid leaf work",
        "avoid leaf cleanup",
        "next action surface",
        "next action routing",
        "active organisational state",
        "active organizational state",
    )
    if any(phrase in text for phrase in phrases):
        return True
    tokens = set(text.split())
    return (
        ("organisation" in tokens or "organization" in tokens or "organise" in tokens or "organize" in tokens)
        and ("system" in tokens or "control" in tokens or "routing" in tokens or "entry" in tokens)
    )


def _task_mentions_active_execution_constellation(repo_root: Path, task: str | None) -> bool:
    """Detect requests about active work liveness across phase/Work Ledger state."""
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").split())
    if not text:
        return False
    projected_terms = _projected_situation_match_terms(
        repo_root,
        situation_id="active_execution_constellation",
        route_id="sit_active_execution_constellation",
    )
    if any(term in text for term in projected_terms):
        return True
    phrases = (
        "active execution constellation",
        "active work constellation",
        "active execution",
        "active work",
        "current work",
        "static subphase",
        "stagnant subphase",
        "stale subphase",
        "subphase pointer",
        "sub phase pointer",
        "subphase liveness",
        "sub phase liveness",
        "work ledger concurrency",
        "workitem work ledger",
        "parallel missions",
        "parallel mission",
        "concurrency robust",
        "concurrency robustness",
    )
    if any(phrase in text for phrase in phrases):
        return True
    tokens = set(text.split())
    mentions_phase = "subphase" in tokens or ("sub" in tokens and "phase" in tokens)
    mentions_runtime = bool({"active", "current", "stale", "stagnant", "static", "concurrency"} & tokens)
    mentions_work_ledger = "workitem" in tokens or ("work" in tokens and "ledger" in tokens)
    return (mentions_phase and mentions_runtime) or (mentions_work_ledger and "concurrency" in tokens)


def _task_mentions_doctrine_population(task: str | None) -> bool:
    """Detect raw-seed-to-doctrine population/crystallization requests.

    This lane is intentionally narrower than generic doctrine/standards work.
    It catches the operator pattern where "autonomous seed" or "dogfood" is
    paired with doctrine authorship, so those words do not get absorbed by the
    navigation-repair predicate.
    """
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").split())
    if not text:
        return False
    phrases = (
        "doctrine population",
        "doctrine derivation",
        "doctrine authorship",
        "populate doctrine",
        "populate concepts",
        "populate mechanisms",
        "populate principles",
        "populate paper modules",
        "concepts mechanisms principles paper modules",
        "concepts mechanisms principles",
        "raw seed to doctrine",
        "raw seed doctrine",
        "author doctrine from raw seed",
        "crystallize doctrine",
        "crystallise doctrine",
        "crystallize a doctrine object",
        "crystallise a doctrine object",
        "missing doctrine object",
        "highest leverage missing doctrine object",
        "durable new thought",
        "implicit scattered half written rediscovered",
        "implicit, scattered, half written",
        "self uppropagate doctrine",
        "self up propagate doctrine",
    )
    if any(phrase in text for phrase in phrases):
        return True
    terms = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in text.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    population_terms = {"populate", "derive", "derivation", "author", "authorship", "crystallize", "crystallise", "rediscovered"}
    evidence_terms = {"raw", "seed", "caps", "traces", "failures", "workflows"}
    return bool(
        ("doctrine" in terms or {"principles", "concepts", "mechanisms"} <= terms)
        and (terms & population_terms)
        and (terms & evidence_terms or "paper" in terms or "modules" in terms)
    )


def _task_mentions_agent_principle_authoring(task: str | None) -> bool:
    """Detect requests to add/refine/mint the Type A agent-principle lens.

    This is deliberately narrower than generic doctrine population. The lane is
    not a new principle schema; it is the standard-owned control packet for
    deciding whether a Type A behavior lesson belongs in an existing owner,
    an existing ``pri_*`` refinement, or a new ordinary principle row with an
    agent-principle scope.
    """
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    principle_phrases = (
        "agent principle",
        "agent principles",
        "type a principle",
        "type a principles",
        "type a behavior principle",
        "type a behaviour principle",
        "type a operating principle",
        "type a operating principles",
    )
    authoring_phrases = (
        "add",
        "mint",
        "author",
        "create",
        "propose",
        "proposal",
        "promote",
        "promotion",
        "refine",
        "standard",
        "curation",
        "govern",
        "route",
        "routed",
        "discoverable",
        "wire",
        "entry",
        "cap",
        "caps",
        "capture",
        "failure mode",
        "failure-mode",
    )
    return any(phrase in text for phrase in principle_phrases) and any(
        phrase in text for phrase in authoring_phrases
    )


def _task_mentions_cognitive_operator_discovery(task: str | None) -> bool:
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    phrases = (
        "missing cognitive operator",
        "cognitive operator",
        "autonomous seed",
        "thinking substrate",
        "structurally incapable",
        "changes cognition",
        "highest compounding value",
        "disconfirmation harness",
        "disconfirming evidence",
        "counterevidence",
        "counter evidence",
        "counterexample",
        "falsifier",
        "negative evidence",
        "route disagreement",
        "entry context pack disagreement",
    )
    if any(phrase in text for phrase in phrases):
        return True
    terms = {
        part.strip(".,:;!?()[]{}\"'`")
        for part in text.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    if {"cognitive", "operator"} <= terms or {"cognitive", "operators"} <= terms:
        return True
    if "operator" in terms and ({"cognition", "capability", "substrate", "autonomous"} & terms):
        return True
    return False


def _task_mentions_autonomous_seed_framework(task: str | None) -> bool:
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    explicit_cognitive_operator = (
        "cognitive operator" in text
        or "cognitive operators" in text
        or "counterevidence" in text
        or "counter evidence" in text
        or "disconfirmation harness" in text
    )
    if explicit_cognitive_operator:
        return False
    phrases = (
        "autonomous seed",
        "autonomous seeds",
        "wake prompt",
        "wake prompts",
        "seed prompt",
        "seed prompts",
        "type a autonomous seed",
        "type a seed loop",
        "repeated prompt",
        "repeated prompts",
        "prompt cluster",
        "prompt clusters",
        "seed corpus",
        "seed cohort",
        "seed setup",
        "rotautonomous",
        "no null edit",
    )
    return any(phrase in text for phrase in phrases)


def _task_mentions_autonomous_seed_replay_continuity(task: str | None) -> bool:
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").replace("_", " ").split())
    if not text or not _task_mentions_autonomous_seed_framework(text):
        return False
    phrases = (
        "replay",
        "replayed",
        "replay receipt",
        "seed replay",
        "continuation receipt",
        "continuity receipt",
        "replay dogfood",
        "dogfood hardening",
        "seed rehydration",
        "live seed rehydration",
        "seed recognition",
    )
    return any(phrase in text for phrase in phrases)


def _task_mentions_speed_refinement(task: str | None) -> bool:
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    phrases = (
        "speed refinement",
        "speed refinements",
        "command telemetry",
        "command timing",
        "command timings",
        "command latency",
        "meta diagnostic",
        "meta diagnostics",
        "process bottleneck",
        "process bottlenecks",
        "latency seed",
        "latency speedboard",
        "wait tax",
        "command profile",
        "command startup",
        "startup profile",
        "slow command",
        "slow commands",
        "command surface inventory",
    )
    if any(phrase in text for phrase in phrases):
        return True
    terms = {
        part.strip(".,:;!?()[]{}\"'`")
        for part in text.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    speed_terms = {
        "speed",
        "latency",
        "efficient",
        "efficiency",
        "optimise",
        "optimising",
        "optimisation",
        "optimize",
        "optimizing",
        "optimization",
        "timing",
        "timings",
        "throughput",
        "bottleneck",
        "bottlenecks",
        "wait",
        "tax",
    }
    telemetry_terms = {
        "command",
        "commands",
        "telemetry",
        "diagnostic",
        "diagnostics",
        "meta",
        "process",
        "profile",
        "profiles",
        "speedboard",
        "pytest",
        "validation",
        "runtime",
        "surface",
        "surfaces",
        "kernel",
        "startup",
    }
    return bool((terms & speed_terms) and (terms & telemetry_terms))


def _speed_refinement_routes_card() -> dict[str, Any]:
    return {
        "schema_version": "speed_refinement_routes_v0",
        "status": "available",
        "first_route_commands": [
            "./repo-python tools/meta/control/action_quote.py --action latency_seed_preflight",
            "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage",
            "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory",
            "./repo-python kernel.py --latency-seed-digest",
            "./repo-python kernel.py --process-bottlenecks",
            "./repo-python kernel.py --command-profile latency-speedboard",
        ],
    }


def _projection_match_variants(value: str) -> set[str]:
    text = " ".join(str(value or "").strip().casefold().split())
    if not text:
        return set()
    variants = {
        text,
        text.replace("_", " "),
        text.replace("-", " "),
        text.replace("/", " "),
    }
    out: set[str] = set()
    for variant in variants:
        clean = " ".join(variant.split())
        if clean:
            out.add(clean)
    return out


def _add_projected_match_value(terms: set[str], value: Any) -> None:
    if isinstance(value, str):
        for variant in _projection_match_variants(value):
            terms.add(variant)
        path = Path(value)
        for candidate in (path.name, path.stem):
            for variant in _projection_match_variants(candidate):
                terms.add(variant)
        return
    if isinstance(value, list):
        for item in value:
            _add_projected_match_value(terms, item)


def _projected_situation_match_terms(
    repo_root: Path,
    *,
    situation_id: str,
    route_id: str,
) -> set[str]:
    """Load task-match terms from the compressed route surfaces.

    The entry packet may classify a stable lane only after the lane exists in
    the projected navigation substrate. This keeps runtime classification from
    becoming a private phrase list that disagrees with AGENTS/docs-route rows.
    """
    terms: set[str] = set()
    projected_paths: set[str] = set()

    def _add_projected_path_values(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            projected_paths.add(value.strip())
        elif isinstance(value, list):
            for item in value:
                _add_projected_path_values(item)

    bootstrap = _read_json_safe(repo_root / "codex/doctrine/agent_bootstrap.json") or {}
    route: dict[str, Any] | None = None
    for row in bootstrap.get("situation_routes") or []:
        if not isinstance(row, dict):
            continue
        if row.get("situation_id") == situation_id or row.get("route_id") == route_id:
            route = row
            break
    if isinstance(route, dict):
        for key in (
            "situation_id",
            "route_id",
            "label",
            "match_tokens",
            "canonical_next_read",
            "minimum_read_set_id",
        ):
            _add_projected_match_value(terms, route.get(key))
        _add_projected_path_values(route.get("canonical_next_read"))
        actor_delivery = route.get("actor_delivery") or {}
        if isinstance(actor_delivery, dict):
            _add_projected_match_value(terms, actor_delivery.get("required_tokens"))
        for target in route.get("route_targets") or []:
            if not isinstance(target, dict):
                continue
            for key in ("ref", "label", "role", "relation", "match_tokens"):
                _add_projected_match_value(terms, target.get(key))
            _add_projected_path_values(target.get("ref"))
            _add_projected_path_values(target.get("command"))
            _add_projected_path_values(target.get("freshness_command"))
        minimum_read_sets = bootstrap.get("minimum_read_sets") or {}
        minimum_read_set_id = route.get("minimum_read_set_id")
        minimum_read_set = (
            minimum_read_sets.get(str(minimum_read_set_id))
            if isinstance(minimum_read_sets, dict) and minimum_read_set_id
            else None
        )
        if isinstance(minimum_read_set, dict):
            _add_projected_match_value(terms, minimum_read_set.get("paths"))
            _add_projected_path_values(minimum_read_set.get("paths"))

    docs_index = _read_json_safe(repo_root / "codex/doctrine/documentation_theory_index.json") or {}
    machine_routes = docs_index.get("machine_routes") or {}
    for row in machine_routes.get("situation_routes") or []:
        if not isinstance(row, dict) or row.get("route_id") != route_id:
            continue
        _add_projected_match_value(terms, row.get("route_id"))
        _add_projected_match_value(terms, row.get("authority_surfaces"))
        _add_projected_match_value(terms, row.get("local_artifacts"))
        _add_projected_path_values(row.get("authority_surfaces"))
        _add_projected_path_values(row.get("local_artifacts"))
        match = row.get("match") or {}
        if isinstance(match, dict):
            for key in ("exact_tokens", "tokens", "intent_terms", "path_contains", "exact_paths"):
                _add_projected_match_value(terms, match.get(key))

    skill_registry = _read_json_safe(repo_root / "codex/doctrine/skills/skill_registry.json") or {}
    for family in skill_registry.get("families") or []:
        if not isinstance(family, dict):
            continue
        for skill in family.get("skills") or []:
            if not isinstance(skill, dict):
                continue
            skill_file = str(skill.get("file") or "").strip()
            if skill_file not in projected_paths:
                continue
            for key in ("id", "title", "description", "triggers", "kernel_commands", "focus_paths"):
                _add_projected_match_value(terms, skill.get(key))
            for section_name, keys in (
                ("context_pack_anchors", ("trigger_phrases",)),
                ("compression_passport", ("cluster_keys", "atom", "flag", "card", "when_to_open")),
                ("holographic", ("one_liner", "one_line", "situation_signature")),
                ("agent_surface", ("does", "use_when", "entry")),
            ):
                section = skill.get(section_name) or {}
                if not isinstance(section, dict):
                    continue
                for key in keys:
                    _add_projected_match_value(terms, section.get(key))

    route_singleton_allowlist = {
        "dissemination",
        "outreach",
    }
    generic_singletons = {
        "agent",
        "agents",
        "assimilation",
        "bundle",
        "classifier",
        "classifiers",
        "blocked",
        "checkpoint",
        "clean",
        "commit",
        "commits",
        "compressed",
        "control",
        "demo",
        "detached",
        "entry",
        "external",
        "hologram",
        "holographic",
        "launch",
        "plane",
        "positioning",
        "projection",
        "surface",
        "surfaces",
        "publish",
        "published",
        "publication",
        "push",
        "pushed",
        "pushing",
        "recognition",
        "research",
        "router",
        "routing",
        "public",
        "docs",
        "readme",
        "route",
        "runtime",
        "standard",
        "standards",
        "task",
        "worktree",
    }
    generic_phrases = {
        "agent entry",
        "agent entry surface",
        "agent entry surfaces",
        "scoped commit",
        "scoped commit.py",
        "scoped_commit",
        "std agent entry surface",
        "std agent entry surface.json",
        "type a",
        "type b",
    }
    return {
        term
        for term in terms
        if len(term) >= 3
        and term not in generic_phrases
        and (" " in term or term in route_singleton_allowlist)
        and not (term in generic_singletons and term not in route_singleton_allowlist)
    }


def _task_mentions_dissemination_lane(repo_root: Path, task: str | None) -> bool:
    text = " ".join(str(task or "").casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    terms = _projected_situation_match_terms(
        repo_root,
        situation_id="dissemination_agent_entry",
        route_id="sit_dissemination_agent_entry",
    )
    return any(term in text for term in terms)


def _task_mentions_publication_lane_push_recovery(repo_root: Path, task: str | None) -> bool:
    text = " ".join(str(task or "").casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    terms = _projected_situation_match_terms(
        repo_root,
        situation_id="publication_lane_push_recovery",
        route_id="sit_publication_lane_push_recovery",
    )
    return any(term in text for term in terms)


def _projected_situation_route_command(
    repo_root: Path,
    *,
    situation_id: str,
    route_id: str,
    fallback: str,
) -> str:
    bootstrap = _read_json_safe(repo_root / "codex/doctrine/agent_bootstrap.json") or {}
    for row in bootstrap.get("situation_routes") or []:
        if not isinstance(row, dict):
            continue
        if row.get("situation_id") != situation_id and row.get("route_id") != route_id:
            continue
        command = str(row.get("route_command") or "").strip()
        return command or fallback
    return fallback


def _entry_next_action_surface_role(command: str) -> str:
    tokens: list[str]
    try:
        tokens = shlex.split(str(command or ""))
    except ValueError:
        return DRILLDOWN
    token_set = set(tokens)
    if {"--kind-atlas", "--option-surface", "--facts"} & token_set:
        return ATLAS_PROJECTION
    if "--skill-find" in token_set:
        return DEBUG_TRACE
    if {"--row", "--paper-module", "--paper-lattice", "--docs-route"} & token_set:
        return DRILLDOWN
    if (
        "publication_lane.py" in token_set
        or "mission_transaction_preflight.py" in token_set
    ):
        return DRILLDOWN
    return CONTROL_ENTRY


def _task_mentions_config_authority_plane(repo_root: Path, task: str | None) -> bool:
    text = " ".join(str(task or "").casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    terms = _projected_situation_match_terms(
        repo_root,
        situation_id="config_authority_plane",
        route_id="sit_config_authority_plane",
    )
    return any(term in text for term in terms)


def _task_mentions_microcosm_public_substrate(repo_root: Path, task: str | None) -> bool:
    text = " ".join(str(task or "").casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    terms = _projected_situation_match_terms(
        repo_root,
        situation_id="microcosm_public_substrate",
        route_id="sit_microcosm_public_substrate",
    )
    return any(term in text for term in terms)


def _task_is_type_b_handoff_framing_repair(task: str | None) -> bool:
    text = " ".join(str(task or "").casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    return any(
        phrase in text
        for phrase in (
            "make sure in agent entry",
            "when receiving a prompt",
            "small tweak in the framing",
            "understands the user is pasting",
            "user is pasting the full response",
        )
    )


def _task_mentions_type_b_to_type_a_handoff(repo_root: Path, task: str | None) -> bool:
    text = " ".join(str(task or "").casefold().replace("-", " ").replace("_", " ").split())
    if not text or _task_is_type_b_handoff_framing_repair(task):
        return False
    terms = _projected_situation_match_terms(
        repo_root,
        situation_id="type_b_to_type_a_continuation_handoff",
        route_id="sit_type_b_to_type_a_continuation_handoff",
    )
    return any(term in text for term in terms)


def _task_is_sender_side_type_b_ask(task: str | None) -> bool:
    text = " ".join(str(task or "").casefold().replace("-", " ").replace("_", " ").split())
    if not text:
        return False
    ask_markers = (
        "ask type b",
        "type b ask",
        "operator mediated type b",
        "operator hud type b",
    )
    response_markers = (
        "pasted",
        "paste ready type a continuation",
        "type a continuation prompt",
        "continuation response",
        "final call",
        "full response from type b",
    )
    return any(marker in text for marker in ask_markers) and not any(
        marker in text for marker in response_markers
    )


def _task_mentions_task_ledger_dependency_unlocks(task: str | None) -> bool:
    text = str(task or "").casefold()
    if not text:
        return False
    dependency_tokens = (
        "depends on",
        "dependency",
        "dependencies",
        "blocked by",
        "blocks",
        "blockers",
        "upstream_dependency_edges",
        "upstream dependency",
        "dependency_blocked",
    )
    unlock_tokens = (
        "unlock",
        "unlocks",
        "unlocking",
        "downstream_unlock_edges",
        "downstream unlock",
        "unlocks_by_rank",
    )
    cap_tokens = ("cap", "caps", "workitem", "work item", "task ledger", "todo")
    return (
        "upstream_dependency_edges" in text
        or "downstream_unlock_edges" in text
        or "unlocks_by_rank" in text
        or (
            any(token in text for token in cap_tokens)
            and (
                any(token in text for token in dependency_tokens)
                or any(token in text for token in unlock_tokens)
            )
        )
    )


def _task_mentions_mechanism_workitem_affinity(task: str | None) -> bool:
    text = " ".join(str(task or "").strip().casefold().replace("-", " ").split())
    if not text:
        return False
    phrases = (
        "mechanisms and workitems",
        "mechanisms and work items",
        "mechanism workitem",
        "mechanism work item",
        "mechanisms describe workitems",
        "mechanisms describe work items",
        "mechanisms describing workitems",
        "mechanisms describing work items",
        "merge mechanisms and workitems",
        "merge mechanisms and work items",
        "merge mechanisms with workitems",
        "merge mechanisms with work items",
        "mechanism workitem affinity",
        "mechanism work item affinity",
        "mechanism pressure cluster",
        "mechanism pressure clustering",
        "mechanisms cluster workitems",
        "mechanisms cluster work items",
        "mechanism backlog",
    )
    if any(phrase in text for phrase in phrases):
        return True
    has_mechanism = "mechanism" in text or "mechanisms" in text or "mech_" in text
    has_workitem = (
        "workitem" in text
        or "work item" in text
        or "workitems" in text
        or "work items" in text
        or "task ledger" in text
    )
    boundary_or_lens = (
        "affinity",
        "cluster",
        "clusters",
        "clustering",
        "pressure",
        "merge",
        "describe",
        "describing",
        "backlog",
    )
    return has_mechanism and has_workitem and any(token in text for token in boundary_or_lens)


_IMPERATIVE_AUTHORING_VERBS = (
    "create",
    "build",
    "wire",
    "implement",
    "add",
    "make",
    "author",
    "ship",
    "scaffold",
    "draft",
    "patch",
    "fix",
    "finish",
    "extend",
    "refactor",
    "organize",
    "organise",
    "reorganize",
    "reorganise",
    "migrate",
    "rewrite",
    "rebuild",
    "introduce",
    "land",
)


def _task_is_imperative_authoring(task: str | None) -> bool:
    """Detect imperative authoring intent.

    Imperative verbs ('create', 'wire', 'build', 'fix', etc.) override the
    read-only atlas/comprehension classification. A request like
    'create the system self-comprehension surface and wire it into
    dissemination' is authoring work, not a comprehension query, so it
    must route through the WorkItem/authoring lane rather than emitting a
    tier-0 observe-only context-pack as the next action.
    """
    text = str(task or "").strip().casefold()
    if not text:
        return False
    # First-token verb is the strongest signal.
    first = text.split(maxsplit=1)[0].strip(".,:;!?()[]{}\"'`")
    if first in _IMPERATIVE_AUTHORING_VERBS:
        return True
    # Otherwise look for any imperative verb followed by a noun phrase
    # somewhere in the task text. Bare mention of a verb word inside a
    # noun (e.g. "creation") would not match because we tokenize on
    # whitespace and punctuation.
    tokens = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in text.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    return bool(tokens & set(_IMPERATIVE_AUTHORING_VERBS))


def _task_mentions_system_atlas(task: str) -> bool:
    text = task.casefold()
    terms = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in task.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    phrases = (
        "what is this system",
        "what is the system",
        "one place",
        "understand the repo",
        "understand this repo",
        "repo self-comprehension",
        "self-comprehension atlas",
        "system self-comprehension",
        "system atlas",
        "substrate atlas",
        "whole system",
        "paper module hierarchy",
        "paper-module hierarchy",
        "system crystal",
        "private system crystal",
        "internal crystal",
        "ultimate distillation",
        "densest private self-model",
        "dense private self-model",
        "cap of caps",
    )
    if any(phrase in text for phrase in phrases):
        return True
    if "system" in terms and ({"atlas", "comprehension", "coverage", "substrate"} & terms):
        return True
    if "crystal" in terms and ({"system", "private", "whole"} & terms):
        return True
    if "distillation" in terms and ({"system", "self", "whole", "private"} & terms):
        return True
    if "densest" in terms and ({"system", "self", "whole"} & terms):
        return True
    if "repo" in terms and ({"atlas", "comprehension", "understand", "coverage"} & terms):
        return True
    return False


def _classify_frontend_capability_slices(task: str | None) -> list[str]:
    """Classify which frontend capability slices a task touches.

    Returns active slice slugs from: design-authoring, accessibility-audit,
    runtime-debug-performance, visual-verification, research-copy-handoff.
    Multiple slices may co-fire. Returns empty list if no frontend trigger.
    """
    if not task:
        return []
    text = task.casefold()
    terms = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in task.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    active: list[str] = []
    # design-authoring
    if any(p in text for p in ("dashboard clearer", "make this dashboard", "ai-sloppy", "ai sloppy", "ui mockup", "app mockup", "hi-fi prototype", "high-fidelity prototype", "design critique", "design review", "anti-ai-slop", "html prototype", "html mockup")):
        active.append("design-authoring")
    elif "ui" in terms and ({"polish", "design", "build", "mockup", "prototype", "clarity", "layout", "interaction"} & terms):
        active.append("design-authoring")
    elif ({"html"} & terms) and ({"prototype", "mockup"} & terms):
        active.append("design-authoring")
    elif ("high-fidelity" in text or "hi-fi" in text) and ({"prototype", "mockup"} & terms):
        active.append("design-authoring")
    # accessibility-audit
    if ({"a11y", "accessibility", "wcag", "aria"} & terms) or "screen reader" in text or "semantic html" in text or ("keyboard" in terms and ({"usability", "navigation", "support", "access"} & terms)):
        active.append("accessibility-audit")
    # runtime-debug-performance
    if ({"lcp", "cls", "inp"} & terms) or "core web vitals" in text or "layout shift" in text or ({"chrome", "devtools", "browser"} & terms and ({"debug", "perf", "performance", "memory", "network", "trace"} & terms)):
        active.append("runtime-debug-performance")
    # visual-verification
    if any(p in text for p in ("visually verify", "visual verify", "visual verification", "before/after", "pixel diff")) or ("screenshot" in terms and ({"verify", "diff", "before", "after", "compare"} & terms)):
        active.append("visual-verification")
    # research-copy-handoff
    if "ux copy" in text or "design system handoff" in text or "design-system handoff" in text or ({"ux"} & terms and ({"copy", "research"} & terms)):
        active.append("research-copy-handoff")
    return active


def _task_mentions_frontend_visual_memory(task: str | None) -> bool:
    """Return True for the governed per-view screenshot/settlement memory lane."""
    if not task:
        return False
    text = task.casefold()
    terms = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in task.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    phrases = (
        "screenshot ledger",
        "frontend screenshot ledger",
        "view observation memory",
        "view observation packet",
        "visual memory cell",
        "frontend visual memory",
        "frontend visual settlement",
        "latest visual delta",
    )
    if any(phrase in text for phrase in phrases):
        return True
    return bool(
        {"frontend", "front-end", "view", "views"} & terms
        and {"ledger", "observation", "settlement", "delta", "memory"} & terms
        and {"visual", "screenshot", "render"} & terms
    )


def _frontend_capability_enrichment(
    repo_root: Path,
    active_slices: list[str],
) -> dict[str, Any] | None:
    """Build the parallel frontend capability enrichment field for the entry packet.

    Reads carriers from the source-controlled authored seed at
    `codex/doctrine/skills/frontend/capability_lanes.json` so the Python
    layer never duplicates the carrier matrix. Returns None when no
    frontend slice is active so negative prompts emit no field.
    """
    if not active_slices:
        return None
    seed_ref = "codex/doctrine/skills/frontend/capability_lanes.json"
    runtime_ref = "state/system_atlas/frontend_capability_lanes.json"
    runtime_path = repo_root / runtime_ref
    seed_path = repo_root / seed_ref

    payload: dict[str, Any] | None = None
    projection_read_status = "seed_fallback_used"
    used_path_label = seed_ref
    runtime_load_error: str | None = None
    if runtime_path.exists():
        try:
            payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            projection_read_status = "runtime_projection_used"
            used_path_label = runtime_ref
        except Exception as exc:
            runtime_load_error = f"runtime_unreadable:{type(exc).__name__}"
            payload = None
    if payload is None:
        try:
            payload = json.loads(seed_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            payload = {"capability_slices": []}
            projection_read_status = "missing_seed_and_runtime"
        except Exception as exc:
            payload = {"capability_slices": []}
            projection_read_status = f"unreadable:{type(exc).__name__}"

    by_slice: dict[str, dict[str, Any]] = {}
    for row in payload.get("capability_slices", []) or []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slice") or "").strip()
        if slug:
            by_slice[slug] = row

    carrier_summary: list[dict[str, Any]] = []
    for slice_id in active_slices:
        row = by_slice.get(slice_id) or {}
        raw_carriers = row.get("carriers") or []
        carriers: list[dict[str, Any]] = []
        for carrier in raw_carriers[:8]:
            if not isinstance(carrier, dict):
                continue
            entry: dict[str, Any] = {
                "carrier_lane": carrier.get("carrier_lane"),
                "id": carrier.get("id"),
                "availability_status": carrier.get("availability_status"),
            }
            for opt_key in ("observed_availability", "evidence_result", "drift_risk", "evidence_ref", "legacy_or_current_unresolved"):
                v = carrier.get(opt_key)
                if v not in (None, ""):
                    entry[opt_key] = v
            carriers.append(entry)
        carrier_summary.append({"slice": slice_id, "carriers": carriers})

    out: dict[str, Any] = {
        "domain": "frontend",
        "active_slices": active_slices,
        "source": "kernel.entry_packet.frontend_capability_discovery",
        "source_ref": seed_ref,
        "projection_ref": runtime_ref,
        "projection_read_status": projection_read_status,
        "used_path": used_path_label,
        "entry_behavior": "parallel_enrichment_not_top_level_precedence",
        "availability_boundary": (
            "carrier availability is evidence-backed; session-advertised skills are drift-prone; "
            "registry projection != publication topology != session advertisement != invocation"
        ),
        "carrier_summary": carrier_summary,
    }
    if runtime_load_error:
        out["runtime_load_error"] = runtime_load_error
    return out


def _task_mentions_frontend_capability_discovery(task: str | None) -> bool:
    if not task:
        return False
    text = task.casefold()
    terms = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in task.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    phrases = (
        "ai-sloppy", "ai sloppy", "less ai-sloppy",
        "design system handoff", "design-system handoff",
        "high-fidelity prototype", "hi-fi prototype",
        "html prototype", "html mockup",
        "react page", "react component",
        "core web vitals", "layout shift",
        "before/after", "visually verify", "visual verify", "visual verification",
        "dashboard clearer", "make this look", "make this dashboard",
        "ux copy", "ui mockup", "app mockup",
        "design critique", "design review",
        "screen reader", "semantic html",
        "anti-ai-slop", "anti ai slop",
    )
    if any(phrase in text for phrase in phrases):
        return True
    if ({"html"} & terms) and ({"prototype", "mockup"} & terms):
        return True
    if ("high-fidelity" in text or "hi-fi" in text) and ({"prototype", "mockup"} & terms):
        return True
    if {"a11y", "accessibility"} & terms:
        return True
    if {"lcp", "cls", "inp"} & terms:
        return True
    if "screenshot" in terms and ({"verify", "diff", "before", "after", "compare"} & terms):
        return True
    if "frontend" in terms or "front-end" in terms:
        return True
    if "ui" in terms and ({"polish", "design", "build", "mockup", "prototype", "clarity", "layout", "interaction"} & terms):
        return True
    if "ux" in terms:
        return True
    if {"chrome", "devtools", "browser"} & terms and ({"debug", "perf", "performance", "memory", "network", "trace"} & terms):
        return True
    if "keyboard" in terms and ({"usability", "navigation", "support", "access"} & terms):
        return True
    if "wcag" in terms or "aria" in terms:
        return True
    return False


def _task_mentions_frontend_page_meta_contract(task: str | None) -> bool:
    """Lexically narrow predicate for the frontend page-meta contract route.

    Requires a strong page-meta scent — bare ``frontend``, bare ``documentation``,
    or bare ``navigation`` must not trigger this lane. Either an exact phrase
    (``page meta``, ``page-meta``, ``PageHeader``, ``PageIdentityBadge``, etc.)
    or a conjunction of (role: frontend/station/lens) AND (surface: page/lens)
    AND (meta-scent: meta/metadata/self-description/purpose/principles/decisions/
    overwhelm) is required. The predicate is placed before ``is_navigation`` in
    the ``recognized_situation`` and ``selected_lane`` chains so the page-meta
    contract surfaces from natural cold-start phrases instead of being absorbed
    by the generic navigation lane.
    """
    if not task:
        return False
    text = task.casefold()
    terms = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in task.split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    phrases = (
        "page meta",
        "page-meta",
        "page_meta",
        "page metadata",
        "page meta documentation",
        "page meta contract",
        "page-meta contract",
        "frontend page meta",
        "lens self description",
        "lens self-description",
        "page self description",
        "page self-description",
        "station lens meta",
        "station coverage page",
        "pageheader purpose",
        "pageidentitybadge purpose",
        "page purpose principles decisions",
        "purpose principles decisions navigation",
    )
    if any(phrase in text for phrase in phrases):
        return True
    component_terms = {"pageheader", "pageidentitybadge"}
    if component_terms & terms:
        return True
    role_terms = {"frontend", "station", "lens"}
    surface_terms = {"page", "lens", "lenses", "pages"}
    meta_terms = {
        "meta",
        "metadata",
        "self-description",
        "purpose",
        "principles",
        "decisions",
        "overwhelm",
    }
    has_role = bool(role_terms & terms)
    has_surface = bool(surface_terms & terms)
    has_meta = bool(meta_terms & terms) or "self-description" in text or "self description" in text
    if has_role and has_surface and has_meta:
        return True
    return False


def _task_mentions_kind_atlas_browse(task: str | None) -> bool:
    """Detect explicit requests to use the typed artifact-kind ladder.

    This is deliberately lexical and narrow. The Kind Atlas is not a semantic
    answer engine; it is the row-0 contents page for artifact kinds. When an
    operator names that layer, entry should route to the atlas directly instead
    of wrapping the request in context-pack or navigation-metabolism prose.
    """
    text = str(task or "").strip().casefold()
    if not text:
        return False
    compact = text.replace("-", " ")
    phrases = (
        "--kind-atlas",
        "kind atlas",
        "kind-atlas",
        "option surface",
        "option-surface",
        "russian doll",
        "artifact kind",
        "artifact kinds",
        "typed layer",
        "typed layers",
        "use the atlas",
        "try using the atlas",
        "atlas never used",
    )
    if any(phrase in compact for phrase in phrases):
        # A bare System Atlas request is a whole-system snapshot request; keep
        # that on the system_comprehension_atlas lane unless the operator also
        # names Kind Atlas / option-surface / typed layers.
        if "system atlas" in compact and not any(
            phrase in compact
            for phrase in (
                "--kind-atlas",
                "kind atlas",
                "kind-atlas",
                "option surface",
                "option-surface",
                "artifact kind",
                "artifact kinds",
                "typed layer",
                "typed layers",
            )
        ):
            return False
        return True
    return False


def _state_axis_for_task(task: str | None) -> tuple[str, str] | None:
    text = str(task or "").casefold()
    compact = text.replace("-", " ")
    if "what" not in compact and "which" not in compact and "show" not in compact:
        return None
    if "banned" in compact or "ban " in compact:
        return ("tag", "banned")
    if "stale" in compact or "freshness" in compact or "source changed" in compact:
        return ("tag", "stale")
    if "first contact allowed" in compact or "first contact" in compact:
        return ("facet", "first_contact_policy")
    return None


def _task_mentions_state_axis_overview(task: str | None) -> bool:
    text = str(task or "").casefold()
    compact = text.replace("-", " ")
    phrases = (
        "state axes",
        "state axis",
        "what states can things be in",
        "states can things be in",
        "compressed state universe",
        "state universe",
        "state facts",
        "fact state plane",
        "fact state",
        "state rows",
        "what states exist",
    )
    return any(phrase in compact for phrase in phrases)


def _task_mentions_disclosure_query(task: str | None) -> bool:
    text = str(task or "").casefold()
    compact = text.replace("-", " ")
    if "what" not in compact and "which" not in compact and "show" not in compact:
        return False
    return any(
        phrase in compact
        for phrase in (
            "private",
            "public",
            "disclosure",
            "private root",
            "private_root_only",
            "public safe",
        )
    )


def _task_mentions_projection_closure_audit(task: str | None) -> bool:
    text = str(task or "").casefold()
    phrases = (
        "not projected",
        "missing projection",
        "projection closure",
        "tribal knowledge",
        "behavior-affecting clauses",
        "behaviour-affecting clauses",
        "not compiled",
        "unprojected",
    )
    return any(phrase in text for phrase in phrases)


def build_entry_packet(
    repo_root: Path,
    *,
    task: str | None = None,
    context_budget: int = 12000,
    include_transaction_control_plane: bool | None = None,
) -> dict[str, Any]:
    """Compile task + live state into one first-contact control packet."""
    from system.lib.task_ledger_priority import (
        detect_workitem_ids,
        find_workitem_by_id,
        top_ready_workitem,
        top_schedulable_workitem,
    )

    task_text = str(task or "").strip()
    task_arg = shlex.quote(task_text) if task_text else ""
    # Entry is the cheapest control route. Do not compile the full
    # comprehension snapshot here; it pulls kind-atlas, reaction, and bridge
    # summaries that are evidence drilldowns, not required entry decisions.
    active_phase = _summarize_active_phase(repo_root)
    # Task Ledger first-contact routing: if the task names a WorkItem id, the
    # entry packet must select it (route-by-id), not silently default to the
    # active phase. Always surface the top ready/rank-1 WorkItem too so cold
    # agents see the P0 even when they never typed an id.
    explicit_workitem_ids = detect_workitem_ids(task_text)
    selected_workitem_payload: dict[str, Any] | None = None
    for wid in explicit_workitem_ids:
        match = find_workitem_by_id(repo_root, wid)
        if match is not None:
            selected_workitem_payload = match
            break
    top_ready_payload = top_ready_workitem(repo_root)
    top_schedulable_payload = top_schedulable_workitem(repo_root)
    from system.lib.active_execution_constellation import (
        build_active_execution_constellation,
        compact_active_execution_constellation_for_entry,
    )

    active_execution_constellation = compact_active_execution_constellation_for_entry(
        build_active_execution_constellation(
            repo_root,
            active_phase=active_phase,
            top_schedulable_workitem=top_schedulable_payload,
            top_ready_workitem=top_ready_payload,
            campaign_limit=4,
            claim_limit=8,
            session_limit=6,
        )
    )
    latest_intent_gate = build_latest_intent_gate(task_text)
    is_agent_trouble_diagnosis = task_mentions_agent_trouble_diagnosis(task_text)
    is_imperative_authoring = _task_is_imperative_authoring(task_text)
    state_axis = _state_axis_for_task(task_text)
    is_state_axis_overview = _task_mentions_state_axis_overview(task_text)
    is_disclosure_query = _task_mentions_disclosure_query(task_text)
    is_projection_closure_audit = _task_mentions_projection_closure_audit(task_text)
    is_speed_refinement = _task_mentions_speed_refinement(task_text)
    is_task_ledger_dependency_unlocks = _task_mentions_task_ledger_dependency_unlocks(task_text)
    is_mechanism_workitem_affinity = _task_mentions_mechanism_workitem_affinity(task_text)
    is_doctrine_population = _task_mentions_doctrine_population(task_text)
    is_type_b_to_type_a_handoff = _task_mentions_type_b_to_type_a_handoff(repo_root, task_text)
    is_agent_principle_authoring = (
        _task_mentions_agent_principle_authoring(task_text)
        and not is_type_b_to_type_a_handoff
    )
    is_organisation_control_plane = (
        _task_mentions_organisation_control_plane(task_text)
        and not is_type_b_to_type_a_handoff
    )
    base_navigation_match = _task_mentions_navigation(task_text)
    is_active_execution_constellation = (
        _task_mentions_active_execution_constellation(repo_root, task_text)
        and not base_navigation_match
        and not is_type_b_to_type_a_handoff
    )
    mentions_autonomous_seed_framework = _task_mentions_autonomous_seed_framework(task_text)
    mentions_autonomous_seed_replay_continuity = _task_mentions_autonomous_seed_replay_continuity(
        task_text
    )
    is_navigation_repair = (
        _task_mentions_navigation_repair(task_text)
        and not is_doctrine_population
        and not mentions_autonomous_seed_replay_continuity
    )
    is_autonomous_seed_framework = (
        mentions_autonomous_seed_framework
        and (not is_speed_refinement or mentions_autonomous_seed_replay_continuity)
        and not is_doctrine_population
        and not is_navigation_repair
    )
    is_cognitive_operator_discovery = (
        _task_mentions_cognitive_operator_discovery(task_text)
        and not is_autonomous_seed_framework
        and not is_speed_refinement
        and not is_doctrine_population
        and not is_navigation_repair
    )
    is_frontend_capability_discovery = _task_mentions_frontend_capability_discovery(task_text)
    frontend_capability_slices = (
        _classify_frontend_capability_slices(task_text) if is_frontend_capability_discovery else []
    )
    is_frontend_visual_memory = _task_mentions_frontend_visual_memory(task_text)
    is_frontend_page_meta_contract = _task_mentions_frontend_page_meta_contract(task_text)
    is_sender_side_type_b_ask = is_type_b_to_type_a_handoff and _task_is_sender_side_type_b_ask(
        task_text
    )
    is_publication_lane_push_recovery = _task_mentions_publication_lane_push_recovery(
        repo_root,
        task_text,
    )
    is_config_authority_plane = (
        not is_type_b_to_type_a_handoff
        and not is_publication_lane_push_recovery
        and _task_mentions_config_authority_plane(repo_root, task_text)
    )
    is_microcosm_public_substrate = (
        not is_type_b_to_type_a_handoff
        and not is_publication_lane_push_recovery
        and not is_config_authority_plane
        and _task_mentions_microcosm_public_substrate(repo_root, task_text)
    )
    is_dissemination_lane = (
        not is_type_b_to_type_a_handoff
        and not is_publication_lane_push_recovery
        and not is_config_authority_plane
        and not is_microcosm_public_substrate
        and _task_mentions_dissemination_lane(repo_root, task_text)
    )
    is_kind_atlas_browse = (
        _task_mentions_kind_atlas_browse(task_text)
        and not (is_imperative_authoring and is_navigation_repair)
        and not is_type_b_to_type_a_handoff
        and not is_publication_lane_push_recovery
        and not is_config_authority_plane
        and not is_microcosm_public_substrate
        and not is_frontend_visual_memory
        and not is_dissemination_lane
        and not is_cognitive_operator_discovery
        and not is_doctrine_population
        and not is_agent_principle_authoring
        and not is_organisation_control_plane
        and state_axis is None
        and not is_state_axis_overview
        and not is_projection_closure_audit
    )
    # Imperative authoring intent ("create ...", "wire ...", "build ...",
    # "fix ...") overrides the read-only atlas/comprehension classification.
    # The user is asking for change, not a read; routing the request through
    # a tier-0 observe-only context-pack would mis-frame it as browsing.
    is_system_atlas = (
        _task_mentions_system_atlas(task_text)
        and not is_kind_atlas_browse
        and not is_imperative_authoring
        and not is_microcosm_public_substrate
    )
    is_navigation = (
        ((base_navigation_match and not is_imperative_authoring) or is_navigation_repair)
        and not is_system_atlas
        and not is_kind_atlas_browse
        and not is_type_b_to_type_a_handoff
        and not is_publication_lane_push_recovery
        and not is_config_authority_plane
        and not is_microcosm_public_substrate
        and not is_dissemination_lane
        and not is_cognitive_operator_discovery
        and not is_doctrine_population
        and not is_agent_principle_authoring
        and not is_organisation_control_plane
        and not is_mechanism_workitem_affinity
        and state_axis is None
        and not is_state_axis_overview
    ) or is_projection_closure_audit or (is_speed_refinement and not is_autonomous_seed_framework)
    config_authority_command = _projected_situation_route_command(
        repo_root,
        situation_id="config_authority_plane",
        route_id="sit_config_authority_plane",
        fallback="./repo-python kernel.py --option-surface config_authorities --band cluster_flag",
    )
    microcosm_public_substrate_command = _projected_situation_route_command(
        repo_root,
        situation_id="microcosm_public_substrate",
        route_id="sit_microcosm_public_substrate",
        fallback="./repo-python kernel.py --paper-module microcosm_substrate",
    )
    mechanism_workitem_affinity_command = _projected_situation_route_command(
        repo_root,
        situation_id="mechanism_workitem_affinity",
        route_id="sit_mechanism_workitem_affinity",
        fallback=(
            f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
            if task_text
            else "./repo-python kernel.py --option-surface mechanisms --band flag"
        ),
    )
    type_b_handoff_reason = (
        "Task asks the current Type A repo agent to ask Type B; resolve Type A/B through actor axes, explore the live substrate, prepare a paste-ready external/HUD/bridge ask, and verify any returned synthesis before acting."
        if is_sender_side_type_b_ask
        else "Operator pasted a Type B/bridge continuation response; the current repo agent is Type A, so execute the embedded Type A continuation prompt after verifying live repo state before any actuator."
    )
    effective_imperative_authoring = (
        is_imperative_authoring
        and not is_autonomous_seed_framework
        and not is_cognitive_operator_discovery
        and not is_doctrine_population
        and not is_agent_principle_authoring
        and not is_organisation_control_plane
        and not is_active_execution_constellation
        and not is_agent_trouble_diagnosis
        and not is_navigation
        and not is_publication_lane_push_recovery
        and not is_config_authority_plane
        and not is_frontend_visual_memory
    )
    selected_lane = {
        "lane_id": (
            "agent_trouble_diagnosis_seed"
            if is_agent_trouble_diagnosis
            else "system_state_axis_overview"
            if is_state_axis_overview and not is_projection_closure_audit
            else "system_state_fact_query"
            if state_axis is not None and not is_projection_closure_audit
            else "system_disclosure_query"
            if is_disclosure_query and not is_projection_closure_audit
            else "projection_closure_audit"
            if is_projection_closure_audit
            else "type_a_autonomous_seed_framework"
            if is_autonomous_seed_framework
            else "navigation_enforcement"
            if is_speed_refinement
            else "cognitive_operator_discovery"
            if is_cognitive_operator_discovery
            else "organisation_control_plane"
            if is_organisation_control_plane
            else "active_execution_constellation"
            if is_active_execution_constellation
            else "russian_doll_option_surface_entry"
            if is_kind_atlas_browse
            else "system_comprehension_atlas"
            if is_system_atlas
            else "microcosm_public_substrate"
            if is_microcosm_public_substrate
            else "type_b_to_type_a_continuation_handoff"
            if is_type_b_to_type_a_handoff
            else "dissemination_agent_entry"
            if is_dissemination_lane
            else "publication_lane_push_recovery"
            if is_publication_lane_push_recovery
            else "config_authority_plane"
            if is_config_authority_plane
            else "frontend_visual_memory"
            if is_frontend_visual_memory
            else "frontend_page_meta_contract"
            if is_frontend_page_meta_contract
            else "agent_principle_authoring"
            if is_agent_principle_authoring
            else "doctrine_population"
            if is_doctrine_population
            else "mechanism_workitem_affinity"
            if is_mechanism_workitem_affinity
            else "navigation_enforcement"
            if is_navigation
            else "task_ledger_dependency_unlocks"
            if is_task_ledger_dependency_unlocks
            else "active_phase"
        ),
        "reason": (
            "Latest operator message asks to diagnose agent trouble/transcript behavior; use the read-only trouble-diagnosis route and keep quoted prior seeds as evidence, not live instructions."
            if is_agent_trouble_diagnosis
            else "Task asks for the compressed state-axis universe; open the generated fact navigation artifact."
            if is_state_axis_overview and not is_projection_closure_audit
            else "Task asks for cross-kind state; route through the generated fact state-axis artifact."
            if state_axis is not None and not is_projection_closure_audit
            else "Task asks for disclosure/private/public state; route through context-pack/System Atlas until a disclosure fact family exists."
            if is_disclosure_query and not is_projection_closure_audit
            else "Task asks what doctrine/state is not projected; route to the projection-closure audit ratchet."
            if is_projection_closure_audit
            else "Task asks about autonomous seeds, wake prompts, repeated prompt clusters, or seed cohorts; open the Type A autonomous-seed framework, prompt-authoring standard, seed corpus, and wake-prompt diagnostics before generic cognitive-operator routing."
            if is_autonomous_seed_framework
            else "Task asks for speed refinements; open existing command telemetry, latency-seed, process-bottleneck, command-profile, and speedboard surfaces before generic autonomous-seed or cognitive-operator routing."
            if is_speed_refinement
            else "Task asks for autonomous cognitive-operator discovery or counterevidence handling; open the cognitive operator surface through context-pack before ordinary active-phase work."
            if is_cognitive_operator_discovery
            else "Task asks for system organisation; compose closeout, dirty ownership, Task Ledger, generated-state, and stale-doctrine lanes before selecting any leaf repair."
            if is_organisation_control_plane
            else "Task asks what work is actually live across static phase anchors, Task Ledger, Work Ledger, and Type A/B concurrency; use Active Execution Constellation instead of treating active_phase as sole liveness authority."
            if is_active_execution_constellation
            else "Task explicitly asks for the typed artifact-kind ladder; open Kind Atlas before context-pack, metabolism, semantic routing, or source evidence."
            if is_kind_atlas_browse
            else "Task asks for broad system comprehension; route through context-pack so the self-comprehension root, packet profiles, and System Atlas are selected before drilldown."
            if is_system_atlas
            else "Task is about the public Microcosm product/substrate entry; open microcosm_substrate/std_microcosm and the public entry packet before the legacy Laboratory system_microcosm compatibility route."
            if is_microcosm_public_substrate
            else type_b_handoff_reason
            if is_type_b_to_type_a_handoff
            else "Task enters dissemination; route through the dissemination skill family and router before opening the 70+ document directory or treating entry as a generic navigation audit."
            if is_dissemination_lane
            else "Task is a push/publication failure; use the publication lane planner and push bloat gate before retrying direct push or inventing a branch."
            if is_publication_lane_push_recovery
            else "Task asks about the federated config authority plane; open the projected config authority route before raw master_config, Settings, or direct source edits."
            if is_config_authority_plane
            else "Task asks for the per-view screenshot-ledger / View Observation Memory lane; open the frontend visual-memory route before raw PNG folders, station_render internals, or generic artifact discovery."
            if is_frontend_visual_memory
            else "Task asks for the frontend page-meta contract / Station lens self-description (purpose, principles, decisions, navigation, overwhelm control); open the constitutional contract before editing PageHeader/PageIdentityBadge or surfaces.ts."
            if is_frontend_page_meta_contract
            else "Task asks to add, refine, mint, or route Type A agent principles; open the standard-owned authoring packet before principle curation or raw-seed apply mutation."
            if is_agent_principle_authoring
            else "Task asks to populate or crystallize doctrine from raw seed; route through doctrine_derivation, the doctrine_population_loop roof, bounded evidence, owning-plane classification, projection refresh, and local-to-general propagation."
            if is_doctrine_population
            else "Task asks how mechanisms relate to WorkItems; preserve the authority split and open the mechanism/Task Ledger affinity lens before mutating either side."
            if is_mechanism_workitem_affinity
            else "Task concerns navigation/control/debug surface boundaries."
            if is_navigation
            else "Task asks about WorkItem/cap dependencies or downstream unlocks; open Task Ledger dependency projections and card edge summaries."
            if is_task_ledger_dependency_unlocks
            else "Default to the active phase control anchor."
        ),
    }
    state_axis_command = None
    if state_axis is not None:
        axis_kind, axis_value = state_axis
        if axis_kind == "tag":
            state_axis_command = f"./repo-python kernel.py --facts --facts-tag {axis_value} --band flag"
        else:
            state_axis_command = f"./repo-python kernel.py --facts --facts-facet {axis_value} --band flag"
    next_command = (
        "./repo-python kernel.py --session-diagnostics --lens all --last 30 --store both --json"
        if is_agent_trouble_diagnosis
        else "./repo-python kernel.py --facts --band cluster_flag"
        if is_state_axis_overview and not is_projection_closure_audit
        else state_axis_command
        if state_axis_command is not None and not is_projection_closure_audit
        else f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if is_disclosure_query and task_text and not is_projection_closure_audit
        else f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if is_autonomous_seed_framework and task_text
        else f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if is_cognitive_operator_discovery and task_text
        else f"./repo-python kernel.py --organisation-control-plane --context-budget {context_budget}"
        if is_organisation_control_plane
        else "./repo-python kernel.py --pulse"
        if is_active_execution_constellation
        else './repo-python kernel.py --docs-route "screenshot ledger"'
        if is_frontend_visual_memory
        else "./repo-python kernel.py --docs-route \"frontend page meta\""
        if is_frontend_page_meta_contract
        else f"./repo-python kernel.py --agent-principle-authoring {task_arg} --context-budget {context_budget}"
        if is_agent_principle_authoring and task_text
        else "./repo-python kernel.py --agent-principle-authoring --context-budget 12000"
        if is_agent_principle_authoring
        else f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if is_doctrine_population and task_text
        else mechanism_workitem_affinity_command
        if is_mechanism_workitem_affinity
        else f"./repo-python kernel.py --navigation-metabolism {task_arg} --metabolism-profile quick --context-budget {context_budget}"
        if is_navigation
        else "./repo-python kernel.py --kind-atlas --band flag"
        if is_kind_atlas_browse
        else microcosm_public_substrate_command
        if is_microcosm_public_substrate
        else f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if is_type_b_to_type_a_handoff and task_text
        else f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if is_dissemination_lane and task_text
        else "./repo-python tools/meta/control/publication_lane.py plan --repo-root ."
        if is_publication_lane_push_recovery
        else config_authority_command
        if is_config_authority_plane
        else "./repo-python kernel.py --option-surface task_ledger --band cluster_flag"
        if is_task_ledger_dependency_unlocks
        else f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if task_text
        else "./repo-python kernel.py --vantage --band card"
    )
    next_action = {
        "command": next_command,
        "why": selected_lane["reason"],
        "surface_role": _entry_next_action_surface_role(next_command),
    }
    # An explicit WorkItem id in the task takes precedence over the default
    # active-phase route. Active phase remains visible as context, but it must
    # not erase the explicit WorkItem the operator/agent already named.
    if selected_workitem_payload is not None:
        wid = selected_workitem_payload.get("id") or ""
        drilldown = selected_workitem_payload.get("drilldown_command") or next_command
        selected_lane = {
            "lane_id": "task_ledger_workitem",
            "reason": (
                f"Task names Task Ledger WorkItem {wid} "
                f"(rank={selected_workitem_payload.get('rank')!r}, "
                f"state={selected_workitem_payload.get('state')!r}); "
                "open the WorkItem card before treating active_phase as the next action."
            ),
        }
        next_action = {
            "command": drilldown,
            "why": selected_lane["reason"],
            "surface_role": _entry_next_action_surface_role(drilldown),
        }
    elif (
        effective_imperative_authoring
        and is_dissemination_lane
        and not is_type_b_to_type_a_handoff
        and not _task_mentions_system_atlas(task_text)
    ):
        selected_lane = {
            "lane_id": "dissemination_authoring",
            "reason": (
                "Task is imperative dissemination work; use the dissemination router, skill family, "
                "public/private boundary, and current gate before changing public projection, outreach, "
                "research, or demo surfaces."
            ),
        }
        dissemination_command = (
            f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
            if task_text
            else "./repo-python kernel.py --context-pack \"dissemination\" --context-budget 12000"
        )
        next_action = {
            "command": dissemination_command,
            "why": selected_lane["reason"],
            "surface_role": _entry_next_action_surface_role(dissemination_command),
        }
    elif effective_imperative_authoring and not is_type_b_to_type_a_handoff:
        # No explicit WorkItem id, but the task is imperative authoring
        # ("create ...", "wire ...", "build ..."). Route to the active-phase
        # WorkItem if one is claimed, else to the top ready WorkItem, else
        # fall back to the active-phase control anchor with an authoring
        # context-pack hint. Do NOT classify this as system_comprehension_atlas.
        selected_lane = {
            "lane_id": "system_comprehension_authoring"
            if _task_mentions_system_atlas(task_text)
            else "imperative_authoring",
            "reason": (
                "Task is imperative authoring (create/wire/build/fix/...); "
                "route to the active-phase WorkItem or the top ready WorkItem "
                "instead of read-only system_comprehension_atlas browsing."
            ),
        }
        preferred_workitem_payload = top_schedulable_payload or top_ready_payload
        if (
            isinstance(preferred_workitem_payload, dict)
            and preferred_workitem_payload.get("drilldown_command")
        ):
            preferred_command = str(preferred_workitem_payload["drilldown_command"])
            next_action = {
                "command": preferred_command,
                "why": selected_lane["reason"],
                "surface_role": _entry_next_action_surface_role(preferred_command),
            }
        else:
            fallback_command = (
                f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
                if task_text
                else next_command
            )
            next_action = {
                "command": fallback_command,
                "why": (
                    selected_lane["reason"]
                    + " No claimed/ready WorkItem found; open a context-pack with authoring intent and route through the active-phase control anchor."
                ),
                "surface_role": _entry_next_action_surface_role(fallback_command),
            }
    recognized_situation = (
        "task_ledger_workitem"
        if selected_workitem_payload is not None
        else "agent_trouble_diagnosis_seed"
        if is_agent_trouble_diagnosis
        else "type_b_to_type_a_continuation_handoff"
        if is_type_b_to_type_a_handoff
        else "system_comprehension_authoring"
        if effective_imperative_authoring and _task_mentions_system_atlas(task_text)
        else "dissemination_authoring"
        if effective_imperative_authoring and is_dissemination_lane
        else "imperative_authoring"
        if effective_imperative_authoring
        else "system_state_axis_overview"
        if is_state_axis_overview and not is_projection_closure_audit
        else "system_state_fact_query"
        if state_axis is not None and not is_projection_closure_audit
        else "system_disclosure_query"
        if is_disclosure_query and not is_projection_closure_audit
        else "projection_closure_audit"
        if is_projection_closure_audit
        else "type_a_autonomous_seed_framework"
        if is_autonomous_seed_framework
        else "cognitive_operator_discovery"
        if is_cognitive_operator_discovery
        else "active_execution_constellation"
        if is_active_execution_constellation
        else "russian_doll_option_surface_entry"
        if is_kind_atlas_browse
        else "system_comprehension_atlas"
        if is_system_atlas
        else "microcosm_public_substrate"
        if is_microcosm_public_substrate
        else "type_b_to_type_a_continuation_handoff"
        if is_type_b_to_type_a_handoff
        else "dissemination_agent_entry"
        if is_dissemination_lane
        else "publication_lane_push_recovery"
        if is_publication_lane_push_recovery
        else "config_authority_plane"
        if is_config_authority_plane
        else "frontend_visual_memory"
        if is_frontend_visual_memory
        else "frontend_page_meta_contract"
        if is_frontend_page_meta_contract
        else "agent_principle_authoring"
        if is_agent_principle_authoring
        else "doctrine_population"
        if is_doctrine_population
        else "mechanism_workitem_affinity"
        if is_mechanism_workitem_affinity
        else "navigation_control_boundary"
        if is_navigation
        else "task_ledger_dependency_unlocks"
        if is_task_ledger_dependency_unlocks
        else "frontend_capability_discovery"
        if is_frontend_capability_discovery
        else "general_task_entry"
    )
    from system.lib.compliance.diagnostics_projection import project_compliance_diagnostics
    from system.lib.agent_operating_packet import (
        build_agent_operating_packet_strip,
        build_agent_principle_lens,
        load_agent_operating_packet,
    )
    from system.lib.candidate_runtime_pressure_policy import filter_first_contact_candidate_pressure
    from system.lib.paper_module_freshness_diagnostics import project_paper_module_freshness_diagnostics
    from system.lib.standard_option_surface import (
        candidate_runtime_pressure_rows,
        no_edit_pass_floor_card,
    )
    from system.lib.entrypoint_health import project_entry_surface_diagnostics
    evidence_texts: list[str] = []
    if isinstance(selected_workitem_payload, dict):
        for key in ("id", "title", "statement_snippet"):
            value = selected_workitem_payload.get(key)
            if isinstance(value, str) and value.strip():
                evidence_texts.append(value)
    raw_candidate_pressure_rows = candidate_runtime_pressure_rows(
        repo_root,
        task_text or "",
        evidence_texts=evidence_texts or None,
    )
    candidate_pressure_policy = filter_first_contact_candidate_pressure(raw_candidate_pressure_rows)
    structural_entry_surface_triggers: list[dict[str, Any]] = []
    structural_trigger = ENTRY_SURFACE_STRUCTURAL_LANE_TRIGGERS.get(recognized_situation)
    if structural_trigger is not None:
        structural_entry_surface_triggers.append(
            {
                "trigger_id": structural_trigger["trigger_id"],
                "recognized_situation": recognized_situation,
                "selected_lane_id": str(selected_lane.get("lane_id") or ""),
                "source": "kernel.entry_packet.recognized_situation",
                "reason": structural_trigger["reason"],
            }
        )
    entry_surface_diagnostics = project_entry_surface_diagnostics(
        repo_root,
        task_text or "",
        structural_triggers=structural_entry_surface_triggers,
        content_sync_mode="source_coupling_only",
    )
    compliance_diagnostics = project_compliance_diagnostics(repo_root, task_text or "")
    paper_module_freshness_diagnostics = project_paper_module_freshness_diagnostics(repo_root, task_text or "")
    candidate_runtime_pressure_block = {
        **candidate_pressure_policy,
        "contract_ref": "codex/standards/std_agent_entry_surface.json::candidate_runtime_pressure_contract",
        "source_standard": "codex/standards/principles/std_system_axiom_candidate.json::promotion_contract.candidate_to_runtime_packet",
        "non_law_warning": "Candidate axioms surfaced as provisional pressure; not active doctrine. Do not treat as binding.",
        "match_strategy": "layered_priority_explicit_id_then_explicit_slug_then_workitem_evidence_overlap_then_deterministic_query_overlap_min_2",
        "match_strategy_ref": "codex/standards/std_agent_entry_surface.json::candidate_runtime_pressure_contract::match_strategy",
    }
    if is_speed_refinement and isinstance(candidate_runtime_pressure_block.get("rows"), list):
        candidate_runtime_pressure_block = {
            "count": len(candidate_runtime_pressure_block.get("rows") or []),
            "suppressed_count": candidate_runtime_pressure_block.get("suppressed_count", 0),
            "rows_omitted_for_speed_refinement_entry_budget": True,
            "drilldown": "./repo-python kernel.py --agent-operating-packet --band card",
        }
    no_edit_pass_floor = no_edit_pass_floor_card(repo_root, task_text or "")
    full_agent_operating_packet = load_agent_operating_packet(repo_root)
    agent_operating_packet = build_agent_operating_packet_strip(full_agent_operating_packet)
    from system.lib.python_target_resolution import resolve_python_targets

    python_target_resolution = _suppress_python_unresolved_for_selected_workitem(
        resolve_python_targets(repo_root, task_text or ""),
        selected_workitem_payload,
    )
    transaction_task_text = task_text
    if include_transaction_control_plane is True and not _mentions_transaction_control_plane(task_text):
        transaction_task_text = f"transaction control plane {task_text}"
    if include_transaction_control_plane is True:
        transaction_control_plane = _entry_transaction_control_plane_summary(
            repo_root,
            task_text=transaction_task_text,
            selected_workitem=selected_workitem_payload,
            top_schedulable_workitem=top_schedulable_payload,
            top_ready_workitem=top_ready_payload,
        )
    else:
        transaction_control_plane = _entry_transaction_control_plane_hint(
            task_text=transaction_task_text,
            selected_workitem=selected_workitem_payload,
            top_schedulable_workitem=top_schedulable_payload,
            top_ready_workitem=top_ready_payload,
        )
    try:
        from system.lib.git_state_snapshot import (
            build_closeout_git_state_conditions,
            compact_closeout_git_state_conditions,
        )

        closeout_git_state = compact_closeout_git_state_conditions(
            build_closeout_git_state_conditions(repo_root, path_limit=5, recent_limit=1)
        )
    except Exception as exc:
        closeout_git_state = {
            "schema": "closeout_git_state_summary_v0",
            "status": "unknown",
            "reason": "closeout_git_state_projection_failed",
            "error": str(exc)[:240],
            "drilldowns": {
                "closeout_conditions": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions"
            },
        }
    navigation_index_spine = None
    if recognized_situation in {
        "system_comprehension_atlas",
        "system_comprehension_authoring",
        "navigation_control_boundary",
        "publication_lane_push_recovery",
        "projection_closure_audit",
        "cognitive_operator_discovery",
        "russian_doll_option_surface_entry",
        "frontend_visual_memory",
        "system_state_axis_overview",
        "system_state_fact_query",
    }:
        from system.lib.navigation_index_spine import build_navigation_index_spine

        navigation_index_spine = build_navigation_index_spine(
            repo_root,
            max_gap_kinds=4,
            task_text=task_text,
            fast_entry=True,
        )
    route_lease = _entry_route_lease(
        task_text=task_text,
        selected_lane=selected_lane,
        next_action=next_action,
        active_phase=active_phase,
        python_target_resolution=python_target_resolution,
        navigation_index_spine=navigation_index_spine,
    )
    entry_navigation_index_spine = _compact_entry_navigation_index_spine(
        navigation_index_spine,
        task_text=task_text,
        context_budget=context_budget,
    )
    agent_principle_lens = build_agent_principle_lens(
        full_agent_operating_packet,
        task_text=task_text,
        recognized_situation=recognized_situation,
        selected_lane_id=str(selected_lane.get("lane_id") or ""),
        max_rows=7,
    )
    operator_prompt_framing = None
    if is_type_b_to_type_a_handoff:
        if is_sender_side_type_b_ask:
            operator_prompt_framing = {
                "framing_id": "type_b_sender_side_ask",
                "concept_ref": "codex/doctrine/concepts/con_016_intelligence_delegation_cascade.json::actor_axes",
                "source_role": "type_a_sender_preparing_operator_carried_type_b_ask",
                "receiving_agent_role": "type_a_repo_agent",
                "execution_stance": "prepare_paste_ready_external_hud_bridge_ask_then_verify_return",
                "directive_boundary": (
                    "The operator asked the current repo agent to ask Type B. The current repo "
                    "agent is Type A: it should inspect live substrate, materialize the bounded "
                    "context, prepare a paste-ready ask for the operator/HUD/bridge lane, and "
                    "treat any returned Type B response as advisory synthesis until verified."
                ),
                "agent_obligations": [
                    "resolve Type A/B through con_016::actor_axes before choosing mechanics",
                    "do not spawn a native Codex/Claude subagent unless the operator explicitly asks for native subagents",
                    "materialize the private context, authority boundary, output shape, and ASK_TYPE_A return requirements for Type B",
                    "verify any returned Type B claims against live repo state before mutating",
                ],
            }
        else:
            operator_prompt_framing = {
                "framing_id": "type_b_to_type_a_continuation_handoff",
                "concept_ref": "codex/doctrine/concepts/con_016_intelligence_delegation_cascade.json::actor_axes",
                "source_role": "operator_pasted_type_b_response",
                "receiving_agent_role": "type_a_repo_agent",
                "execution_stance": "current_agent_is_type_a_execute_after_verification",
                "directive_boundary": (
                    "The operator pasted a Type B response that was written to the operator and handed it "
                    "to the current repo agent. The current repo agent is Type A; execute the embedded "
                    "Type A continuation prompt after verifying live repo state. The Type B response is "
                    "advisory synthesis, not live repo-state authority."
                ),
                "agent_obligations": [
                    "do not hallucinate that Type A is a different future actor",
                    "extract the concrete Type A continuation prompt / final-call decision",
                    "verify exact current repo state, claims, intake/drainer commands, and staged-index status before acting",
                    "do not classify the paste from broad Type A/Type B labels or public/dissemination/prior-art terms alone",
                ],
            }
    packet = {
        "kind": "kernel.entry_packet",
        "schema_version": "entry_packet_v0",
        "surface_role": CONTROL_ENTRY,
        "first_contact_allowed": True,
        "generated_at": _utc_now(),
        "task": task_text,
        "recognized_situation": recognized_situation,
        "agent_operating_packet": agent_operating_packet,
        "agent_principle_lens": agent_principle_lens,
        "candidate_runtime_pressure": candidate_runtime_pressure_block,
        "no_edit_pass_floor": no_edit_pass_floor,
        "speed_refinement_routes": _speed_refinement_routes_card() if is_speed_refinement else None,
        "transaction_control_plane": transaction_control_plane,
        "closeout_git_state": closeout_git_state,
        "mutation_governance": {
            "latest_intent_gate": latest_intent_gate,
        },
        "entry_surface_diagnostics": entry_surface_diagnostics,
        "compliance_diagnostics": compliance_diagnostics,
        "paper_module_freshness_diagnostics": paper_module_freshness_diagnostics,
        "active_phase": active_phase,
        "selected_lane": selected_lane,
        "selected_workitem": selected_workitem_payload,
        "operator_prompt_framing": operator_prompt_framing,
        "python_target_resolution": python_target_resolution
        if python_target_resolution.get("status") in {"resolved", "unresolved"}
        else None,
        "navigation_index_spine": entry_navigation_index_spine,
        "top_schedulable_workitem": top_schedulable_payload,
        "top_ready_workitem": top_ready_payload,
        "next_action": next_action,
        "route_lease": route_lease,
        "write_scope": [],
        "banned_routes": [
            {
                "route_id": "skill_find_first_contact",
                "surface": "--skill-find",
                "surface_role": DEBUG_TRACE,
                "replacement": ENTRY_REPLACEMENT,
            },
            {
                "route_id": "atlas_as_control_entry",
                "surface": "--kind-atlas / --option-surface",
                "surface_role": ATLAS_PROJECTION,
                "replacement": ENTRY_REPLACEMENT,
            },
            {
                "route_id": "ranked_debug_as_instruction",
                "surface": "ranked debug internals",
                "surface_role": DEBUG_TRACE,
                "replacement": ENTRY_REPLACEMENT,
            },
        ],
        "allowed_drilldowns": [
            {
                "command": "./repo-python kernel.py --row <kind_id>:<row_id> --band card",
                "surface_role": DRILLDOWN,
                "allowed_after": "stable row id selected",
            },
            {
                "command": "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag",
                "surface_role": ATLAS_PROJECTION,
                "allowed_after": "entry packet selected the kind or operator explicitly browses",
            },
            {
                "command": "./repo-python kernel.py --agent-principles --band card",
                "surface_role": DRILLDOWN,
                "allowed_after": "entry packet emits agent_principle_lens or task concerns agent behavior, Type A/B, proof binding, projection ownership, or transaction closeout",
            },
            {
                "command": "./repo-python kernel.py --agent-principle-authoring \"<lesson>\" --context-budget 12000",
                "surface_role": CONTROL_ENTRY,
                "allowed_after": "task asks to add, refine, mint, promote, or route a Type A/agent principle",
            },
            {
                "command": "./repo-python kernel.py --agent-operating-packet --band card",
                "surface_role": DRILLDOWN,
                "allowed_after": "agent needs global/frequent/situational principle or axiom-candidate expansion",
            },
        ],
        "ceremony_budget": {
            "tier": "tier_0_observe_only",
            "effect_kinds": ["read_only_navigation"],
            "required_steps": ["run_next_action"],
            "required_proof": ["command_output_or_snapshot_section"],
        },
        "proof_required": ["next action emits a control packet or a selected stable-id drilldown"],
        "fallback_if_uncertain": f"./repo-python kernel.py --context-pack {task_arg} --context-budget {context_budget}"
        if task_text
        else "./repo-python kernel.py --vantage --band card",
        "debug_trace_command": f"./repo-python kernel.py --skill-find {task_arg} --debug" if task_text else "./repo-python kernel.py --skill-find <query> --debug",
        "atlas_drilldown_command": "./repo-python kernel.py --kind-atlas --band flag",
        "surface_contract": surface_contract(
            surface_id="entry",
            command="./repo-python kernel.py --entry",
            surface_role=CONTROL_ENTRY,
            authority_plane="control",
            first_contact_allowed=True,
            replacement=ENTRY_REPLACEMENT,
            allowed_callers=["agent_first_contact", "normal_task_entry", "navigation_complaint"],
            banned_callers=[],
            default_output_policy={
                "emits": "one_selected_route_packet",
                "debug_fields": "hidden",
                "atlas_rows": "labeled_drilldown_only",
            },
        ),
    }
    if is_active_execution_constellation:
        packet["active_execution_constellation"] = active_execution_constellation
    if transaction_control_plane is None:
        packet.pop("transaction_control_plane", None)
    if packet.get("python_target_resolution") is None:
        packet.pop("python_target_resolution", None)
    if packet.get("no_edit_pass_floor") is None:
        packet.pop("no_edit_pass_floor", None)
    if packet.get("speed_refinement_routes") is None:
        packet.pop("speed_refinement_routes", None)
    if entry_navigation_index_spine is None:
        packet.pop("navigation_index_spine", None)
    frontend_enrichment = _frontend_capability_enrichment(
        repo_root,
        frontend_capability_slices,
    )
    if frontend_enrichment is not None:
        packet["capability_enrichments"] = [frontend_enrichment]
    return _apply_entry_payload_admission(
        packet,
        context_budget=context_budget,
        task_text=task_text,
    )


def _mentions_transaction_control_plane(task_text: str) -> bool:
    lowered = str(task_text or "").lower()
    return any(term in lowered for term in TRANSACTION_CONTROL_PLANE_TERMS)


def _workitem_control_target(*items: dict[str, Any] | None) -> str | None:
    for item in items:
        if not isinstance(item, dict):
            continue
        token = str(item.get("id") or "").strip()
        if token.startswith(("cap_", "td_")):
            return token
    return None


def _entry_transaction_control_plane_summary(
    repo_root: Path,
    *,
    task_text: str,
    selected_workitem: dict[str, Any] | None,
    top_schedulable_workitem: dict[str, Any] | None,
    top_ready_workitem: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not _mentions_transaction_control_plane(task_text):
        return None
    target_id = (
        _workitem_control_target(selected_workitem, top_schedulable_workitem, top_ready_workitem)
        or TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT
    )
    try:
        from system.lib.mission_transaction_landing_preflight import (
            build_mission_transaction_landing_preflight,
            mission_transaction_control_summary,
        )

        packet = build_mission_transaction_landing_preflight(
            repo_root,
            target_ids=[target_id],
        )
        return mission_transaction_control_summary(packet, consumer_surface="kernel.entry")
    except Exception as exc:  # pragma: no cover - entry must degrade on partial fixtures.
        return {
            "schema": "transaction_control_plane_summary_v0",
            "consumer_surface": "kernel.entry",
            "status": "watch",
            "next_action": "open_mission_transaction_preflight_drilldown",
            "target_id": target_id,
            "unavailable_reason": type(exc).__name__,
            "drilldown_commands": [
                f"./repo-python tools/meta/control/mission_transaction_preflight.py --subject-id {target_id} --control-summary",
            ],
        }


def _entry_transaction_control_plane_hint(
    *,
    task_text: str,
    selected_workitem: dict[str, Any] | None,
    top_schedulable_workitem: dict[str, Any] | None,
    top_ready_workitem: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not _mentions_transaction_control_plane(task_text):
        return None
    target_id = (
        _workitem_control_target(selected_workitem, top_schedulable_workitem, top_ready_workitem)
        or TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT
    )
    drilldown = (
        "./repo-python tools/meta/control/mission_transaction_preflight.py "
        f"--subject-id {target_id} --control-summary"
    )
    status = "omitted_from_summary"
    return {
        "schema": "transaction_control_plane_summary_v0",
        "consumer_surface": "kernel.entry",
        "status": status,
        "reason": "Transaction-control preflight is expensive and belongs behind an explicit drilldown or --full entry packet.",
        "next_action": drilldown,
        "target_id": target_id,
        "shared_index_quarantine": {
            "schema": "shared_index_quarantine_v0",
            "status": status,
            "next_action": drilldown,
        },
        "workspace_bloat_pressure": {
            "schema": "workspace_bloat_pressure_v0",
            "status": status,
            "next_action": drilldown,
        },
        "github_push_bloat_gate": {
            "schema": "github_push_bloat_gate_v1",
            "status": status,
            "next_action": drilldown,
        },
        "drilldown_commands": [
            drilldown,
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {target_id} --staged-index-quarantine"
            ),
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {target_id} --workspace-bloat-pressure"
            ),
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {target_id} --github-push-bloat-gate"
            ),
        ],
    }


def cmd_comprehension_snapshot() -> int:
    """
    [ACTION]
    - Teleology: Kernel CLI handler for ``--comprehension-snapshot``.
    """
    payload = build_comprehension_snapshot(kernel_state.REPO_ROOT)
    return kernel_output.emit_json(payload)


def cmd_vantage(*, band: str = "flag") -> int:
    """
    [ACTION]
    - Teleology: Kernel CLI handler for ``--vantage``.
    """
    payload = build_vantage(kernel_state.REPO_ROOT, band=band)
    return kernel_output.emit_json(payload)


def cmd_what_am_i(task: str | None = None, *, band: str = "card", context_budget: int = 12000) -> int:
    """
    [ACTION]
    - Teleology: Kernel CLI handler for ``--what-am-i``.
    """
    payload = build_what_am_i(kernel_state.REPO_ROOT, task=task, band=band, context_budget=context_budget)
    return kernel_output.emit_json(payload)


def cmd_what_am_i_record(task: str | None = None, *, band: str = "card", context_budget: int = 12000) -> int:
    """
    [ACTION]
    - Teleology: Explicitly record a compact Constitution Workspace packet
      receipt for later retread comparison. This is the mutating counterpart
      to read-only ``--what-am-i``.
    """
    payload = build_what_am_i_record(
        kernel_state.REPO_ROOT,
        task=task,
        band=band,
        context_budget=context_budget,
    )
    return kernel_output.emit_json(payload)


def cmd_constitution_workspace_replay(
    selector: str | None = "latest",
    *,
    band: str | None = None,
    context_budget: int = 12000,
) -> int:
    """
    [ACTION]
    - Teleology: Compare the current Constitution Workspace packet identity
      against a prior receipt without writing state.
    """
    payload = build_constitution_workspace_replay(
        kernel_state.REPO_ROOT,
        selector,
        band=band,
        context_budget=context_budget,
    )
    return kernel_output.emit_json(payload)


def cmd_entry(
    task: str | None = None,
    *,
    context_budget: int = 12000,
    include_transaction_control_plane: bool | None = None,
) -> int:
    payload = build_entry_packet(
        kernel_state.REPO_ROOT,
        task=task,
        context_budget=context_budget,
        include_transaction_control_plane=include_transaction_control_plane,
    )
    return kernel_output.emit_json(payload)


__all__ = [
    "cmd_comprehension_snapshot",
    "cmd_vantage",
    "cmd_what_am_i",
    "cmd_what_am_i_record",
    "cmd_constitution_workspace_replay",
    "cmd_entry",
    "build_comprehension_snapshot",
    "build_vantage",
    "build_what_am_i",
    "build_what_am_i_record",
    "build_constitution_workspace_replay",
    "write_constitution_workspace_receipt",
    "build_entry_packet",
]
