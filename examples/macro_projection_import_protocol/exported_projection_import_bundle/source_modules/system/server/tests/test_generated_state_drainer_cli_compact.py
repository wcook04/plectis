from __future__ import annotations

import json

import tools.meta.control.generated_state_drainer as generated_state_drainer_cli


def test_status_compact_emits_counts_and_full_drilldown(monkeypatch, capsys) -> None:
    def fake_status(repo_root, owner_ids=None):
        assert owner_ids == ["task_ledger_projection"]
        return {
            "schema": "generated_state_drainer_status_v0",
            "ok": True,
            "mode": "read_only",
            "repo_root": str(repo_root),
            "summary": {"stale_count": 1, "dirty_count": 1},
            "owners": [
                {"owner_id": "task_ledger_projection"},
                {"owner_id": "work_ledger_index_projection"},
            ],
            "projection_targets": [
                {
                    "generated_path": "state/task_ledger/ledger.json",
                    "owner_id": "task_ledger_projection",
                    "owner_tool": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild",
                    "check_command": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
                    "freshness_status": "projection_stale",
                    "dirty_status": "dirty",
                    "recommended_owner_action": "refresh",
                },
                {
                    "generated_path": "state/task_ledger/views/recent_events.json",
                    "owner_id": "task_ledger_projection",
                    "owner_tool": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild",
                    "check_command": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
                    "freshness_status": "fresh",
                    "dirty_status": "clean",
                    "recommended_owner_action": "none",
                },
            ],
            "dirty_generated_paths": [
                {
                    "generated_path": "state/task_ledger/ledger.json",
                    "owner_id": "task_ledger_projection",
                    "owner_tool": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild",
                    "check_command": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
                    "freshness_status": "projection_stale",
                    "dirty_status": "dirty",
                    "recommended_owner_action": "refresh",
                    "source_event_hash": "full-row-hash-omitted-from-compact",
                    "projection_hash": "full-row-projection-hash-omitted-from-compact",
                    "source_authority": {"large": "omitted"},
                    "commit_policy": {"large": "omitted"},
                    "safe_to_commit_by_agent": False,
                    "counts": {"large": "omitted"},
                }
            ],
            "owner_checks": {
                "task_ledger_projection": {
                    "ok": False,
                    "mode": "check",
                    "mismatches": [{"path": "state/task_ledger/ledger.json"}],
                    "projection_paths": [
                        "state/task_ledger/ledger.json",
                        "state/task_ledger/views/recent_events.json",
                    ],
                }
            },
            "non_goals": ["does_not_commit_generated_state"],
        }

    monkeypatch.setattr(generated_state_drainer_cli, "build_generated_state_drainer_status", fake_status)

    exit_code = generated_state_drainer_cli.main(
        ["status", "--owner-id", "task_ledger_projection", "--compact"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_state_drainer_status_compact_v0"
    assert payload["summary"] == {"stale_count": 1, "dirty_count": 1}
    assert payload["counts"]["projection_target_count"] == 2
    assert payload["counts"]["freshness"] == {"fresh": 1, "projection_stale": 1}
    assert payload["counts"]["dirty_status"] == {"clean": 1, "dirty": 1}
    assert payload["actionability"] == {
        "schema": "generated_state_drainer_compact_actionability_v0",
        "status": "dirty_owner_action_required",
        "recommended_next": (
            "run the owner action for dirty generated paths before treating generated state as settled"
        ),
        "dirty_recommended_action_count": 1,
        "clean_recommended_action_count": 0,
        "dirty_fresh_no_action_count": 0,
        "clean_recommended_action_sample_paths": [],
        "dirty_recommended_action_sample_paths": ["state/task_ledger/ledger.json"],
    }
    assert payload["dirty_generated_paths_sample"] == [
        {
            "generated_path": "state/task_ledger/ledger.json",
            "owner_id": "task_ledger_projection",
            "freshness_status": "projection_stale",
            "dirty_status": "dirty",
            "recommended_owner_action": "refresh",
            "check_command": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
            "owner_tool": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild",
        }
    ]
    assert payload["dirty_generated_paths_omission_receipt"]["status"] == (
        "full_dirty_rows_omitted_from_compact_sample"
    )
    assert "source_event_hash" in payload["dirty_generated_paths_omission_receipt"]["omitted_fields"]
    assert "source_event_hash" not in json.dumps(payload["dirty_generated_paths_sample"])
    assert payload["projection_groups"] == [
        {
            "owner_id": "task_ledger_projection",
            "projection_count": 2,
            "freshness": {"projection_stale": 1, "fresh": 1},
            "dirty_status": {"dirty": 1, "clean": 1},
            "recommended_owner_action": {"refresh": 1, "none": 1},
            "dirty_recommended_action_count": 1,
            "clean_recommended_action_count": 0,
            "dirty_fresh_no_action_count": 0,
            "dirty_or_stale_sample_paths": ["state/task_ledger/ledger.json"],
            "clean_recommended_action_sample_paths": [],
            "check_command": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
            "owner_tool": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild",
        }
    ]
    assert payload["owner_checks"]["task_ledger_projection"] == {
        "ok": False,
        "mode": "check",
        "mismatch_count": 1,
        "projection_path_count": 2,
    }
    assert (
        payload["drilldown"]["full_status_command"]
        == "./repo-python tools/meta/control/generated_state_drainer.py status --owner-id task_ledger_projection"
    )


def test_status_compact_distinguishes_clean_stale_backlog_from_dirty_fresh_paths(
    monkeypatch,
    capsys,
) -> None:
    def fake_status(repo_root, owner_ids=None):
        return {
            "schema": "generated_state_drainer_status_v0",
            "ok": True,
            "mode": "read_only",
            "repo_root": str(repo_root),
            "summary": {"status": "stale", "stale_count": 1, "dirty_count": 1},
            "owners": [{"owner_id": "work_ledger_index_projection"}],
            "projection_targets": [
                {
                    "generated_path": "codex/ledger/09_54/work_ledger_index.json",
                    "owner_id": "work_ledger_index_projection",
                    "owner_tool": "./repo-python tools/meta/factory/work_ledger.py project --all",
                    "check_command": "./repo-python tools/meta/factory/work_ledger.py project --check --all",
                    "freshness_status": "fresh",
                    "dirty_status": "modified",
                    "recommended_owner_action": "none",
                },
                {
                    "generated_path": "codex/ledger/09_35/work_ledger_index.json",
                    "owner_id": "work_ledger_index_projection",
                    "owner_tool": "./repo-python tools/meta/factory/work_ledger.py project --all",
                    "check_command": "./repo-python tools/meta/factory/work_ledger.py project --check --all",
                    "freshness_status": "projection_stale",
                    "dirty_status": "clean",
                    "recommended_owner_action": "./repo-python tools/meta/factory/work_ledger.py project --all",
                },
            ],
            "dirty_generated_paths": [
                {
                    "generated_path": "codex/ledger/09_54/work_ledger_index.json",
                    "owner_id": "work_ledger_index_projection",
                    "freshness_status": "fresh",
                    "dirty_status": "modified",
                    "recommended_owner_action": "none",
                }
            ],
            "owner_checks": {
                "work_ledger_index_projection": {
                    "ok": False,
                    "mode": "check",
                    "families": [
                        {
                            "family_id": "09",
                            "ok": False,
                            "projection_results": [
                                {
                                    "phase_id": "09_35",
                                    "index_path": "codex/ledger/09_35/work_ledger_index.json",
                                    "fresh": False,
                                    "reason": "projection_stale",
                                },
                                {
                                    "phase_id": "09_54",
                                    "index_path": "codex/ledger/09_54/work_ledger_index.json",
                                    "fresh": True,
                                    "reason": "fresh",
                                },
                            ],
                        }
                    ],
                }
            },
            "non_goals": ["does_not_commit_generated_state"],
        }

    monkeypatch.setattr(generated_state_drainer_cli, "build_generated_state_drainer_status", fake_status)

    exit_code = generated_state_drainer_cli.main(["status", "--compact"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["status"] == "stale"
    assert payload["actionability"]["status"] == "clean_or_historical_backlog_only"
    assert payload["actionability"]["dirty_recommended_action_count"] == 0
    assert payload["actionability"]["clean_recommended_action_count"] == 1
    assert payload["actionability"]["dirty_fresh_no_action_count"] == 1
    assert payload["actionability"]["clean_recommended_action_sample_paths"] == [
        "codex/ledger/09_35/work_ledger_index.json"
    ]
    assert payload["projection_groups"] == [
        {
            "owner_id": "work_ledger_index_projection",
            "projection_count": 2,
            "freshness": {"fresh": 1, "projection_stale": 1},
            "dirty_status": {"modified": 1, "clean": 1},
            "recommended_owner_action": {
                "./repo-python tools/meta/factory/work_ledger.py project --all": 1,
                "none": 1,
            },
            "dirty_recommended_action_count": 0,
            "clean_recommended_action_count": 1,
            "dirty_fresh_no_action_count": 1,
            "dirty_or_stale_sample_paths": [
                "codex/ledger/09_54/work_ledger_index.json",
                "codex/ledger/09_35/work_ledger_index.json",
            ],
            "clean_recommended_action_sample_paths": [
                "codex/ledger/09_35/work_ledger_index.json"
            ],
            "check_command": "./repo-python tools/meta/factory/work_ledger.py project --check --all",
            "owner_tool": "./repo-python tools/meta/factory/work_ledger.py project --all",
        }
    ]
    assert payload["owner_checks"]["work_ledger_index_projection"] == {
        "ok": False,
        "mode": "check",
        "mismatch_count": 0,
        "projection_path_count": 0,
        "family_count": 1,
        "projection_result_count": 2,
        "stale_projection_count": 1,
        "fresh_projection_count": 1,
        "reason_counts": {"fresh": 1, "projection_stale": 1},
        "stale_phase_ids_sample": ["09_35"],
        "stale_projection_sample_paths": ["codex/ledger/09_35/work_ledger_index.json"],
        "compact_failure_class": "projection_stale_family_results",
        "recommended_owner_action": "./repo-python tools/meta/factory/work_ledger.py project --all",
        "owner_tool": "./repo-python tools/meta/factory/work_ledger.py project --all",
        "check_command": "./repo-python tools/meta/factory/work_ledger.py project --check --all",
        "recommended_next": "run ./repo-python tools/meta/factory/work_ledger.py project --all",
    }
