#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Produce shadow-only probability calibration candidates from
  finance forecast scorecards without changing calculator output.
- Mechanism: Read resolved train/holdout scorecards, summarize empirical
  probability bins, compare baseline and shadow-calibrated Brier on holdout
  when available, and emit a versioned calibrator artifact that remains gated
  until holdout improvement is proven.

[INTERFACE]
- Reads: one or more finance_eval_replay or finance_historical_replay envelopes.
- Returns/prints: `finance_probability_calibrator.1` ArtifactEnvelope.

[CONSTRAINTS]
- Shadow-only: never rewrites forecast cards, claims, calculator weights, or
  live probability mappings.
- In-sample improvement is diagnostic only, never an acceptance receipt.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from system.lib import feed_envelope

TOOL_NAME = "finance_probability_calibrator"
DATA_SCHEMA_VERSION = "finance_probability_calibrator.1"
SUPPORTED_METHODS = {"isotonic", "sigmoid", "isotonic_or_sigmoid"}


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


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


def _scorecards_from_payload(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), Mapping) else {}
    raw = data.get("scorecards") if isinstance(data, Mapping) else None
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, Mapping)]
    ledger_cards = _nested(data, "experiment_ledger", "scorecards")
    if isinstance(ledger_cards, list):
        return [dict(item) for item in ledger_cards if isinstance(item, Mapping)]
    return []


