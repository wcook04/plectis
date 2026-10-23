"""Every proposed negative is checked against the current finite models."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from plectis.compatibility import check_counterexample, compare
from plectis.compatibility import _api


ROOT = Path(__file__).resolve().parents[1]


def machine(output="ok"):
    return {"name": "example", "initial": "idle", "inputs": ["go", "wait"],
            "states": {"idle": {"go": {"next": "idle", "output": output}}}}


@pytest.mark.parametrize("kind", ["output_mismatch", "missing_input"])
def test_fresh_negatives_are_independently_confirmed(kind):
    old, new = machine(), machine("changed")
    if kind == "missing_input":
        new["states"]["idle"].clear()
    result = compare(old, new)
    assert result == {"accepted": False, "continuation": ["go"], "reason": kind,
                      "approved_outputs": ["ok"],
                      "candidate_outputs": [] if kind == "missing_input" else ["changed"]}
    assert check_counterexample(json.dumps(old), json.dumps(new), result["continuation"])
    # A proposed word is rechecked after a candidate or requirement changes.
    assert not check_counterexample(old, old, result["continuation"])
    assert not check_counterexample(new, new, result["continuation"])


@pytest.mark.parametrize("word", [[], ["wait"], ["unknown"], ["wait", "go"],
                                  ["unknown", "go"]])
def test_stale_or_disabled_prefixes_are_not_counterexamples(word):
    assert not check_counterexample(machine(), machine("changed"), word)


@pytest.mark.parametrize("suffix", [["wait"], ["unknown"], ["wait", "go"]])
def test_earlier_bad_prefix_survives_a_stale_suffix(suffix):
    assert check_counterexample(machine(), machine("changed"), ["go"] + suffix)


def test_candidate_additions_and_empty_alphabets_are_not_failures():
    old, new = machine(), machine()
    new["states"]["idle"]["wait"] = {"next": "idle", "output": "new"}
    assert not check_counterexample(old, new, ["wait"])
    empty = {"name": "empty", "initial": "s", "inputs": [], "states": {"s": {}}}
    assert not check_counterexample(empty, empty, ["unknown"])
    assert compare(empty, empty)["accepted"]


def test_a_silent_word_is_not_approval_and_outputs_are_exact_labels():
    old, new = machine(), machine()
    for model, output in ((old, "unknown"), (new, "error")):
        model["states"]["idle"]["wait"] = {"next": "idle", "output": output}
    assert not check_counterexample(old, new, ["go"])
    assert check_counterexample(old, new, ["wait"])
    assert not compare(old, new)["accepted"]


@pytest.mark.parametrize("word", [None, True, 1, "go", ("go",), {}, [1], [True],
                                  [None], [""], [["go"]]])
def test_malformed_word_proposals_are_not_evidence(monkeypatch, word):
    def unexpected(*args, **kwargs):
        pytest.fail("malformed word reached the generated worker")
    monkeypatch.setattr(_api.subprocess, "run", unexpected)
    assert not check_counterexample(machine(), machine("changed"), word)


def test_malformed_models_are_not_evidence():
    bad = machine()
    bad["states"]["idle"]["go"]["next"] = "absent"
    assert not check_counterexample(bad, machine(), ["go"])
    assert not check_counterexample(machine(), bad, ["go"])
    assert not check_counterexample('{"name":"x","name":"y"}', machine(), ["go"])


def test_an_incorrect_search_proposal_cannot_be_returned(monkeypatch):
    monkeypatch.setattr(_api, "_continuation", lambda *args: ["unknown"])
    with pytest.raises(RuntimeError, match="rejected the searched counterexample"):
        compare(machine(), machine("changed"))


def test_negative_results_require_the_checker_even_after_search(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("unavailable")
    monkeypatch.setattr(_api.subprocess, "run", unavailable)
    with pytest.raises(RuntimeError):
        compare(machine(), machine("changed"))
    with pytest.raises(RuntimeError):
        check_counterexample(machine(), machine("changed"), ["go"])


@pytest.mark.parametrize("response", ['{"mismatch":1}', '{"mismatch":"true"}',
                                      '{"accepted":true}', '{}', 'null', '[]',
                                      '{"mismatch":true,"extra":0}',
                                      '{"mismatch":false,"mismatch":true}',
                                      '{"mismatch":NaN}'])
def test_malformed_worker_output_cannot_confirm_a_witness(monkeypatch, response):
    monkeypatch.setattr(_api.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, stdout=response))
    with pytest.raises(RuntimeError):
        check_counterexample(machine(), machine("changed"), ["go"])


def test_nonzero_worker_exit_cannot_confirm_a_witness(monkeypatch):
    monkeypatch.setattr(_api.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 2, stdout='{"mismatch":true}'))
    with pytest.raises(RuntimeError):
        check_counterexample(machine(), machine("changed"), ["go"])


def test_worker_rejects_malformed_words_and_invalid_models():
    request = _api._encode(machine(), machine("changed"), set())
    request.pop("relation")
    request["word"] = [0]
    worker = ROOT / "src/plectis/compatibility/_worker.py"
    for field, value in (("word", [True]), ("word", ["0"]), ("word", {}),
                         ("old_initial", -1), ("old_next", [[2, -1]]),
                         ("new_output", []), ("inputs", True)):
        bad = deepcopy(request)
        bad[field] = value
        result = subprocess.run([sys.executable, "-I", "-B", str(worker)],
                                input=json.dumps(bad), text=True, capture_output=True,
                                timeout=15, check=False)
        assert result.returncode == 2, result.stderr
        assert set(json.loads(result.stdout)) == {"error"}


def test_generated_witnesses_against_an_independent_small_trace_oracle():
    """Every two-state/one-input pair and bounded stale-word placement.

    This finite check tests the independent intended meaning, not search or
    proof completeness. One isolated import avoids thousands of worker starts.
    """
    code = r'''
from itertools import product
from pathlib import Path
import runpy, sys
root = Path(sys.argv[1])
loader = runpy.run_path(str(root / "src/plectis/_sealed_kernel.py"))
with loader["sealed_kernel"](root / "src/plectis/compatibility/_generated", "Compatibility"):
    import _dafny, Replay
    options = [None] + list(product(range(2), range(2)))
    tables = list(product(options, repeat=2))
    words = [()] + [(0,) * size for size in range(1, 5)]
    words += [(0,) * before + (stale,) + (0,) * after
              for stale in (-1, 1) for before in range(4) for after in range(3)]
    def model(edges):
        return Replay.Model_Model(
            _dafny.Seq([_dafny.Seq([-1 if e is None else e[0]]) for e in edges]),
            _dafny.Seq([_dafny.Seq([-1 if e is None else e[1]]) for e in edges]), 0, 1)
    def oracle(old, new, word):
        s = t = 0
        for action in word:
            if action != 0 or old[s] is None:
                return False
            if new[t] is None or old[s][1] != new[t][1]:
                return True
            s, t = old[s][0], new[t][0]
        return False
    count = 0
    for old, new in product(tables, repeat=2):
        approved, candidate = model(old), model(new)
        assert Replay.default__.ValidPair(approved, candidate)
        for word in words:
            actual = Replay.default__.Mismatch(approved, candidate, _dafny.Seq(word))
            assert type(actual) is bool and actual == oracle(old, new, word), (old, new, word)
            count += 1
    print(count)
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(ROOT)],
                            text=True, capture_output=True, check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "18125"
