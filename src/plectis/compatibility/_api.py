"""Unproved adapter and counterexample search for the finite Mealy checker.

Adapted from supplied research return p12's artifacts/refinement/refine.py and
check_certificate.py (23 October 2026); p15's artifact/review_transfer.py and
SPECIFICATION.md informed strict input and non-vacuity checks. The independent
certificate acceptance decision here uses the generated Dafny checker.
"""

from collections import deque
import hashlib
import json
from pathlib import Path
import subprocess
import sys


class InvalidMachine(ValueError):
    """The supplied value is outside the explicit finite-machine format."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(",", ":"))


def _object(value):
    if type(value) is str:
        value = json.loads(value, object_pairs_hook=_unique_object,
                           parse_constant=_bad_constant)
    if type(value) is not dict:
        raise ValueError("expected a JSON object or object text")
    if any(type(key) is not str for key in value):
        raise ValueError("JSON object keys must be strings")
    return value


def _label(value, field):
    if type(value) is not str or not value:
        raise ValueError(field + " must be a nonempty string")


def _machine(value):
    """Validate without Python's bool/int or implicit JSON coercions."""
    try:
        value = _object(value)
        if set(value) != {"name", "initial", "inputs", "states"}:
            raise ValueError("machine fields must be name, initial, inputs, states")
        _label(value["name"], "name")
        _label(value["initial"], "initial")
        inputs, states = value["inputs"], value["states"]
        if type(inputs) is not list:
            raise ValueError("inputs must be a list")
        for action in inputs:
            _label(action, "input")
        if len(set(inputs)) != len(inputs):
            raise ValueError("inputs must be unique")
        if type(states) is not dict or not states:
            raise ValueError("states must be a nonempty object")
        for state in states:
            _label(state, "state")
        if value["initial"] not in states:
            raise ValueError("initial state is absent")
        for transitions in states.values():
            if type(transitions) is not dict:
                raise ValueError("state transitions must be objects")
            for action, transition in transitions.items():
                if type(action) is not str or action not in inputs:
                    raise ValueError("transition uses an undeclared input")
                if (type(transition) is not dict
                        or set(transition) != {"next", "output"}):
                    raise ValueError("transition fields must be next and output")
                if (type(transition["next"]) is not str
                        or transition["next"] not in states):
                    raise ValueError("transition target is absent")
                if type(transition["output"]) is not str:
                    raise ValueError("output must be a string observation label")
        # The snapshot detaches all mutable caller aliases after validation.
        return json.loads(_canonical(value))
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        raise InvalidMachine(str(error)) from error


def _digest(machine):
    return hashlib.sha256(_canonical(machine).encode("ascii")).hexdigest()


def _certificate(approved, candidate, pairs):
    return {"schema_version": 1,
            "approved_sha256": _digest(approved),
            "candidate_sha256": _digest(candidate),
            "relation": [list(pair) for pair in sorted(pairs)]}


def _encode(approved, candidate, pairs):
    actions = sorted(set(approved["inputs"]) | set(candidate["inputs"]))
    labels = sorted({edge["output"] for machine in (approved, candidate)
                     for transitions in machine["states"].values()
                     for edge in transitions.values()})
    output_ids = {label: index for index, label in enumerate(labels)}

    def table(machine):
        names = sorted(machine["states"])
        ids = {name: index for index, name in enumerate(names)}
        next_rows, output_rows = [], []
        for state in names:
            transitions = machine["states"][state]
            next_rows.append([ids[transitions[a]["next"]] if a in transitions else -1
                              for a in actions])
            output_rows.append([output_ids[transitions[a]["output"]]
                                if a in transitions else -1 for a in actions])
        return names, next_rows, output_rows, ids[machine["initial"]]

    old_names, old_next, old_output, old_initial = table(approved)
    new_names, new_next, new_output, new_initial = table(candidate)
    relation = [[(s, t) in pairs for t in new_names] for s in old_names]
    return {"old_next": old_next, "old_output": old_output,
            "old_initial": old_initial, "new_next": new_next,
            "new_output": new_output, "new_initial": new_initial,
            "inputs": len(actions), "relation": relation}


