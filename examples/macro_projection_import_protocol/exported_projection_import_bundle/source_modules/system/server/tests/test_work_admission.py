from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def _synthetic_resident_pressure_packet() -> dict:
    packet = _synthetic_queue_packet()
    packet["summary"] = {
        **packet["summary"],
        "resident_thread_count": 4,
        "resident_hot_active_claims": 1,
        "resident_warm_claim_quiet": 1,
        "resident_idle_unclaimed_over_10m": 2,
        "resident_idle_unclaimed_over_30m": 1,
        "resident_safe_to_nap": 2,
        "resident_safe_to_terminate_after_grace": 1,
        "resident_pressure_mode": "memory_pressure_swap_churn",
        "resident_projection_status": "available",
    }
    packet["resident_threads"] = {
        "schema_version": "resident_thread_pressure_projection_v0",
        "status": "available",
        "pressure_mode": "memory_pressure_swap_churn",
        "counts": {
            "resident_threads": 4,
            "hot_active_claims": 1,
            "warm_claim_quiet": 1,
            "idle_unclaimed_over_10m": 2,
            "idle_unclaimed_over_30m": 1,
            "safe_to_nap": 2,
            "safe_to_terminate_after_grace": 1,
        },
    }
    packet["load_shed"] = {
        "target_classes": [
            "resident_work_ledger_threads",
            "python_processes",
        ],
    }
    packet["load_shed_action_receipts"] = [
        {
            "target_class": "resident_work_ledger_threads",
            "action": "request_yield_or_nap_then_recheck",
            "kill_arbitrary_agents": False,
        }
    ]
    return packet


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


def test_host_pressure_admission_projects_resident_thread_relief(tmp_path) -> None:
    decision = work_admission.build_host_pressure_admission(
        tmp_path,
        workload_class="test_build",
        host_pressure_packet=_synthetic_resident_pressure_packet(),
    )

    assert decision["resident_relief_recommended"] is True
    assert decision["load_shed_target_classes"] == [
        "resident_work_ledger_threads",
        "python_processes",
    ]
    assert decision["resident_threads"]["status"] == "available"
    assert decision["resident_threads"]["resident_thread_count"] == 4
    assert decision["resident_threads"]["safe_to_nap"] == 2
    assert decision["resident_threads"]["safe_to_terminate_after_grace"] == 1
    assert decision["resident_threads"]["safe_relief_count"] == 4
    assert decision["summary"]["resident_thread_count"] == 4
    assert decision["summary"]["resident_safe_to_nap"] == 2
    assert decision["summary"]["resident_safe_to_terminate_after_grace"] == 1
    assert decision["summary"]["resident_projection_status"] == "available"
    assert decision["summary"]["resident_relief_recommended"] is True


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


def test_projection_suffix_write_profile_classifies_as_projection_rebuild() -> None:
    classification = work_admission.classify_work_creation_request(
        write_profiles=[{"profile": "microcosm_public_site_projection"}],
    )

    assert classification["work_class"] == work_admission.PROJECTION_REBUILD
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


def test_projection_settlement_remains_allowed_under_synthetic_host_pressure(tmp_path) -> None:
    decision = work_admission.build_work_admission_decision(
        tmp_path,
        work_class=work_admission.PROJECTION_SETTLEMENT,
        policy="auto",
        request_id="task_ledger_projection_settlement",
        host_pressure_packet=_synthetic_queue_packet(),
        admission_consumer_coverage=_closed_coverage(),
    )

    assert decision["allow"] is True
    assert decision["heavy"] is False
    assert decision["result"] == "allow"
    assert decision["status"] == "allowed_by_admission"
    assert decision["host_pressure_workload_class"] == "edit_light_patch"
    assert decision["host_pressure_decision"] == "queue_until_pressure_clears"


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


