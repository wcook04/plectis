from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
import tempfile
import types
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch12_market_dashboard_read_model_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"

EXPECTED_NEGATIVE_CASES = {
    "dangling_graph_edge": ("BATCH12_MDRM_DANGLING_EDGE",),
    "traversal_route_ref": ("BATCH12_MDRM_TRAVERSAL_ROUTE_REF",),
    "oracle_auto_apply_overclaim": ("BATCH12_MDRM_ORACLE_AUTO_APPLY_OVERCLAIM",),
    "strict_trading_claim_language": ("BATCH12_MDRM_STRICT_TRADING_CLAIM",),
    "silent_omission_count": ("BATCH12_MDRM_SILENT_OMISSION",),
    "freshness_missing_readiness_artifact": ("BATCH12_MDRM_FRESHNESS_MISSING_ARTIFACT",),
    "freshness_success_shortfall": ("BATCH12_MDRM_FRESHNESS_SUCCESS_SHORTFALL",),
    "freshness_blocker_list": ("BATCH12_MDRM_FRESHNESS_BLOCKER_LIST",),
    "freshness_stale_not_fresh": ("BATCH12_MDRM_FRESHNESS_STALE_NOT_FRESH",),
    "related_no_overlap_different_type": ("BATCH12_MDRM_RELATED_NO_OVERLAP",),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch12_market_dashboard_read_model_capsule_fixture_only_not_market_truth",
    "real_substrate_disposition": "real_substrate_capsule",
    "live_market_truth": False,
    "investment_advice": False,
    "provider_dispatch": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Batch 12 market-dashboard read-model validation executes copied non-secret "
    "macro source over bounded public fixtures. It validates structure, feed "
    "freshness states, and entity-overlap cohort behavior only; it is not live "
    "market truth, investment advice, provider capability, release authority, "
    "or whole-system correctness."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/lib/market_dashboard_read_model.py": (
        "def validate_market_dashboard_read_model",
        "def _runtime_feed_freshness_overlay",
        "def _related_situations",
        "TRADING_CLAIM_PATTERN",
    )
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 12 market dashboard read-model capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=("dashboard_payload.json", "feed_freshness_cases.json", "related_situations.json"),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/batch12_market_dashboard_read_model_capsule/"
        "exported_batch12_market_dashboard_read_model_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


@contextmanager
def _market_dashboard_import_stubs() -> Any:
    names = [
        "system",
        "system.lib",
        "system.lib.market_situation_graph",
    ]
    sentinel = object()
    previous = {name: sys.modules.get(name, sentinel) for name in names}
    system_mod = types.ModuleType("system")
    lib_mod = types.ModuleType("system.lib")
    graph_mod = types.ModuleType("system.lib.market_situation_graph")
    graph_mod.DEFAULT_LATEST_FILENAME = "latest_market_situation_graph.json"
    graph_mod.DEFAULT_REPORT_ROOT = Path("state/reports/market_situations")
    graph_mod.REPORT_FILENAME = "market_situation_graph_v0.json"
    graph_mod.RUN_ARTIFACT_FILENAME = "market_situation_graph.json"
    graph_mod.SCHEMA_VERSION = "market_situation_graph_v0"
    graph_mod.render_market_situation_graph = lambda *_args, **_kwargs: {}
    system_mod.lib = lib_mod
    lib_mod.market_situation_graph = graph_mod
    sys.modules["system"] = system_mod
    sys.modules["system.lib"] = lib_mod
    sys.modules["system.lib.market_situation_graph"] = graph_mod
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
    target = _source_target(source_manifest, "system/lib/market_dashboard_read_model.py")
    with _market_dashboard_import_stubs():
        spec = importlib.util.spec_from_file_location(
            "batch12_market_dashboard_read_model_source",
            target,
        )
        if spec is None or spec.loader is None:
            raise ImportError(str(target))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def _case_payload(input_dir: Path, case_id: str, base_payload: Mapping[str, Any]) -> tuple[dict[str, Any], bool, str]:
    case = _load_json(input_dir / f"{case_id}.json")
    payload = copy.deepcopy(dict(base_payload))
    for path, value in (case.get("set") or {}).items():
        cursor: Any = payload
        parts = str(path).split(".")
        for part in parts[:-1]:
            cursor = cursor[int(part)] if isinstance(cursor, list) else cursor.setdefault(part, {})
        leaf = parts[-1]
        if isinstance(cursor, list):
            cursor[int(leaf)] = value
        else:
            cursor[leaf] = value
    return payload, bool(case.get("strict")), str(case.get("expected_error_fragment") or "")


