"""
[PURPOSE]
- Teleology: Ingest raw StockGrid or AXLFI datasets and emit a byte-budgeted artifact for downstream agents.
- Mechanism: HTTP session -> dataset normalization -> merge/fuse -> sector integer encoding -> budget-aware packing of a compatibility matrix plus richer side datasets.
- Optimization: Converts repeated string categories (sector) into integer IDs, preserves the legacy matrix for continuity, and fills remaining byte budget with higher-signal sidecars before fallback texture.
- Persistence: Sector identity resolved via codex/refs/stockgrid_ticker_map.json (grows in-place per run via SEC EDGAR backfill).
- Compatibility: Main matrix stays stable while richer datasets are added alongside it when space allows.
[INTERFACE]
- Exports: `run(config, run_dir)`
- Inputs:
  - `config`: Zenith tool config envelope or raw config dict.
  - `run_dir`: Optional run directory (currently not required for persistence behavior).
- Outputs:
  - Returns: `ArtifactEnvelope` (schema-compliant dict envelope with `metadata` and `data`).
[FLOW]
- Ingest: `StockGridDirectEngine.ingest_all()` downloads datasets into in-memory DataFrames.
- Enrich: `SecSectorEnricher.enrich()` backfills missing sectors from codex/refs/stockgrid_ticker_map.json,
          lazily resolving unknowns via SEC EDGAR (company_tickers.json -> submissions CIK).
- Fuse: `PayloadFactory.fuse()` merges dark pool, signals, and clusters into a unified table.
- Build: `PayloadFactory.build()` selects named rows (whales + setups), encodes categories, and fills remaining bytes with texture rows.
- Emit: `StandardActor.execute()` returns a success/failure artifact envelope and flushes the grown ticker map.
[DEPENDENCIES]
- pypi.requests: stockgrid_api, sec_edgar, axlfi_public_api
- pypi.pandas: dataset_joins
- env.STOCKGRID_KEY: optional legacy authentication
[CONSTRAINTS]
- Network I/O: Uses HTTP GET requests; obeys configurable timeout. SEC calls rate-limited to ~8 req/s.
- Size budget: Attempts to fit the emitted artifact under a configurable `target_kb` budget.
- Determinism: Uses a fixed `random_state` for texture sampling to reduce variance across runs.
- Ref persistence: stockgrid_ticker_map.json is written atomically (temp-file swap) after each successful run.
- When-needed: Open when a market-intelligence workflow needs the StockGrid dark-pool and signal lane, including provider fallback, SEC sector backfill, and the byte-budgeted stockgrid artifact shape.
- Escalates-to: tools/stock/stock.py::run; tools/calculator/calculator.py::run; tools/oracle/subject_index.py::run
- Navigation-group: market_intelligence
"""

import json
import math
import os
import re
import time
from datetime import datetime, timezone
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlencode

from system.lib import feed_envelope
from system.lib.types import TOOL_METADATA_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# 0. UTILS
# ---------------------------------------------------------------------------


class SectorMap:
    """
    [ROLE]
    - Teleology: Compress categorical sector strings into stable integer identifiers.
    - Mechanism: Maintain an in-memory mapping with a reserved Unknown=0 entry.
    """

    def __init__(self) -> None:
        self.mapping: Dict[str, int] = {"Unknown": 0}
        self.next_id: int = 1

    def encode(self, sector: str) -> int:
        """
        [ACTION]
        - Teleology: Compress a sector label into a stable integer ID for byte-budgeted matrix encoding.
        - Mechanism: Normalize to stripped string; allocate new ID on first-seen; reuse existing mapping thereafter.
        - Reads: sector (arg); self.mapping; self.next_id.
        - Writes: self.mapping (may add new key); self.next_id (may increment).
        - Orders: Deterministic within-process given first-seen order; IDs depend on encounter order across calls.
        - Fails: None.
        - Guarantee: Returns an int ID; after return, str(sector).strip() exists in self.mapping and mapped to returned ID.
        """
        s = str(sector).strip()
        if s not in self.mapping:
            self.mapping[s] = self.next_id
            self.next_id += 1
        return self.mapping[s]

    def export(self) -> Dict[str, int]:
        """
        [ACTION]
        - Teleology: Expose the current sector->int encoding table for embedding into artifact metadata.
        - Mechanism: Return the internal mapping object (live reference, not a copy).
        - Guarantee: Returns a Dict[str, int] representing the current encoder state.
        """
        return self.mapping


# ---------------------------------------------------------------------------
# 0.5. SEC SECTOR ENRICHER
# ---------------------------------------------------------------------------

# SIC code → human-readable sector label (top-level NAICS/SIC division mapping).
# Stable — SIC divisions haven't changed. Extend if you need finer granularity.
_SIC_SECTOR_MAP: List[tuple] = [
    (range(100,   1000),  "Agriculture"),
    (range(1000,  1500),  "Mining"),
    (range(1500,  1800),  "Construction"),
    (range(2000,  4000),  "Manufacturing"),
    (range(4000,  4900),  "Transportation & Utilities"),
    (range(4900,  5000),  "Utilities"),
    (range(5000,  5200),  "Wholesale Trade"),
    (range(5200,  5900),  "Retail Trade"),
    (range(6000,  6800),  "Finance & Insurance"),
    (range(6800,  7000),  "Real Estate"),
    (range(7000,  7400),  "Services"),
    (range(7370,  7380),  "Technology"),          # SIC 737x = Computer Services
    (range(7380,  8000),  "Services"),
    (range(8000,  8100),  "Health Services"),
    (range(8100,  8700),  "Professional Services"),
    (range(8700,  9000),  "Engineering & Management"),
    (range(9000,  9999),  "Public Administration"),
]


def _sic_to_sector(sic: int) -> str:
    """Map a raw SIC integer to a human sector label. Returns 'Unknown' if unmapped."""
    for r, label in _SIC_SECTOR_MAP:
        if sic in r:
            return label
    return "Unknown"


# Where your ref file lives relative to this script's project root.
# ai_workflow/codex/refs/stockgrid_ticker_map.json
_DEFAULT_TICKER_MAP_PATH = Path(__file__).resolve().parents[2] / "codex" / "refs" / "stockgrid_ticker_map.json"

# SEC public endpoints — no auth required, but User-Agent header is mandatory.
_SEC_TICKERS_URL    = "https://www.sec.gov/files/company_tickers.json"
_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_SEC_USER_AGENT     = "ai_workflow research@localhost.dev"
_AXLFI_PUBLIC_BASE  = "https://axlfi.com/axlfi-app-backend"
_AXLFI_DEFAULT_STRATEGY = "nasdaq_mom"
_AXLFI_ALLOWED_PROVIDER_MODES = {"legacy", "axlfi_public", "auto"}


def _to_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "nan"):
            return None
        parsed = float(value)
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _round_float(value: Any, digits: int = 4) -> Optional[float]:
    parsed = _to_float(value)
    if parsed is None:
        return None
    return round(parsed, digits)


def _count_message_matches(messages: List[str], needle: str) -> int:
    lowered = needle.strip().lower()
    if not lowered:
        return 0
    return sum(1 for message in messages if lowered in str(message).lower())


