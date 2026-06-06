#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Turn the operator's "obvious structural logic" finance idea into a
  governed, NON-ADVISORY research family layered on the existing CP1/CP2 forecast
  evaluation spine. The product is NOT "find obvious high-return things"; it is
  "admit timestamped claims that looked structurally obvious AT THE TIME, resolve
  them forward, and learn which reasoning families survive denominator-aware
  replay." The load-bearing inversion: "obvious" is a CP1 claim-status, never a
  label on outcomes. The corpus must store theses that looked obvious at the time
  INCLUDING the ones that failed; "obvious-in-hindsight" is a smell flag, never
  the sampling rule.
- Mechanism: Map each `structural_thesis_card_v0` onto the existing
  `forecast_claim_card_v0` shape, then drive the real CP1 admission
  (admit_forecasts), CP2 truth resolution (resolve_forecasts), proper-scoring
  replay (eval_replay), and purged/walk-forward historical replay
  (historical_replay) with deterministic public-fixture prices. No new evaluator
  is built; the long-horizon (month/year) adapter is the only new machinery.

[INTERFACE]
- Reads: structural_thesis_card_v0 dicts + a deterministic public-fixture price
  history (no live provider).
- Returns: `structural_thesis_research_family_v0` surface with per-thesis CP1/CP2
  results, family memory, purged-replay discipline, and a non-advisory forward
  lens. `validate_structural_thesis_family` returns findings (empty == valid).

[CONSTRAINTS]
- CP1 forward-only: source_evidence_as_of <= as_of (leakage guard). A thesis that
  changes meaning after the result is known is a rejected post-hoc mutation.
- A LOSER (claim refuted forward) and a NEGATIVE CONTROL are valid, required
  evidence; treating them as tooling failure is forbidden.
- Output language is restricted to: awaiting_evidence, insufficient_evidence,
  candidate_set, review_candidate, rejected, blocked_authority_overclaim.
- No financial advice, no investment recommendation, no winner language, no
  performance claim, no live provider calls, no portfolio action. A
  review_candidate is a human-review flag, never a tradable winner.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from tools.finance import admit_forecasts, eval_replay, historical_replay, resolve_forecasts

STRUCTURAL_THESIS_CARD_SCHEMA = "structural_thesis_card_v0"
STRUCTURAL_THESIS_FAMILY_SCHEMA = "structural_thesis_research_family_v0"

# CP1-admissible research output vocabulary, inherited from the quant research
# experiment spine. A tradable "winner" is deliberately absent.
ALLOWED_OUTPUT_STATES = {
    "awaiting_evidence",
    "insufficient_evidence",
    "candidate_set",
    "review_candidate",
    "rejected",
    "blocked_authority_overclaim",
}
CONTROL_ROLES = {
    "negative_control_structural_shuffle",
    "negative_control_temporal_shuffle",
    "base_rate_control",
}

# Authority ceiling: every flag must stay false. Mirrors the finance eval spine.
AUTHORITY_CEILING: Dict[str, bool] = {
    "calculator_weight_mutation_authorized": False,
    "financial_advice_authorized": False,
    "forecast_performance_claim": False,
    "hosted_public_authorized": False,
    "investment_recommendation_authorized": False,
    "live_market_data_authorized": False,
    "optimizer_mutation_authorized": False,
    "performance_guarantee_claim": False,
    "portfolio_action_authorized": False,
    "private_account_state_exported": False,
    "private_portfolio_exported": False,
    "provider_calls_authorized": False,
    "provider_payload_exported": False,
    "publication_authorized": False,
    "release_authorized": False,
    "trading_advice_authorized": False,
}

# Advisory phrasings that must never appear in a non-advisory research surface.
ADVISORY_FORBIDDEN_SUBSTRINGS: Tuple[str, ...] = (
    "buy ",
    "sell ",
    "purchase ",
    "invest now",
    "invest in ",
    "you should",
    "we recommend",
    "recommended allocation",
    "guaranteed",
    "guarantee of",
    "sure thing",
    "can't lose",
    "cannot lose",
    "risk-free",
    "price target",
    "strong buy",
)

