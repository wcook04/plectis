from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from microcosm_core.doctrine_lattice import (
    build_concept_instance_corpus,
    build_concept_instance_from_source_row,
)
from microcosm_core.schemas import DuplicateJsonKeyError
from microcosm_core.validators.concept_mechanism_population import (
    validate_concept_mechanism_population,
    validate_paths,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FAMILY_SPECIMEN_CONCEPTS = {
    "agent_reliability_and_safety_validator_bundle": "concept.agent_reliability_and_safety_validator_bundle",
    "architecture_and_navigation_route_contract_bundle": "concept.architecture_and_navigation_route_contract_bundle",
    "entry_and_reveal_route_readiness_bundle": "concept.entry_and_reveal_route_readiness_bundle",
    "formal_math_and_proof_witness_bundle": "concept.formal_math_and_proof_witness_bundle",
    "import_projection_and_drift_control_bundle": "concept.import_projection_and_drift_control_bundle",
    "research_and_science_replay_evidence_bundle": "concept.research_and_science_replay_evidence_bundle",
    "work_landing_and_continuity_control_bundle": "concept.work_landing_and_continuity_control_bundle",
}


def _load_entry_packet() -> dict:
    return json.loads((MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8"))


def _load_pressure() -> dict:
    return json.loads(
        (MICROCOSM_ROOT / "core/public_standard_pressure.json").read_text(encoding="utf-8")
    )


def _population_specimen_row(specimen_id: str) -> dict:
    route = _load_entry_packet()["concept_mechanism_entry_route"]
    for index, row in enumerate(route["population_specimens"]):
        if row["specimen_id"] != specimen_id:
            continue
        copied = copy.deepcopy(row)
        copied["id"] = f"concept.{specimen_id}"
        copied["source_ref"] = (
            "atlas/entry_packet.json::"
            f"concept_mechanism_entry_route.population_specimens[{index}:{specimen_id}]"
        )
        return copied
    raise AssertionError(f"missing concept population specimen: {specimen_id}")


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


def test_concept_mechanism_population_validator_checks_record_corpus() -> None:
    receipt = validate_paths(
        entry_packet_path=MICROCOSM_ROOT / "atlas/entry_packet.json",
        pressure_path=MICROCOSM_ROOT / "core/public_standard_pressure.json",
        out=None,
        root=MICROCOSM_ROOT,
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["record_validation"]["concept_count"] == 11
    assert receipt["record_validation"]["mechanism_count"] >= 99
    assert receipt["record_validation"]["cluster_flag_count"] == receipt["record_validation"][
        "concept_count"
    ]
    assert receipt["record_validation"]["draft_or_seed_status_count"] == 0


def test_concept_corpus_computes_source_named_selective_edges() -> None:
    corpus = build_concept_instance_corpus(MICROCOSM_ROOT)
    concepts = {
        concept_id: json.loads(
            (MICROCOSM_ROOT / "concepts" / f"{concept_id}.json").read_text(
                encoding="utf-8"
            )
        )
        for concept_id in corpus["instance_ids"]
    }

    assert corpus["unpopulated_selective_relation_count"] == 0
    first_screen = concepts["concept.first_screen_doctrine_effect_frame"]
    assert first_screen["relationships"]["mechanism_refs"] == [
        "mechanism.cold_reader_route_map.validates_public_first_run_route_map"
    ]
    assert first_screen["relationships"]["unpopulated_selective_relations"] == []

    resolved = concepts["concept.executable_doctrine_grammar_standard_bundle"]
    relationships = resolved["relationships"]
    assert relationships["principle_refs"] == ["P-8", "P-12", "P-15"]
    assert relationships["mechanism_refs"] == [
        "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle"
    ]
    assert relationships["axiom_refs"] == ["AX-7", "AX-11", "AX-12"]
    assert relationships["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_status"])
        for edge in relationships["edges"]
    } == {
        ("concept.implements_or_refines.principle", "resolved_json_instance"),
        ("concept.instantiated_by.mechanism", "resolved_json_instance"),
        ("concept.abides_by.axiom", "resolved_json_instance"),
    }


def test_family_population_specimens_bind_resolved_mechanisms() -> None:
    entry_packet = _load_entry_packet()
    route = entry_packet["concept_mechanism_entry_route"]
    specimens_by_id = {
        row["specimen_id"]: row
        for row in route["population_specimens"]
        if row["specimen_id"] in FAMILY_SPECIMEN_CONCEPTS
    }
    organ_atlas = json.loads(
        (MICROCOSM_ROOT / "core/organ_atlas.json").read_text(encoding="utf-8")
    )
    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    family_by_organ = {
        row["organ_id"]: row.get("family")
        for row in organ_atlas["organs"]
        if row.get("family")
    }
    mechanisms_by_family: dict[str, set[str]] = {}
    for row in mechanism_registry["mechanisms"]:
        for organ_id in row.get("runs_in") or []:
            family = family_by_organ.get(organ_id)
            if family:
                mechanisms_by_family.setdefault(family, set()).add(row["id"])

    assert set(specimens_by_id) == set(FAMILY_SPECIMEN_CONCEPTS)
    corpus = build_concept_instance_corpus(MICROCOSM_ROOT)
    for specimen_id, concept_id in FAMILY_SPECIMEN_CONCEPTS.items():
        specimen = specimens_by_id[specimen_id]
        source_family = specimen["entry_ref"].split("family=", 1)[1]
        direct_pairing_refs = set(specimen.get("mechanism_refs") or [])
        expected_concept_mechanisms = mechanisms_by_family[source_family] | direct_pairing_refs
        assert set(specimen["mechanism_ids"]) == mechanisms_by_family[source_family]
        assert specimen["concept_binding"]["anti_glossary_rule"].startswith(
            "Family concept population must remain source-bound"
        )
        assert "feature prose" in specimen["mechanism_binding"]["anti_feature_prose_rule"]
        concept = json.loads(
            (MICROCOSM_ROOT / "concepts" / f"{concept_id}.json").read_text(
                encoding="utf-8"
            )
        )
        assert concept_id in corpus["instance_ids"]
        assert concept["relationships"]["unpopulated_selective_relations"] == []
        assert set(concept["relationships"]["mechanism_refs"]) == expected_concept_mechanisms


def test_concept_corpus_does_not_launder_unresolved_named_targets() -> None:
    row = _population_specimen_row("executable_doctrine_grammar_standard_bundle")
    row["mechanism_ids"] = [
        "mechanism.fake_missing_runtime.validates_unresolved_target"
    ]

    instance = build_concept_instance_from_source_row(row, MICROCOSM_ROOT)
    mechanism_edges = [
        edge
        for edge in instance["relationships"]["edges"]
        if edge["relation_id"] == "concept.instantiated_by.mechanism"
    ]

    assert mechanism_edges == [
        {
            "justification": {
                "source_ref": (
                    "atlas/entry_packet.json::"
                    "concept_mechanism_entry_route.population_specimens"
                    "[1:executable_doctrine_grammar_standard_bundle].mechanism_ids"
                ),
                "summary": (
                    "Population specimen source row names this mechanism as "
                    "the concrete runtime instance for the concept."
                ),
            },
            "relation_id": "concept.instantiated_by.mechanism",
            "relation_verb": "instantiated_by",
            "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            "reverse_verb": "instantiates",
            "target_id": "mechanism.fake_missing_runtime.validates_unresolved_target",
            "target_kind": "mechanism",
            "target_status": "unresolved_json_instance",
        }
    ]
    assert instance["relationships"]["unpopulated_selective_relations"] == []
    assert instance["omission_receipt"]["residual_pressure"] == [
        {
            "gap_class": "concept_selective_edges_unpopulated_or_unresolved",
            "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            "reentry_condition": (
                "Bind concept implements/instantiated_by/abides_by edges "
                "from source evidence once target ids are named and resolve as generated instances."
            ),
        }
    ]


def test_concept_records_expose_cluster_flags_for_navigation() -> None:
    for path in sorted((MICROCOSM_ROOT / "concepts").glob("*.json")):
        concept = json.loads(path.read_text(encoding="utf-8"))
        relationships = concept["relationships"]
        flag = concept["cluster_flag"]

        assert flag["schema_version"] == "microcosm_concept_cluster_flag_v1"
        assert flag["kind"] == "concept"
        assert flag["concept_id"] == concept["id"]
        assert flag["cluster_id"] == relationships["specimen_id"]
        assert flag["source_ref"].startswith(
            "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
        )
        assert flag["mechanism_count"] == len(relationships["mechanism_refs"])
        assert flag["principle_count"] == len(relationships["principle_refs"])
        assert flag["axiom_count"] == len(relationships["axiom_refs"])
        assert flag["drilldown"] == f"concepts/{path.name}"
        assert "not_source_authority" in flag["authority_boundary"]


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


def test_concept_mechanism_population_validator_rejects_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    entry_packet_path = tmp_path / "entry_packet.json"
    entry_packet_path.write_text(
        (
            '{"concept_mechanism_entry_route": {"population_specimens": []}, '
            '"concept_mechanism_entry_route": {"activation_receipts": []}}'
        ),
        encoding="utf-8",
    )

    with pytest.raises(DuplicateJsonKeyError):
        validate_paths(
            entry_packet_path=entry_packet_path,
            pressure_path=None,
            out=None,
            command="pytest",
        )