def test_dev_resource_broker_reuses_compatible_agent_only_resource(tmp_path) -> None:
    first = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.FRONTEND_DEV_SERVER,
        request_id="vite_start",
        requested_by="sess_a",
        fingerprint={"cwd": "web", "port": 5173, "command": "npm run dev", "host": "localhost"},
        host_pressure_packet=_synthetic_after_packet(),
    )
    existing = dict(first["lease"])
    existing["state"] = "running"

    second = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.FRONTEND_DEV_SERVER,
        request_id="vite_attach",
        requested_by="sess_b",
        fingerprint={"cwd": "web", "port": 5173, "command": "npm run dev", "host": "localhost"},
        existing_leases=[existing],
        host_pressure_packet=_synthetic_queue_packet(),
    )

    assert second["allow"] is True
    assert second["result"] == "reuse_existing"
    assert second["resource_action"] == "attach_existing_compatible_resource"
    assert second["lease_ref"] == existing["lease_id"]
    assert second["new_resource_started"] is False


def test_dev_resource_broker_refuses_unsafe_host_or_proxy(tmp_path) -> None:
    decision = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.BACKEND_API_SERVER,
        request_id="api_start",
        fingerprint={"host": "0.0.0.0", "port": 8000},
        unsafe_host_or_proxy=True,
        host_pressure_packet=_synthetic_after_packet(),
    )

    assert decision["allow"] is False
    assert decision["result"] == "refuse_unsafe_host_or_proxy"
    assert decision["safety"]["unsafe_host_or_proxy"] is True
    assert decision["new_resource_permitted"] is False


def test_dev_resource_broker_queues_new_resource_under_host_pressure(tmp_path) -> None:
    decision = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.PLAYWRIGHT_WEBSERVER,
        request_id="playwright_webserver",
        fingerprint={"cwd": "app", "port": 9323, "host": "localhost"},
        host_pressure_packet=_synthetic_queue_packet(),
    )

    assert decision["allow"] is False
    assert decision["status"] == "blocked_by_host_pressure"
    assert decision["resource_action"] == "queue_new_resource_start"
    assert decision["resource_queue_item"]["queue_reason"] == "host_pressure_blocks_new_dev_resource"


def test_dev_resource_projection_builder_uses_background_projection_admission(tmp_path) -> None:
    decision = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.GENERATED_PROJECTION_BUILDER,
        request_id="task_ledger_rebuild",
        fingerprint={"repo_root": str(tmp_path), "command": "task_ledger_apply rebuild"},
        host_pressure_packet=_synthetic_queue_packet(),
    )

    assert decision["allow"] is False
    assert decision["status"] == "blocked_by_host_pressure"
    assert decision["host_pressure_admission"]["work_class"] == work_admission.PROJECTION_REBUILD
    assert decision["host_pressure_admission"]["host_pressure_workload_class"] == "background_projection"
    assert decision["resource_queue_item"]["work_class"] == work_admission.PROJECTION_REBUILD


def test_dev_resource_projection_builder_can_request_projection_settlement(tmp_path) -> None:
    decision = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.GENERATED_PROJECTION_BUILDER,
        request_id="task_ledger_quick_capture_rebuild",
        fingerprint={
            "repo_root": str(tmp_path),
            "command": "task_ledger_apply quick-capture",
            "admission_work_class": work_admission.PROJECTION_SETTLEMENT,
        },
        exclusive_required=True,
        host_pressure_packet=_synthetic_queue_packet(),
    )

    assert decision["allow"] is True
    assert decision["status"] == "isolated_resource_permitted"
    assert decision["resource_work_class"] == work_admission.PROJECTION_SETTLEMENT
    assert decision["resource_work_class_source"] == "fingerprint.admission_work_class"
    assert decision["host_pressure_admission"]["work_class"] == work_admission.PROJECTION_SETTLEMENT
    assert decision["host_pressure_admission"]["host_pressure_workload_class"] == "edit_light_patch"
    assert decision["host_pressure_admission"]["allow"] is True


