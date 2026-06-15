from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch7_secondary_runtime_capsule"
FIXTURE_ID = "first_wave.batch7_secondary_runtime_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch7_secondary_runtime_capsule"

RESULT_NAME = "batch7_secondary_runtime_capsule_result.json"
BOARD_NAME = "batch7_secondary_runtime_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch7_secondary_runtime_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch7_secondary_runtime_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch7_secondary_runtime_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch7_secondary_runtime_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch7_secondary_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "stockgrid_payload_factory_terms",
    "polymarket_clob_microstructure",
    "polymarket_four_lens_scanner",
)

EXPECTED_NEGATIVE_CASES = {
    "stockgrid_extreme_momentum": (
        "BATCH7_SECONDARY_STOCKGRID_EXTREME_MOMENTUM_REFUSED",
    ),
    "polymarket_sorted_book_trap": (
        "BATCH7_SECONDARY_POLYMARKET_NUMERIC_EXTREMA_REQUIRED",
    ),
    "polymarket_resolved_market": (
        "BATCH7_SECONDARY_POLYMARKET_RESOLVED_MARKET_GATED",
    ),
}

NEGATIVE_CASE_CODES = {
    case_id: codes[0] for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch7_secondary_public_capsule_not_release_or_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "source_mutation_authorized": False,
    "investment_advice": False,
    "semantic_truth_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 7 secondary imports public-safe stockgrid and Polymarket source "
    "bodies. It is not a release, not private-root equivalence, not browser or "
    "wallet access, not market data freshness, not investment advice, and not "
    "proof that the ranking systems are complete."
)

