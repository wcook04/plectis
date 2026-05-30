from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core import cli
from microcosm_core import project_substrate
from microcosm_core.validators import transaction_evidence_stability
from microcosm_core.validators.transaction_evidence_stability import validate_stability


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


def _run_causal_loop(project: Path) -> str:
    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project, "readme_onboarding_route")
    project_substrate.run_work(project, str(created["work_id"]))
    project_substrate.observe_project(project)
    project_substrate.state_graph(project)
    project_substrate.list_evidence(project)
    return str(created["work_id"])


def test_state_artifact_semantics_checks_json_presence_without_materializing_glob(
    tmp_path: Path, monkeypatch
) -> None:
    json_dir = tmp_path / ".microcosm/explanations"
    json_dir.mkdir(parents=True)
    first = json_dir / "first.json"
    second = json_dir / "second.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    original_glob = Path.glob
    yielded: list[str] = []

    def guarded_glob(self: Path, pattern: str):
        if self == json_dir and pattern == "*.json":
            def stream():
                yielded.append("first")
                yield first
                yielded.append("second")
                raise AssertionError("json presence check should stop after first match")

            return stream()
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", guarded_glob)

    assert transaction_evidence_stability._has_json_file(json_dir) is True
    assert yielded == ["first"]


def test_transaction_evidence_stability_read_jsonl_streams_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        '{"event_id":"evt_0001","ref":"evidence/one.json"}\n'
        '["skip non-object rows"]\n'
        "\n"
        '{"event_id":"evt_0002","ref":"evidence/two.json"}\n',
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == events:
            raise AssertionError("transaction evidence JSONL reader should stream rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert transaction_evidence_stability._read_jsonl(events) == [
        {"event_id": "evt_0001", "ref": "evidence/one.json"},
        {"event_id": "evt_0002", "ref": "evidence/two.json"},
    ]


def test_transaction_evidence_stability_validator_proves_resolved_chain(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    work_id = _run_causal_loop(project)
    first_events = (project / ".microcosm/events.jsonl").read_text(encoding="utf-8").splitlines()

    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    rerun = project_substrate.run_work(project, work_id)
    project_substrate.observe_project(project)
    project_substrate.state_graph(project)
    project_substrate.list_evidence(project)

    assert rerun["idempotent_replay"] is True
    second_events = (project / ".microcosm/events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(second_events) > len(first_events)
    work_payload = json.loads((project / ".microcosm/work_items.json").read_text(encoding="utf-8"))
    assert [row["state"] for row in work_payload["work_items"][0]["state_history"]] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]

    out = tmp_path / "transaction_evidence_stability.json"
    receipt = validate_stability(MICROCOSM_ROOT, project, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["consistency_summary"]["route_pattern_refs_resolve"] is True
    assert receipt["consistency_summary"]["route_standard_refs_resolve"] is True
    assert receipt["consistency_summary"]["explain_refs_resolve"] is True
    assert receipt["consistency_summary"]["work_event_evidence_refs_resolve"] is True
    assert receipt["consistency_summary"]["events_reference_existing_evidence"] is True
    assert receipt["consistency_summary"]["evidence_replacements_recorded"] is True
    assert receipt["consistency_summary"]["events_are_append_only"] is True
    semantics = {
        row["state_ref"]: row["semantics"]
        for row in receipt["state_artifact_semantics"]
    }
    assert semantics[".microcosm/events.jsonl"] == "append_only_event_history"
    assert semantics[".microcosm/evidence/*.json"] == "stable_ref_latest_body_with_replacement_metadata"


def test_cli_transaction_evidence_stability_command(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    _run_causal_loop(project)
    out = tmp_path / "transaction_evidence_stability.json"

    assert cli.main(
        [
            "transaction-evidence-stability",
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
    assert payload["consistency_summary"]["release_authorized"] is False
    assert "pass" not in capsys.readouterr().err
