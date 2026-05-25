"""Regression coverage for the coverage-first enforcement matrix."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.navigation_context_pack import HIGH_CARDINALITY_THRESHOLD
from system.lib.navigation_coverage_matrix import _debt_is_coverage_watch, build_coverage_enforcement_matrix


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_coverage_enforcement_matrix_marks_skill_find_as_drilldown_only() -> None:
    payload = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="coverage first skill discovery",
        context_budget=40000,
    )

    assert payload["kind"] == "coverage_enforcement_matrix"
    assert payload["schema_version"] == "coverage_enforcement_matrix_v0"
    assert payload["strategy"]["read_only_composer"] is True
    assert payload["strategy"]["new_registry_created"] is False
    assert payload["strategy"]["coverage_is_not_permission"] is True
    assert payload["strategy"]["control_entry_required"] is True
    assert payload["summary"]["kind_count"] >= 25
    assert payload["summary"]["coverage_surface_available_count"] >= 1
    assert payload["summary"]["coverage_matrix_scope"] == "kind_atlas_rows"
    assert payload["summary"]["kind_atlas_coverage_surface_available_count"] == payload["summary"][
        "coverage_surface_available_count"
    ]
    type_plane_resolution = payload["type_plane_resolution"]
    extra_type_plane_count = type_plane_resolution["extra_resolved_surface_count"]
    extra_type_plane_ids = {row["type_id"] for row in type_plane_resolution["extra_resolved_routes"]}
    assert extra_type_plane_count >= 3
    assert payload["summary"]["standard_type_plane_resolved_surface_count"] == extra_type_plane_count
    assert payload["summary"]["resolved_route_surface_count"] == (
        payload["summary"]["coverage_surface_available_count"] + extra_type_plane_count
    )
    assert payload["summary"]["coverage_surface_resolution_sources"] == {
        "kind_atlas": payload["summary"]["coverage_surface_available_count"],
        "standard_type_plane": extra_type_plane_count,
    }
    assert payload["summary"]["control_entry_allowed_count"] == 0
    assert payload["process_audit_regression_pressure"]["hook_shadow_coverage"]["authority"] == (
        "anti_pattern_id_then_repair_class"
    )
    source_freshness = payload["process_audit_regression_pressure"]["source_freshness"]
    assert source_freshness["patch_selection_policy"] in {
        "refresh_before_selecting_process_audit_source_patch",
        "cached_read_model_ok_for_process_audit_patch_selection",
    }
    assert source_freshness["authoritative_decision_command"] == (
        "./repo-python kernel.py --process-bottlenecks --force"
    )
    behavior_lifecycle = payload["process_audit_regression_pressure"]["behavior_lifecycle_summary"]
    assert behavior_lifecycle["active_behavior_debt_count"] >= 0
    assert behavior_lifecycle["advisory_behavior_debt_count"] >= 1
    assert behavior_lifecycle["retired_by_navigation_mechanism_count"] >= 1
    assert "active behavior routing should prefer rows where active_debt is true" in behavior_lifecycle["rule"]
    top_behavior_rows = payload["process_audit_regression_pressure"]["top_behavior_rows"]
    fast_path = payload["process_audit_fast_path"]
    next_command_texts = [item["command"] for item in payload["next_commands"]]
    assert len(next_command_texts) == len(set(next_command_texts))
    assert "full coverage matrix rows" in fast_path["rule"] or "matrix rows as the audit surface" in fast_path["rule"]
    if behavior_lifecycle["active_behavior_debt_count"]:
        assert top_behavior_rows[0]["debt_lifecycle_state"] == "active"
        assert top_behavior_rows[0]["active_debt"] is True
        assert fast_path["status"] == "active_behavior_debt"
        assert fast_path["debt"]["debt_lifecycle_state"] == "active"
        assert fast_path["debt"]["active_debt"] is True
        assert fast_path["owner_card_command"] or fast_path["process_bottleneck_quote_command"]
        if fast_path["owner_card_command"]:
            assert fast_path["owner_card_command"].startswith("./repo-python kernel.py --option-surface")
        if fast_path["authoritative_decision_command"]:
            assert fast_path["authoritative_decision_command"] in {
                "./repo-python kernel.py --process-bottlenecks --force",
                './repo-python kernel.py --navigation-metabolism "anti_pattern_deep_without_ladder owner route" --metabolism-profile quick --context-budget 12000',
            }
        assert fast_path["source_freshness"] == source_freshness
        assert fast_path["target_files"]
        assert payload["next_commands"][0]["command"] in {
            fast_path["owner_card_command"],
            fast_path["process_bottleneck_quote_command"],
        }
    else:
        assert all(row["debt_lifecycle_state"] != "active" for row in top_behavior_rows)
        assert all(row["active_debt"] is False for row in top_behavior_rows)
        assert fast_path["status"] == "no_active_behavior_debt"
        assert fast_path["next_commands"] == []
    assert behavior_lifecycle["advisory_behavior_debt_ids"]
    assert (
        "behavior:process_audit:anti_pattern_stall_detected"
        in behavior_lifecycle["retired_behavior_debt_ids"]
    )
    assert type_plane_resolution["coverage_matrix_scope"] == "kind_atlas_rows"
    assert type_plane_resolution["authority_ref"] == "codex/standards/std_standard_type_plane.json"
    assert {
        "public_microcosm_exports",
        "routes_and_option_surfaces",
        "task_ledger_caps",
    } <= extra_type_plane_ids
    assert all(
        row["coverage_relationship"] == "resolved_by_standard_type_plane_not_matrix_kind_row"
        for row in type_plane_resolution["extra_resolved_routes"]
    )

    rows = {row["kind_id"]: row for row in payload["rows"]}
    skills = rows["skills"]
    assert skills["atlas_visible"] is True
    assert skills["cluster_flag_available"] is True
    assert skills["surface_role"] == "ATLAS_PROJECTION"
    assert skills["coverage_surface_available"] is True
    assert skills["atlas_projection_available"] is True
    assert skills["control_entry_allowed"] is False
    assert skills["first_contact_policy"] == "entry_packet_required"
    assert skills["entry_replacement"].startswith("./repo-python kernel.py --entry")
    assert skills["coverage_surface"].endswith("--option-surface skills --band cluster_flag")
    assert "first_contact_allowed" not in skills
    assert "first_contact_surface" not in skills
    assert skills["route_lifecycle_status"]["exact_lookup"]["route_id"] == "skill_find"
    # skill_find is now active_typed_debug_trace: actively-maintained DEBUG_TRACE-restricted
    # surface (not a deprecation candidate). Live --skill-find blocks first-contact and
    # preserves --debug exact-id lookup.
    assert skills["route_lifecycle_status"]["exact_lookup"]["status"] == "active_typed_debug_trace"
    assert skills["coverage_status"] == "covered"
    assert skills["process_audit_violations"]["direct_count"] == 0
    assert "behavior:skill_find_first_contact:policy_gap" not in skills["process_audit_violations"][
        "top_direct_debt_ids"
    ]
    assert "global_count" not in skills["process_audit_violations"]

    paper_modules = rows["paper_modules"]
    assert paper_modules["cluster_flag_available"] is True
    assert paper_modules["surface_role"] == "ATLAS_PROJECTION"
    assert paper_modules["coverage_surface_available"] is True
    assert paper_modules["control_entry_allowed"] is False
    assert paper_modules["coverage_status"] == "covered"
    assert paper_modules["route_lifecycle_status"]["all_row_flag"]["status"] == "compatibility_shim"
    assert paper_modules["process_audit_violations"]["direct_count"] >= 1
    assert paper_modules["process_audit_violations"]["blocking_count"] == 0
    assert paper_modules["process_audit_violations"]["accepted_projected_count"] >= 1
    assert "mpc_9008b18dd3f052e2" in paper_modules["process_audit_violations"]["accepted_projected_claim_ids"]
    assert any(
        row["future_observation_status"] in {"awaiting_observation", "observed"}
        for row in paper_modules["process_audit_violations"]["accepted_projected_repairs"]
    )
    paper_projection = next(
        row
        for row in paper_modules["debt_pressure"]["top_debt_rows"]
        if row["debt_id"] == "projection:paper_modules.row_flag_all.library"
    )
    assert paper_projection["library_reference_only"] is True
    assert "CLI redirects" in paper_projection["compatibility_behavior"]
    assert paper_modules["debt_pressure"]["coverage_watch_debt_count"] == 0

    derived_facts = rows["derived_facts"]
    assert derived_facts["surface_role"] == "ATLAS_PROJECTION"
    assert derived_facts["coverage_surface_available"] is True
    assert derived_facts["atlas_projection_available"] is True
    assert derived_facts["control_entry_allowed"] is False
    assert derived_facts["coverage_status"] == "covered"
    assert derived_facts["coverage_surface"] == "./repo-python kernel.py --facts --band cluster_flag"
    assert derived_facts["fallback_surface"] == "./repo-python kernel.py --facts --band cluster_flag"

    prompt_shelf = rows["prompt_shelf_metadata"]
    assert prompt_shelf["row_count"] >= HIGH_CARDINALITY_THRESHOLD
    assert prompt_shelf["cluster_flag_available"] is True
    assert prompt_shelf["coverage_surface_available"] is True
    assert prompt_shelf["coverage_status"] == "covered"
    assert prompt_shelf["coverage_surface"].endswith("--option-surface prompt_shelf_metadata --band cluster_flag")


def test_coverage_watch_debt_excludes_advisory_and_lifecycle_rows() -> None:
    assert _debt_is_coverage_watch({"debt_class": "projection_debt", "active_debt": False}) is False
    assert _debt_is_coverage_watch({"debt_class": "projection_debt", "advisory_only": True}) is False
    assert _debt_is_coverage_watch({"debt_class": "layer_sprawl_debt"}) is False
    assert _debt_is_coverage_watch({"debt_class": "projection_debt"}) is True


def test_coverage_enforcement_matrix_flags_high_cardinality_without_cluster_surface() -> None:
    payload = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="coverage first matrix",
        context_budget=40000,
    )

    rows = {row["kind_id"]: row for row in payload["rows"]}
    standard_skill_map = rows.get("standard_skill_map")
    if standard_skill_map and standard_skill_map["row_count"] >= HIGH_CARDINALITY_THRESHOLD:
        if not standard_skill_map["cluster_flag_available"]:
            assert standard_skill_map["coverage_surface_available"] is False
            assert standard_skill_map["control_entry_allowed"] is False
            assert standard_skill_map["coverage_status"] == "blocked_missing_cluster_flag"


def test_coverage_enforcement_matrix_budget_trim_keeps_rows_routeable() -> None:
    payload = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="low-risk speed latency context-efficiency improvements across live system",
        context_budget=12000,
    )

    assert payload["budget"]["trimmed_for_budget"] is True
    assert payload["budget"]["estimated_tokens"] <= 12000
    assert len(json.dumps(payload, indent=2).encode("utf-8")) <= 12000 * 4
    assert payload["summary"]["kind_count"] == len(payload["rows"])
    extra_type_plane_count = payload["type_plane_resolution"]["extra_resolved_surface_count"]
    assert payload["summary"]["standard_type_plane_resolved_surface_count"] == extra_type_plane_count
    assert extra_type_plane_count >= 3
    assert "row_compaction_contract" in payload["budget"]
    assert payload["summary"]["coverage_status_counts"].get("watch_behavior_or_debt", 0) >= 0
    assert "process_audit_fast_path" in payload
    if payload["process_audit_fast_path"]["status"] == "active_behavior_debt":
        fast_path = payload["process_audit_fast_path"]
        first_command = payload["next_commands"][0]["command"]
        assert fast_path["owner_card_command"] or fast_path["process_bottleneck_quote_command"]
        assert first_command in {
            fast_path["owner_card_command"],
            fast_path["process_bottleneck_quote_command"],
        }

    rows = {row["kind_id"]: row for row in payload["rows"]}
    paper_modules = rows["paper_modules"]
    assert paper_modules["coverage_status"] == "covered"
    assert paper_modules["process_audit_violations"]["blocking_count"] == 0
    assert paper_modules["process_audit_violations"]["accepted_projected_count"] >= 1

    covered = rows["transform_job_receipts"]
    assert covered["coverage_status"] == "covered"
    assert covered["coverage_surface"].endswith("--option-surface transform_job_receipts --band cluster_flag")
    assert "process_audit_violations" not in covered
    assert "debt_pressure" not in covered

    skills = rows["skills"]
    assert skills["coverage_status"] == "covered"
    assert "process_audit_violations" not in skills
    assert skills["route_lifecycle_status"]["exact_lookup"]["route_id"] == "skill_find"
    assert "debt_pressure" not in skills


def test_coverage_enforcement_matrix_omits_rows_for_active_fast_path_query() -> None:
    compact = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="anti_pattern_deep_without_ladder",
        context_budget=12000,
    )
    full = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="anti_pattern_deep_without_ladder",
        context_budget=40000,
    )

    if compact["process_audit_fast_path"]["status"] != "active_behavior_debt":
        assert compact["process_audit_fast_path"]["status"] == "matched_behavior_debt_not_active"
        assert compact["process_audit_fast_path"]["debt"]["debt_id"] == (
            "behavior:process_audit:anti_pattern_deep_without_ladder"
        )
        assert compact["rows"]
        return

    assert compact["budget"]["fast_path_row_omission"] is True
    assert compact["rows"] == []
    assert compact["summary"]["rows_emitted_count"] == 0
    assert compact["summary"]["matrix_rows_omitted_count"] == compact["summary"]["kind_count"]
    assert compact["matrix_rows_omission_receipt"]["omitted_row_count"] == compact["summary"]["kind_count"]
    assert "--context-budget 40000" in compact["matrix_rows_omission_receipt"]["full_matrix_command"]
    assert compact["next_commands"][0]["command"] == compact["process_audit_fast_path"]["owner_card_command"]
    assert any(
        item["command"] == compact["matrix_rows_omission_receipt"]["full_matrix_command"]
        for item in compact["next_commands"]
    )
    assert full["rows"]
    assert len(json.dumps(compact, indent=2).encode("utf-8")) < len(json.dumps(full, indent=2).encode("utf-8"))


def test_coverage_enforcement_matrix_compacts_slow_action_fast_path_query() -> None:
    compact = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="slow_action_shape",
        context_budget=12000,
    )
    full = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="slow_action_shape",
        context_budget=40000,
    )

    if compact["process_audit_fast_path"]["status"] != "active_behavior_debt":
        assert compact["rows"]
        return

    assert compact["process_audit_fast_path"]["debt"]["debt_id"].startswith(
        "behavior:process_audit:slow_action_shape:"
    )
    fast_path_debt = compact["process_audit_fast_path"]["debt"]
    if fast_path_debt.get("repair_hints"):
        assert fast_path_debt["repair_hints"][0]["hint_id"]
    quote_command = compact["process_audit_fast_path"]["process_bottleneck_quote_command"]
    assert quote_command == (
        "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage "
        f"--action-kind {fast_path_debt['debt_id'].rsplit(':', 1)[-1]}"
    )
    assert compact["next_commands"][0]["command"] == quote_command
    assert compact["budget"]["fast_path_row_omission"] is True
    assert compact["rows"] == []
    assert compact["summary"]["matrix_rows_omitted_count"] == compact["summary"]["kind_count"]
    assert "--context-budget 40000" in compact["matrix_rows_omission_receipt"]["full_matrix_command"]
    assert full["rows"]
    assert len(json.dumps(compact, indent=2).encode("utf-8")) < len(json.dumps(full, indent=2).encode("utf-8"))


def test_coverage_enforcement_matrix_routes_speed_query_to_throughput_fast_path() -> None:
    payload = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="speed efficiency context economy route cost command profile latency diagnostics",
        context_budget=12000,
    )

    if payload["process_audit_fast_path"]["status"] != "active_behavior_debt":
        assert payload["rows"]
        return

    fast_path = payload["process_audit_fast_path"]
    assert fast_path["debt"]["debt_id"].startswith("behavior:process_audit:slow_action_shape:")
    assert fast_path["selection_reason"] == "throughput_query_preferred_action_kind_debt"
    assert fast_path["active_behavior_debt_count"] >= 1
    assert fast_path["alternate_active_debt_count"] == len(fast_path["alternate_active_debt_ids"])
    assert "behavior:process_audit:anti_pattern_deep_without_ladder" not in fast_path[
        "alternate_active_debt_ids"
    ]
    assert fast_path["process_bottleneck_quote_command"] == (
        "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage "
        f"--action-kind {fast_path['debt']['debt_id'].rsplit(':', 1)[-1]}"
    )
    assert any(
        item["command"] == fast_path["process_bottleneck_quote_command"]
        for item in payload["next_commands"]
    )


def test_coverage_enforcement_matrix_reports_privacy_safe_phase_timings() -> None:
    payload = build_coverage_enforcement_matrix(
        REPO_ROOT,
        query="command path economy diagnostics",
        context_budget=12000,
    )

    strategy = payload["strategy"]
    timings = strategy["stage_timings_ms"]
    assert {
        "kind_atlas",
        "navigation_metabolism",
        "matrix_rows",
        "standard_type_plane",
        "packet_assembly",
        "budget_trim",
    } <= set(timings)
    assert all(isinstance(value, int) and value >= 0 for value in timings.values())

    latency = strategy["latency_profile"]
    assert latency["schema_version"] == "coverage_matrix_latency_profile_v0"
    assert latency["phase_count"] == len(timings)
    assert latency["slow_phase_count"] == len(latency["slow_phases"])
    assert latency["total_ms"] >= max(timings.values())
    assert latency["privacy"] == "phase_names_wall_time_only_no_command_output_bodies"
    assert "stdout" not in json.dumps(latency).lower()
    assert "stderr" not in json.dumps(latency).lower()


def test_coverage_enforcement_matrix_cli_emits_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--coverage-enforcement-matrix",
            "coverage first matrix",
            "--context-budget",
            "20000",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "coverage_enforcement_matrix"
    assert payload["summary"]["kind_count"] >= 25
    assert payload["summary"]["control_entry_allowed_count"] == 0
    assert any(row["kind_id"] == "skills" for row in payload["rows"])
    assert len(result.stdout.encode("utf-8")) <= 20000 * 4