def _generated_check(request):
    worker = Path(__file__).with_name("_worker.py")
    try:
        result = subprocess.run([sys.executable, "-I", "-B", str(worker)],
                                input=_canonical(request), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=False, timeout=30)
        response = _object(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("generated compatibility checker failed") from error
    if (result.returncode or set(response) != {"accepted"}
            or type(response["accepted"]) is not bool):
        raise RuntimeError("generated compatibility checker returned invalid output")
    return response["accepted"]


def check_certificate(approved, candidate, certificate):
    """Check a hash-bound relation with the generated proved checker.

    Malformed or stale certificates return False. Checker/tooling failure raises
    RuntimeError; it never becomes an accepted certificate or a Python fallback.
    Models and certificates may be objects or strict JSON object text.
    """
    try:
        approved, candidate = _machine(approved), _machine(candidate)
        certificate = _object(certificate)
        if (set(certificate) != {"schema_version", "approved_sha256",
                                 "candidate_sha256", "relation"}
                or type(certificate["schema_version"]) is not int
                or certificate["schema_version"] != 1
                or type(certificate["approved_sha256"]) is not str
                or type(certificate["candidate_sha256"]) is not str
                or certificate["approved_sha256"] != _digest(approved)
                or certificate["candidate_sha256"] != _digest(candidate)):
            return False
        relation = certificate["relation"]
        if type(relation) is not list:
            return False
        pairs = set()
        for pair in relation:
            if (type(pair) is not list or len(pair) != 2
                    or type(pair[0]) is not str or type(pair[1]) is not str
                    or pair[0] not in approved["states"]
                    or pair[1] not in candidate["states"]):
                return False
            pairs.add(tuple(pair))
        if len(pairs) != len(relation):
            return False
    except (ValueError, TypeError, KeyError, OverflowError):
        return False
    return _generated_check(_encode(approved, candidate, pairs))


def _continuation(parents, pair, action):
    word = [action]
    while parents[pair] is not None:
        pair, previous = parents[pair]
        word.append(previous)
    return list(reversed(word))


def _observations(machine, word):
    state, outputs = machine["initial"], []
    for action in word:
        edge = machine["states"][state].get(action)
        if edge is None:
            break
        outputs.append(edge["output"])
        state = edge["next"]
    return outputs


def compare(approved, candidate):
    """Return an accepted relation or a shortest distinguishing continuation.

    Every approved-enabled transition is an obligation, including transitions
    labelled error or unknown. Candidate additions are allowed. Search visits
    the finite reachable product, with no user-supplied depth cutoff. Ties use
    sorted input names. Search correctness is tested, not formally proved.
    """
    approved, candidate = _machine(approved), _machine(candidate)
    initial = (approved["initial"], candidate["initial"])
    parents, queue = {initial: None}, deque([initial])
    while queue:
        pair = queue.popleft()
        old = approved["states"][pair[0]]
        new = candidate["states"][pair[1]]
        for action in sorted(old):
            reason = None
            if action not in new:
                reason = "missing_input"
            elif old[action]["output"] != new[action]["output"]:
                reason = "output_mismatch"
            if reason:
                word = _continuation(parents, pair, action)
                return {"accepted": False, "continuation": word, "reason": reason,
                        "approved_outputs": _observations(approved, word),
                        "candidate_outputs": _observations(candidate, word)}
            following = (old[action]["next"], new[action]["next"])
            if following not in parents:
                parents[following] = (pair, action)
                queue.append(following)
    certificate = _certificate(approved, candidate, parents)
    if not check_certificate(approved, candidate, certificate):
        raise RuntimeError("generated checker rejected the searched relation")
    return {"accepted": True, "certificate": certificate}
