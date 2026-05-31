"""
[PURPOSE]
- Teleology: Lock the overnight planner heuristics that decide when synth material is stale and when pipeline state must be reinitialized from a newer synth seed.
- Mechanism: Build temporary raw-seed, synth-seed, and pipeline-state fixtures, adjust mtimes, and assert the assessment payloads returned by `pipeline_overnight`.

[INTERFACE]
- Inputs: pytest `tmp_path` fixtures, synthetic JSON files, and monkeypatched state readers.
- Outputs: Assertion-only coverage for synth-refresh and pipeline-reinit assessment decisions.

[FLOW]
- Write seed or state fixtures -> adjust mtimes to create ordered freshness scenarios -> call overnight assessment helpers -> assert the returned reason keys and flags.
- When-needed: Open when overnight automation regresses on synth-refresh detection or reinit gating driven by freshness comparisons and you need the precise test expectations before reading the operator entrypoint.
- Escalates-to: pipeline_overnight.py::_assess_synth_refresh; pipeline_overnight.py::_assess_pipeline_state; seed_pipeline.py::load_state
- Navigation-group: server_backend

[DEPENDENCIES]
- json: Serializes temporary synth-seed and pipeline-state payloads.
- os: Adjusts fixture mtimes to create freshness orderings.
- pathlib.Path: Builds the temporary phase tree.
- pipeline_overnight: Supplies the overnight assessment helpers under test.

[CONSTRAINTS]
- Determinism: Fixed timestamp ordering is created with explicit `utime()` calls rather than wall-clock sleeps.
- Non-goal: These tests do not start launch agents, refresh synth seeds, or run the full overnight command.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pipeline_overnight
import pytest


def _write_json(path: Path, payload: dict) -> None:
    """
    [ACTION]
    - Teleology: Materialize one JSON fixture file for overnight synth-refresh and pipeline-state assessments.
    - Mechanism: Create the parent directory tree, then serialize the payload with stable indentation and a trailing newline.
    - Reads: `path` and `payload`.
    - Writes: `path`.
    - Guarantee: The target file exists after return and contains the serialized payload.
    - Fails: Propagates filesystem or JSON serialization errors from `mkdir()` or `write_text()`.
    - When-needed: Open when extending overnight freshness tests and you need the exact fixture writer that prepares synth and state files before mtime manipulation.
    - Escalates-to: pipeline_overnight.py::_assess_synth_refresh; pipeline_overnight.py::_assess_pipeline_state
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_resolve_phase_entry_prefers_explicit_active_marker_over_stale_runtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    family_dir = tmp_path / "obsidian" / "family"
    phase_35 = family_dir / "09.35"
    phase_37 = family_dir / "09.37"
    _write_json(
        phase_35 / "phase_scaffold.json",
        {
            "phase_id": "09_35",
            "phase_number": "09.35",
            "phase_title": "Phase 09.35",
            "phase_dir": "obsidian/family/09.35",
            "family_dir": "obsidian/family",
        },
    )
    _write_json(
        phase_37 / "phase_scaffold.json",
        {
            "phase_id": "09_37",
            "phase_number": "09.37",
            "phase_title": "Phase 09.37",
            "phase_dir": "obsidian/family/09.37",
            "family_dir": "obsidian/family",
        },
    )
    _write_json(
        family_dir / "phase_family.json",
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
    monkeypatch.setattr(
        pipeline_overnight.pipeline_advance,
        "find_state",
        lambda: (phase_35 / "pipeline_state.json", {"phase_dir": "obsidian/family/09.35"}),
    )

    default_entry, _entries = pipeline_overnight._resolve_phase_entry(None, root=tmp_path)
    active_entry, _entries = pipeline_overnight._resolve_phase_entry("__active__", root=tmp_path)
    explicit_entry, _entries = pipeline_overnight._resolve_phase_entry("09_35", root=tmp_path)

    assert default_entry["phase_id"] == "09_37"
    assert active_entry["phase_id"] == "09_37"
    assert explicit_entry["phase_id"] == "09_35"


def test_assess_synth_refresh_flags_raw_seed_newer_than_synth(tmp_path: Path) -> None:
    raw_seed = tmp_path / "family" / "raw_seed.md"
    synth_seed = tmp_path / "phase" / "synth_seed.json"
    raw_seed.parent.mkdir(parents=True, exist_ok=True)
    synth_seed.parent.mkdir(parents=True, exist_ok=True)

    raw_seed.write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(
        synth_seed,
        {
            "intent": "Keep the overnight planner moving.",
            "success_criteria": "Produce a stable plan.",
            "authoring_status": "authored",
        },
    )
    raw_stat = raw_seed.stat()
    os.utime(raw_seed, (raw_stat.st_atime, raw_stat.st_mtime + 5))

    assessment = pipeline_overnight._assess_synth_refresh(
        raw_seed_path=raw_seed,
        synth_seed_path=synth_seed,
        refresh_mode="auto",
    )

    assert assessment["needs_refresh"] is True
    assert assessment["reason"] == "raw_seed_newer_than_synth"


def test_assess_pipeline_state_requests_reinit_when_synth_is_newer(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "phase" / "pipeline_state.json"
    synth_seed = tmp_path / "phase" / "synth_seed.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    synth_seed.parent.mkdir(parents=True, exist_ok=True)

    state_path.write_text("{}", encoding="utf-8")
    _write_json(synth_seed, {"intent": "newer synth"})
    state_stat = state_path.stat()
    synth_stat = synth_seed.stat()
    os.utime(state_path, (state_stat.st_atime, state_stat.st_mtime))
    os.utime(synth_seed, (synth_stat.st_atime, synth_stat.st_mtime + 5))
    monkeypatch.setattr(
        pipeline_overnight,
        "load_state",
        lambda path: {"stage": "results_processed", "cycle": 3},
    )

    assessment = pipeline_overnight._assess_pipeline_state(
        state_path=state_path,
        synth_seed_path=synth_seed,
        force_reinit=False,
    )

    assert assessment["needs_reinit"] is True
    assert assessment["reason"] == "synth_newer_than_state"
    assert assessment["stage"] == "results_processed"
    assert assessment["cycle"] == 3


def test_synth_refresh_and_pipeline_reinit_stay_distinct(monkeypatch, tmp_path: Path) -> None:
    raw_seed = tmp_path / "family" / "raw_seed.md"
    synth_seed = tmp_path / "phase" / "synth_seed.json"
    state_path = tmp_path / "phase" / "pipeline_state.json"
    raw_seed.parent.mkdir(parents=True, exist_ok=True)
    synth_seed.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    raw_seed.write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(synth_seed, {"intent": "newer synth"})
    state_path.write_text("{}", encoding="utf-8")

    raw_stat = raw_seed.stat()
    synth_stat = synth_seed.stat()
    state_stat = state_path.stat()
    os.utime(raw_seed, (raw_stat.st_atime, raw_stat.st_mtime))
    os.utime(synth_seed, (synth_stat.st_atime, synth_stat.st_mtime + 5))
    os.utime(state_path, (state_stat.st_atime, state_stat.st_mtime))

    monkeypatch.setattr(
        pipeline_overnight,
        "load_state",
        lambda path: {"stage": "apply_ready", "cycle": 7},
    )

    synth_refresh = pipeline_overnight._assess_synth_refresh(
        raw_seed_path=raw_seed,
        synth_seed_path=synth_seed,
        refresh_mode="auto",
    )
    pipeline_state = pipeline_overnight._assess_pipeline_state(
        state_path=state_path,
        synth_seed_path=synth_seed,
        force_reinit=False,
    )

    assert synth_refresh["needs_refresh"] is False
    assert synth_refresh["reason"] == "up_to_date"
    assert pipeline_state["needs_reinit"] is True
    assert pipeline_state["reason"] == "synth_newer_than_state"
    assert pipeline_state["stage"] == "apply_ready"


def test_arm_overnight_defers_auto_refresh_when_dock_packet_is_under_split(
    monkeypatch,
    tmp_path: Path,
) -> None:
    family_dir = tmp_path / "obsidian" / "family"
    phase_dir = family_dir / "09.35"
    family_dir.mkdir(parents=True, exist_ok=True)
    phase_dir.mkdir(parents=True, exist_ok=True)
    raw_seed = family_dir / "raw_seed.md"
    synth_seed = phase_dir / "synth_seed.json"
    raw_seed.write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(synth_seed, {"authoring_status": "authored"})
    raw_stat = raw_seed.stat()
    os.utime(raw_seed, (raw_stat.st_atime, raw_stat.st_mtime + 5))

    phase_entry = {
        "phase_id": "09_35",
        "phase_number": "09.35",
        "phase_title": "Phase 09.35",
        "phase_dir": "obsidian/family/09.35",
    }
    harbor = {
        "paths": {
            "phase_dir": "obsidian/family/09.35",
            "blackboard_dir": "obsidian/family",
            "raw_seed": "obsidian/family/raw_seed.md",
            "synth_seed": "obsidian/family/09.35/synth_seed.json",
        }
    }

    monkeypatch.setattr(pipeline_overnight, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_overnight,
        "_resolve_phase_entry",
        lambda phase_token, root=None: (phase_entry, [phase_entry]),
    )
    monkeypatch.setattr(pipeline_overnight, "resolve_phase_harbor", lambda *args, **kwargs: harbor)
    monkeypatch.setattr(
        pipeline_overnight,
        "load_control_state",
        lambda repo_root=None: {
            "paused": False,
            "pause_reason": None,
            "wake_lock": {"sleep_policy": "keep_awake", "enabled": False},
        },
    )
    monkeypatch.setattr(pipeline_overnight, "pause_automation", lambda **kwargs: {"status": "paused"})
    monkeypatch.setattr(pipeline_overnight, "bootstrap_phase_harbor", lambda *args, **kwargs: {"status": "bootstrapped"})
    monkeypatch.setattr(
        pipeline_overnight,
        "_assess_pipeline_state",
        lambda **kwargs: {"needs_reinit": False, "reason": "up_to_date", "exists": True},
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "preflight_phase_dock",
        lambda *args, **kwargs: {
            "response_artifact": {"will_reuse_existing_response": False},
            "prompt_metrics": {
                "risk_flags": [
                    "recommended_prompt_budget_exceeded",
                    "prompt_decomposition_required",
                ],
                "warnings": [
                    "phase dock prompt estimates 209,374 chars, above the single-packet design budget (200,000); this dock is under-split."
                ],
            },
            "must_have": [
                {
                    "id": "dispatch_budget",
                    "status": "warning",
                    "detail": "phase dock prompt estimates 209,374 chars, above the single-packet design budget (200,000); this dock is under-split.",
                }
            ],
        },
    )
    dock_calls: list[str] = []

    def _run_phase_dock_should_not_dispatch(*args, **kwargs):
        dock_calls.append("called")
        raise AssertionError("live dock should stay blocked")

    monkeypatch.setattr(
        pipeline_overnight,
        "run_phase_dock",
        _run_phase_dock_should_not_dispatch,
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "_load_or_init_state",
        lambda **kwargs: (
            {
                "pipeline_id": "pipe-demo",
                "stage": "initialized",
                "cycle": 0,
            },
            "retained",
        ),
    )
    monkeypatch.setattr(
        pipeline_overnight.pipeline_advance,
        "write_resume_artifacts",
        lambda state_path, state: (
            tmp_path / "resume.json",
            tmp_path / "resume.md",
        ),
    )
    monkeypatch.setattr(
        pipeline_overnight.pipeline_advance,
        "build_resume_packet",
        lambda state_path, state: {
            "next_action": {"summary": "Advance phase.", "command": "python3 pipeline_advance.py --advance"},
            "codex_attention": {},
        },
    )
    monkeypatch.setattr(pipeline_overnight, "resolve_wake_agent", lambda wake_agent, repo_root=None: "none")
    monkeypatch.setattr(pipeline_overnight, "_install_launch_agent", lambda label: {"label": label, "status": "ok"})
    monkeypatch.setattr(
        pipeline_overnight,
        "mark_pipeline_resumed",
        lambda repo_root=None, sleep_policy=None: {
            "paused": False,
            "wake_lock": {"sleep_policy": sleep_policy},
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "ensure_wake_lock",
        lambda sleep_policy, repo_root=None: {
            "paused": False,
            "wake_lock": {"sleep_policy": sleep_policy, "enabled": True},
        },
    )

    payload = pipeline_overnight.arm_overnight(
        phase_token="09_35",
        wake_agent="auto",
        refresh_mode="auto",
        sleep_policy="keep_awake",
        force_reinit=False,
        pause_reason="test",
    )

    assert dock_calls == []
    refresh = payload["synth_refresh"]
    assert refresh["deferred"] is True
    assert refresh["reason"] == "raw_seed_newer_than_synth_deferred"
    assert "blocked before live dispatch" in refresh["dock_guard_error"]
    assert (phase_dir / "synth_refresh_deferred.json").exists()

    assessment = pipeline_overnight._assess_synth_refresh(
        raw_seed_path=raw_seed,
        synth_seed_path=synth_seed,
        refresh_mode="auto",
    )

    assert assessment["needs_refresh"] is False
    assert assessment["deferred"] is True
    assert assessment["raw_seed_newer_than_synth"] is True


def test_arm_overnight_still_blocks_forced_refresh_when_dock_packet_is_under_split(
    monkeypatch,
    tmp_path: Path,
) -> None:
    family_dir = tmp_path / "obsidian" / "family"
    phase_dir = family_dir / "09.35"
    family_dir.mkdir(parents=True, exist_ok=True)
    phase_dir.mkdir(parents=True, exist_ok=True)
    (family_dir / "raw_seed.md").write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(phase_dir / "synth_seed.json", {"authoring_status": "authored"})

    phase_entry = {
        "phase_id": "09_35",
        "phase_number": "09.35",
        "phase_title": "Phase 09.35",
        "phase_dir": "obsidian/family/09.35",
    }
    harbor = {
        "paths": {
            "phase_dir": "obsidian/family/09.35",
            "blackboard_dir": "obsidian/family",
            "raw_seed": "obsidian/family/raw_seed.md",
            "synth_seed": "obsidian/family/09.35/synth_seed.json",
        }
    }

    monkeypatch.setattr(pipeline_overnight, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_overnight,
        "_resolve_phase_entry",
        lambda phase_token, root=None: (phase_entry, [phase_entry]),
    )
    monkeypatch.setattr(pipeline_overnight, "resolve_phase_harbor", lambda *args, **kwargs: harbor)
    monkeypatch.setattr(
        pipeline_overnight,
        "load_control_state",
        lambda repo_root=None: {
            "paused": False,
            "pause_reason": None,
            "wake_lock": {"sleep_policy": "keep_awake", "enabled": False},
        },
    )
    monkeypatch.setattr(pipeline_overnight, "pause_automation", lambda **kwargs: {"status": "paused"})
    monkeypatch.setattr(pipeline_overnight, "bootstrap_phase_harbor", lambda *args, **kwargs: {"status": "bootstrapped"})
    monkeypatch.setattr(
        pipeline_overnight,
        "preflight_phase_dock",
        lambda *args, **kwargs: {
            "response_artifact": {"will_reuse_existing_response": False},
            "prompt_metrics": {
                "risk_flags": ["prompt_decomposition_required"],
                "warnings": ["phase dock prompt estimates 209,374 chars; this dock is under-split."],
            },
            "must_have": [
                {
                    "id": "dispatch_budget",
                    "status": "warning",
                    "detail": "phase dock prompt estimates 209,374 chars; this dock is under-split.",
                }
            ],
        },
    )

    with pytest.raises(RuntimeError, match="blocked before live dispatch"):
        pipeline_overnight.arm_overnight(
            phase_token="09_35",
            wake_agent="auto",
            refresh_mode="always",
            sleep_policy="keep_awake",
            force_reinit=False,
            pause_reason="test",
        )


def test_arm_overnight_restores_control_state_after_failed_dock_dispatch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    family_dir = tmp_path / "obsidian" / "family"
    phase_dir = family_dir / "09.35"
    family_dir.mkdir(parents=True, exist_ok=True)
    phase_dir.mkdir(parents=True, exist_ok=True)
    (family_dir / "raw_seed.md").write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(phase_dir / "synth_seed.json", {"authoring_status": "authored"})

    phase_entry = {
        "phase_id": "09_35",
        "phase_number": "09.35",
        "phase_title": "Phase 09.35",
        "phase_dir": "obsidian/family/09.35",
    }
    harbor = {
        "paths": {
            "phase_dir": "obsidian/family/09.35",
            "blackboard_dir": "obsidian/family",
            "raw_seed": "obsidian/family/raw_seed.md",
            "synth_seed": "obsidian/family/09.35/synth_seed.json",
        }
    }

    initial_control_state = {
        "paused": False,
        "pause_reason": None,
        "wake_lock": {
            "sleep_policy": "keep_awake",
            "enabled": False,
            "pid": None,
            "started_at": None,
            "command": None,
        },
    }
    restored: dict[str, object] = {}

    monkeypatch.setattr(pipeline_overnight, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_overnight,
        "_resolve_phase_entry",
        lambda phase_token, root=None: (phase_entry, [phase_entry]),
    )
    monkeypatch.setattr(pipeline_overnight, "resolve_phase_harbor", lambda *args, **kwargs: harbor)
    monkeypatch.setattr(pipeline_overnight, "load_control_state", lambda repo_root=None: dict(initial_control_state))
    monkeypatch.setattr(pipeline_overnight, "pause_automation", lambda **kwargs: {"status": "paused"})
    monkeypatch.setattr(pipeline_overnight, "bootstrap_phase_harbor", lambda *args, **kwargs: {"status": "bootstrapped"})
    monkeypatch.setattr(
        pipeline_overnight,
        "_assess_synth_refresh",
        lambda **kwargs: {
            "mode": "auto",
            "needs_refresh": True,
            "blocked": False,
            "reason": "raw_seed_newer_than_synth",
            "raw_seed": {"path": "obsidian/family/raw_seed.md", "exists": True},
            "synth_seed": {"path": "obsidian/family/09.35/synth_seed.json", "exists": True},
            "synth_authoring_status": "authored",
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "preflight_phase_dock",
        lambda *args, **kwargs: {
            "response_artifact": {"will_reuse_existing_response": False},
            "prompt_metrics": {
                "risk_flags": [],
                "warnings": [],
            },
            "must_have": [],
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "run_phase_dock",
        lambda *args, **kwargs: {
            "status": "error",
            "dispatch": {"status": "error"},
        },
    )

    def _fake_resume_automation(*, root, dry_run, sleep_policy):
        restored["root"] = root
        restored["dry_run"] = dry_run
        restored["sleep_policy"] = sleep_policy
        return {
            "action": "resume",
            "control_state": {
                "paused": False,
                "pause_reason": None,
                "wake_lock": {"sleep_policy": sleep_policy},
            },
        }

    monkeypatch.setattr(pipeline_overnight, "resume_automation", _fake_resume_automation)

    with pytest.raises(RuntimeError, match="did not apply cleanly"):
        pipeline_overnight.arm_overnight(
            phase_token="09_35",
            wake_agent="auto",
            refresh_mode="auto",
            sleep_policy="keep_awake",
            force_reinit=False,
            pause_reason="test",
        )

    assert restored["root"] == tmp_path
    assert restored["dry_run"] is False
    assert restored["sleep_policy"] == "keep_awake"


def test_arm_overnight_restores_control_state_after_abort(
    monkeypatch,
    tmp_path: Path,
) -> None:
    family_dir = tmp_path / "obsidian" / "family"
    phase_dir = family_dir / "09.35"
    family_dir.mkdir(parents=True, exist_ok=True)
    phase_dir.mkdir(parents=True, exist_ok=True)
    (family_dir / "raw_seed.md").write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(phase_dir / "synth_seed.json", {"authoring_status": "authored"})

    phase_entry = {
        "phase_id": "09_35",
        "phase_number": "09.35",
        "phase_title": "Phase 09.35",
        "phase_dir": "obsidian/family/09.35",
    }
    harbor = {
        "paths": {
            "phase_dir": "obsidian/family/09.35",
            "blackboard_dir": "obsidian/family",
            "raw_seed": "obsidian/family/raw_seed.md",
            "synth_seed": "obsidian/family/09.35/synth_seed.json",
        }
    }

    initial_control_state = {
        "paused": False,
        "pause_reason": None,
        "wake_lock": {
            "sleep_policy": "keep_awake",
            "enabled": False,
            "pid": None,
            "started_at": None,
            "command": None,
        },
    }
    restored: dict[str, object] = {}

    monkeypatch.setattr(pipeline_overnight, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_overnight,
        "_resolve_phase_entry",
        lambda phase_token, root=None: (phase_entry, [phase_entry]),
    )
    monkeypatch.setattr(pipeline_overnight, "resolve_phase_harbor", lambda *args, **kwargs: harbor)
    monkeypatch.setattr(pipeline_overnight, "load_control_state", lambda repo_root=None: dict(initial_control_state))
    monkeypatch.setattr(pipeline_overnight, "pause_automation", lambda **kwargs: {"status": "paused"})
    monkeypatch.setattr(pipeline_overnight, "bootstrap_phase_harbor", lambda *args, **kwargs: {"status": "bootstrapped"})
    monkeypatch.setattr(
        pipeline_overnight,
        "_assess_synth_refresh",
        lambda **kwargs: {
            "mode": "auto",
            "needs_refresh": True,
            "blocked": False,
            "reason": "raw_seed_newer_than_synth",
            "raw_seed": {"path": "obsidian/family/raw_seed.md", "exists": True},
            "synth_seed": {"path": "obsidian/family/09.35/synth_seed.json", "exists": True},
            "synth_authoring_status": "authored",
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "preflight_phase_dock",
        lambda *args, **kwargs: {
            "response_artifact": {"will_reuse_existing_response": False},
            "prompt_metrics": {
                "risk_flags": [],
                "warnings": [],
            },
            "must_have": [],
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "run_phase_dock",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    def _fake_resume_automation(*, root, dry_run, sleep_policy):
        restored["root"] = root
        restored["dry_run"] = dry_run
        restored["sleep_policy"] = sleep_policy
        return {
            "action": "resume",
            "control_state": {
                "paused": False,
                "pause_reason": None,
                "wake_lock": {"sleep_policy": sleep_policy},
            },
        }

    monkeypatch.setattr(pipeline_overnight, "resume_automation", _fake_resume_automation)

    with pytest.raises(KeyboardInterrupt):
        pipeline_overnight.arm_overnight(
            phase_token="09_35",
            wake_agent="auto",
            refresh_mode="auto",
            sleep_policy="keep_awake",
            force_reinit=False,
            pause_reason="test",
        )


def test_install_launch_agent_soft_skips_sandbox_permission_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    script = tmp_path / "pipeline_autopilot_install.sh"
    script.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    monkeypatch.setitem(
        pipeline_overnight.INSTALL_SCRIPTS,
        pipeline_overnight.PIPELINE_AUTOPILOT_LABEL,
        script,
    )
    monkeypatch.setattr(
        pipeline_overnight.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="install: sandbox detected, falling back to direct copy\n",
            stderr="install: /Users/example/Library/LaunchAgents/demo: Operation not permitted\n",
        ),
    )

    payload = pipeline_overnight._install_launch_agent(pipeline_overnight.PIPELINE_AUTOPILOT_LABEL)

    assert payload["status"] == "skipped_permission_blocked"
    assert payload["permission_blocked"] is True
    assert "sandboxed environment" in payload["warning"]


def test_arm_overnight_continues_when_launch_agent_install_is_permission_blocked(
    monkeypatch,
    tmp_path: Path,
) -> None:
    family_dir = tmp_path / "obsidian" / "family"
    phase_dir = family_dir / "09.35"
    family_dir.mkdir(parents=True, exist_ok=True)
    phase_dir.mkdir(parents=True, exist_ok=True)
    (family_dir / "raw_seed.md").write_text("# Raw Seed\n", encoding="utf-8")
    _write_json(phase_dir / "synth_seed.json", {"authoring_status": "authored"})

    phase_entry = {
        "phase_id": "09_35",
        "phase_number": "09.35",
        "phase_title": "Phase 09.35",
        "phase_dir": "obsidian/family/09.35",
    }
    harbor = {
        "paths": {
            "phase_dir": "obsidian/family/09.35",
            "blackboard_dir": "obsidian/family",
            "raw_seed": "obsidian/family/raw_seed.md",
            "synth_seed": "obsidian/family/09.35/synth_seed.json",
        }
    }

    monkeypatch.setattr(pipeline_overnight, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_overnight,
        "_resolve_phase_entry",
        lambda phase_token, root=None: (phase_entry, [phase_entry]),
    )
    monkeypatch.setattr(pipeline_overnight, "resolve_phase_harbor", lambda *args, **kwargs: harbor)
    monkeypatch.setattr(
        pipeline_overnight,
        "load_control_state",
        lambda repo_root=None: {
            "paused": False,
            "pause_reason": None,
            "wake_lock": {
                "sleep_policy": "keep_awake",
                "enabled": False,
                "pid": None,
                "started_at": None,
                "command": None,
            },
        },
    )
    monkeypatch.setattr(pipeline_overnight, "pause_automation", lambda **kwargs: {"status": "paused"})
    monkeypatch.setattr(pipeline_overnight, "bootstrap_phase_harbor", lambda *args, **kwargs: {"status": "bootstrapped"})
    monkeypatch.setattr(
        pipeline_overnight,
        "_assess_synth_refresh",
        lambda **kwargs: {
            "mode": "auto",
            "needs_refresh": False,
            "blocked": False,
            "reason": "up_to_date",
            "raw_seed": {"path": "obsidian/family/raw_seed.md", "exists": True},
            "synth_seed": {"path": "obsidian/family/09.35/synth_seed.json", "exists": True},
            "synth_authoring_status": "authored",
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "_assess_pipeline_state",
        lambda **kwargs: {
            "needs_reinit": False,
            "reason": "up_to_date",
            "state_path": "obsidian/family/09.35/pipeline_state.json",
            "exists": True,
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "_load_or_init_state",
        lambda **kwargs: (
            {
                "pipeline_id": "pipe-demo",
                "stage": "initialized",
                "cycle": 0,
            },
            "retained",
        ),
    )
    monkeypatch.setattr(
        pipeline_overnight.pipeline_advance,
        "write_resume_artifacts",
        lambda state_path, state: (
            tmp_path / "resume.json",
            tmp_path / "resume.md",
        ),
    )
    monkeypatch.setattr(
        pipeline_overnight.pipeline_advance,
        "build_resume_packet",
        lambda state_path, state: {
            "next_action": {"summary": "Advance phase.", "command": "python3 pipeline_advance.py --advance"},
            "codex_attention": {},
        },
    )
    monkeypatch.setattr(pipeline_overnight, "resolve_wake_agent", lambda wake_agent, repo_root=None: "none")
    monkeypatch.setattr(
        pipeline_overnight,
        "_install_launch_agent",
        lambda label: {
            "label": label,
            "status": "skipped_permission_blocked",
            "permission_blocked": True,
            "warning": "sandbox",
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "mark_pipeline_resumed",
        lambda repo_root=None, sleep_policy=None: {
            "paused": False,
            "wake_lock": {"sleep_policy": sleep_policy},
        },
    )
    monkeypatch.setattr(
        pipeline_overnight,
        "ensure_wake_lock",
        lambda sleep_policy, repo_root=None: {
            "paused": False,
            "wake_lock": {"sleep_policy": sleep_policy, "enabled": True},
        },
    )

    payload = pipeline_overnight.arm_overnight(
        phase_token="09_35",
        wake_agent="auto",
        refresh_mode="auto",
        sleep_policy="keep_awake",
        force_reinit=False,
        pause_reason="test",
    )

    assert payload["launch_agents"]["wake_agent"] == "none"
    assert payload["launch_agents"]["install_results"][0]["status"] == "skipped_permission_blocked"
    assert payload["control_state"]["wake_lock"]["enabled"] is True
