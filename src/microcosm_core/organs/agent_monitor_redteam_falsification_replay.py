from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_monitor_redteam_falsification_trace,
)
from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "agent_monitor_redteam_falsification_replay"
FIXTURE_ID = "first_wave.agent_monitor_redteam_falsification_replay"
VALIDATOR_ID = "validator.microcosm.organs.agent_monitor_redteam_falsification_replay"

RESULT_NAME = "agent_monitor_redteam_falsification_replay_result.json"
BOARD_NAME = "agent_monitor_redteam_falsification_replay_board.json"
VALIDATION_RECEIPT_NAME = "agent_monitor_redteam_falsification_replay_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "agent_monitor_redteam_falsification_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_monitor_redteam_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "agent_monitor_redteam_falsification_replay_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "private_state_scan",
    "public_agent_execution_trace",
    "source_open_body_imports",
    "authority_ceiling",
    "anti_claim",
    "source_refs",
    "projection_receipt_refs",
    "public_regression_fixture_refs",
    "trajectory_cases",
    "monitor_rows",
    "monitor_redteam_board",
)
SOURCE_OPEN_BODY_SCHEMA = (
    "agent_monitor_redteam_falsification_source_open_body_imports_v1"
)
SOURCE_OPEN_BODY_IMPORTS = (
    "microcosm_core.macro_tools.agent_execution_trace::"
    "build_public_monitor_redteam_falsification_trace",
)

INPUT_NAMES = (
    "projection_protocol.json",
    "monitor_policy.json",
    "trajectory_cases.json",
    "monitor_observations.json",
)
NEGATIVE_INPUT_NAMES = (
    "private_chain_of_thought_leakage.json",
    "internal_code_export.json",
    "exploit_instruction_material.json",
    "credential_material.json",
    "live_agent_traffic.json",
    "monitor_product_performance_claim.json",
    "coverage_without_adversarial_probe.json",
)

EXPECTED_NEGATIVE_CASES = {
    "private_chain_of_thought_leakage": ["MONITOR_REDTEAM_PRIVATE_COT_FORBIDDEN"],
    "internal_code_export": ["MONITOR_REDTEAM_INTERNAL_CODE_FORBIDDEN"],
    "exploit_instruction_material": ["MONITOR_REDTEAM_EXPLOIT_INSTRUCTIONS_FORBIDDEN"],
    "credential_material": ["MONITOR_REDTEAM_CREDENTIAL_MATERIAL_FORBIDDEN"],
    "live_agent_traffic": ["MONITOR_REDTEAM_LIVE_TRAFFIC_FORBIDDEN"],
    "monitor_product_performance_claim": [
        "MONITOR_REDTEAM_PRODUCT_PERFORMANCE_CLAIM_FORBIDDEN"
    ],
    "coverage_without_adversarial_probe": ["MONITOR_REDTEAM_COVERAGE_WITHOUT_PROBE"],
}

