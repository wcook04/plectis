from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli


def _payload(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_cli_evidence_list_fails_closed_for_missing_project(capsys, tmp_path: Path) -> None:
    missing = tmp_path / "missing-project"

    assert cli.main(["evidence", "list", missing.as_posix()]) == 1
    payload = _payload(capsys)

    assert payload["status"] == "missing_project"
    assert payload["project_ref"] == missing.as_posix()
    assert payload["state_ref"] == ".microcosm"
    assert payload["evidence_count"] == 0
    assert payload["release_authorized"] is False
    assert "microcosm tour --card" in payload["reader_action"]


def test_cli_evidence_list_fails_closed_for_missing_state(capsys, tmp_path: Path) -> None:
    project = tmp_path / "empty-project"
    project.mkdir()

    assert cli.main(["evidence", "list", project.as_posix()]) == 1
    payload = _payload(capsys)

    assert payload["status"] == "missing_state"
    assert payload["project_ref"] == project.as_posix()
    assert payload["state_dir_exists"] is False
    assert payload["evidence_count"] == 0
    assert "before evidence drilldown" in payload["reader_action"]


def test_cli_evidence_list_preserves_initialized_project_success(
    capsys, tmp_path: Path
) -> None:
    project = tmp_path / "ready-project"
    evidence_dir = project / ".microcosm" / "evidence"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "routes.json").write_text(
        json.dumps(
            {
                "schema_version": "microcosm_project_routes_v1",
                "status": "pass",
                "project_id": "ready-project",
                "created_at": "2026-05-28T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["evidence", "list", project.as_posix()]) == 0
    payload = _payload(capsys)

    assert payload["status"] == "pass"
    assert payload["evidence_count"] == 1
    assert payload["evidence"][0]["evidence_ref"] == ".microcosm/evidence/routes.json"