def _compute_validator_cases(module: Any, input_dir: Path, base_payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    findings = []
    for case_id in (
        "dangling_graph_edge",
        "traversal_route_ref",
        "oracle_auto_apply_overclaim",
        "strict_trading_claim_language",
        "silent_omission_count",
    ):
        payload, strict, expected = _case_payload(input_dir, case_id, base_payload)
        errors = module.validate_market_dashboard_read_model(payload, strict=strict)
        computed = any(expected in error for error in errors)
        rows.append(
            {
                "case_id": case_id,
                "computed": computed,
                "expected_error_fragment": expected,
                "observed_errors": errors,
                "body_in_receipt": False,
            }
        )
        if not computed:
            findings.append(
                finding(
                    f"{case_id.upper()}_NOT_OBSERVED",
                    "Market dashboard validator did not emit the expected source error.",
                    case_id=case_id,
                    expected=expected,
                    observed=errors,
                )
            )
    return {"rows": rows, "findings": findings}


def _write_readiness(root: Path, run_id: str, row: Mapping[str, Any]) -> None:
    artifacts = root / "state" / "runs" / run_id / "artifacts"
    if row.get("write_readiness") is False:
        return
    artifacts.mkdir(parents=True, exist_ok=True)
    days_ago = int(row.get("generated_at_days_ago") or 0)
    generated_at = (
        datetime.now(timezone.utc) - timedelta(days=days_ago)
    ).replace(microsecond=0).isoformat()
    payload = {
        "generated_at": generated_at,
        "ready": row.get("ready") is True,
        "target_count": int(row.get("target_count") or 0),
        "status_counts": {"success": int(row.get("success_count") or 0)},
        "blockers": list(row.get("blockers") or []),
    }
    (artifacts / "feed_readiness_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _compute_freshness_cases(module: Any, input_dir: Path) -> dict[str, Any]:
    fixture = _load_json(input_dir / "feed_freshness_cases.json")
    rows = []
    findings = []
    with tempfile.TemporaryDirectory(prefix="batch12-mdrm-feed-") as tmp:
        root = Path(tmp)
        for case in fixture.get("cases", []):
            if not isinstance(case, dict):
                continue
            run_id = str(case.get("run_id") or "")
            _write_readiness(root, run_id, case)
            result = module._runtime_feed_freshness_overlay(
                root,
                run_id=run_id,
                fallback=fixture.get("fallback") or {},
            )
            state = (result or {}).get("state")
            computed = state == case.get("expected_state")
            rows.append(
                {
                    "case_id": case.get("case_id"),
                    "computed": computed,
                    "state": state,
                    "expected_state": case.get("expected_state"),
                    "staleness_days": (result or {}).get("staleness_days"),
                }
            )
            if not computed:
                findings.append(
                    finding(
                        "BATCH12_MDRM_FRESHNESS_CASE_NOT_OBSERVED",
                        "Feed freshness classifier returned an unexpected state.",
                        case_id=str(case.get("case_id") or ""),
                        expected=case.get("expected_state"),
                        observed=state,
                    )
                )
    return {"rows": rows, "findings": findings}


def _compute_related_cases(module: Any, input_dir: Path) -> dict[str, Any]:
    fixture = _load_json(input_dir / "related_situations.json")
    situations = fixture.get("situations") if isinstance(fixture.get("situations"), list) else []
    by_id = {str(row.get("situation_id")): row for row in situations if isinstance(row, dict)}
    rows = []
    findings = []
    for case in fixture.get("cases", []):
        if not isinstance(case, dict):
            continue
        focus = by_id.get(str(case.get("focus_id") or ""), {})
        result = module._related_situations(focus, situations)
        expected = case.get("expected")
        computed = result == expected
        rows.append(
            {
                "case_id": case.get("case_id"),
                "computed": computed,
                "result": result,
                "expected": expected,
                "self_excluded": str(case.get("focus_id") or "") not in result,
            }
        )
        if not computed:
            findings.append(
                finding(
                    "BATCH12_MDRM_RELATED_CASE_NOT_OBSERVED",
                    "Related-situations scorer returned an unexpected cohort.",
                    case_id=str(case.get("case_id") or ""),
                    expected=expected,
                    observed=result,
                )
            )
    return {"rows": rows, "findings": findings}


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
            f"BATCH12_MDRM_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _freshness_result_by_case(module: Any, input_dir: Path, case_id: str) -> dict[str, Any]:
    fixture = _load_json(input_dir / "feed_freshness_cases.json")
    cases = fixture.get("cases") if isinstance(fixture.get("cases"), list) else []
    case = next(
        (row for row in cases if isinstance(row, dict) and row.get("case_id") == case_id),
        {},
    )
    if not case and case_id == "freshness_stale_not_fresh":
        case = next(
            (row for row in cases if isinstance(row, dict) and row.get("case_id") == "stale_green_feed"),
            {},
        )
    with tempfile.TemporaryDirectory(prefix="batch12-mdrm-negative-feed-") as tmp:
        root = Path(tmp)
        run_id = str(case.get("run_id") or "")
        _write_readiness(root, run_id, case)
        return module._runtime_feed_freshness_overlay(
            root,
            run_id=run_id,
            fallback=fixture.get("fallback") or {},
        ) or {}


def _related_result_by_case(module: Any, input_dir: Path, case_id: str) -> list[str]:
    fixture = _load_json(input_dir / "related_situations.json")
    situations = fixture.get("situations") if isinstance(fixture.get("situations"), list) else []
    cases = fixture.get("cases") if isinstance(fixture.get("cases"), list) else []
    case = next(
        (row for row in cases if isinstance(row, dict) and row.get("case_id") == case_id),
        {},
    )
    by_id = {str(row.get("situation_id")): row for row in situations if isinstance(row, dict)}
    focus = by_id.get(str(case.get("focus_id") or ""), {})
    return module._related_situations(focus, situations)


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        local_manifest_path = input_dir / "source_module_manifest.json"
        source_manifest = {
            "source_manifest_path": str(local_manifest_path.resolve())
        }
        if not local_manifest_path.is_file():
            public_root = public_root_for_path(input_dir)
            source_manifest = {
                "source_manifest_path": str(
                    public_root / SPEC.source_manifest_ref.removeprefix("microcosm-substrate/")
                )
            }
        module = _load_source_module(source_manifest)
        base_payload = _load_json(input_dir / "dashboard_payload.json")

        if case_id in {
            "dangling_graph_edge",
            "traversal_route_ref",
            "oracle_auto_apply_overclaim",
            "strict_trading_claim_language",
            "silent_omission_count",
        }:
            payload, strict, _expected = _case_payload(input_dir, case_id, base_payload)
            errors = module.validate_market_dashboard_read_model(payload, strict=strict)
            expected_fragments = {
                "dangling_graph_edge": "$.graph_slice.edges[edge1].target is dangling",
                "traversal_route_ref": "route_ref contains traversal",
                "oracle_auto_apply_overclaim": "auto_apply_allowed must be false",
                "strict_trading_claim_language": "contains trading/action claim language",
                "silent_omission_count": "silent_omission_count must be 0",
            }
            fragment = expected_fragments[case_id]
            if any(fragment in error for error in errors):
                return _semantic_negative_result(case_id, expected_codes)
            return _semantic_negative_not_rejected(case_id, errors)

        if case_id in {
            "freshness_missing_readiness_artifact",
            "freshness_success_shortfall",
            "freshness_blocker_list",
            "freshness_stale_not_fresh",
        }:
            result = _freshness_result_by_case(module, input_dir, case_id)
            evidence = result.get("runtime_evidence") if isinstance(result.get("runtime_evidence"), Mapping) else {}
            if case_id == "freshness_missing_readiness_artifact" and (
                result.get("state") == "blocked_missing_artifact"
                and evidence.get("present") is False
            ):
                return _semantic_negative_result(case_id, expected_codes)
            if case_id == "freshness_success_shortfall" and (
                result.get("state") == "blocked_missing_artifact"
                and evidence.get("present") is True
                and int(evidence.get("success_count") or 0)
                < int(evidence.get("target_count") or 0)
            ):
                return _semantic_negative_result(case_id, expected_codes)
            if case_id == "freshness_blocker_list" and (
                result.get("state") == "blocked_missing_artifact"
                and int(evidence.get("blocker_count") or 0) > 0
            ):
                return _semantic_negative_result(case_id, expected_codes)
            if case_id == "freshness_stale_not_fresh" and (
                result.get("state") == "stale_green_feed"
                and int(result.get("staleness_days") or 0) > 0
            ):
                return _semantic_negative_result(case_id, expected_codes)
            return _semantic_negative_not_rejected(case_id, result)

        if case_id == "related_no_overlap_different_type":
            result = _related_result_by_case(module, input_dir, case_id)
            if result == []:
                return _semantic_negative_result(case_id, expected_codes)
            return _semantic_negative_not_rejected(case_id, result)
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)

    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH12_MDRM_UNKNOWN_NEGATIVE_CASE_{case_id.upper()}"
        ],
        "body_in_receipt": False,
    }


