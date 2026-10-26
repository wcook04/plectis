"""
[PURPOSE]
- Teleology: Provide deterministic artifact IO utilities for loading, discovering, and extracting data
  from run-directory artifacts. Foundation for Golden ID checks and observer tracing.
- Mechanism: Pure filesystem reads over the artifacts/ subdirectory of a run directory; never writes;
  all functions return None or empty collections on missing data rather than raising.

[INTERFACE]
- Reads: Run directory artifact files (*.json) from run_dir/artifacts/ or run_dir/ fallback.
- Writes: None (read-only utilities).
- Exports: load_artifact, load_artifact_data, discover_feed_artifacts, list_artifact_ledger_ids,
           list_all_artifact_ledger_ids, load_snapshot_ledger_ids, load_equity_universe, EQUITY_FEED_IDS.

[FLOW]
- load_artifact: Reads full artifact envelope from artifacts/{node_id}.json; falls back to run_dir root.
- load_artifact_data: Returns the .data field only.
- discover_feed_artifacts: Finds artifact files by feed node ID list; returns all *.json if feed_ids=None.
- list_artifact_ledger_ids: Extracts ledger_id values from one artifact's evidence_dictionary.
- list_all_artifact_ledger_ids: Unions ledger_ids across all JSON artifacts in a run.
- load_snapshot_ledger_ids: Returns Optional[Set[str]] snapshot ledger set for Golden-ID checks.
- load_equity_universe: Unions ticker sets from global_stock_feed and global_etf_feed artifacts.
- When-needed: Open when Golden-ID checks, observer tracing, or CP2 universe validation need the canonical read-only artifact lookup rules for a run directory.
- Escalates-to: system/lib/artifacts.py::load_artifact; system/lib/contracts.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- Python stdlib: json, pathlib, typing.

[CONSTRAINTS]
- All functions are pure (no mutation, no writes).
- All functions return None or empty collections on any IO or shape failure; never raise.
- Ticker normalization is always .upper().strip().
- load_artifact tries artifacts/ subdir first, then run_dir root (backward-compatible with tools that
  wrote artifacts to the run root before the artifacts/ convention was formalized).
- EQUITY_FEED_IDS defines the canonical set of equity feed node IDs whose ticker sets are unioned for
  CP2 universe validation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Canonical equity feed node IDs whose ticker sets are unioned for CP2 universe checks.
EQUITY_FEED_IDS: List[str] = ["global_stock_feed", "global_etf_feed"]


# ---------------------------------------------------------------------------
# Core load helpers
# ---------------------------------------------------------------------------

def load_artifact(run_dir: Path, node_id: str) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Load the canonical artifact envelope for one run/node pair.
    - Mechanism: Probes run_dir/artifacts/{node_id}.json first, then the legacy run_dir/{node_id}.json location, and returns parsed JSON on the first successful read.
    - Guarantee: Returns the artifact mapping on success or None on any missing-file, parse, or IO failure.
    - Fails: None.
    - When-needed: Open when a caller needs the exact fallback order for reading one artifact envelope from a run directory.
    - Escalates-to: system/lib/artifacts.py::load_artifact_data; system/lib/artifacts.py::list_artifact_ledger_ids
    """
    run_dir = Path(run_dir)
    paths = [
        run_dir / "artifacts" / f"{node_id}.json",
        run_dir / f"{node_id}.json",
    ]
    for p in paths:
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except Exception:
                continue
    return None


