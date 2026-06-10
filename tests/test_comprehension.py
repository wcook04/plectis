"""Tests for the Comprehension Plane: the source-body-free read-pack compiler.

Proves ``microcosm comprehend`` compiles bounded read packs from the join index +
organ atlas + synopses (never source bodies), routes goals to modes, stamps a
non-authorizing ceiling on every pack, and that the cold-agent assay confirms the
packs answer substrate / authority / organ questions without opening source.
"""
from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import comprehension as C


def _write_fixture(root: Path, *, leaky: bool = False, legacy_graph: bool = False) -> None:
    """Write a minimal substrate root (atlas + synopses + join index) for tests.

    legacy_graph=True writes a pre-v2 join index (no graph block, no claim/route/
    family nodes) so tests can prove the packets re-defer honestly on old clones.
    """
    (root / "core").mkdir(parents=True, exist_ok=True)
    (root / "receipts/code_lens").mkdir(parents=True, exist_ok=True)
    atlas = {
        "authority_boundary": "Plain-language comprehension layer over the registry.",
        "anti_claim": "Glosses are navigation metadata only; not release authority.",
        "organs": [
            {
                "organ_id": "alpha_validator",
                "display_name": "Alpha Validator",
                "specialty": "binding contracts",
                "family": "agent_reliability_and_safety",
                "human_gloss": "Validates declared public bindings and reports findings.",
                "agent_gloss": "Run it to check public binding rows.",
                "first_command": "microcosm alpha-validator validate --input fixtures/x",
                "wires_to": ["beta_projection"],
                "mechanism_refs": [
                    {"ref": "mechanism.alpha.validates", "resolution_status": "resolved"}
                ],
                "concept_refs": [{"ref": "concept.binding", "resolution_status": "resolved"}],
                "paper_module_ref": "paper.alpha",
                "claim_ceiling_restated": "Validates only the declared public contract.",
                "standalone_or_wired": "wired",
                "code_loci": [
                    {"path": "src/microcosm_core/organs/alpha_validator.py",
                     "symbols": ["validate_bindings", "report"]}
                ],
            },
            {
                "organ_id": "beta_projection",
                "display_name": "Beta Projection",
                "specialty": "drift projection",
                "family": "import_projection_and_drift",
                "human_gloss": "Projects drift between imported and owned bodies.",
                "agent_gloss": "Run it to see drift.",
                "first_command": "microcosm beta-projection run",
                "wires_to": [],
                "mechanism_refs": [],
                "concept_refs": [],
                "paper_module_ref": "paper.beta",
                "claim_ceiling_restated": "Projects drift only; does not certify release.",
                "standalone_or_wired": "standalone",
                "code_loci": [],
            },
        ],
    }
    synopses = {
        "schema_version": "x",
        "synopses": {
            "alpha_validator": "Checks public binding rows and rejects contract breaks.",
            "beta_projection": "Shows where imported bodies drifted from their owned source.",
        },
    }
    join = {
        "schema_version": "microcosm_code_lens_join_index_v2",
        "export_band": "presence_only",
        "source_bodies_exported": bool(leaky),
        "nodes": {
            "organ": [
                {
                    "organ_id": "alpha_validator",
                    "evidence_class": "semantic_validator",
                    "claim_ceiling": "validates_public_contract",
                    "status": "accepted",
                    "family": "agent_reliability_and_safety",
                    "runner_module": "microcosm_core.organs.alpha_validator",
                    "runner_source_ref": "src/microcosm_core/organs/alpha_validator.py",
                    "runner_source_resolved": True,
                    "runner_custody_basis": "directory_coupling_marker",
                    "runner_specificity": {"real_coverage": 5, "body_specific": 4, "generic_unique": 1},
                    "validator_command": "microcosm alpha-validator validate --input fixtures/x",
                    "authority_receipt": "receipts/first_wave/alpha_validator/acceptance.json",
                },
                {
                    "organ_id": "beta_projection",
                    "evidence_class": "algorithmic_projection",
                    "claim_ceiling": "projects_drift",
                    "status": "accepted",
                    "family": "import_projection_and_drift",
                    "runner_module": "microcosm_core.beta_projection",
                    "runner_source_ref": "src/microcosm_core/beta_projection.py",
                    "runner_source_resolved": True,
                    "runner_custody_basis": "owned",
                    "runner_specificity": {"real_coverage": 3, "body_specific": 3, "generic_unique": 0},
                    "validator_command": "microcosm beta-projection run",
                    "authority_receipt": None,
                },
            ],
            "source_file": [],
        },
        "edges": [
            {"from_type": "organ", "from": "alpha_validator", "to_type": "source_file",
             "to": "src/microcosm_core/organs/alpha_validator.py", "kind": "implemented_by_runner"},
            {"from_type": "organ", "from": "alpha_validator", "to_type": "receipt",
             "to": "receipts/first_wave/alpha_validator/acceptance.json", "kind": "emits_receipt"},
        ],
    }
    if legacy_graph:
        # Pre-v2 clones: no graph block, no claim/route/family nodes.
        join["schema_version"] = "microcosm_code_lens_join_index_v0"
        for node in join["nodes"]["organ"]:
            node.pop("family", None)
            node.pop("validator_command", None)
    else:
        join["nodes"]["claim"] = [
            {
                "claim_id": "claim::alpha_validator",
                "organ_id": "alpha_validator",
                "claim_ceiling": "validates_public_contract",
                "claim_ceiling_restated": "Validates only the declared public contract.",
                "evidence_class": "semantic_validator",
                "evidence_strength_rank": 4,
                "truth_accounting_bucket": "owned_validator",
                "validator_command": "microcosm alpha-validator validate --input fixtures/x",
                "authority_receipt": "receipts/first_wave/alpha_validator/acceptance.json",
            },
            {
                "claim_id": "claim::beta_projection",
                "organ_id": "beta_projection",
                "claim_ceiling": "projects_drift",
                "claim_ceiling_restated": "Projects drift only; does not certify release.",
                "evidence_class": "algorithmic_projection",
                "evidence_strength_rank": 3,
                "truth_accounting_bucket": "owned_projection",
                "validator_command": "microcosm beta-projection run",
                "authority_receipt": None,
            },
        ]
        join["nodes"]["route"] = [
            {
                "task_class": "agent-entry",
                "route_role": "agent_task_class_to_organ_selector",
                "primary_organ_id": "alpha_validator",
                "primary_display_name": "Alpha Validator",
                "first_command": "microcosm alpha-validator validate --input fixtures/x",
                "stop_condition": "Stop when the binding receipt is visible.",
                "allowed_scope": "Validates declared binding rows only; no release decision.",
                "organ_count": 2,
            }
        ]
        join["nodes"]["family"] = [
            {"family_id": "agent_reliability_and_safety", "organ_count": 1},
            {"family_id": "import_projection_and_drift", "organ_count": 1},
        ]
        join["edges"] += [
            {"from_type": "organ", "from": "alpha_validator", "to_type": "claim",
             "to": "claim::alpha_validator", "kind": "asserts_claim"},
            {"from_type": "claim", "from": "claim::alpha_validator", "to_type": "validator_command",
             "to": "microcosm alpha-validator validate --input fixtures/x", "kind": "validated_by"},
            {"from_type": "claim", "from": "claim::alpha_validator", "to_type": "receipt",
             "to": "receipts/first_wave/alpha_validator/acceptance.json", "kind": "proven_by"},
            {"from_type": "organ", "from": "beta_projection", "to_type": "claim",
             "to": "claim::beta_projection", "kind": "asserts_claim"},
            {"from_type": "organ", "from": "alpha_validator", "to_type": "family",
             "to": "agent_reliability_and_safety", "kind": "member_of_family"},
            {"from_type": "organ", "from": "beta_projection", "to_type": "family",
             "to": "import_projection_and_drift", "kind": "member_of_family"},
            {"from_type": "organ", "from": "alpha_validator", "to_type": "organ",
             "to": "beta_projection", "kind": "wires_to"},
            {"from_type": "organ", "from": "alpha_validator", "to_type": "doctrine_ref",
             "to": "mechanism.alpha.validates", "kind": "grounded_in_doctrine",
             "ref_kind": "mechanism"},
            {"from_type": "route", "from": "agent-entry", "to_type": "organ",
             "to": "alpha_validator", "kind": "routes_to", "role": "primary"},
            {"from_type": "route", "from": "agent-entry", "to_type": "organ",
             "to": "beta_projection", "kind": "routes_to", "role": "relevant"},
        ]
        kind_counts: dict[str, int] = {}
        for edge in join["edges"]:
            kind_counts[edge["kind"]] = kind_counts.get(edge["kind"], 0) + 1
        join["graph"] = {
            "edge_kinds": sorted(kind_counts),
            "edge_kind_counts": kind_counts,
            "resolved_edge_classes": ["claim_node_ontology", "cross_organ_route_topology"],
            "deferred_edge_classes": [
                {
                    "edge_class": "proof_internal_structure",
                    "missing": "theorem -> lemma -> tactic edges inside a proof organ",
                    "missing_source_class": "lean_proof_term_graph_not_extracted",
                    "owner_path": "scripts/build_code_lens_join_index.py",
                    "re_entry_command": "PYTHONPATH=src python3 scripts/build_code_lens_join_index.py --help",
                    "would_come_from": "a Lean-aware proof-graph builder feeding this join index",
                }
            ],
            "atlas_plane_present": True,
            "route_plane_present": True,
        }
        join["rollup"] = {
            "organ_count": 2,
            "claim_node_count": 2,
            "route_node_count": 1,
            "family_node_count": 2,
            "organs_reachable_from_routes": 2,
            "edge_count": len(join["edges"]),
        }
    (root / "core/organ_atlas.json").write_text(json.dumps(atlas))
    (root / "core/component_public_synopses.json").write_text(json.dumps(synopses))
    (root / "receipts/code_lens/code_lens_join_index_v0.json").write_text(json.dumps(join))


