from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import materials_chemistry_closed_loop_lab_safety_replay
from microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD,
    NUMERIC_REPLAY_ASSAY_VALUE_FIELD,
    NUMERIC_REPLAY_MIN_SAFETY_GATE,
    NUMERIC_REPLAY_SAFETY_GATE_FIELD,
    NUMERIC_REPLAY_SELECTION_RULE,
    NUMERIC_REPLAY_VERDICT_BASIS,
    main,
    run,
    run_lab_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/materials_chemistry_closed_loop_lab_safety_replay/"
    "exported_materials_lab_safety_bundle"
)
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"


def _copy_fixture_input(tmp_path: Path, case_id: str) -> Path:
    public_root = tmp_path / case_id / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    target = (
        public_root
        / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input"
    )
    shutil.copytree(FIXTURE_INPUT, target)
    return target


def _mutate_json(path: Path, mutator: Any) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutator(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _copy_bundle_input(tmp_path: Path, case_id: str) -> Path:
    public_root = tmp_path / case_id / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/materials_chemistry_closed_loop_lab_safety_replay",
        public_root / "examples/materials_chemistry_closed_loop_lab_safety_replay",
    )
    return (
        public_root
        / "examples/materials_chemistry_closed_loop_lab_safety_replay/"
        "exported_materials_lab_safety_bundle"
    )


def _copy_live_source_refs_for_bundle(bundle: Path) -> None:
    public_root = bundle.parents[2]
    manifest = json.loads((bundle / "source_module_manifest.json").read_text())
    for row in manifest["modules"]:
        source_ref = row["source_ref"]
        source = SOURCE_ROOT / source_ref
        target = public_root.parent / source_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


BASELINE_NUMERIC_PROXY_SCORES = {
    "mat_polymer_membrane_001": {
        "safety_gate": 0.94,
        "assay_proxy": 0.92,
        "active_learning": 0.90,
    },
    "mat_solid_electrolyte_002": {
        "safety_gate": 0.91,
        "assay_proxy": 0.84,
        "active_learning": 0.81,
    },
    "mat_catalyst_support_003": {
        "safety_gate": 0.85,
        "assay_proxy": 0.78,
        "active_learning": 0.74,
    },
    "mat_sorbent_surface_004": {
        "safety_gate": 0.88,
        "assay_proxy": 0.70,
        "active_learning": 0.66,
    },
}


def _write_bundle_numeric_replay(
    bundle: Path,
    *,
    score_overrides: dict[str, dict[str, float]] | None = None,
    expected_selected: str = "mat_polymer_membrane_001",
) -> None:
    scores = {
        candidate_id: dict(values)
        for candidate_id, values in BASELINE_NUMERIC_PROXY_SCORES.items()
    }
    for candidate_id, values in (score_overrides or {}).items():
        scores.setdefault(candidate_id, {}).update(values)

    def set_policy(payload: dict[str, Any]) -> None:
        numeric_policy = payload.setdefault("numeric_replay", {})
        numeric_policy.update(
            {
                "expected_selected_candidate_material_id": expected_selected,
                "selection_rule": NUMERIC_REPLAY_SELECTION_RULE,
                "minimum_safety_gate_score": NUMERIC_REPLAY_MIN_SAFETY_GATE,
            }
        )

    def set_candidate_scores(payload: dict[str, Any]) -> None:
        for row in payload["candidate_materials"]:
            values = scores[str(row["candidate_material_id"])]
            row[NUMERIC_REPLAY_SAFETY_GATE_FIELD] = values["safety_gate"]

    def set_assay_scores(payload: dict[str, Any]) -> None:
        for row in payload["simulator_assays"]:
            values = scores[str(row["candidate_material_ref"])]
            row[NUMERIC_REPLAY_ASSAY_VALUE_FIELD] = values["assay_proxy"]

    def set_decision_scores(payload: dict[str, Any]) -> None:
        for row in payload["active_learning_decisions"]:
            values = scores[str(row["candidate_material_ref"])]
            row[NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD] = values["active_learning"]

    _mutate_json(bundle / "replay_policy.json", set_policy)
    _mutate_json(bundle / "candidate_materials.json", set_candidate_scores)
    _mutate_json(bundle / "simulator_assays.json", set_assay_scores)
    _mutate_json(bundle / "active_learning_decisions.json", set_decision_scores)


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


def test_materials_chemistry_digest_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source.txt"
    body = b"materials lab source module body" * 4096
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("materials lab source module digest must stream")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert materials_chemistry_closed_loop_lab_safety_replay._sha256(source) == (
        "sha256:" + hashlib.sha256(body).hexdigest()
    )


