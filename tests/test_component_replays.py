from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

import pytest

from microcosm_core.receipts import write_json_atomic


def _gate():
    source = Path(__file__).resolve().parents[1] / "scripts/check/check_component_replays.py"
    spec = spec_from_file_location("component_replays", source)
    gate = module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def test_replay_gate_keeps_failures_exceptions_and_later_results(tmp_path):
    gate = _gate()
    (tmp_path / "fixtures/input").mkdir(parents=True)

    def crash(*args):
        raise RuntimeError("component failed")

    def step(name, runner):
        return SimpleNamespace(organ_id=name, runner=runner, example_rel="fixtures/input",
                               receipt_name="result.json")

    def recorded(status):
        def run(source, out, command):
            out.mkdir(parents=True)
            result = {"status": status, "organ_id": out.name, "error_codes": ["BOUNDARY_FAILED"] if status == "blocked" else []}
            write_json_atomic(out / "result.json", result)
            return result
        return run

    rows = gate.replay_steps(tmp_path, tmp_path / ".microcosm/run", [
        step("blocked", recorded("blocked")), step("crashed", crash),
        step("passed", recorded("pass")),
        step("unrecorded", lambda *args: {"status": "pass"}),
    ])
    assert [row["status"] for row in rows] == ["blocked", "error", "pass", "error"]
    assert rows[0]["error_codes"] == ["BOUNDARY_FAILED"]
    assert "RuntimeError" in rows[1]["error"]
    assert rows[2]["input_tree_sha256"]
    assert rows[2]["receipt_sha256"]
    assert "FileNotFoundError" in rows[3]["error"]


@pytest.mark.parametrize("kind", ["file", "directory", "dangling", "root"])
def test_input_tree_hash_rejects_uncaptured_symlinks(tmp_path, kind):
    gate = _gate()
    source = tmp_path / "input"
    source.mkdir()
    target = tmp_path / "external"
    if kind in {"directory", "root"}:
        target.mkdir()
        (target / "value").write_text("before")
    elif kind == "file":
        target.write_text("before")
    link = tmp_path / "root-link" if kind == "root" else source / "link"
    try:
        link.symlink_to(target, target_is_directory=kind in {"directory", "root"})
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(gate.UnsupportedInputSymlink):
        gate.input_tree_hash(link if kind == "root" else source)


def test_replay_rejects_linked_input_before_runner_can_read_external_bytes(tmp_path):
    gate = _gate()
    source = tmp_path / "input"
    source.mkdir()
    target = tmp_path / "external"
    target.write_text("before")
    try:
        (source / "value").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")

    def forbidden(*args):
        pytest.fail("unsupported linked input reached the component")

    step = SimpleNamespace(organ_id="probe", example_rel="input", receipt_name="result.json", runner=forbidden)
    rows = gate.replay_steps(tmp_path, tmp_path / ".microcosm/run", [step])
    assert rows[0]["status"] == "error"
    assert rows[0]["error"] == "UnsupportedInputSymlink"
    assert target.read_text() == "before"


@pytest.mark.parametrize("recorded", [
    {"status": "blocked"}, {"status": "pass", "organ_id": "different"},
])
def test_replay_gate_rejects_unbound_written_receipt(tmp_path, recorded):
    gate = _gate()
    (tmp_path / "input").mkdir()

    def run(source, out, command):
        out.mkdir(parents=True)
        write_json_atomic(out / "result.json", recorded)
        return {"status": "pass", "organ_id": "probe"}

    step = SimpleNamespace(organ_id="probe", example_rel="input", receipt_name="result.json", runner=run)
    rows = gate.replay_steps(tmp_path, tmp_path / ".microcosm/run", [step])
    assert rows[0]["status"] == "error"
    assert rows[0]["error"] == "ValueError"