# month/year -> day mapping convention (documented + recorded per card so the
# horizon expansion is transparent). 30d/month, 365d/year.
_UNIT_DAYS = {"d": 1, "m": 30, "y": 365}


def horizon_to_days(label: str) -> int:
    """Expand a month/year/day horizon label to a positive day count.

    The existing CP1 admission only accepts ``Nd`` horizons; this is the single
    new adapter that lets month/year structural theses reuse it unchanged.
    """
    text = str(label or "").strip().lower()
    if len(text) < 2 or text[-1] not in _UNIT_DAYS:
        raise ValueError(f"unsupported horizon {label!r}; expected Nd / Nm / Ny")
    try:
        magnitude = int(text[:-1])
    except ValueError as exc:
        raise ValueError(f"unsupported horizon {label!r}; expected Nd / Nm / Ny") from exc
    if magnitude <= 0:
        raise ValueError("horizon magnitude must be positive")
    return magnitude * _UNIT_DAYS[text[-1]]


def _parse_dt(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("timestamp is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _iso_date(dt: datetime) -> str:
    return dt.date().isoformat()


def validate_forward_only(card: Mapping[str, Any]) -> None:
    """Enforce the at-time evidence boundary before CP2 (the leakage guard)."""
    as_of = _parse_dt(card["as_of"])
    source_as_of = _parse_dt(card.get("source_evidence_as_of") or card["as_of"])
    if source_as_of > as_of:
        raise ValueError(
            f"leakage guard: source_evidence_as_of {source_as_of.isoformat()} is after "
            f"as_of {as_of.isoformat()} for thesis {card.get('thesis_id')!r}"
        )
    if not str(card.get("resolution_criterion") or "").strip():
        raise ValueError(
            f"thesis {card.get('thesis_id')!r} must freeze a falsifiable resolution_criterion at CP1"
        )


def thesis_to_calculator_artifact(card: Mapping[str, Any], *, benchmark: str) -> Dict[str, Any]:
    """Map a structural_thesis_card onto the calculator forecast-card artifact."""
    horizon_days = horizon_to_days(card["horizon"])
    members = [str(m).upper() for m in card["members"]]
    if benchmark.upper() in members:
        raise ValueError(
            f"benchmark {benchmark!r} must not be a member of thesis {card.get('thesis_id')!r}"
        )
    return {
        "metadata": {"tool": "calculator", "data_schema_version": "calculator.6"},
        "data": {
            "candidate_forecast_cards": [
                {
                    "schema_version": "forecast_claim_card_v0",
                    "identity": {
                        "forecast_id": card["thesis_id"],
                        "run_id": "structural_thesis_family",
                        "generator_variant_id": "calculator:calculator.6:default",
                        "source_artifact_refs": [
                            {"artifact_id": "public_fixture_structural_thesis", "quality_tone": "ok"}
                        ],
                        "as_of": card["as_of"],
                    },
                    "target": {
                        "universe": card.get("universe", "public_fixture_structural"),
                        "entity_or_group": card["structural_pattern"],
                        "members": members,
                        "horizon": f"{horizon_days}d",
                        "event_definition": "group_directional_continuation_relative_to_configured_benchmark",
                        "direction": str(card["direction"]).upper(),
                        "benchmark_definition": "not_bound_until_cp1_commitment",
                    },
                    "belief": {
                        "event_probability": float(card.get("claimed_probability", 0.5)),
                        "confidence": card.get("confidence", "LOW"),
                    },
                    "admissibility": {
                        "candidate_only_not_cp1_commitment": True,
                        "no_trade_advice_flag": True,
                        "leakage_guard": "subject_time_only_inputs_plus_horizon_embargo",
                    },
                    # Structural reasoning rides in `explanation`, which admit_card
                    # copies verbatim into the CP1 claim. This is where the
                    # "obvious at the time" reasoning is frozen, pre-CP2.
                    "explanation": {
                        "structural_thesis_card_schema": STRUCTURAL_THESIS_CARD_SCHEMA,
                        "thesis_text": card["thesis_text"],
                        "structural_pattern": card["structural_pattern"],
                        "source_evidence_as_of": card.get("source_evidence_as_of") or card["as_of"],
                        "resolution_criterion": card["resolution_criterion"],
                        "negative_or_control_role": card.get("negative_or_control_role"),
                        "horizon_label": card["horizon"],
                        "horizon_days": horizon_days,
                        "benchmark_or_counterfactual": benchmark.upper(),
                    },
                }
            ]
        },
    }


def build_price_history_fixture(
    theses: Sequence[Mapping[str, Any]],
    realized: Mapping[str, Mapping[str, float]],
    *,
    benchmark: str,
    base_price: float = 100.0,
) -> Dict[str, Any]:
    """Build a deterministic public-fixture price history from REALIZED returns.

    `realized` is the "what actually happened" world, kept strictly separate from
    the at-time claim cards — the separation IS the leakage discipline. Each
    thesis owns distinct member tickers and a distinct event window, so the shared
    benchmark series never collides.
    """
    prices: Dict[str, Dict[str, float]] = {}
    bmk = benchmark.upper()
    for card in theses:
        thesis_id = card["thesis_id"]
        if thesis_id not in realized:
            raise ValueError(f"realized returns missing for thesis {thesis_id!r}")
        start = _parse_dt(card["as_of"])
        end = start + timedelta(days=horizon_to_days(card["horizon"]))
        sd, ed = _iso_date(start), _iso_date(end)
        member_return = float(realized[thesis_id]["member_return"])
        benchmark_return = float(realized[thesis_id]["benchmark_return"])
        for member in (str(m).upper() for m in card["members"]):
            series = prices.setdefault(member, {})
            series[sd] = base_price
            series[ed] = round(base_price * (1.0 + member_return), 6)
        bmk_series = prices.setdefault(bmk, {})
        bmk_series.setdefault(sd, base_price)
        bmk_series[ed] = round(base_price * (1.0 + benchmark_return), 6)
    return {"data": {"prices": prices}}


def _run_or_raise(envelope: Mapping[str, Any], *, stage: str) -> Mapping[str, Any]:
    metadata = envelope.get("metadata", {}) if isinstance(envelope, Mapping) else {}
    if metadata.get("status") != "success":
        raise RuntimeError(f"{stage} failed: {metadata.get('error') or metadata.get('status')}")
    return envelope


def _correctness(status: str, event_outcome: Optional[float]) -> Tuple[str, str]:
    """Map a CP2 scorecard outcome to (correctness, research_state)."""
    if status != "resolved" or event_outcome is None:
        return "unresolved_insufficient", "insufficient_evidence"
    if float(event_outcome) >= 1.0:
        return "claim_confirmed_forward", "candidate_set"
    return "claim_refuted_forward", "rejected"


def build_structural_thesis_family(
    theses: Sequence[Mapping[str, Any]],
    realized: Optional[Mapping[str, Mapping[str, float]]] = None,
    *,
    run_dir: Path,
    benchmark: str = "BMK",
    sampling_frame: Mapping[str, Any],
    split_policy: str = "purged_holdout",
    embargo_days: int = 0,
    truth_as_of: Optional[str] = None,
    price_history: Optional[Any] = None,
) -> Dict[str, Any]:
    """Flow the corpus through the real CP1->CP2->replay machinery and fold the
    result into a non-advisory structural-thesis research family surface.

    Truth comes from one of two sources, never both: a REAL ``price_history``
    artifact (the feeds-data integration seam — a dict or a path to a
    build_price_history.py output) or, for deterministic offline tests, a
    synthetic ``realized`` returns map. Real precedent runs pass price_history;
    unit tests pass realized.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    benchmark = benchmark.upper()

    for card in theses:
        validate_forward_only(card)

    # Maturity boundary: truth_as_of must be at/after the latest event_end.
    latest_end = max(
        _parse_dt(card["as_of"]) + timedelta(days=horizon_to_days(card["horizon"]))
        for card in theses
    )
    truth_as_of = truth_as_of or _iso_date(latest_end + timedelta(days=5)) + "T00:00:00+00:00"

    if price_history is None:
        if realized is None:
            raise ValueError("provide either a price_history artifact or a realized returns map")
        price_history = build_price_history_fixture(theses, realized, benchmark=benchmark)
    elif isinstance(price_history, (str, Path)):
        price_history = json.loads(Path(price_history).read_text(encoding="utf-8"))
    price_path = run_dir / "structural_price_history.json"
    price_path.write_text(json.dumps(price_history), encoding="utf-8")

    thesis_results: List[Dict[str, Any]] = []
    calculator_paths_by_horizon: Dict[int, List[str]] = {}

    for card in theses:
        thesis_id = card["thesis_id"]
        horizon_days = horizon_to_days(card["horizon"])
        artifact = thesis_to_calculator_artifact(card, benchmark=benchmark)
        calc_path = run_dir / f"calc_{thesis_id}.json"
        calc_path.write_text(json.dumps(artifact), encoding="utf-8")
        calculator_paths_by_horizon.setdefault(horizon_days, []).append(str(calc_path))

        # --- CP1: admit the at-time claim (forward-only) -----------------------
        admitted = _run_or_raise(
            admit_forecasts.run(
                {
                    "calculator_artifact": str(calc_path),
                    "horizon": f"{horizon_days}d",
                    "benchmark": benchmark,
                    "cp1_ref": f"cp1:structural_thesis:{thesis_id}",
                    "runtime": {"run_id": f"admit_{thesis_id}", "as_of": card["as_of"]},
                },
                run_dir=run_dir,
            ),
            stage=f"cp1_admit[{thesis_id}]",
        )
        admitted_claims = admitted["data"]["admitted_claims"]
        if not admitted_claims:
            raise RuntimeError(f"thesis {thesis_id!r} produced no CP1 claim (direction unadmissible?)")
        claim = admitted_claims[0]
        admitted_path = run_dir / f"admitted_{thesis_id}.json"
        admitted_path.write_text(json.dumps(admitted), encoding="utf-8")

        # --- CP2: resolve against frozen criterion (deterministic prices) ------
        resolved = _run_or_raise(
            resolve_forecasts.run(
                {
                    "admitted_claims": str(admitted_path),
                    "price_history": str(price_path),
                    "as_of": truth_as_of,
                    "runtime": {"run_id": f"resolve_{thesis_id}", "as_of": truth_as_of},
                },
                run_dir=run_dir,
            ),
            stage=f"cp2_resolve[{thesis_id}]",
        )
        resolved_path = run_dir / f"resolved_{thesis_id}.json"
        resolved_path.write_text(json.dumps(resolved), encoding="utf-8")

        # --- Proper-scoring replay (CP1-admitted only) -------------------------
        replay = _run_or_raise(
            eval_replay.run(
                {
                    "forecast_cards": str(admitted_path),
                    "prediction_reconciliation": str(resolved_path),
                    "horizon": f"{horizon_days}d",
                    "mode": "cp1_admitted_only",
                    "runtime": {"run_id": f"replay_{thesis_id}", "as_of": truth_as_of},
                },
                run_dir=run_dir,
            ),
            stage=f"replay[{thesis_id}]",
        )
        scorecard = replay["data"]["scorecards"][0]
        proper = scorecard.get("proper_score", {}) if isinstance(scorecard, Mapping) else {}
        status = str(scorecard.get("status") or "")
        event_outcome = proper.get("event_outcome")
        correctness, research_state = _correctness(status, event_outcome)
        role = card.get("negative_or_control_role")

        thesis_results.append(
            {
                "thesis_id": thesis_id,
                "structural_pattern": card["structural_pattern"],
                "thesis_text": card["thesis_text"],
                "as_of": card["as_of"],
                "source_evidence_as_of": card.get("source_evidence_as_of") or card["as_of"],
                "cp1_forward_only": True,
                "horizon_label": card["horizon"],
                "horizon_days": horizon_days,
                "cp1_claim_id": claim["forecast_id"],
                "frozen_resolution_criterion": card["resolution_criterion"],
                "cp2_status": status,
                "cp2_event_outcome": event_outcome,
                "brier_score": proper.get("brier_score"),
                "group_excess_return": proper.get("group_excess_return"),
                "correctness": correctness,
                "research_state": research_state,
                "negative_or_control_role": role,
                "is_control": role in CONTROL_ROLES,
                "loser_is_valid_evidence": correctness == "claim_refuted_forward" and status == "resolved",
            }
        )

    # --- Family-level purged/walk-forward replay discipline receipt ------------
    replay_groups: List[Dict[str, Any]] = []
    split_counts: Dict[str, int] = {}
    optimizer_permission_any = False
    random_kfold_allowed_any = False
    for horizon_days, calc_paths in sorted(calculator_paths_by_horizon.items()):
        hist = _run_or_raise(
            historical_replay.run(
                {
                    "calculator_artifacts": calc_paths,
                    "price_history": str(price_path),
                    "horizons": f"{horizon_days}d",
                    "benchmark": benchmark,
                    "split_policy": split_policy,
                    "embargo_days": embargo_days,
                    "truth_as_of": truth_as_of,
                    "runtime": {"run_id": f"structural_hist_{horizon_days}d", "as_of": truth_as_of},
                },
                run_dir=run_dir,
            ),
            stage=f"historical_replay[{horizon_days}d]",
        )
        ledger = hist["data"]["experiment_ledger"]
        split = ledger["split_policy"]
        for key, value in (split.get("split_membership_counts") or {}).items():
            split_counts[key] = split_counts.get(key, 0) + int(value)
        optimizer_permission_any = optimizer_permission_any or bool(
            ledger.get("variant_decision", {}).get("optimizer_permission")
        )
        random_kfold_allowed_any = random_kfold_allowed_any or bool(split.get("random_kfold_allowed"))
        replay_groups.append(
            {
                "horizon_days": horizon_days,
                "experiment_id": ledger.get("experiment_id"),
                "split_policy": split.get("kind"),
                "executable": split.get("executable"),
                "random_kfold_allowed": split.get("random_kfold_allowed"),
                "claim_counts": ledger.get("claim_counts"),
            }
        )

    family = _fold_family_surface(
        thesis_results,
        sampling_frame=sampling_frame,
        benchmark=benchmark,
        replay_groups=replay_groups,
        split_counts=split_counts,
        split_policy=split_policy,
        optimizer_permission_any=optimizer_permission_any,
        random_kfold_allowed_any=random_kfold_allowed_any,
        truth_as_of=truth_as_of,
    )
    return family


def _fold_family_surface(
    thesis_results: List[Dict[str, Any]],
    *,
    sampling_frame: Mapping[str, Any],
    benchmark: str,
    replay_groups: List[Dict[str, Any]],
    split_counts: Dict[str, int],
    split_policy: str,
    optimizer_permission_any: bool,
    random_kfold_allowed_any: bool,
    truth_as_of: str,
) -> Dict[str, Any]:
    # Per-pattern family memory. A refuted or control pattern reduces future
    # search pressure instead of being rewritten into a post-hoc success story.
    patterns: Dict[str, Dict[str, int]] = {}
    for row in thesis_results:
        pat = row["structural_pattern"]
        bucket = patterns.setdefault(pat, {"confirmed": 0, "refuted": 0, "control": 0, "insufficient": 0})
        if row["is_control"]:
            bucket["control"] += 1
            if row["correctness"] != "claim_confirmed_forward":
                pass  # control correctly failed
        elif row["correctness"] == "claim_confirmed_forward":
            bucket["confirmed"] += 1
        elif row["correctness"] == "claim_refuted_forward":
            bucket["refuted"] += 1
        else:
            bucket["insufficient"] += 1

    family_memory: List[Dict[str, Any]] = []
    surviving_patterns: set[str] = set()
    for pat, bucket in sorted(patterns.items()):
        if bucket["control"]:
            memory_state = "control_rejected"
            implication = "keep_control_in_rotation_before_learning_claims"
            reduces = True
        elif bucket["refuted"] and not bucket["confirmed"]:
            memory_state = "insufficient_evidence"
            implication = "deprioritize_until_new_at_time_evidence_reduces_uncertainty"
            reduces = True
        elif bucket["confirmed"] and not bucket["refuted"]:
            memory_state = "candidate_set"
            implication = "retain_as_candidate_family_without_winner_language"
            reduces = False
            surviving_patterns.add(pat)
        else:
            memory_state = "insufficient_evidence"
            implication = "mixed_or_thin_evidence_keep_testing"
            reduces = False
        family_memory.append(
            {
                "family_id": pat,
                "memory_state": memory_state,
                "current_evidence": {
                    "confirmed_forward": bucket["confirmed"],
                    "refuted_forward": bucket["refuted"],
                    "control": bucket["control"],
                    "insufficient": bucket["insufficient"],
                },
                "program_implication": implication,
                "reduces_search_pressure": reduces,
            }
        )

    # Forward lens: "where things are headed" in allowed, non-advisory language.
    # GATE: only patterns that survived at-time replay (>=1 confirmation, 0
    # refutations, not a control) may yield a review_candidate. The loser's and
    # control's patterns are barred — a current-looking candidate cannot enter
    # before a loser has flowed through the same pipe.
    forward_candidates: List[Dict[str, Any]] = []
    for pat, bucket in sorted(patterns.items()):
        if pat in surviving_patterns:
            forward_candidates.append(
                {
                    "structural_pattern": pat,
                    "current_situation_descriptor": f"public-fixture situation matching the {pat} structure",
                    "research_state": "review_candidate",
                    "gated_reason": (
                        "pattern survived at-time forward replay; flagged for human review only, "
                        "not an action, not a winner"
                    ),
                    "winner_language_allowed": False,
                }
            )
        elif bucket["control"]:
            forward_candidates.append(
                {
                    "structural_pattern": pat,
                    "current_situation_descriptor": f"control family {pat}",
                    "research_state": "rejected",
                    "gated_reason": "negative control must not enter the forward candidate set",
                    "winner_language_allowed": False,
                }
            )
        else:
            forward_candidates.append(
                {
                    "structural_pattern": pat,
                    "current_situation_descriptor": f"public-fixture situation matching the {pat} structure",
                    "research_state": "insufficient_evidence",
                    "gated_reason": "pattern was refuted forward or has thin evidence; barred from review candidacy",
                    "winner_language_allowed": False,
                }
            )

    resolved_count = sum(1 for r in thesis_results if r["cp2_status"] == "resolved")
    refuted_count = sum(1 for r in thesis_results if r["correctness"] == "claim_refuted_forward")
    control_count = sum(1 for r in thesis_results if r["is_control"])

    return {
        "schema_version": STRUCTURAL_THESIS_FAMILY_SCHEMA,
        "surface_id": "structural_thesis_research_family_public_demo",
        "authority_boundary": dict(AUTHORITY_CEILING),
        "no_advice_mode": {
            "enabled": True,
            "non_advisory_research_only": True,
            "prohibited_output_classes": [
                "trading_action_labels",
                "personalized_account_action",
                "portfolio_allocation",
                "performance_guarantee",
                "tradable_winner_declaration",
                "automatic_execution",
            ],
        },
        "sampling_frame": dict(sampling_frame),
        "at_time_discipline": {
            "forward_only": all(r["cp1_forward_only"] for r in thesis_results),
            "source_evidence_boundary_checked": True,
            "obvious_is_cp1_claim_status_not_outcome_label": True,
            "survivorship_guard": "at_time_sampling_including_failures",
        },
        "benchmark_or_counterfactual": benchmark,
        "thesis_results": thesis_results,
        "family_memory": family_memory,
        "model_comparison": {
            "output_state": "insufficient_evidence",
            "winner_language_allowed": False,
            "scoring_rule": "brier_score_binary_directional_event",
            "effective_sample": len(thesis_results),
            "resolved_count": resolved_count,
            "refuted_forward_count": refuted_count,
            "negative_control_count": control_count,
            "note": "small public-fixture sample; report uncertainty, never a winner",
        },
        "replay_discipline": {
            "split_policy": split_policy,
            "executable": all(g.get("executable") for g in replay_groups) if replay_groups else False,
            "random_kfold_allowed": random_kfold_allowed_any,
            "optimizer_permission": optimizer_permission_any,
            "split_membership_counts": split_counts,
            "groups": replay_groups,
        },
        "forward_lens": {
            "gate": "only_patterns_surviving_at_time_replay_may_produce_review_candidate",
            "surviving_pattern_count": len(surviving_patterns),
            "candidates": forward_candidates,
        },
        "oracle_evolve_bridge": {
            "review_gated": True,
            "auto_apply_allowed": False,
            "decision": "hold_for_review",
            "learning_authority": "human_review_required_before_any_evolve_candidate",
        },
        "truth_as_of": truth_as_of,
    }


def _finding(code: str, message: str, **extra: Any) -> Dict[str, Any]:
    payload = {"error_code": code, "message": message}
    payload.update(extra)
    return payload


def validate_structural_thesis_family(surface: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Return findings enforcing the inversion invariants. Empty == valid."""
    findings: List[Dict[str, Any]] = []

    if surface.get("schema_version") != STRUCTURAL_THESIS_FAMILY_SCHEMA:
        findings.append(
            _finding("UNEXPECTED_SCHEMA", "Structural thesis family schema mismatch.",
                     expected=STRUCTURAL_THESIS_FAMILY_SCHEMA, observed=surface.get("schema_version"))
        )

    authority = surface.get("authority_boundary", {})
    for key, expected in AUTHORITY_CEILING.items():
        if authority.get(key) is not False:
            findings.append(
                _finding("AUTHORITY_CEILING_OVERCLAIM", f"Authority flag {key} must be false.",
                         source=key, observed=authority.get(key))
            )

    advice = surface.get("no_advice_mode", {})
    if advice.get("enabled") is not True or advice.get("non_advisory_research_only") is not True:
        findings.append(_finding("NO_ADVICE_MODE_OFF", "Family must run in non-advisory research-only mode."))

    # Denominator declared, and the corpus must NOT be a survivor-only sample.
    frame = surface.get("sampling_frame", {})
    considered = int(frame.get("considered_count") or 0)
    admitted = int(frame.get("admitted_count") or 0)
    if considered < admitted or admitted <= 0:
        findings.append(
            _finding("DENOMINATOR_NOT_DECLARED", "Sampling frame must declare considered>=admitted>0.",
                     observed={"considered": considered, "admitted": admitted})
        )
    if not str(frame.get("exclusion_rule") or "").strip():
        findings.append(_finding("DENOMINATOR_NOT_DECLARED", "Sampling frame must declare an exclusion_rule."))
    if frame.get("includes_failed_thesis") is not True:
        findings.append(
            _finding("SURVIVORSHIP_SAMPLE", "Sampling frame must include at least one failed at-time thesis.")
        )

    at_time = surface.get("at_time_discipline", {})
    if at_time.get("forward_only") is not True:
        findings.append(_finding("FORWARD_ONLY_VIOLATION", "All theses must be CP1 forward-only."))
    if at_time.get("obvious_is_cp1_claim_status_not_outcome_label") is not True:
        findings.append(
            _finding("HINDSIGHT_LABELLING", "'Obvious' must be a CP1 claim-status, not an outcome label.")
        )

    results = surface.get("thesis_results", [])
    if not any(
        r.get("correctness") == "claim_refuted_forward" and r.get("cp2_status") == "resolved"
        for r in results
    ):
        findings.append(
            _finding(
                "NO_LOSER_FLOWED_THROUGH",
                "At least one loser (claim refuted forward) must be CP2-resolved as valid evidence.",
            )
        )
    if not any(r.get("loser_is_valid_evidence") for r in results):
        findings.append(_finding("LOSER_NOT_LEGIBLE", "A refuted thesis must be legible as valid evidence, not a tooling failure."))

    controls = [r for r in results if r.get("is_control")]
    if not controls:
        findings.append(_finding("NO_NEGATIVE_CONTROL", "Family must include at least one negative control."))
    for control in controls:
        if control.get("correctness") == "claim_confirmed_forward":
            findings.append(
                _finding("CONTROL_LEAK", "A negative control must not resolve as a confirmed claim.",
                         source=control.get("thesis_id"))
            )
    for row in results:
        if row.get("cp1_forward_only") is not True:
            findings.append(_finding("FORWARD_ONLY_VIOLATION", "Thesis not forward-only.", source=row.get("thesis_id")))
        if str(row.get("research_state")) not in ALLOWED_OUTPUT_STATES:
            findings.append(
                _finding("OUTPUT_STATE_UNKNOWN", "Research state outside allowed vocabulary.",
                         source=row.get("thesis_id"), observed=row.get("research_state"))
            )

    comparison = surface.get("model_comparison", {})
    if comparison.get("winner_language_allowed") is not False:
        findings.append(_finding("WINNER_LANGUAGE", "Model comparison must not allow winner language."))
    if str(comparison.get("output_state")) not in ALLOWED_OUTPUT_STATES:
        findings.append(
            _finding("OUTPUT_STATE_UNKNOWN", "Family output state outside allowed vocabulary.",
                     observed=comparison.get("output_state"))
        )

    # Forward gate: review_candidate only for patterns that survived at-time
    # replay (i.e. never the refuted or control patterns).
    refuted_or_control_patterns = {
        r["structural_pattern"]
        for r in results
        if r.get("is_control") or r.get("correctness") == "claim_refuted_forward"
    }
    confirmed_patterns = {
        r["structural_pattern"] for r in results if r.get("correctness") == "claim_confirmed_forward"
    }
    lens = surface.get("forward_lens", {})
    for candidate in lens.get("candidates", []):
        state = str(candidate.get("research_state"))
        pattern = candidate.get("structural_pattern")
        if state not in ALLOWED_OUTPUT_STATES:
            findings.append(
                _finding("OUTPUT_STATE_UNKNOWN", "Forward candidate state outside allowed vocabulary.",
                         observed=state)
            )
        if candidate.get("winner_language_allowed") is not False:
            findings.append(_finding("WINNER_LANGUAGE", "Forward candidate must not allow winner language."))
        if state == "review_candidate" and (
            pattern in refuted_or_control_patterns or pattern not in confirmed_patterns
        ):
            findings.append(
                _finding(
                    "FORWARD_GATE_BREACH",
                    "review_candidate is only allowed for a pattern that survived at-time replay.",
                    source=pattern,
                )
            )

    replay = surface.get("replay_discipline", {})
    if replay.get("random_kfold_allowed") is not False:
        findings.append(_finding("RANDOM_KFOLD_ALLOWED", "Replay must forbid random k-fold."))
    if replay.get("executable") is not True:
        findings.append(_finding("REPLAY_NOT_EXECUTABLE", "Replay split must be executable."))
    if replay.get("optimizer_permission") is not False:
        findings.append(_finding("OPTIMIZER_PERMISSION_OPEN", "Replay must not grant optimizer permission."))

    bridge = surface.get("oracle_evolve_bridge", {})
    if bridge.get("review_gated") is not True or bridge.get("auto_apply_allowed") is not False:
        findings.append(_finding("EVOLVE_GATE_OPEN", "Oracle/Evolve bridge must stay review-gated, no auto-apply."))

    # Belt-and-braces: no advisory phrasing anywhere in the serialized surface.
    blob = json.dumps(surface, sort_keys=True).lower()
    for needle in ADVISORY_FORBIDDEN_SUBSTRINGS:
        if needle in blob:
            findings.append(_finding("ADVISORY_LANGUAGE_PRESENT", f"Forbidden advisory phrasing {needle!r} present."))

    return findings


__all__ = [
    "STRUCTURAL_THESIS_CARD_SCHEMA",
    "STRUCTURAL_THESIS_FAMILY_SCHEMA",
    "ALLOWED_OUTPUT_STATES",
    "horizon_to_days",
    "validate_forward_only",
    "thesis_to_calculator_artifact",
    "build_price_history_fixture",
    "build_structural_thesis_family",
    "validate_structural_thesis_family",
]
