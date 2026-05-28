"""Regression coverage for the dynamic paper-as-lattice exemplar."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.dynamic_paper_lattice import build_dynamic_paper_lattice


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dynamic_paper_lattice_projects_source_anchored_affordance_rows() -> None:
    payload = build_dynamic_paper_lattice(
        REPO_ROOT,
        slug="navigation_hologram_theory",
        band="card",
        context_budget=12000,
    )

    assert payload["kind"] == "dynamic_paper_lattice"
    assert payload["schema_version"] == "dynamic_paper_lattice_v0"
    assert payload["contract"]["paper_module_profile_id"] == "paper_module_navigation_v0"
    assert payload["source"]["generated_sidecar_posture"] == "not_used_for_authority"
    assert payload["budget"]["estimated_tokens"] <= payload["budget"]["context_budget_tokens"]

    rows = {row["row_id"]: row for row in payload["rows"]}
    assert "paper_module:navigation_hologram_theory" in rows
    assert "nav_hologram.option_surface" in rows
    assert "paper_section:navigation_hologram_theory:shape" in rows
    assert "paper_principle_insert:navigation_hologram_theory:pri_049" in rows

    option_surface = rows["nav_hologram.option_surface"]
    assert option_surface["facet"] == "mechanism"
    assert option_surface["source_anchor"]["path"] == "codex/doctrine/paper_modules/navigation_hologram_theory.md"
    assert option_surface["band_packet"]["drilldown_to"] == "context"

    edge_verbs = {edge["verb"] for edge in payload["edge_rows"]}
    assert {"depends_on", "governs", "contains", "evidenced_by"}.issubset(edge_verbs)

    paper_view = payload["paper_view"]
    assert paper_view["view_kind"] == "human_readable_dynamic_paper"
    assert any(section["slot"] == "governing_principles" for section in paper_view["sections"])
    assert "full paper-module body" in payload["omission_receipt"]["omitted"]


def test_dynamic_paper_lattice_filters_scope_and_facet() -> None:
    payload = build_dynamic_paper_lattice(
        REPO_ROOT,
        slug="navigation_hologram_theory",
        band="card",
        scope="section",
        facet="mechanism",
        edge_neighborhood=0,
        context_budget=12000,
    )

    assert payload["edge_rows"] == []
    assert payload["rows"]
    assert {row["scope"] for row in payload["rows"]} == {"section"}
    assert {row["facet"] for row in payload["rows"]} == {"mechanism"}


def test_dynamic_paper_lattice_supports_existing_non_exemplar_slug() -> None:
    payload = build_dynamic_paper_lattice(
        REPO_ROOT,
        slug="raw_seed_theory",
        band="card",
        context_budget=12000,
    )

    assert "error" not in payload
    assert payload["root_row"]["row_id"] == "paper_module:raw_seed_theory"
    assert payload["source"]["path"] == "codex/doctrine/paper_modules/raw_seed_theory.md"
    assert payload["source"]["stable_slug_support"] == "generic_existing_paper_module_slug"
    rows = {row["row_id"]: row for row in payload["rows"]}
    assert "paper_section:raw_seed_theory:tldr_compressed_view" in rows
    assert "paper_section:raw_seed_theory:intent" in rows
    assert payload["summary"]["self_application_row_count"] == 0
    assert any(edge["target_ref"] == "paper_module:navigation_hologram_theory" for edge in payload["edge_rows"])
    assert payload["budget"]["estimated_tokens"] <= payload["budget"]["context_budget_tokens"]


def test_dynamic_paper_lattice_cli_emits_budgeted_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--paper-lattice",
            "navigation_hologram_theory",
            "--band",
            "card",
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
    assert payload["kind"] == "dynamic_paper_lattice"
    assert payload["summary"]["self_application_row_count"] >= 10
    assert len(result.stdout.encode("utf-8")) <= 12000 * 4


def test_dynamic_paper_lattice_unknown_slug_is_structured_selection_error() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--paper-lattice",
            "guessed_navigation_query",
            "--band",
            "card",
            "--context-budget",
            "12000",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["kind"] == "dynamic_paper_lattice"
    assert payload["error"] == "unknown_paper_module_slug"
    assert "--option-surface paper_modules --band cluster_flag" in " ".join(payload["selection_routes"])
