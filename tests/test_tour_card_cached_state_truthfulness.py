from __future__ import annotations

import os
from pathlib import Path

import pytest

from microcosm_core import project_substrate, runtime_shell
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/scratch_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text(
        "# Scratch Project\n\nLocal proof project.\n",
        encoding="utf-8",
    )
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src/scratch_app/__init__.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (project / "tests/test_smoke.py").write_text(
        "from scratch_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_tour_card_distinguishes_cached_read_from_write_contract(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(MICROCOSM_ROOT)

    first = shell.tour_card(project)
    second = shell.tour_card(project)

    first_write = first["state_write_result"]
    second_write = second["state_write_result"]

    assert first_write["current_invocation_wrote_microcosm_state"] is True
    assert first_write["cached_state_reused"] is False
    assert second_write["writes_microcosm_state"] is False
    assert second_write["writes_microcosm_state_semantics"] == (
        "current_invocation_only"
    )
    assert second_write["current_invocation_wrote_microcosm_state"] is False
    assert second_write["cached_state_reused"] is True
    assert second_write["command_writes_microcosm_state_when_needed"] is True
    assert "current-invocation only" in second_write["reader_action"]


def test_tour_card_blocks_incomplete_cached_state_refs(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(MICROCOSM_ROOT)

    first = shell.tour_card(project)
    assert first["status"] == "pass"

    missing_ref = project / ".microcosm" / "work_items.json"
    missing_ref.unlink()

    second = shell.tour_card(project)

    assert second["status"] == "blocked"
    assert second["front_door_status"]["status"] == "blocked"
    assert second["surface_statuses"]["state_inspection"] == "missing_state_refs"
    assert second["state_inspection"]["status"] == "missing_state_refs"
    assert ".microcosm/work_items.json" in second["state_inspection"][
        "missing_first_screen_refs"
    ]
    assert second["state_write_result"]["status"] == "blocked"
    assert second["state_write_result"]["cached_state_reused"] is True
    assert "state_inspection" in second["blocking_surface_ids"]
    assert "state_write" in second["blocking_surface_ids"]


def test_tour_card_rebuilds_when_fast_cached_state_is_stale(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(MICROCOSM_ROOT)

    first = shell.tour_card(project)
    assert first["status"] == "pass"
    assert (
        first["state_write_result"]["current_invocation_wrote_microcosm_state"] is True
    )

    state_index = project / ".microcosm/state_index.json"
    readme = project / "README.md"
    readme.write_text(
        "# Scratch Project\n\nLocal proof project changed after cache.\n",
        encoding="utf-8",
    )
    stale_mtime_ns = state_index.stat().st_mtime_ns + 1_000_000_000
    os.utime(readme, ns=(stale_mtime_ns, stale_mtime_ns))

    stale_fast_card = runtime_shell._fast_cached_project_compile_card(project)
    assert stale_fast_card["status"] == "stale_cached_state"
    assert stale_fast_card["cache_status"] == "stale_cached_state"
    assert stale_fast_card["cache_freshness"]["status"] == "stale"

    second = shell.tour_card(project)

    assert second["status"] == "pass"
    assert second["state_write_result"]["compile_cache_status"] == "stale_cached_state"
    assert (
        second["state_write_result"]["current_invocation_wrote_microcosm_state"] is True
    )
    assert second["state_write_result"]["cached_state_reused"] is False


def test_tour_card_rebuilds_uncompiled_partial_state(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(MICROCOSM_ROOT)

    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project, "readme_onboarding_route")
    project_substrate.run_work(project, str(created["work_id"]))
    assert not (project / ".microcosm" / "python_lens.json").exists()

    card = shell.tour_card(project)

    assert card["status"] == "pass"
    assert card["state_write_result"]["current_invocation_wrote_microcosm_state"] is True
    assert card["state_write_result"]["cached_state_reused"] is False
    assert (project / ".microcosm" / "python_lens.json").exists()


def test_state_inspection_counts_files_without_rglob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    (state_dir / "nested").mkdir(parents=True)
    (state_dir / "routes.json").write_text("{}", encoding="utf-8")
    (state_dir / "nested/graph.json").write_text("{}", encoding="utf-8")

    def fail_if_rglobbed(self: Path, *_args: object, **_kwargs: object) -> object:
        if self == state_dir:
            raise AssertionError("state inspection should stream file counting")
        return original_rglob(self, *_args, **_kwargs)

    original_rglob = Path.rglob
    monkeypatch.setattr(Path, "rglob", fail_if_rglobbed)

    card = runtime_shell._project_state_inspection_card(
        project,
        first_screen_refs=[
            ".microcosm/routes.json",
            ".microcosm/nested/graph.json",
        ],
    )

    assert card["status"] == "pass"
    assert card["state_file_count"] == 2
    assert card["missing_first_screen_refs"] == []
