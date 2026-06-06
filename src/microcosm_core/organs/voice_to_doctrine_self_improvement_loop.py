from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)


ORGAN_ID = "voice_to_doctrine_self_improvement_loop"
FIXTURE_ID = "first_wave.voice_to_doctrine_self_improvement_loop"
VALIDATOR_ID = "validator.microcosm.organs.voice_to_doctrine_self_improvement_loop"
MODULE_PATH = "microcosm_core.organs.voice_to_doctrine_self_improvement_loop"
CARD_SCHEMA_VERSION = "voice_to_doctrine_self_improvement_command_card_v1"

RESULT_NAME = "voice_to_doctrine_self_improvement_loop_result.json"
BOARD_NAME = "voice_to_doctrine_self_improvement_loop_board.json"
VALIDATION_RECEIPT_NAME = (
    "voice_to_doctrine_self_improvement_loop_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "voice_to_doctrine_self_improvement_loop_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_voice_to_doctrine_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "propagation_policy.json",
    "owner_surfaces.json",
    "local_lessons.json",
)
NEGATIVE_INPUT_NAMES = (
    "raw_operator_voice_export.json",
    "doctrine_node_hand_edit.json",
    "consume_without_deposit.json",
    "pattern_receipt_only_progress.json",
    "global_promotion_without_owner_validation.json",
    "private_thread_body_export.json",
)

EXPECTED_NEGATIVE_CASES = {
    "raw_operator_voice_export": ["VOICE_DOCTRINE_RAW_OPERATOR_BODY_FORBIDDEN"],
    "doctrine_node_hand_edit": ["VOICE_DOCTRINE_DIRECT_NODE_EDIT_FORBIDDEN"],
    "consume_without_deposit": ["VOICE_DOCTRINE_CONSUME_WITHOUT_DEPOSIT"],
    "pattern_receipt_only_progress": ["VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS"],
    "global_promotion_without_owner_validation": [
        "VOICE_DOCTRINE_GLOBAL_PROMOTION_WITHOUT_OWNER_VALIDATION"
    ],
    "private_thread_body_export": ["VOICE_DOCTRINE_PRIVATE_THREAD_BODY_FORBIDDEN"],
}

REQUIRED_PATTERN_REFS = {
    "recursive_self_improvement_operating_loop",
    "doctrine_population_loop",
    "local_to_general_propagation",
}
REQUIRED_SEQUENCE = (
    "sense_local_pressure",
    "classify_pressure_shape",
    "select_owner_surface",
    "mutate_or_capture_owner",
    "validate_owner_result",
    "bind_closeout",
    "publish_reentry_condition",
)
REQUIRED_LESSON_FIELDS = (
    "lesson_id",
    "input_signal_class",
    "macro_pattern_refs",
    "selected_owner_surface_id",
    "owner_action",
    "status",
    "evidence_refs",
    "validation_ref",
    "closeout_ref",
)
FORBIDDEN_KEYS = (
    "raw_operator_voice",
    "operator_voice_body",
    "private_thread_body",
    "provider_payload",
    "credential_value",
    "secret_value",
    "raw_seed_body",
)
BAKED_EXPECTED_LABEL_KEYS = (
    "expected_label",
    "expected_outcome",
    "expected_status",
    "expected_verdict",
)
DOCTRINE_NODE_KINDS = {"principle", "concept", "mechanism", "axiom"}
VALID_OUTCOMES = {
    "refined_existing_surface",
    "workitem_captured",
    "nothing_to_refine",
    "already_propagated_verified",
}
SOURCE_BODY_MATERIAL_CLASSES = {
    "public_macro_paper_module_body",
    "public_macro_skill_body",
    "public_macro_standard_body",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_voice_to_doctrine_self_improvement_fixture_with_real_macro_bodies"
    ),
    "raw_operator_voice_export_authorized": False,
    "private_thread_body_export_authorized": False,
    "doctrine_node_hand_edit_authorized": False,
    "global_doctrine_promotion_authorized": False,
    "live_task_ledger_mutation_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Voice-to-doctrine self-improvement validates the public shape of the macro "
    "metabolism: local pressure is classified, routed to an owner surface, "
    "mutated or captured there, validated, and closed with a re-entry condition. "
    "It imports real macro paper-module, skill, and standard bodies as public "
    "substrate, but it does not export raw operator voice, private thread bodies, "
    "provider payloads, live Task Ledger rows, hand-edited doctrine nodes, global "
    "promotion authority, source mutation, or release authority."
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
    return public_relative_path(path.resolve(strict=False), display_root=public_root)


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    source_manifest = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if source_manifest.is_file():
        paths.append(source_manifest)
    return paths


def _scan_input_paths(input_dir: Path) -> list[Path]:
    paths = [input_dir / name for name in INPUT_NAMES]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    source_manifest = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if source_manifest.is_file():
        paths.append(source_manifest)
        try:
            source_payload = read_json_strict(source_manifest)
        except Exception:
            source_payload = {}
        public_root = _public_root_for_path(input_dir)
        if isinstance(source_payload, dict):
            for row in _rows(source_payload, "modules"):
                target_ref = row.get("target_ref")
                if isinstance(target_ref, str) and target_ref:
                    paths.append(public_root / target_ref)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


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


def _repo_root_for_public_root(public_root: Path) -> Path:
    search_roots = [public_root, *public_root.parents, Path.cwd().resolve(strict=False)]
    search_roots.extend(Path.cwd().resolve(strict=False).parents)
    for candidate in search_roots:
        if (candidate / "AGENTS.override.md").is_file() and (
            candidate / "microcosm-substrate"
        ).is_dir():
            return candidate
    return public_root


