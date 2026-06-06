"""
[PURPOSE]
- Teleology: Provide canonical, deterministic ledger_id generation for all diff lanes.
  A ledger_id is the stable unique identifier for an evidence record across Lab/Oracle runs.
- Mechanism: normalize_lane() + canonical_identity_key() → hash "{lane}|{key}" (SHA256, 8 hex).

[INTERFACE]
- Exports: normalize_lane, canonical_identity_key, generate_ledger_id, generate_ledger_id_raw.
- Reads: Nothing (pure function).
- Writes: Nothing (pure function).

[FLOW]
- normalize_lane: .upper().strip() + alias map → canonical lane name (e.g. "poly" → "POLYMARKET").
- canonical_identity_key: per-lane dispatch to extract the identity string from a record dict/tuple.
- generate_ledger_id: normalize → extract key → generate_ledger_id_raw.
- generate_ledger_id_raw: compatibility shim for callers holding a raw identity string already.

[DEPENDENCIES]
- Python stdlib: hashlib, typing.

[CONSTRAINTS]
- Hash input is always "{lane_norm}|{identity_key}" (UTF-8, SHA256, first 8 uppercase hex).
- Lane canonicalization: .upper().strip() then alias lookup — normalize_lane() is the sole entry.
- ETF/ETFS → STOCK (v0 equity rule: no ETF lane or prefix; both feeds stay S_ prefix).
- Unknown lanes map to prefix "X" and still hash correctly (no crash).
- canonical_identity_key raises ValueError on missing key — callers must handle gracefully.
- STOCK and STOCKGRID identity keys are uppercased; others returned as-is.
- When-needed: Open when a diff or refinement surface needs the canonical lane aliasing and stable ledger_id contract used to correlate evidence across runs.
- Escalates-to: tools/diff/observer_lane_diff.py::run; tools/diff/observer_diff_master.py::run
- Navigation-group: diff_refinement
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Union

# ---------------------------------------------------------------------------
# Lane alias map and prefix map
# ---------------------------------------------------------------------------

_LANE_ALIASES: Dict[str, str] = {
    # Canonical names map to themselves
    "STOCK": "STOCK",
    "MACRO": "MACRO",
    "POLYMARKET": "POLYMARKET",
    "STOCKGRID": "STOCKGRID",
    "NEWS": "NEWS",
    "CALCULATOR": "CALCULATOR",
    # Short aliases
    "POLY": "POLYMARKET",
    "CALC": "CALCULATOR",
    # ETF → STOCK: v0 split-feed design keeps ETFs in the STOCK lane (Locked Decision 13)
    "ETF": "STOCK",
    "ETFS": "STOCK",
}

_PREFIXES: Dict[str, str] = {
    "STOCK": "S",
    "MACRO": "M",
    "POLYMARKET": "P",
    "STOCKGRID": "G",
    "NEWS": "N",
    "CALCULATOR": "C",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_lane(lane: str) -> str:
    """
    [ACTION]
    - Teleology: Collapse caller-supplied lane labels onto the canonical diff-lane vocabulary before identity extraction or prefix selection.
    - Mechanism: Uppercase and trim the input, then resolve aliases through _LANE_ALIASES.
    - Guarantee: Returns a canonical uppercase lane name; unknown lanes pass through uppercased instead of failing.
    - Fails: None.
    - When-needed: Open when a caller only needs the alias contract for POLY/CALC/ETF-style lane variants before reading full diff execution surfaces.
    - Escalates-to: tools/diff/observer_lane_diff.py::run
    """
    key = lane.upper().strip()
    return _LANE_ALIASES.get(key, key)


def canonical_identity_key(lane: str, record: Any) -> str:
    """
    [ACTION]
    - Teleology: Extract the per-lane identity field that must remain stable before hashing into a ledger_id.
    - Mechanism: Normalize lane first, then dispatch to the lane-specific key contract for dict or tuple-shaped records.
    - Guarantee: Returns the canonical identity string for supported lanes and uppercases STOCK/STOCKGRID identities before returning.
    - Fails: Raises ValueError when a supported lane record is missing its required identity field or has the wrong container type.
    - Schema: STOCK -> Ticker/ticker; MACRO -> slug or Ticker/ticker; POLYMARKET -> slug; STOCKGRID -> tkr; NEWS -> url; CALCULATOR -> record[0]; unknown lanes use best-effort extraction.
    - When-needed: Open when a diff lane is producing unstable IDs and you need the exact field-selection contract instead of only the final hash output.
    - Escalates-to: tools/diff/observer_lane_diff.py::run; tools/diff/observer_diff_master.py::run
    """
    lane_norm = normalize_lane(lane)

    if lane_norm == "STOCK":
        if isinstance(record, dict):
            key = record.get("Ticker") or record.get("ticker")
            if not key:
                raise ValueError(f"STOCK record missing 'Ticker'/'ticker': {record!r}")
            return str(key).strip().upper()
        raise ValueError(f"STOCK record must be a dict, got {type(record).__name__}")

    if lane_norm == "MACRO":
        if isinstance(record, dict):
            slug = record.get("slug")
            if slug:
                return str(slug)
            ticker = record.get("Ticker") or record.get("ticker")
            if ticker:
                return str(ticker)
            raise ValueError(f"MACRO record missing 'slug'/'Ticker'/'ticker': {record!r}")
        raise ValueError(f"MACRO record must be a dict, got {type(record).__name__}")

    if lane_norm == "POLYMARKET":
        if isinstance(record, dict):
            slug = record.get("slug")
            if not slug:
                raise ValueError(f"POLYMARKET record missing 'slug': {record!r}")
            return str(slug)
        raise ValueError(f"POLYMARKET record must be a dict, got {type(record).__name__}")

    if lane_norm == "STOCKGRID":
        if isinstance(record, dict):
            tkr = record.get("tkr")
            if not tkr:
                raise ValueError(f"STOCKGRID record missing 'tkr': {record!r}")
            return str(tkr).strip().upper()
        raise ValueError(f"STOCKGRID record must be a dict, got {type(record).__name__}")

    if lane_norm == "NEWS":
        if isinstance(record, dict):
            url = record.get("url")
            if not url:
                raise ValueError(f"NEWS record missing 'url': {record!r}")
            return str(url)
        raise ValueError(f"NEWS record must be a dict, got {type(record).__name__}")

    if lane_norm == "CALCULATOR":
        if isinstance(record, (list, tuple)) and record:
            return str(record[0])
        raise ValueError(
            f"CALCULATOR record must be a non-empty list/tuple, got {type(record).__name__}: {record!r}"
        )

    # Unknown lane — best-effort, no crash
    if isinstance(record, dict):
        for k in ("Ticker", "ticker", "slug", "url", "tkr"):
            if record.get(k):
                return str(record[k])
        return str(next(iter(record.values()))) if record else "unknown"
    if isinstance(record, (list, tuple)) and record:
        return str(record[0])
    return str(record)


def generate_ledger_id_raw(lane: str, identity_key: str) -> str:
    """
    [ACTION]
    - Teleology: Preserve deterministic ledger_id generation for callers that already hold a normalized identity string.
    - Mechanism: Normalize the lane, choose its prefix from _PREFIXES, hash "{lane_norm}|{identity_key}" with SHA256, and emit the first 8 uppercase hex digits.
    - Guarantee: Returns `<prefix>_<sha8>` and uses prefix X for unknown lanes without failing.
    - Fails: None.
    - When-needed: Open when a legacy diff caller already extracted the identity key and only needs the exact hash-and-prefix contract.
    - Escalates-to: tools/diff/observer_lane_diff.py::run
    """
    lane_norm = normalize_lane(lane)
    prefix = _PREFIXES.get(lane_norm, "X")
    hash_input = f"{lane_norm}|{identity_key}"
    sha8 = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}_{sha8}"


def generate_ledger_id(lane: str, record: Any) -> str:
    """
    [ACTION]
    - Teleology: Provide the one-call public path from raw lane plus record payload to the stable ledger_id shared across diff artifacts.
    - Mechanism: Calls normalize_lane(), canonical_identity_key(), and generate_ledger_id_raw() in sequence.
    - Guarantee: Returns the deterministic ledger_id for the supplied record whenever the lane contract can extract an identity key.
    - Fails: Raises ValueError if the required identity key is absent or the record shape violates the supported lane contract.
    - When-needed: Open when a caller needs the authoritative generate_ledger_id end-to-end ledger_id path instead of re-deriving normalization and hash rules from sibling helpers.
    - Escalates-to: tools/diff/observer_lane_diff.py::run; tools/diff/observer_diff_master.py::run
    - Navigation-group: diff_refinement
    """
    lane_norm = normalize_lane(lane)
    key = canonical_identity_key(lane_norm, record)
    return generate_ledger_id_raw(lane_norm, key)
