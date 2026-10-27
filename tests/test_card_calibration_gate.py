"""Bind public one-line descriptions to their canonical source and evidence.

The projection overclaim guard remains separate. Real execution is disclosed
through the canonical mechanism card, its resolved runner locus, evidence
classification and scope ceiling; a list of approved verbs cannot establish
that relationship. Synopsis budgets are the deployed 100/108/120 contract.
Refine capsule compression at its source, then regenerate the compatibility
synopses through the atlas owner. These checks do not execute a component or
turn a saved evidence classification into a fresh result.
"""
from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.component_descriptions import load_description_atlas, resolve_component_capsules

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

PROJECTION_ONLY = {"algorithmic_projection"}
REAL_EXECUTION = {"bounded_runtime_computation", "external_subprocess_witness"}

# Verbs that assert a real runtime action a projection-only organ cannot perform.
OVERCLAIM_VERBS = ("recomputes", "authorizes", "proves", "compiles")
# Markers that defuse an overclaim verb by scoping it to recorded/synthetic data.
QUALIFIERS = (
    "recorded", "declared", "synthetic", "replay", "fixture",
    "copied", "make-believe", "stated", "projection",
)


def _load() -> tuple[dict[str, str], dict[str, dict]]:
    syn = json.loads((CORE / "component_public_synopses.json").read_text())["synopses"]
    reg = {
        row["organ_id"]: row
        for row in json.loads((CORE / "organ_registry.json").read_text())["implemented_organs"]
    }
    return syn, reg


def test_projection_one_lines_make_no_unqualified_execution_claim() -> None:
    """OVERSELL guard: projection-only cards must not claim live execution."""
    syn, reg = _load()
    violations = []
    for organ_id, line in syn.items():
        if reg.get(organ_id, {}).get("evidence_class") not in PROJECTION_ONLY:
            continue
        low = line.lower()
        hits = [verb for verb in OVERCLAIM_VERBS if verb in low]
        if hits and not any(q in low for q in QUALIFIERS):
            violations.append(f"  {organ_id} {hits}: {line}")
    assert not violations, (
        "algorithmic_projection one-lines assert unqualified real-runtime verbs; "
        "add a qualifier (recorded/synthetic/...) or soften the verb:\n"
        + "\n".join(violations)
    )


def test_real_execution_one_lines_signal_the_real_work() -> None:
    """Check canonical mechanism/evidence fidelity, not an editorial verb list."""
    synopsis_doc = json.loads((CORE / "component_public_synopses.json").read_text())
    syn, reg = _load()
    atlas_doc = json.loads((CORE / "organ_atlas.json").read_text())
    capsule_doc = json.loads((CORE / "paper_module_capsules.json").read_text())
    resolved = resolve_component_capsules(atlas_doc["organs"], capsule_doc["paper_modules"])
    public_by_id = {row["organ_id"]: row for row in load_description_atlas(ROOT)["organs"]}
    evidence = json.loads((CORE / "organ_evidence_classes.json").read_text())
    evidence_by_id = {row["organ_id"]: row for row in evidence["organ_evidence_classes"]}

    assert set(syn) == set(reg) == set(public_by_id) == set(resolved)
    assert synopsis_doc["generation"]["method"] == "canonical_capsule_synopsis"
    assert synopsis_doc["source_ref"] == "core/paper_module_capsules.json::paper_modules[].compression.one_line"
    budget = synopsis_doc["budget"]
    assert (budget["target_max_chars"], budget["warn_over_chars"], budget["hard_ceiling_chars"]) == (100, 108, 120)
    assert all(0 < len(line) <= budget["hard_ceiling_chars"] for line in syn.values())
    real_ids = {oid for oid, row in reg.items() if row["evidence_class"] in REAL_EXECUTION}
    assert {reg[oid]["evidence_class"] for oid in real_ids} == REAL_EXECUTION
    for oid in sorted(real_ids):
        capsule = resolved[oid][0]
        compression = capsule["compression"]
        public = public_by_id[oid]
        row = reg[oid]
        evidence_row = evidence_by_id[oid]
        profile = evidence["class_profiles"][row["evidence_class"]]
        assert syn[oid] == compression["one_line"] == public["one_line"], oid
        assert public["agent_gloss"] == compression["card"] and compression["card"].strip(), oid
        assert public["claim_ceiling_restated"] == compression["authority_ceiling"], oid
        assert compression["authority_ceiling"].strip(), oid
        assert row["evidence_class"] == evidence_row["evidence_class"], oid
        assert row["classification_basis"] == evidence_row["classification_basis"], oid
        assert row["classification_basis"].strip(), oid
        assert row["evidence_strength_rank"] == profile["evidence_strength_rank"], oid
        assert row["truth_accounting_bucket"] == profile["truth_accounting_bucket"] == "real_runtime_receipt", oid
        # A canonical description must retain a concrete source route to the
        # declared engine/witness. This is source availability, not execution.
        runner_ref = "src/" + row["runner"].replace(".", "/") + ".py"
        assert (ROOT / runner_ref).is_file(), (oid, runner_ref)
        assert any(locus.get("path") == runner_ref and locus.get("resolution") == "resolved"
                   and locus.get("symbols") for locus in capsule["code_loci"]), oid
