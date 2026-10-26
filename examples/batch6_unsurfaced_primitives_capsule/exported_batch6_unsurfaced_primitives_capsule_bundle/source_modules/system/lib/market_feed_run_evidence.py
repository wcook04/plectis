"""
[PURPOSE]
- Teleology: Project a market-feed run into a portable evidence card so Station,
  dissemination packets, and application snapshots can cite the same run facts
  without treating artifact presence as readiness.
- Mechanism: Read one feed run directory, summarize artifacts, sidecars,
  specimen rows, quality tones, readiness-summary state, blockers, and safe-use
  posture into deterministic JSON.
- Non-goal: This is not a trading signal, not a production market claim, and
  not a replacement for `feed_readiness_summary.json`.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib.feed_quality import artifact_quality_from_mapping, normalize_quality_tone
from system.lib.utils import resolve_runs_dir


SCHEMA_VERSION = "market_feed_run_evidence_card_v0"
DEFAULT_REPORT_ROOT = Path("state/reports/market_feeds")
DEFAULT_LATEST_FILENAME = "latest_evidence_card.json"
CARD_FILENAME = "market_feed_run_evidence_card_v0.json"

FEED_NODE_IDS: tuple[str, ...] = (
    "global_stock_feed",
    "global_etf_feed",
    "global_macro_feed",
    "global_polymarket_feed",
    "global_stockgrid_feed",
    "global_news_feed",
    "global_calculator_feed",
)

METRIC_COLUMNS: frozenset[str] = frozenset(
    {
        "Price",
        "price",
        "Last",
        "Change",
        "Chg_1d",
        "Chg_5d",
        "Chg_20d",
        "Vol_20d",
        "Z_Short",
        "Z_Medium",
        "value",
        "latest_value",
        "close",
        "open",
        "high",
        "low",
        "volume",
        "probability",
        "probability_mid",
        "yes_price",
        "no_price",
    }
)

SPECIMEN_ROW_LIMIT = 3
SPECIMEN_COLUMN_LIMIT = 8
TABLE_LIMIT = 4

RUN_SOURCE_FILENAMES: tuple[str, ...] = (
    "runtime_context.json",
    "run_summary.json",
    "regrade_summary.json",
)


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_evidence_card(payload), encoding="utf-8")


def _read_runs_dir_value(repo_root: Path) -> Any:
    master = _read_json(repo_root / "master_config.json")
    paths = master.get("paths") if isinstance(master.get("paths"), dict) else {}
    return paths.get("runs_dir") if isinstance(paths, dict) else None


def _is_feed_run(run_dir: Path) -> bool:
    runtime = _read_json(run_dir / "runtime_context.json")
    mission = str(runtime.get("mission_name") or runtime.get("subject_group") or "").strip()
    if mission == "feeds":
        return True
    artifacts = run_dir / "artifacts"
    return any((artifacts / f"{node_id}.json").exists() for node_id in FEED_NODE_IDS)


def _latest_feed_run_dir(repo_root: Path) -> Path:
    runs_dir = resolve_runs_dir(repo_root, _read_runs_dir_value(repo_root))
    candidates = [path for path in runs_dir.iterdir() if path.is_dir() and _is_feed_run(path)]
    if not candidates:
        raise FileNotFoundError(f"no feed runs found under {runs_dir}")
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_feed_run_dir(repo_root: Path, run_id: str | None = None) -> Path:
    if run_id:
        runs_dir = resolve_runs_dir(repo_root, _read_runs_dir_value(repo_root))
        run_dir = runs_dir / run_id
        if not run_dir.exists():
            raise FileNotFoundError(f"feed run not found: {run_id}")
        return run_dir
    return _latest_feed_run_dir(repo_root)


def declared_feed_source_paths(run_dir: Path) -> list[Path]:
    paths = [run_dir / filename for filename in RUN_SOURCE_FILENAMES]
    paths.append(run_dir / "artifacts" / "feed_readiness_summary.json")
    paths.extend(run_dir / "artifacts" / f"{node_id}.json" for node_id in FEED_NODE_IDS)
    return paths


def _source_mtime_iso(paths: Sequence[Path], fallback_dir: Path) -> str:
    newest = fallback_dir.stat().st_mtime
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return datetime.fromtimestamp(newest, tz=timezone.utc).replace(microsecond=0).isoformat()


def _source_fingerprint(paths: Sequence[Path], repo_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: _repo_rel(repo_root, item)):
        rel = _repo_rel(repo_root, path)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        if not path.exists() or path.is_dir():
            digest.update(b"missing")
            continue
        try:
            digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
        except OSError:
            digest.update(b"unreadable")
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def feed_source_manifest(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = declared_feed_source_paths(run_dir)
    artifacts = []
    for path in paths:
        artifacts.append(
            {
                "path": _repo_rel(repo_root, path),
                "present": path.exists() and path.is_file(),
                "role": "feed_artifact" if path.parent.name == "artifacts" and path.name.endswith(".json") else "run_metadata",
                "feed_id": path.stem if path.parent.name == "artifacts" and path.stem in FEED_NODE_IDS else None,
                "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            }
        )
    return {
        "schema_version": "feed_run_source_manifest_v0",
        "authority_boundary": "declared_feed_source_inputs_only",
        "source_count": len(paths),
        "present_source_count": sum(1 for path in paths if path.exists() and path.is_file()),
        "input_watermark": _source_mtime_iso(paths, run_dir),
        "source_fingerprint": _source_fingerprint(paths, repo_root),
        "source_artifacts": artifacts,
        "downstream_projection_globs_excluded": [
            "state/runs/<run_id>/artifacts/quant_presentation_mart.json",
            "state/reports/market_feeds/<run_id>/*.json",
            "state/reports/market_feeds/latest_*.json",
        ],
    }


def _compact_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        text = value.strip()
        return text if len(text) <= 120 else f"{text[:117]}..."
    return str(value)[:120]


def _table_candidates(data: Any) -> list[tuple[str, list[Any], list[Any]]]:
    tables: list[tuple[str, list[Any], list[Any]]] = []

    def visit(value: Any, path: str, depth: int) -> None:
        if depth > 4 or not isinstance(value, Mapping):
            return
        columns = value.get("columns")
        rows = value.get("rows")
        if isinstance(columns, list) and isinstance(rows, list):
            tables.append((path or "data", columns, rows))
        # v0.10.2: list-of-record shape (data.items used by the news lane).
        # Synthesize columns from the union of keys in the first few items
        # so evidence-card row_count / column_count reflect items, not 0.
        # Without this the news lane evaluates as artifact_rows_by_lane=0
        # even when data.items has 140 rows, cascading into quant_mart
        # coverage rows=0 and a "news dark" data_quality state.
        items = value.get("items")
        if (
            isinstance(items, list)
            and items
            and all(isinstance(item, Mapping) for item in items[:5])
        ):
            synthetic_cols: list[Any] = []
            seen: set[str] = set()
            for item in items[:10]:
                for key in item.keys():
                    if key not in seen:
                        seen.add(key)
                        synthetic_cols.append(key)
            table_path = f"{path}.items" if path else "data.items"
            tables.append((table_path, synthetic_cols, items))
        for key, child in value.items():
            if isinstance(child, Mapping):
                child_path = f"{path}.{key}" if path else str(key)
                visit(child, child_path, depth + 1)

    visit(data, "", 0)
    tables.sort(key=lambda item: len(item[2]), reverse=True)
    return tables


def _row_preview(columns: Sequence[Any], rows: Sequence[Any]) -> list[dict[str, Any]]:
    selected_columns = [str(column) for column in list(columns)[:SPECIMEN_COLUMN_LIMIT]]
    previews: list[dict[str, Any]] = []
    for row in list(rows)[:SPECIMEN_ROW_LIMIT]:
        if isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
            previews.append(
                {
                    column: _compact_value(row[index] if index < len(row) else None)
                    for index, column in enumerate(selected_columns)
                }
            )
        elif isinstance(row, Mapping):
            previews.append(
                {
                    column: _compact_value(row.get(column))
                    for column in selected_columns
                    if column in row
                }
            )
    return previews


def _table_shape(tables: Sequence[tuple[str, list[Any], list[Any]]]) -> dict[str, Any]:
    columns = sorted({str(column) for _path, cols, _rows in tables for column in cols})
    metric_columns = [column for column in columns if column in METRIC_COLUMNS]
    return {
        "table_count": len(tables),
        "row_count": sum(len(rows) for _path, _columns, rows in tables),
        "column_count": len(columns),
        "metric_columns": metric_columns[:16],
    }


def _diagnostic_summary(diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    selected = {}
    for key in (
        "input_rows",
        "output_rows",
        "dropped_rows",
        "fetch_success_count",
        "fetch_failure_count",
        "fetch_success_rate",
        "batch_download_ok",
        "batch_ticker_count",
        "emitted_rows",
        "emitted_topics",
    ):
        if key in diagnostics:
            selected[key] = diagnostics.get(key)
    warnings = diagnostics.get("warnings")
    if isinstance(warnings, list):
        selected["warning_count"] = len(warnings)
        selected["warning_preview"] = [str(item)[:160] for item in warnings[:3]]
    return selected


def _sidecar_summary(metadata: Mapping[str, Any]) -> list[dict[str, Any]]:
    sidecars = metadata.get("sidecars")
    if not isinstance(sidecars, Mapping):
        return []
    rows: list[dict[str, Any]] = []
    for key, value in sidecars.items():
        if not isinstance(value, Mapping):
            rows.append({"key": str(key), "type": type(value).__name__})
            continue
        row: dict[str, Any] = {
            "key": str(key),
            "schema_version": value.get("schema_version"),
            "row_count": value.get("row_count"),
        }
        distribution = value.get("state_distribution") or value.get("lifecycle_distribution")
        if isinstance(distribution, Mapping):
            row["state_distribution"] = dict(distribution)
        rows.append(row)
    return rows


def _artifact_summary(repo_root: Path, run_dir: Path, node_id: str) -> dict[str, Any]:
    artifact_path = run_dir / "artifacts" / f"{node_id}.json"
    payload = _read_json(artifact_path)
    if not payload:
        return {
            "present": False,
            "path": _repo_rel(repo_root, artifact_path),
            "status": "missing",
            "row_count": 0,
            "metric_columns": [],
            "specimen_rows": [],
            "sidecars": [],
            "quality": {"tone": "block", "reasons": ["artifact missing"], "blocked_metrics": []},
        }

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    tables = _table_candidates(payload.get("data"))
    primary_path, primary_columns, primary_rows = tables[0] if tables else ("data", [], [])
    shape = _table_shape(tables)
    quality_status = artifact_quality_from_mapping(node_id, payload)
    quality = {
        "tone": quality_status.tone if quality_status is not None else "ok",
        "reasons": list(quality_status.reasons[:6]) if quality_status is not None else [],
        "blocked_metrics": list(quality_status.blocked_metrics[:6]) if quality_status is not None else [],
        "artifact_status": quality_status.artifact_status if quality_status is not None else payload.get("status") or metadata.get("status"),
    }
    return {
        "present": True,
        "path": _repo_rel(repo_root, artifact_path),
        "status": payload.get("status") or metadata.get("status") or "unknown",
        "tool": metadata.get("tool"),
        "as_of": metadata.get("as_of") or metadata.get("timestamp_iso"),
        "items_count": metadata.get("items_count"),
        "data_schema_version": metadata.get("data_schema_version"),
        "row_count": shape["row_count"],
        "table_count": shape["table_count"],
        "column_count": shape["column_count"],
        "metric_columns": shape["metric_columns"],
        "primary_table_path": primary_path,
        "tables": [
            {"path": path, "row_count": len(rows), "column_count": len(columns)}
            for path, columns, rows in list(tables)[:TABLE_LIMIT]
        ],
        "specimen_rows": _row_preview(primary_columns, primary_rows),
        "diagnostics": _diagnostic_summary(
            metadata.get("diagnostics") if isinstance(metadata.get("diagnostics"), Mapping) else {}
        ),
        "sidecars": _sidecar_summary(metadata),
        "sidecar_keys": sorted(str(key) for key in (metadata.get("sidecars") or {}).keys())
        if isinstance(metadata.get("sidecars"), Mapping)
        else [],
        "quality": quality,
    }


def _readiness_state(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    path = run_dir / "artifacts" / "feed_readiness_summary.json"
    payload = _read_json(path)
    if not payload:
        return {
            "state": "missing",
            "present": False,
            "ready": False,
            "path": _repo_rel(repo_root, path),
            "owner": "run_tools6.py",
            "blocking_reason": "feed_readiness_summary_missing",
        }
    blockers = [row for row in payload.get("blockers") or [] if isinstance(row, Mapping)]
    return {
        "state": "present_ready" if bool(payload.get("ready")) else "present_not_ready",
        "present": True,
        "ready": bool(payload.get("ready")),
        "path": _repo_rel(repo_root, path),
        "owner": "run_tools6.py",
        "target_count": payload.get("target_count"),
        "status_counts": payload.get("status_counts") if isinstance(payload.get("status_counts"), Mapping) else {},
        "blocker_count": len(blockers),
        "blockers": blockers[:8],
    }


def _run_grade(run_dir: Path) -> dict[str, Any]:
    summary = _read_json(run_dir / "run_summary.json")
    regrade = _read_json(run_dir / "regrade_summary.json")
    return {
        "grade": regrade.get("grade") or summary.get("grade") or "unknown",
        "grade_reason": regrade.get("grade_reason") or summary.get("grade_reason") or "",
        "original_grade": regrade.get("original_grade") or summary.get("grade"),
        "regraded_at": regrade.get("regraded_at"),
        "node_outcomes": summary.get("node_outcomes") if isinstance(summary.get("node_outcomes"), Mapping) else {},
        "duration_seconds": summary.get("duration_seconds"),
    }


def _quality_blockers(
    artifacts: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for node_id, artifact in artifacts.items():
        quality = artifact.get("quality") if isinstance(artifact.get("quality"), Mapping) else {}
        tone = normalize_quality_tone(quality.get("tone"))
        reasons = [str(item) for item in quality.get("reasons") or [] if str(item)]
        row = {
            "node_id": node_id,
            "tone": tone or "ok",
            "reasons": reasons[:6],
            "artifact_status": quality.get("artifact_status") or artifact.get("status"),
        }
        if tone == "block":
            blockers.append(row)
        elif tone == "warn":
            warnings.append(row)
    return blockers, warnings


def _evidence_posture(
    *,
    artifact_count: int,
    readiness: Mapping[str, Any],
    quality_blockers: Sequence[Mapping[str, Any]],
    quality_warnings: Sequence[Mapping[str, Any]],
    grade: Mapping[str, Any],
) -> dict[str, Any]:
    readiness_ready = readiness.get("present") is True and readiness.get("ready") is True
    grade_token = str(grade.get("grade") or "").strip().lower()
    external_claims_allowed = (
        readiness_ready and not quality_blockers and grade_token in {"green", "ok", "success"}
    )
    if not artifact_count:
        safe_use_level = "no_artifacts"
    elif external_claims_allowed:
        safe_use_level = "run_evidence_ready"
    elif (
        quality_blockers
        or readiness.get("present") is False
        or readiness.get("ready") is False
        or grade_token == "red"
    ):
        safe_use_level = "artifact_specimen_only"
    elif quality_warnings:
        safe_use_level = "controlled_internal_evidence_only"
    else:
        safe_use_level = "controlled_internal_evidence_only"

    return {
        "safe_use_level": safe_use_level,
        "evidence_use": {
            "artifact_specimens_visible": artifact_count > 0,
            "station_display_allowed": artifact_count > 0,
            "readiness_claim_allowed": readiness_ready,
            "proof_montage_allowed": artifact_count > 0,
            "thiel_snapshot_mode": "redacted_or_controlled_specimen" if artifact_count > 0 else "not_eligible",
            "external_market_claims_allowed": external_claims_allowed,
            "trading_or_investment_claims_allowed": False,
        },
        "disclosure_class": "controlled_private_review",
        "thiel_snapshot_eligible": artifact_count > 0,
        "station_display_eligible": artifact_count > 0,
        "proof_montage_eligible": artifact_count > 0,
    }


def build_market_feed_run_evidence_card(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_dir: Path | None = None,
    validation_refs: Iterable[str] = (),
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    run_dir = run_dir or resolve_feed_run_dir(repo_root, run_id)
    runtime_context = _read_json(run_dir / "runtime_context.json")
    source_manifest = feed_source_manifest(repo_root, run_dir)
    artifacts = {
        node_id: _artifact_summary(repo_root, run_dir, node_id)
        for node_id in FEED_NODE_IDS
    }
    present_artifacts = {
        node_id: artifact
        for node_id, artifact in artifacts.items()
        if artifact.get("present") is True
    }
    readiness = _readiness_state(repo_root, run_dir)
    grade = _run_grade(run_dir)
    quality_blockers, quality_warnings = _quality_blockers(present_artifacts)
    blockers: list[dict[str, Any]] = []
    if readiness.get("present") is False:
        blockers.append(
            {
                "kind": "readiness_summary",
                "node_id": "feed_readiness_summary",
                "reason": "feed_readiness_summary_missing",
                "path": readiness.get("path"),
            }
        )
    elif readiness.get("ready") is False:
        for row in readiness.get("blockers") or []:
            if isinstance(row, Mapping):
                blockers.append({"kind": "readiness_summary", **dict(row)})
    blockers.extend({"kind": "artifact_quality", **row} for row in quality_blockers)
    grade_reason = str(grade.get("grade_reason") or "").strip()
    if str(grade.get("grade") or "").strip().lower() == "red" and grade_reason:
        blockers.append({"kind": "run_grade", "grade": grade.get("grade"), "reason": grade_reason})

    posture = _evidence_posture(
        artifact_count=len(present_artifacts),
        readiness=readiness,
        quality_blockers=quality_blockers,
        quality_warnings=quality_warnings,
        grade=grade,
    )
    artifact_rows_by_lane = {
        node_id: int(artifact.get("row_count") or 0)
        for node_id, artifact in present_artifacts.items()
    }
    specimen_rows_by_lane = {
        node_id: artifact.get("specimen_rows") or []
        for node_id, artifact in present_artifacts.items()
    }
    metric_columns_by_lane = {
        node_id: artifact.get("metric_columns") or []
        for node_id, artifact in present_artifacts.items()
    }
    sidecars_by_lane = {
        node_id: artifact.get("sidecar_keys") or []
        for node_id, artifact in present_artifacts.items()
    }
    quality_by_lane = {
        node_id: artifact.get("quality")
        for node_id, artifact in present_artifacts.items()
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_dir.name,
        "as_of": runtime_context.get("as_of") or runtime_context.get("time_anchor"),
        "generated_at": source_manifest["input_watermark"],
        "input_watermark": source_manifest["input_watermark"],
        "source_fingerprint": source_manifest["source_fingerprint"],
        "feed_source_manifest": source_manifest,
        "source_run_dir": _repo_rel(repo_root, run_dir),
        "source_surfaces": {
            "refresh_operator": "tools/finance/refresh_feeds.py",
            "readiness_summary_owner": "run_tools6.py",
            "station_snapshot_owner": "system/server/world_model.py",
            "quality_parser": "system/lib/feed_quality.py",
        },
        "artifact_count": len(present_artifacts),
        "expected_artifact_count": len(FEED_NODE_IDS),
        "artifact_rows_by_lane": artifact_rows_by_lane,
        "artifact_status_by_lane": {
            node_id: artifact.get("status")
            for node_id, artifact in present_artifacts.items()
        },
        "artifact_paths_by_lane": {
            node_id: artifact.get("path")
            for node_id, artifact in present_artifacts.items()
        },
        "specimen_rows_by_lane": specimen_rows_by_lane,
        "metric_columns_by_lane": metric_columns_by_lane,
        "sidecars_by_lane": sidecars_by_lane,
        "sidecar_details_by_lane": {
            node_id: artifact.get("sidecars") or []
            for node_id, artifact in present_artifacts.items()
        },
        "quality_by_lane": quality_by_lane,
        "diagnostics_by_lane": {
            node_id: artifact.get("diagnostics") or {}
            for node_id, artifact in present_artifacts.items()
        },
        "readiness_summary_state": readiness,
        "run_grade": grade,
        "blockers": blockers,
        "warnings": [{"kind": "artifact_quality", **row} for row in quality_warnings],
        **posture,
        "refresh_command_used": "./repo-env ./repo-python tools/finance/refresh_feeds.py refresh",
        "validation_refs": list(validation_refs),
        "consumer_contract": {
            "artifact_present_is_not_readiness": True,
            "specimen_visible_is_not_external_claim": True,
            "missing_readiness_blocks_stronger_claims": readiness.get("present") is False,
            "quality_blockers_remain_visible": bool(quality_blockers),
        },
    }


def render_evidence_card(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_market_feed_run_evidence_card(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_dir: Path | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    latest_filename: str = DEFAULT_LATEST_FILENAME,
    validation_refs: Iterable[str] = (),
) -> dict[str, Any]:
    payload = build_market_feed_run_evidence_card(
        repo_root,
        run_id=run_id,
        run_dir=run_dir,
        validation_refs=validation_refs,
    )
    root = report_root if report_root.is_absolute() else repo_root / report_root
    run_output = root / str(payload["run_id"]) / CARD_FILENAME
    latest_output = root / latest_filename
    _write_json(run_output, payload)
    _write_json(latest_output, payload)
    return payload
