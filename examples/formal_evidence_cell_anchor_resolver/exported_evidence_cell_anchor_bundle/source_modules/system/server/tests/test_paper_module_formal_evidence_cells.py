"""Focused tests for the Formal Evidence Cells paper-module audit.

Anchors: mathematics_mission_pipeline.md::Formal Evidence Cells,
std_paper_module.json::formal_evidence_cells, and
cap_quick_paper_module_formal_evidence_cells_contr_07bbd9411ed2.

Scope contract: tests verify the helper directly via ParsedModule fixtures.
This isolates the audit from the heavy paper-module index builder. Integration
through validate_module is covered by the live builder run + the
mathematics_mission_pipeline specimen test below. The standard-alignment test
verifies the runtime constants stay in sync with the standard-owned contract.
"""
from __future__ import annotations

import json
from pathlib import Path

from system.lib.paper_modules import (
    FORMAL_EVIDENCE_ANCHOR_CLASSES,
    FORMAL_EVIDENCE_HIGH_SIGNAL_PHRASES,
    FORMAL_EVIDENCE_MEDIUM_SIGNAL_PHRASES,
    ParsedModule,
    _load_known_formal_evidence_cells,
    audit_formal_evidence_cells,
)


def _module(slug: str, body: str) -> ParsedModule:
    return ParsedModule(
        slug=slug,
        title=slug.replace("_", " ").title(),
        file=Path(f"codex/doctrine/paper_modules/{slug}.md"),
        frontmatter={},
        sections={},
        section_order=[],
        raw_text=body,
    )


def test_compliant_cell_emits_info() -> None:
    body = """# Compliant
This module mentions Lean-proved theorems with a clear `claim_boundary`
qualifier; the proof attempt links a `receipt_ref` and binds to
cap_quick_test_abc123 work item.
"""
    findings = audit_formal_evidence_cells(_module("test_compliant", body))
    assert len(findings) == 1
    assert findings[0].rule == "formal_evidence_cell_present"
    assert findings[0].severity == "info"


def test_missing_one_anchor_emits_warning() -> None:
    body = """# Partial
This module discusses no-sorry status with a clear `claim_boundary` and a
`receipt_ref`, but provides no work-item / cap anchor.
"""
    findings = audit_formal_evidence_cells(_module("test_missing_one", body))
    assert len(findings) == 1
    assert findings[0].rule == "formal_evidence_cell_missing_anchor"
    assert findings[0].severity == "warning"
    assert "work_item" in findings[0].message


def test_missing_two_anchors_emits_warning() -> None:
    body = """# Partial2
This module says no-sorry and claim_boundary but provides neither receipts
nor any cap anchor.
"""
    findings = audit_formal_evidence_cells(_module("test_missing_two", body))
    assert len(findings) == 1
    assert findings[0].rule == "formal_evidence_cell_missing_anchor"
    assert findings[0].severity == "warning"
    assert "receipt" in findings[0].message
    assert "work_item" in findings[0].message


def test_overclaim_emits_error_with_explicit_rule() -> None:
    """Severity ratched from warning to error on 2026-05-17 after the surfaced
    corpus drift was remediated. Per std_paper_module::formal_evidence_cells.
    """
    body = """# Overclaim
This module asserts no-sorry, sorryAx-free, and formally proved results
without any boundary, receipt, or work-item anchor anywhere in the body.
"""
    findings = audit_formal_evidence_cells(_module("test_overclaim", body))
    assert len(findings) == 1
    assert findings[0].rule == "formal_evidence_overclaim"
    assert findings[0].severity == "error"
    assert "mathematics_mission_pipeline" in findings[0].message
    assert "std_paper_module" in findings[0].message


def test_no_formal_vocab_no_finding() -> None:
    body = """# Navigation
This module discusses navigation grammar and coverage-first routing only.
"""
    findings = audit_formal_evidence_cells(_module("test_no_vocab", body))
    assert findings == []


def test_bare_proof_metaphor_does_not_trigger() -> None:
    """`proof surface`, `proof of concept` are metaphor; should not fire."""
    body = """# Dissemination
The website-card axiom is the public-projection reflex of the proof surface.
Dissemination is a proof of concept, not a theorem. The bare word Lean appears
here only as a directional reference, not as a proof claim.
"""
    findings = audit_formal_evidence_cells(_module("test_proof_metaphor", body))
    assert findings == []


def test_medium_signal_only_no_overclaim_promotion() -> None:
    """Medium-signal vocab (mathlib alone) without anchors should NOT escalate
    to ``formal_evidence_overclaim`` (which requires high-signal phrasing).
    It still warns as ``formal_evidence_cell_missing_anchor``.
    """
    body = """# Medium
This module mentions mathlib as a dependency context but provides no
claim_boundary, no receipt, and no work item anchor.
"""
    findings = audit_formal_evidence_cells(_module("test_medium", body))
    assert len(findings) == 1
    assert findings[0].rule == "formal_evidence_cell_missing_anchor"
    assert findings[0].severity == "warning"


