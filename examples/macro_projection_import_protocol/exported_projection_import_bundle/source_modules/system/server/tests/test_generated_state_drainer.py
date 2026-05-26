from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import system.lib.generated_state_drainer as generated_state_drainer
import tools.meta.control.generated_state_drainer as generated_state_drainer_cli
from system.lib import task_ledger_events, work_ledger
from system.lib.generated_projection_registry import get_projection_owner
from system.lib.generated_state_drainer import (
    APPEND_EXEMPT_LANDING_MODE,
    LANDING_MANIFEST_SCHEMA,
    SYSTEM_ATLAS_OWNER_ID,
    TASK_LEDGER_OWNER_ID,
    TASK_LEDGER_REFRESH_ACTION,
    WORK_LEDGER_OWNER_ID,
    WORK_LEDGER_REFRESH_ACTION,
    apply_generated_state_drainer,
    build_generated_projection_landing_plan,
    build_generated_projection_settlement_fast_plan,
    build_generated_projection_settlement_plan,
    build_generated_state_drainer_status,
    land_generated_projection_bundle,
    settle_generated_projection_owners,
)

pytestmark = [pytest.mark.integration_generated_state, pytest.mark.slow_control_plane]
full_drainer_settlement = pytest.mark.skipif(
    os.environ.get("AI_WORKFLOW_FULL_DRAINER_SETTLEMENT") != "1",
    reason="full two-owner settlement integration is explicit; default drainer validation keeps focused landing proofs",
)


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    subprocess.run(["git", "config", "gc.auto", "0"], cwd=root, check=True)
    subprocess.run(["git", "config", "maintenance.auto", "false"], cwd=root, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "baseline"], cwd=root, check=True, stdout=subprocess.DEVNULL)


def _fake_scoped_commit_result(**kwargs) -> dict:
    return {
        "new_commit": "fake-generated-state-drainer-commit",
        "changed_paths": [str(path) for path in kwargs.get("paths", [])],
    }


def _landing_plan_fixture(
    *,
    owner_id: str,
    status: str,
    dirty_status: str = "clean",
    source_dirty_status: str = "clean",
    can_apply: bool = True,
    blocked_by: list[str] | None = None,
) -> dict:
    if owner_id == TASK_LEDGER_OWNER_ID:
        required_projection = str(task_ledger_events.LEDGER_REL)
        source_path = str(task_ledger_events.EVENTS_REL)
    elif owner_id == SYSTEM_ATLAS_OWNER_ID:
        required_projection = "docs/system_atlas/generated_system_atlas_snapshot.md"
        source_path = "state/system_atlas/system_atlas.graph.json"
    else:
        required_projection = "codex/ledger/09_52/work_ledger_index.json"
        source_path = "codex/ledger/09_52/work_ledger.jsonl"
    return {
        "schema": "generated_projection_landing_plan_v0",
        "ok": not blocked_by,
        "owner_id": owner_id,
        "status": status,
        "source_authority": source_path,
        "source_authority_paths": [source_path],
        "source_authority_paths_to_stage": [source_path] if source_dirty_status == "dirty" else [],
        "source_event_hashes": {},
        "source_path_hashes": {},
        "projection_paths": [required_projection],
        "projection_hashes": {required_projection: "sha256:test"},
        "freshness_status": "fresh_dirty" if dirty_status == "dirty" else "fresh_clean",
        "dirty_status": dirty_status,
        "source_dirty_status": source_dirty_status,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2 if dirty_status == "dirty" else 0},
        "self_invalidation_reason": "test fixture",
        "can_apply": can_apply,
        "blocked_by": blocked_by or [],
        "landing_manifest_path": str(
            Path("state/generated_projection_landing")
            / f"{owner_id}_manifest.json"
        ),
    }


def _open_work_ledger_thread(root: Path) -> Path:
    work_ledger.open_thread(
        root,
        actor="codex",
        actor_session_id="session_demo",
        phase_id="09_52",
        family_id="09",
        title="Generated drainer fixture",
        body="Seed a Work Ledger event so the projection has source authority.",
    )
    return root / "codex/ledger/09_52/work_ledger_index.json"


