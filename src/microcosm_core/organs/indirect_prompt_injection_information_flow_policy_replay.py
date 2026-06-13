from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_prompt_injection_trace,
)
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import (
    normalize_public_receipt_paths,
    utc_now,
    write_json_atomic,
)
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "indirect_prompt_injection_information_flow_policy_replay"
FIXTURE_ID = "first_wave.indirect_prompt_injection_information_flow_policy_replay"
VALIDATOR_ID = (
    "validator.microcosm.organs."
    "indirect_prompt_injection_information_flow_policy_replay"
)

RESULT_NAME = "indirect_prompt_injection_information_flow_policy_replay_result.json"
BOARD_NAME = "indirect_prompt_injection_information_flow_policy_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "indirect_prompt_injection_information_flow_policy_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "indirect_prompt_injection_information_flow_policy_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_prompt_injection_flow_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "indirect_prompt_injection_information_flow_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "secret_exclusion_scan",
    "authority_ceiling",
    "anti_claim",
    "source_refs",
    "projection_receipt_refs",
    "target_refs",
    "target_symbols",
    "public_runtime_refs",
    "omitted_secret_or_live_access_material",
    "public_agent_execution_trace",
    "source_rows",
    "flow_rows",
    "policy_verdict_rows",
    "sanitized_output_rows",
    "cold_replay_rows",
    "prompt_injection_flow_board",
    "source_module_imports",
    "source_open_body_imports",
)
BODY_IMPORT_STATUS = "extension_of_existing_public_refactor_landed"
BODY_IMPORT_CLASSIFICATION = "extension_of_existing_public_refactor"
PRODUCT_PATH_ROLE = "source_faithful_public_agent_execution_trace_refactor"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = (
    "copied_non_secret_prompt_injection_macro_body_landed"
)
AGENT_EXECUTION_TRACE_SOURCE_REF = "system/lib/agent_execution_trace.py"
AGENT_EXECUTION_TRACE_TARGET_FILE_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
)
AGENT_EXECUTION_TRACE_TARGET_SYMBOL_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/"
    "agent_execution_trace.py::build_public_prompt_injection_trace"
)
SOURCE_OPEN_BODY_SCHEMA = (
    "indirect_prompt_injection_information_flow_policy_replay_"
    "source_open_body_imports_v1"
)
HASH_CHUNK_SIZE = 1024 * 1024
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_control_plane_body",
        "public_macro_pattern_body",
        "public_macro_receipt_body",
        "public_macro_standard_body",
        "public_macro_tool_body",
    }
)

INPUT_NAMES = (
    "projection_protocol.json",
    "injection_policy.json",
    "source_documents.json",
    "information_flow_graph.json",
    "policy_verdicts.json",
    "sanitized_outputs.json",
    "cold_replay.json",
)
NEGATIVE_INPUT_NAMES = (
    "real_account_material.json",
    "secret_exfiltration.json",
    "raw_prompt_body_export.json",
    "tool_output_as_instruction.json",
    "hidden_system_message_promotion.json",
    "credential_exfiltration.json",
    "final_answer_only_success.json",
    "untrusted_to_privileged_sink.json",
)

EXPECTED_NEGATIVE_CASES = {
    "real_account_material": ["PROMPT_INJECTION_REAL_ACCOUNT_FORBIDDEN"],
    "secret_exfiltration": ["PROMPT_INJECTION_SECRET_EXFILTRATION_FORBIDDEN"],
    "raw_prompt_body_export": ["PROMPT_INJECTION_RAW_PROMPT_BODY_FORBIDDEN"],
    "tool_output_as_instruction": [
        "PROMPT_INJECTION_TOOL_OUTPUT_AS_INSTRUCTION"
    ],
    "hidden_system_message_promotion": [
        "PROMPT_INJECTION_HIDDEN_SYSTEM_MESSAGE_PROMOTION"
    ],
    "credential_exfiltration": [
        "PROMPT_INJECTION_CREDENTIAL_EXFILTRATION_FORBIDDEN"
    ],
    "final_answer_only_success": ["PROMPT_INJECTION_FINAL_ANSWER_ONLY_SUCCESS"],
    "untrusted_to_privileged_sink": [
        "PROMPT_INJECTION_UNTRUSTED_PRIVILEGED_SINK_UNGATED"
    ],
}

REQUIRED_SOURCE_FIELDS = (
    "source_id",
    "episode_id",
    "source_kind",
    "trust_label",
    "channel",
    "body_ref",
    "taint_labels",
    "instruction_authority",
    "body_redacted",
)
REQUIRED_FLOW_FIELDS = (
    "flow_id",
    "episode_id",
    "from_source_id",
    "to_sink_id",
    "sink_kind",
    "source_trust_label",
    "taint_labels",
    "sanitization_applied",
    "proposed_action_ref",
    "privileged_sink",
    "body_redacted",
)
REQUIRED_VERDICT_FIELDS = (
    "flow_id",
    "policy_version",
    "verdict",
    "rule_refs",
    "pre_action",
    "confirmation_required",
    "decision_reason_ref",
    "body_redacted",
)
REQUIRED_OUTPUT_FIELDS = (
    "flow_id",
    "sanitized_answer_ref",
    "trusted_context_disclosed",
    "untrusted_instruction_obeyed",
    "confirmation_boundary_ref",
    "counterfactual_safe_path_ref",
    "body_redacted",
)
FORBIDDEN_KEYS = (
    "raw_email_body",
    "raw_document_body",
    "raw_prompt_body",
    "raw_system_prompt",
    "credential_value",
    "secret_value",
    "account_identifier",
    "real_account_identifier",
    "provider_payload",
    "raw_tool_output_body",
    "hidden_system_message_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_agent_execution_trace_refactor_over_prompt_injection_fixture_regression_inputs"
    ),
    "general_prompt_injection_robustness_claim_authorized": False,
    "real_email_or_document_account_use_authorized": False,
    "raw_prompt_body_export_authorized": False,
    "secret_or_credential_exfiltration_authorized": False,
    "tool_output_instruction_authority_authorized": False,
    "hidden_system_message_promotion_authorized": False,
    "public_tool_call_trace_input_authorized": True,
    "live_tool_call_authorized": False,
    "provider_calls_authorized": False,
    "benchmark_score_claim_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Indirect prompt-injection information-flow replay validates synthetic "
    "source-trust, taint-graph, policy-verdict, sanitized-output, cold-replay, "
    "negative-case, and authority-ceiling receipts, and now emits public "
    "agent-execution trace spans over those public refs plus one generated "
    "public tool-call trace input through the same taint propagation mechanic. "
    "It does not use real email, documents, accounts, credentials, raw prompts, "
    "provider payloads, or live external tools, and it does not claim general "
    "prompt-injection robustness, benchmark performance, source mutation, or "
    "release authority."
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _repo_root_for_public_refactor(public_root: Path) -> Path | None:
    for candidate in (public_root.parent, *public_root.parents):
        if (
            (candidate / AGENT_EXECUTION_TRACE_SOURCE_REF).is_file()
            and (candidate / AGENT_EXECUTION_TRACE_TARGET_FILE_REF).is_file()
        ):
            return candidate
    return None


