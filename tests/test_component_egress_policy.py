from __future__ import annotations

import itertools
import re

import pytest

from microcosm_core.engine_room import egress_self_compliance_gate as gate
from plectis.components.egress_policy import evaluate


def _legacy_matches(text, phrases):
    result = []
    for phrase in phrases:
        left = r"(?<![a-z0-9])" if phrase[:1].isalnum() else ""
        right = r"(?![a-z0-9])" if phrase[-1:].isalnum() else ""
        if re.search(f"{left}{re.escape(phrase)}{right}", text):
            result.append(phrase)
    return tuple(result)


def test_real_matcher_matches_original_regex_on_boundaries_and_unicode():
    phrases = ("passed", "i ran", "cap_", "ran:", "", "é", "passed", "a.b")
    for text in ("bypassed", "passedly", "passed", "i ranked", "i ran:",
                 "cap_demo", "écap_", "é", "é1", "1é", "a.b", "a\nb", ""):
        assert gate._matches(text, phrases) == _legacy_matches(text, phrases)


def test_codepoint_scan_preserves_ascii_edges_for_unicode_and_lowercase_expansion():
    import importlib
    from pathlib import Path
    from plectis._sealed_kernel import sealed_kernel
    from plectis.components.egress_policy._adapter import evaluate as adapter

    generated = Path(__file__).resolve().parents[1] / "src/plectis/components/egress_policy/_generated"
    phrases = ["a", "é", "𐐨", "\u0307", "_", "a_", "_a", "a.b", "", "a"]
    edges = ("", "a", "9", "A", "_", "é", "𐐨", "\u0307", "\n", "\x00")
    texts = {left + phrase + right for phrase in phrases for left in edges for right in edges}
    texts.update(gate._body(value) for value in ("İ A", "K a", "𐐀 a", "ÉA", "AÉ", None, 0))
    with sealed_kernel(generated, "EgressPolicy"):
        kernel = importlib.import_module("EgressPolicy")
        dafny = importlib.import_module("_dafny")
        for text in texts:
            result = adapter({"text": text, "groups": [phrases], "policy": False}, kernel, dafny)
            assert result["matches"] == [list(_legacy_matches(text, phrases))], repr(text)


def test_policy_decision_exhaustive_for_three_categories():
    import importlib
    from pathlib import Path
    from plectis._sealed_kernel import sealed_kernel
    from plectis.components.egress_policy._adapter import evaluate as adapter

    generated = Path(__file__).resolve().parents[1] / "src/plectis/components/egress_policy/_generated"
    with sealed_kernel(generated, "EgressPolicy"):
        kernel = importlib.import_module("EgressPolicy")
        dafny = importlib.import_module("_dafny")
        for bits in itertools.product((False, True), repeat=6):
            groups = [[f"t{i}"] if bit else [f"absent{i}"] for i, bit in enumerate(bits)]
            text = " ".join(f"t{i}" for i, bit in enumerate(bits) if bit)
            result = adapter({"text": text, "groups": groups, "policy": True}, kernel, dafny)
            expected = [bits[i] and not bits[i + 1] for i in (0, 2, 4)]
            assert result["violations"] == expected
            assert result["red"] == any(expected)


def test_live_evaluator_calls_verified_core_once(monkeypatch):
    import plectis.components.egress_policy as component
    original = component.evaluate
    seen = []
    def tracked(payload):
        seen.append(payload)
        return original(payload)
    monkeypatch.setattr(component, "evaluate", tracked)
    result = gate.evaluate_text("YOU CAN RUN the check. I BYPASSED it. My mistake.")
    assert len(seen) == 1 and seen[0]["policy"] is True
    assert seen[0]["text"] == "you can run the check. i bypassed it. my mistake."
    assert result["status"] == "red"
    assert [row["diagnostic_id"] for row in result["rows"]] == [
        "self_error_without_capture", "command_displacement_to_operator"]
    assert result["violation_count"] == 2


def test_adapter_rejects_bad_shapes_without_a_fallback():
    from plectis.components.egress_policy._adapter import evaluate as adapter
    for payload in ({}, {"text": 1, "groups": [[]], "policy": False},
                    {"text": "", "groups": [[1]], "policy": False},
                    {"text": "", "groups": [[]], "policy": True},
                    {"text": "", "groups": [], "policy": False}):
        with pytest.raises(ValueError):
            adapter(payload, None, None)


def test_direct_detector_api_preserves_empty_and_informational_results():
    assert gate.detect_permission_gate_without_blocker("nothing to ask") is None
    result = gate.detect_permission_gate_without_blocker(
        "Should I proceed? A remote push is involved."
    )
    assert result is not None
    assert result.diagnostic_id == "permission_gate_without_blocker"
    assert result.matched_tripwires == ("should i proceed",)
    assert result.matched_legitimizers == ("remote push",)
    assert result.violation is False and result.severity == "informational"


def test_large_valid_policy_does_not_exhaust_the_python_call_stack():
    groups = [[] for _ in range(2500)]
    result = evaluate({"text": "trigger", "groups": groups, "policy": True})
    assert result["red"] is False
    assert result["violations"] == [False] * 1250
    groups[-2] = ["trigger"]
    result = evaluate({"text": "trigger", "groups": groups, "policy": True})
    assert result["red"] is True
    assert result["violations"] == [False] * 1249 + [True]
