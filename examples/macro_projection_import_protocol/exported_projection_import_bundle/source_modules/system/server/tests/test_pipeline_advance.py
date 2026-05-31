"""
[PURPOSE]
- Teleology: Exercise the server-backend pipeline_advance selector and attention heuristics against isolated pipeline-state fixtures.
- Mechanism: Build temporary phase-family state files, invoke pipeline_advance decision helpers, and assert fallback selection, wake-up heuristics, and safe launch-profile commands.

[INTERFACE]
- Exports: Module-level regression tests for find_state(), compute_codex_attention(), and next_action().
- Reads: Temporary pipeline_state, phase_family, cycle summary, and cycle assimilation fixtures plus dictionaries returned by pipeline_advance.
- Writes: JSON fixture artifacts inside per-test temporary directories.
- Non-goal: Does not advance live pipelines; it only validates the backend decision logic exposed by pipeline_advance.

[FLOW]
- Helper writers create bounded phase-family and cycle artifacts under temporary roots.
- Tests point pipeline_advance.REPO_ROOT at those roots and call selection or attention helpers.
- Assertions verify explicit active-phase preference, bounded-loop suppression, wake conditions, and safe dispatch commands.
- When-needed: Open when server-backend failures involve pipeline state selection, Codex-attention heuristics, or next-action command composition and you need the exact regression coverage before reading pipeline_advance.py.
- Escalates-to: pipeline_advance.py
- Navigation-group: server_backend

[DEPENDENCIES]
- pipeline_advance: Supplies the state-selection, attention, and next-action helpers under test.
- pathlib.Path, os, json: Provide deterministic on-disk fixtures for pipeline state and cycle summaries.

[CONSTRAINTS]
- Couples: These tests assume pipeline_advance continues to read phase_family markers, cycle summaries, and cycle assimilation packets from the current repo-root contract.
- Orders: Each test rewrites REPO_ROOT to a fresh temporary tree before invoking decision helpers.
- Fails: Assertion failures indicate drift in state preference, attention gating, or generated action commands.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pipeline_advance


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_find_state_prefers_explicit_active_phase_state_over_newer_mtime(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    family_rel = "obsidian/workstream/08 - Distributed Autonomy, JSON-First Artifacts, and Bridge-Native Workflows"
    family_path = tmp_path / family_rel
    phase_82_state = tmp_path / family_rel / "08.2 - Phase 08.2 - Old Runtime" / "pipeline_state.json"
    phase_83_state = tmp_path / family_rel / "08.3 - Phase 08.3 - New Activation" / "pipeline_state.json"
    _write_json(
        family_path / "phase_family.json",
        {
            "kind": "phase_family",
            "family_id": "08",
            "family_number": "08",
            "family_title": "Distributed Autonomy, JSON-First Artifacts, and Bridge-Native Workflows",
            "family_dir": family_rel,
            "active_phase_id": "08_3",
            "active_phase_number": "08.3",
            "active_phase_title": "Phase 08.3 - New Activation",
            "active_phase_dir": f"{family_rel}/08.3 - Phase 08.3 - New Activation",
            "active_phase_changed_at": "2026-03-23T20:00:00+00:00",
            "active_phase_source_command": "new-phase",
        },
    )
    _write_json(phase_82_state, {"pipeline_id": "PIPE_82", "phase_dir": "old"})
    _write_json(phase_83_state, {"pipeline_id": "PIPE_83", "phase_dir": "new"})
    newer = phase_82_state.stat().st_mtime + 100
    os.utime(phase_82_state, (newer, newer))

    state_path, state = pipeline_advance.find_state()

    assert state_path == phase_83_state
    assert state["pipeline_id"] == "PIPE_83"


def test_find_state_falls_back_when_explicit_active_phase_state_is_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    family_rel = "obsidian/workstream/08 - Distributed Autonomy, JSON-First Artifacts, and Bridge-Native Workflows"
    family_path = tmp_path / family_rel
    active_phase_dir = f"{family_rel}/08.10 - Phase 08.10 - Missing Runtime"
    fallback_state = tmp_path / family_rel / "08.5 - Phase 08.5 - Live Runtime" / "pipeline_state.json"
    _write_json(
        family_path / "phase_family.json",
        {
            "kind": "phase_family",
            "family_id": "08",
            "family_number": "08",
            "family_title": "Distributed Autonomy, JSON-First Artifacts, and Bridge-Native Workflows",
            "family_dir": family_rel,
            "active_phase_id": "08_10",
            "active_phase_number": "08.10",
            "active_phase_title": "Phase 08.10 - Missing Runtime",
            "active_phase_dir": active_phase_dir,
            "active_phase_changed_at": "2026-03-24T04:08:42+00:00",
            "active_phase_source_command": "new-phase",
        },
    )
    _write_json(fallback_state, {"pipeline_id": "PIPE_85", "phase_dir": "live"})

    state_path, state = pipeline_advance.find_state()

    # Constitutional rule (operator decision 2026-05-04, see
    # system/lib/phase_lifecycle.py::resolve_latest_runtime_state): when an
    # explicit active phase activation exists but its phase_dir contains no
    # pipeline_state.json, find_state must NOT fall back to a different
    # phase's pipeline_state. The earlier expectation that 08.5's runtime
    # would be returned when 08.10 was the active phase silently rendered
    # an unrelated legacy phase as if it were current. Return None instead.
    assert state_path is None
    assert state is None
    # The would-be fallback file was written for negative-test verification:
    # confirm it exists on disk so we are testing the new constitutional
    # refusal, not a fixture-write failure.
    assert fallback_state.exists()


def test_find_state_returns_none_when_only_deprecated_lineage_has_runtime(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    legacy_family_rel = "obsidian/workstream/08 - Legacy Family"
    live_family_rel = "obsidian/workstream/09 - Live Family"
    legacy_phase_rel = f"{legacy_family_rel}/08.5 - Phase 08.5 - Legacy Runtime"
    live_phase_rel = f"{live_family_rel}/09.15 - Phase 09.15 - Active On Paper"
    _write_json(
        tmp_path / legacy_family_rel / "phase_family.json",
        {
            "kind": "phase_family",
            "family_id": "08",
            "family_number": "08",
            "family_title": "Legacy Family",
            "family_dir": legacy_family_rel,
            "active_phase_id": "08_5",
            "active_phase_number": "08.5",
            "active_phase_title": "Legacy Runtime",
            "active_phase_dir": legacy_phase_rel,
            "lifecycle": {
                "state": "deprecated",
                "visibility": "visible",
                "runtime_eligible": False,
                "routing_eligible": False,
            },
        },
    )
    _write_json(
        tmp_path / live_family_rel / "phase_family.json",
        {
            "kind": "phase_family",
            "family_id": "09",
            "family_number": "09",
            "family_title": "Live Family",
            "family_dir": live_family_rel,
            "active_phase_id": "09_15",
            "active_phase_number": "09.15",
            "active_phase_title": "Active On Paper",
            "active_phase_dir": live_phase_rel,
        },
    )
    _write_json(tmp_path / legacy_phase_rel / "pipeline_state.json", {"pipeline_id": "PIPE_85", "phase_dir": legacy_phase_rel})

    state_path, state = pipeline_advance.find_state()

    assert state_path is None
    assert state is None


def test_compute_codex_attention_flags_stagnation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    plan_rel = "phase/observe_plan.json"
    dump_dir_rel = "tools/meta/apply/observe_dumps/07_6_cycle_2"
    _write_json(tmp_path / plan_rel, {"dump_dir": dump_dir_rel})
    _write_json(
        tmp_path / f"{dump_dir_rel}/_cycle_summary.json",
        {
            "cycle": 2,
            "zero_evolution_streak": 3,
            "frontier_repeat_streak": 1,
            "new_shards_ingested": 0,
        },
    )

    state = {
        "stage": "results_processed",
        "cycle": 3,
        "observe_plan_path": plan_rel,
        "pipeline_id": "PIPE_test",
        "phase_dir": "phase",
    }

    attention = pipeline_advance.compute_codex_attention(state)

    assert attention["needs_attention"] is True
    assert attention["reason_key"] == "stagnation"
    assert "Zero-evolution streak" in " ".join(attention["details"])


def test_compute_codex_attention_suppresses_stagnation_for_bounded_controller_loop(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    phase_rel = "phase"
    dump_dir_rel = f"{phase_rel}/cycle_2"
    _write_json(
        tmp_path / f"{dump_dir_rel}/_cycle_summary.json",
        {
            "cycle": 2,
            "zero_evolution_streak": 3,
            "frontier_repeat_streak": 3,
            "new_shards_ingested": 0,
        },
    )
    _write_json(
        tmp_path / f"{dump_dir_rel}/cycle_assimilation.json",
        {
            "kind": "cycle_assimilation",
            "loop_decision": {
                "action": "continue_bounded_loop",
                "reason_key": "continue_probe_within_known_universe",
                "summary": "Stay inside the known universe and retarget the next probe.",
            },
        },
    )
    monkeypatch.setattr(
        pipeline_advance,
        "_controller_policy",
        lambda: {
            "wake_conditions": [],
            "smart_pause": {"enabled": True, "non_advance_cycle_limit": 4},
        },
    )

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "results_processed",
            "cycle": 3,
            "phase_dir": phase_rel,
            "controller_phase": "probe",
            "pipeline_id": "PIPE_test",
            "current_cycle_assimilation_path": f"{dump_dir_rel}/cycle_assimilation.json",
        }
    )

    assert attention["needs_attention"] is False
    assert attention["reason_key"] == "none"


def test_compute_codex_attention_suppresses_smart_pause_for_controller_loop(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_advance,
        "_controller_policy",
        lambda: {
            "wake_conditions": [],
            "smart_pause": {"enabled": True, "non_advance_cycle_limit": 4},
        },
    )

    phase_rel = "phase"
    for cycle, controller_phase, routing_decision, confidence in [
        (1, "scope", {"decision": "expand_scope"}, 0.91),
        (2, "probe", {}, 0.93),
        (3, "scope", {"decision": "expand_scope"}, 0.89),
        (4, "probe", {}, 0.9),
    ]:
        _write_json(
            tmp_path / phase_rel / f"cycle_{cycle}" / "_cycle_summary.json",
            {
                "cycle": cycle,
                "controller_phase": controller_phase,
                "routing_decision": routing_decision,
                "gate_reason": "none",
                "degraded_groups": [],
                "confidence_score": confidence,
            },
        )

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "results_processed",
            "cycle": 5,
            "controller_phase": "probe",
            "pipeline_id": "PIPE_test",
            "phase_dir": phase_rel,
        }
    )

    assert attention["needs_attention"] is False
    assert attention["pause_pipeline"] is False
    assert attention["reason_key"] == "none"


def test_next_action_dispatch_uses_safe_launch_profile(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    action = pipeline_advance.next_action({"stage": "observe_plan_compiled"})

    assert action["key"] == "dispatch_bridge"
    assert "--launch-profile safe" in action["command"]


def test_next_action_retries_unmaterialized_bridge_dispatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    plan_rel = "phase/cycle_1/observe_plan.json"
    dump_dir_rel = "phase/cycle_1"
    _write_json(
        tmp_path / plan_rel,
        {
            "dump_dir": dump_dir_rel,
            "groups": [{"label": "a"}, {"label": "b"}],
        },
    )

    state = {
        "stage": "observe_dispatched",
        "observe_plan_path": plan_rel,
        "observe_session_id": None,
        "observe_manifest_path": None,
        "observe_dispatch_started_at": "2026-04-21T10:22:58+00:00",
    }

    readiness = pipeline_advance.check_responses_ready(state)
    action = pipeline_advance.next_action(state)

    assert readiness["status"] == "dispatch_unmaterialized"
    assert readiness["retryable_dispatch"] is True
    assert action["key"] == "retry_bridge_dispatch"
    assert "--bridge" in action["command"]
    assert "--launch-profile safe" in action["command"]


def test_check_responses_is_not_applicable_before_observe_dispatch() -> None:
    state = {
        "stage": "synth_seed_emitted",
        "observe_plan_path": None,
        "observe_session_id": None,
        "observe_manifest_path": None,
    }

    readiness = pipeline_advance.check_responses_ready(state)
    action = pipeline_advance.next_action(state)

    assert readiness["status"] == "not_applicable_no_observe_dispatch"
    assert readiness["not_applicable"] is True
    assert readiness["suggested_command"] == "python3 pipeline_advance.py --advance"
    assert action["key"] == "advance_one_step"


def test_prepare_state_for_retry_dispatch_restores_compiled_stage() -> None:
    state = {
        "stage": "observe_dispatched",
        "observe_session_id": None,
        "observe_manifest_path": None,
    }
    action = {
        "key": "retry_bridge_dispatch",
        "summary": "Bridge dispatch did not materialize.",
    }

    changed = pipeline_advance.prepare_state_for_action(state, action)

    assert changed is True
    assert state["stage"] == "observe_plan_compiled"
    assert state["observe_dispatch_status"] == "retrying"
    assert state["observe_dispatch_retry_reason"] == "Bridge dispatch did not materialize."
    assert state["observe_session_id"] is None
    assert state["observe_manifest_path"] is None


def test_next_action_retries_failed_compiled_dispatch() -> None:
    action = pipeline_advance.next_action(
        {
            "stage": "observe_plan_compiled",
            "observe_dispatch_status": "failed",
            "observe_dispatch_error": "provider gate blocked",
        }
    )

    assert action["key"] == "retry_bridge_dispatch"
    assert "provider gate blocked" in action["summary"]
    assert "--bridge" in action["command"]
    assert "--launch-profile safe" in action["command"]


def test_next_action_prefers_retry_gate_for_retryable_controller_block() -> None:
    action = pipeline_advance.next_action(
        {
            "stage": "results_processed",
            "phase_dir": "obsidian/family/phase",
            "gate_reason": "uncertainty_block",
            "apply_plan_diagnostic_path": "obsidian/family/phase/cycle_3/apply_plan.invalid.json",
        }
    )

    assert action["key"] == "retry_gate"
    assert "--retry-gate" in action["command"]
    assert "not executable" in action["summary"]
    assert "apply_plan.invalid.json" in action["summary"]


def test_compute_codex_attention_flags_apply_review_pending(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "apply_ready",
            "cycle": 4,
            "controller_version": "07.7",
            "controller_phase": "apply_review_pending",
            "current_task_id": "TASK_bridge_infrastructure",
            "gate_reason": "apply_review_pending",
            "apply_plan_path": "phase/apply_plan.json",
            "pipeline_id": "PIPE_test",
            "phase_dir": "phase",
        }
    )

    assert attention["needs_attention"] is True
    assert attention["wake_requested"] is True
    assert attention["reason_key"] == "apply_review_pending"
    assert any("Apply plan" in detail for detail in attention["details"])


def test_next_action_apply_ready_keeps_phase_local_review_gate() -> None:
    action = pipeline_advance.next_action(
        {
            "stage": "apply_ready",
            "phase_dir": "obsidian/family/phase",
            "controller_phase": "apply_review_pending",
        }
    )

    assert action["key"] == "approval_gate"
    assert action["command"] == "python3 seed_pipeline.py --status"
    assert "Review the compiled plan" in action["summary"]


def test_compute_codex_attention_flags_resource_universe_widening(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    phase_rel = "phase"
    dump_dir_rel = f"{phase_rel}/cycle_2"
    _write_json(tmp_path / f"{dump_dir_rel}/_cycle_summary.json", {"cycle": 2})
    _write_json(
        tmp_path / f"{dump_dir_rel}/cycle_assimilation.json",
        {
            "kind": "cycle_assimilation",
            "loop_decision": {
                "action": "widen_scope_candidate",
                "reason_key": "resource_universe_widening",
                "summary": "The finished pass surfaced evidence outside the current bounded universe.",
                "widened_files_outside_scope": ["kernel.py", "system/lib/kernel_navigation.py"],
                "missing_evidence_count": 2,
            },
        },
    )

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "results_processed",
            "cycle": 3,
            "phase_dir": phase_rel,
            "pipeline_id": "PIPE_test",
            "current_cycle_assimilation_path": f"{dump_dir_rel}/cycle_assimilation.json",
        }
    )

    assert attention["needs_attention"] is True
    assert attention["reason_key"] == "resource_universe_widening"
    assert "kernel.py" in " ".join(attention["details"])


def test_compute_codex_attention_ignores_auto_absorbed_scope_widening(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    phase_rel = "phase"
    dump_dir_rel = f"{phase_rel}/cycle_2"
    _write_json(tmp_path / f"{dump_dir_rel}/_cycle_summary.json", {"cycle": 2})
    _write_json(
        tmp_path / f"{dump_dir_rel}/cycle_assimilation.json",
        {
            "kind": "cycle_assimilation",
            "loop_decision": {
                "action": "continue_bounded_loop",
                "reason_key": "auto_absorbed_scope_widening",
                "summary": "Concrete local files were absorbed directly into the next probe.",
                "widened_files_outside_scope": ["pipeline_signal_watcher.py"],
            },
        },
    )

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "results_processed",
            "cycle": 3,
            "phase_dir": phase_rel,
            "controller_phase": "probe",
            "pipeline_id": "PIPE_test",
            "current_cycle_assimilation_path": f"{dump_dir_rel}/cycle_assimilation.json",
        }
    )

    assert attention["needs_attention"] is False
    assert attention["reason_key"] == "none"


def test_compute_codex_attention_ignores_advance_to_plan_within_known_universe(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    phase_rel = "phase"
    dump_dir_rel = f"{phase_rel}/cycle_2"
    _write_json(tmp_path / f"{dump_dir_rel}/_cycle_summary.json", {"cycle": 2})
    _write_json(
        tmp_path / f"{dump_dir_rel}/cycle_assimilation.json",
        {
            "kind": "cycle_assimilation",
            "loop_decision": {
                "action": "continue_bounded_loop",
                "reason_key": "advance_to_plan_within_known_universe",
                "summary": "The finished pass grounded enough evidence to move into planning without widening beyond the current known universe.",
                "missing_evidence_count": 7,
            },
        },
    )

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "results_processed",
            "cycle": 3,
            "phase_dir": phase_rel,
            "controller_phase": "probe",
            "pipeline_id": "PIPE_test",
            "current_cycle_assimilation_path": f"{dump_dir_rel}/cycle_assimilation.json",
        }
    )

    assert attention["needs_attention"] is False
    assert attention["reason_key"] == "none"


def test_compute_codex_attention_allows_retryable_bridge_degradation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    phase_rel = "phase"
    dump_dir_rel = f"{phase_rel}/cycle_2"
    manifest_rel = "tools/meta/apply/observe_history/entries/OBS_retryable.json"
    _write_json(
        tmp_path / manifest_rel,
        {
            "state": "error",
            "dump_dir": dump_dir_rel,
            "groups": [
                {
                    "label": "probe_1",
                    "role": "probe",
                    "response_status": "error",
                    "response_error_category": "provider_submit_failed_fast",
                    "response_error_stage": "provider_submit",
                },
                {
                    "label": "probe_2",
                    "role": "probe",
                    "response_status": "success",
                },
                {
                    "label": "probe_3",
                    "role": "probe",
                    "response_status": "error",
                    "response_error_category": "provider_cancelled",
                    "response_error_stage": "provider_extract",
                },
            ],
        },
    )
    _write_json(
        tmp_path / f"{dump_dir_rel}/_cycle_summary.json",
        {
            "cycle": 2,
            "controller_phase": "scope",
            "gate_reason": "none",
            "degraded_groups": ["probe_1:error", "probe_3:error"],
            "degradation_summary": {
                "degraded_count": 2,
                "retryable_count": 2,
                "non_retryable_count": 0,
                "auto_retry_safe_count": 2,
                "all_degraded_retryable": True,
                "all_degraded_auto_retry_safe": True,
                "successful_probe_count": 1,
                "retryable_labels": ["probe_1", "probe_3"],
                "non_retryable_labels": [],
            },
        },
    )

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "results_processed",
            "cycle": 3,
            "controller_phase": "scope",
            "pipeline_id": "PIPE_test",
            "phase_dir": phase_rel,
            "observe_manifest_path": manifest_rel,
        }
    )

    assert attention["needs_attention"] is False
    assert attention["reason_key"] == "none"


def test_compute_codex_attention_degraded_cycle_is_pause_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    phase_rel = "phase"
    dump_dir_rel = f"{phase_rel}/cycle_2"
    manifest_rel = "tools/meta/apply/observe_history/entries/OBS_degraded.json"
    _write_json(
        tmp_path / manifest_rel,
        {
            "state": "error",
            "dump_dir": dump_dir_rel,
            "groups": [
                {
                    "label": "probe_1",
                    "role": "probe",
                    "response_status": "error",
                    "response_error_category": "provider_selector_failure",
                    "response_error_stage": "provider_wake",
                }
            ],
        },
    )
    _write_json(
        tmp_path / f"{dump_dir_rel}/_cycle_summary.json",
        {
            "cycle": 2,
            "controller_phase": "probe",
            "gate_reason": "none",
            "degraded_groups": ["probe_1:error"],
            "degradation_summary": {
                "degraded_count": 1,
                "retryable_count": 0,
                "non_retryable_count": 1,
                "auto_retry_safe_count": 0,
                "all_degraded_retryable": False,
                "all_degraded_auto_retry_safe": False,
                "successful_probe_count": 0,
                "retryable_labels": [],
                "non_retryable_labels": ["probe_1"],
            },
        },
    )

    attention = pipeline_advance.compute_codex_attention(
        {
            "stage": "results_processed",
            "cycle": 3,
            "controller_phase": "probe",
            "pipeline_id": "PIPE_test",
            "phase_dir": phase_rel,
            "observe_manifest_path": manifest_rel,
        }
    )

    assert attention["needs_attention"] is True
    assert attention["wake_requested"] is False
    assert attention["reason_key"] == "degraded_cycle"


def test_attention_gate_exit_code_clear_ok_treats_no_attention_as_success() -> None:
    assert pipeline_advance.attention_gate_exit_code({"needs_attention": False}) == 0
    assert pipeline_advance.attention_gate_exit_code({"needs_attention": True}) == 1


def test_attention_gate_exit_code_predicate_preserves_shell_attention_test() -> None:
    assert (
        pipeline_advance.attention_gate_exit_code(
            {"needs_attention": True},
            exit_mode="predicate",
        )
        == 0
    )
    assert (
        pipeline_advance.attention_gate_exit_code(
            {"needs_attention": False},
            exit_mode="predicate",
        )
        == 1
    )


def test_build_context_recovery_prefers_family_dir_for_raw_seed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    family_rel = "obsidian/workstream/08 - Bridge-Native Rebaseline"
    phase_rel = f"{family_rel}/08.1 - Phase 08.1 - Architecture Realignment/08.1.1 - Nested Follow-up"
    (tmp_path / family_rel).mkdir(parents=True, exist_ok=True)
    (tmp_path / phase_rel).mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{family_rel}/raw_seed.md").write_text("# Raw Seed\n", encoding="utf-8")

    recovery = pipeline_advance._build_context_recovery(
        {
            "phase_dir": phase_rel,
            "family_dir": family_rel,
        }
    )

    assert recovery["raw_seed_path"] == f"{family_rel}/raw_seed.md"


def test_build_resume_packet_includes_authority_surfaces_and_role_split(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    family_rel = "obsidian/workstream/08 - Bridge"
    phase_rel = f"{family_rel}/08.1 - Phase 08.1 - Planner"
    raw_seed_rel = f"{family_rel}/raw_seed.md"
    synth_seed_rel = f"{phase_rel}/synth_seed.json"
    (tmp_path / family_rel).mkdir(parents=True, exist_ok=True)
    (tmp_path / phase_rel).mkdir(parents=True, exist_ok=True)
    (tmp_path / raw_seed_rel).write_text("# Raw Seed\n", encoding="utf-8")
    cycle_assimilation_rel = f"{phase_rel}/cycle_2/cycle_assimilation.json"
    (tmp_path / cycle_assimilation_rel).parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        tmp_path / cycle_assimilation_rel,
        {
            "kind": "cycle_assimilation",
            "loop_decision": {
                "action": "continue_bounded_loop",
                "reason_key": "none",
                "summary": "Loop can continue.",
            },
        },
    )
    cycle_timeline_rel = f"{phase_rel}/cycle_2/cycle_timeline.jsonl"
    (tmp_path / cycle_timeline_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / cycle_timeline_rel).write_text('{"event":"observe_runtime_finalized"}\n', encoding="utf-8")
    _write_json(
        tmp_path / synth_seed_rel,
        {
            "version": "synth_seed_v3",
            "authoring_status": "authored",
            "intent": {
                "goal": "Ship the overnight planner.",
                "why_now": "Reduce manual babysitting.",
                "raw_seed_anchors": [],
                "success_criteria": ["Wake IDE only at real gates."],
                "non_goals": [],
            },
            "constraints": [],
            "relevant_files": [],
            "investigation_threads": [],
            "apply_boundary": {},
            "source_shards": [],
            "meta": {
                "phase_id": "08_1",
                "phase_number": "08.1",
                "phase_dir": phase_rel,
                "family_dir": family_rel,
            },
        },
    )

    packet = pipeline_advance.build_resume_packet(
        tmp_path / phase_rel / "pipeline_state.json",
        {
            "pipeline_id": "PIPE_test",
            "stage": "results_processed",
            "cycle": 3,
            "phase_dir": phase_rel,
            "family_dir": family_rel,
            "synth_seed_path": synth_seed_rel,
            "raw_seed_path": raw_seed_rel,
            "history": [],
        },
    )

    assert packet["authority_surfaces"]["synth_seed"]["path"] == synth_seed_rel
    assert packet["environment_contract"]["commands"]["repo_python"] == "./repo-python"
    assert packet["authority_surfaces"]["commands"]["sync_synth_markdown"] == "python3 kernel.py --sync-synth 08_1 --live"
    assert packet["authority_surfaces"]["synth_refresh"]["needed"] is False
    assert packet["continuation_packet_path"] == f"{phase_rel}/continuation_packet.json"
    assert packet["artifacts"]["continuation_packet_path"] == f"{phase_rel}/continuation_packet.json"
    assert packet["continuation_packet_fingerprint"]
    assert packet["cycle_assimilation_path"] == cycle_assimilation_rel
    assert packet["cycle_timeline_path"] == cycle_timeline_rel
    assert any("Cheap synthesis" in item for item in packet["agent_operating_contract"]["bridge_owns"])
    assert "Canonical synth write target" in packet["codex_wake_prompt"]
    assert "Current cycle assimilation" in packet["codex_wake_prompt"]
    assert "Current cycle timeline" in packet["codex_wake_prompt"]
    assert "Canonical synth write target" in packet["codex_resume_prompt"]
    assert "Read the cycle assimilation first" in packet["codex_wake_prompt"]
    assert "Canonical repo python: ./repo-python" in packet["codex_resume_prompt"]
    assert "IDE owns:" in packet["codex_resume_prompt"]


def test_build_resume_packet_flags_when_raw_seed_outruns_synth(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    family_rel = "obsidian/workstream/09 - Fresh Raw"
    phase_rel = f"{family_rel}/09.1 - Phase 09.1 - Planner"
    raw_seed_rel = f"{family_rel}/raw_seed.md"
    synth_seed_rel = f"{phase_rel}/synth_seed.json"
    (tmp_path / family_rel).mkdir(parents=True, exist_ok=True)
    (tmp_path / phase_rel).mkdir(parents=True, exist_ok=True)
    raw_path = tmp_path / raw_seed_rel
    synth_path = tmp_path / synth_seed_rel
    raw_path.write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(synth_path, {"intent": "seed", "success_criteria": "plan", "authoring_status": "authored"})
    raw_stat = raw_path.stat()
    os.utime(raw_path, (raw_stat.st_atime, raw_stat.st_mtime + 5))

    packet = pipeline_advance.build_resume_packet(
        tmp_path / phase_rel / "pipeline_state.json",
        {
            "pipeline_id": "PIPE_test",
            "stage": "results_processed",
            "cycle": 4,
            "phase_dir": phase_rel,
            "family_dir": family_rel,
            "synth_seed_path": synth_seed_rel,
            "raw_seed_path": raw_seed_rel,
            "history": [],
        },
    )

    assert packet["authority_surfaces"]["synth_refresh"]["needed"] is True
    assert packet["authority_surfaces"]["synth_refresh"]["reason"] == "raw_seed_newer_than_synth"


def test_build_resume_packet_ignores_old_manifest_match_before_dispatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    family_rel = "obsidian/workstream/08 - Bridge"
    phase_rel = f"{family_rel}/08.5 - Phase 08.5 - Restarted"
    plan_rel = f"{phase_rel}/cycle_0/observe_plan.json"
    dump_dir_rel = f"{phase_rel}/cycle_0"
    entry_rel = "tools/meta/apply/observe_history/entries/OBS_old_cycle_0.json"

    (tmp_path / phase_rel / "cycle_0").mkdir(parents=True, exist_ok=True)
    _write_json(tmp_path / plan_rel, {"dump_dir": dump_dir_rel})
    _write_json(tmp_path / entry_rel, {"dump_dir": dump_dir_rel})

    packet = pipeline_advance.build_resume_packet(
        tmp_path / phase_rel / "pipeline_state.json",
        {
            "pipeline_id": "PIPE_restart",
            "stage": "observe_plan_compiled",
            "cycle": 0,
            "created_at": "2026-03-23T23:51:47+00:00",
            "phase_dir": phase_rel,
            "family_dir": family_rel,
            "observe_plan_path": plan_rel,
            "observe_manifest_path": None,
            "history": [],
        },
    )

    assert packet["observe_manifest_path"] is None


def test_active_scope_uses_synth_file_paths_not_stringified_dicts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline_advance, "REPO_ROOT", tmp_path)

    family_rel = "obsidian/workstream/08 - Bridge"
    phase_rel = f"{family_rel}/08.5 - Phase 08.5 - Restarted"
    synth_rel = f"{phase_rel}/synth_seed.json"
    (tmp_path / phase_rel).mkdir(parents=True, exist_ok=True)
    _write_json(
        tmp_path / synth_rel,
        {
            "version": "synth_seed_v3",
            "authoring_status": "authored",
            "intent": {
                "goal": "Test active scope rendering.",
                "why_now": "Resume packet should show file paths.",
                "raw_seed_anchors": [],
                "success_criteria": [],
                "non_goals": [],
            },
            "constraints": [],
            "relevant_files": [
                {"path": "pipeline_advance.py", "role": "surface", "why": "status"},
                {"path": "seed_pipeline.py", "role": "runtime", "why": "state"},
            ],
            "investigation_threads": [],
            "apply_boundary": {},
            "source_shards": [],
            "meta": {"phase_id": "08_5", "phase_number": "08.5", "phase_dir": phase_rel, "family_dir": family_rel},
        },
    )

    active_scope = pipeline_advance._active_scope(
        {
            "phase_dir": phase_rel,
            "synth_seed_path": synth_rel,
            "known_relevant_files": [],
            "active_scope_files": [],
        }
    )

    assert active_scope["active_scope_files"] == ["pipeline_advance.py", "seed_pipeline.py"]
