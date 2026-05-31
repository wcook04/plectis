"""
[PURPOSE]
- Teleology: Verify runtime-control orchestration precedence, gate selection, and persisted control-plane artifacts for the server backend overnight/control-room surface.
- Mechanism: Patch orchestration lane drivers and snapshots, then assert that the synthesized state and persisted artifacts reflect the expected ownership, gate, and event-log contracts.

[INTERFACE]
- Tests: `build_orchestration_state` decision precedence plus `write_orchestration_artifacts` state, brief, and event-log persistence behavior.

[FLOW]
- Stub phase, factory, mission, documentation, and bridge-lock inputs with `monkeypatch`.
- Build orchestration state or write orchestration artifacts under `tmp_path`.
- Assert on active driver selection, gate reasoning, handoff metadata, and event-log deduplication.

[DEPENDENCIES]
- system.control.orchestration: Runtime-control authority surface under test.
- pytest monkeypatch fixture: Rebind lane drivers and snapshot loaders for deterministic scenarios.

[CONSTRAINTS]
- Tests only mutate temporary state under `tmp_path` or monkeypatched in-memory collaborators.
- Assertions focus on control-plane precedence and persistence contracts rather than TUI rendering.
- When-needed: Open when a server-backend regression touches orchestration gate precedence, control-room authority artifacts, or event-log deduplication.
- Escalates-to: system/control/orchestration.py::build_orchestration_state; system/control/orchestration.py::write_orchestration_artifacts; docs/orchestration_state.md
- Navigation-group: server_backend
"""

from __future__ import annotations

import json
from pathlib import Path

from system.control import orchestration


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_build_orchestration_state_blocks_on_factory_review_gate(monkeypatch) -> None:
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "results_processed",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Advance the phase loop.",
                "command": "python3 pipeline_advance.py --advance --bridge --provider chatgpt --launch-profile safe",
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 4,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "apply_review_pending",
            "blocked": True,
            "gate_reason": "apply_review_pending",
            "next_action": {"summary": "Review pending apply.", "command": None},
            "review_artifacts": ["obsidian/family/phase/pending_apply_checklist.md"],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "review_ready",
            "review_ready": True,
            "pending_apply": {"path": "obsidian/family/phase/pending_apply.json", "exists": True},
            "checklist_json": {"path": "obsidian/family/phase/pending_apply_checklist.json", "exists": True},
            "checklist_md": {"path": "obsidian/family/phase/pending_apply_checklist.md", "exists": True},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()
    sequence = state["decision"]["sequence"]

    assert state["active_driver"] == "manual_review"
    assert state["gate"]["gate_reason"] == "apply_review_pending"
    assert sequence[0]["mode"] == "manual_review"
    assert sequence[1]["mode"] == "phase_pipeline"
    assert sequence[1]["command"] == "python3 pipeline_advance.py --advance --bridge --provider chatgpt --launch-profile safe"
    assert "coordination" in state
    assert state["coordination"]["current_owner"]["actor_id"] == "human_operator"
    assert state["coordination"]["next_handoff"]["actor_id"] == "control_room_manager"


def test_build_orchestration_state_surfaces_phase_checkpoint_review_gate(monkeypatch) -> None:
    assimilate_command = "./repo-python kernel.py --phase-assimilate 09_35 --live"
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "results_processed",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Advance the phase loop.",
                "command": "python3 pipeline_advance.py --advance",
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "09_35",
            "phase_title": "Phase 09.35",
            "phase_dir": "obsidian/family/09.35",
            "family_dir": "obsidian/family",
            "cycle": 1,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "apply_review_pending",
            "blocked": True,
            "gate_reason": "phase_checkpoint_review_pending",
            "next_action": {
                "summary": "Review the landed phase checkpoint packet before continuing factory work.",
                "command": assimilate_command,
            },
            "review_artifacts": ["obsidian/family/phase/pending_apply_checklist.md"],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "review_ready",
            "review_ready": True,
            "source_kind": "phase_dock_response",
            "apply_cmd": assimilate_command,
            "invalid_reasons": [],
            "compiled_apply_ready": True,
            "apply_session_status": "success",
            "pending_apply": {"path": "obsidian/family/phase/pending_apply.json", "exists": True},
            "checklist_json": {"path": "obsidian/family/phase/pending_apply_checklist.json", "exists": True},
            "checklist_md": {"path": "obsidian/family/phase/pending_apply_checklist.md", "exists": True},
            "phase_runtime": {"latest_dock_status": {"path": "tools/meta/apply/phase_packets/09_35_dock_status.json"}},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()
    sequence = state["decision"]["sequence"]
    factory_driver = next(driver for driver in state["drivers"] if driver["driver_id"] == "factory_lane")

    assert state["active_driver"] == "manual_review"
    assert state["gate"]["gate_reason"] == "phase_checkpoint_review_pending"
    assert state["gate"]["review_ready"] is True
    assert state["decision"]["command"] == assimilate_command
    assert "phase-checkpoint review" in state["decision"]["summary"]
    assert sequence[0]["mode"] == "manual_review"
    assert sequence[0]["command"] == assimilate_command
    assert factory_driver["gate_reason"] == "phase_checkpoint_review_pending"
    assert factory_driver["next_action"]["command"] == assimilate_command


