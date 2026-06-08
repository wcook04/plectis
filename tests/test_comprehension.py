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


def _write_fixture(root: Path, *, leaky: bool = False) -> None:
    """Write a minimal substrate root (atlas + synopses + join index) for tests."""
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
        "schema_version": "microcosm_code_lens_join_index_v0",
        "export_band": "presence_only",
        "source_bodies_exported": bool(leaky),
        "nodes": {
            "organ": [
                {
                    "organ_id": "alpha_validator",
                    "evidence_class": "semantic_validator",
                    "claim_ceiling": "validates_public_contract",
                    "status": "accepted",
                    "runner_module": "microcosm_core.organs.alpha_validator",
                    "runner_source_ref": "src/microcosm_core/organs/alpha_validator.py",
                    "runner_source_resolved": True,
                    "runner_custody_basis": "directory_coupling_marker",
                    "runner_specificity": {"real_coverage": 5, "body_specific": 4, "generic_unique": 1},
                    "authority_receipt": "receipts/first_wave/alpha_validator/acceptance.json",
                },
                {
                    "organ_id": "beta_projection",
                    "evidence_class": "algorithmic_projection",
                    "claim_ceiling": "projects_drift",
                    "status": "accepted",
                    "runner_module": "microcosm_core.beta_projection",
                    "runner_source_ref": "src/microcosm_core/beta_projection.py",
                    "runner_source_resolved": True,
                    "runner_custody_basis": "owned",
                    "runner_specificity": {"real_coverage": 3, "body_specific": 3, "generic_unique": 0},
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


def test_goal_routes_to_organ_authority_and_deferred_slice(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    bundle = C.load_inputs(tmp_path)
    assert C.route_goal("tell me about alpha_validator", bundle)[:2] == ("organ", "alpha_validator")
    assert C.route_goal("what am I allowed to trust", bundle)[0] == "authority"
    mode, _organ, note = C.route_goal("show me all the math proofs", bundle)
    assert mode == "first-contact" and note and "deferred" in note


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


def test_cache_build_writes_three_packs(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    manifest = C.build_cached_read_packs(tmp_path)
    names = {p["name"] for p in manifest["packs"]}
    assert names == {"first_contact", "authority", "organs_index"}
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