def load_artifact_data(run_dir: Path, node_id: str) -> Optional[Any]:
    """
    [ACTION]
    - Load and return only the .data field from the artifact envelope.
    - Returns None if the artifact is missing or the data field is absent.
    - Never raises.
    """
    envelope = load_artifact(run_dir, node_id)
    if envelope is None:
        return None
    return envelope.get("data")


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def discover_feed_artifacts(
    run_dir: Path,
    feed_ids: Optional[List[str]] = None,
) -> List[Path]:
    """
    [ACTION]
    - Teleology: Enumerate the feed artifact files that downstream checks should inspect for one run.
    - Mechanism: Lists run_dir/artifacts/*.json when feed_ids is None or resolves each requested feed id to an existing JSON path in input order.
    - Guarantee: Returns only existing paths and never raises on a missing artifacts directory.
    - Fails: None.
    - When-needed: Open when a caller needs the authoritative discovery rule for feed artifacts before reading them.
    - Escalates-to: system/lib/artifacts.py::load_artifact; system/lib/artifacts.py::load_equity_universe
    """
    artifacts_dir = Path(run_dir) / "artifacts"
    if not artifacts_dir.is_dir():
        return []

    if feed_ids is None:
        return sorted(artifacts_dir.glob("*.json"))

    result: List[Path] = []
    for fid in feed_ids:
        p = artifacts_dir / f"{fid}.json"
        if p.exists():
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Ledger-ID extraction helpers
# ---------------------------------------------------------------------------

def list_artifact_ledger_ids(run_dir: Path, node_id: str) -> Set[str]:
    """
    [ACTION]
    - Teleology: Extract the Golden-ID evidence ledger ids attached to one artifact.
    - Mechanism: Loads the artifact envelope, inspects evidence_dictionary under data first and then the top level, and collects every truthy ledger_id into a set.
    - Guarantee: Returns a deduplicated set of ledger ids or an empty set when the artifact/evidence structure is absent.
    - Fails: None.
    - When-needed: Open when a caller is debugging why one artifact did or did not contribute ledger ids to a Golden-ID comparison.
    - Escalates-to: system/lib/artifacts.py::load_artifact; system/lib/artifacts.py::list_all_artifact_ledger_ids
    """
    envelope = load_artifact(run_dir, node_id)
    if envelope is None:
        return set()

    # evidence_dictionary may live directly in the envelope or nested under .data
    payload = envelope.get("data", envelope)
    evidence = payload.get("evidence_dictionary") if isinstance(payload, dict) else None
    if not isinstance(evidence, list):
        # Try top-level as fallback
        evidence = envelope.get("evidence_dictionary")
    if not isinstance(evidence, list):
        return set()

    ids: Set[str] = set()
    for entry in evidence:
        if isinstance(entry, dict):
            lid = entry.get("ledger_id")
            if lid:
                ids.add(str(lid))
    return ids


def list_all_artifact_ledger_ids(run_dir: Path) -> Set[str]:
    """
    [ACTION]
    - Teleology: Build the full ledger-id set visible in one run directory.
    - Mechanism: Reads every JSON file under run_dir/artifacts/, probes evidence_dictionary under data and top-level shapes, and unions all truthy ledger_id values.
    - Guarantee: Returns a deduplicated set and tolerates malformed artifacts by skipping them.
    - Fails: None.
    - When-needed: Open when a caller needs the exact union rule for all ledger ids across a run before asserting Golden-ID coverage.
    - Escalates-to: system/lib/artifacts.py::list_artifact_ledger_ids; system/lib/artifacts.py::load_snapshot_ledger_ids
    """
    artifacts_dir = Path(run_dir) / "artifacts"
    if not artifacts_dir.is_dir():
        return set()

    all_ids: Set[str] = set()
    for path in artifacts_dir.glob("*.json"):
        try:
            with open(path) as f:
                artifact = json.load(f)
            # evidence may be under .data or at top level
            payload = artifact.get("data", artifact)
            evidence = payload.get("evidence_dictionary") if isinstance(payload, dict) else None
            if not isinstance(evidence, list):
                evidence = artifact.get("evidence_dictionary")
            if isinstance(evidence, list):
                for entry in evidence:
                    if isinstance(entry, dict):
                        lid = entry.get("ledger_id")
                        if lid:
                            all_ids.add(str(lid))
        except Exception:
            continue
    return all_ids


