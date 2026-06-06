from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

from microcosm_core.projections.organ_discoverability_matrix import (
    AUTHORITY_POSTURE,
    build_organ_discoverability_matrix,
    compile_paths,
    validate_organ_discoverability_matrix,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _matrix() -> dict:
    return build_organ_discoverability_matrix(root=MICROCOSM_ROOT)


def test_matrix_preserves_cold_agent_fields_for_every_accepted_organ() -> None:
    payload = _matrix()

    assert payload["validation"]["status"] == "pass"
    assert payload["authority_posture"] == AUTHORITY_POSTURE
    assert payload["release_authorized"] is False
    assert payload["source_mutation_authorized"] is False
    assert payload["provider_call_authorized"] is False
    assert payload["generated_projection_is_source_authority"] is False
    assert payload["row_count"] == payload["source_summary"]["accepted_organ_count"]
    assert payload["row_count"] >= 70

    by_organ = {row["organ_id"]: row for row in payload["rows"]}
    cold_reader = by_organ["cold_reader_route_map"]
    assert cold_reader["first_command"].startswith("microcosm cold-reader-route-map ")
    assert cold_reader["command_runnable_shape"] is True
    assert cold_reader["authority_ceiling"]
    assert cold_reader["evidence_class"] == "semantic_validator"
    assert cold_reader["proof_receipts"]["refs"]
    assert cold_reader["task_routes"]
    cold_reader_route = cold_reader["task_routes"][0]
    assert cold_reader_route["task_route_ref"] == cold_reader_route["source_ref"]
    assert cold_reader_route["task_route_ref"] == (
        "atlas/agent_task_routes.json::routes[task_class=agent-entry]"
    )
    assert cold_reader_route["route_role"] == "agent_task_class_to_organ_selector"
    assert cold_reader_route["organ_route_role"] == "primary"
    assert cold_reader_route["organ_route_ref"] == (
        "atlas/agent_task_routes.json::routes[task_class=agent-entry].primary_organ_id"
    )
    assert cold_reader_route["source_relation_summary"]["edge_count"] > 0
    assert cold_reader_route["source_relation_summary"]["source_shard_ref_count"] > 0
    assert cold_reader_route["source_relation_summary"]["query_examples"]
    assert cold_reader_route["organ_source_relation_handle"][
        "source_relation_ref"
    ] == (
        "organ-surface-contract::coverage.source_module_file_graph."
        "edges_by_organ[organ_id=cold_reader_route_map]"
    )
    assert cold_reader_route["organ_source_relation_handle"]["query"] == (
        "microcosm organ-topology --organ cold_reader_route_map"
    )
    assert cold_reader["owner_build_route"]["builder_check_commands"]
    assert "source JSON" in cold_reader["authority_boundary"]


def test_matrix_resolves_capsule_paper_modules_and_route_handles() -> None:
    payload = _matrix()
    by_organ = {row["organ_id"]: row for row in payload["rows"]}

    navigation = by_organ["navigation_hologram_route_plane"]
    assert navigation["paper_module"]["source"] in {"direct_file", "json_capsule"}
    assert navigation["paper_module"]["ref"] == "paper_modules/navigation_hologram_route_plane.md"
    assert "doctrine_missing_paper_module_ref" not in navigation["gap_codes"]

    durable = by_organ["durable_agent_work_landing_replay"]
    assert durable["paper_module"]["status"] == "available"
    assert durable["paper_module"]["ref"] == "paper_modules/durable_agent_work_landing_replay.md"
    assert durable["paper_module"]["source"] == "json_capsule"
    assert "doctrine_missing_paper_module_ref" not in durable["gap_codes"]
    assert any(
        card["source_relation_summary"]["edge_count"] > 0
        for card in durable["task_routes"]
    )

    proof_spine = by_organ["proof_diagnostic_evidence_spine"]
    assert proof_spine["paper_module"]["source"] == "json_capsule"
    assert proof_spine["paper_module"]["ref"] == "paper_modules/proof_diagnostic_evidence_spine.md"
    assert proof_spine["paper_module"]["capsule_ref"] == (
        "paper_module.proof_diagnostic_evidence_spine"
    )
    assert "doctrine_missing_paper_module_ref" not in proof_spine["gap_codes"]


def test_matrix_exposes_route_proof_handles_for_non_primary_organs() -> None:
    payload = _matrix()
    by_organ = {row["organ_id"]: row for row in payload["rows"]}

    route_runtime = by_organ["agent_route_observability_runtime"]
    evaluation_route = next(
        card
        for card in route_runtime["task_routes"]
        if card["task_class"] == "agent-evaluation"
    )

    assert evaluation_route["task_route_ref"] == (
        "atlas/agent_task_routes.json::routes[task_class=agent-evaluation]"
    )
    assert evaluation_route["source_ref"] == evaluation_route["task_route_ref"]
    assert evaluation_route["route_role"] == "agent_task_class_to_organ_selector"
    assert evaluation_route["primary_organ_id"] != "agent_route_observability_runtime"
    assert evaluation_route["organ_route_role"] == "relevant"
    assert evaluation_route["organ_route_ref"] == (
        "atlas/agent_task_routes.json::routes[task_class=agent-evaluation]."
        "relevant_organs[organ_id=agent_route_observability_runtime]"
    )


def test_matrix_classifies_requested_discoverability_gap_families() -> None:
    payload = _matrix()

    target_counts = payload["validation_target_gap_counts"]
    assert set(target_counts) == {
        "missing_first_command",
        "route_points_to_non_runnable_command",
        "missing_authority_ceiling",
        "missing_paper_module_link",
        "proof_receipt_hidden",
        "owner_build_route_unclear",
    }
    assert isinstance(payload["gap_counts"], dict)
    assert payload["top_gap_rows"]
    assert payload["top_gap_rows"][0]["reentry_condition"]
    if payload["discoverability_status"] == "complete":
        assert payload["gap_counts"] == {}
        assert all(count == 0 for count in target_counts.values())
        assert payload["top_gap_rows"][0]["gap_codes"] == []
    else:
        assert payload["top_gap_rows"][0]["gap_codes"]


def test_matrix_validator_rejects_non_runnable_command_false_positive() -> None:
    payload = _matrix()
    bad_payload = copy.deepcopy(payload)
    bad_payload["rows"][0]["first_command"] = "see AGENT_ROUTES.md"
    bad_payload["rows"][0]["command_runnable_shape"] = True

    result = validate_organ_discoverability_matrix(bad_payload)

    assert result["status"] == "blocked"
    assert "command_shape_false_positive" in {error["code"] for error in result["errors"]}


def test_matrix_validator_requires_receipt_gap_to_be_explicit() -> None:
    payload = _matrix()
    bad_payload = copy.deepcopy(payload)
    bad_payload["rows"][0]["proof_receipts"]["refs"] = []
    bad_payload["rows"][0]["gap_codes"] = [
        code for code in bad_payload["rows"][0]["gap_codes"] if code != "proof_receipt_hidden"
    ]

    result = validate_organ_discoverability_matrix(bad_payload)

    assert result["status"] == "blocked"
    assert "missing_receipt_gap_not_declared" in {
        error["code"] for error in result["errors"]
    }


def test_matrix_validator_requires_route_proof_handles() -> None:
    payload = _matrix()
    bad_payload = copy.deepcopy(payload)
    bad_payload["rows"][0]["task_routes"][0]["task_route_ref"] = ""
    bad_payload["rows"][0]["task_routes"][0]["source_ref"] = "atlas/agent_task_routes.json::routes"
    bad_payload["rows"][0]["task_routes"][0]["route_role"] = ""
    bad_payload["rows"][0]["task_routes"][0]["organ_route_ref"] = "not-a-route-ref"

    result = validate_organ_discoverability_matrix(bad_payload)

    assert result["status"] == "blocked"
    assert {
        "missing_task_route_ref",
        "route_source_ref_mismatch",
        "missing_route_role",
        "organ_route_ref_not_anchored",
    } <= {error["code"] for error in result["errors"]}


def test_matrix_cli_writes_projection_and_receipt(tmp_path: Path) -> None:
    payload = compile_paths(root=MICROCOSM_ROOT, out=tmp_path)

    matrix_path = tmp_path / "organ_discoverability_matrix.json"
    receipt_path = tmp_path / "organ_discoverability_matrix_receipt.json"
    assert payload["validation"]["status"] == "pass"
    assert matrix_path.exists()
    assert receipt_path.exists()
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert matrix["row_count"] == payload["row_count"]
    assert receipt["authority_posture"] == AUTHORITY_POSTURE
    assert receipt["body_in_receipt"] is False


def test_microcosm_cli_exposes_organ_discoverability_matrix(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MICROCOSM_ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core",
            "organ-discoverability-matrix",
            "--root",
            str(MICROCOSM_ROOT),
            "--out",
            str(tmp_path),
            "--check",
        ],
        cwd=MICROCOSM_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["validation"]["status"] == "pass"
    assert payload["row_count"] == payload["source_summary"]["accepted_organ_count"]
    assert payload["row_count"] >= 70
    assert "route_points_to_non_runnable_command" in payload["validation_target_gap_counts"]
    assert (tmp_path / "organ_discoverability_matrix.json").exists()
    assert (tmp_path / "organ_discoverability_matrix_receipt.json").exists()
