from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import json

import pytest


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
            result = {"status": status, "error_codes": ["BOUNDARY_FAILED"] if status == "blocked" else []}
            (out / "result.json").write_text(json.dumps(result))
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
        (out / "result.json").write_text(json.dumps(recorded))
        return {"status": "pass"}

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
        (out / lab.RESULT_NAME).write_text(json.dumps(result))
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
        (out / witness.RESULT_NAME).write_text(json.dumps(recorded))
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
