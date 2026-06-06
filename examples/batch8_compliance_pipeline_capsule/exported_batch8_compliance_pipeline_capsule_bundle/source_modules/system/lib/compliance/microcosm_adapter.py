"""
[PURPOSE]
- Teleology: Project std_microcosm source-open product invariants into the
  generic compliance ledger so Atlas/navigation can see Microcosm compliance
  state through the existing compliance_ledger surface.
- Mechanism: Read std_microcosm.json, the public Microcosm entry packet, and
  the Microcosm standards registry; verify doctrine-lattice parity, source
  surface existence, first-screen navigation parity, registry count/file
  coverage, the public-export type-plane bridge, and the native standards
  meta-diagnostics lane.
- Non-goal: Re-run Microcosm validators, publish release readiness, mutate
  Microcosm source, or make system_microcosm public product authority.

[INTERFACE]
- scan_microcosm(repo_root): returns per-standard coverage payload for
  std_microcosm.

[CONSTRAINTS]
- Forbid: provider calls, network IO, source mutation, generated projection
  writes.
- Determinism: same persisted Microcosm substrate -> same finding ids.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_VALIDATOR = "system/lib/compliance/microcosm_adapter.py::scan_microcosm"
_STANDARD_ID = "std_microcosm"
_STANDARD_PATH = "codex/standards/std_microcosm.json"
_STANDARD_TYPE_PLANE_PATH = "codex/standards/std_standard_type_plane.json"
_ENTRY_PACKET_PATH = "microcosm-substrate/atlas/entry_packet.json"
_REGISTRY_PATH = "microcosm-substrate/core/standards_registry.json"
_STANDARDS_META_STANDARD_PATH = (
    "microcosm-substrate/standards/std_microcosm_standards_meta_diagnostics.json"
)
_STANDARDS_META_ORGAN_PATH = (
    "microcosm-substrate/src/microcosm_core/organs/standards_meta_diagnostics.py"
)
_STANDARDS_META_TEST_PATH = "microcosm-substrate/tests/test_standards_meta_diagnostics.py"
_COMPLIANCE_COVERAGE_STANDARD = "codex/standards/std_compliance_coverage.json"
_COMPLIANCE_FINDING_STANDARD = "codex/standards/std_compliance_finding.json"
_LEDGER_COVERAGE_PATH = "codex/hologram/compliance/ledger.json::by_standard[std_microcosm]"

_PARITY_FIELDS = (
    "principle_refs",
    "candidate_axiom_pressure_refs",
    "candidate_axiom_policy",
    "concept_refs",
    "mechanism_refs",
    "standard_refs",
    "paper_module_refs",
    "atlas_option_surfaces",
)

_SAFE_TO_SHOW_FIELDS = (
    "project_local_state_refs_visible",
    "route_metadata_visible",
    "receipt_refs_visible",
    "body_text_exported_in_status_or_observatory",
    "source_files_mutated",
    "provider_calls_authorized",
    "release_authorized",
    "proof_correctness_claim",
)

_PAPER_MODULE_COVERAGE_REQUIRED_FIELDS = (
    "primary_modules",
    "required_projection_surfaces",
    "atlas_option_surfaces",
    "healthy_state_receipt",
    "depth_order",
    "standard_type_plane_bridge",
    "authority_ceiling",
)

_PAPER_MODULE_COVERAGE_HEALTH_FIELDS = (
    "module_status",
    "queue_status",
    "fact_audit_status",
)

_PAPER_MODULE_COVERAGE_DEPTH_STEPS = (
    "entry_packet_selects_microcosm_public_substrate",
    "behavior_first_screen_visible",
    "microcosm_substrate_product_roof",
    "microcosm_entry_lattice_route_depth",
    "microcosm_public_export_type_plane_bridge",
    "microcosm_runtime_organ_atlas_source_loci_depth",
    "paper_module_coverage_metabolism_corpus_health",
    "selected_module_card_then_source_evidence",
)

_PAPER_MODULE_BRIDGE_REQUIRED_FIELDS = (
    "type_plane_row",
    "paper_module",
    "entry_route",
    "atlas_drilldowns",
    "authority_ceiling",
)

_PAPER_MODULE_BRIDGE_AUTHORITY_DENIALS = (
    "not_release",
    "source_truth",
    "provider",
    "proof",
    "candidate_axiom",
)

_PAPER_MODULE_COVERAGE_AUTHORITY_DENIALS = (
    "not_public_release",
    "source_truth",
    "proof",
    "candidate_axiom",
)

_MICROCOSM_REQUIRED_STANDARD_FIELDS = {
    "schema_version",
    "standard_id",
    "kind_id",
    "status",
    "authority_boundary",
    "source_refs",
    "relationships",
    "required_fields",
    "validation_rules",
    "receipt_expectations",
    "validator_contract",
    "receipt_contract",
    "public_private_boundary",
    "authority_ceiling",
    "anti_claim",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding_id(parts: list[str]) -> str:
    payload = "|".join(str(p) for p in parts).encode("utf-8")
    return "fcf_" + hashlib.sha256(payload).hexdigest()[:16]


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"json_decode_error:{exc.msg}"
    except OSError as exc:
        return None, f"os_error:{exc.__class__.__name__}"
    if not isinstance(payload, dict):
        return None, "not_object"
    return payload, None


def _public_microcosm_type_row(
    standard_type_plane: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not standard_type_plane:
        return None
    for row in standard_type_plane.get("type_plane_rows") or []:
        if not isinstance(row, dict):
            continue
        if row.get("type_id") == "public_microcosm_exports":
            return row
    return None


def _normalise_atlas_option_surfaces(value: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(value, list):
        return out
    for item in value:
        if isinstance(item, dict):
            kind = item.get("kind")
            if kind:
                out.append(str(kind))
        elif item:
            out.append(str(item))
    return out


def _finding(
    *,
    validated_at: str,
    finding_kind: str,
    severity: str,
    artifact_path: str,
    scope_kind: str,
    scope_id: str,
    summary: str,
    evidence_refs: list[str],
    candidate_target_paths: list[str],
    mutation_class: str,
    missing_fields: list[str] | None = None,
    candidate_target_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing = sorted(missing_fields or [])
    return {
        "finding_id": _finding_id([
            _STANDARD_ID,
            artifact_path,
            scope_kind,
            scope_id,
            finding_kind,
            ",".join(missing),
        ]),
        "standard_id": _STANDARD_ID,
        "validator": _VALIDATOR,
        "validated_at": validated_at,
        "finding_kind": finding_kind,
        "severity": severity,
        "artifact_path": artifact_path,
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "summary": summary,
        "missing_fields": missing,
        "missing_atoms": [],
        "evidence_refs": evidence_refs,
        "candidate_target_paths": candidate_target_paths,
        "candidate_target_payload": candidate_target_payload or {},
        "mutation_class": mutation_class,
        "provider_hint": "type_a_only",
        "authority_ceiling": "authoring_agent",
        "status": "open",
    }


def _path_exists(repo_root: Path, rel_path: str) -> bool:
    return (repo_root / rel_path).exists()


def _registry_standard_file(repo_root: Path, row: dict[str, Any]) -> Path:
    row_path = str(row.get("path") or "").strip()
    if row_path:
        return repo_root / "microcosm-substrate" / row_path
    standard_id = str(row.get("standard_id") or "")
    return repo_root / "microcosm-substrate" / "standards" / f"{standard_id}.json"


def _scan_doctrine_lattice(
    repo_root: Path,
    *,
    std_microcosm: dict[str, Any] | None,
    entry_packet: dict[str, Any] | None,
    validated_at: str,
) -> tuple[int, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    checks = len(_PARITY_FIELDS)
    if not std_microcosm or not entry_packet:
        return checks, findings

    standard_lattice = std_microcosm.get("doctrine_lattice") or {}
    entry_lattice = entry_packet.get("doctrine_lattice_route") or {}
    for field in _PARITY_FIELDS:
        expected = standard_lattice.get(field)
        observed = entry_lattice.get(field)
        if field == "atlas_option_surfaces":
            observed = _normalise_atlas_option_surfaces(observed)
        if expected != observed:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="schema_violation",
                severity="error",
                artifact_path=_ENTRY_PACKET_PATH,
                scope_kind="field",
                scope_id=f"doctrine_lattice_route.{field}",
                summary=(
                    f"Microcosm entry packet doctrine_lattice_route.{field} does not "
                    "match std_microcosm.json::doctrine_lattice."
                ),
                evidence_refs=[
                    f"{_STANDARD_PATH}::doctrine_lattice.{field}",
                    f"{_ENTRY_PACKET_PATH}::doctrine_lattice_route.{field}",
                ],
                candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
                candidate_target_payload={"field": field},
                mutation_class="rewrite_field",
            ))
    return checks, findings


def _reader_routes_by_id(entry_packet: dict[str, Any]) -> dict[str, list[str]]:
    routes = (entry_packet.get("reader_first_screen_routes") or {}).get("routes") or []
    out: dict[str, list[str]] = {}
    for row in routes:
        if not isinstance(row, dict):
            continue
        reader_id = str(row.get("reader_id") or "").strip()
        if not reader_id:
            continue
        commands: list[str] = []
        for field in ("first_screen_command", "next_command", "followup_command"):
            command = str(row.get(field) or "").strip()
            if not command:
                continue
            commands.extend(part.strip() for part in command.split("&&") if part.strip())
        out[reader_id] = [command for command in commands if command]
    return out


def _normalised_safe_to_show(entry_packet: dict[str, Any]) -> dict[str, Any]:
    local = (entry_packet.get("local_first_screen_route") or {}).get("safe_to_show") or {}
    status = (entry_packet.get("status_and_workingness_route") or {}).get("safe_to_show") or {}
    observatory = (entry_packet.get("observatory_route") or {}).get("safe_to_show") or {}
    proof = (entry_packet.get("proof_lab_route") or {}).get("safe_to_show") or {}
    pattern = (entry_packet.get("pattern_route_readiness_route") or {}).get("safe_to_show") or {}
    return {
        "project_local_state_refs_visible": bool(
            local.get("project_local_state_refs_visible")
            or observatory.get("project_local_state_refs_visible")
        ),
        "route_metadata_visible": bool(
            observatory.get("route_metadata_visible")
            or proof.get("route_metadata_visible")
            or pattern.get("route_metadata_visible")
        ),
        "receipt_refs_visible": bool(
            status.get("receipt_refs_visible")
            or observatory.get("receipt_refs_visible")
            or proof.get("receipt_refs_visible")
            or pattern.get("receipt_refs_visible")
        ),
        "body_text_exported_in_status_or_observatory": bool(
            status.get("body_text_exported_in_status")
            or observatory.get("body_text_exported_in_observatory")
        ),
        "source_files_mutated": bool(
            local.get("source_files_mutated")
            or observatory.get("source_files_mutated")
            or status.get("source_mutation_authorized")
        ),
        "provider_calls_authorized": bool(
            local.get("provider_calls_authorized")
            or status.get("provider_calls_authorized")
            or observatory.get("provider_calls_authorized")
        ),
        "release_authorized": bool(
            local.get("release_authorized")
            or status.get("release_authorized")
            or observatory.get("release_authorized")
            or proof.get("release_authorized")
            or pattern.get("release_authorized")
        ),
        "proof_correctness_claim": bool(
            local.get("proof_correctness_claim")
            or status.get("proof_correctness_claim")
            or observatory.get("proof_correctness_claim")
        ),
    }


def _scan_first_screen_navigation_contract(
    repo_root: Path,
    *,
    std_microcosm: dict[str, Any] | None,
    entry_packet: dict[str, Any] | None,
    validated_at: str,
) -> tuple[int, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    checks = 1
    if not std_microcosm or not entry_packet:
        return checks, findings

    contract = std_microcosm.get("first_screen_navigation_contract")
    if not isinstance(contract, dict):
        return checks, [
            _finding(
                validated_at=validated_at,
                finding_kind="missing_required_field",
                severity="error",
                artifact_path=_STANDARD_PATH,
                scope_kind="field",
                scope_id="first_screen_navigation_contract",
                summary="std_microcosm is missing the first-screen navigation contract.",
                missing_fields=["first_screen_navigation_contract"],
                evidence_refs=[_STANDARD_PATH],
                candidate_target_paths=[_STANDARD_PATH],
                mutation_class="add_required_field",
            )
        ]

    local_route = entry_packet.get("local_first_screen_route")
    local_route = local_route if isinstance(local_route, dict) else {}
    expected_first_command = contract.get("shared_first_screen_command")
    observed_first_commands = {
        "first_command": entry_packet.get("first_command"),
        "local_first_screen_route.primary_first_screen_command": local_route.get(
            "primary_first_screen_command"
        ),
    }
    for scope, observed in observed_first_commands.items():
        checks += 1
        if observed != expected_first_command:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="schema_violation",
                severity="error",
                artifact_path=_ENTRY_PACKET_PATH,
                scope_kind="field",
                scope_id=scope,
                summary="Microcosm entry packet first-screen command drifts from std_microcosm.",
                evidence_refs=[
                    f"{_STANDARD_PATH}::first_screen_navigation_contract.shared_first_screen_command",
                    f"{_ENTRY_PACKET_PATH}::{scope}",
                ],
                candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
                candidate_target_payload={
                    "expected": expected_first_command,
                    "observed": observed,
                },
                mutation_class="rewrite_field",
            ))

    checks += 1
    if local_route.get("state_dir") != contract.get("state_dir"):
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_ENTRY_PACKET_PATH,
            scope_kind="field",
            scope_id="local_first_screen_route.state_dir",
            summary="Microcosm entry packet state_dir drifts from std_microcosm.",
            evidence_refs=[
                f"{_STANDARD_PATH}::first_screen_navigation_contract.state_dir",
                f"{_ENTRY_PACKET_PATH}::local_first_screen_route.state_dir",
            ],
            candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
            candidate_target_payload={
                "expected": contract.get("state_dir"),
                "observed": local_route.get("state_dir"),
            },
            mutation_class="rewrite_field",
        ))

    for route_ref in contract.get("required_route_refs") or []:
        checks += 1
        if not isinstance(entry_packet.get(str(route_ref)), dict):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref",
                severity="error",
                artifact_path=_ENTRY_PACKET_PATH,
                scope_kind="route_ref",
                scope_id=str(route_ref),
                summary=f"Microcosm entry packet is missing required first-screen route ref: {route_ref}",
                evidence_refs=[
                    f"{_STANDARD_PATH}::first_screen_navigation_contract.required_route_refs",
                    f"{_ENTRY_PACKET_PATH}::{route_ref}",
                ],
                candidate_target_paths=[_ENTRY_PACKET_PATH],
                candidate_target_payload={"missing_route_ref": route_ref},
                mutation_class="fix_broken_ref",
            ))

    checks += 1
    expected_state_refs = list(contract.get("required_project_state_refs") or [])
    observed_state_refs = list(local_route.get("state_refs") or [])
    if observed_state_refs != expected_state_refs:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_ENTRY_PACKET_PATH,
            scope_kind="field",
            scope_id="local_first_screen_route.state_refs",
            summary="Microcosm first-screen project state refs drift from std_microcosm.",
            evidence_refs=[
                f"{_STANDARD_PATH}::first_screen_navigation_contract.required_project_state_refs",
                f"{_ENTRY_PACKET_PATH}::local_first_screen_route.state_refs",
            ],
            candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
            candidate_target_payload={
                "expected": expected_state_refs,
                "observed": observed_state_refs,
            },
            mutation_class="rewrite_field",
        ))

    reader_policy = contract.get("reader_branch_policy") or {}
    entry_reader_policy = entry_packet.get("reader_first_screen_routes") or {}
    checks += 1
    if entry_reader_policy.get("shared_prerequisite_command") != reader_policy.get(
        "shared_prerequisite_command"
    ):
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_ENTRY_PACKET_PATH,
            scope_kind="field",
            scope_id="reader_first_screen_routes.shared_prerequisite_command",
            summary="Microcosm reader first-screen prerequisite command drifts from std_microcosm.",
            evidence_refs=[
                f"{_STANDARD_PATH}::first_screen_navigation_contract.reader_branch_policy",
                f"{_ENTRY_PACKET_PATH}::reader_first_screen_routes",
            ],
            candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
            candidate_target_payload={
                "expected": reader_policy.get("shared_prerequisite_command"),
                "observed": entry_reader_policy.get("shared_prerequisite_command"),
            },
            mutation_class="rewrite_field",
        ))

    observed_reader_routes = _reader_routes_by_id(entry_packet)
    for reader_id, expected_commands in (reader_policy.get("routes") or {}).items():
        checks += 1
        observed_commands = observed_reader_routes.get(str(reader_id), [])
        if list(expected_commands) != observed_commands:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="schema_violation",
                severity="error",
                artifact_path=_ENTRY_PACKET_PATH,
                scope_kind="reader_route",
                scope_id=f"reader_first_screen_routes.{reader_id}",
                summary=f"Microcosm reader route {reader_id!r} drifts from std_microcosm.",
                evidence_refs=[
                    f"{_STANDARD_PATH}::first_screen_navigation_contract.reader_branch_policy.routes.{reader_id}",
                    f"{_ENTRY_PACKET_PATH}::reader_first_screen_routes",
                ],
                candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
                candidate_target_payload={
                    "expected": list(expected_commands),
                    "observed": observed_commands,
                },
                mutation_class="rewrite_field",
            ))

    observed_safe_to_show = _normalised_safe_to_show(entry_packet)
    expected_safe_to_show = contract.get("safe_to_show") or {}
    for field in _SAFE_TO_SHOW_FIELDS:
        checks += 1
        if observed_safe_to_show.get(field) != expected_safe_to_show.get(field):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="authority_boundary_drift",
                severity="error",
                artifact_path=_ENTRY_PACKET_PATH,
                scope_kind="field",
                scope_id=f"first_screen_navigation_contract.safe_to_show.{field}",
                summary=f"Microcosm safe-to-show invariant {field!r} drifts from std_microcosm.",
                evidence_refs=[
                    f"{_STANDARD_PATH}::first_screen_navigation_contract.safe_to_show.{field}",
                    f"{_ENTRY_PACKET_PATH}::*_route.safe_to_show",
                ],
                candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
                candidate_target_payload={
                    "expected": expected_safe_to_show.get(field),
                    "observed": observed_safe_to_show.get(field),
                },
                mutation_class="rewrite_field",
            ))

    checks += 1
    authority_text = " ".join([
        str(entry_packet.get("authority_ceiling") or ""),
        str(local_route.get("authority") or ""),
        str((entry_packet.get("reader_first_screen_routes") or {}).get("authority") or ""),
    ]).lower()
    missing_authority_denials = [
        token
        for token in ("release", "provider", "proof", "mutation")
        if token not in authority_text
    ]
    if missing_authority_denials:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="authority_boundary_drift",
            severity="error",
            artifact_path=_ENTRY_PACKET_PATH,
            scope_kind="authority",
            scope_id="first_screen_authority_denials",
            summary="Microcosm first-screen route authority text lost required denial terms.",
            missing_fields=missing_authority_denials,
            evidence_refs=[
                f"{_STANDARD_PATH}::first_screen_navigation_contract.authority_ceiling",
                f"{_ENTRY_PACKET_PATH}::authority_ceiling",
                f"{_ENTRY_PACKET_PATH}::local_first_screen_route.authority",
            ],
            candidate_target_paths=[_STANDARD_PATH, _ENTRY_PACKET_PATH],
            candidate_target_payload={"missing_denials": missing_authority_denials},
            mutation_class="rewrite_field",
        ))

    return checks, findings


def _scan_paper_module_coverage_contract(
    repo_root: Path,
    *,
    std_microcosm: dict[str, Any] | None,
    standard_type_plane: dict[str, Any] | None,
    validated_at: str,
) -> tuple[int, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    checks = 1
    if not std_microcosm:
        return checks, findings

    contract = std_microcosm.get("paper_module_coverage_contract")
    if not isinstance(contract, dict):
        return checks, [
            _finding(
                validated_at=validated_at,
                finding_kind="missing_required_field",
                severity="error",
                artifact_path=_STANDARD_PATH,
                scope_kind="field",
                scope_id="paper_module_coverage_contract",
                summary="std_microcosm is missing the paper-module coverage/depth contract.",
                missing_fields=["paper_module_coverage_contract"],
                evidence_refs=[_STANDARD_PATH],
                candidate_target_paths=[_STANDARD_PATH],
                mutation_class="add_required_field",
            )
        ]

    missing_fields = [
        field
        for field in _PAPER_MODULE_COVERAGE_REQUIRED_FIELDS
        if field not in contract
    ]
    checks += len(_PAPER_MODULE_COVERAGE_REQUIRED_FIELDS)
    if missing_fields:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="missing_required_field",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract",
            summary="Microcosm paper-module coverage contract is missing required fields.",
            missing_fields=missing_fields,
            evidence_refs=[f"{_STANDARD_PATH}::paper_module_coverage_contract"],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"missing_fields": missing_fields},
            mutation_class="add_required_field",
        ))

    for field in ("primary_modules", "required_projection_surfaces", "atlas_option_surfaces", "depth_order"):
        checks += 1
        if not isinstance(contract.get(field), list) or not contract.get(field):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="schema_violation",
                severity="error",
                artifact_path=_STANDARD_PATH,
                scope_kind="field",
                scope_id=f"paper_module_coverage_contract.{field}",
                summary=f"Microcosm paper-module coverage contract field {field} must be a non-empty list.",
                evidence_refs=[f"{_STANDARD_PATH}::paper_module_coverage_contract.{field}"],
                candidate_target_paths=[_STANDARD_PATH],
                candidate_target_payload={"field": field},
                mutation_class="rewrite_field",
            ))

    for rel_path in contract.get("primary_modules") or []:
        checks += 1
        rel = str(rel_path)
        if not _path_exists(repo_root, rel):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref",
                severity="error",
                artifact_path=_STANDARD_PATH,
                scope_kind="ref",
                scope_id=f"paper_module_coverage_contract.primary_modules:{rel}",
                summary=f"Microcosm paper-module coverage primary module does not resolve: {rel}",
                evidence_refs=[f"{_STANDARD_PATH}::paper_module_coverage_contract.primary_modules"],
                candidate_target_paths=[_STANDARD_PATH, rel],
                candidate_target_payload={"missing_ref": rel},
                mutation_class="fix_broken_ref",
            ))

    for rel_path in contract.get("required_projection_surfaces") or []:
        checks += 1
        rel = str(rel_path)
        if not _path_exists(repo_root, rel):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref",
                severity="error",
                artifact_path=_STANDARD_PATH,
                scope_kind="ref",
                scope_id=f"paper_module_coverage_contract.required_projection_surfaces:{rel}",
                summary=f"Microcosm paper-module coverage projection surface does not resolve: {rel}",
                evidence_refs=[
                    f"{_STANDARD_PATH}::paper_module_coverage_contract.required_projection_surfaces"
                ],
                candidate_target_paths=[_STANDARD_PATH, rel],
                candidate_target_payload={"missing_ref": rel},
                mutation_class="fix_broken_ref",
            ))

    coverage_surfaces = set(str(item) for item in contract.get("atlas_option_surfaces") or [])
    lattice_surfaces = set(
        str(item)
        for item in ((std_microcosm.get("doctrine_lattice") or {}).get("atlas_option_surfaces") or [])
    )
    checks += 1
    missing_from_lattice = sorted(coverage_surfaces - lattice_surfaces)
    if missing_from_lattice:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.atlas_option_surfaces",
            summary="Microcosm paper-module coverage surfaces are not present in the doctrine lattice Atlas surface set.",
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.atlas_option_surfaces",
                f"{_STANDARD_PATH}::doctrine_lattice.atlas_option_surfaces",
            ],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"missing_from_lattice": missing_from_lattice},
            mutation_class="rewrite_field",
        ))

    health = contract.get("healthy_state_receipt")
    checks += len(_PAPER_MODULE_COVERAGE_HEALTH_FIELDS)
    if not isinstance(health, dict):
        health = {}
    missing_health = [
        field
        for field in _PAPER_MODULE_COVERAGE_HEALTH_FIELDS
        if not health.get(field)
    ]
    if missing_health:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="missing_required_field",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.healthy_state_receipt",
            summary="Microcosm paper-module coverage contract is missing healthy-state receipt atoms.",
            missing_fields=missing_health,
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.healthy_state_receipt"
            ],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"missing_fields": missing_health},
            mutation_class="add_required_field",
        ))

    depth_order = set(str(item) for item in contract.get("depth_order") or [])
    missing_depth = [
        step for step in _PAPER_MODULE_COVERAGE_DEPTH_STEPS if step not in depth_order
    ]
    checks += len(_PAPER_MODULE_COVERAGE_DEPTH_STEPS)
    if missing_depth:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.depth_order",
            summary="Microcosm paper-module coverage contract is missing required depth-order steps.",
            missing_fields=missing_depth,
            evidence_refs=[f"{_STANDARD_PATH}::paper_module_coverage_contract.depth_order"],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"missing_steps": missing_depth},
            mutation_class="rewrite_field",
        ))

    bridge = contract.get("standard_type_plane_bridge")
    checks += 1
    if not isinstance(bridge, dict):
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="missing_required_field",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.standard_type_plane_bridge",
            summary="Microcosm paper-module coverage contract is missing the public export type-plane bridge.",
            missing_fields=["standard_type_plane_bridge"],
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge"
            ],
            candidate_target_paths=[_STANDARD_PATH],
            mutation_class="add_required_field",
        ))
        bridge = {}

    missing_bridge_fields = [
        field
        for field in _PAPER_MODULE_BRIDGE_REQUIRED_FIELDS
        if not bridge.get(field)
    ]
    checks += len(_PAPER_MODULE_BRIDGE_REQUIRED_FIELDS)
    if missing_bridge_fields:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="missing_required_field",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.standard_type_plane_bridge",
            summary="Microcosm public export type-plane bridge is missing required fields.",
            missing_fields=missing_bridge_fields,
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge"
            ],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"missing_fields": missing_bridge_fields},
            mutation_class="add_required_field",
        ))

    bridge_module = str(bridge.get("paper_module") or "")
    checks += 1
    if bridge_module and not _path_exists(repo_root, bridge_module):
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="broken_ref",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="ref",
            scope_id=f"paper_module_coverage_contract.standard_type_plane_bridge.paper_module:{bridge_module}",
            summary=f"Microcosm public export type-plane bridge module does not resolve: {bridge_module}",
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge.paper_module"
            ],
            candidate_target_paths=[_STANDARD_PATH, bridge_module],
            candidate_target_payload={"missing_ref": bridge_module},
            mutation_class="fix_broken_ref",
        ))

    bridge_entry_route = str(bridge.get("entry_route") or "")
    checks += 1
    if bridge_entry_route and "--entry" not in bridge_entry_route:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.standard_type_plane_bridge.entry_route",
            summary="Microcosm public export type-plane bridge must route broad prompts through --entry.",
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge.entry_route"
            ],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"observed": bridge_entry_route},
            mutation_class="rewrite_field",
        ))

    bridge_authority = str(bridge.get("authority_ceiling") or "")
    missing_bridge_denials = [
        denial
        for denial in _PAPER_MODULE_BRIDGE_AUTHORITY_DENIALS
        if denial not in bridge_authority
    ]
    checks += len(_PAPER_MODULE_BRIDGE_AUTHORITY_DENIALS)
    if missing_bridge_denials:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="authority_boundary_gap",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.standard_type_plane_bridge.authority_ceiling",
            summary="Microcosm public export type-plane bridge authority ceiling is missing required denials.",
            missing_fields=missing_bridge_denials,
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge.authority_ceiling"
            ],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"missing_denials": missing_bridge_denials},
            mutation_class="rewrite_field",
        ))

    type_row = _public_microcosm_type_row(standard_type_plane)
    expected_type_ref = (
        "codex/standards/std_standard_type_plane.json::type_plane_rows.public_microcosm_exports"
    )
    checks += 1
    if bridge.get("type_plane_row") != expected_type_ref:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.standard_type_plane_bridge.type_plane_row",
            summary="Microcosm public export type-plane bridge points at the wrong type-plane row.",
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge.type_plane_row",
                f"{_STANDARD_TYPE_PLANE_PATH}::type_plane_rows.public_microcosm_exports",
            ],
            candidate_target_paths=[_STANDARD_PATH, _STANDARD_TYPE_PLANE_PATH],
            candidate_target_payload={
                "expected": expected_type_ref,
                "observed": bridge.get("type_plane_row"),
            },
            mutation_class="rewrite_field",
        ))

    checks += 1
    if not type_row:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="broken_ref",
            severity="error",
            artifact_path=_STANDARD_TYPE_PLANE_PATH,
            scope_kind="row",
            scope_id="type_plane_rows.public_microcosm_exports",
            summary="std_standard_type_plane is missing the public_microcosm_exports row named by std_microcosm.",
            evidence_refs=[
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge",
                _STANDARD_TYPE_PLANE_PATH,
            ],
            candidate_target_paths=[_STANDARD_TYPE_PLANE_PATH],
            mutation_class="fix_broken_ref",
        ))
    else:
        governing_refs = set(str(item) for item in type_row.get("governing_standard_refs") or [])
        projection_refs = set(str(item) for item in type_row.get("projection_refs") or [])
        checks += 2
        if bridge_module and bridge_module not in governing_refs:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref",
                severity="error",
                artifact_path=_STANDARD_TYPE_PLANE_PATH,
                scope_kind="ref",
                scope_id="type_plane_rows.public_microcosm_exports.governing_standard_refs",
                summary="public_microcosm_exports does not govern through the Microcosm public export bridge module.",
                evidence_refs=[
                    f"{_STANDARD_TYPE_PLANE_PATH}::type_plane_rows.public_microcosm_exports.governing_standard_refs",
                    f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge.paper_module",
                ],
                candidate_target_paths=[_STANDARD_TYPE_PLANE_PATH],
                candidate_target_payload={"missing_ref": bridge_module},
                mutation_class="add_required_field",
            ))
        if bridge_module and bridge_module not in projection_refs:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref",
                severity="error",
                artifact_path=_STANDARD_TYPE_PLANE_PATH,
                scope_kind="ref",
                scope_id="type_plane_rows.public_microcosm_exports.projection_refs",
                summary="public_microcosm_exports projection refs do not name the Microcosm public export bridge module.",
                evidence_refs=[
                    f"{_STANDARD_TYPE_PLANE_PATH}::type_plane_rows.public_microcosm_exports.projection_refs",
                    f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge.paper_module",
                ],
                candidate_target_paths=[_STANDARD_TYPE_PLANE_PATH],
                candidate_target_payload={"missing_ref": bridge_module},
                mutation_class="add_required_field",
            ))

        entry_depth = type_row.get("entry_depth_contract")
        checks += 1
        if not isinstance(entry_depth, dict):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="missing_required_field",
                severity="error",
                artifact_path=_STANDARD_TYPE_PLANE_PATH,
                scope_kind="field",
                scope_id="type_plane_rows.public_microcosm_exports.entry_depth_contract",
                summary="public_microcosm_exports is missing the Microcosm entry-depth contract.",
                missing_fields=["entry_depth_contract"],
                evidence_refs=[
                    f"{_STANDARD_TYPE_PLANE_PATH}::type_plane_rows.public_microcosm_exports",
                    f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge",
                ],
                candidate_target_paths=[_STANDARD_TYPE_PLANE_PATH],
                mutation_class="add_required_field",
            ))
        else:
            depth_order = set(str(item) for item in entry_depth.get("paper_module_depth_order") or [])
            checks += 2
            if "microcosm_public_export_type_plane" not in depth_order:
                findings.append(_finding(
                    validated_at=validated_at,
                    finding_kind="schema_violation",
                    severity="error",
                    artifact_path=_STANDARD_TYPE_PLANE_PATH,
                    scope_kind="field",
                    scope_id="type_plane_rows.public_microcosm_exports.entry_depth_contract.paper_module_depth_order",
                    summary="public_microcosm_exports entry-depth contract does not include the public export bridge module.",
                    missing_fields=["microcosm_public_export_type_plane"],
                    evidence_refs=[
                        f"{_STANDARD_TYPE_PLANE_PATH}::type_plane_rows.public_microcosm_exports.entry_depth_contract",
                        bridge_module,
                    ],
                    candidate_target_paths=[_STANDARD_TYPE_PLANE_PATH],
                    mutation_class="rewrite_field",
                ))
            if entry_depth.get("standard_bridge") != (
                f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge"
            ):
                findings.append(_finding(
                    validated_at=validated_at,
                    finding_kind="schema_violation",
                    severity="error",
                    artifact_path=_STANDARD_TYPE_PLANE_PATH,
                    scope_kind="field",
                    scope_id="type_plane_rows.public_microcosm_exports.entry_depth_contract.standard_bridge",
                    summary="public_microcosm_exports entry-depth contract does not point back to std_microcosm's bridge field.",
                    evidence_refs=[
                        f"{_STANDARD_TYPE_PLANE_PATH}::type_plane_rows.public_microcosm_exports.entry_depth_contract.standard_bridge",
                        f"{_STANDARD_PATH}::paper_module_coverage_contract.standard_type_plane_bridge",
                    ],
                    candidate_target_paths=[_STANDARD_TYPE_PLANE_PATH],
                    candidate_target_payload={
                        "observed": entry_depth.get("standard_bridge")
                    },
                    mutation_class="rewrite_field",
                ))

    authority_ceiling = str(contract.get("authority_ceiling") or "")
    missing_denials = [
        denial
        for denial in _PAPER_MODULE_COVERAGE_AUTHORITY_DENIALS
        if denial not in authority_ceiling
    ]
    checks += len(_PAPER_MODULE_COVERAGE_AUTHORITY_DENIALS)
    if missing_denials:
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="authority_boundary_gap",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="paper_module_coverage_contract.authority_ceiling",
            summary="Microcosm paper-module coverage contract authority ceiling is missing required denials.",
            missing_fields=missing_denials,
            evidence_refs=[f"{_STANDARD_PATH}::paper_module_coverage_contract.authority_ceiling"],
            candidate_target_paths=[_STANDARD_PATH],
            candidate_target_payload={"missing_denials": missing_denials},
            mutation_class="rewrite_field",
        ))

    validation_rules = [
        rule
        for rule in (std_microcosm.get("validation_rules") or [])
        if isinstance(rule, dict)
    ]
    checks += 1
    if not any(rule.get("id") == "microcosm_paper_module_coverage_contract" for rule in validation_rules):
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="missing_required_field",
            severity="error",
            artifact_path=_STANDARD_PATH,
            scope_kind="field",
            scope_id="validation_rules.microcosm_paper_module_coverage_contract",
            summary="std_microcosm validation_rules is missing the paper-module coverage contract rule.",
            missing_fields=["microcosm_paper_module_coverage_contract"],
            evidence_refs=[
                f"{_STANDARD_PATH}::validation_rules",
                f"{_STANDARD_PATH}::paper_module_coverage_contract",
            ],
            candidate_target_paths=[_STANDARD_PATH],
            mutation_class="add_required_field",
        ))

    return checks, findings


def _scan_source_surfaces(
    repo_root: Path,
    *,
    std_microcosm: dict[str, Any] | None,
    validated_at: str,
) -> tuple[int, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    surfaces = []
    if std_microcosm:
        surfaces = list((std_microcosm.get("governance") or {}).get("current_source_surfaces") or [])
    for rel_path in surfaces:
        rel = str(rel_path)
        if not _path_exists(repo_root, rel):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref",
                severity="error",
                artifact_path=_STANDARD_PATH,
                scope_kind="ref",
                scope_id=f"governance.current_source_surfaces:{rel}",
                summary=f"std_microcosm current source surface does not resolve: {rel}",
                evidence_refs=[f"{_STANDARD_PATH}::governance.current_source_surfaces"],
                candidate_target_paths=[_STANDARD_PATH],
                candidate_target_payload={"missing_ref": rel},
                mutation_class="fix_broken_ref",
            ))
    return len(surfaces), findings


def _scan_registry(
    repo_root: Path,
    *,
    registry: dict[str, Any] | None,
    validated_at: str,
) -> tuple[int, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    if not registry:
        return 1, findings

    rows = [row for row in (registry.get("standards") or []) if isinstance(row, dict)]
    declared_count = int(registry.get("standard_count") or len(rows))
    if declared_count != len(rows):
        findings.append(_finding(
            validated_at=validated_at,
            finding_kind="schema_violation",
            severity="error",
            artifact_path=_REGISTRY_PATH,
            scope_kind="field",
            scope_id="standard_count",
            summary=(
                f"Microcosm standards registry declares {declared_count} standards "
                f"but contains {len(rows)} rows."
            ),
            evidence_refs=[_REGISTRY_PATH],
            candidate_target_paths=[_REGISTRY_PATH],
            candidate_target_payload={"declared_count": declared_count, "actual_count": len(rows)},
            mutation_class="rewrite_field",
        ))

    standard_ids = [str(row.get("standard_id") or "") for row in rows]
    for standard_id, count in Counter(standard_ids).items():
        if standard_id and count > 1:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="duplicate_id",
                severity="error",
                artifact_path=_REGISTRY_PATH,
                scope_kind="row",
                scope_id=f"standards[{standard_id}]",
                summary=f"Microcosm standards registry has duplicate standard_id {standard_id!r}.",
                evidence_refs=[_REGISTRY_PATH],
                candidate_target_paths=[_REGISTRY_PATH],
                candidate_target_payload={"standard_id": standard_id},
                mutation_class="rename_duplicate_id",
            ))

    for row in rows:
        standard_id = str(row.get("standard_id") or "")
        standard_file = _registry_standard_file(repo_root, row)
        try:
            rel_file = standard_file.relative_to(repo_root).as_posix()
        except ValueError:
            rel_file = str(standard_file)
        standard, error = _load_json(standard_file)
        if error:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref" if error == "missing" else "parse_error",
                severity="error",
                artifact_path=_REGISTRY_PATH,
                scope_kind="ref",
                scope_id=f"standards[{standard_id}].path",
                summary=f"Microcosm registry row {standard_id!r} points at unreadable standard file: {rel_file}.",
                evidence_refs=[_REGISTRY_PATH, rel_file],
                candidate_target_paths=[_REGISTRY_PATH, rel_file],
                candidate_target_payload={"standard_id": standard_id, "path": rel_file, "error": error},
                mutation_class="fix_broken_ref",
            ))
            continue
        missing = sorted(field for field in _MICROCOSM_REQUIRED_STANDARD_FIELDS if field not in standard)
        if missing:
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="missing_required_field",
                severity="warning",
                artifact_path=rel_file,
                scope_kind="artifact",
                scope_id=standard_id or rel_file,
                summary=f"Microcosm standard {standard_id!r} is missing required public registry fields.",
                missing_fields=missing,
                evidence_refs=[
                    _REGISTRY_PATH,
                    "microcosm-substrate/standards/std_microcosm_standards_registry.json",
                    rel_file,
                ],
                candidate_target_paths=[rel_file],
                candidate_target_payload={"standard_id": standard_id, "missing_fields": missing},
                mutation_class="add_required_field",
            ))
    return max(1, len(rows)), findings


def _scan_standards_meta_lane(repo_root: Path, *, validated_at: str) -> tuple[int, list[dict[str, Any]]]:
    expected = [
        _STANDARDS_META_STANDARD_PATH,
        _STANDARDS_META_ORGAN_PATH,
        _STANDARDS_META_TEST_PATH,
    ]
    findings: list[dict[str, Any]] = []
    for rel in expected:
        if not _path_exists(repo_root, rel):
            findings.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref",
                severity="error",
                artifact_path=_STANDARD_PATH,
                scope_kind="ref",
                scope_id=f"standards_meta_diagnostics:{rel}",
                summary=f"Microcosm standards-meta diagnostics lane is missing expected surface: {rel}",
                evidence_refs=[_STANDARD_PATH, _COMPLIANCE_COVERAGE_STANDARD],
                candidate_target_paths=[rel],
                candidate_target_payload={"missing_ref": rel},
                mutation_class="fix_broken_ref",
            ))
    return len(expected), findings


def scan_microcosm(repo_root: Path) -> dict[str, Any]:
    validated_at = _utc_now()
    findings_out: list[dict[str, Any]] = []
    check_count = 0

    std_microcosm, std_error = _load_json(repo_root / _STANDARD_PATH)
    standard_type_plane, type_plane_error = _load_json(
        repo_root / _STANDARD_TYPE_PLANE_PATH
    )
    entry_packet, entry_error = _load_json(repo_root / _ENTRY_PACKET_PATH)
    registry, registry_error = _load_json(repo_root / _REGISTRY_PATH)

    for rel_path, error, summary in (
        (_STANDARD_PATH, std_error, "std_microcosm.json is missing or unreadable."),
        (
            _STANDARD_TYPE_PLANE_PATH,
            type_plane_error,
            "std_standard_type_plane.json is missing or unreadable.",
        ),
        (_ENTRY_PACKET_PATH, entry_error, "Microcosm entry packet is missing or unreadable."),
        (_REGISTRY_PATH, registry_error, "Microcosm standards registry is missing or unreadable."),
    ):
        check_count += 1
        if error:
            findings_out.append(_finding(
                validated_at=validated_at,
                finding_kind="broken_ref" if error == "missing" else "parse_error",
                severity="error",
                artifact_path=rel_path,
                scope_kind="artifact",
                scope_id=rel_path,
                summary=summary,
                evidence_refs=[rel_path, _STANDARD_PATH],
                candidate_target_paths=[rel_path],
                candidate_target_payload={"error": error},
                mutation_class="fix_broken_ref",
            ))

    for count, findings in (
        _scan_doctrine_lattice(
            repo_root,
            std_microcosm=std_microcosm,
            entry_packet=entry_packet,
            validated_at=validated_at,
        ),
        _scan_source_surfaces(
            repo_root,
            std_microcosm=std_microcosm,
            validated_at=validated_at,
        ),
        _scan_first_screen_navigation_contract(
            repo_root,
            std_microcosm=std_microcosm,
            entry_packet=entry_packet,
            validated_at=validated_at,
        ),
        _scan_paper_module_coverage_contract(
            repo_root,
            std_microcosm=std_microcosm,
            standard_type_plane=standard_type_plane,
            validated_at=validated_at,
        ),
        _scan_registry(repo_root, registry=registry, validated_at=validated_at),
        _scan_standards_meta_lane(repo_root, validated_at=validated_at),
    ):
        check_count += count
        findings_out.extend(findings)

    failure_counts = Counter(str(f.get("finding_kind") or "") for f in findings_out)
    top_failure_kinds = [
        {"finding_kind": kind, "count": count}
        for kind, count in sorted(failure_counts.items(), key=lambda item: (-item[1], item[0]))
    ][:8]
    noncompliant = len(findings_out)
    checked = max(1, check_count)
    compliant = max(0, checked - noncompliant)
    compliance_rate = float(compliant) / float(checked)

    return {
        "standard_id": _STANDARD_ID,
        "validator": _VALIDATOR,
        "validated_at": validated_at,
        "applicable_artifact_count": checked,
        "checked_artifact_count": checked,
        "compliant_artifact_count": compliant,
        "noncompliant_artifact_count": noncompliant,
        "compliance_rate": compliance_rate,
        "top_failure_kinds": top_failure_kinds,
        "findings": findings_out,
        "evidence_refs": [
            _STANDARD_PATH,
            _STANDARD_TYPE_PLANE_PATH,
            _ENTRY_PACKET_PATH,
            _REGISTRY_PATH,
            _STANDARDS_META_STANDARD_PATH,
            _COMPLIANCE_COVERAGE_STANDARD,
            _COMPLIANCE_FINDING_STANDARD,
        ],
        "metabolism_trigger_state": "scanner_partial" if findings_out else "ready_compliant",
        "specialization_of": "std_compliance_coverage",
        "coverage_path": _LEDGER_COVERAGE_PATH,
        "microcosm_status": {
            "entry_packet_exists": entry_packet is not None,
            "standards_registry_exists": registry is not None,
            "standard_type_plane_exists": standard_type_plane is not None,
            "parity_field_count": len(_PARITY_FIELDS),
            "paper_module_depth_step_count": len(_PAPER_MODULE_COVERAGE_DEPTH_STEPS),
            "standards_meta_lane": {
                "standard_exists": _path_exists(repo_root, _STANDARDS_META_STANDARD_PATH),
                "organ_exists": _path_exists(repo_root, _STANDARDS_META_ORGAN_PATH),
                "test_exists": _path_exists(repo_root, _STANDARDS_META_TEST_PATH),
            },
        },
        "navigation_role": (
            "Validates Microcosm product authority, public entry parity, "
            "paper-module coverage depth, public-export type-plane bridge, and "
            "standards-meta diagnostics through the shared compliance ledger."
        ),
        "notes": (
            "Scans Microcosm doctrine-lattice parity, current source-surface "
            "resolution, first-screen navigation parity, paper-module coverage "
            "contract health, public-export type-plane bridge health, native standards "
            "registry coverage, and standards-meta diagnostics lane presence. "
            "The row is navigation evidence, not public release, "
            "system_microcosm authority, or product readiness."
        ),
    }
