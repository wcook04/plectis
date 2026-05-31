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

    assert route["full_proof_prerequisite_command"] == "microcosm tour --card <project>"
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
    assert python_lens["command"] == "microcosm python-lens <project>"
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
    assert "microcosm serve <project>" in compiled["open_observatory"]
    assert compiled["bounded_observatory_validation"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
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
        "microcosm observe --card <project>"
    )
    assert truth_surface["observatory_surface"]["project_observe_full_command"] == (
        "microcosm observe <project>"
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
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
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


def test_cli_python_lens_defaults_to_compact_card_and_full_keeps_rows(
    capsys, tmp_path: Path
) -> None:
    project = _scratch_project(tmp_path)

    assert cli.main(["python-lens", project.as_posix()]) == 0
    card = json.loads(capsys.readouterr().out)

    assert card["schema_version"] == "microcosm_project_python_lens_card_v1"
    assert card["command"] == "microcosm python-lens <project>"
    assert card["full_lens_command"] == "microcosm python-lens --full <project>"
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
    assert full["full_lens_command"] == "microcosm python-lens --full <project>"
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
