from __future__ import annotations

import argparse
import hashlib
import json
import math
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


ORGAN_ID = "mechanistic_interpretability_circuit_attribution_replay"
FIXTURE_ID = "first_wave.mechanistic_interpretability_circuit_attribution_replay"
VALIDATOR_ID = (
    "validator.microcosm.organs."
    "mechanistic_interpretability_circuit_attribution_replay"
)

RESULT_NAME = "mechanistic_interpretability_circuit_attribution_replay_result.json"
BOARD_NAME = "mechanistic_interpretability_circuit_attribution_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "mechanistic_interpretability_circuit_attribution_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "mechanistic_interpretability_circuit_attribution_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_circuit_attribution_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
CARD_SCHEMA_VERSION = "mechanistic_interpretability_circuit_attribution_replay_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "features",
    "attribution_replays",
    "positive_findings",
    "negative_case_findings",
    "source_module_summary.modules",
    "source_refs",
    "target_refs",
    "anti_claim",
    "secret_exclusion_scan",
)

INPUT_NAMES = (
    "attribution_protocol.json",
    "intervention_policy.json",
    "feature_catalog.json",
    "attribution_replays.json",
    SOURCE_MODULE_MANIFEST_NAME,
)
NEGATIVE_INPUT_NAMES = (
    "private_model_weights_export.json",
    "raw_activation_dump.json",
    "proprietary_prompt_export.json",
    "hidden_chain_of_thought_export.json",
    "unverifiable_feature_name.json",
    "graph_screenshot_without_edges.json",
    "transparency_claim_without_intervention.json",
    "faithfulness_claim_without_sufficiency_limit.json",
)
HASH_CHUNK_SIZE = 1024 * 1024

EXPECTED_NEGATIVE_CASES = {
    "private_model_weights_export": ["INTERPRETABILITY_PRIVATE_WEIGHTS_FORBIDDEN"],
    "raw_activation_dump": ["INTERPRETABILITY_RAW_ACTIVATION_DUMP_FORBIDDEN"],
    "proprietary_prompt_export": ["INTERPRETABILITY_PROPRIETARY_PROMPT_FORBIDDEN"],
    "hidden_chain_of_thought_export": ["INTERPRETABILITY_HIDDEN_COT_FORBIDDEN"],
    "unverifiable_feature_name": ["INTERPRETABILITY_FEATURE_NAME_UNVERIFIABLE"],
    "graph_screenshot_without_edges": [
        "INTERPRETABILITY_MACHINE_READABLE_EDGES_REQUIRED"
    ],
    "transparency_claim_without_intervention": [
        "INTERPRETABILITY_INTERVENTION_RECEIPT_REQUIRED"
    ],
    "faithfulness_claim_without_sufficiency_limit": [
        "INTERPRETABILITY_FAITHFULNESS_REQUIRES_LIMITS"
    ],
}

REQUIRED_REPLAY_FIELDS = (
    "replay_id",
    "toy_prompt_ref",
    "sparse_feature_ids",
    "attribution_graph_ref",
    "graph_nodes",
    "graph_edges",
    "replacement_model_approximation_score",
    "feature_visualization_summary_refs",
    "causal_inhibition_delta_ref",
    "causal_injection_delta_ref",
    "sufficiency_label",
    "faithfulness_label",
    "faithfulness_limit_ref",
    "uninterpretable_error_node_budget",
    "contradiction_case_ref",
    "cold_replay_ref",
    "private_model_weights_exported",
    "raw_activation_dump_exported",
    "proprietary_prompt_exported",
    "hidden_chain_of_thought_exported",
    "unverifiable_feature_name_claim",
    "graph_screenshot_only",
    "machine_readable_edges_present",
    "transparency_claim",
    "causal_intervention_receipt_ref",
    "faithfulness_claim",
    "release_authorized",
    "target_ref",
    "body_in_receipt",
)

PRIVATE_NEEDLES = (
    "/Users/",
    "src/ai_workflow",
    "Library/Application Support/Google",
    "sk-",
    "model_weights_blob",
    "raw_activation_tensor",
    "proprietary_prompt_body",
    "hidden_chain_of_thought_body",
    "provider_payload_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_circuit_attribution_runtime_receipt_only",
    "public_runtime_receipt_required": True,
    "public_toy_transformer_runtime_authorized": True,
    "private_model_weights_export_authorized": False,
    "raw_activation_dump_export_authorized": False,
    "proprietary_prompt_export_authorized": False,
    "hidden_chain_of_thought_export_authorized": False,
    "model_transparency_product_claim_authorized": False,
    "private_model_internals_claim_authorized": False,
    "live_model_access_authorized": False,
    "benchmark_score_claim_authorized": False,
    "provider_calls_authorized": False,
    "release_authorized": False,
    "hosted_public_authorized": False,
    "publication_authorized": False,
}

