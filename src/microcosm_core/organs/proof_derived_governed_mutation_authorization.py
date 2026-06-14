from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "proof_derived_governed_mutation_authorization"
FIXTURE_ID = "first_wave.proof_derived_governed_mutation_authorization"
VALIDATOR_ID = (
    "validator.microcosm.organs.proof_derived_governed_mutation_authorization"
)

RESULT_NAME = "proof_derived_governed_mutation_authorization_result.json"
BOARD_NAME = "proof_derived_governed_mutation_authorization_board.json"
VALIDATION_RECEIPT_NAME = (
    "proof_derived_governed_mutation_authorization_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "proof_derived_governed_mutation_authorization_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_governed_mutation_authorization_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "governed_mutation_authorization_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "private_state_scan",
    "authority_ceiling",
    "anti_claim",
    "governed_mutation_record_rows",
    "proof_cell_rows",
    "policy_verdict_rows",
    "proposal_rows",
    "side_effect_rows",
    "rollback_rows",
    "cold_replay_rows",
    "source_module_imports",
    "source_open_body_imports",
    "authorization_board",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = (
    "copied_non_secret_governed_mutation_authorization_macro_body_landed"
)
GOVERNED_MUTATION_RECORDS_NAME = "governed_mutation_records.json"
REAL_RECORD_IMPORT_STATUS = "real_public_safe_governed_mutation_record_bound"
REAL_RECORD_ANTI_BAKE_PROOF_STATUS = (
    "real_record_refs_derived_from_git_scope_and_fixture_indices"
)
SOURCE_OPEN_BODY_SCHEMA = (
    "proof_derived_governed_mutation_authorization_source_open_body_imports_v1"
)
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_receipt_body",
        "public_macro_tool_body",
        "public_macro_control_plane_body",
        "public_macro_ledger_body",
    }
)
PUBLIC_SAFE_REAL_RECORD_CLASSES = frozenset(
    {
        "real_repo_scoped_commit_record",
        "real_repo_mission_transaction_record",
        "real_repo_work_landing_record",
        "real_repo_task_ledger_record",
    }
)
REAL_RECORD_REQUIRED_COMMIT_PATH_SUFFIXES = (
    "microcosm-substrate/src/microcosm_core/organs/"
    "proof_derived_governed_mutation_authorization.py",
    "microcosm-substrate/tests/"
    "test_proof_derived_governed_mutation_authorization.py",
)

INPUT_NAMES = (
    "projection_protocol.json",
    "authorization_policy.json",
    "mutation_proposals.json",
    "proof_evidence_cells.json",
    "policy_verdicts.json",
    "side_effect_ledger.json",
    "rollback_receipts.json",
    "cold_replay.json",
    GOVERNED_MUTATION_RECORDS_NAME,
)
NEGATIVE_INPUT_NAMES = (
    "standing_credential_authority.json",
    "policy_after_execution.json",
    "hidden_policy_vote.json",
    "live_cloud_credential.json",
    "irreversible_mutation.json",
    "unlogged_side_effect.json",
    "consensus_without_evidence.json",
    "final_answer_only_success.json",
)

EXPECTED_NEGATIVE_CASES = {
    "standing_credential_authority": ["GOV_MUT_STANDING_CREDENTIAL_AUTHORITY"],
    "policy_after_execution": ["GOV_MUT_POLICY_AFTER_EXECUTION"],
    "hidden_policy_vote": ["GOV_MUT_HIDDEN_POLICY_VOTE"],
    "live_cloud_credential": ["GOV_MUT_LIVE_CLOUD_CREDENTIAL"],
    "irreversible_mutation": ["GOV_MUT_IRREVERSIBLE_MUTATION"],
    "unlogged_side_effect": ["GOV_MUT_UNLOGGED_SIDE_EFFECT"],
    "consensus_without_evidence": ["GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE"],
    "final_answer_only_success": ["GOV_MUT_FINAL_ANSWER_ONLY_SUCCESS"],
}

