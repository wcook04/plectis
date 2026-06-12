"""Doctrine enrichment health covers reader cards plus concept routing."""
from __future__ import annotations

import importlib.util
from pathlib import Path

MICRO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, MICRO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


HEALTH = _load(
    "build_doctrine_enrichment_health",
    "scripts/build_doctrine_enrichment_health.py",
)


def test_health_projection_counts_concept_routing_floor() -> None:
    report = HEALTH.build_health(MICRO_ROOT)
    routing = report["routing_floor"]
    concept = routing["kinds"]["concept"]

    assert report["reader_enrichment_total_objects"] == 49
    assert report["governed_floor_total_objects"] == 60
    assert routing["status"] == "complete"
    assert routing["covered_kinds"] == ["concept"]
    assert concept["total"] == 11
    assert concept["routed"] == 11
    assert concept["incomplete_ids"] == []
    assert concept["issue_rows"] == []
    assert report["status"] == "complete"


def test_concept_routing_floor_requires_resolved_mechanism_route() -> None:
    record = {
        "id": "concept.test",
        "kind": "concept",
        "authority_boundary": "test_boundary",
        "source_refs": [{"path": "source", "role": "source"}],
        "validator_refs": ["validator"],
        "receipt_refs": ["receipt"],
        "anti_claims": ["not authority"],
        "entry_surface_contract": {"required": True},
        "cluster_flag": {"concept_id": "concept.test"},
        "relationships": {
            "unpopulated_selective_relations": [],
            "edges": [
                {
                    "relation_id": "concept.implements_or_refines.principle",
                    "relation_verb": "implements_or_refines",
                    "reverse_verb": "refined_by",
                    "target_id": "P-1",
                    "target_kind": "principle",
                    "target_status": "resolved_json_instance",
                    "justification": {
                        "source_ref": "source::principle_ids",
                        "summary": "Source row names this principle.",
                    },
                }
            ],
        },
    }

    issues = HEALTH._audit_concept_routing_record(record)
    assert "resolved_mechanism_route_missing" in issues


def test_concept_routing_floor_rejects_unresolved_edges() -> None:
    record = {
        "id": "concept.test",
        "kind": "concept",
        "authority_boundary": "test_boundary",
        "source_refs": [{"path": "source", "role": "source"}],
        "validator_refs": ["validator"],
        "receipt_refs": ["receipt"],
        "anti_claims": ["not authority"],
        "entry_surface_contract": {"required": True},
        "cluster_flag": {"concept_id": "concept.test"},
        "relationships": {
            "unpopulated_selective_relations": [],
            "edges": [
                {
                    "relation_id": "concept.instantiated_by.mechanism",
                    "relation_verb": "instantiated_by",
                    "reverse_verb": "instantiates",
                    "target_id": "mechanism.test",
                    "target_kind": "mechanism",
                    "target_status": "residual_pressure",
                    "justification": {
                        "source_ref": "source::mechanism_ids",
                        "summary": "Source row names this mechanism.",
                    },
                }
            ],
        },
    }

    issues = HEALTH._audit_concept_routing_record(record)
    assert "edge_0_target_unresolved" in issues
    assert "resolved_mechanism_route_missing" in issues


def test_concept_routing_floor_counts_malformed_json_as_incomplete(tmp_path: Path) -> None:
    concepts_dir = tmp_path / "concepts"
    concepts_dir.mkdir()
    (concepts_dir / "concept.bad.json").write_text("{", encoding="utf-8")

    routing = HEALTH._build_routing_floor(tmp_path)
    issue_row = routing["incomplete"][0]

    assert routing["total_objects"] == 1
    assert routing["routed_objects"] == 0
    assert routing["status"] == "partial"
    assert issue_row["id"] == "concept.invalid_json.concept.bad.json"
    assert len(issue_row["issues"]) == 1
    assert issue_row["issues"][0].startswith("json_decode_error:")