def load_snapshot_ledger_ids(run_dir: Path) -> Optional[Set[str]]:
    """
    [ACTION]
    - Teleology: Surface the run-wide Golden-ID snapshot in the Optional form expected by callers that distinguish missing context from an empty set.
    - Mechanism: Reuses list_all_artifact_ledger_ids() and converts an empty result to None.
    - Guarantee: Returns a non-empty set when ledger ids are discoverable and None otherwise.
    - Fails: None.
    - When-needed: Open when a caller needs the missing-context versus empty-set rule for snapshot ledger loading.
    - Escalates-to: system/lib/artifacts.py::list_all_artifact_ledger_ids
    """
    ledger_ids = list_all_artifact_ledger_ids(Path(run_dir))
    return ledger_ids if ledger_ids else None


# ---------------------------------------------------------------------------
# Equity universe (stock + ETF union) — used by CP2 OUT_OF_UNIVERSE checks
# ---------------------------------------------------------------------------

def _extract_tickers_from_artifact_file(path: Path) -> Set[str]:
    """
    [ACTION]
    - Internal helper: extract ticker set from a stock/ETF feed artifact file.
    - Tries flat format data.{columns, rows} first; then nested data.topic.row.{columns, rows}.
    - Returns empty set on any failure or missing Ticker column.
    - Never raises.
    """
    try:
        with open(path) as f:
            artifact = json.load(f)
        data = artifact.get("data", {})

        # Flat format: data.{columns, rows}
        if isinstance(data, dict) and "columns" in data and "rows" in data:
            columns = data["columns"]
            rows = data["rows"]
            for col_name in ("Ticker", "ticker"):
                if col_name in columns:
                    idx = columns.index(col_name)
                    tickers = {
                        str(r[idx]).upper().strip()
                        for r in rows
                        if isinstance(r, list) and len(r) > idx and r[idx]
                    }
                    if tickers:
                        return tickers

        # Nested format: data.topic.row.{columns, rows}
        if isinstance(data, dict) and isinstance(data.get("topic"), dict):
            row = data["topic"].get("row", {})
            columns = row.get("columns", [])
            rows = row.get("rows", [])
            for col_name in ("Ticker", "ticker"):
                if col_name in columns:
                    idx = columns.index(col_name)
                    tickers = {
                        str(r[idx]).upper().strip()
                        for r in rows
                        if isinstance(r, list) and len(r) > idx and r[idx]
                    }
                    if tickers:
                        return tickers
    except Exception:
        pass
    return set()


def load_equity_universe(run_dir: Path) -> Optional[Set[str]]:
    """
    [ACTION]
    - Teleology: Build the canonical CP2 equity universe from stock and ETF feed artifacts in one run.
    - Mechanism: Tries the canonical EQUITY_FEED_IDS first, extracts uppercase tickers from each artifact, and falls back to stock/etf glob patterns when named feeds are absent.
    - Guarantee: Returns the unioned ticker set when any feed yields tickers, or None when no usable equity feed context exists.
    - Fails: None.
    - When-needed: Open when CP2 OUT_OF_UNIVERSE checks need the exact ticker-union and fallback rules for equity feed artifacts.
    - Escalates-to: system/lib/artifacts.py::discover_feed_artifacts; system/lib/artifacts.py::list_all_artifact_ledger_ids
    """
    artifacts_dir = Path(run_dir) / "artifacts"
    if not artifacts_dir.is_dir():
        return None

    all_tickers: Set[str] = set()

    # Primary: try canonical feed IDs
    for feed_id in EQUITY_FEED_IDS:
        path = artifacts_dir / f"{feed_id}.json"
        if path.exists():
            tickers = _extract_tickers_from_artifact_file(path)
            all_tickers.update(tickers)

    # Fallback: glob for any stock/etf feed artifacts if neither named feed was found
    if not all_tickers:
        for pattern in ("*stock*feed*.json", "*etf*feed*.json"):
            for p in sorted(artifacts_dir.glob(pattern)):
                tickers = _extract_tickers_from_artifact_file(p)
                all_tickers.update(tickers)

    return all_tickers if all_tickers else None