@pytest.mark.parametrize("live", [True, False])
def test_replay_gate_selects_native_lab_and_requires_its_execution_witness(tmp_path, monkeypatch, live):
    from microcosm_core import runtime_shell
    from microcosm_core.organs import lean_proof_search_lab_runtime as lab

    gate = _gate()
    fixture_ref = "fixtures/first_wave/lean_proof_search_lab_runtime/input"
    (tmp_path / fixture_ref).mkdir(parents=True)
    (tmp_path / fixture_ref / "public.json").write_text("{}")

    def run(source, out, command):
        assert source == tmp_path / fixture_ref
        result = {"status": "pass", "organ_id": lab.ORGAN_ID,
                  "execution_witness_mode": lab.EXECUTION_LIVE if live else lab.EXECUTION_STANDALONE,
                  "verification_performed": live,
                  "tool_state": lab.TOOL_PRESENT_AND_VERIFIED if live else "not_executed"}
        out.mkdir(parents=True)
        write_json_atomic(out / lab.RESULT_NAME, result)
        return result

    monkeypatch.setattr(lab, "run", run)
    declared = next(step for step in runtime_shell.RUNTIME_STEPS if step.organ_id == lab.ORGAN_ID)
    rows = gate.replay_steps(tmp_path, tmp_path / ".microcosm/run", [declared])
    assert rows[0]["input_ref"] == fixture_ref
    assert rows[0]["status"] == ("pass" if live else "missing_native_lean_witness")
    assert rows[0]["verification_performed"] is live


@pytest.mark.parametrize("mode", ["live", "contract", "relabelled_skipped_build", "written_contract"])
def test_replay_gate_requires_live_lake_witness_in_returned_and_fresh_receipt(tmp_path, monkeypatch, mode):
    from microcosm_core import runtime_shell
    from microcosm_core.organs import formal_math_lean_proof_witness as witness

    gate = _gate()
    fixture_ref = "fixtures/first_wave/formal_math_lean_proof_witness/input"
    (tmp_path / fixture_ref).mkdir(parents=True)
    (tmp_path / fixture_ref / "public.json").write_text("{}")
    declared = next(step for step in runtime_shell.RUNTIME_STEPS if step.organ_id == witness.ORGAN_ID)
    compatibility_runner = declared.runner

    def run(source, out, command):
        assert source == tmp_path / fixture_ref
        result = {
            "status": "pass", "organ_id": witness.ORGAN_ID,
            "execution_witness_mode": "live_lean_lake_execution",
            "real_runtime_receipt": True, "synthetic_contract": False, "not_a_live_run": False,
            "tool_versions": {"lean_available": True, "lake_available": True},
            "lake_build": {"return_code": 0, "timed_out": False},
            "compiled_declaration_count": 1,
            "observed_negative_cases": witness.EXPECTED_NEGATIVE_CASES,
            "missing_negative_cases": [],
        }
        if mode in {"contract", "relabelled_skipped_build"}:
            result["lake_build"] = witness._standalone_exported_lake_build({})
        if mode == "contract":
            result.update(execution_witness_mode="standalone_exported_witness_contract",
                          real_runtime_receipt=False, synthetic_contract=True, not_a_live_run=True)
        recorded = dict(result)
        if mode == "written_contract":
            recorded["execution_witness_mode"] = "standalone_exported_witness_contract"
        out.mkdir(parents=True)
        write_json_atomic(out / witness.RESULT_NAME, recorded)
        return result

    monkeypatch.setattr(witness, "run", run)
    rows = gate.replay_steps(tmp_path, tmp_path / ".microcosm/run", [declared])
    assert rows[0]["input_ref"] == fixture_ref
    assert rows[0]["status"] == (
        "pass" if mode == "live" else "error" if mode == "written_contract"
        else "missing_native_lean_lake_witness"
    )
    assert declared.runner is compatibility_runner
    assert declared.runner.__name__ == witness.run_witness_bundle.__name__


def _shared_step(runner, name="probe", input_ref="input"):
    return SimpleNamespace(organ_id=name, runner=runner, example_rel=input_ref,
                           receipt_name="result.json")


def _write_result(out, result):
    out.mkdir(parents=True)
    write_json_atomic(out / "result.json", result)
    return result


@pytest.mark.parametrize("mutation", ["missing_both_ids", "wrong_return_id", "nested_payload", "execution"])
def test_shared_host_rejects_unbound_or_contradictory_payloads(tmp_path, mutation):
    from microcosm_core.component_replay import replay_components
    (tmp_path / "input").mkdir()

    def runner(source, out, command):
        result = {"status": "pass", "organ_id": "probe", "detail": {"value": "original"}}
        if mutation == "missing_both_ids":
            result.pop("organ_id")
        if mutation == "execution":
            result["exercise"] = {"status": "blocked"}
        _write_result(out, result)
        if mutation == "wrong_return_id":
            result["organ_id"] = "another"
        if mutation == "nested_payload":
            result["detail"]["value"] = "different"
            (out / "result.json").write_text(json.dumps(result))
        return result

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == "blocked"
    assert result["admission"]["accepted"] is False


