from __future__ import annotations

import copy
import json
from pathlib import Path

from microcosm_core.validators.concept_mechanism_population import (
    validate_concept_mechanism_population,
    validate_paths,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _load_entry_packet() -> dict:
    return json.loads((MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8"))


def _load_pressure() -> dict:
    return json.loads(
        (MICROCOSM_ROOT / "core/public_standard_pressure.json").read_text(encoding="utf-8")
    )


def test_concept_mechanism_population_validator_accepts_live_route() -> None:
    receipt = validate_concept_mechanism_population(
        entry_packet=_load_entry_packet(),
        pressure_payload=_load_pressure(),
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["specimen_count"] >= 4
    assert receipt["activation_receipt_count"] >= 1
    assert "concept_index_frontend_view_compiler_projection_guard_2026_05_27" in receipt[
        "activation_receipt_ids"
    ]
    assert receipt["parallel_index_authorized"] is False
    assert receipt["errors"] == []


def test_concept_mechanism_population_validator_rejects_parallel_index_receipt() -> None:
    entry_packet = _load_entry_packet()
    bad_packet = copy.deepcopy(entry_packet)
    receipt = bad_packet["concept_mechanism_entry_route"]["activation_receipts"][0]
    receipt["residual_disposition"] = "parallel_concept_index_allowed"
    receipt["authority_boundary"] = "frontend_registry_authority"

    result = validate_concept_mechanism_population(
        entry_packet=bad_packet,
        pressure_payload=_load_pressure(),
        command="pytest",
    )

    assert result["status"] == "blocked"
    error_codes = {error["code"] for error in result["errors"]}
    assert "activation_receipt_bad_disposition" in error_codes
    assert "concept_index_pressure_boundary_missing" in error_codes


def test_concept_mechanism_population_validator_rejects_glossary_only_activation() -> None:
    entry_packet = _load_entry_packet()
    bad_packet = copy.deepcopy(entry_packet)
    receipt = bad_packet["concept_mechanism_entry_route"]["activation_receipts"][0]
    receipt["concept_binding"]["anti_glossary_rule"] = "terms can be browsed"
    receipt["mechanism_binding"]["anti_feature_prose_rule"] = "planned frontend surface"

    result = validate_concept_mechanism_population(
        entry_packet=bad_packet,
        pressure_payload=_load_pressure(),
        command="pytest",
    )

    assert result["status"] == "blocked"
    error_codes = {error["code"] for error in result["errors"]}
    assert "concept_binding_not_anti_glossary" in error_codes
    assert "mechanism_binding_not_anti_feature_prose" in error_codes


def test_concept_mechanism_population_validator_writes_receipt(tmp_path: Path) -> None:
    receipt = validate_paths(
        entry_packet_path=MICROCOSM_ROOT / "atlas/entry_packet.json",
        pressure_path=MICROCOSM_ROOT / "core/public_standard_pressure.json",
        out=tmp_path,
        command="pytest",
    )
    receipt_path = tmp_path / "concept_mechanism_population_validation.json"

    assert receipt["status"] == "pass"
    assert receipt_path.exists()
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["status"] == "pass"