def test_dev_resource_broker_isolates_conflicting_same_port_resource(tmp_path) -> None:
    existing = {
        "schema": work_admission.DEV_RESOURCE_LEASE_SCHEMA,
        "lease_id": "lease_existing",
        "resource_kind": work_admission.FRONTEND_DEV_SERVER,
        "state": "running",
        "fingerprint": {"cwd": "web", "port": 5173, "command": "npm run dev"},
    }

    decision = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.FRONTEND_DEV_SERVER,
        request_id="vite_conflict",
        fingerprint={"cwd": "web", "port": 5173, "command": "pnpm dev --host localhost"},
        existing_leases=[existing],
        host_pressure_packet=_synthetic_after_packet(),
    )

    assert decision["allow"] is True
    assert decision["status"] == "isolated_resource_permitted"
    assert decision["resource_action"] == "start_isolated_resource"
    assert decision["conflict_count"] == 1


def test_dev_resource_broker_covers_projection_and_exact_copy_runners(tmp_path) -> None:
    for resource_kind in (
        work_admission.GENERATED_PROJECTION_BUILDER,
        work_admission.EXACT_COPY_REPAIR_RUNNER,
        work_admission.WATCHER,
    ):
        decision = work_admission.build_dev_resource_lease_decision(
            tmp_path,
            resource_kind=resource_kind,
            policy="off",
            request_id=f"{resource_kind}_start",
            fingerprint={
                "repo_root": str(tmp_path),
                "worktree": "main",
                "transaction_id": "mtx_1",
                "command": f"run {resource_kind}",
                "package_lock_hash": "sha256:lock",
                "env_hash": "sha256:env",
                "route": "projection",
                "backend": "local",
                "dirty_scope_hash": "sha256:dirty",
            },
        )

        assert decision["allow"] is True
        assert decision["requested_resource_kind"] == resource_kind
        assert decision["broker_contract"]["host_pressure_gates_new_resource_start"] is True


def test_dev_resource_broker_detects_conflicting_command_fingerprint_keys(tmp_path) -> None:
    existing = {
        "schema": work_admission.DEV_RESOURCE_LEASE_SCHEMA,
        "lease_id": "lease_existing_projection_builder",
        "resource_kind": work_admission.GENERATED_PROJECTION_BUILDER,
        "state": "running",
        "fingerprint": {
            "repo_root": str(tmp_path),
            "command": "build projections",
            "env_hash": "sha256:env-a",
        },
    }

    decision = work_admission.build_dev_resource_lease_decision(
        tmp_path,
        resource_kind=work_admission.GENERATED_PROJECTION_BUILDER,
        policy="off",
        request_id="projection_builder_conflict",
        fingerprint={
            "repo_root": str(tmp_path),
            "command": "build projections",
            "env_hash": "sha256:env-b",
        },
        existing_leases=[existing],
    )

    assert decision["allow"] is True
    assert decision["resource_action"] == "start_isolated_resource"
    assert decision["conflict_count"] == 1
    assert {"repo_root", "command"}.issubset(set(decision["conflicts"][0]["matched_keys"]))


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


def test_session_yield_request_accepts_settlement_actions() -> None:
    receipt = work_admission.build_session_yield_request_receipt(
        target_id="codex-session",
        target_class="settlement_obligation_owner",
        requested_action="release_after_landing",
        result="requested",
    )

    assert receipt["requested_action"] == "release_after_landing"
    assert receipt["target_class"] == "settlement_obligation_owner"
    assert receipt["accepted"] is False
    assert receipt["safety"]["no_process_signal_sent"] is True


def test_session_yield_coordination_request_builds_paste_ready_message() -> None:
    receipt = work_admission.build_session_yield_request_receipt(
        target_id="codex-target",
        request_id="syr-test",
        target_class="settlement_obligation_owner",
        requested_action="release_after_landing",
        result="requested",
    )

    brief = work_admission.build_session_yield_coordination_request(
        yield_request=receipt,
        requester_label="Batch5 integration closure thread",
        requester_session_id="codex-requester",
        blocked_on="microcosm_accepted_organ_admission_missing_companions",
        validation_status="Batch5 closure validation is green",
        held_paths=["microcosm-substrate/core/organ_atlas.json"],
        avoid_session_ids=["codex_certificate_owner"],
    )

    assert brief["schema"] == work_admission.SESSION_YIELD_COORDINATION_REQUEST_SCHEMA
    assert brief["request_id"] == "syr-test"
    assert brief["target_session_id"] == "codex-target"
    assert brief["held_paths"] == ["microcosm-substrate/core/organ_atlas.json"]
    assert "Batch5 integration closure thread" in brief["message"]
    assert "microcosm_accepted_organ_admission_missing_companions" in brief["message"]
    assert "codex_certificate_owner" in brief["message"]
    assert brief["acknowledgement_template"].startswith("Received.")
    assert "--applied-action landed_or_released_paths" in brief["result_command"]


