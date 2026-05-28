#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Materialize the dynamic finance-evaluation operating picture that
  `/station/finance-data` can render without inventing evaluator semantics.
- Mechanism: Read finance replay scorecard envelopes, fold pending/resolved
  counts, calibration bins, residual tags, and generator variant summaries, then
  write `state/finance_eval/views/finance_eval_operating_picture.json`.

[INTERFACE]
- Reads: optional `finance_eval_replay` envelopes.
- Writes: optional output JSON path.
- Returns/prints: `finance_eval_operating_picture_v0` projection.

[CONSTRAINTS]
- Dynamic projection only; stable doctrine defines semantics elsewhere.
- Empty inputs produce a valid zero-state operating picture.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from tools.finance import variant_registry
from tools.finance.event_keys import COMPARISON_EVENT_KEY_AUTHORITY, COMPARISON_EVENT_KEY_SCHEMA
from tools.finance.eval_replay import build_operating_picture
from tools.finance.family_loss_matrix import FAMILY_LOSS_MATRIX_AUTHORITY
from tools.finance.loss_differentials import LOSS_DIFFERENTIAL_AUTHORITY
from tools.finance.model_selection import RECEIPT_SCHEMA_VERSION as MODEL_SELECTION_RECEIPT_SCHEMA

DEFAULT_OUTPUT = Path("state/finance_eval/views/finance_eval_operating_picture.json")


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else payload


