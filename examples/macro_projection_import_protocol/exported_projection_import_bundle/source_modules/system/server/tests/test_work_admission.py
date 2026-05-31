from __future__ import annotations

from system.lib import agent_observability, host_pressure as host_pressure_lib, work_admission


def _synthetic_queue_packet() -> dict:
    return {
        "summary": {
            "active_agents": 8,
            "pressure_index": 0.92,
            "bottleneck_class": "memory_pressure_swap_churn",
            "admission_default_decision": "queue_until_pressure_clears",
            "load_shed_recommended": True,
        },
        "mac_throttle_relief_governor": {
            "admission": {
                "requested_workload_class": "test_build",
                "decision": "queue_until_pressure_clears",
                "reason": "synthetic swap churn",
                "operator_override_required": False,
            },
        },
        "host": {
            "memory": {
                "memory_class": "swap_rising",
                "swap": {
                    "used_mb": 512.0,
                },
            },
        },
    }


def _synthetic_after_packet() -> dict:
    return {
        "summary": {
            "active_agents": 6,
            "pressure_index": 0.72,
            "progress_per_pressure": 66.0,
            "bottleneck_class": "cpu_saturated_but_productive",
        },
        "host": {
            "memory": {
                "memory_class": "normal",
                "swap": {
                    "used_mb": 128.0,
                },
            },
        },
    }


def _closed_coverage() -> dict:
    return {
        "summary": {
            "coverage_closure_status": "closed",
            "blocking_gap_count": 0,
        },
        "rows": [],
    }


def _owner_check_inventory_summary() -> dict:
    return {
        "candidate_safe_close_count": 0,
        "requires_owner_check_count": 5,
        "requires_owner_check_rss_mb": 640.0,
        "kind_counts": {
            "playwright_mcp": 5,
        },
    }


def test_host_pressure_admission_samples_process_rows_for_launch_gate(monkeypatch, tmp_path) -> None:
    trace_path = tmp_path / "state/observability/agent_trace/events.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text("", encoding="utf-8")
    calls: list[dict] = []

    class FakeTraceStore:
        def __init__(self, repo_root, *, max_history: int) -> None:
            self.repo_root = repo_root
            self.max_history = max_history

    def fake_packet_from_store(store, repo_root, **kwargs):
        calls.append({"store": store, "repo_root": repo_root, **kwargs})
        return {
            "summary": {"admission_default_decision": "allow"},
            "mac_throttle_relief_governor": {
                "admission": {
                    "requested_workload_class": kwargs["requested_workload_class"],
                    "decision": "allow",
                    "reason": "synthetic normal pressure",
                },
            },
        }

    monkeypatch.setattr(agent_observability, "AgentTraceStore", FakeTraceStore)
    monkeypatch.setattr(host_pressure_lib, "build_progress_pressure_packet_from_store", fake_packet_from_store)

    decision = work_admission.build_host_pressure_admission(
        tmp_path,
        workload_class="test_build",
    )

    assert calls
    assert calls[0]["include_processes"] is True
    assert decision["source"]["include_processes"] is True
    assert decision["source"]["process_rows_policy"] == "sampled_for_launch_gate"


def test_heavy_work_queues_under_synthetic_host_pressure(tmp_path) -> None:
    decision = work_admission.build_work_admission_decision(
        tmp_path,
        work_class=work_admission.VALIDATION_OR_BUILD,
        policy="auto",
        request_id="validation_batch",
        host_pressure_packet=_synthetic_queue_packet(),
        admission_consumer_coverage=_closed_coverage(),
    )

    assert decision["allow"] is False
    assert decision["result"] == "queue_until_pressure_clears"
    assert decision["new_heavy_work_launched"] is False


def test_cheap_read_remains_allowed_under_synthetic_host_pressure(tmp_path) -> None:
    decision = work_admission.build_work_admission_decision(
        tmp_path,
        work_class=work_admission.CHEAP_READ,
        policy="auto",
        request_id="read_summary",
        host_pressure_packet=_synthetic_queue_packet(),
        admission_consumer_coverage=_closed_coverage(),
    )

    assert decision["allow"] is True
    assert decision["result"] == "allow"
    assert decision["status"] == "cheap_or_attach_allowed"


