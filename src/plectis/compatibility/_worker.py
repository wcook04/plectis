"""Strict isolated JSON adapter to unchanged Dafny-generated Check."""

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
    fields = {"old_next", "old_output", "old_initial", "new_next",
              "new_output", "new_initial", "inputs", "relation"}
    if type(value) is not dict or set(value) != fields:
        raise ValueError("wrong request fields")
    for key in ("old_initial", "new_initial", "inputs"):
        if type(value[key]) is not int:
            raise ValueError("indices must be integers")
    for key in ("old_next", "old_output", "new_next", "new_output", "relation"):
        rows = value[key]
        kind = bool if key == "relation" else int
        if (type(rows) is not list or any(type(row) is not list for row in rows)
                or any(type(item) is not kind for row in rows for item in row)):
            raise ValueError("invalid matrix type: " + key)
    return value


def main():
    try:
        request = decode(sys.stdin.read())
        sys.path.insert(0, str(Path(__file__).resolve().parent / "_generated"))
        import _dafny
        import Compatibility
        seq = _dafny.Seq

        def matrix(key):
            return seq([seq(row) for row in request[key]])

        accepted = Compatibility.default__.Check(
            matrix("old_next"), matrix("old_output"), request["old_initial"],
            matrix("new_next"), matrix("new_output"), request["new_initial"],
            request["inputs"], matrix("relation"))
        print(json.dumps({"accepted": bool(accepted)}))
    except (ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
