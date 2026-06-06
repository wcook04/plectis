#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Evaluate calculator forecast-generator variants over a historical,
  leakage-aware sequence without mutating calculator weights or probabilities.
- Mechanism: Replay archived calculator artifacts through CP1 admission,
  deterministic truth resolution, and `eval_replay.py`, then fold scorecards into
  a finance-evaluation experiment ledger.

[INTERFACE]
- Reads: one or more calculator artifacts with candidate_forecast_cards.
- Reads: deterministic price-history artifact.
- Returns/prints: `finance_historical_replay.1` ArtifactEnvelope.

[CONSTRAINTS]
- Evaluation only; no optimizer/GEPA or live probability mutation.
- Supported split policies must emit executable membership evidence, not random k-fold.
- Intermediate artifacts are written under run_dir/artifacts for auditability.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import glob
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from system.lib import feed_envelope
from tools.finance import admit_forecasts, eval_replay, resolve_forecasts, variant_registry

TOOL_NAME = "finance_historical_replay"
DATA_SCHEMA_VERSION = "finance_historical_replay.1"

SUPPORTED_SPLIT_POLICIES = {"prequential", "walk_forward_shadow", "purged_holdout"}
DEFAULT_SPLIT_POLICY = "prequential"
STATUS_UNKNOWN_VARIANT = "not_admissible_unknown_variant"


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _coerce_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [_as_text(item) for item in value if _as_text(item)]
    text = _as_text(value)
    if not text:
        return []
    return [_as_text(item) for item in text.split(",") if _as_text(item)]


def _expand_artifacts(values: Sequence[str]) -> List[Path]:
    paths: List[Path] = []
    for value in values:
        if any(token in value for token in ("*", "?", "[")):
            paths.extend(Path(path) for path in sorted(glob.glob(value)))
        else:
            paths.append(Path(value))
    unique: Dict[str, Path] = {}
    for path in paths:
        unique[str(path)] = path
    return list(unique.values())


def _horizons(value: Any) -> List[str]:
    horizons = _coerce_list(value)
    return horizons or ["5d"]


def _horizon_days(horizon: str) -> int:
    text = _as_text(horizon).lower()
    if not text.endswith("d"):
        return 0
    try:
        return max(int(text[:-1]), 0)
    except ValueError:
        return 0