def test_mathematics_mission_pipeline_specimen_passes() -> None:
    """The repo's live mathematics_mission_pipeline.md is the first compliant
    specimen for this contract (per its 2026-05-17 Formal Evidence Cells
    addendum + the cross-link paragraph that cites example cell_ids). It MUST
    emit ``formal_evidence_cell_present`` at info severity, MAY also emit
    ``formal_evidence_cell_id_present`` because the cross-link paragraph
    cites real cell_ids, and MUST NOT emit any warning/error finding from
    this rule family.
    """
    repo_root = Path(__file__).resolve().parents[3]
    md_path = (
        repo_root
        / "codex/doctrine/paper_modules/mathematics_mission_pipeline.md"
    )
    body = md_path.read_text(encoding="utf-8")
    findings = audit_formal_evidence_cells(
        _module("mathematics_mission_pipeline", body)
    )
    rule_severities = {(f.rule, f.severity) for f in findings}
    assert ("formal_evidence_cell_present", "info") in rule_severities, (
        f"Expected formal_evidence_cell_present (info); got {rule_severities}"
    )
    for rule, severity in rule_severities:
        assert severity == "info", (
            f"specimen must not emit warnings/errors from formal-evidence rule "
            f"family; got ({rule}, {severity})"
        )


def test_runtime_vocab_matches_standard() -> None:
    """The runtime FORMAL_EVIDENCE_* constants must stay in sync with the
    standard-owned contract in codex/standards/std_paper_module.json under
    `formal_evidence_cells`. Drift here is a silent ownership split between
    code and standard.
    """
    repo_root = Path(__file__).resolve().parents[3]
    standard_path = repo_root / "codex/standards/std_paper_module.json"
    standard = json.loads(standard_path.read_text(encoding="utf-8"))

    contract = standard.get("formal_evidence_cells")
    assert contract is not None, (
        "std_paper_module.json is missing the formal_evidence_cells contract "
        "section. The runtime audit references this section as authority."
    )

    signal_classes = contract.get("signal_classes", {})
    assert tuple(signal_classes.get("high_signal", [])) == (
        FORMAL_EVIDENCE_HIGH_SIGNAL_PHRASES
    ), (
        "Runtime FORMAL_EVIDENCE_HIGH_SIGNAL_PHRASES drifted from "
        "std_paper_module::formal_evidence_cells.signal_classes.high_signal."
    )
    assert tuple(signal_classes.get("medium_signal", [])) == (
        FORMAL_EVIDENCE_MEDIUM_SIGNAL_PHRASES
    ), (
        "Runtime FORMAL_EVIDENCE_MEDIUM_SIGNAL_PHRASES drifted from "
        "std_paper_module::formal_evidence_cells.signal_classes.medium_signal."
    )

    anchor_classes = contract.get("required_anchor_classes", {})
    assert set(anchor_classes.keys()) == set(FORMAL_EVIDENCE_ANCHOR_CLASSES.keys()), (
        f"Runtime anchor-class names {sorted(FORMAL_EVIDENCE_ANCHOR_CLASSES.keys())} "
        f"drifted from standard {sorted(anchor_classes.keys())}."
    )
    for name, runtime_vocab in FORMAL_EVIDENCE_ANCHOR_CLASSES.items():
        standard_vocab = tuple(anchor_classes.get(name, []))
        assert tuple(runtime_vocab) == standard_vocab, (
            f"Runtime anchor class '{name}' vocabulary {list(runtime_vocab)} "
            f"drifted from standard {list(standard_vocab)}."
        )

    overclaim_spec = contract.get("classifications", {}).get(
        "formal_evidence_overclaim", {}
    )
    assert overclaim_spec.get("severity_current_slice") == "error", (
        "After the 2026-05-17 ratchet, the standard must declare "
        "formal_evidence_overclaim severity_current_slice == 'error'."
    )

    assert contract.get("known_manifests"), (
        "std_paper_module::formal_evidence_cells.known_manifests must list "
        "at least one manifest for the cell-id resolver to dereference."
    )


