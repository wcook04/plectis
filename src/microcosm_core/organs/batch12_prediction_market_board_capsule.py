from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch12_prediction_market_board_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"

EXPECTED_NEGATIVE_CASES = {
    "duplicate_lower_volume_retained_higher": ("BATCH12_PREDICTION_DUPLICATE_HIGHER_VOLUME_WINS",),
    "orphan_slug_no_identity_fabrication": ("BATCH12_PREDICTION_ORPHAN_NO_IDENTITY_FABRICATION",),
    "aggregate_count_and_max_volume_deduped": ("BATCH12_PREDICTION_AGGREGATE_DEDUPED",),
    "provider_drift_multisignal_flags": ("BATCH12_QUANT_PROVIDER_DRIFT_MULTISIGNAL_FLAGS",),
    "provider_drift_fred_diagnostics_flags": ("BATCH12_QUANT_PROVIDER_DRIFT_FRED_DIAGNOSTICS_FLAGS",),
    "missingness_zero_row_lane_flagged": ("BATCH12_QUANT_MISSINGNESS_ZERO_ROW_LANE_FLAGGED",),
    "delta_no_previous_green_unavailable": ("BATCH12_QUANT_DELTA_NO_PREVIOUS_GREEN_UNAVAILABLE",),
    "macro_lifecycle_vintage_status_bound": ("BATCH12_QUANT_MACRO_LIFECYCLE_VINTAGE_STATUS_BOUND",),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": (
        "batch12_prediction_market_and_quant_mart_helper_fixture_only_not_market_truth"
    ),
    "real_substrate_disposition": "real_substrate_capsule",
    "live_prediction_market_truth": False,
    "provider_truth": False,
    "forecast_correctness": False,
    "calibration_claim": False,
    "investment_advice": False,
    "provider_dispatch": False,
    "release_authorized": False,
    "publication_authorized": False,
    "private_root_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Batch 12 prediction-market board validation executes the copied macro "
    "event join/dedup/aggregate body plus copied quant mart helper diagnostics "
    "over synthetic rows only. It does not claim live prediction-market truth, "
    "provider truth, forecast correctness, calibration, investment advice, "
    "provider dispatch, release authority, or whole-system correctness."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/lib/quant_presentation_mart.py": (
        "def _prediction_market_board",
        "def _polymarket_identity_by_slug",
        "def _provider_drift_monitor",
        "def _missingness_board",
        "def _delta_since_previous_green",
        "def _macro_lifecycle_by_slug",
        "def _macro_regime_board",
        "vintage_metadata_present",
        "event_identity_status",
        "duplicate_index",
    )
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 12 prediction market board capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(
        "prediction_market_rows.json",
        "polymarket_identity_artifact.json",
        "quant_mart_helper_cases.json",
    ),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/batch12_prediction_market_board_capsule/"
        "exported_batch12_prediction_market_board_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


@contextmanager
def _quant_mart_import_stubs() -> Any:
    names = [
        "system",
        "system.lib",
        "system.lib.market_feed_run_evidence",
        "system.lib.market_fusion_readiness",
        "system.lib.finance_numeric_assurance",
    ]
    sentinel = object()
    previous = {name: sys.modules.get(name, sentinel) for name in names}
    system_mod = types.ModuleType("system")
    lib_mod = types.ModuleType("system.lib")
    feed_mod = types.ModuleType("system.lib.market_feed_run_evidence")
    feed_mod.FEED_NODE_IDS = ["global_stock_feed", "global_news_feed", "global_macro_feed"]
    feed_mod.build_market_feed_run_evidence_card = lambda *_args, **_kwargs: {}
    feed_mod.feed_source_manifest = lambda *_args, **_kwargs: {}
    feed_mod.resolve_feed_run_dir = lambda *_args, **_kwargs: Path(".")
    readiness_mod = types.ModuleType("system.lib.market_fusion_readiness")
    readiness_mod.build_readiness_gate = lambda *_args, **_kwargs: {}
    assurance_mod = types.ModuleType("system.lib.finance_numeric_assurance")
    assurance_mod.blocking_numeric_contract_errors = lambda *_args, **_kwargs: []
    system_mod.lib = lib_mod
    lib_mod.market_feed_run_evidence = feed_mod
    lib_mod.market_fusion_readiness = readiness_mod
    lib_mod.finance_numeric_assurance = assurance_mod
    for name, module in {
        "system": system_mod,
        "system.lib": lib_mod,
        "system.lib.market_feed_run_evidence": feed_mod,
        "system.lib.market_fusion_readiness": readiness_mod,
        "system.lib.finance_numeric_assurance": assurance_mod,
    }.items():
        sys.modules[name] = module
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is sentinel:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def _source_target(source_manifest: Mapping[str, Any], source_ref: str) -> Path:
    manifest = Path(str(source_manifest.get("source_manifest_path") or ""))
    if not manifest.is_file():
        raise FileNotFoundError("source manifest path unavailable")
    manifest_payload = _load_json(manifest)
    for row in manifest_payload.get("modules", []):
        if isinstance(row, dict) and row.get("source_ref") == source_ref:
            return manifest.parent / str(row.get("path") or "")
    raise FileNotFoundError(source_ref)


