from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


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
    nested = json_dir / "routes"
    nested.mkdir(parents=True)
    (nested / "first.json").write_text("{}", encoding="utf-8")
    original_glob = Path.glob

    def guarded_glob(self: Path, pattern: str):
        if self == json_dir and pattern == "*.json":
            raise AssertionError("json presence check should use recursive state streaming")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", guarded_glob)

    assert transaction_evidence_stability._has_json_file(json_dir) is True


def test_transaction_evidence_stability_state_files_stream_without_path_rglob(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "scratch_project"
    state = project / ".microcosm"
    nested = state / "nested"
    nested.mkdir(parents=True)
    (state / "events.jsonl").write_text('{"event_id":"evt_0001"}\n', encoding="utf-8")
    (nested / "artifact.json").write_text("{}", encoding="utf-8")
    (nested / "ignored.txt").write_text("not state json", encoding="utf-8")
    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == state:
            raise AssertionError("transaction state scan should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    assert [
        path.relative_to(state).as_posix()
        for path in transaction_evidence_stability._state_files(project)
    ] == ["events.jsonl", "nested/artifact.json"]


def test_transaction_evidence_stability_state_files_skip_symlinked_json(
    tmp_path: Path,
) -> None:
    project = tmp_path / "scratch_project"
    state = project / ".microcosm"
    state.mkdir(parents=True)
    (state / "project_manifest.json").write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside_state.json"
    outside.write_text('{"outside": true}', encoding="utf-8")
    symlink = state / "linked_state.json"
    try:
        symlink.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    assert [
        path.relative_to(state).as_posix()
        for path in transaction_evidence_stability._state_files(project)
    ] == ["project_manifest.json"]


def test_transaction_evidence_stability_state_file_walk_recurses_without_entry_list(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "scratch_project"
    state = project / ".microcosm"
    nested = state / "nested"
    nested.mkdir(parents=True)
    (state / "root.json").write_text("{}", encoding="utf-8")
    (nested / "artifact.json").write_text("{}", encoding="utf-8")

    original_scandir = transaction_evidence_stability.os.scandir
    nested_opened = False

    class FakeEntry:
        def __init__(self, name: str, *, is_dir: bool, is_file: bool) -> None:
            self.name = name
            self._is_dir = is_dir
            self._is_file = is_file

        def is_dir(self, *, follow_symlinks: bool = False) -> bool:
            return self._is_dir

        def is_file(self, *, follow_symlinks: bool = False) -> bool:
            return self._is_file

    class ScandirRows:
        def __init__(
            self, rows: list[FakeEntry], *, guarded_parent: bool = False
        ) -> None:
            self._rows = rows
            self._guarded_parent = guarded_parent
            self._index = 0

        def __enter__(self) -> "ScandirRows":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> "ScandirRows":
            return self

        def __next__(self) -> FakeEntry:
            nonlocal nested_opened
            if self._index >= len(self._rows):
                raise StopIteration
            if self._guarded_parent and self._index == 1 and not nested_opened:
                raise AssertionError(
                    "state file scan should recurse before pulling sibling entries"
                )
            row = self._rows[self._index]
            self._index += 1
            return row

    def guarded_scandir(path: Path):
        nonlocal nested_opened
        if path == state:
            return ScandirRows(
                [
                    FakeEntry("nested", is_dir=True, is_file=False),
                    FakeEntry("root.json", is_dir=False, is_file=True),
                ],
                guarded_parent=True,
            )
        if path == nested:
            nested_opened = True
            return ScandirRows([FakeEntry("artifact.json", is_dir=False, is_file=True)])
        return original_scandir(path)

    monkeypatch.setattr(transaction_evidence_stability.os, "scandir", guarded_scandir)

    assert [
        path.relative_to(state).as_posix()
        for path in transaction_evidence_stability._state_files(project)
    ] == ["nested/artifact.json", "root.json"]
    assert nested_opened is True


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


def test_transaction_evidence_stability_validator_resolves_nested_evidence_and_explanations(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    state = project / ".microcosm"
    state.mkdir()
    route_id = "readme_onboarding_route"
    pattern_id = "pat_readme"
    work_id = "work_0001"
    event_id = "evt_0001"
    evidence_ref = ".microcosm/evidence/routes/readme_onboarding.json"

    _write_json(state / "patterns.json", {"patterns": [{"pattern_id": pattern_id}]})
    _write_json(
        state / "routes.json",
        {
            "routes": [
                {
                    "route_id": route_id,
                    "pattern_refs": [pattern_id],
                    "standard_pressure_refs": [],
                }
            ]
        },
    )
    _write_json(
        state / "work_items.json",
        {
            "work_items": [
                {
                    "work_id": work_id,
                    "route_id": route_id,
                    "route_snapshot": {"route_id": route_id},
                    "satisfaction_contract": {"status": "declared"},
                    "integration_contract": {"status": "declared"},
                    "transaction_policy": {"source_files_mutated": False},
                    "status": "closed",
                    "state_history": [
                        {"state": "created"},
                        {"state": "selected"},
                        {"state": "planned"},
                        {"state": "executed_simulation"},
                        {"state": "closed"},
                    ],
                    "closeout": {
                        "satisfaction_contract_met": True,
                        "integration_contract_met": True,
                        "evidence_ref": evidence_ref,
                    },
                    "event_refs": [{"event_id": event_id}],
                    "evidence_refs": [evidence_ref],
                    "source_files_mutated": False,
                }
            ]
        },
    )
    (state / "events.jsonl").write_text(
        json.dumps({"event_id": event_id, "span": "work.closed", "evidence_ref": evidence_ref}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        state / "explanations/routes/readme_onboarding.json",
        {
            "route_id": route_id,
            "pattern_bindings": [{"pattern_id": pattern_id, "resolved": True}],
            "standard_bindings": [{"standard_id": "std_microcosm", "resolved": True}],
            "evidence_refs": [evidence_ref],
        },
    )
    _write_json(
        state / "evidence/routes/readme_onboarding.json",
        {
            "evidence_id": "evidence_0001",
            "evidence_replacement": {
                "stable_ref": evidence_ref,
                "policy": "stable_ref_latest_body",
                "replacement_recorded": True,
                "append_only_event_history_ref": ".microcosm/events.jsonl",
            },
        },
    )
    _write_json(
        state / "graph.json",
        {
            "nodes": [
                {"node_id": f"route:{route_id}"},
                {"node_id": f"work:{work_id}"},
            ],
            "edges": [
                {
                    "from": f"work:{work_id}",
                    "to": f"route:{route_id}",
                    "relation": "uses_route",
                }
            ],
        },
    )

    out = tmp_path / "transaction_evidence_stability_nested.json"
    receipt = validate_stability(MICROCOSM_ROOT, project, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["evidence_count"] == 1
    assert receipt["consistency_summary"]["explain_refs_resolve"] is True
    assert receipt["consistency_summary"]["work_event_evidence_refs_resolve"] is True
    assert receipt["consistency_summary"]["events_reference_existing_evidence"] is True
    assert receipt["consistency_summary"]["evidence_replacements_recorded"] is True


def test_transaction_evidence_stability_validator_streams_event_summary(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    _run_causal_loop(project)
    out = tmp_path / "transaction_evidence_stability.json"

    def fail_read_jsonl(_path: Path) -> list[dict[str, Any]]:
        raise AssertionError("transaction stability validator should stream event summaries")

    monkeypatch.setattr(transaction_evidence_stability, "_read_jsonl", fail_read_jsonl)

    receipt = validate_stability(MICROCOSM_ROOT, project, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["event_count"] >= 1
    assert receipt["consistency_summary"]["events_reference_existing_evidence"] is True
    assert receipt["consistency_summary"]["work_event_evidence_refs_resolve"] is True


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
