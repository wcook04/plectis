#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Replay finance forecast claims against delayed truth rows without
  letting inert calculator candidates masquerade as CP1 commitments.
- Mechanism: Load calculator candidate cards or CP1-admitted finance claims,
  enforce event/horizon/benchmark truth bindings, compute Brier scorecards plus
  calibration rollups, and return a canonical ArtifactEnvelope.

[INTERFACE]
- Reads: calculator artifact, admitted forecast-claim envelope, or raw cards.
- Reads: optional `prediction_reconciliation` artifact carrying realized truth.
- Returns/prints: `finance_eval_replay.2` envelope with scorecards, aggregate
  calibration, generator summaries, and an operating-picture payload.

[CONSTRAINTS]
- Default mode is CP1-admitted only. Candidate cards can be scored only through
  explicit `candidate_smoke_test` mode.
- No trading advice: this scores forecast/evaluation artifacts only.
- No optimizer mutation: replay receipts do not permit calculator weight changes.
- Missing or mismatched truth remains explicit status, never silently scored.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from system.lib import feed_envelope
from tools.finance.event_keys import (
    COMPARISON_EVENT_KEY_AUTHORITY,
    COMPARISON_EVENT_KEY_SCHEMA,
    comparison_event_key_payload,
    members_signature,
    normalize_key_parts,
)

TOOL_NAME = "finance_eval_replay"
DATA_SCHEMA_VERSION = "finance_eval_replay.3"

MODE_CP1_ADMITTED_ONLY = "cp1_admitted_only"
MODE_CANDIDATE_SMOKE_TEST = "candidate_smoke_test"
SUPPORTED_MODES = {MODE_CP1_ADMITTED_ONLY, MODE_CANDIDATE_SMOKE_TEST}
SUPPORTED_SCORE_BUNDLES = {"proper", "proper+calibration+data_quality"}

STATUS_RESOLVED = "resolved"
STATUS_PENDING_TRUTH = "pending_truth"
STATUS_ABSTAINED = "abstained"
STATUS_MISSING_EVENT_BINDING = "not_admissible_missing_event_binding"
STATUS_HORIZON_MISMATCH = "not_admissible_horizon_mismatch"
STATUS_TRUTH_WINDOW_MISMATCH = "not_admissible_truth_window_mismatch"
STATUS_BENCHMARK_MISMATCH = "not_admissible_benchmark_mismatch"
STATUS_LOW_QUALITY_TRUTH = "excluded_stale_or_low_quality_truth"
STATUS_INSUFFICIENT_MEMBER_COVERAGE = "not_admissible_insufficient_member_coverage"
STATUS_MISSING_BENCHMARK_TRUTH = "not_admissible_missing_benchmark_truth"
STATUS_MATURED_TRUTH_MISSING = "matured_truth_missing"
STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION = "not_admissible_benchmark_member_policy_violation"

OUTCOME_BASIS_GROUP_RETURN = "equal_weight_group_return_direction"
OUTCOME_BASIS_MEAN_MEMBER_HIT = "mean_member_binary_hit"
BENCHMARK_MEMBER_POLICY_REJECT = "reject_if_benchmark_is_member"
BENCHMARK_MEMBER_POLICY_INCLUDE_ZERO = "include_as_zero_excess"
BENCHMARK_MEMBER_POLICY_EXCLUDE = "exclude_from_claim_outcome"
SUPPORTED_BENCHMARK_MEMBER_POLICIES = {
    BENCHMARK_MEMBER_POLICY_REJECT,
    BENCHMARK_MEMBER_POLICY_INCLUDE_ZERO,
    BENCHMARK_MEMBER_POLICY_EXCLUDE,
}
DEFAULT_MINIMUM_COVERAGE = 1.0


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else payload


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _as_text(value).upper()


def _round_optional(value: Optional[float], digits: int = 6) -> Optional[float]:
    return round(float(value), digits) if isinstance(value, (int, float)) else None


def _parse_dt(value: Any) -> Optional[datetime]:
    text = _as_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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


