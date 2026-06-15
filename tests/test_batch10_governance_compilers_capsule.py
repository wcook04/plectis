from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch10_governance_compilers_capsule import (
    AUTHORITY_CEILING,
    CASE_VERDICT_AUTHORITY,
    EXPECTED_MECHANISMS,
    EXPECTED_NEGATIVE_CASES,
    MECHANISM_CLASSIFICATIONS,
    MECHANISM_SOURCE_REFS,
    NEGATIVE_CASE_BINDINGS,
    _blocker_class,
    _path_overlaps,
    _persona_results_from_public_artifact,
    _public_artifact_fixture_docs,
    _reviewer_decision,
    _reviewer_gauntlet_matrix,
    _route_quality_from_public_artifact,
    _status_from_requirements,
    classify_latest_user_intent,
    evaluate_negative_case,
    result_card,
    run,
    run_batch10_governance_compilers_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch10_governance_compilers_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch10_governance_compilers_capsule/exported_batch10_governance_compilers_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _load_source_module(relative_path: str, module_name: str) -> Any:
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    spec = importlib.util.spec_from_file_location(module_name, SOURCE_ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def _write_public_artifact_fixture(root: Path, docs: dict[str, str]) -> None:
    for rel_path, text in docs.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch10_governance_compilers_capsule",
        public_root / "examples/batch10_governance_compilers_capsule",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch10_governance_compilers_capsule",
        public_root / "fixtures/first_wave/batch10_governance_compilers_capsule",
    )
    return public_root / "fixtures/first_wave/batch10_governance_compilers_capsule/input"


def test_batch10_governance_compilers_capsule_runs_all_mechanisms(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_governance_compilers_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch10_governance_compilers_capsule_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert set(exercise["mechanism_ids"]) == set(EXPECTED_MECHANISMS)
    assert exercise["passed_mechanism_count"] == len(EXPECTED_MECHANISMS) - 1
    assert exercise["blocked_binding_repair_count"] == 1

    by_mechanism = {row["mechanism_id"]: row for row in exercise["mechanisms"]}
    assert by_mechanism["mutation_governance_intent_gate"]["negative_intent"]["prohibit_file_writes"] is True
    assert by_mechanism["publication_manifest_selector_contract_verifier"]["hard_exclude_rejected"] is True
    assert by_mechanism["finance_no_lookahead_temporal_contract"]["invalid_horizon_rejected"] is True
    assert by_mechanism["session_dependency_wave_executor"]["node_states"]["C"] == "skipped"
    assert by_mechanism["role_aware_dag_block_propagation"]["quality_error_softened"] is True
    reviewer_gauntlet = by_mechanism["flagship_reviewer_persona_gauntlet_adjudicator"]
    assert reviewer_gauntlet["persona_ids"] == [
        "cold_cloner",
        "programming_systems_reviewer",
        "agent_infra_reviewer",
        "safety_evaluator_reviewer",
        "substrate_skeptic",
        "visual_first_reviewer",
    ]
    assert reviewer_gauntlet["persona_status_counts"] == {"pass": 6, "warn": 0, "fail": 0}
    assert set(reviewer_gauntlet["route_quality"].values()) == {"pass"}
    assert reviewer_gauntlet["decision"] == "report_only_public_proof_smoke_pass"
    assert reviewer_gauntlet["missing_boundary_persona_id"] == "safety_evaluator_reviewer"
    assert reviewer_gauntlet["missing_boundary_patches_required"] == ["repair boundary_doc_exists"]
    assert by_mechanism["weighted_lane_width_apportionment_binding_repair"]["disposition"] == "under_bound_repair_deferred_to_batch9_claim"
    assert exercise["integrity_summary"]["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert exercise["integrity_summary"]["computed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert exercise["integrity_summary"]["fixture_verdict_echo_risk_count"] == 0
    assert exercise["integrity_summary"]["under_bound_binding_repair_count"] == 1
    matrix = {row["mechanism_id"]: row for row in exercise["integrity_matrix"]}
    assert set(matrix) == set(EXPECTED_MECHANISMS)
    assert matrix["weighted_lane_width_apportionment_binding_repair"]["classification"] == "under_bound_binding_repair"
    assert matrix["weighted_lane_width_apportionment_binding_repair"]["current_action"] == "block"
    for row in matrix.values():
        assert row["negative_verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert row["fixture_verdict_echo_risk"] is False
        assert row["negative_result_computed"] is True
        assert row["source_evidence"]
        assert row["negative_cases"][0]["probe_status"] == "pass"
        assert row["negative_cases"][0]["probe_input_digest"]
    assert result["body_in_receipt"] is False


def test_batch10_governance_compilers_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch10_governance_compilers_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch10_governance_compilers_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch10_governance_compilers_capsule_bundle"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["source_module_manifest"]["module_count"] == 10
    assert result["exercise"]["copied_macro_source_module_count"] == 10
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_governance_compilers_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch10_governance_compilers_capsule/"
        "exported_batch10_governance_compilers_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch10_governance_compilers_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "batch10_governance_compilers_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_source_modules_are_exact_or_declared_public_refactors() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 10
    assert manifest["source_faithful_public_refactors"][0]["mechanism_id"] == (
        "publication_manifest_selector_contract_verifier"
    )

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


def test_batch10_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_governance_compilers_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert card["source_module_count"] == 10
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)


def test_batch10_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert payload["verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert payload["mechanism_id"] == NEGATIVE_CASE_BINDINGS[case_id]["mechanism_id"]
        assert payload["computed_path"] == NEGATIVE_CASE_BINDINGS[case_id]["computed_path"]
        assert payload["expected_computed_value"] is True
        assert isinstance(payload["probe_input"], dict)
        assert payload["probe_input"] == NEGATIVE_CASE_BINDINGS[case_id]["input_shape"]
        assert payload["body_in_receipt"] is False


def test_batch10_integrity_matrix_binds_source_evidence_and_classifications(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_governance_compilers_capsule",
        command="pytest",
    )

    exercise = result["exercise"]
    assert exercise["integrity_summary"]["source_faithful_refactor_count"] == 1
    assert exercise["integrity_summary"]["under_bound_binding_repair_count"] == 1

    expected_default = "exact_macro_body_copied_but_port_exercises_refactor"
    matrix = {row["mechanism_id"]: row for row in exercise["integrity_matrix"]}
    assert set(matrix) == set(EXPECTED_MECHANISMS)

    for mechanism_id, row in matrix.items():
        expected_classification = MECHANISM_CLASSIFICATIONS.get(
            mechanism_id,
            expected_default,
        )
        assert row["classification"] == expected_classification
        assert row["current_action"] in {"keep", "block"}
        assert row["negative_result_computed"] is True
        assert row["fixture_verdict_echo_risk"] is False
        assert len(row["negative_cases"]) == 1

        case = row["negative_cases"][0]
        binding = NEGATIVE_CASE_BINDINGS[case["case_id"]]
        assert case["computed_path"] == binding["computed_path"]
        assert case["computed"] is True
        assert case["probe_status"] == "pass"
        assert case["probe_input_digest"]
        assert case["verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert case["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert case["body_in_receipt"] is False

        evidence = row["source_evidence"]
        assert {item["source_ref"] for item in evidence} == set(
            MECHANISM_SOURCE_REFS[mechanism_id]
        )
        for item in evidence:
            assert item["body_in_receipt"] is False
            if expected_classification == "source_faithful_refactor_read_verified_only":
                assert item["source_to_target_relation"] == (
                    "source_faithful_public_refactor_private_path_literal_removed"
                )
                assert item["digest_status"] == "source_digest_recorded_target_is_public_refactor"
                assert item["body_copied"] is False
                assert item["rewrite_recipe"]
            elif expected_classification == "under_bound_binding_repair":
                assert item["source_to_target_relation"] == "not_batch10_body_import"
                assert item["digest_status"] == "external_binding_required"
                assert item["body_copied"] is False
                assert row["current_action"] == "block"
            else:
                assert item["source_to_target_relation"] == "exact_copy"
                assert item["digest_status"] == "match"
                assert item["missing_required_anchor_count"] == 0
                assert item["body_copied"] is True


def test_batch10_low_dependency_python_ports_match_source_helpers() -> None:
    mutation_governance = _load_source_module(
        "system/lib/mutation_governance.py",
        "batch10_source_mutation_governance",
    )
    action_quote = _load_source_module(
        "system/lib/action_quote.py",
        "batch10_source_action_quote",
    )
    reviewer = _load_source_module(
        "tools/meta/dissemination/build_public_microcosm_flagship_reviewer_gauntlet.py",
        "batch10_source_reviewer_gauntlet",
    )
    release = _load_source_module(
        "tools/meta/dissemination/release_public_toggle_closure_map.py",
        "batch10_source_release_toggle",
    )

    messages = [
        "please implement this parser fix",
        "diagnose the attached transcript and pattern ledger seed",
        "summarize the prior run",
        "continue",
    ]
    for message in messages:
        assert classify_latest_user_intent(message) == mutation_governance.classify_latest_user_intent(message)

    assert _path_overlaps("microcosm-substrate/src/a.py", "microcosm-substrate/src") == (
        action_quote._path_overlaps("microcosm-substrate/src/a.py", "microcosm-substrate/src")
    )
    assert _status_from_requirements({"a": True, "b": False}) == reviewer._status_from_requirements(
        {"a": True, "b": False}
    )
    assert _blocker_class("public_toggle_no_go", {}) == release._blocker_class("public_toggle_no_go", {})
    assert _blocker_class("operator_public_approval_absent", {}) == release._blocker_class(
        "operator_public_approval_absent",
        {},
    )


def test_batch10_reviewer_gauntlet_exercises_six_source_personas(tmp_path: Path) -> None:
    reviewer = _load_source_module(
        "tools/meta/dissemination/build_public_microcosm_flagship_reviewer_gauntlet.py",
        "batch10_source_reviewer_gauntlet_personas",
    )
    docs = _public_artifact_fixture_docs()
    _write_public_artifact_fixture(tmp_path, docs)

    local_personas = _persona_results_from_public_artifact(docs)
    source_personas = reviewer._persona_results(tmp_path)
    assert [row["persona_id"] for row in local_personas] == [
        "cold_cloner",
        "programming_systems_reviewer",
        "agent_infra_reviewer",
        "safety_evaluator_reviewer",
        "substrate_skeptic",
        "visual_first_reviewer",
    ]
    assert [(row["persona_id"], row["status"]) for row in local_personas] == [
        (row["persona_id"], row["status"]) for row in source_personas
    ]
    assert _route_quality_from_public_artifact(docs) == reviewer._route_quality(tmp_path)
    assert _reviewer_decision(
        [{"command_id": "demo_substrate", "status": "pass"}],
        local_personas,
        _route_quality_from_public_artifact(docs),
    ) == reviewer.REPORT_DECISION

    missing_boundary_docs = _public_artifact_fixture_docs(boundary_doc_exists=False)
    _write_public_artifact_fixture(tmp_path, missing_boundary_docs)
    local_missing = _persona_results_from_public_artifact(missing_boundary_docs)
    source_missing = reviewer._persona_results(tmp_path)
    assert [(row["persona_id"], row["status"]) for row in local_missing] == [
        (row["persona_id"], row["status"]) for row in source_missing
    ]
    matrix = _reviewer_gauntlet_matrix()
    assert matrix["status"] == "pass"
    assert matrix["persona_count"] == 6
    assert matrix["missing_boundary_status"] == "warn"


def test_batch10_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        payload["computed_path"] = "bogus_declared_computed_path"
        payload["expected_computed_value"] = False
        payload["fixture_role"] = "forged_fixture_verdict"
        payload["verdict_authority"] = "declared_label_attempt"
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/batch10_governance_compilers_capsule",
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


def test_batch10_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]


def test_batch10_negative_case_probe_input_change_blocks_fixture_run(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    case_id = "mutation_status_intent_blocks_writes"
    case_path = fixture / f"{case_id}.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["probe_input"]["latest_user_message"] = "please implement this parser fix"
    payload["probe_input"]["requested_route"] = "normal_task"
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    direct = evaluate_negative_case(case_id, fixture, EXPECTED_NEGATIVE_CASES[case_id])
    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/batch10_governance_compilers_capsule",
    )
    semantic_row = next(
        row for row in result["negative_case_semantics"] if row["case_id"] == case_id
    )
    matrix = {
        row["mechanism_id"]: row
        for row in result["exercise"]["integrity_matrix"]
    }
    negative_case = matrix["mutation_governance_intent_gate"]["negative_cases"][0]

    assert direct["status"] == "pass"
    assert result["status"] == "blocked"
    assert semantic_row["status"] == "pass"
    assert negative_case["computed"] is False
    assert case_id not in result["observed_negative_cases"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in result["error_codes"]
