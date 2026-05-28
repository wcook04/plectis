from __future__ import annotations

import copy
import json
from pathlib import Path

from microcosm_core.projections.concept_mechanism_read_model import (
    DEFAULT_CONSUMER_ID,
    build_concept_mechanism_projection_read_model,
    compile_paths,
    validate_concept_mechanism_projection_read_model,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _load_entry_packet() -> dict:
    return json.loads((MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8"))


def _load_pressure() -> dict:
    return json.loads(
        (MICROCOSM_ROOT / "core/public_standard_pressure.json").read_text(encoding="utf-8")
    )


def _build_model() -> dict:
    return build_concept_mechanism_projection_read_model(
        entry_packet=_load_entry_packet(),
        pressure_payload=_load_pressure(),
        command="pytest",
    )


def test_projection_read_model_preserves_proof_critical_fields() -> None:
    payload = _build_model()

    assert payload["status"] == "pass"
    assert payload["consumer_id"] == DEFAULT_CONSUMER_ID
    assert payload["authority_posture"] == "derived_projection_not_source_authority"
    assert payload["route_consumer_declared"] is True
    assert payload["parallel_concept_index_authorized"] is False
    assert payload["workitem_completion_authority"] is False
    assert payload["source_validation"]["activation_receipt_count"] >= 1
    assert payload["pressure_checked"] is True
    assert payload["consumer_receipt"]["receipt_id"] == (
        "frontend_view_compiler_concept_mechanism_read_model_2026_05_27"
    )

    row = payload["rows"][0]
    for key in payload["field_preservation_contract"]["required_preserved_fields"]:
        assert row[key]
    assert row["source_route_ref"] == "atlas/entry_packet.json::concept_mechanism_entry_route"
    assert "population_specimens" in row["source_specimen_ref"]
    assert "activation_receipts" in row["source_activation_receipt_ref"]
    assert "parallel concept index" in row["authority_boundary"].replace("_", " ")
    assert "glossary" in row["concept_binding"]["anti_glossary_rule"]
    assert "feature prose" in row["mechanism_binding"]["anti_feature_prose_rule"]
    assert row["validator_refs"]
    assert row["receipt_refs"]
    assert any("projection_consumers" in ref for ref in row["receipt_refs"])


def test_projection_read_model_rejects_undeclared_route_consumer() -> None:
    entry_packet = _load_entry_packet()
    entry_packet["concept_mechanism_entry_route"]["projection_consumers"] = []

    payload = build_concept_mechanism_projection_read_model(
        entry_packet=entry_packet,
        pressure_payload=_load_pressure(),
        command="pytest",
    )

    assert payload["status"] == "blocked"
    assert "projection_consumer_not_declared_by_route" in {
        error["code"] for error in payload["errors"]
    }


def test_projection_read_model_rejects_dropped_proof_fields() -> None:
    payload = _build_model()
    bad_payload = copy.deepcopy(payload)
    del bad_payload["rows"][0]["validator_refs"]

    result = validate_concept_mechanism_projection_read_model(
        bad_payload,
        pressure_payload=_load_pressure(),
    )

    assert result["status"] == "blocked"
    assert "projection_row_missing_preserved_field" in {
        error["code"] for error in result["errors"]
    }


def test_projection_read_model_rejects_independent_concept_inventory() -> None:
    payload = _build_model()
    bad_payload = copy.deepcopy(payload)
    bad_payload["independent_concept_inventory"] = [{"term": "concept"}]

    result = validate_concept_mechanism_projection_read_model(
        bad_payload,
        pressure_payload=_load_pressure(),
    )

    assert result["status"] == "blocked"
    assert "parallel_concept_index_key_present" in {
        error["code"] for error in result["errors"]
    }


def test_projection_read_model_rejects_completed_product_claim() -> None:
    payload = _build_model()
    bad_payload = copy.deepcopy(payload)
    bad_payload["workitem_completion_authority"] = True
    bad_payload["rows"][0]["consumer_disposition"] = "completed_product_work"

    result = validate_concept_mechanism_projection_read_model(
        bad_payload,
        pressure_payload=_load_pressure(),
    )

    error_codes = {error["code"] for error in result["errors"]}
    assert result["status"] == "blocked"
    assert "projection_claims_product_completion" in error_codes
    assert "projection_row_claims_completed_product" in error_codes


def test_projection_read_model_cli_writes_model_and_receipt(tmp_path: Path) -> None:
    payload = compile_paths(
        entry_packet_path=MICROCOSM_ROOT / "atlas/entry_packet.json",
        pressure_path=MICROCOSM_ROOT / "core/public_standard_pressure.json",
        out=tmp_path,
        consumer_id=DEFAULT_CONSUMER_ID,
        command="pytest",
    )

    model_path = tmp_path / "concept_mechanism_projection_read_model.json"
    receipt_path = tmp_path / "concept_mechanism_projection_read_model_receipt.json"
    assert payload["status"] == "pass"
    assert model_path.exists()
    assert receipt_path.exists()
    assert json.loads(model_path.read_text(encoding="utf-8"))["status"] == "pass"
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["source_route_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route"
    )
