"""Isolated strict bridge to the pinned generated Dafny admission kernel."""

from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys

SPEC_FIELDS = frozenset({"component_id", "input_ref", "evidence_class", "claim_digest", "native_kind"})
OBS_FIELDS = frozenset({
    "component_id", "runner_component_id", "receipt_component_id", "input_ref",
    "evidence_class", "claim_digest", "source_before", "source_after", "input_before",
    "input_after", "runner_payload_digest", "receipt_payload_digest", "receipt_digest",
    "runner_status", "receipt_status", "runner_verdict", "receipt_verdict",
    "runner_native_kind", "receipt_native_kind", "receipt_present",
})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate request key")
        result[key] = value
    return result


def _strict_rows(rows, fields, bool_field=None):
    if type(rows) is not list:
        raise ValueError("rows must be a list")
    for row in rows:
        if type(row) is not dict or set(row) != fields:
            raise ValueError("wrong row fields")
        for key, value in row.items():
            if key == bool_field:
                if type(value) is not bool:
                    raise ValueError("wrong presence type")
            elif type(value) is not int:
                raise ValueError("wrong integer observation type")


def main() -> int:
    try:
        request = json.loads(sys.stdin.read(), object_pairs_hook=_unique_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if type(request) is not dict or set(request) != {"specs", "source", "observations"}:
            raise ValueError("wrong request fields")
        if type(request["source"]) is not int:
            raise ValueError("source must be an integer identity")
        _strict_rows(request["specs"], SPEC_FIELDS)
        _strict_rows(request["observations"], OBS_FIELDS, "receipt_present")
        loader = runpy.run_path(str(Path(__file__).resolve().parents[1] / "_sealed_kernel.py"))
        generated = Path(__file__).resolve().parent / "_generated"
        with loader["sealed_kernel"](generated, "ReplayAdmission"):
            import _dafny
            import ReplayAdmission

            specs = _dafny.Seq([
                ReplayAdmission.Spec_Spec(row["component_id"], row["input_ref"],
                    row["evidence_class"], row["claim_digest"], row["native_kind"])
                for row in request["specs"]
            ])
            observations = _dafny.Seq([
                ReplayAdmission.Observation_Observation(
                    row["component_id"], row["runner_component_id"],
                    row["receipt_component_id"], row["input_ref"],
                    row["evidence_class"], row["claim_digest"],
                    row["source_before"], row["source_after"],
                    row["input_before"], row["input_after"],
                    row["runner_payload_digest"], row["receipt_payload_digest"],
                    row["receipt_digest"], row["runner_status"],
                    row["receipt_status"], row["runner_verdict"],
                    row["receipt_verdict"], row["runner_native_kind"],
                    row["receipt_native_kind"], row["receipt_present"])
                for row in request["observations"]
            ])
            accepted = ReplayAdmission.default__.Check(specs, request["source"], observations)
        if type(accepted) is not bool:
            raise ValueError("generated checker returned a nonboolean")
        print(json.dumps({"accepted": accepted}))
        return 0
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as error:
        print(json.dumps({"error": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
