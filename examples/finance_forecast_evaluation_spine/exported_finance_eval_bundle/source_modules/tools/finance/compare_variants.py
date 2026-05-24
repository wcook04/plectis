#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Compare finance forecast generator variants against the registered
  baseline with paired loss receipts before any optimizer or calculator mutation
  can be considered.
- Mechanism: Read two historical-replay ledgers, pair resolved scorecards by
  stable event-contract keys, compute paired loss deltas, and emit a
  `finance_variant_admission_receipt_v0` envelope.
- Hardening: Refuses row-order comparison, unknown variant ids, non-executable
  split policies, and candidate-smoke-test scorecards.

[INTERFACE]
- Reads: baseline and candidate finance_historical_replay envelopes.
- Returns/prints: `finance_variant_admission.1` ArtifactEnvelope.

[CONSTRAINTS]
- Shadow comparison only; no optimizer/GEPA or calculator mutation permission.
- Statistical test fields are reserved, but v4 only admits deterministic paired
  loss receipts unless sample size is sufficient for later statistical tests.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from system.lib import feed_envelope
from tools.finance.event_keys import (
    COMPARISON_EVENT_KEY_AUTHORITY,
    COMPARISON_EVENT_KEY_SCHEMA,
    comparison_event_key_payload,
    members_signature,
    parts_from_event_contract,
)
from tools.finance.loss_differentials import (
    LOSS_DIFFERENTIAL_AUTHORITY,
    build_loss_differential_series,
    paired_loss_summary,
)
from tools.finance import variant_registry

TOOL_NAME = "finance_compare_variants"
DATA_SCHEMA_VERSION = "finance_variant_admission.1"
RECEIPT_SCHEMA_VERSION = "finance_variant_admission_receipt_v0"
DEFAULT_LOSS = "brier_score_binary_directional_event"
SUPPORTED_TESTS = {"deterministic_delta", "diebold_mariano"}
SUPPORTED_MULTIPLE_TESTING = {"none", "reality_check_placeholder", "spa_placeholder"}
PAIRING_CONTRACT_FIELDS = (
    "subject_as_of",
    "lane",
    "group",
    "members_signature",
    "event_start",
    "event_end",
    "horizon",
    "benchmark",
    "event_type",
    "outcome_basis",
    "benchmark_member_policy",
)


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _failure_envelope(error: str, *, run_dir: Optional[Path] = None) -> Dict[str, Any]:
    now = feed_envelope.utc_now()
    diagnostics = feed_envelope.new_diagnostics()
    feed_envelope.append_warning(diagnostics, error)
    metadata = feed_envelope.build_metadata(
        tool=TOOL_NAME,
        status="failure",
        now=now,
        run_id=feed_envelope.resolve_run_id(None, run_dir, default=TOOL_NAME),
        as_of=now.iso,
        items_count=0,
        diagnostics=diagnostics,
        data_schema_version=DATA_SCHEMA_VERSION,
        timestamp=now.iso,
        error=error,
    )
    return {"metadata": metadata, "data": {}}


def _data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else payload


