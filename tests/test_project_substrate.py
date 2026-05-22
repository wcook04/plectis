from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import project_substrate
from microcosm_core import cli


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
    assert python_lens["body_redacted"] is True
    assert python_lens["authority_ceiling"]["source_bodies_exported"] is False
    assert all(row["body_redacted"] is True for row in python_lens["path_rows"])
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
    assert created["work_id"] == "work_0001"
    assert run["transaction_status"] == "pass"
    assert run["state_machine"] == ["created", "selected", "planned", "executed_simulation", "closed"]
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
    assert inspected["body_redacted"] is True
    assert compiled["status"] == "pass"
    assert compiled["headline"] == "repo -> .microcosm"
    assert compiled["selected_route_id"] == "readme_onboarding_route"
    assert compiled["python_lens_ref"] == ".microcosm/python_lens.json"
    assert compiled["python_file_count"] == 2
    assert compiled["python_ready_route_count"] == 3
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

    state_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted((project / ".microcosm").rglob("*.json")))
    assert tmp_path.as_posix() not in state_text
    assert "/Users/" not in state_text


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
