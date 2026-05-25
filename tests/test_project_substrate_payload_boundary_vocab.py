from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli, project_substrate
from microcosm_core.public_payload_boundary import SOURCE_OPEN_BODY_POLICY


LEGACY_PAYLOAD_TERMS = [
    "body_" + "red" + "acted",
    "private_" + "state" + "_scan",
    "public_" + "replacement_ref",
    "public_" + "replacement_landed",
]


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


def _encoded(payload: object) -> str:
    return json.dumps(payload, sort_keys=True)


def _assert_current_payload_boundary_vocab(payload: object) -> None:
    encoded = _encoded(payload)
    assert "payload_boundary" in encoded
    assert SOURCE_OPEN_BODY_POLICY in encoded
    for term in LEGACY_PAYLOAD_TERMS:
        assert term not in encoded


def test_project_python_lens_raw_payload_uses_payload_boundary_vocab(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    compiled = project_substrate.compile_project(project)
    python_lens = project_substrate.python_lens(project)
    stored_lens = json.loads((project / ".microcosm/python_lens.json").read_text(encoding="utf-8"))

    for payload in (compiled, python_lens, stored_lens):
        _assert_current_payload_boundary_vocab(payload)

    assert python_lens["payload_boundary"]["boundary_id"] == "project_python_lens_read_model"
    assert python_lens["safe_to_show"]["python_lens_rows_are_public_payload_boundary_rows"] is True
    assert python_lens["authority_ceiling"]["source_bodies_exported"] is False
    assert python_lens["route_utility_curriculum"]["payload_boundary_ok"] is True
    assert all(row["source_bodies_exported"] is False for row in python_lens["path_rows"])
    assert all(row["source_bodies_exported"] is False for row in python_lens["source_span_rows"])


def test_cli_compile_and_python_lens_keep_payload_boundary_vocab(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    for argv in (
        ["compile", project.as_posix()],
        ["python-lens", project.as_posix()],
    ):
        assert cli.main(argv) == 0
        payload = json.loads(capsys.readouterr().out)
        _assert_current_payload_boundary_vocab(payload)