def _make_projection_stale(root: Path) -> Path:
    index_path = _open_work_ledger_thread(root)
    index_path.write_text(
        json.dumps(
            {
                "schema": work_ledger.WORK_LEDGER_INDEX_SCHEMA,
                "phase_id": "09_52",
                "family_id": "09",
                "counts": {"events": 0},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return index_path


def _append_task_ledger_capture(root: Path) -> Path:
    task_ledger_events.append_event(
        root,
        {
            "event_id": "wie_test_task_drainer",
            "event_type": "work_item.captured",
            "created_at": "2026-05-07T00:00:00+00:00",
            "created_by": "codex",
            "subject_id": "cap_task_drainer",
            "payload": {
                "title": "Task drainer fixture",
                "statement": "Seed Task Ledger projections for generated-state drainer tests.",
                "confidence": 0.9,
                "tags": ["generated_state_drainer"],
            },
        },
    )
    task_ledger_events.rebuild_projections(root)
    return root / task_ledger_events.LEDGER_REL


def _make_task_ledger_projection_stale(root: Path) -> Path:
    ledger_path = _append_task_ledger_capture(root)
    ledger_path.write_text(
        json.dumps(
            {
                "kind": "task_ledger",
                "schema_version": task_ledger_events.TASK_LEDGER_PROJECTION_SCHEMA,
                "ledger_id": "global",
                "generated_at": "2026-05-07T00:00:00+00:00",
                "updated_at": "2026-05-07T00:00:00+00:00",
                "tasks": [],
                "work_items": [],
                "event_count": 0,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return ledger_path


def _write_mission_blackboard(root: Path) -> None:
    path = root / task_ledger_events.MISSION_BLACKBOARD_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "mission_blackboard_v1",
                "rows": [
                    {
                        "row_id": "09_54::09_54_wave_001",
                        "status": "active",
                        "phase_id": "09_54",
                        "wave_id": "09_54_wave_001",
                        "focus_summary": "Active launch nucleus.",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_status_classifies_stale_work_ledger_projection(tmp_path: Path) -> None:
    root = tmp_path
    _make_projection_stale(root)

    status = build_generated_state_drainer_status(root)
    row = status["projection_targets"][0]

    assert status["schema"] == "generated_state_drainer_status_v0"
    assert status["summary"]["stale_count"] == 1
    assert row["generated_path"] == "codex/ledger/09_52/work_ledger_index.json"
    assert row["owner_id"] == "work_ledger_index_projection"
    assert row["freshness_status"] == "projection_stale"
    assert row["owner_tool"] == "./repo-python tools/meta/factory/work_ledger.py project --all"
    assert row["commit_policy"] == "serial_drainer_only"
    assert row["safe_to_commit_by_agent"] is False
    assert row["durable_projection"] is True
    assert row["bloat_class"] == "work_ledger_event_or_projection"


def test_status_distinguishes_fresh_dirty_projection(tmp_path: Path) -> None:
    root = tmp_path
    index_path = _open_work_ledger_thread(root)

    status = build_generated_state_drainer_status(
        root,
        status_map={str(index_path.relative_to(root)): "??"},
    )
    row = status["projection_targets"][0]

    assert status["summary"]["stale_count"] == 0
    assert status["summary"]["dirty_count"] == 1
    assert status["summary"]["status"] == "fresh_dirty"
    assert row["freshness_status"] == "fresh"
    assert row["dirty_status"] == "untracked"
    assert row["commit_policy"] == "serial_drainer_only"


def test_landing_plan_exposes_dirty_subset_separately_from_owner_bundle(tmp_path: Path) -> None:
    root = tmp_path
    index_path = _open_work_ledger_thread(root)
    source_rel = "codex/ledger/09_52/work_ledger.jsonl"

    plan = build_generated_projection_landing_plan(
        root,
        owner_id=WORK_LEDGER_OWNER_ID,
        status_map={
            source_rel: " M",
            str(index_path.relative_to(root)): "",
        },
    )

    assert source_rel in plan["source_authority_paths"]
    assert plan["source_authority_paths_to_stage"] == [source_rel]
    assert plan["projection_paths_to_stage"] == []
    assert plan["dirty_path_summary"]["source_authority_dirty_count"] == 1
    assert plan["dirty_path_summary"]["projection_dirty_count"] == 0
    assert plan["dirty_path_summary"]["projection_clean_count"] == len(plan["projection_paths"])
    assert "exact dirty subset" in plan["owner_bundle_rationale"]


def test_status_reports_source_authority_missing_when_projections_exist_without_events(tmp_path: Path) -> None:
    """Case B: events.jsonl absent but projection artifacts exist on disk.

    A pristine repo with neither events nor projections (case A) is correctly
    skipped by the absence guard so default scans do not emit phantom-stale
    rows. But when projection artifacts exist without their source authority,
    the drainer must surface them as ``source_authority_missing`` rather than
    silently reporting ``fresh_clean`` — that would be a regression on the
    operator-stated invariant that index/projection surfaces declare freshness
    rather than hide it.
    """
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    # Establish projection artifacts via the normal apply path.
    _append_task_ledger_capture(root)
    events_path = root / task_ledger_events.EVENTS_REL
    ledger_path = root / task_ledger_events.LEDGER_REL
    assert events_path.exists()
    assert ledger_path.exists()
    # Now orphan the projections by removing the source authority.
    events_path.unlink()

    status = build_generated_state_drainer_status(root, owner_ids=[TASK_LEDGER_OWNER_ID])
    task_rows = [r for r in status["projection_targets"] if r["owner_id"] == TASK_LEDGER_OWNER_ID]

    assert task_rows, "expected at least one source_authority_missing row for orphaned projections"
    assert all(r["freshness_status"] == "source_authority_missing" for r in task_rows)
    assert all(r["safe_to_commit_by_agent"] is False for r in task_rows)
    assert all(r["commit_policy"] == "serial_drainer_only" for r in task_rows)
    assert status["summary"]["stale_count"] >= 1
    assert status["summary"]["status"] == "stale"

    check = status["owner_checks"][TASK_LEDGER_OWNER_ID]
    assert check["ok"] is False
    assert check["reason"] == "source_authority_missing_with_existing_projections"
    assert check["existing_artifact_count"] >= 1


def test_status_skips_task_ledger_when_repo_is_uninitialized(tmp_path: Path) -> None:
    """Case A: pure uninitialized — no events.jsonl AND no projection artifacts.

    The default scan must not emit phantom rows; the absence guard returns
    cleanly so a pristine repo is reported as fresh_clean for Task Ledger.
    """
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)

    status = build_generated_state_drainer_status(root, owner_ids=[TASK_LEDGER_OWNER_ID])
    task_rows = [r for r in status["projection_targets"] if r["owner_id"] == TASK_LEDGER_OWNER_ID]

    assert task_rows == []
    check = status["owner_checks"][TASK_LEDGER_OWNER_ID]
    assert check["ok"] is True
    assert check["reason"] == "task_ledger_events_log_absent"


def test_status_task_ledger_owner_uses_mission_blackboard_like_rebuild_check(tmp_path: Path) -> None:
    root = tmp_path
    _append_task_ledger_capture(root)
    _write_mission_blackboard(root)
    rebuild = task_ledger_events.rebuild_projections(root)
    assert rebuild["ok"] is True

    owner_check = task_ledger_events.rebuild_projections(root, check=True)
    assert owner_check["ok"] is True
    assert owner_check["mismatches"] == []

    status = build_generated_state_drainer_status(root, owner_ids=[TASK_LEDGER_OWNER_ID])
    check = status["owner_checks"][TASK_LEDGER_OWNER_ID]
    stale_paths = [
        row["generated_path"]
        for row in status["projection_targets"]
        if row["owner_id"] == TASK_LEDGER_OWNER_ID and row["freshness_status"] != "fresh"
    ]

    assert check["ok"] is True
    assert check["mismatches"] == []
    assert stale_paths == []


def _orphan_task_ledger_projections(root: Path) -> None:
    """Set up Task Ledger projection artifacts then remove the events.jsonl source authority."""
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    events_path = root / task_ledger_events.EVENTS_REL
    assert events_path.exists()
    assert (root / task_ledger_events.LEDGER_REL).exists()
    events_path.unlink()


def test_landing_plan_refuses_source_authority_missing_task_ledger_projection(tmp_path: Path) -> None:
    """Case B at landing layer: events.jsonl absent but projections exist.

    The landing plan must refuse to apply, must not recommend a refresh that
    cannot succeed without source authority, and must surface the reason as
    source_authority_missing rather than the ordinary projection_not_fresh
    blocker. Otherwise, settlement can attempt to rebuild orphaned projections
    and silently re-introduce a false-green at the egress layer.
    """
    root = tmp_path
    _orphan_task_ledger_projections(root)

    plan = build_generated_projection_landing_plan(root, owner_id=TASK_LEDGER_OWNER_ID)

    assert plan["schema"] == "generated_projection_landing_plan_v0"
    assert plan["owner_id"] == TASK_LEDGER_OWNER_ID
    assert plan["can_apply"] is False
    assert plan["status"] not in {"already_landed", "append_exempt_manifest_available"}
    assert "source_authority_missing" in plan.get("blocked_by", [])
    refresh_action_hint = "apply --only " + TASK_LEDGER_REFRESH_ACTION
    assert refresh_action_hint not in str(plan.get("required_next_command") or "")


def test_settlement_plan_refuses_source_authority_missing_task_ledger_projection(tmp_path: Path) -> None:
    """Case B at settlement layer: refresh_then_land_append_exempt is the wrong action.

    A refresh requires events.jsonl. With source authority absent, settlement
    must report blocked rather than scheduling a refresh that would fail.
    """
    root = tmp_path
    _orphan_task_ledger_projections(root)

    plan = build_generated_projection_settlement_plan(root, owner_ids=[TASK_LEDGER_OWNER_ID])

    rows = [r for r in plan.get("owners") or [] if r.get("owner_id") == TASK_LEDGER_OWNER_ID]
    assert len(rows) == 1
    row = rows[0]
    assert row.get("required_action") != "refresh_then_land_append_exempt"
    assert row.get("required_action") in {"blocked"}
    assert row.get("can_apply") is False


def test_landing_plan_for_fresh_dirty_work_ledger_indexes(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _open_work_ledger_thread(root)

    plan = build_generated_projection_landing_plan(root)

    assert plan["schema"] == "generated_projection_landing_plan_v0"
    assert plan["owner_id"] == "work_ledger_index_projection"
    assert plan["freshness_status"] == "fresh_dirty"
    assert plan["dirty_status"] == "dirty"
    assert plan["normal_agent_commit_allowed"] is False
    assert plan["safe_to_commit_by_agent"] is False
    assert plan["self_invalidating_if_eventful"] is True
    assert plan["scoped_commit_directly_appends_work_ledger_event"] is False
    assert plan["append_exempt_policy_verified"] is True
    assert plan["recommended_mode"] == "append_exempt_projection_landing"
    assert plan["can_apply"] is True
    assert plan["blocked_by"] == []
    assert plan["landing_manifest_path"] == "state/generated_projection_landing/work_ledger_index_projection_manifest.json"
    assert plan["projection_paths"] == ["codex/ledger/09_52/work_ledger_index.json"]
    assert plan["source_authority_paths"] == ["codex/ledger/09_52/work_ledger.jsonl"]
    assert plan["source_authority_paths_to_stage"] == ["codex/ledger/09_52/work_ledger.jsonl"]
    assert plan["source_event_hash"]
    assert plan["projection_hashes"]["codex/ledger/09_52/work_ledger_index.json"]
    assert plan["diff_stat"]["review_status"] == "watch"


def test_landing_plan_requires_refresh_for_stale_projection(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _make_projection_stale(root)

    plan = build_generated_projection_landing_plan(root)

    assert plan["status"] == "refresh_required"
    assert plan["freshness_status"] == "stale"
    assert plan["can_apply"] is False
    assert plan["blocked_by"] == ["projection_not_fresh"]
    assert plan["required_next_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py apply --only "
        "work_ledger_projection_refresh"
    )


def test_append_exempt_landing_dry_run_reports_manifest_and_exact_paths(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _open_work_ledger_thread(root)

    result = land_generated_projection_bundle(root, mode=APPEND_EXEMPT_LANDING_MODE, dry_run=True)

    assert result["schema"] == "generated_projection_landing_v0"
    assert result["ok"] is True
    assert result["status"] == "would_land"
    assert result["normal_work_ledger_event_after_refresh_allowed"] is False
    assert result["paths_to_stage"] == [
        "codex/ledger/09_52/work_ledger.jsonl",
        "codex/ledger/09_52/work_ledger_index.json",
        "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
    ]
    manifest = result["manifest"]
    assert manifest["schema"] == LANDING_MANIFEST_SCHEMA
    assert manifest["landing_mode"] == "append_exempt_projection_landing"
    assert manifest["normal_work_ledger_event_after_refresh_allowed"] is False
    assert manifest["source_authority_paths_included"] == ["codex/ledger/09_52/work_ledger.jsonl"]
    assert "no Work Ledger event is appended after projection refresh" in manifest["source_inclusion_reason"]
    assert manifest["source_event_hashes"]["09"]
    assert manifest["projection_hashes"]["codex/ledger/09_52/work_ledger_index.json"]


def test_append_exempt_landing_progress_callback_reports_phase_boundaries(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _open_work_ledger_thread(root)
    progress: list[dict] = []

    result = land_generated_projection_bundle(
        root,
        mode=APPEND_EXEMPT_LANDING_MODE,
        dry_run=True,
        progress_callback=progress.append,
    )

    assert result["ok"] is True
    events = [row["event"] for row in progress]
    assert events[0] == "start"
    assert "landing_plan_ready" in events
    assert "manifest_ready" in events
    assert "paths_selected" in events
    assert events[-1] == "done"
    assert all(row["schema"] == "generated_state_drainer_progress_v0" for row in progress)
    assert all(row["privacy"] == "phase_names_counts_and_status_only_no_stdout_stderr_bodies" for row in progress)


def test_append_exempt_landing_refuses_stale_projection(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _make_projection_stale(root)

    result = land_generated_projection_bundle(root, mode=APPEND_EXEMPT_LANDING_MODE, dry_run=True)

    assert result["ok"] is False
    assert result["status"] == "refresh_required"
    assert result["blocked_by"] == ["projection_not_fresh"]


def test_append_exempt_landing_refuses_unsupported_owner(tmp_path: Path) -> None:
    result = land_generated_projection_bundle(
        tmp_path,
        owner_id="unsupported_projection_owner",
        mode=APPEND_EXEMPT_LANDING_MODE,
        dry_run=True,
    )

    assert result["ok"] is False
    assert result["status"] == "refused"
    assert result["reason"] == "unsupported_owner_for_landing"


def test_append_exempt_landing_commits_without_appending_work_ledger_event(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _open_work_ledger_thread(root)
    event_count_before = len(work_ledger.load_events(root, family_id="09"))

    result = land_generated_projection_bundle(root, mode=APPEND_EXEMPT_LANDING_MODE)

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert result["commit_hash"]
    assert result["normal_work_ledger_event_after_refresh_allowed"] is False
    assert len(work_ledger.load_events(root, family_id="09")) == event_count_before
    manifest_path = root / "state/generated_projection_landing/work_ledger_index_projection_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == LANDING_MANIFEST_SCHEMA
    assert manifest["commit_hash"] is None


def test_landing_plan_for_fresh_dirty_task_ledger_projections(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)

    plan = build_generated_projection_landing_plan(root, owner_id=TASK_LEDGER_OWNER_ID)

    assert plan["schema"] == "generated_projection_landing_plan_v0"
    assert plan["owner_id"] == TASK_LEDGER_OWNER_ID
    assert plan["status"] == "append_exempt_manifest_available"
    assert plan["freshness_status"] == "fresh_dirty"
    assert plan["dirty_status"] == "dirty"
    assert plan["source_authority"] == "state/task_ledger/events.jsonl"
    assert plan["source_authority_paths"] == [
        "state/task_ledger/events.jsonl",
        "state/task_ledger/events_audit.jsonl",
    ]
    assert plan["source_authority_paths_to_stage"] == [
        "state/task_ledger/events.jsonl",
        "state/task_ledger/events_audit.jsonl",
    ]
    assert "state/task_ledger/ledger.json" in plan["projection_paths"]
    assert "state/task_ledger/sign_offs.json" in plan["projection_paths"]
    assert any(path.startswith("state/task_ledger/views/") for path in plan["projection_paths"])
    assert plan["projection_hashes"]["state/task_ledger/ledger.json"]
    assert plan["normal_task_ledger_event_after_refresh_allowed"] is False
    assert plan["normal_agent_commit_allowed"] is False
    assert plan["safe_to_commit_by_agent"] is False
    assert plan["recommended_mode"] == "append_exempt_projection_landing"
    assert plan["can_apply"] is True
    assert plan["blocked_by"] == []
    assert plan["landing_manifest_path"] == "state/generated_projection_landing/task_ledger_projection_manifest.json"


def test_task_ledger_landing_plan_passes_repo_root_to_projection_builder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    original_build_projection = task_ledger_events.build_projection
    observed: dict[str, Path | None] = {}

    def record_build_projection(*args, **kwargs):
        observed["repo_root"] = kwargs.get("repo_root")
        return original_build_projection(*args, **kwargs)

    monkeypatch.setattr(task_ledger_events, "build_projection", record_build_projection)

    plan = build_generated_projection_landing_plan(root, owner_id=TASK_LEDGER_OWNER_ID)

    assert observed["repo_root"] == root
    assert plan["status"] == "append_exempt_manifest_available"


def test_landing_plan_requires_refresh_for_stale_task_ledger_projection(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _make_task_ledger_projection_stale(root)

    plan = build_generated_projection_landing_plan(root, owner_id=TASK_LEDGER_OWNER_ID)

    assert plan["status"] == "refresh_required"
    assert plan["freshness_status"] == "stale"
    assert plan["can_apply"] is False
    assert plan["blocked_by"] == ["projection_not_fresh"]
    assert plan["required_next_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py apply --only "
        "task_ledger_projection_refresh"
    )


def test_task_ledger_append_exempt_landing_dry_run_reports_manifest_and_exact_paths(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        dry_run=True,
    )

    assert result["schema"] == "generated_projection_landing_v0"
    assert result["ok"] is True
    assert result["status"] == "would_land"
    assert result["normal_task_ledger_event_after_refresh_allowed"] is False
    assert "state/task_ledger/events.jsonl" in result["paths_to_stage"]
    assert "state/task_ledger/events_audit.jsonl" in result["paths_to_stage"]
    assert "state/task_ledger/ledger.json" in result["paths_to_stage"]
    assert "state/task_ledger/sign_offs.json" in result["paths_to_stage"]
    assert "state/generated_projection_landing/task_ledger_projection_manifest.json" in result["paths_to_stage"]
    assert any(path.startswith("state/task_ledger/views/") for path in result["paths_to_stage"])
    manifest = result["manifest"]
    assert manifest["schema"] == LANDING_MANIFEST_SCHEMA
    assert manifest["owner_id"] == TASK_LEDGER_OWNER_ID
    assert manifest["landing_mode"] == "append_exempt_projection_landing"
    assert manifest["normal_task_ledger_event_after_refresh_allowed"] is False
    assert manifest["source_authority_paths_included"] == [
        "state/task_ledger/events.jsonl",
        "state/task_ledger/events_audit.jsonl",
    ]
    assert "no Task Ledger event is appended after projection refresh" in manifest["source_inclusion_reason"]
    assert manifest["source_event_hashes"][TASK_LEDGER_OWNER_ID]
    assert manifest["projection_hashes"]["state/task_ledger/ledger.json"]


def test_task_ledger_append_exempt_landing_commits_without_appending_task_ledger_event(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)
    event_count_before = len(task_ledger_events.load_and_validate_events(root))

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert result["commit_hash"]
    assert result["normal_task_ledger_event_after_refresh_allowed"] is False
    assert str(task_ledger_events.EVENTS_AUDIT_REL) in result["paths_staged"]
    assert len(task_ledger_events.load_and_validate_events(root)) == event_count_before
    assert subprocess.run(
        ["git", "status", "--short", "--", str(task_ledger_events.EVENTS_AUDIT_REL)],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout == ""
    manifest_path = root / "state/generated_projection_landing/task_ledger_projection_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == LANDING_MANIFEST_SCHEMA
    assert manifest["commit_hash"] is None


def test_task_ledger_landing_does_not_refresh_fresh_dirty_bundle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    original_rebuild = task_ledger_events.rebuild_projections

    def fail_non_check_rebuild(repo_root: Path, *, check: bool = False):
        if not check:
            raise AssertionError("fresh-dirty append-exempt landing must not rebuild Task Ledger projections")
        return original_rebuild(repo_root, check=check)

    monkeypatch.setattr(task_ledger_events, "rebuild_projections", fail_non_check_rebuild)

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        commit_func=_fake_scoped_commit_result,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert original_rebuild(root, check=True)["ok"] is True


def test_append_exempt_landing_filters_clean_declared_paths_before_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    event_log = root / task_ledger_events.EVENTS_REL
    event_log.parent.mkdir(parents=True, exist_ok=True)
    event_log.write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "add", str(task_ledger_events.EVENTS_REL)],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["git", "commit", "-m", "seed clean task ledger event log"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    def fake_plan(repo_root: Path, *, owner_id: str = TASK_LEDGER_OWNER_ID):
        assert owner_id == TASK_LEDGER_OWNER_ID
        return {
            "schema": "generated_projection_landing_plan_v0",
            "ok": True,
            "owner_id": TASK_LEDGER_OWNER_ID,
            "status": "append_exempt_manifest_available",
            "source_authority": "state/task_ledger/events.jsonl",
            "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
            "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
            "source_event_hashes": {},
            "source_path_hashes": {},
            "projection_paths": [],
            "projection_hashes": {},
            "freshness_status": "fresh_dirty",
            "dirty_status": "dirty",
            "source_dirty_status": "dirty",
            "diff_stat": {},
            "self_invalidation_reason": "test fixture",
            "can_apply": True,
            "blocked_by": [],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_landing_plan", fake_plan)

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        commit_func=_fake_scoped_commit_result,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert result["paths_staged"] == [
        "state/generated_projection_landing/task_ledger_projection_manifest.json"
    ]


def test_append_exempt_landing_ignores_index_only_manifest_residue(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    plan = {
        "schema": "generated_projection_landing_plan_v0",
        "ok": True,
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "source_authority": "state/task_ledger/events.jsonl",
        "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
        "source_authority_paths_to_stage": [],
        "source_event_hashes": {},
        "source_path_hashes": {},
        "projection_paths": [],
        "projection_hashes": {},
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "diff_stat": {},
        "self_invalidation_reason": "test fixture",
        "can_apply": True,
        "blocked_by": [],
    }
    manifest_rel = Path("state/generated_projection_landing/task_ledger_projection_manifest.json")
    manifest_path = root / manifest_rel
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = generated_state_drainer.build_generated_projection_landing_manifest(root, plan=plan)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(manifest_rel)], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(
        ["git", "commit", "-m", "seed landing manifest"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    manifest_path.write_text("{\"schema\":\"staged-residue\"}\n", encoding="utf-8")
    subprocess.run(["git", "add", str(manifest_rel)], cwd=root, check=True, stdout=subprocess.DEVNULL)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_landing_plan",
        lambda repo_root, *, owner_id=TASK_LEDGER_OWNER_ID: plan,
    )

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
    )

    assert result["ok"] is True
    assert result["status"] == "already_landed"
    assert result["paths_to_stage"] == []


def test_append_exempt_landing_refreshes_index_only_projection_residue(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    projection_rel = Path("state/task_ledger/views/incomplete_work_items.json")
    projection_path = root / projection_rel
    projection_path.parent.mkdir(parents=True, exist_ok=True)
    current_payload = {"kind": "task_ledger_view", "items": ["current"]}
    stale_payload = {"kind": "task_ledger_view", "items": ["stale"]}
    projection_path.write_text(json.dumps(current_payload, indent=2) + "\n", encoding="utf-8")

    plan = {
        "schema": "generated_projection_landing_plan_v0",
        "ok": True,
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "source_authority": "state/task_ledger/events.jsonl",
        "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
        "source_authority_paths_to_stage": [],
        "source_event_hashes": {},
        "source_path_hashes": {},
        "projection_paths": [str(projection_rel)],
        "projection_hashes": {str(projection_rel): "sha256:test"},
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "diff_stat": {},
        "self_invalidation_reason": "test fixture",
        "can_apply": True,
        "blocked_by": [],
    }
    manifest_rel = Path("state/generated_projection_landing/task_ledger_projection_manifest.json")
    manifest_path = root / manifest_rel
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = generated_state_drainer.build_generated_projection_landing_manifest(root, plan=plan)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(projection_rel), str(manifest_rel)], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(
        ["git", "commit", "-m", "seed generated projection"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    projection_path.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(projection_rel)], cwd=root, check=True, stdout=subprocess.DEVNULL)
    projection_path.write_text(json.dumps(current_payload, indent=2) + "\n", encoding="utf-8")

    assert subprocess.run(
        ["git", "status", "--short", "--", str(projection_rel)],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.startswith("MM ")

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_landing_plan",
        lambda repo_root, *, owner_id=TASK_LEDGER_OWNER_ID: plan,
    )

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
    )

    assert result["ok"] is True
    assert result["status"] == "already_landed"
    assert result["reason"] == "index_only_projection_residue_refreshed"
    assert result["paths_index_refreshed"] == [str(projection_rel)]
    assert subprocess.run(
        ["git", "status", "--short", "--", str(projection_rel)],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout == ""


def test_append_exempt_landing_refreshes_index_only_projection_residue_after_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    source_rel = str(task_ledger_events.EVENTS_REL)
    projection_rel = "state/task_ledger/views/incomplete_work_items.json"
    refreshed = generated_state_drainer._refresh_index_only_projection_residue(
        root,
        [],
    )
    assert refreshed == []

    plan = {
        "schema": "generated_projection_landing_plan_v0",
        "ok": True,
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "source_authority": "state/task_ledger/events.jsonl",
        "source_authority_paths": [source_rel],
        "source_authority_paths_to_stage": [source_rel],
        "source_event_hashes": {},
        "source_path_hashes": {},
        "projection_paths": [projection_rel],
        "projection_hashes": {projection_rel: "sha256:test"},
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "diff_stat": {},
        "self_invalidation_reason": "test fixture",
        "can_apply": True,
        "blocked_by": [],
    }

    monkeypatch.setattr(generated_state_drainer, "_git_status_map", lambda repo_root: {})
    monkeypatch.setattr(
        generated_state_drainer,
        "_dirty_existing_paths",
        lambda repo_root, paths, *, status_map=None: [projection_rel],
    )
    monkeypatch.setattr(
        generated_state_drainer,
        "_head_changed_existing_paths",
        lambda repo_root, paths, *, status_map=None: [source_rel],
    )
    monkeypatch.setattr(
        generated_state_drainer,
        "_refresh_index_only_projection_residue",
        lambda repo_root, paths, *, status_map=None: [projection_rel],
    )

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        landing_plan=plan,
        commit_func=_fake_scoped_commit_result,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert result["paths_index_refreshed"] == [projection_rel]


def test_work_ledger_landing_does_not_refresh_fresh_dirty_bundle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _open_work_ledger_thread(root)

    def fail_project_all(repo_root: Path):
        raise AssertionError("fresh-dirty append-exempt landing must not rebuild Work Ledger projections")

    monkeypatch.setattr(work_ledger, "project_all", fail_project_all)

    result = land_generated_projection_bundle(
        root,
        mode=APPEND_EXEMPT_LANDING_MODE,
        commit_func=_fake_scoped_commit_result,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert work_ledger.check_project_all(root)["ok"] is True


def test_task_ledger_projection_owner_is_distinct_and_apply_supported(tmp_path: Path) -> None:
    owner = get_projection_owner(TASK_LEDGER_OWNER_ID)

    assert "state/task_ledger/ledger.json" in owner.artifacts
    assert "state/task_ledger/events.jsonl" in owner.source_authorities
    assert owner.repair_command == ("./repo-python", "tools/meta/factory/task_ledger_apply.py", "rebuild")

    root = tmp_path
    _open_work_ledger_thread(root)
    status = build_generated_state_drainer_status(root)
    owner_rows = {row["owner_id"]: row for row in status["owners"]}

    assert owner_rows[TASK_LEDGER_OWNER_ID]["apply_supported"] is True
    assert owner_rows["work_ledger_index_projection"]["apply_supported"] is True


def test_system_atlas_landing_plan_blocks_source_coupling_before_projection_landing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    atlas_path = root / "state/system_atlas/system_atlas.graph.json"
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    atlas_path.write_text("{}\n", encoding="utf-8")

    def fake_owner_check(repo_root: Path, argv):
        return {
            "ok": False,
            "source_coupling": {
                "status": "source_inputs_changed_since_artifact_generation",
                "reason": "fixture source moved",
                "changed_source_count": 1,
                "blocking_changed_source_count": 1,
                "dirty_changed_source_count": 0,
                "safe_to_commit_generated_outputs_without_sources": False,
                "blocking_changed_sources": [
                    {
                        "source_id": "task_ledger_ledger",
                        "path": "state/task_ledger/ledger.json",
                        "git_pathspec": "state/task_ledger/ledger.json",
                        "owner_route_hint": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
                    }
                ],
            },
        }

    monkeypatch.setattr(generated_state_drainer, "_run_owner_json_command", fake_owner_check)

    plan = build_generated_projection_landing_plan(root, owner_id=SYSTEM_ATLAS_OWNER_ID)
    settlement = build_generated_projection_settlement_plan(root, owner_ids=[SYSTEM_ATLAS_OWNER_ID])

    assert plan["owner_id"] == SYSTEM_ATLAS_OWNER_ID
    assert plan["status"] == "source_coupling_unsettled"
    assert plan["can_apply"] is False
    assert plan["blocked_by"] == ["source_coupling_not_settled"]
    assert plan["source_authority"] == "generated_projection_registry.source_authorities"
    assert plan["bloat_class"] == "system_atlas_projection_event_or_projection"
    assert plan["owner_handoff_class"] == "source_coupling_source_owner_handoff"
    assert plan["source_coupling"]["safe_to_commit_generated_outputs_without_sources"] is False
    assert plan["source_coupling"]["blocking_changed_sources_sample"][0]["path"] == "state/task_ledger/ledger.json"
    assert plan["source_coupling_owner_route_hints"] == [
        "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check"
    ]
    assert settlement["status"] == "blocked"
    assert settlement["owners"][0]["required_action"] == "blocked"
    assert settlement["owners"][0]["owner_handoff_class"] == "source_coupling_source_owner_handoff"
    assert settlement["owners"][0]["required_owner_resolution"].startswith("Settle or claim")
    assert settlement["owners"][0]["source_coupling"]["blocking_changed_sources_sample"][0]["source_id"] == (
        "task_ledger_ledger"
    )
    assert "owner_settlement_blocked" in settlement["blocked_by"]


def test_fast_settlement_plan_supports_explicit_system_atlas_owner_without_owner_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    atlas_path = root / "state/system_atlas/system_atlas.graph.json"
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    atlas_path.write_text("{}\n", encoding="utf-8")

    def fail_owner_check(*args, **kwargs):
        raise AssertionError("fast System Atlas settlement plan must not run owner checks")

    monkeypatch.setattr(generated_state_drainer, "_run_owner_json_command", fail_owner_check)

    plan = build_generated_projection_settlement_fast_plan(root, owner_ids=[SYSTEM_ATLAS_OWNER_ID])
    owner = plan["owners"][0]

    assert plan["schema"] == "generated_projection_settlement_plan_v0"
    assert plan["supported_owner_ids"][-1] == SYSTEM_ATLAS_OWNER_ID
    assert owner["owner_id"] == SYSTEM_ATLAS_OWNER_ID
    assert owner["blocked_by"] == []
    assert owner["planning_mode"] == "cached_git_status"
    assert owner["source_authority"] == "generated_projection_registry.source_authorities"
    assert "state/system_atlas/system_atlas.graph.json" in owner["projection_paths"]


def test_fast_settlement_plan_includes_system_atlas_in_default_owner_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    atlas_path = root / "state/system_atlas/system_atlas.graph.json"
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    atlas_path.write_text("{}\n", encoding="utf-8")

    def fail_owner_check(*args, **kwargs):
        raise AssertionError("fast default settlement plan must not run owner checks")

    monkeypatch.setattr(generated_state_drainer, "_run_owner_json_command", fail_owner_check)

    plan = build_generated_projection_settlement_fast_plan(root)
    owner_ids = [owner["owner_id"] for owner in plan["owners"]]
    owner_by_id = {owner["owner_id"]: owner for owner in plan["owners"]}

    assert owner_ids == [TASK_LEDGER_OWNER_ID, WORK_LEDGER_OWNER_ID, SYSTEM_ATLAS_OWNER_ID]
    assert plan["status"] == "settlement_required"
    assert plan["settlement_order"] == owner_ids
    assert owner_by_id[SYSTEM_ATLAS_OWNER_ID]["required_action"] == "land_append_exempt"
    assert "state/system_atlas/system_atlas.graph.json" in owner_by_id[SYSTEM_ATLAS_OWNER_ID]["projection_paths_to_stage"]


def test_apply_refreshes_work_ledger_projection_lane(tmp_path: Path) -> None:
    root = tmp_path
    _make_projection_stale(root)

    dry_run = apply_generated_state_drainer(root, only=WORK_LEDGER_REFRESH_ACTION, dry_run=True)
    assert dry_run["schema"] == "generated_state_drainer_apply_v0"
    assert dry_run["status"] == "would_apply"
    assert dry_run["action"]["scope"] == "codex/ledger/*/work_ledger_index.json"

    applied = apply_generated_state_drainer(root, only=WORK_LEDGER_REFRESH_ACTION)
    assert applied["ok"] is True
    assert applied["status"] == "applied"
    assert applied["after"]["summary"]["stale_count"] == 0
    assert work_ledger.check_project_all(root)["ok"] is True


def test_apply_refreshes_task_ledger_projection_lane(tmp_path: Path) -> None:
    root = tmp_path
    _make_task_ledger_projection_stale(root)

    dry_run = apply_generated_state_drainer(root, only=TASK_LEDGER_REFRESH_ACTION, dry_run=True)
    assert dry_run["schema"] == "generated_state_drainer_apply_v0"
    assert dry_run["status"] == "would_apply"
    assert dry_run["action"]["scope"] == "state/task_ledger/{ledger.json,sign_offs.json,views/*.json}"

    applied = apply_generated_state_drainer(root, only=TASK_LEDGER_REFRESH_ACTION)
    assert applied["ok"] is True
    assert applied["status"] == "applied"
    assert applied["after"]["summary"]["stale_count"] == 0
    assert task_ledger_events.rebuild_projections(root, check=True)["ok"] is True


def test_apply_refuses_unsupported_actions(tmp_path: Path) -> None:
    root = tmp_path

    result = apply_generated_state_drainer(root, only="unsupported_projection_refresh")

    assert result["ok"] is False
    assert result["status"] == "refused"
    assert result["reason"] == "unsupported_action"
    assert result["supported_actions"] == [
        WORK_LEDGER_REFRESH_ACTION,
        TASK_LEDGER_REFRESH_ACTION,
        generated_state_drainer.SYSTEM_ATLAS_REFRESH_ACTION,
    ]


def test_settlement_plan_reports_clean_when_supported_owners_are_landed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    plans = {
        TASK_LEDGER_OWNER_ID: _landing_plan_fixture(
            owner_id=TASK_LEDGER_OWNER_ID,
            status="already_landed",
        ),
        WORK_LEDGER_OWNER_ID: _landing_plan_fixture(
            owner_id=WORK_LEDGER_OWNER_ID,
            status="already_landed",
        ),
        SYSTEM_ATLAS_OWNER_ID: _landing_plan_fixture(
            owner_id=SYSTEM_ATLAS_OWNER_ID,
            status="already_landed",
        ),
    }

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_landing_plan",
        lambda repo_root, *, owner_id, **kwargs: plans[owner_id],
    )

    plan = build_generated_projection_settlement_plan(root)

    assert plan["schema"] == "generated_projection_settlement_plan_v0"
    assert plan["status"] == "clean"
    assert plan["can_settle"] is True
    assert plan["dirty_owner_count"] == 0
    assert plan["settlement_order"] == [TASK_LEDGER_OWNER_ID, WORK_LEDGER_OWNER_ID, SYSTEM_ATLAS_OWNER_ID]
    assert [row["required_action"] for row in plan["owners"]] == ["none", "none", "none"]
    assert plan["eventful_closeout_allowed_after_settlement"] is False


def test_settlement_plan_reports_dirty_owners_in_settlement_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    plans = {
        TASK_LEDGER_OWNER_ID: _landing_plan_fixture(
            owner_id=TASK_LEDGER_OWNER_ID,
            status="append_exempt_manifest_available",
            dirty_status="dirty",
            source_dirty_status="dirty",
        ),
        WORK_LEDGER_OWNER_ID: _landing_plan_fixture(
            owner_id=WORK_LEDGER_OWNER_ID,
            status="append_exempt_manifest_available",
            dirty_status="dirty",
            source_dirty_status="dirty",
        ),
        SYSTEM_ATLAS_OWNER_ID: _landing_plan_fixture(
            owner_id=SYSTEM_ATLAS_OWNER_ID,
            status="already_landed",
        ),
    }

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_landing_plan",
        lambda repo_root, *, owner_id, **kwargs: plans[owner_id],
    )

    plan = build_generated_projection_settlement_plan(root)

    assert plan["status"] == "settlement_required"
    assert plan["can_settle"] is True
    assert plan["required_next_command"] == "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
    by_owner = {row["owner_id"]: row for row in plan["owners"]}
    assert by_owner[TASK_LEDGER_OWNER_ID]["required_action"] == "land_append_exempt"
    assert by_owner[WORK_LEDGER_OWNER_ID]["required_action"] == "land_append_exempt"
    assert by_owner[SYSTEM_ATLAS_OWNER_ID]["required_action"] == "none"
    assert plan["owners"][0]["owner_id"] == TASK_LEDGER_OWNER_ID
    assert plan["owners"][1]["owner_id"] == WORK_LEDGER_OWNER_ID
    assert plan["owners"][2]["owner_id"] == SYSTEM_ATLAS_OWNER_ID


def test_settlement_dry_run_reports_owner_paths_without_appending_events(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    _open_work_ledger_thread(root)
    task_event_count = len(task_ledger_events.load_and_validate_events(root))
    work_event_count = len(work_ledger.load_events(root, family_id="09"))

    result = settle_generated_projection_owners(root, dry_run=True)

    assert result["schema"] == "generated_projection_settlement_v0"
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["status"] == "would_settle"
    assert result["settlement_done"] is False
    assert result["validation_done"] is False
    assert result["refinement_done"] is False
    assert result["settlement_is_not_refinement"] is True
    assert result["stewardship_checked"] is True
    assert result["next_best_lane_checked"] is True
    assert result["timing"]["schema"] == "generated_projection_settlement_timing_v0"
    assert result["timing"]["total_wall_ms"] >= 0
    assert result["timing"]["privacy"] == "phase_names_wall_time_and_counts_only_no_stdout_stderr_bodies"
    assert {row["phase"] for row in result["timing"]["phases"]} >= {"initial_plan", "owner_dry_run"}
    assert all("wall_ms" in row for row in result["timing"]["phases"])
    task_bundle = result["stewardship_check"]["source_bundle_by_owner"][TASK_LEDGER_OWNER_ID]
    assert "state/task_ledger/events.jsonl" in task_bundle["source_authority_paths"]
    assert "state/task_ledger/events_audit.jsonl" in task_bundle["source_authority_paths"]
    assert result["stewardship_check"]["omitted_audit_or_source_sidecars"] == []
    assert [row["owner_id"] for row in result["owners"]] == [
        TASK_LEDGER_OWNER_ID,
        WORK_LEDGER_OWNER_ID,
        SYSTEM_ATLAS_OWNER_ID,
    ]
    assert result["resource_lease_status"]["status"] == "unavailable"
    assert result["duplicate_settlement_guard"]["resource_class"] == "generated_state"
    assert result["duplicate_settlement_guard"]["entrypoint"].endswith("generated_state_drainer.py settle")
    assert any(event["event"] == "pass_start" for event in result["progress_events"])
    task_owner = result["owners"][0]
    work_owner = result["owners"][1]
    task_paths = task_owner["paths_to_stage"]
    work_paths = work_owner["paths_to_stage"]
    assert "state/task_ledger/events.jsonl" in task_paths
    assert "state/task_ledger/events_audit.jsonl" in task_paths
    assert "state/task_ledger/ledger.json" in task_paths
    assert "codex/ledger/09_52/work_ledger.jsonl" in work_paths
    assert "codex/ledger/09_52/work_ledger_index.json" in work_paths
    assert "state/task_ledger/events.jsonl" in task_owner["source_authority_paths"]
    assert "state/task_ledger/events_audit.jsonl" in task_owner["source_authority_paths"]
    assert "state/task_ledger/events_audit.jsonl" in task_owner["source_authority_paths_to_stage"]
    assert "state/task_ledger/ledger.json" in task_owner["projection_paths"]
    assert (
        task_owner["path_bundle"]["landing_manifest_path"]
        == "state/generated_projection_landing/task_ledger_projection_manifest.json"
    )
    assert task_owner["owner_bundle_completeness"]["task_ledger_audit_journal_declared"] is True
    assert task_owner["owner_bundle_completeness"]["all_expected_stage_paths_reported"] is True
    assert work_owner["owner_bundle_completeness"]["landing_manifest_included"] is True
    assert len(task_ledger_events.load_and_validate_events(root)) == task_event_count
    assert len(work_ledger.load_events(root, family_id="09")) == work_event_count


def test_settlement_progress_callback_reports_plan_and_owner_boundaries(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    progress: list[dict] = []

    result = settle_generated_projection_owners(
        root,
        owner_ids=[TASK_LEDGER_OWNER_ID],
        dry_run=True,
        fast_plan=True,
        progress_callback=progress.append,
    )

    assert result["ok"] is True
    events = [row["event"] for row in progress]
    assert events[0] == "start"
    assert "initial_plan_start" in events
    assert "initial_plan_done" in events
    assert "pass_start" in events
    assert "owner_start" in events
    assert "owner_done" in events
    assert events[-1] == "done"
    assert progress[-1]["status"] == "would_settle"


def test_settlement_owner_receipt_expects_only_dirty_projection_stage_paths() -> None:
    manifest = "state/generated_projection_landing/task_ledger_projection_manifest.json"
    owner = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "source_authority_paths": [
            "state/task_ledger/events.jsonl",
            "state/task_ledger/events_audit.jsonl",
        ],
        "source_authority_paths_to_stage": ["state/task_ledger/events.jsonl"],
        "projection_paths": [
            "state/task_ledger/ledger.json",
            "state/task_ledger/views/cap_census.json",
        ],
        "projection_paths_to_stage": ["state/task_ledger/ledger.json"],
        "path_bundle": {
            "source_authority_paths": [
                "state/task_ledger/events.jsonl",
                "state/task_ledger/events_audit.jsonl",
            ],
            "source_authority_paths_to_stage": ["state/task_ledger/events.jsonl"],
            "projection_paths": [
                "state/task_ledger/ledger.json",
                "state/task_ledger/views/cap_census.json",
            ],
            "projection_paths_to_stage": ["state/task_ledger/ledger.json"],
            "landing_manifest_path": manifest,
        },
    }
    result = {
        "paths_to_stage": [
            "state/task_ledger/events.jsonl",
            "state/task_ledger/ledger.json",
            manifest,
        ],
        "landing_manifest_path": manifest,
    }

    receipt = generated_state_drainer._settlement_owner_path_receipt(owner, result)

    assert receipt["path_bundle"]["projection_paths_to_stage"] == ["state/task_ledger/ledger.json"]
    assert receipt["owner_bundle_completeness"]["projection_path_count"] == 2
    assert receipt["owner_bundle_completeness"]["projection_stage_path_count"] == 1
    assert receipt["owner_bundle_completeness"]["all_expected_stage_paths_reported"] is True
    assert receipt["owner_bundle_completeness"]["missing_expected_stage_paths"] == []
    assert receipt["owner_bundle_completeness"]["task_ledger_audit_journal_declared"] is True


def test_settlement_dry_run_uses_dirty_projection_stage_subset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    manifest = "state/generated_projection_landing/task_ledger_projection_manifest.json"
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "supported_owner_ids": [TASK_LEDGER_OWNER_ID],
        "settlement_order": [TASK_LEDGER_OWNER_ID],
        "owners": [
            {
                "owner_id": TASK_LEDGER_OWNER_ID,
                "status": "append_exempt_manifest_available",
                "freshness_status": "fresh_dirty",
                "dirty_status": "dirty",
                "source_dirty_status": "dirty",
                "required_action": "land_append_exempt",
                "can_apply": True,
                "blocked_by": [],
                "landing_manifest_path": manifest,
                "path_count": 2,
                "path_bundle": {
                    "source_authority_paths": [
                        "state/task_ledger/events.jsonl",
                        "state/task_ledger/events_audit.jsonl",
                    ],
                    "source_authority_paths_to_stage": ["state/task_ledger/events.jsonl"],
                    "projection_paths": [
                        "state/task_ledger/ledger.json",
                        "state/task_ledger/views/cap_census.json",
                    ],
                    "projection_paths_to_stage": ["state/task_ledger/ledger.json"],
                    "landing_manifest_path": manifest,
                },
            }
        ],
        "dirty_owner_count": 1,
        "refresh_required_owner_count": 0,
        "blocked_owner_count": 0,
        "can_settle": True,
        "blocked_by": [],
        "required_next_command": "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run",
        "eventful_closeout_allowed_after_settlement": False,
        "normal_source_event_after_refresh_allowed": False,
    }
    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_settlement_plan",
        lambda *args, **kwargs: plan,
    )

    result = settle_generated_projection_owners(root, owner_ids=[TASK_LEDGER_OWNER_ID], dry_run=True)
    owner = result["owners"][0]

    assert owner["result_status"] == "would_land"
    assert "state/task_ledger/ledger.json" in owner["paths_to_stage"]
    assert "state/task_ledger/views/cap_census.json" not in owner["paths_to_stage"]
    assert owner["owner_bundle_completeness"]["all_expected_stage_paths_reported"] is True
    assert owner["owner_bundle_completeness"]["missing_expected_stage_paths"] == []


def test_settlement_dry_run_uses_status_only_diff_stats(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    _open_work_ledger_thread(root)

    result = settle_generated_projection_owners(root, dry_run=True)

    assert result["ok"] is True
    assert result["status"] == "would_settle"
    for owner in result["before_plan"]["owners"]:
        assert owner["diff_stat"]["stat_mode"] == "status_only"
        assert owner["diff_stat"]["total_changed_lines"] is None


def test_fast_settlement_plan_uses_cached_status_without_owner_checks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    _open_work_ledger_thread(root)

    def fail_owner_check(*args, **kwargs):
        raise AssertionError("fast settlement plan must not rebuild owner projections")

    monkeypatch.setattr(task_ledger_events, "build_projection", fail_owner_check)
    monkeypatch.setattr(work_ledger, "check_project_all", fail_owner_check)

    plan = build_generated_projection_settlement_fast_plan(root)

    assert plan["schema"] == "generated_projection_settlement_plan_v0"
    assert plan["planning_mode"] == "cached_git_status"
    assert plan["authority_level"] == "cached_status_only"
    assert plan["status"] == "settlement_required"
    by_owner = {row["owner_id"]: row for row in plan["owners"]}
    assert by_owner[TASK_LEDGER_OWNER_ID]["planning_mode"] == "cached_git_status"
    assert by_owner[TASK_LEDGER_OWNER_ID]["diff_stat"]["stat_mode"] == "status_only"
    assert "state/task_ledger/events.jsonl" in by_owner[TASK_LEDGER_OWNER_ID]["path_bundle"]["source_authority_paths_to_stage"]
    assert "state/task_ledger/events_audit.jsonl" in by_owner[TASK_LEDGER_OWNER_ID]["path_bundle"]["source_authority_paths_to_stage"]
    assert "codex/ledger/09_52/work_ledger.jsonl" in by_owner["work_ledger_index_projection"]["source_authority_paths"]


def test_settlement_fast_dry_run_uses_cached_status_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    _open_work_ledger_thread(root)

    def fail_owner_check(*args, **kwargs):
        raise AssertionError("fast dry-run must not rebuild owner projections")

    monkeypatch.setattr(task_ledger_events, "build_projection", fail_owner_check)
    monkeypatch.setattr(work_ledger, "check_project_all", fail_owner_check)

    result = settle_generated_projection_owners(root, dry_run=True, fast_plan=True)

    assert result["ok"] is True
    assert result["status"] == "would_settle"
    assert result["before_plan"]["planning_mode"] == "cached_git_status"
    assert result["timing"]["phase_count"] >= 1
    assert result["timing"]["privacy"] == "phase_names_wall_time_and_counts_only_no_stdout_stderr_bodies"
    assert [row["owner_id"] for row in result["owners"]] == [
        TASK_LEDGER_OWNER_ID,
        WORK_LEDGER_OWNER_ID,
        SYSTEM_ATLAS_OWNER_ID,
    ]
    task_owner = result["owners"][0]
    assert "state/task_ledger/events_audit.jsonl" in task_owner["source_authority_paths"]
    assert "state/task_ledger/events_audit.jsonl" in task_owner["source_authority_paths_to_stage"]
    assert task_owner["owner_bundle_completeness"]["task_ledger_audit_journal_declared"] is True
    assert task_owner["owner_bundle_completeness"]["all_expected_stage_paths_reported"] is True


def test_settlement_stewardship_detects_task_ledger_audit_sidecar_omission(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "clean",
        "can_settle": True,
        "blocked_by": [],
        "owners": [
            {
                "owner_id": TASK_LEDGER_OWNER_ID,
                "status": "already_landed",
                "freshness_status": "fresh_clean",
                "dirty_status": "clean",
                "source_dirty_status": "clean",
                "can_apply": True,
                "blocked_by": [],
                "required_action": "none",
                "path_bundle": {
                    "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
                    "source_authority_paths_to_stage": [],
                    "projection_paths": [str(task_ledger_events.LEDGER_REL)],
                    "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
                },
            }
        ],
    }

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_settlement_plan",
        lambda *args, **kwargs: plan,
    )

    result = generated_state_drainer.settle_generated_projection_owners(root)

    omissions = result["stewardship_check"]["omitted_audit_or_source_sidecars"]
    assert result["status"] == "already_settled"
    assert result["settlement_done"] is True
    assert result["validation_done"] is True
    assert result["refinement_done"] is False
    assert omissions == [
        {
            "owner_id": TASK_LEDGER_OWNER_ID,
            "missing_path": "state/task_ledger/events_audit.jsonl",
            "source_class": "audit_sidecar",
            "reason": "existing Task Ledger audit sidecar was not declared in the settlement source bundle",
        }
    ]
    assert result["stewardship_check"]["settlement_revealed_contract_gap"] is True
    assert result["next_best_lane_check"]["lane_results"][0]["status"] == "needs_repair"


def test_settlement_stewardship_respects_requested_owner_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "can_settle": True,
        "blocked_by": [],
        "owners": [
            {
                "owner_id": WORK_LEDGER_OWNER_ID,
                "status": "append_exempt_manifest_available",
                "freshness_status": "fresh_dirty",
                "dirty_status": "dirty",
                "source_dirty_status": "dirty",
                "can_apply": True,
                "blocked_by": [],
                "required_action": "land_append_exempt",
                "path_count": 1,
                "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
                "path_bundle": {
                    "source_authority_paths": ["codex/ledger/09_54/work_ledger.jsonl"],
                    "source_authority_paths_to_stage": ["codex/ledger/09_54/work_ledger.jsonl"],
                    "projection_paths": ["codex/ledger/09_54/work_ledger_index.json"],
                    "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
                },
            }
        ],
    }

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_settlement_plan",
        lambda *args, **kwargs: plan,
    )

    result = generated_state_drainer.settle_generated_projection_owners(
        root,
        owner_ids=[WORK_LEDGER_OWNER_ID],
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["status"] == "would_settle"
    assert result["stewardship_check"]["omitted_audit_or_source_sidecars"] == []
    assert [row["owner_id"] for row in result["owners"]] == [WORK_LEDGER_OWNER_ID]
    assert result["stewardship_check"]["lane_results"][0]["status"] == "checked_no_patch"


def test_settle_cli_uses_command_singleflight(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict] = []

    def fake_run_command_singleflight(repo_root: Path, **kwargs) -> int:
        calls.append({"repo_root": repo_root, **kwargs})
        return 17

    monkeypatch.delenv(generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV, raising=False)
    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "run_command_singleflight", fake_run_command_singleflight)

    result = generated_state_drainer_cli.main(
        ["settle", "--owner-id", TASK_LEDGER_OWNER_ID, "--dry-run"]
    )

    assert result == 17
    assert calls
    assert calls[0]["resource_class"] == "generated_state"
    assert calls[0]["owner_surface"] == "generated_state_drainer"
    assert calls[0]["scope_paths"] == ["state/task_ledger"]
    assert calls[0]["env"][generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV] == "1"


def test_land_cli_streams_progress_to_stderr(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_land(repo_root: Path, **kwargs) -> dict:
        progress_callback = kwargs.get("progress_callback")
        assert progress_callback is not None
        progress_callback({"schema": "generated_state_drainer_progress_v0", "event": "fake"})
        return {"schema": "generated_projection_landing_v0", "ok": True, "status": "would_land"}

    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer_cli.main(
        ["land", "--owner-id", TASK_LEDGER_OWNER_ID, "--dry-run"]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert json.loads(captured.err.splitlines()[0])["event"] == "fake"
    assert json.loads(captured.out)["status"] == "would_land"


def test_land_cli_quiet_progress_suppresses_stderr(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_land(repo_root: Path, **kwargs) -> dict:
        assert kwargs.get("progress_callback") is None
        return {"schema": "generated_projection_landing_v0", "ok": True, "status": "would_land"}

    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer_cli.main(
        ["land", "--owner-id", TASK_LEDGER_OWNER_ID, "--dry-run", "--quiet-progress"]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""


def test_settlement_dry_run_uses_active_plan_without_owner_replan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_dirty = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "diff_stat": {"path_count": 2, "total_changed_lines": 4},
        "path_bundle": {
            "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
            "projection_paths": [
                str(task_ledger_events.LEDGER_REL),
                str(task_ledger_events.SIGNOFFS_REL),
            ],
            "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        },
    }
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "can_settle": True,
        "blocked_by": [],
        "owners": [task_dirty],
    }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", lambda *args, **kwargs: plan)

    def fail_owner_replan(*args, **kwargs):
        raise AssertionError("dry-run settlement should render from the active plan without re-planning the owner")

    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fail_owner_replan)

    result = generated_state_drainer.settle_generated_projection_owners(tmp_path, dry_run=True)

    assert result["ok"] is True
    assert result["status"] == "would_settle"
    assert result["owners"][0]["result_status"] == "would_land"
    assert result["owners"][0]["paths_to_stage"] == [
        "state/generated_projection_landing/task_ledger_projection_manifest.json",
        str(task_ledger_events.EVENTS_REL),
        str(task_ledger_events.LEDGER_REL),
        str(task_ledger_events.SIGNOFFS_REL),
    ]


def test_landing_uses_supplied_plan_without_owner_replan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_dirty = {
        "schema": "generated_projection_landing_plan_v0",
        "ok": True,
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "source_authority": "state/task_ledger/events.jsonl",
        "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
        "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
        "source_event_hashes": {},
        "source_path_hashes": {},
        "projection_paths": [str(task_ledger_events.LEDGER_REL)],
        "projection_hashes": {str(task_ledger_events.LEDGER_REL): "sha256:test"},
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "diff_stat": {"path_count": 1},
        "can_apply": True,
        "blocked_by": [],
        "self_invalidation_reason": "test fixture",
    }

    def fail_owner_replan(*args, **kwargs):
        raise AssertionError("supplied landing plan should avoid owner re-plan")

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_landing_plan", fail_owner_replan)

    result = generated_state_drainer.land_generated_projection_bundle(
        tmp_path,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        dry_run=True,
        landing_plan=task_dirty,
    )

    assert result["ok"] is True
    assert result["status"] == "would_land"
    assert result["manifest"]["projection_hashes"][str(task_ledger_events.LEDGER_REL)] == "sha256:test"


def test_append_exempt_landing_passes_work_ledger_session_to_scoped_commit(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    projection = root / "docs/system_atlas/generated_system_atlas_snapshot.md"
    projection.parent.mkdir(parents=True, exist_ok=True)
    projection.write_text("old snapshot\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(
        ["git", "commit", "-m", "baseline atlas projection"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    projection.write_text("new snapshot\n", encoding="utf-8")

    observed: dict[str, object] = {}

    def fake_scoped_commit(**kwargs) -> dict:
        observed.update(kwargs)
        return {
            "new_commit": "fake-session-aware-commit",
            "changed_paths": [str(path) for path in kwargs.get("paths", [])],
        }

    plan = {
        "schema": "generated_projection_landing_plan_v0",
        "ok": True,
        "owner_id": SYSTEM_ATLAS_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "source_authority": "generated_projection_registry.source_authorities",
        "source_authority_paths": [],
        "source_authority_paths_to_stage": [],
        "source_event_hashes": {},
        "source_path_hashes": {},
        "projection_paths": ["docs/system_atlas/generated_system_atlas_snapshot.md"],
        "projection_hashes": {"docs/system_atlas/generated_system_atlas_snapshot.md": "sha256:test"},
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "diff_stat": {"path_count": 1},
        "can_apply": True,
        "blocked_by": [],
        "self_invalidation_reason": "test fixture",
    }

    result = generated_state_drainer.land_generated_projection_bundle(
        root,
        owner_id=SYSTEM_ATLAS_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        landing_plan=plan,
        commit_func=fake_scoped_commit,
        work_ledger_session_id="codex_owner_session",
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert observed["work_ledger_session_id"] == "codex_owner_session"


@full_drainer_settlement
def test_settlement_lands_dirty_owners_serially_without_appending_events(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)
    _open_work_ledger_thread(root)
    task_event_count = len(task_ledger_events.load_and_validate_events(root))
    work_event_count = len(work_ledger.load_events(root, family_id="09"))

    result = settle_generated_projection_owners(root)

    assert result["ok"] is True
    assert result["status"] == "settled"
    assert result["settlement_done"] is True
    assert result["validation_done"] is True
    assert result["refinement_done"] is False
    assert result["settlement_is_not_refinement"] is True
    assert result["stewardship_checked"] is True
    assert result["next_best_lane_checked"] is True
    assert result["stewardship_check"]["omitted_audit_or_source_sidecars"] == []
    assert [row["owner_id"] for row in result["owners"]] == [
        TASK_LEDGER_OWNER_ID,
        WORK_LEDGER_OWNER_ID,
        SYSTEM_ATLAS_OWNER_ID,
    ]
    assert all(row["commit_hash"] for row in result["owners"])
    assert result["final_plan"]["status"] == "clean"
    assert result["eventful_closeout_allowed_after_settlement"] is False
    assert len(task_ledger_events.load_and_validate_events(root)) == task_event_count
    assert len(work_ledger.load_events(root, family_id="09")) == work_event_count


def test_settlement_reports_blocked_replan_after_prior_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_dirty = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2},
    }
    blocked_task = {
        **task_dirty,
        "status": "blocked",
        "can_apply": False,
        "blocked_by": ["source_authority_missing"],
        "required_action": "blocked",
    }
    plans = [
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [task_dirty],
        },
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": False,
            "status": "blocked",
            "can_settle": False,
            "blocked_by": ["owner_settlement_blocked"],
            "owners": [blocked_task],
        },
    ]
    state = {"plan_index": 0}

    def fake_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        index = min(state["plan_index"], len(plans) - 1)
        state["plan_index"] += 1
        return plans[index]

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": "commit-task",
            "paths_staged": [owner_id],
            "landing_manifest_path": task_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(tmp_path, max_passes=3)

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["reason"] == "settlement_plan_not_apply_safe"
    assert result["blocked_by"] == ["owner_settlement_blocked"]
    assert result["owners"][0]["commit_hash"] == "commit-task"
    assert result["stewardship_check"]["owner_tool_blockers"] == [
        "owner_settlement_blocked",
        f"{TASK_LEDGER_OWNER_ID}:source_authority_missing",
    ]


def test_settlement_rechecks_to_fixed_point_when_later_owner_dirties_prior_owner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_dirty = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
    }
    work_dirty = {
        "owner_id": "work_ledger_index_projection",
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
    }
    task_clean = {**task_dirty, "status": "already_landed", "dirty_status": "clean", "required_action": "none"}
    work_clean = {**work_dirty, "status": "already_landed", "dirty_status": "clean", "required_action": "none"}
    plans = [
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [task_dirty, work_dirty],
        },
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [task_dirty, work_clean],
        },
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "clean",
            "can_settle": True,
            "blocked_by": [],
            "owners": [task_clean, work_clean],
        },
    ]
    state = {"plan_index": 0, "landed": []}

    def fake_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        index = min(state["plan_index"], len(plans) - 1)
        state["plan_index"] += 1
        return plans[index]

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        state["landed"].append(owner_id)
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": f"commit-{owner_id}-{len(state['landed'])}",
            "paths_staged": [owner_id],
            "landing_manifest_path": f"state/generated_projection_landing/{owner_id}_manifest.json",
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(tmp_path, max_passes=3)

    assert result["ok"] is True
    assert result["status"] == "settled"
    assert result["pass_count"] == 2
    assert state["landed"] == [TASK_LEDGER_OWNER_ID, "work_ledger_index_projection", TASK_LEDGER_OWNER_ID]


def test_settlement_reports_repeated_signature_before_duplicate_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_dirty = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "diff_stat": {"path_count": 2, "total_changed_lines": 4},
    }
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "can_settle": True,
        "blocked_by": [],
        "owners": [task_dirty],
    }
    state = {"land_count": 0}

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        state["land_count"] += 1
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": f"commit-{state['land_count']}",
            "paths_staged": [owner_id],
            "landing_manifest_path": task_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(tmp_path, max_passes=2)

    assert result["ok"] is False
    assert result["status"] == "settlement_residual_repeated_signature"
    assert result["reason"] == "residual_plan_repeated_after_progress"
    assert result["pass_count"] == 1
    assert result["previous_pass_index"] == 1
    assert result["current_pass_index"] == 2
    assert result["progress"]["commit_count"] == 1
    assert result["progress"]["commit_hashes"] == ["commit-1"]
    assert state["land_count"] == 1
    assert result["residual_owners"] == [
        {
            "owner_id": TASK_LEDGER_OWNER_ID,
            "status": "append_exempt_manifest_available",
            "required_action": "land_append_exempt",
            "dirty_status": "dirty",
            "source_dirty_status": "clean",
            "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
            "path_count": 2,
            "diff_path_count": 2,
            "total_changed_lines": 4,
        }
    ]


def test_settlement_reports_capped_residual_when_passes_change_but_do_not_converge(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def dirty_plan(pass_count: int) -> dict:
        task_dirty = {
            "owner_id": TASK_LEDGER_OWNER_ID,
            "status": "append_exempt_manifest_available",
            "freshness_status": "fresh_dirty",
            "dirty_status": "dirty",
            "source_dirty_status": "clean",
            "can_apply": True,
            "blocked_by": [],
            "required_action": "land_append_exempt",
            "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
            "path_count": 2,
            "diff_stat": {"path_count": 2, "total_changed_lines": 4 + pass_count},
        }
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [task_dirty],
        }

    state = {"plan_count": 0, "land_count": 0}

    def fake_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        state["plan_count"] += 1
        return dirty_plan(state["plan_count"])

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        state["land_count"] += 1
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": f"commit-{state['land_count']}",
            "paths_staged": [owner_id],
            "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(tmp_path, max_passes=2)

    assert result["ok"] is False
    assert result["status"] == "settlement_residual_capped"
    assert result["reason"] == "max_passes_exhausted"
    assert result["pass_count"] == 2
    assert result["progress"]["commit_count"] == 2
    assert result["progress"]["commit_hashes"] == ["commit-1", "commit-2"]
    assert result["residual_owners"][0]["total_changed_lines"] == 7


def test_settlement_reports_no_progress_residual_when_dirty_owner_lands_no_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_dirty = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2},
    }
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "can_settle": True,
        "blocked_by": [],
        "owners": [task_dirty],
    }

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        return {
            "ok": True,
            "status": "already_landed",
            "commit_hash": None,
            "paths_staged": [],
            "landing_manifest_path": task_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(tmp_path, max_passes=3)

    assert result["ok"] is False
    assert result["status"] == "settlement_residual_no_progress"
    assert result["reason"] == "dirty_settlement_owner_made_no_commit"
    assert result["pass_count"] == 1
    assert result["progress"]["commit_count"] == 0
    assert result["progress"]["already_landed_count"] == 1
    assert result["residual_owners"][0]["owner_id"] == TASK_LEDGER_OWNER_ID


def test_settlement_plans_refresh_then_land_when_owner_projection_requires_refresh(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    task_refresh = _landing_plan_fixture(
        owner_id=TASK_LEDGER_OWNER_ID,
        status="refresh_required",
        dirty_status="dirty",
        source_dirty_status="dirty",
    )
    work_clean = _landing_plan_fixture(
        owner_id=WORK_LEDGER_OWNER_ID,
        status="already_landed",
    )
    plans = {
        TASK_LEDGER_OWNER_ID: task_refresh,
        WORK_LEDGER_OWNER_ID: work_clean,
        SYSTEM_ATLAS_OWNER_ID: _landing_plan_fixture(
            owner_id=SYSTEM_ATLAS_OWNER_ID,
            status="already_landed",
        ),
    }

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_landing_plan",
        lambda repo_root, *, owner_id, **kwargs: plans[owner_id],
    )

    plan = build_generated_projection_settlement_plan(root)
    result = settle_generated_projection_owners(root, dry_run=True)

    assert plan["status"] == "settlement_required"
    assert plan["can_settle"] is True
    assert plan["refresh_required_owner_count"] == 1
    task_owner = plan["owners"][0]
    assert task_owner["required_action"] == "refresh_then_land_append_exempt"
    assert result["ok"] is True
    assert result["status"] == "would_settle"
    assert result["owners"][0]["result_status"] == "would_refresh_then_land"
    assert "state/task_ledger/ledger.json" in result["owners"][0]["paths_to_stage"]


def test_settlement_refuses_unsupported_owner(tmp_path: Path) -> None:
    root = tmp_path

    plan = build_generated_projection_settlement_plan(root, owner_ids=["unsupported_projection_owner"])
    result = settle_generated_projection_owners(root, owner_ids=["unsupported_projection_owner"], dry_run=True)

    assert plan["status"] == "blocked"
    assert plan["can_settle"] is False
    assert plan["blocked_by"] == ["unsupported_owner_id", "owner_settlement_blocked"]
    assert result["ok"] is False
    assert result["status"] == "blocked"
