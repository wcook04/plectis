from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_mcp_tool_authority_trace,
)
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "mcp_tool_authority_replay"
FIXTURE_ID = "first_wave.mcp_tool_authority_replay"
VALIDATOR_ID = "validator.microcosm.organs.mcp_tool_authority_replay"

RESULT_NAME = "mcp_tool_authority_replay_result.json"
BOARD_NAME = "mcp_tool_authority_replay_board.json"
VALIDATION_RECEIPT_NAME = "mcp_tool_authority_replay_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "mcp_tool_authority_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_mcp_tool_authority_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "mcp_tool_authority_replay_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "secret_exclusion_scan",
    "public_agent_execution_trace",
    "source_refs",
    "projection_receipt_refs",
    "target_refs",
    "target_symbols",
    "public_runtime_refs",
    "tool_rows",
    "call_rows",
    "tool_result_rows",
    "side_effect_rows",
    "cold_replay_rows",
    "source_module_imports",
    "source_open_body_imports",
    "authority_ceiling",
    "anti_claim",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_mcp_tool_authority_macro_body_landed"
SOURCE_OPEN_BODY_SCHEMA = "mcp_tool_authority_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_standard_body",
        "public_macro_control_plane_body",
    }
)

INPUT_NAMES = (
    "projection_protocol.json",
    "tool_policy.json",
    "tool_manifest.json",
    "tool_calls.json",
    "tool_results.json",
    "side_effect_ledger.json",
    "cold_replay.json",
)
NEGATIVE_INPUT_NAMES = (
    "overbroad_scope.json",
    "hidden_credential_export.json",
    "tool_output_as_instruction.json",
    "unapproved_side_effect.json",
    "live_account_access.json",
    "final_answer_only_grading.json",
    "missing_rollback_receipt.json",
    "unredacted_tool_payload.json",
)

EXPECTED_NEGATIVE_CASES = {
    "overbroad_scope": ["MCP_TOOL_OVERBROAD_SCOPE"],
    "hidden_credential_export": ["MCP_TOOL_HIDDEN_CREDENTIAL_EXPORT"],
    "tool_output_as_instruction": ["MCP_TOOL_OUTPUT_AS_INSTRUCTION"],
    "unapproved_side_effect": ["MCP_TOOL_UNAPPROVED_SIDE_EFFECT"],
    "live_account_access": ["MCP_TOOL_LIVE_ACCOUNT_ACCESS"],
    "final_answer_only_grading": ["MCP_TOOL_FINAL_ANSWER_ONLY_GRADING"],
    "missing_rollback_receipt": ["MCP_TOOL_MISSING_ROLLBACK_RECEIPT"],
    "unredacted_tool_payload": ["MCP_TOOL_UNREDACTED_PAYLOAD_EXPORT"],
}

