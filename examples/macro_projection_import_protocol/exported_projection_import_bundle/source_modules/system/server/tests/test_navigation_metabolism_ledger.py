"""Regression coverage for the unified navigation metabolism ledger."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from system.lib.navigation_metabolism_ledger import (
    TACO_ANNEX,
    _actor_delivery_debt_rows,
    _annotate_process_audit_source_freshness,
    _annex_intake_rows,
    _annex_movement_pressure_debt_rows,
    _budget_trim,
    _cached_navigation_mechanism_metabolism,
    _cached_process_audit_payload,
    _cached_routing_projection_status,
    _count_by_class,
    _entrypoint_debt_rows,
    _latency_profile,
    _latency_profile_debt_rows,
    _layer_sprawl_rows,
    _quick_projection_debt_rows,
    _process_audit_behavior_rows,
    _priority_trim_debt_rows,
    _quality_signal,
    _retire_observed_navigation_mechanism_debt_rows,
    _routing_source_coupling_debt_rows,
    _top_repairs,
    build_navigation_metabolism_ledger,
    compact_quick_navigation_metabolism_packet_for_cli,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
KERNEL_CLI_TIMEOUT_SECONDS = 30


def _run_kernel_cli(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = KERNEL_CLI_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [sys.executable, "kernel.py", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
        raise AssertionError(
            f"kernel.py {' '.join(args)} timed out after {timeout}s\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        ) from exc


def _fake_metabolism_payload(profile: str, *, oversize: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "navigation_metabolism_ledger",
        "schema_version": "navigation_metabolism_ledger_v0",
        "metabolism_profile": profile,
        "strategy": {"profile": profile},
        "summary": {"projection_debt": 0, "behavior_debt": 0},
        "debt_rows": [],
    }
    if oversize:
        payload["oversized_debug_blob"] = "x" * (25 * 1024)
    return payload


def test_library_reference_projection_rows_are_advisory_not_active_debt() -> None:
    rows = _quick_projection_debt_rows({"contract_status": "valid"})
    row = next(row for row in rows if row["debt_id"] == "projection:paper_modules.row_flag_all.library")

    assert row["library_reference_only"] is True
    assert row["advisory_only"] is True
    assert row["active_debt"] is False
    assert _count_by_class(rows)["projection_debt"] == 0
    assert _top_repairs(rows) == []


def test_observed_navigation_mechanisms_retire_matching_process_audit_debt() -> None:
    rows = _process_audit_behavior_rows(
        {
            "status": "available",
            "session_count": 4,
            "patterns": [
                {
                    "pattern_id": "anti_pattern_grep_before_kernel",
                    "instances": 3,
                    "session_id_hits": ["s1", "s2"],
                },
                {
                    "pattern_id": "anti_pattern_loop_detected",
                    "instances": 2,
                    "session_id_hits": ["s3"],
                },
            ],
        }
    )

    retired_rows, receipt = _retire_observed_navigation_mechanism_debt_rows(
        rows,
        {
            "observed_anti_pattern_ids": ["anti_pattern_grep_before_kernel"],
            "observed_claim_refs": [
                {
                    "claim_id": "mpc_demo",
                    "anti_pattern_id": "anti_pattern_grep_before_kernel",
                    "state": "observed",
                    "acceptance_event_ref": "navigation_mechanism_acceptance_event:nmae_demo",
                    "future_observation": {"status": "observed"},
                }
            ],
        },
    )

    grep_row = next(row for row in retired_rows if row["anti_pattern_id"] == "anti_pattern_grep_before_kernel")
    loop_row = next(row for row in retired_rows if row["anti_pattern_id"] == "anti_pattern_loop_detected")
    assert grep_row["active_debt"] is False
    assert grep_row["advisory_only"] is True
    assert grep_row["retired_by_navigation_mechanism_observation"] is True
    assert grep_row["navigation_mechanism_claim_id"] == "mpc_demo"
    assert "behavior:process_audit:anti_pattern_grep_before_kernel" in receipt["retired_debt_ids"]
    assert loop_row.get("active_debt") is not False
    assert _count_by_class(retired_rows)["behavior_debt"] == 1
    assert {
        row["debt_id"]
        for row in _top_repairs(retired_rows)
    } == {"behavior:process_audit:anti_pattern_loop_detected"}


def test_deep_without_ladder_rows_surface_owner_boundary_at_top_repair() -> None:
    rows = _process_audit_behavior_rows(
        {
            "status": "available",
            "session_count": 4,
            "patterns": [
                {
                    "pattern_id": "anti_pattern_deep_without_ladder",
                    "instances": 3,
                    "session_id_hits": ["s1", "s2"],
                }
            ],
        }
    )

    row = rows[0]
    assert row["debt_id"] == "behavior:process_audit:anti_pattern_deep_without_ladder"
    assert row["owner_surface"] == "navigation_ladder_owner_route"
    assert row["owner_status_command"] == (
        './repo-python kernel.py --coverage-enforcement-matrix "anti_pattern_deep_without_ladder" '
        "--context-budget 12000"
    )
    assert row["authoritative_decision_command"] == (
        './repo-python kernel.py --navigation-metabolism "anti_pattern_deep_without_ladder owner route" '
        "--metabolism-profile quick --context-budget 12000"
    )
    assert row["source_projection_boundary"] == {
        "process_audit_policy": "behavior_evidence_not_source_authority",
        "patch_selection_policy": "select_stable_owner_card_before_source_patch",
        "owner_status_route": (
            './repo-python kernel.py --coverage-enforcement-matrix "anti_pattern_deep_without_ladder" '
            "--context-budget 12000"
        ),
        "authoritative_decision_route": (
            './repo-python kernel.py --navigation-metabolism "anti_pattern_deep_without_ladder owner route" '
            "--metabolism-profile quick --context-budget 12000"
        ),
        "owner_card_route": (
            "./repo-python kernel.py --option-surface skills --band card "
            "--ids navigation_seed,agent_session_diagnostics"
        ),
    }

    repair = _top_repairs(rows)[0]
    assert repair["owner_surface"] == "navigation_ladder_owner_route"
    assert repair["owner_status_command"] == row["owner_status_command"]
    assert repair["authoritative_decision_command"] == row["authoritative_decision_command"]
    assert repair["source_projection_boundary"]["patch_selection_policy"] == (
        "select_stable_owner_card_before_source_patch"
    )
    assert repair["source_projection_boundary"]["owner_card_route"].endswith(
        "--ids navigation_seed,agent_session_diagnostics"
    )


def test_process_audit_stale_cache_boundary_demotes_active_repair() -> None:
    rows = _process_audit_behavior_rows(
        {
            "status": "available",
            "session_count": 4,
            "patterns": [
                {
                    "pattern_id": "anti_pattern_deep_without_ladder",
                    "instances": 3,
                    "session_id_hits": ["s1", "s2"],
                }
            ],
        }
    )
    annotated = _annotate_process_audit_source_freshness(
        rows,
        {"status": "stale_ok_hit", "age_s": 1200.0, "ttl_s": 600.0},
    )

    row = annotated[0]
    assert row["source_freshness"]["status"] == "advisory_only_stale_read_model"
    assert row["source_freshness"]["cache_status"] == "stale_ok_hit"
    assert row["source_freshness"]["authoritative_decision_command"] == (
        "./repo-python kernel.py --process-bottlenecks --force"
    )
    assert row["source_projection_boundary"]["process_audit_cache_policy"] == (
        "refresh_before_selecting_process_audit_source_patch"
    )
    assert row["active_debt"] is False
    assert row["advisory_only"] is True
    assert row["active_debt_demoted_by"] == "stale_process_audit_read_model"
    assert _count_by_class(annotated)["behavior_debt"] == 0
    assert _top_repairs(annotated) == []

    compact = compact_quick_navigation_metabolism_packet_for_cli(
        {
            "metabolism_profile": "quick",
            "summary": {"behavior_debt": 0, "total_debt_rows": 0},
            "budget": {"context_budget_tokens": 12000},
            "debt_rows": annotated,
            "top_repairs": [],
            "route_lifecycle": [],
            "command_node_cache": {},
            "observation_sources": {},
        },
        context_budget=12000,
    )
    compact_row = compact["debt_rows"][0]
    assert compact_row["active_debt"] is False
    assert compact_row["source_freshness"]["patch_selection_policy"] == (
        "refresh_before_selecting_process_audit_source_patch"
    )
    assert compact_row["source_freshness"]["authoritative_decision_command"] == (
        "./repo-python kernel.py --process-bottlenecks --force"
    )


def test_cli_compaction_caps_clean_advisory_rows() -> None:
    rows = [
        {
            "debt_id": f"advisory:{index}",
            "debt_class": "behavior_debt",
            "priority": 100 - index,
            "title": f"Advisory row {index}",
            "evidence": "x" * 1000,
            "repair_class": "advisory_only",
            "active_debt": False,
            "advisory_only": True,
        }
        for index in range(6)
    ]

    compact = compact_quick_navigation_metabolism_packet_for_cli(
        {
            "metabolism_profile": "quick",
            "summary": {
                "behavior_debt": 0,
                "total_debt_rows": 0,
                "quality_signal_bottleneck": None,
            },
            "budget": {"context_budget_tokens": 1000},
            "debt_rows": rows,
            "top_repairs": [],
            "route_lifecycle": [],
            "command_node_cache": {},
            "observation_sources": {},
        },
        context_budget=1000,
    )

    assert len(compact["debt_rows"]) == 3
    assert {row["debt_id"] for row in compact["debt_rows"]} == {
        "advisory:0",
        "advisory:1",
        "advisory:2",
    }
    assert compact["summary"]["total_debt_rows_after_cli_compaction"] == 0
    assert compact["summary"]["advisory_debt_rows_after_cli_compaction"] == 3


def test_cli_compaction_omits_clean_advisory_rows_for_speed_context_query() -> None:
    rows = [
        {
            "debt_id": f"advisory:{index}",
            "debt_class": "behavior_debt",
            "priority": 100 - index,
            "title": f"Advisory row {index}",
            "evidence": "x" * 1000,
            "repair_class": "advisory_only",
            "active_debt": False,
            "advisory_only": True,
        }
        for index in range(6)
    ]
    full_profile_route = (
        './repo-python kernel.py --navigation-metabolism "speed context route cost" '
        "--metabolism-profile full --context-budget 12000"
    )

    compact = compact_quick_navigation_metabolism_packet_for_cli(
        {
            "metabolism_profile": "quick",
            "query": "speed context route cost",
            "summary": {
                "behavior_debt": 0,
                "advisory_debt_rows": 6,
                "total_debt_rows": 0,
                "total_rows_including_advisory": 6,
                "quality_signal_bottleneck": None,
            },
            "strategy": {"full_profile_drilldown": full_profile_route},
            "budget": {"context_budget_tokens": 1000},
            "debt_rows": rows,
            "top_repairs": [],
            "route_lifecycle": [],
            "command_node_cache": {},
            "observation_sources": {},
        },
        context_budget=1000,
    )

    assert compact["debt_rows"] == []
    receipt = compact["clean_advisory_rows_omission_receipt"]
    assert receipt["status"] == "omitted_for_clean_speed_context_first_contact"
    assert receipt["omitted_row_count"] == 6
    assert receipt["full_evidence_routes"] == [full_profile_route]
    assert compact["summary"]["total_debt_rows_after_cli_compaction"] == 0
    assert compact["summary"]["advisory_debt_rows_after_cli_compaction"] == 0
    assert compact["summary"]["clean_advisory_rows_omitted"] == 6
    assert full_profile_route in compact["budget"]["full_evidence_routes"]


def test_budget_trim_preserves_behavior_owner_boundary_on_visible_debt_rows() -> None:
    rows = _process_audit_behavior_rows(
        {
            "status": "available",
            "session_count": 4,
            "patterns": [
                {
                    "pattern_id": "anti_pattern_deep_without_ladder",
                    "instances": 3,
                    "session_id_hits": ["s1", "s2"],
                }
            ],
        }
    )
    packet = {
        "budget": {
            "context_budget_tokens": 1000,
            "hard_ceiling": True,
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "summary": {"behavior_debt": len(rows), "total_debt_rows": len(rows)},
        "debt_rows": rows,
        "top_repairs": _top_repairs(rows),
        "observation_sources": {},
        "oversized_debug_blob": "x" * 50000,
    }

    trimmed = _budget_trim(packet, context_budget=1000)
    row = next(
        row
        for row in trimmed["debt_rows"]
        if row["debt_id"] == "behavior:process_audit:anti_pattern_deep_without_ladder"
    )

    assert row["owner_surface"] == "navigation_ladder_owner_route"
    assert row["owner_status_command"] == (
        './repo-python kernel.py --coverage-enforcement-matrix "anti_pattern_deep_without_ladder" '
        "--context-budget 12000"
    )
    assert row["authoritative_decision_command"] == (
        './repo-python kernel.py --navigation-metabolism "anti_pattern_deep_without_ladder owner route" '
        "--metabolism-profile quick --context-budget 12000"
    )
    assert row["source_projection_boundary"]["owner_card_route"].endswith(
        "--ids navigation_seed,agent_session_diagnostics"
    )


def test_slow_action_shape_rows_surface_repair_hints_at_top_repair() -> None:
    rows = _process_audit_behavior_rows(
        {
            "status": "available",
            "session_count": 5,
            "findings": [
                {
                    "rule": "slow_action_shape",
                    "action_kind": "kernel_command",
                }
            ],
            "bottlenecks": {
                "kernel_command": {
                    "p50_ms": 1259,
                    "p95_ms": 31856,
                    "max_ms": 282302,
                        "threshold_ms": 15000,
                        "repair_hints": [
                            {
                                "hint_id": "replace_context_pack_limiter_with_selected_lens",
                                "reason": "Slow context-pack examples hide large packets behind shell output limiters.",
                                "preferred_next": "Use the routine context-pack row handles, then drill into a selected row/card instead of truncating the full packet.",
                            }
                        ],
                    "example_spans": [
                        {
                            "normalized_command": "./repo-python kernel.py --kind-atlas 2>&1 | head -80",
                            "command_shape_tags": ["output_limited", "tmp_artifact_file"],
                        },
                        {
                            "normalized_command": "./repo-python kernel.py --context-pack demo",
                            "command_shape_tags": ["context_pack", "output_limited"],
                        },
                    ],
                }
            },
        }
    )

    row = rows[0]
    assert row["debt_id"] == "behavior:process_audit:slow_action_shape:kernel_command"
    assert row["repair_hints"][0]["hint_id"] == "replace_context_pack_limiter_with_selected_lens"
    assert row["preferred_next"].startswith("Use the routine context-pack row handles")
    assert row["example_command_shape_tags"] == ["output_limited", "tmp_artifact_file", "context_pack"]
    assert row["owner_surface"] == "process_bottlenecks"
    assert row["owner_status_command"] == "./repo-python kernel.py --process-bottlenecks"
    assert row["authoritative_decision_command"] == "./repo-python kernel.py --process-bottlenecks --force"
    assert row["source_projection_boundary"] == {
        "cached_summary_policy": "advisory_only_for_candidate_ranking",
        "patch_selection_policy": "force_live_before_source_patch",
        "default_status_route": "./repo-python kernel.py --process-bottlenecks",
        "authoritative_decision_route": "./repo-python kernel.py --process-bottlenecks --force",
    }

    repair = _top_repairs(rows)[0]
    assert repair["repair_hints"] == row["repair_hints"]
    assert repair["preferred_next"] == row["preferred_next"]
    assert repair["example_command_shape_tags"] == row["example_command_shape_tags"]
    assert repair["owner_surface"] == "process_bottlenecks"
    assert repair["authoritative_decision_command"] == "./repo-python kernel.py --process-bottlenecks --force"
    assert repair["process_bottleneck_drilldown"] == "./repo-python kernel.py --process-bottlenecks"
    assert repair["source_projection_boundary"]["patch_selection_policy"] == "force_live_before_source_patch"
    assert "normalized_command" not in json.dumps(repair)


def test_quick_routing_projection_status_defers_missing_cache(tmp_path: Path) -> None:
    payload, status = _cached_routing_projection_status(tmp_path, allow_build=False)

    assert status["status"] == "deferred_missing_cache"
    assert payload["status"] == "deferred_by_quick_profile"
    assert payload["source_coupling"]["status"] == "deferred_by_quick_profile"
    assert payload["safe_alternative"] == "./repo-python kernel.py --routing-check"
    assert _routing_source_coupling_debt_rows(payload) == []


def test_layer_sprawl_rows_ignore_resolved_lifecycle_shims() -> None:
    rows = _layer_sprawl_rows(
        [
            {
                "route_id": "paper_modules.row_flag_all",
                "status": "compatibility_shim",
                "superseded_by": "paper_modules.cluster_flag",
                "compatibility_behavior": "CLI redirects unless --ids is explicit",
                "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
            },
            {
                "route_id": "navigation_context_rosetta",
                "status": "active_reference",
                "superseded_by": "context_pack for first-contact task routing",
                "compatibility_behavior": "open when changing the math/grammar, not for ordinary task entry",
                "removal_condition": "only after its grammar is embedded in executable standards and tests",
            },
        ]
    )

    assert rows == []


def test_layer_sprawl_rows_flag_watched_routes_missing_lifecycle_fields() -> None:
    rows = _layer_sprawl_rows(
        [
            {
                "route_id": "legacy.row_flag_all",
                "status": "compatibility_shim",
                "superseded_by": "legacy.cluster_flag",
            }
        ]
    )

    assert len(rows) == 1
    assert rows[0]["debt_id"] == "layer_sprawl:legacy.row_flag_all"
    assert rows[0]["missing_lifecycle_fields"] == ["compatibility_behavior", "removal_condition"]
    assert "missing explicit lifecycle handling" in rows[0]["title"]


def test_skill_find_policy_gap_retires_when_debug_trace_contract_is_hardened() -> None:
    payload = build_navigation_metabolism_ledger(
        REPO_ROOT,
        query="coverage first skill discovery",
        context_budget=40000,
        include_session_summary=False,
        include_fitness=False,
        behavior_events=[],
        metabolism_profile="quick",
    )

    policy = payload["observation_sources"]["skill_find_debug_trace_policy"]
    assert policy["status"] == "hardened_debug_trace_only"
    assert policy["first_contact_allowed"] is False
    assert policy["debug_requires_flag"] == "--debug"
    assert policy["ranked_matches_default"] == "hidden"
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "behavior:skill_find_first_contact:policy_gap" not in debt_ids


def test_entrypoint_debt_rows_partition_by_load_posture_match_summary_counts() -> None:
    # Structural invariant: the metabolism ledger and entrypoint_health summary
    # must agree on which over-budget files are "primary entry over budget"
    # (counted in over_budget_count, repair=entrypoint_shrink_or_split) vs
    # "generated_or_doctrine_skill over budget" (counted in
    # generated_or_doctrine_over_budget_count, repair=generated_or_doctrine_skill_compaction).
    # A previous version emitted entrypoint_shrink_or_split for ALL over_budget
    # files irrespective of load_posture, creating a split-brain metric where
    # a row could exist while over_budget_count was 0. This test exercises both
    # subkinds via fixture data so the bug cannot recur even when current entry
    # files happen to all be within budget.
    fixture = {
        "instruction_files": [
            {
                "path": "AGENTS.md",
                "bytes": 50000,
                "budget": 32768,
                "budget_status": "over_budget",
                "load_posture": "shared_hub",
            },
            {
                "path": "CLAUDE.md",
                "bytes": 20000,
                "budget": 32768,
                "budget_status": "within_budget",
                "load_posture": "actor_adapter",
            },
            {
                "path": ".agents/skills/SOMETHING/SKILL.md",
                "bytes": 9000,
                "budget": 4000,
                "budget_status": "over_budget",
                "load_posture": "generated_or_doctrine_skill",
            },
        ],
        "summary": {
            "over_budget_count": 1,
            "generated_or_doctrine_over_budget_count": 1,
        },
        "forbidden_first_contact_hits": [],
    }
    rows = _entrypoint_debt_rows(fixture)

    primary_rows = [row for row in rows if row.get("repair_class") == "entrypoint_shrink_or_split"]
    generated_rows = [row for row in rows if row.get("repair_class") == "generated_or_doctrine_skill_compaction"]

    # Structural invariant 1: primary count == summary.over_budget_count
    assert len(primary_rows) == fixture["summary"]["over_budget_count"]
    # Structural invariant 2: generated count == summary.generated_or_doctrine_over_budget_count
    assert len(generated_rows) == fixture["summary"]["generated_or_doctrine_over_budget_count"]
    # The primary row must be the AGENTS.md one
    assert primary_rows[0]["debt_id"] == "entrypoint:AGENTS.md:over_budget"
    assert primary_rows[0]["over_budget_subkind"] == "primary_entry_file"
    # The generated/doctrine row must NOT use the entrypoint_shrink_or_split repair_class
    assert generated_rows[0]["repair_class"] != "entrypoint_shrink_or_split"
    assert generated_rows[0]["over_budget_subkind"] == "generated_or_doctrine_skill"
    # Both rows must still belong to the entrypoint_debt class
    assert all(row["debt_class"] == "entrypoint_debt" for row in primary_rows + generated_rows)


def test_entrypoint_debt_rows_skip_when_all_within_budget() -> None:
    fixture = {
        "instruction_files": [
            {
                "path": "AGENTS.md",
                "bytes": 1000,
                "budget": 32768,
                "budget_status": "within_budget",
                "load_posture": "shared_hub",
            },
        ],
        "summary": {"over_budget_count": 0, "generated_or_doctrine_over_budget_count": 0},
        "forbidden_first_contact_hits": [],
    }
    rows = _entrypoint_debt_rows(fixture)
    assert rows == []


def test_actor_delivery_debt_rows_include_decision_coverage_gaps() -> None:
    rows = _actor_delivery_debt_rows(
        {
            "kind": "agent_bootstrap_actor_receipt",
            "required_delivery_route_count": 1,
            "total_situation_route_count": 3,
            "actor_delivery_decision_count": 1,
            "unknown_delivery_decision_count": 1,
            "missing_workitem_ref_count": 1,
            "warnings": ["unknown_route: missing actor_delivery.decision"],
            "blockers": [],
            "unknown_delivery_decisions": [
                {
                    "situation_id": "unknown_route",
                    "route_id": "sit_unknown_route",
                    "reason": "missing_actor_delivery_decision",
                }
            ],
            "missing_workitem_refs": [
                {
                    "situation_id": "deferred_route",
                    "route_id": "sit_deferred_route",
                    "decision": "defer_with_workitem",
                    "reason": "missing_or_unknown_workitem_ref",
                }
            ],
        }
    )

    repair_classes = {row["repair_class"] for row in rows}
    assert "actor_delivery_decision_missing" in repair_classes
    assert "actor_delivery_defer_workitem_missing" in repair_classes
    assert {row["debt_class"] for row in rows} == {"actor_delivery_debt"}
    assert all(row["source_surface"] == "check_agent_bootstrap_projection.py --actor-receipt" for row in rows)


def test_navigation_metabolism_latency_profile_names_slow_actor_receipt_phase() -> None:
    phase_rows = [{"phase": "actor_delivery_receipt", "ms": 4200.0}]

    profile = _latency_profile(
        phase_rows,
        total_ms=4300.0,
        phase_warn_ms=2500.0,
        total_warn_ms=10000.0,
    )
    rows = _latency_profile_debt_rows(
        phase_rows,
        surface="navigation_metabolism.quick",
        total_ms=4300.0,
        phase_warn_ms=2500.0,
        total_warn_ms=10000.0,
    )

    assert profile["status"] == "latency_debt"
    assert profile["measurement_scope"] == "in_process_internal_phases_only"
    assert profile["external_wall_clock_status"] == "unmeasured"
    assert profile["speed_contract"]["primary_question"] == (
        "How long until the agent or operator gets the next useful signal?"
    )
    assert profile["slow_phases"][0]["phase"] == "actor_delivery_receipt"
    assert {row["route_id"] for row in rows} == {"external_wall_clock", "actor_delivery_receipt"}
    actor_row = next(row for row in rows if row["route_id"] == "actor_delivery_receipt")
    assert actor_row["debt_class"] == "latency_debt"
    assert "tools/meta/factory/check_agent_bootstrap_projection.py" in actor_row["target_files"]


def test_navigation_metabolism_latency_profile_does_not_close_speed_without_wall_clock() -> None:
    phase_rows = [{"phase": "entrypoint_health", "ms": 12.0}]

    profile = _latency_profile(
        phase_rows,
        total_ms=80.0,
        phase_warn_ms=2500.0,
        total_warn_ms=10000.0,
    )
    rows = _latency_profile_debt_rows(
        phase_rows,
        surface="navigation_metabolism.quick",
        total_ms=80.0,
        phase_warn_ms=2500.0,
        total_warn_ms=10000.0,
    )

    assert profile["status"] == "within_budget"
    assert profile["status_qualifier"] == "within_budget_internal_only_external_elapsed_unmeasured"
    assert "toolhost_wall_clock_ms" in profile["speed_contract"]["axes"]
    assert "retry_rework_elapsed_ms" in profile["speed_contract"]["axes"]
    scope_gap = next(row for row in rows if row["route_id"] == "external_wall_clock")
    assert scope_gap["debt_class"] == "latency_debt"
    assert scope_gap["repair_class"] == "perceived_latency_measurement_repair"
    assert "toolhost_wall_clock_ms" in scope_gap["missing_axes"]
    assert "inner_phase_ms" not in scope_gap["missing_axes"]


def test_clusterability_quick_projection_is_uncached_for_dynamic_artifacts(monkeypatch, tmp_path) -> None:
    import system.lib.navigation_metabolism_ledger as ledger_module

    calls = 0

    def fake_clusterability_audit(*_args, **kwargs):
        nonlocal calls
        calls += 1
        assert kwargs["measure_all_rows"] is False
        return {
            "kind": "navigation_clusterability_audit",
            "summary": {"debt_count": 0},
            "debt_rows": [],
        }

    monkeypatch.setattr(
        ledger_module,
        "build_navigation_clusterability_audit",
        fake_clusterability_audit,
    )

    first_payload, first_status = ledger_module._cached_clusterability_quick(tmp_path, budget=12000)
    second_payload, second_status = ledger_module._cached_clusterability_quick(tmp_path, budget=12000)

    assert calls == 2
    assert first_payload["summary"]["debt_count"] == 0
    assert second_payload["summary"]["debt_count"] == 0
    assert first_status["status"] == "uncached_built"
    assert second_status["status"] == "uncached_built"
    assert first_status["freshness_policy"] == "uncached_dynamic_artifact_projection"
    assert first_status["dynamic_inputs_manifested"] is False
    assert not (tmp_path / "state" / "command_cache" / "navigation_metabolism.clusterability.quick").exists()


def test_clusterability_quick_default_defers_measurement_for_latency(tmp_path) -> None:
    import system.lib.navigation_metabolism_ledger as ledger_module

    payload, status = ledger_module._cached_clusterability_quick(
        tmp_path,
        budget=12000,
        allow_build=False,
    )

    assert payload["status"] == "deferred_by_quick_profile"
    assert payload["summary"]["debt_count"] == 0
    assert status["status"] == "deferred_by_quick_profile"
    assert payload["drilldown_command"] == "./repo-python kernel.py --clusterability-audit --context-budget 12000"


def test_entrypoint_health_quick_reuses_command_node_cache(monkeypatch, tmp_path) -> None:
    import system.lib.navigation_metabolism_ledger as ledger_module

    calls = 0

    def fake_entrypoint_health(_root, *, include_generated_targets=True):
        nonlocal calls
        calls += 1
        assert include_generated_targets is False
        return {
            "kind": "entrypoint_health",
            "schema_version": "entrypoint_health_v0",
            "summary": {"contract_status": "valid", "file_count": 4},
            "instruction_files": [],
            "forbidden_first_contact_hits": [],
        }

    monkeypatch.delenv("AIW_COMMAND_CACHE", raising=False)
    monkeypatch.delenv("AIW_COMMAND_CACHE_REFRESH", raising=False)
    monkeypatch.setattr(ledger_module, "build_entrypoint_health", fake_entrypoint_health)

    first_payload, first_status = ledger_module._cached_entrypoint_health_quick(tmp_path)
    second_payload, second_status = ledger_module._cached_entrypoint_health_quick(tmp_path)

    assert calls == 1
    assert first_payload["summary"]["contract_status"] == "valid"
    assert second_payload["summary"]["contract_status"] == "valid"
    assert first_status["status"] == "miss_built"
    assert second_status["status"] == "hit"
    assert second_status["freshness_policy"] == "ttl_for_entrypoint_files_plus_budget_standard_manifest"


def test_quick_navigation_metabolism_refresh_env_rebuilds_process_nodes(monkeypatch, tmp_path) -> None:
    import system.lib.navigation_metabolism_ledger as ledger_module

    process_allow_build: list[bool] = []
    mechanism_allow_build: list[bool] = []

    def fake_process_audit(_root, *, allow_build=True):
        process_allow_build.append(allow_build)
        return (
            {
                "status": "available",
                "summary": {"session_count": 1, "finding_count": 0},
                "patterns": [],
                "findings": [],
                "bottlenecks": {},
                "session_count": 1,
            },
            {"status": "demo"},
        )

    def fake_navigation_mechanism(_root, _process_audit, *, allow_build=True):
        mechanism_allow_build.append(allow_build)
        return (
            {
                "status": "acceptance_read_model_available",
                "accepted_count": 0,
                "projected_count": 0,
                "observed_count": 0,
                "observed_anti_pattern_ids": [],
            },
            {"status": "demo"},
        )

    monkeypatch.setattr(ledger_module, "_cached_process_audit_payload", fake_process_audit)
    monkeypatch.setattr(ledger_module, "_cached_navigation_mechanism_metabolism", fake_navigation_mechanism)

    monkeypatch.delenv("AIW_COMMAND_CACHE_REFRESH", raising=False)
    ledger_module._build_quick_navigation_metabolism_ledger(
        tmp_path,
        query="process refresh demo",
        context_budget=12000,
    )

    monkeypatch.setenv("AIW_COMMAND_CACHE_REFRESH", "1")
    ledger_module._build_quick_navigation_metabolism_ledger(
        tmp_path,
        query="process refresh demo",
        context_budget=12000,
    )

    assert process_allow_build == [False, True]
    assert mechanism_allow_build == [False, True]


def test_actor_delivery_receipt_quick_default_defers_rebuild_for_latency(monkeypatch, tmp_path) -> None:
    import system.lib.navigation_metabolism_ledger as ledger_module

    def fail_build(_root):
        raise AssertionError("quick profile must not rebuild actor-delivery receipt")

    monkeypatch.setattr(ledger_module, "_actor_delivery_receipt", fail_build)

    payload, status = ledger_module._cached_actor_delivery_receipt(
        tmp_path,
        allow_build=False,
    )

    assert payload["status"] == "deferred_by_quick_profile"
    assert payload["blockers"] == []
    assert payload["safe_alternative"].endswith("check_agent_bootstrap_projection.py --actor-receipt")
    assert status["status"] == "deferred_missing_cache"
    assert not (
        tmp_path / "state" / "command_cache" / "navigation_metabolism.actor_delivery_receipt.quick"
    ).exists()


def test_quick_navigation_metabolism_defers_annex_projection_freshness(
    monkeypatch,
    tmp_path,
) -> None:
    import system.lib.navigation_metabolism_ledger as ledger_module

    def fake_annex_currentness(*_args, **kwargs):
        assert kwargs["include_projection_freshness"] is False
        return {
            "kind": "annex_currentness",
            "schema_version": "annex_currentness_v0",
            "summary": {
                "digest_status": "current",
                "currentness_debt": 0,
                "projection_freshness_status": "deferred_by_quick_profile",
                "projection_currentness_debt": 0,
                "projection_freshness_deferred": True,
            },
            "source": {},
            "currentness_contract": {},
            "top_attention_rows": [],
            "debt_rows": [],
        }

    monkeypatch.setattr(ledger_module, "build_annex_currentness", fake_annex_currentness)

    payload = ledger_module._build_quick_navigation_metabolism_ledger(
        tmp_path,
        query="autonomous seed latency",
        context_budget=12000,
    )

    annex_source = payload["observation_sources"]["annex_currentness"]
    assert annex_source["status"] == "available"
    assert annex_source["summary"]["projection_freshness_status"] == "deferred_by_quick_profile"
    assert payload["annex_currentness"]["summary"]["projection_freshness_deferred"] is True


def test_annex_movement_pressure_debt_rows_include_hidden_source_job_blockers() -> None:
    routed_rows = _annex_movement_pressure_debt_rows(
        {
            "summary": {
                "selected_row_job_count": 0,
                "source_row_job_count": 5,
                "source_job_blocker_count": 5,
                "source_classification_counts": {"repair_note_targets_before_mining": 5},
                "missing_report_count": 0,
                "unclassified_count": 0,
            },
            "quality_signal": {
                "status": "source_row_job_blockers_routed",
                "debt_policy": "source_row_job_blockers_are_routable_owner_review_rows",
            },
        }
    )

    assert routed_rows == []

    rows = _annex_movement_pressure_debt_rows(
        {
            "summary": {
                "selected_row_job_count": 0,
                "source_row_job_count": 5,
                "source_job_blocker_count": 5,
                "source_classification_counts": {"repair_note_targets_before_mining": 5},
                "missing_report_count": 0,
                "unclassified_count": 0,
            },
            "quality_signal": {
                "status": "source_row_jobs_blocked_before_mining",
                "debt_policy": "emit_debt_for_hidden_source_row_jobs_missing_report_or_unclassified_rows",
            },
        }
    )

    assert len(rows) == 1
    assert rows[0]["debt_class"] == "annex_currentness_debt"
    assert rows[0]["priority"] == 78
    assert "pre-mining source row-job blockers" in rows[0]["title"]
    assert "repair_note_targets_before_mining" in rows[0]["evidence"]
    assert any("false green" in test for test in rows[0]["tests"])


def test_routing_source_coupling_debt_row_title_matches_each_non_clean_status() -> None:
    """Regression: the debt-row title must reflect the actual source-coupling status,
    not a single hardcoded string. Pre-fix, the title was always
    'routing_hologram matches the worktree renderer but is coupled to dirty source inputs'
    even when the live status was `artifact_drift_from_clean_sources` (drifts + clean) or
    `dirty_source_inputs_and_artifact_drift` (drifts + dirty) or `source_state_unavailable`.
    The mismatch is a false-labeling projection-honesty bug.
    """
    cases = {
        "artifact_matches_dirty_source_inputs": "matches the worktree renderer but is coupled to dirty source inputs",
        "dirty_source_inputs_and_artifact_drift": "drifts from the worktree renderer and source inputs are dirty",
        "artifact_drift_from_clean_sources": "drifts from the worktree renderer with clean source inputs",
        "source_state_unavailable": "source-coupling state is unavailable",
    }
    for status, expected_substr in cases.items():
        rows = _routing_source_coupling_debt_rows(
            {
                "artifact_path": "codex/doctrine/routing_hologram.json",
                "source_coupling": {
                    "status": status,
                    "safe_to_commit_generated_outputs_without_sources": False,
                    "dirty_source_paths": [],
                    "reason": "synthetic test",
                },
            }
        )
        assert len(rows) == 1, f"status={status} produced {len(rows)} rows"
        title = rows[0]["title"]
        assert expected_substr in title, (
            f"status={status} title={title!r} missing {expected_substr!r}"
        )
        # Negative: should NOT carry a contradictory phrasing for non-matching statuses.
        if status != "artifact_matches_dirty_source_inputs":
            assert "matches the worktree renderer" not in title, (
                f"status={status} title still says 'matches' (false-label): {title!r}"
            )


def test_routing_source_coupling_debt_rows_surface_dirty_projection_inputs() -> None:
    rows = _routing_source_coupling_debt_rows(
        {
            "artifact_path": "codex/doctrine/routing_hologram.json",
            "check_command": "python3 kernel.py --routing-check",
            "refresh_command": "./repo-python tools/meta/factory/build_routing_projection.py",
            "source_coupling": {
                "status": "artifact_matches_dirty_source_inputs",
                "safe_to_commit_generated_outputs_without_sources": False,
                "dirty_source_paths": ["codex/doctrine/skills/skill_registry.json"],
                "reason": "generated targets match dirty source inputs",
            },
        }
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["debt_id"] == "projection:routing_hologram.source_coupling"
    assert row["debt_class"] == "projection_debt"
    assert row["priority"] == 94
    assert row["source_surface"] == "kernel.py --routing"
    assert row["source_coupling_status"] == "artifact_matches_dirty_source_inputs"
    assert row["dirty_source_paths"] == ["codex/doctrine/skills/skill_registry.json"]


def test_budget_trim_preserves_routing_source_coupling_receipt() -> None:
    debt_rows = _routing_source_coupling_debt_rows(
        {
            "artifact_path": "codex/doctrine/routing_hologram.json",
            "check_command": "python3 kernel.py --routing-check",
            "refresh_command": "./repo-python tools/meta/factory/build_routing_projection.py",
            "source_coupling": {
                "status": "artifact_matches_dirty_source_inputs",
                "safe_to_commit_generated_outputs_without_sources": False,
                "dirty_source_paths": ["codex/doctrine/skills/skill_registry.json"],
            },
        }
    )
    packet = {
        "budget": {
            "context_budget_tokens": 1000,
            "hard_ceiling": True,
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "debt_rows": debt_rows,
        "top_repairs": _top_repairs(debt_rows),
        "observation_sources": {
            "routing_projection_status": {
                "status": "available",
                "stale": False,
                "artifact_path": "codex/doctrine/routing_hologram.json",
                "source_coupling": {
                    "status": "artifact_matches_dirty_source_inputs",
                    "safe_to_commit_generated_outputs_without_sources": False,
                    "dirty_source_paths": ["codex/doctrine/skills/skill_registry.json"],
                },
            }
        },
        "oversized_debug_blob": "x" * 50000,
    }

    trimmed = _budget_trim(packet, context_budget=1000)

    source = trimmed["observation_sources"]["routing_projection_status"]
    assert source["source_coupling"]["status"] == "artifact_matches_dirty_source_inputs"
    assert source["source_coupling"]["dirty_source_paths"] == [
        "codex/doctrine/skills/skill_registry.json"
    ]
    assert trimmed["debt_rows"][0]["source_coupling_status"] == "artifact_matches_dirty_source_inputs"
    assert trimmed["debt_rows"][0]["dirty_source_paths"] == [
        "codex/doctrine/skills/skill_registry.json"
    ]
    assert trimmed["top_repairs"][0]["source_coupling_status"] == "artifact_matches_dirty_source_inputs"


def test_budget_trim_preserves_command_node_cache_freshness_policy() -> None:
    packet = {
        "budget": {
            "context_budget_tokens": 1000,
            "hard_ceiling": True,
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "summary": {"total_debt_rows": 0},
        "debt_rows": [],
        "top_repairs": [],
        "command_node_cache": {
            "process_audit": {
                "schema_version": "command_node_cache_v1",
                "node_id": "navigation_metabolism.process_audit.quick",
                "status": "stale_ok_hit",
                "reason": "expired",
                "cache_path": "state/command_cache/navigation_metabolism.process_audit.quick/example.json",
                "age_s": 1200.5,
                "ttl_s": 600.0,
                "freshness_policy": "ttl_for_dynamic_session_state_plus_static_source_manifest",
                "dynamic_inputs_manifested": False,
            },
            "navigation_mechanism_metabolism": {
                "schema_version": "command_node_cache_v1",
                "node_id": "navigation_metabolism.navigation_mechanism.quick",
                "status": "hit",
                "reason": "hit",
                "cache_path": "state/command_cache/navigation_metabolism.navigation_mechanism.quick/example.json",
                "age_s": 30.0,
                "ttl_s": 600.0,
                "freshness_policy": "ttl_plus_input_manifest",
                "dynamic_inputs_manifested": True,
            },
        },
        "oversized_debug_blob": "x" * 50000,
    }

    trimmed = _budget_trim(packet, context_budget=1000)

    process_cache = trimmed["command_node_cache"]["process_audit"]
    assert process_cache["status"] == "stale_ok_hit"
    assert process_cache["ttl_s"] == 600.0
    assert process_cache["freshness_policy"] == "ttl_for_dynamic_session_state_plus_static_source_manifest"
    assert process_cache["patch_selection_policy"] == (
        "refresh_before_selecting_process_audit_source_patch"
    )
    assert process_cache["dynamic_inputs_manifested"] is False
    assert "cache_path" not in process_cache

    mechanism_cache = trimmed["command_node_cache"]["navigation_mechanism_metabolism"]
    assert mechanism_cache["freshness_policy"] == "ttl_plus_input_manifest"
    assert mechanism_cache["dynamic_inputs_manifested"] is True


def test_quick_cli_compaction_drops_empty_command_node_cache_scalars() -> None:
    compact = compact_quick_navigation_metabolism_packet_for_cli(
        {
            "metabolism_profile": "quick",
            "summary": {"total_debt_rows": 0, "quality_signal_bottleneck": None},
            "budget": {"context_budget_tokens": 1000},
            "debt_rows": [
                {
                    "debt_id": "advisory:large",
                    "debt_class": "behavior_debt",
                    "priority": 10,
                    "title": "Large advisory row",
                    "evidence": "x" * 5000,
                    "active_debt": False,
                    "advisory_only": True,
                }
            ],
            "top_repairs": [],
            "route_lifecycle": [],
            "command_node_cache": {
                "actor_delivery_receipt": {
                    "status": "deferred_missing_cache",
                    "reason": "quick_profile_does_not_rebuild_expensive_node",
                    "age_s": None,
                    "ttl_s": None,
                    "freshness_policy": "ttl_for_actor_delivery_smoke_plus_static_source_manifest",
                    "dynamic_inputs_manifested": False,
                },
                "navigation_mechanism_metabolism": {
                    "status": "deferred_stale_cache",
                    "reason": "expired",
                    "age_s": 1200.5,
                    "ttl_s": 600.0,
                    "freshness_policy": "ttl_plus_input_manifest",
                    "dynamic_inputs_manifested": True,
                },
            },
            "observation_sources": {},
        },
        context_budget=1000,
    )

    deferred = compact["command_node_cache"]["actor_delivery_receipt"]
    assert "age_s" not in deferred
    assert "ttl_s" not in deferred
    assert "dynamic_inputs_manifested" not in deferred
    mechanism = compact["command_node_cache"]["navigation_mechanism_metabolism"]
    assert mechanism["dynamic_inputs_manifested"] is True
    assert mechanism["age_s"] == 1200.5
    assert mechanism["patch_selection_policy"] == "refresh_before_selecting_source_patch"


def test_quick_cli_compaction_keeps_control_packet_under_smaller_budget() -> None:
    payload = build_navigation_metabolism_ledger(
        REPO_ROOT,
        query="command latency and route bloat",
        context_budget=12000,
        metabolism_profile="quick",
    )

    compact = compact_quick_navigation_metabolism_packet_for_cli(payload, context_budget=12000)

    assert compact["kind"] == "navigation_metabolism_ledger"
    assert compact["metabolism_profile"] == "quick"
    assert compact["budget"]["cli_compacted_for_output"] is True
    assert compact["budget"]["estimated_tokens"] <= compact["budget"]["cli_compaction_target_tokens"]
    assert compact["budget"]["cli_compaction_target_bytes"] == 8000 * 4
    assert compact["budget"]["estimated_output_bytes"] <= compact["budget"]["cli_compaction_target_bytes"]
    assert compact["budget"]["over_budget_basis"] == "json_bytes_vs_advertised_token_target"
    assert compact["budget"]["over_budget"] is False
    assert compact["budget"]["hard_ceiling"] is True
    assert "over_budget_reason" not in compact["budget"]
    assert len(json.dumps(compact, indent=2).encode("utf-8")) <= compact["budget"]["cli_compaction_target_bytes"]
    assert compact["route_lifecycle"]
    assert len(compact["route_lifecycle"]) <= 8
    route_summary = compact["route_lifecycle_summary"]
    assert route_summary["total_rows"] >= len(compact["route_lifecycle"])
    assert route_summary["omitted_rows"] == route_summary["total_rows"] - route_summary["emitted_rows"]
    assert route_summary["compression_policy"] == "quick_cli_prioritized_slice_static_lifecycle_summary"
    assert route_summary["full_evidence_route"].startswith("./repo-python kernel.py --navigation-metabolism")
    assert "status_counts" in route_summary
    assert all("purpose" not in row for row in compact["route_lifecycle"])
    assert all("compatibility_behavior" not in row for row in compact["route_lifecycle"])
    phase_alignment = next(
        row for row in compact["route_lifecycle"] if row["route_id"] == "phase_task_alignment"
    )
    assert phase_alignment["write_guard_present"] is True
    assert "write_guard" not in phase_alignment
    assert phase_alignment["residual_lane_command_templates_omitted"] >= 1
    assert phase_alignment["owner_surface_templates_omitted"] >= 1
    assert all("entry_command_template" not in row for row in phase_alignment["residual_lanes"])
    assert all("template" not in row for row in phase_alignment["owner_surfaces"])
    retirement_source = compact["observation_sources"]["observed_mechanism_debt_retirement"]
    assert "retired_debt_count" in retirement_source
    assert "retired_debt_ids" not in retirement_source
    sources = compact["observation_sources"]
    assert "surface_authoring_audit" not in sources
    assert sources["deferred_by_quick_profile_sources"]["count"] >= 1
    assert "process_audit_pattern_classes" not in sources["agent_path_events"]
    assert sources["agent_path_events"]["process_audit_pattern_class_count"] >= len(
        sources["agent_path_events"]["process_audit_pattern_classes_preview"]
    )
    annex_summary = sources["annex_currentness"]["summary"]
    assert "bucket_counts" not in annex_summary
    assert "bucket_counts_nonzero" in annex_summary
    assert compact["debt_rows"]
    assert compact["navigation_mechanism_metabolism"]["cli_compacted"] is True
    quality_signal = compact["quality_signal"]
    assert quality_signal["cli_compacted"] is True
    assert quality_signal["component_drilldown_policy"] == "filter debt_rows by debt_class"
    assert "drilldown_into_components" not in quality_signal
    assert "components" in quality_signal
    assert "authoritative_decision_command" not in json.dumps(quality_signal, sort_keys=True)
    mechanism = compact["navigation_mechanism_metabolism"]
    assert "observed_claim_refs" not in mechanism
    assert mechanism.get("observed_claim_ref_count", 0) >= 1
    assert mechanism.get("top_candidate_claims_omitted", 0) >= 1


def test_quality_signal_has_no_false_bottleneck_when_clean() -> None:
    signal = _quality_signal(_count_by_class([]), process_audit_status="deferred_by_quick_profile")

    assert signal["score"] == 1.0
    assert signal["status"] == "clean"
    assert signal["bottleneck_debt_class"] is None
    assert all(value == 1.0 for value in signal["components"].values())


def test_quality_signal_keeps_bottleneck_when_debt_exists() -> None:
    counts = _count_by_class(
        [
            {
                "debt_id": "latency:slow",
                "debt_class": "latency_debt",
                "priority": 100,
                "title": "Slow command",
            }
        ]
    )

    signal = _quality_signal(counts, process_audit_status="deferred_by_quick_profile")

    assert signal["status"] == "debt"
    assert signal["bottleneck_debt_class"] == "latency_debt"
    assert signal["components"]["latency_debt"] == 0.5


def test_priority_trim_preserves_active_required_bottleneck_class() -> None:
    rows = [
        {
            "debt_id": f"projection:{index}",
            "debt_class": "projection_debt",
            "priority": 100 - index,
            "title": f"Projection row {index}",
        }
        for index in range(10)
    ]
    rows.extend(
        [
            {
                "debt_id": "behavior:retired",
                "debt_class": "behavior_debt",
                "priority": 99,
                "title": "Retired behavior row",
                "active_debt": False,
                "advisory_only": True,
            },
            {
                "debt_id": "behavior:active",
                "debt_class": "behavior_debt",
                "priority": 10,
                "title": "Active behavior row",
            },
        ]
    )

    trimmed = _priority_trim_debt_rows(rows, limit=3, required_active_class="behavior_debt")
    debt_ids = {row["debt_id"] for row in trimmed}

    assert "behavior:active" in debt_ids
    assert "behavior:retired" not in debt_ids


def test_budget_trim_preserves_named_bottleneck_drilldown() -> None:
    packet = {
        "budget": {
            "context_budget_tokens": 1000,
            "hard_ceiling": True,
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "quality_signal": {
            "bottleneck_debt_class": "behavior_debt",
        },
        "summary": {
            "projection_debt": 10,
            "behavior_debt": 1,
            "total_debt_rows": 11,
            "quality_signal_bottleneck": "behavior_debt",
        },
        "debt_rows": [
            {
                "debt_id": f"projection:{index}",
                "debt_class": "projection_debt",
                "priority": 100 - index,
                "title": f"Projection row {index}",
            }
            for index in range(10)
        ]
        + [
            {
                "debt_id": "behavior:retired",
                "debt_class": "behavior_debt",
                "priority": 99,
                "title": "Retired behavior row",
                "active_debt": False,
                "advisory_only": True,
            },
            {
                "debt_id": "behavior:active",
                "debt_class": "behavior_debt",
                "priority": 10,
                "title": "Active behavior row",
            },
        ],
        "top_repairs": [],
        "oversized_debug_blob": "x" * 50000,
    }

    trimmed = _budget_trim(packet, context_budget=1000)
    debt_ids = {row["debt_id"] for row in trimmed["debt_rows"]}

    assert "behavior:active" in debt_ids
    assert trimmed["summary"]["bottleneck_drilldowns_in_packet"] >= 1
    assert trimmed["summary"]["bottleneck_drilldown_status"] == "available_in_packet"


def test_navigation_metabolism_ledger_unifies_debt_classes() -> None:
    payload = build_navigation_metabolism_ledger(
        REPO_ROOT,
        query="navigation context compression",
        context_budget=12000,
        include_session_summary=False,
        metabolism_profile="quick",
        behavior_events=[
            {
                "session_id": "fixture",
                "agent_runtime": "codex",
                "tool": "Bash",
                "command": "./repo-python kernel.py --skill-find agent_session_diagnostics",
                "first_contact": True,
                "output_bytes": 84231,
            }
        ],
    )

    assert payload["kind"] == "navigation_metabolism_ledger"
    assert payload["schema_version"] == "navigation_metabolism_ledger_v0"
    assert payload["metabolism_profile"] == "quick"
    assert payload["strategy"]["single_ratchet"] is True
    assert payload["strategy"]["profile"] == "quick"
    if payload["budget"]["over_budget"]:
        assert payload["budget"]["budget_contract"] == "best_effort_trim_target"
        assert payload["budget"]["over_budget"] is True
        assert payload["budget"]["hard_ceiling"] is False
    else:
        assert payload["budget"]["estimated_tokens"] <= payload["budget"]["context_budget_tokens"]
        assert payload["budget"]["over_budget"] is False
    assert payload["summary"]["entrypoint_debt"] >= 0
    assert payload["summary"]["sufficiency_debt"] >= 0
    assert "latency_debt" in payload["summary"]
    assert "clusterability_debt" in payload["summary"]
    assert payload["summary"]["clusterability_debt"] >= 0
    assert payload["summary"]["routing_coverage_debt"] == 0
    assert "annex_currentness_debt" in payload["summary"]
    assert payload["entrypoint_health"]["summary"]["contract_status"] in {"valid", "entrypoint_debt"}
    over_budget_entrypoint_debt = [
        row
        for row in payload["debt_rows"]
        if row.get("debt_class") == "entrypoint_debt"
        and row.get("repair_class") == "entrypoint_shrink_or_split"
    ]
    if over_budget_entrypoint_debt:
        summary = payload["entrypoint_health"]["summary"]
        assert (
            int(summary.get("over_budget_count") or 0)
            + int(summary.get("generated_or_doctrine_over_budget_count") or 0)
        ) >= 1
    assert payload["observation_sources"]["entrypoint_health"]["status"] == "available"
    assert payload["observation_sources"]["clusterability"]["status"] == "deferred_by_quick_profile"
    assert payload["observation_sources"]["annex_routing_coverage"]["status"] == "deferred_by_quick_profile"
    assert payload["observation_sources"]["annex_currentness"]["status"] == "available"
    assert payload["observation_sources"]["annex_movement_pressure_map"]["status"] == "available"
    assert payload["observation_sources"]["annex_navigation_dogfood"]["status"] == "deferred_by_quick_profile"
    assert payload["observation_sources"]["navigation_fitness"]["status"] == "deferred_by_quick_profile"
    hook_status = payload["observation_sources"]["hook_shadow_coverage"]["status"]
    assert hook_status in {"available", "no_recent_anti_patterns"}
    assert payload["hook_shadow_coverage"]["authority"] == "anti_pattern_id_then_repair_class"
    hook_ratio = payload["hook_shadow_coverage"]["hook_shadow_coverage_top_patterns"]
    assert "/" in hook_ratio
    if hook_status == "no_recent_anti_patterns":
        assert hook_ratio == "0/0"

    classes = {row["debt_class"] for row in payload["debt_rows"]}
    assert payload["summary"]["authoring_debt"] >= 0
    assert {
        "projection_debt",
        "behavior_debt",
    }.issubset(classes)
    if payload["summary"]["authoring_debt"]:
        assert "authoring_debt" in classes
    assert "annex_import_debt" in payload["summary"]
    assert "layer_sprawl_debt" in payload["summary"]
    if payload["summary"]["annex_currentness_debt"]:
        assert "annex_currentness_debt" in classes
    bottleneck = payload["summary"].get("quality_signal_bottleneck")
    if payload["budget"].get("trimmed_for_budget") and bottleneck and payload["summary"].get(bottleneck, 0):
        assert payload["summary"]["bottleneck_drilldowns_in_packet"] >= 1
        assert payload["summary"]["bottleneck_drilldown_status"] == "available_in_packet"
        assert any(
            row.get("debt_class") == bottleneck and row.get("active_debt") is not False
            for row in payload["debt_rows"]
        )

    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "authoring:paper_modules:navigation_rosetta_math" not in debt_ids
    if payload["summary"]["authoring_debt"]:
        assert "authoring:paper_modules:holographic_navigation_compression" in debt_ids
    assert "projection:paper_modules.row_flag_all.library" in debt_ids
    paper_projection = next(
        row for row in payload["debt_rows"] if row["debt_id"] == "projection:paper_modules.row_flag_all.library"
    )
    assert paper_projection["library_reference_only"] is True
    assert paper_projection["advisory_only"] is True
    assert paper_projection["active_debt"] is False
    assert "reference" in paper_projection["title"]
    assert "unsafe" in paper_projection["title"]
    assert "CLI redirects" in paper_projection["compatibility_behavior"]
    active_projection_rows = [
        row
        for row in payload["debt_rows"]
        if row.get("debt_class") == "projection_debt" and row.get("active_debt") is not False
    ]
    # summary.projection_debt is the pre-trim count of all projection_debt rows;
    # active_projection_rows is the post-trim visible-active subset. When trimming
    # occurs, the summary count is at least the visible count; when the packet is
    # untrimmed, exact equality holds.
    if payload["budget"].get("trimmed_for_budget"):
        assert payload["summary"]["projection_debt"] >= len(active_projection_rows)
    else:
        assert payload["summary"]["projection_debt"] == len(active_projection_rows)
    phase_summary_projection = payload["observation_sources"].get("phase_summary_projection_status")
    if phase_summary_projection:
        assert phase_summary_projection["contract_status"] in {
            "valid",
            "deferred_by_quick_profile",
        }
        assert phase_summary_projection["status"] in {
            "retired_from_quick_debt",
            "deferred_by_quick_profile",
        }
        if phase_summary_projection["status"] == "deferred_by_quick_profile":
            assert phase_summary_projection["safe_alternative"] == "./repo-python kernel.py --phase --warnings-only"
    assert "projection:phase.summary_default" not in debt_ids
    top_repair_ids = {row["debt_id"] for row in payload["top_repairs"]}
    assert "projection:paper_modules.row_flag_all.library" not in top_repair_ids
    assert "projection:phase.summary_default" not in top_repair_ids
    assert top_repair_ids
    assert all(row.get("library_reference_only") is not True for row in payload["top_repairs"])
    assert "clusterability:annex_patterns" not in debt_ids
    assert "clusterability:standards" not in debt_ids
    if payload["summary"]["clusterability_debt"]:
        assert "clusterability:standard_skill_map" not in debt_ids
        assert {"clusterability:transform_job_receipts", "clusterability:row_patches"} & debt_ids
    assert "routing_coverage:annex_patterns:unrouted" not in debt_ids
    assert "behavior:skill_find_first_contact" in debt_ids
    if payload["summary"]["annex_import_debt"]:
        assert "annex:arxiv-2604-19572:adaptive_terminal_compression_rules" in debt_ids
    else:
        assert payload["annex_intake"][0]["import_status"] == "mapped"
        assert payload["annex_intake"][0]["ratchet_mapped_pattern_count"] >= 1
        assert "route_event_overcompression_feedback" in payload["annex_intake"][0]["mapped_repair_classes"]
    if payload["budget"].get("trimmed_for_budget"):
        assert payload["summary"]["layer_sprawl_debt"] >= 0
    else:
        # skill_find is now active_typed_debug_trace — actively maintained DEBUG_TRACE
        # surface with surface_role-enforced first_contact_allowed=False — and no longer
        # emits a layer_sprawl debt row. The fixture behavior event above still proves
        # actual first-contact use lands as behavior debt.
        assert "layer_sprawl:skill_find" not in debt_ids

    skill_find = next(row for row in payload["route_lifecycle"] if row["route_id"] == "skill_find")
    assert skill_find["status"] == "active_typed_debug_trace"
    assert "--entry" in skill_find["superseded_by"]
    assert "skills" in skill_find["superseded_by"]
    assert "DEBUG_TRACE" in skill_find["compatibility_behavior"]
    phase_summary = next(row for row in payload["route_lifecycle"] if row["route_id"] == "phase.summary_default")
    assert phase_summary["status"] == "active"
    assert "layer_sprawl:phase.summary_default" not in debt_ids

    coverage_matrix = next(
        row for row in payload["route_lifecycle"] if row["route_id"] == "coverage_enforcement_matrix"
    )
    assert coverage_matrix["status"] == "active"
    assert "per-kind coverage-first enforcement matrix" in coverage_matrix["purpose"]
    assert "not a new registry" in coverage_matrix["compatibility_behavior"]

    phase_alignment = next(row for row in payload["route_lifecycle"] if row["route_id"] == "phase_task_alignment")
    assert phase_alignment["status"] == "active"
    assert "residual lanes" in phase_alignment["purpose"]
    assert "navigation_enforcement" in phase_alignment["compatibility_behavior"]
    assert "active phase" in phase_alignment["compatibility_behavior"]
    assert "09_44" not in phase_alignment["compatibility_behavior"]
    assert phase_alignment["residual_lanes"][0]["lane_id"] == "navigation_enforcement"
    assert phase_alignment["residual_lanes"][0]["entry_command_template"].endswith(
        '"<task>" --context-budget 12000'
    )
    assert phase_alignment["owner_surfaces"][0]["surface_id"] == "coverage_enforcement_matrix"
    assert "mixed_lane" in phase_alignment["write_guard"]

    python_scopes = next(row for row in payload["route_lifecycle"] if row["route_id"] == "python_scopes.row_flag_all")
    assert python_scopes["status"] == "compatibility_shim"
    assert python_scopes["superseded_by"] == "python_scopes.cluster_flag"
    assert "CLI redirects" in python_scopes["compatibility_behavior"]

    standards = next(row for row in payload["route_lifecycle"] if row["route_id"] == "standards.row_flag_all")
    assert standards["status"] == "compatibility_shim"
    assert standards["superseded_by"] == "standards.cluster_flag"

    frontend_components = next(
        row for row in payload["route_lifecycle"] if row["route_id"] == "frontend_components.row_flag_all"
    )
    assert frontend_components["status"] == "compatibility_shim"
    assert frontend_components["superseded_by"] == "frontend_components.cluster_flag"

    principles = next(row for row in payload["route_lifecycle"] if row["route_id"] == "principles.row_flag_all")
    assert principles["status"] == "compatibility_shim"
    assert principles["superseded_by"] == "principles.cluster_flag"

    annex_patterns = next(row for row in payload["route_lifecycle"] if row["route_id"] == "annex_patterns.row_flag_all")
    assert annex_patterns["status"] == "compatibility_shim"
    assert annex_patterns["superseded_by"] == "annex_patterns.cluster_flag"

    coverage = next(row for row in payload["route_lifecycle"] if row["route_id"] == "annex_routing_coverage")
    assert coverage["status"] == "active_input"
    assert "unrouted" in coverage["purpose"]

    currentness = next(row for row in payload["route_lifecycle"] if row["route_id"] == "annex_currentness")
    assert currentness["status"] == "active_input"
    assert "sync digest" in currentness["purpose"]

    pressure_map = next(row for row in payload["route_lifecycle"] if row["route_id"] == "annex_movement_pressure_map")
    assert pressure_map["status"] == "active_input"
    assert "lane selector" in pressure_map["purpose"]
    assert "owner-review blockers" in pressure_map["purpose"]

    dogfood = next(row for row in payload["route_lifecycle"] if row["route_id"] == "annex_navigation_dogfood")
    assert dogfood["status"] == "active_input"
    assert "self-use composer" in dogfood["purpose"]

    annex_distillation = next(
        row for row in payload["route_lifecycle"] if row["route_id"] == "annex_distillation_patterns.row_flag_all"
    )
    assert annex_distillation["status"] == "compatibility_shim"
    assert annex_distillation["superseded_by"] == "annex_distillation_patterns.cluster_flag"

    paper_lattice = next(row for row in payload["route_lifecycle"] if row["route_id"] == "paper_lattice")
    assert paper_lattice["status"] == "active_stable_slug_drilldown"
    assert paper_lattice["generic_existing_slug_support"] is True
    assert "paper_modules/<slug>.md" in paper_lattice["supported_slug_source"]
    assert "stable paper-module slug" in paper_lattice["entry_condition"]

    model_instructions = next(
        row for row in payload["route_lifecycle"] if row["route_id"] == "codex.model_instructions_file"
    )
    assert model_instructions["status"] == "experimental_high_blast"
    assert "not normal repo bootstrap" in model_instructions["purpose"]

    behavior = next(row for row in payload["debt_rows"] if row["debt_id"] == "behavior:skill_find_first_contact")
    assert behavior["anti_pattern"] == "keyword_search_before_cluster_surface"
    assert behavior["better_first_surface"].endswith("--option-surface skills --band cluster_flag")


def test_annex_intake_maps_taco_patterns_to_route_event_repair_classes(tmp_path: Path) -> None:
    annex_root = tmp_path / "annexes" / TACO_ANNEX
    annex_root.mkdir(parents=True)
    (annex_root / "annex_index.json").write_text(
        json.dumps({"title": "TACO"}, indent=2) + "\n",
        encoding="utf-8",
    )
    (annex_root / "annex_notes.json").write_text(
        json.dumps({"notes": [{"id": "n001"}]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (annex_root / "distillation.json").write_text(
        json.dumps(
            {
                "distillation_status": "partial",
                "patterns": [
                    {
                        "id": "p003",
                        "name": "over-compression complaint feedback",
                        "one_liner": "Requests for full output repair the compression rule.",
                        "axis": "evaluation_feedback",
                        "adoption_status": "evaluated",
                        "source_locus": ["prompt/prompt-for-conservative-rule-update-after-over-compression-c"],
                        "local_target": ["system/lib/navigation_metabolism_ledger.py"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    intake, debt = _annex_intake_rows(tmp_path)

    assert debt == []
    assert intake[0]["import_status"] == "mapped"
    assert intake[0]["ratchet_mapped_pattern_ids"] == ["p003"]
    assert intake[0]["mapped_repair_classes"] == ["route_event_overcompression_feedback"]


def test_navigation_metabolism_command_full_profile_can_emit_inline_json(monkeypatch, capsys) -> None:
    """Explicit full profile + AIW_COMMAND_OUTPUT_INLINE=1 keeps the rich audit-shape contract.

    Sidecar containment is the new default for full profile, so the rich-shape
    test opts out of containment while stubbing the expensive builder.
    """
    from system.lib.kernel import state as kernel_state
    from system.lib.kernel.commands.navigate import cmd_navigation_metabolism
    import system.lib.navigation_metabolism_ledger as ledger_module

    def fake_build(*_args, **kwargs):
        assert kwargs["metabolism_profile"] == "full"
        return _fake_metabolism_payload("full")

    kernel_state.init(REPO_ROOT)
    monkeypatch.setenv("AIW_COMMAND_OUTPUT_INLINE", "1")
    monkeypatch.setattr(ledger_module, "build_navigation_metabolism_ledger", fake_build)

    rc = cmd_navigation_metabolism("navigation context compression", context_budget=12000, metabolism_profile="full")
    captured = capsys.readouterr()

    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["kind"] == "navigation_metabolism_ledger"
    assert payload["metabolism_profile"] == "full"


def test_navigation_metabolism_cli_default_is_quick_profile() -> None:
    """Default --navigation-metabolism must stay on the cheap, bounded path.

    Concurrent agents who omit --metabolism-profile must not pull the expensive
    full ledger. Full is opt-in only.
    """
    result = _run_kernel_cli(
        [
            "--navigation-metabolism",
            "command substrate fast path",
            "--context-budget",
            "12000",
        ]
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "navigation_metabolism_ledger"
    assert payload["metabolism_profile"] == "quick"
    assert payload["strategy"]["profile"] == "quick"
    assert payload["budget"]["cli_compacted_for_output"] is True
    assert len(result.stdout.encode("utf-8")) <= 32 * 1024


def test_navigation_metabolism_command_full_profile_is_explicit_optin(monkeypatch, capsys) -> None:
    """--metabolism-profile full remains available, but only when explicitly requested.

    Default sidecar containment is overridden via AIW_COMMAND_OUTPUT_INLINE=1
    so the inline payload is observable for the profile assertion.
    """
    from system.lib.kernel import state as kernel_state
    from system.lib.kernel.commands.navigate import cmd_navigation_metabolism
    import system.lib.navigation_metabolism_ledger as ledger_module

    def fake_build(*_args, **kwargs):
        assert kwargs["metabolism_profile"] == "full"
        return _fake_metabolism_payload("full")

    kernel_state.init(REPO_ROOT)
    monkeypatch.setenv("AIW_COMMAND_OUTPUT_INLINE", "1")
    monkeypatch.setattr(ledger_module, "build_navigation_metabolism_ledger", fake_build)

    rc = cmd_navigation_metabolism("command substrate fast path", context_budget=12000, metabolism_profile="full")
    captured = capsys.readouterr()

    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["metabolism_profile"] == "full"
    assert payload["strategy"]["profile"] == "full"


def test_quick_navigation_metabolism_keeps_phase_summary_out_of_active_debt() -> None:
    payload = build_navigation_metabolism_ledger(
        REPO_ROOT,
        query="phase summary projection watch",
        context_budget=12000,
        include_session_summary=False,
        metabolism_profile="quick",
    )

    phase_status = payload["observation_sources"]["phase_summary_projection_status"]
    assert phase_status["contract_status"] in {"valid", "deferred_by_quick_profile"}
    assert phase_status["status"] in {"retired_from_quick_debt", "deferred_by_quick_profile"}
    if phase_status["status"] == "deferred_by_quick_profile":
        assert phase_status["safe_alternative"] == "./repo-python kernel.py --phase --warnings-only"

    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "projection:phase.summary_default" not in debt_ids
    assert "layer_sprawl:phase.summary_default" not in debt_ids

    phase_route = next(row for row in payload["route_lifecycle"] if row["route_id"] == "phase.summary_default")
    assert phase_route["status"] == "active"
    assert "full evidence remains behind --full" in phase_route["compatibility_behavior"]


def test_phase_summary_projection_status_uses_own_packet_budget_not_caller_trim_budget() -> None:
    """Regression: phase summary's bounded-control-packet contract must not be measured
    against the metabolism ledger's trim budget. The default kernel CLI passes
    --context-budget=1400 (the metabolism ledger's trim target). When that small budget
    is propagated to the phase-summary contract checker, the ~12,000-byte phase summary
    packet falsely reports `violates_entry_contract` even though the actual phase summary
    is well-formed and within its own intended ~12,000-token budget.

    Fix: _phase_summary_projection_status uses a fixed PHASE_SUMMARY_BOUNDED_PACKET_BUDGET_TOKENS
    constant (12000) for budget_bytes, ignoring the caller's context_budget.
    """
    from system.lib.navigation_metabolism_ledger import (
        PHASE_SUMMARY_BOUNDED_PACKET_BUDGET_TOKENS,
        _phase_summary_projection_status,
    )

    # Run with the small metabolism-ledger trim budget. Pre-fix, this asserted "violates".
    result = _phase_summary_projection_status(REPO_ROOT, context_budget=1400)
    assert result["contract_status"] == "valid"
    assert result["status"] == "retired_from_quick_debt"
    assert result["budget_bytes"] == PHASE_SUMMARY_BOUNDED_PACKET_BUDGET_TOKENS * 4
    assert result["budget_relation"] in {"within_budget", "large_but_within_budget"}

    # And with no budget passed: still uses the fixed phase-summary packet budget.
    result_none = _phase_summary_projection_status(REPO_ROOT, context_budget=0)
    assert result_none["contract_status"] == "valid"
    assert result_none["budget_bytes"] == PHASE_SUMMARY_BOUNDED_PACKET_BUDGET_TOKENS * 4


def test_cmd_navigation_metabolism_function_default_is_quick(capsys) -> None:
    """The command-surface function default must be quick, independent of argparse.

    Direct in-process callers should never inherit the full profile by accident.
    """
    from system.lib.kernel import state as kernel_state
    from system.lib.kernel.commands.navigate import cmd_navigation_metabolism

    kernel_state.init(REPO_ROOT)
    rc = cmd_navigation_metabolism("command substrate fast path", context_budget=12000)
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["kind"] == "navigation_metabolism_ledger"
    assert payload["metabolism_profile"] == "quick"


def test_cmd_navigation_metabolism_quick_timeout_emits_packet(monkeypatch, capsys) -> None:
    """The quick command surface must degrade to JSON instead of hanging."""
    from system.lib.kernel import state as kernel_state
    from system.lib.kernel.commands.navigate import cmd_navigation_metabolism
    import system.lib.navigation_metabolism_ledger as ledger_module

    def slow_build(*_args, **_kwargs):
        time.sleep(0.05)
        return {"kind": "unreachable"}

    kernel_state.init(REPO_ROOT)
    monkeypatch.setenv("AIW_NAVIGATION_METABOLISM_TIMEOUT_MS", "1")
    monkeypatch.setattr(ledger_module, "build_navigation_metabolism_ledger", slow_build)

    rc = cmd_navigation_metabolism("timeout budget", context_budget=12000)
    captured = capsys.readouterr()

    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["kind"] == "navigation_metabolism_timeout_packet"
    assert payload["failure_kind"] == "navigation_metabolism_timeout"
    assert payload["metabolism_profile"] == "quick"
    assert payload["work_item_ref"] == "lifecycle-navigation-metabolism-budget-probe-timeout"


def test_navigation_metabolism_full_profile_emits_sidecar_receipt_by_default(monkeypatch, capsys) -> None:
    """Without explicit opt-out, --metabolism-profile full sidecars heavy output."""
    from system.lib.kernel import state as kernel_state
    from system.lib.kernel.commands.navigate import cmd_navigation_metabolism
    import system.lib.navigation_metabolism_ledger as ledger_module

    def fake_build(*_args, **kwargs):
        assert kwargs["metabolism_profile"] == "full"
        return _fake_metabolism_payload("full", oversize=True)

    kernel_state.init(REPO_ROOT)
    monkeypatch.delenv("AIW_COMMAND_OUTPUT_INLINE", raising=False)
    monkeypatch.delenv("AIW_COMMAND_OUTPUT_SIDECAR_BYTES", raising=False)
    monkeypatch.setattr(ledger_module, "build_navigation_metabolism_ledger", fake_build)

    rc = cmd_navigation_metabolism("command substrate fast path", context_budget=12000, metabolism_profile="full")
    captured = capsys.readouterr()

    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["kind"] == "command_output_receipt"
    assert payload["status"] == "written_to_sidecar"
    assert payload["surface"] == "navigation_metabolism.full"
    assert payload["policy"]["trigger_source"] == "heavy_surface_default"
    sidecar = REPO_ROOT / payload["output_path"]
    assert sidecar.is_file()
    full_payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert full_payload["kind"] == "navigation_metabolism_ledger"
    assert full_payload["metabolism_profile"] == "full"
    sidecar.unlink()
    parent = sidecar.parent
    if not any(parent.iterdir()):
        parent.rmdir()


def test_navigation_metabolism_promotes_fitness_failures_to_debt_rows() -> None:
    payload = build_navigation_metabolism_ledger(
        REPO_ROOT,
        query="navigation fitness",
        context_budget=12000,
        include_session_summary=False,
        metabolism_profile="quick",
        fitness_payload={
            "kind": "navigation_fitness",
            "suite": "fixture",
            "strategy": {"fitness_mode": "semantic"},
            "summary": {"task_count": 1, "debt_candidate_count": 2},
            "route_type_metrics": {
                "context_pack": {
                    "count": 2,
                    "p50_wall_ms": 9000,
                    "p95_wall_ms": 9000,
                    "max_wall_ms": 9000,
                    "latency_fail_count": 1,
                }
            },
            "debt_candidates": [
                {
                    "debt_id": "sufficiency:context_pack:fixture_missing",
                    "debt_class": "sufficiency_debt",
                    "priority": 87,
                    "title": "fixture missing expected id",
                    "evidence": "missing=['skills:agent_session_diagnostics']",
                    "repair_class": "compression_passport_or_selector_repair",
                    "target_files": ["system/lib/navigation_context_pack.py"],
                    "tests": ["fixture passes"],
                    "task_id": "fixture_missing",
                    "route_type": "context_pack",
                    "route_role": "first_contact",
                    "failure_kind": "weak_scent",
                    "fitness_mode": "semantic",
                },
                {
                    "debt_id": "latency:context_pack:fixture_slow",
                    "debt_class": "latency_debt",
                    "priority": 78,
                    "title": "fixture slow route",
                    "evidence": "wall_ms=9000",
                    "repair_class": "cache_or_precompute_selector",
                    "target_files": ["system/lib/navigation_context_pack.py"],
                    "tests": ["fixture latency passes"],
                    "task_id": "fixture_slow",
                    "route_type": "context_pack",
                    "route_role": "first_contact",
                    "slow_stage": "semantic_candidates",
                    "fitness_mode": "semantic",
                },
            ],
        },
    )

    assert payload["summary"]["sufficiency_debt"] >= 1
    assert payload["summary"]["latency_debt"] >= 1
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "sufficiency:context_pack:fixture_missing" in debt_ids
    assert "latency:context_pack:fixture_slow" in debt_ids
    assert payload["observation_sources"]["navigation_fitness"]["fitness_mode"] == "semantic"
    assert payload["observation_sources"]["navigation_fitness"]["route_type_metrics"]["context_pack"]["latency_fail_count"] == 1
    latency = next(row for row in payload["debt_rows"] if row["debt_id"] == "latency:context_pack:fixture_slow")
    assert latency["slow_stage"] == "semantic_candidates"
    assert latency["fitness_mode"] == "semantic"
    assert latency["route_role"] == "first_contact"
    sufficiency = next(
        row for row in payload["debt_rows"] if row["debt_id"] == "sufficiency:context_pack:fixture_missing"
    )
    assert sufficiency["failure_kind"] == "weak_scent"


def test_navigation_metabolism_promotes_fitness_timeouts_to_distinct_timeout_debt() -> None:
    payload = build_navigation_metabolism_ledger(
        REPO_ROOT,
        query="navigation fitness timeouts",
        context_budget=12000,
        include_session_summary=False,
        metabolism_profile="quick",
        fitness_payload={
            "kind": "navigation_fitness",
            "suite": "smoke",
            "strategy": {"fitness_mode": "cli"},
            "summary": {"task_count": 1, "debt_candidate_count": 1},
            "route_type_metrics": {
                "navigation_metabolism": {
                    "count": 1,
                    "p50_wall_ms": 8013,
                    "p95_wall_ms": 8013,
                    "max_wall_ms": 8013,
                    "latency_fail_count": 1,
                }
            },
            "debt_candidates": [
                {
                    "debt_id": "timeout:navigation_metabolism:entrypoint_budget_route_health",
                    "debt_class": "timeout_debt",
                    "priority": 88,
                    "title": (
                        "Navigation route timed out before producing a packet; "
                        "repair_owner=system/lib/navigation_metabolism_ledger.py; "
                        "hidden_expected_ids=['entrypoint_health:valid', 'route_lifecycle:context_pack']"
                    ),
                    "evidence": "failure_kind=route_timeout; wall_ms=8013; latency_budget_ms=6000",
                    "repair_class": "split_metabolism_summary_from_full",
                    "target_files": [
                        "system/lib/navigation_metabolism_ledger.py",
                        "system/lib/navigation_fitness.py",
                    ],
                    "tests": ["navigation-fitness timeout debt names hidden expected ids and repair owner"],
                    "task_id": "entrypoint_budget_route_health",
                    "route_type": "navigation_metabolism",
                    "route_role": "diagnostic",
                    "failure_kind": "route_timeout",
                    "fitness_mode": "cli",
                    "slow_stage": None,
                    "hidden_expected_artifacts": [
                        "entrypoint_health:valid",
                        "route_lifecycle:context_pack",
                    ],
                },
            ],
        },
    )

    assert payload["summary"]["timeout_debt"] >= 1
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "timeout:navigation_metabolism:entrypoint_budget_route_health" in debt_ids
    timeout_row = next(
        row
        for row in payload["debt_rows"]
        if row["debt_id"] == "timeout:navigation_metabolism:entrypoint_budget_route_health"
    )
    assert timeout_row["debt_class"] == "timeout_debt"
    assert timeout_row["failure_kind"] == "route_timeout"
    assert timeout_row["fitness_mode"] == "cli"
    assert timeout_row["hidden_expected_artifacts"] == [
        "entrypoint_health:valid",
        "route_lifecycle:context_pack",
    ]
    assert "system/lib/navigation_metabolism_ledger.py" in timeout_row["target_files"]


def test_navigation_metabolism_exposes_route_learning_acceptance_posture() -> None:
    process_audit, _ = _cached_process_audit_payload(REPO_ROOT, allow_build=True)
    warmed_block, warmed_status = _cached_navigation_mechanism_metabolism(
        REPO_ROOT,
        process_audit,
        allow_build=True,
    )
    assert warmed_block["projected_count"] == 6
    assert warmed_block["observed_count"] == 6
    assert warmed_status["status"] in {"hit", "miss_built", "waited_hit"}

    payload = build_navigation_metabolism_ledger(
        REPO_ROOT,
        query="route learning acceptance posture",
        context_budget=12000,
        include_session_summary=False,
        metabolism_profile="quick",
    )

    block = payload["navigation_mechanism_metabolism"]
    assert block["status"] == "candidate_learning_available"
    assert block["candidate_count"] >= 1
    assert block["validated_count"] >= 1
    assert block["accepted_count"] == 6
    assert block["projected_count"] == 6
    assert block["observed_count"] == 6
    assert block["authority_posture"] == "candidate_and_validated_are_not_accepted"
    assert set(block["observed_anti_pattern_ids"]) == {
        "anti_pattern_grep_before_kernel",
        "anti_pattern_paper_module_skip",
        "anti_pattern_loop_detected",
        "anti_pattern_cold_boot_missing_info",
        "anti_pattern_stall_detected",
        "anti_pattern_deep_without_ladder",
    }
    observed_claims_by_pattern = {row["anti_pattern_id"]: row for row in block["observed_claim_refs"]}
    assert set(observed_claims_by_pattern) == set(block["observed_anti_pattern_ids"])
    assert payload["observation_sources"]["navigation_mechanism_metabolism"]["validated_count"] == block["validated_count"]
    retirement = payload["observation_sources"]["observed_mechanism_debt_retirement"]
    assert retirement["retired_debt_count"] == 6
    assert set(retirement["observed_anti_pattern_ids"]) == set(block["observed_anti_pattern_ids"])
    retired_debt_ids = set(retirement["retired_debt_ids"])
    assert "behavior:process_audit:anti_pattern_grep_before_kernel" in retired_debt_ids
    assert "behavior:process_audit:anti_pattern_paper_module_skip" in retired_debt_ids
    assert "behavior:process_audit:anti_pattern_loop_detected" in retired_debt_ids
    assert "behavior:process_audit:anti_pattern_cold_boot_missing_info" in retired_debt_ids
    assert "behavior:process_audit:anti_pattern_stall_detected" in retired_debt_ids
    assert "behavior:process_audit:anti_pattern_deep_without_ladder" in retired_debt_ids
    top_repair_ids = {row["debt_id"] for row in payload["top_repairs"]}
    assert "behavior:process_audit:anti_pattern_grep_before_kernel" not in top_repair_ids
    assert "behavior:process_audit:anti_pattern_paper_module_skip" not in top_repair_ids
    assert "behavior:process_audit:anti_pattern_loop_detected" not in top_repair_ids
    assert "behavior:process_audit:anti_pattern_cold_boot_missing_info" not in top_repair_ids
    assert "behavior:process_audit:anti_pattern_stall_detected" not in top_repair_ids
    assert "behavior:process_audit:anti_pattern_deep_without_ladder" not in top_repair_ids
    debt_by_id = {row["debt_id"]: row for row in payload["debt_rows"]}
    for debt_id in retired_debt_ids & set(debt_by_id):
        assert debt_by_id[debt_id]["active_debt"] is False

    top = block["top_candidate_claims"][0]
    assert top["next_owner_surface"]
    assert top["replay_status"] == "passed"
    assert top["validation_status"] == "valid"
    assert top["future_observation"]["status"]

    paper = next(
        row
        for row in block["top_candidate_claims"]
        if row["claim_id"] == "mpc_9008b18dd3f052e2"
    )
    assert paper["anti_pattern_id"] == "anti_pattern_paper_module_skip"
    assert paper["state"] in {"observed", "superseded"}
    assert paper["latest_acceptance_event_type"] in {"observation.recorded", "claim.superseded"}
    if paper["state"] == "superseded":
        assert "owner materialization now carries the accepted route behavior" in paper["no_count_increment_reason"]
    else:
        assert paper["latest_acceptance_event_type"] == "observation.recorded"
    assert paper["acceptance_event_ref"].startswith("navigation_mechanism_acceptance_event:nmae_")
    assert paper["blocked_event_ref"] == "navigation_mechanism_acceptance_event:nmae_178d6405fd20d36b"
    assert paper["owner_packet_ref"].startswith("navigation_mechanism_owner_packet:nmop_")
    assert paper["owner_locus_ref"].startswith("navigation_mechanism_owner_locus_verification:nmolv_")
    assert paper["replay_receipt_ref"].startswith("navigation_mechanism_replay_receipt:nmrr_")
    assert paper["owner_acceptance_status"] == "accepted"
    assert paper["acceptance_eligibility"] == "accepted"
    assert paper["acceptance_dossier_id"] == "nmad_mpc_9008b18dd3f052e2"
    assert "owner_acceptance_ref_missing" not in paper["missing_refs"]
    assert "durable_replay_receipt_lane_unresolved" not in paper["missing_refs"]
    assert "future_observation_window_unverified" not in paper["missing_refs"]
    assert paper["missing_refs"] == []
    assert "code_or_tool_loci_ref_missing" not in paper["missing_refs"]
    assert paper["no_count_increment_reason"]
    assert paper["future_observation"]["status"] == "observed"
    assert paper["future_observation"]["future_observation_window_status"] == "recorded"
    assert paper["future_observation"]["post_count"] < paper["future_observation"]["baseline_count"]

    cold_boot = observed_claims_by_pattern["anti_pattern_cold_boot_missing_info"]
    assert cold_boot["claim_id"] == "mpc_2442946adc646040"
    assert cold_boot["anti_pattern_id"] == "anti_pattern_cold_boot_missing_info"
    assert cold_boot["state"] == "observed"
    assert cold_boot["owner_acceptance_status"] == "accepted"
    assert cold_boot["acceptance_dossier_id"] == "nmad_mpc_2442946adc646040"
    assert cold_boot["future_observation"]["status"] == "observed"
    assert cold_boot["future_observation"]["post_count"] < cold_boot["future_observation"]["baseline_count"]

    stall = observed_claims_by_pattern["anti_pattern_stall_detected"]
    assert stall["claim_id"] == "mpc_5608ed018582131c"
    assert stall["anti_pattern_id"] == "anti_pattern_stall_detected"
    assert stall["debt_id"] == "behavior:process_audit:anti_pattern_stall_detected"
    assert stall["state"] == "observed"
    assert stall["owner_acceptance_status"] == "accepted"
    assert stall["acceptance_dossier_id"] == "nmad_mpc_5608ed018582131c"
    assert stall["future_observation"]["status"] == "observed"
    assert stall["future_observation"]["post_count"] < stall["future_observation"]["baseline_count"]

    assert block["future_observation"]["future_observation_window_status"] == "recorded"
    assert block["future_observation"]["status"] == "observed"
    assert block["future_observation"]["post_projection_source"].startswith(
        "./repo-python kernel.py --process-audit --after"
    )
    assert "--process-patterns --after" in block["future_observation"]["post_projection_source"]


def test_navigation_mechanism_quick_cache_miss_uses_acceptance_read_model(tmp_path) -> None:
    dossier_root = tmp_path / "codex" / "ledger" / "navigation_mechanism_acceptance" / "dossiers"
    dossier_root.mkdir(parents=True)
    (dossier_root / "claim.json").write_text(
        json.dumps(
            {
                "schema_version": "navigation_mechanism_acceptance_dossier_v0",
                "dossier_id": "nmad_claim_demo",
                "claim_id": "claim_demo",
                "anti_pattern_id": "anti_pattern_demo",
                "state": "projected",
                "acceptance_eligibility": "accepted",
                "read_model_projection": {
                    "latest_acceptance_event_ref": "navigation_mechanism_acceptance_event:nmae_demo",
                    "latest_acceptance_event_type": "projection.recorded",
                    "blocked_event_ref": "navigation_mechanism_acceptance_event:nmae_blocked",
                    "owner_packet_ref": "navigation_mechanism_owner_packet:nmop_demo",
                    "owner_locus_ref": "navigation_mechanism_owner_locus_verification:nmolv_demo",
                    "replay_receipt_ref": "navigation_mechanism_replay_receipt:nmrr_demo",
                },
                "owner_acceptance_ref": "codex/standards/std_navigation_mechanism_acceptance.json#owner_acceptance_proof",
                "projection_ref": "system/lib/demo.py::surface",
                "missing_refs": ["future_observation_window_unverified"],
                "future_observation": {
                    "baseline_window": "current_process_audit_window",
                    "post_projection_window": "after 2026-05-11T00:00:00Z",
                    "metric": "anti_pattern_instances_per_session",
                    "baseline_count": 4,
                    "post_count": None,
                    "status": "awaiting_observation",
                    "future_observation_window_status": "window_selector_available_unrun",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    events_path = tmp_path / "codex" / "ledger" / "navigation_mechanism_acceptance" / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "schema_version": "navigation_mechanism_acceptance_event_v0",
                "event_id": "nmae_demo",
                "claim_id": "claim_demo",
                "anti_pattern_id": "anti_pattern_demo",
                "event_type": "projection.recorded",
                "created_at": "2026-05-11T00:00:00Z",
                "actor": "codex",
                "authority_posture": "projection_proof",
                "previous_event_ref": "navigation_mechanism_acceptance_event:nmae_accept",
                "state_before": "accepted",
                "state_after": "projected",
                "proof_refs": {"projection_ref": "system/lib/demo.py::surface"},
                "missing_refs": ["future_observation_window_unverified"],
                "next_legal_events": ["observation.recorded", "rollback.recorded"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    block, status = _cached_navigation_mechanism_metabolism(
        tmp_path,
        {"status": "available", "summary": {}, "patterns": [], "session_count": 0},
        allow_build=False,
    )

    assert status["status"] == "deferred_missing_cache"
    assert block["status"] == "acceptance_read_model_available"
    assert block["authority_posture"] == "acceptance_read_model_not_candidate_factory"
    assert block["candidate_count"] is None
    assert block["validated_count"] is None
    assert block["accepted_count"] == 1
    assert block["projected_count"] == 1
    assert block["observed_count"] == 0
    assert block["cache_fallback"]["reason"] == "quick_profile_does_not_rebuild_expensive_node"

    card = block["top_candidate_claims"][0]
    assert card["claim_id"] == "claim_demo"
    assert card["state"] == "projected"
    assert card["latest_acceptance_event_type"] == "projection.recorded"
    assert card["replay_status"] == "not_rebuilt_in_quick_profile"
    assert card["future_observation"]["status"] == "awaiting_observation"
