from __future__ import annotations

import json

import tools.meta.control.generated_state_drainer as generated_state_drainer_cli


def test_status_compact_uses_fast_settlement_plan_by_default(monkeypatch, capsys) -> None:
    def fail_full_status(*args, **kwargs):
        raise AssertionError("compact status should not run owner freshness checks by default")

    def fake_fast_plan(repo_root, owner_ids=None):
        assert owner_ids == ["task_ledger_projection"]
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "planning_mode": "cached_git_status",
            "authority_level": "cached_status_only",
            "full_authority_command": (
                "./repo-python tools/meta/control/generated_state_drainer.py "
                "settlement-plan --full-diff-stat"
            ),
            "supported_owner_ids": [
                "task_ledger_projection",
                "work_ledger_index_projection",
            ],
            "dirty_owner_count": 1,
            "refresh_required_owner_count": 0,
            "blocked_owner_count": 0,
            "owners": [
                {
                    "owner_id": "task_ledger_projection",
                    "status": "append_exempt_manifest_available",
                    "freshness_status": "not_checked_cached_status_only",
                    "dirty_status": "dirty",
                    "source_dirty_status": "dirty",
                    "can_apply": True,
                    "blocked_by": [],
                    "required_action": "land_append_exempt",
                    "required_next_command": (
                        "./repo-python tools/meta/control/generated_state_drainer.py "
                        "settle --dry-run"
                    ),
                    "path_count": 2,
                    "diff_stat": {
                        "stat_mode": "status_only",
                        "paths": [
                            {
                                "path": "state/task_ledger/ledger.json",
                                "dirty_status": "modified",
                            },
                            {
                                "path": "state/task_ledger/views/recent_events.json",
                                "dirty_status": "clean",
                            },
                        ],
                    },
                    "path_bundle": {
                        "projection_paths": [
                            "state/task_ledger/ledger.json",
                            "state/task_ledger/views/recent_events.json",
                        ],
                        "projection_paths_to_stage": [
                            "state/task_ledger/ledger.json",
                        ],
                        "dirty_path_summary": {
                            "projection_dirty_count": 1,
                            "projection_clean_count": 1,
                        },
                    },
                    "planning_mode": "cached_git_status",
                }
            ],
        }

    monkeypatch.setattr(generated_state_drainer_cli, "build_generated_state_drainer_status", fail_full_status)
    monkeypatch.setattr(
        generated_state_drainer_cli,
        "build_generated_projection_settlement_fast_plan",
        fake_fast_plan,
    )

    exit_code = generated_state_drainer_cli.main(
        ["status", "--owner-id", "task_ledger_projection", "--compact"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_state_drainer_status_compact_v0"
    assert payload["planning_mode"] == "cached_git_status"
    assert payload["authority_level"] == "cached_status_only"
    assert payload["summary"]["dirty_owner_count"] == 1
    assert payload["counts"]["owner_check_count"] == 0
    assert payload["counts"]["dirty_generated_path_count"] == 1
    assert payload["counts"]["recommended_owner_action"] == {
        "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run": 1,
        "none": 1,
    }
    assert payload["owner_checks"] == {}
    assert payload["owner_actions"][0]["required_action"] == "land_append_exempt"
    assert payload["dirty_generated_paths_sample"] == [
        {
            "generated_path": "state/task_ledger/ledger.json",
            "owner_id": "task_ledger_projection",
            "freshness_status": "not_checked_cached_status_only",
            "dirty_status": "modified",
            "recommended_owner_action": (
                "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
            ),
            "check_command": (
                "./repo-python tools/meta/control/generated_state_drainer.py "
                "settlement-plan --full-diff-stat"
            ),
            "owner_tool": (
                "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
            ),
        }
    ]
    assert payload["fast_status_receipt"]["status"] == "cached_git_status_only"
    assert payload["drilldown"]["full_status_command"] == (
        "./repo-python tools/meta/control/generated_state_drainer.py "
        "status --owner-id task_ledger_projection --compact --full-authority"
    )


def test_status_compact_fast_mode_bounds_path_samples(monkeypatch, capsys) -> None:
    projection_paths = [
        f"state/task_ledger/views/generated_{index}.json"
        for index in range(8)
    ]

    def fake_fast_plan(repo_root, owner_ids=None):
        assert owner_ids == ["task_ledger_projection"]
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "planning_mode": "cached_git_status",
            "authority_level": "cached_status_only",
            "full_authority_command": (
                "./repo-python tools/meta/control/generated_state_drainer.py "
                "settlement-plan --full-diff-stat"
            ),
            "supported_owner_ids": ["task_ledger_projection"],
            "dirty_owner_count": 1,
            "refresh_required_owner_count": 0,
            "blocked_owner_count": 0,
            "owners": [
                {
                    "owner_id": "task_ledger_projection",
                    "status": "append_exempt_manifest_available",
                    "freshness_status": "not_checked_cached_status_only",
                    "dirty_status": "dirty",
                    "source_dirty_status": "dirty",
                    "can_apply": True,
                    "blocked_by": [],
                    "required_action": "land_append_exempt",
                    "required_next_command": (
                        "./repo-python tools/meta/control/generated_state_drainer.py "
                        "settle --dry-run"
                    ),
                    "path_count": len(projection_paths),
                    "diff_stat": {
                        "stat_mode": "status_only",
                        "paths": [
                            {"path": path, "dirty_status": "modified"}
                            for path in projection_paths
                        ],
                    },
                    "path_bundle": {
                        "projection_paths": projection_paths,
                        "projection_paths_to_stage": projection_paths,
                        "dirty_path_summary": {
                            "projection_dirty_count": len(projection_paths),
                        },
                    },
                    "planning_mode": "cached_git_status",
                }
            ],
        }

    monkeypatch.setattr(
        generated_state_drainer_cli,
        "build_generated_projection_settlement_fast_plan",
        fake_fast_plan,
    )

    exit_code = generated_state_drainer_cli.main(
        ["status", "--owner-id", "task_ledger_projection", "--compact"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [
        row["generated_path"] for row in payload["dirty_generated_paths_sample"]
    ] == projection_paths[:6]
    assert payload["projection_groups"][0]["dirty_or_stale_sample_paths"] == projection_paths[:3]
    assert payload["compact_sampling_receipt"] == {
        "status": "path_samples_bounded",
        "dirty_generated_paths_sample_limit": 6,
        "dirty_generated_paths_omitted_count": 2,
        "projection_group_sample_limit": 3,
        "projection_group_sample_fields": [
            "dirty_or_stale_sample_paths",
            "clean_recommended_action_sample_paths",
        ],
    }


def test_apply_compact_omits_full_status_and_projection_rows(monkeypatch, capsys) -> None:
    def fake_apply(repo_root, only=None, dry_run=False):
        assert only == "task_ledger_projection_refresh"
        assert dry_run is False
        return {
            "schema": "generated_state_drainer_apply_v0",
            "ok": True,
            "dry_run": False,
            "status": "applied",
            "action": {
                "action_id": "task_ledger_projection_refresh",
                "owner_id": "task_ledger_projection",
            },
            "projection_result": {
                "ok": True,
                "checked": True,
                "mode": "all",
                "event_count": 14568,
                "projection_paths": [
                    "state/task_ledger/ledger.json",
                    "state/task_ledger/views/recent_events.json",
                    "state/task_ledger/views/ready_by_rank.json",
                ],
                "families": [
                    {"family_id": "task_ledger_views"},
                    {"family_id": "task_ledger_rollups"},
                ],
            },
            "before": {
                "summary": {"dirty_generated_path_count": 3},
                "owner_checks": {"task_ledger_projection": {"rows": ["large"]}},
            },
            "after": {
                "summary": {"dirty_generated_path_count": 0},
                "owner_checks": {"task_ledger_projection": {"rows": ["large"]}},
            },
        }

    monkeypatch.setattr(generated_state_drainer_cli, "apply_generated_state_drainer", fake_apply)

    exit_code = generated_state_drainer_cli.main(
        ["apply", "--only", "task_ledger_projection_refresh", "--compact"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_state_drainer_apply_compact_v0"
    assert payload["source_schema"] == "generated_state_drainer_apply_v0"
    assert payload["status"] == "applied"
    assert payload["projection_result_summary"]["projection_path_count"] == 3
    assert payload["projection_result_summary"]["family_count"] == 2
    assert payload["before_summary"] == {"dirty_generated_path_count": 3}
    assert payload["after_summary"] == {"dirty_generated_path_count": 0}
    assert payload["omission_receipt"]["status"] == "apply_payload_compacted"
    assert payload["omission_receipt"]["full_result_command"].endswith(
        "apply --only task_ledger_projection_refresh"
    )
    assert "before" not in payload
    assert "after" not in payload
    assert "projection_result" not in payload
    assert "large" not in json.dumps(payload)


def test_apply_compact_dry_run_skips_full_freshness_check(monkeypatch, capsys) -> None:
    def fail_apply(*args, **kwargs):
        raise AssertionError("compact dry-run should not build full owner status")

    monkeypatch.setattr(generated_state_drainer_cli, "apply_generated_state_drainer", fail_apply)

    exit_code = generated_state_drainer_cli.main(
        ["apply", "--only", "task_ledger_projection_refresh", "--dry-run", "--compact"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_state_drainer_apply_compact_v0"
    assert payload["status"] == "dry_run_planned_fast_compact"
    assert payload["freshness_status"] == "not_checked_fast_compact_dry_run"
    assert payload["action"]["owner_id"] == "task_ledger_projection"
    assert payload["action"]["would_mutate"] == "not_checked_fast_compact_dry_run"
    assert payload["omission_receipt"]["status"] == "full_owner_freshness_check_omitted"
    assert payload["omission_receipt"]["full_result_command"].endswith(
        "apply --only task_ledger_projection_refresh --dry-run"
    )
    assert "before" not in payload
    assert "owner_checks" not in payload


def test_settlement_plan_compact_omits_owner_path_lists(monkeypatch, capsys) -> None:
    def fake_fast_plan(repo_root, owner_ids=None):
        assert owner_ids == ["task_ledger_projection"]
        return {
            "schema": "generated_projection_settlement_plan_v0",
            "ok": True,
            "status": "settlement_required",
            "planning_mode": "cached_git_status",
            "authority_level": "cached_status_only",
            "supported_owner_ids": ["task_ledger_projection"],
            "settlement_order": ["task_ledger_projection"],
            "dirty_owner_count": 1,
            "refresh_required_owner_count": 0,
            "blocked_owner_count": 0,
            "can_settle": True,
            "blocked_by": [],
            "required_next_command": (
                "./repo-python tools/meta/control/generated_state_drainer.py "
                "settle --dry-run --fast-plan"
            ),
            "eventful_closeout_allowed_after_settlement": False,
            "normal_source_event_after_refresh_allowed": False,
            "owners": [
                {
                    "owner_id": "task_ledger_projection",
                    "status": "append_exempt_manifest_available",
                    "freshness_status": "not_checked_cached_status_only",
                    "dirty_status": "dirty",
                    "source_dirty_status": "dirty",
                    "can_apply": True,
                    "blocked_by": [],
                    "required_action": "land_append_exempt",
                    "required_next_command": (
                        "./repo-python tools/meta/control/generated_state_drainer.py "
                        "settle --dry-run"
                    ),
                    "landing_manifest_path": (
                        "state/generated_projection_landing/task_ledger_projection_manifest.json"
                    ),
                    "path_count": 2,
                    "diff_stat": {
                        "stat_mode": "status_only",
                        "path_count": 2,
                        "dirty_path_count": 1,
                        "paths": [{"path": "state/task_ledger/ledger.json"}],
                    },
                    "path_bundle": {
                        "source_authority_paths": ["state/task_ledger/events.jsonl"],
                        "projection_paths": ["state/task_ledger/ledger.json"],
                        "projection_paths_to_stage": ["state/task_ledger/ledger.json"],
                        "dirty_path_summary": {
                            "source_authority_dirty_count": 1,
                            "projection_dirty_count": 1,
                        },
                    },
                    "projection_hashes": {"state/task_ledger/ledger.json": "sha256:test"},
                    "planning_mode": "cached_git_status",
                }
            ],
        }

    monkeypatch.setattr(
        generated_state_drainer_cli,
        "build_generated_projection_settlement_fast_plan",
        fake_fast_plan,
    )

    exit_code = generated_state_drainer_cli.main(
        [
            "settlement-plan",
            "--fast",
            "--owner-id",
            "task_ledger_projection",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_projection_settlement_plan_compact_v0"
    assert payload["owners"] == [
        {
            "owner_id": "task_ledger_projection",
            "status": "append_exempt_manifest_available",
            "freshness_status": "not_checked_cached_status_only",
            "dirty_status": "dirty",
            "source_dirty_status": "dirty",
            "can_apply": True,
            "blocked_by": [],
            "required_action": "land_append_exempt",
            "required_next_command": (
                "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
            ),
            "landing_manifest_path": (
                "state/generated_projection_landing/task_ledger_projection_manifest.json"
            ),
            "path_count": 2,
            "dirty_path_summary": {
                "source_authority_dirty_count": 1,
                "projection_dirty_count": 1,
            },
            "diff_stat": {
                "path_count": 2,
                "dirty_path_count": 1,
                "stat_mode": "status_only",
            },
            "planning_mode": "cached_git_status",
        }
    ]
    assert payload["omission_receipt"]["status"] == "path_lists_and_hashes_omitted"
    assert "state/task_ledger/ledger.json" not in json.dumps(payload["owners"])
    assert payload["compact_plan_command"].endswith("settlement-plan --fast")
    assert payload["full_plan_command"].endswith("settlement-plan --fast --full-output")

    exit_code = generated_state_drainer_cli.main(
        [
            "settlement-plan",
            "--fast",
            "--full-output",
            "--owner-id",
            "task_ledger_projection",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_projection_settlement_plan_v0"
    assert payload["owners"][0]["path_bundle"]["projection_paths"] == [
        "state/task_ledger/ledger.json"
    ]


def test_settle_compact_omits_full_owner_path_bundles(monkeypatch, capsys) -> None:
    def fake_settle(
        repo_root,
        owner_ids=None,
        dry_run=False,
        max_passes=3,
        fast_plan=False,
        bounded_final_plan=False,
        work_ledger_session_id=None,
        progress_callback=None,
    ):
        assert owner_ids == ["task_ledger_projection"]
        assert dry_run is True
        assert fast_plan is True
        assert bounded_final_plan is False
        assert max_passes == 3
        assert work_ledger_session_id is None
        assert progress_callback is not None
        return {
            "schema": "generated_projection_settlement_v0",
            "ok": True,
            "dry_run": True,
            "status": "would_settle",
            "pass_count": 1,
            "max_passes": 3,
            "progress": {"commit_count": 0, "landed_count": 0},
            "owners": [
                {
                    "pass_index": 1,
                    "owner_id": "task_ledger_projection",
                    "before_status": "append_exempt_manifest_available",
                    "required_action": "land_append_exempt",
                    "result_status": "would_land",
                    "ok": True,
                    "commit_hash": None,
                    "paths_to_stage": [
                        "state/generated_projection_landing/task_ledger_projection_manifest.json",
                        "state/task_ledger/events.jsonl",
                        "state/task_ledger/events_audit.jsonl",
                        "state/task_ledger/ledger.json",
                        "state/task_ledger/views/recent_events.json",
                        "state/task_ledger/views/ready_by_rank.json",
                        "state/task_ledger/views/incomplete_work_items.json",
                    ],
                    "source_authority_paths": [
                        "state/task_ledger/events.jsonl",
                        "state/task_ledger/events_audit.jsonl",
                    ],
                    "projection_paths": [
                        "state/task_ledger/ledger.json",
                        "state/task_ledger/views/recent_events.json",
                    ],
                    "path_bundle": {
                        "projection_paths_to_stage": [
                            "state/task_ledger/ledger.json",
                            "state/task_ledger/views/recent_events.json",
                        ],
                        "dirty_path_summary": {
                            "source_authority_dirty_count": 2,
                            "projection_dirty_count": 2,
                        },
                        "landing_manifest_path": (
                            "state/generated_projection_landing/task_ledger_projection_manifest.json"
                        ),
                    },
                    "owner_bundle_completeness": {
                        "source_authority_path_count": 2,
                        "source_authority_stage_path_count": 2,
                        "projection_path_count": 2,
                        "projection_stage_path_count": 2,
                        "landing_manifest_included": True,
                        "all_expected_stage_paths_reported": True,
                        "missing_expected_stage_paths": [],
                        "task_ledger_audit_journal_declared": True,
                    },
                    "landing_manifest_path": (
                        "state/generated_projection_landing/task_ledger_projection_manifest.json"
                    ),
                    "expected_path_count": 2,
                    "pass_reason": "initial_settlement_pass",
                }
            ],
            "residual_owners": [],
            "before_plan": {
                "schema": "generated_projection_settlement_plan_v0",
                "ok": True,
                "status": "settlement_required",
                "planning_mode": "cached_git_status",
                "authority_level": "cached_status_only",
                "supported_owner_ids": ["task_ledger_projection"],
                "settlement_order": ["task_ledger_projection"],
                "dirty_owner_count": 1,
                "refresh_required_owner_count": 0,
                "blocked_owner_count": 0,
                "can_settle": True,
                "blocked_by": [],
                "required_next_command": (
                    "./repo-python tools/meta/control/generated_state_drainer.py "
                    "settle --dry-run --fast-plan"
                ),
                "owners": [],
            },
            "stewardship_check": {
                "rule": "settlement_is_not_refinement",
                "checked_surfaces": ["source_bundle_coverage"],
                "source_bundle_by_owner": {
                    "task_ledger_projection": {
                        "source_authority_paths": [
                            "state/task_ledger/events.jsonl",
                            "state/task_ledger/events_audit.jsonl",
                        ],
                        "projection_paths": [
                            "state/task_ledger/ledger.json",
                            "state/task_ledger/views/recent_events.json",
                            "state/task_ledger/views/ready_by_rank.json",
                            "state/task_ledger/views/incomplete_work_items.json",
                            "state/task_ledger/views/missing_contracts_ranked.json",
                            "state/task_ledger/views/missing_satisfaction_contract.json",
                            "state/task_ledger/views/missing_integration_contract.json",
                        ],
                        "landing_manifest_path": (
                            "state/generated_projection_landing/task_ledger_projection_manifest.json"
                        ),
                    }
                },
                "lane_results": [],
                "reentry_conditions": [],
            },
            "settlement_done": False,
            "validation_done": False,
            "refinement_done": False,
            "settlement_is_not_refinement": True,
            "stewardship_checked": True,
            "next_best_lane_checked": True,
            "timing": {
                "schema": "generated_projection_settlement_timing_v0",
                "total_wall_ms": 4,
                "phases": [],
            },
        }

    monkeypatch.setenv(generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV, "1")
    monkeypatch.setattr(generated_state_drainer_cli, "settle_generated_projection_owners", fake_settle)

    exit_code = generated_state_drainer_cli.main(
        [
            "settle",
            "--dry-run",
            "--fast-plan",
            "--compact",
            "--owner-id",
            "task_ledger_projection",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_projection_settlement_compact_v0"
    assert payload["owners"][0]["paths_to_stage"]["count"] == 7
    assert payload["owners"][0]["paths_to_stage"]["omitted"] == 4
    assert payload["owners"][0]["owner_bundle_completeness"]["projection_path_count"] == 2
    assert payload["before_plan"]["schema"] == "generated_projection_settlement_plan_handle_v0"
    assert payload["stewardship_check"]["source_bundle_by_owner"]["task_ledger_projection"][
        "projection_paths"
    ] == {
        "count": 7,
        "preview": [
            "state/task_ledger/ledger.json",
            "state/task_ledger/views/recent_events.json",
            "state/task_ledger/views/ready_by_rank.json",
        ],
        "omitted": 4,
    }
    assert payload["omission_receipt"]["status"] == "settle_path_bundles_compacted"
    payload_text = json.dumps(payload)
    assert "path_bundle" not in payload["owners"][0]
    assert "source_bundle_by_owner" in payload_text


def test_settle_dry_run_fast_plan_compacts_by_default(monkeypatch, capsys) -> None:
    def fake_settle(
        repo_root,
        owner_ids=None,
        dry_run=False,
        max_passes=3,
        fast_plan=False,
        bounded_final_plan=False,
        work_ledger_session_id=None,
        progress_callback=None,
    ):
        assert owner_ids == ["task_ledger_projection"]
        assert dry_run is True
        assert fast_plan is True
        assert bounded_final_plan is False
        assert progress_callback is not None
        return {
            "schema": "generated_projection_settlement_v0",
            "ok": True,
            "dry_run": True,
            "status": "would_settle",
            "owners": [
                {
                    "owner_id": "task_ledger_projection",
                    "result_status": "would_land",
                    "paths_to_stage": [
                        "state/generated_projection_landing/task_ledger_projection_manifest.json",
                        "state/task_ledger/events.jsonl",
                        "state/task_ledger/ledger.json",
                        "state/task_ledger/views/recent_events.json",
                    ],
                    "path_bundle": {
                        "projection_paths_to_stage": [
                            "state/task_ledger/ledger.json",
                            "state/task_ledger/views/recent_events.json",
                        ],
                        "dirty_path_summary": {"projection_dirty_count": 2},
                        "landing_manifest_path": (
                            "state/generated_projection_landing/task_ledger_projection_manifest.json"
                        ),
                    },
                }
            ],
            "stewardship_check": {
                "source_bundle_by_owner": {
                    "task_ledger_projection": {
                        "projection_paths": [
                            "state/task_ledger/ledger.json",
                            "state/task_ledger/views/recent_events.json",
                            "state/task_ledger/views/ready_by_rank.json",
                            "state/task_ledger/views/incomplete_work_items.json",
                        ]
                    }
                }
            },
            "settlement_is_not_refinement": True,
            "stewardship_checked": True,
            "next_best_lane_checked": True,
        }

    monkeypatch.setenv(generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV, "1")
    monkeypatch.setattr(generated_state_drainer_cli, "settle_generated_projection_owners", fake_settle)

    exit_code = generated_state_drainer_cli.main(
        [
            "settle",
            "--dry-run",
            "--fast-plan",
            "--owner-id",
            "task_ledger_projection",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_projection_settlement_compact_v0"
    assert payload["owners"][0]["paths_to_stage"] == {
        "count": 4,
        "preview": [
            "state/generated_projection_landing/task_ledger_projection_manifest.json",
            "state/task_ledger/events.jsonl",
            "state/task_ledger/ledger.json",
        ],
        "omitted": 1,
    }
    assert "path_bundle" not in payload["owners"][0]
    assert payload["omission_receipt"]["full_result_command"].endswith(
        "settle --dry-run --fast-plan --full-output"
    )


def test_settle_dry_run_fast_plan_full_output_preserves_full_result(
    monkeypatch,
    capsys,
) -> None:
    def fake_settle(
        repo_root,
        owner_ids=None,
        dry_run=False,
        max_passes=3,
        fast_plan=False,
        bounded_final_plan=False,
        work_ledger_session_id=None,
        progress_callback=None,
    ):
        assert dry_run is True
        assert fast_plan is True
        return {
            "schema": "generated_projection_settlement_v0",
            "ok": True,
            "dry_run": True,
            "status": "would_settle",
            "owners": [
                {
                    "owner_id": "task_ledger_projection",
                    "paths_to_stage": ["state/task_ledger/ledger.json"],
                    "path_bundle": {
                        "projection_paths_to_stage": ["state/task_ledger/ledger.json"]
                    },
                }
            ],
        }

    monkeypatch.setenv(generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV, "1")
    monkeypatch.setattr(generated_state_drainer_cli, "settle_generated_projection_owners", fake_settle)

    exit_code = generated_state_drainer_cli.main(
        [
            "settle",
            "--dry-run",
            "--fast-plan",
            "--full-output",
            "--owner-id",
            "task_ledger_projection",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_projection_settlement_v0"
    assert payload["owners"][0]["path_bundle"]["projection_paths_to_stage"] == [
        "state/task_ledger/ledger.json"
    ]


def test_settle_compact_preserves_source_moved_partial_success(monkeypatch, capsys) -> None:
    def fake_settle(
        repo_root,
        owner_ids=None,
        dry_run=False,
        max_passes=3,
        fast_plan=False,
        bounded_final_plan=False,
        work_ledger_session_id=None,
        progress_callback=None,
    ):
        assert bounded_final_plan is True
        return {
            "schema": "generated_projection_settlement_v0",
            "ok": True,
            "dry_run": False,
            "status": "settlement_residual_source_moved",
            "reason": "source_authority_moved_during_settlement",
            "partial_success": True,
            "residual_class": "concurrent_source_authority_moved",
            "source_moved_owner_ids": ["task_ledger_projection"],
            "pass_count": 1,
            "max_passes": 3,
            "progress": {
                "commit_count": 1,
                "commit_hashes": ["commit-task"],
                "landed_count": 1,
            },
            "owners": [],
            "residual_owners": [
                {
                    "owner_id": "task_ledger_projection",
                    "status": "refresh_required",
                    "required_action": "refresh_then_land_append_exempt",
                }
            ],
            "before_plan": None,
            "settlement_done": False,
            "validation_done": False,
            "refinement_done": False,
            "settlement_is_not_refinement": True,
            "stewardship_checked": True,
            "next_best_lane_checked": True,
            "timing": {
                "schema": "generated_projection_settlement_timing_v0",
                "total_wall_ms": 4,
                "phases": [],
            },
        }

    monkeypatch.setenv(generated_state_drainer_cli.SETTLE_SINGLEFLIGHT_CHILD_ENV, "1")
    monkeypatch.setattr(generated_state_drainer_cli, "settle_generated_projection_owners", fake_settle)

    exit_code = generated_state_drainer_cli.main(["settle", "--compact"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["status"] == "settlement_residual_source_moved"
    assert payload["partial_success"] is True
    assert payload["residual_class"] == "concurrent_source_authority_moved"
    assert payload["source_moved_owner_ids"] == ["task_ledger_projection"]
    assert payload["settlement_done"] is False


def test_status_compact_full_authority_emits_counts_and_full_drilldown(monkeypatch, capsys) -> None:
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
        ["status", "--owner-id", "task_ledger_projection", "--compact", "--full-authority"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "generated_state_drainer_status_compact_v0"
    assert payload["summary"] == {"stale_count": 1, "dirty_count": 1}
    assert payload["counts"]["projection_target_count"] == 2
    assert payload["counts"]["freshness"] == {"fresh": 1, "projection_stale": 1}
    assert payload["counts"]["dirty_status"] == {"clean": 1, "dirty": 1}
    assert payload["actionability"]["schema"] == "generated_state_drainer_compact_actionability_v0"
    assert payload["actionability"]["status"] == "dirty_owner_action_required"
    assert payload["actionability"]["recommended_next"] == (
        "run the owner action for dirty generated paths before treating generated state as settled"
    )
    assert payload["actionability"]["dirty_recommended_action_count"] == 1
    assert payload["actionability"]["clean_recommended_action_count"] == 0
    assert payload["actionability"]["dirty_fresh_no_action_count"] == 0
    assert payload["actionability"]["clean_recommended_action_sample_paths"] == []
    assert payload["actionability"]["dirty_recommended_action_sample_paths"] == [
        "state/task_ledger/ledger.json"
    ]
    assert payload["actionability"]["mutation_guard"]["status"] == "claim_required_for_mutation"
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

    exit_code = generated_state_drainer_cli.main(["status", "--compact", "--full-authority"])

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
