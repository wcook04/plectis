#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Single durable append point for the lattice event/evidence ledger.
  Every reaction, op, validator, test slice, improver, and Type-A receipt
  routes through here so the ledger stays canonical and replay-safe.
- Mechanism: Canonicalize the event JSON, compute a deterministic event_id from
  sha256(canonical_json(event_minus_event_id)), enforce minimum-required
  invariants, and atomically append one JSONL line to
  state/lattice/events/ledger.jsonl. Idempotent on event_id.

[INTERFACE]
- Exports: append_event, build_event, canonical_dumps, sha256_short, main.
- Reads: state/lattice/events/ledger.jsonl (tail-scan for dedupe; bounded),
  codex/standards/std_lattice_event.json (existence check; not strictly
  validated here — Pass 6 will add a hard validator).
- Writes: state/lattice/events/ledger.jsonl (append-only, atomic).

[CONTRACT]
- Per std_lattice_event.json. Latest_*.json files are projections; this ledger
  is the truth. Updates are forbidden — corrections are new events of type
  'event.correction' that reference the prior event_id.

[CLI]
  python3 append_lattice_event.py --event-json '{...}'        # append one event
  python3 append_lattice_event.py --self-test                 # round-trip a synthetic event
  python3 append_lattice_event.py --tail 5                    # show last N events (read-only)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
LEDGER_DIR = REPO_ROOT / "state" / "lattice" / "events"
LEDGER_PATH = LEDGER_DIR / "ledger.jsonl"
STD_PATH = REPO_ROOT / "codex" / "standards" / "std_lattice_event.json"

REQUIRED_TOP_FIELDS = (
    "schema_version",
    "event_type",
    "occurred_at",
    "actor",
    "trigger",
    "operation",
    "subject",
    "read_set",
    "write_set",
    "result",
    "evidence",
    "next_safe_action",
)

VALID_MUTATION_CLASSES = {"M0R", "M0E", "M1", "M2", "M3", "M4"}
HUMAN_REQUIRED_CLASSES = {"M3", "M4"}
HUMAN_ACTOR_KINDS = {"human", "controller"}


def canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_short(text: str, n: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def now_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _enforce_invariants(event: dict) -> None:
    missing = [f for f in REQUIRED_TOP_FIELDS if f not in event]
    if missing:
        raise ValueError(f"event missing required fields: {missing}")
    if event["schema_version"] != 1:
        raise ValueError(f"unsupported schema_version: {event['schema_version']!r} (expected 1)")
    op = event.get("operation", {})
    mc = op.get("mutation_class")
    if mc not in VALID_MUTATION_CLASSES:
        raise ValueError(f"operation.mutation_class must be one of {VALID_MUTATION_CLASSES}, got {mc!r}")
    if mc in HUMAN_REQUIRED_CLASSES:
        actor_kind = event.get("actor", {}).get("kind")
        if actor_kind not in HUMAN_ACTOR_KINDS:
            raise ValueError(
                f"mutation_class {mc} requires actor.kind in {HUMAN_ACTOR_KINDS}, got {actor_kind!r}"
            )
    actor_kind = event.get("actor", {}).get("kind")
    non_human = actor_kind not in HUMAN_ACTOR_KINDS
    if non_human and not op.get("idempotency_key"):
        raise ValueError(
            f"operation.idempotency_key is required for non-human actor.kind={actor_kind!r}"
        )


def build_event(
    *,
    event_type: str,
    actor: dict,
    trigger: dict,
    operation: dict,
    subject: dict | None = None,
    read_set: list | None = None,
    write_set: list | None = None,
    result: dict | None = None,
    evidence: list | None = None,
    next_safe_action: str = "none",
    occurred_at: str | None = None,
) -> dict:
    event = {
        "schema_version": 1,
        "event_type": event_type,
        "occurred_at": occurred_at or now_rfc3339(),
        "actor": actor,
        "trigger": trigger,
        "operation": operation,
        "subject": subject or {"artifact_kind": "unknown", "paths": []},
        "read_set": read_set or [],
        "write_set": write_set or [],
        "result": result or {"status": "passed", "duration_s": 0.0},
        "evidence": evidence or [],
        "next_safe_action": next_safe_action,
    }
    event["event_id"] = "evt_" + sha256_short(canonical_dumps(event))
    return event


def lookup_idempotent_success(
    op_name: str,
    idempotency_key: str,
    *,
    path: Path | None = None,
    limit: int = 8192,
) -> dict | None:
    """Return the most recent ledger event whose operation.name == op_name,
    operation.idempotency_key == idempotency_key, and result.status == 'passed'.
    None if no such prior success exists. Used by callers to short-circuit
    equivalent work — distinct from event_id dedupe (which catches literally
    identical ledger rows).
    """
    target = path or LEDGER_PATH
    if not target.exists():
        return None
    rows: list[str] = []
    with target.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                rows.append(raw)
    for raw in reversed(rows[-limit:]):
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        op = row.get("operation", {}) or {}
        if op.get("name") != op_name or op.get("idempotency_key") != idempotency_key:
            continue
        if (row.get("result") or {}).get("status") != "passed":
            continue
        return row
    return None


def _tail_event_ids(path: Path, limit: int = 4096) -> set[str]:
    if not path.exists():
        return set()
    out: list[str] = []
    with path.open("rb") as f:
        try:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 65536
            tail = b""
            while size > 0 and len(out) < limit:
                step = min(block, size)
                size -= step
                f.seek(size)
                tail = f.read(step) + tail
                out = tail.splitlines()
        except OSError:
            f.seek(0)
            out = f.read().splitlines()
    ids: set[str] = set()
    for raw in out[-limit:]:
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        eid = row.get("event_id")
        if eid:
            ids.add(eid)
    return ids


def append_event(event: dict) -> dict:
    _enforce_invariants(event)
    if "event_id" not in event:
        # Recompute deterministically without the event_id field.
        ev_min = {k: v for k, v in event.items() if k != "event_id"}
        event["event_id"] = "evt_" + sha256_short(canonical_dumps(ev_min))
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    existing = _tail_event_ids(LEDGER_PATH, limit=4096)
    if event["event_id"] in existing:
        return {"status": "duplicate_skipped", "event_id": event["event_id"], "ledger_path": str(LEDGER_PATH)}
    line = canonical_dumps(event) + "\n"
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
    return {"status": "appended", "event_id": event["event_id"], "ledger_path": str(LEDGER_PATH)}


def _validate_no_write() -> int:
    """Read-only validation suitable for use as a validator inside a test slice.
    Checks that std_lattice_event.json parses, that the ledger (if present) is
    line-by-line valid JSON, and that build_event + canonicalize round-trips
    deterministically WITHOUT appending. Exit 0 on success.
    """
    if not STD_PATH.exists():
        print(f"[FAIL] std_lattice_event.json missing at {STD_PATH}", file=sys.stderr)
        return 2
    try:
        with STD_PATH.open("r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as exc:
        print(f"[FAIL] std_lattice_event.json invalid JSON: {exc}", file=sys.stderr)
        return 2
    bad_lines = 0
    line_count = 0
    if LEDGER_PATH.exists():
        with LEDGER_PATH.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                line_count += 1
                try:
                    json.loads(raw)
                except json.JSONDecodeError:
                    bad_lines += 1
    ev = build_event(
        event_type="lattice.validate_no_write",
        actor={"kind": "validator", "id": "append_lattice_event.py"},
        trigger={"kind": "manual", "id": "validate"},
        operation={
            "name": "append_lattice_event_validate",
            "attempt_id": "static",
            "idempotency_key": "validate_static_v1",
            "mutation_class": "M0R",
        },
        subject={"artifact_kind": "lattice_event", "paths": []},
        result={"status": "passed", "duration_s": 0.0},
        occurred_at="2026-01-01T00:00:00+00:00",
    )
    parsed = json.loads(canonical_dumps(ev))
    if parsed["event_id"] != ev["event_id"]:
        print("[FAIL] event_id round-trip mismatch", file=sys.stderr)
        return 2
    if bad_lines:
        print(f"[FAIL] ledger has {bad_lines} unparseable lines (of {line_count})", file=sys.stderr)
        return 2
    print(json.dumps({
        "validate": "ok",
        "ledger_lines": line_count,
        "bad_lines": bad_lines,
        "writes": "none (M0R)",
    }, indent=2))
    return 0


def _self_test() -> int:
    if not STD_PATH.exists():
        print(f"[FAIL] std_lattice_event.json missing at {STD_PATH}", file=sys.stderr)
        return 2
    try:
        with STD_PATH.open("r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as exc:
        print(f"[FAIL] std_lattice_event.json invalid JSON: {exc}", file=sys.stderr)
        return 2
    ev = build_event(
        event_type="lattice.self_test",
        actor={"kind": "validator", "id": "append_lattice_event.py"},
        trigger={"kind": "manual", "id": "self-test"},
        operation={
            "name": "append_lattice_event_self_test",
            "attempt_id": f"attempt_{int(time.time())}",
            "idempotency_key": "self_test_static_key_v1",
            "mutation_class": "M0E",
        },
        subject={"artifact_kind": "lattice_event", "paths": [str(LEDGER_PATH)]},
        result={"status": "passed", "duration_s": 0.0},
        next_safe_action="none",
    )
    res = append_event(ev)
    line = canonical_dumps(ev)
    parsed = json.loads(line)
    if parsed["event_id"] != ev["event_id"]:
        print(f"[FAIL] event_id round-trip mismatch", file=sys.stderr)
        return 2
    print(json.dumps({"self_test": "ok", **res, "event_id": ev["event_id"]}, indent=2))
    return 0


def _tail(n: int) -> int:
    if not LEDGER_PATH.exists():
        print(json.dumps({"tail": [], "ledger_path": str(LEDGER_PATH), "exists": False}, indent=2))
        return 0
    rows: list[dict] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    print(json.dumps({"tail": rows[-n:], "count": len(rows), "ledger_path": str(LEDGER_PATH)}, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Append a lattice event to the canonical ledger.")
    ap.add_argument("--event-json", type=str, default=None, help="Inline JSON event payload (will compute event_id if missing).")
    ap.add_argument("--event-file", type=str, default=None, help="Path to a JSON file containing one event payload.")
    ap.add_argument("--self-test", action="store_true", help="Append a synthetic self-test event and verify round-trip (M0E: writes one event).")
    ap.add_argument("--validate", action="store_true", help="No-write substrate validation (M0R). Use this from validators inside test slices.")
    ap.add_argument("--tail", type=int, default=0, help="Print the last N events as JSON (read-only).")
    args = ap.parse_args()

    if args.validate:
        return _validate_no_write()
    if args.self_test:
        return _self_test()
    if args.tail and args.tail > 0:
        return _tail(args.tail)
    if args.event_json:
        ev = json.loads(args.event_json)
        res = append_event(ev)
        print(json.dumps(res, indent=2))
        return 0
    if args.event_file:
        with open(args.event_file, "r", encoding="utf-8") as f:
            ev = json.load(f)
        res = append_event(ev)
        print(json.dumps(res, indent=2))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