def test_shared_host_compares_full_public_normalized_payload(tmp_path):
    from microcosm_core.component_replay import replay_components
    from microcosm_core.receipts import normalize_public_receipt_paths
    (tmp_path / "input").mkdir()

    def runner(source, out, command):
        result = {"status": "pass", "organ_id": "probe", "detail": {"path": "/tmp/a-fixture/result.json"}}
        _write_result(out, result)
        return result

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == "pass"
    observation = result["admission"]["observations"][0]
    assert observation["runner_payload_digest"] == observation["receipt_payload_digest"]
    assert result["admission"]["run_nonce"]


def test_shared_host_rejects_symlinked_output_ancestor_and_stale_file(tmp_path):
    from microcosm_core.component_replay import replay_components
    (tmp_path / "input").mkdir()
    external = tmp_path / "external"
    old = {"status": "pass", "organ_id": "probe", "created_at": "2000-01-01T00:00:00Z"}
    _write_result(external, old)

    def runner(source, out, command):
        out.symlink_to(external, target_is_directory=True)
        return old

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == "blocked"
    assert result["results"][0]["error"] == "UnsupportedInputSymlink"
    assert json.loads((external / "result.json").read_text()) == old


def test_shared_host_refuses_preexisting_component_output(tmp_path):
    from microcosm_core.component_replay import replay_components
    (tmp_path / "input").mkdir()
    out = tmp_path / ".microcosm/run"
    _write_result(out / "probe", {"status": "pass", "organ_id": "probe"})

    def runner(*args):
        pytest.fail("a stale output reached the runner")

    result = replay_components(tmp_path, out, [_shared_step(runner)])
    assert result["status"] == "blocked"
    assert result["results"][0]["error"] == "FileExistsError"


@pytest.mark.parametrize("owner", ["src", "core", "standards"])
def test_shared_host_rejects_mutated_source_registry_or_policy(tmp_path, owner):
    from microcosm_core.component_replay import replay_components
    (tmp_path / "input").mkdir()
    (tmp_path / owner).mkdir()
    target = tmp_path / owner / "owned.txt"
    target.write_text("original")

    def runner(source, out, command):
        target.write_text("changed")
        return _write_result(out, {"status": "pass", "organ_id": "probe"})

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == "blocked"
    assert result["results"][0]["status"] == "source_changed"
    observation = result["admission"]["observations"][0]
    assert observation["source_before"] != observation["source_after"]


def test_shared_host_snapshots_all_inputs_before_any_runner(tmp_path):
    from microcosm_core.component_replay import replay_components
    for directory in ("first", "second"):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / "data").write_text("original")

    def first(source, out, command):
        (tmp_path / "second/data").write_text("changed by first")
        return _write_result(out, {"status": "pass", "organ_id": "first"})

    def second(source, out, command):
        return _write_result(out, {"status": "pass", "organ_id": "second"})

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [
        _shared_step(first, "first", "first"), _shared_step(second, "second", "second")])
    assert result["status"] == "blocked"
    assert [r["status"] for r in result["results"]] == ["pass", "input_changed"]


@pytest.mark.parametrize("mutation", ["remove_empty_directory", "directory_mode", "file_mode"])
def test_shared_input_snapshot_captures_empty_directories_and_full_modes(tmp_path, mutation):
    from microcosm_core.component_replay import input_tree_hash
    source = tmp_path / "input"
    source.mkdir()
    directory = source / "empty"
    directory.mkdir()
    file = source / "data"
    file.write_text("same bytes")
    directory.chmod(0o755)
    file.chmod(0o755)
    before = input_tree_hash(source)
    if mutation == "remove_empty_directory":
        directory.rmdir()
    elif mutation == "directory_mode":
        directory.chmod(0o700)
    else:
        file.chmod(0o744)
    assert input_tree_hash(source) != before