def test_materials_chemistry_lab_safety_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["selected_route_id"] == "materials_chemistry_closed_loop_lab_safety_replay"
    assert result["public_surface_name"] == (
        "materials_chemistry_artifact_safety_refusal_validator"
    )
    assert result["surface_reframe"]["reframe_reason"] == (
        "no_wetlab_loop_authorized_artifact_safety_refusal_validation_only"
    )
    assert result["product_path_role"] == "artifact_safety_refusal_validator"
    assert result["materials_lab_safety_summary"]["candidate_material_count"] == 4
    assert result["materials_lab_safety_summary"]["experiment_count"] == 4
    assert result["materials_lab_safety_summary"]["simulator_assay_count"] == 4
    assert result["materials_lab_safety_summary"]["active_learning_decision_count"] == 4
    assert result["materials_lab_safety_summary"]["wetlab_protocol_export_count"] == 0
    assert result["materials_lab_safety_summary"]["robot_command_count"] == 0
    assert result["safety_verdict"]["status"] == "pass"
    assert result["safety_verdict"]["verdict"] == "public_safe_simulator_replay_accepted"
    assert result["safety_verdict"]["derived_from"]["policy_passed"] is True
    assert result["safety_verdict"]["derived_from"]["positive_finding_codes"] == []
    assert result["body_import_status"] == "source_faithful_refactor_landed"
    assert result["body_import_classification"] == "source_faithful_refactor"
    assert result["body_import_verification"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"
    replay = result["public_lab_evolve_replay"]
    assert replay["status"] == "pass"
    assert replay["summary"]["replay_case_count"] == 4
    assert replay["summary"]["boundary_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert replay["summary"]["source_capsule_count"] == 12
    assert (
        "self-indexing-cognitive-substrate/src/idea_microcosm/"
        "lab_evolve_failure_replay_specimen.py"
    ) in replay["source_refs"]
    assert replay["body_in_receipt"] is False
    assert result["negative_case_summary"]["expected_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["observed_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["authority_ceiling"]["wetlab_protocol_authorized"] is False
    assert result["authority_ceiling"]["hazardous_synthesis_authorized"] is False
    assert result["authority_ceiling"]["reagent_amounts_authorized"] is False
    assert result["authority_ceiling"]["robot_command_authorized"] is False
    assert result["authority_ceiling"]["discovery_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        assert result["negative_case_summary"]["observed_codes"][case_id] == codes


def test_materials_chemistry_safety_verdict_tracks_public_safe_perturbations(
    tmp_path: Path,
) -> None:
    baseline = run(
        FIXTURE_INPUT,
        tmp_path / "baseline/receipts",
        command="pytest",
        acceptance_out=tmp_path / "baseline/acceptance.json",
    )
    baseline_digest = baseline["safety_verdict"]["evidence_digest"]

    cases = [
        (
            "material_target_boundary",
            "candidate_materials.json",
            lambda payload: payload["candidate_materials"][0].update(
                {"controlled_substance_target": True}
            ),
            "MATERIALS_CONTROLLED_OR_BIOACTIVE_TARGET_FORBIDDEN",
        ),
        (
            "hazard_export_boundary",
            "experiment_dag.json",
            lambda payload: payload["experiments"][0].update(
                {"hazardous_synthesis_steps_exported": True}
            ),
            "MATERIALS_HAZARDOUS_SYNTHESIS_FORBIDDEN",
        ),
        (
            "safety_screen_linkage_boundary",
            "experiment_dag.json",
            lambda payload: payload["experiments"][0].update(
                {"safety_screen_ref": "safety_screen:mismatched_public_gate"}
            ),
            "MATERIALS_SAFETY_SCREEN_REF_MISMATCH",
        ),
    ]

    for case_id, file_name, mutator, expected_code in cases:
        input_dir = _copy_fixture_input(tmp_path, case_id)
        _mutate_json(input_dir / file_name, mutator)

        result = run(
            input_dir,
            tmp_path / case_id / "receipts",
            command="pytest",
            acceptance_out=tmp_path / case_id / "acceptance.json",
        )
        summary = result["materials_lab_safety_summary"]
        verdict = result["safety_verdict"]

        assert summary["candidate_material_count"] == 4
        assert summary["experiment_count"] == 4
        assert summary["simulator_assay_count"] == 4
        assert summary["active_learning_decision_count"] == 4
        assert result["status"] == "blocked"
        assert verdict["status"] == "blocked"
        assert verdict["verdict"] == "blocked_public_safety_boundary"
        assert verdict["evidence_digest"] != baseline_digest
        assert expected_code in verdict["derived_from"]["positive_finding_codes"]
        assert expected_code in {
            finding["error_code"] for finding in result["positive_findings"]
        }
        assert result["negative_case_summary"]["expected_missing"] == {}
        assert result["public_lab_evolve_replay"]["summary"]["replay_case_count"] == 4


def test_materials_chemistry_numeric_replay_recomputes_verdict_from_fixture_numbers(
    tmp_path: Path,
) -> None:
    baseline = run(
        FIXTURE_INPUT,
        tmp_path / "numeric_good" / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "numeric_good" / "acceptance.json",
    )

    assert baseline["status"] == "pass"
    assert baseline["numeric_replay"]["status"] == "pass"
    assert baseline["numeric_replay"]["verified_numeric_row_count"] == 4
    assert baseline["numeric_replay"]["selection_rule"] == (
        "max_weighted_public_assay_active_learning_and_safety_gate_score"
    )
    assert baseline["numeric_replay"]["minimum_safety_gate_score"] == 0.7
    assert baseline["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_polymer_membrane_001"
    )
    assert baseline["numeric_replay"]["selected_decision_id"] == "decision_membrane_001"
    assert baseline["numeric_replay"]["selected_next_action_class"] == "simulate_assay"
    assert round(
        baseline["numeric_replay"]["selected_computed_numeric_score"], 3
    ) == 0.917
    assert baseline["numeric_replay"]["selected_score_components"] == {
        "assay_proxy_value": 0.92,
        "active_learning_score": 0.90,
        "safety_gate_score": 0.94,
    }
    assert baseline["realness_rank"] == 3
    assert baseline["realness_rung"] == "R3"
    assert baseline["realness_state"] == "public_safe_numeric_verdict_replay"
    assert baseline["realness_evidence"]["status"] == "pass"
    assert baseline["realness_evidence"]["realness_rank"] == 3
    assert baseline["realness_evidence"]["realness_rung"] == "R3"
    assert baseline["realness_evidence"][
        "verdict_rederived_from_numeric_fixture_content"
    ] is True
    assert baseline["realness_evidence"]["score_backed_rows_bound"] is True
    assert baseline["realness_evidence"]["expected_numeric_row_count"] == 4
    assert baseline["realness_evidence"]["verified_numeric_row_count"] == 4
    assert baseline["realness_evidence"]["selected_candidate_material_id"] == (
        "mat_polymer_membrane_001"
    )
    assert baseline["realness_evidence"]["selected_computed_numeric_score"] == (
        baseline["numeric_replay"]["selected_computed_numeric_score"]
    )
    assert baseline["realness_evidence"]["expected_labels_used_for_selection"] is False
    assert baseline["realness_evidence"]["baked_fixture_label_sufficient"] is False
    assert baseline["realness_evidence"]["authority_ceiling_bound"] is True
    assert baseline["realness_evidence"]["release_authorized"] is False
    assert baseline["numeric_replay"]["verdict_basis"] == NUMERIC_REPLAY_VERDICT_BASIS
    assert baseline["public_lab_evolve_replay"]["status"] == "pass"
    assert baseline["public_lab_evolve_replay"]["numeric_replay"]["status"] == "pass"
    assert baseline["public_lab_evolve_replay"]["numeric_replay"][
        "selected_score_components"
    ] == baseline["numeric_replay"]["selected_score_components"]
    assert baseline["public_lab_evolve_replay"]["numeric_replay"][
        "verdict_basis"
    ] == NUMERIC_REPLAY_VERDICT_BASIS
    assert baseline["public_lab_evolve_replay"]["summary"][
        "numeric_replay_verified_row_count"
    ] == 4
    assert round(
        baseline["public_lab_evolve_replay"]["numeric_replay"][
            "selected_computed_numeric_score"
        ],
        3,
    ) == 0.917
    assert baseline["safety_verdict"]["derived_from"]["numeric_replay"][
        "status"
    ] == "pass"
    assert baseline["safety_verdict"]["derived_from"]["numeric_replay"][
        "selected_score_components"
    ] == {
        "assay_proxy_value": 0.92,
        "active_learning_score": 0.90,
        "safety_gate_score": 0.94,
    }
    assert baseline["safety_verdict"]["derived_from"]["numeric_replay"][
        "verdict_basis"
    ] == NUMERIC_REPLAY_VERDICT_BASIS
    assert baseline["safety_verdict"]["derived_from"][
        "numeric_replay_verdict_basis"
    ] == NUMERIC_REPLAY_VERDICT_BASIS
    baseline_digest = baseline["safety_verdict"]["evidence_digest"]

    low_gate_input = _copy_fixture_input(tmp_path, "numeric_low_safety_gate")
    _mutate_json(
        low_gate_input / "candidate_materials.json",
        lambda payload: payload["candidate_materials"][0].update(
            {NUMERIC_REPLAY_SAFETY_GATE_FIELD: 0.52}
        ),
    )
    low_gate = run(
        low_gate_input,
        tmp_path / "numeric_low_safety_gate" / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "numeric_low_safety_gate" / "acceptance.json",
    )

    assert low_gate["status"] == "blocked"
    assert low_gate["safety_verdict"]["status"] == "blocked"
    assert low_gate["safety_verdict"]["evidence_digest"] != baseline_digest
    assert low_gate["numeric_replay"]["status"] == "blocked"
    assert low_gate["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_solid_electrolyte_002"
    )
    assert low_gate["public_lab_evolve_replay"]["status"] == "blocked"
    assert low_gate["public_lab_evolve_replay"]["numeric_replay"]["status"] == (
        "blocked"
    )
    assert low_gate["public_lab_evolve_replay"]["summary"][
        "numeric_replay_status"
    ] == "blocked"
    assert low_gate["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE",
        "MATERIALS_NUMERIC_REPLAY_SAFETY_GATE_FAILED",
    ]
    assert "MATERIALS_NUMERIC_REPLAY_SAFETY_GATE_FAILED" in low_gate[
        "safety_verdict"
    ]["derived_from"]["positive_finding_codes"]

    moved_pick_input = _copy_fixture_input(tmp_path, "numeric_moved_next_pick")

    def move_sorbent_safety_score(payload: dict[str, Any]) -> None:
        for row in payload["candidate_materials"]:
            if row["candidate_material_id"] == "mat_sorbent_surface_004":
                row[NUMERIC_REPLAY_SAFETY_GATE_FIELD] = 0.93

    def move_sorbent_assay_score(payload: dict[str, Any]) -> None:
        for row in payload["simulator_assays"]:
            if row["candidate_material_ref"] == "mat_sorbent_surface_004":
                row[NUMERIC_REPLAY_ASSAY_VALUE_FIELD] = 0.98

    def move_sorbent_active_learning_score(payload: dict[str, Any]) -> None:
        for row in payload["active_learning_decisions"]:
            if row["candidate_material_ref"] == "mat_sorbent_surface_004":
                row[NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD] = 0.98

    _mutate_json(moved_pick_input / "candidate_materials.json", move_sorbent_safety_score)
    _mutate_json(moved_pick_input / "simulator_assays.json", move_sorbent_assay_score)
    _mutate_json(
        moved_pick_input / "active_learning_decisions.json",
        move_sorbent_active_learning_score,
    )
    _mutate_json(
        moved_pick_input / "replay_policy.json",
        lambda payload: payload["numeric_replay"].update(
            {
                "expected_selected_candidate_material_id": (
                    "mat_sorbent_surface_004"
                )
            }
        ),
    )

    moved_pick = run(
        moved_pick_input,
        tmp_path / "numeric_moved_next_pick" / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "numeric_moved_next_pick" / "acceptance.json",
    )

    assert moved_pick["status"] == "pass"
    assert moved_pick["numeric_replay"]["status"] == "pass"
    assert moved_pick["numeric_replay"]["verified_numeric_row_count"] == 4
    assert moved_pick["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_sorbent_surface_004"
    )
    assert moved_pick["numeric_replay"]["selected_decision_id"] == "decision_sorbent_004"
    assert moved_pick["numeric_replay"]["selected_next_action_class"] == "screen_candidate"
    assert round(
        moved_pick["numeric_replay"]["selected_computed_numeric_score"], 3
    ) == 0.970
    assert moved_pick["public_lab_evolve_replay"]["status"] == "pass"
    assert moved_pick["public_lab_evolve_replay"]["numeric_replay"][
        "selected_candidate_material_id"
    ] == "mat_sorbent_surface_004"
    assert moved_pick["safety_verdict"]["evidence_digest"] != baseline_digest
    assert moved_pick["safety_verdict"]["derived_from"]["numeric_replay"][
        "selected_candidate_material_id"
    ] == "mat_sorbent_surface_004"

    stale_label_input = _copy_fixture_input(tmp_path, "numeric_stale_expected_label")
    _mutate_json(
        stale_label_input / "replay_policy.json",
        lambda payload: payload["numeric_replay"].update(
            {
                "expected_selected_candidate_material_id": (
                    "mat_catalyst_support_003"
                )
            }
        )
    )

    stale_label = run(
        stale_label_input,
        tmp_path / "numeric_stale_expected_label" / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "numeric_stale_expected_label" / "acceptance.json",
    )

    assert stale_label["status"] == "blocked"
    assert stale_label["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_polymer_membrane_001"
    )
    assert stale_label["numeric_replay"][
        "declared_expected_selected_candidate_material_id"
    ] == "mat_catalyst_support_003"
    assert stale_label["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE"
    ]
    assert stale_label["public_lab_evolve_replay"]["status"] == "blocked"
    assert stale_label["public_lab_evolve_replay"]["numeric_replay"][
        "finding_codes"
    ] == ["MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE"]
    assert "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE" in stale_label[
        "safety_verdict"
    ]["derived_from"]["positive_finding_codes"]

    single_numeric_move_input = _copy_fixture_input(
        tmp_path, "numeric_single_assay_move_blocks_stale_label"
    )
    _mutate_json(
        single_numeric_move_input / "simulator_assays.json",
        lambda payload: payload["simulator_assays"][0].update(
            {NUMERIC_REPLAY_ASSAY_VALUE_FIELD: 0.55}
        ),
    )

    single_numeric_move = run(
        single_numeric_move_input,
        tmp_path / "numeric_single_assay_move_blocks_stale_label" / "receipts",
        command="pytest",
        acceptance_out=tmp_path
        / "numeric_single_assay_move_blocks_stale_label"
        / "acceptance.json",
    )

    assert single_numeric_move["status"] == "blocked"
    assert single_numeric_move["numeric_replay"]["status"] == "blocked"
    assert single_numeric_move["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_solid_electrolyte_002"
    )
    assert single_numeric_move["numeric_replay"]["selected_decision_id"] == (
        "decision_electrolyte_002"
    )
    assert single_numeric_move["numeric_replay"]["selected_next_action_class"] == (
        "update_surrogate_model"
    )
    assert round(
        single_numeric_move["numeric_replay"]["selected_computed_numeric_score"], 3
    ) == 0.844
    assert single_numeric_move["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE"
    ]
    assert single_numeric_move["realness_rank"] == 2
    assert single_numeric_move["realness_rung"] == "blocked"
    assert single_numeric_move["realness_evidence"]["score_backed_rows_bound"] is True
    assert single_numeric_move["realness_evidence"][
        "verdict_rederived_from_numeric_fixture_content"
    ] is True
    assert single_numeric_move["realness_evidence"][
        "baked_fixture_label_sufficient"
    ] is False
    assert single_numeric_move["safety_verdict"]["evidence_digest"] != baseline_digest


def test_materials_chemistry_numeric_replay_policy_requires_score_backed_rows(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path, "numeric_policy_requires_scores")

    for file_name in (
        "candidate_materials.json",
        "simulator_assays.json",
        "active_learning_decisions.json",
    ):
        _mutate_json(
            input_dir / file_name,
            lambda payload: [
                row.pop(field, None)
                for row in next(
                    value for value in payload.values() if isinstance(value, list)
                )
                for field in (
                    NUMERIC_REPLAY_SAFETY_GATE_FIELD,
                    NUMERIC_REPLAY_ASSAY_VALUE_FIELD,
                    NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD,
                )
            ],
        )

    result = run(
        input_dir,
        tmp_path / "numeric_policy_requires_scores" / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "numeric_policy_requires_scores" / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["safety_verdict"]["status"] == "blocked"
    assert result["numeric_replay"]["status"] == "blocked"
    assert result["numeric_replay"]["verified_numeric_row_count"] == 0
    assert result["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_POLICY_REQUIRES_SCORE_BACKED_ROWS"
    ]
    assert "MATERIALS_NUMERIC_REPLAY_POLICY_REQUIRES_SCORE_BACKED_ROWS" in result[
        "safety_verdict"
    ]["derived_from"]["positive_finding_codes"]
    assert result["realness_rank"] == 1
    assert result["realness_rung"] == "blocked"
    assert result["realness_evidence"]["score_backed_rows_bound"] is False


def test_materials_chemistry_numeric_replay_is_required_for_passing_verdict(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path, "numeric_required_for_pass")

    _mutate_json(input_dir / "replay_policy.json", lambda payload: payload.pop("numeric_replay"))
    for file_name in (
        "candidate_materials.json",
        "simulator_assays.json",
        "active_learning_decisions.json",
    ):
        _mutate_json(
            input_dir / file_name,
            lambda payload: [
                row.pop(field, None)
                for row in next(
                    value for value in payload.values() if isinstance(value, list)
                )
                for field in (
                    NUMERIC_REPLAY_SAFETY_GATE_FIELD,
                    NUMERIC_REPLAY_ASSAY_VALUE_FIELD,
                    NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD,
                )
            ],
        )

    result = run(
        input_dir,
        tmp_path / "numeric_required_for_pass" / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "numeric_required_for_pass" / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["safety_verdict"]["status"] == "blocked"
    assert result["numeric_replay"]["status"] == "blocked"
    assert result["numeric_replay"]["verified_numeric_row_count"] == 0
    assert result["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_REQUIRED"
    ]
    assert result["realness_rank"] == 1
    assert result["realness_rung"] == "blocked"
    assert result["realness_state"] == "metadata_or_missing_numeric_replay"
    assert result["realness_evidence"]["score_backed_rows_bound"] is False
    assert "MATERIALS_NUMERIC_REPLAY_REQUIRED" in result["safety_verdict"][
        "derived_from"
    ]["positive_finding_codes"]


def test_materials_chemistry_numeric_replay_honors_expected_next_pick_alias(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path, "numeric_expected_next_pick_alias")
    _mutate_json(
        input_dir / "replay_policy.json",
        lambda payload: payload["numeric_replay"].update(
            {
                "expected_selected_candidate_material_id": "",
                "expected_next_pick_candidate_material_id": (
                    "mat_catalyst_support_003"
                ),
            }
        ),
    )

    result = run(
        input_dir,
        tmp_path / "numeric_expected_next_pick_alias" / "receipts",
        command="pytest",
        acceptance_out=tmp_path
        / "numeric_expected_next_pick_alias"
        / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["numeric_replay"]["status"] == "blocked"
    assert result["numeric_replay"][
        "declared_expected_selected_candidate_material_id"
    ] == "mat_catalyst_support_003"
    assert result["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE"
    ]
    assert "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE" in result[
        "safety_verdict"
    ]["derived_from"]["positive_finding_codes"]


def test_materials_chemistry_numeric_replay_rejects_baked_static_expected_label(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path, "numeric_baked_static_label")
    _mutate_json(
        input_dir / "replay_policy.json",
        lambda payload: payload["numeric_replay"].update(
            {
                "expected_selected_candidate_material_id": "",
                "expected_next_pick_candidate_material_id": "",
                "baked_expected_selected_candidate_material_id": (
                    "mat_catalyst_support_003"
                ),
            }
        ),
    )

    result = run(
        input_dir,
        tmp_path / "numeric_baked_static_label" / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "numeric_baked_static_label" / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["numeric_replay"]["status"] == "blocked"
    assert result["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_polymer_membrane_001"
    )
    assert result["numeric_replay"][
        "declared_expected_selected_candidate_material_id"
    ] == "mat_catalyst_support_003"
    assert result["numeric_replay"]["selected_score_components"] == {
        "assay_proxy_value": 0.92,
        "active_learning_score": 0.90,
        "safety_gate_score": 0.94,
    }
    assert result["numeric_replay"]["verdict_basis"] == NUMERIC_REPLAY_VERDICT_BASIS
    assert result["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE"
    ]
    assert result["public_lab_evolve_replay"]["numeric_replay"][
        "verdict_basis"
    ] == NUMERIC_REPLAY_VERDICT_BASIS
    assert result["safety_verdict"]["derived_from"]["numeric_replay"][
        "verdict_basis"
    ] == NUMERIC_REPLAY_VERDICT_BASIS


def test_materials_chemistry_numeric_replay_rejects_out_of_range_scores(
    tmp_path: Path,
) -> None:
    cases = [
        (
            "candidate_safety_gate_out_of_range",
            "candidate_materials.json",
            lambda payload: payload["candidate_materials"][0].update(
                {NUMERIC_REPLAY_SAFETY_GATE_FIELD: 1.01}
            ),
        ),
        (
            "assay_proxy_out_of_range",
            "simulator_assays.json",
            lambda payload: payload["simulator_assays"][0].update(
                {NUMERIC_REPLAY_ASSAY_VALUE_FIELD: -0.01}
            ),
        ),
        (
            "active_learning_out_of_range",
            "active_learning_decisions.json",
            lambda payload: payload["active_learning_decisions"][0].update(
                {NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD: 1.25}
            ),
        ),
    ]

    for case_id, file_name, mutator in cases:
        input_dir = _copy_fixture_input(tmp_path, case_id)
        _mutate_json(input_dir / file_name, mutator)

        result = run(
            input_dir,
            tmp_path / case_id / "receipts",
            command="pytest",
            acceptance_out=tmp_path / case_id / "acceptance.json",
        )

        assert result["status"] == "blocked"
        assert result["safety_verdict"]["status"] == "blocked"
        assert result["numeric_replay"]["status"] == "blocked"
        assert "MATERIALS_NUMERIC_REPLAY_SCORE_OUT_OF_RANGE" in result[
            "numeric_replay"
        ]["finding_codes"]
        assert "MATERIALS_NUMERIC_REPLAY_SCORE_OUT_OF_RANGE" in result[
            "safety_verdict"
        ]["derived_from"]["positive_finding_codes"]


def test_materials_chemistry_lab_safety_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
        public_root
        / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input",
        public_root / "receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
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
        assert "wetlab_step_body" not in keys
        assert "reagent_quantity_body" not in keys
        assert "robot_command_payload" not in keys
        assert "credential_secret" not in keys
        assert "private_state_scan" not in keys


def test_materials_chemistry_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle_input(tmp_path, "runtime_shape_bundle")
    _write_bundle_numeric_replay(bundle)
    _copy_live_source_refs_for_bundle(bundle)

    result = run_lab_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_materials_lab_safety_bundle"
    assert result["selected_route_id"] == "materials_chemistry_closed_loop_lab_safety_replay"
    assert result["public_surface_name"] == (
        "materials_chemistry_artifact_safety_refusal_validator"
    )
    assert result["surface_reframe"]["forbidden_name_promises"] == [
        "closed_loop_wetlab_execution",
        "materials_discovery_lab",
        "robot_command_execution",
    ]
    assert result["materials_lab_safety_summary"]["experiment_count"] == 4
    assert result["public_lab_evolve_replay"]["summary"]["replay_case_count"] == 4
    assert result["public_lab_evolve_replay"]["summary"]["boundary_case_count"] == 0
    assert result["safety_verdict"]["status"] == "pass"
    assert result["safety_verdict"]["derived_from"]["source_open_body_import_count"] == 4
    assert (
        result["safety_verdict"]["derived_from"]["source_module_manifest_status"]
        == "pass"
    )
    assert result["body_import_status"] == "source_faithful_refactor_landed"
    assert result["body_import_verification"]["body_in_receipt"] is False
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_imports"]["verified_module_count"] == 4
    assert result["source_module_imports"]["live_source_checked_count"] == 4
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["body_copied_material_count"] == 4
    assert result["body_import_verification"]["source_open_body_import_count"] == 4
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    assert result["authority_ceiling"]["simulator_only"] is True
    assert result["authority_ceiling"]["robot_command_authorized"] is False
    assert result["authority_ceiling"]["discovery_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False


def test_materials_chemistry_exported_bundle_rejects_static_non_numeric_artifact(
    tmp_path: Path,
) -> None:
    result = run_lab_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "numeric_bundle_static/receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["safety_verdict"]["status"] == "blocked"
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_imports"]["verified_module_count"] == 4
    assert result["numeric_replay"]["status"] == "blocked"
    assert result["numeric_replay"]["verified_numeric_row_count"] == 0
    assert result["numeric_replay"]["selected_candidate_material_id"] == ""
    assert result["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_REQUIRED"
    ]
    assert result["realness_rank"] == 1
    assert result["realness_rung"] == "blocked"
    assert result["realness_state"] == "metadata_or_missing_numeric_replay"
    assert result["realness_evidence"]["score_backed_rows_bound"] is False
    assert result["realness_evidence"][
        "verdict_rederived_from_numeric_fixture_content"
    ] is True
    assert "MATERIALS_NUMERIC_REPLAY_REQUIRED" in result["safety_verdict"][
        "derived_from"
    ]["positive_finding_codes"]


def test_materials_chemistry_exported_bundle_recomputes_numeric_replay_verdict(
    tmp_path: Path,
) -> None:
    good_bundle = _copy_bundle_input(tmp_path, "numeric_bundle_good")
    _write_bundle_numeric_replay(good_bundle)

    good = run_lab_bundle(
        good_bundle,
        tmp_path
        / "numeric_bundle_good/receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert good["status"] == "pass"
    assert good["source_module_manifest_status"] == "pass"
    assert good["source_module_imports"]["verified_module_count"] == 4
    assert good["numeric_replay"]["status"] == "pass"
    assert good["numeric_replay"]["verified_numeric_row_count"] == 4
    assert good["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_polymer_membrane_001"
    )
    assert good["numeric_replay"]["selected_decision_id"] == "decision_membrane_001"
    assert good["numeric_replay"]["selected_next_action_class"] == "simulate_assay"
    assert round(
        good["numeric_replay"]["selected_computed_numeric_score"], 3
    ) == 0.917
    assert good["numeric_replay"]["selected_score_components"] == {
        "assay_proxy_value": 0.92,
        "active_learning_score": 0.90,
        "safety_gate_score": 0.94,
    }
    assert good["numeric_replay"]["verdict_basis"] == NUMERIC_REPLAY_VERDICT_BASIS
    assert good["public_lab_evolve_replay"]["status"] == "pass"
    assert good["public_lab_evolve_replay"]["numeric_replay"]["status"] == "pass"
    assert good["public_lab_evolve_replay"]["numeric_replay"][
        "selected_score_components"
    ] == good["numeric_replay"]["selected_score_components"]
    assert good["public_lab_evolve_replay"]["summary"][
        "numeric_replay_selected_candidate_material_id"
    ] == "mat_polymer_membrane_001"
    good_numeric_digest = good["numeric_replay"]["evidence_digest"]

    wrong_bundle = _copy_bundle_input(tmp_path, "numeric_bundle_real_but_wrong")
    _write_bundle_numeric_replay(
        wrong_bundle,
        score_overrides={
            "mat_sorbent_surface_004": {
                "safety_gate": 0.93,
                "assay_proxy": 0.98,
                "active_learning": 0.98,
            }
        },
    )

    wrong = run_lab_bundle(
        wrong_bundle,
        tmp_path
        / "numeric_bundle_real_but_wrong/receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert wrong["status"] == "blocked"
    assert wrong["safety_verdict"]["status"] == "blocked"
    assert wrong["source_module_manifest_status"] == "pass"
    assert wrong["source_module_imports"]["verified_module_count"] == 4
    assert wrong["source_module_findings"] == []
    assert wrong["numeric_replay"]["status"] == "blocked"
    assert wrong["numeric_replay"]["verified_numeric_row_count"] == 4
    assert wrong["numeric_replay"]["selected_candidate_material_id"] == (
        "mat_sorbent_surface_004"
    )
    assert wrong["numeric_replay"]["selected_decision_id"] == "decision_sorbent_004"
    assert wrong["numeric_replay"]["selected_next_action_class"] == "screen_candidate"
    assert wrong["numeric_replay"][
        "declared_expected_selected_candidate_material_id"
    ] == "mat_polymer_membrane_001"
    assert round(
        wrong["numeric_replay"]["selected_computed_numeric_score"], 3
    ) == 0.970
    assert wrong["numeric_replay"]["selected_score_components"] == {
        "assay_proxy_value": 0.98,
        "active_learning_score": 0.98,
        "safety_gate_score": 0.93,
    }
    assert wrong["numeric_replay"]["verdict_basis"] == NUMERIC_REPLAY_VERDICT_BASIS
    assert wrong["numeric_replay"]["evidence_digest"] != good_numeric_digest
    assert wrong["numeric_replay"]["finding_codes"] == [
        "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE"
    ]
    assert wrong["public_lab_evolve_replay"]["status"] == "blocked"
    assert wrong["public_lab_evolve_replay"]["numeric_replay"]["status"] == (
        "blocked"
    )
    assert wrong["public_lab_evolve_replay"]["numeric_replay"][
        "selected_candidate_material_id"
    ] == "mat_sorbent_surface_004"
    assert wrong["public_lab_evolve_replay"]["summary"][
        "numeric_replay_status"
    ] == "blocked"
    assert wrong["safety_verdict"]["derived_from"]["replay_status"] == "blocked"
    assert "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE" in wrong[
        "safety_verdict"
    ]["derived_from"]["positive_finding_codes"]


def test_materials_chemistry_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/materials_chemistry_closed_loop_lab_safety_replay",
        public_root / "examples/materials_chemistry_closed_loop_lab_safety_replay",
    )
    bundle = (
        public_root
        / "examples/materials_chemistry_closed_loop_lab_safety_replay/"
        "exported_materials_lab_safety_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_lab_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["safety_verdict"]["status"] == "blocked"
    assert "MATERIALS_SOURCE_MODULE_DIGEST_MISMATCH" in result["safety_verdict"][
        "derived_from"
    ]["source_module_finding_codes"]
    assert result["source_module_manifest_status"] == "blocked"
    assert any(
        finding["error_code"] == "MATERIALS_SOURCE_MODULE_DIGEST_MISMATCH"
        for finding in result["source_module_findings"]
    )


def test_materials_chemistry_rejects_partial_target_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/materials_chemistry_closed_loop_lab_safety_replay",
        public_root / "examples/materials_chemistry_closed_loop_lab_safety_replay",
    )
    bundle = (
        public_root
        / "examples/materials_chemistry_closed_loop_lab_safety_replay/"
        "exported_materials_lab_safety_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_lab_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert any(
        finding["error_code"] == "MATERIALS_SOURCE_MODULE_DIGEST_MISMATCH"
        for finding in result["source_module_findings"]
    )


def test_materials_chemistry_rejects_self_consistent_source_module_body_swap(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle_input(tmp_path, "self_consistent_body_swap")
    _copy_live_source_refs_for_bundle(bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = bundle / manifest["modules"][0]["path"]
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n# verifier-dispute body swap keeps anchors but changes live source digest\n",
        encoding="utf-8",
    )
    swapped_digest = _sha256(target)
    manifest["modules"][0]["sha256"] = swapped_digest
    manifest["modules"][0]["source_sha256"] = swapped_digest
    manifest["modules"][0]["target_sha256"] = swapped_digest
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_lab_bundle(
        bundle,
        tmp_path
        / "self_consistent_body_swap/receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_imports"]["live_source_checked_count"] == 4
    assert result["source_module_imports"]["live_source_missing"] == []
    assert any(
        finding["error_code"]
        == "MATERIALS_SOURCE_MODULE_AUTHORITY_DIGEST_MISMATCH"
        for finding in result["source_module_findings"]
    )
    assert any(
        finding["error_code"]
        == "MATERIALS_SOURCE_MODULE_LIVE_SOURCE_DIGEST_MISMATCH"
        for finding in result["source_module_findings"]
    )
    assert "MATERIALS_SOURCE_MODULE_AUTHORITY_DIGEST_MISMATCH" in result[
        "safety_verdict"
    ]["derived_from"]["source_module_finding_codes"]
    assert "MATERIALS_SOURCE_MODULE_LIVE_SOURCE_DIGEST_MISMATCH" in result[
        "safety_verdict"
    ]["derived_from"]["source_module_finding_codes"]


def test_materials_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["body_text_in_receipt"] is False
    assert manifest["module_count"] == 4

    modules = manifest["modules"]
    assert [row["module_id"] for row in modules] == [
        "materials_lab_evolve_failure_replay_specimen_body_import",
        "materials_lab_evolve_replay_graph_body_import",
        "materials_lab_evolve_receipt_body_import",
        "laboratory_standard_body_import",
    ]

    for row in modules:
        source = SOURCE_ROOT / row["source_ref"]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        if not target.is_file():
            target = BUNDLE_INPUT / row["path"]

        assert source.is_file()
        assert target.is_file()
        assert target.read_bytes() == source.read_bytes()
        digest = _sha256(target)
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        assert row["sha256_match"] is True
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in text

    blocked_refs = {
        row["source_ref"]: row for row in manifest["blocked_source_refs"]
    }
    blocked = blocked_refs["codex/doctrine/paper_modules/lab_oracle_evolve_pipeline.md"]
    assert blocked["status"] == "blocked_by_raw_operator_voice_boundary"
    assert "raw operator voice" in blocked["replacement_criteria"]


def test_materials_chemistry_rejects_source_module_manifest_body_text_boundary(
    tmp_path: Path,
) -> None:
    cases = {
        "manifest_body_text_missing": None,
        "manifest_body_text_true": True,
    }

    for case_id, body_text_value in cases.items():
        public_root = tmp_path / case_id / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        shutil.copytree(
            MICROCOSM_ROOT / "examples/materials_chemistry_closed_loop_lab_safety_replay",
            public_root / "examples/materials_chemistry_closed_loop_lab_safety_replay",
        )
        bundle = (
            public_root
            / "examples/materials_chemistry_closed_loop_lab_safety_replay/"
            "exported_materials_lab_safety_bundle"
        )
        manifest_path = bundle / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if body_text_value is None:
            manifest.pop("body_text_in_receipt", None)
        else:
            manifest["body_text_in_receipt"] = body_text_value
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run_lab_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            f"materials_chemistry_closed_loop_lab_safety_replay/{case_id}",
            command="pytest",
        )
        source_modules = result["source_module_imports"]

        assert result["status"] == "blocked"
        assert result["safety_verdict"]["status"] == "blocked"
        assert "MATERIALS_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED" in result[
            "safety_verdict"
        ]["derived_from"]["source_module_finding_codes"]
        assert result["source_module_manifest_status"] == "blocked"
        assert source_modules["status"] == "blocked"
        assert source_modules["body_in_receipt"] is False
        assert source_modules["body_text_in_receipt"] is False
        findings = [
            row
            for row in result["source_module_findings"]
            if row["error_code"] == "MATERIALS_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED"
        ]
        assert findings
        assert {row["subject_kind"] for row in findings} == {"body_text_in_receipt"}
        assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert result["body_in_receipt"] is False
        receipt_text = json.dumps(result, sort_keys=True)
        assert "wetlab_step_body" not in receipt_text
        assert "robot_command_payload" not in receipt_text


def test_materials_chemistry_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    bundle = _copy_bundle_input(tmp_path, "bundle_card")
    _write_bundle_numeric_replay(bundle)
    _copy_live_source_refs_for_bundle(bundle)

    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay"
    )
    args = [
        "run-lab-bundle",
        "--input",
        str(bundle),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["public_surface_name"] == (
        "materials_chemistry_artifact_safety_refusal_validator"
    )
    assert first_card["surface_reframe"]["reframe_reason"] == (
        "no_wetlab_loop_authorized_artifact_safety_refusal_validation_only"
    )
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["command_speed"]["freshness_input_count"] == 15
    assert first_card["materials_lab_safety"]["candidate_material_count"] == 4
    assert first_card["materials_lab_safety"]["experiment_count"] == 4
    assert first_card["materials_lab_safety"]["simulator_assay_count"] == 4
    assert first_card["materials_lab_safety"]["wetlab_protocol_export_count"] == 0
    assert first_card["materials_lab_safety"]["robot_command_count"] == 0
    assert first_card["public_lab_evolve_replay"]["replay_case_count"] == 4
    assert first_card["public_lab_evolve_replay"]["boundary_case_count"] == 0
    assert first_card["body_floor"]["source_module_manifest_status"] == "pass"
    assert first_card["body_floor"]["source_open_body_import_status"] == "pass"
    assert first_card["body_floor"]["source_open_body_import_count"] == 4
    assert first_card["body_floor"]["body_copied_material_count"] == 4
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert first_card["safety_verdict"]["status"] == "pass"
    assert first_card["safety_verdict"]["verdict"] == (
        "public_safe_simulator_replay_accepted"
    )
    assert first_card["safety_verdict"]["derived_from_in_card"] is False
    assert "candidate_materials" not in _walk_keys(first_card)
    assert "experiments" not in _walk_keys(first_card)
    assert "simulator_assays" not in _walk_keys(first_card)
    assert "active_learning_decisions" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "authority_ceiling" not in _walk_keys(first_card)
    assert "anti_claim" not in _walk_keys(first_card)
    assert "wetlab_step_body" not in _walk_keys(first_card)
    assert "robot_command_payload" not in _walk_keys(first_card)
    assert "derived_from" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        materials_chemistry_closed_loop_lab_safety_replay,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert [Path(path).name for path in cached_card["receipt_paths"]] == [
        Path(path).name for path in first_card["receipt_paths"]
    ]
