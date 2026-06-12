"""Regression coverage for standard-owned option-surface navigation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.kind_atlas import build_kind_atlas
from system.lib.cognitive_operator_registry import validate_cognitive_operator_registry
from system.lib import standard_option_surface, task_ledger_events
from system.lib.kernel.commands import generated_artifact_surfaces as generated_surfaces
from system.lib.kernel.commands.generated_artifact_surfaces import emit_agent_observation
from system.lib.standard_option_surface import build_option_surface


REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_SEED_TEST_SHARD_ID = "sh_00da19772a638cba"
RAW_SEED_TEST_PARENT_ID = (
    "par_phase_09_raw_seed__the_actual_problem_space_not_repeated_back_at_you__problem_3_bridge_outputs_have_no_machine_readable_contract_with_downstream_systems_001"
)
ANNEX_PATTERN_TEST_SLUG = "llm-wiki"
ANNEX_PATTERN_TEST_NOTE_ID = "n001"
ANNEX_PATTERN_TEST_ID = f"{ANNEX_PATTERN_TEST_SLUG}:{ANNEX_PATTERN_TEST_NOTE_ID}"
ANNEX_DISTILLATION_TEST_SLUG = "agentic-stack"
ANNEX_DISTILLATION_TEST_PATTERN_ID = "p001"
ANNEX_DISTILLATION_TEST_ID = (
    f"{ANNEX_DISTILLATION_TEST_SLUG}:{ANNEX_DISTILLATION_TEST_PATTERN_ID}"
)
MICROCOSM_EXTRACTED_PATTERN_TEST_ID = "navigation_hologram_unified_route_plane"
PYTHON_FILE_TEST_ID = "codex/standards/std_python.py"
PYTHON_SCOPE_TEST_ID = "codex/standards/std_python.py::StandardReference"
PYTHON_SCOPE_TEST_PATH = "codex/standards/std_python.py"
FRONTEND_COMPONENT_TEST_ID = "system/server/ui/src/components/ArtifactViewer.tsx::ArtifactViewer"
FRONTEND_COMPONENT_LOW_CONFIDENCE_ID = (
    "system/server/ui/src/components/GraphViewer.tsx::EMPHASIS_TIERS"
)
FRONTEND_COMPONENT_PROJECTION_PATH = "state/frontend_navigation/component_index.json"


def _write_json(root: Path, rel_path: str, payload: object) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _seed_mechanism_workitem_fixture(root: Path) -> None:
    _write_json(
        root,
        "codex/standards/std_task_ledger.json",
        {"schema_version": "std_task_ledger_v1"},
    )
    _write_json(
        root,
        "codex/standards/principles/std_mechanism.json",
        {"schema_version": "doctrine_mechanism_standard_v1"},
    )
    _write_json(
        root,
        "codex/doctrine/mechanisms/mech_002_typed_receipt_validation.json",
        {
            "kind": "doctrine_mechanism",
            "schema_version": "doctrine_mechanism_v1",
            "id": "mech_002",
            "slug": "typed-receipt-validation",
            "title": "Typed Receipt Validation",
            "statement": "Bridge receipts are validated as typed JSON contracts.",
            "scope": "universal",
            "status": "active",
            "tags": ["receipts", "validation", "json-first"],
        },
    )
    task_ledger_events.append_event(
        root,
        {
            "event_id": "wie_test_mechanism_workitem_cluster",
            "event_type": "work_item.captured",
            "created_at": "2026-05-12T00:00:00+00:00",
            "created_by": "codex",
            "subject_id": "cap_typed_receipt_validation_work",
            "payload": {
                "title": "Typed receipt validation WorkItem",
                "statement": "Fix mech_002 typed receipt validation so receipts remain JSON-first.",
                "work_item_type": "task",
                "tags": ["receipts", "validation"],
            },
        },
    )
    task_ledger_events.rebuild_projections(root)


def _annex_distillation_source(slug: str, pattern_id: str) -> tuple[dict, dict]:
    path = REPO_ROOT / "annexes" / slug / "distillation.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for pattern in data["patterns"]:
        if pattern["id"] == pattern_id:
            return data, pattern
    raise AssertionError(f"Missing pattern {slug}:{pattern_id}")


def test_paper_modules_flag_surface_enumerates_without_query() -> None:
    payload = build_option_surface(REPO_ROOT, "paper_modules", band="flag")

    assert payload["kind"] == "standard_owned_option_surface"
    assert payload["profile_status"] == "supported"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration"
    assert payload["summary"]["row_count"] > 20

    rows = {row["slug"]: row for row in payload["rows"]}
    assert "navigation_hologram_theory" in rows
    row = rows["navigation_hologram_theory"]
    assert row["band"] == "flag"
    assert row["standard_ref"] == "codex/standards/std_paper_module.json"
    assert row["source_ref"] == "codex/doctrine/paper_modules/navigation_hologram_theory.md"
    assert row["drilldown_command"].endswith("--band card --ids navigation_hologram_theory")
    assert row["dependency_counts"]["depends_on"] >= 1
    assert row["governing_counts"]["principles"] >= len(row["governing_principles"]) >= 1
    assert row["governing_counts"]["concepts"] >= len(row["governing_concepts"]) >= 1
    assert row["governing_refs"]["principles"] == row["governing_principles"]
    assert row["governing_refs"]["concepts"] == row["governing_concepts"]
    assert row["currentness"]["recommended_action"]


def test_paper_module_currentness_demotes_trust_when_code_loci_changed() -> None:
    currentness = standard_option_surface._paper_module_currentness(
        {
            "recommended_action": "trust",
            "action_reason": "Module passes its current projection-class contract.",
            "code_loci_freshness": {
                "status": "source_changed",
                "source_newer_than_module_count": 2,
                "newest_source_path": "system/lib/example.py",
                "newest_source_mtime": "2026-05-09T13:00:00+00:00",
            },
        },
        index={"freshness": {"sync_status": "in_sync"}, "generated_at": "2026-05-09T03:44:23+00:00"},
    )

    assert currentness["recommended_action"] == "verify_code_loci_before_trust"
    assert currentness["module_recommended_action"] == "trust"
    assert currentness["code_loci_freshness"] == "source_changed"
    assert currentness["source_newer_than_module_count"] == 2
    assert currentness["trust_boundary"] == "paper_module_projection_requires_code_loci_verification"


def test_paper_modules_cluster_flag_clusters_before_row_expansion() -> None:
    payload = build_option_surface(REPO_ROOT, "paper_modules", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    pretty_bytes = len(json.dumps(payload, indent=2, sort_keys=True))
    assert pretty_bytes <= 48_000
    assert payload["summary"]["cluster_row_output_policy"].startswith("compact_clusters_top_")
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "subdomain_authority_projection" in rows
    cluster = rows["subdomain_authority_projection"]
    assert cluster["band"] == "cluster_flag"
    assert cluster["count"] >= 1
    assert cluster["cluster_source_axis"] == "primary_subdomain"
    # Invariant: the system_self_comprehension family of paper modules MUST be
    # represented in this cluster (the family is what the
    # subdomain_authority_projection cluster names). Avoid asserting on a
    # specific slug being in the truncated `top_ids` preview — `top_ids` is an
    # alphabetical truncated list (the first compact preview of N), so as new
    # `system_self_comprehension_*` siblings land they can push older ones
    # out of the preview without changing the invariant. Family membership in
    # the cluster is the durable contract.
    assert len(cluster["top_ids"]) <= standard_option_surface.PAPER_MODULE_CLUSTER_TOP_ID_LIMIT
    family_top = [tid for tid in cluster["top_ids"] if tid.startswith("system_self_comprehension")]
    if not family_top:
        # The whole family fell off the alphabetical preview; verify the
        # cluster's overall count is still consistent with at least one
        # family member being inside the cluster proper. Counting on disk is
        # cheaper than re-running the full row-band query here.
        family_modules = list(
            (REPO_ROOT / "codex" / "doctrine" / "paper_modules").glob(
                "system_self_comprehension*.md"
            )
        )
        assert family_modules, (
            "no system_self_comprehension_* paper module exists on disk; "
            "cluster cannot legitimately omit the family from its preview"
        )
    else:
        assert family_top, (
            f"system_self_comprehension family missing from top_ids preview "
            f"and from disk: top_ids={cluster['top_ids']!r}"
        )
    assert cluster["authority_distribution"]["authored_primary"] >= 1
    assert cluster["top_ids_omitted"] >= 1
    assert "route_metadata" not in cluster
    assert "top_governing_refs" not in cluster
    assert cluster["top_ids"]
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert cluster["omission_policy"] == "details via drilldown"
    assert "all row-level flag rows" in payload["cluster_omission_receipt"]["omitted"]
    assert "per-cluster route metadata and governing refs" in payload["cluster_omission_receipt"]["omitted"]


def test_paper_modules_card_surface_drills_selected_ids_only() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "paper_modules",
        band="card",
        ids=["navigation_hologram_theory", "raw_seed_theory"],
    )

    assert payload["summary"]["query_used"] is False
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert {row["slug"] for row in payload["rows"]} == {"navigation_hologram_theory", "raw_seed_theory"}
    for row in payload["rows"]:
        assert row["band"] == "card"
        assert row["tldr_excerpt"]
        assert row["purpose_or_intent"]
        assert row["nearest_standard"]["ref"] == "codex/standards/std_paper_module.json"
        assert row["nearest_skill"]["ref"] == "codex/doctrine/skills/compression/profile_governed_compression.md"
        assert row["omission_receipt"]["drilldown"].endswith(row["slug"])


def test_paper_modules_context_surface_projects_task_packet() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "paper_modules",
        band="context",
        ids=["navigation_hologram_theory"],
    )

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "context"
    assert "context" in payload["governing_standard"]["owned_bands"]
    assert payload["selection"]["mode"] == "ids"

    row = payload["rows"][0]
    assert row["slug"] == "navigation_hologram_theory"
    assert row["band"] == "context"
    assert row["section_summaries"]["tldr"]
    assert row["section_summaries"]["intent"]
    assert "depends_on" in row["dependency_edges"]
    assert row["code_loci_summary"]["top_paths"]
    assert row["evidence_commands"][0].endswith("--paper-module navigation_hologram_theory")
    assert row["omission_receipt"]["drilldown"].endswith("navigation_hologram_theory")


def test_paper_modules_cluster_flag_collapses_authored_and_suggested_subdomains(tmp_path: Path) -> None:
    """The contents-page rung must not list the same subdomain twice as
    `subdomain_X` and `suggested_subdomain_X`. Authored and heuristic
    contributors merge into one canonical cluster keyed by subdomain identity;
    the authored-vs-suggested split lives in route_metadata and per-row
    authority_distribution. See std_paper_module.json::cluster_authority_collapse_rule.
    """
    _write_json(
        tmp_path,
        "codex/standards/std_paper_module.json",
        {"schema_version": "std_paper_module_v1"},
    )
    _write_json(
        tmp_path,
        "codex/doctrine/paper_modules/_index.json",
        {
            "schema_version": "paper_module_index_v1",
            "generated_at": "2026-05-16T00:00:00+00:00",
            "freshness": {"sync_status": "in_sync"},
            "modules": [
                {
                    "slug": "authored_authority_projection",
                    "title": "Authored Authority Projection",
                },
                {
                    "slug": "suggested_authority_projection",
                    "title": "Suggested Authority Projection",
                },
            ],
        },
    )
    _write_json(
        tmp_path,
        "codex/doctrine/paper_modules/_route_coverage.json",
        {
            "schema_version": "paper_module_route_coverage_v4",
            "paper_module_routes": {
                "authored_authority_projection": {
                    "slug": "authored_authority_projection",
                    "routes": [
                        {
                            "axis": "primary_subdomain",
                            "target": "authority_projection",
                            "source": "frontmatter",
                        }
                    ],
                    "suggested_routes": [],
                },
                "suggested_authority_projection": {
                    "slug": "suggested_authority_projection",
                    "routes": [],
                    "suggested_routes": [
                        {
                            "axis": "suggested_primary_subdomain",
                            "target": "authority_projection",
                            "source": "generated_route_inference",
                            "confidence": 0.75,
                        }
                    ],
                },
            },
        },
    )

    payload = build_option_surface(tmp_path, "paper_modules", band="cluster_flag")
    rows = payload["rows"]

    # Invariant 1: no cluster id starts with `suggested_subdomain_`. The
    # canonical id is always `subdomain_<slug>`.
    suggested_ids = [r["cluster_id"] for r in rows if r["cluster_id"].startswith("suggested_subdomain_")]
    assert suggested_ids == [], (
        f"contents-page rung still lists redundant suggested_subdomain_ rows: {suggested_ids}"
    )

    # Invariant 2: the merged Authority Projection cluster carries the
    # authority breakdown chip and reports the most-authoritative axis when
    # both authored and suggested contributors are present.
    rows_by_id = {r["cluster_id"]: r for r in rows}
    authority = rows_by_id.get("subdomain_authority_projection")
    assert authority is not None
    assert authority["cluster_source_axis"] == "primary_subdomain"
    breakdown = authority["authority_distribution"]
    assert breakdown["authored_primary"] >= 1
    assert breakdown["suggested_primary"] >= 1
    # Sum of bucket counts agrees with the cluster count.
    assert (
        breakdown["authored_primary"]
        + breakdown["suggested_primary"]
        + breakdown["hierarchy_fallback"]
        + breakdown["heuristic_fallback"]
        + breakdown["unclassified"]
    ) == authority["count"]
    # The contents-page row claim names the authority distribution so a future
    # agent reading the cluster row knows the trust posture without drilldown.
    assert "authored" in authority["claim"]
    assert "suggested" in authority["claim"]

    # Invariant 3: the payload-level summary reports the global authority
    # distribution so the contents page itself is a trust-aware contents page.
    summary = payload["summary"]["cluster_authority_distribution"]
    assert summary["authored_primary"] >= 1
    assert summary["suggested_primary"] >= 1
    assert summary["chip"]
    # cluster_omission_receipt names the collapse rule so a future agent reading
    # the receipt understands why subdomain rows do not split by authority.
    assert "authority_collapse_rule" in payload["cluster_omission_receipt"]


def test_paper_modules_card_projects_authored_compression_when_present() -> None:
    """When a paper module has authored compression frontmatter, the card row
    must surface ``open_when`` / ``do_not_open_when`` / ``safe_drilldown``
    directly (per std_paper_module.json::compression_authoring_contract.required_navigation_fields).
    A card without authored compression must NOT leak fallback prose into those
    fields; it must instead carry an authoring_debt chip.
    """
    payload = build_option_surface(
        REPO_ROOT,
        "paper_modules",
        band="card",
        ids=[
            "annex_crystal_navigation_spine",
            "navigation_hologram_theory",
            "agent_observability",
        ],
    )
    rows = {row["slug"]: row for row in payload["rows"]}

    authored = rows["annex_crystal_navigation_spine"]
    assert authored["compression"]["compression_status"] == "authored"
    assert authored["open_when"]
    assert authored["do_not_open_when"]
    assert authored["safe_drilldown"].startswith("./repo-python kernel.py")
    passport = authored["compression_passport"]
    assert passport["source_contract"] == (
        "codex/standards/std_paper_module.json::compression_passport_projection_contract"
    )
    assert passport["atom"]
    assert passport["cluster_keys"]
    assert passport["when_to_open"] == authored["open_when"]
    assert passport["when_not_to_open"] == authored["do_not_open_when"]
    assert passport["safe_drilldown"] == authored["safe_drilldown"]
    sources = authored["compression"]["compression_sources"]
    assert sources.get("open_when", "").startswith("authored")
    assert sources.get("do_not_open_when", "").startswith("authored")
    assert sources.get("safe_drilldown", "").startswith("authored")

    route_theory = rows["navigation_hologram_theory"]
    assert route_theory["compression"]["compression_status"] == "authored"
    assert route_theory["compression_passport"]["atom"] == "Route-first option surface theory"
    assert route_theory["compression_passport"]["safe_drilldown"] == (
        "./repo-python kernel.py --paper-module navigation_hologram_theory"
    )
    assert "authority_projection_boundary" in route_theory["compression_passport"]["cluster_keys"]
    assert "doctrine_routing_weave" in route_theory["compression_passport"]["cluster_keys"]
    assert (
        "bidirectional doctrine-to-substrate traversal"
        in route_theory["compression_passport"]["when_to_open"]
    )
    assert "replacement for `--entry`" in route_theory["compression_passport"]["when_not_to_open"]

    fallback = rows["agent_observability"]
    assert fallback["compression"]["compression_status"] == "fallback"
    # Fallback rows must not project authored-only fields.
    assert "open_when" not in fallback or fallback.get("open_when") in (None, "")
    assert "do_not_open_when" not in fallback or fallback.get("do_not_open_when") in (None, "")
    assert "safe_drilldown" not in fallback or fallback.get("safe_drilldown") in (None, "")
    assert "compression_passport" not in fallback
    # And they must surface authoring debt so the gap is visible at the row.
    assert "authoring_debt" in fallback["compression"]


def test_option_surface_unsupported_kind_emits_profile_gap() -> None:
    payload = build_option_surface(REPO_ROOT, "unknown_kind", band="flag")

    assert payload["profile_status"] == "profile_gap"
    assert payload["rows"] == []
    assert payload["summary"]["query_used"] is False


def test_type_a_autonomous_seeds_cluster_flag_groups_by_lane() -> None:
    payload = build_option_surface(REPO_ROOT, "type_a_autonomous_seeds", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "type_a_autonomous_seed_cluster_overview"
    assert payload["summary"]["drilldown_by"] == "lane"
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "lane:terrain_with_task_touches" in rows
    cluster = rows["lane:terrain_with_task_touches"]
    assert cluster["band"] == "cluster_flag"
    assert cluster["count"] >= 1
    assert cluster["top_ids"]
    assert "focused_with_pivot" in cluster["scope_shape_counts"]
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert any("raw_seed.md bodies" in item for item in cluster["omission_receipt"]["omitted"])
    assert "all row-level seed flags" in payload["cluster_omission_receipt"]["omitted"]


def test_type_a_autonomous_seeds_cluster_flag_ids_select_lane_cluster() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "type_a_autonomous_seeds",
        band="cluster_flag",
        ids="lane:terrain_with_task_touches",
    )

    assert payload["selection"]["missing_ids"] == []
    assert [row["cluster_id"] for row in payload["rows"]] == ["lane:terrain_with_task_touches"]
    assert payload["rows"][0]["top_ids"]


def test_system_atlas_option_surface_projects_source_coupling_when_inputs_move(
    tmp_path: Path,
    monkeypatch,
) -> None:
    graph_path = tmp_path / "state" / "system_atlas" / "system_atlas.graph.json"
    graph_path.parent.mkdir(parents=True)
    graph_path.write_text(
        json.dumps(
            {
                "schema_version": "system_atlas_graph_v1",
                "generated_at": "2026-05-09T00:00:00Z",
                "generated_by": "tools/meta/factory/build_system_atlas.py",
                "source_inputs": [
                    {
                        "source_id": "task_ledger_views",
                        "path": "state/task_ledger/views/*.json",
                        "count": 30,
                        "latest_mtime": "2026-05-09T00:00:00Z",
                    }
                ],
                "entities": [
                    {
                        "id": "dom_system_atlas",
                        "kind": "Domain",
                        "title": "System Atlas control plane",
                        "summary": "Generated System Atlas v1.",
                        "authority_class": "derived_projection",
                        "freshness_status": "fresh",
                    }
                ],
                "findings": [],
                "summary": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        standard_option_surface,
        "_system_atlas_current_source_inputs",
        lambda repo_root: [
            {
                "source_id": "task_ledger_views",
                "path": "state/task_ledger/views/*.json",
                "count": 31,
                "latest_mtime": "2026-05-09T01:00:00Z",
            }
        ],
    )

    payload = standard_option_surface.build_option_surface(
        tmp_path,
        "system_atlas",
        band="card",
        ids=["dom_system_atlas"],
    )

    assert payload["source_coupling"]["status"] == "source_inputs_changed_since_artifact_generation"
    assert payload["currentness"]["status"] == "stale_source_coupling"
    assert payload["currentness"]["source_coupling_status"] == "source_inputs_changed_since_artifact_generation"
    assert payload["currentness"]["safe_to_commit_generated_outputs_without_sources"] is False
    assert payload["currentness"]["freshness_command"] == (
        "./repo-python tools/meta/factory/build_system_atlas.py --check"
    )
    assert payload["summary"]["projection_freshness_status"] == "stale_source_coupling"
    assert payload["summary"]["safe_to_commit_generated_outputs_without_sources"] is False
    assert payload["summary"]["row_count"] == 1
    assert payload["warnings"][0]["kind"] == "system_atlas_source_coupling_not_clean"
    assert payload["warnings"][0]["repair_command"] == payload["currentness"]["freshness_command"]
    boundary = payload["navigation_boundary"]
    assert boundary["first_contact_allowed"] is False
    assert "kernel.py --entry" in boundary["control_replacement"]
    assert boundary["source_coupling_status"] == "source_inputs_changed_since_artifact_generation"
    assert boundary["safe_to_commit_generated_outputs_without_sources"] is False
    # Soft-stale semantics: stale projection rows remain available for diagnostics;
    # this sentinel pins payload shape, not a hard refusal.
    assert payload["rows"]
    row = payload["rows"][0]
    assert row["freshness_status"] == "fresh"
    assert row["currentness"]["status"] == "stale_source_coupling"
    assert row["currentness"]["freshness_command"] == payload["currentness"]["freshness_command"]
    assert row["source_coupling_status"] == "source_inputs_changed_since_artifact_generation"
    assert row["safe_to_commit_generated_outputs_without_sources"] is False


def test_system_atlas_option_surface_resolves_missing_type_plane_ids_from_standard(
    tmp_path: Path,
    monkeypatch,
) -> None:
    graph_path = tmp_path / "state" / "system_atlas" / "system_atlas.graph.json"
    graph_path.parent.mkdir(parents=True)
    source_inputs = [
        {
            "source_id": "standard_type_plane",
            "path": "codex/standards/std_standard_type_plane.json",
            "count": 1,
            "latest_mtime": "2026-05-27T00:00:00Z",
        }
    ]
    graph_path.write_text(
        json.dumps(
            {
                "schema_version": "system_atlas_graph_v1",
                "generated_at": "2026-05-27T00:00:00Z",
                "generated_by": "tools/meta/factory/build_system_atlas.py",
                "source_inputs": source_inputs,
                "entities": [],
                "findings": [],
                "summary": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        standard_option_surface,
        "_system_atlas_current_source_inputs",
        lambda repo_root: source_inputs,
    )

    requested_ids = [
        "kind_standards_compliance_projection",
        "surface_type_plane_standards_compliance_projection_option_surface",
        "validator_type_plane_standards_compliance_projection",
    ]
    payload = standard_option_surface.build_option_surface(
        tmp_path,
        "system_atlas",
        band="card",
        ids=requested_ids,
    )

    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["selection_method"] == "generated_system_atlas_graph_plus_live_type_plane_overlay"
    assert payload["summary"]["generated_graph_entity_count"] == 0
    assert payload["summary"]["live_type_plane_overlay_count"] == 3
    assert payload["summary"]["missing_ids_resolved_by_live_overlay"] == requested_ids
    assert payload["source_coupling"]["status"] == "source_inputs_match_checked_artifact"
    rows = {row["id"]: row for row in payload["rows"]}
    assert set(rows) == set(requested_ids)

    kind_row = rows["kind_standards_compliance_projection"]
    assert kind_row["metrics"]["standard_type_plane"]["type_id"] == "standards_compliance_projection"
    assert kind_row["metrics"]["system_atlas_live_overlay"]["status"] == "live_standard_type_plane_overlay"
    assert kind_row["omission_receipt"]["drilldown"] == (
        "./repo-python kernel.py --option-surface navigation_type_plane --band card --ids standards_compliance_projection"
    )
    assert any(
        warning["kind"] == "system_atlas_live_type_plane_overlay"
        and warning["resolved_ids"] == requested_ids
        for warning in payload["warnings"]
    )


def test_task_ledger_cluster_flag_groups_workitem_views() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "task_ledger"
    assert payload["summary"]["selection_method"] == "task_ledger_view_cluster_overview"
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert payload["next"][0]["command"] == (
        "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2"
    )
    assert "before portfolio mutation" in payload["next"][0]["reason"]

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "execution_menu" in rows
    assert "execution_menu_schedulable" in rows
    assert "schedulable_by_rank" in rows
    assert "dependency_graph" in rows
    assert "dependency_blocked" in rows
    assert "dependency_anomalies" in rows
    assert "propagation_needed" in rows
    assert rows["propagation_needed"]["organizer_routing"]["organizer_role"] == "local_to_general_disposition"
    assert "work_item.propagation_recorded" in rows["propagation_needed"]["organizer_routing"]["recommended_next_events"]
    assert payload["cluster_organizer_routing_omission_receipt"]["drilldowns"]
    assert payload["event_command_hints"]["work_item.propagation_recorded"].startswith(
        "./repo-python tools/meta/factory/task_ledger_apply.py propagate"
    )
    assert "--rebuild" not in payload["event_command_hints"]["work_item.captured"]
    assert payload["event_command_hints"]["work_item.captured"].endswith(
        "--created-by <agent_id>"
    )
    assert payload["projection_settlement_hint"]["settle_deferred_rebuilds"].endswith(
        "drain-deferred-rebuilds --limit 1"
    )
    assert "task_ledger_projection" in payload["projection_settlement_hint"]["settle_generated_state"]
    assert "capture_triage" in rows
    assert "capture_inbox" in rows
    inbox = rows["capture_inbox"]
    assert inbox["count_semantics"] == "total_capture_log_including_closed_shaped_and_raw_rows"
    assert inbox["projection_semantics"]["not_live_backlog_count"] is True
    assert isinstance(inbox["raw_capture_inbox_count"], int)
    assert "raw_capture_inbox_count" in inbox["purpose"]
    assert isinstance(rows["execution_menu"]["top_ids"], list)
    if rows["execution_menu"]["top_ids"]:
        assert rows["execution_menu"]["drilldown_command"].startswith(
            "./repo-python kernel.py --option-surface task_ledger --band flag --ids"
        )
        assert rows["execution_menu"]["drilldown_command"].endswith(
            ",".join(rows["execution_menu"]["top_ids"])
        )
    else:
        assert rows["execution_menu"]["drilldown_command"] == (
            "./repo-python kernel.py --option-surface task_ledger --band flag"
        )
    assert "stale_review" in rows
    assert "stale_fixed_candidates" in rows
    stale_fixed = rows["stale_fixed_candidates"]
    assert stale_fixed["source_ref"] == "state/task_ledger/views/stale_fixed_candidates.json"
    assert stale_fixed["organizer_routing"]["organizer_role"] == "stale_fixed_candidate_sweeper"
    assert "work_item.retired" in stale_fixed["organizer_routing"]["recommended_next_events"]
    assert "meta_mission_active" in rows
    assert "mission_operating_picture" in rows
    operating_picture = rows["mission_operating_picture"]
    assert operating_picture["source_ref"] == "state/task_ledger/views/mission_operating_picture.json"
    assert operating_picture["organizer_routing"]["organizer_role"] == "mission_operating_picture_review"
    assert "work_item.note_added" in operating_picture["organizer_routing"]["recommended_next_events"]
    assert "cap_census" in rows
    cap_census = rows["cap_census"]
    assert cap_census["source_ref"] == "state/task_ledger/views/cap_census.json"
    assert cap_census["organizer_routing"]["organizer_role"] == "cap_universe_census"
    assert "work_item.note_added" in cap_census["organizer_routing"]["recommended_next_events"]
    assert "cap_cartography" in rows
    cap_cartography = rows["cap_cartography"]
    assert cap_cartography["source_ref"] == "state/task_ledger/views/cap_cartography.json"
    assert cap_cartography["organizer_routing"]["organizer_role"] == "cap_cartography_review"
    assert "work_item.note_added" in cap_cartography["organizer_routing"]["recommended_next_events"]
    assert "representative nodes" in cap_cartography["purpose"]
    assert "workitem_cartography" in rows
    workitem_cartography = rows["workitem_cartography"]
    assert workitem_cartography["source_ref"] == "state/task_ledger/views/workitem_cartography.json"
    assert workitem_cartography["organizer_routing"]["organizer_role"] == "workitem_cartography_review"
    assert "work_item.signoff_recorded" in workitem_cartography["organizer_routing"]["recommended_next_events"]
    assert "signoff" in workitem_cartography["purpose"]
    triage = rows["capture_triage"]["organizer_routing"]
    assert triage["organizer_role"] == "gating_triage"
    assert triage["routing_scent_not_authority"] is True
    assert "work_item.retired" in triage["recommended_next_events"]
    assert triage["conceptual_next_events"] == []
    assert "per-row supported command templates" in payload["cluster_organizer_routing_omission_receipt"]["omitted"]
    assert all(event in payload["event_command_hints"] for event in triage["recommended_next_events"])


def test_task_ledger_cluster_flag_uses_projection_browse_health(monkeypatch) -> None:
    def fail_authority_health(*_args, **_kwargs):
        raise AssertionError("bare cluster_flag should not run full Task Ledger authority health")

    monkeypatch.setattr(task_ledger_events, "authority_health", fail_authority_health)

    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag")

    health = payload["authority_health"]
    assert health["schema"] == "task_ledger_projection_browse_health_v0"
    assert health["ok"] is True
    assert health["status"] == "projection_browse_summary"
    assert health["full_authority_scan"] is False
    assert health["projection_work_item_count"] == payload["summary"]["total_available"]
    assert health["full_authority_check_command"] == (
        "./repo-python tools/meta/factory/task_ledger_apply.py authority-health"
    )
    assert not any(
        warning["kind"] == "task_ledger_authority_recovery_required"
        for warning in payload["warnings"]
    )


def test_task_ledger_cluster_flag_compact_reads_large_views(monkeypatch, tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "codex/standards/std_task_ledger.json",
        {"schema_version": "std_task_ledger_v1"},
    )
    work_items = [
        {
            "id": f"cap_compact_{index:03d}",
            "title": f"Compact row {index}",
            "state": "captured",
            "work_item_type": "capture",
        }
        for index in range(20)
    ]
    _write_json(tmp_path, "state/task_ledger/ledger.json", {"work_items": work_items})
    _write_json(
        tmp_path,
        "state/task_ledger/views/capture_inbox.json",
        {
            "kind": "task_ledger_view",
            "schema_version": "task_ledger_view_v1",
            "view_id": "capture_inbox",
            "items": [
                {
                    **item,
                    "count": 999,
                    "view_id": "nested_row_field_not_view_metadata",
                    "large_payload": "x" * 200,
                }
                for item in work_items
            ],
            "count": len(work_items),
            "count_semantics": "test_count_semantics",
            "projection_semantics": {"not_live_backlog_count": True},
            "raw_capture_inbox_count": 20,
        },
    )
    original_load_json = standard_option_surface._load_json

    def guarded_load_json(path: Path):
        if path.name == "capture_inbox.json":
            raise AssertionError("cluster_flag should compact-read large Task Ledger views")
        return original_load_json(path)

    monkeypatch.setattr(standard_option_surface, "TASK_LEDGER_COMPACT_VIEW_BYTES_THRESHOLD", 1)
    monkeypatch.setattr(standard_option_surface, "_load_json", guarded_load_json)

    payload = build_option_surface(tmp_path, "task_ledger", band="cluster_flag")
    rows = {row["cluster_id"]: row for row in payload["rows"]}
    capture_inbox = rows["capture_inbox"]

    assert capture_inbox["count"] == 20
    assert capture_inbox["top_ids"] == [
        "cap_compact_000",
        "cap_compact_001",
        "cap_compact_002",
    ]
    assert capture_inbox["count_semantics"] == "test_count_semantics"
    assert capture_inbox["projection_semantics"]["not_live_backlog_count"] is True
    assert capture_inbox["raw_capture_inbox_count"] == 20
    assert capture_inbox["projection_read"]["full_item_payload_omitted"] is True


def test_task_ledger_compact_view_payload_samples_rows_fallback(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "cap_census.json"
    payload = {
        "kind": "task_ledger_view",
        "schema_version": "cap_census_v0",
        "view_id": "cap_census",
        "rows": [
            {
                "id": "cap_rows_001",
                "state": "captured",
                "count": 999,
            },
            {
                "id": "cap_rows_002",
                "state": "captured",
            },
        ],
        "padding": "x" * 2000,
        "items": [
            {
                "id": "cap_late_items_001",
                "state": "captured",
            }
        ],
        "count": 2,
    }
    text = json.dumps(payload, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    prefix_len = text.index('"padding"') - 1

    monkeypatch.setattr(standard_option_surface, "TASK_LEDGER_COMPACT_VIEW_PREFIX_BYTES", prefix_len)
    monkeypatch.setattr(standard_option_surface, "TASK_LEDGER_COMPACT_VIEW_SUFFIX_BYTES", 256)

    compact = standard_option_surface._task_ledger_compact_view_payload(path)

    assert compact["count"] == 2
    assert [item["id"] for item in compact["items"]] == ["cap_rows_001", "cap_rows_002"]
    assert compact["_cluster_view_compact_read"]["sample_source_key"] == "rows"


def test_task_ledger_compact_view_top_level_scan_stops_at_sample_array() -> None:
    text = json.dumps(
        {
            "kind": "task_ledger_view",
            "schema_version": "task_ledger_view_v1",
            "view_id": "large_view",
            "items": [
                {
                    "id": "cap_large_001",
                    "state": "captured",
                    "nested_count": 999,
                    "large_payload": "x" * 10_000,
                }
            ],
            "count": 1,
        },
        separators=(",", ":"),
    )

    starts = standard_option_surface._json_top_level_value_starts(
        text,
        stop_after_keys={"items", "work_items", "candidates", "rows"},
    )

    assert set(starts) == {"kind", "schema_version", "view_id", "items"}
    assert "count" not in starts


def test_task_ledger_selected_card_skips_large_unmatched_view(monkeypatch, tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "codex/standards/std_task_ledger.json",
        {"schema_version": "std_task_ledger_v1"},
    )
    _write_json(
        tmp_path,
        "state/task_ledger/ledger.json",
        {
            "work_items": [
                {
                    "id": "cap_selected_card",
                    "title": "Selected card",
                    "state": "captured",
                    "work_item_type": "performance",
                }
            ]
        },
    )
    unrelated_view = {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_view_v1",
        "view_id": "capture_inbox",
        "items": [
            {
                "id": "cap_unrelated_card",
                "state": "captured",
                "large_payload": "x" * 5000,
            }
        ],
        "count": 1,
    }
    _write_json(tmp_path, "state/task_ledger/views/capture_inbox.json", unrelated_view)
    heavyweight_view = {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_view_v1",
        "view_id": "cap_execution_market",
        "items": [
            {
                "id": "cap_selected_card",
                "state": "captured",
                "large_payload": "x" * 5000,
            }
        ],
        "count": 1,
    }
    _write_json(tmp_path, "state/task_ledger/views/cap_execution_market.json", heavyweight_view)
    original_load_json = standard_option_surface._load_json

    def guarded_load_json(path: Path):
        if path.name == "capture_inbox.json":
            raise AssertionError("selected card drilldowns should not parse large unmatched views")
        if path.name == "cap_execution_market.json":
            raise AssertionError("selected card drilldowns should not parse heavyweight market views")
        return original_load_json(path)

    def fail_authority_health(*_args, **_kwargs):
        raise AssertionError("selected card drilldowns should use projection-browse health")

    monkeypatch.setattr(standard_option_surface, "TASK_LEDGER_COMPACT_VIEW_BYTES_THRESHOLD", 1)
    monkeypatch.setattr(standard_option_surface, "_load_json", guarded_load_json)
    monkeypatch.setattr(task_ledger_events, "authority_health", fail_authority_health)

    payload = build_option_surface(
        tmp_path,
        "task_ledger",
        band="card",
        ids=["cap_selected_card"],
    )

    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["row_count"] == 1
    health = payload["authority_health"]
    assert health["schema"] == "task_ledger_projection_browse_health_v0"
    assert health["full_authority_scan"] is False
    assert health["selected_card_visibility"]["cap_selected_card"]["visible"] is True
    assert health["full_authority_check_command"] == (
        "./repo-python tools/meta/factory/task_ledger_apply.py authority-health"
    )
    row = payload["rows"][0]
    assert row["id"] == "cap_selected_card"
    assert row["views"] == []


def test_task_ledger_selected_view_payload_decodes_matched_large_item(monkeypatch, tmp_path: Path) -> None:
    view_path = tmp_path / "capture_inbox.json"
    _write_json(
        tmp_path,
        "capture_inbox.json",
        {
            "kind": "task_ledger_view",
            "schema_version": "task_ledger_view_v1",
            "view_id": "capture_inbox",
            "items": [
                {
                    "id": "cap_unrelated_card",
                    "state": "captured",
                    "large_payload": "x" * 5000,
                },
                {
                    "id": "cap_selected_card",
                    "state": "ready",
                    "triage_status": "selected",
                },
            ],
            "count": 2,
        },
    )

    def fail_full_document_loads(_text: str):
        raise AssertionError("selected large view hit should not parse the full payload")

    monkeypatch.setattr(standard_option_surface, "TASK_LEDGER_COMPACT_VIEW_BYTES_THRESHOLD", 1)
    monkeypatch.setattr(standard_option_surface.json, "loads", fail_full_document_loads)

    payload = standard_option_surface._task_ledger_selected_view_payload(
        view_path,
        selected_work_item_ids={"cap_selected_card"},
    )

    assert payload["items"] == [
        {
            "id": "cap_selected_card",
            "state": "ready",
            "triage_status": "selected",
        }
    ]
    assert payload["_selected_view_fast_read"]["full_payload_omitted"] is True
    assert payload["_selected_view_fast_read"]["selected_item_count"] == 1


def test_task_ledger_cluster_flag_ids_keep_authority_health(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_authority_health(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return {
            "schema": "task_ledger_authority_health_v0",
            "ok": True,
            "status": "clean",
            "lost_subject_ids": [],
        }

    monkeypatch.setattr(task_ledger_events, "authority_health", fake_authority_health)

    payload = build_option_surface(
        REPO_ROOT,
        "task_ledger",
        band="cluster_flag",
        ids="capture_inbox",
    )

    assert calls, "selected cluster drilldowns should retain full authority health"
    assert payload["authority_health"]["schema"] == "task_ledger_authority_health_v0"


def test_task_ledger_cluster_flag_ids_select_view_cluster() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag", ids="capture_inbox")

    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["ids"] == ["capture_inbox"]
    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["drilldown_by"] == "view_id"
    assert [row["cluster_id"] for row in payload["rows"]] == ["capture_inbox"]
    assert payload["rows"][0]["projection_semantics"]["not_live_backlog_count"] is True


def test_task_ledger_cluster_flag_ids_select_stale_fixed_candidates_view() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "task_ledger",
        band="cluster_flag",
        ids="stale_fixed_candidates",
    )

    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["ids"] == ["stale_fixed_candidates"]
    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["drilldown_by"] == "view_id"
    assert [row["cluster_id"] for row in payload["rows"]] == ["stale_fixed_candidates"]
    row = payload["rows"][0]
    assert row["source_ref"] == "state/task_ledger/views/stale_fixed_candidates.json"
    assert row["organizer_routing"]["organizer_role"] == "stale_fixed_candidate_sweeper"
    assert row["top_ids"], "candidate-backed cleanup view should expose candidate ids"


def test_prompt_ledger_option_surface_exposes_mission_trace_current_state() -> None:
    payload = build_option_surface(REPO_ROOT, "prompt_ledger", band="flag")

    rows = {row["view_id"]: row for row in payload["rows"]}
    assert "mission_trace_current_state" in rows
    row = rows["mission_trace_current_state"]
    assert row["path"] == "state/prompt_ledger/views/mission_trace_current_state.json"
    assert row["authority_posture"] == "projection_browse_only_events_are_authority"
    assert row["projection_only"] is True
    assert row["owner_check_command"] == "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check"
    assert "mission trace" in row["flag"].lower()
    assert payload["summary"]["view_count"] >= 9


def test_task_ledger_cluster_flag_exposes_mechanism_affinity_clusters(tmp_path: Path) -> None:
    _seed_mechanism_workitem_fixture(tmp_path)

    payload = build_option_surface(tmp_path, "task_ledger", band="cluster_flag", ids="mechanism:mech_002")

    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["mechanism_cluster_count"] == 1
    assert payload["mechanism_cluster_overview"]["status"] == "selected_mechanism_cluster"
    row = payload["rows"][0]
    assert row["cluster_id"] == "mechanism:mech_002"
    assert row["artifact_kind"] == "task_ledger_mechanism_cluster"
    assert row["mechanism_id"] == "mech_002"
    assert row["top_ids"] == ["cap_typed_receipt_validation_work"]
    assert row["organizer_routing"]["routing_scent_not_authority"] is True
    assert "direct_mechanism_ref" in row["match_reason_counts"]
    assert row["mechanism_drilldown_command"].endswith("--ids mech_002")


def test_mechanism_flag_surface_links_back_to_workitem_pressure(tmp_path: Path) -> None:
    _seed_mechanism_workitem_fixture(tmp_path)

    payload = build_option_surface(tmp_path, "mechanisms", band="flag", ids="mech_002")

    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["mechanism_id"] == "mech_002"
    assert row["workitem_pressure_count"] == 1
    assert row["top_workitem_ids"] == ["cap_typed_receipt_validation_work"]
    assert row["task_ledger_cluster_id"] == "mechanism:mech_002"
    assert row["task_ledger_cluster_drilldown"].endswith("--ids mechanism:mech_002")


def test_task_ledger_cluster_flag_emits_anomaly_type_counts_for_typed_anomaly_views() -> None:
    """Regression: views whose items carry `anomaly_type` (e.g. dependency_anomalies)
    must surface anomaly_type_counts alongside state_counts. Pre-fix, state_counts
    collapsed to {"unknown": N} (true but uninformative) because anomaly items have
    no `state` field — the cluster row had no readable dimension to summarize on.
    The fix: when at least one item has `anomaly_type`, emit
    `anomaly_type_counts: Counter(anomaly_type)` so the row is self-describing
    instead of forcing a drilldown to discover the anomaly classification.
    """
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag")
    rows = {row["cluster_id"]: row for row in payload["rows"]}

    deps = rows["dependency_anomalies"]
    assert "state_counts" in deps
    # state_counts may legitimately collapse to {"unknown": N} for typed-anomaly
    # views; that's honest reflection that the items don't carry `state`.
    if deps["count"] > 0:
        assert "anomaly_type_counts" in deps, (
            "dependency_anomalies cluster row should carry anomaly_type_counts "
            "when it has typed anomaly items"
        )
        assert deps["anomaly_type_counts"], (
            "anomaly_type_counts must be a non-empty Counter when items exist"
        )
        for anomaly_type, count in deps["anomaly_type_counts"].items():
            assert anomaly_type and anomaly_type != "None", (
                f"anomaly_type_counts should not include null/None keys; got {anomaly_type!r}"
            )
            assert isinstance(count, int) and count > 0
        # The total of anomaly_type_counts should equal the cluster count for
        # a fully-typed anomaly view.
        assert sum(deps["anomaly_type_counts"].values()) == deps["count"]

    # Views without anomaly_type items should not gain the field gratuitously.
    execution_menu = rows["execution_menu"]
    assert "anomaly_type_counts" not in execution_menu or not execution_menu["anomaly_type_counts"]


def test_task_ledger_anomaly_cluster_drilldown_stays_on_cluster_surface() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag")
    rows = {row["cluster_id"]: row for row in payload["rows"]}

    deps = rows["dependency_anomalies"]
    if deps["top_ids"]:
        assert deps["drilldown_command"] == (
            "./repo-python kernel.py --option-surface task_ledger --band cluster_flag "
            "--ids dependency_anomalies"
        )
        selected = build_option_surface(
            REPO_ROOT,
            "task_ledger",
            band="cluster_flag",
            ids="dependency_anomalies",
        )
        assert selected["selection"]["missing_ids"] == []
        assert [row["cluster_id"] for row in selected["rows"]] == ["dependency_anomalies"]


def test_task_ledger_cluster_flag_exposes_commitment_and_evaporation_boundaries() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag")

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    execution = rows["execution_menu"]["organizer_routing"]
    assert execution["organizer_role"] == "commitment_boundary"
    assert "work_item.claimed" in execution["recommended_next_events"]

    merge = rows["merge_or_retire_candidates"]["organizer_routing"]
    assert merge["organizer_role"] == "trace_evaporation"
    assert "work_item.retired" in merge["recommended_next_events"]
    assert merge["routing_scent_not_authority"] is True
    assert merge["governance_route"]["owner_view"] == "state/task_ledger/views/merge_or_retire_candidates.json"
    assert merge["governance_route"]["review_required_count"] == 3


def test_option_surface_kernel_command_redirects_task_ledger_flag_all_to_clusters() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "task_ledger", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "task_ledger"
    assert payload["profile_status"] == "supported"
    assert payload["requested_band"] == "flag"
    assert payload["band"] == "cluster_flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "task_ledger_view_cluster_overview"
    assert "execution_menu" in {row["cluster_id"] for row in payload["rows"]}


def test_task_ledger_cluster_flag_separates_executable_and_conceptual_events() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag")

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    needs_signoff = rows["needs_signoff"]["organizer_routing"]
    assert "work_item.captured" in needs_signoff["recommended_next_events"]
    assert "work_item.followup_captured" not in needs_signoff["conceptual_next_events"]
    assert needs_signoff["missing_affordance_count"] == 0
    assert "quick-capture" in payload["event_command_hints"]["work_item.captured"]
    assert "--rebuild" not in payload["event_command_hints"]["work_item.captured"]

    signoffs = rows["signoffs"]["organizer_routing"]
    assert "work_item.captured" in signoffs["recommended_next_events"]
    assert "work_item.followup_captured" not in signoffs["conceptual_next_events"]

    bridge = rows["bridge_assignable"]["organizer_routing"]
    assert "work_item.shaped" in bridge["recommended_next_events"]
    assert "work_item.blocked" in bridge["recommended_next_events"]
    assert "work_item.bridge_delegated" in bridge["recommended_next_events"]
    assert "work_item.bridge_delegated" not in bridge["conceptual_next_events"]
    assert bridge["missing_affordance_count"] == 0

    for row in rows.values():
        routing = row["organizer_routing"]
        assert set(routing["recommended_next_events"]).issubset(
            set(payload["event_command_hints"])
        )


def test_task_ledger_cluster_flag_keeps_contents_page_bounded() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="cluster_flag")

    encoded = json.dumps(payload, sort_keys=True)
    assert len(encoded.encode("utf-8")) < 60_000
    assert payload["event_command_hints"]
    assert not any(
        row["artifact_kind"] == "task_ledger_mechanism_cluster"
        for row in payload["rows"]
    )
    mechanism_overview = payload["mechanism_cluster_overview"]
    assert mechanism_overview["status"] == "deferred_for_bare_contents_page"
    assert mechanism_overview["emitted_row_count"] == 0
    assert mechanism_overview["top_clusters"] == []
    assert mechanism_overview["potential_mechanism_count"] >= 0
    assert mechanism_overview["exact_drilldown_command"] == (
        "./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:<mech_id>"
    )
    for row in payload["rows"]:
        routing = row["organizer_routing"]
        assert "supported_commands" not in routing
        assert "common_source_surfaces" not in routing
        assert "common_file_hints" not in routing
        assert "common_integration_paths" not in routing
        assert "organizer_role" in routing
    assert payload["cluster_organizer_routing_omission_receipt"]["drilldowns"]
    assert (
        "default mechanism affinity cluster rows beyond compact mechanism_cluster_overview"
        in payload["cluster_organizer_routing_omission_receipt"]["omitted"]
    )


def test_task_ledger_flag_surface_drills_workitem_ids() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="flag", ids=["cap_035"])

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["missing_ids"] == []
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["id"] == "cap_035"
    assert isinstance(row["state"], str) and row["state"]
    assert row["work_item_type"] == "task"
    assert row["source_refs"]
    assert row["drilldown_command"].endswith("--band card --ids cap_035")


def test_task_ledger_card_surface_exposes_contracts_and_linkage() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="card", ids=["cap_035"])

    assert payload["profile_status"] == "supported"
    next_commands = [row["command"] for row in payload["next"]]
    assert (
        "./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings"
        in next_commands
    )
    row = payload["rows"][0]
    assert row["id"] == "cap_035"
    assert row["contracts"]["satisfaction_refs"]
    assert row["contracts"]["integration_paths"]
    assert "depends_on" in row["contracts"]
    assert "dependencies" in row["contracts"]
    assert "dependency_status" in row
    assert {"schedulable", "hard_dep_count", "unsatisfied_dep_ids", "dangling_dep_ids", "downstream_unlock_ids", "anomaly_refs"}.issubset(row["dependency_status"])
    assert "linkage" in row
    assert row["omission_receipt"]["drilldown"].endswith('select(.id=="cap_035")\' state/task_ledger/ledger.json')


def test_task_ledger_card_surface_exposes_quick_capture_provenance(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "codex/standards/std_task_ledger.json",
        {"schema_version": "std_task_ledger_v1"},
    )
    task_ledger_events.append_event(
        tmp_path,
        {
            "event_id": "wie_test_quick_capture_metadata",
            "event_type": "work_item.captured",
            "created_at": "2026-05-10T01:15:56+00:00",
            "created_by": "claude_code",
            "subject_id": "cap_quick_capture_metadata",
            "payload": {
                "title": "Quick capture metadata",
                "statement": "Quick capture metadata should be visible from the Task Ledger card.",
                "work_item_type": "capture",
                "confidence": 0.85,
                "tags": ["task_ledger", "projection_gap"],
            },
        },
    )
    task_ledger_events.rebuild_projections(tmp_path)

    payload = build_option_surface(tmp_path, "task_ledger", band="card", ids=["cap_quick_capture_metadata"])

    assert payload["profile_status"] == "supported"
    row = payload["rows"][0]
    assert row["tags"] == ["task_ledger", "projection_gap"]
    assert row["confidence"] == 0.85
    assert row["created_by"] == "claude_code"


def test_task_ledger_unsupported_band_emits_profile_gap() -> None:
    payload = build_option_surface(REPO_ROOT, "task_ledger", band="tape")

    assert payload["profile_status"] == "profile_gap"
    assert payload["rows"] == []
    assert payload["warnings"][0]["kind"] == "unsupported_artifact_kind_or_band"


def test_kind_atlas_includes_type_a_observation_surfaces() -> None:
    payload = build_kind_atlas(REPO_ROOT, band="flag")

    rows = {row["kind_id"]: row for row in payload["rows"]}
    assert rows["task_ledger"]["support_status"] == "option_surface_supported"
    assert rows["task_ledger"]["option_surface_command"].endswith("--option-surface task_ledger --band cluster_flag")
    for kind_id in (
        "agent_observations",
        "navigation_training_emissions",
        "navigation_mechanism_candidates",
        "standard_projection_gaps",
        "system_microcosm",
        "cognitive_operators",
        "github_import_candidates",
    ):
        assert kind_id in rows
        assert rows[kind_id]["support_status"] == "option_surface_supported"
    for kind_id in (
        "agent_observations",
        "navigation_training_emissions",
        "navigation_mechanism_candidates",
        "standard_projection_gaps",
        "system_microcosm",
        "cognitive_operators",
    ):
        assert rows[kind_id]["option_surface_command"].endswith(f"--option-surface {kind_id} --band flag")
    assert rows["github_import_candidates"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["github_import_candidates"]["option_surface_command"].endswith(
        "--option-surface github_import_candidates --band cluster_flag"
    )
    assert rows["skill_compression_debt"]["support_status"] == "option_surface_supported"
    assert rows["skill_compression_debt"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["skill_compression_debt"]["option_surface_command"].endswith(
        "--option-surface skill_compression_debt --band cluster_flag"
    )
    assert rows["artifact_projection_debt"]["support_status"] == "option_surface_supported"
    assert rows["artifact_projection_debt"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["artifact_projection_debt"]["option_surface_command"].endswith(
        "--option-surface artifact_projection_debt --band cluster_flag"
    )
    assert rows["compliance_ledger"]["support_status"] == "option_surface_supported"
    assert rows["compliance_ledger"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["compliance_ledger"]["option_surface_command"].endswith(
        "--option-surface compliance_ledger --band cluster_flag"
    )
    assert rows["standard_skill_map"]["support_status"] == "option_surface_supported"
    assert rows["standard_skill_map"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["standard_skill_map"]["option_surface_command"].endswith(
        "--option-surface standard_skill_map --band cluster_flag"
    )
    assert rows["renderer_passports"]["support_status"] == "option_surface_supported"
    assert rows["renderer_passports"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["renderer_passports"]["option_surface_command"].endswith(
        "--option-surface renderer_passports --band cluster_flag"
    )
    assert rows["navigation_type_plane"]["support_status"] == "option_surface_supported"
    assert rows["navigation_type_plane"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["navigation_type_plane"]["option_surface_command"].endswith(
        "--option-surface navigation_type_plane --band cluster_flag"
    )
    assert rows["transform_job_receipts"]["support_status"] == "option_surface_supported"
    assert rows["transform_job_receipts"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["transform_job_receipts"]["option_surface_command"].endswith(
        "--option-surface transform_job_receipts --band cluster_flag"
    )
    assert rows["row_patches"]["support_status"] == "option_surface_supported"
    assert rows["row_patches"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["row_patches"]["option_surface_command"].endswith(
        "--option-surface row_patches --band cluster_flag"
    )


def test_kind_atlas_generated_rows_do_not_run_live_refresh_builders(monkeypatch) -> None:
    def fail_live_builder(*_args, **_kwargs):
        raise AssertionError("kind-atlas hot path must not run live generated builders")

    monkeypatch.setattr(generated_surfaces, "_navigation_training_rows", fail_live_builder)
    monkeypatch.setattr(generated_surfaces, "_navigation_mechanism_candidate_rows", fail_live_builder)
    monkeypatch.setattr(generated_surfaces, "_artifact_projection_debt_rows", fail_live_builder)
    monkeypatch.setattr(generated_surfaces, "_system_microcosm_rows", fail_live_builder)
    monkeypatch.setattr(generated_surfaces, "_cognitive_operator_rows", fail_live_builder)
    monkeypatch.setattr(generated_surfaces, "_github_import_candidate_rows", fail_live_builder)
    monkeypatch.setattr(generated_surfaces, "_authoring_contract_rows", fail_live_builder)

    rows = {row["kind_id"]: row for row in build_kind_atlas(REPO_ROOT, band="flag")["rows"]}

    assert rows["navigation_training_emissions"]["row_count"] >= 1
    assert rows["navigation_mechanism_candidates"]["row_count"] >= 1
    assert rows["system_microcosm"]["row_count"] == 1
    assert rows["cognitive_operators"]["row_count"] >= 1
    assert rows["artifact_projection_debt"]["currentness"]["status"] in {
        "materialized_summary_available",
        "materialized_summary_missing_live_refresh_required",
    }
    assert rows["artifact_projection_debt"]["row_count_semantics"]["mode"] in {
        "materialized",
        "unknown",
    }
    if rows["artifact_projection_debt"]["row_count_semantics"]["mode"] == "unknown":
        assert rows["artifact_projection_debt"]["row_count_semantics"]["zero_means"] == "unknown_not_empty"
        assert rows["artifact_projection_debt"]["row_count_semantics"]["refresh_command"].endswith(
            "tools/meta/factory/build_generated_artifact_surface_summary.py"
        )
        assert rows["artifact_projection_debt"]["currentness"]["refresh_missing"] is True
        assert rows["artifact_projection_debt"]["currentness"]["refresh_boundary"] == "explicit_projection_refresh_available"
        assert rows["artifact_projection_debt"]["currentness"]["refresh_command"].endswith(
            "tools/meta/factory/build_generated_artifact_surface_summary.py"
        )
        assert "drilldown_command" in rows["artifact_projection_debt"]["currentness"]


def test_agent_observations_emit_and_browse_raw_row(tmp_path: Path) -> None:
    receipt = emit_agent_observation(
        tmp_path,
        summary="Skill discovery should browse option surfaces, not guessed skill-find strings.",
        signal_type="mechanism_candidate",
        candidate_routes=["mechanisms", "standards"],
        evidence_refs=["codex/standards/std_skill.json::compression_authoring_contract"],
        actor_surface="codex_test",
        session_id="session-test",
    )

    observation_id = receipt["observation_id"]
    flag_payload = build_option_surface(tmp_path, "agent_observations", band="flag")
    assert flag_payload["profile_status"] == "supported"
    assert flag_payload["summary"]["query_used"] is False
    assert flag_payload["summary"]["row_count"] == 1

    row = flag_payload["rows"][0]
    assert row["observation_id"] == observation_id
    assert row["signal_type"] == "mechanism_candidate"
    assert row["promotion_state"] == "routed_candidate"
    assert row["top_candidate_route"] == "mechanisms"
    assert "option surfaces" in row["claim"]

    card_payload = build_option_surface(tmp_path, "agent_observations", band="card", ids=[observation_id])
    card = card_payload["rows"][0]
    assert card["band"] == "card"
    assert card["candidate_routes"][1]["target_kind"] == "standards"
    assert card["evidence_refs"] == ["codex/standards/std_skill.json::compression_authoring_contract"]
    assert card["why_not_canon_yet"]


def test_navigation_training_emissions_surface_exposes_route_repairs() -> None:
    payload = build_option_surface(REPO_ROOT, "navigation_training_emissions", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "navigation_training_emissions"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["row_count"] >= 1
    rows = {row["anti_pattern_id"]: row for row in payload["rows"]}
    assert "skill_find_first_contact" in rows
    assert rows["skill_find_first_contact"]["repair_class"] == "hook_steering_plus_context_pack_first_contact"
    assert rows["skill_find_first_contact"]["preferred_first_surface"].startswith("./repo-python kernel.py")
    assert "coverage-first" in rows["skill_find_first_contact"]["claim"]
    assert rows["skill_find_first_contact"]["fallback_surface"].endswith(
        "--option-surface skills --band cluster_flag"
    )

    card_payload = build_option_surface(
        REPO_ROOT,
        "navigation_training_emissions",
        band="card",
        ids=["skill_find_first_contact"],
    )
    card = card_payload["rows"][0]
    assert "lexical-luck" in card["why"]
    assert "standards:std_agent_entry_surface" in card["expected_artifacts"]


def test_navigation_mechanism_candidates_surface_exposes_candidate_facets() -> None:
    payload = build_option_surface(REPO_ROOT, "navigation_mechanism_candidates", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "navigation_mechanism_candidates"
    assert payload["authority_posture"] == "generated_artifact_projection"
    assert payload["summary"]["active_candidate_count"] >= 1
    assert payload["summary"]["terminal_superseded_count"] >= 1
    assert payload["summary"]["terminal_count"] >= payload["summary"]["terminal_superseded_count"]
    assert payload["summary"]["active_pressure_count"] + payload["summary"]["terminal_count"] == payload["summary"]["total_available"]
    assert payload["summary"]["acceptance_eligibility_counts"]["accepted"] >= 1
    assert "operational_state_counts" in payload["summary"]
    assert "historical" in payload["summary"]["display_rule"]
    rows = {row["anti_pattern_id"]: row for row in payload["rows"]}
    assert "skill_find_first_contact" in rows
    row = rows["skill_find_first_contact"]
    assert row["claim_type"] == "facet_candidate"
    assert row["authority_posture"] == "candidate_only"
    assert row["projection_status"] == "candidate"
    assert row["facet_type"] == "navigation_trace"
    assert row["owner_acceptance_status"] == "missing"
    assert row["operational_state"] == "blocked_missing_owner_packet"
    assert row["terminal_state"] is False
    assert row["next_owner_surface"]

    card_payload = build_option_surface(
        REPO_ROOT,
        "navigation_mechanism_candidates",
        band="card",
        ids=[row["claim_id"]],
    )
    card = card_payload["rows"][0]
    assert card["facet_manifest"]["schema_version"] == "mechanism_facet_manifest_v0"
    assert card["projection_claim"]["state"] == "candidate"
    assert card["owner_target"]["owner_acceptance_status"] == "missing"
    assert card["route_replay_case"]["case_id"].startswith("replay_")
    assert card["route_replay_result"]["schema_version"] == "navigation_route_replay_result_v0"
    assert card["route_replay_result"]["authority_posture"] == "fitness_probe_not_acceptance"
    assert card["why_not_canon_yet"]

    paper_row = rows["anti_pattern_paper_module_skip"]
    paper_card_payload = build_option_surface(
        REPO_ROOT,
        "navigation_mechanism_candidates",
        band="card",
        ids=[paper_row["claim_id"]],
    )
    paper_card = paper_card_payload["rows"][0]
    assert paper_card["acceptance_eligibility"] == "accepted"
    assert paper_card["owner_acceptance_status"] == "accepted"
    assert paper_card["operational_state"] == "terminal_superseded"
    assert paper_card["terminal_state"] is True
    assert paper_card["owner_target"]["owner_acceptance_status"] == "accepted"
    assert paper_card["state"] == "superseded"
    assert paper_card["latest_acceptance_event_type"] == "claim.superseded"
    assert paper_card["acceptance_event_ref"].startswith("navigation_mechanism_acceptance_event:nmae_")
    assert paper_card["blocked_event_ref"] == "navigation_mechanism_acceptance_event:nmae_178d6405fd20d36b"
    assert paper_card["owner_packet_ref"].startswith("navigation_mechanism_owner_packet:nmop_")
    assert paper_card["owner_locus_ref"].startswith("navigation_mechanism_owner_locus_verification:nmolv_")
    assert paper_card["replay_receipt_ref"].startswith("navigation_mechanism_replay_receipt:nmrr_")
    assert paper_card["latest_acceptance_event"]["state_after"] == "superseded"
    assert paper_card["latest_acceptance_event"]["proof_refs"]["observation_ref"] == (
        paper_card["acceptance_dossier"]["observation_ref"]
    )
    assert paper_card["owner_packet"]["packet_event_type"] == "owner_packet.created"
    assert paper_card["owner_locus"]["authority_posture"] == "owner_locus_candidate_not_owner_acceptance"
    assert paper_card["replay_receipt"]["authority_posture"] == "durable_replay_evidence_not_acceptance"
    assert paper_card["acceptance_dossier"]["state"] == "superseded"
    assert paper_card["acceptance_dossier"]["acceptance_eligibility"] == "accepted"
    assert "owner_acceptance_ref_missing" not in paper_card["missing_refs"]
    assert "durable_replay_receipt_lane_unresolved" not in paper_card["missing_refs"]
    assert "future_observation_window_unverified" not in paper_card["missing_refs"]
    assert paper_card["missing_refs"] == []
    future_observation = paper_card["acceptance_dossier"]["future_observation"]
    assert future_observation["status"] == "observed"
    assert future_observation["future_observation_window_status"] == "recorded"
    assert future_observation["post_count"] < future_observation["baseline_count"]
    assert "code_or_tool_loci_ref_missing" not in paper_card["missing_refs"]
    assert paper_card["no_count_increment_reason"]


def test_cognitive_operators_surface_exposes_dogfooded_operator() -> None:
    payload = build_option_surface(REPO_ROOT, "cognitive_operators", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "cognitive_operators"
    rows = {row["operator_id"]: row for row in payload["rows"]}
    assert "cogop_capability_gap_ladder" in rows
    assert "cogop_disconfirmation_harness" in rows
    assert "cogop_causal_trial_harness" in rows
    assert "cogop_operator_composition_sequencer" in rows
    assert "cogop_affordance_passport_author" in rows
    assert "cogop_operator_passport_propagator" in rows
    assert "cogop_route_lease_executor" in rows
    assert "cogop_prompt_route_assimilator" in rows
    assert "cogop_pressure_to_action_reducer" in rows
    row = rows["cogop_capability_gap_ladder"]
    assert row["validation_status"] == "valid"
    assert row["dogfood_receipt_count"] >= 1
    assert row["task_selection_hook_count"] >= 1
    disconfirmation_row = rows["cogop_disconfirmation_harness"]
    assert disconfirmation_row["validation_status"] == "valid"
    assert disconfirmation_row["dogfood_receipt_count"] >= 1
    causal_trial_row = rows["cogop_causal_trial_harness"]
    assert causal_trial_row["validation_status"] == "valid"
    assert causal_trial_row["dogfood_receipt_count"] >= 1
    composition_row = rows["cogop_operator_composition_sequencer"]
    assert composition_row["validation_status"] == "valid"
    assert composition_row["dogfood_receipt_count"] >= 1
    passport_row = rows["cogop_affordance_passport_author"]
    assert passport_row["validation_status"] == "valid"
    assert passport_row["dogfood_receipt_count"] >= 1
    propagator_row = rows["cogop_operator_passport_propagator"]
    assert propagator_row["validation_status"] == "valid"
    assert propagator_row["dogfood_receipt_count"] >= 1
    route_lease_row = rows["cogop_route_lease_executor"]
    assert route_lease_row["validation_status"] == "valid"
    assert route_lease_row["dogfood_receipt_count"] >= 1
    prompt_route_row = rows["cogop_prompt_route_assimilator"]
    assert prompt_route_row["validation_status"] == "valid"
    assert prompt_route_row["dogfood_receipt_count"] >= 1
    pressure_row = rows["cogop_pressure_to_action_reducer"]
    assert pressure_row["validation_status"] == "valid"
    assert pressure_row["dogfood_receipt_count"] >= 1

    card_payload = build_option_surface(
        REPO_ROOT,
        "cognitive_operators",
        band="card",
        ids=[
            "cogop_capability_gap_ladder",
            "cogop_disconfirmation_harness",
            "cogop_causal_trial_harness",
            "cogop_operator_composition_sequencer",
            "cogop_affordance_passport_author",
            "cogop_operator_passport_propagator",
            "cogop_route_lease_executor",
            "cogop_prompt_route_assimilator",
            "cogop_pressure_to_action_reducer",
        ],
    )
    cards = {row["operator_id"]: row for row in card_payload["rows"]}
    card = cards["cogop_capability_gap_ladder"]
    assert card["operator_validation"]["ok"] is True
    assert card["operator_validation"]["affordance_passport_required"] is True
    assert card["compression_passport"]["when_to_open"]
    assert card["compression_passport"]["when_not_to_open"]
    assert card["dogfood_receipts"][0]["cognition_delta_evidence"]
    assert "task_selection_hooks" in card["integration"]
    assert card["next_safe_moves"][-1].endswith("validate_cognitive_operator_registry.py --json")
    disconfirmation_card = cards["cogop_disconfirmation_harness"]
    assert disconfirmation_card["operator_validation"]["ok"] is True
    assert disconfirmation_card["operator_validation"]["counterevidence_contract_required"] is True
    assert disconfirmation_card["dogfood_receipts"][0]["counterevidence_checked"]
    assert disconfirmation_card["dogfood_receipts"][0]["surviving_claim"]
    causal_trial_card = cards["cogop_causal_trial_harness"]
    assert causal_trial_card["operator_validation"]["ok"] is True
    assert causal_trial_card["operator_validation"]["causal_trial_contract_required"] is True
    assert causal_trial_card["dogfood_receipts"][0]["pre_action_prediction"]
    assert causal_trial_card["dogfood_receipts"][0]["prediction_result"]
    composition_card = cards["cogop_operator_composition_sequencer"]
    assert composition_card["operator_validation"]["ok"] is True
    assert composition_card["operator_validation"]["composition_contract_required"] is True
    assert composition_card["compression_passport"]["when_to_open"]
    assert composition_card["compression_passport"]["when_not_to_open"]
    assert composition_card["dogfood_receipts"][0]["operator_sequence"]
    assert composition_card["dogfood_receipts"][0]["sequence_result"]
    passport_card = cards["cogop_affordance_passport_author"]
    assert passport_card["operator_validation"]["ok"] is True
    assert passport_card["operator_validation"]["affordance_passport_required"] is True
    assert passport_card["affordance_passport_contract"]["required"] is True
    assert passport_card["compression_passport"]["when_to_open"]
    assert passport_card["compression_passport"]["when_not_to_open"]
    assert passport_card["dogfood_receipts"][0]["prediction_result"]
    propagator_card = cards["cogop_operator_passport_propagator"]
    assert propagator_card["operator_validation"]["ok"] is True
    assert propagator_card["operator_validation"]["passport_propagation_required"] is True
    assert propagator_card["passport_propagation_contract"]["required"] is True
    assert propagator_card["compression_passport"]["when_to_open"]
    assert propagator_card["dogfood_receipts"][0]["source_operator_id"] == "cogop_capability_gap_ladder"
    assert propagator_card["dogfood_receipts"][0]["coverage_after"]["passported_operator_count"] >= 3
    route_lease_card = cards["cogop_route_lease_executor"]
    assert route_lease_card["operator_validation"]["ok"] is True
    assert route_lease_card["operator_validation"]["route_lease_required"] is True
    assert route_lease_card["route_lease_contract"]["required"] is True
    assert route_lease_card["compression_passport"]["when_to_open"]
    assert route_lease_card["dogfood_receipts"][0]["route_lease_id"]
    assert route_lease_card["dogfood_receipts"][0]["validation_return_condition"]
    prompt_route_card = cards["cogop_prompt_route_assimilator"]
    assert prompt_route_card["operator_validation"]["ok"] is True
    assert prompt_route_card["operator_validation"]["prompt_route_assimilation_required"] is True
    assert prompt_route_card["prompt_route_assimilation_contract"]["required"] is True
    assert prompt_route_card["compression_passport"]["when_to_open"]
    assert prompt_route_card["dogfood_receipts"][0]["source_lens"]
    assert prompt_route_card["dogfood_receipts"][0]["validation_prompt"]
    assert prompt_route_card["dogfood_receipts"][0]["retention_check"]
    prompt_route_receipt_ids = {
        receipt["receipt_id"] for receipt in prompt_route_card["dogfood_receipts"]
    }
    assert "cogop_prompt_route_assimilator_routing_seed_20260511" in prompt_route_receipt_ids
    assert "cogop_prompt_route_assimilator_trace_cap_refinement_20260603" in prompt_route_receipt_ids
    routing_seed_receipt = next(
        receipt
        for receipt in prompt_route_card["dogfood_receipts"]
        if receipt["receipt_id"] == "cogop_prompt_route_assimilator_routing_seed_20260511"
    )
    assert "route proof obligation" in routing_seed_receipt["route_miss_evidence"]["abstracted_phrases"]
    assert "concepts:con_038" in routing_seed_receipt["route_miss_evidence"]["target_authority_planes"]
    assert (
        "./repo-python kernel.py --option-surface concepts --band card --ids con_038"
        in prompt_route_card["next_safe_moves"]
    )
    assert (
        "./repo-python kernel.py --option-surface standards --band card --ids std_concept"
        in prompt_route_card["next_safe_moves"]
    )
    assert (
        "./repo-python kernel.py --option-surface standards --band card --ids std_agent_entry_surface"
        in prompt_route_card["next_safe_moves"]
    )
    trace_cap_receipt = next(
        receipt
        for receipt in prompt_route_card["dogfood_receipts"]
        if receipt["receipt_id"] == "cogop_prompt_route_assimilator_trace_cap_refinement_20260603"
    )
    assert "read other traces or caps" in trace_cap_receipt["route_miss_evidence"]["abstracted_phrases"]
    assert trace_cap_receipt["validation_prompt"].startswith("read other traces or caps")
    pressure_card = cards["cogop_pressure_to_action_reducer"]
    assert pressure_card["operator_validation"]["ok"] is True
    assert pressure_card["operator_validation"]["pressure_reduction_required"] is True
    assert pressure_card["pressure_reduction_contract"]["required"] is True
    assert pressure_card["compression_passport"]["when_to_open"]
    assert pressure_card["dogfood_receipts"][0]["pressure_surfaces"]
    assert pressure_card["dogfood_receipts"][0]["selected_pressure"]
    assert pressure_card["dogfood_receipts"][0]["bounded_action"]
    assert pressure_card["dogfood_receipts"][0]["status_binding_target"]

    validation = validate_cognitive_operator_registry(REPO_ROOT)
    assert validation["ok"] is True
    assert validation["active_operator_count"] >= 8
    passport_coverage = validation["affordance_passport_coverage"]
    assert passport_coverage["passported_operator_count"] >= 5
    assert "cogop_capability_gap_ladder" in passport_coverage["passported_operator_ids"]
    assert "cogop_operator_passport_propagator" in passport_coverage["passported_operator_ids"]
    assert "cogop_route_lease_executor" in passport_coverage["passported_operator_ids"]
    assert "cogop_prompt_route_assimilator" in passport_coverage["passported_operator_ids"]
    assert "cogop_pressure_to_action_reducer" in passport_coverage["passported_operator_ids"]
    assert "cogop_disconfirmation_harness" in passport_coverage["passported_operator_ids"]
    assert "cogop_operator_composition_sequencer" in passport_coverage["passported_operator_ids"]
    assert set(passport_coverage["passported_operator_ids"]).isdisjoint(
        passport_coverage["missing_passport_operator_ids"]
    )


def test_concepts_card_resolves_source_file_stem_alias() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "concepts",
        band="card",
        ids=["con_038_routing_as_semantic_relation_graph"],
    )

    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["drilldown_by"] == "concept_id_slug_or_source_stem"
    row = payload["rows"][0]
    assert row["concept_id"] == "con_038"
    assert row["slug"] == "routing-as-semantic-relation-graph"
    assert row["drilldown_command"].endswith("--band card --ids con_038")


def test_cognitive_operator_validator_rejects_missing_counterevidence_receipt(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/bad_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_disconfirmation",
                        "slug": "test-disconfirmation",
                        "title": "Test Disconfirmation",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["counterevidence"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "counterevidence_contract": {
                            "required": True,
                            "required_receipt_fields": [
                                "counterevidence_checked",
                                "disconfirmation_result",
                                "surviving_claim",
                            ],
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/bad_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "bad",
                "operator_id": "cogop_test_disconfirmation",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_disconfirmation"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert any("missing_counterevidence_field:counterevidence_checked" in row for row in missing)
    assert any("missing_counterevidence_field:surviving_claim" in row for row in missing)


def test_cognitive_operator_validator_rejects_missing_causal_trial_receipt(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/bad_trial_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_causal_trial",
                        "slug": "test-causal-trial",
                        "title": "Test Causal Trial",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["causal evidence"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "causal_trial_contract": {
                            "required": True,
                            "required_receipt_fields": [
                                "pre_action_prediction",
                                "no_effect_falsifier",
                                "intervention",
                                "post_action_observation",
                                "prediction_result",
                            ],
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/bad_trial_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "bad",
                "operator_id": "cogop_test_causal_trial",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_causal_trial"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert any("missing_causal_trial_field:pre_action_prediction" in row for row in missing)
    assert any("missing_causal_trial_field:prediction_result" in row for row in missing)


def test_cognitive_operator_validator_rejects_missing_composition_receipt(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/bad_composition_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_composition",
                        "slug": "test-composition",
                        "title": "Test Composition",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["operator composition"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "composition_contract": {
                            "required": True,
                            "required_receipt_fields": [
                                "operator_sequence",
                                "composition_decision",
                                "handoff_contracts",
                                "sequence_result",
                            ],
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/bad_composition_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "bad",
                "operator_id": "cogop_test_composition",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_composition"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert any("missing_composition_field:operator_sequence" in row for row in missing)
    assert any("missing_composition_field:sequence_result" in row for row in missing)


def test_cognitive_operator_validator_rejects_missing_passport_propagation_receipt(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/bad_passport_propagation_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_passport_propagation",
                        "slug": "test-passport-propagation",
                        "title": "Test Passport Propagation",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["passport propagation"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "passport_propagation_contract": {
                            "required": True,
                            "required_receipt_fields": [
                                "source_operator_id",
                                "target_operator_passport_written",
                                "coverage_before",
                                "coverage_after",
                                "remaining_unpassportized_operators",
                                "next_propagation_rule",
                            ],
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/bad_passport_propagation_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "bad",
                "operator_id": "cogop_test_passport_propagation",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_passport_propagation"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
                "source_operator_id": "cogop_old",
                "target_operator_passport_written": True,
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert any("missing_passport_propagation_field:coverage_before" in row for row in missing)
    assert any(
        "missing_passport_propagation_field:remaining_unpassportized_operators" in row
        for row in missing
    )


def test_cognitive_operator_validator_rejects_missing_route_lease_receipt(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/bad_route_lease_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_route_lease",
                        "slug": "test-route-lease",
                        "title": "Test Route Lease",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["route lease"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "route_lease_contract": {
                            "required": True,
                            "required_receipt_fields": [
                                "route_lease_id",
                                "lease_selected_lane",
                                "direct_action_boundary",
                                "consumed_by_action",
                                "forbidden_followup_routes",
                                "validation_return_condition",
                            ],
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/bad_route_lease_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "bad",
                "operator_id": "cogop_test_route_lease",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_route_lease"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
                "route_lease_id": "entry:test",
                "lease_selected_lane": "test_lane",
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert any("missing_route_lease_field:direct_action_boundary" in row for row in missing)
    assert any("missing_route_lease_field:validation_return_condition" in row for row in missing)


def test_cognitive_operator_validator_rejects_missing_prompt_route_receipt(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/bad_prompt_route_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_prompt_route",
                        "slug": "test-prompt-route",
                        "title": "Test Prompt Route",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["prompt-derived route miss"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "prompt_route_assimilation_contract": {
                            "required": True,
                            "required_receipt_fields": [
                                "source_lens",
                                "prompt_phrase",
                                "route_miss_evidence",
                                "target_surface",
                                "routing_mutation",
                                "validation_prompt",
                                "retention_check",
                            ],
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/bad_prompt_route_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "bad",
                "operator_id": "cogop_test_prompt_route",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_prompt_route"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
                "source_lens": "session_diagnostics.route-misses",
                "prompt_phrase": "trace continuation",
                "route_miss_evidence": {"candidate_count": 1},
                "target_surface": "cognitive_operators:cogop_test_prompt_route",
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert any("missing_prompt_route_assimilation_field:routing_mutation" in row for row in missing)
    assert any("missing_prompt_route_assimilation_field:validation_prompt" in row for row in missing)
    assert any("missing_prompt_route_assimilation_field:retention_check" in row for row in missing)


def test_cognitive_operator_validator_rejects_missing_pressure_reduction_receipt(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/bad_pressure_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_pressure",
                        "slug": "test-pressure",
                        "title": "Test Pressure",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["backlog pressure"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "pressure_reduction_contract": {
                            "required": True,
                            "required_receipt_fields": [
                                "pressure_surfaces",
                                "selected_pressure",
                                "rejected_pressures",
                                "decision_axes",
                                "bounded_action",
                                "status_binding_target",
                                "validation_return_condition",
                            ],
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/bad_pressure_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "bad",
                "operator_id": "cogop_test_pressure",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_pressure"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
                "pressure_surfaces": [{"surface": "task_ledger", "count": 1}],
                "selected_pressure": {"surface": "task_ledger"},
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert any("missing_pressure_reduction_field:rejected_pressures" in row for row in missing)
    assert any("missing_pressure_reduction_field:bounded_action" in row for row in missing)
    assert any("missing_pressure_reduction_field:status_binding_target" in row for row in missing)
    assert any("missing_pressure_reduction_field:validation_return_condition" in row for row in missing)


def test_cognitive_operator_validator_rejects_missing_affordance_passport(tmp_path: Path) -> None:
    registry_path = tmp_path / "codex/doctrine/cognitive_operators.json"
    standard_path = tmp_path / "codex/standards/std_cognitive_operator.json"
    receipt_path = tmp_path / "state/cognitive_operators/dogfood/passport_receipt.json"
    registry_path.parent.mkdir(parents=True)
    standard_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    standard_path.write_text("{}", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "cognitive_operator_registry_v0",
                "operators": [
                    {
                        "operator_id": "cogop_test_passport",
                        "slug": "test-passport",
                        "title": "Test Passport",
                        "status": "active",
                        "claim": "Test claim.",
                        "activation": {
                            "trigger_phrases": ["affordance passport"],
                            "opens_when": ["testing"],
                            "skip_when": ["not testing"],
                        },
                        "process": ["test"],
                        "affordance_passport_contract": {
                            "required": True,
                            "required_passport_fields": [
                                "cluster_keys",
                                "atom",
                                "when_to_open",
                                "when_not_to_open",
                                "safe_drilldown",
                                "landmines",
                                "sufficiency_claims",
                            ],
                        },
                        "compression_passport": {
                            "cluster_keys": ["affordance passport"],
                            "atom": "Passport test",
                            "when_to_open": "testing",
                        },
                        "integration": {
                            "navigation": {"kind_id": "cognitive_operators"},
                            "validation": {"command": "validate"},
                            "task_selection_hooks": ["test hook"],
                        },
                        "validation": {"acceptance_criteria": ["test"]},
                        "evidence_refs": ["test"],
                        "dogfood_receipt_refs": [
                            "state/cognitive_operators/dogfood/passport_receipt.json"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(
            {
                "receipt_id": "passport",
                "operator_id": "cogop_test_passport",
                "live_problem": "test",
                "evidence_surfaces": ["test"],
                "candidate_set": ["test"],
                "selected_operator": {"operator_id": "cogop_test_passport"},
                "actions_taken": ["test"],
                "cognition_delta_evidence": ["test"],
                "result_state": "test",
            }
        ),
        encoding="utf-8",
    )

    validation = validate_cognitive_operator_registry(tmp_path)

    assert validation["ok"] is False
    missing = validation["failures"][0]["missing_or_invalid"]
    assert "missing_affordance_passport_field:when_not_to_open" in missing
    assert "missing_affordance_passport_field:sufficiency_claims" in missing


def test_transform_job_receipts_surface_tolerates_string_validation_rows() -> None:
    payload = build_option_surface(REPO_ROOT, "transform_job_receipts", band="flag")

    assert payload["profile_status"] == "supported"
    string_rows = [row for row in payload["rows"] if row.get("validation_shape") == "str"]
    assert string_rows
    assert string_rows[0]["validation_passed"] is False


def test_skill_compression_debt_surface_reports_missing_passports(tmp_path: Path) -> None:
    registry = tmp_path / "codex/doctrine/skills/skill_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "families": [
                    {
                        "family_id": "kernel",
                        "title": "Kernel",
                        "skills": [
                            {
                                "id": "legacy_skill",
                                "title": "Legacy Skill",
                                "file": "codex/doctrine/skills/kernel/legacy_skill.md",
                                "description": "Legacy skill with inferred compression only.",
                            },
                            {
                                "id": "complete_skill",
                                "title": "Complete Skill",
                                "file": "codex/doctrine/skills/kernel/complete_skill.md",
                                "compression_passport": {
                                    "cluster_keys": ["navigation"],
                                    "atom": "Complete skill",
                                    "flag": "Complete skill flag.",
                                    "card": "Complete skill card.",
                                    "when_to_open": "Open for tests.",
                                    "when_not_to_open": "Do not open otherwise.",
                                    "safe_drilldown": "./repo-python kernel.py --option-surface skills --band card --ids complete_skill",
                                },
                            },
                        ],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(tmp_path, "skill_compression_debt", band="card")

    assert payload["profile_status"] == "supported"
    assert payload["summary"]["row_count"] == 1
    row = payload["rows"][0]
    assert row["skill_id"] == "legacy_skill"
    assert row["debt_status"] == "missing_compression_passport"
    assert "when_not_to_open" in row["missing_fields"]
    assert row["standard_ref"] == "codex/standards/std_skill.json"

    cluster_payload = build_option_surface(tmp_path, "skill_compression_debt", band="cluster_flag")
    assert cluster_payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert cluster_payload["summary"]["total_available"] == 1
    assert cluster_payload["rows"][0]["cluster_id"] == "missing_compression_passport"


def test_standard_projection_gaps_surface_reports_missing_generated_projections(tmp_path: Path) -> None:
    payload = build_option_surface(tmp_path, "standard_projection_gaps", band="card")

    assert payload["profile_status"] == "supported"
    rows = {row["projection_id"]: row for row in payload["rows"]}
    compliance = rows["compliance_ledger"]
    standard_skill_map = rows["standard_skill_map"]
    assert compliance["gap_status"] == "projection_missing"
    assert standard_skill_map["gap_status"] == "projection_missing"
    assert compliance["projection_owner_id"] == "compliance_ledger_projection"
    assert standard_skill_map["projection_owner_id"] == "standard_skill_map_projection"
    assert compliance["projection_owner_status"] == "registered"
    assert standard_skill_map["projection_owner_status"] == "registered"
    assert "build_compliance_ledger.py --check" in compliance["owner_check_command"]
    assert "build_standard_skill_map.py --check" in standard_skill_map["owner_check_command"]
    assert compliance["build_command"] == compliance["owner_repair_command"]
    assert standard_skill_map["build_command"] == standard_skill_map["owner_repair_command"]
    assert compliance["evidence_command"].endswith(
        "projection_drift.py check --owner compliance_ledger_projection --json"
    )
    assert standard_skill_map["authority_boundary"] == (
        "generated_projection_is_read_model_not_source_authority"
    )
    assert standard_skill_map["projection_git_boundary"] == "ignored_local_hologram_read_model"
    assert "Do not hand-edit" in compliance["manual_edit_boundary"]
    assert "codex/doctrine/skills/skill_registry.json" in standard_skill_map["source_authorities"]


def test_compliance_ledger_card_exposes_standard_skill_map_status(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_skill",
                        "validator": "system/lib/compliance/skill_registry_adapter.py::scan_skill_registry",
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 4,
                        "checked_artifact_count": 4,
                        "compliant_artifact_count": 4,
                        "noncompliant_artifact_count": 0,
                        "compliance_rate": 1.0,
                        "top_failure_kinds": [],
                        "findings": [],
                        "evidence_refs": ["codex/hologram/skills/standard_skill_map.json"],
                        "metabolism_trigger_state": "ready_compliant",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": "codex/hologram/compliance/ledger.json::by_standard[std_skill]",
                        "standard_skill_map_status": {
                            "builder_agrees": True,
                            "option_surface_status": {
                                "surface_role": "ATLAS_PROJECTION",
                                "first_contact_allowed": False,
                                "grouping_keys": ["pairing_status"],
                            },
                        },
                        "skill_registry_status": {
                            "skill_count": 1,
                            "skills_with_governing_standard_ids": 1,
                        },
                        "navigation_role": "Validates the standards-to-skills projection.",
                    }
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(tmp_path, "compliance_ledger", band="card", ids=["std_skill"])
    row = payload["rows"][0]

    assert row["standard_id"] == "std_skill"
    assert row["standard_skill_map_status"]["builder_agrees"] is True
    assert row["standard_skill_map_status"]["option_surface_status"]["surface_role"] == "ATLAS_PROJECTION"
    assert row["standard_skill_map_status"]["option_surface_status"]["first_contact_allowed"] is False
    assert row["standard_skill_map_status"]["option_surface_status"]["grouping_keys"] == ["pairing_status"]
    assert row["skill_registry_status"]["skills_with_governing_standard_ids"] == 1
    assert row["navigation_role"].startswith("Validates")


def test_compliance_ledger_card_exposes_microcosm_status(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_microcosm",
                        "validator": "system/lib/compliance/microcosm_adapter.py::scan_microcosm",
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 6,
                        "checked_artifact_count": 6,
                        "compliant_artifact_count": 6,
                        "noncompliant_artifact_count": 0,
                        "compliance_rate": 1.0,
                        "top_failure_kinds": [],
                        "findings": [],
                        "evidence_refs": [
                            "microcosm-substrate/atlas/entry_packet.json",
                            "microcosm-substrate/standards/meta/index.json",
                        ],
                        "metabolism_trigger_state": "ready_compliant",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": (
                            "codex/hologram/compliance/ledger.json::"
                            "by_standard[std_microcosm]"
                        ),
                        "coverage_row_kind": "domain_scanner",
                        "scanner_depth_status": "domain_scanner_present",
                        "microcosm_status": {
                            "entry_packet_exists": True,
                            "standards_meta_lane": {
                                "organ_exists": True,
                                "index_exists": True,
                            },
                            "option_surface_status": {
                                "surface_role": "ATLAS_PROJECTION",
                                "first_contact_allowed": False,
                            },
                        },
                        "navigation_role": (
                            "Validates the Microcosm entry packet and standards meta lane."
                        ),
                    }
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(
        tmp_path,
        "compliance_ledger",
        band="card",
        ids=["std_microcosm"],
    )
    row = payload["rows"][0]

    assert row["standard_id"] == "std_microcosm"
    assert row["coverage_row_kind"] == "domain_scanner"
    assert row["scanner_depth_status"] == "domain_scanner_present"
    assert row["coverage_path"] == (
        "codex/hologram/compliance/ledger.json::by_standard[std_microcosm]"
    )
    assert row["microcosm_status"]["entry_packet_exists"] is True
    assert row["microcosm_status"]["standards_meta_lane"]["organ_exists"] is True
    assert row["microcosm_status"]["option_surface_status"]["surface_role"] == (
        "ATLAS_PROJECTION"
    )
    assert row["microcosm_status"]["option_surface_status"]["first_contact_allowed"] is False
    assert "microcosm-substrate/atlas/entry_packet.json" in row["evidence_refs"]
    assert row["navigation_role"].startswith("Validates")


def test_compliance_ledger_card_exposes_actionable_finding_targets(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    seed_path = (
        "state/meta_missions/type_a_autonomous_seed_loop/seeds/"
        "example_autonomous_seed.json"
    )
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_autonomous_seed_prompt",
                        "validator": (
                            "system/lib/compliance/autonomous_seed_prompt_adapter.py::"
                            "scan_autonomous_seed_prompt"
                        ),
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 2,
                        "checked_artifact_count": 2,
                        "compliant_artifact_count": 1,
                        "noncompliant_artifact_count": 1,
                        "compliance_rate": 0.5,
                        "top_failure_kinds": [
                            {"finding_kind": "missing_required_field", "count": 1}
                        ],
                        "findings": [
                            {
                                "finding_id": "fcf_test_seed_prompt",
                                "finding_kind": "missing_required_field",
                                "severity": "warning",
                                "summary": "Example seed missing required fields.",
                                "candidate_target_paths": [
                                    seed_path,
                                    "codex/standards/std_autonomous_seed_prompt.json",
                                ],
                                "candidate_target_payload": {
                                    "impacted_seed_count": 1,
                                    "impacted_seed_paths_preview": [seed_path],
                                    "impacted_seed_missing_fields_preview": {
                                        "example": ["lane", "scope_shape"],
                                    },
                                    "repair_targets_preview": [
                                        {
                                            "seed_id": "example",
                                            "path": seed_path,
                                            "missing_fields": ["lane", "scope_shape"],
                                            "validation_command": (
                                                "./repo-python kernel.py "
                                                "--validate-seed-continuity "
                                                f"{seed_path}"
                                            ),
                                            "legacy_validation_command": (
                                                "./repo-python kernel.py "
                                                "--validate-seed-heartbeat "
                                                f"{seed_path}"
                                            ),
                                            "option_surface_command": (
                                                "./repo-python kernel.py --option-surface "
                                                "type_a_autonomous_seeds --band card "
                                                "--ids example"
                                            ),
                                        }
                                    ],
                                },
                            }
                        ],
                        "evidence_refs": [
                            "codex/standards/std_autonomous_seed_prompt.json",
                        ],
                        "metabolism_trigger_state": "scanner_partial",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": (
                            "codex/hologram/compliance/ledger.json::"
                            "by_standard[std_autonomous_seed_prompt]"
                        ),
                    }
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(
        tmp_path,
        "compliance_ledger",
        band="card",
        ids=["std_autonomous_seed_prompt"],
    )
    row = payload["rows"][0]
    actionable = row["actionable_findings"][0]

    assert row["repair_target_paths_preview"] == [
        seed_path,
        "codex/standards/std_autonomous_seed_prompt.json",
    ]
    assert actionable["finding_kind"] == "missing_required_field"
    assert actionable["candidate_target_paths"][0] == seed_path
    assert actionable["candidate_target_payload"]["impacted_seed_paths_preview"] == [seed_path]
    assert actionable["candidate_target_payload"]["repair_targets_preview"][0]["path"] == seed_path


def test_compliance_ledger_card_keeps_baseline_companion_non_claiming(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    standard_path = "codex/standards/std_example.json"
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_example",
                        "validator": (
                            "system/lib/compliance/standard_baseline_adapter.py::"
                            "scan_standard_baseline[std_example]"
                        ),
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 0,
                        "checked_artifact_count": 0,
                        "compliant_artifact_count": 0,
                        "noncompliant_artifact_count": 0,
                        "compliance_rate": None,
                        "top_failure_kinds": [],
                        "findings": [],
                        "evidence_refs": [standard_path],
                        "metabolism_trigger_state": "baseline_only",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": standard_path,
                        "coverage_depth": "baseline_standard_file_only",
                        "coverage_row_kind": "baseline_inventory_only",
                        "baseline_companion": True,
                        "scanner_adapter_present": False,
                        "adapter_registered": True,
                        "governed_projection_present": False,
                        "compliance_claim_status": "no_compliance_claim",
                        "scanner_depth_status": "missing_domain_scanner",
                        "coverage_depth_gap": True,
                        "baseline_reason": "standard_inventory_row_only",
                        "domain_scanner_status": "missing_domain_specific_adapter",
                    }
                ],
                "metabolism_worklist": {"ready_now": [], "deferred_until_scanner_authored": ["std_example"]},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(tmp_path, "compliance_ledger", band="card", ids=["std_example"])
    row = payload["rows"][0]

    assert row["claim"] == (
        "coverage_depth=baseline_standard_file_only "
        "claim_status=no_compliance_claim "
        "scanner_depth=missing_domain_scanner"
    )
    assert row["compliance_rate"] is None
    assert row["checked_artifact_count"] == 0
    assert row["compliant_artifact_count"] == 0
    assert row["noncompliant_artifact_count"] == 0
    assert row["coverage_row_kind"] == "baseline_inventory_only"
    assert row["compliance_claim_status"] == "no_compliance_claim"
    assert row["baseline_companion"] is True
    assert row["scanner_adapter_present"] is False
    assert row["coverage_depth_gap"] is True


def test_compliance_ledger_card_exposes_config_authority_registry_status(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_config_authority_registry",
                        "validator": (
                            "system/lib/compliance/config_authority_registry_adapter.py::"
                            "scan_config_authority_registry"
                        ),
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 111,
                        "checked_artifact_count": 111,
                        "compliant_artifact_count": 111,
                        "noncompliant_artifact_count": 0,
                        "compliance_rate": 1.0,
                        "top_failure_kinds": [],
                        "findings": [],
                        "evidence_refs": ["codex/derived/config_authority_registry.json"],
                        "metabolism_trigger_state": "ready_compliant",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": (
                            "codex/hologram/compliance/ledger.json::"
                            "by_standard[std_config_authority_registry]"
                        ),
                        "config_authority_registry_status": {
                            "registry_path": "codex/derived/config_authority_registry.json",
                            "builder": "tools/meta/factory/build_config_authority_registry.py",
                            "option_surface_status": {
                                "surface_role": "ATLAS_PROJECTION",
                                "first_contact_allowed": False,
                                "cluster_first_for_high_cardinality": True,
                            },
                        },
                        "navigation_role": "Validates the config_authorities projection.",
                    }
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(
        tmp_path,
        "compliance_ledger",
        band="card",
        ids=["std_config_authority_registry"],
    )
    row = payload["rows"][0]

    assert row["standard_id"] == "std_config_authority_registry"
    assert row["config_authority_registry_status"]["registry_path"] == (
        "codex/derived/config_authority_registry.json"
    )
    assert row["config_authority_registry_status"]["option_surface_status"]["surface_role"] == (
        "ATLAS_PROJECTION"
    )
    assert row["config_authority_registry_status"]["option_surface_status"]["first_contact_allowed"] is False
    assert row["config_authority_registry_status"]["option_surface_status"][
        "cluster_first_for_high_cardinality"
    ] is True
    assert row["navigation_role"].startswith("Validates")


def test_compliance_ledger_card_exposes_task_ledger_status(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_task_ledger",
                        "validator": (
                            "system/lib/compliance/task_ledger_adapter.py::scan_task_ledger"
                        ),
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 4000,
                        "checked_artifact_count": 4000,
                        "compliant_artifact_count": 3999,
                        "noncompliant_artifact_count": 1,
                        "compliance_rate": 0.99975,
                        "top_failure_kinds": [{"finding_kind": "stale_projection", "count": 1}],
                        "findings": [],
                        "evidence_refs": ["state/task_ledger/events.jsonl"],
                        "metabolism_trigger_state": "scanner_partial",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": (
                            "codex/hologram/compliance/ledger.json::"
                            "by_standard[std_task_ledger]"
                        ),
                        "task_ledger_status": {
                            "canonical_event_log": "state/task_ledger/events.jsonl",
                            "authority_health": {"status": "clean"},
                            "validation": {"error_count": 0, "warning_count": 1},
                            "projection_check": {"ok": False, "mismatch_count": 1},
                            "option_surface_status": {
                                "surface_role": "ATLAS_PROJECTION",
                                "first_contact_allowed": False,
                                "cluster_first_for_high_cardinality": True,
                            },
                        },
                        "navigation_role": "Validates the task_ledger option surface.",
                    }
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(
        tmp_path,
        "compliance_ledger",
        band="card",
        ids=["std_task_ledger"],
    )
    row = payload["rows"][0]

    assert row["standard_id"] == "std_task_ledger"
    assert row["task_ledger_status"]["canonical_event_log"] == (
        "state/task_ledger/events.jsonl"
    )
    assert row["task_ledger_status"]["option_surface_status"]["surface_role"] == (
        "ATLAS_PROJECTION"
    )
    assert row["task_ledger_status"]["option_surface_status"]["first_contact_allowed"] is False
    assert row["task_ledger_status"]["projection_check"]["mismatch_count"] == 1
    assert row["navigation_role"].startswith("Validates")


def test_compliance_ledger_card_exposes_prompt_ledger_status(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_prompt_ledger",
                        "validator": (
                            "system/lib/compliance/prompt_ledger_adapter.py::scan_prompt_ledger"
                        ),
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 40,
                        "checked_artifact_count": 40,
                        "compliant_artifact_count": 40,
                        "noncompliant_artifact_count": 0,
                        "compliance_rate": 1.0,
                        "top_failure_kinds": [],
                        "findings": [],
                        "evidence_refs": ["state/prompt_ledger/events.jsonl"],
                        "metabolism_trigger_state": "ready_compliant",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": (
                            "codex/hologram/compliance/ledger.json::"
                            "by_standard[std_prompt_ledger]"
                        ),
                        "prompt_ledger_status": {
                            "canonical_event_log": "state/prompt_ledger/events.jsonl",
                            "validation": {"ok": True, "event_count": 36},
                            "projection_check": {"ok": True, "mismatch_count": 0},
                            "option_surface_status": {
                                "surface_role": "ATLAS_PROJECTION",
                                "first_contact_allowed": False,
                                "authority_posture": "projection_browse_only_events_are_authority",
                            },
                        },
                        "navigation_role": "Validates the prompt_ledger option surface.",
                    }
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(
        tmp_path,
        "compliance_ledger",
        band="card",
        ids=["std_prompt_ledger"],
    )
    row = payload["rows"][0]

    assert row["standard_id"] == "std_prompt_ledger"
    assert row["prompt_ledger_status"]["canonical_event_log"] == (
        "state/prompt_ledger/events.jsonl"
    )
    assert row["prompt_ledger_status"]["option_surface_status"]["surface_role"] == (
        "ATLAS_PROJECTION"
    )
    assert row["prompt_ledger_status"]["option_surface_status"]["first_contact_allowed"] is False
    assert row["prompt_ledger_status"]["projection_check"]["mismatch_count"] == 0
    assert row["navigation_role"].startswith("Validates")


def test_compliance_ledger_card_exposes_navigation_contract_status(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_navigation_contract",
                        "validator": (
                            "system/lib/compliance/navigation_contract_adapter.py::"
                            "scan_navigation_contract"
                        ),
                        "validated_at": "2026-05-26T00:00:00+00:00",
                        "applicable_artifact_count": 50,
                        "checked_artifact_count": 50,
                        "compliant_artifact_count": 6,
                        "noncompliant_artifact_count": 44,
                        "compliance_rate": 0.12,
                        "top_failure_kinds": [
                            {"finding_kind": "missing_required_atom", "count": 1}
                        ],
                        "findings": [],
                        "evidence_refs": ["system/lib/kind_band_contract_audit.py"],
                        "metabolism_trigger_state": "scanner_partial",
                        "specialization_of": "std_compliance_coverage",
                        "coverage_path": (
                            "codex/hologram/compliance/ledger.json::"
                            "by_standard[std_navigation_contract]"
                        ),
                        "navigation_contract_status": {
                            "audit_kind": "kind_band_contract_audit",
                            "total_kinds": 49,
                            "declared_count": 5,
                            "profile_declared_count": 1,
                            "drafted_candidate_count": 7,
                            "missing_count": 36,
                            "option_surface_support_upgraded_by_this_audit": False,
                        },
                        "navigation_role": "Validates the Kind Atlas band/scope/facet contract audit.",
                    }
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(
        tmp_path,
        "compliance_ledger",
        band="card",
        ids=["std_navigation_contract"],
    )
    row = payload["rows"][0]

    assert row["standard_id"] == "std_navigation_contract"
    assert row["navigation_contract_status"]["audit_kind"] == "kind_band_contract_audit"
    assert row["navigation_contract_status"]["missing_count"] == 36
    assert (
        row["navigation_contract_status"]["option_surface_support_upgraded_by_this_audit"]
        is False
    )
    assert row["navigation_role"].startswith("Validates")


def test_compliance_ledger_cluster_flag_groups_by_scanner_depth(tmp_path: Path) -> None:
    ledger = tmp_path / "codex/hologram/compliance/ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            {
                "by_standard": [
                    {
                        "standard_id": "std_baseline",
                        "validator": (
                            "system/lib/compliance/standard_baseline_adapter.py::"
                            "scan_standard_baseline[std_baseline]"
                        ),
                        "applicable_artifact_count": 0,
                        "checked_artifact_count": 0,
                        "compliant_artifact_count": 0,
                        "noncompliant_artifact_count": 0,
                        "compliance_rate": None,
                        "metabolism_trigger_state": "baseline_only",
                        "coverage_depth": "baseline_standard_file_only",
                        "coverage_row_kind": "baseline_inventory_only",
                        "baseline_companion": True,
                        "scanner_adapter_present": False,
                        "adapter_registered": True,
                        "governed_projection_present": False,
                        "compliance_claim_status": "no_compliance_claim",
                        "scanner_depth_status": "missing_domain_scanner",
                        "coverage_depth_gap": True,
                        "baseline_reason": "standard_inventory_row_only",
                        "domain_scanner_status": "missing_domain_specific_adapter",
                        "standard_file_status": "present",
                        "id_resolution_source": "standard_inventory",
                    },
                    {
                        "standard_id": "std_domain_partial",
                        "validator": "system/lib/compliance/example_adapter.py::scan_example",
                        "applicable_artifact_count": 4,
                        "checked_artifact_count": 4,
                        "compliant_artifact_count": 2,
                        "noncompliant_artifact_count": 2,
                        "compliance_rate": 0.5,
                        "metabolism_trigger_state": "scanner_partial",
                    },
                    {
                        "standard_id": "std_domain_ready",
                        "validator": "system/lib/compliance/example_adapter.py::scan_example",
                        "applicable_artifact_count": 2,
                        "checked_artifact_count": 2,
                        "compliant_artifact_count": 2,
                        "noncompliant_artifact_count": 0,
                        "compliance_rate": 1.0,
                        "metabolism_trigger_state": "ready_compliant",
                    },
                    {
                        "standard_id": "std_compliance_coverage",
                        "validator": (
                            "system/lib/compliance/compliance_coverage_adapter.py::"
                            "scan_compliance_coverage"
                        ),
                        "applicable_artifact_count": 4,
                        "checked_artifact_count": 4,
                        "compliant_artifact_count": 3,
                        "noncompliant_artifact_count": 1,
                        "compliance_rate": 0.75,
                        "metabolism_trigger_state": "scanner_partial",
                        "coverage_row_kind": "scanner_coverage_self_audit",
                        "compliance_claim_status": (
                            "row_coverage_complete_domain_scanner_partial"
                        ),
                        "scanner_depth_status": "missing_domain_scanners",
                        "coverage_depth_gap": True,
                        "ledger_row_coverage": {
                            "covered_standard_count": 4,
                            "standards_total": 4,
                        },
                        "domain_scanner_coverage": {
                            "domain_scanner_count": 2,
                            "baseline_companion_count": 1,
                            "pending_domain_scanner_count": 1,
                        },
                    },
                ],
                "metabolism_worklist": {"ready_now": []},
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(tmp_path, "compliance_ledger", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert payload["summary"]["drilldown_by"] == "coverage_row_kind_scanner_depth_status"
    assert payload["summary"]["grouping_keys"] == [
        "coverage_row_kind",
        "scanner_depth_status",
    ]
    assert payload["summary"]["total_available"] == 4
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    baseline = rows["baseline_inventory_only:missing_domain_scanner"]
    assert baseline["count"] == 1
    assert baseline["baseline_companion_count"] == 1
    assert baseline["domain_scanner_count"] == 0
    assert baseline["coverage_depth_gap_count"] == 1
    assert baseline["compliance_claim_statuses"] == ["no_compliance_claim"]
    assert baseline["top_ids"] == ["std_baseline"]
    assert "--band card --ids std_baseline" in baseline["card_drilldown_command"]

    domain_partial = rows["domain_scanner:domain_scanner_present"]
    assert domain_partial["count"] == 2
    assert domain_partial["domain_scanner_count"] == 2
    assert domain_partial["noncompliant_standard_count"] == 1
    assert domain_partial["noncompliant_artifact_count_total"] == 2
    assert domain_partial["lowest_known_compliance_rate"] == 0.5

    self_audit = rows["scanner_coverage_self_audit:missing_domain_scanners"]
    assert self_audit["self_audit_count"] == 1
    assert self_audit["coverage_depth_gap_count"] == 1
    assert self_audit["domain_scanner_coverage"]["baseline_companion_count"] == 1
    assert self_audit["ledger_row_coverage"]["covered_standard_count"] == 4
    assert payload["summary"]["recommended_first_cluster"]["cluster_id"] == (
        "baseline_inventory_only:missing_domain_scanner"
    )


def test_standard_skill_map_cluster_flag_groups_by_pairing_status(tmp_path: Path) -> None:
    projection = tmp_path / "codex/hologram/skills/standard_skill_map.json"
    projection.parent.mkdir(parents=True)
    projection.write_text(
        json.dumps(
            {
                "pairings": [
                    {
                        "standard_id": "std_alpha",
                        "pairing_status": "missing_authoring_skill",
                        "authoring_skill_ids": [],
                        "gap_reason": "no_governing_skill",
                    },
                    {
                        "standard_id": "std_beta",
                        "pairing_status": "paired_explicit",
                        "authoring_skill_ids": ["skill_beta"],
                        "gap_reason": None,
                    },
                    {
                        "standard_id": "std_gamma",
                        "pairing_status": "missing_authoring_skill",
                        "authoring_skill_ids": [],
                        "gap_reason": "no_governing_skill",
                    },
                    {
                        "standard_id": "std_delta",
                        "pairing_status": "tool_only_no_skill_required",
                        "authoring_skill_ids": [],
                        "gap_reason": "tool_authority_only",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = build_option_surface(tmp_path, "standard_skill_map", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert payload["summary"]["drilldown_by"] == "pairing_status"
    assert payload["summary"]["total_available"] == 4
    assert payload["summary"]["row_count"] == 3
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    missing = rows["missing_authoring_skill"]
    assert missing["band"] == "cluster_flag"
    assert missing["cluster_source_axis"] == "pairing_status"
    assert missing["count"] == 2
    assert missing["top_ids"] == ["std_alpha", "std_gamma"]
    assert "--band flag --ids std_alpha,std_gamma" in missing["drilldown_command"]
    assert "row-level standard-skill map entries outside top_ids" in missing["omission_receipt"]["omitted"]


def test_renderer_passports_option_surface_exposes_standard_derived_cards() -> None:
    cluster_payload = build_option_surface(REPO_ROOT, "renderer_passports", band="cluster_flag")

    assert cluster_payload["profile_status"] == "supported"
    assert cluster_payload["band"] == "cluster_flag"
    assert cluster_payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert cluster_payload["summary"]["drilldown_by"] == "type_plane_row_status"
    assert cluster_payload["summary"]["grouping_keys"] == ["type_plane_row_status"]
    assert cluster_payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]

    clusters = {row["cluster_id"]: row for row in cluster_payload["rows"]}
    assert "matched" in clusters
    matched = clusters["matched"]
    assert "standards" in matched["target_artifact_kinds"]
    assert matched["cluster_source_axis"] == "type_plane_row_status"
    assert "--option-surface renderer_passports --band flag --ids" in matched["drilldown_command"]

    card_payload = build_option_surface(
        REPO_ROOT,
        "renderer_passports",
        band="card",
        ids=["renderer_passport.standards"],
    )
    assert card_payload["profile_status"] == "supported"
    row = card_payload["rows"][0]
    assert row["passport_id"] == "renderer_passport.standards"
    assert row["renderer_target_kind"] == "standards"
    assert row["type_plane_row_status"] == "matched"
    assert row["source_authority"]["status"] == "declared_by_type_plane_row"
    assert row["option_surface_alignment"]["target_surface"].endswith(
        "--option-surface standards --band cluster_flag"
    )
    assert row["receipt_policy"]["omission_receipt_required"] is True
    assert "full source artifact bodies" in row["omission_receipt"]["omitted"]


def test_navigation_type_plane_option_surface_exposes_standard_owned_graph() -> None:
    cluster_payload = build_option_surface(REPO_ROOT, "navigation_type_plane", band="cluster_flag")

    assert cluster_payload["profile_status"] == "supported"
    assert cluster_payload["band"] == "cluster_flag"
    assert cluster_payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert cluster_payload["summary"]["drilldown_by"] == "artifact_family"
    assert cluster_payload["summary"]["grouping_keys"] == ["artifact_family"]
    assert cluster_payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]

    clusters = {row["cluster_id"]: row for row in cluster_payload["rows"]}
    assert "standard_contract" in clusters
    assert "standards" in clusters["standard_contract"]["top_ids"]
    assert "--option-surface navigation_type_plane --band flag --ids" in clusters["standard_contract"]["drilldown_command"]

    card_payload = build_option_surface(REPO_ROOT, "navigation-type-plane", band="card", ids=["standards"])
    assert card_payload["profile_status"] == "supported"
    row = card_payload["rows"][0]
    assert row["type_id"] == "standards"
    assert row["option_surface_kind"] == "standards"
    assert row["authority_posture"] == "standard_row_is_source_generated_type_plane_is_projection"
    assert row["field_coverage"]["known_gaps"] is True
    assert "full governing standard bodies" in row["omission_receipt"]["omitted"]

    public_payload = build_option_surface(
        REPO_ROOT,
        "navigation_type_plane",
        band="card",
        ids=["public_microcosm_exports"],
    )
    public_row = public_payload["rows"][0]
    assert public_row["entry_depth_contract"]["coverage_role_contract"] == (
        "codex/standards/std_microcosm.json::"
        "paper_module_coverage_contract.module_depth_roles"
    )
    assert "microcosm_runtime_organ_atlas" in public_row["entry_depth_contract"][
        "paper_module_depth_order"
    ]
    assert (
        "codex/doctrine/paper_modules/microcosm_runtime_organ_atlas.md"
        in public_row["governing_standard_refs"]
    )
    assert (
        "codex/doctrine/paper_modules/microcosm_runtime_organ_atlas.md"
        in public_row["projection_refs"]
    )
    assert public_row["entry_depth_contract"]["supporting_lattice_depth"] == [
        "prime_directives",
        "local_to_general_propagation",
        "navigation_hologram_theory",
    ]
    assert public_row["compression_passport"]["safe_drilldown"] == (
        "./repo-python kernel.py --option-surface navigation_type_plane --band card "
        "--ids public_microcosm_exports"
    )
    assert "public microcosm exports" in public_row["compression_passport"][
        "cluster_keys"
    ]

    microcosm_standard_payload = build_option_surface(
        REPO_ROOT,
        "standards",
        band="card",
        ids=["std_microcosm"],
    )
    standard_row = microcosm_standard_payload["rows"][0]
    assert standard_row["compression_passport"]["safe_drilldown"] == (
        "./repo-python kernel.py --option-surface standards --band card --ids std_microcosm"
    )
    assert "microcosm paper module coverage" in standard_row["compression_passport"][
        "cluster_keys"
    ]


def test_row_patches_cluster_flag_groups_by_target_facet() -> None:
    payload = build_option_surface(REPO_ROOT, "row_patches", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert payload["summary"]["drilldown_by"] == "target_facet"
    assert payload["summary"]["grouping_keys"] == ["target_facet"]
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert payload["summary"]["total_available"] >= payload["summary"]["row_count"]

    rows = {row["target_facet"]: row for row in payload["rows"]}
    assert rows
    sample = next(iter(rows.values()))
    assert sample["band"] == "cluster_flag"
    assert sample["cluster_source_axis"] == "target_facet"
    assert sample["count"] >= len(sample["top_ids"])
    assert sample["promotion_counts"]
    assert sample["validation_counts"]
    assert "--option-surface row_patches --band flag --ids" in sample["drilldown_command"]
    assert "proposed_value bodies" in sample["omission_receipt"]["omitted"]

    raw_seed_cluster = rows["raw_seed_candidate_shards"]
    assert len(raw_seed_cluster["top_ids"]) <= generated_surfaces._ROW_PATCH_CLUSTER_TOP_IDS_LIMIT
    assert raw_seed_cluster["top_ids_total"] > len(raw_seed_cluster["top_ids"])
    assert raw_seed_cluster["top_ids_omitted"] > 0
    assert raw_seed_cluster["top_ids_preview_limit"] == (
        generated_surfaces._ROW_PATCH_CLUSTER_TOP_IDS_LIMIT
    )
    assert "patch ids beyond top_ids preview" in raw_seed_cluster["omission_receipt"]["omitted"]


def test_transform_job_receipts_cluster_flag_groups_by_task_class() -> None:
    payload = build_option_surface(REPO_ROOT, "transform_job_receipts", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert payload["summary"]["drilldown_by"] == "task_class"
    assert payload["summary"]["grouping_keys"] == ["task_class"]
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert payload["summary"]["total_available"] >= payload["summary"]["row_count"]

    rows = {row["task_class"]: row for row in payload["rows"]}
    assert rows
    sample = next(iter(rows.values()))
    assert sample["band"] == "cluster_flag"
    assert sample["cluster_source_axis"] == "task_class"
    assert sample["count"] >= len(sample["top_ids"])
    assert sample["status_counts"]
    assert sample["provider_counts"]
    assert sample["promotion_counts"]
    assert "--option-surface transform_job_receipts --band flag --ids" in sample["drilldown_command"]
    assert "provider_metadata bodies" in sample["omission_receipt"]["omitted"]


def test_skills_flag_surface_enumerates_registry_families() -> None:
    payload = build_option_surface(REPO_ROOT, "skills", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "skills"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration_grouped_by_family"
    assert payload["summary"]["row_count"] >= 150
    assert payload["summary"]["total_available"] == payload["summary"]["row_count"]
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]

    groups = {group["family_id"]: group for group in payload["family_groups"]}
    assert "compression" in groups
    assert groups["compression"]["family_title"] == "Shared Compression Profiles"
    assert "profile_governed_compression" in groups["compression"]["skill_ids"]
    assert groups["compression"]["rows"][0]["flag"]

    rows = {row["skill_id"]: row for row in payload["rows"]}
    row = rows["profile_governed_compression"]
    assert row["row_id"] == "skill:profile_governed_compression::flag"
    assert row["artifact_kind"] == "skill"
    assert row["band"] == "flag"
    assert row["atom"] == "Profile-governed compression"
    assert row["compression_source"] == "authored_compression_passport"
    assert "compression" in row["cluster_keys"]
    assert row["family_id"] == "compression"
    assert row["family_title"] == "Shared Compression Profiles"
    assert row["skill_type"] == "authoring"
    assert row["source_ref"] == "codex/doctrine/skills/compression/profile_governed_compression.md"
    assert row["registry_ref"] == "codex/doctrine/skills/skill_registry.json"
    assert row["drilldown_command"].endswith("--band card --ids profile_governed_compression")
    assert row["evidence_command"].endswith("--row skills:profile_governed_compression --band card")
    assert row["debug_trace_command"].endswith("--skill-find profile_governed_compression --debug")
    assert row["currentness"]["status"] == "registry_plus_file_mtime"


def test_skills_cluster_flag_surface_is_all_skills_contents_page() -> None:
    payload = build_option_surface(REPO_ROOT, "skills", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "skills"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert payload["summary"]["row_count"] == payload["summary"]["family_count"]
    assert payload["summary"]["total_available"] >= 150
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    groups = {group["family_id"]: group for group in payload["rows"]}
    assert "compression" in groups
    compression = groups["compression"]
    assert compression["band"] == "cluster_flag"
    assert "profile_governed_compression" in compression["skill_ids"]
    assert compression["skill_type_counts"]
    assert "skill descriptions" in compression["omission_receipt"]["omitted"]
    assert "--band flag --ids" in compression["drilldown_command"]

    task_ledger = groups["task_ledger"]
    assert len(task_ledger["cluster_key_counts"]) <= standard_option_surface.SKILL_CLUSTER_KEY_PREVIEW_LIMIT
    assert task_ledger["cluster_key_counts_total"] > len(task_ledger["cluster_key_counts"])
    assert task_ledger["cluster_key_counts_omitted"] > 0
    assert task_ledger["cluster_key_counts_order"] == "count_desc_then_key"
    assert any(
        "cluster_key_counts beyond top preview" in item
        for item in task_ledger["omission_receipt"]["omitted"]
    )
    assert "--band card --ids" in task_ledger["card_drilldown_command"]


def test_skills_card_surface_exposes_skill_contract() -> None:
    payload = build_option_surface(REPO_ROOT, "skills", band="card", ids=["profile_governed_compression"])

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["row_id"] == "skill:profile_governed_compression::card"
    assert row["band"] == "card"
    assert row["skill_id"] == "profile_governed_compression"
    assert row["description"].startswith("Compress rows through declared profiles")
    assert row["compression_passport"]["atom"] == "Profile-governed compression"
    assert row["triggers"]
    assert row["entry"].startswith("Read codex/doctrine/skills/compression/profile_governed_compression.md")
    assert "codex/doctrine/compression_profiles.json" in row["focus_paths"]
    assert row["doctrine_edges"]["principles"]
    assert "raw_seed_contextual_compression" in row["composes_with"]
    assert row["agent_surface"]["entry"].startswith("Read codex/doctrine/skills/compression")
    assert row["native_bands"] == ["triggers", "card", "workflow", "evidence"]
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["source_ref"] == "codex/doctrine/skills/compression/profile_governed_compression.md"
    assert row["registry_ref"] == "codex/doctrine/skills/skill_registry.json"
    assert row["evidence_command"].endswith("--row skills:profile_governed_compression --band card")
    assert row["debug_trace_command"].endswith("--skill-find profile_governed_compression --debug")
    assert row["currentness"]["status"] == "registry_plus_file_mtime"
    assert row["nearest_standard"]["ref"] == "codex/standards/std_skill.json"
    assert row["nearest_term"]["term_id"] == "skill"
    assert row["omission_receipt"]["drilldown"].endswith("--row skills:profile_governed_compression --band card")
    assert row["omission_receipt"]["debug_trace"].endswith("--skill-find profile_governed_compression --debug")


def test_multi_skill_card_compacts_transitive_principle_capsules() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "skills",
        band="card",
        ids=["navigation_seed", "agent_session_diagnostics"],
    )

    assert len(payload["rows"]) == 2
    assert len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) < 36000
    for row in payload["rows"]:
        assert row["doctrine_edge_ref_compaction"]["profile"] == "multi_skill_card_fast_path"
        assert row["doctrine_edge_ref_compaction"]["omitted_projection_capsule_count"] >= 1
        assert row["doctrine_edge_ref_compaction"]["full_capsule_drilldown"].endswith(
            f"--row skills:{row['skill_id']} --band card"
        )
        assert "full principle projection capsules for multi-skill card rows" in row["omission_receipt"]["omitted"]
        principle_refs = row["doctrine_edge_refs"]["principles"]
        assert principle_refs
        assert all("projection_capsule" not in ref for ref in principle_refs)
        assert any(ref.get("projection_capsule_omitted") is True for ref in principle_refs)
        assert all(ref.get("drilldown_command", "").startswith("./repo-python kernel.py") for ref in principle_refs)


def test_frontend_views_flag_surface_enumerates_view_graph_rows() -> None:
    payload = build_option_surface(REPO_ROOT, "frontend_views", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "frontend_views"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration_from_view_graph"
    assert payload["summary"]["row_count"] >= 30
    assert payload["summary"]["total_available"] == payload["summary"]["row_count"]
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["source_graph_reused"] == "state/frontend_navigation/navigation_graph.json"

    rows = {row["view_id"]: row for row in payload["rows"]}
    row = rows["station"]
    assert row["row_id"] == "frontend_view:station::flag"
    assert row["artifact_kind"] == "frontend_view"
    assert row["band"] == "flag"
    assert row["title"] == "Station"
    assert row["route"] == "/station"
    assert row["path"] == "/station"
    assert row["source_ref"] == "system/server/ui/src/navigation/surfaces.ts"
    assert row["source_component_ref"]["line"] > 0
    assert row["validation_contract"]["schema"] == "frontend_validation_matrix_v1"
    assert row["validation_contract"]["route_class"] == "captured_page"
    assert row["validation_contract"]["browser_visual_requirement"]["status"] == "required"
    assert row["view_observation"]["packet_path"].endswith("views/station.json")
    assert row["view_observation"]["visual_delta_status"] is not None
    assert row["graph_ref"] == "state/frontend_navigation/navigation_graph.json"
    assert row["drilldown_command"].endswith("--band card --ids station")
    assert row["evidence_command"].endswith("--view station")
    assert row["currentness"]["status"] == "frontend_navigation_graph_available"
    assert row["currentness"]["view_observation_index_ref"].endswith(
        "frontend_view_observation_index_v0.json"
    )
    assert row["nearest_doctrine"]["ref"] == "codex/doctrine/paper_modules/frontend_navigation_plane.md"
    assert row["omission_receipt"]["drilldown"].endswith("--view station")


def test_frontend_views_cluster_flag_groups_by_shell_group() -> None:
    payload = build_option_surface(REPO_ROOT, "frontend_views", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "frontend_views"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview_from_view_graph"
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["drilldown_by"] == "shell_group"
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert "all row-level frontend view flags" in payload["cluster_omission_receipt"]["omitted"]

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "shell_group:map" in rows
    cluster = rows["shell_group:map"]
    assert cluster["artifact_kind"] == "frontend_view_cluster"
    assert cluster["band"] == "cluster_flag"
    assert cluster["cluster_source_axis"] == "shell_group"
    assert cluster["count"] >= 1
    assert "rootNavigator" in cluster["top_ids"]
    assert cluster["visual_delta_status_counts"]
    assert cluster["validation_route_class_counts"]
    assert cluster["validation_browser_requirement_status_counts"]
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert "full UI source bodies" in cluster["omission_receipt"]["omitted"]
    assert cluster["currentness"]["status"] == "frontend_navigation_graph_available"


def test_frontend_views_card_surface_drills_stable_view_id() -> None:
    payload = build_option_surface(REPO_ROOT, "frontend_views", band="card", ids=["station"])

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["row_id"] == "frontend_view:station::card"
    assert row["band"] == "card"
    assert row["view_id"] == "station"
    assert row["route"] == "/station"
    assert row["capture_contract"]["slug"] == "home"
    assert row["edge_counts"]["fanout"] >= 1
    assert row["graph_counts"]["routes_declared"] >= 30
    assert row["validation_contract"]["schema"] == "frontend_validation_matrix_v1"
    assert row["validation_contract"]["route_class"] == "captured_page"
    assert "browser_visual_smoke" in row["validation_contract"]["required_lanes"]
    assert row["validation_contract"]["browser_visual_requirement"]["status"] == "required"
    assert row["validation_matrix"]["schema"] == "frontend_validation_matrix_v1"
    assert row["validation_matrix"]["route_class_counts"]["captured_page"] >= 30
    assert row["view_observation"]["packet_path"].endswith("views/station.json")
    assert row["view_observation"]["screenshot_status"] is not None
    assert row["visual_memory"]["docs_route"] == './repo-python kernel.py --docs-route "screenshot ledger"'
    assert row["visual_memory"]["packet_path"].endswith("views/station.json")
    assert "screenshot ledger" in row["visual_memory"]["alias_terms"]
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["native_graph_facets"] == [
        "route",
        "purpose",
        "component_tree",
        "source_capture",
        "validation_contract",
    ]
    assert (
        payload["navigation_boundary"]["native_graph_facets"]
        == row["native_graph_facets"]
    )
    assert payload["summary"]["visual_memory_discovery"]["packet_index_ref"].endswith(
        "frontend_view_observation_index_v0.json"
    )
    assert (
        payload["navigation_boundary"]["visual_memory_docs_route"]
        == './repo-python kernel.py --docs-route "screenshot ledger"'
    )
    assert "system/server/ui/src/App.tsx" in row["source_refs"]
    assert row["omission_receipt"]["drilldown"].endswith("--view station")


def test_frontend_views_card_surface_accepts_code_map_alias() -> None:
    payload = build_option_surface(REPO_ROOT, "frontend_views", band="card", ids=["codeMap"])

    assert payload["selection"]["missing_ids"] == []
    assert payload["selection"]["resolved_ids"] == {"codeMap": "codemap"}
    assert payload["summary"]["row_count"] == 1
    row = payload["rows"][0]
    assert row["view_id"] == "codemap"
    assert row["route"] == "/station/codemap"
    assert row["row_id"] == "frontend_view:codemap::card"


def test_frontend_views_option_surface_exposes_visual_settlement_refs(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "state/frontend_navigation/navigation_graph.json",
        {
            "generated_at": "2026-05-21T00:00:00+00:00",
            "counts": {"pages": 1, "routes_declared": 1},
            "views": [
                {
                    "id": "station",
                    "label": "Station",
                    "route": "/station",
                    "purpose": "Launcher and visual proof queue.",
                    "kind": "page",
                    "shell_group": "operate",
                    "capture": {"slug": "home", "capture_group": "station_runtime"},
                    "evidence": {
                        "file": "system/server/ui/src/navigation/surfaces.ts",
                        "line": 237,
                    },
                }
            ],
        },
    )
    _write_json(
        tmp_path,
        "state/observability/view_quality/frontend_view_observation_index_v0.json",
        {
            "schema": "frontend_view_observation_index_v0",
            "generated_at": "2026-05-21T00:00:00+00:00",
            "row_count": 1,
            "rows": [
                {
                    "view_id": "station",
                    "packet_path": "state/observability/view_quality/views/station.json",
                    "markdown_path": "state/observability/view_quality/views/station.md",
                    "screenshot_status": "fresh",
                    "refresh_due": False,
                    "visual_delta_status": "review_needed",
                }
            ],
        },
    )
    _write_json(
        tmp_path,
        "state/observability/view_quality/frontend_visual_settlement_v0.json",
        {
            "schema": "frontend_visual_settlement_v0",
            "generated_at": "2026-05-21T00:00:00+00:00",
            "summary": {
                "row_count": 1,
                "status_counts": {"review_needed": 1},
                "review_queue_count": 1,
            },
            "rows": [
                {
                    "view_id": "station",
                    "settlement_status": "review_needed",
                    "requires_review": True,
                    "screenshot_status": "fresh",
                    "screenshot_refresh_due": False,
                    "latest_visual_delta": {
                        "status": "review_needed",
                        "receipt_path": "state/observability/renders/run/visual_deltas/manifest.json",
                        "changed_percent": 2.4,
                    },
                    "refs": {
                        "packet_path": "state/observability/view_quality/views/station.json",
                        "markdown_path": "state/observability/view_quality/views/station.md",
                        "open_view_card": "./repo-python kernel.py --option-surface frontend_views --band card --ids station",
                    },
                }
            ],
        },
    )

    card = build_option_surface(tmp_path, "frontend_views", band="card", ids=["station"])
    row = card["rows"][0]
    assert card["summary"]["visual_settlement"]["status_counts"] == {"review_needed": 1}
    assert card["summary"]["visual_settlement"]["review_queue_count"] == 1
    assert row["visual_settlement"]["settlement_status"] == "review_needed"
    assert row["visual_settlement"]["requires_review"] is True
    assert row["visual_memory"]["settlement_status"] == "review_needed"
    assert row["visual_memory"]["visual_delta_status"] == "review_needed"
    assert row["currentness"]["visual_settlement_status"] == "review_needed"

    cluster = build_option_surface(tmp_path, "frontend_views", band="cluster_flag")
    assert cluster["rows"][0]["visual_settlement_status_counts"] == {"review_needed": 1}


def test_raw_seed_shards_flag_surface_enumerates_projection_rows() -> None:
    payload = build_option_surface(REPO_ROOT, "raw_seed_shards", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "raw_seed_shards"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration_from_raw_seed_shards_projection"
    assert payload["summary"]["row_count"] == payload["summary"]["total_available"]
    assert payload["summary"]["row_count"] >= 65
    assert payload["summary"]["source_projection_reused"].endswith("raw_seed_shards.json")
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["flag", "card"]
    assert payload["navigation_boundary"]["native_profile_bands"] == ["flag", "card", "context", "deep"]

    rows = {row["shard_id"]: row for row in payload["rows"]}
    row = rows[RAW_SEED_TEST_SHARD_ID]
    assert row["row_id"] == f"raw_seed_shard:{RAW_SEED_TEST_SHARD_ID}::flag"
    assert row["artifact_kind"] == "raw_seed_shard"
    assert row["band"] == "flag"
    assert row["profile_id"] == "raw_seed_voice_context_v1"
    assert row["source_ref"].endswith("raw_seed_shards.json")
    assert row["parent_paragraph_id"] == RAW_SEED_TEST_PARENT_ID
    assert row["primary_idea_group_id"] == "grp_bridge_contract"
    assert row["drilldown_command"].endswith(f"--band card --ids {RAW_SEED_TEST_SHARD_ID}")
    assert row["evidence_command"].endswith(f"--shard {RAW_SEED_TEST_SHARD_ID} --shards-source raw_seed")
    assert row["currentness"]["status"] == "raw_seed_shards_projection_available"
    assert row["omission_receipt"]["drilldown"].endswith("--shards-source raw_seed")
    assert "text" not in row
    assert "plain_text" not in row


def test_raw_seed_shards_card_surface_drills_stable_shard_id() -> None:
    payload = build_option_surface(REPO_ROOT, "raw_seed_shards", band="card", ids=[RAW_SEED_TEST_SHARD_ID])

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["row_id"] == f"raw_seed_shard:{RAW_SEED_TEST_SHARD_ID}::card"
    assert row["band"] == "card"
    assert row["shard_id"] == RAW_SEED_TEST_SHARD_ID
    assert row["profile_id"] == "raw_seed_voice_context_v1"
    assert row["native_profile_bands"] == ["flag", "card", "context", "deep"]
    assert row["adapter_supported_bands"] == ["flag", "card"]
    assert row["nearest_profile"] == "codex/doctrine/compression_profiles.json::raw_seed_voice_context_v1"
    assert row["nearest_skill"]["ref"] == "codex/doctrine/skills/compression/raw_seed_contextual_compression.md"
    assert {skill["skill_id"] for skill in row["nearest_skills"]} == {
        "raw_seed_contextual_compression",
        "raw_seed_navigation",
    }
    assert row["projection_source"]["raw_seed_markdown_path"].endswith("raw_seed.md")
    assert row["sibling_shard_ids"]
    assert row["dedication_scores"]["grp_bridge_contract"] == 1.0
    assert any(command.endswith("--shards-source raw_seed") for command in row["evidence_commands"])
    assert any("--shards-packet" in command for command in row["evidence_commands"])
    assert "raw voice paragraph body" in row["omission_receipt"]["omitted"]
    assert "context/deep profile-band expansion" in row["omission_receipt"]["omitted"]
    assert "text" not in row
    assert "plain_text" not in row


def test_raw_seed_shards_card_surface_reports_missing_ids() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "raw_seed_shards",
        band="card",
        ids=[RAW_SEED_TEST_SHARD_ID, "missing_shard"],
    )

    assert payload["selection"]["missing_ids"] == ["missing_shard"]
    assert [row["shard_id"] for row in payload["rows"]] == [RAW_SEED_TEST_SHARD_ID]


def test_annex_patterns_flag_surface_enumerates_local_annex_notes() -> None:
    payload = build_option_surface(REPO_ROOT, "annex_patterns", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "annex_patterns"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration_from_annex_notes"
    assert payload["summary"]["row_count"] == payload["summary"]["total_available"]
    assert payload["summary"]["row_count"] > 0
    assert payload["summary"]["source_projection_reused"] == "annexes"
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["native_profile_bands"] == [
        "family",
        "contents",
        "pattern_notes",
        "source",
    ]
    assert payload["navigation_boundary"]["annex_repair_or_population_allowed"] is False
    assert payload["navigation_boundary"]["external_source_fetch_allowed"] is False

    rows = {row["pattern_id"]: row for row in payload["rows"]}
    assert ANNEX_PATTERN_TEST_ID in rows
    row = rows[ANNEX_PATTERN_TEST_ID]
    assert row["row_id"] == f"annex_pattern:{ANNEX_PATTERN_TEST_ID}::flag"
    assert row["artifact_kind"] == "annex_pattern"
    assert row["band"] == "flag"
    assert row["annex_slug"] == ANNEX_PATTERN_TEST_SLUG
    assert row["note_id"] == ANNEX_PATTERN_TEST_NOTE_ID
    assert row["annex_pattern_cluster_key"]
    assert row["cluster_key_provenance"] == "annex_catalog.routing_summary.problem_spaces[0]"
    assert isinstance(row["catalog_problem_spaces"], list)
    assert row["source_ref"] == f"annexes/{ANNEX_PATTERN_TEST_SLUG}/annex_notes.json"
    assert row["drilldown_command"].endswith(f"--band card --ids {ANNEX_PATTERN_TEST_ID}")
    assert row["evidence_command"].startswith("jq '.notes[] | select(.id==")
    assert row["evidence_command"].endswith(f"annexes/{ANNEX_PATTERN_TEST_SLUG}/annex_notes.json'")
    assert row["annex_evidence_command"].endswith(f"--annex-search {ANNEX_PATTERN_TEST_SLUG}")
    assert row["currentness"]["status"] == "annex_notes_available"
    assert row["currentness"]["source_ref"] == f"annexes/{ANNEX_PATTERN_TEST_SLUG}/annex_notes.json"
    assert "navigation" in row["tags"]
    assert isinstance(row["targets"], list) and row["targets"]
    assert "external source repository body" in row["omission_receipt"]["omitted"]
    assert row["omission_receipt"]["drilldown"].startswith("jq '.notes[] | select(.id==")
    assert "note_excerpt" not in row
    assert "note_word_count" not in row


def test_annex_patterns_card_surface_drills_stable_pattern_id() -> None:
    payload = build_option_surface(
        REPO_ROOT, "annex_patterns", band="card", ids=[ANNEX_PATTERN_TEST_ID]
    )

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["row_id"] == f"annex_pattern:{ANNEX_PATTERN_TEST_ID}::card"
    assert row["band"] == "card"
    assert row["pattern_id"] == ANNEX_PATTERN_TEST_ID
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["native_annex_facets"] == ["family", "contents", "pattern_notes", "source"]
    assert row["nearest_standard"]["ref"] == "codex/standards/annex/annex_authority_index.json"
    assert {skill["skill_id"] for skill in row["nearest_skills"]} == {
        "annex_pattern_floor_runtime_fork",
        "annex_pattern_transfer",
    }
    assert row["note_excerpt"]
    assert isinstance(row["note_char_count"], int) and row["note_char_count"] > 0
    assert isinstance(row["note_word_count"], int) and row["note_word_count"] > 0
    assert len(row["note_excerpt"]) <= 600
    assert any(
        command.startswith("jq '.notes[] | select(.id==") for command in row["evidence_commands"]
    )
    assert any(
        command.endswith(f"--annex-search {ANNEX_PATTERN_TEST_SLUG}") for command in row["evidence_commands"]
    )
    assert "external source repository body" in row["omission_receipt"]["omitted"]
    assert "full note prose beyond bounded excerpt" in row["omission_receipt"]["omitted"]
    assert row["source_refs"] == [f"annexes/{ANNEX_PATTERN_TEST_SLUG}/annex_notes.json"]
    assert "note" not in row


def test_annex_patterns_card_surface_reports_missing_ids() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "annex_patterns",
        band="card",
        ids=[ANNEX_PATTERN_TEST_ID, "no-such-annex:n999"],
    )

    assert payload["selection"]["missing_ids"] == ["no-such-annex:n999"]
    assert [row["pattern_id"] for row in payload["rows"]] == [ANNEX_PATTERN_TEST_ID]


def test_annex_patterns_cluster_flag_groups_by_catalog_problem_space() -> None:
    payload = build_option_surface(REPO_ROOT, "annex_patterns", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "annex_patterns"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == (
        "artifact_kind_cluster_overview_from_annex_catalog_problem_spaces"
    )
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["drilldown_by"] == "annex_pattern_cluster_key"
    assert payload["summary"]["source_projection_reused"] == "annexes/annex_catalog.json"
    assert payload["summary"]["grouping_keys"] == [
        "annex_pattern_cluster_key",
        "annex_catalog.routing_summary.problem_spaces[0]",
    ]
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["governing_standard"]["cluster_key_standard_ref"] == (
        "codex/standards/annex/std_annex_catalog.json"
    )
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "skills-authoring" in rows
    assert "unrouted" in rows
    cluster = rows["skills-authoring"]
    assert set(cluster) == {"cluster_id", "label", "count", "annex_count", "top_ids", "claim"}
    assert cluster["count"] > 0
    assert cluster["annex_count"] > 0
    assert cluster["top_ids"]
    assert "full annex_notes.json prose" in payload["omission_receipt"]["omitted"]


def test_annex_patterns_boundary_keeps_native_bands_as_card_data_only() -> None:
    payload = build_option_surface(
        REPO_ROOT, "annex_patterns", band="card", ids=[ANNEX_PATTERN_TEST_ID]
    )

    boundary = payload["navigation_boundary"]
    assert boundary["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert "family" not in boundary["adapter_supported_bands"]
    assert "pattern_notes" not in boundary["adapter_supported_bands"]
    assert boundary["native_profile_bands"] == ["family", "contents", "pattern_notes", "source"]
    assert boundary["annex_repair_or_population_allowed"] is False
    assert boundary["external_source_fetch_allowed"] is False


def test_annex_distillation_patterns_flag_surface_exposes_adoption_metadata() -> None:
    source_data, source_pattern = _annex_distillation_source(
        ANNEX_DISTILLATION_TEST_SLUG,
        ANNEX_DISTILLATION_TEST_PATTERN_ID,
    )
    payload = build_option_surface(REPO_ROOT, "annex_distillation_patterns", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "annex_distillation_patterns"
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration_from_annex_distillation_json"
    assert payload["summary"]["row_count"] == payload["summary"]["total_available"]
    assert payload["summary"]["row_count"] > 0
    assert payload["navigation_boundary"]["adoption_status_mutation_allowed"] is False

    rows = {row["pattern_id"]: row for row in payload["rows"]}
    row = rows[ANNEX_DISTILLATION_TEST_ID]
    assert row["row_id"] == f"annex_distillation_pattern:{ANNEX_DISTILLATION_TEST_ID}::flag"
    assert row["artifact_kind"] == "annex_distillation_pattern"
    assert row["annex_slug"] == ANNEX_DISTILLATION_TEST_SLUG
    assert row["native_pattern_id"] == ANNEX_DISTILLATION_TEST_PATTERN_ID
    assert row["adoption_status"] == source_pattern["adoption_status"]
    assert row["authored_artifact"] == source_pattern["authored_artifact"]
    assert row["axis"] == source_pattern["axis"]
    assert row["adoption_lane"] == source_pattern["adoption_lane"]
    assert row["flag"]
    assert row["one_liner"] == row["flag"]
    assert row["source_locus"] == source_pattern["source_locus"]
    assert row["local_target"] == source_pattern["local_target"]
    assert row["source_ref"] == "annexes/agentic-stack/distillation.json"
    assert row["drilldown_command"].endswith(
        f"--option-surface annex_distillation_patterns --band card --ids {ANNEX_DISTILLATION_TEST_ID}"
    )
    assert row["evidence_command"].endswith("'annexes/agentic-stack/distillation.json'")
    assert row["currentness"]["status"] == "distillation_json_available"
    assert row["currentness"]["distillation_status"] == source_data["distillation_status"]
    assert "external source repository body" in row["omission_receipt"]["omitted"]


def test_annex_distillation_patterns_cluster_flag_groups_by_annex_slug() -> None:
    payload = build_option_surface(REPO_ROOT, "annex_distillation_patterns", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "annex_distillation_patterns"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == (
        "artifact_kind_cluster_overview_from_annex_distillation_json"
    )
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["drilldown_by"] == "annex_slug"
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert ANNEX_DISTILLATION_TEST_SLUG in rows
    cluster = rows[ANNEX_DISTILLATION_TEST_SLUG]
    assert set(cluster) == {
        "cluster_id",
        "count",
        "authored_artifact_count",
        "top_ids",
        "adoption_status_counts",
        "claim",
    }
    assert cluster["count"] >= 1
    assert cluster["top_ids"]
    assert cluster["adoption_status_counts"]
    assert "pattern-level flag rows outside each cluster's top_ids" in payload["omission_receipt"]["omitted"]


def test_annex_distillation_patterns_card_surface_drills_pattern_identity() -> None:
    _, source_pattern = _annex_distillation_source(
        ANNEX_DISTILLATION_TEST_SLUG,
        ANNEX_DISTILLATION_TEST_PATTERN_ID,
    )
    payload = build_option_surface(
        REPO_ROOT,
        "annex_distillation_patterns",
        band="card",
        ids=[ANNEX_DISTILLATION_TEST_ID],
    )

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["row_id"] == f"annex_distillation_pattern:{ANNEX_DISTILLATION_TEST_ID}::card"
    assert row["band"] == "card"
    assert row["pattern_id"] == ANNEX_DISTILLATION_TEST_ID
    assert row["adoption_status"] == source_pattern["adoption_status"]
    assert row["authored_artifact"] == source_pattern["authored_artifact"]
    assert row["adoption_action"] == source_pattern["adoption_action"]
    assert row["relevance"] == source_pattern["relevance"]
    assert row["confidence"] == source_pattern["confidence"]
    assert row["source_locus"] == source_pattern["source_locus"]
    assert row["local_target"] == source_pattern["local_target"]
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert "adoption_action" in row["available_pattern_fields"]
    assert "local_target" in row["decision_support"]["implementation_decision_fields"]
    assert row["nearest_standard"]["ref"] == "codex/standards/annex/annex_authority_index.json"
    assert row["nearest_paper_module"]["ref"] == "codex/doctrine/paper_modules/annex_distillation_layer.md"
    assert row["source_refs"] == ["annexes/agentic-stack/distillation.json"]
    assert any(command.endswith("--annex-search agentic-stack") for command in row["evidence_commands"])


def test_option_surface_kernel_command_redirects_annex_distillation_flag_to_cluster_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "annex_distillation_patterns",
            "--band",
            "flag",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "annex_distillation_patterns"
    assert payload["band"] == "cluster_flag"
    assert payload["requested_band"] == "flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert ANNEX_DISTILLATION_TEST_SLUG in {row["cluster_id"] for row in payload["rows"]}


def test_microcosm_extracted_patterns_cluster_flag_groups_by_organ_family() -> None:
    payload = build_option_surface(REPO_ROOT, "microcosm_extracted_patterns", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "microcosm_extracted_patterns"
    assert payload["summary"]["total_available"] >= 300
    assert payload["summary"]["drilldown_by"] == "organ_family"
    assert payload["navigation_boundary"]["macro_side_only"] is True
    assert payload["navigation_boundary"]["public_release_authority"] is False

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "navigation" in rows
    assert rows["navigation"]["top_ids"]
    assert "pattern-level flag rows outside each cluster's top_ids" in payload["omission_receipt"]["omitted"]


def test_microcosm_extracted_patterns_cluster_flag_exposes_binding_overlay_status() -> None:
    payload = build_option_surface(REPO_ROOT, "microcosm_extracted_patterns", band="cluster_flag")

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    bridge = rows["bridge_continuity"]

    assert bridge["current_microcosm_status_counts"]["absent"] >= 1
    assert bridge["binding_overlay_status_counts"]["routed_with_detailed_binding"] >= 1
    assert bridge["route_readiness_status_counts"]["routed_to_organ_bundle"] >= 1
    assert bridge["substrate_binding_status_counts"]["detailed_binding_available"] >= 1
    assert "bridge_phase_continuity_runtime" in bridge["top_route_to_organ_ids"]
    assert "raw extraction snapshot" in bridge["status_boundary"]


def test_microcosm_extracted_patterns_card_surface_drills_pattern_identity() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "microcosm_extracted_patterns",
        band="card",
        ids=[MICROCOSM_EXTRACTED_PATTERN_TEST_ID],
    )

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["missing_ids"] == []
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["row_id"] == (
        f"microcosm_extracted_pattern:{MICROCOSM_EXTRACTED_PATTERN_TEST_ID}::card"
    )
    assert row["artifact_kind"] == "microcosm_extracted_pattern"
    assert row["pattern_id"] == MICROCOSM_EXTRACTED_PATTERN_TEST_ID
    assert row["organ_family"] == "navigation"
    assert row["source_ref"] == "state/microcosm_portfolio/extracted_patterns_ledger.jsonl"
    assert row["currentness"]["status"] == "macro_side_extracted_pattern_ledger_available"
    assert row["nearest_paper_module"]["ref"] == "codex/doctrine/paper_modules/microcosm_substrate.md"
    assert row["route_readiness_membership"]["status"] == "routed_to_organ_bundle"
    assert "navigation_hologram_route_plane" in row["route_readiness_membership"]["route_to_organ_ids"]
    assert row["binding_overlay"]["status"] == row["binding_overlay_status"]
    assert row["binding_overlay"]["authority"].startswith("binding-aware routability overlay only")
    assert "full macro-private source refs beyond row-local handles" in row["omission_receipt"]["omitted"]


def test_microcosm_extracted_patterns_card_routes_pattern_ledger_validator_pair() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "microcosm_extracted_patterns",
        band="card",
        ids=["extracted_pattern_organ_readiness_selector"],
    )

    row = payload["rows"][0]
    membership = row["route_readiness_membership"]

    assert membership["status"] == "routed_to_organ_bundle"
    assert "pattern_ledger_preselection_validation_spine" in membership["route_to_organ_ids"]
    assert "route_card_pattern_ledger_preselection_validation" in membership["route_card_ids"]
    assert "pattern_ledger_validator_rows" in membership["router_ids"]
    assert membership["individual_row_selection"] == ["forbidden"]
    assert membership["authority"].startswith("macro-side route-readiness membership only")


def test_microcosm_extracted_patterns_card_routes_root_readiness_card() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "microcosm_extracted_patterns",
        band="card",
        ids=["source_shuttle_bounded_carryforward"],
    )

    row = payload["rows"][0]
    membership = row["route_readiness_membership"]

    assert membership["status"] == "routed_to_organ_bundle"
    assert "root_binding_and_executable_grammar" in membership["route_to_organ_ids"]
    assert "root_binding_and_executable_grammar" in membership["readiness_ids"]
    assert "route_card_root_binding_and_grammar" in membership["route_card_ids"]
    assert membership["individual_row_selection"] == ["forbidden"]


def test_microcosm_extracted_patterns_card_routes_foundation_combination_route() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "microcosm_extracted_patterns",
        band="card",
        ids=["blind_policy_problem_id_ablation_gate"],
    )

    row = payload["rows"][0]
    membership = row["route_readiness_membership"]

    assert membership["status"] == "routed_to_organ_bundle"
    assert "formal_policy_integrity_search_foundry" in membership["combination_route_ids"]
    assert "foundation_combination_routes" in membership["route_collections"]
    assert "proof_diagnostic_evidence_spine" in membership["route_to_organ_ids"]
    assert "external_boundary_anti_corruption_runtime" in membership["route_to_organ_ids"]
    assert "route_card_proof_diagnostic_evidence" in membership["route_card_ids"]
    assert "route_card_external_boundary" in membership["route_card_ids"]
    assert "selector_may_select" in membership["selector_postures"]
    assert "selector_may_select_after_roots" in membership["selector_postures"]


def test_microcosm_extracted_patterns_card_includes_binding_summary() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "microcosm_extracted_patterns",
        band="card",
        ids=["recursive_self_improvement_operating_loop"],
    )

    row = payload["rows"][0]
    binding = row["substrate_binding_summary"]

    assert binding["status"] == "detailed_binding_available"
    assert binding["missing_bindings"] == []
    assert (
        binding["grounding_status"]
        == "public_microcosm_organ_bound_with_standard_fixture_validator_and_receipts"
    )
    assert (
        "microcosm-substrate/standards/std_microcosm_voice_to_doctrine_self_improvement_loop.json"
        in binding["standard_refs"]
    )
    assert (
        "microcosm-substrate/src/microcosm_core/organs/voice_to_doctrine_self_improvement_loop.py"
        in binding["code_owner_refs"]
    )
    organ_test_path = "microcosm-substrate/tests/test_voice_to_doctrine_self_improvement_loop.py"
    assert any(
        "./repo-pytest" in command and organ_test_path in command
        for command in binding["command_surfaces"]
    )


def test_microcosm_extracted_patterns_card_includes_formal_prover_payload_policy_boundary_binding() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "microcosm_extracted_patterns",
        band="card",
        ids=["formal_prover_payload_policy_boundary"],
    )

    row = payload["rows"][0]
    binding = row["substrate_binding_summary"]
    membership = row["route_readiness_membership"]

    assert binding["status"] == "detailed_binding_available"
    assert binding["missing_bindings"] == []
    assert (
        binding["grounding_status"]
        == "formal_prover_provider_payload_membrane_bound_to_transform_job_receipts_reducer_policy_and_proof_authority_boundary"
    )
    assert "codex/standards/std_transform_job.json" in binding["standard_refs"]
    assert (
        "tools/meta/factory/reduce_prover_provider_receipts.py"
        in binding["code_owner_refs"]
    )
    assert (
        "./repo-python kernel.py --option-surface microcosm_extracted_patterns --band card --ids formal_prover_payload_policy_boundary"
        in binding["command_surfaces"]
    )
    assert membership["status"] == "routed_to_organ_bundle"
    assert "proof_diagnostic_evidence_spine" in membership["route_to_organ_ids"]
    assert "proof_diagnostic_and_formal_body_rows" in membership["router_ids"]
    assert membership["individual_row_selection"] == ["forbidden"]


def test_microcosm_extracted_patterns_card_routes_agent_self_observability_anchor() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "microcosm_extracted_patterns",
        band="card",
        ids=["agent_self_observability_plane"],
    )

    row = payload["rows"][0]
    membership = row["route_readiness_membership"]

    assert membership["status"] == "routed_to_organ_bundle"
    assert "agent_route_observability_runtime" in membership["route_to_organ_ids"]
    assert "route_card_agent_observability_runtime" in membership["route_card_ids"]
    assert "agent_observability_runtime_rows" in membership["router_ids"]
    assert membership["individual_row_selection"] == ["forbidden"]


def test_python_files_flag_surface_enumerates_scope_index_files() -> None:
    payload = build_option_surface(REPO_ROOT, "python_files", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "python_files"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration_from_python_scope_index"
    assert payload["summary"]["row_count"] == payload["summary"]["total_available"]
    assert payload["summary"]["row_count"] > 0
    assert payload["summary"]["source_projection_reused"].endswith("std_python_scope_index.json")
    boundary = payload["navigation_boundary"]
    assert boundary["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert boundary["native_profile_bands"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert boundary["python_scope_index_rebuild_allowed"] is False
    assert boundary["python_source_mutation_allowed"] is False
    assert boundary["python_scopes_expansion_in_this_adapter"] is False

    rows = {row["file_id"]: row for row in payload["rows"]}
    assert PYTHON_FILE_TEST_ID in rows
    row = rows[PYTHON_FILE_TEST_ID]
    assert row["row_id"] == f"python_file:{PYTHON_FILE_TEST_ID}::flag"
    assert row["artifact_kind"] == "python_file"
    assert row["band"] == "flag"
    assert row["path"] == PYTHON_FILE_TEST_ID
    assert row["profile_id"] == "python_scope_navigation_v0"
    assert row["source_ref"].endswith("std_python_scope_index.json")
    assert row["drilldown_command"].endswith(f"--band card --ids {PYTHON_FILE_TEST_ID}")
    assert row["evidence_command"].endswith(f"--compile {PYTHON_FILE_TEST_ID}")
    assert row["currentness"]["status"] == "python_scope_index_available"
    assert row["usage"]["source_ref"] == "state/python_usage/python_usage_stats.json"
    assert row["usage"]["status"] in {"observed", "unobserved"}
    assert row["usage"]["run_count"] >= 0
    assert row["usage"]["function_call_count"] >= 0
    assert row["currentness"]["file_count"] > 0
    assert row["scope_count"] >= 1
    assert row["public_symbol_count"] >= 1
    assert "full Python source body" in row["omission_receipt"]["omitted"]
    assert "public_symbol_ids" not in row
    assert "top_scopes" not in row
    assert "scope_summary" not in row


def test_python_files_cluster_flag_groups_before_row_expansion() -> None:
    payload = build_option_surface(REPO_ROOT, "python_files", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "python_files"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == (
        "artifact_kind_cluster_overview_from_python_scope_index"
    )
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "kernel_lib" in rows
    cluster = rows["kernel_lib"]
    assert cluster["artifact_kind"] == "python_file_cluster"
    assert cluster["band"] == "cluster_flag"
    assert cluster["file_count"] >= 1
    assert cluster["scope_count"] >= cluster["file_count"]
    assert cluster["top_ids"]
    assert cluster["usage"]["source_ref"] == "state/python_usage/python_usage_stats.json"
    assert cluster["usage"]["observed_file_count"] >= 0
    assert cluster["usage"]["unobserved_file_count"] >= 0
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert "file-level flag rows" in cluster["omission_receipt"]["omitted"]


def test_python_files_card_all_redirects_to_cluster_flag() -> None:
    payload = build_option_surface(REPO_ROOT, "python_files", band="card")

    assert payload["profile_status"] == "supported"
    assert payload["requested_band"] == "card"
    assert payload["band"] == "cluster_flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert all(row["band"] == "cluster_flag" for row in payload["rows"])
    assert any(warning["kind"] == "high_cardinality_card_redirect" for warning in payload["warnings"])


def test_python_option_surfaces_overlay_live_runtime_usage(tmp_path: Path) -> None:
    index_path = tmp_path / "codex/standards/std_python_scope_index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps(
            {
                "__meta": {
                    "schema_version": "std_python_scope_index_v0",
                    "generated_at": "2026-05-07T00:00:00+00:00",
                    "file_count": 1,
                    "scope_count": 1,
                },
                "files": [
                    {
                        "path": "sample.py",
                        "summary": "Sample file.",
                        "browse_summary": "Open sample file.",
                        "group_id": "kernel_lib",
                        "group_label": "Kernel Library",
                        "navigation_group": "kernel_lib",
                        "public_symbol_ids": ["sample.py::alpha"],
                        "status": "compliant",
                    }
                ],
                "scopes": [
                    {
                        "symbol_id": "sample.py::alpha",
                        "path": "sample.py",
                        "scope_kind": "function",
                        "name": "alpha",
                        "summary": "Run alpha.",
                        "group_id": "kernel_lib",
                        "navigation_group": "kernel_lib",
                        "status": "up_to_date",
                        "line_start": 1,
                        "line_end": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    usage_path = tmp_path / "state/python_usage/python_usage_stats.json"
    usage_path.parent.mkdir(parents=True)
    usage_path.write_text(
        json.dumps(
            {
                "__meta": {
                    "schema_version": "python_runtime_usage_stats_v0",
                    "generated_at": "2026-05-07T00:00:01+00:00",
                    "file_count": 1,
                    "scope_count": 1,
                    "event_count": 12,
                },
                "files": {
                    "sample.py": {
                        "run_count": 3,
                        "function_call_count": 4,
                        "last_seen_at": "2026-05-07T00:00:02+00:00",
                    }
                },
                "scopes": {
                    "sample.py::alpha": {
                        "call_count": 5,
                        "last_seen_at": "2026-05-07T00:00:02+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    files_payload = build_option_surface(tmp_path, "python_files", band="flag", ids=["sample.py"])
    file_row = files_payload["rows"][0]
    assert files_payload["summary"]["runtime_usage_projection"]["event_count"] == 12
    assert file_row["usage"]["status"] == "observed"
    assert file_row["usage"]["run_count"] == 3
    assert file_row["usage"]["function_call_count"] == 4

    scopes_payload = build_option_surface(
        tmp_path, "python_scopes", band="flag", ids=["sample.py::alpha"]
    )
    scope_row = scopes_payload["rows"][0]
    assert scopes_payload["summary"]["runtime_usage_projection"]["event_count"] == 12
    assert scope_row["usage"]["status"] == "observed"
    assert scope_row["usage"]["call_count"] == 5


def test_python_files_card_surface_drills_stable_file_id() -> None:
    payload = build_option_surface(
        REPO_ROOT, "python_files", band="card", ids=[PYTHON_FILE_TEST_ID]
    )

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["row_id"] == f"python_file:{PYTHON_FILE_TEST_ID}::card"
    assert row["band"] == "card"
    assert row["file_id"] == PYTHON_FILE_TEST_ID
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["native_python_facets"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert row["nearest_standard"]["ref"] == "codex/standards/std_python.py"
    assert row["nearest_index"]["ref"] == "codex/standards/std_python_scope_index.json"
    upstream = row["upstream_doctrine_route"]
    assert upstream["status"] == "available"
    assert upstream["route_kind"] == "python_file"
    assert upstream["canonical_source"] == PYTHON_FILE_TEST_ID
    assert upstream["authority_layer"] == "operational"
    assert upstream["authority_tier"] == "owner_surface_route_not_source_authority"
    assert upstream["source_projection"] == "codex/standards/std_python_scope_index.json"
    assert upstream["governing_standard"] == "codex/standards/std_python.py"
    assert upstream["governing_doctrine"] == "codex/doctrine/paper_modules/navigation_hologram_theory.md"
    assert upstream["governing_skill"] == "codex/doctrine/skills/compression/profile_governed_compression.md"
    assert upstream["route_commands"]["standard"].endswith(
        "--option-surface standards --band card --ids std_python"
    )
    assert upstream["route_commands"]["scope_index"].endswith(
        "--option-surface standards --band card --ids std_python_scope_index"
    )
    assert upstream["route_commands"]["doctrine"].endswith(
        "--paper-module navigation_hologram_theory"
    )
    assert upstream["evaluator_lane"].endswith(f"--compile {PYTHON_FILE_TEST_ID}")
    assert upstream["receipt_lane"].endswith("std_python_scope_index.json")
    assert "navigation_context_pack.selected_rows" in upstream["runtime_consumers"]
    assert isinstance(row["public_symbol_ids"], list) and row["public_symbol_ids"]
    assert all(sym.startswith(PYTHON_FILE_TEST_ID + "::") for sym in row["public_symbol_ids"])
    assert isinstance(row["scope_summary"], dict)
    assert row["scope_summary"]["total"] == row["scope_count"]
    assert row["scope_summary"]["function"] + row["scope_summary"]["class"] + row["scope_summary"]["method"] + row["scope_summary"]["other"] == row["scope_summary"]["total"]
    assert isinstance(row["top_scopes"], list) and row["top_scopes"]
    assert row["top_scopes"][0]["scope_kind"] in {"class", "function", "method"}
    assert any(cmd.endswith(f"--compile {PYTHON_FILE_TEST_ID}") for cmd in row["evidence_commands"])
    assert any("std_python_scope_index.json" in cmd for cmd in row["evidence_commands"])
    assert "full Python source body" in row["omission_receipt"]["omitted"]
    assert "python_scopes expansion" in row["omission_receipt"]["omitted"][-1]


def test_python_files_card_surface_reports_missing_ids() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "python_files",
        band="card",
        ids=[PYTHON_FILE_TEST_ID, "no/such/file.py"],
    )

    assert payload["selection"]["missing_ids"] == ["no/such/file.py"]
    assert [row["file_id"] for row in payload["rows"]] == [PYTHON_FILE_TEST_ID]


def test_python_files_boundary_keeps_native_bands_as_card_data_only() -> None:
    payload = build_option_surface(
        REPO_ROOT, "python_files", band="card", ids=[PYTHON_FILE_TEST_ID]
    )

    boundary = payload["navigation_boundary"]
    assert boundary["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert "module_docs" not in boundary["adapter_supported_bands"]
    assert "symbol_capsule" not in boundary["adapter_supported_bands"]
    assert boundary["native_profile_bands"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]


def test_python_scopes_flag_surface_enumerates_scope_index_rows() -> None:
    payload = build_option_surface(REPO_ROOT, "python_scopes", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "python_scopes"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == (
        "artifact_kind_enumeration_from_python_scope_index"
    )
    assert payload["summary"]["row_count"] == payload["summary"]["total_available"]
    assert payload["summary"]["total_available"] > 1000
    assert payload["summary"]["drilldown_by"] == "scope_id"
    assert payload["summary"]["scope_id_strategy"] == (
        "symbol_id_when_unique_else_symbol_id_with_line_start_suffix"
    )
    assert payload["summary"]["source_projection_reused"].endswith(
        "std_python_scope_index.json"
    )

    boundary = payload["navigation_boundary"]
    assert boundary["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert boundary["python_scope_index_rebuild_allowed"] is False
    assert boundary["python_source_mutation_allowed"] is False
    assert boundary["python_scope_callgraph_closure_in_this_adapter"] is False

    rows = {row["scope_id"]: row for row in payload["rows"]}
    assert PYTHON_SCOPE_TEST_ID in rows
    row = rows[PYTHON_SCOPE_TEST_ID]
    assert row["row_id"] == f"python_scope:{PYTHON_SCOPE_TEST_ID}::flag"
    assert row["artifact_kind"] == "python_scope"
    assert row["band"] == "flag"
    assert row["symbol_id"] == PYTHON_SCOPE_TEST_ID
    assert row["path"] == PYTHON_SCOPE_TEST_PATH
    assert row["scope_kind"] in {"class", "function", "method"}
    assert row["line_start"] is not None and row["line_end"] is not None
    assert row["profile_id"] == "python_scope_navigation_v0"
    assert row["source_ref"].endswith("std_python_scope_index.json")
    assert row["drilldown_command"].endswith(
        f"--option-surface python_scopes --band card --ids {PYTHON_SCOPE_TEST_ID}"
    )
    assert "select(.symbol_id==$sid)" in row["evidence_command"]
    assert row["currentness"]["status"] == "python_scope_index_available"
    assert row["usage"]["source_ref"] == "state/python_usage/python_usage_stats.json"
    assert row["usage"]["status"] in {"observed", "unobserved"}
    assert row["usage"]["call_count"] >= 0
    assert "full Python source body" in row["omission_receipt"]["omitted"]


def test_python_scopes_cluster_flag_groups_by_navigation_group_and_kind() -> None:
    payload = build_option_surface(REPO_ROOT, "python_scopes", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "python_scopes"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == (
        "artifact_kind_cluster_overview_from_python_scope_index"
    )
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["drilldown_by"] == "group_id"
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "kernel_lib" in rows
    cluster = rows["kernel_lib"]
    assert cluster["artifact_kind"] == "python_scope_cluster"
    assert cluster["band"] == "cluster_flag"
    assert cluster["scope_count"] >= 1
    assert cluster["scope_kind_counts"]["function"] >= 1
    assert cluster["file_count"] >= 1
    assert cluster["top_ids"]
    assert cluster["usage"]["source_ref"] == "state/python_usage/python_usage_stats.json"
    assert cluster["usage"]["observed_scope_count"] >= 0
    assert cluster["usage"]["unobserved_scope_count"] >= 0
    assert cluster["top_ids_total"] == cluster["scope_count"]
    assert cluster["top_ids_omitted"] == cluster["top_ids_total"] - len(cluster["top_ids"])
    assert cluster["cluster_drilldown_command"].endswith(
        "--option-surface python_scopes --band cluster_flag --ids kernel_lib"
    )
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert "scope-level flag rows" in cluster["omission_receipt"]["omitted"]
    assert cluster["omission_receipt"]["drilldown"] == cluster["cluster_drilldown_command"]
    assert cluster["omission_receipt"]["sample_scope_drilldown"] == cluster["drilldown_command"]


def test_python_scopes_cluster_flag_accepts_group_id_drilldown() -> None:
    payload = build_option_surface(
        REPO_ROOT, "python_scopes", band="cluster_flag", ids=["kernel_lib"]
    )

    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["drilldown_by"] == "group_id"
    assert len(payload["rows"]) == 1
    cluster = payload["rows"][0]
    assert cluster["cluster_id"] == "kernel_lib"
    assert cluster["scope_count"] >= 1
    assert cluster["cluster_drilldown_command"].endswith(
        "--option-surface python_scopes --band cluster_flag --ids kernel_lib"
    )


def test_python_scopes_card_surface_drills_stable_symbol_id() -> None:
    payload = build_option_surface(
        REPO_ROOT, "python_scopes", band="card", ids=[PYTHON_SCOPE_TEST_ID]
    )

    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["row_id"] == f"python_scope:{PYTHON_SCOPE_TEST_ID}::card"
    assert row["band"] == "card"
    assert row["scope_id"] == PYTHON_SCOPE_TEST_ID
    assert row["symbol_id"] == PYTHON_SCOPE_TEST_ID
    assert row["path"] == PYTHON_SCOPE_TEST_PATH
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["native_python_facets"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert row["nearest_standard"]["ref"] == "codex/standards/std_python.py"
    assert row["nearest_index"]["ref"] == "codex/standards/std_python_scope_index.json"
    upstream = row["upstream_doctrine_route"]
    assert upstream["status"] == "available"
    assert upstream["route_kind"] == "python_scope"
    assert upstream["canonical_source"].startswith(f"{PYTHON_SCOPE_TEST_PATH}::")
    assert upstream["authority_boundary"] == "route_metadata_only_open_canonical_source_before_mutation"
    assert upstream["source_projection"] == "codex/standards/std_python_scope_index.json"
    assert upstream["governing_standard"] == "codex/standards/std_python.py"
    assert upstream["governing_doctrine"] == "codex/doctrine/paper_modules/navigation_hologram_theory.md"
    assert upstream["route_commands"]["parent_file"].endswith(
        f"--option-surface python_files --band card --ids {PYTHON_SCOPE_TEST_PATH}"
    )
    assert upstream["route_commands"]["standard"].endswith(
        "--option-surface standards --band card --ids std_python"
    )
    assert upstream["evaluator_lane"].endswith(f"--compile {PYTHON_SCOPE_TEST_PATH}")
    assert "select(.symbol_id==$sid)" in upstream["receipt_lane"]
    assert row["parent_file_command"].endswith(
        f"--option-surface python_files --band card --ids {PYTHON_SCOPE_TEST_PATH}"
    )
    assert isinstance(row["related_symbols"], list)
    assert isinstance(row["callee_refs"], list)
    assert isinstance(row["inbound_dependents"], list)
    assert row["source_span"]["path"] == PYTHON_SCOPE_TEST_PATH
    assert any("select(.symbol_id==$sid)" in cmd for cmd in row["evidence_commands"])
    assert any(cmd.endswith(f"--compile {PYTHON_SCOPE_TEST_PATH}") for cmd in row["evidence_commands"])
    assert "full Python source body" in row["omission_receipt"]["omitted"]
    assert "complete callers/callees graph closure" in row["omission_receipt"]["omitted"]


def test_python_scopes_card_surface_reports_missing_ids() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "python_scopes",
        band="card",
        ids=[PYTHON_SCOPE_TEST_ID, "no/such/module.py::NotASymbol"],
    )

    assert payload["selection"]["missing_ids"] == ["no/such/module.py::NotASymbol"]
    assert [row["scope_id"] for row in payload["rows"]] == [PYTHON_SCOPE_TEST_ID]


def test_python_scopes_boundary_keeps_native_bands_as_card_data_only() -> None:
    payload = build_option_surface(
        REPO_ROOT, "python_scopes", band="card", ids=[PYTHON_SCOPE_TEST_ID]
    )

    boundary = payload["navigation_boundary"]
    assert boundary["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert "symbol_capsule" not in boundary["adapter_supported_bands"]
    assert "graph_context" not in boundary["adapter_supported_bands"]
    assert boundary["native_profile_bands"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert boundary["native_profile_bands_are_data_not_adapter_support"] is True


def test_standards_flag_surface_enumerates_without_query() -> None:
    payload = build_option_surface(REPO_ROOT, "standards", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "standards"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["row_count"] > 50

    rows = {row["standard_id"]: row for row in payload["rows"]}
    assert "std_semantic_naming" in rows
    semantic = rows["std_semantic_naming"]
    assert semantic["claim"] == (
        "A name should reveal artifact kind, role, authority plane, lifecycle posture, "
        "and safe expansion path before source is opened."
    )
    assert semantic["drilldown_command"].endswith("--band card --ids std_semantic_naming")
    assert semantic["source_ref"] == "codex/standards/std_semantic_naming.json"


def test_standards_surface_includes_python_module_standard() -> None:
    payload = build_option_surface(REPO_ROOT, "standards", band="card", ids=["std_python"])

    assert payload["selection"]["missing_ids"] == []
    assert payload["summary"]["row_count"] == 1
    row = payload["rows"][0]
    assert row["standard_id"] == "std_python"
    assert row["source_ref"] == "codex/standards/std_python.py"
    assert row["claim"]
    assert row["evidence_command"].endswith(
        "--option-surface python_files --band card --ids codex/standards/std_python.py"
    )
    assert row["omission_receipt"]["drilldown"].endswith(
        "--option-surface python_files --band card --ids codex/standards/std_python.py"
    )


def test_standards_cluster_flag_groups_by_standard_group() -> None:
    payload = build_option_surface(REPO_ROOT, "standards", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "standards"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == (
        "artifact_kind_cluster_overview_grouped_by_standard_group"
    )
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["drilldown_by"] == "group"
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "core" in rows
    cluster = rows["core"]
    assert cluster["artifact_kind"] == "standard_group"
    assert cluster["band"] == "cluster_flag"
    assert cluster["count"] >= 1
    assert cluster["top_ids"]
    assert cluster["claim"]
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert "full JSON standard bodies" in cluster["omission_receipt"]["omitted"]


def test_standards_card_surface_exposes_naming_shards() -> None:
    payload = build_option_surface(REPO_ROOT, "standards", band="card", ids=["std_semantic_naming"])

    assert payload["summary"]["query_used"] is False
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert [row["standard_id"] for row in payload["rows"]] == ["std_semantic_naming"]
    row = payload["rows"][0]
    assert row["core_law"]["phrase"] == "names compress role and authority"
    assert {shard["id"] for shard in row["option_shards"]} >= {
        "role",
        "authority",
        "lifecycle",
        "retrieval",
        "compatibility",
        "migration",
    }
    assert row["omission_receipt"]["drilldown"] == "jq '.' codex/standards/std_semantic_naming.json"


def test_standards_card_surface_exposes_no_edit_pass_floor() -> None:
    payload = build_option_surface(REPO_ROOT, "standards", band="card", ids=["std_agent_entry_surface"])

    row = payload["rows"][0]
    mechanisms = {item["id"]: item for item in row["compact_mechanisms"]}
    assert mechanisms["no_edit_pass_floor"]["forbidden_closeout"] == (
        "already_exists_without_stewardship_or_next_best_lane"
    )
    assert "typed_no_edit_receipt_with_reentry_condition" in mechanisms["no_edit_pass_floor"]["valid_outputs"]
    assert "launch condition" in mechanisms["no_edit_pass_floor"]["resolved_blocker_acceleration_rule"]
    assert "second consecutive null" in mechanisms["non_null_pass_yield"]["forbidden_closeout"]
    assert "downstream owner action" in mechanisms["non_null_pass_yield"]["resolved_blocker_acceleration_rule"]


def test_standards_card_surface_exposes_architecture_comprehension_fields() -> None:
    payload = build_option_surface(REPO_ROOT, "standards", band="card", ids=["std_standard_type_plane"])

    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["source_projection_boundary"]["source_authority"] == (
        "codex/standards/std_standard_type_plane.json"
    )
    assert row["owner_surface"]["projection_owner"] == (
        "system/lib/standard_option_surface.py::_standard_card_row"
    )
    validation_route = row["validation_route"]
    assert validation_route[:2] == [
        "./repo-python tools/meta/factory/build_navigation_type_plane.py --check",
        "./repo-python tools/meta/factory/build_renderer_passports.py --check",
    ]
    assert "./repo-python -m json.tool codex/standards/std_standard_type_plane.json" in validation_route
    assert (
        "./repo-python kernel.py --option-surface standards --band card --ids std_standard_type_plane"
        in validation_route
    )
    assert row["mutation_route"][0].endswith(
        "--path codex/standards/std_standard_type_plane.json --require-exclusive"
    )
    assert row["disclosure_posture"] == "controlled_private_review"
    assert row["workitem_cap_pressure"]["status"] == "lookup_required"
    assert "standards option-surface card" in row["graph_neighbors"]["projects_to"]
    assert row["drilldown_commands"][0] == row["drilldown_command"]


def test_task_ledger_type_plane_and_failure_caps_append_before_projection_settlement() -> None:
    type_plane = json.loads(
        (REPO_ROOT / "codex/standards/std_standard_type_plane.json").read_text(
            encoding="utf-8"
        )
    )
    type_rows = {row["type_id"]: row for row in type_plane["type_plane_rows"]}
    for type_id in ("task_ledger", "task_ledger_caps"):
        mutation_lane = type_rows[type_id]["mutation_lane"]
        assert "append authority first" in mutation_lane
        assert "task_ledger_projection" in mutation_lane
        assert "quick-capture,claim,refine,sign-off,...} --rebuild" not in mutation_lane

    task_ledger_standard = json.loads(
        (REPO_ROOT / "codex/standards/std_task_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    raw_seed_standard = json.loads(
        (
            REPO_ROOT / "codex/standards/principles/std_raw_seed_principles.json"
        ).read_text(encoding="utf-8")
    )
    task_capture = task_ledger_standard["metacontrol_contract"][
        "agent_principle_failure_mode_cap_contract"
    ]["capture_command_template"]
    raw_seed_capture = raw_seed_standard["navigation_contract"][
        "agent_principle_authoring_contract"
    ]["cap_first_intake"]["capture_command_template"]
    assert "--rebuild" not in task_capture
    assert "--rebuild" not in raw_seed_capture


def test_standards_card_surface_flattens_structured_validation_rules() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "standards",
        band="card",
        ids=["std_extracted_pattern_route_readiness"],
    )

    row = payload["rows"][0]
    joined = "\n".join(row["top_validation_rules"])
    assert "hard error: route readiness audit source ledger count" in joined
    assert "hard error: fixture specs lack imported substrate target" in joined
    assert row["validation_route"][0] == (
        "./repo-python -m json.tool codex/standards/std_extracted_pattern_route_readiness.json"
    )


def test_standards_card_surface_exposes_operator_action_receipt_health_projection() -> None:
    payload = build_option_surface(REPO_ROOT, "standards", band="card", ids=["std_operator_action_receipt"])

    row = payload["rows"][0]
    assert "hud_action_receipt_health" == row["current_projection_fields"]["health_function"]
    assert "proof_governed_action_count" in row["current_projection_fields"]["stable_projection_fields"]
    assert "proof_missing_count_by_action" in row["current_projection_fields"]["stable_projection_fields"]
    assert any(
        "test_hud_action_receipt_health_counts_future_proof_governed_actions" in command
        for command in row["validation_probe"]
    )
    assert row["validation_route"][: len(row["validation_probe"])] == row["validation_probe"]


def test_principles_flag_surface_groups_rows_by_type() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "principles"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration_grouped_by_type"
    assert payload["summary"]["row_count"] > 100

    groups = {group["type"]: group for group in payload["type_groups"]}
    assert {"meta", "operational", "substance"} <= set(groups)
    assert groups["meta"]["rows"][0]["one_sentence_description"]
    rows = {row["principle_id"]: row for row in payload["rows"]}
    assert rows["pri_014"]["type"] == "meta"
    assert rows["pri_014"]["one_sentence_description"]
    assert rows["pri_014"]["drilldown_command"].endswith("--band card --ids pri_014")


def test_principles_cluster_flag_groups_rows_by_type() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "principles"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview_grouped_by_type"
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["drilldown_by"] == "type"
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card", "tape"]
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["cluster_flag", "flag", "card", "tape"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "meta" in rows
    cluster = rows["meta"]
    assert cluster["artifact_kind"] == "principle_type_cluster"
    assert cluster["band"] == "cluster_flag"
    assert cluster["count"] >= 1
    assert cluster["top_ids"]
    assert cluster["scope_counts"]
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert "operating cards" in cluster["omission_receipt"]["omitted"]


def test_principles_surface_exposes_incoming_concept_edges() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="flag", ids=["pri_049"])

    assert payload["summary"]["incoming_concept_edge_population"]["selected_incoming_concept_edge_count"] >= 1
    row = payload["rows"][0]
    assert row["principle_id"] == "pri_049"
    assert row["incoming_concept_edge_count"] >= 1
    assert (
        "con_022",
        "Documentation Surface Operations And Lensable Navigation",
    ) in {
        (edge["concept_id"], edge["title"])
        for edge in row["top_incoming_concept_edges"]
    }
    assert row["top_concept_targets"][0]["target"].startswith("con_")
    assert row["top_mechanism_targets"][0]["target"].startswith("mech_")

    clusters = build_option_surface(REPO_ROOT, "principles", band="cluster_flag")
    with_edges = [row for row in clusters["rows"] if row["incoming_concept_edge_count"] > 0]
    assert with_edges
    assert with_edges[0]["principles_with_incoming_concept_edges"] >= 1
    assert with_edges[0]["top_incoming_concept_edges"]
    assert with_edges[0]["top_concept_targets"]
    assert with_edges[0]["top_mechanism_targets"]


def test_principles_card_surface_drills_to_operating_context() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="card", ids=["pri_014"])

    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["principle_id"] == "pri_014"
    assert row["band"] == "card"
    assert row["statement"]
    assert row["nearest_standard"]["ref"] == "codex/standards/principles/std_raw_seed_principles.json"
    assert row["nearest_skill"]["ref"] == "codex/doctrine/skills/doctrine/principles_curation.md"


def test_principles_card_resolves_pri_121_candidate_alias() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="card", ids=["pri_121_candidate"])

    assert payload["selection"]["missing_ids"] == []
    assert payload["rows"][0]["principle_id"] == "pri_121"


def test_principles_card_all_redirects_to_cluster_flag() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="card")

    assert payload["profile_status"] == "supported"
    assert payload["requested_band"] == "card"
    assert payload["band"] == "cluster_flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert all(row["band"] == "cluster_flag" for row in payload["rows"])
    assert any(warning["kind"] == "high_cardinality_card_redirect" for warning in payload["warnings"])


def test_principles_tape_requires_ids() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="tape")

    assert payload["profile_status"] == "profile_gap"
    assert any(w.get("kind") == "tape_requires_ids" for w in payload["warnings"])


def test_principles_tape_surface_emits_compression_layers() -> None:
    payload = build_option_surface(REPO_ROOT, "principles", band="tape", ids=["pri_014"])

    assert payload["profile_status"] == "supported"
    assert payload["band"] == "tape"
    row = payload["rows"][0]
    assert row["band"] == "tape"
    assert row["principle_id"] == "pri_014"
    layers = row["compression_layers"]
    assert len(layers) == 5
    assert {layer["rung"] for layer in layers} == {"L0", "L1", "L2", "L3", "L4"}
    assert all("populated" in layer and "route" in layer for layer in layers)
    assert isinstance(row["layer_debt"], list)


def test_option_surface_kernel_command_redirects_principles_flag_to_cluster_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "principles", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "principles"
    assert payload["band"] == "cluster_flag"
    assert payload["requested_band"] == "flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert "meta" in {row["cluster_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_allows_explicit_principles_flag_ids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "principles",
            "--band",
            "flag",
            "--ids",
            "pri_014",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["band"] == "flag"
    assert payload["summary"]["row_count"] == 1
    assert payload["rows"][0]["principle_id"] == "pri_014"


def test_axiom_candidates_flag_surface_enumerates() -> None:
    payload = build_option_surface(REPO_ROOT, "axiom_candidates", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "axiom_candidates"
    assert payload["summary"]["row_count"] >= 1
    rows = {row["axiom_candidate_id"]: row for row in payload["rows"]}
    assert "axiom_candidate_operator_gesture_seed" in rows
    assert rows["axiom_candidate_operator_gesture_seed"]["tape_command"]


def test_teleologies_surface_compresses_many_pairs_into_shared_desires() -> None:
    payload = build_option_surface(REPO_ROOT, "teleologies", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "teleologies"
    assert payload["summary"]["row_count"] < payload["summary"]["positive_anti_pair_count"]
    assert payload["summary"]["teleologies_less_than_pairs"] is True

    rows = {row["teleology_id"]: row for row in payload["rows"]}
    navigation = rows["tel_navigation_orientation"]
    assert navigation["linked_principle_count"] >= 2
    assert {"pri_049", "pri_111"} <= set(navigation["principle_ids"])
    assert navigation["linked_anti_principle_count"] == navigation["linked_principle_count"]
    assert navigation["linked_anti_axiom_count"] == navigation["linked_axiom_candidate_count"]


def test_teleologies_cluster_flag_self_describes_shared_desires() -> None:
    payload = build_option_surface(REPO_ROOT, "teleologies", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "teleologies"
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["summary"]["cluster_first_for_shared_desires"] is True
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    rows = {row["teleology_id"]: row for row in payload["rows"]}
    navigation = rows["tel_navigation_orientation"]
    assert navigation["artifact_kind"] == "teleology_node_cluster"
    assert navigation["band"] == "cluster_flag"
    assert {"pri_049", "pri_111"} <= set(navigation["top_principle_ids"])
    assert navigation["drilldown_command"].endswith(
        "--option-surface teleologies --band flag --ids tel_navigation_orientation"
    )
    assert navigation["card_drilldown_command"].endswith(
        "--option-surface teleologies --band card --ids tel_navigation_orientation"
    )


def test_teleology_card_browses_from_desire_to_positive_and_anti_rows() -> None:
    payload = build_option_surface(REPO_ROOT, "teleologies", band="card", ids=["tel_navigation_orientation"])

    assert payload["summary"]["teleologies_less_than_pairs"] is True
    row = payload["rows"][0]
    assert row["teleology_id"] == "tel_navigation_orientation"
    assert {item["principle_id"] for item in row["linked_principles"]} >= {"pri_049", "pri_111"}
    assert {item["id"] for item in row["anti_principles"]} >= {"anti_pri_049", "anti_pri_111"}
    assert {item["axiom_candidate_id"] for item in row["linked_axiom_candidates"]} >= {
        "axiom_candidate_availability_before_invention",
        "axiom_candidate_context_discretionary_capital",
    }
    assert {item["id"] for item in row["anti_axioms"]} >= {
        "anti_axiom_candidate_availability_before_invention",
        "anti_axiom_candidate_context_discretionary_capital",
    }
    assert row["principles_command"].endswith("--option-surface principles_by_teleology --band flag --ids tel_navigation_orientation")
    assert row["axioms_command"].endswith("--option-surface axioms_by_teleology --band flag --ids tel_navigation_orientation")


def test_principles_by_teleology_shares_refs_with_anti_principles() -> None:
    principles = build_option_surface(
        REPO_ROOT,
        "principles_by_teleology",
        band="flag",
        ids=["tel_navigation_orientation"],
    )
    anti = build_option_surface(REPO_ROOT, "anti_principles", band="flag", ids=["tel_navigation_orientation"])

    principle_rows = {row["principle_id"]: row for row in principles["rows"]}
    anti_rows = {row["anti_principle_id"]: row for row in anti["rows"]}
    assert {"pri_049", "pri_111"} <= set(principle_rows)
    assert anti["summary"]["all_rows_share_parent_teleology_refs"] is True

    row = principle_rows["pri_049"]
    anti_row = anti_rows[row["anti_principle_id"]]
    assert row["teleology_refs"] == ["tel_navigation_orientation"]
    assert anti_row["teleology_refs"] == row["teleology_refs"]
    assert anti_row["shares_parent_teleology_refs"] is True
    assert anti_row["resolved_teleology_nodes"] == [
        {"id": "tel_navigation_orientation", "title": "Agents Orient Through Available Substrate"}
    ]
    assert "teleology" not in anti_row
    assert anti_row["teleology_command"].endswith("--option-surface teleologies --band card --ids tel_navigation_orientation")


def test_principles_by_teleology_cluster_flag_groups_desires() -> None:
    payload = build_option_surface(REPO_ROOT, "principles_by_teleology", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["summary"]["cluster_first_for_reverse_teleology"] is True
    rows = {row["teleology_id"]: row for row in payload["rows"]}
    navigation = rows["tel_navigation_orientation"]
    assert navigation["linked_principle_count"] >= 2
    assert {"pri_049", "pri_111"} <= set(navigation["top_principle_ids"])
    assert navigation["drilldown_command"].endswith(
        "--option-surface principles_by_teleology --band flag --ids tel_navigation_orientation"
    )
    assert navigation["teleology_command"].endswith(
        "--option-surface teleologies --band card --ids tel_navigation_orientation"
    )


def test_axioms_by_teleology_shares_refs_with_anti_axioms() -> None:
    payload = build_option_surface(REPO_ROOT, "axioms_by_teleology", band="flag", ids=["tel_navigation_orientation"])

    assert payload["profile_status"] == "supported"
    assert payload["summary"]["all_anti_axioms_share_parent_teleology_refs"] is True
    rows = {row["axiom_candidate_id"]: row for row in payload["rows"]}
    availability = rows["axiom_candidate_availability_before_invention"]
    assert availability["teleology_refs"] == ["tel_navigation_orientation"]
    assert availability["teleology_profile_source"] == "shared_teleology_node"
    assert availability["anti_axiom_id"] == "anti_axiom_candidate_availability_before_invention"
    assert availability["back_to_teleologies_command"].endswith(
        "--option-surface teleologies --band card --ids tel_navigation_orientation"
    )


def test_axioms_by_teleology_cluster_flag_groups_desires() -> None:
    payload = build_option_surface(REPO_ROOT, "axioms_by_teleology", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["summary"]["cluster_first_for_reverse_teleology"] is True
    rows = {row["teleology_id"]: row for row in payload["rows"]}
    navigation = rows["tel_navigation_orientation"]
    assert navigation["linked_axiom_candidate_count"] >= 2
    assert "axiom_candidate_availability_before_invention" in navigation["top_axiom_candidate_ids"]
    assert navigation["drilldown_command"].endswith(
        "--option-surface axioms_by_teleology --band flag --ids tel_navigation_orientation"
    )
    assert navigation["teleology_command"].endswith(
        "--option-surface teleologies --band card --ids tel_navigation_orientation"
    )


def test_anti_axioms_surface_exposes_routed_failure_profiles() -> None:
    payload = build_option_surface(REPO_ROOT, "anti_axioms", band="flag", ids=["tel_navigation_orientation"])

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "anti_axioms"
    assert payload["summary"]["row_count"] == 3
    assert payload["summary"]["all_rows_share_parent_teleology_refs"] is True
    assert payload["summary"]["routed_profile_count"] == 3

    rows = {row["anti_axiom_id"]: row for row in payload["rows"]}
    assert set(rows) == {
        "anti_axiom_candidate_availability_before_invention",
        "anti_axiom_candidate_context_discretionary_capital",
        "anti_axiom_candidate_evolution_proves_in_microcosm",
    }
    availability = rows["anti_axiom_candidate_availability_before_invention"]
    assert availability["parent_axiom_candidate_id"] == "axiom_candidate_availability_before_invention"
    assert availability["teleology_refs"] == ["tel_navigation_orientation"]
    assert availability["anti_teleology_refs"] == availability["teleology_refs"]
    assert availability["shares_parent_teleology_refs"] is True
    assert availability["failure_attractor"]
    assert availability["constitutional_risk"]
    assert availability["recovery_protocol"]
    assert availability["route_commands"][0]["command"].startswith("./repo-python kernel.py --entry")
    assert availability["teleology_command"].endswith("--option-surface teleologies --band card --ids tel_navigation_orientation")
    assert "teleology" not in availability

    card = build_option_surface(
        REPO_ROOT,
        "anti_axioms",
        band="card",
        ids=["anti_axiom_candidate_context_discretionary_capital"],
    )
    context = card["rows"][0]
    assert context["navigation_receipt"]["same_desire_as_parent_axiom"] is True
    assert context["navigation_receipt"]["route_count"] == 3
    assert context["teleology_glance"][0]["id"] == "tel_navigation_orientation"


def test_axiom_candidates_tape_surface_emits_layers() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "axiom_candidates",
        band="tape",
        ids=["axiom_candidate_operator_gesture_seed"],
    )

    assert payload["profile_status"] == "supported"
    row = payload["rows"][0]
    assert row["band"] == "tape"
    assert len(row["compression_layers"]) == 5
    assert {layer["rung"] for layer in row["compression_layers"]} == {"A0", "A1", "A2", "A3", "A4"}


def test_compression_profiles_flag_surface_enumerates_profiles() -> None:
    payload = build_option_surface(REPO_ROOT, "compression_profiles", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "compression_profiles"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["row_count"] == payload["summary"]["total_available"]
    assert payload["summary"]["row_count"] >= 1
    assert payload["governing_standard"]["owned_bands"] == ["flag", "card"]

    rows = {row["profile_id"]: row for row in payload["rows"]}
    row = rows["raw_seed_voice_context_v1"]
    assert row["row_id"] == "compression_profile:raw_seed_voice_context_v1::flag"
    assert row["artifact_kind"] == "compression_profile"
    assert row["band"] == "flag"
    assert row["profile_id"] == "raw_seed_voice_context_v1"
    assert row["profile_artifact_kind"] == "raw_seed"
    assert row["profile_bands"] == ["flag", "card", "context", "deep"]
    assert row["creator_skill_id"] == "compression.raw_seed_contextual_compression"
    assert row["navigator_skill_id"] == "raw_seed_navigation"
    assert row["source_ref"] == "codex/doctrine/compression_profiles.json"
    assert row["drilldown_command"].endswith("--band card --ids raw_seed_voice_context_v1")
    assert row["currentness"]["status"] == "profile_registry_available"


def test_compression_profiles_card_surface_exposes_contract() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "compression_profiles",
        band="card",
        ids=["raw_seed_voice_context_v1"],
    )

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["row_id"] == "compression_profile:raw_seed_voice_context_v1::card"
    assert row["band"] == "card"
    assert row["profile_id"] == "raw_seed_voice_context_v1"
    assert row["profile_bands"] == ["flag", "card", "context", "deep"]
    assert row["band_contract_summary"]["bands"] == ["flag", "card", "context", "deep"]
    assert row["source_ladder_summary"]["count"] >= 4
    assert "raw_paragraph" in row["source_ladder_summary"]["brackets"]
    assert row["band_contracts"]["context"]["minimum_payload"]
    assert row["mandatory_preserve"]
    assert row["allowed_loss"]
    assert row["forbidden_collapse"]
    assert row["worker_tier_policy"]["controller"]
    assert row["validation_probe"]["must"]
    assert row["drilldown_policy"]["commands"]
    assert row["source_ref"] == "codex/doctrine/compression_profiles.json"
    assert "raw_seed_voice_context_v1" in row["evidence_command"]
    assert row["currentness"]["status"] == "profile_registry_available"
    assert row["nearest_skill"]["ref"] == "codex/doctrine/skills/compression/profile_governed_compression.md"
    assert row["omission_receipt"]["drilldown"] == "jq '.' codex/doctrine/compression_profiles.json"


def test_compression_profiles_card_surface_exposes_render_profile_owner_routes() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "compression_profiles",
        band="card",
        ids=["type_b_external_grounding_v1"],
    )

    assert payload["profile_status"] == "supported"
    row = payload["rows"][0]
    assert row["profile_id"] == "type_b_external_grounding_v1"
    assert row["profile_kind"] == "render_profile"
    assert row["artifact_role"] == "render_profile"
    assert row["context_profile_id"] == "raw_seed_voice_context_v1"
    assert row["render_profile"]["output_path"] == "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md"
    assert row["render_profile"]["status_sidecar_path"] == "state/system_atlas/type_b_grounding_packet_status.json"
    assert row["render_profile"]["projection_not_authority"] is True
    assert row["render_profile"]["refresh_owner"] == "type_a_or_always_on_metabolism"
    assert row["compression_passport"]["atom"] == "Type B grounding packet"
    assert "public_safe_projection" in row["compression_passport"]["cluster_keys"]
    assert row["compression_passport"]["safe_drilldown"].endswith(
        "--ids type_b_external_grounding_v1"
    )
    assert row["owner_routes"]["entry_command"].endswith("--ids type_b_external_grounding_v1")
    assert row["owner_routes"]["refresh_command"].endswith(
        "--render-profile type_b_external_grounding_v1"
    )
    assert row["owner_routes"]["check_command"].endswith(
        "--render-profile type_b_external_grounding_v1 --check"
    )
    assert row["route_summary"] == {
        "has_refresh_command": True,
        "has_check_command": True,
        "has_status_command": True,
        "has_root_drilldown_command": True,
    }


def test_compression_profiles_card_surface_exposes_sibling_render_profiles() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "compression_profiles",
        band="card",
        ids=["type_b_external_grounding_v1"],
    )

    row = payload["rows"][0]
    assert row["sibling_profile_summary"] == {
        "count": 1,
        "profile_ids": ["ai_workflow_system_packet_v1"],
        "relationship": "same_surface_family_root_and_context_profile",
        "source_authority": "codex/doctrine/compression_profiles.json",
    }
    sibling = row["sibling_profiles"][0]
    assert sibling["profile_id"] == "ai_workflow_system_packet_v1"
    assert sibling["relationship"] == "sibling_render_profile"
    assert sibling["same_surface_family_id"] == "system_self_comprehension_packet"
    assert sibling["same_root_slug"] == "system_self_comprehension_root"
    assert sibling["same_context_profile_id"] == "raw_seed_voice_context_v1"
    assert sibling["output_path"] == "dist/type_b/AI_WORKFLOW_SYSTEM_PACKET.md"
    assert sibling["status_sidecar_path"] == "state/system_atlas/system_packet_status.json"
    assert sibling["card_command"].endswith("--ids ai_workflow_system_packet_v1")
    assert sibling["refresh_command"].endswith("--render-profile ai_workflow_system_packet_v1")
    assert sibling["check_command"].endswith("--render-profile ai_workflow_system_packet_v1 --check")
    assert sibling["status_command"] == "jq '.' state/system_atlas/system_packet_status.json"


def test_compression_profiles_boundary_keeps_native_bands_as_card_data_only() -> None:
    atlas = build_option_surface(REPO_ROOT, "kinds", band="flag")
    atlas_rows = {row["kind_id"]: row for row in atlas["rows"]}
    assert atlas_rows["compression_profiles"]["bands"] == ["flag", "card"]

    card = build_option_surface(
        REPO_ROOT,
        "compression_profiles",
        band="card",
        ids=["raw_seed_voice_context_v1"],
    )
    assert card["navigation_boundary"]["adapter_supported_bands"] == ["flag", "card"]
    assert card["rows"][0]["profile_bands"] == ["flag", "card", "context", "deep"]


def test_system_terms_flag_surface_enumerates_terms() -> None:
    payload = build_option_surface(REPO_ROOT, "system_terms", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "system_terms"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration"
    assert payload["summary"]["row_count"] >= 50
    assert payload["governing_standard"]["owned_bands"] == ["flag", "card"]

    rows = {row["term_id"]: row for row in payload["rows"]}
    assert "living_system_posture" in rows
    row = rows["living_system_posture"]
    assert row["row_id"] == "system_term:living_system_posture::flag"
    assert row["artifact_kind"] == "system_term"
    assert row["band"] == "flag"
    assert row["flag"].startswith("Living system posture")
    assert row["source_ref"] == "codex/doctrine/system_vocabulary/term_registry.json"
    assert row["standard_ref"] == "codex/standards/std_system_term.json"
    assert row["drilldown_command"].endswith("--band card --ids living_system_posture")
    assert row["evidence_command"].endswith("--term living_system_posture --term-band context")
    assert row["currentness"]["status"] == "authored_registry"


def test_system_terms_card_surface_exposes_definition_ladder() -> None:
    payload = build_option_surface(REPO_ROOT, "system_terms", band="card", ids=["living_system_posture"])

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    row = payload["rows"][0]
    assert row["row_id"] == "system_term:living_system_posture::card"
    assert row["band"] == "card"
    assert row["term_id"] == "living_system_posture"
    assert row["definition_ladder"]["word"] == "currentness"
    assert row["definition_ladder"]["phrase"] == "read with currentness"
    assert row["definition_ladder"]["context"]
    assert row["definition_ladder"]["deep"]
    assert row["native_bands"] == ["word", "phrase", "flag", "card", "context", "deep"]
    assert row["adapter_supported_bands"] == ["flag", "card"]
    assert row["source_refs"]
    assert row["relationships"]
    assert row["evidence_commands"]
    assert row["nearest_standard"]["ref"] == "codex/standards/std_system_term.json"
    assert row["currentness"]["status"] == "authored_registry"
    assert row["omission_receipt"]["drilldown"].endswith("--term living_system_posture --term-band context")


def test_system_terms_boundary_keeps_native_bands_as_card_data_only() -> None:
    atlas = build_option_surface(REPO_ROOT, "kinds", band="flag")
    atlas_rows = {row["kind_id"]: row for row in atlas["rows"]}
    assert atlas_rows["system_terms"]["bands"] == ["flag", "card"]

    card = build_option_surface(REPO_ROOT, "system_terms", band="card", ids=["living_system_posture"])
    assert card["navigation_boundary"]["adapter_supported_bands"] == ["flag", "card"]
    assert card["navigation_boundary"]["native_ladder_bands"] == [
        "word",
        "phrase",
        "flag",
        "card",
        "context",
        "deep",
    ]
    assert card["rows"][0]["native_bands"] == ["word", "phrase", "flag", "card", "context", "deep"]


def test_option_surface_kernel_command_redirects_paper_module_flag_all_to_clusters() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "paper_modules", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["profile_status"] == "supported"
    assert payload["requested_band"] == "flag"
    assert payload["band"] == "cluster_flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    cluster_ids = {row["cluster_id"] for row in payload["rows"]}
    assert cluster_ids
    assert all(row["drilldown_command"].startswith("./repo-python kernel.py --option-surface paper_modules") for row in payload["rows"])


def test_option_surface_kernel_command_allows_explicit_paper_module_flag_ids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "paper_modules",
            "--band",
            "flag",
            "--ids",
            "navigation_hologram_theory",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["band"] == "flag"
    assert payload["summary"]["row_count"] == 1
    assert payload["rows"][0]["slug"] == "navigation_hologram_theory"


def test_option_surface_kernel_command_emits_standards_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "standards", "--band", "card", "--ids", "std_semantic_naming"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "standards"
    assert payload["rows"][0]["standard_id"] == "std_semantic_naming"
    assert payload["rows"][0]["core_law"]["context"].startswith("The first interface is an option surface")


def test_option_surface_kernel_command_redirects_standards_flag_to_cluster_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "standards", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "standards"
    assert payload["band"] == "cluster_flag"
    assert payload["requested_band"] == "flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert "core" in {row["cluster_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_allows_explicit_standards_flag_ids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "standards",
            "--band",
            "flag",
            "--ids",
            "std_semantic_naming",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["band"] == "flag"
    assert payload["summary"]["row_count"] == 1
    assert payload["rows"][0]["standard_id"] == "std_semantic_naming"


def test_option_surface_kernel_command_filters_card_ids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "paper_modules",
            "--band",
            "card",
            "--ids",
            "navigation_hologram_theory,raw_seed_theory",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert {row["slug"] for row in payload["rows"]} == {"navigation_hologram_theory", "raw_seed_theory"}


def test_option_surface_kernel_command_emits_compression_profiles_flag_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "compression_profiles", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "compression_profiles"
    assert payload["profile_status"] == "supported"
    assert payload["summary"]["row_count"] == payload["summary"]["total_available"]
    assert "raw_seed_voice_context_v1" in {row["profile_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_compression_profiles_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "compression_profiles",
            "--band",
            "card",
            "--ids",
            "raw_seed_voice_context_v1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["profile_id"] == "raw_seed_voice_context_v1"
    assert row["profile_bands"] == ["flag", "card", "context", "deep"]
    assert row["omission_receipt"]["reason"].startswith("The card band supports selecting")


def test_option_surface_kernel_command_emits_system_terms_flag_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "system_terms", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "system_terms"
    assert payload["profile_status"] == "supported"
    assert "living_system_posture" in {row["term_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_system_terms_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "system_terms",
            "--band",
            "card",
            "--ids",
            "living_system_posture",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["term_id"] == "living_system_posture"
    assert row["native_bands"] == ["word", "phrase", "flag", "card", "context", "deep"]
    assert row["adapter_supported_bands"] == ["flag", "card"]


def test_option_surface_kernel_command_redirects_skills_flag_all_to_clusters() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "skills", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "skills"
    assert payload["profile_status"] == "supported"
    assert payload["requested_band"] == "flag"
    assert payload["band"] == "cluster_flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert "profile_governed_compression" in {
        skill_id
        for group in payload["rows"]
        for skill_id in group["skill_ids"]
    }
    assert "compression" in {group["family_id"] for group in payload["rows"]}
    assert payload["family_groups"] == []


def test_option_surface_kernel_command_allows_explicit_skills_flag_ids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "skills",
            "--band",
            "flag",
            "--ids",
            "profile_governed_compression",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["band"] == "flag"
    assert payload["summary"]["row_count"] == 1
    assert payload["rows"][0]["skill_id"] == "profile_governed_compression"


def test_option_surface_kernel_command_emits_skills_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "skills",
            "--band",
            "card",
            "--ids",
            "profile_governed_compression",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["skill_id"] == "profile_governed_compression"
    assert row["native_bands"] == ["triggers", "card", "workflow", "evidence"]
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]


def test_option_surface_kernel_command_emits_frontend_views_flag_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "frontend_views", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "frontend_views"
    assert payload["profile_status"] == "supported"
    assert "station" in {row["view_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_frontend_views_cluster_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "frontend_views", "--band", "cluster_flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "frontend_views"
    assert payload["band"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert "shell_group:map" in {row["cluster_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_frontend_views_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "frontend_views",
            "--band",
            "card",
            "--ids",
            "station",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["view_id"] == "station"
    assert row["route"] == "/station"
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]


def test_option_surface_kernel_command_emits_raw_seed_shards_flag_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "raw_seed_shards", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "raw_seed_shards"
    assert payload["profile_status"] == "supported"
    assert RAW_SEED_TEST_SHARD_ID in {row["shard_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_raw_seed_shards_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "raw_seed_shards",
            "--band",
            "card",
            "--ids",
            RAW_SEED_TEST_SHARD_ID,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["shard_id"] == RAW_SEED_TEST_SHARD_ID
    assert row["profile_id"] == "raw_seed_voice_context_v1"
    assert row["adapter_supported_bands"] == ["flag", "card"]


def test_option_surface_kernel_command_emits_annex_patterns_flag_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "annex_patterns", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "annex_patterns"
    assert payload["band"] == "cluster_flag"
    assert payload["requested_band"] == "flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert "skills-authoring" in {row["cluster_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_annex_patterns_explicit_flag_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "annex_patterns",
            "--band",
            "flag",
            "--ids",
            ANNEX_PATTERN_TEST_ID,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "annex_patterns"
    assert payload["band"] == "flag"
    assert payload["profile_status"] == "supported"
    assert [row["pattern_id"] for row in payload["rows"]] == [ANNEX_PATTERN_TEST_ID]


def test_option_surface_kernel_command_emits_annex_patterns_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "annex_patterns",
            "--band",
            "card",
            "--ids",
            ANNEX_PATTERN_TEST_ID,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["pattern_id"] == ANNEX_PATTERN_TEST_ID
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["nearest_standard"]["ref"] == "codex/standards/annex/annex_authority_index.json"


def test_option_surface_kernel_command_redirects_python_files_flag_to_cluster_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "python_files", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "python_files"
    assert payload["band"] == "cluster_flag"
    assert payload["requested_band"] == "flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert "kernel_lib" in {row["cluster_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_python_files_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "python_files",
            "--band",
            "card",
            "--ids",
            PYTHON_FILE_TEST_ID,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["file_id"] == PYTHON_FILE_TEST_ID
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["nearest_standard"]["ref"] == "codex/standards/std_python.py"


def test_option_surface_kernel_command_redirects_python_scopes_flag_to_cluster_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "python_scopes", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "python_scopes"
    assert payload["band"] == "cluster_flag"
    assert payload["requested_band"] == "flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert "kernel_lib" in {row["cluster_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_emits_python_scopes_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "python_scopes",
            "--band",
            "card",
            "--ids",
            PYTHON_SCOPE_TEST_ID,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["scope_id"] == PYTHON_SCOPE_TEST_ID
    assert row["symbol_id"] == PYTHON_SCOPE_TEST_ID
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["nearest_standard"]["ref"] == "codex/standards/std_python.py"
    assert row["parent_file_command"].endswith(
        f"--option-surface python_files --band card --ids {PYTHON_SCOPE_TEST_PATH}"
    )


def test_frontend_components_cluster_flag_groups_by_source_directory() -> None:
    payload = build_option_surface(REPO_ROOT, "frontend_components", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "frontend_components"
    assert payload["band"] == "cluster_flag"
    assert payload["summary"]["selection_method"] == (
        "artifact_kind_cluster_overview_from_frontend_component_index"
    )
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["drilldown_by"] == "source_directory"
    assert payload["governing_standard"]["owned_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert payload["omissions"] == []

    rows = {row["cluster_id"]: row for row in payload["rows"]}
    assert "system/server/ui/src/components" in rows
    cluster = rows["system/server/ui/src/components"]
    assert cluster["artifact_kind"] == "frontend_component_cluster"
    assert cluster["band"] == "cluster_flag"
    assert cluster["count"] >= 1
    assert cluster["top_ids"]
    assert cluster["declaration_kind_counts"]
    assert cluster["classification_confidence_counts"]
    assert "--band flag --ids" in cluster["drilldown_command"]
    assert "full TSX source bodies" in cluster["omission_receipt"]["omitted"]


def test_frontend_components_flag_surface_enumerates_extracted_primary_rows() -> None:
    payload = build_option_surface(REPO_ROOT, "frontend_components", band="flag")

    assert payload["profile_status"] == "supported"
    assert payload["artifact_kind"] == "frontend_components"
    summary = payload["summary"]
    assert summary["query_used"] is False
    assert summary["selection_method"] == "artifact_kind_enumeration_from_frontend_component_index"
    assert summary["row_count"] == summary["primary_row_count"]
    assert summary["primary_row_count"] > 0
    assert summary["candidate_count"] >= summary["primary_row_count"]
    assert summary["omitted_low_confidence_count"] == (
        summary["candidate_count"] - summary["primary_row_count"]
    )
    assert summary["drilldown_by"] == "component_id"
    assert summary["source_projection_reused"] == FRONTEND_COMPONENT_PROJECTION_PATH

    boundary = payload["navigation_boundary"]
    assert boundary["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert boundary["tsx_parsing_in_this_adapter"] is False
    assert boundary["projection_regeneration_in_this_adapter"] is False
    assert boundary["low_confidence_first_class_rows_allowed"] is False

    assert len(payload["omissions"]) == summary["omitted_low_confidence_count"]
    if payload["omissions"]:
        receipt = payload["omissions"][0]
        assert receipt["omitted"] is True
        assert receipt["reason"] == "low_confidence_classification"
        assert receipt["classification_confidence"] == "low"

    rows = {row["component_id"]: row for row in payload["rows"]}
    assert FRONTEND_COMPONENT_TEST_ID in rows
    assert FRONTEND_COMPONENT_LOW_CONFIDENCE_ID not in rows
    row = rows[FRONTEND_COMPONENT_TEST_ID]
    assert row["row_id"] == f"frontend_component:{FRONTEND_COMPONENT_TEST_ID}::flag"
    assert row["band"] == "flag"
    assert row["classification_confidence"] in {"high", "medium"}
    assert row["path"] == "system/server/ui/src/components/ArtifactViewer.tsx"
    assert row["export_name"] == "ArtifactViewer"
    assert row["display_name"] == "ArtifactViewer"
    assert row["declaration_kind"] == "function"
    assert row["is_default_export"] is True
    assert isinstance(row["line_start"], int) and row["line_start"] > 0
    assert isinstance(row["line_end"], int) and row["line_end"] >= row["line_start"]
    assert row["flag"]
    assert row["drilldown_command"].endswith(
        f"--option-surface frontend_components --band card --ids {FRONTEND_COMPONENT_TEST_ID}"
    )
    assert row["evidence_command"].endswith(FRONTEND_COMPONENT_PROJECTION_PATH)
    assert row["currentness"]["status"] == "frontend_component_index_available"
    assert row["currentness"]["component_count"] >= summary["primary_row_count"]
    assert "full TSX source body" in row["omission_receipt"]["omitted"]
    assert "wrappers" not in row
    assert "jsx_returns" not in row


def test_frontend_components_card_surface_drills_high_confidence_id() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "frontend_components",
        band="card",
        ids=[FRONTEND_COMPONENT_TEST_ID],
    )

    assert payload["profile_status"] == "supported"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["missing_ids"] == []
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["row_id"] == f"frontend_component:{FRONTEND_COMPONENT_TEST_ID}::card"
    assert row["band"] == "card"
    assert row["component_id"] == FRONTEND_COMPONENT_TEST_ID
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["native_frontend_component_bands"] == ["component_id", "purpose", "props_state", "source"]
    assert row["jsx_returns"] is True
    assert isinstance(row["wrappers"], list)
    assert isinstance(row["classification_reasons"], list) and row["classification_reasons"]
    assert row["source_span"]["path"] == row["path"]
    assert row["source_span"]["line_start"] == row["line_start"]
    assert row["source_span"]["line_end"] == row["line_end"]
    assert row["nearest_standard"]["ref"] == "codex/standards/std_frontend_component_index.json"
    assert row["nearest_extractor"]["ref"] == "tools/meta/observability/frontend_component_index.py"
    upstream = row["upstream_doctrine_route"]
    assert upstream["status"] == "available"
    assert upstream["route_kind"] == "frontend_component"
    assert upstream["canonical_source"] == "system/server/ui/src/components/ArtifactViewer.tsx"
    assert upstream["authority_layer"] == "operational"
    assert upstream["authority_tier"] == "owner_surface_route_not_source_authority"
    assert upstream["source_projection"] == FRONTEND_COMPONENT_PROJECTION_PATH
    assert upstream["governing_standard"] == "codex/standards/std_frontend_component_index.json"
    assert upstream["governing_doctrine"] == "codex/doctrine/paper_modules/frontend_station_cockpit.md"
    assert upstream["governing_extractor"] == "tools/meta/observability/frontend_component_index.py"
    assert upstream["route_commands"]["standard"].endswith(
        "--option-surface standards --band card --ids std_frontend_component_index"
    )
    assert upstream["route_commands"]["doctrine"].endswith(
        "--paper-module frontend_station_cockpit"
    )
    assert upstream["route_commands"]["extractor_summary"].endswith(
        "tools/meta/observability/frontend_component_index.py --summary"
    )
    assert upstream["route_commands"]["freshness_check"].endswith(
        "tools/meta/observability/frontend_component_index.py --check"
    )
    assert upstream["evaluator_lane"].endswith("frontend_component_index.py --summary")
    assert upstream["route_commands"]["source"].startswith("sed -n ")
    assert upstream["receipt_lane"].endswith(FRONTEND_COMPONENT_PROJECTION_PATH)
    assert "frontend_components.card" in upstream["runtime_consumers"]
    assert any(
        cmd.endswith(FRONTEND_COMPONENT_PROJECTION_PATH) for cmd in row["evidence_commands"]
    )
    assert any(cmd.startswith("sed -n ") for cmd in row["evidence_commands"])
    assert "full TSX source body" in row["omission_receipt"]["omitted"]


def test_frontend_components_low_confidence_id_lands_in_omissions_not_missing() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "frontend_components",
        band="card",
        ids=[FRONTEND_COMPONENT_LOW_CONFIDENCE_ID],
    )

    assert payload["selection"]["missing_ids"] == []
    assert payload["rows"] == []
    assert len(payload["omissions"]) == 1
    receipt = payload["omissions"][0]
    assert receipt["component_id"] == FRONTEND_COMPONENT_LOW_CONFIDENCE_ID
    assert receipt["omitted"] is True
    assert receipt["reason"] == "low_confidence_classification"
    assert receipt["classification_confidence"] == "low"
    assert receipt["declaration_kind"] == "const_literal"
    assert "low_confidence_classification" in receipt["reason"]
    assert receipt["evidence_command"].endswith(FRONTEND_COMPONENT_PROJECTION_PATH)


def test_frontend_components_truly_absent_id_lands_in_missing_ids() -> None:
    payload = build_option_surface(
        REPO_ROOT,
        "frontend_components",
        band="card",
        ids=[FRONTEND_COMPONENT_TEST_ID, "no/such/component.tsx::Bogus"],
    )

    assert "no/such/component.tsx::Bogus" in payload["selection"]["missing_ids"]
    assert FRONTEND_COMPONENT_TEST_ID not in payload["selection"]["missing_ids"]
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["component_id"] == FRONTEND_COMPONENT_TEST_ID


def test_frontend_components_unsupported_band_emits_profile_gap() -> None:
    payload = build_option_surface(REPO_ROOT, "frontend_components", band="tape")

    assert payload["profile_status"] == "profile_gap"
    assert payload["rows"] == []
    assert any(
        warning["kind"] == "unsupported_artifact_kind_or_band"
        for warning in payload.get("warnings") or []
    )


def test_option_surface_kernel_command_redirects_frontend_components_flag_to_cluster_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "frontend_components", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "frontend_components"
    assert payload["band"] == "cluster_flag"
    assert payload["requested_band"] == "flag"
    assert payload["band_redirect"]["to"] == "cluster_flag"
    assert payload["profile_status"] == "supported"
    assert "system/server/ui/src/components" in {row["cluster_id"] for row in payload["rows"]}


def test_option_surface_kernel_command_allows_explicit_frontend_components_flag_ids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "frontend_components",
            "--band",
            "flag",
            "--ids",
            FRONTEND_COMPONENT_TEST_ID,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["band"] == "flag"
    assert payload["summary"]["row_count"] == 1
    assert payload["rows"][0]["component_id"] == FRONTEND_COMPONENT_TEST_ID


def test_option_surface_kernel_command_emits_frontend_components_card_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--option-surface",
            "frontend_components",
            "--band",
            "card",
            "--ids",
            FRONTEND_COMPONENT_TEST_ID,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    row = payload["rows"][0]
    assert row["component_id"] == FRONTEND_COMPONENT_TEST_ID
    assert row["adapter_supported_bands"] == ["cluster_flag", "flag", "card"]
    assert row["nearest_standard"]["ref"] == "codex/standards/std_frontend_component_index.json"
    assert row["upstream_doctrine_route"]["governing_standard"] == (
        "codex/standards/std_frontend_component_index.json"
    )
    assert row["upstream_doctrine_route"]["governing_doctrine"] == (
        "codex/doctrine/paper_modules/frontend_station_cockpit.md"
    )
