"""Host-observation mutants around the generated replay admission checker."""

from __future__ import annotations

import hashlib

import pytest

from plectis.replay import accept


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def spec(component="alpha", native=0):
    return {"component_id": component, "input_ref": "examples/" + component,
            "evidence_class": "semantic_validator", "claim_digest": sha("claim:" + component),
            "native_kind": native}


def observation(component="alpha", native=0):
    return {"component_id": component, "runner_component_id": component,
            "receipt_component_id": component, "input_ref": "examples/" + component,
            "evidence_class": "semantic_validator", "claim_digest": sha("claim:" + component),
            "source_before": sha("source"), "source_after": sha("source"),
            "input_before": sha("input:" + component),
            "input_after": sha("input:" + component),
            "runner_payload_digest": sha("payload:" + component),
            "receipt_payload_digest": sha("payload:" + component),
            "receipt_digest": sha("receipt:" + component),
            "runner_status": "pass", "receipt_status": "pass",
            "runner_verdict": "pass", "receipt_verdict": "pass",
            "runner_native_kind": native, "receipt_native_kind": native,
            "receipt_present": True}


def test_exact_coverage_and_subset():
    specs = [spec("alpha"), spec("beta")]
    rows = [observation("beta"), observation("alpha")]
    assert accept(specs, sha("source"), rows)
    assert accept(specs[:1], sha("source"), rows[1:])
    assert not accept([], sha("source"), [])
    assert not accept(specs, sha("source"), rows[:1])
    assert not accept([spec("alpha"), spec("alpha")], sha("source"), rows)
    assert not accept(specs, sha("source"), [rows[0], rows[0]])
    assert not accept(specs, sha("source"), [rows[1], observation("gamma")])


@pytest.mark.parametrize("key,value", [
    ("runner_component_id", "wrong"),
    ("receipt_component_id", None),
    ("input_ref", "examples/wrong"),
    ("evidence_class", "fixture_only"),
    ("claim_digest", sha("other claim")),
    ("source_before", sha("old source")),
    ("source_after", sha("changed source")),
    ("input_after", sha("changed input")),
    ("runner_payload_digest", sha("other payload")),
    ("receipt_payload_digest", sha("other payload")),
    ("receipt_digest", None),
    ("runner_status", "blocked"),
    ("receipt_status", "blocked"),
    ("runner_verdict", "error"),
    ("receipt_verdict", "error"),
    ("runner_native_kind", 1),
    ("receipt_native_kind", 1),
    ("receipt_present", False),
])
def test_observed_binding_mutants_reject(key, value):
    row = observation()
    row[key] = value
    assert not accept([spec()], sha("source"), [row])


def test_required_native_witness_and_malformed_input_reject():
    assert accept([spec(native=2)], sha("source"), [observation(native=2)])
    assert not accept([spec(native=2)], sha("source"), [observation()])
    assert not accept([spec(native=3)], sha("source"), [observation()])
    assert not accept([spec()], "not-a-sha256", [observation()])
    assert not accept([spec()], sha("source"), [{**observation(), "extra": True}])
