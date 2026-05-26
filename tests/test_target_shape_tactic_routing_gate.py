import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.target_shape_tactic_routing_gate import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SOURCE_PATTERN_IDS,
    main,
    run,
    run_routing_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/target_shape_tactic_routing_gate/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/target_shape_tactic_routing_gate/exported_target_shape_tactic_routing_bundle"
)


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


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


def test_target_shape_tactic_routing_gate_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["source_pattern_ids"] == SOURCE_PATTERN_IDS
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["route_case_count"] == 5
    assert result["target_shapes"] == [
        "bool_decision_goal",
        "list_length_rewrite_goal",
        "list_map_index_rewrite_goal",
        "nat_injective_goal",
        "propositional_intro_goal",
    ]
    assert result["selected_tactic_ids"] == ["decide", "omega", "rfl", "simp_all"]
    assert result["all_expectations_met"] is True
    assert result["body_material_status"] == "real_ring2_target_shape_routing_refs"
    assert (
        result["source_artifact_status"]
        == "copied_ring2_target_shape_routing_source_bodies"
    )
    assert result["source_artifact_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    assert result["source_artifacts_pass"] is True
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert all(row["body_copied"] for row in result["source_artifact_imports"])
    assert all(row["digest_matches"] for row in result["source_artifact_imports"])
    assert result["source_artifact_imports"][0]["expected_digest"].startswith(
        "sha256:"
    )
    assert (
        result["routing_evidence_status"]
        == "real_ring2_problem_domain_failure_class_route_refs"
    )
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["routing_board"]["public_contract"]["routing_pre_execution"] is True
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_target_shape_tactic_routing_gate_accepts_exported_bundle(
    tmp_path: Path,
) -> None:
    result = run_routing_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_target_shape_tactic_routing_bundle"
    assert result["bundle_id"] == "target_shape_tactic_routing_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["route_case_count"] == 5
    assert result["body_material_status"] == "real_ring2_target_shape_routing_refs"
    assert (
        result["source_artifact_status"]
        == "copied_ring2_target_shape_routing_source_bodies"
    )
    assert result["source_artifact_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    assert result["source_artifacts_pass"] is True
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert (
        result["routing_evidence_status"]
        == "real_ring2_problem_domain_failure_class_route_refs"
    )
    assert result["receipt_paths"] == [
        "receipts/exported_target_shape_tactic_routing_bundle_validation_result.json"
    ]


def test_target_shape_tactic_routing_bundle_card_is_compact(
    tmp_path: Path,
    capsys: Any,
) -> None:
    exit_code = main(
        [
            "run-routing-bundle",
            "--input",
            str(EXPORTED_BUNDLE_INPUT),
            "--out",
            str(tmp_path / "receipts"),
            "--card",
        ]
    )
    stdout = capsys.readouterr().out
    card = json.loads(stdout)

    assert exit_code == 0
    assert len(stdout.encode("utf-8")) < 6000
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["card_id"] == "target_shape_tactic_routing_bundle_card"
    assert card["route_case_count"] == 5
    assert card["selected_tactic_ids"] == ["decide", "omega", "rfl", "simp_all"]
    assert len(card["shape_decision_summary"]) == 5
    assert card["source_artifact_summary"]["copied_source_artifact_count"] == 4
    assert card["source_open_body_imports_summary"]["body_in_receipt"] is False
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert card["output_economy"]["full_routing_board_omitted"] is True
    assert "routing_board" not in card
    assert "scored_route_cases" not in card
    assert (
        tmp_path
        / "receipts"
        / "exported_target_shape_tactic_routing_bundle_validation_result.json"
    ).is_file()


def test_target_shape_tactic_routing_exported_source_modules_are_exact_copies() -> None:
    manifest = json.loads((EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 4
    assert len(manifest["modules"]) == 4

    repo_root = MICROCOSM_ROOT.parent
    for module in manifest["modules"]:
        source = repo_root / module["source_ref"]
        target = repo_root / module["target_ref"]
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == module["sha256"]
        assert _sha256(target) == module["sha256"]
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False


def test_target_shape_tactic_routing_receipts_use_real_substrate_contract(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/target_shape_tactic_routing_gate",
        public_root / "fixtures/first_wave/target_shape_tactic_routing_gate",
    )

    result = run(
        public_root / "fixtures/first_wave/target_shape_tactic_routing_gate/input",
        public_root / "receipts/first_wave/target_shape_tactic_routing_gate",
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
        assert "matched_excerpt" not in text
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == "real_ring2_target_shape_routing_refs"
        assert (
            payload["source_artifact_status"]
            == "copied_ring2_target_shape_routing_source_bodies"
        )
        assert payload["source_artifact_count"] == 4
        assert payload["copied_source_artifact_count"] == 4
        assert payload["source_artifacts_pass"] is True
        assert payload["source_open_body_imports"]["body_material_count"] == 4
        assert payload["source_open_body_imports"]["body_in_receipt"] is False
        assert (
            payload["routing_evidence_status"]
            == "real_ring2_problem_domain_failure_class_route_refs"
        )
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
