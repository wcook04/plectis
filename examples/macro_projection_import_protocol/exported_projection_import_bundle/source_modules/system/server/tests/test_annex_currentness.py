from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib import annex_currentness
from system.lib.annex_currentness import build_annex_currentness


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_annex_currentness_reads_digest_as_candidate_review_surface(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest.json",
        {
            "kind": "annex_sync_digest",
            "schema_version": "annex_sync_digest_v1",
            "generated_at": "2026-04-29T12:00:00+00:00",
            "mode": "sync",
            "annex_count": 2,
            "attention_slugs": ["moved"],
            "attention_count": 1,
            "stale_count": 1,
            "max_stale_days": 12,
            "stale_threshold_days": 7,
            "bucket_counts": {
                "drift_detected": 1,
                "unchanged": 1,
            },
            "sync": {
                "requested": True,
                "status": "ok",
                "requested_count": 1,
                "synced_count": 1,
                "failure_count": 0,
                "selected_slugs": ["moved"],
                "chunk": {"strategy": "rotating_chunk", "selected_count": 1},
            },
            "upstream_movers_top": [
                {"slug": "moved", "commit_count": 3, "status": "drift_detected"},
            ],
            "rows": [
                {
                    "slug": "moved",
                    "bucket": "drift_detected",
                    "status": "drift_detected",
                    "headline": "1 note target no longer resolves.",
                    "report_path": "annexes/moved/annex_sync_report.json",
                    "commit_count": 3,
                    "broken_target_count": 1,
                    "high_signal_change_count": 4,
                    "distillation_issue_count": 0,
                    "coverage_status": "curated",
                    "stale_days": 12,
                    "repair_actions": ["repair_broken_targets"],
                },
                {
                    "slug": "quiet",
                    "bucket": "unchanged",
                    "status": "unchanged",
                    "headline": "No upstream changes.",
                    "report_path": "annexes/quiet/annex_sync_report.json",
                    "commit_count": 0,
                    "broken_target_count": 0,
                    "high_signal_change_count": 0,
                    "distillation_issue_count": 0,
                    "coverage_status": "curated",
                    "stale_days": 0,
                },
            ],
        },
    )
    _write_json(
        tmp_path / "annexes" / "moved" / "annex_sync_report.json",
        {
            "kind": "annex_sync_report",
            "schema_version": "annex_sync_report_v1",
            "slug": "moved",
            "mode": "sync",
            "generated_at": "2026-04-29T12:04:00+00:00",
            "source": {"changed": True, "commit_count": 3},
            "annotation_alignment": {
                "broken_target_count": 1,
                "high_signal_change_count": 4,
            },
            "summary": {"status": "drift_detected"},
        },
    )
    _write_json(
        tmp_path / "annexes" / "annex_catalog.json",
        {"kind": "annex_catalog", "schema_version": "annex_catalog_v1", "generated_at": "2026-04-29T12:06:00+00:00"},
    )
    _write_json(
        tmp_path / "annexes" / "annex_distillation_index.json",
        {
            "kind": "annex_distillation_index",
            "schema_version": "annex_distillation_index_v1",
            "generated_at": "2026-04-29T12:06:00+00:00",
        },
    )
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest_run_state.json",
        {
            "schema_version": "annex_sync_digest_run_state_v1",
            "updated_at": "2026-04-29T12:05:00+00:00",
            "last_selected_slug": "moved",
            "selected_slugs": ["moved"],
            "available_count": 2,
            "limit": 1,
        },
    )

    payload = build_annex_currentness(tmp_path, context_budget=12000, stale_threshold_days=7)

    assert payload["kind"] == "annex_currentness"
    assert payload["summary"]["digest_status"] == "attention_needed"
    assert payload["summary"]["attention_count"] == 1
    assert payload["summary"]["stale_count"] == 1
    assert payload["summary"]["currentness_debt"] == 2
    assert payload["summary"]["refresh_actuator_status"] == "bounded_refresh_recorded"
    assert payload["summary"]["projection_freshness_status"] == "current"
    assert payload["summary"]["movement_to_row_job_status"] == "ready"
    assert payload["source"]["reused_existing_infra"] is True
    assert payload["refresh_actuator"]["selected_slugs"] == ["moved"]
    assert payload["refresh_actuator"]["selected_report_receipt_count"] == 1
    assert payload["refresh_actuator"]["selected_reports_source_changed_count"] == 1
    assert payload["refresh_actuator"]["run_state"]["last_selected_slug"] == "moved"
    assert payload["projection_freshness"]["status"] == "current"
    assert payload["movement_to_row_job"]["candidate_row_job_count"] == 1
    assert payload["currentness_contract"]["pattern_rows_are"].startswith("relevance indexes")
    assert payload["currentness_contract"]["movement_policy"].startswith("upstream movement creates candidate")
    assert payload["top_attention_rows"][0]["slug"] == "moved"
    assert payload["candidate_review_work"][0]["next"] == "repair notes before mining"
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "annex_currentness:sync_digest:attention" in debt_ids
    assert "annex_currentness:sync_digest:stale" in debt_ids


