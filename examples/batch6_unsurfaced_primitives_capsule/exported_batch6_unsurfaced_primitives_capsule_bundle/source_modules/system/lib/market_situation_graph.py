"""
[PURPOSE]
- Teleology: Compile the quant presentation mart into a backend-owned market
  situation graph: situation objects, evidence/counterevidence edges,
  horizon/risk/regime context, validation posture, and drilldown refs.
- Mechanism: Read the generated quant mart sidecar as input, preserve its source
  refs, and emit a stricter semantic layer without rebuilding feeds or making
  trading claims.
- Non-goal: This is not an alpha engine, not a frontend layout contract, and
  not a replacement for the market-fusion readiness refusal gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib.quant_presentation_mart import (
    DEFAULT_LATEST_FILENAME as MART_LATEST_FILENAME,
    DEFAULT_REPORT_ROOT,
    REPORT_FILENAME as MART_REPORT_FILENAME,
    SCHEMA_VERSION as MART_SCHEMA_VERSION,
)


SCHEMA_VERSION = "market_situation_graph_v0"
RUN_ARTIFACT_FILENAME = "market_situation_graph.json"
REPORT_FILENAME = "market_situation_graph_v0.json"
DEFAULT_LATEST_FILENAME = "latest_market_situation_graph.json"

HORIZONS: frozenset[str] = frozenset(
    {"intraday", "1d", "5d", "20d", "63d", "release-cycle", "event-expiry", "structural"}
)
CLAIM_LEVELS: frozenset[str] = frozenset(
    {"salience_observation", "validated_signal_candidate", "risk_context", "data_quality_warning"}
)
VALIDATION_STATES: frozenset[str] = frozenset(
    {"data_fact", "salience_observation", "signal_candidate", "validated_signal", "blocked"}
)
DISPLAY_STATES: frozenset[str] = frozenset({"ready", "degraded", "suppressed"})
SITUATION_TYPES: frozenset[str] = frozenset(
    {
        "flow_price_confirmation",
        "flow_price_divergence",
        "macro_regime_shift",
        "event_market_salience",
        "provider_or_data_drift",
        "coverage_or_missingness_gap",
        "cross_asset_theme",
    }
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
    path.write_text(render_market_situation_graph(payload), encoding="utf-8")


def _stable_slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9._:-]+", "-", text)
    return text.strip("-") or "unknown"


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


def _source_ref_id(ref: Mapping[str, Any]) -> str:
    raw = json.dumps(ref, sort_keys=True, separators=(",", ":"))
    return "src_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _source_ref_index(source_refs: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for ref in source_refs:
        index[_source_ref_id(ref)] = dict(ref)
    return index


def _entity_index(mart: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("entity_id")): row
        for row in mart.get("entity_index") or []
        if isinstance(row, Mapping) and str(row.get("entity_id") or "").strip()
    }


def _features_by_entity(mart: Mapping[str, Any], family: str) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for feature in mart.get("features") or []:
        if not isinstance(feature, Mapping):
            continue
        if feature.get("feature_family") != family:
            continue
        entity_id = str(feature.get("entity_id") or "").strip()
        if entity_id and entity_id not in rows:
            rows[entity_id] = feature
    return rows


def _bucket_number(value: float | None, *, low: float, high: float) -> str:
    if value is None:
        return "unknown"
    if abs(value) >= high:
        return "high"
    if abs(value) >= low:
        return "medium"
    return "low"


def _asset_risk_context(
    entity_id: str,
    *,
    entity_rows: Mapping[str, Mapping[str, Any]],
    price_features: Mapping[str, Mapping[str, Any]],
    stockgrid_row: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entity = entity_rows.get(entity_id) or {}
    entity_type = str(entity.get("entity_type") or "").strip() or "unknown"
    quality = entity.get("quality") if isinstance(entity.get("quality"), Mapping) else {}
    feature = price_features.get(entity_id) or {}
    metrics = feature.get("metrics") if isinstance(feature.get("metrics"), Mapping) else {}
    chg_5d = _float(metrics.get("chg_5d"))
    vol_20d = _float(metrics.get("vol_20d"))
    flow_score = _float((stockgrid_row or {}).get("flow_score"))
    return {
        "asset_class": entity_type,
        "sector": (stockgrid_row or {}).get("sector") or quality.get("category"),
        "liquidity_proxy": _bucket_number(flow_score, low=25_000_000.0, high=250_000_000.0),
        "volatility_proxy": _bucket_number(vol_20d, low=0.2, high=0.5),
        "momentum_proxy": _bucket_number(chg_5d, low=2.0, high=7.0),
        "factor_context_status": "partial" if feature else "insufficient_data",
        "factor_exposures": [],
        "residual_status": "not_computed",
        "notes": [
            "Local proxy context only; no estimated factor model or residual return is computed."
        ],
    }


def _generic_risk_context(asset_class: str, *, status: str = "insufficient_data") -> dict[str, Any]:
    return {
        "asset_class": asset_class,
        "sector": None,
        "liquidity_proxy": "unknown",
        "volatility_proxy": "unknown",
        "momentum_proxy": "unknown",
        "factor_context_status": status,
        "factor_exposures": [],
        "residual_status": "not_computed",
        "notes": ["No asset-level factor model is computed for this situation."],
    }


def _regime_context_from_macro(mart: Mapping[str, Any]) -> dict[str, Any]:
    board = [row for row in mart.get("macro_regime_board") or [] if isinstance(row, Mapping)]
    top = board[0] if board else {}
    return {
        "status": "available" if top else "insufficient_data",
        "top_bucket": top.get("bucket"),
        "average_z_score": top.get("average_z_score"),
        "series_count": top.get("series_count"),
        "vintage_status": top.get("vintage_status"),
        "release_calendar_status": top.get("release_calendar_status"),
        "interpretation_level": top.get("interpretation_level"),
    }


def _confidence(
    *,
    data_quality: float,
    evidence_strength: float,
    counterevidence_penalty: float,
    traceability: float,
) -> dict[str, float]:
    overall = data_quality * 0.35 + evidence_strength * 0.3 + traceability * 0.25 - counterevidence_penalty * 0.1
    return {
        "data_quality": round(max(0.0, min(1.0, data_quality)), 3),
        "evidence_strength": round(max(0.0, min(1.0, evidence_strength)), 3),
        "counterevidence_penalty": round(max(0.0, min(1.0, counterevidence_penalty)), 3),
        "traceability": round(max(0.0, min(1.0, traceability)), 3),
        "overall": round(max(0.0, min(1.0, overall)), 3),
    }


def _validation(
    state: str,
    *,
    requires_backtest: bool,
    requires_event_study: bool = False,
    overfit_risk: str = "unknown",
    history_available: bool = False,
    n_observations: int | None = None,
    lookback: str | None = None,
    validation_refs: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "state": state,
        "requires_backtest": requires_backtest,
        "requires_event_study": requires_event_study,
        "overfit_risk": overfit_risk,
        "sample_support": {
            "history_available": history_available,
            "n_observations": n_observations,
            "lookback": lookback,
        },
        "validation_refs": list(validation_refs),
    }


def _edge(
    *,
    situation_id: str,
    edge_type: str,
    reason_code: str,
    source_ref: Mapping[str, Any] | None,
    metric: Mapping[str, Any] | None = None,
    weight: float = 0.5,
    severity: str | None = None,
    target_entity_id: str | None = None,
) -> dict[str, Any]:
    ref = dict(source_ref or {"kind": "derived_projection", "path": "state/reports/market_feeds/latest_quant_presentation_mart.json"})
    row = {
        "edge_id": f"edge_{_stable_slug(situation_id)}_{_stable_slug(reason_code)}_{_source_ref_id(ref)[4:]}",
        "situation_id": situation_id,
        "edge_type": edge_type,
        "reason_code": reason_code,
        "source_ref_id": _source_ref_id(ref),
        "source_ref": ref,
        "metric": dict(metric or {}),
        "weight": round(max(0.0, min(1.0, weight)), 3),
    }
    if severity:
        row["severity"] = severity
    if target_entity_id:
        row["target_entity_id"] = target_entity_id
    return row


def _situation(
    *,
    situation_id: str,
    situation_type: str,
    rank: int,
    title: str,
    horizon: str,
    claim_level: str,
    thesis_plain: str,
    formal_shape: str,
    entities: Sequence[str],
    evidence_edges: Sequence[Mapping[str, Any]],
    counterevidence_edges: Sequence[Mapping[str, Any]],
    risk_context: Mapping[str, Any],
    regime_context: Mapping[str, Any],
    confidence: Mapping[str, float],
    validation: Mapping[str, Any],
    source_refs: Sequence[Any],
    safe_use_level: str,
    display_state: str = "ready",
    mart_observation_ids: Sequence[str] = (),
    mart_panel_refs: Sequence[str] = (),
) -> dict[str, Any]:
    typed_refs = _typed_source_refs(source_refs)
    return {
        "situation_id": situation_id,
        "situation_type": situation_type,
        "rank": rank,
        "title": title,
        "horizon": horizon,
        "claim_level": claim_level,
        "thesis": {
            "plain_language": thesis_plain,
            "formal_shape": formal_shape,
            "not_investment_advice": True,
        },
        "entities": list(dict.fromkeys(str(entity) for entity in entities if str(entity))),
        "evidence_edges": [dict(edge) for edge in evidence_edges],
        "counterevidence_edges": [dict(edge) for edge in counterevidence_edges],
        "risk_context": dict(risk_context),
        "regime_context": dict(regime_context),
        "confidence": dict(confidence),
        "source_refs": typed_refs,
        "drilldown": {
            "mart_observation_ids": list(mart_observation_ids),
            "mart_panel_refs": list(mart_panel_refs),
            "source_ref_ids": [_source_ref_id(ref) for ref in typed_refs],
        },
        "display_contract": {
            "title": title,
            "summary": thesis_plain,
            "badge_codes": [situation_type, claim_level, horizon, display_state],
            "display_state": display_state,
            "safe_use_level": safe_use_level,
        },
        "validation": dict(validation),
    }


def _first_source_ref(row: Mapping[str, Any] | None) -> dict[str, Any]:
    refs = (row or {}).get("source_refs") if isinstance((row or {}).get("source_refs"), list) else []
    typed = _typed_source_refs(refs)
    return typed[0] if typed else {"kind": "derived_projection", "path": "state/reports/market_feeds/latest_quant_presentation_mart.json"}


def _source_refs_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    refs: list[Any] = []
    for row in rows:
        if isinstance(row.get("source_refs"), list):
            refs.extend(row.get("source_refs") or [])
    return _typed_source_refs(refs)


def _observation_by_id(mart: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("observation_id")): row
        for row in mart.get("ranked_observations") or []
        if isinstance(row, Mapping) and str(row.get("observation_id") or "").strip()
    }


def _stockgrid_flow_situation(
    *,
    mart: Mapping[str, Any],
    entity_rows: Mapping[str, Mapping[str, Any]],
    price_features: Mapping[str, Mapping[str, Any]],
    regime_context: Mapping[str, Any],
    safe_use_level: str,
) -> dict[str, Any] | None:
    board = [row for row in mart.get("stockgrid_flow_board") or [] if isinstance(row, Mapping)]
    if not board:
        return None
    row = board[0]
    ticker = str(row.get("ticker") or "").strip()
    entity_id = str(row.get("entity_id") or f"equity:{ticker}").strip()
    feature = price_features.get(entity_id)
    metrics = feature.get("metrics") if isinstance((feature or {}).get("metrics"), Mapping) else {}
    flow_value = _float(row.get("flow_usd")) or _float(row.get("net_usd")) or _float(row.get("flow"))
    chg_5d = _float(metrics.get("chg_5d"))
    if flow_value is not None and chg_5d is not None and flow_value * chg_5d >= 0:
        situation_type = "flow_price_confirmation"
        title = f"{ticker} flow and 5-day price action are directionally aligned"
        reason_code = "FLOW_PRICE_ALIGNED_5D"
        counter_code = "BACKTEST_REQUIRED_BEFORE_SIGNAL_PROMOTION"
    else:
        situation_type = "flow_price_divergence"
        title = f"{ticker} flow salience lacks 5-day price confirmation"
        reason_code = "STOCKGRID_FLOW_SALIENT"
        counter_code = "PRICE_ACTION_NOT_CONFIRMING_OR_UNAVAILABLE"
    source_refs = _typed_source_refs(list(row.get("source_refs") or []) + list((feature or {}).get("source_refs") or []))
    evidence_edges = [
        _edge(
            situation_id=f"stockgrid_{_stable_slug(ticker)}",
            edge_type="supports",
            reason_code=reason_code,
            source_ref=source_refs[0] if source_refs else _first_source_ref(row),
            metric={"name": "stockgrid_flow_score", "value": row.get("flow_score")},
            weight=0.84,
            target_entity_id=entity_id,
        )
    ]
    if feature:
        evidence_edges.append(
            _edge(
                situation_id=f"stockgrid_{_stable_slug(ticker)}",
                edge_type="supports",
                reason_code="PRICE_ACTION_CONTEXT_AVAILABLE",
                source_ref=_first_source_ref(feature),
                metric={"name": "chg_5d", "value": chg_5d},
                weight=0.55,
                target_entity_id=entity_id,
            )
        )
    counterevidence_edges = [
        _edge(
            situation_id=f"stockgrid_{_stable_slug(ticker)}",
            edge_type="weakens",
            reason_code=counter_code,
            source_ref=source_refs[0] if source_refs else _first_source_ref(row),
            metric={"name": "history_available", "value": False},
            weight=0.52,
            severity="warn",
            target_entity_id=entity_id,
        )
    ]
    evidence_strength = min(1.0, float(row.get("flow_score") or 0.0) / 300_000_000.0)
    return _situation(
        situation_id=f"stockgrid_{_stable_slug(ticker)}",
        situation_type=situation_type,
        rank=1,
        title=title,
        horizon="5d",
        claim_level="salience_observation",
        thesis_plain=(
            "Stockgrid flow is a high-salience feed fact; price context is used only to classify whether the move is confirmed or still unconfirmed."
        ),
        formal_shape="stockgrid_flow(entity,t) x price_action_5d(entity,t) -> salience_relation",
        entities=[entity_id],
        evidence_edges=evidence_edges,
        counterevidence_edges=counterevidence_edges,
        risk_context=_asset_risk_context(
            entity_id,
            entity_rows=entity_rows,
            price_features=price_features,
            stockgrid_row=row,
        ),
        regime_context=regime_context,
        confidence=_confidence(
            data_quality=0.86,
            evidence_strength=evidence_strength,
            counterevidence_penalty=0.45 if not feature else 0.25,
            traceability=0.95 if source_refs else 0.65,
        ),
        validation=_validation(
            "salience_observation",
            requires_backtest=True,
            overfit_risk="unknown",
            history_available=False,
        ),
        source_refs=source_refs,
        safe_use_level=safe_use_level,
        display_state="ready" if source_refs else "degraded",
        mart_observation_ids=[f"stockgrid_flow_{_stable_slug(ticker)}"],
        mart_panel_refs=["stockgrid_flow_board", "ranked_observations"],
    )


def _macro_situation(mart: Mapping[str, Any], *, safe_use_level: str) -> dict[str, Any] | None:
    board = [row for row in mart.get("macro_regime_board") or [] if isinstance(row, Mapping)]
    if not board:
        return None
    row = board[0]
    bucket = str(row.get("bucket") or "macro").strip()
    source_ref = {
        "kind": "derived_projection",
        "path": "state/reports/market_feeds/latest_quant_presentation_mart.json",
        "table_path": "macro_regime_board",
        "row_selector": {"bucket": bucket},
    }
    counter_code = (
        "MACRO_RELEASE_OR_VINTAGE_MISSING"
        if row.get("vintage_status") != "available" or row.get("release_calendar_status") != "available"
        else "MACRO_EVENT_STUDY_NOT_COMPUTED"
    )
    entities = [
        str(series.get("entity_id"))
        for series in row.get("top_series") or []
        if isinstance(series, Mapping) and str(series.get("entity_id") or "").strip()
    ]
    return _situation(
        situation_id=f"macro_{_stable_slug(bucket)}",
        situation_type="macro_regime_shift",
        rank=2,
        title=f"Macro regime displacement is concentrated in {bucket}",
        horizon="release-cycle",
        claim_level="risk_context",
        thesis_plain="The macro board identifies a displaced bucket, but interpretation stays at series-observation level unless release and vintage context are present.",
        formal_shape="macro_bucket(series_z_scores,t) -> regime_context(bucket,t)",
        entities=entities,
        evidence_edges=[
            _edge(
                situation_id=f"macro_{_stable_slug(bucket)}",
                edge_type="supports",
                reason_code="MACRO_BUCKET_DISPLACED",
                source_ref=source_ref,
                metric={"name": "average_z_score", "value": row.get("average_z_score")},
                weight=0.76,
            )
        ],
        counterevidence_edges=[
            _edge(
                situation_id=f"macro_{_stable_slug(bucket)}",
                edge_type="weakens",
                reason_code=counter_code,
                source_ref=source_ref,
                metric={
                    "vintage_status": row.get("vintage_status"),
                    "release_calendar_status": row.get("release_calendar_status"),
                },
                weight=0.42,
                severity="warn",
            )
        ],
        risk_context=_generic_risk_context("macro", status="partial"),
        regime_context={
            "status": "available",
            "top_bucket": bucket,
            "average_z_score": row.get("average_z_score"),
            "series_count": row.get("series_count"),
            "vintage_status": row.get("vintage_status"),
            "release_calendar_status": row.get("release_calendar_status"),
            "interpretation_level": row.get("interpretation_level"),
        },
        confidence=_confidence(
            data_quality=0.84,
            evidence_strength=min(1.0, abs(float(row.get("average_z_score") or 0.0)) / 2.0),
            counterevidence_penalty=0.2 if counter_code == "MACRO_EVENT_STUDY_NOT_COMPUTED" else 0.45,
            traceability=0.8,
        ),
        validation=_validation(
            "data_fact",
            requires_backtest=False,
            requires_event_study=True,
            overfit_risk="not_applicable",
            history_available=True,
            n_observations=int(row.get("series_count") or 0),
            lookback="feed_series_history",
        ),
        source_refs=[source_ref],
        safe_use_level=safe_use_level,
        display_state="ready",
        mart_observation_ids=[f"macro_regime_{_stable_slug(bucket)}"],
        mart_panel_refs=["macro_regime_board"],
    )


def _prediction_market_situation(mart: Mapping[str, Any], *, safe_use_level: str) -> dict[str, Any] | None:
    board = [row for row in mart.get("prediction_market_event_board") or [] if isinstance(row, Mapping)]
    if not board:
        return None
    row = board[0]
    event_key = row.get("event_id") or row.get("event_slug") or row.get("slug") or row.get("question")
    entity_id = str(row.get("entity_id") or f"prediction_market_event:{_stable_slug(event_key)}")
    source_ref = {
        "kind": "derived_projection",
        "path": "state/reports/market_feeds/latest_quant_presentation_mart.json",
        "table_path": "prediction_market_event_board",
        "row_selector": {"event_id": row.get("event_id"), "event_slug": row.get("event_slug"), "slug": row.get("slug")},
    }
    identity_missing = row.get("event_identity_status") != "available"
    return _situation(
        situation_id=f"prediction_event_{_stable_slug(event_key)}",
        situation_type="event_market_salience",
        rank=3,
        title="Prediction-market event has salience, not forecast authority",
        horizon="event-expiry",
        claim_level="salience_observation",
        thesis_plain="Prediction-market volume and probability movement are useful context only after event identity, lifecycle, and calibration gaps stay visible.",
        formal_shape="event_market(volume,probability_change,t) -> event_salience(event,t)",
        entities=[entity_id],
        evidence_edges=[
            _edge(
                situation_id=f"prediction_event_{_stable_slug(event_key)}",
                edge_type="supports",
                reason_code="EVENT_MARKET_VOLUME_SALIENCE",
                source_ref=source_ref,
                metric={"name": "max_volume", "value": row.get("volume")},
                weight=0.78,
                target_entity_id=entity_id,
            )
        ],
        counterevidence_edges=[
            _edge(
                situation_id=f"prediction_event_{_stable_slug(event_key)}",
                edge_type="weakens",
                reason_code="EVENT_IDENTITY_MISSING" if identity_missing else "RESOLVED_ARCHIVE_NOT_ATTACHED",
                source_ref=source_ref,
                metric={"event_identity_status": row.get("event_identity_status")},
                weight=0.5 if identity_missing else 0.34,
                severity="warn",
                target_entity_id=entity_id,
            )
        ],
        risk_context=_generic_risk_context("event", status="partial"),
        regime_context=_regime_context_from_macro(mart),
        confidence=_confidence(
            data_quality=0.78,
            evidence_strength=min(1.0, float(row.get("volume") or 0.0) / 1_000_000.0),
            counterevidence_penalty=0.5 if identity_missing else 0.35,
            traceability=0.78,
        ),
        validation=_validation(
            "salience_observation",
            requires_backtest=True,
            requires_event_study=True,
            overfit_risk="unknown",
            history_available=False,
        ),
        source_refs=[source_ref],
        safe_use_level=safe_use_level,
        display_state="degraded" if identity_missing else "ready",
        mart_observation_ids=[
            f"prediction_market_liquidity_{_stable_slug(row.get('slug') or row.get('question'))}"
        ],
        mart_panel_refs=["prediction_market_event_board"],
    )


def _provider_drift_situation(mart: Mapping[str, Any], *, safe_use_level: str) -> dict[str, Any] | None:
    rows = [row for row in mart.get("provider_drift_monitor") or [] if isinstance(row, Mapping)]
    if not rows:
        return None
    flagged = [row for row in rows if row.get("drift_flags")]
    subject = flagged[0] if flagged else rows[0]
    provider_id = str(subject.get("provider_id") or "provider").strip()
    source_refs = _source_refs_from_rows([subject])
    source_ref = source_refs[0] if source_refs else {
        "kind": "derived_projection",
        "path": "state/reports/market_feeds/latest_quant_presentation_mart.json",
        "table_path": "provider_drift_monitor",
    }
    title = (
        f"{provider_id} has active provider/data drift"
        if flagged
        else "Provider drift monitor is clean for this run"
    )
    return _situation(
        situation_id=f"provider_drift_{_stable_slug(provider_id)}",
        situation_type="provider_or_data_drift",
        rank=4,
        title=title,
        horizon="1d",
        claim_level="data_quality_warning" if flagged else "risk_context",
        thesis_plain="Provider drift changes how much trust downstream situations deserve, but clean transport does not validate economic meaning.",
        formal_shape="provider_quality(feed,t) -> situation_trust_modifier(feed,t)",
        entities=[f"provider:{provider_id}"],
        evidence_edges=[
            _edge(
                situation_id=f"provider_drift_{_stable_slug(provider_id)}",
                edge_type="supports",
                reason_code="PROVIDER_DRIFT_ACTIVE" if flagged else "PROVIDER_DRIFT_CLEAN",
                source_ref=source_ref,
                metric={"active_drift_flag_count": sum(len(row.get("drift_flags") or []) for row in rows)},
                weight=0.72,
                target_entity_id=f"provider:{provider_id}",
            )
        ],
        counterevidence_edges=[
            _edge(
                situation_id=f"provider_drift_{_stable_slug(provider_id)}",
                edge_type="weakens",
                reason_code="TRANSPORT_HEALTH_NOT_ECONOMIC_VALIDATION",
                source_ref=source_ref,
                metric={"quality_tone": subject.get("quality_tone")},
                weight=0.3,
                severity="info",
                target_entity_id=f"provider:{provider_id}",
            )
        ],
        risk_context=_generic_risk_context("provider", status="not_applicable"),
        regime_context=_regime_context_from_macro(mart),
        confidence=_confidence(
            data_quality=0.9 if not flagged else 0.58,
            evidence_strength=0.7,
            counterevidence_penalty=0.2,
            traceability=0.86 if source_refs else 0.6,
        ),
        validation=_validation(
            "data_fact",
            requires_backtest=False,
            overfit_risk="not_applicable",
            history_available=False,
        ),
        source_refs=source_refs or [source_ref],
        safe_use_level=safe_use_level,
        display_state="degraded" if flagged else "ready",
        mart_observation_ids=["provider_drift_monitor"],
        mart_panel_refs=["provider_drift_monitor"],
    )


def _missingness_situation(mart: Mapping[str, Any], *, safe_use_level: str) -> dict[str, Any] | None:
    rows = [row for row in mart.get("missingness_board") or [] if isinstance(row, Mapping)]
    coverage_feeds = [row for row in ((mart.get("coverage") or {}).get("feeds") or []) if isinstance(row, Mapping)]
    if not rows and not coverage_feeds:
        return None
    subject = rows[0] if rows else min(coverage_feeds, key=lambda row: int(row.get("rows") or 0))
    feed_id = str(subject.get("feed_id") or "unknown_feed").strip()
    source_ref = _typed_source_ref(subject.get("artifact_ref")) or {
        "kind": "derived_projection",
        "path": "state/reports/market_feeds/latest_quant_presentation_mart.json",
        "table_path": "missingness_board",
    }
    return _situation(
        situation_id=f"coverage_gap_{_stable_slug(feed_id)}",
        situation_type="coverage_or_missingness_gap",
        rank=5,
        title=f"{feed_id} is the current missingness/coverage constraint",
        horizon="structural",
        claim_level="data_quality_warning",
        thesis_plain="Empty, degraded, or thin lanes are backend facts that should be visible before any cross-feed interpretation.",
        formal_shape="coverage(feed,t) x quality(feed,t) -> display_readiness_constraint(feed,t)",
        entities=[f"provider:{feed_id}"],
        evidence_edges=[
            _edge(
                situation_id=f"coverage_gap_{_stable_slug(feed_id)}",
                edge_type="supports",
                reason_code="COVERAGE_OR_MISSINGNESS_GAP",
                source_ref=source_ref,
                metric={"rows": subject.get("rows"), "quality": subject.get("quality")},
                weight=0.74,
                target_entity_id=f"provider:{feed_id}",
            )
        ],
        counterevidence_edges=[
            _edge(
                situation_id=f"coverage_gap_{_stable_slug(feed_id)}",
                edge_type="weakens",
                reason_code="EMPTY_LANE_NOT_MARKET_SIGNAL",
                source_ref=source_ref,
                metric={"empty_reason": subject.get("empty_reason")},
                weight=0.35,
                severity="info",
                target_entity_id=f"provider:{feed_id}",
            )
        ],
        risk_context=_generic_risk_context("provider", status="not_applicable"),
        regime_context=_regime_context_from_macro(mart),
        confidence=_confidence(
            data_quality=0.82,
            evidence_strength=0.68,
            counterevidence_penalty=0.18,
            traceability=0.8,
        ),
        validation=_validation(
            "data_fact",
            requires_backtest=False,
            overfit_risk="not_applicable",
            history_available=False,
        ),
        source_refs=[source_ref],
        safe_use_level=safe_use_level,
        display_state="degraded" if rows else "ready",
        mart_observation_ids=["coverage_matrix_ready"],
        mart_panel_refs=["missingness_empty_lane_board", "coverage_matrix"],
    )


def _cross_asset_theme_situation(
    mart: Mapping[str, Any],
    *,
    safe_use_level: str,
) -> dict[str, Any] | None:
    stockgrid = [row for row in mart.get("stockgrid_flow_board") or [] if isinstance(row, Mapping)]
    macro = [row for row in mart.get("macro_regime_board") or [] if isinstance(row, Mapping)]
    events = [row for row in mart.get("prediction_market_event_board") or [] if isinstance(row, Mapping)]
    if not stockgrid or not macro:
        return None
    flow_row = stockgrid[0]
    macro_row = macro[0]
    event_row = events[0] if events else {}
    ticker = str(flow_row.get("ticker") or "").strip()
    entity_ids = [str(flow_row.get("entity_id") or f"equity:{ticker}")]
    if event_row:
        entity_ids.append(str(event_row.get("entity_id") or ""))
    entity_ids.extend(
        str(series.get("entity_id"))
        for series in macro_row.get("top_series") or []
        if isinstance(series, Mapping) and str(series.get("entity_id") or "").strip()
    )
    refs = _typed_source_refs(
        list(flow_row.get("source_refs") or [])
        + [
            {
                "kind": "derived_projection",
                "path": "state/reports/market_feeds/latest_quant_presentation_mart.json",
                "table_path": "macro_regime_board",
                "row_selector": {"bucket": macro_row.get("bucket")},
            }
        ]
        + (
            [
                {
                    "kind": "derived_projection",
                    "path": "state/reports/market_feeds/latest_quant_presentation_mart.json",
                    "table_path": "prediction_market_event_board",
                    "row_selector": {"event_id": event_row.get("event_id"), "slug": event_row.get("slug")},
                }
            ]
            if event_row
            else []
        )
    )
    situation_id = f"cross_asset_theme_{_stable_slug(ticker)}_{_stable_slug(macro_row.get('bucket'))}"
    evidence_edges = [
        _edge(
            situation_id=situation_id,
            edge_type="supports",
            reason_code="MULTI_LANE_SALIENCE_PRESENT",
            source_ref=refs[0] if refs else None,
            metric={"stockgrid_flow_score": flow_row.get("flow_score"), "macro_bucket": macro_row.get("bucket")},
            weight=0.62,
            target_entity_id=entity_ids[0] if entity_ids else None,
        )
    ]
    if len(refs) > 1:
        evidence_edges.append(
            _edge(
                situation_id=situation_id,
                edge_type="supports",
                reason_code="REGIME_CONTEXT_PRESENT",
                source_ref=refs[1],
                metric={"average_z_score": macro_row.get("average_z_score")},
                weight=0.48,
            )
        )
    return _situation(
        situation_id=situation_id,
        situation_type="cross_asset_theme",
        rank=6,
        title=f"{ticker or 'asset'} salience can be viewed against the {macro_row.get('bucket')} regime bucket",
        horizon="5d",
        claim_level="risk_context",
        thesis_plain="The graph can relate flow salience, macro regime context, and event-market context, while marking the relation itself as unvalidated.",
        formal_shape="asset_flow(entity,t) + macro_regime(bucket,t) + optional_event(event,t) -> relation_candidate",
        entities=entity_ids,
        evidence_edges=evidence_edges,
        counterevidence_edges=[
            _edge(
                situation_id=situation_id,
                edge_type="weakens",
                reason_code="RELATION_EDGE_NOT_VALIDATED",
                source_ref=refs[0] if refs else None,
                metric={"requires_backtest": True, "requires_event_study": True},
                weight=0.68,
                severity="warn",
            )
        ],
        risk_context=_generic_risk_context("cross_asset", status="partial"),
        regime_context={
            "status": "available",
            "top_bucket": macro_row.get("bucket"),
            "average_z_score": macro_row.get("average_z_score"),
            "interpretation_level": macro_row.get("interpretation_level"),
        },
        confidence=_confidence(
            data_quality=0.72,
            evidence_strength=0.55,
            counterevidence_penalty=0.68,
            traceability=0.82 if refs else 0.5,
        ),
        validation=_validation(
            "signal_candidate",
            requires_backtest=True,
            requires_event_study=True,
            overfit_risk="high",
            history_available=False,
        ),
        source_refs=refs,
        safe_use_level=safe_use_level,
        display_state="degraded",
        mart_observation_ids=[
            f"stockgrid_flow_{_stable_slug(ticker)}",
            f"macro_regime_{_stable_slug(macro_row.get('bucket'))}",
        ],
        mart_panel_refs=["stockgrid_flow_board", "macro_regime_board", "prediction_market_event_board"],
    )


def _compile_situations(mart: Mapping[str, Any]) -> list[dict[str, Any]]:
    safe_use_level = str(((mart.get("run") or {}).get("safe_use_level")) or "artifact_specimen_only")
    entity_rows = _entity_index(mart)
    price_features = _features_by_entity(mart, "price_action")
    regime_context = _regime_context_from_macro(mart)
    builders = [
        lambda: _stockgrid_flow_situation(
            mart=mart,
            entity_rows=entity_rows,
            price_features=price_features,
            regime_context=regime_context,
            safe_use_level=safe_use_level,
        ),
        lambda: _macro_situation(mart, safe_use_level=safe_use_level),
        lambda: _prediction_market_situation(mart, safe_use_level=safe_use_level),
        lambda: _provider_drift_situation(mart, safe_use_level=safe_use_level),
        lambda: _missingness_situation(mart, safe_use_level=safe_use_level),
        lambda: _cross_asset_theme_situation(mart, safe_use_level=safe_use_level),
    ]
    rows = [row for row in (builder() for builder in builders) if isinstance(row, dict)]
    rows.sort(key=lambda row: (int(row.get("rank") or 999), str(row.get("situation_id") or "")))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _graph_entities(
    mart: Mapping[str, Any],
    situations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    entity_rows = _entity_index(mart)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for situation in situations:
        for entity_id in situation.get("entities") or []:
            entity_id = str(entity_id or "").strip()
            if not entity_id or entity_id in seen:
                continue
            seen.add(entity_id)
            source = entity_rows.get(entity_id) or {}
            rows.append(
                {
                    "entity_id": entity_id,
                    "entity_type": source.get("entity_type") or entity_id.split(":", 1)[0],
                    "display_name": source.get("display_name") or entity_id,
                    "symbols": list(source.get("symbols") or []),
                    "source_refs": _typed_source_refs(source.get("source_refs") or []),
                    "quality": dict(source.get("quality") or {}) if isinstance(source.get("quality"), Mapping) else {},
                }
            )
    return rows


def _flatten_edges(situations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for situation in situations:
        for key in ("evidence_edges", "counterevidence_edges"):
            for edge in situation.get(key) or []:
                if isinstance(edge, Mapping):
                    edges.append(dict(edge))
    return edges


def _factor_context_summary(situations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    statuses = Counter(
        str((situation.get("risk_context") or {}).get("factor_context_status") or "unknown")
        for situation in situations
        if isinstance(situation.get("risk_context"), Mapping)
    )
    return {
        "status": "proxy_only",
        "factor_model_status": "not_computed",
        "residual_model_status": "not_computed",
        "available_proxy_fields": [
            "Chg_5d",
            "Chg_63d",
            "Vol_20d",
            "stockgrid_flow_score",
            "macro_average_z_score",
            "prediction_market_volume",
        ],
        "factor_context_status_counts": dict(sorted(statuses.items())),
    }


def _validation_summary(situations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    states = Counter(
        str((situation.get("validation") or {}).get("state") or "unknown")
        for situation in situations
        if isinstance(situation.get("validation"), Mapping)
    )
    return {
        "situation_count": len(situations),
        "state_counts": dict(sorted(states.items())),
        "requires_backtest_count": sum(
            1
            for situation in situations
            if isinstance(situation.get("validation"), Mapping)
            and (situation.get("validation") or {}).get("requires_backtest") is True
        ),
        "requires_event_study_count": sum(
            1
            for situation in situations
            if isinstance(situation.get("validation"), Mapping)
            and (situation.get("validation") or {}).get("requires_event_study") is True
        ),
        "validated_signal_count": states.get("validated_signal", 0),
        "validation_posture": "no_validated_signals_without_external_validation_artifacts",
    }


def _all_situation_source_refs(situations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    refs: list[Any] = []
    for situation in situations:
        refs.extend(situation.get("source_refs") or [])
        for edge in list(situation.get("evidence_edges") or []) + list(situation.get("counterevidence_edges") or []):
            if isinstance(edge, Mapping) and isinstance(edge.get("source_ref"), Mapping):
                refs.append(edge.get("source_ref"))
    return _typed_source_refs(refs)


def _mart_path_for_run(repo_root: Path, run_id: str | None, report_root: Path = DEFAULT_REPORT_ROOT) -> Path:
    root = report_root if report_root.is_absolute() else repo_root / report_root
    if run_id:
        return root / run_id / MART_REPORT_FILENAME
    return root / MART_LATEST_FILENAME


def _load_quant_mart_input(
    repo_root: Path,
    *,
    run_id: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
) -> tuple[dict[str, Any], Path]:
    path = _mart_path_for_run(repo_root, run_id, report_root=report_root)
    payload = _read_json(path)
    if payload:
        return payload, path
    if run_id:
        fallback = repo_root / "state" / "runs" / run_id / "artifacts" / "quant_presentation_mart.json"
        payload = _read_json(fallback)
        if payload:
            return payload, fallback
    return {}, path


def build_market_situation_graph(
    repo_root: Path,
    *,
    run_id: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    mart_payload: Mapping[str, Any] | None = None,
    mart_path: Path | None = None,
    validation_refs: Iterable[str] = (),
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    if mart_payload is None:
        loaded, loaded_path = _load_quant_mart_input(repo_root, run_id=run_id, report_root=report_root)
        mart_payload = loaded
        mart_path = loaded_path
    mart = dict(mart_payload or {})
    if not mart:
        return _unavailable_graph(
            run_id=run_id,
            status="market_situation_graph_input_missing",
            reason="quant_presentation_mart_input_missing",
            path=mart_path or _mart_path_for_run(repo_root, run_id, report_root=report_root),
        )
    run = mart.get("run") if isinstance(mart.get("run"), Mapping) else {}
    run_id = str(run.get("run_id") or run_id or "").strip() or None
    situations = _compile_situations(mart)
    entities = _graph_entities(mart, situations)
    edges = _flatten_edges(situations)
    source_refs = _all_situation_source_refs(situations)
    source_index = _source_ref_index(source_refs)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "input_mart_schema_version": mart.get("schema_version"),
        "input_mart_fingerprint": mart.get("source_fingerprint"),
        "run_id": run_id,
        "input_watermark": mart.get("input_watermark"),
        "build": {
            "builder": "system/lib/market_situation_graph.py",
            "builder_schema_version": SCHEMA_VERSION,
            "input_mart_path": _repo_rel(repo_root, mart_path or _mart_path_for_run(repo_root, run_id, report_root=report_root)),
            "input_mart_schema_version": mart.get("schema_version"),
            "input_mart_fingerprint": mart.get("source_fingerprint"),
            "input_watermark": mart.get("input_watermark"),
            "deterministic_render": True,
        },
        "authority_boundary": {
            "projection_not_authority": True,
            "source_projection": "quant_presentation_mart_v0_1",
            "backend_only_contract": True,
            "not_frontend_layout": True,
            "not_trading_or_investment_advice": True,
            "situations_not_asset_recommendations": True,
            "validated_signal_requires_validation_refs": True,
        },
        "situations": situations,
        "entities": entities,
        "edges": edges,
        "factor_context": _factor_context_summary(situations),
        "regime_context": _regime_context_from_macro(mart),
        "validation_summary": _validation_summary(situations),
        "drilldown_index": {
            "source_refs": source_index,
            "input_mart": _repo_rel(repo_root, mart_path or _mart_path_for_run(repo_root, run_id, report_root=report_root)),
            "input_mart_fingerprint": mart.get("source_fingerprint"),
        },
        "panel_hints": [
            {
                "hint_id": "situation_queue",
                "data_ref": "situations",
                "default_sort": "rank asc",
                "badge_fields": ["situation_type", "claim_level", "horizon", "validation.state"],
            },
            {
                "hint_id": "evidence_graph",
                "data_ref": "edges",
                "default_sort": "weight desc",
                "badge_fields": ["edge_type", "reason_code", "severity"],
            },
            {
                "hint_id": "validation_debt",
                "data_ref": "validation_summary",
                "default_sort": None,
                "badge_fields": ["requires_backtest_count", "requires_event_study_count"],
            },
        ],
        "quality_gates": mart.get("quality_gates") or {},
        "source_surfaces": {
            "input_mart": "system/lib/quant_presentation_mart.py",
            "situation_graph_builder": "system/lib/market_situation_graph.py",
            "fusion_readiness_gate": "system/lib/market_fusion_readiness.py",
            "world_model_read_path": "system/server/world_model.py::load_market_feeds_snapshot",
        },
        "validation_refs": list(validation_refs),
    }
    return payload


def _unavailable_graph(
    *,
    run_id: str | None,
    status: str,
    reason: str,
    path: Path,
    payload_run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "projection_status": {
            "status": status,
            "reason": reason,
            "path": str(path),
            "expected_run_id": run_id,
            "payload_run_id": payload_run_id,
        },
        "situations": [],
        "entities": [],
        "edges": [],
        "validation_summary": {"situation_count": 0},
    }


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
            if isinstance(refs, Mapping) and path.endswith(".drilldown_index"):
                for ref_id, ref in refs.items():
                    if not isinstance(ref, Mapping):
                        errors.append(f"{path}.source_refs[{ref_id}] must be an object")
                        continue
                    if not ref.get("kind") or not ref.get("path"):
                        errors.append(f"{path}.source_refs[{ref_id}] must include kind and path")
            elif not isinstance(refs, list):
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


def _text_fields(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in {"plain_language", "formal_shape", "title", "summary"} and isinstance(child, str):
                yield child
            elif isinstance(child, (Mapping, list)):
                yield from _text_fields(child)
    elif isinstance(value, list):
        for child in value:
            yield from _text_fields(child)


def validate_market_situation_graph(payload: Mapping[str, Any], *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("input_mart_schema_version") not in {MART_SCHEMA_VERSION, None}:
        errors.append(f"input_mart_schema_version must be {MART_SCHEMA_VERSION}")
    if not isinstance(payload.get("build"), Mapping):
        errors.append("build block is required")
    if not payload.get("input_mart_fingerprint") and payload.get("projection_status") is None:
        errors.append("input_mart_fingerprint is required")

    entity_ids = {
        str(row.get("entity_id"))
        for row in payload.get("entities") or []
        if isinstance(row, Mapping) and str(row.get("entity_id") or "").strip()
    }
    source_index = ((payload.get("drilldown_index") or {}).get("source_refs") or {}) if isinstance(payload.get("drilldown_index"), Mapping) else {}

    for index, situation in enumerate(payload.get("situations") or []):
        if not isinstance(situation, Mapping):
            errors.append(f"situations[{index}] must be an object")
            continue
        prefix = f"situations[{index}]"
        situation_type = str(situation.get("situation_type") or "")
        if situation_type not in SITUATION_TYPES:
            errors.append(f"{prefix}.situation_type is not controlled: {situation_type}")
        if situation.get("horizon") not in HORIZONS:
            errors.append(f"{prefix}.horizon is not controlled: {situation.get('horizon')}")
        if situation.get("claim_level") not in CLAIM_LEVELS:
            errors.append(f"{prefix}.claim_level is not controlled: {situation.get('claim_level')}")
        display_state = ((situation.get("display_contract") or {}).get("display_state") if isinstance(situation.get("display_contract"), Mapping) else None)
        if display_state not in DISPLAY_STATES:
            errors.append(f"{prefix}.display_contract.display_state is not controlled: {display_state}")
        thesis = situation.get("thesis")
        if not isinstance(thesis, Mapping) or not thesis.get("plain_language") or not thesis.get("formal_shape"):
            errors.append(f"{prefix}.thesis must include plain_language and formal_shape")
        if not situation.get("evidence_edges"):
            errors.append(f"{prefix}.evidence_edges is required")
        if not situation.get("counterevidence_edges"):
            errors.append(f"{prefix}.counterevidence_edges is required")
        if not isinstance(situation.get("risk_context"), Mapping):
            errors.append(f"{prefix}.risk_context is required")
        else:
            factor_status = situation["risk_context"].get("factor_context_status")
            if factor_status not in {"computed", "partial", "insufficient_data", "not_applicable"}:
                errors.append(f"{prefix}.risk_context.factor_context_status is not controlled: {factor_status}")
            if "residual_status" not in situation["risk_context"]:
                errors.append(f"{prefix}.risk_context.residual_status is required")
        if not isinstance(situation.get("regime_context"), Mapping):
            errors.append(f"{prefix}.regime_context is required")
        validation = situation.get("validation") if isinstance(situation.get("validation"), Mapping) else {}
        validation_state = validation.get("state")
        if validation_state not in VALIDATION_STATES:
            errors.append(f"{prefix}.validation.state is not controlled: {validation_state}")
        if validation_state == "validated_signal" and not validation.get("validation_refs"):
            errors.append(f"{prefix}.validated_signal requires validation_refs")
        if not isinstance(situation.get("drilldown"), Mapping):
            errors.append(f"{prefix}.drilldown is required")
        else:
            for ref_id in situation["drilldown"].get("source_ref_ids") or []:
                if ref_id not in source_index:
                    errors.append(f"{prefix}.drilldown.source_ref_ids contains dangling ref: {ref_id}")
        for entity_id in situation.get("entities") or []:
            if str(entity_id) not in entity_ids:
                errors.append(f"{prefix}.entities contains dangling entity id: {entity_id}")

    for index, edge in enumerate(payload.get("edges") or []):
        if not isinstance(edge, Mapping):
            errors.append(f"edges[{index}] must be an object")
            continue
        if edge.get("edge_type") not in {"supports", "weakens", "blocks", "missing"}:
            errors.append(f"edges[{index}].edge_type is not controlled: {edge.get('edge_type')}")
        if not edge.get("reason_code"):
            errors.append(f"edges[{index}].reason_code is required")
        if not isinstance(edge.get("source_ref"), Mapping) or not edge["source_ref"].get("kind") or not edge["source_ref"].get("path"):
            errors.append(f"edges[{index}].source_ref must be typed")

    for hint_index, hint in enumerate(payload.get("panel_hints") or []):
        if not isinstance(hint, Mapping):
            errors.append(f"panel_hints[{hint_index}] must be an object")
            continue
        data_ref = str(hint.get("data_ref") or "")
        if data_ref and not _ref_exists(payload, data_ref):
            errors.append(f"panel_hints[{hint_index}].data_ref is dangling: {data_ref}")

    boundary = payload.get("authority_boundary") if isinstance(payload.get("authority_boundary"), Mapping) else {}
    if boundary.get("not_frontend_layout") is not True:
        errors.append("authority_boundary.not_frontend_layout must be true")
    if boundary.get("not_trading_or_investment_advice") is not True:
        errors.append("authority_boundary.not_trading_or_investment_advice must be true")

    forbidden_text = "\n".join(_text_fields(payload)).lower()
    for token in ("buy ", "sell ", "target price", "should trade", "investment advice", "recommendation"):
        if token in forbidden_text:
            errors.append(f"trading/action language leaked into graph text: {token.strip()}")

    if strict:
        _source_refs_are_typed(payload, "$", errors)
        serialized = json.dumps(payload, sort_keys=True).lower()
        for token in ('"react"', '"css"', '"chart.js"', '"tailwind"', '"classname"'):
            if token in serialized:
                errors.append(f"frontend layout token leaked into graph: {token}")
    return errors


def load_latest_market_situation_graph(
    repo_root: Path,
    *,
    expected_run_id: str | None = None,
    expected_mart_fingerprint: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    latest_filename: str = DEFAULT_LATEST_FILENAME,
) -> dict[str, Any]:
    root = report_root if report_root.is_absolute() else repo_root / report_root
    path = root / latest_filename
    if not path.exists():
        return _unavailable_graph(
            run_id=expected_run_id,
            status="market_situation_graph_missing",
            reason="latest_market_situation_graph_missing",
            path=path,
        )
    payload = _read_json(path)
    if not payload:
        return _unavailable_graph(
            run_id=expected_run_id,
            status="market_situation_graph_unreadable",
            reason="latest_market_situation_graph_unreadable",
            path=path,
        )
    payload_run_id = str(payload.get("run_id") or "").strip()
    if expected_run_id and payload_run_id != expected_run_id:
        return _unavailable_graph(
            run_id=expected_run_id,
            status="market_situation_graph_stale",
            reason="latest_market_situation_graph_run_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
    if payload.get("schema_version") != SCHEMA_VERSION:
        return _unavailable_graph(
            run_id=expected_run_id or payload_run_id,
            status="market_situation_graph_schema_mismatch",
            reason="latest_market_situation_graph_schema_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
    payload_fingerprint = str(payload.get("input_mart_fingerprint") or "").strip()
    if expected_mart_fingerprint and payload_fingerprint != expected_mart_fingerprint:
        result = _unavailable_graph(
            run_id=expected_run_id or payload_run_id,
            status="market_situation_graph_stale",
            reason="latest_market_situation_graph_mart_fingerprint_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
        result["projection_status"]["expected_mart_fingerprint"] = expected_mart_fingerprint
        result["projection_status"]["payload_mart_fingerprint"] = payload_fingerprint
        return result
    payload = dict(payload)
    payload["projection_status"] = {
        "status": "in_sync",
        "path": _repo_rel(repo_root, path),
        "expected_run_id": expected_run_id,
        "payload_run_id": payload_run_id,
        "input_mart_fingerprint": payload.get("input_mart_fingerprint"),
    }
    return payload


def render_market_situation_graph(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_market_situation_graph(
    repo_root: Path,
    *,
    run_id: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    latest_filename: str = DEFAULT_LATEST_FILENAME,
    validation_refs: Iterable[str] = (),
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    payload = build_market_situation_graph(
        repo_root,
        run_id=run_id,
        report_root=report_root,
        validation_refs=validation_refs,
    )
    run_id = str(payload.get("run_id") or run_id or "").strip()
    if not run_id:
        raise ValueError("market situation graph requires a run_id")
    artifacts_output = repo_root / "state" / "runs" / run_id / "artifacts" / RUN_ARTIFACT_FILENAME
    root = report_root if report_root.is_absolute() else repo_root / report_root
    run_report_output = root / run_id / REPORT_FILENAME
    latest_output = root / latest_filename
    _write_json(artifacts_output, payload)
    _write_json(run_report_output, payload)
    _write_json(latest_output, payload)
    return payload