def test_settlement_yield_result_can_count_as_applied() -> None:
    request = work_admission.build_session_yield_request_receipt(
        target_id="codex-session",
        request_id="syr-settlement",
        target_class="settlement_obligation_owner",
        requested_action="release_after_landing",
        result="requested",
    )

    result = work_admission.build_owner_yield_result_receipt(
        yield_request=request,
        result="accepted",
        applied_action="landed_or_released_paths",
    )

    assert result["status"] == "accepted_and_applied"
    assert result["applied"] is True
    assert result["applied_action"] == "landed_or_released_paths"

    surface = work_admission.build_session_yield_control_surface(
        request_events=[request],
        result_events=[{"owner_yield_result": result}],
    )
    assert surface["counts"]["applied_result_count"] == 1
    assert surface["counts"]["resident_applied_result_count"] == 0
    assert surface["accepted_actuator_count"] == 0


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
    assert surface["latest_request_cards"][0]["request_id"] == "syr-applied"
    assert surface["latest_request_cards"][0]["request_result"] == "requested"
    assert surface["latest_request_cards"][0]["result"] == "accepted"
    assert surface["latest_request_cards"][0]["accepted"] is True
    assert surface["latest_request_cards"][0]["applied"] is True
    assert surface["latest_request_cards"][0]["applied_action"] == "lowered_poll_rate"
    assert surface["latest_request_cards"][0]["pending"] is False
    assert surface["latest_request_cards"][0]["resolved"] is True
    assert surface["latest_request_cards"][0]["latest_result_status"] == "accepted_and_applied"
    assert surface["latest_request_cards"][1]["request_id"] == "syr-pending"
    assert surface["latest_request_cards"][1]["pending"] is True
    assert surface["latest_request_cards"][1]["resolved"] is False


def test_resident_relief_settlement_pending_and_fresh_heartbeat_are_not_effective() -> None:
    now = datetime(2026, 6, 3, 4, 0, tzinfo=timezone.utc)
    pending = work_admission.build_session_yield_request_receipt(
        target_id="quiet-session",
        request_id="syr-pending-settlement",
        owner_status="quiet_active_claim",
        result="requested",
        issued_at=(now - timedelta(minutes=5)).isoformat(),
    )
    fresh = work_admission.build_session_yield_request_receipt(
        target_id="fresh-session",
        request_id="syr-fresh-settlement",
        owner_status="quiet_active_claim",
        result="requested",
        issued_at=(now - timedelta(minutes=8)).isoformat(),
    )

    settlement = work_admission.build_resident_relief_settlement_window(
        request_events=[pending, fresh],
        runtime_status={
            "sessions": {
                "fresh-session": {
                    "session_id": "fresh-session",
                    "last_activity_at": (now - timedelta(minutes=1)).isoformat(),
                    "pass_heartbeat": {
                        "updated_at": (now - timedelta(minutes=1)).isoformat()
                    },
                }
            }
        },
        now=now,
        pending_ttl_s=30 * 60,
        output_profile="full",
    )

    by_request = {
        row["request_id"]: row for row in settlement["settlement_rows"]
    }
    assert settlement["counts"]["settled_effective_count"] == 0
    assert settlement["counts"]["pending_count"] == 1
    assert settlement["counts"]["superseded_by_fresh_activity_count"] == 1
    assert by_request["syr-pending-settlement"]["verdict"] == "request_pending"
    assert by_request["syr-fresh-settlement"]["verdict"] == "superseded_by_fresh_activity"


