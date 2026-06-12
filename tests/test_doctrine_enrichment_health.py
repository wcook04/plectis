"""Doctrine enrichment health covers reader cards plus routing floors."""
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


def _mechanism_record(code_path: str = "src/microcosm_core/organs/example.py") -> dict:
    return {
        "id": "mechanism.test.validates_example",
        "kind": "mechanism",
        "authority_boundary": "test_boundary",
        "source_refs": [{"path": "source", "role": "source"}],
        "validator_refs": ["validator"],
        "receipt_refs": ["receipt"],
        "anti_claims": ["not authority"],
        "entry_surface_contract": {"required": True},
        "organ_refs": ["example"],
        "code_loci": [
            {
                "path": code_path,
                "resolution": "resolved",
                "role": "Runtime authority.",
                "symbols": ["run"],
            }
        ],
        "mechanism_payload": {
            "contract_version": "test",
            "guardrails": ["guard"],
            "migration_contract": {"source_of_record": "source"},
            "projection_contract": {"markdown": "projection"},
            "resolution_evidence": {"code_loci": ["code"]},
            "support_contract": {"support": "none"},
        },
        "relationships": {
            "unpopulated_selective_relations": ["known_residual"],
            "edges": [
                {
                    "relation_id": "mechanism.grounds.concept",
                    "relation_verb": "grounds",
                    "reverse_verb": "grounded_by",
                    "target_id": "concept.test",
                    "target_kind": "concept",
                    "target_status": "resolved_json_instance",
                    "justification": {
                        "source_ref": "source::concept_refs",
                        "summary": "Source row names this concept.",
                    },
                }
            ],
        },
    }


def test_health_projection_counts_doctrine_routing_floor() -> None:
    report = HEALTH.build_health(MICRO_ROOT)
    routing = report["routing_floor"]
    concept = routing["kinds"]["concept"]
    mechanism = routing["kinds"]["mechanism"]

    assert report["reader_enrichment_total_objects"] == 49
    assert report["governed_floor_total_objects"] == 159
    assert routing["status"] == "complete"
    assert routing["covered_kinds"] == ["concept", "mechanism"]
    assert concept["total"] == 11
    assert concept["routed"] == 11
    assert concept["incomplete_ids"] == []
    assert concept["issue_rows"] == []
    assert mechanism["total"] == 99
    assert mechanism["routed"] == 99
    assert mechanism["incomplete_ids"] == []
    assert mechanism["issue_rows"] == []
    assert mechanism["known_residual_selective_relation_row_count"] == 37
    assert mechanism["known_residual_selective_relation_count"] == 37
    assert mechanism["planned_edge_row_count"] == 3
    assert mechanism["planned_edge_count"] == 3
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


def test_mechanism_routing_floor_requires_resolved_concept_route(tmp_path: Path) -> None:
    code_path = "src/microcosm_core/organs/example.py"
    (tmp_path / code_path).parent.mkdir(parents=True)
    (tmp_path / code_path).write_text("def run(): pass\n", encoding="utf-8")
    record = _mechanism_record(code_path)
    record["relationships"]["edges"] = []

    issues = HEALTH._audit_mechanism_routing_record(tmp_path, record)
    assert "edges_missing" in issues
    assert "resolved_concept_route_missing" in issues


def test_mechanism_routing_floor_requires_existing_code_locus(tmp_path: Path) -> None:
    record = _mechanism_record("src/microcosm_core/organs/missing.py")

    issues = HEALTH._audit_mechanism_routing_record(tmp_path, record)
    assert "code_locus_0_path_not_found" in issues
    assert "resolved_existing_code_locus_missing" in issues
