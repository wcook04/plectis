"""
Read-only annex currentness packet over the existing sync digest substrate.

This module does not refresh or pull annexes. It exposes the current
annex_sync_digest.json state as a bounded navigation/metabolism surface so
agents can distinguish upstream movement from routing coverage or cluster
availability.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "annex_currentness_v0"
DEFAULT_STALE_THRESHOLD_DAYS = 7


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _iso_from_timestamp(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_timestamp(raw_value: Any) -> datetime | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _path_metadata(repo_root: Path, path: Path) -> dict[str, Any]:
    exists = path.exists()
    mtime = path.stat().st_mtime if exists else None
    generated_at = None
    schema_version = None
    if exists and path.suffix == ".json":
        payload = _load_json(path)
        if isinstance(payload, Mapping):
            generated_at = payload.get("generated_at") or payload.get("updated_at")
            schema_version = payload.get("schema_version")
    return {
        "path": _repo_rel(repo_root, path),
        "exists": exists,
        "mtime": _iso_from_timestamp(mtime),
        "mtime_epoch": mtime,
        "generated_at": generated_at,
        "schema_version": schema_version,
    }


def _path_stat_metadata(repo_root: Path, path: Path) -> dict[str, Any]:
    exists = path.exists()
    mtime = path.stat().st_mtime if exists else None
    size_bytes = path.stat().st_size if exists else None
    return {
        "path": _repo_rel(repo_root, path),
        "exists": exists,
        "mtime": _iso_from_timestamp(mtime),
        "mtime_epoch": mtime,
        "size_bytes": size_bytes,
        "generated_at": None,
        "schema_version": None,
        "metadata_mode": "stat_only",
    }


def _newest_path_metadata(repo_root: Path, patterns: Sequence[str]) -> dict[str, Any]:
    newest: Path | None = None
    newest_mtime: float | None = None
    count = 0
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            count += 1
            mtime = path.stat().st_mtime
            if newest_mtime is None or mtime > newest_mtime:
                newest = path
                newest_mtime = mtime
    if newest is None:
        return {
            "path": None,
            "exists": False,
            "count": count,
            "mtime": None,
            "mtime_epoch": None,
            "generated_at": None,
        }
    metadata = _path_metadata(repo_root, newest)
    metadata["count"] = count
    return metadata


def _newest_annex_sync_report_metadata(repo_root: Path) -> dict[str, Any]:
    newest: Path | None = None
    newest_mtime: float | None = None
    count = 0
    skipped_modes: dict[str, int] = {}
    for path in repo_root.glob("annexes/*/annex_sync_report.json"):
        if not path.is_file():
            continue
        report = _load_json(path)
        mode = str((report or {}).get("mode") or "").strip()
        if mode != "sync":
            skipped_modes[mode or "missing"] = skipped_modes.get(mode or "missing", 0) + 1
            continue
        count += 1
        mtime = path.stat().st_mtime
        if newest_mtime is None or mtime > newest_mtime:
            newest = path
            newest_mtime = mtime
    if newest is None:
        return {
            "path": None,
            "exists": False,
            "count": count,
            "mtime": None,
            "mtime_epoch": None,
            "generated_at": None,
            "report_mode_filter": "sync",
            "skipped_report_modes": skipped_modes,
        }
    metadata = _path_metadata(repo_root, newest)
    metadata["count"] = count
    metadata["report_mode_filter"] = "sync"
    metadata["skipped_report_modes"] = skipped_modes
    return metadata


def _is_newer(source: Mapping[str, Any], target: Mapping[str, Any], *, margin_seconds: float = 1.0) -> bool:
    source_mtime = source.get("mtime_epoch")
    target_mtime = target.get("mtime_epoch")
    if source_mtime is not None and target_mtime is not None:
        try:
            if float(source_mtime) > float(target_mtime) + margin_seconds:
                return True
        except (TypeError, ValueError):
            pass
    source_generated = _parse_iso_timestamp(source.get("generated_at"))
    target_generated = _parse_iso_timestamp(target.get("generated_at"))
    if source_generated is None or target_generated is None:
        return False
    return (source_generated - target_generated).total_seconds() > margin_seconds


def _seconds_between(later_iso: Any, earlier_iso: Any) -> float | None:
    later = _parse_iso_timestamp(later_iso)
    earlier = _parse_iso_timestamp(earlier_iso)
    if later is None or earlier is None:
        return None
    return (later - earlier).total_seconds()


def _trim(text: Any, *, max_chars: int = 180) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _compact_row(row: Mapping[str, Any]) -> dict[str, Any]:
    slug = str(row.get("slug") or "")
    report_path = str(row.get("report_path") or f"annexes/{slug}/annex_sync_report.json")
    return {
        "slug": slug,
        "bucket": str(row.get("bucket") or ""),
        "status": str(row.get("status") or ""),
        "headline": _trim(row.get("headline")),
        "report_path": report_path,
        "commit_count": _int(row.get("commit_count")),
        "broken_target_count": _int(row.get("broken_target_count")),
        "high_signal_change_count": _int(row.get("high_signal_change_count")),
        "distillation_issue_count": _int(row.get("distillation_issue_count")),
        "coverage_status": row.get("coverage_status"),
        "stale_days": row.get("stale_days"),
        "repair_actions": [str(item) for item in list(row.get("repair_actions") or [])[:4]],
    }


def _top_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    bucket_rank = {
        "error": 0,
        "drift_detected": 1,
        "review_needed": 2,
        "annotation_needed": 3,
        "unannotated": 4,
        "missing_clone": 5,
        "aligned": 6,
        "unchanged": 7,
    }
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            bucket_rank.get(str(row.get("bucket") or ""), 99),
            -_int(row.get("broken_target_count")),
            -_int(row.get("high_signal_change_count")),
            -_int(row.get("commit_count")),
            str(row.get("slug") or ""),
        ),
    )
    return [_compact_row(row) for row in sorted_rows[:limit]]


_ATTENTION_BUCKETS = {
    "error",
    "drift_detected",
    "review_needed",
    "annotation_needed",
    "unannotated",
}


def _high_signal_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    candidates = [
        row for row in rows
        if _int(row.get("high_signal_change_count")) > 0 or _int(row.get("commit_count")) > 0
    ]
    candidates.sort(
        key=lambda row: (
            -_int(row.get("high_signal_change_count")),
            -_int(row.get("commit_count")),
            str(row.get("slug") or ""),
        )
    )
    return [_compact_row(row) for row in candidates[:limit]]


def _selected_report_receipts(
    repo_root: Path,
    *,
    selected_slugs: Sequence[str],
    run_updated_at: Any,
    limit: int = 12,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for slug in [str(item) for item in selected_slugs if str(item or "").strip()][:limit]:
        report_path = repo_root / "annexes" / slug / "annex_sync_report.json"
        report = _load_json(report_path)
        metadata = _path_metadata(repo_root, report_path)
        source = report.get("source") if isinstance(report, Mapping) and isinstance(report.get("source"), Mapping) else {}
        summary = report.get("summary") if isinstance(report, Mapping) and isinstance(report.get("summary"), Mapping) else {}
        alignment = (
            report.get("annotation_alignment")
            if isinstance(report, Mapping) and isinstance(report.get("annotation_alignment"), Mapping)
            else {}
        )
        seconds_before_state = _seconds_between(run_updated_at, report.get("generated_at") if isinstance(report, Mapping) else None)
        receipts.append(
            {
                "slug": slug,
                "path": metadata.get("path"),
                "exists": bool(report),
                "mtime": metadata.get("mtime"),
                "generated_at": report.get("generated_at") if isinstance(report, Mapping) else None,
                "mode": report.get("mode") if isinstance(report, Mapping) else None,
                "status": summary.get("status"),
                "source_changed": bool(source.get("changed")),
                "commit_count": _int(source.get("commit_count")),
                "high_signal_change_count": _int(alignment.get("high_signal_change_count")),
                "broken_target_count": _int(alignment.get("broken_target_count")),
                "near_run_state": (
                    seconds_before_state is not None
                    and -60 <= seconds_before_state <= 15 * 60
                ),
            }
        )
    return receipts


def _selected_run_state_sync_receipts(
    repo_root: Path,
    *,
    selected_slugs: Sequence[str],
    run_state: Mapping[str, Any],
    limit: int = 12,
) -> list[dict[str, Any]]:
    raw_receipts = run_state.get("selected_sync_receipts")
    if not isinstance(raw_receipts, list):
        return []

    by_slug: dict[str, Mapping[str, Any]] = {}
    for raw in raw_receipts:
        if not isinstance(raw, Mapping):
            continue
        slug = str(raw.get("slug") or "").strip()
        if not slug:
            continue
        by_slug[slug] = raw

    receipts: list[dict[str, Any]] = []
    for slug in [str(item) for item in selected_slugs if str(item or "").strip()][:limit]:
        raw = by_slug.get(slug)
        if raw is None:
            continue
        report_path = str(raw.get("report_path") or "").strip()
        mode = str(raw.get("report_mode") or "").strip()
        generated_at = str(raw.get("report_generated_at") or "").strip()
        receipts.append(
            {
                "slug": slug,
                "path": _repo_rel(repo_root, repo_root / report_path) if report_path else None,
                "exists": bool(report_path),
                "generated_at": generated_at or None,
                "mode": mode or None,
                "status": raw.get("report_status"),
                "source_changed": bool(raw.get("source_changed")),
                "commit_count": _int(raw.get("commit_count")),
                "high_signal_change_count": _int(raw.get("high_signal_change_count")),
                "broken_target_count": _int(raw.get("broken_target_count")),
                "run_state_receipt": True,
                "verified_sync": mode == "sync" and bool(report_path) and bool(generated_at),
            }
        )
    return receipts


def _build_refresh_actuator(
    repo_root: Path,
    *,
    digest: Mapping[str, Any] | None,
    sync: Mapping[str, Any],
    stale_rows: Sequence[Mapping[str, Any]],
    attention_rows: Sequence[Mapping[str, Any]],
    attention_limit: int,
) -> dict[str, Any]:
    run_state_path = repo_root / "annexes" / "annex_sync_digest_run_state.json"
    run_state = _load_json(run_state_path) or {}
    sync_selected = [str(item) for item in list(sync.get("selected_slugs") or []) if str(item or "").strip()]
    state_selected = [str(item) for item in list(run_state.get("selected_slugs") or []) if str(item or "").strip()]
    selected_slugs = sync_selected or state_selected
    receipts = _selected_report_receipts(
        repo_root,
        selected_slugs=selected_slugs,
        run_updated_at=run_state.get("updated_at"),
        limit=attention_limit,
    )
    run_state_receipts = _selected_run_state_sync_receipts(
        repo_root,
        selected_slugs=selected_slugs,
        run_state=run_state,
        limit=attention_limit,
    )
    current_verified_slugs = {
        str(row.get("slug") or "")
        for row in receipts
        if row.get("exists")
        and row.get("mode") == "sync"
        and (not run_state or row.get("near_run_state"))
    }
    state_verified_slugs = {
        str(row.get("slug") or "")
        for row in run_state_receipts
        if row.get("verified_sync")
    }
    verified_slugs = current_verified_slugs | state_verified_slugs
    receipt_rows_by_slug = {str(row.get("slug") or ""): row for row in receipts}
    state_receipt_rows_by_slug = {str(row.get("slug") or ""): row for row in run_state_receipts}
    evidence_rows: list[Mapping[str, Any]] = []
    for slug in [str(item) for item in selected_slugs if str(item or "").strip()][:attention_limit]:
        state_row = state_receipt_rows_by_slug.get(slug)
        current_row = receipt_rows_by_slug.get(slug)
        if state_row is not None and state_row.get("verified_sync"):
            evidence_rows.append(state_row)
        elif current_row is not None:
            evidence_rows.append(current_row)
    report_receipt_count = sum(1 for row in receipts if row.get("exists"))
    near_state_count = sum(1 for row in receipts if row.get("near_run_state"))
    sync_mode_count = sum(1 for row in receipts if row.get("mode") == "sync")
    expected_receipt_count = min(len(selected_slugs), attention_limit)
    verified_sync_count = sum(
        1
        for slug in [str(item) for item in selected_slugs if str(item or "").strip()][:attention_limit]
        if slug in verified_slugs
    )
    run_state_sync_receipt_count = sum(1 for row in run_state_receipts if row.get("mode") == "sync")
    run_state_verified_sync_count = sum(1 for row in run_state_receipts if row.get("verified_sync"))
    source_changed_count = sum(1 for row in evidence_rows if row.get("source_changed"))
    commit_count_total = sum(_int(row.get("commit_count")) for row in evidence_rows)
    high_signal_total = sum(_int(row.get("high_signal_change_count")) for row in evidence_rows)
    failure_count = _int(sync.get("failure_count"))
    requested = bool(sync.get("requested"))
    if requested and failure_count:
        status = "partial_failure"
    elif requested and expected_receipt_count and verified_sync_count < expected_receipt_count:
        status = "bounded_refresh_unverified"
    elif requested:
        status = "bounded_refresh_recorded"
    elif run_state:
        status = "last_run_state_available"
    else:
        status = "no_run_state"

    return {
        "status": status,
        "last_digest_mode": (digest or {}).get("mode") if isinstance(digest, Mapping) else None,
        "last_sync_requested": requested,
        "sync_status": sync.get("status"),
        "requested_count": sync.get("requested_count"),
        "synced_count": sync.get("synced_count"),
        "failure_count": failure_count,
        "selected_slugs": selected_slugs[:attention_limit],
        "expected_report_receipt_count": expected_receipt_count,
        "selected_report_receipt_count": report_receipt_count,
        "selected_reports_near_run_state_count": near_state_count,
        "selected_reports_sync_mode_count": sync_mode_count,
        "selected_reports_verified_sync_count": verified_sync_count,
        "selected_reports_unverified_count": max(0, expected_receipt_count - verified_sync_count),
        "selected_run_state_sync_receipt_count": run_state_sync_receipt_count,
        "selected_run_state_verified_sync_count": run_state_verified_sync_count,
        "selected_reports_source_changed_count": source_changed_count,
        "selected_reports_commit_count_total": commit_count_total,
        "selected_reports_high_signal_change_count_total": high_signal_total,
        "selected_report_receipts": receipts,
        "selected_run_state_sync_receipts": run_state_receipts,
        "run_state": {
            "path": _repo_rel(repo_root, run_state_path),
            "exists": bool(run_state),
            "updated_at": run_state.get("updated_at"),
            "last_selected_slug": run_state.get("last_selected_slug"),
            "available_count": run_state.get("available_count"),
            "limit": run_state.get("limit"),
            "wrapped": run_state.get("wrapped"),
            "selected_slugs": state_selected[:attention_limit],
            "selected_sync_receipt_count": len(run_state.get("selected_sync_receipts") or [])
            if isinstance(run_state.get("selected_sync_receipts"), list)
            else 0,
        },
        "chunk": sync.get("chunk") if isinstance(sync.get("chunk"), Mapping) else {},
        "stale_queue_count": len(stale_rows),
        "oldest_stale_days": max((_int(row.get("stale_days")) for row in stale_rows), default=0),
        "attention_queue_count": len(attention_rows),
        "bounded_refresh_command": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 8",
        "bounded_smoke_command": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 1",
        "full_fleet_guardrail": "Full-fleet refresh requires explicit --full and is foreground/debug only.",
        "actuator_contract": [
            "pull only the selected repo-kind annex chunk",
            "write per-annex sync reports for selected slugs",
            "refresh annex contents/catalog/distillation projections after successful syncs",
            "roll up the fleet digest and rotate annex_sync_digest_run_state.json",
        ],
    }


def _build_projection_freshness(repo_root: Path) -> dict[str, Any]:
    digest = _path_metadata(repo_root, repo_root / "annexes" / "annex_sync_digest.json")
    digest_markdown = _path_metadata(repo_root, repo_root / "annexes" / "annex_sync_digest.md")
    run_state = _path_metadata(repo_root, repo_root / "annexes" / "annex_sync_digest_run_state.json")
    catalog = _path_metadata(repo_root, repo_root / "annexes" / "annex_catalog.json")
    distillation_index = _path_metadata(repo_root, repo_root / "annexes" / "annex_distillation_index.json")
    newest_report = _newest_path_metadata(repo_root, ["annexes/*/annex_sync_report.json"])
    newest_sync_report = _newest_annex_sync_report_metadata(repo_root)
    newest_family_or_notes = _newest_path_metadata(repo_root, ["annexes/*/annex_family.json", "annexes/*/annex_notes.json"])
    newest_distillation = _newest_path_metadata(repo_root, ["annexes/*/distillation.json"])

    debt_signals: list[dict[str, Any]] = []
    if not catalog.get("exists"):
        debt_signals.append(
            {
                "debt_id": "annex_currentness:projection_freshness:catalog_missing",
                "projection": "annex_catalog",
                "repair_class": "projection_rebuild_required",
                "evidence": "annexes/annex_catalog.json is missing.",
                "priority": 78,
            }
        )
    elif _is_newer(newest_sync_report, catalog) or _is_newer(newest_family_or_notes, catalog):
        source = newest_sync_report if _is_newer(newest_sync_report, catalog) else newest_family_or_notes
        debt_signals.append(
            {
                "debt_id": "annex_currentness:projection_freshness:catalog_stale",
                "projection": "annex_catalog",
                "repair_class": "projection_rebuild_required",
                "evidence": (
                    f"{source.get('path')} mtime={source.get('mtime')} is newer than "
                    f"annexes/annex_catalog.json mtime={catalog.get('mtime')}"
                ),
                "priority": 76,
            }
        )

    if not distillation_index.get("exists"):
        debt_signals.append(
            {
                "debt_id": "annex_currentness:projection_freshness:distillation_index_missing",
                "projection": "annex_distillation_index",
                "repair_class": "projection_rebuild_required",
                "evidence": "annexes/annex_distillation_index.json is missing.",
                "priority": 78,
            }
        )
    elif _is_newer(newest_sync_report, distillation_index) or _is_newer(newest_distillation, distillation_index):
        source = newest_sync_report if _is_newer(newest_sync_report, distillation_index) else newest_distillation
        debt_signals.append(
            {
                "debt_id": "annex_currentness:projection_freshness:distillation_index_stale",
                "projection": "annex_distillation_index",
                "repair_class": "projection_rebuild_required",
                "evidence": (
                    f"{source.get('path')} mtime={source.get('mtime')} is newer than "
                    f"annexes/annex_distillation_index.json mtime={distillation_index.get('mtime')}"
                ),
                "priority": 76,
            }
        )

    return {
        "status": "stale" if debt_signals else "current",
        "debt_count": len(debt_signals),
        "artifacts": {
            "annex_sync_digest": digest,
            "annex_sync_digest_markdown": digest_markdown,
            "annex_sync_digest_run_state": run_state,
            "annex_catalog": catalog,
            "annex_distillation_index": distillation_index,
        },
        "source_mtimes": {
            "newest_annex_sync_report": newest_report,
            "newest_projection_relevant_sync_report": newest_sync_report,
            "newest_annex_family_or_notes": newest_family_or_notes,
            "newest_distillation": newest_distillation,
        },
        "freshness_rule": (
            "Per-annex sync-mode reports, family metadata, notes, or distillation files newer than "
            "catalog/distillation projections create projection freshness debt. Validate-mode reports "
            "are verification receipts and do not by themselves require catalog/distillation rebuilds. "
            "Digest mtime is reported but is not stale evidence by itself because digest --run writes "
            "digest after projections."
        ),
        "debt_signals": debt_signals,
    }


def _deferred_projection_freshness(repo_root: Path) -> dict[str, Any]:
    return {
        "status": "deferred_by_quick_profile",
        "debt_count": 0,
        "deferred": True,
        "reason": (
            "Projection freshness scans per-annex report mtimes and is explicit drilldown/full-profile "
            "work, not quick first-contact work."
        ),
        "artifacts": {
            "annex_sync_digest": _path_stat_metadata(repo_root, repo_root / "annexes" / "annex_sync_digest.json"),
            "annex_sync_digest_markdown": _path_stat_metadata(repo_root, repo_root / "annexes" / "annex_sync_digest.md"),
            "annex_sync_digest_run_state": _path_stat_metadata(
                repo_root,
                repo_root / "annexes" / "annex_sync_digest_run_state.json",
            ),
            "annex_catalog": _path_stat_metadata(repo_root, repo_root / "annexes" / "annex_catalog.json"),
            "annex_distillation_index": _path_stat_metadata(
                repo_root,
                repo_root / "annexes" / "annex_distillation_index.json",
            ),
        },
        "source_mtimes": {
            "status": "deferred_by_quick_profile",
            "omitted": [
                "newest_annex_sync_report",
                "newest_projection_relevant_sync_report",
                "newest_annex_family_or_notes",
                "newest_distillation",
            ],
        },
        "freshness_rule": (
            "Run the full annex currentness route when a decision depends on projection freshness; "
            "quick metabolism preserves digest-level currentness pressure only."
        ),
        "debt_signals": [],
        "drilldown_command": "./repo-python kernel.py --annex-currentness --context-budget 12000",
    }


def _build_movement_to_row_job(
    attention_rows: Sequence[Mapping[str, Any]],
    *,
    attention_limit: int,
) -> dict[str, Any]:
    changed_rows = [
        _compact_row(row)
        for row in attention_rows
        if _int(row.get("commit_count")) > 0
        or _int(row.get("high_signal_change_count")) > 0
        or _int(row.get("broken_target_count")) > 0
        or _int(row.get("distillation_issue_count")) > 0
        or str(row.get("bucket") or "") in {"error", "annotation_needed", "unannotated"}
    ]
    missing_report_rows = [
        row for row in changed_rows
        if not str(row.get("report_path") or "").strip()
    ]
    row_job_limit = min(attention_limit, 5)
    return {
        "status": "gap" if missing_report_rows else "ready",
        "changed_attention_row_count": len(changed_rows),
        "candidate_row_job_count": min(len(changed_rows), row_job_limit),
        "changed_rows_without_report_path_count": len(missing_report_rows),
        "top_candidate_rows": changed_rows[:row_job_limit],
        "row_job_command": f"./repo-python kernel.py --metabolism-row-jobs annex-sync-digest --limit {row_job_limit}",
        "contract": "Substrate movement receipts become row jobs; row jobs select exact evidence before repair, mining, or pattern transfer.",
    }


def _debt_row(
    *,
    debt_id: str,
    priority: int,
    title: str,
    evidence: str,
    repair_class: str,
    target_files: Sequence[str],
    tests: Sequence[str],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "debt_id": debt_id,
        "debt_class": "annex_currentness_debt",
        "priority": priority,
        "title": title,
        "evidence": _trim(evidence, max_chars=320),
        "repair_class": repair_class,
        "target_files": list(target_files),
        "tests": list(tests),
        "source_surface": "annexes/annex_sync_digest.json",
    }
    if extra:
        row.update(dict(extra))
    return row


def _currentness_debt_rows(
    *,
    digest_path: str,
    markdown_path: str,
    digest: Mapping[str, Any] | None,
    rows: Sequence[Mapping[str, Any]],
    refresh_actuator: Mapping[str, Any],
    projection_freshness: Mapping[str, Any],
    movement_to_row_job: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if digest is None:
        return [
            _debt_row(
                debt_id="annex_currentness:sync_digest:missing",
                priority=84,
                title="annex sync digest is missing or unreadable",
                evidence="No usable annexes/annex_sync_digest.json was found; annex currentness cannot be assessed.",
                repair_class="refresh_annex_sync_digest",
                target_files=[digest_path, markdown_path, "annex_import.py"],
                tests=[
                    "kernel annex-currentness reports digest_status=available after digest refresh",
                    "navigation metabolism separates annex_currentness_debt from routing_coverage_debt",
                ],
                extra={
                    "next_command": "./repo-python annex_import.py digest",
                },
            )
        ]

    summary = digest.get("summary") if isinstance(digest.get("summary"), Mapping) else {}
    bucket_counts = digest.get("bucket_counts") if isinstance(digest.get("bucket_counts"), Mapping) else {}
    sync = digest.get("sync") if isinstance(digest.get("sync"), Mapping) else {}
    attention_count = _int(digest.get("attention_count"))
    stale_count = _int(digest.get("stale_count"))
    failure_count = _int(sync.get("failure_count"))
    debt: list[dict[str, Any]] = []

    if attention_count:
        top = _top_rows(rows, limit=3)
        debt.append(
            _debt_row(
                debt_id="annex_currentness:sync_digest:attention",
                priority=84,
                title="annex sync digest has attention rows",
                evidence=(
                    f"attention_count={attention_count}; buckets={dict(bucket_counts)}; "
                    f"top={[row.get('slug') for row in top]}"
                ),
                repair_class="annex_digest_attention_triage",
                target_files=[digest_path, markdown_path, "system/lib/metabolism_row_jobs.py"],
                tests=[
                    "kernel --metabolism-row-jobs annex-sync-digest emits bounded row jobs",
                    "annex currentness route reports attention rows without rewriting patterns",
                ],
                extra={
                    "safe_alternative": "./repo-python kernel.py --metabolism-row-jobs annex-sync-digest --limit 5",
                    "attention_count": attention_count,
                    "bucket_counts": dict(bucket_counts),
                },
            )
        )

    if stale_count:
        debt.append(
            _debt_row(
                debt_id="annex_currentness:sync_digest:stale",
                priority=72,
                title="annex sync digest has stale rows",
                evidence=(
                    f"stale_count={stale_count}; max_stale_days={digest.get('max_stale_days')}; "
                    f"threshold={digest.get('stale_threshold_days')}"
                ),
                repair_class="bounded_annex_digest_refresh",
                target_files=[digest_path, markdown_path, "annex_import.py"],
                tests=[
                    "annex digest --run --quiet --limit keeps refresh bounded",
                    "annex currentness debt remains separate from clusterability and routing coverage",
                ],
                extra={
                    "safe_alternative": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 8",
                    "stale_count": stale_count,
                    "max_stale_days": digest.get("max_stale_days"),
                },
            )
        )

    if refresh_actuator.get("status") == "no_run_state" and stale_count:
        debt.append(
            _debt_row(
                debt_id="annex_currentness:refresh_actuator:no_run_state",
                priority=74,
                title="annex refresh actuator has no rotation receipt",
                evidence=(
                    "annex_sync_digest_run_state.json is missing while stale rows exist; "
                    "bounded refresh rotation cannot be proven."
                ),
                repair_class="bounded_annex_digest_refresh",
                target_files=[digest_path, markdown_path, "annexes/annex_sync_digest_run_state.json", "annex_import.py"],
                tests=[
                    "digest --run --quiet --limit writes annex_sync_digest_run_state.json",
                    "annex currentness reports selected_slugs and run_state cursor",
                ],
                extra={
                    "safe_alternative": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 1",
                },
            )
        )

    if refresh_actuator.get("status") == "bounded_refresh_unverified":
        debt.append(
            _debt_row(
                debt_id="annex_currentness:refresh_actuator:unverified_sync_receipt",
                priority=78,
                title="annex refresh actuator lacks selected sync receipts",
                evidence=(
                    f"verified_sync={refresh_actuator.get('selected_reports_verified_sync_count')}/"
                    f"{refresh_actuator.get('expected_report_receipt_count')}; "
                    f"sync_mode={refresh_actuator.get('selected_reports_sync_mode_count')}; "
                    f"near_run_state={refresh_actuator.get('selected_reports_near_run_state_count')}"
                ),
                repair_class="bounded_annex_digest_refresh",
                target_files=[digest_path, markdown_path, "annexes/*/annex_sync_report.json", "annex_import.py"],
                tests=[
                    "annex currentness marks validate-overwritten selected reports as unverified",
                    "digest --run --quiet --limit rewrites selected reports with sync receipts",
                ],
                extra={
                    "safe_alternative": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 8",
                },
            )
        )

    if failure_count:
        debt.append(
            _debt_row(
                debt_id="annex_currentness:sync_digest:sync_failures",
                priority=82,
                title="annex sync digest pull had failures",
                evidence=f"failure_count={failure_count}; status={sync.get('status') or summary.get('status')}",
                repair_class="annex_digest_sync_failure_triage",
                target_files=[digest_path, markdown_path, "annex_import.py"],
                tests=[
                    "annex digest surfaces sync failures without hiding currentness posture",
                ],
                extra={
                    "failure_count": failure_count,
                    "failures": list(sync.get("failures") or [])[:5],
                },
            )
        )

    for signal in list(projection_freshness.get("debt_signals") or []):
        if not isinstance(signal, Mapping):
            continue
        debt.append(
            _debt_row(
                debt_id=str(signal.get("debt_id") or "annex_currentness:projection_freshness:unknown"),
                priority=_int(signal.get("priority")) or 76,
                title=f"annex {signal.get('projection') or 'projection'} is older than refresh substrate",
                evidence=str(signal.get("evidence") or "Annex projection freshness could not be proven."),
                repair_class=str(signal.get("repair_class") or "projection_rebuild_required"),
                target_files=[
                    "annexes/annex_catalog.json",
                    "annexes/annex_distillation_index.json",
                    "annex_import.py",
                ],
                tests=[
                    "annex currentness reports projection_freshness.status=current after bounded refresh",
                    "digest --run refreshes browse projections after selected sync reports",
                ],
                extra={
                    "safe_alternative": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 1",
                    "projection": signal.get("projection"),
                },
            )
        )

    movement_gap_count = _int(movement_to_row_job.get("changed_rows_without_report_path_count"))
    if movement_gap_count:
        debt.append(
            _debt_row(
                debt_id="annex_currentness:movement_to_row_job:missing_report_paths",
                priority=80,
                title="changed annex digest rows are not row-job routable",
                evidence=f"{movement_gap_count} changed attention row(s) lack report_path evidence.",
                repair_class="movement_to_row_job_gap",
                target_files=[digest_path, "system/lib/metabolism_row_jobs.py", "annex_import.py"],
                tests=[
                    "kernel --metabolism-row-jobs annex-sync-digest emits row jobs for changed attention rows",
                    "annex digest rows include report_path for changed rows",
                ],
                extra={
                    "safe_alternative": "./repo-python kernel.py --metabolism-row-jobs annex-sync-digest --limit 5",
                },
            )
        )

    return debt


def build_annex_currentness(
    repo_root: Path | str,
    *,
    context_budget: int = 12000,
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS,
    attention_limit: int = 12,
    include_projection_freshness: bool = True,
) -> dict[str, Any]:
    """
    Return a compact read-only packet over annex_sync_digest.json.

    The packet intentionally treats movement as candidate review work. It never
    refreshes, rewrites notes, rewrites patterns, or promotes doctrine.
    """
    root = Path(repo_root).resolve()
    digest_path = root / "annexes" / "annex_sync_digest.json"
    markdown_path = root / "annexes" / "annex_sync_digest.md"
    digest = _load_json(digest_path)
    digest_rel = _repo_rel(root, digest_path)
    markdown_rel = _repo_rel(root, markdown_path)

    rows: list[Mapping[str, Any]] = []
    if isinstance(digest, Mapping):
        rows = [row for row in list(digest.get("rows") or []) if isinstance(row, Mapping)]

    attention_slugs = set(str(slug) for slug in (digest or {}).get("attention_slugs", []) or [])
    attention_rows = [
        row for row in rows
        if str(row.get("slug") or "") in attention_slugs
        or str(row.get("bucket") or "") in _ATTENTION_BUCKETS
    ]
    stale_rows = [
        row for row in rows
        if str(row.get("bucket") or "") != "missing_clone"
        and row.get("stale_days") is not None
        and _int(row.get("stale_days")) >= stale_threshold_days
    ]
    high_signal_rows = _high_signal_rows(rows, limit=max(8, attention_limit))

    sync = digest.get("sync") if isinstance(digest, Mapping) and isinstance(digest.get("sync"), Mapping) else {}
    bucket_counts = (
        dict(digest.get("bucket_counts") or {})
        if isinstance(digest, Mapping) and isinstance(digest.get("bucket_counts"), Mapping)
        else {}
    )
    refresh_actuator = _build_refresh_actuator(
        root,
        digest=digest,
        sync=sync,
        stale_rows=stale_rows,
        attention_rows=attention_rows,
        attention_limit=attention_limit,
    )
    projection_freshness = (
        _build_projection_freshness(root)
        if include_projection_freshness
        else _deferred_projection_freshness(root)
    )
    movement_to_row_job = _build_movement_to_row_job(
        attention_rows,
        attention_limit=attention_limit,
    )
    debt_rows = _currentness_debt_rows(
        digest_path=digest_rel,
        markdown_path=markdown_rel,
        digest=digest,
        rows=rows,
        refresh_actuator=refresh_actuator,
        projection_freshness=projection_freshness,
        movement_to_row_job=movement_to_row_job,
    )
    status = "missing_digest"
    if digest is not None:
        status = "attention_needed" if debt_rows else "current"

    packet: dict[str, Any] = {
        "kind": "annex_currentness",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "budget": {
            "context_budget_tokens": max(1000, int(context_budget or 12000)),
            "trimmed_for_budget": False,
        },
        "summary": {
            "digest_status": status,
            "digest_generated_at": (digest or {}).get("generated_at") if isinstance(digest, Mapping) else None,
            "mode": (digest or {}).get("mode") if isinstance(digest, Mapping) else None,
            "annex_count": _int((digest or {}).get("annex_count") if isinstance(digest, Mapping) else 0),
            "attention_count": _int((digest or {}).get("attention_count") if isinstance(digest, Mapping) else 0),
            "stale_count": _int((digest or {}).get("stale_count") if isinstance(digest, Mapping) else 0),
            "max_stale_days": _int((digest or {}).get("max_stale_days") if isinstance(digest, Mapping) else 0),
            "sync_requested": bool(sync.get("requested")),
            "sync_status": sync.get("status"),
            "sync_failure_count": _int(sync.get("failure_count")),
            "currentness_debt": len(debt_rows),
            "refresh_actuator_status": refresh_actuator.get("status"),
            "projection_freshness_status": projection_freshness.get("status"),
            "projection_currentness_debt": _int(projection_freshness.get("debt_count")),
            "projection_freshness_deferred": bool(projection_freshness.get("deferred")),
            "movement_to_row_job_status": movement_to_row_job.get("status"),
            "movement_to_row_job_gap_count": _int(movement_to_row_job.get("changed_rows_without_report_path_count")),
            "bucket_counts": bucket_counts,
        },
        "source": {
            "reused_existing_infra": True,
            "digest_json": digest_rel,
            "digest_markdown": markdown_rel,
            "per_annex_report_pattern": "annexes/<slug>/annex_sync_report.json",
            "report_schema": "codex/standards/annex/std_annex_sync_report.json",
            "review_command": "./repo-python annex_import.py digest --json",
            "bounded_refresh_command": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 8",
        },
        "currentness_contract": {
            "pattern_rows_are": "relevance indexes and routing handles, not authority",
            "before_transfer": [
                "check digest/currentness posture",
                "open the selected annex report when its row is attention-bearing",
                "open exact annex notes and source files before adapting a pattern",
            ],
            "cluster_surfaces": "stale annexes do not invalidate annex_patterns.cluster_flag automatically",
            "movement_policy": "upstream movement creates candidate review work; it does not rewrite distillation rows or doctrine by itself",
            "stale_row_policy": (
                "stale rows are refreshable sync targets; missing_clone rows stay in the missing_clone bucket because "
                "bounded refresh cannot update absent local clones"
            ),
            "imagination_policy": "emerging upstream affordances may enter imagination as candidates only after exact evidence is opened",
        },
        "last_sync_run": {
            "requested": bool(sync.get("requested")),
            "status": sync.get("status"),
            "requested_count": sync.get("requested_count"),
            "synced_count": sync.get("synced_count"),
            "failure_count": sync.get("failure_count"),
            "selected_slugs": list(sync.get("selected_slugs") or [])[:24],
            "chunk": sync.get("chunk") if isinstance(sync.get("chunk"), Mapping) else {},
        },
        "refresh_actuator": refresh_actuator,
        "projection_freshness": projection_freshness,
        "movement_to_row_job": movement_to_row_job,
        "top_attention_rows": _top_rows(attention_rows, limit=attention_limit),
        "high_signal_movement_top": high_signal_rows[:attention_limit],
        "stale_rows": [
            {"slug": str(row.get("slug") or ""), "stale_days": row.get("stale_days")}
            for row in sorted(stale_rows, key=lambda row: (-_int(row.get("stale_days")), str(row.get("slug") or "")))[:attention_limit]
        ],
        "upstream_movers_top": list((digest or {}).get("upstream_movers_top") or [])[:attention_limit]
        if isinstance(digest, Mapping)
        else [],
        "candidate_review_work": [
            {
                "slug": row.get("slug"),
                "bucket": row.get("bucket"),
                "report_path": row.get("report_path"),
                "next": (
                    "repair notes before mining"
                    if row.get("bucket") == "drift_detected"
                    else "inspect high_signal_changes before pattern transfer"
                    if row.get("bucket") == "review_needed"
                    else "bootstrap annotations before mining"
                ),
            }
            for row in _top_rows(attention_rows, limit=min(attention_limit, 8))
        ],
        "debt_rows": debt_rows,
        "next_commands": [
            "./repo-python annex_import.py digest --json",
            "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 8",
            "./repo-python kernel.py --metabolism-row-jobs annex-sync-digest --limit 5",
        ],
    }
    return packet
