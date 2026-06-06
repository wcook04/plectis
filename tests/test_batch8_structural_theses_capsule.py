from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch8_structural_theses_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_SOURCE_MODULE_IDS,
    main,
    result_card,
    run,
    run_batch8_structural_theses_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
ORGAN_ID = "batch8_structural_theses_capsule"
FIXTURE_INPUT = MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}/input"
EXPORTED_BUNDLE = MICROCOSM_ROOT / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
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
        MICROCOSM_ROOT / f"examples/{ORGAN_ID}",
        public_root / f"examples/{ORGAN_ID}",
    )
    shutil.copytree(
        MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}",
        public_root / f"fixtures/first_wave/{ORGAN_ID}",
    )
    return public_root / f"fixtures/first_wave/{ORGAN_ID}/input"


def test_batch8_structural_theses_runs_public_fixture(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        acceptance_out=tmp_path
        / f"receipts/acceptance/first_wave/{ORGAN_ID}_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_SOURCE_MODULE_IDS)
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    assert result["semantic_negative_case_evaluator_used"] is True

    exercise = result["exercise"]
    assert exercise["thesis_result_count"] == 4
    assert exercise["winner_correctness"] == "claim_confirmed_forward"
    assert exercise["loser_correctness"] == "claim_refuted_forward"
    assert exercise["loser_is_valid_evidence"] is True
    assert exercise["control_is_control"] is True
    assert exercise["control_correctness"] != "claim_confirmed_forward"
    assert exercise["authority_boundary"]["investment_recommendation_authorized"] is False
    assert result["body_in_receipt"] is False


def test_batch8_structural_theses_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch8_structural_theses_bundle(
        EXPORTED_BUNDLE,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_SOURCE_MODULE_IDS)
    assert result["exercise"]["copied_macro_source_module_count"] == len(EXPECTED_SOURCE_MODULE_IDS)
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch8_structural_theses_source_module_is_exact_macro_source_ref() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["source_port_class"] == "exact_macro_source_runtime_exercise"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == len(EXPECTED_SOURCE_MODULE_IDS)
    assert {row["module_id"] for row in manifest["modules"]} == set(EXPECTED_SOURCE_MODULE_IDS)

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch8_structural_theses_card_omits_private_bodies(
    tmp_path: Path,
    capsys,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["source_module_count"] == len(EXPECTED_SOURCE_MODULE_IDS)
    assert card["observed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": "real_substrate_capsule",
        "python_import": True,
        "financial_advice_authorized": False,
        "investment_recommendation_authorized": False,
        "live_market_data_authorized": False,
        "portfolio_action_authorized": False,
        "provider_calls_authorized": False,
        "publication_authorized": False,
        "release_authorized": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)

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


def test_batch8_structural_theses_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch8_structural_theses_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = fixture / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(row["semantic_evaluator_used"] for row in result["negative_case_semantics"])
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "BATCH8_STRUCTURAL_THESES_CONTROL_LEAK_REJECTED" in result["error_codes"]
    assert "BATCH8_STRUCTURAL_THESES_FORWARD_GATE_BREACH_REJECTED" in result["error_codes"]
    assert "BATCH8_STRUCTURAL_THESES_SURVIVOR_ONLY_REJECTED" in result["error_codes"]
