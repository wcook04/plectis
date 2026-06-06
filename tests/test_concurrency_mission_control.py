from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.concurrency_mission_control import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    classify_concurrency_closure_state_lens,
    classify_generated_surface_claim_lens,
    result_card,
    run,
    run_concurrency_mission_control_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/concurrency_mission_control/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/concurrency_mission_control/exported_concurrency_mission_control_bundle"
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
        MICROCOSM_ROOT / "examples/concurrency_mission_control",
        public_root / "examples/concurrency_mission_control",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/concurrency_mission_control",
        public_root / "fixtures/first_wave/concurrency_mission_control",
    )
    return public_root / "fixtures/first_wave/concurrency_mission_control/input"


def test_concurrency_mission_control_runs_copied_builder(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/concurrency_mission_control",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/concurrency_mission_control_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    assert result["semantic_negative_case_evaluator_used"] is True

    exercise = result["exercise"]
    assert exercise["engine_count"] == len(EXPECTED_ENGINES)
    assert set(exercise["engine_ids"]) == set(EXPECTED_ENGINES)
    assert all(row["status"] == "pass" for row in exercise["engines"])

    by_engine = {row["engine_id"]: row for row in exercise["engines"]}
    original = by_engine["mission_transaction_original_builder"]
    assert original["result_status"] == "ok"
    assert original["case_count"] == 9
    assert original["accept_count"] == 1
    assert original["block_count"] >= 8
    assert original["provider_repair_bridge_status"] == "ok"
    assert original["task_ledger_residual_replay_bridge_status"] == "ok"
    assert original["work_metabolism_bridge_status"] == "ok"

    matrix = by_engine["failure_matrix_gate"]
    assert matrix["missing_failure_classes"] == []
    assert "write_scope_conflict" in matrix["observed_failure_classes"]

    membrane = by_engine["bridge_authority_membrane"]
    assert membrane["authority_collapse_count"] == 0
    assert membrane["bridge_statuses_pass"] is True
    assert "private_work_ledger_session_export" in membrane["forbidden_claims_present"]

    seed_speed = by_engine["work_ledger_seed_speed_gate"]
    assert seed_speed["snapshot_schema_version"] == "work_ledger_seed_speed_status_v1"
    assert seed_speed["checks"]["active_shape"] is True
    assert seed_speed["checks"]["collision_gate"] is True
    assert seed_speed["session_collision_count"] == 0
    assert seed_speed["claim_collision_count"] == 0
    assert seed_speed["heartbeat_participation_status"] == "complete"
    assert seed_speed["source_refs_bound"] is True

    generated_surface = by_engine["generated_surface_claim_lens"]
    assert generated_surface["status"] == "pass"
    assert generated_surface["missing_classifications"] == []
    assert set(generated_surface["observed_classifications"]) == {
        "owned_live",
        "owned_stale",
        "unowned_generated_drift",
        "unrelated_dirty_state",
    }
    by_case = {row["case_id"]: row for row in generated_surface["rows"]}
    assert by_case["route_projection_drift_owned_live"]["allowed_action"] == (
        "do_not_patch_from_sibling_lane"
    )
    assert by_case["architecture_projection_drift_unowned"]["allowed_action"] == (
        "claim_builder_lane_then_regenerate_and_validate"
    )

    closure_state = by_engine["closure_state_lens"]
    assert closure_state["status"] == "pass"
    assert closure_state["missing_classifications"] == []
    assert set(closure_state["observed_classifications"]) == {
        "closed_and_committed",
        "closed_uncommitted_authority",
        "closed_validation_deferred",
        "false_residual_stale",
        "owned_live_handoff",
        "owned_stale_reentry",
        "unowned_generated_drift",
    }
    by_closure_case = {row["case_id"]: row for row in closure_state["rows"]}
    assert by_closure_case["route_cap_closed_uncommitted"]["allowed_action"] == (
        "do_not_stage_shared_append_logs; rely_on_event_authority_and_reenter_scoped_commit"
    )
    assert by_closure_case["heavy_pytest_deferred_by_host_pressure"][
        "classification"
    ] == "closed_validation_deferred"
    assert by_closure_case["overbroad_microcosm_path_preflight"][
        "allowed_action"
    ] == "narrow_path_scope_or_coordinate_owner"
    assert result["body_in_receipt"] is False


def test_concurrency_mission_control_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_concurrency_mission_control_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/concurrency_mission_control",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_concurrency_mission_control_bundle"
    assert result["source_module_manifest"]["module_count"] == 7
    assert result["exercise"]["copied_macro_source_module_count"] == 7
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_concurrency_mission_control_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/concurrency_mission_control/"
        "exported_concurrency_mission_control_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_concurrency_mission_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/concurrency_mission_control",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["receipt_body_scan"]["status"] == "pass"


def test_concurrency_mission_control_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 7

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


def test_concurrency_mission_control_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/concurrency_mission_control",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["source_module_count"] == 7
    assert card["work_ledger_seed_speed_status"] == "pass"
    assert card["generated_surface_claim_lens_status"] == "pass"
    assert card["closure_state_lens_status"] == "pass"
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)