def _build_quality_block(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    warnings = diagnostics.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = [str(warnings)] if warnings else []

    reasons: List[str] = []
    blocked_metrics: List[str] = []
    tone = "ok"

    html_response_count = int(diagnostics.get("html_response_count", 0) or 0)
    provider_fallback_used = bool(diagnostics.get("provider_fallback_used", False))
    join_eligible_rows = int(diagnostics.get("join_eligible_rows", 0) or 0)
    join_matched_rows = int(diagnostics.get("join_matched_rows", 0) or 0)
    join_hit_rate_eligible = _to_float(diagnostics.get("join_hit_rate_eligible"))

    if provider_fallback_used:
        tone = "warn"
        reasons.append("legacy provider fallback used; stockgrid stayed usable but is degraded")

    if html_response_count > 0:
        tone = "block"
        reasons.append(f"provider returned {html_response_count} HTML landing-page responses")
        blocked_metrics.append("provider_transport")

    if join_eligible_rows > 0 and join_hit_rate_eligible is not None:
        coverage_reason = (
            f"eligible join coverage {join_hit_rate_eligible * 100:.1f}% "
            f"({join_matched_rows}/{join_eligible_rows})"
        )
        if join_hit_rate_eligible < 0.25:
            tone = "block"
            reasons.append(coverage_reason)
            blocked_metrics.append("join_coverage")
        elif join_hit_rate_eligible < 0.75:
            if tone != "block":
                tone = "warn"
            reasons.append(coverage_reason)

    if tone == "ok" and warnings:
        first_warning = str(warnings[0]).strip()
        if first_warning:
            tone = "warn"
            reasons.append(first_warning)

    quality: Dict[str, Any] = {"tone": tone, "reasons": list(dict.fromkeys(reasons))}
    if blocked_metrics:
        quality["blocked_metrics"] = list(dict.fromkeys(blocked_metrics))
    return quality


class SecSectorEnricher:
    """
    [ROLE]
    - Teleology: Backfill missing sector labels from codex/refs/stockgrid_ticker_map.json,
      lazily resolving unknowns from SEC EDGAR (company_tickers.json + submissions endpoint).
    - Mechanism:
        1. Load the ref file into self.identity_map (ticker → {sector, sic, cik, title}).
        2. On enrich(tickers), cache-hit first; for misses, resolve CIK then fetch sic+sicDescription.
        3. Write updated map back to disk after the run (caller-driven via flush()).
    - Persistence: The ref file grows monotonically — known tickers are never re-fetched from SEC.
    - Compatibility: identity_map values are dicts; consumers should use .get("sector", "Unknown").
    """

    def __init__(
        self,
        ticker_map_path: Path = _DEFAULT_TICKER_MAP_PATH,
        session: Optional[requests.Session] = None,
        rate_limit_s: float = 0.13,   # ~7.7 req/s — stays safely under SEC's informal 10 req/s cap
        sec_enabled: bool = True,
        sec_per_run_limit: int = 200,  # cap SEC calls per run; map grows incrementally across runs
    ) -> None:
        self.ticker_map_path = ticker_map_path
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": _SEC_USER_AGENT})
        self.rate_limit_s = rate_limit_s
        self.sec_enabled = sec_enabled
        self.sec_per_run_limit = sec_per_run_limit

        # identity_map: ticker (str, upper) → {"sector": str, "sic": int|None, "cik": str|None, "title": str|None}
        self.identity_map: Dict[str, Dict[str, Any]] = self._load_ref()

        # CIK index: ticker → zero-padded 10-digit CIK string. Loaded lazily once.
        self._cik_index: Dict[str, str] = {}
        self._cik_index_loaded: bool = False

        # Diagnostics
        self.diagnostics: Dict[str, Any] = {
            "sec_hits": 0,
            "sec_misses": 0,   # ticker not found in SEC tickers index
            "cache_hits": 0,
            "sec_errors": [],
            "map_new_entries": 0,
        }

    # ------------------------------------------------------------------
    # Ref file I/O
    # ------------------------------------------------------------------

    def _load_ref(self) -> Dict[str, Dict[str, Any]]:
        """
        [ACTION]
        - Teleology: Load the persistent ticker→sector map from disk.
        - Mechanism: Accept only rich dict entries with a resolved sector (sic populated OR known sector).
          Flat strings and Unknown-placeholder entries are skipped — let SEC re-resolve on demand.
        - Guarantee: Always returns a dict (possibly empty).
        """
        KNOWN_SECTORS = {
            'Technology', 'Financial', 'Consumer Cyclical', 'Consumer Defensive',
            'Healthcare', 'Industrials', 'Communication Services', 'Energy',
            'Utilities', 'Basic Materials', 'Real Estate',
        }
        try:
            if self.ticker_map_path.exists():
                data = json.loads(self.ticker_map_path.read_text(encoding="utf-8"))
                normalised: Dict[str, Dict[str, Any]] = {}
                for ticker, val in data.items():
                    t = str(ticker).strip().upper()
                    if not isinstance(val, dict):
                        continue
                    sector = val.get("sector", "")
                    sic = val.get("sic")
                    # Keep if SEC-sourced (sic present) or exact StockGrid signal sector
                    if sic is not None or sector in KNOWN_SECTORS:
                        normalised[t] = val
                    # Skip Unknown-placeholders and company-name entries → will SEC-resolve lazily
                return normalised
        except Exception:
            pass
        return {}

    def flush(self) -> None:
        """
        [ACTION]
        - Teleology: Atomically write the grown identity_map back to stockgrid_ticker_map.json.
        - Mechanism: Write only resolved entries (sic present or known sector) — avoids re-polluting
          the file with Unknown placeholders. Uses .tmp rename for crash safety.
        - Fails: Any exception is silently swallowed — flush failure must never break the artifact pipeline.
        - Guarantee: If flush succeeds, the ref file on disk reflects resolved entries only.
        """
        KNOWN_SECTORS = {
            'Technology', 'Financial', 'Consumer Cyclical', 'Consumer Defensive',
            'Healthcare', 'Industrials', 'Communication Services', 'Energy',
            'Utilities', 'Basic Materials', 'Real Estate',
        }
        try:
            self.ticker_map_path.parent.mkdir(parents=True, exist_ok=True)
            to_write = {
                t: v for t, v in self.identity_map.items()
                if isinstance(v, dict) and (
                    v.get("sic") is not None or v.get("sector", "") in KNOWN_SECTORS
                )
            }
            tmp = self.ticker_map_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(to_write, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp.replace(self.ticker_map_path)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # SEC index
    # ------------------------------------------------------------------

    def _load_cik_index(self) -> None:
        """
        [ACTION]
        - Teleology: Build the in-memory ticker→CIK index from SEC's company_tickers.json.
        - Mechanism: Single GET; parse all entries into self._cik_index (uppercase ticker → zero-padded CIK).
        - Orders: Called at most once per instance (guarded by self._cik_index_loaded).
        - Fails: Any network/parse error is recorded to diagnostics; _cik_index stays empty (enricher degrades gracefully).
        """
        if self._cik_index_loaded:
            return
        if not self.sec_enabled:
            self._cik_index_loaded = True
            return
        try:
            r = self.session.get(_SEC_TICKERS_URL, timeout=20)
            r.raise_for_status()
            data = r.json()
            for entry in data.values():
                ticker = str(entry.get("ticker", "")).strip().upper()
                cik    = str(entry.get("cik_str", "")).strip().zfill(10)
                if ticker:
                    self._cik_index[ticker] = cik
        except Exception as e:
            self.diagnostics["sec_errors"].append(f"cik_index: {e}")
        finally:
            self._cik_index_loaded = True

    def _fetch_sec_entry(self, ticker: str, cik: str) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Fetch sic + sicDescription for a single ticker from SEC submissions endpoint.
        - Mechanism: GET data.sec.gov/submissions/CIK{cik}.json; extract sic (int) and sicDescription (str).
        - Reads: cik; network.
        - Writes: self.diagnostics.
        - Fails: Any exception returns a minimal Unknown entry; error appended to diagnostics.
        - Guarantee: Always returns a dict with at minimum {"sector": str, "sic": int|None, "cik": str, "title": str|None}.
        """
        try:
            url = _SEC_SUBMISSIONS_URL.format(cik=cik)
            r = self.session.get(url, timeout=12)
            r.raise_for_status()
            data = r.json()

            sic_raw  = data.get("sic")
            sic_desc = data.get("sicDescription", "")   # e.g. "SERVICES-COMPUTER PROGRAMMING, DATA PROCESSING"
            title    = data.get("name", None)

            try:
                sic_int = int(sic_raw) if sic_raw is not None and str(sic_raw).strip() else None
            except (TypeError, ValueError):
                sic_int = None
            # Prefer sicDescription (human) if non-empty; fall back to SIC division label
            if sic_desc and str(sic_desc).strip():
                sector = str(sic_desc).strip().title()
            elif sic_int is not None:
                sector = _sic_to_sector(sic_int)
            else:
                sector = "Unknown"

            self.diagnostics["sec_hits"] += 1
            return {"sector": sector, "sic": sic_int, "cik": cik, "title": title}

        except Exception as e:
            self.diagnostics["sec_errors"].append(f"{ticker}: {e}")
            return {"sector": "Unknown", "sic": None, "cik": cik, "title": None}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich(self, tickers: List[str]) -> Dict[str, str]:
        """
        [ACTION]
        - Teleology: Return a ticker→sector string mapping for all requested tickers, growing
          the identity_map in-place for any previously unseen tickers.
        - Mechanism:
            1. Cache-hit from self.identity_map → immediate return, no network.
            2. Miss → ensure CIK index is loaded → look up CIK → fetch SEC submissions → store entry.
            3. Ticker absent from SEC index → store Unknown entry (won't retry next run unless you delete the entry).
        - Reads: self.identity_map; self._cik_index (lazy); network (SEC, rate-limited).
        - Writes: self.identity_map (new entries); self.diagnostics.
        - Fails: Per-ticker errors produce "Unknown" entries; never raises.
        - Guarantee: Returns Dict[str, str] mapping every input ticker to a sector string.
        - When-needed: Open when StockGrid rows are still sectorless and you need the exact cache-first SEC enrichment rules instead of tracing the whole artifact builder.
        - Escalates-to: codex/refs/stockgrid_ticker_map.json; tools/oracle/subject_index.py::run
        """
        self._load_cik_index()  # no-op after first call

        result: Dict[str, str] = {}
        sec_calls_this_run = 0

        for raw_ticker in tickers:
            t = str(raw_ticker).strip().upper()
            if not t:
                continue

            # 1. Cache hit
            if t in self.identity_map:
                result[t] = self.identity_map[t].get("sector", "Unknown")
                self.diagnostics["cache_hits"] += 1
                continue

            # 2. SEC lookup (rate-limited and capped per run)
            cik = self._cik_index.get(t)
            if cik and self.sec_enabled and sec_calls_this_run < self.sec_per_run_limit:
                time.sleep(self.rate_limit_s)
                entry = self._fetch_sec_entry(t, cik)
                sec_calls_this_run += 1
            else:
                self.diagnostics["sec_misses"] += 1
                entry = {"sector": "Unknown", "sic": None, "cik": None, "title": None}

            self.identity_map[t] = entry
            self.diagnostics["map_new_entries"] += 1
            result[t] = entry["sector"]

        return result


# ---------------------------------------------------------------------------
# 1. THE ENGINE (INGEST)
# ---------------------------------------------------------------------------


class StockGridDirectEngine:
    """
    [ROLE]
    - Teleology: Retrieve remote StockGrid datasets and store them as normalized DataFrames.
    - Mechanism: HTTP session -> dataset-specific parsing -> column normalization -> in-memory DB.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config: Dict[str, Any] = config
        self.endpoints: Dict[str, Any] = config.get("endpoints", {})
        self.api_key: str = os.getenv("STOCKGRID_KEY", "")
        provider_cfg = config.get("provider", {}) if isinstance(config.get("provider"), dict) else {}
        raw_provider_mode = provider_cfg.get("mode", "legacy")
        provider_mode = str(raw_provider_mode).strip().lower() if raw_provider_mode is not None else "legacy"
        if provider_mode not in _AXLFI_ALLOWED_PROVIDER_MODES:
            provider_mode = "legacy"
        self.provider_mode: str = provider_mode
        self.axlfi_cfg: Dict[str, Any] = (
            provider_cfg.get("axlfi_public", {})
            if isinstance(provider_cfg.get("axlfi_public"), dict)
            else {}
        )
        runtime_cfg   = config.get("runtime", {}) if isinstance(config.get("runtime", {}), dict) else {}
        execution_cfg = config.get("execution", {}) if isinstance(config.get("execution", {}), dict) else {}
        timeout_val   = runtime_cfg.get("timeout")
        if timeout_val is None:
            timeout_val = execution_cfg.get("timeout", 15.0)
        try:
            self.timeout = float(timeout_val)
        except (TypeError, ValueError):
            self.timeout = 15.0

        self.session: requests.Session = requests.Session()
        self.memory_db: Dict[str, pd.DataFrame] = {}
        self.diagnostics: Dict[str, Any] = {
            "fetched": {},
            "errors": [],
            "warnings": [],
            "provider_mode": provider_mode,
            "provider_used": None,
        }

    def authenticate(self) -> bool:
        """
        [ACTION]
        - Teleology: Gate remote ingestion behind an auth step when required by upstream StockGrid endpoints.
        - Mechanism: Placeholder — unconditionally succeeds.
        - Guarantee: Returns True.
        """
        return True

    def fetch_dataset(self, name: str, parser_type: str = "standard") -> None:
        """
        [ACTION]
        - Teleology: Fetch a named StockGrid dataset over HTTP and materialize it as a normalized DataFrame.
        - Mechanism: Resolve URL; GET; parse JSON (robust to stringified JSON); select parser; normalize columns.
        - Fails: Any exception is caught and recorded to self.diagnostics["errors"]; never raises.
        - Guarantee: If non-empty DataFrame produced, self.memory_db[name] exists.
        """
        url = self.endpoints.get(name)
        if not url:
            return
        try:
            data = self._fetch_json(url, name)
            if data is None:
                return
            df = pd.DataFrame()

            if parser_type == "standard":
                df = pd.DataFrame(data)
            elif parser_type == "wrapper":
                if isinstance(data, dict) and "data" in data:
                    df = pd.DataFrame(data["data"])
            elif parser_type == "clusters":
                all_rows: List[Any] = []
                if isinstance(data, dict):
                    for _, content in data.items():
                        if isinstance(content, dict) and "data" in content:
                            all_rows.extend(content["data"])
                df = pd.DataFrame(all_rows)

            if not df.empty:
                df.columns = df.columns.str.lower().str.strip()
                self.memory_db[name] = df
                self.diagnostics["fetched"][name] = len(df)
                feed_envelope.record_fetch_outcome(self.diagnostics, ok=True)
            else:
                self.diagnostics["errors"].append(f"{name} empty")
                feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
                feed_envelope.append_partial_failure(
                    self.diagnostics,
                    feed_envelope.warning_event(
                        code="stockgrid_fetch_failed",
                        lane="stockgrid",
                        message=f"{name} empty",
                        endpoint=name,
                    ),
                )

        except Exception as e:
            self.diagnostics["errors"].append(f"{name} error: {str(e)}")
            feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
            feed_envelope.append_partial_failure(
                self.diagnostics,
                feed_envelope.warning_event(
                    code="stockgrid_fetch_failed",
                    lane="stockgrid",
                    exc=e,
                    message=f"{name} error: {str(e)}",
                    endpoint=name,
                ),
            )

    def _fetch_json(self, url: str, name: str) -> Optional[Any]:
        try:
            r = self.session.get(url, timeout=self.timeout)
        except Exception as e:
            self.diagnostics["errors"].append(f"{name} error: {str(e)}")
            feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
            feed_envelope.append_partial_failure(
                self.diagnostics,
                feed_envelope.warning_event(
                    code="stockgrid_fetch_failed",
                    lane="stockgrid",
                    exc=e,
                    message=f"{name} error: {str(e)}",
                    endpoint=name,
                ),
            )
            return None

        if r.status_code != 200:
            self.diagnostics["errors"].append(f"{name} HTTP {r.status_code}")
            feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
            feed_envelope.append_partial_failure(
                self.diagnostics,
                feed_envelope.warning_event(
                    code="stockgrid_fetch_failed",
                    lane="stockgrid",
                    message=f"{name} HTTP {r.status_code}",
                    endpoint=name,
                    http_status=r.status_code,
                ),
            )
            return None

        final_url = str(getattr(r, "url", "") or url)
        content_type = str(getattr(r, "headers", {}).get("content-type", "") or "").lower()
        body_text = r.text if isinstance(getattr(r, "text", ""), str) else ""
        body_stripped = body_text.lstrip()
        redirect_urls = [
            str(getattr(prev, "url", "")).strip()
            for prev in getattr(r, "history", [])
            if str(getattr(prev, "url", "")).strip()
        ]
        if final_url:
            redirect_urls.append(final_url)
        redirect_chain = " -> ".join(dict.fromkeys(redirect_urls))

        if "json" not in content_type and body_stripped.startswith("<"):
            snippet = re.sub(r"\s+", " ", body_stripped)[:140]
            location = f" at {final_url}" if final_url else ""
            chain = f" via {redirect_chain}" if redirect_chain and redirect_chain != final_url else ""
            ctype = f" [{content_type}]" if content_type else ""
            detail = f"; snippet={snippet}" if snippet else ""
            html_error_message = f"{name} non-json HTML response{location}{chain}{ctype}{detail}"
            self.diagnostics["errors"].append(html_error_message)
            feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
            feed_envelope.append_partial_failure(
                self.diagnostics,
                feed_envelope.warning_event(
                    code="stockgrid_fetch_failed",
                    lane="stockgrid",
                    message=html_error_message,
                    endpoint=name,
                    http_status=r.status_code,
                ),
            )
            return None

        try:
            raw = r.json()
        except Exception as parse_err:
            snippet = re.sub(r"\s+", " ", body_stripped or body_text)[:140]
            location = f" at {final_url}" if final_url else ""
            ctype = f" [{content_type}]" if content_type else ""
            detail = f"; snippet={snippet}" if snippet else ""
            parse_error_message = f"{name} invalid JSON response{location}{ctype}: {parse_err}{detail}"
            self.diagnostics["errors"].append(parse_error_message)
            feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
            feed_envelope.append_partial_failure(
                self.diagnostics,
                feed_envelope.warning_event(
                    code="stockgrid_fetch_failed",
                    lane="stockgrid",
                    exc=parse_err,
                    message=parse_error_message,
                    endpoint=name,
                    http_status=r.status_code,
                ),
            )
            return None

        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception as parse_err:
                snippet = re.sub(r"\s+", " ", raw)[:140]
                detail = f"; snippet={snippet}" if snippet else ""
                nested_error_message = f"{name} invalid nested JSON string at {final_url}: {parse_err}{detail}"
                self.diagnostics["errors"].append(nested_error_message)
                feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
                feed_envelope.append_partial_failure(
                    self.diagnostics,
                    feed_envelope.warning_event(
                        code="stockgrid_fetch_failed",
                        lane="stockgrid",
                        exc=parse_err,
                        message=nested_error_message,
                        endpoint=name,
                        http_status=r.status_code,
                    ),
                )
                return None
        return raw

    def _extract_axlfi_strategy_win_rate(self, payload: Any) -> Optional[float]:
        if not isinstance(payload, dict):
            return None
        scopes = payload.get("metrics_by_scope", [])
        if not isinstance(scopes, list):
            return None
        for scope in scopes:
            if not isinstance(scope, dict) or scope.get("scope") != "trades":
                continue
            metrics = scope.get("metrics", [])
            if not isinstance(metrics, list):
                continue
            for metric in metrics:
                if not isinstance(metric, dict):
                    continue
                if str(metric.get("metric_name", "")).strip().lower() != "win rate %":
                    continue
                try:
                    value = float(metric.get("metric_value"))
                except (TypeError, ValueError):
                    return None
                return value
        return None

    def _normalise_axlfi_signal_rows(
        self,
        payload: Any,
        strategy_name: str,
        strategy_win_rate: Optional[float],
    ) -> List[Dict[str, Any]]:
        source_rows: List[Any]
        if isinstance(payload, list):
            source_rows = payload
        elif isinstance(payload, dict):
            candidate = payload.get("symbols")
            if not isinstance(candidate, list):
                candidate = payload.get("data")
            source_rows = candidate if isinstance(candidate, list) else []
        else:
            source_rows = []

        rows: List[Dict[str, Any]] = []
        for item in source_rows:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("symbol", "")).strip().upper()
            if not ticker:
                continue

            raw_dir = item.get("dir")
            try:
                direction_value = int(raw_dir)
            except (TypeError, ValueError):
                direction_value = 0
            direction_label = "long" if direction_value > 0 else "short" if direction_value < 0 else "flat"

            row: Dict[str, Any] = {
                "ticker": ticker,
                "factor": f"{strategy_name}:{direction_label}",
                "sector": str(item.get("sector", "")).strip() or "Unknown",
                "industry": str(item.get("industry", "")).strip() or None,
                "company": str(item.get("company", "")).strip() or None,
                "country": str(item.get("country", "")).strip() or None,
                "signal_dir": direction_value,
                "market_cap_b": _round_float(item.get("market_cap_b"), 2),
                "avg_volume": _round_float(item.get("avg_volume"), 0),
                "eps_next_5y_pct": _round_float(item.get("eps_next_5y_pct"), 2),
                "eps_next_y_pct": _round_float(item.get("eps_next_y_pct"), 2),
                "eps_q_q_pct": _round_float(item.get("eps_q_q_pct"), 2),
                "eps_this_y_pct": _round_float(item.get("eps_this_y_pct"), 2),
                "sales_q_q_pct": _round_float(item.get("sales_q_q_pct"), 2),
                "nasdaq100": int(bool(item.get("nasdaq100"))),
                "sp500": int(bool(item.get("sp500"))),
                "russell2000": int(bool(item.get("russel2000") or item.get("russell2000"))),
            }
            if strategy_win_rate is not None:
                row["profitable%"] = strategy_win_rate

            momentum = item.get("momentum")
            if isinstance(momentum, dict):
                for key, value in momentum.items():
                    row[f"momentum_{key}"] = _round_float(value, 4)

            rows.append(row)
        return rows

    def _extract_axlfi_signal_history_rows(self, payload: Any) -> List[Dict[str, Any]]:
        source_rows: List[Any]
        if isinstance(payload, list):
            source_rows = payload
        elif isinstance(payload, dict):
            candidate = payload.get("symbols")
            if not isinstance(candidate, list):
                candidate = payload.get("data")
            source_rows = candidate if isinstance(candidate, list) else []
        else:
            source_rows = []

        rows: List[Dict[str, Any]] = []
        for item in source_rows:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("symbol", "")).strip().upper()
            if not ticker:
                continue
            history = item.get("history", [])
            if not isinstance(history, list):
                continue
            for point in history:
                if not isinstance(point, dict):
                    continue
                date = str(point.get("date", "")).strip()
                if not date:
                    continue
                rows.append(
                    {
                        "ticker": ticker,
                        "date": date,
                        "close": _round_float(point.get("close"), 4),
                        "momentum_1d": _round_float(point.get("momentum_1d"), 4),
                        "momentum_10d": _round_float(point.get("momentum_10d"), 4),
                        "momentum_20d": _round_float(point.get("momentum_20d"), 4),
                        "momentum_60d": _round_float(point.get("momentum_60d"), 4),
                        "momentum_120d": _round_float(point.get("momentum_120d"), 4),
                        "momentum_250d": _round_float(point.get("momentum_250d"), 4),
                    }
                )
        return rows

    def _normalise_axlfi_dark_pool_rows(self, payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        source_rows = payload.get("data", [])
        if not isinstance(source_rows, list):
            return []

        rows: List[Dict[str, Any]] = []
        for item in source_rows:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker", "")).strip().upper()
            if not ticker:
                continue
            row = dict(item)
            row["ticker"] = ticker
            row["dark pools position $"] = item.get("dollar_dp_position")
            row["short volume %"] = item.get("short_volume_percent")
            row["dp_sector"] = str(item.get("sector", "")).strip() or "Unknown"
            rows.append(row)
        return rows

    def _normalise_axlfi_dark_pool_symbol_row(
        self,
        payload: Any,
        fallback: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None

        latest = payload.get("latest", {}) if isinstance(payload.get("latest"), dict) else {}
        short_rows = (
            payload.get("individual_short_volume_table", [])
            if isinstance(payload.get("individual_short_volume_table"), list)
            else []
        )
        latest_short = short_rows[-1] if short_rows and isinstance(short_rows[-1], dict) else {}
        prices = payload.get("prices", {}) if isinstance(payload.get("prices"), dict) else {}
        price_dates = prices.get("dates", []) if isinstance(prices.get("dates"), list) else []
        price_values = prices.get("prices", []) if isinstance(prices.get("prices"), list) else []

        ticker = str(payload.get("symbol", "")).strip().upper()
        if not ticker and fallback is not None:
            ticker = str(fallback.get("ticker", "")).strip().upper()
        if not ticker:
            return None

        close = price_values[-1] if price_values else None
        as_of_date = payload.get("as_of_date")
        date = (
            str(as_of_date).strip()
            if isinstance(as_of_date, str) and str(as_of_date).strip()
            else latest_short.get("date") or (price_dates[-1] if price_dates else None)
        )
        row = {
            "ticker": ticker,
            "date": date,
            "company": fallback.get("company") if isinstance(fallback, dict) else None,
            "sector": fallback.get("sector") if isinstance(fallback, dict) else None,
            "industry": fallback.get("industry") if isinstance(fallback, dict) else None,
            "close": close,
            "short_exempt_volume": latest_short.get("short_exempt_volume"),
            "short_volume": latest_short.get("short_volume"),
            "short_volume_percent": latest_short.get("short_volume_pct"),
            "market": latest_short.get("market"),
            "total_volume": latest_short.get("total_volume"),
            "net_volume": latest.get("net_volume"),
            "dollar_net_volume": latest.get("dollar_net_volume"),
            "dp_position": latest.get("dp_position"),
            "dollar_dp_position": latest.get("dollar_dp_position"),
        }
        row["dark pools position $"] = row["dollar_dp_position"]
        row["short volume %"] = row["short_volume_percent"]
        row["dp_sector"] = str(row.get("sector", "")).strip() or "Unknown"
        return row

    def _normalise_axlfi_cluster_rows(self, payload: Any, universe: str) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        datasets = payload.get("datasets") if isinstance(payload.get("datasets"), dict) else payload
        if not isinstance(datasets, dict):
            return []
        requested_key = str(universe or "all").strip().lower() or "all"
        block = datasets.get(requested_key) or datasets.get("all")
        if not isinstance(block, dict):
            return []
        source_rows = block.get("data", [])
        if not isinstance(source_rows, list):
            return []

        rows: List[Dict[str, Any]] = []
        for item in source_rows:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker", "")).strip().upper()
            if not ticker:
                continue
            row = dict(item)
            row["ticker"] = ticker
            rows.append(row)
        return rows

    def _normalise_axlfi_index_return_rows(self, payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        block = payload.get("index_returns", {})
        if not isinstance(block, dict):
            return []
        quotes = block.get("index_quotes", [])
        if not isinstance(quotes, list):
            return []

        rows: List[Dict[str, Any]] = []
        as_of_date = block.get("as_of_date")
        prior_date = block.get("prior_date")
        for item in quotes:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker", "")).strip().upper()
            if not ticker:
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "label": str(item.get("label", "")).strip() or ticker,
                    "close": _round_float(item.get("close"), 4),
                    "previous_close": _round_float(item.get("previous_close"), 4),
                    "change": _round_float(item.get("change"), 4),
                    "change_pct": _round_float(item.get("change_pct"), 4),
                    "as_of_date": as_of_date,
                    "prior_date": prior_date,
                }
            )
        return rows

    def _normalise_axlfi_mover_rows(self, payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        block = payload.get("movers", {})
        if not isinstance(block, dict):
            return []
        as_of_date = block.get("as_of_date")
        prior_date = block.get("prior_date")
        rows: List[Dict[str, Any]] = []
        for bucket in (
            "top_price_gainers",
            "top_price_losers",
            "top_volume_gainers",
            "top_volume_losers",
        ):
            source_rows = block.get(bucket, [])
            if not isinstance(source_rows, list):
                continue
            for item in source_rows:
                if not isinstance(item, dict):
                    continue
                ticker = str(item.get("ticker", "")).strip().upper()
                if not ticker:
                    continue
                rows.append(
                    {
                        "bucket": bucket,
                        "ticker": ticker,
                        "change_pct": _round_float(item.get("change_pct"), 4),
                        "current_close": _round_float(item.get("current_close"), 4),
                        "prior_close": _round_float(item.get("prior_close"), 4),
                        "current_volume": _round_float(item.get("current_volume"), 2),
                        "as_of_date": as_of_date,
                        "prior_date": prior_date,
                    }
                )
        return rows

    def _normalise_axlfi_overview_rows(
        self,
        dashboard_payload: Any,
        strategy_metrics_payload: Any,
        strategy_name: str,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        if isinstance(dashboard_payload, dict):
            strategy_block = dashboard_payload.get("strategy_metrics", {})
            volatility_regime = (
                strategy_block.get("volatility_regime", {})
                if isinstance(strategy_block, dict)
                else {}
            )
            if isinstance(volatility_regime, dict) and volatility_regime:
                rows.append(
                    {
                        "group": "volatility_regime",
                        "metric": "current_regime",
                        "value": volatility_regime.get("current_regime"),
                        "note": volatility_regime.get("tier_label"),
                        "context": strategy_name,
                    }
                )
                rows.append(
                    {
                        "group": "volatility_regime",
                        "metric": "next_open_flag",
                        "value": int(bool(volatility_regime.get("is_next_open"))),
                        "note": volatility_regime.get("date"),
                        "context": strategy_name,
                    }
                )

            movers = dashboard_payload.get("movers", {})
            if isinstance(movers, dict):
                sector_leaders = movers.get("sector_leaders_1d", {})
                if isinstance(sector_leaders, dict):
                    rows.append(
                        {
                            "group": "sector_leaders_1d",
                            "metric": "best_sector",
                            "value": _round_float(sector_leaders.get("best_value"), 4),
                            "note": sector_leaders.get("best_sector"),
                            "context": strategy_name,
                        }
                    )
                    rows.append(
                        {
                            "group": "sector_leaders_1d",
                            "metric": "worst_sector",
                            "value": _round_float(sector_leaders.get("worst_value"), 4),
                            "note": sector_leaders.get("worst_sector"),
                            "context": strategy_name,
                        }
                    )

        if isinstance(strategy_metrics_payload, dict):
            for scope in strategy_metrics_payload.get("metrics_by_scope", []):
                if not isinstance(scope, dict):
                    continue
                scope_name = str(scope.get("scope", "")).strip() or "unknown"
                metrics = scope.get("metrics", [])
                if not isinstance(metrics, list):
                    continue
                for metric in metrics:
                    if not isinstance(metric, dict):
                        continue
                    rows.append(
                        {
                            "group": f"strategy:{scope_name}",
                            "metric": str(metric.get("metric_name", "")).strip() or "metric",
                            "value": _round_float(metric.get("metric_value"), 4),
                            "note": metric.get("metric_value_text"),
                            "context": strategy_name,
                        }
                    )
        return rows

    def _normalise_axlfi_tactical_rows(self, payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []

        momentum_lookup: Dict[str, Optional[float]] = {}
        for item in payload.get("momentum_1y", []):
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker", "")).strip().upper()
            if not ticker:
                continue
            momentum_lookup[ticker] = _round_float(item.get("momentum_1y"), 4)

        rows: List[Dict[str, Any]] = []
        for item in payload.get("positions", []):
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker", "")).strip().upper()
            if not ticker:
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "dir": int(item.get("dir", 0)) if str(item.get("dir", "")).strip() else 0,
                    "position": str(item.get("position", "")).strip() or None,
                    "rank": _round_float(item.get("rank"), 2),
                    "mom": _round_float(item.get("mom"), 4),
                    "mom_s": _round_float(item.get("mom_s"), 4),
                    "momentum_1y": momentum_lookup.get(ticker),
                }
            )
        return rows

    def _normalise_axlfi_period_return_rows(self, payload: Any, family: str) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        rows: List[Dict[str, Any]] = []
        for bucket, frequency in (
            ("period_returns_monthly", "M"),
            ("period_returns_yearly", "Y"),
            ("period_returns_latest", "L"),
        ):
            source_rows = payload.get(bucket, [])
            if not isinstance(source_rows, list):
                continue
            for item in source_rows:
                if not isinstance(item, dict):
                    continue
                rows.append(
                    {
                        "family": family,
                        "frequency": str(item.get("frequency", "")).strip() or frequency,
                        "period_date": str(item.get("period_date", "")).strip() or None,
                        "return_value": _round_float(item.get("return_value"), 6),
                    }
                )
        return rows

    def _store_dataframe(self, name: str, rows: List[Dict[str, Any]]) -> None:
        df = pd.DataFrame(rows)
        if df.empty:
            self.diagnostics["errors"].append(f"{name} empty")
            feed_envelope.record_fetch_outcome(self.diagnostics, ok=False)
            feed_envelope.append_partial_failure(
                self.diagnostics,
                feed_envelope.warning_event(
                    code="stockgrid_fetch_failed",
                    lane="stockgrid",
                    message=f"{name} empty",
                    endpoint=name,
                ),
            )
            return
        df.columns = df.columns.str.lower().str.strip()
        self.memory_db[name] = df
        self.diagnostics["fetched"][name] = len(df)
        feed_envelope.record_fetch_outcome(self.diagnostics, ok=True)

    def _ingest_legacy(self) -> None:
        if self.authenticate():
            self.fetch_dataset("signals", "standard")
            self.fetch_dataset("dark_pools", "wrapper")
            self.fetch_dataset("clusters", "clusters")
            if self.memory_db:
                self.diagnostics["provider_used"] = "legacy"

    def _ingest_axlfi_public(self) -> None:
        base = str(self.axlfi_cfg.get("base") or _AXLFI_PUBLIC_BASE).rstrip("/")
        strategy_name = str(self.axlfi_cfg.get("strategy_name") or _AXLFI_DEFAULT_STRATEGY).strip() or _AXLFI_DEFAULT_STRATEGY
        cluster_universe = str(self.axlfi_cfg.get("cluster_universe") or "all").strip().lower() or "all"
        dark_pools_metric = str(self.axlfi_cfg.get("dark_pools_metric") or "dollar_dp_position").strip() or "dollar_dp_position"
        dark_pools_sort = str(self.axlfi_cfg.get("dark_pools_sort") or "desc").strip().lower() or "desc"
        try:
            dark_pools_limit = int(self.axlfi_cfg.get("dark_pools_limit", 500))
        except (TypeError, ValueError):
            dark_pools_limit = 500

        signal_rows: List[Dict[str, Any]] = []
        signal_history_rows: List[Dict[str, Any]] = []
        strategy_metrics_payload = self._fetch_json(
            f"{base}/api/signals/strategy_metrics?{urlencode({'strategy_name': strategy_name})}",
            "strategy_metrics",
        )
        strategy_win_rate = self._extract_axlfi_strategy_win_rate(strategy_metrics_payload)
        strategy_period_rows = self._normalise_axlfi_period_return_rows(strategy_metrics_payload, strategy_name)
        if strategy_period_rows:
            self._store_dataframe("strategy_period_returns", strategy_period_rows)

        signals_payload = self._fetch_json(
            f"{base}/api/signals/signal_symbols?{urlencode({'strategy_name': strategy_name})}",
            "signals",
        )
        if signals_payload is not None:
            signal_rows = self._normalise_axlfi_signal_rows(signals_payload, strategy_name, strategy_win_rate)
            signal_history_rows = self._extract_axlfi_signal_history_rows(signals_payload)
            self._store_dataframe("signals", signal_rows)
            if signal_history_rows:
                self._store_dataframe("signal_history", signal_history_rows)

        dark_pools_rows: List[Dict[str, Any]] = []
        dark_pools_payload = self._fetch_json(
            f"{base}/api/dark_pools/leaderboard?{urlencode({'metric': dark_pools_metric, 'sort': dark_pools_sort, 'limit': dark_pools_limit})}",
            "dark_pools",
        )
        if dark_pools_payload is not None:
            dark_pools_rows = self._normalise_axlfi_dark_pool_rows(dark_pools_payload)

        dark_pool_tickers = {
            str(row.get("ticker", "")).strip().upper()
            for row in dark_pools_rows
            if str(row.get("ticker", "")).strip()
        }
        signal_symbol_snapshot_rows = 0
        for signal_row in signal_rows:
            ticker = str(signal_row.get("ticker", "")).strip().upper()
            if not ticker or ticker in dark_pool_tickers:
                continue
            symbol_payload = self._fetch_json(
                f"{base}/api/dark_pools/symbol?{urlencode({'symbol': ticker, 'window': 252})}",
                f"dark_pools:{ticker}",
            )
            symbol_row = self._normalise_axlfi_dark_pool_symbol_row(symbol_payload, signal_row)
            if symbol_row is None:
                continue
            dark_pools_rows.append(symbol_row)
            dark_pool_tickers.add(ticker)
            signal_symbol_snapshot_rows += 1
        if dark_pools_rows:
            self._store_dataframe("dark_pools", dark_pools_rows)

        clusters_payload = self._fetch_json(f"{base}/api/clusters/table", "clusters")
        if clusters_payload is not None:
            self._store_dataframe("clusters", self._normalise_axlfi_cluster_rows(clusters_payload, cluster_universe))

        dashboard_payload = self._fetch_json(f"{base}/api/dashboard/all", "dashboard")
        overview_rows: List[Dict[str, Any]] = self._normalise_axlfi_overview_rows(
            dashboard_payload,
            strategy_metrics_payload,
            strategy_name,
        )
        if dashboard_payload is not None:
            index_rows = self._normalise_axlfi_index_return_rows(dashboard_payload)
            if index_rows:
                self._store_dataframe("index_returns", index_rows)
            mover_rows = self._normalise_axlfi_mover_rows(dashboard_payload)
            if mover_rows:
                self._store_dataframe("movers", mover_rows)

        tactical_payload = self._fetch_json(
            f"{base}/api/global_asset_allocation/get_tactical_allocation",
            "tactical_allocation",
        )
        if tactical_payload is not None:
            allocation_rows = self._normalise_axlfi_tactical_rows(tactical_payload)
            if allocation_rows:
                self._store_dataframe("allocation", allocation_rows)
            gtaa_metrics = (
                tactical_payload.get("gtaa_strategy_metrics", {})
                if isinstance(tactical_payload, dict)
                else {}
            )
            if isinstance(gtaa_metrics, dict) and gtaa_metrics:
                overview_rows.extend(
                    self._normalise_axlfi_overview_rows({}, gtaa_metrics, "gtaa")
                )
                gtaa_period_rows = self._normalise_axlfi_period_return_rows(gtaa_metrics, "gtaa")
                if gtaa_period_rows:
                    self._store_dataframe("gtaa_period_returns", gtaa_period_rows)

        if overview_rows:
            self._store_dataframe("overview", overview_rows)

        if self.memory_db:
            self.diagnostics["provider_used"] = "axlfi_public"
            self.diagnostics["axlfi_public"] = {
                "strategy_name": strategy_name,
                "strategy_win_rate_pct": strategy_win_rate,
                "cluster_universe": cluster_universe,
                "dark_pools_metric": dark_pools_metric,
                "dark_pools_sort": dark_pools_sort,
                "dark_pools_limit": dark_pools_limit,
                "signal_rows": len(signal_rows),
                "signal_history_rows": len(signal_history_rows),
                "signal_symbol_snapshot_rows": signal_symbol_snapshot_rows,
            }

    def ingest_all(self) -> None:
        """
        [ACTION]
        - Teleology: Perform a full ingestion sweep of all configured StockGrid datasets.
        - Mechanism: Authenticate then fetch signals, dark_pools, clusters in fixed order.
        - Fails: Per-dataset errors recorded in diagnostics; never raises.
        - When-needed: Open when debugging provider-mode selection, legacy-to-AXLFI fallback, or why the engine populated some datasets but not others before fusion.
        - Escalates-to: tools/stock/stock.py::run; tools/calculator/calculator.py::run
        """
        if self.provider_mode == "legacy":
            self._ingest_legacy()
            return

        if self.provider_mode == "axlfi_public":
            self._ingest_axlfi_public()
            return

        self._ingest_legacy()
        if self.memory_db:
            return

        legacy_errors = [str(err) for err in self.diagnostics.get("errors", []) if str(err).strip()]
        if legacy_errors:
            self.diagnostics["warnings"].append(
                "legacy provider returned no usable datasets; falling back to axlfi_public"
            )
            self.diagnostics["warnings"].extend(legacy_errors)
        self.diagnostics["errors"] = []
        self._ingest_axlfi_public()


# ---------------------------------------------------------------------------
# 2. THE FACTORY (LOGIC & COMPRESSION)
# ---------------------------------------------------------------------------


class PayloadFactory:
    """
    [ROLE]
    - Teleology: Fuse ingested datasets into a compact, byte-budgeted artifact payload.
    - Mechanism: SEC-enrich -> merge -> clean/normalize -> select -> encode -> adaptive fill under size cap.
    """

    def __init__(
        self,
        db: Dict[str, pd.DataFrame],
        config: Dict[str, Any],
        enricher: Optional[SecSectorEnricher] = None,
    ) -> None:
        self.db: Dict[str, pd.DataFrame] = db
        self.config: Dict[str, Any] = config
        self.tuning: Dict[str, Any] = config.get("tuning", {})
        self.rich_cfg: Dict[str, Any] = (
            config.get("rich_payload", {})
            if isinstance(config.get("rich_payload"), dict)
            else {}
        )
        self.master: pd.DataFrame = pd.DataFrame()
        self.meta_log: Dict[str, Any] = {}
        self.sector_map: SectorMap = SectorMap()
        self.enricher: Optional[SecSectorEnricher] = enricher

    def _measure_json_bytes(self, obj: Any) -> int:
        return len(json.dumps(obj, separators=(",", ":")).encode("utf-8"))

    def fuse(self) -> None:
        """
        [ACTION]
        - Teleology: Fuse ingested datasets into self.master with SEC sector backfill for Unknown rows.
        - Mechanism:
            1. Dark pools → derive flow_m, short_vol.
            2. Signals → best-per-ticker by win_rate.
            3. Clusters → mean 1d_forward_return per ticker.
            4. Merge all on ticker (left joins from dark_pools).
            5. SEC backfill → for rows where sector is Unknown/None/empty, call enricher.enrich()
               to resolve from stockgrid_ticker_map.json (or SEC EDGAR lazily).
            6. Fill remaining defaults.
        - Guarantee: On success, self.master contains augmented rows; sector column is as resolved as possible.
        - When-needed: Open when the stockgrid lane has join-hit, sector, or flow anomalies and you need the exact merge-plus-backfill rules before the byte-budgeted emit stage.
        - Escalates-to: codex/refs/stockgrid_ticker_map.json; tools/calculator/calculator.py::run
        """
        # 1. Dark Pools
        dp = self.db.get("dark_pools", pd.DataFrame()).copy()
        if dp.empty:
            return
        if "ticker" in dp.columns:
            dp["ticker"] = dp["ticker"].astype(str).str.strip().str.upper()
        if "sector" in dp.columns and "dp_sector" not in dp.columns:
            dp["dp_sector"] = dp["sector"].astype(str).str.strip()
            dp = dp.drop(columns=["sector"])

        if "dark pools position $" in dp.columns:
            dp["flow_m"] = (
                dp["dark pools position $"]
                .astype(str)
                .str.replace(r"[$,]", "", regex=True)
                .replace("nan", 0)
                .astype(float)
                / 1e6
            ).fillna(0)

        if "short volume %" in dp.columns:
            dp["short_vol"] = pd.to_numeric(
                dp["short volume %"].astype(str).str.replace("%", ""), errors="coerce"
            ).astype(float)
            mask = dp["short_vol"] > 1.0
            dp.loc[mask, "short_vol"] = dp.loc[mask, "short_vol"] / 100.0

        # 2. Signals
        sig = self.db.get("signals", pd.DataFrame()).copy()
        sig_best = pd.DataFrame(columns=["ticker", "factor", "win_rate", "sector"])
        if not sig.empty and "ticker" in sig.columns:
            sig["ticker"] = sig["ticker"].astype(str).str.strip().str.upper()

        if not sig.empty:
            if "profitable%" in sig.columns:
                sig["win_rate"] = pd.to_numeric(
                    sig["profitable%"].astype(str).str.replace("%", ""), errors="coerce"
                )
            elif "win_rate" not in sig.columns:
                sig["win_rate"] = pd.Series([None] * len(sig), index=sig.index, dtype="float64")
            try:
                sig_best = (
                    sig.sort_values("win_rate", ascending=False, na_position="last")
                    .groupby("ticker")
                    .first()
                    .reset_index()
                )
            except Exception:
                pass
        if not sig_best.empty and "ticker" in sig_best.columns:
            sig_best["ticker"] = sig_best["ticker"].astype(str).str.strip().str.upper()

        for col in ["factor", "sector"]:
            if col not in sig_best.columns:
                sig_best[col] = "Unknown"
        if "win_rate" not in sig_best.columns:
            sig_best["win_rate"] = pd.Series(dtype="float64")

        # 3. Clusters
        cl = self.db.get("clusters", pd.DataFrame()).copy()
        if not cl.empty and "ticker" in cl.columns:
            cl["ticker"] = cl["ticker"].astype(str).str.strip().str.upper()
        if not cl.empty:
            available_cluster_cols = [
                col
                for col in ["1d_forward_return", "5d_forward_return", "10d_forward_return", "20d_forward_return"]
                if col in cl.columns
            ]
            if available_cluster_cols:
                cl_grouped = cl.groupby("ticker")[available_cluster_cols].mean().reset_index()
            else:
                cl_grouped = pd.DataFrame(columns=["ticker"])
        else:
            cl_grouped = pd.DataFrame(
                columns=["ticker", "1d_forward_return", "5d_forward_return", "10d_forward_return", "20d_forward_return"]
            )
        if not cl_grouped.empty and "ticker" in cl_grouped.columns:
            cl_grouped["ticker"] = cl_grouped["ticker"].astype(str).str.strip().str.upper()

        # Track unmatched for diagnostics
        sig_ticker_set: set = set()
        if "ticker" in sig_best.columns:
            sig_ticker_set = {
                t for t in sig_best["ticker"].dropna().astype(str).str.strip().str.upper().tolist() if t
            }

        unmatched_tickers: List[str] = []
        if "ticker" in dp.columns and sig_ticker_set:
            for ticker in dp["ticker"].tolist():
                t = str(ticker).strip().upper()
                if t and t not in sig_ticker_set:
                    unmatched_tickers.append(t)
        elif "ticker" in dp.columns and not sig_ticker_set:
            unmatched_tickers = [str(t).strip().upper() for t in dp["ticker"].tolist() if str(t).strip()]

        unmatched_tickers = list(dict.fromkeys(unmatched_tickers))

        # 4. Merge
        self.master = pd.merge(
            dp, sig_best[["ticker", "factor", "win_rate", "sector"]], on="ticker", how="left"
        )
        self.master = pd.merge(self.master, cl_grouped, on="ticker", how="left")

        if "dp_sector" in self.master.columns:
            base_sector = self.master["dp_sector"].astype(str).str.strip()
            if "sector" in self.master.columns:
                sector_missing = self.master["sector"].isna() | self.master["sector"].isin(["Unknown", "None", "", "nan"])
                self.master.loc[sector_missing, "sector"] = base_sector.loc[sector_missing]
            else:
                self.master["sector"] = base_sector

        # 5. Defaults fill (pre-enrichment)
        defaults = {"flow_m": 0, "short_vol": 0, "sector": "Unknown", "factor": "None"}
        for col, val in defaults.items():
            if col in self.master.columns:
                self.master[col] = self.master[col].fillna(val)

        # ------------------------------------------------------------------
        # 6. SEC SECTOR BACKFILL
        #    Operate on rows where sector is still Unknown / empty.
        #    Uses self.enricher (SecSectorEnricher), which reads/writes
        #    codex/refs/stockgrid_ticker_map.json via cache-first + SEC lazy.
        # ------------------------------------------------------------------
        if self.enricher is not None and "sector" in self.master.columns and "ticker" in self.master.columns:
            unknown_mask = self.master["sector"].isin(["Unknown", "None", "", "nan"])
            # Sort unknown tickers by absolute flow so the most active get resolved first
            # within the per-run SEC call budget
            unknown_sub = self.master.loc[unknown_mask, ["ticker", "flow_m"]].copy()
            unknown_sub["ticker"] = unknown_sub["ticker"].astype(str).str.strip().str.upper()
            unknown_sub["abs_flow"] = unknown_sub["flow_m"].abs() if "flow_m" in unknown_sub.columns else 0
            unknown_tickers = (
                unknown_sub.sort_values("abs_flow", ascending=False)
                .drop_duplicates("ticker")["ticker"]
                .dropna()
                .tolist()
            )

            if unknown_tickers:
                resolved = self.enricher.enrich(unknown_tickers)
                # Map resolved sectors back onto master rows
                self.master.loc[unknown_mask, "sector"] = (
                    self.master.loc[unknown_mask, "ticker"]
                    .map(resolved)
                    .fillna("Unknown")
                )

            self.meta_log["sec_enricher_diagnostics"] = self.enricher.diagnostics

        # Join diagnostics
        join_hit_rate = 0.0
        join_eligible_rows = 0
        join_matched_rows = 0
        join_hit_rate_eligible = 0.0
        if "win_rate" in self.master.columns and len(self.master) > 0:
            join_hit_rate = float(self.master["win_rate"].notna().sum()) / float(len(self.master))
            if "ticker" in self.master.columns and sig_ticker_set:
                eligible_mask = self.master["ticker"].astype(str).str.strip().str.upper().isin(sig_ticker_set)
                join_eligible_rows = int(eligible_mask.sum())
                join_matched_rows = int(self.master.loc[eligible_mask, "win_rate"].notna().sum())
                if join_eligible_rows > 0:
                    join_hit_rate_eligible = float(join_matched_rows) / float(join_eligible_rows)

        self.meta_log["join_hit_rate"] = round(join_hit_rate, 4)
        self.meta_log["join_eligible_rows"] = join_eligible_rows
        self.meta_log["join_matched_rows"] = join_matched_rows
        self.meta_log["join_hit_rate_eligible"] = round(join_hit_rate_eligible, 4)
        self.meta_log["unmatched_tickers_sample"] = unmatched_tickers[:20]

    def _py_value(self, value: Any) -> Any:
        if pd.isna(value):
            return None
        if hasattr(value, "item") and not isinstance(value, (str, bytes)):
            try:
                value = value.item()
            except Exception:
                pass
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d")
        return value

    def _rich_enabled(self) -> bool:
        enabled = self.rich_cfg.get("enabled", True)
        return bool(enabled)

    def _rich_limits(self) -> Dict[str, int]:
        limits = self.rich_cfg.get("limits", {}) if isinstance(self.rich_cfg.get("limits"), dict) else {}
        resolved: Dict[str, int] = {}
        for key, default in (
            ("movers_per_bucket", 25),
            ("signal_history_points_per_symbol", 90),
            ("period_return_points_per_family", 120),
        ):
            try:
                resolved[key] = max(1, int(limits.get(key, default)))
            except (TypeError, ValueError):
                resolved[key] = default
        return resolved

    def _make_dataset(
        self,
        key: str,
        title: str,
        columns: List[str],
        rows: List[List[Any]],
        *,
        default_sort: Optional[Dict[str, Any]] = None,
        default_columns: Optional[List[str]] = None,
        value_format_hints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dataset: Dict[str, Any] = {
            "key": key,
            "title": title,
            "columns": columns,
            "rows": rows,
        }
        if default_sort:
            dataset["default_sort"] = default_sort
        if default_columns:
            dataset["default_columns"] = default_columns
        if value_format_hints:
            dataset["value_format_hints"] = value_format_hints
        return dataset

    def _mean_defined(self, values: List[Any]) -> Optional[float]:
        defined: List[float] = []
        for value in values:
            parsed = _to_float(value)
            if parsed is not None:
                defined.append(parsed)
        if not defined:
            return None
        return float(sum(defined) / len(defined))

    def _zscore(self, series: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        valid = numeric.dropna()
        if len(valid) < 2:
            return pd.Series([0.0] * len(series), index=series.index, dtype="float64")
        std = float(valid.std(ddof=0))
        if std < 1e-12:
            return pd.Series([0.0] * len(series), index=series.index, dtype="float64")
        mean = float(valid.mean())
        return ((numeric - mean) / std).clip(-3.0, 3.0).fillna(0.0)

    def _daily_log_momentum_bps(self, value: Any, days: int) -> Optional[float]:
        parsed = _to_float(value)
        if parsed is None or days <= 0:
            return None
        ratio = parsed / 100.0
        if ratio <= -0.999999:
            return None
        return float(math.log1p(ratio) / float(days) * 10_000.0)

    def _signal_history_features(self) -> pd.DataFrame:
        hist = self.db.get("signal_history", pd.DataFrame()).copy()
        if hist.empty or "ticker" not in hist.columns or "date" not in hist.columns:
            return pd.DataFrame()

        hist["ticker"] = hist["ticker"].astype(str).str.strip().str.upper()
        hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
        hist = hist.dropna(subset=["ticker", "date"]).sort_values(["ticker", "date"])
        if hist.empty:
            return pd.DataFrame()

        rows: List[Dict[str, Any]] = []
        momentum_cols = [
            ("momentum_1d", 1),
            ("momentum_10d", 10),
            ("momentum_20d", 20),
            ("momentum_60d", 60),
            ("momentum_120d", 120),
            ("momentum_250d", 250),
        ]

        for ticker, group in hist.groupby("ticker", sort=False):
            ordered = group.drop_duplicates("date", keep="last").sort_values("date")
            if ordered.empty:
                continue

            latest = ordered.iloc[-1]
            closes = pd.to_numeric(ordered.get("close"), errors="coerce")
            returns = closes.pct_change().replace([np.inf, -np.inf], np.nan)

            close_20 = closes.tail(20).dropna()
            close_60 = closes.tail(60).dropna()
            vol_20_src = returns.tail(20).dropna()

            latest_close = _to_float(latest.get("close"))
            pullback_20d: Optional[float] = None
            if latest_close is not None and not close_20.empty:
                high_20 = float(close_20.max())
                if high_20 > 0:
                    pullback_20d = float((latest_close / high_20) - 1.0)

            range_pos_60d: Optional[float] = None
            if latest_close is not None and not close_60.empty:
                low_60 = float(close_60.min())
                high_60 = float(close_60.max())
                if high_60 - low_60 > 1e-12:
                    range_pos_60d = float((latest_close - low_60) / (high_60 - low_60))

            term_bps: Dict[str, Optional[float]] = {}
            breadth_votes: List[int] = []
            for col, days in momentum_cols:
                term_bps[col] = self._daily_log_momentum_bps(latest.get(col), days)
                raw_value = _to_float(latest.get(col))
                if raw_value is None:
                    continue
                if raw_value > 0:
                    breadth_votes.append(1)
                elif raw_value < 0:
                    breadth_votes.append(-1)
                else:
                    breadth_votes.append(0)

            short_trend = self._mean_defined(
                [term_bps["momentum_1d"], term_bps["momentum_10d"], term_bps["momentum_20d"]]
            )
            long_trend = self._mean_defined(
                [term_bps["momentum_60d"], term_bps["momentum_120d"], term_bps["momentum_250d"]]
            )
            trend_bps_d = self._mean_defined(
                [
                    term_bps["momentum_10d"],
                    term_bps["momentum_20d"],
                    term_bps["momentum_60d"],
                    term_bps["momentum_120d"],
                    term_bps["momentum_250d"],
                ]
            )
            accel_bps_d = (
                float(short_trend - long_trend)
                if short_trend is not None and long_trend is not None
                else None
            )
            mom_breadth = (
                float(sum(breadth_votes) / len(breadth_votes))
                if breadth_votes
                else None
            )

            rows.append(
                {
                    "ticker": ticker,
                    "hist_m1": _round_float(latest.get("momentum_1d"), 4),
                    "hist_m10": _round_float(latest.get("momentum_10d"), 4),
                    "hist_m20": _round_float(latest.get("momentum_20d"), 4),
                    "hist_m60": _round_float(latest.get("momentum_60d"), 4),
                    "hist_m120": _round_float(latest.get("momentum_120d"), 4),
                    "hist_m250": _round_float(latest.get("momentum_250d"), 4),
                    "trend_bps_d": _round_float(trend_bps_d, 2),
                    "accel_bps_d": _round_float(accel_bps_d, 2),
                    "mom_breadth": _round_float(mom_breadth, 4),
                    "pullback_20d": _round_float(pullback_20d, 6),
                    "range_pos_60d": _round_float(range_pos_60d, 4),
                    "vol_20d": _round_float(vol_20_src.std(ddof=0) if len(vol_20_src) >= 2 else None, 6),
                    "history_points": int(len(ordered)),
                }
            )

        return pd.DataFrame(rows)

    def _build_signal_dataset(self) -> Optional[Dict[str, Any]]:
        sig = self.db.get("signals", pd.DataFrame()).copy()
        if sig.empty or "ticker" not in sig.columns:
            return None
        sig["ticker"] = sig["ticker"].astype(str).str.strip().str.upper()
        sort_cols = [col for col in ["profitable%", "momentum_20d"] if col in sig.columns]
        if sort_cols:
            sig = sig.sort_values(sort_cols, ascending=[False] * len(sort_cols), na_position="last")
        sig = sig.drop_duplicates("ticker")

        dp = self.db.get("dark_pools", pd.DataFrame()).copy()
        if not dp.empty and "ticker" in dp.columns:
            dp["ticker"] = dp["ticker"].astype(str).str.strip().str.upper()
            keep = [col for col in ["ticker", "dark pools position $", "dollar_net_volume", "short volume %"] if col in dp.columns]
            dp = dp[keep].drop_duplicates("ticker")

        cl = self.db.get("clusters", pd.DataFrame()).copy()
        if not cl.empty and "ticker" in cl.columns:
            cl["ticker"] = cl["ticker"].astype(str).str.strip().str.upper()
            available = [col for col in ["1d_forward_return", "5d_forward_return", "20d_forward_return"] if col in cl.columns]
            if available:
                cl = cl.groupby("ticker")[available].mean().reset_index()
            else:
                cl = pd.DataFrame(columns=["ticker"])

        merged = sig
        if not dp.empty:
            merged = pd.merge(merged, dp, on="ticker", how="left")
        if not cl.empty:
            merged = pd.merge(merged, cl, on="ticker", how="left")
        hist_features = self._signal_history_features()
        if not hist_features.empty:
            merged = pd.merge(merged, hist_features, on="ticker", how="left")

        for live_col, hist_col in (
            ("momentum_1d", "hist_m1"),
            ("momentum_10d", "hist_m10"),
            ("momentum_20d", "hist_m20"),
            ("momentum_60d", "hist_m60"),
            ("momentum_120d", "hist_m120"),
            ("momentum_250d", "hist_m250"),
        ):
            if live_col not in merged.columns:
                merged[live_col] = pd.Series([None] * len(merged), index=merged.index, dtype="float64")
            if hist_col in merged.columns:
                merged[live_col] = merged[live_col].where(merged[live_col].notna(), merged[hist_col])

        merged["flow_usd"] = pd.to_numeric(merged.get("dark pools position $"), errors="coerce")
        merged["net_usd"] = pd.to_numeric(merged.get("dollar_net_volume"), errors="coerce")
        merged["sv"] = pd.to_numeric(merged.get("short volume %"), errors="coerce")
        merged["wr"] = pd.to_numeric(merged.get("profitable%"), errors="coerce")
        if "signal_dir" in merged.columns:
            merged["signal_dir"] = pd.to_numeric(merged["signal_dir"], errors="coerce").fillna(0.0)
        else:
            merged["signal_dir"] = 0.0
        merged["trend_bps_d"] = pd.to_numeric(merged.get("trend_bps_d"), errors="coerce")
        merged["accel_bps_d"] = pd.to_numeric(merged.get("accel_bps_d"), errors="coerce")
        merged["mom_breadth"] = pd.to_numeric(merged.get("mom_breadth"), errors="coerce")
        merged["pullback_20d"] = pd.to_numeric(merged.get("pullback_20d"), errors="coerce")
        merged["range_pos_60d"] = pd.to_numeric(merged.get("range_pos_60d"), errors="coerce")
        merged["vol_20d"] = pd.to_numeric(merged.get("vol_20d"), errors="coerce")

        available_edge_terms = []
        for col, weight in (
            ("1d_forward_return", 0.15),
            ("5d_forward_return", 0.35),
            ("20d_forward_return", 0.50),
        ):
            if col in merged.columns:
                available_edge_terms.append((pd.to_numeric(merged.get(col), errors="coerce"), weight))
        if available_edge_terms:
            weighted_sum = pd.Series([0.0] * len(merged), index=merged.index, dtype="float64")
            weight_sum = pd.Series([0.0] * len(merged), index=merged.index, dtype="float64")
            for series, weight in available_edge_terms:
                mask = series.notna()
                weighted_sum.loc[mask] = weighted_sum.loc[mask] + (series.loc[mask] * weight)
                weight_sum.loc[mask] = weight_sum.loc[mask] + weight
            merged["edge_bps"] = (weighted_sum / weight_sum.replace(0.0, np.nan)) * 10_000.0
        else:
            merged["edge_bps"] = pd.Series([None] * len(merged), index=merged.index, dtype="float64")

        merged["align"] = merged["signal_dir"] * merged["mom_breadth"]
        merged["flow_support"] = merged["signal_dir"] * np.arcsinh(merged["flow_usd"].fillna(0.0) / 100_000_000.0)
        merged["trend_support"] = merged["signal_dir"] * merged["trend_bps_d"]
        merged["accel_support"] = merged["signal_dir"] * merged["accel_bps_d"]
        merged["edge_support"] = merged["signal_dir"] * merged["edge_bps"]
        conviction = (
            (self._zscore(merged["flow_support"]) * 0.30)
            + (self._zscore(merged["trend_support"]) * 0.25)
            + (self._zscore(merged["accel_support"]) * 0.15)
            + (self._zscore(merged["edge_support"]) * 0.15)
            + (self._zscore(merged["align"]) * 0.10)
            + (self._zscore(merged["wr"]) * 0.05)
        )
        merged["conv"] = (50.0 + (conviction * 15.0)).clip(0.0, 100.0)
        merged = merged.sort_values(["conv", "flow_support"], ascending=[False, False], na_position="last")

        columns = [
            "tkr",
            "dir",
            "sector",
            "industry",
            "company",
            "flow_usd",
            "net_usd",
            "sv",
            "wr",
            "r1d",
            "r5d",
            "r20d",
            "m1",
            "m10",
            "m20",
            "m60",
            "m120",
            "m250",
            "align",
            "trend_bps_d",
            "accel_bps_d",
            "edge_bps",
            "pullback_20d",
            "range_pos_60d",
            "vol_20d",
            "conv",
            "cap_b",
            "avg_vol",
            "eps_next_y",
            "eps_this_y",
            "eps_q_q",
            "sales_q_q",
            "n100",
            "sp500",
            "r2000",
        ]
        rows: List[List[Any]] = []
        for _, row in merged.iterrows():
            rows.append(
                [
                    str(row.get("ticker", "")),
                    self._py_value(row.get("signal_dir")),
                    self._py_value(row.get("sector")),
                    self._py_value(row.get("industry")),
                    self._py_value(row.get("company")),
                    _round_float(row.get("flow_usd"), 2),
                    _round_float(row.get("net_usd"), 2),
                    _round_float(row.get("sv"), 2),
                    _round_float(row.get("wr"), 2),
                    _round_float(row.get("1d_forward_return"), 6),
                    _round_float(row.get("5d_forward_return"), 6),
                    _round_float(row.get("20d_forward_return"), 6),
                    _round_float(row.get("momentum_1d"), 4),
                    _round_float(row.get("momentum_10d"), 4),
                    _round_float(row.get("momentum_20d"), 4),
                    _round_float(row.get("momentum_60d"), 4),
                    _round_float(row.get("momentum_120d"), 4),
                    _round_float(row.get("momentum_250d"), 4),
                    _round_float(row.get("align"), 4),
                    _round_float(row.get("trend_bps_d"), 2),
                    _round_float(row.get("accel_bps_d"), 2),
                    _round_float(row.get("edge_bps"), 2),
                    _round_float(row.get("pullback_20d"), 6),
                    _round_float(row.get("range_pos_60d"), 4),
                    _round_float(row.get("vol_20d"), 6),
                    _round_float(row.get("conv"), 2),
                    _round_float(row.get("market_cap_b"), 2),
                    _round_float(row.get("avg_volume"), 0),
                    _round_float(row.get("eps_next_y_pct"), 2),
                    _round_float(row.get("eps_this_y_pct"), 2),
                    _round_float(row.get("eps_q_q_pct"), 2),
                    _round_float(row.get("sales_q_q_pct"), 2),
                    self._py_value(row.get("nasdaq100")),
                    self._py_value(row.get("sp500")),
                    self._py_value(row.get("russell2000")),
                ]
            )

        if not rows:
            return None
        return self._make_dataset(
            "signals",
            "active_signals",
            columns,
            rows,
            default_sort={"column": "conv", "direction": "desc"},
            default_columns=["tkr", "dir", "conv", "flow_usd", "sv", "wr", "align", "trend_bps_d", "edge_bps", "pullback_20d"],
            value_format_hints={
                "flow_usd": {"type": "flow_usd"},
                "net_usd": {"type": "flow_usd"},
                "sv": {"type": "pct_int"},
                "wr": {"type": "pct_int"},
                "r1d": {"type": "pct_ratio"},
                "r5d": {"type": "pct_ratio"},
                "r20d": {"type": "pct_ratio"},
                "m1": {"type": "pct_int"},
                "m10": {"type": "pct_int"},
                "m20": {"type": "pct_int"},
                "m60": {"type": "pct_int"},
                "m120": {"type": "pct_int"},
                "m250": {"type": "pct_int"},
                "pullback_20d": {"type": "pct_ratio"},
                "vol_20d": {"type": "pct_ratio"},
                "eps_next_y": {"type": "pct_int"},
                "eps_this_y": {"type": "pct_int"},
                "eps_q_q": {"type": "pct_int"},
                "sales_q_q": {"type": "pct_int"},
            },
        )

    def _build_signal_history_dataset(self, max_points_per_symbol: int) -> Optional[Dict[str, Any]]:
        hist = self.db.get("signal_history", pd.DataFrame()).copy()
        if hist.empty or "ticker" not in hist.columns or "date" not in hist.columns:
            return None
        hist["ticker"] = hist["ticker"].astype(str).str.strip().str.upper()
        hist["date"] = hist["date"].astype(str).str.strip()
        hist = hist.sort_values(["ticker", "date"], ascending=[True, False])

        tickers = hist["ticker"].dropna().astype(str).unique().tolist()
        grouped_rows: Dict[str, List[List[Any]]] = {}
        for ticker in tickers:
            ticker_rows = hist[hist["ticker"] == ticker].head(max_points_per_symbol)
            grouped_rows[ticker] = [
                [
                    ticker,
                    self._py_value(row.get("date")),
                    _round_float(row.get("close"), 4),
                    _round_float(row.get("momentum_1d"), 4),
                    _round_float(row.get("momentum_10d"), 4),
                    _round_float(row.get("momentum_20d"), 4),
                    _round_float(row.get("momentum_60d"), 4),
                    _round_float(row.get("momentum_120d"), 4),
                    _round_float(row.get("momentum_250d"), 4),
                ]
                for _, row in ticker_rows.iterrows()
            ]

        rows: List[List[Any]] = []
        max_depth = max((len(items) for items in grouped_rows.values()), default=0)
        for idx in range(max_depth):
            for ticker in tickers:
                ticker_rows = grouped_rows.get(ticker, [])
                if idx < len(ticker_rows):
                    rows.append(ticker_rows[idx])

        if not rows:
            return None
        return self._make_dataset(
            "signal_history",
            "signal_history",
            ["tkr", "date", "close", "m1", "m10", "m20", "m60", "m120", "m250"],
            rows,
            default_sort={"column": "date", "direction": "desc"},
            default_columns=["tkr", "date", "close", "m1", "m10", "m20", "m60", "m250"],
            value_format_hints={
                "close": {"type": "currency", "decimals": 2},
                "m1": {"type": "pct_int"},
                "m10": {"type": "pct_int"},
                "m20": {"type": "pct_int"},
                "m60": {"type": "pct_int"},
                "m120": {"type": "pct_int"},
                "m250": {"type": "pct_int"},
            },
        )

    def _build_sector_dataset(self) -> Optional[Dict[str, Any]]:
        df = self.master.copy()
        if df.empty or "sector" not in df.columns:
            return None
        df["sector"] = df["sector"].astype(str).str.strip().replace("", "Unknown")
        df["signal_flag"] = ~df["factor"].astype(str).str.strip().isin(["", "None", "Unknown", "nan"]) if "factor" in df.columns else False
        df["positive_flow"] = df["flow_m"] > 0
        df["negative_flow"] = df["flow_m"] < 0
        df["abs_flow_m"] = pd.to_numeric(df.get("flow_m"), errors="coerce").abs().fillna(0.0)

        rows: List[List[Any]] = []
        grouped = df.groupby("sector", dropna=False)
        for sector, group in grouped:
            group_abs_flow = group["abs_flow_m"]
            abs_flow_sum = float(group_abs_flow.sum())
            top_names = (
                group.assign(abs_flow=group_abs_flow)
                .sort_values("abs_flow", ascending=False)["ticker"]
                .astype(str)
                .head(3)
                .tolist()
            )
            top3_flow_conc = (
                float(group_abs_flow.sort_values(ascending=False).head(3).sum() / abs_flow_sum * 100.0)
                if abs_flow_sum > 0
                else None
            )
            breadth_pct = float((group["positive_flow"].sum() - group["negative_flow"].sum()) / max(len(group), 1) * 100.0)
            rows.append(
                [
                    str(sector or "Unknown"),
                    int(len(group)),
                    int(group["signal_flag"].sum()),
                    _round_float(breadth_pct, 2),
                    _round_float(group["flow_m"].sum() * 1_000_000, 2),
                    _round_float(group["flow_m"].abs().sum() * 1_000_000, 2),
                    _round_float(top3_flow_conc, 2),
                    _round_float(group["short_vol"].mean() * 100, 2),
                    _round_float(group["win_rate"].dropna().mean(), 2),
                    _round_float(group["1d_forward_return"].dropna().mean(), 6),
                    _round_float(group["5d_forward_return"].dropna().mean(), 6) if "5d_forward_return" in group.columns else None,
                    _round_float(group["20d_forward_return"].dropna().mean(), 6) if "20d_forward_return" in group.columns else None,
                    "/".join(top_names),
                ]
            )

        rows.sort(key=lambda item: abs(float(item[6] or 0.0)), reverse=True)
        return self._make_dataset(
            "sectors",
            "sector_summary",
            [
                "sector",
                "count",
                "signal_count",
                "breadth_pct",
                "net_flow_usd",
                "abs_flow_usd",
                "flow_conc_pct",
                "avg_sv",
                "avg_wr",
                "avg_r1d",
                "avg_r5d",
                "avg_r20d",
                "leaders",
            ],
            rows,
            default_sort={"column": "abs_flow_usd", "direction": "desc"},
            default_columns=["sector", "count", "signal_count", "breadth_pct", "net_flow_usd", "abs_flow_usd", "flow_conc_pct", "avg_wr", "leaders"],
            value_format_hints={
                "breadth_pct": {"type": "pct_int"},
                "net_flow_usd": {"type": "flow_usd"},
                "abs_flow_usd": {"type": "flow_usd"},
                "flow_conc_pct": {"type": "pct_int"},
                "avg_sv": {"type": "pct_int"},
                "avg_wr": {"type": "pct_int"},
                "avg_r1d": {"type": "pct_ratio"},
                "avg_r5d": {"type": "pct_ratio"},
                "avg_r20d": {"type": "pct_ratio"},
            },
        )

    def _score_positive_metric(self, value: Any, scale: float) -> Optional[float]:
        parsed = _to_float(value)
        if parsed is None or scale <= 0:
            return None
        return float(max(0.0, min(100.0, 100.0 * math.tanh(max(parsed, 0.0) / scale))))

    def _score_inverse_metric(self, value: Any, threshold: float) -> Optional[float]:
        parsed = _to_float(value)
        if parsed is None or threshold <= 0:
            return None
        return float(max(0.0, 100.0 * (1.0 - min(abs(parsed) / threshold, 1.0))))

    def _build_overview_dataset(self) -> Optional[Dict[str, Any]]:
        df = self.db.get("overview", pd.DataFrame()).copy()
        if df.empty:
            return None

        for col in ["group", "metric", "note", "context"]:
            if col not in df.columns:
                df[col] = None
        if "value" not in df.columns:
            df["value"] = None

        df["group"] = df["group"].astype(str).str.strip()
        df["metric"] = df["metric"].astype(str).str.strip()
        df["context"] = df["context"].astype(str).str.strip()
        note_text = df["note"].fillna("").astype(str).str.strip()
        df = df[df["value"].notna() | note_text.ne("")]
        if df.empty:
            return None

        rows: List[List[Any]] = []
        special_metric_order = [
            ("volatility_regime", "current_regime"),
            ("volatility_regime", "next_open_flag"),
            ("sector_leaders_1d", "best_sector"),
            ("sector_leaders_1d", "worst_sector"),
        ]
        for group_name, metric_name in special_metric_order:
            subset = df[(df["group"] == group_name) & (df["metric"] == metric_name)].sort_values("context")
            for _, row in subset.iterrows():
                raw_value = row.get("value")
                parsed_value = _to_float(raw_value)
                rows.append(
                    [
                        self._py_value(row.get("group")),
                        self._py_value(row.get("metric")),
                        _round_float(parsed_value, 4) if parsed_value is not None else self._py_value(raw_value),
                        self._py_value(row.get("note")),
                        self._py_value(row.get("context")),
                    ]
                )

        metric_order = [
            "CAGR",
            "Sharpe Ratio",
            "Sortino Ratio",
            "Calmar Ratio",
            "Annualized Volatility (Latest)",
            "% Positive Months",
            "% Positive Years",
            "Win Rate %",
            "Profit Factor",
            "Expectancy",
            "Worst Rolling 3-Month Return",
            "Worst Rolling 6-Month Return",
        ]
        metric_df = df[~df["group"].isin(["volatility_regime", "sector_leaders_1d"])].copy()
        metric_df = metric_df[metric_df["metric"].isin(metric_order)]
        if metric_df.empty and not rows:
            return None

        for context in metric_df["context"].dropna().astype(str).sort_values().unique().tolist():
            ctx = metric_df[metric_df["context"] == context]
            metrics_numeric = {
                str(row["metric"]): _to_float(row["value"])
                for _, row in ctx.iterrows()
            }
            risk_adj_score = self._mean_defined(
                [
                    self._score_positive_metric(metrics_numeric.get("Sharpe Ratio"), 1.5),
                    self._score_positive_metric(metrics_numeric.get("Sortino Ratio"), 2.0),
                    self._score_positive_metric(metrics_numeric.get("Calmar Ratio"), 1.0),
                    self._score_inverse_metric(metrics_numeric.get("Annualized Volatility (Latest)"), 25.0),
                ]
            )
            consistency_score = self._mean_defined(
                [
                    metrics_numeric.get("% Positive Months"),
                    metrics_numeric.get("% Positive Years"),
                    self._score_inverse_metric(metrics_numeric.get("Worst Rolling 3-Month Return"), 30.0),
                    self._score_inverse_metric(metrics_numeric.get("Worst Rolling 6-Month Return"), 35.0),
                ]
            )
            edge_score = self._mean_defined(
                [
                    self._score_positive_metric(metrics_numeric.get("CAGR"), 25.0),
                    self._score_positive_metric((metrics_numeric.get("Win Rate %") or 0.0) - 45.0, 12.0),
                    self._score_positive_metric((metrics_numeric.get("Profit Factor") or 0.0) - 1.0, 1.0),
                    self._score_positive_metric(
                        math.log1p(max(metrics_numeric.get("Expectancy") or 0.0, 0.0)),
                        6.0,
                    ),
                ]
            )
            for metric_name, score, note in (
                ("risk_adj_score", risk_adj_score, "0-100 composite; higher is sturdier"),
                ("consistency_score", consistency_score, "0-100 composite; higher is steadier"),
                ("edge_score", edge_score, "0-100 composite; higher is more monetized"),
            ):
                if score is None:
                    continue
                rows.append(["summary", metric_name, _round_float(score, 2), note, context])

            for metric_name in metric_order:
                subset = ctx[ctx["metric"] == metric_name]
                if subset.empty:
                    continue
                row = subset.iloc[0]
                raw_value = row.get("value")
                parsed_value = _to_float(raw_value)
                rows.append(
                    [
                        self._py_value(row.get("group")),
                        self._py_value(row.get("metric")),
                        _round_float(parsed_value, 4) if parsed_value is not None else self._py_value(raw_value),
                        self._py_value(row.get("note")),
                        self._py_value(row.get("context")),
                    ]
                )

        if not rows:
            return None
        return self._make_dataset(
            "overview",
            "overview",
            ["group", "metric", "value", "note", "context"],
            rows,
            default_columns=["context", "group", "metric", "value", "note"],
        )

    def _build_mover_dataset(self) -> Optional[Dict[str, Any]]:
        df = self.db.get("movers", pd.DataFrame()).copy()
        if df.empty:
            return None

        if "bucket" not in df.columns:
            df["bucket"] = ""
        else:
            df["bucket"] = df["bucket"].astype(str).str.strip()
        if "ticker" not in df.columns:
            return None
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
        df = df[df["ticker"] != ""]
        if df.empty:
            return None

        for col in ["change_pct", "current_close", "prior_close", "current_volume"]:
            df[col] = pd.to_numeric(df.get(col), errors="coerce")

        price_ref = (
            df[["current_close", "prior_close"]]
            .abs()
            .max(axis=1, skipna=True)
            .fillna(0.0)
        )
        volume_ref = df["current_volume"].clip(lower=0).fillna(0.0)
        price_gate = (price_ref / 5.0).clip(lower=0.0, upper=1.0)
        volume_gate = (1.0 + (np.log10(volume_ref + 1.0) / 6.0)).clip(lower=1.0, upper=2.0)
        df["move_score"] = (
            df["change_pct"].abs().fillna(0.0)
            * np.sqrt(price_gate.clip(lower=0.01))
            * volume_gate
        )
        df = df.sort_values(
            ["bucket", "move_score", "change_pct", "current_volume"],
            ascending=[True, False, False, False],
            na_position="last",
        )

        rows: List[List[Any]] = []
        for _, row in df.iterrows():
            rows.append(
                [
                    self._py_value(row.get("bucket")),
                    self._py_value(row.get("ticker")),
                    _round_float(row.get("change_pct"), 4),
                    _round_float(row.get("move_score"), 4),
                    _round_float(row.get("current_close"), 4),
                    _round_float(row.get("prior_close"), 4),
                    _round_float(row.get("current_volume"), 2),
                ]
            )

        if not rows:
            return None
        return self._make_dataset(
            "movers",
            "movers",
            ["bucket", "ticker", "change_pct", "move_score", "current_close", "prior_close", "current_volume"],
            rows,
            default_sort={"column": "move_score", "direction": "desc"},
            default_columns=["bucket", "ticker", "change_pct", "move_score", "current_close", "current_volume"],
            value_format_hints={
                "change_pct": {"type": "pct_ratio"},
                "current_close": {"type": "currency", "decimals": 2},
                "prior_close": {"type": "currency", "decimals": 2},
            },
        )

    def _build_db_matrix_dataset(
        self,
        df_name: str,
        key: str,
        title: str,
        columns: List[str],
        *,
        default_sort: Optional[Dict[str, Any]] = None,
        default_columns: Optional[List[str]] = None,
        value_format_hints: Optional[Dict[str, Any]] = None,
        sort_by: Optional[List[Tuple[str, bool]]] = None,
    ) -> Optional[Dict[str, Any]]:
        df = self.db.get(df_name, pd.DataFrame()).copy()
        if df.empty:
            return None
        for column, ascending in reversed(sort_by or []):
            if column in df.columns:
                df = df.sort_values(column, ascending=ascending, na_position="last")
        rows: List[List[Any]] = []
        for _, row in df.iterrows():
            rows.append([self._py_value(row.get(column)) for column in columns])
        if not rows:
            return None
        return self._make_dataset(
            key,
            title,
            columns,
            rows,
            default_sort=default_sort,
            default_columns=default_columns,
            value_format_hints=value_format_hints,
        )

    def _candidate_datasets(self) -> List[Tuple[Dict[str, Any], bool]]:
        limits = self._rich_limits()
        candidates: List[Tuple[Optional[Dict[str, Any]], bool]] = [
            (self._build_signal_dataset(), False),
            (
                self._build_db_matrix_dataset(
                    "index_returns",
                    "index_returns",
                    "index_returns",
                    ["label", "tkr", "change_pct", "change", "close", "previous_close", "as_of_date"],
                    default_sort={"column": "change_pct", "direction": "desc"},
                    default_columns=["label", "change_pct", "change", "close"],
                    value_format_hints={
                        "change_pct": {"type": "pct_ratio"},
                        "change": {"type": "currency", "decimals": 2},
                        "close": {"type": "currency", "decimals": 2},
                        "previous_close": {"type": "currency", "decimals": 2},
                    },
                    sort_by=[("change_pct", False)],
                ),
                False,
            ),
            (self._build_sector_dataset(), False),
            (
                self._build_overview_dataset(),
                False,
            ),
            (
                self._build_db_matrix_dataset(
                    "allocation",
                    "allocation",
                    "tactical_allocation",
                    ["ticker", "position", "dir", "rank", "mom", "mom_s", "momentum_1y"],
                    default_sort={"column": "rank", "direction": "asc"},
                    default_columns=["ticker", "position", "dir", "rank", "mom", "mom_s", "momentum_1y"],
                    value_format_hints={
                        "mom": {"type": "pct_ratio"},
                        "mom_s": {"type": "pct_ratio"},
                        "momentum_1y": {"type": "pct_int"},
                    },
                    sort_by=[("rank", True)],
                ),
                False,
            ),
            (
                self._build_mover_dataset(),
                True,
            ),
            (self._build_signal_history_dataset(limits["signal_history_points_per_symbol"]), True),
            (
                self._build_db_matrix_dataset(
                    "strategy_period_returns",
                    "strategy_returns",
                    "strategy_returns",
                    ["family", "frequency", "period_date", "return_value"],
                    default_sort={"column": "period_date", "direction": "desc"},
                    default_columns=["family", "frequency", "period_date", "return_value"],
                    value_format_hints={"return_value": {"type": "pct_ratio"}},
                    sort_by=[("family", True), ("period_date", False)],
                ),
                True,
            ),
            (
                self._build_db_matrix_dataset(
                    "gtaa_period_returns",
                    "gtaa_returns",
                    "gtaa_returns",
                    ["family", "frequency", "period_date", "return_value"],
                    default_sort={"column": "period_date", "direction": "desc"},
                    default_columns=["family", "frequency", "period_date", "return_value"],
                    value_format_hints={"return_value": {"type": "pct_ratio"}},
                    sort_by=[("family", True), ("period_date", False)],
                ),
                True,
            ),
        ]

        filtered: List[Tuple[Dict[str, Any], bool]] = []
        for dataset, allow_trim in candidates:
            if dataset and dataset.get("rows"):
                if allow_trim and dataset["key"] in {"strategy_returns", "gtaa_returns"}:
                    max_rows = limits["period_return_points_per_family"] * 3
                    dataset["rows"] = dataset["rows"][:max_rows]
                if dataset["key"] == "movers":
                    per_bucket = limits["movers_per_bucket"]
                    bucketed_rows: Dict[str, int] = {}
                    trimmed_rows: List[List[Any]] = []
                    for row in dataset["rows"]:
                        bucket = str(row[0]) if row else ""
                        bucketed_rows.setdefault(bucket, 0)
                        if bucketed_rows[bucket] >= per_bucket:
                            continue
                        bucketed_rows[bucket] += 1
                        trimmed_rows.append(row)
                    dataset["rows"] = trimmed_rows
                filtered.append((dataset, allow_trim))
        return filtered

    def _fit_dataset_rows_to_budget(
        self,
        artifact: Dict[str, Any],
        dataset: Dict[str, Any],
        target_bytes: int,
        main_only_bytes: int,
    ) -> List[List[Any]]:
        rows = dataset.get("rows", [])
        if not isinstance(rows, list) or not rows:
            return []

        probe = {key: value for key, value in dataset.items()}
        low = 0
        high = len(rows)
        best_rows: List[List[Any]] = []

        while low <= high:
            mid = (low + high) // 2
            probe["rows"] = rows[:mid]
            candidate = json.loads(json.dumps(artifact))
            candidate_datasets = candidate.setdefault("data", {}).setdefault("datasets", [])
            candidate_datasets.append(probe)
            self._apply_side_dataset_diagnostics(candidate, candidate_datasets, main_only_bytes)
            candidate_size = self._measure_json_bytes(candidate)
            if candidate_size <= target_bytes:
                best_rows = rows[:mid]
                low = mid + 1
            else:
                high = mid - 1

        return best_rows

    def _apply_side_dataset_diagnostics(
        self,
        artifact: Dict[str, Any],
        datasets: List[Dict[str, Any]],
        main_only_bytes: int,
    ) -> None:
        data = artifact.setdefault("data", {})
        diagnostics = artifact.get("metadata", {}).get("diagnostics", {})

        if datasets:
            data["datasets"] = datasets
        else:
            data.pop("datasets", None)

        if not isinstance(diagnostics, dict):
            return

        for key in ["side_dataset_keys", "side_dataset_rows", "side_datasets_kb"]:
            diagnostics.pop(key, None)

        if datasets:
            diagnostics["side_dataset_keys"] = [str(ds.get("key", "")) for ds in datasets]
            diagnostics["side_dataset_rows"] = {
                str(ds.get("key", "")): len(ds.get("rows", []))
                for ds in datasets
            }
            diagnostics["side_datasets_kb"] = 0.0
            diagnostics["side_datasets_kb"] = round(
                max(0, self._measure_json_bytes(artifact) - main_only_bytes) / 1024,
                2,
            )

    def _attach_side_datasets(self, artifact: Dict[str, Any], target_bytes: int) -> None:
        if not self._rich_enabled():
            return

        data = artifact.setdefault("data", {})
        diagnostics = artifact.get("metadata", {}).get("diagnostics", {})
        datasets: List[Dict[str, Any]] = []
        current_bytes = self._measure_json_bytes(artifact)
        main_only_bytes = current_bytes

        for dataset, allow_trim in self._candidate_datasets():
            candidate_rows = dataset.get("rows", [])
            if not candidate_rows:
                continue

            artifact_with_current = json.loads(json.dumps(artifact))
            self._apply_side_dataset_diagnostics(artifact_with_current, datasets.copy(), main_only_bytes)
            rows_to_add = candidate_rows
            if allow_trim:
                rows_to_add = self._fit_dataset_rows_to_budget(
                    artifact=artifact_with_current,
                    dataset=dataset,
                    target_bytes=target_bytes,
                    main_only_bytes=main_only_bytes,
                )
            elif current_bytes >= target_bytes:
                continue
            else:
                probe = json.loads(json.dumps(artifact_with_current))
                probe_datasets = probe.setdefault("data", {}).setdefault("datasets", [])
                probe_datasets.append(dataset)
                self._apply_side_dataset_diagnostics(probe, probe_datasets, main_only_bytes)
                if self._measure_json_bytes(probe) > target_bytes:
                    continue

            if not rows_to_add:
                continue

            dataset_copy = dict(dataset)
            dataset_copy["rows"] = rows_to_add
            datasets.append(dataset_copy)
            self._apply_side_dataset_diagnostics(artifact, datasets, main_only_bytes)
            current_bytes = self._measure_json_bytes(artifact)

        if not datasets:
            self._apply_side_dataset_diagnostics(artifact, [], main_only_bytes)

    def build(self, run_id: str, timestamp: float, as_of: str) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Convert the fused master table into a schema-stable, byte-budgeted artifact envelope.
        - Mechanism: Select whales + setups; encode sectors; build compatibility rows; adaptive texture fill;
          then spend remaining byte budget on richer side datasets sourced from AXLFI.
        - Guarantee: On success, metadata.status == "success"; data.columns begins with the compatibility matrix
          ["tkr","sec","flow","sv","wr","flg"] and may include side datasets under data.datasets.
        - When-needed: Open when a caller needs the exact stockgrid envelope layout, compatibility-matrix semantics, or side-dataset budget trimming rules.
        - Escalates-to: tools/calculator/calculator.py::run; tools/oracle/subject_index.py::run
        """
        df = self.master
        if df.empty:
            return {}

        limit_whales = self.tuning.get("whales_limit", 400)
        limit_setups = self.tuning.get("setups_limit", 100)

        filters = self.tuning.get("filters", {})
        if not filters:
            filters = {"min_net_flow_m": 2.0, "squeeze_short_vol_pct": 0.6, "golden_win_rate_pct": 80}

        min_flow = filters.get("min_net_flow_m", 2.0)
        min_sv   = filters.get("squeeze_short_vol_pct", 0.6)
        min_wr   = filters.get("golden_win_rate_pct", 80)

        # Whales
        whales = df.reindex(df["flow_m"].abs().sort_values(ascending=False).index).head(limit_whales).copy()
        whales["flag"] = 1

        # Setups
        mask_buy = df["flow_m"] > min_flow
        squeeze = (
            df[mask_buy & (df["short_vol"] > min_sv)]
            .sort_values("flow_m", ascending=False)
            .head(limit_setups)
        )
        golden = (
            df[mask_buy & (df["win_rate"] > min_wr)]
            .sort_values("win_rate", ascending=False)
            .head(limit_setups)
        )
        signal_setups = pd.DataFrame(columns=df.columns)
        signal_flow_conflict_rows = 0
        if "factor" in df.columns:
            factor_series = df["factor"].astype(str).str.strip()
            signal_mask = ~factor_series.isin(["", "None", "Unknown", "nan"])
            signal_candidates = df[signal_mask].copy()
            if not signal_candidates.empty:
                signal_candidates["_signal_abs_flow"] = signal_candidates["flow_m"].abs()
                signal_flow_conflict_rows = int((signal_candidates["flow_m"] < 0).sum())
                signal_setups = (
                    signal_candidates
                    .sort_values(["_signal_abs_flow", "win_rate"], ascending=[False, False], na_position="last")
                    .head(limit_setups)
                    .drop(columns=["_signal_abs_flow"], errors="ignore")
                )
        setups = pd.concat([squeeze, golden, signal_setups])
        setups = setups[~setups.index.duplicated(keep="first")].copy()
        setups["flag"] = 2

        if whales.empty:
            named = setups.copy()
        else:
            named = whales.copy()
            if not setups.empty:
                overlap = named.index.intersection(setups.index)
                if len(overlap) > 0:
                    named.loc[overlap, "flag"] = named.loc[overlap, "flag"].astype(int) | 2
                extra_setups = setups.loc[~setups.index.isin(named.index)]
                if not extra_setups.empty:
                    named = pd.concat([named, extra_setups])

        def _encode_wr(value: Any) -> Optional[int]:
            if pd.isna(value):
                return None
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return None

        named_rows: List[List[Any]] = []
        for _, r in named.iterrows():
            named_rows.append([
                str(r["ticker"]),
                self.sector_map.encode(r["sector"]),
                int(r["flow_m"]),
                int(r["short_vol"] * 100),
                _encode_wr(r["win_rate"]),
                int(r["flag"]),
            ])

        columns = ["tkr", "sec", "flow", "sv", "wr", "flg"]
        definitions = self.config.get("definitions", {})

        input_rows    = int(len(df))
        output_rows   = int(len(named_rows))
        timestamp_iso = datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()
        dropped_rows  = max(0, input_rows - output_rows)
        signal_setup_rows = int(len(signal_setups)) if "signal_setups" in locals() else 0
        signal_flow_conflict_rows = int(signal_flow_conflict_rows)

        # Build enricher diagnostics block for metadata (safe if no enricher)
        sec_diag = self.meta_log.get("sec_enricher_diagnostics", {})

        base_artifact: Dict[str, Any] = {
            "metadata": {
                "status": "success",
                "tool": "stockgrid",
                "schema_version": TOOL_METADATA_SCHEMA_VERSION,
                "data_schema_version": "stockgrid.2",
                "run_id": run_id,
                "as_of": as_of,
                "timestamp": timestamp,
                "timestamp_iso": timestamp_iso,
                "timestamp_epoch_s": timestamp,
                "override_keys": [],
                "items_count": len(named_rows),
                "sector_map": self.sector_map.export(),
                "definitions": definitions,
                "diagnostics": {
                    "input_rows": input_rows,
                    "output_rows": output_rows,
                    "dropped_rows": dropped_rows,
                    "warnings": [],
                    "base_rows": len(named_rows),
                    "join_hit_rate": self.meta_log.get("join_hit_rate", 0.0),
                    "join_eligible_rows": self.meta_log.get("join_eligible_rows", 0),
                    "join_matched_rows": self.meta_log.get("join_matched_rows", 0),
                    "join_hit_rate_eligible": self.meta_log.get("join_hit_rate_eligible", 0.0),
                    "unmatched_tickers_sample": self.meta_log.get("unmatched_tickers_sample", []),
                    "provider_fallback_used": bool(self.meta_log.get("provider_fallback_used", False)),
                    "html_response_count": int(self.meta_log.get("html_response_count", 0) or 0),
                    "signal_setup_rows": signal_setup_rows,
                    "signal_flow_conflict_rows": signal_flow_conflict_rows,
                    # SEC enrichment diagnostics embedded here for traceability
                    "sec_cache_hits":    sec_diag.get("cache_hits", 0),
                    "sec_new_entries":   sec_diag.get("map_new_entries", 0),
                    "sec_misses":        sec_diag.get("sec_misses", 0),
                    "sec_errors":        sec_diag.get("sec_errors", []),
                },
                "quality": {"tone": "ok", "reasons": []},
            },
            "data": {"columns": columns, "rows": named_rows},
        }

        # Adaptive texture fill
        target_kb      = self.tuning.get("target_kb", 60)
        safety_buffer  = self.tuning.get("row_buffer_safety", 0.95)
        current_bytes  = self._measure_json_bytes(base_artifact)
        target_bytes   = target_kb * 1024
        remaining_bytes = target_bytes - current_bytes
        pool = df.drop(named.index)

        if remaining_bytes > 0 and not pool.empty and self.tuning.get("texture_enabled", True):
            default_sample = ["AAAA", "Technology", 50, 50, 50, 0]
            raw_sample = self.tuning.get("texture_sample", default_sample)
            sample_row = list(raw_sample)
            if isinstance(sample_row[1], str):
                sample_row[1] = self.sector_map.encode(sample_row[1])

            row_cost   = self._measure_json_bytes(sample_row) + 1
            fill_count = int((remaining_bytes / row_cost) * safety_buffer)
            fill_count = min(fill_count, len(pool))

            if fill_count > 0:
                texture = pool.sample(n=fill_count, random_state=42)
                for _, r in texture.iterrows():
                    base_artifact["data"]["rows"].append([
                        str(r["ticker"]),
                        self.sector_map.encode(r["sector"]),
                        int(r["flow_m"]),
                        int(r["short_vol"] * 100),
                        _encode_wr(r["win_rate"]),
                        0,
                    ])
                base_artifact["metadata"]["items_count"] += fill_count
                base_artifact["metadata"]["diagnostics"]["output_rows"] = int(base_artifact["metadata"]["items_count"])
                base_artifact["metadata"]["diagnostics"]["texture_rows"] = fill_count
                base_artifact["metadata"]["sector_map"] = self.sector_map.export()

        self._attach_side_datasets(base_artifact, target_bytes)
        final_bytes = self._measure_json_bytes(base_artifact)
        base_artifact["metadata"]["diagnostics"]["target_kb"] = target_kb
        base_artifact["metadata"]["diagnostics"]["final_kb"] = round(final_bytes / 1024, 2)
        base_artifact["metadata"]["quality"] = _build_quality_block(base_artifact["metadata"]["diagnostics"])
        return base_artifact


# ---------------------------------------------------------------------------
# 3. THE ACTOR (MAIN)
# ---------------------------------------------------------------------------


class StandardActor:
    """
    [ROLE]
    - Teleology: Orchestrate ingestion, SEC enrichment, and payload construction into a single artifact envelope.
    - Mechanism: Unwrap config -> ingest -> enrich -> fuse -> build -> flush ref map -> return success/failure envelope.
    """

    TOOL_NAME          = "stockgrid"
    DATA_SCHEMA_VERSION = "stockgrid.2"

    def __init__(self, config: Dict[str, Any], run_dir: Optional[str] = None) -> None:
        c = config
        while isinstance(c, dict) and c.get("type") == "config" and "data" in c:
            c = c["data"]
        self.config: Dict[str, Any] = c
        self.run_dir: Optional[str] = run_dir

    def execute(self) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: End-to-end orchestration: ingest -> SEC-enrich fuse -> build -> flush ticker map.
        - Mechanism:
            1. StockGridDirectEngine.ingest_all()
            2. SecSectorEnricher constructed from config (sec_enabled flag, rate_limit_s).
            3. PayloadFactory(db, config, enricher).fuse() — backfill happens inside fuse().
            4. PayloadFactory.build() — sector integers already resolved.
            5. enricher.flush() — write grown stockgrid_ticker_map.json atomically.
            6. Merge engine diagnostics into artifact.
        - Fails: Any exception → failure envelope (no raise).
        - Guarantee: On success: metadata.status == "success". On failure: metadata.status == "failure", data == {}.
        - When-needed: Open when you need the full stockgrid tool control flow, including where ingestion, SEC enrichment, artifact assembly, and failure-envelope conversion join up.
        - Escalates-to: tools/calculator/calculator.py::run; tools/oracle/subject_index.py::run
        """
        start_ts = time.time()
        runtime_cfg = self.config.get("runtime", {}) if isinstance(self.config.get("runtime"), dict) else {}
        run_id = "manual"
        if self.run_dir:
            try:
                run_id = Path(self.run_dir).name or "manual"
            except Exception:
                run_id = "manual"
        as_of = runtime_cfg.get("as_of") or runtime_cfg.get("time_anchor")
        if isinstance(as_of, str) and as_of.strip():
            try:
                parsed_as_of = datetime.fromisoformat(as_of.strip().replace("Z", "+00:00"))
                if parsed_as_of.tzinfo is None:
                    parsed_as_of = parsed_as_of.replace(tzinfo=timezone.utc)
                else:
                    parsed_as_of = parsed_as_of.astimezone(timezone.utc)
                as_of = parsed_as_of.replace(microsecond=0).isoformat()
            except ValueError:
                as_of = datetime.fromtimestamp(start_ts, tz=timezone.utc).replace(microsecond=0).isoformat()
        else:
            as_of = datetime.fromtimestamp(start_ts, tz=timezone.utc).replace(microsecond=0).isoformat()

        engine: Optional[StockGridDirectEngine] = None
        try:
            # 1. Ingest
            engine = StockGridDirectEngine(self.config)
            engine.ingest_all()

            if not engine.memory_db:
                raise ValueError("No data fetched from StockGrid. Check Endpoints.")

            # 2. Build enricher — respects config flags for opt-out or rate tuning
            sec_cfg = self.config.get("sec_enricher", {})
            enricher = SecSectorEnricher(
                ticker_map_path=_DEFAULT_TICKER_MAP_PATH,
                session=engine.session,        # reuse the same requests.Session
                rate_limit_s=float(sec_cfg.get("rate_limit_s", 0.13)),
                sec_enabled=bool(sec_cfg.get("enabled", True)),
                sec_per_run_limit=int(sec_cfg.get("per_run_limit", 200)),
            )

            # 3. Fuse & enrich
            factory = PayloadFactory(engine.memory_db, self.config, enricher=enricher)
            factory.fuse()

            # 4. Build artifact
            artifact = factory.build(run_id, start_ts, as_of)

            # 5. Flush grown ticker map back to codex/refs/stockgrid_ticker_map.json
            enricher.flush()

            # 6. Merge engine diagnostics
            diagnostics = artifact["metadata"].get("diagnostics", {})
            if isinstance(diagnostics, dict):
                diagnostics.setdefault("input_rows", 0)
                diagnostics.setdefault("output_rows", int(artifact.get("metadata", {}).get("items_count", 0)))
                diagnostics.setdefault("dropped_rows", 0)
                warnings = diagnostics.get("warnings")
                if not isinstance(warnings, list):
                    warnings = [str(warnings)] if warnings else []
                engine_warnings = engine.diagnostics.get("warnings", [])
                if isinstance(engine_warnings, list):
                    warnings.extend(str(msg) for msg in engine_warnings if str(msg).strip())
                engine_errors = engine.diagnostics.get("errors", [])
                if isinstance(engine_errors, list):
                    warnings.extend(str(err) for err in engine_errors if str(err).strip())
                merge_diag = {
                    key: value
                    for key, value in engine.diagnostics.items()
                    if key not in {"errors", "warnings"}
                }
                diagnostics.update(merge_diag)
                deduped_warnings: List[str] = []
                seen_warnings = set()
                for warning in warnings:
                    w = str(warning).strip()
                    if not w or w in seen_warnings:
                        continue
                    seen_warnings.add(w)
                    deduped_warnings.append(w)
                diagnostics["warnings"] = deduped_warnings
                diagnostics["provider_fallback_used"] = bool(
                    diagnostics.get("provider_fallback_used", False)
                ) or any("falling back to axlfi_public" in warning.lower() for warning in deduped_warnings)
                diagnostics["html_response_count"] = max(
                    int(diagnostics.get("html_response_count", 0) or 0),
                    _count_message_matches(deduped_warnings, "non-json HTML response"),
                )
                artifact["metadata"]["diagnostics"] = diagnostics
                artifact["metadata"]["quality"] = _build_quality_block(diagnostics)

            return artifact

        except Exception as e:
            timestamp_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).replace(microsecond=0).isoformat()
            warning = str(e)
            diagnostics: Dict[str, Any] = {
                "input_rows": 0,
                "output_rows": 0,
                "dropped_rows": 0,
                "warnings": [warning] if warning else [],
                "provider_fallback_used": False,
                "html_response_count": 0,
                "join_eligible_rows": 0,
                "join_matched_rows": 0,
                "join_hit_rate_eligible": 0.0,
            }
            failure_data: Dict[str, Any] = {}
            if engine is not None:
                engine_diag = engine.diagnostics if isinstance(engine.diagnostics, dict) else {}
                fetched = engine_diag.get("fetched", {})
                source_errors = engine_diag.get("errors", [])
                source_warnings = engine_diag.get("warnings", [])
                if isinstance(source_errors, list):
                    diagnostics["source_errors"] = [str(err) for err in source_errors if str(err).strip()]
                    diagnostics["warnings"].extend(diagnostics["source_errors"])
                if isinstance(source_warnings, list):
                    diagnostics["source_warnings"] = [str(msg) for msg in source_warnings if str(msg).strip()]
                    diagnostics["warnings"].extend(diagnostics["source_warnings"])
                if isinstance(fetched, dict):
                    diagnostics["fetched"] = dict(fetched)
                for key, value in engine_diag.items():
                    if key not in {"errors", "warnings", "fetched"}:
                        diagnostics[key] = value
                diagnostics["provider_fallback_used"] = bool(
                    diagnostics.get("provider_fallback_used", False)
                ) or any(
                    "falling back to axlfi_public" in str(message).lower()
                    for message in diagnostics.get("warnings", [])
                )
                diagnostics["html_response_count"] = max(
                    int(diagnostics.get("html_response_count", 0) or 0),
                    _count_message_matches(diagnostics.get("warnings", []), "non-json HTML response"),
                )
                failure_data["source_diagnostics"] = engine_diag
            return {
                "metadata": {
                    "status": "failure",
                    "tool": self.TOOL_NAME,
                    "schema_version": TOOL_METADATA_SCHEMA_VERSION,
                    "data_schema_version": self.DATA_SCHEMA_VERSION,
                    "error": str(e),
                    "timestamp": start_ts,
                    "timestamp_iso": timestamp_iso,
                    "timestamp_epoch_s": start_ts,
                    "override_keys": [],
                    "run_id": run_id,
                    "as_of": as_of,
                    "definitions": self.config.get("definitions", {}),
                    "items_count": 0,
                    "diagnostics": diagnostics,
                    "quality": {
                        "tone": "block",
                        "reasons": diagnostics["warnings"] or ["stockgrid feed failed before emission"],
                    },
                },
                "data": failure_data,
            }


def run(config: Dict[str, Any], run_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Entry point required by Zenith tool runner.
    - Mechanism: Construct a StandardActor and return its emitted artifact envelope.
    - When-needed: Open when the market-intelligence runtime only needs the public stockgrid entrypoint contract, not the internal ingestion and packing classes.
    - Escalates-to: tools/stock/stock.py::run; tools/calculator/calculator.py::run; tools/oracle/subject_index.py::run
    """
    actor = StandardActor(config, run_dir)
    return actor.execute()
