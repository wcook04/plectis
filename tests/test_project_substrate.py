from __future__ import annotations

import builtins
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from microcosm_core import architecture_kernel
from microcosm_core import project_substrate
from microcosm_core import cli
from microcosm_core import runtime_shell
from microcosm_core.public_payload_boundary import SOURCE_OPEN_BODY_POLICY
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/scratch_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch Project\n\nLocal proof project.\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src/scratch_app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_smoke.py").write_text(
        "from scratch_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_project_index_skips_file_that_disappears_during_walk(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    transient = (
        project
        / "receipts/runtime_shell/workingness_failure_map.json.disappearing"
    )
    transient.parent.mkdir(parents=True)
    transient.write_text("{}", encoding="utf-8")
    original_stat = os.stat

    def stat_with_disappearing_file(
        path: str | os.PathLike[str], *args: Any, **kwargs: Any
    ) -> os.stat_result:
        if os.fspath(path) == os.fspath(transient):
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", stat_with_disappearing_file)

    index_result = project_substrate.index_project(project)
    catalog_paths = {
        row["path"] for row in project_substrate.catalog_project(project)["files"]
    }

    assert index_result["status"] == "pass"
    assert index_result["file_count"] == 4
    assert (
        "receipts/runtime_shell/workingness_failure_map.json.disappearing"
        not in catalog_paths
    )


def test_project_walk_passes_precomputed_classification_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    original_classify = project_substrate._classify_file
    calls: list[dict[str, Any]] = []

    def classify_spy(rel: str, path=None, **kwargs: Any) -> str:
        calls.append({"rel": rel, "path": path, **kwargs})
        return original_classify(rel, path, **kwargs)

    monkeypatch.setattr(project_substrate, "_classify_file", classify_spy)

    catalog = project_substrate._project_catalog_payload(project)

    assert catalog["file_count"] == 4
    assert calls
    assert all(call["path"] is None for call in calls)
    assert all(call["name"] and call["suffix"] is not None for call in calls)
    assert any(call["parts"] == {"src", "scratch_app", "__init__.py"} for call in calls)


def test_tour_assay_predicate_coverage_prefers_verification_status() -> None:
    producer_predicates = {
        "join_integrity": True,
        "selection_binding": True,
        "record_classification_matrix": True,
    }
    verified_predicates = {
        "record_classification_matrix": False,
        "assertion_matrix_coverage": True,
    }

    assay = runtime_shell._tour_command_causality_coverage_assay(
        compiled={
            "selected_route_id": "readme_onboarding_route",
            "work_id": "work_0002",
        },
        command_reference_execution_case={
            "status": "blocked",
            "selected_work_id": "work_0002",
            "root_work_id": "work_0002",
            "verification_status": "blocked",
            "public_architecture_witness_eligible": False,
            "public_witness_status": "verification_blocked",
            "state_delta_refs": [".microcosm/work_items.json::work_0002"],
            "predicate_status": producer_predicates,
            "verification_predicate_status": verified_predicates,
        },
        project_compile_state_written=False,
        cached_state_reused=True,
    )

    assert assay["predicate_coverage"]["join_integrity"] is True
    assert assay["predicate_coverage"]["record_classification_matrix"] is False
    assert assay["predicate_coverage"]["assertion_matrix_coverage"] is True
    assert assay["predicate_coverage_sources"] == {
        "join_integrity": "predicate_status",
        "selection_binding": "predicate_status",
        "record_classification_matrix": "verification_predicate_status",
        "assertion_matrix_coverage": "verification_predicate_status",
    }
    review = assay["agent_harness_record_review"]
    assert review["schema_version"] == "microcosm_agent_harness_record_review_cue_v1"
    assert review["status"] == "selected_work_record_gap"
    assert review["candidate_record_scope"] == (
        "selected_work_reference_case_not_tour_invocation"
    )
    assert review["selected_work_id"] == "work_0002"
    assert review["tour_command_root_blockers"] == [
        "tour_returned_root_handle",
        "tour_invocation_envelope",
        "tour_direct_child_relation_closure",
        "tour_state_delta_scope",
        "tour_projection_fidelity_to_tour_root",
    ]
    axes = {row["axis"]: row for row in review["review_axes"]}
    assert axes["trajectory"]["status"] == "missing"
    assert axes["reproducibility_fixture"]["state_delta_ref_count"] == 1
    assert axes["task_boundary"]["record_classification_matrix_verified"] is False
    assert axes["benchmark_anti_claim"]["status"] == (
        "not_claimed_here_check_if_benchmark_context"
    )
    assert axes["closeout_check"]["status"] == "missing_or_blocked"


