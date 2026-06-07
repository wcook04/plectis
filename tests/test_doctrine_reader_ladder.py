"""The doctrine reader-ladder gate is a permanent floor, not a one-off pass.

  1. Every object carries a sound reader ladder (plain + bounded analogy + maps
     + why_it_matters + common_misread, laundering-free).
  2. The gate is NOT vacuous: it catches a missing analogy boundary, a banned
     visible term, a proof claim in an affirmative lay field, and math leakage.
  3. The health projection consumes the gate and reflects it in `status`.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

MICRO_ROOT = Path(__file__).resolve().parents[1]
ENRICHMENT = MICRO_ROOT / "core" / "doctrine_enrichment.json"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, MICRO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GATE = _load("check_doctrine_reader_ladder", "scripts/check_doctrine_reader_ladder.py")


def _well_formed() -> dict:
    return {
        "id": "TEST",
        "kind": "axiom",
        "reader_ladder": {
            "plain": "A result counts only when its inputs and an independent check can reproduce it.",
            "analogy": {
                "text": "A library catalogue card is trusted only if the book is actually on the named shelf.",
                "maps": [{"doctrine": "the claim", "analogy": "the catalogue card"}],
                "boundary": "The catalogue picture shows lookup, it does not show that the book's contents are correct.",
            },
            "why_it_matters": "It keeps a label from standing in for the thing it points at.",
            "common_misread": "That a present card means a present book.",
        },
    }


def test_every_object_has_a_sound_reader_ladder() -> None:
    report = GATE.run(ENRICHMENT)
    assert report["total"] == 49, f"expected 49 objects, found {report['total']}"
    defects = [r for r in report["results"] if not r["clean"]]
    detail = "; ".join(f"{r['id']}: {r['issues']}" for r in defects)
    assert not defects, f"reader-ladder defects: {detail}"


def test_gate_passes_a_well_formed_ladder() -> None:
    assert GATE.audit_record(_well_formed())["clean"]


def test_gate_catches_missing_boundary() -> None:
    rec = _well_formed()
    rec["reader_ladder"]["analogy"]["boundary"] = ""
    assert not GATE.audit_record(rec)["clean"]


def test_gate_catches_boundary_without_a_limit() -> None:
    rec = _well_formed()
    rec["reader_ladder"]["analogy"]["boundary"] = "The catalogue resembles the claim closely."
    issues = GATE.audit_record(rec)["issues"]
    assert any("does not signal a limit" in i for i in issues)


def test_gate_catches_banned_visible_term() -> None:
    rec = _well_formed()
    rec["reader_ladder"]["plain"] = "A result record echoes the substrate organ."
    issues = GATE.audit_record(rec)["issues"]
    assert any("banned visible term" in i for i in issues)


def test_gate_catches_proof_claim_in_affirmative_field() -> None:
    rec = _well_formed()
    rec["reader_ladder"]["why_it_matters"] = "The analogy proves the system is correct."
    issues = GATE.audit_record(rec)["issues"]
    assert any("proof/guarantee claim" in i for i in issues)


def test_gate_catches_math_leak_in_lay_field() -> None:
    rec = _well_formed()
    rec["reader_ladder"]["plain"] = r"A claim is admissible iff \mathrm{adm}(\varphi) holds."
    issues = GATE.audit_record(rec)["issues"]
    assert any("math/LaTeX leaked" in i for i in issues)


def test_gate_requires_a_mapping() -> None:
    rec = _well_formed()
    rec["reader_ladder"]["analogy"]["maps"] = []
    issues = GATE.audit_record(rec)["issues"]
    assert any("maps empty" in i for i in issues)


def test_health_projection_reports_and_gates_on_reader_ladder() -> None:
    health = _load("build_doctrine_enrichment_health", "scripts/build_doctrine_enrichment_health.py")
    report = health.build_health(MICRO_ROOT)
    assert "reader_ladder" in report
    rl = report["reader_ladder"]
    assert rl["checked"] == 49
    assert rl["unsound"] == 0, f"health reports unsound reader ladders: {rl['defects']}"
    assert report["status"] == "complete"
