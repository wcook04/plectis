from __future__ import annotations

from pathlib import Path

from microcosm_core import runtime_shell


def test_macro_body_target_path_resolves_package_source_ref_outside_project_root(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "smoke_project"
    project_root.mkdir()
    target_ref = "src/microcosm_core/macro_tools/work_landing.py"

    target_path = runtime_shell._macro_body_target_path(project_root, target_ref)

    assert target_path.is_file()
    assert target_path == (
        Path(runtime_shell.__file__).resolve().parent / "macro_tools/work_landing.py"
    )
    assert not str(target_path).startswith(str(project_root))