ANTI_CLAIM = (
    "Mechanistic interpretability circuit-attribution replay validates public "
    "runtime receipt rows, a deterministic public toy transformer forward, "
    "gradient, and ablation attribution receipt, plus copied public-safe macro "
    "source bodies: toy prompt refs, sparse feature ids, "
    "machine-readable graph edges, replacement-model approximation scores, "
    "causal inhibition and injection deltas, sufficiency and faithfulness "
    "limits, contradiction cases, target refs, cold replay refs, Oracle attribution "
    "nodes, pattern-ledger rows, projection IR, readiness checker code, mission "
    "transaction code, trace code, and standards bodies. Receipts carry refs, "
    "digests, counts, and verdicts only; they do not export private model weights, "
    "raw activation dumps, proprietary prompt bodies, hidden chain-of-thought, "
    "provider payloads, private model internals, benchmark scores, or release authority."
)
BODY_IMPORT_STATUS = "real_runtime_receipt_landed"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_macro_body_landed"
BODY_DIGEST_PREFIX = "sha256:"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = SOURCE_MODULE_IMPORT_STATUS
SOURCE_OPEN_BODY_SCHEMA = (
    "mechanistic_interpretability_circuit_attribution_replay_source_open_body_imports_v1"
)
SOURCE_MODULE_MATERIAL_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_proof_body",
    "public_macro_tool_body",
}
SOURCE_REFS = [
    "microcosm-substrate/receipts/runtime_shell/public_mechanistic_interpretability_circuit_attribution_replay_lens.json",
    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::mechanistic_interpretability_circuit_attribution_replay_compound",
    "codex/nodes/oracle/oracle_attribution_map.json",
    "codex/substrate/nodes/oracle/oracle_attribution_map.json",
    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
    "state/microcosm_portfolio/reconstruction/high_novelty_substrate_gap_scout_v1.json",
    "state/microcosm_portfolio/reconstruction/organ_projection_ir_v1.json",
    "state/microcosm_portfolio/reconstruction/projection_readiness_checker_v1.py",
    "tools/meta/control/mission_transaction_preflight.py",
    "system/lib/agent_execution_trace.py",
    "codex/standards/std_agent_execution_trace.json",
    "codex/standards/std_extracted_pattern_route_readiness.json",
]
TARGET_REFS = [
    "microcosm-substrate/src/microcosm_core/organs/mechanistic_interpretability_circuit_attribution_replay.py",
    "microcosm-substrate/fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input/attribution_replays.json",
    "microcosm-substrate/examples/mechanistic_interpretability_circuit_attribution_replay/exported_circuit_attribution_bundle/attribution_replays.json",
    "microcosm-substrate/examples/mechanistic_interpretability_circuit_attribution_replay/exported_circuit_attribution_bundle/source_module_manifest.json",
]
VALIDATION_REFS = [
    "microcosm-substrate/tests/test_mechanistic_interpretability_circuit_attribution_replay.py::test_mechanistic_interpretability_exported_bundle_validates_runtime_shape",
    "microcosm-substrate/tests/test_mechanistic_interpretability_circuit_attribution_replay.py::test_mechanistic_interpretability_circuit_attribution_receipts_consume_public_runtime_refs",
    "microcosm-substrate/tests/test_mechanistic_interpretability_circuit_attribution_replay.py::test_mechanistic_interpretability_macro_source_modules_are_exact_imports",
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
        "exclude only credential/account/session/provider/live-access material, "
        "private model weights, raw activations, proprietary prompt bodies, and "
        "hidden chain-of-thought bodies"
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


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _target_path_for_ref(target_ref: str, *, public_root: Path) -> Path:
    return public_root / target_ref.removeprefix("microcosm-substrate/")


def _source_file_candidates(source_ref: str, *, public_root: Path) -> list[Path]:
    rel = Path(source_ref.split("::", 1)[0])
    if rel.is_absolute() or ".." in rel.parts:
        return []
    candidates = [public_root / rel, public_root.parent / rel, Path.cwd() / rel]
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _first_existing_source(source_ref: str, *, public_root: Path) -> Path | None:
    for candidate in _source_file_candidates(source_ref, public_root=public_root):
        if candidate.is_file():
            return candidate
    return None


def _sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_ref(path: Path) -> str:
    return f"{BODY_DIGEST_PREFIX}{_sha256_hex(path)}"


def _line_count(path: Path) -> int:
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _source_module_paths(manifest_payload: object, *, public_root: Path) -> list[Path]:
    if not isinstance(manifest_payload, dict):
        return []
    paths: list[Path] = []
    for row in _rows(manifest_payload, "modules"):
        target_ref = row.get("target_ref")
        if isinstance(target_ref, str) and target_ref:
            target = _target_path_for_ref(target_ref, public_root=public_root)
            if target.is_file():
                paths.append(target)
    return paths


def _freshness_input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    public_root = _public_root_for_path(input_dir)
    paths = [*_input_paths(input_dir, include_negative=include_negative)]
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if manifest_path.is_file():
        manifest = read_json_strict(manifest_path)
        paths.extend(_source_module_paths(manifest, public_root=public_root))
    forbidden_policy_path = public_root / "core/private_state_forbidden_classes.json"
    if forbidden_policy_path.is_file():
        paths.append(forbidden_policy_path)
    return paths


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_input_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256_ref(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "mechanistic_interpretability_circuit_attribution_replay_result_v1"
        if include_negative
        else "exported_circuit_attribution_bundle_validation_result_v1"
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
            "mechanistic_interpretability_circuit_attribution_replay_"
            "freshness_basis_v1"
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


def _fresh_bundle_receipt(
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
        "exported_circuit_attribution_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_circuit_attribution_bundle":
        return None
    if payload.get("command") != command:
        return None
    toy_runtime = payload.get("toy_transformer_attribution_runtime")
    if not isinstance(toy_runtime, dict):
        return None
    fabrication_guard = toy_runtime.get("fabrication_guard")
    if not isinstance(fabrication_guard, dict):
        return None
    if toy_runtime.get("spec_source") != "attribution_replays.toy_transformer_runtime":
        return None
    if toy_runtime.get("input_coupled_fixture") is not True:
        return None
    if fabrication_guard.get("passed") is not True:
        return None
    if fabrication_guard.get("input_coupled_verdict") is not True:
        return None
    if fabrication_guard.get("failure_codes") not in ([], ()):
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    cached = dict(payload)
    cached["freshness_basis"] = basis
    cached["receipt_reused"] = True
    return cached


def _source_module_manifest_result(
    manifest_payload: object,
    *,
    public_root: Path,
) -> dict[str, Any]:
    if not isinstance(manifest_payload, dict):
        return {
            "status": "not_present",
            "body_import_status": "not_present",
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "public_safe_body_material_ids": [],
            "body_text_in_receipt": False,
            "findings": [],
        }

    findings: list[dict[str, Any]] = []
    module_results: list[dict[str, Any]] = []
    material_classes: set[str] = set()
    if manifest_payload.get("body_text_in_receipt") is True:
        findings.append(
            {
                "error_code": "INTERPRETABILITY_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                "module_id": SOURCE_MODULE_MANIFEST_NAME,
                "source_ref": "",
                "target_ref": SOURCE_MODULE_MANIFEST_NAME,
                "missing_anchors": [],
                "reasons": ["manifest_body_text_in_receipt_forbidden"],
                "body_in_receipt": False,
            }
        )
    for row in _rows(manifest_payload, "modules"):
        module_id = str(row.get("module_id") or "source_module")
        source_ref = str(row.get("source_ref") or "")
        target_ref = str(row.get("target_ref") or "")
        target = _target_path_for_ref(target_ref, public_root=public_root)
        row_findings: list[str] = []
        material_class = row.get("material_class")

        if row.get("classification") != "copied_non_secret_macro_body":
            row_findings.append("classification_must_be_copied_non_secret_macro_body")
        if material_class not in SOURCE_MODULE_MATERIAL_CLASSES:
            row_findings.append("material_class_must_be_public_macro_pattern_or_tool_body")
        else:
            material_classes.add(str(material_class))
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            row_findings.append("body_must_be_copied_without_receipt_body_text")
        if row.get("body_text_in_receipt") is True:
            row_findings.append("body_text_in_receipt_forbidden")
            findings.append(
                {
                    "error_code": (
                        "INTERPRETABILITY_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN"
                    ),
                    "module_id": module_id,
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "missing_anchors": [],
                    "reasons": ["body_text_in_receipt_forbidden"],
                    "body_in_receipt": False,
                }
            )
        if not target.is_file():
            row_findings.append("target_ref_missing")

        target_digest = _sha256_hex(target) if target.is_file() else ""
        if target_digest and row.get("target_sha256") != target_digest:
            row_findings.append("target_sha256_mismatch")
        if target_digest and row.get("source_sha256") != target_digest:
            row_findings.append("source_target_sha256_mismatch")
        if row.get("sha256_match") is not True:
            row_findings.append("sha256_match_must_be_true")

        required_anchors = _strings(row.get("required_anchors"))
        target_text = target.read_text(encoding="utf-8") if target.is_file() else ""
        missing_anchors = [anchor for anchor in required_anchors if anchor not in target_text]
        if missing_anchors:
            row_findings.append("required_anchor_missing")

        source = _first_existing_source(source_ref, public_root=public_root)
        if source is not None:
            source_digest = _sha256_hex(source)
            if source_digest != target_digest:
                row_findings.append("available_source_digest_mismatch")
            if row.get("line_count") != _line_count(source):
                row_findings.append("source_line_count_mismatch")

        if row_findings:
            findings.append(
                {
                    "error_code": "INTERPRETABILITY_SOURCE_MODULE_IMPORT_INVALID",
                    "module_id": module_id,
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "missing_anchors": missing_anchors,
                    "reasons": row_findings,
                    "body_in_receipt": False,
                }
            )
        module_results.append(
            {
                "module_id": module_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "material_class": row.get("material_class"),
                "classification": row.get("classification"),
                "body_copied": row.get("body_copied"),
                "body_text_in_receipt": False,
                "body_in_receipt": row.get("body_in_receipt"),
                "source_sha256": row.get("source_sha256"),
                "target_sha256": row.get("target_sha256"),
                "target_body_digest": _sha256_ref(target) if target.is_file() else "",
                "line_count": row.get("line_count"),
                "anchor_count": row.get("anchor_count"),
                "required_anchors": required_anchors,
                "status": PASS if not row_findings else "blocked",
            }
        )

    status = PASS if module_results and not findings else "blocked"
    return {
        "status": status,
        "body_import_status": SOURCE_MODULE_IMPORT_STATUS
        if status == PASS
        else "blocked",
        "manifest_id": manifest_payload.get("manifest_id"),
        "bundle_id": manifest_payload.get("bundle_id"),
        "module_count": len(module_results),
        "verified_module_count": sum(1 for row in module_results if row["status"] == PASS),
        "module_ids": [row["module_id"] for row in module_results],
        "public_safe_body_material_ids": [row["module_id"] for row in module_results],
        "material_classes": sorted(material_classes),
        "modules": module_results,
        "body_text_in_receipt": False,
        "body_in_receipt": False,
        "findings": findings,
    }


def _source_open_body_import_summary(
    source_module_summary: dict[str, Any],
    *,
    manifest_ref: str,
) -> dict[str, Any]:
    material_ids = _strings(source_module_summary.get("public_safe_body_material_ids"))
    material_classes = _strings(source_module_summary.get("material_classes"))
    imported = source_module_summary.get("status") == PASS and bool(material_ids)
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": PASS if imported else str(source_module_summary.get("status") or ""),
        "source_import_class": SOURCE_IMPORT_CLASS if imported else "",
        "body_material_status": SOURCE_BODY_STATUS if imported else "",
        "body_material_count": len(material_ids) if imported else 0,
        "body_material_ids": material_ids if imported else [],
        "material_classes": material_classes if imported else [],
        "source_manifest_refs": [manifest_ref] if imported and manifest_ref else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules"
        if imported and manifest_ref
        else "",
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "private_model_weights_exported": False,
            "raw_activation_dump_exported": False,
            "proprietary_prompt_body_exported": False,
            "hidden_chain_of_thought_exported": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "live_model_access_authorized": False,
            "benchmark_score_claim_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported circuit attribution bundle for copied Oracle, pattern-ledger, "
            "projection, mission-transaction, trace, and standards bodies; receipts "
            "carry refs, digests, counts, and verdicts only."
        )
        if imported
        else "",
    }


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


def _replay_policy_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("replay_id") or case_id)
    for field in REQUIRED_REPLAY_FIELDS:
        if field not in row:
            _record(
                findings,
                observed,
                "INTERPRETABILITY_REPLAY_FIELD_REQUIRED",
                f"circuit-attribution replay is missing required field {field}",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="circuit_attribution_replay",
            )

    if not row.get("toy_prompt_ref") or "prompt_body" in row:
        _record(
            findings,
            observed,
            "INTERPRETABILITY_TOY_PROMPT_REF_REQUIRED",
            "replay rows must cite toy prompt refs and omit prompt bodies",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if not _strings(row.get("sparse_feature_ids")):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_FEATURE_IDS_REQUIRED",
            "replay rows must cite sparse feature ids",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if row.get("unverifiable_feature_name_claim") is True:
        _record(
            findings,
            observed,
            "INTERPRETABILITY_FEATURE_NAME_UNVERIFIABLE",
            "feature names must be supported by catalog ids and summaries",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if (
        not row.get("attribution_graph_ref")
        or row.get("machine_readable_edges_present") is not True
        or not _rows(row, "graph_nodes")
        or not _rows(row, "graph_edges")
    ):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_MACHINE_READABLE_EDGES_REQUIRED",
            "attribution graph evidence must include machine-readable nodes and edges",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if row.get("graph_screenshot_only") is True:
        _record(
            findings,
            observed,
            "INTERPRETABILITY_MACHINE_READABLE_EDGES_REQUIRED",
            "graph screenshots alone are not evidence for public attribution rows",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    score = row.get("replacement_model_approximation_score")
    if not isinstance(score, (int, float)) or score < 0 or score > 1:
        _record(
            findings,
            observed,
            "INTERPRETABILITY_APPROXIMATION_SCORE_REQUIRED",
            "replacement model approximation score must be a bounded numeric proxy",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if not _strings(row.get("feature_visualization_summary_refs")):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_FEATURE_VIS_SUMMARY_REQUIRED",
            "feature visualization evidence must be summary refs, not raw activations",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if not row.get("causal_inhibition_delta_ref") or not row.get("causal_injection_delta_ref"):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_CAUSAL_DELTA_REQUIRED",
            "replay rows must cite inhibition and injection delta receipts",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if row.get("transparency_claim") is True and not row.get(
        "causal_intervention_receipt_ref"
    ):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_INTERVENTION_RECEIPT_REQUIRED",
            "transparency language requires a causal intervention receipt ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if row.get("faithfulness_claim") is True and not row.get("faithfulness_limit_ref"):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_FAITHFULNESS_REQUIRES_LIMITS",
            "faithfulness claims require an explicit sufficiency or limit ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    forbidden_flags = {
        "private_model_weights_exported": "INTERPRETABILITY_PRIVATE_WEIGHTS_FORBIDDEN",
        "raw_activation_dump_exported": (
            "INTERPRETABILITY_RAW_ACTIVATION_DUMP_FORBIDDEN"
        ),
        "proprietary_prompt_exported": (
            "INTERPRETABILITY_PROPRIETARY_PROMPT_FORBIDDEN"
        ),
        "hidden_chain_of_thought_exported": "INTERPRETABILITY_HIDDEN_COT_FORBIDDEN",
        "release_authorized": "INTERPRETABILITY_RELEASE_AUTHORITY_FORBIDDEN",
    }
    for field, code in forbidden_flags.items():
        if row.get(field) is True:
            _record(
                findings,
                observed,
                code,
                f"{field} must be false for public circuit-attribution replay rows",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="circuit_attribution_replay",
            )
    if not row.get("target_ref"):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_TARGET_REF_REQUIRED",
            "circuit-attribution rows must cite a public runtime target ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if row.get("body_in_receipt") is not False:
        _record(
            findings,
            observed,
            "INTERPRETABILITY_BODY_RECEIPT_BOUNDARY_REQUIRED",
            "private model, activation, prompt, hidden-reasoning, and provider bodies must stay out of public runtime receipts",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    if any(needle in json.dumps(row, sort_keys=True) for needle in PRIVATE_NEEDLES):
        _record(
            findings,
            observed,
            "INTERPRETABILITY_PRIVATE_OR_RAW_BODY_FORBIDDEN",
            "private weights, raw activations, prompt bodies, hidden reasoning, and provider payloads cannot enter public replay rows",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="circuit_attribution_replay",
        )
    return findings


def _edge_weight(row: dict[str, Any]) -> float:
    weight = row.get("weight")
    return float(weight) if isinstance(weight, (int, float)) else 0.0


def _graph_analysis_for_replay(
    row: dict[str, Any],
    *,
    case_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    replay_id = str(row.get("replay_id") or case_id)
    nodes = _rows(row, "graph_nodes")
    edges = _rows(row, "graph_edges")
    node_ids = {str(node.get("node_id")) for node in nodes if node.get("node_id")}
    start_ids = set(_strings(row.get("sparse_feature_ids")))
    target_ids = {
        str(node.get("node_id"))
        for node in nodes
        if node.get("node_kind") == "public_error_node" and node.get("node_id")
    }
    findings: list[dict[str, Any]] = []
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in node_ids or target not in node_ids:
            findings.append(
                _finding(
                    "INTERPRETABILITY_GRAPH_EDGE_ENDPOINT_UNRESOLVED",
                    "attribution graph edges must resolve to machine-readable graph nodes",
                    case_id=case_id,
                    subject_id=replay_id,
                    subject_kind="circuit_attribution_replay",
                )
            )
        adjacency[source].append(edge)

    path_rows: list[dict[str, Any]] = []
    stack: list[tuple[str, list[str], float]] = [
        (start_id, [start_id], 1.0) for start_id in sorted(start_ids)
    ]
    max_depth = max(len(node_ids), 1)
    while stack:
        node_id, path, path_weight = stack.pop()
        if len(path) > max_depth:
            continue
        if node_id in target_ids and len(path) > 1:
            path_rows.append(
                {
                    "path": path,
                    "target_node_id": node_id,
                    "path_weight": round(path_weight, 6),
                    "body_in_receipt": False,
                }
            )
            continue
        for edge in adjacency.get(node_id, []):
            target = str(edge.get("target") or "")
            if not target or target in path:
                continue
            stack.append(
                (
                    target,
                    [*path, target],
                    path_weight * _edge_weight(edge),
                )
            )

    reachable_targets = {row["target_node_id"] for row in path_rows}
    if not target_ids or not path_rows:
        findings.append(
            _finding(
                "INTERPRETABILITY_GRAPH_PATH_REQUIRED",
                "attribution graph must contain at least one traversable sparse-feature to public-error-node path",
                case_id=case_id,
                subject_id=replay_id,
                subject_kind="circuit_attribution_replay",
            )
        )
    return (
        {
            "replay_id": replay_id,
            "node_count": len(node_ids),
            "edge_count": len(edges),
            "start_feature_ids": sorted(start_ids),
            "target_error_node_ids": sorted(target_ids),
            "path_count": len(path_rows),
            "reachable_error_node_count": len(reachable_targets),
            "max_path_weight": max(
                (float(path["path_weight"]) for path in path_rows),
                default=0.0,
            ),
            "path_rows": sorted(path_rows, key=lambda item: item["path"]),
            "body_in_receipt": False,
        },
        findings,
    )


def _constant_delta_sequence(values: list[float]) -> bool:
    if len(values) < 4:
        return False
    deltas = [round(values[index + 1] - values[index], 6) for index in range(len(values) - 1)]
    return len(set(deltas)) == 1 and deltas[0] != 0


def _weight_sequence_analysis(
    replays: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    edge_columns: dict[int, list[float]] = defaultdict(list)
    for replay in replays:
        for index, edge in enumerate(_rows(replay, "graph_edges")):
            edge_columns[index].append(_edge_weight(edge))
    sequence_rows: list[dict[str, Any]] = []
    for index, values in sorted(edge_columns.items()):
        is_constant_delta = _constant_delta_sequence(values)
        if is_constant_delta:
            findings.append(
                _finding(
                    "INTERPRETABILITY_DECORATIVE_WEIGHT_SEQUENCE",
                    "edge weights must not be simple arithmetic sequences across replay rows",
                    case_id="positive_fixture",
                    subject_id=f"edge_column_{index}",
                    subject_kind="circuit_attribution_replay",
                )
            )
        sequence_rows.append(
            {
                "edge_index": index,
                "weights": values,
                "constant_delta_sequence": is_constant_delta,
                "body_in_receipt": False,
            }
        )
    return (
        {
            "status": PASS if not findings else "blocked",
            "analysis_kind": "graph_weight_sequence_fabrication_check",
            "edge_column_count": len(edge_columns),
            "decorative_sequence_detected": bool(findings),
            "sequence_rows": sequence_rows,
            "body_in_receipt": False,
        },
        findings,
    )


def _round_vector(values: list[float]) -> list[float]:
    return [round(float(value), 6) for value in values]


def _mean_vectors(rows: list[list[float]]) -> list[float]:
    width = len(rows[0])
    return [sum(row[index] for row in rows) / len(rows) for index in range(width)]


def _vector_matrix_product(
    vector: list[float], matrix: list[list[float]]
) -> list[float]:
    width = len(matrix[0])
    return [
        sum(
            vector[row_index] * matrix[row_index][column_index]
            for row_index in range(len(vector))
        )
        for column_index in range(width)
    ]


def _toy_transformer_forward(
    token_ids: list[int],
    embeddings: list[list[float]],
    layer1: list[list[float]],
    layer2: list[list[float]],
) -> dict[str, list[float] | list[list[float]]]:
    token_embeddings = [embeddings[token_id] for token_id in token_ids]
    context = _mean_vectors(token_embeddings)
    hidden_linear = _vector_matrix_product(context, layer1)
    hidden = [math.tanh(value) for value in hidden_linear]
    logits = _vector_matrix_product(hidden, layer2)
    return {
        "token_embeddings": token_embeddings,
        "context": context,
        "hidden_linear": hidden_linear,
        "hidden": hidden,
        "logits": logits,
    }


DEFAULT_TOY_TRANSFORMER_RUNTIME = {
    "token_ids": [0, 1, 2],
    "embeddings": [
        [1.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0],
    ],
    "layer1": [
        [0.8, -0.4, 0.2],
        [0.1, 0.7, -0.6],
    ],
    "layer2": [
        [0.6, -0.2],
        [-0.1, 0.9],
        [0.4, 0.1],
    ],
    "target_logit_index": 1,
    "expected_top_feature_by_attribution": "toy_hidden_feature_1",
    "expected_top_feature_by_ablation": "toy_hidden_feature_1",
}


def _float_matrix(value: object) -> list[list[float]] | None:
    if not isinstance(value, list) or not value:
        return None
    matrix: list[list[float]] = []
    width: int | None = None
    for row in value:
        if not isinstance(row, list) or not row:
            return None
        converted: list[float] = []
        for item in row:
            if not isinstance(item, int | float):
                return None
            converted.append(float(item))
        if width is None:
            width = len(converted)
        elif len(converted) != width:
            return None
        matrix.append(converted)
    return matrix


def _toy_runtime_payload(payload: object | None) -> tuple[dict[str, Any], str]:
    if isinstance(payload, dict) and isinstance(payload.get("toy_transformer_runtime"), dict):
        return dict(payload["toy_transformer_runtime"]), (
            "attribution_replays.toy_transformer_runtime"
        )
    return dict(DEFAULT_TOY_TRANSFORMER_RUNTIME), "internal_default_for_direct_unit_call"


def _toy_transformer_attribution_runtime(payload: object | None = None) -> dict[str, Any]:
    spec, spec_source = _toy_runtime_payload(payload)
    failure_codes: list[str] = []
    token_ids_raw = spec.get("token_ids")
    token_ids = [
        int(item)
        for item in token_ids_raw
        if isinstance(item, int) and not isinstance(item, bool)
    ] if isinstance(token_ids_raw, list) else []
    embeddings = _float_matrix(spec.get("embeddings"))
    layer1 = _float_matrix(spec.get("layer1"))
    layer2 = _float_matrix(spec.get("layer2"))
    target_logit_index = spec.get("target_logit_index")
    if not isinstance(target_logit_index, int) or isinstance(target_logit_index, bool):
        target_logit_index = -1
    if (
        not token_ids
        or embeddings is None
        or layer1 is None
        or layer2 is None
        or any(token_id < 0 or token_id >= len(embeddings) for token_id in token_ids)
        or len(layer1) != len(embeddings[0])
        or len(layer2) != len(layer1[0])
        or target_logit_index < 0
        or target_logit_index >= len(layer2[0])
    ):
        failure_codes.append("INTERPRETABILITY_TOY_TRANSFORMER_SPEC_INVALID")
        token_ids = list(DEFAULT_TOY_TRANSFORMER_RUNTIME["token_ids"])
        embeddings = [list(row) for row in DEFAULT_TOY_TRANSFORMER_RUNTIME["embeddings"]]
        layer1 = [list(row) for row in DEFAULT_TOY_TRANSFORMER_RUNTIME["layer1"]]
        layer2 = [list(row) for row in DEFAULT_TOY_TRANSFORMER_RUNTIME["layer2"]]
        target_logit_index = int(DEFAULT_TOY_TRANSFORMER_RUNTIME["target_logit_index"])
    forward = _toy_transformer_forward(token_ids, embeddings, layer1, layer2)
    hidden = forward["hidden"]
    hidden_linear = forward["hidden_linear"]
    baseline_logit = float(forward["logits"][target_logit_index])
    gradient_scores = [
        layer2[index][target_logit_index] * (1.0 - hidden[index] * hidden[index])
        for index in range(len(hidden))
    ]
    attribution_scores = [
        hidden_linear[index] * gradient_scores[index] for index in range(len(hidden))
    ]
    ablation_rows: list[dict[str, Any]] = []
    for feature_index in range(len(hidden)):
        ablated_hidden = hidden.copy()
        ablated_hidden[feature_index] = 0.0
        ablated_logit = _vector_matrix_product(ablated_hidden, layer2)[target_logit_index]
        ablation_rows.append(
            {
                "feature_id": f"toy_hidden_feature_{feature_index}",
                "ablated_logit": round(ablated_logit, 6),
                "logit_delta_from_baseline": round(baseline_logit - ablated_logit, 6),
                "body_in_receipt": False,
            }
        )
    attribution_rows = [
        {
            "feature_id": f"toy_hidden_feature_{index}",
            "gradient_score": round(float(gradient_scores[index]), 6),
            "activation_gradient_attribution": round(float(attribution_scores[index]), 6),
            "ablation_logit_delta": ablation_rows[index]["logit_delta_from_baseline"],
            "body_in_receipt": False,
        }
        for index in range(len(ablation_rows))
    ]
    top_by_attribution = max(
        attribution_rows,
        key=lambda row: abs(float(row["activation_gradient_attribution"])),
    )["feature_id"]
    top_by_ablation = max(
        ablation_rows,
        key=lambda row: abs(float(row["logit_delta_from_baseline"])),
    )["feature_id"]
    declared_top_by_attribution = str(spec.get("expected_top_feature_by_attribution") or "")
    declared_top_by_ablation = str(spec.get("expected_top_feature_by_ablation") or "")
    declared_matches_recompute = (
        declared_top_by_attribution == top_by_attribution
        and declared_top_by_ablation == top_by_ablation
    )
    if not declared_matches_recompute:
        failure_codes.append(
            "INTERPRETABILITY_TOY_TRANSFORMER_DECLARED_TOP_FEATURE_MISMATCH"
        )
    weight_digest = hashlib.sha256(
        json.dumps(
            {
                "token_ids": token_ids,
                "embeddings": embeddings,
                "layer1": layer1,
                "layer2": layer2,
                "target_logit_index": target_logit_index,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    input_coupled_verdict = (
        top_by_attribution == top_by_ablation
        and declared_matches_recompute
        and not failure_codes
    )
    fabrication_guard_passed = (
        input_coupled_verdict
        and baseline_logit != 0.0
        and any(abs(float(row["logit_delta_from_baseline"])) > 0 for row in ablation_rows)
    )
    return {
        "schema_version": "mechanistic_interpretability_toy_transformer_attribution_v1",
        "status": PASS if fabrication_guard_passed else "blocked",
        "runtime_kind": "pure_python_two_layer_toy_transformer_forward_gradient_ablation",
        "spec_source": spec_source,
        "input_coupled_fixture": spec_source != "internal_default_for_direct_unit_call",
        "model_scope": "public_toy_model_only",
        "token_ids": token_ids,
        "weight_digest": f"sha256:{weight_digest}",
        "target_logit_index": target_logit_index,
        "forward_receipt": {
            "context_vector": _round_vector(forward["context"]),
            "hidden_linear": _round_vector(forward["hidden_linear"]),
            "hidden_activation_summary": _round_vector(forward["hidden"]),
            "logits": _round_vector(forward["logits"]),
            "target_logit": round(baseline_logit, 6),
            "body_in_receipt": False,
        },
        "gradient_scores": attribution_rows,
        "ablation_result": {
            "baseline_target_logit": round(baseline_logit, 6),
            "rows": ablation_rows,
            "top_feature_by_ablation": top_by_ablation,
            "body_in_receipt": False,
        },
        "fabrication_guard": {
            "verdict_source": (
                "fixture_claim_compared_to_recomputed_forward_gradient_ablation"
            ),
            "recompute_input_fields": [
                "token_ids",
                "embeddings",
                "layer1",
                "layer2",
                "target_logit_index",
            ],
            "claimed_top_feature_fields": [
                "expected_top_feature_by_attribution",
                "expected_top_feature_by_ablation",
            ],
            "declared_top_feature_by_attribution": declared_top_by_attribution,
            "declared_top_feature_by_ablation": declared_top_by_ablation,
            "top_feature_by_attribution": top_by_attribution,
            "top_feature_by_ablation": top_by_ablation,
            "declared_matches_recompute": declared_matches_recompute,
            "input_coupled_verdict": input_coupled_verdict,
            "passed": fabrication_guard_passed,
            "failure_codes": sorted(set(failure_codes)),
            "body_in_receipt": False,
        },
        "private_model_weights_exported": False,
        "raw_activation_dump_exported": False,
        "body_in_receipt": False,
    }


def _required_policy_ok(policy: dict[str, Any]) -> bool:
    ceiling = policy.get("authority_ceiling")
    if not isinstance(ceiling, dict):
        return False
    return (
        ceiling.get("public_runtime_receipt_required") is True
        and ceiling.get("public_toy_transformer_runtime_authorized") is True
        and all(
            value is False
            for key, value in ceiling.items()
            if key
            not in {
                "public_runtime_receipt_required",
                "public_toy_transformer_runtime_authorized",
            }
        )
    )


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    public_root = _public_root_for_path(input_dir)
    attribution_protocol = payloads.get("attribution_protocol", {})
    intervention_policy = payloads.get("intervention_policy", {})
    features = _rows(payloads.get("feature_catalog", {}), "features")
    replays = _rows(payloads.get("attribution_replays", {}), "attribution_replays")
    observed_negative_codes: dict[str, set[str]] = defaultdict(set)
    positive_findings: list[dict[str, Any]] = []
    source_module_summary = _source_module_manifest_result(
        payloads.get("source_module_manifest"),
        public_root=public_root,
    )
    manifest_ref = (
        _display(input_dir / SOURCE_MODULE_MANIFEST_NAME, public_root=public_root)
        if (input_dir / SOURCE_MODULE_MANIFEST_NAME).is_file()
        else ""
    )
    source_open_body_imports = _source_open_body_import_summary(
        source_module_summary,
        manifest_ref=manifest_ref,
    )

    if (
        not isinstance(attribution_protocol, dict)
        or attribution_protocol.get("selected_route_id") != ORGAN_ID
    ):
        positive_findings.append(
            _finding(
                "INTERPRETABILITY_PROTOCOL_ROUTE_REQUIRED",
                f"attribution protocol must select {ORGAN_ID}",
                case_id="positive_fixture",
                subject_id="attribution_protocol",
                subject_kind="protocol",
            )
        )
    protocol_target_refs = _strings(attribution_protocol.get("target_refs"))
    protocol_verification = attribution_protocol.get("body_import_verification")
    if attribution_protocol.get("body_import_status") != BODY_IMPORT_STATUS:
        positive_findings.append(
            _finding(
                "INTERPRETABILITY_BODY_IMPORT_STATUS_REQUIRED",
                "attribution protocol must declare the public runtime receipt import status",
                case_id="positive_fixture",
                subject_id="attribution_protocol",
                subject_kind="protocol",
            )
        )
    if TARGET_REFS[0] not in protocol_target_refs:
        positive_findings.append(
            _finding(
                "INTERPRETABILITY_TARGET_REF_REQUIRED",
                "attribution protocol must cite the public circuit-attribution organ target ref",
                case_id="positive_fixture",
                subject_id="attribution_protocol",
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
                "INTERPRETABILITY_BODY_IMPORT_VERIFICATION_REQUIRED",
                "attribution protocol must bind body-import verification for the runtime receipt",
                case_id="positive_fixture",
                subject_id="attribution_protocol",
                subject_kind="protocol",
            )
        )
    if not _required_policy_ok(
        intervention_policy if isinstance(intervention_policy, dict) else {}
    ):
        positive_findings.append(
            _finding(
                "INTERPRETABILITY_AUTHORITY_CEILING_REQUIRED",
                "intervention policy must declare public runtime receipt authority ceiling",
                case_id="positive_fixture",
                subject_id="intervention_policy",
                subject_kind="policy",
            )
        )
    feature_ids = {str(row.get("feature_id")) for row in features if row.get("feature_id")}
    graph_analyses: list[dict[str, Any]] = []
    for row in replays:
        positive_findings.extend(
            _replay_policy_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
            )
        )
        graph_analysis, graph_findings = _graph_analysis_for_replay(
            row,
            case_id="positive_fixture",
        )
        graph_analyses.append(graph_analysis)
        positive_findings.extend(graph_findings)
        for feature_id in _strings(row.get("sparse_feature_ids")):
            if feature_id not in feature_ids:
                positive_findings.append(
                    _finding(
                        "INTERPRETABILITY_FEATURE_CATALOG_REF_REQUIRED",
                        "sparse feature ids must resolve to feature_catalog rows",
                        case_id="positive_fixture",
                        subject_id=str(row.get("replay_id") or feature_id),
                        subject_kind="circuit_attribution_replay",
                    )
                )
    selected_pattern_ids = _strings(attribution_protocol.get("selected_pattern_ids"))
    replay_ids = [str(row.get("replay_id")) for row in replays if row.get("replay_id")]
    if selected_pattern_ids and selected_pattern_ids != replay_ids:
        positive_findings.append(
            _finding(
                "INTERPRETABILITY_SELECTED_PATTERN_IDS_MISMATCH",
                "selected_pattern_ids must exactly match validated replay ids",
                case_id="positive_fixture",
                subject_id="attribution_protocol",
                subject_kind="protocol",
            )
        )
    weight_sequence_analysis, weight_sequence_findings = _weight_sequence_analysis(replays)
    positive_findings.extend(weight_sequence_findings)
    toy_runtime = _toy_transformer_attribution_runtime(payloads.get("attribution_replays"))
    if toy_runtime.get("input_coupled_fixture") is not True:
        positive_findings.append(
            _finding(
                "INTERPRETABILITY_TOY_TRANSFORMER_FIXTURE_SPEC_REQUIRED",
                "mechanistic interpretability proof must load token ids and weights from the public fixture, not the internal default runtime",
                case_id="positive_fixture",
                subject_id="toy_transformer_attribution_runtime",
                subject_kind="runtime_receipt",
            )
        )
    if toy_runtime["status"] != PASS:
        failure_codes = toy_runtime.get("fabrication_guard", {}).get("failure_codes", [])
        for failure_code in failure_codes or [
            "INTERPRETABILITY_TOY_TRANSFORMER_RUNTIME_REQUIRED"
        ]:
            positive_findings.append(
                _finding(
                    str(failure_code),
                    "mechanistic interpretability claim requires a fixture-coupled toy transformer forward, gradient, ablation, and fabrication guard receipt",
                    case_id="positive_fixture",
                    subject_id="toy_transformer_attribution_runtime",
                    subject_kind="runtime_receipt",
                )
            )

    negative_findings: list[dict[str, Any]] = []
    if include_negative:
        for name in NEGATIVE_INPUT_NAMES:
            case_id = Path(name).stem
            payload = payloads.get(case_id, {})
            replay_payload = (
                payload.get("attribution_replay", payload)
                if isinstance(payload, dict)
                else {}
            )
            if isinstance(replay_payload, dict):
                negative_findings.extend(
                    _replay_policy_findings(
                        replay_payload,
                        case_id=case_id,
                        observed=observed_negative_codes,
                    )
                )

    expected_cases = EXPECTED_NEGATIVE_CASES if include_negative else {}
    expected_missing = {
        case_id: sorted(set(codes) - observed_negative_codes.get(case_id, set()))
        for case_id, codes in expected_cases.items()
    }
    expected_missing = {
        case_id: codes for case_id, codes in expected_missing.items() if codes
    }
    encoded_positive = json.dumps(replays, sort_keys=True)
    body_free_public_rows = not any(needle in encoded_positive for needle in PRIVATE_NEEDLES)
    policy_passed = (
        bool(features)
        and bool(replays)
        and not positive_findings
        and weight_sequence_analysis["status"] == PASS
        and toy_runtime["status"] == PASS
        and source_module_summary["status"] in {PASS, "not_present"}
        and body_free_public_rows
        and not expected_missing
        and all(row.get("body_in_receipt") is False for row in replays)
        and all(row.get("private_model_weights_exported") is False for row in replays)
        and all(row.get("raw_activation_dump_exported") is False for row in replays)
        and all(row.get("proprietary_prompt_exported") is False for row in replays)
        and all(row.get("hidden_chain_of_thought_exported") is False for row in replays)
        and all(row.get("machine_readable_edges_present") is True for row in replays)
        and all(row.get("release_authorized") is False for row in replays)
    )

    scan = scan_paths(
        [
            *_input_paths(input_dir, include_negative=include_negative),
            *_source_module_paths(
                payloads.get("source_module_manifest"),
                public_root=public_root,
            ),
        ],
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    status = PASS if policy_passed and scan.get("status") == PASS else "blocked"
    return {
        "schema_version": "mechanistic_interpretability_circuit_attribution_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "input_ref": _display(input_dir, public_root=public_root),
        "selected_route_id": ORGAN_ID,
        "selected_pattern_ids": replay_ids,
        "features": features,
        "attribution_replays": replays,
        "attribution_graph_analyses": graph_analyses,
        "weight_sequence_analysis": weight_sequence_analysis,
        "toy_transformer_attribution_runtime": toy_runtime,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": source_module_summary["body_import_status"],
        "source_module_manifest_ref": manifest_ref,
        "source_module_summary": source_module_summary,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "source_refs": SOURCE_REFS,
        "target_refs": TARGET_REFS,
        "attribution_summary": {
            "feature_count": len(features),
            "replay_count": len(replays),
            "target_ref_count": sum(1 for row in replays if row.get("target_ref")),
            "attribution_edge_count": sum(len(_rows(row, "graph_edges")) for row in replays),
            "attribution_path_count": sum(
                int(row["path_count"]) for row in graph_analyses
            ),
            "reachable_error_node_count": sum(
                int(row["reachable_error_node_count"]) for row in graph_analyses
            ),
            "decorative_weight_sequence_detected": weight_sequence_analysis[
                "decorative_sequence_detected"
            ],
            "toy_transformer_runtime_status": toy_runtime["status"],
            "toy_transformer_input_coupled_fixture": toy_runtime[
                "input_coupled_fixture"
            ],
            "toy_transformer_weight_digest": toy_runtime["weight_digest"],
            "toy_transformer_target_logit": toy_runtime["forward_receipt"][
                "target_logit"
            ],
            "toy_transformer_ablation_count": len(
                toy_runtime["ablation_result"]["rows"]
            ),
            "toy_transformer_top_feature_by_attribution": toy_runtime[
                "fabrication_guard"
            ]["top_feature_by_attribution"],
            "toy_transformer_top_feature_by_ablation": toy_runtime[
                "fabrication_guard"
            ]["top_feature_by_ablation"],
            "toy_transformer_fabrication_guard_passed": toy_runtime[
                "fabrication_guard"
            ]["passed"],
            "causal_intervention_count": sum(
                1
                for row in replays
                if row.get("causal_inhibition_delta_ref")
                and row.get("causal_injection_delta_ref")
            ),
            "contradiction_case_count": sum(
                1 for row in replays if row.get("contradiction_case_ref")
            ),
            "cold_replay_count": sum(1 for row in replays if row.get("cold_replay_ref")),
            "private_weight_export_count": sum(
                1 for row in replays if row.get("private_model_weights_exported") is True
            ),
            "raw_activation_dump_export_count": sum(
                1 for row in replays if row.get("raw_activation_dump_exported") is True
            ),
            "proprietary_prompt_export_count": sum(
                1 for row in replays if row.get("proprietary_prompt_exported") is True
            ),
            "hidden_chain_of_thought_export_count": sum(
                1 for row in replays if row.get("hidden_chain_of_thought_exported") is True
            ),
            "transparency_claim_count": sum(
                1 for row in replays if row.get("transparency_claim") is True
            ),
        },
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
            "private_model_weights_omitted": True,
            "raw_activation_dumps_omitted": True,
            "proprietary_prompt_bodies_omitted": True,
            "hidden_chain_of_thought_omitted": True,
            "provider_payloads_omitted": True,
        },
        "release_authorized": False,
        "body_in_receipt": False,
        "secret_exclusion_scan": scan,
    }


def _board(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("attribution_summary", {})
    negatives = result.get("negative_case_summary", {})
    return {
        "schema_version": "mechanistic_interpretability_circuit_attribution_replay_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "mechanistic_interpretability_circuit_attribution_public_board",
        "route": ORGAN_ID,
        "feature_count": summary.get("feature_count", 0)
        if isinstance(summary, dict)
        else 0,
        "replay_count": summary.get("replay_count", 0) if isinstance(summary, dict) else 0,
        "attribution_edge_count": summary.get("attribution_edge_count", 0)
        if isinstance(summary, dict)
        else 0,
        "attribution_path_count": summary.get("attribution_path_count", 0)
        if isinstance(summary, dict)
        else 0,
        "reachable_error_node_count": summary.get("reachable_error_node_count", 0)
        if isinstance(summary, dict)
        else 0,
        "decorative_weight_sequence_detected": summary.get(
            "decorative_weight_sequence_detected",
            True,
        )
        if isinstance(summary, dict)
        else True,
        "toy_transformer_runtime_status": summary.get(
            "toy_transformer_runtime_status"
        )
        if isinstance(summary, dict)
        else None,
        "toy_transformer_input_coupled_fixture": summary.get(
            "toy_transformer_input_coupled_fixture", False
        )
        if isinstance(summary, dict)
        else False,
        "toy_transformer_weight_digest": summary.get(
            "toy_transformer_weight_digest", ""
        )
        if isinstance(summary, dict)
        else "",
        "toy_transformer_ablation_count": summary.get(
            "toy_transformer_ablation_count", 0
        )
        if isinstance(summary, dict)
        else 0,
        "toy_transformer_top_feature_by_attribution": summary.get(
            "toy_transformer_top_feature_by_attribution", ""
        )
        if isinstance(summary, dict)
        else "",
        "toy_transformer_top_feature_by_ablation": summary.get(
            "toy_transformer_top_feature_by_ablation", ""
        )
        if isinstance(summary, dict)
        else "",
        "toy_transformer_fabrication_guard_passed": summary.get(
            "toy_transformer_fabrication_guard_passed", False
        )
        if isinstance(summary, dict)
        else False,
        "toy_transformer_attribution_runtime": result.get(
            "toy_transformer_attribution_runtime"
        ),
        "causal_intervention_count": summary.get("causal_intervention_count", 0)
        if isinstance(summary, dict)
        else 0,
        "negative_case_count": negatives.get("expected_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "observed_negative_case_count": negatives.get("observed_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "authority_ceiling": AUTHORITY_CEILING,
        "toy_transformer_attribution_runtime": result.get(
            "toy_transformer_attribution_runtime"
        ),
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result.get("source_module_manifest_ref", ""),
        "source_module_summary": result["source_module_summary"],
        "source_open_body_imports": result.get("source_open_body_imports"),
        "body_copied_material_count": result.get("body_copied_material_count", 0),
        "target_refs": TARGET_REFS,
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
        "schema_version": (
            "mechanistic_interpretability_circuit_attribution_replay_"
            "validation_receipt_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "receipt_paths": receipt_paths,
        "replay_count": (result.get("attribution_summary") or {}).get("replay_count"),
        "expected_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "expected_negative_case_count"
        ),
        "observed_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "observed_negative_case_count"
        ),
        "authority_ceiling": AUTHORITY_CEILING,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result.get("source_module_manifest_ref", ""),
        "source_module_summary": result["source_module_summary"],
        "source_open_body_imports": result.get("source_open_body_imports"),
        "body_copied_material_count": result.get("body_copied_material_count", 0),
        "target_refs": TARGET_REFS,
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
        "schema_version": (
            "mechanistic_interpretability_circuit_attribution_replay_"
            "fixture_acceptance_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "validation_ref": receipt_paths[2],
        "authority_ceiling": AUTHORITY_CEILING,
        "toy_transformer_attribution_runtime": result.get(
            "toy_transformer_attribution_runtime"
        ),
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result.get("source_module_manifest_ref", ""),
        "source_module_summary": result["source_module_summary"],
        "source_open_body_imports": result.get("source_open_body_imports"),
        "body_copied_material_count": result.get("body_copied_material_count", 0),
        "target_refs": TARGET_REFS,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "release_authorized": False,
        "body_in_receipt": False,
    }
    write_json_atomic(acceptance_path, acceptance)
    return {
        **result,
        "mechanistic_interpretability_board": board,
        "receipt_paths": receipt_paths,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs."
        "mechanistic_interpretability_circuit_attribution_replay run"
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


def run_attribution_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "mechanistic_interpretability_circuit_attribution_replay run-attribution-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_circuit_attribution_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_circuit_attribution_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("attribution_summary")
    attribution_summary = summary if isinstance(summary, dict) else {}
    negatives = result.get("negative_case_summary")
    negative_summary = negatives if isinstance(negatives, dict) else {}
    source_modules = result.get("source_module_summary")
    source_module_summary = source_modules if isinstance(source_modules, dict) else {}
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    scan_payload = result.get("secret_exclusion_scan")
    scan = scan_payload if isinstance(scan_payload, dict) else {}
    expected_missing = negative_summary.get("expected_missing")
    missing_negative_count = (
        len(expected_missing) if isinstance(expected_missing, dict) else 0
    )
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "selected_route_id": result.get("selected_route_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "circuit_attribution": {
            "feature_count": attribution_summary.get("feature_count"),
            "replay_count": attribution_summary.get("replay_count"),
            "target_ref_count": attribution_summary.get("target_ref_count"),
            "attribution_edge_count": attribution_summary.get(
                "attribution_edge_count"
            ),
            "attribution_path_count": attribution_summary.get(
                "attribution_path_count"
            ),
            "reachable_error_node_count": attribution_summary.get(
                "reachable_error_node_count"
            ),
            "decorative_weight_sequence_detected": attribution_summary.get(
                "decorative_weight_sequence_detected"
            ),
            "toy_transformer_runtime_status": attribution_summary.get(
                "toy_transformer_runtime_status"
            ),
            "toy_transformer_input_coupled_fixture": attribution_summary.get(
                "toy_transformer_input_coupled_fixture"
            ),
            "toy_transformer_weight_digest": attribution_summary.get(
                "toy_transformer_weight_digest"
            ),
            "toy_transformer_target_logit": attribution_summary.get(
                "toy_transformer_target_logit"
            ),
            "toy_transformer_ablation_count": attribution_summary.get(
                "toy_transformer_ablation_count"
            ),
            "toy_transformer_top_feature_by_attribution": attribution_summary.get(
                "toy_transformer_top_feature_by_attribution"
            ),
            "toy_transformer_top_feature_by_ablation": attribution_summary.get(
                "toy_transformer_top_feature_by_ablation"
            ),
            "toy_transformer_fabrication_guard_passed": attribution_summary.get(
                "toy_transformer_fabrication_guard_passed"
            ),
            "causal_intervention_count": attribution_summary.get(
                "causal_intervention_count"
            ),
            "contradiction_case_count": attribution_summary.get(
                "contradiction_case_count"
            ),
            "cold_replay_count": attribution_summary.get("cold_replay_count"),
            "source_module_import_status": result.get(
                "source_module_import_status"
            ),
            "source_module_count": source_module_summary.get("module_count"),
            "verified_source_module_count": source_module_summary.get(
                "verified_module_count"
            ),
            "body_import_status": result.get("body_import_status"),
            "source_open_body_material_count": result.get(
                "body_copied_material_count"
            ),
        },
        "validation": {
            "finding_count": result.get("finding_count"),
            "expected_negative_case_count": negative_summary.get(
                "expected_negative_case_count"
            ),
            "observed_negative_case_count": negative_summary.get(
                "observed_negative_case_count"
            ),
            "missing_negative_case_count": missing_negative_count,
            "secret_exclusion_status": scan.get("status"),
            "secret_blocking_hit_count": scan.get("blocking_hit_count"),
        },
        "body_floor": {
            "body_in_receipt": False,
            "features_in_card": False,
            "attribution_replays_in_card": False,
            "secret_exclusion_scan_in_card": False,
            "source_module_bodies_in_card": False,
            "source_open_body_imports_in_card": False,
        },
        "authority_boundary": {
            "private_model_weights_export_authorized": False,
            "raw_activation_dump_export_authorized": False,
            "proprietary_prompt_export_authorized": False,
            "hidden_chain_of_thought_export_authorized": False,
            "private_model_internals_claim_authorized": False,
            "provider_calls_authorized": False,
            "benchmark_score_claim_authorized": False,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
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
        prog="mechanistic_interpretability_circuit_attribution_replay"
    )
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-attribution-bundle")
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
            "mechanistic_interpretability_circuit_attribution_replay "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-attribution-bundle":
        command = (
            "python -m microcosm_core.organs."
            "mechanistic_interpretability_circuit_attribution_replay "
            f"run-attribution-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_attribution_bundle(
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
