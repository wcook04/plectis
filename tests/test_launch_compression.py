from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli
from microcosm_core.validators.launch_compression import validate_launch_compression


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
    return project


def test_launch_compression_validator_proves_one_command_aha(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "launch_compression.json"

    receipt = validate_launch_compression(MICROCOSM_ROOT, project, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert all(receipt["assertions"].values())
    assert receipt["one_line_identity"] == "repo -> .microcosm: turn any folder into an inspectable work substrate."
    assert receipt["quickstart_command"] == "microcosm compile ."
    assert receipt["compiled_summary"]["selected_route_id"] == "readme_onboarding_route"
    assert receipt["compiled_summary"]["work_id"] == "work_0001"
    assert receipt["compiled_summary"]["event_count"] > 0
    assert receipt["compiled_summary"]["evidence_count"] > 0


def test_cli_launch_compression_command(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "launch_compression.json"

    assert cli.main(
        [
            "launch-compression",
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
    assert payload["assertions"]["one_command_quickstart_present"] is True
    assert "pass" not in capsys.readouterr().err