def load_scorecards(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for path in paths:
        cards.extend(_scorecards_from_payload(_read_json(path)))
    return cards


def _scorecard_paths(value: Any) -> List[Path]:
    if isinstance(value, str):
        return [Path(path.strip()) for path in value.split(",") if path.strip()]
    if isinstance(value, list):
        return [Path(str(path)) for path in value if _as_text(path)]
    return []


def _stable_digest(*parts: Any, length: int = 16) -> str:
    text = "|".join(_as_text(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _probability_bin(probability: float) -> str:
    low = min(0.9, max(0.0, int(probability * 10) / 10))
    high = min(1.0, low + 0.1)
    return f"{low:.1f}-{high:.1f}"


def _observations(scorecards: Sequence[Mapping[str, Any]]) -> List[Dict[str, float]]:
    resolved = [card for card in scorecards if card.get("status") == "resolved"]
    observations: List[Dict[str, float]] = []
    for card in resolved:
        probability = _float(_nested(card, "proper_score", "directional_hit_probability"))
        outcome = _float(_nested(card, "proper_score", "event_outcome"))
        if probability is None or outcome is None:
            continue
        observations.append({"probability": probability, "outcome": outcome})
    return observations


def _calibration_points(observations: Sequence[Mapping[str, float]]) -> tuple[List[Dict[str, Any]], Dict[str, float]]:
    bins: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    for row in observations:
        bins[_probability_bin(row["probability"])].append(row)

    calibration_points: List[Dict[str, Any]] = []
    bin_rates: Dict[str, float] = {}
    for label in sorted(bins):
        rows = bins[label]
        mean_probability = sum(row["probability"] for row in rows) / len(rows)
        observed_rate = sum(row["outcome"] for row in rows) / len(rows)
        bin_rates[label] = observed_rate
        calibration_points.append(
            {
                "probability_bin": label,
                "forecast_count": len(rows),
                "mean_probability": round(mean_probability, 6),
                "observed_event_rate": round(observed_rate, 6),
            }
        )
    return calibration_points, bin_rates


def _mean_brier(observations: Sequence[Mapping[str, float]], bin_rates: Optional[Mapping[str, float]] = None) -> Optional[float]:
    if not observations:
        return None
    terms = []
    for row in observations:
        probability = float(row["probability"])
        if bin_rates is not None:
            probability = float(bin_rates.get(_probability_bin(probability), probability))
        terms.append((probability - float(row["outcome"])) ** 2)
    return sum(terms) / len(terms)


def _window_summary(scorecards: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    starts = []
    ends = []
    for card in scorecards:
        event_contract = card.get("event_contract") if isinstance(card.get("event_contract"), Mapping) else {}
        if _as_text(event_contract.get("event_start")):
            starts.append(_as_text(event_contract.get("event_start")))
        if _as_text(event_contract.get("event_end")):
            ends.append(_as_text(event_contract.get("event_end")))
    return {
        "event_start_min": min(starts) if starts else None,
        "event_end_max": max(ends) if ends else None,
        "scorecard_count": len(scorecards),
    }


def build_calibrator(
    train_scorecards: Sequence[Mapping[str, Any]],
    *,
    method: str,
    holdout_policy: str,
    min_resolved: int = 30,
    holdout_scorecards: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    if method not in SUPPORTED_METHODS:
        raise ValueError(f"unsupported calibration method: {method}")
    train_observations = _observations(train_scorecards)
    eval_scorecards = list(holdout_scorecards) if holdout_scorecards is not None else list(train_scorecards)
    eval_observations = _observations(eval_scorecards)
    in_sample_only = holdout_scorecards is None

    calibration_points, bin_rates = _calibration_points(train_observations)

    baseline_brier = _mean_brier(eval_observations)
    calibrated_brier = _mean_brier(eval_observations, bin_rates)
    holdout_brier_improved = (
        None
        if in_sample_only or baseline_brier is None or calibrated_brier is None
        else bool(calibrated_brier < baseline_brier)
    )
    minimum_resolved_met = len(eval_observations) >= min_resolved
    calibrator_id = "fin_cal_" + _stable_digest(
        method,
        holdout_policy,
        len(train_observations),
        len(eval_observations),
        baseline_brier,
        calibrated_brier,
    )
    if in_sample_only:
        reason = "in_sample_diagnostic_only"
    elif not minimum_resolved_met:
        reason = "insufficient_holdout"
    elif holdout_brier_improved:
        reason = "holdout_improvement_observed_shadow_only"
    else:
        reason = "requires_holdout_improvement"

    return {
        "schema_version": "finance_probability_calibrator_v0",
        "calibrator_id": calibrator_id,
        "method": method,
        "training_window": _window_summary(train_scorecards),
        "holdout_window": _window_summary(eval_scorecards),
        "holdout_policy": holdout_policy,
        "input_probability_field": "directional_hit_probability",
        "output_probability_field": "calibrated_directional_hit_probability",
        "status": "shadow_only",
        "training_resolved_observation_count": len(train_observations),
        "holdout_resolved_observation_count": len(eval_observations) if not in_sample_only else 0,
        "resolved_observation_count": len(eval_observations),
        "calibration_points": calibration_points,
        "diagnostics": {
            "baseline_brier": round(baseline_brier, 6) if baseline_brier is not None else None,
            "shadow_calibrated_brier": round(calibrated_brier, 6) if calibrated_brier is not None else None,
            "in_sample_only": in_sample_only,
            "train_observation_count": len(train_observations),
            "holdout_observation_count": len(eval_observations) if not in_sample_only else 0,
        },
        "admission_decision": {
            "accepted": False,
            "reason": reason,
            "holdout_brier_improved": holdout_brier_improved,
            "reliability_improved": None,
            "minimum_resolved_met": minimum_resolved_met,
            "live_probability_mutation_allowed": False,
        },
    }


def run(config: Dict[str, Any], run_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        scorecard_paths = _scorecard_paths(config.get("scorecards"))
        train_paths = _scorecard_paths(config.get("train_scorecards"))
        holdout_paths = _scorecard_paths(config.get("holdout_scorecards"))
        if not scorecard_paths and not train_paths:
            raise ValueError("scorecards or train_scorecards path is required")
        method = _as_text(config.get("method") or "isotonic")
        holdout_policy = _as_text(config.get("holdout_policy") or "prequential")
        min_resolved = int(config.get("min_resolved") or 30)
        train_scorecards = load_scorecards(train_paths or scorecard_paths)
        holdout_scorecards = load_scorecards(holdout_paths) if holdout_paths else None
        calibrator = build_calibrator(
            train_scorecards,
            method=method,
            holdout_policy=holdout_policy,
            min_resolved=min_resolved,
            holdout_scorecards=holdout_scorecards,
        )
        now = feed_envelope.utc_now()
        runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), Mapping) else {}
        run_id = _as_text(runtime.get("run_id") or calibrator["calibrator_id"])
        as_of = _as_text(runtime.get("as_of") or now.iso)
        diagnostics = feed_envelope.new_diagnostics(
            input_rows=len(train_scorecards) + (len(holdout_scorecards) if holdout_scorecards is not None else 0),
            output_rows=1,
            dropped_rows=0,
            holdout_policy=holdout_policy,
            shadow_only=True,
            in_sample_only=calibrator["diagnostics"]["in_sample_only"],
        )
        metadata = feed_envelope.build_metadata(
            tool=TOOL_NAME,
            status="success",
            now=now,
            run_id=run_id,
            as_of=as_of,
            items_count=1,
            diagnostics=diagnostics,
            data_schema_version=DATA_SCHEMA_VERSION,
            timestamp=now.iso,
        )
        return {"metadata": metadata, "data": {"calibrator": calibrator}}
    except Exception as exc:
        return _failure_envelope(str(exc), run_dir=run_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shadow-only finance probability calibrator artifact.")
    parser.add_argument("--scorecards", action="append", help="finance_eval_replay or historical_replay envelope.")
    parser.add_argument("--train-scorecards", action="append", help="Training scorecard envelope for holdout-aware calibration.")
    parser.add_argument("--holdout-scorecards", action="append", help="Holdout scorecard envelope for shadow gate evaluation.")
    parser.add_argument("--method", default="isotonic", choices=sorted(SUPPORTED_METHODS))
    parser.add_argument("--holdout-policy", default="prequential")
    parser.add_argument("--min-resolved", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Print JSON envelope.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(
        {
            "scorecards": args.scorecards,
            "train_scorecards": args.train_scorecards,
            "holdout_scorecards": args.holdout_scorecards,
            "method": args.method,
            "holdout_policy": args.holdout_policy,
            "min_resolved": args.min_resolved,
            "runtime": {"run_id": TOOL_NAME},
        }
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text if args.json else text)
    return 0 if payload.get("metadata", {}).get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