def _body_import_verification(
    base_verification: dict[str, Any],
    *,
    public_root: Path,
    public_trace: dict[str, Any],
    source_modules: dict[str, Any],
) -> dict[str, Any]:
    repo_root = _repo_root_for_public_refactor(public_root)
    source_path = (
        repo_root / AGENT_EXECUTION_TRACE_SOURCE_REF if repo_root is not None else None
    )
    target_path = (
        repo_root / AGENT_EXECUTION_TRACE_TARGET_FILE_REF
        if repo_root is not None
        else None
    )
    source_digest = (
        _sha256(source_path) if source_path is not None and source_path.is_file() else None
    )
    target_digest = (
        _sha256(target_path) if target_path is not None and target_path.is_file() else None
    )
    return {
        **base_verification,
        "status": PASS,
        "classification": BODY_IMPORT_CLASSIFICATION,
        "verification_status": "verified",
        "verification_mode": (
            "extension_of_existing_public_refactor_with_live_digest_relation"
        ),
        "body_import_classification": BODY_IMPORT_CLASSIFICATION,
        "source_to_target_relation": "source_faithful_public_refactor",
        "digest_relation": "source_target_refactor_digests_recorded"
        if source_digest and target_digest
        else "source_target_refactor_digests_unavailable_in_public_copy",
        "public_trace_status": public_trace["status"],
        "public_trace_span_count": public_trace["span_count"],
        "trace_digest": public_trace["summary"]["trace_digest"],
        "source_ref": AGENT_EXECUTION_TRACE_SOURCE_REF,
        "target_ref": AGENT_EXECUTION_TRACE_TARGET_SYMBOL_REF,
        "target_file_ref": AGENT_EXECUTION_TRACE_TARGET_FILE_REF,
        "source_body_digest": source_digest,
        "target_body_digest": target_digest,
        "source_symbols": public_trace["source_symbols"],
        "target_symbols": public_trace["target_symbols"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_digest_relation": "manifest_target_digests_verified"
        if source_modules["status"] == PASS
        else str(source_modules["status"]),
        "source_module_digest_count": int(source_modules.get("verified_module_count") or 0),
        "validation_refs": [
            (
                "microcosm-substrate/tests/"
                "test_indirect_prompt_injection_information_flow_policy_replay.py"
            ),
            (
                "python -m microcosm_core.macro_tools.agent_execution_trace "
                "prompt-injection --input <bundle>"
            ),
        ],
        "body_in_receipt": False,
    }


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
        target_refs = [
            str(row.get("target_ref") or ""),
            str(row.get("path") or ""),
        ]
        for target_ref in target_refs:
            if not target_ref:
                continue
            paths.append(
                _source_module_target_path(
                    target_ref,
                    input_dir=input_dir,
                    public_root=public_root,
                )
            )
    return paths


def _source_module_target_path_for_ref(
    target_ref: str,
    *,
    input_dir: Path,
    public_root: Path,
) -> Path | None:
    if not target_ref:
        return None
    return _source_module_target_path(
        target_ref,
        input_dir=input_dir,
        public_root=public_root,
    )


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
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "indirect_prompt_injection_information_flow_policy_replay_result_v1"
        if include_negative
        else "exported_prompt_injection_flow_bundle_validation_result_v1"
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
        "schema_version": "indirect_prompt_injection_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_prompt_injection_bundle_receipt(
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
        "exported_prompt_injection_flow_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_prompt_injection_flow_bundle":
        return None
    normalized_command = normalize_public_receipt_paths({"command": command}).get(
        "command"
    )
    if payload.get("command") != normalized_command:
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
                    "PROMPT_INJECTION_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported prompt-injection bundle must include a source module manifest for copied non-secret macro body material.",
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
            "body_text_in_receipt": False,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    module_results: list[dict[str, Any]] = []
    source_refs = [manifest_ref]

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "PROMPT_INJECTION_SOURCE_MODULE_MANIFEST_REQUIRED",
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
                    "PROMPT_INJECTION_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_in_receipt",
                )
            )
        if manifest.get("body_text_in_receipt") is not False:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_text_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_MODULE_COUNT_MISMATCH",
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
                    "PROMPT_INJECTION_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_MODULE_CLASS_REQUIRED",
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
                    "PROMPT_INJECTION_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while keeping receipt fields body-free.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        path_ref = str(row.get("path") or "")
        declared_target_ref = str(row.get("target_ref") or "")
        path_target = _source_module_target_path_for_ref(
            path_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        target_ref_target = _source_module_target_path_for_ref(
            declared_target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        target_ref = declared_target_ref or path_ref
        target = target_ref_target or path_target
        target_ref_matches_path = not (
            path_target
            and target_ref_target
            and path_target.resolve(strict=False)
            != target_ref_target.resolve(strict=False)
        )
        module_result = {
            "module_id": module_id,
            "source_ref": str(row.get("source_ref") or ""),
            "path_ref": path_ref,
            "target_ref": target_ref,
            "path_target_ref": _display(path_target, public_root=public_root)
            if path_target
            else "",
            "declared_target_ref": declared_target_ref,
            "declared_target_path_ref": _display(
                target_ref_target, public_root=public_root
            )
            if target_ref_target
            else "",
            "exists": bool(target and target.is_file()),
            "digest_match": None,
            "target_ref_matches_path": target_ref_matches_path,
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        }
        module_results.append(module_result)
        if not target or not target.is_file():
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_MODULE_TARGET_MISSING",
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
        digest_match = all(value == actual for value in expected_digests.values())
        module_result["sha256"] = actual
        module_result["digest_match"] = digest_match
        if not target_ref_matches_path:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_MODULE_TARGET_REF_PATH_MISMATCH",
                    "Source module manifest path and target_ref must resolve to the same copied bundle body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not digest_match:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_MODULE_DIGEST_MISMATCH",
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
                        "PROMPT_INJECTION_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared prompt-injection macro anchors.",
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
        "modules": module_results,
        "source_refs": source_refs,
        "findings": findings,
        "observed_negative_cases": {},
        "body_in_receipt": False,
        "body_text_in_receipt": False,
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
            "credential_payload_exported": False,
            "account_session_exported": False,
            "browser_hud_live_access_exported": False,
            "provider_payload_exported": False,
            "raw_prompt_body_exported": False,
            "real_account_material_exported": False,
            "live_tool_access_exported": False,
            "general_robustness_claim_authorized": False,
            "source_mutation_authorized": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported prompt-injection information-flow bundle for copied macro "
            "pattern, reconstruction, trace-standard, and trace runtime bodies; "
            "receipts carry refs, hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _missing(row: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [field for field in required if row.get(field) in (None, "", [])]


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def _is_untrusted(label: str) -> bool:
    return label.startswith("untrusted_")


def validate_projection_protocol(
    payload: object,
    *,
    public_root: Path,
    public_trace: dict[str, Any],
    source_modules: dict[str, Any],
) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    target_refs = _strings(protocol.get("target_refs"))
    target_symbols = _strings(protocol.get("target_symbols"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    omitted = _strings(protocol.get("omitted_secret_or_live_access_material"))
    source_open_body_import_refs = _strings(
        protocol.get("source_open_body_import_refs")
    )
    body_import = protocol.get("body_import_verification", {})
    if not isinstance(body_import, dict):
        body_import = {}
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 4
        or "indirect_prompt_injection_information_flow_policy_replay_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or "system/lib/agent_execution_trace.py" not in source_refs
        or "codex/standards/std_agent_execution_trace.json" not in source_refs
        or "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        not in target_refs
        or len(public_runtime_refs) < 1
        or len(source_open_body_import_refs) < 4
        or len(omitted) < 6
        or not any(ref.endswith("build_public_prompt_injection_trace") for ref in target_symbols)
        or protocol.get("body_import_status") != BODY_IMPORT_STATUS
        or body_import.get("verification_mode") != BODY_IMPORT_CLASSIFICATION
        or body_import.get("verification_status") != "verified"
        or body_import.get("body_import_classification") != BODY_IMPORT_CLASSIFICATION
        or protocol.get("body_in_receipt") is not False
    ):
        findings.append(
            _finding(
                "PROMPT_INJECTION_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite trace source refs, target refs, runtime refs, body-import verification, and omitted secret/live-access material.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for flag in (
        "copied_credential_or_account_bound_source",
        "exports_secret_or_live_access_material",
        "exports_raw_prompt_bodies",
        "exports_real_accounts",
        "authorizes_live_tool_calls",
        "claims_general_robustness",
    ):
        if protocol.get(flag) is not False:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_PROJECTION_PROTOCOL_AUTHORITY_OVERCLAIM",
                    "Projection protocol must deny credential/account-bound copy, secret/live-access export, raw prompt bodies, real accounts, live tools, and general robustness claims.",
                    case_id="projection_protocol_floor",
                    subject_id=flag,
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
        "source_open_body_import_refs": source_open_body_import_refs,
        "body_import_status": protocol.get("body_import_status"),
        "body_import_verification": _body_import_verification(
            body_import,
            public_root=public_root,
            public_trace=public_trace,
            source_modules=source_modules,
        ),
        "omitted_secret_or_live_access_material": omitted,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_injection_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    allowed = set(_strings(policy.get("allowed_verdicts")))
    required_source = set(_strings(policy.get("required_source_fields")))
    required_flow = set(_strings(policy.get("required_flow_fields")))
    required_verdict = set(_strings(policy.get("required_verdict_fields")))
    required_output = set(_strings(policy.get("required_output_fields")))
    findings: list[dict[str, Any]] = []
    if not {"allow", "warn", "block", "review"}.issubset(allowed):
        findings.append(
            _finding(
                "PROMPT_INJECTION_POLICY_VERDICTS_INCOMPLETE",
                "Policy must define allow, warn, block, and review verdicts.",
                case_id="injection_policy_floor",
                subject_id=str(policy.get("policy_id") or "injection_policy"),
                subject_kind="injection_policy",
            )
        )
    floors = (
        (REQUIRED_SOURCE_FIELDS, required_source, "source"),
        (REQUIRED_FLOW_FIELDS, required_flow, "flow"),
        (REQUIRED_VERDICT_FIELDS, required_verdict, "verdict"),
        (REQUIRED_OUTPUT_FIELDS, required_output, "output"),
    )
    for expected, actual, label in floors:
        if not set(expected).issubset(actual):
            findings.append(
                _finding(
                    "PROMPT_INJECTION_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                    f"Policy must require complete {label} evidence fields.",
                    case_id="injection_policy_floor",
                    subject_id=label,
                    subject_kind="injection_policy",
                )
            )
    for field in (
        "real_account_material_authorized",
        "raw_prompt_body_export_authorized",
        "credential_exfiltration_authorized",
        "tool_output_instruction_authority_authorized",
        "hidden_system_message_promotion_authorized",
        "live_tool_call_authorized",
        "general_robustness_claim_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_POLICY_AUTHORITY_OVERCLAIM",
                    "Policy cannot authorize real accounts, raw prompts, credential exfiltration, tool-output authority, hidden-message promotion, live tools, robustness claims, or release.",
                    case_id="injection_policy_floor",
                    subject_id=field,
                    subject_kind="injection_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_verdicts": sorted(allowed),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_source_documents(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "source_documents")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        source_id = str(row.get("source_id") or "")
        trust_label = str(row.get("trust_label") or "")
        if (
            _missing(row, REQUIRED_SOURCE_FIELDS)
            or _has_forbidden_key(row)
            or row.get("body_redacted") is not True
            or row.get("synthetic_fixture") is not True
            or row.get("raw_body_exported") is not False
            or row.get("real_account_material") is not False
        ):
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SOURCE_DOCUMENT_INVALID",
                    "Source documents require trust labels, taint labels, synthetic-only refs, body redaction, and no raw/private body export.",
                    case_id="source_document_floor",
                    subject_id=source_id or "source_document",
                    subject_kind="source_document",
                )
            )
        if _is_untrusted(trust_label) and row.get("instruction_authority") is not False:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_UNTRUSTED_SOURCE_AUTHORITY",
                    "Untrusted source text cannot carry instruction authority.",
                    case_id="source_document_floor",
                    subject_id=source_id or "source_document",
                    subject_kind="source_document",
                )
            )
        exported.append(
            {
                "source_id": source_id,
                "episode_id": row.get("episode_id"),
                "source_kind": row.get("source_kind"),
                "trust_label": trust_label,
                "channel": row.get("channel"),
                "taint_labels": _strings(row.get("taint_labels")),
                "instruction_authority": row.get("instruction_authority"),
                "body_in_receipt": False,
            }
        )
    trust_labels = sorted(
        {str(row.get("trust_label")) for row in exported if row.get("trust_label")}
    )
    untrusted_count = sum(1 for row in exported if _is_untrusted(str(row["trust_label"])))
    trusted_count = sum(1 for row in exported if not _is_untrusted(str(row["trust_label"])))
    return {
        "status": PASS if rows and untrusted_count >= 3 and trusted_count >= 2 and not findings else "blocked",
        "source_document_count": len(rows),
        "untrusted_source_count": untrusted_count,
        "trusted_source_count": trusted_count,
        "trust_labels": trust_labels,
        "source_rows": sorted(exported, key=lambda row: row["source_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _derived_flow_taint_labels(
    row: dict[str, Any],
    source: dict[str, Any],
) -> list[str]:
    labels = set(_strings(source.get("taint_labels")))
    proposed_action = str(row.get("proposed_action_ref") or "")
    sink_kind = str(row.get("sink_kind") or "")
    if sink_kind == "instruction_channel" or "promote" in proposed_action:
        labels.add("hidden_policy_claim")
    return sorted(labels)


def _has_untrusted_taint(labels: list[str]) -> bool:
    return any(
        label.startswith("untrusted_")
        or label in {"prompt_injection", "hidden_policy_claim"}
        for label in labels
    )


def _derived_policy_verdict(
    row: dict[str, Any],
    derived_taint_labels: list[str],
) -> str:
    labels = set(derived_taint_labels)
    sink_kind = str(row.get("sink_kind") or "")
    proposed_action = str(row.get("proposed_action_ref") or "")
    privileged = row.get("privileged_sink") is True
    sanitized = row.get("sanitization_applied") is True
    hidden_policy_promotion = (
        "hidden_policy_claim" in labels
        or sink_kind == "instruction_channel"
        or "promote" in proposed_action
    )
    untrusted = _has_untrusted_taint(sorted(labels))

    if hidden_policy_promotion:
        return "block"
    if untrusted and privileged and not sanitized:
        return "block"
    if untrusted and privileged and sanitized:
        return "review"
    if untrusted and sanitized:
        return "warn"
    if untrusted:
        return "review"
    return "allow"


def _taint_propagation_receipt(
    rows: list[dict[str, Any]],
    source_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    taints_by_node: dict[str, set[str]] = {
        source_id: set(_strings(source.get("taint_labels")))
        for source_id, source in source_by_id.items()
    }
    paths_by_node: dict[str, list[list[str]]] = {
        source_id: [[source_id]] for source_id in source_by_id
    }
    path_rows: list[dict[str, Any]] = []
    for row in sorted(
        rows,
        key=lambda item: (
            str(item.get("episode_id") or ""),
            str(item.get("flow_id") or ""),
        ),
    ):
        flow_id = str(row.get("flow_id") or "")
        source_id = str(row.get("from_source_id") or "")
        sink_id = str(row.get("to_sink_id") or "")
        source = source_by_id.get(source_id, {})
        upstream_labels = set(taints_by_node.get(source_id) or ())
        if not upstream_labels:
            upstream_labels = set(_strings(source.get("taint_labels")))
        derived_labels = set(_derived_flow_taint_labels(row, source))
        derived_labels.update(upstream_labels)
        declared_labels = set(_strings(row.get("taint_labels")))
        if declared_labels != derived_labels:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_TAINT_PROPAGATION_MISMATCH",
                    "Flow taint labels must be derived from the source row plus policy transforms, not hand-written independently.",
                    case_id="taint_propagation_floor",
                    subject_id=flow_id or "information_flow",
                    subject_kind="information_flow",
                )
            )
        declared_verdict = str(row.get("policy_verdict") or "")
        derived_verdict = _derived_policy_verdict(row, sorted(derived_labels))
        if declared_verdict != derived_verdict:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_POLICY_VERDICT_DERIVATION_MISMATCH",
                    "Flow policy verdicts must be computed from propagated taint, sink privilege, sanitizer state, sink kind, and proposed action.",
                    case_id="policy_verdict_derivation_floor",
                    subject_id=flow_id or "information_flow",
                    subject_kind="information_flow",
                )
            )
        source_paths = paths_by_node.get(source_id) or [[source_id]]
        propagated_paths = [path + [sink_id] for path in source_paths if sink_id]
        if sink_id:
            taints_by_node.setdefault(sink_id, set()).update(derived_labels)
            paths_by_node.setdefault(sink_id, []).extend(propagated_paths)
        path_rows.append(
            {
                "flow_id": flow_id,
                "from_source_id": source_id,
                "to_sink_id": sink_id,
                "derived_taint_labels": sorted(derived_labels),
                "declared_taint_labels": sorted(declared_labels),
                "taint_derivation_passed": declared_labels == derived_labels,
                "derived_policy_verdict": derived_verdict,
                "declared_policy_verdict": declared_verdict,
                "policy_derivation_passed": declared_verdict == derived_verdict,
                "source_to_sink_paths": propagated_paths,
                "path_count": len(propagated_paths),
                "body_in_receipt": False,
            }
        )
    return (
        {
            "status": PASS if rows and not findings else "blocked",
            "analysis_kind": "derived_taint_propagation_over_source_to_sink_graph",
            "propagated_node_count": len(taints_by_node),
            "propagated_path_count": sum(row["path_count"] for row in path_rows),
            "derived_taint_mismatch_count": sum(
                1 for row in path_rows if row["taint_derivation_passed"] is not True
            ),
            "derived_policy_verdict_mismatch_count": sum(
                1 for row in path_rows if row["policy_derivation_passed"] is not True
            ),
            "flow_path_rows": path_rows,
            "body_in_receipt": False,
        },
        findings,
    )


