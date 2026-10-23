"""Isolated, strict JSON boundary to the unchanged Dafny-generated kernel.

Run with ``python -I -B _worker.py``. This module has no fallback planner.
"""
import json
from pathlib import Path
import sys


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def bad_constant(value):
    raise ValueError("non-finite JSON number")


def decode(text):
    value = json.loads(text, object_pairs_hook=unique_object,
                       parse_constant=bad_constant)
    if type(value) is not dict:
        raise ValueError("request must be an object")
    op = value.get("op")
    expected = {"op", "deps", "roots", "effects"}
    if op == "check":
        expected |= {"dirty", "blocked"}
    elif op != "make":
        raise ValueError("unknown operation")
    if set(value) != expected:
        raise ValueError("wrong fields")
    deps = value["deps"]
    if type(deps) is not list:
        raise ValueError("deps must be a list")
    n = len(deps)
    for i, parents in enumerate(deps):
        if type(parents) is not list:
            raise ValueError("parents must be a list")
        for parent in parents:
            # bool is a subclass of int in Python: isinstance is insufficient.
            if type(parent) is not int or not 0 <= parent < i:
                raise ValueError("parents must be integer earlier-node indices")
    for field in expected - {"op", "deps"}:
        flags = value[field]
        if (type(flags) is not list or len(flags) != n
                or any(type(flag) is not bool for flag in flags)):
            raise ValueError(field + " must be a Boolean list of graph length")
    return value


def main():
    try:
        request = decode(sys.stdin.read())
        # Imports are isolated to this short-lived process. The caller's
        # modules named Repair, module_ and _dafny are never changed.
        sys.path.insert(0, str(Path(__file__).resolve().parent / "_generated"))
        import _dafny
        import Repair
        seq = _dafny.Seq
        deps = seq([seq(parents) for parents in request["deps"]])
        roots = seq(request["roots"])
        effects = seq(request["effects"])
        kernel = Repair.default__
        if not kernel.ValidInputs(deps, roots, effects):
            raise ValueError("generated ValidInputs rejected request")
        if request["op"] == "make":
            dirty, blocked = kernel.MakePlan(deps, roots, effects)
            # Always check the producer's result using the generated checker.
            accepted = kernel.CheckPlan(deps, roots, effects, dirty, blocked)
            result = {"accepted": bool(accepted), "dirty": list(dirty),
                      "blocked": list(blocked)}
        else:
            accepted = kernel.CheckPlan(deps, roots, effects,
                                        seq(request["dirty"]),
                                        seq(request["blocked"]))
            result = {"accepted": bool(accepted)}
        print(json.dumps(result, allow_nan=False, separators=(",", ":")))
    except (ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
