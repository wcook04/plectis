from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch10_frontend_work_market_cockpit_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"
SOURCE_MANIFEST_NAME = "source_module_manifest.json"

WORK_LENS_SOURCE = "system/server/ui/src/components/intelligence/WorkLens.tsx"
WORK_LENS_TEST_SOURCE = "system/server/ui/src/components/intelligence/__tests__/WorkLens.test.tsx"
MARKET_COCKPIT_SOURCE = "system/server/ui/src/components/marketIntelligence/MarketCockpit.tsx"
MARKET_LENS_SOURCE = "system/server/ui/src/components/marketIntelligence/MarketIntelligenceLens.tsx"
MARKET_COCKPIT_TEST_SOURCE = (
    "system/server/ui/src/components/marketIntelligence/__tests__/MarketCockpit.test.tsx"
)

EXPECTED_ENGINES: tuple[str, ...] = (
    "work_lens_live_state_read_contract",
    "market_cockpit_honest_signal_contract",
    "market_lens_route_readiness_contract",
    "frontend_source_test_witness",
    "private_frontend_source_ref_guard",
)

EXPECTED_NEGATIVE_CASES = {
    "work_lens_mutation_creep": ("BATCH10_FRONTEND_WORK_LENS_MUTATION_CREEP_REFUSED",),
    "market_cockpit_fake_timeseries": ("BATCH10_FRONTEND_MARKET_FAKE_TIMESERIES_REFUSED",),
    "market_claim_recommendation_leak": (
        "BATCH10_FRONTEND_MARKET_RECOMMENDATION_LEAK_REFUSED",
    ),
    "private_frontend_source_ref": ("BATCH10_FRONTEND_PRIVATE_REF_REJECTED",),
}

CASE_VERDICT_AUTHORITY = (
    "computed_by_batch10_frontend_work_market_cockpit_integrity_matrix"
)

NEGATIVE_CASE_BINDINGS: dict[str, dict[str, Any]] = {
    "work_lens_mutation_creep": {
        "engine_id": "work_lens_live_state_read_contract",
        "computed_path": "required_fragments.mutation_boundary_copy",
        "expected": True,
        "input_shape": {
            "surface": "WorkLens",
            "blocked_claim": "frontend work lens may observe WorkItems but not mutate ledgers",
        },
    },
    "market_cockpit_fake_timeseries": {
        "engine_id": "market_cockpit_honest_signal_contract",
        "computed_path": "fake_timeseries_allowed",
        "expected": False,
        "input_shape": {
            "surface": "MarketCockpit",
            "blocked_claim": "fake market time-series may not be drawn without substrate evidence",
        },
    },
    "market_claim_recommendation_leak": {
        "engine_id": "market_cockpit_honest_signal_contract",
        "computed_path": "recommendation_claims_allowed",
        "expected": False,
        "input_shape": {
            "surface": "MarketCockpit",
            "blocked_claim": "market salience observations must not become recommendations",
        },
    },
    "private_frontend_source_ref": {
        "engine_id": "private_frontend_source_ref_guard",
        "computed_path": "private_ref_count",
        "expected": 0,
        "input_shape": {
            "surface": "source_module_manifest",
            "blocked_claim": "public capsule source refs must remain repo-relative and non-private",
        },
    },
}

