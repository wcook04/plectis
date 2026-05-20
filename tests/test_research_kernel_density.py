from __future__ import annotations

from pathlib import Path

from microcosm_core import project_substrate
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
    assert receipt["density_assertions"]["route_explanation_available"] is True
    assert receipt["density_assertions"]["release_authorized"] is False
