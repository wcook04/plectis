from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import project_substrate
from microcosm_core.public_payload_boundary import SOURCE_OPEN_BODY_POLICY


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/scratch_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch project\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """
[project]
name = "scratch-app"
version = "0.1.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
""".lstrip(),
        encoding="utf-8",
    )
    (project / "src/scratch_app/__init__.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (project / "tests/test_smoke.py").write_text(
        "from scratch_app import VALUE\n\n\n"
        "def test_value():\n"
        "    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_compile_project_omits_legacy_body_redacted_payload_vocabulary(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)

    compiled = project_substrate.compile_project(project)
    python_lens = json.loads(
        (project / ".microcosm/python_lens.json").read_text(encoding="utf-8")
    )
    serialized = json.dumps(
        {"compiled": compiled, "python_lens": python_lens},
        sort_keys=True,
    )

    assert compiled["status"] == "pass"
    assert compiled["source_files_mutated"] is False
    assert python_lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert python_lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"][
            "source_bodies_exported"
        ]
        is False
    )
    assert python_lens["route_utility_curriculum"]["source_bodies_exported"] is False
    assert "body_redacted" not in serialized
    assert "payload_boundary_normalization" not in serialized
