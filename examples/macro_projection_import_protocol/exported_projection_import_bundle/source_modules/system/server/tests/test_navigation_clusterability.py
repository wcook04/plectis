"""Regression coverage for high-cardinality clusterability decisions."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.navigation_clusterability import build_navigation_clusterability_audit


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_clusterability_audit_classifies_remaining_high_cardinality_kinds() -> None:
    payload = build_navigation_clusterability_audit(REPO_ROOT, context_budget=12000)

    assert payload["kind"] == "navigation_clusterability_audit"
    assert payload["summary"]["high_cardinality_kind_count"] >= 9
    assert payload["summary"]["implemented_count"] >= 9
    assert payload["summary"]["safe_now_count"] == 0
    assert payload["summary"]["blocked_count"] == 0
    assert payload["summary"]["missing_cluster_adapter_count"] == 0
    assert payload["summary"]["debt_count"] == 0

    rows = {row["kind_id"]: row for row in payload["rows"]}
    assert rows["standards"]["cluster_flag_status"] == "implemented"
    assert rows["python_files"]["cluster_flag_status"] == "implemented"
    assert rows["python_scopes"]["cluster_flag_status"] == "implemented"
    assert rows["frontend_components"]["cluster_flag_status"] == "implemented"
    assert rows["principles"]["cluster_flag_status"] == "implemented"
    assert rows["annex_patterns"]["cluster_flag_status"] == "implemented"
    assert rows["annex_distillation_patterns"]["cluster_flag_status"] == "implemented"
    assert rows["standards"]["grouping_keys_available"] == ["group"]
    assert rows["standards"]["grouping_key_provenance"] == "implemented_adapter"
    assert rows["annex_patterns"]["cluster_flag_budget_relation"] in {"within_budget", "large_but_within_budget"}
    assert rows["annex_patterns"]["grouping_keys_available"] == [
        "annex_pattern_cluster_key",
        "annex_catalog.routing_summary.problem_spaces[0]",
    ]
    assert rows["derived_facts"]["cluster_flag_status"] == "implemented"
    assert rows["derived_facts"]["repair_class"] == "not_needed"
    if "standard_skill_map" in rows:
        assert rows["standard_skill_map"]["cluster_flag_status"] == "implemented"
        assert rows["standard_skill_map"]["grouping_keys_available"] == ["pairing_status"]
        assert rows["standard_skill_map"]["repair_class"] == "not_needed"
    assert rows["skill_compression_debt"]["cluster_flag_status"] == "implemented"
    assert rows["skill_compression_debt"]["repair_class"] == "not_needed"
    assert rows["row_patches"]["cluster_flag_status"] == "implemented"
    assert rows["row_patches"]["grouping_keys_available"] == ["target_facet"]
    assert rows["row_patches"]["repair_class"] == "not_needed"
    assert rows["transform_job_receipts"]["cluster_flag_status"] == "implemented"
    assert rows["transform_job_receipts"]["grouping_keys_available"] == ["task_class"]
    assert rows["transform_job_receipts"]["repair_class"] == "not_needed"

    debt = {row["debt_id"]: row for row in payload["debt_rows"]}
    assert "clusterability:standards" not in debt
    assert "clusterability:annex_patterns" not in debt
    assert "clusterability:derived_facts" not in debt
    assert "clusterability:standard_skill_map" not in debt
    assert "clusterability:row_patches" not in debt
    assert "clusterability:transform_job_receipts" not in debt


def test_clusterability_quick_profile_defers_measuring_implemented_cluster_payloads() -> None:
    payload = build_navigation_clusterability_audit(
        REPO_ROOT,
        context_budget=12000,
        measure_all_rows=False,
    )

    assert payload["summary"]["debt_count"] == 0
    rows = {row["kind_id"]: row for row in payload["rows"]}
    assert rows["standards"]["cluster_flag_status"] == "implemented_unmeasured"
    assert rows["standards"]["cluster_flag_budget_relation"] == "deferred_by_quick_profile"
    assert rows["standards"]["repair_class"] == "not_needed"


def test_clusterability_audit_cli_emits_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--clusterability-audit",
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
    assert payload["kind"] == "navigation_clusterability_audit"
    assert payload["output_profile"] == "clusterability_no_debt_cli_compact_v0"
    assert payload["summary"]["missing_cluster_adapter_count"] == 0
    assert payload["summary"]["rows_omitted_count"] >= 1
    assert payload["rows"] == []
    assert payload["row_budget_pressure_preview"]
    assert payload["omission_receipt"]["full_evidence_command"].endswith("--context-budget 40000")
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "clusterability:standard_skill_map" not in debt_ids
    assert "clusterability:transform_job_receipts" not in debt_ids
    assert "clusterability:row_patches" not in debt_ids
