from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from microcosm_core import project_substrate
from microcosm_core import cli
from microcosm_core.public_payload_boundary import SOURCE_OPEN_BODY_POLICY


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/scratch_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch Project\n\nLocal proof project.\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src/scratch_app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_smoke.py").write_text(
        "from scratch_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_project_index_skips_file_that_disappears_during_walk(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    transient = (
        project
        / "receipts/runtime_shell/workingness_failure_map.json.disappearing"
    )
    transient.parent.mkdir(parents=True)
    transient.write_text("{}", encoding="utf-8")
    original_stat = Path.stat

    def stat_with_disappearing_file(
        self: Path, *args: Any, **kwargs: Any
    ) -> os.stat_result:
        if self == transient:
            raise FileNotFoundError(self)
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_with_disappearing_file)

    index_result = project_substrate.index_project(project)
    catalog_paths = {
        row["path"] for row in project_substrate.catalog_project(project)["files"]
    }

    assert index_result["status"] == "pass"
    assert index_result["file_count"] == 4
    assert (
        "receipts/runtime_shell/workingness_failure_map.json.disappearing"
        not in catalog_paths
    )


def test_project_substrate_runs_on_user_owned_scratch_project(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    init_result = project_substrate.init_project(project)
    index_result = project_substrate.index_project(project)
    catalog = project_substrate.catalog_project(project)
    architecture = project_substrate.architecture_project(project)
    python_lens = project_substrate.python_lens(project)
    patterns = project_substrate.discover_patterns(project)
    routes = project_substrate.propose_routes(project)
    explanation = project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project)
    run = project_substrate.run_work(project, str(created["work_id"]))
    post_run_explanation = project_substrate.explain_route(project, "readme_onboarding_route")
    observed = project_substrate.observe_project(project)
    graph = project_substrate.state_graph(project)
    evidence = project_substrate.list_evidence(project)
    inspected = project_substrate.inspect_evidence(project, str(run["evidence_ref"]))
    compiled = project_substrate.compile_project(project)

    assert init_result["status"] == "pass"
    assert index_result["file_count"] == 4
    assert catalog["role_counts"]["readme"] == 1
    assert catalog["role_counts"]["package_manifest"] == 1
    assert catalog["role_counts"]["source"] == 1
    assert catalog["role_counts"]["test"] == 1
    assert architecture["kernel"]["posture"] == "executable_research_prototype"
    assert "route" in architecture["primitive_ids"]
    assert architecture["pattern_surface"]["state_ref"] == ".microcosm/patterns.json"
    assert python_lens["status"] == "pass"
    assert python_lens["schema_version"] == "microcosm_project_python_lens_v1"
    assert python_lens["lens_id"] == "project_python_route_lens"
    assert python_lens["command"] == "microcosm python-lens <project>"
    assert python_lens["python_file_count"] == 2
    assert python_lens["passing_check_count"] == 4
    assert python_lens["missing_check_count"] == 1
    assert python_lens["ready_route_count"] == 3
    assert python_lens["package_roots"] == ["src/scratch_app"]
    assert python_lens["payload_boundary"]["boundary_id"] == "project_python_lens_read_model"
    assert python_lens["payload_boundary"]["source_open_default"] is True
    assert python_lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert python_lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert python_lens["safe_to_show"]["python_lens_rows_are_public_payload_boundary_rows"] is True
    assert python_lens["state_written"] is True
    assert python_lens["authority_ceiling"]["source_bodies_exported"] is False
    assert python_lens["source_span_count"] == 3
    assert python_lens["symbol_capsule_count"] == 1
    assert python_lens["graph_edge_count"] == 1
    assert python_lens["navigation_assay"]["assay_id"] == "std_python_microcosm_navigation_assay"
    assert python_lens["navigation_assay"]["canonical_depth_ladder"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert python_lens["navigation_assay"]["depth_band_coverage"] == {
        "module_docs": 0,
        "file_card": 2,
        "symbol_capsule": 1,
        "graph_context": 1,
        "source_span": 3,
    }
    assert python_lens["navigation_assay"]["probe_disposition_counts"] == {
        "file_local_defect": 0,
        "standard_amendment_candidate": 0,
        "nothing_to_refine": 4,
    }
    assert python_lens["navigation_assay"]["route_probe_tasks"][0]["expected_depth_band"] == "file_card"
    assert python_lens["navigation_assay"]["route_probe_tasks"][1]["expected_depth_band"] == "source_span"
    assert python_lens["navigation_assay"]["standard_amendment_candidate_count"] == 0
    assert python_lens["navigation_assay"]["parse_error_count"] == 0
    assert python_lens["navigation_assay"]["route_utility_task_count"] == 10
    assert python_lens["navigation_assay"]["route_utility_disposition_counts"] == {
        "local_projection_defect": 0,
        "local_source_or_test_defect": 0,
        "macro_standard_amendment_candidate": 0,
        "nothing_to_refine": 10,
    }
    assert (
        python_lens["navigation_assay"]["route_utility_ratchet_ref"]
        == ".microcosm/python_lens.json::route_utility_curriculum.ratchet"
    )
    assert python_lens["navigation_assay"]["route_utility_ratchet_status"] == (
        "curriculum_current"
    )
    assert python_lens["navigation_assay"]["route_utility_stale_task_count"] == 0
    assert python_lens["python_navigation_route"]["assay_ref"] == (
        ".microcosm/python_lens.json::navigation_assay"
    )
    assert python_lens["python_navigation_route"]["implementation_atlas_ref"] == (
        ".microcosm/python_lens.json::implementation_atlas.python_navigation_assay"
    )
    assert python_lens["python_navigation_route"]["route_utility_curriculum_ref"] == (
        ".microcosm/python_lens.json::route_utility_curriculum"
    )
    assert python_lens["python_navigation_route"]["route_utility_ratchet_ref"] == (
        ".microcosm/python_lens.json::route_utility_curriculum.ratchet"
    )
    assert python_lens["python_navigation_route"]["canonical_depth_ladder"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"]["assay_id"]
        == "std_python_microcosm_navigation_assay"
    )
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"]["source_span_count"]
        == 3
    )
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"]["source_bodies_exported"]
        is False
    )
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"][
            "route_utility_ratchet_status"
        ]
        == "curriculum_current"
    )
    route_curriculum = python_lens["route_utility_curriculum"]
    assert route_curriculum["curriculum_id"] == "microcosm_python_route_utility_curriculum"
    assert route_curriculum["task_count"] == 10
    assert route_curriculum["route_utility_metrics"]["failed_task_count"] == 0
    assert route_curriculum["route_utility_metrics"]["not_applicable_count"] == 1
    assert route_curriculum["disposition_counts"] == {
        "local_projection_defect": 0,
        "local_source_or_test_defect": 0,
        "macro_standard_amendment_candidate": 0,
        "nothing_to_refine": 10,
    }
    assert route_curriculum["payload_boundary_ok"] is True
    assert route_curriculum["source_bodies_exported"] is False
    assert route_curriculum["route_utility_metrics"]["stale_task_count"] == 0
    assert route_curriculum["ratchet"]["schema_version"] == (
        "microcosm_python_route_utility_ratchet_v1"
    )
    assert route_curriculum["ratchet"]["seed_task_count"] == 10
    assert route_curriculum["ratchet"]["generated_task_count"] == 0
    assert route_curriculum["ratchet"]["stale_task_ids"] == []
    assert route_curriculum["ratchet"]["last_run_result"] == "curriculum_current"
    task_by_id = {row["task_id"]: row for row in route_curriculum["tasks"]}
    assert (
        task_by_id["route_utility:entry_surface_to_python_assay"]["entry_surface_ref"]
        == "atlas/entry_packet.json::python_navigation_route"
    )
    assert (
        task_by_id["route_utility:test_behavior_source_span"]["expected_source_span"]
        == "tests/test_smoke.py::test_value"
    )
    assert task_by_id["route_utility:entrypoint_source_span"]["correctness"] == "not_applicable"
    assert task_by_id["route_utility:payload_boundary"]["source_bodies_exported"] is False
    test_span = next(
        row
        for row in python_lens["source_span_rows"]
        if row["span_id"] == "tests/test_smoke.py::test_value"
    )
    assert test_span["line_start"] == 4
    assert test_span["source_bodies_exported"] is False
    assert all(row["source_bodies_exported"] is False for row in python_lens["path_rows"])
    assert {row["route_id"]: row["readiness"] for row in python_lens["route_rows"]} == {
        "python_package_metadata_route": "pass",
        "python_source_core_route": "pass",
        "python_test_behavior_route": "pass",
        "python_entrypoint_route": "missing",
    }
    assert (project / ".microcosm/python_lens.json").is_file()
    assert (project / ".microcosm/evidence/python_lens.json").is_file()
    assert patterns["passing_pattern_count"] >= 4
    assert patterns["pattern_surface"]["surface_id"] == "public_microcosm_pattern_surface"
    pattern_ids = {row["pattern_id"] for row in patterns["patterns"]}
    assert all(row["standard_refs"] for row in patterns["patterns"])
    assert {row["route_id"] for row in routes["routes"]} >= {
        "readme_onboarding_route",
        "package_runtime_route",
        "source_core_route",
        "test_behavior_route",
    }
    assert all(set(row["pattern_refs"]).issubset(pattern_ids) for row in routes["routes"])
    assert explanation["status"] == "pass"
    assert explanation["route_id"] == "readme_onboarding_route"
    assert explanation["pattern_refs"] == ["repo_has_readme"]
    assert explanation["pattern_surface"]["state_ref"] == ".microcosm/patterns.json"
    assert explanation["pattern_bindings"][0]["pattern_id"] == "repo_has_readme"
    assert explanation["pattern_bindings"][0]["resolved"] is True
    assert explanation["standard_pressure_surface"]["surface_id"] == "public_microcosm_standard_pressure"
    assert "reversible_work_transaction" in explanation["standard_pressure_refs"]
    assert all(row["resolved"] is True for row in explanation["standard_bindings"])
    assert {
        row["standard_id"] for row in explanation["standard_bindings"]
    } >= {
        "json_contract_markdown_projection",
        "substrate_derived_projection",
        "projection_lineage_not_authority",
        "reversible_work_transaction",
        "evidence_as_black_box_recorder",
        "assimilation_without_promotion",
    }
    assert explanation["kernel_primitives"] == [
        "catalog",
        "pattern",
        "route",
        "work",
        "event",
        "evidence",
        "explanation",
    ]
    assert explanation["authority_boundary"] == "project_local_projection_not_source_authority"
    assert explanation["causal_chain_proof"]["status"] == "partial"
    assert created["work_id"] == "work_0001"
    assert run["transaction_status"] == "pass"
    assert run["state_machine"] == ["created", "selected", "planned", "executed_simulation", "closed"]
    causal_proof = post_run_explanation["causal_chain_proof"]
    assert causal_proof["status"] == "pass"
    assert causal_proof["proof_scope"] == (
        "project_local_state_lineage_not_correctness_authority"
    )
    assert causal_proof["route_id"] == "readme_onboarding_route"
    assert causal_proof["route_ref"] == ".microcosm/routes.json::readme_onboarding_route"
    assert causal_proof["pattern_binding_ids"] == ["repo_has_readme"]
    assert "reversible_work_transaction" in causal_proof["standard_binding_ids"]
    assert causal_proof["work_ids"] == ["work_0001"]
    assert causal_proof["selected_work_id"] == "work_0001"
    assert causal_proof["selected_work_status"] == "closed"
    assert causal_proof["state_history"] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]
    assert causal_proof["event_ref_count"] >= 4
    assert causal_proof["evidence_ref_count"] >= 4
    assert causal_proof["source_files_mutated"] is False
    assert ".microcosm/work_items.json" in causal_proof["reader_drilldowns"]
    assert ".microcosm/evidence/work_create_work_0001.json" in causal_proof["evidence_refs"]
    assert ".microcosm/evidence/work_run_work_0001.json" in causal_proof["evidence_refs"]
    assert causal_proof["authority_boundary"] == (
        "causal_chain_lineage_not_release_or_proof_correctness_authority"
    )
    rerun = project_substrate.run_work(project, str(created["work_id"]))
    assert rerun["transaction_status"] == "pass"
    assert rerun["idempotent_replay"] is True
    work_payload = json.loads((project / ".microcosm/work_items.json").read_text(encoding="utf-8"))
    work_row = work_payload["work_items"][0]
    assert work_row["satisfaction_contract"]["contract_id"] == "satisfaction:readme_onboarding_route"
    assert work_row["integration_contract"]["integration_mode"] == "project_local_record_only"
    assert work_row["closeout"]["satisfaction_contract_met"] is True
    assert work_row["closeout"]["integration_contract_met"] is True
    assert [row["state"] for row in work_row["state_history"]] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]
    assert work_row["event_refs"]
    assert work_row["evidence_refs"]
    assert observed["event_count"] >= 6
    assert observed["architecture_ref"] == ".microcosm/architecture.json"
    assert graph["edge_count"] >= 7
    assert {node["node_id"] for node in graph["nodes"]} >= {
        "pattern_surface",
        "standard:std_microcosm_pattern",
        "standard:std_microcosm_pattern_binding_contract",
        "standard_pressure_surface",
        "standard_pressure:reversible_work_transaction",
    }
    assert any(edge["relation"] == "resolves_pattern_refs_against" for edge in graph["edges"])
    assert any(edge["relation"] == "resolves_standard_pressure_against" for edge in graph["edges"])
    assert evidence["evidence_count"] >= 6
    assert inspected["status"] == "pass"
    assert inspected["payload_boundary_ref"] == "project_python_lens_read_model"
    assert inspected["source_bodies_exported"] is False
    assert compiled["status"] == "pass"
    assert compiled["headline"] == "repo -> .microcosm"
    assert compiled["selected_route_id"] == "readme_onboarding_route"
    assert compiled["python_lens_ref"] == ".microcosm/python_lens.json"
    assert compiled["python_navigation_assay_ref"] == ".microcosm/python_lens.json::navigation_assay"
    assert compiled["python_file_count"] == 2
    assert compiled["python_ready_route_count"] == 3
    assert compiled["python_source_span_count"] == 3
    assert compiled["python_navigation_assay"]["assay_id"] == "std_python_microcosm_navigation_assay"
    assert compiled["python_navigation_assay"]["route_utility_task_count"] == 10
    assert compiled["python_navigation_assay"]["route_utility_stale_task_count"] == 0
    assert (
        compiled["implementation_atlas"]["python_navigation_assay"]["assay_ref"]
        == ".microcosm/python_lens.json::navigation_assay"
    )
    assert compiled["route_utility_curriculum"]["task_count"] == 10
    assert (
        compiled["route_utility_curriculum"]["ratchet"]["last_run_result"]
        == "curriculum_current"
    )
    assert compiled["python_navigation_route"]["surface_id"] == "project_python_lens"
    assert compiled["work_id"] == "work_0001"
    assert compiled["idempotent_replay"] is True
    assert compiled["source_files_mutated"] is False
    assert "microcosm serve <project>" in compiled["open_observatory"]

    state_files = {
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
        ".microcosm/explanations/readme_onboarding_route.json",
    }
    for rel in state_files:
        assert (project / rel).is_file()
    saved_explanation = json.loads(
        (project / ".microcosm/explanations/readme_onboarding_route.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved_explanation["causal_chain_proof"]["selected_work_id"] == "work_0001"

    state_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted((project / ".microcosm").rglob("*.json")))
    assert tmp_path.as_posix() not in state_text
    assert "/Users/" not in state_text


def test_python_lens_can_emit_navigation_assay_without_writing_state(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    python_lens = project_substrate.python_lens(project, write_state=False)

    assert python_lens["status"] == "pass"
    assert python_lens["state_written"] is False
    assert python_lens["evidence_ref"] is None
    assert python_lens["event_id"] is None
    assert python_lens["navigation_assay"]["assay_id"] == "std_python_microcosm_navigation_assay"
    assert python_lens["navigation_assay"]["probe_disposition_counts"] == {
        "file_local_defect": 0,
        "standard_amendment_candidate": 0,
        "nothing_to_refine": 4,
    }
    assert python_lens["route_utility_curriculum"]["task_count"] == 10
    assert python_lens["route_utility_curriculum"]["state_written"] is False
    assert python_lens["route_utility_curriculum"]["source_bodies_exported"] is False
    assert python_lens["route_utility_curriculum"]["ratchet"]["last_run_result"] == (
        "nothing_to_refine"
    )
    assert python_lens["route_utility_curriculum"]["ratchet"]["state_freshness"] == (
        "no_written_state"
    )
    assert python_lens["source_span_count"] == 3
    assert not (project / ".microcosm").exists()


def test_python_lens_route_utility_ratchet_marks_changed_surface_without_writing(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    project_substrate.python_lens(project)
    state_path = project / ".microcosm/python_lens.json"
    test_path = project / "tests/test_smoke.py"
    future = state_path.stat().st_mtime + 10
    test_path.write_text(
        "from scratch_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n\n",
        encoding="utf-8",
    )
    os.utime(test_path, (future, future))

    python_lens = project_substrate.python_lens(project, write_state=False)
    ratchet = python_lens["route_utility_curriculum"]["ratchet"]

    assert python_lens["state_written"] is False
    assert ratchet["last_run_result"] == "curriculum_stale_for_changed_surface"
    assert ratchet["changed_surface_refs"] == ["tests/test_smoke.py"]
    assert "route_utility:test_behavior_source_span" in ratchet["affected_task_ids"]
    assert "route_utility:payload_boundary" in ratchet["affected_task_ids"]
    assert sorted(ratchet["stale_task_ids"]) == sorted(ratchet["affected_task_ids"])
    assert ratchet["generated_task_count"] == len(ratchet["affected_task_ids"])
    assert python_lens["navigation_assay"]["route_utility_ratchet_status"] == (
        "curriculum_stale_for_changed_surface"
    )
    assert python_lens["navigation_assay"]["route_utility_stale_task_count"] == len(
        ratchet["stale_task_ids"]
    )
    assert (project / ".microcosm/python_lens.json").is_file()


def test_python_lens_route_utility_ratchet_ignores_unwatched_surface(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    project_substrate.python_lens(project)
    state_path = project / ".microcosm/python_lens.json"
    note_path = project / "notes/operator_note.md"
    note_path.parent.mkdir()
    future = state_path.stat().st_mtime + 10
    note_path.write_text(
        "This note is outside the Python route utility surfaces.\n",
        encoding="utf-8",
    )
    os.utime(note_path, (future, future))

    python_lens = project_substrate.python_lens(project, write_state=False)
    ratchet = python_lens["route_utility_curriculum"]["ratchet"]

    assert python_lens["state_written"] is False
    assert ratchet["state_freshness"] == "compared_to_written_state"
    assert ratchet["last_run_result"] == "nothing_to_refine"
    assert ratchet["changed_surface_refs"] == []
    assert ratchet["affected_task_ids"] == []
    assert ratchet["stale_task_ids"] == []
    assert ratchet["generated_task_count"] == 0
    assert python_lens["route_utility_curriculum"]["route_utility_metrics"][
        "stale_task_count"
    ] == 0
    assert python_lens["route_utility_curriculum"]["source_bodies_exported"] is False
    assert (project / ".microcosm/python_lens.json").is_file()


def test_cli_project_first_run_commands(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    for argv in [
        ["init", project.as_posix()],
        ["index", project.as_posix()],
        ["catalog", project.as_posix()],
        ["architecture", project.as_posix()],
        ["compile", project.as_posix()],
        ["python-lens", project.as_posix()],
        ["patterns", project.as_posix()],
        ["route", project.as_posix()],
        ["explain", project.as_posix(), "readme_onboarding_route"],
        ["graph", project.as_posix()],
        ["work", "create", project.as_posix()],
        ["work", "run", project.as_posix()],
        ["observe", project.as_posix()],
        ["evidence", "list", project.as_posix()],
    ]:
        assert cli.main(argv) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "pass"
        if argv[0] == "explain":
            assert payload["causal_chain_proof"]["status"] == "pass"
            assert payload["causal_chain_proof"]["selected_work_id"] == "work_0001"
            assert payload["causal_chain_proof"]["event_ref_count"] >= 4