def test_annex_currentness_does_not_bless_overwritten_sync_receipt(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest.json",
        {
            "kind": "annex_sync_digest",
            "schema_version": "annex_sync_digest_v1",
            "generated_at": "2026-04-29T12:00:00+00:00",
            "mode": "sync",
            "annex_count": 1,
            "attention_slugs": [],
            "attention_count": 0,
            "stale_count": 1,
            "max_stale_days": 12,
            "stale_threshold_days": 7,
            "bucket_counts": {"unchanged": 1},
            "sync": {
                "requested": True,
                "status": "ok",
                "requested_count": 1,
                "synced_count": 1,
                "failure_count": 0,
                "selected_slugs": ["moved"],
            },
            "rows": [
                {
                    "slug": "moved",
                    "bucket": "unchanged",
                    "status": "unchanged",
                    "headline": "No upstream changes.",
                    "report_path": "annexes/moved/annex_sync_report.json",
                    "commit_count": 0,
                    "broken_target_count": 0,
                    "high_signal_change_count": 0,
                    "distillation_issue_count": 0,
                    "coverage_status": "curated",
                    "stale_days": 12,
                },
            ],
        },
    )
    _write_json(
        tmp_path / "annexes" / "moved" / "annex_sync_report.json",
        {
            "kind": "annex_sync_report",
            "schema_version": "annex_sync_report_v1",
            "slug": "moved",
            "mode": "validate",
            "generated_at": "2026-04-29T12:07:00+00:00",
            "source": {"changed": False, "commit_count": 0},
            "annotation_alignment": {},
            "summary": {"status": "unchanged"},
        },
    )
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest_run_state.json",
        {
            "schema_version": "annex_sync_digest_run_state_v1",
            "updated_at": "2026-04-29T12:05:00+00:00",
            "last_selected_slug": "moved",
            "selected_slugs": ["moved"],
            "available_count": 1,
            "limit": 1,
        },
    )

    payload = build_annex_currentness(tmp_path, context_budget=12000, stale_threshold_days=7)

    assert payload["summary"]["refresh_actuator_status"] == "bounded_refresh_unverified"
    assert payload["refresh_actuator"]["expected_report_receipt_count"] == 1
    assert payload["refresh_actuator"]["selected_reports_sync_mode_count"] == 0
    assert payload["refresh_actuator"]["selected_reports_verified_sync_count"] == 0
    assert payload["refresh_actuator"]["selected_reports_unverified_count"] == 1
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "annex_currentness:refresh_actuator:unverified_sync_receipt" in debt_ids