def _load_source_module(source_manifest: Mapping[str, Any]) -> Any:
    target = _source_target(source_manifest, "system/lib/quant_presentation_mart.py")
    with _quant_mart_import_stubs():
        spec = importlib.util.spec_from_file_location(
            "batch12_prediction_market_board_source",
            target,
        )
        if spec is None or spec.loader is None:
            raise ImportError(str(target))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def _evaluate(input_dir: Path, _public_root: Path, source_manifest: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    module = _load_source_module(source_manifest)
    row_payload = _load_json(input_dir / "prediction_market_rows.json")
    artifact = _load_json(input_dir / "polymarket_identity_artifact.json")
    helper_payload = _load_json(input_dir / "quant_mart_helper_cases.json")
    rows = row_payload.get("rows") if isinstance(row_payload.get("rows"), list) else []
    board = module._prediction_market_board(rows, polymarket_artifact=artifact)
    events = {row.get("event_identity_status"): row for row in board}
    available = events.get("available") or {}
    orphan = events.get("missing_from_feed_artifact") or {}
    available_markets = available.get("markets") if isinstance(available.get("markets"), list) else []
    top_market = available_markets[0] if available_markets else {}

    computed_cases = [
        {
            "case_id": "duplicate_lower_volume_retained_higher",
            "computed": top_market.get("volume") == 900000.0
            and len(available_markets) == 1,
            "observed": {"top_volume": top_market.get("volume"), "market_count": len(available_markets)},
        },
        {
            "case_id": "orphan_slug_no_identity_fabrication",
            "computed": orphan.get("event_id") is None
            and (orphan.get("aggregate") or {}).get("max_liquidity") == 0.0,
            "observed": {
                "event_id": orphan.get("event_id"),
                "max_liquidity": (orphan.get("aggregate") or {}).get("max_liquidity"),
            },
        },
        {
            "case_id": "aggregate_count_and_max_volume_deduped",
            "computed": (available.get("aggregate") or {}).get("market_count") == 1
            and (available.get("aggregate") or {}).get("max_volume") == 900000.0,
            "observed": available.get("aggregate"),
        },
    ]
    for row in computed_cases:
        if not row["computed"]:
            findings.append(
                finding(
                    "BATCH12_PREDICTION_CASE_NOT_OBSERVED",
                    "Prediction-market board did not compute the expected fixture invariant.",
                    case_id=str(row["case_id"]),
                    observed=row.get("observed"),
                )
            )
    helper_cases = _evaluate_quant_mart_helpers(
        module,
        input_dir=input_dir,
        payload=helper_payload,
        findings=findings,
    )
    return {
        "status": "pass" if not findings else "blocked",
        "mechanism_count": 1 + len(helper_cases["mechanisms"]),
        "mechanisms": [
            {
                "mechanism_id": "prediction_market_event_join_dedup_aggregate_engine",
                "source_symbols": ["_prediction_market_board", "_polymarket_identity_by_slug"],
                "status": "pass" if not findings else "blocked",
                "event_count": len(board),
                "negative_cases": computed_cases,
            },
            *helper_cases["mechanisms"],
        ],
        "board": board,
        "quant_mart_helpers": helper_cases["helper_outputs"],
        "computed_negative_case_count": (
            sum(1 for row in computed_cases if row["computed"])
            + helper_cases["computed_negative_case_count"]
        ),
        "error_codes": [
            code
            for case_codes in EXPECTED_NEGATIVE_CASES.values()
            for code in case_codes
        ],
        "findings": findings,
    }


def _evaluate_quant_mart_helpers(
    module: Any,
    *,
    input_dir: Path,
    payload: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    provider_case = payload.get("provider_drift") if isinstance(payload.get("provider_drift"), Mapping) else {}
    artifacts = provider_case.get("artifacts") if isinstance(provider_case.get("artifacts"), Mapping) else {}
    evidence_card = provider_case.get("evidence_card") if isinstance(provider_case.get("evidence_card"), Mapping) else {}
    run_dir = input_dir / "runs" / str(provider_case.get("run_id") or "current_fixture_run")
    provider_rows = module._provider_drift_monitor(
        repo_root=input_dir,
        run_dir=run_dir,
        artifacts=artifacts,
        evidence_card=evidence_card,
    )
    provider_by_id = {row.get("provider_id"): row for row in provider_rows}
    stock_flags = provider_by_id.get("global_stock_feed", {}).get("drift_flags") or []
    news_flags = provider_by_id.get("global_news_feed", {}).get("drift_flags") or []
    macro_flags = provider_by_id.get("global_macro_feed", {}).get("drift_flags") or []
    provider_case_row = {
        "case_id": "provider_drift_multisignal_flags",
        "computed": all(
            flag in stock_flags
            for flag in ("provider_fallback_used", "html_response_seen", "fetch_failures")
        )
        and news_flags == [],
        "observed": {
            "global_stock_feed": stock_flags,
            "global_news_feed": news_flags,
        },
    }
    fred_case_row = {
        "case_id": "provider_drift_fred_diagnostics_flags",
        "computed": all(
            flag in macro_flags
            for flag in ("fred_invalid_series", "fred_network_warning")
        ),
        "observed": {
            "global_macro_feed": macro_flags,
        },
    }

    missingness_case = payload.get("missingness") if isinstance(payload.get("missingness"), Mapping) else {}
    coverage = missingness_case.get("coverage") if isinstance(missingness_case.get("coverage"), Mapping) else {}
    missingness_rows = module._missingness_board(coverage)
    missingness_by_id = {row.get("feed_id"): row for row in missingness_rows}
    missingness_case_row = {
        "case_id": "missingness_zero_row_lane_flagged",
        "computed": "healthy_feed" not in missingness_by_id
        and (missingness_by_id.get("empty_feed") or {}).get("empty_reason") == "zero_rows"
        and (missingness_by_id.get("degraded_feed") or {}).get("empty_reason") == "quality_degraded",
        "observed": missingness_rows,
    }

    delta_case = payload.get("delta") if isinstance(payload.get("delta"), Mapping) else {}
    delta_run_dir = input_dir / "runs" / str(delta_case.get("run_id") or "current_fixture_run")
    delta_evidence = (
        delta_case.get("evidence_card")
        if isinstance(delta_case.get("evidence_card"), Mapping)
        else {}
    )
    delta = module._delta_since_previous_green(
        repo_root=input_dir,
        run_dir=delta_run_dir,
        evidence_card=delta_evidence,
    )
    delta_case_row = {
        "case_id": "delta_no_previous_green_unavailable",
        "computed": delta.get("status") == "unavailable"
        and delta.get("row_deltas_by_lane") == {},
        "observed": delta,
    }

    macro_case = payload.get("macro_lifecycle") if isinstance(payload.get("macro_lifecycle"), Mapping) else {}
    macro_rows = macro_case.get("rows") if isinstance(macro_case.get("rows"), list) else []
    macro_artifact = (
        macro_case.get("macro_artifact")
        if isinstance(macro_case.get("macro_artifact"), Mapping)
        else {}
    )
    macro_board = module._macro_regime_board(macro_rows, macro_artifact=macro_artifact)
    macro_by_bucket = {row.get("bucket"): row for row in macro_board}
    inflation_top = (macro_by_bucket.get("inflation") or {}).get("top_series") or []
    macro_case_row = {
        "case_id": "macro_lifecycle_vintage_status_bound",
        "computed": (macro_by_bucket.get("inflation") or {}).get("vintage_status") == "available"
        and (macro_by_bucket.get("inflation") or {}).get("release_calendar_status") == "available"
        and (inflation_top[0] if inflation_top else {}).get("latest_observation_date") == "2026-05-01"
        and (macro_by_bucket.get("growth") or {}).get("vintage_status") == "missing_from_feed_artifact"
        and (macro_by_bucket.get("growth") or {}).get("release_calendar_status") == "missing_from_feed_artifact",
        "observed": macro_board,
    }

    computed_cases = [
        provider_case_row,
        fred_case_row,
        missingness_case_row,
        delta_case_row,
        macro_case_row,
    ]
    expected_codes = {
        "provider_drift_multisignal_flags": "BATCH12_QUANT_PROVIDER_DRIFT_MULTISIGNAL_FLAGS",
        "provider_drift_fred_diagnostics_flags": "BATCH12_QUANT_PROVIDER_DRIFT_FRED_DIAGNOSTICS_FLAGS",
        "missingness_zero_row_lane_flagged": "BATCH12_QUANT_MISSINGNESS_ZERO_ROW_LANE_FLAGGED",
        "delta_no_previous_green_unavailable": "BATCH12_QUANT_DELTA_NO_PREVIOUS_GREEN_UNAVAILABLE",
        "macro_lifecycle_vintage_status_bound": "BATCH12_QUANT_MACRO_LIFECYCLE_VINTAGE_STATUS_BOUND",
    }
    for row in computed_cases:
        if not row["computed"]:
            findings.append(
                finding(
                    "BATCH12_QUANT_MART_HELPER_CASE_NOT_OBSERVED",
                    "Quant mart helper did not compute the expected fixture invariant.",
                    case_id=str(row["case_id"]),
                    observed=row.get("observed"),
                )
            )
    mechanisms = [
        {
            "mechanism_id": "provider_drift_multisignal_flag_engine",
            "source_symbols": ["_provider_drift_monitor"],
            "status": "pass"
            if provider_case_row["computed"] and fred_case_row["computed"]
            else "blocked",
            "negative_cases": [provider_case_row, fred_case_row],
        },
        {
            "mechanism_id": "missingness_empty_lane_classifier",
            "source_symbols": ["_missingness_board"],
            "status": "pass" if missingness_case_row["computed"] else "blocked",
            "negative_cases": [missingness_case_row],
        },
        {
            "mechanism_id": "delta_since_previous_green",
            "source_symbols": [
                "_delta_since_previous_green",
                "_previous_green_run",
                "_is_green_feed_run",
            ],
            "status": "pass" if delta_case_row["computed"] else "blocked",
            "negative_cases": [delta_case_row],
        },
        {
            "mechanism_id": "macro_lifecycle_vintage_enrichment",
            "source_symbols": ["_macro_lifecycle_by_slug", "_macro_regime_board"],
            "status": "pass" if macro_case_row["computed"] else "blocked",
            "negative_cases": [macro_case_row],
        },
    ]
    return {
        "mechanisms": mechanisms,
        "helper_outputs": {
            "provider_drift_monitor": provider_rows,
            "missingness_board": missingness_rows,
            "delta_since_previous_green_run": delta,
            "macro_regime_board": macro_board,
            "error_codes": [
                expected_codes[row["case_id"]]
                for row in computed_cases
                if row["computed"]
            ],
        },
        "computed_negative_case_count": sum(1 for row in computed_cases if row["computed"]),
    }


def _semantic_negative_result(case_id: str, error_codes: tuple[str, ...]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": list(error_codes),
        "body_in_receipt": False,
    }


def _semantic_negative_not_rejected(case_id: str, observed: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "pass",
        "error_codes": [],
        "observed": observed,
        "body_in_receipt": False,
    }


def _semantic_negative_error(case_id: str, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH12_PREDICTION_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _source_manifest_for_input(input_dir: Path) -> dict[str, Any]:
    local_manifest = input_dir / "source_module_manifest.json"
    if local_manifest.is_file():
        return {"source_manifest_path": str(local_manifest.resolve())}
    public_root = public_root_for_path(input_dir)
    return {
        "source_manifest_path": str(
            public_root / SPEC.source_manifest_ref.removeprefix("microcosm-substrate/")
        )
    }


def _computed_case_row(exercise: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    mechanisms = exercise.get("mechanisms") if isinstance(exercise.get("mechanisms"), list) else []
    for mechanism in mechanisms:
        if not isinstance(mechanism, Mapping):
            continue
        rows = (
            mechanism.get("negative_cases")
            if isinstance(mechanism.get("negative_cases"), list)
            else []
        )
        for row in rows:
            if isinstance(row, Mapping) and row.get("case_id") == case_id:
                return dict(row)
    return {}


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        source_manifest = _source_manifest_for_input(input_dir)
        exercise = _evaluate(input_dir, public_root_for_path(input_dir), source_manifest)
        row = _computed_case_row(exercise, case_id)
        if row.get("computed") is True:
            return _semantic_negative_result(case_id, expected_codes)
        return _semantic_negative_not_rejected(case_id, row or {"case_id": case_id})
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
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


def run_batch12_prediction_market_board_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    ceiling = (
        result.get("authority_ceiling")
        if isinstance(result.get("authority_ceiling"), Mapping)
        else {}
    )
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["mechanism_count"] = exercise.get("mechanism_count")
    card["computed_negative_case_count"] = exercise.get("computed_negative_case_count")
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "live_prediction_market_truth": ceiling.get("live_prediction_market_truth"),
        "provider_truth": ceiling.get("provider_truth"),
        "forecast_correctness": ceiling.get("forecast_correctness"),
        "calibration_claim": ceiling.get("calibration_claim"),
        "investment_advice": ceiling.get("investment_advice"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "release_authorized": ceiling.get("release_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "private_root_equivalence_claim": ceiling.get("private_root_equivalence_claim"),
        "whole_system_correctness_claim": ceiling.get("whole_system_correctness_claim"),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "source_bodies_in_card": False,
        "helper_outputs_body_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle", "run-prediction-market-board-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=(
            BUNDLE_INPUT_MODE
            if args.action in {"validate-bundle", "run-prediction-market-board-bundle"}
            else "fixture_input"
        ),
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(
        json.dumps(
            result_card(result) if args.card else result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
