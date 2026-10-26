"""Strict host bridge to the generated Dafny replay admission decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


SPEC_FIELDS = frozenset({"component_id", "input_ref", "evidence_class",
                         "claim_digest", "native_kind"})
OBS_FIELDS = frozenset({
    "component_id", "runner_component_id", "receipt_component_id", "input_ref",
    "evidence_class", "claim_digest", "source_before", "source_after",
    "input_before", "input_after", "runner_payload_digest",
    "receipt_payload_digest", "receipt_digest", "runner_status",
    "receipt_status", "runner_verdict", "receipt_verdict", "runner_native_kind",
    "receipt_native_kind", "receipt_present",
})
SPEC_IDENTITIES = ("component_id", "input_ref", "evidence_class", "claim_digest")
OBS_IDENTITIES = (
    "component_id", "runner_component_id", "receipt_component_id", "input_ref",
    "evidence_class", "claim_digest", "source_before", "source_after",
    "input_before", "input_after", "runner_payload_digest",
    "receipt_payload_digest", "receipt_digest",
)
OBS_VERDICTS = ("runner_status", "receipt_status", "runner_verdict", "receipt_verdict")


def _token(value: object, kind: str) -> int:
    """Encode exact labels or SHA-256 bytes; zero means absent observation."""
    if value is None or value == "":
        return 0
    if type(value) is not str:
        raise ValueError("identity must be a string or missing")
    if kind in {"runner_component_id", "receipt_component_id"}:
        kind = "component_id"
    if kind in {"source_before", "source_after"}:
        kind = "source_identity"
    if kind in {"input_before", "input_after"}:
        kind = "input_digest"
    if kind in {"runner_payload_digest", "receipt_payload_digest"}:
        kind = "payload_digest"
    digest_kinds = {"claim_digest", "source_identity", "input_digest",
                    "payload_digest", "receipt_digest"}
    if kind in digest_kinds:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("identity must be lowercase SHA-256 hex")
        data = bytes.fromhex(value)
    else:
        data = value.encode("utf-8")
    return int.from_bytes(hashlib.sha256(kind.encode() + b"\0" + data).digest(), "big") + 1


def _kind(value: object) -> int:
    if type(value) is not int or value not in (0, 1, 2):
        raise ValueError("native witness kind must be 0, 1, or 2")
    return value


def _verdict(value: object) -> int:
    if type(value) is not str:
        raise ValueError("status/verdict must be a string")
    return int(value == "pass")


def _record(value: object, fields: frozenset[str]) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("replay evidence has unexpected fields")
    return value


def _encode_spec(value: object) -> dict[str, object]:
    row = _record(value, SPEC_FIELDS)
    result = {key: _token(row[key], key) for key in SPEC_IDENTITIES}
    result["native_kind"] = _kind(row["native_kind"])
    return result


def _encode_observation(value: object) -> dict[str, object]:
    row = _record(value, OBS_FIELDS)
    result = {key: _token(row[key], key) for key in OBS_IDENTITIES}
    result.update({key: _verdict(row[key]) for key in OBS_VERDICTS})
    result["runner_native_kind"] = _kind(row["runner_native_kind"])
    result["receipt_native_kind"] = _kind(row["receipt_native_kind"])
    if type(row["receipt_present"]) is not bool:
        raise ValueError("receipt_present must be a boolean")
    result["receipt_present"] = row["receipt_present"]
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate response key")
        result[key] = value
    return result


def accept(registry_specs: list[dict] | tuple[dict, ...], source_identity: str,
           observations: list[dict] | tuple[dict, ...]) -> bool:
    """Decide admission for one nonempty registry slice and its replay rows.

    Host observations are trusted; invalid evidence rejects. A broken checker
    raises instead of silently falling back to an unverified Python decision.
    """
    try:
        if (type(registry_specs) not in (tuple, list)
                or type(observations) not in (tuple, list)):
            return False
        request = {
            "specs": [_encode_spec(row) for row in registry_specs],
            "source": _token(source_identity, "source_identity"),
            "observations": [_encode_observation(row) for row in observations],
        }
    except (ValueError, TypeError, UnicodeError):
        return False
    worker = Path(__file__).with_name("_worker.py")
    try:
        process = subprocess.run(
            [sys.executable, "-I", "-B", str(worker)],
            input=json.dumps(request, separators=(",", ":"), allow_nan=False),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=30,
        )
        response = json.loads(process.stdout, object_pairs_hook=_unique_object)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("generated replay admission checker failed") from error
    if (process.returncode != 0 or type(response) is not dict
            or set(response) != {"accepted"}
            or type(response["accepted"]) is not bool):
        raise RuntimeError("generated replay admission checker returned invalid output")
    return response["accepted"]