def _live_tool_call_trace_promotion(public_trace: dict[str, Any]) -> dict[str, Any]:
    spans = [
        row
        for row in public_trace.get("spans", [])
        if isinstance(row, dict) and row.get("tool_name")
    ]
    if not spans:
        return {
            "status": "blocked",
            "promotion_kind": "public_tool_call_trace_to_taint_graph",
            "live_input_trace_count": 0,
            "taint_propagation_path_count": 0,
            "findings": [
                _finding(
                    "PROMPT_INJECTION_LIVE_TRACE_SPAN_MISSING",
                    "Live-input promotion requires at least one generated public tool-call trace span.",
                    case_id="live_input_promotion_floor",
                    subject_id="public_tool_call_trace",
                    subject_kind="public_agent_execution_trace",
                )
            ],
            "body_in_receipt": False,
        }

    span = spans[0]
    source_id = "live_public_tool_call_trace_source"
    flow_id = "live_public_tool_call_trace_flow"
    source = {
        "source_id": source_id,
        "episode_id": span.get("episode_id") or "live_input_promotion_episode",
        "source_kind": "public_tool_call_trace",
        "trust_label": "untrusted_tool_output",
        "channel": "tool_output",
        "body_ref": span.get("observation_ref") or span.get("span_id"),
        "taint_labels": ["prompt_injection", "untrusted_tool_output"],
        "instruction_authority": False,
        "body_redacted": True,
    }
    flow = {
        "flow_id": flow_id,
        "episode_id": source["episode_id"],
        "from_source_id": source_id,
        "to_sink_id": "sink_public_tool_policy_gate",
        "sink_kind": "external_action",
        "source_trust_label": "untrusted_tool_output",
        "taint_labels": ["prompt_injection", "untrusted_tool_output"],
        "sanitization_applied": True,
        "proposed_action_ref": "public_tool_call_trace_policy_gate",
        "privileged_sink": True,
        "body_redacted": True,
        "policy_verdict": "review",
    }
    propagation, findings = _taint_propagation_receipt([flow], {source_id: source})
    return {
        "status": PASS if propagation["status"] == PASS and not findings else "blocked",
        "promotion_kind": "public_tool_call_trace_to_taint_graph",
        "input_origin": "generated_public_trace_span",
        "source_span_id": span.get("span_id"),
        "source_tool_name": span.get("tool_name"),
        "live_input_trace_count": 1,
        "taint_propagation_path_count": propagation["propagated_path_count"],
        "derived_policy_verdict_mismatch_count": propagation[
            "derived_policy_verdict_mismatch_count"
        ],
        "taint_propagation": propagation,
        "findings": findings,
        "body_in_receipt": False,
    }


