"""Behavioural comparison, certificate tampering and the unproved boundary."""

import copy
from itertools import product
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from plectis.compatibility import InvalidMachine, check_certificate, compare
from plectis.compatibility import _api


ROOT = Path(__file__).resolve().parents[1]


def machine(output="ready", *, name="contract"):
    return {"name": name, "initial": "idle", "inputs": ["read"],
            "states": {"idle": {"read": {"next": "idle", "output": output}}}}


def test_accepts_extension_with_different_states_and_added_inputs():
    old, new = machine(), machine(name="candidate")
    new["inputs"].append("new")
    new["states"] = {"start": {"read": {"next": "start", "output": "ready"},
                               "new": {"next": "added", "output": "anything"}},
                     "added": {}}
    new["initial"] = "start"
    result = compare(old, new)
    assert result["accepted"]
    assert result["certificate"]["relation"] == [["idle", "start"]]
    assert check_certificate(json.dumps(old), json.dumps(new),
                             json.dumps(result["certificate"]))
    # A continuation after candidate-only input is outside the approved domain.
    assert new["states"]["added"] == {}


def test_returns_a_shortest_stable_distinguishing_continuation():
    old = {"name": "old", "initial": "s", "inputs": ["z", "a", "next"],
           "states": {"s": {"next": {"next": "later", "output": "ok"},
                              "a": {"next": "s", "output": "error"},
                              "z": {"next": "s", "output": "unknown"}},
                      "later": {"a": {"next": "later", "output": "good"}}}}
    new = copy.deepcopy(old)
    new["states"]["later"]["a"]["output"] = "bad"
    assert compare(old, new) == {
        "accepted": False, "continuation": ["next", "a"],
        "reason": "output_mismatch", "approved_outputs": ["ok", "good"],
        "candidate_outputs": ["ok", "bad"]}
    new["states"]["s"]["z"]["output"] = "ok"
    new["states"]["s"]["a"]["output"] = "ok"
    assert compare(old, new)["continuation"] == ["a"]


def test_removing_required_input_is_not_vacuous_compatibility():
    old, new = machine("error"), machine("error")
    new["inputs"] = []
    new["states"]["idle"] = {}
    assert compare(old, new) == {
        "accepted": False, "continuation": ["read"], "reason": "missing_input",
        "approved_outputs": ["error"], "candidate_outputs": []}
    # Direction matters: an empty approved domain imposes no enabled-edge duty.
    assert compare(new, old)["accepted"]


def test_no_fixed_search_depth_and_cycles_terminate():
    old = {"name": "chain", "initial": "0", "inputs": ["advance", "wait"],
           "states": {str(i): {"advance": {"next": str(min(i + 1, 17)),
                                           "output": "ok"},
                               "wait": {"next": str(i), "output": "ok"}}
                      for i in range(18)}}
    new = copy.deepcopy(old)
    new["states"]["17"]["advance"]["output"] = "changed"
    assert compare(old, new)["continuation"] == ["advance"] * 18
    assert compare(old, old)["accepted"]


def test_certificate_is_bound_to_both_models_and_behaviour_is_rechecked():
    old, new = machine(), machine(name="candidate")
    certificate = compare(old, new)["certificate"]
    changed = machine("broken", name="candidate")
    assert not check_certificate(old, changed, certificate)
    # Rehashing a forged model does not make its false relation acceptable.
    forged = copy.deepcopy(certificate)
    forged["candidate_sha256"] = _api._digest(changed)
    assert not check_certificate(old, changed, forged)
    changed_old = machine(name="different approval")
    assert not check_certificate(changed_old, new, certificate)
    for relation in ([], [["idle", "idle"], ["idle", "idle"]],
                     [["absent", "idle"]], [[False, "idle"]]):
        forged = dict(certificate, relation=relation)
        assert not check_certificate(old, new, forged)
    assert not check_certificate(old, new, dict(certificate, schema_version=True))


def test_certificate_requires_successor_closure():
    old = {"name": "old", "initial": "0", "inputs": ["go"],
           "states": {"0": {"go": {"next": "1", "output": "ok"}}, "1": {}}}
    certificate = compare(old, old)["certificate"]
    certificate["relation"] = [["0", "0"]]
    assert not check_certificate(old, old, certificate)


