"""
[PURPOSE]
- Teleology: Characterize current behavior of all five master_config read loaders
  across missing / empty / malformed / non-object / partial / full input scenarios,
  so any subsequent convergence wave under config plane v2 child slice 2
  (loader ownership) starts from a known parity matrix instead of inferred safety.
- Mechanism: For each scenario, write (or omit) master_config.json under tmp_path,
  monkeypatch the global REPO_ROOT for loaders that read it, call each loader,
  and capture either its return value or the exception class it raises.

[INTERFACE]
- Tests one characterization assertion per (scenario, loader) cell; the expected
  matrix is encoded explicitly. Divergence is documented, not converged.

[FLOW]
- This is intentionally a characterization test. If a loader's behavior is
  intentionally changed later, update the matrix in this file as part of that change.

[CONSTRAINTS]
- No test mutates the live repository config.
- No test asserts what a loader "should" do — only what it currently does.
- Server reader's pre-existing intolerance (raise on malformed, pass-through
  non-dict) is recorded as the documented divergence; converging it requires
  caller-impact analysis under the loader-ownership child slice.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


SAMPLE_FULL = {
    "bridge": {"debug_port": {"value": 9222}, "default_target": "chatgpt"},
    "execution": {"max_workers": {"value": 8}},
    "observe": {"default_launch_profile": {"value": "experimental"}},
    "pipeline": {"orchestrator_primary": {"value": "codex"}},
    "paths": {"runs_dir": {"value": "state/runs"}},
    "ui": {"node_width": 220},
}

SAMPLE_PARTIAL = {"bridge": {"debug_port": {"value": 9222}}}


def _write(tmp_path: Path, content: str | None) -> None:
    """Write content to tmp_path/master_config.json, or skip when content is None."""
    if content is None:
        return
    (tmp_path / "master_config.json").write_text(content, encoding="utf-8")


def _scenario_payload(scenario: str) -> str | None:
    if scenario == "missing_file":
        return None
    if scenario == "empty_file":
        return ""
    if scenario == "malformed_json":
        return "{not json"
    if scenario == "non_object_array":
        return "[]"
    if scenario == "partial_object":
        return json.dumps(SAMPLE_PARTIAL)
    if scenario == "full_object":
        return json.dumps(SAMPLE_FULL)
    raise ValueError(f"unknown scenario: {scenario}")


def _call_loader(name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Call one loader against tmp_path master_config.json. Returns value or raises."""
    if name == "kernel_canonical":
        # No repo_root arg; reads system.lib.kernel.state.REPO_ROOT, which is
        # declared at module load and assigned via state.init() at runtime —
        # may be unset on fresh import, so use raising=False.
        from system.lib.kernel import config as kernel_config
        from system.lib.kernel import state as kernel_state
        monkeypatch.setattr(kernel_state, "REPO_ROOT", tmp_path, raising=False)
        return kernel_config.load_master_config()
    if name == "server_reader":
        # No repo_root arg; reads system.server.main.REPO_ROOT.
        from system.server import main as server_main
        monkeypatch.setattr(server_main, "REPO_ROOT", tmp_path)
        return server_main._read_master_config()
    if name == "observe_runtime":
        from system.lib import observe_runtime
        return observe_runtime.load_master_config(tmp_path)
    if name == "pipeline_control":
        import pipeline_control
        return pipeline_control.load_master_config(tmp_path)
    if name == "run_observe_plan":
        from tools.meta.apply import run_observe_plan
        return run_observe_plan._load_master_config(tmp_path)
    raise ValueError(f"unknown loader: {name}")


# Expected behavior matrix.
# Each cell is one of:
#   ("ok", expected_value)
#   ("raises", expected_exception_class_name)
#
# The server_reader cells encode the documented divergence: raises on malformed
# and on empty input (json.load(""))), and passes through non-dict types.
EXPECTED_MATRIX: dict[tuple[str, str], tuple[str, object]] = {
    # missing_file: every loader returns {} (every loader has if-not-exists guard).
    ("missing_file", "kernel_canonical"): ("ok", {}),
    ("missing_file", "server_reader"): ("ok", {}),
    ("missing_file", "observe_runtime"): ("ok", {}),
    ("missing_file", "pipeline_control"): ("ok", {}),
    ("missing_file", "run_observe_plan"): ("ok", {}),

    # empty_file: every loader tolerates and returns {}.
    ("empty_file", "kernel_canonical"): ("ok", {}),
    ("empty_file", "server_reader"): ("ok", {}),
    ("empty_file", "observe_runtime"): ("ok", {}),
    ("empty_file", "pipeline_control"): ("ok", {}),
    ("empty_file", "run_observe_plan"): ("ok", {}),

    # malformed_json: every loader tolerates and returns {}.
    ("malformed_json", "kernel_canonical"): ("ok", {}),
    ("malformed_json", "server_reader"): ("ok", {}),
    ("malformed_json", "observe_runtime"): ("ok", {}),
    ("malformed_json", "pipeline_control"): ("ok", {}),
    ("malformed_json", "run_observe_plan"): ("ok", {}),

    # non_object_array: every loader coerces to {}.
    ("non_object_array", "kernel_canonical"): ("ok", {}),
    ("non_object_array", "server_reader"): ("ok", {}),
    ("non_object_array", "observe_runtime"): ("ok", {}),
    ("non_object_array", "pipeline_control"): ("ok", {}),
    ("non_object_array", "run_observe_plan"): ("ok", {}),

    # partial_object and full_object: every loader passes the dict through.
    ("partial_object", "kernel_canonical"): ("ok", SAMPLE_PARTIAL),
    ("partial_object", "server_reader"): ("ok", SAMPLE_PARTIAL),
    ("partial_object", "observe_runtime"): ("ok", SAMPLE_PARTIAL),
    ("partial_object", "pipeline_control"): ("ok", SAMPLE_PARTIAL),
    ("partial_object", "run_observe_plan"): ("ok", SAMPLE_PARTIAL),

    ("full_object", "kernel_canonical"): ("ok", SAMPLE_FULL),
    ("full_object", "server_reader"): ("ok", SAMPLE_FULL),
    ("full_object", "observe_runtime"): ("ok", SAMPLE_FULL),
    ("full_object", "pipeline_control"): ("ok", SAMPLE_FULL),
    ("full_object", "run_observe_plan"): ("ok", SAMPLE_FULL),
}


@pytest.mark.parametrize("scenario", [
    "missing_file", "empty_file", "malformed_json",
    "non_object_array", "partial_object", "full_object",
])
@pytest.mark.parametrize("loader", [
    "kernel_canonical", "server_reader", "observe_runtime",
    "pipeline_control", "run_observe_plan",
])
def test_master_config_loader_parity(
    scenario: str,
    loader: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_kind, expected_value = EXPECTED_MATRIX[(scenario, loader)]
    _write(tmp_path, _scenario_payload(scenario))

    if expected_kind == "raises":
        with pytest.raises(Exception) as exc_info:
            _call_loader(loader, tmp_path, monkeypatch)
        actual_class_name = type(exc_info.value).__name__
        assert actual_class_name == expected_value, (
            f"{loader}/{scenario}: expected {expected_value}, got {actual_class_name}"
        )
        return

    actual = _call_loader(loader, tmp_path, monkeypatch)
    assert actual == expected_value, (
        f"{loader}/{scenario}: expected {expected_value!r}, got {actual!r}"
    )
