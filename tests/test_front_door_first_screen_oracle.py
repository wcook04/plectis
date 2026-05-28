from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core import cli
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def _copytree_fixture(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=FIXTURE_COPY_IGNORE)


def _copy_runtime_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    _copytree_fixture(MICROCOSM_ROOT / "core", public_root / "core")
    _copytree_fixture(MICROCOSM_ROOT / "examples", public_root / "examples")
    _copytree_fixture(MICROCOSM_ROOT / "src", public_root / "src")
    _copytree_fixture(MICROCOSM_ROOT / "standards", public_root / "standards")
    _copytree_fixture(
        MICROCOSM_ROOT / "receipts/first_wave",
        public_root / "receipts/first_wave",
    )
    _copytree_fixture(
        MICROCOSM_ROOT / "receipts/preflight",
        public_root / "receipts/preflight",
    )
    return public_root


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src" / "scratch_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text(
        "# Scratch Project\n\nLocal proof project.\n",
        encoding="utf-8",
    )
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src" / "scratch_app" / "__init__.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (project / "tests" / "test_smoke.py").write_text(
        "from scratch_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def _assert_body_floor_blocking_details(details: dict) -> None:
    assert details["status"] == "blocked"
    assert details["defect_count"] >= 1
    assert details["defect_preview"]
    first_defect = details["defect_preview"][0]
    assert first_defect["target_ref"]
    assert first_defect["defect_codes"]
    assert first_defect["body_text_in_receipt"] is False
    assert details["full_defects_ref"] == (
        "microcosm status::macro_body_import_floor.defects"
    )


def test_empty_folder_first_screen_oracle_names_selected_route(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)
    project = tmp_path / "empty_project"
    project.mkdir()
    shell = RuntimeShell(public_root)

    assert cli.main(["tour", str(project)]) in {0, 1}
    tour = json.loads(capsys.readouterr().out)
    status_rc = cli.main(["status", "--card", str(project)])
    status_card = json.loads(capsys.readouterr().out)
    observatory = shell.project_observatory(project, persist_receipts=False)
    body_floor_blocked = (
        status_card["front_door_status"]["surface_statuses"].get(
            "macro_body_import_floor"
        )
        != "pass"
    )
    assert status_rc == (1 if body_floor_blocked else 0)

    selected_route_id = tour["selected_route_id"]
    first_screen = tour["first_screen"]
    front_door = status_card["front_door"]
    route_proof = front_door["route_selection_proof"]
    route_explanation = front_door["route_explanation"]
    observatory_card = observatory["observatory_card"]

    assert selected_route_id == "missing_tests_route"
    assert first_screen["status"] == "pass"
    assert first_screen["available_project_route_ids"] == ["missing_tests_route"]
    assert "selected_route_id" in first_screen["route_selection_rule"]
    assert "readme_onboarding_route is only present when the project has a README" in (
        first_screen["route_selection_rule"]
    )
    assert (
        "empty or non-README folders can select missing_tests_route"
        in first_screen["route_selection_rule"]
    )
    assert "missing_tests_route when tests are absent" in (
        first_screen["route_selection_rule"]
    )

    assert status_card["front_door_status"]["status"] == (
        "blocked" if body_floor_blocked else "pass"
    )
    if body_floor_blocked:
        assert "macro_body_import_floor" in status_card["front_door_status"][
            "blocking_surface_ids"
        ]
        _assert_body_floor_blocking_details(
            status_card["front_door_status"]["blocking_surface_details"][
                "macro_body_import_floor"
            ]
        )
    else:
        assert status_card["front_door_status"]["blocking_surface_ids"] == []
    assert route_proof["status"] == "pass"
    assert route_proof["selected_route_id"] == selected_route_id
    assert route_proof["route_id_available_in_state"] is True
    assert route_explanation["status"] == "pass"
    assert route_explanation["route_id"] == selected_route_id
    assert route_explanation["command"] == "microcosm explain <project> missing_tests_route"
    assert route_explanation["selected_work_id"] == "work_0001"
    assert route_explanation["source_files_mutated"] is False
    assert front_door["observatory"]["route_explanation_endpoint"] == (
        "/project/explain/missing_tests_route"
    )
    assert observatory_card["status"] == ("blocked" if body_floor_blocked else "pass")
    assert observatory_card["selected_route_id"] == selected_route_id
    expected_observatory_statuses = {
        "first_screen": "pass",
        "route": "pass",
        "work": "pass",
        "evidence": "pass",
        "graph": "pass",
        "state_inspection": "pass",
        "state_write_proof": "pass",
        "proof_lab": "pass",
        "source_open_body_import_floor": "pass",
        "first_screen_composition": "pass",
        "observatory": "pass",
    }
    if body_floor_blocked:
        expected_observatory_statuses["first_screen"] = "blocked"
        expected_observatory_statuses["source_open_body_import_floor"] = "blocked"
        expected_observatory_statuses["observatory"] = "blocked"
    assert observatory_card["surface_statuses"] == expected_observatory_statuses
    assert observatory_card["state_inspection"]["status"] == "pass"
    assert observatory_card["state_inspection"]["state_dir"] == ".microcosm"
    assert observatory_card["state_inspection"]["state_dir_exists"] is True
    assert observatory_card["state_inspection"]["missing_first_screen_refs"] == []
    assert ".microcosm/routes.json" in (
        observatory_card["state_inspection"]["first_screen_refs"]
    )
    assert observatory_card["surface_status_refs"]["route"] == (
        ".microcosm/routes.json::missing_tests_route"
    )
    assert observatory_card["surface_status_refs"]["state_inspection"] == (
        ".microcosm/"
    )
    assert observatory_card["surface_status_refs"]["evidence"] == (
        ".microcosm/evidence/"
    )
    assert observatory_card["status_card_endpoint"] == "/project/status"
    assert observatory_card["surface_status_refs"]["status_card"] == (
        "/project/status"
    )
    assert observatory_card["causal_chain_summary"]["route"]["route_id"] == (
        selected_route_id
    )

    for relative in [
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/evidence/explain_missing_tests_route.json",
        ".microcosm/graph.json",
        ".microcosm/explanations/missing_tests_route.json",
    ]:
        assert (project / relative).is_file()


def test_cold_reader_first_screen_oracle_exposes_live_route_chain(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(public_root)

    assert cli.main(["tour", str(project)]) in {0, 1}
    tour = json.loads(capsys.readouterr().out)
    assert cli.main(["tour", "--card", str(project)]) in {0, 1}
    tour_card = json.loads(capsys.readouterr().out)
    status_rc = cli.main(["status", "--card", str(project)])
    status_card = json.loads(capsys.readouterr().out)
    observatory = shell.project_observatory(project, persist_receipts=False)
    proof_lab = shell.proof_lab()
    intake_card = shell.intake_card()

    selected_route_id = tour["selected_route_id"]
    first_screen = tour["first_screen"]
    front_door = status_card["front_door"]
    front_door_status = status_card["front_door_status"]
    route_proof = front_door["route_selection_proof"]
    route_explanation = front_door["route_explanation"]
    body_floor = front_door["source_open_body_import_floor"]
    body_floor_pointer = front_door["source_open_body_imports"]
    tour_card_observatory = tour_card["observatory"]
    observatory_card = observatory["observatory_card"]
    causal_summary = observatory_card["causal_chain_summary"]
    body_floor_blocked = (
        front_door_status["surface_statuses"].get("macro_body_import_floor")
        != "pass"
    )
    assert status_rc == (1 if body_floor_blocked else 0)

    assert selected_route_id == "readme_onboarding_route"
    assert tour_card["selected_route_id"] == selected_route_id
    assert tour_card_observatory["project_observe_endpoint"] == "/project/observe"
    assert tour_card_observatory["project_observe_ref"] == (
        "microcosm serve <project>::/project/observe"
    )
    assert tour_card_observatory["command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 6"
    )
    assert tour_card_observatory["route_explanation_endpoint"] == (
        f"/project/explain/{selected_route_id}"
    )
    assert first_screen["status"] == "pass"
    assert "selected_route_id" in first_screen["route_selection_rule"]
    assert "readme_onboarding_route is only present when the project has a README" in (
        first_screen["route_selection_rule"]
    )
    assert (
        "empty or non-README folders can select missing_tests_route"
        in first_screen["route_selection_rule"]
    )
    assert "missing_tests_route when tests are absent" in (
        first_screen["route_selection_rule"]
    )
    assert front_door_status["status"] == (
        "blocked" if body_floor_blocked else "pass"
    )
    if body_floor_blocked:
        assert "macro_body_import_floor" in front_door_status[
            "blocking_surface_ids"
        ]
        _assert_body_floor_blocking_details(
            front_door_status["blocking_surface_details"]["macro_body_import_floor"]
        )
    else:
        assert front_door_status["blocking_surface_ids"] == []
    assert front_door_status["surface_statuses"]["route_selection_proof"] == "pass"
    assert front_door_status["surface_statuses"]["route_explanation"] == "pass"
    assert front_door_status["surface_statuses"]["macro_body_import_floor"] == (
        "blocked" if body_floor_blocked else "pass"
    )
    assert front_door_status["surface_statuses"]["observatory"] == "pass"
    assert front_door_status["surface_statuses"]["proof_lab"] == "pass"

    first_screen_commands = [
        step["command"] for step in first_screen["minimal_command_path"]
    ]
    assert "microcosm tour --card <project>" in first_screen_commands
    assert "microcosm status --card <project>" in first_screen_commands
    assert "microcosm workingness --card" in first_screen_commands
    assert all("&&" not in command for command in first_screen_commands)
    assert "microcosm proof-lab --out /tmp/microcosm-proof-lab" in (
        first_screen_commands
    )
    assert "microcosm observe <project>" in first_screen_commands
    observe_step = next(
        step
        for step in first_screen["minimal_command_path"]
        if step["step_id"] == "inspect_project_observe"
    )
    assert observe_step["endpoint"] == "/project/observe"
    assert observe_step["selected_route_id"] == selected_route_id
    status_step = next(
        step
        for step in first_screen["minimal_command_path"]
        if step["step_id"] == "inspect_status_card"
    )
    assert status_step["status_card_endpoint"] == "/project/status"
    workingness_step = next(
        step
        for step in first_screen["minimal_command_path"]
        if step["step_id"] == "inspect_workingness"
    )
    assert workingness_step["workingness_command"] == "microcosm workingness --card"
    assert workingness_step["workingness_endpoint"] == "/workingness"

    status_route_card = tour["route_cards_by_id"]["status_and_workingness"]
    assert status_route_card["command"] == "microcosm status --card <project>"
    assert status_route_card["next_command"] == "microcosm workingness --card"
    assert status_route_card["status_card_endpoint"] == "/project/status"
    assert status_route_card["workingness_endpoint"] == "/workingness"
    assert status_route_card["endpoint"] == "/workingness"

    assert route_proof["status"] == "pass"
    assert route_proof["selected_route_id"] == selected_route_id
    assert route_proof["route_id_available_in_state"] is True
    assert route_proof["state_refs_checked_count"] >= 2
    assert route_proof["observatory_route_proof_ref"] == (
        "microcosm serve <project>::first_screen_route_proof"
    )
    assert route_explanation["status"] == "pass"
    assert route_explanation["route_id"] == selected_route_id
    assert route_explanation["selected_work_id"] == "work_0001"
    assert route_explanation["selected_work_status"] == "closed"
    assert route_explanation["reader_drilldown_count"] >= 4
    assert route_explanation["event_ref_count"] >= 1
    assert route_explanation["evidence_ref_count"] >= 1

    assert body_floor["status"] == ("blocked" if body_floor_blocked else "pass")
    assert body_floor["body_text_exported_in_status"] is False
    assert body_floor["body_text_exported_in_receipts"] is False
    assert body_floor["public_safe_body_material_count"] == (
        status_card["substrate_counts"]["copied_non_secret_macro_body_material_count"]
    )
    assert body_floor["public_safe_body_material_count"] >= 1
    assert body_floor["verified_source_module_family_count"] >= 1
    assert body_floor["latest_verified_source_module_family_ids"]
    assert body_floor_pointer["ref"] == "front_door.source_open_body_import_floor"
    assert body_floor_pointer["public_safe_body_material_count"] == (
        body_floor["public_safe_body_material_count"]
    )
    assert intake_card["status"] == "pass"
    assert intake_card["surface_counts"]["open_actionable_cell_count"] == 0
    assert intake_card["surface_counts"]["projection_cell_count"] >= 1
    assert intake_card["projection_status_counts"]["public_runtime_import_landed"] >= 1

    assert front_door["observatory"]["status"] == "pass"
    assert front_door["observatory"]["compact_endpoint"] == "/project/observatory-card"
    assert front_door["observatory"]["project_observe_command"] == (
        "microcosm observe <project>"
    )
    assert front_door["observatory"]["model_field_count"] >= 10
    assert front_door["observatory"]["first_screen_route_proof_ref"] == (
        "microcosm serve <project>::first_screen_route_proof"
    )
    assert observatory["front_door_status"]["status"] == (
        "blocked" if body_floor_blocked else "pass"
    )
    assert observatory_card["status"] == ("blocked" if body_floor_blocked else "pass")
    assert observatory_card["selected_route_id"] == selected_route_id
    assert observatory_card["surface_statuses"]["route"] == "pass"
    assert observatory_card["surface_statuses"]["work"] == "pass"
    assert observatory_card["surface_statuses"]["evidence"] == "pass"
    assert observatory_card["surface_statuses"]["graph"] == "pass"
    assert observatory_card["surface_statuses"]["state_inspection"] == "pass"
    assert observatory_card["surface_statuses"]["proof_lab"] == "pass"
    assert observatory_card["state_inspection"]["status"] == "pass"
    assert observatory_card["state_inspection"]["missing_first_screen_refs"] == []
    assert observatory_card["state_inspection"]["state_file_count"] >= 8
    assert ".microcosm/graph.json" in (
        observatory_card["state_inspection"]["first_screen_refs"]
    )
    assert observatory_card["surface_status_refs"]["route"] == (
        ".microcosm/routes.json::readme_onboarding_route"
    )
    assert observatory_card["surface_status_refs"]["work"] == (
        ".microcosm/work_items.json"
    )
    assert observatory_card["surface_status_refs"]["graph"] == (
        ".microcosm/graph.json"
    )
    assert observatory_card["status_card_endpoint"] == "/project/status"
    assert observatory_card["surface_status_refs"]["status_card"] == (
        "/project/status"
    )
    assert causal_summary["route"]["route_id"] == selected_route_id
    assert causal_summary["work_transaction"]["work_id"] == "work_0001"
    assert causal_summary["work_transaction"]["status"] == "closed"
    assert causal_summary["work_transaction"]["source_files_mutated"] is False
    assert causal_summary["graph"]["graph_ref"] == ".microcosm/graph.json"
    assert causal_summary["event_rows_shown"] >= 4
    assert causal_summary["evidence_rows_shown"] >= 4

    assert proof_lab["status"] == "pass"
    assert proof_lab["route_id"] == "formal_prover_context_strategy_gate"
    assert proof_lab["lean_lake_return_code"] == 0
    assert proof_lab["safe_to_show"]["credential_equivalent_payloads_omitted"] is True
    assert proof_lab["safe_to_show"]["provider_payloads_omitted"] is True
    assert proof_lab["safe_to_show"]["proof_bodies_omitted"] is True
    assert status_card["authority_ceiling"]["credential_equivalent_payloads_exported"] is False
    assert status_card["authority_ceiling"]["provider_calls_authorized"] is False
    assert status_card["front_door"]["proof_lab"]["proof_bodies_exported"] is False
    assert status_card["payload_boundary_audit"]["status"] == "pass"
    assert status_card["payload_boundary_audit"]["omitted_payload_schema_hit_count"] == 0

    for relative in [
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/evidence/explain_readme_onboarding_route.json",
        ".microcosm/graph.json",
        ".microcosm/explanations/readme_onboarding_route.json",
    ]:
        assert (project / relative).is_file()
