from __future__ import annotations

import json
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent


def _std_microcosm() -> dict:
    return json.loads(
        (REPO_ROOT / "codex/standards/std_microcosm.json").read_text(
            encoding="utf-8"
        )
    )


def test_microcosm_paper_module_coverage_contract_is_standard_backed() -> None:
    standard = _std_microcosm()
    contract = standard["paper_module_coverage_contract"]

    assert contract["primary_modules"] == [
        "codex/doctrine/paper_modules/microcosm_substrate.md",
        "codex/doctrine/paper_modules/microcosm_entry_lattice.md",
        "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md",
        "codex/doctrine/paper_modules/idea_microcosm_metabolism.md",
        "codex/doctrine/paper_modules/public_constellation_strategy.md",
        "codex/doctrine/paper_modules/dissemination_strategy.md",
    ]
    assert contract["required_projection_surfaces"] == [
        "codex/doctrine/paper_modules/_index.json",
        "codex/doctrine/paper_modules/_validation_report.json",
        "codex/doctrine/paper_modules/_route_coverage.json",
        "codex/doctrine/paper_modules/README.md",
    ]
    assert contract["atlas_option_surfaces"] == [
        "paper_modules",
        "standards",
        "microcosm_extracted_patterns",
        "system_microcosm",
        "axiom_candidates",
    ]
    assert contract["healthy_state_receipt"] == {
        "module_status": "all_authored_modules_up_to_date",
        "queue_status": "refresh_split_first_author_deprecate_queues_zero",
        "fact_audit_status": "paper_module_fact_audit_findings_zero",
    }
    assert contract["depth_order"] == [
        "entry_packet_selects_microcosm_public_substrate",
        "behavior_first_screen_visible",
        "microcosm_substrate_product_roof",
        "microcosm_entry_lattice_route_depth",
        "paper_module_coverage_metabolism_corpus_health",
        "selected_module_card_then_source_evidence",
    ]
    assert contract["authority_ceiling"] == (
        "coverage_navigation_only_not_public_release_source_truth_proof_or_"
        "candidate_axiom_authority"
    )

    rule = next(
        rule
        for rule in standard["validation_rules"]
        if rule["id"] == "microcosm_paper_module_coverage_contract"
    )
    assert rule["source_ref"] == (
        "codex/standards/std_microcosm.json::paper_module_coverage_contract"
    )
    assert rule["projection_ref"] == (
        "codex/doctrine/paper_modules/microcosm_entry_lattice.md::"
        "paper_module_coverage_contract"
    )
    assert rule["fields"] == [
        "primary_modules",
        "required_projection_surfaces",
        "atlas_option_surfaces",
        "healthy_state_receipt",
        "depth_order",
        "authority_ceiling",
    ]


def test_microcosm_paper_module_coverage_contract_is_projected_into_modules() -> None:
    entry_lattice = (
        REPO_ROOT / "codex/doctrine/paper_modules/microcosm_entry_lattice.md"
    ).read_text(encoding="utf-8")
    product_roof = (
        REPO_ROOT / "codex/doctrine/paper_modules/microcosm_substrate.md"
    ).read_text(encoding="utf-8")

    for required in [
        "std_microcosm.json::paper_module_coverage_contract",
        "paper_module_coverage_metabolism",
        "generated sidecars",
        "all authored modules up to date",
        "refresh/split/first-author/deprecate queues at zero",
    ]:
        assert required in entry_lattice

    assert "Verify paper-module coverage/depth" in entry_lattice
    assert "Verify paper-module coverage without bloating this roof" in product_roof
    assert "sidecars as source truth" in product_roof
