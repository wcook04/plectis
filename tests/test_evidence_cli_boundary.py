from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    assert payload["project_ref"] == project.as_posix()
    assert payload["evidence_count"] == 1
    assert payload["evidence"][0]["evidence_ref"] == ".microcosm/evidence/routes.json"


def test_cli_observe_preserves_initialized_project_ref(
    capsys, tmp_path: Path
) -> None:
    project = tmp_path / "ready-project"
    project.mkdir()
    (project / "README.md").write_text(
        "# Ready Project\n\nProject-ref smoke.\n",
        encoding="utf-8",
    )

    assert cli.main(["tour", "--card", project.as_posix()]) == 0
    _payload(capsys)

    assert cli.main(["observe", project.as_posix()]) == 0
    payload = _payload(capsys)

    assert payload["status"] == "pass"
    assert payload["project_ref"] == project.as_posix()
    assert payload["state_ref"] == ".microcosm"
    assert payload["safe_to_show"]["source_files_mutated"] is False


def test_cli_evidence_inspect_accepts_project_shorthand(
    capsys, tmp_path: Path
) -> None:
    project = tmp_path / "ready-project"
    project.mkdir()
    (project / "README.md").write_text(
        "# Ready Project\n\nEvidence inspect shorthand smoke.\n",
        encoding="utf-8",
    )

    assert cli.main(["tour", "--card", project.as_posix()]) == 0
    _payload(capsys)

    ref = ".microcosm/evidence/routes.json"
    assert cli.main(["evidence", "inspect", project.as_posix(), ref]) == 0
    shorthand_payload = _payload(capsys)

    assert shorthand_payload["status"] == "pass"
    assert shorthand_payload["project_ref"] == project.as_posix()
    assert shorthand_payload["evidence_ref"] == ref
    assert shorthand_payload["payload_summary"]["count_fields"]["route_count"] >= 2
    assert "readme_onboarding_route" in shorthand_payload["payload_summary"]["route_ids"]
    assert shorthand_payload["payload_summary"]["list_field_counts"]["routes"] >= 2

    assert cli.main(["evidence", "inspect", "--project", project.as_posix(), ref]) == 0
    project_flag_payload = _payload(capsys)

    assert project_flag_payload["status"] == "pass"
    assert project_flag_payload["project_ref"] == project.as_posix()
    assert project_flag_payload["evidence_ref"] == ref


def test_cli_evidence_inspect_infers_current_project_for_microcosm_ref(
    capsys, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = tmp_path / "ready-project"
    project.mkdir()
    (project / "README.md").write_text(
        "# Ready Project\n\nCurrent-directory evidence inspect smoke.\n",
        encoding="utf-8",
    )

    assert cli.main(["tour", "--card", project.as_posix()]) == 0
    _payload(capsys)

    monkeypatch.chdir(project)
    ref = ".microcosm/evidence/routes.json"
    assert cli.main(["evidence", "inspect", ref]) == 0
    payload = _payload(capsys)

    assert payload["status"] == "pass"
    assert payload["project_ref"] == "."
    assert payload["schema_version"] == "microcosm_project_evidence_card_v1"
    assert payload["evidence_ref"] == ref


def test_cli_evidence_list_limit_bounds_initialized_project(
    capsys, tmp_path: Path
) -> None:
    project = tmp_path / "ready-project"
    evidence_dir = project / ".microcosm" / "evidence"
    evidence_dir.mkdir(parents=True)
    for name in ("routes", "patterns", "index"):
        (evidence_dir / f"{name}.json").write_text(
            json.dumps(
                {
                    "schema_version": f"microcosm_project_{name}_v1",
                    "status": "pass",
                    "project_id": "ready-project",
                    "created_at": "2026-05-28T00:00:00+00:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )

    assert cli.main(["evidence", "list", project.as_posix(), "--limit", "2"]) == 0
    payload = _payload(capsys)

    assert payload["status"] == "pass"
    assert payload["evidence_count"] == 3
    assert payload["returned_evidence_count"] == 2
    assert payload["limit"] == 2
    assert payload["truncated"] is True
    assert len(payload["evidence"]) == 2