def test_shared_host_hashes_the_same_receipt_bytes_it_parses(tmp_path, monkeypatch):
    from microcosm_core import component_replay
    (tmp_path / "input").mkdir()
    original = {"status": "pass", "organ_id": "probe"}
    original_bytes = []
    receipt_path = tmp_path / ".microcosm/run/probe/result.json"

    def runner(source, out, command):
        _write_result(out, original)
        original_bytes.append((out / "result.json").read_bytes())
        return original

    real_parse = component_replay.loads_json_strict

    def parse_then_concurrent_replace(data, source):
        parsed = real_parse(data, source)
        receipt_path.write_text('{"status":"blocked","organ_id":"another"}')
        return parsed

    monkeypatch.setattr(component_replay, "loads_json_strict", parse_then_concurrent_replace)
    result = component_replay.replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == "blocked"
    assert result["results"][0]["status"] == "receipt_changed"
    captured_digest = result["admission"]["observations"][0]["receipt_digest"]
    assert captured_digest == hashlib.sha256(original_bytes[0]).hexdigest()
    assert captured_digest != hashlib.sha256(receipt_path.read_bytes()).hexdigest()


def test_shared_host_uses_generated_admission_even_when_every_row_passes(tmp_path, monkeypatch):
    from microcosm_core.component_replay import replay_components
    import plectis.replay
    (tmp_path / "input").mkdir()
    called = []

    def reject(*args):
        called.append(args)
        return False

    monkeypatch.setattr(plectis.replay, "accept", reject)

    def runner(source, out, command):
        return _write_result(out, {"status": "pass", "organ_id": "probe"})

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert called and result["results"][0]["status"] == "pass"
    assert result["status"] == "blocked"


def test_shared_host_rejects_empty_or_duplicate_selection(tmp_path):
    from microcosm_core.component_replay import replay_components
    (tmp_path / "input").mkdir()

    def runner(source, out, command):
        return _write_result(out, {"status": "pass", "organ_id": "probe"})

    assert replay_components(tmp_path, tmp_path / ".microcosm/empty", [])["status"] == "blocked"
    route = _shared_step(runner)
    result = replay_components(tmp_path, tmp_path / ".microcosm/duplicates", [route, route])
    assert result["status"] == "blocked"


def test_distinct_original_private_paths_do_not_collapse_payload_binding():
    from microcosm_core.component_replay import payload_digest
    from microcosm_core.receipts import normalize_public_receipt_paths
    left = {"status": "pass", "organ_id": "probe", "witness_path": "/Users/alice/a"}
    right = {"status": "pass", "organ_id": "probe", "witness_path": "/Users/bob/b"}
    assert payload_digest(left) != payload_digest(right)
    saved = normalize_public_receipt_paths(left)
    assert payload_digest(left) == payload_digest(saved, persisted=True)
    assert payload_digest(saved) == payload_digest(saved, persisted=True)


def test_cli_records_source_material_that_recomputes_to_its_identity(tmp_path, monkeypatch):
    from microcosm_core.component_replay import _json_digest
    gate = _gate()
    (tmp_path / "input").mkdir()
    (tmp_path / "core").mkdir()
    (tmp_path / "core/organ_registry.json").write_text(json.dumps({"implemented_organs": [{
        "organ_id": "probe", "evidence_class": "semantic_validator", "claim_ceiling": "fixture only"}]}))

    def runner(source, out, command):
        return _write_result(out, {"status": "pass", "organ_id": "probe"})

    monkeypatch.setattr(gate, "RUNTIME_STEPS", (_shared_step(runner),))
    assert gate.main(["--root", str(tmp_path), "--out", str(tmp_path / ".microcosm/out")]) == 0
    summary = json.loads(next((tmp_path / ".microcosm/out").glob("run-*/component-replays.json")).read_text())
    assert _json_digest(summary["source"]) == summary["source_identity"]
    assert summary["source"] == summary["source_identity_material"]
    assert "git_identity" not in summary["source"]
    assert "git_identity" in summary


@pytest.mark.parametrize("target", [".", "src", "receipts"])
def test_shared_host_rejects_checkout_output_paths(tmp_path, target):
    from microcosm_core.component_replay import replay_components
    with pytest.raises(ValueError, match="output"):
        replay_components(tmp_path, tmp_path / target, [])


