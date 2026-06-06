from __future__ import annotations

import copy
import json
from pathlib import Path

from microcosm_core.projections.route_candidate_read_model import (
    AUTHORITY_POSTURE,
    build_route_candidate_read_model,
    compile_paths,
    validate_route_candidate_read_model,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _model() -> dict:
    return build_route_candidate_read_model(root=MICROCOSM_ROOT)


def test_route_candidate_read_model_ranks_source_backed_observability_lane() -> None:
    payload = _model()

    assert payload["status"] == "pass"
    assert payload["authority_posture"] == AUTHORITY_POSTURE
    assert payload["route_mining_controller_ready"] is True
    assert payload["generated_projection_is_source_authority"] is False
    assert payload["chat_memory_authority"] is False

    top = payload["candidate_rows"][0]
    assert top["organ_id"] == "agent_route_observability_runtime"
    assert top["rank"] == 1
    assert top["score"] >= payload["candidate_rows"][1]["score"]
    assert top["first_command"].startswith("microcosm ")
    assert top["task_route_ref"].startswith("atlas/agent_task_routes.json::routes[task_class=")
    assert top["route_role"] == "agent_task_class_to_organ_selector"
    assert top["stop_condition"].startswith("Stop when the first command")
    assert top["route_refs"]["task_route_ref"] == top["task_route_ref"]
    assert top["route_refs"]["route_relation"] in {"primary", "relevant", "legacy_ref"}
    assert top["claim_ceiling"]
    assert top["receipt_refs"]
    assert top["source_refs"]
    assert top["trace_repair_support"]["route_repair_row_count"] >= 3
    assert top["observability_store_support"]["route_decision_event_count"] >= 3
    assert "chat memory" in top["authority_boundary"]


def test_route_candidate_read_model_preserves_named_existing_organs() -> None:
    payload = _model()
    by_organ = {row["organ_id"]: row for row in payload["candidate_rows"]}

    assert {
        "agent_route_observability_runtime",
        "navigation_hologram_route_plane",
        "cold_reader_route_map",
        "pattern_binding_contract",
    }.issubset(by_organ)
    assert by_organ["navigation_hologram_route_plane"]["first_command"]
    assert by_organ["cold_reader_route_map"]["receipt_refs"]
    assert by_organ["pattern_binding_contract"]["source_refs"]
    assert all(by_organ[organ_id]["candidate_group"] == "route_mining" for organ_id in {
        "agent_route_observability_runtime",
        "navigation_hologram_route_plane",
        "cold_reader_route_map",
        "pattern_binding_contract",
    })


def test_route_candidate_read_model_exposes_mechanism_spine_next_lanes() -> None:
    payload = _model()
    by_organ = {row["organ_id"]: row for row in payload["candidate_rows"]}
    expected_spine = {
        "certificate_kernel_execution_lab",
        "cognitive_operator_registry",
        "doctrine_fact_claim_audit",
        "durable_agent_work_landing_replay",
        "engine_room_demo",
        "finance_forecast_evaluation_spine",
        "mission_transaction_work_spine",
        "proof_derived_governed_mutation_authorization",
    }

    assert expected_spine.issubset(by_organ)
    for organ_id in expected_spine:
        row = by_organ[organ_id]
        assert row["candidate_group"] == "mechanism_spine"
        assert row["first_command"].startswith("microcosm ")
        assert row["task_route_ref"].startswith("atlas/agent_task_routes.json::routes[task_class=")
        assert row["route_role"] == "agent_task_class_to_organ_selector"
        assert row["stop_condition"].startswith("Stop when the first command")
        assert row["claim_ceiling"]
        assert row["receipt_refs"]
        assert row["source_refs"]
        assert row["authority_boundary"].startswith("projection ranks public route candidates")


def test_route_candidate_read_model_validator_rejects_name_only_candidates() -> None:
    payload = _model()
    bad_payload = copy.deepcopy(payload)
    bad_payload["candidate_rows"][0]["receipt_refs"] = []
    bad_payload["candidate_rows"][0]["task_route_ref"] = ""

    result = validate_route_candidate_read_model(bad_payload)

    assert result["status"] == "blocked"
    assert "candidate_missing_required_field" in {error["code"] for error in result["errors"]}
    assert "candidate_not_source_backed" in {error["code"] for error in result["errors"]}


def test_route_candidate_read_model_validator_rejects_generated_authority_claim() -> None:
    payload = _model()
    bad_payload = copy.deepcopy(payload)
    bad_payload["generated_projection_is_source_authority"] = True

    result = validate_route_candidate_read_model(bad_payload)

    assert result["status"] == "blocked"
    assert "banned_authority_claim_true" in {error["code"] for error in result["errors"]}


def test_route_candidate_read_model_cli_writes_model_and_receipt(tmp_path: Path) -> None:
    payload = compile_paths(root=MICROCOSM_ROOT, out=tmp_path)

    model_path = tmp_path / "route_candidate_read_model.json"
    receipt_path = tmp_path / "route_candidate_read_model_receipt.json"
    assert payload["status"] == "pass"
    assert model_path.exists()
    assert receipt_path.exists()
    assert json.loads(model_path.read_text(encoding="utf-8"))["candidate_count"] >= 12
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["authority_posture"] == AUTHORITY_POSTURE
    assert receipt["body_in_receipt"] is False