def test_annex_currentness_uses_run_state_sync_receipt_after_validate_overwrite(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest.json",
        {
            "kind": "annex_sync_digest",
            "schema_version": "annex_sync_digest_v1",
            "generated_at": "2026-04-29T12:00:00+00:00",
            "mode": "sync",
            "annex_count": 1,
            "attention_slugs": [],
            "attention_count": 0,
            "stale_count": 0,
            "max_stale_days": 0,
            "stale_threshold_days": 7,
            "bucket_counts": {"unchanged": 1},
            "sync": {
                "requested": True,
                "status": "ok",
                "requested_count": 1,
                "synced_count": 1,
                "failure_count": 0,
                "selected_slugs": ["moved"],
            },
            "rows": [
                {
                    "slug": "moved",
                    "bucket": "unchanged",
                    "status": "unchanged",
                    "headline": "No upstream changes.",
                    "report_path": "annexes/moved/annex_sync_report.json",
                    "commit_count": 0,
                    "broken_target_count": 0,
                    "high_signal_change_count": 0,
                    "distillation_issue_count": 0,
                    "coverage_status": "curated",
                    "stale_days": 0,
                },
            ],
        },
    )
    _write_json(
        tmp_path / "annexes" / "moved" / "annex_sync_report.json",
        {
            "kind": "annex_sync_report",
            "schema_version": "annex_sync_report_v1",
            "slug": "moved",
            "mode": "validate",
            "generated_at": "2026-04-29T12:07:00+00:00",
            "source": {"changed": False, "commit_count": 0},
            "annotation_alignment": {"high_signal_change_count": 0, "broken_target_count": 0},
            "summary": {"status": "unchanged"},
        },
    )
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest_run_state.json",
        {
            "schema_version": "annex_sync_digest_run_state_v1",
            "updated_at": "2026-04-29T12:05:00+00:00",
            "last_selected_slug": "moved",
            "selected_slugs": ["moved"],
            "available_count": 1,
            "limit": 1,
            "selected_sync_receipts": [
                {
                    "slug": "moved",
                    "report_path": "annexes/moved/annex_sync_report.json",
                    "report_mode": "sync",
                    "report_generated_at": "2026-04-29T12:04:30+00:00",
                    "report_status": "unchanged",
                    "source_changed": False,
                    "commit_count": 0,
                    "high_signal_change_count": 0,
                    "broken_target_count": 0,
                }
            ],
        },
    )

    payload = build_annex_currentness(tmp_path, context_budget=12000, stale_threshold_days=7)

    assert payload["summary"]["refresh_actuator_status"] == "bounded_refresh_recorded"
    assert payload["refresh_actuator"]["selected_reports_sync_mode_count"] == 0
    assert payload["refresh_actuator"]["selected_reports_verified_sync_count"] == 1
    assert payload["refresh_actuator"]["selected_run_state_sync_receipt_count"] == 1
    assert payload["refresh_actuator"]["selected_run_state_verified_sync_count"] == 1
    assert payload["refresh_actuator"]["selected_reports_unverified_count"] == 0
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "annex_currentness:refresh_actuator:unverified_sync_receipt" not in debt_ids


def test_annex_currentness_excludes_missing_clone_rows_from_stale_queue(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest.json",
        {
            "kind": "annex_sync_digest",
            "schema_version": "annex_sync_digest_v1",
            "generated_at": "2026-04-29T12:00:00+00:00",
            "mode": "sync",
            "annex_count": 1,
            "attention_slugs": [],
            "attention_count": 0,
            "stale_count": 0,
            "max_stale_days": 0,
            "stale_threshold_days": 7,
            "bucket_counts": {"missing_clone": 1},
            "sync": {
                "requested": True,
                "status": "ok",
                "requested_count": 0,
                "synced_count": 0,
                "failure_count": 0,
                "selected_slugs": [],
            },
            "rows": [
                {
                    "slug": "missing",
                    "bucket": "missing_clone",
                    "status": "missing_clone",
                    "headline": "Registered annex without a local clone.",
                    "report_path": None,
                    "commit_count": 0,
                    "broken_target_count": 0,
                    "high_signal_change_count": 0,
                    "distillation_issue_count": 0,
                    "coverage_status": None,
                    "stale_days": 12,
                },
            ],
        },
    )

    payload = build_annex_currentness(tmp_path, context_budget=12000, stale_threshold_days=7)

    assert payload["summary"]["stale_count"] == 0
    assert payload["stale_rows"] == []
    assert payload["top_attention_rows"] == []
    assert payload["candidate_review_work"] == []
    assert payload["refresh_actuator"]["stale_queue_count"] == 0
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "annex_currentness:sync_digest:stale" not in debt_ids


