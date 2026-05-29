import json
import os
import sqlite3

from tools.meta.observability import cli_prompt_trace as trace
from tools.meta.observability.cli_prompt_trace import (
    ToolEvent,
    Turn,
    merge_full_thread,
    render_thread_closeout_report,
    render_trace_capsule_text,
)


def _event(index: int, cmd: str, exit_code: int, output_text: str = "") -> ToolEvent:
    return ToolEvent(
        index=index,
        name="exec_command",
        input={"cmd": cmd},
        tool_call_id=None,
        started_at=None,
        completed_at=None,
        duration_ms=None,
        is_error=exit_code != 0,
        output_text=output_text,
        output_char_count=len(output_text),
        output_sha256_16="",
        exit_code=exit_code,
    )


def _turn(
    events: list[ToolEvent],
    *,
    turn_index: int = 1,
    prompt_text: str = "test prompt",
    assistant_text: str = "done",
) -> Turn:
    return Turn(
        provider="codex",
        session_id="session-for-test",
        session_file="/tmp/session.jsonl",
        turn_id=f"turn-for-test-{turn_index}",
        turn_index=turn_index,
        cwd=None,
        started_at=None,
        completed_at=f"2026-05-24T00:0{turn_index}:00+00:00",
        prompt_text=prompt_text,
        prompt_char_count=len(prompt_text),
        prompt_sha256_16=f"promptsha{turn_index}",
        tool_events=events,
        assistant_text=assistant_text,
        is_complete=True,
    )


