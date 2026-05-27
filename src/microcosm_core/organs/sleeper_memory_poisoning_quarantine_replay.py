from __future__ import annotations

import argparse
import hashlib
import json
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


ORGAN_ID = "sleeper_memory_poisoning_quarantine_replay"
FIXTURE_ID = "first_wave.sleeper_memory_poisoning_quarantine_replay"
VALIDATOR_ID = "validator.microcosm.organs.sleeper_memory_poisoning_quarantine_replay"

RESULT_NAME = "sleeper_memory_poisoning_quarantine_replay_result.json"
BOARD_NAME = "sleeper_memory_poisoning_quarantine_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "sleeper_memory_poisoning_quarantine_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "sleeper_memory_poisoning_quarantine_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_sleeper_memory_poisoning_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "sleeper_memory_poisoning_quarantine_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "private_state_scan",
    "authority_ceiling",
    "anti_claim",
    "source_refs",
    "projection_receipt_refs",
    "public_replacement_refs",
    "session_rows",
    "write_rows",
    "retrieval_rows",
    "rollback_rows",
    "sleeper_memory_board",
    "source_module_imports",
    "source_open_body_imports",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_sleeper_memory_macro_body_landed"
SOURCE_OPEN_BODY_SCHEMA = "sleeper_memory_poisoning_quarantine_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_proof_body",
    }
)

INPUT_NAMES = (
    "projection_protocol.json",
    "memory_policy.json",
    "session_chain.json",
    "quarantine_events.json",
    "retrieval_replays.json",
    "rollback_rerun.json",
)
NEGATIVE_INPUT_NAMES = (
    "private_memory_body_export.json",
    "live_user_memory_claim.json",
    "raw_transcript_export.json",
    "memory_write_without_provenance.json",
    "trusted_promotion_from_untrusted_context.json",
    "deletion_without_audit.json",
    "final_answer_only_grading.json",
    "unmetered_poison_influence.json",
)

EXPECTED_NEGATIVE_CASES = {
    "private_memory_body_export": ["SLEEPER_MEMORY_PRIVATE_BODY_EXPORT"],
    "live_user_memory_claim": ["SLEEPER_MEMORY_LIVE_USER_MEMORY_CLAIM"],
    "raw_transcript_export": ["SLEEPER_MEMORY_RAW_TRANSCRIPT_EXPORT"],
    "memory_write_without_provenance": [
        "SLEEPER_MEMORY_WRITE_WITHOUT_PROVENANCE"
    ],
    "trusted_promotion_from_untrusted_context": [
        "SLEEPER_MEMORY_TRUSTED_PROMOTION_FORBIDDEN"
    ],
    "deletion_without_audit": ["SLEEPER_MEMORY_DELETION_WITHOUT_AUDIT"],
    "final_answer_only_grading": ["SLEEPER_MEMORY_FINAL_ANSWER_ONLY_GRADING"],
    "unmetered_poison_influence": [
        "SLEEPER_MEMORY_UNMETERED_POISON_INFLUENCE"
    ],
}

