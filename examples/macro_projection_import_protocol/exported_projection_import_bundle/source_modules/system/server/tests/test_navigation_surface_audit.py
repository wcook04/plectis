"""Regression coverage for navigation-surface contract diagnostics."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.navigation_surface_audit import (
    build_navigation_surface_audit,
    build_navigation_surface_audit_catalog,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_bounded_entry_routes_use_subject_budget_not_caller_budget() -> None:
    """Regression: bounded_entry routes must measure their contract against
    the subject packet's intended ~12000-token budget, NOT the caller's
    `context_budget`. Pre-fix, calling with the kernel CLI default
    --context-budget=1400 (a metabolism-ledger trim target) caused
    phase.summary_default and other ~12k-byte bounded_entry routes to
    falsely report `violates_entry_contract` because their budget was 5,600
    bytes instead of 48,000. This is a caller-trim-budget vs subject-packet-budget
    category error: the caller's small budget is intended for the *caller's
    own packet*, not for the subject route's contract.
    """
    from system.lib.navigation_surface_audit import BOUNDED_ENTRY_PACKET_BUDGET_TOKENS

    small = build_navigation_surface_audit(REPO_ROOT, context_budget=1400)
    routes_small = {row["route_id"]: row for row in small["route_map"]}
    bounded_entry_violations = [
        row for row in small["route_map"]
        if row.get("contract_expectation") == "bounded_entry"
        and row.get("contract_status") == "violates_entry_contract"
    ]
    assert bounded_entry_violations == [], (
        f"bounded_entry routes falsely violating with caller context_budget=1400: "
        f"{[r['route_id'] for r in bounded_entry_violations]}"
    )
    assert routes_small["phase.summary_default"]["contract_status"] == "valid"
    assert routes_small["phase.summary_default"]["budget_relation"] in {
        "within_budget",
        "large_but_within_budget",
    }
    # Library-only unsafe references and contents-page routes are unaffected.
    assert routes_small["paper_modules.row_flag_all.library"]["contract_status"] == "violates_entry_contract"

    large = build_navigation_surface_audit(REPO_ROOT, context_budget=12000)
    routes_large = {row["route_id"]: row for row in large["route_map"]}
    # Bounded-entry routes should report identical contract status across budgets,
    # because their effective budget is fixed at BOUNDED_ENTRY_PACKET_BUDGET_TOKENS*4.
    for route_id in (
        "phase.summary_default",
        "paper_modules.row_flag_one",
        "paper_module.output_band_flag_browse",
    ):
        assert routes_small[route_id]["contract_status"] == routes_large[route_id]["contract_status"], (
            f"bounded_entry route {route_id} differs across caller budgets — caller budget is leaking"
        )

    # Sanity: BOUNDED_ENTRY_PACKET_BUDGET_TOKENS is the documented constant.
    assert BOUNDED_ENTRY_PACKET_BUDGET_TOKENS == 12000


def test_navigation_surface_audit_separates_size_measurement_from_contract_status() -> None:
    payload = build_navigation_surface_audit(
        REPO_ROOT,
        query="navigation context compression",
        context_budget=12000,
    )

    assert payload["kind"] == "navigation_surface_audit"
    assert "contract_status decides" in payload["budget"]["classification"]
    assert payload["summary"]["missing_cluster_adapter_count"] == 0

    routes = {row["route_id"]: row for row in payload["route_map"]}
    assert routes["paper_modules.row_flag_all.library"]["budget_relation"] == "exceeds_context_budget"

    # known_unsafe_reference routes (the *.row_flag_all.library variants) must
    # always violate contract; the CLI redirects callers to cluster_flag.
    library_routes = (
        "paper_modules.row_flag_all.library",
        "standards.row_flag_all.library",
        "task_ledger.row_flag_all.library",
        "skills.row_flag_all.library",
        "python_files.row_flag_all.library",
        "python_scopes.row_flag_all.library",
        "frontend_components.row_flag_all.library",
        "principles.row_flag_all.library",
        "annex_patterns.row_flag_all.library",
        "annex_distillation_patterns.row_flag_all.library",
        "row_patches.row_flag_all.library",
        "transform_job_receipts.row_flag_all.library",
    )
    for route_id in library_routes:
        assert routes[route_id]["contract_status"] == "violates_entry_contract", (
            f"library reference {route_id} should violate contract"
        )

    # cluster_flag routes are contents_page-style: they should never
    # violate_entry_contract, but they MAY exceed the caller's budget under live
    # data growth (status `contents_page_too_large` is a non-violation
    # size-derived signal, not a contract failure). The test name
    # "separates_size_measurement_from_contract_status" encodes exactly this:
    # size is one axis, contract is another. Per iter 8 of autonomous bug sweep,
    # task_ledger.cluster_flag genuinely exceeds the 48,000-byte budget under
    # live data. Allow the non-violation contents_page_too_large status here
    # rather than papering over the real bloat finding with a strict `valid`.
    cluster_flag_routes = (
        "paper_modules.cluster_flag",
        "standards.cluster_flag",
        "task_ledger.cluster_flag",
        "skills.cluster_flag",
        "python_files.cluster_flag",
        "python_scopes.cluster_flag",
        "frontend_components.cluster_flag",
        "principles.cluster_flag",
        "annex_patterns.cluster_flag",
        "annex_distillation_patterns.cluster_flag",
        "row_patches.cluster_flag",
        "transform_job_receipts.cluster_flag",
        "compliance_ledger.cluster_flag",
    )
    cluster_flag_non_violation_statuses = {"valid", "contents_page_too_large"}
    for route_id in cluster_flag_routes:
        status = routes[route_id]["contract_status"]
        assert status in cluster_flag_non_violation_statuses, (
            f"cluster_flag route {route_id} contract_status={status!r} is a "
            f"violation; cluster_flag must never violate the entry contract"
        )
        # Hard-line: cluster_flag must NEVER report violates_entry_contract.
        # That status is reserved for known_unsafe_reference.
        assert status != "violates_entry_contract", (
            f"cluster_flag {route_id} is reporting bounded_entry violation; "
            f"only known_unsafe_reference routes may violate contract"
        )
    assert routes["paper_modules.cluster_flag"]["contract_status"] == "valid"
    assert routes["paper_modules.cluster_flag"]["budget_relation"] != "exceeds_context_budget"

    assert routes["phase.summary_default"]["contract_expectation"] == "bounded_entry"

    high_card = {row["kind_id"]: row for row in payload["high_cardinality_kinds"]}
    assert high_card["paper_modules"]["cluster_adapter_status"] == "implemented"
    assert high_card["standards"]["cluster_adapter_status"] == "implemented"
    assert high_card["task_ledger"]["cluster_adapter_status"] == "implemented"
    assert high_card["skills"]["cluster_adapter_status"] == "implemented"
    assert high_card["python_files"]["cluster_adapter_status"] == "implemented"
    assert high_card["python_scopes"]["cluster_adapter_status"] == "implemented"
    assert high_card["frontend_components"]["cluster_adapter_status"] == "implemented"
    assert high_card["principles"]["cluster_adapter_status"] == "implemented"
    assert high_card["annex_patterns"]["cluster_adapter_status"] == "implemented"
    assert high_card["annex_distillation_patterns"]["cluster_adapter_status"] == "implemented"
    assert high_card["transform_job_receipts"]["cluster_adapter_status"] == "implemented"
    assert high_card["row_patches"]["cluster_adapter_status"] == "implemented"
    assert routes["compliance_ledger.cluster_flag"]["contract_status"] == "valid"
    missing_cluster = {
        row["kind_id"]
        for row in payload["high_cardinality_kinds"]
        if row["cluster_adapter_status"] == "missing"
    }
    assert missing_cluster == set()
    assert "skills_all_flag_over_budget" in {finding["finding_id"] for finding in payload["findings"]}
    assert "python_scopes_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }
    assert "annex_distillation_patterns_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }
    assert "standards_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }
    assert "frontend_components_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }
    assert "principles_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }
    assert "annex_patterns_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }
    assert "row_patches_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }
    assert "transform_job_receipts_cluster_flag_compresses_global_overview" in {
        finding["finding_id"] for finding in payload["findings"]
    }


def test_navigation_surface_audit_cli_emits_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--navigation-surface-audit",
            "navigation context compression",
            "--context-budget",
            "12000",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "navigation_surface_audit"
    assert payload["measurement_mode"] == "contract_catalog"
    assert payload["summary"]["contract_violation_count"] >= 2
    assert payload["full_measurement_command"].startswith("./repo-python kernel.py --full")


def test_navigation_surface_audit_catalog_names_full_drilldown() -> None:
    payload = build_navigation_surface_audit_catalog(
        REPO_ROOT,
        query="navigation context compression",
        context_budget=12000,
    )

    assert payload["measurement_mode"] == "contract_catalog"
    assert payload["summary"]["omitted_live_measurement_count"] >= 1
    skills = {
        row["route_id"]: row
        for row in payload["route_map"]
    }["skills.row_flag_all.library"]
    assert skills["contract_status"] == "violates_entry_contract"
    assert skills["safe_alternative"].endswith("--option-surface skills --band cluster_flag")
    assert "--full --navigation-surface-audit" in skills["full_audit_drilldown"]
