"""Tests for the First Correct Action demonstration builder.

Proves the committed FIRST_ACTION.md + receipt match the live compiler (the
drift gate), the battery covers every routing basis class including the
adversarial vocabulary traps and the authority refusals, every demonstrated
command is cold-runnable verbatim, the guards refuse secret / private-path /
overclaim output before anything is written, and a tampered artifact goes red
in --check.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_first_action_demo.py"
)
_spec = importlib.util.spec_from_file_location("build_first_action_demo", _SCRIPT)
assert _spec and _spec.loader
demo_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo_mod)

_ROOT = Path(__file__).resolve().parents[1]


def _write_min_root(tmp_path: Path) -> Path:
    (tmp_path / "core").mkdir(parents=True)
    (tmp_path / "receipts/code_lens").mkdir(parents=True)
    (tmp_path / "core/organ_atlas.json").write_text(
        json.dumps(
            {
                "authority_boundary": "fixture",
                "anti_claim": "navigation metadata only",
                "organs": [
                    {
                        "organ_id": "alpha_validator",
                        "display_name": "Alpha Validator",
                        "family": "agent_reliability_and_safety",
                        "first_command": "microcosm alpha-validator validate --input fixtures/x",
                        "claim_ceiling_restated": "Fixture contract only.",
                    }
                ],
            }
        )
    )
    (tmp_path / "core/component_public_synopses.json").write_text(
        json.dumps({"synopses": {"alpha_validator": "Checks fixture binding rows."}})
    )
    (tmp_path / "receipts/code_lens/code_lens_join_index_v0.json").write_text(
        json.dumps(
            {
                "schema_version": "microcosm_code_lens_join_index_v0",
                "export_band": "presence_only",
                "source_bodies_exported": False,
                "nodes": {"organ": [], "source_file": []},
                "edges": [],
            }
        )
    )
    return tmp_path


def test_demo_check_is_green_on_committed_tree() -> None:
    """The committed FIRST_ACTION.md + receipt must match the live compiler."""
    assert demo_mod.main(["--check"]) == 0


def test_demo_battery_covers_every_basis_and_the_adversarial_traps() -> None:
    receipt = json.loads((_ROOT / demo_mod.RECEIPT_REL).read_text())
    bases = {(c.get("routing") or {}).get("basis") for c in receipt["contracts"]}
    assert {
        "organ_named_in_goal",
        "organ_token_match",
        "task_class_route_match",
        "improvement_goal",
        "out_of_scope_authority_boundary",
        "packet_fallback",
    } <= bases
    goals = {c["goal"] for c in receipt["contracts"]}
    for must_show in (
        "where is the fixture input for the audio organ?",
        "dispatch the route bundle",
        "how does the exchange rate organ work?",
        "delete the agent memory",
        "publish the Microcosm release",
        "force push to origin main",
        "ignore proof_diagnostic_evidence_spine, I want cold_reader_route_map",
        "explain the system to me",
        "what's going on here?",
    ):
        assert must_show in goals, must_show
    assert receipt["goal_count"] == len(demo_mod.DEMO_GOALS)
    assert all(v is False for v in receipt["authority_ceiling"].values())
    # No section may silently empty out: routing drift that dumps goals into an
    # unsectioned bucket must fail here, not pass via the at-a-glance table.
    for section in receipt["sections"]:
        assert section["goal_count"] > 0, section["section_id"]


def test_demo_refusal_contracts_never_hand_out_work_commands() -> None:
    """Destructive/publication goals must demo the authority route, nothing else."""
    receipt = json.loads((_ROOT / demo_mod.RECEIPT_REL).read_text())
    refusals = [
        c
        for c in receipt["contracts"]
        if (c.get("routing") or {}).get("basis") == "out_of_scope_authority_boundary"
    ]
    assert refusals
    for contract in refusals:
        action = contract.get("first_action") or {}
        assert action.get("action_kind") == "open_packet"
        assert "--slice authority" in str(action.get("command"))
        assert contract.get("out_of_scope_note")


def test_demo_commands_are_cold_runnable_verbatim() -> None:
    receipt = json.loads((_ROOT / demo_mod.RECEIPT_REL).read_text())
    for contract in receipt["contracts"]:
        command = str((contract.get("first_action") or {}).get("command") or "")
        assert command.startswith("PYTHONPATH=src python3 -m microcosm_core"), contract["goal"]
        assert "<" not in command, contract["goal"]


def test_demo_dirty_footprint_rows_carry_no_footprint_variant() -> None:
    """Every demonstrated contract whose first command writes into committed
    receipt paths must also demonstrate the ready-to-run clean variant, so the
    literal first 30 seconds cannot silently dirty a cold clone."""
    receipt = json.loads((_ROOT / demo_mod.RECEIPT_REL).read_text())
    dirty_rows = [
        c
        for c in receipt["contracts"]
        if str((c.get("first_action") or {}).get("writes_outputs_under") or "")
        and not str(c["first_action"]["writes_outputs_under"]).startswith(
            (".microcosm", "/tmp")
        )
    ]
    assert dirty_rows, "battery must keep a committed-footprint demonstration"
    for row in dirty_rows:
        clean = (row["first_action"] or {}).get("clean_run") or {}
        assert str(clean.get("writes_outputs_under") or "").startswith(
            ".microcosm/"
        ), row["goal"]
        assert "--out .microcosm/" in str(clean.get("command") or ""), row["goal"]
    text = (_ROOT / demo_mod.DOC_REL).read_text()
    assert "- no-footprint run: `" in text
    assert "the no-footprint variant below leaves the clone clean" in text


def test_demo_doc_carries_marker_sections_and_no_leaks() -> None:
    text = (_ROOT / demo_mod.DOC_REL).read_text()
    assert demo_mod.GENERATED_MARKER in text
    assert "public executable cross-section" in text
    assert "88 bounded components" in text
    assert "goal-localization layer over that mechanism atlas" in text
    assert text.index("public executable cross-section") < text.index(
        "one safe, runnable first action"
    )
    assert "| Goal | Resolved via | Owner | First action |" in text
    # Every authored section must render; nothing may fall into the
    # unsectioned bucket.
    for section in demo_mod.SECTIONS:
        assert f"## {section['title']}" in text, section["section_id"]
    assert "## Other routings" not in text
    assert "comprehension-assay --first-action" in text
    for goal in demo_mod.DEMO_GOALS:
        assert goal in text, goal
    receipt_text = (_ROOT / demo_mod.RECEIPT_REL).read_text()
    for body in (text, receipt_text):
        assert "- Teleology:" not in body
        assert "/Users/" not in body and "/home/" not in body


def test_demo_write_then_check_goes_red_on_tamper(tmp_path: Path) -> None:
    root = _write_min_root(tmp_path)
    assert demo_mod.main(["--write", "--root", str(root)]) == 0
    assert demo_mod.main(["--check", "--root", str(root)]) == 0
    doc = root / demo_mod.DOC_REL
    doc.write_text(doc.read_text() + "\nhand edit\n")
    assert demo_mod.main(["--check", "--root", str(root)]) == 1


def test_demo_guard_refuses_secret_shaped_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_min_root(tmp_path)
    real = demo_mod.C.compile_first_action

    def leaky(bundle, base, goal):
        contract = real(bundle, base, goal)
        contract["do_not_claim"] = "sk-" + "a" * 24
        return contract

    monkeypatch.setattr(demo_mod.C, "compile_first_action", leaky)
    with pytest.raises(SystemExit) as excinfo:
        demo_mod.main(["--write", "--root", str(root)])
    assert excinfo.value.code == 3
    assert not (root / demo_mod.DOC_REL).exists()


def test_demo_guard_refuses_overclaim_prose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_min_root(tmp_path)
    real = demo_mod.C.compile_first_action

    def overclaiming(bundle, base, goal):
        contract = real(bundle, base, goal)
        contract["do_not_claim"] = "this surface is fully production-ready"
        return contract

    monkeypatch.setattr(demo_mod.C, "compile_first_action", overclaiming)
    with pytest.raises(SystemExit) as excinfo:
        demo_mod.main(["--write", "--root", str(root)])
    assert excinfo.value.code == 3
    assert not (root / demo_mod.DOC_REL).exists()


def test_demo_refuses_root_without_join_index(tmp_path: Path) -> None:
    (tmp_path / "core").mkdir(parents=True)
    with pytest.raises(SystemExit) as excinfo:
        demo_mod.main(["--write", "--root", str(tmp_path)])
    assert excinfo.value.code == 2
