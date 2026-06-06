from __future__ import annotations

import json
import sys
import threading
import types
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from microcosm_core import cli, runtime_shell
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _write_minimal_first_screen_cache_state(state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in {
        "project_manifest.json": '{"project_id": "project"}\n',
        "architecture.json": '{"status": "pass"}\n',
        "state_index.json": '{"status": "pass"}\n',
        "python_lens.json": '{"python_file_count": 1, "ready_route_count": 1}\n',
        "patterns.json": '{"patterns": []}\n',
        "work_items.json": '{"work_items": []}\n',
    }.items():
        path = state_dir / filename
        if not path.exists():
            path.write_text(payload, encoding="utf-8")
    events_path = state_dir / "events.jsonl"
    if not events_path.exists():
        events_path.write_text("", encoding="utf-8")
    (state_dir / "explanations").mkdir(exist_ok=True)
    (state_dir / "evidence").mkdir(exist_ok=True)


def _raise_is_file_for(
    monkeypatch: pytest.MonkeyPatch, target: Path, message: str = "metadata unavailable"
) -> None:
    original_is_file = Path.is_file

    def guarded_is_file(self: Path) -> bool:
        if self == target:
            raise OSError(message)
        return original_is_file(self)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)


def _raise_is_dir_for(
    monkeypatch: pytest.MonkeyPatch, target: Path, message: str = "metadata unavailable"
) -> None:
    original_is_dir = Path.is_dir

    def guarded_is_dir(self: Path) -> bool:
        if self == target:
            raise OSError(message)
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)


def _raise_exists_for(
    monkeypatch: pytest.MonkeyPatch, target: Path, message: str = "metadata unavailable"
) -> None:
    original_exists = Path.exists

    def guarded_exists(self: Path) -> bool:
        if self == target:
            raise OSError(message)
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", guarded_exists)


def test_cli_project_evidence_boundary_marks_unreadable_project_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _raise_exists_for(monkeypatch, project)

    boundary = cli._project_evidence_state_boundary(str(project))

    assert boundary is not None
    assert boundary["status"] == "missing_project"
    assert boundary["state_dir_exists"] is False
    assert boundary["evidence_count"] == 0


def test_cli_project_evidence_boundary_marks_unreadable_state_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    state_dir.mkdir(parents=True)
    _raise_is_dir_for(monkeypatch, state_dir)

    boundary = cli._project_evidence_state_boundary(str(project))

    assert boundary is not None
    assert boundary["status"] == "missing_state"
    assert boundary["state_dir_exists"] is False
    assert boundary["evidence_count"] == 0


def test_cli_status_card_default_proof_lab_skips_unreadable_receipt_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "proof-lab"
    receipt_path = out_dir / cli.verifier_lab_kernel.BUNDLE_RESULT_NAME
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"status": "pass"}\n', encoding="utf-8")
    _raise_is_file_for(monkeypatch, receipt_path)
    monkeypatch.setattr(cli, "DEFAULT_PROOF_LAB_OUT", str(out_dir))
    monkeypatch.setattr(
        cli,
        "_proof_lab_cached_result",
        lambda *_args, **_kwargs: pytest.fail(
            "unreadable receipt metadata should skip cache loading"
        ),
    )

    card = cli._status_card_current_default_proof_lab_card(
        {"cache_status": "stale_cached_receipt"}
    )

    assert card is None


def test_runtime_shell_jsonl_count_treats_unreadable_metadata_as_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events_path = tmp_path / "events.jsonl"
    events_path.write_text('{"status": "pass"}\n', encoding="utf-8")
    _raise_is_file_for(monkeypatch, events_path)

    assert runtime_shell._count_jsonl_dict_rows(events_path) == 0


def test_project_state_inspection_card_marks_unreadable_ref_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    _write_minimal_first_screen_cache_state(state_dir)
    ref = ".microcosm/work_items.json"
    unreadable_ref = project / ref
    _raise_is_file_for(monkeypatch, unreadable_ref)

    card = runtime_shell._project_state_inspection_card(
        project,
        first_screen_refs=[ref],
    )

    assert card["status"] == "missing_state_refs"
    assert card["state_dir_exists"] is True
    assert card["missing_first_screen_refs"] == [ref]


def test_fast_cached_project_compile_card_handles_unreadable_state_dir_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    _write_minimal_first_screen_cache_state(state_dir)
    _raise_is_dir_for(monkeypatch, state_dir)

    card = runtime_shell._fast_cached_project_compile_card(project)

    assert card["status"] == "missing_cached_state"
    assert card["cache_status"] == "missing_cache"


def test_project_status_overlay_skips_unreadable_state_ref_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    _write_minimal_first_screen_cache_state(state_dir)
    catalog = state_dir / "catalog.json"
    catalog.write_text('{"catalog": []}\n', encoding="utf-8")
    (state_dir / "routes.json").write_text(
        '{"routes": [{"route_id": "readme_onboarding_route"}]}\n',
        encoding="utf-8",
    )
    original_exists = Path.exists

    def guarded_exists(self: Path) -> bool:
        if self == catalog:
            raise OSError("metadata unavailable")
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    overlay = runtime_shell._project_status_overlay(project)

    assert overlay["status"] == "pass"
    assert ".microcosm/catalog.json" not in overlay["existing_state_refs"]
    assert ".microcosm/routes.json" in overlay["existing_state_refs"]


