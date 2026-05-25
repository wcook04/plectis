from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from system.lib.agent_observability_animation import (
    build_agent_observability_animation_delta,
    build_agent_observability_animation_scene,
)
from system.lib.agent_observability_animation_coverage import (
    build_agent_observability_animation_coverage,
)


NOW = datetime(2026, 5, 20, 22, 5, 10, tzinfo=timezone.utc)


def _event(
    seq: int,
    *,
    session_id: str,
    source_runtime: str,
    canonical_type: str,
    summary: str,
    tool_use_id: str | None = None,
    payload: dict | None = None,
    observed_at: str | None = None,
    artifact_refs: list[str] | None = None,
) -> dict:
    at = observed_at or f"2026-05-20T22:05:{seq:02d}+00:00"
    return {
        "id": f"{session_id}-ev-{seq}",
        "seq": seq,
        "schema": "1.0.0",
        "trace_id": session_id,
        "source_runtime": source_runtime,
        "source_event_name": canonical_type,
        "canonical_type": canonical_type,
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "artifact_refs": artifact_refs or [],
        "observed_at": at,
        "occurred_at": at,
        "summary": summary,
        "payload": payload or {},
    }


def _mixed_provider_events() -> list[dict]:
    return [
        _event(
            1,
            session_id="codex-live",
            source_runtime="codex_app",
            canonical_type="turn.prompt",
            summary="backend coverage pass",
        ),
        _event(
            2,
            session_id="codex-live",
            source_runtime="codex_app",
            canonical_type="tool.started",
            summary="Bash: pytest system/server/tests/test_agent_observability_animation.py",
            tool_use_id="codex-test-pass",
            payload={
                "tool_name": "Bash",
                "tool_input": {"command": "pytest system/server/tests/test_agent_observability_animation.py"},
            },
        ),
        _event(
            3,
            session_id="codex-live",
            source_runtime="codex_app",
            canonical_type="tool.completed",
            summary="pytest passed",
            tool_use_id="codex-test-pass",
            payload={"exit_code": 0},
        ),
        _event(
            4,
            session_id="codex-live",
            source_runtime="codex_app",
            canonical_type="tool.started",
            summary="Bash: pytest system/server/tests/test_missing_semantic.py",
            tool_use_id="codex-test-fail",
            payload={"tool_name": "Bash", "tool_input": {"command": "pytest system/server/tests/test_missing_semantic.py"}},
        ),
        _event(
            5,
            session_id="codex-live",
            source_runtime="codex_app",
            canonical_type="tool.completed",
            summary="pytest failed",
            tool_use_id="codex-test-fail",
            payload={"exit_code": 1},
        ),
        _event(
            6,
            session_id="codex-live",
            source_runtime="codex_app",
            canonical_type="permission.requested",
            summary="operator approval needed",
        ),
        _event(
            7,
            session_id="claude-stale",
            source_runtime="claude_code",
            canonical_type="turn.prompt",
            summary="edit backend route",
            observed_at="2026-05-20T22:00:01+00:00",
        ),
        _event(
            8,
            session_id="claude-stale",
            source_runtime="claude_code",
            canonical_type="tool.started",
            summary="Edit system/server/main.py",
            tool_use_id="claude-edit-main",
            payload={"tool_name": "Edit", "tool_input": {"file_path": "system/server/main.py"}},
            observed_at="2026-05-20T22:00:02+00:00",
        ),
        _event(
            9,
            session_id="claude-stale",
            source_runtime="claude_code",
            canonical_type="artifact.changed",
            summary="generated api projection",
            artifact_refs=["system/server/ui/src/api/generated/types.ts"],
            observed_at="2026-05-20T22:00:03+00:00",
        ),
    ]


def _status() -> dict:
    return {
        "schema": "1.0.0",
        "api_revision": "agent_observability_backend_v2",
        "trace_path": "state/observability/agent_trace/events.jsonl",
        "seq": 42,
        "history_size": 42,
        "max_history": 2000,
        "dropped_count": 1,
        "gap_count": 1,
        "persistence": {"enabled": True, "dropped_count": 1},
        "source_status": [],
        "active_sessions": [
            {
                "session_id": "codex-live",
                "source_runtime": "codex_app",
                "title": "Codex backend evaluator",
                "current_activity": "pytest",
                "last_observed_at": "2026-05-20T22:05:06+00:00",
                "last_canonical_type": "permission.requested",
                "cwd": "/repo",
                "lag_s": 4,
                "touched_files": ["system/lib/agent_observability_animation_coverage.py"],
            },
            {
                "session_id": "claude-stale",
                "source_runtime": "claude_code",
                "title": "Claude route edit",
                "current_activity": "Edit system/server/main.py",
                "last_observed_at": "2026-05-20T22:00:02+00:00",
                "last_canonical_type": "tool.started",
                "cwd": "/repo",
                "lag_s": 308,
                "touched_files": ["system/server/main.py"],
            },
        ],
        "canonical_counts": {},
        "source_counts": {},
    }