def _stable_digest(*parts: Any, length: int = 16) -> str:
    text = "|".join(_as_text(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _parse_dt(value: Any) -> Optional[datetime]:
    text = _as_text(value)
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _dt_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _event_contract(card: Mapping[str, Any]) -> Dict[str, Any]:
    contract = card.get("event_contract") if isinstance(card.get("event_contract"), Mapping) else {}
    return dict(contract)


def _card_subject_as_of(card: Mapping[str, Any]) -> Optional[datetime]:
    contract = _event_contract(card)
    return _parse_dt(contract.get("subject_as_of") or contract.get("event_start"))


def _card_event_start(card: Mapping[str, Any]) -> Optional[datetime]:
    return _parse_dt(_event_contract(card).get("event_start"))


def _card_event_end(card: Mapping[str, Any]) -> Optional[datetime]:
    return _parse_dt(_event_contract(card).get("event_end"))


def _card_key(card: Mapping[str, Any]) -> str:
    contract = _event_contract(card)
    return "|".join(
        _as_text(part)
        for part in [
            card.get("forecast_id") or card.get("candidate_ref"),
            contract.get("event_start"),
            contract.get("event_end"),
            contract.get("horizon"),
            contract.get("benchmark"),
            contract.get("event_type"),
            contract.get("outcome_basis"),
            contract.get("benchmark_member_policy"),
        ]
    )


def _card_comparison_event_key(card: Mapping[str, Any]) -> str:
    contract = _event_contract(card)
    return _as_text(card.get("comparison_event_key") or contract.get("comparison_event_key"))


def _split_membership_counts(rows: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        split = _as_text(row.get("split") or "unknown")
        counts[split] = counts.get(split, 0) + 1
    return dict(sorted(counts.items()))


def _split_row(
    card: Mapping[str, Any],
    split: str,
    *,
    reason: str,
    split_policy: str,
    embargo_days: int,
    training_available_count: int = 0,
) -> Dict[str, Any]:
    contract = _event_contract(card)
    event_end = _card_event_end(card)
    embargo_until = event_end + timedelta(days=embargo_days) if event_end is not None and embargo_days > 0 else None
    usable = split not in {"purged", "embargoed"}
    return {
        "forecast_id": _as_text(card.get("forecast_id")),
        "candidate_ref": _as_text(card.get("candidate_ref")),
        "comparison_event_key": _card_comparison_event_key(card),
        "event_key": _card_key(card),
        "split": split,
        "split_policy": split_policy,
        "reason": reason,
        "training_available_count": int(training_available_count),
        "usable_for_variant_comparison": usable,
        "usable_for_calibration": usable,
        "subject_as_of": contract.get("subject_as_of"),
        "event_start": contract.get("event_start"),
        "event_end": contract.get("event_end"),
        "embargo_until": _dt_iso(embargo_until),
        "horizon": contract.get("horizon"),
        "benchmark": contract.get("benchmark"),
        "outcome_basis": contract.get("outcome_basis"),
    }


def _split_membership_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "split": _as_text(row.get("split") or "unknown"),
        "split_policy": _as_text(row.get("split_policy")),
        "reason": _as_text(row.get("reason")),
        "usable_for_variant_comparison": bool(row.get("usable_for_variant_comparison")),
        "usable_for_calibration": bool(row.get("usable_for_calibration")),
        "comparison_event_key": _as_text(row.get("comparison_event_key")),
        "event_start": row.get("event_start"),
        "event_end": row.get("event_end"),
        "embargo_until": row.get("embargo_until"),
    }


def _annotate_scorecards_with_split_membership(
    scorecards: Sequence[Dict[str, Any]],
    split_membership: Mapping[str, Any],
) -> None:
    rows = split_membership.get("rows") if isinstance(split_membership.get("rows"), list) else []
    by_key: Dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        comparison_key = _as_text(row.get("comparison_event_key"))
        legacy_key = _as_text(row.get("event_key"))
        if comparison_key:
            by_key[comparison_key] = row
        if legacy_key:
            by_key.setdefault(legacy_key, row)
    for card in scorecards:
        row = by_key.get(_card_comparison_event_key(card)) or by_key.get(_card_key(card))
        if row:
            card["split_membership"] = _split_membership_payload(row)


def plan_split_membership(
    scorecards: Sequence[Mapping[str, Any]],
    *,
    split_policy: str,
    embargo_days: int,
) -> Dict[str, Any]:
    ordered = sorted(
        [card for card in scorecards if isinstance(card, Mapping)],
        key=lambda card: (
            _card_subject_as_of(card) or datetime.min.replace(tzinfo=timezone.utc),
            _card_key(card),
        ),
    )
    if not ordered:
        return {"executable": True, "rows": [], "counts": {}, "purged_count": 0}

    if split_policy == "prequential":
        rows: List[Dict[str, Any]] = []
        for card in ordered:
            subject_as_of = _card_subject_as_of(card)
            available = 0
            if subject_as_of is not None:
                for prior in ordered:
                    if prior is card:
                        break
                    prior_end = _card_event_end(prior)
                    if prior_end is not None and prior_end + timedelta(days=embargo_days) <= subject_as_of:
                        available += 1
            rows.append(
                _split_row(
                    card,
                    "evaluation",
                    reason="prequential_subject_order_no_future_training",
                    split_policy=split_policy,
                    embargo_days=embargo_days,
                    training_available_count=available,
                )
            )
        return {
            "executable": True,
            "rows": rows,
            "counts": _split_membership_counts(rows),
            "purged_count": 0,
        }

    if split_policy == "walk_forward_shadow":
        n = len(ordered)
        train_cut = max(1, n // 2) if n > 1 else 0
        validation_cut = max(train_cut, int(n * 0.75)) if n > 2 else train_cut
        rows = []
        for index, card in enumerate(ordered):
            if index < train_cut:
                split = "train"
            elif index < validation_cut:
                split = "validation"
            else:
                split = "holdout"
            rows.append(
                _split_row(
                    card,
                    split,
                    reason="walk_forward_shadow_chronological_membership",
                    split_policy=split_policy,
                    embargo_days=embargo_days,
                    training_available_count=max(index, 0),
                )
            )
        return {
            "executable": True,
            "rows": rows,
            "counts": _split_membership_counts(rows),
            "purged_count": 0,
        }

    # purged_holdout
    holdout_count = max(1, len(ordered) // 5)
    holdout = ordered[-holdout_count:]
    train_candidates = ordered[:-holdout_count]
    holdout_start_candidates = [_card_event_start(card) for card in holdout]
    holdout_start = min([dt for dt in holdout_start_candidates if dt is not None], default=None)
    rows = []
    purged_count = 0
    for card in train_candidates:
        event_end = _card_event_end(card)
        if holdout_start is not None and event_end is not None and event_end + timedelta(days=embargo_days) > holdout_start:
            split = "purged"
            purged_count += 1
            reason = "event_window_or_embargo_overlaps_holdout_boundary"
        else:
            split = "train"
            reason = "purged_holdout_train_before_embargo_boundary"
        rows.append(_split_row(card, split, reason=reason, split_policy=split_policy, embargo_days=embargo_days))
    for card in holdout:
        rows.append(
            _split_row(
                card,
                "holdout",
                reason="purged_holdout_chronological_holdout",
                split_policy=split_policy,
                embargo_days=embargo_days,
            )
        )
    return {
        "executable": True,
        "rows": rows,
        "counts": _split_membership_counts(rows),
        "purged_count": purged_count,
        "holdout_start": _dt_iso(holdout_start),
    }


def _scorecards_from_replay(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), Mapping) else {}
    raw = data.get("scorecards") if isinstance(data, Mapping) else None
    return [dict(item) for item in raw] if isinstance(raw, list) else []


def _count_admitted(payload: Mapping[str, Any]) -> int:
    data = payload.get("data") if isinstance(payload.get("data"), Mapping) else {}
    raw = data.get("admitted_claims") if isinstance(data, Mapping) else None
    return len(raw) if isinstance(raw, list) else 0


def _count_candidates(path: Path) -> int:
    payload = _read_json(path)
    return len(eval_replay.load_forecast_cards(payload))


def _artifact_with_variant(path: Path, variant_id: str, experiment_dir: Path, suffix: str) -> Path:
    payload = deepcopy(_read_json(path))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if isinstance(data, dict):
        cards = data.get("candidate_forecast_cards")
        if isinstance(cards, list):
            for card in cards:
                if not isinstance(card, dict):
                    continue
                identity = card.setdefault("identity", {})
                if isinstance(identity, dict):
                    identity["generator_variant_id"] = variant_id
    if variant_id == variant_registry.BASELINE_VARIANT_ID:
        return path
    out = experiment_dir / f"variant_input_{suffix}.json"
    _write_json(out, payload)
    return out


def _resolution_status_counts(payloads: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for payload in payloads:
        summary = payload.get("data", {}).get("summary", {}) if isinstance(payload.get("data"), Mapping) else {}
        status_counts = summary.get("status_counts") if isinstance(summary, Mapping) else None
        if isinstance(status_counts, Mapping):
            for key, value in status_counts.items():
                counts[_as_text(key)] = counts.get(_as_text(key), 0) + int(value)
    return dict(sorted(counts.items()))


def _resolution_summary_counts(payloads: Iterable[Mapping[str, Any]], field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for payload in payloads:
        summary = payload.get("data", {}).get("summary", {}) if isinstance(payload.get("data"), Mapping) else {}
        field_counts = summary.get(field) if isinstance(summary, Mapping) else None
        if isinstance(field_counts, Mapping):
            for key, value in field_counts.items():
                counts[_as_text(key)] = counts.get(_as_text(key), 0) + int(value)
    return dict(sorted(counts.items()))


def run_experiment(config: Mapping[str, Any], *, run_dir: Path) -> Dict[str, Any]:
    calculator_artifacts = _expand_artifacts(_coerce_list(config.get("calculator_artifacts") or config.get("calculator_artifact")))
    if not calculator_artifacts:
        raise ValueError("calculator_artifacts is required")
    price_history = _as_text(config.get("price_history"))
    if not price_history:
        raise ValueError("price_history path is required")

    split_policy = _as_text(config.get("split_policy") or DEFAULT_SPLIT_POLICY)
    if split_policy not in SUPPORTED_SPLIT_POLICIES:
        raise ValueError(f"unsupported split_policy: {split_policy}")
    horizons = _horizons(config.get("horizons") or config.get("horizon"))
    benchmark = _as_text(config.get("benchmark") or "SPY")
    max_cards = int(config.get("max_cards") or 10)
    minimum_coverage = float(config.get("minimum_coverage", eval_replay.DEFAULT_MINIMUM_COVERAGE))
    outcome_basis = _as_text(config.get("outcome_basis") or admit_forecasts.DEFAULT_OUTCOME_BASIS)
    benchmark_member_policy = _as_text(
        config.get("benchmark_member_policy") or admit_forecasts.DEFAULT_BENCHMARK_MEMBER_POLICY
    )
    variant_id = _as_text(config.get("variant_id") or config.get("generator_variant_id") or variant_registry.BASELINE_VARIANT_ID)
    try:
        variant_row = variant_registry.assert_variant_known(variant_id)
    except KeyError as exc:
        raise ValueError(f"{STATUS_UNKNOWN_VARIANT}: {variant_id}") from exc
    runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), Mapping) else {}
    truth_as_of = _as_text(config.get("truth_as_of") or config.get("as_of") or runtime.get("as_of") or feed_envelope.utc_now().iso)
    date_match_policy = _as_text(config.get("date_match_policy") or resolve_forecasts.DEFAULT_DATE_MATCH_POLICY)
    max_roll_days = int(config.get("max_roll_days") or resolve_forecasts.DEFAULT_MAX_ROLL_DAYS)
    experiment_id = _as_text(config.get("experiment_id")) or "fin_hist_" + _stable_digest(
        ",".join(str(path) for path in calculator_artifacts),
        price_history,
        ",".join(horizons),
        benchmark,
        split_policy,
        variant_id,
        truth_as_of,
        date_match_policy,
        str(max_roll_days),
    )
    experiment_dir = run_dir / "artifacts" / "finance_eval" / "historical_replay" / experiment_id

    scorecards: List[Dict[str, Any]] = []
    admission_payloads: List[Dict[str, Any]] = []
    resolution_payloads: List[Dict[str, Any]] = []
    replay_payloads: List[Dict[str, Any]] = []
    intermediate_refs: List[Dict[str, str]] = []
    candidate_count = sum(_count_candidates(path) for path in calculator_artifacts)

    for artifact_index, artifact_path in enumerate(calculator_artifacts):
        for horizon in horizons:
            suffix = f"{artifact_index}_{horizon}"
            variant_artifact_path = _artifact_with_variant(artifact_path, variant_id, experiment_dir, suffix)
            admitted = admit_forecasts.run(
                {
                    "calculator_artifact": str(variant_artifact_path),
                    "horizon": horizon,
                    "benchmark": benchmark,
                    "cp1_ref": f"cp1:historical_replay:{experiment_id}",
                    "outcome_basis": outcome_basis,
                    "benchmark_member_policy": benchmark_member_policy,
                    "max_cards": max_cards,
                    "runtime": {"run_id": f"{experiment_id}:admit:{suffix}", "as_of": truth_as_of},
                },
                run_dir=experiment_dir,
            )
            admitted_path = experiment_dir / f"admitted_{suffix}.json"
            _write_json(admitted_path, admitted)
            admission_payloads.append(admitted)

            resolved = resolve_forecasts.run(
                {
                    "admitted_claims": str(admitted_path),
                    "price_history": price_history,
                    "as_of": truth_as_of,
                    "date_match_policy": date_match_policy,
                    "max_roll_days": max_roll_days,
                    "runtime": {"run_id": f"{experiment_id}:resolve:{suffix}", "as_of": truth_as_of},
                },
                run_dir=experiment_dir,
            )
            resolved_path = experiment_dir / f"resolved_{suffix}.json"
            _write_json(resolved_path, resolved)
            resolution_payloads.append(resolved)

            replay = eval_replay.run(
                {
                    "forecast_cards": str(admitted_path),
                    "prediction_reconciliation": str(resolved_path),
                    "horizon": horizon,
                    "minimum_coverage": minimum_coverage,
                    "mode": eval_replay.MODE_CP1_ADMITTED_ONLY,
                    "runtime": {"run_id": f"{experiment_id}:replay:{suffix}", "as_of": truth_as_of},
                },
                run_dir=experiment_dir,
            )
            replay_path = experiment_dir / f"replay_{suffix}.json"
            _write_json(replay_path, replay)
            replay_payloads.append(replay)
            scorecards.extend(_scorecards_from_replay(replay))
            intermediate_refs.append(
                {
                    "calculator_artifact": str(artifact_path),
                    "variant_input_artifact": str(variant_artifact_path),
                    "admitted_claims": str(admitted_path),
                    "resolution": str(resolved_path),
                    "replay": str(replay_path),
                    "horizon": horizon,
                }
            )

    calibration = eval_replay.calibration_summary(scorecards)
    generator_variants = eval_replay.generator_variant_summary(scorecards)
    resolved_count = int(calibration["resolved_count"])
    excluded_count = sum(1 for card in scorecards if str(card.get("status", "")).startswith(("excluded", "not_admissible")))
    pending_count = sum(1 for card in scorecards if card.get("status") in {"pending_truth", "matured_truth_missing"})
    admitted_count = sum(_count_admitted(payload) for payload in admission_payloads)
    matured_count = sum(
        1
        for card in scorecards
        if card.get("status") not in {"pending_truth", "not_admissible_missing_event_binding"}
    )
    embargo_days = int(config.get("embargo_days") or max((_horizon_days(horizon) for horizon in horizons), default=0))
    split_membership = plan_split_membership(scorecards, split_policy=split_policy, embargo_days=embargo_days)
    _annotate_scorecards_with_split_membership(scorecards, split_membership)

    return {
        "experiment_ledger": {
            "schema_version": "finance_eval_experiment_ledger_v0",
            "experiment_id": experiment_id,
            "generator_variant_id": variant_id,
            "calibrator_variant_id": None,
            "variant_registry_ref": variant_registry.REGISTRY_REF,
            "variant_known": True,
            "variant_status": variant_row.get("status", "unknown"),
            "truth_resolution_policy": {
                "resolver_ref": "tools/finance/resolve_forecasts.py",
                "date_match_policy": date_match_policy,
                "max_roll_days": max_roll_days,
                "deterministic_local_truth_only": True,
                "match_reason_authority": "tools/finance/resolve_forecasts.py",
            },
            "split_policy": {
                "kind": split_policy,
                "embargo_days": embargo_days,
                "horizon_groups": horizons,
                "random_kfold_allowed": False,
                "executable": bool(split_membership.get("executable")),
                "split_membership_counts": split_membership.get("counts", {}),
                "purged_count": split_membership.get("purged_count", 0),
                "data_snooping_guard": "registry_bound_paired_comparison_required_before_mutation",
            },
            "claim_counts": {
                "candidate": candidate_count,
                "admitted": admitted_count,
                "matured": matured_count,
                "resolved": resolved_count,
                "pending": pending_count,
                "excluded": excluded_count,
            },
            "scores": {
                "mean_brier": calibration["mean_brier"],
                "brier_skill_vs_base_rate": calibration["brier_skill_vs_base_rate"],
                "reliability": calibration["decomposition"]["reliability"],
                "resolution": calibration["decomposition"]["resolution"],
                "uncertainty": calibration["decomposition"]["uncertainty"],
            },
            "calibration": {
                "bins": calibration["bins"],
                "calibrator_admitted": False,
                "calibrator_reason": "calibrator_not_run_in_historical_replay",
            },
            "variant_decision": {
                "status": "accepted_for_shadow_only",
                "optimizer_permission": False,
                "calculator_mutation_permission": False,
                "reason": "historical replay evaluates variants only; no calculator mutation permission emitted",
                "mutation_gate": variant_registry.mutation_gate_for(variant_id),
            },
        },
        "scorecards": scorecards,
        "split_membership": split_membership,
        "calibration_summary": calibration,
        "generator_variants": generator_variants,
        "resolution_status_counts": _resolution_status_counts(resolution_payloads),
        "price_match_status_counts": _resolution_summary_counts(resolution_payloads, "price_match_status_counts"),
        "price_match_reason_counts": _resolution_summary_counts(resolution_payloads, "price_match_reason_counts"),
        "intermediate_artifacts": intermediate_refs,
    }


def run(config: Dict[str, Any], run_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        root = Path(run_dir) if run_dir else Path(".")
        data = run_experiment(config, run_dir=root)
        now = feed_envelope.utc_now()
        runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), Mapping) else {}
        run_id = _as_text(runtime.get("run_id") or data["experiment_ledger"]["experiment_id"])
        as_of = _as_text(runtime.get("as_of") or config.get("truth_as_of") or config.get("as_of") or now.iso)
        diagnostics = feed_envelope.new_diagnostics(
            input_rows=len(_coerce_list(config.get("calculator_artifacts") or config.get("calculator_artifact"))),
            output_rows=len(data["scorecards"]),
            dropped_rows=0,
            split_policy=data["experiment_ledger"]["split_policy"],
            variant_decision=data["experiment_ledger"]["variant_decision"],
            variant_registry_ref=data["experiment_ledger"].get("variant_registry_ref"),
            variant_known=data["experiment_ledger"].get("variant_known"),
            truth_resolution_policy=data["experiment_ledger"].get("truth_resolution_policy"),
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
    parser = argparse.ArgumentParser(description="Run finance forecast historical replay without optimizer mutation.")
    parser.add_argument("--calculator-artifacts", action="append", required=True, help="Calculator artifact path/glob. Repeatable.")
    parser.add_argument("--price-history", required=True, help="Local price-history artifact.")
    parser.add_argument("--horizons", default="5d", help="Comma-separated horizons such as 5d,20d.")
    parser.add_argument("--benchmark", default="SPY", help="Benchmark id for admission.")
    parser.add_argument("--variant-id", default=variant_registry.BASELINE_VARIANT_ID, help="Registered generator variant id.")
    parser.add_argument("--split-policy", default=DEFAULT_SPLIT_POLICY, choices=sorted(SUPPORTED_SPLIT_POLICIES))
    parser.add_argument("--embargo-days", type=int, help="Explicit embargo-days metadata.")
    parser.add_argument("--max-cards", type=int, default=10)
    parser.add_argument("--minimum-coverage", type=float, default=eval_replay.DEFAULT_MINIMUM_COVERAGE)
    parser.add_argument("--truth-as-of", required=True, help="Truth materialization timestamp.")
    parser.add_argument("--benchmark-member-policy", default=admit_forecasts.DEFAULT_BENCHMARK_MEMBER_POLICY)
    parser.add_argument(
        "--date-match-policy",
        default=resolve_forecasts.DEFAULT_DATE_MATCH_POLICY,
        choices=sorted(resolve_forecasts.SUPPORTED_DATE_MATCH_POLICIES),
    )
    parser.add_argument("--max-roll-days", type=int, default=resolve_forecasts.DEFAULT_MAX_ROLL_DAYS)
    parser.add_argument("--json", action="store_true", help="Print JSON envelope.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(
        {
            "calculator_artifacts": args.calculator_artifacts,
            "price_history": args.price_history,
            "horizons": args.horizons,
            "benchmark": args.benchmark,
            "variant_id": args.variant_id,
            "split_policy": args.split_policy,
            "embargo_days": args.embargo_days,
            "max_cards": args.max_cards,
            "minimum_coverage": args.minimum_coverage,
            "truth_as_of": args.truth_as_of,
            "benchmark_member_policy": args.benchmark_member_policy,
            "date_match_policy": args.date_match_policy,
            "max_roll_days": args.max_roll_days,
            "runtime": {"run_id": TOOL_NAME, "as_of": args.truth_as_of},
        }
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text if args.json else text)
    return 0 if payload.get("metadata", {}).get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
