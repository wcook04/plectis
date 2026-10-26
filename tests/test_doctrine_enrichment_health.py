"""Doctrine enrichment health covers reader cards plus routing floors."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MICRO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, MICRO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


HEALTH = _load(
    "build_doctrine_enrichment_health",
    "scripts/build/build_doctrine_enrichment_health.py",
)


def _health_source_root(root: Path) -> None:
    (root / "core").mkdir()
    (root / HEALTH.ENRICHMENT_REL).write_text('{"records": []}\n', encoding="utf-8")
    for directory, _ in (
        *HEALTH.KIND_DIRS.values(),
        *HEALTH.ROUTING_KIND_DIRS.values(),
        HEALTH.PAPER_MODULE_DIR,
    ):
        (root / directory).mkdir()


@pytest.mark.parametrize("operation", ["--write", "--check"])
def test_mutation_and_completeness_require_source_corpora(
    tmp_path: Path, capsys, operation: str
) -> None:
    (tmp_path / "core").mkdir()
    (tmp_path / HEALTH.ENRICHMENT_REL).write_text('{"records": []}\n', encoding="utf-8")
    saved = tmp_path / HEALTH.HEALTH_REL
    saved.write_bytes(b'{"historical_snapshot": true}\n')

    with pytest.raises(SystemExit) as error:
        HEALTH.main(["--root", str(tmp_path), operation])

    assert error.value.code == 2
    assert "axioms/" in capsys.readouterr().err
    assert saved.read_bytes() == b'{"historical_snapshot": true}\n'


def test_write_accepts_explicit_empty_corpora(tmp_path: Path) -> None:
    _health_source_root(tmp_path)

    assert HEALTH.main(["--root", str(tmp_path), "--write"]) == 0

    health = json.loads((tmp_path / HEALTH.HEALTH_REL).read_text(encoding="utf-8"))
    assert health["total_objects"] == 0
    assert health["routing_floor"]["total_objects"] == 0


def test_check_accepts_explicit_empty_corpora(tmp_path: Path, capsys) -> None:
    _health_source_root(tmp_path)

    assert HEALTH.main(["--root", str(tmp_path), "--check"]) == 0

    assert json.loads(capsys.readouterr().out)["status"] == "complete"
    assert not (tmp_path / HEALTH.HEALTH_REL).exists()


def test_report_remains_available_without_source_corpora(tmp_path: Path, capsys) -> None:
    (tmp_path / "core").mkdir()
    (tmp_path / HEALTH.ENRICHMENT_REL).write_text('{"records": []}\n', encoding="utf-8")

    assert HEALTH.main(["--root", str(tmp_path)]) == 0

    assert json.loads(capsys.readouterr().out)["total_objects"] == 0
    assert not (tmp_path / HEALTH.HEALTH_REL).exists()


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


def _paper_module_record(code_path: str = "src/microcosm_core/organs/example.py") -> dict:
    return {
        "id": "paper_module.test",
        "kind": "paper_module",
        "authority_boundary": "test_boundary",
        "source_refs": [{"path": "source", "role": "source"}],
        "validator_refs": ["validator"],
        "receipt_refs": [],
        "anti_claims": ["not authority"],
        "relationships": {
            "source_authority": "json_capsule",
            "code_loci": [
                {
                    "path": code_path,
                    "resolution": "resolved",
                    "role": "Runtime authority.",
                    "symbols": ["run"],
                }
            ],
            "unpopulated_selective_relations": [],
            "edges": [
                {
                    "relation_id": "paper_module.explains.organ_or_mechanism",
                    "relation_verb": "explains",
                    "reverse_verb": "explained_by",
                    "target_id": "example",
                    "target_kind": "organ",
                    "target_status": "resolved_json_instance",
                    "justification": {
                        "source_ref": "source::subjects",
                        "summary": "Source row names this organ.",
                    },
                },
                {
                    "relation_id": "paper_module.governed_by.concept",
                    "relation_verb": "governed_by",
                    "reverse_verb": "governs",
                    "target_id": "concept.test",
                    "target_kind": "concept",
                    "target_status": "resolved_json_instance",
                    "justification": {
                        "source_ref": "source::concept_refs",
                        "summary": "Source row names this concept.",
                    },
                },
                {
                    "relation_id": "paper_module.cites.code_locus",
                    "relation_verb": "cites",
                    "reverse_verb": "cited_by",
                    "target_id": code_path,
                    "target_kind": "code_locus",
                    "target_status": "resolved_code_locus",
                    "justification": {
                        "source_ref": "source::code_loci",
                        "summary": "Source row names this code locus.",
                    },
                },
            ],
        },
    }


def test_health_projection_counts_doctrine_routing_floor(tmp_path: Path) -> None:
    _health_source_root(tmp_path)
    enrichment = json.loads((MICRO_ROOT / HEALTH.ENRICHMENT_REL).read_text(encoding="utf-8"))
    axiom = next(row for row in enrichment["records"] if row["kind"] == "axiom")
    (tmp_path / HEALTH.ENRICHMENT_REL).write_text(
        json.dumps({"records": [axiom]}), encoding="utf-8"
    )
    (tmp_path / "axioms" / f"{axiom['id']}.json").write_text(
        json.dumps({"id": axiom["id"]}), encoding="utf-8"
    )
    concept = {
        "id": "concept.test",
        "kind": "concept",
        "authority_boundary": "test_boundary",
        "source_refs": ["source"],
        "validator_refs": ["validator"],
        "receipt_refs": ["receipt"],
        "anti_claims": ["not authority"],
        "entry_surface_contract": {"required": True},
        "cluster_flag": {"concept_id": "concept.test"},
        "relationships": {
            "unpopulated_selective_relations": [],
            "edges": [{
                "relation_id": "concept.instantiated_by.mechanism",
                "relation_verb": "instantiated_by",
                "reverse_verb": "instantiates",
                "target_id": "mechanism.test.validates_example",
                "target_kind": "mechanism",
                "target_status": "resolved_json_instance",
                "justification": {"source_ref": "source", "summary": "Test mechanism."},
            }],
        },
    }
    (tmp_path / "concepts/concept.test.json").write_text(json.dumps(concept), encoding="utf-8")
    (tmp_path / "example.py").write_text("def run(): pass\n", encoding="utf-8")
    mechanism = _mechanism_record("example.py")
    planned_target = {
        "target_kind": "organ",
        "target_id": "example_host",
        "target_status": "planned_registry_or_atlas_target",
        "residual_pressure_ref": "test_residual",
        "reentry_condition": "Admit the example host through its registry owner.",
        "authority_boundary": "planned_target_marker_not_resolved_organ_authority",
    }
    mechanism["mechanism_payload"]["source_registry_row"] = {
        "planned_targets": [planned_target]
    }
    mechanism["relationships"]["source_registry_row_ref"] = "source::mechanism"
    mechanism["relationships"]["edges"].append({
        "relation_id": "mechanism.runs_in.organ",
        "relation_verb": "runs_in",
        "reverse_verb": "hosts",
        **{key: planned_target[key] for key in ("target_kind", "target_id", "target_status")},
        "justification": {"source_ref": "source::host", "summary": "Planned host."},
    })
    (tmp_path / "mechanisms/mechanism.test.json").write_text(
        json.dumps(mechanism), encoding="utf-8"
    )
    (tmp_path / "paper_modules/example.json").write_text(
        json.dumps(_paper_module_record("example.py")), encoding="utf-8"
    )

    report = HEALTH.build_health(tmp_path)
    routing = report["routing_floor"]
    mechanism_summary = routing["kinds"]["mechanism"]
    paper_modules = report["paper_module_readiness_audit"]

    assert report["reader_enrichment_total_objects"] == 1
    assert report["governed_floor_total_objects"] == 3
    assert routing["status"] == "complete"
    assert routing["covered_kinds"] == ["concept", "mechanism"]
    for kind in ("concept", "mechanism"):
        assert routing["kinds"][kind]["total"] == 1
        assert routing["kinds"][kind]["routed"] == 1
        assert routing["kinds"][kind]["incomplete_ids"] == []
    assert mechanism_summary["known_residual_selective_relation_row_count"] == 1
    assert mechanism_summary["known_residual_selective_relation_count"] == 1
    assert mechanism_summary["planned_edge_detail_count"] == 1
    assert mechanism_summary["planned_edge_counts_by_target_kind"] == {"organ": 1}
    assert mechanism_summary["planned_edge_counts_by_target_status"] == {
        "planned_registry_or_atlas_target": 1
    }
    detail = mechanism_summary["planned_edge_details"][0]
    assert detail["id"] == mechanism["id"]
    assert detail["residual_pressure_ref"] == "test_residual"
    assert detail["reentry_condition"] == planned_target["reentry_condition"]
    assert detail["planned_target_source_ref"] == "source::mechanism.planned_targets[0]"
    assert detail["planned_target_authority_boundary"] == planned_target["authority_boundary"]
    assert detail["next_safe_mutation_route"] == "organ_owner_admission_or_runs_in_source_remap"
    assert paper_modules["status"] == "complete"
    assert paper_modules["total_objects"] == 1
    assert paper_modules["ready_objects"] == 1
    assert paper_modules["source_authority_counts"] == {"json_capsule": 1}
    assert paper_modules["required_gap_ids"] == []
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


def test_paper_module_readiness_audit_accepts_resolved_routes(tmp_path: Path) -> None:
    code_path = "src/microcosm_core/organs/example.py"
    (tmp_path / code_path).parent.mkdir(parents=True)
    (tmp_path / code_path).write_text("def run(): pass\n", encoding="utf-8")
    record = _paper_module_record(code_path)

    issues = HEALTH._audit_paper_module_readiness_record(tmp_path, record)
    assert issues == []


# --- section-model boundary tests -----------------------------------------
# These are count-independent: they pin the projection's gate composition,
# plane, and authority grammar, so they must survive the day the paper-module
# corpus changes; the integration case above supplies its own source rows.


def test_section_model_keeps_frontier_audit_out_of_completion_gate() -> None:
    report = HEALTH.build_health(MICRO_ROOT)

    assert report["completion_gate_sections"] == [
        "reader_enrichment_floor",
        "formal_soundness",
        "reader_ladder",
        "doctrine_routing_floor",
    ]
    assert report["frontier_audit_sections"] == ["paper_module_readiness_audit"]
    sections = report["sections"]
    assert set(sections) == set(report["completion_gate_sections"]) | set(
        report["frontier_audit_sections"]
    )
    for name in report["completion_gate_sections"]:
        assert sections[name]["gate_role"] == "completion_floor", name
        assert sections[name]["counts_toward_completion_gate"] is True, name
    audit_section = sections["paper_module_readiness_audit"]
    assert audit_section["gate_role"] == "frontier_audit"
    assert audit_section["counts_toward_completion_gate"] is False
    assert "promotion" in audit_section["promotion_contract"].lower()

    # The governing standard and the checker must agree on the gate model;
    # promoting the audit means editing BOTH deliberately, plus this test.
    standard = json.loads(
        (MICRO_ROOT / "standards/std_microcosm_doctrine_enrichment.json").read_text(
            encoding="utf-8"
        )
    )
    model = standard["health_projection_section_model"]
    assert model["completion_gate_sections"] == report["completion_gate_sections"]
    assert model["frontier_audit_sections"] == report["frontier_audit_sections"]


def test_completion_gate_folds_exactly_the_declared_sections() -> None:
    report = HEALTH.build_health(MICRO_ROOT)

    gate_ok = (
        report["coverage_complete"]
        and report["formal_soundness"]["unsound"] == 0
        and report["reader_ladder"]["unsound"] == 0
        and report["routing_floor"]["status"] == "complete"
    )
    # Top-level status must equal the recomputation from completion-gate
    # sections alone: the frontier audit's status must never decide it.
    assert report["status"] == ("complete" if gate_ok else "partial")
    assert report["governed_floor_complete"] == (report["status"] == "complete")
    assert report["paper_module_readiness_audit"]["status"] in {"complete", "frontier"}


def test_authority_boundary_names_what_it_does_not_prove() -> None:
    report = HEALTH.build_health(MICRO_ROOT)

    boundary = report["authority_boundary"].lower()
    for phrase in ("support evidence", "proof authority", "release readiness"):
        assert phrase in boundary, phrase
    for name, section in report["sections"].items():
        does_not_prove = section["does_not_prove"].lower()
        assert "support" in does_not_prove, name
        assert "release" in does_not_prove, name


def test_sources_of_record_resolve_inside_supplied_source_root(tmp_path: Path) -> None:
    _health_source_root(tmp_path)
    report = HEALTH.build_health(tmp_path)

    declared = [report["source_of_record"]]
    for section in report["sections"].values():
        declared.extend(section["sources_of_record"])
    for source in declared:
        token = source.split()[0]
        assert not token.startswith("/"), source
        parts = Path(token).parts
        assert ".." not in parts, source
        base_parts: list[str] = []
        for part in parts:
            if any(glob_char in part for glob_char in "*?["):
                break
            base_parts.append(part)
        assert base_parts, source
        assert (tmp_path / Path(*base_parts)).exists(), source


def test_projection_declares_role_and_plane_beyond_enrichment() -> None:
    report = HEALTH.build_health(MICRO_ROOT)

    assert report["projection_role"] == "microcosm_doctrine_and_readiness_health_projection"
    assert report["plane"] == "microcosm_substrate_public_read_model"
    assert "readiness" in report["display_name"].lower()
    assert "not represented" in report["plane_note"]


def test_paper_module_readiness_audit_requires_json_capsule_subject_and_code_locus(tmp_path: Path) -> None:
    record = _paper_module_record("src/microcosm_core/organs/missing.py")
    record["relationships"]["source_authority"] = "legacy_markdown_projection"
    record["relationships"]["code_loci"] = []
    record["relationships"]["edges"] = []
    record["relationships"]["unpopulated_selective_relations"] = [
        {
            "relation_id": "paper_module.explains.organ_or_mechanism",
            "requirement": "required",
            "status": "residual_pressure",
        }
    ]

    issues = HEALTH._audit_paper_module_readiness_record(tmp_path, record)
    assert "source_authority_not_json_capsule" in issues
    assert "required_residual_relations_present" in issues
    assert "edges_missing" in issues
    assert "resolved_subject_route_missing" in issues
    assert "resolved_concept_route_missing" in issues
    assert "resolved_existing_code_locus_missing" in issues
