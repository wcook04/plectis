from __future__ import annotations

from pathlib import Path

import pytest

from microcosm_core import runtime_shell


def test_fast_cached_project_compile_card_streams_evidence_count_without_glob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    evidence_dir = state_dir / "evidence"
    (evidence_dir / "nested").mkdir(parents=True)
    (state_dir / "catalog.json").write_text(
        '{"file_count": 1, "role_counts": {"readme": 1}}\n',
        encoding="utf-8",
    )
    (state_dir / "routes.json").write_text(
        '{"route_count": 1, "routes": [{"route_id": "readme_onboarding_route"}]}\n',
        encoding="utf-8",
    )
    (state_dir / "graph.json").write_text(
        '{"node_count": 1, "edge_count": 0}\n',
        encoding="utf-8",
    )
    (evidence_dir / "compile.json").write_text('{"status": "pass"}\n', encoding="utf-8")
    (evidence_dir / "nested" / "proof.json").write_text(
        '{"status": "pass"}\n',
        encoding="utf-8",
    )
    (evidence_dir / "nested" / "notes.txt").write_text("skip\n", encoding="utf-8")

    original_glob = Path.glob

    def fail_if_globbed(self: Path, pattern: str) -> object:
        if self == evidence_dir and pattern == "*.json":
            raise AssertionError("cached compile card should stream evidence counting")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fail_if_globbed)

    card = runtime_shell._fast_cached_project_compile_card(project)

    assert card["status"] == "pass"
    assert card["cache_freshness"]["status"] == "missing_cache_marker"
    assert card["safe_to_show"]["freshness_certified"] is False
    assert card["evidence_count"] == 2


def test_fast_cached_project_compile_card_streams_event_count_without_rows_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    state_dir.mkdir(parents=True)
    (state_dir / "catalog.json").write_text(
        '{"file_count": 1, "role_counts": {"readme": 1}}\n',
        encoding="utf-8",
    )
    (state_dir / "routes.json").write_text(
        '{"route_count": 1, "routes": [{"route_id": "readme_onboarding_route"}]}\n',
        encoding="utf-8",
    )
    (state_dir / "graph.json").write_text(
        '{"node_count": 1, "edge_count": 0}\n',
        encoding="utf-8",
    )
    (state_dir / "events.jsonl").write_text(
        "".join(f'{{"event_id":"evt_{index:04d}"}}\n' for index in range(1, 26))
        + '["skip non-object rows"]\n'
        + "\n",
        encoding="utf-8",
    )

    def fail_read_jsonl(_path: Path) -> list[dict[str, object]]:
        raise AssertionError("cached compile card should stream-count event rows")

    monkeypatch.setattr(runtime_shell, "_read_jsonl", fail_read_jsonl)

    card = runtime_shell._fast_cached_project_compile_card(project)

    assert card["status"] == "pass"
    assert card["cache_freshness"]["status"] == "missing_cache_marker"
    assert card["safe_to_show"]["freshness_certified"] is False
    assert card["event_count"] == 25