def test_macro_body_import_floor_treats_unreadable_target_metadata_as_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_ref = "src/demo_tool.py"
    target_path = tmp_path / target_ref
    target_path.parent.mkdir(parents=True)
    target_path.write_text("print('demo')\n", encoding="utf-8")
    protocol_path = tmp_path / runtime_shell.MACRO_PROJECTION_PROTOCOL_REF
    protocol_path.parent.mkdir(parents=True)
    protocol_path.write_text(
        json.dumps(
            {
                "copied_material": [
                    {
                        "material_id": "demo_tool",
                        "material_class": "public_macro_tool_body",
                        "target_ref": target_ref,
                        "body_copied": True,
                        "body_in_receipt": False,
                        "body_digest": "sha256:expected",
                        "body_import_verification": {
                            "verification_status": "verified",
                            "verification_mode": "exact_source_digest_match",
                            "target_body_digest": "sha256:expected",
                        },
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _raise_is_file_for(monkeypatch, target_path)

    floor = runtime_shell._macro_projection_body_import_floor(tmp_path)

    assert floor["status"] == "blocked"
    assert floor["defect_count"] == 1
    assert floor["defects"] == [
        {
            "material_id": "demo_tool",
            "material_class": "public_macro_tool_body",
            "target_ref": target_ref,
            "defect_codes": ["target_missing"],
            "body_in_receipt": False,
        }
    ]
    assert floor["body_imports"][0]["status"] == "blocked"
    assert floor["body_imports"][0]["target_digest_matches"] is False


def test_source_module_body_rows_treat_unreadable_examples_root_as_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    examples_root = tmp_path / "examples"
    examples_root.mkdir()
    _raise_is_dir_for(monkeypatch, examples_root)

    rows = runtime_shell._source_module_manifest_body_rows(
        tmp_path,
        existing_target_refs=set(),
    )

    assert rows == []


def test_proof_lab_input_files_treats_unreadable_input_metadata_as_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_ref = tmp_path / runtime_shell.PROOF_LAB_BUNDLE_REF
    input_ref.parent.mkdir(parents=True)
    input_ref.write_text("fixture\n", encoding="utf-8")
    _raise_exists_for(monkeypatch, input_ref)

    assert runtime_shell._proof_lab_input_files(tmp_path) == []


def test_verifier_lab_execution_spine_lens_falls_back_when_primary_receipt_metadata_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = tmp_path / runtime_shell.VERIFIER_EXECUTION_RECEIPT_REF
    fallback = tmp_path / runtime_shell.VERIFIER_EXECUTION_FIRST_WAVE_RECEIPT_REF
    primary.parent.mkdir(parents=True)
    fallback.parent.mkdir(parents=True)
    fallback.write_text(
        json.dumps(
            {
                "schema_version": "verifier_lab_execution_spine_validation_v1",
                "status": "blocked",
                "real_runtime_receipt": True,
                "authority_counters": {},
                "secret_exclusion_scan": {"blocking_hit_count": 0},
                "tool_versions": {},
                "lake_project_build": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _raise_is_file_for(monkeypatch, primary)
    monkeypatch.setattr(
        runtime_shell.verifier_lab_execution_spine,
        "run_execution_bundle",
        lambda *_args, **_kwargs: pytest.fail(
            "fallback receipt should avoid regenerating the execution bundle"
        ),
    )

    lens = RuntimeShell(tmp_path).verifier_lab_execution_spine_lens()

    assert (
        lens["source_receipt_ref"]
        == runtime_shell.VERIFIER_EXECUTION_FIRST_WAVE_RECEIPT_REF
    )
    assert lens["status"] == "blocked"


def test_inspect_evidence_treats_unreadable_receipt_metadata_as_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt_ref = "receipts/demo.json"
    receipt_path = tmp_path / receipt_ref
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"status": "pass"}\n', encoding="utf-8")
    _raise_is_file_for(monkeypatch, receipt_path)

    card = RuntimeShell(tmp_path).inspect_evidence(receipt_ref)

    assert card["status"] == "not_found"
    assert card["receipt_ref"] == receipt_ref


def test_cached_runtime_demo_result_treats_unreadable_cache_metadata_as_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    result_path = (
        shell.runtime_receipt_dir / "demo_project" / "demo_project_result.json"
    )
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "schema_version": "microcosm_runtime_demo_result_v1",
                "project_id": "demo_project",
                "events": [],
                "evidence_refs": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _raise_is_file_for(monkeypatch, result_path)

    assert shell._cached_runtime_demo_result("demo") is None


def test_tour_card_state_write_result_handles_unreadable_state_dir_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    state_dir.mkdir(parents=True)

    monkeypatch.setattr(
        runtime_shell,
        "_fast_cached_project_compile_card",
        lambda _project: {
            "status": "pass",
            "cache_status": "fresh_cached_state",
            "cache_source_ref": ".microcosm/state_index.json",
            "headline": "cached",
            "selected_route_id": "readme_onboarding_route",
            "route_count": 1,
            "file_count": 1,
        },
    )
    monkeypatch.setattr(
        runtime_shell,
        "_proof_lab_first_screen_card",
        lambda _root: {
            "status": "pass",
            "cache_status": "fresh_cached_receipt",
            "cache_freshness": {"status": "fresh"},
        },
    )
    monkeypatch.setattr(
        runtime_shell,
        "_macro_projection_body_import_floor_card",
        lambda _root: {"status": "pass", "source_body_import_lens": {}},
    )
    monkeypatch.setattr(
        RuntimeShell,
        "workingness_card",
        lambda _self: {
            "status": "pass",
            "card_status": "clear",
            "command": "microcosm workingness --card",
            "surface_counts": {},
        },
    )
    monkeypatch.setattr(
        runtime_shell,
        "_cold_reader_first_screen_card",
        lambda **_kwargs: {
            "status": "pass",
            "primary_command": "microcosm tour --card <project>",
            "reader_routes_ref": "atlas/entry_packet.json::reader_first_screen_routes",
            "selected_route_id": "readme_onboarding_route",
            "minimal_command_path": [],
            "generated_state": {
                "state_dir": ".microcosm",
                "refs": [".microcosm/routes.json"],
                "source_files_mutated": False,
            },
            "behavior_surfaces": {
                "route_state_ref": ".microcosm/routes.json",
                "observatory_bounded_validation_command": "microcosm serve <project>",
            },
            "route_explanation": {"endpoint": "/project/explain/readme_onboarding_route"},
            "proof_surface": {"route_id": "readme_onboarding_route"},
        },
    )
    monkeypatch.setattr(
        runtime_shell.first_screen_composition,
        "first_screen_composition_card",
        lambda *_args, **_kwargs: {"status": "pass"},
    )
    monkeypatch.setattr(
        runtime_shell,
        "_compact_first_contact_surface_refs",
        lambda _card: {
            "required_surface_ids": ["route"],
            "surface_count": 1,
            "surfaces": {"route": {"state_ref": ".microcosm/routes.json"}},
            "safe_to_show": {"source_files_mutated": False},
        },
    )
    monkeypatch.setattr(
        runtime_shell,
        "_project_state_inspection_card",
        lambda *_args, **_kwargs: {
            "status": "pass",
            "state_dir": ".microcosm",
            "state_dir_exists": True,
            "state_file_count": 1,
            "state_ref_count": 1,
            "inspect_command": "find <project>/.microcosm -maxdepth 2 -type f | sort",
            "route_state_json_check_command": (
                "python3 -m json.tool <project>/.microcosm/routes.json"
            ),
        },
    )
    monkeypatch.setattr(runtime_shell, "_runtime_receipt_write_persists", lambda _path: False)
    monkeypatch.setattr(
        runtime_shell,
        "_tracked_receipt_refresh_requires_env",
        lambda _path: False,
    )
    monkeypatch.setattr(runtime_shell, "_tracked_receipt_refresh_env", lambda _path: None)
    original_is_dir = Path.is_dir

    def guarded_is_dir(self: Path) -> bool:
        if self == state_dir:
            raise OSError("metadata unavailable")
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)

    card = RuntimeShell(MICROCOSM_ROOT).tour_card(project)

    assert card["state_write_result"]["state_dir_exists"] is False


def _accepted_registry_runner_refs() -> dict[str, str]:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    return {
        str(row["organ_id"]): str(row["runner"])
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    }


def test_runtime_shell_lazy_attr_uses_parent_module_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "microcosm_core._lazy_runtime_shell_test_module"
    module = types.ModuleType(module_name)
    call_results: list[str] = []

    def answer() -> str:
        call_results.append("called")
        return "ok"

    module.answer = answer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, module_name, module)
    original_import_module = runtime_shell.importlib.import_module
    import_calls: list[str] = []

    def import_spy(name: str, package: str | None = None) -> object:
        if name == module_name:
            import_calls.append(name)
        return original_import_module(name, package)

    monkeypatch.setattr(runtime_shell.importlib, "import_module", import_spy)

    lazy_module = runtime_shell._LazyModule(module_name)
    lazy_attr = lazy_module.answer

    assert import_calls == []
    assert lazy_attr() == "ok"
    assert lazy_attr() == "ok"
    assert import_calls == [module_name]
    assert call_results == ["called", "called"]


def test_runtime_shell_binds_accepted_organ_modules_from_registry() -> None:
    runner_refs = _accepted_registry_runner_refs()

    assert runner_refs == runtime_shell.RUNTIME_ORGAN_RUNNER_MODULE_REFS
    assert {step.organ_id for step in runtime_shell.RUNTIME_STEPS} == set(runner_refs)

    fresh_bindings = runtime_shell._lazy_organ_module_bindings(runner_refs)
    for organ_id, module_ref in runner_refs.items():
        lazy_module = getattr(runtime_shell, organ_id)
        assert isinstance(lazy_module, runtime_shell._LazyModule)
        assert lazy_module.module_name == module_ref
        fresh_module = fresh_bindings[organ_id]
        assert fresh_module.module_name == module_ref
        assert fresh_module.loaded is False

    assimilation = next(
        step
        for step in runtime_shell.RUNTIME_STEPS
        if step.organ_id == "pattern_assimilation_step"
    )
    assert isinstance(assimilation.runner, runtime_shell._LazyAttr)
    assert runtime_shell.pattern_assimilation_step.module_name == (
        "microcosm_core.validators.acceptance"
    )


def _read_server_json(server: object, path: str) -> dict[str, object]:
    host, port = getattr(server, "server_address")
    with urlopen(f"http://{host}:{port}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_server_json(server: object, path: str) -> dict[str, object]:
    host, port = getattr(server, "server_address")
    with urlopen(f"http://{host}:{port}{path}", data=b"", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_runtime_evidence_count_streams_receipts_without_rglob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipts_dir = tmp_path / "receipts"
    (receipts_dir / "nested").mkdir(parents=True)
    (receipts_dir / "runtime.json").write_text("{}", encoding="utf-8")
    (receipts_dir / "nested" / "proof.json").write_text("{}", encoding="utf-8")
    (receipts_dir / "nested" / "notes.txt").write_text("skip", encoding="utf-8")

    original_rglob = Path.rglob

    def fail_if_rglobbed(self: Path, *_args: object, **_kwargs: object) -> object:
        if self == receipts_dir:
            raise AssertionError("evidence_count should stream receipt counting")
        return original_rglob(self, *_args, **_kwargs)

    monkeypatch.setattr(Path, "rglob", fail_if_rglobbed)

    assert RuntimeShell(tmp_path).evidence_count() == 2


def test_runtime_evidence_count_skips_symlinked_json_files(tmp_path: Path) -> None:
    receipts_dir = tmp_path / "receipts"
    receipts_dir.mkdir()
    (receipts_dir / "direct.json").write_text("{}", encoding="utf-8")
    outside_receipt = tmp_path / "outside.json"
    outside_receipt.write_text("{}", encoding="utf-8")
    try:
        (receipts_dir / "linked.json").symlink_to(outside_receipt)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    assert RuntimeShell(tmp_path).evidence_count() == 1


def test_fast_cached_project_compile_card_streams_evidence_count_without_glob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    evidence_dir = state_dir / "evidence"
    (evidence_dir / "nested").mkdir(parents=True)
    _write_minimal_first_screen_cache_state(state_dir)
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
    assert card["evidence_count"] == 2


def test_project_compile_card_streams_evidence_count_without_glob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    evidence_dir = state_dir / "evidence"
    explanation_dir = state_dir / "explanations"
    (evidence_dir / "nested").mkdir(parents=True)
    explanation_dir.mkdir(parents=True)
    (state_dir / "catalog.json").write_text(
        '{"file_count": 1, "role_counts": {"readme": 1}, "source_fingerprint": "fp"}\n',
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
    (state_dir / "project_manifest.json").write_text(
        '{"status": "pass"}\n',
        encoding="utf-8",
    )
    (state_dir / "architecture.json").write_text(
        '{"status": "pass"}\n',
        encoding="utf-8",
    )
    (state_dir / "python_lens.json").write_text(
        '{"python_file_count": 1, "ready_route_count": 1}\n',
        encoding="utf-8",
    )
    (state_dir / "patterns.json").write_text('{"patterns": []}\n', encoding="utf-8")
    (state_dir / "state_index.json").write_text(
        '{"status": "pass"}\n',
        encoding="utf-8",
    )
    (state_dir / "work_items.json").write_text(
        '{"work_items": [{"work_id": "work_1", "route_id": "readme_onboarding_route", "status": "closed"}]}\n',
        encoding="utf-8",
    )
    (state_dir / "events.jsonl").write_text(
        '{"event_id": "event_1", "span": "compile", "status": "pass"}\n',
        encoding="utf-8",
    )
    (explanation_dir / "readme_onboarding_route.json").write_text(
        '{"status": "pass"}\n',
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
            raise AssertionError("project compile card should stream evidence counting")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fail_if_globbed)

    card = runtime_shell.project_substrate.compile_project_card(project)

    assert card["status"] == "pass"
    assert card["evidence_count"] == 2
    assert (
        card["truth_readiness_surface"]["truth_accounting"]["evidence_refs_present"]
        is True
    )


def test_fast_cached_project_compile_card_streams_event_count_without_rows_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    state_dir = project / ".microcosm"
    state_dir.mkdir(parents=True)
    _write_minimal_first_screen_cache_state(state_dir)
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
    assert card["event_count"] == 25


def test_runtime_shell_patterns_streams_projection_without_source_rows_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = (
        tmp_path
        / "examples/pattern_binding_contract/exported_substrate_bundle/pattern_rows.jsonl"
    )
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "pattern_id": "pattern_one",
                        "organ_id": "organ_one",
                        "title": "Pattern One",
                        "public_projection_posture": "source_open",
                        "source_refs": ["source_a", "source_b"],
                    }
                ),
                json.dumps(
                    {
                        "pattern_id": "pattern_two",
                        "projection_mode": "metadata_only",
                        "source_refs": "not-a-list",
                    }
                ),
                json.dumps(["skip non-object rows"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def fail_read_jsonl(_path: Path) -> list[dict[str, object]]:
        raise AssertionError("RuntimeShell.patterns should stream pattern rows")

    monkeypatch.setattr(runtime_shell, "_read_jsonl", fail_read_jsonl)

    assert RuntimeShell(tmp_path).patterns() == [
        {
            "pattern_id": "pattern_one",
            "organ_id": "organ_one",
            "title": "Pattern One",
            "projection_posture": "source_open",
            "source_ref_count": 2,
        },
        {
            "pattern_id": "pattern_two",
            "organ_id": None,
            "title": None,
            "projection_posture": "metadata_only",
            "source_ref_count": 0,
        },
    ]


def test_runtime_count_files_under_missing_root_is_zero(tmp_path: Path) -> None:
    assert runtime_shell._count_files_under(tmp_path / "missing") == 0


def test_runtime_shell_evidence_list_limit_bounds_receipt_summaries(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    receipt_root = public_root / "receipts"
    (receipt_root / "runtime_shell/demo").mkdir(parents=True)
    for index in range(5):
        (receipt_root / "runtime_shell/demo" / f"result_{index}.json").write_text(
            json.dumps({"status": "pass", "organ_id": f"demo_{index}"}) + "\n",
            encoding="utf-8",
        )
    summarized_refs: list[str] = []

    def compact_summary(path: Path, root: Path) -> dict[str, object]:
        summarized_refs.append(path.relative_to(root).as_posix())
        return {
            "receipt_ref": summarized_refs[-1],
            "status": "pass",
        }

    monkeypatch.setattr(
        runtime_shell.runtime_evidence_index,
        "compact_receipt_summary",
        compact_summary,
    )

    assert (
        runtime_shell.main(["evidence", "list", "--limit", "2"], root=public_root)
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["receipt_count"] == 5
    assert payload["returned_receipt_count"] == 2
    assert payload["limit"] == 2
    assert payload["truncated"] is True
    assert summarized_refs == [
        "receipts/runtime_shell/demo/result_0.json",
        "receipts/runtime_shell/demo/result_1.json",
    ]


def test_standards_control_counts_fixture_manifests_without_materializing_glob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    manifests_root = public_root / "core/fixture_manifests"
    manifests_root.mkdir(parents=True)
    manifest_paths = []
    for index in range(3):
        path = manifests_root / f"organ_{index}.fixture_manifest.json"
        path.write_text('{"status": "pass"}\n', encoding="utf-8")
        manifest_paths.append(path)

    class NoLengthHintIterable:
        def __iter__(self):
            return iter(manifest_paths)

        def __length_hint__(self) -> int:
            raise AssertionError(
                "standards_control should stream fixture manifest counting"
            )

    original_glob = Path.glob

    def glob_spy(self: Path, pattern: str):
        if self == manifests_root and pattern == "*.fixture_manifest.json":
            return NoLengthHintIterable()
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", glob_spy)

    lens = RuntimeShell(public_root).standards_control()

    assert lens["standards_summary"]["fixture_manifest_count"] == 3


def test_runtime_shell_evidence_list_rejects_negative_limit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        runtime_shell.main(["evidence", "list", "--limit", "-1"])

    assert excinfo.value.code == 2
    assert "argument --limit: must be >= 0" in capsys.readouterr().err


def test_runtime_shell_serve_evidence_endpoint_defaults_to_compact_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    observed_limits: list[int | None] = []

    def evidence_index(*, limit: int | None = None) -> dict[str, object]:
        observed_limits.append(limit)
        return {"status": "pass", "limit": limit, "evidence": []}

    monkeypatch.setattr(shell, "evidence_index", evidence_index)
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        default_payload = _read_server_json(server, "/evidence")
        limited_payload = _read_server_json(server, "/evidence?limit=2")
        full_payload = _read_server_json(server, "/evidence?limit=0")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert default_payload["limit"] == runtime_shell.DEFAULT_EVIDENCE_LIST_LIMIT
    assert limited_payload["limit"] == 2
    assert full_payload["limit"] is None
    assert observed_limits == [runtime_shell.DEFAULT_EVIDENCE_LIST_LIMIT, 2, None]


def test_runtime_shell_serve_project_evidence_endpoint_accepts_query_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    observed_limits: list[int | None] = []

    def list_evidence(
        project_path: str | Path,
        *,
        limit: int | None = None,
    ) -> dict[str, object]:
        observed_limits.append(limit)
        return {
            "status": "pass",
            "project_ref": Path(project_path).name,
            "limit": limit,
            "evidence": [],
        }

    monkeypatch.setattr(runtime_shell.project_substrate, "list_evidence", list_evidence)
    server = shell.serve("127.0.0.1", 0, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        default_payload = _read_server_json(server, "/project/evidence")
        limited_payload = _read_server_json(server, "/project/evidence?limit=3")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert default_payload["limit"] == runtime_shell.DEFAULT_EVIDENCE_LIST_LIMIT
    assert limited_payload["limit"] == 3
    assert observed_limits == [runtime_shell.DEFAULT_EVIDENCE_LIST_LIMIT, 3]


def test_runtime_shell_serve_uses_tight_shutdown_poll_interval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    server = shell.serve("127.0.0.1", 0)
    try:
        assert server.serve_forever.__func__.__defaults__ == (
            runtime_shell.RUNTIME_SHELL_SERVE_FOREVER_POLL_INTERVAL,
        )
        assert runtime_shell.RUNTIME_SHELL_SERVE_FOREVER_POLL_INTERVAL <= 0.05
        assert getattr(server, "daemon_threads") is True
        assert getattr(server, "block_on_close") is False
    finally:
        server.server_close()


def test_runtime_shell_serve_status_endpoint_reuses_project_status_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    expected_project_ref = runtime_shell._public_project_command_ref(
        project.resolve(strict=False),
        tmp_path,
    )
    status_calls: list[tuple[Path | None, str | Path | None]] = []

    def status(
        project_path: str | Path | None = None,
        *,
        project_ref: str | Path | None = None,
    ) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        status_calls.append((resolved_project, project_ref))
        return {
            "status": "pass",
            "project_ref": str(project_ref),
            "project_front_door_status": {"status": "pass"},
            "status_card": {"project_ref": str(project_ref)},
        }

    def fail_project_status_overlay(_project_path: Path) -> dict[str, object]:
        raise AssertionError("/status should call status(project), not overlay directly")

    monkeypatch.setattr(shell, "status", status)
    monkeypatch.setattr(
        runtime_shell,
        "_project_status_overlay",
        fail_project_status_overlay,
    )
    server = shell.serve("127.0.0.1", 0, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _read_server_json(server, "/status")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert payload["project_ref"] == expected_project_ref
    assert payload["status_card"]["project_ref"] == expected_project_ref
    assert status_calls == [(project.resolve(strict=False), expected_project_ref)]


def test_runtime_shell_serve_project_status_card_reuses_status_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    expected_project_ref = runtime_shell._public_project_command_ref(
        project.resolve(strict=False),
        tmp_path,
    )
    status_calls: list[tuple[Path | None, str | Path | None]] = []
    status_card_calls: list[tuple[Path | None, str | Path | None]] = []
    tour_card_calls: list[Path] = []

    def status(
        project_path: str | Path | None = None,
        *,
        project_ref: str | Path | None = None,
    ) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        status_calls.append((resolved_project, project_ref))
        return {
            "status": "pass",
            "project_ref": str(project_ref),
            "status_card": {
                "status": "pass",
                "project_ref": str(project_ref),
                "source": "full_status_payload",
            },
        }

    def status_card(
        project_path: str | Path | None = None,
        *,
        project_ref: str | Path | None = None,
    ) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        status_card_calls.append((resolved_project, project_ref))
        raise AssertionError("/project/status should reuse cached /status card")

    def tour_card(project_path: str | Path | None = None) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        if resolved_project is not None:
            tour_card_calls.append(resolved_project)
        return {"status": "pass", "source": "tour_card"}

    monkeypatch.setattr(shell, "status", status)
    monkeypatch.setattr(shell, "status_card", status_card)
    monkeypatch.setattr(shell, "tour_card", tour_card)
    server = shell.serve("127.0.0.1", 0, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        payload = _read_server_json(server, "/status")
        card = _read_server_json(server, "/project/status")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert payload["project_ref"] == expected_project_ref
    assert card == payload["status_card"]
    assert card["source"] == "full_status_payload"
    assert status_calls == [(project.resolve(strict=False), expected_project_ref)]
    assert status_card_calls == []
    assert tour_card_calls == [project.resolve(strict=False)]


def test_runtime_shell_serve_project_observatory_reuses_cached_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    expected_project_ref = runtime_shell._public_project_command_ref(
        project.resolve(strict=False),
        tmp_path,
    )
    served_status_payload = {
        "status": "pass",
        "project_ref": expected_project_ref,
        "status_card": {
            "status": "pass",
            "project_ref": expected_project_ref,
            "source": "full_status_payload",
        },
    }
    served_tour_payload = {
        "status": "pass",
        "selected_route_id": "readme_onboarding_route",
        "source": "tour_card",
    }
    status_calls: list[tuple[Path | None, str | Path | None]] = []
    tour_card_calls: list[Path | None] = []
    observatory_calls: list[dict[str, object]] = []

    def status(
        project_path: str | Path | None = None,
        *,
        project_ref: str | Path | None = None,
    ) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        status_calls.append((resolved_project, project_ref))
        return served_status_payload

    def tour_card(project_path: str | Path | None = None) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        tour_card_calls.append(resolved_project)
        return served_tour_payload

    def project_observatory(
        project_path: str | Path | None = None,
        *,
        persist_receipts: bool = True,
        tour_payload_mode: str = "full",
        tour_payload: dict[str, object] | None = None,
        status_payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        observatory_calls.append(
            {
                "project_path": resolved_project,
                "persist_receipts": persist_receipts,
                "tour_payload_mode": tour_payload_mode,
                "tour_payload": tour_payload,
                "status_payload": status_payload,
            }
        )
        return {
            "schema_version": "microcosm_project_observatory_v1",
            "status": "pass",
            "tour": tour_payload,
            "runtime_status": {
                "status": "pass",
                "status_card": (
                    status_payload.get("status_card")
                    if isinstance(status_payload, dict)
                    else {}
                ),
            },
        }

    monkeypatch.setattr(shell, "status", status)
    monkeypatch.setattr(shell, "tour_card", tour_card)
    monkeypatch.setattr(shell, "project_observatory", project_observatory)
    server = shell.serve("127.0.0.1", 0, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        status_payload = _read_server_json(server, "/status")
        tour_payload = _read_server_json(server, "/tour")
        observatory_payload = _read_server_json(server, "/project/observatory")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert status_payload is not served_status_payload
    assert status_payload == served_status_payload
    assert tour_payload == served_tour_payload
    assert observatory_payload["tour"] == served_tour_payload
    assert status_calls == [(project.resolve(strict=False), expected_project_ref)]
    assert tour_card_calls == [project.resolve(strict=False)]
    assert len(observatory_calls) == 1
    observatory_call = observatory_calls[0]
    assert observatory_call["project_path"] == project.resolve(strict=False)
    assert observatory_call["persist_receipts"] is False
    assert observatory_call["tour_payload_mode"] == "card"
    assert observatory_call["tour_payload"] is served_tour_payload
    assert observatory_call["status_payload"] is served_status_payload


def test_project_observatory_reuses_precomputed_lenses_for_bridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    call_counts: dict[str, int] = {}

    def counted_payload(name: str, payload: dict[str, object]):
        def read_model(*_args: object, **_kwargs: object) -> dict[str, object]:
            call_counts[name] = call_counts.get(name, 0) + 1
            return {"status": "pass", **payload}

        return read_model

    shared_lens_payloads: dict[str, dict[str, object]] = {
        "intake": {
            "cell_status": [],
            "runtime_bridge_evidence_refs": ["intake_ref.json"],
            "projection_status_counts": {},
            "open_actionable_cell_count": 0,
            "landed_cell_count": 0,
            "consumed_cell_count": 0,
        },
        "reveal": {
            "evidence_ref": "reveal_ref.json",
            "time_budget_minutes": 10,
            "step_count": 1,
            "evidence_ref_count": 1,
        },
        "market_boundary": {"market_boundary_lens_ref": "market_ref.json"},
        "trace_lens": {"trace_lens_ref": "trace_ref.json"},
        "repair_loop": {"repair_loop_ref": "repair_ref.json"},
        "evidence_cells": {"evidence_cell_lens_ref": "evidence_ref.json"},
        "proof_loop_depth": {"proof_loop_depth_ref": "proof_loop_ref.json"},
        "landing_replay": {"landing_replay_ref": "landing_ref.json"},
        "view_quality": {"view_quality_lens_ref": "view_quality_ref.json"},
        "projection_safety": {"projection_safety_lens_ref": "safety_ref.json"},
        "projection_drift": {"projection_drift_lens_ref": "drift_ref.json"},
        "route_cleanup": {"route_cleanup_lens_ref": "cleanup_ref.json"},
        "projection_import_map": {
            "projection_import_map_ref": "import_map_ref.json"
        },
        "import_projector": {"import_projector_ref": "projector_ref.json"},
        "option_surface_lens": {"option_surface_lens_ref": "option_ref.json"},
        "stripping_guard": {"stripping_guard_ref": "guard_ref.json"},
        "standards_control": {"standards_control_ref": "standards_ref.json"},
        "hook_coverage": {
            "hook_intervention_coverage_lens_ref": "hook_ref.json"
        },
        "replay_gauntlet": {"replay_gauntlet_lens_ref": "replay_ref.json"},
        "benchmark_lab": {"benchmark_lab_ref": "benchmark_ref.json"},
        "legibility_scorecard": {
            "legibility_scorecard_ref": "legibility_ref.json"
        },
    }
    for method_name, payload in shared_lens_payloads.items():
        monkeypatch.setattr(
            shell,
            method_name,
            counted_payload(method_name, payload),
        )
    monkeypatch.setattr(
        shell,
        "prediction_lens",
        counted_payload("prediction_lens", {"prediction_lens_ref": "prediction.json"}),
    )
    monkeypatch.setattr(
        shell,
        "corpus_lens",
        counted_payload("corpus_lens", {"corpus_lens_ref": "corpus.json"}),
    )
    monkeypatch.setattr(
        runtime_shell.architecture_kernel,
        "load_kernel_manifest",
        lambda _root: {"primitives": []},
    )
    monkeypatch.setattr(
        runtime_shell.architecture_kernel,
        "load_standard_pressure_surface",
        lambda _root: {},
    )

    payload = shell.project_observatory(
        project=None,
        persist_receipts=False,
        tour_payload={"status": "pass", "front_door_status": {"status": "pass"}},
        status_payload={"status": "pass", "status_card": {"status": "pass"}},
    )

    assert payload["runtime_bridge"]["status"] == "pass"
    assert payload["runtime_bridge"]["reveal_summary"]["status"] == "pass"
    for method_name in shared_lens_payloads:
        assert call_counts[method_name] == 1
    assert call_counts["prediction_lens"] == 1
    assert call_counts["corpus_lens"] == 1


def test_runtime_shell_serve_demo_run_uses_served_project_and_clears_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    resolved_project = project.resolve(strict=False)
    expected_project_ref = runtime_shell._public_project_command_ref(
        resolved_project,
        tmp_path,
    )
    status_calls: list[tuple[Path | None, str | Path | None]] = []
    run_demo_calls: list[Path] = []

    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    monkeypatch.setattr(
        shell,
        "tour_card",
        lambda project_path=None: {"status": "pass", "project": str(project_path)},
    )

    def status(
        project_path: str | Path | None = None,
        *,
        project_ref: str | Path | None = None,
    ) -> dict[str, object]:
        resolved = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        status_calls.append((resolved, project_ref))
        generation = len(status_calls)
        return {
            "status": "pass",
            "project_ref": str(project_ref),
            "status_card": {
                "status": "pass",
                "project_ref": str(project_ref),
                "generation": generation,
            },
        }

    def run_demo(
        project_path: str | Path = runtime_shell.DEFAULT_PROJECT_REL,
        *,
        command: str | None = None,
    ) -> dict[str, object]:
        del command
        resolved = Path(project_path).resolve(strict=False)
        run_demo_calls.append(resolved)
        return {
            "status": "pass",
            "project_ref": runtime_shell._public_project_command_ref(
                resolved,
                tmp_path,
            ),
        }

    monkeypatch.setattr(shell, "status", status)
    monkeypatch.setattr(shell, "run_demo", run_demo)
    server = shell.serve("127.0.0.1", 0, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        first_status = _read_server_json(server, "/status")
        first_card = _read_server_json(server, "/project/status")
        demo_result = _post_server_json(server, "/demo/run")
        second_status = _read_server_json(server, "/status")
        second_card = _read_server_json(server, "/project/status")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert demo_result["project_ref"] == expected_project_ref
    assert first_status["status_card"] == first_card
    assert second_status["status_card"] == second_card
    assert first_card["generation"] == 1
    assert second_card["generation"] == 2
    assert run_demo_calls == [resolved_project]
    assert status_calls == [
        (resolved_project, expected_project_ref),
        (resolved_project, expected_project_ref),
    ]


def test_runtime_shell_serve_global_tour_endpoint_caches_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    served_tour_payload = {
        "status": "pass",
        "selected_route_id": "default_route",
        "source": "global_tour",
    }
    tour_calls: list[Path] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    def tour(project_path: str | Path | None = None, **_kwargs: object) -> dict[str, object]:
        tour_calls.append(Path(project_path).resolve(strict=False))
        return served_tour_payload

    monkeypatch.setattr(shell, "tour", tour)
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        first_payload = _read_server_json(server, "/tour")
        second_payload = _read_server_json(server, "/tour")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert first_payload == served_tour_payload
    assert second_payload == served_tour_payload
    assert tour_calls == [Path(runtime_shell.DEFAULT_PROJECT_REL).resolve(strict=False)]


def test_runtime_shell_serve_global_observatory_primes_tour_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    served_tour_payload = {
        "status": "pass",
        "selected_route_id": "observatory_route",
        "source": "observatory_model",
    }
    observatory_calls: list[dict[str, object]] = []
    tour_calls: list[Path | None] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    def project_observatory(
        project_path: str | Path | None = None,
        *,
        persist_receipts: bool = True,
        tour_payload_mode: str = "full",
        tour_payload: dict[str, object] | None = None,
        status_payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        observatory_calls.append(
            {
                "project_path": project_path,
                "persist_receipts": persist_receipts,
                "tour_payload_mode": tour_payload_mode,
                "tour_payload": tour_payload,
                "status_payload": status_payload,
            }
        )
        return {
            "schema_version": "microcosm_project_observatory_v1",
            "status": "pass",
            "tour": served_tour_payload,
        }

    def observatory_html(
        project_path: str | Path | None = None,
        *,
        model: dict[str, object] | None = None,
    ) -> str:
        assert project_path is None
        assert isinstance(model, dict)
        assert model["tour"] is served_tour_payload
        return "<!doctype html><title>Microcosm Observatory</title>"

    def tour(project_path: str | Path | None = None, **_kwargs: object) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        tour_calls.append(resolved_project)
        raise AssertionError("/tour should reuse the root observatory tour payload")

    monkeypatch.setattr(shell, "project_observatory", project_observatory)
    monkeypatch.setattr(shell, "_observatory_html", observatory_html)
    monkeypatch.setattr(shell, "tour", tour)
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = getattr(server, "server_address")
        with urlopen(f"http://{host}:{port}/", timeout=5) as response:
            root_html = response.read().decode("utf-8")
        tour_payload = _read_server_json(server, "/tour")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert "Microcosm Observatory" in root_html
    assert tour_payload == served_tour_payload
    assert tour_calls == []
    assert observatory_calls == [
        {
            "project_path": None,
            "persist_receipts": False,
            "tour_payload_mode": "full",
            "tour_payload": None,
            "status_payload": None,
        }
    ]


def test_runtime_shell_serve_spine_endpoints_cache_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    served_spine = {
        "schema_version": "microcosm_public_runtime_spine_v1",
        "status": "pass",
        "source": "spine",
    }
    served_card = {
        "schema_version": "microcosm_public_runtime_spine_card_v1",
        "status": "pass",
        "source": "spine_card",
    }
    spine_calls: list[str] = []
    spine_card_calls: list[str] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    def spine() -> dict[str, object]:
        spine_calls.append("spine")
        return served_spine

    def spine_card() -> dict[str, object]:
        spine_card_calls.append("spine_card")
        return served_card

    monkeypatch.setattr(shell, "spine", spine)
    monkeypatch.setattr(shell, "spine_card", spine_card)
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        first_spine = _read_server_json(server, "/spine")
        second_spine = _read_server_json(server, "/spine")
        first_card = _read_server_json(server, "/spine-card")
        second_card = _read_server_json(server, "/spine-card")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert first_spine == served_spine
    assert second_spine == served_spine
    assert first_card == served_card
    assert second_card == served_card
    assert spine_calls == ["spine"]
    assert spine_card_calls == ["spine_card"]


def test_runtime_shell_serve_runtime_lens_endpoints_cache_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    served_prediction = {
        "schema_version": "microcosm_public_prediction_lens_v1",
        "status": "pass",
        "source": "prediction",
    }
    served_proof_lab = {
        "schema_version": "microcosm_public_verifier_lab_kernel_lens_v1",
        "status": "pass",
        "source": "proof_lab",
    }
    served_intake_card = {
        "schema_version": "microcosm_runtime_reveal_import_bridge_card_v1",
        "status": "pass",
        "source": "intake_card",
    }
    prediction_calls: list[str] = []
    proof_lab_calls: list[str] = []
    intake_card_calls: list[str] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    def prediction_lens() -> dict[str, object]:
        prediction_calls.append("prediction")
        return served_prediction

    def proof_lab() -> dict[str, object]:
        proof_lab_calls.append("proof_lab")
        return served_proof_lab

    def intake_card() -> dict[str, object]:
        intake_card_calls.append("intake_card")
        return served_intake_card

    monkeypatch.setattr(shell, "prediction_lens", prediction_lens)
    monkeypatch.setattr(shell, "proof_lab", proof_lab)
    monkeypatch.setattr(shell, "intake_card", intake_card)
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        first_prediction = _read_server_json(server, "/prediction")
        second_prediction = _read_server_json(server, "/prediction")
        proof_lab_payload = _read_server_json(server, "/proof-lab")
        verifier_alias_payload = _read_server_json(server, "/verifier-lab-kernel")
        first_intake_card = _read_server_json(server, "/intake-card")
        second_intake_card = _read_server_json(server, "/intake-card")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert first_prediction == served_prediction
    assert second_prediction == served_prediction
    assert proof_lab_payload == served_proof_lab
    assert verifier_alias_payload == served_proof_lab
    assert first_intake_card == served_intake_card
    assert second_intake_card == served_intake_card
    assert prediction_calls == ["prediction"]
    assert proof_lab_calls == ["proof_lab"]
    assert intake_card_calls == ["intake_card"]


def test_runtime_shell_serve_project_view_endpoints_cache_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    resolved_project = project.resolve(strict=False)
    builder_calls: dict[str, list[dict[str, object]]] = {
        "observe": [],
        "architecture": [],
        "graph": [],
        "catalog": [],
        "python_lens": [],
        "patterns": [],
        "routes": [],
    }
    workitem_calls: list[Path] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    def builder(name: str):
        def _build(project_path: str | Path, **kwargs: object) -> dict[str, object]:
            builder_calls[name].append(
                {
                    "project_path": Path(project_path).resolve(strict=False),
                    "kwargs": kwargs,
                }
            )
            return {"status": "pass", "source": name}

        return _build

    def load_work_items(project_path: str | Path) -> list[dict[str, object]]:
        workitem_calls.append(Path(project_path).resolve(strict=False))
        return [{"work_id": "cached_project_work"}]

    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "observe_project",
        builder("observe"),
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "architecture_project",
        builder("architecture"),
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "state_graph",
        builder("graph"),
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "catalog_project",
        builder("catalog"),
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "python_lens_card",
        builder("python_lens"),
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "discover_patterns",
        builder("patterns"),
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "propose_routes",
        builder("routes"),
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "_load_work_items",
        load_work_items,
    )
    server = shell.serve("127.0.0.1", 0, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        first_payloads = {
            path: _read_server_json(server, path)
            for path in (
                "/project/observe",
                "/project/architecture",
                "/project/graph",
                "/project/catalog",
                "/project/python-lens",
                "/project/patterns",
                "/project/routes",
                "/project/workitems",
            )
        }
        second_payloads = {
            path: _read_server_json(server, path) for path in first_payloads
        }
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert second_payloads == first_payloads
    assert first_payloads["/project/observe"] == {"status": "pass", "source": "observe"}
    assert first_payloads["/project/architecture"] == {
        "status": "pass",
        "source": "architecture",
    }
    assert first_payloads["/project/graph"] == {"status": "pass", "source": "graph"}
    assert first_payloads["/project/catalog"] == {
        "status": "pass",
        "source": "catalog",
    }
    assert first_payloads["/project/python-lens"] == {
        "status": "pass",
        "source": "python_lens",
    }
    assert first_payloads["/project/patterns"] == {
        "status": "pass",
        "source": "patterns",
    }
    assert first_payloads["/project/routes"] == {"status": "pass", "source": "routes"}
    assert first_payloads["/project/workitems"] == {
        "schema_version": "microcosm_project_workitems_view_v1",
        "status": "pass",
        "work_items": [{"work_id": "cached_project_work"}],
    }
    assert builder_calls["observe"] == [
        {
            "project_path": resolved_project,
            "kwargs": {"refresh_architecture": False},
        }
    ]
    for name in (
        "architecture",
        "graph",
        "catalog",
        "python_lens",
        "patterns",
        "routes",
    ):
        assert builder_calls[name] == [
            {
                "project_path": resolved_project,
                "kwargs": {},
            }
        ]
    assert workitem_calls == [resolved_project]


def test_runtime_shell_project_landing_primes_project_view_endpoint_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    resolved_project = project.resolve(strict=False)
    observe_payload = {
        "status": "pass",
        "causal_chain": {
            "events": [{"event_id": "event_1"}],
            "evidence_refs": ["evidence/project.json"],
            "graph": {
                "node_count": 1,
                "edge_count": 1,
                "graph_ref": ".microcosm/graph.json",
            },
        },
    }
    work_rows = [
        {
            "work_id": "work_1",
            "status": "closed",
            "route_id": "route_1",
            "event_refs": ["event_1"],
            "evidence_refs": ["evidence/project.json"],
            "source_files_mutated": False,
        }
    ]
    observe_calls: list[dict[str, object]] = []
    workitem_calls: list[Path] = []
    tour_card_calls: list[Path] = []
    status_card_calls: list[Path] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    monkeypatch.setattr(
        runtime_shell.first_screen_composition,
        "first_screen_composition_card",
        lambda root, project_label="<project>": {
            "status": "pass",
            "human_first_command": "microcosm hello <project>",
            "shared_first_command": "microcosm status <project>",
        },
    )
    monkeypatch.setattr(
        runtime_shell.first_screen_composition,
        "first_screen_compact_card",
        lambda card: {
            "status": card.get("status"),
            "human_first_command": card.get("human_first_command"),
            "shared_first_command": card.get("shared_first_command"),
        },
    )

    def observe_project(
        project_path: str | Path,
        *,
        refresh_architecture: bool = True,
    ) -> dict[str, object]:
        observe_calls.append(
            {
                "project_path": Path(project_path).resolve(strict=False),
                "refresh_architecture": refresh_architecture,
            }
        )
        return observe_payload

    def load_work_items(project_path: str | Path) -> list[dict[str, object]]:
        workitem_calls.append(Path(project_path).resolve(strict=False))
        return work_rows

    def tour_card(project_path: str | Path | None = None) -> dict[str, object]:
        assert project_path is not None
        tour_card_calls.append(Path(project_path).resolve(strict=False))
        return {"status": "pass", "selected_route_id": "route_1"}

    def status_card(
        project_path: str | Path | None = None,
        *,
        project_ref: str | Path | None = None,
    ) -> dict[str, object]:
        assert project_path is not None
        status_card_calls.append(Path(project_path).resolve(strict=False))
        return {
            "status": "pass",
            "project_ref": str(project_ref),
            "front_door": {
                "project_ref": str(project_ref),
                "selected_route_id": "route_1",
                "project_state": {
                    "status": "pass",
                    "state_dir_exists": True,
                    "existing_state_refs": [".microcosm/routes.json"],
                },
                "source_open_body_import_floor": {"status": "pass"},
                "state_write_proof": {"status": "pass"},
                "route_explanation": {
                    "status": "pass",
                    "selected_work_id": "work_1",
                    "selected_work_status": "closed",
                },
                "route_selection_proof": {
                    "status": "pass",
                    "route_id_available_in_state": True,
                },
                "local_first_screen_route": {
                    "route_id": "route_1",
                    "status": "pass",
                },
            },
            "front_door_status": {
                "surface_statuses": {"graph": "pass"},
            },
        }

    monkeypatch.setattr(runtime_shell.project_substrate, "observe_project", observe_project)
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "_load_work_items",
        load_work_items,
    )
    monkeypatch.setattr(shell, "tour_card", tour_card)
    monkeypatch.setattr(shell, "status_card", status_card)
    server = shell.serve("127.0.0.1", 0, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = getattr(server, "server_address")
        with urlopen(f"http://{host}:{port}/", timeout=5) as response:
            landing_html = response.read().decode("utf-8")
        observe_response = _read_server_json(server, "/project/observe")
        workitems_response = _read_server_json(server, "/project/workitems")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert "Microcosm Observatory" in landing_html
    assert observe_response == observe_payload
    assert workitems_response == {
        "schema_version": "microcosm_project_workitems_view_v1",
        "status": "pass",
        "work_items": work_rows,
    }
    assert observe_calls == [
        {
            "project_path": resolved_project,
            "refresh_architecture": False,
        }
    ]
    assert workitem_calls == [resolved_project]
    assert tour_card_calls == [resolved_project]
    assert status_card_calls == [resolved_project]


def test_runtime_shell_serve_authority_card_endpoint_caches_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    served_card = {
        "schema_version": "microcosm_public_authority_card_v1",
        "status": "pass",
        "source": "authority_card",
    }
    authority_card_calls: list[str] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    def authority_card() -> dict[str, object]:
        authority_card_calls.append("authority_card")
        return served_card

    monkeypatch.setattr(shell, "authority_card", authority_card)
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        first_payload = _read_server_json(server, "/authority-card")
        second_payload = _read_server_json(server, "/authority-card")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert first_payload == served_card
    assert second_payload == served_card
    assert authority_card_calls == ["authority_card"]


def test_runtime_shell_serve_workingness_endpoints_share_cached_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    served_map = {
        "schema_version": "microcosm_workingness_failure_map_v1",
        "status": "pass",
        "completeness_status": "complete_failure_modes",
        "command": "microcosm workingness",
        "endpoint": runtime_shell.WORKINGNESS_ENDPOINT,
        "workingness_map_ref": runtime_shell.WORKINGNESS_MAP_REF.as_posix(),
        "surface_counts": {
            "mapped_organ_count": 1,
            "adapter_backed_organ_count": 1,
            "demoted_drilldown_count": 0,
            "rows_with_failure_modes": 1,
            "rows_with_future_work_targets": 0,
            "rows_with_source_body_imports": 0,
            "source_open_body_material_count": 0,
            "missing_standard_count": 0,
            "missing_failure_modes_count": 0,
        },
        "source_body_material_count_scope": {},
        "thing_failure_map": [],
        "map_policy": {
            "not_a_scorecard": True,
            "accepted_status_is_not_evidence_strength": True,
        },
        "authority_ceiling": {
            "release_authorized": False,
            "score_based_progress_authority": False,
            "whole_system_correctness_claim": False,
        },
    }
    workingness_calls: list[bool] = []
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )

    def workingness_map(*, persist_receipt: bool = False) -> dict[str, object]:
        workingness_calls.append(persist_receipt)
        return served_map

    monkeypatch.setattr(shell, "workingness_map", workingness_map)
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        card = _read_server_json(server, runtime_shell.WORKINGNESS_CARD_ENDPOINT)
        payload = _read_server_json(server, runtime_shell.WORKINGNESS_ENDPOINT)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert card["schema_version"] == "microcosm_workingness_command_speed_card_v1"
    assert card["status"] == "pass"
    assert card["card_status"] == "clear"
    assert card["surface_counts"]["mapped_organ_count"] == 1
    assert payload == served_map
    assert workingness_calls == [False]


def test_project_observatory_bounds_project_evidence_preview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    shell = RuntimeShell(tmp_path)
    selected_route_id = "readme_onboarding_route"
    expected_project_ref = runtime_shell._public_project_command_ref(
        project.resolve(strict=False),
        tmp_path,
    )
    status_calls: list[tuple[Path | None, str | Path | None]] = []
    call_order: list[str] = []

    def status(
        project_path: str | Path | None = None,
        *,
        project_ref: str | Path | None = None,
    ) -> dict[str, object]:
        resolved_project = (
            Path(project_path).resolve(strict=False)
            if project_path is not None
            else None
        )
        call_order.append("status")
        status_calls.append((resolved_project, project_ref))
        return {
            "status": "pass",
            "project_ref": str(project_ref),
            "project_front_door_status": {
                "status": "pass",
                "selected_route_id": selected_route_id,
            },
            "status_card": {
                "project_ref": str(project_ref),
                "front_door_status": {
                    "status": "pass",
                    "blocking_surface_ids": [],
                    "drilldown_warning_surface_ids": [],
                    "surface_statuses": {},
                },
                "front_door": {
                    "source_open_body_import_floor": {"status": "pass"},
                },
            },
        }

    monkeypatch.setattr(shell, "status", status)

    def tour(*_args: object, **_kwargs: object) -> dict[str, object]:
        call_order.append("tour")
        return {
            "status": "pass",
            "selected_route_id": selected_route_id,
            "front_door_status": {
                "status": "pass",
                "blocking_surface_ids": [],
                "drilldown_warning_surface_ids": [],
            },
            "first_screen": {
                "selected_route_id": selected_route_id,
                "proof_surface": {"status": "pass"},
            },
            "compile_summary": {"selected_route_id": selected_route_id},
        }

    monkeypatch.setattr(
        shell,
        "tour",
        tour,
    )

    def compact_lens(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"status": "pass"}

    for method_name in [
        "intake",
        "reveal",
        "observatory_intake_bridge",
        "prediction_lens",
        "market_boundary",
        "corpus_lens",
        "trace_lens",
        "repair_loop",
        "evidence_cells",
        "proof_loop_depth",
        "landing_replay",
        "view_quality",
        "projection_safety",
        "projection_drift",
        "route_cleanup",
        "projection_import_map",
        "import_projector",
        "option_surface_lens",
        "stripping_guard",
        "standards_control",
        "hook_coverage",
        "replay_gauntlet",
        "benchmark_lab",
        "legibility_scorecard",
    ]:
        monkeypatch.setattr(shell, method_name, compact_lens)

    monkeypatch.setattr(
        runtime_shell.architecture_kernel,
        "load_kernel_manifest",
        lambda _root: {
            "primitives": [{"public_name": "observe"}],
            "pattern_surface": {"surface_id": "patterns"},
        },
    )
    monkeypatch.setattr(
        runtime_shell.architecture_kernel,
        "load_standard_pressure_surface",
        lambda _root: {"surface_id": "standards"},
    )
    monkeypatch.setattr(
        runtime_shell.first_screen_composition,
        "first_screen_composition_card",
        lambda *_args, **_kwargs: {
            "status": "pass",
            "schema_version": "test_first_screen_card",
            "reader_routes": [],
            "evidence_count_frame": {
                "interpretation": "accounting_not_maturity_score",
            },
            "comparison_frame": {"purpose": "test"},
            "authority_ceiling": {"status": "pass"},
        },
    )
    monkeypatch.setattr(
        runtime_shell.first_screen_composition,
        "first_screen_compact_card",
        lambda card: {"status": card.get("status")},
    )
    monkeypatch.setattr(
        runtime_shell,
        "_project_state_inspection_card",
        lambda *_args, **_kwargs: {
            "status": "pass",
            "state_dir": ".microcosm",
            "state_file_count": 0,
            "first_screen_refs": [],
            "missing_first_screen_refs": [],
        },
    )

    monkeypatch.setattr(runtime_shell.project_substrate, "init_project", compact_lens)
    monkeypatch.setattr(runtime_shell.project_substrate, "index_project", compact_lens)
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "discover_patterns",
        lambda *_args, **_kwargs: {"patterns": []},
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "architecture_project",
        lambda *_args, **_kwargs: {
            "pattern_surface": {"surface_id": "patterns"},
            "standard_pressure_surface": {"surface_id": "standards"},
        },
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "state_graph",
        lambda *_args, **_kwargs: {
            "node_count": 1,
            "edge_count": 1,
            "graph_ref": ".microcosm/graph.json",
        },
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "catalog_project",
        lambda *_args, **_kwargs: {
            "project_id": "project",
            "file_count": 1,
            "role_counts": {},
        },
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "python_lens_card",
        lambda *_args, **_kwargs: {
            "status": "pass",
            "lens_id": "python_lens",
            "python_file_count": 1,
            "ready_route_count": 1,
        },
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "propose_routes",
        lambda *_args, **_kwargs: {
            "routes": [
                {
                    "route_id": selected_route_id,
                    "title": "Inspect README onboarding",
                    "grounded_refs": ["README.md"],
                    "pattern_refs": [],
                    "standard_pressure_refs": [],
                    "authority": "project_local_projection_not_source_authority",
                }
            ]
        },
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "explain_route",
        lambda *_args, **_kwargs: {
            "status": "pass",
            "route_id": selected_route_id,
            "pattern_bindings": [],
            "standard_bindings": [],
            "authority_boundary": "project_local_projection_not_source_authority",
        },
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "_load_work_items",
        lambda _project: [
            {
                "work_id": "work_0001",
                "status": "closed",
                "route_id": selected_route_id,
                "source_files_mutated": False,
                "event_refs": [{"event_id": "evt_1"}],
                "evidence_refs": [".microcosm/evidence/work.json"],
            }
        ],
    )
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "observe_project",
        lambda *_args, **_kwargs: {
            "events": [
                {
                    "event_id": "evt_1",
                    "span": "work.run",
                    "status": "pass",
                    "evidence_ref": ".microcosm/evidence/work.json",
                }
            ],
            "state_write_proof": {"status": "pass"},
        },
    )
    observed_limits: list[int | None] = []

    def list_evidence(
        _project_path: str | Path,
        *,
        limit: int | None = None,
    ) -> dict[str, object]:
        if limit is None:
            raise AssertionError("observatory should request a bounded evidence preview")
        observed_limits.append(limit)
        rows = [
            {
                "evidence_ref": f".microcosm/evidence/evidence_{idx}.json",
                "status": "pass",
                "replacement_policy": "stable_ref_latest_body",
            }
            for idx in range(limit)
        ]
        return {
            "status": "pass",
            "evidence_count": 42,
            "returned_evidence_count": len(rows),
            "limit": limit,
            "truncated": True,
            "evidence": rows,
        }

    monkeypatch.setattr(runtime_shell.project_substrate, "list_evidence", list_evidence)

    model = shell.project_observatory(project, persist_receipts=False)

    assert call_order == ["tour", "status"]
    assert status_calls == [(project.resolve(strict=False), expected_project_ref)]
    assert model["status_card_ref"] == (
        f"microcosm status --card {expected_project_ref}"
    )
    assert model["runtime_status"]["status_card"]["project_ref"] == expected_project_ref
    assert model["project_summary"]["project_ref"] == expected_project_ref
    assert observed_limits == [
        runtime_shell.PROJECT_OBSERVATORY_EVIDENCE_PREVIEW_LIMIT
    ]
    causal = model["causal_chain"]
    assert (
        len(causal["evidence"])
        == runtime_shell.PROJECT_OBSERVATORY_EVIDENCE_PREVIEW_LIMIT
    )
    assert causal["evidence_summary"]["evidence_count"] == 42
    assert causal["evidence_summary"]["preview_limit"] == (
        runtime_shell.PROJECT_OBSERVATORY_EVIDENCE_PREVIEW_LIMIT
    )
    assert model["observatory_card"]["causal_chain_summary"]["evidence_count"] == 42


def test_runtime_spine_counts_evidence_without_materializing_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    registry = {
        "source_ref": "core/organ_evidence_classes.json",
        "schema_version": "test",
        "registry_id": "test",
        "fail_closed_no_default": True,
        "explicit_coverage": True,
        "class_profiles": {},
        "organ_profiles_by_id": {},
        "missing_organs": [],
        "extra_organs": [],
        "duplicate_organs": [],
    }
    body_import_floor = {
        "status": "pass",
        "copied_non_secret_macro_body_material_count": 0,
        "public_safe_body_material_count": 0,
        "mixed_public_safe_macro_import_assay": {"status": "pass"},
    }

    monkeypatch.setattr(shell, "organs", lambda: [])
    monkeypatch.setattr(shell, "patterns", lambda: [])
    monkeypatch.setattr(shell, "routes", lambda: [])
    monkeypatch.setattr(shell, "workitems", lambda: [])
    monkeypatch.setattr(shell, "evidence_count", lambda: 7)
    monkeypatch.setattr(
        runtime_shell,
        "_load_evidence_class_registry",
        lambda _root: registry,
    )
    monkeypatch.setattr(
        runtime_shell,
        "_proof_lab_first_screen_card",
        lambda _root: {"status": "pass"},
    )
    monkeypatch.setattr(
        runtime_shell,
        "_macro_projection_body_import_floor",
        lambda _root: body_import_floor,
    )

    def fail_if_receipts_materialized() -> list[dict[str, object]]:
        raise AssertionError("spine should use evidence_count instead of evidence")

    monkeypatch.setattr(shell, "evidence", fail_if_receipts_materialized)

    spine = shell.spine()

    assert spine["surface_counts"]["evidence_count"] == 7


def test_runtime_status_reuses_full_status_inputs_for_embedded_card(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    call_counts = {
        "organs": 0,
        "patterns": 0,
        "routes": 0,
        "workitems": 0,
        "evidence_count": 0,
        "body_import_floor": 0,
        "proof_lab": 0,
        "workingness_map": 0,
        "project_status_overlay": 0,
    }
    project = tmp_path / "project"
    project.mkdir()

    def count_call(name: str) -> None:
        call_counts[name] += 1

    monkeypatch.setattr(runtime_shell, "_product_runtime_steps", lambda: [])
    monkeypatch.setattr(
        runtime_shell.architecture_kernel,
        "pattern_surface_contract",
        lambda _root: {"surface_id": "patterns"},
    )
    monkeypatch.setattr(
        runtime_shell.architecture_kernel,
        "standard_pressure_contract",
        lambda _root: {"surface_id": "standards"},
    )
    monkeypatch.setattr(
        runtime_shell.architecture_kernel,
        "load_kernel_manifest",
        lambda _root: {"primitive_count": 0},
    )
    monkeypatch.setattr(
        runtime_shell,
        "_cold_reader_first_screen_card",
        lambda **_kwargs: {
            "status": "pass",
            "generated_state": {},
            "behavior_surfaces": {},
            "authority_ceiling": {},
            "safe_to_show": {"source_files_mutated": False},
            "route_explanation": {},
        },
    )

    def proof_lab(_root: Path) -> dict[str, object]:
        count_call("proof_lab")
        return {"status": "pass"}

    def body_import_floor(_root: Path) -> dict[str, object]:
        count_call("body_import_floor")
        return {
            "status": "pass",
            "copied_non_secret_macro_body_material_count": 1,
            "public_safe_body_material_count": 1,
            "public_safe_body_material_counts_by_class": {},
            "source_body_import_lens": {},
            "direct_source_module_manifest_count": 0,
            "direct_source_module_manifest_material_count": 0,
            "mixed_public_safe_macro_import_assay": {"status": "pass"},
            "validation_hooks": [],
            "routing_refs": {},
            "defect_count": 0,
        }

    def workingness_map(*, persist_receipt: bool = False) -> dict[str, object]:
        count_call("workingness_map")
        return {
            "status": "pass",
            "completeness_status": "complete_failure_modes",
            "surface_counts": {
                "missing_standard_count": 0,
                "missing_failure_modes_count": 0,
            },
            "map_policy": {},
        }

    def organs() -> list[dict[str, object]]:
        count_call("organs")
        return []

    def patterns() -> list[dict[str, object]]:
        count_call("patterns")
        return []

    def routes() -> list[dict[str, object]]:
        count_call("routes")
        return []

    def workitems() -> list[dict[str, object]]:
        count_call("workitems")
        return []

    def evidence_count() -> int:
        count_call("evidence_count")
        return 7

    def project_status_overlay(_project_path: Path) -> dict[str, object]:
        count_call("project_status_overlay")
        return {
            "status": "pass",
            "state_dir_exists": True,
            "selected_route_id": "readme_onboarding_route",
            "available_project_route_ids": ["readme_onboarding_route"],
            "route_explanation": {},
        }

    monkeypatch.setattr(runtime_shell, "_proof_lab_first_screen_card", proof_lab)
    monkeypatch.setattr(
        runtime_shell,
        "_macro_projection_body_import_floor",
        body_import_floor,
    )
    monkeypatch.setattr(
        runtime_shell,
        "_project_status_overlay",
        project_status_overlay,
    )
    monkeypatch.setattr(shell, "workingness_map", workingness_map)
    monkeypatch.setattr(shell, "organs", organs)
    monkeypatch.setattr(shell, "patterns", patterns)
    monkeypatch.setattr(shell, "routes", routes)
    monkeypatch.setattr(shell, "workitems", workitems)
    monkeypatch.setattr(shell, "evidence_count", evidence_count)

    payload = shell.status(project)

    assert payload["evidence_count"] == 7
    assert payload["status_card"]["substrate_counts"]["evidence_count"] == 7
    assert (
        payload["project_front_door_status"]["selected_route_id"]
        == "readme_onboarding_route"
    )
    assert (
        payload["status_card"]["front_door"]["selected_route_id"]
        == "readme_onboarding_route"
    )
    assert call_counts == {
        "organs": 1,
        "patterns": 1,
        "routes": 1,
        "workitems": 1,
        "evidence_count": 1,
        "body_import_floor": 1,
        "proof_lab": 1,
        "workingness_map": 1,
        "project_status_overlay": 1,
    }


def test_runtime_shell_reuses_body_import_floor_within_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    call_count = 0
    body_import_floor = {
        "status": "pass",
        "public_safe_body_material_count": 1,
        "direct_source_module_manifest_count": 0,
        "direct_source_module_manifest_material_count": 0,
    }

    def counted_body_import_floor(_root: Path) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return dict(body_import_floor)

    monkeypatch.setattr(
        runtime_shell,
        "_cached_macro_projection_body_import_floor",
        lambda _root: {},
    )
    monkeypatch.setattr(
        runtime_shell,
        "_macro_projection_body_import_floor",
        counted_body_import_floor,
    )

    first_card = shell._macro_projection_body_import_floor_card()
    first_card["status"] = "mutated_after_return"
    second_card = shell._macro_projection_body_import_floor_card()
    live_floor = shell._macro_projection_body_import_floor()

    assert call_count == 1
    assert second_card["status"] == "pass"
    assert live_floor["status"] == "pass"


def test_runtime_shell_full_tour_suppresses_nested_receipt_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    write_paths: list[Path] = []

    def counted_atomic_write(path: Path, payload: dict[str, object]) -> None:
        write_paths.append(path)

    def nested_payload(**extra: object) -> dict[str, object]:
        runtime_shell.write_json_atomic(
            tmp_path / "nested_lens.json",
            {"status": "pass"},
        )
        return {"status": "pass", **extra}

    monkeypatch.setattr(runtime_shell, "_write_json_atomic", counted_atomic_write)
    monkeypatch.setattr(
        runtime_shell.project_substrate,
        "compile_project",
        lambda *_args, **_kwargs: {
            "headline": "repo -> .microcosm",
            "file_count": 1,
            "passing_pattern_count": 1,
            "route_count": 1,
            "selected_route_id": "readme_onboarding_route",
            "work_id": "work_0001",
            "event_count": 1,
            "evidence_count": 1,
            "source_files_mutated": False,
            "available_project_route_ids": ["readme_onboarding_route"],
        },
    )
    monkeypatch.setattr(
        runtime_shell,
        "_proof_lab_first_screen_card",
        lambda _root: nested_payload(
            route_component_count=9,
            route_id="formal_prover_context_strategy_gate",
            lean_lake_return_code=0,
            component_metrics={},
        ),
    )
    monkeypatch.setattr(
        shell,
        "_macro_projection_body_import_floor",
        lambda: nested_payload(
            public_safe_body_material_count=1,
            direct_source_module_manifest_count=0,
            direct_source_module_manifest_material_count=0,
            public_safe_body_material_counts_by_class={},
            verified_source_module_family_count=1,
        ),
    )
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=True: nested_payload(
            surface_counts={"surface_authority_count": 1}
        ),
    )
    monkeypatch.setattr(
        shell,
        "workingness_map",
        lambda *, persist_receipt=False: nested_payload(
            mapped_organ_count=1,
            missing_standard_count=0,
            missing_failure_modes_count=0,
        ),
    )
    monkeypatch.setattr(
        shell,
        "reveal",
        lambda *, persist_receipt=True: nested_payload(step_count=0),
    )
    method_payloads = {
        "spine": {"surface_counts": {"organ_count": 1}},
        "prediction_lens": {"mechanics": []},
        "market_boundary": {"boundary_summary": {"row_count": 0, "negative_case_count": 0}},
        "corpus_lens": {"corpus_summary": {"corpus_count": 0}, "consumer_gate": {}},
        "trace_lens": {"trace_rows": [], "negative_case_ids": []},
        "repair_loop": {"loop_stages": [], "transition_rows": [], "negative_case_ids": []},
        "evidence_cells": {"evidence_cells": [], "negative_case_ids": []},
        "verifier_lab_execution_spine_lens": {"execution_summary": {}},
        "proof_loop_depth": {
            "proof_loop_summary": {"gate_count": 0, "negative_case_count": 0}
        },
        "landing_replay": {"lane_decision_table": [], "negative_case_ids": []},
        "view_quality": {"action_rows": [], "hot_action_rollup": []},
        "projection_safety": {"projection_rows": []},
        "projection_drift": {"drift_summary": {"row_count": 0, "repair_route_count": 0}},
        "spatial_simulation": {},
        "circuit_attribution": {},
        "route_cleanup": {"cleanup_summary": {"row_count": 0, "negative_case_count": 0}},
        "projection_import_map": {"map_summary": {"row_count": 0}, "import_stages": []},
        "import_projector": {"projector_summary": {"row_count": 0, "stage_count": 0}},
        "option_surface_lens": {
            "option_surface_summary": {"row_count": 0, "stage_count": 0}
        },
        "stripping_guard": {
            "guard_summary": {"guard_row_count": 0, "negative_case_count": 0}
        },
        "standards_control": {
            "standards_summary": {
                "standards_control_row_count": 0,
                "negative_case_count": 0,
            }
        },
        "hook_coverage": {"intervention_rows": [], "missing_authority_case_ids": []},
        "replay_gauntlet": {
            "coverage_summary": {"episode_count": 0, "blocked_episode_count": 0}
        },
        "benchmark_lab": {"scorecard": {"task_count": 0, "oracle_patch_count": 0}},
        "legibility_scorecard": {
            "scorecard": {"checkpoint_count": 0, "reader_question_count": 0}
        },
        "intake": {"projection_cell_count": 0},
    }
    for method_name, payload in method_payloads.items():
        monkeypatch.setattr(
            shell,
            method_name,
            lambda payload=payload: nested_payload(**payload),
        )

    payload = shell.tour(project)

    assert payload["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert write_paths == [tmp_path / "receipts/runtime_shell/public_ten_minute_tour.json"]


def test_runtime_shell_serve_evidence_endpoint_rejects_invalid_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = RuntimeShell(tmp_path)
    monkeypatch.setattr(
        shell,
        "authority",
        lambda persist_receipts=False: {"status": "pass"},
    )
    server = shell.serve("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        with pytest.raises(HTTPError) as excinfo:
            urlopen(f"http://{host}:{port}/evidence?limit=-1", timeout=5)
        payload = json.loads(excinfo.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert excinfo.value.code == 400
    assert payload == {
        "expected": "nonnegative integer; 0 means full list",
        "parameter": "limit",
        "received": "-1",
        "status": "invalid_query",
    }
