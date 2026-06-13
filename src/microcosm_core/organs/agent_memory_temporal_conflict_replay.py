from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_memory_conflict_trace,
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


ORGAN_ID = "agent_memory_temporal_conflict_replay"
FIXTURE_ID = "first_wave.agent_memory_temporal_conflict_replay"
VALIDATOR_ID = "validator.microcosm.organs.agent_memory_temporal_conflict_replay"

RESULT_NAME = "agent_memory_temporal_conflict_replay_result.json"
BOARD_NAME = "agent_memory_temporal_conflict_replay_board.json"
VALIDATION_RECEIPT_NAME = "agent_memory_temporal_conflict_replay_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "agent_memory_temporal_conflict_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_memory_temporal_conflict_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "agent_memory_temporal_conflict_replay_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "secret_exclusion_scan",
    "public_agent_execution_trace",
    "source_refs",
    "projection_receipt_refs",
    "target_refs",
    "target_symbols",
    "public_runtime_refs",
    "memory_rows",
    "replay_rows",
    "source_open_body_imports",
    "authority_ceiling",
    "anti_claim",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = "copied_non_secret_macro_agent_memory_body_with_provenance"

INPUT_NAMES = (
    "projection_protocol.json",
    "memory_policy.json",
    "memory_episodes.json",
    "replay_observations.json",
)
NEGATIVE_INPUT_NAMES = (
    "raw_transcript_export.json",
    "private_candidate_auto_promotion.json",
    "stale_preference_override.json",
    "memory_as_source_authority.json",
    "vector_recall_without_evidence_handle.json",
    "final_answer_only_memory_credit.json",
    "active_injection_as_authoritative.json",
)
HASH_CHUNK_SIZE = 1024 * 1024

EXPECTED_NEGATIVE_CASES = {
    "raw_transcript_export": ["MEMORY_CONFLICT_RAW_TRANSCRIPT_FORBIDDEN"],
    "private_candidate_auto_promotion": [
        "MEMORY_CONFLICT_PRIVATE_CANDIDATE_AUTO_PROMOTION"
    ],
    "stale_preference_override": ["MEMORY_CONFLICT_STALE_OVERRIDE_FORBIDDEN"],
    "memory_as_source_authority": ["MEMORY_CONFLICT_SOURCE_AUTHORITY_FORBIDDEN"],
    "vector_recall_without_evidence_handle": [
        "MEMORY_CONFLICT_VECTOR_RECALL_WITHOUT_EVIDENCE"
    ],
    "final_answer_only_memory_credit": ["MEMORY_CONFLICT_FINAL_ANSWER_ONLY_CREDIT"],
    "active_injection_as_authoritative": [
        "MEMORY_CONFLICT_ACTIVE_INJECTION_AUTHORITY_FORBIDDEN"
    ],
}

REQUIRED_MEMORY_EVENT_FIELDS = (
    "event_id",
    "episode_id",
    "episode_order",
    "event_timestamp",
    "memory_route_ref",
    "decision",
    "memory_subject_id",
    "memory_priority",
    "source_trust_score",
    "evidence_handle_ref",
    "private_thread_ref",
    "metadata_only_ref",
    "body_exported",
    "source_authority_claim",
    "active_injection_adopted",
)
REQUIRED_REPLAY_FIELDS = (
    "observation_id",
    "episode_id",
    "replay_group_id",
    "memory_enabled",
    "answer_hash",
    "cold_replay_receipt_ref",
    "evidence_used_refs",
    "body_in_receipt",
)
FORBIDDEN_KEYS = (
    "raw_transcript",
    "raw_transcript_body",
    "private_thread_body",
    "private_message_body",
    "provider_payload",
    "credential_value",
    "secret_value",
)
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {
    "public_macro_doctrine_body",
    "public_macro_pattern_body",
    "public_macro_standard_body",
    "public_macro_tool_body",
}
SOURCE_MODULE_RELATIONS = {
    "exact_copy",
    "source_faithful_json_slice",
}
REAL_TRACE_EVENT_FIELDS = (
    "sanitized_real_episode",
    "source_artifact_ref",
    "source_event_ref",
)
TIMESTAMP_FIELDS = ("event_timestamp", "timestamp", "occurred_at")
PRIORITY_FIELDS = ("memory_priority", "priority", "priority_score")
SOURCE_TRUST_FIELDS = ("source_trust_score", "source_trust", "trust_score")
SOURCE_TRUST_LABEL_SCORES = {
    "digest_verified_public_source": 1.0,
    "trusted_public_source": 0.95,
    "public_sanitized_source": 0.85,
    "metadata_only_private_ref": 0.65,
    "untrusted_source": 0.0,
}
SOURCE_TRUST_FLOOR = 0.6

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_agent_execution_trace_refactor_over_memory_temporal_conflict_replay_fixture"
    ),
    "live_memory_product_claim_authorized": False,
    "private_transcript_export_authorized": False,
    "private_candidate_auto_promotion_authorized": False,
    "memory_as_source_authority_authorized": False,
    "active_injection_authority_authorized": False,
    "vector_recall_without_evidence_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Agent memory temporal-conflict replay validates a public three-episode "
    "memory update/replay contract with conflict edges, stale downgrades, "
    "metadata-only private refs, paired memory-on/off replay, public execution "
    "trace spans, negative cases, and receipts. The first-wave fixture rows are "
    "byte-aligned with the exported sanitized real memory stream and remain "
    "regression inputs around that real replay contract. It does not claim live "
    "memory product quality, export private "
    "transcripts, promote private candidates, treat memory recall as source "
    "authority, adopt active injection, call providers, mutate source, or "
    "authorize release."
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


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> object | None:
    for key in keys:
        value = row.get(key)
        if value not in ("", None):
            return value
    return None


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _normalized_timestamp(value: object) -> str | None:
    if value in ("", None) or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _timestamp_sort_value(value: object) -> float | None:
    normalized = _normalized_timestamp(value)
    if normalized is None:
        return None
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None