REQUIRED_ACTION_CLASSES = (
    "read_only_inspection",
    "scoped_config_write",
    "rollback",
)
REQUIRED_PROPOSAL_FIELDS = (
    "proposal_id",
    "action_class",
    "intent_capsule_ref",
    "authority_ceiling_ref",
    "proof_cell_refs",
    "policy_verdict_refs",
    "ephemeral_identity_ref",
    "side_effect_class",
    "policy_evaluated_before_execution",
    "execution_state",
    "evidence_chain_hash",
    "cold_replay_ref",
    "body_redacted",
    "private_ref_metadata_only",
)
FORBIDDEN_KEYS = (
    "credential_value",
    "secret_value",
    "token_value",
    "provider_payload",
    "private_account_id",
    "raw_policy_vote_body",
    "raw_proof_body",
    "cloud_account_id",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_safe_real_governed_mutation_records_plus_redacted_fixture_metadata_only"
    ),
    "real_public_safe_record_required": True,
    "live_cloud_account_authorized": False,
    "standing_credentials_authorized": False,
    "source_mutation_authorized": False,
    "irreversible_mutation_authorized": False,
    "policy_after_execution_authorized": False,
    "hidden_policy_votes_authorized": False,
    "provider_calls_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Proof-derived governed mutation authorization validates public-safe real "
    "governed-mutation records bound to redacted mutation-authorization "
    "metadata: intent capsules, proof evidence cells, independent policy "
    "verdicts, ephemeral execution identity refs, logged side-effect diffs, "
    "rollback receipts, cold replay, negative cases, private state scan, and "
    "authority ceilings. It does not use standing credentials, access live "
    "cloud/accounts, mutate source, export proof bodies or provider payloads, "
    "claim benchmark safety, or authorize release."
)


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
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _row_sha256(row: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _input_record_ref(
    input_dir: Path,
    filename: str,
    selector_key: str,
    selector_value: str,
    *,
    public_root: Path,
) -> str:
    return (
        f"{_display(input_dir / filename, public_root=public_root)}::"
        f"{selector_key}={selector_value}"
    )


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
    paths = [manifest_path]
    try:
        manifest = read_json_strict(manifest_path)
    except Exception:
        return paths
    for row in _rows(manifest, "modules"):
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        if target_ref:
            paths.append(
                _source_module_target_path(
                    target_ref,
                    input_dir=input_dir,
                    public_root=public_root,
                )
            )
    return paths


def _scan_paths_for_input(input_dir: Path, *, include_negative: bool) -> list[Path]:
    public_root = _public_root_for_path(input_dir)
    return [
        *_input_paths(input_dir, include_negative=include_negative),
        *_source_module_paths(input_dir, public_root=public_root),
    ]


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        *_source_module_paths(source, public_root=public_root),
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
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "proof_derived_governed_mutation_authorization_result_v1"
        if include_negative
        else "exported_governed_mutation_authorization_bundle_validation_result_v1"
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
        "schema_version": (
            "governed_mutation_authorization_freshness_basis_v1"
        ),
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_authorization_bundle_receipt(
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
        "exported_governed_mutation_authorization_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_governed_mutation_authorization_bundle":
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
        "body_redacted": True,
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
    observed[case_id].add(code)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[str(case_id)].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = _display(manifest_path, public_root=public_root)
    if not manifest_path.is_file():
        findings = []
        status = "blocked" if require_manifest else "not_present"
        if require_manifest:
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported governed-mutation authorization bundle must include a source module manifest for copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_module_manifest",
                )
            )
        return {
            "status": status,
            "source_module_import_status": status,
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "material_classes": [],
            "body_material_classes": {},
            "source_refs": [],
            "findings": findings,
            "observed_negative_cases": {},
            "body_in_receipt": False,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [manifest_ref]

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "GOV_MUT_SOURCE_MODULE_MANIFEST_REQUIRED",
                "Source module manifest must be a JSON object.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    else:
        if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_COUNT_MISMATCH",
                    "Source module manifest module_count must match the module row count.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="module_count",
                )
            )

    verified_count = 0
    for row in modules:
        module_id = str(row.get("module_id") or "source_module")
        module_ids.append(module_id)
        material_class = str(row.get("material_class") or "")
        if material_class:
            material_class_counts[material_class] = (
                material_class_counts.get(material_class, 0) + 1
            )
        module_findings_start = len(findings)
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must use a public-safe macro body material class.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="material_class",
                )
            )
        if (
            row.get("body_copied") is not True
            or row.get("body_in_receipt") is not False
            or row.get("body_text_in_receipt") is not False
        ):
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while keeping receipt fields body-free.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        target = _source_module_target_path(
            target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        if not target.is_file():
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        expected_digests = {
            "sha256": str(row.get("sha256") or ""),
            "source_sha256": str(row.get("source_sha256") or ""),
            "target_sha256": str(row.get("target_sha256") or ""),
        }
        if any(value != actual for value in expected_digests.values()):
            findings.append(
                _finding(
                    "GOV_MUT_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module digest declarations must match the copied target body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        text = target.read_text(encoding="utf-8")
        missing_anchors = [
            anchor
            for anchor in _strings(row.get("required_anchors"))
            if anchor not in text
        ]
        if missing_anchors:
            findings.append(
                {
                    **_finding(
                        "GOV_MUT_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared governed-mutation macro anchors.",
                        case_id="source_module_manifest_floor",
                        subject_id=module_id,
                        subject_kind="source_module",
                    ),
                    "missing_anchors": missing_anchors,
                }
            )
        source_refs.append(_display(target, public_root=public_root))
        if len(findings) == module_findings_start:
            verified_count += 1

    status = PASS if modules and not findings else "blocked"
    return {
        "status": status,
        "source_module_import_status": (
            SOURCE_MODULE_IMPORT_STATUS if status == PASS else "blocked"
        ),
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "verified_module_count": verified_count,
        "module_ids": module_ids,
        "material_classes": sorted(material_class_counts),
        "body_material_classes": material_class_counts,
        "source_refs": source_refs,
        "findings": findings,
        "observed_negative_cases": {},
        "body_in_receipt": False,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    module_ids = _strings(source_module_result.get("module_ids"))
    manifest_ref = source_module_result.get("source_module_manifest_ref")
    imported = source_module_result.get("status") == PASS and bool(module_ids)
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": PASS if imported else str(source_module_result.get("status") or ""),
        "source_import_class": SOURCE_IMPORT_CLASS if imported else "",
        "body_material_status": SOURCE_MODULE_IMPORT_STATUS if imported else "",
        "body_material_count": len(module_ids) if imported else 0,
        "body_material_ids": module_ids if imported else [],
        "material_classes": source_module_result.get("material_classes", [])
        if imported
        else [],
        "body_material_classes": source_module_result.get("body_material_classes", {})
        if imported
        else {},
        "source_manifest_refs": [str(manifest_ref)]
        if imported and manifest_ref
        else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules"
        if imported and manifest_ref
        else "",
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "standing_credentials_authorized": False,
            "live_cloud_account_authorized": False,
            "provider_payload_exported": False,
            "proof_body_exported": False,
            "source_mutation_authorized": False,
            "irreversible_mutation_authorized": False,
            "release_authorized": False,
            "benchmark_score_claim_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported governed-mutation authorization bundle for copied macro "
            "pattern, receipt, Work Ledger, scoped-commit, mission-transaction, "
            "and work-landing control bodies; receipts carry refs, hashes, "
            "counts, and verdicts only."
        )
        if imported
        else "",
    }


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def _negative_rows(payloads: dict[str, object], key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in payloads.values():
        nested = _rows(payload, key)
        if nested:
            rows.extend(nested)
        elif isinstance(payload, dict):
            rows.append(payload)
    return rows


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_replacements = _strings(protocol.get("public_replacement_refs"))
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 5
        or "proof_derived_governed_mutation_authorization_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or len(public_replacements) < 3
        or not _strings(protocol.get("reimplemented"))
        or not _strings(protocol.get("omitted"))
    ):
        findings.append(
            _finding(
                "GOV_MUT_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, projection receipts, public replacements, reimplemented pieces, and omissions.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if protocol.get("copied_private_proof_bodies") is not False:
        findings.append(
            _finding(
                "GOV_MUT_PRIVATE_PROOF_BODY_COPY_CLAIM",
                "Projection protocol must explicitly deny copying private proof bodies or provider payloads.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_replacement_refs": public_replacements,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_authorization_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    allowed_classes = set(_strings(policy.get("allowed_action_classes")))
    required_fields = set(_strings(policy.get("required_proposal_fields")))
    findings: list[dict[str, Any]] = []
    if not set(REQUIRED_ACTION_CLASSES).issubset(allowed_classes):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_CLASSES_INCOMPLETE",
                "Policy must define read-only, scoped write, and rollback action classes.",
                case_id="authorization_policy_floor",
                subject_id=str(policy.get("policy_id") or "authorization_policy"),
                subject_kind="authorization_policy",
            )
        )
    if not set(REQUIRED_PROPOSAL_FIELDS).issubset(required_fields):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Policy must require intent, proof, verdict, side-effect, rollback, cold-replay, redaction, and anti-overclaim fields.",
                case_id="authorization_policy_floor",
                subject_id=str(policy.get("policy_id") or "authorization_policy"),
                subject_kind="authorization_policy",
            )
        )
    if int(policy.get("minimum_independent_verdicts") or 0) < 2:
        findings.append(
            _finding(
                "GOV_MUT_POLICY_CONSENSUS_FLOOR_MISSING",
                "Policy must require at least two visible independent policy verdicts before execution identity is minted.",
                case_id="authorization_policy_floor",
                subject_id="minimum_independent_verdicts",
                subject_kind="authorization_policy",
            )
        )
    for field in (
        "standing_credentials_authorized",
        "live_cloud_account_authorized",
        "policy_after_execution_authorized",
        "hidden_policy_votes_authorized",
        "irreversible_mutation_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "GOV_MUT_POLICY_AUTHORITY_OVERCLAIM",
                    "Governed mutation policy cannot authorize standing credentials, live cloud/account mutation, policy-after-execution, hidden policy votes, irreversible mutation, provider calls, or release.",
                    case_id="authorization_policy_floor",
                    subject_id=field,
                    subject_kind="authorization_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_action_classes": sorted(allowed_classes),
        "required_proposal_fields": sorted(required_fields),
        "minimum_independent_verdicts": int(
            policy.get("minimum_independent_verdicts") or 0
        ),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _build_proof_index(payload: object) -> dict[str, dict[str, Any]]:
    return {str(row.get("proof_cell_id") or ""): row for row in _rows(payload, "proof_cells")}


def _build_verdict_index(payload: object) -> dict[str, dict[str, Any]]:
    return {str(row.get("verdict_id") or ""): row for row in _rows(payload, "verdicts")}


def _build_side_effect_index(payload: object) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("proposal_id") or ""): row
        for row in _rows(payload, "side_effects")
    }


def _build_rollback_index(payload: object) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("rollback_receipt_ref") or row.get("rollback_id") or ""): row
        for row in _rows(payload, "rollback_receipts")
    }


def _build_cold_replay_index(payload: object) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("replay_id") or ""): row
        for row in _rows(payload, "cold_replays")
    }


def _public_receipt_ref_result(refs: list[str], *, public_root: Path) -> dict[str, Any]:
    resolved: list[str] = []
    missing: list[str] = []
    digests: list[str] = []
    canonical_root = _public_root_for_path(Path(__file__).resolve())
    for ref in refs:
        path_ref = ref.split("::", 1)[0]
        if path_ref.startswith(("/", "..")):
            missing.append(ref)
            continue
        candidates = [public_root / path_ref]
        if canonical_root != public_root:
            candidates.append(canonical_root / path_ref)
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is not None:
            resolved.append(ref)
            digests.append(_sha256(path))
        else:
            missing.append(ref)
    return {
        "resolved_refs": resolved,
        "missing_refs": missing,
        "digests": digests,
    }


def _proof_row_has_public_evidence(
    row: dict[str, Any],
    *,
    public_root: Path | None = None,
) -> bool:
    evidence_refs = _strings(row.get("evidence_refs"))
    validator_refs = _strings(row.get("validator_receipt_refs"))
    if (
        not evidence_refs
        or not validator_refs
        or row.get("body_redacted") is not True
        or row.get("private_ref_metadata_only") is not True
        or row.get("proof_body_exported") is not False
    ):
        return False
    if public_root is None:
        return True
    evidence = _public_receipt_ref_result(evidence_refs, public_root=public_root)
    validator = _public_receipt_ref_result(validator_refs, public_root=public_root)
    return not evidence["missing_refs"] and not validator["missing_refs"]


def _verdict_row_resolves_proof(
    row: dict[str, Any],
    proof_index: dict[str, dict[str, Any]],
    proposal_id: str,
    *,
    public_root: Path | None = None,
) -> bool:
    evidence_refs = _strings(row.get("evidence_refs"))
    if not evidence_refs:
        return False
    for ref in evidence_refs:
        proof = proof_index.get(ref, {})
        if str(proof.get("proposal_id") or "") != proposal_id:
            return False
        if not _proof_row_has_public_evidence(proof, public_root=public_root):
            return False
    return True


def _rollback_row_resolves_records(
    row: dict[str, Any],
    side_effect_index: dict[str, dict[str, Any]],
    cold_replay_index: dict[str, dict[str, Any]],
    proposal_id: str,
) -> bool:
    evidence_refs = set(_strings(row.get("evidence_refs")))
    side_effect = side_effect_index.get(proposal_id, {})
    diff_ref = str(side_effect.get("diff_ref") or "")
    cold_refs = {
        replay_id
        for replay_id, cold_row in cold_replay_index.items()
        if str(cold_row.get("proposal_id") or "") == proposal_id
        and cold_row.get("status") == PASS
    }
    return bool(
        diff_ref
        and diff_ref in evidence_refs
        and cold_refs
        and evidence_refs.intersection(cold_refs)
    )


