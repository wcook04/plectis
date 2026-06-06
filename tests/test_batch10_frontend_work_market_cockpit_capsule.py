from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch10_frontend_work_market_cockpit_capsule import (
    AUTHORITY_CEILING,
    CASE_VERDICT_AUTHORITY,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    NEGATIVE_CASE_BINDINGS,
    evaluate_negative_case,
    main,
    result_card,
    run,
    run_batch10_frontend_work_market_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch10_frontend_work_market_cockpit_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch10_frontend_work_market_cockpit_capsule/exported_batch10_frontend_work_market_cockpit_capsule_bundle"
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


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch10_frontend_work_market_cockpit_capsule",
        public_root / "examples/batch10_frontend_work_market_cockpit_capsule",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch10_frontend_work_market_cockpit_capsule",
        public_root / "fixtures/first_wave/batch10_frontend_work_market_cockpit_capsule",
    )
    return public_root / "fixtures/first_wave/batch10_frontend_work_market_cockpit_capsule/input"


def test_batch10_frontend_work_market_capsule_runs_source_body_audit(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_frontend_work_market_cockpit_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch10_frontend_work_market_cockpit_capsule_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["engine_count"] == len(EXPECTED_ENGINES)
    assert set(exercise["engine_ids"]) == set(EXPECTED_ENGINES)
    assert all(row["status"] == "pass" for row in exercise["engines"])

    by_engine = {row["engine_id"]: row for row in exercise["engines"]}
    assert by_engine["work_lens_live_state_read_contract"]["deduped_ids"] == [
        "td_duplicate",
        "td_unique",
    ]
    assert by_engine["market_cockpit_honest_signal_contract"]["normalized_entities"][0]["label"] == "ARM"
    assert (
        by_engine["market_cockpit_honest_signal_contract"]["translated_reason_codes"][
            "FLOW_SALIENCE_NOT_RECOMMENDATION"
        ]
        == "Flow salience, not a recommendation"
    )
    assert by_engine["market_lens_route_readiness_contract"]["route_ready"] is False
    assert by_engine["private_frontend_source_ref_guard"]["private_ref_count"] == 0
    assert by_engine["private_frontend_source_ref_guard"]["non_repo_relative_source_ref_count"] == 0
    assert exercise["integrity_summary"]["engine_count"] == len(EXPECTED_ENGINES)
    assert exercise["integrity_summary"]["computed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert exercise["integrity_summary"]["fixture_verdict_echo_risk_count"] == 0
    matrix = {row["engine_id"]: row for row in exercise["integrity_matrix"]}
    assert set(matrix) == set(EXPECTED_ENGINES)
    for row in matrix.values():
        assert row["negative_verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert row["fixture_verdict_echo_risk"] is False
        if row["negative_cases"]:
            assert row["negative_result_computed"] is True
        assert row["source_evidence"]
        assert row["current_action"] == "keep"
    assert result["body_in_receipt"] is False


def test_batch10_frontend_work_market_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch10_frontend_work_market_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch10_frontend_work_market_cockpit_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["input_mode"] == "exported_batch10_frontend_work_market_cockpit_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] == 5
    assert result["exercise"]["copied_macro_source_module_count"] == 5
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_frontend_work_market_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch10_frontend_work_market_cockpit_capsule/"
        "exported_batch10_frontend_work_market_cockpit_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch10_frontend_work_market_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "batch10_frontend_work_market_cockpit_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_frontend_work_market_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 5

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


def test_batch10_frontend_work_market_card_omits_private_bodies(
    tmp_path: Path,
    capsys,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_frontend_work_market_cockpit_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["source_module_count"] == 5
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": "real_substrate_capsule",
        "standard_authority": AUTHORITY_CEILING["standard_authority"],
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
        "whole_system_correctness_claim": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)

    assert (
        main(
            [
                "run",
                "--input",
                str(FIXTURE_INPUT),
                "--out",
                str(tmp_path / "cli_card"),
                "--card",
            ]
        )
        == 0
    )
    cli_card = json.loads(capsys.readouterr().out)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]


def test_batch10_frontend_work_market_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert payload["verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert payload["engine_id"] == NEGATIVE_CASE_BINDINGS[case_id]["engine_id"]
        assert payload["body_in_receipt"] is False


def test_batch10_frontend_work_market_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3]
        / "receipts/first_wave/batch10_frontend_work_market_cockpit_capsule",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    for expected_codes in EXPECTED_NEGATIVE_CASES.values():
        for code in expected_codes:
            assert code in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch10_frontend_work_market_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]