def test_resident_relief_settlement_marks_stale_pending_and_terminate_grace_escrow() -> None:
    now = datetime(2026, 6, 3, 4, 0, tzinfo=timezone.utc)
    stale = work_admission.build_session_yield_request_receipt(
        target_id="stale-claim-session",
        request_id="syr-stale-settlement",
        owner_status="quiet_active_claim",
        result="requested",
        issued_at=(now - timedelta(minutes=45)).isoformat(),
    )

    settlement = work_admission.build_resident_relief_settlement_window(
        request_events=[stale],
        runtime_status={
            "sessions": {
                "stale-claim-session": {
                    "session_id": "stale-claim-session",
                    "claims": [{"path": "system/lib/work_admission.py"}],
                }
            }
        },
        resident_thread_rows=[
            {
                "session_id": "idle-session",
                "recommended_action": "terminate_grace",
                "state": "idle_unclaimed",
                "quiet_for_s": 2700,
            }
        ],
        now=now,
        pending_ttl_s=30 * 60,
        output_profile="full",
    )

    assert settlement["status"] == "stale_pending_recheck_required"
    assert settlement["counts"]["stale_pending_count"] == 1
    assert settlement["counts"]["stale_claim_needs_demote_count"] == 1
    assert settlement["counts"]["terminate_grace_escrow_candidate_count"] == 1
    assert settlement["settlement_rows"][0]["verdict"] == "stale_claim_needs_demote"
    assert settlement["safety"]["terminate_grace_is_not_actuated"] is True
    assert settlement["safety"]["no_active_session_terminated"] is True


def test_resident_relief_settlement_counts_owner_applied_result_as_effective() -> None:
    now = datetime(2026, 6, 3, 4, 0, tzinfo=timezone.utc)
    request = work_admission.build_session_yield_request_receipt(
        target_id="nap-session",
        request_id="syr-effective-settlement",
        owner_status="idle_unclaimed",
        requested_action="yield",
        result="requested",
        issued_at=(now - timedelta(minutes=10)).isoformat(),
    )
    result = work_admission.build_owner_yield_result_receipt(
        yield_request=request,
        result="accepted",
        applied_action="yielded",
    )

    settlement = work_admission.build_resident_relief_settlement_window(
        request_events=[request],
        result_events=[{"owner_yield_result": result}],
        now=now,
        output_profile="full",
    )

    assert settlement["status"] == "relief_effective"
    assert settlement["counts"]["settled_effective_count"] == 1
    assert settlement["settlement_rows"][0]["verdict"] == "relief_effective"
    assert settlement["settlement_rows"][0]["evidence_type"] == "owner_result_applied"


def test_session_yield_control_surface_compact_profile_omits_coordination_bodies() -> None:
    request = work_admission.build_session_yield_request_receipt(
        target_id="codex-target",
        request_id="syr-compact",
        target_class="settlement_obligation_owner",
        owner_status="active_session",
        requested_action="release_after_landing",
        result="requested",
    )
    coordination = work_admission.build_session_yield_coordination_request(
        yield_request=request,
        requester_label="compact default test",
        blocked_on="same-path claim",
        validation_status="focused validation passed",
        held_paths=["tools/meta/factory/work_ledger.py", "system/lib/work_admission.py"],
    )
    body_marker = "FULL_COORDINATION_BODY_MARKER"
    coordination["message"] = f"{body_marker} " + coordination["message"]

    compact = work_admission.build_session_yield_control_surface(
        request_events=[{"session_yield_request": {**request, "coordination_request": coordination}}],
    )
    full = work_admission.build_session_yield_control_surface(
        request_events=[{"session_yield_request": {**request, "coordination_request": coordination}}],
        output_profile="full",
    )

    assert compact["output_profile"] == "compact"
    assert compact["latest_request_cards"][0]["request_id"] == "syr-compact"
    assert compact["latest_request_cards"][0]["coordination_body_omitted"] is True
    assert compact["latest_request_cards"][0]["held_paths_preview"] == [
        "tools/meta/factory/work_ledger.py",
        "system/lib/work_admission.py",
    ]
    assert body_marker not in str(compact)
    assert full["output_profile"] == "full"
    assert body_marker in str(full["latest_requests"][0]["coordination_request"]["message"])


