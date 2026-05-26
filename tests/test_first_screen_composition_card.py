from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = MICROCOSM_ROOT / "scripts/first_screen_composition_card.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("first_screen_composition_card", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def test_first_screen_composition_card_is_public_one_screen_contract() -> None:
    module = _load_module()

    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label="<project>")
    route_ids = {route["reader_route_id"] for route in card["reader_routes"]}

    assert card["status"] == "pass"
    assert card["composition_root_id"] == "first_screen_composition_root"
    assert (
        card["source_standard_ref"]
        == "standards/std_microcosm_first_screen_composition_root.json"
    )
    assert card["shared_first_command"] == "microcosm tour --card <project>"
    assert route_ids == {
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    }
    assert card["evidence_count_frame"]["interpretation"] == "accounting_not_maturity_score"
    assert "maturity_score" in card["evidence_count_frame"]["forbidden_reads"]
    assert card["comparison_frame"]["purpose"] == (
        "make_rigor_visible_without_claim_inflation"
    )
    assert "one shared local behavior command before reader branching" in card[
        "comparison_frame"
    ]["microcosm_entry_discipline"]
    assert card["entry_surface_contract"]["shared_behavior_surface"] == (
        card["shared_first_command"]
    )
    assert card["entry_surface_contract"]["package_surface"] == (
        "microcosm_core.first_screen_composition.first_screen_composition_card"
    )
    assert "README, CLI, and observatory consumers" in card[
        "entry_surface_contract"
    ]["consumer_rule"]
    assert card["authority_ceiling"]["release_authority"] is False
    assert card["authority_ceiling"]["source_mutation_authority"] is False
    assert card["authority_ceiling"]["private_data_equivalence_authority"] is False
    assert card["authority_ceiling"]["provider_call_authority"] is False
    assert card["authority_ceiling"]["score_based_progress_authority"] is False
    assert card["authority_ceiling"]["whole_system_correctness_authority"] is False
    assert card["omission_receipt"]["drilldown"] == "paper_modules/first_screen_composition_root.md"
    assert any(
        drilldown.get("command") == "microcosm workingness"
        for drilldown in card["drilldowns"]
    )
    assert card["validation"]["checks"]["workingness_drilldown"] is True
    assert card["validation"]["checks"]["comparison_frame"] is True
    assert card["validation"]["checks"]["entry_surface_contract"] is True
    assert "body" not in _walk_keys(card)
    assert (
        module.first_screen_composition_card.__module__
        == "microcosm_core.first_screen_composition"
    )


def test_first_screen_composition_card_cli_emits_ascii_public_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/first_screen_composition_card.py",
            "--project-label",
            ".",
        ],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    result.stdout.encode("ascii")
    card = json.loads(result.stdout)

    assert card["status"] == "pass"
    assert card["shared_first_command"] == "microcosm tour --card ."
    assert card["entry_surface_contract"]["script_surface"] == (
        "python3 scripts/first_screen_composition_card.py --project-label ."
    )
    assert {route["reader_route_id"] for route in card["reader_routes"]} == {
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    }
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout
    assert '"body":' not in result.stdout


def test_first_screen_text_card_is_terminal_sized_and_honest() -> None:
    module = _load_module()
    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")

    text = module.first_screen_text_card(card)

    text.encode("ascii")
    assert text.startswith("Microcosm first screen\n")
    assert "First run: microcosm tour --card ." in text
    assert "A local evidence router, not a maturity brochure" in text
    assert "Evidence counts are accounting fields" in text
    assert (
        "Safety/evals: microcosm status --card . -> microcosm authority -> "
        "microcosm workingness"
    ) in text
    assert "Hiring: microcosm legibility-scorecard -> microcosm tour --card ." in text
    assert "Peer developer: microcosm tour --card . -> microcosm observe ." in text
    assert "No release, hosted publication, provider-call" in text
    assert "paper_modules/first_screen_composition_root.md" in text
    assert len(text.splitlines()) <= module.TEXT_CARD_MAX_LINES
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert '"body":' not in text


def test_first_screen_text_card_can_focus_each_reader_branch() -> None:
    module = _load_module()
    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")
    expected = {
        "safety_evals_engineer": {
            "label": "Safety/evals",
            "next": "microcosm status --card . -> microcosm authority -> microcosm workingness",
            "absent": ["Reader branch: Hiring", "Reader branch: Peer developer"],
        },
        "hiring_reviewer": {
            "label": "Hiring",
            "next": "microcosm legibility-scorecard -> microcosm tour --card .",
            "absent": ["Reader branch: Safety/evals", "Reader branch: Peer developer"],
        },
        "peer_developer": {
            "label": "Peer developer",
            "next": "microcosm tour --card . -> microcosm observe .",
            "absent": ["Reader branch: Safety/evals", "Reader branch: Hiring"],
        },
    }

    for reader_id, assertions in expected.items():
        text = module.first_screen_text_card(card, reader_id=reader_id)

        text.encode("ascii")
        assert text.startswith("Microcosm first screen\n")
        assert "First run: microcosm tour --card ." in text
        assert f"Reader branch: {assertions['label']}" in text
        assert "  Question: " in text
        assert f"  Next: {assertions['next']}" in text
        assert "  Focus:\n" in text
        assert "Authority ceiling:" in text
        assert "Evidence counts are accounting fields" in text
        assert len(text.splitlines()) <= module.TEXT_CARD_MAX_LINES
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        for absent in assertions["absent"]:
            assert absent not in text


def test_first_screen_composition_card_cli_emits_text_projection() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/first_screen_composition_card.py",
            "--project-label",
            ".",
            "--format",
            "text",
        ],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    result.stdout.encode("ascii")
    assert result.stdout.startswith("Microcosm first screen\n")
    assert "First run: microcosm tour --card ." in result.stdout
    assert "reader_routes" not in result.stdout
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout


def test_first_screen_composition_card_cli_can_focus_text_projection() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/first_screen_composition_card.py",
            "--project-label",
            ".",
            "--format",
            "text",
            "--reader",
            "safety_evals_engineer",
        ],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    result.stdout.encode("ascii")
    assert result.stdout.startswith("Microcosm first screen\n")
    assert "First run: microcosm tour --card ." in result.stdout
    assert "Reader branch: Safety/evals" in result.stdout
    assert "  Next: microcosm status --card . -> microcosm authority -> microcosm workingness" in result.stdout
    assert "Reader branches:" not in result.stdout
    assert "Reader branch: Hiring" not in result.stdout
    assert "reader_routes" not in result.stdout
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout
