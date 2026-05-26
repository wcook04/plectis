from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core import project_substrate


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _make_cached_compile_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch"
    (project / "src/app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "scratch"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_app.py").write_text(
        "from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    state_dir = project / ".microcosm"
    (state_dir / "evidence").mkdir(parents=True)
    (state_dir / "explanations").mkdir()
    _write_json(state_dir / "project_manifest.json", {"status": "pass"})
    _write_json(state_dir / "architecture.json", {"status": "pass"})
    _write_json(state_dir / "state_index.json", {"status": "pass"})
    _write_json(
        state_dir / "catalog.json",
        {
            "file_count": 4,
            "role_counts": {"package_manifest": 1, "readme": 1, "source": 1, "test": 1},
            "files": [
                {"path": "README.md"},
                {"path": "pyproject.toml"},
                {"path": "src/app/__init__.py"},
                {"path": "tests/test_app.py"},
            ],
        },
    )
    _write_json(
        state_dir / "python_lens.json",
        {"python_file_count": 2, "ready_route_count": 1},
    )
    _write_json(state_dir / "patterns.json", {"passing_pattern_count": 1})
    _write_json(
        state_dir / "routes.json",
        {
            "route_count": 1,
            "routes": [{"route_id": "readme_onboarding_route", "status": "pass"}],
        },
    )
    _write_json(
        state_dir / "work_items.json",
        {
            "work_item_count": 1,
            "work_items": [
                {
                    "route_id": "readme_onboarding_route",
                    "status": "pass",
                    "work_id": "work_readme_onboarding_route",
                }
            ],
        },
    )
    _write_json(
        state_dir / "explanations/readme_onboarding_route.json",
        {"status": "pass"},
    )
    _write_json(state_dir / "evidence/compile.json", {"status": "pass"})
    _write_json(state_dir / "graph.json", {"edge_count": 0, "node_count": 1})
    (state_dir / "events.jsonl").write_text(
        json.dumps({"event_id": "evt_0001", "span": "compile_project", "status": "pass"})
        + "\n",
        encoding="utf-8",
    )
    return project


def test_cli_compile_card_reads_cached_project_state_without_rebuild(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_cached_compile_project(tmp_path)

    def fail_if_rebuilt(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("compile --card must not rebuild project state")

    monkeypatch.setattr(cli.project_substrate, "compile_project", fail_if_rebuilt)

    status = cli.main(["compile", "--card", str(project)])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert status == 0
    assert len(json.dumps(payload, sort_keys=True)) < 8000
    assert payload["schema_version"] == "microcosm_project_compile_cached_card_v1"
    assert payload["status"] == "pass"
    assert payload["card_id"] == "compile_cached_state"
    assert payload["command"] == "microcosm compile --card <project>"
    assert payload["full_command"] == "microcosm compile <project>"
    assert payload["cache_status"] == "cached_state_read"
    assert payload["cache_source_ref"] == ".microcosm/state_index.json"
    assert payload["cache_freshness"]["status"] == "current"
    assert payload["cache_freshness"]["source_status"] == "current"
    assert payload["cache_freshness"]["freshness_source"] == "cached_catalog"
    assert payload["cache_freshness"]["tracked_source_count"] >= 4
    assert payload["cache_freshness"]["source_refs_exported"] is False
    assert payload["selected_route_id"] == "readme_onboarding_route"
    assert payload["route_explanation_status"] == "pass"
    assert payload["state_ref_status_summary"]["missing_state_ref_count"] == 0
    assert payload["file_count"] >= 4
    assert payload["route_count"] >= 1
    assert payload["work_item_count"] >= 1
    assert payload["event_count"] >= 1
    assert payload["evidence_count"] >= 1
    assert payload["graph_summary"]["node_count"] >= 1
    assert payload["source_files_mutated"] is False
    assert payload["safe_to_show"]["source_files_mutated"] is False
    assert payload["safe_to_show"]["provider_calls_authorized"] is False
    assert "reader_causal_chain" not in payload


def test_cli_compile_card_marks_source_changes_stale_without_rebuild(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_cached_compile_project(tmp_path)
    state_index = project / ".microcosm/state_index.json"
    readme = project / "README.md"
    readme.write_text("# Scratch\n\nChanged after compile.\n", encoding="utf-8")
    source_mtime_ns = state_index.stat().st_mtime_ns + 1_000_000_000
    os.utime(readme, ns=(source_mtime_ns, source_mtime_ns))

    def fail_if_rebuilt(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("compile --card must not rebuild stale project state")

    monkeypatch.setattr(cli.project_substrate, "compile_project", fail_if_rebuilt)

    status = cli.main(["compile", "--card", str(project)])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert status == 1
    assert len(json.dumps(payload, sort_keys=True)) < 8000
    assert payload["schema_version"] == "microcosm_project_compile_cached_card_v1"
    assert payload["status"] == "stale_cached_state"
    assert payload["cache_status"] == "stale_cached_state"
    assert payload["cache_freshness"]["status"] == "stale"
    assert payload["cache_freshness"]["source_status"] == "stale"
    assert payload["cache_freshness"]["freshness_source"] == "cached_catalog"
    assert payload["cache_freshness"]["tracked_source_count"] >= 4
    assert payload["cache_freshness"]["stale_source_count"] >= 1
    assert payload["cache_freshness"]["source_refs_exported"] is False
    assert "source_refs" not in payload
    assert "README.md" not in output
    assert "reader_causal_chain" not in payload


def test_compile_card_uses_cached_catalog_for_freshness_without_recrawling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_cached_compile_project(tmp_path)

    def fail_if_walked(*_args: object, **_kwargs: object) -> list[dict]:
        raise AssertionError("compile --card freshness must use cached catalog rows")

    monkeypatch.setattr(project_substrate, "_walk_project", fail_if_walked)

    payload = project_substrate.compile_project_card(project)

    assert payload["status"] == "pass"
    assert payload["cache_freshness"]["freshness_source"] == "cached_catalog"
    assert payload["cache_freshness"]["catalog_file_count"] == 4
    assert payload["cache_freshness"]["tracked_source_count"] == 4


def test_compile_card_marks_directory_changes_stale_without_recrawling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_cached_compile_project(tmp_path)
    state_index = project / ".microcosm/state_index.json"
    new_source = project / "src/app/new_module.py"
    new_source.write_text("NEW_VALUE = 2\n", encoding="utf-8")
    source_mtime_ns = state_index.stat().st_mtime_ns + 1_000_000_000
    os.utime(new_source, ns=(source_mtime_ns, source_mtime_ns))
    os.utime(new_source.parent, ns=(source_mtime_ns, source_mtime_ns))

    def fail_if_walked(*_args: object, **_kwargs: object) -> list[dict]:
        raise AssertionError("compile --card freshness must not recrawl for new files")

    monkeypatch.setattr(project_substrate, "_walk_project", fail_if_walked)

    payload = project_substrate.compile_project_card(project)

    assert payload["status"] == "stale_cached_state"
    assert payload["cache_freshness"]["freshness_source"] == "cached_catalog"
    assert payload["cache_freshness"]["tracked_source_count"] == 4
    assert payload["cache_freshness"]["stale_directory_count"] >= 1
    assert payload["cache_freshness"]["source_refs_exported"] is False


def test_compile_project_batches_architecture_refresh_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_cached_compile_project(tmp_path)
    original_refresh = project_substrate.architecture_kernel.write_project_architecture
    refresh_calls: list[Path] = []

    def counted_refresh(project_path: str | Path) -> dict:
        refresh_calls.append(Path(project_path))
        return original_refresh(project_path)

    monkeypatch.setattr(
        project_substrate.architecture_kernel,
        "write_project_architecture",
        counted_refresh,
    )

    payload = project_substrate.compile_project(project)

    assert payload["status"] == "pass"
    assert len(refresh_calls) == 1
    assert payload["graph_summary"]["node_count"] >= 1
    assert (project / ".microcosm/state_index.json").is_file()
