"""Build the meta diagnostics workbench specimen.

[PURPOSE]
Give the public microcosm its own fixture-backed diagnostics for command speed,
command wait tax, context fit, tests, architecture boundaries, and
standalone-wrapper readiness.

[INTERFACE]
Expose a builder that writes a diagnostic board, README, and optional receipt.

[FLOW]
Evaluate synthetic diagnostic cases, bind evaluator authority, summarize repair
routes, and keep private-root/live-performance claims fail-closed.

[DEPENDENCIES]
Uses local fixture rows, JSON/pathlib writes, UTC timestamps, and no private
command logs, provider traces, or external telemetry.

[CONSTRAINTS]
It is a diagnostic fixture only, not command-speed certification, live latency
telemetry, private-root context proof, standalone wrapper shipment, hosted
readiness, or publication approval.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPECIMEN_ID = "meta_diagnostics_workbench_microcosm"
DEFAULT_OUTPUT_PATH = "microcosms/meta_diagnostics_workbench/diagnostic_board.json"
DEFAULT_RECEIPT_PATH = "microcosms/meta_diagnostics_workbench/receipt.json"
README_PATH = "microcosms/meta_diagnostics_workbench/README.md"
AUTHORITY_POSTURE = "public_safe_synthetic_meta_diagnostic_fixture_not_private_root_or_live_performance_authority"
RELEASE_SCOPE_STATEMENT = "This is a distilled beta demonstration of selected mechanisms. It is not the full private system."


FIXTURE_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "case.command_profile_within_budget",
        "diagnostic_family": "command_speed",
        "synthetic_input": "Run a fixture command profile for a root-backed diagnostic builder.",
        "expected_contract": "A command-speed diagnostic records fixture latency bands, budget, owner route, and evidence refs without certifying live performance.",
        "observed_artifact": "Synthetic command completed in 140 ms against a 2500 ms diagnostic budget.",
        "diagnostic_status": "pass",
        "owner_surface": "src/idea_microcosm/cli.py",
        "repair_route": "keep_fixture_budget_row_and_repeat_with_real_receipt_before_any_performance_claim",
        "speed_signal": {
            "source": "synthetic_fixture",
            "threshold_ms": 2500,
            "observed_ms": 140,
            "within_budget": True,
            "certifies_live_performance": False,
        },
        "context_fit_signal": None,
        "test_signal": None,
        "architecture_signal": None,
        "standalone_signal": None,
        "repair_contract": "",
        "next_action": "Use as the command-speed control row for the workbench.",
    },
    {
        "case_id": "case.command_wait_tax_without_singleflight",
        "diagnostic_family": "command_wait_tax",
        "synthetic_input": "A second agent launches the same focused validation while the first run is still active.",
        "expected_contract": "Command latency diagnostics carry a command key, latency band, owner route, and attach-or-reuse repair route without importing live private timing logs.",
        "observed_artifact": "Synthetic duplicate validation spends 38000 ms waiting behind the same command key against a 5000 ms local diagnostic budget.",
        "diagnostic_status": "block",
        "owner_surface": "microcosms/concurrency_mission_control/mission_board.json",
        "repair_route": "claim_command_key_then_attach_or_reuse_focused_validation_before_spawning_duplicate_run",
        "speed_signal": {
            "source": "synthetic_fixture",
            "command_key": "pytest:tests/test_microcosm_contract.py::test_meta_diagnostics_workbench_specimen_routes_meta_failures_without_authority_collapse",
            "command_family": "focused_pytest",
            "threshold_ms": 5000,
            "observed_ms": 38000,
            "wait_tax_ms": 33000,
            "within_budget": False,
            "latency_seed_transfer": True,
            "owner_route": "microcosms/concurrency_mission_control/mission_board.json",
            "certifies_live_performance": False,
        },
        "context_fit_signal": None,
        "test_signal": {
            "source": "synthetic_fixture",
            "singleflight_policy": "attach_or_reuse_active_command_key",
            "reuse_completed_requires_explicit_freshness": True,
            "claim_strengthening_allowed": False,
        },
        "architecture_signal": None,
        "standalone_signal": None,
        "repair_contract": "Route duplicate validation through the command key owner, attach to the active run or reuse a fresh receipt, and narrow scope before spawning another test process.",
        "next_action": "Use the concurrency mission-control command-key row as the local arbiter for repeated slow validation.",
    },
    {
        "case_id": "case.context_pack_over_budget",
        "diagnostic_family": "context_fit",
        "synthetic_input": "Ask a cold reviewer to inspect every source file before choosing a microcosm leaf.",
        "expected_contract": "Context fit must start from entry packet, microcosm index, leaf contract, summary ladder, and selected leaf evidence before source spans.",
        "observed_artifact": "Reviewer opens the whole source tree and exceeds the 12000 token budget before reaching receipts.",
        "diagnostic_status": "block",
        "owner_surface": "microcosms/leaf_entry_contract.json",
        "repair_route": "route_through_leaf_entry_contract_then_selected_leaf_receipt_before_source_span",
        "speed_signal": None,
        "context_fit_signal": {
            "source": "synthetic_fixture",
            "budget_tokens": 12000,
            "estimated_tokens": 21400,
            "within_budget": False,
            "first_repair_surface": "microcosms/leaf_entry_contract.json",
        },
        "test_signal": None,
        "architecture_signal": None,
        "standalone_signal": None,
        "repair_contract": "Compress through the release-local ladder, then drill into one selected evidence surface and receipt.",
        "next_action": "Update reviewer route language if a leaf cannot be selected before source traversal.",
    },
    {
        "case_id": "case.deep_source_traversal_without_ladder",
        "diagnostic_family": "context_fit",
        "synthetic_input": "Debug navigation behavior by grepping implementation files before reading the entry packet.",
        "expected_contract": "Navigation diagnostics use the local entry packet, microcosm index, and self-comprehension navigator before deep source traversal.",
        "observed_artifact": "The agent reaches a source helper but misses the stale-projection refusal and receipt boundary.",
        "diagnostic_status": "block",
        "owner_surface": "microcosms/self_comprehension_navigator/navigator_board.json",
        "repair_route": "use_self_comprehension_navigator_before_source_span",
        "speed_signal": None,
        "context_fit_signal": {
            "source": "synthetic_fixture",
            "budget_tokens": 12000,
            "estimated_tokens": 15600,
            "within_budget": False,
            "first_repair_surface": "microcosms/self_comprehension_navigator/navigator_board.json",
        },
        "test_signal": None,
        "architecture_signal": None,
        "standalone_signal": None,
        "repair_contract": "Recover the selected kind and option-surface row before opening Python source spans.",
        "next_action": "Treat repeated source-first misses as navigation-contract repair, not a one-off reviewer error.",
    },
    {
        "case_id": "case.test_surface_missing_for_claim",
        "diagnostic_family": "test_coverage",
        "synthetic_input": "Add a new meta diagnostic claim to the registry without a validator or focused test.",
        "expected_contract": "Every diagnostic claim has a validator row, CLI build path, fixture receipt, and focused regression test.",
        "observed_artifact": "Registry row exists, but validate cannot prove the diagnostic board shape.",
        "diagnostic_status": "fail",
        "owner_surface": "tests/test_microcosm_contract.py",
        "repair_route": "add_validator_and_cli_regression_before_registry_claim_strengthens",
        "speed_signal": None,
        "context_fit_signal": None,
        "test_signal": {
            "source": "synthetic_fixture",
            "required_validator": "validator.meta_diagnostics_workbench_specimen",
            "required_test": "test_meta_diagnostics_workbench_specimen_routes_meta_failures_without_authority_collapse",
            "claim_strengthening_allowed": False,
        },
        "architecture_signal": None,
        "standalone_signal": None,
        "repair_contract": "Add executable validation before the release-candidate row can be treated as fixture-validated.",
        "next_action": "Patch validator registry, validators.py, CLI, and focused pytest together.",
    },
    {
        "case_id": "case.root_leaf_boundary_conflation",
        "diagnostic_family": "architecture_boundary",
        "synthetic_input": "A leaf README claims it can replace the root registry, validators, and release package gates.",
        "expected_contract": "Leaves prove one organ; the root composes leaves and owns cross-leaf strengthening.",
        "observed_artifact": "The leaf carries local evidence but implies root-level package readiness.",
        "diagnostic_status": "fail",
        "owner_surface": "microcosms/leaf_entry_contract.json",
        "repair_route": "separate_leaf_organ_from_root_composition_before_public_claim",
        "speed_signal": None,
        "context_fit_signal": None,
        "test_signal": None,
        "architecture_signal": {
            "source": "synthetic_fixture",
            "root_surface": "registry/release_candidates.json",
            "leaf_surface": "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
            "boundary_preserved": False,
            "root_composition_required": True,
        },
        "standalone_signal": None,
        "repair_contract": "Keep local diagnostic status inside the leaf and route cross-leaf claim changes to root gates.",
        "next_action": "Bind the leaf to clone_posture=root_clone_supported until an export wrapper carries its local standards subset.",
    },
    {
        "case_id": "case.standalone_wrapper_gap",
        "diagnostic_family": "standalone_wrapper",
        "synthetic_input": "Export only the leaf folder and expect a standalone repo to validate itself.",
        "expected_contract": "Standalone leaves need a wrapper projection carrying README, standards subset, fixtures, validator or probe, receipt, and CLI path.",
        "observed_artifact": "The exported folder has the board and receipt, but no local validator registry or CLI wrapper.",
        "diagnostic_status": "block",
        "owner_surface": "skills/leaf_porting.md",
        "repair_route": "build_leaf_export_wrapper_before_standalone_subrepo_claim",
        "speed_signal": None,
        "context_fit_signal": None,
        "test_signal": None,
        "architecture_signal": {
            "source": "synthetic_fixture",
            "root_surface": "self-indexing-cognitive-substrate/",
            "leaf_surface": "microcosms/meta_diagnostics_workbench/",
            "boundary_preserved": True,
            "root_composition_required": True,
        },
        "standalone_signal": {
            "source": "synthetic_fixture",
            "standalone_leaf_supported": False,
            "wrapper_projection_required": True,
            "required_wrapper_parts": [
                "README",
                "local standards subset",
                "fixture board",
                "validator or probe",
                "receipt",
                "CLI path",
            ],
        },
        "repair_contract": "Generate a wrapper projection before treating the leaf folder as an independent public repo.",
        "next_action": "Use this row as the acceptance contract for a future leaf export wrapper.",
    },
)


AUTHORITY_TRACE: tuple[dict[str, Any], ...] = (
    {
        "node_id": "synthetic_diagnostic_case",
        "authority_role": "describes_public_safe_meta_diagnostic_fixture",
        "status_authority": False,
    },
    {
        "node_id": "route_or_budget_signal",
        "authority_role": "provides_fixture_observation_not_live_performance_truth",
        "status_authority": False,
    },
    {
        "node_id": "meta_diagnostic_evaluator",
        "authority_role": "classifies_diagnostic_status_repair_route_and_boundary",
        "status_authority": True,
    },
    {
        "node_id": "receipt_gate",
        "authority_role": "records_fixture_result_and_public_boundary",
        "status_authority": True,
    },
)


DOGFOOD_PREFLIGHT: tuple[dict[str, Any], ...] = (
    {
        "step_id": "select_meta_diagnostics_leaf",
        "scope": "root_route",
        "surface": "microcosms/leaf_entry_contract.json",
        "command": None,
        "authority": "route_selection_only",
        "checks": [
            "leaf exists in the root leaf contract",
            "first surface and evidence surface resolve",
            "root clone support is distinct from standalone leaf export support",
        ],
        "blocks_claims": [
            "leaf folder alone is standalone",
            "leaf fixture proves root package health",
        ],
    },
    {
        "step_id": "build_fixture_board",
        "scope": "leaf_fixture",
        "surface": "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
        "command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-meta-diagnostics-workbench-specimen --root . --write-receipt",
        "authority": "writes_synthetic_fixture_and_receipt",
        "checks": [
            "command-speed and command wait-tax rows stay synthetic",
            "context-fit rows route to leaf contract or self-comprehension navigator before source spans",
            "standalone wrapper remains diagnosed as missing",
        ],
        "blocks_claims": [
            "live command speed certified",
            "private command telemetry imported",
            "standalone wrapper shipped",
        ],
    },
    {
        "step_id": "validate_root_composition",
        "scope": "root_gate",
        "surface": "registry/validators.json",
        "command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        "authority": "root_validator_gate",
        "checks": [
            "validator.meta_diagnostics_workbench_specimen passes",
            "receipt refs resolve",
            "anti-claims and fail-closed boundaries remain present",
        ],
        "blocks_claims": [
            "leaf-local pass bypasses root validator",
            "registry claim strengthens without validator proof",
        ],
    },
    {
        "step_id": "run_focused_regression",
        "scope": "test_gate",
        "surface": "tests/test_microcosm_contract.py",
        "command": "python -m pytest tests/test_microcosm_contract.py -q -k meta_diagnostics",
        "authority": "focused_regression_test",
        "checks": [
            "dogfood preflight rows are present",
            "root/leaf split contract stays fail-closed",
            "command-speed and publication counts remain zero",
        ],
        "blocks_claims": [
            "fixture-valid without regression coverage",
            "diagnostic board can drop dogfood route",
        ],
    },
)


COMMAND_LATENCY_INVENTORY: tuple[dict[str, Any], ...] = (
    {
        "rank": 1,
        "command_id": "cmd.focused_pytest_duplicate_wait_tax",
        "command_key": "pytest:tests/test_microcosm_contract.py::test_meta_diagnostics_workbench_specimen_routes_meta_failures_without_authority_collapse",
        "command_family": "focused_pytest",
        "observed_ms": 38000,
        "threshold_ms": 5000,
        "wait_tax_ms": 33000,
        "within_budget": False,
        "concurrency_policy": "attach_or_reuse_active_command_key",
        "owner_surface": "microcosms/concurrency_mission_control/mission_board.json",
        "repair_route": "claim_command_key_then_attach_or_reuse_focused_validation_before_spawning_duplicate_run",
        "source": "synthetic_fixture",
        "certifies_live_performance": False,
        "imports_private_telemetry": False,
    },
    {
        "rank": 2,
        "command_id": "cmd.root_microcosm_validate",
        "command_key": "validate:idea_microcosm_root",
        "command_family": "microcosm_validate",
        "observed_ms": 4200,
        "threshold_ms": 10000,
        "wait_tax_ms": 0,
        "within_budget": True,
        "concurrency_policy": "reuse_fresh_receipt_before_full_rerun",
        "owner_surface": "src/idea_microcosm/validators.py",
        "repair_route": "use_focused_validator_or_fresh_receipt_before_full_root_validate",
        "source": "synthetic_fixture",
        "certifies_live_performance": False,
        "imports_private_telemetry": False,
    },
    {
        "rank": 3,
        "command_id": "cmd.meta_diagnostics_fixture_build",
        "command_key": "build:meta_diagnostics_workbench_specimen",
        "command_family": "microcosm_fixture_build",
        "observed_ms": 140,
        "threshold_ms": 2500,
        "wait_tax_ms": 0,
        "within_budget": True,
        "concurrency_policy": "normal_focused_run",
        "owner_surface": "src/idea_microcosm/meta_diagnostics_workbench_specimen.py",
        "repair_route": "keep_fixture_budget_row_and_repeat_with_real_receipt_before_any_performance_claim",
        "source": "synthetic_fixture",
        "certifies_live_performance": False,
        "imports_private_telemetry": False,
    },
)


FAST_VALIDATION_PLAN_RULES: tuple[dict[str, Any], ...] = (
    {
        "rule_id": "fast_validation.meta_diagnostics_owner",
        "match_path_prefixes": [
            "src/idea_microcosm/meta_diagnostics_workbench_specimen.py",
            "microcosms/meta_diagnostics_workbench/",
        ],
        "primary_command": (
            "python -m pytest tests/test_microcosm_contract.py::"
            "test_meta_diagnostics_workbench_specimen_routes_meta_failures_without_authority_collapse -q"
        ),
        "command_key": (
            "pytest:tests/test_microcosm_contract.py::"
            "test_meta_diagnostics_workbench_specimen_routes_meta_failures_without_authority_collapse"
        ),
        "command_family": "focused_pytest",
        "estimated_cost_tier": "focused_fast",
        "concurrency_policy": "attach_or_reuse_active_command_key",
        "why": "Meta diagnostics source or board changed; run the owner fixture test before paying root validation.",
        "fallback_command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        "fallback_policy": "run_after_focused_pass_or_when_validator_code_changed",
        "authority_boundary": "Selection rule is a public-safe fixture planner, not live test timing telemetry.",
    },
    {
        "rule_id": "fast_validation.command_latency_query",
        "match_path_prefixes": ["src/idea_microcosm/cli.py"],
        "match_tokens": ["query_command_latency_inventory", "query-command-latency-inventory"],
        "primary_command": (
            "python -m pytest tests/test_microcosm_contract.py::"
            "test_command_latency_inventory_query_surface_returns_ranked_rows -q"
        ),
        "command_key": "pytest:tests/test_microcosm_contract.py::test_command_latency_inventory_query_surface_returns_ranked_rows",
        "command_family": "focused_pytest",
        "estimated_cost_tier": "focused_fast",
        "concurrency_policy": "attach_or_reuse_active_command_key",
        "why": "Latency query surface changed; run its direct contract test before broader CLI checks.",
        "fallback_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-latency-inventory --root . --slow-only --limit 2",
        "fallback_policy": "use_direct_query_as_a_subsecond_shape_check",
        "authority_boundary": "Selection rule is a public-safe fixture planner, not live test timing telemetry.",
    },
    {
        "rule_id": "fast_validation.command_concurrency_query",
        "match_path_prefixes": ["src/idea_microcosm/cli.py"],
        "match_tokens": ["query_command_concurrency", "query-command-concurrency"],
        "primary_command": (
            "python -m pytest tests/test_microcosm_contract.py::"
            "test_command_concurrency_query_joins_duplicate_blocks_to_latency_inventory -q"
        ),
        "command_key": (
            "pytest:tests/test_microcosm_contract.py::"
            "test_command_concurrency_query_joins_duplicate_blocks_to_latency_inventory"
        ),
        "command_family": "focused_pytest",
        "estimated_cost_tier": "focused_fast",
        "concurrency_policy": "attach_or_reuse_active_command_key",
        "why": "Command concurrency query changed; run its joined latency/concurrency contract before root validation.",
        "fallback_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-concurrency --root . --duplicates-only --limit 2",
        "fallback_policy": "use_direct_concurrency_query_as_a_subsecond_shape_check",
        "authority_boundary": "Selection rule is a public-safe fixture planner, not live test timing telemetry.",
    },
    {
        "rule_id": "fast_validation.concurrency_mission_control",
        "match_path_prefixes": [
            "src/idea_microcosm/concurrency_mission_control_specimen.py",
            "microcosms/concurrency_mission_control/",
        ],
        "primary_command": (
            "python -m pytest tests/test_microcosm_contract.py::"
            "test_concurrency_transaction_mission_control_specimen_blocks_overlap_and_stale_work -q"
        ),
        "command_key": (
            "pytest:tests/test_microcosm_contract.py::"
            "test_concurrency_transaction_mission_control_specimen_blocks_overlap_and_stale_work"
        ),
        "command_family": "focused_pytest",
        "estimated_cost_tier": "focused_medium",
        "concurrency_policy": "attach_or_reuse_active_command_key",
        "why": "Concurrency owner changed; validate duplicate command and overlap gates before root validation.",
        "fallback_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
        "fallback_policy": "use_builder_when fixture artifacts need refresh",
        "authority_boundary": "Selection rule is a public-safe fixture planner, not live test timing telemetry.",
    },
    {
        "rule_id": "fast_validation.root_validator_owner",
        "match_path_prefixes": ["src/idea_microcosm/validators.py"],
        "primary_command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        "command_key": "validate:idea_microcosm_root",
        "command_family": "microcosm_validate",
        "estimated_cost_tier": "root_validator",
        "concurrency_policy": "reuse_fresh_receipt_before_full_rerun",
        "why": "Validator logic changed; full root validation is the owner command, but fresh receipts should be reused before duplicate reruns.",
        "fallback_command": "python -m pytest tests/test_microcosm_contract.py::test_validator_passes -q",
        "fallback_policy": "use_pytest_wrapper_when CLI validation needs pytest integration coverage",
        "authority_boundary": "Selection rule is a public-safe fixture planner, not live test timing telemetry.",
    },
)


COMMAND_SPEEDBOARD: dict[str, Any] = {
    "schema_version": "meta_diagnostics_command_speedboard_v0",
    "status": "fixture_ready",
    "source": "synthetic_join_over_latency_inventory_concurrency_owner_and_fast_validation_rules",
    "purpose": (
        "Give a cold standalone-root agent one command-speed control board before it launches "
        "duplicate focused tests or pays root validation."
    ),
    "joins": {
        "latency_inventory_ref": "microcosms/meta_diagnostics_workbench/diagnostic_board.json::command_latency_inventory",
        "concurrency_owner_ref": "microcosms/concurrency_mission_control/mission_board.json",
        "fast_validation_planner_ref": "microcosms/meta_diagnostics_workbench/diagnostic_board.json::fast_validation_planner",
    },
    "summary": {
        "lane_count": len(COMMAND_LATENCY_INVENTORY),
        "slow_lane_count": sum(1 for row in COMMAND_LATENCY_INVENTORY if row["within_budget"] is False),
        "duplicate_wait_tax_lane_count": sum(1 for row in COMMAND_LATENCY_INVENTORY if row["wait_tax_ms"] > 0),
        "focused_rule_count": sum(
            1 for row in FAST_VALIDATION_PLAN_RULES if row["command_family"] == "focused_pytest"
        ),
        "root_validate_deferred_rule_count": sum(
            1 for row in FAST_VALIDATION_PLAN_RULES if row["command_family"] != "microcosm_validate"
        ),
        "max_observed_ms": max(row["observed_ms"] for row in COMMAND_LATENCY_INVENTORY),
        "max_wait_tax_ms": max(row["wait_tax_ms"] for row in COMMAND_LATENCY_INVENTORY),
        "private_telemetry_count": sum(
            1 for row in COMMAND_LATENCY_INVENTORY if row["imports_private_telemetry"] is True
        ),
        "live_performance_certification_count": sum(
            1 for row in COMMAND_LATENCY_INVENTORY if row["certifies_live_performance"] is True
        ),
    },
    "next_query_order": [
        {
            "surface": "command_latency_inventory",
            "command": (
                "PYTHONPATH=src python3 -m idea_microcosm.cli "
                "query-command-latency-inventory --root . --slow-only --limit 5"
            ),
            "why": "Pick the highest wait-tax or slowest fixture command before running another validator.",
        },
        {
            "surface": "command_concurrency",
            "command": (
                "PYTHONPATH=src python3 -m idea_microcosm.cli "
                "query-command-concurrency --root . --duplicates-only --limit 5"
            ),
            "why": "Check whether the same command key should attach or reuse before spawning a duplicate run.",
        },
        {
            "surface": "fast_validation_plan",
            "command": (
                "PYTHONPATH=src python3 -m idea_microcosm.cli "
                "plan-fast-validation --root . --path <changed-path>"
            ),
            "why": "Select focused commands first and defer root validation unless the owner path requires it.",
        },
    ],
    "lanes": [
        {
            "command_key": row["command_key"],
            "command_family": row["command_family"],
            "observed_ms": row["observed_ms"],
            "threshold_ms": row["threshold_ms"],
            "wait_tax_ms": row["wait_tax_ms"],
            "within_budget": row["within_budget"],
            "owner_surface": row["owner_surface"],
            "concurrency_policy": row["concurrency_policy"],
            "planner_rule_ids": [
                rule["rule_id"]
                for rule in FAST_VALIDATION_PLAN_RULES
                if rule["command_key"] == row["command_key"]
            ],
            "speedboard_status": "attach_or_reuse_before_rerun"
            if row["wait_tax_ms"] > 0
            else "focused_or_receipt_reuse_before_root_validate",
        }
        for row in COMMAND_LATENCY_INVENTORY
    ],
    "authority_boundary": (
        "Speedboard joins public-safe fixture rows only. It is not live timing telemetry, "
        "private session telemetry, hosted CI proof, benchmark evidence, or performance certification."
    ),
    "anti_claims": [
        "speedboard contains live private telemetry",
        "speedboard certifies command performance",
        "speedboard proves hosted CI speed",
        "speedboard grants publication readiness",
    ],
}


DIAGNOSTIC_EXECUTION_LADDER: dict[str, Any] = {
    "schema_version": "meta_diagnostics_execution_ladder_v0",
    "status": "fixture_ready",
    "policy": "selected_lens_and_leaf_smoke_before_root_wide_validation",
    "purpose": "Keep the standalone microcosm fast by making cheap/focused diagnostics the default, while preserving explicit escalation to root and private adapter evidence.",
    "tiers": [
        {
            "tier_id": "leaf_smoke",
            "scope": "leaf_fixture",
            "command": (
                "PYTHONPATH=src python3 -m idea_microcosm.cli "
                "build-meta-diagnostics-workbench-specimen --root . --write-receipt"
            ),
            "command_key": "build:meta_diagnostics_workbench_specimen",
            "synthetic_budget_ms": 2500,
            "context_budget_tokens": 4000,
            "runs_by_default": True,
            "standalone_safe": True,
            "private_root_only": False,
            "escalates_to": "focused_owner_regression",
            "escalate_when": [
                "fixture status is not ok",
                "receipt missing",
                "zero-export counters nonzero",
                "changed path is covered by fast_validation_planner",
            ],
        },
        {
            "tier_id": "focused_owner_regression",
            "scope": "focused_test_gate",
            "command": "python -m pytest tests/test_meta_diagnostics_workbench.py -q",
            "command_key": "pytest:tests/test_meta_diagnostics_workbench.py",
            "synthetic_budget_ms": 5000,
            "context_budget_tokens": 6000,
            "runs_by_default": True,
            "standalone_safe": True,
            "private_root_only": False,
            "escalates_to": "root_composition_validate",
            "escalate_when": [
                "focused test fails",
                "validator source changed",
                "registry source changed",
                "root-owned surface changed",
            ],
        },
        {
            "tier_id": "root_composition_validate",
            "scope": "release_root",
            "command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "command_key": "validate:idea_microcosm_root",
            "synthetic_budget_ms": 10000,
            "context_budget_tokens": 12000,
            "runs_by_default": False,
            "standalone_safe": True,
            "private_root_only": False,
            "escalates_to": "private_root_adapter_summary",
            "escalate_when": [
                "root validation fails",
                "route miss requires private root diagnosis",
                "agent path dashboard source shape changed",
            ],
        },
        {
            "tier_id": "private_root_adapter_summary",
            "scope": "private_root_adapter",
            "command": "./repo-python kernel.py --session-diagnostics --lens all --last 10 --store both --json --diagnostics-summary",
            "command_key": "private:session_diagnostics_summary",
            "synthetic_budget_ms": 7000,
            "context_budget_tokens": 8000,
            "runs_by_default": False,
            "standalone_safe": False,
            "private_root_only": True,
            "escalates_to": None,
            "escalate_when": [],
            "projection_rule": "private_root_summary_may_project_counts_and_route_obligations_only",
        },
    ],
    "escalation_guards": {
        "full_root_validate_before_focus_allowed": False,
        "all_lens_session_diagnostics_before_summary_allowed": False,
        "private_adapter_allowed_in_standalone": False,
        "duplicate_command_spawn_allowed_without_attach_or_reuse": False,
    },
    "zero_export_counters": {
        "private_adapter_raw_body_export_count": 0,
        "private_adapter_prompt_export_count": 0,
        "private_adapter_hidden_reasoning_export_count": 0,
        "standalone_private_route_dependency_count": 0,
    },
}


CONTEXT_FIT_COMPRESSION_GATE: dict[str, Any] = {
    "schema_version": "meta_diagnostics_context_fit_compression_gate_v0",
    "status": "fixture_ready",
    "policy": "selected_lens_summary_before_full_trace_payload",
    "purpose": "Keep meta-diagnostic dogfood under a cold-agent context budget by selecting the smallest adequate lens before opening all session-diagnostic evidence.",
    "source_shape": {
        "source": "public_safe_summary_shape_modeled_on_agent_session_diagnostics",
        "selected_lens": "latency",
        "selected_lens_count": 1,
        "selected_lens_adequacy": "single_lens_sufficient",
        "selection_reason": "Context pressure is active; inspect selected-lens rows before full all-lens JSON.",
        "summary_estimated_bytes": 6296,
        "full_report_estimated_bytes": 21856,
        "byte_reduction_percent": 71.2,
        "raw_report_export_allowed": False,
        "raw_session_body_export_allowed": False,
        "private_prompt_export_allowed": False,
    },
    "gate_steps": [
        {
            "step_id": "summary_first_scan",
            "scope": "private_root_adapter_or_local_fixture",
            "command": "./repo-python kernel.py --session-diagnostics --lens all --last 10 --store both --json --diagnostics-summary",
            "runs_by_default": True,
            "standalone_safe": False,
            "public_projection": "summary counts, selected lens id, byte-reduction ratio, route obligations, and zero-export counters only",
            "next_step": "selected_lens_drilldown",
        },
        {
            "step_id": "selected_lens_drilldown",
            "scope": "focused_context_fit",
            "command": "./repo-python kernel.py --session-diagnostics --lens latency --last 10 --store both --json",
            "runs_by_default": True,
            "standalone_safe": False,
            "public_projection": "synthetic lens adequacy row and repair route only",
            "next_step": "leaf_receipt_check",
        },
        {
            "step_id": "leaf_receipt_check",
            "scope": "standalone_leaf_fixture",
            "command": "read microcosms/meta_diagnostics_workbench/receipt.json",
            "runs_by_default": True,
            "standalone_safe": True,
            "public_projection": "leaf receipt counters and anti-claims",
            "next_step": "full_report_fallback",
        },
        {
            "step_id": "full_report_fallback",
            "scope": "private_root_adapter",
            "command": "./repo-python kernel.py --session-diagnostics --lens all --last 30 --store both --json",
            "runs_by_default": False,
            "standalone_safe": False,
            "public_projection": "none until reduced through summary-first gate",
            "next_step": None,
        },
    ],
    "escalate_to_full_report_when": [
        "summary reports selected_lens_adequacy below sufficient",
        "selected lens lacks a repair route",
        "owned path cannot be classified from summary and leaf receipt",
        "route miss requires private-root trace-to-git handoff evidence",
    ],
    "standalone_contract": {
        "mode": "local_fixture_or_empty_snapshot",
        "may_consume": [
            "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
            "microcosms/meta_diagnostics_workbench/receipt.json",
            "tests/test_meta_diagnostics_workbench.py",
        ],
        "must_not_require": [
            ".codex session store",
            "private root Work Ledger",
            "raw prompts",
            "raw session bodies",
            "hidden reasoning",
        ],
        "private_root_dependency_count": 0,
    },
    "zero_export_counters": {
        "full_report_raw_body_export_count": 0,
        "selected_lens_raw_body_export_count": 0,
        "private_prompt_export_count": 0,
        "hidden_reasoning_export_count": 0,
        "private_path_export_count": 0,
    },
}


AGENT_PATH_DIAGNOSTIC_DASHBOARD: dict[str, Any] = {
    "status": "fixture_ready",
    "source": "synthetic_fixture_modeled_on_agent_session_diagnostics_shape",
    "private_root_route": "./repo-python kernel.py --session-diagnostics --lens all --last 30 --store both --json",
    "authority_boundary": "Dashboard carries public-safe diagnostic shape only; no raw prompts, raw session bodies, hidden reasoning, private paths, or live telemetry are exported.",
    "trace_to_git_handoff": {
        "status": "required_before_status_promotion",
        "edge_order": [
            "agent_trace",
            "claimed_intent",
            "head_and_dirty_tree",
            "owner_path",
            "commands_run",
            "validation",
            "task_work_ledger_disposition",
            "commit_or_failed_landing",
        ],
        "promotion_rule": "A trace symptom cannot become substrate truth until owned paths, validation, and ledger disposition confirm it.",
    },
    "behavior_fitness_signals": [
        {
            "signal_id": "ladder_skip_ratio",
            "kind": "navigation_behavior",
            "synthetic_value": 0.361,
            "healthy_direction": "down",
            "repair_surface": "microcosms/self_comprehension_navigator/navigator_board.json",
            "public_safe": True,
        },
        {
            "signal_id": "grep_before_nav_count",
            "kind": "navigation_behavior",
            "synthetic_value": 2,
            "healthy_direction": "down",
            "repair_surface": "navigation/entry_packet.json",
            "public_safe": True,
        },
        {
            "signal_id": "route_miss_candidate_count",
            "kind": "route_surface_fit",
            "synthetic_value": 4,
            "healthy_direction": "down",
            "repair_surface": "navigation/microcosm_index.json",
            "public_safe": True,
        },
        {
            "signal_id": "session_scan_wall_ms",
            "kind": "command_speed_shape",
            "synthetic_value": 6589,
            "healthy_direction": "down",
            "repair_surface": "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
            "public_safe": True,
        },
    ],
    "standalone_port_contract": {
        "root_mode": "consume_private_root_route_then_project_synthetic_counts",
        "standalone_mode": "consume_local_agent_event_fixture_or_empty_snapshot",
        "requires_raw_session_export": False,
        "requires_private_prompt_export": False,
        "requires_hidden_reasoning": False,
    },
    "anti_claims": [
        "session dashboard contains raw prompts",
        "session dashboard contains hidden reasoning",
        "session dashboard certifies live command latency",
        "session dashboard proves private-root equivalence",
    ],
}


STANDALONE_SPLIT_CONTRACT: dict[str, Any] = {
    "status": "root_clone_supported_leaf_subrepo_not_supported",
    "root_clone_supported": True,
    "leaf_folder_export_supported": False,
    "wrapper_gap_status": "diagnosed_not_solved",
    "root_owned_surfaces": [
        "README.md",
        "AGENTS.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/cli.py",
        "src/idea_microcosm/validators.py",
        "tests/test_microcosm_contract.py",
    ],
    "leaf_owned_surfaces": [
        "microcosms/meta_diagnostics_workbench/README.md",
        "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
        "microcosms/meta_diagnostics_workbench/receipt.json",
    ],
    "wrapper_required_parts": [
        "README",
        "local standards subset",
        "fixture board",
        "validator or probe",
        "receipt",
        "CLI path",
    ],
    "forbidden_promotions": [
        "leaf_validated_to_root_package_ready",
        "root_clone_supported_to_leaf_subrepo_supported",
        "fixture_latency_to_live_command_speed_certified",
        "local_validate_to_hosted_public_available",
    ],
}


PORTABILITY_AUTHORITY_MATRIX: dict[str, Any] = {
    "schema_version": "meta_diagnostics_portability_authority_matrix_v0",
    "status": "fixture_ready",
    "purpose": "Separate private-root diagnostic adapters, release-root clone diagnostics, and leaf-only export posture before any standalone claim strengthens.",
    "modes": [
        {
            "mode_id": "private_root_adapter",
            "scope": "private_root_only",
            "standalone_safe": False,
            "may_consume": [
                "./repo-python kernel.py --session-diagnostics --lens all --last 30 --store both --json",
                "./repo-python kernel.py --navigation-metabolism \"<task>\" --metabolism-profile quick --context-budget 12000",
                "./repo-python tools/meta/factory/work_ledger.py session-status --overview",
                "./repo-python tools/meta/control/git_state_snapshot.py --compact",
            ],
            "may_project": [
                "synthetic signal ids",
                "route obligations",
                "zero-export counters",
                "anti-claims",
                "fixture timing bands",
            ],
            "must_not_export": [
                "raw session bodies",
                "raw prompts",
                "hidden reasoning",
                "private root paths",
                "live command logs",
                "private Work Ledger session cards",
            ],
            "promotion_gate": "private_root_evidence_must_be_reduced_to_public_safe_fixture_shape_before_release_root_consumption",
        },
        {
            "mode_id": "release_root_clone",
            "scope": "self_indexing_cognitive_substrate_root",
            "standalone_safe": True,
            "may_consume": [
                "registry/release_candidates.json",
                "registry/validators.json",
                "src/idea_microcosm/validators.py",
                "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
                "microcosms/meta_diagnostics_workbench/receipt.json",
            ],
            "may_project": [
                "fixture board",
                "receipt",
                "README route",
                "focused regression expectation",
                "root composition status",
            ],
            "must_not_export": [
                "private root adapters",
                "private telemetry",
                "hosted availability claim",
                "publication approval",
            ],
            "promotion_gate": "root_validate_and_focused_test_must_pass_before_release_root_claim_strengthens",
        },
        {
            "mode_id": "leaf_subrepo_fixture",
            "scope": "microcosms/meta_diagnostics_workbench_only",
            "standalone_safe": False,
            "may_consume": [
                "local diagnostic_board.json",
                "local receipt.json",
                "local README.md",
            ],
            "may_project": [
                "leaf-local diagnostic posture",
                "wrapper gap diagnosis",
                "required wrapper parts",
            ],
            "must_not_export": [
                "root validator authority",
                "root registry authority",
                "CLI package authority",
                "leaf folder alone is standalone",
            ],
            "promotion_gate": "leaf_subrepo_requires_wrapper_projection_with_standards_subset_validator_or_probe_receipt_readme_and_cli_path",
        },
    ],
    "zero_export_counters": {
        "raw_session_body_export_count": 0,
        "raw_prompt_export_count": 0,
        "hidden_reasoning_export_count": 0,
        "private_path_export_count": 0,
        "live_command_log_export_count": 0,
        "private_work_ledger_card_export_count": 0,
    },
    "fail_closed_if_missing": [
        "release root validator",
        "focused regression",
        "receipt",
        "standards subset",
        "CLI path",
        "zero-export counter check",
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _decision_reason(case: dict[str, Any]) -> str:
    if case["diagnostic_status"] == "pass":
        return "Synthetic control row stays within its fixture budget without claiming live command speed."
    return f"Fixture localizes the {case['diagnostic_family']} issue to {case['owner_surface']} and routes repair through {case['repair_route']}."


def _case_result(case: dict[str, Any]) -> dict[str, Any]:
    diagnostic_status = str(case["diagnostic_status"])
    repair_row = None
    if diagnostic_status in {"block", "fail"}:
        repair_row = {
            "diagnostic_family": case["diagnostic_family"],
            "owner_surface": case["owner_surface"],
            "repair_route": case["repair_route"],
            "repair_contract": case["repair_contract"],
            "next_action": case["next_action"],
        }
    return {
        "case_id": case["case_id"],
        "diagnostic_family": case["diagnostic_family"],
        "synthetic_input": case["synthetic_input"],
        "expected_contract": case["expected_contract"],
        "observed_artifact": case["observed_artifact"],
        "diagnostic_status": diagnostic_status,
        "owner_surface": case["owner_surface"],
        "repair_route": case["repair_route"],
        "speed_signal": case["speed_signal"],
        "context_fit_signal": case["context_fit_signal"],
        "test_signal": case["test_signal"],
        "architecture_signal": case["architecture_signal"],
        "standalone_signal": case["standalone_signal"],
        "repair_row": repair_row,
        "evaluator_decision": {
            "evaluator_status": diagnostic_status,
            "reason": _decision_reason(case),
            "status_authority": "meta_diagnostic_evaluator_only",
            "private_context_used": False,
            "command_speed_certified": False,
            "publication_claimed": False,
            "private_root_equivalence_claimed": False,
            "standalone_wrapper_claimed": False,
        },
    }


def _readme() -> str:
    return "\n".join(
        [
            "# Meta Diagnostics Workbench",
            "",
            "This specimen is a public-safe synthetic diagnostic board for the release microcosm itself.",
            "It checks command-speed shape, command wait-tax routing, context fit, focused tests, root/leaf architecture boundaries, and standalone wrapper readiness.",
            "",
            "It is not command-speed certification, not live latency telemetry, not private-root context-fit proof, not a standalone wrapper, and not publication approval.",
            "",
            "Run it from the release root:",
            "",
            "```bash",
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-meta-diagnostics-workbench-specimen --root . --write-receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "```",
            "",
            "The fixture is intentionally synthetic. It never imports private command logs, live kernel timings, private context packs, provider traces, hosted status, or private root paths.",
            "The command wait-tax row ports the broader latency-seed and singleflight pattern into the microcosm as public-safe fixture evidence only.",
            "The command latency inventory ranks public-safe synthetic command shapes by observed fixture milliseconds and points slow duplicate runs at the concurrency mission-control owner.",
            "The command speedboard joins latency inventory, command-concurrency owner route, and fast-validation planner state so agents can choose attach/reuse/focused checks before root validation.",
            "The diagnostic execution ladder runs leaf smoke and focused owner checks before root-wide validation, and keeps private-root adapter diagnostics summary-only.",
            "The context-fit compression gate uses selected-lens summaries before full session traces, then projects only public-safe counts and route obligations into the leaf.",
            "The fast validation planner maps touched microcosm paths to focused commands first, then defers full root validation unless validator ownership requires it.",
            "The agent-path dashboard carries the shape of session diagnostics as counts and route obligations only; it does not export raw prompts, raw sessions, or private trace bodies.",
            "The portability authority matrix separates private-root adapters, release-root clone diagnostics, and leaf-only export posture so the standalone story cannot silently inherit root-only authority.",
            "",
            "Dogfood preflight sequence:",
            "",
            "```bash",
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-meta-diagnostics-workbench-specimen --root . --write-receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "python -m pytest tests/test_microcosm_contract.py -q -k meta_diagnostics",
            "```",
            "",
            "The root composes leaves. This leaf can diagnose whether a future standalone wrapper is missing, but direct leaf-folder export is blocked until the wrapper carries the README, standards subset, fixtures, validator or probe, receipt, and CLI path.",
            "",
        ]
    )


def build_meta_diagnostics_workbench_specimen(
    root: Path,
    *,
    output_path: str = DEFAULT_OUTPUT_PATH,
    receipt_path: str = DEFAULT_RECEIPT_PATH,
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or _utc_now()
    cases = [_case_result(case) for case in FIXTURE_CASES]
    failures: list[dict[str, Any]] = []

    repair_cases = [case for case in cases if case["diagnostic_status"] in {"block", "fail"}]
    pass_cases = [case for case in cases if case["diagnostic_status"] == "pass"]
    diagnostic_families = {case["diagnostic_family"] for case in cases}
    if len(cases) < 7:
        failures.append({"reason": "fixture must include at least seven meta diagnostic cases"})
    if len(diagnostic_families) < 6:
        failures.append({"reason": "fixture must cover command_speed, command_wait_tax, context_fit, test_coverage, architecture_boundary, and standalone_wrapper"})
    if len(repair_cases) < 6:
        failures.append({"reason": "fixture must include at least six blocked or failed repair rows"})
    if not pass_cases:
        failures.append({"reason": "fixture must include one synthetic command-speed control pass"})
    if any(case["evaluator_decision"]["private_context_used"] for case in cases):
        failures.append({"reason": "diagnostic fixture must not use private context"})
    if any(case["evaluator_decision"]["command_speed_certified"] for case in cases):
        failures.append({"reason": "diagnostic fixture must not certify live command speed"})
    if any(case["evaluator_decision"]["publication_claimed"] for case in cases):
        failures.append({"reason": "diagnostic fixture must not claim publication approval"})
    if any(case["evaluator_decision"]["standalone_wrapper_claimed"] for case in cases):
        failures.append({"reason": "diagnostic fixture must not claim the standalone wrapper is shipped"})

    status = "ok" if not failures else "failed"
    summary = {
        "case_count": len(cases),
        "pass_count": len(pass_cases),
        "repair_row_count": len(repair_cases),
        "diagnostic_family_count": len(diagnostic_families),
        "command_speed_certification_count": 0,
        "command_wait_tax_case_count": sum(1 for case in cases if case["diagnostic_family"] == "command_wait_tax"),
        "latency_seed_transfer_case_count": sum(
            1
            for case in cases
            if isinstance(case.get("speed_signal"), dict) and case["speed_signal"].get("latency_seed_transfer") is True
        ),
        "live_performance_certification_count": 0,
        "private_telemetry_dependency_count": 0,
        "private_context_dependency_count": 0,
        "publication_claim_count": 0,
        "private_root_equivalence_claim_count": 0,
        "standalone_leaf_supported_count": 0,
        "standalone_wrapper_target_count": sum(1 for case in cases if case.get("standalone_signal")),
        "root_leaf_boundary_case_count": sum(1 for case in cases if case.get("architecture_signal")),
        "dogfood_preflight_step_count": len(DOGFOOD_PREFLIGHT),
        "command_latency_inventory_count": len(COMMAND_LATENCY_INVENTORY),
        "command_speedboard_count": 1,
        "command_speedboard_lane_count": COMMAND_SPEEDBOARD["summary"]["lane_count"],
        "command_speedboard_duplicate_wait_tax_lane_count": COMMAND_SPEEDBOARD["summary"][
            "duplicate_wait_tax_lane_count"
        ],
        "command_speedboard_private_telemetry_count": COMMAND_SPEEDBOARD["summary"]["private_telemetry_count"],
        "command_speedboard_live_performance_certification_count": COMMAND_SPEEDBOARD["summary"][
            "live_performance_certification_count"
        ],
        "diagnostic_execution_tier_count": len(DIAGNOSTIC_EXECUTION_LADDER["tiers"]),
        "diagnostic_execution_default_tier_count": sum(
            1 for row in DIAGNOSTIC_EXECUTION_LADDER["tiers"] if row["runs_by_default"] is True
        ),
        "diagnostic_execution_private_root_tier_count": sum(
            1 for row in DIAGNOSTIC_EXECUTION_LADDER["tiers"] if row["private_root_only"] is True
        ),
        "diagnostic_execution_standalone_safe_tier_count": sum(
            1 for row in DIAGNOSTIC_EXECUTION_LADDER["tiers"] if row["standalone_safe"] is True
        ),
        "diagnostic_execution_nonzero_zero_export_counter_count": sum(
            1 for value in DIAGNOSTIC_EXECUTION_LADDER["zero_export_counters"].values() if value != 0
        ),
        "context_fit_compression_gate_count": 1,
        "context_fit_gate_step_count": len(CONTEXT_FIT_COMPRESSION_GATE["gate_steps"]),
        "context_fit_gate_default_step_count": sum(
            1 for row in CONTEXT_FIT_COMPRESSION_GATE["gate_steps"] if row["runs_by_default"] is True
        ),
        "context_fit_gate_standalone_safe_step_count": sum(
            1 for row in CONTEXT_FIT_COMPRESSION_GATE["gate_steps"] if row["standalone_safe"] is True
        ),
        "context_fit_full_report_default_count": sum(
            1
            for row in CONTEXT_FIT_COMPRESSION_GATE["gate_steps"]
            if row["step_id"] == "full_report_fallback" and row["runs_by_default"] is True
        ),
        "context_fit_summary_byte_reduction_percent": CONTEXT_FIT_COMPRESSION_GATE["source_shape"][
            "byte_reduction_percent"
        ],
        "context_fit_nonzero_zero_export_counter_count": sum(
            1 for value in CONTEXT_FIT_COMPRESSION_GATE["zero_export_counters"].values() if value != 0
        ),
        "fast_validation_rule_count": len(FAST_VALIDATION_PLAN_RULES),
        "focused_validation_rule_count": sum(
            1 for row in FAST_VALIDATION_PLAN_RULES if row["command_family"] == "focused_pytest"
        ),
        "full_validation_defer_rule_count": sum(
            1 for row in FAST_VALIDATION_PLAN_RULES if row["command_family"] != "microcosm_validate"
        ),
        "slow_command_rank_count": sum(1 for row in COMMAND_LATENCY_INVENTORY if row["within_budget"] is False),
        "singleflight_policy_count": sum(
            1 for row in COMMAND_LATENCY_INVENTORY if "reuse" in row["concurrency_policy"] or "attach" in row["concurrency_policy"]
        ),
        "latency_inventory_private_telemetry_count": sum(
            1 for row in COMMAND_LATENCY_INVENTORY if row["imports_private_telemetry"] is True
        ),
        "agent_path_dashboard_count": 1,
        "agent_path_signal_count": len(AGENT_PATH_DIAGNOSTIC_DASHBOARD["behavior_fitness_signals"]),
        "trace_to_git_handoff_edge_count": len(AGENT_PATH_DIAGNOSTIC_DASHBOARD["trace_to_git_handoff"]["edge_order"]),
        "raw_session_body_export_count": 0,
        "raw_prompt_export_count": 0,
        "hidden_reasoning_export_count": 0,
        "private_path_export_count": 0,
        "live_command_log_export_count": 0,
        "private_work_ledger_card_export_count": 0,
        "portability_mode_count": len(PORTABILITY_AUTHORITY_MATRIX["modes"]),
        "standalone_safe_portability_mode_count": sum(
            1 for row in PORTABILITY_AUTHORITY_MATRIX["modes"] if row["standalone_safe"] is True
        ),
        "root_only_adapter_mode_count": sum(
            1 for row in PORTABILITY_AUTHORITY_MATRIX["modes"] if row["scope"] == "private_root_only"
        ),
        "leaf_subrepo_blocked_mode_count": sum(
            1
            for row in PORTABILITY_AUTHORITY_MATRIX["modes"]
            if row["scope"] == "microcosms/meta_diagnostics_workbench_only" and row["standalone_safe"] is False
        ),
        "zero_export_counter_count": len(PORTABILITY_AUTHORITY_MATRIX["zero_export_counters"]),
        "nonzero_zero_export_counter_count": sum(
            1 for value in PORTABILITY_AUTHORITY_MATRIX["zero_export_counters"].values() if value != 0
        ),
        "root_owned_surface_count": len(STANDALONE_SPLIT_CONTRACT["root_owned_surfaces"]),
        "leaf_owned_surface_count": len(STANDALONE_SPLIT_CONTRACT["leaf_owned_surfaces"]),
        "status_authority_nodes": ["meta_diagnostic_evaluator", "receipt_gate"],
    }
    diagnostic_board = {
        "kind": "meta_diagnostics_workbench_specimen",
        "schema_version": "meta_diagnostics_workbench_specimen_v0",
        "generated_at": generated_at,
        "status": status,
        "candidate_id": SPECIMEN_ID,
        "authority_posture": AUTHORITY_POSTURE,
        "release_scope_statement": RELEASE_SCOPE_STATEMENT,
        "source_refs": [
            "AGENTS.md",
            "README.md",
            "navigation/entry_packet.json",
            "navigation/microcosm_index.json",
            "microcosms/leaf_entry_contract.json",
            "microcosms/self_comprehension_navigator/navigator_board.json",
            "microcosms/concurrency_mission_control/mission_board.json",
            "microcosms/specimen_suite/std_python_compliance_report.json",
            "registry/release_candidates.json",
            "registry/validators.json",
            "standards/leaf_entry_contract.json",
            "skills/leaf_porting.md",
        ],
        "improvement_delta": "Bring command-speed, command wait-tax, context-fit, test, architecture-boundary, and standalone-wrapper diagnostics into the public microcosm as fixture-backed local evidence.",
        "authority_trace": list(AUTHORITY_TRACE),
        "dogfood_preflight": {
            "status": "fixture_ready",
            "context_budget_tokens": 12000,
            "private_root_dependency": False,
            "command_speed_certification": False,
            "publication_authority": False,
            "command_sequence": list(DOGFOOD_PREFLIGHT),
            "standalone_split_contract": STANDALONE_SPLIT_CONTRACT,
        },
        "command_latency_inventory": {
            "status": "fixture_ready",
            "source": "synthetic_latency_seed_transfer",
            "ranking_basis": "observed_ms_desc_public_safe_fixture",
            "owner_surface": "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
            "slow_command_owner_surface": "microcosms/concurrency_mission_control/mission_board.json",
            "rows": list(COMMAND_LATENCY_INVENTORY),
            "authority_boundary": "Ranks synthetic command shapes for local microcosm routing only; not live telemetry, benchmark evidence, hosted CI evidence, or performance certification.",
        },
        "command_speedboard": COMMAND_SPEEDBOARD,
        "diagnostic_execution_ladder": DIAGNOSTIC_EXECUTION_LADDER,
        "context_fit_compression_gate": CONTEXT_FIT_COMPRESSION_GATE,
        "fast_validation_planner": {
            "status": "fixture_ready",
            "source": "synthetic_validation_selection_rules",
            "selection_policy": "changed_path_to_focused_command_before_full_root_validate",
            "full_root_validate_policy": "defer_until_focused_checks_pass_or_validator_owner_changes",
            "duplicate_command_policy": "attach_or_reuse_active_command_key",
            "rules": list(FAST_VALIDATION_PLAN_RULES),
            "authority_boundary": "Plans public-safe validation command shapes only; not live timing telemetry, hidden test selection, hosted CI proof, or performance certification.",
        },
        "agent_path_diagnostic_dashboard": AGENT_PATH_DIAGNOSTIC_DASHBOARD,
        "portability_authority_matrix": PORTABILITY_AUTHORITY_MATRIX,
        "cases": cases,
        "summary": summary,
        "public_safety_boundary": "Synthetic diagnostic fixtures only; no private command logs, live timing telemetry, private root paths, provider traces, hosted receipts, private context packs, or benchmark scores are included.",
        "claim_boundary": "Fixture-level proof of meta diagnostic routing; not command-speed certification, live latency telemetry, private-root context-fit proof, standalone wrapper shipment, hosted readiness, publication approval, or private-root equivalence claim.",
        "publication_boundary": {
            "status": "fail_closed",
            "blocked_until": "disclosure, license, citation, hosted-public, clean-run, clone-run, standalone wrapper, and package-manifest gates are current",
        },
        "anti_claims": [
            "command speed certified",
            "microcosm latency fixture certifies live command performance",
            "private context budget proven",
            "standalone leaf wrapper shipped",
            "local diagnostic fixture proves hosted public availability",
            "meta diagnostic board approves publication",
            "microcosm is equivalent to the private root",
        ],
        "failures": failures,
    }

    output = root / output_path
    _write_json(output, diagnostic_board)
    readme_path = root / README_PATH
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(_readme(), encoding="utf-8")

    result: dict[str, Any] = {
        "kind": "meta_diagnostics_workbench_specimen_build",
        "schema_version": "meta_diagnostics_workbench_specimen_build_v0",
        "generated_at": generated_at,
        "status": status,
        "output": output_path,
        "case_count": len(cases),
        "pass_count": len(pass_cases),
        "repair_row_count": len(repair_cases),
        "diagnostic_family_count": len(diagnostic_families),
        "standalone_wrapper_target_count": summary["standalone_wrapper_target_count"],
        "standalone_leaf_supported_count": 0,
        "command_speed_certification_count": 0,
        "command_wait_tax_case_count": summary["command_wait_tax_case_count"],
        "latency_seed_transfer_case_count": summary["latency_seed_transfer_case_count"],
        "dogfood_preflight_step_count": summary["dogfood_preflight_step_count"],
        "command_latency_inventory_count": summary["command_latency_inventory_count"],
        "command_speedboard_count": summary["command_speedboard_count"],
        "command_speedboard_lane_count": summary["command_speedboard_lane_count"],
        "command_speedboard_duplicate_wait_tax_lane_count": summary[
            "command_speedboard_duplicate_wait_tax_lane_count"
        ],
        "command_speedboard_private_telemetry_count": summary["command_speedboard_private_telemetry_count"],
        "command_speedboard_live_performance_certification_count": summary[
            "command_speedboard_live_performance_certification_count"
        ],
        "diagnostic_execution_tier_count": summary["diagnostic_execution_tier_count"],
        "diagnostic_execution_default_tier_count": summary["diagnostic_execution_default_tier_count"],
        "diagnostic_execution_private_root_tier_count": summary["diagnostic_execution_private_root_tier_count"],
        "diagnostic_execution_standalone_safe_tier_count": summary["diagnostic_execution_standalone_safe_tier_count"],
        "diagnostic_execution_nonzero_zero_export_counter_count": summary[
            "diagnostic_execution_nonzero_zero_export_counter_count"
        ],
        "context_fit_compression_gate_count": summary["context_fit_compression_gate_count"],
        "context_fit_gate_step_count": summary["context_fit_gate_step_count"],
        "context_fit_gate_default_step_count": summary["context_fit_gate_default_step_count"],
        "context_fit_gate_standalone_safe_step_count": summary["context_fit_gate_standalone_safe_step_count"],
        "context_fit_full_report_default_count": summary["context_fit_full_report_default_count"],
        "context_fit_summary_byte_reduction_percent": summary["context_fit_summary_byte_reduction_percent"],
        "context_fit_nonzero_zero_export_counter_count": summary["context_fit_nonzero_zero_export_counter_count"],
        "fast_validation_rule_count": summary["fast_validation_rule_count"],
        "focused_validation_rule_count": summary["focused_validation_rule_count"],
        "full_validation_defer_rule_count": summary["full_validation_defer_rule_count"],
        "slow_command_rank_count": summary["slow_command_rank_count"],
        "singleflight_policy_count": summary["singleflight_policy_count"],
        "latency_inventory_private_telemetry_count": summary["latency_inventory_private_telemetry_count"],
        "agent_path_dashboard_count": summary["agent_path_dashboard_count"],
        "agent_path_signal_count": summary["agent_path_signal_count"],
        "trace_to_git_handoff_edge_count": summary["trace_to_git_handoff_edge_count"],
        "raw_session_body_export_count": 0,
        "raw_prompt_export_count": 0,
        "hidden_reasoning_export_count": 0,
        "private_path_export_count": 0,
        "live_command_log_export_count": 0,
        "private_work_ledger_card_export_count": 0,
        "portability_mode_count": summary["portability_mode_count"],
        "standalone_safe_portability_mode_count": summary["standalone_safe_portability_mode_count"],
        "root_only_adapter_mode_count": summary["root_only_adapter_mode_count"],
        "leaf_subrepo_blocked_mode_count": summary["leaf_subrepo_blocked_mode_count"],
        "zero_export_counter_count": summary["zero_export_counter_count"],
        "nonzero_zero_export_counter_count": summary["nonzero_zero_export_counter_count"],
        "root_owned_surface_count": summary["root_owned_surface_count"],
        "leaf_owned_surface_count": summary["leaf_owned_surface_count"],
        "live_performance_certification_count": 0,
        "private_telemetry_dependency_count": 0,
        "private_context_dependency_count": 0,
        "publication_claim_count": 0,
        "failure_count": len(failures),
        "failures": failures,
    }

    if write_receipt:
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": "receipt.meta_diagnostics_workbench_specimen",
            "generated_at": generated_at,
            "owner": "idea_microcosm.meta_diagnostics_workbench_specimen",
            "claim_ref": SPECIMEN_ID,
            "claim_tier": "fixture_validated",
            "command": "python -m idea_microcosm.cli build-meta-diagnostics-workbench-specimen --root . --write-receipt",
            "result": status,
            "status": status,
            "evidence_refs": [
                "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
                "microcosms/meta_diagnostics_workbench/README.md",
                "registry/release_candidates.json",
                "registry/validators.json",
                "src/idea_microcosm/meta_diagnostics_workbench_specimen.py",
                "src/idea_microcosm/validators.py",
                "src/idea_microcosm/cli.py",
                "microcosms/leaf_entry_contract.json",
                "navigation/entry_packet.json",
                "navigation/microcosm_index.json",
                "microcosms/specimen_suite/std_python_compliance_report.json",
            ],
            "omissions": [
                "This receipt proves a synthetic meta diagnostic fixture only, not live command-speed certification.",
                "The command wait-tax case transfers latency-seed and singleflight shape only; it does not include live private command telemetry.",
                "The command latency inventory ranks synthetic command shapes only; it does not import private timing logs or certify production latency.",
                "The command speedboard joins latency, concurrency, and fast-validation route state only; it does not import live process tables or certify speed.",
                "The diagnostic execution ladder selects leaf smoke and focused owner checks before root-wide validation; private-root adapter diagnostics remain summary-only and zero-export.",
                "The context-fit compression gate selects summary and focused-lens views before full trace payloads; raw session bodies, raw prompts, hidden reasoning, and private paths stay omitted.",
                "The fast validation planner selects focused public-safe command shapes only; it does not certify live timing or replace the root validator authority.",
                "The agent-path dashboard exports counts, signal ids, route obligations, and anti-claims only; it omits raw prompts, raw session bodies, hidden reasoning, and private traces.",
                "The portability authority matrix separates private-root adapters from release-root clone and leaf-only posture; all zero-export counters must remain zero.",
                "No private command logs, private context packs, provider traces, hosted receipts, or private root paths are included.",
                "Standalone leaf export remains blocked until a wrapper projection carries standards, fixtures, validator or probe, receipt, README, and CLI path.",
                "The dogfood preflight sequence proves local fixture route shape only; root composition remains the validator authority.",
                "Publication remains fail-closed until disclosure, license, citation, clean-run, clone-run, hosted-public, package-manifest, and publication gates are current.",
            ],
            "summary": summary,
        }
        _write_json(root / receipt_path, receipt)
        result["receipt_written"] = receipt_path
    return result
