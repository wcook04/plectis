"""Focused meta diagnostics workbench contract tests.

[PURPOSE]
Prove portability, execution-ladder, and zero-export contracts for the meta diagnostics leaf.

[INTERFACE]
Pytest tests build the specimen into a temp root and inspect the generated board/receipt JSON.

[FLOW]
Build fixture, read the diagnostic board, then assert authority modes, execution tiers, and counters.

[DEPENDENCIES]
idea_microcosm.meta_diagnostics_workbench_specimen, pathlib, and json.

[CONSTRAINTS]
Public-safe fixture assertions only; no private telemetry, live command logs, or publication claims.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from idea_microcosm.meta_diagnostics_workbench_specimen import build_meta_diagnostics_workbench_specimen


def test_meta_diagnostics_portability_authority_matrix_stays_public_safe(tmp_path: Path) -> None:
    result = build_meta_diagnostics_workbench_specimen(
        tmp_path,
        write_receipt=True,
        at="2026-05-17T16:58:00Z",
    )

    assert result["status"] == "ok"
    assert result["portability_mode_count"] == 3
    assert result["root_only_adapter_mode_count"] == 1
    assert result["leaf_subrepo_blocked_mode_count"] == 1
    assert result["standalone_safe_portability_mode_count"] == 1
    assert result["nonzero_zero_export_counter_count"] == 0

    board = json.loads(
        (tmp_path / "microcosms" / "meta_diagnostics_workbench" / "diagnostic_board.json").read_text(
            encoding="utf-8"
        )
    )
    matrix = board["portability_authority_matrix"]
    modes = {row["mode_id"]: row for row in matrix["modes"]}

    assert matrix["status"] == "fixture_ready"
    assert set(modes) == {"private_root_adapter", "release_root_clone", "leaf_subrepo_fixture"}
    assert modes["private_root_adapter"]["standalone_safe"] is False
    assert modes["release_root_clone"]["standalone_safe"] is True
    assert modes["leaf_subrepo_fixture"]["standalone_safe"] is False
    assert "raw prompts" in modes["private_root_adapter"]["must_not_export"]
    assert "private Work Ledger session cards" in modes["private_root_adapter"]["must_not_export"]
    assert "leaf folder alone is standalone" in modes["leaf_subrepo_fixture"]["must_not_export"]
    assert "root_validate_and_focused_test_must_pass_before_release_root_claim_strengthens" == modes[
        "release_root_clone"
    ]["promotion_gate"]
    assert all(value == 0 for value in matrix["zero_export_counters"].values())

    summary = board["summary"]
    assert summary["portability_mode_count"] == len(matrix["modes"])
    assert summary["zero_export_counter_count"] == len(matrix["zero_export_counters"])
    assert summary["nonzero_zero_export_counter_count"] == 0
    assert summary["private_path_export_count"] == 0
    assert summary["live_command_log_export_count"] == 0
    assert summary["private_work_ledger_card_export_count"] == 0
    assert "zero-export counter check" in matrix["fail_closed_if_missing"]


def test_meta_diagnostics_execution_ladder_prefers_focused_checks(tmp_path: Path) -> None:
    result = build_meta_diagnostics_workbench_specimen(
        tmp_path,
        write_receipt=True,
        at="2026-05-17T17:08:00Z",
    )

    assert result["status"] == "ok"
    assert result["diagnostic_execution_tier_count"] == 4
    assert result["diagnostic_execution_default_tier_count"] == 2
    assert result["diagnostic_execution_private_root_tier_count"] == 1
    assert result["diagnostic_execution_standalone_safe_tier_count"] == 3
    assert result["diagnostic_execution_nonzero_zero_export_counter_count"] == 0

    board = json.loads(
        (tmp_path / "microcosms" / "meta_diagnostics_workbench" / "diagnostic_board.json").read_text(
            encoding="utf-8"
        )
    )
    ladder = board["diagnostic_execution_ladder"]
    tiers = {row["tier_id"]: row for row in ladder["tiers"]}

    assert ladder["status"] == "fixture_ready"
    assert ladder["policy"] == "selected_lens_and_leaf_smoke_before_root_wide_validation"
    assert list(tiers) == [
        "leaf_smoke",
        "focused_owner_regression",
        "root_composition_validate",
        "private_root_adapter_summary",
    ]
    assert tiers["leaf_smoke"]["runs_by_default"] is True
    assert tiers["focused_owner_regression"]["runs_by_default"] is True
    assert tiers["root_composition_validate"]["runs_by_default"] is False
    assert tiers["private_root_adapter_summary"]["private_root_only"] is True
    assert tiers["private_root_adapter_summary"]["standalone_safe"] is False
    assert tiers["private_root_adapter_summary"]["projection_rule"] == (
        "private_root_summary_may_project_counts_and_route_obligations_only"
    )
    assert ladder["escalation_guards"]["full_root_validate_before_focus_allowed"] is False
    assert ladder["escalation_guards"]["all_lens_session_diagnostics_before_summary_allowed"] is False
    assert ladder["escalation_guards"]["private_adapter_allowed_in_standalone"] is False
    assert ladder["escalation_guards"]["duplicate_command_spawn_allowed_without_attach_or_reuse"] is False
    assert all(value == 0 for value in ladder["zero_export_counters"].values())

    summary = board["summary"]
    assert summary["diagnostic_execution_tier_count"] == len(ladder["tiers"])
    assert summary["diagnostic_execution_nonzero_zero_export_counter_count"] == 0


def test_meta_diagnostics_context_fit_gate_is_summary_first(tmp_path: Path) -> None:
    result = build_meta_diagnostics_workbench_specimen(
        tmp_path,
        write_receipt=True,
        at="2026-05-17T17:16:00Z",
    )

    assert result["status"] == "ok"
    assert result["context_fit_compression_gate_count"] == 1
    assert result["context_fit_gate_step_count"] == 4
    assert result["context_fit_gate_default_step_count"] == 3
    assert result["context_fit_gate_standalone_safe_step_count"] == 1
    assert result["context_fit_full_report_default_count"] == 0
    assert result["context_fit_summary_byte_reduction_percent"] == 71.2
    assert result["context_fit_nonzero_zero_export_counter_count"] == 0

    board = json.loads(
        (tmp_path / "microcosms" / "meta_diagnostics_workbench" / "diagnostic_board.json").read_text(
            encoding="utf-8"
        )
    )
    gate = board["context_fit_compression_gate"]
    steps = {row["step_id"]: row for row in gate["gate_steps"]}

    assert gate["status"] == "fixture_ready"
    assert gate["policy"] == "selected_lens_summary_before_full_trace_payload"
    assert gate["source_shape"]["selected_lens"] == "latency"
    assert gate["source_shape"]["selected_lens_adequacy"] == "single_lens_sufficient"
    assert gate["source_shape"]["raw_report_export_allowed"] is False
    assert gate["source_shape"]["raw_session_body_export_allowed"] is False
    assert gate["source_shape"]["private_prompt_export_allowed"] is False
    assert list(steps) == [
        "summary_first_scan",
        "selected_lens_drilldown",
        "leaf_receipt_check",
        "full_report_fallback",
    ]
    assert steps["summary_first_scan"]["runs_by_default"] is True
    assert steps["selected_lens_drilldown"]["runs_by_default"] is True
    assert steps["leaf_receipt_check"]["standalone_safe"] is True
    assert steps["full_report_fallback"]["runs_by_default"] is False
    assert steps["full_report_fallback"]["standalone_safe"] is False
    assert gate["standalone_contract"]["private_root_dependency_count"] == 0
    assert ".codex session store" in gate["standalone_contract"]["must_not_require"]
    assert all(value == 0 for value in gate["zero_export_counters"].values())

    summary = board["summary"]
    assert summary["context_fit_gate_step_count"] == len(gate["gate_steps"])
    assert summary["context_fit_nonzero_zero_export_counter_count"] == 0