def test_annex_currentness_marks_projection_freshness_debt(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest.json",
        {
            "kind": "annex_sync_digest",
            "schema_version": "annex_sync_digest_v1",
            "generated_at": "2026-04-29T12:00:00+00:00",
            "mode": "sync",
            "annex_count": 1,
            "attention_slugs": [],
            "attention_count": 0,
            "stale_count": 0,
            "max_stale_days": 0,
            "bucket_counts": {"unchanged": 1},
            "sync": {
                "requested": True,
                "status": "ok",
                "requested_count": 1,
                "synced_count": 1,
                "failure_count": 0,
                "failures": [],
                "selected_slugs": ["moved"],
            },
            "rows": [
                {
                    "slug": "moved",
                    "bucket": "unchanged",
                    "status": "unchanged",
                    "headline": "No upstream changes.",
                    "report_path": "annexes/moved/annex_sync_report.json",
                    "commit_count": 0,
                    "broken_target_count": 0,
                    "high_signal_change_count": 0,
                    "distillation_issue_count": 0,
                    "stale_days": 0,
                },
            ],
        },
    )
    _write_json(
        tmp_path / "annexes" / "annex_catalog.json",
        {"kind": "annex_catalog", "schema_version": "annex_catalog_v1", "generated_at": "2026-04-29T11:00:00+00:00"},
    )
    _write_json(
        tmp_path / "annexes" / "annex_distillation_index.json",
        {
            "kind": "annex_distillation_index",
            "schema_version": "annex_distillation_index_v1",
            "generated_at": "2026-04-29T11:00:00+00:00",
        },
    )
    _write_json(
        tmp_path / "annexes" / "moved" / "annex_sync_report.json",
        {
            "kind": "annex_sync_report",
            "schema_version": "annex_sync_report_v1",
            "slug": "moved",
            "mode": "sync",
            "generated_at": "2026-04-29T12:04:00+00:00",
            "source": {"changed": False, "commit_count": 0},
            "annotation_alignment": {},
            "summary": {"status": "unchanged"},
        },
    )

    payload = build_annex_currentness(tmp_path, context_budget=12000, stale_threshold_days=7)

    assert payload["summary"]["projection_freshness_status"] == "stale"
    assert payload["summary"]["projection_currentness_debt"] == 2
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "annex_currentness:projection_freshness:catalog_stale" in debt_ids
    assert "annex_currentness:projection_freshness:distillation_index_stale" in debt_ids


def test_annex_currentness_validate_report_does_not_stale_projections(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest.json",
        {
            "kind": "annex_sync_digest",
            "schema_version": "annex_sync_digest_v1",
            "generated_at": "2026-04-29T12:00:00+00:00",
            "mode": "sync",
            "annex_count": 1,
            "attention_slugs": [],
            "attention_count": 0,
            "stale_count": 0,
            "max_stale_days": 0,
            "bucket_counts": {"unchanged": 1},
            "sync": {
                "requested": True,
                "status": "ok",
                "requested_count": 1,
                "synced_count": 1,
                "failure_count": 0,
                "selected_slugs": ["moved"],
            },
            "rows": [
                {
                    "slug": "moved",
                    "bucket": "unchanged",
                    "status": "unchanged",
                    "headline": "No upstream changes.",
                    "report_path": "annexes/moved/annex_sync_report.json",
                    "commit_count": 0,
                    "broken_target_count": 0,
                    "high_signal_change_count": 0,
                    "distillation_issue_count": 0,
                    "stale_days": 0,
                },
            ],
        },
    )
    _write_json(
        tmp_path / "annexes" / "annex_catalog.json",
        {"kind": "annex_catalog", "schema_version": "annex_catalog_v1", "generated_at": "2026-04-29T12:06:00+00:00"},
    )
    _write_json(
        tmp_path / "annexes" / "annex_distillation_index.json",
        {
            "kind": "annex_distillation_index",
            "schema_version": "annex_distillation_index_v1",
            "generated_at": "2026-04-29T12:06:00+00:00",
        },
    )
    _write_json(
        tmp_path / "annexes" / "moved" / "annex_sync_report.json",
        {
            "kind": "annex_sync_report",
            "schema_version": "annex_sync_report_v1",
            "slug": "moved",
            "mode": "validate",
            "generated_at": "2026-04-29T12:07:00+00:00",
            "source": {"changed": False, "commit_count": 0},
            "annotation_alignment": {},
            "summary": {"status": "unchanged"},
        },
    )

    payload = build_annex_currentness(tmp_path, context_budget=12000, stale_threshold_days=7)

    assert payload["summary"]["projection_freshness_status"] == "current"
    assert payload["summary"]["projection_currentness_debt"] == 0
    assert payload["projection_freshness"]["source_mtimes"]["newest_projection_relevant_sync_report"]["exists"] is False
    assert payload["projection_freshness"]["source_mtimes"]["newest_projection_relevant_sync_report"]["skipped_report_modes"] == {
        "validate": 1,
    }
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "annex_currentness:projection_freshness:catalog_stale" not in debt_ids
    assert "annex_currentness:projection_freshness:distillation_index_stale" not in debt_ids


