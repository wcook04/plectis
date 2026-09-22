"""Source-bound demo cards remain cheap and cannot promote archived evidence."""
from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from microcosm_core import runtime_shell
from microcosm_core.runtime_shell import RuntimeShell, RuntimeStep


@pytest.fixture
def recorded_demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "public"
    (root / "examples/probe").mkdir(parents=True)
    (root / "core").mkdir()
    (root / "core/policy.json").write_text('{"revision": 1}\n')
    (root / "examples/probe/input.json").write_text('{"value": 1}\n')
    (root / "examples/probe/project_manifest.json").write_text('{"project_id": "probe"}\n')

    def runner(input_dir: Path, output_dir: Path, command: str):
        result = {"status": "pass", "value": json.loads((input_dir / "input.json").read_text())["value"]}
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "result.json").write_text(json.dumps(result))
        return result

    step = RuntimeStep("probe", "probe", "fixture_input", "examples/probe", runner, "result.json")
    monkeypatch.setattr(runtime_shell, "_product_runtime_steps", lambda: [step])
    monkeypatch.setenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", "1")
    shell = RuntimeShell(root)
    result = shell.run_demo("examples/probe")
    assert result["input_binding"]["status"] == "bound"
    monkeypatch.setattr(shell, "run_demo", lambda *a, **kw: pytest.fail("card read replayed the demo"))
    return root, shell, step


def test_demo_binding_survives_independent_clone(recorded_demo, tmp_path: Path):
    root, shell, _ = recorded_demo
    assert shell.run_demo_card("examples/probe")["cache_freshness"]["status"] == "current"
    clone = tmp_path / "clone"
    shutil.copytree(root, clone)
    assert RuntimeShell(clone).run_demo_card("examples/probe")["cache_freshness"]["status"] == "current"


@pytest.mark.parametrize("mutation", ["fixture", "policy", "new_input", "missing_input", "evidence", "missing_evidence", "selected_steps", "toolchain", "code", "unbound", "result"])
def test_demo_card_rejects_changed_inputs_without_replay(recorded_demo, monkeypatch, mutation):
    root, shell, step = recorded_demo
    result_path = root / "receipts/runtime_shell/probe/demo_project_result.json"
    evidence_path = root / "receipts/runtime_shell/probe/organs/probe/result.json"
    if mutation == "fixture":
        (root / "examples/probe/input.json").write_text('{"value": 2}\n')
    elif mutation == "policy":
        (root / "core/policy.json").write_text('{"revision": 2}\n')
    elif mutation == "new_input":
        (root / "core/new-policy.json").write_text('{}\n')
    elif mutation == "missing_input":
        (root / "examples/probe/input.json").unlink()
    elif mutation == "evidence":
        evidence_path.write_text('{"status":"blocked"}\n')
    elif mutation == "missing_evidence":
        evidence_path.unlink()
    elif mutation == "selected_steps":
        monkeypatch.setattr(runtime_shell, "_product_runtime_steps", lambda: [replace(step, organ_id="other")])
    elif mutation == "toolchain":
        monkeypatch.setattr(runtime_shell.sys, "version", "different Python")
    elif mutation == "code":
        replacement = root.parent / "runtime/runtime_shell.py"
        replacement.parent.mkdir()
        replacement.write_text("# changed checker\n")
        monkeypatch.setattr(runtime_shell, "__file__", str(replacement))
    else:
        payload = json.loads(result_path.read_text())
        if mutation == "unbound":
            payload.pop("input_binding")
        else:
            payload["events"][0]["status"] = "blocked"
        result_path.write_text(json.dumps(payload))
    card = shell.run_demo_card("examples/probe")
    assert card["status"] == "stale_cached_result"
    assert card["cache_freshness"]["status"].startswith("stale_")


def test_demo_cache_rejects_malformed_json(recorded_demo):
    root, shell, _ = recorded_demo
    (root / "receipts/runtime_shell/probe/demo_project_result.json").write_text('{"broken":')
    assert shell._cached_runtime_demo_result("examples/probe") is None
