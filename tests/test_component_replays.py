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
