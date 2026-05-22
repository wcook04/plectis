from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core import release_activation_rehearsal
from microcosm_core import release_impressiveness_compiler


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _copy_activation_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    for dirname in ("core", "examples", "fixtures", "paper_modules", "receipts", "standards"):
        shutil.copytree(MICROCOSM_ROOT / dirname, public_root / dirname)
    shutil.copy2(MICROCOSM_ROOT / "pyproject.toml", public_root / "pyproject.toml")
    return public_root


def test_release_activation_rehearsal_builds_cold_reader_cards() -> None:
    receipt = release_activation_rehearsal.build_rehearsal(MICROCOSM_ROOT)

    assert receipt["schema_version"] == "microcosm_release_activation_rehearsal_receipt_v1"
    assert receipt["status"] == "pass"
    assert receipt["cold_reader_loop_status"] == "pass"
    assert receipt["activation_card_count"] == 6
    assert receipt["selected_pattern_count"] == 23
    assert receipt["blocking_codes"] == []
    assert receipt["authority_ceiling"]["release_authorized"] is False
    assert receipt["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert receipt["showcase_mode"]["command"] == "microcosm release-activation --root ."
    assert receipt["falsification_mode"]["expected_blocker"] == (
        "CAPABILITY_ACTIVATION_ACTION_MISSING"
    )

    cards = {card["lane_id"]: card for card in receipt["activation_cards"]}
    assert set(cards) == {
        "proof_formal_kernel",
        "prover_evaluator_lab",
        "work_landing_governance",
        "navigation_option_surface",
        "pattern_doctrine_compiler",
        "observatory_provenance_diagnostics",
    }
    assert cards["proof_formal_kernel"]["command_or_view_ref"] == "microcosm trace-lens"
    assert cards["prover_evaluator_lab"]["command_or_view_ref"] == "microcosm benchmark-lab"
    assert cards["work_landing_governance"]["command_or_view_ref"] == "microcosm landing-replay"
    assert cards["observatory_provenance_diagnostics"]["command_or_view_ref"] == "microcosm reveal"
    for card in cards.values():
        assert card["activation_status"] == "pass"
        assert card["activation_maturity"]["level"] >= 4
        assert card["expected_output_probe"]["expected_status"] == "pass"
        assert card["claim_card_refs"]
        assert card["receipt_ref"]
        assert card["provenance_ref"]
        assert card["standalone_severance_status"] == "pass"
        assert card["private_runtime_dependency_status"] == "pass"


def test_release_activation_rehearsal_runs_from_copied_root(tmp_path: Path) -> None:
    public_root = _copy_activation_root(tmp_path)

    receipt = release_activation_rehearsal.build_rehearsal(public_root)

    assert receipt["status"] == "pass"
    assert receipt["activation_card_count"] == 6
    assert receipt["activation_maturity_counts"]["M5 cold-reader loop"] == 6
    encoded = json.dumps(receipt, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_release_activation_rehearsal_demotes_hollow_action(tmp_path: Path) -> None:
    public_root = _copy_activation_root(tmp_path)
    tranche_path = public_root / release_impressiveness_compiler.FLAGSHIP_TRANCHE_REL
    payload = json.loads(tranche_path.read_text(encoding="utf-8"))
    payload["lanes"][0]["runtime_surface_refs"] = []
    tranche_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    receipt = release_activation_rehearsal.build_rehearsal(public_root)

    assert receipt["status"] == "blocked"
    assert "CAPABILITY_ACTIVATION_ACTION_MISSING" in receipt["blocking_codes"]
    assert "CAPABILITY_TRANSFER_RUNTIME_SURFACE_MISSING" in receipt["blocking_codes"]
    first_card = receipt["activation_cards"][0]
    assert first_card["activation_status"] == "blocked"
    assert first_card["fallback_if_blocked"].startswith("Demote")
