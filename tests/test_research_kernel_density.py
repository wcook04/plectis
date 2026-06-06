from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import project_substrate
from microcosm_core.validators import research_kernel_density
from microcosm_core.validators.research_kernel_density import validate_density


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/app").mkdir(parents=True)
    (project / "README.md").write_text("# Scratch\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project, "readme_onboarding_route")
    project_substrate.run_work(project, str(created["work_id"]))
    project_substrate.compile_project(project)
    return project


def test_research_kernel_density_validator_passes_with_scratch_project(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "research_kernel_density.json"

    receipt = validate_density(MICROCOSM_ROOT, out, command="pytest", project=project)

    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["density_assertions"]["readme_declares_research_prototype"] is True
    assert receipt["density_assertions"]["kernel_primitives_have_runtime_hooks"] is True
    assert receipt["density_assertions"]["kernel_declares_pattern_surface"] is True
    assert receipt["density_assertions"]["route_pattern_refs_resolve"] is True
    assert receipt["density_assertions"]["explanations_include_pattern_bindings"] is True
    assert receipt["density_assertions"]["explanations_include_standard_bindings"] is True
    assert receipt["density_assertions"]["route_standard_refs_resolve"] is True
    assert receipt["density_assertions"]["route_explanation_available"] is True
    assert receipt["density_assertions"]["work_transaction_contract_present"] is True
    assert receipt["density_assertions"]["truth_readiness_surface_available"] is True
    assert receipt["density_assertions"]["observatory_surface_available"] is True
    assert receipt["density_assertions"]["desktop_sandbox_relative_refs"] is True
    assert receipt["density_assertions"]["release_authorized"] is False


def test_explanation_json_presence_streams_nested_without_glob(
    tmp_path: Path, monkeypatch
) -> None:
    explanations = tmp_path / "explanations"
    nested = explanations / "routes"
    nested.mkdir(parents=True)
    first = nested / "route.json"
    first.write_text("{}", encoding="utf-8")

    original_glob = Path.glob

    def guarded_glob(path: Path, pattern: str):
        if path == explanations:
            raise AssertionError("explanation JSON presence should stream nested state files")
        yield from original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", guarded_glob)

    assert research_kernel_density._has_json_file(explanations) is True


def test_project_findings_validate_nested_explanation_bindings(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    explanations = project / ".microcosm/explanations"
    flat = explanations / "readme_onboarding_route.json"
    nested = explanations / "routes/readme_onboarding_route.json"
    nested.parent.mkdir(parents=True)
    flat.replace(nested)
    payload = json.loads(nested.read_text(encoding="utf-8"))
    payload["pattern_bindings"] = [
        {**row, "resolved": False} for row in payload["pattern_bindings"]
    ]
    nested.write_text(json.dumps(payload), encoding="utf-8")

    findings, blocking_codes = research_kernel_density._project_findings(project)

    assert "PROJECT_ROUTE_EXPLANATION_MISSING" not in blocking_codes
    assert "PROJECT_EXPLANATION_PATTERN_BINDING_UNRESOLVED" in blocking_codes
    assert {
        "explanation_ref": ".microcosm/explanations/routes/readme_onboarding_route.json",
        "unresolved_pattern_refs": ["repo_has_readme"],
    } in next(
        finding["explanations"]
        for finding in findings
        if finding["finding_id"] == "project_explanation_pattern_binding_unresolved"
    )
    assert all(
        ".microcosm/explanations/readme_onboarding_route.json" not in str(finding)
        for finding in findings
    )


def test_state_payload_file_scan_streams_without_path_rglob(
    tmp_path: Path, monkeypatch
) -> None:
    state = tmp_path / ".microcosm"
    nested = state / "nested"
    nested.mkdir(parents=True)
    (state / "architecture.json").write_text("{}", encoding="utf-8")
    (nested / "routes.json").write_text("{}", encoding="utf-8")
    (state / "events.jsonl").write_text("{}\n", encoding="utf-8")
    (state / "notes.txt").write_text("not payload\n", encoding="utf-8")

    def guarded_rglob(path: Path, pattern: str):
        raise AssertionError("state payload scan should not use Path.rglob")

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    refs = {
        path.relative_to(state).as_posix()
        for path in research_kernel_density._iter_state_payload_files(state)
    }

    assert refs == {"architecture.json", "nested/routes.json", "events.jsonl"}


def test_state_host_path_scan_streams_payload_files(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    streamed = project / ".microcosm/streamed.json"
    streamed.write_text(
        "/Users/example/private-root\n"
        + "\n".join(f'{{"public_row": {index}}}' for index in range(500)),
        encoding="utf-8",
    )

    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs):
        if path == streamed:
            raise AssertionError("state payload scan should stream instead of read_text")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    receipt = validate_density(
        MICROCOSM_ROOT,
        tmp_path / "research_kernel_density.json",
        command="pytest",
        project=project,
    )

    assert receipt["status"] == "blocked"
    assert "PROJECT_STATE_HOST_PATH_LEAK" in receipt["blocking_codes"]
    assert {
        "finding_id": "project_state_host_path_leak",
        "state_refs": ["streamed.json"],
    } in receipt["findings"]