def test_build_orchestration_state_projects_python_std_compliance_lane(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "results_processed",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Advance phase.", "command": "python3 pipeline_advance.py --advance"},
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 4,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No factory work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {"packet_status": "missing_review_packet", "review_ready": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )
    monkeypatch.setattr(
        orchestration.reactions_runtime,
        "build_reactions_orchestration_projection",
        lambda repo_root: {"engine_armed": True, "engine_status": "armed", "awaiting_barriers": []},
    )
    coverage_path = tmp_path / "state" / "meta_missions" / "python_std_compliance_authoring" / "python_std_compliance_coverage.json"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T00:00:00+00:00",
                "coverage_path": "state/meta_missions/python_std_compliance_authoring/python_std_compliance_coverage.json",
                "counts": {
                    "findings_unapplied": 12,
                    "bins_pending": 3,
                    "active_campaigns": 1,
                    "campaigns_awaiting_approval": 1,
                    "blocked_campaigns": 0,
                },
                "triggers": {
                    "preview_kickoff_ready": False,
                    "drain_ready": False,
                    "approval_required": True,
                },
                "active_campaign": {
                    "campaign_slug": "demo",
                    "campaign_summary_path": "state/meta_missions/python_std_compliance_authoring/runs/demo/campaign_summary.json",
                    "lifecycle_state": "preview_ready",
                    "approve_command": "./repo-python tools/meta/factory/python_std_compliance_cycle.py --approve-campaign-summary state/meta_missions/python_std_compliance_authoring/runs/demo/campaign_summary.json --approved-by human_operator",
                },
                "campaigns": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    state = orchestration.build_orchestration_state(repo_root=tmp_path)
    brief = orchestration.build_orchestration_brief(state)
    rendered = orchestration.render_orchestration_brief(brief)

    assert state["python_std_compliance"]["stage"] == "preview_ready"
    assert state["python_std_compliance"]["gate"] == "approval_required"
    assert state["python_std_compliance"]["approval_needed"]["required"] is True
    assert "Python std compliance" in rendered
    assert "Python std approve command" in rendered


def test_build_orchestration_state_prefers_retryable_phase_gate(monkeypatch) -> None:
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "results_processed",
            "blocked": True,
            "gate_reason": "uncertainty_block",
            "next_action": {
                "summary": "Retry the controller gate.",
                "command": "python3 seed_pipeline.py --retry-gate --state 'obsidian/family/phase/pipeline_state.json'",
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 4,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": True,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Advance factory.", "command": "./repo-python tools/meta/factory/factory_runner.py --advance --provider chatgpt"},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "active",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Advance mission.", "command": "./repo-python tools/meta/factory/mission_runner.py --step --provider chatgpt"},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": True,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {"packet_status": "missing_review_packet", "review_ready": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()

    assert state["active_driver"] == "phase_pipeline"
    assert state["gate"]["gate_reason"] == "uncertainty_block"
    assert state["decision"]["command"] == "python3 seed_pipeline.py --retry-gate --state 'obsidian/family/phase/pipeline_state.json'"


def test_build_orchestration_state_hard_stops_when_no_active_runtime_phase(monkeypatch) -> None:
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "no_active_runtime_phase",
            "blocked": True,
            "gate_reason": "no_active_runtime_phase",
            "next_action": {
                "summary": "Re-arm the active phase so synth refresh and runtime state converge again.",
                "command": "python3 pipeline_overnight.py --phase 09_15 --wake-agent auto --sleep-policy keep_awake",
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/09.15/pipeline_state.json",
            "last_updated": None,
            "phase_ref": "09_15",
            "phase_title": "Phase 09.15",
            "phase_dir": "obsidian/family/09.15",
            "family_dir": "obsidian/family",
            "cycle": None,
            "needs_synth_refresh": False,
            "needs_reinit": True,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "apply_review_pending",
            "blocked": True,
            "gate_reason": "apply_review_pending",
            "next_action": {"summary": "Review pending apply.", "command": None},
            "review_artifacts": ["obsidian/legacy/08.5/pending_apply_checklist.md"],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {"packet_status": "review_ready", "review_ready": True},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()

    assert state["active_driver"] == "no_active_runtime_phase"
    assert state["gate"]["gate_reason"] == "no_active_runtime_phase"
    assert state["decision"]["command"] == "python3 pipeline_overnight.py --phase 09_15 --wake-agent auto --sleep-policy keep_awake"


def test_load_orchestration_state_rebuilds_stale_cached_active_phase_without_writing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "tools" / "meta" / "control" / "orchestration_state.json"
    _write_json(
        state_path,
        {
            "kind": "orchestration_state",
            "schema_version": "orchestration_state_v1",
            "active_driver": "phase_pipeline",
            "decision": {
                "immediate_mode": "phase_pipeline",
                "summary": "Stale phase runtime.",
                "command": "python3 pipeline_overnight.py --phase 09_35 --wake-agent auto --sleep-policy keep_awake",
                "launch_recommended_now": True,
                "sequence": [],
            },
            "drivers": [
                {
                    "driver_id": "phase_pipeline",
                    "phase_ref": "09_35",
                    "phase_dir": "obsidian/family/09.35",
                }
            ],
            "source_snapshots": {
                "phase_pipeline": {
                    "phase_ref": "09_35",
                    "phase_dir": "obsidian/family/09.35",
                }
            },
        },
    )
    _write_json(
        tmp_path / "obsidian" / "family" / "phase_family.json",
        {
            "family_id": "09",
            "family_number": "09",
            "family_dir": "obsidian/family",
            "active_phase_id": "09_37",
            "active_phase_number": "09.37",
            "active_phase_title": "Phase 09.37",
            "active_phase_dir": "obsidian/family/09.37",
            "active_phase_changed_at": "2026-04-22T00:00:00+00:00",
            "active_phase_source_command": "new-phase",
        },
    )
    rebuilt_state = {
        "kind": "orchestration_state",
        "schema_version": "orchestration_state_v1",
        "active_driver": "phase_pipeline",
        "decision": {
            "immediate_mode": "phase_pipeline",
            "summary": "Fresh active phase.",
            "command": "python3 pipeline_overnight.py --phase 09_37 --wake-agent auto --sleep-policy keep_awake",
            "launch_recommended_now": True,
            "sequence": [],
        },
        "source_snapshots": {
            "phase_pipeline": {
                "phase_ref": "09_37",
                "phase_dir": "obsidian/family/09.37",
            }
        },
    }
    build_calls: list[tuple[Path, str | None]] = []

    def fake_build_orchestration_state(*, repo_root: Path, phase_token: str | None = None) -> dict:
        build_calls.append((repo_root, phase_token))
        return rebuilt_state

    monkeypatch.setattr(orchestration, "build_orchestration_state", fake_build_orchestration_state)

    state = orchestration.load_orchestration_state(repo_root=tmp_path, refresh=False)
    persisted = json.loads(state_path.read_text(encoding="utf-8"))

    assert build_calls == [(tmp_path, None)]
    assert state["source_snapshots"]["phase_pipeline"]["phase_ref"] == "09_37"
    assert persisted["source_snapshots"]["phase_pipeline"]["phase_ref"] == "09_35"


def test_bridge_lock_precedence_blocks_new_launch(monkeypatch) -> None:
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "observe_dispatched",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Advance phase.", "command": "python3 pipeline_advance.py --advance --bridge --provider chatgpt --launch-profile safe"},
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 4,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Advance factory.", "command": "./repo-python tools/meta/factory/factory_runner.py --advance --provider chatgpt"},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {"packet_status": "missing_review_packet", "review_ready": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 1, "live_locks": [{"provider": "chatgpt"}]},
    )

    state = orchestration.build_orchestration_state()

    assert state["active_driver"] == "wait_existing_bridge"
    assert state["gate"]["gate_reason"] == "bridge_lock_owned"
    assert state["decision"]["launch_recommended_now"] is False


def test_build_orchestration_state_flags_invalid_review_packet(monkeypatch) -> None:
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "observe_plan_compiled",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Advance the phase loop.",
                "command": "python3 pipeline_overnight.py --phase 08_5 --wake-agent auto --sleep-policy keep_awake",
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 4,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "apply_review_pending",
            "blocked": True,
            "gate_reason": "apply_review_pending",
            "next_action": {"summary": "Review pending apply.", "command": None},
            "review_artifacts": ["obsidian/family/phase/pending_apply_checklist.md"],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "invalid_review_packet",
            "review_ready": False,
            "invalid_reasons": ["apply_session_failure"],
            "compiled_apply_ready": True,
            "apply_session_status": "failure",
            "pending_apply": {"path": "obsidian/family/phase/pending_apply.json", "exists": True},
            "checklist_json": {"path": "obsidian/family/phase/pending_apply_checklist.json", "exists": True},
            "checklist_md": {"path": "obsidian/family/phase/pending_apply_checklist.md", "exists": True},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()
    sequence = state["decision"]["sequence"]

    assert state["active_driver"] == "manual_review"
    assert state["gate"]["gate_reason"] == "invalid_review_packet"
    assert state["gate"]["review_ready"] is False
    assert sequence[0]["mode"] == "manual_review"
    assert "staged packet is invalid" in sequence[0]["summary"]
    assert sequence[0]["command"] == orchestration.FACTORY_STAGE_APPLY_COMMAND
    assert state["coordination"]["current_owner"]["actor_id"] == "human_operator"


def test_build_orchestration_state_routes_missing_phase_apply_source_to_phase_pipeline(monkeypatch) -> None:
    phase_command = "python3 pipeline_overnight.py --phase 08_5 --wake-agent auto --sleep-policy keep_awake"
    phase_status_command = "python3 seed_pipeline.py --status"
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "observe_plan_compiled",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Inspect the current phase-local state.",
                "command": phase_status_command,
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 4,
            "resume_command": phase_command,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "invalid_review_packet",
            "review_ready": False,
            "invalid_reasons": [
                "compiled_apply_not_ready",
                "apply_session_error",
                "phase_apply_source_missing",
            ],
            "compiled_apply_ready": False,
            "apply_session_status": "error",
            "apply_session_error": "no compiled apply-ready observe session found for active phase 08_5",
            "pending_apply": {"path": "obsidian/family/phase/pending_apply.json", "exists": True},
            "checklist_json": {"path": "obsidian/family/phase/pending_apply_checklist.json", "exists": True},
            "checklist_md": {"path": "obsidian/family/phase/pending_apply_checklist.md", "exists": True},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()
    sequence = state["decision"]["sequence"]
    factory_driver = next(driver for driver in state["drivers"] if driver["driver_id"] == "factory_lane")

    # The test name pins the contract: missing phase-apply source routes to
    # phase_pipeline, which is now what the orchestration state surfaces. The
    # earlier 'manual_review' expectation reflected a pre-routing-cleanup
    # snapshot; the live behavior puts the phase pipeline as the primary
    # active driver and exposes the phase_command via factory + sequence.
    assert state["active_driver"] == "phase_pipeline"
    assert sequence[0]["mode"] == "phase_pipeline"
    # The phase_command should still appear somewhere in the surface (via the
    # factory driver's next_action) so the operator can find the resume
    # entrypoint even though it is no longer the leading sequence command.
    assert factory_driver["next_action"]["command"] == phase_command


def test_build_orchestration_state_routes_stage_apply_failed_missing_apply_source_back_to_phase_resume(
    monkeypatch,
    tmp_path: Path,
) -> None:
    phase_command = "python3 pipeline_overnight.py --phase 08_5 --wake-agent auto --sleep-policy keep_awake"
    factory_dir = tmp_path / "tools/meta/factory"
    factory_dir.mkdir(parents=True)
    (factory_dir / "factory_state.json").write_text(
        json.dumps(
            {
                "kind": "factory_state",
                "stage": "stage_apply_failed",
                "errors": [
                    {
                        "step": "stage_apply",
                        "time": "2026-03-25T00:00:00+00:00",
                        "detail": "no compiled apply-ready observe session found for active phase 08_5",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "results_processed",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Resume the phase pipeline.", "command": phase_command},
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 4,
            "resume_command": phase_command,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "missing_review_packet",
            "review_ready": False,
            "invalid_reasons": [],
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state(repo_root=tmp_path)
    factory_driver = next(driver for driver in state["drivers"] if driver["driver_id"] == "factory_lane")

    assert state["active_driver"] == "phase_pipeline"
    assert state["decision"]["command"] == phase_command
    assert factory_driver["stage"] == "stage_apply_failed"
    assert factory_driver["next_action"]["command"] == phase_command
    assert "apply-ready session yet" in factory_driver["next_action"]["summary"]


def test_build_orchestration_state_prefers_synth_seed_phase_over_stale_factory_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    phase_command = "python3 pipeline_advance.py --advance"
    stale_factory_command = "python3 pipeline_overnight.py --phase 09_54_1 --wake-agent auto --sleep-policy keep_awake"
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "active": True,
            "stage": "synth_seed_emitted",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Advance one bounded step.", "command": phase_command},
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-05-30T14:45:00+00:00",
            "phase_ref": "09_54_1",
            "phase_title": "Phase 09.54.1",
            "phase_dir": "obsidian/family/phase",
            "family_dir": "obsidian/family",
            "cycle": 1,
            "resume_command": stale_factory_command,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(orchestration, "_load_phase_runtime_snapshot", lambda repo_root, phase_driver: {})
    monkeypatch.setattr(orchestration, "_load_python_std_compliance_projection", lambda repo_root: {})
    monkeypatch.setattr(
        orchestration.reactions_runtime,
        "build_reactions_orchestration_projection",
        lambda repo_root: {},
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "stage_apply_failed",
            "blocked": True,
            "gate_reason": "factory_step_failed",
            "next_action": {"summary": "Retry stale overnight lane.", "command": stale_factory_command},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-05-30T14:40:00+00:00",
            "active": True,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-05-30T14:40:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "missing_review_packet",
            "review_ready": False,
            "invalid_reasons": [],
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state(repo_root=tmp_path)
    phase_driver = next(driver for driver in state["drivers"] if driver["driver_id"] == "phase_pipeline")

    assert phase_driver["active"] is True
    assert state["active_driver"] == "phase_pipeline"
    assert state["decision"]["command"] == phase_command
    assert state["gate"]["owner_driver"] == "phase_pipeline"
    assert state["gate"]["active"] is False


def test_build_orchestration_state_routes_stale_phase_apply_packet_to_stage_apply_when_phase_dock_is_newer(
    monkeypatch,
    tmp_path: Path,
) -> None:
    phase_command = "python3 pipeline_overnight.py --phase 08_5 --wake-agent auto --sleep-policy keep_awake"
    phase_dir_rel = "obsidian/family/phase"
    phase_dir = tmp_path / phase_dir_rel
    phase_dir.mkdir(parents=True)
    (phase_dir / "pending_apply.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply",
                "staged_at": "2026-03-25T00:00:00+00:00",
                "compiled_apply": {
                    "ready": False,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply_checklist",
                "staged_at": "2026-03-25T00:00:00+00:00",
                "apply_session_result": {
                    "status": "error",
                    "error": "no compiled apply-ready observe session found for active phase 08_5",
                },
                "items": [
                    {"id": "apply_ops", "status": "fail"},
                    {"id": "active_phase", "status": "info"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.md").write_text("# Pending Apply Checklist\n", encoding="utf-8")
    factory_dir = tmp_path / "tools/meta/factory"
    factory_dir.mkdir(parents=True)
    (factory_dir / "factory_state.json").write_text(
        json.dumps(
            {
                "kind": "factory_state",
                "stage": "apply_review_pending",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    phase_packets_dir = tmp_path / "tools/meta/apply/phase_packets"
    phase_packets_dir.mkdir(parents=True)
    (phase_packets_dir / "08_5_dock_status.json").write_text(
        json.dumps(
            {
                "kind": "phase_dock_status",
                "updated_at": "2026-03-25T00:10:00+00:00",
                "status": "applied",
                "operation": "extract_subphase_seed",
                "dispatch": {
                    "status": "success",
                    "waves": [
                        {
                            "wave_index": 0,
                            "results": [
                                {
                                    "unit_id": "08_5.extract_subphase_seed",
                                    "status": "success",
                                    "provider": "chatgpt",
                                    "route": "phase_dock",
                                }
                            ],
                        }
                    ],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "observe_plan_compiled",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Inspect the current phase-local state.",
                "command": "python3 seed_pipeline.py --status",
            },
            "review_artifacts": [],
            "state_path": f"{phase_dir_rel}/pipeline_state.json",
            "last_updated": "2026-03-25T00:11:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": phase_dir_rel,
            "family_dir": "obsidian/family",
            "cycle": 4,
            "resume_command": phase_command,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state(repo_root=tmp_path)
    factory_driver = next(driver for driver in state["drivers"] if driver["driver_id"] == "factory_lane")
    apply_staging = state["artifacts"]["apply_staging"]

    assert state["active_driver"] == "manual_review"
    assert state["decision"]["command"] == orchestration.FACTORY_STAGE_APPLY_COMMAND
    assert "stale" in state["decision"]["summary"]
    assert factory_driver["next_action"]["command"] == orchestration.FACTORY_STAGE_APPLY_COMMAND
    assert apply_staging["stale_against_phase_runtime"] is True
    assert "stale_review_packet" in apply_staging["invalid_reasons"]
    assert state["artifacts"]["phase_runtime"]["latest_dock_status"]["path"] == "tools/meta/apply/phase_packets/08_5_dock_status.json"


def test_build_orchestration_state_surfaces_newer_phase_dock_failure_before_phase_rearm(
    monkeypatch,
    tmp_path: Path,
) -> None:
    phase_command = "python3 pipeline_overnight.py --phase 08_5 --wake-agent auto --sleep-policy keep_awake"
    phase_dir_rel = "obsidian/family/phase"
    phase_dir = tmp_path / phase_dir_rel
    phase_dir.mkdir(parents=True)
    (phase_dir / "pending_apply.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply",
                "staged_at": "2026-03-25T00:00:00+00:00",
                "compiled_apply": {
                    "ready": False,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply_checklist",
                "staged_at": "2026-03-25T00:00:00+00:00",
                "apply_session_result": {
                    "status": "error",
                    "error": "no compiled apply-ready observe session found for active phase 08_5",
                },
                "items": [
                    {"id": "apply_ops", "status": "fail"},
                    {"id": "active_phase", "status": "info"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.md").write_text("# Pending Apply Checklist\n", encoding="utf-8")
    factory_dir = tmp_path / "tools/meta/factory"
    factory_dir.mkdir(parents=True)
    (factory_dir / "factory_state.json").write_text(
        json.dumps(
            {
                "kind": "factory_state",
                "stage": "apply_review_pending",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    phase_packets_dir = tmp_path / "tools/meta/apply/phase_packets"
    phase_packets_dir.mkdir(parents=True)
    (phase_packets_dir / "08_5_dock_status.json").write_text(
        json.dumps(
            {
                "kind": "phase_dock_status",
                "updated_at": "2026-03-25T00:10:00+00:00",
                "status": "error",
                "operation": "extract_subphase_seed",
                "dispatch": {
                    "status": "error",
                    "waves": [
                        {
                            "wave_index": 0,
                            "results": [
                                {
                                    "unit_id": "08_5.extract_subphase_seed",
                                    "status": "error",
                                    "error": "Chrome launched but CDP endpoint did not become ready",
                                    "error_category": "cdp_unreachable",
                                    "error_stage": "browser_connect",
                                    "provider": "chatgpt",
                                    "route": "phase_dock",
                                }
                            ],
                        }
                    ],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "observe_plan_compiled",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Inspect the current phase-local state.",
                "command": "python3 seed_pipeline.py --status",
            },
            "review_artifacts": [],
            "state_path": f"{phase_dir_rel}/pipeline_state.json",
            "last_updated": "2026-03-25T00:11:00+00:00",
            "phase_ref": "08_5",
            "phase_title": "Phase 08.5",
            "phase_dir": phase_dir_rel,
            "family_dir": "obsidian/family",
            "cycle": 4,
            "resume_command": phase_command,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state(repo_root=tmp_path)
    factory_driver = next(driver for driver in state["drivers"] if driver["driver_id"] == "factory_lane")
    apply_staging = state["artifacts"]["apply_staging"]

    assert state["active_driver"] == "manual_review"
    assert state["decision"]["command"] == phase_command
    assert "browser_connect" in state["decision"]["summary"]
    assert "cdp_unreachable" in state["decision"]["summary"]
    assert state["decision"]["sequence"][0]["path"] == "tools/meta/apply/phase_packets/08_5_dock_status.json"
    assert factory_driver["next_action"]["command"] == phase_command
    assert "phase_dock_failed_after_packet" in apply_staging["invalid_reasons"]
    assert apply_staging["latest_phase_dock_error"]["error_category"] == "cdp_unreachable"
    assert apply_staging["latest_phase_dock_error"]["error_stage"] == "browser_connect"


def test_load_apply_staging_snapshot_marks_failed_apply_session_invalid(tmp_path: Path) -> None:
    phase_dir = tmp_path / "obsidian/family/phase"
    phase_dir.mkdir(parents=True)
    (phase_dir / "pending_apply.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply",
                "compiled_apply": {
                    "ready": True,
                    "preview_command": "./repo-python kernel.py --apply obsidian/family/phase/pending_apply.json",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply_checklist",
                "apply_session_result": {"status": "failure"},
                "items": [
                    {"id": "apply_ops", "status": "review"},
                    {"id": "active_phase", "status": "info"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.md").write_text("# Pending Apply Checklist\n", encoding="utf-8")

    snapshot = orchestration._load_apply_staging_snapshot(tmp_path, "obsidian/family/phase")

    assert snapshot["packet_status"] == "invalid_review_packet"
    assert snapshot["review_ready"] is False
    assert snapshot["compiled_apply_ready"] is True
    assert snapshot["apply_session_status"] == "failure"
    assert "apply_session_failure" in snapshot["invalid_reasons"]


def test_load_apply_staging_snapshot_marks_missing_phase_apply_source_invalid(tmp_path: Path) -> None:
    phase_dir = tmp_path / "obsidian/family/phase"
    phase_dir.mkdir(parents=True)
    (phase_dir / "pending_apply.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply",
                "compiled_apply": {
                    "ready": False,
                    "preview_command": "./repo-python kernel.py --apply obsidian/family/phase/pending_apply.json",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply_checklist",
                "apply_session_result": {
                    "status": "error",
                    "error": "no compiled apply-ready observe session found for active phase 08_5",
                },
                "items": [
                    {"id": "apply_ops", "status": "fail"},
                    {"id": "active_phase", "status": "info"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.md").write_text("# Pending Apply Checklist\n", encoding="utf-8")

    snapshot = orchestration._load_apply_staging_snapshot(tmp_path, "obsidian/family/phase")

    assert snapshot["packet_status"] == "invalid_review_packet"
    assert snapshot["review_ready"] is False
    assert snapshot["compiled_apply_ready"] is False
    assert snapshot["apply_session_status"] == "error"
    assert snapshot["apply_session_error"] == "no compiled apply-ready observe session found for active phase 08_5"
    assert "phase_apply_source_missing" in snapshot["invalid_reasons"]


def test_load_apply_staging_snapshot_accepts_phase_dock_review_source(tmp_path: Path) -> None:
    phase_dir = tmp_path / "obsidian/family/phase"
    phase_dir.mkdir(parents=True)
    staged_at = "2026-03-25T23:29:08.037695+00:00"
    (phase_dir / "pending_apply.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply",
                "staged_at": staged_at,
                "source_kind": "phase_dock_response",
                "apply_cmd": "./repo-python kernel.py --phase-assimilate 08_5 --live",
                "compiled_apply": {
                    "ready": True,
                    "source_kind": "phase_dock_response",
                    "already_applied": True,
                    "phase_dock_status_path": "tools/meta/apply/phase_packets/08_5_dock_status.json",
                    "phase_dock_response_path": "tools/meta/apply/phase_packets/08_5_deposit_response.json",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply_checklist",
                "staged_at": staged_at,
                "apply_session_result": {
                    "status": "success",
                    "source_kind": "phase_dock_response",
                    "review_command": "./repo-python kernel.py --phase-assimilate 08_5 --live",
                },
                "items": [
                    {"id": "apply_ops", "status": "review"},
                    {"id": "active_phase", "status": "info"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.md").write_text("# Pending Apply Checklist\n", encoding="utf-8")

    snapshot = orchestration._load_apply_staging_snapshot(tmp_path, "obsidian/family/phase")

    assert snapshot["packet_status"] == "review_ready"
    assert snapshot["review_ready"] is True
    assert snapshot["compiled_apply_ready"] is True
    assert snapshot["apply_session_status"] == "success"
    assert snapshot["invalid_reasons"] == []


def test_load_apply_staging_snapshot_marks_assimilated_phase_checkpoint_stale(tmp_path: Path) -> None:
    phase_dir = tmp_path / "obsidian/family/phase"
    phase_dir.mkdir(parents=True)
    staged_at = "2026-03-25T23:29:08.037695+00:00"
    (phase_dir / "pending_apply.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply",
                "staged_at": staged_at,
                "source_kind": "phase_dock_response",
                "apply_cmd": "./repo-python kernel.py --phase-assimilate 08_5 --live",
                "compiled_apply": {
                    "ready": True,
                    "source_kind": "phase_dock_response",
                    "already_applied": True,
                    "phase_dock_status_path": "tools/meta/apply/phase_packets/08_5_dock_status.json",
                    "phase_dock_response_path": "tools/meta/apply/phase_packets/08_5_deposit_response.json",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply_checklist",
                "staged_at": staged_at,
                "apply_session_result": {
                    "status": "success",
                    "source_kind": "phase_dock_response",
                    "review_command": "./repo-python kernel.py --phase-assimilate 08_5 --live",
                },
                "items": [
                    {"id": "apply_ops", "status": "review"},
                    {"id": "active_phase", "status": "info"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.md").write_text("# Pending Apply Checklist\n", encoding="utf-8")

    snapshot = orchestration._load_apply_staging_snapshot(
        tmp_path,
        "obsidian/family/phase",
        phase_runtime={
            "phase_step_preview": {
                "wave_status": "assimilated",
                "action": "assimilate_ready",
                "checkpoint_ready": True,
            }
        },
    )

    assert snapshot["packet_status"] == "invalid_review_packet"
    assert snapshot["review_ready"] is False
    assert snapshot["stale_against_phase_runtime"] is True
    assert snapshot["phase_checkpoint_consumed"] is True
    assert "phase_checkpoint_already_assimilated" in snapshot["invalid_reasons"]


def test_load_apply_staging_snapshot_marks_stale_packet_invalid(tmp_path: Path) -> None:
    phase_dir = tmp_path / "obsidian/family/phase"
    phase_dir.mkdir(parents=True)
    (tmp_path / "tools/meta/factory").mkdir(parents=True)
    (tmp_path / "tools/meta/factory/factory_state.json").write_text(
        json.dumps(
            {
                "kind": "factory_state",
                "stage": "apply_review_pending",
                "last_stage_apply": "2026-03-25T23:30:08.037695+00:00",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    staged_at = "2026-03-25T23:29:08.037695+00:00"
    (phase_dir / "pending_apply.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply",
                "staged_at": staged_at,
                "compiled_apply": {
                    "ready": True,
                    "preview_command": "./repo-python kernel.py --apply obsidian/family/phase/pending_apply.json",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.json").write_text(
        json.dumps(
            {
                "kind": "pending_apply_checklist",
                "staged_at": staged_at,
                "apply_session_result": {"status": "success"},
                "items": [
                    {"id": "apply_ops", "status": "pass"},
                    {"id": "active_phase", "status": "info"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (phase_dir / "pending_apply_checklist.md").write_text("# Pending Apply Checklist\n", encoding="utf-8")

    snapshot = orchestration._load_apply_staging_snapshot(tmp_path, "obsidian/family/phase")

    assert snapshot["packet_status"] == "invalid_review_packet"
    assert snapshot["review_ready"] is False
    assert snapshot["stale_against_factory"] is True
    assert snapshot["packet_staged_at"] == staged_at
    assert snapshot["factory_last_stage_apply"] == "2026-03-25T23:30:08.037695+00:00"
    assert "stale_review_packet" in snapshot["invalid_reasons"]


def test_build_orchestration_state_rearms_phase_when_checkpoint_packet_already_assimilated(monkeypatch) -> None:
    phase_command = "python3 pipeline_overnight.py --phase 09_35 --wake-agent auto --sleep-policy keep_awake"
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "observe_plan_compiled",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Re-arm the active phase so synth refresh and runtime state converge again.",
                "command": phase_command,
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "09_35",
            "phase_title": "Phase 09.35",
            "phase_dir": "obsidian/family/09.35",
            "family_dir": "obsidian/family",
            "cycle": 1,
            "needs_synth_refresh": False,
            "needs_reinit": True,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "apply_review_pending",
            "blocked": False,
            "gate_reason": "phase_runtime_rearm_required",
            "next_action": {
                "summary": "The staged phase checkpoint packet was already assimilated into the live wave.",
                "command": phase_command,
            },
            "review_artifacts": [],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "invalid_review_packet",
            "review_ready": False,
            "source_kind": "phase_dock_response",
            "apply_cmd": "./repo-python kernel.py --phase-assimilate 09_35 --live",
            "invalid_reasons": ["phase_checkpoint_already_assimilated"],
            "compiled_apply_ready": True,
            "apply_session_status": "success",
            "stale_against_phase_runtime": True,
            "phase_checkpoint_consumed": True,
            "pending_apply": {"path": "obsidian/family/phase/pending_apply.json", "exists": True},
            "checklist_json": {"path": "obsidian/family/phase/pending_apply_checklist.json", "exists": True},
            "checklist_md": {"path": "obsidian/family/phase/pending_apply_checklist.md", "exists": True},
            "phase_runtime": {"latest_dock_status": {"path": "tools/meta/apply/phase_packets/09_35_dock_status.json"}},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()
    factory_driver = next(driver for driver in state["drivers"] if driver["driver_id"] == "factory_lane")

    assert state["active_driver"] == "phase_pipeline"
    assert state["decision"]["command"] == phase_command
    assert "already assimilated" in state["decision"]["summary"]
    assert state["gate"]["gate_reason"] == "phase_runtime_rearm_required"
    assert state["gate"]["owner_driver"] == "phase_pipeline"
    assert factory_driver["gate_reason"] == "phase_runtime_rearm_required"
    assert factory_driver["blocked"] is False


def test_build_orchestration_state_continues_live_phase_when_consumed_checkpoint_is_stale(monkeypatch) -> None:
    phase_command = "python3 pipeline_advance.py --advance"
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "observe_dispatched",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Bridge responses are ready; process results now.",
                "command": phase_command,
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "09_35",
            "phase_title": "Phase 09.35",
            "phase_dir": "obsidian/family/09.35",
            "family_dir": "obsidian/family",
            "cycle": 1,
            "resume_command": "python3 pipeline_overnight.py --phase 09_35 --wake-agent auto --sleep-policy keep_awake",
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "apply_review_pending",
            "blocked": False,
            "gate_reason": "phase_runtime_rearm_required",
            "next_action": {
                "summary": "The staged phase checkpoint packet was already assimilated into the live wave.",
                "command": "python3 pipeline_overnight.py --phase 09_35 --wake-agent auto --sleep-policy keep_awake",
            },
            "review_artifacts": [],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {
            "packet_status": "invalid_review_packet",
            "review_ready": False,
            "source_kind": "phase_dock_response",
            "apply_cmd": "./repo-python kernel.py --phase-assimilate 09_35 --live",
            "invalid_reasons": ["phase_checkpoint_already_assimilated"],
            "compiled_apply_ready": True,
            "apply_session_status": "success",
            "stale_against_phase_runtime": True,
            "phase_checkpoint_consumed": True,
            "pending_apply": {"path": "obsidian/family/phase/pending_apply.json", "exists": True},
            "checklist_json": {"path": "obsidian/family/phase/pending_apply_checklist.json", "exists": True},
            "checklist_md": {"path": "obsidian/family/phase/pending_apply_checklist.md", "exists": True},
            "phase_runtime": {"latest_dock_status": {"path": "tools/meta/apply/phase_packets/09_35_dock_status.json"}},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )

    state = orchestration.build_orchestration_state()

    assert state["active_driver"] == "phase_pipeline"
    assert state["decision"]["command"] == phase_command
    assert "Use the live phase-pipeline action" in state["decision"]["summary"]
    assert "Bridge responses are ready" in state["decision"]["summary"]
    assert state["gate"]["active"] is False
    assert state["gate"]["gate_reason"] is None


def test_write_orchestration_artifacts_declares_authority_source(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        orchestration,
        "build_orchestration_state",
        lambda repo_root, phase_token=None: {
            "kind": "orchestration_state",
            "schema_version": "orchestration_state_v1",
            "active_driver": "phase_pipeline",
            "decision": {
                "immediate_mode": "phase_pipeline",
                "summary": "Advance the active phase.",
                "command": "python3 pipeline_advance.py --advance --bridge --provider chatgpt --launch-profile safe",
                "launch_recommended_now": True,
                "sequence": [
                    {
                        "mode": "phase_pipeline",
                        "summary": "Advance the active phase.",
                        "command": "python3 pipeline_advance.py --advance --bridge --provider chatgpt --launch-profile safe",
                        "launch_recommended_now": True,
                    }
                ],
            },
            "gate": {"active": False, "gate_reason": None, "owner_driver": "phase_pipeline", "review_ready": False, "command": None},
            "drivers": [],
            "agent_actions": [],
            "human_surface": {"primary_command": "python3 run_control_room.py"},
            "artifacts": {},
            "updated_at": "2026-03-25T00:00:00+00:00",
            "source_snapshots": {},
        },
    )

    wrote = orchestration.write_orchestration_artifacts(repo_root=tmp_path)
    state_path = tmp_path / wrote["state_path"]
    brief_json = tmp_path / wrote["brief_json_path"]
    brief_md = tmp_path / wrote["brief_markdown_path"]

    assert json.loads(state_path.read_text(encoding="utf-8"))["kind"] == "orchestration_state"
    brief_payload = json.loads(brief_json.read_text(encoding="utf-8"))
    assert brief_payload["authority_state_path"] == orchestration.ORCHESTRATION_STATE_REL
    assert "Authority:" in brief_md.read_text(encoding="utf-8")


def test_build_orchestration_state_projects_reactions_block(monkeypatch) -> None:
    monkeypatch.setattr(
        orchestration,
        "_phase_driver",
        lambda repo_root, phase_token: {
            "driver_id": "phase_pipeline",
            "stage": "results_processed",
            "blocked": False,
            "gate_reason": None,
            "next_action": {
                "summary": "Advance the phase loop.",
                "command": "python3 pipeline_advance.py --advance",
            },
            "review_artifacts": [],
            "state_path": "obsidian/family/phase/pipeline_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "phase_ref": "09_35",
            "phase_title": "Phase 09.35",
            "phase_dir": "obsidian/family/09.35",
            "family_dir": "obsidian/family",
            "cycle": 1,
            "needs_synth_refresh": False,
            "needs_reinit": False,
            "attention": {},
            "retryable_gate": False,
            "packet": {},
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_factory_driver",
        lambda repo_root, apply_staging, **kwargs: {
            "driver_id": "factory_lane",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "Advance factory.", "command": "./repo-python tools/meta/factory/factory_runner.py --step"},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/factory_state.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_mission_driver",
        lambda repo_root: {
            "driver_id": "mission_queue",
            "stage": "idle",
            "blocked": False,
            "gate_reason": None,
            "next_action": {"summary": "No mission work.", "command": None},
            "review_artifacts": [],
            "state_path": "tools/meta/factory/mission_session_v0.json",
            "last_updated": "2026-03-25T00:00:00+00:00",
            "active": False,
            "state_payload": {},
        },
    )
    monkeypatch.setattr(
        orchestration,
        "_load_apply_staging_snapshot",
        lambda repo_root, phase_dir_rel, **kwargs: {"packet_status": "missing_review_packet", "review_ready": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_documentation_snapshot",
        lambda repo_root, family_dir_rel: {"raw_seed_newer_than_docs": False},
    )
    monkeypatch.setattr(
        orchestration,
        "_load_bridge_snapshot",
        lambda repo_root: {"live_count": 0, "live_locks": []},
    )
    monkeypatch.setattr(
        orchestration.reactions_runtime,
        "build_reactions_orchestration_projection",
        lambda repo_root: {
            "engine_armed": True,
            "engine_status": "awaiting_barrier",
            "pid": 4321,
            "cursor_event_id": "rxn_event_001",
            "last_tick_at": "2026-04-17T00:10:00+00:00",
            "last_error": None,
            "awaiting_barriers": [
                {
                    "reaction_id": "route_backlog_high",
                    "kind": "operation_completion",
                    "label": "awaiting operation: raw_seed_route_review",
                    "status": "pending",
                    "operation_id": "raw_seed_route_review",
                    "wake_at": None,
                    "started_at": "2026-04-17T00:09:00+00:00",
                }
            ],
            "active_reaction_id": "route_backlog_high",
            "last_fired_at": "2026-04-17T00:09:00+00:00",
        },
    )

    state = orchestration.build_orchestration_state()

    assert state["active_driver"] == "phase_pipeline"
    assert state["reactions"]["engine_armed"] is True
    assert state["reactions"]["awaiting_barriers"][0]["reaction_id"] == "route_backlog_high"
    assert state["reactions"]["awaiting_barriers"][0]["label"] == "awaiting operation: raw_seed_route_review"


def test_write_orchestration_artifacts_event_log_and_jsonl_dedupe(tmp_path: Path, monkeypatch) -> None:
    base_state = {
        "kind": "orchestration_state",
        "schema_version": "orchestration_state_v1",
        "active_driver": "phase_pipeline",
        "decision": {
            "immediate_mode": "phase_pipeline",
            "summary": "Test summary",
            "command": "python3 pipeline_advance.py --advance",
            "launch_recommended_now": False,
            "sequence": [],
        },
        "gate": {"active": False, "gate_reason": None, "owner_driver": "phase_pipeline", "review_ready": False, "command": None},
        "drivers": [],
        "agent_actions": [],
        "human_surface": {
            "primary_command": "python3 run_control_room.py",
            "recommended_review_surface": "docs/orchestration_state.md",
        },
        "coordination": {
            "docs_route_focus": {
                "active_preset_id": "neutral",
                "label": "Neutral",
            },
            "active_directive": {
                "active": False,
                "path": None,
                "task": None,
                "summary": None,
                "file_targets": [],
                "updated_at": None,
            },
            "system_view": {
                "path": "obsidian/family/phase/system_view.json",
                "exists": True,
                "file_count": 7,
            },
            "routing_emphasis": {
                "active_tags": ["runtime_control"],
                "tag_deltas": {"runtime_control": 170},
                "reasons": ["Gate-free runtime default."],
            },
            "current_owner": {
                "actor_id": "control_room_manager",
                "driver_id": "phase_pipeline",
            },
            "next_handoff": {
                "actor_id": "control_room_manager",
                "mode": "phase_pipeline",
                "command": "python3 pipeline_advance.py --advance",
                "review_surface": "docs/orchestration_state.md",
                "completion_basis": "Test summary",
            },
            "actor_frames": {
                "control_room_manager": {
                    "status": "current_owner",
                }
            },
        },
        "artifacts": {},
        "updated_at": "2026-03-26T10:00:00+00:00",
        "source_snapshots": {},
    }

    state_holder = json.loads(json.dumps(base_state))

    def build_state(repo_root, phase_token=None):
        return json.loads(json.dumps(state_holder))

    monkeypatch.setattr(orchestration, "build_orchestration_state", build_state)

    first = orchestration.write_orchestration_artifacts(repo_root=tmp_path)
    state1 = json.loads((tmp_path / first["state_path"]).read_text(encoding="utf-8"))
    el = state1.get("event_log")
    assert isinstance(el, dict)
    assert el.get("path") == orchestration.ORCHESTRATION_EVENT_LOG_REL
    assert el.get("latest_event_id")
    assert el.get("latest_event_fingerprint")
    assert el.get("appended") is True
    log_path = tmp_path / orchestration.ORCHESTRATION_EVENT_LOG_REL
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec.get("event_fingerprint") == el.get("latest_event_fingerprint")
    assert rec.get("coordination", {}).get("docs_route_focus", {}).get("active_preset_id") == "neutral"

    second = orchestration.write_orchestration_artifacts(repo_root=tmp_path)
    state2 = json.loads((tmp_path / second["state_path"]).read_text(encoding="utf-8"))
    el2 = state2.get("event_log")
    assert el2.get("appended") is False
    lines2 = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines2) == 1

    state_holder["updated_at"] = "2026-03-26T11:00:00+00:00"
    state_holder["coordination"]["docs_route_focus"]["active_preset_id"] = "runtime_control"
    state_holder["coordination"]["docs_route_focus"]["label"] = "Runtime control"
    third = orchestration.write_orchestration_artifacts(repo_root=tmp_path)
    state3 = json.loads((tmp_path / third["state_path"]).read_text(encoding="utf-8"))
    assert state3.get("event_log", {}).get("appended") is True
    lines3 = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines3) == 2
    rec3 = json.loads(lines3[-1])
    assert rec3.get("coordination", {}).get("docs_route_focus", {}).get("active_preset_id") == "runtime_control"

    state_holder["updated_at"] = "2026-03-26T12:00:00+00:00"
    state_holder["coordination"]["active_directive"] = {
        "active": True,
        "path": "obsidian/family/phase/focus_directive.json",
        "task": "Review packet",
        "summary": "Review the staged packet before continuing.",
        "file_targets": ["obsidian/family/phase/pending_apply.json"],
        "updated_at": "2026-03-26T12:00:00+00:00",
    }
    fourth = orchestration.write_orchestration_artifacts(repo_root=tmp_path)
    state4 = json.loads((tmp_path / fourth["state_path"]).read_text(encoding="utf-8"))
    assert state4.get("event_log", {}).get("appended") is True
    lines4 = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines4) == 3
    rec4 = json.loads(lines4[-1])
    assert rec4.get("coordination", {}).get("active_directive", {}).get("summary") == "Review the staged packet before continuing."