def test_test_path_claim_classifies_as_light_edit_not_validation_launch() -> None:
    classification = work_admission.classify_work_creation_request(
        paths=[
            "system/lib/work_admission.py",
            "system/server/tests/test_work_admission.py",
        ],
    )

    assert classification["work_class"] == work_admission.EDIT_LIGHT_PATCH
    assert classification["heavy"] is False
    assert "not validation launches" in classification["reason"]


def test_explicit_test_plane_still_classifies_as_validation_work() -> None:
    classification = work_admission.classify_work_creation_request(
        paths=["system/server/tests/test_work_admission.py"],
        plane_home="test",
    )

    assert classification["work_class"] == work_admission.VALIDATION_OR_BUILD
    assert classification["heavy"] is True


def test_warn_policy_reports_blocked_result_but_admits(tmp_path) -> None:
    decision = work_admission.build_work_admission_decision(
        tmp_path,
        work_class=work_admission.PROJECTION_REBUILD,
        policy="warn",
        request_id="projection",
        host_pressure_packet=_synthetic_queue_packet(),
        admission_consumer_coverage=_closed_coverage(),
    )

    assert decision["allow"] is True
    assert decision["status"] == "warn_only"
    assert decision["blocked_result"] == "queue_until_pressure_clears"


def test_uncatalogued_heavy_work_requires_explicit_override(tmp_path) -> None:
    decision = work_admission.build_work_admission_decision(
        tmp_path,
        work_class=work_admission.UNCATALOGUED_HEAVY_WORK,
        policy="auto",
        request_id="new_launcher",
        admission_consumer_coverage=_closed_coverage(),
    )

    assert decision["allow"] is False
    assert decision["result"] == "explicit_override_required"
    assert decision["status"] == "blocked_uncatalogued_heavy_work"


def test_no_safe_close_routes_to_helper_budget_under_swap_pressure() -> None:
    decision = work_admission.build_pressure_budget_relief_decision(
        host_pressure_packet=_synthetic_queue_packet(),
        hygiene_receipt={"before": {"inventory_summary": _owner_check_inventory_summary()}},
        admission_coverage_summary=_closed_coverage()["summary"],
    )

    assert decision["status"] == "pressure_active_start_gate_working_no_safe_cleanup"
    assert decision["next_action"] == "resident_pressure_relief_owner_release_or_downshift"
    assert decision["safety"]["no_unknown_owner_killed"] is True
    assert decision["front_door_gate_sufficient_for_recovery"] is False


def test_helper_lease_queues_under_degraded_pressure(tmp_path) -> None:
    decision = work_admission.build_helper_lease_admission_decision(
        tmp_path,
        lease_kind=work_admission.PLAYWRIGHT_MCP,
        policy="auto",
        request_id="playwright_start",
        requested_by="codex_session",
        owner_status="active_session",
        host_pressure_packet=_synthetic_queue_packet(),
        inventory_summary=_owner_check_inventory_summary(),
    )

    assert decision["allow"] is False
    assert decision["result"] == "queue_until_pressure_clears"
    assert decision["new_helper_lease_started"] is False
    assert decision["safety"]["no_process_signal_sent"] is True


def test_helper_lease_queues_when_resident_budget_exhausted_under_normal_pressure(tmp_path) -> None:
    decision = work_admission.build_helper_lease_admission_decision(
        tmp_path,
        lease_kind=work_admission.PLAYWRIGHT_MCP,
        policy="auto",
        request_id="playwright_start",
        requested_by="codex_session",
        owner_status="active_session",
        host_pressure_packet=_synthetic_after_packet(),
        inventory_summary={
            "candidate_safe_close_count": 0,
            "requires_owner_check_count": 3,
            "requires_owner_check_rss_mb": 384.0,
            "active_owner_release_request_count": 1,
            "active_owner_release_rss_mb": 384.0,
            "kind_counts": {"playwright_mcp": 3},
        },
    )

    assert decision["allow"] is False
    assert decision["pressure_mode"] == "normal"
    assert decision["result"] == "queue_until_pressure_clears"
    assert decision["status"] == "blocked_resident_helper_budget_exhausted"
    assert decision["next_action"] == "reuse_existing_or_release_helper_before_start"
    assert decision["helper_lease_budget"]["normal_budget"] == 2
    assert decision["helper_lease_budget"]["resident_budget_exhausted"] is True
    assert decision["hygiene_summary"]["active_owner_release_request_count"] == 1
    assert decision["new_helper_lease_started"] is False
    assert decision["safety"]["no_process_signal_sent"] is True


