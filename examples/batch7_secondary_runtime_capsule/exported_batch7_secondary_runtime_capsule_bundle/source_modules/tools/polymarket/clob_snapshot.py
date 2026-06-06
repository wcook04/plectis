"""
[PURPOSE]
- Teleology: Enrich the pre-normalization identity substrate with bounded read-only
  CLOB microstructure evidence — canonical fees (opt-in), tick size, two-sided book
  extrema, spread, client-computed midpoint, and depth imbalance — so the future
  calibration and divergence layers see book reality, not scanner emit-only signal.
- Mechanism: Filter the FULL in-memory identity_rows sequence to CLOB-eligible
  markets, order by volume descending, truncate to `cap`, flatten token_ids into
  batches of `batch_size`, and POST each batch to the public `/books` endpoint
  once per batch. Compute best_bid/best_ask via NUMERIC EXTREMA across the
  bids/asks arrays (do NOT trust array order). Compute midpoint client-side from
  the extracted best prices; the per-token `/midpoint` endpoint returned empty {}
  for every rail-priced market in the 2026-05-12 probe and is not canonical.
  Optionally enrich a subset with GET `/markets/<condition_id>` for per-market
  fee/tick/neg_risk/accepting_orders metadata (default OFF; controlled via
  `fetch_market_info` config flag).

[INTERFACE]
- `ClobOptions` (frozen dataclass) — config: enabled, cap, timeout, base_url,
  batch_size, fetch_market_info.
- `hydrate_clob_options(raw_cfg)` — pulls the `clob_enrichment` block from
  polymarket_scan with safe defaults.
- `CLOBClient(options, request_get, request_post)` — bounded HTTP client; both
  callables are injectable for tests.
- Pure math: `compute_best_prices`, `compute_depth_at_band`, `compute_depth_imbalance`.
- `build_clob_snapshot(identity_rows, options, diagnostics, *, request_get, request_post, as_of)`
  consumes the full in-memory identity sequence (NOT the truncated embedded
  snapshot — see ledger invariant `clob_snapshot_consumes_full_in_memory_identity_rows`).

[CONSTRAINTS]
- Read-only: never places orders or makes signed calls.
- Default off: scans stay byte-stable unless `clob_enrichment.enabled: true` is set.
- Bounded: `cap` is hard-clamped to `MAX_CAP` (500 markets) regardless of config.
- Batch-first: per-token GET `/book` and `/spread` loops are NOT used. POST `/books`
  fetches up to `batch_size` (default 100) tokens per request.
- Numeric-extrema only: never trust bids/asks array ordering for best-price extraction.
- Stable failure shape: every market emits one row with a typed `fetch_status` value.
  CLOB-ineligible markets emit `fetch_status="not_clob_eligible"` and do NOT trigger
  HTTP calls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import requests

from tools.polymarket.identity import PolymarketMarketIdentity
from tools.polymarket.lifecycle import (
    CLOB_ENRICHMENT_ELIGIBLE_STATES,
    LifecycleClassification,
)


CLOB_BASE_DEFAULT = "https://clob.polymarket.com"
MAX_CAP = 500
DEFAULT_CAP = 50
DEFAULT_TIMEOUT = 10.0
DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 500


@dataclass(frozen=True)
class ClobOptions:
    enabled: bool
    cap: int
    timeout: float
    base_url: str
    batch_size: int
    fetch_market_info: bool


def hydrate_clob_options(raw_cfg: Any) -> ClobOptions:
    block: Dict[str, Any] = {}
    if isinstance(raw_cfg, dict):
        candidate = raw_cfg.get("clob_enrichment")
        if isinstance(candidate, dict):
            block = candidate

    enabled = bool(block.get("enabled", False))

    raw_cap = block.get("cap", DEFAULT_CAP)
    try:
        cap = int(raw_cap)
    except (TypeError, ValueError):
        cap = DEFAULT_CAP
    cap = max(0, min(cap, MAX_CAP))

    raw_timeout = block.get("timeout", DEFAULT_TIMEOUT)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    timeout = max(1.0, timeout)

    raw_batch = block.get("batch_size", DEFAULT_BATCH_SIZE)
    try:
        batch_size = int(raw_batch)
    except (TypeError, ValueError):
        batch_size = DEFAULT_BATCH_SIZE
    batch_size = max(1, min(batch_size, MAX_BATCH_SIZE))

    base_url = str(block.get("base_url") or CLOB_BASE_DEFAULT).rstrip("/")
    fetch_market_info = bool(block.get("fetch_market_info", False))

    return ClobOptions(
        enabled=enabled,
        cap=cap,
        timeout=timeout,
        base_url=base_url,
        batch_size=batch_size,
        fetch_market_info=fetch_market_info,
    )


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def compute_best_prices(
    bids: Sequence[Dict[str, Any]],
    asks: Sequence[Dict[str, Any]],
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Numeric-extrema best-price extraction.

    Per the 2026-05-12 probe: bids may be sorted floor-first and asks ceiling-first
    at the API layer, which inverts a naive `bids[0]`/`asks[0]` reader. Always
    derive best_bid via `max(price)` and best_ask via `min(price)`.

    Returns `(best_bid, best_ask, spread, midpoint, best_bid_size, best_ask_size)`.
    Any element is `None` when the corresponding side has no parseable price.
    """
    best_bid: Optional[float] = None
    best_bid_size: Optional[float] = None
    for entry in bids or []:
        if not isinstance(entry, dict):
            continue
        price = _safe_float(entry.get("price"))
        if price is None:
            continue
        if best_bid is None or price > best_bid:
            best_bid = price
            best_bid_size = _safe_float(entry.get("size"))

    best_ask: Optional[float] = None
    best_ask_size: Optional[float] = None
    for entry in asks or []:
        if not isinstance(entry, dict):
            continue
        price = _safe_float(entry.get("price"))
        if price is None:
            continue
        if best_ask is None or price < best_ask:
            best_ask = price
            best_ask_size = _safe_float(entry.get("size"))

    spread = (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None
    midpoint = ((best_bid + best_ask) / 2.0) if (best_bid is not None and best_ask is not None) else None
    return best_bid, best_ask, spread, midpoint, best_bid_size, best_ask_size


def compute_depth_at_band(
    side: Sequence[Dict[str, Any]],
    anchor_price: Optional[float],
    band: float,
    *,
    direction: str,
) -> Optional[float]:
    """Sum of resting size within `band` of `anchor_price` on one book side."""
    if anchor_price is None:
        return None
    total = 0.0
    matched = 0
    for entry in side or []:
        if not isinstance(entry, dict):
            continue
        price = _safe_float(entry.get("price"))
        size = _safe_float(entry.get("size"))
        if price is None or size is None:
            continue
        if direction == "bid" and price < anchor_price - band:
            continue
        if direction == "ask" and price > anchor_price + band:
            continue
        total += size
        matched += 1
    return total if matched > 0 else None


def compute_depth_imbalance(
    bid_depth: Optional[float],
    ask_depth: Optional[float],
) -> Optional[float]:
    """Standard limit-order-book volume imbalance in [-1, 1]."""
    if bid_depth is None or ask_depth is None:
        return None
    denom = bid_depth + ask_depth
    if denom <= 0:
        return None
    return (bid_depth - ask_depth) / denom


class CLOBClient:
    """Bounded, injectable HTTP client for public CLOB read endpoints."""

    def __init__(
        self,
        options: ClobOptions,
        *,
        request_get: Optional[Callable[..., Any]] = None,
        request_post: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.options = options
        self._get = request_get or requests.get
        self._post = request_post or requests.post

    def _result(self, response: Any) -> Dict[str, Any]:
        status_code = getattr(response, "status_code", None)
        ok = getattr(response, "ok", False)
        body: Any = None
        if ok:
            try:
                body = response.json()
            except Exception as exc:
                return {"status_code": status_code, "ok": False, "error": f"json_parse: {exc}", "body": None}
        return {"status_code": status_code, "ok": ok, "body": body}

    def fetch_market_info(self, condition_id: str) -> Dict[str, Any]:
        url = f"{self.options.base_url}/markets/{condition_id}"
        try:
            response = self._get(url, params={}, timeout=self.options.timeout)
        except Exception as exc:
            return {"status_code": None, "ok": False, "error": str(exc), "body": None}
        return self._result(response)

    def fetch_books_batch(self, token_ids: Sequence[str]) -> Dict[str, Any]:
        if not token_ids:
            return {"status_code": None, "ok": True, "body": [], "request_count": 0}
        url = f"{self.options.base_url}/books"
        body = [{"token_id": str(tok)} for tok in token_ids]
        try:
            response = self._post(url, json=body, timeout=self.options.timeout)
        except Exception as exc:
            return {"status_code": None, "ok": False, "error": str(exc), "body": None, "request_count": 1}
        result = self._result(response)
        result["request_count"] = 1
        return result


def _pick_clob_eligible_rows(
    rows: Sequence[PolymarketMarketIdentity],
    cap: int,
    *,
    lifecycle_classifications: Optional[Sequence[LifecycleClassification]] = None,
) -> Tuple[List[PolymarketMarketIdentity], Dict[str, int]]:
    """Filter to CLOB-enrichment-eligible rows and order by 24h volume desc.

    Substrate-safe: we filter ONLY for enrichment feasibility (Gamma flag
    enable_order_book=True, has token_ids and condition_id) AND lifecycle state
    in CLOB_ENRICHMENT_ELIGIBLE_STATES when lifecycle classifications are given.
    Terminal-lifecycle markets (DE_FACTO_TERMINAL, FORMALLY_RESOLVED, etc.) are
    filtered out BEFORE any HTTP — their no_clob_book is expected, not anomalous.
    Returns (rows, filter_diagnostic) so callers can record why markets were skipped.
    """
    if cap <= 0:
        return [], {"reason": "cap_zero"}

    skip_counts: Dict[str, int] = {
        "missing_clob_identity": 0,
        "lifecycle_not_eligible": 0,
    }
    eligible: List[PolymarketMarketIdentity] = []
    for idx, row in enumerate(rows):
        if not (row.enable_order_book is True and row.clob_token_ids and row.condition_id):
            skip_counts["missing_clob_identity"] += 1
            continue
        if lifecycle_classifications is not None and idx < len(lifecycle_classifications):
            state = lifecycle_classifications[idx].state
            if state not in CLOB_ENRICHMENT_ELIGIBLE_STATES:
                skip_counts["lifecycle_not_eligible"] += 1
                continue
        eligible.append(row)

    def _volume(row: PolymarketMarketIdentity) -> float:
        return row.volume_24h or row.volume_total or 0.0

    eligible.sort(key=_volume, reverse=True)
    return eligible[:cap], skip_counts


def _flatten_token_ids(rows: Sequence[PolymarketMarketIdentity]) -> List[str]:
    """Preserve order of (row, token) pairs across rows."""
    out: List[str] = []
    for row in rows:
        for tok in (row.clob_token_ids or ()):
            out.append(str(tok))
    return out


def _chunk(seq: List[str], size: int) -> List[List[str]]:
    if size <= 0:
        return [seq]
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def _build_book_map(
    token_ids: List[str],
    response_items: Any,
) -> Dict[str, Any]:
    """Map token_id -> book object from the batched /books response.

    The Polymarket public batch endpoint returns one book per requested token, in
    request order. We key by `asset_id` (the canonical token id in the response)
    when present, else fall back to positional order. Mismatches surface as a
    per-token 'batch_response_mismatch' fetch_status downstream.
    """
    book_map: Dict[str, Any] = {}
    if not isinstance(response_items, list):
        return book_map
    for i, item in enumerate(response_items):
        if not isinstance(item, dict):
            continue
        tok = str(item.get("asset_id") or "").strip()
        if not tok and i < len(token_ids):
            tok = token_ids[i]
        if tok:
            book_map[tok] = item
    return book_map


def _snapshot_for_token(
    *,
    token_id: str,
    outcome_index: int,
    outcome_label: Optional[str],
    book: Optional[Dict[str, Any]],
    fetch_status_when_missing: str,
) -> Dict[str, Any]:
    snap: Dict[str, Any] = {
        "outcome_index": outcome_index,
        "outcome_label": outcome_label,
        "token_id": token_id,
        "book_timestamp": None,
        "tick_size": None,
        "neg_risk": None,
        "best_bid": None,
        "best_ask": None,
        "best_bid_size": None,
        "best_ask_size": None,
        "spread_book_computed": None,
        "midpoint_book_computed": None,
        "bid_depth_1c": None,
        "ask_depth_1c": None,
        "bid_depth_5c": None,
        "ask_depth_5c": None,
        "depth_imbalance": None,
        "book_sort_observed": None,
        "fetch_status": fetch_status_when_missing,
    }

    if not isinstance(book, dict):
        return snap

    bids = book.get("bids") or []
    asks = book.get("asks") or []
    snap["book_timestamp"] = book.get("timestamp")
    snap["tick_size"] = _safe_float(book.get("tick_size"))
    snap["neg_risk"] = book.get("neg_risk")

    if bids and isinstance(bids[0], dict) and len(bids) > 1:
        first = _safe_float(bids[0].get("price"))
        last = _safe_float(bids[-1].get("price"))
        if first is not None and last is not None and first != last:
            snap["book_sort_observed"] = "bids_floor_first" if first < last else "bids_best_first"

    best_bid, best_ask, spread_book, midpoint_book, bbs, bas = compute_best_prices(bids, asks)
    snap["best_bid"] = best_bid
    snap["best_ask"] = best_ask
    snap["best_bid_size"] = bbs
    snap["best_ask_size"] = bas
    snap["spread_book_computed"] = spread_book
    snap["midpoint_book_computed"] = midpoint_book

    snap["bid_depth_1c"] = compute_depth_at_band(bids, best_bid, 0.01, direction="bid")
    snap["ask_depth_1c"] = compute_depth_at_band(asks, best_ask, 0.01, direction="ask")
    snap["bid_depth_5c"] = compute_depth_at_band(bids, best_bid, 0.05, direction="bid")
    snap["ask_depth_5c"] = compute_depth_at_band(asks, best_ask, 0.05, direction="ask")
    snap["depth_imbalance"] = compute_depth_imbalance(snap["bid_depth_1c"], snap["ask_depth_1c"])

    if best_bid is not None and best_ask is not None:
        snap["fetch_status"] = "ok"
    elif best_bid is not None or best_ask is not None:
        snap["fetch_status"] = "one_sided_book"
    else:
        snap["fetch_status"] = "empty_book"
    return snap


def _market_info_extract(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    return {
        "condition_id": payload.get("condition_id"),
        "question_id": payload.get("question_id"),
        "market_slug": payload.get("market_slug"),
        "active": payload.get("active"),
        "closed": payload.get("closed"),
        "archived": payload.get("archived"),
        "accepting_orders": payload.get("accepting_orders"),
        "accepting_order_timestamp": payload.get("accepting_order_timestamp"),
        "enable_order_book": payload.get("enable_order_book"),
        "neg_risk": payload.get("neg_risk"),
        "neg_risk_market_id": payload.get("neg_risk_market_id"),
        "neg_risk_request_id": payload.get("neg_risk_request_id"),
        "minimum_tick_size": _safe_float(payload.get("minimum_tick_size")),
        "minimum_order_size": _safe_float(payload.get("minimum_order_size")),
        "maker_base_fee": _safe_float(payload.get("maker_base_fee")),
        "taker_base_fee": _safe_float(payload.get("taker_base_fee")),
        "end_date_iso": payload.get("end_date_iso"),
        "tokens_count": len(payload["tokens"]) if isinstance(payload.get("tokens"), list) else None,
    }


def build_clob_snapshot(
    identity_rows: Sequence[PolymarketMarketIdentity],
    options: ClobOptions,
    diagnostics: Dict[str, Any],
    *,
    request_get: Optional[Callable[..., Any]] = None,
    request_post: Optional[Callable[..., Any]] = None,
    as_of: Optional[str] = None,
    lifecycle_classifications: Optional[Sequence[LifecycleClassification]] = None,
) -> Dict[str, Any]:
    """Build the CLOB snapshot sidecar payload from the FULL in-memory identity sequence.

    Substrate invariant: this function MUST receive `identity_rows` (the in-memory
    Sequence[PolymarketMarketIdentity]), NOT the truncated rows list from
    metadata.sidecars.polymarket_market_identity_snapshot.rows. The latter caps at
    1000 rows; iterating it would silently reintroduce selection bias.
    """
    started = time.time()
    if as_of is None:
        from datetime import datetime, timezone

        as_of = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if not options.enabled:
        return {
            "schema_version": "polymarket_clob_snapshot.0",
            "enabled": False,
            "as_of": as_of,
            "row_count": 0,
            "rows": [],
            "diagnostics": {
                "enabled": False,
                "cap": options.cap,
                "batch_size": options.batch_size,
                "fetch_market_info": options.fetch_market_info,
                "candidate_pool_size": len(identity_rows),
                "reason": "clob_enrichment.enabled is false in polymarket_scan config",
            },
        }

    candidates, candidate_skip_counts = _pick_clob_eligible_rows(
        identity_rows,
        options.cap,
        lifecycle_classifications=lifecycle_classifications,
    )
    token_ids = _flatten_token_ids(candidates)
    batches = _chunk(token_ids, options.batch_size)

    client = CLOBClient(options, request_get=request_get, request_post=request_post)

    book_map: Dict[str, Any] = {}
    batch_diagnostics: Dict[str, Any] = {
        "batch_count": len(batches),
        "batch_size": options.batch_size,
        "batch_errors": [],
        "request_count": 0,
    }
    for i, batch in enumerate(batches):
        result = client.fetch_books_batch(batch)
        batch_diagnostics["request_count"] += int(result.get("request_count") or 0)
        if not result.get("ok"):
            batch_diagnostics["batch_errors"].append({
                "batch_index": i,
                "batch_size": len(batch),
                "status_code": result.get("status_code"),
                "error": result.get("error"),
            })
            continue
        batch_map = _build_book_map(batch, result.get("body"))
        for tok, book in batch_map.items():
            book_map[tok] = book

    rows: List[Dict[str, Any]] = []
    status_counts: Dict[str, int] = {}
    book_sort_counts: Dict[str, int] = {}

    market_info_call_count = 0
    market_info_error_count = 0

    for row in candidates:
        base_row: Dict[str, Any] = {
            "condition_id": row.condition_id,
            "market_id": row.market_id,
            "event_slug": row.event_slug,
            "market_slug": row.market_slug,
            "market_question": row.market_question,
            "as_of": as_of,
            "fetch_status": "pending",
            "token_snapshots": [],
            "market_info": None,
        }

        token_snapshots: List[Dict[str, Any]] = []
        for idx, tok in enumerate(row.clob_token_ids or ()):
            tok_str = str(tok)
            book = book_map.get(tok_str)
            outcome_label = row.outcomes[idx] if (row.outcomes and idx < len(row.outcomes)) else None
            # Polymarket's POST /books silently drops tokens whose CLOB book is
            # not actually published: enable_order_book=True at the Gamma level
            # is necessary but NOT sufficient (live verification 2026-05-12).
            # We classify the absence as `no_clob_book_for_token` so calibration
            # can audit the gap, NOT as a generic "missing from response".
            snap = _snapshot_for_token(
                token_id=tok_str,
                outcome_index=idx,
                outcome_label=outcome_label,
                book=book,
                fetch_status_when_missing="no_clob_book_for_token",
            )
            token_snapshots.append(snap)
            obs = snap.get("book_sort_observed")
            if obs:
                book_sort_counts[obs] = book_sort_counts.get(obs, 0) + 1

        base_row["token_snapshots"] = token_snapshots

        # Roll up market-level fetch_status from per-token outcomes.
        # Categories (in priority order so the rollup never collapses signal):
        #   ok                       — every token returned a two-sided book.
        #   partial_ok               — at least one token returned a two-sided book.
        #   one_sided_book_only      — every responding token returned a one-sided book.
        #   thin_or_partial_book     — mix of one-sided / empty / no-book across tokens.
        #   no_clob_book_published   — every token absent from the batch response (silent drop).
        #   all_token_errors         — non-empty error statuses on every token.
        token_statuses = [s["fetch_status"] for s in token_snapshots]
        if not token_statuses:
            base_row["fetch_status"] = "no_token_ids"
        elif all(s == "ok" for s in token_statuses):
            base_row["fetch_status"] = "ok"
        elif any(s == "ok" for s in token_statuses):
            base_row["fetch_status"] = "partial_ok"
        elif all(s == "one_sided_book" for s in token_statuses):
            base_row["fetch_status"] = "one_sided_book_only"
        elif all(s in ("no_clob_book_for_token", "empty_book") for s in token_statuses):
            base_row["fetch_status"] = "no_clob_book_published"
        elif all(s in ("ok", "one_sided_book", "empty_book", "no_clob_book_for_token") for s in token_statuses):
            base_row["fetch_status"] = "thin_or_partial_book"
        else:
            base_row["fetch_status"] = "all_token_errors"

        # Opt-in per-market metadata enrichment.
        if options.fetch_market_info and row.condition_id:
            market_info_call_count += 1
            info = client.fetch_market_info(row.condition_id)
            if info.get("ok"):
                base_row["market_info"] = _market_info_extract(info.get("body"))
            else:
                market_info_error_count += 1
                base_row["market_info_error"] = {
                    "status_code": info.get("status_code"),
                    "error": info.get("error"),
                }

        rows.append(base_row)
        status_counts[base_row["fetch_status"]] = status_counts.get(base_row["fetch_status"], 0) + 1

    elapsed = time.time() - started

    # Tokens requested vs returned: surfaces Polymarket's silent-drop behaviour
    # for tokens flagged enable_order_book=True at Gamma but with no CLOB book yet.
    requested_token_count = sum(len(row.clob_token_ids or ()) for row in candidates)
    returned_token_count = len(book_map)
    no_clob_book_token_count = max(0, requested_token_count - returned_token_count)
    no_clob_book_market_count = sum(
        1 for r in rows if r.get("fetch_status") == "no_clob_book_published"
    )

    snapshot = {
        "schema_version": "polymarket_clob_snapshot.0",
        "enabled": True,
        "as_of": as_of,
        "base_url": options.base_url,
        "cap": options.cap,
        "batch_size": options.batch_size,
        "fetch_market_info": options.fetch_market_info,
        "candidate_pool_size": len(identity_rows),
        "clob_eligible_pool_size": sum(
            1 for r in identity_rows if r.enable_order_book is True and r.clob_token_ids and r.condition_id
        ),
        "enriched_market_count": len(rows),
        "row_count": len(rows),
        "diagnostics": {
            "elapsed_seconds": round(elapsed, 3),
            "candidate_pool_size": len(identity_rows),
            "cap": options.cap,
            "batch_size": options.batch_size,
            "batch_count": batch_diagnostics["batch_count"],
            "batch_errors": batch_diagnostics["batch_errors"],
            "http_request_count": batch_diagnostics["request_count"] + market_info_call_count,
            "books_batch_request_count": batch_diagnostics["request_count"],
            "market_info_request_count": market_info_call_count,
            "market_info_error_count": market_info_error_count,
            "fetch_status_counts": status_counts,
            "book_sort_observed_counts": book_sort_counts,
            "tokens_requested": requested_token_count,
            "tokens_returned_with_book": returned_token_count,
            "no_clob_book_token_count": no_clob_book_token_count,
            "no_clob_book_market_count": no_clob_book_market_count,
            "candidate_skip_counts": candidate_skip_counts,
            "lifecycle_filter_applied": lifecycle_classifications is not None,
            "lifecycle_eligible_states": sorted(CLOB_ENRICHMENT_ELIGIBLE_STATES),
            "no_clob_book_silent_drop_explanation": (
                "Polymarket's POST /books returns 200 with a sparse list, silently "
                "omitting tokens whose CLOB orderbook is not currently published. "
                "enable_order_book=True at Gamma is necessary but not sufficient; "
                "GET /book?token_id=<tok> for these tokens returns 404 'No orderbook "
                "exists for the requested token id'. Verified 2026-05-12."
            ),
            "extraction_mode": "numeric_extrema",
            "midpoint_source": "book_computed_best_bid_best_ask_mean",
            "midpoint_endpoint_trust": "diagnostic_corroboration_only",
        },
        "rows": rows,
    }

    diagnostics["clob_snapshot_enriched_count"] = len(rows)
    diagnostics["clob_snapshot_status_counts"] = dict(status_counts)
    diagnostics["clob_snapshot_elapsed_seconds"] = round(elapsed, 3)
    diagnostics["clob_snapshot_http_request_count"] = (
        batch_diagnostics["request_count"] + market_info_call_count
    )

    return snapshot


def empty_clob_snapshot() -> Dict[str, Any]:
    """Stable disabled-shape sidecar for the failure envelope path."""
    return {
        "schema_version": "polymarket_clob_snapshot.0",
        "enabled": False,
        "row_count": 0,
        "rows": [],
        "diagnostics": {"reason": "scanner failure path; clob enrichment not attempted"},
    }