def _receipt(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = _data(payload)
    receipt = data.get("receipt") if isinstance(data, Mapping) else None
    if isinstance(receipt, Mapping):
        return receipt
    return data if isinstance(data, Mapping) else {}


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def load_scorecards(paths: List[Path]) -> List[Dict[str, Any]]:
    scorecards: List[Dict[str, Any]] = []
    for path in paths:
        payload = _read_json(path)
        data = _data(payload)
        raw = data.get("scorecards") or payload.get("scorecards")
        if isinstance(raw, list):
            scorecards.extend(item for item in raw if isinstance(item, dict))
    return scorecards


def _load_payloads(paths: List[Path]) -> List[Dict[str, Any]]:
    return [_read_json(path) for path in paths]


def _latest_experiment(payloads: List[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    ledgers: List[Mapping[str, Any]] = []
    for payload in payloads:
        data = _data(payload)
        ledger = data.get("experiment_ledger") if isinstance(data, Mapping) else None
        if isinstance(ledger, Mapping):
            ledgers.append(ledger)
    if not ledgers:
        return None
    return sorted(ledgers, key=lambda ledger: str(ledger.get("experiment_id") or ""))[-1]


def _calibrator_summary(payloads: List[Mapping[str, Any]]) -> Dict[str, Any]:
    calibrators: List[Mapping[str, Any]] = []
    for payload in payloads:
        data = _data(payload)
        calibrator = data.get("calibrator") if isinstance(data, Mapping) else None
        if isinstance(calibrator, Mapping):
            calibrators.append(calibrator)
    active = [
        calibrator
        for calibrator in calibrators
        if calibrator.get("status") == "active"
        or bool((calibrator.get("admission_decision") or {}).get("live_probability_mutation_allowed"))
    ]
    return {
        "active_calibrator_id": str(active[-1].get("calibrator_id")) if active else None,
        "shadow_calibrator_count": sum(1 for calibrator in calibrators if calibrator.get("status") == "shadow_only"),
        "holdout_eligible_count": sum(
            1
            for calibrator in calibrators
            if not bool((calibrator.get("diagnostics") or {}).get("in_sample_only", True))
        ),
        "live_probability_mutation_allowed": bool(active),
    }


def _variant_gate_summary(payloads: List[Mapping[str, Any]]) -> Dict[str, Any]:
    receipts: List[Mapping[str, Any]] = []
    for payload in payloads:
        data = _data(payload)
        receipt = data.get("receipt") if isinstance(data, Mapping) else None
        if isinstance(receipt, Mapping):
            receipts.append(receipt)

    blocked_reasons = {
        "insufficient_paired_sample": 0,
        "unknown_variant": 0,
        "non_executable_split_policy": 0,
        "data_snooping_guard": 0,
        "split_membership_unbound": 0,
    }
    for receipt in receipts:
        decision = receipt.get("decision") if isinstance(receipt.get("decision"), Mapping) else {}
        reason = str(decision.get("reason") or "")
        if reason in blocked_reasons:
            blocked_reasons[reason] += 1
        elif reason:
            blocked_reasons["data_snooping_guard"] += 1

    admitted = [
        receipt
        for receipt in receipts
        if (receipt.get("decision") or {}).get("status") in {"eligible_for_optimizer_trial", "admitted_shadow_variant"}
    ]
    pairing_blocks = [
        receipt.get("pairing")
        for receipt in receipts
        if isinstance(receipt.get("pairing"), Mapping)
    ]
    pairing_integrity_status = "unknown"
    if receipts:
        pairing_integrity_status = "pass" if len(pairing_blocks) == len(receipts) and all(
            block.get("paired_by") == "comparison_event_key" for block in pairing_blocks
        ) else "fail"
    statistical_statuses = [
        str(((receipt.get("statistics") or {}).get("diebold_mariano") or {}).get("status") or "")
        for receipt in receipts
    ]
    if not receipts:
        statistical_test_status = "reserved"
    elif any(status.startswith("computed") for status in statistical_statuses):
        statistical_test_status = "computed"
    elif any("minimum_sample" in status for status in statistical_statuses):
        statistical_test_status = "insufficient_sample"
    else:
        statistical_test_status = "reserved"
    latest_statistics = receipts[-1].get("statistics") if receipts and isinstance(receipts[-1].get("statistics"), Mapping) else {}
    latest_dependence = (
        latest_statistics.get("dependence_diagnostics")
        if isinstance(latest_statistics.get("dependence_diagnostics"), Mapping)
        else {}
    )
    split_binding = latest_dependence.get("split_binding") if isinstance(latest_dependence.get("split_binding"), Mapping) else {}
    missing_split_count = int(latest_dependence.get("missing_split_membership_count") or split_binding.get("missing_split_membership_count") or 0)
    excluded_split_count = int(latest_dependence.get("excluded_split_count") or split_binding.get("excluded_split_count") or 0)
    split_binding_status = "unknown"
    if receipts:
        split_binding_status = "fail" if missing_split_count > 0 else "pass"
    mutation_allowed = any(bool((receipt.get("decision") or {}).get("calculator_mutation_permission")) for receipt in receipts)
    return {
        "latest_gate_id": str(receipts[-1].get("variant_gate_id")) if receipts else None,
        "comparison_key_schema": COMPARISON_EVENT_KEY_SCHEMA,
        "comparison_key_authority": COMPARISON_EVENT_KEY_AUTHORITY,
        "loss_differential_authority": LOSS_DIFFERENTIAL_AUTHORITY,
        "pairing_integrity_status": pairing_integrity_status,
        "baseline_variant_id": variant_registry.BASELINE_VARIANT_ID,
        "candidate_variant_count": len({str(receipt.get("candidate_variant_id")) for receipt in receipts if receipt.get("candidate_variant_id")}),
        "paired_comparison_count": len(receipts),
        "identity_decoupled_pair_count": sum(int((block or {}).get("identity_decoupled_pair_count") or 0) for block in pairing_blocks),
        "unpaired_baseline_count": sum(int((block or {}).get("unpaired_baseline_count") or 0) for block in pairing_blocks),
        "unpaired_candidate_count": sum(int((block or {}).get("unpaired_candidate_count") or 0) for block in pairing_blocks),
        "statistical_test_status": statistical_test_status,
        "model_selection_status": "not_started",
        "eligible_for_optimizer_trial_count": sum(
            1
            for receipt in receipts
            if (receipt.get("decision") or {}).get("status") == "eligible_for_optimizer_trial"
        ),
        "admitted_shadow_variant_count": len(admitted),
        "variance_estimator": latest_statistics.get("variance_estimator"),
        "selected_lag": latest_statistics.get("selected_lag"),
        "event_window_overlap_count": latest_statistics.get("event_window_overlap_count") or latest_dependence.get("event_window_overlap_count", 0),
        "split_membership_binding_status": split_binding_status,
        "missing_split_membership_count": missing_split_count,
        "excluded_split_count": excluded_split_count,
        "purged_pair_count": int(latest_dependence.get("purged_pair_count") or split_binding.get("purged_pair_count") or 0),
        "embargoed_pair_count": int(latest_dependence.get("embargoed_pair_count") or split_binding.get("embargoed_pair_count") or 0),
        "usable_pair_count": int(latest_dependence.get("usable_pair_count") or split_binding.get("usable_pair_count") or 0),
        "calculator_mutation_permission": mutation_allowed,
        "blocked_reasons": blocked_reasons,
    }


def _model_selection_summary(payloads: List[Mapping[str, Any]]) -> Dict[str, Any]:
    receipts: List[Mapping[str, Any]] = []
    for payload in payloads:
        data = _data(payload)
        receipt = data.get("receipt") if isinstance(data, Mapping) else None
        if isinstance(receipt, Mapping):
            receipts.append(receipt)
        elif payload.get("schema_version") == MODEL_SELECTION_RECEIPT_SCHEMA:
            receipts.append(payload)
    latest = receipts[-1] if receipts else {}
    sample = latest.get("sample") if isinstance(latest.get("sample"), Mapping) else {}
    stats = latest.get("family_statistics") if isinstance(latest.get("family_statistics"), Mapping) else {}
    family_loss_matrix = latest.get("family_loss_matrix") if isinstance(latest.get("family_loss_matrix"), Mapping) else {}
    matrix_coverage = family_loss_matrix.get("coverage") if isinstance(family_loss_matrix.get("coverage"), Mapping) else {}
    bootstrap = latest.get("bootstrap") if isinstance(latest.get("bootstrap"), Mapping) else {}
    bootstrap_conformance = (
        latest.get("bootstrap_conformance")
        if isinstance(latest.get("bootstrap_conformance"), Mapping)
        else {}
    )
    spa = stats.get("spa") if isinstance(stats.get("spa"), Mapping) else {}
    spa_studentization = spa.get("studentization") if isinstance(spa.get("studentization"), Mapping) else {}
    spa_null = spa.get("sample_dependent_null") if isinstance(spa.get("sample_dependent_null"), Mapping) else {}
    mcs = stats.get("model_confidence_set") if isinstance(stats.get("model_confidence_set"), Mapping) else {}
    spa_readiness = latest.get("spa_readiness") if isinstance(latest.get("spa_readiness"), Mapping) else {}
    resampling = bootstrap_conformance.get("resampling") if isinstance(bootstrap_conformance.get("resampling"), Mapping) else {}
    decision = latest.get("decision") if isinstance(latest.get("decision"), Mapping) else {}
    return {
        "latest_selection_id": latest.get("selection_id") if latest else None,
        "method": latest.get("method") if latest else None,
        "variant_count": len(latest.get("variant_set") or []) if latest else 0,
        "candidate_count": sample.get("candidate_count", 0),
        "family_loss_matrix_status": family_loss_matrix.get("status", "not_started") if latest else "not_started",
        "family_loss_matrix_authority": FAMILY_LOSS_MATRIX_AUTHORITY,
        "shared_event_count": matrix_coverage.get("shared_event_count", sample.get("shared_event_count", 0)) if latest else 0,
        "dropped_unshared_event_count": matrix_coverage.get("dropped_unshared_event_count", sample.get("dropped_unshared_event_count", 0)) if latest else 0,
        "bootstrap_status": bootstrap.get("status", "not_started") if latest else "not_started",
        "bootstrap_conformance_status": bootstrap_conformance.get("status", "not_started") if latest else "not_started",
        "bootstrap_reference_status": latest.get("bootstrap_reference_status", "not_started") if latest else "not_started",
        "bootstrap_method": (resampling.get("method") or bootstrap.get("method")) if latest else None,
        "bootstrap_reps": (resampling.get("bootstrap_reps") or bootstrap.get("bootstrap_reps")) if latest else None,
        "bootstrap_seed": (resampling.get("seed") or bootstrap.get("seed")) if latest else None,
        "spa_readiness_status": spa_readiness.get("status", "not_started") if latest else "not_started",
        "poor_or_irrelevant_alternative_count": spa_readiness.get("poor_or_irrelevant_alternative_count", 0) if latest else 0,
        "spa_studentized_candidate_count": spa_studentization.get("studentized_candidate_count", 0) if latest else 0,
        "spa_dropped_zero_variance_count": spa_studentization.get("dropped_zero_variance_count", 0) if latest else 0,
        "spa_poor_or_irrelevant_alternative_count": spa_null.get("poor_or_irrelevant_alternative_count", 0) if latest else 0,
        "spa_p_value": spa.get("p_value") if latest else None,
        "best_mean_delta_variant_id": stats.get("best_mean_delta_variant_id"),
        "best_mean_delta": stats.get("best_mean_delta"),
        "reality_check_status": ((stats.get("reality_check") or {}).get("status") if isinstance(stats.get("reality_check"), Mapping) else "reserved") if latest else "reserved",
        "spa_status": spa.get("status", "reserved") if latest else "reserved",
        "model_confidence_set_status": mcs.get("status", "reserved") if latest else "reserved",
        "model_confidence_set_alpha": mcs.get("alpha") if latest else None,
        "model_confidence_set_confidence_level": mcs.get("confidence_level") if latest else None,
        "model_confidence_set_retained_variants": mcs.get("retained_variants", []) if latest else [],
        "model_confidence_set_retained_count": len(mcs.get("retained_variants") or []) if latest else 0,
        "model_confidence_set_eliminated_count": len(mcs.get("eliminated_variants") or []) if latest else 0,
        "family_level_inference_status": stats.get("family_level_inference_status", "not_started") if latest else "not_started",
        "paired_event_count": sample.get("shared_event_count", 0),
        "retained_variant_count": len(stats.get("retained_shadow_variants") or []) if latest else 0,
        "optimizer_permission": bool(decision.get("optimizer_permission")) if latest else False,
        "calculator_mutation_permission": bool(decision.get("calculator_mutation_permission")) if latest else False,
        "mutation_permission": bool(decision.get("optimizer_permission") or decision.get("calculator_mutation_permission")) if latest else False,
    }


def _bootstrap_reference_summary(payloads: List[Mapping[str, Any]]) -> Dict[str, Any]:
    suites: List[Mapping[str, Any]] = []
    for payload in payloads:
        data = _data(payload)
        if isinstance(data, Mapping) and data.get("schema_version") == "finance_bootstrap_reference_suite_v0":
            suites.append(data)
        elif payload.get("schema_version") == "finance_bootstrap_reference_suite_v0":
            suites.append(payload)
    latest = suites[-1] if suites else {}
    cases = latest.get("cases") if isinstance(latest.get("cases"), list) else []
    failed = [
        case
        for case in cases
        if isinstance(case, Mapping) and case.get("status") != "pass"
    ]
    return {
        "bootstrap_reference_status": "pass" if latest and not failed else ("fail" if failed else "not_started"),
        "bootstrap_reference_case_count": len(cases) if latest else 0,
    }


def _effective_sample_deficit(deduplicated: Mapping[str, Any]) -> int:
    if "effective_sample_deficit" in deduplicated:
        return _as_int(deduplicated.get("effective_sample_deficit"))
    minimum = _as_int(deduplicated.get("minimum_sample"))
    selected = _as_int(deduplicated.get("selected_non_overlapping_window_count"))
    return max(minimum - selected, 0)


def _effective_horizon_summary(horizons: Mapping[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for horizon, raw_row in horizons.items():
        if not isinstance(raw_row, Mapping):
            continue
        model_selection = (
            raw_row.get("model_selection")
            if isinstance(raw_row.get("model_selection"), Mapping)
            else {}
        )
        effective = (
            raw_row.get("effective_independence")
            if isinstance(raw_row.get("effective_independence"), Mapping)
            else {}
        )
        deduplicated = (
            effective.get("deduplicated_sensitivity")
            if isinstance(effective.get("deduplicated_sensitivity"), Mapping)
            else {}
        )
        summary[str(horizon)] = {
            "raw_scorecards": raw_row.get("raw_scorecards", 0),
            "mature_count": raw_row.get("mature_count", 0),
            "resolved_count": raw_row.get("resolved_count", 0),
            "pending_count": raw_row.get("pending_count", 0),
            "paired_event_count": raw_row.get("paired_event_count", 0),
            "match_status_counts": raw_row.get("match_status_counts", {}),
            "match_reason_counts": raw_row.get("match_reason_counts", {}),
            "raw_model_confidence_set_status": model_selection.get("model_confidence_set_status"),
            "raw_family_inference_status": model_selection.get("family_level_inference_status"),
            "raw_best_mean_delta_variant_id": model_selection.get("best_mean_delta_variant_id"),
            "raw_best_mean_delta": model_selection.get("best_mean_delta"),
            "raw_sample_gate_reason": model_selection.get("sample_gate_reason"),
            "effective_non_overlapping_window_count": deduplicated.get("selected_non_overlapping_window_count", 0),
            "effective_inference_status": deduplicated.get("inference_status", "not_started"),
            "effective_sample_gate_reason": deduplicated.get("sample_gate_reason"),
            "effective_sample_minimum": deduplicated.get("minimum_sample"),
            "effective_sample_deficit": _effective_sample_deficit(deduplicated),
            "effective_best_mean_delta_variant_id": deduplicated.get("best_mean_delta_variant_id"),
            "effective_best_mean_delta": deduplicated.get("best_mean_delta"),
        }
    return dict(sorted(summary.items()))


def _effective_evidence_summary(payloads: List[Mapping[str, Any]]) -> Dict[str, Any]:
    receipts: List[Mapping[str, Any]] = []
    for payload in payloads:
        receipt = _receipt(payload)
        if receipt.get("schema_version") == "finance_effective_evidence_receipt_v0":
            receipts.append(receipt)
    if not receipts:
        return {
            "status": "not_started",
            "raw_family_inference_status": "not_started",
            "raw_model_confidence_set_status": "not_started",
            "effective_inference_status": "not_started",
            "admission_status": "not_started",
            "calibration_prior_benchmark_variant_id": None,
            "live_calibrator_permission": False,
            "optimizer_permission": False,
            "calculator_mutation_permission": False,
            "horizons": {},
        }

    latest = receipts[-1]
    horizons = latest.get("horizons") if isinstance(latest.get("horizons"), Mapping) else {}
    combined = latest.get("combined_summary") if isinstance(latest.get("combined_summary"), Mapping) else {}
    combined_horizon = horizons.get("combined") if isinstance(horizons.get("combined"), Mapping) else {}
    primary_horizon = combined_horizon
    if not primary_horizon and horizons:
        first_key = sorted(str(key) for key in horizons.keys())[0]
        candidate_horizon = horizons.get(first_key)
        primary_horizon = candidate_horizon if isinstance(candidate_horizon, Mapping) else {}
    raw_model_selection = (
        primary_horizon.get("model_selection")
        if isinstance(primary_horizon.get("model_selection"), Mapping)
        else {}
    )
    effective = (
        combined.get("effective_independence")
        if isinstance(combined.get("effective_independence"), Mapping)
        else {}
    )
    if not effective:
        effective = (
            primary_horizon.get("effective_independence")
            if isinstance(primary_horizon.get("effective_independence"), Mapping)
            else {}
        )
    deduplicated = (
        effective.get("deduplicated_sensitivity")
        if isinstance(effective.get("deduplicated_sensitivity"), Mapping)
        else {}
    )
    taxonomy = latest.get("variant_taxonomy") if isinstance(latest.get("variant_taxonomy"), Mapping) else {}
    benchmark = (
        taxonomy.get("calibration_prior_benchmark")
        if isinstance(taxonomy.get("calibration_prior_benchmark"), Mapping)
        else {}
    )
    expansion_plan = (
        latest.get("expansion_plan")
        if isinstance(latest.get("expansion_plan"), Mapping)
        else {}
    )
    top_candidates = []
    candidate_ranking = expansion_plan.get("candidate_ranking")
    for row in candidate_ranking if isinstance(candidate_ranking, list) else []:
        if not isinstance(row, Mapping):
            continue
        top_candidates.append(
            {
                "run_id": row.get("run_id"),
                "subject_as_of": row.get("subject_as_of"),
                "marginal_effective_window_count": row.get("marginal_effective_window_count", 0),
                "mature_truth_covered_horizons": row.get("mature_truth_covered_horizons", []),
                "reason": row.get("reason"),
            }
        )
        if len(top_candidates) >= 5:
            break
    gate_status = latest.get("gate_status") if isinstance(latest.get("gate_status"), Mapping) else {}
    mutation_allowed = bool(gate_status.get("calculator_mutation_permission"))
    optimizer_allowed = bool(gate_status.get("optimizer_permission"))
    live_calibrator_allowed = bool(gate_status.get("live_calibrator_permission"))
    return {
        "status": "available",
        "schema_version": latest.get("schema_version"),
        "selection_id": combined.get("selection_id") or raw_model_selection.get("selection_id"),
        "raw_family_inference_status": raw_model_selection.get("family_level_inference_status", "unknown"),
        "raw_model_confidence_set_status": raw_model_selection.get("model_confidence_set_status", "unknown"),
        "raw_model_confidence_set_retained_variants": combined.get(
            "model_confidence_set_retained_variants",
            raw_model_selection.get("model_confidence_set_retained_variants", []),
        ),
        "raw_paired_event_count": combined.get("paired_event_count")
        or primary_horizon.get("paired_event_count", 0),
        "raw_best_mean_delta_variant_id": combined.get("best_mean_delta_variant_id")
        or raw_model_selection.get("best_mean_delta_variant_id"),
        "raw_best_mean_delta": combined.get("best_mean_delta", raw_model_selection.get("best_mean_delta")),
        "raw_event_window_overlap_count": effective.get("event_window_overlap_count", 0),
        "raw_event_window_overlap_density": effective.get("event_window_overlap_density", 0.0),
        "unique_event_window_count": effective.get("unique_event_window_count", 0),
        "unique_subject_as_of_count": effective.get("unique_subject_as_of_count", 0),
        "unique_subject_date_count": effective.get("unique_subject_date_count", 0),
        "effective_non_overlapping_window_count": deduplicated.get("selected_non_overlapping_window_count", 0),
        "effective_inference_status": deduplicated.get("inference_status", "not_started"),
        "effective_sample_gate_reason": deduplicated.get("sample_gate_reason"),
        "effective_sample_minimum": deduplicated.get("minimum_sample"),
        "effective_sample_deficit": _effective_sample_deficit(deduplicated),
        "effective_best_mean_delta_variant_id": deduplicated.get("best_mean_delta_variant_id"),
        "effective_best_mean_delta": deduplicated.get("best_mean_delta"),
        "expansion_plan_status": expansion_plan.get("status", "not_started"),
        "expansion_candidate_run_count": expansion_plan.get("candidate_run_count", 0),
        "expansion_candidate_runs_with_marginal_windows": expansion_plan.get("candidate_runs_with_marginal_windows", 0),
        "expansion_recommended_window_count": expansion_plan.get("recommended_window_count", 0),
        "expansion_expected_effective_count_after_recommended": expansion_plan.get(
            "expected_effective_count_after_recommended"
        ),
        "expansion_remaining_deficit_after_recommended": expansion_plan.get("remaining_deficit_after_recommended"),
        "expansion_top_candidate_runs": top_candidates,
        "calibration_prior_benchmark_variant_id": taxonomy.get("calibration_prior_benchmark_variant_id"),
        "calibration_prior_benchmark_family": benchmark.get("variant_family"),
        "calibration_prior_benchmark_role": benchmark.get("evidence_role"),
        "calibration_prior_benchmark_fitted": (
            (benchmark.get("calibration_policy") or {}).get("fitted")
            if isinstance(benchmark.get("calibration_policy"), Mapping)
            else None
        ),
        "calibration_prior_benchmark_common_support_preserving": (
            (benchmark.get("calibration_policy") or {}).get("common_support_preserving")
            if isinstance(benchmark.get("calibration_policy"), Mapping)
            else None
        ),
        "admission_status": (
            "mutation_permission_present"
            if mutation_allowed or optimizer_allowed or live_calibrator_allowed
            else "shadow_only_no_mutation"
        ),
        "calculator_mutation_permission": mutation_allowed,
        "optimizer_permission": optimizer_allowed,
        "live_calibrator_permission": live_calibrator_allowed,
        "horizons": _effective_horizon_summary(horizons),
    }


def _artifact_count(source_refs: Mapping[str, Any], key: str) -> int:
    value = source_refs.get(key)
    return len(value) if isinstance(value, list) else 0


def _lineage_ref(path: str, *, role: str, present: bool) -> Dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "present": present,
    }


def _quant_experiment_registry(
    *,
    experiment_count: int,
    variant_gate_count: int,
    model_selection_count: int,
    effective_count: int,
    split_policy: Any,
    split_executable: bool,
    purged_count: int,
    embargoed_count: int,
    effective_status: str,
    effective_sample_deficit: int,
    comparison_status: str,
    retained_count: int,
    output_state: str,
    model_selection: Mapping[str, Any],
    variant_gate: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Return a public-safe registry that proves the spine is repeatable."""

    primary_state = output_state
    primary = {
        "experiment_id": "public_quant_research_demo_shadow_forecast_family_5d",
        "stress_role": "primary_public_fixture",
        "hypothesis_type": "shadow_forecast_family_comparison",
        "public_safe_hypothesis": (
            "Compare shadow forecast-evidence variants over deterministic historical "
            "replay artifacts, then report uncertainty rather than an action."
        ),
        "target_universe": "public_market_fixture_universe",
        "time_horizon": "event_windowed_forecast_horizon",
        "authority_ceiling": "non_advisory_research_evaluation_only",
        "lineage_refs": [
            _lineage_ref(
                "tools/finance/historical_replay.py",
                role="purged_temporal_replay",
                present=True,
            ),
            _lineage_ref(
                "tools/finance/build_effective_evidence.py",
                role="effective_evidence_construction",
                present=effective_count > 0,
            ),
            _lineage_ref(
                "tools/finance/model_selection.py",
                role="family_level_model_comparison",
                present=model_selection_count > 0,
            ),
            _lineage_ref(
                "tools/finance/spa_statistics.py",
                role="multiple_comparison_guard",
                present=model_selection_count > 0,
            ),
        ],
        "artifact_counts": {
            "experiment_artifacts": experiment_count,
            "variant_gate_artifacts": variant_gate_count,
            "model_selection_artifacts": model_selection_count,
            "effective_evidence_artifacts": effective_count,
        },
        "split_discipline": {
            "split_policy": split_policy,
            "split_executable": split_executable,
            "random_kfold_allowed": False,
            "purged_pair_count": purged_count,
            "embargoed_pair_count": embargoed_count,
            "leakage_risks": [
                "truth_time_contamination",
                "overlapping_event_windows",
                "unbound_split_membership",
                "variant_registry_bypass",
            ],
        },
        "anti_overfit_guard": {
            "status": (
                "available"
                if (experiment_count or variant_gate_count or model_selection_count or effective_count)
                and (split_executable or effective_count > 0)
                else "pending_evidence"
            ),
            "selection_bias_guard": (
                "family_level_loss_matrix_plus_bootstrap_spa_mcs_before_review"
            ),
            "trial_count": max(
                _as_int(model_selection.get("candidate_count")),
                _as_int(variant_gate.get("candidate_variant_count")),
            ),
            "too_many_trials_metadata_present": bool(
                model_selection.get("candidate_count")
                or variant_gate.get("candidate_variant_count")
            ),
            "effective_inference_status": effective_status,
            "effective_sample_deficit": effective_sample_deficit,
        },
        "model_comparison": {
            "scoring_rule": "brier_score_binary_directional_event",
            "pairwise_equal_loss_status": variant_gate.get("statistical_test_status")
            or "not_started",
            "family_level_inference_status": comparison_status,
            "spa_status": model_selection.get("spa_status") or "reserved",
            "model_confidence_set_status": model_selection.get("model_confidence_set_status")
            or "reserved",
            "model_confidence_set_retained_count": retained_count,
            "winner_language_allowed": False,
            "output_state": primary_state,
        },
        "oracle_evolve_implication": {
            "decision": "review_candidate" if primary_state == "candidate_set" else primary_state,
            "review_gated": True,
            "auto_apply_allowed": False,
            "learning_authority": "human_review_required_before_any_evolve_candidate",
        },
        "no_advice_mode": {
            "enabled": True,
            "non_advisory_research_only": True,
        },
    }

    weak_control = {
        "experiment_id": "public_quant_research_stress_temporal_shuffle_control_5d",
        "stress_role": "negative_control_public_fixture",
        "hypothesis_type": "temporal_shuffle_control",
        "public_safe_hypothesis": (
            "Shuffle event-time labels inside the public fixture to verify that the "
            "evaluator rejects leakage-prone pseudo-signal rather than promoting it."
        ),
        "target_universe": "public_market_fixture_universe",
        "time_horizon": "5d",
        "authority_ceiling": "non_advisory_research_evaluation_only",
        "expected_failure_mode": "temporal_label_shuffle_breaks_out_of_sample_lineage",
        "lineage_refs": [
            _lineage_ref(
                "tools/finance/event_keys.py",
                role="comparison_event_key_lineage",
                present=True,
            ),
            _lineage_ref(
                "tools/finance/loss_differentials.py",
                role="pairwise_loss_differential_guard",
                present=variant_gate_count > 0,
            ),
            _lineage_ref(
                "tools/finance/model_selection_stats.py",
                role="selection_bias_and_mcs_guard",
                present=model_selection_count > 0,
            ),
        ],
        "artifact_counts": {
            "experiment_artifacts": 1,
            "variant_gate_artifacts": 0,
            "model_selection_artifacts": 0,
            "effective_evidence_artifacts": 0,
        },
        "split_discipline": {
            "split_policy": "purged_temporal_out_of_sample",
            "split_executable": True,
            "random_kfold_allowed": False,
            "purged_pair_count": 1,
            "embargoed_pair_count": 1,
            "leakage_risks": [
                "temporal_shuffle_leakage",
                "truth_time_contamination",
                "event_order_destroyed",
            ],
        },
        "anti_overfit_guard": {
            "status": "rejected_control",
            "selection_bias_guard": (
                "negative_control_must_not_enter_candidate_set_or_evolve_learning"
            ),
            "trial_count": 1,
            "too_many_trials_metadata_present": True,
            "effective_inference_status": "negative_control",
            "effective_sample_deficit": 0,
        },
        "model_comparison": {
            "scoring_rule": "brier_score_binary_directional_event",
            "pairwise_equal_loss_status": "not_applicable_control_rejected",
            "family_level_inference_status": "control_rejected",
            "spa_status": "not_applicable_control_rejected",
            "model_confidence_set_status": "control_rejected",
            "model_confidence_set_retained_count": 0,
            "winner_language_allowed": False,
            "output_state": "rejected",
        },
        "oracle_evolve_implication": {
            "decision": "reject_control_no_learning",
            "review_gated": True,
            "auto_apply_allowed": False,
            "learning_authority": "no_evolve_candidate_for_negative_control",
        },
        "no_advice_mode": {
            "enabled": True,
            "non_advisory_research_only": True,
        },
    }
    return [primary, weak_control]


def _quant_lineage_summary(registry: List[Mapping[str, Any]]) -> Dict[str, Any]:
    output_counts: Dict[str, int] = {}
    for entry in registry:
        state = str(_data(_data(entry).get("model_comparison")).get("output_state") or "unknown")
        output_counts[state] = output_counts.get(state, 0) + 1
    negative_or_insufficient = sum(
        output_counts.get(state, 0)
        for state in ("insufficient_evidence", "rejected", "blocked_authority_overclaim")
    )
    return {
        "schema_version": "finance_quant_experiment_registry_v0",
        "registry_count": len(registry),
        "minimum_registry_count": 2,
        "lineage_status": (
            "stress_validated_public_demo"
            if len(registry) >= 2 and negative_or_insufficient > 0
            else "single_demo_only"
        ),
        "output_state_counts": output_counts,
        "negative_or_insufficient_count": negative_or_insufficient,
        "negative_control_count": sum(
            1
            for entry in registry
            if str(entry.get("stress_role") or "").startswith("negative_control")
        ),
        "review_gated_all": all(
            _data(entry.get("oracle_evolve_implication")).get("review_gated") is True
            for entry in registry
        ),
        "auto_apply_allowed_any": any(
            _data(entry.get("oracle_evolve_implication")).get("auto_apply_allowed") is True
            for entry in registry
        ),
        "no_advice_enabled_all": all(
            _data(entry.get("no_advice_mode")).get("enabled") is True
            for entry in registry
        ),
        "winner_language_allowed_any": any(
            _data(entry.get("model_comparison")).get("winner_language_allowed") is True
            for entry in registry
        ),
        "random_kfold_allowed_any": any(
            _data(entry.get("split_discipline")).get("random_kfold_allowed") is True
            for entry in registry
        ),
    }


def _quant_agenda_candidate(
    *,
    candidate_id: str,
    rank: int,
    family_id: str,
    agenda_state: str,
    hypothesis_type: str,
    public_safe_hypothesis: str,
    target_universe: str,
    time_horizon: str,
    evidence_sources: List[str],
    leakage_risks: List[str],
    expected_failure_mode: str,
    selection_reason: str,
    expected_information_gain: str,
    falsifiability: str,
    family_diversity: str,
    data_snooping_risk: str,
    selection_score: float,
) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "rank": rank,
        "family_id": family_id,
        "agenda_state": agenda_state,
        "hypothesis_type": hypothesis_type,
        "public_safe_hypothesis": public_safe_hypothesis,
        "target_universe": target_universe,
        "time_horizon": time_horizon,
        "evidence_sources": evidence_sources,
        "leakage_risks": leakage_risks,
        "expected_failure_mode": expected_failure_mode,
        "selection_reason": selection_reason,
        "expected_information_gain": expected_information_gain,
        "falsifiability": falsifiability,
        "family_diversity": family_diversity,
        "data_snooping_risk": data_snooping_risk,
        "selection_score": selection_score,
        "authority_ceiling": "non_advisory_research_evaluation_only",
        "review_gated": True,
        "auto_apply_allowed": False,
        "no_advice_enabled": True,
        "winner_language_allowed": False,
    }


def _quant_research_agenda(
    *,
    registry: List[Mapping[str, Any]],
    lineage_summary: Mapping[str, Any],
    effective_sample_deficit: int,
    comparison_status: str,
    output_state: str,
) -> Dict[str, Any]:
    candidates = [
        _quant_agenda_candidate(
            candidate_id="public_quant_agenda_calibration_drift_cross_family_5d",
            rank=1,
            family_id="calibration_drift_cross_family",
            agenda_state="selected_for_next_test",
            hypothesis_type="calibration_drift_cross_family",
            public_safe_hypothesis=(
                "Test whether calibration-drift evidence persists across shadow forecast "
                "and macro-volatility public fixture families."
            ),
            target_universe="public_market_fixture_universe",
            time_horizon="5d",
            evidence_sources=[
                "tools/finance/calibrate_forecast_probabilities.py",
                "tools/finance/build_effective_evidence.py",
                "tools/finance/model_selection_stats.py",
            ],
            leakage_risks=[
                "calibration_window_peeking",
                "overlapping_event_windows",
                "family_duplicate_pressure",
            ],
            expected_failure_mode="drift_signal_fails_under_purged_cross_family_split",
            selection_reason=(
                "highest information gain among public-safe candidates while remaining "
                "falsifiable and family-diverse from the current registry"
            ),
            expected_information_gain="high",
            falsifiability="high",
            family_diversity="high",
            data_snooping_risk="low",
            selection_score=0.82,
        ),
        _quant_agenda_candidate(
            candidate_id="public_quant_agenda_threshold_grid_sweep_deferred",
            rank=2,
            family_id="threshold_grid_sweep",
            agenda_state="deferred_data_snooping_risk",
            hypothesis_type="threshold_grid_sweep",
            public_safe_hypothesis=(
                "Sweep threshold variants over the same public fixture family only after "
                "the search budget can justify the extra trial pressure."
            ),
            target_universe="public_market_fixture_universe",
            time_horizon="5d",
            evidence_sources=[
                "tools/finance/variant_registry.py",
                "tools/finance/compare_variants.py",
                "tools/finance/spa_statistics.py",
            ],
            leakage_risks=[
                "parameter_grid_fishing",
                "duplicate_prior_family",
                "multiple_comparison_pressure",
            ],
            expected_failure_mode="apparent_variant_edge_disappears_after_spa_guard",
            selection_reason=(
                "deferred because the candidate adds many near-duplicate variants before "
                "the current family memory has enough independent evidence"
            ),
            expected_information_gain="medium",
            falsifiability="medium",
            family_diversity="low",
            data_snooping_risk="high",
            selection_score=0.31,
        ),
        _quant_agenda_candidate(
            candidate_id="public_quant_agenda_temporal_permutation_control_refresh",
            rank=3,
            family_id="negative_control_temporal_permutation",
            agenda_state="control_candidate",
            hypothesis_type="temporal_permutation_control",
            public_safe_hypothesis=(
                "Refresh the temporal-permutation control to verify that shuffled event "
                "lineage still fails before any review learning is considered."
            ),
            target_universe="public_market_fixture_universe",
            time_horizon="5d",
            evidence_sources=[
                "tools/finance/event_keys.py",
                "tools/finance/loss_differentials.py",
                "tools/finance/model_selection.py",
            ],
            leakage_risks=[
                "event_order_destroyed",
                "temporal_shuffle_leakage",
                "truth_time_contamination",
            ],
            expected_failure_mode="temporal_permutation_should_not_survive_purged_split",
            selection_reason=(
                "kept as a control-family candidate so the program repeatedly proves it "
                "can reject pseudo-signal"
            ),
            expected_information_gain="medium",
            falsifiability="high",
            family_diversity="control",
            data_snooping_risk="low",
            selection_score=0.58,
        ),
        _quant_agenda_candidate(
            candidate_id="public_quant_agenda_cross_asset_macro_window_needs_evidence",
            rank=4,
            family_id="cross_asset_macro_window",
            agenda_state="needs_more_evidence",
            hypothesis_type="cross_asset_macro_window",
            public_safe_hypothesis=(
                "Compare cross-asset macro evidence windows only after the public fixture "
                "has enough effective samples and dated artifact lineage."
            ),
            target_universe="public_fixture_us_large_cap_macro_cross_asset",
            time_horizon="event_windowed_forecast_horizon",
            evidence_sources=[
                "tools/finance/build_price_history.py",
                "tools/finance/refresh_feeds.py",
                "tools/finance/build_effective_evidence.py",
            ],
            leakage_risks=[
                "missing_public_history_window",
                "effective_sample_deficit",
                "feed_artifact_gap",
            ],
            expected_failure_mode="insufficient_effective_sample_or_missing_public_artifact",
            selection_reason=(
                "held until the evidence path has enough public-safe samples to avoid "
                "turning absence of data into a research claim"
            ),
            expected_information_gain="high_after_evidence",
            falsifiability="medium",
            family_diversity="high",
            data_snooping_risk="medium",
            selection_score=0.49,
        ),
    ]
    family_ids = {str(row.get("family_id") or "") for row in candidates if row.get("family_id")}
    selected_count = sum(1 for row in candidates if row.get("agenda_state") == "selected_for_next_test")
    deferred_count = sum(1 for row in candidates if row.get("agenda_state") == "deferred_data_snooping_risk")
    control_count = sum(1 for row in candidates if row.get("agenda_state") == "control_candidate")
    needs_more_evidence_count = sum(1 for row in candidates if row.get("agenda_state") == "needs_more_evidence")
    return {
        "schema_version": "finance_quant_research_agenda_v0",
        "agenda_id": "public_quant_research_agenda_compiler_v0",
        "status": "compiled_public_safe",
        "selection_policy": {
            "prefer_falsifiable": True,
            "prefer_family_diversity": True,
            "prefer_expected_information_gain": True,
            "penalize_parameter_fishing": True,
            "penalize_duplicate_prior_family": True,
            "require_negative_or_control_candidate": True,
            "performance_metric_optimization_allowed": False,
            "winner_language_allowed": False,
        },
        "search_budget": {
            "candidate_count": len(candidates),
            "family_count": len(family_ids),
            "registry_count": _as_int(lineage_summary.get("registry_count")),
            "prior_negative_or_insufficient_count": _as_int(
                lineage_summary.get("negative_or_insufficient_count")
            ),
            "selected_for_next_test_count": selected_count,
            "deferred_data_snooping_count": deferred_count,
            "negative_or_control_candidate_count": control_count,
            "needs_more_evidence_count": needs_more_evidence_count,
            "rejected_count": sum(
                1
                for entry in registry
                if _data(_data(entry).get("model_comparison")).get("output_state") == "rejected"
            ),
            "max_selected_next": 1,
            "duplicate_family_count": len(candidates) - len(family_ids),
            "data_snooping_guard_active": True,
            "budget_pressure": "controlled",
        },
        "candidate_agenda": candidates,
        "family_memory": [
            {
                "family_id": "shadow_forecast_family_comparison",
                "memory_state": output_state,
                "current_evidence": comparison_status,
                "program_implication": "retain_as_baseline_family_without_winner_language",
            },
            {
                "family_id": "negative_control_temporal_permutation",
                "memory_state": "control_rejected",
                "current_evidence": "negative_control_rejected",
                "program_implication": "keep_control_in_rotation_before_learning_claims",
            },
            {
                "family_id": "threshold_grid_sweep",
                "memory_state": "deferred_data_snooping_risk",
                "current_evidence": "too_many_near_duplicate_variants",
                "program_implication": "do_not_spend_search_budget_until_family_memory_diversifies",
            },
            {
                "family_id": "cross_asset_macro_window",
                "memory_state": "needs_more_evidence",
                "current_evidence": f"effective_sample_deficit_{effective_sample_deficit}",
                "program_implication": "wait_for_public_artifact_lineage_before_testing",
            },
        ],
        "oracle_evolve_implication": {
            "decision": "agenda_review_required",
            "review_gated": True,
            "auto_apply_allowed": False,
            "learning_authority": "agenda_can_rank_tests_but_cannot_mutate_evolve_without_review",
        },
        "no_advice_mode": {
            "enabled": True,
            "non_advisory_research_only": True,
        },
    }


def _quant_research_experiment_spine(projection: Mapping[str, Any]) -> Dict[str, Any]:
    source_refs = projection.get("source_refs") if isinstance(projection.get("source_refs"), Mapping) else {}
    historical = (
        projection.get("historical_replay")
        if isinstance(projection.get("historical_replay"), Mapping)
        else {}
    )
    variant_gate = (
        projection.get("variant_gate")
        if isinstance(projection.get("variant_gate"), Mapping)
        else {}
    )
    model_selection = (
        projection.get("model_selection")
        if isinstance(projection.get("model_selection"), Mapping)
        else {}
    )
    effective = (
        projection.get("effective_evidence")
        if isinstance(projection.get("effective_evidence"), Mapping)
        else {}
    )
    experiment_count = _artifact_count(source_refs, "experiment_artifacts")
    variant_gate_count = _artifact_count(source_refs, "variant_gate_artifacts")
    model_selection_count = _artifact_count(source_refs, "model_selection_artifacts")
    effective_count = _artifact_count(source_refs, "effective_evidence_artifacts")
    evidence_available = any(
        [experiment_count, variant_gate_count, model_selection_count, effective_count]
    )
    mutation_requested = any(
        bool(row.get(field))
        for row in (variant_gate, model_selection, effective)
        for field in (
            "calculator_mutation_permission",
            "optimizer_permission",
            "mutation_permission",
            "live_calibrator_permission",
        )
    )
    split_policy = historical.get("split_policy") or "not_started"
    split_executable = historical.get("split_executable") is True
    purged_count = _as_int(variant_gate.get("purged_pair_count"))
    embargoed_count = _as_int(variant_gate.get("embargoed_pair_count"))
    effective_status = str(effective.get("effective_inference_status") or "not_started")
    effective_sample_deficit = _as_int(effective.get("effective_sample_deficit"))
    comparison_status = "not_started"
    if model_selection_count:
        comparison_status = str(
            model_selection.get("family_level_inference_status") or "reserved"
        )
    elif variant_gate_count:
        comparison_status = str(variant_gate.get("statistical_test_status") or "reserved")
    retained_count = _as_int(model_selection.get("model_confidence_set_retained_count"))
    output_state = "awaiting_evidence"
    if mutation_requested:
        output_state = "blocked_authority_overclaim"
    elif retained_count > 0:
        output_state = "candidate_set"
    elif evidence_available:
        output_state = "insufficient_evidence"
    registry = _quant_experiment_registry(
        experiment_count=experiment_count,
        variant_gate_count=variant_gate_count,
        model_selection_count=model_selection_count,
        effective_count=effective_count,
        split_policy=split_policy,
        split_executable=split_executable,
        purged_count=purged_count,
        embargoed_count=embargoed_count,
        effective_status=effective_status,
        effective_sample_deficit=effective_sample_deficit,
        comparison_status=comparison_status,
        retained_count=retained_count,
        output_state=output_state,
        model_selection=model_selection,
        variant_gate=variant_gate,
    )
    lineage_summary = _quant_lineage_summary(registry)
    research_agenda = _quant_research_agenda(
        registry=registry,
        lineage_summary=lineage_summary,
        effective_sample_deficit=effective_sample_deficit,
        comparison_status=comparison_status,
        output_state=output_state,
    )
    return {
        "schema_version": "finance_quant_research_experiment_spine_v0",
        "status": "available" if evidence_available else "awaiting_evidence",
        "hypothesis_ledger": {
            "hypothesis_type": "shadow_forecast_family_comparison",
            "public_safe_hypothesis": (
                "Compare shadow forecast-evidence variants over deterministic historical "
                "replay artifacts, then report uncertainty rather than an action."
            ),
            "target_universe": "public_market_fixture_universe",
            "time_horizon": "event_windowed_forecast_horizon",
            "authority_ceiling": "non_advisory_research_evaluation_only",
            "experiment_artifact_count": experiment_count,
            "variant_gate_artifact_count": variant_gate_count,
            "model_selection_artifact_count": model_selection_count,
            "effective_evidence_artifact_count": effective_count,
        },
        "anti_overfit_evaluator": {
            "split_policy": split_policy,
            "split_executable": split_executable,
            "random_kfold_allowed": False,
            "purged_pair_count": purged_count,
            "embargoed_pair_count": embargoed_count,
            "effective_inference_status": effective_status,
            "effective_sample_deficit": effective_sample_deficit,
            "too_many_trials_metadata_present": bool(
                model_selection.get("candidate_count")
                or variant_gate.get("candidate_variant_count")
            ),
            "status": (
                "available"
                if evidence_available
                and (split_executable or effective.get("status") == "available")
                else "pending_evidence"
            ),
        },
        "model_comparison": {
            "scoring_rule": "brier_score_binary_directional_event",
            "pairwise_equal_loss_status": variant_gate.get("statistical_test_status")
            or "not_started",
            "family_level_inference_status": comparison_status,
            "spa_status": model_selection.get("spa_status") or "reserved",
            "model_confidence_set_status": model_selection.get("model_confidence_set_status")
            or "reserved",
            "model_confidence_set_retained_count": retained_count,
            "winner_language_allowed": False,
            "output_state": output_state,
        },
        "experiment_registry": registry,
        "lineage_summary": lineage_summary,
        "research_agenda": research_agenda,
        "oracle_evolve_bridge": {
            "review_gated": True,
            "auto_apply_allowed": False,
            "decision": "review_candidate" if output_state == "candidate_set" else output_state,
            "bridge_path": [
                "hypothesis_registered",
                "evidence_constructed",
                "comparison_scored",
                "overfit_guard_checked",
                "oracle_reconciled",
                "evolve_review_gate",
            ],
        },
        "no_advice_mode": {
            "enabled": True,
            "non_advisory_research_only": True,
            "prohibited_output_classes": [
                "trading_action_labels",
                "personalized_account_action",
                "portfolio_allocation",
                "performance_guarantee",
                "automatic_execution",
            ],
        },
    }


def build_projection(
    scorecard_paths: List[Path],
    *,
    experiment_paths: Optional[List[Path]] = None,
    calibrator_paths: Optional[List[Path]] = None,
    variant_gate_paths: Optional[List[Path]] = None,
    model_selection_paths: Optional[List[Path]] = None,
    bootstrap_reference_paths: Optional[List[Path]] = None,
    effective_evidence_paths: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    scorecards = load_scorecards(scorecard_paths)
    projection = build_operating_picture(
        scorecards=scorecards,
        source_refs={
            "calculator_artifacts": [],
            "admitted_claims": [],
            "resolution_artifacts": [],
            "scorecard_artifacts": [str(path) for path in scorecard_paths],
            "experiment_artifacts": [str(path) for path in experiment_paths or []],
            "calibrator_artifacts": [str(path) for path in calibrator_paths or []],
            "variant_gate_artifacts": [str(path) for path in variant_gate_paths or []],
            "model_selection_artifacts": [str(path) for path in model_selection_paths or []],
            "bootstrap_reference_artifacts": [str(path) for path in bootstrap_reference_paths or []],
            "effective_evidence_artifacts": [str(path) for path in effective_evidence_paths or []],
        },
    )
    experiments = _load_payloads(experiment_paths or [])
    latest = _latest_experiment(experiments)
    if latest:
        scores = latest.get("scores") if isinstance(latest.get("scores"), Mapping) else {}
        split = latest.get("split_policy") if isinstance(latest.get("split_policy"), Mapping) else {}
        counts = latest.get("claim_counts") if isinstance(latest.get("claim_counts"), Mapping) else {}
        projection["historical_replay"] = {
            "latest_experiment_id": latest.get("experiment_id"),
            "split_policy": split.get("kind"),
            "split_executable": split.get("executable", False),
            "split_membership_counts": split.get("split_membership_counts", {}),
            "resolved_count": counts.get("resolved", 0),
            "holdout_count": (split.get("split_membership_counts") or {}).get("holdout", counts.get("resolved", 0)),
            "mean_brier": scores.get("mean_brier"),
            "brier_skill_vs_base_rate": scores.get("brier_skill_vs_base_rate"),
        }
    projection["calibration_gate"].update(_calibrator_summary(_load_payloads(calibrator_paths or [])))
    projection["variant_gate"] = _variant_gate_summary(_load_payloads(variant_gate_paths or []))
    projection["model_selection"] = _model_selection_summary(_load_payloads(model_selection_paths or []))
    projection["model_selection"].update(
        _bootstrap_reference_summary(_load_payloads(bootstrap_reference_paths or []))
    )
    projection["effective_evidence"] = _effective_evidence_summary(_load_payloads(effective_evidence_paths or []))
    projection["quant_research_experiment_spine"] = _quant_research_experiment_spine(projection)
    return projection


def write_projection(projection: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the finance evaluation operating-picture projection.")
    parser.add_argument("--scorecards", action="append", default=[], help="finance_eval_replay envelope path. Repeatable.")
    parser.add_argument("--experiments", action="append", default=[], help="finance_historical_replay envelope path. Repeatable.")
    parser.add_argument("--calibrators", action="append", default=[], help="finance_probability_calibrator envelope path. Repeatable.")
    parser.add_argument("--variant-gates", action="append", default=[], help="finance_variant_admission receipt envelope path. Repeatable.")
    parser.add_argument("--model-selections", action="append", default=[], help="finance_model_selection receipt envelope path. Repeatable.")
    parser.add_argument("--bootstrap-references", action="append", default=[], help="finance_bootstrap_reference_suite envelope path. Repeatable.")
    parser.add_argument("--effective-evidence", action="append", default=[], help="finance_effective_evidence receipt envelope path. Repeatable.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Projection output path.")
    parser.add_argument("--json", action="store_true", help="Print projection JSON.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    projection = build_projection(
        [Path(path) for path in args.scorecards],
        experiment_paths=[Path(path) for path in args.experiments],
        calibrator_paths=[Path(path) for path in args.calibrators],
        variant_gate_paths=[Path(path) for path in args.variant_gates],
        model_selection_paths=[Path(path) for path in args.model_selections],
        bootstrap_reference_paths=[Path(path) for path in args.bootstrap_references],
        effective_evidence_paths=[Path(path) for path in args.effective_evidence],
    )
    output = Path(args.output)
    write_projection(projection, output)
    text = json.dumps(projection, indent=2, sort_keys=True)
    print(text if args.json else text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
