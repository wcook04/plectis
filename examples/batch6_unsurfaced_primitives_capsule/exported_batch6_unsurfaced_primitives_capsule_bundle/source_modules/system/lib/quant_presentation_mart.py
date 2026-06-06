"""
[PURPOSE]
- Teleology: Compile a green market-feed run into a backend-owned quant
  presentation mart: ranked observations, coverage/freshness, provider drift,
  macro/event boards, panel contracts, and source lineage for future Station
  consumers.
- Mechanism: Reuse the feed evidence card and cross-feed readiness gate, then
  deterministically project feed artifacts into dashboard-ready JSON without
  making trading or investment claims.
- Non-goal: This is not an alpha engine, not a frontend layout contract, and
  not a replacement for feed readiness or the market-fusion refusal gate.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib.market_feed_run_evidence import (
    FEED_NODE_IDS,
    build_market_feed_run_evidence_card,
    feed_source_manifest,
    resolve_feed_run_dir,
)
from system.lib.market_fusion_readiness import build_readiness_gate
from system.lib.finance_numeric_assurance import blocking_numeric_contract_errors


SCHEMA_VERSION = "quant_presentation_mart_v0_1"
RUN_ARTIFACT_FILENAME = "quant_presentation_mart.json"
REPORT_FILENAME = "quant_presentation_mart_v0_1.json"
DEFAULT_REPORT_ROOT = Path("state/reports/market_feeds")
DEFAULT_LATEST_FILENAME = "latest_quant_presentation_mart.json"

CLAIM_LEVEL = "salience_observation"
DISPLAY_READY = "ready"
DISPLAY_DEGRADED = "degraded"
DISPLAY_SUPPRESSED = "suppressed"

FEATURE_FAMILIES: frozenset[str] = frozenset(
    {
        "coverage",
        "liquidity",
        "price_action",
        "macro_regime",
        "event_market",
        "news",
        "provider_drift",
        "stockgrid_flow",
        "missingness",
    }
)

FEED_LABELS: Mapping[str, str] = {
    "global_stock_feed": "Equities",
    "global_etf_feed": "ETFs",
    "global_macro_feed": "Macro",
    "global_news_feed": "News",
    "global_polymarket_feed": "Prediction markets",
    "global_stockgrid_feed": "Stockgrid",
    "global_calculator_feed": "Calculator",
}


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
    path.write_text(render_quant_presentation_mart(payload), encoding="utf-8")


def _run_mtime_iso(run_dir: Path) -> str:
    newest = run_dir.stat().st_mtime
    for path in run_dir.rglob("*"):
        if path.is_dir():
            continue
        if path.name == RUN_ARTIFACT_FILENAME:
            continue
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return datetime.fromtimestamp(newest, tz=timezone.utc).replace(microsecond=0).isoformat()


def _stable_slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9._:-]+", "-", text)
    return text.strip("-") or "unknown"


def _compact_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return round(value, 6)
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if len(text) <= 180 else f"{text[:177]}..."
    return str(value)[:180]


def _float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    try:
        number = float(str(value).strip())
    except Exception:
        return None
    return number if math.isfinite(number) else None


def _table_candidates(data: Any) -> list[tuple[str, list[Any], list[Any]]]:
    tables: list[tuple[str, list[Any], list[Any]]] = []

    def visit(value: Any, path: str, depth: int) -> None:
        if depth > 5:
            return
        if isinstance(value, Mapping):
            columns = value.get("columns")
            rows = value.get("rows")
            if isinstance(columns, list) and isinstance(rows, list):
                tables.append((path or "data", columns, rows))
            # v0.10.2: list-of-record shape (data.items used by the news
            # lane and any future list-of-record artifact). Synthesize
            # columns from the union of keys in the first few items so
            # downstream row-count + column-count surfaces report
            # meaningful values, and _row_dicts can iterate items as
            # Mappings without column-positional lookup.
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
                if isinstance(child, (Mapping, list)):
                    child_path = f"{path}.{key}" if path else str(key)
                    visit(child, child_path, depth + 1)
        elif isinstance(value, list):
            for index, child in enumerate(value[:100]):
                if isinstance(child, (Mapping, list)):
                    visit(child, f"{path}[{index}]" if path else f"[{index}]", depth + 1)

    visit(data, "", 0)
    tables.sort(key=lambda item: len(item[2]), reverse=True)
    return tables


def _row_dicts(payload: Mapping[str, Any], *, limit: int | None = None) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    data_schema_version = str(metadata.get("data_schema_version") or "")
    tool = str(metadata.get("tool") or "")
    for table_path, columns, rows in _table_candidates(payload.get("data")):
        column_names = [str(column) for column in columns]
        for row in rows:
            if limit is not None and len(rows_out) >= limit:
                return rows_out
            if isinstance(row, Mapping):
                mapped = {str(key): _compact_value(value) for key, value in row.items()}
            elif isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
                mapped = {
                    column: _compact_value(row[index] if index < len(row) else None)
                    for index, column in enumerate(column_names)
                }
            else:
                continue
            mapped["_table_path"] = table_path
            if data_schema_version:
                mapped["_data_schema_version"] = data_schema_version
            if tool:
                mapped["_tool"] = tool
            rows_out.append(mapped)
    return rows_out


def _artifact_path(run_dir: Path, node_id: str) -> Path:
    return run_dir / "artifacts" / f"{node_id}.json"


def _artifact_payloads(run_dir: Path) -> dict[str, dict[str, Any]]:
    return {node_id: _read_json(_artifact_path(run_dir, node_id)) for node_id in FEED_NODE_IDS}


def _artifact_rows_by_node(artifacts: Mapping[str, Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {node_id: _row_dicts(payload) for node_id, payload in artifacts.items() if payload}


def _source_ref(repo_root: Path, run_dir: Path, node_id: str) -> str:
    return _repo_rel(repo_root, _artifact_path(run_dir, node_id))


def _source_ref_obj(
    repo_root: Path,
    run_dir: Path,
    node_id: str,
    *,
    table_path: str | None = None,
    row_selector: Mapping[str, Any] | None = None,
    field_refs: Sequence[str] = (),
    kind: str = "feed_artifact",
) -> dict[str, Any]:
    row = {
        "kind": kind,
        "feed_id": node_id,
        "path": _source_ref(repo_root, run_dir, node_id),
    }
    if table_path:
        row["table_path"] = table_path
    if row_selector:
        row["row_selector"] = {str(key): _compact_value(value) for key, value in row_selector.items()}
    if field_refs:
        row["field_refs"] = [str(item) for item in field_refs if str(item)]
    return row


def _typed_source_ref(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        path = str(value.get("path") or "").strip()
        kind = str(value.get("kind") or "feed_artifact").strip()
        if not path:
            return None
        row = dict(value)
        row["kind"] = kind
        row["path"] = path
        return row
    text = str(value or "").strip()
    if not text:
        return None
    return {"kind": "artifact_ref", "path": text}


def _typed_source_refs(values: Sequence[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        row = _typed_source_ref(value)
        if not row:
            continue
        key = json.dumps(row, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _quality_score(tone: Any) -> float:
    token = str(tone or "ok").strip().lower()
    if token == "ok":
        return 1.0
    if token == "warn":
        return 0.68
    if token == "block":
        return 0.2
    return 0.55


def _lane_quality(evidence_card: Mapping[str, Any], node_id: str) -> Mapping[str, Any]:
    quality_by_lane = evidence_card.get("quality_by_lane")
    if isinstance(quality_by_lane, Mapping):
        value = quality_by_lane.get(node_id)
        if isinstance(value, Mapping):
            return value
    return {}


def _confidence(
    *,
    tone: Any = "ok",
    freshness: float = 0.85,
    coverage: float = 0.8,
    explainability: float = 0.8,
) -> dict[str, float]:
    return {
        "data_quality": round(_quality_score(tone), 3),
        "freshness": round(max(0.0, min(1.0, freshness)), 3),
        "coverage": round(max(0.0, min(1.0, coverage)), 3),
        "explainability": round(max(0.0, min(1.0, explainability)), 3),
    }


def _score(
    *,
    interestingness: float,
    confidence: Mapping[str, float],
    display_readiness: float,
) -> dict[str, float]:
    confidence_score = sum(float(confidence.get(key, 0.0)) for key in confidence) / max(len(confidence), 1)
    return {
        "interestingness": round(max(0.0, min(1.0, interestingness)), 3),
        "confidence": round(confidence_score, 3),
        "display_readiness": round(max(0.0, min(1.0, display_readiness)), 3),
    }


def _observation(
    *,
    observation_id: str,
    title: str,
    why_interesting: str,
    entities: Sequence[str],
    score: Mapping[str, float],
    reasons: Sequence[str],
    caveats: Sequence[str],
    disconfirming_checks: Sequence[str],
    source_refs: Sequence[Any],
    safe_use_level: str,
    reason_codes: Sequence[str],
    primary_metric: Mapping[str, Any] | None = None,
    supporting_metrics: Sequence[Mapping[str, Any]] = (),
    suppression_reasons: Sequence[str] = (),
    claim_level: str = CLAIM_LEVEL,
    display_state: str = DISPLAY_READY,
) -> dict[str, Any]:
    return {
        "observation_id": observation_id,
        "rank": 0,
        "title": title,
        "why_interesting": why_interesting,
        "entities": list(dict.fromkeys(entities)),
        "score": dict(score),
        "reasons": [str(item) for item in reasons if str(item)],
        "reason_codes": [str(item) for item in reason_codes if str(item)],
        "caveats": [str(item) for item in caveats if str(item)],
        "disconfirming_checks": [str(item) for item in disconfirming_checks if str(item)],
        "source_refs": _typed_source_refs(source_refs),
        "safe_use_level": safe_use_level,
        "claim_level": claim_level,
        "display_state": display_state,
        "suppression_reasons": [str(item) for item in suppression_reasons if str(item)],
        "primary_metric": dict(primary_metric or {}),
        "supporting_metrics": [dict(item) for item in supporting_metrics if isinstance(item, Mapping)],
    }


def _coverage(
    *,
    repo_root: Path,
    run_dir: Path,
    evidence_card: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    artifact_rows = evidence_card.get("artifact_rows_by_lane")
    quality_by_lane = evidence_card.get("quality_by_lane")
    paths_by_lane = evidence_card.get("artifact_paths_by_lane")
    feeds: list[dict[str, Any]] = []
    for node_id in FEED_NODE_IDS:
        payload = artifacts.get(node_id) if isinstance(artifacts.get(node_id), Mapping) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        quality = quality_by_lane.get(node_id) if isinstance(quality_by_lane, Mapping) else {}
        artifact_ref = paths_by_lane.get(node_id) if isinstance(paths_by_lane, Mapping) else None
        feeds.append(
            {
                "feed_id": node_id,
                "label": FEED_LABELS.get(node_id, node_id),
                "rows": int((artifact_rows or {}).get(node_id) or 0) if isinstance(artifact_rows, Mapping) else 0,
                "items_count": metadata.get("items_count"),
                "freshness": metadata.get("as_of") or metadata.get("timestamp_iso") or evidence_card.get("as_of"),
                "quality": (quality or {}).get("tone") or "missing",
                "artifact_ref": artifact_ref or _source_ref(repo_root, run_dir, node_id),
                "metric_columns": (evidence_card.get("metric_columns_by_lane") or {}).get(node_id, [])
                if isinstance(evidence_card.get("metric_columns_by_lane"), Mapping)
                else [],
            }
        )
    return {"feeds": feeds}


def _entities(
    *,
    repo_root: Path,
    run_dir: Path,
    rows_by_node: Mapping[str, Sequence[Mapping[str, Any]]],
    coverage: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    entities: list[dict[str, Any]] = []
    seen: set[str] = set()
    counts = {
        "equities": 0,
        "etfs": 0,
        "macro_series": 0,
        "prediction_markets": 0,
        "news_items": 0,
        "providers": len(FEED_NODE_IDS),
    }

    def add(row: dict[str, Any]) -> None:
        entity_id = str(row.get("entity_id") or "")
        if not entity_id or entity_id in seen:
            return
        seen.add(entity_id)
        entities.append(row)

    for node_id, entity_type, count_key in (
        ("global_stock_feed", "equity", "equities"),
        ("global_etf_feed", "etf", "etfs"),
    ):
        for row in rows_by_node.get(node_id, []):
            ticker = str(row.get("Ticker") or "").strip()
            if not ticker:
                continue
            counts[count_key] += 1
            identity = str(row.get("Identity") or ticker).split(" | ")[0]
            add(
                {
                    "entity_id": f"{entity_type}:{ticker}",
                    "entity_type": entity_type,
                    "display_name": identity,
                    "symbols": [ticker],
                    "source_refs": [
                        _source_ref_obj(
                            repo_root,
                            run_dir,
                            node_id,
                            row_selector={"Ticker": ticker},
                            field_refs=["Ticker", "Identity", "Category"],
                        )
                    ],
                    "quality": {"lane": node_id, "category": row.get("Category")},
                }
            )

    for row in rows_by_node.get("global_macro_feed", []):
        ticker = str(row.get("ticker") or row.get("Series") or "").strip()
        if not ticker:
            continue
        counts["macro_series"] += 1
        add(
            {
                "entity_id": f"macro_series:{_stable_slug(ticker)}",
                "entity_type": "macro_series",
                "display_name": ticker,
                "symbols": [ticker],
                "source_refs": [
                    _source_ref_obj(
                        repo_root,
                        run_dir,
                        "global_macro_feed",
                        row_selector={"ticker": ticker},
                        field_refs=["ticker", "Proxy", "z_score", "recent_change"],
                    )
                ],
                "quality": {"proxy": row.get("Proxy"), "error": row.get("error")},
            }
        )

    for row in rows_by_node.get("global_polymarket_feed", []):
        slug = str(row.get("slug") or "").strip()
        question = str(row.get("q") or row.get("question") or slug).strip()
        if not slug and not question:
            continue
        counts["prediction_markets"] += 1
        key = slug or question
        add(
            {
                "entity_id": f"prediction_market:{_stable_slug(key)}",
                "entity_type": "prediction_market",
                "display_name": question or key,
                "symbols": [],
                "source_refs": [
                    _source_ref_obj(
                        repo_root,
                        run_dir,
                        "global_polymarket_feed",
                        table_path=str(row.get("_table_path") or ""),
                        row_selector={"slug": slug or None, "q": question or None},
                        field_refs=["q", "o", "p", "c", "v", "s", "slug"],
                    )
                ],
                "quality": {"topic": row.get("_table_path"), "outcome": row.get("o")},
            }
        )

    for row in rows_by_node.get("global_news_feed", []):
        title = str(row.get("title") or row.get("headline") or row.get("q") or "").strip()
        url = str(row.get("url") or row.get("link") or "").strip()
        if not title and not url:
            continue
        counts["news_items"] += 1
        add(
            {
                "entity_id": f"news_item:{_stable_slug(url or title)}",
                "entity_type": "news_item",
                "display_name": title or url,
                "symbols": [],
                "source_refs": [
                    _source_ref_obj(
                        repo_root,
                        run_dir,
                        "global_news_feed",
                        row_selector={"url": url or None, "title": title or None},
                        field_refs=["title", "source", "url", "published_at"],
                    )
                ],
                "quality": {"source": row.get("source"), "published_at": row.get("published_at")},
            }
        )

    for feed in coverage.get("feeds") or []:
        if not isinstance(feed, Mapping):
            continue
        node_id = str(feed.get("feed_id") or "")
        add(
            {
                "entity_id": f"provider:{node_id}",
                "entity_type": "provider",
                "display_name": str(feed.get("label") or node_id),
                "symbols": [],
                "source_refs": _typed_source_refs([feed.get("artifact_ref")]),
                "quality": {"tone": feed.get("quality"), "rows": feed.get("rows")},
            }
        )

    return entities, counts


def _top_numeric_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric: str,
    limit: int = 8,
    absolute: bool = True,
) -> list[Mapping[str, Any]]:
    def key(row: Mapping[str, Any]) -> float:
        value = _float(row.get(metric))
        if value is None:
            return -1.0
        return abs(value) if absolute else value

    return sorted(rows, key=key, reverse=True)[:limit]


def _stockgrid_flow_score(row: Mapping[str, Any]) -> float:
    value = _stockgrid_flow_usd(row)
    if value is not None:
        return abs(value)
    conv = _float(row.get("conv"))
    sv = _float(row.get("sv"))
    return abs(conv or sv or 0.0)


def _has_stockgrid_value(value: Any) -> bool:
    return value not in (None, "", [], {})


def _stockgrid_flow_is_usd_millions(row: Mapping[str, Any]) -> bool:
    schema = str(row.get("_data_schema_version") or "").strip().lower()
    return schema.startswith("stockgrid.2") and str(row.get("_table_path") or "") == "data"


def _stockgrid_flow_usd(row: Mapping[str, Any]) -> float | None:
    cached = _float(row.get("_normalized_flow_usd"))
    if cached is not None:
        return cached
    direct = _float(row.get("flow_usd"))
    if direct is not None:
        return direct
    flow = _float(row.get("flow"))
    if flow is not None:
        if _stockgrid_flow_is_usd_millions(row):
            return flow * 1_000_000.0
        return flow
    return _float(row.get("net_usd"))


def _stockgrid_detail_score(row: Mapping[str, Any]) -> tuple[int, float]:
    fields = ("company", "sector", "dir", "flow_usd", "net_usd", "conv", "sv", "wr", "flow")
    present = sum(1 for key in fields if _has_stockgrid_value(row.get(key)))
    direct_usd = 1 if _float(row.get("flow_usd")) is not None else 0
    return (present + direct_usd * 3, _stockgrid_flow_score(row))


def _merge_stockgrid_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=_stockgrid_detail_score, reverse=True)
    merged = dict(ordered[0])
    source_table_paths: list[str] = []
    source_field_refs: list[str] = []
    for row in ordered:
        table_path = str(row.get("_table_path") or "")
        if table_path and table_path not in source_table_paths:
            source_table_paths.append(table_path)
        for key in ("tkr", "flow", "flow_usd", "net_usd", "sv", "wr", "flg", "sec", "sector", "company", "dir", "conv"):
            if _has_stockgrid_value(row.get(key)) and key not in source_field_refs:
                source_field_refs.append(key)
            if not _has_stockgrid_value(merged.get(key)) and _has_stockgrid_value(row.get(key)):
                merged[key] = row.get(key)
        # Rich side datasets carry exact USD plus identity/conviction fields;
        # compact stockgrid.2 data rows carry compatibility flow in USD millions.
        for key in ("flow_usd", "net_usd", "sector", "company", "dir", "conv"):
            if _has_stockgrid_value(row.get(key)):
                merged[key] = row.get(key)
        if _stockgrid_flow_is_usd_millions(row):
            merged["_flow_unit"] = "usd_millions"

    normalized = _stockgrid_flow_usd(merged)
    if normalized is None:
        for row in ordered:
            normalized = _stockgrid_flow_usd(row)
            if normalized is not None:
                break
    if normalized is not None:
        merged["_normalized_flow_usd"] = normalized
        if _float(merged.get("flow_usd")) is None:
            merged["flow_usd"] = normalized
    merged["_source_table_paths"] = source_table_paths or [str(merged.get("_table_path") or "")]
    merged["_source_field_refs"] = source_field_refs or ["tkr", "flow", "flow_usd", "net_usd", "conv", "sv", "wr", "flg"]
    return merged


def _top_stockgrid_flow_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 16) -> list[Mapping[str, Any]]:
    candidates = [
        row
        for row in rows
        if str(row.get("tkr") or "").strip()
        and any(_float(row.get(key)) is not None for key in ("flow_usd", "net_usd", "flow", "conv", "sv"))
    ]
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in candidates:
        grouped.setdefault(str(row.get("tkr") or "").strip(), []).append(row)
    merged = [_merge_stockgrid_rows(group_rows) for group_rows in grouped.values()]
    return sorted(merged, key=_stockgrid_flow_score, reverse=True)[:limit]


def _stockgrid_source_refs(
    *,
    repo_root: Path,
    run_dir: Path,
    row: Mapping[str, Any],
    ticker: str,
) -> list[dict[str, Any]]:
    table_paths = [
        str(path)
        for path in (row.get("_source_table_paths") if isinstance(row.get("_source_table_paths"), list) else [])
        if str(path)
    ] or [str(row.get("_table_path") or "")]
    field_refs = [
        str(field)
        for field in (row.get("_source_field_refs") if isinstance(row.get("_source_field_refs"), list) else [])
        if str(field)
    ] or ["tkr", "flow", "flow_usd", "net_usd", "conv", "sv", "wr", "flg"]
    return [
        _source_ref_obj(
            repo_root,
            run_dir,
            "global_stockgrid_feed",
            table_path=table_path,
            row_selector={"tkr": ticker},
            field_refs=field_refs,
        )
        for table_path in table_paths
    ]



def _feature_rows(
    *,
    repo_root: Path,
    run_dir: Path,
    evidence_card: Mapping[str, Any],
    rows_by_node: Mapping[str, Sequence[Mapping[str, Any]]],
    coverage: Mapping[str, Any],
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    computed_at = str(evidence_card.get("generated_at") or evidence_card.get("as_of") or "")

    for feed in coverage.get("feeds") or []:
        if not isinstance(feed, Mapping):
            continue
        node_id = str(feed.get("feed_id") or "")
        conf = _confidence(tone=feed.get("quality"), coverage=1.0 if feed.get("rows") else 0.2)
        features.append(
            {
                "entity_id": f"provider:{node_id}",
                "feature_family": "coverage",
                "metrics": {
                    "rows": feed.get("rows"),
                    "items_count": feed.get("items_count"),
                    "quality": feed.get("quality"),
                },
                "computed_at": computed_at,
                "source_refs": _typed_source_refs([feed.get("artifact_ref")]),
                "confidence": conf,
            }
        )

    for node_id, entity_prefix in (
        ("global_stock_feed", "equity"),
        ("global_etf_feed", "etf"),
    ):
        quality = _lane_quality(evidence_card, node_id)
        for row in _top_numeric_rows(rows_by_node.get(node_id, []), metric="Chg_5d", limit=12):
            ticker = str(row.get("Ticker") or "").strip()
            if not ticker:
                continue
            features.append(
                {
                    "entity_id": f"{entity_prefix}:{ticker}",
                    "feature_family": "price_action",
                    "metrics": {
                        "chg_5d": _float(row.get("Chg_5d")),
                        "chg_63d": _float(row.get("Chg_63d")),
                        "z_short": _float(row.get("Z_Short")),
                        "z_long": _float(row.get("Z_Long")),
                        "vol_20d": _float(row.get("Vol_20d")),
                    },
                    "computed_at": computed_at,
                    "source_refs": [
                        _source_ref_obj(
                            repo_root,
                            run_dir,
                            node_id,
                            row_selector={"Ticker": ticker},
                            field_refs=["Chg_5d", "Chg_63d", "Z_Short", "Z_Long", "Vol_20d"],
                        )
                    ],
                    "confidence": _confidence(tone=quality.get("tone"), explainability=0.7),
                }
            )

    macro_quality = _lane_quality(evidence_card, "global_macro_feed")
    for row in _top_numeric_rows(rows_by_node.get("global_macro_feed", []), metric="z_score", limit=16):
        ticker = str(row.get("ticker") or "").strip()
        if not ticker:
            continue
        features.append(
            {
                "entity_id": f"macro_series:{_stable_slug(ticker)}",
                "feature_family": "macro_regime",
                "metrics": {
                    "proxy": row.get("Proxy"),
                    "recent_change": _float(row.get("recent_change")),
                    "pct_change": _float(row.get("pct_change")),
                    "z_score": _float(row.get("z_score")),
                    "risk_d2": _float(row.get("risk_d2")),
                    },
                    "computed_at": computed_at,
                    "source_refs": [
                        _source_ref_obj(
                            repo_root,
                            run_dir,
                            "global_macro_feed",
                            row_selector={"ticker": ticker},
                            field_refs=["ticker", "Proxy", "z_score", "risk_d2", "recent_change"],
                        )
                    ],
                    "confidence": _confidence(tone=macro_quality.get("tone"), explainability=0.75),
                }
            )

    poly_quality = _lane_quality(evidence_card, "global_polymarket_feed")
    for row in _top_numeric_rows(rows_by_node.get("global_polymarket_feed", []), metric="v", limit=16, absolute=False):
        slug = str(row.get("slug") or row.get("q") or "").strip()
        if not slug:
            continue
        features.append(
            {
                "entity_id": f"prediction_market:{_stable_slug(slug)}",
                "feature_family": "event_market",
                "metrics": {
                    "probability": _float(row.get("p")),
                    "change": _float(row.get("c")),
                    "volume": _float(row.get("v")),
                    "spread": _float(row.get("s")),
                    "outcome": row.get("o"),
                    "topic": row.get("_table_path"),
                    },
                    "computed_at": computed_at,
                    "source_refs": [
                        _source_ref_obj(
                            repo_root,
                            run_dir,
                            "global_polymarket_feed",
                            table_path=str(row.get("_table_path") or ""),
                            row_selector={"slug": slug},
                            field_refs=["p", "c", "v", "s", "o"],
                        )
                    ],
                "confidence": _confidence(tone=poly_quality.get("tone"), explainability=0.74),
            }
        )

    stockgrid_quality = _lane_quality(evidence_card, "global_stockgrid_feed")
    for row in _top_stockgrid_flow_rows(rows_by_node.get("global_stockgrid_feed", []), limit=16):
        ticker = str(row.get("tkr") or "").strip()
        features.append(
            {
                "entity_id": f"equity:{ticker}",
                "feature_family": "stockgrid_flow",
                "metrics": {
                    "ticker": ticker,
                    "sector": row.get("sector") or row.get("sec"),
                    "company": row.get("company"),
                    "direction": row.get("dir"),
                    "flow": _float(row.get("flow")),
                    "flow_usd": _float(row.get("flow_usd")),
                    "net_usd": _float(row.get("net_usd")),
                    "conviction": _float(row.get("conv")),
                    "signal_value": _float(row.get("sv")),
                    "win_rate": _float(row.get("wr")),
                    "flag": row.get("flg"),
                    "flow_unit": row.get("_flow_unit") or "usd",
                    "score": round(_stockgrid_flow_score(row), 6),
                },
                "computed_at": computed_at,
                "source_refs": _stockgrid_source_refs(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    row=row,
                    ticker=ticker,
                ),
                "confidence": _confidence(tone=stockgrid_quality.get("tone"), explainability=0.82),
            }
        )

    return features


def _macro_bucket(row: Mapping[str, Any]) -> str:
    text = f"{row.get('ticker') or ''} {row.get('Proxy') or ''}".lower()
    if any(token in text for token in ("cpi", "ppi", "pce", "inflation", "price")):
        return "inflation"
    if any(token in text for token in ("rate", "yield", "fed", "sofr", "effr", "mortgage")):
        return "rates"
    if any(token in text for token in ("labor", "job", "claims", "unemployment", "payroll")):
        return "labor"
    if any(token in text for token in ("gdp", "growth", "industrial", "sales", "pmi")):
        return "growth"
    if any(token in text for token in ("credit", "spread", "loan", "delinq", "debt")):
        return "credit"
    if any(token in text for token in ("oil", "gas", "energy", "wti")):
        return "energy"
    if any(token in text for token in ("housing", "consumer", "saving", "income")):
        return "housing_consumer"
    return "other"


def _macro_lifecycle_by_slug(macro_artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    metadata = macro_artifact.get("metadata") if isinstance(macro_artifact.get("metadata"), Mapping) else {}
    sidecars = metadata.get("sidecars") if isinstance(metadata.get("sidecars"), Mapping) else {}
    lifecycle = sidecars.get("macro_lifecycle_snapshot") if isinstance(sidecars.get("macro_lifecycle_snapshot"), Mapping) else {}
    by_slug: dict[str, Mapping[str, Any]] = {}
    for row in lifecycle.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug") or "").strip()
        if slug:
            by_slug[slug] = row
    return by_slug


def _macro_regime_board(
    rows: Sequence[Mapping[str, Any]],
    *,
    macro_artifact: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    lifecycle_by_slug = _macro_lifecycle_by_slug(macro_artifact or {})
    for row in rows:
        buckets.setdefault(_macro_bucket(row), []).append(row)
    board: list[dict[str, Any]] = []
    for bucket, bucket_rows in sorted(buckets.items()):
        scored = [(_float(row.get("z_score")) or 0.0, row) for row in bucket_rows]
        avg_z = sum(score for score, _row in scored) / max(len(scored), 1)
        top = sorted(scored, key=lambda item: abs(item[0]), reverse=True)[:5]
        lifecycle_rows = [lifecycle_by_slug.get(str(row.get("ticker") or "")) for row in bucket_rows]
        lifecycle_rows = [row for row in lifecycle_rows if isinstance(row, Mapping)]
        vintage_available = any(
            ((row.get("components") or {}).get("vintage_metadata_present") is True)
            for row in lifecycle_rows
            if isinstance(row.get("components"), Mapping)
        )
        release_calendar_available = any(
            bool((row.get("components") or {}).get("latest_observation_date"))
            for row in lifecycle_rows
            if isinstance(row.get("components"), Mapping)
        )
        board.append(
            {
                "bucket": bucket,
                "series_count": len(bucket_rows),
                "average_z_score": round(avg_z, 4),
                "vintage_status": "available" if vintage_available else "missing_from_feed_artifact",
                "release_calendar_status": "available" if release_calendar_available else "missing_from_feed_artifact",
                "interpretation_level": "series_observation_summary",
                "top_series": [
                    {
                        "entity_id": f"macro_series:{_stable_slug(row.get('ticker'))}",
                        "ticker": row.get("ticker"),
                        "proxy": row.get("Proxy"),
                        "z_score": _float(row.get("z_score")),
                        "recent_change": _float(row.get("recent_change")),
                        "latest_observation_date": (
                            (((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components") or {}).get("latest_observation_date"))
                            if isinstance((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components"), Mapping)
                            else None
                        ),
                        "realtime_start": (
                            (((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components") or {}).get("realtime_start"))
                            if isinstance((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components"), Mapping)
                            else None
                        ),
                        "realtime_end": (
                            (((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components") or {}).get("realtime_end"))
                            if isinstance((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components"), Mapping)
                            else None
                        ),
                    }
                    for _score, row in top
                ],
            }
        )
    return sorted(board, key=lambda row: abs(float(row.get("average_z_score") or 0.0)), reverse=True)


def _polymarket_identity_by_slug(polymarket_artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    metadata = polymarket_artifact.get("metadata") if isinstance(polymarket_artifact.get("metadata"), Mapping) else {}
    sidecars = metadata.get("sidecars") if isinstance(metadata.get("sidecars"), Mapping) else {}
    identity = sidecars.get("polymarket_market_identity_snapshot")
    rows = identity.get("rows") if isinstance(identity, Mapping) else []
    by_slug: dict[str, Mapping[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("market_slug") or "").strip()
        if slug:
            by_slug[slug] = row
    return by_slug


def _prediction_market_board(
    rows: Sequence[Mapping[str, Any]],
    *,
    polymarket_artifact: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    identity_by_slug = _polymarket_identity_by_slug(polymarket_artifact or {})
    events: dict[str, dict[str, Any]] = {}
    for row in rows:
        slug = str(row.get("slug") or "").strip()
        question = str(row.get("q") or slug).strip()
        key = slug or question
        if not key:
            continue
        identity = identity_by_slug.get(slug)
        event_key = (
            str(identity.get("event_id") or identity.get("event_slug") or "").strip()
            if isinstance(identity, Mapping)
            else ""
        ) or key
        event = events.setdefault(
            event_key,
            {
                "entity_id": f"prediction_market_event:{_stable_slug(event_key)}",
                "event_id": identity.get("event_id") if isinstance(identity, Mapping) else None,
                "event_slug": identity.get("event_slug") if isinstance(identity, Mapping) else None,
                "event_title": identity.get("event_title") if isinstance(identity, Mapping) else question,
                "event_identity_status": "available" if isinstance(identity, Mapping) else "missing_from_feed_artifact",
                "markets": [],
                "aggregate": {
                    "max_volume": 0.0,
                    "market_count": 0,
                    "largest_probability_move": 0.0,
                    "max_liquidity": 0.0,
                },
                "topic": row.get("_table_path"),
            },
        )
        probability = _float(row.get("p"))
        probability_change = _float(row.get("c"))
        volume = _float(row.get("v")) or 0.0
        spread = _float(row.get("s"))
        liquidity = _float(identity.get("liquidity")) if isinstance(identity, Mapping) else None
        market = {
            "market_id": identity.get("market_id") if isinstance(identity, Mapping) else None,
            "market_slug": slug or (identity.get("market_slug") if isinstance(identity, Mapping) else None),
            "question": identity.get("market_question") if isinstance(identity, Mapping) else question,
            "outcome": row.get("o"),
            "probability": probability,
            "probability_change": probability_change,
            "volume": volume,
            "spread": spread,
            "liquidity": liquidity,
            "end_date_iso": identity.get("end_date_iso") if isinstance(identity, Mapping) else None,
            "lifecycle_state": ((identity.get("lifecycle") or {}).get("state") if isinstance(identity.get("lifecycle"), Mapping) else None)
            if isinstance(identity, Mapping)
            else None,
        }
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(event["markets"])
                if existing.get("market_slug") == market.get("market_slug")
                and existing.get("outcome") == market.get("outcome")
            ),
            None,
        )
        if duplicate_index is not None:
            if float(market.get("volume") or 0.0) > float(event["markets"][duplicate_index].get("volume") or 0.0):
                event["markets"][duplicate_index] = market
        else:
            event["markets"].append(market)
        aggregate = event["aggregate"]
        aggregate["max_volume"] = max(float(aggregate.get("max_volume") or 0.0), volume)
        aggregate["largest_probability_move"] = max(
            float(aggregate.get("largest_probability_move") or 0.0),
            abs(probability_change or 0.0),
        )
        aggregate["max_liquidity"] = max(float(aggregate.get("max_liquidity") or 0.0), liquidity or 0.0)
    for event in events.values():
        event["markets"].sort(key=lambda market: float(market.get("volume") or 0.0), reverse=True)
        event["markets"] = event["markets"][:12]
        event["aggregate"]["market_count"] = len(event["markets"])
        top_market = event["markets"][0] if event["markets"] else {}
        event["slug"] = top_market.get("market_slug")
        event["question"] = event.get("event_title") or top_market.get("question")
        event["probability"] = top_market.get("probability")
        event["probability_change"] = top_market.get("probability_change")
        event["volume"] = event["aggregate"]["max_volume"]
        event["spread"] = top_market.get("spread")
    return sorted(
        events.values(),
        key=lambda event: float((event.get("aggregate") or {}).get("max_volume") or 0.0),
        reverse=True,
    )[:25]


def _provider_drift_monitor(
    *,
    repo_root: Path,
    run_dir: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
    evidence_card: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node_id in FEED_NODE_IDS:
        payload = artifacts.get(node_id) if isinstance(artifacts.get(node_id), Mapping) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        diagnostics = metadata.get("diagnostics") if isinstance(metadata.get("diagnostics"), Mapping) else {}
        quality = _lane_quality(evidence_card, node_id)
        drift_flags: list[str] = []
        if diagnostics.get("provider_fallback_used") is True:
            drift_flags.append("provider_fallback_used")
        if int(diagnostics.get("html_response_count") or 0):
            drift_flags.append("html_response_seen")
        fred = diagnostics.get("fred") if isinstance(diagnostics.get("fred"), Mapping) else {}
        if int(fred.get("invalid_series_count") or 0):
            drift_flags.append("fred_invalid_series")
        if int(fred.get("network_warn_count") or 0):
            drift_flags.append("fred_network_warning")
        if int(diagnostics.get("fetch_failure_count") or 0):
            drift_flags.append("fetch_failures")
        rows.append(
            {
                "provider_id": node_id,
                "label": FEED_LABELS.get(node_id, node_id),
                "quality_tone": quality.get("tone") or "missing",
                "row_count": (evidence_card.get("artifact_rows_by_lane") or {}).get(node_id)
                if isinstance(evidence_card.get("artifact_rows_by_lane"), Mapping)
                else None,
                "drift_flags": drift_flags,
                "provider_mode": diagnostics.get("provider_mode"),
                "provider_used": diagnostics.get("provider_used"),
                "fallback_used": diagnostics.get("provider_fallback_used"),
                "html_response_count": diagnostics.get("html_response_count"),
                "fetch_success_count": diagnostics.get("fetch_success_count")
                or fred.get("fetch_success_count"),
                "fetch_failure_count": diagnostics.get("fetch_failure_count")
                or fred.get("fetch_failure_count"),
                "fetch_success_rate": diagnostics.get("fetch_success_rate")
                or fred.get("fetch_success_rate"),
                "fred_invalid_series_count": fred.get("invalid_series_count"),
                "fred_network_warn_count": fred.get("network_warn_count"),
                "drift_events": [
                    {
                        "event_type": flag,
                        "severity": "warn",
                        "first_seen_run_id": None,
                        "current_run_id": run_dir.name,
                        "resolved": False,
                    }
                    for flag in drift_flags
                ],
                "source_refs": [
                    _source_ref_obj(
                        repo_root,
                        run_dir,
                        node_id,
                        field_refs=[
                            "metadata.diagnostics.provider_mode",
                            "metadata.diagnostics.provider_fallback_used",
                            "metadata.diagnostics.html_response_count",
                            "metadata.diagnostics.fetch_success_rate",
                        ],
                    )
                ],
            }
        )
    return rows


def _stockgrid_flow_board(
    *,
    repo_root: Path,
    run_dir: Path,
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    board: list[dict[str, Any]] = []
    for row in _top_stockgrid_flow_rows(rows, limit=25):
        ticker = str(row.get("tkr") or "").strip()
        if not ticker:
            continue
        board.append(
            {
                "entity_id": f"equity:{ticker}",
                "ticker": ticker,
                "company": row.get("company"),
                "sector": row.get("sector") or row.get("sec"),
                "direction": row.get("dir"),
                "flow": _float(row.get("flow")),
                "flow_usd": _float(row.get("flow_usd")),
                "net_usd": _float(row.get("net_usd")),
                "conviction": _float(row.get("conv")),
                "signal_value": _float(row.get("sv")),
                "win_rate": _float(row.get("wr")),
                "flag": row.get("flg"),
                "flow_score": round(_stockgrid_flow_score(row), 6),
                "flow_unit": row.get("_flow_unit") or "usd",
                "claim_level": CLAIM_LEVEL,
                "source_refs": _stockgrid_source_refs(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    row=row,
                    ticker=ticker,
                ),
            }
        )
    return board


def _is_green_feed_run(repo_root: Path, run_dir: Path) -> bool:
    try:
        card = build_market_feed_run_evidence_card(repo_root, run_dir=run_dir)
    except Exception:
        return False
    grade = card.get("run_grade") if isinstance(card.get("run_grade"), Mapping) else {}
    return (
        card.get("safe_use_level") == "run_evidence_ready"
        and str(grade.get("grade") or "").strip().lower() == "green"
    )


def _previous_green_run(repo_root: Path, current_run_dir: Path) -> Path | None:
    runs_dir = current_run_dir.parent
    if not runs_dir.exists():
        return None
    current_resolved = current_run_dir.resolve()
    candidates = [path for path in runs_dir.iterdir() if path.is_dir() and path.resolve() != current_resolved]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for candidate in candidates[:80]:
        if _is_green_feed_run(repo_root, candidate):
            return candidate
    return None


def _delta_since_previous_green(
    *,
    repo_root: Path,
    run_dir: Path,
    evidence_card: Mapping[str, Any],
) -> dict[str, Any]:
    previous = _previous_green_run(repo_root, run_dir)
    if previous is None:
        return {
            "status": "unavailable",
            "reason": "no_previous_green_feed_run_found",
            "previous_run_id": None,
            "row_deltas_by_lane": {},
            "quality_changes": [],
        }
    previous_card = build_market_feed_run_evidence_card(repo_root, run_dir=previous)
    current_rows = evidence_card.get("artifact_rows_by_lane") if isinstance(evidence_card.get("artifact_rows_by_lane"), Mapping) else {}
    previous_rows = previous_card.get("artifact_rows_by_lane") if isinstance(previous_card.get("artifact_rows_by_lane"), Mapping) else {}
    row_deltas = {
        node_id: int(current_rows.get(node_id) or 0) - int(previous_rows.get(node_id) or 0)
        for node_id in FEED_NODE_IDS
    }
    current_quality = evidence_card.get("quality_by_lane") if isinstance(evidence_card.get("quality_by_lane"), Mapping) else {}
    previous_quality = previous_card.get("quality_by_lane") if isinstance(previous_card.get("quality_by_lane"), Mapping) else {}
    quality_changes = []
    for node_id in FEED_NODE_IDS:
        current_tone = ((current_quality.get(node_id) or {}).get("tone") if isinstance(current_quality.get(node_id), Mapping) else None)
        previous_tone = ((previous_quality.get(node_id) or {}).get("tone") if isinstance(previous_quality.get(node_id), Mapping) else None)
        if current_tone != previous_tone:
            quality_changes.append(
                {
                    "feed_id": node_id,
                    "previous_tone": previous_tone,
                    "current_tone": current_tone,
                }
            )
    return {
        "status": "computed",
        "previous_run_id": previous.name,
        "previous_evidence_card": _repo_rel(
            repo_root,
            DEFAULT_REPORT_ROOT / previous.name / "market_feed_run_evidence_card_v0.json",
        ),
        "row_deltas_by_lane": row_deltas,
        "quality_changes": quality_changes,
    }


def _ranked_observations(
    *,
    repo_root: Path,
    run_dir: Path,
    evidence_card: Mapping[str, Any],
    coverage: Mapping[str, Any],
    entity_counts: Mapping[str, int],
    rows_by_node: Mapping[str, Sequence[Mapping[str, Any]]],
    provider_drift: Sequence[Mapping[str, Any]],
    stockgrid_board: Sequence[Mapping[str, Any]],
    macro_board: Sequence[Mapping[str, Any]],
    prediction_board: Sequence[Mapping[str, Any]],
    delta: Mapping[str, Any],
) -> list[dict[str, Any]]:
    safe_level = (
        "internal_dashboard_evidence"
        if evidence_card.get("safe_use_level") == "run_evidence_ready"
        else str(evidence_card.get("safe_use_level") or "artifact_specimen_only")
    )
    observations: list[dict[str, Any]] = []
    run_grade = evidence_card.get("run_grade") if isinstance(evidence_card.get("run_grade"), Mapping) else {}
    all_source_refs = _typed_source_refs([
        str(feed.get("artifact_ref"))
        for feed in coverage.get("feeds") or []
        if isinstance(feed, Mapping) and feed.get("artifact_ref")
    ])
    readiness = evidence_card.get("readiness_summary_state") if isinstance(evidence_card.get("readiness_summary_state"), Mapping) else {}
    ready_count = sum(1 for feed in coverage.get("feeds") or [] if isinstance(feed, Mapping) and feed.get("quality") == "ok")

    health_conf = _confidence(
        tone="ok" if evidence_card.get("safe_use_level") == "run_evidence_ready" else "warn",
        coverage=ready_count / max(len(FEED_NODE_IDS), 1),
        explainability=0.95,
    )
    observations.append(
        _observation(
            observation_id="run_health_trust_strip",
            title=f"Feed run {evidence_card.get('run_id')} is {run_grade.get('grade') or 'unknown'}",
            why_interesting="This is the gating status every downstream quant panel inherits.",
            entities=[f"provider:{node_id}" for node_id in FEED_NODE_IDS],
            score=_score(interestingness=0.9, confidence=health_conf, display_readiness=0.96),
            reasons=[
                f"safe_use_level={evidence_card.get('safe_use_level')}",
                f"artifact_count={evidence_card.get('artifact_count')}/{evidence_card.get('expected_artifact_count')}",
                f"readiness_state={readiness.get('state')}",
            ],
            reason_codes=[
                "RUN_GREEN" if str(run_grade.get("grade") or "").lower() == "green" else "RUN_NOT_GREEN",
                "SAFE_USE_RUN_EVIDENCE_READY"
                if evidence_card.get("safe_use_level") == "run_evidence_ready"
                else "SAFE_USE_LIMITED",
                "READINESS_PRESENT_READY" if readiness.get("ready") is True else "READINESS_NOT_READY",
            ],
            caveats=[
                "Allows dashboard evidence, not trading or investment claims.",
                "All current counts are run-local and must be regenerated after a later refresh.",
            ],
            disconfirming_checks=[
                "Read feed_readiness_summary blockers.",
                "Read evidence-card quality_by_lane before promoting a claim.",
            ],
            source_refs=list(all_source_refs) + [str(readiness.get("path") or "")],
            safe_use_level=safe_level,
            primary_metric={"name": "safe_use_level", "value": evidence_card.get("safe_use_level")},
        )
    )

    total_entities = sum(int(value or 0) for value in entity_counts.values())
    coverage_conf = _confidence(tone="ok", coverage=min(1.0, total_entities / 1000.0), explainability=0.85)
    observations.append(
        _observation(
            observation_id="coverage_matrix_ready",
            title=f"{total_entities} normalized feed entities available",
            why_interesting="The mart can present breadth before it tries to present interpretation.",
            entities=[f"provider:{node_id}" for node_id in FEED_NODE_IDS],
            score=_score(interestingness=0.74, confidence=coverage_conf, display_readiness=0.9),
            reasons=[
                f"equities={entity_counts.get('equities', 0)}",
                f"etfs={entity_counts.get('etfs', 0)}",
                f"macro_series={entity_counts.get('macro_series', 0)}",
                f"prediction_markets={entity_counts.get('prediction_markets', 0)}",
            ],
            reason_codes=["COVERAGE_MATRIX_READY", "ENTITY_INDEX_BUILT"],
            caveats=["Entity counts are normalized from artifact rows, not a security master."],
            disconfirming_checks=["Inspect per-lane missingness and lifecycle sidecars before cross-feed use."],
            source_refs=all_source_refs,
            safe_use_level=safe_level,
            primary_metric={"name": "normalized_entity_count", "value": total_entities},
        )
    )

    drift_flags = [flag for row in provider_drift for flag in row.get("drift_flags", []) if isinstance(row, Mapping)]
    drift_conf = _confidence(tone="warn" if drift_flags else "ok", coverage=1.0, explainability=0.85)
    observations.append(
        _observation(
            observation_id="provider_drift_monitor",
            title="Provider drift monitor is clean" if not drift_flags else "Provider drift monitor has active flags",
            why_interesting="Stockgrid/FRED-style transport or series failures can make a dashboard look healthy while the substrate is degrading.",
            entities=[f"provider:{row.get('provider_id')}" for row in provider_drift if isinstance(row, Mapping)],
            score=_score(interestingness=0.82 if drift_flags else 0.66, confidence=drift_conf, display_readiness=0.88),
            reasons=drift_flags or ["no provider fallback, HTML response, invalid FRED series, or fetch-failure drift flags detected"],
            reason_codes=["PROVIDER_DRIFT_ACTIVE"] if drift_flags else ["PROVIDER_DRIFT_CLEAN"],
            caveats=["Clean provider drift is a run-local transport result, not proof that the economic interpretation is valid."],
            disconfirming_checks=["Inspect provider_drift_monitor rows for per-feed fetch and fallback fields."],
            source_refs=all_source_refs,
            safe_use_level=safe_level,
            primary_metric={"name": "active_drift_flag_count", "value": len(drift_flags)},
        )
    )

    top_stock = _top_numeric_rows(rows_by_node.get("global_stock_feed", []), metric="Chg_5d", limit=1)
    if top_stock:
        row = top_stock[0]
        ticker = str(row.get("Ticker") or "").strip()
        conf = _confidence(tone=_lane_quality(evidence_card, "global_stock_feed").get("tone"), explainability=0.68)
        observations.append(
            _observation(
                observation_id=f"equity_price_action_{_stable_slug(ticker)}",
                title=f"{ticker} has the largest absolute 5-day equity move in the run",
                why_interesting="This is a salience cue for investigation, not a recommendation.",
                entities=[f"equity:{ticker}"],
                score=_score(
                    interestingness=min(1.0, abs(_float(row.get("Chg_5d")) or 0.0) / 10.0),
                    confidence=conf,
                    display_readiness=0.78,
                ),
                reasons=[
                    f"Chg_5d={row.get('Chg_5d')}",
                    f"Z_Short={row.get('Z_Short')}",
                    f"Vol_20d={row.get('Vol_20d')}",
                ],
                reason_codes=["TOP_ABS_5D_MOVE", "PRICE_ACTION_SALIENCE"],
                caveats=["Price-action salience has no event-window, halt, or corporate-action adjustment in this mart."],
                disconfirming_checks=["Check equity lifecycle sidecar and source artifact row before interpretation."],
                source_refs=[
                    _source_ref_obj(
                        repo_root,
                        run_dir,
                        "global_stock_feed",
                        row_selector={"Ticker": ticker},
                        field_refs=["Chg_5d", "Z_Short", "Vol_20d"],
                    )
                ],
                safe_use_level=safe_level,
                primary_metric={"name": "chg_5d", "value": _float(row.get("Chg_5d"))},
            )
        )

    top_flow = stockgrid_board[0] if stockgrid_board else None
    if top_flow:
        ticker = str(top_flow.get("ticker") or "").strip()
        conf = _confidence(tone=_lane_quality(evidence_card, "global_stockgrid_feed").get("tone"), explainability=0.84)
        observations.append(
            _observation(
                observation_id=f"stockgrid_flow_{_stable_slug(ticker)}",
                title=f"{ticker} is the top Stockgrid flow/conviction observation in the run",
                why_interesting="Stockgrid flow is useful as salience and context when explicitly separated from a recommendation.",
                entities=[f"equity:{ticker}"] if ticker else [],
                score=_score(
                    interestingness=min(1.0, float(top_flow.get("flow_score") or 0.0) / 300_000_000.0),
                    confidence=conf,
                    display_readiness=0.84,
                ),
                reasons=[
                    f"flow_score={top_flow.get('flow_score')}",
                    f"flow_usd={top_flow.get('flow_usd')}",
                    f"conviction={top_flow.get('conviction')}",
                    f"signal_value={top_flow.get('signal_value')}",
                ],
                reason_codes=["STOCKGRID_FLOW_TOP", "FLOW_SALIENCE_NOT_RECOMMENDATION"],
                caveats=["Stockgrid flow is a provider signal lane; it is not a buy/sell ranking."],
                disconfirming_checks=["Check provider drift and row-level Stockgrid source before interpreting the signal."],
                source_refs=top_flow.get("source_refs") or [_source_ref_obj(repo_root, run_dir, "global_stockgrid_feed")],
                safe_use_level=safe_level,
                primary_metric={"name": "stockgrid_flow_score", "value": top_flow.get("flow_score")},
            )
        )

    top_macro_bucket = macro_board[0] if macro_board else None
    if top_macro_bucket:
        conf = _confidence(tone=_lane_quality(evidence_card, "global_macro_feed").get("tone"), explainability=0.76)
        observations.append(
            _observation(
                observation_id=f"macro_regime_{_stable_slug(top_macro_bucket.get('bucket'))}",
                title=f"Macro board is most displaced in {top_macro_bucket.get('bucket')}",
                why_interesting="Bucket-level macro displacement is safer to present than a single unsupported causal story.",
                entities=[row.get("entity_id") for row in top_macro_bucket.get("top_series") or [] if isinstance(row, Mapping)],
                score=_score(
                    interestingness=min(1.0, abs(_float(top_macro_bucket.get("average_z_score")) or 0.0) / 2.0),
                    confidence=conf,
                    display_readiness=0.8,
                ),
                reasons=[
                    f"series_count={top_macro_bucket.get('series_count')}",
                    f"average_z_score={top_macro_bucket.get('average_z_score')}",
                    f"vintage_status={top_macro_bucket.get('vintage_status')}",
                ],
                reason_codes=["MACRO_BUCKET_DISPLACED", "MACRO_SEMANTICS_DECLARED"],
                caveats=[
                    "Macro interpretation remains a series-observation summary unless release/vintage status is available for the bucket."
                ],
                disconfirming_checks=["Inspect macro lifecycle sidecar and FRED diagnostics."],
                source_refs=[
                    _source_ref_obj(
                        repo_root,
                        run_dir,
                        "global_macro_feed",
                        field_refs=["z_score", "recent_change", "metadata.sidecars.macro_lifecycle_snapshot"],
                    )
                ],
                safe_use_level=safe_level,
                primary_metric={"name": "average_z_score", "value": top_macro_bucket.get("average_z_score")},
            )
        )

    top_market = prediction_board[0] if prediction_board else None
    if top_market:
        conf = _confidence(tone=_lane_quality(evidence_card, "global_polymarket_feed").get("tone"), explainability=0.76)
        observations.append(
            _observation(
                observation_id=f"prediction_market_liquidity_{_stable_slug(top_market.get('slug') or top_market.get('question'))}",
                title="Highest-volume prediction-market event is dashboard-ready as an observation",
                why_interesting="Event-market liquidity and probability movement are useful context when kept as observation, not forecast.",
                entities=[top_market.get("entity_id")],
                score=_score(
                    interestingness=min(1.0, (_float(top_market.get("volume")) or 0.0) / 1_000_000.0),
                    confidence=conf,
                    display_readiness=0.82,
                ),
                reasons=[
                    f"question={top_market.get('question')}",
                    f"probability={top_market.get('probability')}",
                    f"volume={top_market.get('volume')}",
                    f"event_identity_status={top_market.get('event_identity_status')}",
                ],
                reason_codes=["PREDICTION_MARKET_EVENT_LIQUIDITY", "EVENT_MARKET_NOT_FORECAST"],
                caveats=["Prediction market rows are not calibrated to realized truth in this mart."],
                disconfirming_checks=["Check Polymarket lifecycle/CLOB sidecars and resolved-archive availability."],
                source_refs=[
                    _source_ref_obj(
                        repo_root,
                        run_dir,
                        "global_polymarket_feed",
                        row_selector={"event_id": top_market.get("event_id"), "event_slug": top_market.get("event_slug")},
                        field_refs=["p", "c", "v", "s", "metadata.sidecars.polymarket_market_identity_snapshot"],
                    )
                ],
                safe_use_level=safe_level,
                primary_metric={"name": "max_volume", "value": top_market.get("volume")},
            )
        )

    if delta.get("status") == "computed":
        largest_lane = max(
            (delta.get("row_deltas_by_lane") or {}).items(),
            key=lambda item: abs(int(item[1] or 0)),
            default=("", 0),
        )
        conf = _confidence(tone="ok", coverage=0.8, explainability=0.82)
        observations.append(
            _observation(
                observation_id="delta_since_previous_green_run",
                title=f"Largest row-count delta since previous green run: {largest_lane[0] or 'none'}",
                why_interesting="Delta since a trusted run is the fastest path from static data to an operator-facing change queue.",
                entities=[f"provider:{largest_lane[0]}"] if largest_lane[0] else [],
                score=_score(
                    interestingness=min(1.0, abs(int(largest_lane[1] or 0)) / 100.0),
                    confidence=conf,
                    display_readiness=0.84,
                ),
                reasons=[
                    f"previous_run_id={delta.get('previous_run_id')}",
                    f"row_delta={largest_lane[1]}",
                    f"quality_change_count={len(delta.get('quality_changes') or [])}",
                ],
                reason_codes=["PREVIOUS_GREEN_DELTA_COMPUTED", "RUN_TO_RUN_DRIFT"],
                caveats=["Row-count deltas are shape changes, not economic movement."],
                disconfirming_checks=["Compare artifact schemas before treating row deltas as comparable economic coverage."],
                source_refs=[delta.get("previous_evidence_card")],
                safe_use_level=safe_level,
                primary_metric={"name": "largest_row_delta", "value": largest_lane[1]},
            )
        )
    else:
        conf = _confidence(tone="warn", coverage=0.25, explainability=0.9)
        observations.append(
            _observation(
                observation_id="delta_since_previous_green_unavailable",
                title="No comparable previous green feed run found",
                why_interesting="The mart refuses to fake deltas when the comparison root is missing.",
                entities=[],
                score=_score(interestingness=0.55, confidence=conf, display_readiness=0.72),
                reasons=[str(delta.get("reason") or "delta_unavailable")],
                reason_codes=["PREVIOUS_GREEN_DELTA_UNAVAILABLE"],
                caveats=["A future green run will unlock run-to-run deltas."],
                disconfirming_checks=["Inspect state/runs for older green feed runs with readiness summaries."],
                source_refs=all_source_refs,
                safe_use_level=safe_level,
                display_state=DISPLAY_DEGRADED,
                primary_metric={"name": "previous_green_run_available", "value": False},
            )
        )

    observations.sort(
        key=lambda row: (
            float((row.get("score") or {}).get("interestingness") or 0.0),
            float((row.get("score") or {}).get("confidence") or 0.0),
            float((row.get("score") or {}).get("display_readiness") or 0.0),
            str(row.get("observation_id") or ""),
        ),
        reverse=True,
    )
    for index, row in enumerate(observations, start=1):
        row["rank"] = index
    return observations


def _panel_manifest() -> list[dict[str, Any]]:
    return [
        {
            "panel_id": "run_health",
            "panel_type": "status_card",
            "title": "Run Health / Trust Strip",
            "data_ref": "run",
            "default_sort": None,
            "badges": ["safe_use_level", "quality_tone"],
            "empty_state": "No feed run available.",
            "quality_ref": "run.safe_use_level",
        },
        {
            "panel_id": "coverage_matrix",
            "panel_type": "ranked_table",
            "title": "Coverage Matrix",
            "data_ref": "coverage.feeds",
            "default_sort": "rows desc",
            "badges": ["quality", "freshness"],
            "empty_state": "No feed artifacts available.",
            "quality_ref": "coverage.feeds[].quality",
        },
        {
            "panel_id": "ranked_observations",
            "panel_type": "ranked_table",
            "title": "Observation Queue",
            "data_ref": "ranked_observations",
            "default_sort": "rank asc",
            "badges": ["safe_use_level", "claim_level", "display_state", "confidence"],
            "empty_state": "No ranked observations generated.",
            "quality_ref": "ranked_observations[].safe_use_level",
        },
        {
            "panel_id": "stockgrid_flow_board",
            "panel_type": "ranked_table",
            "title": "Stockgrid Flow Board",
            "data_ref": "stockgrid_flow_board",
            "default_sort": "flow_score desc",
            "badges": ["claim_level", "ticker", "flow_score"],
            "empty_state": "No Stockgrid flow rows available.",
            "quality_ref": "provider_drift_monitor[].quality_tone",
        },
        {
            "panel_id": "macro_regime_board",
            "panel_type": "ranked_table",
            "title": "Macro Regime Board",
            "data_ref": "macro_regime_board",
            "default_sort": "abs(average_z_score) desc",
            "badges": ["series_count", "vintage_status", "release_calendar_status"],
            "empty_state": "No macro rows available.",
            "quality_ref": "quality_gates.cross_feed_readiness",
        },
        {
            "panel_id": "prediction_market_event_board",
            "panel_type": "ranked_table",
            "title": "Prediction Market Event Board",
            "data_ref": "prediction_market_event_board",
            "default_sort": "volume desc",
            "badges": ["probability", "volume"],
            "empty_state": "No prediction-market rows available.",
            "quality_ref": "quality_gates.cross_feed_readiness",
        },
        {
            "panel_id": "provider_drift_monitor",
            "panel_type": "ranked_table",
            "title": "Provider Drift Monitor",
            "data_ref": "provider_drift_monitor",
            "default_sort": "drift_flags desc",
            "badges": ["quality_tone", "drift_flags"],
            "empty_state": "No provider diagnostics available.",
            "quality_ref": "provider_drift_monitor[].quality_tone",
        },
        {
            "panel_id": "delta_since_previous_green_run",
            "panel_type": "status_card",
            "title": "Delta Since Previous Green Run",
            "data_ref": "delta_since_previous_green_run",
            "default_sort": None,
            "badges": ["status", "previous_run_id"],
            "empty_state": "No previous green run available.",
            "quality_ref": "delta_since_previous_green_run.status",
        },
        {
            "panel_id": "missingness_empty_lane_board",
            "panel_type": "ranked_table",
            "title": "Missingness / Empty Lane Board",
            "data_ref": "missingness_board",
            "default_sort": "rows asc",
            "badges": ["quality", "empty_reason"],
            "empty_state": "No empty or degraded feed lanes.",
            "quality_ref": "coverage.feeds[].quality",
        },
    ]


def _missingness_board(coverage: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feed in coverage.get("feeds") or []:
        if not isinstance(feed, Mapping):
            continue
        row_count = int(feed.get("rows") or 0)
        quality = str(feed.get("quality") or "missing")
        if row_count > 0 and quality == "ok":
            continue
        rows.append(
            {
                "feed_id": feed.get("feed_id"),
                "label": feed.get("label"),
                "rows": row_count,
                "quality": quality,
                "empty_reason": "zero_rows" if row_count == 0 else "quality_degraded",
                "artifact_ref": feed.get("artifact_ref"),
            }
        )
    return rows


def _quality_gates(evidence_card: Mapping[str, Any]) -> dict[str, Any]:
    readiness_gate = build_readiness_gate()
    return {
        "feed_evidence_card": {
            "schema_version": evidence_card.get("schema_version"),
            "safe_use_level": evidence_card.get("safe_use_level"),
            "external_market_claims_allowed": (evidence_card.get("evidence_use") or {}).get("external_market_claims_allowed")
            if isinstance(evidence_card.get("evidence_use"), Mapping)
            else False,
            "trading_or_investment_claims_allowed": False,
            "blocker_count": len(evidence_card.get("blockers") or []),
            "warning_count": len(evidence_card.get("warnings") or []),
        },
        "cross_feed_readiness": {
            "schema_version": readiness_gate.get("schema_version"),
            "safe_use_level_counts": (readiness_gate.get("summary") or {}).get("safe_use_level_counts"),
            "production_divergence_cards_allowed": (readiness_gate.get("summary") or {}).get("production_divergence_cards_allowed"),
            "market_evidence_object_built": (readiness_gate.get("summary") or {}).get("market_evidence_object_built"),
            "source_ref": "state/reports/market_feeds/cross_feed_measurement_readiness_gate_v0.json",
        },
    }


def build_quant_presentation_mart(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_dir: Path | None = None,
    validation_refs: Iterable[str] = (),
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    run_dir = run_dir or resolve_feed_run_dir(repo_root, run_id)
    evidence_card = build_market_feed_run_evidence_card(repo_root, run_dir=run_dir)
    artifacts = _artifact_payloads(run_dir)
    rows_by_node = _artifact_rows_by_node(artifacts)
    coverage = _coverage(repo_root=repo_root, run_dir=run_dir, evidence_card=evidence_card, artifacts=artifacts)
    entity_index, entity_counts = _entities(
        repo_root=repo_root,
        run_dir=run_dir,
        rows_by_node=rows_by_node,
        coverage=coverage,
    )
    coverage["entity_counts"] = entity_counts
    features = _feature_rows(
        repo_root=repo_root,
        run_dir=run_dir,
        evidence_card=evidence_card,
        rows_by_node=rows_by_node,
        coverage=coverage,
    )
    provider_drift = _provider_drift_monitor(
        repo_root=repo_root,
        run_dir=run_dir,
        artifacts=artifacts,
        evidence_card=evidence_card,
    )
    stockgrid_board = _stockgrid_flow_board(
        repo_root=repo_root,
        run_dir=run_dir,
        rows=rows_by_node.get("global_stockgrid_feed", []),
    )
    macro_board = _macro_regime_board(
        rows_by_node.get("global_macro_feed", []),
        macro_artifact=artifacts.get("global_macro_feed"),
    )
    prediction_board = _prediction_market_board(
        rows_by_node.get("global_polymarket_feed", []),
        polymarket_artifact=artifacts.get("global_polymarket_feed"),
    )
    delta = _delta_since_previous_green(repo_root=repo_root, run_dir=run_dir, evidence_card=evidence_card)
    missingness_board = _missingness_board(coverage)
    observations = _ranked_observations(
        repo_root=repo_root,
        run_dir=run_dir,
        evidence_card=evidence_card,
        coverage=coverage,
        entity_counts=entity_counts,
        rows_by_node=rows_by_node,
        provider_drift=provider_drift,
        stockgrid_board=stockgrid_board,
        macro_board=macro_board,
        prediction_board=prediction_board,
        delta=delta,
    )
    run_grade = evidence_card.get("run_grade") if isinstance(evidence_card.get("run_grade"), Mapping) else {}
    source_manifest = (
        evidence_card.get("feed_source_manifest")
        if isinstance(evidence_card.get("feed_source_manifest"), Mapping)
        else feed_source_manifest(repo_root, run_dir)
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "input_watermark": source_manifest.get("input_watermark"),
        "source_fingerprint": source_manifest.get("source_fingerprint"),
        "build": {
            "builder": "system/lib/quant_presentation_mart.py",
            "builder_schema_version": SCHEMA_VERSION,
            "generated_at": source_manifest.get("input_watermark"),
            "generated_at_semantics": "deterministic_input_watermark",
            "input_watermark": source_manifest.get("input_watermark"),
            "source_fingerprint": source_manifest.get("source_fingerprint"),
            "deterministic_render": True,
        },
        "source_manifest": source_manifest,
        "run": {
            "run_id": evidence_card.get("run_id") or run_dir.name,
            "as_of": evidence_card.get("as_of"),
            "source_run_dir": evidence_card.get("source_run_dir"),
            "source_evidence_card": _repo_rel(
                repo_root,
                DEFAULT_REPORT_ROOT / str(evidence_card.get("run_id") or run_dir.name) / "market_feed_run_evidence_card_v0.json",
            ),
            "source_readiness_summary": (evidence_card.get("readiness_summary_state") or {}).get("path")
            if isinstance(evidence_card.get("readiness_summary_state"), Mapping)
            else None,
            "safe_use_level": evidence_card.get("safe_use_level"),
            "quality_tone": "green" if str(run_grade.get("grade") or "").lower() == "green" else str(run_grade.get("grade") or "unknown"),
            "run_grade": run_grade,
        },
        "authority_boundary": {
            "projection_not_authority": True,
            "backend_only_contract": True,
            "not_frontend_layout": True,
            "not_trading_or_investment_advice": True,
            "ranked_observations_not_asset_recommendations": True,
        },
        "coverage": coverage,
        "entity_index": entity_index,
        "features": features,
        "ranked_observations": observations,
        "stockgrid_flow_board": stockgrid_board,
        "macro_regime_board": macro_board,
        "prediction_market_event_board": prediction_board,
        "provider_drift_monitor": provider_drift,
        "missingness_board": missingness_board,
        "delta_since_previous_green_run": delta,
        "panel_manifest": _panel_manifest(),
        "quality_gates": _quality_gates(evidence_card),
        "source_surfaces": {
            "refresh_operator": "tools/finance/refresh_feeds.py",
            "evidence_card_builder": "system/lib/market_feed_run_evidence.py",
            "market_feeds_world_model": "system/server/world_model.py::load_market_feeds_snapshot",
            "fusion_readiness_gate": "system/lib/market_fusion_readiness.py",
            "quant_mart_builder": "system/lib/quant_presentation_mart.py",
        },
        "validation_refs": list(validation_refs),
    }
    return payload


def _ref_exists(payload: Mapping[str, Any], ref: str) -> bool:
    parts = [part.replace("[]", "") for part in ref.split(".") if part]

    def descend(current: Any, remaining: Sequence[str]) -> bool:
        if not remaining:
            return True
        part = remaining[0]
        if isinstance(current, list):
            return any(descend(item, remaining) for item in current)
        if not isinstance(current, Mapping) or part not in current:
            return False
        return descend(current[part], remaining[1:])

    return descend(payload, parts)


def _source_refs_are_typed(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        if "source_refs" in value:
            refs = value.get("source_refs")
            if not isinstance(refs, list):
                errors.append(f"{path}.source_refs must be a list")
            else:
                for index, ref in enumerate(refs):
                    if not isinstance(ref, Mapping):
                        errors.append(f"{path}.source_refs[{index}] must be an object")
                        continue
                    if not ref.get("kind") or not ref.get("path"):
                        errors.append(f"{path}.source_refs[{index}] must include kind and path")
        for key, child in value.items():
            if isinstance(child, (Mapping, list)):
                _source_refs_are_typed(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (Mapping, list)):
                _source_refs_are_typed(child, f"{path}[{index}]", errors)


def validate_quant_presentation_mart(payload: Mapping[str, Any], *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(payload.get("build"), Mapping):
        errors.append("build block is required")
    if not payload.get("source_fingerprint"):
        errors.append("source_fingerprint is required")
    if not isinstance(payload.get("source_manifest"), Mapping):
        errors.append("source_manifest is required")

    for index, panel in enumerate(payload.get("panel_manifest") or []):
        if not isinstance(panel, Mapping):
            errors.append(f"panel_manifest[{index}] must be an object")
            continue
        data_ref = str(panel.get("data_ref") or "")
        quality_ref = str(panel.get("quality_ref") or "")
        if data_ref and not _ref_exists(payload, data_ref):
            errors.append(f"panel_manifest[{index}].data_ref is dangling: {data_ref}")
        if quality_ref and not _ref_exists(payload, quality_ref):
            errors.append(f"panel_manifest[{index}].quality_ref is dangling: {quality_ref}")

    allowed_claim_levels = {CLAIM_LEVEL, "run_health", "coverage_observation"}
    allowed_display_states = {DISPLAY_READY, DISPLAY_DEGRADED, DISPLAY_SUPPRESSED}
    for index, observation in enumerate(payload.get("ranked_observations") or []):
        if not isinstance(observation, Mapping):
            errors.append(f"ranked_observations[{index}] must be an object")
            continue
        prefix = f"ranked_observations[{index}]"
        for required in ("reason_codes", "caveats", "disconfirming_checks", "source_refs"):
            if not observation.get(required):
                errors.append(f"{prefix}.{required} is required")
        if observation.get("claim_level") not in allowed_claim_levels:
            errors.append(f"{prefix}.claim_level is not allowed: {observation.get('claim_level')}")
        if observation.get("display_state") not in allowed_display_states:
            errors.append(f"{prefix}.display_state is not allowed: {observation.get('display_state')}")
        forbidden = f"{observation.get('title', '')} {observation.get('why_interesting', '')}".lower()
        if any(token in forbidden for token in ("buy ", "sell ", "target price")):
            errors.append(f"{prefix} contains trading recommendation language")

    for index, feature in enumerate(payload.get("features") or []):
        if not isinstance(feature, Mapping):
            errors.append(f"features[{index}] must be an object")
            continue
        family = str(feature.get("feature_family") or "")
        if family not in FEATURE_FAMILIES:
            errors.append(f"features[{index}].feature_family is not controlled: {family}")

    boundary = payload.get("authority_boundary") if isinstance(payload.get("authority_boundary"), Mapping) else {}
    if boundary.get("not_frontend_layout") is not True:
        errors.append("authority_boundary.not_frontend_layout must be true")
    if boundary.get("not_trading_or_investment_advice") is not True:
        errors.append("authority_boundary.not_trading_or_investment_advice must be true")

    errors.extend(blocking_numeric_contract_errors(payload))

    if strict:
        _source_refs_are_typed(payload, "$", errors)
        serialized = json.dumps(payload, sort_keys=True).lower()
        for token in ('"react"', '"css"', '"chart.js"', '"tailwind"', '"classname"'):
            if token in serialized:
                errors.append(f"frontend layout token leaked into mart: {token}")
    return errors


def _unavailable_mart(
    *,
    run_id: str | None,
    status: str,
    reason: str,
    path: Path,
    payload_run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "run_id": run_id,
            "safe_use_level": status,
        },
        "projection_status": {
            "status": status,
            "reason": reason,
            "path": str(path),
            "expected_run_id": run_id,
            "payload_run_id": payload_run_id,
        },
        "ranked_observations": [],
        "panel_manifest": [],
    }


def load_latest_quant_presentation_mart(
    repo_root: Path,
    *,
    expected_run_id: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    latest_filename: str = DEFAULT_LATEST_FILENAME,
) -> dict[str, Any]:
    root = report_root if report_root.is_absolute() else repo_root / report_root
    path = root / latest_filename
    if not path.exists():
        return _unavailable_mart(
            run_id=expected_run_id,
            status="quant_mart_missing",
            reason="latest_quant_presentation_mart_missing",
            path=path,
        )
    payload = _read_json(path)
    if not payload:
        return _unavailable_mart(
            run_id=expected_run_id,
            status="quant_mart_unreadable",
            reason="latest_quant_presentation_mart_unreadable",
            path=path,
        )
    payload_run_id = (
        str((payload.get("run") or {}).get("run_id") or "")
        if isinstance(payload.get("run"), Mapping)
        else ""
    )
    if expected_run_id and payload_run_id != expected_run_id:
        return _unavailable_mart(
            run_id=expected_run_id,
            status="quant_mart_stale",
            reason="latest_quant_presentation_mart_run_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
    if payload.get("schema_version") != SCHEMA_VERSION:
        return _unavailable_mart(
            run_id=expected_run_id or payload_run_id,
            status="quant_mart_schema_mismatch",
            reason="latest_quant_presentation_mart_schema_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
    payload = dict(payload)
    payload["projection_status"] = {
        "status": "in_sync",
        "path": _repo_rel(repo_root, path),
        "expected_run_id": expected_run_id,
        "payload_run_id": payload_run_id,
        "source_fingerprint": payload.get("source_fingerprint"),
    }
    return payload


def render_quant_presentation_mart(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_quant_presentation_mart(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_dir: Path | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    latest_filename: str = DEFAULT_LATEST_FILENAME,
    validation_refs: Iterable[str] = (),
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    run_dir = run_dir or resolve_feed_run_dir(repo_root, run_id)
    payload = build_quant_presentation_mart(
        repo_root,
        run_dir=run_dir,
        validation_refs=validation_refs,
    )
    artifacts_output = run_dir / "artifacts" / RUN_ARTIFACT_FILENAME
    root = report_root if report_root.is_absolute() else repo_root / report_root
    run_report_output = root / str(payload["run"]["run_id"]) / REPORT_FILENAME
    latest_output = root / latest_filename
    _write_json(artifacts_output, payload)
    _write_json(run_report_output, payload)
    _write_json(latest_output, payload)
    return payload