SOURCE_REQUIRED_ANCHORS = {
    "tools/stockgrid/stockgrid.py": (
        "class PayloadFactory",
        "def _daily_log_momentum_bps",
        "np.arcsinh",
    ),
    "tools/polymarket/clob_snapshot.py": (
        "def compute_best_prices",
        "Numeric-extrema best-price extraction",
        "def compute_depth_imbalance",
    ),
    "tools/polymarket/score.py": (
        "def calculate_lenses",
        "NEWSBREAKER",
        "is_resolved",
    ),
    "tools/polymarket/models.py": (
        "class NormalizedMarket",
        "@dataclass",
        "scores",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 7 Secondary Runtime Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch7_secondary_runtime_capsule/"
        "exported_batch7_secondary_runtime_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    return public_root.parent


def _copied_source(public_root: Path, source_ref: str) -> Path:
    return (
        public_root
        / "examples/batch7_secondary_runtime_capsule/"
        "exported_batch7_secondary_runtime_capsule_bundle/source_modules"
        / source_ref
    )


def _stockgrid_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import pandas as pd
    from tools.stockgrid.stockgrid import PayloadFactory

    factory = PayloadFactory.__new__(PayloadFactory)
    positive_bps = factory._daily_log_momentum_bps(10.0, 10)
    refused_extreme = factory._daily_log_momentum_bps(-100.0, 10) is None
    zscores = [round(float(value), 6) for value in factory._zscore(pd.Series([1.0, 2.0, 3.0]))]
    mean_defined = factory._mean_defined([1, None, "3"])
    return {
        "status": "pass"
        if positive_bps is not None
        and positive_bps > 90
        and refused_extreme
        and zscores == [-1.224745, 0.0, 1.224745]
        and mean_defined == 2.0
        else "blocked",
        "engine_id": "stockgrid_payload_factory_terms",
        "daily_log_momentum_bps": round(float(positive_bps or 0.0), 6),
        "zscore_triplet": zscores,
        "mean_defined": mean_defined,
        "extreme_momentum_refused": refused_extreme,
        "dependency_versions": {"pandas": getattr(pd, "__version__", "unknown")},
        "claim_ceiling": "local feature engineering primitive only; excludes upstream fetch and trading advice.",
    }


def _polymarket_clob_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.polymarket.clob_snapshot import (
        compute_best_prices,
        compute_depth_at_band,
        compute_depth_imbalance,
    )

    bids = [
        {"price": "0.12", "size": "20"},
        {"price": "0.42", "size": "5"},
        {"price": "0.25", "size": "2"},
    ]
    asks = [
        {"price": "0.88", "size": "3"},
        {"price": "0.53", "size": "7"},
        {"price": "0.65", "size": "9"},
    ]
    best_bid, best_ask, spread, midpoint, best_bid_size, best_ask_size = compute_best_prices(
        bids,
        asks,
    )
    bid_depth = compute_depth_at_band(bids, best_bid, 0.20, direction="bid")
    ask_depth = compute_depth_at_band(asks, best_ask, 0.20, direction="ask")
    imbalance = compute_depth_imbalance(bid_depth, ask_depth)
    sorted_book_trap_rejected = best_bid != float(bids[0]["price"]) and best_ask != float(asks[0]["price"])
    return {
        "status": "pass"
        if best_bid == 0.42
        and best_ask == 0.53
        and round(float(spread or 0), 2) == 0.11
        and sorted_book_trap_rejected
        and imbalance is not None
        and -1.0 <= imbalance <= 1.0
        else "blocked",
        "engine_id": "polymarket_clob_microstructure",
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "midpoint": midpoint,
        "best_bid_size": best_bid_size,
        "best_ask_size": best_ask_size,
        "depth_imbalance": round(float(imbalance or 0.0), 6),
        "sorted_book_trap_rejected": sorted_book_trap_rejected,
        "claim_ceiling": "public CLOB math primitive only; excludes wallet/client identity and live market access.",
    }


def _polymarket_score_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.polymarket.models import NormalizedMarket
    from tools.polymarket.score import calculate_lenses

    tuning = {
        "newsbreaker": {
            "min_volume": 100,
            "min_uncertainty": 0.1,
            "max_abs_change": 0.5,
            "uncertainty_power": 1.0,
        },
        "god_mode": {"min_price": 0.2, "max_price": 0.8},
        "scout": {"max_volume": 50_000},
    }
    open_market = NormalizedMarket(
        q="Will the synthetic fixture resolve?",
        o="Yes",
        p=0.52,
        c=0.1,
        v=1000.0,
        s=0.0,
        slug="synthetic-fixture",
        topic="synthetic",
        status="open",
        liquidity=1000.0,
        event_title="Synthetic Fixture",
        event_slug="synthetic-fixture",
        market_id="fixture-open",
        market_slug="fixture-open",
    )
    resolved_market = NormalizedMarket(
        q=open_market.q,
        o=open_market.o,
        p=0.99,
        c=0.01,
        v=1000.0,
        s=0.0,
        slug="synthetic-resolved",
        topic="synthetic",
        status="resolved",
        liquidity=1000.0,
        event_title="Synthetic Fixture",
        event_slug="synthetic-fixture",
        market_id="fixture-resolved",
        market_slug="fixture-resolved",
    )
    open_scores = calculate_lenses(open_market, tuning)
    resolved_scores = calculate_lenses(resolved_market, tuning)
    return {
        "status": "pass"
        if open_scores["NEWSBREAKER"] > 0
        and resolved_scores["NEWSBREAKER"] == 0.0
        and set(open_scores) == {"HOT SEAT", "NEWSBREAKER", "GOD MODE", "SCOUT"}
        else "blocked",
        "engine_id": "polymarket_four_lens_scanner",
        "open_scores": {key: round(value, 6) for key, value in sorted(open_scores.items())},
        "resolved_newsbreaker_gated": resolved_scores["NEWSBREAKER"] == 0.0,
        "claim_ceiling": "synthetic market scoring fixture only; not prediction or investment advice.",
    }


def _stockgrid_extreme_momentum_negative(public_root: Path) -> dict[str, Any]:
    result = _stockgrid_exercise(public_root)
    observed = (
        result.get("status") == "pass"
        and result.get("extreme_momentum_refused") is True
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "stockgrid_extreme_momentum",
        "engine_id": result.get("engine_id"),
        "extreme_momentum_refused": result.get("extreme_momentum_refused"),
        "body_in_receipt": False,
    }


def _polymarket_sorted_book_trap_negative(public_root: Path) -> dict[str, Any]:
    result = _polymarket_clob_exercise(public_root)
    observed = (
        result.get("status") == "pass"
        and result.get("sorted_book_trap_rejected") is True
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "polymarket_sorted_book_trap",
        "engine_id": result.get("engine_id"),
        "sorted_book_trap_rejected": result.get("sorted_book_trap_rejected"),
        "body_in_receipt": False,
    }


def _polymarket_resolved_market_negative(public_root: Path) -> dict[str, Any]:
    result = _polymarket_score_exercise(public_root)
    observed = (
        result.get("status") == "pass"
        and result.get("resolved_newsbreaker_gated") is True
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "polymarket_resolved_market",
        "engine_id": result.get("engine_id"),
        "resolved_newsbreaker_gated": result.get("resolved_newsbreaker_gated"),
        "body_in_receipt": False,
    }


@lru_cache(maxsize=16)
def _semantic_runtime_exercises(input_ref: str) -> Mapping[str, Any]:
    public_root = public_root_for_path(Path(input_ref))
    return {
        "negative_exercises": {
            "stockgrid_extreme_momentum": _stockgrid_extreme_momentum_negative(public_root),
            "polymarket_sorted_book_trap": _polymarket_sorted_book_trap_negative(public_root),
            "polymarket_resolved_market": _polymarket_resolved_market_negative(public_root),
        },
        "body_in_receipt": False,
    }


def _negative_exercise(runtime: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    cases = (
        runtime.get("negative_exercises")
        if isinstance(runtime.get("negative_exercises"), Mapping)
        else {}
    )
    case = cases.get(case_id)
    return case if isinstance(case, Mapping) else {}


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    exercise = _negative_exercise(runtime, case_id)
    if case_id == "stockgrid_extreme_momentum":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("extreme_momentum_refused") is True
        )
    if case_id == "polymarket_sorted_book_trap":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("sorted_book_trap_rejected") is True
        )
    if case_id == "polymarket_resolved_market":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("resolved_newsbreaker_gated") is True
        )
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    expected_code = NEGATIVE_CASE_CODES.get(case_id, "")
    observed = _observed_negative_case(
        case_id,
        _semantic_runtime_exercises(str(Path(input_dir))),
    )
    return {
        "status": "blocked" if observed else "pass",
        "error_codes": [expected_code] if observed and expected_code else [],
        "body_in_receipt": False,
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    exercises = [
        _stockgrid_exercise(public_root),
        _polymarket_clob_exercise(public_root),
        _polymarket_score_exercise(public_root),
    ]
    for exercise in exercises:
        if exercise.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH7_SECONDARY_ENGINE_EXERCISE_BLOCKED",
                    "A Batch-7 secondary engine exercise did not pass.",
                    subject_id=str(exercise.get("engine_id")),
                    observed=exercise.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in exercises}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "BATCH7_SECONDARY_ENGINE_EXERCISE_MISSING",
                "A Batch-7 secondary engine is missing from the exercise result.",
                observed=missing,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(exercises),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": exercises,
        "error_codes": [
            str(row["error_code"]) for row in findings if row.get("error_code")
        ],
        "body_in_receipt": False,
        "findings": findings,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch7_secondary_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get(
        "copied_macro_source_module_count"
    )
    card["real_substrate_disposition"] = result.get("real_substrate_disposition")
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="microcosm batch7-secondary-runtime-capsule")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-batch7-secondary-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    runner = run_batch7_secondary_bundle if args.action == "run-batch7-secondary-bundle" else run
    result = runner(
        args.input,
        args.out,
        acceptance_out=args.acceptance_out,
        command=f"{ORGAN_ID} {args.action}",
    )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