def test_first_contact_pack_is_presence_only_and_maps_families(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="first-contact")
    assert pack["schema_version"] == C.READ_PACK_SCHEMA
    assert pack["export_band"] == "presence_only"
    assert pack["mode"] == "tutorial"
    # Family roster surfaces both organs across their two families.
    roster = pack["selected_nodes"][0]["families"]
    fams = {f["family"]: f["count"] for f in roster}
    assert fams == {"agent_reliability_and_safety": 1, "import_projection_and_drift": 1}
    # The headline custody truth is surfaced.
    custody = pack["specificity_risks"][0]["custody_split"]
    assert custody.get("directory_coupling_marker") == 1
    # Ceiling authorizes nothing.
    assert all(v is False for v in pack["authority_ceiling"].values())


def test_organ_pack_joins_synopsis_gloss_and_source_spans(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="organ", organ_id="alpha_validator")
    assert pack["found"] is True
    assert pack["mode"] == "explanation"
    # what_this_is draws from the synopsis + human gloss.
    assert "binding rows" in pack["summary"]["what_this_is"]
    # first_command and mechanisms appear in inspect-next.
    joined = " ".join(pack["summary"]["what_to_inspect_next"])
    assert "alpha-validator validate" in joined
    assert "mechanism.alpha.validates" in joined
    # ceiling restated as what-not-to-trust.
    assert "declared public contract" in pack["summary"]["what_not_to_trust"]
    # source-span escalation carries code_loci path + symbols, no bodies.
    spans = {s["path"]: s["symbols"] for s in pack["source_span_escalation"]}
    assert "validate_bindings" in spans["src/microcosm_core/organs/alpha_validator.py"]
    # custody-bound runner is flagged as comprehend-via-metadata.
    risk = pack["specificity_risks"][0]
    assert risk["runner_custody_basis"] == "directory_coupling_marker"
    assert "exact-copy macro body" in risk["note"]


