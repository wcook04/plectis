from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli
from microcosm_core import project_substrate
from microcosm_core.validators.observatory_legibility import validate_legibility


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch\n\nLocal proof project.\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_smoke.py").write_text(
        "from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project, "readme_onboarding_route")
    project_substrate.run_work(project, str(created["work_id"]))
    project_substrate.observe_project(project)
    project_substrate.state_graph(project)
    project_substrate.list_evidence(project)
    return project


def test_observatory_legibility_validator_exposes_causal_chain(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "observatory_legibility.json"

    receipt = validate_legibility(MICROCOSM_ROOT, project, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["html_assertions"]["root_is_not_raw_json_only"] is True
    assert receipt["html_assertions"]["causal_chain_section_present"] is True
    assert receipt["html_assertions"]["pattern_binding_visible"] is True
    assert receipt["html_assertions"]["standard_binding_visible"] is True
    assert receipt["html_assertions"]["work_state_history_visible"] is True
    assert receipt["html_assertions"]["evidence_marked_drilldown"] is True
    assert receipt["html_assertions"]["release_ceiling_visible"] is True
    assert receipt["html_assertions"]["private_paths_absent"] is True
    assert receipt["causal_chain_proof"]["route_id"] == "readme_onboarding_route"
    assert "repo_has_readme" in receipt["causal_chain_proof"]["pattern_binding_ids"]
    assert "reversible_work_transaction" in receipt["causal_chain_proof"]["standard_binding_ids"]
    assert receipt["causal_chain_proof"]["work_id"] == "work_0001"
    assert receipt["causal_chain_proof"]["state_history"] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]


def test_cli_observatory_legibility_command(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "observatory_legibility.json"

    assert cli.main(
        [
            "observatory-legibility",
            "--root",
            MICROCOSM_ROOT.as_posix(),
            "--project",
            project.as_posix(),
            "--out",
            out.as_posix(),
        ]
    ) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["html_sections_present"]["causal_chain"] is True
    assert "pass" not in capsys.readouterr().err