def _mission_status() -> dict:
    return {
        "missions": [
            {
                "session_id": "other-agent",
                "source_runtime": "codex_app",
                "active_claims": [
                    {
                        "claim_id": "claim-main",
                        "path": "system/server/main.py",
                        "scope_kind": "path",
                    }
                ],
            }
        ],
        "demoted_missions": [],
    }


def _expectations() -> dict[str, list[str]]:
    return {
        "providers": ["codex_app", "claude_code"],
        "channels": ["attention", "artifact", "file_io", "proof", "session_lifecycle"],
        "file_operations": ["generated", "write"],
        "claim_states": ["owned_by_other"],
        "generated_states": ["generated_projection", "source"],
        "proof_kinds": ["test"],
        "proof_statuses": ["fail", "pass", "observed"],
        "actor_statuses": ["stale", "waiting_operator"],
        "span_statuses": ["running"],
        "attention_kinds": ["event_error", "heartbeat", "waiting_for_operator"],
        "delta_op_types": [
            "counter_update",
            "event_append",
            "file_impact_upsert",
            "flow_upsert",
            "proof_receipt_upsert",
            "quality_update",
            "span_upsert",
        ],
    }


def _scene_and_delta() -> tuple[dict, dict]:
    events = _mixed_provider_events()
    status = _status()
    scene = build_agent_observability_animation_scene(
        events=events,
        status=status,
        mission_status=_mission_status(),
        now=NOW,
        window_ms=10 * 60 * 1000,
    )
    delta = build_agent_observability_animation_delta(
        events=events,
        status=status,
        mission_status=_mission_status(),
        now=NOW,
        window_ms=10 * 60 * 1000,
        since_seq=1,
        max_ops=500,
    )
    return scene, delta


def test_animation_coverage_accepts_mixed_provider_semantic_camera_contract() -> None:
    scene, delta = _scene_and_delta()

    coverage = build_agent_observability_animation_coverage(
        scene=scene,
        delta=delta,
        expectations=_expectations(),
    )

    assert coverage["kind"] == "agent_observability.animation_coverage"
    assert coverage["readiness"]["ready_for_first_live_visual_consumer"] is True
    assert coverage["readiness"]["frontend_string_heuristics_required"] is False
    assert coverage["coverage"]["events"]["semantic_fields"]["coverage"] == 1.0
    assert coverage["coverage"]["spans"]["count"] >= 1
    assert coverage["coverage"]["flows"]["count"] >= 1
    assert coverage["coverage"]["file_impacts"]["operation_counts"]["write"] == 1
    assert coverage["coverage"]["file_impacts"]["generated_state_counts"]["generated_projection"] == 1
    assert coverage["coverage"]["proof_receipts"]["status_counts"]["fail"] >= 1
    assert coverage["coverage"]["attention"]["kind_counts"]["heartbeat"] >= 1
    assert coverage["coverage"]["delta"]["snapshot_required"] is True
    assert coverage["coverage"]["delta"]["backpressure"]["degraded"] is True


def test_animation_coverage_does_not_depend_on_summary_strings() -> None:
    scene, delta = _scene_and_delta()
    stripped_scene = deepcopy(scene)
    stripped_delta = deepcopy(delta)
    for event in stripped_scene["events"]:
        event["summary"] = "classification text removed"
    for receipt in stripped_scene["proof_receipts"]:
        receipt["command_ref"] = "classification text removed"
    for op in stripped_delta["ops"]:
        payload = op.get("payload")
        if isinstance(payload, dict):
            payload["summary"] = "classification text removed"
            payload["command_ref"] = "classification text removed"

    original = build_agent_observability_animation_coverage(
        scene=scene,
        delta=delta,
        expectations=_expectations(),
    )
    stripped = build_agent_observability_animation_coverage(
        scene=stripped_scene,
        delta=stripped_delta,
        expectations=_expectations(),
    )

    assert stripped["readiness"] == original["readiness"]
    assert stripped["coverage"]["proof_receipts"]["kind_counts"] == original["coverage"]["proof_receipts"]["kind_counts"]
    assert stripped["coverage"]["file_impacts"]["operation_counts"] == original["coverage"]["file_impacts"]["operation_counts"]


def test_animation_coverage_reports_backend_gaps_that_would_force_ui_heuristics() -> None:
    scene, delta = _scene_and_delta()
    degraded_scene = deepcopy(scene)
    degraded_scene["proof_receipts"] = []
    degraded_scene["file_impacts"][0].pop("quality", None)

    coverage = build_agent_observability_animation_coverage(
        scene=degraded_scene,
        delta=delta,
        expectations=_expectations(),
    )

    assert coverage["readiness"]["ready_for_first_live_visual_consumer"] is False
    assert coverage["readiness"]["frontend_string_heuristics_required"] is True
    assert "proof_receipts_available" in coverage["readiness"]["missing_backend_semantics"]
    assert "file_impacts_available" in coverage["readiness"]["missing_backend_semantics"]