ENGINE_SOURCE_REFS: dict[str, tuple[str, ...]] = {
    "work_lens_live_state_read_contract": (WORK_LENS_SOURCE,),
    "market_cockpit_honest_signal_contract": (MARKET_COCKPIT_SOURCE,),
    "market_lens_route_readiness_contract": (MARKET_LENS_SOURCE,),
    "frontend_source_test_witness": (
        WORK_LENS_TEST_SOURCE,
        MARKET_COCKPIT_TEST_SOURCE,
    ),
    "private_frontend_source_ref_guard": (
        WORK_LENS_SOURCE,
        WORK_LENS_TEST_SOURCE,
        MARKET_COCKPIT_SOURCE,
        MARKET_LENS_SOURCE,
        MARKET_COCKPIT_TEST_SOURCE,
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch10_frontend_work_market_cockpit_not_runtime_or_market_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "frontend_runtime_authorized": False,
    "task_ledger_mutation_authorized": False,
    "work_ledger_mutation_authorized": False,
    "market_recommendation_authorized": False,
    "trading_or_prediction_authorized": False,
    "provider_dispatch": False,
    "browser_or_wallet_access": False,
    "publication_authorized": False,
    "release_authorized": False,
    "source_mutation_authorized": False,
    "standard_authority": (
        "public_batch10_frontend_work_market_source_open_capsule_and_source_body_digest_contract_only"
    ),
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Batch 10 Frontend Work/Market Cockpit imports exact non-secret TS/TSX "
    "source bodies for WorkLens, MarketCockpit, MarketIntelligenceLens, and "
    "their source tests, then audits their read-only work-state and honest "
    "market-signal contracts over public fixtures. It is not a browser run, "
    "not frontend release approval, not Task Ledger or Work Ledger mutation "
    "authority, not market advice, and not proof of live UI correctness."
)

SOURCE_REQUIRED_ANCHORS = {
    WORK_LENS_SOURCE: (
        "Work lens",
        "api.worldModel.workLedgerOverview",
        "api.worldModel.taskLedgerProjection",
        "Mutation flows live in",
        "WORK_LEDGER_OVERVIEW_TIMEOUT_MS",
        "selectedRouteReason",
        "data-zenith-work-priority-queue",
    ),
    WORK_LENS_TEST_SOURCE: (
        "deduplicates repeated WorkItems",
        "times out a cold Work Ledger overview",
        "keeps the cold-open queue selection local",
        "__workLensLaneForMarkForTests",
    ),
    MARKET_COCKPIT_SOURCE: (
        "Intelligence v0.6",
        "No frontend finance computation",
        "no fake",
        "normalizeEntity",
        "REASON_CODE_TRANSLATIONS",
        "calendarDaysBetween",
        "stockgrid · salience, not a recommendation",
        "data-zenith-market-cockpit",
    ),
    MARKET_LENS_SOURCE: (
        "FinanceAssuranceStrip",
        "Situations are not trading recommendations",
        "objectTokenIssue",
        "marketReadinessState",
        "data-zenith-market-intelligence-route-ready",
        "latest_market_dashboard_read_model",
    ),
    MARKET_COCKPIT_TEST_SOURCE: (
        "Smoke test for v0.6 MarketCockpit",
        "not.toContain('equity:ARM')",
        "Market Insight Matrix",
        "data-zenith-market-cockpit-version",
        "flow salience, not a recommendation",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 10 Frontend Work/Market Cockpit Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _manifest_path(input_path: Path, public_root: Path) -> Path:
    local = input_path / SOURCE_MANIFEST_NAME
    if local.is_file():
        return local
    return public_root / SPEC.source_manifest_ref


def _source_texts(input_path: Path, public_root: Path) -> dict[str, str]:
    manifest_path = _manifest_path(input_path, public_root)
    manifest = _load_json(manifest_path)
    texts: dict[str, str] = {}
    for row in manifest.get("modules", []):
        if not isinstance(row, Mapping):
            continue
        source_ref = str(row.get("source_ref") or "")
        rel_path = str(row.get("path") or "")
        if source_ref and rel_path:
            texts[source_ref] = (manifest_path.parent / rel_path).read_text(encoding="utf-8")
    return texts


def _as_record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _as_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _value_at_path(payload: Mapping[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _expected_matches(value: Any, binding: Mapping[str, Any]) -> bool:
    if "expected" in binding:
        return value == binding["expected"]
    if "expected_contains" in binding:
        return binding["expected_contains"] in value if isinstance(value, list | str) else False
    return False


def _source_evidence(engine_id: str, source_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_ref = {
        str(row.get("source_ref")): row
        for row in source_manifest.get("modules", [])
        if isinstance(row, Mapping)
    }
    evidence: list[dict[str, Any]] = []
    for source_ref in ENGINE_SOURCE_REFS.get(engine_id, ()):
        row = by_ref.get(source_ref)
        if not row:
            evidence.append(
                {
                    "source_ref": source_ref,
                    "source_to_target_relation": "missing_from_source_manifest",
                    "digest_status": "missing",
                    "body_copied": False,
                    "body_in_receipt": False,
                }
            )
            continue
        evidence.append(
            {
                "source_ref": source_ref,
                "source_to_target_relation": row.get("source_to_target_relation"),
                "digest_status": row.get("digest_status"),
                "missing_required_anchor_count": len(row.get("missing_required_anchors") or []),
                "body_copied": row.get("body_copied") is True,
                "body_in_receipt": False,
            }
        )
    return evidence


def _work_item_rows(open_by_actor: Mapping[str, Any], stale_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for actor, raw_list in open_by_actor.items():
        for raw in raw_list if isinstance(raw_list, list) else []:
            row = _as_record(raw)
            item_id = _as_string(row.get("id")) or _as_string(row.get("td_id"))
            if item_id:
                rows.append({"id": item_id, "actor": _as_string(row.get("actor")) or actor})
    for raw in stale_rows:
        item_id = _as_string(raw.get("id")) or _as_string(raw.get("td_id"))
        if item_id:
            rows.append({"id": item_id, "actor": _as_string(raw.get("actor"))})
    return rows


def _dedupe_ids(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        item_id = str(row["id"])
        if item_id in seen:
            continue
        seen.add(item_id)
        ordered.append(item_id)
    return ordered


def _extract_reason_translations(source_text: str) -> dict[str, str]:
    return dict(re.findall(r"\b([A-Z0-9_]+): '([^']+)'", source_text))


def _normalize_entity(raw: str) -> dict[str, str | None]:
    if raw.startswith("equity:"):
        return {"kind": "equity", "label": raw[7:], "hint": None}
    if raw.startswith("etf:"):
        return {"kind": "etf", "label": raw[4:], "hint": None}
    if raw.startswith("prediction_market_event:"):
        slug = raw[24:]
        return {"kind": "event", "label": slug[:28], "hint": slug}
    if raw.startswith("macro_series:"):
        slug = raw[13:]
        return {"kind": "macro", "label": slug.replace("_", " ").title(), "hint": slug}
    return {"kind": "other", "label": raw, "hint": None}


def _work_lens_live_state_read_contract(
    texts: Mapping[str, str],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    source = texts.get(WORK_LENS_SOURCE, "")
    fixture = _as_record(manifest.get("work_lens_fixture"))
    open_by_actor = _as_record(fixture.get("open_by_actor"))
    stale_rows = _as_records(fixture.get("stale_open"))
    rows = _work_item_rows(open_by_actor, stale_rows)
    deduped = _dedupe_ids(rows)
    required_fragments = {
        "work_ledger_api": "api.worldModel.workLedgerOverview" in source,
        "task_ledger_projection_api": "api.worldModel.taskLedgerProjection" in source,
        "timeout_budget": "WORK_LEDGER_OVERVIEW_TIMEOUT_MS = 12000" in source,
        "selection_locality": "onSelectedWorkItemChange" in source and "source === 'default'" in source,
        "mutation_boundary_copy": "Mutation lives in" in source and "task_ledger_apply" in source,
        "route_reason_drillthrough": "selectedRouteReason" in source and "routeReasonVocab" in source,
        "queue_containment": "data-zenith-work-priority-queue" in source,
    }
    return {
        "status": "pass"
        if all(required_fragments.values()) and len(rows) > len(deduped) and "td_duplicate" in deduped
        else "blocked",
        "engine_id": "work_lens_live_state_read_contract",
        "required_fragments": required_fragments,
        "fixture_row_count": len(rows),
        "deduped_row_count": len(deduped),
        "deduped_ids": deduped,
        "mutation_boundary": "observes_only_cli_capture_and_scoped_commits_own_mutation",
        "body_in_receipt": False,
    }


def _market_cockpit_honest_signal_contract(
    texts: Mapping[str, str],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    source = texts.get(MARKET_COCKPIT_SOURCE, "")
    fixture = _as_record(manifest.get("market_cockpit_fixture"))
    observations = _as_records(
        _as_record(fixture.get("latest_quant_presentation_mart")).get("ranked_observations")
    )
    entities = [
        entity
        for row in observations
        for entity in row.get("entities", [])
        if isinstance(entity, str)
    ]
    normalized = [_normalize_entity(entity) for entity in entities]
    translations = _extract_reason_translations(source)
    reason_codes = [
        code
        for row in observations
        for code in row.get("reason_codes", [])
        if isinstance(code, str)
    ]
    translated = [translations.get(code) for code in reason_codes]
    policy = _as_record(manifest.get("market_claim_policy"))
    required_fragments = {
        "no_frontend_finance_computation": "No frontend finance computation" in source,
        "no_fake_time_series": "no fake" in source and "time series" in source,
        "entity_normalization": "function normalizeEntity" in source,
        "reason_translations": "REASON_CODE_TRANSLATIONS" in source,
        "calendar_days_not_trading_days": "calendarDaysBetween" in source,
        "recommendation_boundary": "not a recommendation" in source,
        "primary_market_surface": "data-zenith-market-cockpit" in source,
    }
    return {
        "status": "pass"
        if all(required_fragments.values())
        and normalized
        and all(row["label"] != row.get("raw") for row in normalized)
        and all(translated)
        and policy.get("fake_timeseries_allowed") is False
        and policy.get("recommendation_claims_allowed") is False
        else "blocked",
        "engine_id": "market_cockpit_honest_signal_contract",
        "required_fragments": required_fragments,
        "normalized_entities": normalized,
        "translated_reason_codes": dict(zip(reason_codes, translated, strict=False)),
        "fake_timeseries_allowed": policy.get("fake_timeseries_allowed"),
        "recommendation_claims_allowed": policy.get("recommendation_claims_allowed"),
        "body_in_receipt": False,
    }


def _market_lens_route_readiness_contract(
    texts: Mapping[str, str],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    source = texts.get(MARKET_LENS_SOURCE, "")
    fixture = _as_record(manifest.get("market_lens_fixture"))
    read_model = _as_record(fixture.get("read_model"))
    overview = _as_record(read_model.get("overview"))
    projection_status = _as_record(read_model.get("projection_status"))
    required_fragments = {
        "finance_assurance_strip": "FinanceAssuranceStrip" in source,
        "route_ready_attr": "data-zenith-market-intelligence-route-ready" in source,
        "object_token_guard": "function objectTokenIssue" in source,
        "readiness_state": "function marketReadinessState" in source,
        "source_read_model": "latest_market_dashboard_read_model" in source,
        "not_trading_recommendations": "Situations are not trading recommendations" in source,
    }
    return {
        "status": "pass"
        if all(required_fragments.values())
        and projection_status.get("status") == "in_sync"
        and overview.get("situation_count") == 1
        and fixture.get("route_ready") is False
        else "blocked",
        "engine_id": "market_lens_route_readiness_contract",
        "required_fragments": required_fragments,
        "projection_status": projection_status.get("status"),
        "situation_count": overview.get("situation_count"),
        "route_ready": fixture.get("route_ready"),
        "body_in_receipt": False,
    }


def _frontend_source_test_witness(texts: Mapping[str, str]) -> dict[str, Any]:
    work_test = texts.get(WORK_LENS_TEST_SOURCE, "")
    market_test = texts.get(MARKET_COCKPIT_TEST_SOURCE, "")
    witnesses = {
        "work_dedupe_test": "deduplicates repeated WorkItems" in work_test,
        "work_timeout_test": "times out a cold Work Ledger overview" in work_test,
        "work_local_selection_test": "keeps the cold-open queue selection local" in work_test,
        "market_normalization_assertion": "not.toContain('equity:ARM')" in market_test,
        "market_hmc_matrix_assertion": "Market Insight Matrix" in market_test,
        "market_version_assertion": "data-zenith-market-cockpit-version" in market_test,
        "market_primary_demotes_diagnostics": "Lane defects demoted out of primary market panels." in market_test,
    }
    return {
        "status": "pass" if all(witnesses.values()) else "blocked",
        "engine_id": "frontend_source_test_witness",
        "witnesses": witnesses,
        "body_in_receipt": False,
    }


def _private_frontend_source_ref_guard(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    modules = [
        dict(row)
        for row in source_manifest.get("modules", [])
        if isinstance(row, Mapping)
    ]
    private_markers = ("/Users/", "src/ai_workflow", "browser profile", "wallet", "provider_payload")
    private_refs: list[str] = []
    non_repo_relative_refs: list[str] = []
    for row in modules:
        for key in ("source_ref", "target_ref", "path"):
            ref = str(row.get(key) or "")
            if any(marker in ref for marker in private_markers):
                private_refs.append(ref)
            if key == "source_ref" and (ref.startswith("/") or ref.startswith("~")):
                non_repo_relative_refs.append(ref)
    return {
        "status": "pass" if not private_refs and not non_repo_relative_refs else "blocked",
        "engine_id": "private_frontend_source_ref_guard",
        "private_ref_count": len(private_refs),
        "non_repo_relative_source_ref_count": len(non_repo_relative_refs),
        "source_ref_count": sum(1 for row in modules if row.get("source_ref")),
        "body_in_receipt": False,
    }


def _build_integrity_matrix(
    engines: list[dict[str, Any]],
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    engines_by_id = {str(row.get("engine_id")): row for row in engines}
    negative_cases_by_engine: dict[str, list[dict[str, Any]]] = {}
    for case_id, binding in NEGATIVE_CASE_BINDINGS.items():
        engine_id = str(binding["engine_id"])
        engine = engines_by_id.get(engine_id, {})
        computed_value = _value_at_path(engine, str(binding["computed_path"]))
        computed = _expected_matches(computed_value, binding)
        negative_cases_by_engine.setdefault(engine_id, []).append(
            {
                "case_id": case_id,
                "fixture_role": "negative_case_label_not_verdict_authority",
                "fixture_error_code": EXPECTED_NEGATIVE_CASES[case_id][0],
                "verdict_authority": CASE_VERDICT_AUTHORITY,
                "computed_path": binding["computed_path"],
                "computed_value": computed_value,
                "expected": binding.get("expected", binding.get("expected_contains")),
                "computed": computed,
                "input_shape": binding["input_shape"],
                "body_in_receipt": False,
            }
        )

    rows_out: list[dict[str, Any]] = []
    for engine_id in EXPECTED_ENGINES:
        engine = engines_by_id.get(engine_id, {})
        cases = negative_cases_by_engine.get(engine_id, [])
        rows_out.append(
            {
                "engine_id": engine_id,
                "classification": "exact_macro_body_copied_frontend_source_contract",
                "status": engine.get("status"),
                "source_evidence": _source_evidence(engine_id, source_manifest),
                "positive_input_shape": "controlled_public_input_constructed_by_capsule_evaluator",
                "positive_computed_output": engine.get("status"),
                "negative_cases": cases,
                "negative_verdict_authority": CASE_VERDICT_AUTHORITY,
                "negative_result_computed": bool(cases) and all(case["computed"] for case in cases),
                "fixture_verdict_echo_risk": bool(cases) and not all(case["computed"] for case in cases),
                "secret_private_carve_out": "receipts carry refs/digests/counts only; copied bodies remain under source_modules",
                "current_action": "keep"
                if engine.get("status") == "pass" and all(case["computed"] for case in cases)
                else "harden",
                "body_in_receipt": False,
            }
        )

    return {
        "schema_version": "batch10_frontend_work_market_integrity_matrix_v1",
        "rows": rows_out,
        "summary": {
            "engine_count": len(rows_out),
            "computed_negative_case_count": sum(
                len(row["negative_cases"])
                for row in rows_out
                if row["negative_result_computed"]
            ),
            "fixture_verdict_echo_risk_count": sum(
                1 for row in rows_out if row["fixture_verdict_echo_risk"]
            ),
            "body_in_receipt": False,
        },
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    probe_manifest = _load_json(input_path / PROBE_MANIFEST_NAME)
    texts = _source_texts(input_path, public_root)
    engines = [
        _work_lens_live_state_read_contract(texts, probe_manifest),
        _market_cockpit_honest_signal_contract(texts, probe_manifest),
        _market_lens_route_readiness_contract(texts, probe_manifest),
        _frontend_source_test_witness(texts),
        _private_frontend_source_ref_guard(source_manifest),
    ]
    integrity = _build_integrity_matrix(engines, source_manifest)
    findings: list[dict[str, Any]] = []
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH10_FRONTEND_ENGINE_BLOCKED",
                    "A Batch-10 frontend work/market engine did not pass.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in engines}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "BATCH10_FRONTEND_ENGINE_MISSING",
                "Expected frontend engines were not observed.",
                expected=list(EXPECTED_ENGINES),
                observed=sorted(observed),
            )
        )
    if source_manifest.get("module_count") != len(SOURCE_REQUIRED_ANCHORS):
        findings.append(
            finding(
                "BATCH10_FRONTEND_SOURCE_MODULE_COUNT_MISMATCH",
                "The frontend cockpit capsule must import all expected source bodies.",
                expected=len(SOURCE_REQUIRED_ANCHORS),
                observed=source_manifest.get("module_count"),
            )
        )
    integrity_summary = integrity["summary"]
    if integrity_summary["fixture_verdict_echo_risk_count"]:
        findings.append(
            finding(
                "BATCH10_FRONTEND_FIXTURE_VERDICT_ECHO_RISK",
                "Every frontend work/market negative case must be paired to computed evaluator evidence.",
                observed=integrity_summary["fixture_verdict_echo_risk_count"],
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(engines),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": engines,
        "integrity_matrix": integrity["rows"],
        "integrity_summary": integrity_summary,
        "error_codes": [str(code) for codes in EXPECTED_NEGATIVE_CASES.values() for code in codes],
        "body_in_receipt": False,
        "findings": findings,
    }


def _engine_by_id(exercise: Mapping[str, Any], engine_id: str) -> dict[str, Any]:
    engines = exercise.get("engines")
    if not isinstance(engines, list):
        return {}
    for row in engines:
        if isinstance(row, Mapping) and row.get("engine_id") == engine_id:
            return dict(row)
    return {}


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
            f"BATCH10_FRONTEND_WORK_MARKET_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _copy_bundle_for_negative_case(input_dir: Path, work_dir: Path) -> tuple[Path, Path]:
    input_path = input_dir.resolve(strict=False)
    source_public_root = public_root_for_path(input_path)
    target_public_root = work_dir / "microcosm-substrate"
    shutil.copytree(source_public_root / "core", target_public_root / "core")
    source_bundle = (
        input_path
        if (input_path / SOURCE_MANIFEST_NAME).is_file()
        else (source_public_root / SPEC.source_manifest_ref).parent
    )
    target_bundle = target_public_root / source_bundle.relative_to(source_public_root)
    target_bundle.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_bundle, target_bundle)
    return target_public_root, target_bundle


def _refresh_bundle_manifest_digest_for_body(
    bundle: Path,
    *,
    source_ref: str,
    body: str,
) -> tuple[dict[str, Any], str]:
    manifest_path = bundle / SOURCE_MANIFEST_NAME
    manifest = _load_json(manifest_path)
    rows = _as_records(manifest.get("modules"))
    for index, row in enumerate(rows):
        if row.get("source_ref") != source_ref:
            continue
        target = bundle / str(row.get("path") or "")
        target.write_text(body, encoding="utf-8")
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        row["sha256"] = sha
        row["source_sha256"] = sha
        row["target_sha256"] = sha
        row["byte_count"] = target.stat().st_size
        row["line_count"] = len(body.splitlines()) or 1
        row["sha256_match"] = True
        manifest["modules"][index] = row
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return row, sha
    raise KeyError(source_ref)


def _evaluate_bundle_negative_case(bundle: Path, public_root: Path) -> dict[str, Any]:
    source_manifest = validate_source_manifest(bundle, SPEC, public_root=public_root)
    return _evaluate(bundle, public_root, source_manifest)


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_negative_") as tmp:
            public_root, bundle = _copy_bundle_for_negative_case(input_dir, Path(tmp))
            probe_path = bundle / PROBE_MANIFEST_NAME
            probe = _load_json(probe_path)

            if case_id == "work_lens_mutation_creep":
                source_text = (
                    bundle
                    / "source_modules/system/server/ui/src/components/intelligence/WorkLens.tsx"
                ).read_text(encoding="utf-8")
                mutated = (
                    source_text.replace("Mutation lives in", "Mutation moved into")
                    .replace("Mutation flows live in", "Mutation flows moved into")
                    .replace("task_ledger_apply", "task ledger apply")
                )
                _refresh_bundle_manifest_digest_for_body(
                    bundle,
                    source_ref=WORK_LENS_SOURCE,
                    body=mutated,
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                work_engine = _engine_by_id(
                    exercise, "work_lens_live_state_read_contract"
                )
                if (
                    _as_record(work_engine.get("required_fragments")).get(
                        "mutation_boundary_copy"
                    )
                    is False
                ):
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, work_engine)

            if case_id == "market_cockpit_fake_timeseries":
                policy = _as_record(probe.get("market_claim_policy"))
                policy["fake_timeseries_allowed"] = True
                probe["market_claim_policy"] = policy
                probe_path.write_text(
                    json.dumps(probe, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                market_engine = _engine_by_id(
                    exercise, "market_cockpit_honest_signal_contract"
                )
                if market_engine.get("fake_timeseries_allowed") is True:
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, market_engine)

            if case_id == "market_claim_recommendation_leak":
                policy = _as_record(probe.get("market_claim_policy"))
                policy["recommendation_claims_allowed"] = True
                probe["market_claim_policy"] = policy
                probe_path.write_text(
                    json.dumps(probe, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                market_engine = _engine_by_id(
                    exercise, "market_cockpit_honest_signal_contract"
                )
                if market_engine.get("recommendation_claims_allowed") is True:
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, market_engine)

            if case_id == "private_frontend_source_ref":
                manifest_path = bundle / SOURCE_MANIFEST_NAME
                manifest = _load_json(manifest_path)
                rows = _as_records(manifest.get("modules"))
                row = rows[0]
                row["target_ref"] = "/Users/example/browser profile/WorkLens.tsx"
                manifest["modules"][0] = row
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                ref_engine = _engine_by_id(exercise, "private_frontend_source_ref_guard")
                if ref_engine.get("private_ref_count", 0) > 0:
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, ref_engine)
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)

    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH10_FRONTEND_WORK_MARKET_UNKNOWN_NEGATIVE_CASE_{case_id.upper()}"
        ],
        "body_in_receipt": False,
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


def run_batch10_frontend_work_market_bundle(
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
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get("copied_macro_source_module_count")
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "standard_authority": ceiling.get("standard_authority"),
        "frontend_runtime_authorized": ceiling.get("frontend_runtime_authorized"),
        "task_ledger_mutation_authorized": ceiling.get("task_ledger_mutation_authorized"),
        "work_ledger_mutation_authorized": ceiling.get("work_ledger_mutation_authorized"),
        "market_recommendation_authorized": ceiling.get("market_recommendation_authorized"),
        "trading_or_prediction_authorized": ceiling.get("trading_or_prediction_authorized"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "browser_or_wallet_access": ceiling.get("browser_or_wallet_access"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "release_authorized": ceiling.get("release_authorized"),
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
        "secret_scan_scope_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    bundle_action = "run-batch10-frontend-work-market-bundle"
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", bundle_action):
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
            BUNDLE_INPUT_MODE if args.action == bundle_action else "fixture_input"
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
