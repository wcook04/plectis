#!/usr/bin/env python3
"""
Confirm EDC-normalized route discovery proposals before accepted-edge promotion.

[PURPOSE]
- Teleology: Keep invented edges useful without letting them mutate the route
  universe directly.
- Mechanism: Re-canonicalize proposals, verify path/verb/evidence shape, dedupe
  against accepted edges, and write a confirmation receipt. Optional accepted
  ledger append is explicit and conservative.
- Non-goal: This script does not update the canonical semantic route graph.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import route_discovery_edc  # noqa: E402
from system.lib.repo_env import maybe_reexec_into_repo_python  # noqa: E402
from tools.meta.control import routing_pilot_harness  # noqa: E402


if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)


CONFIRMATION_ROOT_REL = "state/raw_seed_routing_pilot/discovery_confirmations"
STOPWORDS = {
    "about",
    "after",
    "because",
    "from",
    "into",
    "that",
    "this",
    "with",
    "source",
    "target",
    "route",
    "edge",
    "file",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return rows


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def _words(value: str) -> set[str]:
    return {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", value)
        if word.lower() not in STOPWORDS
    }


def _read_file_text(path: str) -> str:
    try:
        return (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return ""


def _evidence_items(value: Any, bucket: str | None = None) -> list[str]:
    if isinstance(value, Mapping):
        items: list[str] = []
        buckets = [bucket] if bucket else ["source_evidence", "target_evidence", "bridge_evidence"]
        for key in buckets:
            nested = value.get(key)
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, Mapping):
                        items.append(str(item.get("text") or ""))
                    else:
                        items.append(str(item))
        return [item for item in items if item.strip()]
    if isinstance(value, list):
        return [str(item.get("text") if isinstance(item, Mapping) else item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def _support_score(path: str, evidence_texts: Sequence[str]) -> dict[str, Any]:
    haystack = _read_file_text(path)
    if not haystack or not evidence_texts:
        return {"supported": 0, "total": len(evidence_texts), "rate": 0.0, "mode": "missing"}
    supported = 0
    for text in evidence_texts:
        normalized = str(text or "").strip().lower()
        if not normalized:
            continue
        if normalized in haystack:
            supported += 1
            continue
        evidence_words = _words(normalized)
        if evidence_words:
            overlap = len(evidence_words & _words(haystack[:80000])) / max(1, len(evidence_words))
            if overlap >= 0.45:
                supported += 1
    total = len([text for text in evidence_texts if str(text).strip()])
    return {
        "supported": supported,
        "total": total,
        "rate": supported / total if total else 0.0,
        "mode": "substring_or_token_overlap",
    }


def _accepted_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("source") or ""),
        str(row.get("target") or ""),
        str(row.get("verb") or row.get("connector_verb") or row.get("nearest_canonical_verb") or ""),
    )


def _accepted_id(row: Mapping[str, Any]) -> str:
    return str(row.get("accepted_edge_id") or row.get("proposal_id") or row.get("fingerprint") or "")


def _confirmation_id(row: Mapping[str, Any]) -> str:
    base = str(row.get("proposal_id") or row.get("fingerprint") or json.dumps(row, sort_keys=True))
    return "confirm_" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def confirm_proposals(*, limit: int | None = None, accept: bool = False) -> dict[str, Any]:
    proposed_path = REPO_ROOT / routing_pilot_harness.PROPOSED_EDGES_REL
    accepted_path = REPO_ROOT / routing_pilot_harness.ACCEPTED_EDGES_REL
    grammar = routing_pilot_harness._read_json(routing_pilot_harness.GRAMMAR_REL)
    baseline = routing_pilot_harness._read_json(routing_pilot_harness.BASELINE_REL)
    allowed_verbs = routing_pilot_harness._base_verbs(grammar, baseline)
    proposed = _read_jsonl(proposed_path)
    accepted = _read_jsonl(accepted_path)
    accepted_index = {_accepted_key(row): _accepted_id(row) for row in accepted}
    seen_rows: list[dict[str, Any]] = []
    seen_index: dict[tuple[str, str, str], str] = {}
    rows: list[dict[str, Any]] = []
    accepted_appended = 0

    for proposal in proposed[:limit]:
        edc = route_discovery_edc.canonicalize_discovery_edge(
            proposal,
            allowed_verbs=allowed_verbs,
            existing_rows=[*accepted, *seen_rows],
        )
        source = str(edc.get("source") or "")
        target = str(edc.get("target") or "")
        verb = str(edc.get("nearest_canonical_verb") or "")
        key = (source, target, verb)
        source_exists = (REPO_ROOT / source).exists()
        target_exists = (REPO_ROOT / target).exists()
        evidence = proposal.get("evidence") or proposal.get("evidence_set") or proposal.get("evidence_phrases") or []
        source_support = _support_score(source, _evidence_items(evidence, "source_evidence"))
        target_support = _support_score(target, _evidence_items(evidence, "target_evidence"))
        bridge_items = _evidence_items(evidence, "bridge_evidence")
        if not bridge_items and isinstance(evidence, list):
            bridge_items = [str(item) for item in evidence if str(item).strip()]
        duplicate_of = edc.get("duplicate_of") or accepted_index.get(key) or seen_index.get(key)
        path_valid = source_exists and target_exists
        verb_valid = verb in allowed_verbs
        definition_valid = bool(str(proposal.get("definition") or edc.get("definition") or "").strip())
        bridge_valid = bool(bridge_items)
        support_rate = (float(source_support["rate"]) + float(target_support["rate"])) / 2
        deterministic_ready = (
            path_valid
            and verb_valid
            and definition_valid
            and bridge_valid
            and support_rate >= 0.4
            and not duplicate_of
            and edc.get("canonicalization_status") != "proposed_new_relation_pattern"
        )
        status = (
            "duplicate_candidate"
            if duplicate_of
            else "deterministically_confirmed"
            if deterministic_ready
            else "needs_controller_review"
        )
        receipt = {
            "kind": "route_discovery_confirmation",
            "schema_version": "route_discovery_confirmation_v1",
            "confirmation_id": _confirmation_id(proposal),
            "proposal_id": proposal.get("proposal_id"),
            "source": source,
            "target": target,
            "verb": verb,
            "status": status,
            "path_valid": path_valid,
            "verb_valid": verb_valid,
            "definition_valid": definition_valid,
            "bridge_evidence_present": bridge_valid,
            "source_evidence_support": source_support,
            "target_evidence_support": target_support,
            "support_rate": support_rate,
            "duplicate_of": duplicate_of,
            "edc": edc,
            "accepted_edge_ref": None,
        }
        if accept and deterministic_ready:
            accepted_row = {
                "kind": "accepted_route_edge",
                "schema_version": "accepted_route_edge_v1",
                "accepted_edge_id": f"aedge_{uuid.uuid4().hex[:16]}",
                "accepted_at": _utc_now(),
                "source": source,
                "target": target,
                "verb": verb,
                "definition": proposal.get("definition") or edc.get("definition"),
                "source_proposal_id": proposal.get("proposal_id"),
                "confirmation_id": receipt["confirmation_id"],
                "promotion_scope": "accepted_ledger_only_not_canonical_graph",
            }
            _append_jsonl(accepted_path, accepted_row)
            receipt["accepted_edge_ref"] = routing_pilot_harness.ACCEPTED_EDGES_REL
            accepted_appended += 1
        seen_rows.append(proposal)
        seen_index[key] = str(proposal.get("proposal_id") or proposal.get("fingerprint") or "")
        rows.append(receipt)

    return {
        "kind": "route_discovery_confirmation_batch",
        "schema_version": "route_discovery_confirmation_batch_v1",
        "generated_at": _utc_now(),
        "proposed_edges_ref": routing_pilot_harness.PROPOSED_EDGES_REL,
        "accepted_edges_ref": routing_pilot_harness.ACCEPTED_EDGES_REL,
        "proposal_count": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "accepted_appended": accepted_appended,
        "confirmations": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--accept", action="store_true", help="Append deterministically confirmed rows to accepted_edges.jsonl")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    payload = confirm_proposals(limit=args.limit, accept=args.accept)
    if args.write:
        run_id = args.run_id or f"rdc_{uuid.uuid4().hex[:16]}"
        path = REPO_ROOT / CONFIRMATION_ROOT_REL / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["confirmation_ref"] = path.relative_to(REPO_ROOT).as_posix()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
