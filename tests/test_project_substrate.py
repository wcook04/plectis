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
    patterns = project_substrate.discover_patterns(project)
    routes = project_substrate.propose_routes(project)
    created = project_substrate.create_work(project)
    run = project_substrate.run_work(project, str(created["work_id"]))
    observed = project_substrate.observe_project(project)
    evidence = project_substrate.list_evidence(project)
    inspected = project_substrate.inspect_evidence(project, str(run["evidence_ref"]))

    assert init_result["status"] == "pass"
    assert index_result["file_count"] == 4
    assert catalog["role_counts"]["readme"] == 1
    assert catalog["role_counts"]["package_manifest"] == 1
    assert catalog["role_counts"]["source"] == 1
    assert catalog["role_counts"]["test"] == 1
    assert patterns["passing_pattern_count"] >= 4
    assert {row["route_id"] for row in routes["routes"]} >= {
        "readme_onboarding_route",
        "package_runtime_route",
        "source_core_route",
        "test_behavior_route",
    }
    assert created["work_id"] == "work_0001"
    assert run["transaction_status"] == "pass"
    assert observed["event_count"] >= 6
    assert evidence["evidence_count"] >= 6
    assert inspected["status"] == "pass"
    assert inspected["body_redacted"] is True

    state_files = {
        ".microcosm/project_manifest.json",
        ".microcosm/catalog.json",
        ".microcosm/patterns.json",
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
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
        ["patterns", project.as_posix()],
        ["route", project.as_posix()],
        ["work", "create", project.as_posix()],
        ["work", "run", project.as_posix()],
        ["observe", project.as_posix()],
        ["evidence", "list", project.as_posix()],
    ]:
        assert cli.main(argv) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "pass"