def _ledger(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    ledger = _data(payload).get("experiment_ledger")
    return ledger if isinstance(ledger, Mapping) else {}


def _scorecards(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    raw = _data(payload).get("scorecards")
    return [dict(item) for item in raw] if isinstance(raw, list) else []


def _event_contract(card: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = card.get("event_contract")
    return contract if isinstance(contract, Mapping) else {}


def _semantic_parts(card: Mapping[str, Any]) -> Dict[str, str]:
    parts = parts_from_event_contract(card)
    return {
        "subject_as_of": parts.subject_as_of,
        "lane": parts.lane,
        "group": parts.group,
        "members_signature": members_signature(parts.members),
        "event_start": parts.event_start,
        "event_end": parts.event_end,
        "horizon": parts.horizon,
        "benchmark": parts.benchmark,
        "event_type": parts.event_type,
        "outcome_basis": parts.outcome_basis,
        "benchmark_member_policy": parts.benchmark_member_policy,
    }


def _pair_key(card: Mapping[str, Any]) -> str:
    key = _as_text(card.get("comparison_event_key") or _event_contract(card).get("comparison_event_key"))
    if key:
        return key
    parts = _semantic_parts(card)
    if not all(parts.get(field) for field in PAIRING_CONTRACT_FIELDS):
        return ""
    return comparison_event_key_payload(parts_from_event_contract(card))["comparison_event_key"]


def _pair_audit(card: Mapping[str, Any]) -> Dict[str, str]:
    audit = card.get("pair_audit") if isinstance(card.get("pair_audit"), Mapping) else {}
    contract = _event_contract(card)
    return {
        "forecast_id": _as_text(audit.get("forecast_id") or card.get("forecast_id")),
        "candidate_ref": _as_text(audit.get("candidate_ref") or card.get("candidate_ref")),
        "truth_join_key": _as_text(audit.get("truth_join_key") or contract.get("truth_join_key")),
        "generator_variant_id": _as_text(audit.get("generator_variant_id") or card.get("generator_variant_id")),
        "calibrator_id": _as_text(audit.get("calibrator_id") or card.get("calibrator_id")),
    }


def _loss(card: Mapping[str, Any], loss_metric: str) -> Optional[float]:
    if loss_metric != DEFAULT_LOSS:
        raise ValueError(f"unsupported loss metric: {loss_metric}")
    proper = card.get("proper_score") if isinstance(card.get("proper_score"), Mapping) else {}
    value = proper.get("brier_score")
    return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None


def _resolved_index(cards: Sequence[Mapping[str, Any]], loss_metric: str) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {}
    excluded: Counter[str] = Counter()
    for card in cards:
        if card.get("status") != "resolved":
            continue
        if card.get("mode") == "candidate_smoke_test":
            excluded["candidate_smoke_test"] += 1
            continue
        loss_value = _loss(card, loss_metric)
        if loss_value is None:
            excluded["missing_loss"] += 1
            continue
        key = _pair_key(card)
        if not key:
            excluded["missing_comparison_event_key"] += 1
            continue
        out[key] = {"card": dict(card), "loss": loss_value}
    return {"index": out, "excluded": dict(sorted(excluded.items()))}


def _stable_digest(*parts: Any, length: int = 16) -> str:
    text = "|".join(_as_text(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _variant_id(payload: Mapping[str, Any]) -> str:
    ledger = _ledger(payload)
    return _as_text(ledger.get("generator_variant_id"))


def _split_executable(payload: Mapping[str, Any]) -> bool:
    split = _ledger(payload).get("split_policy")
    return bool(isinstance(split, Mapping) and split.get("executable") is True)


def _mismatch_reason(card: Mapping[str, Any], comparison_cards: Sequence[Mapping[str, Any]]) -> str:
    candidate_parts = _semantic_parts(card)
    best_diffs: Optional[List[str]] = None
    for other in comparison_cards:
        other_parts = _semantic_parts(other)
        diffs = [
            field
            for field in PAIRING_CONTRACT_FIELDS
            if _as_text(candidate_parts.get(field)) != _as_text(other_parts.get(field))
        ]
        if best_diffs is None or len(diffs) < len(best_diffs):
            best_diffs = diffs
    if not best_diffs:
        return "no_matching_event_contract"
    if len(best_diffs) == 1:
        return f"{best_diffs[0]}_mismatch"
    return "multiple_event_contract_mismatch"


def _identity_decoupled(baseline_card: Mapping[str, Any], candidate_card: Mapping[str, Any]) -> bool:
    baseline_audit = _pair_audit(baseline_card)
    candidate_audit = _pair_audit(candidate_card)
    return any(
        baseline_audit.get(field) != candidate_audit.get(field)
        for field in ("forecast_id", "candidate_ref", "truth_join_key")
    )


def _split_label(card: Mapping[str, Any]) -> str:
    contract = _event_contract(card)
    for source in (card, contract):
        membership = source.get("split_membership")
        if isinstance(membership, Mapping):
            split = _as_text(membership.get("split"))
            if split:
                return split
    for source in (card, contract):
        split = _as_text(source.get("split") or source.get("split_membership"))
        if split:
            return split
    return ""


def _split_membership_payload(card: Mapping[str, Any]) -> Dict[str, Any]:
    contract = _event_contract(card)
    for source in (card, contract):
        membership = source.get("split_membership")
        if isinstance(membership, Mapping):
            split = _as_text(membership.get("split"))
            usable_value = membership.get("usable_for_variant_comparison")
            calibration_value = membership.get("usable_for_calibration")
            usable = bool(usable_value) if isinstance(usable_value, bool) else split not in {"purged", "embargoed"}
            usable_for_calibration = (
                bool(calibration_value) if isinstance(calibration_value, bool) else split not in {"purged", "embargoed"}
            )
            return {
                "split": split,
                "split_policy": _as_text(membership.get("split_policy")),
                "reason": _as_text(membership.get("reason")),
                "usable_for_variant_comparison": usable,
                "usable_for_calibration": usable_for_calibration,
                "comparison_event_key": _as_text(membership.get("comparison_event_key")),
                "bound": bool(split),
            }
    split = _split_label(card)
    return {
        "split": split,
        "split_policy": "",
        "reason": "missing_split_membership_binding",
        "usable_for_variant_comparison": split not in {"purged", "embargoed"} if split else True,
        "usable_for_calibration": split not in {"purged", "embargoed"} if split else True,
        "comparison_event_key": _pair_key(card),
        "bound": False,
    }


def _combined_split_membership(
    baseline_card: Mapping[str, Any],
    candidate_card: Mapping[str, Any],
) -> Dict[str, Any]:
    baseline = _split_membership_payload(baseline_card)
    candidate = _split_membership_payload(candidate_card)
    baseline_split = _as_text(baseline.get("split"))
    candidate_split = _as_text(candidate.get("split"))
    if baseline_split and candidate_split and baseline_split != candidate_split:
        split = f"{baseline_split}|{candidate_split}"
    else:
        split = baseline_split or candidate_split
    usable = bool(baseline.get("usable_for_variant_comparison")) and bool(candidate.get("usable_for_variant_comparison"))
    return {
        "split": split,
        "split_policy": _as_text(candidate.get("split_policy") or baseline.get("split_policy")),
        "reason": _as_text(candidate.get("reason") or baseline.get("reason")),
        "usable_for_variant_comparison": usable,
        "usable_for_calibration": bool(baseline.get("usable_for_calibration")) and bool(candidate.get("usable_for_calibration")),
        "bound": bool(baseline.get("bound")) and bool(candidate.get("bound")),
        "baseline": baseline,
        "candidate": candidate,
    }


def _pair_context(card: Mapping[str, Any]) -> Dict[str, Any]:
    parts = _semantic_parts(card)
    return {
        "subject_as_of": parts["subject_as_of"],
        "event_start": parts["event_start"],
        "event_end": parts["event_end"],
        "horizon": parts["horizon"],
        "split": _split_label(card),
    }


def compare(
    baseline_payload: Mapping[str, Any],
    candidate_payload: Mapping[str, Any],
    *,
    loss_metric: str = DEFAULT_LOSS,
    test: str = "diebold_mariano",
    multiple_testing: str = "none",
    min_paired: int = 30,
) -> Dict[str, Any]:
    if test not in SUPPORTED_TESTS:
        raise ValueError(f"unsupported comparison test: {test}")
    if multiple_testing not in SUPPORTED_MULTIPLE_TESTING:
        raise ValueError(f"unsupported multiple_testing: {multiple_testing}")

    baseline_variant_id = _variant_id(baseline_payload) or variant_registry.BASELINE_VARIANT_ID
    candidate_variant_id = _variant_id(candidate_payload)
    variant_registry.assert_variant_known(baseline_variant_id)
    variant_registry.assert_variant_known(candidate_variant_id)

    if not _split_executable(baseline_payload) or not _split_executable(candidate_payload):
        non_executable = True
    else:
        non_executable = False

    baseline_cards = _scorecards(baseline_payload)
    candidate_cards = _scorecards(candidate_payload)
    baseline_resolution = _resolved_index(baseline_cards, loss_metric)
    candidate_resolution = _resolved_index(candidate_cards, loss_metric)
    baseline_index = baseline_resolution["index"]
    candidate_index = candidate_resolution["index"]
    paired_keys = sorted(set(baseline_index).intersection(candidate_index))
    pairs = []
    for key in paired_keys:
        baseline_card = baseline_index[key]["card"]
        candidate_card = candidate_index[key]["card"]
        context = _pair_context(baseline_card)
        split_membership = _combined_split_membership(baseline_card, candidate_card)
        context["split"] = split_membership["split"]
        pairs.append(
            {
                "comparison_event_key": key,
                "event_key": key,
                **context,
                "split_membership": split_membership,
                "baseline_loss": round(float(baseline_index[key]["loss"]), 10),
                "candidate_loss": round(float(candidate_index[key]["loss"]), 10),
                "loss_delta_candidate_minus_baseline": round(
                    float(candidate_index[key]["loss"] - baseline_index[key]["loss"]),
                    10,
                ),
                "pair_audit": {
                    "baseline": _pair_audit(baseline_card),
                    "candidate": _pair_audit(candidate_card),
                },
            }
        )
    identity_decoupled_pair_count = sum(
        1
        for key in paired_keys
        if _identity_decoupled(baseline_index[key]["card"], candidate_index[key]["card"])
    )
    unpaired_baseline_keys = sorted(set(baseline_index).difference(candidate_index))
    unpaired_candidate_keys = sorted(set(candidate_index).difference(baseline_index))
    mismatch_counter: Counter[str] = Counter()
    for key in unpaired_candidate_keys:
        mismatch_counter[_mismatch_reason(candidate_index[key]["card"], [row["card"] for row in baseline_index.values()])] += 1
    if unpaired_baseline_keys and not unpaired_candidate_keys:
        mismatch_counter["candidate_missing_event_contract"] += len(unpaired_baseline_keys)
    loss_series = build_loss_differential_series(
        pairs,
        baseline_variant_id=baseline_variant_id,
        candidate_variant_id=candidate_variant_id,
        loss_metric=loss_metric,
        comparison_key_schema=COMPARISON_EVENT_KEY_SCHEMA,
    )
    loss_summary = paired_loss_summary(loss_series, test=test, min_paired=min_paired)
    mean_delta = loss_summary["mean_loss_delta"]

    gate_id = "fin_var_gate_" + _stable_digest(
        baseline_variant_id,
        candidate_variant_id,
        _ledger(baseline_payload).get("experiment_id"),
        _ledger(candidate_payload).get("experiment_id"),
        loss_summary["paired_sample_size"],
        mean_delta,
    )

    if non_executable:
        status = "shadow_only"
        reason = "non_executable_split_policy"
    elif int(loss_summary["dependence_diagnostics"].get("missing_split_membership_count") or 0) > 0:
        status = "shadow_only"
        reason = "split_membership_unbound"
    elif int(loss_summary["paired_sample_size"]) < min_paired:
        status = "shadow_only"
        reason = "insufficient_paired_sample"
    elif mean_delta is not None and mean_delta < 0:
        status = "admitted_shadow_variant"
        reason = "paired_loss_improved_shadow_only"
    else:
        status = "rejected"
        reason = "candidate_not_better_than_baseline"

    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "variant_gate_id": gate_id,
        "baseline_variant_id": baseline_variant_id,
        "candidate_variant_id": candidate_variant_id,
        "experiment_refs": [
            _as_text(_ledger(baseline_payload).get("experiment_id")),
            _as_text(_ledger(candidate_payload).get("experiment_id")),
        ],
        "comparison_unit": "paired_forecast_loss",
        "loss_metric": loss_metric,
        "split_policy": {
            "kind": _as_text((_ledger(candidate_payload).get("split_policy") or {}).get("kind")),
            "embargo_days": (_ledger(candidate_payload).get("split_policy") or {}).get("embargo_days"),
            "executable": not non_executable,
            "baseline_executable": _split_executable(baseline_payload),
            "candidate_executable": _split_executable(candidate_payload),
        },
        "pairing": {
            "key_schema": COMPARISON_EVENT_KEY_SCHEMA,
            "key_authority": COMPARISON_EVENT_KEY_AUTHORITY,
            "paired_by": "comparison_event_key",
            "identity_decoupled_pair_count": identity_decoupled_pair_count,
            "unpaired_baseline_count": len(unpaired_baseline_keys),
            "unpaired_candidate_count": len(unpaired_candidate_keys),
            "excluded_from_variant_comparison": {
                "baseline": baseline_resolution["excluded"],
                "candidate": candidate_resolution["excluded"],
                "total": sum(baseline_resolution["excluded"].values()) + sum(candidate_resolution["excluded"].values()),
            },
            "mismatch_reasons": dict(sorted(mismatch_counter.items())),
        },
        "sample": {
            "paired_claim_count": loss_summary["paired_sample_size"],
            "baseline_resolved_count": len(baseline_index),
            "candidate_resolved_count": len(candidate_index),
            "excluded_unpaired_count": len(unpaired_baseline_keys) + len(unpaired_candidate_keys),
            "excluded_split_count": loss_summary["dependence_diagnostics"].get("excluded_split_count", 0),
            "missing_split_membership_count": loss_summary["dependence_diagnostics"].get(
                "missing_split_membership_count",
                0,
            ),
        },
        "statistics": {
            "loss_differential_authority": LOSS_DIFFERENTIAL_AUTHORITY,
            "mean_loss_baseline": loss_summary["mean_loss_baseline"],
            "mean_loss_candidate": loss_summary["mean_loss_candidate"],
            "mean_loss_delta": mean_delta,
            "loss_delta_std": loss_summary["loss_delta_std"],
            "loss_delta_std_error": loss_summary["loss_delta_std_error"],
            "paired_sample_size": loss_summary["paired_sample_size"],
            "paired_losses": pairs,
            "loss_differential_series": loss_summary["loss_differential_series"],
            "dependence_diagnostics": loss_summary["dependence_diagnostics"],
            "variance_estimator": loss_summary["variance_estimator"],
            "selected_lag": loss_summary["selected_lag"],
            "event_window_overlap_count": loss_summary["event_window_overlap_count"],
            "diebold_mariano": loss_summary["diebold_mariano"],
            "hln_small_sample_correction": loss_summary["hln_small_sample_correction"],
            "multiple_testing_adjustment": {
                "method": multiple_testing,
                "status": "not_applied_single_candidate" if multiple_testing == "none" else "reserved_placeholder",
                "data_snooping_guard": "variant_admission_gate_required_before_optimizer_permission",
            },
        },
        "decision": {
            "status": status,
            "optimizer_permission": False,
            "calculator_mutation_permission": False,
            "reason": reason,
        },
    }


def run(config: Dict[str, Any], run_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        baseline_text = _as_text(config.get("baseline_experiment"))
        candidate_text = _as_text(config.get("candidate_experiment"))
        if not baseline_text:
            raise ValueError("baseline_experiment is required")
        if not candidate_text:
            raise ValueError("candidate_experiment is required")
        baseline_path = Path(baseline_text)
        candidate_path = Path(candidate_text)
        receipt = compare(
            _read_json(baseline_path),
            _read_json(candidate_path),
            loss_metric=_as_text(config.get("loss") or DEFAULT_LOSS),
            test=_as_text(config.get("test") or "diebold_mariano"),
            multiple_testing=_as_text(config.get("multiple_testing") or "none"),
            min_paired=int(config.get("min_paired") or 30),
        )
        now = feed_envelope.utc_now()
        runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), Mapping) else {}
        run_id = _as_text(runtime.get("run_id") or receipt["variant_gate_id"])
        diagnostics = feed_envelope.new_diagnostics(
            input_rows=2,
            output_rows=1,
            dropped_rows=0,
            paired_claim_count=receipt["sample"]["paired_claim_count"],
            decision=receipt["decision"],
        )
        metadata = feed_envelope.build_metadata(
            tool=TOOL_NAME,
            status="success",
            now=now,
            run_id=run_id,
            as_of=_as_text(runtime.get("as_of") or now.iso),
            items_count=1,
            diagnostics=diagnostics,
            data_schema_version=DATA_SCHEMA_VERSION,
            timestamp=now.iso,
        )
        return {"metadata": metadata, "data": {"receipt": receipt}}
    except Exception as exc:
        return _failure_envelope(str(exc), run_dir=run_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare finance forecast generator variants with paired loss receipts.")
    parser.add_argument("--baseline-experiment", required=True, help="Baseline finance_historical_replay envelope.")
    parser.add_argument("--candidate-experiment", required=True, help="Candidate finance_historical_replay envelope.")
    parser.add_argument("--loss", default=DEFAULT_LOSS)
    parser.add_argument("--test", default="diebold_mariano", choices=sorted(SUPPORTED_TESTS))
    parser.add_argument("--multiple-testing", default="none", choices=sorted(SUPPORTED_MULTIPLE_TESTING))
    parser.add_argument("--min-paired", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Print JSON envelope.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(
        {
            "baseline_experiment": args.baseline_experiment,
            "candidate_experiment": args.candidate_experiment,
            "loss": args.loss,
            "test": args.test,
            "multiple_testing": args.multiple_testing,
            "min_paired": args.min_paired,
            "runtime": {"run_id": TOOL_NAME},
        }
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text if args.json else text)
    return 0 if payload.get("metadata", {}).get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