def _source_module_refs(source_manifest: object) -> dict[str, str]:
    refs: dict[str, str] = {}
    for row in _rows(source_manifest, "modules"):
        source_ref = row.get("source_ref")
        target_ref = row.get("target_ref")
        if (
            isinstance(source_ref, str)
            and source_ref
            and isinstance(target_ref, str)
            and target_ref
        ):
            refs[source_ref] = target_ref
    return refs


def _split_ref(ref: str) -> tuple[str, str]:
    path_ref, separator, anchor = ref.partition("::")
    return path_ref.strip(), anchor.strip() if separator else ""


def _path_ref_is_public_safe(path_ref: str) -> bool:
    if not path_ref or path_ref.startswith(("~", "\\")):
        return False
    path = Path(path_ref)
    return not path.is_absolute() and ".." not in path.parts


def _claim_or_anchor_resolves(path: Path, locator: str) -> bool:
    if not locator:
        return True
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return locator in text


def _candidate_ref(path: Path, *, public_root: Path, repo_root: Path) -> str:
    resolved = path.resolve(strict=False)
    for root in (public_root, repo_root / "microcosm-substrate"):
        try:
            return resolved.relative_to(root.resolve(strict=False)).as_posix()
        except ValueError:
            continue
    return path.name


def _resolve_ref(
    ref: str,
    *,
    public_root: Path,
    repo_root: Path,
    source_module_refs: dict[str, str],
) -> dict[str, Any]:
    path_ref, locator = _split_ref(ref)
    resolution = {
        "ref": ref,
        "path_ref": path_ref,
        "locator": locator,
        "resolved": False,
        "resolution_root": None,
        "resolved_ref": None,
        "path_exists": False,
        "locator_present": False,
        "body_in_receipt": False,
    }
    if not _path_ref_is_public_safe(path_ref):
        resolution["failure_reason"] = "unsafe_or_empty_path_ref"
        return resolution

    candidates: list[tuple[str, Path]] = []
    mapped_ref = source_module_refs.get(path_ref)
    if mapped_ref and _path_ref_is_public_safe(mapped_ref):
        candidates.append(("source_module_manifest_target", public_root / mapped_ref))
    candidates.extend(
        [
            ("exported_bundle_public_root", public_root / path_ref),
            (
                "checked_in_public_microcosm_tree",
                repo_root / "microcosm-substrate" / path_ref,
            ),
        ]
    )

    best = dict(resolution)
    for root_kind, candidate in candidates:
        exists = candidate.is_file()
        locator_present = exists and _claim_or_anchor_resolves(candidate, locator)
        candidate_row = {
            **resolution,
            "resolution_root": root_kind,
            "resolved_ref": _candidate_ref(
                candidate, public_root=public_root, repo_root=repo_root
            ),
            "path_exists": exists,
            "locator_present": locator_present,
            "resolved": exists and locator_present,
        }
        if candidate_row["resolved"]:
            return candidate_row
        if exists or not best["path_exists"]:
            best = candidate_row
    best["failure_reason"] = (
        "locator_missing" if best["path_exists"] else "path_missing"
    )
    return best


def _ref_resolves(
    ref: str,
    *,
    public_root: Path,
    repo_root: Path,
    source_module_refs: dict[str, str],
) -> bool:
    return _resolve_ref(
        ref,
        public_root=public_root,
        repo_root=repo_root,
        source_module_refs=source_module_refs,
    )["resolved"]


