"""Regression coverage for cold-task navigation fitness."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.navigation_fitness import (
    ADVERSARIAL_TASKS,
    CLI_TIMEOUT_SECONDS_BY_ROUTE,
    DEFAULT_LATENCY_BUDGETS_MS,
    HELDOUT_TASKS,
    FitnessTask,
    _debt_candidates,
    _cli_timeout_seconds,
    build_navigation_fitness,
)
from system.lib.navigation_metabolism_ledger import QUICK_COMMAND_CACHE_TTL_SECONDS


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_cli_timeout_profile_is_packet_guard_not_latency_budget() -> None:
    for route_type, latency_budget_ms in DEFAULT_LATENCY_BUDGETS_MS.items():
        task = FitnessTask(
            f"{route_type}_timeout_profile_probe",
            "timeout_profile",
            "probe",
            route_type,
            (),
        )
        timeout_ms = int(_cli_timeout_seconds(task, fitness_mode="cli") * 1000)
        assert timeout_ms >= latency_budget_ms * 3, (
            f"{route_type} timeout must leave room for latency debt before packet timeout"
        )
        assert route_type in CLI_TIMEOUT_SECONDS_BY_ROUTE

    context_pack = FitnessTask(
        "semantic_context_pack_timeout_profile_probe",
        "timeout_profile",
        "probe",
        "context_pack",
        (),
    )
    assert _cli_timeout_seconds(context_pack, fitness_mode="semantic") == _cli_timeout_seconds(
        context_pack,
        fitness_mode="cli",
    )


def test_quick_command_cache_ttl_covers_normal_agent_wave() -> None:
    assert QUICK_COMMAND_CACHE_TTL_SECONDS >= 600.0


def test_navigation_fitness_smoke_proves_expected_ids_without_legacy_first_routes() -> None:
    payload = build_navigation_fitness(REPO_ROOT, "smoke", context_budget=12000, fitness_mode="library")

    assert payload["kind"] == "navigation_fitness"
    assert payload["schema_version"] == "navigation_fitness_v0"
    assert payload["summary"]["task_count"] >= 6
    assert payload["summary"]["sufficiency_fail_count"] == 0
    assert "p95_wall_ms" in payload["summary"]
    assert "latency_fail_count" in payload["summary"]
    assert payload["strategy"]["fitness_mode"] == "library"
    assert "context_pack" in payload["route_type_metrics"]
    assert payload["budget"]["estimated_tokens"] <= 12000

    by_id = {row["task_id"]: row for row in payload["task_results"]}
    diagnostics = by_id["skill_discovery_agent_session_diagnostics"]
    assert "skills:agent_session_diagnostics" in diagnostics["selected_artifacts"]
    assert "skills:navigation_metabolism" in diagnostics["selected_artifacts"]
    assert diagnostics["forbidden_first_route_hits"] == []
    assert diagnostics["scent_status"] == "pass"
    assert diagnostics["stage_timings_ms"]
    assert "semantic_candidates" in diagnostics["stage_timings_ms"]

    lattice = by_id["skill_discovery_dynamic_paper_lattice"]
    assert "skills:dynamic_paper_lattice" in lattice["selected_artifacts"]
    assert "drilldown:paper_lattice:navigation_hologram_theory" in lattice["selected_artifacts"]

    unsupported = by_id["unsupported_lattice_structured"]
    assert unsupported["selected_artifacts"] == ["error:unknown_paper_module_slug"]
    assert unsupported["sufficiency_status"] == "pass"


def test_navigation_fitness_baseline_covers_twenty_task_families() -> None:
    payload = build_navigation_fitness(REPO_ROOT, "baseline", context_budget=12000, fitness_mode="library")

    assert payload["summary"]["task_count"] == 27
    assert payload["summary"]["sufficiency_fail_count"] == 0
    assert "latency_fail_count" in payload["summary"]
    assert len(payload["task_results"]) <= 27
    assert payload["budget"]["estimated_tokens"] <= 12000

    cluster_payload = build_navigation_fitness(
        REPO_ROOT,
        "cluster_surface",
        context_budget=12000,
        fitness_mode="library",
    )
    by_id = {row["task_id"]: row for row in cluster_payload["task_results"]}
    assert "cluster:standards:core" in by_id["standards_cluster_surface"]["selected_artifacts"]
    assert "cluster:python_files:kernel_lib" in by_id["python_files_cluster_surface"]["selected_artifacts"]
    assert "cluster:python_scopes:kernel_lib" in by_id["python_scopes_cluster_surface"]["selected_artifacts"]
    assert "cluster:frontend_components:system/server/ui/src/components" in by_id[
        "frontend_components_cluster_surface"
    ]["selected_artifacts"]
    assert "cluster:principles:meta" in by_id["principles_cluster_surface"]["selected_artifacts"]
    assert "cluster:annex_patterns:skills-authoring" in by_id[
        "annex_patterns_cluster_surface"
    ]["selected_artifacts"]
    assert "cluster:annex_distillation_patterns:meta-harness" in by_id[
        "annex_distillation_patterns_cluster_surface"
    ]["selected_artifacts"]


def test_navigation_fitness_heldout_and_adversarial_suites_are_nonliteral() -> None:
    heldout = build_navigation_fitness(REPO_ROOT, "heldout_20", context_budget=50000, fitness_mode="library")
    adversarial = build_navigation_fitness(REPO_ROOT, "adversarial_20", context_budget=50000, fitness_mode="library")

    assert heldout["summary"]["task_count"] == 20
    assert heldout["summary"]["sufficiency_fail_count"] == 0
    assert adversarial["summary"]["task_count"] == 23
    assert adversarial["summary"]["sufficiency_fail_count"] == 0
    adversarial_by_id = {row["task_id"]: row for row in adversarial["task_results"]}
    for task_id in (
        "adversarial_grep_with_extra_steps",
        "adversarial_artifact_kind_owns_repair",
        "adversarial_session_better_or_worse",
    ):
        assert adversarial_by_id[task_id]["sufficiency_status"] == "pass"
    nonliteral = 0
    for task in HELDOUT_TASKS:
        prompt = task.task_prompt.lower()
        if task.expected_artifacts and not any(expected.lower().split(":", 1)[-1] in prompt for expected in task.expected_artifacts):
            nonliteral += 1
    assert nonliteral >= 3
    assert any("--skill-find" in route for task in ADVERSARIAL_TASKS for route in task.forbidden_first_routes)
    assert all(row["forbidden_first_route_hits"] == [] for row in adversarial["task_results"])


def test_navigation_fitness_cli_and_semantic_modes_are_explicit() -> None:
    cli_payload = build_navigation_fitness(REPO_ROOT, "smoke", context_budget=12000, fitness_mode="cli")
    assert cli_payload["strategy"]["fitness_mode"] == "cli"
    assert cli_payload["budget"]["estimated_tokens"] <= 12000
    assert any(row["command_used"].startswith("./repo-python kernel.py") for row in cli_payload["task_results"])
    assert "route_type_metrics" in cli_payload
    assert cli_payload["summary"]["sufficiency_fail_count"] == 0
    assert [row for row in cli_payload["debt_candidates"] if row["debt_class"] == "timeout_debt"] == []
    by_id = {row["task_id"]: row for row in cli_payload["task_results"]}
    assert by_id["entrypoint_health_direct"]["command_used"] == "./repo-python kernel.py --entrypoint-health"
    assert by_id["entrypoint_health_direct"]["sufficiency_status"] == "pass"
    assert "--metabolism-profile quick" in by_id["entrypoint_budget_route_health"]["command_used"]
    metab_row = by_id["entrypoint_budget_route_health"]
    if metab_row["sufficiency_status"] == "fail":
        assert metab_row["sufficiency_failure_kind"] == "route_timeout"
        timeout_row = next(
            row
            for row in cli_payload["debt_candidates"]
            if row["debt_class"] == "timeout_debt" and row["task_id"] == "entrypoint_budget_route_health"
        )
        assert timeout_row["target_files"], "timeout_debt must name at least one repair owner"
        assert timeout_row["repair_class"]
        assert "hidden_expected_artifacts" in timeout_row
        sufficiency_rows = [
            row
            for row in cli_payload["debt_candidates"]
            if row["debt_class"] == "sufficiency_debt" and row["task_id"] == "entrypoint_budget_route_health"
        ]
        assert sufficiency_rows == [], "route_timeout must not also emit a sufficiency_debt row"
    else:
        assert metab_row["sufficiency_status"] == "pass"

    semantic_payload = build_navigation_fitness(
        REPO_ROOT,
        "skill_discovery_agent_session_diagnostics",
        context_budget=12000,
        fitness_mode="semantic",
    )
    assert semantic_payload["strategy"]["fitness_mode"] == "semantic"
    assert semantic_payload["summary"]["task_count"] == 1
    semantic_row = semantic_payload["task_results"][0]
    assert semantic_row["timed_out"] is False
    assert semantic_row["semantic_status"]["status"] in {
        "available",
        "timeout_deferred",
        "deferred_due_to_routine_latency_budget",
    }
    assert semantic_payload["summary"]["sufficiency_fail_count"] == 0
    assert semantic_payload["summary"]["latency_fail_count"] in {0, 1}
    if semantic_payload["summary"]["latency_fail_count"]:
        latency = next(row for row in semantic_payload["debt_candidates"] if row["debt_class"] == "latency_debt")
        assert latency["repair_class"] in {
            "defer_or_cache_semantic_expansion",
            "live_semantic_latency_profile",
        }
        if latency["repair_class"] == "defer_or_cache_semantic_expansion":
            assert latency["slow_stage"] == "semantic_candidates"
        assert latency["route_role"] == "first_contact"


def test_entrypoint_health_cli_and_metabolism_quick_profile_are_compact() -> None:
    entrypoint = subprocess.run(
        [sys.executable, "kernel.py", "--entrypoint-health"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert entrypoint.returncode == 0
    entrypoint_payload = json.loads(entrypoint.stdout)
    assert entrypoint_payload["kind"] == "entrypoint_health"
    assert entrypoint_payload["summary"]["contract_status"] == "valid"
    assert len(entrypoint.stdout.encode("utf-8")) <= 12000 * 4

    quick = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--navigation-metabolism",
            "entrypoint budget route health",
            "--metabolism-profile",
            "quick",
            "--context-budget",
            "12000",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert quick.returncode == 0
    quick_payload = json.loads(quick.stdout)
    assert quick_payload["metabolism_profile"] == "quick"
    entrypoint_debt = int(quick_payload["summary"].get("entrypoint_debt") or 0)
    assert entrypoint_debt >= 0
    if entrypoint_debt:
        assert any(row.get("debt_class") == "entrypoint_debt" for row in quick_payload.get("debt_rows") or [])
    assert quick_payload["budget"]["estimated_tokens"] <= 12000
    assert len(quick.stdout.encode("utf-8")) <= 12000 * 4


def test_navigation_fitness_cli_emits_budgeted_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--navigation-fitness",
            "smoke",
            "--fitness-mode",
            "library",
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
    assert payload["kind"] == "navigation_fitness"
    assert payload["summary"]["sufficiency_fail_count"] == 0
    assert "latency_fail_count" in payload["summary"]
    assert len(result.stdout.encode("utf-8")) <= 12000 * 4


def test_route_timeout_emits_timeout_debt_with_repair_owner_and_hidden_ids() -> None:
    timeout_result = {
        "task_id": "entrypoint_budget_route_health",
        "route_type": "navigation_metabolism",
        "route_role": "diagnostic",
        "fitness_mode": "cli",
        "sufficiency_status": "fail",
        "sufficiency_failure_kind": "route_timeout",
        "latency_status": "timeout",
        "missing_expected_artifacts": [
            "entrypoint_health:valid",
            "route_lifecycle:context_pack",
        ],
        "wall_ms": 8013,
        "latency_budget_ms": 6000,
        "command_used": (
            "./repo-python kernel.py --navigation-metabolism "
            '"Check AGENTS.md budget and stale first-contact route health." '
            "--metabolism-profile quick --context-budget 12000"
        ),
        "slow_stage": None,
    }
    sufficiency_result = {
        "task_id": "context_bloat_paper_module_flag",
        "route_type": "context_pack",
        "route_role": "first_contact",
        "fitness_mode": "library",
        "sufficiency_status": "fail",
        "sufficiency_failure_kind": "weak_scent",
        "latency_status": "pass",
        "missing_expected_artifacts": [],
        "wall_ms": 200,
        "latency_budget_ms": 1500,
        "command_used": "./repo-python kernel.py --context-pack <weak scent>",
        "slow_stage": "kind_atlas",
        "scent_checks": [],
        "recall_at_packet": 0.0,
    }

    rows = _debt_candidates([timeout_result, sufficiency_result])

    timeout_rows = [row for row in rows if row["debt_class"] == "timeout_debt"]
    assert len(timeout_rows) == 1
    timeout_row = timeout_rows[0]
    assert timeout_row["task_id"] == "entrypoint_budget_route_health"
    assert timeout_row["debt_id"] == "timeout:navigation_metabolism:entrypoint_budget_route_health"
    assert timeout_row["target_files"], "timeout_debt must name at least one repair owner"
    assert "system/lib/navigation_metabolism_ledger.py" in timeout_row["target_files"]
    assert timeout_row["repair_class"] == "split_metabolism_summary_from_full"
    assert timeout_row["hidden_expected_artifacts"] == [
        "entrypoint_health:valid",
        "route_lifecycle:context_pack",
    ]
    assert "entrypoint_health:valid" in timeout_row["title"]
    assert "repair_owner=" in timeout_row["title"]

    sufficiency_rows_for_timeout = [
        row
        for row in rows
        if row["debt_class"] == "sufficiency_debt" and row["task_id"] == "entrypoint_budget_route_health"
    ]
    assert sufficiency_rows_for_timeout == [], "route_timeout must not also emit sufficiency_debt"


def test_navigation_metabolism_latency_debt_names_metabolism_owner_files() -> None:
    rows = _debt_candidates(
        [
            {
                "task_id": "entrypoint_budget_route_health",
                "route_type": "navigation_metabolism",
                "route_role": "diagnostic",
                "fitness_mode": "cli",
                "sufficiency_status": "pass",
                "latency_status": "fail",
                "wall_ms": 14331,
                "latency_budget_ms": 6000,
                "slow_stage": None,
                "command_used": (
                    "./repo-python kernel.py --navigation-metabolism "
                    '"Check AGENTS.md budget and stale first-contact route health." '
                    "--metabolism-profile quick --context-budget 12000"
                ),
            }
        ]
    )

    latency_row = rows[0]
    assert latency_row["debt_id"] == "latency:navigation_metabolism:entrypoint_budget_route_health"
    assert latency_row["repair_class"] == "split_metabolism_summary_from_full"
    assert "system/lib/navigation_metabolism_ledger.py" in latency_row["target_files"]