def test_cell_id_citation_satisfies_anchors_without_prose() -> None:
    """A module that cites only a valid cell_id (no claim_boundary / receipt /
    work_item prose) should pass as formal_evidence_cell_present. This is the
    contract std_paper_module::formal_evidence_cells.preferred_anchor_form_cell_id_citation
    promises and the runtime resolver makes executable.
    """
    cell_id = "erdos257.issue217.period_noncollapse.selector_interface_kernel"
    known = {
        cell_id: {
            "cell_id": cell_id,
            "claim_boundary": "finite_period_noncollapse_strike_not_erdos257_solution",
            "receipt_refs": [
                "state/formal_math_research_operations/pilots/erdos257_issue217/period_noncollapse_strike_receipt.json"
            ],
            "work_item_id": "cap_quick_mathematics_oracle_prover_evolve_lane_er_8264150e650a",
        }
    }
    body = f"""# CitedOnly
This module discusses no-sorry status by citing {cell_id} as the sole
formal-evidence anchor; no claim/receipt/work-item prose is repeated.
"""
    findings = audit_formal_evidence_cells(
        _module("test_cell_id_only", body), known_cells=known
    )
    rules = {f.rule for f in findings}
    assert "formal_evidence_cell_id_present" in rules, (
        f"expected resolver-present finding; got {rules}"
    )
    assert "formal_evidence_cell_present" in rules, (
        f"expected anchor-class compliance via resolved cell; got {rules}"
    )
    assert "formal_evidence_cell_missing_anchor" not in rules
    assert "formal_evidence_overclaim" not in rules


def test_unknown_cell_id_warns_and_does_not_satisfy() -> None:
    """A module that cites a dotted id not in any known manifest must emit
    formal_evidence_cell_id_unknown AND remain non-compliant for anchors.
    """
    body = """# Unknown
The proof claim invokes no-sorry and references
erdos999.fake.cell.unknown as its only evidence anchor.
"""
    findings = audit_formal_evidence_cells(
        _module("test_unknown_cell_id", body), known_cells={}
    )
    rules = {f.rule for f in findings}
    assert "formal_evidence_cell_id_unknown" in rules
    # No anchors at all + high-signal vocab -> still overclaim
    assert "formal_evidence_overclaim" in rules
    for f in findings:
        if f.rule == "formal_evidence_cell_id_unknown":
            assert f.severity == "warning"
        if f.rule == "formal_evidence_overclaim":
            assert f.severity == "error"


def test_missing_source_cell_does_not_supply_anchors() -> None:
    """A resolved cell whose status is ``missing_source`` MUST NOT count as
    an anchor supplier and MUST emit formal_evidence_cell_id_missing_source
    (error severity).
    """
    cell_id = "erdos257.issue217.period_noncollapse.selector_interface_kernel"
    known = {
        cell_id: {
            "cell_id": cell_id,
            "status": "missing_source",
            "claim_boundary": "x",
            "receipt_refs": ["x"],
            "work_item_id": "x",
        }
    }
    body = f"""# Degraded
The proof claim invokes no-sorry and cites {cell_id}.
"""
    findings = audit_formal_evidence_cells(
        _module("test_missing_source_cell", body), known_cells=known
    )
    rules_severities = {(f.rule, f.severity) for f in findings}
    assert ("formal_evidence_cell_id_missing_source", "error") in rules_severities
    # The missing-source cell did NOT supply anchors, so still overclaim
    assert any(r == "formal_evidence_overclaim" for r, _ in rules_severities)


def test_incomplete_cell_warns_and_supplies_only_present_anchors() -> None:
    """A resolved cell missing one anchor class supplies only the classes it
    carries; the module surfaces formal_evidence_cell_id_incomplete (warning)
    and may still need explicit prose for the missing anchor class.
    """
    cell_id = "erdos257.issue217.partial.cell"
    known = {
        cell_id: {
            "cell_id": cell_id,
            "claim_boundary": "partial_boundary",
            "receipt_refs": ["x.json"],
            # Missing work_item_id intentionally
        }
    }
    body = f"""# Partial
This module cites {cell_id} alongside no-sorry vocabulary; the cell carries
boundary and receipt but no work_item, so the module needs an additional
work_item anchor (e.g. cap_quick_example) or must downgrade the language.
"""
    findings = audit_formal_evidence_cells(
        _module("test_incomplete_cell", body), known_cells=known
    )
    rules = {f.rule for f in findings}
    assert "formal_evidence_cell_id_incomplete" in rules
    # The body adds cap_quick_example so work_item is also present via prose,
    # therefore overall compliance is formal_evidence_cell_present.
    assert "formal_evidence_cell_present" in rules
    incomplete = [f for f in findings if f.rule == "formal_evidence_cell_id_incomplete"][0]
    assert "work_item" in incomplete.message


def test_live_known_manifest_loads_six_cells() -> None:
    """``_load_known_formal_evidence_cells`` should resolve the live Erdős257
    manifest and surface all six v0 cell ids.
    """
    cells = _load_known_formal_evidence_cells()
    assert len(cells) >= 6, (
        f"expected >=6 known cells from the live manifest registry, got "
        f"{len(cells)}: {sorted(cells)}"
    )
    expected_prefix = "erdos257.issue217."
    assert any(cid.startswith(expected_prefix) for cid in cells), (
        f"no Erdős257 pilot cell_ids loaded: {sorted(cells)}"
    )
