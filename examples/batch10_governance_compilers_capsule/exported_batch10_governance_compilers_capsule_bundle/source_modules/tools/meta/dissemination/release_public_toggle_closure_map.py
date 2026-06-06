#!/usr/bin/env python3
"""Build the fail-closed public-toggle closure map."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = Path("docs/dissemination/release_public_toggle_closure_map_v0.json")
PUBLIC_TOGGLE_GATE = Path("docs/dissemination/public_toggle_readiness_gate_v0.json")
RELEASE_DECISION_REGISTER = Path("docs/dissemination/release_decision_register_v0.json")
OPERATOR_DECISION_LOCK = Path("docs/dissemination/release_operator_decision_lock_v0.json")
OPERATOR_DECISION_PACKET = Path("docs/dissemination/release_operator_decision_packet_v0.json")
OPERATOR_DECISION_INTAKE = Path("docs/dissemination/release_operator_decision_intake_v0.json")
PUBLIC_GOVERNANCE_SCAFFOLD = Path(
    "docs/dissemination/release_public_governance_scaffold_v0.json"
)
RIGHTS_POSTURE_SCAFFOLD = Path(
    "docs/dissemination/release_rights_posture_scaffold_v0.json"
)
DEPENDENCY_REVIEW_SCAFFOLD = Path(
    "docs/dissemination/release_dependency_review_scaffold_v0.json"
)
DEMO_MEDIA_REVIEW_SCAFFOLD = Path(
    "docs/dissemination/release_demo_media_review_scaffold_v0.json"
)
CLAIM_LANGUAGE_GATE = Path("docs/dissemination/release_claim_language_gate_v0.json")
VIRAL_SECURITY_GATE = Path("docs/dissemination/release_viral_security_gate_v0.json")
SUBSTRATE_RELEASE_ESCROW = Path(
    "docs/dissemination/public_substrate_release_candidate_escrow_v0.json"
)
SUBSTRATE_RELEASE_VALIDATION_RECEIPT = Path(
    "docs/dissemination/public_substrate_release_candidate_validation_receipt_v0.json"
)
SUBSTRATE_RELEASE_SWITCH_BLOCKERS = Path(
    "docs/dissemination/public_substrate_release_switch_blockers_v0.md"
)
SECURITY_CONTACT_CLOSURE = Path(
    "docs/dissemination/release_security_contact_closure_v0.json"
)
DEMO_CUT_LEDGER = Path("docs/dissemination/demo_cut_ledger_v0.json")
DEMO_MEDIA_RELEASE_RECEIPT = Path(
    "docs/dissemination/demo_media_release_receipt_v0.json"
)
SOURCE_FINGERPRINT_PATHS = [
    PUBLIC_TOGGLE_GATE,
    RELEASE_DECISION_REGISTER,
    OPERATOR_DECISION_LOCK,
    OPERATOR_DECISION_PACKET,
    OPERATOR_DECISION_INTAKE,
    PUBLIC_GOVERNANCE_SCAFFOLD,
    RIGHTS_POSTURE_SCAFFOLD,
    DEPENDENCY_REVIEW_SCAFFOLD,
    DEMO_MEDIA_REVIEW_SCAFFOLD,
    CLAIM_LANGUAGE_GATE,
    VIRAL_SECURITY_GATE,
    SUBSTRATE_RELEASE_ESCROW,
    SUBSTRATE_RELEASE_VALIDATION_RECEIPT,
    SUBSTRATE_RELEASE_SWITCH_BLOCKERS,
    SECURITY_CONTACT_CLOSURE,
    DEMO_CUT_LEDGER,
    DEMO_MEDIA_RELEASE_RECEIPT,
    Path("docs/dissemination/third_party_notices_policy_v0.json"),
    Path("docs/dissemination/release_dependency_inventory_v0.json"),
    Path("docs/dissemination/release_ip_license_gate_v0.md"),
    Path("docs/dissemination/public_trust_packet_v0.md"),
    Path("docs/dissemination/release_coverage_manifest_v0.md"),
    Path("publication_manifest.yaml"),
]

GROUP_ORDER = [
    "license_and_rights",
    "dependency_and_notices",
    "public_governance_paths",
    "demo_media_release",
]

SCAFFOLD_BY_GROUP: dict[str, dict[str, Any]] = {
    "license_and_rights": {
        "path": RIGHTS_POSTURE_SCAFFOLD,
        "open_key": "open_rights_decision_count",
        "decision_key": "rights_decision_count",
    },
    "dependency_and_notices": {
        "path": DEPENDENCY_REVIEW_SCAFFOLD,
        "open_key": "open_dependency_decision_count",
        "decision_key": "dependency_decision_count",
    },
    "public_governance_paths": {
        "path": PUBLIC_GOVERNANCE_SCAFFOLD,
        "open_key": "open_governance_decision_count",
        "decision_key": "governance_decision_count",
    },
    "demo_media_release": {
        "path": DEMO_MEDIA_REVIEW_SCAFFOLD,
        "open_key": "open_demo_media_decision_count",
        "decision_key": "demo_media_decision_count",
    },
}


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _repo_path(path: Path, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _read_optional_json(repo_root: Path, rel_path: Path) -> dict[str, Any]:
    path = repo_root / rel_path
    if not path.exists():
        return {}
    return _read_json(path)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _source_fingerprints(repo_root: Path, paths: list[Path]) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for rel_path in paths:
        path = _repo_path(rel_path, repo_root)
        if path.exists():
            fingerprints[_rel(path, repo_root)] = _sha256(path)
    return dict(sorted(fingerprints.items()))


def _safe_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _group_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("operator_action_groups", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("id", "unknown")): row
        for row in rows
        if isinstance(row, dict)
    }


def _blocking_conditions_by_id(gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = gate.get("blocking_conditions", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("id", "unknown")): row
        for row in rows
        if isinstance(row, dict)
    }


def _scaffold_status(repo_root: Path, group_id: str) -> dict[str, Any]:
    definition = SCAFFOLD_BY_GROUP[group_id]
    path = repo_root / definition["path"]
    if not path.exists():
        return {
            "path": definition["path"].as_posix(),
            "status": "absent",
            "public_toggle": "red",
            "open_decision_count": None,
            "blocked_target_surface_count": None,
            "writable_target_surface_count": None,
        }
    payload = _read_json(path)
    summary = _safe_summary(payload)
    return {
        "path": _rel(path, repo_root),
        "schema_version": payload.get("schema_version"),
        "status": payload.get("status"),
        "public_toggle": payload.get("public_toggle"),
        "decision_count": summary.get(definition["decision_key"], 0),
        "open_decision_count": summary.get(definition["open_key"], 0),
        "queue_item_count": summary.get("queue_item_count", 0),
        "blocked_target_surface_count": summary.get("blocked_target_surface_count", 0),
        "writable_target_surface_count": summary.get("writable_target_surface_count", 0),
        "media_release_receipt_present": summary.get("media_release_receipt_present"),
    }


def _compact_blocker(row: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in (
        "id",
        "kind",
        "current_state",
        "required_before_public_toggle",
        "queue_count",
        "path",
        "release_effect",
        "required_action",
    ):
        if key in row:
            compact[key] = row[key]
    return compact


def _find_decision(register: dict[str, Any], decision_id: str) -> dict[str, Any]:
    rows = register.get("required_decisions", [])
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, dict) and row.get("id") == decision_id:
            return row
    return {}


def _operator_target(register: dict[str, Any], escrow: dict[str, Any]) -> dict[str, Any]:
    decision = _find_decision(register, "publication_target_authority")
    lock = decision.get("operator_decision_lock", {})
    if not isinstance(lock, dict):
        lock = {}
    identity = escrow.get("candidate_identity", {})
    if not isinstance(identity, dict):
        identity = {}
    artifact_id = str(identity.get("artifact_id") or "ai-workflow-proof")
    return {
        "target_repo": lock.get("target_repo") or artifact_id,
        "target_site": lock.get("target_site") or "site/substrate_map.html in the proof repo",
        "target_video_surface": lock.get("target_video_surface") or "none for v0 dry-run",
        "publication_target_decision_state": decision.get("current_state", "unknown"),
    }


def _substrate_candidate_ref(
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    escrow = _read_optional_json(repo_root, SUBSTRATE_RELEASE_ESCROW)
    validation = _read_optional_json(repo_root, SUBSTRATE_RELEASE_VALIDATION_RECEIPT)
    if not escrow:
        return (
            {
                "status": "absent",
                "candidate_identity_status": "no_escrow_packet",
                "escrow_packet": SUBSTRATE_RELEASE_ESCROW.as_posix(),
                "validation_receipt": SUBSTRATE_RELEASE_VALIDATION_RECEIPT.as_posix(),
            },
            escrow,
            validation,
        )

    identity = escrow.get("candidate_identity", {})
    artifact = escrow.get("generated_artifact", {})
    archive = artifact.get("archive", {}) if isinstance(artifact, dict) else {}
    hashes = artifact.get("hashes", {}) if isinstance(artifact, dict) else {}
    validation_hashes = validation.get("artifact_hashes", {}) if validation else {}
    mismatches: list[str] = []
    if validation:
        if identity.get("source_commit") != validation.get("evaluated_commit"):
            mismatches.append("source_commit_vs_validation_evaluated_commit")
        if identity.get("artifact_git_head") != validation.get("artifact_git_head"):
            mismatches.append("artifact_git_head_vs_validation")
        if archive.get("sha256") != validation_hashes.get("archive_tar_gz"):
            mismatches.append("archive_sha256_vs_validation")

    status = "verified_current" if not mismatches and validation else "stale_or_mismatched"
    if not validation:
        status = "validation_receipt_absent"

    return (
        {
            "escrow_packet": SUBSTRATE_RELEASE_ESCROW.as_posix(),
            "validation_receipt": SUBSTRATE_RELEASE_VALIDATION_RECEIPT.as_posix(),
            "switch_blockers_projection": SUBSTRATE_RELEASE_SWITCH_BLOCKERS.as_posix(),
            "candidate_identity_status": status,
            "review_projection_identity": "non_authority_prompt_or_review_previews_ignored",
            "mismatches": mismatches,
            "artifact_id": identity.get("artifact_id"),
            "artifact_class": identity.get("artifact_class"),
            "candidate_commit": identity.get("candidate_commit"),
            "source_commit": identity.get("source_commit"),
            "artifact_git_head": identity.get("artifact_git_head"),
            "archive_sha256": archive.get("sha256"),
            "tracked_manifest_sha256": identity.get("tracked_manifest_sha256"),
            "readme_sha256": hashes.get("README.md"),
            "site_map_sha256": hashes.get("site/substrate_map.html"),
            "manifest_sha256": hashes.get("public_executable_projection_manifest_v0.json"),
            "candidate_integrity": escrow.get("candidate_integrity"),
            "public_release_authority": escrow.get("public_release_authority"),
        },
        escrow,
        validation,
    )


def _clearing_surface(blocker_id: str, row: dict[str, Any]) -> str:
    if blocker_id == "security_contact_path":
        return SECURITY_CONTACT_CLOSURE.as_posix()
    if blocker_id == "demo_media_release_review":
        return DEMO_MEDIA_RELEASE_RECEIPT.as_posix()
    if blocker_id == "release_viral_security_gate_not_ready":
        return VIRAL_SECURITY_GATE.as_posix()
    if blocker_id == "release_decision_register_not_ready":
        return RELEASE_DECISION_REGISTER.as_posix()
    if blocker_id == "release_claim_language_gate_not_clear":
        return CLAIM_LANGUAGE_GATE.as_posix()
    if blocker_id == "portability_gate_not_green":
        return PUBLIC_TOGGLE_GATE.as_posix()
    return str(row.get("path") or PUBLIC_TOGGLE_GATE.as_posix())


def _blocker_class(blocker_id: str, row: dict[str, Any]) -> str:
    if blocker_id in {"public_toggle_no_go"}:
        return "switch"
    if blocker_id in {"operator_public_approval_absent"}:
        return "authority"
    if blocker_id == "security_contact_path":
        return "security_contact"
    if blocker_id == "demo_media_release_review":
        return "media_redaction"
    if blocker_id == "release_viral_security_gate_not_ready":
        return "viral_security"
    if blocker_id == "release_decision_register_not_ready":
        return "release_decision_register"
    return str(row.get("kind") or "operational")


def _blocker_row(
    *,
    blocker_id: str,
    row: dict[str, Any],
    queue_class: str,
    can_clear_without_public_flip: bool,
) -> dict[str, Any]:
    current_status = (
        row.get("current_state")
        or row.get("status")
        or row.get("overall_status")
        or "blocking"
    )
    if blocker_id == "portability_gate_not_green" and current_status == "green":
        current_status = "not_green_freshness_or_manifest_binding"
    details = {
        key: row[key]
        for key in (
            "overall_status",
            "publication_status",
            "hard_blocker_count",
            "failed_check_count",
            "blocking_control_count",
            "dependency_review_queue_count",
        )
        if key in row
    }
    return {
        "blocker_id": blocker_id,
        "queue_class": queue_class,
        "class": _blocker_class(blocker_id, row),
        "current_status": current_status,
        "clearing_surface": _clearing_surface(blocker_id, row),
        "release_effect": row.get("release_effect"),
        "evidence_needed": row.get("required_action")
        or "Regenerate the owning gate with evidence that this blocker is clear.",
        "can_clear_without_public_flip": can_clear_without_public_flip,
        "details": details,
    }


def _blocker_closure(
    gate: dict[str, Any],
    escrow: dict[str, Any],
) -> dict[str, Any]:
    blockers = _blocking_conditions_by_id(gate)
    operational = [
        _blocker_row(
            blocker_id=blocker_id,
            row=row,
            queue_class="operational",
            can_clear_without_public_flip=True,
        )
        for blocker_id, row in sorted(blockers.items())
        if blocker_id not in {"operator_public_approval_absent", "public_toggle_no_go"}
    ]
    authority = [
        _blocker_row(
            blocker_id="operator_public_approval_absent",
            row={
                "current_state": escrow.get("public_release_authority", "no_go"),
                "release_effect": "blocks_public_release_until_operator_approves_exact_candidate_identity",
                "required_action": (
                    "Operator must approve this exact escrow identity after "
                    "non-authority blockers are clear or explicitly accepted."
                ),
            },
            queue_class="authority",
            can_clear_without_public_flip=False,
        )
    ]
    switch = [
        _blocker_row(
            blocker_id="public_toggle_no_go",
            row={
                "current_state": gate.get("status", "no_go"),
                "release_effect": "blocks_repository_visibility_demo_outreach_and_source_language_switches",
                "required_action": (
                    "Rerun the public-toggle readiness gate green after exact "
                    "candidate approval; do not infer release from candidate integrity."
                ),
            },
            queue_class="switch",
            can_clear_without_public_flip=False,
        )
    ]
    all_rows = operational + authority + switch
    return {
        "status": "blocking" if all_rows else "clear",
        "operational_blocker_count": len(operational),
        "authority_blocker_count": len(authority),
        "switch_blocker_count": len(switch),
        "operator_review_ready": len(operational) == 0,
        "operational": operational,
        "authority": authority,
        "switch": switch,
        "all": all_rows,
    }


def _release_switches(
    gate: dict[str, Any],
    register: dict[str, Any],
    escrow: dict[str, Any],
) -> dict[str, Any]:
    target = _operator_target(register, escrow)
    status = str(gate.get("status", "no_go"))
    approved = status == "ready" and gate.get("public_toggle") == "green"
    return {
        "repo_visibility": "approved" if approved else "blocked",
        "public_demo_or_video": "approved" if approved else "static_map_only_video_blocked",
        "outreach_send": "approved" if approved else "blocked",
        "source_or_open_language": "approved" if approved else "boundary_only",
        "target_repo": target["target_repo"],
        "target_site": target["target_site"],
        "target_video_surface": target["target_video_surface"],
        "publication_target_decision_state": target["publication_target_decision_state"],
    }


def _decision_state(
    gate: dict[str, Any],
    closure_status: str,
    escrow: dict[str, Any],
    blocker_closure: dict[str, Any],
) -> dict[str, Any]:
    candidate_integrity = escrow.get("candidate_integrity", "unknown")
    public_release_authority = escrow.get("public_release_authority", "no_go")
    publication_operation = (
        "ready_to_execute"
        if closure_status == "ready" and public_release_authority == "approved"
        else "dry_run_only"
        if candidate_integrity == "pass"
        else "blocked"
    )
    return {
        "candidate_integrity": candidate_integrity,
        "public_release_authority": public_release_authority,
        "publication_operation": publication_operation,
        "public_toggle_gate_status": gate.get("status"),
        "public_toggle_gate": gate.get("public_toggle"),
        "operator_review_ready": blocker_closure.get("operator_review_ready", False),
        "approval_target_rule": "exact_escrow_identity_only_never_latest_head",
    }


def _dry_run_switch_plan(
    register: dict[str, Any],
    escrow: dict[str, Any],
    candidate_ref: dict[str, Any],
) -> dict[str, Any]:
    target = _operator_target(register, escrow)
    publishable = escrow.get("publishable_surfaces_if_unblocked", [])
    if not isinstance(publishable, list):
        publishable = []
    withheld = escrow.get("withheld_surfaces", [])
    if not isinstance(withheld, list):
        withheld = []
    return {
        "status": "dry_run_plan_recorded_external_mutation_blocked",
        "mutated_external_state": False,
        "would_publish_candidate": {
            "artifact_id": candidate_ref.get("artifact_id"),
            "source_commit": candidate_ref.get("source_commit"),
            "artifact_git_head": candidate_ref.get("artifact_git_head"),
            "archive_sha256": candidate_ref.get("archive_sha256"),
            "target_repo": target["target_repo"],
        },
        "would_change": [
            "repository visibility only after public-toggle green",
            "site or Pages visibility only after public-toggle green",
            "demo/media visibility only after media review clears",
            "outreach send only after operator send approval",
        ],
        "blocked_in_dry_run": [
            "github_repository_visibility_change",
            "public_site_enablement",
            "public_video_upload_or_visibility_change",
            "outreach_send",
            "source_available_or_open_source_wording",
        ],
        "included_surfaces_if_unblocked": publishable,
        "withheld_surfaces": withheld,
        "post_switch_abort_condition": (
            "If any post-switch private-marker, gitleaks, claim-language, media, "
            "or public-toggle check fails, restore private visibility, pause "
            "outreach/media, and regenerate escrow before reapproval."
        ),
    }


def _operator_decision_prompt(candidate_ref: dict[str, Any]) -> dict[str, Any]:
    exact_identity = (
        f"{candidate_ref.get('artifact_id')} source="
        f"{candidate_ref.get('source_commit')} artifact="
        f"{candidate_ref.get('artifact_git_head')} archive="
        f"{candidate_ref.get('archive_sha256')}"
    )
    return {
        "exact_candidate_identity": exact_identity,
        "allowed_yes": (
            "approve_this_exact_candidate_for_public_release_after_non_authority_"
            "blockers_clear_and_public_toggle_gate_reruns_green"
        ),
        "allowed_no": "hold_candidate_private_and_name_next_blocker",
        "allowed_regenerate": "regenerate_escrow_from_new_source_snapshot_before_review",
        "not_a_valid_yes": [
            "general vibe approval",
            "approval for latest HEAD",
            "approval for an unspecified future candidate",
            "approval that bypasses security/contact, media, or gate rerun evidence",
        ],
    }


def _closure_group(
    repo_root: Path,
    group_id: str,
    packet_group: dict[str, Any],
    intake_group: dict[str, Any],
    blockers_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    decision_ids = [str(row) for row in packet_group.get("decision_ids", [])]
    decision_blockers = [
        _compact_blocker(blockers_by_id[decision_id])
        for decision_id in decision_ids
        if decision_id in blockers_by_id
    ]
    scaffold = _scaffold_status(repo_root, group_id)
    open_required_decision_count = int(packet_group.get("open_decision_count", 0) or 0)
    queue_item_count = int(packet_group.get("queue_item_count", 0) or 0)
    open_decision_answer_count = int(
        intake_group.get("open_decision_answer_count", 0) or 0
    )
    queue_item_answer_count = int(intake_group.get("queue_item_answer_count", 0) or 0)
    answer_slot_count = open_decision_answer_count + queue_item_answer_count
    blocked_target_surface_count = int(
        scaffold.get("blocked_target_surface_count") or 0
    )
    status = (
        "operator_input_required"
        if open_required_decision_count or answer_slot_count or blocked_target_surface_count
        else "clear"
    )
    return {
        "id": group_id,
        "title": packet_group.get("title", intake_group.get("title")),
        "status": status,
        "public_toggle": "red" if status != "clear" else "amber",
        "purpose": packet_group.get("purpose", intake_group.get("purpose")),
        "decision_ids": decision_ids,
        "open_required_decision_count": open_required_decision_count,
        "queue_item_count": queue_item_count,
        "open_decision_answer_count": open_decision_answer_count,
        "queue_item_answer_count": queue_item_answer_count,
        "answer_slot_count": answer_slot_count,
        "blocked_target_surface_count": blocked_target_surface_count,
        "writable_target_surface_count": int(
            scaffold.get("writable_target_surface_count") or 0
        ),
        "operator_packet_status": packet_group.get("status"),
        "operator_intake_status": intake_group.get("status"),
        "scaffold": scaffold,
        "decision_blockers": decision_blockers,
        "closure_condition": (
            "All decision ids have recorded authority/evidence, queue items have "
            "retain/drop/replace/notice/no-release dispositions, and scaffolded "
            "target surfaces are written by their owner after the decisions exist."
        ),
        "does_not_authorize": [
            "public_release",
            "public_pr",
            "push",
            "publication",
            "dependency_changes",
            "frontend_implementation_changes",
            "demo_media_recording_or_export",
        ],
    }


def build_map(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    gate = _read_json(repo_root / PUBLIC_TOGGLE_GATE)
    register = _read_json(repo_root / RELEASE_DECISION_REGISTER)
    packet = _read_json(repo_root / OPERATOR_DECISION_PACKET)
    intake = _read_json(repo_root / OPERATOR_DECISION_INTAKE)
    candidate_ref, escrow, validation_receipt = _substrate_candidate_ref(repo_root)

    gate_summary = _safe_summary(gate)
    register_summary = _safe_summary(register)
    packet_summary = _safe_summary(packet)
    intake_summary = _safe_summary(intake)
    packet_groups = _group_rows(packet)
    intake_groups = _group_rows(intake)
    blockers_by_id = _blocking_conditions_by_id(gate)

    closure_groups = [
        _closure_group(
            repo_root,
            group_id,
            packet_groups.get(group_id, {}),
            intake_groups.get(group_id, {}),
            blockers_by_id,
        )
        for group_id in GROUP_ORDER
    ]
    open_closure_group_count = sum(1 for row in closure_groups if row["status"] != "clear")
    blocked_target_surface_count = sum(
        int(row["blocked_target_surface_count"]) for row in closure_groups
    )
    answer_slot_count = sum(int(row["answer_slot_count"]) for row in closure_groups)
    queue_item_count = sum(int(row["queue_item_count"]) for row in closure_groups)
    required_decision_blockers = [
        _compact_blocker(row)
        for row in blockers_by_id.values()
        if row.get("kind") == "required_release_decision"
    ]
    global_blockers = [
        _compact_blocker(row)
        for row in blockers_by_id.values()
        if row.get("kind") != "required_release_decision"
    ]
    status = "no_go" if gate.get("status") != "ready" or open_closure_group_count else "ready"
    blocker_closure = _blocker_closure(gate, escrow)
    decision_state = _decision_state(gate, status, escrow, blocker_closure)
    return {
        "schema_version": "release_public_toggle_closure_map_v0",
        "status": status,
        "public_toggle": "red" if status != "ready" else "green",
        "release_action": "none" if status != "ready" else "eligible_for_operator_release_decision",
        "source_authority": "private_repo",
        "projection_authority": "manifest_driven_public_projection",
        "purpose": (
            "Deterministic closure map for the red public-toggle gate. It binds "
            "the machine-readable gate blockers to operator action groups, answer "
            "slots, queue rows, and scaffolded target surfaces without choosing "
            "policy or authorizing release."
        ),
        "summary": {
            "public_toggle_gate_status": gate.get("status"),
            "public_toggle_gate_public_toggle": gate.get("public_toggle"),
            "public_toggle_blocking_condition_count": gate_summary.get(
                "blocking_condition_count", 0
            ),
            "portability_gate_status": gate_summary.get("portability_gate_status"),
            "viral_security_blocking_control_count": gate_summary.get(
                "viral_security_blocking_control_count", 0
            ),
            "closure_group_count": len(closure_groups),
            "open_closure_group_count": open_closure_group_count,
            "required_decision_count": register_summary.get("required_decision_count", 0),
            "implementation_check_count": gate_summary.get(
                "implementation_check_count", 0
            ),
            "operator_decision_lock_present": gate_summary.get(
                "operator_decision_lock_present", False
            ),
            "open_required_decision_count": packet_summary.get(
                "open_required_decision_count", 0
            ),
            "operator_open_action_group_count": packet_summary.get(
                "open_action_group_count", 0
            ),
            "queue_item_count": queue_item_count,
            "answer_slot_count": answer_slot_count,
            "blocked_target_surface_count": blocked_target_surface_count,
            "root_license_file_count": register_summary.get("root_license_file_count", 0),
            "security_contact_path_present": register_summary.get(
                "security_contact_path_present", False
            ),
            "substrate_candidate_identity_status": candidate_ref.get(
                "candidate_identity_status"
            ),
            "candidate_integrity": decision_state["candidate_integrity"],
            "public_release_authority": decision_state["public_release_authority"],
            "publication_operation": decision_state["publication_operation"],
            "operational_blocker_count": blocker_closure[
                "operational_blocker_count"
            ],
            "authority_blocker_count": blocker_closure["authority_blocker_count"],
            "switch_blocker_count": blocker_closure["switch_blocker_count"],
            "operator_review_ready": blocker_closure["operator_review_ready"],
            "contribution_policy_path_present": register_summary.get(
                "contribution_policy_path_present", False
            ),
            "intake_total_answer_slot_count": intake_summary.get(
                "total_answer_slot_count", 0
            ),
        },
        "gate_binding": {
            "path": PUBLIC_TOGGLE_GATE.as_posix(),
            "schema_version": gate.get("schema_version"),
            "status": gate.get("status"),
            "public_toggle": gate.get("public_toggle"),
            "blocking_condition_count": gate_summary.get("blocking_condition_count", 0),
            "portability_gate_status": gate_summary.get("portability_gate_status"),
        },
        "candidate_ref": candidate_ref,
        "decision_state": decision_state,
        "switches": _release_switches(gate, register, escrow),
        "blocker_closure": blocker_closure,
        "operator_decision_prompt": _operator_decision_prompt(candidate_ref),
        "dry_run_switch_plan": _dry_run_switch_plan(
            register,
            escrow,
            candidate_ref,
        ),
        "candidate_validation_binding": {
            "path": SUBSTRATE_RELEASE_VALIDATION_RECEIPT.as_posix(),
            "schema_version": validation_receipt.get("schema_version"),
            "status": validation_receipt.get("status"),
            "evaluated_commit": validation_receipt.get("evaluated_commit"),
            "artifact_git_head": validation_receipt.get("artifact_git_head"),
            "archive_sha256": (
                validation_receipt.get("artifact_hashes", {}) or {}
            ).get("archive_tar_gz")
            if isinstance(validation_receipt.get("artifact_hashes"), dict)
            else None,
        },
        "register_binding": {
            "path": RELEASE_DECISION_REGISTER.as_posix(),
            "schema_version": register.get("schema_version"),
            "status": register.get("status"),
            "public_toggle": register.get("public_toggle"),
            "required_decision_count": register_summary.get("required_decision_count", 0),
            "dependency_review_queue_count": register_summary.get(
                "dependency_review_queue_count", 0
            ),
        },
        "global_blockers": global_blockers,
        "required_decision_blockers": required_decision_blockers,
        "implementation_check_blockers": [
            _compact_blocker(row)
            for row in blockers_by_id.values()
            if row.get("kind") == "implementation_check"
        ],
        "closure_groups": closure_groups,
        "rerun_after_decision_record": [
            "./repo-python tools/meta/dissemination/release_decision_register.py --check",
            "./repo-python tools/meta/dissemination/release_operator_decision_packet.py --check",
            "./repo-python tools/meta/dissemination/release_operator_decision_intake.py --check",
            "./repo-python tools/meta/dissemination/release_public_governance_scaffold.py --check",
            "./repo-python tools/meta/dissemination/release_rights_posture_scaffold.py --check",
            "./repo-python tools/meta/dissemination/release_dependency_review_scaffold.py --check",
            "./repo-python tools/meta/dissemination/release_demo_media_review_scaffold.py --check",
            "./repo-python tools/meta/dissemination/release_claim_language_gate.py --check",
            "./repo-python tools/meta/dissemination/release_viral_security_gate.py --check",
            "./repo-python tools/meta/dissemination/public_toggle_readiness_gate.py --portability-report <latest_green_report> --check",
            "./repo-python tools/meta/dissemination/release_public_toggle_closure_map.py --check",
            "./repo-python tools/meta/dissemination/release_operator_action_matrix.py --check",
        ],
        "claim_guard": {
            "allowed_current_wording": [
                "public-toggle closure map exists",
                "public toggle remains red/no-go",
                "operator action groups are mapped to unanswered answer slots",
                "blocked target surfaces are counted but not materialized",
            ],
            "forbidden_current_wording": [
                "release ready",
                "open source",
                "publicly reproducible",
                "dependency review complete",
                "license cleared",
                "demo media cleared",
                "security/contact ready",
                "operator approved latest HEAD",
                "approval can apply to an unspecified future candidate",
            ],
        },
        "input_policy": {
            "template_edit_policy": "do_not_fill_or_resolve_decisions_in_this_map",
            "decision_record_destination": (
                "operator-owned decision record or future release decision register update"
            ),
            "does_not_authorize": [
                "public_release",
                "public_pr",
                "push",
                "publication",
                "license_selection",
                "dependency_replacement",
                "notice_file_creation",
                "security_contact_publication",
                "contribution_policy_publication",
                "demo_media_recording_or_export",
                "frontend_implementation_changes",
                "latest_head_release_approval",
            ],
        },
        "source_fingerprints": _source_fingerprints(repo_root, SOURCE_FINGERPRINT_PATHS),
    }


def write_map(
    output_path: Path,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    payload = build_map(repo_root)
    output = _repo_path(output_path, repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_canonical_json(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--assert-ready", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    output = _repo_path(args.output, repo_root)
    payload = build_map(repo_root)
    rendered = _canonical_json(payload)
    if args.check:
        if not output.exists():
            print(json.dumps({"ok": False, "missing": _rel(output, repo_root)}, sort_keys=True))
            return 1
        current = output.read_text(encoding="utf-8")
        if current != rendered:
            print(json.dumps({"ok": False, "mismatch": _rel(output, repo_root)}, sort_keys=True))
            return 1

    if not args.check:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    result = {
        "ok": True,
        "checked": bool(args.check),
        "path": _rel(output, repo_root),
        "status": payload["status"],
        "public_toggle": payload["public_toggle"],
        "open_closure_group_count": payload["summary"]["open_closure_group_count"],
        "answer_slot_count": payload["summary"]["answer_slot_count"],
        "blocked_target_surface_count": payload["summary"]["blocked_target_surface_count"],
    }
    if args.assert_ready and payload["status"] != "ready":
        result["ok"] = False
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
