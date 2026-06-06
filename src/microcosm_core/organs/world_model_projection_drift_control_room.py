from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "world_model_projection_drift_control_room"
FIXTURE_ID = "first_wave.world_model_projection_drift_control_room"
VALIDATOR_ID = "validator.microcosm.organs.world_model_projection_drift_control_room"

RESULT_NAME = "world_model_projection_drift_control_room_result.json"
BOARD_NAME = "world_model_projection_drift_control_room_board.json"
VALIDATION_RECEIPT_NAME = "world_model_projection_drift_control_room_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "world_model_projection_drift_control_room_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_projection_drift_control_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "world_model_projection_drift_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "drift_rows",
    "projection_recompute",
    "supplied_drift_rows_snapshot",
    "view_quality_geometry_grade",
    "positive_findings",
    "negative_case_findings",
    "authority_ceiling",
    "anti_claim",
    "safe_to_show",
    "secret_exclusion_scan",
    "drift_control_board",
)

INPUT_NAMES = (
    "projection_protocol.json",
    "drift_policy.json",
    "drift_rows.json",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
VIEW_QUALITY_GEOMETRY_PROBE_NAME = "view_quality_geometry_probe.json"
NEGATIVE_INPUT_NAMES = (
    "drift_row_without_source_ref.json",
    "repair_route_without_validation_ref.json",
    "drift_row_without_fact_authority.json",
    "projection_claiming_source_authority.json",
    "live_repair_action_authorized.json",
    "private_runtime_data_export.json",
    "provider_payload_export.json",
    "automatic_doctrine_promotion.json",
    "release_from_drift_projection.json",
)

EXPECTED_NEGATIVE_CASES = {
    "drift_row_without_source_ref": ["DRIFT_SOURCE_REF_REQUIRED"],
    "repair_route_without_validation_ref": ["DRIFT_VALIDATION_REF_REQUIRED"],
    "drift_row_without_fact_authority": ["DRIFT_FACT_AUTHORITY_REQUIRED"],
    "projection_claiming_source_authority": ["DRIFT_SOURCE_AUTHORITY_FORBIDDEN"],
    "live_repair_action_authorized": ["DRIFT_LIVE_REPAIR_FORBIDDEN"],
    "private_runtime_data_export": ["DRIFT_PRIVATE_RUNTIME_EXPORT_FORBIDDEN"],
    "provider_payload_export": ["DRIFT_PROVIDER_PAYLOAD_FORBIDDEN"],
    "automatic_doctrine_promotion": ["DRIFT_AUTOMATIC_DOCTRINE_PROMOTION_FORBIDDEN"],
    "release_from_drift_projection": ["DRIFT_RELEASE_AUTHORITY_FORBIDDEN"],
}

REQUIRED_ROW_FIELDS = (
    "drift_row_id",
    "source_signal",
    "source_ref",
    "repair_route",
    "validation_ref",
    "target_ref",
    "body_in_receipt",
    "source_authority_claim",
    "live_repair_authorized",
    "source_mutation_authorized",
    "automatic_doctrine_promotion_authorized",
)
FACT_AUTHORITY_REQUIRED_FIELDS = (
    "authority_ref",
    "appearance_refs",
    "derivation_path",
    "guard_ref",
    "treatment",
    "residual_route",
)
ALLOWED_FACT_AUTHORITY_TREATMENTS = {
    "guarded_public_projection",
    "curated_exception",
}
PRIVATE_NEEDLES = (
    "/Users/",
    "src/ai_workflow",
    "Library/Application Support/Google",
    "sk-",
    "private_runtime_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_projection_drift_control_runtime_receipt_only",
    "public_runtime_receipt_required": True,
    "release_authorized": False,
    "hosted_public_authorized": False,
    "publication_authorized": False,
    "provider_calls_authorized": False,
    "provider_payload_exported": False,
    "source_authority_claim": False,
    "source_mutation_authorized": False,
    "live_route_repair_authorized": False,
    "live_task_ledger_mutation_authorized": False,
    "private_runtime_data_exported": False,
    "proof_body_exported": False,
    "automatic_doctrine_promotion_authorized": False,
}
ANTI_CLAIM = (
    "World-model projection drift control validates public body-free runtime "
    "receipt rows that name source signals, target refs, repair routes, "
    "validation refs, and live-access exclusion boundaries. It does not inspect "
    "private runtime bodies, repair live routes, mutate source, promote doctrine, "
    "export provider payloads, claim source authority, or authorize release."
)
BODY_IMPORT_STATUS = "real_runtime_receipt_landed"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_macro_body_landed"
SOURCE_BODY_STATUS = SOURCE_MODULE_IMPORT_STATUS
SOURCE_OPEN_BODY_SCHEMA = (
    "world_model_projection_drift_control_room_source_open_body_imports_v1"
)
SOURCE_REFS = [
    "microcosm-substrate/receipts/runtime_shell/public_projection_drift_control_lens.json",
    "microcosm-substrate/receipts/runtime_shell/public_view_quality_action_map_lens.json",
    "microcosm-substrate/receipts/runtime_shell/public_projection_safety_audit_lens.json",
    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
]
SUPPORTED_DRIFT_SOURCE_REFS = {
    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::world_model_projection_drift_control_room": {
        "evidence_kind": "portfolio_pattern_row",
        "artifact_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
    },
    "microcosm view-quality::action_rows": {
        "evidence_kind": "public_runtime_projection_alias",
        "artifact_ref": "receipts/runtime_shell/public_view_quality_action_map_lens.json",
    },
    "codex/standards/std_command_output_projection.json": {
        "evidence_kind": "standard_source_ref",
        "artifact_ref": "codex/standards/std_command_output_projection.json",
    },
    "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_plane.json": {
        "evidence_kind": "exported_route_plane_ref",
        "artifact_ref": "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_plane.json",
    },
    "codex/standards/std_task_ledger.json::quick_capture_contract": {
        "evidence_kind": "standard_fragment_source_ref",
        "artifact_ref": "codex/standards/std_task_ledger.json",
    },
    "state/meta_missions/type_a_autonomous_seed_loop/seeds/microcosm_substrate_import_autonomous_seed.json": {
        "evidence_kind": "autonomous_seed_source_ref",
        "artifact_ref": "state/meta_missions/type_a_autonomous_seed_loop/seeds/microcosm_substrate_import_autonomous_seed.json",
    },
    "microcosm projection-safety::projection_rows": {
        "evidence_kind": "public_runtime_projection_alias",
        "artifact_ref": "receipts/runtime_shell/public_projection_safety_audit_lens.json",
    },
    "kernel.py --entry::task_conditioned_context_pack_entry": {
        "evidence_kind": "kernel_entry_surface_ref",
        "artifact_ref": "kernel.py",
    },
}
SUPPORTED_SOURCE_MODULE_SOURCE_REFS = {
    "system/server/world_model.py",
    "system/server/main.py",
    "tools/meta/observability/view_quality_census.py",
    "system/server/tests/test_view_quality_census.py",
}
RUNTIME_DRIFT_RECEIPT_REFS = (
    "receipts/runtime_shell/public_projection_drift_control_lens.json",
)
SOURCE_STATE_DIFF_ARTIFACT_REFS = {
    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
    "receipts/runtime_shell/public_view_quality_action_map_lens.json",
}
TARGET_REFS = [
    "microcosm-substrate/src/microcosm_core/organs/world_model_projection_drift_control_room.py",
    "microcosm-substrate/fixtures/first_wave/world_model_projection_drift_control_room/input/drift_rows.json",
    "microcosm-substrate/examples/world_model_projection_drift_control_room/exported_projection_drift_control_bundle/drift_rows.json",
]
VALIDATION_REFS = [
    "microcosm-substrate/tests/test_world_model_projection_drift_control_room.py::test_world_model_projection_drift_exported_bundle_validates_runtime_shape",
    "microcosm-substrate/tests/test_world_model_projection_drift_control_room.py::test_world_model_projection_drift_receipts_consume_public_runtime_refs",
]
BODY_IMPORT_VERIFICATION = {
    "status": PASS,
    "classification": "real_runtime_receipt",
    "body_import_status": BODY_IMPORT_STATUS,
    "source_refs": SOURCE_REFS,
    "target_refs": TARGET_REFS,
    "validation_refs": VALIDATION_REFS,
    "body_in_receipt": False,
    "secret_exclusion_policy": (
        "exclude only credential/account/session/provider/live-access material "
        "and private runtime bodies"
    ),
}


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _sha256_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _source_module_manifest_path(input_dir: Path) -> Path:
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    target_ref: str,
    *,
    input_dir: Path,
    public_root: Path,
) -> Path:
    normalized = target_ref.removeprefix("microcosm-substrate/")
    if normalized.startswith("source_modules/"):
        return input_dir / normalized
    return public_root / normalized