def _git_root_candidates(public_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for start in (public_root.parent, Path.cwd(), Path(__file__).resolve()):
        for candidate in (start, *start.parents):
            if (candidate / ".git").exists() and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _git_output(repo_root: Path, args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.rstrip("\n")


def _git_commit_evidence(commit_ref: str, *, public_root: Path) -> dict[str, Any]:
    if not commit_ref:
        return {"status": "missing", "verified": False}
    for repo_root in _git_root_candidates(public_root):
        full_ref = _git_output(repo_root, ["rev-parse", "--verify", f"{commit_ref}^{{commit}}"])
        if not full_ref:
            continue
        subject = _git_output(repo_root, ["show", "--quiet", "--format=%s", full_ref])
        changed = _git_output(repo_root, ["show", "--name-only", "--format=", full_ref])
        touched_paths = [
            line.strip()
            for line in (changed or "").splitlines()
            if line.strip()
        ]
        matched_paths = [
            path
            for path in touched_paths
            if any(path.endswith(suffix) for suffix in REAL_RECORD_REQUIRED_COMMIT_PATH_SUFFIXES)
        ]
        evidence_digest = hashlib.sha256(
            json.dumps(
                {
                    "commit_ref": full_ref,
                    "subject": subject or "",
                    "matched_paths": matched_paths,
                    "required_path_suffixes": REAL_RECORD_REQUIRED_COMMIT_PATH_SUFFIXES,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return {
            "status": PASS,
            "verified": True,
            "repo_root_ref": _display(repo_root, public_root=public_root)
            if public_root in repo_root.parents or repo_root == public_root
            else "repo_root",
            "commit_ref": full_ref,
            "commit_subject": subject or "",
            "touched_paths": touched_paths,
            "matched_required_paths": matched_paths,
            "scope_verified": bool(matched_paths),
            "evidence_digest": f"sha256:{evidence_digest}",
        }
    return {
        "status": "blocked",
        "verified": False,
        "commit_ref": commit_ref,
        "scope_verified": False,
        "matched_required_paths": [],
        "evidence_digest": "",
    }


def _derived_proof_refs(
    proof_index: dict[str, dict[str, Any]],
    proposal_id: str,
    *,
    public_root: Path | None = None,
) -> list[str]:
    return [
        ref
        for ref, row in proof_index.items()
        if str(row.get("proposal_id") or "") == proposal_id
        and _proposal_has_evidence(
            [ref],
            proof_index,
            proposal_id,
            public_root=public_root,
        )
    ]


def _derived_policy_refs(
    verdict_index: dict[str, dict[str, Any]],
    proof_index: dict[str, dict[str, Any]],
    proposal_id: str,
    *,
    public_root: Path | None = None,
) -> list[str]:
    return [
        ref
        for ref, row in verdict_index.items()
        if str(row.get("proposal_id") or "") == proposal_id
        and row.get("visible_to_receipt") is True
        and row.get("hidden_policy_vote") is not True
        and row.get("verdict") in {"allow", "warn"}
        and _verdict_row_resolves_proof(
            row,
            proof_index,
            proposal_id,
            public_root=public_root,
        )
    ]


def _derived_rollback_ref(
    rollback_index: dict[str, dict[str, Any]],
    side_effect_index: dict[str, dict[str, Any]],
    cold_replay_index: dict[str, dict[str, Any]],
    proposal_id: str,
) -> str:
    for ref, row in rollback_index.items():
        if (
            str(row.get("proposal_id") or "") == proposal_id
            and row.get("rollback_status") == PASS
            and _rollback_row_resolves_records(
                row,
                side_effect_index,
                cold_replay_index,
                proposal_id,
            )
        ):
            return ref
    return ""


def _proposal_evidence_chain_hash(
    row: dict[str, Any],
    *,
    proof_index: dict[str, dict[str, Any]],
    verdict_index: dict[str, dict[str, Any]],
    side_effect_index: dict[str, dict[str, Any]],
    rollback_index: dict[str, dict[str, Any]],
    cold_replay_index: dict[str, dict[str, Any]],
    public_root: Path | None = None,
) -> str:
    proposal_id = str(row.get("proposal_id") or "")
    proof_refs = _strings(row.get("proof_cell_refs"))
    verdict_refs = _strings(row.get("policy_verdict_refs"))
    side_effect_ref = str(row.get("side_effect_diff_ref") or "")
    rollback_ref = str(row.get("rollback_receipt_ref") or "")
    cold_replay_ref = str(row.get("cold_replay_ref") or "")

    proof_digests = {
        ref: _row_sha256(proof_index[ref])
        for ref in proof_refs
        if ref in proof_index
        and str(proof_index[ref].get("proposal_id") or "") == proposal_id
        and _proof_row_has_public_evidence(
            proof_index[ref],
            public_root=public_root,
        )
    }
    policy_digests = {
        ref: _row_sha256(verdict_index[ref])
        for ref in verdict_refs
        if ref in verdict_index
        and str(verdict_index[ref].get("proposal_id") or "") == proposal_id
        and _verdict_row_resolves_proof(
            verdict_index[ref],
            proof_index,
            proposal_id,
            public_root=public_root,
        )
    }
    side_effect = side_effect_index.get(proposal_id, {})
    side_effect_digest = (
        _row_sha256(side_effect)
        if side_effect_ref
        and side_effect_ref == str(side_effect.get("diff_ref") or "")
        else ""
    )
    rollback = rollback_index.get(rollback_ref, {})
    rollback_digest = (
        _row_sha256(rollback)
        if rollback_ref
        and str(rollback.get("proposal_id") or "") == proposal_id
        and rollback.get("rollback_status") == PASS
        else ""
    )
    cold_replay = cold_replay_index.get(cold_replay_ref, {})
    cold_replay_digest = (
        _row_sha256(cold_replay)
        if cold_replay_ref
        and str(cold_replay.get("proposal_id") or "") == proposal_id
        and cold_replay.get("status") == PASS
        else ""
    )
    digest = hashlib.sha256(
        json.dumps(
            {
                "cold_replay": {
                    "digest": cold_replay_digest,
                    "ref": cold_replay_ref,
                },
                "policy_verdicts": policy_digests,
                "proof_cells": proof_digests,
                "proposal_id": proposal_id,
                "rollback": {
                    "digest": rollback_digest,
                    "ref": rollback_ref,
                },
                "side_effect": {
                    "digest": side_effect_digest,
                    "ref": side_effect_ref,
                },
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _visible_allowing_verdict_count(
    refs: list[str],
    verdict_index: dict[str, dict[str, Any]],
    proposal_id: str,
    proof_index: dict[str, dict[str, Any]] | None = None,
    *,
    public_root: Path | None = None,
) -> int:
    count = 0
    for ref in refs:
        row = verdict_index.get(ref, {})
        if (
            str(row.get("proposal_id") or "") == proposal_id
            and row.get("visible_to_receipt") is True
            and row.get("hidden_policy_vote") is not True
            and row.get("verdict") in {"allow", "warn"}
            and (
                proof_index is None
                or _verdict_row_resolves_proof(
                    row,
                    proof_index,
                    proposal_id,
                    public_root=public_root,
                )
            )
        ):
            count += 1
    return count


def _proposal_has_evidence(
    refs: list[str],
    proof_index: dict[str, dict[str, Any]],
    proposal_id: str,
    *,
    public_root: Path | None = None,
) -> bool:
    for ref in refs:
        row = proof_index.get(ref, {})
        if (
            str(row.get("proposal_id") or "") == proposal_id
            and _proof_row_has_public_evidence(row, public_root=public_root)
        ):
            return True
    return False


def _validate_proposal_row(
    row: dict[str, Any],
    *,
    proof_index: dict[str, dict[str, Any]],
    verdict_index: dict[str, dict[str, Any]],
    side_effect_index: dict[str, dict[str, Any]],
    rollback_index: dict[str, dict[str, Any]],
    cold_replay_index: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
    public_root: Path | None = None,
) -> dict[str, Any]:
    case_id = str(
        row.get("expected_negative_case_id") or row.get("proposal_id") or "proposal"
    )
    proposal_id = str(row.get("proposal_id") or case_id)
    subject_kind = "negative_case" if negative else "mutation_proposal"
    proof_refs = _strings(row.get("proof_cell_refs"))
    verdict_refs = _strings(row.get("policy_verdict_refs"))
    action_class = str(row.get("action_class") or "")
    side_effect_class = str(row.get("side_effect_class") or "")
    side_effect_ref = str(row.get("side_effect_diff_ref") or "")
    rollback_ref = str(row.get("rollback_receipt_ref") or "")
    declared_evidence_chain_hash = str(row.get("evidence_chain_hash") or "")
    derived_evidence_chain_hash = _proposal_evidence_chain_hash(
        row,
        proof_index=proof_index,
        verdict_index=verdict_index,
        side_effect_index=side_effect_index,
        rollback_index=rollback_index,
        cold_replay_index=cold_replay_index,
        public_root=public_root,
    )
    reasons: list[str] = []
    missing = [
        field
        for field in REQUIRED_PROPOSAL_FIELDS
        if field not in row or row.get(field) is None
    ]

    if row.get("standing_credential_claimed") is True or row.get(
        "authorization_basis"
    ) == "standing_credential":
        reasons.append("standing_credential_authority")
        _record(
            findings,
            observed,
            "GOV_MUT_STANDING_CREDENTIAL_AUTHORITY",
            "Standing credentials are not mutation authority; authorization must derive from replayable proof and visible verdicts.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("policy_evaluated_before_execution") is not True or row.get(
        "executed_before_policy"
    ) is True:
        reasons.append("policy_after_execution")
        _record(
            findings,
            observed,
            "GOV_MUT_POLICY_AFTER_EXECUTION",
            "Policy evaluation must occur before any execution identity or side-effect metadata is admitted.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("hidden_policy_vote") is True or not verdict_refs:
        reasons.append("hidden_policy_vote")
        _record(
            findings,
            observed,
            "GOV_MUT_HIDDEN_POLICY_VOTE",
            "Policy verdicts must be visible receipt refs; hidden consensus cannot authorize mutation.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("live_cloud_credential_ref") is True or _has_forbidden_key(row):
        reasons.append("live_cloud_credential")
        _record(
            findings,
            observed,
            "GOV_MUT_LIVE_CLOUD_CREDENTIAL",
            "Public governed-mutation fixtures cannot carry live cloud/account credentials or private account refs.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("irreversible_side_effect") is True or (
        side_effect_class in {"scoped_config_write", "rollback"}
        and not rollback_ref
    ):
        reasons.append("irreversible_mutation")
        _record(
            findings,
            observed,
            "GOV_MUT_IRREVERSIBLE_MUTATION",
            "Write or rollback proposals require rollback/verifiability refs and cannot claim irreversible mutation authority.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if side_effect_class in {"scoped_config_write", "rollback"} and (
        not side_effect_ref or row.get("side_effect_logged") is not True
    ):
        reasons.append("unlogged_side_effect")
        _record(
            findings,
            observed,
            "GOV_MUT_UNLOGGED_SIDE_EFFECT",
            "Side effects must be logged with a synthetic diff ref before claim admission.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if (
        not proof_refs
        or not declared_evidence_chain_hash
        or declared_evidence_chain_hash != derived_evidence_chain_hash
        or not _proposal_has_evidence(proof_refs, proof_index, proposal_id)
        or _visible_allowing_verdict_count(
            verdict_refs,
            verdict_index,
            proposal_id,
            proof_index,
            public_root=public_root,
        )
        < 2
    ):
        reasons.append("consensus_without_evidence")
        if declared_evidence_chain_hash != derived_evidence_chain_hash:
            reasons.append("evidence_chain_hash_mismatch")
            _record(
                findings,
                observed,
                "GOV_MUT_EVIDENCE_CHAIN_HASH_MISMATCH",
                "Proposal evidence-chain hash must be recomputed from resolved proof, policy verdict, side-effect, rollback, and cold-replay rows.",
                case_id=case_id,
                subject_id=proposal_id,
                subject_kind=subject_kind,
            )
        _record(
            findings,
            observed,
            "GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE",
            "Consensus must cite proof evidence cells, validator receipts, an evidence-chain hash, and two visible verdicts.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("final_answer_only_success") is True:
        reasons.append("final_answer_only_success")
        _record(
            findings,
            observed,
            "GOV_MUT_FINAL_ANSWER_ONLY_SUCCESS",
            "Mutation authorization cannot be graded by final-answer success without proof, verdict, side-effect, rollback, and replay evidence.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("body_redacted") is not True or row.get("private_ref_metadata_only") is not True:
        reasons.append("unredacted_public_fixture")
    if action_class not in REQUIRED_ACTION_CLASSES:
        reasons.append("unknown_action_class")
    if missing:
        reasons.append("proposal_field_missing")

    return {
        "proposal_id": proposal_id,
        "action_class": action_class,
        "intent_capsule_ref": row.get("intent_capsule_ref"),
        "authority_ceiling_ref": row.get("authority_ceiling_ref"),
        "proof_cell_refs": proof_refs,
        "policy_verdict_refs": verdict_refs,
        "ephemeral_identity_ref": row.get("ephemeral_identity_ref"),
        "side_effect_class": side_effect_class,
        "side_effect_diff_ref": side_effect_ref,
        "rollback_receipt_ref": rollback_ref,
        "policy_evaluated_before_execution": (
            row.get("policy_evaluated_before_execution") is True
        ),
        "execution_state": str(row.get("execution_state") or ""),
        "evidence_chain_hash": declared_evidence_chain_hash,
        "derived_evidence_chain_hash": derived_evidence_chain_hash,
        "evidence_chain_hash_matches": (
            declared_evidence_chain_hash == derived_evidence_chain_hash
        ),
        "cold_replay_ref": row.get("cold_replay_ref"),
        "computed_verdict": (
            "authorized_synthetic_mutation_metadata" if not reasons else "blocked"
        ),
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_redacted": True,
    }


def validate_proof_evidence_cells(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "proof_cells")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        proof_id = str(row.get("proof_cell_id") or "")
        reasons: list[str] = []
        if not row.get("proposal_id"):
            reasons.append("missing_proposal_ref")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        if not _strings(row.get("validator_receipt_refs")):
            reasons.append("missing_validator_receipt_refs")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if row.get("private_ref_metadata_only") is not True:
            reasons.append("private_ref_not_metadata_only")
        if row.get("proof_body_exported") is not False:
            reasons.append("proof_body_exported")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "proof_cell_id": proof_id,
                "proposal_id": row.get("proposal_id"),
                "evidence_kind": row.get("evidence_kind"),
                "evidence_ref_count": len(_strings(row.get("evidence_refs"))),
                "validator_receipt_ref_count": len(
                    _strings(row.get("validator_receipt_refs"))
                ),
                "computed_verdict": "accepted_proof_cell" if not reasons else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) < 3 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_PROOF_CELL_FLOOR_MISSING",
                "Positive fixture must expose redacted proof cells with evidence refs and validator receipt refs for each proposed action.",
                case_id="proof_cell_floor",
                subject_id="proof_evidence_cells",
                subject_kind="proof_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "proof_cell_count": len(rows),
        "accepted_proof_cell_count": sum(1 for row in accepted if not row["reason_codes"]),
        "proof_cell_rows": sorted(accepted, key=lambda row: row["proof_cell_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_policy_verdicts(
    payload: object,
    proof_payload: object,
    *,
    public_root: Path | None = None,
) -> dict[str, Any]:
    rows = _rows(payload, "verdicts")
    proof_index = _build_proof_index(proof_payload)
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    by_proposal: dict[str, int] = defaultdict(int)
    for row in rows:
        verdict_id = str(row.get("verdict_id") or "")
        proposal_id = str(row.get("proposal_id") or "")
        reasons: list[str] = []
        if row.get("verdict") not in {"allow", "warn", "block", "review"}:
            reasons.append("unknown_verdict")
        if row.get("visible_to_receipt") is not True:
            reasons.append("hidden_vote")
        if row.get("hidden_policy_vote") is True:
            reasons.append("hidden_policy_vote")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        elif not _verdict_row_resolves_proof(
            row,
            proof_index,
            proposal_id,
            public_root=public_root,
        ):
            reasons.append("evidence_ref_unresolved")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if not reasons and row.get("verdict") in {"allow", "warn"}:
            by_proposal[proposal_id] += 1
        accepted.append(
            {
                "verdict_id": verdict_id,
                "proposal_id": proposal_id,
                "evaluator_id": row.get("evaluator_id"),
                "verdict": row.get("verdict"),
                "visible_to_receipt": row.get("visible_to_receipt") is True,
                "computed_verdict": "accepted_policy_verdict" if not reasons else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) < 6 or any(count < 2 for count in by_proposal.values()):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_VERDICT_FLOOR_MISSING",
                "Positive fixture must carry at least two visible allow/warn verdicts per authorized proposal.",
                case_id="policy_verdict_floor",
                subject_id="policy_verdicts",
                subject_kind="policy_verdict_fixture",
            )
        )
    if any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_VERDICT_INVALID",
                "Positive policy verdict rows must be visible, redacted, evidence-backed receipt refs.",
                case_id="policy_verdict_floor",
                subject_id="policy_verdicts",
                subject_kind="policy_verdict_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "policy_verdict_count": len(rows),
        "visible_policy_verdict_count": sum(
            1 for row in accepted if row["visible_to_receipt"]
        ),
        "proposal_consensus_counts": dict(sorted(by_proposal.items())),
        "policy_verdict_rows": sorted(accepted, key=lambda row: row["verdict_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_mutation_proposals(
    payload: object,
    proof_payload: object,
    verdict_payload: object,
    side_effect_payload: object,
    rollback_payload: object,
    cold_replay_payload: object,
    negative_payloads: dict[str, object],
    *,
    public_root: Path | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    proof_index = _build_proof_index(proof_payload)
    verdict_index = _build_verdict_index(verdict_payload)
    side_effect_index = _build_side_effect_index(side_effect_payload)
    rollback_index = _build_rollback_index(rollback_payload)
    cold_replay_index = _build_cold_replay_index(cold_replay_payload)
    rows = [
        _validate_proposal_row(
            row,
            proof_index=proof_index,
            verdict_index=verdict_index,
            side_effect_index=side_effect_index,
            rollback_index=rollback_index,
            cold_replay_index=cold_replay_index,
            findings=findings,
            observed=observed,
            negative=False,
            public_root=public_root,
        )
        for row in _rows(payload, "mutation_proposals")
    ]
    for row in _negative_rows(negative_payloads, "mutation_proposals"):
        _validate_proposal_row(
            row,
            proof_index=proof_index,
            verdict_index=verdict_index,
            side_effect_index=side_effect_index,
            rollback_index=rollback_index,
            cold_replay_index=cold_replay_index,
            findings=findings,
            observed=observed,
            negative=True,
            public_root=public_root,
        )

    authorized = [row for row in rows if not row["reason_codes"]]
    write_or_rollback = [
        row
        for row in authorized
        if row["side_effect_class"] in {"scoped_config_write", "rollback"}
    ]
    action_classes = {row["action_class"] for row in authorized}
    floor_blocked = (
        len(authorized) != 3
        or not set(REQUIRED_ACTION_CLASSES).issubset(action_classes)
        or len(write_or_rollback) != 2
    )
    positive_findings = [row for row in rows if row["reason_codes"]]
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "GOV_MUT_PROPOSAL_FLOOR_MISSING",
                "Positive fixture must authorize read-only, scoped write, and rollback proposal metadata with proof, visible verdict, side-effect, rollback, and replay refs.",
                case_id="mutation_proposal_floor",
                subject_id="mutation_proposals",
                subject_kind="mutation_proposal_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked and not positive_findings else "blocked",
        "proposal_count": len(rows),
        "authorized_mutation_count": len(authorized),
        "write_or_rollback_count": len(write_or_rollback),
        "action_classes": sorted(action_classes),
        "proposal_rows": sorted(rows, key=lambda row: row["proposal_id"]),
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _proposal_result_with_real_record_gate(
    proposals: dict[str, Any],
    governed_records: dict[str, Any],
) -> dict[str, Any]:
    accepted_real_ids = set(
        _strings(governed_records.get("accepted_real_record_proposal_ids"))
    )
    rows: list[dict[str, Any]] = []
    for row in _rows(proposals, "proposal_rows"):
        next_row = dict(row)
        proposal_id = str(next_row.get("proposal_id") or "")
        reasons = set(_strings(next_row.get("reason_codes")))
        if (
            next_row.get("computed_verdict") == "authorized_synthetic_mutation_metadata"
            and proposal_id not in accepted_real_ids
        ):
            reasons.add("real_governed_mutation_record_missing")
            next_row["computed_verdict"] = "blocked"
        next_row["reason_codes"] = sorted(reasons)
        rows.append(next_row)

    authorized = [
        row
        for row in rows
        if row["computed_verdict"] == "authorized_synthetic_mutation_metadata"
    ]
    write_or_rollback = [
        row
        for row in authorized
        if row["side_effect_class"] in {"scoped_config_write", "rollback"}
    ]
    action_classes = {row["action_class"] for row in authorized}
    floor_blocked = (
        len(authorized) != 3
        or not set(REQUIRED_ACTION_CLASSES).issubset(action_classes)
        or len(write_or_rollback) != 2
    )
    result = dict(proposals)
    result["status"] = PASS if not floor_blocked else "blocked"
    result["authorized_mutation_count"] = len(authorized)
    result["write_or_rollback_count"] = len(write_or_rollback)
    result["action_classes"] = sorted(action_classes)
    result["proposal_rows"] = sorted(rows, key=lambda row: row["proposal_id"])
    return result


def _record_real_finding(
    findings: list[dict[str, Any]],
    code: str,
    message: str,
    *,
    record_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id="real_governed_mutation_record_floor",
            subject_id=record_id,
            subject_kind=subject_kind,
        )
    )


def _real_record_ref_digest(
    *,
    record_id: str,
    proposal_id: str,
    commit_evidence: dict[str, Any],
    derived_proof_refs: list[str],
    derived_policy_refs: list[str],
    derived_rollback_ref: str,
    resolved_record_digests: dict[str, str],
) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "commit_evidence_digest": commit_evidence.get("evidence_digest"),
                "derived_policy_refs": derived_policy_refs,
                "derived_proof_refs": derived_proof_refs,
                "derived_rollback_ref": derived_rollback_ref,
                "proposal_id": proposal_id,
                "record_id": record_id,
                "resolved_record_digests": resolved_record_digests,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def validate_governed_mutation_records(
    payload: object,
    proposal_payload: object,
    proof_payload: object,
    verdict_payload: object,
    side_effect_payload: object,
    rollback_payload: object,
    cold_replay_payload: object,
    input_dir: Path,
    public_root: Path,
) -> dict[str, Any]:
    records = _rows(payload, "governed_mutation_records")
    if not records:
        records = _rows(payload, "records")
    proposals = {
        str(row.get("proposal_id") or ""): row
        for row in _rows(proposal_payload, "mutation_proposals")
    }
    proof_index = _build_proof_index(proof_payload)
    verdict_index = _build_verdict_index(verdict_payload)
    side_effect_index = _build_side_effect_index(side_effect_payload)
    rollback_index = _build_rollback_index(rollback_payload)
    cold_replay_index = _build_cold_replay_index(cold_replay_payload)
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    accepted_proposal_ids: set[str] = set()

    for row in records:
        record_id = str(row.get("record_id") or row.get("proposal_id") or "real_record")
        proposal_id = str(row.get("proposal_id") or "")
        proposal = proposals.get(proposal_id, {})
        proposal_policy_refs = set(_strings(proposal.get("policy_verdict_refs")))
        proposal_proof_refs = set(_strings(proposal.get("proof_cell_refs")))
        policy_refs = _strings(row.get("policy_verdict_refs"))
        proof_refs = _strings(row.get("proof_cell_refs"))
        source_refs = _strings(row.get("source_refs"))
        record_class = str(row.get("source_record_class") or "")
        side_effect_ref = str(row.get("side_effect_diff_ref") or "")
        rollback_ref = str(row.get("rollback_receipt_ref") or "")
        derived_proof_refs = _derived_proof_refs(
            proof_index,
            proposal_id,
            public_root=public_root,
        )
        derived_policy_refs = _derived_policy_refs(
            verdict_index,
            proof_index,
            proposal_id,
            public_root=public_root,
        )
        derived_rollback_ref = _derived_rollback_ref(
            rollback_index,
            side_effect_index,
            cold_replay_index,
            proposal_id,
        )
        commit_ref = str(row.get("commit_ref") or "")
        commit_evidence = _git_commit_evidence(commit_ref, public_root=public_root)
        reasons: list[str] = []
        rollback_refs_match = True
        proof_record_digests = {
            ref: _row_sha256(proof_index[ref])
            for ref in proof_refs
            if ref in proof_index
        }
        policy_record_digests = {
            ref: _row_sha256(verdict_index[ref])
            for ref in policy_refs
            if ref in verdict_index
        }
        side_effect_record_digest = (
            _row_sha256(side_effect_index[proposal_id])
            if proposal_id in side_effect_index
            else ""
        )
        rollback_record_digest = (
            _row_sha256(rollback_index[rollback_ref])
            if rollback_ref in rollback_index
            else ""
        )
        cold_replay_record_refs = [
            _input_record_ref(
                input_dir,
                "cold_replay.json",
                "replay_id",
                replay_id,
                public_root=public_root,
            )
            for replay_id, cold_row in sorted(cold_replay_index.items())
            if str(cold_row.get("proposal_id") or "") == proposal_id
            and cold_row.get("status") == PASS
        ]
        cold_replay_record_digests = {
            replay_id: _row_sha256(cold_row)
            for replay_id, cold_row in sorted(cold_replay_index.items())
            if str(cold_row.get("proposal_id") or "") == proposal_id
            and cold_row.get("status") == PASS
        }

        if record_class not in PUBLIC_SAFE_REAL_RECORD_CLASSES:
            reasons.append("unsupported_real_record_class")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_CLASS_INVALID",
                "Real governed-mutation records must declare a public-safe repo record class.",
                record_id=record_id,
                subject_kind="governed_mutation_record",
            )
        if proposal_id not in proposals:
            reasons.append("proposal_ref_missing")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_PROPOSAL_REF_INVALID",
                "Real governed-mutation records must bind to an existing mutation proposal.",
                record_id=record_id,
                subject_kind="proposal_ref",
            )
        if row.get("public_safe") is not True or row.get("body_redacted") is not True:
            reasons.append("public_safe_boundary_missing")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_PUBLIC_SAFE_BOUNDARY_MISSING",
                "Real governed-mutation records must be public-safe and body-redacted.",
                record_id=record_id,
                subject_kind="public_safe_boundary",
            )
        if (
            row.get("private_ref_metadata_only") is not True
            or row.get("provider_payload_exported") is not False
            or row.get("live_credential_ref") is True
        ):
            reasons.append("private_boundary_overclaim")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_PRIVATE_BOUNDARY_OVERCLAIM",
                "Real governed-mutation records cannot export provider payloads, live credentials, or private body refs.",
                record_id=record_id,
                subject_kind="private_boundary",
            )
        if not (
            10 <= len(commit_ref) <= 40
            and all(char in "0123456789abcdef" for char in commit_ref.lower())
        ):
            reasons.append("commit_ref_invalid")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_COMMIT_REF_INVALID",
                "Real governed-mutation records must cite a concrete git commit ref.",
                record_id=record_id,
                subject_kind="commit_ref",
            )
        elif not commit_evidence.get("verified"):
            reasons.append("commit_ref_unverified")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_COMMIT_REF_UNVERIFIED",
                "Real governed-mutation records must resolve to a real git commit.",
                record_id=record_id,
                subject_kind="commit_ref",
            )
        else:
            full_ref = str(commit_evidence.get("commit_ref") or "")
            if commit_ref.lower() not in full_ref.lower() or not any(
                commit_ref.lower() in ref.lower()
                for ref in source_refs
                if ref.startswith(("git:", "commit:"))
            ):
                reasons.append("commit_ref_not_bound_to_source_refs")
                _record_real_finding(
                    findings,
                    "GOV_MUT_REAL_RECORD_COMMIT_REF_UNBOUND",
                    "Real governed-mutation records must bind the resolved commit ref to their source refs.",
                    record_id=record_id,
                    subject_kind="commit_ref",
                )
            if str(row.get("commit_subject") or "") != str(
                commit_evidence.get("commit_subject") or ""
            ):
                reasons.append("commit_subject_mismatch")
                _record_real_finding(
                    findings,
                    "GOV_MUT_REAL_RECORD_COMMIT_SUBJECT_MISMATCH",
                    "Real governed-mutation record subject labels must match the resolved git commit subject.",
                    record_id=record_id,
                    subject_kind="commit_subject",
                )
            if commit_evidence.get("scope_verified") is not True:
                reasons.append("commit_scope_unverified")
                _record_real_finding(
                    findings,
                    "GOV_MUT_REAL_RECORD_COMMIT_SCOPE_UNVERIFIED",
                    "Real governed-mutation records must cite a commit that touches the validator source or focused test scope.",
                    record_id=record_id,
                    subject_kind="commit_scope",
                )
        if (
            len(source_refs) < 4
            or not any(ref.startswith(("git:", "commit:")) for ref in source_refs)
            or not any("mission_transaction" in ref for ref in source_refs)
            or not any("work_landing" in ref for ref in source_refs)
            or not any("task_ledger" in ref or "Work Ledger" in ref for ref in source_refs)
        ):
            reasons.append("source_refs_incomplete")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_SOURCE_REFS_INCOMPLETE",
                "Real governed-mutation records must cite git, mission-transaction, work-landing, and ledger refs.",
                record_id=record_id,
                subject_kind="source_refs",
            )
        if (
            not policy_refs
            or set(policy_refs) != set(derived_policy_refs)
            or not set(policy_refs).issubset(proposal_policy_refs)
            or _visible_allowing_verdict_count(
                policy_refs,
                verdict_index,
                proposal_id,
                proof_index,
                public_root=public_root,
            )
            < 2
            or any(
                not _verdict_row_resolves_proof(
                    verdict_index.get(ref, {}),
                    proof_index,
                    proposal_id,
                    public_root=public_root,
                )
                for ref in policy_refs
            )
        ):
            reasons.append("policy_verdict_ref_invalid")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_POLICY_REF_INVALID",
                "Real governed-mutation records must cite visible policy verdict refs for the same proposal.",
                record_id=record_id,
                subject_kind="policy_verdict_refs",
            )
        if (
            not proof_refs
            or set(proof_refs) != set(derived_proof_refs)
            or not set(proof_refs).issubset(proposal_proof_refs)
            or not _proposal_has_evidence(
                proof_refs,
                proof_index,
                proposal_id,
                public_root=public_root,
            )
        ):
            reasons.append("proof_cell_ref_invalid")
            _record_real_finding(
                findings,
                "GOV_MUT_REAL_RECORD_PROOF_REF_INVALID",
                "Real governed-mutation records must cite proof-cell refs for the same proposal.",
                record_id=record_id,
                subject_kind="proof_cell_refs",
            )

        side_effect_class = str(proposal.get("side_effect_class") or "")
        if side_effect_class in {"scoped_config_write", "rollback"}:
            side_effect = side_effect_index.get(proposal_id, {})
            if (
                row.get("side_effect_logged") is not True
                or not side_effect_ref
                or side_effect_ref != str(side_effect.get("diff_ref") or "")
                or side_effect.get("side_effect_logged") is not True
                or not side_effect_record_digest
            ):
                reasons.append("side_effect_unlogged")
                _record_real_finding(
                    findings,
                    "GOV_MUT_REAL_RECORD_SIDE_EFFECT_UNLOGGED",
                    "Real governed-mutation records must bind to the logged side-effect diff for the same proposal.",
                    record_id=record_id,
                    subject_kind="side_effect_ref",
                )
            rollback = rollback_index.get(rollback_ref, {})
            if (
                not rollback_ref
                or row.get("rollback_receipt_present") is not True
                or str(rollback.get("proposal_id") or "") != proposal_id
                or rollback.get("rollback_status") != PASS
                or not rollback_record_digest
            ):
                reasons.append("rollback_receipt_missing")
                _record_real_finding(
                    findings,
                    "GOV_MUT_REAL_RECORD_ROLLBACK_RECEIPT_MISSING",
                    "Real governed-mutation records must bind to a passing rollback receipt for the same proposal.",
                    record_id=record_id,
                    subject_kind="rollback_ref",
                )
            elif rollback_ref != derived_rollback_ref:
                rollback_refs_match = False
                reasons.append("rollback_ref_not_derived")
                _record_real_finding(
                    findings,
                    "GOV_MUT_REAL_RECORD_ROLLBACK_REF_INVALID",
                    "Real governed-mutation records must use the rollback receipt ref derived from passing rollback evidence for the same proposal.",
                    record_id=record_id,
                    subject_kind="rollback_ref",
                )
            elif not _rollback_row_resolves_records(
                rollback,
                side_effect_index,
                cold_replay_index,
                proposal_id,
            ):
                rollback_refs_match = False
                reasons.append("rollback_receipt_not_record_resolved")
                _record_real_finding(
                    findings,
                    "GOV_MUT_REAL_RECORD_ROLLBACK_REF_INVALID",
                    "Real governed-mutation rollback refs must resolve side-effect and cold-replay row records for the same proposal.",
                    record_id=record_id,
                    subject_kind="rollback_ref",
                )

        declared_refs_match_derived = (
            set(proof_refs) == set(derived_proof_refs)
            and set(policy_refs) == set(derived_policy_refs)
            and rollback_refs_match
        )
        if not reasons:
            accepted_proposal_ids.add(proposal_id)
        accepted.append(
            {
                "record_id": record_id,
                "proposal_id": proposal_id,
                "source_record_class": record_class,
                "commit_ref": commit_ref,
                "resolved_commit_ref": str(commit_evidence.get("commit_ref") or ""),
                "commit_scope_verified": commit_evidence.get("scope_verified")
                is True,
                "verified_commit_touched_paths": commit_evidence.get(
                    "matched_required_paths",
                    [],
                ),
                "source_ref_count": len(source_refs),
                "proof_cell_refs": proof_refs,
                "policy_verdict_refs": policy_refs,
                "side_effect_diff_ref": side_effect_ref,
                "rollback_receipt_ref": rollback_ref,
                "resolved_proof_cell_record_refs": [
                    _input_record_ref(
                        input_dir,
                        "proof_evidence_cells.json",
                        "proof_cell_id",
                        ref,
                        public_root=public_root,
                    )
                    for ref in proof_refs
                    if ref in proof_index
                ],
                "resolved_policy_verdict_record_refs": [
                    _input_record_ref(
                        input_dir,
                        "policy_verdicts.json",
                        "verdict_id",
                        ref,
                        public_root=public_root,
                    )
                    for ref in policy_refs
                    if ref in verdict_index
                ],
                "resolved_side_effect_record_ref": _input_record_ref(
                    input_dir,
                    "side_effect_ledger.json",
                    "proposal_id",
                    proposal_id,
                    public_root=public_root,
                )
                if side_effect_record_digest
                else "",
                "resolved_rollback_record_ref": _input_record_ref(
                    input_dir,
                    "rollback_receipts.json",
                    "rollback_receipt_ref",
                    rollback_ref,
                    public_root=public_root,
                )
                if rollback_record_digest
                else "",
                "resolved_cold_replay_record_refs": cold_replay_record_refs,
                "resolved_record_digests": {
                    "proof_cells": proof_record_digests,
                    "policy_verdicts": policy_record_digests,
                    "side_effect": side_effect_record_digest,
                    "rollback": rollback_record_digest,
                    "cold_replay": cold_replay_record_digests,
                },
                "derived_proof_cell_refs": derived_proof_refs,
                "derived_policy_verdict_refs": derived_policy_refs,
                "derived_rollback_receipt_ref": derived_rollback_ref,
                "declared_refs_match_derived": declared_refs_match_derived,
                "anti_bake_proof_status": REAL_RECORD_ANTI_BAKE_PROOF_STATUS
                if not reasons and declared_refs_match_derived
                else "blocked",
                "real_evidence_ref_digest": _real_record_ref_digest(
                    record_id=record_id,
                    proposal_id=proposal_id,
                    commit_evidence=commit_evidence,
                    derived_proof_refs=derived_proof_refs,
                    derived_policy_refs=derived_policy_refs,
                    derived_rollback_ref=derived_rollback_ref,
                    resolved_record_digests={
                        "proof_cells": proof_record_digests,
                        "policy_verdicts": policy_record_digests,
                        "side_effect": side_effect_record_digest,
                        "rollback": rollback_record_digest,
                        "cold_replay": cold_replay_record_digests,
                    },
                ),
                "computed_verdict": "accepted_real_governed_mutation_record"
                if not reasons
                else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_redacted": True,
            }
        )

    missing_proposal_ids = sorted(set(proposals) - accepted_proposal_ids)
    anti_bake_positive_record_count = sum(
        1
        for row in accepted
        if row["computed_verdict"] == "accepted_real_governed_mutation_record"
        and row["commit_scope_verified"] is True
        and row["declared_refs_match_derived"] is True
        and row["anti_bake_proof_status"] == REAL_RECORD_ANTI_BAKE_PROOF_STATUS
    )
    if missing_proposal_ids:
        findings.append(
            {
                **_finding(
                    "GOV_MUT_REAL_RECORD_FLOOR_MISSING",
                    "Every positive governed-mutation proposal must bind to a public-safe real repo record.",
                    case_id="real_governed_mutation_record_floor",
                    subject_id="governed_mutation_records",
                    subject_kind="governed_mutation_records",
                ),
                "missing_proposal_ids": missing_proposal_ids,
            }
        )
    return {
        "status": PASS if not findings and records else "blocked",
        "real_record_count": len(records),
        "accepted_real_record_count": len(accepted_proposal_ids),
        "accepted_real_record_proposal_ids": sorted(accepted_proposal_ids),
        "missing_real_record_proposal_ids": missing_proposal_ids,
        "real_record_status": REAL_RECORD_IMPORT_STATUS
        if not findings and records
        else "blocked",
        "anti_bake_positive_mutation_proof_status": (
            REAL_RECORD_ANTI_BAKE_PROOF_STATUS
            if records and anti_bake_positive_record_count == len(proposals)
            else "blocked"
        ),
        "anti_bake_positive_record_count": anti_bake_positive_record_count,
        "governed_mutation_record_rows": sorted(
            accepted,
            key=lambda row: row["record_id"],
        ),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_side_effect_ledger(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "side_effects")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if row.get("synthetic_side_effect") is not True:
            reasons.append("not_synthetic")
        if row.get("side_effect_logged") is not True:
            reasons.append("not_logged")
        if row.get("reversible") is not True:
            reasons.append("not_reversible")
        if not row.get("diff_ref"):
            reasons.append("missing_diff_ref")
        if not row.get("rollback_receipt_ref"):
            reasons.append("missing_rollback_receipt_ref")
        if row.get("live_cloud_account_touched") is True:
            reasons.append("live_cloud_account_touched")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "side_effect_id": str(row.get("side_effect_id") or ""),
                "proposal_id": row.get("proposal_id"),
                "side_effect_class": row.get("side_effect_class"),
                "diff_ref": row.get("diff_ref"),
                "rollback_receipt_ref": row.get("rollback_receipt_ref"),
                "synthetic_side_effect": row.get("synthetic_side_effect") is True,
                "computed_verdict": "accepted_side_effect_metadata"
                if not reasons
                else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) != 2 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_SIDE_EFFECT_LEDGER_FLOOR_MISSING",
                "Positive fixture must expose two logged, reversible synthetic side-effect refs: scoped write and rollback.",
                case_id="side_effect_floor",
                subject_id="side_effect_ledger",
                subject_kind="side_effect_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "side_effect_count": len(rows),
        "logged_side_effect_count": sum(
            1 for row in accepted if row["computed_verdict"] == "accepted_side_effect_metadata"
        ),
        "side_effect_rows": sorted(accepted, key=lambda row: row["side_effect_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_rollback_receipts(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "rollback_receipts")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if row.get("rollback_status") != PASS:
            reasons.append("rollback_not_pass")
        if not row.get("rollback_receipt_ref"):
            reasons.append("missing_rollback_receipt_ref")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        if row.get("irreversible_mutation_authorized") is not False:
            reasons.append("irreversible_authority_overclaim")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "rollback_id": str(row.get("rollback_id") or ""),
                "proposal_id": row.get("proposal_id"),
                "rollback_status": row.get("rollback_status"),
                "rollback_receipt_ref": row.get("rollback_receipt_ref"),
                "evidence_ref_count": len(_strings(row.get("evidence_refs"))),
                "computed_verdict": "accepted_rollback_receipt"
                if not reasons
                else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) < 2 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_ROLLBACK_RECEIPT_FLOOR_MISSING",
                "Positive fixture must carry passing rollback receipts for scoped write and rollback verification.",
                case_id="rollback_floor",
                subject_id="rollback_receipts",
                subject_kind="rollback_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "rollback_receipt_count": len(rows),
        "rollback_pass_count": sum(
            1 for row in accepted if row["computed_verdict"] == "accepted_rollback_receipt"
        ),
        "rollback_rows": sorted(accepted, key=lambda row: row["rollback_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_cold_replay(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "cold_replays")
    findings: list[dict[str, Any]] = []
    passing = [
        row
        for row in rows
        if row.get("status") == PASS
        and row.get("body_redacted") is True
        and row.get("private_ref_metadata_only") is True
    ]
    if len(passing) < 3:
        findings.append(
            _finding(
                "GOV_MUT_COLD_REPLAY_FLOOR_MISSING",
                "Positive fixture must include redacted cold replay receipts for read-only, write, and rollback proposal paths.",
                case_id="cold_replay_floor",
                subject_id="cold_replay",
                subject_kind="cold_replay_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "cold_replay_count": len(rows),
        "cold_replay_pass_count": len(passing),
        "cold_replay_rows": [
            {
                "replay_id": str(row.get("replay_id") or ""),
                "proposal_id": str(row.get("proposal_id") or ""),
                "status": row.get("status"),
                "evidence_refs": _strings(row.get("evidence_refs")),
                "body_redacted": row.get("body_redacted") is True,
                "private_ref_metadata_only": row.get("private_ref_metadata_only") is True,
            }
            for row in rows
        ],
        "findings": findings,
        "observed_negative_cases": {},
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    private_scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    projection = validate_projection_protocol(payloads["projection_protocol"])
    auth_policy = validate_authorization_policy(payloads["authorization_policy"])
    proof_cells = validate_proof_evidence_cells(payloads["proof_evidence_cells"])
    verdicts = validate_policy_verdicts(
        payloads["policy_verdicts"],
        payloads["proof_evidence_cells"],
        public_root=public_root,
    )
    proposals = validate_mutation_proposals(
        payloads["mutation_proposals"],
        payloads["proof_evidence_cells"],
        payloads["policy_verdicts"],
        payloads["side_effect_ledger"],
        payloads["rollback_receipts"],
        payloads["cold_replay"],
        negative_payloads,
        public_root=public_root,
    )
    governed_records = validate_governed_mutation_records(
        payloads["governed_mutation_records"],
        payloads["mutation_proposals"],
        payloads["proof_evidence_cells"],
        payloads["policy_verdicts"],
        payloads["side_effect_ledger"],
        payloads["rollback_receipts"],
        payloads["cold_replay"],
        input_dir,
        public_root,
    )
    proposals = _proposal_result_with_real_record_gate(proposals, governed_records)
    side_effects = validate_side_effect_ledger(payloads["side_effect_ledger"])
    rollbacks = validate_rollback_receipts(payloads["rollback_receipts"])
    cold_replay = validate_cold_replay(payloads["cold_replay"])
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_governed_mutation_authorization_bundle",
    )
    source_open_body_imports = _source_open_body_import_summary(source_modules)

    observed = _merge_observed(
        projection,
        auth_policy,
        proof_cells,
        verdicts,
        proposals,
        governed_records,
        side_effects,
        rollbacks,
        cold_replay,
        source_modules,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        auth_policy,
        proof_cells,
        verdicts,
        proposals,
        governed_records,
        side_effects,
        rollbacks,
        cold_replay,
        source_modules,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and auth_policy["status"] == PASS
        and proof_cells["status"] == PASS
        and verdicts["status"] == PASS
        and proposals["status"] == PASS
        and governed_records["status"] == PASS
        and side_effects["status"] == PASS
        and rollbacks["status"] == PASS
        and cold_replay["status"] == PASS
        and (
            input_mode != "exported_governed_mutation_authorization_bundle"
            or source_modules["status"] == PASS
        )
        else "blocked"
    )
    return {
        "schema_version": "proof_derived_governed_mutation_authorization_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id")
        if isinstance(bundle_manifest, dict)
        else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_replacement_refs": projection["public_replacement_refs"],
        "authorization_policy_id": auth_policy["policy_id"],
        "allowed_action_classes": auth_policy["allowed_action_classes"],
        "minimum_independent_verdicts": auth_policy["minimum_independent_verdicts"],
        "proof_cell_count": proof_cells["proof_cell_count"],
        "accepted_proof_cell_count": proof_cells["accepted_proof_cell_count"],
        "policy_verdict_count": verdicts["policy_verdict_count"],
        "visible_policy_verdict_count": verdicts["visible_policy_verdict_count"],
        "proposal_consensus_counts": verdicts["proposal_consensus_counts"],
        "proposal_count": proposals["proposal_count"],
        "authorized_mutation_count": proposals["authorized_mutation_count"],
        "write_or_rollback_count": proposals["write_or_rollback_count"],
        "action_classes": proposals["action_classes"],
        "real_record_count": governed_records["real_record_count"],
        "accepted_real_record_count": governed_records["accepted_real_record_count"],
        "missing_real_record_proposal_ids": governed_records[
            "missing_real_record_proposal_ids"
        ],
        "real_record_status": governed_records["real_record_status"],
        "anti_bake_positive_mutation_proof_status": governed_records[
            "anti_bake_positive_mutation_proof_status"
        ],
        "anti_bake_positive_record_count": governed_records[
            "anti_bake_positive_record_count"
        ],
        "side_effect_count": side_effects["side_effect_count"],
        "logged_side_effect_count": side_effects["logged_side_effect_count"],
        "rollback_receipt_count": rollbacks["rollback_receipt_count"],
        "rollback_pass_count": rollbacks["rollback_pass_count"],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_imports": source_modules,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "governed_mutation_record_rows": governed_records[
            "governed_mutation_record_rows"
        ],
        "proof_cell_rows": proof_cells["proof_cell_rows"],
        "policy_verdict_rows": verdicts["policy_verdict_rows"],
        "proposal_rows": proposals["proposal_rows"],
        "side_effect_rows": side_effects["side_effect_rows"],
        "rollback_rows": rollbacks["rollback_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "proof_derived_governed_mutation_authorization_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "proof_derived_governed_mutation_authorization_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "standing_credentials_rejected_before_authorization",
                "count": result["authorized_mutation_count"],
                "authority": "mutation authority derives from proof cells and visible verdicts, not credential possession",
            },
            {
                "mechanic_id": "consensus_before_ephemeral_identity",
                "count": result["visible_policy_verdict_count"],
                "authority": "at least two visible verdict refs precede synthetic execution identity refs",
            },
            {
                "mechanic_id": "side_effects_need_diff_and_rollback",
                "count": result["logged_side_effect_count"],
                "authority": "write and rollback proposal metadata needs logged diffs and rollback receipts",
            },
            {
                "mechanic_id": "cold_replay_before_claim_admission",
                "count": result["cold_replay_pass_count"],
                "authority": "governed-mutation language requires cold replay receipts",
            },
        ],
        "proposal_rows": result["proposal_rows"],
        "proof_cell_rows": result["proof_cell_rows"],
        "policy_verdict_rows": result["policy_verdict_rows"],
        "side_effect_rows": result["side_effect_rows"],
        "rollback_rows": result["rollback_rows"],
        "cold_replay_rows": result["cold_replay_rows"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "real_record_status": result["real_record_status"],
        "real_record_count": result["real_record_count"],
        "accepted_real_record_count": result["accepted_real_record_count"],
        "anti_bake_positive_mutation_proof_status": result[
            "anti_bake_positive_mutation_proof_status"
        ],
        "anti_bake_positive_record_count": result[
            "anti_bake_positive_record_count"
        ],
        "governed_mutation_record_rows": result["governed_mutation_record_rows"],
        "body_redacted": True,
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
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
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": (
            "proof_derived_governed_mutation_authorization_result_receipt_v1"
        ),
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": (
            "proof_derived_governed_mutation_authorization_validation_receipt_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "proposal_count": result["proposal_count"],
        "authorized_mutation_count": result["authorized_mutation_count"],
        "proof_cell_count": result["proof_cell_count"],
        "visible_policy_verdict_count": result["visible_policy_verdict_count"],
        "logged_side_effect_count": result["logged_side_effect_count"],
        "rollback_pass_count": result["rollback_pass_count"],
        "cold_replay_pass_count": result["cold_replay_pass_count"],
        "real_record_status": result["real_record_status"],
        "real_record_count": result["real_record_count"],
        "accepted_real_record_count": result["accepted_real_record_count"],
        "missing_real_record_proposal_ids": result["missing_real_record_proposal_ids"],
        "anti_bake_positive_mutation_proof_status": result[
            "anti_bake_positive_mutation_proof_status"
        ],
        "anti_bake_positive_record_count": result[
            "anti_bake_positive_record_count"
        ],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": (
            "proof_derived_governed_mutation_authorization_fixture_acceptance_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "real_record_status": result["real_record_status"],
        "real_record_count": result["real_record_count"],
        "accepted_real_record_count": result["accepted_real_record_count"],
        "missing_real_record_proposal_ids": result["missing_real_record_proposal_ids"],
        "anti_bake_positive_mutation_proof_status": result[
            "anti_bake_positive_mutation_proof_status"
        ],
        "anti_bake_positive_record_count": result[
            "anti_bake_positive_record_count"
        ],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "authorization_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs."
        "proof_derived_governed_mutation_authorization run"
    ),
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


def run_authorization_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "proof_derived_governed_mutation_authorization run-authorization-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    source = Path(input_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if reuse_fresh_receipt:
        cached = _fresh_authorization_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_governed_mutation_authorization_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": (
            "exported_governed_mutation_authorization_bundle_validation_result_v1"
        ),
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return read_json_strict(bundle_path)


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    private_scan_payload = result.get("private_state_scan")
    private_scan = private_scan_payload if isinstance(private_scan_payload, dict) else {}
    source_imports = result.get("source_open_body_imports")
    source_body_floor = source_imports if isinstance(source_imports, dict) else {}
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
        "governed_mutation_authorization": {
            "proposal_count": result.get("proposal_count"),
            "authorized_mutation_count": result.get("authorized_mutation_count"),
            "write_or_rollback_count": result.get("write_or_rollback_count"),
            "proof_cell_count": result.get("proof_cell_count"),
            "accepted_proof_cell_count": result.get("accepted_proof_cell_count"),
            "real_record_status": result.get("real_record_status"),
            "real_record_count": result.get("real_record_count"),
            "accepted_real_record_count": result.get("accepted_real_record_count"),
            "anti_bake_positive_mutation_proof_status": result.get(
                "anti_bake_positive_mutation_proof_status"
            ),
            "anti_bake_positive_record_count": result.get(
                "anti_bake_positive_record_count"
            ),
            "policy_verdict_count": result.get("policy_verdict_count"),
            "visible_policy_verdict_count": result.get(
                "visible_policy_verdict_count"
            ),
            "logged_side_effect_count": result.get("logged_side_effect_count"),
            "rollback_pass_count": result.get("rollback_pass_count"),
            "cold_replay_pass_count": result.get("cold_replay_pass_count"),
        },
        "negative_case_coverage": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "observed_negative_case_count": len(
                result.get("observed_negative_cases") or {}
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
        },
        "validation": {
            "private_state_blocking_hit_count": private_scan.get(
                "blocking_hit_count"
            ),
            "bundle_id": result.get("bundle_id"),
            "source_module_manifest_status": result.get(
                "source_module_manifest_status"
            ),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "body_material_status": source_body_floor.get("body_material_status"),
            "body_material_count": source_body_floor.get("body_material_count", 0),
            "body_material_classes": source_body_floor.get(
                "body_material_classes",
                {},
            ),
            "real_record_status": result.get("real_record_status"),
            "missing_real_record_proposal_count": len(
                result.get("missing_real_record_proposal_ids") or []
            ),
        },
        "body_floor": {
            "governed_mutation_record_rows_in_card": False,
            "proof_cell_rows_in_card": False,
            "policy_verdict_rows_in_card": False,
            "proposal_rows_in_card": False,
            "side_effect_rows_in_card": False,
            "rollback_rows_in_card": False,
            "cold_replay_rows_in_card": False,
            "source_module_imports_in_card": False,
            "source_open_body_imports_in_card": False,
            "private_state_scan_in_card": False,
            "authority_ceiling_in_card": False,
            "anti_claim_in_card": False,
            "authorization_board_in_card": False,
        },
        "authority_boundary": {
            "synthetic_receipts_only": False,
            "real_public_safe_record_required": True,
            "live_cloud_account_authorized": False,
            "standing_credentials_authorized": False,
            "source_mutation_authorized": False,
            "irreversible_mutation_authorized": False,
            "policy_after_execution_authorized": False,
            "hidden_policy_votes_authorized": False,
            "provider_calls_authorized": False,
            "benchmark_score_claim_authorized": False,
            "release_authorized": False,
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
    parser = argparse.ArgumentParser(
        prog="proof_derived_governed_mutation_authorization"
    )
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-authorization-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        command = (
            "proof_derived_governed_mutation_authorization run"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-authorization-bundle":
        command = (
            "proof_derived_governed_mutation_authorization "
            f"run-authorization-bundle{card_suffix}"
        )
        result = run_authorization_bundle(
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
