from __future__ import annotations

import json
from pathlib import Path

import pytest

from system.lib import work_ledger_runtime
from system.lib.active_execution_constellation import (
    build_active_execution_constellation,
    compact_active_execution_constellation_for_entry,
)
from system.lib.kernel.commands import navigate as kernel_navigate
from system.lib.kernel_navigation import NavigationResult
from system.lib.work_ledger_commands import WORK_LEDGER_SEED_SPEED_NO_HEARTBEAT_COMMAND


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_projection_marks_static_phase_dormant_when_runtime_has_no_active_phase(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-17T09:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "state/task_ledger/views/execution_menu_schedulable.json",
        {
            "kind": "task_ledger_view",
            "items": [
                {
                    "id": "cap_unrelated_live_campaign",
                    "title": "Unrelated live campaign",
                    "state": "shaping",
                    "work_item_type": "task",
                    "rank": 4,
                }
            ],
        },
    )
    _write_json(
        tmp_path / "state/work_ledger/active_claims_snapshot.json",
        {
            "schema": "work_ledger_active_claims_snapshot_v1",
            "generated_at": "2026-05-17T09:01:00+00:00",
            "counts": {
                "active_claims": 4,
                "effective_active_sessions": 2,
                "orphaned_active_sessions": 0,
                "claim_collisions": 0,
            },
            "active_claims": [
                {
                    "scope_kind": "path",
                    "scope_id": "a.py",
                    "path": "a.py",
                    "session_id": "session_a",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
                {
                    "scope_kind": "path",
                    "scope_id": "b.py",
                    "path": "b.py",
                    "session_id": "session_a",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
                {
                    "scope_kind": "path",
                    "scope_id": "c.py",
                    "path": "c.py",
                    "session_id": "session_b",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
                {
                    "scope_kind": "work_item_id",
                    "scope_id": "cap_other",
                    "work_item_id": "cap_other",
                    "session_id": "session_b",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
            ],
        },
    )

    payload = build_active_execution_constellation(
        tmp_path,
        active_phase={"active_phase_id": "09_54", "active_phase_title": "Static phase"},
    )

    assert payload["kind"] == "active_execution_constellation"
    assert payload["declared_anchor"]["status"] == "declared_anchor_runtime_dormant"
    assert payload["live_campaigns"][0]["workitem_id"] == "cap_unrelated_live_campaign"
    assert payload["live_sessions"]["counts"]["active_claims"] == 4
    assert payload["live_sessions"]["phase_claim_counts"]["09_54"] == 4
    assert payload["live_sessions"]["sessions"][0]["claim_count"] == 2
    assert payload["supervised_scope_candidates"][0]["requires_child_phase"] is False
    assert payload["stale_decorative_pointers"][0]["pointer"] == "active_phase"
    assert payload["projection_freshness"]["status"] in {"fresh", "stale"}
    assert payload["demotion_guard"]["closeable"] is False
    assert payload["demotion_guard"]["blockers"][0]["blocker_id"] == "phase_has_active_work_ledger_claims"
    topology = payload["demotion_guard"]["blocker_topology"]
    assert topology["claim_count"] == 4
    assert topology["bucket_counts"]["campaign_claim_misanchored_to_09_54"] == 4
    assert topology["bucket_counts"]["supervised_scope_candidate"] == 4
    assert payload["demotion_guard"]["blockers"][0]["bucket_counts"] == topology["bucket_counts"]
    assert payload["demotion_guard"]["blockers"][0]["safe_mutation_allowed"] is False


def test_projection_degrades_when_work_ledger_snapshot_is_missing(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-17T09:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "state/task_ledger/views/execution_menu_schedulable.json",
        {"kind": "task_ledger_view", "generated_at": "2026-05-17T09:00:30+00:00", "items": []},
    )

    payload = build_active_execution_constellation(
        tmp_path,
        active_phase={"active_phase_id": "09_54", "active_phase_title": "Static phase"},
    )

    assert payload["live_sessions"]["counts"]["active_claims"] == 0
    assert payload["live_sessions"]["source_freshness"]["status"] == "unavailable"
    assert payload["projection_freshness"]["status"] == "unavailable"
    assert payload["demotion_guard"]["closeable"] is False
    assert payload["demotion_guard"]["blockers"][0]["blocker_id"] == "work_ledger_claim_snapshot_not_decisive"


def test_projection_carries_owner_lane_first_policy_when_claims_are_live(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "phase_pipeline",
            "updated_at": "2026-05-17T09:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "state/task_ledger/views/execution_menu_schedulable.json",
        {"kind": "task_ledger_view", "generated_at": "2026-05-17T09:00:30+00:00", "items": []},
    )
    _write_json(
        tmp_path / "state/work_ledger/active_claims_snapshot.json",
        {
            "schema": "work_ledger_active_claims_snapshot_v1",
            "generated_at": "2026-05-17T09:01:00+00:00",
            "counts": {
                "active_claims": 1,
                "effective_active_sessions": 1,
                "orphaned_active_sessions": 0,
                "claim_collisions": 0,
            },
            "active_claims": [
                {
                    "scope_kind": "path",
                    "scope_id": "microcosm-substrate/src/microcosm_core/organs/live.py",
                    "path": "microcosm-substrate/src/microcosm_core/organs/live.py",
                    "session_id": "session_owner",
                    "actor": "codex",
                    "phase_id": "09_54_1",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                }
            ],
        },
    )

    payload = build_active_execution_constellation(
        tmp_path,
        active_phase={"active_phase_id": "09_54_1", "active_phase_title": "Static phase"},
        work_priority={
            "schema_version": "task_ledger_priority_constellation_v1",
            "view_counts": {
                "execution_menu_schedulable": 0,
                "unlock_pressure": 7,
            },
            "top_global_unlock_pressure_workitems": [
                {"id": "cap_hidden", "title": "Hidden pressure", "rank": 1}
            ],
        },
    )

    policy = payload["continuation_selection_policy"]
    assert policy["status"] == "owner_lane_first"
    assert policy["signals"]["active_claim_count"] == 1
    assert policy["signals"]["global_unlock_pressure_count"] == 7
    assert "global/hidden pressure" in policy["blocked_move"]

    compact = compact_active_execution_constellation_for_entry(payload)
    assert compact["continuation_selection_policy"]["status"] == "owner_lane_first"


def test_projection_carries_work_ledger_pass_awareness_cards(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-17T09:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "state/task_ledger/views/execution_menu_schedulable.json",
        {"kind": "task_ledger_view", "generated_at": "2026-05-17T09:00:30+00:00", "items": []},
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_heartbeat",
        actor="codex",
        phase_id="09_54",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_imported_without_heartbeat",
        actor="codex",
        phase_id="09_54",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_heartbeat",
        path="system/lib/live.py",
        lease_minutes=60,
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_imported_without_heartbeat",
        path="system/lib/imported.py",
        lease_minutes=60,
    )
    work_ledger_runtime.mark_session_pass_heartbeat(
        tmp_path,
        session_id="sess_heartbeat",
        pass_state="validating",
        current_pass_line="Validating the active-execution awareness strip.",
        last_pass_result_line="Added a Work Ledger claim and heartbeat.",
        scope_refs=["system/lib/live.py"],
    )
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    work_ledger_runtime.write_active_claims_snapshot(tmp_path, status)
    snapshot = _read_json(tmp_path / "state/work_ledger/active_claims_snapshot.json")

    payload = build_active_execution_constellation(
        tmp_path,
        active_phase={"active_phase_id": "09_54", "active_phase_title": "Static phase"},
    )

    awareness = payload["live_sessions"]["awareness_cards"]
    assert awareness[0]["session_id"] == "sess_heartbeat"
    assert awareness[0]["freshness_state"] == "live"
    assert awareness[0]["current_pass_line"] == "Validating the active-execution awareness strip."
    assert awareness[1]["session_id"] == "sess_imported_without_heartbeat"
    assert awareness[1]["source"] == "projected_unknown"
    assert payload["live_sessions"]["counts"]["claim_session_heartbeat_gap_count"] == 1
    assert (
        payload["live_sessions"]["drilldown_commands"]["seed_speed_no_heartbeat"]
        == WORK_LEDGER_SEED_SPEED_NO_HEARTBEAT_COMMAND
    )
    assert (
        payload["live_sessions"]["runtime_source_freshness"]["no_heartbeat_refresh_command"]
        == WORK_LEDGER_SEED_SPEED_NO_HEARTBEAT_COMMAND
    )
    heartbeat_gaps = payload["live_sessions"]["heartbeat_gap_claim_sessions"]
    assert heartbeat_gaps[0]["session_id"] == "sess_imported_without_heartbeat"
    assert heartbeat_gaps[0]["scope_ref"] == "system/lib/imported.py"
    assert (
        "session-heartbeat --session-id sess_imported_without_heartbeat"
        in heartbeat_gaps[0]["heartbeat_command"]
    )
    assert payload["live_sessions"]["runtime_source_freshness"]["freshness_status"] in {
        "fresh",
        "stale",
    }
    compact = compact_active_execution_constellation_for_entry(payload)
    assert compact["live_sessions"]["awareness_cards"][0]["pass_state"] == "validating"
    assert compact["live_sessions"]["counts"]["claim_session_heartbeat_gap_count"] == 1
    assert (
        compact["live_sessions"]["drilldown_commands"]["seed_speed_no_heartbeat"]
        == WORK_LEDGER_SEED_SPEED_NO_HEARTBEAT_COMMAND
    )
    assert (
        compact["live_sessions"]["heartbeat_gap_claim_sessions"][0]["session_id"]
        == "sess_imported_without_heartbeat"
    )
    assert (
        "session-heartbeat --session-id sess_imported_without_heartbeat"
        in compact["live_sessions"]["heartbeat_gap_claim_sessions"][0]["heartbeat_command"]
    )
    assert snapshot["seed_speed_hint"]["counts"]["claim_session_heartbeat_gap_count"] == 1
    assert snapshot["seed_speed_hint"]["first_action_kind"] == "choose_disjoint_write_lane"
    assert (
        "session-claims --refresh --session-summary"
        in snapshot["seed_speed_hint"]["first_action_command"]
    )


def test_projection_can_use_active_claims_sidecar_without_runtime_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-17T09:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "state/task_ledger/views/execution_menu_schedulable.json",
        {"kind": "task_ledger_view", "generated_at": "2026-05-17T09:00:30+00:00", "items": []},
    )
    _write_json(
        tmp_path / "state/work_ledger/active_claims_snapshot.json",
        {
            "schema": "work_ledger_active_claims_snapshot_v1",
            "generated_at": "2026-05-17T09:01:00+00:00",
            "counts": {
                "sessions_total": 12,
                "active_sessions": 3,
                "effective_active_sessions": 2,
                "orphaned_active_sessions": 1,
                "active_claims": 0,
                "claim_collisions": 0,
            },
            "seed_speed_hint": {
                "first_action": "Publish heartbeat for claim-owning seed sessions listed in heartbeat_gap_claim_sessions.",
                "first_action_kind": "heartbeat_gap",
                "first_action_command": "./repo-python tools/meta/factory/work_ledger.py session-heartbeat --session-id sess_fast_gap --state inspecting --current-pass-line '<public current pass>' --last-pass-result-line '<public previous result>' --scope-ref system/lib/fast.py",
                "first_action_ref": "heartbeat_gap_claim_sessions[0].heartbeat_command",
                "counts": {"claim_session_heartbeat_gap_count": 1},
                "heartbeat_gap_claim_sessions": [
                    {
                        "session_id": "sess_fast_gap",
                        "active_claim_count": 1,
                        "scope_ref": "system/lib/fast.py",
                        "heartbeat_command": "./repo-python tools/meta/factory/work_ledger.py session-heartbeat --session-id sess_fast_gap --state inspecting --current-pass-line '<public current pass>' --last-pass-result-line '<public previous result>' --scope-ref system/lib/fast.py",
                    }
                ],
            },
            "active_claims": [],
        },
    )

    def fail_runtime_status(_repo_root: Path) -> dict:
        raise AssertionError("sidecar fast path should not load runtime_status.json")

    monkeypatch.setattr(work_ledger_runtime, "load_runtime_status", fail_runtime_status)

    payload = build_active_execution_constellation(
        tmp_path,
        active_phase={"active_phase_id": "09_54", "active_phase_title": "Static phase"},
        include_runtime_status=False,
    )

    assert payload["live_sessions"]["counts"]["active_claims"] == 0
    assert payload["live_sessions"]["counts"]["effective_active_sessions"] == 2
    assert payload["live_sessions"]["counts"]["orphaned_active_sessions"] == 1
    assert payload["live_sessions"]["awareness_cards"] == []
    assert payload["live_sessions"]["runtime_source_freshness"]["status"] == "deferred_by_fast_path"
    assert payload["live_sessions"]["runtime_source_freshness"]["freshness_status"] == "not_checked"
    assert payload["live_sessions"]["heartbeat_gap_status"] == "cached_snapshot"
    assert payload["live_sessions"]["counts"]["claim_session_heartbeat_gap_count"] == 1
    assert payload["live_sessions"]["heartbeat_gap_claim_sessions"][0]["session_id"] == "sess_fast_gap"
    assert (
        "session-heartbeat --session-id sess_fast_gap"
        in payload["live_sessions"]["first_action_command"]
    )


def test_projection_reuses_supplied_work_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from system.lib import task_ledger_priority

    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-17T09:00:00+00:00",
        },
    )
    supplied_priority = {
        "schema_version": "task_ledger_priority_constellation_v1",
        "status": "ok",
        "top_ready_workitem": {"id": "cap_ready", "title": "Ready"},
    }
    priority_calls: list[Path] = []

    def record_priority_call(repo_root: Path) -> dict:
        priority_calls.append(repo_root)
        return {"status": "unexpected"}

    monkeypatch.setattr(task_ledger_priority, "priority_constellation", record_priority_call)

    payload = build_active_execution_constellation(
        tmp_path,
        active_phase={"active_phase_id": "09_54", "active_phase_title": "Static phase"},
        work_priority=supplied_priority,
    )

    assert priority_calls == []
    assert payload["work_priority"] == supplied_priority


def test_claim_topology_classifies_phase_claim_disposition(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-17T09:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "state/task_ledger/views/execution_menu_schedulable.json",
        {"kind": "task_ledger_view", "generated_at": "2026-05-17T09:00:30+00:00", "items": []},
    )
    _write_json(
        tmp_path / "state/work_ledger/active_claims_snapshot.json",
        {
            "schema": "work_ledger_active_claims_snapshot_v1",
            "generated_at": "2026-05-17T09:01:00+00:00",
            "counts": {"active_claims": 5, "effective_active_sessions": 3, "claim_collisions": 0},
            "active_claims": [
                {
                    "claim_id": "c1",
                    "scope_kind": "work_item_id",
                    "scope_id": "cap_dissemination_launch_surface_v0",
                    "work_item_id": "cap_dissemination_launch_surface_v0",
                    "session_id": "session_dissemination",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
                {
                    "claim_id": "c2",
                    "scope_kind": "path",
                    "scope_id": "docs/dissemination/public_launch_remaining_deliverables_v0.md",
                    "path": "docs/dissemination/public_launch_remaining_deliverables_v0.md",
                    "session_id": "session_dissemination",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
                {
                    "claim_id": "c3",
                    "scope_kind": "work_item_id",
                    "scope_id": "prompt_shelf_response_attention_prompt_armed_obligation_reducer",
                    "work_item_id": "prompt_shelf_response_attention_prompt_armed_obligation_reducer",
                    "session_id": "session_prompt",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
                {
                    "claim_id": "c4",
                    "scope_kind": "path",
                    "scope_id": "tools/meta/observability/prompt_shelf_chatgpt_observer.py",
                    "path": "tools/meta/observability/prompt_shelf_chatgpt_observer.py",
                    "session_id": "session_prompt",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
                {
                    "claim_id": "c5",
                    "scope_kind": "path",
                    "scope_id": "system/lib/active_execution_constellation.py",
                    "path": "system/lib/active_execution_constellation.py",
                    "session_id": "session_aec",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                },
            ],
        },
    )

    payload = build_active_execution_constellation(
        tmp_path,
        active_phase={"active_phase_id": "09_54", "active_phase_title": "Static phase"},
    )

    topology = payload["demotion_guard"]["blocker_topology"]
    assert topology["bucket_counts"]["true_09_54_dissemination"] == 2
    assert topology["bucket_counts"]["campaign_claim_misanchored_to_09_54"] == 2
    assert topology["bucket_counts"]["route_infrastructure_or_aec_cleanup"] == 1
    assert topology["bucket_counts"]["supervised_scope_candidate"] == 4
    assert topology["buckets"][0]["recommended_lane"].startswith("Keep 09_54 demotion blocked")


def test_entry_packet_routes_subphase_liveness_to_active_execution_constellation() -> None:
    from system.lib.kernel.commands import comprehension_snapshot

    payload = comprehension_snapshot.build_entry_packet(
        REPO_ROOT,
        task=(
            "active execution constellation replace stagnant 09_54 subphase pointer "
            "with WorkItem Work Ledger concurrency projection"
        ),
        context_budget=12000,
    )

    assert payload["recognized_situation"] == "active_execution_constellation"
    assert payload["selected_lane"]["lane_id"] == "active_execution_constellation"
    assert payload["next_action"]["command"] == "./repo-python kernel.py --pulse"
    assert payload["active_execution_constellation"]["kind"] == "active_execution_constellation"
    assert "declared_anchor" in payload["active_execution_constellation"]
    assert "projection_freshness" in payload["active_execution_constellation"]
    assert "demotion_guard" in payload["active_execution_constellation"]
    assert "blocker_topology" in payload["active_execution_constellation"]["demotion_guard"]
    assert (
        payload["active_execution_constellation"]["continuation_selection_policy"]["status"]
        in {"owner_lane_first", "task_ledger_schedulable_first", "support_or_capture"}
    )
    assert "claim_topology_summary" in payload["active_execution_constellation"]["live_sessions"]
    assert "claim_topology" not in payload["active_execution_constellation"]["live_sessions"]


def test_general_entry_packet_defers_active_execution_constellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from system.lib import active_execution_constellation
    from system.lib.kernel.commands import comprehension_snapshot

    def fail_if_built(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("active execution constellation should be lazy for general entry")

    monkeypatch.setattr(
        active_execution_constellation,
        "build_active_execution_constellation",
        fail_if_built,
    )

    payload = comprehension_snapshot.build_entry_packet(
        REPO_ROOT,
        task="write a focused local patch",
        context_budget=12000,
    )

    assert payload["recognized_situation"] != "active_execution_constellation"
    assert "active_execution_constellation" not in payload


def test_phase_summary_overlay_prefers_workitems_over_phase_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-21T05:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "state/task_ledger/views/execution_menu_schedulable.json",
        {
            "kind": "task_ledger_view",
            "generated_at": "2026-05-21T05:01:00+00:00",
            "items": [
                {
                    "id": "cap_hot_workitem",
                    "title": "Hot WorkItem",
                    "state": "shaping",
                    "work_item_type": "capture",
                    "rank": 3,
                }
            ],
        },
    )
    _write_json(
        tmp_path / "state/work_ledger/active_claims_snapshot.json",
        {
            "schema": "work_ledger_active_claims_snapshot_v1",
            "generated_at": "2026-05-21T05:02:00+00:00",
            "counts": {
                "active_claims": 1,
                "effective_active_sessions": 1,
                "orphaned_active_sessions": 0,
                "claim_collisions": 0,
            },
            "active_claims": [
                {
                    "scope_kind": "path",
                    "scope_id": "system/lib/live.py",
                    "path": "system/lib/live.py",
                    "session_id": "session_live",
                    "actor": "codex",
                    "phase_id": "09_54",
                    "leased_until": "2099-01-01T00:00:00+00:00",
                }
            ],
        },
    )
    monkeypatch.setattr(kernel_navigate.state, "REPO_ROOT", tmp_path, raising=False)

    result = NavigationResult(
        kind="kernel.navigate.phase",
        query={"command": "phase", "phase": "09_54"},
        payload={
            "phase": {
                "phase_id": "09_54",
                "phase_number": "09.54",
                "phase_title": "Static phase",
                "phase_dir": "obsidian/phase",
                "status": "authored",
                "execution_mode": "subagent_cohort",
                "current_wave_id": "wave_1",
            },
            "phase_card": {
                "active_wave": {
                    "wave_id": "wave_1",
                    "mode": "subagent_cohort",
                    "status": "active",
                    "target_paths": ["docs/phase_target.md"],
                }
            },
            "canonical_entry": {"path": "obsidian/phase/synth_seed.md"},
            "stage_guidance": {},
        },
        live_sources=[],
        derived_sources=[],
        suggested_next=[
            {
                "command": "./repo-python kernel.py --phase-step 09_54",
                "reason": "Preview phase step.",
            }
        ],
        warnings=[],
    )

    packet = kernel_navigate._phase_output_mode_packet(result, output_mode="summary")

    overlay = packet["payload"]["active_execution_overlay"]
    assert packet["summary"]["active_execution_status"] == "declared_anchor_runtime_dormant"
    assert overlay["liveness_summary"].startswith("Declared phase is contextual/dormant")
    assert overlay["authority_order"][:2] == [
        "Task Ledger WorkItems",
        "Work Ledger claims",
    ]
    assert overlay["live_campaigns"][0]["workitem_id"] == "cap_hot_workitem"
    assert overlay["live_sessions"]["counts"]["active_claims"] == 1
    assert packet["next"][0]["command"].endswith("--ids cap_hot_workitem")
    assert "phase-step" not in packet["next"][0]["command"]
    assert packet["next"][1]["command"].startswith(
        "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed"
    )


def test_pulse_latest_runtime_reuses_supplied_active_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_json(
        tmp_path / "tools/meta/control/orchestration_state.json",
        {
            "kind": "orchestration_state",
            "active_driver": "no_active_runtime_phase",
            "gate": {"gate_reason": "no_active_runtime_phase"},
            "updated_at": "2026-05-21T05:00:00+00:00",
            "drivers": {
                "phase_pipeline": {
                    "phase_id": "09_54",
                    "phase_dir": "obsidian/okay lets do this/09 - Raw-Seed Preservation",
                }
            },
        },
    )
    activation_calls: list[Path] = []
    bootstrap_calls: list[None] = []

    def record_activation_call(repo_root: Path) -> dict:
        activation_calls.append(repo_root)
        return {"phase_id": "unexpected"}

    def record_bootstrap_call() -> dict | None:
        bootstrap_calls.append(None)
        return None

    monkeypatch.setattr(kernel_navigate.state, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(kernel_navigate, "load_explicit_active_phase", record_activation_call)
    monkeypatch.setattr(kernel_navigate, "_pulse_active_phase_from_bootstrap_live", record_bootstrap_call)

    runtime = kernel_navigate._pulse_latest_runtime(
        exact=False,
        active_phase={
            "phase_id": "09_54",
            "phase_dir": "obsidian/okay lets do this/09 - Raw-Seed Preservation",
        },
    )

    assert activation_calls == []
    assert bootstrap_calls == []
    assert runtime is not None
    assert runtime["source"] == "persisted_orchestration_projection"
    assert runtime["state"] == "no_active_runtime_phase"


def test_annex_landing_summary_uses_bounded_index_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_path = tmp_path / "annexes" / "annex_distillation_index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        "\n".join(
            [
                "{",
                '  "kind": "annex_distillation_index",',
                '  "annex_count": 12,',
                '  "pattern_count": 20,',
                '  "distillation_status_counts": {"placeholder": 3},',
                '  "missing_distillation": [],',
                '  "by_axis": [THIS_SECTION_IS_NOT_PARSED_BY_PULSE],',
                '  "adoption_summary": {',
                '    "status_counts": {"adopted": 5, "evaluated": 6, "proposed": 7, "rejected": 1, "deferred": 1}',
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(kernel_navigate.state, "REPO_ROOT", tmp_path, raising=False)

    summary = kernel_navigate._pulse_annex_landing_summary()

    assert summary["available"] is True
    assert summary["total_patterns"] == 20
    assert summary["annex_count"] == 12
    assert summary["placeholder_count"] == 3
    assert summary["adopted_count"] == 5
    assert summary["landing_rate_pct"] == 25.0


def test_annex_landing_summary_cache_reuses_manifest_valid_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_path = tmp_path / "annexes" / "annex_distillation_index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text('{"pattern_count": 1, "adoption_summary": {}}', encoding="utf-8")
    monkeypatch.setattr(kernel_navigate.state, "REPO_ROOT", tmp_path, raising=False)
    calls = {"count": 0}

    def build_summary() -> dict:
        calls["count"] += 1
        return {
            "available": True,
            "total_patterns": 1,
            "adopted_count": 1,
            "evaluated_count": 0,
            "proposed_count": 0,
            "rejected_count": 0,
            "deferred_count": 0,
            "landing_rate_pct": 100.0,
            "under_fire": False,
        }

    monkeypatch.setattr(kernel_navigate, "_pulse_annex_landing_summary", build_summary)

    first, first_status = kernel_navigate._pulse_annex_landing_summary_cached()
    second, second_status = kernel_navigate._pulse_annex_landing_summary_cached()

    assert calls["count"] == 1
    assert first["landing_rate_pct"] == 100.0
    assert second["landing_rate_pct"] == 100.0
    assert first_status["status"] == "miss_built"
    assert second_status["status"] == "hit"


def test_pulse_snapshot_includes_active_execution_constellation(monkeypatch: pytest.MonkeyPatch) -> None:
    from system.lib.kernel.commands import navigate as kernel_navigate
    from system.lib.kernel import state as kernel_state

    def fail_runtime_status(_repo_root: Path) -> dict:
        raise AssertionError("pulse active-execution projection should use the sidecar fast path")

    kernel_state.init(REPO_ROOT)
    monkeypatch.setattr(kernel_state, "NAVIGATION_FULL_OUTPUT", False, raising=False)
    monkeypatch.setattr(kernel_navigate, "_pulse_recent_autonomous_fires", lambda limit=5: [])
    monkeypatch.setattr(kernel_navigate, "_pulse_ready_deferred_reactions", lambda limit=5: [])
    monkeypatch.setattr(work_ledger_runtime, "load_runtime_status", fail_runtime_status)
    snapshot = kernel_navigate._pulse_snapshot(exact=False)

    assert "active_execution_constellation" in snapshot
    assert snapshot["active_execution_constellation"]["schema_version"] == "active_execution_constellation_v0"
    assert "live_sessions" in snapshot["active_execution_constellation"]
    assert "demotion_guard" in snapshot["active_execution_constellation"]
