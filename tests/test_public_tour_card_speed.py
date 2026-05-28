from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import project_substrate


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_first_screen_compile_defers_full_python_ast_scan(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "public_project"
    _write(project / "README.md", "# Public project\n")
    _write(project / "pyproject.toml", "[project]\nname = 'public-project'\n")
    _write(project / "src/public_project/__init__.py", '"""Public package."""\n')
    _write(
        project / "src/public_project/app.py",
        "import json\n\n\ndef main():\n    return json.dumps({'ok': True})\n",
    )
    _write(project / "tests/test_app.py", "def test_app():\n    assert True\n")

    def unexpected_full_ast_scan(rel: str, text: str) -> dict:
        raise AssertionError(f"full AST scan should be deferred for {rel}")

    monkeypatch.setattr(
        project_substrate,
        "_python_span_projection",
        unexpected_full_ast_scan,
    )

    result = project_substrate.compile_project(
        project,
        python_lens_scan_mode=project_substrate.PYTHON_LENS_SCAN_FIRST_SCREEN,
    )
    lens = json.loads(
        (project / ".microcosm/python_lens.json").read_text(encoding="utf-8")
    )

    assert result["status"] == "pass"
    assert result["python_lens_scan_mode"] == "first_screen_summary"
    assert result["python_lens_deferred_full_scan"] is True
    assert result["python_lens_full_command"] == "microcosm python-lens <project>"
    assert lens["scan_mode"] == "first_screen_summary"
    assert lens["deferred_full_scan"] is True
    assert lens["python_file_count"] == 3
    assert lens["source_span_count"] == 0
    assert all(
        row["parse_status"] == "deferred_first_screen_summary"
        for row in lens["path_rows"]
    )
    assert (project / ".microcosm/routes.json").is_file()
    assert (project / ".microcosm/work_items.json").is_file()
