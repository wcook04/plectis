from __future__ import annotations

import argparse
import hashlib
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


ORGAN_ID = "public_reveal_walkthrough"
FIXTURE_ID = "first_wave.public_reveal_walkthrough"
VALIDATOR_ID = "validator.microcosm.organs.public_reveal_walkthrough"
CARD_SCHEMA_VERSION = "public_reveal_walkthrough_command_card_v1"

RESULT_NAME = "public_reveal_walkthrough_result.json"
BOARD_NAME = "ten_minute_reveal_board.json"
VALIDATION_RECEIPT_NAME = "public_reveal_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/public_reveal_walkthrough_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_public_reveal_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_public_reveal_macro_body_landed"
SOURCE_OPEN_BODY_SCHEMA = "public_reveal_walkthrough_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_proof_body",
    }
)

INPUT_NAMES = (
    "reveal_walkthrough.json",
    "substrate_evidence_map.json",
    "audience_claim_floor.json",
)
NEGATIVE_INPUT_NAMES = (
    "release_or_hosting_overclaim.json",
    "private_equivalence_overclaim.json",
    "missing_evidence_route.json",
    "marketing_without_runtime.json",
)

EXPECTED_NEGATIVE_CASES = {
    "release_or_hosting_overclaim": ["PUBLIC_REVEAL_RELEASE_OVERCLAIM"],
    "private_equivalence_overclaim": ["PUBLIC_REVEAL_PRIVATE_EQUIVALENCE_OVERCLAIM"],
    "missing_evidence_route": ["PUBLIC_REVEAL_STEP_EVIDENCE_MISSING"],
    "marketing_without_runtime": ["PUBLIC_REVEAL_RUNTIME_COMMAND_MISSING"],
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_reveal_walkthrough_metadata_and_command_plan_only",
    "release_authorized": False,
    "hosted_public_authorized": False,
    "publication_authorized": False,
    "recipient_work_authorized": False,
    "provider_calls_authorized": False,
    "private_data_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}
ANTI_CLAIM = (
    "The public reveal walkthrough validates a source-available public entry "
    "path, commands, evidence refs, public runtime refs, and anti-claims. It "
    "does not authorize release, hosting, publication, recipient work, "
    "provider calls, private-data equivalence, Lean/Lake execution, or "
    "whole-system correctness."
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


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        *(
            [input_dir / "bundle_manifest.json"]
            if (input_dir / "bundle_manifest.json").is_file()
            else []
        ),
        *_source_module_paths(input_dir, public_root=public_root),
    ]


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


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        findings = []
        status = "blocked" if require_manifest else "not_present"
        if require_manifest:
            findings.append(
                _finding(
                    "PUBLIC_REVEAL_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported public reveal bundle must include a source module manifest for copied macro body material.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_module_manifest",
                )
            )
        return {
            "status": status,
            "source_module_import_status": status,
            "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "material_classes": [],
            "body_material_classes": {},
            "body_in_receipt": False,
            "source_refs": [],
            "findings": findings,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [_display(manifest_path, public_root=public_root)]

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "PUBLIC_REVEAL_SOURCE_MODULE_MANIFEST_REQUIRED",
                "Source module manifest must be a JSON object.",
                case_id="source_module_manifest",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    else:
        if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "PUBLIC_REVEAL_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "PUBLIC_REVEAL_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="body_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "PUBLIC_REVEAL_SOURCE_MODULE_COUNT_MISMATCH",
                    "Source module manifest module_count must match the module row count.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
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
                    "PUBLIC_REVEAL_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "PUBLIC_REVEAL_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must use a public-safe macro body material class.",
                    case_id="source_module_manifest",
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
                    "PUBLIC_REVEAL_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while keeping receipt fields body-free.",
                    case_id="source_module_manifest",
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
                    "PUBLIC_REVEAL_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest",
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
                    "PUBLIC_REVEAL_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module digest declarations must match the copied target body.",
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
                        "PUBLIC_REVEAL_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared public reveal macro anchors.",
                        case_id="source_module_manifest",
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
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "module_count": len(modules),
        "verified_module_count": verified_count,
        "module_ids": module_ids,
        "material_classes": sorted(material_class_counts),
        "body_material_classes": material_class_counts,
        "body_in_receipt": False,
        "source_refs": source_refs,
        "findings": findings,
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
            "body_text_in_receipt": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "release_authorized": False,
            "whole_system_correctness_claim": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported public reveal bundle for copied macro reconstruction "
            "receipts and public substrate boundary policy bodies; receipts "
            "carry refs, hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )


def validate_walkthrough(payload: object, negative_payload: object | None = None) -> dict[str, Any]:
    steps = _rows(payload, "steps")
    normalized_steps: list[dict[str, Any]] = []
    command_refs: list[str] = []
    evidence_refs: list[str] = []
    substrate_refs: list[str] = []
    for row in steps:
        step_id = str(row.get("step_id") or "step")
        commands = [str(item) for item in row.get("commands", []) if isinstance(item, str)]
        inspect_refs = [str(item) for item in row.get("inspect_refs", []) if isinstance(item, str)]
        step_evidence = [str(item) for item in row.get("evidence_refs", []) if isinstance(item, str)]
        command_refs.extend(commands)
        evidence_refs.extend(step_evidence)
        substrate_refs.extend(inspect_refs)
        normalized_steps.append(
            {
                "step_id": step_id,
                "minute_range": row.get("minute_range"),
                "commands": commands,
                "inspect_refs": inspect_refs,
                "evidence_refs": step_evidence,
                "expected_signal": row.get("expected_signal"),
                "body_in_receipt": False,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if isinstance(negative_payload, dict):
        case_id = str(
            negative_payload.get("expected_negative_case_id") or "missing_evidence_route"
        )
        for row in _rows(negative_payload, "steps"):
            step_id = str(row.get("step_id") or "step")
            commands = [item for item in row.get("commands", []) if isinstance(item, str)]
            evidence = [item for item in row.get("evidence_refs", []) if isinstance(item, str)]
            inspect_refs = [item for item in row.get("inspect_refs", []) if isinstance(item, str)]
            if not evidence or not inspect_refs:
                _record(
                    findings,
                    observed,
                    "PUBLIC_REVEAL_STEP_EVIDENCE_MISSING",
                    "Reveal step must point at concrete substrate refs and evidence refs.",
                    case_id=case_id,
                    subject_id=step_id,
                    subject_kind="reveal_step",
                )
            if not commands:
                _record(
                    findings,
                    observed,
                    "PUBLIC_REVEAL_RUNTIME_COMMAND_MISSING",
                    "Reveal step must include a command or local runtime action.",
                    case_id=str(
                        row.get("expected_negative_case_id")
                        or "marketing_without_runtime"
                    ),
                    subject_id=step_id,
                    subject_kind="reveal_step",
                )

    command_count = len(set(command_refs))
    evidence_count = len(set(evidence_refs))
    status = PASS if len(normalized_steps) >= 5 and command_count >= 4 and evidence_count >= 4 else "blocked"
    first_command = next(
        (
            command
            for step in normalized_steps
            for command in step.get("commands", [])
        ),
        None,
    )
    if status != PASS:
        findings.append(
            _finding(
                "PUBLIC_REVEAL_DENSITY_FLOOR_MISSING",
                "Reveal walkthrough must fit at least five steps, four commands, and four evidence refs.",
                case_id="density_floor",
                subject_id="reveal_walkthrough",
                subject_kind="walkthrough",
            )
        )
    return {
        "status": status,
        "walkthrough_id": payload.get("walkthrough_id") if isinstance(payload, dict) else None,
        "claim": payload.get("claim") if isinstance(payload, dict) else None,
        "target_reader": payload.get("target_reader") if isinstance(payload, dict) else None,
        "time_budget_minutes": payload.get("time_budget_minutes") if isinstance(payload, dict) else None,
        "step_count": len(normalized_steps),
        "command_count": command_count,
        "evidence_ref_count": evidence_count,
        "substrate_ref_count": len(set(substrate_refs)),
        "steps": normalized_steps,
        "commands": sorted(set(command_refs)),
        "first_command": first_command,
        "evidence_refs": sorted(set(evidence_refs)),
        "substrate_refs": sorted(set(substrate_refs)),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_evidence_map(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "evidence")
    evidence_ids: list[str] = []
    refs: list[str] = []
    missing_refs: list[str] = []
    for row in rows:
        evidence_id = str(row.get("evidence_id") or "")
        ref = str(row.get("ref") or "")
        if evidence_id:
            evidence_ids.append(evidence_id)
        if ref:
            refs.append(ref)
        if not evidence_id or not ref or row.get("projection_not_authority") is not True:
            missing_refs.append(evidence_id or ref or "evidence")
    return {
        "status": PASS if rows and not missing_refs else "blocked",
        "evidence_ids": sorted(evidence_ids),
        "evidence_refs": sorted(refs),
        "evidence_count": len(rows),
        "missing_or_unbounded_evidence_refs": sorted(missing_refs),
        "findings": [
            _finding(
                "PUBLIC_REVEAL_EVIDENCE_MAP_INCOMPLETE",
                "Evidence rows must name evidence_id, ref, and projection_not_authority.",
                case_id="evidence_map_floor",
                subject_id=subject,
                subject_kind="evidence_row",
            )
            for subject in sorted(missing_refs)
        ],
        "observed_negative_cases": {},
    }


def validate_claim_floor(
    payload: object,
    release_negative: object | None = None,
    private_negative: object | None = None,
    marketing_negative: object | None = None,
) -> dict[str, Any]:
    claim = payload if isinstance(payload, dict) else {}
    required_phrases = [
        str(item)
        for item in claim.get("required_public_claim_phrases", [])
        if isinstance(item, str)
    ]
    allowed_claim = str(claim.get("public_claim") or "")
    missing_required = [phrase for phrase in required_phrases if phrase not in allowed_claim]
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if missing_required:
        findings.append(
            _finding(
                "PUBLIC_REVEAL_CLAIM_FLOOR_MISSING",
                "Public reveal claim is missing required product-loop phrases.",
                case_id="claim_floor",
                subject_id="public_claim",
                subject_kind="claim_floor",
            )
        )
    for negative, case_id, code, message in (
        (
            release_negative,
            "release_or_hosting_overclaim",
            "PUBLIC_REVEAL_RELEASE_OVERCLAIM",
            "Reveal material cannot claim release, hosting, publication, or recipient-work authority.",
        ),
        (
            private_negative,
            "private_equivalence_overclaim",
            "PUBLIC_REVEAL_PRIVATE_EQUIVALENCE_OVERCLAIM",
            "Reveal material cannot claim private-data equivalence or whole-system correctness.",
        ),
        (
            marketing_negative,
            "marketing_without_runtime",
            "PUBLIC_REVEAL_RUNTIME_COMMAND_MISSING",
            "Reveal material cannot be marketing-only without commands and evidence refs.",
        ),
    ):
        if not isinstance(negative, dict):
            continue
        flags = [
            "release_authorized",
            "hosted_public_authorized",
            "publication_authorized",
            "recipient_work_authorized",
            "private_data_equivalence_claim",
            "whole_system_correctness_claim",
            "runtime_commands_present",
        ]
        overclaim = any(negative.get(flag) is True for flag in flags[:-1]) or (
            case_id == "marketing_without_runtime"
            and negative.get("runtime_commands_present") is False
        )
        if overclaim:
            _record(
                findings,
                observed,
                code,
                message,
                case_id=case_id,
                subject_id=str(negative.get("claim_id") or case_id),
                subject_kind="claim_floor",
            )
    return {
        "status": PASS if not missing_required else "blocked",
        "public_claim": allowed_claim,
        "required_public_claim_phrases": required_phrases,
        "missing_required_phrases": missing_required,
        "forbidden_authority_rejected": True,
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

    walkthrough = validate_walkthrough(
        payloads["reveal_walkthrough"],
        payloads.get("missing_evidence_route"),
    )
    evidence = validate_evidence_map(payloads["substrate_evidence_map"])
    claim = validate_claim_floor(
        payloads["audience_claim_floor"],
        payloads.get("release_or_hosting_overclaim"),
        payloads.get("private_equivalence_overclaim"),
        payloads.get("marketing_without_runtime"),
    )
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=not include_negative,
    )
    source_open_body_imports = _source_open_body_import_summary(source_modules)

    observed = _merge_observed(walkthrough, evidence, claim)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(walkthrough, evidence, claim, source_modules)
    error_codes = sorted({finding["error_code"] for finding in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and walkthrough["status"] == PASS
        and evidence["status"] == PASS
        and claim["status"] == PASS
        and (include_negative or source_modules["status"] == PASS)
        else "blocked"
    )
    return {
        "schema_version": "public_reveal_walkthrough_result_v1",
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
        "source_module_manifest_status": source_modules["status"],
        "source_module_import_status": source_modules["source_module_import_status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_count": source_modules["module_count"],
        "source_module_verified_count": source_modules["verified_module_count"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "source_open_body_imports": source_open_body_imports,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "walkthrough_id": walkthrough["walkthrough_id"],
        "public_claim": claim["public_claim"],
        "target_reader": walkthrough["target_reader"],
        "time_budget_minutes": walkthrough["time_budget_minutes"],
        "step_count": walkthrough["step_count"],
        "command_count": walkthrough["command_count"],
        "evidence_ref_count": walkthrough["evidence_ref_count"],
        "substrate_ref_count": walkthrough["substrate_ref_count"],
        "commands": walkthrough["commands"],
        "evidence_refs": sorted(set(walkthrough["evidence_refs"]) | set(evidence["evidence_refs"])),
        "substrate_refs": walkthrough["substrate_refs"],
        "public_runtime_refs": sorted(
            set(walkthrough["substrate_refs"])
            | set(walkthrough["evidence_refs"])
            | set(evidence["evidence_refs"])
        ),
        "steps": walkthrough["steps"],
        "reveal_board": {
            "headline": "Microcosm turns a repo into a local operating substrate.",
            "time_budget_minutes": walkthrough["time_budget_minutes"],
            "step_count": walkthrough["step_count"],
            "first_command": walkthrough["first_command"],
            "primary_loop": "repo -> .microcosm -> catalog/patterns/routes/work/events/evidence/explanations",
            "evidence_is_drilldown": True,
            "release_authorized": False,
            "provider_calls_authorized": False,
            "private_data_equivalence_claim": False,
            "steps": walkthrough["steps"],
            "body_in_receipt": False,
        },
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "input_mode",
        "bundle_id",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "source_module_manifest_status",
        "source_module_import_status",
        "source_module_manifest_ref",
        "source_module_count",
        "source_module_verified_count",
        "body_copied_material_count",
        "source_open_body_imports",
        "authority_ceiling",
        "anti_claim",
        "walkthrough_id",
        "public_claim",
        "target_reader",
        "time_budget_minutes",
        "step_count",
        "command_count",
        "evidence_ref_count",
        "substrate_ref_count",
        "commands",
        "evidence_refs",
        "substrate_refs",
        "public_runtime_refs",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "public_reveal_walkthrough_result": target / RESULT_NAME,
        "ten_minute_reveal_board": target / BOARD_NAME,
        "public_reveal_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = [_display(path, public_root=public_root_path) for path in paths.values()]

    result_receipt = _common_receipt(
        result,
        schema_version="public_reveal_walkthrough_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    result_receipt.update({"reveal_board": result["reveal_board"]})
    board = _common_receipt(
        result,
        schema_version="public_reveal_walkthrough_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["reveal_board"])
    validation = _common_receipt(
        result,
        schema_version="public_reveal_walkthrough_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "ten_minute_density_floor_met": result["step_count"] >= 5,
            "runtime_commands_present": result["command_count"] >= 4,
            "evidence_refs_present": result["evidence_ref_count"] >= 4,
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="public_reveal_walkthrough_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "product_reveal_boundary": "ten_minute_public_entry_path",
        }
    )

    write_json_atomic(paths["public_reveal_walkthrough_result"], result_receipt)
    write_json_atomic(paths["ten_minute_reveal_board"], board)
    write_json_atomic(paths["public_reveal_validation_receipt"], validation)
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.public_reveal_walkthrough run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_reveal_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.public_reveal_walkthrough "
        f"run-reveal-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_public_reveal_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    receipt_path = target / BUNDLE_RESULT_NAME
    receipt_ref = _display(receipt_path, public_root=public_root)
    if Path(receipt_ref).is_absolute() and "receipts" in receipt_path.parts:
        receipts_index = len(receipt_path.parts) - 1 - list(reversed(receipt_path.parts)).index("receipts")
        receipt_ref = Path(*receipt_path.parts[receipts_index:]).as_posix()
    receipt = _common_receipt(
        result,
        schema_version="public_reveal_walkthrough_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update({"reveal_board": result["reveal_board"]})
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _scan_card(scan: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(scan, dict):
        return {
            "status": "missing",
            "blocking_hit_count": None,
            "hit_count": None,
            "scanned_path_count": None,
            "body_in_receipt": False,
            "hits_exported": False,
            "scan_scope_exported": False,
        }
    return {
        "status": scan.get("status"),
        "blocking_hit_count": scan.get("blocking_hit_count"),
        "hit_count": scan.get("hit_count"),
        "scanned_path_count": scan.get("scanned_path_count"),
        "body_in_receipt": scan.get("body_in_receipt") is True,
        "hits_exported": False,
        "scan_scope_exported": False,
    }


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    ceiling = result.get("authority_ceiling", {})
    if not isinstance(ceiling, dict):
        ceiling = {}
    return {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "release_authorized": ceiling.get("release_authorized") is True,
        "hosted_public_authorized": ceiling.get("hosted_public_authorized") is True,
        "publication_authorized": ceiling.get("publication_authorized") is True,
        "recipient_work_authorized": ceiling.get("recipient_work_authorized") is True,
        "provider_calls_authorized": ceiling.get("provider_calls_authorized") is True,
        "private_data_equivalence_claim": (
            ceiling.get("private_data_equivalence_claim") is True
        ),
        "whole_system_correctness_claim": (
            ceiling.get("whole_system_correctness_claim") is True
        ),
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    input_mode = result.get("input_mode")
    action = "run-reveal-bundle" if input_mode == "exported_public_reveal_bundle" else "run"
    card_id = (
        "public_reveal_walkthrough_bundle_card"
        if action == "run-reveal-bundle"
        else "public_reveal_walkthrough_fixture_card"
    )
    reveal_board = result.get("reveal_board", {})
    if not isinstance(reveal_board, dict):
        reveal_board = {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "input_mode": input_mode,
        "bundle_id": result.get("bundle_id"),
        "card_id": card_id,
        "output_profile": "compact_card_no_step_tables_or_ref_lists",
        "full_output_available": True,
        "full_output_drilldown": f"rerun {action} without --card",
        "receipt_paths": result.get("receipt_paths", []),
        "reveal_summary": {
            "walkthrough_id": result.get("walkthrough_id"),
            "target_reader": result.get("target_reader"),
            "time_budget_minutes": result.get("time_budget_minutes"),
            "step_count": result.get("step_count"),
            "command_count": result.get("command_count"),
            "evidence_ref_count": result.get("evidence_ref_count"),
            "substrate_ref_count": result.get("substrate_ref_count"),
            "first_command": reveal_board.get("first_command"),
            "primary_loop": reveal_board.get("primary_loop"),
            "evidence_is_drilldown": reveal_board.get("evidence_is_drilldown") is True,
        },
        "negative_case_coverage": {
            "expected_case_count": len(result.get("expected_negative_cases", [])),
            "observed_case_count": len(result.get("observed_negative_cases", {})),
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_code_count": len(result.get("error_codes", [])),
        },
        "secret_exclusion_scan_summary": _scan_card(result.get("secret_exclusion_scan")),
        "source_open_body_imports": {
            "status": (
                result.get("source_open_body_imports", {}).get("status")
                if isinstance(result.get("source_open_body_imports"), dict)
                else None
            ),
            "body_material_count": result.get("body_copied_material_count", 0),
            "manifest_ref": result.get("source_module_manifest_ref"),
            "body_text_exported_in_receipts": False,
            "body_text_exported_in_workingness": False,
        },
        "authority_ceiling": _authority_ceiling_card(result),
        "runtime_receipt": {
            "body_in_receipt": result.get("body_in_receipt") is True,
            "real_runtime_receipt": result.get("real_runtime_receipt") is True,
            "synthetic_receipt_standin_allowed": (
                result.get("synthetic_receipt_standin_allowed") is True
            ),
        },
        "no_export_guards": {
            "step_rows_exported": False,
            "commands_exported": False,
            "evidence_refs_exported": False,
            "substrate_refs_exported": False,
            "public_runtime_refs_exported": False,
            "private_state_scan_exported": False,
            "provider_payloads_exported": False,
            "release_authority_exported": False,
        },
        "output_economy": {
            "stdout_mode": "card",
            "full_payload_drilldown": "rerun without --card",
            "omitted_full_payload_keys": [
                "steps",
                "commands",
                "evidence_refs",
                "substrate_refs",
                "public_runtime_refs",
                "findings",
                "secret_exclusion_scan.hits",
                "secret_exclusion_scan.scan_scope",
                "source_open_body_imports.body_material_ids",
                "anti_claim",
                "reveal_board.steps",
            ],
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public reveal walkthrough")
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    bundle_parser = subparsers.add_parser("run-reveal-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        card_suffix = " --card" if args.card else ""
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        result = run(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.public_reveal_walkthrough "
                f"run --input {args.input} --out {args.out}{acceptance_suffix}{card_suffix}"
            ),
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-reveal-bundle":
        card_suffix = " --card" if args.card else ""
        result = run_reveal_bundle(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.public_reveal_walkthrough "
                f"run-reveal-bundle --input {args.input} --out {args.out}{card_suffix}"
            ),
        )
    else:
        return 2
    output = result_card(result) if args.card else result
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