def _explicit_source_trust_score(row: dict[str, Any]) -> tuple[float | None, bool]:
    value = _first_present(row, SOURCE_TRUST_FIELDS)
    if value is not None:
        return _number(value), True
    label = str(row.get("source_trust_label") or "")
    if label:
        return SOURCE_TRUST_LABEL_SCORES.get(label), True
    return None, False


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _strip_microcosm_prefix(ref: str) -> str:
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _source_evidence_posture(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    posture = payload.get("source_evidence_posture", {})
    return posture if isinstance(posture, dict) else {}


def _source_module_manifest_path(
    input_dir: Path,
    *,
    public_root: Path | None = None,
    source_evidence_posture: dict[str, Any] | None = None,
) -> Path:
    posture = source_evidence_posture or {}
    manifest_ref = str(posture.get("source_module_manifest_ref") or "")
    if manifest_ref and public_root is not None:
        return public_root / _strip_microcosm_prefix(manifest_ref)
    if manifest_ref:
        return _public_root_for_path(input_dir) / _strip_microcosm_prefix(manifest_ref)
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    row_path = str(row.get("path") or "")
    if target_ref:
        return public_root / target_ref, target_ref
    if row_path:
        target = manifest_path.parent / row_path
        return target, _display(target, public_root=public_root)
    return public_root, ""


def _source_artifact_paths(
    input_dir: Path,
    *,
    public_root: Path,
    source_evidence_posture: dict[str, Any] | None = None,
) -> list[Path]:
    manifest_path = _source_module_manifest_path(
        input_dir,
        public_root=public_root,
        source_evidence_posture=source_evidence_posture,
    )
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    paths = [manifest_path]
    for row in _rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)
    paths = _input_paths(source, include_negative=include_negative)
    source_posture: dict[str, Any] = {}
    memory_path = source / "memory_episodes.json"
    if memory_path.is_file():
        try:
            source_posture = _source_evidence_posture(read_json_strict(memory_path))
        except (OSError, ValueError, TypeError):
            source_posture = {}
    paths = [
        *paths,
        *_source_artifact_paths(
            source,
            public_root=public_root,
            source_evidence_posture=source_posture,
        ),
    ]

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in paths:
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
        "agent_memory_temporal_conflict_replay_result_v1"
        if include_negative
        else "exported_memory_temporal_conflict_bundle_validation_result_v1"
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
        "schema_version": "agent_memory_temporal_conflict_replay_freshness_basis_v1",
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
    if payload.get("schema_version") != (
        "exported_memory_temporal_conflict_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_memory_temporal_conflict_bundle":
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


def validate_source_module_imports(
    input_dir: Path,
    *,
    public_root: Path,
    source_evidence_posture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(
        input_dir,
        public_root=public_root,
        source_evidence_posture=source_evidence_posture,
    )
    manifest_ref = _display(manifest_path, public_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "MEMORY_CONFLICT_SOURCE_MODULE_MANIFEST_MISSING",
                "Agent memory body floor requires a source_module_manifest.json for copied macro source bodies.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
        return {
            "status": "blocked",
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "modules": [],
            "findings": findings,
            "observed_negative_cases": {},
        }

    manifest = read_json_strict(manifest_path)
    module_rows = _rows(manifest, "modules")
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "MEMORY_CONFLICT_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "MEMORY_CONFLICT_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied agent-memory macro bodies may live in source_artifacts, not in receipts.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_text_in_receipt") is True:
        findings.append(
            _finding(
                "MEMORY_CONFLICT_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                "Copied agent-memory macro body text may not be exported in receipts.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("module_count") != len(module_rows):
        findings.append(
            _finding(
                "MEMORY_CONFLICT_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )

    for row in module_rows:
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        material_class = str(row.get("material_class") or "")
        expected_digest = str(row.get("sha256") or "")
        relation = str(row.get("source_to_target_relation") or "")
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Agent memory body imports may include only public macro doctrine, pattern, standard, and tool bodies.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_text_in_receipt") is True:
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                    "Source module rows must not export copied macro body text in receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if relation not in SOURCE_MODULE_RELATIONS:
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy or source_faithful_json_slice.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
            continue
        actual_digest = _sha256(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": str(row.get("source_ref") or ""),
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "body_in_receipt": False,
                "body_text_in_receipt": False,
            }
        )

    return {
        "status": PASS if not findings and modules else "blocked",
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "modules": modules,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _empty_source_module_imports() -> dict[str, Any]:
    return {
        "status": PASS,
        "source_module_manifest_ref": "",
        "module_count": 0,
        "modules": [],
        "findings": [],
        "observed_negative_cases": {},
    }


def _source_open_body_import_summary(source_imports: dict[str, Any]) -> dict[str, Any]:
    modules = _rows(source_imports, "modules")
    module_ids = [str(row.get("module_id")) for row in modules if row.get("module_id")]
    return {
        "schema_version": "agent_memory_source_open_body_imports_v1",
        "status": source_imports.get("status"),
        "source_import_class": SOURCE_IMPORT_CLASS if modules else "",
        "body_material_status": SOURCE_BODY_STATUS if modules else "",
        "body_material_count": len(modules),
        "body_material_ids": module_ids,
        "material_classes": sorted(
            {str(row.get("material_class")) for row in modules if row.get("material_class")}
        ),
        "source_manifest_refs": [
            source_imports["source_module_manifest_ref"]
        ]
        if source_imports.get("source_module_manifest_ref")
        else [],
        "aggregate_floor_ref": (
            f"{source_imports['source_module_manifest_ref']}::modules"
            if source_imports.get("source_module_manifest_ref")
            else ""
        ),
        "body_in_receipt": False,
        "authority_ceiling": {
            "live_memory_product_claim_authorized": False,
            "private_transcript_export_authorized": False,
            "private_candidate_auto_promotion_authorized": False,
            "memory_as_source_authority_authorized": False,
            "active_injection_authority_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json and source_artifacts/ for copied "
            "agent-memory macro bodies; receipts carry digests and status only."
        )
        if modules
        else "",
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


def _replay_reference_index(memory_rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    episode_ids = {
        str(row.get("episode_id") or "")
        for row in memory_rows
        if row.get("episode_id")
    }
    evidence_refs: set[str] = set()
    for row in memory_rows:
        for key in (
            "evidence_handle_ref",
            "conflict_edge_ref",
            "stale_downgrade_ref",
            "prompt_adoption_observation_ref",
        ):
            value = row.get(key)
            if isinstance(value, str) and value:
                evidence_refs.add(value)
    return {"episode_ids": episode_ids, "evidence_refs": evidence_refs}


def _trace_spans_by_id(
    public_agent_execution_trace: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(public_agent_execution_trace, dict):
        return {}
    spans = public_agent_execution_trace.get("spans", [])
    if not isinstance(spans, list):
        return {}
    return {
        str(span.get("span_id") or ""): span
        for span in spans
        if isinstance(span, dict) and span.get("span_id")
    }


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def _ref_base(ref: object) -> str:
    return str(ref or "").split("::", 1)[0]


def _source_event_alignment_index(
    input_dir: Path,
    *,
    public_root: Path,
    source_evidence_posture: dict[str, Any],
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(
        input_dir,
        public_root=public_root,
        source_evidence_posture=source_evidence_posture,
    )
    if not manifest_path.is_file():
        return {"modules": {}, "omitted_source_refs": set(), "manifest_ref": ""}
    manifest = read_json_strict(manifest_path)
    modules: dict[str, set[str]] = {}
    for row in _rows(manifest, "modules"):
        _target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        artifact_refs = {
            _strip_microcosm_prefix(target_ref),
            _strip_microcosm_prefix(str(row.get("target_ref") or "")),
            str(row.get("path") or ""),
        }
        source_ref = str(row.get("source_ref") or "")
        for artifact_ref in artifact_refs:
            if artifact_ref and source_ref:
                modules.setdefault(artifact_ref, set()).add(source_ref)
    omitted_refs = {
        str(row.get("source_ref") or "")
        for row in _rows(manifest, "omitted_material")
        if row.get("source_ref")
    }
    return {
        "modules": modules,
        "omitted_source_refs": omitted_refs,
        "manifest_ref": _display(manifest_path, public_root=public_root),
    }


def _source_event_ref_matches(source_event_ref: str, allowed_refs: set[str]) -> bool:
    return any(
        source_event_ref == allowed
        or source_event_ref.startswith(f"{allowed}::")
        or source_event_ref.startswith(f"{allowed}.")
        for allowed in allowed_refs
    )


def _apply_source_event_alignment(
    event_rows: list[dict[str, Any]],
    *,
    input_dir: Path,
    public_root: Path,
    source_evidence_posture: dict[str, Any],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> None:
    index = _source_event_alignment_index(
        input_dir,
        public_root=public_root,
        source_evidence_posture=source_evidence_posture,
    )
    modules: dict[str, set[str]] = index["modules"]
    omitted_source_refs: set[str] = index["omitted_source_refs"]
    manifest_ref = str(index["manifest_ref"] or "")
    for row in event_rows:
        event_id = str(row["event_id"])
        source_artifact_ref = str(row.get("source_artifact_ref") or "")
        source_event_ref = str(row.get("source_event_ref") or "")
        artifact_base = _strip_microcosm_prefix(_ref_base(source_artifact_ref))
        reason_codes = row["reason_codes"]
        verified = False
        if source_artifact_ref.startswith("microcosm_core."):
            verified = source_event_ref.startswith("receipts/") and "::" in source_event_ref
        elif artifact_base == manifest_ref and omitted_source_refs:
            verified = _source_event_ref_matches(source_event_ref, omitted_source_refs)
        elif artifact_base in modules:
            verified = _source_event_ref_matches(source_event_ref, modules[artifact_base])
        if not verified:
            reason_codes.append("source_event_ref_unverified")
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_SOURCE_EVENT_REF_UNVERIFIED",
                "Positive memory rows must link source_event_ref to the digest-verified public source artifact they cite.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )
        row["source_event_verified"] = verified
        row["reason_codes"] = sorted(set(reason_codes))
        if row["reason_codes"]:
            row["computed_verdict"] = "quarantine"


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    target_refs = _strings(protocol.get("target_refs"))
    target_symbols = _strings(protocol.get("target_symbols"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    body_import_status = str(protocol.get("body_import_status") or "")
    body_import_verification = protocol.get("body_import_verification", {})
    verification_mode = (
        str(body_import_verification.get("verification_mode") or "")
        if isinstance(body_import_verification, dict)
        else ""
    )
    copied = _strings(protocol.get("copied"))
    reimplemented = _strings(protocol.get("reimplemented"))
    cleaned = _strings(protocol.get("cleaned"))
    omitted = _strings(protocol.get("omitted"))
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 4
        or "agent_memory_temporal_conflict_replay_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or body_import_status
        not in {
            "extension_of_existing_public_refactor_landed",
            "real_macro_body_floor_landed",
        }
        or not isinstance(body_import_verification, dict)
        or verification_mode
        not in {
            "extension_of_existing_public_refactor",
            "digest_verified_copied_non_secret_macro_body",
        }
        or len(target_refs) < 2
        or len(target_symbols) < 2
        or len(public_runtime_refs) < 2
        or not reimplemented
        or not omitted
    ):
        findings.append(
            _finding(
                "MEMORY_CONFLICT_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Memory conflict replay projection must cite source refs, projection receipts, target refs, runtime refs, public trace import verification, reimplemented pieces, and omissions.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if protocol.get("copied_private_thread_bodies") is not False:
        findings.append(
            _finding(
                "MEMORY_CONFLICT_PRIVATE_BODY_COPY_CLAIM",
                "Projection protocol must explicitly deny copying private thread bodies.",
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
        "body_import_status": body_import_status,
        "body_import_verification": body_import_verification,
        "copied": copied,
        "reimplemented": reimplemented,
        "cleaned": cleaned,
        "omitted": omitted,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_memory_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    allowed = set(_strings(policy.get("allowed_memory_decisions")))
    required = set(_strings(policy.get("required_memory_event_fields")))
    findings: list[dict[str, Any]] = []
    if not {"ADD", "UPDATE", "DELETE", "NOOP"}.issubset(allowed):
        findings.append(
            _finding(
                "MEMORY_CONFLICT_POLICY_DECISIONS_INCOMPLETE",
                "Memory policy must define ADD, UPDATE, DELETE, and NOOP decisions.",
                case_id="memory_policy_floor",
                subject_id=str(policy.get("policy_id") or "memory_policy"),
                subject_kind="memory_policy",
            )
        )
    if not set(REQUIRED_MEMORY_EVENT_FIELDS).issubset(required):
        findings.append(
            _finding(
                "MEMORY_CONFLICT_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Memory policy must require route refs, evidence handles, metadata-only private refs, and authority flags.",
                case_id="memory_policy_floor",
                subject_id=str(policy.get("policy_id") or "memory_policy"),
                subject_kind="memory_policy",
            )
        )
    for field in (
        "live_memory_product_claim_authorized",
        "private_transcript_export_authorized",
        "memory_as_source_authority_authorized",
        "active_injection_authority_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "MEMORY_CONFLICT_POLICY_AUTHORITY_OVERCLAIM",
                    "Memory conflict replay policy cannot authorize live product, private transcript, source-authority, injection, provider, or release claims.",
                    case_id="memory_policy_floor",
                    subject_id=field,
                    subject_kind="memory_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_memory_decisions": sorted(allowed),
        "required_memory_event_fields": sorted(required),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _validate_event_row(
    row: dict[str, Any],
    *,
    allowed_decisions: set[str],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("event_id") or "memory")
    event_id = str(row.get("event_id") or case_id)
    subject_kind = "negative_case" if negative else "memory_event"
    missing = [field for field in REQUIRED_MEMORY_EVENT_FIELDS if field not in row or row.get(field) in ("", None)]
    decision = str(row.get("decision") or "")
    reasons: list[str] = []

    if decision not in allowed_decisions:
        reasons.append("unknown_memory_decision")
    if _has_forbidden_key(row) or row.get("raw_transcript_exported") is True:
        reasons.append("raw_transcript_export")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_RAW_TRANSCRIPT_FORBIDDEN",
            "Public memory replay cannot export raw transcripts, private thread bodies, provider payloads, credentials, or secrets.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if row.get("private_candidate_auto_promoted") is True:
        reasons.append("private_candidate_auto_promotion")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_PRIVATE_CANDIDATE_AUTO_PROMOTION",
            "Private memory candidates cannot be promoted without an explicit public receipt boundary.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if row.get("stale_preference_override") is True:
        reasons.append("stale_preference_override")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_STALE_OVERRIDE_FORBIDDEN",
            "A stale preference cannot override a newer scoped preference without conflict-edge and downgrade receipts.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
        if not negative and not row.get("stale_downgrade_ref"):
            reasons.append("stale_override_without_downgrade_receipt")
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_STALE_OVERRIDE_DOWNGRADE_MISSING",
                "A positive stale override row must carry a stale-downgrade receipt before it can affect replay.",
                case_id=case_id,
                subject_id=event_id,
                subject_kind=subject_kind,
            )
    if row.get("source_authority_claim") is True or row.get("memory_as_source_authority") is True:
        reasons.append("memory_as_source_authority")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_SOURCE_AUTHORITY_FORBIDDEN",
            "Memory recall is contextual evidence and cannot be treated as source authority.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if row.get("vector_recall_used") is True and not row.get("evidence_handle_ref"):
        reasons.append("vector_recall_without_evidence")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_VECTOR_RECALL_WITHOUT_EVIDENCE",
            "Vector recall requires a public evidence handle before it can affect replay credit.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if row.get("active_injection_adopted") is True or row.get("active_injection_as_authority") is True:
        reasons.append("active_injection_authority")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_ACTIVE_INJECTION_AUTHORITY_FORBIDDEN",
            "Active injection text cannot become memory authority or trusted instruction.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    real_trace_fields_missing = [
        field
        for field in REAL_TRACE_EVENT_FIELDS
        if row.get(field) in ("", None) or (
            field == "sanitized_real_episode" and row.get(field) is not True
        )
    ]
    if not negative and real_trace_fields_missing:
        reasons.append("real_trace_source_evidence_missing")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_REAL_TRACE_SOURCE_EVIDENCE_MISSING",
            "Positive memory rows must cite sanitized real trace provenance, not only synthetic replay shape.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    conflict_edge_ref = str(row.get("conflict_edge_ref") or "")
    stale_downgrade_ref = str(row.get("stale_downgrade_ref") or "")
    event_timestamp = _normalized_timestamp(_first_present(row, TIMESTAMP_FIELDS))
    memory_priority = _number(_first_present(row, PRIORITY_FIELDS))
    source_trust_score, source_trust_explicit = _explicit_source_trust_score(row)
    if not negative and event_timestamp is None:
        reasons.append("event_timestamp_missing_or_invalid")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_TIMESTAMP_MISSING_OR_INVALID",
            "Positive memory rows must carry a public-safe timestamp for semantic replay recomputation.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if not negative and memory_priority is None:
        reasons.append("memory_priority_missing_or_invalid")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_PRIORITY_MISSING_OR_INVALID",
            "Positive memory rows must carry a priority score for semantic replay recomputation.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if not negative and (source_trust_score is None or not source_trust_explicit):
        reasons.append("source_trust_missing_or_invalid")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_SOURCE_TRUST_MISSING_OR_INVALID",
            "Positive memory rows must carry a source trust score for semantic replay recomputation.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if not negative and source_trust_score is not None and source_trust_score < SOURCE_TRUST_FLOOR:
        reasons.append("source_trust_below_public_floor")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_SOURCE_TRUST_BELOW_PUBLIC_FLOOR",
            "Positive memory rows must be backed by a public-safe source trust score above the acceptance floor.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if not negative and decision in {"UPDATE", "DELETE"} and not conflict_edge_ref:
        reasons.append("temporal_conflict_edge_missing")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_UPDATE_DELETE_EDGE_MISSING",
            "Positive UPDATE/DELETE memory rows must carry a temporal conflict edge before they can affect replay.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if (
        not negative
        and conflict_edge_ref
        and not conflict_edge_ref.startswith("edge.memory.temporal_conflict.")
    ):
        reasons.append("temporal_conflict_edge_unverified")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_EDGE_REF_UNVERIFIED",
            "Conflict edge refs must cite the public temporal-conflict edge namespace, not an arbitrary evidence label.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if (
        not negative
        and decision in {"UPDATE", "DELETE"}
        and not stale_downgrade_ref.startswith("receipt.memory.")
    ):
        reasons.append("stale_downgrade_receipt_missing")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_STALE_DOWNGRADE_RECEIPT_MISSING",
            "Positive UPDATE/DELETE conflict rows must carry a stale-downgrade receipt before replay credit.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if row.get("body_exported") is not False:
        reasons.append("private_body_export_flag")
    if row.get("metadata_only_ref") is not True:
        reasons.append("private_ref_not_metadata_only")
    if not negative and not row.get("evidence_handle_ref"):
        reasons.append("evidence_handle_missing")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_EVIDENCE_HANDLE_MISSING",
            "Positive memory rows must carry a public evidence handle before memory can receive replay credit.",
            case_id=case_id,
            subject_id=event_id,
            subject_kind=subject_kind,
        )
    if missing:
        reasons.append("memory_event_field_missing")

    return {
        "event_id": event_id,
        "episode_id": str(row.get("episode_id") or ""),
        "episode_order": row.get("episode_order"),
        "event_timestamp": event_timestamp,
        "memory_route_ref": row.get("memory_route_ref"),
        "decision": decision,
        "memory_subject_id": row.get("memory_subject_id"),
        "conflict_subject_ref": row.get("conflict_subject_ref"),
        "memory_priority": memory_priority,
        "source_trust_score": source_trust_score,
        "source_trust_label": row.get("source_trust_label"),
        "evidence_handle_ref": row.get("evidence_handle_ref"),
        "private_thread_ref": row.get("private_thread_ref"),
        "metadata_only_ref": row.get("metadata_only_ref") is True,
        "conflict_edge_ref": row.get("conflict_edge_ref"),
        "stale_downgrade_ref": row.get("stale_downgrade_ref"),
        "prompt_adoption_observation_ref": row.get("prompt_adoption_observation_ref"),
        "sanitized_real_episode": row.get("sanitized_real_episode") is True,
        "source_artifact_ref": row.get("source_artifact_ref"),
        "source_event_ref": row.get("source_event_ref"),
        "computed_verdict": "accepted_memory_metadata" if not reasons else "quarantine",
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_in_receipt": False,
    }


def _episode_order(row: dict[str, Any]) -> int | None:
    value = row.get("episode_order")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _conflict_group_ref(row: dict[str, Any]) -> str:
    return str(row.get("conflict_subject_ref") or row.get("memory_subject_id") or "")


def _event_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    order = _episode_order(row)
    timestamp = _timestamp_sort_value(row.get("event_timestamp"))
    return (
        order if order is not None else 10**9,
        timestamp if timestamp is not None else float("inf"),
        str(row.get("event_id") or ""),
    )


def _apply_conflict_semantic_recompute(
    event_rows: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> None:
    prior_by_group: dict[str, dict[str, Any]] = {}
    for row in sorted(event_rows, key=_event_sort_key):
        event_id = str(row["event_id"])
        reason_codes = row["reason_codes"]
        group_ref = _conflict_group_ref(row)
        timestamp = _timestamp_sort_value(row.get("event_timestamp"))
        priority = _number(row.get("memory_priority"))
        trust = _number(row.get("source_trust_score"))
        row["semantic_recompute"] = {
            "status": "not_applicable",
            "conflict_group_ref": group_ref,
            "prior_event_id": "",
            "timestamp_checked": timestamp is not None,
            "priority_checked": priority is not None,
            "source_trust_checked": trust is not None,
        }

        if row["computed_verdict"] == "quarantine":
            continue

        if row["decision"] not in {"ADD", "UPDATE", "DELETE"}:
            continue

        if not group_ref:
            reason_codes.append("conflict_group_missing")
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_SEMANTIC_GROUP_MISSING",
                "Memory writes must carry a subject or conflict lineage so temporal conflict semantics can be recomputed.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )

        if timestamp is None:
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_TIMESTAMP_MISSING_OR_INVALID",
                "Memory writes must carry a public-safe timestamp for semantic replay recomputation.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )
        if priority is None:
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_PRIORITY_MISSING_OR_INVALID",
                "Memory writes must carry a priority score for semantic replay recomputation.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )
        if trust is None:
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_SOURCE_TRUST_MISSING_OR_INVALID",
                "Memory writes must carry a source trust score for semantic replay recomputation.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )

        prior = prior_by_group.get(group_ref)
        if row["decision"] in {"UPDATE", "DELETE"}:
            if prior is None:
                reason_codes.append("semantic_prior_memory_event_missing")
                _record(
                    findings,
                    observed,
                    "MEMORY_CONFLICT_SEMANTIC_PRIOR_EVENT_MISSING",
                    "UPDATE/DELETE rows must recompute against an earlier accepted write in the same conflict lineage.",
                    case_id=event_id,
                    subject_id=event_id,
                    subject_kind="memory_event",
                )
            else:
                prior_timestamp = _timestamp_sort_value(prior.get("event_timestamp"))
                prior_priority = _number(prior.get("memory_priority"))
                prior_trust = _number(prior.get("source_trust_score"))
                row["semantic_recompute"] = {
                    "status": "checked",
                    "conflict_group_ref": group_ref,
                    "prior_event_id": prior.get("event_id"),
                    "timestamp_checked": timestamp is not None and prior_timestamp is not None,
                    "priority_checked": priority is not None and prior_priority is not None,
                    "source_trust_checked": trust is not None and prior_trust is not None,
                }
                if (
                    timestamp is None
                    or prior_timestamp is None
                    or timestamp <= prior_timestamp
                ):
                    reason_codes.append("semantic_timestamp_not_after_prior")
                    _record(
                        findings,
                        observed,
                        "MEMORY_CONFLICT_SEMANTIC_TIMESTAMP_INCOHERENT",
                        "UPDATE/DELETE rows must be timestamped after the prior accepted write they supersede.",
                        case_id=event_id,
                        subject_id=event_id,
                        subject_kind="memory_event",
                    )
                if priority is None or prior_priority is None or priority < prior_priority:
                    reason_codes.append("semantic_priority_regression")
                    _record(
                        findings,
                        observed,
                        "MEMORY_CONFLICT_SEMANTIC_PRIORITY_REGRESSION",
                        "UPDATE/DELETE rows must not downgrade accepted memory priority during temporal conflict recomputation.",
                        case_id=event_id,
                        subject_id=event_id,
                        subject_kind="memory_event",
                    )
                if trust is None or prior_trust is None or trust < prior_trust:
                    reason_codes.append("semantic_source_trust_regression")
                    _record(
                        findings,
                        observed,
                        "MEMORY_CONFLICT_SEMANTIC_SOURCE_TRUST_REGRESSION",
                        "UPDATE/DELETE rows must not rely on lower-trust source evidence than the prior accepted write.",
                        case_id=event_id,
                        subject_id=event_id,
                        subject_kind="memory_event",
                    )

        row["reason_codes"] = sorted(set(reason_codes))
        if row["reason_codes"]:
            row["computed_verdict"] = "quarantine"
            continue
        if row["decision"] in {"ADD", "UPDATE"} and group_ref:
            prior_by_group[group_ref] = row


def _apply_temporal_order_checks(
    event_rows: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> None:
    accepted_writes = [
        row
        for row in event_rows
        if row["computed_verdict"] != "quarantine"
        and row["decision"] in {"ADD", "UPDATE", "DELETE"}
        and _episode_order(row) is not None
    ]
    first_write_order = min(
        (_episode_order(row) for row in accepted_writes),
        default=None,
    )
    conflict_orders = [
        _episode_order(row)
        for row in event_rows
        if row.get("conflict_edge_ref") and _episode_order(row) is not None
    ]
    latest_conflict_order = max(conflict_orders, default=None)

    for row in event_rows:
        order = _episode_order(row)
        reason_codes = row["reason_codes"]
        event_id = str(row["event_id"])
        if order is None:
            reason_codes.append("episode_order_missing_or_invalid")
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_EPISODE_ORDER_INVALID",
                "Positive memory rows must carry a numeric episode_order for temporal replay.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )
        if row.get("conflict_edge_ref") and (
            order is None
            or first_write_order is None
            or order <= first_write_order
        ):
            reason_codes.append("temporal_conflict_not_after_prior_episode")
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_EPISODE_ORDER_INCOHERENT",
                "Temporal conflict edges must occur after an earlier accepted memory write.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )
        if row["decision"] == "NOOP" and (
            order is None
            or latest_conflict_order is None
            or order <= latest_conflict_order
        ):
            reason_codes.append("replay_not_after_temporal_conflict")
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_REPLAY_ORDER_INCOHERENT",
                "Replay NOOP rows must occur after the temporal conflict and stale downgrade evidence.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )
        row["reason_codes"] = sorted(set(reason_codes))
        if row["reason_codes"]:
            row["computed_verdict"] = "quarantine"


def _apply_public_trace_alignment(
    event_rows: list[dict[str, Any]],
    public_agent_execution_trace: dict[str, Any] | None,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> None:
    spans_by_id = _trace_spans_by_id(public_agent_execution_trace)
    for row in event_rows:
        event_id = str(row["event_id"])
        span_id = f"span:{event_id}"
        span = spans_by_id.get(span_id)
        reason_codes = row["reason_codes"]
        if not span:
            reason_codes.append("public_trace_span_missing")
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_PUBLIC_TRACE_SPAN_MISSING",
                "Positive memory rows must be backed by a public execution-trace span on the run path.",
                case_id=event_id,
                subject_id=event_id,
                subject_kind="memory_event",
            )
        else:
            expected_authority = (
                row.get("conflict_edge_ref")
                or row.get("stale_downgrade_ref")
                or row.get("memory_route_ref")
                or ""
            )
            expected_transition = (
                row.get("stale_downgrade_ref")
                or row.get("conflict_edge_ref")
                or row.get("memory_route_ref")
                or ""
            )
            mismatches = [
                label
                for label, expected, actual in (
                    ("trace_outcome", row.get("decision"), span.get("outcome")),
                    (
                        "trace_evidence_handle",
                        row.get("evidence_handle_ref"),
                        span.get("observation_ref"),
                    ),
                    (
                        "trace_authority_verdict",
                        expected_authority,
                        span.get("authority_verdict_id"),
                    ),
                    (
                        "trace_state_transition",
                        expected_transition,
                        span.get("state_transition_ref"),
                    ),
                    (
                        "trace_memory_subject",
                        row.get("memory_subject_id"),
                        span.get("memory_subject_id"),
                    ),
                )
                if str(expected or "") != str(actual or "")
            ]
            if mismatches:
                reason_codes.append("public_trace_span_mismatch")
                _record(
                    findings,
                    observed,
                    "MEMORY_CONFLICT_PUBLIC_TRACE_SPAN_MISMATCH",
                    "Positive memory row fields must match the public execution-trace span derived on the run path.",
                    case_id=event_id,
                    subject_id=event_id,
                    subject_kind="memory_event",
                )
            row["trace_span_id"] = span_id
            row["trace_backed"] = not mismatches and not reason_codes
        if span is None:
            row["trace_span_id"] = span_id
            row["trace_backed"] = False
        row["reason_codes"] = sorted(set(reason_codes))
        if row["reason_codes"]:
            row["computed_verdict"] = "quarantine"


def validate_memory_episodes(
    payload: object,
    policy: object,
    negative_payloads: dict[str, object],
    *,
    input_dir: Path,
    public_root: Path,
    source_evidence_posture: dict[str, Any],
    public_agent_execution_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy_rows = policy if isinstance(policy, dict) else {}
    allowed = set(_strings(policy_rows.get("allowed_memory_decisions")))
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    event_rows: list[dict[str, Any]] = []
    for row in _rows(payload, "memory_events"):
        event_rows.append(
            _validate_event_row(
                row,
                allowed_decisions=allowed,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for negative_payload in negative_payloads.values():
        negative_rows = _rows(negative_payload, "memory_events")
        if isinstance(negative_payload, dict) and not negative_rows:
            negative_rows = [negative_payload]
        for row in negative_rows:
            _validate_event_row(
                row,
                allowed_decisions=allowed,
                findings=findings,
                observed=observed,
                negative=True,
            )

    _apply_temporal_order_checks(event_rows, findings, observed)
    _apply_conflict_semantic_recompute(event_rows, findings, observed)
    _apply_source_event_alignment(
        event_rows,
        input_dir=input_dir,
        public_root=public_root,
        source_evidence_posture=source_evidence_posture,
        findings=findings,
        observed=observed,
    )
    _apply_public_trace_alignment(
        event_rows,
        public_agent_execution_trace,
        findings,
        observed,
    )

    decision_counts = {
        decision: sum(1 for row in event_rows if row["decision"] == decision)
        for decision in ("ADD", "UPDATE", "DELETE", "NOOP")
    }
    accepted_trace_rows = [
        row
        for row in event_rows
        if row["computed_verdict"] != "quarantine" and row.get("trace_backed") is True
    ]
    conflict_edge_count = sum(
        1 for row in accepted_trace_rows if row.get("conflict_edge_ref")
    )
    stale_downgrade_count = sum(
        1 for row in accepted_trace_rows if row.get("stale_downgrade_ref")
    )
    prompt_adoption_count = sum(
        1 for row in event_rows if row.get("prompt_adoption_observation_ref")
    )
    semantic_checked_rows = [
        row
        for row in event_rows
        if isinstance(row.get("semantic_recompute"), dict)
        and row["semantic_recompute"].get("status") == "checked"
    ]
    semantic_rejected_rows = [
        row
        for row in event_rows
        if any(str(code).startswith("semantic_") for code in row["reason_codes"])
    ]
    source_posture = (
        payload.get("source_evidence_posture", {})
        if isinstance(payload, dict)
        else {}
    )
    source_posture_ok = (
        isinstance(source_posture, dict)
        and source_posture.get("real_source_floor") == SOURCE_BODY_STATUS
        and source_posture.get("body_in_receipt") is False
        and source_posture.get("private_bodies_exported") is False
        and bool(source_posture.get("source_module_manifest_ref"))
    )
    if not source_posture_ok:
        findings.append(
            _finding(
                "MEMORY_CONFLICT_REAL_TRACE_SOURCE_POSTURE_MISSING",
                "Memory episode payload must declare the copied non-secret macro source floor and private-body boundary.",
                case_id="memory_episode_floor",
                subject_id="source_evidence_posture",
                subject_kind="memory_fixture",
            )
        )
    positive_findings = [
        row for row in event_rows if row["computed_verdict"] == "quarantine"
    ]
    floor_blocked = (
        not event_rows
        or any(count < 1 for count in decision_counts.values())
        or conflict_edge_count < 2
        or stale_downgrade_count < 1
        or prompt_adoption_count < 1
        or not source_posture_ok
        or positive_findings
    )
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "MEMORY_CONFLICT_POSITIVE_FLOOR_MISSING",
                "Positive memory fixture must include ADD/UPDATE/DELETE/NOOP decisions, conflict edges, stale downgrade, and prompt-adoption observation refs.",
                case_id="memory_episode_floor",
                subject_id="memory_events",
                subject_kind="memory_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked else "blocked",
        "event_count": len(event_rows),
        "episode_count": len({row["episode_id"] for row in event_rows}),
        "decision_counts": decision_counts,
        "conflict_edge_count": conflict_edge_count,
        "stale_downgrade_count": stale_downgrade_count,
        "trace_backed_event_count": len(accepted_trace_rows),
        "prompt_adoption_observation_count": prompt_adoption_count,
        "semantic_recompute": {
            "schema_version": "memory_temporal_conflict_semantic_recompute_v1",
            "status": PASS if not semantic_rejected_rows else "blocked",
            "checked_conflict_count": len(semantic_checked_rows),
            "rejected_conflict_count": len(semantic_rejected_rows),
            "checked_event_ids": [
                str(row["event_id"]) for row in semantic_checked_rows
            ],
            "rejected_event_ids": [
                str(row["event_id"]) for row in semantic_rejected_rows
            ],
            "required_fields": [
                "event_timestamp",
                "memory_priority",
                "source_trust_score",
            ],
            "source_trust_floor": SOURCE_TRUST_FLOOR,
        },
        "source_evidence_posture": (
            source_posture if isinstance(source_posture, dict) else {}
        ),
        "memory_rows": sorted(event_rows, key=lambda row: str(row["event_id"])),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _validate_replay_row(
    row: dict[str, Any],
    *,
    known_episode_ids: set[str],
    known_evidence_refs: set[str],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("observation_id") or "replay")
    observation_id = str(row.get("observation_id") or case_id)
    subject_kind = "negative_case" if negative else "replay_observation"
    missing = [field for field in REQUIRED_REPLAY_FIELDS if field not in row or row.get(field) in ("", None)]
    evidence_refs = _strings(row.get("evidence_used_refs"))
    episode_id = str(row.get("episode_id") or "")
    unresolved_evidence_refs = sorted(
        ref for ref in evidence_refs if ref not in known_evidence_refs
    )
    reasons: list[str] = []
    if row.get("body_in_receipt") is not False:
        reasons.append("body_in_receipt")
    if not negative and episode_id and episode_id not in known_episode_ids:
        reasons.append("replay_episode_unresolved")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_REPLAY_EPISODE_UNRESOLVED",
            "Replay observations must reference an episode declared by memory events.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if not negative and unresolved_evidence_refs:
        reasons.append("replay_evidence_unresolved")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_REPLAY_EVIDENCE_UNRESOLVED",
            "Replay evidence refs must resolve to public memory evidence handles or receipt refs declared by memory events.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("final_answer_only_memory_credit") is True:
        reasons.append("final_answer_only_credit")
        _record(
            findings,
            observed,
            "MEMORY_CONFLICT_FINAL_ANSWER_ONLY_CREDIT",
            "Memory credit requires evidence handles and cold replay receipts, not final-answer-only comparison.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("memory_enabled") is True and not evidence_refs:
        reasons.append("memory_enabled_without_evidence")
        if not negative:
            _record(
                findings,
                observed,
                "MEMORY_CONFLICT_MEMORY_ENABLED_REPLAY_WITHOUT_EVIDENCE",
                "Memory-enabled replay rows must carry public evidence refs before memory can receive replay credit.",
                case_id=case_id,
                subject_id=observation_id,
                subject_kind=subject_kind,
            )
    if missing:
        reasons.append("replay_field_missing")
    return {
        "observation_id": observation_id,
        "episode_id": episode_id,
        "replay_group_id": str(row.get("replay_group_id") or ""),
        "memory_enabled": row.get("memory_enabled") is True,
        "answer_hash": row.get("answer_hash"),
        "cold_replay_receipt_ref": row.get("cold_replay_receipt_ref"),
        "evidence_used_refs": evidence_refs,
        "unresolved_evidence_refs": unresolved_evidence_refs,
        "episode_resolved": not episode_id or episode_id in known_episode_ids,
        "computed_verdict": "accepted_replay_metadata" if not reasons else "quarantine",
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_in_receipt": False,
    }


def validate_replay_observations(
    payload: object,
    negative_payloads: dict[str, object],
    *,
    memory_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    reference_index = _replay_reference_index(memory_rows or [])
    known_episode_ids = reference_index["episode_ids"]
    known_evidence_refs = reference_index["evidence_refs"]
    for row in _rows(payload, "replay_observations"):
        rows.append(
            _validate_replay_row(
                row,
                known_episode_ids=known_episode_ids,
                known_evidence_refs=known_evidence_refs,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for negative_payload in negative_payloads.values():
        negative_rows = _rows(negative_payload, "replay_observations")
        if isinstance(negative_payload, dict) and not negative_rows:
            negative_rows = [negative_payload]
        for row in negative_rows:
            _validate_replay_row(
                row,
                known_episode_ids=known_episode_ids,
                known_evidence_refs=known_evidence_refs,
                findings=findings,
                observed=observed,
                negative=True,
            )

    enabled = [row for row in rows if row["memory_enabled"]]
    disabled = [row for row in rows if not row["memory_enabled"]]
    delta = payload.get("answer_delta", {}) if isinstance(payload, dict) else {}
    has_delta = (
        isinstance(delta, dict)
        and bool(delta.get("delta_ref"))
        and delta.get("memory_credit_requires_evidence_handle") is True
    )
    positive_findings = [row for row in rows if row["computed_verdict"] == "quarantine"]
    floor_blocked = not rows or not enabled or not disabled or not has_delta or positive_findings
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "MEMORY_CONFLICT_REPLAY_PAIR_FLOOR_MISSING",
                "Replay observations must include paired memory-enabled and memory-disabled cold replay refs plus an answer-delta receipt.",
                case_id="replay_observation_floor",
                subject_id="replay_observations",
                subject_kind="replay_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked else "blocked",
        "replay_observation_count": len(rows),
        "memory_enabled_replay_count": len(enabled),
        "memory_disabled_replay_count": len(disabled),
        "answer_delta_ref": delta.get("delta_ref") if isinstance(delta, dict) else None,
        "answer_delta_claim_effect": delta.get("claim_effect") if isinstance(delta, dict) else None,
        "replay_rows": sorted(rows, key=lambda row: row["observation_id"]),
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
    episode_payload = payloads.get("memory_episodes", {})
    source_posture = _source_evidence_posture(episode_payload)
    source_artifact_paths = _source_artifact_paths(
        input_dir,
        public_root=public_root,
        source_evidence_posture=source_posture,
    )
    secret_scan = scan_paths(
        [
            *_input_paths(input_dir, include_negative=include_negative),
            *source_artifact_paths,
        ],
        forbidden_classes=policy,
        display_root=public_root,
    )
    public_agent_execution_trace = build_public_memory_conflict_trace(input_dir)

    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    projection = validate_projection_protocol(payloads["projection_protocol"])
    memory_policy = validate_memory_policy(payloads["memory_policy"])
    episodes = validate_memory_episodes(
        payloads["memory_episodes"],
        payloads["memory_policy"],
        negative_payloads,
        input_dir=input_dir,
        public_root=public_root,
        source_evidence_posture=source_posture,
        public_agent_execution_trace=public_agent_execution_trace,
    )
    replays = validate_replay_observations(
        payloads["replay_observations"],
        negative_payloads,
        memory_rows=episodes["memory_rows"],
    )
    source_imports = (
        validate_source_module_imports(
            input_dir,
            public_root=public_root,
            source_evidence_posture=source_posture,
        )
        if source_posture.get("source_module_manifest_ref")
        or input_mode == "exported_memory_temporal_conflict_bundle"
        else _empty_source_module_imports()
    )
    source_open_body_imports = _source_open_body_import_summary(source_imports)
    observed = _merge_observed(projection, memory_policy, episodes, replays, source_imports)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(projection, memory_policy, episodes, replays, source_imports)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and public_agent_execution_trace["status"] == PASS
        and projection["status"] == PASS
        and memory_policy["status"] == PASS
        and episodes["status"] == PASS
        and replays["status"] == PASS
        and source_imports["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "agent_memory_temporal_conflict_replay_result_v1",
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
        "public_agent_execution_trace": public_agent_execution_trace,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "target_symbols": projection["target_symbols"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "body_import_status": projection["body_import_status"],
        "body_import_verification": projection["body_import_verification"],
        "memory_policy_id": memory_policy["policy_id"],
        "allowed_memory_decisions": memory_policy["allowed_memory_decisions"],
        "event_count": episodes["event_count"],
        "episode_count": episodes["episode_count"],
        "decision_counts": episodes["decision_counts"],
        "conflict_edge_count": episodes["conflict_edge_count"],
        "stale_downgrade_count": episodes["stale_downgrade_count"],
        "trace_backed_event_count": episodes["trace_backed_event_count"],
        "prompt_adoption_observation_count": episodes["prompt_adoption_observation_count"],
        "semantic_recompute": episodes["semantic_recompute"],
        "source_evidence_posture": episodes["source_evidence_posture"],
        "replay_observation_count": replays["replay_observation_count"],
        "memory_enabled_replay_count": replays["memory_enabled_replay_count"],
        "memory_disabled_replay_count": replays["memory_disabled_replay_count"],
        "answer_delta_ref": replays["answer_delta_ref"],
        "answer_delta_claim_effect": replays["answer_delta_claim_effect"],
        "memory_rows": episodes["memory_rows"],
        "replay_rows": replays["replay_rows"],
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "agent_memory_temporal_conflict_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "agent_memory_temporal_conflict_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "temporal_conflict_edges_before_memory_update",
                "count": result["conflict_edge_count"],
                "authority": "updates_and_deletes_require_conflict_edge_refs",
            },
            {
                "mechanic_id": "stale_memory_downgrade_before_answer_authority",
                "count": result["stale_downgrade_count"],
                "authority": "stale_facts_are_downgraded_before_replay_credit",
            },
            {
                "mechanic_id": "paired_memory_replay_before_utility_claim",
                "count": (
                    result["memory_enabled_replay_count"]
                    + result["memory_disabled_replay_count"]
                ),
                "authority": "memory_enabled_and_disabled_replays_bound_answer_delta",
            },
        ],
        "decision_counts": result["decision_counts"],
        "memory_rows": result["memory_rows"],
        "replay_rows": result["replay_rows"],
        "semantic_recompute": result["semantic_recompute"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_material_status": result["body_material_status"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_import_status": result["body_import_status"],
        "body_import_verification": result["body_import_verification"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
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
        "schema_version": "agent_memory_temporal_conflict_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "agent_memory_temporal_conflict_replay_validation_receipt_v1",
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
        "event_count": result["event_count"],
        "episode_count": result["episode_count"],
        "decision_counts": result["decision_counts"],
        "conflict_edge_count": result["conflict_edge_count"],
        "stale_downgrade_count": result["stale_downgrade_count"],
        "semantic_recompute": result["semantic_recompute"],
        "prompt_adoption_observation_count": result["prompt_adoption_observation_count"],
        "replay_observation_count": result["replay_observation_count"],
        "answer_delta_ref": result["answer_delta_ref"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_material_status": result["body_material_status"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "agent_memory_temporal_conflict_replay_fixture_acceptance_v1",
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
        "source_open_body_imports": result["source_open_body_imports"],
        "semantic_recompute": result["semantic_recompute"],
        "body_material_status": result["body_material_status"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "memory_conflict_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.agent_memory_temporal_conflict_replay run",
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


def run_memory_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.agent_memory_temporal_conflict_replay "
        "run-memory-bundle"
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
        input_mode="exported_memory_temporal_conflict_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_memory_temporal_conflict_bundle_validation_result_v1",
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
        "memory_conflict": {
            "event_count": result.get("event_count"),
            "episode_count": result.get("episode_count"),
            "decision_counts": result.get("decision_counts", {}),
            "conflict_edge_count": result.get("conflict_edge_count"),
            "stale_downgrade_count": result.get("stale_downgrade_count"),
            "semantic_recompute_status": (
                result.get("semantic_recompute", {}).get("status")
                if isinstance(result.get("semantic_recompute"), dict)
                else None
            ),
            "semantic_recompute_checked_conflict_count": (
                result.get("semantic_recompute", {}).get("checked_conflict_count")
                if isinstance(result.get("semantic_recompute"), dict)
                else None
            ),
            "prompt_adoption_observation_count": result.get(
                "prompt_adoption_observation_count"
            ),
            "memory_enabled_replay_count": result.get("memory_enabled_replay_count"),
            "memory_disabled_replay_count": result.get("memory_disabled_replay_count"),
            "answer_delta_ref": result.get("answer_delta_ref"),
        },
        "body_floor": {
            "body_import_status": result.get("body_import_status"),
            "body_material_status": result.get("body_material_status"),
            "body_copied_material_count": result.get("body_copied_material_count"),
            "body_import_verification_mode": (
                result.get("body_import_verification", {}).get("verification_mode")
                if isinstance(result.get("body_import_verification"), dict)
                else None
            ),
            "body_in_receipt": result.get("body_in_receipt") is True,
        },
        "validation": {
            "missing_negative_case_count": len(result.get("missing_negative_cases") or []),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "public_agent_execution_trace_status": (
                result.get("public_agent_execution_trace", {}).get("status")
                if isinstance(result.get("public_agent_execution_trace"), dict)
                else None
            ),
        },
        "authority_boundary": {
            "live_memory_product_claim_authorized": False,
            "private_transcript_export_authorized": False,
            "private_candidate_auto_promotion_authorized": False,
            "memory_as_source_authority_authorized": False,
            "active_injection_authority_authorized": False,
            "provider_calls_authorized": False,
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
    parser = argparse.ArgumentParser(prog="agent_memory_temporal_conflict_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-memory-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.agent_memory_temporal_conflict_replay "
            f"run --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-memory-bundle":
        command = (
            "python -m microcosm_core.organs.agent_memory_temporal_conflict_replay "
            f"run-memory-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_memory_bundle(
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
