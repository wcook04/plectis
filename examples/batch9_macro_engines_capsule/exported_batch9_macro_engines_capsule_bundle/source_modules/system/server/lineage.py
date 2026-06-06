"""
[PURPOSE]
- Teleology: Resolve canonical data-root lineage for historical runs and summarize reusable
  source snapshots for the UI.
- Mechanism: Pure runtime_context inspection over `state/runs/*` with additive market-session
  classification and deterministic grouping.
- Non-goal: Does not mutate run state or execute any runtime behavior.
- When-needed: Open when lobby or translator code needs canonical lineage and reusable data-root summaries from historical run metadata.
- Escalates-to: system/server/translator.py::Translator; system/server/schemas.py::RunLineageContext; system/server/schemas.py::DataRootSummary
- Navigation-group: server_backend
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, MutableMapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo


_ET = ZoneInfo("America/New_York")
ORACLE_PAIRING_MISSION = "oracle"
LEGACY_ORACLE_PAIRING_ALIASES = frozenset({"audit"})


def is_oracle_pairing_context(
    *,
    mission_name: Optional[str] = None,
    subject_group: Optional[str] = None,
) -> bool:
    """
    [ACTION]
    - Teleology: Detect whether a run's mission_name or subject_group identifies an oracle-pairing context.
    - Guarantee: Returns True when either argument matches the oracle pairing mission name or its legacy aliases.
    - Fails: None — returns False for None or unrecognized values.
    """
    for raw in (mission_name, subject_group):
        normalized = str(raw or "").strip().lower()
        if normalized == ORACLE_PAIRING_MISSION or normalized in LEGACY_ORACLE_PAIRING_ALIASES:
            return True
    return False


def _coerce_iso_timestamp(value: object) -> Optional[str]:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(microsecond=0).isoformat()
        except Exception:
            return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except ValueError:
            return raw
    return None


def iso_to_epoch_s(value: Optional[str]) -> Optional[float]:
    """
    [ACTION]
    - Teleology: Convert an ISO-8601 timestamp string to a UTC epoch float in seconds.
    - Guarantee: Returns a float epoch value when the string is a valid ISO timestamp; returns None otherwise.
    - Fails: None — malformed or non-string input returns None without raising.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).timestamp()
    except ValueError:
        return None