def _lesson_ref_values(row: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    changed_surface_ref = row.get("changed_surface_ref")
    if isinstance(changed_surface_ref, str) and changed_surface_ref:
        refs.append(("changed_surface_ref", changed_surface_ref))
    evidence_ref = row.get("evidence_ref")
    if isinstance(evidence_ref, str) and evidence_ref:
        refs.append(("evidence_ref", evidence_ref))
    for evidence in _strings(row.get("evidence_refs")):
        refs.append(("evidence_refs", evidence))
    validation_ref = row.get("validation_ref")
    if isinstance(validation_ref, str) and validation_ref:
        refs.append(("validation_ref", validation_ref))
    closeout_ref = row.get("closeout_ref")
    if isinstance(closeout_ref, str) and closeout_ref:
        refs.append(("closeout_ref", closeout_ref))
    return refs


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


def _blocking_findings(
    findings: list[dict[str, Any]], *, include_negative: bool
) -> list[dict[str, Any]]:
    if not include_negative:
        return findings
    expected_cases = set(EXPECTED_NEGATIVE_CASES)
    return [
        finding
        for finding in findings
        if str(finding.get("negative_case_id") or "") not in expected_cases
    ]


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def _source_module_result(
    payload: object,
    *,
    input_dir: Path,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if not manifest_path.is_file():
        if not require_manifest:
            return {
                "status": "not_present",
                "findings": [],
                "observed_negative_cases": {},
                "source_module_manifest_ref": None,
                "source_module_count": 0,
                "verified_source_module_count": 0,
                "body_copied_material_count": 0,
                "source_module_imports": [],
                "source_open_body_imports": {
                    "status": "not_present",
                    "source_import_class": None,
                    "body_material_count": 0,
                    "body_material_byte_count": 0,
                    "body_text_exported_in_receipts": False,
                    "body_in_receipt": False,
                },
            }
        finding = _finding(
            "VOICE_DOCTRINE_SOURCE_MODULE_MANIFEST_MISSING",
            "Exported voice-to-doctrine bundle must carry copied source-module manifest.",
            case_id="source_module_manifest",
            subject_id=SOURCE_MODULE_MANIFEST_NAME,
            subject_kind="source_module_manifest",
        )
        return {
            "status": "fail",
            "findings": [finding],
            "observed_negative_cases": {},
            "source_module_manifest_ref": None,
            "source_module_count": 0,
            "verified_source_module_count": 0,
            "body_copied_material_count": 0,
            "source_module_imports": [],
            "source_open_body_imports": {
                "status": "fail",
                "source_import_class": None,
                "body_material_count": 0,
                "body_material_byte_count": 0,
                "body_text_exported_in_receipts": False,
                "body_in_receipt": False,
            },
        }

    manifest = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    module_imports: list[dict[str, Any]] = []
    verified_count = 0
    byte_count = 0
    modules = _rows(manifest, "modules")
    repo_root = _repo_root_for_public_root(public_root)
    if not modules:
        findings.append(
            _finding(
                "VOICE_DOCTRINE_SOURCE_MODULE_ROWS_MISSING",
                "Source-module manifest must list copied macro source bodies.",
                case_id="source_module_manifest",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    for row in modules:
        module_id = str(row.get("module_id") or "missing_module_id")
        target_ref = row.get("target_ref")
        source_ref = str(row.get("source_ref") or "")
        material_class = str(row.get("material_class") or "")
        required_anchors = _strings(row.get("required_anchors"))
        module_findings: list[dict[str, Any]] = []
        if material_class not in SOURCE_BODY_MATERIAL_CLASSES:
            module_findings.append(
                _finding(
                    "VOICE_DOCTRINE_SOURCE_MODULE_CLASS_INVALID",
                    "Copied source bodies must use public macro body material classes.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not isinstance(target_ref, str) or not target_ref:
            module_findings.append(
                _finding(
                    "VOICE_DOCTRINE_SOURCE_MODULE_TARGET_REF_MISSING",
                    "Copied source body row must name a Microcosm target_ref.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
            target_path = None
        else:
            target_path = public_root / target_ref
        actual_sha = None
        actual_byte_count = 0
        actual_line_count = 0
        anchors_present = False
        source_path_exists = False
        source_sha = None
        source_hash_matches = False
        source_target_exact_copy = False
        source_anchors_present = False
        source_path = None
        if not _path_ref_is_public_safe(source_ref):
            module_findings.append(
                _finding(
                    "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_REF_UNSAFE",
                    "Copied source body row must use a public-safe macro source_ref.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif source_ref:
            source_path = repo_root / source_ref
            source_path_exists = source_path.is_file()
            if not source_path_exists:
                module_findings.append(
                    _finding(
                        "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_MISSING",
                        "Copied source body source_ref must exist in the macro source tree.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )
        if target_path is None or not target_path.is_file():
            module_findings.append(
                _finding(
                    "VOICE_DOCTRINE_SOURCE_MODULE_TARGET_MISSING",
                    "Copied source body target_ref must exist in the public bundle.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        else:
            body = target_path.read_bytes()
            text = body.decode("utf-8")
            actual_sha = hashlib.sha256(body).hexdigest()
            actual_byte_count = len(body)
            actual_line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
            expected_target_sha = str(row.get("target_sha256") or "")
            expected_source_sha = str(row.get("source_sha256") or "")
            if actual_sha != expected_target_sha or (
                expected_source_sha and expected_source_sha != actual_sha
            ):
                module_findings.append(
                    _finding(
                        "VOICE_DOCTRINE_SOURCE_MODULE_HASH_MISMATCH",
                        "Copied source body hash must match the manifest.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )
            if row.get("byte_count") != actual_byte_count:
                module_findings.append(
                    _finding(
                        "VOICE_DOCTRINE_SOURCE_MODULE_BYTE_COUNT_MISMATCH",
                        "Copied source body byte_count must match the target file.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )
            if row.get("line_count") != actual_line_count:
                module_findings.append(
                    _finding(
                        "VOICE_DOCTRINE_SOURCE_MODULE_LINE_COUNT_MISMATCH",
                        "Copied source body line_count must match the target file.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )
            anchors_present = all(anchor in text for anchor in required_anchors)
            if not anchors_present:
                module_findings.append(
                    _finding(
                        "VOICE_DOCTRINE_SOURCE_MODULE_ANCHOR_MISSING",
                        "Copied source body must contain each manifest anchor.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )
            if source_path is not None and source_path_exists:
                source_body = source_path.read_bytes()
                source_text = source_body.decode("utf-8")
                source_sha = hashlib.sha256(source_body).hexdigest()
                expected_source_sha = str(row.get("source_sha256") or "")
                source_hash_matches = bool(expected_source_sha) and (
                    source_sha == expected_source_sha
                )
                source_target_exact_copy = source_body == body
                source_anchors_present = all(
                    anchor in source_text for anchor in required_anchors
                )
                if not source_hash_matches:
                    module_findings.append(
                        _finding(
                            "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_HASH_MISMATCH",
                            "Copied source body source_sha256 must match the live macro source file.",
                            case_id="source_module_manifest",
                            subject_id=module_id,
                            subject_kind="source_module",
                        )
                    )
                if not source_target_exact_copy:
                    module_findings.append(
                        _finding(
                            "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_TARGET_COPY_MISMATCH",
                            "Copied source body target must be an exact copy of the live macro source file.",
                            case_id="source_module_manifest",
                            subject_id=module_id,
                            subject_kind="source_module",
                        )
                    )
                if not source_anchors_present:
                    module_findings.append(
                        _finding(
                            "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_ANCHOR_MISSING",
                            "Live macro source file must contain each manifest anchor.",
                            case_id="source_module_manifest",
                            subject_id=module_id,
                            subject_kind="source_module",
                        )
                    )
        if not source_ref:
            module_findings.append(
                _finding(
                    "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_REF_MISSING",
                    "Copied source body row must retain its macro source_ref.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        findings.extend(module_findings)
        if not module_findings:
            verified_count += 1
            byte_count += actual_byte_count
        module_imports.append(
            {
                "module_id": module_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": actual_sha,
                "source_path_exists": source_path_exists,
                "source_sha256": source_sha,
                "source_hash_matches": source_hash_matches,
                "source_target_exact_copy": source_target_exact_copy,
                "source_anchors_present": source_anchors_present,
                "byte_count": actual_byte_count,
                "line_count": actual_line_count,
                "required_anchor_count": len(required_anchors),
                "required_anchors_present": anchors_present,
                "body_in_receipt": False,
            }
        )
    status = PASS if not findings else "fail"
    return {
        "status": status,
        "findings": findings,
        "observed_negative_cases": {},
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "source_module_count": len(modules),
        "verified_source_module_count": verified_count,
        "body_copied_material_count": verified_count,
        "source_module_imports": module_imports,
        "source_open_body_imports": {
            "status": status,
            "source_import_class": manifest.get("source_import_class"),
            "body_material_count": verified_count,
            "body_material_byte_count": byte_count,
            "module_ids": sorted(
                str(row.get("module_id") or "") for row in modules if row.get("module_id")
            ),
            "source_refs": sorted(
                str(row.get("source_ref") or "") for row in modules if row.get("source_ref")
            ),
            "target_refs": sorted(
                str(row.get("target_ref") or "") for row in modules if row.get("target_ref")
            ),
            "manifest_ref": _display(manifest_path, public_root=public_root),
            "source_refs_live_checked": True,
            "source_target_exact_copy_count": len(
                [
                    row
                    for row in module_imports
                    if row.get("source_target_exact_copy") is True
                ]
            ),
            "body_text_exported_in_receipts": False,
            "body_in_receipt": False,
        },
    }


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    pattern_refs = set(_strings(protocol.get("source_pattern_refs")))
    missing_refs = sorted(REQUIRED_PATTERN_REFS - pattern_refs)
    if missing_refs:
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_REQUIRED_MACRO_PATTERN_REF_MISSING",
            "Projection protocol must carry the macro self-improvement refs.",
            case_id="projection_protocol",
            subject_id=",".join(missing_refs),
            subject_kind="projection_protocol",
        )
    verification = protocol.get("body_import_verification", {})
    if not isinstance(verification, dict) or not verification.get("target_ref"):
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_BODY_IMPORT_VERIFICATION_MISSING",
            "Projection protocol must name the public target body/refactor.",
            case_id="projection_protocol",
            subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
            subject_kind="projection_protocol",
        )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "source_pattern_refs": sorted(pattern_refs),
        "body_import_verification": verification if isinstance(verification, dict) else {},
    }


def validate_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    sequence = _strings(policy.get("required_sequence"))
    missing_sequence = [step for step in REQUIRED_SEQUENCE if step not in sequence]
    if missing_sequence:
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_REQUIRED_SEQUENCE_MISSING",
            "Self-improvement loop must carry the full sense-to-reentry sequence.",
            case_id="propagation_policy",
            subject_id=",".join(missing_sequence),
            subject_kind="propagation_policy",
        )
    if policy.get("receipt_only_progress_authorized") is True:
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS",
            "Receipt-only progress cannot satisfy the self-improvement loop.",
            case_id="pattern_receipt_only_progress",
            subject_id=str(policy.get("policy_id") or "propagation_policy"),
            subject_kind="propagation_policy",
        )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "required_sequence": sequence,
    }


def validate_owner_surfaces(payload: object) -> dict[str, Any]:
    owner_rows = _rows(payload, "owner_surfaces")
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    owner_map: dict[str, dict[str, Any]] = {}
    for row in owner_rows:
        owner_id = str(row.get("owner_surface_id") or "")
        if not owner_id:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OWNER_SURFACE_ID_MISSING",
                "Owner surface rows need stable ids.",
                case_id="owner_surfaces",
                subject_id=str(row.get("title") or "missing_owner_id"),
                subject_kind="owner_surface",
            )
            continue
        owner_map[owner_id] = row
        if not row.get("public_ref") or not row.get("mutation_authority"):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OWNER_SURFACE_CONTRACT_MISSING",
                "Owner surface rows need public refs and mutation authority.",
                case_id="owner_surfaces",
                subject_id=owner_id,
                subject_kind="owner_surface",
            )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "owner_map": owner_map,
    }


def validate_lessons(
    payload: object,
    *,
    owner_map: dict[str, dict[str, Any]],
    public_root: Path,
    source_module_manifest: object,
) -> dict[str, Any]:
    lessons = _rows(payload, "lessons")
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    status_counts: dict[str, int] = defaultdict(int)
    owner_counts: dict[str, int] = defaultdict(int)
    lesson_ref_resolutions: list[dict[str, Any]] = []
    ignored_expected_label_count = 0
    repo_root = _repo_root_for_public_root(public_root)
    source_refs = _source_module_refs(source_module_manifest)
    for row in lessons:
        lesson_id = str(row.get("lesson_id") or "missing_lesson_id")
        missing = [field for field in REQUIRED_LESSON_FIELDS if field not in row]
        baked_expected_keys = [
            key for key in BAKED_EXPECTED_LABEL_KEYS if key in row
        ]
        ignored_expected_label_count += len(baked_expected_keys)
        has_forbidden_body = _has_forbidden_key(row) or row.get("body_exported") is True
        owner_id = str(row.get("selected_owner_surface_id") or "")
        owner_known = owner_id in owner_map
        status = str(row.get("status") or "")
        status_known = status in VALID_OUTCOMES
        receipt_only_progress = row.get("owner_action") == "append_receipt_only" or (
            status == "refined_existing_surface" and not row.get("changed_surface_ref")
        )
        capture_without_reentry = (
            status == "workitem_captured" and not row.get("reentry_condition")
        )
        null_pass_without_stewardship = status == "nothing_to_refine" and (
            row.get("stewardship_checked") is not True
            or row.get("next_best_lane_checked") is not True
        )
        global_promotion_without_validation = row.get("global_promotion_requested") is True and (
            row.get("owner_surface_validated") is not True or not row.get("validation_ref")
        )
        if missing:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_LESSON_FIELD_MISSING",
                "Lesson rows must carry owner, validation, and closeout fields.",
                case_id="local_lessons",
                subject_id=f"{lesson_id}:{','.join(missing)}",
                subject_kind="lesson",
            )
        if has_forbidden_body:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RAW_OPERATOR_BODY_FORBIDDEN",
                "Lesson rows must not export raw operator, private, or provider bodies.",
                case_id="raw_operator_voice_export",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        if not owner_known:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OWNER_SURFACE_UNKNOWN",
                "Lesson selected an owner surface not present in owner_surfaces.",
                case_id="local_lessons",
                subject_id=f"{lesson_id}:{owner_id}",
                subject_kind="lesson",
            )
        else:
            owner_counts[owner_id] += 1
        status_counts[status] += 1
        if not status_known:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OUTCOME_UNKNOWN",
                "Lesson outcome must be one of the accepted propagation outcomes.",
                case_id="local_lessons",
                subject_id=f"{lesson_id}:{status}",
                subject_kind="lesson",
            )
        if receipt_only_progress:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS",
                "Refinement requires an owner surface change, not a receipt-only row.",
                case_id="pattern_receipt_only_progress",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        unresolved_ref_for_row = False
        for field_name, ref in _lesson_ref_values(row):
            resolution = _resolve_ref(
                ref,
                public_root=public_root,
                repo_root=repo_root,
                source_module_refs=source_refs,
            )
            resolution["lesson_id"] = lesson_id
            resolution["field_name"] = field_name
            lesson_ref_resolutions.append(resolution)
            if not resolution["resolved"]:
                unresolved_ref_for_row = True
                _record(
                    findings,
                    observed,
                    "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED",
                    "Lesson refs must resolve to exported bundle, source-module, or public Microcosm files.",
                    case_id="local_lessons",
                    subject_id=f"{lesson_id}:{field_name}:{ref}",
                    subject_kind="lesson_ref",
                )
        if capture_without_reentry:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_CAPTURE_WITHOUT_REENTRY",
                "Residual captures need a concrete re-entry condition.",
                case_id="local_lessons",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        if null_pass_without_stewardship:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_NULL_PASS_WITHOUT_STEWARDSHIP",
                "Nothing-to-refine requires stewardship and next-best-lane evidence.",
                case_id="consume_without_deposit",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        if global_promotion_without_validation:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_GLOBAL_PROMOTION_WITHOUT_OWNER_VALIDATION",
                "Global promotion is blocked without owner validation.",
                case_id="global_promotion_without_owner_validation",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        real_backed = not any(
            [
                missing,
                has_forbidden_body,
                not owner_known,
                not status_known,
                receipt_only_progress,
                unresolved_ref_for_row,
                capture_without_reentry,
                null_pass_without_stewardship,
                global_promotion_without_validation,
            ]
        )
        if baked_expected_keys and not real_backed:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_BAKED_EXPECTED_LABEL_IGNORED",
                "Expected labels are ignored and cannot satisfy unbacked lesson evidence.",
                case_id="local_lessons",
                subject_id=f"{lesson_id}:{','.join(baked_expected_keys)}",
                subject_kind="lesson",
            )
    unresolved_ref_count = len(
        [row for row in lesson_ref_resolutions if not row["resolved"]]
    )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "lesson_count": len(lessons),
        "status_counts": dict(sorted(status_counts.items())),
        "owner_counts": dict(sorted(owner_counts.items())),
        "lesson_ref_resolution_count": len(lesson_ref_resolutions),
        "unresolved_lesson_ref_count": unresolved_ref_count,
        "lesson_ref_resolutions": lesson_ref_resolutions,
        "ignored_expected_label_count": ignored_expected_label_count,
        "lessons": lessons,
    }


def validate_negative_cases(payloads: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for case_id in NEGATIVE_INPUT_NAMES:
        stem = Path(case_id).stem
        payload = payloads.get(stem, {})
        row = payload if isinstance(payload, dict) else {}
        if stem == "raw_operator_voice_export" and _has_forbidden_key(row):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RAW_OPERATOR_BODY_FORBIDDEN",
                "Raw operator voice bodies are excluded from public microcosm.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "doctrine_node_hand_edit" and (
            row.get("target_kind") in DOCTRINE_NODE_KINDS
            and row.get("mutation_route") == "direct_file_edit"
        ):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_DIRECT_NODE_EDIT_FORBIDDEN",
                "Doctrine nodes must route through apply lanes, not hand edits.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "consume_without_deposit" and not row.get("deposit_outcome"):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_CONSUME_WITHOUT_DEPOSIT",
                "Consumed surfaces require an owner mutation, capture, or typed no-op.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "pattern_receipt_only_progress" and row.get("owner_action") == "append_receipt_only":
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS",
                "Pattern receipts are evidence, not the main progress unit.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "global_promotion_without_owner_validation" and (
            row.get("global_promotion_requested") is True
            and row.get("owner_surface_validated") is not True
        ):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_GLOBAL_PROMOTION_WITHOUT_OWNER_VALIDATION",
                "Global promotion requires owner validation first.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "private_thread_body_export" and _has_forbidden_key(row):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_PRIVATE_THREAD_BODY_FORBIDDEN",
                "Private thread bodies must remain out of public fixtures.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
    }


def _receipt_paths(out: Path, *, acceptance_out: Path | None, public_root: Path) -> list[str]:
    paths = [
        out / RESULT_NAME,
        out / BOARD_NAME,
        out / VALIDATION_RECEIPT_NAME,
    ]
    if acceptance_out is not None:
        paths.append(acceptance_out)
    return [_display(path, public_root=public_root) for path in paths]


def _build_board(
    *,
    lessons_result: dict[str, Any],
    owner_map: dict[str, dict[str, Any]],
    command: str | None,
) -> dict[str, Any]:
    rows = []
    for row in lessons_result.get("lessons", []):
        owner = owner_map.get(str(row.get("selected_owner_surface_id") or ""), {})
        rows.append(
            {
                "lesson_id": row.get("lesson_id"),
                "input_signal_class": row.get("input_signal_class"),
                "selected_owner_surface_id": row.get("selected_owner_surface_id"),
                "owner_surface_kind": owner.get("surface_kind"),
                "owner_action": row.get("owner_action"),
                "status": row.get("status"),
                "changed_surface_ref": row.get("changed_surface_ref"),
                "validation_ref": row.get("validation_ref"),
                "closeout_ref": row.get("closeout_ref"),
                "reentry_condition": row.get("reentry_condition"),
                "body_in_receipt": False,
            }
        )
    return {
        "schema_version": "voice_to_doctrine_self_improvement_board_v1",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "created_at": utc_now(),
        "status": PASS,
        "command": command,
        "board_rows": rows,
        "owner_surface_ids": sorted(owner_map),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
    include_negative: bool = True,
    require_source_module_manifest: bool = False,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    output_dir = Path(out)
    public_root = _public_root_for_path(input_path)
    payloads = _load_payloads(input_path, include_negative=include_negative)

    protocol_result = validate_projection_protocol(payloads.get("projection_protocol"))
    policy_result = validate_policy(payloads.get("propagation_policy"))
    owner_result = validate_owner_surfaces(payloads.get("owner_surfaces"))
    lessons_result = validate_lessons(
        payloads.get("local_lessons"),
        owner_map=owner_result["owner_map"],
        public_root=public_root,
        source_module_manifest=payloads.get("source_module_manifest"),
    )
    source_module_result = _source_module_result(
        payloads.get("source_module_manifest"),
        input_dir=input_path,
        public_root=public_root,
        require_manifest=require_source_module_manifest,
    )
    negative_result = (
        validate_negative_cases(payloads) if include_negative else {"findings": [], "observed_negative_cases": {}}
    )
    secret_scan = scan_paths(
        [path.resolve(strict=False) for path in _scan_input_paths(input_path)],
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        source_context="target",
        display_root=public_root,
    )
    observed = _merge_observed(
        protocol_result,
        policy_result,
        owner_result,
        lessons_result,
        source_module_result,
        negative_result,
    )
    missing_negative_cases = (
        [
            case_id
            for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
            if sorted(observed.get(case_id, [])) != sorted(codes)
        ]
        if include_negative
        else []
    )
    findings = _merge_findings(
        protocol_result,
        policy_result,
        owner_result,
        lessons_result,
        source_module_result,
        negative_result,
    )
    blocking_findings = _blocking_findings(
        findings, include_negative=include_negative
    )
    source_modules_ok = source_module_result["status"] == PASS or (
        source_module_result["status"] == "not_present"
        and not require_source_module_manifest
    )
    status = (
        PASS
        if not blocking_findings
        and not missing_negative_cases
        and secret_scan.get("status") == PASS
        and source_modules_ok
        else "fail"
    )
    receipt_refs = _receipt_paths(
        output_dir,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
        public_root=public_root,
    )
    status_counts = lessons_result["status_counts"]
    result = {
        "schema_version": "voice_to_doctrine_self_improvement_loop_result_v1",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "created_at": utc_now(),
        "status": status,
        "command": command,
        "input_mode": "first_wave_fixture",
        "lesson_count": lessons_result["lesson_count"],
        "owner_surface_count": len(owner_result["owner_map"]),
        "refined_existing_surface_count": status_counts.get(
            "refined_existing_surface", 0
        ),
        "workitem_capture_count": status_counts.get("workitem_captured", 0),
        "nothing_to_refine_count": status_counts.get("nothing_to_refine", 0),
        "already_propagated_verified_count": status_counts.get(
            "already_propagated_verified", 0
        ),
        "status_counts": status_counts,
        "owner_counts": lessons_result["owner_counts"],
        "lesson_ref_resolution_count": lessons_result[
            "lesson_ref_resolution_count"
        ],
        "unresolved_lesson_ref_count": lessons_result[
            "unresolved_lesson_ref_count"
        ],
        "lesson_ref_resolutions": lessons_result["lesson_ref_resolutions"],
        "ignored_expected_label_count": lessons_result[
            "ignored_expected_label_count"
        ],
        "source_pattern_refs": protocol_result["source_pattern_refs"],
        "body_import_verification": protocol_result["body_import_verification"],
        "source_module_manifest_status": source_module_result["status"],
        "source_module_manifest_ref": source_module_result[
            "source_module_manifest_ref"
        ],
        "source_module_count": source_module_result["source_module_count"],
        "verified_source_module_count": source_module_result[
            "verified_source_module_count"
        ],
        "body_copied_material_count": source_module_result[
            "body_copied_material_count"
        ],
        "source_module_imports": source_module_result["source_module_imports"],
        "source_open_body_imports": source_module_result[
            "source_open_body_imports"
        ],
        "required_sequence": policy_result["required_sequence"],
        "observed_negative_cases": observed,
        "expected_negative_cases": EXPECTED_NEGATIVE_CASES if include_negative else {},
        "missing_negative_cases": missing_negative_cases,
        "error_codes": sorted({str(finding.get("error_code")) for finding in findings}),
        "blocking_error_codes": sorted(
            {str(finding.get("error_code")) for finding in blocking_findings}
        ),
        "findings": findings,
        "blocking_findings": blocking_findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "metadata_projection_not_live_learning_authority": True,
        "receipt_paths": receipt_refs,
    }
    board = _build_board(
        lessons_result=lessons_result,
        owner_map=owner_result["owner_map"],
        command=command,
    )
    validation_receipt = {
        "schema_version": "voice_to_doctrine_self_improvement_validation_v1",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "created_at": utc_now(),
        "status": status,
        "command": command,
        "checks": {
            "required_macro_pattern_refs_present": not any(
                finding.get("error_code")
                == "VOICE_DOCTRINE_REQUIRED_MACRO_PATTERN_REF_MISSING"
                for finding in findings
            ),
            "owner_surfaces_present": len(owner_result["owner_map"]) >= 4,
            "lesson_owner_deposits_present": result["lesson_count"] >= 4,
            "lesson_refs_resolved": result["unresolved_lesson_ref_count"] == 0,
            "lesson_ref_resolution_count": result["lesson_ref_resolution_count"],
            "unresolved_lesson_ref_count": result["unresolved_lesson_ref_count"],
            "ignored_expected_label_count": result["ignored_expected_label_count"],
            "negative_cases_observed": missing_negative_cases == [],
            "secret_exclusion_scan_passed": secret_scan.get("status") == PASS,
            "source_module_manifest_required": require_source_module_manifest,
            "source_module_manifest_verified": source_module_result["status"] == PASS,
            "source_module_count": source_module_result["source_module_count"],
            "verified_source_module_count": source_module_result[
                "verified_source_module_count"
            ],
            "receipt_only_progress_rejected": (
                "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS" in result["error_codes"]
                if include_negative
                else True
            ),
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }
    write_json_atomic(output_dir / RESULT_NAME, result)
    write_json_atomic(output_dir / BOARD_NAME, board)
    write_json_atomic(output_dir / VALIDATION_RECEIPT_NAME, validation_receipt)
    if acceptance_out:
        acceptance = dict(result)
        acceptance["schema_version"] = "voice_to_doctrine_self_improvement_acceptance_v1"
        acceptance["receipt_id"] = "voice_to_doctrine_self_improvement_fixture_acceptance"
        write_json_atomic(acceptance_out, acceptance)
    return result


def run_voice_to_doctrine_bundle(
    input_dir: str | Path,
    out: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    result = run(
        input_dir,
        out,
        command=command,
        include_negative=False,
        require_source_module_manifest=True,
    )
    bundle_manifest_path = Path(input_dir) / "bundle_manifest.json"
    manifest = read_json_strict(bundle_manifest_path) if bundle_manifest_path.is_file() else {}
    result = dict(result)
    result["schema_version"] = "voice_to_doctrine_exported_bundle_validation_v1"
    result["input_mode"] = "exported_voice_to_doctrine_bundle"
    result["bundle_id"] = manifest.get(
        "bundle_id", "voice_to_doctrine_self_improvement_loop_runtime_example"
    )
    result["expected_negative_cases"] = {}
    result["missing_negative_cases"] = []
    if result.get("status") == PASS:
        result["error_codes"] = []
        result["findings"] = []
    write_json_atomic(Path(out) / BUNDLE_RESULT_NAME, result)
    return result


def _scan_card(scan: object) -> dict[str, Any]:
    scan_row = scan if isinstance(scan, dict) else {}
    return {
        "status": scan_row.get("status"),
        "blocking_hit_count": scan_row.get("blocking_hit_count"),
        "hit_count": scan_row.get("hit_count"),
        "scanned_path_count": scan_row.get("scanned_path_count"),
        "body_in_receipt": scan_row.get("body_in_receipt") is True,
        "hits_exported": False,
        "scan_scope_exported": False,
        "source_excerpt_exported": False,
    }


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    ceiling = result.get("authority_ceiling", {})
    if not isinstance(ceiling, dict):
        ceiling = {}
    return {
        "status": ceiling.get("status"),
        "raw_operator_voice_export_authorized": (
            ceiling.get("raw_operator_voice_export_authorized") is True
        ),
        "private_thread_body_export_authorized": (
            ceiling.get("private_thread_body_export_authorized") is True
        ),
        "doctrine_node_hand_edit_authorized": (
            ceiling.get("doctrine_node_hand_edit_authorized") is True
        ),
        "global_doctrine_promotion_authorized": (
            ceiling.get("global_doctrine_promotion_authorized") is True
        ),
        "live_task_ledger_mutation_authorized": (
            ceiling.get("live_task_ledger_mutation_authorized") is True
        ),
        "provider_calls_authorized": ceiling.get("provider_calls_authorized") is True,
        "source_mutation_authorized": (
            ceiling.get("source_mutation_authorized") is True
        ),
        "release_authorized": ceiling.get("release_authorized") is True,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    input_mode = result.get("input_mode")
    action = "run-bundle" if input_mode == "exported_voice_to_doctrine_bundle" else "run"
    expected_cases = result.get("expected_negative_cases", {})
    observed_cases = result.get("observed_negative_cases", {})
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "input_mode": input_mode,
        "bundle_id": result.get("bundle_id"),
        "card_id": (
            "voice_to_doctrine_exported_bundle_card"
            if action == "run-bundle"
            else "voice_to_doctrine_fixture_card"
        ),
        "output_profile": "compact_card_no_findings_tables_bodies_or_scan_scope",
        "full_output_available": True,
        "full_output_drilldown": f"rerun {action} without --card",
        "receipt_summary": {
            "receipt_count": len(result.get("receipt_paths", [])),
            "receipt_paths_exported": False,
            "result_receipt_name": (
                BUNDLE_RESULT_NAME if action == "run-bundle" else RESULT_NAME
            ),
            "board_receipt_name": BOARD_NAME,
            "validation_receipt_name": VALIDATION_RECEIPT_NAME,
        },
        "doctrine_loop_summary": {
            "lesson_count": result.get("lesson_count"),
            "owner_surface_count": result.get("owner_surface_count"),
            "refined_existing_surface_count": result.get(
                "refined_existing_surface_count"
            ),
            "workitem_capture_count": result.get("workitem_capture_count"),
            "nothing_to_refine_count": result.get("nothing_to_refine_count"),
            "status_counts": result.get("status_counts", {}),
            "source_pattern_ref_count": len(result.get("source_pattern_refs", [])),
            "required_sequence_count": len(result.get("required_sequence", [])),
            "body_import_verification_mode": (
                result.get("body_import_verification", {}).get("verification_mode")
                if isinstance(result.get("body_import_verification"), dict)
                else None
            ),
        },
        "negative_case_coverage": {
            "expected_case_count": len(expected_cases)
            if isinstance(expected_cases, dict)
            else 0,
            "observed_case_count": len(observed_cases)
            if isinstance(observed_cases, dict)
            else 0,
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_code_count": len(result.get("error_codes", [])),
            "blocking_error_code_count": len(result.get("blocking_error_codes", [])),
        },
        "secret_exclusion_scan_summary": _scan_card(
            result.get("secret_exclusion_scan")
        ),
        "authority_ceiling": _authority_ceiling_card(result),
        "runtime_authority": {
            "body_in_receipt": result.get("body_in_receipt") is True,
            "metadata_projection_not_live_learning_authority": (
                result.get("metadata_projection_not_live_learning_authority") is True
            ),
        },
        "source_body_floor": {
            "source_module_manifest_status": result.get(
                "source_module_manifest_status"
            ),
            "source_module_count": result.get("source_module_count", 0),
            "verified_source_module_count": result.get(
                "verified_source_module_count", 0
            ),
            "body_copied_material_count": result.get(
                "body_copied_material_count", 0
            ),
        },
        "no_export_guards": {
            "findings_exported": False,
            "blocking_findings_exported": False,
            "owner_counts_exported": False,
            "observed_negative_cases_exported": False,
            "secret_scan_hits_exported": False,
            "secret_scan_scope_exported": False,
            "anti_claim_exported": False,
            "body_import_source_refs_exported": False,
            "private_bodies_exported": False,
            "provider_payloads_exported": False,
        },
        "output_economy": {
            "stdout_mode": "card",
            "full_payload_drilldown": "rerun without --card",
            "omitted_full_payload_keys": [
                "findings",
                "blocking_findings",
                "owner_counts",
                "observed_negative_cases",
                "source_pattern_refs",
                "required_sequence",
                "body_import_verification.source_refs",
                "source_open_body_imports.source_refs",
                "source_module_imports",
                "secret_exclusion_scan.hits",
                "secret_exclusion_scan.scan_scope",
                "anti_claim",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    bundle_parser = subparsers.add_parser("run-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    args = parser.parse_args(argv)
    if args.command == "run":
        card_suffix = " --card" if args.card else ""
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        result = run(
            args.input,
            args.out,
            command=(
                f"python -m {MODULE_PATH} run --input {args.input} "
                f"--out {args.out}{acceptance_suffix}{card_suffix}"
            ),
            acceptance_out=args.acceptance_out,
        )
    elif args.command == "run-bundle":
        card_suffix = " --card" if args.card else ""
        result = run_voice_to_doctrine_bundle(
            args.input,
            args.out,
            command=(
                f"python -m {MODULE_PATH} run-bundle --input {args.input} "
                f"--out {args.out}{card_suffix}"
            ),
        )
    else:
        parser.error("expected a subcommand")
    output = result_card(result) if args.card else result
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.get("status") == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