def _evaluate(input_dir: Path, _public_root: Path, source_manifest: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    module = _load_source_module(source_manifest)
    base_payload = _load_json(input_dir / "dashboard_payload.json")
    clean_errors = module.validate_market_dashboard_read_model(base_payload, strict=True)
    if clean_errors:
        findings.append(
            finding(
                "BATCH12_MDRM_CLEAN_PAYLOAD_FAILED",
                "Clean dashboard read-model fixture must validate without source errors.",
                observed=clean_errors,
            )
        )
    validator = _compute_validator_cases(module, input_dir, base_payload)
    freshness = _compute_freshness_cases(module, input_dir)
    related = _compute_related_cases(module, input_dir)
    findings.extend(validator["findings"])
    findings.extend(freshness["findings"])
    findings.extend(related["findings"])
    mechanisms = [
        {
            "mechanism_id": "market_dashboard_read_model_overclaim_ceiling_validator",
            "source_symbol": "validate_market_dashboard_read_model",
            "status": "pass" if not clean_errors and all(row["computed"] for row in validator["rows"]) else "blocked",
            "negative_cases": validator["rows"],
        },
        {
            "mechanism_id": "market_feed_freshness_state_classifier",
            "source_symbol": "_runtime_feed_freshness_overlay",
            "status": "pass" if all(row["computed"] for row in freshness["rows"]) else "blocked",
            "negative_cases": freshness["rows"],
        },
        {
            "mechanism_id": "market_situation_entity_overlap_cohort_scorer",
            "source_symbol": "_related_situations",
            "status": "pass" if all(row["computed"] for row in related["rows"]) else "blocked",
            "negative_cases": related["rows"],
        },
    ]
    return {
        "status": "pass" if not findings else "blocked",
        "mechanism_count": len(mechanisms),
        "mechanisms": mechanisms,
        "clean_validator_error_count": len(clean_errors),
        "computed_negative_case_count": sum(
            1
            for mechanism in mechanisms
            for row in mechanism["negative_cases"]
            if row.get("computed")
        ),
        "error_codes": [
            code
            for case_codes in EXPECTED_NEGATIVE_CASES.values()
            for code in case_codes
        ],
        "findings": findings,
    }


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


def run_batch12_market_dashboard_read_model_bundle(
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
        "live_market_truth": ceiling.get("live_market_truth"),
        "investment_advice": ceiling.get("investment_advice"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "release_authorized": ceiling.get("release_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
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
        "validator_errors_body_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle", "run-market-dashboard-bundle"):
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
            if args.action in {"validate-bundle", "run-market-dashboard-bundle"}
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