def test_helper_lease_allows_when_resident_budget_available_under_normal_pressure(tmp_path) -> None:
    decision = work_admission.build_helper_lease_admission_decision(
        tmp_path,
        lease_kind=work_admission.PLAYWRIGHT_MCP,
        policy="auto",
        request_id="playwright_start",
        requested_by="codex_session",
        owner_status="active_session",
        host_pressure_packet=_synthetic_after_packet(),
        inventory_summary={
            "candidate_safe_close_count": 0,
            "requires_owner_check_count": 1,
            "requires_owner_check_rss_mb": 128.0,
            "kind_counts": {"playwright_mcp": 1},
        },
    )

    assert decision["allow"] is True
    assert decision["pressure_mode"] == "normal"
    assert decision["status"] == "allowed_by_pressure_budget"
    assert decision["helper_lease_budget"]["resident_budget_exhausted"] is False
    assert decision["new_helper_lease_started"] is None


def test_helper_lease_unknown_owner_requires_resolution_not_kill(tmp_path) -> None:
    decision = work_admission.build_helper_lease_admission_decision(
        tmp_path,
        lease_kind=work_admission.CHROME_DEVTOOLS_MCP,
        policy="auto",
        request_id="chrome_tool_start",
        requested_by=None,
        owner_status="unknown_parent",
        host_pressure_packet=_synthetic_queue_packet(),
        inventory_summary=_owner_check_inventory_summary(),
    )

    assert decision["allow"] is False
    assert decision["result"] == "require_owner_override"
    assert decision["next_action"] == "resolve_owner_before_helper_lease"
    assert decision["safety"]["no_unknown_owner_killed"] is True


def test_active_owner_release_request_does_not_kill() -> None:
    request = work_admission.build_helper_owner_release_request(
        process_kind=work_admission.PLAYWRIGHT_MCP,
        owner_status="active_session",
        rss_mb_total=512.0,
        target_owner="codex_session",
    )

    assert request["permitted_action"] == "ask_owner_to_release"
    assert request["requested_action"] == "release_tool_lease"
    assert request["result"] == "requested"
    assert request["safety"]["no_process_signal_sent"] is True
    assert request["safety"]["no_active_session_terminated"] is True


def test_unknown_owner_release_request_requires_resolution() -> None:
    request = work_admission.build_helper_owner_release_request(
        process_kind=work_admission.CODEX_STDIO_APP_SERVER,
        owner_status="unknown_parent",
        rss_mb_total=128.0,
    )

    assert request["permitted_action"] == "resolve_owner"
    assert request["requested_action"] == "resolve_owner_before_release"
    assert request["result"] == "owner_unresolved"
    assert request["safety"]["no_unknown_owner_killed"] is True


def test_owner_release_result_never_accepts_unknown_owner() -> None:
    request = work_admission.build_helper_owner_release_request(
        process_kind=work_admission.CODEX_STDIO_APP_SERVER,
        owner_status="unknown_parent",
        rss_mb_total=128.0,
    )

    result = work_admission.build_owner_release_result_receipt(
        release_request=request,
        result="accepted",
    )

    assert result["result"] == "owner_unresolved"
    assert result["release_confirmed"] is False
    assert result["safety"]["no_process_signal_sent"] is True


def test_background_loop_downshift_receipt_is_non_destructive() -> None:
    receipt = work_admission.build_background_loop_downshift_receipt(
        loop_kind=work_admission.AGENT_OBSERVABILITY_SAMPLER,
        owner_surface="system/server/main.py::agent_observability_sampler_loop",
        result="applied",
        duration_s=300,
    )

    assert receipt["schema"] == work_admission.BACKGROUND_LOOP_DOWNSHIFT_SCHEMA
    assert receipt["action"] == "lower_poll_rate"
    assert receipt["applied"] is True
    assert receipt["safety"]["no_active_session_terminated"] is True


def test_resident_relief_window_requires_resident_actuator() -> None:
    window = work_admission.build_resident_pressure_relief_window(
        before_packet=_synthetic_queue_packet(),
        blocked_work_starts=2,
        blocked_helper_leases=1,
    )

    assert window["verdict"] == "no_resident_actuator"
    assert window["front_door_blocks_not_counted_as_resident_relief"] is True
    assert window["actuators"]["resident_actuator_count"] == 0


