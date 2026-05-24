#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Convert inert calculator forecast candidates into CP1-admitted
  finance forecast claims with explicit event windows and truth-join contracts.
- Mechanism: Load `candidate_forecast_cards`, bind horizon/benchmark/event
  semantics under an admission policy, and emit `finance_forecast_claim_v1`
  objects in an ArtifactEnvelope.

[INTERFACE]
- Reads: calculator artifact or raw candidate-card JSON.
- Reads: optional admission policy JSON.
- Returns/prints: `finance_forecast_admission.1` envelope with admitted claims.

[CONSTRAINTS]
- Admission is a contract transform, not a trading recommendation.
- ABSTAIN and unbound candidates remain rejected, not silently committed.
- The emitted claim is CP1-admitted only for evaluation/replay; it does not
  rewrite the canonical Lab CP1/CP2 schema.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from system.lib import feed_envelope
from tools.finance.event_keys import (
    COMPARISON_EVENT_KEY_AUTHORITY,
    COMPARISON_EVENT_KEY_SCHEMA,
    comparison_event_key_payload,
    normalize_key_parts,
)
from tools.finance.eval_replay import load_forecast_cards

TOOL_NAME = "finance_forecast_admission"
DATA_SCHEMA_VERSION = "finance_forecast_admission.2"
CLAIM_SCHEMA_VERSION = "finance_forecast_claim_v1"
DEFAULT_EVENT_TYPE = "group_return_direction_vs_benchmark"
DEFAULT_AGGREGATION = "equal_weight_member_return"
DEFAULT_OUTCOME_BASIS = "equal_weight_group_return_direction"
DEFAULT_MEMBER_DIAGNOSTICS_BASIS = "per_member_directional_hit"
DEFAULT_BENCHMARK_MEMBER_POLICY = "reject_if_benchmark_is_member"
SUPPORTED_BENCHMARK_MEMBER_POLICIES = {
    "reject_if_benchmark_is_member",
    "include_as_zero_excess",
    "exclude_from_claim_outcome",
}


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else payload


def _as_text(value: Any) -> str:
    return str(value or "").strip()


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


