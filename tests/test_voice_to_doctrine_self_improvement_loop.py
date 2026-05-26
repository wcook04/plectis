from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.voice_to_doctrine_self_improvement_loop import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_voice_to_doctrine_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/voice_to_doctrine_self_improvement_loop/"
    "exported_voice_to_doctrine_bundle"
)


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


def test_voice_to_doctrine_loop_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "voice_to_doctrine_self_improvement_loop_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["lesson_count"] == 4
    assert result["owner_surface_count"] == 5
    assert result["refined_existing_surface_count"] == 2
    assert result["workitem_capture_count"] == 1
    assert result["nothing_to_refine_count"] == 1
    assert set(result["source_pattern_refs"]) >= {
        "recursive_self_improvement_operating_loop",
        "doctrine_population_loop",
        "local_to_general_propagation",
    }
    assert result["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert result["authority_ceiling"]["raw_operator_voice_export_authorized"] is False
    assert result["authority_ceiling"]["doctrine_node_hand_edit_authorized"] is False
    assert result["authority_ceiling"]["global_doctrine_promotion_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_voice_to_doctrine_receipts_are_public_relative_and_body_free(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
        public_root / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
    )

    result = run(
        public_root / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop/input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        keys = _walk_keys(json.loads(text))
        assert "raw_operator_voice" not in keys
        assert "operator_voice_body" not in keys
        assert "private_thread_body" not in keys
        assert "provider_payload" not in keys
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "raw_seed_body" not in keys
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_voice_to_doctrine_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_voice_to_doctrine_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_voice_to_doctrine_bundle"
    assert (
        result["bundle_id"]
        == "voice_to_doctrine_self_improvement_loop_runtime_example"
    )
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["metadata_projection_not_live_learning_authority"] is True
    assert result["status_counts"] == {
        "nothing_to_refine": 1,
        "refined_existing_surface": 2,
        "workitem_captured": 1,
    }
    assert result["required_sequence"] == [
        "sense_local_pressure",
        "classify_pressure_shape",
        "select_owner_surface",
        "mutate_or_capture_owner",
        "validate_owner_result",
        "bind_closeout",
        "publish_reentry_condition",
    ]


def test_voice_to_doctrine_bundle_card_prints_compact_summary(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "bundle-card"

    rc = main(
        [
            "run-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = out_dir / "exported_voice_to_doctrine_bundle_validation_result.json"

    assert rc == 0
    assert len(captured.encode("utf-8")) < 3500
    assert full_receipt.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == "voice_to_doctrine_self_improvement_loop"
    assert card["input_mode"] == "exported_voice_to_doctrine_bundle"
    assert (
        card["bundle_id"]
        == "voice_to_doctrine_self_improvement_loop_runtime_example"
    )
    assert card["doctrine_loop_summary"]["lesson_count"] == 4
    assert card["doctrine_loop_summary"]["owner_surface_count"] == 5
    assert card["doctrine_loop_summary"]["refined_existing_surface_count"] == 2
    assert card["negative_case_coverage"]["expected_case_count"] == 0
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["secret_exclusion_scan_summary"]["hits_exported"] is False
    assert card["authority_ceiling"]["release_authorized"] is False
    assert card["no_export_guards"]["findings_exported"] is False
    assert card["no_export_guards"]["observed_negative_cases_exported"] is False
    assert card["output_economy"]["full_payload_drilldown"] == "rerun without --card"
    assert "findings" not in card
    assert "blocking_findings" not in card
    assert "observed_negative_cases" not in card
    assert "anti_claim" not in card


def test_voice_to_doctrine_fixture_card_honors_acceptance_out(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "fixture-card"
    acceptance_out = tmp_path / "acceptance.json"

    rc = main(
        [
            "run",
            "--input",
            str(FIXTURE_INPUT),
            "--out",
            str(out_dir),
            "--acceptance-out",
            str(acceptance_out),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)

    assert rc == 0
    assert len(captured.encode("utf-8")) < 3500
    assert acceptance_out.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["input_mode"] == "first_wave_fixture"
    assert card["negative_case_coverage"]["expected_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["observed_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["missing_negative_cases"] == []
    assert card["no_export_guards"]["private_bodies_exported"] is False
    assert card["no_export_guards"]["provider_payloads_exported"] is False
