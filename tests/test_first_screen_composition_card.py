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
    assert card["human_first_command"] == "microcosm hello <project>"
    assert card["shared_first_command"] == "microcosm tour --card <project>"
    text_projection = card["text_projection"]
    assert text_projection == {
        "command": card["human_first_command"],
        "writes_microcosm_state": False,
        "behavioral_proof_command": card["shared_first_command"],
        "authority": "terminal_text_projection_only_not_behavior_proof",
        "reader_rule": (
            "Use this command to view the first-screen card; run the "
            "behavior proof command to write .microcosm state."
        ),
    }
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
    assert "observatory landing frame" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    scale_counts = card["scale_frame"]["public_scale_counts"]
    assert card["scale_frame"]["count_interpretation"] == (
        "receipt_backed_handles_not_scores"
    )
    assert scale_counts["implemented_organs"]["source_ref"] == "core/organ_registry.json"
    assert scale_counts["implemented_organs"]["count"] > 0
    assert scale_counts["public_standards"]["source_ref"] == (
        "core/standards_registry.json"
    )
    assert scale_counts["public_standards"]["count"] > 0
    assert scale_counts["source_open_materials"]["source_ref"] == (
        "receipts/runtime_shell/workingness_failure_map.json"
    )
    assert scale_counts["source_open_materials"]["count"] > 0
    assert scale_counts["source_open_materials"]["read_as"] == (
        "copy_boundary_accounting_not_maturity_score"
    )
    observatory_landing_frame = card["observatory_landing_frame"]
    assert observatory_landing_frame["schema_version"] == (
        "microcosm_observatory_landing_frame_v1"
    )
    assert observatory_landing_frame["role"] == (
        "make_the_hello_first_screen_card_the_browser_landing_frame"
    )
    assert observatory_landing_frame["human_first_command"] == (
        card["human_first_command"]
    )
    assert observatory_landing_frame["text_projection_command"] == (
        card["human_first_command"]
    )
    assert observatory_landing_frame["shared_first_command"] == (
        card["shared_first_command"]
    )
    assert observatory_landing_frame["behavioral_proof_command"] == (
        card["shared_first_command"]
    )
    assert observatory_landing_frame["browser_landing_reuse"] == {
        "source_projection": (
            "microcosm_core.first_screen_composition.first_screen_text_card"
        ),
        "default_endpoint": "/",
        "card_endpoint": "/project/first-screen",
        "authority": "browser_projection_over_same_card_not_json_first_lens_inventory",
    }
    assert observatory_landing_frame["endpoints"] == {
        "html_landing": "/",
        "first_screen_card": "/project/first-screen",
        "compact_observatory_card": "/project/observatory-card",
        "full_observatory_model": "/project/observatory",
        "project_observe": "/project/observe",
    }
    assert observatory_landing_frame["drilldown_order"] == [
        "html_landing",
        "first_screen_card",
        "compact_observatory_card",
        "full_observatory_model",
        "project_observe",
    ]
    assert "human_first_command" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "text_projection" in observatory_landing_frame["required_visible_handles"]
    assert "behavioral_proof_command" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "public_scale_counts" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "release, hosting, provider calls" in observatory_landing_frame[
        "authority_boundary"
    ]
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
    assert card["validation"]["checks"]["human_first_command"] is True
    assert card["validation"]["checks"]["text_projection"] is True
    assert card["validation"]["checks"]["scale_frame"] is True
    assert card["validation"]["checks"]["observatory_landing_frame"] is True
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
    assert card["human_first_command"] == "microcosm hello ."
    assert card["shared_first_command"] == "microcosm tour --card ."
    assert card["text_projection"]["command"] == "microcosm hello ."
    assert card["text_projection"]["behavioral_proof_command"] == (
        "microcosm tour --card ."
    )
    assert card["text_projection"]["writes_microcosm_state"] is False
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
    assert "Open card: microcosm hello ." in text
    assert "First run: microcosm tour --card ." in text
    assert "A local evidence router, not a maturity brochure" in text
    assert "Public scale:" in text
    assert "source-open materials" in text
    assert "Counts are receipt-backed handles" in text
    assert (
        "Safety/evals: microcosm status --card . -> microcosm authority -> "
        "microcosm workingness"
    ) in text
    assert "Hiring: microcosm legibility-scorecard -> microcosm tour --card ." in text
    assert "Peer developer: microcosm tour --card . -> microcosm observe ." in text
    assert (
        "browser landing: / -> /project/first-screen -> /project/observatory-card"
        in text
    )
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
        assert "Open card: microcosm hello ." in text
        assert "First run: microcosm tour --card ." in text
        assert f"Reader branch: {assertions['label']}" in text
        assert "  Question: " in text
        assert f"  Next: {assertions['next']}" in text
        assert "  Focus:\n" in text
        assert "Authority ceiling:" in text
        assert "Counts are receipt-backed handles" in text
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
    assert "Open card: microcosm hello ." in result.stdout
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
    assert "Open card: microcosm hello ." in result.stdout
    assert "First run: microcosm tour --card ." in result.stdout
    assert "Reader branch: Safety/evals" in result.stdout
    assert "  Next: microcosm status --card . -> microcosm authority -> microcosm workingness" in result.stdout
    assert "Reader branches:" not in result.stdout
    assert "Reader branch: Hiring" not in result.stdout
    assert "reader_routes" not in result.stdout
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout
