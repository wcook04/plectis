from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
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
    FRONTEND_NAVIGATION_GRAPH_OWNER_ID,
    FRONTEND_NAVIGATION_GRAPH_REFRESH_ACTION,
    LANDING_MANIFEST_SCHEMA,
    MICROCOSM_ORGAN_ATLAS_OWNER_ID,
    MICROCOSM_ORGAN_ATLAS_REFRESH_ACTION,
    MICROCOSM_PUBLIC_SITE_OWNER_ID,
    MICROCOSM_PUBLIC_SITE_REFRESH_ACTION,
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
TEST_WORK_LEDGER_SESSION_ID = "codex_test_generated_state_drainer"
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


def _write_frontend_navigation_fixture(root: Path) -> None:
    owner = get_projection_owner(FRONTEND_NAVIGATION_GRAPH_OWNER_ID)
    for rel_path in owner.artifacts:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".md":
            path.write_text("# Frontend navigation snapshot\n", encoding="utf-8")
        else:
            path.write_text("{}\n", encoding="utf-8")
    for rel_path in (
        "system/server/ui/src/App.tsx",
        "system/server/ui/src/navigation/surfaces.ts",
        "system/server/ui/src/navigation/overlays.ts",
        "system/server/ui/src/pages/StationLens.tsx",
        "tools/meta/observability/station_views.json",
        "tools/meta/observability/wayfinding_scenarios.json",
        "state/observability/render_load_index.json",
        "state/frontend_navigation/semantic_layer.v1.json",
        "state/frontend_navigation/component_index.json",
        "tools/meta/observability/frontend_nav_graph.py",
    ):
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")


def _write_microcosm_public_site_fixture(root: Path) -> None:
    for rel_path in (
        "sites/microcosm/content-graph.json",
        "sites/microcosm/docs/source.html",
        "sites/microcosm/assets/site-packet.js",
        "microcosm-substrate/core/organ_registry.json",
        "tools/meta/dissemination/build_microcosm_public_site.py",
    ):
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")


def test_work_ledger_refresh_uses_stale_projection_targets(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, list[str], bool]] = []

    def fail_project_all(repo_root: Path) -> dict:
        raise AssertionError("targeted refresh should not call project_all")

    def fake_targeted_refresh(
        repo_root: Path,
        *,
        family_id: str,
        phase_ids,
        compare_existing: bool = True,
    ) -> list[dict]:
        calls.append((family_id, list(phase_ids), compare_existing))
        return [
            {
                "phase_id": phase_id,
                "index_path": f"codex/ledger/{phase_id}/work_ledger_index.json",
                "targeted": True,
            }
            for phase_id in phase_ids
        ]

    monkeypatch.setattr(generated_state_drainer.work_ledger, "project_all", fail_project_all)
    monkeypatch.setattr(
        generated_state_drainer.work_ledger,
        "write_family_projection_targets",
        fake_targeted_refresh,
    )

    result = generated_state_drainer._refresh_work_ledger_projection_for_landing_plan(
        tmp_path,
        {
            "owner_id": WORK_LEDGER_OWNER_ID,
            "stale_projection_targets": [
                {
                    "generated_path": "codex/ledger/09_35/work_ledger_index.json",
                    "phase_id": "09_35",
                    "family_id": "09",
                },
                {
                    "generated_path": "codex/ledger/09_36/work_ledger_index.json",
                    "phase_id": "09_36",
                    "family_id": "09",
                },
            ],
        },
    )

    assert calls == [("09", ["09_35", "09_36"], False)]
    assert result["targeted"] is True
    assert result["families"][0]["projection_results"][0]["targeted"] is True


def test_work_ledger_refresh_falls_back_without_stale_projection_targets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = {"project_all": 0}

    def fake_project_all(repo_root: Path) -> dict:
        calls["project_all"] += 1
        return {"ok": True, "families": []}

    monkeypatch.setattr(generated_state_drainer.work_ledger, "project_all", fake_project_all)

    result = generated_state_drainer._refresh_work_ledger_projection_for_landing_plan(
        tmp_path,
        {"owner_id": WORK_LEDGER_OWNER_ID},
    )

    assert calls == {"project_all": 1}
    assert result == {"ok": True, "families": []}


def test_status_classifies_stale_work_ledger_projection(tmp_path: Path) -> None:
    root = tmp_path
    _make_projection_stale(root)

    status = build_generated_state_drainer_status(root)
    row = status["projection_targets"][0]

    assert status["schema"] == "generated_state_drainer_status_v0"
    assert status["summary"]["stale_count"] == 1
    assert row["generated_path"] == "codex/ledger/09_52/work_ledger_index.json"
    assert row["owner_id"] == "work_ledger_index_projection"
    assert row["freshness_status"] == "source_authority_advanced_since_projection"
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
    assert rebuild.get("rebuild_skipped") is not True

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


def test_work_ledger_landing_plan_uses_target_only_check_for_dirty_phase(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _open_work_ledger_thread(root)

    def fail_full_check(*args, **kwargs):
        raise AssertionError("landing plan should not run full Work Ledger projection check")

    monkeypatch.setattr(work_ledger, "check_project_all", fail_full_check)

    plan = build_generated_projection_landing_plan(root, owner_id=WORK_LEDGER_OWNER_ID)

    assert plan["status"] == "append_exempt_manifest_available"
    assert plan["freshness_status"] == "fresh_dirty"
    assert plan["projection_paths"] == ["codex/ledger/09_52/work_ledger_index.json"]
    assert plan["source_authority_paths"] == ["codex/ledger/09_52/work_ledger.jsonl"]
    assert plan["status_ref"]["schema"] == "generated_state_drainer_status_v0"
    assert plan["status_ref"]["summary"]["projection_target_count"] == 1


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
    assert plan["stale_projection_paths"] == ["codex/ledger/09_52/work_ledger_index.json"]
    assert plan["stale_projection_targets"] == [
        {
            "generated_path": "codex/ledger/09_52/work_ledger_index.json",
            "phase_id": "09_52",
            "family_id": "09",
        }
    ]


def test_landing_plan_treats_historical_work_ledger_fanout_stale_as_advisory(
    tmp_path: Path,
) -> None:
    root = tmp_path
    latest_index = root / "codex/ledger/09_54_1/work_ledger_index.json"
    latest_source = root / "codex/ledger/09_54_1/work_ledger.jsonl"
    latest_index.parent.mkdir(parents=True, exist_ok=True)
    latest_index.write_text('{"counts":{"events":3}}\n', encoding="utf-8")
    latest_source.write_text('{"event_id":"wle_latest"}\n', encoding="utf-8")

    status = {
        "schema": "generated_state_drainer_status_v0",
        "projection_targets": [
            {
                "generated_path": "codex/ledger/09_35/work_ledger_index.json",
                "owner_id": WORK_LEDGER_OWNER_ID,
                "source_event_hash": "sha256:family",
                "projection_hash": "sha256:old",
                "freshness_status": "projection_stale",
                "dirty_status": "modified",
                "phase_id": "09_35",
                "family_id": "09",
            },
            {
                "generated_path": "codex/ledger/09_54_1/work_ledger_index.json",
                "owner_id": WORK_LEDGER_OWNER_ID,
                "source_event_hash": "sha256:family",
                "projection_hash": "sha256:latest",
                "freshness_status": "fresh",
                "dirty_status": "modified",
                "phase_id": "09_54_1",
                "family_id": "09",
            },
        ],
        "owner_checks": {},
    }
    status_map = {
        "codex/ledger/09_35/work_ledger_index.json": "modified",
        "codex/ledger/09_54_1/work_ledger_index.json": "modified",
        "codex/ledger/09_54_1/work_ledger.jsonl": "modified",
    }

    plan = build_generated_projection_landing_plan(
        root,
        status=status,
        status_map=status_map,
        collect_diff_stat=False,
    )

    assert plan["status"] == "append_exempt_manifest_available"
    assert plan["freshness_status"] == "fresh_dirty"
    assert plan["can_apply"] is True
    assert plan["blocked_by"] == []
    assert plan["stale_projection_paths"] == []
    assert plan["projection_paths"] == ["codex/ledger/09_54_1/work_ledger_index.json"]
    assert plan["projection_paths_to_stage"] == [
        "codex/ledger/09_54_1/work_ledger_index.json"
    ]
    assert plan["source_authority_paths"] == ["codex/ledger/09_54_1/work_ledger.jsonl"]
    assert plan["source_authority_paths_to_stage"] == [
        "codex/ledger/09_54_1/work_ledger.jsonl"
    ]
    assert plan["advisory_stale_projection_paths"] == [
        "codex/ledger/09_35/work_ledger_index.json"
    ]
    assert (
        plan["advisory_stale_projection_disposition"]
        == "historical_work_ledger_family_fanout_not_settlement_blocking"
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


def test_append_exempt_landing_refuses_missing_work_ledger_session_id_for_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    _open_work_ledger_thread(root)

    def fail_commit(**kwargs) -> dict:
        raise AssertionError("landing must refuse before scoped_commit without a session id")

    result = land_generated_projection_bundle(
        root,
        mode=APPEND_EXEMPT_LANDING_MODE,
        commit_func=fail_commit,
    )

    assert result["ok"] is False
    assert result["status"] == "refused"
    assert result["reason"] == "missing_work_ledger_session_id"
    assert result["blocked_by"] == ["work_ledger_session_id_required"]
    assert result["mutation_guard"]["work_ledger_session_id_required_for_mutation"] is True
    assert "session-status --seed-speed" in result["mutation_guard"]["active_session_status_command"]
    assert "session-preflight" in result["mutation_guard"]["session_preflight_command_template"]
    assert [
        row["step"] for row in result["mutation_guard"]["repair_sequence"]
    ] == [
        "inspect_active_work_ledger_sessions",
        "open_or_reuse_claimed_session",
        "rerun_generated_state_mutation",
    ]
    assert "--work-ledger-session-id <session_id>" in result["required_next_command"]
    assert result["normal_work_ledger_event_after_refresh_allowed"] is False


def test_append_exempt_landing_commits_without_appending_work_ledger_event(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _open_work_ledger_thread(root)
    event_count_before = len(work_ledger.load_events(root, family_id="09"))

    result = land_generated_projection_bundle(
        root,
        mode=APPEND_EXEMPT_LANDING_MODE,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

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


def test_task_ledger_refresh_landing_returns_retry_later_when_source_lock_held(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if task_ledger_events.fcntl is None:
        pytest.skip("nonblocking Task Ledger source lock probe requires fcntl")
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _make_task_ledger_projection_stale(root)
    monkeypatch.setattr(generated_state_drainer, "TASK_LEDGER_SOURCE_LOCK_RETRY_SLEEP_S", 0)
    lock_path = root / task_ledger_events.LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as handle:
        task_ledger_events.fcntl.flock(
            handle.fileno(),
            task_ledger_events.fcntl.LOCK_EX | task_ledger_events.fcntl.LOCK_NB,
        )
        try:
            result = land_generated_projection_bundle(
                root,
                owner_id=TASK_LEDGER_OWNER_ID,
                mode=APPEND_EXEMPT_LANDING_MODE,
                work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
            )
        finally:
            task_ledger_events.fcntl.flock(handle.fileno(), task_ledger_events.fcntl.LOCK_UN)

    assert result["schema"] == "generated_projection_landing_v0"
    assert result["ok"] is False
    assert result["status"] == "retry_later"
    assert result["reason"] == "task_ledger_source_mutation_in_progress"
    assert result["retry_later"] is True
    assert result["blocked_by"] == ["task_ledger_source_writer_lock_held"]
    assert result["source_lock"]["attempts"] == generated_state_drainer.TASK_LEDGER_SOURCE_LOCK_ATTEMPTS
    assert result["source_lock"]["wait_budget_s"] >= 0
    assert result["source_lock"]["lock_file_exists"] is True
    assert result["source_lock"]["lock_file_size"] == 0
    assert result["normal_task_ledger_event_after_refresh_allowed"] is False
    assert not (root / "state/generated_projection_landing/task_ledger_projection_manifest.json").exists()


def test_task_ledger_source_lock_retries_transient_busy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if task_ledger_events.fcntl is None:
        pytest.skip("nonblocking Task Ledger source lock probe requires fcntl")
    real_flock = task_ledger_events.fcntl.flock
    observed = {"busy_count": 0, "sleeps": []}

    def flaky_flock(fd: int, operation: int) -> None:
        if (
            operation & task_ledger_events.fcntl.LOCK_NB
            and observed["busy_count"] == 0
        ):
            observed["busy_count"] += 1
            raise BlockingIOError(errno.EAGAIN, "temporary writer overlap")
        real_flock(fd, operation)

    monkeypatch.setattr(task_ledger_events.fcntl, "flock", flaky_flock)
    monkeypatch.setattr(
        generated_state_drainer.time,
        "sleep",
        lambda seconds: observed["sleeps"].append(seconds),
    )

    with generated_state_drainer._task_ledger_source_lock_for_landing(tmp_path) as probe:
        assert probe["acquired"] is True
        assert probe["status"] == "acquired"
        assert probe["busy_retry_count"] == 1
        assert probe["wait_budget_s"] >= generated_state_drainer.TASK_LEDGER_SOURCE_LOCK_RETRY_SLEEP_S
        assert probe["lock_file_exists"] is True

    assert observed["sleeps"] == [
        generated_state_drainer.TASK_LEDGER_SOURCE_LOCK_RETRY_SLEEP_S
    ]


def test_task_ledger_source_lock_reports_holder_metadata_when_busy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if task_ledger_events.fcntl is None:
        pytest.skip("nonblocking Task Ledger source lock probe requires fcntl")
    monkeypatch.setattr(generated_state_drainer, "TASK_LEDGER_SOURCE_LOCK_RETRY_SLEEP_S", 0)
    lock_path = tmp_path / task_ledger_events.LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    holder = {
        "schema": "task_ledger_writer_lock_holder_v0",
        "pid": 12345,
        "ppid": 123,
        "created_at": "2026-06-04T22:30:00+00:00",
        "lock_path": str(lock_path),
        "argv": ["task_ledger_apply.py", "drain-intake"],
    }

    with lock_path.open("w+", encoding="utf-8") as handle:
        json.dump(holder, handle)
        handle.write("\n")
        handle.flush()
        task_ledger_events.fcntl.flock(
            handle.fileno(),
            task_ledger_events.fcntl.LOCK_EX | task_ledger_events.fcntl.LOCK_NB,
        )
        try:
            with generated_state_drainer._task_ledger_source_lock_for_landing(tmp_path) as probe:
                assert probe["acquired"] is False
                assert probe["status"] == "busy"
                assert probe["lock_holder_metadata_status"] == "present"
                assert probe["lock_holder"]["pid"] == 12345
                assert probe["lock_holder"]["argv"] == ["task_ledger_apply.py", "drain-intake"]
        finally:
            task_ledger_events.fcntl.flock(handle.fileno(), task_ledger_events.fcntl.LOCK_UN)


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


def test_task_ledger_append_exempt_landing_commits_without_appending_task_ledger_event(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)
    event_count_before = len(task_ledger_events.load_and_validate_events(root))
    monkeypatch.delenv("AIW_SCOPED_COMMIT_ALLOW_TASK_LEDGER_MONOLITH", raising=False)

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert result["commit_hash"]
    assert result["normal_task_ledger_event_after_refresh_allowed"] is False
    assert result["task_ledger_monolith_settlement_override"]["status"] == "override_set_for_commit"
    assert result["scoped_commit_task_ledger_monolith_guard"]["status"] == "override_allowed"
    assert "AIW_SCOPED_COMMIT_ALLOW_TASK_LEDGER_MONOLITH" not in os.environ
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


def test_task_ledger_landing_holds_source_lock_through_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)
    lock_events: list[str] = []

    @contextmanager
    def fake_source_lock(repo_root: Path):
        assert repo_root == root.resolve()
        lock_events.append("enter")
        try:
            yield {
                "schema": "task_ledger_source_lock_probe_v0",
                "acquired": True,
                "status": "acquired",
                "mode": "test_lock",
            }
        finally:
            lock_events.append("exit")

    def fake_commit(**kwargs) -> dict:
        assert lock_events[-1] == "enter"
        lock_events.append("commit")
        return _fake_scoped_commit_result(**kwargs)

    monkeypatch.setattr(
        generated_state_drainer,
        "_task_ledger_source_lock_for_landing",
        fake_source_lock,
    )

    result = land_generated_projection_bundle(
        root,
        owner_id=TASK_LEDGER_OWNER_ID,
        mode=APPEND_EXEMPT_LANDING_MODE,
        commit_func=fake_commit,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert lock_events == ["enter", "exit", "enter", "commit", "exit"]


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
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert original_rebuild(root, check=True)["ok"] is True


def test_task_ledger_locked_landing_plan_forces_refresh_on_manifest_staleness(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_fast_row(repo_root: Path, *, owner_id: str, status_map=None):
        assert repo_root == tmp_path.resolve()
        assert owner_id == TASK_LEDGER_OWNER_ID
        assert status_map is not None
        return {
            "owner_id": TASK_LEDGER_OWNER_ID,
            "status": "append_exempt_manifest_available",
            "freshness_status": "not_checked_cached_status_only",
            "dirty_status": "dirty",
            "source_dirty_status": "dirty",
            "can_apply": True,
            "blocked_by": [],
            "required_next_command": "./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id task_ledger_projection --dry-run",
            "source_authority": "state/task_ledger/events.jsonl",
            "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
            "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
            "projection_paths": [str(task_ledger_events.LEDGER_REL)],
            "projection_paths_to_stage": [str(task_ledger_events.LEDGER_REL)],
            "diff_stat": {},
            "path_bundle": {
                "dirty_path_summary": {
                    "source_authority_dirty_count": 1,
                    "projection_dirty_count": 1,
                    "landing_manifest_dirty": False,
                },
                "owner_bundle_rationale": "test bundle",
            },
        }

    def stale_manifest(repo_root: Path):
        return {
            "schema": "task_ledger_projection_manifest_staleness_v0",
            "status": "stale",
            "stale": True,
            "reason": "projection_manifest_authority_mismatch",
            "projection_event_count": 2,
            "authority_event_count": 3,
            "authority_tail_hash_matches": False,
        }

    def fail_full_plan(*args, **kwargs):
        raise AssertionError("locked Task Ledger landing must not re-enter the full projection planner")

    monkeypatch.setattr(generated_state_drainer, "_fast_settlement_owner_row", fake_fast_row)
    monkeypatch.setattr(generated_state_drainer, "_task_ledger_projection_manifest_staleness", stale_manifest)
    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_landing_plan", fail_full_plan)

    plan = generated_state_drainer._task_ledger_locked_landing_plan_from_current_state(tmp_path)

    assert plan["status"] == "refresh_required"
    assert plan["blocked_by"] == ["projection_not_fresh"]
    assert plan["can_apply"] is False
    assert plan["projection_manifest_staleness"]["authority_event_count"] == 3


def test_task_ledger_locked_replan_refreshes_before_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _init_git_repo(root)
    refresh_plan = {
        "schema": "generated_projection_landing_plan_v0",
        "ok": True,
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "stale",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "source_authority": "state/task_ledger/events.jsonl",
        "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
        "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
        "projection_paths": [str(task_ledger_events.LEDGER_REL)],
        "projection_paths_to_stage": [str(task_ledger_events.LEDGER_REL)],
        "projection_hashes": {},
        "can_apply": False,
        "blocked_by": ["projection_not_fresh"],
        "required_next_command": "./repo-python tools/meta/control/generated_state_drainer.py apply --only task_ledger_projection_refresh",
    }
    land_plan = {
        **refresh_plan,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "can_apply": True,
        "blocked_by": [],
    }
    initial_plan = {**land_plan}
    locked_plans = [refresh_plan, land_plan]
    rebuild_calls: list[Path] = []

    @contextmanager
    def fake_source_lock(repo_root: Path):
        assert repo_root == root.resolve()
        yield {
            "schema": "task_ledger_source_lock_probe_v0",
            "acquired": True,
            "status": "acquired",
            "mode": "test_lock",
        }

    def fake_locked_plan(repo_root: Path):
        assert repo_root == root.resolve()
        return locked_plans.pop(0)

    def fake_rebuild(repo_root: Path):
        rebuild_calls.append(repo_root)
        return {"ok": True}

    monkeypatch.setattr(generated_state_drainer, "_task_ledger_source_lock_for_landing", fake_source_lock)
    monkeypatch.setattr(generated_state_drainer, "_task_ledger_locked_landing_plan_from_current_state", fake_locked_plan)
    monkeypatch.setattr(task_ledger_events, "_rebuild_projections_with_health_unlocked", fake_rebuild)
    monkeypatch.setattr(
        generated_state_drainer,
        "_dirty_existing_paths",
        lambda repo_root, paths, *, status_map=None: [str(path) for path in paths],
    )
    monkeypatch.setattr(
        generated_state_drainer,
        "_head_changed_existing_paths",
        lambda repo_root, paths, *, status_map=None: [str(path) for path in paths],
    )

    result = generated_state_drainer._land_task_ledger_projection_bundle_locked(
        root,
        mode=APPEND_EXEMPT_LANDING_MODE,
        dry_run=False,
        landing_plan=initial_plan,
        commit_func=_fake_scoped_commit_result,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "landed"
    assert rebuild_calls == [root.resolve()]
    assert locked_plans == []


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
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
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
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
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
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
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
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
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
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
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


def test_task_ledger_alias_routes_to_projection_owner(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)

    status = build_generated_state_drainer_status(root, owner_ids=["task_ledger"])
    assert status["selected_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert status["missing_owner_ids"] == []

    plan = build_generated_projection_landing_plan(root, owner_id="task_ledger")
    assert plan["owner_id"] == TASK_LEDGER_OWNER_ID
    assert plan["blocked_by"] == []

    fast_plan = build_generated_projection_settlement_fast_plan(root, owner_ids=["task_ledger"])
    assert fast_plan["settlement_order"] == [TASK_LEDGER_OWNER_ID]
    assert "unsupported_owner_id" not in fast_plan["blocked_by"]
    assert fast_plan["owners"][0]["owner_id"] == TASK_LEDGER_OWNER_ID

    dry_run = land_generated_projection_bundle(root, owner_id="task_ledger", dry_run=True)
    assert dry_run["owner_id"] == TASK_LEDGER_OWNER_ID
    assert dry_run["status"] in {"would_land", "already_landed"}


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


def test_system_atlas_landing_plan_routes_clean_source_coupling_to_owner_rebuild(
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
                "reason": "clean committed source moved",
                "changed_source_count": 1,
                "blocking_changed_source_count": 1,
                "dirty_changed_source_count": 0,
                "claimed_dirty_source_count": 0,
                "unknown_git_status_source_count": 0,
                "refresh_policy": "rebuild_generated_atlas_with_owner_builder_then_check",
                "safe_to_commit_generated_outputs_without_sources": False,
                "blocking_changed_sources": [
                    {
                        "source_id": "annex_distillation_index",
                        "path": "annexes/annex_distillation_index.json",
                        "git_pathspec": "annexes/annex_distillation_index.json",
                        "git_status": "clean",
                        "owner_route_hint": "./repo-python annex_import.py validate --all --read-only",
                    }
                ],
            },
        }

    monkeypatch.setattr(generated_state_drainer, "_run_owner_json_command", fake_owner_check)

    plan = build_generated_projection_landing_plan(root, owner_id=SYSTEM_ATLAS_OWNER_ID)
    settlement = build_generated_projection_settlement_plan(root, owner_ids=[SYSTEM_ATLAS_OWNER_ID])

    assert plan["owner_id"] == SYSTEM_ATLAS_OWNER_ID
    assert plan["status"] == "refresh_required"
    assert plan["blocked_by"] == ["projection_not_fresh"]
    assert plan["required_next_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py apply --only "
        "system_atlas_projection_refresh"
    )
    assert plan["owner_handoff_class"] == "system_atlas_owner_rebuild"
    assert plan["source_coupling"]["refresh_policy"] == (
        "rebuild_generated_atlas_with_owner_builder_then_check"
    )
    assert plan["source_coupling"]["unknown_git_status_source_count"] == 0
    assert settlement["status"] == "settlement_required"
    assert settlement["owners"][0]["required_action"] == "refresh_then_land_append_exempt"
    assert settlement["owners"][0]["can_apply"] is True


def test_system_atlas_landing_plan_omits_tolerated_live_task_ledger_sources() -> None:
    source_coupling = {
        "status": "live_task_ledger_source_churn_tolerated",
        "reason": "clean append-tail Task Ledger source moved",
        "changed_source_count": 2,
        "blocking_changed_source_count": 0,
        "dirty_changed_source_count": 2,
        "claimed_dirty_source_count": 0,
        "unknown_git_status_source_count": 0,
        "source_coupled_blocker_status": "none",
        "refresh_policy": (
            "stable_snapshot_check_tolerates_clean_task_ledger_churn_"
            "rebuild_before_atlas_output_commit"
        ),
        "safe_to_commit_generated_outputs_without_sources": True,
    }

    assert generated_state_drainer._system_atlas_source_coupling_allows_append_exempt_landing(
        source_coupling
    )
    assert generated_state_drainer._filter_system_atlas_append_exempt_safe_source_paths(
        [
            "state/task_ledger/ledger.json",
            "state/task_ledger/views/active_wip.json",
            "docs/system_atlas/generated_system_atlas_snapshot.md",
        ],
        source_coupling,
    ) == ["docs/system_atlas/generated_system_atlas_snapshot.md"]


def test_system_atlas_landing_plan_blocks_unknown_source_coupling_even_with_rebuild_policy(
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
                "reason": "git status unavailable for source",
                "changed_source_count": 1,
                "blocking_changed_source_count": 1,
                "dirty_changed_source_count": 0,
                "claimed_dirty_source_count": 0,
                "unknown_git_status_source_count": 1,
                "refresh_policy": "rebuild_generated_atlas_with_owner_builder_then_check",
                "safe_to_commit_generated_outputs_without_sources": False,
                "blocking_changed_sources": [
                    {
                        "source_id": "manual_system_atlas_docs",
                        "path": "docs/system_atlas/*.md",
                        "git_pathspec": "docs/system_atlas",
                        "git_status": "unknown",
                        "owner_route_hint": "./repo-python tools/meta/factory/build_system_atlas.py --check",
                    }
                ],
            },
        }

    monkeypatch.setattr(generated_state_drainer, "_run_owner_json_command", fake_owner_check)

    plan = build_generated_projection_landing_plan(root, owner_id=SYSTEM_ATLAS_OWNER_ID)
    settlement = build_generated_projection_settlement_plan(root, owner_ids=[SYSTEM_ATLAS_OWNER_ID])

    assert plan["status"] == "source_coupling_unsettled"
    assert plan["can_apply"] is False
    assert plan["blocked_by"] == ["source_coupling_not_settled"]
    assert plan["source_coupling"]["unknown_git_status_source_count"] == 1
    assert settlement["status"] == "blocked"
    assert settlement["owners"][0]["required_action"] == "blocked"


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
    assert SYSTEM_ATLAS_OWNER_ID in plan["supported_owner_ids"]
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


def test_fast_settlement_plan_supports_frontend_navigation_owner_alias(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_frontend_navigation_fixture(root)

    plan = build_generated_projection_settlement_fast_plan(root, owner_ids=["frontend_navigation"])
    owner = plan["owners"][0]

    assert plan["schema"] == "generated_projection_settlement_plan_v0"
    assert FRONTEND_NAVIGATION_GRAPH_OWNER_ID in plan["supported_owner_ids"]
    assert plan["settlement_order"] == [FRONTEND_NAVIGATION_GRAPH_OWNER_ID]
    assert owner["owner_id"] == FRONTEND_NAVIGATION_GRAPH_OWNER_ID
    assert owner["blocked_by"] == []
    assert owner["required_action"] == "land_append_exempt"
    assert owner["path_count"] == len(get_projection_owner(FRONTEND_NAVIGATION_GRAPH_OWNER_ID).artifacts)
    assert "state/frontend_navigation/navigation_graph.json" in owner["projection_paths_to_stage"]


def test_full_settlement_plan_collects_frontend_navigation_registered_owner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_frontend_navigation_fixture(root)

    monkeypatch.setattr(
        generated_state_drainer,
        "_run_owner_json_command",
        lambda *args, **kwargs: {"ok": True},
    )

    plan = build_generated_projection_settlement_plan(
        root,
        owner_ids=[FRONTEND_NAVIGATION_GRAPH_OWNER_ID],
    )
    owner = plan["owners"][0]

    assert plan["status"] == "settlement_required"
    assert plan["blocked_by"] == []
    assert owner["owner_id"] == FRONTEND_NAVIGATION_GRAPH_OWNER_ID
    assert owner["blocked_by"] == []
    assert owner["required_action"] == "land_append_exempt"
    assert owner["source_authority"] == "generated_projection_registry.source_authorities"
    assert owner["required_next_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py "
        "settle --owner-id frontend_navigation_graph_projection --dry-run"
    )


def test_apply_accepts_frontend_navigation_refresh_action(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    _write_frontend_navigation_fixture(root)
    monkeypatch.setattr(
        generated_state_drainer,
        "_run_owner_json_command",
        lambda *args, **kwargs: {"ok": True},
    )

    result = apply_generated_state_drainer(
        root,
        only=FRONTEND_NAVIGATION_GRAPH_REFRESH_ACTION,
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["status"] == "already_fresh"
    assert result["action"]["owner_id"] == FRONTEND_NAVIGATION_GRAPH_OWNER_ID
    assert "state/frontend_navigation/navigation_graph.json" in result["action"]["scope"]


def test_fast_settlement_plan_supports_microcosm_public_site_owner_alias(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_microcosm_public_site_fixture(root)

    plan = build_generated_projection_settlement_fast_plan(root, owner_ids=["microcosm_site"])
    owner = plan["owners"][0]

    assert plan["schema"] == "generated_projection_settlement_plan_v0"
    assert MICROCOSM_PUBLIC_SITE_OWNER_ID in plan["supported_owner_ids"]
    assert plan["settlement_order"] == [MICROCOSM_PUBLIC_SITE_OWNER_ID]
    assert owner["owner_id"] == MICROCOSM_PUBLIC_SITE_OWNER_ID
    assert owner["blocked_by"] == []
    assert owner["required_action"] == "land_append_exempt"
    assert "sites/microcosm/content-graph.json" in owner["projection_paths_to_stage"]
    assert "sites/microcosm/docs/source.html" in owner["projection_paths_to_stage"]


def test_microcosm_public_site_landing_plan_blocks_dirty_source_coupling(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_microcosm_public_site_fixture(root)

    def fake_owner_check(repo_root: Path, argv):
        return {
            "ok": False,
            "source_coupling": {
                "status": "blocked_dirty_source_inputs",
                "reason": "fixture source moved",
                "dirty_source_count": 1,
                "changed_source_count": 1,
                "blocking_changed_source_count": 1,
                "dirty_changed_source_count": 1,
                "safe_to_commit_generated_outputs_without_sources": False,
                "blocking_changed_sources": [
                    {
                        "source_id": "organ_registry",
                        "path": "microcosm-substrate/core/organ_registry.json",
                        "git_pathspec": "microcosm-substrate/core/organ_registry.json",
                        "owner_route_hint": (
                            "cd microcosm-substrate && "
                            "PYTHONPATH=src python3 scripts/build_organ_atlas.py --check"
                        ),
                    }
                ],
            },
        }

    monkeypatch.setattr(generated_state_drainer, "_run_owner_json_command", fake_owner_check)

    plan = build_generated_projection_landing_plan(root, owner_id=MICROCOSM_PUBLIC_SITE_OWNER_ID)
    settlement = build_generated_projection_settlement_plan(
        root,
        owner_ids=[MICROCOSM_PUBLIC_SITE_OWNER_ID],
    )

    assert plan["owner_id"] == MICROCOSM_PUBLIC_SITE_OWNER_ID
    assert plan["status"] == "source_coupling_unsettled"
    assert plan["can_apply"] is False
    assert plan["blocked_by"] == ["source_coupling_not_settled"]
    assert plan["source_authority"] == "generated_projection_registry.source_authorities"
    assert plan["owner_handoff_class"] == "source_coupling_source_owner_handoff"
    assert plan["source_coupling"]["status"] == "blocked_dirty_source_inputs"
    assert plan["source_coupling"]["blocking_changed_sources_sample"][0]["source_id"] == (
        "organ_registry"
    )
    assert plan["source_coupling_owner_route_hints"] == [
        "cd microcosm-substrate && PYTHONPATH=src python3 scripts/build_organ_atlas.py --check"
    ]
    assert "sites/microcosm/docs/source.html" in plan["projection_paths"]
    assert settlement["status"] == "blocked"
    assert settlement["owners"][0]["required_action"] == "blocked"
    assert settlement["owners"][0]["owner_handoff_class"] == "source_coupling_source_owner_handoff"
    assert settlement["owners"][0]["required_owner_resolution"].startswith(
        "Settle or claim the changed Microcosm Public Site source inputs"
    )
    assert "owner_settlement_blocked" in settlement["blocked_by"]


def test_apply_accepts_microcosm_registered_owner_refresh_actions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    _write_microcosm_public_site_fixture(root)
    monkeypatch.setattr(
        generated_state_drainer,
        "_run_owner_json_command",
        lambda *args, **kwargs: {"ok": True},
    )

    site_result = apply_generated_state_drainer(
        root,
        only=MICROCOSM_PUBLIC_SITE_REFRESH_ACTION,
        dry_run=True,
    )
    organ_result = apply_generated_state_drainer(
        root,
        only=MICROCOSM_ORGAN_ATLAS_REFRESH_ACTION,
        dry_run=True,
    )

    assert site_result["ok"] is True
    assert site_result["action"]["owner_id"] == MICROCOSM_PUBLIC_SITE_OWNER_ID
    assert "sites/microcosm/content-graph.json" in site_result["action"]["scope"]
    assert organ_result["ok"] is True
    assert organ_result["action"]["owner_id"] == MICROCOSM_ORGAN_ATLAS_OWNER_ID
    assert "microcosm-substrate/ORGANS.md" in organ_result["action"]["scope"]


def test_cli_apply_parser_accepts_microcosm_registered_owner_actions() -> None:
    parser = generated_state_drainer_cli.build_parser()

    site_args = parser.parse_args(
        ["apply", "--only", MICROCOSM_PUBLIC_SITE_REFRESH_ACTION, "--dry-run"]
    )
    organ_args = parser.parse_args(
        ["apply", "--only", MICROCOSM_ORGAN_ATLAS_REFRESH_ACTION, "--dry-run"]
    )

    assert site_args.only == MICROCOSM_PUBLIC_SITE_REFRESH_ACTION
    assert organ_args.only == MICROCOSM_ORGAN_ATLAS_REFRESH_ACTION


def test_cli_compact_apply_dry_run_accepts_microcosm_registered_owner_action() -> None:
    payload = generated_state_drainer_cli._compact_apply_dry_run_payload(
        MICROCOSM_PUBLIC_SITE_REFRESH_ACTION
    )

    assert payload["ok"] is True
    assert payload["status"] == "dry_run_planned_fast_compact"
    assert payload["action"]["owner_id"] == MICROCOSM_PUBLIC_SITE_OWNER_ID
    assert "sites/microcosm/content-graph.json" in payload["action"]["scope"]


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
        FRONTEND_NAVIGATION_GRAPH_REFRESH_ACTION,
        MICROCOSM_PUBLIC_SITE_REFRESH_ACTION,
        MICROCOSM_ORGAN_ATLAS_REFRESH_ACTION,
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
    assert plan["required_next_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py settle "
        "--owner-id task_ledger_projection --owner-id work_ledger_index_projection "
        "--owner-id system_atlas_projection --dry-run"
    )
    by_owner = {row["owner_id"]: row for row in plan["owners"]}
    assert by_owner[TASK_LEDGER_OWNER_ID]["required_action"] == "land_append_exempt"
    assert by_owner[TASK_LEDGER_OWNER_ID]["required_next_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py "
        "settle --owner-id task_ledger_projection --dry-run"
    )
    assert by_owner[TASK_LEDGER_OWNER_ID]["settlement_item"]["schema"] == "projection_settlement_item_v1"
    assert by_owner[TASK_LEDGER_OWNER_ID]["settlement_item_class"] == "source_dirty_projection_stale"
    assert by_owner[TASK_LEDGER_OWNER_ID]["settlement_item"]["reentry_command"].endswith(
        "settle --owner-id task_ledger_projection --dry-run"
    )
    assert by_owner[TASK_LEDGER_OWNER_ID]["settlement_item"]["retirement_condition"].startswith("owner required_action")
    assert by_owner[TASK_LEDGER_OWNER_ID]["closeout_relevance"] is True
    assert by_owner[WORK_LEDGER_OWNER_ID]["required_action"] == "land_append_exempt"
    assert by_owner[SYSTEM_ATLAS_OWNER_ID]["required_action"] == "none"
    assert by_owner[SYSTEM_ATLAS_OWNER_ID]["settlement_item_class"] == "none"
    assert by_owner[SYSTEM_ATLAS_OWNER_ID]["closeout_relevance"] is False
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


def test_compact_settlement_plan_cli_uses_fast_plan_by_default(monkeypatch) -> None:
    calls = {"fast": 0, "full": 0}
    printed: list[dict] = []

    def fake_fast_plan(repo_root: Path, *, owner_ids=None):
        calls["fast"] += 1
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "planning_mode": "cached_git_status",
            "authority_level": "cached_status_only",
            "supported_owner_ids": [TASK_LEDGER_OWNER_ID],
            "settlement_order": [TASK_LEDGER_OWNER_ID],
            "owners": [
                {
                    "owner_id": TASK_LEDGER_OWNER_ID,
                    "status": "append_exempt_manifest_available",
                    "freshness_status": "not_checked_cached_status_only",
                    "dirty_status": "dirty",
                    "source_dirty_status": "dirty",
                    "can_apply": True,
                    "blocked_by": [],
                    "required_action": "land_append_exempt",
                    "required_next_command": "settle --dry-run --fast-plan",
                    "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
                    "path_count": 1,
                    "diff_stat": {"path_count": 1, "stat_mode": "status_only"},
                    "planning_mode": "cached_git_status",
                }
            ],
            "dirty_owner_count": 1,
            "refresh_required_owner_count": 0,
            "blocked_owner_count": 0,
            "can_settle": True,
            "blocked_by": [],
            "required_next_command": "settle --dry-run --fast-plan",
            "eventful_closeout_allowed_after_settlement": False,
            "normal_source_event_after_refresh_allowed": False,
        }

    def fail_full_plan(*args, **kwargs):
        calls["full"] += 1
        raise AssertionError("compact settlement-plan should use cached fast plan by default")

    monkeypatch.setattr(generated_state_drainer_cli, "build_generated_projection_settlement_fast_plan", fake_fast_plan)
    monkeypatch.setattr(generated_state_drainer_cli, "build_generated_projection_settlement_plan", fail_full_plan)
    monkeypatch.setattr(generated_state_drainer_cli, "_print", lambda payload: printed.append(payload) or 0)

    args = generated_state_drainer_cli.build_parser().parse_args(["settlement-plan", "--compact"])

    assert generated_state_drainer_cli.cmd_settlement_plan(args) == 0
    assert calls == {"fast": 1, "full": 0}
    assert printed[0]["schema"] == "generated_projection_settlement_plan_compact_v0"
    assert printed[0]["planning_mode"] == "cached_git_status"
    assert printed[0]["authority_level"] == "cached_status_only"


def test_compact_settlement_plan_cli_full_authority_uses_owner_checks(monkeypatch) -> None:
    calls = {"fast": 0, "full": 0}
    printed: list[dict] = []

    def fail_fast_plan(*args, **kwargs):
        calls["fast"] += 1
        raise AssertionError("full-authority compact settlement-plan should not use fast plan")

    def fake_full_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        calls["full"] += 1
        assert collect_diff_stat is False
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "clean",
            "supported_owner_ids": [TASK_LEDGER_OWNER_ID],
            "settlement_order": [TASK_LEDGER_OWNER_ID],
            "owners": [],
            "dirty_owner_count": 0,
            "refresh_required_owner_count": 0,
            "blocked_owner_count": 0,
            "can_settle": True,
            "blocked_by": [],
            "required_next_command": "none",
            "eventful_closeout_allowed_after_settlement": False,
            "normal_source_event_after_refresh_allowed": False,
        }

    monkeypatch.setattr(generated_state_drainer_cli, "build_generated_projection_settlement_fast_plan", fail_fast_plan)
    monkeypatch.setattr(generated_state_drainer_cli, "build_generated_projection_settlement_plan", fake_full_plan)
    monkeypatch.setattr(generated_state_drainer_cli, "_print", lambda payload: printed.append(payload) or 0)

    args = generated_state_drainer_cli.build_parser().parse_args(
        ["settlement-plan", "--compact", "--full-authority"]
    )

    assert generated_state_drainer_cli.cmd_settlement_plan(args) == 0
    assert calls == {"fast": 0, "full": 1}
    assert printed[0]["schema"] == "generated_projection_settlement_plan_compact_v0"
    assert printed[0]["status"] == "clean"


def test_fast_settlement_plan_owner_rows_use_fast_compact_dry_run(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)

    plan = build_generated_projection_settlement_fast_plan(root, owner_ids=[TASK_LEDGER_OWNER_ID])
    owner = plan["owners"][0]

    assert plan["required_next_command"].endswith(
        "settle --owner-id task_ledger_projection --dry-run --fast-plan"
    )
    assert owner["required_next_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py "
        "settle --owner-id task_ledger_projection --dry-run --fast-plan --compact"
    )
    assert owner["settlement_item"]["reentry_command"].endswith(
        "settle --owner-id task_ledger_projection --dry-run --fast-plan --compact"
    )


def test_fast_compact_status_marks_settle_mutation_as_claim_guarded(tmp_path: Path) -> None:
    root = tmp_path
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _append_task_ledger_capture(root)
    _open_work_ledger_thread(root)

    plan = build_generated_projection_settlement_fast_plan(root)
    payload = generated_state_drainer_cli._fast_compact_status_payload(plan, owner_ids=[])

    guard = payload["actionability"]["mutation_guard"]
    assert guard["status"] == "claim_required_for_mutation"
    assert guard["can_apply_scope"] == "owner_plan_only_not_worktree_permission"
    assert guard["work_ledger_session_id_required_for_mutation"] is True
    assert "session-status --seed-speed" in guard["active_session_status_command"]
    assert "session-preflight" in guard["session_preflight_command_template"]
    assert guard["repair_sequence"][-1]["step"] == "rerun_generated_state_settle"
    assert "--work-ledger-session-id <session_id>" in guard["mutating_command_template"]

    guarded_owner_actions = [
        row for row in payload["owner_actions"] if row["required_action"] != "none"
    ]
    assert guarded_owner_actions
    assert all(row["mutation_guard"]["status"] == "claim_required_for_mutation" for row in guarded_owner_actions)


def test_settlement_refuses_missing_work_ledger_session_id_for_mutation(tmp_path: Path) -> None:
    root = tmp_path
    _init_git_repo(root)
    _append_task_ledger_capture(root)
    _open_work_ledger_thread(root)

    result = settle_generated_projection_owners(root)

    assert result["ok"] is False
    assert result["status"] == "refused"
    assert result["reason"] == "missing_work_ledger_session_id"
    assert result["blocked_by"] == ["work_ledger_session_id_required"]
    assert result["mutation_guard"]["work_ledger_session_id_required_for_mutation"] is True
    assert "session-status --seed-speed" in result["mutation_guard"]["active_session_status_command"]
    assert "session-preflight" in result["mutation_guard"]["session_preflight_command_template"]
    assert result["mutation_guard"]["repair_sequence"][-1]["command_template"] == result[
        "required_next_command"
    ]
    assert "--work-ledger-session-id <session_id>" in result["required_next_command"]
    assert result["owners"] == []
    assert result["settlement_done"] is False


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


def test_settlement_fast_mutating_plan_uses_cached_initial_selection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    work_dirty = {
        "owner_id": WORK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "not_checked_cached_status_only",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        "path_count": 1,
        "path_bundle": {
            "source_authority_paths": ["codex/ledger/09_54_1/work_ledger.jsonl"],
            "source_authority_paths_to_stage": ["codex/ledger/09_54_1/work_ledger.jsonl"],
            "projection_paths": ["codex/ledger/09_54_1/work_ledger_index.json"],
            "projection_paths_to_stage": ["codex/ledger/09_54_1/work_ledger_index.json"],
            "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        },
    }
    clean_plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "clean",
        "authority_level": "full_owner_checks",
        "can_settle": True,
        "blocked_by": [],
        "owners": [],
    }
    calls = {"fast_plan": 0, "full_plan": 0, "land": 0}

    def fake_fast_plan(repo_root: Path, *, owner_ids=None):
        calls["fast_plan"] += 1
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "planning_mode": "cached_git_status",
            "authority_level": "cached_status_only",
            "can_settle": True,
            "blocked_by": [],
            "dirty_owner_count": 1,
            "blocked_owner_count": 0,
            "owners": [work_dirty],
        }

    def fake_full_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        calls["full_plan"] += 1
        return clean_plan

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        calls["land"] += 1
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": "commit-work",
            "paths_staged": ["codex/ledger/09_54_1/work_ledger.jsonl"],
            "landing_manifest_path": work_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_fast_plan", fake_fast_plan)
    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_full_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        owner_ids=[WORK_LEDGER_OWNER_ID],
        fast_plan=True,
        max_passes=1,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert calls == {"fast_plan": 1, "full_plan": 1, "land": 1}
    assert result["ok"] is True
    assert result["status"] == "settled"
    assert result["before_plan"]["authority_level"] == "cached_status_only"
    assert result["final_plan"]["authority_level"] == "full_owner_checks"
    assert result["timing"]["phases"][0]["fast_plan"] is True
    assert result["timing"]["phases"][0]["authority_level"] == "cached_status_only"


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


def test_settle_cli_blocks_mutating_run_when_host_pressure_queues_projection(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    calls: list[dict] = []

    def fake_admission(repo_root: Path) -> dict:
        calls.append({"repo_root": repo_root})
        return {
            "schema": "generated_state_drainer_host_pressure_admission_v0",
            "status": "available",
            "decision": "queue_until_pressure_clears",
            "reason": "memory_pressure_blocks_background_projection",
            "requested_workload_class": "background_projection",
            "should_block_run": True,
            "recheck_command": "./repo-python kernel.py --host-pressure --host-pressure-admission-only",
        }

    def fail_singleflight(*args, **kwargs) -> int:
        raise AssertionError("blocked host pressure must not enter singleflight settlement")

    monkeypatch.delenv(generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV, raising=False)
    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "_settle_host_pressure_admission", fake_admission)
    monkeypatch.setattr(generated_state_drainer_cli, "run_command_singleflight", fail_singleflight)

    result = generated_state_drainer_cli.main(
        ["settle", "--owner-id", TASK_LEDGER_OWNER_ID, "--work-ledger-session-id", "codex_session"]
    )

    assert result == 1
    assert calls == [{"repo_root": tmp_path}]
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "queued_until_host_pressure_clears"
    assert payload["requested_workload_class"] == "background_projection"
    assert payload["host_pressure_admission"]["decision"] == "queue_until_pressure_clears"
    assert payload["deferred_suggested_command"].endswith("settle --dry-run --fast-plan")
    assert payload["override_flag"] == "--ignore-host-pressure"


def test_settle_cli_ignore_host_pressure_keeps_singleflight_override(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[dict] = []
    admission_calls: list[Path] = []

    def fake_admission(repo_root: Path) -> dict:
        admission_calls.append(repo_root)
        return {
            "status": "available",
            "decision": "queue_until_pressure_clears",
            "should_block_run": True,
        }

    def fake_run_command_singleflight(repo_root: Path, **kwargs) -> int:
        calls.append({"repo_root": repo_root, **kwargs})
        return 0

    monkeypatch.delenv(generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV, raising=False)
    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "_settle_host_pressure_admission", fake_admission)
    monkeypatch.setattr(generated_state_drainer_cli, "run_command_singleflight", fake_run_command_singleflight)

    result = generated_state_drainer_cli.main(
        [
            "settle",
            "--owner-id",
            TASK_LEDGER_OWNER_ID,
            "--work-ledger-session-id",
            "codex_session",
            "--ignore-host-pressure",
        ]
    )

    assert result == 0
    assert admission_calls == []
    assert calls
    assert "--ignore-host-pressure" in calls[0]["argv"]
    assert calls[0]["resource_class"] == "generated_state"


def test_compact_settle_cli_uses_fast_initial_plan(monkeypatch, tmp_path: Path, capsys) -> None:
    observed: dict[str, object] = {}

    def fake_settle(repo_root: Path, **kwargs) -> dict:
        observed.update(kwargs)
        return {
            "schema": "generated_projection_settlement_v0",
            "ok": True,
            "status": "settled",
        }

    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "settle_generated_projection_owners", fake_settle)

    args = argparse.Namespace(
        owner_id=[WORK_LEDGER_OWNER_ID],
        dry_run=False,
        max_passes=1,
        fast_plan=False,
        compact=True,
        work_ledger_session_id="codex_session",
        quiet_progress=True,
    )

    assert generated_state_drainer_cli.cmd_settle(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "settled"
    assert observed["fast_plan"] is True
    assert observed["bounded_final_plan"] is True
    assert observed["work_ledger_session_id"] == "codex_session"


def test_fast_plan_settle_cli_uses_bounded_final_plan_for_mutation(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    observed: dict[str, object] = {}

    def fake_settle(repo_root: Path, **kwargs) -> dict:
        observed.update(kwargs)
        return {
            "schema": "generated_projection_settlement_v0",
            "ok": True,
            "status": "settled",
        }

    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "settle_generated_projection_owners", fake_settle)

    args = argparse.Namespace(
        owner_id=[TASK_LEDGER_OWNER_ID],
        dry_run=False,
        max_passes=1,
        fast_plan=True,
        compact=False,
        work_ledger_session_id="codex_session",
        quiet_progress=True,
    )

    assert generated_state_drainer_cli.cmd_settle(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "settled"
    assert observed["fast_plan"] is True
    assert observed["bounded_final_plan"] is True
    assert observed["work_ledger_session_id"] == "codex_session"


def test_fast_plan_settle_cli_keeps_dry_run_full_output_available(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    observed: dict[str, object] = {}

    def fake_settle(repo_root: Path, **kwargs) -> dict:
        observed.update(kwargs)
        return {
            "schema": "generated_projection_settlement_v0",
            "ok": True,
            "dry_run": True,
            "status": "would_settle",
        }

    monkeypatch.setattr(generated_state_drainer_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generated_state_drainer_cli, "settle_generated_projection_owners", fake_settle)

    args = argparse.Namespace(
        owner_id=[TASK_LEDGER_OWNER_ID],
        dry_run=True,
        max_passes=1,
        fast_plan=True,
        compact=False,
        work_ledger_session_id=None,
        quiet_progress=True,
    )

    assert generated_state_drainer_cli.cmd_settle(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "would_settle"
    assert observed["fast_plan"] is True
    assert observed["bounded_final_plan"] is False
    assert observed["work_ledger_session_id"] is None


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

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_settlement_plan",
        lambda *args, **kwargs: plan,
    )

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

    result = settle_generated_projection_owners(
        root,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

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

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=3,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

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

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=3,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

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

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=2,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

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


def test_settlement_repeated_signature_reports_source_moved_after_prior_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_source_moved = {
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
            "source_authority_paths_to_stage": [
                "state/task_ledger/events.jsonl",
                "state/task_ledger/events_audit.jsonl",
            ],
            "dirty_path_summary": {"source_authority_dirty_count": 2},
        },
    }
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "can_settle": True,
        "blocked_by": [],
        "owners": [task_source_moved],
    }
    state = {"land_count": 0}

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        state["land_count"] += 1
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": f"commit-{state['land_count']}",
            "paths_staged": [owner_id],
            "landing_manifest_path": task_source_moved["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=2,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settlement_residual_source_moved"
    assert result["reason"] == "source_authority_moved_during_settlement"
    assert result["partial_success"] is True
    assert result["residual_class"] == "concurrent_source_authority_moved"
    assert result["terminal_residual"] is True
    assert result["residual_actionability"] == "wait_for_source_authority_quiescence_before_retry"
    assert result["retry_policy"] == "do_not_loop_immediately_after_partial_settlement_progress"
    assert "settlement-plan --fast --compact" in result["next_safe_command"]
    assert "do not repeat settlement in a tight loop" in result["reentry_condition"]
    assert result["progress"]["commit_count"] == 1
    assert result["progress"]["commit_hashes"] == ["commit-1"]
    assert result["source_moved_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert result["previous_pass_index"] == 1
    assert result["current_pass_index"] == 2
    assert state["land_count"] == 1


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

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=2,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is False
    assert result["status"] == "settlement_residual_capped"
    assert result["reason"] == "max_passes_exhausted"
    assert result["pass_count"] == 2
    assert result["progress"]["commit_count"] == 2
    assert result["progress"]["commit_hashes"] == ["commit-1", "commit-2"]
    assert result["residual_owners"][0]["total_changed_lines"] == 7


def test_settlement_reports_source_moved_residual_when_refresh_required_after_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def refresh_plan(plan_count: int) -> dict:
        task_dirty = {
            "owner_id": TASK_LEDGER_OWNER_ID,
            "status": "refresh_required",
            "freshness_status": "stale",
            "dirty_status": "dirty",
            "source_dirty_status": "dirty",
            "can_apply": True,
            "blocked_by": ["projection_not_fresh"],
            "required_action": "refresh_then_land_append_exempt",
            "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
            "path_count": 2,
            "diff_stat": {"path_count": 2, "total_changed_lines": 4 + plan_count},
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
        return refresh_plan(state["plan_count"])

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

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=1,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settlement_residual_source_moved"
    assert result["reason"] == "source_authority_moved_during_settlement"
    assert result["partial_success"] is True
    assert result["residual_class"] == "concurrent_source_authority_moved"
    assert result["terminal_residual"] is True
    assert result["retry_policy"] == "do_not_loop_immediately_after_partial_settlement_progress"
    assert result["settlement_done"] is False
    assert result["progress"]["commit_count"] == 1
    assert result["source_moved_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert result["residual_owners"][0]["required_action"] == "refresh_then_land_append_exempt"


def test_settlement_reports_source_moved_residual_when_append_exempt_source_dirty_after_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:
    work_dirty = {
        "owner_id": WORK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2},
    }
    task_source_moved = {
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
        "diff_stat": {"path_count": 2, "total_changed_lines": 6},
        "path_bundle": {
            "source_authority_paths_to_stage": [
                "state/task_ledger/events.jsonl",
                "state/task_ledger/events_audit.jsonl",
            ],
            "dirty_path_summary": {"source_authority_dirty_count": 2},
        },
    }
    plans = [
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [work_dirty],
        },
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [task_source_moved],
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
            "commit_hash": "commit-work",
            "paths_staged": [owner_id],
            "landing_manifest_path": work_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=1,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settlement_residual_source_moved"
    assert result["reason"] == "source_authority_moved_during_settlement"
    assert result["partial_success"] is True
    assert result["residual_class"] == "concurrent_source_authority_moved"
    assert result["terminal_residual"] is True
    assert result["retry_policy"] == "do_not_loop_immediately_after_partial_settlement_progress"
    assert result["progress"]["commit_hashes"] == ["commit-work"]
    assert result["source_moved_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert result["residual_owners"][0]["required_action"] == "land_append_exempt"


def test_settlement_stops_before_refresh_source_moved_owner_after_prior_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    work_dirty = {
        "owner_id": WORK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2},
    }
    task_refresh_source_moved = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "stale",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "refresh_then_land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "diff_stat": {"path_count": 2, "total_changed_lines": 6},
        "path_bundle": {
            "source_authority_paths_to_stage": [
                "state/task_ledger/events.jsonl",
                "state/task_ledger/events_audit.jsonl",
            ],
            "dirty_path_summary": {"source_authority_dirty_count": 2},
        },
    }
    plans = [
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [work_dirty],
        },
        {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [task_refresh_source_moved, work_dirty],
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
            "commit_hash": f"commit-{len(state['landed'])}",
            "paths_staged": [owner_id],
            "landing_manifest_path": work_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=3,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settlement_residual_source_moved"
    assert result["reason"] == "source_authority_moved_during_settlement"
    assert result["partial_success"] is True
    assert result["residual_class"] == "concurrent_source_authority_moved"
    assert result["terminal_residual"] is True
    assert result["pass_count"] == 1
    assert result["current_pass_index"] == 2
    assert result["progress"]["commit_hashes"] == ["commit-1"]
    assert result["source_moved_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert state["landed"] == [WORK_LEDGER_OWNER_ID]


def test_settlement_bounded_final_plan_avoids_full_replan_after_commit_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initial_owner = {
        "owner_id": WORK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2},
    }
    moved_owner = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "not_checked_cached_status_only",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "refresh_then_land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "diff_stat": {"path_count": 2, "stat_mode": "status_only"},
    }
    call_count = {"full_plan": 0, "fast_plan": 0}

    def fake_full_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        call_count["full_plan"] += 1
        if call_count["full_plan"] > 1:
            raise AssertionError("bounded final plan should skip the full post-commit replan")
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "owners": [initial_owner],
        }

    def fake_fast_plan(repo_root: Path, *, owner_ids=None):
        call_count["fast_plan"] += 1
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "authority_level": "cached_status_only",
            "can_settle": True,
            "blocked_by": [],
            "dirty_owner_count": 1,
            "blocked_owner_count": 0,
            "owners": [moved_owner],
        }

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": "commit-work",
            "paths_staged": [owner_id],
            "landing_manifest_path": initial_owner["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_full_plan)
    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_fast_plan", fake_fast_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=1,
        bounded_final_plan=True,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert call_count == {"full_plan": 1, "fast_plan": 1}
    assert result["ok"] is True
    assert result["status"] == "settlement_residual_source_moved"
    assert result["source_moved_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert result["terminal_residual"] is True
    assert result["timing"]["phases"][-1]["phase"] == "final_fast_plan"
    assert result["final_plan"]["authority_level"] == "cached_status_only"


def test_settlement_reports_source_moved_residual_when_refresh_owner_fails_after_prior_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    work_dirty = {
        "owner_id": WORK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "fresh_dirty",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2},
    }
    task_refresh = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "stale",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": ["projection_not_fresh"],
        "required_action": "refresh_then_land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "diff_stat": {"path_count": 2, "total_changed_lines": 5},
    }
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "can_settle": True,
        "blocked_by": [],
        "owners": [work_dirty, task_refresh],
    }

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        if owner_id == WORK_LEDGER_OWNER_ID:
            return {
                "ok": True,
                "status": "landed",
                "commit_hash": "commit-work",
                "paths_staged": [owner_id],
                "landing_manifest_path": work_dirty["landing_manifest_path"],
            }
        return {
            "ok": False,
            "status": "refresh_required",
            "reason": "projection_not_fresh",
            "paths_staged": [owner_id],
            "landing_manifest_path": task_refresh["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=3,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settlement_residual_source_moved"
    assert result["reason"] == "source_authority_moved_during_settlement"
    assert result["partial_success"] is True
    assert result["residual_class"] == "concurrent_source_authority_moved"
    assert result["terminal_residual"] is True
    assert result["retry_policy"] == "do_not_loop_immediately_after_partial_settlement_progress"
    assert result["settlement_done"] is False
    assert result["progress"]["commit_hashes"] == ["commit-work"]
    assert result["source_moved_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert result["owners"][1]["result_status"] == "refresh_required"


def test_settlement_reports_freshness_only_residual_after_zero_diff_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial_owner = {
        "owner_id": SYSTEM_ATLAS_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "stale",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "refresh_then_land_append_exempt",
        "landing_manifest_path": (
            "state/generated_projection_landing/system_atlas_projection_manifest.json"
        ),
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 2},
    }
    freshness_only_owner = {
        "owner_id": SYSTEM_ATLAS_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "stale",
        "dirty_status": "clean",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": ["projection_not_fresh"],
        "required_action": "refresh_then_land_append_exempt",
        "landing_manifest_path": (
            "state/generated_projection_landing/system_atlas_projection_manifest.json"
        ),
        "path_count": 1,
        "diff_stat": {"path_count": 1, "total_changed_lines": 0},
        "path_bundle": {
            "source_authority_paths_to_stage": [],
            "projection_paths_to_stage": [],
            "dirty_path_summary": {
                "source_authority_dirty_count": 0,
                "projection_dirty_count": 0,
                "landing_manifest_dirty": False,
            },
        },
    }
    calls = {"plan": 0}

    def fake_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        calls["plan"] += 1
        owner = initial_owner if calls["plan"] == 1 else freshness_only_owner
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "can_settle": True,
            "blocked_by": [],
            "dirty_owner_count": 1,
            "blocked_owner_count": 0,
            "owners": [owner],
        }

    def fake_land(
        repo_root: Path,
        *,
        owner_id: str,
        mode: str,
        dry_run: bool = False,
        **kwargs,
    ):
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": "commit-system-atlas",
            "paths_staged": [owner_id],
            "landing_manifest_path": initial_owner["landing_manifest_path"],
        }

    monkeypatch.setattr(
        generated_state_drainer,
        "build_generated_projection_settlement_plan",
        fake_plan,
    )
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=1,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settlement_residual_freshness_only"
    assert result["reason"] == "zero_diff_freshness_marker_after_settlement"
    assert result["residual_class"] == "zero_diff_freshness_only"
    assert result["freshness_only_owner_ids"] == [SYSTEM_ATLAS_OWNER_ID]
    assert result["retry_policy"] == "do_not_loop_for_zero_diff_freshness_residual"
    assert result["residual_owners"][0]["total_changed_lines"] == 0
    assert result["progress"]["commit_hashes"] == ["commit-system-atlas"]


def test_settlement_returns_retry_later_when_task_ledger_source_lock_held(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if task_ledger_events.fcntl is None:
        pytest.skip("nonblocking Task Ledger source lock probe requires fcntl")
    monkeypatch.setattr(generated_state_drainer, "TASK_LEDGER_SOURCE_LOCK_RETRY_SLEEP_S", 0)
    lock_path = tmp_path / task_ledger_events.LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as handle:
        task_ledger_events.fcntl.flock(
            handle.fileno(),
            task_ledger_events.fcntl.LOCK_EX | task_ledger_events.fcntl.LOCK_NB,
        )
        try:
            result = generated_state_drainer.settle_generated_projection_owners(
                tmp_path,
                owner_ids=[TASK_LEDGER_OWNER_ID],
            )
        finally:
            task_ledger_events.fcntl.flock(handle.fileno(), task_ledger_events.fcntl.LOCK_UN)

    assert result["ok"] is False
    assert result["status"] == "settlement_retry_later"
    assert result["reason"] == "task_ledger_source_mutation_in_progress"
    assert result["retry_later"] is True
    assert result["retry_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert result["source_moving_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert result["blocked_by"] == ["task_ledger_source_writer_lock_held"]
    assert result["source_lock"]["attempts"] == (
        generated_state_drainer.TASK_LEDGER_SOURCE_LOCK_ATTEMPTS
    )
    assert result["source_lock"]["lock_file_exists"] is True
    assert result["progress_events"] == [
        {
            "event": "source_lock_retry_later",
            "owner_id": TASK_LEDGER_OWNER_ID,
            "status": "busy",
            "reason": "task_ledger_source_writer_lock_held",
        }
    ]


def test_settlement_owner_retry_later_skips_final_replan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_refresh = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "stale",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": ["projection_not_fresh"],
        "required_action": "refresh_then_land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "diff_stat": {"path_count": 2, "total_changed_lines": 5},
    }
    plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "can_settle": True,
        "blocked_by": [],
        "owners": [task_refresh],
    }
    state = {"plan_count": 0, "land_count": 0}

    def fake_plan(repo_root: Path, *, owner_ids=None, collect_diff_stat: bool = True):
        state["plan_count"] += 1
        return plan

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        state["land_count"] += 1
        return {
            "ok": False,
            "status": "retry_later",
            "reason": "task_ledger_source_mutation_in_progress",
            "retry_later": True,
            "blocked_by": ["task_ledger_source_writer_lock_held"],
            "landing_manifest_path": task_refresh["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fake_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        owner_ids=[TASK_LEDGER_OWNER_ID],
        max_passes=3,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is False
    assert result["status"] == "settlement_retry_later"
    assert result["reason"] == "task_ledger_source_mutation_in_progress"
    assert result["retry_owner_ids"] == [TASK_LEDGER_OWNER_ID]
    assert state["land_count"] == 1
    assert state["plan_count"] == 1
    assert result["owners"][0]["result_status"] == "retry_later"


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

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        max_passes=3,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

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
    assert task_owner["settlement_item_class"] == "source_dirty_projection_stale"
    assert task_owner["settlement_item"]["closeout_relevance"] is True
    assert result["ok"] is True
    assert result["status"] == "would_settle"
    assert result["owners"][0]["result_status"] == "would_refresh_then_land"
    assert "state/task_ledger/ledger.json" in result["owners"][0]["paths_to_stage"]


def test_fast_plan_settlement_passes_refresh_owner_row_to_landing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_refresh = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "refresh_required",
        "freshness_status": "not_checked_cached_status_only",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "refresh_then_land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "path_bundle": {
            "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
            "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
            "projection_paths": [str(task_ledger_events.LEDGER_REL)],
            "projection_paths_to_stage": [],
            "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        },
    }
    dirty_plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "authority_level": "cached_status_only",
        "can_settle": True,
        "blocked_by": [],
        "dirty_owner_count": 1,
        "blocked_owner_count": 0,
        "owners": [task_refresh],
    }
    clean_plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "clean",
        "authority_level": "cached_status_only",
        "can_settle": True,
        "blocked_by": [],
        "dirty_owner_count": 0,
        "blocked_owner_count": 0,
        "owners": [],
    }
    plan_calls = {"count": 0}
    observed: dict[str, object] = {}

    def fake_fast_plan(repo_root: Path, *, owner_ids=None):
        plan_calls["count"] += 1
        return dirty_plan if plan_calls["count"] == 1 else clean_plan

    def fail_full_plan(*args, **kwargs):
        raise AssertionError("fast-plan settlement should not need a full owner replan for refresh-first task ledger landing")

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        observed.update(kwargs)
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": "commit-task-refresh",
            "paths_to_stage": [
                str(task_ledger_events.EVENTS_REL),
                str(task_ledger_events.LEDGER_REL),
            ],
            "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
            "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
            "projection_paths": [str(task_ledger_events.LEDGER_REL)],
            "landing_manifest_path": task_refresh["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_fast_plan", fake_fast_plan)
    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fail_full_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        fast_plan=True,
        bounded_final_plan=True,
        max_passes=1,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settled"
    assert observed["landing_plan"] is task_refresh


def test_fast_plan_settlement_passes_dirty_task_source_owner_row_to_landing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_dirty = {
        "owner_id": TASK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "not_checked_cached_status_only",
        "dirty_status": "dirty",
        "source_dirty_status": "dirty",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        "path_count": 2,
        "path_bundle": {
            "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
            "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
            "projection_paths": [str(task_ledger_events.LEDGER_REL)],
            "projection_paths_to_stage": [str(task_ledger_events.LEDGER_REL)],
            "landing_manifest_path": "state/generated_projection_landing/task_ledger_projection_manifest.json",
        },
    }
    dirty_plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "authority_level": "cached_status_only",
        "can_settle": True,
        "blocked_by": [],
        "dirty_owner_count": 1,
        "blocked_owner_count": 0,
        "owners": [task_dirty],
    }
    clean_plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "clean",
        "authority_level": "cached_status_only",
        "can_settle": True,
        "blocked_by": [],
        "dirty_owner_count": 0,
        "blocked_owner_count": 0,
        "owners": [],
    }
    plan_calls = {"count": 0}
    observed: dict[str, object] = {}

    def fake_fast_plan(repo_root: Path, *, owner_ids=None):
        plan_calls["count"] += 1
        return dirty_plan if plan_calls["count"] == 1 else clean_plan

    def fail_full_plan(*args, **kwargs):
        raise AssertionError("dirty task-ledger source rows should reuse the fast owner row before locked replan")

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        observed.update(kwargs)
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": "commit-task-dirty",
            "paths_to_stage": [
                str(task_ledger_events.EVENTS_REL),
                str(task_ledger_events.LEDGER_REL),
            ],
            "source_authority_paths": [str(task_ledger_events.EVENTS_REL)],
            "source_authority_paths_to_stage": [str(task_ledger_events.EVENTS_REL)],
            "projection_paths": [str(task_ledger_events.LEDGER_REL)],
            "landing_manifest_path": task_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_fast_plan", fake_fast_plan)
    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fail_full_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        fast_plan=True,
        bounded_final_plan=True,
        max_passes=1,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settled"
    assert observed["landing_plan"] is task_dirty


def test_fast_plan_settlement_passes_work_ledger_owner_row_to_landing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    work_dirty = {
        "owner_id": WORK_LEDGER_OWNER_ID,
        "status": "append_exempt_manifest_available",
        "freshness_status": "not_checked_cached_status_only",
        "dirty_status": "dirty",
        "source_dirty_status": "clean",
        "can_apply": True,
        "blocked_by": [],
        "required_action": "land_append_exempt",
        "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        "path_count": 2,
        "path_bundle": {
            "source_authority_paths": [
                "codex/ledger/09_35/work_ledger.jsonl",
                "codex/ledger/09_54_1/work_ledger.jsonl",
            ],
            "source_authority_paths_to_stage": [],
            "projection_paths": [
                "codex/ledger/09_35/work_ledger_index.json",
                "codex/ledger/09_54_1/work_ledger_index.json",
            ],
            "projection_paths_to_stage": [
                "codex/ledger/09_35/work_ledger_index.json",
            ],
            "landing_manifest_path": "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
        },
    }
    dirty_plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "settlement_required",
        "authority_level": "cached_status_only",
        "can_settle": True,
        "blocked_by": [],
        "dirty_owner_count": 1,
        "blocked_owner_count": 0,
        "owners": [work_dirty],
    }
    clean_plan = {
        "schema": "generated_projection_settlement_plan_v0",
        "ok": True,
        "status": "clean",
        "authority_level": "cached_status_only",
        "can_settle": True,
        "blocked_by": [],
        "dirty_owner_count": 0,
        "blocked_owner_count": 0,
        "owners": [],
    }
    plan_calls = {"count": 0}
    observed: dict[str, object] = {}

    def fake_fast_plan(repo_root: Path, *, owner_ids=None):
        plan_calls["count"] += 1
        return dirty_plan if plan_calls["count"] == 1 else clean_plan

    def fail_full_plan(*args, **kwargs):
        raise AssertionError("fast-plan settlement should reuse the Work Ledger owner bundle")

    def fake_land(repo_root: Path, *, owner_id: str, mode: str, dry_run: bool = False, **kwargs):
        observed.update(kwargs)
        return {
            "ok": True,
            "status": "landed",
            "commit_hash": "commit-work-ledger",
            "paths_to_stage": [
                "codex/ledger/09_35/work_ledger_index.json",
                "state/generated_projection_landing/work_ledger_index_projection_manifest.json",
            ],
            "source_authority_paths": work_dirty["path_bundle"]["source_authority_paths"],
            "source_authority_paths_to_stage": [],
            "projection_paths": work_dirty["path_bundle"]["projection_paths"],
            "landing_manifest_path": work_dirty["landing_manifest_path"],
        }

    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_fast_plan", fake_fast_plan)
    monkeypatch.setattr(generated_state_drainer, "build_generated_projection_settlement_plan", fail_full_plan)
    monkeypatch.setattr(generated_state_drainer, "land_generated_projection_bundle", fake_land)

    result = generated_state_drainer.settle_generated_projection_owners(
        tmp_path,
        fast_plan=True,
        bounded_final_plan=True,
        max_passes=1,
        work_ledger_session_id=TEST_WORK_LEDGER_SESSION_ID,
    )

    assert result["ok"] is True
    assert result["status"] == "settled"
    landing_plan = observed["landing_plan"]
    assert isinstance(landing_plan, dict)
    assert landing_plan["owner_id"] == WORK_LEDGER_OWNER_ID
    assert landing_plan["projection_paths"] == work_dirty["path_bundle"]["projection_paths"]
    assert landing_plan["projection_paths_to_stage"] == work_dirty["path_bundle"]["projection_paths_to_stage"]
    assert landing_plan["landing_manifest_path"] == work_dirty["landing_manifest_path"]


def test_settlement_refuses_unsupported_owner(tmp_path: Path) -> None:
    root = tmp_path

    plan = build_generated_projection_settlement_plan(root, owner_ids=["unsupported_projection_owner"])
    result = settle_generated_projection_owners(root, owner_ids=["unsupported_projection_owner"], dry_run=True)

    assert plan["status"] == "blocked"
    assert plan["can_settle"] is False
    assert plan["blocked_by"] == ["unsupported_owner_id", "owner_settlement_blocked"]
    assert plan["owners"][0]["settlement_item_class"] == "owner_landing_policy_not_implemented"
    assert plan["owners"][0]["settlement_item"]["reentry_command"] == "none"
    assert result["ok"] is False
    assert result["status"] == "blocked"
