import hashlib
import importlib.util
import json
import shutil
import sys
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
SOURCE_BODY_FLOOR_MODULE = (
    EXPORTED_BUNDLE_INPUT
    / "source_body_floor/source_modules/microcosm_core/organs/"
    "target_shape_tactic_routing_gate.py"
)


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _sha256_prefixed(value: str) -> str:
    return value if value.startswith("sha256:") else f"sha256:{value}"


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


def _load_source_body_floor_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_target_shape_tactic_routing_gate_source_body_floor",
        SOURCE_BODY_FLOOR_MODULE,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    assert result["route_case_count"] == 7
    assert result["target_shapes"] == [
        "bool_decision_goal",
        "list_length_rewrite_goal",
        "list_map_index_rewrite_goal",
        "mathlib_search_goal",
        "nat_injective_goal",
        "propositional_intro_goal",
        "unmapped_public_goal_shape",
    ]
    assert result["selected_tactic_ids"] == ["decide", "omega", "rfl", "simp_all"]
    cases_by_id = {row["route_case_id"]: row for row in result["scored_route_cases"]}
    assert cases_by_id["ring2_bool_not_not_route"][
        "shape_preferred_tactic_ids"
    ] == ["decide", "simp_all", "rfl"]
    assert cases_by_id["ring2_bool_not_not_route"][
        "computed_selected_tactic_id"
    ] == "decide"
    assert cases_by_id["ring2_bool_not_not_route"][
        "declared_selected_tactic_id"
    ] == "decide"
    unknown_shape = cases_by_id["synthetic_unknown_shape_default_fallback_route"]
    assert unknown_shape["computed_selected_tactic_id"] == "rfl"
    assert unknown_shape["selection_basis"] == "unknown_shape_default_preference"
    assert unknown_shape["unknown_shape_default_used"] is True
    assert "default safe tactic order" in unknown_shape["fallback_reason"]
    mathlib_fallback = cases_by_id[
        "synthetic_mathlib_preferred_unavailable_fallback_route"
    ]
    assert mathlib_fallback["shape_preferred_tactic_ids"] == [
        "aesop",
        "simp_all",
        "rfl",
    ]
    assert mathlib_fallback["preferred_unavailable_tactic_ids"] == ["aesop"]
    assert mathlib_fallback["computed_selected_tactic_id"] == "simp_all"
    assert mathlib_fallback["selection_basis"] == "preferred_tactic_fallback"
    assert "next available allowed tactic" in mathlib_fallback["fallback_reason"]
    assert all(
        row["computed_selected_tactic_id"] == row["selected_tactic_id"]
        for row in result["scored_route_cases"]
    )
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
    assert (
        result["routing_board"]["public_contract"][
            "unknown_shape_default_fallback_computed"
        ]
        is True
    )
    assert (
        result["routing_board"]["public_contract"][
            "preferred_unavailable_fallback_computed"
        ]
        is True
    )
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    assert "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED" in result[
        "error_codes"
    ]
    assert "TARGET_SHAPE_UNKNOWN_SHAPE_FALLBACK_REQUIRED" in result["error_codes"]
    assert "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED" in result[
        "error_codes"
    ]