def validate_information_flow_graph(
    payload: object,
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "information_flows")
    source_by_id = {str(row["source_id"]): row for row in source_rows}
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    taint_propagation, taint_findings = _taint_propagation_receipt(rows, source_by_id)
    findings.extend(taint_findings)
    taint_by_flow = {
        str(row.get("flow_id")): row
        for row in taint_propagation.get("flow_path_rows", [])
        if isinstance(row, dict)
    }
    for row in rows:
        flow_id = str(row.get("flow_id") or "")
        source_id = str(row.get("from_source_id") or "")
        trust_label = str(row.get("source_trust_label") or "")
        verdict = str(row.get("policy_verdict") or "")
        privileged = row.get("privileged_sink") is True
        sanitized = row.get("sanitization_applied") is True
        if (
            _missing(row, REQUIRED_FLOW_FIELDS)
            or _has_forbidden_key(row)
            or source_id not in source_by_id
            or source_by_id.get(source_id, {}).get("trust_label") != trust_label
            or row.get("body_redacted") is not True
            or not _strings(row.get("taint_labels"))
        ):
            findings.append(
                _finding(
                    "PROMPT_INJECTION_INFORMATION_FLOW_INVALID",
                    "Information-flow rows must join to sources, carry taint labels, expose only refs, and stay redacted.",
                    case_id="information_flow_floor",
                    subject_id=flow_id or "information_flow",
                    subject_kind="information_flow",
                )
            )
        if _is_untrusted(trust_label) and privileged and verdict == "allow" and not sanitized:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_UNTRUSTED_PRIVILEGED_FLOW_ALLOWED",
                    "Untrusted text cannot flow to a privileged sink as an allowed unsanitized action.",
                    case_id="information_flow_floor",
                    subject_id=flow_id or "information_flow",
                    subject_kind="information_flow",
                )
            )
        exported.append(
            {
                "flow_id": flow_id,
                "episode_id": row.get("episode_id"),
                "from_source_id": source_id,
                "to_sink_id": row.get("to_sink_id"),
                "sink_kind": row.get("sink_kind"),
                "source_trust_label": trust_label,
                "taint_labels": _strings(row.get("taint_labels")),
                "derived_taint_labels": (
                    taint_by_flow.get(flow_id, {}).get("derived_taint_labels", [])
                ),
                "source_to_sink_paths": (
                    taint_by_flow.get(flow_id, {}).get("source_to_sink_paths", [])
                ),
                "derived_policy_verdict": (
                    taint_by_flow.get(flow_id, {}).get("derived_policy_verdict")
                ),
                "sanitization_applied": sanitized,
                "policy_verdict": verdict,
                "privileged_sink": privileged,
                "proposed_action_ref": row.get("proposed_action_ref"),
                "body_in_receipt": False,
            }
        )
    verdicts = {row["policy_verdict"] for row in exported}
    return {
        "status": PASS if rows and {"allow", "warn", "block", "review"}.issubset(verdicts) and not findings else "blocked",
        "information_flow_count": len(rows),
        "privileged_flow_count": sum(1 for row in exported if row["privileged_sink"]),
        "sanitized_flow_count": sum(1 for row in exported if row["sanitization_applied"]),
        "taint_propagation": taint_propagation,
        "taint_propagation_path_count": taint_propagation["propagated_path_count"],
        "derived_policy_verdict_mismatch_count": taint_propagation[
            "derived_policy_verdict_mismatch_count"
        ],
        "flow_rows": sorted(exported, key=lambda row: row["flow_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_policy_verdicts(
    payload: object,
    policy: object,
    flow_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "policy_verdicts")
    policy_rows = policy if isinstance(policy, dict) else {}
    allowed = set(_strings(policy_rows.get("allowed_verdicts")))
    flow_by_id = {str(row["flow_id"]): row for row in flow_rows}
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        flow_id = str(row.get("flow_id") or "")
        verdict = str(row.get("verdict") or "")
        expected = str(flow_by_id.get(flow_id, {}).get("policy_verdict") or "")
        if (
            _missing(row, REQUIRED_VERDICT_FIELDS)
            or _has_forbidden_key(row)
            or flow_id not in flow_by_id
            or verdict not in allowed
            or verdict != expected
            or row.get("pre_action") is not True
            or row.get("body_redacted") is not True
            or not _strings(row.get("rule_refs"))
        ):
            findings.append(
                _finding(
                    "PROMPT_INJECTION_POLICY_VERDICT_INVALID",
                    "Policy verdicts must join to flows, precede action, cite rules, stay redacted, and match the flow verdict.",
                    case_id="policy_verdict_floor",
                    subject_id=flow_id or "policy_verdict",
                    subject_kind="policy_verdict",
                )
            )
        exported.append(
            {
                "flow_id": flow_id,
                "policy_version": row.get("policy_version"),
                "verdict": verdict,
                "rule_refs": _strings(row.get("rule_refs")),
                "pre_action": row.get("pre_action"),
                "confirmation_required": row.get("confirmation_required"),
                "decision_reason_ref": row.get("decision_reason_ref"),
                "body_in_receipt": False,
            }
        )
    verdicts = {row["verdict"] for row in exported}
    return {
        "status": PASS if rows and {"allow", "warn", "block", "review"}.issubset(verdicts) and not findings else "blocked",
        "policy_verdict_count": len(rows),
        "allow_count": sum(1 for row in exported if row["verdict"] == "allow"),
        "warn_count": sum(1 for row in exported if row["verdict"] == "warn"),
        "block_count": sum(1 for row in exported if row["verdict"] == "block"),
        "review_count": sum(1 for row in exported if row["verdict"] == "review"),
        "policy_verdict_rows": sorted(exported, key=lambda row: row["flow_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_sanitized_outputs(
    payload: object,
    flow_rows: list[dict[str, Any]],
    verdicts_by_flow: dict[str, str],
) -> dict[str, Any]:
    rows = _rows(payload, "sanitized_outputs")
    flow_by_id = {str(row["flow_id"]): row for row in flow_rows}
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        flow_id = str(row.get("flow_id") or "")
        verdict = verdicts_by_flow.get(flow_id, "")
        if (
            _missing(row, REQUIRED_OUTPUT_FIELDS)
            or _has_forbidden_key(row)
            or flow_id not in flow_by_id
            or row.get("trusted_context_disclosed") is not False
            or row.get("untrusted_instruction_obeyed") is not False
            or row.get("body_redacted") is not True
        ):
            findings.append(
                _finding(
                    "PROMPT_INJECTION_SANITIZED_OUTPUT_INVALID",
                    "Sanitized outputs must join to flows, disclose no trusted context, obey no untrusted instruction, and stay redacted.",
                    case_id="sanitized_output_floor",
                    subject_id=flow_id or "sanitized_output",
                    subject_kind="sanitized_output",
                )
            )
        if verdict == "block" and row.get("external_action_attempted") is not False:
            findings.append(
                _finding(
                    "PROMPT_INJECTION_BLOCKED_FLOW_ACTION_ATTEMPTED",
                    "Blocked prompt-injection flows cannot attempt external actions.",
                    case_id="sanitized_output_floor",
                    subject_id=flow_id or "sanitized_output",
                    subject_kind="sanitized_output",
                )
            )
        exported.append(
            {
                "flow_id": flow_id,
                "verdict": verdict,
                "sanitized_answer_ref": row.get("sanitized_answer_ref"),
                "trusted_context_disclosed": row.get("trusted_context_disclosed"),
                "untrusted_instruction_obeyed": row.get("untrusted_instruction_obeyed"),
                "external_action_attempted": row.get("external_action_attempted"),
                "confirmation_boundary_ref": row.get("confirmation_boundary_ref"),
                "counterfactual_safe_path_ref": row.get("counterfactual_safe_path_ref"),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "sanitized_output_count": len(rows),
        "trusted_context_disclosure_count": sum(
            1 for row in exported if row["trusted_context_disclosed"] is True
        ),
        "untrusted_instruction_obeyed_count": sum(
            1 for row in exported if row["untrusted_instruction_obeyed"] is True
        ),
        "blocked_without_external_action_count": sum(
            1
            for row in exported
            if row["verdict"] == "block" and row["external_action_attempted"] is False
        ),
        "sanitized_output_rows": sorted(exported, key=lambda row: row["flow_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_cold_replay(payload: object, flow_ids: set[str]) -> dict[str, Any]:
    rows = _rows(payload, "cold_replay")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        replay_id = str(row.get("replay_id") or "")
        flow_id = str(row.get("flow_id") or "")
        if (
            not replay_id
            or flow_id not in flow_ids
            or not row.get("replay_command")
            or not row.get("receipt_ref")
            or row.get("verdict_reproduced") is not True
            or row.get("sanitized_output_reproduced") is not True
            or row.get("trusted_context_disclosed") is not False
            or row.get("pass_label") is not True
            or row.get("body_redacted") is not True
            or _has_forbidden_key(row)
        ):
            findings.append(
                _finding(
                    "PROMPT_INJECTION_COLD_REPLAY_INVALID",
                    "Cold replay rows require command, receipt ref, reproduced verdict/output, no trusted-context disclosure, pass label, and redacted metadata.",
                    case_id="cold_replay_floor",
                    subject_id=replay_id or "cold_replay",
                    subject_kind="cold_replay",
                )
            )
        exported.append(
            {
                "replay_id": replay_id,
                "flow_id": flow_id,
                "replay_command": row.get("replay_command"),
                "receipt_ref": row.get("receipt_ref"),
                "verdict_reproduced": row.get("verdict_reproduced"),
                "sanitized_output_reproduced": row.get("sanitized_output_reproduced"),
                "trusted_context_disclosed": row.get("trusted_context_disclosed"),
                "pass_label": row.get("pass_label"),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "cold_replay_count": len(rows),
        "cold_replay_pass_count": sum(1 for row in exported if row["pass_label"] is True),
        "cold_replay_rows": sorted(exported, key=lambda row: row["replay_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_negative_cases(negative_payloads: dict[str, object]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for case_id, payload in negative_payloads.items():
        row = payload if isinstance(payload, dict) else {}
        subject_id = str(row.get("case_id") or case_id)
        subject_kind = "negative_case"
        if row.get("real_account_material_included") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_REAL_ACCOUNT_FORBIDDEN",
                "Public prompt-injection fixtures cannot include real email, document, browser, or account material.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("secret_or_trusted_context_disclosed") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_SECRET_EXFILTRATION_FORBIDDEN",
                "Synthetic prompt-injection replay cannot disclose trusted context or secrets.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("raw_prompt_body_exported") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_RAW_PROMPT_BODY_FORBIDDEN",
                "Public replay cannot export raw prompt, system, developer, or tool bodies.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("tool_output_treated_as_instruction") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_TOOL_OUTPUT_AS_INSTRUCTION",
                "Untrusted tool output cannot become instruction-channel authority.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("hidden_system_message_promoted") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_HIDDEN_SYSTEM_MESSAGE_PROMOTION",
                "Hidden or retrieved text cannot be promoted to system-message authority.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("credential_exfiltration_requested") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_CREDENTIAL_EXFILTRATION_FORBIDDEN",
                "Public replay cannot request credential exfiltration.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("success_judged_only_by_final_answer") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_FINAL_ANSWER_ONLY_SUCCESS",
                "Prompt-injection claims need flow and receipt evidence, not final-answer-only success.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("untrusted_to_privileged_sink_allowed") is True:
            _record(
                findings,
                observed,
                "PROMPT_INJECTION_UNTRUSTED_PRIVILEGED_SINK_UNGATED",
                "Untrusted text cannot be allowed into a privileged sink without blocking, review, or sanitization.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
    return {
        "status": PASS,
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
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
    public_trace = build_public_prompt_injection_trace(input_dir)
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_prompt_injection_flow_bundle",
    )
    projection = validate_projection_protocol(
        payloads["projection_protocol"],
        public_root=public_root,
        public_trace=public_trace,
        source_modules=source_modules,
    )
    injection_policy = validate_injection_policy(payloads["injection_policy"])
    sources = validate_source_documents(payloads["source_documents"])
    flows = validate_information_flow_graph(
        payloads["information_flow_graph"], sources["source_rows"]
    )
    live_input_promotion = _live_tool_call_trace_promotion(public_trace)
    verdicts = validate_policy_verdicts(
        payloads["policy_verdicts"],
        payloads["injection_policy"],
        flows["flow_rows"],
    )
    verdicts_by_flow = {
        str(row["flow_id"]): str(row["verdict"])
        for row in verdicts["policy_verdict_rows"]
    }
    outputs = validate_sanitized_outputs(
        payloads["sanitized_outputs"],
        flows["flow_rows"],
        verdicts_by_flow,
    )
    flow_ids = {str(row["flow_id"]) for row in flows["flow_rows"]}
    cold_replay = validate_cold_replay(payloads["cold_replay"], flow_ids)
    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    negatives = validate_negative_cases(negative_payloads)
    source_open_body_imports = _source_open_body_import_summary(source_modules)
    observed = _merge_observed(
        projection,
        injection_policy,
        sources,
        flows,
        verdicts,
        outputs,
        cold_replay,
        negatives,
        source_modules,
        live_input_promotion,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        injection_policy,
        sources,
        flows,
        verdicts,
        outputs,
        cold_replay,
        negatives,
        source_modules,
    )
    positive_statuses = (
        projection["status"],
        injection_policy["status"],
        sources["status"],
        flows["status"],
        verdicts["status"],
        outputs["status"],
        cold_replay["status"],
        public_trace["status"],
        live_input_promotion["status"],
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and all(value == PASS for value in positive_statuses)
        and (
            input_mode != "exported_prompt_injection_flow_bundle"
            or source_modules["status"] == PASS
        )
        else "blocked"
    )
    return {
        "schema_version": (
            "indirect_prompt_injection_information_flow_policy_replay_result_v1"
        ),
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": (
            bundle_manifest.get("bundle_id")
            if isinstance(bundle_manifest, dict)
            else None
        ),
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_classification": BODY_IMPORT_CLASSIFICATION,
        "product_path_role": PRODUCT_PATH_ROLE,
        "body_import_verification": projection["body_import_verification"],
        "body_in_receipt": False,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "target_symbols": projection["target_symbols"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "source_open_body_import_refs": projection["source_open_body_import_refs"],
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_imports": source_modules,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "omitted_secret_or_live_access_material": projection[
            "omitted_secret_or_live_access_material"
        ],
        "public_agent_execution_trace": public_trace,
        "live_input_promotion": live_input_promotion,
        "live_tool_call_trace_count": live_input_promotion["live_input_trace_count"],
        "live_tool_call_taint_path_count": live_input_promotion[
            "taint_propagation_path_count"
        ],
        "injection_policy_id": injection_policy["policy_id"],
        "allowed_verdicts": injection_policy["allowed_verdicts"],
        "source_document_count": sources["source_document_count"],
        "untrusted_source_count": sources["untrusted_source_count"],
        "trusted_source_count": sources["trusted_source_count"],
        "trust_labels": sources["trust_labels"],
        "information_flow_count": flows["information_flow_count"],
        "privileged_flow_count": flows["privileged_flow_count"],
        "sanitized_flow_count": flows["sanitized_flow_count"],
        "taint_propagation": flows["taint_propagation"],
        "taint_propagation_path_count": flows["taint_propagation_path_count"],
        "derived_policy_verdict_mismatch_count": flows[
            "derived_policy_verdict_mismatch_count"
        ],
        "policy_verdict_count": verdicts["policy_verdict_count"],
        "allow_count": verdicts["allow_count"],
        "warn_count": verdicts["warn_count"],
        "block_count": verdicts["block_count"],
        "review_count": verdicts["review_count"],
        "sanitized_output_count": outputs["sanitized_output_count"],
        "trusted_context_disclosure_count": outputs[
            "trusted_context_disclosure_count"
        ],
        "untrusted_instruction_obeyed_count": outputs[
            "untrusted_instruction_obeyed_count"
        ],
        "blocked_without_external_action_count": outputs[
            "blocked_without_external_action_count"
        ],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "source_rows": sources["source_rows"],
        "flow_rows": flows["flow_rows"],
        "policy_verdict_rows": verdicts["policy_verdict_rows"],
        "sanitized_output_rows": outputs["sanitized_output_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": (
            "indirect_prompt_injection_information_flow_policy_replay_board_v1"
        ),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "indirect_prompt_injection_flow_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "source_trust_labels_before_flow",
                "count": result["source_document_count"],
                "authority": "every source must be synthetic, labeled, redacted, and scoped by trust tier",
            },
            {
                "mechanic_id": "taint_graph_before_action_verdict",
                "count": result["information_flow_count"],
                "authority": "source-to-sink flows carry taint labels before a verdict is admitted",
            },
            {
                "mechanic_id": "derived_taint_propagation",
                "count": result["taint_propagation_path_count"],
                "authority": "source taints are propagated over source-to-sink paths before verdicts are accepted",
            },
            {
                "mechanic_id": "live_input_tool_trace_taint_promotion",
                "count": result["live_tool_call_taint_path_count"],
                "authority": "one generated public tool-call trace is converted into source/flow rows and checked by the same taint propagation mechanic",
            },
            {
                "mechanic_id": "derived_policy_verdicts",
                "count": result["information_flow_count"],
                "authority": "allow, warn, review, and block verdicts are derived from propagated taint, sink privilege, sanitizer state, sink kind, and proposed action",
            },
            {
                "mechanic_id": "policy_verdicts_precede_privileged_sinks",
                "count": result["policy_verdict_count"],
                "authority": "allow, warn, block, and review verdicts precede any synthetic action",
            },
            {
                "mechanic_id": "sanitized_outputs_prevent_trusted_context_disclosure",
                "count": result["sanitized_output_count"],
                "authority": "outputs must not disclose trusted context or obey untrusted instructions",
            },
            {
                "mechanic_id": "negative_cases_are_admission_boundary",
                "count": len(result["observed_negative_cases"]),
                "authority": "real accounts, raw prompts, credentials, hidden-message promotion, and final-answer-only claims are rejected",
            },
        ],
        "source_rows": result["source_rows"],
        "flow_rows": result["flow_rows"],
        "policy_verdict_rows": result["policy_verdict_rows"],
        "sanitized_output_rows": result["sanitized_output_rows"],
        "cold_replay_rows": result["cold_replay_rows"],
        "body_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "live_input_promotion": result["live_input_promotion"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "product_path_role": result["product_path_role"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
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
            "indirect_prompt_injection_information_flow_policy_replay_result_receipt_v1"
        ),
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": (
            "indirect_prompt_injection_information_flow_policy_replay_validation_receipt_v1"
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
        "source_document_count": result["source_document_count"],
        "information_flow_count": result["information_flow_count"],
        "policy_verdict_count": result["policy_verdict_count"],
        "sanitized_output_count": result["sanitized_output_count"],
        "blocked_without_external_action_count": result[
            "blocked_without_external_action_count"
        ],
        "cold_replay_pass_count": result["cold_replay_pass_count"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "live_input_promotion": result["live_input_promotion"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": (
            "indirect_prompt_injection_information_flow_policy_replay_fixture_acceptance_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "live_input_promotion": result["live_input_promotion"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {
        **result,
        "prompt_injection_flow_board": board,
        "receipt_paths": receipt_paths,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs."
        "indirect_prompt_injection_information_flow_policy_replay run"
    ),
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(input_dir)
    result = _build_result(
        source,
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_prompt_injection_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "indirect_prompt_injection_information_flow_policy_replay "
        "run-prompt-injection-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_prompt_injection_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_prompt_injection_flow_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_prompt_injection_flow_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _card_receipt_paths(paths: object) -> list[str]:
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        return []
    normalized = normalize_public_receipt_paths({"receipt_paths": paths})
    values = normalized.get("receipt_paths") if isinstance(normalized, dict) else paths
    if isinstance(values, list) and all(isinstance(path, str) for path in values):
        return values
    return paths


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    secret_scan = result.get("secret_exclusion_scan")
    scan = secret_scan if isinstance(secret_scan, dict) else {}
    public_trace = result.get("public_agent_execution_trace")
    trace = public_trace if isinstance(public_trace, dict) else {}
    trace_summary = trace.get("summary") if isinstance(trace.get("summary"), dict) else {}
    source_body_floor = result.get("source_open_body_imports")
    source_body_floor = source_body_floor if isinstance(source_body_floor, dict) else {}
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
        "prompt_injection_flow": {
            "source_document_count": result.get("source_document_count"),
            "untrusted_source_count": result.get("untrusted_source_count"),
            "trusted_source_count": result.get("trusted_source_count"),
            "information_flow_count": result.get("information_flow_count"),
            "privileged_flow_count": result.get("privileged_flow_count"),
            "sanitized_flow_count": result.get("sanitized_flow_count"),
            "policy_verdict_count": result.get("policy_verdict_count"),
            "allow_count": result.get("allow_count"),
            "warn_count": result.get("warn_count"),
            "block_count": result.get("block_count"),
            "review_count": result.get("review_count"),
            "sanitized_output_count": result.get("sanitized_output_count"),
            "blocked_without_external_action_count": result.get(
                "blocked_without_external_action_count"
            ),
            "cold_replay_pass_count": result.get("cold_replay_pass_count"),
        },
        "public_trace": {
            "status": trace.get("status"),
            "span_count": trace.get("span_count"),
            "trace_digest": trace_summary.get("trace_digest"),
        },
        "live_input_promotion": {
            "status": (
                result.get("live_input_promotion", {}).get("status")
                if isinstance(result.get("live_input_promotion"), dict)
                else None
            ),
            "live_tool_call_trace_count": result.get("live_tool_call_trace_count"),
            "taint_propagation_path_count": result.get(
                "live_tool_call_taint_path_count"
            ),
        },
        "validation": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "secret_exclusion_blocking_hit_count": scan.get("blocking_hit_count"),
            "source_module_manifest_status": result.get(
                "source_module_manifest_status"
            ),
        },
        "body_floor": {
            "body_in_receipt": False,
            "body_material_status": source_body_floor.get("body_material_status"),
            "body_copied_material_count": source_body_floor.get(
                "body_material_count"
            ),
            "source_open_body_import_status": source_body_floor.get("status"),
            "secret_exclusion_scan_in_card": False,
            "source_rows_in_card": False,
            "flow_rows_in_card": False,
            "policy_verdict_rows_in_card": False,
            "sanitized_output_rows_in_card": False,
            "cold_replay_rows_in_card": False,
            "public_trace_spans_in_card": False,
            "source_module_bodies_in_card": False,
        },
        "authority_boundary": {
            "real_email_or_document_account_use_authorized": False,
            "raw_prompt_body_export_authorized": False,
            "secret_or_credential_exfiltration_authorized": False,
            "tool_output_instruction_authority_authorized": False,
            "hidden_system_message_promotion_authorized": False,
            "live_tool_call_authorized": False,
            "provider_calls_authorized": False,
            "benchmark_score_claim_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": _card_receipt_paths(result.get("receipt_paths", [])),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="indirect_prompt_injection_information_flow_policy_replay"
    )
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-prompt-injection-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        command = (
            "python -m microcosm_core.organs."
            "indirect_prompt_injection_information_flow_policy_replay "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-prompt-injection-bundle":
        command = (
            "python -m microcosm_core.organs."
            "indirect_prompt_injection_information_flow_policy_replay "
            f"run-prompt-injection-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_prompt_injection_bundle(
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