def test_python_lens_counts_relative_and_absolute_imports_separately(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    (project / "src/scratch_app/helpers.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "src/scratch_app/imports.py").write_text(
        "from . import helpers\n"
        "from .helpers import VALUE\n"
        "import os\n"
        "from pathlib import Path\n",
        encoding="utf-8",
    )

    lens = project_substrate.python_lens(project, write_state=False)
    imports_row = next(
        row for row in lens["path_rows"] if row["path"] == "src/scratch_app/imports.py"
    )

    assert imports_row["relative_import_count"] == 2
    assert imports_row["absolute_import_count"] == 2


def test_event_id_allocation_counts_existing_lines_without_decoding_history(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    event_path = project / ".microcosm/events.jsonl"
    event_path.parent.mkdir()
    event_path.write_text(
        '{"event_id":"evt_0001","span":"seed"}\n'
        '{"malformed"\n'
        "\n",
        encoding="utf-8",
    )

    event = project_substrate._event(project, "project.fast_append", "pass")
    project_substrate._append_event(project, event)

    assert event["event_id"] == "evt_0003"
    assert event_path.read_text(encoding="utf-8").splitlines()[-1].startswith(
        '{"created_at":'
    )


def test_event_id_allocation_reuses_cache_after_append(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    event_path = project / ".microcosm/events.jsonl"
    event_path.parent.mkdir()
    event_path.write_text(
        '{"event_id":"evt_0001","span":"seed"}\n'
        '{"event_id":"evt_0002","span":"seed"}\n',
        encoding="utf-8",
    )
    project_substrate._EVENT_NUMBER_CACHE.clear()
    read_count = 0
    original_open = Path.open

    def open_spy(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        nonlocal read_count
        if self == event_path and "r" in mode and "+" not in mode:
            read_count += 1
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_spy)

    first_event = project_substrate._event(project, "project.first", "pass")
    project_substrate._append_event(project, first_event)
    second_event = project_substrate._event(project, "project.second", "pass")

    assert first_event["event_id"] == "evt_0003"
    assert second_event["event_id"] == "evt_0004"
    assert read_count == 1


def test_event_id_allocation_cache_invalidates_on_external_event_stream_change(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    event_path = project / ".microcosm/events.jsonl"
    event_path.parent.mkdir()
    event_path.write_text('{"event_id":"evt_0001","span":"seed"}\n', encoding="utf-8")
    project_substrate._EVENT_NUMBER_CACHE.clear()

    first_event = project_substrate._event(project, "project.first", "pass")
    with event_path.open("a", encoding="utf-8") as fh:
        fh.write('{"event_id":"evt_0002","span":"external"}\n')
    second_event = project_substrate._event(project, "project.second", "pass")

    assert first_event["event_id"] == "evt_0002"
    assert second_event["event_id"] == "evt_0003"


def test_read_jsonl_streams_dict_rows_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    jsonl_path = tmp_path / "events.jsonl"
    jsonl_path.write_text(
        '{"event_id":"evt_0001","span":"seed"}\n'
        '["skip non-object rows"]\n'
        "\n"
        '{"event_id":"evt_0002","span":"next"}\n',
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == jsonl_path:
            raise AssertionError("_read_jsonl should stream JSONL rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert project_substrate._read_jsonl(jsonl_path) == [
        {"event_id": "evt_0001", "span": "seed"},
        {"event_id": "evt_0002", "span": "next"},
    ]


def test_observe_project_counts_evidence_without_materializing_payloads(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    state = project / ".microcosm"
    route_id = "readme_onboarding_route"
    (state / "explanations").mkdir(parents=True)
    (state / "evidence").mkdir()
    (state / "routes.json").write_text(
        json.dumps({"routes": [{"route_id": route_id}]}) + "\n",
        encoding="utf-8",
    )
    (state / "work_items.json").write_text(
        json.dumps(
            {
                "work_items": [
                    {
                        "work_id": "work_0001",
                        "route_id": route_id,
                        "status": "closed",
                        "state_history": [{"state": "closed"}],
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (state / "explanations" / f"{route_id}.json").write_text(
        json.dumps(
            {
                "status": "pass",
                "route_id": route_id,
                "causal_chain_proof": {
                    "status": "pass",
                    "selected_work_id": "work_0001",
                    "selected_work_status": "closed",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (state / "graph.json").write_text(
        json.dumps({"node_count": 1, "edge_count": 0}) + "\n",
        encoding="utf-8",
    )
    (state / "state_index.json").write_text(
        json.dumps({"status": "pass"}) + "\n",
        encoding="utf-8",
    )
    (state / "events.jsonl").write_text(
        json.dumps({"event_id": "evt_0001", "span": "work.run", "status": "pass"})
        + "\n",
        encoding="utf-8",
    )
    observed_limits: list[int | None] = []

    def list_evidence_count_only(
        _project: str | Path,
        *,
        limit: int | None = None,
    ) -> dict[str, object]:
        if limit is None:
            raise AssertionError("observe should request count-only evidence listing")
        observed_limits.append(limit)
        return {
            "status": "pass",
            "evidence_count": 42,
            "returned_evidence_count": 0,
            "limit": limit,
            "truncated": True,
            "evidence": [],
        }

    monkeypatch.setattr(project_substrate, "list_evidence", list_evidence_count_only)

    observed = project_substrate.observe_project(project, refresh_architecture=False)

    assert observed_limits == [0]
    assert observed["evidence_ref_count"] == 42
    assert observed["causal_chain"]["evidence_ref_count"] == 42


def test_compile_project_counts_evidence_without_materializing_payloads(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    observed_limits: list[int | None] = []

    def list_evidence_count_only(
        _project: str | Path,
        *,
        limit: int | None = None,
    ) -> dict[str, object]:
        if limit is None:
            raise AssertionError("compile should request count-only evidence listing")
        observed_limits.append(limit)
        return {
            "status": "pass",
            "evidence_count": 42,
            "returned_evidence_count": 0,
            "limit": limit,
            "truncated": True,
            "evidence": [],
        }

    monkeypatch.setattr(project_substrate, "list_evidence", list_evidence_count_only)

    compiled = project_substrate.compile_project(project)

    assert observed_limits == [0, 0]
    assert compiled["evidence_count"] == 42
    assert "wrote 42 evidence refs" in compiled["what_happened"]


def test_event_stream_summary_streams_counts_and_bounded_tail(
    tmp_path: Path, monkeypatch
) -> None:
    jsonl_path = tmp_path / "events.jsonl"
    jsonl_path.write_text(
        "".join(
            f'{{"event_id":"evt_{index:04d}","span":"span_{index % 2}"}}\n'
            for index in range(1, 26)
        )
        + '["skip non-object rows"]\n'
        + "\n",
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == jsonl_path:
            raise AssertionError("_read_event_stream_summary should stream JSONL rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    summary = project_substrate._read_event_stream_summary(jsonl_path, tail_limit=3)

    assert summary["event_count"] == 25
    assert summary["spans"] == {"span_0": 12, "span_1": 13}
    assert [row["event_id"] for row in summary["events"]] == [
        "evt_0023",
        "evt_0024",
        "evt_0025",
    ]
    assert summary["last_event"]["event_id"] == "evt_0025"


def test_observe_project_streams_event_summary_without_full_jsonl_list(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    event_path = project / ".microcosm/events.jsonl"
    event_path.parent.mkdir()
    event_path.write_text(
        "".join(
            f'{{"event_id":"evt_{index:04d}","span":"span_{index % 3}"}}\n'
            for index in range(1, 26)
        ),
        encoding="utf-8",
    )

    def fail_read_jsonl(_path: Path) -> list[dict[str, Any]]:
        raise AssertionError("observe_project should use the streaming event summary")

    monkeypatch.setattr(project_substrate, "_read_jsonl", fail_read_jsonl)

    observed = project_substrate.observe_project(project, refresh_architecture=False)

    assert observed["event_count"] == 25
    assert observed["spans"] == {"span_0": 8, "span_1": 9, "span_2": 8}
    assert len(observed["events"]) == 20
    assert observed["events"][0]["event_id"] == "evt_0006"
    assert observed["events"][-1]["event_id"] == "evt_0025"


def test_architecture_kernel_read_jsonl_streams_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    jsonl_path = tmp_path / "architecture_events.jsonl"
    jsonl_path.write_text(
        '{"event_id":"evt_0001","span":"seed"}\n'
        '["skip non-object rows"]\n'
        "\n"
        '{"event_id":"evt_0002","span":"next"}\n',
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == jsonl_path:
            raise AssertionError("architecture_kernel.read_jsonl should stream JSONL rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert architecture_kernel.read_jsonl(jsonl_path) == [
        {"event_id": "evt_0001", "span": "seed"},
        {"event_id": "evt_0002", "span": "next"},
    ]


def test_route_explanation_streams_event_refs_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    RuntimeShell(MICROCOSM_ROOT).tour_card(project)
    events_path = project / ".microcosm" / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as handle:
        for index in range(1, 16):
            handle.write(
                json.dumps(
                    {
                        "event_id": f"evt_stream_{index:04d}",
                        "span": "project.route",
                        "status": "pass",
                    }
                )
                + "\n"
            )
            handle.write(
                json.dumps(
                    {
                        "event_id": f"evt_skip_{index:04d}",
                        "span": "ignore.this",
                        "status": "pass",
                    }
                )
                + "\n"
            )

    def fail_read_jsonl(_path: Path) -> list[dict[str, Any]]:
        raise AssertionError("route explanations should stream bounded event refs")

    standard_surface_calls = 0
    original_load_standard_surface = architecture_kernel.load_standard_pressure_surface

    def counted_load_standard_surface(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal standard_surface_calls
        standard_surface_calls += 1
        return original_load_standard_surface(*args, **kwargs)

    monkeypatch.setattr(architecture_kernel, "read_jsonl", fail_read_jsonl)
    monkeypatch.setattr(
        architecture_kernel,
        "load_standard_pressure_surface",
        counted_load_standard_surface,
    )

    explanation = architecture_kernel.explain_route(project, "readme_onboarding_route")

    assert standard_surface_calls == 1
    assert [row["event_id"] for row in explanation["event_refs"]] == [
        f"evt_stream_{index:04d}" for index in range(4, 16)
    ]
    assert {row["span"] for row in explanation["event_refs"]} == {"project.route"}


def test_read_text_prefix_streams_bounded_prefix_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    source_path = tmp_path / "large_module.py"
    source_path.write_text("0123456789" * 1000, encoding="utf-8")
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == source_path:
            raise AssertionError("_read_text_prefix should stream bounded reads")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert project_substrate._read_text_prefix(source_path, limit=12) == "012345678901"


def test_sha256_file_streams_without_materializing_body(
    tmp_path: Path, monkeypatch
) -> None:
    source_path = tmp_path / "large_evidence.json"
    body = (
        b'{"payload":"'
        + (b"x" * (project_substrate.HASH_CHUNK_SIZE + 17))
        + b'"}'
    )
    source_path.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == source_path:
            raise AssertionError("_sha256_file should stream file bodies")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert project_substrate._sha256_file(source_path) == (
        hashlib.sha256(body).hexdigest()
    )


def test_state_ref_status_counts_directory_json_without_materializing_glob(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    evidence_dir = project / ".microcosm/evidence"
    evidence_dir.mkdir(parents=True)
    for index in range(3):
        (evidence_dir / f"row_{index}.json").write_text("{}", encoding="utf-8")
    (evidence_dir / "notes.txt").write_text("not counted", encoding="utf-8")

    original_glob = Path.glob
    glob_rows = tuple(original_glob(evidence_dir, "*.json"))
    glob_iterable = None

    def guarded_glob(self: Path, pattern: str):
        if self == evidence_dir and pattern == "*.json":
            nonlocal glob_iterable
            glob_iterable = (path for path in glob_rows)
            return glob_iterable
        return original_glob(self, pattern)

    original_list = builtins.list

    def guarded_list(value=(), /):
        if value is glob_iterable:
            raise AssertionError("_state_ref_status should stream JSON counts")
        return original_list(value)

    monkeypatch.setattr(Path, "glob", guarded_glob)
    monkeypatch.setattr(builtins, "list", guarded_list)

    status = project_substrate._state_ref_status(project, ".microcosm/evidence/")

    assert status["json_count"] == 3


def test_architecture_state_index_counts_asset_json_without_materializing_glob(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    evidence_dir = project / ".microcosm/evidence"
    explanation_dir = project / ".microcosm/explanations"
    nested_evidence_dir = evidence_dir / "nested"
    nested_explanation_dir = explanation_dir / "nested"
    evidence_dir.mkdir(parents=True)
    explanation_dir.mkdir(parents=True)
    nested_evidence_dir.mkdir()
    nested_explanation_dir.mkdir()
    for index in range(2):
        (evidence_dir / f"receipt_{index}.json").write_text("{}", encoding="utf-8")
    (nested_evidence_dir / "receipt_nested.json").write_text("{}", encoding="utf-8")
    (explanation_dir / "route.json").write_text("{}", encoding="utf-8")
    (nested_explanation_dir / "route_nested.json").write_text("{}", encoding="utf-8")
    (explanation_dir / "notes.txt").write_text("not counted", encoding="utf-8")
    (nested_evidence_dir / "notes.txt").write_text("not counted", encoding="utf-8")

    original_glob = Path.glob

    def guarded_glob(self: Path, pattern: str):
        if self in {evidence_dir, explanation_dir} and pattern == "*.json":
            raise AssertionError("build_state_index should stream JSON asset counts")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", guarded_glob)

    state_index = architecture_kernel.build_state_index(project)
    item_counts = {
        row["asset_id"]: row.get("item_count") for row in state_index["assets"]
    }

    assert item_counts["evidence"] == 3
    assert item_counts["explanation"] == 2


def test_architecture_state_index_handles_unreadable_asset_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    state_dir = project / ".microcosm"
    evidence_dir = state_dir / "evidence"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "receipt.json").write_text("{}", encoding="utf-8")
    catalog_path = state_dir / "catalog.json"
    catalog_path.write_text("{}", encoding="utf-8")
    original_is_file = Path.is_file
    original_is_dir = Path.is_dir

    def guarded_is_file(self: Path) -> bool:
        if self == catalog_path:
            raise OSError("metadata unavailable")
        return original_is_file(self)

    def guarded_is_dir(self: Path) -> bool:
        if self == evidence_dir:
            raise OSError("metadata unavailable")
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)

    state_index = architecture_kernel.build_state_index(project)
    rows = {row["asset_id"]: row for row in state_index["assets"]}

    assert rows["catalog"]["exists"] is False
    assert rows["evidence"]["exists"] is False
    assert rows["evidence"]["item_count"] == 0


def test_architecture_read_helpers_treat_unreadable_metadata_as_missing(
    tmp_path: Path, monkeypatch
) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_text('{"status": "pass"}\n', encoding="utf-8")
    events_path = tmp_path / "events.jsonl"
    events_path.write_text('{"status": "pass"}\n', encoding="utf-8")
    original_is_file = Path.is_file

    def guarded_is_file(self: Path) -> bool:
        if self in {payload_path, events_path}:
            raise OSError("metadata unavailable")
        return original_is_file(self)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    assert architecture_kernel.read_json_if_exists(payload_path) == {}
    assert architecture_kernel.read_jsonl(events_path) == []


def test_architecture_graph_reuses_standard_pressure_surface_per_build(
    tmp_path: Path, monkeypatch
) -> None:
    project = _scratch_project(tmp_path)
    state_dir = project / ".microcosm"
    state_dir.mkdir(parents=True)
    (state_dir / "routes.json").write_text(
        json.dumps(
            {
                "routes": [
                    {"route_id": "readme_onboarding_route", "title": "Readme"},
                    {"route_id": "docs_route", "title": "Docs"},
                    {"route_id": "test_behavior_route", "title": "Tests"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "patterns.json").write_text(
        json.dumps(
            {"patterns": [{"pattern_id": "repo_has_readme", "title": "Readme"}]}
        ),
        encoding="utf-8",
    )
    (state_dir / "work_items.json").write_text(
        json.dumps({"work_items": []}),
        encoding="utf-8",
    )
    standard_surface_calls = 0
    original_load_standard_surface = architecture_kernel.load_standard_pressure_surface

    def counted_load_standard_surface(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal standard_surface_calls
        standard_surface_calls += 1
        return original_load_standard_surface(*args, **kwargs)

    monkeypatch.setattr(
        architecture_kernel,
        "load_standard_pressure_surface",
        counted_load_standard_surface,
    )

    graph = architecture_kernel.build_graph(project)

    assert standard_surface_calls == 1
    assert graph["standard_pressure_surface"]["row_count"] >= 1
    assert any(edge["relation"] == "constrains" for edge in graph["edges"])


def test_observe_state_write_proof_counts_files_without_rglob(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "scratch_project"
    state_dir = project / ".microcosm"
    (state_dir / "nested").mkdir(parents=True)
    (state_dir / "routes.json").write_text("{}", encoding="utf-8")
    (state_dir / "work_items.json").write_text("{}", encoding="utf-8")
    (state_dir / "events.jsonl").write_text("{}\n", encoding="utf-8")
    (state_dir / "evidence").mkdir()
    (state_dir / "evidence" / "index.json").write_text("{}", encoding="utf-8")
    (state_dir / "graph.json").write_text("{}", encoding="utf-8")
    (state_dir / "state_index.json").write_text("{}", encoding="utf-8")
    (state_dir / "nested" / "extra.json").write_text("{}", encoding="utf-8")

    original_rglob = Path.rglob

    def fail_if_rglobbed(self: Path, *_args: object, **_kwargs: object) -> object:
        if self == state_dir:
            raise AssertionError("observe state-write proof should stream file counting")
        return original_rglob(self, *_args, **_kwargs)

    monkeypatch.setattr(Path, "rglob", fail_if_rglobbed)

    proof = project_substrate._project_observe_state_write_proof_card(project)

    assert proof["status"] == "pass"
    assert proof["state_file_count"] == 7
    assert proof["missing_state_refs"] == []


def test_route_explanation_entry_packet_matches_tour_card_causal_proof(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    route = entry_packet["route_explanation_chain_route"]

    tour_card = RuntimeShell(MICROCOSM_ROOT).tour_card(project)
    selected_route_id = str(tour_card["selected_route_id"])
    explanation = project_substrate.explain_route(project, selected_route_id)
    proof = explanation["causal_chain_proof"]

    assert route["full_proof_prerequisite_command"] == "plectis tour --card <project>"
    assert "causal_chain_proof" in route["expected_fields"]
    assert "selected-route work transaction" in route["full_proof_status_rule"]
    assert tour_card["state_write_result"]["status"] == "pass"
    assert tour_card["state_write_result"]["source_files_mutated"] is False
    assert selected_route_id == "readme_onboarding_route"
    assert proof["status"] == "pass"
    assert proof["selected_work_id"] == "work_0001"
    assert proof["selected_work_status"] == "closed"
    assert proof["event_ref_count"] >= 4
    assert proof["evidence_ref_count"] >= 4
    assert proof["source_files_mutated"] is False


def test_project_substrate_runs_on_user_owned_scratch_project(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    init_result = project_substrate.init_project(project)
    index_result = project_substrate.index_project(project)
    catalog = project_substrate.catalog_project(project)
    architecture = project_substrate.architecture_project(project)
    python_lens = project_substrate.python_lens(project)
    patterns = project_substrate.discover_patterns(project)
    routes = project_substrate.propose_routes(project)
    explanation = project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project)
    run = project_substrate.run_work(project, str(created["work_id"]))
    post_run_explanation = project_substrate.explain_route(project, "readme_onboarding_route")
    observed = project_substrate.observe_project(project)
    graph = project_substrate.state_graph(project)
    evidence = project_substrate.list_evidence(project)
    inspected = project_substrate.inspect_evidence(project, str(run["evidence_ref"]))
    compiled = project_substrate.compile_project(project)

    assert init_result["status"] == "pass"
    assert index_result["file_count"] == 4
    assert catalog["role_counts"]["readme"] == 1
    assert catalog["role_counts"]["package_manifest"] == 1
    assert catalog["role_counts"]["source"] == 1
    assert catalog["role_counts"]["test"] == 1
    assert architecture["kernel"]["posture"] == "executable_research_prototype"
    assert "route" in architecture["primitive_ids"]
    assert architecture["pattern_surface"]["state_ref"] == ".microcosm/patterns.json"
    assert python_lens["status"] == "pass"
    assert python_lens["schema_version"] == "microcosm_project_python_lens_v1"
    assert python_lens["lens_id"] == "project_python_route_lens"
    assert python_lens["command"] == "plectis python-lens <project>"
    assert python_lens["python_file_count"] == 2
    assert python_lens["passing_check_count"] == 4
    assert python_lens["missing_check_count"] == 1
    assert python_lens["ready_route_count"] == 3
    assert python_lens["package_roots"] == ["src/scratch_app"]
    assert python_lens["payload_boundary"]["boundary_id"] == "project_python_lens_read_model"
    assert python_lens["payload_boundary"]["source_open_default"] is True
    assert python_lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert python_lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert python_lens["safe_to_show"]["python_lens_rows_are_public_payload_boundary_rows"] is True
    assert python_lens["state_written"] is True
    assert python_lens["authority_ceiling"]["source_bodies_exported"] is False
    assert python_lens["source_span_count"] == 3
    assert python_lens["symbol_capsule_count"] == 1
    assert python_lens["graph_edge_count"] == 1
    assert python_lens["navigation_assay"]["assay_id"] == "std_python_microcosm_navigation_assay"
    assert python_lens["navigation_assay"]["canonical_depth_ladder"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert python_lens["navigation_assay"]["depth_band_coverage"] == {
        "module_docs": 0,
        "file_card": 2,
        "symbol_capsule": 1,
        "graph_context": 1,
        "source_span": 3,
    }
    assert python_lens["navigation_assay"]["probe_disposition_counts"] == {
        "file_local_defect": 0,
        "standard_amendment_candidate": 0,
        "nothing_to_refine": 4,
    }
    assert python_lens["navigation_assay"]["route_probe_tasks"][0]["expected_depth_band"] == "file_card"
    assert python_lens["navigation_assay"]["route_probe_tasks"][1]["expected_depth_band"] == "source_span"
    assert python_lens["navigation_assay"]["standard_amendment_candidate_count"] == 0
    assert python_lens["navigation_assay"]["parse_error_count"] == 0
    assert python_lens["navigation_assay"]["route_utility_task_count"] == 10
    assert python_lens["navigation_assay"]["route_utility_disposition_counts"] == {
        "local_projection_defect": 0,
        "local_source_or_test_defect": 0,
        "macro_standard_amendment_candidate": 0,
        "nothing_to_refine": 10,
    }
    assert (
        python_lens["navigation_assay"]["route_utility_ratchet_ref"]
        == ".microcosm/python_lens.json::route_utility_curriculum.ratchet"
    )
    assert python_lens["navigation_assay"]["route_utility_ratchet_status"] == (
        "curriculum_current"
    )
    assert python_lens["navigation_assay"]["route_utility_stale_task_count"] == 0
    assert python_lens["python_navigation_route"]["assay_ref"] == (
        ".microcosm/python_lens.json::navigation_assay"
    )
    assert python_lens["python_navigation_route"]["implementation_atlas_ref"] == (
        ".microcosm/python_lens.json::implementation_atlas.python_navigation_assay"
    )
    assert python_lens["python_navigation_route"]["route_utility_curriculum_ref"] == (
        ".microcosm/python_lens.json::route_utility_curriculum"
    )
    assert python_lens["python_navigation_route"]["route_utility_ratchet_ref"] == (
        ".microcosm/python_lens.json::route_utility_curriculum.ratchet"
    )
    assert python_lens["python_navigation_route"]["canonical_depth_ladder"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"]["assay_id"]
        == "std_python_microcosm_navigation_assay"
    )
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"]["source_span_count"]
        == 3
    )
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"]["source_bodies_exported"]
        is False
    )
    assert (
        python_lens["implementation_atlas"]["python_navigation_assay"][
            "route_utility_ratchet_status"
        ]
        == "curriculum_current"
    )
    route_curriculum = python_lens["route_utility_curriculum"]
    assert route_curriculum["curriculum_id"] == "microcosm_python_route_utility_curriculum"
    assert route_curriculum["task_count"] == 10
    assert route_curriculum["route_utility_metrics"]["failed_task_count"] == 0
    assert route_curriculum["route_utility_metrics"]["not_applicable_count"] == 1
    assert route_curriculum["disposition_counts"] == {
        "local_projection_defect": 0,
        "local_source_or_test_defect": 0,
        "macro_standard_amendment_candidate": 0,
        "nothing_to_refine": 10,
    }
    assert route_curriculum["payload_boundary_ok"] is True
    assert route_curriculum["source_bodies_exported"] is False
    assert route_curriculum["route_utility_metrics"]["stale_task_count"] == 0
    assert route_curriculum["ratchet"]["schema_version"] == (
        "microcosm_python_route_utility_ratchet_v1"
    )
    assert route_curriculum["ratchet"]["seed_task_count"] == 10
    assert route_curriculum["ratchet"]["generated_task_count"] == 0
    assert route_curriculum["ratchet"]["stale_task_ids"] == []
    assert route_curriculum["ratchet"]["last_run_result"] == "curriculum_current"
    task_by_id = {row["task_id"]: row for row in route_curriculum["tasks"]}
    assert (
        task_by_id["route_utility:entry_surface_to_python_assay"]["entry_surface_ref"]
        == "atlas/entry_packet.json::python_navigation_route"
    )
    assert (
        task_by_id["route_utility:test_behavior_source_span"]["expected_source_span"]
        == "tests/test_smoke.py::test_value"
    )
    assert task_by_id["route_utility:entrypoint_source_span"]["correctness"] == "not_applicable"
    assert task_by_id["route_utility:payload_boundary"]["source_bodies_exported"] is False
    test_span = next(
        row
        for row in python_lens["source_span_rows"]
        if row["span_id"] == "tests/test_smoke.py::test_value"
    )
    assert test_span["line_start"] == 4
    assert test_span["source_bodies_exported"] is False
    assert all(row["source_bodies_exported"] is False for row in python_lens["path_rows"])
    assert {row["route_id"]: row["readiness"] for row in python_lens["route_rows"]} == {
        "python_package_metadata_route": "pass",
        "python_source_core_route": "pass",
        "python_test_behavior_route": "pass",
        "python_entrypoint_route": "missing",
    }
    assert (project / ".microcosm/python_lens.json").is_file()
    assert (project / ".microcosm/evidence/python_lens.json").is_file()
    assert patterns["passing_pattern_count"] >= 4
    assert patterns["pattern_surface"]["surface_id"] == "public_microcosm_pattern_surface"
    pattern_ids = {row["pattern_id"] for row in patterns["patterns"]}
    assert all(row["standard_refs"] for row in patterns["patterns"])
    assert {row["route_id"] for row in routes["routes"]} >= {
        "readme_onboarding_route",
        "package_runtime_route",
        "source_core_route",
        "test_behavior_route",
    }
    assert all(set(row["pattern_refs"]).issubset(pattern_ids) for row in routes["routes"])
    assert explanation["status"] == "pass"
    assert explanation["route_id"] == "readme_onboarding_route"
    assert explanation["pattern_refs"] == ["repo_has_readme"]
    assert explanation["pattern_surface"]["state_ref"] == ".microcosm/patterns.json"
    assert explanation["pattern_bindings"][0]["pattern_id"] == "repo_has_readme"
    assert explanation["pattern_bindings"][0]["resolved"] is True
    assert explanation["standard_pressure_surface"]["surface_id"] == "public_microcosm_standard_pressure"
    assert "reversible_work_transaction" in explanation["standard_pressure_refs"]
    assert all(row["resolved"] is True for row in explanation["standard_bindings"])
    assert {
        row["standard_id"] for row in explanation["standard_bindings"]
    } >= {
        "json_contract_markdown_projection",
        "substrate_derived_projection",
        "projection_lineage_not_authority",
        "reversible_work_transaction",
        "evidence_as_black_box_recorder",
        "assimilation_without_promotion",
    }
    assert explanation["kernel_primitives"] == [
        "catalog",
        "pattern",
        "route",
        "work",
        "event",
        "evidence",
        "explanation",
    ]
    assert explanation["authority_boundary"] == "project_local_projection_not_source_authority"
    assert explanation["causal_chain_proof"]["status"] == "partial"
    assert created["work_id"] == "work_0001"
    assert run["transaction_status"] == "pass"
    assert run["state_machine"] == ["created", "selected", "planned", "executed_simulation", "closed"]
    causal_proof = post_run_explanation["causal_chain_proof"]
    assert causal_proof["status"] == "pass"
    assert causal_proof["proof_scope"] == (
        "project_local_state_lineage_not_correctness_authority"
    )
    assert causal_proof["route_id"] == "readme_onboarding_route"
    assert causal_proof["route_ref"] == ".microcosm/routes.json::readme_onboarding_route"
    assert causal_proof["pattern_binding_ids"] == ["repo_has_readme"]
    assert "reversible_work_transaction" in causal_proof["standard_binding_ids"]
    assert causal_proof["work_ids"] == ["work_0001"]
    assert causal_proof["selected_work_id"] == "work_0001"
    assert causal_proof["selected_work_status"] == "closed"
    assert causal_proof["state_history"] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]
    assert causal_proof["event_ref_count"] >= 4
    assert causal_proof["evidence_ref_count"] >= 4
    assert causal_proof["source_files_mutated"] is False
    assert ".microcosm/work_items.json" in causal_proof["reader_drilldowns"]
    assert ".microcosm/evidence/work_create_work_0001.json" in causal_proof["evidence_refs"]
    assert ".microcosm/evidence/work_run_work_0001.json" in causal_proof["evidence_refs"]
    # Occurrence vs declaration: exercised_primitives is derived from THIS run's
    # event spans, not the declared kernel_primitives literal. work runs, so work
    # is exercised; the event spans are drawn only from the route/explain/work set.
    assert causal_proof["exercised_event_spans"]
    assert set(causal_proof["exercised_event_spans"]).issubset(
        {"project.route", "project.explain", "work.create", "work.run"}
    )
    assert "work" in causal_proof["exercised_primitives"]
    # catalog/pattern are in the declared kernel_primitives list, but their spans
    # (project.index / project.patterns) never appear in a causal chain, so they
    # must NOT be reported as exercised — occurrence != declaration.
    assert "catalog" not in causal_proof["exercised_primitives"]
    assert "pattern" not in causal_proof["exercised_primitives"]
    # exercised is always a subset of the declared 10-primitive catalog.
    assert set(causal_proof["exercised_primitives"]).issubset(
        set(causal_proof["declared_kernel_primitives"])
    )
    assert len(causal_proof["declared_kernel_primitives"]) == 10
    assert causal_proof["authority_boundary"] == (
        "causal_chain_lineage_not_release_or_proof_correctness_authority"
    )
    rerun = project_substrate.run_work(project, str(created["work_id"]))
    assert rerun["transaction_status"] == "pass"
    assert rerun["idempotent_replay"] is True
    work_payload = json.loads((project / ".microcosm/work_items.json").read_text(encoding="utf-8"))
    work_row = work_payload["work_items"][0]
    assert work_row["satisfaction_contract"]["contract_id"] == "satisfaction:readme_onboarding_route"
    assert work_row["integration_contract"]["integration_mode"] == "project_local_record_only"
    assert work_row["closeout"]["satisfaction_contract_met"] is True
    assert work_row["closeout"]["integration_contract_met"] is True
    assert [row["state"] for row in work_row["state_history"]] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]
    assert work_row["event_refs"]
    assert work_row["evidence_refs"]
    assert observed["event_count"] >= 6
    assert observed["architecture_ref"] == ".microcosm/architecture.json"
    assert observed["selected_route_id"] == "readme_onboarding_route"
    assert observed["causal_chain"]["status"] == "pass"
    assert observed["causal_chain"]["selected_route_id"] == "readme_onboarding_route"
    assert observed["causal_chain"]["selected_work_id"] == "work_0001"
    assert observed["causal_chain"]["work_state_ref"] == (
        ".microcosm/work_items.json::work_0001"
    )
    assert observed["causal_chain"]["event_log_ref"] == ".microcosm/events.jsonl"
    assert observed["causal_chain"]["graph"]["graph_ref"] == ".microcosm/graph.json"
    assert ".microcosm/evidence/" in observed["reader_drilldowns"]
    assert observed["safe_to_show"]["provider_calls_authorized"] is False
    assert observed["safe_to_show"]["source_files_mutated"] is False
    assert graph["edge_count"] >= 7
    assert {node["node_id"] for node in graph["nodes"]} >= {
        "pattern_surface",
        "standard:std_microcosm_pattern",
        "standard:std_microcosm_pattern_binding_contract",
        "standard_pressure_surface",
        "standard_pressure:reversible_work_transaction",
        "truth_readiness_surface",
    }
    assert any(edge["relation"] == "resolves_pattern_refs_against" for edge in graph["edges"])
    assert any(edge["relation"] == "resolves_standard_pressure_against" for edge in graph["edges"])
    assert evidence["evidence_count"] >= 6
    assert inspected["status"] == "pass"
    assert inspected["payload_boundary_ref"] == "project_python_lens_read_model"
    assert inspected["source_bodies_exported"] is False
    assert inspected["payload_summary"]["inspect_card_policy"] == (
        "safe_shape_and_refs_no_source_bodies"
    )
    assert inspected["payload_summary"]["object_field_key_counts"]["work_item"] >= 10
    assert inspected["payload_summary"]["work_item_summary"]["state_history"] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]
    assert compiled["status"] == "pass"
    assert compiled["headline"] == "repo -> .microcosm"
    assert compiled["selected_route_id"] == "readme_onboarding_route"
    assert compiled["python_lens_ref"] == ".microcosm/python_lens.json"
    assert compiled["python_navigation_assay_ref"] == ".microcosm/python_lens.json::navigation_assay"
    assert compiled["python_file_count"] == 2
    assert compiled["python_ready_route_count"] == 3
    assert compiled["python_source_span_count"] == 3
    assert compiled["python_navigation_assay"]["assay_id"] == "std_python_microcosm_navigation_assay"
    assert compiled["python_navigation_assay"]["route_utility_task_count"] == 10
    assert compiled["python_navigation_assay"]["route_utility_stale_task_count"] == 0
    assert (
        compiled["implementation_atlas"]["python_navigation_assay"]["assay_ref"]
        == ".microcosm/python_lens.json::navigation_assay"
    )
    assert compiled["route_utility_curriculum"]["task_count"] == 10
    assert (
        compiled["route_utility_curriculum"]["ratchet"]["last_run_result"]
        == "curriculum_current"
    )
    assert compiled["python_navigation_route"]["surface_id"] == "project_python_lens"
    assert compiled["work_id"] == "work_0001"
    assert compiled["idempotent_replay"] is True
    assert compiled["source_files_mutated"] is False
    reader_case = compiled["reader_causal_chain"]["command_reference_execution_case"]
    assert reader_case["status"] == "pass"
    assert reader_case["verification_status"] == "pass"
    assert reader_case["verification_failed_predicates"] == []
    assert reader_case["predicate_status"]["projection_fidelity"] is True
    assert reader_case["public_architecture_witness_eligible"] is True
    assert reader_case["public_witness_status"] == "pass"
    assert reader_case["producer_claimed_public_architecture_witness_eligible"] is False
    assert reader_case["verification_predicate_status"]["rendered_eligibility_flags"] is True
    assert "plectis serve <project>" in compiled["open_observatory"]
    assert compiled["bounded_observatory_validation"] == (
        "plectis serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    truth_surface = compiled["truth_readiness_surface"]
    assert compiled["truth_readiness_ref"] == ".microcosm/truth_readiness.json"
    assert truth_surface["surface_id"] == "public_microcosm_truth_readiness"
    assert truth_surface["status"] == "pass"
    assert truth_surface["readiness_posture"] == (
        "local_first_executable_research_prototype_ready_for_human_inspection"
    )
    assert truth_surface["truth_accounting"] == {
        "project_local_state_refs_complete": True,
        "route_selected": True,
        "route_explanation_available": True,
        "work_transaction_closed": True,
        "event_stream_present": True,
        "evidence_refs_present": True,
        "graph_present": True,
        "observatory_surface_available": True,
        "source_files_mutated": False,
        "release_authorized": False,
    }
    assert truth_surface["observatory_surface"]["compact_endpoint"] == (
        "/project/observatory-card"
    )
    assert truth_surface["observatory_surface"]["project_observe_command"] == (
        "plectis observe --card <project>"
    )
    assert truth_surface["observatory_surface"]["project_observe_full_command"] == (
        "plectis observe <project>"
    )
    assert truth_surface["authority_ceiling"]["release_authorized"] is False
    reader_chain = compiled["reader_causal_chain"]
    assert reader_chain["status"] == "pass"
    assert reader_chain["selected_route_id"] == "readme_onboarding_route"
    assert reader_chain["selected_route_ref"] == (
        ".microcosm/routes.json::readme_onboarding_route"
    )
    assert reader_chain["selected_work_id"] == "work_0001"
    assert reader_chain["selected_work_status"] == "closed"
    assert reader_chain["work_state_ref"] == ".microcosm/work_items.json::work_0001"
    assert reader_chain["event_log_ref"] == ".microcosm/events.jsonl"
    assert reader_chain["graph"]["graph_ref"] == ".microcosm/graph.json"
    assert reader_chain["observatory"]["compact_endpoint"] == "/project/observatory-card"
    assert reader_chain["observatory"]["expanded_endpoint"] == "/project/observatory"
    assert reader_chain["observatory"]["bounded_validation_command"] == (
        "plectis serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert reader_chain["observatory"]["bounded_validation_request_count"] == 7
    assert reader_chain["proof_lab"]["endpoint"] == "/proof-lab"
    assert ".microcosm/evidence/work_create_work_0001.json" in reader_chain["evidence_refs"]
    assert ".microcosm/evidence/work_run_work_0001.json" in reader_chain["evidence_refs"]
    assert ".microcosm/work_items.json" in reader_chain["reader_drilldowns"]
    assert ".microcosm/graph.json" in reader_chain["reader_drilldowns"]
    assert reader_chain["receipts_are_drilldown_evidence"] is True
    assert reader_chain["safe_to_show"]["provider_calls_authorized"] is False
    assert reader_chain["safe_to_show"]["proof_correctness_claim"] is False

    state_files = {
        ".microcosm/project_manifest.json",
        ".microcosm/architecture.json",
        ".microcosm/state_index.json",
        ".microcosm/graph.json",
        ".microcosm/catalog.json",
        ".microcosm/python_lens.json",
        ".microcosm/patterns.json",
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/truth_readiness.json",
        ".microcosm/events.jsonl",
        ".microcosm/explanations/readme_onboarding_route.json",
    }
    for rel in state_files:
        assert (project / rel).is_file()
    saved_explanation = json.loads(
        (project / ".microcosm/explanations/readme_onboarding_route.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved_explanation["causal_chain_proof"]["selected_work_id"] == "work_0001"

    state_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted((project / ".microcosm").rglob("*.json")))
    assert tmp_path.as_posix() not in state_text
    assert "/Users/" not in state_text


def test_python_lens_counts_pyproject_console_scripts_as_entrypoints(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    (project / "pyproject.toml").write_text(
        "[project]\n"
        "name = \"scratch-project\"\n"
        "version = \"0.1.0\"\n\n"
        "[project.scripts]\n"
        "scratch = \"scratch_app.cli:main\"\n",
        encoding="utf-8",
    )
    (project / "src/scratch_app/cli.py").write_text(
        "def main() -> int:\n"
        "    return 0\n",
        encoding="utf-8",
    )

    python_lens = project_substrate.python_lens(project, write_state=False)
    check_by_id = {row["check_id"]: row for row in python_lens["readiness_checks"]}
    route_by_id = {row["route_id"]: row for row in python_lens["route_rows"]}
    task_by_id = {
        row["task_id"]: row
        for row in python_lens["route_utility_curriculum"]["tasks"]
    }

    assert check_by_id["python_entrypoint_visible"] == {
        "check_id": "python_entrypoint_visible",
        "status": "pass",
        "grounded_refs": [
            "src/scratch_app/cli.py",
            "pyproject.toml::project.scripts.scratch",
        ],
    }
    assert python_lens["console_entrypoint_count"] == 1
    assert python_lens["console_entrypoint_source_refs"] == ["src/scratch_app/cli.py"]
    assert python_lens["console_entrypoint_rows"][0]["target_ref"] == (
        "src/scratch_app/cli.py"
    )
    assert python_lens["console_entrypoint_rows"][0]["source_bodies_exported"] is False
    assert route_by_id["python_entrypoint_route"]["readiness"] == "pass"
    assert route_by_id["python_entrypoint_route"]["grounded_refs"] == [
        "src/scratch_app/cli.py",
        "pyproject.toml::project.scripts.scratch",
    ]
    assert python_lens["missing_check_count"] == 0
    assert python_lens["ready_route_count"] == 4
    assert task_by_id["route_utility:entrypoint_source_span"]["correctness"] == "pass"
    assert task_by_id["route_utility:entrypoint_source_span"]["expected_file_card"] == (
        "src/scratch_app/cli.py"
    )
    assert task_by_id["route_utility:entrypoint_source_span"]["expected_source_span"] == (
        "src/scratch_app/cli.py::main"
    )


def test_compile_project_runs_work_for_selected_readme_route_when_old_work_exists(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)

    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    old = project_substrate.create_work(project, "test_behavior_route")
    project_substrate.run_work(project, str(old["work_id"]))

    compiled = project_substrate.compile_project(project)
    explanation = project_substrate.explain_route(project, "readme_onboarding_route")
    proof = explanation["causal_chain_proof"]
    work_payload = json.loads(
        (project / ".microcosm/work_items.json").read_text(encoding="utf-8")
    )
    rows_by_route = {
        row["route_id"]: row
        for row in work_payload["work_items"]
        if isinstance(row, dict)
    }

    assert compiled["selected_route_id"] == "readme_onboarding_route"
    assert compiled["work_id"] == rows_by_route["readme_onboarding_route"]["work_id"]
    assert compiled["reader_causal_chain"]["status"] == "pass"
    assert compiled["reader_causal_chain"]["selected_route_id"] == (
        "readme_onboarding_route"
    )
    assert compiled["reader_causal_chain"]["selected_work_id"] == (
        rows_by_route["readme_onboarding_route"]["work_id"]
    )
    assert compiled["reader_causal_chain"]["work_state_ref"] == (
        ".microcosm/work_items.json::"
        f"{rows_by_route['readme_onboarding_route']['work_id']}"
    )
    assert proof["status"] == "pass"
    assert proof["selected_work_status"] == "closed"
    assert rows_by_route["test_behavior_route"]["status"] == "closed"
    assert rows_by_route["readme_onboarding_route"]["status"] == "closed"


def test_python_lens_can_emit_navigation_assay_without_writing_state(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    python_lens = project_substrate.python_lens(project, write_state=False)

    assert python_lens["status"] == "pass"
    assert python_lens["state_written"] is False
    assert python_lens["evidence_ref"] is None
    assert python_lens["event_id"] is None
    assert python_lens["navigation_assay"]["assay_id"] == "std_python_microcosm_navigation_assay"
    assert python_lens["navigation_assay"]["probe_disposition_counts"] == {
        "file_local_defect": 0,
        "standard_amendment_candidate": 0,
        "nothing_to_refine": 4,
    }
    assert python_lens["route_utility_curriculum"]["task_count"] == 10
    assert python_lens["route_utility_curriculum"]["state_written"] is False
    assert python_lens["route_utility_curriculum"]["source_bodies_exported"] is False
    assert python_lens["route_utility_curriculum"]["ratchet"]["last_run_result"] == (
        "nothing_to_refine"
    )
    assert python_lens["route_utility_curriculum"]["ratchet"]["state_freshness"] == (
        "no_written_state"
    )
    assert python_lens["source_span_count"] == 3
    assert not (project / ".microcosm").exists()


def test_python_lens_route_utility_ratchet_marks_changed_surface_without_writing(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    project_substrate.python_lens(project)
    state_path = project / ".microcosm/python_lens.json"
    test_path = project / "tests/test_smoke.py"
    future = state_path.stat().st_mtime + 10
    test_path.write_text(
        "from scratch_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n\n",
        encoding="utf-8",
    )
    os.utime(test_path, (future, future))

    python_lens = project_substrate.python_lens(project, write_state=False)
    ratchet = python_lens["route_utility_curriculum"]["ratchet"]

    assert python_lens["state_written"] is False
    assert ratchet["last_run_result"] == "curriculum_stale_for_changed_surface"
    assert ratchet["changed_surface_refs"] == ["tests/test_smoke.py"]
    assert "route_utility:test_behavior_source_span" in ratchet["affected_task_ids"]
    assert "route_utility:payload_boundary" in ratchet["affected_task_ids"]
    assert sorted(ratchet["stale_task_ids"]) == sorted(ratchet["affected_task_ids"])
    assert ratchet["generated_task_count"] == len(ratchet["affected_task_ids"])
    assert python_lens["navigation_assay"]["route_utility_ratchet_status"] == (
        "curriculum_stale_for_changed_surface"
    )
    assert python_lens["navigation_assay"]["route_utility_stale_task_count"] == len(
        ratchet["stale_task_ids"]
    )
    assert (project / ".microcosm/python_lens.json").is_file()


def test_python_lens_route_utility_ratchet_ignores_unwatched_surface(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    project_substrate.python_lens(project)
    state_path = project / ".microcosm/python_lens.json"
    note_path = project / "notes/operator_note.md"
    note_path.parent.mkdir()
    future = state_path.stat().st_mtime + 10
    note_path.write_text(
        "This note is outside the Python route utility surfaces.\n",
        encoding="utf-8",
    )
    os.utime(note_path, (future, future))

    python_lens = project_substrate.python_lens(project, write_state=False)
    ratchet = python_lens["route_utility_curriculum"]["ratchet"]

    assert python_lens["state_written"] is False
    assert ratchet["state_freshness"] == "compared_to_written_state"
    assert ratchet["last_run_result"] == "nothing_to_refine"
    assert ratchet["changed_surface_refs"] == []
    assert ratchet["affected_task_ids"] == []
    assert ratchet["stale_task_ids"] == []
    assert ratchet["generated_task_count"] == 0
    assert python_lens["route_utility_curriculum"]["route_utility_metrics"][
        "stale_task_count"
    ] == 0
    assert python_lens["route_utility_curriculum"]["source_bodies_exported"] is False
    assert (project / ".microcosm/python_lens.json").is_file()


def test_python_lens_route_utility_ratchet_skips_unreadable_surface_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = _scratch_project(tmp_path)
    project_substrate.python_lens(project)
    test_path = project / "tests/test_smoke.py"
    original_mtime_ns = project_substrate._path_mtime_ns

    def guarded_mtime_ns(path: Path) -> int | None:
        if path == test_path:
            return None
        return original_mtime_ns(path)

    monkeypatch.setattr(project_substrate, "_path_mtime_ns", guarded_mtime_ns)

    python_lens = project_substrate.python_lens(project, write_state=False)
    ratchet = python_lens["route_utility_curriculum"]["ratchet"]

    assert python_lens["state_written"] is False
    assert ratchet["state_freshness"] == "compared_to_written_state"
    assert ratchet["last_run_result"] == "nothing_to_refine"
    assert ratchet["changed_surface_refs"] == []
    assert ratchet["unreadable_surface_count"] == 1
    assert ratchet["affected_task_ids"] == []
    assert ratchet["stale_task_ids"] == []


def test_python_lens_route_utility_ratchet_handles_unreadable_state_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = _scratch_project(tmp_path)
    project_substrate.python_lens(project)
    state_path = project / ".microcosm/python_lens.json"
    original_mtime_ns = project_substrate._path_mtime_ns

    def guarded_mtime_ns(path: Path) -> int | None:
        if path == state_path:
            return None
        return original_mtime_ns(path)

    monkeypatch.setattr(project_substrate, "_path_mtime_ns", guarded_mtime_ns)

    python_lens = project_substrate.python_lens(project, write_state=False)
    ratchet = python_lens["route_utility_curriculum"]["ratchet"]

    assert python_lens["state_written"] is False
    assert ratchet["state_freshness"] == "unreadable_written_state"
    assert ratchet["last_run_result"] == "nothing_to_refine"
    assert ratchet["changed_surface_refs"] == []
    assert ratchet["affected_task_ids"] == []
    assert ratchet["stale_task_ids"] == []
    assert "python_lens state metadata can be read" in ratchet["next_reentry_condition"]


def test_cli_python_lens_defaults_to_compact_card_and_full_keeps_rows(
    capsys, tmp_path: Path
) -> None:
    project = _scratch_project(tmp_path)

    assert cli.main(["python-lens", project.as_posix()]) == 0
    card = json.loads(capsys.readouterr().out)

    assert card["schema_version"] == "microcosm_project_python_lens_card_v1"
    assert card["command"] == "plectis python-lens <project>"
    assert card["full_lens_command"] == "plectis python-lens --full <project>"
    assert card["deferred_full_scan"] is True
    assert card["python_file_count"] == 2
    assert card["path_preview_limit"] == project_substrate.PYTHON_LENS_CARD_PREVIEW_LIMIT
    assert card["payload_boundary"]["boundary_id"] == "project_python_lens_read_model"
    assert card["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert card["safe_to_show"]["full_source_span_graph_deferred"] is True
    assert "source_span_rows" not in card
    assert "symbol_capsule_rows" not in card
    assert "graph_context_edges" not in card
    assert len(json.dumps(card, sort_keys=True)) < 16000

    assert cli.main(["python-lens", "--full", project.as_posix()]) == 0
    full = json.loads(capsys.readouterr().out)

    assert full["schema_version"] == "microcosm_project_python_lens_v1"
    assert full["full_lens_command"] == "plectis python-lens --full <project>"
    assert full["source_span_count"] == 3
    assert full["symbol_capsule_count"] == 1
    assert full["graph_edge_count"] == 1
    assert full["source_span_rows"]
    assert full["symbol_capsule_rows"]
    assert full["graph_context_edges"]


def test_cli_project_first_run_commands(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)

    for argv in [
        ["init", project.as_posix()],
        ["index", project.as_posix()],
        ["catalog", project.as_posix()],
        ["architecture", project.as_posix()],
        ["compile", project.as_posix()],
        ["python-lens", project.as_posix()],
        ["patterns", project.as_posix()],
        ["route", project.as_posix()],
        ["explain", project.as_posix(), "readme_onboarding_route"],
        ["graph", project.as_posix()],
        ["work", "create", project.as_posix()],
        ["work", "run", project.as_posix()],
        ["observe", project.as_posix()],
        ["evidence", "list", project.as_posix()],
    ]:
        assert cli.main(argv) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "pass"
        if argv[0] == "explain":
            assert payload["causal_chain_proof"]["status"] == "pass"
            assert payload["causal_chain_proof"]["selected_work_id"] == "work_0001"
            assert payload["causal_chain_proof"]["event_ref_count"] >= 4


def test_exercised_primitives_are_occurrence_not_declaration() -> None:
    """exercised_primitives is derived from a run's event spans, not the declared catalog.

    Guards the occurrence-vs-declaration trap: the explanation's hardcoded
    ``kernel_primitives`` list (and the kernel's 10-primitive catalog) are
    DECLARATION; ``exercised_primitives`` must reflect only the spans that
    actually fired. A drift-immune unit test of the helper directly, so it does
    not depend on CLI command-name state elsewhere in the tree.
    """
    from microcosm_core.architecture_kernel import (
        _exercised_primitives_from_event_refs,
        load_kernel_manifest,
    )

    manifest = load_kernel_manifest()
    declared = {
        row["primitive_id"]
        for row in manifest["primitives"]
        if isinstance(row, dict) and row.get("primitive_id")
    }
    refs = [
        {"event_id": "evt_1", "span": "project.route", "status": "pass"},
        {"event_id": "evt_2", "span": "project.explain", "status": "pass"},
        {"event_id": "evt_3", "span": "work.create", "status": "pass"},
        {"event_id": "evt_4", "span": "work.run", "status": "pass"},
    ]
    spans, exercised = _exercised_primitives_from_event_refs(refs, manifest)

    assert spans == ["project.explain", "project.route", "work.create", "work.run"]
    # occurrence: derived from the spans that fired
    assert {"route", "explanation", "work", "assimilation"}.issubset(set(exercised))
    # declaration leakage guard: primitives whose spans never fired are excluded
    for absent in ("catalog", "pattern", "standard", "project"):
        assert absent not in exercised
    # the glob-span primitive ("event": "project.* / work.*") is never auto-marked
    assert "event" not in exercised
    # exercised is always a subset of the declared catalog
    assert set(exercised).issubset(declared)
    # empty run -> empty occurrence
    assert _exercised_primitives_from_event_refs([], manifest) == ([], [])


def test_execution_instance_is_single_invocation_scoped() -> None:
    """The execution_instance partition is one work transaction, not the route neighbourhood.

    Disconfirming check: a second, interleaved run of the same route must not be able
    to enter the selected execution's partition. Correlation closure comes from the
    selected work's own work_id-correlated event_refs/evidence_refs, not proximity.
    """
    from microcosm_core.architecture_kernel import (
        _execution_instance,
        load_kernel_manifest,
    )

    manifest = load_kernel_manifest()
    selected = {
        "work_id": "work_0001",
        "status": "closed",
        "event_refs": [
            {"event_id": "evt_0008", "span": "work.create", "status": "pass"},
            {"event_id": "evt_0009", "span": "work.run", "status": "pass"},
        ],
        "evidence_refs": [
            ".microcosm/evidence/work_create_work_0001.json",
            ".microcosm/evidence/work_run_work_0001.json",
        ],
    }
    # A DIFFERENT, interleaved run of the same route — its records must stay out.
    _other = {
        "work_id": "work_0002",
        "status": "closed",
        "event_refs": [
            {"event_id": "evt_0068", "span": "work.create", "status": "pass"},
        ],
        "evidence_refs": [".microcosm/evidence/work_create_work_0002.json"],
    }
    inst = _execution_instance(
        selected, "readme_onboarding_route", ["created", "closed"], manifest
    )
    event_ids = {row["event_id"] for row in inst["event_refs"]}
    assert event_ids == {"evt_0008", "evt_0009"}
    # the interleaved run cannot leak in
    assert "evt_0068" not in event_ids
    assert all("work_0002" not in ref for ref in inst["evidence_refs"])
    assert inst["selected_work_id"] == "work_0001"
    assert inst["single_execution_scoped"] is True
    assert inst["correlation_status"] == "work_correlated"
    # selection is honestly labeled as representative, NOT causal invocation binding
    assert inst["selection_basis"] == (
        "representative_first_closed_work_not_causal_invocation"
    )
    # exercised reflects only this execution's spans (create + run)
    assert inst["exercised_primitives"] == ["assimilation", "work"]
    # an absent selected work yields an empty partition that does NOT self-certify
    empty = _execution_instance(None, "readme_onboarding_route", [], manifest)
    assert empty["event_refs"] == []
    assert empty["exercised_primitives"] == []
    assert empty["single_execution_scoped"] is False
    assert empty["correlation_status"] == "no_selected_work"


def test_reference_execution_case_binds_returned_work_id_not_first_closed(
    tmp_path: Path,
) -> None:
    """Command-root witness binds the returned work_id, not historical route order."""
    project = _scratch_project(tmp_path)
    route_id = "readme_onboarding_route"

    project_substrate.propose_routes(project)
    older = project_substrate.create_work(project, route_id)
    project_substrate.run_work(project, str(older["work_id"]))
    explanation = project_substrate.explain_route(project, route_id)

    before_second = architecture_kernel.command_state_snapshot(project)
    newer = project_substrate.create_work(project, route_id)
    run = project_substrate.run_work(project, str(newer["work_id"]))
    assert run["work_id"] == "work_0002"
    assert run["reference_execution_case"]["root_binding"]["work_id"] == "work_0002"
    assert run["reference_execution_case"]["command_case_eligible"] is True
    run_case_delta = run["reference_execution_case"]["state_delta"]
    assert run_case_delta["status"] == "available"
    assert run_case_delta["new_work_ids"] == []
    assert len(run_case_delta["new_event_ids"]) == 1
    assert run_case_delta["new_evidence_refs"] == [
        ".microcosm/evidence/work_run_work_0002.json"
    ]
    assert run["reference_execution_case_ref"] == (
        ".microcosm/evidence/reference_execution_case_work_0002.json"
    )
    assert (
        project / ".microcosm/evidence/reference_execution_case_work_0002.json"
    ).is_file()
    persisted_run_case = json.loads(
        (project / ".microcosm/evidence/reference_execution_case_work_0002.json")
        .read_text(encoding="utf-8")
    )
    assert persisted_run_case["state_delta"] == run_case_delta
    rerun = project_substrate.run_work(project, str(newer["work_id"]))
    assert rerun["transaction_status"] == "pass"
    assert rerun["idempotent_replay"] is True
    rerun_case = rerun["reference_execution_case"]
    assert rerun_case["command_kind"] == "work.run.idempotent_replay"
    assert rerun_case["state_delta"] == {
        "status": "available",
        "new_work_ids": [],
        "new_event_ids": [],
        "new_evidence_refs": [],
    }
    assert rerun_case["predicate_status"]["replay_equivalence"] is False
    assert rerun_case["command_case_eligible"] is False
    rerun_case_verification = architecture_kernel.verify_reference_execution_case(
        project,
        rerun_case,
    )
    assert rerun_case_verification["status"] == "blocked"
    assert "replay_equivalence" in rerun_case_verification["failed_predicates"]
    assert rerun_case_verification["predicate_details"]["replay_equivalence_basis"] == (
        "available_delta_missing_root_or_descendant_or_current_state_ref"
    )

    # The existing route explanation still uses the representative first-closed
    # selector; the command-root case must not inherit that historical selection.
    assert explanation["causal_chain_proof"]["selected_work_id"] == "work_0001"

    case = architecture_kernel.build_reference_execution_case(
        project,
        route_id,
        run,
        command_kind="work.create+work.run",
        before_state=before_second,
    )
    reference_predicates = {
        "join_integrity",
        "selection_binding",
        "scope_completeness",
        "execution_terminality",
        "authority_boundedness",
        "replay_equivalence",
        "state_delta_scope",
        "record_classification_matrix",
        "assertion_matrix_coverage",
        "projection_fidelity",
    }

    assert case["root_binding"]["binding_kind"] == "command_returned_work_id"
    assert case["root_binding"]["work_id"] == "work_0002"
    assert case["command_case_eligible"] is True
    assert case["public_architecture_witness_eligible"] is False
    assert case["predicate_status"] == {
        "join_integrity": True,
        "selection_binding": True,
        "scope_completeness": True,
        "execution_terminality": True,
        "authority_boundedness": True,
        "replay_equivalence": True,
        "state_delta_scope": True,
        "record_classification_matrix": True,
        "assertion_matrix_coverage": True,
        "projection_fidelity": False,
    }
    assert set(case["predicate_status"]) == reference_predicates
    assert case["required_assertion_predicates"] == (
        architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES
    )
    assert {
        row["eligibility_predicate"] for row in case["assertion_matrix"]
    } == set(architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES)
    assert case["predicate_details"]["projection_selected_work_id"] == "work_0001"
    assert case["state_delta"]["new_work_ids"] == ["work_0002"]
    assert architecture_kernel.reference_state_delta_refs(case["state_delta"])[0] == (
        ".microcosm/work_items.json::work_0002"
    )
    assert all(
        ref.startswith(".microcosm/evidence/")
        for ref in case["state_delta"]["new_evidence_refs"]
    )
    assert set(case["ambient_history_excluded"]["work_ids"]) == {"work_0001"}
    ambient_history_count = len(case["ambient_history_excluded"]["work_ids"]) + len(
        case["ambient_history_excluded"]["event_ids"]
    )
    assert len(case["ambient_history_excluded"]["records"]) == ambient_history_count
    assert {
        row["classification"] for row in case["ambient_history_excluded"]["records"]
    } == {"ambient_history"}
    assert all(
        row["included_in_occurrence_witness"] is False
        for row in case["ambient_history_excluded"]["records"]
    )
    work_payload = json.loads(
        (project / ".microcosm/work_items.json").read_text(encoding="utf-8")
    )
    work_0002 = next(
        row for row in work_payload["work_items"] if row["work_id"] == "work_0002"
    )
    assert work_0002["reference_execution_case_ref"] == (
        ".microcosm/evidence/reference_execution_case_work_0002.json"
    )
    assert work_0002["reference_execution_case_ref"] not in work_0002["evidence_refs"]
    classification_counts = case["record_classification_counts"]
    assert classification_counts["direct_child"] == 2
    assert classification_counts["causal_descendant"] == (
        len(work_0002["event_refs"]) + len(work_0002["evidence_refs"]) - 1
    )
    assert classification_counts["structural_lookup"] == 1
    assert classification_counts["structural_constitutional_lookup"] == 1
    assert classification_counts["ambient_history"] == ambient_history_count
    assert len(case["record_classification_matrix"]) == sum(
        classification_counts.values()
    )

    compiled = project_substrate.compile_project(project)
    reader_case = compiled["reader_causal_chain"]["command_reference_execution_case"]
    expected_card_state_delta_refs = architecture_kernel.reference_state_delta_refs(
        persisted_run_case["state_delta"]
    )
    assert reader_case["status"] == "pass"
    assert reader_case["selected_work_id"] == "work_0002"
    assert reader_case["root_work_id"] == "work_0002"
    assert reader_case["state_delta_refs"] == expected_card_state_delta_refs
    assert reader_case["command_case_eligible"] is True
    assert reader_case["public_architecture_witness_eligible"] is False
    assert reader_case["public_witness_status"] == "projection_not_eligible"
    assert reader_case["predicate_status"]["projection_fidelity"] is False
    assert reader_case["verification_status"] == "pass"
    assert reader_case["verification_failed_predicates"] == []
    assert set(reference_predicates).issubset(
        reader_case["verification_predicate_status"]
    )
    assert {
        key: reader_case["verification_predicate_status"][key]
        for key in reference_predicates
    } == {
        "join_integrity": True,
        "selection_binding": True,
        "scope_completeness": True,
        "execution_terminality": True,
        "authority_boundedness": True,
        "replay_equivalence": True,
        "state_delta_scope": True,
        "record_classification_matrix": True,
        "assertion_matrix_coverage": True,
        "projection_fidelity": False,
    }
    assert reader_case["required_assertion_predicates"] == (
        architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES
    )
    assert set(reader_case["assertion_matrix_predicates"]) == set(
        architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES
    )
    assert reader_case["assertion_matrix_predicate_count"] == len(
        architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES
    )
    assert reader_case["required_assertion_predicate_count"] == len(
        architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES
    )
    assert reader_case["assertion_matrix_coverage_verified"] is True
    assert reader_case["record_classification_matrix_verified"] is True
    assert reader_case["record_classification_counts"] == classification_counts
    assert reader_case["ambient_history_ref_count"] == ambient_history_count
    assert reader_case["record_classification_matrix_ref"] == (
        ".microcosm/evidence/reference_execution_case_work_0002.json"
        "::record_classification_matrix"
    )
    assert reader_case["verification_predicate_status"][
        "truth_class_authority"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_occurrence_refs"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_state_delta_refs"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_state_delta_summary"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_predicate_details"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_predicate_status"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_semantic_digest"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_truth_class_authority"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_truth_class_summary"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_record_classification_summary"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_root_binding"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_eligibility_flags"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_verification_summary"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_safe_to_show_boundary"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_guidance_boundary"
    ] is True
    assert reader_case["verification_predicate_status"][
        "rendered_late_predicate_status"
    ] is True
    assert set(reader_case["truth_classes"]) == {
        "constitution",
        "occurrence",
        "projection",
        "structure",
    }
    assert (
        ".microcosm/evidence/reference_execution_case_work_0002.json"
        in compiled["reader_causal_chain"]["reader_drilldowns"]
    )
    assert (
        ".microcosm/evidence/reference_execution_case_work_0002.json"
        not in compiled["reader_causal_chain"]["evidence_refs"]
    )

    observe_card = project_substrate.observe_project_card(project)
    observe_case_summary = observe_card["causal_chain_summary"][
        "command_reference_execution_case"
    ]
    assert observe_case_summary["state_delta_ref_count"] == len(
        expected_card_state_delta_refs
    )
    assert observe_case_summary["state_delta_refs_verified"] is True
    assert observe_case_summary["state_delta_scope_verified"] is True
    assert observe_case_summary["state_delta_refs_ref"] == (
        "command_reference_execution_case.state_delta_refs"
    )
    assert observe_case_summary["state_delta_scope_ref"] == (
        "verification_predicate_status.state_delta_scope"
    )
    assert observe_case_summary["assertion_matrix_coverage_verified"] is True
    assert observe_case_summary["assertion_matrix_coverage_ref"] == (
        "verification_predicate_status.assertion_matrix_coverage"
    )
    assert observe_case_summary["record_classification_matrix_verified"] is True
    assert observe_case_summary["record_classification_matrix_ref"] == (
        "verification_predicate_status.record_classification_matrix"
    )
    assert observe_card["causal_chain_summary"][
        "agent_harness_record_review_status"
    ] == "selected_work_record_reviewable_observe_handoff"
    assert observe_card["causal_chain_summary"][
        "agent_harness_record_review_ref"
    ] == "agent_harness_record_review"
    observe_harness_review = observe_card["agent_harness_record_review"]
    assert (
        observe_harness_review["schema_version"]
        == "microcosm_observe_agent_harness_record_review_cue_v1"
    )
    assert observe_harness_review["status"] == (
        "selected_work_record_reviewable_observe_handoff"
    )
    assert observe_harness_review["selected_work_id"] == "work_0002"
    assert observe_harness_review["root_work_id"] == "work_0002"
    assert observe_harness_review["root_matches_selected"] is True
    assert observe_harness_review["selected_work_reference_case_status"] == "pass"
    assert (
        observe_harness_review["selected_work_reference_verification_status"]
        == "pass"
    )
    observe_review_axes = {
        row["axis"]: row for row in observe_harness_review["review_axes"]
    }
    assert observe_review_axes["trajectory"]["status"] == "present"
    assert observe_review_axes["reproducibility_fixture"]["status"] == "present"
    assert observe_review_axes["reproducibility_fixture"][
        "state_delta_ref_count"
    ] == len(expected_card_state_delta_refs)
    assert observe_review_axes["task_boundary"]["status"] == "present"
    assert observe_review_axes["benchmark_anti_claim"]["drilldown_command"] == (
        "plectis comprehend --slice claims --organ "
        "agent_benchmark_integrity_anti_gaming_replay"
    )
    assert observe_review_axes["closeout_check"]["status"] == "present"
    assert "does not make observe --card a command-root witness" in (
        observe_harness_review["anti_claim"]
    )

    tour_card = RuntimeShell(MICROCOSM_ROOT).tour_card(project)
    tour_case = tour_card["command_reference_execution_case"]
    assert tour_case["status"] == "pass"
    assert tour_case["selected_work_id"] == "work_0002"
    assert tour_case["root_work_id"] == "work_0002"
    assert tour_case["state_delta_refs"] == expected_card_state_delta_refs
    assert tour_case["command_case_eligible"] is True
    assert tour_case["public_architecture_witness_eligible"] is False
    assert tour_case["verification_status"] == "pass"
    assert tour_case["verification_failed_predicates"] == []
    assert {
        key: tour_case["verification_predicate_status"][key]
        for key in reference_predicates
    } == {
        "join_integrity": True,
        "selection_binding": True,
        "scope_completeness": True,
        "execution_terminality": True,
        "authority_boundedness": True,
        "replay_equivalence": True,
        "state_delta_scope": True,
        "record_classification_matrix": True,
        "assertion_matrix_coverage": True,
        "projection_fidelity": False,
    }
    assert tour_case["verification_predicate_status"][
        "truth_class_authority"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_occurrence_refs"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_state_delta_refs"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_state_delta_summary"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_predicate_details"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_predicate_status"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_semantic_digest"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_truth_class_authority"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_truth_class_summary"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_record_classification_summary"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_root_binding"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_eligibility_flags"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_verification_summary"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_safe_to_show_boundary"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_guidance_boundary"
    ] is True
    assert tour_case["verification_predicate_status"][
        "rendered_late_predicate_status"
    ] is True
    assert tour_case["record_classification_counts"] == classification_counts
    assert tour_case["ambient_history_ref_count"] == ambient_history_count
    assert tour_case["record_classification_matrix_verified"] is True
    assert tour_card["compile_summary"]["command_reference_execution_case_status"] == (
        "pass"
    )
    assert tour_card["compile_summary"]["public_architecture_witness_eligible"] is False
    assert tour_card["compile_summary"][
        "command_reference_state_delta_ref_count"
    ] == len(expected_card_state_delta_refs)
    assert tour_card["compile_summary"][
        "command_reference_state_delta_refs_verified"
    ] is True
    assert tour_card["compile_summary"][
        "command_reference_state_delta_scope_verified"
    ] is True
    assert tour_card["compile_summary"][
        "command_reference_state_delta_refs_ref"
    ] == "command_reference_execution_case.state_delta_refs"
    assert tour_card["compile_summary"][
        "command_reference_state_delta_scope_ref"
    ] == "verification_predicate_status.state_delta_scope"
    assert tour_card["compile_summary"][
        "command_reference_assertion_matrix_predicate_count"
    ] == len(architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES)
    assert tour_card["compile_summary"][
        "command_reference_required_assertion_predicate_count"
    ] == len(architecture_kernel.REFERENCE_CASE_ASSERTION_PREDICATES)
    assert tour_card["compile_summary"][
        "command_reference_assertion_matrix_coverage_verified"
    ] is True
    assert tour_card["compile_summary"][
        "command_reference_assertion_matrix_coverage_ref"
    ] == "verification_predicate_status.assertion_matrix_coverage"
    assert tour_card["compile_summary"][
        "command_reference_record_classification_matrix_verified"
    ] is True
    assert tour_card["compile_summary"][
        "command_reference_record_classification_matrix_ref"
    ] == "verification_predicate_status.record_classification_matrix"
    assert tour_card["compile_summary"][
        "command_reference_ambient_history_ref_count"
    ] == ambient_history_count
    assert tour_card["compile_summary"][
        "tour_command_causality_coverage_status"
    ] == "partial"
    assert tour_card["compile_summary"][
        "tour_public_witness_command_root_status"
    ] == "not_command_rooted"
    assert tour_card["compile_summary"]["tour_command_root_gap_count"] == 6
    assert (
        tour_card["compile_summary"]["tour_command_root_blocking_gap_count"]
        == 5
    )
    assert tour_card["compile_summary"][
        "agent_harness_record_review_status"
    ] == "selected_work_record_reviewable_tour_not_command_rooted"
    assert tour_card["compile_summary"]["agent_harness_record_review_ref"] == (
        "tour_command_causality_coverage_assay.agent_harness_record_review"
    )
    assay = tour_card["tour_command_causality_coverage_assay"]
    assert (
        assay["schema_version"]
        == "microcosm_tour_command_causality_coverage_assay_v1"
    )
    assert assay["status"] == "partial"
    assert assay["public_witness_command_root_status"] == "not_command_rooted"
    assert assay["tour_command_has_returned_work_id"] is False
    assert assay["tour_command_root_binding_ref"] is None
    assert assay["selected_work_id"] == "work_0002"
    assert assay["selected_work_root_work_id"] == "work_0002"
    assert assay["selected_work_root_matches_selected"] is True
    assert assay["selected_work_reference_case_status"] == "pass"
    assert assay["selected_work_reference_verification_status"] == "pass"
    assert assay["selected_work_reference_public_witness_eligible"] is False
    assert assay["selected_work_reference_state_delta_refs"] == (
        expected_card_state_delta_refs
    )
    assert assay["selected_work_reference_state_delta_ref_count"] == len(
        expected_card_state_delta_refs
    )
    assert assay["selected_work_reference_state_delta_refs_verified"] is True
    assert assay["selected_work_reference_state_delta_scope_verified"] is True
    assert assay["tour_command_root_gap_count"] == 6
    assert assay["tour_command_root_blocking_gap_count"] == 5
    gap_by_id = {row["gap_id"]: row for row in assay["tour_command_root_gap_matrix"]}
    assert gap_by_id["tour_returned_root_handle"]["status"] == "missing"
    assert gap_by_id["tour_invocation_envelope"]["status"] == "missing"
    assert (
        gap_by_id["tour_direct_child_relation_closure"]["status"]
        == "missing_for_tour"
    )
    assert (
        gap_by_id["tour_state_delta_scope"]["status"]
        == "not_claimed_for_tour"
    )
    assert gap_by_id["tour_state_delta_scope"][
        "selected_work_state_delta_scope_verified"
    ] is True
    assert (
        gap_by_id["tour_projection_fidelity_to_tour_root"]["status"]
        == "not_testable_without_tour_root"
    )
    assert gap_by_id["selected_work_reference_case"]["status"] == "delegated_pass"
    assert (
        gap_by_id["selected_work_reference_case"]["blocks_tour_public_witness"]
        is False
    )
    assert assay["predicate_coverage"] == {
        "join_integrity": True,
        "selection_binding": True,
        "scope_completeness": True,
        "execution_terminality": True,
        "authority_boundedness": True,
        "replay_equivalence": True,
        "state_delta_scope": True,
        "record_classification_matrix": True,
        "assertion_matrix_coverage": True,
        "projection_fidelity": False,
    }
    assert assay["classification_matrix"][0]["scope"] == "tour_command_invocation"
    assert assay["classification_matrix"][0]["claim_status"] == "not_command_rooted"
    assert assay["classification_matrix"][1]["scope"] == (
        "selected_work_reference_case"
    )
    assert assay["classification_matrix"][1]["claim_status"] == "pass"
    assert assay["classification_matrix"][1]["state_delta_ref_count"] == len(
        expected_card_state_delta_refs
    )
    assert assay["classification_matrix"][1]["state_delta_refs_verified"] is True
    assert assay["classification_matrix"][1]["state_delta_scope_verified"] is True
    assert assay["classification_matrix"][2]["scope"] == "ambient_route_history"
    assert assay["authority_ceiling"]["tour_command_public_occurrence_witness"] is False
    assert (
        assay["authority_ceiling"][
            "selected_work_reference_case_may_be_occurrence_witness"
        ]
        is True
    )
    harness_review = assay["agent_harness_record_review"]
    assert harness_review["status"] == (
        "selected_work_record_reviewable_tour_not_command_rooted"
    )
    assert harness_review["selected_work_reference_case_status"] == "pass"
    assert harness_review["selected_work_reference_verification_status"] == "pass"
    assert harness_review["selected_work_id"] == "work_0002"
    assert harness_review["root_work_id"] == "work_0002"
    assert harness_review["root_matches_selected"] is True
    assert harness_review["tour_command_root_blockers"] == [
        "tour_returned_root_handle",
        "tour_invocation_envelope",
        "tour_direct_child_relation_closure",
        "tour_state_delta_scope",
        "tour_projection_fidelity_to_tour_root",
    ]
    review_axes = {row["axis"]: row for row in harness_review["review_axes"]}
    assert review_axes["trajectory"]["evidence_count"] == len(
        tour_case["occurrence_witness_refs"]
    )
    assert review_axes["trajectory"]["status"] == "present"
    assert review_axes["reproducibility_fixture"]["status"] == "present"
    assert review_axes["reproducibility_fixture"]["state_delta_ref_count"] == len(
        expected_card_state_delta_refs
    )
    assert review_axes["task_boundary"]["status"] == "present"
    assert review_axes["benchmark_anti_claim"]["drilldown_command"] == (
        "plectis comprehend --slice claims --organ "
        "agent_benchmark_integrity_anti_gaming_replay"
    )
    assert review_axes["closeout_check"]["status"] == "present"
    full_tour = RuntimeShell(MICROCOSM_ROOT).tour(project, persist_receipt=False)
    full_assay = full_tour["tour_command_causality_coverage_assay"]
    assert (
        full_assay["schema_version"]
        == "microcosm_tour_command_causality_coverage_assay_v1"
    )
    assert full_assay["public_witness_command_root_status"] == "not_command_rooted"
    assert full_assay["tour_command_has_returned_work_id"] is False
    assert full_assay["project_compile_state_written"] is True
    assert full_assay["cached_state_reused"] is False
    assert full_assay["selected_work_reference_case_status"] == "pass"
    assert full_assay["selected_work_reference_verification_status"] == "pass"
    assert full_assay["tour_command_root_gap_count"] == 6
    assert full_assay["tour_command_root_blocking_gap_count"] == 5
    assert full_tour["compile_summary"][
        "command_reference_state_delta_ref_count"
    ] == len(expected_card_state_delta_refs)
    assert full_tour["compile_summary"][
        "command_reference_state_delta_refs_verified"
    ] is True
    assert full_tour["compile_summary"][
        "command_reference_state_delta_scope_verified"
    ] is True
    assert full_tour["compile_summary"][
        "command_reference_state_delta_refs_ref"
    ] == "command_reference_execution_case.state_delta_refs"
    assert full_tour["compile_summary"][
        "command_reference_state_delta_scope_ref"
    ] == "verification_predicate_status.state_delta_scope"
    assert full_tour["compile_summary"][
        "command_reference_assertion_matrix_coverage_verified"
    ] is True
    assert full_tour["compile_summary"][
        "tour_command_causality_coverage_status"
    ] == full_assay["status"]
    assert full_tour["compile_summary"][
        "tour_public_witness_command_root_status"
    ] == "not_command_rooted"
    assert full_tour["compile_summary"]["tour_command_root_gap_count"] == 6
    assert (
        full_tour["compile_summary"]["tour_command_root_blocking_gap_count"]
        == 5
    )
    assert full_tour["compile_summary"][
        "agent_harness_record_review_status"
    ] == "selected_work_record_reviewable_tour_not_command_rooted"

    tour_rendered_verification = architecture_kernel.verify_reference_execution_case(
        project,
        persisted_run_case,
        rendered_witness=tour_card,
    )
    assert tour_rendered_verification["status"] == "pass"
    assert tour_rendered_verification["predicate_status"][
        "rendered_semantic_digest"
    ] is True

    compact_truth_classes = [
        row["truth_class"]
        for row in [
            *case["assertion_matrix"],
            *case["structural_and_constitutional_lookups"],
        ]
        if isinstance(row.get("truth_class"), str)
    ]
    rendered_witness_for_case = {
        "command_reference_execution_case": {
            "schema_version": "microcosm_command_reference_execution_case_card_v1",
            "selected_work_id": case["root_binding"]["work_id"],
            "root_work_id": case["root_binding"]["work_id"],
            "root_binding_kind": case["root_binding"]["binding_kind"],
            "root_matches_selected_work": True,
            "evidence_ref": run["reference_execution_case_ref"],
            "semantic_digest": case["semantic_digest"],
            "occurrence_witness_refs": case["occurrence_witness_refs"],
            "state_delta_refs": architecture_kernel.reference_state_delta_refs(
                case["state_delta"]
            ),
            "predicate_status": case["predicate_status"],
            "predicate_details": case["predicate_details"],
            "record_classification_counts": case["record_classification_counts"],
            "ambient_history_ref_count": case["record_classification_counts"][
                "ambient_history"
            ],
            "record_classification_matrix_ref": (
                f"{run['reference_execution_case_ref']}::record_classification_matrix"
            ),
            "command_case_eligible": case["command_case_eligible"],
            "public_architecture_witness_eligible": case[
                "public_architecture_witness_eligible"
            ],
            "producer_claimed_command_case_eligible": case["command_case_eligible"],
            "producer_claimed_public_architecture_witness_eligible": case[
                "public_architecture_witness_eligible"
            ],
            "status": "pass",
            "public_witness_status": "projection_not_eligible",
            "verification_status": "pass",
            "verification_failed_predicates": [],
            "verification_predicate_status": {
                "rendered_verification_summary": True,
                "rendered_safe_to_show_boundary": True,
                "rendered_guidance_boundary": True,
                "rendered_predicate_details": True,
                "rendered_state_delta_refs": True,
                "rendered_predicate_status": True,
                "rendered_record_classification_summary": True,
                "rendered_late_predicate_status": True,
            },
            "anti_claim": case["anti_claim"],
            "reader_action": (
                "Use this compact card to decide whether the command-root "
                "occurrence case is eligible before treating any architecture "
                "projection as a public witness."
            ),
            "verification_ref": "architecture_kernel.verify_reference_execution_case",
            "safe_to_show": {
                "receipt_ref_visible": True,
                "predicate_status_visible": True,
                "full_receipt_body_omitted": True,
                "source_files_mutated": False,
                "provider_calls_authorized": False,
                "release_authorized": False,
                "proof_correctness_claim": False,
            },
            "truth_classes": sorted(set(compact_truth_classes)),
            "truth_class_counts": {
                truth_class: compact_truth_classes.count(truth_class)
                for truth_class in sorted(set(compact_truth_classes))
            },
            "assertion_matrix_ref": (
                f"{run['reference_execution_case_ref']}::assertion_matrix"
            ),
        }
    }
    verification = architecture_kernel.verify_reference_execution_case(
        project,
        case,
        rendered_witness=rendered_witness_for_case,
    )
    assert verification["status"] == "pass"
    assert {
        key: verification["predicate_status"][key]
        for key in reference_predicates
    } == {
        "join_integrity": True,
        "selection_binding": True,
        "scope_completeness": True,
        "execution_terminality": True,
        "authority_boundedness": True,
        "replay_equivalence": True,
        "state_delta_scope": True,
        "record_classification_matrix": True,
        "assertion_matrix_coverage": True,
        "projection_fidelity": False,
    }
    assert verification["predicate_status"]["truth_class_authority"] is True
    assert verification["predicate_status"]["assertion_matrix_coverage"] is True
    assert verification["predicate_status"]["rendered_occurrence_refs"] is True
    assert verification["predicate_status"]["rendered_state_delta_refs"] is True
    assert verification["predicate_status"]["rendered_state_delta_summary"] is True
    assert verification["predicate_status"]["rendered_predicate_details"] is True
    assert verification["predicate_status"]["rendered_predicate_status"] is True
    assert verification["predicate_status"][
        "rendered_assertion_matrix_coverage"
    ] is True
    assert verification["predicate_status"]["rendered_truth_class_summary"] is True
    assert verification["predicate_status"][
        "rendered_record_classification_summary"
    ] is True
    assert verification["predicate_status"]["rendered_root_binding"] is True
    assert verification["predicate_status"]["rendered_eligibility_flags"] is True
    assert verification["predicate_status"]["rendered_verification_summary"] is True
    assert verification["predicate_status"]["rendered_safe_to_show_boundary"] is True
    assert verification["predicate_status"]["rendered_guidance_boundary"] is True
    assert verification["predicate_status"]["rendered_late_predicate_status"] is True
    assert verification["predicate_status"]["projection_fidelity"] is False
    assert verification["predicate_details"]["replay_equivalence_basis"] == (
        "available_delta_contains_root_or_descendant"
    )

    forged_assertion_missing_case = json.loads(json.dumps(case))
    forged_assertion_missing_case["assertion_matrix"] = [
        row
        for row in forged_assertion_missing_case["assertion_matrix"]
        if row.get("eligibility_predicate") != "state_delta_scope"
    ]
    forged_assertion_missing_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            forged_assertion_missing_case,
            rendered_witness=rendered_witness_for_case,
        )
    )
    assert forged_assertion_missing_verification["status"] == "blocked"
    assert "assertion_matrix_coverage" in (
        forged_assertion_missing_verification["failed_predicates"]
    )
    assert any(
        row["reason"] == "assertion_matrix_missing_required_predicate"
        and row["predicate_id"] == "state_delta_scope"
        for row in forged_assertion_missing_verification["predicate_details"][
            "assertion_matrix_coverage_violations"
        ]
    )

    forged_assertion_duplicate_case = json.loads(json.dumps(case))
    forged_assertion_duplicate_case["assertion_matrix"].append(
        json.loads(json.dumps(case["assertion_matrix"][0]))
    )
    forged_assertion_duplicate_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            forged_assertion_duplicate_case,
            rendered_witness=rendered_witness_for_case,
        )
    )
    assert forged_assertion_duplicate_verification["status"] == "blocked"
    assert "assertion_matrix_coverage" in (
        forged_assertion_duplicate_verification["failed_predicates"]
    )
    assert any(
        row["reason"] == "assertion_matrix_duplicate_required_predicate"
        and row["predicate_id"] == "join_integrity"
        and row["count"] == 2
        for row in forged_assertion_duplicate_verification["predicate_details"][
            "assertion_matrix_coverage_violations"
        ]
    )

    forged_assertion_unknown_case = json.loads(json.dumps(case))
    forged_assertion_unknown_case["assertion_matrix"][0][
        "eligibility_predicate"
    ] = "release_ready"
    forged_assertion_unknown_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            forged_assertion_unknown_case,
            rendered_witness=rendered_witness_for_case,
        )
    )
    assert forged_assertion_unknown_verification["status"] == "blocked"
    assert "assertion_matrix_coverage" in (
        forged_assertion_unknown_verification["failed_predicates"]
    )
    assertion_unknown_violations = forged_assertion_unknown_verification[
        "predicate_details"
    ]["assertion_matrix_coverage_violations"]
    assert any(
        row["reason"] == "assertion_matrix_missing_required_predicate"
        and row["predicate_id"] == "join_integrity"
        for row in assertion_unknown_violations
    )
    assert any(
        row["reason"] == "assertion_matrix_unknown_predicate"
        and row["predicate_id"] == "release_ready"
        for row in assertion_unknown_violations
    )

    forged_rendered_status_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_status_case = forged_rendered_status_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_status = forged_rendered_status_case[
        "verification_predicate_status"
    ]
    forged_rendered_status["release_ready"] = True
    forged_rendered_status_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_status_witness,
        )
    )
    assert forged_rendered_status_verification["status"] == "blocked"
    assert "rendered_predicate_status" in (
        forged_rendered_status_verification["failed_predicates"]
    )
    assert forged_rendered_status_verification["predicate_status"][
        "rendered_predicate_status"
    ] is False
    rendered_status_violations = forged_rendered_status_verification[
        "predicate_details"
    ]["rendered_predicate_status_violations"]
    assert any(
        row["reason"] == "rendered_predicate_status_unexpected_predicate"
        and row["predicate_id"] == "release_ready"
        and row["rendered"] is True
        for row in rendered_status_violations
    )
    assert any(
        row["reason"] == "rendered_predicate_status_predicate_mismatch"
        and row["predicate_id"] == "rendered_predicate_status"
        and row["expected"] is False
        and row["rendered"] is True
        for row in rendered_status_violations
    )

    forged_rendered_record_summary_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_record_summary_case = forged_rendered_record_summary_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_record_summary_case["record_classification_counts"][
        "ambient_history"
    ] += 1
    forged_rendered_record_summary_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_record_summary_witness,
        )
    )
    assert forged_rendered_record_summary_verification["status"] == "blocked"
    assert "rendered_record_classification_summary" in (
        forged_rendered_record_summary_verification["failed_predicates"]
    )
    assert (
        forged_rendered_record_summary_verification["predicate_status"][
            "rendered_record_classification_summary"
        ]
        is False
    )
    rendered_record_summary_violations = forged_rendered_record_summary_verification[
        "predicate_details"
    ]["rendered_record_classification_summary_violations"]
    assert any(
        row["reason"] == "rendered_record_classification_counts_mismatch"
        and row["field"] == "record_classification_counts"
        for row in rendered_record_summary_violations
    )

    forged_replay_case = json.loads(json.dumps(case))
    forged_replay_case["state_delta"] = {
        "status": "available",
        "new_work_ids": [],
        "new_event_ids": [],
        "new_evidence_refs": [],
    }
    forged_replay_verification = architecture_kernel.verify_reference_execution_case(
        project,
        forged_replay_case,
        rendered_witness=rendered_witness_for_case,
    )
    assert forged_replay_verification["status"] == "blocked"
    assert "replay_equivalence" in forged_replay_verification["failed_predicates"]
    assert forged_replay_verification["predicate_status"]["replay_equivalence"] is False
    assert forged_replay_verification["predicate_details"][
        "replay_equivalence_basis"
    ] == "available_delta_missing_root_or_descendant_or_current_state_ref"

    forged_delta_scope_case = json.loads(json.dumps(case))
    ambient_delta_event_id = case["ambient_history_excluded"]["event_ids"][0]
    forged_delta_scope_case["state_delta"]["new_event_ids"].append(
        ambient_delta_event_id
    )
    forged_delta_scope_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_delta_scope_rendered_case = forged_delta_scope_witness[
        "command_reference_execution_case"
    ]
    forged_delta_scope_rendered_case["state_delta_refs"] = (
        architecture_kernel.reference_state_delta_refs(
            forged_delta_scope_case["state_delta"]
        )
    )
    forged_delta_scope_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            forged_delta_scope_case,
            rendered_witness=forged_delta_scope_witness,
        )
    )
    assert forged_delta_scope_verification["status"] == "blocked"
    assert "state_delta_scope" in (
        forged_delta_scope_verification["failed_predicates"]
    )
    assert "command_case_eligible" in (
        forged_delta_scope_verification["failed_predicates"]
    )
    assert "rendered_predicate_status" in (
        forged_delta_scope_verification["failed_predicates"]
    )
    assert forged_delta_scope_verification["predicate_status"][
        "replay_equivalence"
    ] is True
    assert forged_delta_scope_verification["predicate_status"][
        "state_delta_scope"
    ] is False
    assert forged_delta_scope_verification["predicate_status"][
        "rendered_state_delta_refs"
    ] is True
    assert forged_delta_scope_verification["predicate_status"][
        "rendered_state_delta_summary"
    ] is True
    assert forged_delta_scope_verification["predicate_details"][
        "unexpected_delta_event_ids"
    ] == [ambient_delta_event_id]
    assert any(
        row["field"] == "new_event_ids"
        and row["reason"] == "state_delta_event_id_outside_selected_work"
        and row["unexpected"] == [ambient_delta_event_id]
        for row in forged_delta_scope_verification["predicate_details"][
            "state_delta_scope_violations"
        ]
    )

    reference_case_path = (
        project / ".microcosm/evidence/reference_execution_case_work_0002.json"
    )
    original_reference_case_text = reference_case_path.read_text(encoding="utf-8")
    reference_case_path.write_text(
        json.dumps(forged_replay_case, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        forged_compiled = project_substrate.compile_project(project)
    finally:
        reference_case_path.write_text(
            original_reference_case_text,
            encoding="utf-8",
        )
    forged_reader_case = forged_compiled["reader_causal_chain"][
        "command_reference_execution_case"
    ]
    assert forged_reader_case["status"] == "blocked"
    assert forged_reader_case["command_case_eligible"] is False
    assert forged_reader_case["public_witness_status"] == "verification_blocked"
    assert forged_reader_case["producer_claimed_command_case_eligible"] is True
    assert forged_reader_case["verification_status"] == "blocked"
    assert "replay_equivalence" in forged_reader_case[
        "verification_failed_predicates"
    ]

    reference_case_path.write_text(
        json.dumps(forged_delta_scope_case, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        forged_delta_scope_compiled = project_substrate.compile_project(project)
        forged_delta_scope_tour = RuntimeShell(MICROCOSM_ROOT).tour_card(project)
    finally:
        reference_case_path.write_text(
            original_reference_case_text,
            encoding="utf-8",
        )
    forged_delta_scope_reader_case = forged_delta_scope_compiled[
        "reader_causal_chain"
    ]["command_reference_execution_case"]
    assert forged_delta_scope_reader_case["status"] == "blocked"
    assert forged_delta_scope_reader_case["command_case_eligible"] is False
    assert forged_delta_scope_reader_case["verification_status"] == "blocked"
    assert "state_delta_scope" in forged_delta_scope_reader_case[
        "verification_failed_predicates"
    ]
    assert forged_delta_scope_reader_case["verification_predicate_status"][
        "rendered_state_delta_refs"
    ] is True
    assert forged_delta_scope_reader_case["verification_predicate_status"][
        "state_delta_scope"
    ] is False
    forged_delta_scope_compile_summary = forged_delta_scope_tour["compile_summary"]
    assert (
        forged_delta_scope_compile_summary[
            "command_reference_state_delta_refs_verified"
        ]
        is True
    )
    assert (
        forged_delta_scope_compile_summary[
            "command_reference_state_delta_scope_verified"
        ]
        is False
    )
    forged_delta_scope_assay = forged_delta_scope_tour[
        "tour_command_causality_coverage_assay"
    ]
    assert (
        forged_delta_scope_assay[
            "selected_work_reference_state_delta_refs_verified"
        ]
        is True
    )
    assert (
        forged_delta_scope_assay[
            "selected_work_reference_state_delta_scope_verified"
        ]
        is False
    )
    assert (
        forged_delta_scope_assay["classification_matrix"][1][
            "state_delta_refs_verified"
        ]
        is True
    )
    assert (
        forged_delta_scope_assay["classification_matrix"][1][
            "state_delta_scope_verified"
        ]
        is False
    )

    forged_scope_case = json.loads(json.dumps(case))
    forged_scope_case["occurrence_witness_refs"].append(
        ".microcosm/work_items.json::work_0001"
    )
    forged_scope_verification = architecture_kernel.verify_reference_execution_case(
        project,
        forged_scope_case,
        rendered_witness=rendered_witness_for_case,
    )
    assert forged_scope_verification["status"] == "blocked"
    assert "scope_completeness" in forged_scope_verification["failed_predicates"]
    assert forged_scope_verification["predicate_details"][
        "unexpected_occurrence_witness_refs"
    ] == [".microcosm/work_items.json::work_0001"]
    assert forged_scope_verification["predicate_details"][
        "ambient_occurrence_refs_in_case"
    ] == [".microcosm/work_items.json::work_0001"]

    forged_classification_case = json.loads(json.dumps(case))
    ambient_work_ref = ".microcosm/work_items.json::work_0001"
    for row in forged_classification_case["record_classification_matrix"]:
        if row.get("source_ref") == ambient_work_ref:
            row["classification"] = "causal_descendant"
            row["binding"] = "work_item.event_refs"
            row["included_in_occurrence_witness"] = True
            break
    forged_classification_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            forged_classification_case,
            rendered_witness=rendered_witness_for_case,
        )
    )
    assert forged_classification_verification["status"] == "blocked"
    assert "record_classification_matrix" in (
        forged_classification_verification["failed_predicates"]
    )
    assert forged_classification_verification["predicate_status"][
        "record_classification_matrix"
    ] is False
    classification_violations = forged_classification_verification[
        "predicate_details"
    ]["record_classification_matrix_violations"]
    assert any(
        row["reason"] == "record_classification_matrix_missing_rows"
        and any(
            missing["source_ref"] == ambient_work_ref
            and missing["classification"] == "ambient_history"
            and missing["included_in_occurrence_witness"] is False
            for missing in row["missing"]
        )
        for row in classification_violations
    )
    assert any(
        row["reason"] == "record_classification_matrix_unexpected_rows"
        and any(
            rendered["source_ref"] == ambient_work_ref
            and rendered["classification"] == "causal_descendant"
            and rendered["included_in_occurrence_witness"] is True
            for rendered in row["rendered"]
        )
        for row in classification_violations
    )

    forged_classification_counts_case = json.loads(json.dumps(case))
    forged_classification_counts_case["record_classification_counts"][
        "ambient_history"
    ] += 1
    forged_classification_counts_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            forged_classification_counts_case,
            rendered_witness=rendered_witness_for_case,
        )
    )
    assert forged_classification_counts_verification["status"] == "blocked"
    assert "record_classification_matrix" in (
        forged_classification_counts_verification["failed_predicates"]
    )
    assert any(
        row["reason"] == "record_classification_counts_mismatch"
        and row["field"] == "record_classification_counts"
        for row in forged_classification_counts_verification["predicate_details"][
            "record_classification_matrix_violations"
        ]
    )

    forged_ambient_history_case = json.loads(json.dumps(case))
    forged_ambient_history_case["ambient_history_excluded"]["records"] = []
    forged_ambient_history_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            forged_ambient_history_case,
            rendered_witness=rendered_witness_for_case,
        )
    )
    assert forged_ambient_history_verification["status"] == "blocked"
    assert "record_classification_matrix" in (
        forged_ambient_history_verification["failed_predicates"]
    )
    assert any(
        row["reason"] == "ambient_history_records_mismatch"
        and row["field"] == "ambient_history_excluded.records"
        for row in forged_ambient_history_verification["predicate_details"][
            "record_classification_matrix_violations"
        ]
    )

    forged_truth_case = json.loads(json.dumps(case))
    forged_truth_case["structural_and_constitutional_lookups"][1][
        "truth_class"
    ] = "occurrence"
    forged_truth_verification = architecture_kernel.verify_reference_execution_case(
        project,
        forged_truth_case,
        rendered_witness=rendered_witness_for_case,
    )
    assert forged_truth_verification["status"] == "blocked"
    assert "truth_class_authority" in forged_truth_verification["failed_predicates"]
    assert forged_truth_verification["predicate_details"]["truth_class_violations"][
        0
    ]["reason"] == "occurrence_claim_without_occurrence_ref"

    forged_rendered_detail_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_detail_case = forged_rendered_detail_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_details = forged_rendered_detail_case["predicate_details"]
    case_root_work_id = case["root_binding"]["work_id"]
    forged_rendered_details["projection_selected_work_id"] = case_root_work_id
    forged_rendered_details["missing_event_ids"] = ["evt_missing"]
    forged_rendered_details["unexpected_detail"] = "release_ready"
    forged_rendered_detail_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_detail_witness,
        )
    )
    assert forged_rendered_detail_verification["status"] == "blocked"
    assert "rendered_predicate_details" in (
        forged_rendered_detail_verification["failed_predicates"]
    )
    assert "rendered_predicate_status" in (
        forged_rendered_detail_verification["failed_predicates"]
    )
    assert forged_rendered_detail_verification["predicate_status"][
        "rendered_predicate_details"
    ] is False
    assert forged_rendered_detail_verification["predicate_status"][
        "rendered_predicate_status"
    ] is False
    rendered_detail_violations = forged_rendered_detail_verification[
        "predicate_details"
    ]["rendered_predicate_detail_violations"]
    assert any(
        row.get("field") == "projection_selected_work_id"
        and row["expected"]
        == case["predicate_details"]["projection_selected_work_id"]
        and row["rendered"] == case_root_work_id
        for row in rendered_detail_violations
    )
    assert any(
        row.get("field") == "missing_event_ids"
        and row["expected"] == case["predicate_details"]["missing_event_ids"]
        and row["rendered"] == ["evt_missing"]
        for row in rendered_detail_violations
    )
    assert any(
        row["reason"] == "rendered_predicate_details_unexpected_keys"
        and row["rendered"] == ["unexpected_detail"]
        for row in rendered_detail_violations
    )

    forged_rendered_truth_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_truth_case = forged_rendered_truth_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_truth_case[
        "structural_and_constitutional_lookups"
    ] = json.loads(json.dumps(case["structural_and_constitutional_lookups"]))
    forged_rendered_truth_case["structural_and_constitutional_lookups"][1][
        "truth_class"
    ] = "occurrence"
    forged_rendered_truth_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_truth_witness,
        )
    )
    assert forged_rendered_truth_verification["status"] == "blocked"
    assert "rendered_truth_class_authority" in (
        forged_rendered_truth_verification["failed_predicates"]
    )
    rendered_truth_violations = forged_rendered_truth_verification[
        "predicate_details"
    ]["rendered_truth_class_violations"]
    assert any(
        row["reason"] == "rendered_truth_class_mismatch"
        and row["expected_truth_class"] == "constitution"
        and row["rendered_truth_class"] == "occurrence"
        for row in rendered_truth_violations
    )
    assert any(
        row["reason"] == "rendered_occurrence_claim_without_occurrence_ref"
        and row["source_ref"] == "architecture_kernel._base"
        for row in rendered_truth_violations
    )

    forged_rendered_truth_summary_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_truth_summary_case = forged_rendered_truth_summary_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_truth_summary_case["truth_classes"] = ["occurrence"]
    forged_rendered_truth_summary_case["truth_class_counts"] = {"occurrence": 999}
    forged_rendered_truth_summary_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_truth_summary_witness,
        )
    )
    assert forged_rendered_truth_summary_verification["status"] == "blocked"
    assert "rendered_truth_class_summary" in (
        forged_rendered_truth_summary_verification["failed_predicates"]
    )
    assert forged_rendered_truth_summary_verification["predicate_status"][
        "rendered_truth_class_summary"
    ] is False
    rendered_truth_summary_violations = forged_rendered_truth_summary_verification[
        "predicate_details"
    ]["rendered_truth_class_summary_violations"]
    assert any(
        row["reason"] == "rendered_truth_classes_mismatch"
        and row["expected"] == [
            "constitution",
            "occurrence",
            "projection",
            "structure",
        ]
        and row["rendered"] == ["occurrence"]
        for row in rendered_truth_summary_violations
    )
    assert any(
        row["reason"] == "rendered_truth_class_counts_mismatch"
        and row["rendered"] == {"occurrence": 999}
        for row in rendered_truth_summary_violations
    )

    forged_rendered_root_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_root_case = forged_rendered_root_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_root_case["selected_work_id"] = "work_0001"
    forged_rendered_root_case["root_work_id"] = "work_0001"
    forged_rendered_root_case["root_binding_kind"] = "representative_first_closed_work"
    forged_rendered_root_case["root_matches_selected_work"] = False
    forged_rendered_root_case["evidence_ref"] = (
        ".microcosm/evidence/reference_execution_case_work_0001.json"
    )
    forged_rendered_root_case["assertion_matrix_ref"] = (
        ".microcosm/evidence/reference_execution_case_work_0001.json::assertion_matrix"
    )
    forged_rendered_root_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_root_witness,
        )
    )
    assert forged_rendered_root_verification["status"] == "blocked"
    assert "rendered_root_binding" in (
        forged_rendered_root_verification["failed_predicates"]
    )
    assert forged_rendered_root_verification["predicate_status"][
        "rendered_root_binding"
    ] is False
    rendered_root_violations = forged_rendered_root_verification[
        "predicate_details"
    ]["rendered_root_binding_violations"]
    assert any(
        row["field"] == "root_work_id"
        and row["expected"] == "work_0002"
        and row["rendered"] == "work_0001"
        for row in rendered_root_violations
    )
    assert any(
        row["field"] == "evidence_ref"
        and row["expected"] == ".microcosm/evidence/reference_execution_case_work_0002.json"
        and row["rendered"] == ".microcosm/evidence/reference_execution_case_work_0001.json"
        for row in rendered_root_violations
    )

    forged_rendered_eligibility_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_eligibility_case = forged_rendered_eligibility_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_eligibility_case["command_case_eligible"] = False
    forged_rendered_eligibility_case[
        "producer_claimed_public_architecture_witness_eligible"
    ] = True
    forged_rendered_eligibility_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_eligibility_witness,
        )
    )
    assert forged_rendered_eligibility_verification["status"] == "blocked"
    assert "rendered_eligibility_flags" in (
        forged_rendered_eligibility_verification["failed_predicates"]
    )
    assert forged_rendered_eligibility_verification["predicate_status"][
        "rendered_eligibility_flags"
    ] is False
    rendered_eligibility_violations = forged_rendered_eligibility_verification[
        "predicate_details"
    ]["rendered_eligibility_flag_violations"]
    assert any(
        row["field"] == "command_case_eligible"
        and row["expected"] is True
        and row["rendered"] is False
        for row in rendered_eligibility_violations
    )
    assert any(
        row["field"] == "producer_claimed_public_architecture_witness_eligible"
        and row["expected"] is False
        and row["rendered"] is True
        for row in rendered_eligibility_violations
    )

    forged_rendered_summary_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_summary_case = forged_rendered_summary_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_summary_case["status"] = "partial"
    forged_rendered_summary_case["verification_status"] = "blocked"
    forged_rendered_summary_case["verification_failed_predicates"] = [
        "scope_completeness"
    ]
    forged_rendered_summary_case["public_witness_status"] = "pass"
    forged_rendered_summary_case["verification_predicate_status"][
        "rendered_verification_summary"
    ] = True
    forged_rendered_summary_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_summary_witness,
        )
    )
    assert forged_rendered_summary_verification["status"] == "blocked"
    assert "rendered_verification_summary" in (
        forged_rendered_summary_verification["failed_predicates"]
    )
    assert forged_rendered_summary_verification["predicate_status"][
        "rendered_verification_summary"
    ] is False
    rendered_summary_violations = forged_rendered_summary_verification[
        "predicate_details"
    ]["rendered_verification_summary_violations"]
    assert any(
        row.get("field") == "status"
        and row["expected"] == "pass"
        and row["rendered"] == "partial"
        for row in rendered_summary_violations
    )
    assert any(
        row.get("field") == "verification_status"
        and row["expected"] == "pass"
        and row["rendered"] == "blocked"
        for row in rendered_summary_violations
    )
    assert any(
        row.get("field") == "verification_failed_predicates"
        and row["expected"] == []
        and row["rendered"] == ["scope_completeness"]
        for row in rendered_summary_violations
    )
    assert any(
        row.get("field") == "public_witness_status"
        and row["expected"] == "projection_not_eligible"
        and row["rendered"] == "pass"
        for row in rendered_summary_violations
    )
    assert any(
        row.get("predicate_id") == "rendered_verification_summary"
        and row["expected"] is False
        and row["rendered"] is True
        for row in rendered_summary_violations
    )

    forged_rendered_safe_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_safe_case = forged_rendered_safe_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_safe = forged_rendered_safe_case["safe_to_show"]
    forged_rendered_safe.pop("full_receipt_body_omitted")
    forged_rendered_safe["provider_calls_authorized"] = True
    forged_rendered_safe["release_authorized"] = True
    forged_rendered_safe["proof_correctness_claim"] = True
    forged_rendered_safe["release_ready"] = True
    forged_rendered_safe_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_safe_witness,
        )
    )
    assert forged_rendered_safe_verification["status"] == "blocked"
    assert "rendered_safe_to_show_boundary" in (
        forged_rendered_safe_verification["failed_predicates"]
    )
    assert forged_rendered_safe_verification["predicate_status"][
        "rendered_safe_to_show_boundary"
    ] is False
    assert forged_rendered_safe_verification["predicate_status"][
        "rendered_late_predicate_status"
    ] is False
    rendered_safe_violations = forged_rendered_safe_verification[
        "predicate_details"
    ]["rendered_safe_to_show_boundary_violations"]
    assert any(
        row["reason"] == "rendered_safe_to_show_missing_keys"
        and row["missing"] == ["full_receipt_body_omitted"]
        for row in rendered_safe_violations
    )
    assert any(
        row["reason"] == "rendered_safe_to_show_unexpected_keys"
        and row["rendered"] == ["release_ready"]
        for row in rendered_safe_violations
    )
    assert any(
        row.get("field") == "release_authorized"
        and row["expected"] is False
        and row["rendered"] is True
        for row in rendered_safe_violations
    )
    assert any(
        row.get("field") == "proof_correctness_claim"
        and row["expected"] is False
        and row["rendered"] is True
        for row in rendered_safe_violations
    )

    forged_rendered_guidance_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_guidance_case = forged_rendered_guidance_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_guidance_case["schema_version"] = (
        "microcosm_release_ready_card_v1"
    )
    forged_rendered_guidance_case["anti_claim"] = "This is release-ready proof."
    forged_rendered_guidance_case["reader_action"] = (
        "Publish this as a public proof."
    )
    forged_rendered_guidance_case["verification_ref"] = "renderer.self_verified"
    forged_rendered_guidance_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_guidance_witness,
        )
    )
    assert forged_rendered_guidance_verification["status"] == "blocked"
    assert "rendered_guidance_boundary" in (
        forged_rendered_guidance_verification["failed_predicates"]
    )
    assert "rendered_late_predicate_status" in (
        forged_rendered_guidance_verification["failed_predicates"]
    )
    assert forged_rendered_guidance_verification["predicate_status"][
        "rendered_guidance_boundary"
    ] is False
    assert forged_rendered_guidance_verification["predicate_status"][
        "rendered_late_predicate_status"
    ] is False
    rendered_guidance_violations = forged_rendered_guidance_verification[
        "predicate_details"
    ]["rendered_guidance_boundary_violations"]
    assert any(
        row.get("field") == "schema_version"
        and row["expected"] == "microcosm_command_reference_execution_case_card_v1"
        and row["rendered"] == "microcosm_release_ready_card_v1"
        for row in rendered_guidance_violations
    )
    assert any(
        row.get("field") == "anti_claim"
        and row["expected"] == case["anti_claim"]
        and row["rendered"] == "This is release-ready proof."
        for row in rendered_guidance_violations
    )
    assert any(
        row.get("field") == "reader_action"
        and row["expected"]
        == (
            "Use this compact card to decide whether the command-root occurrence "
            "case is eligible before treating any architecture projection as a "
            "public witness."
        )
        and row["rendered"] == "Publish this as a public proof."
        for row in rendered_guidance_violations
    )
    assert any(
        row.get("field") == "verification_ref"
        and row["expected"] == "architecture_kernel.verify_reference_execution_case"
        and row["rendered"] == "renderer.self_verified"
        for row in rendered_guidance_violations
    )

    forged_rendered_late_status_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_late_status_case = forged_rendered_late_status_witness[
        "command_reference_execution_case"
    ]
    forged_rendered_late_status_case["verification_predicate_status"][
        "rendered_safe_to_show_boundary"
    ] = False
    forged_rendered_late_status_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_late_status_witness,
        )
    )
    assert forged_rendered_late_status_verification["status"] == "blocked"
    assert "rendered_late_predicate_status" in (
        forged_rendered_late_status_verification["failed_predicates"]
    )
    assert forged_rendered_late_status_verification["predicate_status"][
        "rendered_safe_to_show_boundary"
    ] is True
    assert forged_rendered_late_status_verification["predicate_status"][
        "rendered_late_predicate_status"
    ] is False
    assert forged_rendered_late_status_verification["predicate_details"][
        "rendered_late_predicate_status_violations"
    ] == [
        {
            "status_field": "verification_predicate_status",
            "predicate_id": "rendered_safe_to_show_boundary",
            "expected": True,
            "rendered": False,
        },
        {
            "status_field": "verification_predicate_status",
            "predicate_id": "rendered_late_predicate_status",
            "reason": "rendered_late_predicate_status_predicate_mismatch",
            "expected": False,
            "rendered": True,
        },
    ]

    forged_rendered_digest_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_digest_witness["command_reference_execution_case"][
        "semantic_digest"
    ] = "forged-semantic-digest"
    forged_rendered_digest_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_digest_witness,
        )
    )
    assert forged_rendered_digest_verification["status"] == "blocked"
    assert "rendered_semantic_digest" in forged_rendered_digest_verification[
        "failed_predicates"
    ]
    assert forged_rendered_digest_verification["predicate_status"][
        "rendered_semantic_digest"
    ] is False
    assert forged_rendered_digest_verification["predicate_details"][
        "rendered_semantic_digest"
    ] == "forged-semantic-digest"

    forged_rendered_predicate_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_predicate_witness["command_reference_execution_case"][
        "predicate_status"
    ]["projection_fidelity"] = True
    forged_rendered_predicate_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_predicate_witness,
        )
    )
    assert forged_rendered_predicate_verification["status"] == "blocked"
    assert "rendered_predicate_status" in forged_rendered_predicate_verification[
        "failed_predicates"
    ]
    assert forged_rendered_predicate_verification["predicate_status"][
        "rendered_predicate_status"
    ] is False
    assert forged_rendered_predicate_verification["predicate_details"][
        "rendered_predicate_status_violations"
    ] == [
        {
            "status_field": "predicate_status",
            "predicate_id": "projection_fidelity",
            "expected": False,
            "rendered": True,
        },
        {
            "status_field": "verification_predicate_status",
            "predicate_id": "rendered_predicate_status",
            "reason": "rendered_predicate_status_predicate_mismatch",
            "expected": False,
            "rendered": True,
        },
    ]

    forged_rendered_predicate_omission_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_predicate_omission_witness["command_reference_execution_case"][
        "predicate_status"
    ].pop("projection_fidelity")
    forged_rendered_predicate_omission_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_predicate_omission_witness,
        )
    )
    assert forged_rendered_predicate_omission_verification["status"] == "blocked"
    assert "rendered_predicate_status" in (
        forged_rendered_predicate_omission_verification["failed_predicates"]
    )
    assert forged_rendered_predicate_omission_verification["predicate_status"][
        "rendered_predicate_status"
    ] is False
    assert forged_rendered_predicate_omission_verification["predicate_details"][
        "rendered_predicate_status_violations"
    ] == [
        {
            "status_field": "predicate_status",
            "reason": "rendered_predicate_status_missing_predicates",
            "expected": sorted(case["predicate_status"]),
            "missing": ["projection_fidelity"],
        },
        {
            "status_field": "verification_predicate_status",
            "predicate_id": "rendered_predicate_status",
            "reason": "rendered_predicate_status_predicate_mismatch",
            "expected": False,
            "rendered": True,
        },
    ]

    forged_rendered_omission = json.loads(json.dumps(rendered_witness_for_case))
    omitted_rendered_ref = forged_rendered_omission["command_reference_execution_case"][
        "occurrence_witness_refs"
    ].pop()
    forged_rendered_omission_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_omission,
        )
    )
    assert forged_rendered_omission_verification["status"] == "blocked"
    assert "rendered_occurrence_refs" in forged_rendered_omission_verification[
        "failed_predicates"
    ]
    assert forged_rendered_omission_verification["predicate_status"][
        "rendered_occurrence_refs"
    ] is False
    assert forged_rendered_omission_verification["predicate_details"][
        "missing_rendered_occurrence_refs"
    ] == [omitted_rendered_ref]

    forged_rendered_witness = json.loads(json.dumps(rendered_witness_for_case))
    forged_rendered_witness["command_reference_execution_case"][
        "occurrence_witness_refs"
    ].append(".microcosm/state_index.json")
    forged_rendered_verification = architecture_kernel.verify_reference_execution_case(
        project,
        case,
        rendered_witness=forged_rendered_witness,
    )
    assert forged_rendered_verification["status"] == "blocked"
    assert "rendered_occurrence_refs" in forged_rendered_verification[
        "failed_predicates"
    ]
    assert forged_rendered_verification["predicate_details"][
        "unexpected_rendered_occurrence_refs"
    ] == [".microcosm/state_index.json"]
    assert forged_rendered_verification["predicate_details"][
        "missing_rendered_occurrence_refs"
    ] == []

    forged_rendered_state_delta_witness = json.loads(
        json.dumps(rendered_witness_for_case)
    )
    forged_rendered_state_delta_witness["command_reference_execution_case"][
        "state_delta_refs"
    ].append(".microcosm/state_index.json")
    forged_rendered_state_delta_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            case,
            rendered_witness=forged_rendered_state_delta_witness,
        )
    )
    assert forged_rendered_state_delta_verification["status"] == "blocked"
    assert "rendered_state_delta_refs" in (
        forged_rendered_state_delta_verification["failed_predicates"]
    )
    assert "rendered_predicate_status" in (
        forged_rendered_state_delta_verification["failed_predicates"]
    )
    assert forged_rendered_state_delta_verification["predicate_status"][
        "rendered_state_delta_refs"
    ] is False
    assert forged_rendered_state_delta_verification["predicate_details"][
        "unexpected_rendered_state_delta_refs"
    ] == [".microcosm/state_index.json"]
    assert forged_rendered_state_delta_verification["predicate_details"][
        "missing_rendered_state_delta_refs"
    ] == []

    forged_rendered_summary_witness = json.loads(json.dumps(tour_card))
    forged_rendered_summary = forged_rendered_summary_witness["compile_summary"]
    forged_rendered_summary["command_reference_state_delta_ref_count"] = 999
    forged_rendered_summary["command_reference_state_delta_refs_verified"] = False
    forged_rendered_summary["command_reference_state_delta_refs_ref"] = (
        "compile_summary.local_state_delta_refs"
    )
    forged_rendered_summary["command_reference_state_delta_scope_verified"] = False
    forged_rendered_summary["command_reference_state_delta_scope_ref"] = (
        "compile_summary.local_state_delta_scope"
    )
    forged_rendered_summary_verification = (
        architecture_kernel.verify_reference_execution_case(
            project,
            persisted_run_case,
            rendered_witness=forged_rendered_summary_witness,
        )
    )
    assert forged_rendered_summary_verification["status"] == "blocked"
    assert "rendered_state_delta_summary" in (
        forged_rendered_summary_verification["failed_predicates"]
    )
    assert "rendered_predicate_status" in (
        forged_rendered_summary_verification["failed_predicates"]
    )
    assert forged_rendered_summary_verification["predicate_status"][
        "rendered_state_delta_summary"
    ] is False
    rendered_summary_violations = forged_rendered_summary_verification[
        "predicate_details"
    ]["rendered_state_delta_summary_violations"]
    assert any(
        row["scope"] == "compile_summary"
        and row["field"] == "command_reference_state_delta_ref_count"
        and row["expected"] == len(expected_card_state_delta_refs)
        and row["rendered"] == 999
        for row in rendered_summary_violations
    )
    assert any(
        row["scope"] == "compile_summary"
        and row["field"] == "command_reference_state_delta_refs_verified"
        and row["expected"] is True
        and row["rendered"] is False
        for row in rendered_summary_violations
    )
    assert any(
        row["scope"] == "compile_summary"
        and row["field"] == "command_reference_state_delta_refs_ref"
        and row["expected"] == "command_reference_execution_case.state_delta_refs"
        and row["rendered"] == "compile_summary.local_state_delta_refs"
        for row in rendered_summary_violations
    )
    assert any(
        row["scope"] == "compile_summary"
        and row["field"] == "command_reference_state_delta_scope_verified"
        and row["expected"] is True
        and row["rendered"] is False
        for row in rendered_summary_violations
    )
    assert any(
        row["scope"] == "compile_summary"
        and row["field"] == "command_reference_state_delta_scope_ref"
        and row["expected"] == "verification_predicate_status.state_delta_scope"
        and row["rendered"] == "compile_summary.local_state_delta_scope"
        for row in rendered_summary_violations
    )

    record_by_alias = {
        row["alias"]: row
        for row in case["record_classifications"]
        if row.get("alias")
    }
    assert record_by_alias["work_1"]["source_ref"].endswith("::work_0002")
    assert record_by_alias["work_1"]["classification"] == "direct_child"
    assert all(
        "work_0001" not in row["source_ref"]
        for row in case["record_classifications"]
        if isinstance(row.get("source_ref"), str)
    )
    assert case["alias_map"]["work"] == {"work_0002": "work_1"}
    assert set(case["alias_map"]["events"].values()) == {"event_1", "event_2"}
    assert set(case["alias_map"]["evidence"].values()) == {
        "evidence_1",
        "evidence_2",
    }
    assert case["semantic_digest"] == architecture_kernel.build_reference_execution_case(
        project,
        route_id,
        run,
        command_kind="work.create+work.run",
        before_state=before_second,
    )["semantic_digest"]