def test_session_yield_inbox_filters_owner_requests_and_result_state() -> None:
    pending = work_admission.build_session_yield_request_receipt(
        target_id="codex-target",
        request_id="syr-pending",
        target_class="settlement_obligation_owner",
        requested_action="cede_path",
        owner_status="active_session",
        result="requested",
        issued_at="2026-06-01T21:03:16+00:00",
    )
    pending_brief = work_admission.build_session_yield_coordination_request(
        yield_request=pending,
        requester_label="codex_live_trace_projection_spine",
        requester_session_id="codex-live",
        blocked_on="line-disjoint backend hunk",
        validation_status="focused tests pass",
        held_paths=["system/server/main.py"],
        avoid_session_ids=["codex-live"],
        issued_at="2026-06-01T21:03:16+00:00",
    )
    resolved = work_admission.build_session_yield_request_receipt(
        target_id="codex-target",
        request_id="syr-resolved",
        target_class="settlement_obligation_owner",
        requested_action="release_after_landing",
        owner_status="active_session",
        result="requested",
    )
    other = work_admission.build_session_yield_request_receipt(
        target_id="codex-other",
        request_id="syr-other",
        owner_status="active_session",
        result="requested",
    )
    result = work_admission.build_owner_yield_result_receipt(
        yield_request=resolved,
        result="accepted",
        applied_action="landed_or_released_paths",
    )

    surface = work_admission.build_session_yield_inbox_surface(
        session_id="codex-target",
        request_events=[
            {"session_yield_request": {**pending, "coordination_request": pending_brief}},
            {"session_yield_request": other},
            {"session_yield_request": resolved},
        ],
        result_events=[{"owner_yield_result": result}],
        limit=5,
    )

    assert surface["schema"] == work_admission.SESSION_YIELD_INBOX_SURFACE_SCHEMA
    assert surface["counts"]["inbox_request_count"] == 2
    assert surface["counts"]["pending_request_count"] == 1
    assert surface["counts"]["resolved_request_count"] == 1
    assert surface["pending_requests"][0]["request_id"] == "syr-pending"
    assert surface["pending_requests"][0]["held_paths"] == ["system/server/main.py"]
    assert surface["pending_requests"][0]["requester_label"] == "codex_live_trace_projection_spine"
    assert "--applied-action ceded_path" in surface["pending_requests"][0]["result_command"]
    assert "session-yield-inbox --session-id codex-target" in surface["pending_requests"][0]["inbox_command"]
    assert surface["resolved_requests"][0]["latest_result_status"] == "accepted_and_applied"
    assert surface["transport_boundary"]["claude_code_delivery"] == "poll_disk_backed_inbox_or_shell_command"
    assert surface["recommended_commands"]["record_first_pending_result"].endswith(
        "--applied-action ceded_path"
    )


def test_session_yield_control_surface_tracks_generic_downshift_activity() -> None:
    downshift = work_admission.build_background_loop_downshift_receipt(
        loop_kind=work_admission.AGENT_OBSERVABILITY_SAMPLER,
        owner_surface="system/lib/agent_observability.py",
        result="applied",
        duration_s=900,
        effective_interval_s=60.0,
    )

    surface = work_admission.build_session_yield_control_surface(
        background_loop_downshift=downshift,
    )

    assert surface["background_downshift_active"] is True
    assert surface["background_downshift_expired"] is False
    assert surface["background_downshift_loop_kind"] == work_admission.AGENT_OBSERVABILITY_SAMPLER
    assert surface["background_downshift_status"]["active"] is True
    assert surface["background_downshift_expires_at"] is not None
    assert surface["station_downshift_active"] is False
    assert surface["accepted_actuator_count"] == 1
    assert surface["recovery_verdict"] == "accepted_actuator_available"

    expired = {
        **downshift,
        "issued_at": "2000-01-01T00:00:00+00:00",
        "duration_s": 1,
    }
    expired_surface = work_admission.build_session_yield_control_surface(
        background_loop_downshift=expired,
    )

    assert expired_surface["background_downshift_active"] is False
    assert expired_surface["background_downshift_expired"] is True
    assert expired_surface["accepted_actuator_count"] == 0
    assert expired_surface["recovery_verdict"] == "no_pending_request"


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
