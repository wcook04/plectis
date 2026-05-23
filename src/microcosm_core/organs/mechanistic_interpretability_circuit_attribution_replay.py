from __future__ import annotations

import argparse
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

INPUT_NAMES = (
    "attribution_protocol.json",
    "intervention_policy.json",
    "feature_catalog.json",
    "attribution_replays.json",
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
    "body-free runtime receipt rows: toy prompt refs, sparse feature ids, "
    "machine-readable graph edges, replacement-model approximation scores, "
    "causal inhibition and injection deltas, sufficiency and faithfulness "
    "limits, contradiction cases, target refs, and cold replay refs. It does "
    "not export private model weights, raw activation dumps, proprietary prompt "
    "bodies, hidden chain-of-thought, provider payloads, private model internals, "
    "benchmark scores, or release authority."
)
BODY_IMPORT_STATUS = "real_runtime_receipt_landed"
SOURCE_REFS = [
    "microcosm-substrate/receipts/runtime_shell/public_mechanistic_interpretability_circuit_attribution_replay_lens.json",
    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::mechanistic_interpretability_circuit_attribution_replay_compound",
]
TARGET_REFS = [
    "microcosm-substrate/src/microcosm_core/organs/mechanistic_interpretability_circuit_attribution_replay.py",
    "microcosm-substrate/fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input/attribution_replays.json",
    "microcosm-substrate/examples/mechanistic_interpretability_circuit_attribution_replay/exported_circuit_attribution_bundle/attribution_replays.json",
]
VALIDATION_REFS = [
    "microcosm-substrate/tests/test_mechanistic_interpretability_circuit_attribution_replay.py::test_mechanistic_interpretability_exported_bundle_validates_runtime_shape",
    "microcosm-substrate/tests/test_mechanistic_interpretability_circuit_attribution_replay.py::test_mechanistic_interpretability_circuit_attribution_receipts_consume_public_runtime_refs",
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
        if candidate.name == "microcosm-substrate":
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
    for row in replays:
        positive_findings.extend(
            _replay_policy_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
            )
        )
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
        _input_paths(input_dir, include_negative=include_negative),
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
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
        "source_refs": SOURCE_REFS,
        "target_refs": TARGET_REFS,
        "attribution_summary": {
            "feature_count": len(features),
            "replay_count": len(replays),
            "target_ref_count": sum(1 for row in replays if row.get("target_ref")),
            "attribution_edge_count": sum(len(_rows(row, "graph_edges")) for row in replays),
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
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
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
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": BODY_IMPORT_VERIFICATION,
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
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_circuit_attribution_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_circuit_attribution_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mechanistic_interpretability_circuit_attribution_replay"
    )
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-attribution-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-attribution-bundle":
        result = run_attribution_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
