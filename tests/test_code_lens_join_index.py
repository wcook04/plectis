"""Tests for the code-lens join index v2 builder.

Proves the builder joins organs to runner source files + receipts, rolls up
per-organ specificity, classifies runner custody, refuses a source-body-leaking
lens snapshot, and never emits docstring prose; and that the v2 graph planes
materialize claim/route/family nodes with typed edges, compute resolved vs
deferred edge classes from what was actually built, and degrade honestly when
the atlas/route planes are absent.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_code_lens_join_index.py"
)
_spec = importlib.util.spec_from_file_location("build_code_lens_join_index", _SCRIPT)
assert _spec and _spec.loader
build_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_mod)


def _lens() -> dict:
    return {
        "payload_boundary": {"source_bodies_exported": False},
        "symbol_capsule_rows": [
            {
                "path": "src/microcosm_core/organs/foo.py",
                "symbol_name": "run_work",
                "is_real_coverage": True,
                "atom_specificity": "body_specific",
                "atom_has_non_goal": True,
                "source_class": "source_module",
            },
            {
                "path": "src/microcosm_core/organs/foo.py",
                "symbol_name": "helper",
                "is_real_coverage": False,
                "atom_specificity": "not_applicable",
                "atom_has_non_goal": False,
                "source_class": "source_module",
            },
            {
                "path": "src/microcosm_core/validators/bar.py",
                "symbol_name": "validate_bar",
                "is_real_coverage": True,
                "atom_specificity": "generic_unique",
                "atom_has_non_goal": False,
                "source_class": "source_module",
            },
        ],
    }


def _registry() -> dict:
    return {
        "implemented_organs": [
            {
                "organ_id": "foo",
                "runner": "microcosm_core.organs.foo",
                "evidence_class": "real_substrate_capsule",
                "claim_ceiling": "bounded",
                "status": "implemented",
                "validator_command": "pytest tests/test_foo.py -q",
                "generated_receipts": [
                    "receipts/foo/result.json",
                    "receipts/foo/source_capsules.json",
                ],
                "current_authority_receipt": "receipts/foo/authority.json",
            }
        ]
    }


def _atlas() -> dict:
    return {
        "organs": [
            {
                "organ_id": "foo",
                "family": "agent_reliability_and_safety",
                "claim_ceiling_restated": "Validates the declared fixture contract only.",
                "wires_to": ["bar_peer"],
                "axiom_refs": [{"ref": "axiom.bounded", "resolution_status": "resolved"}],
                "principle_refs": [],
                "concept_refs": [{"ref": "concept.fixture", "resolution_status": "resolved"}],
                "mechanism_refs": [
                    {"ref": "mechanism.foo.validates", "resolution_status": "resolved"},
                    {"ref": "mechanism.unresolved", "resolution_status": "missing"},
                ],
                "paper_module_ref": "paper_modules/foo.md",
            }
        ]
    }


def _routes() -> dict:
    return {
        "routes": [
            {
                "task_class": "agent-entry",
                "route_role": "agent_task_class_to_organ_selector",
                "primary_organ_id": "foo",
                "primary_display_name": "Foo Fixture Gate",
                "first_command": "microcosm foo run --input fixtures/foo",
                "stop_condition": "Stop when the named result record is visible.",
                "allowed_scope": "Validates the foo fixture contract only; no release decision.",
                "relevant_organs": [
                    {"organ_id": "foo", "compression_card": "MUST NOT BE COPIED"},
                    {"organ_id": "bar_peer", "compression_card": "MUST NOT BE COPIED"},
                ],
            }
        ]
    }


def _full_index() -> dict:
    return build_mod.build_join_index(
        _lens(), _registry(), atlas=_atlas(), routes=_routes()
    )


def test_join_index_joins_organ_to_runner_and_receipts() -> None:
    index = build_mod.build_join_index(_lens(), _registry())
    assert index["schema_version"] == "microcosm_code_lens_join_index_v2"
    assert index["source_bodies_exported"] is False
    assert index["export_band"] == "presence_only"
    assert index["rollup"]["organ_count"] == 1
    assert index["rollup"]["organs_with_resolved_runner_source"] == 1
    impl = [e for e in index["edges"] if e["kind"] == "implemented_by_runner"]
    assert impl == [
        {
            "from_type": "organ",
            "from": "foo",
            "to_type": "source_file",
            "to": "src/microcosm_core/organs/foo.py",
            "kind": "implemented_by_runner",
        }
    ]
    assert len([e for e in index["edges"] if e["kind"] == "emits_receipt"]) == 2


def test_runner_custody_and_specificity_rollup() -> None:
    index = build_mod.build_join_index(_lens(), _registry())
    organ = index["nodes"]["organ"][0]
    # organs/ runner is an exact-copy coupling zone.
    assert organ["runner_custody_basis"] == "directory_coupling_marker"
    # only the real-coverage body_specific symbol counts.
    assert organ["runner_specificity"] == {
        "real_coverage": 1,
        "body_specific": 1,
        "generic_unique": 0,
    }
    split = index["rollup"]["runner_custody_split"]
    assert split.get("directory_coupling_marker") == 1


def test_join_index_refuses_source_body_leak() -> None:
    lens = {"payload_boundary": {"source_bodies_exported": True}, "symbol_capsule_rows": []}
    with pytest.raises(SystemExit):
        build_mod.build_join_index(lens, {"implemented_organs": []})


def test_join_index_authority_ceiling_is_non_authorizing() -> None:
    index = build_mod.build_join_index(_lens(), _registry())
    ceiling = index["authority_ceiling"]
    assert ceiling["release_authorized"] is False
    assert ceiling["source_body_export_authorized"] is False
    assert ceiling["static_analysis_authority"] is False


def test_join_index_carries_no_capsule_prose_fields() -> None:
    # The source_file nodes must be counts/refs only -- never a docstring/prose key.
    index = build_mod.build_join_index(_lens(), _registry())
    for node in index["nodes"]["source_file"]:
        assert set(node) <= {
            "path",
            "source_class",
            "custody_basis",
            "symbol_count",
            "real_coverage",
            "body_specific",
            "generic_unique",
            "has_non_goal",
        }


# === v2 graph planes: claim / route / family nodes + computed edge classes =========


def test_join_index_materializes_claim_nodes_and_ontology_edges() -> None:
    index = _full_index()
    claims = index["nodes"]["claim"]
    assert len(claims) == 1
    claim = claims[0]
    assert claim["claim_id"] == "claim::foo"
    assert claim["claim_ceiling"] == "bounded"
    assert claim["claim_ceiling_restated"] == "Validates the declared fixture contract only."
    assert claim["validator_command"] == "pytest tests/test_foo.py -q"
    kinds = {e["kind"] for e in index["edges"]}
    assert {"asserts_claim", "validated_by", "proven_by"} <= kinds
    validated = next(e for e in index["edges"] if e["kind"] == "validated_by")
    assert validated["from"] == "claim::foo"
    assert validated["to"] == "pytest tests/test_foo.py -q"
    proven = next(e for e in index["edges"] if e["kind"] == "proven_by")
    assert proven["to"] == "receipts/foo/authority.json"


def test_join_index_materializes_route_fanout_without_card_bodies() -> None:
    index = _full_index()
    routes = index["nodes"]["route"]
    assert len(routes) == 1
    route = routes[0]
    assert route["task_class"] == "agent-entry"
    assert route["stop_condition"] == "Stop when the named result record is visible."
    assert route["first_command"] == "microcosm foo run --input fixtures/foo"
    assert route["allowed_scope"] == (
        "Validates the foo fixture contract only; no release decision."
    )
    assert route["primary_display_name"] == "Foo Fixture Gate"
    assert route["organ_count"] == 2
    # The heavy embedded organ cards must never be copied into the graph.
    assert "MUST NOT BE COPIED" not in str(index)
    routed = [e for e in index["edges"] if e["kind"] == "routes_to"]
    assert {(e["to"], e["role"]) for e in routed} == {
        ("foo", "primary"),
        ("bar_peer", "relevant"),
    }
    # Reachability is intersected with the organ set; the dangling target is
    # surfaced as route_targets_unknown instead of inflating coverage.
    assert index["rollup"]["organs_reachable_from_routes"] == 1
    assert index["rollup"]["route_targets_unknown"] == 1


def test_join_index_screens_secretish_route_values() -> None:
    routes = _routes()
    secret = "sk-" + "B" * 22
    routes["routes"][0]["stop_condition"] = f"Stop after exporting {secret}."
    index = build_mod.build_join_index(_lens(), _registry(), atlas=_atlas(), routes=routes)
    route = index["nodes"]["route"][0]
    assert route["stop_condition"] is None
    assert secret not in str(index)
    assert index["graph"]["leak_guard"]["values_dropped"] == 1


def test_join_index_materializes_family_wires_and_doctrine_edges() -> None:
    index = _full_index()
    assert index["nodes"]["family"] == [
        {"family_id": "agent_reliability_and_safety", "organ_count": 1}
    ]
    kinds = {e["kind"] for e in index["edges"]}
    assert {"member_of_family", "wires_to", "grounded_in_doctrine"} <= kinds
    doctrine = [e for e in index["edges"] if e["kind"] == "grounded_in_doctrine"]
    refs = {(e["to"], e["ref_kind"]) for e in doctrine}
    assert ("axiom.bounded", "axiom") in refs
    assert ("mechanism.foo.validates", "mechanism") in refs
    assert ("paper_modules/foo.md", "paper_module") in refs
    # Unresolved refs stay out of the graph.
    assert all(e["to"] != "mechanism.unresolved" for e in doctrine)
    wires = next(e for e in index["edges"] if e["kind"] == "wires_to")
    assert (wires["from"], wires["to"]) == ("foo", "bar_peer")


def test_join_index_computes_resolved_and_deferred_edge_classes() -> None:
    index = _full_index()
    graph = index["graph"]
    assert graph["resolved_edge_classes"] == [
        "claim_node_ontology",
        "cross_organ_route_topology",
    ]
    deferred = {d["edge_class"]: d for d in graph["deferred_edge_classes"]}
    assert set(deferred) == {"proof_internal_structure"}
    residual = deferred["proof_internal_structure"]
    # Residuals must be precise: missing-source class + owner + a re-entry surface
    # (a blocked_on statement is the honest form when no command can re-enter yet).
    assert residual["missing_source_class"] == "lean_proof_term_graph_not_extracted"
    assert residual["owner_path"] == "scripts/build_code_lens_join_index.py"
    assert residual["blocked_on"]
    assert "re_entry_command" not in residual
    assert graph["atlas_plane_present"] is True
    assert graph["route_plane_present"] is True
    rollup = index["rollup"]
    assert rollup["claim_node_count"] == 1
    assert rollup["route_node_count"] == 1
    assert rollup["family_node_count"] == 1
    assert rollup["organs_reachable_from_routes"] == 1
    assert rollup["route_targets_unknown"] == 1


def test_join_index_redefers_honestly_without_atlas_and_routes() -> None:
    index = build_mod.build_join_index(_lens(), _registry())
    graph = index["graph"]
    # Claims come from the registry plane alone, so they stay resolved.
    assert "claim_node_ontology" in graph["resolved_edge_classes"]
    # Route topology cannot be faked without the routes plane.
    deferred = {d["edge_class"]: d for d in graph["deferred_edge_classes"]}
    assert "cross_organ_route_topology" in deferred
    assert "proof_internal_structure" in deferred
    # The residual vocabulary is pinned so builder and packets cannot drift.
    assert (
        deferred["cross_organ_route_topology"]["missing_source_class"]
        == "agent_task_routes_plane_absent_from_join_index"
    )
    assert graph["route_plane_present"] is False
    assert graph["atlas_plane_present"] is False
    assert index["nodes"]["route"] == []
    assert index["nodes"]["family"] == []


def test_join_index_partial_plane_atlas_without_routes() -> None:
    # Atlas-only build: family/wires/doctrine edges materialize, the route class
    # honestly stays deferred -- the CLI-default degradation path.
    index = build_mod.build_join_index(_lens(), _registry(), atlas=_atlas())
    kinds = {e["kind"] for e in index["edges"]}
    assert {"member_of_family", "wires_to", "grounded_in_doctrine"} <= kinds
    assert index["nodes"]["family"] != []
    graph = index["graph"]
    assert graph["atlas_plane_present"] is True
    assert graph["route_plane_present"] is False
    deferred = {d["edge_class"] for d in graph["deferred_edge_classes"]}
    assert "cross_organ_route_topology" in deferred
