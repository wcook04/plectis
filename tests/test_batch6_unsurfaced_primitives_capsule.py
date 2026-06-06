from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

import microcosm_core.organs.batch6_unsurfaced_primitives_capsule as batch6
from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs.batch6_unsurfaced_primitives_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_MECHANISMS,
    EXPECTED_MODULE_IDS,
    EXPECTED_NEGATIVE_CASES,
    _load_copied_module,
    evaluate_negative_case,
    result_card,
    run,
    run_batch6_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch6_unsurfaced_primitives_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch6_unsurfaced_primitives_capsule/exported_batch6_unsurfaced_primitives_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _copied_modules() -> dict[str, Mapping[str, Any]]:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    rows = manifest.get("modules")
    assert isinstance(rows, list)
    return {
        str(row["module_id"]): row
        for row in rows
        if isinstance(row, Mapping) and row.get("module_id")
    }


def _write_negative_case_fixtures(input_dir: Path) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    for case_id in EXPECTED_NEGATIVE_CASES:
        (input_dir / f"{case_id}.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "error_codes": ["DECLARED_BOGUS_NEGATIVE_CODE"],
                    "body_in_receipt": False,
                }
            ),
            encoding="utf-8",
        )


def _semantic_runtime_fixture(
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {
        "raw_seed_keyphrase_engine": {
            "status": "pass",
            "stopword_only_phrase_count": 0,
        },
        "schema_loose_distillation_index": {
            "status": "pass",
            "source_roles": ["assistant_text", "user_tail"],
            "body_persisted": False,
        },
        "operator_handoff_linkage": {
            "status": "pass",
            "confidence_floor_met": True,
            "unrelated_below_floor": True,
        },
        "observed_turn_window_merge": {
            "status": "pass",
            "duplicate_window_reason": "observed_window_within_memory",
            "merged_count": 3,
        },
        "market_situation_graph": {
            "status": "pass",
            "missing_counterevidence_rejected": True,
        },
        "finance_numeric_assurance": {
            "status": "pass",
            "display_state": "blocked",
            "check_ids": ["stockgrid_flow_unit_scale_mismatch"],
        },
        "fail_closed_status_judge": {
            "status": "pass",
            "poisoned_policy_decision": "block",
        },
        "idea_microcosm_concurrency_guard": {
            "status": "pass",
            "parent_child_conflict_detected": True,
        },
        "metabolism_market_clock": {
            "status": "pass",
            "open_duplicate_suppressed": True,
        },
        "population_lane_provider_recovery": {
            "status": "pass",
            "timeout_scope": "provider_model",
        },
        "demo_take_temporal_join": {
            "status": "pass",
            "closed_pause_video_t_seconds": 105.0,
            "active_pause_video_t_seconds": 15.0,
        },
    }
    for mechanism_id, patch in (overrides or {}).items():
        rows[mechanism_id].update(patch)
    return rows


def test_batch6_unsurfaced_primitives_capsule_runs_real_source_exercises(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch6_unsurfaced_primitives_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch6_unsurfaced_primitives_capsule_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert {row["mechanism_id"] for row in exercise["mechanisms"]} == set(EXPECTED_MECHANISMS)
    assert all(row["status"] == "pass" for row in exercise["mechanisms"])
    assert set(exercise["runtime_exercises"]) == set(EXPECTED_MECHANISMS)
    assert all(row["status"] == "pass" for row in exercise["runtime_exercises"].values())

    runtime = exercise["runtime_exercises"]
    assert runtime["raw_seed_keyphrase_engine"]["ranked_phrase_count"] >= 1
    assert runtime["schema_loose_distillation_index"]["body_persisted"] is False
    assert runtime["operator_handoff_linkage"]["confidence_floor_met"] is True
    assert runtime["operator_handoff_linkage"]["unrelated_below_floor"] is True
    assert runtime["observed_turn_window_merge"]["merge_reason"] == "observed_appended_tail"
    assert runtime["market_situation_graph"]["all_situations_have_counterevidence"] is True
    assert runtime["market_situation_graph"]["missing_counterevidence_rejected"] is True
    assert "stockgrid_flow_unit_scale_mismatch" in runtime["finance_numeric_assurance"]["check_ids"]
    assert runtime["fail_closed_status_judge"]["poisoned_policy_decision"] == "block"
    assert runtime["idea_microcosm_concurrency_guard"]["parent_child_overlap"] is True
    assert runtime["idea_microcosm_concurrency_guard"]["parent_child_conflict_detected"] is True
    assert runtime["metabolism_market_clock"]["open_duplicate_suppressed"] is True
    assert runtime["population_lane_provider_recovery"]["timeout_scope"] == "provider_model"
    assert runtime["demo_take_temporal_join"]["closed_pause_video_t_seconds"] == 105.0

    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["body_in_receipt"] is False


def test_batch6_operator_thread_memory_window_merge_computes_edge_cases() -> None:
    module = _load_copied_module(
        "operator_thread_memory",
        _copied_modules(),
        public_root=MICROCOSM_ROOT,
    )
    existing = [
        {"role": "user", "text_sha256": "a", "ordinal": 0, "char_count": 10},
        {"role": "assistant", "text_sha256": "b", "ordinal": 1, "char_count": 20},
        {"role": "user", "text_sha256": "c", "ordinal": 2, "char_count": 12},
    ]

    strict_subwindow, strict_subwindow_reason = module.merge_observed_turn_window(
        existing,
        [existing[1], existing[2]],
        now="2026-06-01T12:00:00Z",
    )
    assert strict_subwindow_reason == "observed_window_within_memory"
    assert len(strict_subwindow) == len(existing)
    assert [row["text_sha256"] for row in strict_subwindow] == ["a", "b", "c"]

    disjoint_shorter, disjoint_shorter_reason = module.merge_observed_turn_window(
        existing,
        [{"role": "user", "text_sha256": "z", "ordinal": 99, "char_count": 7}],
        now="2026-06-01T12:01:00Z",
    )
    assert disjoint_shorter_reason == "preserved_existing_no_overlap"
    assert len(disjoint_shorter) == len(existing)
    assert [row["text_sha256"] for row in disjoint_shorter] == ["a", "b", "c"]

    empty_prompt = module.classify_prompt("")
    whitespace_prompt = module.classify_prompt("   \n\t  ")
    labelled_prompt = module.classify_prompt("prompt_received: B2 continue")
    assert empty_prompt["pattern_labels"] == []
    assert whitespace_prompt["pattern_labels"] == []
    assert empty_prompt["structural_hash"] != labelled_prompt["structural_hash"]
    assert whitespace_prompt["structural_hash"] != labelled_prompt["structural_hash"]


def test_batch6_market_situation_graph_computes_fixture_scoring_and_context() -> None:
    module = _load_copied_module(
        "market_situation_graph",
        _copied_modules(),
        public_root=MICROCOSM_ROOT,
    )
    source_ref = {
        "kind": "fixture_public_synthetic",
        "path": (
            "fixtures/first_wave/batch6_unsurfaced_primitives_capsule/input/"
            "batch6_probe_manifest.json"
        ),
    }
    mart = {
        "schema_version": "quant_presentation_mart_v0_1",
        "source_fingerprint": "sha256:batch6-public-synthetic",
        "run": {"run_id": "RUN_BATCH6_PUBLIC_SYNTHETIC"},
        "input_watermark": {"source": "public_synthetic"},
        "quality_gates": {"safe_use_level": "artifact_specimen_only"},
        "entity_index": [
            {
                "entity_id": "equity:ACME",
                "entity_type": "equity",
                "quality": {"category": "Technology"},
                "source_refs": [source_ref],
            },
            {
                "entity_id": "macro:CPI",
                "entity_type": "macro",
                "quality": {"category": "inflation"},
                "source_refs": [source_ref],
            },
        ],
        "features": [
            {
                "feature_family": "price_action",
                "entity_id": "equity:ACME",
                "metrics": {"chg_5d": 3.5, "vol_20d": 0.31},
                "source_refs": [source_ref],
            }
        ],
        "stockgrid_flow_board": [
            {
                "ticker": "ACME",
                "entity_id": "equity:ACME",
                "sector": "Technology",
                "flow": 125.0,
                "flow_usd": 125_000_000.0,
                "flow_score": 125_000_000.0,
                "flow_unit": "usd_millions",
                "source_refs": [source_ref],
            }
        ],
        "macro_regime_board": [
            {
                "bucket": "inflation",
                "average_z_score": 1.4,
                "series_count": 1,
                "vintage_status": "missing",
                "release_calendar_status": "missing",
                "interpretation_level": "observation",
                "top_series": [{"entity_id": "macro:CPI"}],
            }
        ],
    }

    confidence_floor = module._confidence(
        data_quality=0.0,
        evidence_strength=0.0,
        counterevidence_penalty=10.0,
        traceability=0.0,
    )
    confidence_max = module._confidence(
        data_quality=5.0,
        evidence_strength=5.0,
        counterevidence_penalty=-1.0,
        traceability=5.0,
    )
    assert confidence_floor["overall"] == 0.0
    assert confidence_floor["counterevidence_penalty"] == 1.0
    assert confidence_max["overall"] == 1.0
    assert confidence_max["data_quality"] == 1.0
    assert confidence_max["counterevidence_penalty"] == 0.0
    assert {
        "unknown": module._bucket_number(None, low=2.0, high=7.0),
        "low": module._bucket_number(1.0, low=2.0, high=7.0),
        "medium": module._bucket_number(3.0, low=2.0, high=7.0),
        "high": module._bucket_number(8.0, low=2.0, high=7.0),
    } == {"unknown": "unknown", "low": "low", "medium": "medium", "high": "high"}

    graph = module.build_market_situation_graph(
        MICROCOSM_ROOT,
        mart_payload=mart,
        validation_refs=("public_synthetic_batch6",),
    )
    assert module.validate_market_situation_graph(graph, strict=True) == []
    stock_situation = next(
        row
        for row in graph["situations"]
        if row["situation_id"] == "stockgrid_acme"
    )
    risk_context = stock_situation["risk_context"]
    assert risk_context["asset_class"] == "equity"
    assert risk_context["sector"] == "Technology"
    assert risk_context["liquidity_proxy"] == "medium"
    assert risk_context["volatility_proxy"] == "medium"
    assert risk_context["momentum_proxy"] == "medium"
    assert graph["regime_context"]["status"] == "available"
    assert graph["regime_context"]["top_bucket"] == "inflation"

    empty_regime_context = module._regime_context_from_macro({})
    assert empty_regime_context["status"] == "insufficient_data"
    assert empty_regime_context["top_bucket"] is None


def test_batch6_unsurfaced_primitives_capsule_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_batch6_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch6_unsurfaced_primitives_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch6_unsurfaced_primitives_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["exercise"]["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch6_unsurfaced_primitives_capsule_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == len(EXPECTED_MODULE_IDS)
    assert manifest["body_in_receipt"] is False
    assert {row["module_id"] for row in manifest["modules"]} == set(EXPECTED_MODULE_IDS)

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch6_unsurfaced_primitives_capsule_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch6_unsurfaced_primitives_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert card["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "assistant_raw_text" not in _walk_keys(result)
    assert "raw_text" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)


def test_batch6_common_negative_cases_ignore_declared_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        batch6,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(),
    )

    result = validate_negative_cases(
        tmp_path,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert "DECLARED_BOGUS_NEGATIVE_CODE" not in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch6_common_negative_cases_move_with_runtime_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        batch6,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(
            {"operator_handoff_linkage": {"unrelated_below_floor": False}}
        ),
    )

    result = validate_negative_cases(
        tmp_path,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "blocked"
    assert "handoff_unrelated_below_floor" in result["missing_negative_cases"]
    assert "BATCH6_HANDOFF_UNRELATED_BELOW_FLOOR" not in result["error_codes"]
    observed_errors = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in observed_errors
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in observed_errors