def test_mission_index_goal_roster_refresh_overlays_cached_rows(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    conn.execute(
        """
        insert into thread_goals
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "codex-thread-1",
            "goal-1",
            "Keep refining the goal infrastructure from live trace evidence.",
            "active",
            None,
            42,
            9,
            1779980000000,
            1779981000000,
        ),
    )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779982000.0, 1779982000.0))

    session_index = tmp_path / "session_index.jsonl"
    session_index.write_text(
        '{"id":"codex-thread-1","thread_name":"<goal_context>","updated_at":"2026-05-28T16:00:00Z"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    monkeypatch.setattr(trace, "CODEX_SESSION_INDEX", session_index)

    cached_active = {
        "provider": "codex",
        "session_id": "codex-thread-1",
        "display_title": "<goal_context>",
        "title": "<goal_context>",
    }
    cached_rows = [dict(cached_active)]
    index = {
        "schema": "prompt_trace_mission_index_v3",
        "generated_at": "2026-05-28T15:33:46+00:00",
        "goal_authority": {
            "schema": "codex_thread_goal_authority_v1",
            "path": str(goals_db),
            "available": True,
            "row_count": 1,
            "status_counts": {"active": 1},
            "mtime_ms": 1779981000000,
        },
        "active_rows": [cached_active],
        "inactive_rows": [],
        "rows": cached_rows,
    }

    refreshed = trace._refresh_mission_index_goal_roster(index)

    assert refreshed["goal_thread_count"] == 1
    assert refreshed["active_goal_thread_count"] == 1
    assert refreshed["mission_goal_count"] == 1
    assert refreshed["active_mission_goal_count"] == 1
    assert refreshed["goal_authority"]["row_count"] == 1
    assert refreshed["goal_roster_refresh"]["mode"] == "cached_mission_index_overlay"
    assert refreshed["goal_roster_refresh"]["preserved_generated_at"] == "2026-05-28T15:33:46+00:00"
    assert refreshed["goal_roster_refresh"]["goal_authority_stale_before_refresh"] is True
    assert refreshed["goal_roster_refresh"]["previous_goal_authority_mtime_ms"] == 1779981000000
    assert refreshed["goal_roster_refresh"]["current_goal_authority_mtime_ms"] == 1779982000000
    assert refreshed["goal_roster_refresh"]["goal_authority_lag_ms"] == 1000000
    assert refreshed["active_rows"][0]["has_goal"] is True
    assert refreshed["active_rows"][0]["goal_status"] == "active"
    assert refreshed["active_rows"][0]["goal_sort_priority"] == 40
    assert refreshed["rows"][0]["has_goal"] is True
    roster_row = refreshed["goal_threads"][0]
    assert roster_row["thread_id"] == "codex-thread-1"
    assert roster_row["mission_index"]["state"] == "active_row"
    assert roster_row["mission_index"]["title"].startswith("Keep refining the goal infrastructure")


def test_goal_roster_refresh_receipt_sidecar_is_compact(monkeypatch, tmp_path) -> None:
    receipt_path = tmp_path / "goal_roster_receipt.json"
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_BASE", tmp_path)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", tmp_path / "mission_index.json")
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    receipt = trace._write_goal_roster_refresh_receipt({
        "generated_at": "2026-05-28T15:33:46+00:00",
        "goal_authority": {"row_count": 1, "mtime_ms": 1779982000000},
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
        "mission_goal_count": 1,
        "active_mission_goal_count": 1,
        "goal_roster_refresh": {
            "schema": "prompt_trace_mission_index_goal_roster_refresh_v1",
            "goal_authority_stale_before_refresh": True,
            "goal_authority_lag_ms": 1000000,
        },
        "rows": [{"large": "mission rows stay in mission_index.json"}],
    })

    written = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "prompt_trace_mission_index_goal_roster_refresh_receipt_v1"
    assert written["mission_index_path"].endswith("mission_index.json")
    assert written["refresh"]["goal_authority_stale_before_refresh"] is True
    assert written["refresh"]["goal_authority_lag_ms"] == 1000000
    assert written["goal_authority"]["mtime_ms"] == 1779982000000
    assert "rows" not in written


def test_goal_roster_status_reports_current_authority_lag(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    for idx in range(2):
        conn.execute(
            "insert into thread_goals values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"codex-thread-{idx}",
                f"goal-{idx}",
                f"Keep refining goal infrastructure {idx}.",
                "active",
                None,
                10 + idx,
                1,
                1779980000000,
                1779983000000 + idx,
            ),
        )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779983000.0, 1779983000.0))

    mission_index = tmp_path / "mission_index.json"
    receipt_path = tmp_path / "goal_roster_receipt.json"
    cached = {
        "goal_authority": {"mtime_ms": 1779982000000, "row_count": 1},
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
    }
    mission_index.write_text(json.dumps({"generated_at": "2026-05-28T15:33:46+00:00", **cached}))
    receipt_path.write_text(json.dumps({"recorded_at": "2026-05-28T16:00:00+00:00", **cached}))

    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", mission_index)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    status = trace._goal_roster_status(cwd=tmp_path)

    assert status["schema"] == "prompt_trace_mission_index_goal_roster_status_v1"
    assert status["staleness"]["status"] == "stale"
    assert status["staleness"]["kind"] == "roster_count_delta"
    assert status["staleness"]["refresh_recommended"] is True
    assert status["staleness"]["refresh_action"] == "refresh_now"
    assert status["staleness"]["refresh_priority"] == "high"
    assert status["staleness"]["count_delta_present"] is True
    assert status["staleness"]["metadata_lag_only"] is False
    assert status["staleness"]["counts_aligned"] is False
    assert status["staleness"]["full_mission_index_rewrite_required_for_count_accuracy"] is True
    assert status["staleness"]["refresh_recommendation"] == {
        "action": "refresh_now",
        "priority": "high",
        "reason": "goal roster counts, content, or projection anchors are stale",
        "counts_aligned": False,
        "metadata_lag_only": False,
        "content_delta_present": False,
        "full_mission_index_rewrite_required_for_count_accuracy": True,
    }
    assert "goal_authority_mtime_lag" in status["staleness"]["reasons"]
    assert "mission_index_goal_thread_count_delta" in status["staleness"]["reasons"]
    assert status["staleness"]["goal_authority_lag_ms"] == 1000000
    assert status["staleness"]["goal_thread_count_delta"] == 1
    assert status["current"]["goal_thread_count"] == 2
    assert status["mission_index"]["goal_thread_count"] == 1
    assert "rows" not in json.dumps(status)


def test_goal_roster_status_marks_mtime_only_lag(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    conn.execute(
        "insert into thread_goals values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "codex-thread-1",
            "goal-1",
            "Keep refining goal infrastructure.",
            "active",
            None,
            10,
            1,
            1779980000000,
            1779983000000,
        ),
    )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779983000.0, 1779983000.0))

    mission_index = tmp_path / "mission_index.json"
    receipt_path = tmp_path / "goal_roster_receipt.json"
    cached = {
        "goal_authority": {"mtime_ms": 1779982000000, "row_count": 1},
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
    }
    mission_index.write_text(json.dumps({"generated_at": "2026-05-28T15:33:46+00:00", **cached}))
    receipt_path.write_text(json.dumps({"recorded_at": "2026-05-28T16:00:00+00:00", **cached}))

    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", mission_index)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    status = trace._goal_roster_status(cwd=tmp_path)

    assert status["staleness"]["status"] == "stale"
    assert status["staleness"]["kind"] == "metadata_lag"
    assert status["staleness"]["refresh_recommended"] is True
    assert status["staleness"]["refresh_action"] == "refresh_when_metadata_freshness_matters"
    assert status["staleness"]["refresh_priority"] == "low"
    assert status["staleness"]["metadata_lag_only"] is True
    assert status["staleness"]["count_delta_present"] is False
    assert status["staleness"]["availability_issue_present"] is False
    assert status["staleness"]["counts_aligned"] is True
    assert status["staleness"]["full_mission_index_rewrite_required_for_count_accuracy"] is False
    assert status["staleness"]["refresh_recommendation"] == {
        "action": "refresh_when_metadata_freshness_matters",
        "priority": "low",
        "reason": "goal roster counts are aligned; only authority metadata mtime lags",
        "counts_aligned": True,
        "metadata_lag_only": True,
        "content_delta_present": False,
        "full_mission_index_rewrite_required_for_count_accuracy": False,
    }
    assert status["staleness"]["reasons"] == ["goal_authority_mtime_lag"]
    assert status["staleness"]["goal_thread_count_delta"] == 0
    assert status["staleness"]["goal_authority_lag_ms"] == 1000000


def test_goal_roster_status_ignores_mtime_lag_when_content_signature_matches(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    conn.execute(
        "insert into thread_goals values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "codex-thread-1",
            "goal-1",
            "Keep refining goal infrastructure.",
            "active",
            None,
            10,
            1,
            1779980000000,
            1779983000000,
        ),
    )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779983000.0, 1779983000.0))

    mission_index = tmp_path / "mission_index.json"
    receipt_path = tmp_path / "goal_roster_receipt.json"
    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    current_goals = trace._load_codex_thread_goals()
    cached_authority = trace._goal_authority_sources(current_goals)
    cached_authority["mtime_ms"] = 1779982000000
    cached = {
        "goal_authority": cached_authority,
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
    }
    mission_index.write_text(json.dumps({"generated_at": "2026-05-28T15:33:46+00:00", **cached}))
    receipt_path.write_text(json.dumps({"recorded_at": "2026-05-28T16:00:00+00:00", **cached}))

    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", mission_index)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    status = trace._goal_roster_status(cwd=tmp_path)

    assert status["staleness"]["status"] == "fresh"
    assert status["staleness"]["kind"] == "fresh"
    assert status["staleness"]["refresh_recommended"] is False
    assert status["staleness"]["reasons"] == []
    assert status["staleness"]["mtime_lag_without_content_delta"] is True
    assert status["staleness"]["content_delta_present"] is False
    assert status["staleness"]["goal_authority_lag_ms"] == 1000000


def test_trace_capsule_final_validation_uses_terminal_validation_rows() -> None:
    repeated = "./repo-pytest system/server/tests/test_example.py"
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, repeated, 1),
                _event(2, repeated, 0),
                _event(3, "python -m py_compile tools/example.py", 0),
            ]
        ),
        title="terminal validation test",
    )

    assert "final_validation: passed" in text
    assert "checks: pass=2 fail=1 other=0 total=3" in text
    assert "terminal_checks: pass=2 fail=0 other=0 total=2" in text
    assert meta["terminal_validation_count"] == 2
    assert meta["terminal_validation_fail_count"] == 0


def test_trace_capsule_keeps_needs_review_when_terminal_row_fails() -> None:
    repeated = "./repo-pytest system/server/tests/test_example.py"
    text, meta = render_trace_capsule_text(
        _turn([_event(1, repeated, 0), _event(2, repeated, 1)]),
        title="terminal validation fail test",
    )

    assert "final_validation: needs_review" in text
    assert "checks: pass=1 fail=1 other=0 total=2" in text
    assert "terminal_checks: pass=0 fail=1 other=0 total=1" in text
    assert meta["terminal_validation_fail_count"] == 1


def test_trace_capsule_separates_owner_pass_from_ambient_warnings() -> None:
    task_ledger_warning = (
        '{"validation_status":"valid_with_warnings",'
        '"error_count": 0,'
        '"warning_count": 36,'
        '"warning_classes":["historical_evidence_durability_backlog"]}'
    )
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, "./repo-pytest system/server/tests/test_root_readme_entry_orientation.py", 0, "3 passed"),
                _event(2, "./repo-python tools/meta/factory/task_ledger_apply.py validate", 1, task_ledger_warning),
            ]
        ),
        title="ambient warning validation test",
    )

    assert "final_validation: pass_with_external_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "ambient_validation: valid_with_warnings" in text
    assert "ambient_warning_class: historical_evidence_durability_backlog" in text
    assert "release_authority: none" in text
    assert meta["final_validation"] == "pass_with_external_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["ambient_warning_classes"] == ["historical_evidence_durability_backlog"]
    assert meta["external_terminal_warning_count"] == 1
    assert meta["blocking_terminal_failure_count"] == 0


def test_trace_capsule_buckets_residual_mentions_by_state(monkeypatch) -> None:
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        "microcosm_dogfood_paper_module_sidecar_claim": {
            "id": "microcosm_dogfood_paper_module_sidecar_claim",
            "state": "captured",
            "title": "Paper-module sidecar claim blocks clean Microcosm dogfood doctrine landing",
            "tags": ["microcosm", "paper_module_index"],
        },
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561": {
            "id": "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561",
            "state": "done",
            "title": "Trace capsule closeout report command leakage test failure",
            "tags": ["trace_capsule", "validation"],
        },
        "cap_finance_hourly_market_feed_schedule": {
            "id": "cap_finance_hourly_market_feed_schedule",
            "state": "signoff",
            "title": "Finance hourly market feed schedule",
            "tags": ["finance", "metabolismd", "scheduler"],
        },
        "cap_finance_next_natural_market_fire_schedule_observation": {
            "id": "cap_finance_next_natural_market_fire_schedule_observation",
            "state": "blocked",
            "title": "Observe next natural Oracle/Evolve finance market-fire schedule",
            "statement": "Observe the next natural market-clock fire after scheduler parity.",
            "tags": ["finance", "metabolismd", "scheduler", "residual_observation"],
            "satisfaction_contract": {
                "reentry_condition": "Next eligible natural market fire after scheduler parity."
            },
        },
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274": {
            "id": "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274",
            "state": "captured",
            "title": "Focused combined pytest wrapper hung after printing pass",
            "tags": ["validation_process", "pytest_wrapper", "trace_capsule"],
        },
    })
    receipt_text = "\n".join([
        "state/task_ledger/views/cap_cartography.json",
        "microcosm_dogfood_paper_module_sidecar_claim",
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561",
        "cap_finance_hourly_market_feed_schedule",
        "cap_finance_next_natural_market_fire_schedule_observation",
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274",
    ])

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_root_readme_entry_orientation.py", 0, "3 passed"),
            _event(2, "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --subject-id residuals", 0, receipt_text),
        ]),
        title="residual taxonomy test",
    )

    assert "open_product_residuals: microcosm_dogfood_paper_module_sidecar_claim" in text
    assert "open_validation_process_residuals: cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274" in text
    assert "cap_finance_hourly_market_feed_schedule" in text
    assert "closed_residuals_seen: cap_finance_hourly_market_feed_schedule,cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561" in text
    assert "blocked_external_observation_residuals: cap_finance_next_natural_market_fire_schedule_observation" in text
    assert "projection_or_view_artifacts_seen: cap_cartography.json" in text
    assert meta["open_product_residuals"] == ["microcosm_dogfood_paper_module_sidecar_claim"]
    assert meta["open_validation_process_residuals"] == [
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274"
    ]
    assert meta["closed_residuals_seen"] == [
        "cap_finance_hourly_market_feed_schedule",
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561"
    ]
    assert meta["blocked_external_observation_residuals"] == [
        "cap_finance_next_natural_market_fire_schedule_observation"
    ]
    assert meta["projection_or_view_artifacts_seen"] == ["cap_cartography.json"]


def test_trace_capsule_treats_signed_off_finance_caps_as_closed(monkeypatch) -> None:
    hourly_cap = "cap_finance_hourly_market_feed_schedule"
    body_floor_cap = "cap_microcosm_finance_eval_full_body_floor_gap"
    natural_fire_cap = "cap_finance_next_natural_market_fire_schedule_observation"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        hourly_cap: {
            "id": hourly_cap,
            "state": "signoff",
            "title": "Finance hourly market feed schedule",
            "tags": ["finance", "scheduler"],
        },
        body_floor_cap: {
            "id": body_floor_cap,
            "state": "signed_off",
            "title": "Microcosm finance eval body floor should cover the full macro finance spine",
            "tags": ["finance", "microcosm"],
        },
        natural_fire_cap: {
            "id": natural_fire_cap,
            "state": "blocked",
            "title": "Observe next natural Oracle/Evolve finance market-fire schedule",
            "statement": "Blocked on wall-clock evidence for the next natural market fire.",
            "tags": ["finance", "scheduler", "residual_observation"],
        },
    })
    receipt_text = "\n".join([
        hourly_cap,
        body_floor_cap,
        natural_fire_cap,
    ])

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-python tools/meta/factory/task_ledger_apply.py validate", 0, receipt_text),
        ]),
        title="finance readout hygiene test",
    )

    assert "open_product_residuals: none" in text
    assert f"closed_residuals_seen: {hourly_cap},{body_floor_cap}" in text
    assert f"blocked_external_observation_residuals: {natural_fire_cap}" in text
    assert meta["open_product_residuals"] == []
    assert meta["closed_residuals_seen"] == [hourly_cap, body_floor_cap]
    assert meta["blocked_external_observation_residuals"] == [natural_fire_cap]


def test_trace_capsule_validation_process_warning_does_not_block_owner_scope(monkeypatch) -> None:
    process_cap = "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        process_cap: {
            "id": process_cap,
            "state": "captured",
            "title": "Focused combined pytest wrapper hung after printing pass",
            "tags": ["validation_process", "pytest_wrapper", "trace_capsule"],
        },
    })
    wrapper_output = f"15 passed in 0.66s\nwrapper hung after printing pass\n{process_cap}"

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_cli_prompt_trace_capsule.py", 0, "6 passed"),
            _event(2, "./repo-pytest system/server/tests/test_cli_prompt_trace_capsule.py tests/test_microcosm_cold_entry_dogfood.py", 1, wrapper_output),
        ]),
        title="validation process warning test",
    )

    assert "final_validation: pass_with_validation_process_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "validation_process=needs_review" in text
    assert meta["final_validation"] == "pass_with_validation_process_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["validation_process_terminal_warning_count"] == 1
    assert meta["open_validation_process_residuals"] == [process_cap]


def test_trace_capsule_release_candidate_gate_ready_supersedes_historical_failure() -> None:
    release_receipt = """
    {
      "status": "pass",
      "authority_receipt": {
        "release_authorized": false,
        "wheel_install_supported": false
      },
      "projection_freshness_receipt": {"status": "pass"},
      "release_candidate_packet": {
        "candidate_state": "validated_release_candidate_pending_explicit_authorization",
        "candidate_identity": {
          "source": {
            "git_head": "3073d4dda1bbd50210fc7b8b34742e11d6fe95fa",
            "source_tree_state_kind": "git_head_clean",
            "dirty_source_path_count": 0
          },
          "artifact": {
            "artifact_payload_hash_sha256": "ac4a0c729be7feb91b3f107d28da48f34d08b89e404fce49d9f26e1f6bde92f1",
            "file_count": 2332,
            "payload_bytes": 84553842
          }
        },
        "release_authorization_gate_decision": {
          "decision": "ready_pending_operator_authorization",
          "release_authorization_allowed_now": false
        },
        "validation_summary": {
          "projection_freshness_status": "pass",
          "blocking_codes": []
        }
      }
    }
    """
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-pytest microcosm-substrate/tests/test_runtime_shell.py -q -k status_card",
                    1,
                    "AttributeError: missing project observe state write proof helper",
                ),
                _event(
                    2,
                    "PYTHONPATH=src python3 -m microcosm_core.release_export --root . --out /tmp/out --force",
                    0,
                    release_receipt,
                ),
            ],
            assistant_text=(
                "Validated clean-source release candidate; gate decision "
                "ready_pending_operator_authorization; release_authorized remains false."
            ),
        ),
        title="release candidate gate-ready status semantics test",
    )

    assert "final_validation: ready_pending_operator_authorization" in text
    assert "owner_scope_validation: pass" in text
    assert "internal_authorization: pending_operator_authorization" in text
    assert "public_release_authorization: pending_operator_authorization" in text
    assert "release_candidate_gate: ready_pending_operator_authorization" in text
    assert "historical_terminal_failures_superseded: 1" in text
    assert meta["final_validation"] == "ready_pending_operator_authorization"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["internal_authorization"] == "pending_operator_authorization"
    assert meta["public_release_authorization"] == "pending_operator_authorization"
    assert meta["release_candidate_gate_decision"] == "ready_pending_operator_authorization"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["raw_blocking_terminal_failure_count"] == 1


def test_trace_capsule_private_authorization_public_blocked_splits_gate_semantics() -> None:
    release_receipt = """
    {
      "status": "pass",
      "authority_receipt": {
        "release_authorized": false,
        "wheel_install_supported": false
      },
      "projection_freshness_receipt": {"status": "pass"},
      "source_tree_state_kind": "git_head_clean",
      "dirty_source_path_count": 0,
      "projection_freshness_status": "pass",
      "closeout_state": "systembar_slice_internal_authorization_satisfied_public_blocked",
      "release_authorization_gate_decision": {
        "decision": "ready_pending_operator_authorization",
        "release_authorization_allowed_now": false
      }
    }
    """
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-pytest system/server/tests/test_example.py",
                    1,
                    "AssertionError: historical pre-settlement failure",
                ),
                _event(
                    2,
                    "./repo-python tools/agent_trace_structurer/systembar_contract_test.py",
                    0,
                    "ok\nProcess exited with code 0",
                ),
                _event(
                    3,
                    "./repo-python tools/meta/factory/task_ledger_apply.py execution-receipt --work-item cap",
                    0,
                    release_receipt,
                ),
            ],
            assistant_text=(
                "Internal authorization satisfied for private/local/internal settlement; "
                "release gate text still says ready_pending_operator_authorization from an old projection. "
                "Public release remains blocked and no public push, deploy, release toggle, or external action was taken."
            ),
        ),
        title="private authorization public release blocked semantics test",
    )

    assert "final_validation: pass_with_public_release_blocked" in text
    assert "final_validation: ready_pending_operator_authorization" not in text
    assert "owner_scope_validation: pass" in text
    assert "internal_authorization: satisfied" in text
    assert "public_release_authorization: not_authorized_by_operator" in text
    assert "release_candidate_gate: public_release_blocked" in text
    assert "historical_terminal_failures_superseded: 1" in text
    assert "no public push" in text
    assert meta["final_validation"] == "pass_with_public_release_blocked"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["internal_authorization"] == "satisfied"
    assert meta["public_release_authorization"] == "not_authorized_by_operator"
    assert meta["release_candidate_gate_decision"] == "public_release_blocked"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["raw_blocking_terminal_failure_count"] == 1


def test_thread_closeout_report_omits_tools_and_interns_repeated_prompts() -> None:
    prompt = "same autonomous seed prompt"
    merged = merge_full_thread([
        _turn([_event(1, "./repo-pytest tests/test_one.py", 0)], turn_index=1, prompt_text=prompt, assistant_text="Wave one landed."),
        _turn([_event(1, "./repo-pytest tests/test_two.py", 0)], turn_index=2, prompt_text=prompt, assistant_text="Wave two landed."),
    ])

    text = render_thread_closeout_report(
        merged,
        title="Two autonomous seeds",
        intern_repeated_prompts=True,
    )

    assert "# Two autonomous seeds — Closeout Report" in text
    assert "`prompt_001`" in text
    assert "Wave one landed." in text
    assert "Wave two landed." in text
    assert "Exact closeout message" in text
    assert "./repo-pytest tests/test_one.py" not in text