def _source_module_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    try:
        manifest = read_json_strict(manifest_path)
    except Exception:
        return [manifest_path]
    paths = [manifest_path]
    for row in _rows(manifest, "modules"):
        target_ref = str(row.get("target_ref") or "")
        if target_ref:
            paths.append(
                _source_module_target_path(
                    target_ref,
                    input_dir=input_dir,
                    public_root=public_root,
                )
            )
    return paths


def _runtime_receipt_paths(public_root: Path) -> list[Path]:
    return [public_root / ref for ref in RUNTIME_DRIFT_RECEIPT_REFS]


def _source_artifact_paths(public_root: Path) -> list[Path]:
    refs = {
        str(evidence.get("artifact_ref") or "")
        for evidence in SUPPORTED_DRIFT_SOURCE_REFS.values()
    }
    return [
        _resolve_source_artifact_path(ref, public_root=public_root)
        for ref in sorted(refs)
        if ref
    ]


def _runtime_receipt_witness_result(
    drift_rows: list[dict[str, Any]],
    *,
    public_root: Path,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    receipt_row_ids: set[str] = set()
    receipt_refs: list[str] = []
    missing_receipt_refs: list[str] = []
    invalid_receipt_refs: list[str] = []

    for receipt_path in _runtime_receipt_paths(public_root):
        receipt_ref = _display(receipt_path, public_root=public_root)
        receipt_refs.append(receipt_ref)
        if not receipt_path.is_file():
            missing_receipt_refs.append(receipt_ref)
            findings.append(
                _finding(
                    "DRIFT_RUNTIME_RECEIPT_MISSING",
                    "drift rows must be witnessed by the public runtime drift-control lens receipt",
                    case_id="runtime_receipt_witness",
                    subject_id=receipt_ref,
                    subject_kind="runtime_receipt",
                )
            )
            continue
        try:
            payload = read_json_strict(receipt_path)
        except Exception:
            invalid_receipt_refs.append(receipt_ref)
            findings.append(
                _finding(
                    "DRIFT_RUNTIME_RECEIPT_INVALID",
                    "runtime drift-control lens receipt must be valid JSON",
                    case_id="runtime_receipt_witness",
                    subject_id=receipt_ref,
                    subject_kind="runtime_receipt",
                )
            )
            continue
        rows = _rows(payload, "drift_rows")
        if not rows:
            invalid_receipt_refs.append(receipt_ref)
            findings.append(
                _finding(
                    "DRIFT_RUNTIME_RECEIPT_ROWS_REQUIRED",
                    "runtime drift-control lens receipt must carry public drift rows",
                    case_id="runtime_receipt_witness",
                    subject_id=receipt_ref,
                    subject_kind="runtime_receipt",
                )
            )
        for row in rows:
            row_id = row.get("drift_row_id")
            if isinstance(row_id, str) and row_id:
                receipt_row_ids.add(row_id)

    drift_row_ids = [
        str(row.get("drift_row_id"))
        for row in drift_rows
        if isinstance(row.get("drift_row_id"), str) and row.get("drift_row_id")
    ]
    missing_row_ids = sorted(set(drift_row_ids) - receipt_row_ids)
    for row_id in missing_row_ids:
        findings.append(
            _finding(
                "DRIFT_RUNTIME_RECEIPT_ROW_MISSING",
                "drift row is not witnessed by the public runtime drift-control lens receipt",
                case_id="runtime_receipt_witness",
                subject_id=row_id,
                subject_kind="drift_row",
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "runtime_receipt_refs": receipt_refs,
        "missing_runtime_receipt_refs": missing_receipt_refs,
        "invalid_runtime_receipt_refs": invalid_receipt_refs,
        "runtime_receipt_row_count": len(receipt_row_ids),
        "witnessed_drift_row_count": len(set(drift_row_ids) & receipt_row_ids),
        "missing_drift_row_ids": missing_row_ids,
        "body_in_receipt": False,
        "findings": findings,
    }


def _derive_drift_row_from_projection(
    row: dict[str, Any],
    *,
    receipt_ref: str,
) -> dict[str, Any]:
    row_id = str(row.get("drift_row_id") or "")
    source_ref = str(row.get("source_ref") or "")
    repair_route = str(row.get("repair_route") or "")
    validation_ref = str(row.get("validation_ref") or "")
    target_ref = str(
        row.get("target_ref")
        or row.get("public_drilldown_ref")
        or f"{receipt_ref}::drift_rows[{row_id}]"
    )
    return {
        "drift_row_id": row_id,
        "source_signal": str(row.get("source_signal") or ""),
        "source_ref": source_ref,
        "repair_route": repair_route,
        "validation_ref": validation_ref,
        "target_ref": target_ref,
        "body_in_receipt": False,
        "source_authority_claim": row.get("source_authority_claim") is True,
        "live_repair_authorized": row.get("live_repair_authorized") is True,
        "source_mutation_authorized": row.get("source_mutation_authorized") is True,
        "automatic_doctrine_promotion_authorized": (
            row.get("automatic_doctrine_promotion_authorized") is True
        ),
        "release_authorized": row.get("release_authorized") is True,
        "fact_authority": {
            "authority_ref": source_ref,
            "appearance_refs": [
                ref for ref in (target_ref, validation_ref) if ref
            ],
            "derivation_path": [
                "projection_protocol.selected_pattern_ids",
                f"{receipt_ref}::drift_rows",
                "source_ref",
                "source_signal",
                "repair_route",
                "target_ref",
                "validation_ref",
            ],
            "guard_ref": validation_ref,
            "treatment": "guarded_public_projection",
            "residual_route": repair_route,
        },
    }


def _projection_recompute_result(
    projection_protocol: dict[str, Any],
    *,
    public_root: Path,
) -> dict[str, Any]:
    selected_ids = _strings(projection_protocol.get("selected_pattern_ids"))
    findings: list[dict[str, Any]] = []
    receipt_rows: dict[str, dict[str, Any]] = {}
    row_receipt_refs: dict[str, str] = {}
    runtime_receipt_refs: list[str] = []

    for receipt_path in _runtime_receipt_paths(public_root):
        receipt_ref = _display(receipt_path, public_root=public_root)
        runtime_receipt_refs.append(receipt_ref)
        if not receipt_path.is_file():
            findings.append(
                _finding(
                    "DRIFT_RUNTIME_RECEIPT_MISSING",
                    "public runtime drift-control receipt is required for recompute",
                    case_id="projection_recompute",
                    subject_id=receipt_ref,
                    subject_kind="runtime_receipt",
                )
            )
            continue
        try:
            payload = read_json_strict(receipt_path)
        except Exception:
            findings.append(
                _finding(
                    "DRIFT_RUNTIME_RECEIPT_INVALID",
                    "public runtime drift-control receipt must be valid JSON",
                    case_id="projection_recompute",
                    subject_id=receipt_ref,
                    subject_kind="runtime_receipt",
                )
            )
            continue
        for row in _rows(payload, "drift_rows"):
            row_id = row.get("drift_row_id")
            if isinstance(row_id, str) and row_id:
                receipt_rows[row_id] = row
                row_receipt_refs[row_id] = receipt_ref

    if not selected_ids:
        findings.append(
            _finding(
                "DRIFT_SELECTED_PATTERN_IDS_REQUIRED",
                "projection protocol must select drift row ids for recompute",
                case_id="projection_recompute",
                subject_id="projection_protocol.selected_pattern_ids",
                subject_kind="projection_protocol",
            )
        )
    derived_rows: list[dict[str, Any]] = []
    missing_ids: list[str] = []
    for row_id in selected_ids:
        receipt_row = receipt_rows.get(row_id)
        if not receipt_row:
            missing_ids.append(row_id)
            findings.append(
                _finding(
                    "DRIFT_SOURCE_PROJECTION_ROW_MISSING",
                    "selected drift row id is absent from the public runtime receipt",
                    case_id="projection_recompute",
                    subject_id=row_id,
                    subject_kind="drift_row",
                )
            )
            continue
        derived_rows.append(
            _derive_drift_row_from_projection(
                receipt_row,
                receipt_ref=row_receipt_refs.get(row_id, runtime_receipt_refs[0]),
            )
        )

    digest = hashlib.sha256(
        json.dumps(
            {
                "selected_pattern_ids": selected_ids,
                "runtime_receipt_refs": runtime_receipt_refs,
                "drift_rows": derived_rows,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "world_model_projection_drift_recompute_result_v1",
        "status": PASS if derived_rows and not findings else "blocked",
        "basis": "projection_protocol.selected_pattern_ids + public_runtime_receipt.drift_rows",
        "runtime_receipt_refs": runtime_receipt_refs,
        "selected_pattern_ids": selected_ids,
        "derived_row_count": len(derived_rows),
        "missing_selected_pattern_ids": missing_ids,
        "recompute_digest": f"sha256:{digest}",
        "drift_rows": derived_rows,
        "findings": findings,
    }


def _supplied_drift_rows_snapshot_result(
    supplied_payload: object,
    derived_rows: list[dict[str, Any]],
    projection_recompute: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    supplied_rows = _rows(supplied_payload, "drift_rows")
    supplied_by_id = {
        str(row.get("drift_row_id")): row
        for row in supplied_rows
        if isinstance(row.get("drift_row_id"), str)
    }
    derived_by_id = {
        str(row.get("drift_row_id")): row
        for row in derived_rows
        if isinstance(row.get("drift_row_id"), str)
    }
    supplied_ids = list(supplied_by_id)
    derived_ids = list(derived_by_id)
    missing_ids = [row_id for row_id in derived_ids if row_id not in supplied_by_id]
    extra_ids = [row_id for row_id in supplied_ids if row_id not in derived_by_id]
    changed_ids = [
        row_id
        for row_id in derived_ids
        if row_id in supplied_by_id and supplied_by_id[row_id] != derived_by_id[row_id]
    ]
    if supplied_ids != derived_ids or missing_ids or extra_ids or changed_ids:
        findings.append(
            {
                **_finding(
                    "DRIFT_SUPPLIED_ROW_SNAPSHOT_MISMATCH",
                    "supplied drift_rows.json is stale against recomputed public projection rows",
                    case_id="supplied_drift_rows_snapshot",
                    subject_id="drift_rows.json",
                    subject_kind="expected_snapshot",
                ),
                "missing_drift_row_ids": missing_ids,
                "extra_drift_row_ids": extra_ids,
                "changed_drift_row_ids": changed_ids,
            }
        )
    metadata_mismatch_fields: list[str] = []
    if not isinstance(supplied_payload, dict):
        metadata_mismatch_fields.append("drift_rows_payload")
    else:
        expected_metadata = {
            "generation_basis": projection_recompute.get("basis"),
            "drift_rows_count": len(derived_rows),
            "recompute_digest": projection_recompute.get("recompute_digest"),
        }
        for field, expected in expected_metadata.items():
            if supplied_payload.get(field) != expected:
                metadata_mismatch_fields.append(field)
        if metadata_mismatch_fields:
            findings.append(
                {
                    **_finding(
                        "DRIFT_SUPPLIED_ROW_METADATA_MISMATCH",
                        "supplied drift_rows.json metadata must match recomputed public projection rows",
                        case_id="supplied_drift_rows_snapshot",
                        subject_id="drift_rows.json",
                        subject_kind="expected_snapshot",
                    ),
                    "metadata_mismatch_fields": metadata_mismatch_fields,
                }
            )
    return {
        "schema_version": "world_model_projection_drift_supplied_snapshot_result_v1",
        "status": PASS if supplied_rows and not findings else "blocked",
        "role": "expected_snapshot_not_source_authority",
        "supplied_row_count": len(supplied_rows),
        "derived_row_count": len(derived_rows),
        "missing_drift_row_ids": missing_ids,
        "extra_drift_row_ids": extra_ids,
        "changed_drift_row_ids": changed_ids,
        "metadata_mismatch_fields": metadata_mismatch_fields,
        "findings": findings,
    }


def _source_ref_evidence_result(
    drift_rows: list[dict[str, Any]],
    *,
    public_root: Path,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    for row in drift_rows:
        row_id = str(row.get("drift_row_id") or "drift_row")
        source_ref = str(row.get("source_ref") or "")
        evidence = SUPPORTED_DRIFT_SOURCE_REFS.get(source_ref)
        if not evidence:
            findings.append(
                _finding(
                    "DRIFT_SOURCE_REF_UNSUPPORTED",
                    "drift row source_ref must resolve to a supported source artifact or public projection alias",
                    case_id="source_ref_evidence",
                    subject_id=row_id,
                    subject_kind="drift_row",
                )
            )
            continue
        artifact_ref = str(evidence.get("artifact_ref") or "")
        artifact_path = _resolve_source_artifact_path(
            artifact_ref,
            public_root=public_root,
        )
        evidence_rows.append(
            {
                "drift_row_id": row_id,
                "source_ref": source_ref,
                "evidence_kind": evidence.get("evidence_kind"),
                "artifact_ref": artifact_ref,
                "artifact_present_in_public_root": artifact_path.is_file(),
            }
        )
    return {
        "schema_version": "world_model_projection_drift_source_ref_evidence_v1",
        "status": PASS if drift_rows and not findings else "blocked",
        "supported_source_ref_count": len(SUPPORTED_DRIFT_SOURCE_REFS),
        "validated_source_ref_count": len(evidence_rows),
        "unsupported_source_ref_count": len(findings),
        "evidence_rows": evidence_rows,
        "findings": findings,
    }


def _source_root_for_public_root(public_root: Path) -> Path:
    if public_root.name == "microcosm-substrate":
        return public_root.parent
    return public_root


def _resolve_source_artifact_path(artifact_ref: str, *, public_root: Path) -> Path:
    source_root = _source_root_for_public_root(public_root)
    if artifact_ref.startswith(("receipts/", "examples/", "fixtures/", "core/")):
        return public_root / artifact_ref
    return source_root / artifact_ref


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _source_state_diff_result(
    drift_rows: list[dict[str, Any]],
    *,
    public_root: Path,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []

    for row in drift_rows:
        row_id = str(row.get("drift_row_id") or "drift_row")
        source_ref = str(row.get("source_ref") or "")
        evidence = SUPPORTED_DRIFT_SOURCE_REFS.get(source_ref)
        if not evidence:
            continue
        artifact_ref = str(evidence.get("artifact_ref") or "")
        if artifact_ref not in SOURCE_STATE_DIFF_ARTIFACT_REFS:
            continue
        artifact_path = _resolve_source_artifact_path(
            artifact_ref,
            public_root=public_root,
        )
        if not artifact_path.is_file():
            findings.append(
                _finding(
                    "DRIFT_SOURCE_ARTIFACT_MISSING",
                    "recomputed projection row must resolve to a real source-state artifact",
                    case_id="source_state_diff",
                    subject_id=source_ref,
                    subject_kind="source_ref",
                )
            )
            continue

        if artifact_ref == "receipts/runtime_shell/public_view_quality_action_map_lens.json":
            try:
                action_map = read_json_strict(artifact_path)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                findings.append(
                    _finding(
                        "DRIFT_SOURCE_ARTIFACT_INVALID",
                        "view-quality action-map source artifact must be readable JSON",
                        case_id="source_state_diff",
                        subject_id=source_ref,
                        subject_kind="source_ref",
                    )
                )
                continue

            action_rows = _rows(action_map, "action_rows")
            hot_actions = _rows(action_map, "hot_action_rollup")
            action_summary = (
                action_map.get("action_summary")
                if isinstance(action_map, dict)
                else None
            )
            source_projection_refs = (
                _strings(action_map.get("source_projection_refs"))
                if isinstance(action_map, dict)
                else []
            )
            expected_ledger_ref = (
                "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                f"{row_id}"
            )
            if not action_rows:
                findings.append(
                    _finding(
                        "DRIFT_VIEW_QUALITY_ACTION_ROWS_REQUIRED",
                        "view-quality source artifact must carry action rows",
                        case_id="source_state_diff",
                        subject_id=row_id,
                        subject_kind="source_artifact",
                    )
                )
            if not isinstance(action_summary, dict):
                findings.append(
                    _finding(
                        "DRIFT_VIEW_QUALITY_ACTION_SUMMARY_REQUIRED",
                        "view-quality source artifact must carry action summary",
                        case_id="source_state_diff",
                        subject_id=row_id,
                        subject_kind="source_artifact",
                    )
                )
            else:
                expected_counts = {
                    "action_row_count": len(action_rows),
                    "hot_action_count": len(hot_actions),
                    "live_browser_control_authorized_count": sum(
                        1
                        for action in action_rows
                        if action.get("live_browser_control_authorized") is True
                    ),
                    "private_screenshot_path_export_count": sum(
                        1
                        for action in action_rows
                        if action.get("private_screenshot_path_exported") is True
                    ),
                }
                for field, expected in expected_counts.items():
                    if action_summary.get(field) != expected:
                        findings.append(
                            {
                                **_finding(
                                    "DRIFT_VIEW_QUALITY_ACTION_SUMMARY_MISMATCH",
                                    "view-quality action summary must be recomputed from action rows",
                                    case_id="source_state_diff",
                                    subject_id=row_id,
                                    subject_kind="source_artifact",
                                ),
                                "field": field,
                                "expected": expected,
                                "actual": action_summary.get(field),
                            }
                        )
            if action_map.get("selected_pattern_id") != row_id:
                findings.append(
                    _finding(
                        "DRIFT_VIEW_QUALITY_SELECTED_PATTERN_MISMATCH",
                        "view-quality source artifact selected_pattern_id must match the drift row id",
                        case_id="source_state_diff",
                        subject_id=row_id,
                        subject_kind="source_artifact",
                    )
                )
            if expected_ledger_ref not in source_projection_refs:
                findings.append(
                    _finding(
                        "DRIFT_VIEW_QUALITY_SOURCE_LEDGER_REF_MISSING",
                        "view-quality source artifact must cite the extracted-pattern source ledger row",
                        case_id="source_state_diff",
                        subject_id=row_id,
                        subject_kind="source_artifact",
                    )
                )
            source_digest = hashlib.sha256(
                json.dumps(action_map, sort_keys=True).encode("utf-8")
            ).hexdigest()
            projection_digest = hashlib.sha256(
                json.dumps(row, sort_keys=True).encode("utf-8")
            ).hexdigest()
            evidence_rows.append(
                {
                    "drift_row_id": row_id,
                    "source_ref": source_ref,
                    "source_artifact_ref": artifact_ref,
                    "source_pattern_id": str(action_map.get("selected_pattern_id") or ""),
                    "source_ref_count": len(source_projection_refs),
                    "source_digest": f"sha256:{source_digest}",
                    "projection_row_digest": f"sha256:{projection_digest}",
                    "source_check": "view_quality_action_map_summary_diff",
                }
            )
            continue

        if artifact_ref != "state/microcosm_portfolio/extracted_patterns_ledger.jsonl":
            continue

        try:
            ledger_rows = _load_jsonl_rows(artifact_path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            findings.append(
                _finding(
                    "DRIFT_SOURCE_ARTIFACT_INVALID",
                    "extracted-pattern source ledger must be readable JSONL",
                    case_id="source_state_diff",
                    subject_id=source_ref,
                    subject_kind="source_ref",
                )
            )
            continue

        source_row = next(
            (
                ledger_row
                for ledger_row in ledger_rows
                if ledger_row.get("pattern_id") == row_id
            ),
            None,
        )
        if not source_row:
            findings.append(
                _finding(
                    "DRIFT_SOURCE_ROW_MISSING",
                    "recomputed projection row id must be present in the real extracted-pattern source ledger",
                    case_id="source_state_diff",
                    subject_id=row_id,
                    subject_kind="drift_row",
                )
            )
            continue

        source_refs = _strings(source_row.get("source_refs"))
        if not source_refs:
            findings.append(
                _finding(
                    "DRIFT_SOURCE_ROW_REFS_REQUIRED",
                    "source ledger row must retain concrete source_refs before projection drift can pass",
                    case_id="source_state_diff",
                    subject_id=row_id,
                    subject_kind="source_row",
                )
            )
        source_digest = hashlib.sha256(
            json.dumps(source_row, sort_keys=True).encode("utf-8")
        ).hexdigest()
        projection_digest = hashlib.sha256(
            json.dumps(row, sort_keys=True).encode("utf-8")
        ).hexdigest()
        evidence_rows.append(
            {
                "drift_row_id": row_id,
                "source_ref": source_ref,
                "source_artifact_ref": artifact_ref,
                "source_pattern_id": str(source_row.get("pattern_id") or ""),
                "source_ref_count": len(source_refs),
                "source_digest": f"sha256:{source_digest}",
                "projection_row_digest": f"sha256:{projection_digest}",
                "source_check": "extracted_pattern_ledger_row_diff",
            }
        )

    return {
        "schema_version": "world_model_projection_drift_source_state_diff_v1",
        "status": PASS if evidence_rows and not findings else "blocked",
        "basis": "recomputed_public_projection_rows + real_source_state_artifacts",
        "source_row_count": len(evidence_rows),
        "evidence_rows": evidence_rows,
        "findings": findings,
    }


def _source_module_manifest_result(input_dir: Path, *, public_root: Path) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return {
            "status": "not_present",
            "source_module_import_status": "not_present",
            "source_module_manifest_ref": None,
            "module_count": 0,
            "module_ids": [],
            "material_classes": [],
            "body_in_receipt": False,
            "findings": [],
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    module_ids: list[str] = []
    material_classes: set[str] = set()
    verified_count = 0
    for row in _rows(manifest, "modules"):
        module_id = str(row.get("module_id") or "source_module")
        module_ids.append(module_id)
        if row.get("material_class"):
            material_classes.add(str(row["material_class"]))
        source_ref = str(row.get("source_ref") or "")
        if source_ref not in SUPPORTED_SOURCE_MODULE_SOURCE_REFS:
            findings.append(
                _finding(
                    "DRIFT_SOURCE_MODULE_SOURCE_REF_UNSUPPORTED",
                    "source module source_ref must name a supported copied macro source body",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        target_ref = str(row.get("target_ref") or "")
        target = _source_module_target_path(
            target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "DRIFT_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "source module rows must copy body into the bundle while keeping receipts body-free",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not target.is_file():
            findings.append(
                _finding(
                    "DRIFT_SOURCE_MODULE_TARGET_MISSING",
                    "source module target must exist inside the public Microcosm bundle",
                    case_id="source_module_manifest",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256_digest(target)
        expected = f"sha256:{row.get('source_sha256') or ''}"
        target_expected = f"sha256:{row.get('target_sha256') or ''}"
        if actual != expected or actual != target_expected:
            findings.append(
                _finding(
                    "DRIFT_SOURCE_MODULE_DIGEST_MISMATCH",
                    "source module digest declarations must match the copied target body",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        text = target.read_text(encoding="utf-8")
        missing_anchors = [
            anchor for anchor in _strings(row.get("required_anchors")) if anchor not in text
        ]
        if missing_anchors:
            findings.append(
                {
                    **_finding(
                        "DRIFT_SOURCE_MODULE_ANCHOR_MISSING",
                        "source module must carry the declared macro mechanism anchors",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    ),
                    "missing_anchors": missing_anchors,
                }
            )
        if not any(finding.get("subject_id") == module_id for finding in findings):
            verified_count += 1

    status = PASS if module_ids and not findings else "blocked"
    return {
        "status": status,
        "source_module_import_status": (
            SOURCE_MODULE_IMPORT_STATUS if status == PASS else "blocked"
        ),
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "module_count": len(module_ids),
        "verified_module_count": verified_count,
        "module_ids": module_ids,
        "material_classes": sorted(material_classes),
        "body_in_receipt": False,
        "findings": findings,
    }


def _view_quality_source_module_path(input_dir: Path, *, public_root: Path) -> Path | None:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return None
    try:
        manifest = read_json_strict(manifest_path)
    except Exception:
        return None
    for row in _rows(manifest, "modules"):
        if row.get("source_ref") != "tools/meta/observability/view_quality_census.py":
            continue
        target_ref = str(row.get("target_ref") or "")
        if not target_ref:
            return None
        return _source_module_target_path(
            target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
    return None


def _load_view_quality_source_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        "_microcosm_world_model_projection_drift_view_quality_census",
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not import copied view-quality source module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _view_quality_geometry_grade_result(
    input_dir: Path,
    *,
    public_root: Path,
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    probe_path = input_dir / VIEW_QUALITY_GEOMETRY_PROBE_NAME
    if not probe_path.is_file():
        return {
            "schema_version": "world_model_projection_drift_view_quality_geometry_grade_v1",
            "status": "not_present",
            "geometry_probe_ref": None,
            "source_module_ref": None,
            "body_in_receipt": False,
            "findings": [],
        }

    findings: list[dict[str, Any]] = []
    source_module_path = _view_quality_source_module_path(
        input_dir,
        public_root=public_root,
    )
    if source_module_result.get("status") != PASS or source_module_path is None:
        findings.append(
            _finding(
                "DRIFT_VIEW_QUALITY_SOURCE_MODULE_REQUIRED",
                "view-quality geometry grading requires the copied view_quality_census.py source module",
                case_id="view_quality_geometry_grade",
                subject_id="tools/meta/observability/view_quality_census.py",
                subject_kind="source_module",
            )
        )
        return {
            "schema_version": "world_model_projection_drift_view_quality_geometry_grade_v1",
            "status": "blocked",
            "geometry_probe_ref": _display(probe_path, public_root=public_root),
            "source_module_ref": None,
            "body_in_receipt": False,
            "findings": findings,
        }

    try:
        probe = read_json_strict(probe_path)
        module = _load_view_quality_source_module(source_module_path)
        geometry_summary = probe.get("geometry_summary") if isinstance(probe, dict) else None
        mode = str((probe or {}).get("mode") or "graph_first") if isinstance(probe, dict) else "graph_first"
        view_id = str((probe or {}).get("view_id") or "graph") if isinstance(probe, dict) else "graph"
        view_family = (
            str((probe or {}).get("view_family") or "graph_surface")
            if isinstance(probe, dict)
            else "graph_surface"
        )
        vector = module._geometry_vector_from_summary(geometry_summary, mode=mode)
        review = module._geometry_calibration_review(
            row={
                "view_id": view_id,
                "view_family": view_family,
                "mode": mode,
            },
            geometry_vector=vector,
            screenshot_ledger=probe.get("screenshot_ledger") if isinstance(probe, dict) else {},
        )
    except Exception as exc:
        findings.append(
            {
                **_finding(
                    "DRIFT_VIEW_QUALITY_GEOMETRY_GRADE_ERROR",
                    "view-quality geometry probe must be graded by the copied source module",
                    case_id="view_quality_geometry_grade",
                    subject_id=_display(probe_path, public_root=public_root),
                    subject_kind="geometry_probe",
                ),
                "exception_type": type(exc).__name__,
            }
        )
        return {
            "schema_version": "world_model_projection_drift_view_quality_geometry_grade_v1",
            "status": "blocked",
            "geometry_probe_ref": _display(probe_path, public_root=public_root),
            "source_module_ref": _display(source_module_path, public_root=public_root),
            "body_in_receipt": False,
            "findings": findings,
        }

    calibration_status = str((review or {}).get("status") or "")
    if calibration_status != "calibrated_pass":
        findings.append(
            {
                **_finding(
                    "DRIFT_VIEW_QUALITY_GEOMETRY_CALIBRATION_NOT_PASSING",
                    "view-quality geometry probe must remain a calibrated pass under the copied grader",
                    case_id="view_quality_geometry_grade",
                    subject_id=view_id,
                    subject_kind="geometry_probe",
                ),
                "calibration_status": calibration_status,
                "failed_gates": (review or {}).get("failed_gates", []),
                "watch_gates": (review or {}).get("watch_gates", []),
                "violations": (review or {}).get("violations", []),
            }
        )

    return {
        "schema_version": "world_model_projection_drift_view_quality_geometry_grade_v1",
        "status": PASS if review and not findings else "blocked",
        "geometry_probe_ref": _display(probe_path, public_root=public_root),
        "source_module_ref": _display(source_module_path, public_root=public_root),
        "basis": "view_quality_geometry_probe.json + copied view_quality_census.py geometry grader",
        "view_id": view_id,
        "view_family": view_family,
        "calibration_status": calibration_status,
        "hard_gates": (review or {}).get("hard_gates", {}),
        "failed_gates": (review or {}).get("failed_gates", []),
        "watch_gates": (review or {}).get("watch_gates", []),
        "violations": (review or {}).get("violations", []),
        "evidence": (review or {}).get("evidence", {}),
        "body_in_receipt": False,
        "findings": findings,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    module_ids = _strings(source_module_result.get("module_ids"))
    material_classes = _strings(source_module_result.get("material_classes"))
    manifest_ref = source_module_result.get("source_module_manifest_ref")
    imported = source_module_result.get("status") == PASS and bool(module_ids)
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": PASS if imported else str(source_module_result.get("status") or ""),
        "source_import_class": SOURCE_IMPORT_CLASS if imported else "",
        "body_material_status": SOURCE_BODY_STATUS if imported else "",
        "body_material_count": len(module_ids) if imported else 0,
        "body_material_ids": module_ids if imported else [],
        "material_classes": material_classes if imported else [],
        "source_manifest_refs": [str(manifest_ref)]
        if imported and manifest_ref
        else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules"
        if imported and manifest_ref
        else "",
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "live_git_mutation_authorized": False,
            "broad_checkpoint_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported projection drift control bundle for copied macro "
            "world-model and view-quality source bodies; receipts carry refs, "
            "digests, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    geometry_probe = input_dir / VIEW_QUALITY_GEOMETRY_PROBE_NAME
    if geometry_probe.is_file():
        paths.append(geometry_probe)
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _scan_paths_for_input(input_dir: Path, *, include_negative: bool) -> list[Path]:
    paths = list(_input_paths(input_dir, include_negative=include_negative))
    public_root = _public_root_for_path(input_dir)
    paths.extend(_source_module_paths(input_dir, public_root=public_root))
    paths.extend(path for path in _runtime_receipt_paths(public_root) if path.is_file())
    paths.extend(path for path in _source_artifact_paths(public_root) if path.is_file())
    return paths


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_scan_paths_for_input(source, include_negative=include_negative),
        Path(__file__).resolve(),
        public_root / "core/private_state_forbidden_classes.json",
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256_digest(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "world_model_projection_drift_control_room_result_v1"
        if include_negative
        else "exported_projection_drift_control_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": validator_schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "world_model_projection_drift_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_drift_control_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != (
        "exported_projection_drift_control_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_projection_drift_control_bundle":
        return None
    if payload.get("command") != command:
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    if case_id in EXPECTED_NEGATIVE_CASES:
        observed[case_id].add(code)


def _row_policy_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("drift_row_id") or case_id)
    for field in REQUIRED_ROW_FIELDS:
        if field not in row:
            code = "DRIFT_SOURCE_REF_REQUIRED" if field == "source_ref" else "DRIFT_ROW_FIELD_REQUIRED"
            _record(
                findings,
                observed,
                code,
                f"drift row is missing required field {field}",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="drift_row",
            )
    if not row.get("source_ref"):
        _record(
            findings,
            observed,
            "DRIFT_SOURCE_REF_REQUIRED",
            "drift rows must cite a public-safe source reference",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if not row.get("repair_route") or not row.get("validation_ref"):
        _record(
            findings,
            observed,
            "DRIFT_VALIDATION_REF_REQUIRED",
            "drift rows must cite both a repair route and a validation reference",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    bool_forbidden = {
        "source_authority_claim": "DRIFT_SOURCE_AUTHORITY_FORBIDDEN",
        "live_repair_authorized": "DRIFT_LIVE_REPAIR_FORBIDDEN",
        "source_mutation_authorized": "DRIFT_SOURCE_MUTATION_FORBIDDEN",
        "automatic_doctrine_promotion_authorized": "DRIFT_AUTOMATIC_DOCTRINE_PROMOTION_FORBIDDEN",
        "release_authorized": "DRIFT_RELEASE_AUTHORITY_FORBIDDEN",
    }
    for field, code in bool_forbidden.items():
        if row.get(field) is True:
            _record(
                findings,
                observed,
                code,
                f"{field} must be false for public projection drift rows",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="drift_row",
            )
    if not row.get("target_ref"):
        _record(
            findings,
            observed,
            "DRIFT_TARGET_REF_REQUIRED",
            "drift rows must cite a public runtime target reference",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if row.get("body_in_receipt") is not False:
        _record(
            findings,
            observed,
            "DRIFT_BODY_RECEIPT_BOUNDARY_REQUIRED",
            "drift rows must keep private/provider bodies out of public runtime receipts",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if row.get("private_runtime_data") or any(
        needle in json.dumps(row, sort_keys=True) for needle in PRIVATE_NEEDLES
    ):
        _record(
            findings,
            observed,
            "DRIFT_PRIVATE_RUNTIME_EXPORT_FORBIDDEN",
            "private runtime data cannot enter the public drift control room",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if row.get("provider_payload") or row.get("provider_payload_exported") is True:
        _record(
            findings,
            observed,
            "DRIFT_PROVIDER_PAYLOAD_FORBIDDEN",
            "provider payloads cannot enter the public drift control room",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    fact_authority = row.get("fact_authority")
    if not isinstance(fact_authority, dict):
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_REQUIRED",
            "drift rows must carry a fact-authority map entry",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
        return findings
    missing_fact_fields = [
        field for field in FACT_AUTHORITY_REQUIRED_FIELDS if field not in fact_authority
    ]
    if missing_fact_fields:
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_REQUIRED",
            "fact-authority map entries must name authority, appearances, derivation, guard, treatment, and residual route",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    authority_ref = fact_authority.get("authority_ref")
    if not authority_ref:
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_REF_REQUIRED",
            "fact-authority map entries must name the single live authority ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    elif row.get("source_ref") and authority_ref != row.get("source_ref"):
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_REF_MISMATCH",
            "fact-authority authority_ref must equal the row source_ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    appearance_refs = fact_authority.get("appearance_refs")
    if not isinstance(appearance_refs, list) or not all(
        isinstance(ref, str) and ref for ref in appearance_refs
    ):
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_APPEARANCE_REQUIRED",
            "fact-authority map entries must name public projection appearances",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    else:
        for expected_ref in (row.get("target_ref"), row.get("validation_ref")):
            if expected_ref and expected_ref not in appearance_refs:
                _record(
                    findings,
                    observed,
                    "DRIFT_FACT_AUTHORITY_APPEARANCE_MISSING",
                    "fact-authority appearances must include the row target and validation refs",
                    case_id=case_id,
                    subject_id=subject_id,
                    subject_kind="drift_row",
                )
    derivation_path = fact_authority.get("derivation_path")
    if not isinstance(derivation_path, list) or not all(
        isinstance(step, str) and step for step in derivation_path
    ):
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_DERIVATION_REQUIRED",
            "fact-authority map entries must name a derivation path",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    guard_ref = fact_authority.get("guard_ref")
    if not guard_ref:
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_GUARD_REQUIRED",
            "fact-authority map entries must name a divergence guard ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    elif row.get("validation_ref") and guard_ref != row.get("validation_ref"):
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_GUARD_MISMATCH",
            "fact-authority guard_ref must equal the row validation_ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if fact_authority.get("treatment") not in ALLOWED_FACT_AUTHORITY_TREATMENTS:
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_TREATMENT_REQUIRED",
            "fact-authority treatment must be a guarded projection or curated exception",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    residual_route = fact_authority.get("residual_route")
    if not residual_route:
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_RESIDUAL_ROUTE_REQUIRED",
            "fact-authority map entries must name the residual route",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    elif row.get("repair_route") and residual_route != row.get("repair_route"):
        _record(
            findings,
            observed,
            "DRIFT_FACT_AUTHORITY_RESIDUAL_ROUTE_MISMATCH",
            "fact-authority residual_route must equal the row repair_route",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    return findings


def _required_policy_ok(policy: dict[str, Any]) -> bool:
    ceiling = policy.get("authority_ceiling")
    if not isinstance(ceiling, dict):
        return False
    return (
        ceiling.get("public_runtime_receipt_required") is True
        and all(
            value is False
            for key, value in ceiling.items()
            if key != "public_runtime_receipt_required"
        )
    )


def _fact_authority_mesh_summary(drift_rows: list[dict[str, Any]]) -> dict[str, Any]:
    fact_rows = [
        row for row in drift_rows if isinstance(row.get("fact_authority"), dict)
    ]
    guarded_rows = [
        row
        for row in fact_rows
        if row["fact_authority"].get("treatment") == "guarded_public_projection"
    ]
    unguarded_count = len(drift_rows) - len(fact_rows)
    return {
        "schema_version": "world_model_projection_drift_fact_authority_mesh_v1",
        "status": PASS if drift_rows and unguarded_count == 0 else "blocked",
        "fact_authority_row_count": len(fact_rows),
        "guarded_projection_treatment_count": len(guarded_rows),
        "unguarded_duplicate_count": unguarded_count,
        "authority_ref_policy": "authority_ref_equals_source_ref",
        "appearance_ref_policy": "appearance_refs_include_target_and_validation_refs",
        "guard_ref_policy": "guard_ref_equals_validation_ref",
        "residual_route_policy": "residual_route_equals_repair_route",
        "allowed_treatments": sorted(ALLOWED_FACT_AUTHORITY_TREATMENTS),
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    public_root = _public_root_for_path(input_dir)
    projection_protocol = payloads.get("projection_protocol", {})
    drift_policy = payloads.get("drift_policy", {})
    supplied_drift_rows_payload = payloads.get("drift_rows", {})
    projection_recompute = _projection_recompute_result(
        projection_protocol if isinstance(projection_protocol, dict) else {},
        public_root=public_root,
    )
    drift_rows = _rows(projection_recompute, "drift_rows")
    supplied_snapshot = _supplied_drift_rows_snapshot_result(
        supplied_drift_rows_payload,
        drift_rows,
        projection_recompute,
    )
    source_ref_evidence = _source_ref_evidence_result(
        drift_rows,
        public_root=public_root,
    )
    source_state_diff = _source_state_diff_result(
        drift_rows,
        public_root=public_root,
    )
    source_module_result = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
    )
    source_open_body_imports = _source_open_body_import_summary(source_module_result)
    view_quality_geometry_grade = _view_quality_geometry_grade_result(
        input_dir,
        public_root=public_root,
        source_module_result=source_module_result,
    )
    runtime_receipt_witness = _runtime_receipt_witness_result(
        drift_rows,
        public_root=public_root,
    )
    observed_negative_codes: dict[str, set[str]] = defaultdict(set)
    positive_findings: list[dict[str, Any]] = []
    positive_findings.extend(projection_recompute["findings"])
    positive_findings.extend(supplied_snapshot["findings"])
    positive_findings.extend(source_ref_evidence["findings"])
    positive_findings.extend(source_state_diff["findings"])
    positive_findings.extend(view_quality_geometry_grade["findings"])
    positive_findings.extend(runtime_receipt_witness["findings"])

    if not isinstance(projection_protocol, dict) or projection_protocol.get("selected_route_id") != "world_model_projection_drift_control_room":
        positive_findings.append(
            _finding(
                "DRIFT_PROTOCOL_ROUTE_REQUIRED",
                "projection protocol must select world_model_projection_drift_control_room",
                case_id="positive_fixture",
                subject_id="projection_protocol",
                subject_kind="protocol",
            )
        )
    protocol_target_refs = _strings(projection_protocol.get("target_refs"))
    protocol_verification = projection_protocol.get("body_import_verification")
    if projection_protocol.get("body_import_status") != BODY_IMPORT_STATUS:
        positive_findings.append(
            _finding(
                "DRIFT_BODY_IMPORT_STATUS_REQUIRED",
                "projection protocol must declare the public runtime receipt import status",
                case_id="positive_fixture",
                subject_id="projection_protocol",
                subject_kind="protocol",
            )
        )
    if TARGET_REFS[0] not in protocol_target_refs:
        positive_findings.append(
            _finding(
                "DRIFT_TARGET_REF_REQUIRED",
                "projection protocol must cite the public drift-control organ target ref",
                case_id="positive_fixture",
                subject_id="projection_protocol",
                subject_kind="protocol",
            )
        )
    if (
        not isinstance(protocol_verification, dict)
        or protocol_verification.get("status") != PASS
        or protocol_verification.get("body_in_receipt") is not False
    ):
        positive_findings.append(
            _finding(
                "DRIFT_BODY_IMPORT_VERIFICATION_REQUIRED",
                "projection protocol must bind body-import verification for the runtime receipt",
                case_id="positive_fixture",
                subject_id="projection_protocol",
                subject_kind="protocol",
            )
        )
    if not _required_policy_ok(drift_policy if isinstance(drift_policy, dict) else {}):
        positive_findings.append(
            _finding(
                "DRIFT_AUTHORITY_CEILING_REQUIRED",
                "drift policy must declare public runtime receipt authority ceiling",
                case_id="positive_fixture",
                subject_id="drift_policy",
                subject_kind="policy",
            )
        )
    for row in drift_rows:
        row_findings = _row_policy_findings(
            row,
            case_id="positive_fixture",
            observed=observed_negative_codes,
        )
        positive_findings.extend(row_findings)
    selected_pattern_ids = _strings(projection_protocol.get("selected_pattern_ids"))
    row_ids = [str(row.get("drift_row_id")) for row in drift_rows if row.get("drift_row_id")]
    if selected_pattern_ids and selected_pattern_ids != row_ids:
        positive_findings.append(
            _finding(
                "DRIFT_SELECTED_PATTERN_IDS_MISMATCH",
                "selected_pattern_ids must exactly match validated drift row ids",
                case_id="positive_fixture",
                subject_id="projection_protocol",
                subject_kind="protocol",
            )
        )

    negative_findings: list[dict[str, Any]] = []
    if include_negative:
        for name in NEGATIVE_INPUT_NAMES:
            case_id = Path(name).stem
            payload = payloads.get(case_id, {})
            row_payload = payload.get("drift_row", payload) if isinstance(payload, dict) else {}
            if isinstance(row_payload, dict):
                negative_findings.extend(
                    _row_policy_findings(
                        row_payload,
                        case_id=case_id,
                        observed=observed_negative_codes,
                    )
                )

    expected_cases = EXPECTED_NEGATIVE_CASES if include_negative else {}
    expected_missing = {
        case_id: sorted(set(codes) - observed_negative_codes.get(case_id, set()))
        for case_id, codes in expected_cases.items()
    }
    expected_missing = {case_id: codes for case_id, codes in expected_missing.items() if codes}
    encoded_positive = json.dumps(drift_rows, sort_keys=True)
    body_free_public_rows = not any(needle in encoded_positive for needle in PRIVATE_NEEDLES)
    policy_passed = (
        bool(drift_rows)
        and not positive_findings
        and body_free_public_rows
        and not expected_missing
        and all(row.get("body_in_receipt") is False for row in drift_rows)
        and all(row.get("source_authority_claim") is False for row in drift_rows)
        and all(row.get("live_repair_authorized") is False for row in drift_rows)
        and all(row.get("source_mutation_authorized") is False for row in drift_rows)
        and all(
            row.get("automatic_doctrine_promotion_authorized") is False
            for row in drift_rows
        )
        and runtime_receipt_witness["status"] == PASS
        and projection_recompute["status"] == PASS
        and supplied_snapshot["status"] == PASS
        and source_ref_evidence["status"] == PASS
        and source_state_diff["status"] == PASS
        and source_module_result["status"] in {PASS, "not_present"}
        and view_quality_geometry_grade["status"] in {PASS, "not_present"}
    )

    scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    status = PASS if policy_passed and scan.get("status") == PASS else "blocked"
    fact_authority_mesh = _fact_authority_mesh_summary(drift_rows)
    return {
        "schema_version": "world_model_projection_drift_control_room_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "input_ref": _display(input_dir, public_root=public_root),
        "selected_route_id": "world_model_projection_drift_control_room",
        "selected_pattern_ids": row_ids,
        "drift_rows": drift_rows,
        "projection_recompute": projection_recompute,
        "supplied_drift_rows_snapshot": supplied_snapshot,
        "source_ref_evidence": source_ref_evidence,
        "source_state_diff": source_state_diff,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": source_module_result[
            "source_module_import_status"
        ],
        "source_module_manifest_ref": source_module_result[
            "source_module_manifest_ref"
        ],
        "source_module_summary": source_module_result,
        "source_open_body_imports": source_open_body_imports,
        "view_quality_geometry_grade": view_quality_geometry_grade,
        "runtime_receipt_witness": runtime_receipt_witness,
        "runtime_receipt_witness_status": runtime_receipt_witness["status"],
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "source_refs": SOURCE_REFS,
        "target_refs": TARGET_REFS,
        "drift_summary": {
            "row_count": len(drift_rows),
            "source_ref_count": sum(1 for row in drift_rows if row.get("source_ref")),
            "target_ref_count": sum(1 for row in drift_rows if row.get("target_ref")),
            "repair_route_count": sum(1 for row in drift_rows if row.get("repair_route")),
            "validation_ref_count": sum(1 for row in drift_rows if row.get("validation_ref")),
            "fact_authority_row_count": sum(
                1 for row in drift_rows if isinstance(row.get("fact_authority"), dict)
            ),
            "guarded_projection_treatment_count": sum(
                1
                for row in drift_rows
                if (row.get("fact_authority") or {}).get("treatment")
                == "guarded_public_projection"
            ),
            "unguarded_duplicate_count": sum(
                1 for row in drift_rows if not isinstance(row.get("fact_authority"), dict)
            ),
            "source_authority_claim_count": sum(1 for row in drift_rows if row.get("source_authority_claim") is True),
            "live_repair_authorized_count": sum(1 for row in drift_rows if row.get("live_repair_authorized") is True),
            "source_mutation_authorized_count": sum(1 for row in drift_rows if row.get("source_mutation_authorized") is True),
            "automatic_doctrine_promotion_count": sum(1 for row in drift_rows if row.get("automatic_doctrine_promotion_authorized") is True),
            "private_runtime_data_export_count": 0,
            "provider_payload_export_count": 0,
            "runtime_receipt_witnessed_row_count": runtime_receipt_witness[
                "witnessed_drift_row_count"
            ],
            "runtime_receipt_missing_row_count": len(
                runtime_receipt_witness["missing_drift_row_ids"]
            ),
            "source_ref_evidence_count": source_ref_evidence[
                "validated_source_ref_count"
            ],
            "source_state_diff_row_count": source_state_diff["source_row_count"],
            "unsupported_source_ref_count": source_ref_evidence[
                "unsupported_source_ref_count"
            ],
            "view_quality_geometry_status": view_quality_geometry_grade[
                "status"
            ],
            "view_quality_geometry_calibration_status": (
                view_quality_geometry_grade.get("calibration_status")
            ),
        },
        "fact_authority_mesh": fact_authority_mesh,
        "negative_case_summary": {
            "expected_negative_case_count": len(expected_cases),
            "observed_negative_case_count": sum(
                1 for case_id in expected_cases if observed_negative_codes.get(case_id)
            ),
            "expected_missing": expected_missing,
            "observed_codes": {
                case_id: sorted(codes)
                for case_id, codes in sorted(observed_negative_codes.items())
                if case_id in expected_cases
            },
        },
        "finding_count": len(positive_findings),
        "positive_findings": positive_findings,
        "negative_case_findings": negative_findings,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "safe_to_show": {
            "body_in_receipt": False,
            "real_runtime_receipt": True,
            "private_runtime_bodies_omitted": True,
            "provider_payloads_omitted": True,
            "live_repair_actions_omitted": True,
            "source_mutation_omitted": True,
        },
        "release_authorized": False,
        "body_in_receipt": False,
        "secret_exclusion_scan": scan,
    }


def _board(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("drift_summary", {})
    negatives = result.get("negative_case_summary", {})
    return {
        "schema_version": "world_model_projection_drift_control_room_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "world_model_projection_drift_control_public_board",
        "route": "world_model_projection_drift_control_room",
        "row_count": summary.get("row_count", 0) if isinstance(summary, dict) else 0,
        "source_ref_count": summary.get("source_ref_count", 0) if isinstance(summary, dict) else 0,
        "repair_route_count": summary.get("repair_route_count", 0) if isinstance(summary, dict) else 0,
        "validation_ref_count": summary.get("validation_ref_count", 0) if isinstance(summary, dict) else 0,
        "fact_authority_row_count": summary.get("fact_authority_row_count", 0)
        if isinstance(summary, dict)
        else 0,
        "guarded_projection_treatment_count": summary.get(
            "guarded_projection_treatment_count", 0
        )
        if isinstance(summary, dict)
        else 0,
        "unguarded_duplicate_count": summary.get("unguarded_duplicate_count", 0)
        if isinstance(summary, dict)
        else 0,
        "negative_case_count": negatives.get("expected_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "observed_negative_case_count": negatives.get("observed_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "authority_ceiling": AUTHORITY_CEILING,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": result.get("source_module_import_status"),
        "source_module_summary": result.get("source_module_summary"),
        "source_open_body_imports": result.get("source_open_body_imports"),
        "view_quality_geometry_grade": result.get("view_quality_geometry_grade"),
        "runtime_receipt_witness": result.get("runtime_receipt_witness"),
        "body_copied_material_count": result.get("body_copied_material_count"),
        "target_refs": TARGET_REFS,
        "fact_authority_mesh": {
            "status": PASS
            if summary.get("unguarded_duplicate_count", 0) == 0
            else "blocked",
            "authority_ref_policy": "authority_ref_equals_source_ref",
            "appearance_ref_policy": "appearance_refs_include_target_and_validation_refs",
            "guard_ref_policy": "guard_ref_equals_validation_ref",
            "residual_route_policy": "residual_route_equals_repair_route",
            "allowed_treatments": sorted(ALLOWED_FACT_AUTHORITY_TREATMENTS),
        },
        "anti_claim": ANTI_CLAIM,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    board = _board(result)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
    ]
    validation = {
        "schema_version": "world_model_projection_drift_control_room_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "receipt_paths": receipt_paths,
        "row_count": (result.get("drift_summary") or {}).get("row_count"),
        "expected_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "expected_negative_case_count"
        ),
        "observed_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "observed_negative_case_count"
        ),
        "authority_ceiling": AUTHORITY_CEILING,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": result.get("source_module_import_status"),
        "source_module_summary": result.get("source_module_summary"),
        "source_open_body_imports": result.get("source_open_body_imports"),
        "view_quality_geometry_grade": result.get("view_quality_geometry_grade"),
        "runtime_receipt_witness": result.get("runtime_receipt_witness"),
        "body_copied_material_count": result.get("body_copied_material_count"),
        "target_refs": TARGET_REFS,
        "fact_authority_mesh": board["fact_authority_mesh"],
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "body_in_receipt": False,
        "release_authorized": False,
    }
    write_json_atomic(result_path, result)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    if acceptance_out is not None:
        acceptance_path = acceptance_out
        acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        acceptance_path = public_root / ACCEPTANCE_RECEIPT_REL
    acceptance = {
        "schema_version": "world_model_projection_drift_control_room_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "validation_ref": receipt_paths[2],
        "authority_ceiling": AUTHORITY_CEILING,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": result.get("source_module_import_status"),
        "source_module_summary": result.get("source_module_summary"),
        "source_open_body_imports": result.get("source_open_body_imports"),
        "view_quality_geometry_grade": result.get("view_quality_geometry_grade"),
        "body_copied_material_count": result.get("body_copied_material_count"),
        "target_refs": TARGET_REFS,
        "fact_authority_mesh": board["fact_authority_mesh"],
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "release_authorized": False,
        "body_in_receipt": False,
    }
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "drift_control_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.world_model_projection_drift_control_room run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_drift_control_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.world_model_projection_drift_control_room "
        "run-drift-control-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    source = Path(input_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if reuse_fresh_receipt:
        cached = _fresh_drift_control_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_projection_drift_control_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_projection_drift_control_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    drift_summary_payload = result.get("drift_summary")
    drift_summary = (
        drift_summary_payload if isinstance(drift_summary_payload, dict) else {}
    )
    negatives_payload = result.get("negative_case_summary")
    negatives = negatives_payload if isinstance(negatives_payload, dict) else {}
    source_modules_payload = result.get("source_module_summary")
    source_modules = (
        source_modules_payload if isinstance(source_modules_payload, dict) else {}
    )
    source_open_payload = result.get("source_open_body_imports")
    source_open = source_open_payload if isinstance(source_open_payload, dict) else {}
    geometry_payload = result.get("view_quality_geometry_grade")
    geometry = geometry_payload if isinstance(geometry_payload, dict) else {}
    runtime_receipt_payload = result.get("runtime_receipt_witness")
    runtime_receipt = (
        runtime_receipt_payload if isinstance(runtime_receipt_payload, dict) else {}
    )
    recompute_payload = result.get("projection_recompute")
    recompute = recompute_payload if isinstance(recompute_payload, dict) else {}
    supplied_snapshot_payload = result.get("supplied_drift_rows_snapshot")
    supplied_snapshot = (
        supplied_snapshot_payload if isinstance(supplied_snapshot_payload, dict) else {}
    )
    scan_payload = result.get("secret_exclusion_scan")
    secret_scan = scan_payload if isinstance(scan_payload, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "projection_drift_control": {
            "row_count": drift_summary.get("row_count"),
            "source_ref_count": drift_summary.get("source_ref_count"),
            "target_ref_count": drift_summary.get("target_ref_count"),
            "repair_route_count": drift_summary.get("repair_route_count"),
            "validation_ref_count": drift_summary.get("validation_ref_count"),
            "fact_authority_row_count": drift_summary.get(
                "fact_authority_row_count"
            ),
            "guarded_projection_treatment_count": drift_summary.get(
                "guarded_projection_treatment_count"
            ),
            "unguarded_duplicate_count": drift_summary.get(
                "unguarded_duplicate_count"
            ),
            "source_authority_claim_count": drift_summary.get(
                "source_authority_claim_count"
            ),
            "live_repair_authorized_count": drift_summary.get(
                "live_repair_authorized_count"
            ),
            "source_mutation_authorized_count": drift_summary.get(
                "source_mutation_authorized_count"
            ),
            "automatic_doctrine_promotion_count": drift_summary.get(
                "automatic_doctrine_promotion_count"
            ),
            "runtime_receipt_witnessed_row_count": drift_summary.get(
                "runtime_receipt_witnessed_row_count"
            ),
            "runtime_receipt_missing_row_count": drift_summary.get(
                "runtime_receipt_missing_row_count"
            ),
        },
        "runtime_receipt_witness": {
            "status": runtime_receipt.get("status"),
            "runtime_receipt_row_count": runtime_receipt.get(
                "runtime_receipt_row_count"
            ),
            "witnessed_drift_row_count": runtime_receipt.get(
                "witnessed_drift_row_count"
            ),
            "missing_drift_row_count": len(
                runtime_receipt.get("missing_drift_row_ids") or []
            ),
            "body_in_receipt": runtime_receipt.get("body_in_receipt") is True,
        },
        "projection_recompute": {
            "status": recompute.get("status"),
            "basis": recompute.get("basis"),
            "derived_row_count": recompute.get("derived_row_count"),
            "missing_selected_pattern_count": len(
                recompute.get("missing_selected_pattern_ids") or []
            ),
            "recompute_digest": recompute.get("recompute_digest"),
        },
        "supplied_drift_rows_snapshot": {
            "status": supplied_snapshot.get("status"),
            "role": supplied_snapshot.get("role"),
            "supplied_row_count": supplied_snapshot.get("supplied_row_count"),
            "derived_row_count": supplied_snapshot.get("derived_row_count"),
            "changed_drift_row_count": len(
                supplied_snapshot.get("changed_drift_row_ids") or []
            ),
        },
        "source_open_body_imports": {
            "status": source_open.get("status"),
            "source_import_class": source_open.get("source_import_class"),
            "body_material_status": source_open.get("body_material_status"),
            "body_material_count": source_open.get("body_material_count"),
            "material_classes": source_open.get("material_classes", []),
            "body_text_exported_in_receipts": source_open.get(
                "body_text_exported_in_receipts"
            ),
            "body_text_exported_in_workingness": source_open.get(
                "body_text_exported_in_workingness"
            ),
        },
        "view_quality_geometry_grade": {
            "status": geometry.get("status"),
            "basis": geometry.get("basis"),
            "view_id": geometry.get("view_id"),
            "calibration_status": geometry.get("calibration_status"),
            "failed_gate_count": len(geometry.get("failed_gates") or []),
            "watch_gate_count": len(geometry.get("watch_gates") or []),
            "body_in_receipt": geometry.get("body_in_receipt") is True,
        },
        "source_modules": {
            "source_module_import_status": result.get(
                "source_module_import_status"
            ),
            "module_count": source_modules.get("module_count"),
            "verified_module_count": source_modules.get("verified_module_count"),
            "material_classes": source_modules.get("material_classes", []),
            "body_in_receipt": source_modules.get("body_in_receipt"),
        },
        "negative_case_coverage": {
            "expected_negative_case_count": negatives.get(
                "expected_negative_case_count"
            ),
            "observed_negative_case_count": negatives.get(
                "observed_negative_case_count"
            ),
            "missing_negative_case_count": len(negatives.get("expected_missing") or {}),
            "finding_count": result.get("finding_count"),
        },
        "validation": {
            "secret_exclusion_blocking_hit_count": secret_scan.get(
                "blocking_hit_count"
            ),
            "fact_authority_mesh_guarded": (
                drift_summary.get("unguarded_duplicate_count") == 0
            ),
            "body_in_receipt": result.get("body_in_receipt") is True,
            "release_authorized": result.get("release_authorized") is True,
        },
        "body_floor": {
            "drift_rows_in_card": False,
            "positive_findings_in_card": False,
            "negative_case_findings_in_card": False,
            "secret_exclusion_scan_in_card": False,
            "authority_ceiling_in_card": False,
            "anti_claim_in_card": False,
            "drift_control_board_in_card": False,
        },
        "authority_boundary": {
            "public_runtime_receipt_required": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "provider_payload_exported": False,
            "source_authority_claim": False,
            "source_mutation_authorized": False,
            "live_route_repair_authorized": False,
            "live_task_ledger_mutation_authorized": False,
            "private_runtime_data_exported": False,
            "proof_body_exported": False,
            "automatic_doctrine_promotion_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": (
                "rerun without --card or inspect the written receipt file"
            ),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="world_model_projection_drift_control_room")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-drift-control-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        command = f"world_model_projection_drift_control_room run{card_suffix}"
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-drift-control-bundle":
        command = (
            "world_model_projection_drift_control_room "
            f"run-drift-control-bundle{card_suffix}"
        )
        result = run_drift_control_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    output = result_card(result) if args.card else result["status"]
    print(json.dumps(output, indent=2, sort_keys=True) if args.card else output)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