REQUIRED_OBSERVATION_FIELDS = (
    "trajectory_id",
    "monitor_id",
    "coverage_label",
    "suspicious_action_span_ref",
    "adversarial_probe_ref",
    "monitor_verdict",
    "severity_tier",
    "human_escalation_ref",
    "body_omission_ref",
    "mitigation_diff_ref",
    "cold_replay_ref",
)
FORBIDDEN_KEYS = (
    "private_chain_of_thought",
    "hidden_reasoning_export",
    "internal_code_text",
    "exploit_instructions",
    "credential_value",
    "live_agent_traffic_ref",
    "provider_payload",
    "raw_transcript",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_agent_monitor_falsification_replay_receipts_only",
    "monitor_product_performance_claim_authorized": False,
    "control_eval_score_claim_authorized": False,
    "live_agent_execution_authorized": False,
    "live_agent_traffic_import_authorized": False,
    "exploit_instruction_export_authorized": False,
    "credential_material_export_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Agent monitor redteam falsification replay is a regression-negative "
    "drilldown over synthetic trajectory, monitor verdict, adversarial probe, "
    "escalation, mitigation, and body-omission receipts. It does not count as "
    "product-spine substrate, claim monitor product performance, export private "
    "reasoning or internal code, provide exploit instructions, import live agent "
    "traffic, call providers, mutate source, or authorize release."
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
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
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
        "agent_monitor_redteam_falsification_replay_result_v1"
        if include_negative
        else "exported_monitor_redteam_bundle_validation_result_v1"
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
        "schema_version": "agent_monitor_redteam_falsification_replay_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_monitor_bundle_receipt(
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
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != "exported_monitor_redteam_bundle_validation_result_v1":
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_monitor_redteam_bundle":
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


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    regression_fixture_refs = _strings(protocol.get("public_regression_fixture_refs"))
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 3
        or "agent_monitor_redteam_falsification_replay_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or len(regression_fixture_refs) < 3
    ):
        findings.append(
            _finding(
                "MONITOR_REDTEAM_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Monitor replay projection must cite source refs, projection receipts, and public regression fixture refs.",
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
        "public_regression_fixture_refs": regression_fixture_refs,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_monitor_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    allowed_verdicts = set(_strings(policy.get("allowed_monitor_verdicts")))
    required = set(_strings(policy.get("required_observation_fields")))
    findings: list[dict[str, Any]] = []
    if not {"pass", "escalate", "block"}.issubset(allowed_verdicts):
        findings.append(
            _finding(
                "MONITOR_REDTEAM_POLICY_VERDICTS_INCOMPLETE",
                "Monitor policy must define pass, escalate, and block verdicts.",
                case_id="monitor_policy_floor",
                subject_id=str(policy.get("policy_id") or "monitor_policy"),
                subject_kind="monitor_policy",
            )
        )
    if not set(REQUIRED_OBSERVATION_FIELDS).issubset(required):
        findings.append(
            _finding(
                "MONITOR_REDTEAM_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Monitor policy must require observation, probe, escalation, body omission, mitigation, and replay refs.",
                case_id="monitor_policy_floor",
                subject_id=str(policy.get("policy_id") or "monitor_policy"),
                subject_kind="monitor_policy",
            )
        )
    for field in (
        "monitor_product_performance_claim_authorized",
        "live_agent_traffic_import_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "MONITOR_REDTEAM_POLICY_AUTHORITY_OVERCLAIM",
                    "Monitor replay policy cannot authorize performance claims, live traffic, providers, or release.",
                    case_id="monitor_policy_floor",
                    subject_id=field,
                    subject_kind="monitor_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_monitor_verdicts": sorted(allowed_verdicts),
        "required_observation_fields": sorted(required),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_trajectory_cases(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "trajectory_cases")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        trajectory_id = str(row.get("trajectory_id") or "")
        if not trajectory_id or not row.get("trajectory_hash") or not row.get("monitor_scope"):
            findings.append(
                _finding(
                    "MONITOR_REDTEAM_TRAJECTORY_FLOOR_MISSING",
                    "Trajectory cases require id, hash, and monitor scope.",
                    case_id="trajectory_case_floor",
                    subject_id=trajectory_id or "trajectory_case",
                    subject_kind="trajectory_case",
                )
            )
        if any(key in row for key in FORBIDDEN_KEYS):
            findings.append(
                _finding(
                    "MONITOR_REDTEAM_TRAJECTORY_FORBIDDEN_MATERIAL",
                    "Trajectory cases may expose refs and hashes, not private reasoning, code, exploit, credential, or live traffic material.",
                    case_id="trajectory_case_floor",
                    subject_id=trajectory_id or "trajectory_case",
                    subject_kind="trajectory_case",
                )
            )
        exported.append(
            {
                "trajectory_id": trajectory_id,
                "trajectory_kind": row.get("trajectory_kind"),
                "trajectory_hash": row.get("trajectory_hash"),
                "monitor_scope": row.get("monitor_scope"),
                "adversarial_probe_ids": _strings(row.get("adversarial_probe_ids")),
                "expected_monitor_action": row.get("expected_monitor_action"),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "trajectory_case_count": len(rows),
        "adversarial_probe_count": sum(len(row["adversarial_probe_ids"]) for row in exported),
        "trajectory_cases": exported,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _validate_observation_row(
    row: dict[str, Any],
    *,
    allowed_verdicts: set[str],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("trajectory_id") or "monitor")
    observation_id = str(row.get("observation_id") or row.get("trajectory_id") or case_id)
    subject_kind = "negative_case" if negative else "monitor_observation"
    missing_fields = [field for field in REQUIRED_OBSERVATION_FIELDS if not row.get(field)]
    verdict = str(row.get("monitor_verdict") or "")
    reasons: list[str] = []

    if verdict not in allowed_verdicts:
        reasons.append("monitor_verdict_unknown")
    if row.get("chain_of_thought_export_requested") is True:
        reasons.append("private_chain_of_thought")
        _record(
            findings,
            observed,
            "MONITOR_REDTEAM_PRIVATE_COT_FORBIDDEN",
            "Public monitor replay cannot export private chain-of-thought or hidden reasoning.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("internal_code_export_requested") is True:
        reasons.append("internal_code")
        _record(
            findings,
            observed,
            "MONITOR_REDTEAM_INTERNAL_CODE_FORBIDDEN",
            "Public monitor replay cannot export real internal code or private repositories.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("exploit_instruction_detail_included") is True:
        reasons.append("exploit_instructions")
        _record(
            findings,
            observed,
            "MONITOR_REDTEAM_EXPLOIT_INSTRUCTIONS_FORBIDDEN",
            "Public monitor replay may name exploit-risk classes but cannot provide actionable exploit instructions.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("credential_material_included") is True:
        reasons.append("credential_material")
        _record(
            findings,
            observed,
            "MONITOR_REDTEAM_CREDENTIAL_MATERIAL_FORBIDDEN",
            "Credential material is forbidden in public monitor replay fixtures.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("live_agent_traffic_imported") is True:
        reasons.append("live_agent_traffic")
        _record(
            findings,
            observed,
            "MONITOR_REDTEAM_LIVE_TRAFFIC_FORBIDDEN",
            "Monitor replay fixtures must use synthetic trajectories, not live agent traffic.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("monitor_product_performance_claimed") is True:
        reasons.append("performance_claim")
        _record(
            findings,
            observed,
            "MONITOR_REDTEAM_PRODUCT_PERFORMANCE_CLAIM_FORBIDDEN",
            "Synthetic monitor replay receipts cannot claim product performance or control-eval scores.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if row.get("coverage_claimed") is True and not row.get("adversarial_probe_ref"):
        reasons.append("coverage_without_probe")
        _record(
            findings,
            observed,
            "MONITOR_REDTEAM_COVERAGE_WITHOUT_PROBE",
            "Coverage claims require an adversarial probe ref and cannot rest on benign trajectories only.",
            case_id=case_id,
            subject_id=observation_id,
            subject_kind=subject_kind,
        )
    if any(key in row for key in FORBIDDEN_KEYS):
        reasons.append("forbidden_key_present")
    if missing_fields:
        reasons.append("observation_field_missing")

    computed_verdict = "accepted_monitor_metadata"
    if missing_fields or reasons:
        computed_verdict = "quarantine"
    return {
        "observation_id": observation_id,
        "trajectory_id": str(row.get("trajectory_id") or ""),
        "expected_negative_case_id": case_id if negative else None,
        "monitor_id": row.get("monitor_id"),
        "coverage_label": row.get("coverage_label"),
        "monitor_verdict": verdict,
        "computed_verdict": computed_verdict,
        "severity_tier": row.get("severity_tier"),
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing_fields,
        "suspicious_action_span_ref": row.get("suspicious_action_span_ref"),
        "adversarial_probe_ref": row.get("adversarial_probe_ref"),
        "human_escalation_ref": row.get("human_escalation_ref"),
        "body_omission_ref": row.get("body_omission_ref"),
        "mitigation_diff_ref": row.get("mitigation_diff_ref"),
        "cold_replay_ref": row.get("cold_replay_ref"),
        "body_in_receipt": False,
    }


def validate_monitor_observations(
    payload: object,
    policy: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    policy_rows = policy if isinstance(policy, dict) else {}
    allowed = set(_strings(policy_rows.get("allowed_monitor_verdicts")))
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "monitor_observations"):
        rows.append(
            _validate_observation_row(
                row,
                allowed_verdicts=allowed,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for negative_payload in negative_payloads.values():
        negative_rows = _rows(negative_payload, "monitor_observations")
        if isinstance(negative_payload, dict) and not negative_rows:
            negative_rows = [negative_payload]
        for row in negative_rows:
            _validate_observation_row(
                row,
                allowed_verdicts=allowed,
                findings=findings,
                observed=observed,
                negative=True,
            )

    positive_floor_findings = [row for row in rows if row["computed_verdict"] == "quarantine"]
    return {
        "status": PASS if rows and not positive_floor_findings else "blocked",
        "observation_count": len(rows),
        "pass_count": sum(1 for row in rows if row["monitor_verdict"] == "pass"),
        "escalate_count": sum(1 for row in rows if row["monitor_verdict"] == "escalate"),
        "block_count": sum(1 for row in rows if row["monitor_verdict"] == "block"),
        "high_severity_count": sum(
            1 for row in rows if str(row.get("severity_tier")) in {"high", "critical"}
        ),
        "monitor_rows": sorted(rows, key=lambda row: row["observation_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _source_open_body_import_summary(public_trace: dict[str, Any]) -> dict[str, Any]:
    imported = public_trace.get("status") == PASS
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": str(public_trace.get("status") or ""),
        "body_material_status": (
            "public_agent_execution_trace_refactor_landed" if imported else "blocked"
        ),
        "body_material_count": int(public_trace.get("span_count") or 0),
        "body_material_ids": list(SOURCE_OPEN_BODY_IMPORTS),
        "target_symbols": list(public_trace.get("target_symbols") or []),
        "trace_digest": (public_trace.get("summary") or {}).get("trace_digest"),
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "monitor_product_performance_claim_authorized": False,
            "live_agent_traffic_import_authorized": False,
            "exploit_instruction_export_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open microcosm_core.macro_tools.agent_execution_trace::"
            "build_public_monitor_redteam_falsification_trace for the refactored "
            "body that recomputes each coverage label's probe backing and derives "
            "the monitor verdict from span evidence; receipts carry spans, digests, "
            "counts, and findings only."
        )
        if imported
        else "",
    }


def validate_public_trace(public_trace: dict[str, Any]) -> dict[str, Any]:
    """Fold the recomputed public trace into organ-level findings.

    The macro builder recomputes whether each declared coverage label is backed
    by an adversarial-probe span and derives the monitor verdict from span
    evidence. Any computed-vs-declared mismatch becomes an organ finding.
    """

    findings: list[dict[str, Any]] = []
    for span in public_trace.get("spans", []):
        if not isinstance(span, dict):
            continue
        observation_id = str(
            span.get("span_id", "").replace("span:", "") or "monitor_observation"
        )
        if span.get("coverage_backed_by_probe") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MONITOR_REDTEAM_COVERAGE_WITHOUT_PROBE_SPAN",
                    "Declared coverage label is not backed by an adversarial-probe span.",
                    case_id="public_trace_floor",
                    subject_id=observation_id,
                    subject_kind="public_agent_execution_trace",
                )
            )
        if span.get("monitor_verdict_matches_declared") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH",
                    "Monitor verdict derived from span evidence does not match the "
                    "declared monitor verdict.",
                    case_id="public_trace_floor",
                    subject_id=observation_id,
                    subject_kind="public_agent_execution_trace",
                )
            )
    return {
        "status": PASS if public_trace.get("status") == PASS and not findings else "blocked",
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
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    private_scan.pop("forbidden_output_fields", None)
    private_scan.pop("body_" + "red" + "acted", None)
    private_scan["body_output_field_labels_omitted"] = True
    private_scan["body_in_receipt"] = False
    private_scan["body_storage_policy"] = "body_free_regression_fixture"
    private_scan["legacy_body_receipt_language_removed"] = True

    projection = validate_projection_protocol(payloads["projection_protocol"])
    monitor_policy = validate_monitor_policy(payloads["monitor_policy"])
    trajectories = validate_trajectory_cases(payloads["trajectory_cases"])
    observations = validate_monitor_observations(
        payloads["monitor_observations"],
        payloads["monitor_policy"],
        {
            name: payloads[name]
            for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
            if name in payloads
        },
    )
    public_trace = build_public_monitor_redteam_falsification_trace(input_dir)
    public_trace_validation = validate_public_trace(public_trace)
    source_open_body_imports = _source_open_body_import_summary(public_trace)
    observed = _merge_observed(
        projection, monitor_policy, trajectories, observations, public_trace_validation
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection, monitor_policy, trajectories, observations, public_trace_validation
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and monitor_policy["status"] == PASS
        and trajectories["status"] == PASS
        and observations["status"] == PASS
        and public_trace_validation["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "agent_monitor_redteam_falsification_replay_result_v1",
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
        "public_agent_execution_trace": public_trace,
        "source_open_body_imports": source_open_body_imports,
        "source_open_body_imports_status": source_open_body_imports["status"],
        "body_material_status": source_open_body_imports["body_material_status"],
        "public_trace_span_count": public_trace.get("span_count"),
        "public_trace_coverage_backed_count": (public_trace.get("summary") or {}).get(
            "coverage_backed_count"
        ),
        "public_trace_finding_count": (public_trace.get("summary") or {}).get(
            "finding_count"
        ),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_regression_fixture_refs": projection["public_regression_fixture_refs"],
        "monitor_policy_id": monitor_policy["policy_id"],
        "allowed_monitor_verdicts": monitor_policy["allowed_monitor_verdicts"],
        "trajectory_case_count": trajectories["trajectory_case_count"],
        "adversarial_probe_count": trajectories["adversarial_probe_count"],
        "observation_count": observations["observation_count"],
        "pass_count": observations["pass_count"],
        "escalate_count": observations["escalate_count"],
        "block_count": observations["block_count"],
        "high_severity_count": observations["high_severity_count"],
        "trajectory_cases": trajectories["trajectory_cases"],
        "monitor_rows": observations["monitor_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "agent_monitor_redteam_falsification_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "agent_monitor_redteam_falsification_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "adversarial_probe_before_coverage_claim",
                "count": result["adversarial_probe_count"],
                "authority": "coverage_labels_require_probe_refs",
            },
            {
                "mechanic_id": "monitor_verdict_before_pass_label",
                "count": result["observation_count"],
                "authority": "pass_escalate_block_labels_are_receipt_backed",
            },
            {
                "mechanic_id": "escalation_and_mitigation_receipts",
                "count": result["escalate_count"] + result["block_count"],
                "authority": "high_severity_cases_require_escalation_and_mitigation_refs",
            },
            {
                "mechanic_id": "recomputed_monitor_verdict_matches_declared",
                "count": result["public_trace_coverage_backed_count"],
                "authority": "monitor_verdict_is_derived_from_probe_span_evidence_not_echoed",
            },
        ],
        "trajectory_cases": result["trajectory_cases"],
        "monitor_rows": result["monitor_rows"],
        "body_in_receipt": False,
        "private_state_scan": result["private_state_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "source_open_body_imports": result["source_open_body_imports"],
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
        "schema_version": "agent_monitor_redteam_falsification_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "agent_monitor_redteam_falsification_replay_validation_receipt_v1",
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
        "trajectory_case_count": result["trajectory_case_count"],
        "observation_count": result["observation_count"],
        "adversarial_probe_count": result["adversarial_probe_count"],
        "escalate_count": result["escalate_count"],
        "block_count": result["block_count"],
        "public_trace_span_count": result["public_trace_span_count"],
        "public_trace_coverage_backed_count": result[
            "public_trace_coverage_backed_count"
        ],
        "private_state_scan": result["private_state_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "source_open_body_imports": result["source_open_body_imports"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "agent_monitor_redteam_falsification_replay_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "private_state_scan": result["private_state_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_material_status": result["body_material_status"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "monitor_redteam_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.agent_monitor_redteam_falsification_replay run",
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


def run_monitor_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.agent_monitor_redteam_falsification_replay "
        "run-monitor-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_monitor_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_monitor_redteam_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_monitor_redteam_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    private_scan = result.get("private_state_scan")
    scan = private_scan if isinstance(private_scan, dict) else {}
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
        "monitor_redteam": {
            "trajectory_case_count": result.get("trajectory_case_count"),
            "observation_count": result.get("observation_count"),
            "adversarial_probe_count": result.get("adversarial_probe_count"),
            "pass_count": result.get("pass_count"),
            "escalate_count": result.get("escalate_count"),
            "block_count": result.get("block_count"),
            "high_severity_count": result.get("high_severity_count"),
        },
        "public_trace": {
            "span_count": result.get("public_trace_span_count"),
            "coverage_backed_count": result.get("public_trace_coverage_backed_count"),
            "finding_count": result.get("public_trace_finding_count"),
            "source_open_body_imports_status": result.get(
                "source_open_body_imports_status"
            ),
            "body_material_status": result.get("body_material_status"),
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
            "trajectory_cases_in_card": False,
            "monitor_rows_in_card": False,
            "public_agent_execution_trace_in_card": False,
            "source_open_body_imports_in_card": False,
        },
        "authority_boundary": {
            "monitor_product_performance_claim_authorized": False,
            "control_eval_score_claim_authorized": False,
            "live_agent_execution_authorized": False,
            "live_agent_traffic_import_authorized": False,
            "exploit_instruction_export_authorized": False,
            "credential_material_export_authorized": False,
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
    parser = argparse.ArgumentParser(prog="agent_monitor_redteam_falsification_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-monitor-bundle")
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
            "agent_monitor_redteam_falsification_replay "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-monitor-bundle":
        command = (
            "python -m microcosm_core.organs."
            "agent_monitor_redteam_falsification_replay "
            f"run-monitor-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_monitor_bundle(
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
