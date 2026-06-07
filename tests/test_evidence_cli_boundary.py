from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core import project_substrate


def _payload(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def _assert_evidence_interpretation(payload: dict) -> None:
    interpretation = payload["evidence_interpretation"]
    assert "not release" in interpretation["status_pass_means"]
    assert "proof-correctness" in interpretation["status_pass_means"]
    assert (
        "private-root equivalence authority" in interpretation["status_pass_means"]
    )
    assert "safe shape/ref summary" in interpretation["payload_summary_means"]
    assert "not source body export" in interpretation["payload_summary_means"]
    assert "owning validator/builder" in interpretation["next_step"]


def _assert_full_payload_drilldown(
    payload: dict, *, project_ref: str, evidence_ref: str
) -> None:
    drilldown = payload["full_payload_drilldown"]
    project_prefix = project_ref.rstrip("/")
    if project_prefix in {"", "."}:
        expected_path = f"./{evidence_ref}"
    else:
        expected_path = f"{project_prefix}/{evidence_ref}"
    assert drilldown["path"] == expected_path
    assert drilldown["command"] == f"python3 -m json.tool {expected_path}"
    assert "complete local JSON receipt" in drilldown["meaning"]
    assert "drilldown evidence only" in drilldown["authority_boundary"]
    assert "proof correctness" in drilldown["authority_boundary"]


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
    assert payload["evidence"][0]["inspect_command"] == (
        "microcosm evidence inspect --project "
        f"{project.as_posix()} .microcosm/evidence/routes.json"
    )
    assert payload["inspect_drilldown"] == {
        "command_template": "microcosm evidence inspect --project <project> <evidence_ref>",
        "project_key": "project_ref",
        "row_key": "evidence_ref",
        "field": "payload_summary",
    }
    _assert_evidence_interpretation(payload)


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
    assert payload["state_write_proof"]["state_write_result_ref"] == (
        f"microcosm tour --card {project.as_posix()}::state_write_result"
    )
    assert payload["state_write_proof"]["status_card_project_state_ref"] == (
        f"microcosm status --card {project.as_posix()}::front_door.project_state"
    )
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
    _assert_full_payload_drilldown(
        shorthand_payload,
        project_ref=project.as_posix(),
        evidence_ref=ref,
    )
    _assert_evidence_interpretation(shorthand_payload)

    assert cli.main(["evidence", "inspect", "--project", project.as_posix(), ref]) == 0
    project_flag_payload = _payload(capsys)

    assert project_flag_payload["status"] == "pass"
    assert project_flag_payload["project_ref"] == project.as_posix()
    assert project_flag_payload["evidence_ref"] == ref
    _assert_full_payload_drilldown(
        project_flag_payload,
        project_ref=project.as_posix(),
        evidence_ref=ref,
    )
    _assert_evidence_interpretation(project_flag_payload)


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
    _assert_full_payload_drilldown(payload, project_ref=".", evidence_ref=ref)
    _assert_evidence_interpretation(payload)


def test_cli_evidence_inspect_not_found_keeps_interpretation_boundary(
    capsys, tmp_path: Path
) -> None:
    project = tmp_path / "ready-project"
    (project / ".microcosm" / "evidence").mkdir(parents=True)

    assert (
        cli.main(
            [
                "evidence",
                "inspect",
                project.as_posix(),
                ".microcosm/evidence/missing.json",
            ]
        )
        == 1
    )
    payload = _payload(capsys)

    assert payload["status"] == "not_found"
    assert payload["evidence_ref"] == ".microcosm/evidence/missing.json"
    _assert_full_payload_drilldown(
        payload,
        project_ref=project.as_posix(),
        evidence_ref=".microcosm/evidence/missing.json",
    )
    _assert_evidence_interpretation(payload)


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
    assert payload["evidence"][0]["inspect_command"].startswith(
        f"microcosm evidence inspect --project {project.as_posix()} "
    )
    _assert_evidence_interpretation(payload)


def test_cli_evidence_list_rejects_negative_limit(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["evidence", "list", "--limit", "-1"])

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert "argument --limit: must be >= 0" in stderr


def test_cli_evidence_list_help_explains_reviewer_drilldown(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["evidence", "list", "--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "Lists compact evidence refs." in output
    assert "microcosm evidence list <project> --limit 25" in output
    assert "microcosm evidence inspect --project <project> <evidence_ref>" in output
    assert "bounded receipt index after behavior is visible" in output
    assert "not a release" in output
    assert "schema_version" in output


def test_cli_evidence_inspect_help_explains_receipt_card_boundary(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["evidence", "inspect", "--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "Reads one evidence card." in output
    assert "status=pass means the inspect command produced the card" in output
    assert "payload_summary is the safe shape/ref summary" in output
    assert "inspect cards do not export source bodies" in output
    assert "full_payload_drilldown.command" in output
    assert "not release" in output
    assert "private-root equivalence authority" in output


def test_project_evidence_list_only_reads_returned_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "ready-project"
    evidence_dir = project / ".microcosm" / "evidence"
    evidence_dir.mkdir(parents=True)
    for index in range(5):
        (evidence_dir / f"result_{index}.json").write_text(
            "{}\n",
            encoding="utf-8",
        )
    read_refs: list[str] = []

    def read_project_json(project_path: Path, rel: str) -> dict[str, object]:
        read_refs.append(rel)
        return {
            "schema_version": "microcosm_project_evidence_v1",
            "status": "pass",
            "project_id": project_path.name,
        }

    monkeypatch.setattr(
        project_substrate,
        "_read_project_json",
        read_project_json,
    )

    payload = project_substrate.list_evidence(project, limit=2)

    assert payload["status"] == "pass"
    assert payload["evidence_count"] == 5
    assert payload["returned_evidence_count"] == 2
    assert payload["truncated"] is True
    assert read_refs == [
        "evidence/result_0.json",
        "evidence/result_1.json",
    ]


def test_project_evidence_list_streams_nested_refs_without_glob(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "ready-project"
    evidence_dir = project / ".microcosm" / "evidence"
    nested_dir = evidence_dir / "nested"
    nested_dir.mkdir(parents=True)
    (nested_dir / "proof.json").write_text(
        '{"schema_version": "microcosm_project_evidence_v1", "status": "pass"}\n',
        encoding="utf-8",
    )
    (evidence_dir / "routes.json").write_text(
        '{"schema_version": "microcosm_project_evidence_v1", "status": "pass"}\n',
        encoding="utf-8",
    )
    (nested_dir / "notes.txt").write_text("not evidence\n", encoding="utf-8")

    original_glob = Path.glob

    def fail_if_globbed(self: Path, pattern: str) -> object:
        if self == evidence_dir and pattern == "*.json":
            raise AssertionError("list_evidence should stream evidence discovery")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fail_if_globbed)

    payload = project_substrate.list_evidence(project)

    assert payload["evidence_count"] == 2
    assert payload["returned_evidence_count"] == 2
    assert [row["evidence_ref"] for row in payload["evidence"]] == [
        ".microcosm/evidence/nested/proof.json",
        ".microcosm/evidence/routes.json",
    ]
    assert payload["evidence"][0]["inspect_command"].endswith(
        ".microcosm/evidence/nested/proof.json"
    )


def test_project_evidence_limited_path_selection_preserves_count_and_order(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / ".microcosm" / "evidence"
    rows = [
        evidence_dir / "routes_z.json",
        evidence_dir / "routes_b.json",
        evidence_dir / "routes_a.json",
        evidence_dir / "routes_c.json",
    ]

    count, selected = project_substrate._bounded_sorted_paths(iter(rows), 2)

    assert count == 4
    assert [path.name for path in selected] == [
        "routes_a.json",
        "routes_b.json",
    ]