def test_resident_relief_improved_requires_applied_resident_action() -> None:
    request = work_admission.build_helper_owner_release_request(
        process_kind=work_admission.PLAYWRIGHT_MCP,
        owner_status="active_session",
        rss_mb_total=512.0,
        target_owner="codex_session",
    )
    result = work_admission.build_owner_release_result_receipt(
        release_request=request,
        result="accepted",
    )
    downshift = work_admission.build_background_loop_downshift_receipt(
        loop_kind=work_admission.PROJECTION_REBUILD_LOOP,
        owner_surface="tools/meta/factory/build_paper_module_index.py",
        result="applied",
    )

    window = work_admission.build_resident_pressure_relief_window(
        before_packet=_synthetic_queue_packet(),
        after_packet=_synthetic_after_packet(),
        owner_release_results=[result],
        background_downshifts=[downshift],
    )

    assert window["verdict"] == "improved"
    assert window["actuators"]["resident_actuator_count"] == 2


def test_partial_relief_triggers_ladder_escalation() -> None:
    after = {
        "summary": {
            "active_agents": 7,
            "pressure_index": 0.93,
            "progress_per_pressure": 12.0,
            "bottleneck_class": "memory_pressure_swap_churn",
        },
        "host": {
            "memory": {
                "memory_class": "swap_rising",
                "swap": {"used_mb": 496.0},
            },
        },
    }
    downshift = work_admission.build_background_loop_downshift_receipt(
        loop_kind=work_admission.AGENT_OBSERVABILITY_SAMPLER,
        owner_surface="system/lib/agent_observability.py::AgentObservabilitySampler",
        result="applied",
    )

    window = work_admission.build_resident_pressure_relief_window(
        before_packet=_synthetic_queue_packet(),
        after_packet=after,
        background_downshifts=[downshift],
    )
    effect = work_admission.build_resident_relief_effect_receipt(
        relief_window=window,
        actuator_id=work_admission.AGENT_OBSERVABILITY_SAMPLER,
    )
    ladder = work_admission.build_resident_relief_ladder_state(
        host_pressure_packet=after,
        effect_receipts=[effect],
    )

    assert window["verdict"] == "partial_improved"
    assert effect["effect"] == "partial"
    assert effect["next_escalation_required"] is True
    assert ladder["next_action"] == "select_next_resident_actuator"
    assert ladder["selected_level"] == "level_2"


def test_owner_release_unsupported_not_counted_as_escalation_relief() -> None:
    request = work_admission.build_helper_owner_release_request(
        process_kind=work_admission.PLAYWRIGHT_MCP,
        owner_status="active_session",
        rss_mb_total=512.0,
        target_owner="codex_session",
    )
    result = work_admission.build_owner_release_result_receipt(
        release_request=request,
        result="unsupported",
    )
    previous = work_admission.build_resident_relief_effect_receipt(
        relief_window={
            "schema": work_admission.RESIDENT_PRESSURE_RELIEF_WINDOW_SCHEMA,
            "verdict": "partial_improved",
            "before": {"bottleneck_class": "memory_pressure_swap_churn"},
            "after": {"bottleneck_class": "memory_pressure_swap_churn"},
        },
        actuator_id=work_admission.AGENT_OBSERVABILITY_SAMPLER,
    )

    escalation = work_admission.build_resident_relief_escalation_window(
        previous_effect_receipt=previous,
        before_packet=_synthetic_queue_packet(),
        owner_release_results=[result],
    )

    assert escalation["verdict"] == "no_accepted_actuator"
    assert escalation["second_actuators"]["accepted_owner_releases"] == 0


def test_session_pressure_rank_prefers_low_progress_high_footprint() -> None:
    rank = work_admission.build_session_pressure_rank(
        [
            {
                "session_id": "productive",
                "owner_status": "active_session",
                "helper_rss_mb": 256.0,
                "recent_progress_units": 40.0,
                "active_claim_count": 4,
            },
            {
                "session_id": "idle-heavy",
                "owner_status": "active_session",
                "helper_rss_mb": 768.0,
                "recent_progress_units": 0.0,
                "idle_age_s": 900,
            },
        ]
    )

    assert rank["rows"][0]["session_id"] == "idle-heavy"
    assert rank["rows"][0]["candidate_action"] == "ask_release_tool_lease"
    assert rank["rows"][1]["candidate_action"] == "keep"