def _normalize_run_id(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token:
        return None
    if token.startswith("RUN_") or token.startswith("CONSOLIDATED"):
        return token
    return None


def _load_context(
    run_id: Optional[str],
    runs_dir: Path,
    context_cache: MutableMapping[str, Dict[str, Any]],
) -> Dict[str, Any]:
    if not run_id:
        return {}
    if run_id in context_cache:
        return context_cache[run_id]
    ctx_path = runs_dir / run_id / "runtime_context.json"
    if not ctx_path.exists():
        context_cache[run_id] = {}
        return context_cache[run_id]
    try:
        payload = json.loads(ctx_path.read_text(encoding="utf-8"))
        context_cache[run_id] = payload if isinstance(payload, dict) else {}
    except Exception:
        context_cache[run_id] = {}
    return context_cache[run_id]


def _extract_run_timestamp_iso(ctx: Dict[str, Any]) -> Optional[str]:
    return _coerce_iso_timestamp(
        ctx.get("run_created_at")
        or ctx.get("original_timestamp")
        or ctx.get("timestamp")
    )


def _extract_data_as_of_iso(ctx: Dict[str, Any]) -> Optional[str]:
    temporal_contract = ctx.get("temporal_contract")
    if not isinstance(temporal_contract, dict):
        temporal_contract = {}
    return _coerce_iso_timestamp(
        ctx.get("as_of")
        or ctx.get("time_anchor")
        or ctx.get("original_as_of")
        or ctx.get("data_timestamp")
        or temporal_contract.get("replay_source_data_as_of_iso")
        or temporal_contract.get("truth_data_as_of_iso")
        or temporal_contract.get("subject_data_as_of_iso")
    )


def _extract_links(run_id: str, ctx: Dict[str, Any]) -> Dict[str, Optional[str]]:
    temporal_contract = ctx.get("temporal_contract")
    if isinstance(temporal_contract, dict):
        tc = temporal_contract
    else:
        tc = {}

    validation_status = str(tc.get("validation_status") or "").strip().lower() or None
    source_run_id = _normalize_run_id(ctx.get("source_run_id") or ctx.get("source"))
    feed_source_run_id = _normalize_run_id(ctx.get("feed_source_run_id") or ctx.get("feed_source"))
    replay_source_run_id = _normalize_run_id(tc.get("replay_source_run_id"))
    truth_run_id = _normalize_run_id(tc.get("truth_run_id"))

    if source_run_id is None:
        source_run_id = _normalize_run_id(tc.get("subject_run_id"))
    if replay_source_run_id is None and validation_status == "feed_replay":
        replay_source_run_id = feed_source_run_id or truth_run_id
    if feed_source_run_id is None:
        feed_source_run_id = replay_source_run_id or truth_run_id
    if validation_status == "feed_replay":
        truth_run_id = None
    elif truth_run_id is None and source_run_id and feed_source_run_id:
        truth_run_id = feed_source_run_id

    links = {
        "source_run_id": source_run_id,
        "feed_source_run_id": feed_source_run_id,
        "truth_run_id": truth_run_id,
        "replay_source_run_id": replay_source_run_id,
        "validation_status": validation_status,
    }
    for key, value in list(links.items()):
        if value == run_id:
            links[key] = None
    return links


def _select_primary_parent(run_id: str, ctx: Dict[str, Any]) -> Tuple[Optional[str], str]:
    links = _extract_links(run_id, ctx)
    source_run_id = links.get("source_run_id")
    feed_source_run_id = links.get("feed_source_run_id")
    if is_oracle_pairing_context(
        mission_name=ctx.get("mission_name"),
        subject_group=ctx.get("subject_group"),
    ):
        if source_run_id:
            return source_run_id, "source_run"
        if feed_source_run_id:
            return feed_source_run_id, "feed_source"
        return None, "self"
    execution_mode = str(ctx.get("execution_mode") or ctx.get("exec_mode") or "").strip().lower()
    if execution_mode == "lab":
        if feed_source_run_id:
            return feed_source_run_id, "feed_source"
        if source_run_id:
            return source_run_id, "source_run"
        return None, "self"
    if source_run_id:
        return source_run_id, "source_run"
    if feed_source_run_id:
        return feed_source_run_id, "feed_source"
    return None, "self"


def _select_truth_parent(run_id: str, ctx: Dict[str, Any]) -> Optional[str]:
    links = _extract_links(run_id, ctx)
    source_run_id = links.get("source_run_id")
    truth_run_id = links.get("truth_run_id")
    if is_oracle_pairing_context(
        mission_name=ctx.get("mission_name"),
        subject_group=ctx.get("subject_group"),
    ):
        return truth_run_id
    if truth_run_id and source_run_id:
        return truth_run_id
    return None


def _build_market_session(anchor_time_iso: Optional[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "exchange": "NYSE",
        "anchor_time_iso": anchor_time_iso,
        "session_phase": "unknown",
        "is_market_open": False,
        "is_extended_hours": False,
        "price_regime": "unknown",
        "label": "Unknown market state",
    }
    epoch_s = iso_to_epoch_s(anchor_time_iso)
    if epoch_s is None:
        return payload

    anchor_dt = datetime.fromtimestamp(epoch_s, tz=timezone.utc).astimezone(_ET)
    minutes = anchor_dt.hour * 60 + anchor_dt.minute
    if anchor_dt.weekday() >= 5:
        payload.update(
            {
                "session_phase": "weekend",
                "price_regime": "reference",
                "label": "Weekend, market closed",
            }
        )
        return payload

    if 570 <= minutes < 960:
        payload.update(
            {
                "session_phase": "regular",
                "is_market_open": True,
                "price_regime": "live",
                "label": "Regular session live",
            }
        )
        return payload

    if 240 <= minutes < 570:
        payload.update(
            {
                "session_phase": "pre",
                "is_extended_hours": True,
                "price_regime": "extended",
                "label": "Pre-market",
            }
        )
        return payload

    if 960 <= minutes < 1200:
        payload.update(
            {
                "session_phase": "after",
                "is_extended_hours": True,
                "price_regime": "extended",
                "label": "After-hours",
            }
        )
        return payload

    payload.update(
        {
            "session_phase": "closed",
            "price_regime": "reference",
            "label": "Market closed",
        }
    )
    return payload


def _resolve_primary_lineage(
    run_id: str,
    runs_dir: Path,
    context_cache: MutableMapping[str, Dict[str, Any]],
) -> Dict[str, Any]:
    lineage_run_ids = [run_id]
    relation = "self"
    current_run_id = run_id
    immediate_parent_run_id: Optional[str] = None

    while True:
        ctx = _load_context(current_run_id, runs_dir, context_cache)
        next_run_id, next_relation = _select_primary_parent(current_run_id, ctx)
        if len(lineage_run_ids) == 1:
            immediate_parent_run_id = next_run_id
            relation = next_relation
        if not next_run_id or next_run_id in lineage_run_ids:
            break
        lineage_run_ids.append(next_run_id)
        current_run_id = next_run_id

    root_ctx = _load_context(current_run_id, runs_dir, context_cache)
    root_run_timestamp_iso = _extract_run_timestamp_iso(root_ctx)
    root_data_as_of_iso = _extract_data_as_of_iso(root_ctx)
    canonical_time_iso = root_data_as_of_iso or root_run_timestamp_iso
    return {
        "root_run_id": current_run_id,
        "immediate_parent_run_id": immediate_parent_run_id,
        "root_run_timestamp_iso": root_run_timestamp_iso,
        "root_data_as_of_iso": root_data_as_of_iso,
        "canonical_time_iso": canonical_time_iso,
        "lineage_depth": max(0, len(lineage_run_ids) - 1),
        "lineage_run_ids": lineage_run_ids,
        "relation": relation,
        "is_reused": len(lineage_run_ids) > 1,
        "market": _build_market_session(canonical_time_iso),
    }


def build_temporal_lineage(
    run_id: str,
    ctx: Dict[str, Any],
    runs_dir: Path,
    context_cache: Optional[MutableMapping[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Assemble the primary and optional truth lineage packet for one run from runtime-context metadata.
    - Mechanism: Resolves the primary parent chain, optionally resolves the truth chain, and returns both in one additive dict.
    - Reads: `state/runs/<run_id>/runtime_context.json` through the shared context cache.
    - Writes: None.
    - Guarantee: Returns a dict with `primary` populated and `truth` either populated or `None`.
    - Fails: None — missing or malformed runtime context degrades to partial lineage fields.
    - When-needed: Open when a candidate run or resume flow needs the exact lineage packet that feeds temporal UI state.
    - Escalates-to: system/server/translator.py::Translator; system/server/schemas.py::RunLineageContext
    """
    cache = context_cache if context_cache is not None else {}
    primary = _resolve_primary_lineage(run_id, runs_dir, cache)

    truth_parent_run_id = _select_truth_parent(run_id, ctx)
    truth: Optional[Dict[str, Any]] = None
    if truth_parent_run_id:
        truth_primary = _resolve_primary_lineage(truth_parent_run_id, runs_dir, cache)
        truth = {
            "root_run_id": truth_primary.get("root_run_id"),
            "immediate_parent_run_id": truth_parent_run_id,
            "root_run_timestamp_iso": truth_primary.get("root_run_timestamp_iso"),
            "root_data_as_of_iso": truth_primary.get("root_data_as_of_iso"),
            "canonical_time_iso": truth_primary.get("canonical_time_iso"),
            "lineage_depth": len([run_id] + truth_primary.get("lineage_run_ids", [])) - 1,
            "lineage_run_ids": [run_id] + truth_primary.get("lineage_run_ids", []),
            "relation": "truth_run",
            "is_reused": True,
            "market": truth_primary.get("market") or _build_market_session(None),
        }

    return {
        "primary": primary,
        "truth": truth,
    }


def summarize_data_roots(candidates: Sequence[Any]) -> List[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Group candidate runs by canonical root so the UI can browse reusable source-data snapshots instead of raw runs.
    - Mechanism: Buckets by `root_run_id`, folds canonical timestamps and market context, then emits sorted summary rows with future-root links.
    - Reads: Candidate temporal lineage metadata already present on the input sequence.
    - Writes: None.
    - Orders: Output is sorted by canonical timestamp descending, then root id.
    - Guarantee: Returns one summary dict per canonical root id.
    - Fails: None — malformed candidate fields are skipped or degraded per row.
    - When-needed: Open when `/api/data-roots` or translator flows need grouped reusable roots rather than per-run lobby rows.
    - Escalates-to: system/server/main.py::get_data_roots; system/server/schemas.py::DataRootSummary
    """
    groups: Dict[str, Dict[str, Any]] = {}

    for candidate in candidates:
        temporal = getattr(candidate, "temporal", None)
        lineage = getattr(temporal, "lineage", None) if temporal is not None else None
        primary = getattr(lineage, "primary", None) if lineage is not None else None

        root_run_id = getattr(primary, "root_run_id", None) or getattr(candidate, "id", "")
        if not root_run_id:
            continue

        canonical_time_iso = (
            getattr(primary, "canonical_time_iso", None)
            or getattr(primary, "root_data_as_of_iso", None)
            or getattr(primary, "root_run_timestamp_iso", None)
            or getattr(temporal, "data_as_of_iso", None)
            or getattr(temporal, "run_timestamp_iso", None)
        )
        canonical_timestamp = iso_to_epoch_s(canonical_time_iso)
        market = getattr(primary, "market", None)
        if hasattr(market, "model_dump"):
            market = market.model_dump()

        group = groups.setdefault(
            root_run_id,
            {
                "id": root_run_id,
                "root_run_id": root_run_id,
                "canonical_time_iso": canonical_time_iso,
                "canonical_timestamp": canonical_timestamp,
                "data_as_of_iso": getattr(primary, "root_data_as_of_iso", None),
                "run_timestamp_iso": getattr(primary, "root_run_timestamp_iso", None),
                "market": market or _build_market_session(canonical_time_iso),
                "member_run_ids": [],
                "member_count": 0,
                "derived_run_count": 0,
                "mission_names": set(),
                "latest_member_run_id": None,
                "latest_member_timestamp": None,
                "usable_for_feeds": False,
                "feed_run_id": None,
                "status": "red",
                "has_green_run": False,
            },
        )

        group["member_run_ids"].append(getattr(candidate, "id"))
        group["member_count"] += 1
        group["mission_names"].add(getattr(candidate, "mission_name", "unknown"))
        if getattr(candidate, "id", None) != root_run_id:
            group["derived_run_count"] += 1

        candidate_timestamp = getattr(candidate, "timestamp", None)
        if isinstance(candidate_timestamp, (int, float)):
            latest_member_timestamp = group.get("latest_member_timestamp")
            if latest_member_timestamp is None or candidate_timestamp > latest_member_timestamp:
                group["latest_member_timestamp"] = candidate_timestamp
                group["latest_member_run_id"] = getattr(candidate, "id", None)

        if getattr(candidate, "valid_for_feeds", False):
            group["usable_for_feeds"] = True
            if group.get("feed_run_id") is None or getattr(candidate, "id", None) == root_run_id:
                group["feed_run_id"] = getattr(candidate, "id", None)

        status = str(getattr(candidate, "status", "red")).lower()
        if status == "green":
            group["status"] = "green"
            group["has_green_run"] = True
        elif status == "amber" and group.get("status") != "green":
            group["status"] = "amber"

        if group.get("canonical_timestamp") is None and canonical_timestamp is not None:
            group["canonical_timestamp"] = canonical_timestamp
        if group.get("canonical_time_iso") is None and canonical_time_iso is not None:
            group["canonical_time_iso"] = canonical_time_iso
        if group.get("data_as_of_iso") is None:
            group["data_as_of_iso"] = getattr(primary, "root_data_as_of_iso", None)
        if group.get("run_timestamp_iso") is None:
            group["run_timestamp_iso"] = getattr(primary, "root_run_timestamp_iso", None)

    ordered = sorted(
        groups.values(),
        key=lambda item: (
            item.get("canonical_timestamp") is None,
            -(item.get("canonical_timestamp") or 0.0),
            item.get("root_run_id") or "",
        ),
    )

    ascending = sorted(
        [item for item in ordered if isinstance(item.get("canonical_timestamp"), (int, float))],
        key=lambda item: float(item.get("canonical_timestamp") or 0.0),
    )
    future_ids_by_root: Dict[str, List[str]] = {}
    for idx, item in enumerate(ascending):
        current_ts = float(item.get("canonical_timestamp") or 0.0)
        future_ids_by_root[item["root_run_id"]] = [
            other["root_run_id"]
            for other in ascending[idx + 1 :]
            if float(other.get("canonical_timestamp") or 0.0) > current_ts
        ]

    summaries: List[Dict[str, Any]] = []
    for item in ordered:
        root_run_id = item["root_run_id"]
        summaries.append(
            {
                "id": root_run_id,
                "root_run_id": root_run_id,
                "canonical_time_iso": item.get("canonical_time_iso"),
                "canonical_timestamp": item.get("canonical_timestamp"),
                "data_as_of_iso": item.get("data_as_of_iso"),
                "run_timestamp_iso": item.get("run_timestamp_iso"),
                "market": item.get("market") or _build_market_session(item.get("canonical_time_iso")),
                "member_run_ids": sorted(item.get("member_run_ids", [])),
                "member_count": item.get("member_count", 0),
                "derived_run_count": item.get("derived_run_count", 0),
                "mission_names": sorted(item.get("mission_names", set())),
                "latest_member_run_id": item.get("latest_member_run_id"),
                "usable_for_feeds": bool(item.get("usable_for_feeds")),
                "feed_run_id": item.get("feed_run_id") or item.get("latest_member_run_id") or root_run_id,
                "status": item.get("status", "red"),
                "has_green_run": bool(item.get("has_green_run")),
                "future_root_ids": future_ids_by_root.get(root_run_id, []),
                "future_root_count": len(future_ids_by_root.get(root_run_id, [])),
            }
        )

    return summaries