def _parse_dt(value: str) -> datetime:
    text = _as_text(value)
    if not text:
        raise ValueError("as_of/event_start timestamp is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _parse_horizon_days(horizon: str) -> int:
    text = _as_text(horizon).lower()
    if not text.endswith("d"):
        raise ValueError(f"unsupported horizon {horizon!r}; expected Nd")
    try:
        days = int(text[:-1])
    except ValueError as exc:
        raise ValueError(f"unsupported horizon {horizon!r}; expected Nd") from exc
    if days <= 0:
        raise ValueError("horizon days must be positive")
    return days


def _stable_digest(*parts: Any, length: int = 16) -> str:
    text = "|".join(_as_text(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _candidate_id(card: Mapping[str, Any]) -> str:
    return _as_text(_nested(card, "identity", "forecast_id") or card.get("forecast_id"))


def _candidate_as_of(card: Mapping[str, Any]) -> str:
    return _as_text(_nested(card, "identity", "as_of"))


def _direction(card: Mapping[str, Any]) -> str:
    return _as_text(_nested(card, "target", "direction")).upper()


def _members(card: Mapping[str, Any]) -> List[str]:
    raw = _nested(card, "target", "members")
    if not isinstance(raw, list):
        return []
    return sorted({str(member).upper().strip() for member in raw if str(member).strip()})


def _probability(card: Mapping[str, Any]) -> float:
    value = _float(_nested(card, "belief", "directional_hit_probability"))
    if value is None:
        value = _float(_nested(card, "belief", "event_probability"), 0.5)
    assert value is not None
    return max(0.0, min(1.0, value))


def _load_policy(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    payload = _read_json(Path(path))
    data = _data(payload)
    return dict(data) if isinstance(data, Mapping) else {}


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


def admit_card(
    card: Mapping[str, Any],
    *,
    horizon: str,
    benchmark: str,
    cp1_ref: str,
    event_type: str = DEFAULT_EVENT_TYPE,
    aggregation: str = DEFAULT_AGGREGATION,
    outcome_basis: str = DEFAULT_OUTCOME_BASIS,
    member_diagnostics_basis: str = DEFAULT_MEMBER_DIAGNOSTICS_BASIS,
    benchmark_member_policy: str = DEFAULT_BENCHMARK_MEMBER_POLICY,
    policy_ref: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    direction = _direction(card)
    if direction == "ABSTAIN":
        return None
    if direction not in {"UP", "DOWN"}:
        return None

    candidate_id = _candidate_id(card)
    if not candidate_id:
        return None
    as_of_dt = _parse_dt(_candidate_as_of(card))
    event_start = as_of_dt.isoformat()
    event_end = (as_of_dt + timedelta(days=_parse_horizon_days(horizon))).isoformat()
    group = _as_text(_nested(card, "target", "entity_or_group"))
    lane = _as_text(_nested(card, "target", "universe"))
    members = _members(card)
    key_parts = normalize_key_parts(
        subject_as_of=event_start,
        lane=lane,
        group=group,
        members=members,
        event_start=event_start,
        event_end=event_end,
        horizon=horizon,
        benchmark=benchmark,
        event_type=event_type,
        outcome_basis=outcome_basis,
        benchmark_member_policy=benchmark_member_policy,
    )
    key_payload = comparison_event_key_payload(key_parts)
    comparison_event_key = key_payload["comparison_event_key"]
    truth_join_key = "finance_truth_" + _stable_digest(
        candidate_id,
        event_start,
        event_end,
        horizon,
        benchmark,
        event_type,
        aggregation,
        outcome_basis,
        benchmark_member_policy,
    )
    claim_id = "ff_claim_" + _stable_digest(truth_join_key, cp1_ref, lane, group)

    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "claim_status": "cp1_admitted",
        "forecast_id": claim_id,
        "candidate_ref": candidate_id,
        "comparison_event_key": comparison_event_key,
        "comparison_event_key_schema": COMPARISON_EVENT_KEY_SCHEMA,
        "comparison_event_key_authority": COMPARISON_EVENT_KEY_AUTHORITY,
        "comparison_event_key_parts": key_payload["comparison_event_key_parts"],
        "cp1_ref": cp1_ref,
        "generator_variant_id": _as_text(_nested(card, "identity", "generator_variant_id"))
        or "calculator:calculator.6:default",
        "subject": {
            "as_of": event_start,
            "lane": lane,
            "group": group,
            "members": members,
        },
        "event": {
            "event_type": event_type,
            "horizon": horizon,
            "event_start": event_start,
            "event_end": event_end,
            "benchmark": benchmark,
            "direction": direction,
            "aggregation": aggregation,
            "outcome_basis": outcome_basis,
            "member_diagnostics_basis": member_diagnostics_basis,
            "benchmark_member_policy": benchmark_member_policy,
        },
        "belief": {
            "directional_hit_probability": _probability(card),
            "confidence": _as_text(_nested(card, "belief", "confidence")) or "LOW",
            "source_kind": _as_text(_nested(card, "belief", "kind")) or "calculator_score_proxy_not_calibrated",
        },
        "explanation": dict(card.get("explanation", {})) if isinstance(card.get("explanation"), Mapping) else {},
        "truth_binding": {
            "truth_join_key": truth_join_key,
            "comparison_event_key": comparison_event_key,
            "comparison_event_key_schema": COMPARISON_EVENT_KEY_SCHEMA,
            "comparison_event_key_authority": COMPARISON_EVENT_KEY_AUTHORITY,
            "truth_source": "prediction_reconciliation",
            "required_truth_fields": [
                "target_id",
                "truth_join_key",
                "comparison_event_key",
                "member_return",
                "benchmark_return",
                "event_start",
                "event_end",
                "horizon",
                "benchmark",
                "event_type",
                "outcome_basis",
                "benchmark_member_policy",
            ],
        },
        "admissibility": {
            "candidate_only_not_cp1_commitment": False,
            "cp1_commitment": True,
            "no_trade_advice_flag": True,
            "leakage_guard": "subject_time_only_inputs_plus_horizon_embargo",
            "subject_truth_split_ref": "codex/substrate/contracts/schema_cp2.json::oracle_contract_model",
            "cp1_prompt_or_policy_ref": policy_ref or "codex/substrate/contracts/schema_cp1.json",
        },
    }


def admit_cards(
    cards: List[Mapping[str, Any]],
    *,
    horizon: str,
    benchmark: str,
    cp1_ref: str,
    max_cards: int,
    event_type: str = DEFAULT_EVENT_TYPE,
    aggregation: str = DEFAULT_AGGREGATION,
    outcome_basis: str = DEFAULT_OUTCOME_BASIS,
    member_diagnostics_basis: str = DEFAULT_MEMBER_DIAGNOSTICS_BASIS,
    benchmark_member_policy: str = DEFAULT_BENCHMARK_MEMBER_POLICY,
    policy_ref: Optional[str] = None,
) -> Dict[str, Any]:
    admitted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for card in cards:
        if len(admitted) >= max_cards:
            break
        claim = admit_card(
            card,
            horizon=horizon,
            benchmark=benchmark,
            cp1_ref=cp1_ref,
            event_type=event_type,
            aggregation=aggregation,
            outcome_basis=outcome_basis,
            member_diagnostics_basis=member_diagnostics_basis,
            benchmark_member_policy=benchmark_member_policy,
            policy_ref=policy_ref,
        )
        if claim is None:
            rejected.append(
                {
                    "candidate_ref": _candidate_id(card) or "unknown_candidate",
                    "reason": "direction_unadmissible_or_missing_candidate_identity",
                }
            )
            continue
        admitted.append(claim)
    return {"admitted_claims": admitted, "rejected_candidates": rejected}


def run(config: Dict[str, Any], run_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        artifact_path = config.get("calculator_artifact") or config.get("forecast_cards") or config.get("forecast_cards_path")
        if not artifact_path:
            raise ValueError("calculator_artifact path is required")
        policy_path = config.get("policy")
        policy = _load_policy(str(policy_path)) if policy_path else {}

        horizon = _as_text(config.get("horizon") or policy.get("horizon") or "5d")
        benchmark = _as_text(config.get("benchmark") or policy.get("benchmark") or "SPY")
        cp1_ref = _as_text(config.get("cp1_ref") or policy.get("cp1_ref") or "cp1:finance_forecast_admission")
        event_type = _as_text(config.get("event_type") or policy.get("event_type") or DEFAULT_EVENT_TYPE)
        aggregation = _as_text(config.get("aggregation") or policy.get("aggregation") or DEFAULT_AGGREGATION)
        outcome_basis = _as_text(config.get("outcome_basis") or policy.get("outcome_basis") or DEFAULT_OUTCOME_BASIS)
        member_diagnostics_basis = _as_text(
            config.get("member_diagnostics_basis")
            or policy.get("member_diagnostics_basis")
            or DEFAULT_MEMBER_DIAGNOSTICS_BASIS
        )
        benchmark_member_policy = _as_text(
            config.get("benchmark_member_policy")
            or policy.get("benchmark_member_policy")
            or DEFAULT_BENCHMARK_MEMBER_POLICY
        )
        if benchmark_member_policy not in SUPPORTED_BENCHMARK_MEMBER_POLICIES:
            raise ValueError(f"unsupported benchmark_member_policy: {benchmark_member_policy}")
        max_cards = int(config.get("max_cards") or policy.get("max_cards") or 10)

        payload = _read_json(Path(str(artifact_path)))
        cards = load_forecast_cards(payload)
        data = admit_cards(
            cards,
            horizon=horizon,
            benchmark=benchmark,
            cp1_ref=cp1_ref,
            max_cards=max_cards,
            event_type=event_type,
            aggregation=aggregation,
            outcome_basis=outcome_basis,
            member_diagnostics_basis=member_diagnostics_basis,
            benchmark_member_policy=benchmark_member_policy,
            policy_ref=str(policy_path) if policy_path else None,
        )
        now = feed_envelope.utc_now()
        runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), Mapping) else {}
        run_id = str(runtime.get("run_id") or (run_dir.name if run_dir else "finance_forecast_admission"))
        as_of = str(runtime.get("as_of") or now.iso)
        diagnostics = feed_envelope.new_diagnostics(
            input_rows=len(cards),
            output_rows=len(data["admitted_claims"]),
            dropped_rows=len(data["rejected_candidates"]),
            admission_policy_ref=str(policy_path) if policy_path else None,
            horizon=horizon,
            benchmark=benchmark,
            outcome_basis=outcome_basis,
            benchmark_member_policy=benchmark_member_policy,
        )
        metadata = feed_envelope.build_metadata(
            tool=TOOL_NAME,
            status="success",
            now=now,
            run_id=run_id,
            as_of=as_of,
            items_count=len(data["admitted_claims"]),
            diagnostics=diagnostics,
            data_schema_version=DATA_SCHEMA_VERSION,
            timestamp=now.iso,
        )
        data["aggregate"] = {
            "candidate_count": len(cards),
            "admitted_count": len(data["admitted_claims"]),
            "rejected_count": len(data["rejected_candidates"]),
            "horizon": horizon,
            "benchmark": benchmark,
            "event_type": event_type,
            "aggregation": aggregation,
            "outcome_basis": outcome_basis,
            "member_diagnostics_basis": member_diagnostics_basis,
            "benchmark_member_policy": benchmark_member_policy,
        }
        return {"metadata": metadata, "data": data}
    except Exception as exc:
        return _failure_envelope(str(exc), run_dir=run_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Admit calculator forecast candidates into CP1-bound finance claims.")
    parser.add_argument("--calculator-artifact", required=True, help="Calculator artifact with candidate_forecast_cards.")
    parser.add_argument("--policy", help="Optional CP1 finance admission policy JSON.")
    parser.add_argument("--horizon", default="5d", help="Horizon label such as 5d or 20d.")
    parser.add_argument("--benchmark", default="SPY", help="Benchmark id for relative-return event binding.")
    parser.add_argument("--cp1-ref", default="cp1:finance_forecast_admission", help="CP1 policy/commitment reference.")
    parser.add_argument(
        "--outcome-basis",
        default=DEFAULT_OUTCOME_BASIS,
        choices=["equal_weight_group_return_direction", "mean_member_binary_hit"],
        help="Claim-level event outcome basis.",
    )
    parser.add_argument(
        "--benchmark-member-policy",
        default=DEFAULT_BENCHMARK_MEMBER_POLICY,
        choices=sorted(SUPPORTED_BENCHMARK_MEMBER_POLICIES),
        help="Policy when benchmark id also appears as a claim member.",
    )
    parser.add_argument("--max-cards", type=int, default=10, help="Maximum candidates to admit.")
    parser.add_argument("--json", action="store_true", help="Print JSON envelope.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(
        {
            "calculator_artifact": args.calculator_artifact,
            "policy": args.policy,
            "horizon": args.horizon,
            "benchmark": args.benchmark,
            "cp1_ref": args.cp1_ref,
            "outcome_basis": args.outcome_basis,
            "benchmark_member_policy": args.benchmark_member_policy,
            "max_cards": args.max_cards,
            "runtime": {"run_id": "finance_forecast_admission"},
        }
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text if args.json else text)
    return 0 if payload.get("metadata", {}).get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