def test_annex_currentness_can_defer_projection_freshness_for_quick_profiles(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "annexes" / "annex_sync_digest.json",
        {
            "kind": "annex_sync_digest",
            "schema_version": "annex_sync_digest_v1",
            "generated_at": "2026-04-29T12:00:00+00:00",
            "mode": "sync",
            "annex_count": 1,
            "attention_slugs": [],
            "attention_count": 0,
            "stale_count": 1,
            "max_stale_days": 14,
            "bucket_counts": {"unchanged": 1},
            "sync": {"requested": True, "status": "ok", "failure_count": 0},
            "rows": [
                {
                    "slug": "slow",
                    "bucket": "unchanged",
                    "status": "unchanged",
                    "report_path": "annexes/slow/annex_sync_report.json",
                    "stale_days": 14,
                },
            ],
        },
    )

    def fail_report_scan(_repo_root):
        raise AssertionError("quick profile must not scan per-annex report JSON")

    original_load_json = annex_currentness._load_json

    def guarded_load_json(path):
        if path.name in {"annex_catalog.json", "annex_distillation_index.json"}:
            raise AssertionError("quick profile must not load large projection JSON")
        return original_load_json(path)

    monkeypatch.setattr(annex_currentness, "_newest_annex_sync_report_metadata", fail_report_scan)
    monkeypatch.setattr(annex_currentness, "_load_json", guarded_load_json)

    payload = annex_currentness.build_annex_currentness(
        tmp_path,
        context_budget=12000,
        stale_threshold_days=7,
        include_projection_freshness=False,
    )

    assert payload["summary"]["digest_status"] == "attention_needed"
    assert payload["summary"]["currentness_debt"] == 1
    assert payload["summary"]["projection_freshness_status"] == "deferred_by_quick_profile"
    assert payload["summary"]["projection_currentness_debt"] == 0
    assert payload["summary"]["projection_freshness_deferred"] is True
    assert payload["projection_freshness"]["drilldown_command"] == (
        "./repo-python kernel.py --annex-currentness --context-budget 12000"
    )
    debt_ids = {row["debt_id"] for row in payload["debt_rows"]}
    assert "annex_currentness:sync_digest:stale" in debt_ids
    assert not any(debt_id.startswith("annex_currentness:projection_freshness:") for debt_id in debt_ids)


def test_annex_currentness_missing_digest_emits_currentness_debt(tmp_path: Path) -> None:
    payload = build_annex_currentness(tmp_path, context_budget=12000)

    assert payload["summary"]["digest_status"] == "missing_digest"
    assert payload["summary"]["currentness_debt"] == 1
    assert payload["debt_rows"][0]["debt_class"] == "annex_currentness_debt"
    assert payload["debt_rows"][0]["repair_class"] == "refresh_annex_sync_digest"


def test_kernel_annex_currentness_cli_emits_packet() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--annex-currentness", "--context-budget", "12000"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr[:500]
    payload = json.loads(result.stdout)
    assert payload["kind"] == "annex_currentness"
    assert "currentness_debt" in payload["summary"]
    assert payload["source"]["digest_json"] == "annexes/annex_sync_digest.json"