REQUIRED_SESSION_ROLES = (
    "poisoned_source_seen",
    "memory_write_quarantined",
    "later_retrieval_action_gated",
    "rollback_and_cold_rerun",
)
REQUIRED_WRITE_FIELDS = (
    "proposal_id",
    "session_id",
    "source_capsule_ref",
    "source_trust_tier",
    "proposed_memory_ref",
    "provenance_ref",
    "quarantine_verdict",
    "classifier_labels",
    "trusted_promotion",
    "private_body_exported",
    "raw_transcript_exported",
    "live_user_memory_claim",
    "body_redacted",
    "audit_ref",
)
REQUIRED_RETRIEVAL_FIELDS = (
    "replay_id",
    "session_id",
    "proposed_memory_ref",
    "retrieval_ref",
    "influence_grade",
    "action_gate",
    "cold_replay_receipt_ref",
    "evidence_used_refs",
    "body_redacted",
    "private_ref_metadata_only",
)
REQUIRED_ROLLBACK_FIELDS = (
    "rollback_id",
    "session_id",
    "proposed_memory_ref",
    "rollback_receipt_ref",
    "deletion_audit_ref",
    "rerun_receipt_ref",
    "memory_absent_after_rerun",
    "body_redacted",
)
FORBIDDEN_KEYS = (
    "private_memory_body",
    "raw_transcript",
    "raw_transcript_body",
    "private_thread_body",
    "provider_payload",
    "credential_value",
    "secret_value",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_body_free_sleeper_memory_quarantine_policy_projection_only"
    ),
    "live_memory_product_claim_authorized": False,
    "live_user_memory_claim_authorized": False,
    "private_memory_body_export_authorized": False,
    "raw_transcript_export_authorized": False,
    "trusted_promotion_from_untrusted_context_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Sleeper memory poisoning quarantine replay validates a body-free public "
    "memory-security policy projection: poisoned source metadata, "
    "provenance-bound write proposal, quarantine verdict, later retrieval "
    "influence gating, rollback, cold rerun, negative cases, and receipts. It "
    "does not export private memory bodies or raw transcripts, import live user "
    "memory, promote untrusted context to trusted memory, call providers, mutate "
    "source, claim benchmark security, or authorize release."
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
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        *_source_module_paths(source, public_root=public_root),
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
        "sleeper_memory_poisoning_quarantine_replay_result_v1"
        if include_negative
        else "exported_sleeper_memory_poisoning_bundle_validation_result_v1"
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
        "schema_version": "sleeper_memory_poisoning_quarantine_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_quarantine_bundle_receipt(
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
        "exported_sleeper_memory_poisoning_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_sleeper_memory_poisoning_bundle":
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
                    "SLEEPER_MEMORY_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported sleeper memory bundle must include a source module manifest for copied non-secret macro body material.",
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
                "SLEEPER_MEMORY_SOURCE_MODULE_MANIFEST_REQUIRED",
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
                    "SLEEPER_MEMORY_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "SLEEPER_MEMORY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "SLEEPER_MEMORY_SOURCE_MODULE_COUNT_MISMATCH",
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
                    "SLEEPER_MEMORY_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "SLEEPER_MEMORY_SOURCE_MODULE_CLASS_REQUIRED",
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
                    "SLEEPER_MEMORY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
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
                    "SLEEPER_MEMORY_SOURCE_MODULE_TARGET_MISSING",
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
                    "SLEEPER_MEMORY_SOURCE_MODULE_DIGEST_MISMATCH",
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
                        "SLEEPER_MEMORY_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared memory-plane macro anchors.",
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
            "live_memory_product_claim_authorized": False,
            "private_memory_body_export_authorized": False,
            "raw_transcript_export_authorized": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "release_authorized": False,
            "benchmark_score_claim_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported sleeper memory bundle for copied macro memory-plane "
            "doctrine, trace, standard, and reconstruction bodies; receipts "
            "carry refs, hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_replacements = _strings(protocol.get("public_replacement_refs"))
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 4
        or "sleeper_memory_poisoning_quarantine_replay_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or len(public_replacements) < 3
        or not _strings(protocol.get("reimplemented"))
        or not _strings(protocol.get("omitted"))
    ):
        findings.append(
            _finding(
                "SLEEPER_MEMORY_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, projection receipts, public replacements, reimplemented pieces, and omissions.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if protocol.get("copied_private_memory_bodies") is not False:
        findings.append(
            _finding(
                "SLEEPER_MEMORY_PRIVATE_BODY_COPY_CLAIM",
                "Projection protocol must explicitly deny copying private memory bodies.",
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


def validate_memory_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    trust_tiers = set(_strings(policy.get("allowed_trust_tiers")))
    verdicts = set(_strings(policy.get("allowed_quarantine_verdicts")))
    required = set(_strings(policy.get("required_write_fields")))
    findings: list[dict[str, Any]] = []
    if not {
        "trusted_source",
        "untrusted_context",
        "quarantined_candidate",
        "rolled_back",
    }.issubset(trust_tiers):
        findings.append(
            _finding(
                "SLEEPER_MEMORY_POLICY_TRUST_TIERS_INCOMPLETE",
                "Policy must define trusted, untrusted, quarantined, and rolled-back trust tiers.",
                case_id="memory_policy_floor",
                subject_id=str(policy.get("policy_id") or "memory_policy"),
                subject_kind="memory_policy",
            )
        )
    if not {"admit", "quarantine", "reject", "rollback", "rerun_pass"}.issubset(verdicts):
        findings.append(
            _finding(
                "SLEEPER_MEMORY_POLICY_VERDICTS_INCOMPLETE",
                "Policy must define admit, quarantine, reject, rollback, and rerun-pass verdicts.",
                case_id="memory_policy_floor",
                subject_id=str(policy.get("policy_id") or "memory_policy"),
                subject_kind="memory_policy",
            )
        )
    if not set(REQUIRED_WRITE_FIELDS).issubset(required):
        findings.append(
            _finding(
                "SLEEPER_MEMORY_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Policy must require provenance, trust tier, classifier, quarantine verdict, audit, and redaction fields.",
                case_id="memory_policy_floor",
                subject_id=str(policy.get("policy_id") or "memory_policy"),
                subject_kind="memory_policy",
            )
        )
    for field in (
        "live_memory_product_claim_authorized",
        "live_user_memory_claim_authorized",
        "private_memory_body_export_authorized",
        "raw_transcript_export_authorized",
        "trusted_promotion_from_untrusted_context_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "SLEEPER_MEMORY_POLICY_AUTHORITY_OVERCLAIM",
                    "Sleeper memory replay policy cannot authorize live memory, private body, raw transcript, untrusted promotion, provider, or release claims.",
                    case_id="memory_policy_floor",
                    subject_id=field,
                    subject_kind="memory_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_trust_tiers": sorted(trust_tiers),
        "allowed_quarantine_verdicts": sorted(verdicts),
        "required_write_fields": sorted(required),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_session_chain(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "session_chain")
    findings: list[dict[str, Any]] = []
    roles = [str(row.get("session_role") or "") for row in rows]
    orders = [row.get("chronological_order") for row in rows]
    redaction_ok = all(row.get("body_redacted") is True for row in rows)
    metadata_ok = all(row.get("private_ref_metadata_only") is True for row in rows)
    floor_blocked = (
        len(rows) != 4
        or roles != list(REQUIRED_SESSION_ROLES)
        or orders != [1, 2, 3, 4]
        or not redaction_ok
        or not metadata_ok
    )
    if floor_blocked:
        findings.append(
            _finding(
                "SLEEPER_MEMORY_SESSION_CHAIN_FLOOR_MISSING",
                "Positive fixture must expose four ordered sessions with redacted bodies and metadata-only private refs.",
                case_id="session_chain_floor",
                subject_id="session_chain",
                subject_kind="session_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked else "blocked",
        "session_count": len(rows),
        "session_roles": roles,
        "session_rows": [
            {
                "session_id": str(row.get("session_id") or ""),
                "session_role": str(row.get("session_role") or ""),
                "chronological_order": row.get("chronological_order"),
                "public_evidence_ref": row.get("public_evidence_ref"),
                "body_redacted": row.get("body_redacted") is True,
                "private_ref_metadata_only": row.get("private_ref_metadata_only") is True,
            }
            for row in rows
        ],
        "findings": findings,
        "observed_negative_cases": {},
    }


def _validate_write_row(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("proposal_id") or "write")
    proposal_id = str(row.get("proposal_id") or case_id)
    subject_kind = "negative_case" if negative else "memory_write_proposal"
    missing = [
        field for field in REQUIRED_WRITE_FIELDS if field not in row or row.get(field) in ("", None)
    ]
    trust_tier = str(row.get("source_trust_tier") or "")
    verdict = str(row.get("quarantine_verdict") or "")
    labels = _strings(row.get("classifier_labels"))
    reasons: list[str] = []

    if _has_forbidden_key(row) or row.get("private_body_exported") is True:
        reasons.append("private_memory_body_export")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_PRIVATE_BODY_EXPORT",
            "Public replay cannot export private memory bodies or provider/private payloads.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("raw_transcript_exported") is True:
        reasons.append("raw_transcript_export")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_RAW_TRANSCRIPT_EXPORT",
            "Public replay cannot export raw transcripts as memory evidence.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("live_user_memory_claim") is True:
        reasons.append("live_user_memory_claim")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_LIVE_USER_MEMORY_CLAIM",
            "Synthetic replay cannot claim to contain or validate live user memory.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if not row.get("provenance_ref") or not row.get("source_capsule_ref"):
        reasons.append("memory_write_without_provenance")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_WRITE_WITHOUT_PROVENANCE",
            "Memory writes require source capsule and provenance refs before admission.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if trust_tier == "untrusted_context" and (
        row.get("trusted_promotion") is True or verdict in {"admit", "trusted_promote"}
    ):
        reasons.append("trusted_promotion_from_untrusted_context")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_TRUSTED_PROMOTION_FORBIDDEN",
            "Untrusted context cannot be promoted into trusted memory without quarantine and review.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("body_redacted") is not True:
        reasons.append("body_not_redacted")
    if missing:
        reasons.append("write_field_missing")
    return {
        "proposal_id": proposal_id,
        "session_id": str(row.get("session_id") or ""),
        "source_capsule_ref": row.get("source_capsule_ref"),
        "source_trust_tier": trust_tier,
        "proposed_memory_ref": row.get("proposed_memory_ref"),
        "provenance_ref": row.get("provenance_ref"),
        "quarantine_verdict": verdict,
        "classifier_labels": labels,
        "trusted_promotion": row.get("trusted_promotion") is True,
        "audit_ref": row.get("audit_ref"),
        "computed_verdict": "accepted_write_metadata" if not reasons else "blocked",
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_redacted": True,
    }


def validate_quarantine_events(
    payload: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "memory_write_proposals"):
        rows.append(
            _validate_write_row(
                row,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for negative_payload in negative_payloads.values():
        negative_rows = _rows(negative_payload, "memory_write_proposals")
        if (
            isinstance(negative_payload, dict)
            and not negative_rows
            and (
                negative_payload.get("expected_negative_case_id")
                in {
                    "private_memory_body_export",
                    "live_user_memory_claim",
                    "raw_transcript_export",
                    "memory_write_without_provenance",
                    "trusted_promotion_from_untrusted_context",
                }
                or negative_payload.get("proposal_id")
            )
        ):
            negative_rows = [negative_payload]
        for row in negative_rows:
            _validate_write_row(
                row,
                findings=findings,
                observed=observed,
                negative=True,
            )

    quarantined = [
        row
        for row in rows
        if row["quarantine_verdict"] == "quarantine"
        and row["source_trust_tier"] == "untrusted_context"
        and "sleeper_poisoning" in row["classifier_labels"]
    ]
    admitted_control = [row for row in rows if row["quarantine_verdict"] == "admit"]
    positive_findings = [row for row in rows if row["reason_codes"]]
    floor_blocked = not rows or not quarantined or not admitted_control or positive_findings
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "SLEEPER_MEMORY_QUARANTINE_FLOOR_MISSING",
                "Positive fixture must include a sleeper-poisoning quarantine and a provenance-bound admitted control.",
                case_id="quarantine_event_floor",
                subject_id="memory_write_proposals",
                subject_kind="memory_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked else "blocked",
        "proposal_count": len(rows),
        "quarantined_write_count": len(quarantined),
        "admitted_control_count": len(admitted_control),
        "write_rows": sorted(rows, key=lambda row: row["proposal_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _validate_retrieval_row(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("replay_id") or "replay")
    replay_id = str(row.get("replay_id") or case_id)
    subject_kind = "negative_case" if negative else "retrieval_replay"
    missing = [
        field for field in REQUIRED_RETRIEVAL_FIELDS if field not in row or row.get(field) in ("", None)
    ]
    evidence_refs = _strings(row.get("evidence_used_refs"))
    influence_grade = str(row.get("influence_grade") or "")
    action_gate = str(row.get("action_gate") or "")
    reasons: list[str] = []
    if row.get("final_answer_only_grading") is True:
        reasons.append("final_answer_only_grading")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_FINAL_ANSWER_ONLY_GRADING",
            "Memory poisoning replay cannot be graded from final answers without evidence, retrieval, and rerun receipts.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if influence_grade in {"acted_on_quarantined_memory", "unmetered"} or action_gate in {
        "used_for_action",
        "ungated_action",
    }:
        reasons.append("unmetered_poison_influence")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_UNMETERED_POISON_INFLUENCE",
            "Quarantined poison memory cannot influence action without an explicit gate and receipt.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("body_redacted") is not True:
        reasons.append("body_not_redacted")
    if row.get("private_ref_metadata_only") is not True:
        reasons.append("private_ref_not_metadata_only")
    if row.get("cold_replay_receipt_ref") in ("", None) or not evidence_refs:
        reasons.append("replay_evidence_missing")
    if missing:
        reasons.append("retrieval_field_missing")
    return {
        "replay_id": replay_id,
        "session_id": str(row.get("session_id") or ""),
        "proposed_memory_ref": row.get("proposed_memory_ref"),
        "retrieval_ref": row.get("retrieval_ref"),
        "influence_grade": influence_grade,
        "action_gate": action_gate,
        "cold_replay_receipt_ref": row.get("cold_replay_receipt_ref"),
        "evidence_used_refs": evidence_refs,
        "computed_verdict": "accepted_replay_metadata" if not reasons else "blocked",
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_redacted": True,
    }


def validate_retrieval_replays(
    payload: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "retrieval_replays"):
        rows.append(
            _validate_retrieval_row(
                row,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for negative_payload in negative_payloads.values():
        negative_rows = _rows(negative_payload, "retrieval_replays")
        if (
            isinstance(negative_payload, dict)
            and not negative_rows
            and (
                negative_payload.get("expected_negative_case_id")
                in {"final_answer_only_grading", "unmetered_poison_influence"}
                or negative_payload.get("replay_id")
            )
        ):
            negative_rows = [negative_payload]
        for row in negative_rows:
            _validate_retrieval_row(
                row,
                findings=findings,
                observed=observed,
                negative=True,
            )

    blocked_before_action = [
        row
        for row in rows
        if row["action_gate"] == "blocked_before_action"
        and row["influence_grade"] == "quarantined_before_action"
    ]
    positive_findings = [row for row in rows if row["reason_codes"]]
    floor_blocked = not rows or not blocked_before_action or positive_findings
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "SLEEPER_MEMORY_RETRIEVAL_GATE_FLOOR_MISSING",
                "Positive fixture must show later retrieval of quarantined memory blocked before action with evidence and cold replay refs.",
                case_id="retrieval_replay_floor",
                subject_id="retrieval_replays",
                subject_kind="replay_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked else "blocked",
        "retrieval_replay_count": len(rows),
        "blocked_before_action_count": len(blocked_before_action),
        "retrieval_rows": sorted(rows, key=lambda row: row["replay_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _validate_rollback_row(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("rollback_id") or "rollback")
    rollback_id = str(row.get("rollback_id") or case_id)
    subject_kind = "negative_case" if negative else "rollback_rerun"
    missing = [
        field for field in REQUIRED_ROLLBACK_FIELDS if field not in row or row.get(field) in ("", None)
    ]
    reasons: list[str] = []
    if not row.get("deletion_audit_ref"):
        reasons.append("deletion_without_audit")
        _record(
            findings,
            observed,
            "SLEEPER_MEMORY_DELETION_WITHOUT_AUDIT",
            "Rollback/delete claims require an audit ref and cold rerun receipt.",
            case_id=case_id,
            subject_id=rollback_id,
            subject_kind=subject_kind,
        )
    if row.get("memory_absent_after_rerun") is not True:
        reasons.append("memory_present_after_rerun")
    if row.get("body_redacted") is not True:
        reasons.append("body_not_redacted")
    if missing:
        reasons.append("rollback_field_missing")
    return {
        "rollback_id": rollback_id,
        "session_id": str(row.get("session_id") or ""),
        "proposed_memory_ref": row.get("proposed_memory_ref"),
        "rollback_receipt_ref": row.get("rollback_receipt_ref"),
        "deletion_audit_ref": row.get("deletion_audit_ref"),
        "rerun_receipt_ref": row.get("rerun_receipt_ref"),
        "memory_absent_after_rerun": row.get("memory_absent_after_rerun") is True,
        "computed_verdict": "accepted_rollback_metadata" if not reasons else "blocked",
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_redacted": True,
    }


def validate_rollback_rerun(
    payload: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "rollback_events"):
        rows.append(
            _validate_rollback_row(
                row,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for negative_payload in negative_payloads.values():
        negative_rows = _rows(negative_payload, "rollback_events")
        if (
            isinstance(negative_payload, dict)
            and not negative_rows
            and (
                negative_payload.get("expected_negative_case_id")
                == "deletion_without_audit"
                or negative_payload.get("rollback_id")
            )
        ):
            negative_rows = [negative_payload]
        for row in negative_rows:
            _validate_rollback_row(
                row,
                findings=findings,
                observed=observed,
                negative=True,
            )

    rerun_passes = [row for row in rows if row["memory_absent_after_rerun"]]
    positive_findings = [row for row in rows if row["reason_codes"]]
    floor_blocked = not rows or not rerun_passes or positive_findings
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "SLEEPER_MEMORY_ROLLBACK_RERUN_FLOOR_MISSING",
                "Positive fixture must show rollback audit and cold rerun with poison memory absent.",
                case_id="rollback_rerun_floor",
                subject_id="rollback_events",
                subject_kind="rollback_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked else "blocked",
        "rollback_count": len(rows),
        "rerun_pass_count": len(rerun_passes),
        "rollback_rows": sorted(rows, key=lambda row: row["rollback_id"]),
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
    memory_policy = validate_memory_policy(payloads["memory_policy"])
    sessions = validate_session_chain(payloads["session_chain"])
    quarantine = validate_quarantine_events(
        payloads["quarantine_events"],
        negative_payloads,
    )
    retrieval = validate_retrieval_replays(
        payloads["retrieval_replays"],
        negative_payloads,
    )
    rollback = validate_rollback_rerun(
        payloads["rollback_rerun"],
        negative_payloads,
    )
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_sleeper_memory_poisoning_bundle",
    )
    source_open_body_imports = _source_open_body_import_summary(source_modules)
    observed = _merge_observed(
        projection,
        memory_policy,
        sessions,
        quarantine,
        retrieval,
        rollback,
        source_modules,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        memory_policy,
        sessions,
        quarantine,
        retrieval,
        rollback,
        source_modules,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    source_module_ok = (
        source_modules["status"] == PASS
        if input_mode == "exported_sleeper_memory_poisoning_bundle"
        else source_modules["status"] in {PASS, "not_present"}
    )
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and memory_policy["status"] == PASS
        and sessions["status"] == PASS
        and quarantine["status"] == PASS
        and retrieval["status"] == PASS
        and rollback["status"] == PASS
        and source_module_ok
        else "blocked"
    )
    copied_body_landed = source_open_body_imports["status"] == PASS
    return {
        "schema_version": "sleeper_memory_poisoning_quarantine_replay_result_v1",
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
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_import_status": (
            SOURCE_MODULE_IMPORT_STATUS
            if copied_body_landed
            else "public_body_free_policy_refactor_landed"
        ),
        "body_import_classification": (
            "copied_non_secret_public_memory_plane_macro_body_import"
            if copied_body_landed
            else "algorithmic_projection_public_memory_security_policy_refactor"
        ),
        "product_path_role": (
            "copied_non_secret_macro_body_plus_public_memory_security_policy_refactor"
            if copied_body_landed
            else "algorithmic_projection_public_memory_security_policy_refactor"
        ),
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_imports": source_modules,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_replacement_refs": projection["public_replacement_refs"],
        "memory_policy_id": memory_policy["policy_id"],
        "allowed_trust_tiers": memory_policy["allowed_trust_tiers"],
        "allowed_quarantine_verdicts": memory_policy["allowed_quarantine_verdicts"],
        "session_count": sessions["session_count"],
        "session_roles": sessions["session_roles"],
        "proposal_count": quarantine["proposal_count"],
        "quarantined_write_count": quarantine["quarantined_write_count"],
        "admitted_control_count": quarantine["admitted_control_count"],
        "retrieval_replay_count": retrieval["retrieval_replay_count"],
        "blocked_before_action_count": retrieval["blocked_before_action_count"],
        "rollback_count": rollback["rollback_count"],
        "rerun_pass_count": rollback["rerun_pass_count"],
        "session_rows": sessions["session_rows"],
        "write_rows": quarantine["write_rows"],
        "retrieval_rows": retrieval["retrieval_rows"],
        "rollback_rows": rollback["rollback_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "sleeper_memory_poisoning_quarantine_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "sleeper_memory_poisoning_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "poisoned_source_requires_provenance",
                "count": result["proposal_count"],
                "authority": "memory_write_proposals_need_source_capsule_and_provenance_refs",
            },
            {
                "mechanic_id": "sleeper_poisoning_quarantined_before_retrieval",
                "count": result["quarantined_write_count"],
                "authority": "untrusted_sleeper_poisoning_rows_stay_quarantined",
            },
            {
                "mechanic_id": "later_retrieval_blocked_before_action",
                "count": result["blocked_before_action_count"],
                "authority": "retrieved_quarantined_memory_cannot_influence_action",
            },
            {
                "mechanic_id": "rollback_cold_rerun_proves_absence_boundary",
                "count": result["rerun_pass_count"],
                "authority": "rollback_language_requires_audit_and_cold_rerun_refs",
            },
        ],
        "session_rows": result["session_rows"],
        "write_rows": result["write_rows"],
        "retrieval_rows": result["retrieval_rows"],
        "rollback_rows": result["rollback_rows"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_redacted": True,
        "body_in_receipt": False,
        "body_text_in_receipt": False,
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
        "schema_version": "sleeper_memory_poisoning_quarantine_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "sleeper_memory_poisoning_quarantine_replay_validation_receipt_v1",
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
        "session_count": result["session_count"],
        "proposal_count": result["proposal_count"],
        "quarantined_write_count": result["quarantined_write_count"],
        "retrieval_replay_count": result["retrieval_replay_count"],
        "blocked_before_action_count": result["blocked_before_action_count"],
        "rollback_count": result["rollback_count"],
        "rerun_pass_count": result["rerun_pass_count"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "sleeper_memory_poisoning_quarantine_fixture_acceptance_v1",
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
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "sleeper_memory_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs.sleeper_memory_poisoning_quarantine_replay run"
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


def run_quarantine_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.sleeper_memory_poisoning_quarantine_replay "
        "run-quarantine-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_quarantine_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_sleeper_memory_poisoning_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_sleeper_memory_poisoning_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    private_scan = result.get("private_state_scan")
    scan = private_scan if isinstance(private_scan, dict) else {}
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
        "sleeper_memory": {
            "session_count": result.get("session_count"),
            "proposal_count": result.get("proposal_count"),
            "quarantined_write_count": result.get("quarantined_write_count"),
            "admitted_control_count": result.get("admitted_control_count"),
            "retrieval_replay_count": result.get("retrieval_replay_count"),
            "blocked_before_action_count": result.get("blocked_before_action_count"),
            "rollback_count": result.get("rollback_count"),
            "rerun_pass_count": result.get("rerun_pass_count"),
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
            "private_state_blocking_hit_count": scan.get("blocking_hit_count"),
        },
        "body_floor": {
            "body_in_receipt": False,
            "private_state_scan_in_card": False,
            "session_rows_in_card": False,
            "write_rows_in_card": False,
            "retrieval_rows_in_card": False,
            "rollback_rows_in_card": False,
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
            "live_memory_product_claim_authorized": False,
            "live_user_memory_claim_authorized": False,
            "private_memory_body_export_authorized": False,
            "raw_transcript_export_authorized": False,
            "trusted_promotion_from_untrusted_context_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "benchmark_score_claim_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sleeper_memory_poisoning_quarantine_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-quarantine-bundle")
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
            "sleeper_memory_poisoning_quarantine_replay "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-quarantine-bundle":
        command = (
            "python -m microcosm_core.organs."
            "sleeper_memory_poisoning_quarantine_replay "
            f"run-quarantine-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_quarantine_bundle(
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