def test_public_projection_is_bound_while_raw_diagnostics_are_only_audited(tmp_path):
    from microcosm_core.component_replay import replay_components, _json_digest
    (tmp_path / "input").mkdir()
    raw = {"status": "pass", "organ_id": "probe", "internal_diagnostic": "synthetic omitted private detail"}
    public = {"status": "pass", "organ_id": "probe", "schema_version": "public_projection_v1"}

    def runner(source, out, command):
        _write_result(out, public)
        return raw

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == "pass"
    observation = result["admission"]["observations"][0]
    assert observation["runner_payload_digest"] == observation["receipt_payload_digest"]
    assert result["results"][0]["raw_runner_payload_sha256"] == _json_digest(raw)
    assert _json_digest(raw) != observation["runner_payload_digest"]
    assert result["payload_binding"] == "producer_public_representation_not_all_raw_api_fields"
    assert raw["internal_diagnostic"] not in json.dumps(result)


@pytest.mark.parametrize("mode", ["bypass", "duplicate", "outside_context", "auxiliary"])
def test_primary_producer_write_must_be_unique_and_in_context(tmp_path, mode):
    from contextvars import Context
    from microcosm_core.component_replay import replay_components
    (tmp_path / "input").mkdir()
    payload = {"status": "pass", "organ_id": "probe"}

    def runner(source, out, command):
        out.mkdir(parents=True)
        target = out / "result.json"
        if mode == "bypass":
            target.write_text(json.dumps(payload))
        elif mode == "outside_context":
            Context().run(write_json_atomic, target, payload)
        else:
            if mode == "auxiliary":
                write_json_atomic(out / "auxiliary.json", {"unrelated": True})
            write_json_atomic(target, payload)
            if mode == "duplicate":
                write_json_atomic(target, payload)
        return payload

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == ("pass" if mode == "auxiliary" else "blocked")
    if mode != "auxiliary":
        assert result["results"][0]["error_code"] == (
            "duplicate_primary_receipt_write" if mode == "duplicate" else "missing_producer_write")


def test_saved_private_path_provenance_cannot_substitute_another_writer_intent(tmp_path):
    from microcosm_core.component_replay import replay_components
    from microcosm_core.receipts import normalize_public_receipt_paths
    (tmp_path / "input").mkdir()

    def runner(source, out, command):
        raw = {"status": "pass", "organ_id": "probe", "witness_path": "/Users/alice/a"}
        _write_result(out, raw)
        replacement = normalize_public_receipt_paths({**raw, "witness_path": "/Users/bob/b"})
        (out / "result.json").write_text(json.dumps(replacement))
        return raw

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [_shared_step(runner)])
    assert result["status"] == "blocked"
    assert result["results"][0]["error_code"] == "producer_public_payload_mismatch"


def test_unselected_native_routes_are_not_loaded_or_executed_for_source_inventory(tmp_path, monkeypatch):
    from microcosm_core import component_replay
    (tmp_path / "input").mkdir()

    def runner(source, out, command):
        return _write_result(out, {"status": "pass", "organ_id": "probe"})

    selected = _shared_step(runner)
    unselected = _shared_step(runner, "formal_math_lean_proof_witness", "unused")
    real_select = component_replay.native_replay_step

    def select(step):
        assert step.organ_id == "probe", "unselected native tool route was activated"
        return real_select(step)

    monkeypatch.setattr(component_replay, "native_replay_step", select)
    result = component_replay.replay_components(tmp_path, tmp_path / ".microcosm/run", [selected],
                                                route_provider=lambda: [selected, unselected])
    assert result["status"] == "pass"


def test_late_write_in_copied_context_stays_with_its_original_component(tmp_path):
    from contextvars import copy_context
    from microcosm_core.component_replay import replay_components
    (tmp_path / "input").mkdir()
    previous = {}

    def first(source, out, command):
        result = _write_result(out, {"status": "pass", "organ_id": "first"})
        previous.update(context=copy_context(), target=out / "result.json", payload=result)
        return result

    def second(source, out, command):
        previous["context"].run(write_json_atomic, previous["target"], previous["payload"])
        return _write_result(out, {"status": "pass", "organ_id": "second"})

    result = replay_components(tmp_path, tmp_path / ".microcosm/run", [
        _shared_step(first, "first"), _shared_step(second, "second")])
    assert result["status"] == "blocked"
    assert [row["primary_receipt_write_count"] for row in result["results"]] == [2, 1]
    assert result["results"][0]["error_code"] == "duplicate_primary_receipt_write"
    assert result["results"][1]["status"] == "pass"