@pytest.mark.parametrize("change", [
    lambda m: m.update(extra=True),
    lambda m: m.update(initial="missing"),
    lambda m: m.update(inputs=["read", "read"]),
    lambda m: m.update(inputs=("read",)),
    lambda m: m.update(name=False),
    lambda m: m.update(states={}),
    lambda m: m["states"]["idle"]["read"].update(next="missing"),
    lambda m: m["states"]["idle"]["read"].update(output=1),
    lambda m: m["states"]["idle"]["read"].update(extra="ignored?"),
    lambda m: m["states"]["idle"].update(undeclared={"next": "idle", "output": "x"}),
])
def test_invalid_models_fail_strictly(change):
    value = machine()
    change(value)
    with pytest.raises(InvalidMachine):
        compare(value, machine())
    assert not check_certificate(value, machine(), {})


def test_duplicate_keys_nonfinite_and_nonobjects_are_rejected():
    for text in ('{"name":"first","name":"second"}', '{"x":NaN}',
                 '{"x":Infinity}', '[]', 'null', 'false'):
        with pytest.raises(InvalidMachine):
            compare(text, machine())
        assert not check_certificate(machine(), machine(), text)


def test_no_fallback_if_generated_checker_fails(monkeypatch):
    certificate = compare(machine(), machine())["certificate"]

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 30)

    monkeypatch.setattr(_api.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="checker failed"):
        check_certificate(machine(), machine(), certificate)
    with pytest.raises(RuntimeError, match="checker failed"):
        compare(machine(), machine())


@pytest.mark.parametrize("response", ['[]', '{"accepted":1}',
                                      '{"accepted":true,"extra":true}',
                                      '{"accepted":false,"accepted":true}'])
def test_malformed_worker_response_is_never_accepted(monkeypatch, response):
    monkeypatch.setattr(_api.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=response))
    with pytest.raises(RuntimeError):
        compare(machine(), machine())


def test_generated_imports_do_not_touch_parent_modules(monkeypatch):
    sentinels = {name: object() for name in ("Compatibility", "module_", "_dafny", "System_")}
    for name, sentinel in sentinels.items():
        monkeypatch.setitem(sys.modules, name, sentinel)
    assert compare(machine(), machine())["accepted"]
    assert all(sys.modules[name] is sentinel for name, sentinel in sentinels.items())


def test_worker_rejects_bool_indices_and_nonboolean_relations():
    request = _api._encode(machine(), machine(), {("idle", "idle")})
    worker = ROOT / "src/plectis/compatibility/_worker.py"
    for field, value in (("inputs", True), ("old_initial", False),
                         ("old_next", [[False]]), ("relation", [[1]])):
        bad = dict(request, **{field: value})
        result = subprocess.run([sys.executable, "-I", "-B", str(worker)],
                                input=json.dumps(bad), text=True,
                                stdout=subprocess.PIPE, check=False)
        assert result.returncode == 2
        assert "error" in json.loads(result.stdout)


def test_source_and_generated_bindings():
    script = runpy.run_path(str(ROOT / "scripts/check/check_compatibility_kernel.py"))
    binding = script["check_binding"](ROOT, ROOT / "src/plectis/compatibility/_generated")
    assert len(binding["source_sha256"]) == 64


def test_exhaustive_two_state_one_input_against_direct_trace_oracle():
    """625 ordered pairs; depth four is complete only for this tiny class."""
    options = [None] + [(target, output) for target in range(2) for output in ("x", "y")]
    machines = []
    for edges in product(options, repeat=2):
        states = {str(i): {} if edge is None else
                  {"a": {"next": str(edge[0]), "output": edge[1]}}
                  for i, edge in enumerate(edges)}
        machines.append({"name": "tiny", "initial": "0", "inputs": ["a"], "states": states})

    def first_difference(old, new):
        s = t = "0"
        for depth in range(1, 5):
            before = old["states"][s].get("a")
            after = new["states"][t].get("a")
            if before is None:
                return None
            if after is None or before["output"] != after["output"]:
                return ["a"] * depth
            s, t = before["next"], after["next"]
        return None

    accepted = 0
    for old, new in product(machines, repeat=2):
        expected = first_difference(old, new)
        result = compare(old, new)
        assert result["accepted"] is (expected is None)
        if expected is not None:
            assert result["continuation"] == expected
        else:
            accepted += 1
    assert accepted == 247
