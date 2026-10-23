"""Public graph API and unproved host boundaries that affect safe reuse."""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

from plectis.repair import (
    EffectJournal, InvalidPlan, RepairSession, Task, check_plan, make_plan,
)
from plectis.repair import _host


def pure(callback, *, inputs=None):
    return Task("a", code_id="test/a", version="1", inputs=inputs,
                contract="json", environment="fixed", freshness="fixed",
                replayable=True, fn=callback)


def test_independent_graph_producer_and_candidate_checker():
    deps = ((), (0,), (1,), ())
    roots = (True, False, False, False)
    effects = (False, True, False, False)
    dirty, blocked = make_plan(deps, roots, effects)
    assert dirty == (True, True, True, False)
    assert blocked == (False, True, True, False)
    assert check_plan(deps, roots, effects, dirty, blocked)
    assert not check_plan(deps, roots, effects, dirty, (False,) * 4)
    assert not check_plan(deps, roots, effects, (True,) * 4, blocked)
    assert make_plan([], [], []) == ((), ())
    assert check_plan([], [], [], [], [])


@pytest.mark.parametrize("deps,roots,effects", [
    ([[], [False]], [True, False], [False, False]),
    ([[0]], [True], [False]),
    ([[], [-1]], [True, False], [False, False]),
    ([[]], [1], [False]),
    ([[]], [True], [0]),
    ([[]], [True], []),
    (object(), [], []),
])
def test_public_producer_rejects_malformed_typed_domain(deps, roots, effects):
    with pytest.raises(InvalidPlan):
        make_plan(deps, roots, effects)


def test_public_checker_rejects_integer_flags():
    with pytest.raises(InvalidPlan):
        check_plan([[]], [True], [False], [1], [False])


def test_worker_failure_has_no_fallback(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 30)
    monkeypatch.setattr(_host.subprocess, "run", timeout)
    with pytest.raises(InvalidPlan, match="kernel request failed"):
        make_plan([[]], [True], [False])


def test_malformed_worker_response_is_rejected(monkeypatch):
    monkeypatch.setattr(_host.subprocess, "run", lambda *a, **k:
                        subprocess.CompletedProcess(a[0], 0, stdout="[]"))
    with pytest.raises(InvalidPlan, match="non-object"):
        make_plan([[]], [True], [False])


def test_undeclared_file_change_is_explicitly_outside_reuse_contract(tmp_path):
    source = tmp_path / "hidden.txt"
    source.write_text("first")
    task = pure(lambda inputs, deps: source.read_text())
    old = RepairSession([task])
    old.run(old.plan())
    source.write_text("second")
    changed = RepairSession([task], records=old.records)
    # This is the documented limitation, not a freshness guarantee. The host
    # cannot discover a file read that the caller omitted from its identity.
    assert changed.run(changed.plan()).outputs["a"] == "first"
    declared = RepairSession([pure(lambda inputs, deps: source.read_text(),
                                   inputs={"snapshot": "second"})], records=old.records)
    assert declared.run(declared.plan()).outputs["a"] == "second"


def test_callback_change_requires_declared_identity_change():
    old = RepairSession([pure(lambda inputs, deps: 1)])
    old.run(old.plan())
    changed = RepairSession([pure(lambda inputs, deps: 2)], records=old.records)
    assert changed.plan().classification() == {"a": "reuse"}
    assert changed.run(changed.plan()).outputs["a"] == 1


def test_unknown_effect_survives_new_process_and_graph_pruning(tmp_path):
    checkpoint, journal = tmp_path / "checkpoint.json", tmp_path / "effects.jsonl"
    effect = Task("effect", code_id="test/effect", version="1", contract="json",
                  environment="fixed", freshness="fixed")
    session = RepairSession([effect], checkpoint=checkpoint, journal=journal)
    attempt = session.begin_effect("effect")
    session.mark_unknown(attempt, "local acknowledgement lost")
    # A fresh interpreter reloads the persistent journal. Explicit source path
    # supports no-install source checks; distribution tests exercise imports
    # without this path separately.
    code = """import json,sys
sys.path.insert(0,sys.argv[1])
from plectis.repair import RepairSession
s=RepairSession([],checkpoint=sys.argv[2],journal=sys.argv[3])
r=s.run(s.plan())
print(json.dumps({'settled':r.settled,'unknown':r.unresolved_effects}))
"""
    source_root = Path(_host.__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code,
                             str(source_root), str(checkpoint), str(journal)],
                            cwd=tmp_path, text=True, capture_output=True, check=True)
    observed = json.loads(result.stdout)
    assert observed == {"settled": False,
                        "unknown": [{"attempt": attempt, "task": "effect", "status": "unknown"}]}
    assert EffectJournal(journal).unresolved()[0]["attempt"] == attempt


@pytest.mark.parametrize("records", [[], [1], "invalid", True])
def test_initial_records_require_an_object(records):
    with pytest.raises(ValueError, match="records must be an object"):
        RepairSession([], records=records)


def test_checkpoint_format_boolean_is_not_version_one(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text('{"format":true,"records":{}}')
    with pytest.raises(ValueError, match="malformed checkpoint"):
        RepairSession([], checkpoint=checkpoint)


def test_quick_binding_check_rejects_changed_formal_and_generated_bytes(tmp_path):
    root = Path(__file__).resolve().parents[1]
    checker = runpy.run_path(str(root / "scripts/check/check_repair_kernel.py"))
    formal = tmp_path / "formal/repair"
    generated = tmp_path / "generated"
    shutil.copytree(root / "formal/repair", formal)
    shutil.copytree(Path(_host.__file__).with_name("_generated"), generated)
    checker["check_binding"](tmp_path, generated)
    source = formal / "Repair.dfy"
    original = source.read_bytes()
    source.write_bytes(original + b"\n// altered\n")
    with pytest.raises(ValueError, match="formal source identity changed"):
        checker["check_binding"](tmp_path, generated)
    source.write_bytes(original)
    kernel = generated / "Repair.py"
    kernel.write_bytes(kernel.read_bytes() + b"\n# altered\n")
    with pytest.raises(ValueError, match="generated Python identity changed"):
        checker["check_binding"](tmp_path, generated)