def test_concurrency_mission_control_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_concurrency_mission_control_negative_cases_are_semantic_not_declared_labels(
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
        tmp_path / "microcosm-substrate/receipts/first_wave/concurrency_mission_control",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(row["semantic_evaluator_used"] for row in result["negative_case_semantics"])
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "CONCURRENCY_MISSION_CONTROL_SEED_ROOT_MISSING" in result["error_codes"]
    assert "CONCURRENCY_MISSION_CONTROL_PROVIDER_BRIDGE_BLOCKED" in result["error_codes"]
    assert "CONCURRENCY_MISSION_CONTROL_AUTHORITY_COLLAPSE" in result["error_codes"]
    assert "CONCURRENCY_MISSION_CONTROL_PRIVATE_RUNTIME_OVERCLAIM" in result["error_codes"]
    assert (
        "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COLLISION_UNRESOLVED"
        in result["error_codes"]
    )


def test_generated_surface_claim_lens_classifies_owner_states() -> None:
    cases = json.loads(
        (FIXTURE_INPUT / "concurrency_mission_control_exercise_manifest.json").read_text(
            encoding="utf-8"
        )
    )["generated_surface_claim_lens"]["cases"]

    rows = {case["case_id"]: classify_generated_surface_claim_lens(case) for case in cases}

    assert rows["route_projection_drift_owned_live"]["classification"] == "owned_live"
    assert rows["route_projection_drift_owned_live"]["drift_authority"] == "owner_lane"
    assert rows["route_projection_drift_owned_live"]["owner_session_id"] == (
        "public_projection_owner"
    )
    assert rows["mixed_generated_drift_live_owner_and_unowned"][
        "classification"
    ] == "owned_live"
    assert rows["mixed_generated_drift_live_owner_and_unowned"][
        "unowned_generated_surface_drift_paths"
    ] == ["microcosm-substrate/ARCHITECTURE.md"]
    assert rows["organ_projection_drift_owned_stale"]["classification"] == "owned_stale"
    assert rows["organ_projection_drift_owned_stale"]["allowed_action"] == (
        "release_or_supersede_owner_claim_then_regenerate"
    )
    assert rows["architecture_projection_drift_unowned"]["classification"] == (
        "unowned_generated_drift"
    )
    assert rows["non_projection_dirty_state"]["classification"] == "unrelated_dirty_state"
    assert all(row["body_in_receipt"] is False for row in rows.values())


def test_concurrency_mission_control_rejects_claim_topology_mutation_over_baked_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    manifest_path = fixture / "concurrency_mission_control_exercise_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    good = run(fixture, tmp_path / "receipts/good/concurrency_mission_control")
    good_engines = {row["engine_id"]: row for row in good["exercise"]["engines"]}
    good_generated_rows = {
        row["case_id"]: row for row in good_engines["generated_surface_claim_lens"]["rows"]
    }
    good_closure_rows = {
        row["case_id"]: row for row in good_engines["closure_state_lens"]["rows"]
    }

    assert good["status"] == "pass"
    assert good_generated_rows["route_projection_drift_owned_live"][
        "classification"
    ] == "owned_live"
    assert good_closure_rows["generated_route_drift_live_owner"][
        "classification"
    ] == "owned_live_handoff"

    generated_case = next(
        case
        for case in manifest["generated_surface_claim_lens"]["cases"]
        if case["case_id"] == "route_projection_drift_owned_live"
    )
    closure_case = next(
        case
        for case in manifest["closure_state_lens"]["cases"]
        if case["case_id"] == "generated_route_drift_live_owner"
    )
    generated_case["session_cards"] = []
    generated_case["claim_rows"] = []
    generated_case["expected_classification"] = "owned_live"
    generated_case["expected_allowed_action"] = "do_not_patch_from_sibling_lane"
    closure_case["session_cards"] = []
    closure_case["claim_rows"] = []
    closure_case["expected_classification"] = "owned_live_handoff"
    closure_case["expected_allowed_action"] = "handoff_to_live_owner_or_wait_for_release"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    bad = run(fixture, tmp_path / "receipts/bad/concurrency_mission_control")
    bad_engines = {row["engine_id"]: row for row in bad["exercise"]["engines"]}
    bad_generated = bad_engines["generated_surface_claim_lens"]
    bad_closure = bad_engines["closure_state_lens"]
    bad_generated_rows = {row["case_id"]: row for row in bad_generated["rows"]}
    bad_closure_rows = {row["case_id"]: row for row in bad_closure["rows"]}

    assert bad["status"] == "blocked"
    assert bad_generated["status"] == "blocked"
    assert bad_closure["status"] == "blocked"
    assert bad_generated_rows["route_projection_drift_owned_live"][
        "classification"
    ] == "unowned_generated_drift"
    assert bad_generated_rows["route_projection_drift_owned_live"][
        "allowed_action"
    ] == "claim_builder_lane_then_regenerate_and_validate"
    assert bad_closure_rows["generated_route_drift_live_owner"][
        "classification"
    ] == "unowned_generated_drift"
    assert bad_closure_rows["generated_route_drift_live_owner"][
        "allowed_action"
    ] == "claim_builder_lane_then_regenerate_and_validate"
    assert good_generated_rows["route_projection_drift_owned_live"][
        "classification"
    ] != bad_generated_rows["route_projection_drift_owned_live"]["classification"]
    assert good_closure_rows["generated_route_drift_live_owner"][
        "classification"
    ] != bad_closure_rows["generated_route_drift_live_owner"]["classification"]
    assert {
        finding["error_code"]
        for finding in bad_generated["findings"]
    } == {
        "CONCURRENCY_MISSION_CONTROL_GENERATED_SURFACE_CLASSIFICATION_MISMATCH",
        "CONCURRENCY_MISSION_CONTROL_GENERATED_SURFACE_ACTION_MISMATCH",
    }
    assert {
        finding["error_code"]
        for finding in bad_closure["findings"]
    } == {
        "CONCURRENCY_MISSION_CONTROL_CLOSURE_STATE_CLASSIFICATION_MISMATCH",
        "CONCURRENCY_MISSION_CONTROL_CLOSURE_STATE_ACTION_MISMATCH",
    }


def test_concurrency_mission_control_recomputes_duplicate_claim_topology(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    manifest_path = fixture / "concurrency_mission_control_exercise_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    surface = manifest["work_ledger_seed_speed_surface"]
    primary_claim = next(
        row
        for row in surface["claim_rows"]
        if row["claim_id"] == "claim_public_concurrency_controller"
    )
    duplicate_claim = dict(primary_claim)
    duplicate_claim.update(
        {
            "claim_id": "claim_duplicate_public_concurrency_controller",
            "session_id": "public_microcosm_sibling",
            "collision_count": 1,
        }
    )
    surface["claim_rows"].append(duplicate_claim)
    surface["counts"]["claim_collisions"] = 0
    surface["expected_claim_collision_count"] = 0
    surface["claim_collisions"] = []
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(fixture, tmp_path / "receipts/duplicate_claim/concurrency_mission_control")
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}
    seed_speed = by_engine["work_ledger_seed_speed_gate"]

    assert result["status"] == "blocked"
    assert seed_speed["status"] == "blocked"
    assert seed_speed["checks"]["collision_gate"] is False
    assert seed_speed["claim_collision_count"] == 0
    assert seed_speed["session_collision_count"] == 1
    assert {
        finding["error_code"]
        for finding in seed_speed["findings"]
    } == {"CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COLLISION_UNRESOLVED"}


def test_closure_state_lens_classifies_closure_and_owner_states() -> None:
    cases = json.loads(
        (FIXTURE_INPUT / "concurrency_mission_control_exercise_manifest.json").read_text(
            encoding="utf-8"
        )
    )["closure_state_lens"]["cases"]

    rows = {case["case_id"]: classify_concurrency_closure_state_lens(case) for case in cases}

    assert rows["route_projection_closed_and_committed"]["classification"] == (
        "closed_and_committed"
    )
    assert rows["route_cap_closed_uncommitted"]["classification"] == (
        "closed_uncommitted_authority"
    )
    assert rows["heavy_pytest_deferred_by_host_pressure"]["classification"] == (
        "closed_validation_deferred"
    )
    assert rows["generated_route_drift_live_owner"]["classification"] == (
        "owned_live_handoff"
    )
    assert rows["generated_route_drift_live_owner"]["owner_session_id"] == (
        "public_projection_owner"
    )
    assert rows["mixed_generated_drift_live_owner_and_unowned"][
        "classification"
    ] == "owned_live_handoff"
    assert rows["mixed_generated_drift_live_owner_and_unowned"][
        "allowed_action"
    ] == "handoff_to_live_owner_or_wait_for_release"
    assert rows["generated_organs_drift_stale_owner"]["classification"] == (
        "owned_stale_reentry"
    )
    assert rows["generated_architecture_drift_unowned"]["classification"] == (
        "unowned_generated_drift"
    )
    assert rows["old_drift_residual_after_clean_atlas_check"]["classification"] == (
        "false_residual_stale"
    )
    assert rows["overbroad_microcosm_path_preflight"]["classification"] == (
        "owned_live_handoff"
    )
    assert rows["overbroad_microcosm_path_preflight"]["allowed_action"] == (
        "narrow_path_scope_or_coordinate_owner"
    )
    assert all(row["body_in_receipt"] is False for row in rows.values())