def test_target_shape_tactic_routing_rejects_mutated_real_route_selection(
    tmp_path: Path,
) -> None:
    source_case_id = "ring2_bool_not_not_route"
    source_body_floor = _load_source_body_floor_module()
    floor_manifest = json.loads(
        (
            EXPORTED_BUNDLE_INPUT
            / "source_body_floor/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    floor_module = floor_manifest["modules"][0]
    floor_target = MICROCOSM_ROOT.parent / floor_module["target_ref"]
    assert source_body_floor.ORGAN_ID == "target_shape_tactic_routing_gate"
    assert Path(source_body_floor.__file__).resolve() == SOURCE_BODY_FLOOR_MODULE
    assert floor_manifest["source_import_class"] == (
        "copied_non_secret_public_substrate_body"
    )
    assert floor_module["source_to_target_relation"] == "exact_copy"
    assert floor_module["body_copied"] is True
    assert floor_module["body_in_receipt"] is False
    assert _sha256(floor_target) == floor_module["target_sha256"]

    baseline = source_body_floor.run_routing_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "baseline_receipts",
        command="pytest",
    )
    baseline_cases = {
        row["route_case_id"]: row for row in baseline["scored_route_cases"]
    }
    baseline_case = baseline_cases[source_case_id]
    assert baseline["status"] == "pass"
    original_tactic = baseline_case["computed_selected_tactic_id"]
    fallback_tactic = next(
        tactic_id
        for tactic_id in baseline_case["shape_preferred_tactic_ids"][1:]
        if tactic_id in baseline["available_tactic_ids"]
    )
    donor_case = next(
        row
        for row in baseline["scored_route_cases"]
        if row["route_case_id"] != source_case_id
        and not row["route_case_id"].startswith("synthetic_")
        and row["computed_selected_tactic_id"] == fallback_tactic
    )
    assert baseline_case["declared_selected_tactic_id"] == original_tactic
    assert baseline_case["expectation_met"] is True

    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    mutated_input = public_root / (
        "examples/target_shape_tactic_routing_gate/"
        "exported_target_shape_tactic_routing_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE_INPUT, mutated_input)
    routes_path = mutated_input / "target_shape_routes.json"
    routes_payload = json.loads(routes_path.read_text(encoding="utf-8"))
    route = next(
        row
        for row in routes_payload["route_cases"]
        if row["route_case_id"] == source_case_id
    )
    route["candidate_tactic_ids"] = [fallback_tactic, original_tactic]
    route["allowed_tactic_ids"] = [fallback_tactic, original_tactic]
    route["selected_tactic_id"] = original_tactic
    route["expected_tactic_id"] = original_tactic
    routes_path.write_text(
        json.dumps(routes_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    widened = source_body_floor.run_routing_bundle(
        mutated_input,
        tmp_path / "widened_receipts",
        command="pytest",
    )

    widened_cases = {
        row["route_case_id"]: row for row in widened["scored_route_cases"]
    }
    widened_case = widened_cases[source_case_id]
    assert widened["status"] == "pass"
    assert widened_case["computed_selected_tactic_id"] == original_tactic
    assert widened_case["selected_tactic_id"] == original_tactic
    assert {
        row["tactic_id"]: (row["decision"], row["classifier"])
        for row in widened_case["decisions"]
    } == {
        fallback_tactic: ("allow", "TARGET_SHAPE_ADMISSIBLE"),
        original_tactic: ("allow", "TARGET_SHAPE_ADMISSIBLE"),
    }

    route["target_shape"] = donor_case["target_shape"]
    routes_path.write_text(
        json.dumps(routes_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    shape_mutated = source_body_floor.run_routing_bundle(
        mutated_input,
        tmp_path / "shape_mutated_receipts",
        command="pytest",
    )

    shape_mutated_cases = {
        row["route_case_id"]: row for row in shape_mutated["scored_route_cases"]
    }
    shape_mutated_case = shape_mutated_cases[source_case_id]
    assert shape_mutated["status"] == "blocked"
    assert shape_mutated["all_expectations_met"] is False
    assert shape_mutated_case["target_shape"] == donor_case["target_shape"]
    assert shape_mutated_case["declared_selected_tactic_id"] == original_tactic
    assert shape_mutated_case["computed_selected_tactic_id"] == fallback_tactic
    assert shape_mutated_case["selected_tactic_id"] == fallback_tactic
    assert shape_mutated_case["expectation_met"] is False
    assert "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED" in (
        shape_mutated_case["integrity_codes"]
    )

    route["target_shape"] = baseline_case["target_shape"]
    routes_path.write_text(
        json.dumps(routes_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    portfolio_path = mutated_input / "tactic_portfolio_availability.json"
    portfolio_payload = json.loads(portfolio_path.read_text(encoding="utf-8"))
    for tactic in portfolio_payload["tactics"]:
        if tactic["tactic_id"] == original_tactic:
            tactic["availability_status"] = "unavailable"
            break
    else:
        raise AssertionError("expected baseline selected tactic in target-shape portfolio")
    portfolio_path.write_text(
        json.dumps(portfolio_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    availability_mutated = source_body_floor.run_routing_bundle(
        mutated_input,
        tmp_path / "availability_mutated_receipts",
        command="pytest",
    )

    availability_mutated_cases = {
        row["route_case_id"]: row
        for row in availability_mutated["scored_route_cases"]
    }
    availability_mutated_case = availability_mutated_cases[source_case_id]
    assert availability_mutated["status"] == "blocked"
    assert availability_mutated["missing_negative_cases"] == []
    assert availability_mutated["all_expectations_met"] is False
    assert original_tactic not in availability_mutated["available_tactic_ids"]
    assert original_tactic in availability_mutated["unavailable_tactic_ids"]
    assert "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED" in (
        availability_mutated["error_codes"]
    )
    assert "TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED" in (
        availability_mutated["error_codes"]
    )
    assert "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED" in (
        availability_mutated_case["integrity_codes"]
    )
    assert "TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED" in (
        availability_mutated_case["integrity_codes"]
    )
    assert availability_mutated_case["declared_selected_tactic_id"] == original_tactic
    assert availability_mutated_case["computed_selected_tactic_id"] == fallback_tactic
    assert availability_mutated_case["selected_tactic_id"] == fallback_tactic
    assert availability_mutated_case["expected_tactic_id"] == original_tactic
    assert availability_mutated_case["preferred_unavailable_tactic_ids"] == [
        original_tactic
    ]
    assert availability_mutated_case["blocked_unavailable_tactic_ids"] == [
        original_tactic
    ]
    assert availability_mutated_case["expectation_met"] is False
    assert {
        row["tactic_id"]: (row["decision"], row["classifier"])
        for row in availability_mutated_case["decisions"]
    } == {
        fallback_tactic: ("allow", "TARGET_SHAPE_ADMISSIBLE"),
        original_tactic: ("reject", "UNAVAILABLE_TACTIC"),
    }
    assert any(
        finding["error_code"]
        == "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED"
        and finding["subject_id"] == original_tactic
        and finding["negative_case_id"] == source_case_id
        for finding in availability_mutated["findings"]
    )

    for tactic in portfolio_payload["tactics"]:
        if tactic["tactic_id"] == fallback_tactic:
            tactic["availability_status"] = "unavailable"
            break
    else:
        raise AssertionError("expected fallback tactic in target-shape portfolio")
    portfolio_path.write_text(
        json.dumps(portfolio_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    no_selection = source_body_floor.run_routing_bundle(
        mutated_input,
        tmp_path / "no_selection_receipts",
        command="pytest",
    )

    no_selection_cases = {
        row["route_case_id"]: row for row in no_selection["scored_route_cases"]
    }
    no_selection_case = no_selection_cases[source_case_id]
    assert no_selection["status"] == "blocked"
    assert no_selection_case["declared_selected_tactic_id"] == original_tactic
    assert no_selection_case["computed_selected_tactic_id"] == ""
    assert no_selection_case["selected_tactic_id"] == ""
    assert no_selection_case["expected_tactic_id"] == original_tactic
    assert no_selection_case["selection_basis"] == "no_available_allowed_tactic"
    assert set(no_selection_case["preferred_unavailable_tactic_ids"]) == {
        original_tactic,
        fallback_tactic,
    }
    assert "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED" in (
        no_selection_case["integrity_codes"]
    )


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
    assert result["route_case_count"] == 7
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
    assert card["route_case_count"] == 7
    assert card["selected_tactic_ids"] == ["decide", "omega", "rfl", "simp_all"]
    assert len(card["shape_decision_summary"]) == 7
    bool_card = next(
        row
        for row in card["shape_decision_summary"]
        if row["route_case_id"] == "ring2_bool_not_not_route"
    )
    assert bool_card["computed_selected_tactic_id"] == "decide"
    assert bool_card["selected_tactic_id"] == "decide"
    assert "shape_preferred_tactic_ids" not in bool_card
    unknown_card = next(
        row
        for row in card["shape_decision_summary"]
        if row["route_case_id"] == "synthetic_unknown_shape_default_fallback_route"
    )
    assert unknown_card["selection_basis"] == "unknown_shape_default_preference"
    assert unknown_card["computed_selected_tactic_id"] == "rfl"
    mathlib_card = next(
        row
        for row in card["shape_decision_summary"]
        if row["route_case_id"]
        == "synthetic_mathlib_preferred_unavailable_fallback_route"
    )
    assert mathlib_card["preferred_unavailable_tactic_ids"] == ["aesop"]
    assert mathlib_card["computed_selected_tactic_id"] == "simp_all"
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


def test_target_shape_tactic_routing_exported_source_modules_are_digest_verified() -> None:
    manifest = json.loads((EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 4
    assert len(manifest["modules"]) == 4

    repo_root = MICROCOSM_ROOT.parent
    for module in manifest["modules"]:
        source = repo_root / module["source_ref"]
        target = repo_root / module["target_ref"]
        source_digest = _sha256_prefixed(module.get("source_sha256") or module["sha256"])
        target_digest = _sha256_prefixed(module.get("target_sha256") or module["sha256"])
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == source_digest
        assert _sha256(target) == target_digest
        if module["source_to_target_relation"] == "exact_copy":
            assert source_digest == target_digest
        else:
            assert module["source_to_target_relation"] == (
                "verified_public_safe_private_path_rewrite"
            )
            assert source_digest != target_digest
            assert module["verification_mode"] == "verified_light_edit_recipe"
            assert module["public_safe_transform"]["body_text_in_receipt"] is False
            assert Path.home().as_posix() not in target.read_text(encoding="utf-8")
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
