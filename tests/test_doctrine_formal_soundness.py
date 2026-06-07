"""The doctrine formal-soundness gate is a permanent floor, not a one-off pass.

These tests assert three things:
  1. Every formal statement in the live enrichment is symbol-sound (every
     symbol used is defined, every symbol defined is used).
  2. The gate is NOT vacuous: it catches a planted dangling symbol and a
     planted undefined operator. A green gate that cannot go red proves nothing.
  3. The health projection consumes the gate and reflects it in `status`.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MICRO_ROOT = Path(__file__).resolve().parents[1]
ENRICHMENT = MICRO_ROOT / "core" / "doctrine_enrichment.json"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, MICRO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SOUND = _load("check_doctrine_formal_soundness", "scripts/check_doctrine_formal_soundness.py")


def test_every_formal_statement_is_symbol_sound() -> None:
    report = SOUND.run(ENRICHMENT)
    assert report["total"] == 49, f"expected 49 formal statements, found {report['total']}"
    defects = [r for r in report["results"] if not r["clean"]]
    detail = "; ".join(
        f"{r['id']}: dangling={r['dangling']} vars={r['undefined_vars']} ops={r['undefined_ops']}"
        for r in defects
    )
    assert not defects, f"unsound formal statements: {detail}"


def test_gate_catches_dangling_symbol() -> None:
    rec = {
        "id": "TEST",
        "kind": "axiom",
        "formal": {
            "latex": r"\mathrm{f}(x) = y",
            "symbols": [
                {"sym": "\\mathrm{f}", "meaning": "a function"},
                {"sym": "x", "meaning": "input"},
                {"sym": "y", "meaning": "output"},
                {"sym": "\\mathrm{ghost}(z)", "meaning": "never appears in the formula"},
            ],
        },
    }
    audit = SOUND.audit_record(rec)
    assert audit["dangling"] == ["\\mathrm{ghost}(z)"]
    assert not audit["clean"]


def test_gate_catches_undefined_operator_and_variable() -> None:
    rec = {
        "id": "TEST",
        "kind": "axiom",
        "formal": {
            "latex": r"\mathrm{auth}(u) \iff F(\mathrm{policy})",
            "symbols": [{"sym": "u", "meaning": "subject"}],
        },
    }
    audit = SOUND.audit_record(rec)
    assert "F" in audit["undefined_vars"]
    assert "\\mathrm{auth}" in audit["undefined_ops"]
    assert "\\mathrm{policy}" in audit["undefined_ops"]
    assert not audit["clean"]


def test_gate_passes_a_well_formed_record() -> None:
    rec = {
        "id": "TEST",
        "kind": "axiom",
        "formal": {
            "latex": r"\mathrm{adm}(\varphi) \iff \exists\, K.\ K(\varphi) = \mathsf{accept}",
            "symbols": [
                {"sym": "\\mathrm{adm}(\\varphi)", "meaning": "admissible"},
                {"sym": "\\varphi", "meaning": "a claim"},
                {"sym": "K", "meaning": "a checker"},
            ],
        },
    }
    audit = SOUND.audit_record(rec)
    assert audit["clean"], audit


def test_health_projection_reports_and_gates_on_soundness() -> None:
    health = _load("build_doctrine_enrichment_health", "scripts/build_doctrine_enrichment_health.py")
    report = health.build_health(MICRO_ROOT)
    assert "formal_soundness" in report
    fs = report["formal_soundness"]
    assert fs["checked"] == 49
    assert fs["unsound"] == 0, f"health reports unsound formal statements: {fs['defects']}"
    # status is complete only when coverage AND soundness hold.
    assert report["status"] == "complete"
    assert report["coverage_complete"] is True
