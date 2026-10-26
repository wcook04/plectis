"""Regression coverage for annex_patterns routing-key quality."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.annex_routing_coverage import build_annex_routing_coverage


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_annex_routing_coverage_reports_unrouted_bucket() -> None:
    payload = build_annex_routing_coverage(REPO_ROOT, context_budget=12000)

    assert payload["kind"] == "annex_routing_coverage"
    assert payload["summary"]["total_annex_pattern_rows"] > 0
    assert payload["summary"]["unrouted_rows"] > 0
    assert payload["summary"]["unrouted_rate"] <= payload["budget"]["unrouted_rate_threshold"]
    assert payload["summary"]["coverage_status"] == "acceptable"
    assert payload["cluster_key"]["field"] == "annex_pattern_cluster_key"
    assert payload["cluster_key"]["fallback"] == "unrouted"
    assert payload["source_kind_counts_for_unrouted"]
    assert payload["largest_unrouted_annexes"]
    assert payload["largest_unrouted_annexes"][0]["candidate_repair_files"]
    assert payload["missing_problem_space_by_annex_slug"]
    assert payload["debt_rows"] == []


def test_annex_routing_coverage_emits_debt_when_threshold_is_exceeded() -> None:
    payload = build_annex_routing_coverage(REPO_ROOT, context_budget=12000, unrouted_rate_threshold=0.01)

    assert payload["summary"]["coverage_status"] == "debt"
    debt = {row["debt_id"]: row for row in payload["debt_rows"]}
    assert "routing_coverage:annex_patterns:unrouted" in debt
    assert debt["routing_coverage:annex_patterns:unrouted"]["debt_class"] == "routing_coverage_debt"


def test_annex_routing_coverage_cli_emits_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--annex-routing-coverage",
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
    assert payload["kind"] == "annex_routing_coverage"
    assert payload["summary"]["coverage_status"] in {"acceptable", "debt"}