def test_session_yield_request_never_accepts_unknown_owner() -> None:
    receipt = work_admission.build_session_yield_request_receipt(
        target_id="unknown-session",
        owner_status="unknown_parent",
        requested_action="release_tool_lease",
        result="accepted",
    )

    assert receipt["result"] == "owner_unresolved"
    assert receipt["accepted"] is False
    assert receipt["safety"]["no_process_signal_sent"] is True


def test_requested_yield_does_not_count_as_accepted_relief() -> None:
    request = work_admission.build_session_yield_request_receipt(
        target_id="codex-session",
        request_id="syr-test",
        owner_status="active_session",
        requested_action="release_tool_lease",
        result="requested",
    )

    escalation = work_admission.build_resident_relief_escalation_window(
        previous_effect_receipt={},
        before_packet=_synthetic_queue_packet(),
        session_yield_results=[request],
    )

    assert request["accepted"] is False
    assert escalation["verdict"] == "no_accepted_actuator"
    assert escalation["second_actuators"]["accepted_session_yields"] == 0
    assert escalation["second_actuators"]["applied_session_yields"] == 0


def test_unknown_owner_cannot_accept_yield_result() -> None:
    request = work_admission.build_session_yield_request_receipt(
        target_id="unknown-session",
        request_id="syr-unknown",
        owner_status="unknown_parent",
        requested_action="release_tool_lease",
        result="requested",
    )

    result = work_admission.build_owner_yield_result_receipt(
        yield_request=request,
        result="accepted",
        applied_action="released_tool_lease",
    )

    assert result["result"] == "owner_unresolved"
    assert result["accepted"] is False
    assert result["applied"] is False
    assert result["applied_action"] == "none"
    assert result["safety"]["no_process_signal_sent"] is True


def test_accepted_applied_yield_counts_as_second_resident_actuator() -> None:
    request = work_admission.build_session_yield_request_receipt(
        target_id="station",
        request_id="syr-station",
        target_class="background_loop_owner",
        owner_status="active_session",
        requested_action="lower_poll_rate",
        result="requested",
    )
    result = work_admission.build_owner_yield_result_receipt(
        yield_request=request,
        result="accepted",
        applied_action="lowered_poll_rate",
    )

    escalation = work_admission.build_resident_relief_escalation_window(
        previous_effect_receipt={},
        before_packet=_synthetic_queue_packet(),
        session_yield_results=[result],
    )

    assert result["accepted"] is True
    assert result["applied"] is True
    assert escalation["verdict"] == "pending_recheck"
    assert escalation["second_actuators"]["applied_session_yields"] == 1


def test_session_yield_control_surface_separates_pending_and_applied() -> None:
    pending = work_admission.build_session_yield_request_receipt(
        target_id="codex-session",
        request_id="syr-pending",
        owner_status="active_session",
        result="requested",
    )
    accepted_request = work_admission.build_session_yield_request_receipt(
        target_id="station",
        request_id="syr-applied",
        target_class="background_loop_owner",
        owner_status="active_session",
        requested_action="lower_poll_rate",
        result="requested",
    )
    applied = work_admission.build_owner_yield_result_receipt(
        yield_request=accepted_request,
        result="accepted",
        applied_action="lowered_poll_rate",
    )

    surface = work_admission.build_session_yield_control_surface(
        request_events=[pending, accepted_request],
        result_events=[{"owner_yield_result": applied}],
    )

    assert surface["counts"]["pending_request_count"] == 1
    assert surface["counts"]["accepted_result_count"] == 1
    assert surface["counts"]["applied_result_count"] == 1
    assert surface["recovery_verdict"] == "accepted_actuator_available"


def test_escalation_window_requires_second_resident_actuator() -> None:
    previous = work_admission.build_resident_relief_effect_receipt(
        relief_window={
            "schema": work_admission.RESIDENT_PRESSURE_RELIEF_WINDOW_SCHEMA,
            "verdict": "partial_improved",
            "before": {"bottleneck_class": "memory_pressure_swap_churn"},
            "after": {"bottleneck_class": "memory_pressure_swap_churn"},
        },
        actuator_id=work_admission.AGENT_OBSERVABILITY_SAMPLER,
    )

    escalation = work_admission.build_resident_relief_escalation_window(
        previous_effect_receipt=previous,
        before_packet=_synthetic_queue_packet(),
    )

    assert escalation["verdict"] == "no_accepted_actuator"
    assert escalation["second_actuators"]["second_resident_actuator_count"] == 0
