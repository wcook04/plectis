"""Strict isolated JSON adapter to generated relation and witness checkers."""

import json
from pathlib import Path
import runpy
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
              "new_output", "new_initial", "inputs"}
    if (type(value) is not dict
            or set(value) not in (fields | {"relation"}, fields | {"word"})):
        raise ValueError("wrong request fields")
    for key in ("old_initial", "new_initial", "inputs"):
        if type(value[key]) is not int:
            raise ValueError("indices must be integers")
    matrices = ["old_next", "old_output", "new_next", "new_output"]
    if "relation" in value:
        matrices.append("relation")
    for key in matrices:
        rows = value[key]
        kind = bool if key == "relation" else int
        if (type(rows) is not list or any(type(row) is not list for row in rows)
                or any(type(item) is not kind for row in rows for item in row)):
            raise ValueError("invalid matrix type: " + key)
    if "word" in value and (type(value["word"]) is not list
                            or any(type(item) is not int for item in value["word"])):
        raise ValueError("word must contain integer indices")
    return value


def main():
    try:
        request = decode(sys.stdin.read())
        loader = runpy.run_path(str(Path(__file__).resolve().parents[1] / "_sealed_kernel.py"))
        with loader["sealed_kernel"](Path(__file__).resolve().parent / "_generated", "Compatibility"):
            import _dafny
            import Compatibility
            seq = _dafny.Seq

            def matrix(key):
                return seq([seq(row) for row in request[key]])

            if "relation" in request:
                accepted = Compatibility.default__.Check(
                    matrix("old_next"), matrix("old_output"), request["old_initial"],
                    matrix("new_next"), matrix("new_output"), request["new_initial"],
                    request["inputs"], matrix("relation"))
                response = {"accepted": accepted}
            else:
                import Replay

                def model(prefix):
                    return Replay.Model_Model(matrix(prefix + "_next"),
                                              matrix(prefix + "_output"),
                                              request[prefix + "_initial"], request["inputs"])

                approved, candidate = model("old"), model("new")
                if not Replay.default__.ValidPair(approved, candidate):
                    raise ValueError("invalid finite models")
                response = {"mismatch": Replay.default__.Mismatch(
                    approved, candidate, seq(request["word"]))}
            if any(type(value) is not bool for value in response.values()):
                raise ValueError("generated checker returned a nonboolean decision")
            print(json.dumps(response))
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