def load_forecast_cards(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    data = _data(payload)
    raw = data.get("candidate_forecast_cards") or payload.get("candidate_forecast_cards")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(payload.get("forecast_cards"), list):
        return [item for item in payload["forecast_cards"] if isinstance(item, dict)]
    if payload.get("schema_version") == "forecast_claim_card_v0":
        return [dict(payload)]
    return []


def load_admitted_claims(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    data = _data(payload)
    raw = data.get("admitted_claims") or data.get("forecast_claims") or payload.get("admitted_claims")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if payload.get("schema_version") == "finance_forecast_claim_v1":
        return [dict(payload)]
    return []


def load_forecast_items(payload: Mapping[str, Any], *, mode: str) -> List[Dict[str, Any]]:
    admitted = load_admitted_claims(payload)
    candidates = load_forecast_cards(payload)
    if mode == MODE_CANDIDATE_SMOKE_TEST:
        return admitted + candidates
    return admitted if admitted else candidates


def _claim_status(item: Mapping[str, Any]) -> str:
    return _as_text(item.get("claim_status"))


def _is_admitted_claim(item: Mapping[str, Any]) -> bool:
    return item.get("schema_version") == "finance_forecast_claim_v1" or _claim_status(item) == "cp1_admitted"


def _forecast_id(item: Mapping[str, Any]) -> str:
    return _as_text(
        item.get("forecast_id")
        or _nested(item, "identity", "forecast_id")
        or item.get("candidate_ref")
        or "unknown_forecast"
    )


def _generator_variant_id(item: Mapping[str, Any]) -> str:
    return _as_text(
        item.get("generator_variant_id")
        or _nested(item, "identity", "generator_variant_id")
        or "unknown_generator"
    )


def _subject_as_of(item: Mapping[str, Any]) -> str:
    return _as_text(_nested(item, "subject", "as_of") or _nested(item, "identity", "as_of"))


def _members(item: Mapping[str, Any]) -> List[str]:
    raw = _nested(item, "subject", "members") if _is_admitted_claim(item) else _nested(item, "target", "members")
    if not isinstance(raw, list):
        return []
    return sorted({_upper(member) for member in raw if _upper(member)})


def _direction(item: Mapping[str, Any]) -> str:
    if _is_admitted_claim(item):
        return _upper(_nested(item, "event", "direction"))
    return _upper(_nested(item, "target", "direction"))


def _probability(item: Mapping[str, Any]) -> float:
    probability = _float(_nested(item, "belief", "directional_hit_probability"))
    if probability is None:
        probability = _float(_nested(item, "belief", "event_probability"), 0.5)
    assert probability is not None
    return max(0.0, min(1.0, probability))


def _normalize_outcome_basis(value: str, *, aggregation: str = "", admitted: bool = False) -> str:
    text = _as_text(value)
    if text in {OUTCOME_BASIS_GROUP_RETURN, OUTCOME_BASIS_MEAN_MEMBER_HIT}:
        return text
    if admitted and _as_text(aggregation) == "equal_weight_member_return":
        return OUTCOME_BASIS_GROUP_RETURN
    return OUTCOME_BASIS_MEAN_MEMBER_HIT


def _normalize_benchmark_member_policy(value: Any) -> str:
    text = _as_text(value)
    if text in SUPPORTED_BENCHMARK_MEMBER_POLICIES:
        return text
    return BENCHMARK_MEMBER_POLICY_REJECT


def _event_contract(item: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_admitted_claim(item):
        event = item.get("event") if isinstance(item.get("event"), Mapping) else {}
        subject = item.get("subject") if isinstance(item.get("subject"), Mapping) else {}
        truth_binding = item.get("truth_binding") if isinstance(item.get("truth_binding"), Mapping) else {}
        subject_as_of = _subject_as_of(item)
        lane = _as_text(subject.get("lane"))
        group = _as_text(subject.get("group"))
        member_signature = members_signature(_members(item))
        outcome_basis = _normalize_outcome_basis(
            _as_text(event.get("outcome_basis")),
            aggregation=_as_text(event.get("aggregation")),
            admitted=True,
        )
        benchmark_member_policy = _normalize_benchmark_member_policy(event.get("benchmark_member_policy"))
        comparison_event_key = _as_text(item.get("comparison_event_key") or truth_binding.get("comparison_event_key"))
        key_payload: Dict[str, Any] = {}
        if not comparison_event_key:
            key_payload = comparison_event_key_payload(
                normalize_key_parts(
                    subject_as_of=subject_as_of,
                    lane=lane,
                    group=group,
                    members=_members(item),
                    event_start=_as_text(event.get("event_start")),
                    event_end=_as_text(event.get("event_end")),
                    horizon=_as_text(event.get("horizon")),
                    benchmark=_as_text(event.get("benchmark")),
                    event_type=_as_text(event.get("event_type")),
                    outcome_basis=outcome_basis,
                    benchmark_member_policy=benchmark_member_policy,
                )
            )
            comparison_event_key = key_payload["comparison_event_key"]
        return {
            "bound": True,
            "comparison_event_key": comparison_event_key,
            "comparison_event_key_schema": _as_text(item.get("comparison_event_key_schema") or COMPARISON_EVENT_KEY_SCHEMA),
            "comparison_event_key_authority": _as_text(
                item.get("comparison_event_key_authority")
                or truth_binding.get("comparison_event_key_authority")
                or key_payload.get("comparison_event_key_authority")
                or COMPARISON_EVENT_KEY_AUTHORITY
            ),
            "truth_join_key": _as_text(truth_binding.get("truth_join_key")),
            "subject_as_of": subject_as_of,
            "lane": lane,
            "group": group,
            "members_signature": member_signature,
            "event_start": _as_text(event.get("event_start")),
            "event_end": _as_text(event.get("event_end")),
            "horizon": _as_text(event.get("horizon")),
            "benchmark": _as_text(event.get("benchmark")),
            "event_type": _as_text(event.get("event_type")),
            "aggregation": _as_text(event.get("aggregation")),
            "outcome_basis": outcome_basis,
            "member_diagnostics_basis": _as_text(event.get("member_diagnostics_basis") or "per_member_directional_hit"),
            "benchmark_member_policy": benchmark_member_policy,
            "truth_source": _as_text(truth_binding.get("truth_source") or truth_binding.get("truth_artifact_ref")),
        }
    return {
        "bound": False,
        "comparison_event_key": "",
        "comparison_event_key_schema": COMPARISON_EVENT_KEY_SCHEMA,
        "comparison_event_key_authority": COMPARISON_EVENT_KEY_AUTHORITY,
        "truth_join_key": "",
        "subject_as_of": _subject_as_of(item),
        "lane": _as_text(_nested(item, "target", "universe")),
        "group": _as_text(_nested(item, "target", "entity_or_group")),
        "members_signature": members_signature(_members(item)),
        "event_start": "",
        "event_end": "",
        "horizon": _as_text(_nested(item, "target", "horizon")),
        "benchmark": _as_text(_nested(item, "target", "benchmark_definition")),
        "event_type": _as_text(_nested(item, "target", "event_definition")),
        "aggregation": "",
        "outcome_basis": OUTCOME_BASIS_MEAN_MEMBER_HIT,
        "member_diagnostics_basis": "per_member_directional_hit",
        "benchmark_member_policy": BENCHMARK_MEMBER_POLICY_INCLUDE_ZERO,
        "truth_source": "",
    }


def _event_contract_is_bound(contract: Mapping[str, Any]) -> bool:
    required = (
        "event_start",
        "event_end",
        "horizon",
        "benchmark",
        "event_type",
        "truth_join_key",
        "outcome_basis",
        "benchmark_member_policy",
    )
    return bool(contract.get("bound")) and all(_as_text(contract.get(key)) for key in required)


def _row_target(row: Mapping[str, Any]) -> str:
    return _upper(row.get("target_id") or row.get("member_id") or row.get("symbol") or row.get("ticker"))


def _row_truth_join_key(row: Mapping[str, Any]) -> str:
    return _as_text(row.get("truth_join_key") or row.get("forecast_truth_join_key"))


def _row_field(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        text = _as_text(row.get(key))
        if text:
            return text
    return ""


def load_reconciliation_rows(payload: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not payload:
        return []
    data = _data(payload)
    rows = data.get("rows")
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _row_quality_status(row: Mapping[str, Any]) -> str:
    return _upper(
        row.get("truth_quality_status")
        or row.get("truth_status")
        or row.get("quality_status")
        or row.get("quality_tone")
        or row.get("feed_quality_status")
    )


def _is_low_quality_truth(row: Mapping[str, Any]) -> bool:
    status = _row_quality_status(row)
    if status in {"BLOCKED", "STALE", "LOW", "BAD", "FAILURE", "DEGRADED_STALE"}:
        return True
    if row.get("truth_is_stale") is True or row.get("excluded_stale_or_low_quality_truth") is True:
        return True
    return False


def _truth_window(row: Mapping[str, Any]) -> str:
    return _row_field(row, "truth_window", "truth_window_label", "resolved_window")


def _filter_required_event_field(
    rows: Sequence[Mapping[str, Any]],
    *,
    aliases: Sequence[str],
    expected: str,
    mismatch_status: str,
) -> Tuple[List[Mapping[str, Any]], Optional[str]]:
    matched: List[Mapping[str, Any]] = []
    saw_mismatch = False
    for row in rows:
        value = _row_field(row, *aliases)
        if not value:
            continue
        if value == expected:
            matched.append(row)
        else:
            saw_mismatch = True
    if matched:
        return matched, None
    if saw_mismatch:
        return [], mismatch_status
    return [], STATUS_PENDING_TRUTH


def _matching_rows_for_member(
    rows: Sequence[Mapping[str, Any]],
    *,
    member: str,
    contract: Mapping[str, Any],
    truth_window: Optional[str] = None,
) -> Tuple[List[Mapping[str, Any]], Optional[str]]:
    candidates = [row for row in rows if _row_target(row) == member]
    if not candidates:
        return [], None

    join_key = _as_text(contract.get("truth_join_key"))
    if join_key:
        keyed = [row for row in candidates if _row_truth_join_key(row) == join_key]
        if keyed:
            candidates = keyed
        elif any(_row_truth_join_key(row) for row in candidates):
            return [], STATUS_PENDING_TRUTH

    required_fields = [
        (("subject_as_of", "forecast_as_of"), _as_text(contract.get("subject_as_of")), STATUS_TRUTH_WINDOW_MISMATCH),
        (("horizon", "forecast_horizon"), _as_text(contract.get("horizon")), STATUS_HORIZON_MISMATCH),
        (("benchmark", "benchmark_id"), _as_text(contract.get("benchmark")), STATUS_BENCHMARK_MISMATCH),
        (("event_start", "forecast_event_start"), _as_text(contract.get("event_start")), STATUS_TRUTH_WINDOW_MISMATCH),
        (("event_end", "forecast_event_end"), _as_text(contract.get("event_end")), STATUS_TRUTH_WINDOW_MISMATCH),
        (("event_type", "forecast_event_type"), _as_text(contract.get("event_type")), STATUS_TRUTH_WINDOW_MISMATCH),
        (("outcome_basis", "forecast_outcome_basis"), _as_text(contract.get("outcome_basis")), STATUS_TRUTH_WINDOW_MISMATCH),
        (
            ("benchmark_member_policy", "forecast_benchmark_member_policy"),
            _as_text(contract.get("benchmark_member_policy")),
            STATUS_TRUTH_WINDOW_MISMATCH,
        ),
    ]
    for aliases, expected, mismatch_status in required_fields:
        filtered, status = _filter_required_event_field(
            candidates,
            aliases=aliases,
            expected=expected,
            mismatch_status=mismatch_status,
        )
        if status:
            return [], status
        candidates = filtered

    if truth_window:
        requested_window = _as_text(truth_window)
        truth_window_rows = [row for row in candidates if not _truth_window(row) or _truth_window(row) == requested_window]
        if not truth_window_rows:
            return [], STATUS_TRUTH_WINDOW_MISMATCH
        candidates = truth_window_rows

    return candidates, None


def _realized_direction_from_prices(row: Mapping[str, Any]) -> Optional[str]:
    snapshot = _float(row.get("subject_snapshot_price"))
    realized = _float(row.get("realized_truth_price"))
    if snapshot is None or realized is None:
        return None
    delta = realized - snapshot
    if delta > 0:
        return "UP"
    if delta < 0:
        return "DOWN"
    return "FLAT"


def _realized_direction_from_returns(row: Mapping[str, Any]) -> Optional[str]:
    member_return = _float(row.get("member_return"))
    benchmark_return = _float(row.get("benchmark_return"), 0.0)
    if member_return is None:
        return None
    assert benchmark_return is not None
    excess_return = member_return - benchmark_return
    if excess_return > 0:
        return "UP"
    if excess_return < 0:
        return "DOWN"
    return "FLAT"


def _realized_direction(row: Mapping[str, Any], *, mode: str) -> Optional[str]:
    explicit = _upper(row.get("realized_direction") or row.get("truth_direction"))
    if explicit in {"UP", "DOWN", "FLAT"}:
        return explicit
    if mode == MODE_CP1_ADMITTED_ONLY:
        directional = _realized_direction_from_returns(row)
        if directional is not None:
            return directional
    return _realized_direction_from_prices(row)


def _member_outcome(
    *,
    row: Mapping[str, Any],
    member: str,
    direction: str,
    mode: str,
) -> Dict[str, Any]:
    realized_direction = _realized_direction(row, mode=mode)
    if realized_direction is None or realized_direction == "FLAT":
        outcome = 0.0
        hit = False
    else:
        hit = realized_direction == direction
        outcome = 1.0 if hit else 0.0
    return {
        "target_id": member,
        "realized_direction": realized_direction,
        "event_hit": hit,
        "outcome": outcome,
        "member_return": row.get("member_return"),
        "benchmark_return": row.get("benchmark_return"),
        "subject_snapshot_price": row.get("subject_snapshot_price"),
        "realized_truth_price": row.get("realized_truth_price"),
        "truth_join_key": _row_truth_join_key(row),
    }


def _empty_truth_coverage(item: Mapping[str, Any], *, minimum_coverage: float) -> Dict[str, Any]:
    expected = _members(item)
    return {
        "expected_member_count": len(expected),
        "resolved_member_count": 0,
        "missing_members": expected,
        "benchmark_resolved": False,
        "coverage_ratio": 0.0,
        "minimum_coverage_required": minimum_coverage,
    }


def _truth_coverage(
    item: Mapping[str, Any],
    member_outcomes: Sequence[Mapping[str, Any]],
    *,
    benchmark_resolved: bool,
    minimum_coverage: float,
) -> Dict[str, Any]:
    expected = _members(item)
    resolved = {_upper(row.get("target_id")) for row in member_outcomes if _upper(row.get("target_id"))}
    missing = [member for member in expected if member not in resolved]
    expected_count = len(expected)
    coverage_ratio = (len(resolved) / expected_count) if expected_count else 0.0
    return {
        "expected_member_count": expected_count,
        "resolved_member_count": len(resolved),
        "missing_members": missing,
        "benchmark_resolved": benchmark_resolved,
        "coverage_ratio": round(coverage_ratio, 6),
        "minimum_coverage_required": minimum_coverage,
    }


def _coverage_is_sufficient(coverage: Mapping[str, Any]) -> bool:
    return float(coverage.get("coverage_ratio") or 0.0) >= float(coverage.get("minimum_coverage_required") or 0.0)


def _matured_missing_status(contract: Mapping[str, Any], evaluation_as_of: Optional[str]) -> str:
    as_of_dt = _parse_dt(evaluation_as_of)
    event_end_dt = _parse_dt(contract.get("event_end"))
    if as_of_dt is not None and event_end_dt is not None and event_end_dt <= as_of_dt:
        return STATUS_MATURED_TRUTH_MISSING
    return STATUS_PENDING_TRUTH


def _score_event_rows(
    *,
    item: Mapping[str, Any],
    reconciliation_rows: Sequence[Mapping[str, Any]],
    mode: str,
    truth_window: Optional[str] = None,
    minimum_coverage: float = DEFAULT_MINIMUM_COVERAGE,
    evaluation_as_of: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[float], Optional[str], List[str], Dict[str, Any], Dict[str, Any]]:
    direction = _direction(item)
    probability = _probability(item)
    contract = _event_contract(item)
    outcome_basis = _as_text(contract.get("outcome_basis")) or OUTCOME_BASIS_MEAN_MEMBER_HIT
    benchmark_member_policy = _normalize_benchmark_member_policy(contract.get("benchmark_member_policy"))
    benchmark = _upper(contract.get("benchmark"))
    member_outcomes: List[Dict[str, Any]] = []
    member_brier_terms: List[float] = []
    member_binary_outcomes: List[float] = []
    member_excess_returns: List[float] = []
    status_override: Optional[str] = None
    exclusion_tags: List[str] = []
    benchmark_resolved = True

    for member in _members(item):
        if mode == MODE_CP1_ADMITTED_ONLY:
            matched_rows, match_status = _matching_rows_for_member(
                reconciliation_rows,
                member=member,
                contract=contract,
                truth_window=truth_window,
            )
            if match_status and status_override is None:
                status_override = match_status
            if not matched_rows:
                continue
            row = matched_rows[0]
        else:
            matched_rows = [row for row in reconciliation_rows if _row_target(row) == member]
            if not matched_rows:
                continue
            row = matched_rows[0]

        if _is_low_quality_truth(row):
            status_override = STATUS_LOW_QUALITY_TRUTH
            exclusion_tags.append("data_quality_miss")
            continue

        outcome_row = _member_outcome(row=row, member=member, direction=direction, mode=mode)
        outcome = float(outcome_row["outcome"])
        member_return = _float(row.get("member_return"))
        benchmark_return = _float(row.get("benchmark_return"))
        if mode == MODE_CP1_ADMITTED_ONLY:
            if member_return is None or benchmark_return is None:
                benchmark_resolved = False
                status_override = STATUS_MISSING_BENCHMARK_TRUTH
                exclusion_tags.append("truth_not_available")
                continue
            excess_return = member_return - benchmark_return
            outcome_row["member_excess_return"] = round(excess_return, 10)
            if (
                outcome_basis == OUTCOME_BASIS_GROUP_RETURN
                and benchmark_member_policy == BENCHMARK_MEMBER_POLICY_EXCLUDE
                and member == benchmark
            ):
                outcome_row["claim_outcome_excluded"] = True
            else:
                member_excess_returns.append(excess_return)
        member_binary_outcomes.append(outcome)
        member_brier_terms.append((probability - outcome) ** 2)
        member_outcomes.append(outcome_row)

    coverage = _truth_coverage(
        item,
        member_outcomes,
        benchmark_resolved=benchmark_resolved and bool(member_outcomes),
        minimum_coverage=minimum_coverage,
    )
    event_result: Dict[str, Any] = {
        "outcome_basis": outcome_basis,
        "benchmark_member_policy": benchmark_member_policy,
        "event_outcome": None,
        "realized_event_direction": None,
        "group_excess_return": None,
        "member_hit_rate": _round_optional(
            (sum(member_binary_outcomes) / len(member_binary_outcomes)) if member_binary_outcomes else None
        ),
    }

    if not member_outcomes:
        no_truth_status = status_override
        if no_truth_status in {None, STATUS_PENDING_TRUTH}:
            no_truth_status = _matured_missing_status(contract, evaluation_as_of)
        return (
            member_outcomes,
            None,
            None,
            no_truth_status,
            exclusion_tags,
            coverage,
            event_result,
        )
    if not coverage.get("benchmark_resolved"):
        return member_outcomes, None, None, STATUS_MISSING_BENCHMARK_TRUTH, exclusion_tags, coverage, event_result
    if not _coverage_is_sufficient(coverage):
        return member_outcomes, None, None, STATUS_INSUFFICIENT_MEMBER_COVERAGE, exclusion_tags, coverage, event_result

    if outcome_basis == OUTCOME_BASIS_GROUP_RETURN:
        if not member_excess_returns:
            return (
                member_outcomes,
                None,
                None,
                STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION,
                exclusion_tags,
                coverage,
                event_result,
            )
        group_excess_return = sum(member_excess_returns) / len(member_excess_returns)
        if group_excess_return > 0:
            realized_direction = "UP"
        elif group_excess_return < 0:
            realized_direction = "DOWN"
        else:
            realized_direction = "FLAT"
        event_outcome = 1.0 if realized_direction == direction else 0.0
        brier_score = (probability - event_outcome) ** 2
        event_result.update(
            {
                "event_outcome": event_outcome,
                "realized_event_direction": realized_direction,
                "group_excess_return": round(group_excess_return, 10),
            }
        )
        return member_outcomes, brier_score, event_outcome, None, exclusion_tags, coverage, event_result

    if not member_brier_terms:
        return member_outcomes, None, None, status_override, exclusion_tags, coverage, event_result
    event_outcome = sum(member_binary_outcomes) / len(member_binary_outcomes)
    event_result.update(
        {
            "event_outcome": event_outcome,
            "realized_event_direction": "MIXED" if 0.0 < event_outcome < 1.0 else direction if event_outcome == 1.0 else "MISS",
        }
    )
    return (
        member_outcomes,
        sum(member_brier_terms) / len(member_brier_terms),
        event_outcome,
        None,
        exclusion_tags,
        coverage,
        event_result,
    )


def _configured_horizons(horizon: Optional[str]) -> List[str]:
    if not horizon:
        return []
    return [_as_text(item) for item in str(horizon).split(",") if _as_text(item)]


def _status_for_preflight(
    item: Mapping[str, Any],
    *,
    mode: str,
    horizon_filter: Sequence[str],
) -> Optional[str]:
    contract = _event_contract(item)
    direction = _direction(item)
    if direction == "ABSTAIN":
        return STATUS_ABSTAINED
    if mode == MODE_CP1_ADMITTED_ONLY and not _event_contract_is_bound(contract):
        return STATUS_MISSING_EVENT_BINDING
    if (
        mode == MODE_CP1_ADMITTED_ONLY
        and contract.get("outcome_basis") == OUTCOME_BASIS_GROUP_RETURN
        and contract.get("benchmark_member_policy") == BENCHMARK_MEMBER_POLICY_REJECT
        and _upper(contract.get("benchmark")) in set(_members(item))
    ):
        return STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION
    if horizon_filter and _as_text(contract.get("horizon")) not in set(horizon_filter):
        return STATUS_HORIZON_MISMATCH
    return None


def _residual_tags_for_status(status: str, *, brier_score: Optional[float], event_rate: Optional[float], probability: float) -> List[str]:
    tags: List[str] = []
    if status == STATUS_PENDING_TRUTH:
        tags.append("truth_not_available")
    elif status == STATUS_MISSING_EVENT_BINDING:
        tags.append("event_contract_unbound")
    elif status == STATUS_HORIZON_MISMATCH:
        tags.append("horizon_mismatch")
    elif status == STATUS_BENCHMARK_MISMATCH:
        tags.append("benchmark_mismatch")
    elif status == STATUS_TRUTH_WINDOW_MISMATCH:
        tags.append("truth_window_mismatch")
    elif status == STATUS_INSUFFICIENT_MEMBER_COVERAGE:
        tags.append("low_member_coverage")
    elif status == STATUS_MISSING_BENCHMARK_TRUTH:
        tags.append("missing_benchmark_truth")
    elif status == STATUS_MATURED_TRUTH_MISSING:
        tags.append("truth_not_available")
        tags.append("matured_truth_missing")
    elif status == STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION:
        tags.append("benchmark_member_policy_violation")
    elif status == STATUS_LOW_QUALITY_TRUTH:
        tags.append("data_quality_miss")
    elif status == STATUS_ABSTAINED:
        tags.append("abstention_would_have_been_correct" if event_rate is None else "abstained")
    elif status == STATUS_RESOLVED:
        if brier_score is not None and brier_score > 0.25:
            tags.append("directional_miss")
        else:
            tags.append("directional_signal_supported")
        if event_rate is not None:
            if probability - event_rate >= 0.2:
                tags.append("calibration_overconfident")
            elif event_rate - probability >= 0.2:
                tags.append("calibration_underconfident")
    return tags


def build_scorecard(
    item: Mapping[str, Any],
    reconciliation_rows: Sequence[Mapping[str, Any]],
    *,
    mode: str = MODE_CP1_ADMITTED_ONLY,
    horizon_filter: Sequence[str] = (),
    truth_window: Optional[str] = None,
    minimum_coverage: float = DEFAULT_MINIMUM_COVERAGE,
    evaluation_as_of: Optional[str] = None,
) -> Dict[str, Any]:
    probability = _probability(item)
    contract = _event_contract(item)
    preflight_status = _status_for_preflight(item, mode=mode, horizon_filter=horizon_filter)

    if preflight_status:
        member_outcomes: List[Dict[str, Any]] = []
        brier_score = None
        event_rate = None
        status = preflight_status
        exclusion_tags: List[str] = []
        truth_coverage = _empty_truth_coverage(item, minimum_coverage=minimum_coverage)
        event_result: Dict[str, Any] = {
            "outcome_basis": contract.get("outcome_basis"),
            "benchmark_member_policy": contract.get("benchmark_member_policy"),
            "event_outcome": None,
            "realized_event_direction": None,
            "group_excess_return": None,
            "member_hit_rate": None,
        }
    else:
        (
            member_outcomes,
            brier_score,
            event_rate,
            status_override,
            exclusion_tags,
            truth_coverage,
            event_result,
        ) = _score_event_rows(
            item=item,
            reconciliation_rows=reconciliation_rows,
            mode=mode,
            truth_window=truth_window,
            minimum_coverage=minimum_coverage,
            evaluation_as_of=evaluation_as_of,
        )
        if status_override:
            status = status_override
        elif brier_score is None:
            status = STATUS_PENDING_TRUTH
        else:
            status = STATUS_RESOLVED

    residual_tags = _residual_tags_for_status(
        status,
        brier_score=brier_score,
        event_rate=event_rate,
        probability=probability,
    )
    for tag in exclusion_tags:
        if tag not in residual_tags:
            residual_tags.append(tag)

    scorecard = {
        "schema_version": "finance_forecast_scorecard_v1",
        "forecast_id": _forecast_id(item),
        "candidate_ref": _as_text(item.get("candidate_ref") or _forecast_id(item)),
        "comparison_event_key": _as_text(contract.get("comparison_event_key")),
        "comparison_event_key_schema": _as_text(contract.get("comparison_event_key_schema") or COMPARISON_EVENT_KEY_SCHEMA),
        "comparison_event_key_authority": _as_text(
            contract.get("comparison_event_key_authority") or COMPARISON_EVENT_KEY_AUTHORITY
        ),
        "status": status,
        "mode": mode,
        "generator_variant_id": _generator_variant_id(item),
        "pair_audit": {
            "forecast_id": _forecast_id(item),
            "candidate_ref": _as_text(item.get("candidate_ref") or _forecast_id(item)),
            "truth_join_key": _as_text(contract.get("truth_join_key")),
            "generator_variant_id": _generator_variant_id(item),
            "calibrator_id": _as_text(item.get("calibrator_id")),
        },
        "event_contract": contract,
        "target": (
            dict(item.get("subject", {}))
            if _is_admitted_claim(item) and isinstance(item.get("subject"), Mapping)
            else dict(item.get("target", {})) if isinstance(item.get("target"), Mapping) else {}
        ),
        "proper_score": {
            "score_rule": "brier_score_binary_directional_event",
            "outcome_basis": event_result.get("outcome_basis"),
            "benchmark_member_policy": event_result.get("benchmark_member_policy"),
            "directional_hit_probability": probability,
            "event_outcome": _round_optional(_float(event_result.get("event_outcome"))),
            "brier_score": _round_optional(brier_score),
            "event_rate": _round_optional(event_rate),
            "realized_event_direction": event_result.get("realized_event_direction"),
            "group_excess_return": _round_optional(_float(event_result.get("group_excess_return"))),
        },
        "calibration": {
            "probability_bin": probability_bin_label(probability),
            "base_rate": _round_optional(event_rate),
            "resolved_member_count": len(member_outcomes),
        },
        "truth_coverage": truth_coverage,
        "member_diagnostics": {
            "member_diagnostics_basis": contract.get("member_diagnostics_basis"),
            "diagnostic_only": contract.get("outcome_basis") != OUTCOME_BASIS_MEAN_MEMBER_HIT,
            "member_hit_rate": event_result.get("member_hit_rate"),
            "member_outcomes": member_outcomes,
        },
        "finance_validation": {
            "direction": _direction(item),
            "horizon": contract.get("horizon"),
            "event_start": contract.get("event_start"),
            "event_end": contract.get("event_end"),
            "benchmark": contract.get("benchmark"),
            "event_type": contract.get("event_type"),
            "aggregation": contract.get("aggregation"),
            "outcome_basis": contract.get("outcome_basis"),
            "benchmark_member_policy": contract.get("benchmark_member_policy"),
            "truth_window": truth_window,
            "leakage_guard": _nested(item, "admissibility", "leakage_guard"),
            "member_outcomes": member_outcomes,
        },
        "data_quality": {
            "truth_match_status": (
                "matched_contract_rows"
                if member_outcomes and status == STATUS_RESOLVED
                else "matched_partial_contract_rows"
                if member_outcomes
                else "no_admissible_truth_rows"
            ),
            "source_artifact_refs": _nested(item, "identity", "source_artifact_refs")
            or item.get("source_artifact_refs")
            or [],
            "no_trade_advice_flag": bool(_nested(item, "admissibility", "no_trade_advice_flag")),
        },
        "residual_diagnosis": {
            "tags": residual_tags,
            "notes": [] if residual_tags else ["no residual diagnosis emitted"],
        },
    }
    return scorecard


def probability_bin_label(probability: float) -> str:
    low = min(0.9, max(0.0, int(probability * 10) / 10))
    high = min(1.0, low + 0.1)
    return f"{low:.1f}-{high:.1f}"


def _resolved_scorecards(scorecards: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [card for card in scorecards if card.get("status") == STATUS_RESOLVED]


def _scorecard_probability(card: Mapping[str, Any]) -> float:
    return float(_nested(card, "proper_score", "directional_hit_probability") or 0.5)


def _scorecard_event_rate(card: Mapping[str, Any]) -> Optional[float]:
    return _float(_nested(card, "proper_score", "event_rate"))


def _scorecard_brier(card: Mapping[str, Any]) -> Optional[float]:
    return _float(_nested(card, "proper_score", "brier_score"))


def calibration_summary(scorecards: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    resolved = _resolved_scorecards(scorecards)
    pending_count = sum(1 for card in scorecards if card.get("status") == STATUS_PENDING_TRUTH)
    matured_truth_missing_count = sum(1 for card in scorecards if card.get("status") == STATUS_MATURED_TRUTH_MISSING)
    brier_values = [value for value in (_scorecard_brier(card) for card in resolved) if value is not None]
    event_rates = [value for value in (_scorecard_event_rate(card) for card in resolved) if value is not None]
    mean_brier = sum(brier_values) / len(brier_values) if brier_values else None
    base_rate = sum(event_rates) / len(event_rates) if event_rates else None

    bins_by_label: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for card in resolved:
        bins_by_label[probability_bin_label(_scorecard_probability(card))].append(card)

    bins: List[Dict[str, Any]] = []
    reliability = 0.0
    resolution = 0.0
    total_resolved = max(len(resolved), 1)
    for label in sorted(bins_by_label):
        cards = bins_by_label[label]
        mean_probability = sum(_scorecard_probability(card) for card in cards) / len(cards)
        bin_event_rates = [value for value in (_scorecard_event_rate(card) for card in cards) if value is not None]
        observed_rate = sum(bin_event_rates) / len(bin_event_rates) if bin_event_rates else None
        reliability_error = abs(mean_probability - observed_rate) if observed_rate is not None else None
        if observed_rate is not None:
            weight = len(cards) / total_resolved
            reliability += weight * ((mean_probability - observed_rate) ** 2)
            if base_rate is not None:
                resolution += weight * ((observed_rate - base_rate) ** 2)
        bins.append(
            {
                "probability_bin": label,
                "forecast_count": len(cards),
                "observed_event_rate": _round_optional(observed_rate),
                "mean_probability": round(mean_probability, 6),
                "reliability_error": _round_optional(reliability_error),
            }
        )

    uncertainty = base_rate * (1.0 - base_rate) if base_rate is not None else None
    skill = None
    if mean_brier is not None and uncertainty and uncertainty > 0:
        skill = 1.0 - (mean_brier / uncertainty)

    return {
        "score_rule": "brier_score_binary_directional_event",
        "forecast_count": len(scorecards),
        "resolved_count": len(resolved),
        "pending_count": pending_count,
        "matured_truth_missing_count": matured_truth_missing_count,
        "mean_brier": _round_optional(mean_brier),
        "base_rate": _round_optional(base_rate),
        "brier_skill_vs_base_rate": _round_optional(skill),
        "bins": bins,
        "decomposition": {
            "reliability": _round_optional(reliability) if resolved else None,
            "resolution": _round_optional(resolution) if resolved and base_rate is not None else None,
            "uncertainty": _round_optional(uncertainty),
            "method": "murphy_style_binary_brier_decomposition_over_probability_bins",
        },
    }


def generator_variant_summary(scorecards: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_variant: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for card in scorecards:
        by_variant[_as_text(card.get("generator_variant_id")) or "unknown_generator"].append(card)
    rows: List[Dict[str, Any]] = []
    for variant, cards in sorted(by_variant.items()):
        summary = calibration_summary(cards)
        rows.append(
            {
                "generator_variant_id": variant,
                "forecast_count": len(cards),
                "resolved_count": summary["resolved_count"],
                "pending_count": summary["pending_count"],
                "mean_brier": summary["mean_brier"],
                "brier_skill_vs_base_rate": summary["brier_skill_vs_base_rate"],
            }
        )
    return rows


def residual_counts(scorecards: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for card in scorecards:
        tags = _nested(card, "residual_diagnosis", "tags")
        if isinstance(tags, list):
            counter.update(_as_text(tag) for tag in tags if _as_text(tag))
    return dict(sorted(counter.items()))


def build_operating_picture(
    *,
    scorecards: Sequence[Mapping[str, Any]],
    source_refs: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    summary = calibration_summary(scorecards)
    pending_cards = [card for card in scorecards if card.get("status") in {STATUS_PENDING_TRUTH, STATUS_MATURED_TRUTH_MISSING}]
    pending_by_horizon: Counter[str] = Counter(
        _as_text(_nested(card, "event_contract", "horizon") or _nested(card, "finance_validation", "horizon") or "unknown")
        for card in pending_cards
    )
    maturing_next = sorted(
        [
            {
                "forecast_id": _as_text(card.get("forecast_id")),
                "event_end": _as_text(_nested(card, "event_contract", "event_end")),
                "horizon": _as_text(_nested(card, "event_contract", "horizon")),
                "status": _as_text(card.get("status")),
            }
            for card in pending_cards
        ],
        key=lambda row: (row["event_end"], row["forecast_id"]),
    )[:10]
    residual = residual_counts(scorecards)
    status_counter: Counter[str] = Counter(_as_text(card.get("status")) for card in scorecards)
    admitted_count = sum(1 for card in scorecards if _as_text(_nested(card, "event_contract", "truth_join_key")))
    benchmark_policies = Counter(
        _as_text(_nested(card, "event_contract", "benchmark_member_policy") or "unknown") for card in scorecards
    )
    invariant_checked = [
        card
        for card in scorecards
        if _nested(card, "proper_score", "outcome_basis") == OUTCOME_BASIS_GROUP_RETURN
        and card.get("status") in {STATUS_RESOLVED, STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION}
    ]
    invariant_status = "unknown"
    if invariant_checked:
        invariant_status = "pass"
        for card in invariant_checked:
            proper = card.get("proper_score") if isinstance(card.get("proper_score"), Mapping) else {}
            if card.get("status") == STATUS_RESOLVED and proper.get("event_outcome") is None:
                invariant_status = "fail"
                break
    return {
        "schema_version": "finance_eval_operating_picture_v0",
        "generated_at": feed_envelope.utc_now().iso,
        "source_refs": dict(source_refs or {}),
        "integrity": {
            "claim_outcome_invariant_status": invariant_status,
            "benchmark_member_policy": benchmark_policies.most_common(1)[0][0] if benchmark_policies else "unknown",
            "candidate_smoke_test_count": sum(1 for card in scorecards if card.get("mode") == MODE_CANDIDATE_SMOKE_TEST),
            "production_cp1_admitted_count": sum(1 for card in scorecards if card.get("mode") == MODE_CP1_ADMITTED_ONLY),
            "benchmark_member_policy_violation_count": status_counter.get(STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION, 0),
        },
        "lifecycle": {
            "candidate_count": max(0, len(scorecards) - admitted_count),
            "admitted_count": admitted_count,
            "pending_maturity_count": status_counter.get(STATUS_PENDING_TRUTH, 0),
            "matured_truth_missing_count": status_counter.get(STATUS_MATURED_TRUTH_MISSING, 0),
            "truth_materialized_count": status_counter.get(STATUS_RESOLVED, 0)
            + status_counter.get(STATUS_LOW_QUALITY_TRUTH, 0)
            + status_counter.get(STATUS_INSUFFICIENT_MEMBER_COVERAGE, 0)
            + status_counter.get(STATUS_MISSING_BENCHMARK_TRUTH, 0),
            "resolved_scored_count": summary["resolved_count"],
            "excluded_count": sum(count for status, count in status_counter.items() if status.startswith("excluded")),
            "not_admissible_count": sum(count for status, count in status_counter.items() if status.startswith("not_admissible")),
        },
        "pending": {
            "count": len(pending_cards),
            "by_horizon": dict(sorted(pending_by_horizon.items())),
            "maturing_next": maturing_next,
        },
        "resolved": {
            "count": summary["resolved_count"],
            "mean_brier": summary["mean_brier"],
            "brier_skill_vs_base_rate": summary["brier_skill_vs_base_rate"],
            "calibration_bins": summary["bins"],
        },
        "residuals": {
            "regime_miss": residual.get("regime_shift_after_subject_time", 0),
            "data_quality_miss": residual.get("data_quality_miss", 0),
            "truth_unavailable": residual.get("truth_not_available", 0),
            "event_contract_gap": residual.get("event_contract_unbound", 0),
            "right_direction_wrong_size": residual.get("right_direction_wrong_size", 0),
            "all_tags": residual,
        },
        "generator_variants": generator_variant_summary(scorecards),
        "historical_replay": {
            "latest_experiment_id": None,
            "split_policy": None,
            "resolved_count": 0,
            "holdout_count": 0,
            "mean_brier": None,
            "brier_skill_vs_base_rate": None,
        },
        "calibration_gate": {
            "active_calibrator_id": None,
            "shadow_calibrator_count": 0,
            "live_probability_mutation_allowed": False,
        },
    }


def evaluate(
    forecast_items: Iterable[Mapping[str, Any]],
    *,
    prediction_reconciliation: Optional[Mapping[str, Any]] = None,
    mode: str = MODE_CP1_ADMITTED_ONLY,
    horizon: Optional[str] = None,
    truth_window: Optional[str] = None,
    score: str = "proper+calibration+data_quality",
    minimum_coverage: float = DEFAULT_MINIMUM_COVERAGE,
    evaluation_as_of: Optional[str] = None,
) -> Dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported replay mode: {mode}")
    if score not in SUPPORTED_SCORE_BUNDLES:
        raise ValueError(f"unsupported score bundle: {score}")
    rows = load_reconciliation_rows(prediction_reconciliation)
    horizon_filter = _configured_horizons(horizon)
    scorecards = [
        build_scorecard(
            item,
            rows,
            mode=mode,
            horizon_filter=horizon_filter,
            truth_window=truth_window,
            minimum_coverage=minimum_coverage,
            evaluation_as_of=evaluation_as_of,
        )
        for item in forecast_items
    ]
    resolved = _resolved_scorecards(scorecards)
    summary = calibration_summary(scorecards)
    aggregate = {
        "forecast_card_count": len(scorecards),
        "resolved_forecast_count": len(resolved),
        "pending_forecast_count": sum(1 for card in scorecards if card["status"] == STATUS_PENDING_TRUTH),
        "matured_truth_missing_count": sum(1 for card in scorecards if card["status"] == STATUS_MATURED_TRUTH_MISSING),
        "abstained_forecast_count": sum(1 for card in scorecards if card["status"] == STATUS_ABSTAINED),
        "not_admissible_forecast_count": sum(1 for card in scorecards if str(card["status"]).startswith("not_admissible")),
        "excluded_forecast_count": sum(1 for card in scorecards if str(card["status"]).startswith("excluded")),
        "mean_brier_score": summary["mean_brier"],
        "truth_row_count": len(rows),
        "mode": mode,
        "horizon_filter": horizon_filter,
        "truth_window": truth_window,
        "score_bundle": score,
        "minimum_coverage": minimum_coverage,
    }
    operating_picture = build_operating_picture(
        scorecards=scorecards,
        source_refs={
            "calculator_artifacts": [],
            "admitted_claims": [],
            "resolution_artifacts": [],
            "scorecard_artifacts": [],
        },
    )
    return {
        "scorecards": scorecards,
        "aggregate": aggregate,
        "calibration_summary": summary,
        "generator_variants": generator_variant_summary(scorecards),
        "residuals": residual_counts(scorecards),
        "operating_picture": operating_picture,
    }


def run(config: Dict[str, Any], run_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        forecast_cards_path = config.get("forecast_cards") or config.get("forecast_cards_path")
        if not forecast_cards_path:
            raise ValueError("forecast_cards path is required")
        reconciliation_path = config.get("prediction_reconciliation") or config.get("prediction_reconciliation_path")
        mode = _as_text(config.get("mode") or MODE_CP1_ADMITTED_ONLY)
        horizon = config.get("horizon")
        truth_window = config.get("truth_window")
        score = _as_text(config.get("score") or "proper+calibration+data_quality")
        minimum_coverage = float(config.get("minimum_coverage", DEFAULT_MINIMUM_COVERAGE))

        forecast_payload = _read_json(Path(str(forecast_cards_path)))
        reconciliation_payload = _read_json(Path(str(reconciliation_path))) if reconciliation_path else None
        items = load_forecast_items(forecast_payload, mode=mode)
        now = feed_envelope.utc_now()
        runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), Mapping) else {}
        as_of = str(runtime.get("as_of") or now.iso)
        data = evaluate(
            items,
            prediction_reconciliation=reconciliation_payload,
            mode=mode,
            horizon=str(horizon) if horizon else None,
            truth_window=str(truth_window) if truth_window else None,
            score=score,
            minimum_coverage=minimum_coverage,
            evaluation_as_of=as_of,
        )
        source_refs = {
            "forecast_cards": str(forecast_cards_path),
            "prediction_reconciliation": str(reconciliation_path) if reconciliation_path else None,
        }
        data["operating_picture"]["source_refs"].update(
            {
                "calculator_artifacts": [str(forecast_cards_path)],
                "resolution_artifacts": [str(reconciliation_path)] if reconciliation_path else [],
            }
        )

        run_id = str(runtime.get("run_id") or (run_dir.name if run_dir else "finance_eval_replay"))
        diagnostics = feed_envelope.new_diagnostics(
            input_rows=len(items),
            output_rows=len(data["scorecards"]),
            dropped_rows=0,
            pending_truth_count=data["aggregate"]["pending_forecast_count"],
            not_admissible_count=data["aggregate"]["not_admissible_forecast_count"],
            score_rule="brier_score_binary_directional_event",
            replay_mode=mode,
            truth_window=truth_window,
            minimum_coverage=minimum_coverage,
            source_refs=source_refs,
        )
        metadata = feed_envelope.build_metadata(
            tool=TOOL_NAME,
            status="success",
            now=now,
            run_id=run_id,
            as_of=as_of,
            items_count=len(data["scorecards"]),
            diagnostics=diagnostics,
            data_schema_version=DATA_SCHEMA_VERSION,
            timestamp=now.iso,
        )
        return {"metadata": metadata, "data": data}
    except Exception as exc:
        return _failure_envelope(str(exc), run_dir=run_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay finance forecast claims against delayed truth.")
    parser.add_argument("--forecast-cards", required=True, help="Calculator artifact, admitted-claim envelope, or raw card JSON.")
    parser.add_argument("--prediction-reconciliation", help="Prediction reconciliation artifact with realized prices/returns.")
    parser.add_argument("--truth-window", help="Optional resolved truth-window label; enforced when truth rows carry a window.")
    parser.add_argument("--horizon", help="Optional comma-separated horizon filter.")
    parser.add_argument(
        "--minimum-coverage",
        type=float,
        default=DEFAULT_MINIMUM_COVERAGE,
        help="Minimum member-truth coverage ratio required before scoring an admitted claim.",
    )
    parser.add_argument(
        "--mode",
        default=MODE_CP1_ADMITTED_ONLY,
        choices=sorted(SUPPORTED_MODES),
        help="Replay admission mode. Default refuses inert candidates.",
    )
    parser.add_argument(
        "--score",
        default="proper+calibration+data_quality",
        choices=sorted(SUPPORTED_SCORE_BUNDLES),
        help="Supported score bundle.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON envelope.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(
        {
            "forecast_cards": args.forecast_cards,
            "prediction_reconciliation": args.prediction_reconciliation,
            "truth_window": args.truth_window,
            "horizon": args.horizon,
            "mode": args.mode,
            "score": args.score,
            "minimum_coverage": args.minimum_coverage,
            "runtime": {"run_id": "finance_eval_replay"},
        }
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text if args.json else text)
    return 0 if payload.get("metadata", {}).get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