def test_reference_execution_case_handles_reversed_same_route_completion(
    tmp_path: Path,
) -> None:
    """Two same-route work items can complete out of creation order."""
    project = _scratch_project(tmp_path)
    route_id = "readme_onboarding_route"

    project_substrate.propose_routes(project)
    first = project_substrate.create_work(project, route_id)
    second = project_substrate.create_work(project, route_id)

    second_run = project_substrate.run_work(project, str(second["work_id"]))
    first_run = project_substrate.run_work(project, str(first["work_id"]))

    second_case = second_run["reference_execution_case"]
    first_case = first_run["reference_execution_case"]

    assert second_case["root_binding"]["work_id"] == "work_0002"
    assert first_case["root_binding"]["work_id"] == "work_0001"
    assert second_case["command_case_eligible"] is True
    assert first_case["command_case_eligible"] is True

    second_verification = architecture_kernel.verify_reference_execution_case(
        project,
        second_case,
    )
    first_verification = architecture_kernel.verify_reference_execution_case(
        project,
        first_case,
    )
    assert second_verification["failed_predicates"] == [
        "rendered_occurrence_refs",
        "rendered_state_delta_refs",
    ]
    assert first_verification["failed_predicates"] == [
        "rendered_occurrence_refs",
        "rendered_state_delta_refs",
    ]
    for predicate_id in [
        "join_integrity",
        "selection_binding",
        "scope_completeness",
        "execution_terminality",
        "authority_boundedness",
        "replay_equivalence",
        "state_delta_scope",
        "record_classification_matrix",
        "truth_class_authority",
        "semantic_digest",
        "assertion_matrix_coverage",
    ]:
        assert second_verification["predicate_status"][predicate_id] is True
        assert first_verification["predicate_status"][predicate_id] is True

    assert set(second_case["ambient_history_excluded"]["work_ids"]) == {"work_0001"}
    assert set(first_case["ambient_history_excluded"]["work_ids"]) == {"work_0002"}
    assert all(
        "work_0001" not in ref
        for ref in second_case["occurrence_witness_refs"]
        if isinstance(ref, str)
    )
    assert all(
        "work_0002" not in ref
        for ref in first_case["occurrence_witness_refs"]
        if isinstance(ref, str)
    )

    second_ambient_refs = {
        row["source_ref"]
        for row in second_case["ambient_history_excluded"]["records"]
    }
    first_ambient_refs = {
        row["source_ref"]
        for row in first_case["ambient_history_excluded"]["records"]
    }
    assert ".microcosm/work_items.json::work_0001" in second_ambient_refs
    assert ".microcosm/work_items.json::work_0002" in first_ambient_refs
    assert second_case["record_classification_counts"]["ambient_history"] == len(
        second_case["ambient_history_excluded"]["records"]
    )
    assert first_case["record_classification_counts"]["ambient_history"] == len(
        first_case["ambient_history_excluded"]["records"]
    )

    assert second_case["alias_map"]["work"] == {"work_0002": "work_1"}
    assert first_case["alias_map"]["work"] == {"work_0001": "work_1"}
    assert second_case["state_delta"]["new_work_ids"] == []
    assert first_case["state_delta"]["new_work_ids"] == []
