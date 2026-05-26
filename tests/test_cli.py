from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core import project_substrate
from microcosm_core.runtime_shell import (
    PROOF_LAB_FIRST_SCREEN_COMMAND,
    PROOF_LAB_RECEIPT_REF,
    PROOF_LAB_ROUTE_REF,
    RuntimeShell,
    SOURCE_OPEN_BODY_POLICY,
    VERIFIER_EXECUTION_LENS_COMMAND,
    VERIFIER_EXECUTION_RECEIPT_REF,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def _copytree_fixture(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=FIXTURE_COPY_IGNORE)


def _copy_public_entry_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    _copytree_fixture(MICROCOSM_ROOT / "core", public_root / "core")
    _copytree_fixture(MICROCOSM_ROOT / "atlas", public_root / "atlas")
    _copytree_fixture(MICROCOSM_ROOT / "paper_modules", public_root / "paper_modules")
    _copytree_fixture(MICROCOSM_ROOT / "skills", public_root / "skills")
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENTS.md", public_root / "AGENTS.md")
    (public_root / "receipts/first_wave").mkdir(parents=True)
    return public_root


def _copy_runtime_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    _copytree_fixture(MICROCOSM_ROOT / "core", public_root / "core")
    _copytree_fixture(MICROCOSM_ROOT / "examples", public_root / "examples")
    _copytree_fixture(MICROCOSM_ROOT / "src", public_root / "src")
    _copytree_fixture(
        MICROCOSM_ROOT / "receipts/first_wave",
        public_root / "receipts/first_wave",
    )
    _copytree_fixture(
        MICROCOSM_ROOT / "receipts/preflight",
        public_root / "receipts/preflight",
    )
    return public_root


def _copy_workingness_root(tmp_path: Path) -> Path:
    public_root = _copy_runtime_root(tmp_path)
    _copytree_fixture(MICROCOSM_ROOT / "standards", public_root / "standards")
    return public_root


def _make_scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch"
    (project / "src/app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "scratch"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_app.py").write_text(
        "from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_package_metadata_describes_runtime_spine() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload["project"]
    description = project["description"]

    assert "repo -> .microcosm" in description
    assert "inspectable work substrate" in description
    assert "first-slice" not in description
    assert project["readme"] == "README.md"
    assert project["license"] == {"file": "LICENSE"}
    assert project["authors"] == [{"name": "Microcosm Substrate Contributors"}]
    assert project["optional-dependencies"]["test"] == ["pytest>=8,<9"]
    assert "License :: OSI Approved :: Apache Software License" in project["classifiers"]
    assert payload["project"]["urls"]["Homepage"] == "https://github.com/wcook04/ai-workflow-proof"
    assert (MICROCOSM_ROOT / "LICENSE").read_text(encoding="utf-8").startswith("Apache License")


def test_cli_help_routes_cold_readers_before_drilldown_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    first_line = output.splitlines()[0]
    assert first_line == "usage: microcosm [-h] <command> ..."
    assert "{init,index" not in first_line
    assert "First-screen route:" in output
    assert (
        "microcosm tour <project>        build .microcosm and inspect "
        "route/work/event/evidence/proof refs"
    ) in output
    assert (
        "microcosm tour --card <project> read the compact first-screen tour lens"
        in output
    )
    assert (
        "microcosm status --card <project> read the compressed "
        "project/runtime status lens"
    ) in output
    assert "microcosm spine --card          read the compact runtime spine lens" in output
    assert "microcosm authority --card      read the compact authority ceiling lens" in output
    assert (
        "microcosm intake --card         read the compact intake/projection bridge lens"
        in output
    )
    assert (
        "microcosm workingness --card    read the compact behavior/failure lens"
        in output
    )
    assert "microcosm workingness           inspect behavior evidence and failure gaps" in output
    assert "microcosm proof-lab --card      read the cached verifier-lab receipt card" in output
    assert "microcosm proof-lab --out /tmp/microcosm-proof-lab" in output
    assert "microcosm serve <project>       open the local observatory" in output
    assert (
        "microcosm compile --card <project> read cached .microcosm state "
        "without rebuilding"
    ) in output
    assert (
        "microcosm compile <project>     rebuild local .microcosm state "
        "after the first-screen check"
    ) in output
    assert output.index("microcosm tour <project>") < output.index(
        "microcosm tour --card <project>"
    )
    assert output.index("microcosm tour --card <project>") < output.index(
        "microcosm status --card <project>"
    )
    assert output.index("microcosm status --card <project>") < output.index(
        "microcosm spine --card"
    )
    assert output.index("microcosm spine --card") < output.index(
        "microcosm authority --card"
    )
    assert output.index("microcosm authority --card") < output.index(
        "microcosm intake --card"
    )
    assert output.index("microcosm intake --card") < output.index(
        "microcosm workingness --card"
    )
    assert output.index("microcosm workingness --card") < output.index(
        "microcosm workingness           inspect behavior evidence and failure gaps"
    )
    assert output.index("microcosm workingness") < output.index(
        "microcosm proof-lab --card"
    )
    assert output.index("microcosm proof-lab --card") < output.index(
        "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    )
    assert output.index(
        "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    ) < output.index("microcosm serve <project>")
    assert output.index("microcosm serve <project>") < output.index(
        "microcosm compile --card <project>"
    )
    assert output.index("microcosm compile --card <project>") < output.index(
        "microcosm compile <project>"
    )
    assert "no provider calls, source mutation, release," in output
    assert "Receipts are evidence drilldowns after the behavior route is visible." in output
    for command in [
        "compile",
        "python-lens",
        "explain",
        "status",
        "proof-lab",
        "spine",
        "tour",
        "authority",
        "serve",
        "evidence",
    ]:
        assert command in output
    for command in [
        "workingness",
        "prediction-lens",
        "market-boundary",
        "corpus-lens",
        "trace-lens",
        "repair-loop",
        "evidence-cells",
        "proof-loop-depth",
        "verifier-lab-execution-spine-lens",
        "landing-replay",
        "view-quality",
        "projection-safety",
        "drift-control",
        "spatial-simulation",
        "circuit-attribution",
        "route-cleanup",
        "projection-import-map",
        "import-projector",
        "option-surface-lens",
        "stripping-guard",
        "standards-control",
        "hook-coverage",
        "replay-gauntlet",
        "benchmark-lab",
        "legibility-scorecard",
        "intake",
        "reveal",
    ]:
        assert command in output
    for help_text in [
        "inspect proof loop depth without proving correctness",
        "show navigation route cleanup evidence",
        "show runtime projection intake board",
        "show public reveal walkthrough board",
    ]:
        assert help_text in output
    for drilldown_command in [
        "private-state-scan",
        "macro-projection-import-protocol",
        "verifier-lab-kernel",
        "agentic-vulnerability-discovery-patch-proof-replay",
    ]:
        assert drilldown_command not in output


def test_cli_status_card_can_overlay_project_route_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    project_substrate.compile_project(project)

    assert cli.main(["status", "--card", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(json.dumps(payload, sort_keys=True)) < 11000
    assert payload["card_command"] == "microcosm status --card <project>"
    assert payload["source_files_mutated"] is False
    assert "next_commands" not in payload
    assert payload["front_door"]["front_door_status_ref"] == (
        "microcosm status --card <project>::front_door_status"
    )
    front_door_status = payload["front_door_status"]
    assert front_door_status["status"] == "pass"
    assert front_door_status["blocking_surface_ids"] == []
    assert front_door_status["actionable_surface_ids"] == []
    assert front_door_status["surface_statuses"]["project_state"] == "pass"
    assert front_door_status["surface_statuses"]["route_selection_proof"] == "pass"
    assert front_door_status["surface_statuses"]["route_explanation"] == "pass"
    assert front_door_status["surface_statuses"]["proof_lab"] == "pass"
    assert front_door_status["surface_statuses"]["observatory"] == "pass"
    assert "required_surface_ids" not in front_door_status
    assert (
        front_door_status["surface_statuses"]["workingness_failure_envelope"]
        == "clear"
    )
    assert (
        front_door_status["drilldown_blocked_surface_ids_ref"]
        == "microcosm tour <project>::front_door_status."
        "drilldown_blocked_surface_ids"
    )
    assert payload["front_door"]["project_state_status"] == "pass"
    assert payload["front_door"]["selected_route_id"] == "readme_onboarding_route"
    route_selection_proof = payload["front_door"]["route_selection_proof"]
    assert route_selection_proof["status"] == "pass"
    assert (
        route_selection_proof["schema_version"]
        == "microcosm_project_route_selection_proof_v1"
    )
    assert route_selection_proof["selected_route_id"] == "readme_onboarding_route"
    assert route_selection_proof["route_id_available_in_state"] is True
    assert route_selection_proof["route_explanation_status"] == "pass"
    assert route_selection_proof["observatory_route_proof_ref"] == (
        "microcosm serve <project>::first_screen_route_proof"
    )
    assert payload["front_door"]["route_explanation_command"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    route_explanation = payload["front_door"]["route_explanation"]
    assert route_explanation["status"] == "pass"
    assert route_explanation["route_id"] == "readme_onboarding_route"
    assert route_explanation["selected_work_status"] == "closed"
    assert route_explanation["source_files_mutated"] is False
    assert route_explanation["event_ref_count"] >= 1
    assert route_explanation["evidence_ref_count"] >= 1
    assert route_explanation["reader_drilldown_count"] == 4
    assert route_explanation["drilldown_ref"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    assert "reader_drilldowns" not in route_explanation
    assert "readme_onboarding_route" in payload["front_door"][
        "available_project_route_ids"
    ]
    assert payload["front_door"]["project_state"]["state_dir_exists"] is True
    assert payload["front_door"]["project_state"][
        "available_project_route_id_count"
    ] >= len(payload["front_door"]["project_state"]["available_project_route_ids"])
    proof_lab = payload["front_door"]["proof_lab"]
    assert proof_lab["status"] == "pass"
    assert proof_lab["endpoint"] == "/proof-lab"
    assert proof_lab["route_id"] == "formal_prover_context_strategy_gate"
    assert proof_lab["route_component_count"] == 9
    assert proof_lab["proof_bodies_exported"] is False
    assert proof_lab["proof_correctness_claim"] is False
    observatory = payload["front_door"]["observatory"]
    assert observatory["status"] == "pass"
    assert observatory["command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert observatory["endpoint"] == "/project/observatory"
    assert observatory["compact_endpoint"] == "/project/observatory-card"
    assert observatory["route_explanation_endpoint"] == (
        "/project/explain/readme_onboarding_route"
    )
    assert observatory["first_screen_route_proof_ref"] == (
        "microcosm serve <project>::first_screen_route_proof"
    )
    assert observatory["source_files_mutated"] is False
    assert observatory["provider_calls_authorized"] is False
    assert observatory["model_field_count"] == 13
    body_floor = payload["front_door"]["source_open_body_import_floor"]
    assert body_floor["status"] == "pass"
    assert body_floor["summary_ref"] == (
        "microcosm status --card::macro_body_import_floor"
    )
    assert (
        body_floor["public_safe_body_material_count"]
        == payload["substrate_counts"][
            "copied_non_secret_macro_body_material_count"
        ]
    )
    assert body_floor["verified_source_module_family_count"] >= 20
    assert body_floor["latest_verified_source_module_family_ids"]
    assert all(
        isinstance(family_id, str)
        for family_id in body_floor["latest_verified_source_module_family_ids"]
    )
    assert body_floor["body_text_exported_in_status"] is False
    assert body_floor["body_text_exported_in_receipts"] is False


def test_cli_tour_on_fresh_project_exposes_first_screen_microcosm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_tour = MICROCOSM_ROOT / "receipts/runtime_shell/public_ten_minute_tour.json"
    source_tour_before = source_tour.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)
    project = _make_scratch_project(tmp_path)

    assert cli.main(["tour", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)
    first_screen = payload["first_screen"]
    front_door_status = payload["front_door_status"]

    assert payload["status"] == "pass"
    assert first_screen["schema_version"] == "microcosm_cold_reader_first_screen_v1"
    assert first_screen["intent"] == "bring_folder_run_local_path_inspect_state_then_drill_receipts"
    assert first_screen["selected_route_id"] == "readme_onboarding_route"
    assert first_screen["generated_state"]["state_dir"] == ".microcosm"
    expected_state_refs = {
        ".microcosm/project_manifest.json",
        ".microcosm/architecture.json",
        ".microcosm/state_index.json",
        ".microcosm/graph.json",
        ".microcosm/catalog.json",
        ".microcosm/python_lens.json",
        ".microcosm/patterns.json",
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/explanations/",
        ".microcosm/evidence/",
    }
    assert set(first_screen["generated_state"]["refs"]) == expected_state_refs
    for ref in expected_state_refs:
        assert (project / ref).exists()
    assert first_screen["behavior_surfaces"] == {
        "route_state_ref": ".microcosm/routes.json",
        "work_state_ref": ".microcosm/work_items.json",
        "event_log_ref": ".microcosm/events.jsonl",
        "evidence_dir_ref": ".microcosm/evidence/",
        "graph_ref": ".microcosm/graph.json",
        "observatory_command": "microcosm serve <project> --host 127.0.0.1 --port 8765",
    }
    assert first_screen["route_explanation"]["command"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    assert first_screen["route_explanation"]["endpoint"] == (
        "/project/explain/readme_onboarding_route"
    )
    assert first_screen["proof_surface"]["status"] == "pass"
    assert first_screen["proof_surface"]["route_id"] == "formal_prover_context_strategy_gate"
    assert first_screen["safe_to_show"]["project_local_state_refs_visible"] is True
    assert first_screen["safe_to_show"]["credential_equivalent_payloads_exported"] is False
    assert first_screen["safe_to_show"]["receipt_refs_visible_after_behavior"] is True
    assert front_door_status["status"] == "pass"
    assert front_door_status["blocking_surface_ids"] == []
    assert front_door_status["drilldown_warning_surface_ids"] == [
        "authority",
        "intake",
    ]
    assert front_door_status["safe_to_show"]["blocking_surface_ids_visible"] is True
    step_ids = [row["step_id"] for row in first_screen["minimal_command_path"]]
    assert step_ids.index("inspect_first_screen") < step_ids.index(
        "drill_receipts_only_after_behavior"
    )
    assert step_ids.index("inspect_status_and_workingness") < step_ids.index(
        "compile_project"
    )
    assert step_ids.index("run_first_screen_proof_lab") < step_ids.index(
        "inspect_python_routes"
    )
    observatory_step = {
        row["step_id"]: row for row in first_screen["minimal_command_path"]
    }["open_observatory"]
    assert observatory_step["endpoint"] == "/project/observatory-card"
    assert observatory_step["expanded_endpoint"] == "/project/observatory"

    assert cli.main(["status", "--card", str(project)]) == 0
    status_card = json.loads(capsys.readouterr().out)
    assert len(json.dumps(status_card, sort_keys=True)) < 11000
    assert status_card["status"] == "pass"
    assert status_card["front_door_status"]["blocking_surface_ids"] == []
    assert status_card["front_door_status"]["actionable_surface_ids"] == [
        "workingness_failure_envelope"
    ]
    assert (
        status_card["front_door_status"]["surface_statuses"]["project_state"]
        == "pass"
    )
    assert status_card["front_door"]["project_state_status"] == "pass"
    assert status_card["front_door"]["selected_route_id"] == "readme_onboarding_route"
    assert status_card["front_door"]["route_selection_proof"]["status"] == "pass"
    assert (
        status_card["front_door_status"]["surface_statuses"][
            "route_selection_proof"
        ]
        == "pass"
    )
    assert status_card["front_door_status"]["surface_statuses"]["proof_lab"] == "pass"
    assert status_card["front_door_status"]["surface_statuses"]["observatory"] == "pass"
    assert status_card["front_door"]["state_dir_exists"] is True
    assert status_card["front_door"]["route_explanation"]["status"] == "pass"
    assert status_card["front_door"]["route_explanation"][
        "selected_work_status"
    ] == "closed"
    assert status_card["front_door"]["route_explanation"][
        "source_files_mutated"
    ] is False
    assert status_card["workingness"]["status"] == "actionable"
    assert status_card["proof_lab"]["status"] == "pass"
    assert status_card["front_door"]["proof_lab"]["status"] == "pass"
    assert (
        status_card["front_door"]["proof_lab"]["receipt_ref"]
        == PROOF_LAB_RECEIPT_REF
    )
    assert status_card["front_door"]["observatory"]["endpoint"] == (
        "/project/observatory"
    )
    assert status_card["front_door"]["observatory"]["compact_endpoint"] == (
        "/project/observatory-card"
    )
    assert status_card["front_door"]["observatory"]["status"] == "pass"
    assert status_card["macro_body_import_floor"]["schema_version"] == (
        "microcosm_project_status_body_import_floor_ref_v1"
    )
    assert status_card["macro_body_import_floor"]["project_mode_compacted"] is True
    assert status_card["macro_body_import_floor"]["ref"] == (
        "front_door.source_open_body_import_floor"
    )
    assert (
        status_card["macro_body_import_floor"]["verified_source_module_family_count"]
        == status_card["front_door"]["source_open_body_imports"][
            "verified_source_module_family_count"
        ]
    )
    assert status_card["payload_boundary_audit"]["status"] == "pass"
    assert source_tour.read_text(encoding="utf-8") == source_tour_before


def test_cli_status_card_matches_observatory_card_reader_lens(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)

    assert cli.main(["tour", str(project)]) == 0
    capsys.readouterr()
    assert cli.main(["status", "--card", str(project)]) == 0
    status_card = json.loads(capsys.readouterr().out)
    observatory = RuntimeShell(MICROCOSM_ROOT).project_observatory(
        project,
        persist_receipts=False,
    )
    observatory_card = observatory["observatory_card"]

    status_front_door = status_card["front_door"]
    status_front_door_status = status_card["front_door_status"]
    status_body_floor = status_front_door["source_open_body_import_floor"]
    observatory_body_floor = observatory_card["source_open_body_import_floor"]

    assert status_front_door_status["status"] == "pass"
    assert observatory_card["status"] == "pass"
    assert observatory["front_door_status"]["status"] == "pass"
    assert status_front_door_status["blocking_surface_ids"] == []
    assert observatory_card["first_screen_route_proof"]["blocking_surface_ids"] == []
    assert status_front_door["proof_lab"]["status"] == "pass"
    assert observatory_card["proof_lab"]["status"] == "pass"
    assert status_front_door["proof_lab"]["route_id"] == (
        observatory_card["proof_lab"]["route_id"]
    )
    assert status_front_door["observatory"]["status"] == "pass"
    assert status_front_door["observatory"]["compact_endpoint"] == (
        observatory_card["endpoint"]
    )
    assert observatory["observatory_card"] == observatory_card
    assert status_card["payload_boundary_audit"]["status"] == "pass"
    assert observatory_card["safe_to_show"]["provider_calls_authorized"] is False
    assert observatory_card["safe_to_show"]["source_files_mutated"] is False
    assert observatory_card["safe_to_show"]["proof_correctness_claim"] is False
    assert (
        status_body_floor["public_safe_body_material_count"]
        == observatory_body_floor["public_safe_body_material_count"]
    )
    assert (
        status_body_floor["public_safe_body_material_counts_by_class"]
        == observatory_body_floor["public_safe_body_material_counts_by_class"]
    )
    assert status_body_floor["latest_verified_source_module_family_ids"] == (
        observatory_body_floor["latest_verified_source_module_family_ids"]
    )
    assert status_body_floor["body_text_exported_in_status"] is False
    assert observatory_body_floor["body_text_exported_in_status"] is False
    assert observatory_body_floor["body_text_exported_in_receipts"] is False


def test_cli_pattern_route_readiness_accepts_exported_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "pattern-route-readiness"
    status = cli.main(
        [
            "pattern-route-readiness",
            "validate-bundle",
            "--input",
            str(MICROCOSM_ROOT / "examples/pattern_binding_contract/exported_route_readiness_bundle"),
            "--out",
            str(out_dir),
        ]
    )

    result = json.loads(
        (out_dir / "exported_route_readiness_bundle_validation_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert status == 0
    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_route_readiness_bundle"
    assert result["route_readiness_summary"]["status"] == "ok"
    assert result["selection_contract"]["selector_must_open"] == [
        "row_to_organ_router",
        "organ_route_cards",
        "organ_fixture_specs",
        "route_readiness_audit",
    ]
    assert result["authority_ceiling"]["public_leaf_authority"] is False


def test_cli_spine_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["spine"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_runtime_spine_v1"
    assert payload["status"] == "pass"
    assert payload["surface_counts"]["adapter_backed_organ_count"] == 43
    assert payload["surface_counts"]["product_path_demoted_organ_count"] == 4
    assert payload["first_run_path"][0]["command"] == "microcosm tour <project>"
    assert payload["first_run_path"][2]["command"] == "microcosm python-lens <project>"
    assert payload["first_run_path"][5]["command"] == "microcosm spine"
    assert payload["first_run_path"][6]["command"] == "microcosm authority"
    assert payload["first_run_path"][7]["command"] == "microcosm prediction-lens"
    assert payload["first_run_path"][8]["command"] == "microcosm market-boundary"
    assert payload["first_run_path"][9]["command"] == "microcosm corpus-lens"
    assert payload["first_run_path"][10]["command"] == "microcosm trace-lens"
    assert payload["first_run_path"][11]["command"] == "microcosm repair-loop"
    assert payload["first_run_path"][12]["command"] == "microcosm evidence-cells"
    assert payload["first_run_path"][13]["command"] == "microcosm proof-loop-depth"
    assert payload["first_screen_proof_lab"]["status"] == "pass"
    assert payload["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_run_path"][14]["command"] == PROOF_LAB_FIRST_SCREEN_COMMAND
    assert payload["first_run_path"][14]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert payload["first_run_path"][14]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert payload["first_run_path"][15]["command"] == VERIFIER_EXECUTION_LENS_COMMAND
    assert payload["first_run_path"][15]["receipt_ref"] == VERIFIER_EXECUTION_RECEIPT_REF
    assert payload["first_run_path"][14]["route_component_count"] == 9
    assert payload["first_run_path"][16]["command"] == "microcosm landing-replay"
    assert payload["first_run_path"][17]["command"] == (
        "microcosm durable-agent-work-landing-replay run-work-landing-bundle"
    )
    assert payload["first_run_path"][18]["command"].startswith(
        "microcosm research-replication-rubric-artifact-replay"
    )
    assert payload["first_run_path"][19]["command"] == "microcosm view-quality"
    assert payload["first_run_path"][20]["command"] == "microcosm projection-safety"
    assert payload["first_run_path"][21]["command"] == "microcosm drift-control"
    assert payload["first_run_path"][22]["command"].startswith(
        "microcosm world-model-projection-drift-control-room"
    )
    assert payload["first_run_path"][23]["command"].startswith(
        "microcosm spatial-world-model-counterfactual-simulation-replay"
    )
    assert payload["first_run_path"][24]["command"].startswith(
        "microcosm mechanistic-interpretability-circuit-attribution-replay"
    )
    assert payload["first_run_path"][25]["command"] == "microcosm route-cleanup"
    assert payload["first_run_path"][26]["command"] == "microcosm projection-import-map"
    assert payload["first_run_path"][27]["command"] == "microcosm import-projector"
    assert payload["first_run_path"][28]["command"] == "microcosm option-surface-lens"
    assert payload["first_run_path"][29]["command"] == "microcosm stripping-guard"
    assert payload["first_run_path"][30]["command"] == "microcosm standards-control"
    assert payload["first_run_path"][31]["command"] == "microcosm hook-coverage"
    assert payload["first_run_path"][32]["command"] == "microcosm replay-gauntlet"
    assert payload["first_run_path"][33]["command"].startswith(
        "microcosm agent-memory-temporal-conflict-replay"
    )
    assert payload["first_run_path"][34]["command"].startswith(
        "microcosm sleeper-memory-poisoning-quarantine-replay"
    )
    assert payload["first_run_path"][35]["command"].startswith(
        "microcosm mcp-tool-authority-replay"
    )
    assert payload["first_run_path"][36]["command"].startswith(
        "microcosm proof-derived-governed-mutation-authorization"
    )
    assert payload["first_run_path"][37]["command"].startswith(
        "microcosm belief-state-process-reward-replay"
    )
    assert payload["first_run_path"][38]["command"].startswith(
        "microcosm agent-sandbox-policy-escape-replay"
    )
    assert payload["first_run_path"][39]["command"].startswith(
        "microcosm indirect-prompt-injection-information-flow-policy-replay"
    )
    assert payload["first_run_path"][40]["command"].startswith(
        "microcosm agentic-vulnerability-discovery-patch-proof-replay"
    )
    assert payload["first_run_path"][41]["command"].startswith(
        "microcosm certificate-kernel-execution-lab"
    )
    assert payload["first_run_path"][42]["command"] == "microcosm benchmark-lab"
    assert payload["first_run_path"][43]["command"] == "microcosm legibility-scorecard"
    assert payload["first_run_path"][46]["command"] == "microcosm cold-reader-route-map run-route-map-bundle"
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_authority_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_authority = (
        MICROCOSM_ROOT / "receipts/runtime_shell/public_authority_map.json"
    )
    source_reveal = (
        MICROCOSM_ROOT
        / "receipts/runtime_shell/public_reveal/public_reveal_view.json"
    )
    source_authority_before = source_authority.read_text(encoding="utf-8")
    source_reveal_before = source_reveal.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["authority"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_authority_map_v2"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm authority"
    assert payload["unsafe_payload_bodies_exported"] is False
    assert payload["payload_boundary"]["source_open_default"] is True
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["surface_counts"]["organ_authority_count"] == 43
    assert payload["surface_counts"]["surface_authority_count"] == 45
    assert payload["surface_counts"]["organ_evidence_class_count"] == 4
    assert payload["surface_counts"]["copied_non_secret_macro_body_count"] == 1
    assert payload["surface_counts"]["copied_non_secret_macro_body_material_count"] == 286
    assert payload["surface_counts"]["mixed_public_safe_macro_import_assay_status"] == "pass"
    assert payload["evidence_class_registry"]["fail_closed_no_default"] is True
    assert payload["evidence_class_counts"] == {
        "semantic_validator": 16,
        "algorithmic_projection": 23,
        "external_subprocess_witness": 3,
        "verified_macro_body_import": 1,
    }
    organ_authority_by_id = {row["organ_id"]: row for row in payload["organ_authority"]}
    assert (
        organ_authority_by_id["materials_chemistry_closed_loop_lab_safety_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["agent_sandbox_policy_escape_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["formal_math_lean_proof_witness"]["evidence_class"]
        == "external_subprocess_witness"
    )
    assert (
        organ_authority_by_id["verifier_lab_kernel"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["proof_diagnostic_evidence_spine"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["durable_agent_work_landing_replay"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["proof_derived_governed_mutation_authorization"][
            "evidence_class"
        ]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["world_model_projection_drift_control_room"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["spatial_world_model_counterfactual_simulation_replay"][
            "evidence_class"
        ]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id[
            "mechanistic_interpretability_circuit_attribution_replay"
        ]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["research_replication_rubric_artifact_replay"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["agentic_vulnerability_discovery_patch_proof_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert any(row["surface_id"] == "project_python_lens" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/authority" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/tour" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/market-boundary" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/hook-coverage" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/replay-gauntlet" for row in payload["surface_authority"])
    assert any(
        row["surface_id"] == "public_verifier_lab_kernel_lens"
        and row["provider_hypothesis_proof_authority"] is False
        and row["route_id"] == "formal_prover_context_strategy_gate"
        and row["receipt_ref"] == PROOF_LAB_RECEIPT_REF
        and row["route_component_count"] == 9
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_verifier_lab_execution_spine_lens"
        and row["bounded_public_external_witness_only"] is True
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_sabotage_scheming_monitor_replay_lens"
        and row["runtime_mode"] == "drilldown_only"
        and row["product_path_role"] == "drilldown_regression_not_runtime_spine"
        for row in payload["surface_authority"]
    )
    assert any(row["surface_id"] == "public_mcp_tool_authority_replay_lens" for row in payload["surface_authority"])
    assert any(
        row["surface_id"]
        == "public_proof_derived_governed_mutation_authorization_lens"
        for row in payload["surface_authority"]
    )
    assert source_authority.read_text(encoding="utf-8") == source_authority_before
    assert source_reveal.read_text(encoding="utf-8") == source_reveal_before
    assert any(
        row["surface_id"] == "public_belief_state_process_reward_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_sandbox_policy_escape_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_indirect_prompt_injection_information_flow_policy_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(row["endpoint"] == "/corpus" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/trace" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/repair-loop" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/evidence-cells" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/proof-loop-depth" for row in payload["surface_authority"])
    assert any(
        row["endpoint"] == "/verifier-lab-execution-spine"
        for row in payload["surface_authority"]
    )
    assert any(row["endpoint"] == "/landing-replay" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/view-quality" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/projection-safety" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/drift-control" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/spatial-simulation" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/circuit-attribution" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/route-cleanup" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/projection-import-map" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/import-projector" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/option-surface-lens" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/stripping-guard" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/standards-control" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/benchmark-lab" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/legibility-scorecard" for row in payload["surface_authority"])


def test_cli_workingness_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_workingness_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["workingness"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_workingness_failure_map_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm workingness"
    assert payload["endpoint"] == "/workingness"
    assert payload["completeness_status"] == "complete_failure_modes"
    assert payload["map_generation_status"] == "pass"
    assert payload["failure_envelope_status"] == "clear"
    assert payload["mapped_organ_count"] == 47
    assert payload["adapter_backed_organ_count"] == 43
    assert payload["demoted_drilldown_count"] == 4
    assert payload["missing_standard_count"] == 0
    assert payload["missing_failure_modes_count"] == 0
    assert payload["rows_with_failure_modes"] == 47
    assert payload["accepted_status_is_not_evidence_strength"] is True
    assert payload["not_a_scorecard"] is True
    assert payload["gap_preview"]["status"] == "clear"
    assert payload["surface_counts"]["mapped_organ_count"] == 47
    assert payload["surface_counts"]["adapter_backed_organ_count"] == 43
    assert payload["surface_counts"]["demoted_drilldown_count"] == 4
    assert payload["surface_counts"]["missing_failure_modes_count"] == 0
    rows_by_id = {row["thing_id"]: row for row in payload["thing_failure_map"]}
    assert rows_by_id["verifier_lab_kernel"]["workingness_state"] == (
        "evidence_backed_runtime_spine"
    )
    assert rows_by_id["agent_monitor_redteam_falsification_replay"][
        "workingness_state"
    ] == "demoted_regression_drilldown"
    assert (public_root / payload["workingness_map_ref"]).is_file()


def test_cli_workingness_card_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_workingness_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["workingness", "--card"])

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert status == 0
    assert payload["schema_version"] == "microcosm_workingness_command_speed_card_v1"
    assert payload["status"] == "pass"
    assert payload["card_status"] == "clear"
    assert payload["command"] == "microcosm workingness --card"
    assert payload["source_command"] == "microcosm workingness"
    assert payload["drilldown_command"] == "microcosm workingness"
    assert payload["endpoint"] == "/workingness"
    assert payload["completeness_status"] == "complete_failure_modes"
    assert payload["surface_counts"]["mapped_organ_count"] == 47
    assert payload["surface_counts"]["adapter_backed_organ_count"] == 43
    assert payload["surface_counts"]["demoted_drilldown_count"] == 4
    assert payload["surface_counts"]["rows_with_failure_modes"] == 47
    assert payload["surface_counts"]["missing_standard_count"] == 0
    assert payload["surface_counts"]["missing_failure_modes_count"] == 0
    assert payload["output_economy"]["thing_failure_map_exported"] is False
    assert payload["output_economy"]["known_failure_mode_rows_exported"] is False
    assert payload["output_economy"]["receipt_persisted"] is False
    assert "thing_failure_map" not in payload
    assert "known_failure_modes" not in encoded
    assert len(encoded) < 8000
    assert not (
        public_root / "receipts/runtime_shell/workingness_failure_map.json"
    ).exists()


def test_cli_tour_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_tour = MICROCOSM_ROOT / "receipts/runtime_shell/public_ten_minute_tour.json"
    source_tour_before = source_tour.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["tour"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm tour <project>"
    assert payload["endpoint"] == "/tour"
    assert payload["time_budget_minutes"] == 10
    assert payload["compile_summary"]["headline"] == "repo -> .microcosm"
    assert payload["snapshot_policy"]["test_runs_should_use_temp_public_root"] is True
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["first_screen"]["schema_version"] == (
        "microcosm_cold_reader_first_screen_v1"
    )
    assert payload["first_screen"]["primary_command"] == "microcosm tour <project>"
    assert payload["first_screen"]["minimal_command_path"][0]["command"] == (
        payload["first_screen"]["primary_command"]
    )
    assert payload["first_screen"]["selected_route_id"] == (
        payload["compile_summary"]["selected_route_id"]
    )
    assert payload["selected_route_id"] == payload["first_screen"]["selected_route_id"]
    assert payload["first_screen"]["route_explanation"]["command"] == (
        f"microcosm explain <project> {payload['first_screen']['selected_route_id']}"
    )
    assert payload["first_screen"]["generated_state"]["state_dir"] == ".microcosm"
    assert payload["first_screen"]["proof_surface"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_screen"]["behavior_surfaces"]["observatory_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert "microcosm status --card" in payload["command_path"]
    assert "microcosm workingness" in payload["command_path"]
    assert "/workingness" in payload["endpoint_path"]
    assert any(
        row["step_id"] == "inspect_status_and_workingness"
        for row in payload["first_screen"]["minimal_command_path"]
    )
    tour_step_ids = [
        row["step_id"] for row in payload["first_screen"]["minimal_command_path"]
    ]
    assert tour_step_ids.index("inspect_status_and_workingness") < tour_step_ids.index(
        "compile_project"
    )
    assert tour_step_ids.index("run_first_screen_proof_lab") < tour_step_ids.index(
        "inspect_python_routes"
    )
    assert any(
        card["card_id"] == "status_and_workingness"
        and card["workingness_command"] == "microcosm workingness"
        for card in payload["route_cards"]
    )
    assert payload["first_screen_proof_lab"]["status"] == "pass"
    assert payload["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_screen_proof_lab"]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert payload["first_screen_proof_lab"]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert any(
        card["card_id"] == "verifier_lab_kernel"
        and card["route_component_count"] == 9
        for card in payload["route_cards"]
    )
    assert (public_root / payload["tour_ref"]).is_file()
    assert source_tour.read_text(encoding="utf-8") == source_tour_before


def test_cli_tour_card_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["tour", "--card"])

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert status == 0
    assert payload["schema_version"] == "microcosm_tour_command_speed_card_v1"
    assert payload["status"] == "pass"
    assert payload["card_status"] == "clear"
    assert payload["command"] == "microcosm tour --card <project>"
    assert payload["source_command"] == "microcosm tour <project>"
    assert payload["drilldown_command"] == "microcosm tour <project>"
    assert payload["endpoint"] == "/tour"
    assert payload["first_screen"]["primary_command"] == "microcosm tour <project>"
    assert payload["first_screen"]["minimal_step_count"] == 8
    assert payload["surface_statuses"]["compile"] == "pass"
    assert payload["surface_statuses"]["proof_lab"] == "pass"
    assert payload["surface_statuses"]["workingness_card"] == "pass"
    assert payload["blocking_surface_ids"] == []
    assert payload["workingness"]["command"] == "microcosm workingness --card"
    assert payload["output_economy"]["full_route_cards_exported"] is False
    assert payload["output_economy"]["route_cards_by_id_exported"] is False
    assert payload["output_economy"]["full_command_path_exported"] is False
    assert payload["output_economy"]["full_endpoint_path_exported"] is False
    assert payload["output_economy"]["receipt_persisted"] is False
    assert "route_cards" not in payload
    assert "route_cards_by_id" not in payload
    assert "endpoint_path" not in payload
    assert "command_path" not in payload
    assert len(encoded) < 10000
    assert not (
        public_root / "receipts/runtime_shell/public_ten_minute_tour.json"
    ).exists()


def test_cli_macro_projection_plan_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(
        [
            "macro-projection-import-protocol",
            "plan",
            "--input",
            (
                MICROCOSM_ROOT
                / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
            ).as_posix(),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "macro_projection_import_intake_preview_v1"
    assert payload["projection_intake_board"]["ready_cell_count"] == 31
    assert payload["projection_intake_board"]["blocked_cell_count"] == 0
    assert payload["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert payload["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_public_entry_docs_smoke_uses_temp_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    monkeypatch.chdir(public_root)
    out = Path("receipts/first_wave/public_entry_docs_validation.json")

    status = cli.main(
        [
            "public-entry-docs",
            "--root",
            ".",
            "--out",
            out.as_posix(),
        ]
    )

    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert status == 0
    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert receipt["payload_boundary"]["source_open_default"] is True
    assert receipt["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    text = out.read_text(encoding="utf-8")
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