def test_unknown_organ_returns_not_found(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="organ", organ_id="ghost")
    assert pack["found"] is False
    assert "ghost" in pack["summary"]["what_this_is"]


def test_authority_pack_reports_distribution_and_zero_authorization(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="authority")
    dist = pack["selected_nodes"][0]["by_evidence_class"]
    assert dist == {"algorithmic_projection": 1, "semantic_validator": 1}
    assert "navigation metadata only" in pack["summary"]["what_not_to_trust"]
    assert all(v is False for v in pack["authority_ceiling"].values())


def test_organs_index_lists_every_organ_with_synopsis(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="organs")
    rows = {n["organ_id"]: n for n in pack["selected_nodes"]}
    assert set(rows) == {"alpha_validator", "beta_projection"}
    assert "binding rows" in rows["alpha_validator"]["synopsis"]


def test_goal_routes_to_organ_authority_and_math_packet(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    bundle = C.load_inputs(tmp_path)
    assert C.route_goal("tell me about alpha_validator", bundle)[:2] == ("organ", "alpha_validator")
    assert C.route_goal("what am I allowed to trust", bundle)[0] == "authority"
    # v2: math is a first-class packet now, no longer a deferred-to-first-contact note.
    assert C.route_goal("show me all the math proofs", bundle)[0] == "math"
    assert C.route_goal("what should I work on for the Microcosm release?", bundle)[0] == "mutation_plan"


def test_packs_never_leak_raw_atom_bullets(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    for mode in ("first-contact", "authority", "organs"):
        assert not C._pack_leaks_source_body(C.comprehend(root=tmp_path, mode=mode))
    # And the detector actually fires on an injected raw atom bullet.
    poisoned = {"summary": {"what_this_is": "- Teleology: leaked docstring"}}
    assert C._pack_leaks_source_body(poisoned) is True


def test_membrane_guard_refuses_leaky_join_index(tmp_path: Path) -> None:
    _write_fixture(tmp_path, leaky=True)
    try:
        C.load_inputs(tmp_path)
    except ValueError as exc:
        assert "source bodies" in str(exc)
    else:  # pragma: no cover - guard must raise
        raise AssertionError("load_inputs must refuse a source-body-leaking join index")


def test_assay_meets_thresholds_on_fixture(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    assay = C.run_comprehension_assay(tmp_path)
    assert assay["answerable_without_source_pct"] >= 80.0
    assert assay["wrong_authority_claims"] == 0
    assert assay["source_body_leaks"] == 0
    # The assay prefers a custody-bound organ so the runner-source question bites.
    assert assay["sample_organ"] == "alpha_validator"


def test_cache_build_writes_presence_only_packs(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    manifest = C.build_cached_read_packs(tmp_path)
    names = {p["name"] for p in manifest["packs"]}
    # v2/v3: the packet atlas + whole-system self-model join the prebuilt entry packs.
    assert names == {"first_contact", "authority", "organs_index", "self_model", "packet_atlas"}
    for entry in manifest["packs"]:
        assert (tmp_path / entry["path"]).is_file()
        assert entry["bytes"] > 0


def test_live_substrate_assay_invariants() -> None:
    """Against the real substrate root: packs must stay answerable and leak-free."""
    assay = C.run_comprehension_assay(C.default_root())
    assert assay["answerable_without_source_pct"] >= 80.0
    assert assay["wrong_authority_claims"] == 0
    assert assay["source_body_leaks"] == 0
    # Latency stays far under the 300ms first-contact SLO (no SQLite needed).
    assert assay["max_compile_ms"] < 100.0


# --- atom_value_membrane_v1: local_semantic_excerpt band ---------------------------

def _write_owned_module(
    root: Path,
    rel: str,
    *,
    n_symbols: int = 3,
    secret_value: str | None = None,
    private_value: str | None = None,
) -> None:
    """Write an owned (or coupling-zone) source module with authored atoms."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = ['"""Fixture module."""', ""]
    for i in range(n_symbols):
        guarantee = "returns a bounded list of projected rows from the manifest"
        fails = "missing input -> raises OSError; malformed -> ValueError"
        if secret_value and i == 0:
            guarantee = f"returns the cached token {secret_value} for the row"
        if private_value and i == 0:
            fails = f"on error writes a dump under {private_value} then re-raises"
        parts += [
            f"def owned_fn_{i}(value):",
            '    """Owned fixture function.',
            "",
            f"    - Teleology: owned helper {i} authored for the excerpt test.",
            f"    - Guarantee: {guarantee}.",
            f"    - Fails: {fails}.",
            "    - Non-goal: does not authorize source-body export or release.",
            '    """',
            "    return []",
            "",
        ]
    path.write_text("\n".join(parts))


def test_path_excerpts_emit_bounded_owned_atom_values(tmp_path: Path) -> None:
    _write_owned_module(tmp_path, "src/microcosm_core/sample_owned.py", n_symbols=2)
    pack = C.comprehend(root=tmp_path, mode="path", path="src/microcosm_core/sample_owned.py")
    assert pack["export_band"] == "local_semantic_excerpt"
    assert pack["found"] is True
    assert len(pack["semantic_excerpts"]) == 2
    row = pack["semantic_excerpts"][0]
    assert "Guarantee" in row["atom_values"] and "Non-goal" in row["atom_values"]
    assert row["source_span_ref"].startswith("src/microcosm_core/sample_owned.py:")
    assert len(row["fingerprint"]) == 12
    # every atom value respects the char cap
    for value in row["atom_values"].values():
        assert len(value) <= C.MAX_ATOM_CHARS
    assert all(v is False for v in pack["authority_ceiling"].values())


def test_coupling_zone_path_is_refused(tmp_path: Path) -> None:
    _write_owned_module(tmp_path, "src/microcosm_core/organs/runner.py")
    ex = C.extract_atom_excerpts(tmp_path, "src/microcosm_core/organs/runner.py")
    assert ex["eligible"] is False
    assert ex["custody_basis"] == "directory_coupling_marker"
    assert ex["symbols"] == []


def test_outside_owned_root_is_refused(tmp_path: Path) -> None:
    _write_owned_module(tmp_path, "examples/bundle/mod.py")
    ex = C.extract_atom_excerpts(tmp_path, "examples/bundle/mod.py")
    assert ex["eligible"] is False
    assert ex["symbols"] == []


def test_secret_and_private_path_values_are_dropped(tmp_path: Path) -> None:
    # Build the shapes at runtime so this test file contains no literal secret.
    secret = "sk-" + "A" * 22
    private = "/Users/" + "operator/secret"
    _write_owned_module(
        tmp_path,
        "src/microcosm_core/leaky.py",
        n_symbols=1,
        secret_value=secret,
        private_value=private,
    )
    ex = C.extract_atom_excerpts(tmp_path, "src/microcosm_core/leaky.py")
    assert ex["eligible"] is True
    # The Guarantee (secret) and Fails (private path) atoms were dropped, not emitted.
    body = json.dumps(ex)
    assert secret not in body
    assert private not in body
    assert ex["leak_guard"]["secret_shapes_dropped"] == 1
    assert ex["leak_guard"]["private_paths_dropped"] == 1


def test_excerpt_pack_respects_byte_budget(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(C, "MAX_EXCERPT_PACK_BYTES", 200)
    _write_owned_module(tmp_path, "src/microcosm_core/big.py", n_symbols=6)
    ex = C.extract_atom_excerpts(tmp_path, "src/microcosm_core/big.py")
    assert ex["omitted_for_budget"] > 0
    assert ex["symbol_count"] < 6


def test_organ_with_excerpts_notes_custody_bound_loci(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    # alpha_validator's code_loci points at a coupling-zone runner -> noted, not excerpted.
    _write_owned_module(tmp_path, "src/microcosm_core/organs/alpha_validator.py")
    pack = C.comprehend(
        root=tmp_path, mode="organ", organ_id="alpha_validator", with_excerpts=True
    )
    assert pack["export_band"] == "local_semantic_excerpt"
    notes = {n["path"]: n["custody_basis"] for n in pack["excerpt_custody_notes"]}
    assert "src/microcosm_core/organs/alpha_validator.py" in notes


def test_presence_only_cache_never_carries_excerpts(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    C.build_cached_read_packs(tmp_path)
    cache_dir = tmp_path / "receipts/code_lens/read_packs"
    for name in ("first_contact.json", "authority.json", "organs_index.json", "packet_atlas.json"):
        pack = json.loads((cache_dir / name).read_text())
        assert pack["export_band"] == "presence_only"
        assert "semantic_excerpts" not in pack
        assert "atom_values" not in json.dumps(pack)


def test_hard_assay_invariants_on_live_root() -> None:
    """The hard assay must carry real atom values with zero leaks/custody violations."""
    hard = C.run_hard_comprehension_assay(C.default_root())
    assert hard["owned_symbols_excerpted"] >= 10
    assert hard["answerable_with_atom_values_pct"] >= 80.0
    assert hard["excerpt_leak_count"] == 0
    assert hard["custody_violation_count"] == 0
    assert hard["custody_target_excerpted_symbols"] == 0


# === Comprehension Packet Compiler v2: packet atlas + slices + route assay =========


def test_packet_atlas_lists_every_spec_and_default_entry(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="packet-atlas")
    assert pack["schema_version"] == C.PACKET_ATLAS_SCHEMA
    assert pack["default_entry"] == "first_contact"
    ids = [n["packet_id"] for n in pack["selected_nodes"]]
    assert ids == [s["packet_id"] for s in C.PACKET_SPECS]
    for row in pack["selected_nodes"]:
        assert row["command"] and row["when_needed"]
        assert row["export_band"] in ("presence_only", "local_semantic_excerpt")
        assert "max_bytes" in row and "slo_ms" in row
    assert "closed" in pack["sqlite_gate"]


def test_packet_atlas_is_presence_only_and_carries_no_excerpts(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="packet-atlas")
    assert pack["export_band"] == "presence_only"
    assert "semantic_excerpts" not in pack
    assert "atom_values" not in json.dumps(pack)
    assert all(v is False for v in pack["authority_ceiling"].values())


def test_every_next_packet_resolves_to_a_known_packet() -> None:
    known = {s["packet_id"] for s in C.PACKET_SPECS}
    for spec in C.PACKET_SPECS:
        for nxt in spec["next_packets"]:
            assert nxt in known, f"{spec['packet_id']} -> unknown next_packet {nxt}"
    # The entry packet cannot be a dead end.
    assert C._SPEC_BY_ID["first_contact"]["next_packets"]


def test_every_spec_mode_is_dispatchable() -> None:
    for spec in C.PACKET_SPECS:
        mode = spec["mode"]
        assert mode in C._MODE_COMPILERS or mode in ("path", "mutation_plan")


def test_organ_cluster_is_substantive_for_a_family(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(
        root=tmp_path, mode="organ_cluster", target="import_projection_and_drift"
    )
    assert pack["found"] is True
    assert pack["family"] == "import_projection_and_drift"
    assert pack["packet_kind"] == "explanation"
    organs = [n["organ_id"] for n in pack["selected_nodes"] if n.get("kind") == "organ"]
    assert "beta_projection" in organs
    assert "mechanisms" in pack["shared_refs"]
    assert any(n.get("kind") == "evidence_distribution" for n in pack["selected_nodes"])


def test_organ_cluster_chooser_when_family_unknown(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="organ_cluster", target="")
    assert pack["found"] is False
    fams = {n["family"] for n in pack["selected_nodes"]}
    assert "import_projection_and_drift" in fams


def test_math_packet_names_family_and_defers_proof_internal_edges(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="math")
    assert pack["family"] == "formal_math_and_proof"
    assert pack["export_band"] == "presence_only"
    edge_classes = {d["edge_class"] for d in pack["deferred_edges"]}
    assert "proof_internal_structure" in edge_classes
    assert "proof" in pack["summary"]["what_this_is"].lower()


def test_claim_trace_chains_claim_validator_and_receipts(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="claim_trace", target="alpha_validator")
    assert pack["found"] is True
    assert pack["packet_kind"] == "proof_trace"
    kinds = {n["kind"] for n in pack["selected_nodes"]}
    assert {"claim", "validator"} <= kinds
    assert "receipts/first_wave/alpha_validator/acceptance.json" in pack["receipt_refs"]
    # v2: the claim is the join index's FIRST-CLASS claim node, not a synthesis.
    claim = next(n for n in pack["selected_nodes"] if n["kind"] == "claim")
    assert claim["graph_backed"] is True
    assert claim["claim_id"] == "claim::alpha_validator"
    # The POSITIVE claim statement (from the synopsis), not only the ceiling negations.
    assert "binding rows" in claim["claim_statement"]
    edge_kinds = {e["kind"] for e in pack["selected_edges"]}
    assert {"asserts_claim", "validated_by", "proven_by"} <= edge_kinds
    # Purpose-filtered: the organ's doctrine/wires neighborhood stays on the organ
    # packet; the claim packet carries only the claim chain + receipts.
    assert edge_kinds <= {"asserts_claim", "validated_by", "proven_by", "emits_receipt"}
    assert pack["edge_kinds_included"] == [
        "asserts_claim", "validated_by", "proven_by", "emits_receipt",
    ]
    # The authority receipt is not double-counted when it is also an emitted receipt.
    assert len(pack["receipt_refs"]) == len(set(pack["receipt_refs"]))
    # claim_node_ontology is resolved by the graph -- no longer deferred.
    assert pack["deferred_edges"] == []
    assert pack["graph_backed"]["edge_classes_resolved"] == ["claim_node_ontology"]


def test_flow_packet_orders_validator_runner_receipts(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="flow", target="alpha_validator")
    assert pack["found"] is True
    stages = [n["role"] for n in pack["selected_nodes"] if n.get("kind") == "flow_stage"]
    assert stages == ["validator", "runner", "receipts"]
    # v2: the route plane resolves cross_organ_route_topology -- no longer deferred.
    assert pack["deferred_edges"] == []
    route_ctx = next(n for n in pack["selected_nodes"] if n.get("kind") == "route_context")
    assert route_ctx["routes"][0]["task_class"] == "agent-entry"
    assert route_ctx["routes"][0]["role"] == "primary"
    assert route_ctx["routes"][0]["stop_condition"] == "Stop when the binding receipt is visible."
    wired = next(n for n in pack["selected_nodes"] if n.get("kind") == "wired_neighbors")
    assert wired["wires_to"] == ["beta_projection"]
    assert pack["reading_boundary"]["stop_condition"]
    # Purpose-filtered flow edges: execution/topology kinds only.
    assert {e["kind"] for e in pack["selected_edges"]} <= {
        "implemented_by_runner", "emits_receipt", "wires_to", "routes_to",
    }
    assert pack["graph_backed"]["edge_classes_resolved"] == ["cross_organ_route_topology"]
    # Inbound wires are real topology too: beta's flow shows who wires INTO it.
    beta = C.comprehend(root=tmp_path, mode="flow", target="beta_projection")
    beta_wired = next(
        n for n in beta["selected_nodes"] if n.get("kind") == "wired_neighbors"
    )
    assert beta_wired["wired_from"] == ["alpha_validator"]
    assert beta_wired["wires_to"] == []


def test_organ_pack_carries_reading_boundary_and_graph_edges(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="organ", organ_id="alpha_validator")
    boundary = pack["reading_boundary"]
    assert boundary["stop_condition"] == "Stop when the binding receipt is visible."
    assert boundary["allowed_scope"] == (
        "Validates declared binding rows only; no release decision."
    )
    assert boundary["task_classes"] == ["agent-entry"]
    edge_kinds = {e["kind"] for e in pack["selected_edges"]}
    assert {"member_of_family", "wires_to", "grounded_in_doctrine", "routes_to"} <= edge_kinds
    # beta is routed too (relevant role), so it inherits the route-bound boundary.
    beta = C.comprehend(root=tmp_path, mode="organ", organ_id="beta_projection")
    beta_boundary = beta["reading_boundary"]
    assert beta_boundary["task_classes"] == ["agent-entry"]
    assert beta_boundary["stop_condition"] == "Stop when the binding receipt is visible."


def test_reading_boundary_fallback_when_no_route_lands(tmp_path: Path) -> None:
    """An unrouted organ gets an honest fallback labelled as guidance, never a fake
    route-bound stop condition."""
    _write_fixture(tmp_path, legacy_graph=True)  # no route plane at all
    pack = C.comprehend(root=tmp_path, mode="organ", organ_id="alpha_validator")
    boundary = pack["reading_boundary"]
    assert boundary["stop_condition"] is None
    assert boundary["task_classes"] == []
    assert "comprehension-layer guidance, not route data" in boundary["fallback_guidance"]


def test_packets_redefer_honestly_on_legacy_join_index(tmp_path: Path) -> None:
    """A pre-v2 clone must re-defer the graph edge classes, not fake resolution."""
    _write_fixture(tmp_path, legacy_graph=True)
    claim_pack = C.comprehend(root=tmp_path, mode="claim_trace", target="alpha_validator")
    deferred = {d["edge_class"]: d for d in claim_pack["deferred_edges"]}
    assert set(deferred) == {"claim_node_ontology"}
    # Residuals are precise: missing-source class + owner + re-entry command.
    residual = deferred["claim_node_ontology"]
    assert residual["missing_source_class"]
    assert residual["owner_path"] == "scripts/build_code_lens_join_index.py"
    assert residual["re_entry_command"]
    claim = next(n for n in claim_pack["selected_nodes"] if n["kind"] == "claim")
    assert claim["graph_backed"] is False
    flow_pack = C.comprehend(root=tmp_path, mode="flow", target="alpha_validator")
    assert {d["edge_class"] for d in flow_pack["deferred_edges"]} == {
        "cross_organ_route_topology"
    }
    self_model = C.comprehend(root=tmp_path, mode="self-model")
    assert {d["edge_class"] for d in self_model["deferred_edges"]} == {
        "proof_internal_structure",
        "cross_organ_route_topology",
        "claim_node_ontology",
    }
    # The residual vocabulary matches the builder's exactly (no drift).
    by_class = {d["edge_class"]: d for d in self_model["deferred_edges"]}
    assert (
        by_class["cross_organ_route_topology"]["missing_source_class"]
        == "agent_task_routes_plane_absent_from_join_index"
    )
    assert self_model["route_topology"]["route_node_count"] == 0
    assert "rebuild" in self_model["route_topology"]["note"]
    # The improvement ranker's rank-3 row reverts to the route/claim extraction
    # target while those classes are deferred (the other half of the lifecycle).
    plan = C.comprehend(root=tmp_path, mode="mutation_plan")
    rank3 = next(r for r in plan["selected_nodes"] if r["rank"] == 3)
    assert "route and claim" in rank3["title"].lower()
    assert set(rank3["ranking_basis"]["deferred_edge_classes"]) >= {
        "cross_organ_route_topology",
        "claim_node_ontology",
    }


def test_declared_resolution_over_empty_planes_is_not_trusted(tmp_path: Path) -> None:
    """A corrupted index that DECLARES resolution while carrying no claim/route
    nodes must re-defer: the reader derives resolution structurally, never from
    the label."""
    _write_fixture(tmp_path)
    join_path = tmp_path / "receipts/code_lens/code_lens_join_index_v0.json"
    join = json.loads(join_path.read_text())
    join["nodes"]["claim"] = []
    join["nodes"]["route"] = []
    join["edges"] = [
        e for e in join["edges"] if e["kind"] not in ("asserts_claim", "routes_to")
    ]
    # The (now false) declaration stays in place -- that is the attack.
    assert "claim_node_ontology" in join["graph"]["resolved_edge_classes"]
    join_path.write_text(json.dumps(join))
    claim_pack = C.comprehend(root=tmp_path, mode="claim_trace", target="alpha_validator")
    assert {d["edge_class"] for d in claim_pack["deferred_edges"]} == {
        "claim_node_ontology"
    }
    claim = next(n for n in claim_pack["selected_nodes"] if n["kind"] == "claim")
    assert claim["graph_backed"] is False
    flow_pack = C.comprehend(root=tmp_path, mode="flow", target="alpha_validator")
    assert {d["edge_class"] for d in flow_pack["deferred_edges"]} == {
        "cross_organ_route_topology"
    }


def test_cluster_pack_carries_task_classes_and_doctrine_spine(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(
        root=tmp_path, mode="organ_cluster", target="agent_reliability_and_safety"
    )
    assert pack["task_classes"] == ["agent-entry"]
    assert {"axioms", "principles"} <= set(pack["shared_refs"])
    # Legacy clones have no routes_to edges, so the field is honestly absent.
    legacy_root = tmp_path / "legacy"
    _write_fixture(legacy_root, legacy_graph=True)
    legacy = C.comprehend(
        root=legacy_root, mode="organ_cluster", target="agent_reliability_and_safety"
    )
    assert "task_classes" not in legacy


def test_packet_atlas_data_status_is_computed_from_graph_state(tmp_path: Path) -> None:
    """The menu must not keep apologizing for edges the join index now carries,
    nor advertise 'full' over a degraded clone."""
    _write_fixture(tmp_path)
    atlas = C.comprehend(root=tmp_path, mode="packet-atlas")
    status = {n["packet_id"]: n["data_status"] for n in atlas["selected_nodes"]}
    assert status["claim_trace"] == "full"
    assert status["flow"] == "full"
    assert status["math"] == "substantive_with_deferred_edges"  # proof still deferred
    legacy_root = tmp_path / "legacy"
    _write_fixture(legacy_root, legacy_graph=True)
    legacy_atlas = C.comprehend(root=legacy_root, mode="packet-atlas")
    legacy_status = {
        n["packet_id"]: n["data_status"] for n in legacy_atlas["selected_nodes"]
    }
    assert legacy_status["claim_trace"] == "substantive_with_deferred_edges"
    assert legacy_status["flow"] == "substantive_with_deferred_edges"


def test_claim_trace_and_flow_chooser_when_target_blank(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    for mode in ("claim_trace", "flow"):
        pack = C.comprehend(root=tmp_path, mode=mode, target="")
        assert pack["found"] is False


def test_mutation_plan_organ_is_local_band_and_custody_safe(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    _write_owned_module(tmp_path, "src/microcosm_core/organs/alpha_validator.py")
    pack = C.comprehend(root=tmp_path, mode="mutation_plan", target="alpha_validator")
    assert pack["export_band"] == "local_semantic_excerpt"
    assert pack["mutation_steps"]
    # alpha_validator's loci are custody-bound -> noted, never excerpted.
    assert pack.get("semantic_excerpts", []) == []
    notes = {n["path"] for n in pack.get("excerpt_custody_notes", [])}
    assert "src/microcosm_core/organs/alpha_validator.py" in notes
    # The macro-body warning fires.
    assert any("macro body" in s for s in pack["summary"]["what_to_inspect_next"])


def test_mutation_plan_path_target_excerpts_owned_file(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    _write_owned_module(tmp_path, "src/microcosm_core/widget.py", n_symbols=3)
    pack = C.comprehend(
        root=tmp_path, mode="mutation_plan", target="src/microcosm_core/widget.py"
    )
    assert pack["found"] is True
    assert pack["export_band"] == "local_semantic_excerpt"
    assert pack["semantic_excerpts"][0]["path"] == "src/microcosm_core/widget.py"
    assert pack["semantic_excerpts"][0]["symbols"]


def test_mutation_plan_without_target_returns_ranked_release_improvement_targets(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="mutation_plan")
    assert pack["found"] is True
    assert pack["export_band"] == "local_semantic_excerpt"
    assert pack["selected_nodes"][0]["target"] == "src/microcosm_core/comprehension.py"
    assert "validation_commands" in pack["selected_nodes"][0]
    assert "release approval" in pack["summary"]["what_not_to_trust"]
    body = json.dumps(pack)
    assert "scripts/build_code_lens_join_index.py" in body
    assert all(v is False for v in pack["authority_ceiling"].values())
    # The ranked list stays honest across its own lifecycle: with route/claim
    # topology resolved in the graph, rank 3 advances to the genuinely-remaining
    # proof-graph extraction instead of re-recommending finished work.
    rank3 = next(r for r in pack["selected_nodes"] if r["rank"] == 3)
    assert "proof" in rank3["title"].lower()
    assert rank3["ranking_basis"]["deferred_edge_classes"] == ["proof_internal_structure"]


def test_every_packet_is_stamped_with_identity_and_within_budget(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    _write_owned_module(tmp_path, "src/microcosm_core/widget.py", n_symbols=2)
    targets = {
        "organ_cluster": "import_projection_and_drift",
        "organ": "alpha_validator",
        "claim_trace": "alpha_validator",
        "flow": "alpha_validator",
        "mutation_plan": "src/microcosm_core/widget.py",
        "path": "src/microcosm_core/widget.py",
    }
    for spec in C.PACKET_SPECS:
        mode = spec["mode"]
        kwargs: dict = {"root": tmp_path, "mode": mode}
        if mode == "path":
            kwargs["path"] = targets["path"]
        else:
            kwargs["target"] = targets.get(mode)
        pack = C.comprehend(**kwargs)
        assert pack["packet_id"] == spec["packet_id"]
        assert pack["packet_kind"] == spec["packet_kind"]
        assert pack["next_packets"] == spec["next_packets"]
        assert pack["budget"]["within_budget"] is True


def test_prebuilt_cache_includes_packet_atlas_without_excerpts(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    man = C.build_cached_read_packs(tmp_path)
    names = {p["name"] for p in man["packs"]}
    assert "packet_atlas" in names
    atlas = json.loads(
        (tmp_path / "receipts/code_lens/read_packs/packet_atlas.json").read_text()
    )
    assert atlas["schema_version"] == C.PACKET_ATLAS_SCHEMA
    assert "semantic_excerpts" not in atlas


def test_route_goal_fixtures_land_on_expected_packets_live() -> None:
    """Every cold-agent goal must route to the right packet on the real substrate."""
    bundle = C.load_inputs(C.default_root())
    for goal, expected in C._PACKET_ROUTE_FIXTURES:
        mode, _t, _n = C.route_goal(goal, bundle)
        got = (C._SPEC_BY_MODE.get(mode) or {}).get("packet_id")
        assert got == expected, f"{goal!r} routed to {got}, expected {expected}"


def test_packet_route_assay_is_green_on_live_root() -> None:
    """The atlas must navigate: 100% routing, no overclaim/leak/budget/scent failure."""
    assay = C.run_packet_route_assay(C.default_root())
    assert assay["packet_route_accuracy_pct"] == 100.0
    assert assay["authority_overclaim_count"] == 0
    assert assay["public_excerpt_leak_count"] == 0
    assert assay["budget_violations"] == 0
    assert assay["next_packet_link_coverage_pct"] == 100.0
    assert assay["first_contact_has_scent"] is True
    assert "closed" in assay["sqlite_gate"]


# === Whole-Microcosm Self-Model v0: comprehend the entire substrate at once ========


def test_self_model_operating_picture_has_anchor_health_and_recap(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="self-model")
    assert pack["schema_version"] == C.SELF_MODEL_SCHEMA
    assert pack["context_profile"] == "operating_picture"
    assert pack["export_band"] == "presence_only"
    # Lost-in-the-middle guards: a front anchor and a tail recap must both exist.
    assert pack["read_me_first"] and len(pack["read_me_first"]) >= 3
    assert pack["tail_recap"]["core_frame"]
    assert pack["sections"]
    # Calibration sections present.
    assert pack["code_lens_health"]["by_evidence_class"]
    assert pack["authority_membrane"]["authority_ceiling"]
    assert pack["recommended_drilldowns"]
    assert all(v is False for v in pack["authority_ceiling"].values())


def test_self_model_whole_substrate_map_covers_every_organ(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="self-model", target="whole_substrate_map")
    mapped = sorted(
        o["organ_id"] for fam in pack["whole_substrate_map"] for o in fam["organs"]
    )
    assert mapped == ["alpha_validator", "beta_projection"]
    # Each organ row carries its essence + evidence-class calibration.
    row = pack["whole_substrate_map"][0]["organs"][0]
    assert "essence" in row and "evidence_class" in row and "claim_ceiling" in row


def test_self_model_surfaces_thinness_honestly(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="self-model")
    thin = pack["thin_or_projection_surfaces"]
    # alpha_validator's runner is a directory_coupling_marker (exact-copy macro body).
    assert thin["exact_copy_macro_runners"] == 1
    assert "how_to_probe" in thin
    # The honest deferred edges are always surfaced, never hidden -- and with the v2
    # graph resolved, ONLY the genuinely-missing proof structure remains deferred.
    assert {d["edge_class"] for d in pack["deferred_edges"]} == {"proof_internal_structure"}
    assert pack["graph_backed"]["edge_classes_resolved"] == [
        "claim_node_ontology",
        "cross_organ_route_topology",
    ]


def test_self_model_carries_route_topology_section(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="self-model")
    topo = pack["route_topology"]
    assert topo["route_node_count"] == 1
    assert topo["routes"][0]["task_class"] == "agent-entry"
    assert topo["routes"][0]["primary_organ_id"] == "alpha_validator"
    assert "route_topology" in pack["sections"]
    # Health rollup names the graph shape.
    assert pack["code_lens_health"]["claim_node_count"] == 2
    assert pack["code_lens_health"]["route_node_count"] == 1
    assert pack["code_lens_health"]["edge_kind_counts"]["routes_to"] == 2


def test_self_model_public_reader_is_calibrated_not_promotional(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    pack = C.comprehend(root=tmp_path, mode="self-model", target="public_reader")
    block = pack["public_reader"]
    assert block["what_it_demonstrates"] and block["what_it_does_not_demonstrate"]
    # Calibrated, not promotional: never asserts impressiveness in product-facing copy.
    assert "impressive" not in json.dumps(pack).lower()


def test_self_model_is_presence_only_and_carries_no_excerpts(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    for profile in ("operating_picture", "whole_substrate_map", "public_reader"):
        pack = C.comprehend(root=tmp_path, mode="self-model", target=profile)
        assert pack["export_band"] == "presence_only"
        assert "semantic_excerpts" not in pack
        assert "atom_values" not in json.dumps(pack)


def test_route_goal_routes_whole_system_to_self_model(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    bundle = C.load_inputs(tmp_path)
    for goal in ("comprehend the whole microcosm at once", "show me everything", "self-model"):
        assert C.route_goal(goal, bundle)[0] == "self-model"


def test_self_model_in_prebuilt_cache_and_atlas(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    C.build_cached_read_packs(tmp_path)
    cached = json.loads(
        (tmp_path / "receipts/code_lens/read_packs/self_model.json").read_text()
    )
    assert cached["schema_version"] == C.SELF_MODEL_SCHEMA
    assert "semantic_excerpts" not in cached
    atlas = C.comprehend(root=tmp_path, mode="packet-atlas")
    assert "self_model" in [n["packet_id"] for n in atlas["selected_nodes"]]


def test_whole_system_comprehension_assay_is_green_on_live_root() -> None:
    """A cold reader must comprehend the WHOLE substrate from the self-model alone."""
    assay = C.run_whole_system_comprehension_assay(C.default_root())
    assert assay["whole_system_answerability_pct"] >= 90.0
    assert assay["every_organ_mapped"] is True
    assert assay["organs_mapped"] == assay["organ_total"]
    assert assay["overclaim_count"] == 0
    assert assay["source_body_leaks"] == 0
    assert assay["thinness_surfaced"] is True
    assert assay["deferred_surfaced"] is True
    assert assay["front_anchor_present"] is True
    assert assay["tail_recap_present"] is True
    # v2 graph obligations: route + claim topology are graph-backed on the live
    # substrate, and the ONLY remaining deferred class is proof-internal structure,
    # surfaced as a precise residual (owner + re-entry command), never a vague note.
    assert assay["route_topology_present"] is True
    assert assay["claim_nodes_present"] is True
    assert assay["deferred_edge_classes_remaining"] == ["proof_internal_structure"]
    assert assay["deferred_residuals_are_precise"] is True


def test_live_join_index_resolves_route_and_claim_topology() -> None:
    """The committed join index must carry the v2 graph: typed route/claim/family
    edges covering every organ, so claim_trace and flow answer from the graph."""
    bundle = C.load_inputs(C.default_root())
    state = C._graph_state(bundle)
    assert {"claim_node_ontology", "cross_organ_route_topology"} <= state["resolved"]
    organ_total = len(bundle["join_by_organ"])
    assert len(state["claim_nodes"]) == organ_total
    assert len(state["route_nodes"]) > 0
    # Recompute reachability from the edges themselves -- never trust the rollup
    # label: every organ must be a routes_to target, and no route may point at a
    # phantom organ id.
    routed_targets = {
        e["to"]
        for e in (bundle["join_index"] or {}).get("edges") or []
        if isinstance(e, dict) and e.get("kind") == "routes_to"
    }
    assert routed_targets == set(bundle["join_by_organ"])
    rollup = (bundle["join_index"] or {}).get("rollup") or {}
    assert rollup.get("organs_reachable_from_routes") == organ_total
    assert rollup.get("route_targets_unknown") == 0
    counts = state["graph"]["edge_kind_counts"]
    for kind in (
        "asserts_claim",
        "validated_by",
        "member_of_family",
        "wires_to",
        "routes_to",
        "grounded_in_doctrine",
    ):
        assert counts.get(kind, 0) > 0, f"live graph missing edge kind {kind}"