REQUIRED_TOOL_CLASSES = (
    "readonly_lookup",
    "write_side_effect",
    "untrusted_result",
)
REQUIRED_CALL_FIELDS = (
    "call_id",
    "tool_id",
    "tool_class",
    "capability_scope_ref",
    "call_arguments_hash",
    "approval_token_ref",
    "side_effect_class",
    "result_source_capsule_ref",
    "instruction_data_split_ref",
    "ledger_diff_ref",
    "rollback_receipt_ref",
    "cold_replay_receipt_ref",
    "live_account_access",
    "body_in_receipt",
    "private_ref_metadata_only",
    "untrusted_output_as_instruction",
    "credential_exported",
    "final_answer_only_grading",
)
FORBIDDEN_KEYS = (
    "credential_value",
    "secret_value",
    "token_value",
    "provider_payload",
    "raw_tool_payload",
    "raw_tool_result",
    "private_account_id",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_agent_execution_trace_refactor_over_mcp_tool_authority_policy",
    "live_mcp_account_access_authorized": False,
    "credential_export_authorized": False,
    "untrusted_tool_output_instruction_authorized": False,
    "unapproved_side_effect_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "MCP tool authority replay validates a public trace-backed tool-use contract: "
    "manifest scope, call metadata, approval token refs, side-effect ledger refs, "
    "rollback receipts, untrusted-output instruction/data separation, cold replay, "
    "negative cases, and public agent-execution trace spans. It does not access live MCP accounts, "
    "export credentials or provider payloads, obey tool output as instruction, "
    "mutate source, claim benchmark safety, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


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
    public_root = _public_root_for_path(input_dir)
    return [
        *_input_paths(input_dir, include_negative=include_negative),
        *_source_module_paths(input_dir, public_root=public_root),
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
        "mcp_tool_authority_replay_result_v1"
        if include_negative
        else "exported_mcp_tool_authority_bundle_validation_result_v1"
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
        "schema_version": "mcp_tool_authority_replay_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
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
                    "MCP_TOOL_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported MCP tool-authority bundle must include a source module manifest for copied non-secret macro body material.",
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
                "MCP_TOOL_SOURCE_MODULE_MANIFEST_REQUIRED",
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
                    "MCP_TOOL_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "MCP_TOOL_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "MCP_TOOL_SOURCE_MODULE_COUNT_MISMATCH",
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
                    "MCP_TOOL_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "MCP_TOOL_SOURCE_MODULE_CLASS_REQUIRED",
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
                    "MCP_TOOL_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
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
                    "MCP_TOOL_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        expected_values = {
            str(row.get("sha256") or ""),
            str(row.get("source_sha256") or ""),
            str(row.get("target_sha256") or ""),
        }
        if actual not in expected_values or "" in expected_values:
            findings.append(
                _finding(
                    "MCP_TOOL_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module digest declarations must match the copied target body.",
                    case_id="source_module_manifest_floor",
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
                        "MCP_TOOL_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared MCP tool-authority macro anchors.",
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
            "live_mcp_account_access_authorized": False,
            "credential_or_account_bound_payload_exported": False,
            "raw_tool_payload_exported": False,
            "provider_payload_exported": False,
            "tool_result_body_exported": False,
            "release_authorized": False,
            "benchmark_score_claim_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported MCP tool-authority bundle for copied macro trace, "
            "standard, route-readiness, mission-transaction, and reconstruction "
            "bodies; receipts carry refs, hashes, counts, and verdicts only."
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
    target_refs = _strings(protocol.get("target_refs"))
    target_symbols = _strings(protocol.get("target_symbols"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    verification = protocol.get("body_import_verification", {})
    verification_mode = (
        verification.get("verification_mode") if isinstance(verification, dict) else None
    )
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 5
        or "mcp_tool_authority_replay_compound" not in source_pattern_ids
        or len(projection_receipts) < 2
        or protocol.get("body_import_status")
        != "extension_of_existing_public_refactor_landed"
        or verification_mode != "extension_of_existing_public_refactor"
        or len(target_refs) < 2
        or len(target_symbols) < 2
        or len(public_runtime_refs) < 2
    ):
        findings.append(
            _finding(
                "MCP_TOOL_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, projection receipts, public trace refactor verification, target refs, target symbols, and runtime refs.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if protocol.get("copied_private_tool_payloads") is not False:
        findings.append(
            _finding(
                "MCP_TOOL_PRIVATE_PAYLOAD_COPY_CLAIM",
                "Projection protocol must explicitly deny copying private tool payloads.",
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
        "target_refs": target_refs,
        "target_symbols": target_symbols,
        "public_runtime_refs": public_runtime_refs,
        "body_import_status": protocol.get("body_import_status"),
        "body_import_verification": verification if isinstance(verification, dict) else {},
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_tool_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    allowed_classes = set(_strings(policy.get("allowed_tool_classes")))
    required_fields = set(_strings(policy.get("required_call_fields")))
    findings: list[dict[str, Any]] = []
    if not set(REQUIRED_TOOL_CLASSES).issubset(allowed_classes):
        findings.append(
            _finding(
                "MCP_TOOL_POLICY_CLASSES_INCOMPLETE",
                "Policy must define readonly lookup, write side-effect, and untrusted-result tool classes.",
                case_id="tool_policy_floor",
                subject_id=str(policy.get("policy_id") or "tool_policy"),
                subject_kind="tool_policy",
            )
        )
    if not set(REQUIRED_CALL_FIELDS).issubset(required_fields):
        findings.append(
            _finding(
                "MCP_TOOL_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Policy must require scope, approval, side-effect, result-source, instruction/data split, rollback, cold replay, redaction, and anti-overclaim fields.",
                case_id="tool_policy_floor",
                subject_id=str(policy.get("policy_id") or "tool_policy"),
                subject_kind="tool_policy",
            )
        )
    for field in (
        "live_mcp_account_access_authorized",
        "credential_export_authorized",
        "untrusted_tool_output_instruction_authorized",
        "unapproved_side_effect_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "MCP_TOOL_POLICY_AUTHORITY_OVERCLAIM",
                    "MCP tool authority replay policy cannot authorize live account access, credential export, untrusted output as instruction, unapproved side effects, provider calls, or release.",
                    case_id="tool_policy_floor",
                    subject_id=field,
                    subject_kind="tool_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_tool_classes": sorted(allowed_classes),
        "required_call_fields": sorted(required_fields),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_tool_manifest(payload: object) -> dict[str, Any]:
    tools = _rows(payload, "tools")
    classes = {str(row.get("tool_class") or "") for row in tools}
    findings: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    for row in tools:
        tool_id = str(row.get("tool_id") or "")
        reasons: list[str] = []
        if str(row.get("tool_class") or "") not in REQUIRED_TOOL_CLASSES:
            reasons.append("unknown_tool_class")
        if not row.get("capability_scope_ref"):
            reasons.append("missing_capability_scope_ref")
        if row.get("body_in_receipt") is not False:
            reasons.append("body_in_receipt_not_false")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        manifest_rows.append(
            {
                "tool_id": tool_id,
                "tool_class": str(row.get("tool_class") or ""),
                "capability_scope_ref": row.get("capability_scope_ref"),
                "requires_approval": row.get("requires_approval") is True,
                "requires_rollback_receipt": row.get("requires_rollback_receipt") is True,
                "untrusted_result": row.get("untrusted_result") is True,
                "computed_verdict": "accepted_tool_metadata" if not reasons else "blocked",
                "reason_codes": sorted(reasons),
                "body_in_receipt": False,
            }
        )
    positive_findings = [row for row in manifest_rows if row["reason_codes"]]
    if len(tools) != 3 or not set(REQUIRED_TOOL_CLASSES).issubset(classes) or positive_findings:
        findings.append(
            _finding(
                "MCP_TOOL_MANIFEST_FLOOR_MISSING",
                "Positive manifest must expose exactly three body-free public tool metadata rows: readonly lookup, write side effect, and untrusted result.",
                case_id="tool_manifest_floor",
                subject_id="tool_manifest",
                subject_kind="tool_manifest",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "tool_count": len(tools),
        "tool_classes": sorted(classes),
        "tool_rows": sorted(manifest_rows, key=lambda row: row["tool_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _validate_call_row(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("call_id") or "tool_call")
    call_id = str(row.get("call_id") or case_id)
    subject_kind = "negative_case" if negative else "tool_call"
    missing = [
        field for field in REQUIRED_CALL_FIELDS if field not in row or row.get(field) is None
    ]
    side_effect_class = str(row.get("side_effect_class") or "")
    reasons: list[str] = []
    scope = str(row.get("capability_scope_ref") or "")
    approval = str(row.get("approval_token_ref") or "")
    rollback = str(row.get("rollback_receipt_ref") or "")
    ledger = str(row.get("ledger_diff_ref") or "")
    tool_class = str(row.get("tool_class") or "")

    if (
        row.get("scope_overbroad") is True
        or scope in {"*", "all_tools", "workspace_admin", "account_full_access"}
    ):
        reasons.append("overbroad_scope")
        _record(
            findings,
            observed,
            "MCP_TOOL_OVERBROAD_SCOPE",
            "Tool calls must bind to a narrow capability scope ref before admission.",
            case_id=case_id,
            subject_id=call_id,
            subject_kind=subject_kind,
        )
    if row.get("credential_exported") is True or _has_forbidden_key(row):
        reasons.append("hidden_credential_export")
        _record(
            findings,
            observed,
            "MCP_TOOL_HIDDEN_CREDENTIAL_EXPORT",
            "Public replay cannot export credential values, provider payloads, or hidden account material.",
            case_id=case_id,
            subject_id=call_id,
            subject_kind=subject_kind,
        )
    if row.get("untrusted_output_as_instruction") is True:
        reasons.append("tool_output_as_instruction")
        _record(
            findings,
            observed,
            "MCP_TOOL_OUTPUT_AS_INSTRUCTION",
            "Untrusted tool output must stay data, not become an instruction to the agent.",
            case_id=case_id,
            subject_id=call_id,
            subject_kind=subject_kind,
        )
    if row.get("live_account_access") is True:
        reasons.append("live_account_access")
        _record(
            findings,
            observed,
            "MCP_TOOL_LIVE_ACCOUNT_ACCESS",
                "Public trace refactors cannot call or claim access to live MCP accounts.",
            case_id=case_id,
            subject_id=call_id,
            subject_kind=subject_kind,
        )
    if row.get("final_answer_only_grading") is True:
        reasons.append("final_answer_only_grading")
        _record(
            findings,
            observed,
            "MCP_TOOL_FINAL_ANSWER_ONLY_GRADING",
            "Tool-authority claims require manifest, call, side-effect, rollback, and cold-replay evidence, not final answers alone.",
            case_id=case_id,
            subject_id=call_id,
            subject_kind=subject_kind,
        )
    if side_effect_class in {"write", "external_mutation"}:
        if approval in {"", "not_required", "missing"} or not ledger:
            reasons.append("unapproved_side_effect")
            _record(
                findings,
                observed,
                "MCP_TOOL_UNAPPROVED_SIDE_EFFECT",
                "Write-capable tool calls require approval token refs and side-effect ledger refs.",
                case_id=case_id,
                subject_id=call_id,
                subject_kind=subject_kind,
            )
        if not rollback:
            reasons.append("missing_rollback_receipt")
            _record(
                findings,
                observed,
                "MCP_TOOL_MISSING_ROLLBACK_RECEIPT",
                "Write-capable tool calls require rollback receipt refs before admission.",
                case_id=case_id,
                subject_id=call_id,
                subject_kind=subject_kind,
            )
    if row.get("body_in_receipt") is not False or row.get("private_ref_metadata_only") is not True:
        reasons.append("tool_payload_body_in_receipt")
        _record(
            findings,
            observed,
            "MCP_TOOL_UNREDACTED_PAYLOAD_EXPORT",
            "Tool call payloads must stay out of receipts and private refs must remain metadata-only.",
            case_id=case_id,
            subject_id=call_id,
            subject_kind=subject_kind,
        )
    if missing:
        reasons.append("call_field_missing")
    return {
        "call_id": call_id,
        "tool_id": str(row.get("tool_id") or ""),
        "tool_class": tool_class,
        "capability_scope_ref": scope,
        "call_arguments_hash": row.get("call_arguments_hash"),
        "approval_token_ref": approval,
        "side_effect_class": side_effect_class,
        "result_source_capsule_ref": row.get("result_source_capsule_ref"),
        "instruction_data_split_ref": row.get("instruction_data_split_ref"),
        "ledger_diff_ref": ledger,
        "rollback_receipt_ref": rollback,
        "cold_replay_receipt_ref": row.get("cold_replay_receipt_ref"),
        "computed_verdict": "accepted_tool_call_metadata" if not reasons else "blocked",
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_in_receipt": False,
    }


def validate_tool_calls(
    payload: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows = [
        _validate_call_row(
            row,
            findings=findings,
            observed=observed,
            negative=False,
        )
        for row in _rows(payload, "tool_calls")
    ]
    for row in _negative_rows(negative_payloads, "tool_calls"):
        _validate_call_row(row, findings=findings, observed=observed, negative=True)

    write_side_effects = [
        row
        for row in rows
        if row["side_effect_class"] == "write"
        and row["approval_token_ref"] not in {"", "not_required", "missing"}
        and row["ledger_diff_ref"]
        and row["rollback_receipt_ref"]
    ]
    untrusted_results = [
        row for row in rows if row["tool_class"] == "untrusted_result"
    ]
    positive_findings = [row for row in rows if row["reason_codes"]]
    floor_blocked = (
        len(rows) != 3
        or len(write_side_effects) != 1
        or len(untrusted_results) != 1
        or positive_findings
    )
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "MCP_TOOL_CALL_FLOOR_MISSING",
                "Public MCP authority bundle must include three scoped calls with one approved write side effect and one untrusted result.",
                case_id="tool_call_floor",
                subject_id="tool_calls",
                subject_kind="tool_call_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked else "blocked",
        "call_count": len(rows),
        "write_side_effect_count": len(write_side_effects),
        "untrusted_result_count": len(untrusted_results),
        "call_rows": sorted(rows, key=lambda row: row["call_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_tool_results(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "tool_results")
    findings: list[dict[str, Any]] = []
    output_ignored = [
        row
        for row in rows
        if row.get("untrusted_output") is True
        and row.get("output_instruction_ignored") is True
        and row.get("body_in_receipt") is False
        and row.get("private_ref_metadata_only") is True
    ]
    if not output_ignored:
        findings.append(
            _finding(
                "MCP_TOOL_RESULT_UNTRUSTED_OUTPUT_GATE_MISSING",
                "Public MCP authority bundle must show untrusted tool output treated as data and ignored as instruction.",
                case_id="tool_result_floor",
                subject_id="tool_results",
                subject_kind="tool_result_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "tool_result_count": len(rows),
        "output_instruction_ignored_count": len(output_ignored),
        "tool_result_rows": [
            {
                "result_id": str(row.get("result_id") or ""),
                "call_id": str(row.get("call_id") or ""),
                "source_capsule_ref": row.get("source_capsule_ref"),
                "untrusted_output": row.get("untrusted_output") is True,
                "output_instruction_ignored": row.get("output_instruction_ignored") is True,
                "body_in_receipt": row.get("body_in_receipt") is False,
                "private_ref_metadata_only": row.get("private_ref_metadata_only") is True,
            }
            for row in rows
        ],
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_side_effect_ledger(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "side_effects")
    findings: list[dict[str, Any]] = []
    approved = [
        row
        for row in rows
        if row.get("side_effect_class") == "write"
        and row.get("approval_token_ref")
        and row.get("ledger_diff_ref")
        and row.get("rollback_receipt_ref")
        and row.get("body_in_receipt") is False
    ]
    if len(approved) != 1:
        findings.append(
            _finding(
                "MCP_TOOL_SIDE_EFFECT_LEDGER_FLOOR_MISSING",
                "Public MCP authority bundle must expose one approved write side effect with ledger diff and rollback refs.",
                case_id="side_effect_floor",
                subject_id="side_effect_ledger",
                subject_kind="side_effect_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "side_effect_count": len(rows),
        "approved_side_effect_count": len(approved),
        "rollback_receipt_count": sum(1 for row in rows if row.get("rollback_receipt_ref")),
        "side_effect_rows": [
            {
                "side_effect_id": str(row.get("side_effect_id") or ""),
                "call_id": str(row.get("call_id") or ""),
                "side_effect_class": row.get("side_effect_class"),
                "approval_token_ref": row.get("approval_token_ref"),
                "ledger_diff_ref": row.get("ledger_diff_ref"),
                "rollback_receipt_ref": row.get("rollback_receipt_ref"),
                "body_in_receipt": row.get("body_in_receipt") is False,
            }
            for row in rows
        ],
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
        and row.get("body_in_receipt") is False
        and row.get("private_ref_metadata_only") is True
    ]
    if len(passing) < 3:
        findings.append(
            _finding(
                "MCP_TOOL_COLD_REPLAY_FLOOR_MISSING",
                "Public MCP authority bundle must include body-free cold replay receipts for readonly, write, and untrusted-output paths.",
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
                "call_id": str(row.get("call_id") or ""),
                "status": row.get("status"),
                "evidence_refs": _strings(row.get("evidence_refs")),
                "body_in_receipt": row.get("body_in_receipt") is False,
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
    secret_scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )

    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    projection = validate_projection_protocol(payloads["projection_protocol"])
    tool_policy = validate_tool_policy(payloads["tool_policy"])
    manifest = validate_tool_manifest(payloads["tool_manifest"])
    calls = validate_tool_calls(payloads["tool_calls"], negative_payloads)
    results = validate_tool_results(payloads["tool_results"])
    side_effects = validate_side_effect_ledger(payloads["side_effect_ledger"])
    cold_replay = validate_cold_replay(payloads["cold_replay"])
    public_trace = build_public_mcp_tool_authority_trace(input_dir)
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_mcp_tool_authority_bundle",
    )
    source_open_body_imports = _source_open_body_import_summary(source_modules)

    observed = _merge_observed(
        projection,
        tool_policy,
        manifest,
        calls,
        results,
        side_effects,
        cold_replay,
        source_modules,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        tool_policy,
        manifest,
        calls,
        results,
        side_effects,
        cold_replay,
        source_modules,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    source_module_ok = (
        source_modules["status"] == PASS
        if input_mode == "exported_mcp_tool_authority_bundle"
        else source_modules["status"] in {PASS, "not_present"}
    )
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and tool_policy["status"] == PASS
        and manifest["status"] == PASS
        and calls["status"] == PASS
        and results["status"] == PASS
        and side_effects["status"] == PASS
        and cold_replay["status"] == PASS
        and public_trace["status"] == PASS
        and source_module_ok
        else "blocked"
    )
    copied_body_landed = source_open_body_imports["status"] == PASS
    return {
        "schema_version": "mcp_tool_authority_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "public_agent_execution_trace": public_trace,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "target_symbols": projection["target_symbols"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "body_import_status": (
            SOURCE_MODULE_IMPORT_STATUS
            if copied_body_landed
            else projection["body_import_status"]
        ),
        "body_import_classification": (
            "copied_non_secret_public_mcp_tool_authority_macro_body_import"
            if copied_body_landed
            else str(
                projection["body_import_verification"].get("classification")
                or projection["body_import_verification"].get("verification_mode")
                or ""
            )
        ),
        "product_path_role": (
            "copied_non_secret_macro_body_plus_public_agent_execution_trace_refactor"
            if copied_body_landed
            else "source_faithful_public_agent_execution_trace_refactor"
        ),
        "body_import_verification": projection["body_import_verification"],
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_imports": source_modules,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "tool_policy_id": tool_policy["policy_id"],
        "allowed_tool_classes": tool_policy["allowed_tool_classes"],
        "tool_count": manifest["tool_count"],
        "tool_classes": manifest["tool_classes"],
        "call_count": calls["call_count"],
        "write_side_effect_count": calls["write_side_effect_count"],
        "untrusted_result_count": calls["untrusted_result_count"],
        "tool_result_count": results["tool_result_count"],
        "output_instruction_ignored_count": results["output_instruction_ignored_count"],
        "side_effect_count": side_effects["side_effect_count"],
        "approved_side_effect_count": side_effects["approved_side_effect_count"],
        "rollback_receipt_count": side_effects["rollback_receipt_count"],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "tool_rows": manifest["tool_rows"],
        "call_rows": calls["call_rows"],
        "tool_result_rows": results["tool_result_rows"],
        "side_effect_rows": side_effects["side_effect_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "mcp_tool_authority_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "mcp_tool_authority_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "manifest_scopes_before_call_admission",
                "count": result["tool_count"],
                "authority": "tool_manifest_rows_bind_each_tool_to_a_narrow_scope_ref",
            },
            {
                "mechanic_id": "write_side_effect_requires_approval_and_rollback",
                "count": result["approved_side_effect_count"],
                "authority": "write_capable_calls_need_approval_ledger_and_rollback_refs",
            },
            {
                "mechanic_id": "untrusted_output_stays_data",
                "count": result["output_instruction_ignored_count"],
                "authority": "tool_result_output_cannot_become_agent_instruction",
            },
            {
                "mechanic_id": "cold_replay_before_claim_admission",
                "count": result["cold_replay_pass_count"],
                "authority": "tool_authority_language_requires_cold_replay_receipts",
            },
        ],
        "tool_rows": result["tool_rows"],
        "call_rows": result["call_rows"],
        "side_effect_rows": result["side_effect_rows"],
        "cold_replay_rows": result["cold_replay_rows"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_verification": result["body_import_verification"],
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
        "schema_version": "mcp_tool_authority_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "mcp_tool_authority_replay_validation_receipt_v1",
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
        "tool_count": result["tool_count"],
        "call_count": result["call_count"],
        "write_side_effect_count": result["write_side_effect_count"],
        "approved_side_effect_count": result["approved_side_effect_count"],
        "output_instruction_ignored_count": result["output_instruction_ignored_count"],
        "rollback_receipt_count": result["rollback_receipt_count"],
        "cold_replay_pass_count": result["cold_replay_pass_count"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "mcp_tool_authority_replay_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "mcp_tool_authority_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.mcp_tool_authority_replay run",
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


def run_tool_authority_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.mcp_tool_authority_replay "
        "run-tool-authority-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, out)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_mcp_tool_authority_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_mcp_tool_authority_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    secret_scan = result.get("secret_exclusion_scan")
    scan = secret_scan if isinstance(secret_scan, dict) else {}
    source_imports = result.get("source_open_body_imports")
    source_body_floor = source_imports if isinstance(source_imports, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "tool_authority": {
            "tool_count": result.get("tool_count"),
            "tool_classes": result.get("tool_classes", []),
            "call_count": result.get("call_count"),
            "write_side_effect_count": result.get("write_side_effect_count"),
            "approved_side_effect_count": result.get("approved_side_effect_count"),
            "untrusted_result_count": result.get("untrusted_result_count"),
            "output_instruction_ignored_count": result.get(
                "output_instruction_ignored_count"
            ),
            "rollback_receipt_count": result.get("rollback_receipt_count"),
            "cold_replay_pass_count": result.get("cold_replay_pass_count"),
        },
        "validation": {
            "missing_negative_case_count": len(result.get("missing_negative_cases") or []),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "secret_exclusion_blocking_hit_count": scan.get("blocking_hit_count"),
        },
        "body_floor": {
            "body_in_receipt": False,
            "body_text_in_receipt": False,
            "secret_exclusion_scan_in_card": False,
            "tool_rows_in_card": False,
            "call_rows_in_card": False,
            "source_open_body_imports_in_card": False,
        },
        "source_body_floor": {
            "source_module_manifest_status": result.get("source_module_manifest_status"),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "body_material_status": source_body_floor.get("body_material_status"),
            "body_material_count": source_body_floor.get("body_material_count", 0),
            "body_material_classes": source_body_floor.get("body_material_classes", {}),
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
        "authority_boundary": {
            "live_mcp_account_access_authorized": False,
            "credential_export_authorized": False,
            "untrusted_tool_output_instruction_authorized": False,
            "unapproved_side_effect_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp_tool_authority_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-tool-authority-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.mcp_tool_authority_replay run "
            f"--input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-tool-authority-bundle":
        command = (
            "python -m microcosm_core.organs.mcp_tool_authority_replay "
            f"run-tool-authority-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_tool_authority_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
