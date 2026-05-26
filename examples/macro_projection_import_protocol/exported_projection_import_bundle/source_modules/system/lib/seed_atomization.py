"""
[PURPOSE]
- Teleology: Own the family-level raw-seed atomization loop that converts synced
  raw-seed paragraphs into atomized extracted-shard rows, keeps a coverage
  report on disk, and prepares controller-gated doctrine-routing review
  proposals.

[INTERFACE]
- Exports: atomize_family_raw_seed, ingest_family_raw_seed_distillations,
  route_family_atomized_shards, load_raw_seed_pipeline_snapshot,
  normalize_routing_review_payload,
  provider_safe_parallelism, and path helpers for the family-scope
  extracted/coverage/review/distillation artifacts.
- Reads: family raw_seed.json, raw_seed/raw_seed_shards.json,
  raw_seed/raw_seed_principles.json, doctrine concept/mechanism JSON, and
  tools/meta/bridge/provider_capabilities.json.
- Writes: family-root extracted_shards.json, raw_seed/raw_seed_coverage.json,
  raw_seed/raw_seed_routing_review.json, and
  raw_seed/raw_seed_distillations.json.

[FLOW]
- Load the synced family raw-seed registry.
- Atomize selected paragraphs into extracted_shards rows using a deterministic
  heuristic split.
- Rebuild browser_index and coverage on every write.
- Ingest bridge-authored paragraph distillations as a family artifact that keeps
  paragraph provenance intact and can later feed atomization.
- Score unrouted atomized shards against doctrine nodes and write review-only
  routing proposals with provider-safe batching metadata.

[CONSTRAINTS]
- The family raw seed remains append-only; this module never edits raw_seed.md.
- Doctrine mutation is controller-gated; routing review writes proposals only.
- The extracted_shards family backlog remains the single atomized-shard store;
  this module does not mint a parallel shard artifact.
- Distillation ingestion is additive only; it preserves paragraph-level
  provenance and only influences atomization for paragraphs not yet atomized.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib.dispatch_policy import (
    load_provider_capabilities as _load_dispatch_provider_capabilities,
    provider_ceiling_for_provider,
    resolve_dispatch_policy,
)
from system.lib.json_payloads import extract_json_object
from system.lib.markdown_routing import extract_observe_artifact_payload
from system.lib.raw_seed_registry import (
    agent_seed_json_path_for_family,
    build_raw_seed_shards,
    raw_seed_json_path_for_family,
    raw_seed_principles_path_for_family,
    raw_seed_shards_path_for_family,
    raw_seed_workspace_dir_for_family,
)
from system.lib.shard_browser import (
    _browser_index_for_shards,
    enrich_shard_routing_metadata,
    load_shards,
)
from system.lib.shard_packet_selection import (
    load_shard_batch_packet,
    select_shards as select_packet_shards,
    shard_group_ids,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

EXTRACTED_SHARDS_FILENAME = "extracted_shards.json"
RAW_SEED_COVERAGE_FILENAME = "raw_seed_coverage.json"
RAW_SEED_ROUTING_REVIEW_FILENAME = "raw_seed_routing_review.json"
RAW_SEED_DISTILLATIONS_FILENAME = "raw_seed_distillations.json"
RAW_SEED_ATOMIZATION_LEDGER_FILENAME = "raw_seed_atomization_ledger.json"
RAW_SEED_COVERAGE_SCHEMA_VERSION = "raw_seed_coverage_v1"
RAW_SEED_ROUTING_REVIEW_SCHEMA_VERSION = "raw_seed_routing_review_v1"
RAW_SEED_DISTILLATIONS_SCHEMA_VERSION = "raw_seed_distillations_v1"
RAW_SEED_ATOMIZATION_LEDGER_SCHEMA_VERSION = "raw_seed_atomization_ledger_v1"
ATOMIZATION_SOURCE = "raw_seed_atomization_local_v1"
ATOMIZATION_BRIDGE_SOURCE = "raw_seed_atomization_bridge_v1"
DISTILLATION_SOURCE = "raw_seed_distillation_bridge_ingest_v1"
DEFAULT_COHORT_SIZE = 12
DEFAULT_QUEUE_DEPTH = 10
DEFAULT_ACTIVE_WORKERS = 3
DEFAULT_PROVIDER = "chatgpt"
ROUTING_REVIEW_THRESHOLD = 0.85
AMBIGUITY_DELTA = 1
ATOMIZATION_MISSION_ID = "raw_seed_atomization"
ROUTING_MISSION_ID = "raw_seed_doctrine_routing"
DEFAULT_ATOMIZATION_CONTEXT_WINDOW = 1
DEFAULT_ATOMIZATION_OUTPUT_ROOT = f"state/meta_missions/{ATOMIZATION_MISSION_ID}/runs"
DEFAULT_ATOMIZATION_DUMP_ROOT = f"tools/meta/apply/observe_dumps/{ATOMIZATION_MISSION_ID}"
SELECTION_MODE_FRESH_FIRST = "fresh_first"
SELECTION_MODE_OLDEST_FIRST = "oldest_first"
SELECTION_MODE_MIXED = "mixed"
VALID_SELECTION_MODES = {
    SELECTION_MODE_FRESH_FIRST,
    SELECTION_MODE_OLDEST_FIRST,
    SELECTION_MODE_MIXED,
}
DEFAULT_ATOMIZE_SELECTION_MODE = SELECTION_MODE_FRESH_FIRST
DEFAULT_ROUTE_SELECTION_MODE = SELECTION_MODE_FRESH_FIRST
LOW_SIGNAL_ROUTING_STATEMENTS = {
    "---",
    "{{",
    "}}",
    "a bare separator line.",
    "thinking.",
    "in.",
    "out.",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ").lower()


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _proposal_is_pending_review(proposal: Mapping[str, Any]) -> bool:
    status = _string(proposal.get("status")).strip()
    member_proposals = proposal.get("member_proposals")
    if isinstance(member_proposals, list):
        return any(
            isinstance(member, Mapping) and _proposal_is_pending_review(member)
            for member in member_proposals
        )
    return not status or status == "pending_review"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def family_extracted_shards_path(family_dir: str) -> str:
    family_dir = _string(family_dir).strip().strip("/")
    return f"{family_dir}/{EXTRACTED_SHARDS_FILENAME}" if family_dir else EXTRACTED_SHARDS_FILENAME


def family_raw_seed_coverage_path(family_dir: str) -> str:
    workspace = raw_seed_workspace_dir_for_family(family_dir)
    return f"{workspace}/{RAW_SEED_COVERAGE_FILENAME}"


def family_raw_seed_routing_review_path(family_dir: str) -> str:
    workspace = raw_seed_workspace_dir_for_family(family_dir)
    return f"{workspace}/{RAW_SEED_ROUTING_REVIEW_FILENAME}"


def family_raw_seed_distillations_path(family_dir: str) -> str:
    workspace = raw_seed_workspace_dir_for_family(family_dir)
    return f"{workspace}/{RAW_SEED_DISTILLATIONS_FILENAME}"


def family_raw_seed_atomization_ledger_path(family_dir: str) -> str:
    workspace = raw_seed_workspace_dir_for_family(family_dir)
    return f"{workspace}/{RAW_SEED_ATOMIZATION_LEDGER_FILENAME}"


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", _string(text)).strip()


def _ordinal_label(index: int) -> str:
    index = max(0, int(index))
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    label = ""
    current = index
    while True:
        current, remainder = divmod(current, 26)
        label = alphabet[remainder] + label
        if current == 0:
            return label
        current -= 1


def _sentence_units(text: str) -> list[str]:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return []

    sentence_like = [
        piece.strip(" -")
        for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", normalized)
        if piece.strip(" -")
    ]
    if not sentence_like:
        sentence_like = [normalized]

    units: list[str] = []
    for sentence in sentence_like:
        semicolon_parts = [part.strip(" ,") for part in re.split(r"\s*;\s*", sentence) if part.strip(" ,")]
        units.extend(semicolon_parts or [sentence])

    if len(units) == 1 and len(units[0]) > 280:
        clause_parts = [
            part.strip(" ,")
            for part in re.split(
                r",\s+(?=(?:and|but|so|because|which|then|while|whereas|although|however)\b)",
                units[0],
                flags=re.IGNORECASE,
            )
            if part.strip(" ,")
        ]
        if len(clause_parts) > 1:
            units = clause_parts

    merged: list[str] = []
    for unit in units:
        if merged and len(unit) < 40:
            merged[-1] = _normalize_whitespace(f"{merged[-1]} {unit}")
            continue
        merged.append(_normalize_whitespace(unit))
    return [unit for unit in merged if unit]


def _stable_atom_id(
    parent_paragraph_id: str,
    segment_ordinal: str,
    statement: str,
    *,
    voice_anchor: str = "",
    support_excerpt: str = "",
) -> str:
    anchor_seed = _normalize_whitespace(voice_anchor or support_excerpt or statement)
    seed = f"{parent_paragraph_id}:{segment_ordinal}:{anchor_seed}".encode("utf-8")
    return f"atom_{hashlib.sha1(seed).hexdigest()[:12]}"


def _stable_distillation_id(paragraph_id: str, batch_id: str, statements: Iterable[str]) -> str:
    joined = "|".join(_normalize_whitespace(statement) for statement in statements if _normalize_whitespace(statement))
    seed = f"{paragraph_id}:{batch_id}:{joined}".encode("utf-8")
    return f"dist_{hashlib.sha1(seed).hexdigest()[:12]}"


def _paragraph_anchor(paragraph: Mapping[str, Any]) -> str:
    paragraph_id = _string(paragraph.get("id"))
    if paragraph_id:
        return f"paragraph:{paragraph_id}"
    start = paragraph.get("line_start")
    end = paragraph.get("line_end")
    if isinstance(start, int) and isinstance(end, int):
        return f"lines:{start}-{end}"
    return "paragraph:unknown"


def _paragraph_text(paragraph: Mapping[str, Any]) -> str:
    for key in ("plain_text", "text", "summary", "note"):
        value = _string(paragraph.get(key))
        if value.strip():
            return value
    return ""


def _paragraph_fingerprint(paragraph: Mapping[str, Any]) -> str:
    return _string(paragraph.get("paragraph_fingerprint") or paragraph.get("fingerprint")).strip()


def _paragraph_card(paragraph: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _string(paragraph.get("id")),
        "line_start": paragraph.get("line_start"),
        "line_end": paragraph.get("line_end"),
        "plain_text": _paragraph_text(paragraph),
        "summary": _string(paragraph.get("summary")),
        "idea_group_ids": [
            _string(item)
            for item in (paragraph.get("idea_group_ids") or [])
            if _string(item)
        ],
        "related_paragraph_ids": [
            _string(item)
            for item in (paragraph.get("related_paragraph_ids") or [])
            if _string(item)
        ],
        "paragraph_fingerprint": _paragraph_fingerprint(paragraph),
    }


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        normalized = _normalize_whitespace(value)
        return [normalized] if normalized else []
    if not isinstance(value, list):
        return []

    normalized_values: list[str] = []
    seen: set[str] = set()
    for entry in value:
        normalized = _normalize_whitespace(_string(entry))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)
    return normalized_values


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _string(value).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _normalize_selection_mode(value: Any, *, default: str) -> str:
    token = _string(value).strip().lower()
    if token in VALID_SELECTION_MODES:
        return token
    return default


def _statement_units_from_distillation(distillation: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(distillation, Mapping):
        return []

    for key in ("distilled_statements", "statements", "clarified_statements", "claims"):
        units = _normalize_string_list(distillation.get(key))
        if units:
            return units

    fallback = _string(
        distillation.get("distilled_text")
        or distillation.get("summary")
        or distillation.get("distillation")
    )
    if not fallback.strip():
        return []
    return _sentence_units(fallback) or [_normalize_whitespace(fallback)]


def _resolve_family_dir(repo_root: Path, family_token: str) -> str | None:
    raw_seed_root = repo_root / "obsidian" / "okay lets do this"
    for phase_family in raw_seed_root.glob(f"{family_token}*"):
        if phase_family.is_dir():
            return phase_family.relative_to(repo_root).as_posix()
    return None


def _seed_json_path_for_substrate(family_dir: str, *, substrate: str) -> str:
    return (
        raw_seed_json_path_for_family(family_dir)
        if substrate == "raw_seed"
        else agent_seed_json_path_for_family(family_dir)
    )


def _fallback_shards_payload(raw_seed_payload: Mapping[str, Any], *, substrate: str) -> dict[str, Any]:
    paragraphs = [
        dict(paragraph)
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    ]
    shards: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        fingerprint = _string(paragraph.get("paragraph_fingerprint") or paragraph.get("fingerprint") or paragraph.get("id"))
        if not fingerprint:
            continue
        shard_id = fingerprint if fingerprint.startswith("sh_") else f"sh_{fingerprint}"
        shards.append(
            {
                "shard_id": shard_id,
                "parent_paragraph_id": _string(paragraph.get("id")),
                "paragraph_fingerprint": fingerprint,
                "source_substrate": _string(paragraph.get("source_substrate")) or substrate,
                "authored_by": _string(paragraph.get("authored_by")) or ("operator" if substrate == "raw_seed" else "agent_collective"),
                "idea_group_ids": [
                    _string(item)
                    for item in (paragraph.get("idea_group_ids") or [])
                    if _string(item)
                ],
                "sibling_shard_ids": [],
                "dedication_scores": {},
                "dedication_max": 0.0,
                "status": "open",
            }
        )
    return {
        "kind": "raw_seed_shards",
        "schema_version": "raw_seed_shards_v1",
        "generated_at": _utc_now(),
        "family_id": _string(raw_seed_payload.get("family_id")),
        "family_number": _string(raw_seed_payload.get("family_number")),
        "source": {
            "registry_updated_at": _string(raw_seed_payload.get("updated_at")),
            "source_substrate": substrate,
        },
        "counts": {
            "total_paragraphs": len(paragraphs),
            "total_shards": len(shards),
            "total_idea_groups": 0,
        },
        "shards": shards,
    }


def _seed_shards_payload_for_substrate(
    *,
    repo_root: Path,
    family_dir: str,
    raw_seed_payload: Mapping[str, Any],
    substrate: str,
) -> dict[str, Any]:
    if substrate == "raw_seed":
        return _load_json(repo_root / raw_seed_shards_path_for_family(family_dir)) or {"shards": []}
    built = build_raw_seed_shards(raw_seed_payload)
    if built.get("shards"):
        return built
    return _fallback_shards_payload(raw_seed_payload, substrate=substrate)


def _default_distillations_payload(
    *,
    family_token: str,
    family_dir: str,
    raw_seed_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "raw_seed_distillations",
        "schema_version": RAW_SEED_DISTILLATIONS_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "family_id": _string(raw_seed_payload.get("family_id")) or family_token,
        "family_number": _string(raw_seed_payload.get("family_number")) or family_token,
        "family_title": _string(raw_seed_payload.get("family_title")),
        "family_dir": family_dir,
        "source_paths": {
            "raw_seed_json_path": raw_seed_json_path_for_family(family_dir),
            "extracted_shards_path": family_extracted_shards_path(family_dir),
        },
        "batches": [],
        "distillations": [],
        "stats": {
            "distillation_count": 0,
            "paragraph_count": 0,
        },
    }


def _default_atomization_ledger_payload(
    *,
    family_token: str,
    family_dir: str,
    raw_seed_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "raw_seed_atomization_ledger",
        "schema_version": RAW_SEED_ATOMIZATION_LEDGER_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "family_id": _string(raw_seed_payload.get("family_id")) or family_token,
        "family_number": _string(raw_seed_payload.get("family_number")) or family_token,
        "family_title": _string(raw_seed_payload.get("family_title")),
        "family_dir": family_dir,
        "source_paths": {
            "raw_seed_json_path": raw_seed_json_path_for_family(family_dir),
            "raw_seed_shards_path": raw_seed_shards_path_for_family(family_dir),
            "extracted_shards_path": family_extracted_shards_path(family_dir),
        },
        "counts": {
            "success": 0,
            "retryable": 0,
            "failed": 0,
            "pending": 0,
            "remaining_pending_paragraphs": 0,
            "total_paragraphs": 0,
        },
        "paragraphs": {},
    }


def _distillation_input_items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("distillations", "items", "entries", "paragraphs"):
        value = payload.get(key)
        if isinstance(value, list):
            return [entry for entry in value if isinstance(entry, Mapping)]
    return []


def _merge_rows_by_id(
    existing: Iterable[Mapping[str, Any]],
    new: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in list(existing) + list(new):
        record = dict(row)
        row_id = _string(record.get("id"))
        if not row_id or row_id in seen:
            continue
        seen.add(row_id)
        merged.append(record)
    return merged


def _latest_distillations_by_paragraph(
    payload: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    distillations = payload.get("distillations") if isinstance(payload, Mapping) else []
    rows = [row for row in distillations or [] if isinstance(row, Mapping)]
    rows.sort(
        key=lambda row: (
            _string(row.get("ingested_at")),
            _string(row.get("id")),
        )
    )
    for row in rows:
        paragraph_id = _string(row.get("paragraph_id"))
        if not paragraph_id:
            continue
        latest[paragraph_id] = dict(row)
    return latest


def _paragraph_index(raw_seed_payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _string(paragraph.get("id")): dict(paragraph)
        for paragraph in raw_seed_payload.get("paragraphs") or []
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    }


def _replaceable_atomization_source(source: Any) -> bool:
    token = _string(source).strip()
    if not token:
        return True
    if token in {ATOMIZATION_SOURCE, ATOMIZATION_BRIDGE_SOURCE, DISTILLATION_SOURCE}:
        return True
    return token.startswith("raw_seed_distillation_")


def _bin_rows(raw_seed_shards_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(shard)
        for shard in raw_seed_shards_payload.get("shards") or []
        if isinstance(shard, Mapping) and _string(shard.get("shard_id"))
    ]


def _bins_by_id(bin_rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        _string(bin_row.get("shard_id")): dict(bin_row)
        for bin_row in bin_rows
        if _string(bin_row.get("shard_id"))
    }


def _bins_by_parent_paragraph(bin_rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        _string(bin_row.get("parent_paragraph_id")): dict(bin_row)
        for bin_row in bin_rows
        if _string(bin_row.get("parent_paragraph_id"))
    }


def _source_bin_id_for_shard(
    shard: Mapping[str, Any],
    *,
    bins_by_parent: Mapping[str, Mapping[str, Any]],
) -> str:
    source_bin_id = _string(shard.get("source_bin_id"))
    if source_bin_id:
        return source_bin_id
    parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
    if not parent_paragraph_id:
        return ""
    bin_row = bins_by_parent.get(parent_paragraph_id)
    return _string(bin_row.get("shard_id")) if isinstance(bin_row, Mapping) else ""


def _default_authored_by_for_substrate(substrate: str) -> str:
    return "operator" if _string(substrate) == "raw_seed" else "agent_collective"


def _atomized_members_by_bin(
    extracted_shards: Iterable[Mapping[str, Any]],
    *,
    bins_by_parent: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    members: dict[str, list[dict[str, Any]]] = {}
    for shard in extracted_shards:
        if not isinstance(shard, Mapping):
            continue
        bin_id = _source_bin_id_for_shard(shard, bins_by_parent=bins_by_parent)
        if not bin_id:
            continue
        members.setdefault(bin_id, []).append(dict(shard))
    return members


def _bin_line_marker(
    bin_row: Mapping[str, Any],
    *,
    paragraph_index: Mapping[str, Mapping[str, Any]],
    prefer: str,
) -> int:
    paragraph = paragraph_index.get(_string(bin_row.get("parent_paragraph_id"))) or {}
    if prefer == "start":
        return int(paragraph.get("line_start") or paragraph.get("line_end") or 0)
    return int(paragraph.get("line_end") or paragraph.get("line_start") or 0)


def _ordered_bins(
    bin_rows: list[dict[str, Any]],
    *,
    paragraph_index: Mapping[str, Mapping[str, Any]],
    selection_mode: str,
) -> list[dict[str, Any]]:
    mode = _normalize_selection_mode(selection_mode, default=DEFAULT_ATOMIZE_SELECTION_MODE)
    if mode == SELECTION_MODE_OLDEST_FIRST:
        return sorted(
            bin_rows,
            key=lambda bin_row: (
                _bin_line_marker(bin_row, paragraph_index=paragraph_index, prefer="start"),
                _string(bin_row.get("parent_paragraph_id")),
                _string(bin_row.get("shard_id")),
            ),
        )
    if mode == SELECTION_MODE_MIXED:
        freshest = sorted(
            bin_rows,
            key=lambda bin_row: (
                -_bin_line_marker(bin_row, paragraph_index=paragraph_index, prefer="end"),
                _string(bin_row.get("parent_paragraph_id")),
                _string(bin_row.get("shard_id")),
            ),
        )
        oldest = sorted(
            bin_rows,
            key=lambda bin_row: (
                _bin_line_marker(bin_row, paragraph_index=paragraph_index, prefer="start"),
                _string(bin_row.get("parent_paragraph_id")),
                _string(bin_row.get("shard_id")),
            ),
        )
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for rows in zip(freshest, oldest):
            for bin_row in rows:
                bin_id = _string(bin_row.get("shard_id"))
                if not bin_id or bin_id in seen:
                    continue
                seen.add(bin_id)
                merged.append(bin_row)
        for bin_row in freshest:
            bin_id = _string(bin_row.get("shard_id"))
            if not bin_id or bin_id in seen:
                continue
            seen.add(bin_id)
            merged.append(bin_row)
        return merged
    return sorted(
        bin_rows,
        key=lambda bin_row: (
            -_bin_line_marker(bin_row, paragraph_index=paragraph_index, prefer="end"),
            _string(bin_row.get("parent_paragraph_id")),
            _string(bin_row.get("shard_id")),
        ),
    )


def _select_bin_rows(
    *,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    extracted_shards: list[Mapping[str, Any]],
    atomization_ledger_payload: Mapping[str, Any] | None = None,
    cohort_size: int,
    selection_mode: str,
    paragraph_id: str | None = None,
    require_pending_routing: bool = False,
) -> list[dict[str, Any]]:
    paragraph_index = _paragraph_index(raw_seed_payload)
    bin_rows = _bin_rows(raw_seed_shards_payload)
    bins_by_parent = _bins_by_parent_paragraph(bin_rows)
    atomized_by_bin = _atomized_members_by_bin(extracted_shards, bins_by_parent=bins_by_parent)
    paragraph_rows = (
        atomization_ledger_payload.get("paragraphs")
        if isinstance(atomization_ledger_payload, Mapping)
        and isinstance(atomization_ledger_payload.get("paragraphs"), Mapping)
        else {}
    )

    if paragraph_id:
        explicit = bins_by_parent.get(_string(paragraph_id))
        return [dict(explicit)] if isinstance(explicit, Mapping) else []

    candidates: list[dict[str, Any]] = []
    for bin_row in bin_rows:
        parent_paragraph_id = _string(bin_row.get("parent_paragraph_id"))
        if not parent_paragraph_id or parent_paragraph_id not in paragraph_index:
            continue
        member_atoms = atomized_by_bin.get(_string(bin_row.get("shard_id")), [])
        paragraph_status = _string(
            (paragraph_rows.get(parent_paragraph_id) or {}).get("status")
        ).strip().lower()
        if require_pending_routing:
            pending_members = [
                member
                for member in member_atoms
                if (_string(member.get("routing_state")) or "pending") == "pending"
            ]
            if not pending_members:
                continue
        elif paragraph_status == "success":
            continue
        candidates.append(dict(bin_row))

    ordered = _ordered_bins(
        candidates,
        paragraph_index=paragraph_index,
        selection_mode=selection_mode,
    )
    return ordered[: max(1, int(cohort_size))]


def _relative_selection_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _pending_members_for_bin(
    bin_id: str,
    *,
    atomized_by_bin: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    return [
        dict(member)
        for member in atomized_by_bin.get(bin_id, [])
        if (_string(member.get("routing_state")) or "pending") == "pending"
    ]


def _collapse_shard_rows_to_pending_bins(
    shard_rows: list[Mapping[str, Any]],
    *,
    bins_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_parent: Mapping[str, Mapping[str, Any]],
    atomized_by_bin: Mapping[str, list[dict[str, Any]]],
    max_bins: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected_bins: list[dict[str, Any]] = []
    seen_bin_ids: set[str] = set()
    for shard in shard_rows:
        bin_id = _source_bin_id_for_shard(shard, bins_by_parent=bins_by_parent)
        if not bin_id or bin_id in seen_bin_ids:
            continue
        bin_row = bins_by_id.get(bin_id)
        if not isinstance(bin_row, Mapping):
            continue
        pending_members = _pending_members_for_bin(bin_id, atomized_by_bin=atomized_by_bin)
        if not pending_members:
            continue
        seen_bin_ids.add(bin_id)
        selected_bins.append(dict(bin_row))
        if max_bins > 0 and len(selected_bins) >= max_bins:
            break

    selected_members = [
        member
        for bin_row in selected_bins
        for member in _pending_members_for_bin(
            _string(bin_row.get("shard_id")),
            atomized_by_bin=atomized_by_bin,
        )
    ]
    return selected_bins, selected_members


def _route_selection_context(
    *,
    selection_kind: str,
    selected_bins: list[Mapping[str, Any]],
    selected_members: list[Mapping[str, Any]],
    packet_path: str | None = None,
    group_id: str | None = None,
    query: str | None = None,
    related_limit: int | None = None,
    review_plane_summary: list[Mapping[str, Any]] | None = None,
    next_action_graph: Mapping[str, Any] | None = None,
    shard_synthesis: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = {
        "selection_kind": selection_kind,
        "packet_path": packet_path or None,
        "group_id": group_id or None,
        "query": query or None,
        "related_limit": related_limit,
        "selected_bin_ids": _dedupe_strings(
            [_string(bin_row.get("shard_id")) for bin_row in selected_bins]
        ),
        "selected_shard_ids": _dedupe_strings(
            [_string(member.get("id")) for member in selected_members]
        ),
    }
    review_planes = [
        dict(row)
        for row in review_plane_summary or []
        if isinstance(row, Mapping)
    ]
    if review_planes:
        context["review_plane_summary"] = review_planes
    if isinstance(next_action_graph, Mapping) and next_action_graph:
        context["next_action_graph"] = dict(next_action_graph)
    if isinstance(shard_synthesis, Mapping) and shard_synthesis:
        context["shard_synthesis"] = dict(shard_synthesis)
    return context


def _route_review_plane_metadata(
    index: Any,
    shard_rows: list[dict[str, Any]],
    *,
    selector: Mapping[str, Any],
    query: str = "",
) -> dict[str, Any]:
    review_plane_summary = index.review_plane_summary(shard_rows)
    group_summaries = index.group_summaries(shard_rows)
    next_action_graph = index.next_action_graph(
        query=query,
        shards=shard_rows,
        group_summaries=group_summaries,
        review_plane_summary=review_plane_summary,
        selector=dict(selector),
    )
    return {
        "review_plane_summary": review_plane_summary,
        "next_action_graph": next_action_graph,
        "shard_synthesis": index.shard_synthesis(
            query=query,
            shards=shard_rows,
            group_summaries=group_summaries,
            review_plane_summary=review_plane_summary,
            next_action_graph=next_action_graph,
            selector=dict(selector),
        ),
    }


def _action_commands(action: Mapping[str, Any]) -> list[str]:
    commands: list[str] = []
    raw_commands = action.get("commands")
    if isinstance(raw_commands, list):
        commands.extend(_string(command).strip() for command in raw_commands)
    raw_command = _string(action.get("command")).strip()
    if raw_command:
        commands.append(raw_command)
    return _dedupe_strings(commands)


def _review_plane_specs() -> dict[str, dict[str, str]]:
    return {
        "paper_module": {
            "target_plane": "paper_module",
            "review_question": "Which verified subsystem fact should be refreshed or authored as a paper module?",
            "output_contract": "document present-tense system facts only",
        },
        "principle": {
            "target_plane": "principle",
            "review_question": "Which independent general rule, if any, survives outside this specific system surface?",
            "output_contract": "route through principle curation; do not hand-author doctrine JSON",
        },
        "skill": {
            "target_plane": "skill",
            "review_question": "Which repeatable procedure should become easier for the next agent to execute?",
            "output_contract": "update the named move or routing instruction, not a one-off note",
        },
        "standard": {
            "target_plane": "standard",
            "review_question": "Which schema or contract invariant should be enforced?",
            "output_contract": "route to a standard or validator-facing contract",
        },
        "annex_pattern": {
            "target_plane": "annex_pattern",
            "review_question": "Which external architectural pattern should be translated with provenance?",
            "output_contract": "transfer patterns only; do not import substrate",
        },
        "raw_evidence": {
            "target_plane": "raw_evidence",
            "review_question": "Which paragraph or voice anchor should remain as evidence before curation?",
            "output_contract": "preserve `par_*` provenance and avoid doctrine lift until evidence is bounded",
        },
    }


def _review_plane_work_queue(selection_context: Mapping[str, Any]) -> dict[str, Any]:
    plane_specs = _review_plane_specs()
    plane_rows = [
        dict(row)
        for row in selection_context.get("review_plane_summary") or []
        if isinstance(row, Mapping) and _string(row.get("plane")).strip()
    ]
    actions_by_plane: dict[str, dict[str, Any]] = {}
    next_action_graph = selection_context.get("next_action_graph")
    if isinstance(next_action_graph, Mapping):
        for action in next_action_graph.get("actions") or []:
            if not isinstance(action, Mapping):
                continue
            plane = _string(action.get("plane")).strip()
            if plane and plane not in actions_by_plane:
                actions_by_plane[plane] = dict(action)

    items: list[dict[str, Any]] = []
    for index, row in enumerate(plane_rows, start=1):
        plane = _string(row.get("plane")).strip()
        spec = plane_specs.get(plane, {})
        action = actions_by_plane.get(plane, {})
        items.append(
            {
                "plane": plane,
                "rank": index,
                "score": int(row.get("score") or 0),
                "signals": _normalize_string_list(row.get("signals"))[:8],
                "description": _string(row.get("description")).strip(),
                "target_plane": _string(spec.get("target_plane")).strip() or plane,
                "review_question": _string(spec.get("review_question")).strip(),
                "output_contract": _string(spec.get("output_contract")).strip(),
                "action_id": _string(action.get("action_id")).strip() or None,
                "action_kind": _string(action.get("kind")).strip() or None,
                "next_commands": _action_commands(action)[:5],
            }
        )

    return {
        "schema_version": "raw_seed_review_plane_work_queue_v1",
        "status": "needs_plane_review" if items else "no_plane_hints",
        "selection_kind": _string(selection_context.get("selection_kind")).strip() or "unknown",
        "selected_bin_ids": _normalize_string_list(selection_context.get("selected_bin_ids")),
        "selected_shard_ids": _normalize_string_list(selection_context.get("selected_shard_ids")),
        "items": items,
        "guardrails": [
            "Plane hints choose the next review surface; they are not apply decisions.",
            "Paper modules describe verified system facts; principles carry independent general rules.",
            "Skills and standards carry repeatable procedure and schema contracts respectively.",
            "Annex patterns require pattern transfer with provenance, never substrate import.",
        ],
    }


def _count_rows(counts: Mapping[str, int], *, label: str) -> list[dict[str, Any]]:
    return [
        {label: key, "count": int(count)}
        for key, count in sorted(counts.items(), key=lambda item: (-int(item[1]), item[0]))
    ]


def _member_primary_review_plane(member: Mapping[str, Any]) -> str:
    plane = _string(member.get("primary_review_plane")).strip()
    if plane:
        return plane
    hints = member.get("review_plane_hints")
    if isinstance(hints, list):
        for hint in hints:
            if not isinstance(hint, Mapping):
                continue
            plane = _string(hint.get("plane")).strip()
            if plane:
                return plane
    return "raw_evidence"


def _proposal_plane_bins(
    proposals: list[Mapping[str, Any]],
    *,
    review_plane_work_queue: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    specs = _review_plane_specs()
    work_items_by_plane = {
        _string(item.get("plane")).strip(): dict(item)
        for item in (review_plane_work_queue or {}).get("items") or []
        if isinstance(item, Mapping) and _string(item.get("plane")).strip()
    }
    bins: dict[str, dict[str, Any]] = {}
    for envelope in proposals:
        if not isinstance(envelope, Mapping):
            continue
        source_bin_id = _string(envelope.get("source_bin_id")).strip()
        envelope_id = _string(envelope.get("id")).strip()
        for member in envelope.get("member_proposals") or []:
            if not isinstance(member, Mapping) or not _proposal_is_pending_review(member):
                continue
            plane = _member_primary_review_plane(member)
            entry = bins.setdefault(
                plane,
                {
                    "plane": plane,
                    "member_count": 0,
                    "source_bin_ids": set(),
                    "proposal_ids": [],
                    "member_ids": [],
                    "shard_ids": [],
                    "decision_counts": {},
                    "synthesis_role_counts": {},
                    "representative_parent_paragraphs": set(),
                },
            )
            entry["member_count"] += 1
            if source_bin_id:
                entry["source_bin_ids"].add(source_bin_id)
            if envelope_id:
                entry["proposal_ids"].append(envelope_id)
            member_id = _string(member.get("id")).strip()
            if member_id:
                entry["member_ids"].append(member_id)
            shard_id = _string(member.get("shard_id")).strip()
            if shard_id:
                entry["shard_ids"].append(shard_id)
            parent_id = _string(member.get("parent_paragraph_id")).strip()
            if parent_id:
                entry["representative_parent_paragraphs"].add(parent_id)
            decision = _string(member.get("decision")).strip() or "unknown"
            entry["decision_counts"][decision] = int(entry["decision_counts"].get(decision, 0)) + 1
            role = _string(member.get("synthesis_role")).strip() or "unknown"
            entry["synthesis_role_counts"][role] = int(entry["synthesis_role_counts"].get(role, 0)) + 1

    items: list[dict[str, Any]] = []
    for plane, entry in bins.items():
        work_item = work_items_by_plane.get(plane, {})
        spec = specs.get(plane, {})
        items.append(
            {
                "plane": plane,
                "target_plane": _string(work_item.get("target_plane")).strip()
                or _string(spec.get("target_plane")).strip()
                or plane,
                "member_count": int(entry.get("member_count") or 0),
                "bin_count": len(entry.get("source_bin_ids") or set()),
                "source_bin_ids": sorted(entry.get("source_bin_ids") or [])[:20],
                "proposal_ids": _dedupe_strings(entry.get("proposal_ids") or [])[:20],
                "member_ids": _dedupe_strings(entry.get("member_ids") or [])[:20],
                "shard_ids": _dedupe_strings(entry.get("shard_ids") or [])[:30],
                "decision_counts": _count_rows(entry.get("decision_counts") or {}, label="decision"),
                "synthesis_role_counts": _count_rows(
                    entry.get("synthesis_role_counts") or {},
                    label="synthesis_role",
                ),
                "representative_parent_paragraphs": sorted(
                    entry.get("representative_parent_paragraphs") or []
                )[:10],
                "review_question": _string(work_item.get("review_question")).strip()
                or _string(spec.get("review_question")).strip(),
                "output_contract": _string(work_item.get("output_contract")).strip()
                or _string(spec.get("output_contract")).strip(),
                "next_commands": _normalize_string_list(work_item.get("next_commands"))[:5],
            }
        )
    items.sort(
        key=lambda item: (
            int((work_items_by_plane.get(_string(item.get("plane")).strip()) or {}).get("rank") or 999),
            -int(item.get("member_count") or 0),
            _string(item.get("plane")).strip(),
        )
    )
    for rank, item in enumerate(items, start=1):
        item["rank"] = rank
    return {
        "schema_version": "raw_seed_proposal_plane_bins_v1",
        "status": "has_plane_bins" if items else "no_pending_plane_bins",
        "plane_count": len(items),
        "pending_member_count": sum(int(item.get("member_count") or 0) for item in items),
        "items": items,
        "guardrails": [
            "Plane bins are review routing aids, not apply decisions.",
            "Mixed slices should be reviewed by plane before draining proposals into doctrine.",
            "Paper modules describe verified system facts; principles carry independent general rules.",
        ],
    }


def _resolve_route_review_selection(
    *,
    repo_root: Path,
    extracted_path: Path,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    extracted_shards: list[Mapping[str, Any]],
    requested_cohort_size: int,
    selection_mode: str,
    packet_path: str | Path | None = None,
    shards_group: str | None = None,
    shards_query: str | None = None,
    shards_related_limit: int = 20,
) -> dict[str, Any]:
    paragraph_level_shards = _bin_rows(raw_seed_shards_payload)
    bins_by_id = _bins_by_id(paragraph_level_shards)
    bins_by_parent = _bins_by_parent_paragraph(paragraph_level_shards)
    atomized_by_bin = _atomized_members_by_bin(extracted_shards, bins_by_parent=bins_by_parent)

    if not packet_path and not shards_group and not shards_query:
        selected_bins = _select_bin_rows(
            raw_seed_payload=raw_seed_payload,
            raw_seed_shards_payload=raw_seed_shards_payload,
            extracted_shards=extracted_shards,
            cohort_size=requested_cohort_size,
            selection_mode=selection_mode,
            require_pending_routing=True,
        )
        selected_members = [
            member
            for bin_row in selected_bins
            for member in _pending_members_for_bin(
                _string(bin_row.get("shard_id")),
                atomized_by_bin=atomized_by_bin,
            )
        ]
        return {
            "selected_bins": selected_bins,
            "selected_members": selected_members,
            "selection_context": _route_selection_context(
                selection_kind="selection_mode",
                selected_bins=selected_bins,
                selected_members=selected_members,
            ),
        }

    index = load_shards(explicit_path=extracted_path, repo_root=repo_root)
    if index is None:
        resolved_packet_path = None
        if packet_path:
            resolved_packet_path = Path(packet_path)
            if not resolved_packet_path.is_absolute():
                resolved_packet_path = repo_root / resolved_packet_path
        return {
            "selected_bins": [],
            "selected_members": [],
            "selection_context": _route_selection_context(
                selection_kind="packet"
                if packet_path
                else "group"
                if shards_group
                else "query",
                selected_bins=[],
                selected_members=[],
                packet_path=_relative_selection_path(resolved_packet_path, repo_root=repo_root)
                if resolved_packet_path is not None
                else None,
                group_id=_string(shards_group) or None,
                query=_string(shards_query) or None,
                related_limit=max(0, int(shards_related_limit or 0)) if shards_query else None,
            ),
        }

    selected_shard_rows: list[dict[str, Any]]
    selection_context: dict[str, Any]
    if packet_path:
        packet = load_shard_batch_packet(packet_path, repo_root=repo_root)
        selected_shard_rows = select_packet_shards(
            index,
            exact_shard_ids=list(packet.get("batch_shard_ids") or []),
        )
        selected_bins, selected_members = _collapse_shard_rows_to_pending_bins(
            selected_shard_rows,
            bins_by_id=bins_by_id,
            bins_by_parent=bins_by_parent,
            atomized_by_bin=atomized_by_bin,
            max_bins=0,
        )
        packet_selection = packet.get("selection") if isinstance(packet.get("selection"), Mapping) else {}
        packet_query = packet.get("query_summary") if isinstance(packet.get("query_summary"), Mapping) else {}
        selection_context = _route_selection_context(
            selection_kind="packet",
            selected_bins=selected_bins,
            selected_members=selected_members,
            packet_path=_string(packet.get("path_rel")),
            group_id=_string(packet_selection.get("group")) or None,
            query=_string(packet_query.get("query") or packet_selection.get("query")) or None,
            related_limit=(
                int(packet_query.get("related_limit"))
                if packet_query.get("related_limit") not in (None, "")
                else None
            ),
            review_plane_summary=packet.get("review_plane_summary")
            if isinstance(packet.get("review_plane_summary"), list)
            else None,
            next_action_graph=packet.get("next_action_graph")
            if isinstance(packet.get("next_action_graph"), Mapping)
            else None,
            shard_synthesis=packet.get("shard_synthesis")
            if isinstance(packet.get("shard_synthesis"), Mapping)
            else None,
        )
        return {
            "selected_bins": selected_bins,
            "selected_members": selected_members,
            "selection_context": selection_context,
        }

    if shards_group:
        selected_shard_rows = select_packet_shards(index, group=_string(shards_group))
        metadata = _route_review_plane_metadata(
            index,
            selected_shard_rows,
            selector={"group": _string(shards_group)},
        )
        selected_bins, selected_members = _collapse_shard_rows_to_pending_bins(
            selected_shard_rows,
            bins_by_id=bins_by_id,
            bins_by_parent=bins_by_parent,
            atomized_by_bin=atomized_by_bin,
            max_bins=max(1, int(requested_cohort_size)),
        )
        selection_context = _route_selection_context(
            selection_kind="group",
            selected_bins=selected_bins,
            selected_members=selected_members,
            group_id=_string(shards_group) or None,
            review_plane_summary=metadata["review_plane_summary"],
            next_action_graph=metadata["next_action_graph"],
            shard_synthesis=metadata["shard_synthesis"],
        )
        return {
            "selected_bins": selected_bins,
            "selected_members": selected_members,
            "selection_context": selection_context,
        }

    selected_shard_rows = select_packet_shards(index, query=_string(shards_query))
    metadata = _route_review_plane_metadata(
        index,
        selected_shard_rows,
        selector={"query": _string(shards_query)},
        query=_string(shards_query),
    )
    selected_bins, selected_members = _collapse_shard_rows_to_pending_bins(
        selected_shard_rows,
        bins_by_id=bins_by_id,
        bins_by_parent=bins_by_parent,
        atomized_by_bin=atomized_by_bin,
        max_bins=max(1, int(requested_cohort_size)),
    )
    selection_context = _route_selection_context(
        selection_kind="query",
        selected_bins=selected_bins,
        selected_members=selected_members,
        query=_string(shards_query) or None,
        related_limit=max(0, int(shards_related_limit or 0)),
        review_plane_summary=metadata["review_plane_summary"],
        next_action_graph=metadata["next_action_graph"],
        shard_synthesis=metadata["shard_synthesis"],
    )
    return {
        "selected_bins": selected_bins,
        "selected_members": selected_members,
        "selection_context": selection_context,
    }


def _pending_review_member_proposals(review_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    for proposal in review_payload.get("proposals") or []:
        if not isinstance(proposal, Mapping):
            continue
        member_proposals = proposal.get("member_proposals")
        if isinstance(member_proposals, list):
            for member in member_proposals:
                if isinstance(member, Mapping) and _proposal_is_pending_review(member):
                    members.append(dict(member))
            continue
        if _proposal_is_pending_review(proposal):
            members.append(dict(proposal))
    return members


def _member_parent_paragraph_id(
    proposal: Mapping[str, Any],
    *,
    shards_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_id: Mapping[str, Mapping[str, Any]],
) -> str:
    parent_paragraph_id = _string(proposal.get("parent_paragraph_id"))
    if parent_paragraph_id:
        return parent_paragraph_id
    shard = shards_by_id.get(_string(proposal.get("shard_id")))
    if isinstance(shard, Mapping):
        parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
        if parent_paragraph_id:
            return parent_paragraph_id
    source_bin_id = _string(proposal.get("source_bin_id"))
    if source_bin_id:
        bin_row = bins_by_id.get(source_bin_id)
        if isinstance(bin_row, Mapping):
            return _string(bin_row.get("parent_paragraph_id"))
    return ""


def _member_source_bin_id(
    proposal: Mapping[str, Any],
    *,
    shards_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_parent: Mapping[str, Mapping[str, Any]],
) -> str:
    source_bin_id = _string(proposal.get("source_bin_id"))
    if source_bin_id:
        return source_bin_id
    shard = shards_by_id.get(_string(proposal.get("shard_id")))
    if isinstance(shard, Mapping):
        source_bin_id = _source_bin_id_for_shard(shard, bins_by_parent=bins_by_parent)
        if source_bin_id:
            return source_bin_id
    parent_paragraph_id = _member_parent_paragraph_id(
        proposal,
        shards_by_id=shards_by_id,
        bins_by_id=bins_by_id,
    )
    if parent_paragraph_id:
        bin_row = bins_by_parent.get(parent_paragraph_id)
        if isinstance(bin_row, Mapping):
            return _string(bin_row.get("shard_id"))
    return ""


def _member_source_substrate(
    proposal: Mapping[str, Any],
    *,
    shards_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_parent: Mapping[str, Mapping[str, Any]],
) -> str:
    source_substrate = _string(proposal.get("source_substrate")).strip()
    if source_substrate:
        return source_substrate
    shard = shards_by_id.get(_string(proposal.get("shard_id")))
    if isinstance(shard, Mapping):
        source_substrate = _string(shard.get("source_substrate")).strip()
        if source_substrate:
            return source_substrate
    source_bin_id = _member_source_bin_id(
        proposal,
        shards_by_id=shards_by_id,
        bins_by_id=bins_by_id,
        bins_by_parent=bins_by_parent,
    )
    if source_bin_id:
        bin_row = bins_by_id.get(source_bin_id)
        if isinstance(bin_row, Mapping):
            source_substrate = _string(bin_row.get("source_substrate")).strip()
            if source_substrate:
                return source_substrate
    parent_paragraph_id = _member_parent_paragraph_id(
        proposal,
        shards_by_id=shards_by_id,
        bins_by_id=bins_by_id,
    )
    if parent_paragraph_id:
        bin_row = bins_by_parent.get(parent_paragraph_id)
        if isinstance(bin_row, Mapping):
            source_substrate = _string(bin_row.get("source_substrate")).strip()
            if source_substrate:
                return source_substrate
    return "raw_seed"


def _member_authored_by(
    proposal: Mapping[str, Any],
    *,
    shards_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_parent: Mapping[str, Mapping[str, Any]],
) -> str:
    authored_by = _string(proposal.get("authored_by")).strip()
    if authored_by:
        return authored_by
    shard = shards_by_id.get(_string(proposal.get("shard_id")))
    if isinstance(shard, Mapping):
        authored_by = _string(shard.get("authored_by")).strip()
        if authored_by:
            return authored_by
    source_bin_id = _member_source_bin_id(
        proposal,
        shards_by_id=shards_by_id,
        bins_by_id=bins_by_id,
        bins_by_parent=bins_by_parent,
    )
    if source_bin_id:
        bin_row = bins_by_id.get(source_bin_id)
        if isinstance(bin_row, Mapping):
            authored_by = _string(bin_row.get("authored_by")).strip()
            if authored_by:
                return authored_by
    parent_paragraph_id = _member_parent_paragraph_id(
        proposal,
        shards_by_id=shards_by_id,
        bins_by_id=bins_by_id,
    )
    if parent_paragraph_id:
        bin_row = bins_by_parent.get(parent_paragraph_id)
        if isinstance(bin_row, Mapping):
            authored_by = _string(bin_row.get("authored_by")).strip()
            if authored_by:
                return authored_by
    source_substrate = _member_source_substrate(
        proposal,
        shards_by_id=shards_by_id,
        bins_by_id=bins_by_id,
        bins_by_parent=bins_by_parent,
    )
    return _default_authored_by_for_substrate(source_substrate)


def _review_envelope_key(
    *,
    source_bin_id: str,
    parent_paragraph_id: str,
    proposal_id: str,
    shard_id: str,
) -> str:
    if source_bin_id:
        return f"bin:{source_bin_id}"
    if parent_paragraph_id:
        return f"parent:{parent_paragraph_id}"
    if proposal_id:
        return f"proposal:{proposal_id}"
    if shard_id:
        return f"shard:{shard_id}"
    return "proposal:orphan"


def _seed_review_envelope(
    *,
    source_bin_id: str,
    parent_paragraph_id: str,
    proposal_id: str,
    shard_id: str,
    bins_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_parent: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    bin_row = bins_by_id.get(source_bin_id) or bins_by_parent.get(parent_paragraph_id)
    if isinstance(bin_row, Mapping):
        envelope = _review_envelope_for_bin(
            bin_row=bin_row,
            member_proposals=[],
        )
    else:
        seed = source_bin_id or parent_paragraph_id or proposal_id or shard_id or "raw_seed_routing_review"
        envelope = {
            "id": f"rr_bin_{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:12]}",
            "source_bin_id": source_bin_id,
            "parent_paragraph_id": parent_paragraph_id or None,
            "source_substrate": "raw_seed",
            "authored_by": "operator",
            "sibling_bin_ids": [],
            "member_atom_ids": [],
            "member_count": 0,
            "status": "pending_review",
            "member_proposals": [],
        }
    if source_bin_id and not _string(envelope.get("source_bin_id")):
        envelope["source_bin_id"] = source_bin_id
    if parent_paragraph_id and not _string(envelope.get("parent_paragraph_id")):
        envelope["parent_paragraph_id"] = parent_paragraph_id
    return envelope


def _canonicalize_review_envelope(
    envelope: Mapping[str, Any],
    *,
    source_bin_id: str,
    parent_paragraph_id: str,
    bins_by_id: Mapping[str, Mapping[str, Any]],
    bins_by_parent: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = dict(envelope)
    first_member = next(
        (
            member
            for member in normalized.get("member_proposals") or []
            if isinstance(member, Mapping)
        ),
        None,
    )
    if source_bin_id:
        normalized["source_bin_id"] = source_bin_id
    if not parent_paragraph_id and source_bin_id:
        bin_row = bins_by_id.get(source_bin_id)
        if isinstance(bin_row, Mapping):
            parent_paragraph_id = _string(bin_row.get("parent_paragraph_id"))
    if parent_paragraph_id:
        normalized["parent_paragraph_id"] = parent_paragraph_id
    if not isinstance(normalized.get("sibling_bin_ids"), list):
        normalized["sibling_bin_ids"] = []
    if not normalized["sibling_bin_ids"] and source_bin_id:
        bin_row = bins_by_id.get(source_bin_id) or bins_by_parent.get(parent_paragraph_id)
        if isinstance(bin_row, Mapping):
            normalized["sibling_bin_ids"] = [
                _string(item)
                for item in (bin_row.get("sibling_shard_ids") or [])
                if _string(item)
            ]
    if not _string(normalized.get("id")):
        seed = (
            source_bin_id
            or parent_paragraph_id
            or _string(normalized.get("id"))
            or _string(normalized.get("shard_id"))
            or "raw_seed_routing_review"
        )
        normalized["id"] = f"rr_bin_{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:12]}"
    if not _string(normalized.get("source_substrate")):
        normalized["source_substrate"] = _string((first_member or {}).get("source_substrate")) or "raw_seed"
    if not _string(normalized.get("authored_by")):
        normalized["authored_by"] = _string((first_member or {}).get("authored_by")) or _default_authored_by_for_substrate(
            _string(normalized.get("source_substrate")) or "raw_seed"
        )
    return normalized


def _dedupe_review_members(member_proposals: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for proposal in member_proposals:
        if not isinstance(proposal, Mapping):
            continue
        key = (
            _string(proposal.get("id"))
            or _string(proposal.get("shard_id"))
            or _string(proposal.get("parent_paragraph_id"))
        )
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(dict(proposal))
    return deduped


def _enrich_review_member_classification(
    member: Mapping[str, Any],
    *,
    shards_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = dict(member)
    shard_id = _string(normalized.get("shard_id")).strip()
    source = dict(shards_by_id.get(shard_id) or normalized)
    enriched_source = enrich_shard_routing_metadata(source)
    if not _string(normalized.get("primary_review_plane")).strip():
        normalized["primary_review_plane"] = _string(enriched_source.get("primary_review_plane")).strip()
    if not normalized.get("primary_review_plane_score"):
        normalized["primary_review_plane_score"] = int(enriched_source.get("primary_review_plane_score") or 0)
    if not _string(normalized.get("synthesis_role")).strip():
        normalized["synthesis_role"] = _string(enriched_source.get("synthesis_role")).strip()
    if not isinstance(normalized.get("review_plane_hints"), list) or not normalized.get("review_plane_hints"):
        normalized["review_plane_hints"] = list(enriched_source.get("review_plane_hints") or [])[:4]
    return normalized


def _refresh_normalized_review_envelope_statuses(proposals: list[dict[str, Any]]) -> None:
    for proposal in proposals:
        member_proposals = proposal.get("member_proposals")
        if not isinstance(member_proposals, list):
            continue
        proposal["member_count"] = len(
            [member for member in member_proposals if isinstance(member, Mapping)]
        )
        proposal["member_atom_ids"] = [
            _string(member.get("shard_id"))
            for member in member_proposals
            if isinstance(member, Mapping) and _string(member.get("shard_id"))
        ]
        pending = any(
            isinstance(member, Mapping)
            and _string(member.get("status")) in {"", "pending_review"}
            for member in member_proposals
        )
        proposal["status"] = "pending_review" if pending else "completed"


def _normalized_review_payload_stats(
    proposals: list[dict[str, Any]],
    shards: list[dict[str, Any]],
) -> dict[str, Any]:
    pending_members = [
        member
        for proposal in proposals
        for member in (proposal.get("member_proposals") or [])
        if isinstance(member, Mapping)
        and _string(member.get("status")) in {"", "pending_review"}
    ]
    pending_bins = [
        proposal
        for proposal in proposals
        if any(
            isinstance(member, Mapping)
            and _string(member.get("status")) in {"", "pending_review"}
            for member in proposal.get("member_proposals") or []
        )
    ]
    source_substrate_counts: dict[str, int] = {}
    authored_by_counts: dict[str, int] = {}
    for proposal in proposals:
        if not isinstance(proposal, Mapping):
            continue
        source_substrate = _string(proposal.get("source_substrate")) or "raw_seed"
        authored_by = _string(proposal.get("authored_by")) or _default_authored_by_for_substrate(
            source_substrate
        )
        source_substrate_counts[source_substrate] = source_substrate_counts.get(source_substrate, 0) + 1
        authored_by_counts[authored_by] = authored_by_counts.get(authored_by, 0) + 1
    return {
        "pending_review": len(pending_members),
        "pending_review_bins": len(pending_bins),
        "route_to_existing": sum(
            1 for proposal in pending_members if _string(proposal.get("decision")) == "route_to_existing"
        ),
        "propose_new": sum(
            1 for proposal in pending_members if _string(proposal.get("decision")) == "propose_new"
        ),
        "surface_to_codex": sum(
            1 for proposal in pending_members if _string(proposal.get("decision")) == "surface_to_codex"
        ),
        "remaining_pending_shards": sum(
            1 for shard in shards if (_string(shard.get("routing_state")) or "pending") == "pending"
        ),
        "source_substrate_counts": source_substrate_counts,
        "authored_by_counts": authored_by_counts,
    }


def normalize_routing_review_payload(
    review_payload: Mapping[str, Any] | None,
    *,
    raw_seed_shards_payload: Mapping[str, Any] | None = None,
    extracted_shards_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = dict(review_payload) if isinstance(review_payload, Mapping) else {"proposals": []}
    raw_seed_shards_payload = raw_seed_shards_payload or {}
    extracted_shards_payload = extracted_shards_payload or {}
    bin_rows = _bin_rows(raw_seed_shards_payload)
    bins_by_id = _bins_by_id(bin_rows)
    bins_by_parent = _bins_by_parent_paragraph(bin_rows)
    extracted_shards = [
        dict(shard)
        for shard in extracted_shards_payload.get("shards") or []
        if isinstance(shard, Mapping)
    ]
    shards_by_id = {
        _string(shard.get("id")): dict(shard)
        for shard in extracted_shards
        if _string(shard.get("id"))
    }

    envelopes_by_key: dict[str, dict[str, Any]] = {}
    ordered_keys: list[str] = []
    for proposal in normalized.get("proposals") or []:
        if not isinstance(proposal, Mapping):
            continue
        member_proposals = proposal.get("member_proposals")
        if isinstance(member_proposals, list):
            normalized_members = []
            for member in member_proposals:
                if not isinstance(member, Mapping):
                    continue
                normalized_member = _enrich_review_member_classification(
                    member,
                    shards_by_id=shards_by_id,
                )
                member_parent_paragraph_id = _member_parent_paragraph_id(
                    normalized_member,
                    shards_by_id=shards_by_id,
                    bins_by_id=bins_by_id,
                )
                member_source_bin_id = _member_source_bin_id(
                    normalized_member,
                    shards_by_id=shards_by_id,
                    bins_by_id=bins_by_id,
                    bins_by_parent=bins_by_parent,
                )
                if member_source_bin_id:
                    normalized_member["source_bin_id"] = member_source_bin_id
                if member_parent_paragraph_id:
                    normalized_member["parent_paragraph_id"] = member_parent_paragraph_id
                normalized_member["source_substrate"] = _member_source_substrate(
                    normalized_member,
                    shards_by_id=shards_by_id,
                    bins_by_id=bins_by_id,
                    bins_by_parent=bins_by_parent,
                )
                normalized_member["authored_by"] = _member_authored_by(
                    normalized_member,
                    shards_by_id=shards_by_id,
                    bins_by_id=bins_by_id,
                    bins_by_parent=bins_by_parent,
                )
                normalized_members.append(normalized_member)

            source_bin_id = _string(proposal.get("source_bin_id"))
            if not source_bin_id:
                first_member = next(
                    (
                        member
                        for member in normalized_members
                        if _string(member.get("source_bin_id"))
                    ),
                    None,
                )
                if isinstance(first_member, Mapping):
                    source_bin_id = _string(first_member.get("source_bin_id"))
            parent_paragraph_id = _string(proposal.get("parent_paragraph_id"))
            if not parent_paragraph_id:
                first_member = next(
                    (
                        member
                        for member in normalized_members
                        if _string(member.get("parent_paragraph_id"))
                    ),
                    None,
                )
                if isinstance(first_member, Mapping):
                    parent_paragraph_id = _string(first_member.get("parent_paragraph_id"))
            key = _review_envelope_key(
                source_bin_id=source_bin_id,
                parent_paragraph_id=parent_paragraph_id,
                proposal_id=_string(proposal.get("id")),
                shard_id="",
            )
            envelope = envelopes_by_key.get(key)
            if envelope is None:
                envelope = dict(proposal)
                envelope["member_proposals"] = []
                envelopes_by_key[key] = envelope
                ordered_keys.append(key)
            envelope["member_proposals"].extend(normalized_members)
            envelopes_by_key[key] = _canonicalize_review_envelope(
                envelope,
                source_bin_id=source_bin_id,
                parent_paragraph_id=parent_paragraph_id,
                bins_by_id=bins_by_id,
                bins_by_parent=bins_by_parent,
            )
            continue

        normalized_member = _enrich_review_member_classification(
            proposal,
            shards_by_id=shards_by_id,
        )
        source_bin_id = _member_source_bin_id(
            normalized_member,
            shards_by_id=shards_by_id,
            bins_by_id=bins_by_id,
            bins_by_parent=bins_by_parent,
        )
        parent_paragraph_id = _member_parent_paragraph_id(
            normalized_member,
            shards_by_id=shards_by_id,
            bins_by_id=bins_by_id,
        )
        if source_bin_id:
            normalized_member["source_bin_id"] = source_bin_id
        if parent_paragraph_id:
            normalized_member["parent_paragraph_id"] = parent_paragraph_id
        normalized_member["source_substrate"] = _member_source_substrate(
            normalized_member,
            shards_by_id=shards_by_id,
            bins_by_id=bins_by_id,
            bins_by_parent=bins_by_parent,
        )
        normalized_member["authored_by"] = _member_authored_by(
            normalized_member,
            shards_by_id=shards_by_id,
            bins_by_id=bins_by_id,
            bins_by_parent=bins_by_parent,
        )
        key = _review_envelope_key(
            source_bin_id=source_bin_id,
            parent_paragraph_id=parent_paragraph_id,
            proposal_id=_string(normalized_member.get("id")),
            shard_id=_string(normalized_member.get("shard_id")),
        )
        envelope = envelopes_by_key.get(key)
        if envelope is None:
            envelope = _seed_review_envelope(
                source_bin_id=source_bin_id,
                parent_paragraph_id=parent_paragraph_id,
                proposal_id=_string(normalized_member.get("id")),
                shard_id=_string(normalized_member.get("shard_id")),
                bins_by_id=bins_by_id,
                bins_by_parent=bins_by_parent,
            )
            envelopes_by_key[key] = envelope
            ordered_keys.append(key)
        envelope.setdefault("member_proposals", []).append(normalized_member)
        envelopes_by_key[key] = _canonicalize_review_envelope(
            envelope,
            source_bin_id=source_bin_id,
            parent_paragraph_id=parent_paragraph_id,
            bins_by_id=bins_by_id,
            bins_by_parent=bins_by_parent,
        )

    normalized_envelopes: list[dict[str, Any]] = []
    for key in ordered_keys:
        envelope = dict(envelopes_by_key[key])
        envelope["member_proposals"] = _dedupe_review_members(
            envelope.get("member_proposals") or []
        )
        normalized_envelopes.append(envelope)
    _refresh_normalized_review_envelope_statuses(normalized_envelopes)

    stats = dict(normalized.get("stats") or {})
    stats.update(_normalized_review_payload_stats(normalized_envelopes, extracted_shards))
    normalized["proposals"] = normalized_envelopes
    normalized["stats"] = stats
    normalized["proposal_plane_bins"] = _proposal_plane_bins(
        normalized_envelopes,
        review_plane_work_queue=normalized.get("review_plane_work_queue")
        if isinstance(normalized.get("review_plane_work_queue"), Mapping)
        else None,
    )
    if normalized_envelopes and not _string(normalized.get("schema_version")):
        normalized["schema_version"] = RAW_SEED_ROUTING_REVIEW_SCHEMA_VERSION
    return normalized


def _review_envelopes_by_bin(review_payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    envelopes: dict[str, dict[str, Any]] = {}
    for proposal in review_payload.get("proposals") or []:
        if not isinstance(proposal, Mapping):
            continue
        bin_id = _string(proposal.get("source_bin_id"))
        if not bin_id and isinstance(proposal.get("member_proposals"), list):
            first_member = next(
                (
                    member
                    for member in proposal.get("member_proposals") or []
                    if isinstance(member, Mapping) and _string(member.get("source_bin_id"))
                ),
                None,
            )
            if isinstance(first_member, Mapping):
                bin_id = _string(first_member.get("source_bin_id"))
        if not bin_id:
            continue
        envelopes[bin_id] = dict(proposal)
    return envelopes


def _fresh_pending_bin_ids(
    *,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    extracted_shards: list[Mapping[str, Any]],
    routing_review_payload: Mapping[str, Any] | None,
) -> list[str]:
    paragraph_level_shards = _bin_rows(raw_seed_shards_payload)
    paragraph_index = _paragraph_index(raw_seed_payload)
    bins_by_parent = _bins_by_parent_paragraph(paragraph_level_shards)
    members_by_bin = _atomized_members_by_bin(extracted_shards, bins_by_parent=bins_by_parent)
    pending_review_by_bin: dict[str, int] = {}
    if isinstance(routing_review_payload, Mapping):
        for proposal in _pending_review_member_proposals(routing_review_payload):
            bin_id = _string(proposal.get("source_bin_id"))
            if not bin_id:
                continue
            pending_review_by_bin[bin_id] = pending_review_by_bin.get(bin_id, 0) + 1

    frontier: list[str] = []
    ordered_bins = _ordered_bins(
        paragraph_level_shards,
        paragraph_index=paragraph_index,
        selection_mode=SELECTION_MODE_FRESH_FIRST,
    )
    for bin_row in ordered_bins:
        bin_id = _string(bin_row.get("shard_id"))
        if not bin_id:
            continue
        members = members_by_bin.get(bin_id, [])
        is_pending = (
            not members
            or any((_string(member.get("routing_state")) or "pending") == "pending" for member in members)
            or pending_review_by_bin.get(bin_id, 0) > 0
        )
        if is_pending:
            frontier.append(bin_id)
            continue
        if frontier:
            break
    return frontier


def _build_atomized_shards(
    paragraph: Mapping[str, Any],
    *,
    source_bin_id: str | None = None,
    distillation: Mapping[str, Any] | None = None,
    alchemy_forms: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    paragraph_id = _string(paragraph.get("id"))
    paragraph_text = _paragraph_text(paragraph)
    if not paragraph_id or not paragraph_text:
        return []

    distilled_units = _statement_units_from_distillation(distillation)
    use_distillation = bool(distilled_units)
    units = distilled_units or _sentence_units(paragraph_text) or [paragraph_text]
    anchor = _paragraph_anchor(paragraph)
    groups = [group for group in paragraph.get("idea_group_ids") or [] if isinstance(group, str) and group.strip()]
    line_start = paragraph.get("line_start")
    line_end = paragraph.get("line_end")
    fingerprint = _string(paragraph.get("paragraph_fingerprint") or paragraph.get("fingerprint"))
    notes = ["whitespace_normalized"]
    if use_distillation:
        notes.append("bridge_distilled_units")
    elif len(units) > 1:
        notes.append("sentence_or_clause_split")
    else:
        notes.append("single_unit_fallback")

    shards: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        segment_ordinal = _ordinal_label(index)
        clarified = _normalize_whitespace(unit)
        support_excerpt = _normalize_whitespace(unit) or clarified
        voice_anchor = support_excerpt or clarified
        shard_id = _stable_atom_id(
            paragraph_id,
            segment_ordinal,
            clarified,
            voice_anchor=voice_anchor,
            support_excerpt=support_excerpt,
        )
        shard = {
            "id": shard_id,
            "raw_seed_anchor": anchor,
            "clarified_statement": clarified,
            "status": "pending",
            "raw_paragraph_ids": [paragraph_id],
            "parent_paragraph_id": paragraph_id,
            "segment_ordinal": segment_ordinal,
            "support_excerpt": support_excerpt,
            "voice_anchor": voice_anchor,
            "coverage_state": "atomized_unreviewed",
            "routing_state": "pending",
            "routing_targets": [],
            "compression_notes": notes,
            "source_substrate": _string(paragraph.get("source_substrate")) or "raw_seed",
            "authored_by": _string(paragraph.get("authored_by")) or "operator",
            "idea_group_ids": groups,
            "relevant_files": [],
            "concept_ids": [],
            "intent_provenance": [],
            "atomization_source": ATOMIZATION_SOURCE,
            "source_line_span": {
                "line_start": line_start,
                "line_end": line_end,
            },
            "paragraph_fingerprint": fingerprint,
        }
        if _string(source_bin_id):
            shard["source_bin_id"] = _string(source_bin_id)
        if use_distillation:
            shard["distillation_id"] = _string(distillation.get("id"))
            shard["distillation_batch_id"] = _string(distillation.get("batch_id"))
            shard["distillation_provider"] = _string(distillation.get("provider"))
        alchemy_form_id = _infer_alchemy_form_id(shard, alchemy_forms=alchemy_forms)
        if alchemy_form_id:
            shard["alchemy_form_id"] = alchemy_form_id
        shards.append(shard)
    return shards


def _merge_shards(existing: Iterable[Mapping[str, Any]], new: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for shard in list(existing) + list(new):
        record = dict(shard)
        shard_id = _string(record.get("id"))
        if not shard_id or shard_id in seen:
            continue
        seen.add(shard_id)
        merged.append(record)
    return merged


def _existing_atomized_paragraph_ids(shards: Iterable[Mapping[str, Any]]) -> set[str]:
    seen: set[str] = set()
    for shard in shards:
        parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
        if parent_paragraph_id:
            seen.add(parent_paragraph_id)
    return seen


def _default_routing_review_payload(
    *,
    family_token: str,
    family_dir: str,
    raw_seed_payload: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    initial_wave_resolution = _resolve_routing_wave_width(
        repo_root=repo_root,
        provider=DEFAULT_PROVIDER,
        requested_wave_width="auto",
    )
    return {
        "kind": "raw_seed_routing_review",
        "schema_version": RAW_SEED_ROUTING_REVIEW_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "family_id": _string(raw_seed_payload.get("family_id")) or family_token,
        "family_number": _string(raw_seed_payload.get("family_number")) or family_token,
        "family_dir": family_dir,
        "dispatch_policy": {
            "provider": DEFAULT_PROVIDER,
            "cohort_size": DEFAULT_QUEUE_DEPTH,
            "wave_width_requested": "auto",
            "wave_width_effective": int(
                initial_wave_resolution.get("effective_wave_width") or DEFAULT_ACTIVE_WORKERS
            ),
            "provider_ceiling": int(
                initial_wave_resolution.get("provider_ceiling")
                or _safe_parallelism(repo_root, DEFAULT_PROVIDER)
            ),
            "provider_ceiling_source": "tools/meta/bridge/provider_capabilities.json",
            "queue_depth": DEFAULT_QUEUE_DEPTH,
            "requested_active_workers": DEFAULT_ACTIVE_WORKERS,
            "effective_active_workers": int(
                initial_wave_resolution.get("effective_wave_width") or DEFAULT_ACTIVE_WORKERS
            ),
            "safe_parallelism": int(
                initial_wave_resolution.get("provider_ceiling")
                or _safe_parallelism(repo_root, DEFAULT_PROVIDER)
            ),
            "safe_parallelism_source": "tools/meta/bridge/provider_capabilities.json",
        },
        "proposals": [],
        "stats": {
            "pending_review": 0,
            "pending_review_bins": 0,
        },
    }


def _prune_routing_review_payload_for_touched_paragraphs(
    *,
    review_payload: Mapping[str, Any],
    replaced_rows: Iterable[Mapping[str, Any]],
    replacement_rows: Iterable[Mapping[str, Any]],
    touched_paragraph_ids: set[str],
) -> tuple[dict[str, Any], int]:
    replaced_shard_ids = {
        _string(shard.get("id"))
        for shard in replaced_rows
        if _string(shard.get("id"))
    }
    touched_bin_ids = {
        _string(row.get("source_bin_id"))
        for row in replacement_rows
        if _string(row.get("source_bin_id"))
    }
    filtered_proposals: list[dict[str, Any]] = []
    for proposal in review_payload.get("proposals") or []:
        if not isinstance(proposal, Mapping):
            continue
        source_bin_id = _string(proposal.get("source_bin_id"))
        parent_paragraph_id = _string(proposal.get("parent_paragraph_id"))
        if source_bin_id in touched_bin_ids or parent_paragraph_id in touched_paragraph_ids:
            continue
        member_proposals = proposal.get("member_proposals")
        if isinstance(member_proposals, list):
            kept_members = [
                dict(member)
                for member in member_proposals
                if isinstance(member, Mapping)
                and _string(member.get("shard_id")) not in replaced_shard_ids
                and _string(member.get("parent_paragraph_id")) not in touched_paragraph_ids
                and _string(member.get("source_bin_id")) not in touched_bin_ids
            ]
            if not kept_members:
                continue
            next_envelope = dict(proposal)
            next_envelope["member_proposals"] = kept_members
            next_envelope["member_count"] = len(kept_members)
            next_envelope["member_atom_ids"] = [
                _string(member.get("shard_id"))
                for member in kept_members
                if _string(member.get("shard_id"))
            ]
            next_envelope["status"] = (
                "pending_review"
                if any(
                    _string(member.get("status")) in {"", "pending_review"}
                    for member in kept_members
                )
                else _string(next_envelope.get("status")) or "completed"
            )
            filtered_proposals.append(next_envelope)
            continue
        if (
            _string(proposal.get("shard_id")) not in replaced_shard_ids
            and parent_paragraph_id not in touched_paragraph_ids
        ):
            filtered_proposals.append(dict(proposal))
    normalized = dict(review_payload)
    normalized["generated_at"] = _utc_now()
    normalized["proposals"] = filtered_proposals
    pending_review_members = [
        member
        for proposal in filtered_proposals
        for member in (
            proposal.get("member_proposals")
            if isinstance(proposal.get("member_proposals"), list)
            else [proposal]
        )
        if isinstance(member, Mapping) and _string(member.get("status")) in {"", "pending_review"}
    ]
    pending_review_bins = [
        proposal
        for proposal in filtered_proposals
        if (
            isinstance(proposal.get("member_proposals"), list)
            and any(
                isinstance(member, Mapping)
                and _string(member.get("status")) in {"", "pending_review"}
                for member in proposal.get("member_proposals") or []
            )
        )
        or (
            not isinstance(proposal.get("member_proposals"), list)
            and _string(proposal.get("status")) in {"", "pending_review"}
        )
    ]
    normalized["stats"] = {
        "selected_pending_shards": len(pending_review_members),
        "pending_review": len(pending_review_members),
        "pending_review_bins": len(pending_review_bins),
        "route_to_existing": sum(
            1 for proposal in pending_review_members if _string(proposal.get("decision")) == "route_to_existing"
        ),
        "propose_new": sum(
            1 for proposal in pending_review_members if _string(proposal.get("decision")) == "propose_new"
        ),
        "surface_to_codex": sum(
            1 for proposal in pending_review_members if _string(proposal.get("decision")) == "surface_to_codex"
        ),
    }
    dropped = len(review_payload.get("proposals") or []) - len(filtered_proposals)
    return normalized, dropped


def _apply_touched_atomization_surface_updates(
    *,
    repo_root: Path,
    family_token: str,
    family_dir: str,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    extracted_payload: dict[str, Any],
    replacement_rows: list[dict[str, Any]],
    touched_paragraph_ids: set[str],
    source: str,
    merge_note: str,
) -> dict[str, Any]:
    existing_rows = [
        dict(shard)
        for shard in (extracted_payload.get("shards") or [])
        if isinstance(shard, Mapping)
    ]
    replaced_rows = [
        dict(shard)
        for shard in existing_rows
        if _string(shard.get("parent_paragraph_id")) in touched_paragraph_ids
        and _replaceable_atomization_source(shard.get("atomization_source"))
    ]
    kept_rows = [
        dict(shard)
        for shard in existing_rows
        if not (
            _string(shard.get("parent_paragraph_id")) in touched_paragraph_ids
            and _replaceable_atomization_source(shard.get("atomization_source"))
        )
    ]
    merged_rows = _merge_shards(kept_rows, replacement_rows)
    extracted_payload.update(
        {
            "shards": merged_rows,
            "browser_index": _browser_index_for_shards(merged_rows),
            "extracted_at": _utc_now(),
            "source": source,
            "schema_version_family_shards": "extracted_shards_v0",
            "family_path": family_dir,
            "merge_note": merge_note,
        }
    )
    extracted_path = repo_root / family_extracted_shards_path(family_dir)
    _write_json(extracted_path, extracted_payload)

    review_path = repo_root / family_raw_seed_routing_review_path(family_dir)
    review_payload = _load_json(review_path) or _default_routing_review_payload(
        family_token=family_token,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        repo_root=repo_root,
    )
    review_payload, dropped_review_proposals = _prune_routing_review_payload_for_touched_paragraphs(
        review_payload=review_payload,
        replaced_rows=replaced_rows,
        replacement_rows=replacement_rows,
        touched_paragraph_ids=touched_paragraph_ids,
    )
    review_payload["stats"]["remaining_pending_shards"] = sum(
        1 for shard in merged_rows if (_string(shard.get("routing_state")) or "pending") == "pending"
    )
    _write_json(review_path, review_payload)

    principles_payload = _load_json(repo_root / raw_seed_principles_path_for_family(family_dir)) or {"principles": []}
    coverage_payload = build_raw_seed_coverage(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_shards_payload=extracted_payload,
        principles_payload=principles_payload,
        routing_review_payload=review_payload,
    )
    coverage_path = repo_root / family_raw_seed_coverage_path(family_dir)
    _write_json(coverage_path, coverage_payload)
    return {
        "merged_rows": merged_rows,
        "replaced_rows": replaced_rows,
        "review_payload": review_payload,
        "coverage_payload": coverage_payload,
        "dropped_review_proposals": dropped_review_proposals,
    }


def _relative_repo_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_observe_artifact_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.suffix.lower() == ".json":
        payload = _load_json(path)
        if isinstance(payload, dict):
            surfaced = payload.get("payload")
            return dict(surfaced) if isinstance(surfaced, Mapping) else payload
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if path.suffix.lower() == ".md":
        try:
            artifact_payload = extract_observe_artifact_payload(
                source_text=source,
                source_artifact=str(path),
            )
        except ValueError:
            artifact_payload = None
        if isinstance(artifact_payload, Mapping):
            payload_markdown = _string(artifact_payload.get("payload_markdown"))
            if payload_markdown:
                try:
                    payload = extract_json_object(payload_markdown)
                except ValueError:
                    payload = None
                if isinstance(payload, dict):
                    return payload
    try:
        payload = extract_json_object(source)
    except ValueError:
        return None
    return dict(payload) if isinstance(payload, dict) else None


def _load_applied_alchemy_forms_for_family(
    *,
    family: str,
    repo_root: Path,
) -> list[dict[str, Any]]:
    try:
        from system.lib.raw_seed_alchemy import load_applied_alchemy_forms
    except Exception:
        return []
    try:
        return load_applied_alchemy_forms(family=family, repo_root=repo_root)
    except Exception:
        return []


def _infer_alchemy_form_id(
    shard: Mapping[str, Any],
    *,
    alchemy_forms: Sequence[Mapping[str, Any]] | None,
) -> str | None:
    if not alchemy_forms:
        return None
    try:
        from system.lib.raw_seed_alchemy import infer_alchemy_form_id_for_shard
    except Exception:
        return None
    return infer_alchemy_form_id_for_shard(shard, forms=alchemy_forms)


def _normalize_atomized_shards(
    *,
    raw_seed_payload: Mapping[str, Any],
    shards_payload: Mapping[str, Any],
    source_artifact_rel: str,
    source_bin_ids_by_paragraph: Mapping[str, str],
    alchemy_forms: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    paragraphs = _paragraph_index(raw_seed_payload)
    per_parent_index: dict[str, int] = {}
    normalized: list[dict[str, Any]] = []
    for row in shards_payload.get("shards") or []:
        if not isinstance(row, Mapping):
            continue
        parent_paragraph_id = _string(row.get("parent_paragraph_id")).strip()
        clarified_statement = _normalize_whitespace(_string(row.get("clarified_statement")))
        if not parent_paragraph_id or not clarified_statement:
            continue
        paragraph = paragraphs.get(parent_paragraph_id) or {}
        ordinal = _string(row.get("segment_ordinal")).strip()
        if not ordinal:
            next_index = per_parent_index.get(parent_paragraph_id, 0)
            ordinal = _ordinal_label(next_index)
            per_parent_index[parent_paragraph_id] = next_index + 1
        else:
            per_parent_index[parent_paragraph_id] = per_parent_index.get(parent_paragraph_id, 0) + 1

        support_excerpt = _normalize_whitespace(
            _string(row.get("support_excerpt"))
            or _string(row.get("voice_anchor"))
            or clarified_statement
        )
        voice_anchor = _normalize_whitespace(
            _string(row.get("voice_anchor")) or support_excerpt or clarified_statement
        )
        compression_notes = [
            _string(item)
            for item in (row.get("compression_notes") or [])
            if _string(item)
        ]
        if "bridge_atomized_v1" not in compression_notes:
            compression_notes.append("bridge_atomized_v1")
        shard = {
                "id": _stable_atom_id(
                    parent_paragraph_id,
                    ordinal,
                    clarified_statement,
                    voice_anchor=voice_anchor,
                    support_excerpt=support_excerpt,
                ),
                "raw_seed_anchor": _string(row.get("raw_seed_anchor")) or _paragraph_anchor(paragraph),
                "clarified_statement": clarified_statement,
                "status": _string(row.get("status")) or "pending",
                "raw_paragraph_ids": [
                    _string(item)
                    for item in (row.get("raw_paragraph_ids") or [parent_paragraph_id])
                    if _string(item)
                ]
                or [parent_paragraph_id],
                "parent_paragraph_id": parent_paragraph_id,
                "segment_ordinal": ordinal,
                "support_excerpt": support_excerpt,
                "voice_anchor": voice_anchor,
                "coverage_state": _string(row.get("coverage_state")) or "atomized_unreviewed",
                "routing_state": _string(row.get("routing_state")) or "pending",
                "routing_targets": [
                    dict(item)
                    for item in (row.get("routing_targets") or [])
                    if isinstance(item, Mapping)
                ],
                "compression_notes": compression_notes,
                "source_substrate": _string(paragraph.get("source_substrate")) or _string(row.get("source_substrate")) or "raw_seed",
                "authored_by": _string(paragraph.get("authored_by")) or _string(row.get("authored_by")) or "operator",
                "idea_group_ids": [
                    _string(item)
                    for item in (paragraph.get("idea_group_ids") or [])
                    if _string(item)
                ],
                "relevant_files": [
                    _string(item)
                    for item in (row.get("relevant_files") or [])
                    if _string(item)
                ],
                "concept_ids": [
                    _string(item)
                    for item in (row.get("concept_ids") or [])
                    if _string(item)
                ],
                "intent_provenance": [
                    _string(item)
                    for item in (row.get("intent_provenance") or [])
                    if _string(item)
                ],
                "atomization_source": ATOMIZATION_BRIDGE_SOURCE,
                "source_line_span": {
                    "line_start": paragraph.get("line_start"),
                    "line_end": paragraph.get("line_end"),
                },
                "paragraph_fingerprint": _string(
                    paragraph.get("paragraph_fingerprint") or paragraph.get("fingerprint")
                ),
                "source_bin_id": _string(source_bin_ids_by_paragraph.get(parent_paragraph_id)),
                "compression_ratio": row.get("compression_ratio"),
                "distillation_confidence": row.get("distillation_confidence"),
                "gestures_towards": [
                    _string(item)
                    for item in (row.get("gestures_towards") or [])
                    if _string(item)
                ],
                "source_artifact": source_artifact_rel,
            }
        alchemy_form_id = _infer_alchemy_form_id(shard, alchemy_forms=alchemy_forms)
        if alchemy_form_id:
            shard["alchemy_form_id"] = alchemy_form_id
        normalized.append(shard)
    return normalized


def _atomization_plan_paragraph_ids(
    *,
    repo_root: Path,
    plan: Mapping[str, Any],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in plan.get("groups") or []:
        if not isinstance(group, Mapping):
            continue
        role = _string(group.get("role")).strip().lower() or "probe"
        if role != "probe":
            continue
        label = _string(group.get("label")).strip()
        if not label:
            continue
        paragraph_id = ""
        for target in group.get("targets") or []:
            if not isinstance(target, Mapping):
                continue
            file_rel = _string(target.get("file")).strip()
            if not file_rel:
                continue
            packet = _load_json(repo_root / file_rel) or {}
            focus = packet.get("focus_paragraph") if isinstance(packet.get("focus_paragraph"), Mapping) else {}
            paragraph_id = _string(focus.get("id")).strip()
            if paragraph_id:
                break
        if paragraph_id:
            mapping[label] = paragraph_id
    return mapping


def _seed_atomization_ledger_rows(
    *,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    extracted_rows: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    paragraph_index = _paragraph_index(raw_seed_payload)
    source_bin_ids_by_paragraph = {
        _string(bin_row.get("parent_paragraph_id")): _string(bin_row.get("shard_id"))
        for bin_row in (raw_seed_shards_payload.get("shards") or [])
        if isinstance(bin_row, Mapping)
        and _string(bin_row.get("parent_paragraph_id"))
        and _string(bin_row.get("shard_id"))
    }
    seeded: dict[str, dict[str, Any]] = {}
    by_parent: dict[str, list[Mapping[str, Any]]] = {}
    for row in extracted_rows:
        parent_paragraph_id = _string(row.get("parent_paragraph_id"))
        if not parent_paragraph_id:
            continue
        by_parent.setdefault(parent_paragraph_id, []).append(row)
    for paragraph_id, members in by_parent.items():
        paragraph = paragraph_index.get(paragraph_id) or {}
        seeded[paragraph_id] = {
            "paragraph_id": paragraph_id,
            "status": "success",
            "imported_shard_count": len(members),
            "source_bin_id": _string(source_bin_ids_by_paragraph.get(paragraph_id)),
            "last_succeeded_at": _utc_now(),
            "last_attempted_at": _utc_now(),
            "observe_id": None,
            "latest_group_label": None,
            "latest_artifact": _string(members[-1].get("source_artifact")) or None,
            "error_category": None,
            "error_stage": None,
            "error": None,
            "line_start": paragraph.get("line_start"),
            "line_end": paragraph.get("line_end"),
            "paragraph_fingerprint": _string(
                paragraph.get("paragraph_fingerprint") or paragraph.get("fingerprint")
            ),
        }
    return seeded


def _recompute_atomization_ledger_counts(
    *,
    ledger_payload: dict[str, Any],
    raw_seed_payload: Mapping[str, Any],
) -> None:
    paragraphs = ledger_payload.get("paragraphs")
    paragraph_rows = paragraphs if isinstance(paragraphs, Mapping) else {}
    total_paragraphs = len(
        [
            paragraph
            for paragraph in (raw_seed_payload.get("paragraphs") or [])
            if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
        ]
    )
    success = 0
    retryable = 0
    failed = 0
    pending = 0
    for paragraph_id in [
        _string(paragraph.get("id"))
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    ]:
        status = _string((paragraph_rows.get(paragraph_id) or {}).get("status")).strip().lower()
        if status == "success":
            success += 1
        elif status == "retryable":
            retryable += 1
        elif status == "failed":
            failed += 1
        else:
            pending += 1
    ledger_payload["counts"] = {
        "success": success,
        "retryable": retryable,
        "failed": failed,
        "pending": pending,
        "remaining_pending_paragraphs": retryable + failed + pending,
        "total_paragraphs": total_paragraphs,
    }


def _invalidate_stale_atomization_successes(
    *,
    ledger_payload: dict[str, Any],
    raw_seed_payload: Mapping[str, Any],
) -> list[str]:
    paragraph_rows = (
        ledger_payload.get("paragraphs")
        if isinstance(ledger_payload.get("paragraphs"), Mapping)
        else {}
    )
    paragraph_index = _paragraph_index(raw_seed_payload)
    invalidated: list[str] = []
    for paragraph_id, paragraph in paragraph_index.items():
        row = paragraph_rows.get(paragraph_id)
        if not isinstance(row, Mapping):
            continue
        status = _string(row.get("status")).strip().lower()
        current_fingerprint = _paragraph_fingerprint(paragraph)
        stored_fingerprint = _string(row.get("paragraph_fingerprint")).strip()
        if not current_fingerprint:
            continue
        if status == "success" and stored_fingerprint and stored_fingerprint != current_fingerprint:
            next_row = dict(row)
            next_row.update(
                {
                    "status": "pending",
                    "paragraph_fingerprint": current_fingerprint,
                    "last_invalidated_at": _utc_now(),
                    "error_category": "paragraph_fingerprint_changed",
                    "error_stage": "selection",
                    "error": "Paragraph content changed after the previous successful atomization.",
                }
            )
            paragraph_rows[paragraph_id] = next_row
            invalidated.append(paragraph_id)
            continue
        if stored_fingerprint != current_fingerprint:
            next_row = dict(row)
            next_row["paragraph_fingerprint"] = current_fingerprint
            paragraph_rows[paragraph_id] = next_row
    ledger_payload["paragraphs"] = paragraph_rows
    return invalidated


def _load_atomization_ledger_payload(
    *,
    repo_root: Path,
    family_dir: str,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    extracted_rows: Iterable[Mapping[str, Any]],
    persist: bool = False,
) -> dict[str, Any]:
    family_token = _string(raw_seed_payload.get("family_number")) or _string(raw_seed_payload.get("family_id")) or "09"
    ledger_path = repo_root / family_raw_seed_atomization_ledger_path(family_dir)
    payload = _load_json(ledger_path) or _default_atomization_ledger_payload(
        family_token=family_token,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
    )
    paragraphs = payload.get("paragraphs")
    if not isinstance(paragraphs, Mapping):
        payload["paragraphs"] = {}
        paragraphs = payload["paragraphs"]
    existing_rows = {
        _string(key): dict(value)
        for key, value in paragraphs.items()
        if _string(key) and isinstance(value, Mapping)
    }
    seeded_rows = _seed_atomization_ledger_rows(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_rows=extracted_rows,
    )
    for paragraph_id, seeded in seeded_rows.items():
        current = existing_rows.get(paragraph_id)
        if isinstance(current, Mapping) and _string(current.get("status")).strip().lower() == "success":
            continue
        existing_rows[paragraph_id] = seeded
    payload["paragraphs"] = existing_rows
    _invalidate_stale_atomization_successes(
        ledger_payload=payload,
        raw_seed_payload=raw_seed_payload,
    )
    payload["generated_at"] = _utc_now()
    _recompute_atomization_ledger_counts(
        ledger_payload=payload,
        raw_seed_payload=raw_seed_payload,
    )
    if persist:
        _write_json(ledger_path, payload)
    return payload


def preview_atomization_selection(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    paragraph_id: str | None = None,
    selection_mode: str = DEFAULT_ATOMIZE_SELECTION_MODE,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(f"Could not resolve family dir for family={family_token!r}")

    raw_seed_payload = _load_json(repo_root / _seed_json_path_for_substrate(family_dir, substrate=substrate)) or {}
    raw_seed_shards_payload = _seed_shards_payload_for_substrate(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        substrate=substrate,
    )
    extracted_payload = _load_json(repo_root / family_extracted_shards_path(family_dir)) or {"shards": []}
    existing_shards = [
        shard for shard in (extracted_payload.get("shards") or []) if isinstance(shard, Mapping)
    ]
    ledger_payload = _load_atomization_ledger_payload(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_rows=existing_shards,
        persist=True,
    )
    selected_bins = _select_bin_rows(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_shards=existing_shards,
        atomization_ledger_payload=ledger_payload,
        cohort_size=max(1, int(cohort_size)),
        selection_mode=selection_mode,
        paragraph_id=paragraph_id,
    )
    selected_ids = [
        _string(bin_row.get("parent_paragraph_id"))
        for bin_row in selected_bins
        if _string(bin_row.get("parent_paragraph_id"))
    ]
    return {
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate,
        "cohort_size": max(1, int(cohort_size)),
        "selection_mode": _normalize_selection_mode(
            selection_mode,
            default=DEFAULT_ATOMIZE_SELECTION_MODE,
        ),
        "selected_count": len(selected_ids),
        "selected_paragraph_ids": selected_ids,
        "selected_bin_ids": [
            _string(bin_row.get("shard_id"))
            for bin_row in selected_bins
            if _string(bin_row.get("shard_id"))
        ],
        "status": "ready" if selected_ids else "noop",
    }


def _slugify(text: str, *, fallback: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", _string(text).lower())
    slug = "_".join(tokens).strip("_")
    return slug or fallback


def _neighbor_cards(
    *,
    paragraphs: list[dict[str, Any]],
    paragraph_id: str,
    context_window: int,
) -> list[dict[str, Any]]:
    if context_window <= 0:
        return []
    ordered = sorted(
        paragraphs,
        key=lambda paragraph: (
            int(paragraph.get("line_start") or paragraph.get("line_end") or 0),
            _string(paragraph.get("id")),
        ),
    )
    positions = {
        _string(paragraph.get("id")): index
        for index, paragraph in enumerate(ordered)
        if _string(paragraph.get("id"))
    }
    if paragraph_id not in positions:
        return []
    center = positions[paragraph_id]
    start = max(0, center - int(context_window))
    end = min(len(ordered), center + int(context_window) + 1)
    return [
        _paragraph_card(paragraph)
        for index, paragraph in enumerate(ordered[start:end], start=start)
        if index != center
    ]


def _paragraph_packet_payload(
    *,
    family: str,
    family_dir: str,
    focus_paragraph: Mapping[str, Any],
    neighbor_paragraphs: list[dict[str, Any]],
) -> dict[str, Any]:
    focus_text = _paragraph_text(focus_paragraph)
    return {
        "kind": "raw_seed_atomization_packet",
        "schema_version": "raw_seed_atomization_packet_v1",
        "family": {
            "family_number": family,
            "family_dir": family_dir,
        },
        "focus_paragraph": _paragraph_card(focus_paragraph),
        "neighbor_paragraphs": neighbor_paragraphs,
        "focus_text_length": len(focus_text),
        "operator_constraints": [
            "Output shards only for focus_paragraph.id.",
            "Use neighbor_paragraphs only to disambiguate intent.",
            "Preserve voice while removing speech-to-text noise.",
            "Never route or classify doctrine.",
        ],
    }


def _atomization_response_schema(repo_root: Path) -> dict[str, Any]:
    from system.lib.observe_mission_templates import load_mission_template

    try:
        payload = load_mission_template(repo_root, ATOMIZATION_MISSION_ID)
    except ValueError:
        payload = load_mission_template(REPO_ROOT, ATOMIZATION_MISSION_ID)
    schema = payload.get("atomization_response_schema")
    return dict(schema) if isinstance(schema, Mapping) else {}


def _atomization_dispatch_policy(repo_root: Path) -> dict[str, Any]:
    from system.lib.observe_mission_templates import load_mission_template

    try:
        payload = load_mission_template(repo_root, ATOMIZATION_MISSION_ID)
    except ValueError:
        payload = load_mission_template(REPO_ROOT, ATOMIZATION_MISSION_ID)
    dispatch_policy = payload.get("dispatch_policy") if isinstance(payload.get("dispatch_policy"), Mapping) else {}
    return {
        **dict(dispatch_policy or {}),
        "mission_id": ATOMIZATION_MISSION_ID,
    }


def _resolve_atomization_wave_width(
    *,
    repo_root: Path,
    provider: str,
    requested_wave_width: Any,
) -> dict[str, Any]:
    return resolve_dispatch_policy(
        mission_dispatch_policy=_atomization_dispatch_policy(repo_root),
        provider=provider,
        requested_wave_width=requested_wave_width,
        provider_capabilities_path=repo_root / "tools/meta/bridge/provider_capabilities.json",
    )


def build_atomization_run_payload(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    limit: int | None = None,
    paragraph_ids: list[str] | None = None,
    mission_slug: str | None = None,
    provider: str = DEFAULT_PROVIDER,
    wave_width: Any = "auto",
    context_window: int = DEFAULT_ATOMIZATION_CONTEXT_WINDOW,
    selection_mode: str = DEFAULT_ATOMIZE_SELECTION_MODE,
    output_root_rel: str = DEFAULT_ATOMIZATION_OUTPUT_ROOT,
    dump_root_rel: str = DEFAULT_ATOMIZATION_DUMP_ROOT,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    substrate_token = _string(substrate).strip() or "raw_seed"
    if not family_dir:
        raise FileNotFoundError(f"Could not resolve family dir for family={family_token!r}")

    raw_seed_payload = _load_json(
        repo_root / _seed_json_path_for_substrate(family_dir, substrate=substrate_token)
    )
    if not raw_seed_payload:
        raise FileNotFoundError(f"{substrate_token}.json missing for family {family_token}")
    raw_seed_shards_payload = _seed_shards_payload_for_substrate(
        repo_root=repo_root,
        family_dir=family_dir,
        substrate=substrate_token,
        raw_seed_payload=raw_seed_payload,
    )
    extracted_payload = _load_json(repo_root / family_extracted_shards_path(family_dir)) or {"shards": []}
    existing_shards = [
        shard for shard in (extracted_payload.get("shards") or []) if isinstance(shard, Mapping)
    ]
    ledger_payload = _load_atomization_ledger_payload(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_rows=existing_shards,
        persist=True,
    )

    requested_cohort_size = max(1, int(limit if limit is not None else cohort_size))
    normalized_selection_mode = _normalize_selection_mode(
        selection_mode,
        default=DEFAULT_ATOMIZE_SELECTION_MODE,
    )
    explicit_ids = _dedupe_strings(paragraph_ids or [])
    selected_bins: list[dict[str, Any]]
    if explicit_ids:
        bins_by_parent = _bins_by_parent_paragraph(_bin_rows(raw_seed_shards_payload))
        selected_bins = [
            dict(bins_by_parent[paragraph_id])
            for paragraph_id in explicit_ids
            if paragraph_id in bins_by_parent
        ]
    else:
        selected_bins = _select_bin_rows(
            raw_seed_payload=raw_seed_payload,
            raw_seed_shards_payload=raw_seed_shards_payload,
            extracted_shards=existing_shards,
            atomization_ledger_payload=ledger_payload,
            cohort_size=requested_cohort_size,
            selection_mode=normalized_selection_mode,
        )
    if not selected_bins:
        raise ValueError("No raw-seed paragraphs matched the requested atomization selection.")

    wave_resolution = _resolve_atomization_wave_width(
        repo_root=repo_root,
        provider=provider,
        requested_wave_width=wave_width,
    )
    if _string(wave_resolution.get("status")) != "ok":
        raise ValueError(
            f"wave_width {wave_width!r} exceeds provider ceiling "
            f"{wave_resolution.get('provider_ceiling')} for provider {provider!r}"
        )

    default_slug = f"{ATOMIZATION_MISSION_ID}_{family_token}_{_utc_stamp()}"
    resolved_slug = _slugify(mission_slug or default_slug, fallback=default_slug)
    run_root_rel = f"{output_root_rel.rstrip('/')}/{resolved_slug}"
    packet_root = repo_root / run_root_rel / "paragraph_packets"
    packet_root.mkdir(parents=True, exist_ok=True)

    paragraph_index = _paragraph_index(raw_seed_payload)
    all_paragraphs = [
        dict(paragraph)
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping)
    ]
    paragraph_batches: list[dict[str, Any]] = []
    packet_manifest_rows: list[dict[str, Any]] = []
    selected_paragraph_ids: list[str] = []
    for index, bin_row in enumerate(selected_bins):
        paragraph_id = _string(bin_row.get("parent_paragraph_id"))
        paragraph = paragraph_index.get(paragraph_id)
        if not paragraph:
            continue
        packet_slug = _slugify(paragraph_id, fallback=f"paragraph_{index + 1:02d}")
        packet_rel = f"{run_root_rel}/paragraph_packets/{index + 1:02d}_{packet_slug}.json"
        packet_path = repo_root / packet_rel
        neighbors = _neighbor_cards(
            paragraphs=all_paragraphs,
            paragraph_id=paragraph_id,
            context_window=context_window,
        )
        _write_json(
            packet_path,
            _paragraph_packet_payload(
                family=family_token,
                family_dir=family_dir,
                focus_paragraph=paragraph,
                neighbor_paragraphs=neighbors,
            ),
        )
        selected_paragraph_ids.append(paragraph_id)
        packet_manifest_rows.append(
            {
                "paragraph_id": paragraph_id,
                "source_bin_id": _string(bin_row.get("shard_id")),
                "packet_path": packet_rel,
                "neighbor_ids": [row["id"] for row in neighbors if _string(row.get("id"))],
                "focus_text_length": len(_paragraph_text(paragraph)),
            }
        )
        paragraph_batches.append(
            {
                "slug": packet_slug,
                "notes": (
                    f"Atomize focus paragraph `{paragraph_id}` only. "
                    "Neighbor paragraphs are context-only; use them only to disambiguate local meaning, not to merge provenance."
                ),
                "question": (
                    f"Read the packet for `{paragraph_id}` and atomize its focus paragraph into one or more "
                    "voice-preserving extracted-shard rows. Split whenever the paragraph contains multiple independently routable "
                    "claims, reversals, directives, constraints, rationales, or support statements."
                ),
                "acceptance": (
                    f"Return JSON only. Every shard must keep `parent_paragraph_id` = `{paragraph_id}`, "
                    "emit left-to-right `segment_ordinal` values, preserve a verbatim `voice_anchor`, include "
                    "`support_excerpt`, `compression_ratio`, `distillation_confidence`, `gestures_towards`, and "
                    "`compression_notes`, and leave `raw_paragraph_ids` unset unless this becomes a true multi-parent carry-forward row."
                ),
                "provider": provider,
                "targets": [{"file": packet_rel, "scope": "full"}],
                "context_files": [],
            }
        )

    packet_manifest_rel = f"{run_root_rel}/paragraph_packets_manifest.json"
    _write_json(
        repo_root / packet_manifest_rel,
        {
            "kind": "raw_seed_atomization_packet_manifest",
            "schema_version": "raw_seed_atomization_packet_manifest_v1",
            "generated_at": _utc_now(),
            "family": family_token,
            "family_dir": family_dir,
            "substrate": substrate_token,
            "mission_slug": resolved_slug,
            "count": len(packet_manifest_rows),
            "packets": packet_manifest_rows,
        },
    )

    effective_wave_width = int(wave_resolution.get("effective_wave_width") or 1)
    params = {
        "mission_slug": resolved_slug,
        "dump_dir": f"{dump_root_rel.rstrip('/')}/{resolved_slug}",
        "family": family_token,
        "goal_question": (
            f"How should the next bounded family-{family_token} raw-seed paragraph cohort be atomized into "
            "canonical voice-preserving extracted-shard rows with stable A/B/C provenance?"
        ),
        "success_criteria": (
            "Each selected paragraph yields one or more shard rows with parent provenance, "
            "segment ordinals, support excerpts, and full voice-envelope fields without inventing routing or doctrine targets."
        ),
        "paragraph_batches": paragraph_batches,
        "atomization_response_schema": _atomization_response_schema(repo_root),
        "recommended_provider": provider,
        "recommended_wave_width": effective_wave_width,
        "recommended_max_workers": effective_wave_width,
        "dispatch_policy": _atomization_dispatch_policy(repo_root),
        "source_substrate": substrate_token,
    }
    return {
        "mission_id": ATOMIZATION_MISSION_ID,
        "mission_slug": resolved_slug,
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "run_root": run_root_rel,
        "packet_manifest_path": packet_manifest_rel,
        "selected_paragraph_ids": selected_paragraph_ids,
        "cohort_size": requested_cohort_size,
        "selection_mode": normalized_selection_mode,
        "selected_count": len(selected_paragraph_ids),
        "wave_width_requested": wave_width,
        "wave_width_effective": effective_wave_width,
        "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
        "provider": provider,
        "safe_parallelism": int(wave_resolution.get("provider_ceiling") or 0),
        "dispatch_policy": _atomization_dispatch_policy(repo_root),
        "params": params,
    }


def materialize_atomization_mission(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    limit: int | None = None,
    paragraph_ids: list[str] | None = None,
    mission_slug: str | None = None,
    provider: str = DEFAULT_PROVIDER,
    wave_width: Any = "auto",
    context_window: int = DEFAULT_ATOMIZATION_CONTEXT_WINDOW,
    selection_mode: str = DEFAULT_ATOMIZE_SELECTION_MODE,
    output_root_rel: str = DEFAULT_ATOMIZATION_OUTPUT_ROOT,
    dump_root_rel: str = DEFAULT_ATOMIZATION_DUMP_ROOT,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    payload = build_atomization_run_payload(
        family=family,
        repo_root=repo_root,
        cohort_size=cohort_size,
        limit=limit,
        paragraph_ids=paragraph_ids,
        mission_slug=mission_slug,
        provider=provider,
        wave_width=wave_width,
        context_window=context_window,
        selection_mode=selection_mode,
        output_root_rel=output_root_rel,
        dump_root_rel=dump_root_rel,
        substrate=substrate,
    )
    from system.lib.observe_mission_templates import expand_mission_template

    try:
        expansion = expand_mission_template(
            repo_root=repo_root,
            mission_id=ATOMIZATION_MISSION_ID,
            params=payload["params"],
            family_context={
                "family_id": payload["family"],
                "family_dir": payload["family_dir"],
            },
        )
    except ValueError:
        expansion = expand_mission_template(
            repo_root=REPO_ROOT,
            mission_id=ATOMIZATION_MISSION_ID,
            params=payload["params"],
            family_context={
                "family_id": payload["family"],
                "family_dir": payload["family_dir"],
            },
        )
    run_root = repo_root / payload["run_root"]
    params_rel = f"{payload['run_root']}/mission_params.json"
    plan_rel = f"{payload['run_root']}/observe_session_plan.json"
    mission_launch_plan_rel = f"{payload['params']['dump_dir']}/_mission_launch_plan.json"
    _write_json(repo_root / params_rel, payload["params"])
    _write_json(repo_root / plan_rel, expansion.plan)
    _write_json(repo_root / mission_launch_plan_rel, expansion.plan)

    run_summary = {
        "status": "planned",
        "mission_id": expansion.mission_id,
        "mission_slug": payload["mission_slug"],
        "run_root": payload["run_root"],
        "template_path": expansion.template_path,
        "params_path": params_rel,
        "plan_path": plan_rel,
        "mission_launch_plan_path": mission_launch_plan_rel,
        "packet_manifest_path": payload["packet_manifest_path"],
        "dispatch_policy": dict(expansion.dispatch_policy),
        "cohort_size": payload["cohort_size"],
        "selection_mode": payload["selection_mode"],
        "selected_paragraph_ids": payload["selected_paragraph_ids"],
        "selected_count": payload["selected_count"],
        "wave_width_requested": payload["wave_width_requested"],
        "wave_width_effective": payload["wave_width_effective"],
        "provider_ceiling": payload["provider_ceiling"],
        "provider": payload["provider"],
        "safe_parallelism": payload["safe_parallelism"],
        "family": payload["family"],
        "family_dir": payload["family_dir"],
        "substrate": payload.get("substrate") or "raw_seed",
        "skill_files": list(expansion.skill_files),
        "shared_context_files": list(expansion.shared_context_files),
        "effective_group_context_files": list(expansion.injected_context_files),
        "dispatch_ready": True,
        "launch_mode": "manual_later",
        "import_contract": {
            "ledger_path": family_raw_seed_atomization_ledger_path(payload["family_dir"]),
            "extracted_shards_path": family_extracted_shards_path(payload["family_dir"]),
            "raw_seed_routing_review_path": family_raw_seed_routing_review_path(payload["family_dir"]),
            "raw_seed_coverage_path": family_raw_seed_coverage_path(payload["family_dir"]),
        },
        "review_commands": [
            (
                "./repo-python -m tools.meta.apply.run_observe_plan "
                f"--plan {mission_launch_plan_rel} --bridge --provider {payload['provider']} "
                f"--bridge-workers {payload['wave_width_effective']}"
            ),
        ],
    }
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def _load_provider_capabilities(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "tools" / "meta" / "bridge" / "provider_capabilities.json"
    return _load_dispatch_provider_capabilities(path) or {}


def _safe_parallelism(repo_root: Path, provider: str) -> int:
    path = repo_root / "tools" / "meta" / "bridge" / "provider_capabilities.json"
    value = provider_ceiling_for_provider(provider, path)
    if isinstance(value, int) and value > 0:
        return value
    return DEFAULT_ACTIVE_WORKERS


def provider_safe_parallelism(repo_root: Path, provider: str) -> int:
    return _safe_parallelism(repo_root, provider)


def _mission_dispatch_policy(repo_root: Path, mission_id: str) -> dict[str, Any]:
    from system.lib.observe_mission_templates import load_mission_template

    try:
        payload = load_mission_template(repo_root, mission_id)
    except ValueError:
        payload = load_mission_template(REPO_ROOT, mission_id)
    dispatch_policy = payload.get("dispatch_policy") if isinstance(payload.get("dispatch_policy"), Mapping) else {}
    return {
        **dict(dispatch_policy or {}),
        "mission_id": mission_id,
    }


def _resolve_routing_wave_width(
    *,
    repo_root: Path,
    provider: str,
    requested_wave_width: Any,
) -> dict[str, Any]:
    path = repo_root / "tools" / "meta" / "bridge" / "provider_capabilities.json"
    return resolve_dispatch_policy(
        mission_dispatch_policy=_mission_dispatch_policy(repo_root, ROUTING_MISSION_ID),
        provider=provider,
        requested_wave_width=requested_wave_width,
        provider_capabilities_path=path,
    )


def _top_doctrine_nodes(repo_root: Path) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    for folder, kind in (("codex/doctrine/concepts", "concept"), ("codex/doctrine/mechanisms", "mechanism")):
        base = repo_root / folder
        if not base.exists():
            continue
        for path in sorted(base.glob("*.json")):
            payload = _load_json(path) or {}
            node_id = _string(payload.get("id"))
            title = _string(payload.get("title"))
            if not node_id or not title:
                continue
            text_parts = [
                node_id,
                _string(payload.get("slug")),
                title,
                _string(payload.get("statement")),
                _string(payload.get("summary")),
                _string(payload.get("note")),
            ]
            tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
            text_parts.extend([tag for tag in tags if isinstance(tag, str)])
            nodes.append(
                {
                    "kind": kind,
                    "id": node_id,
                    "title": title,
                    "keywords": _tokenize(" ".join(text_parts)),
                }
            )

    return nodes


def _family_principle_nodes(principles_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for principle in principles_payload.get("principles") or []:
        if not isinstance(principle, Mapping):
            continue
        node_id = _string(principle.get("id"))
        title = _string(principle.get("title"))
        if not node_id or not title:
            continue
        text_parts = [
            node_id,
            _string(principle.get("slug")),
            title,
            _string(principle.get("statement")),
            _string(principle.get("note")),
        ]
        tags = principle.get("tags") if isinstance(principle.get("tags"), list) else []
        text_parts.extend([tag for tag in tags if isinstance(tag, str)])
        nodes.append(
            {
                "kind": "principle",
                "id": node_id,
                "title": title,
                "keywords": _tokenize(" ".join(text_parts)),
            }
        )
    return nodes


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]{3,}", _string(text).lower())
        if token not in {"with", "that", "this", "from", "have", "into", "their", "then", "when", "should"}
    }


def _is_low_signal_routing_statement(statement: str, *, voice_anchor: str = "") -> bool:
    normalized = _normalize_whitespace(statement).lower()
    if not normalized:
        return True
    if normalized in LOW_SIGNAL_ROUTING_STATEMENTS:
        return True

    compact = re.sub(r"\s+", "", normalized)
    if re.fullmatch(r"[-_=~`{}()[\]<>|/\\+*.:;,#]+", compact):
        return True

    lexical_tokens = re.findall(r"[a-z0-9_]{2,}", normalized)
    if len(lexical_tokens) < 2:
        return True

    normalized_voice_anchor = _normalize_whitespace(voice_anchor).lower()
    if normalized_voice_anchor:
        compact_voice_anchor = re.sub(r"\s+", "", normalized_voice_anchor)
        if re.fullmatch(r"[-_=~`{}()[\]<>|/\\+*.:;,#]+", compact_voice_anchor):
            return True

    return False


def _proposed_slug(statement: str) -> str:
    words = re.findall(r"[a-z0-9]+", statement.lower())
    return "-".join(words[:8]) or "raw-seed-proposal"


def _make_forward_gloss(shard: Mapping[str, Any], target_title: str) -> str:
    return (
        f"This atomized raw-seed shard supports `{target_title}` by carrying a directly aligned "
        "intent statement from the family substrate."
    )


def _make_reverse_gloss(shard: Mapping[str, Any], target_title: str) -> str:
    return (
        f"`{target_title}` should route back to this shard as provenance because the shard captures "
        "one explicit statement the doctrine node is meant to encode."
    )


def _rank_doctrine_targets(statement: str, nodes: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    shard_tokens = _tokenize(statement)
    if not shard_tokens:
        return []
    ranked: list[dict[str, Any]] = []
    for node in nodes:
        keywords = node.get("keywords")
        if not isinstance(keywords, set) or not keywords:
            continue
        overlap = shard_tokens & keywords
        if not overlap:
            continue
        score = len(overlap)
        confidence = round(min(0.97, 0.35 + (score * 0.11)), 2)
        ranked.append(
            {
                "kind": _string(node.get("kind")),
                "id": _string(node.get("id")),
                "title": _string(node.get("title")),
                "score": score,
                "confidence": confidence,
            }
        )
    ranked.sort(key=lambda row: (-int(row.get("score") or 0), -float(row.get("confidence") or 0), row.get("id") or ""))
    return ranked


def _routing_decision_for_shard(
    shard: Mapping[str, Any],
    doctrine_nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    statement = _normalize_whitespace(_string(shard.get("clarified_statement")))
    voice_anchor = _string(shard.get("voice_anchor"))
    ranked = _rank_doctrine_targets(statement, doctrine_nodes)
    top = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None

    if top and second and abs(int(top.get("score") or 0) - int(second.get("score") or 0)) <= AMBIGUITY_DELTA:
        return {
            "decision": "surface_to_codex",
            "confidence": round(float(top.get("confidence") or 0), 2),
            "reason": "multiple_doctrine_targets_compete",
            "missing_context_hypothesis": "The shard needs human or controller judgment because multiple doctrine nodes overlap at similar strength.",
            "candidate_targets": ranked[:3],
        }

    if top and float(top.get("confidence") or 0) >= 0.55:
        return {
            "decision": "route_to_existing",
            "confidence": round(float(top.get("confidence") or 0), 2),
            "target": {
                "kind": top["kind"],
                "id": top["id"],
                "title": top["title"],
                "score": top["score"],
            },
            "forward_gloss": _make_forward_gloss(shard, _string(top.get("title"))),
            "reverse_gloss": _make_reverse_gloss(shard, _string(top.get("title"))),
            "candidate_targets": ranked[:3],
        }

    if statement and _is_low_signal_routing_statement(statement, voice_anchor=voice_anchor):
        return {
            "decision": "surface_to_codex",
            "confidence": 0.24,
            "reason": "low_signal_statement",
            "missing_context_hypothesis": (
                "The shard looks like a fragment, delimiter, or single-token state marker. "
                "It should stay surfaced for controller judgment instead of minting new doctrine."
            ),
            "candidate_targets": ranked[:3],
        }

    if statement:
        return {
            "decision": "propose_new",
            "confidence": 0.42,
            "proposed_kind": "principle",
            "proposed_slug": _proposed_slug(statement),
            "seed_statement": statement,
            "why_no_existing_fits": "No current doctrine node crossed the bounded lexical-confidence threshold.",
            "candidate_targets": ranked[:3],
        }

    return {
        "decision": "surface_to_codex",
        "confidence": 0.2,
        "reason": "missing_statement",
        "missing_context_hypothesis": "The shard does not contain enough normalized text to route safely.",
        "candidate_targets": [],
    }


def build_raw_seed_coverage(
    *,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    extracted_shards_payload: Mapping[str, Any],
    principles_payload: Mapping[str, Any],
    routing_review_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    family_dir = _string(raw_seed_payload.get("family_dir"))
    review_payload = normalize_routing_review_payload(
        routing_review_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_shards_payload=extracted_shards_payload,
    )
    paragraphs = [p for p in raw_seed_payload.get("paragraphs") or [] if isinstance(p, Mapping)]
    paragraph_index = _paragraph_index(raw_seed_payload)
    paragraph_level_shards = _bin_rows(raw_seed_shards_payload)
    bins_by_parent = _bins_by_parent_paragraph(paragraph_level_shards)
    atomized_shards = [
        shard for shard in extracted_shards_payload.get("shards") or [] if isinstance(shard, Mapping)
    ]

    atomized_by_parent: dict[str, list[dict[str, Any]]] = {}
    atomized_by_bin = _atomized_members_by_bin(atomized_shards, bins_by_parent=bins_by_parent)
    routing_state_counts: dict[str, int] = {}
    coverage_state_counts: dict[str, int] = {}
    receive_state_counts: dict[str, int] = {}
    audit_state_counts: dict[str, int] = {}
    doctrine_target_counts: dict[str, int] = {}
    pending_routing_groups_index: dict[str, dict[str, Any]] = {}
    for shard in atomized_shards:
        parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
        if parent_paragraph_id:
            atomized_by_parent.setdefault(parent_paragraph_id, []).append(shard)
        routing_state = _string(shard.get("routing_state")) or "pending"
        coverage_state = _string(shard.get("coverage_state")) or "unknown"
        receive_state = _string(shard.get("receive_state")) or "legacy_or_unmarked"
        audit_state = _string(shard.get("audit_state")) or "unmarked"
        routing_state_counts[routing_state] = routing_state_counts.get(routing_state, 0) + 1
        coverage_state_counts[coverage_state] = coverage_state_counts.get(coverage_state, 0) + 1
        receive_state_counts[receive_state] = receive_state_counts.get(receive_state, 0) + 1
        audit_state_counts[audit_state] = audit_state_counts.get(audit_state, 0) + 1
        for target in shard.get("routing_targets") or []:
            if isinstance(target, Mapping):
                target_id = _string(target.get("id"))
            else:
                target_id = _string(target)
            if target_id:
                doctrine_target_counts[target_id] = doctrine_target_counts.get(target_id, 0) + 1
        if routing_state == "pending":
            source_bin_id = _source_bin_id_for_shard(shard, bins_by_parent=bins_by_parent)
            for group_id in shard_group_ids(shard):
                entry = pending_routing_groups_index.setdefault(
                    group_id,
                    {
                        "group_id": group_id,
                        "pending_shard_ids": set(),
                        "pending_bin_ids": set(),
                        "parent_paragraph_ids": set(),
                    },
                )
                shard_id = _string(shard.get("id"))
                if shard_id:
                    entry["pending_shard_ids"].add(shard_id)
                if source_bin_id:
                    entry["pending_bin_ids"].add(source_bin_id)
                if parent_paragraph_id:
                    entry["parent_paragraph_ids"].add(parent_paragraph_id)

    pending_routing_groups = sorted(
        (
            {
                "group_id": group_id,
                "pending_shard_count": len(entry["pending_shard_ids"]),
                "pending_bin_count": len(entry["pending_bin_ids"]),
                "pending_shard_ids": sorted(entry["pending_shard_ids"]),
                "pending_bin_ids": sorted(entry["pending_bin_ids"]),
                "parent_paragraph_ids": sorted(entry["parent_paragraph_ids"]),
            }
            for group_id, entry in pending_routing_groups_index.items()
        ),
        key=lambda item: (
            -int(item.get("pending_shard_count") or 0),
            -int(item.get("pending_bin_count") or 0),
            _string(item.get("group_id")),
        ),
    )
    top_pending_routing_group = pending_routing_groups[0] if pending_routing_groups else None

    principle_support: dict[str, dict[str, Any]] = {}
    for principle in principles_payload.get("principles") or []:
        if not isinstance(principle, Mapping):
            continue
        principle_id = _string(principle.get("id"))
        if not principle_id:
            continue
        evidence_refs = [
            _string(evidence.get("ref"))
            for evidence in principle.get("evidence") or []
            if isinstance(evidence, Mapping)
        ]
        matching_paragraphs = [
            ref for ref in evidence_refs if ref.startswith("par_") and ref in paragraph_index
        ]
        principle_support[principle_id] = {
            "title": _string(principle.get("title")),
            "scope": _string(principle.get("scope")),
            "status": _string(principle.get("status")),
            "paragraph_refs": sorted(set(matching_paragraphs)),
            "paragraph_ref_count": len(set(matching_paragraphs)),
            "atomized_routing_count": doctrine_target_counts.get(principle_id, 0),
        }

    review_entries = [
        proposal
        for proposal in review_payload.get("proposals") or []
        if isinstance(proposal, Mapping)
    ]
    pending_review_entries = [
        proposal for proposal in review_entries if _proposal_is_pending_review(proposal)
    ]
    pending_review_members = _pending_review_member_proposals(review_payload)
    atomized_shards_by_id = {
        _string(shard.get("id")): dict(shard)
        for shard in atomized_shards
        if _string(shard.get("id"))
    }
    pending_review_members_by_bin: dict[str, list[dict[str, Any]]] = {}
    for proposal in pending_review_members:
        bin_id = _string(proposal.get("source_bin_id"))
        if not bin_id:
            shard = atomized_shards_by_id.get(_string(proposal.get("shard_id")))
            if shard:
                bin_id = _source_bin_id_for_shard(shard, bins_by_parent=bins_by_parent)
        if not bin_id:
            continue
        pending_review_members_by_bin.setdefault(bin_id, []).append(dict(proposal))

    review_envelopes_by_bin = _review_envelopes_by_bin(review_payload)
    paragraph_cards: dict[str, Any] = {}
    paragraphs_without_atoms: list[str] = []
    for paragraph_id, paragraph in paragraph_index.items():
        atomized = atomized_by_parent.get(paragraph_id, [])
        raw_seed_shard = bins_by_parent.get(paragraph_id)
        if not atomized:
            paragraphs_without_atoms.append(paragraph_id)
        paragraph_cards[paragraph_id] = {
            "line_start": paragraph.get("line_start"),
            "line_end": paragraph.get("line_end"),
            "raw_seed_shard_id": _string(raw_seed_shard.get("shard_id")) if isinstance(raw_seed_shard, Mapping) else None,
            "source_bin_id": _string(raw_seed_shard.get("shard_id")) if isinstance(raw_seed_shard, Mapping) else None,
            "atomized_shard_ids": sorted(_string(shard.get("id")) for shard in atomized if _string(shard.get("id"))),
            "atomized_count": len(atomized),
            "routing_states": {
                state: sum(1 for shard in atomized if (_string(shard.get("routing_state")) or "pending") == state)
                for state in sorted(
                    {
                        _string(shard.get("routing_state")) or "pending"
                        for shard in atomized
                    }
                )
            },
        }

    bins_map: dict[str, dict[str, Any]] = {}
    pending_routing_bin_ids: list[str] = []
    review_queue_bin_ids: list[str] = []
    for bin_row in paragraph_level_shards:
        bin_id = _string(bin_row.get("shard_id"))
        if not bin_id:
            continue
        parent_paragraph_id = _string(bin_row.get("parent_paragraph_id"))
        members = atomized_by_bin.get(bin_id, [])
        pending_members = [
            member
            for member in members
            if (_string(member.get("routing_state")) or "pending") == "pending"
        ]
        review_members = pending_review_members_by_bin.get(bin_id, [])
        review_envelope = review_envelopes_by_bin.get(bin_id) or {}
        routing_states = {
            state: sum(1 for member in members if (_string(member.get("routing_state")) or "pending") == state)
            for state in sorted(
                {_string(member.get("routing_state")) or "pending" for member in members}
            )
        }
        if pending_members:
            routing_state = "pending"
            pending_routing_bin_ids.append(bin_id)
        elif review_members:
            routing_state = "pending_review"
        elif members:
            routing_state = (
                next(iter(routing_states.keys()))
                if len(routing_states) == 1
                else "mixed"
            )
        else:
            routing_state = "unatomized"
        if review_members:
            review_queue_bin_ids.append(bin_id)
        bins_map[bin_id] = {
            "bin_id": bin_id,
            "parent_paragraph_id": parent_paragraph_id or None,
            "member_atom_ids": sorted(
                _string(member.get("id")) for member in members if _string(member.get("id"))
            ),
            "pending_atom_ids": sorted(
                _string(member.get("id")) for member in pending_members if _string(member.get("id"))
            ),
            "pending_review_proposal_ids": sorted(
                _string(member.get("id")) for member in review_members if _string(member.get("id"))
            ),
            "sibling_bin_ids": sorted(
                _string(item)
                for item in (bin_row.get("sibling_shard_ids") or [])
                if _string(item)
            ),
            "atomization_count": len(members),
            "pending_atom_count": len(pending_members),
            "review_member_count": len(review_members),
            "review_envelope_id": _string(review_envelope.get("id")) or None,
            "routing_state": routing_state,
            "routing_state_counts": routing_states,
        }

    coverage_payload = {
        "kind": "raw_seed_coverage",
        "schema_version": RAW_SEED_COVERAGE_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "family_id": _string(raw_seed_payload.get("family_id")),
        "family_number": _string(raw_seed_payload.get("family_number")),
        "family_title": _string(raw_seed_payload.get("family_title")),
        "family_dir": family_dir,
        "source_paths": {
            "raw_seed_json_path": raw_seed_json_path_for_family(family_dir),
            "raw_seed_shards_path": raw_seed_shards_path_for_family(family_dir),
            "extracted_shards_path": family_extracted_shards_path(family_dir),
            "raw_seed_principles_path": raw_seed_principles_path_for_family(family_dir),
            "raw_seed_routing_review_path": family_raw_seed_routing_review_path(family_dir),
        },
        "counts": {
            "total_paragraphs": len(paragraphs),
            "total_bins": len(paragraph_level_shards),
            "total_paragraph_level_shards": len(paragraph_level_shards),
            "total_atomized_shards": len(atomized_shards),
            "paragraphs_with_atoms": len(paragraph_index) - len(paragraphs_without_atoms),
            "paragraphs_without_atoms": len(paragraphs_without_atoms),
            "pending_routing_shards": sum(1 for shard in atomized_shards if (_string(shard.get("routing_state")) or "pending") == "pending"),
            "pending_routing_bins": len(set(pending_routing_bin_ids)),
            "review_queue_entries": len(pending_review_members),
            "review_queue_bins": len(set(review_queue_bin_ids)),
            "doctrine_target_count": len(doctrine_target_counts),
            "received_shard_rows": receive_state_counts.get("received", 0)
            + receive_state_counts.get("received_with_warnings", 0),
            "received_with_warning_rows": receive_state_counts.get("received_with_warnings", 0),
            "quarantined_rows": int(
                (
                    extracted_shards_payload.get("bridge_import_receipt")
                    if isinstance(extracted_shards_payload.get("bridge_import_receipt"), Mapping)
                    else {}
                ).get("quarantined_rows")
                or 0
            ),
            "max_pending_routing_group_shards": int(
                (top_pending_routing_group or {}).get("pending_shard_count") or 0
            ),
        },
        "routing_state_counts": routing_state_counts,
        "coverage_state_counts": coverage_state_counts,
        "receive_state_counts": receive_state_counts,
        "audit_state_counts": audit_state_counts,
        "bridge_import_receipt": (
            dict(extracted_shards_payload.get("bridge_import_receipt") or {})
            if isinstance(extracted_shards_payload.get("bridge_import_receipt"), Mapping)
            else {}
        ),
        "top_pending_routing_group": top_pending_routing_group,
        "pending_routing_groups": pending_routing_groups,
        "paragraphs_without_atoms": paragraphs_without_atoms,
        "paragraphs": paragraph_cards,
        "bins": bins_map,
        "doctrine_support": principle_support,
        "pending_queues": {
            "atomization": paragraphs_without_atoms,
            "routing": [
                _string(shard.get("id"))
                for shard in atomized_shards
                if (_string(shard.get("routing_state")) or "pending") == "pending"
            ],
            "routing_bins": sorted(set(pending_routing_bin_ids)),
            "review": [
                _string(proposal.get("id"))
                for proposal in pending_review_members
                if _string(proposal.get("id"))
            ],
            "review_bins": sorted(set(review_queue_bin_ids)),
        },
    }
    return coverage_payload


def ingest_family_raw_seed_distillations(
    *,
    family: str,
    input_path: Path,
    repo_root: Path = REPO_ROOT,
    provider: str = DEFAULT_PROVIDER,
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(f"Could not resolve family dir for family={family_token!r}")

    raw_seed_payload_path = repo_root / raw_seed_json_path_for_family(family_dir)
    raw_seed_payload = _load_json(raw_seed_payload_path)
    if not raw_seed_payload:
        raise FileNotFoundError(f"raw_seed.json missing for family {family_token}")

    resolved_input_path = input_path if input_path.is_absolute() else (repo_root / input_path)
    payload = _load_json(resolved_input_path)
    if not payload:
        raise ValueError(f"Could not read distillation payload from {resolved_input_path}")

    paragraph_index = {
        _string(paragraph.get("id")): paragraph
        for paragraph in raw_seed_payload.get("paragraphs") or []
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    }
    input_items = _distillation_input_items(payload)
    if not input_items:
        raise ValueError("Distillation payload must contain a non-empty distillations/items list")

    try:
        source_path = resolved_input_path.relative_to(repo_root).as_posix()
    except ValueError:
        source_path = str(resolved_input_path)
    source_sha256 = hashlib.sha256(resolved_input_path.read_bytes()).hexdigest()
    provider_token = _string(payload.get("provider")) or _string(provider) or DEFAULT_PROVIDER
    batch_id = (
        _string(payload.get("batch_id"))
        or _string(payload.get("distillation_batch_id"))
        or f"dist_batch_{source_sha256[:12]}"
    )

    ingested_rows: list[dict[str, Any]] = []
    rejected_items: list[dict[str, Any]] = []
    for index, item in enumerate(input_items):
        paragraph_id = _string(
            item.get("paragraph_id")
            or item.get("parent_paragraph_id")
            or item.get("raw_paragraph_id")
        )
        paragraph = paragraph_index.get(paragraph_id)
        if not paragraph:
            rejected_items.append(
                {
                    "index": index,
                    "paragraph_id": paragraph_id or None,
                    "reason": "unknown_paragraph_id",
                }
            )
            continue

        statements = _statement_units_from_distillation(item)
        if not statements:
            rejected_items.append(
                {
                    "index": index,
                    "paragraph_id": paragraph_id,
                    "reason": "missing_distilled_statements",
                }
            )
            continue

        support_excerpts = _normalize_string_list(
            item.get("support_excerpts")
            or item.get("evidence_excerpts")
            or item.get("support_excerpt")
        )
        row = {
            "id": _stable_distillation_id(paragraph_id, batch_id, statements),
            "paragraph_id": paragraph_id,
            "raw_seed_anchor": _paragraph_anchor(paragraph),
            "distilled_statements": statements,
            "statement_count": len(statements),
            "summary": _normalize_whitespace(
                _string(item.get("summary") or item.get("distilled_summary"))
            ),
            "support_excerpts": support_excerpts,
            "provider": provider_token,
            "batch_id": batch_id,
            "status": "ingested",
            "source": DISTILLATION_SOURCE,
            "source_path": source_path,
            "source_content_sha256": source_sha256,
            "ingested_at": _utc_now(),
            "source_line_span": {
                "line_start": paragraph.get("line_start"),
                "line_end": paragraph.get("line_end"),
            },
            "paragraph_fingerprint": _string(
                paragraph.get("paragraph_fingerprint") or paragraph.get("fingerprint")
            ),
        }
        ingested_rows.append(row)

    if not ingested_rows:
        raise ValueError("No valid paragraph distillations found in the input payload")

    distillations_path = repo_root / family_raw_seed_distillations_path(family_dir)
    existing_payload = _load_json(distillations_path) or _default_distillations_payload(
        family_token=family_token,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
    )
    merged_rows = _merge_rows_by_id(
        existing_payload.get("distillations") or [],
        ingested_rows,
    )
    batch_record = {
        "id": batch_id,
        "provider": provider_token,
        "source": DISTILLATION_SOURCE,
        "source_path": source_path,
        "source_content_sha256": source_sha256,
        "ingested_at": _utc_now(),
        "paragraph_ids": sorted({_string(row.get("paragraph_id")) for row in ingested_rows if _string(row.get("paragraph_id"))}),
        "distillation_count": len(ingested_rows),
    }
    merged_batches = _merge_rows_by_id(existing_payload.get("batches") or [], [batch_record])

    envelope = dict(existing_payload)
    envelope.update(
        {
            "kind": "raw_seed_distillations",
            "schema_version": RAW_SEED_DISTILLATIONS_SCHEMA_VERSION,
            "generated_at": _utc_now(),
            "family_id": _string(raw_seed_payload.get("family_id")) or family_token,
            "family_number": _string(raw_seed_payload.get("family_number")) or family_token,
            "family_title": _string(raw_seed_payload.get("family_title")),
            "family_dir": family_dir,
            "source_paths": {
                "raw_seed_json_path": raw_seed_json_path_for_family(family_dir),
                "extracted_shards_path": family_extracted_shards_path(family_dir),
                "input_path": source_path,
            },
            "batches": merged_batches,
            "distillations": merged_rows,
            "stats": {
                "distillation_count": len(merged_rows),
                "paragraph_count": len(
                    {
                        _string(row.get("paragraph_id"))
                        for row in merged_rows
                        if _string(row.get("paragraph_id"))
                    }
                ),
            },
        }
    )
    _write_json(distillations_path, envelope)

    return {
        "family": family_token,
        "family_dir": family_dir,
        "provider": provider_token,
        "batch_id": batch_id,
        "input_path": source_path,
        "raw_seed_distillations_path": family_raw_seed_distillations_path(family_dir),
        "ingested_distillations": len(ingested_rows),
        "total_distillations": len(merged_rows),
        "rejected_items": rejected_items,
    }


def atomize_family_raw_seed(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    limit: int | None = None,
    paragraph_id: str | None = None,
    selection_mode: str = DEFAULT_ATOMIZE_SELECTION_MODE,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(f"Could not resolve family dir for family={family_token!r}")

    raw_seed_payload_path = repo_root / _seed_json_path_for_substrate(family_dir, substrate=substrate)
    raw_seed_payload = _load_json(raw_seed_payload_path)
    if not raw_seed_payload:
        raise FileNotFoundError(f"{substrate}.json missing for family {family_token}")
    raw_seed_shards_payload = _seed_shards_payload_for_substrate(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        substrate=substrate,
    )

    extracted_path = repo_root / family_extracted_shards_path(family_dir)
    existing_extracted = _load_json(extracted_path) or {"shards": []}
    existing_shards = [
        shard for shard in existing_extracted.get("shards") or [] if isinstance(shard, Mapping)
    ]
    ledger_payload = _load_atomization_ledger_payload(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_rows=existing_shards,
        persist=True,
    )
    distillations_payload = _load_json(repo_root / family_raw_seed_distillations_path(family_dir)) or {}
    latest_distillations = _latest_distillations_by_paragraph(distillations_payload)
    applied_alchemy_forms = _load_applied_alchemy_forms_for_family(
        family=family_token,
        repo_root=repo_root,
    )

    requested_cohort_size = max(1, int(limit if limit is not None else cohort_size))
    selection_mode_token = _normalize_selection_mode(
        selection_mode,
        default=DEFAULT_ATOMIZE_SELECTION_MODE,
    )
    selected_bins = _select_bin_rows(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_shards=existing_shards,
        atomization_ledger_payload=ledger_payload,
        cohort_size=requested_cohort_size,
        selection_mode=selection_mode_token,
        paragraph_id=paragraph_id,
    )
    paragraphs_by_id = _paragraph_index(raw_seed_payload)

    new_shards: list[dict[str, Any]] = []
    touched_paragraph_ids: list[str] = []
    touched_bin_ids: list[str] = []
    distillation_backed_count = 0
    paragraphs_table = (
        ledger_payload.get("paragraphs")
        if isinstance(ledger_payload.get("paragraphs"), Mapping)
        else {}
    )
    attempted_at = _utc_now()
    for bin_row in selected_bins:
        paragraph_id_token = _string(bin_row.get("parent_paragraph_id"))
        if not paragraph_id_token:
            continue
        paragraph = paragraphs_by_id.get(paragraph_id_token)
        if not paragraph:
            continue
        paragraph_distillation = latest_distillations.get(paragraph_id_token)
        built = _build_atomized_shards(
            paragraph,
            source_bin_id=_string(bin_row.get("shard_id")),
            distillation=paragraph_distillation,
            alchemy_forms=applied_alchemy_forms,
        )
        if not built:
            continue
        new_shards.extend(built)
        touched_paragraph_ids.append(paragraph_id_token)
        touched_bin_ids.append(_string(bin_row.get("shard_id")))
        if paragraph_distillation:
            distillation_backed_count += 1

    envelope = dict(existing_extracted)
    envelope["source_content_sha256"] = hashlib.sha256(raw_seed_payload_path.read_bytes()).hexdigest()
    touched_set = {paragraph_id for paragraph_id in touched_paragraph_ids if paragraph_id}
    if touched_set:
        surface_updates = _apply_touched_atomization_surface_updates(
            repo_root=repo_root,
            family_token=family_token,
            family_dir=family_dir,
            raw_seed_payload=raw_seed_payload,
            raw_seed_shards_payload=raw_seed_shards_payload,
            extracted_payload=envelope,
            replacement_rows=new_shards,
            touched_paragraph_ids=touched_set,
            source=ATOMIZATION_SOURCE,
            merge_note=(
                f"Atomized {len(touched_set)} paragraph(s) into {len(new_shards)} shard row(s) "
                f"using {ATOMIZATION_SOURCE}."
            ),
        )
        merged_shards = surface_updates["merged_rows"]
        coverage = surface_updates["coverage_payload"]
        dropped_review_proposals = int(surface_updates["dropped_review_proposals"] or 0)
        replaced_rows = surface_updates["replaced_rows"]
    else:
        merged_shards = existing_shards
        coverage = _load_json(repo_root / family_raw_seed_coverage_path(family_dir)) or {
            "counts": {"paragraphs_without_atoms": 0}
        }
        dropped_review_proposals = 0
        replaced_rows = []

    for paragraph_id_token in touched_set:
        paragraph = paragraphs_by_id.get(paragraph_id_token) or {}
        current = dict(paragraphs_table.get(paragraph_id_token) or {})
        current.update(
            {
                "paragraph_id": paragraph_id_token,
                "status": "success",
                "imported_shard_count": len(
                    [
                        row
                        for row in new_shards
                        if _string(row.get("parent_paragraph_id")) == paragraph_id_token
                    ]
                ),
                "source_bin_id": next(
                    (
                        _string(row.get("source_bin_id"))
                        for row in new_shards
                        if _string(row.get("parent_paragraph_id")) == paragraph_id_token
                        and _string(row.get("source_bin_id"))
                    ),
                    _string(current.get("source_bin_id")),
                ),
                "last_attempted_at": attempted_at,
                "last_succeeded_at": attempted_at,
                "observe_id": None,
                "latest_group_label": "local_atomize",
                "latest_artifact": family_extracted_shards_path(family_dir),
                "error_category": None,
                "error_stage": None,
                "error": None,
                "line_start": paragraph.get("line_start"),
                "line_end": paragraph.get("line_end"),
                "paragraph_fingerprint": _paragraph_fingerprint(paragraph),
            }
        )
        paragraphs_table[paragraph_id_token] = current

    ledger_payload["paragraphs"] = paragraphs_table
    ledger_payload["generated_at"] = _utc_now()
    _recompute_atomization_ledger_counts(
        ledger_payload=ledger_payload,
        raw_seed_payload=raw_seed_payload,
    )
    _write_json(repo_root / family_raw_seed_atomization_ledger_path(family_dir), ledger_payload)

    return {
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate,
        "extracted_shards_path": family_extracted_shards_path(family_dir),
        "raw_seed_atomization_ledger_path": family_raw_seed_atomization_ledger_path(family_dir),
        "raw_seed_coverage_path": family_raw_seed_coverage_path(family_dir),
        "raw_seed_routing_review_path": family_raw_seed_routing_review_path(family_dir),
        "raw_seed_distillations_path": family_raw_seed_distillations_path(family_dir),
        "cohort_size": requested_cohort_size,
        "selection_mode": selection_mode_token,
        "selected_count": len(selected_bins),
        "paragraphs_selected": len(selected_bins),
        "bins_selected": len(selected_bins),
        "paragraph_ids": touched_paragraph_ids,
        "bin_ids": touched_bin_ids,
        "paragraphs_backed_by_distillation": distillation_backed_count,
        "new_shards": len(new_shards),
        "total_shards": len(merged_shards),
        "replaced_existing_rows": len(replaced_rows),
        "dropped_review_proposals": dropped_review_proposals,
        "paragraphs_remaining_without_atoms": coverage["counts"]["paragraphs_without_atoms"],
    }


def import_atomization_session_results(
    *,
    family_dir: str,
    manifest: Mapping[str, Any],
    plan: Mapping[str, Any],
    repo_root: Path = REPO_ROOT,
    observe_id: str | None = None,
    source_plan_path: str | None = None,
) -> dict[str, Any]:
    raw_seed_payload = _load_json(repo_root / raw_seed_json_path_for_family(family_dir)) or {}
    if not raw_seed_payload:
        raise FileNotFoundError(f"raw_seed.json missing for family dir {family_dir}")
    family_token = _string(raw_seed_payload.get("family_number")) or _string(raw_seed_payload.get("family_id")) or "09"
    raw_seed_shards_payload = _load_json(repo_root / raw_seed_shards_path_for_family(family_dir)) or {"shards": []}
    source_bin_ids_by_paragraph = {
        _string(bin_row.get("parent_paragraph_id")): _string(bin_row.get("shard_id"))
        for bin_row in (raw_seed_shards_payload.get("shards") or [])
        if isinstance(bin_row, Mapping)
        and _string(bin_row.get("parent_paragraph_id"))
        and _string(bin_row.get("shard_id"))
    }
    extracted_path = repo_root / family_extracted_shards_path(family_dir)
    extracted_payload = _load_json(extracted_path) or {"shards": []}
    existing_rows = [
        shard for shard in (extracted_payload.get("shards") or []) if isinstance(shard, Mapping)
    ]
    ledger_payload = _load_atomization_ledger_payload(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_rows=existing_rows,
        persist=True,
    )

    paragraph_by_label = _atomization_plan_paragraph_ids(repo_root=repo_root, plan=plan)
    imported_rows: list[dict[str, Any]] = []
    artifact_paths_rel: list[str] = []
    successful_paragraph_ids: set[str] = set()
    retryable_paragraph_ids: set[str] = set()
    failed_paragraph_ids: set[str] = set()
    imported_group_labels: list[str] = []
    observed_groups = manifest.get("groups") if isinstance(manifest.get("groups"), list) else []
    paragraphs_table = ledger_payload.get("paragraphs") if isinstance(ledger_payload.get("paragraphs"), Mapping) else {}
    attempted_at = _utc_now()
    applied_alchemy_forms = _load_applied_alchemy_forms_for_family(
        family=family_token,
        repo_root=repo_root,
    )

    retryable_error_categories = {
        "cdp_socket_error",
        "browser_not_running",
        "provider_cancelled",
        "provider_selector_failure",
        "stale_after_900s",
        "submit_button_disabled",
        "tab_not_responsive",
    }

    for group in observed_groups:
        if not isinstance(group, Mapping):
            continue
        role = _string(group.get("role")).strip().lower() or "probe"
        if role != "probe":
            continue
        label = _string(group.get("label")).strip()
        if not label:
            continue
        paragraph_id = _string(paragraph_by_label.get(label)).strip()
        response_status = _string(group.get("response_status") or group.get("runtime_state")).strip().lower()
        error_category = _string(group.get("response_error_category")).strip()
        error_stage = _string(group.get("response_error_stage")).strip()
        error_detail = _string(group.get("response_error") or group.get("error")).strip()

        candidate_artifacts = [
            _string(group.get("response_receipt_file")),
            _string(group.get("response_surface_file")),
            _string(group.get("response_file")),
            _string(group.get("artifact_path")),
        ]

        imported_this_group: list[dict[str, Any]] = []
        source_artifact_rel = ""
        if response_status == "success":
            for artifact_rel in candidate_artifacts:
                if not artifact_rel:
                    continue
                artifact_path = (repo_root / artifact_rel).resolve()
                payload = _load_observe_artifact_payload(artifact_path)
                if not isinstance(payload, Mapping):
                    continue
                imported_this_group = _normalize_atomized_shards(
                    raw_seed_payload=raw_seed_payload,
                    shards_payload=payload,
                    source_artifact_rel=_relative_repo_path(repo_root, artifact_path),
                    source_bin_ids_by_paragraph=source_bin_ids_by_paragraph,
                    alchemy_forms=applied_alchemy_forms,
                )
                if imported_this_group:
                    source_artifact_rel = _relative_repo_path(repo_root, artifact_path)
                    break

        if imported_this_group:
            imported_rows.extend(imported_this_group)
            imported_group_labels.append(label)
            artifact_paths_rel.append(source_artifact_rel)
            paragraph_id = paragraph_id or _string(imported_this_group[0].get("parent_paragraph_id")).strip()
            if paragraph_id:
                successful_paragraph_ids.add(paragraph_id)
                current = dict(paragraphs_table.get(paragraph_id) or {})
                current.update(
                    {
                        "paragraph_id": paragraph_id,
                        "status": "success",
                        "imported_shard_count": len(
                            [
                                row
                                for row in imported_this_group
                                if _string(row.get("parent_paragraph_id")) == paragraph_id
                            ]
                        ),
                        "source_bin_id": _string(source_bin_ids_by_paragraph.get(paragraph_id)),
                        "last_attempted_at": attempted_at,
                        "last_succeeded_at": attempted_at,
                        "observe_id": _string(observe_id) or _string(manifest.get("observe_id")) or None,
                        "latest_group_label": label,
                        "latest_artifact": source_artifact_rel or None,
                        "error_category": None,
                        "error_stage": None,
                        "error": None,
                        "source_plan_path": _string(source_plan_path) or None,
                    }
                )
                paragraphs_table[paragraph_id] = current
            continue

        if not paragraph_id:
            continue
        current = dict(paragraphs_table.get(paragraph_id) or {})
        if _string(current.get("status")).strip().lower() == "success":
            current["last_attempted_at"] = attempted_at
            current["latest_group_label"] = label
            current["observe_id"] = _string(observe_id) or _string(manifest.get("observe_id")) or None
            paragraphs_table[paragraph_id] = current
            continue

        status = "retryable" if error_category in retryable_error_categories else "failed"
        current.update(
            {
                "paragraph_id": paragraph_id,
                "status": status,
                "imported_shard_count": int(current.get("imported_shard_count") or 0),
                "source_bin_id": _string(source_bin_ids_by_paragraph.get(paragraph_id)),
                "last_attempted_at": attempted_at,
                "observe_id": _string(observe_id) or _string(manifest.get("observe_id")) or None,
                "latest_group_label": label,
                "latest_artifact": source_artifact_rel or None,
                "error_category": error_category or ("missing_valid_payload" if response_status == "success" else None),
                "error_stage": error_stage or None,
                "error": error_detail or None,
                "source_plan_path": _string(source_plan_path) or None,
            }
        )
        paragraphs_table[paragraph_id] = current
        if status == "retryable":
            retryable_paragraph_ids.add(paragraph_id)
        else:
            failed_paragraph_ids.add(paragraph_id)

    ledger_payload["paragraphs"] = paragraphs_table

    touched_paragraph_ids = {
        _string(row.get("parent_paragraph_id"))
        for row in imported_rows
        if _string(row.get("parent_paragraph_id"))
    }
    replaced_rows: list[dict[str, Any]] = []
    dropped_review_proposals = 0

    if touched_paragraph_ids:
        surface_updates = _apply_touched_atomization_surface_updates(
            repo_root=repo_root,
            family_token=_string(raw_seed_payload.get("family_number")) or _string(raw_seed_payload.get("family_id")) or "09",
            family_dir=family_dir,
            raw_seed_payload=raw_seed_payload,
            raw_seed_shards_payload=raw_seed_shards_payload,
            extracted_payload=extracted_payload,
            replacement_rows=imported_rows,
            touched_paragraph_ids=touched_paragraph_ids,
            source=ATOMIZATION_BRIDGE_SOURCE,
            merge_note=(
                f"Imported {len(imported_rows)} bridge atomized shard row(s) across "
                f"{len(touched_paragraph_ids)} paragraph(s) from {len(artifact_paths_rel)} artifact(s)."
            ),
        )
        replaced_rows = surface_updates["replaced_rows"]
        dropped_review_proposals = int(surface_updates["dropped_review_proposals"] or 0)

    ledger_payload["generated_at"] = _utc_now()
    _recompute_atomization_ledger_counts(
        ledger_payload=ledger_payload,
        raw_seed_payload=raw_seed_payload,
    )
    ledger_path = repo_root / family_raw_seed_atomization_ledger_path(family_dir)
    _write_json(ledger_path, ledger_payload)

    counts = ledger_payload.get("counts") if isinstance(ledger_payload.get("counts"), Mapping) else {}
    selected_plan_paragraph_ids = sorted(
        {
            paragraph_id
            for paragraph_id in paragraph_by_label.values()
            if _string(paragraph_id)
        }
    )
    remaining_plan_paragraph_ids = [
        paragraph_id
        for paragraph_id in selected_plan_paragraph_ids
        if _string((paragraphs_table.get(paragraph_id) or {}).get("status")).strip().lower() != "success"
    ]
    return {
        "status": "completed",
        "observe_id": _string(observe_id) or _string(manifest.get("observe_id")) or None,
        "imported_shards": len(imported_rows),
        "imported_paragraphs": len(touched_paragraph_ids),
        "selected_plan_paragraph_ids": selected_plan_paragraph_ids,
        "successful_paragraph_ids": sorted(successful_paragraph_ids),
        "retryable_paragraph_ids": sorted(retryable_paragraph_ids - successful_paragraph_ids),
        "failed_paragraph_ids": sorted(failed_paragraph_ids - successful_paragraph_ids),
        "remaining_plan_paragraph_ids": remaining_plan_paragraph_ids,
        "remaining_plan_paragraphs": len(remaining_plan_paragraph_ids),
        "imported_group_labels": imported_group_labels,
        "artifact_paths": sorted(set(artifact_paths_rel)),
        "replaced_existing_rows": len(replaced_rows),
        "dropped_review_proposals": dropped_review_proposals,
        "ledger_path": family_raw_seed_atomization_ledger_path(family_dir),
        "extracted_shards_path": family_extracted_shards_path(family_dir),
        "raw_seed_routing_review_path": family_raw_seed_routing_review_path(family_dir),
        "raw_seed_coverage_path": family_raw_seed_coverage_path(family_dir),
        "remaining_pending_paragraphs": int(counts.get("remaining_pending_paragraphs") or 0),
        "success_count": int(counts.get("success") or 0),
        "retryable_count": int(counts.get("retryable") or 0),
        "failed_count": int(counts.get("failed") or 0),
    }


def build_atomization_redrive_plan(
    *,
    family_dir: str,
    plan_path: str | Path,
    repo_root: Path = REPO_ROOT,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_plan_path = Path(plan_path)
    if not resolved_plan_path.is_absolute():
        resolved_plan_path = (repo_root / resolved_plan_path).resolve()
    plan_payload = _load_json(resolved_plan_path)
    if not plan_payload:
        raise FileNotFoundError(f"Atomization mission plan missing: {resolved_plan_path}")

    raw_seed_payload = _load_json(repo_root / raw_seed_json_path_for_family(family_dir)) or {}
    raw_seed_shards_payload = _load_json(repo_root / raw_seed_shards_path_for_family(family_dir)) or {"shards": []}
    extracted_payload = _load_json(repo_root / family_extracted_shards_path(family_dir)) or {"shards": []}
    ledger_payload = _load_atomization_ledger_payload(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_rows=[
            shard for shard in (extracted_payload.get("shards") or []) if isinstance(shard, Mapping)
        ],
        persist=True,
    )
    paragraph_rows = ledger_payload.get("paragraphs") if isinstance(ledger_payload.get("paragraphs"), Mapping) else {}
    paragraph_by_label = _atomization_plan_paragraph_ids(repo_root=repo_root, plan=plan_payload)

    pending_probe_groups: list[dict[str, Any]] = []
    pending_paragraph_ids: list[str] = []
    successful_paragraph_ids: list[str] = []
    deferred_groups: list[dict[str, Any]] = []
    pending_probe_labels: list[str] = []

    for group in plan_payload.get("groups") or []:
        if not isinstance(group, Mapping):
            continue
        role = _string(group.get("role")).strip().lower() or "probe"
        label = _string(group.get("label")).strip()
        if role == "probe":
            paragraph_id = _string(paragraph_by_label.get(label)).strip()
            status = _string((paragraph_rows.get(paragraph_id) or {}).get("status")).strip().lower()
            if paragraph_id and status == "success":
                successful_paragraph_ids.append(paragraph_id)
                continue
            pending_probe_groups.append(dict(group))
            pending_probe_labels.append(label)
            if paragraph_id:
                pending_paragraph_ids.append(paragraph_id)
            continue
        deferred_groups.append(dict(group))

    if not pending_probe_groups:
        return {
            "status": "noop",
            "plan_path": _relative_repo_path(repo_root, resolved_plan_path),
            "pending_probe_count": 0,
            "pending_paragraph_ids": [],
            "successful_paragraph_ids": sorted(set(successful_paragraph_ids)),
        }

    filtered_groups = list(pending_probe_groups)
    for group in deferred_groups:
        role = _string(group.get("role")).strip().lower()
        if role in {"synthesis", "evaluation"}:
            group["depends_on"] = list(pending_probe_labels)
        filtered_groups.append(group)

    redrive_payload = dict(plan_payload)
    redrive_payload["drafted_at"] = _utc_now()
    redrive_payload["groups"] = filtered_groups
    redrive_payload["redrive_of_plan"] = _relative_repo_path(repo_root, resolved_plan_path)
    redrive_payload["redrive_pending_paragraph_ids"] = sorted(set(pending_paragraph_ids))
    redrive_payload["redrive_successful_paragraph_ids"] = sorted(set(successful_paragraph_ids))

    resolved_output_path = Path(output_path) if output_path is not None else resolved_plan_path.with_name(
        f"{resolved_plan_path.stem}_pending.json"
    )
    if not resolved_output_path.is_absolute():
        resolved_output_path = (repo_root / resolved_output_path).resolve()
    _write_json(resolved_output_path, redrive_payload)

    return {
        "status": "completed",
        "plan_path": _relative_repo_path(repo_root, resolved_output_path),
        "pending_probe_count": len(pending_probe_groups),
        "pending_probe_labels": pending_probe_labels,
        "pending_paragraph_ids": sorted(set(pending_paragraph_ids)),
        "successful_paragraph_ids": sorted(set(successful_paragraph_ids)),
    }


def preview_routing_selection(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    provider: str = DEFAULT_PROVIDER,
    cohort_size: int = DEFAULT_QUEUE_DEPTH,
    wave_width: Any = DEFAULT_ACTIVE_WORKERS,
    selection_mode: str = DEFAULT_ROUTE_SELECTION_MODE,
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(f"Could not resolve family dir for family={family_token!r}")

    raw_seed_payload = _load_json(repo_root / raw_seed_json_path_for_family(family_dir)) or {}
    raw_seed_shards_payload = _load_json(repo_root / raw_seed_shards_path_for_family(family_dir)) or {"shards": []}
    extracted_payload = _load_json(repo_root / family_extracted_shards_path(family_dir)) or {"shards": []}
    extracted_shards = [dict(shard) for shard in extracted_payload.get("shards") or [] if isinstance(shard, Mapping)]
    selected_bins = _select_bin_rows(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_shards=extracted_shards,
        cohort_size=max(1, int(cohort_size)),
        selection_mode=selection_mode,
        require_pending_routing=True,
    )
    bins_by_parent = _bins_by_parent_paragraph(_bin_rows(raw_seed_shards_payload))
    members_by_bin = _atomized_members_by_bin(extracted_shards, bins_by_parent=bins_by_parent)
    selected_members = [
        member
        for bin_row in selected_bins
        for member in members_by_bin.get(_string(bin_row.get("shard_id")), [])
        if (_string(member.get("routing_state")) or "pending") == "pending"
    ]
    wave_resolution = _resolve_routing_wave_width(
        repo_root=repo_root,
        provider=provider,
        requested_wave_width=wave_width,
    )
    return {
        "family": family_token,
        "family_dir": family_dir,
        "provider": provider,
        "cohort_size": max(1, int(cohort_size)),
        "selection_mode": _normalize_selection_mode(
            selection_mode,
            default=DEFAULT_ROUTE_SELECTION_MODE,
        ),
        "selected_count": len(selected_bins),
        "selected_bin_ids": [
            _string(bin_row.get("shard_id"))
            for bin_row in selected_bins
            if _string(bin_row.get("shard_id"))
        ],
        "selected_shard_ids": [
            _string(shard.get("id"))
            for shard in selected_members
            if _string(shard.get("id"))
        ],
        "wave_width_requested": wave_width,
        "wave_width_effective": wave_resolution.get("effective_wave_width"),
        "provider_ceiling": wave_resolution.get("provider_ceiling"),
        "status": "ready" if selected_bins else "noop",
    }


def _member_routing_proposal(
    *,
    shard: dict[str, Any],
    source_bin_id: str,
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    enriched_shard = enrich_shard_routing_metadata(shard)
    decision_name = _string(decision.get("decision")) or "surface_to_codex"
    shard_id = _string(enriched_shard.get("id"))
    proposal_seed = f"{shard_id}:{decision_name}".encode("utf-8")
    proposal_id = f"rr_{hashlib.sha1(proposal_seed).hexdigest()[:12]}"
    proposal = {
        "id": proposal_id,
        "source_bin_id": source_bin_id,
        "shard_id": shard_id,
        "parent_paragraph_id": _string(enriched_shard.get("parent_paragraph_id")),
        "primary_review_plane": _string(enriched_shard.get("primary_review_plane")),
        "primary_review_plane_score": int(enriched_shard.get("primary_review_plane_score") or 0),
        "synthesis_role": _string(enriched_shard.get("synthesis_role")),
        "review_plane_hints": list(enriched_shard.get("review_plane_hints") or [])[:4],
        "decision": decision_name,
        "confidence": float(decision.get("confidence") or 0),
        "status": "pending_review",
        "source_substrate": _string(enriched_shard.get("source_substrate")) or "raw_seed",
        "authored_by": _string(enriched_shard.get("authored_by"))
        or _default_authored_by_for_substrate(_string(enriched_shard.get("source_substrate")) or "raw_seed"),
        "candidate_targets": decision.get("candidate_targets") or [],
    }
    if decision_name == "route_to_existing":
        target = dict(decision.get("target") or {})
        proposal["target"] = {
            "kind": _string(target.get("kind")),
            "id": _string(target.get("id")),
            "title": _string(target.get("title")),
            "confidence": float(decision.get("confidence") or 0),
            "review_required": True,
            "forward_gloss": _string(decision.get("forward_gloss")),
            "reverse_gloss": _string(decision.get("reverse_gloss")),
        }
    elif decision_name == "propose_new":
        proposal.update(
            {
                "proposed_kind": _string(decision.get("proposed_kind")),
                "proposed_slug": _string(decision.get("proposed_slug")),
                "seed_statement": _string(decision.get("seed_statement")),
                "why_no_existing_fits": _string(decision.get("why_no_existing_fits")),
            }
        )
    else:
        proposal.update(
            {
                "reason": _string(decision.get("reason")),
                "missing_context_hypothesis": _string(decision.get("missing_context_hypothesis")),
            }
        )
    return proposal


def _review_envelope_for_bin(
    *,
    bin_row: Mapping[str, Any],
    member_proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    source_bin_id = _string(bin_row.get("shard_id"))
    envelope_id = f"rr_bin_{hashlib.sha1(source_bin_id.encode('utf-8')).hexdigest()[:12]}"
    source_substrate = (
        _string(bin_row.get("source_substrate"))
        or _string((member_proposals[0] if member_proposals else {}).get("source_substrate"))
        or "raw_seed"
    )
    return {
        "id": envelope_id,
        "source_bin_id": source_bin_id,
        "parent_paragraph_id": _string(bin_row.get("parent_paragraph_id")),
        "source_substrate": source_substrate,
        "authored_by": _string(bin_row.get("authored_by"))
        or _string((member_proposals[0] if member_proposals else {}).get("authored_by"))
        or _default_authored_by_for_substrate(source_substrate),
        "sibling_bin_ids": [
            _string(item)
            for item in (bin_row.get("sibling_shard_ids") or [])
            if _string(item)
        ],
        "member_atom_ids": [
            _string(member.get("shard_id"))
            for member in member_proposals
            if _string(member.get("shard_id"))
        ],
        "member_count": len(member_proposals),
        "status": "pending_review" if member_proposals else "completed",
        "member_proposals": member_proposals,
    }


def route_family_atomized_shards(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    provider: str = DEFAULT_PROVIDER,
    cohort_size: int = DEFAULT_QUEUE_DEPTH,
    wave_width: Any = DEFAULT_ACTIVE_WORKERS,
    queue_depth: int | None = None,
    active_workers: Any | None = None,
    selection_mode: str = DEFAULT_ROUTE_SELECTION_MODE,
    packet_path: str | Path | None = None,
    shards_group: str | None = None,
    shards_query: str | None = None,
    shards_related_limit: int = 20,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(f"Could not resolve family dir for family={family_token!r}")

    raw_seed_payload = _load_json(repo_root / _seed_json_path_for_substrate(family_dir, substrate=substrate)) or {}
    raw_seed_shards = _seed_shards_payload_for_substrate(
        repo_root=repo_root,
        family_dir=family_dir,
        raw_seed_payload=raw_seed_payload,
        substrate=substrate,
    )
    extracted_path = repo_root / family_extracted_shards_path(family_dir)
    extracted_payload = _load_json(extracted_path) or {"shards": []}
    extracted_shards = [dict(shard) for shard in extracted_payload.get("shards") or [] if isinstance(shard, Mapping)]
    principles_payload = _load_json(repo_root / raw_seed_principles_path_for_family(family_dir)) or {"principles": []}

    doctrine_nodes = _family_principle_nodes(principles_payload) + _top_doctrine_nodes(repo_root)
    requested_cohort_size = max(1, int(queue_depth if queue_depth is not None else cohort_size))
    requested_wave_width = active_workers if active_workers is not None else wave_width
    selection_mode_token = _normalize_selection_mode(
        selection_mode,
        default=DEFAULT_ROUTE_SELECTION_MODE,
    )
    selection_inputs = [
        bool(packet_path),
        bool(_string(shards_group)),
        bool(_string(shards_query)),
    ]
    if sum(1 for present in selection_inputs if present) > 1:
        raise ValueError("--packet-path, --shards-group, and --shards-query are mutually exclusive")

    wave_resolution = _resolve_routing_wave_width(
        repo_root=repo_root,
        provider=provider,
        requested_wave_width=requested_wave_width,
    )
    if _string(wave_resolution.get("status")) != "ok":
        return {
            "ok": False,
            "status": "rejected",
            "family": family_token,
            "family_dir": family_dir,
            "provider": provider,
            "cohort_size": requested_cohort_size,
            "selection_mode": selection_mode_token,
            "wave_width_requested": requested_wave_width,
            "wave_width_effective": None,
            "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
            "error_code": _string(wave_resolution.get("error_code")) or None,
            "error": (
                f"wave_width {requested_wave_width} exceeds provider_ceiling "
                f"{wave_resolution.get('provider_ceiling')} for provider '{provider}'"
                if _string(wave_resolution.get("error_code")) == "wave_width_exceeds_provider_ceiling"
                else "invalid wave_width request"
            ),
            "queue_depth": requested_cohort_size,
            "requested_active_workers": requested_wave_width,
            "effective_active_workers": None,
            "safe_parallelism": int(wave_resolution.get("provider_ceiling") or 0),
        }

    paragraph_level_shards = _bin_rows(raw_seed_shards)
    bins_by_parent = _bins_by_parent_paragraph(paragraph_level_shards)
    atomized_by_bin = _atomized_members_by_bin(extracted_shards, bins_by_parent=bins_by_parent)
    selection_payload = _resolve_route_review_selection(
        repo_root=repo_root,
        extracted_path=extracted_path,
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards,
        extracted_shards=extracted_shards,
        requested_cohort_size=requested_cohort_size,
        selection_mode=selection_mode_token,
        packet_path=packet_path,
        shards_group=shards_group,
        shards_query=shards_query,
        shards_related_limit=shards_related_limit,
    )
    selected_bins = list(selection_payload.get("selected_bins") or [])
    selected_members = list(selection_payload.get("selected_members") or [])
    selection_context = dict(selection_payload.get("selection_context") or {})
    shard_synthesis = (
        dict(selection_context.get("shard_synthesis"))
        if isinstance(selection_context.get("shard_synthesis"), Mapping)
        else {}
    )
    review_plane_work_queue = _review_plane_work_queue(selection_context)
    selected_bin_ids = {
        _string(bin_row.get("shard_id")) for bin_row in selected_bins if _string(bin_row.get("shard_id"))
    }

    new_envelopes: list[dict[str, Any]] = []
    member_proposal_count = 0
    for bin_row in selected_bins:
        bin_id = _string(bin_row.get("shard_id"))
        member_proposals: list[dict[str, Any]] = []
        for shard in extracted_shards:
            shard_bin_id = _source_bin_id_for_shard(shard, bins_by_parent=bins_by_parent)
            if shard_bin_id != bin_id:
                continue
            if (_string(shard.get("routing_state")) or "pending") != "pending":
                continue
            decision = _routing_decision_for_shard(shard, doctrine_nodes)
            decision_name = _string(decision.get("decision")) or "surface_to_codex"
            if decision_name == "route_to_existing":
                target = dict(decision.get("target") or {})
                shard["routing_state"] = "proposed_existing"
                shard["coverage_state"] = "needs_review"
                shard["routing_targets"] = [
                    {
                        "kind": _string(target.get("kind")),
                        "id": _string(target.get("id")),
                        "title": _string(target.get("title")),
                        "confidence": float(decision.get("confidence") or 0),
                        "review_required": True,
                        "forward_gloss": _string(decision.get("forward_gloss")),
                        "reverse_gloss": _string(decision.get("reverse_gloss")),
                    }
                ]
            elif decision_name == "propose_new":
                shard["routing_state"] = "proposed_new"
                shard["coverage_state"] = "needs_review"
                shard["routing_targets"] = []
            else:
                shard["routing_state"] = "needs_codex"
                shard["coverage_state"] = "needs_codex"
                shard["routing_targets"] = []
            member_proposals.append(
                _member_routing_proposal(
                    shard=shard,
                    source_bin_id=bin_id,
                    decision=decision,
                )
            )
        if member_proposals:
            member_proposal_count += len(member_proposals)
            new_envelopes.append(
                _review_envelope_for_bin(
                    bin_row=bin_row,
                    member_proposals=member_proposals,
                )
            )

    extracted_payload = dict(extracted_payload)
    extracted_payload["shards"] = extracted_shards
    extracted_payload["browser_index"] = _browser_index_for_shards(extracted_shards)
    extracted_payload["extracted_at"] = _utc_now()
    extracted_payload["merge_note"] = (
        f"Updated routing review state for {len(new_envelopes)} bin(s) / {member_proposal_count} atom(s) under provider-safe batch policy."
    )

    provider_ceiling = int(wave_resolution.get("provider_ceiling") or _safe_parallelism(repo_root, provider))
    effective_active_workers = int(wave_resolution.get("effective_wave_width") or DEFAULT_ACTIVE_WORKERS)
    review_path = repo_root / family_raw_seed_routing_review_path(family_dir)
    existing_review_payload = normalize_routing_review_payload(
        _load_json(review_path) or {},
        raw_seed_shards_payload=raw_seed_shards,
        extracted_shards_payload=extracted_payload,
    )
    carried_envelopes = [
        dict(proposal)
        for proposal in existing_review_payload.get("proposals") or []
        if isinstance(proposal, Mapping)
        and _string(proposal.get("source_bin_id")) not in selected_bin_ids
    ]
    merged_envelopes = [*carried_envelopes, *new_envelopes]
    pending_review_members = [
        member
        for envelope in merged_envelopes
        for member in (envelope.get("member_proposals") or [])
        if isinstance(member, Mapping) and _proposal_is_pending_review(member)
    ]
    pending_review_bins = [
        envelope
        for envelope in merged_envelopes
        if _proposal_is_pending_review(envelope)
    ]
    proposal_plane_bins = _proposal_plane_bins(
        merged_envelopes,
        review_plane_work_queue=review_plane_work_queue,
    )
    routing_stats = _normalized_review_payload_stats(merged_envelopes, extracted_shards)
    review_payload = {
        "kind": "raw_seed_routing_review",
        "schema_version": RAW_SEED_ROUTING_REVIEW_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "family_id": _string(raw_seed_payload.get("family_id")) or family_token,
        "family_number": _string(raw_seed_payload.get("family_number")) or family_token,
        "family_title": _string(raw_seed_payload.get("family_title")),
        "family_dir": family_dir,
        "source_paths": {
            "extracted_shards_path": family_extracted_shards_path(family_dir),
            "raw_seed_shards_path": raw_seed_shards_path_for_family(family_dir),
            "raw_seed_coverage_path": family_raw_seed_coverage_path(family_dir),
            "raw_seed_principles_path": raw_seed_principles_path_for_family(family_dir),
        },
        "dispatch_policy": {
            "provider": provider,
            "cohort_size": requested_cohort_size,
            "wave_width_requested": requested_wave_width,
            "wave_width_effective": effective_active_workers,
            "provider_ceiling": provider_ceiling,
            "provider_ceiling_source": "tools/meta/bridge/provider_capabilities.json",
            "queue_depth": requested_cohort_size,
            "requested_active_workers": int(effective_active_workers if requested_wave_width == "auto" else requested_wave_width),
            "effective_active_workers": effective_active_workers,
            "safe_parallelism": provider_ceiling,
            "safe_parallelism_source": "tools/meta/bridge/provider_capabilities.json",
            "review_threshold": ROUTING_REVIEW_THRESHOLD,
        },
        "selection_context": selection_context,
        "shard_synthesis": shard_synthesis,
        "review_plane_work_queue": review_plane_work_queue,
        "proposal_plane_bins": proposal_plane_bins,
        "stats": {
            "selected_pending_bins": len(selected_bins),
            "selected_pending_shards": len(selected_members),
            "pending_review": len(pending_review_members),
            "pending_review_bins": len(pending_review_bins),
            "route_to_existing": routing_stats.get("route_to_existing", 0),
            "propose_new": routing_stats.get("propose_new", 0),
            "surface_to_codex": routing_stats.get("surface_to_codex", 0),
            "remaining_pending_shards": routing_stats.get("remaining_pending_shards", 0),
            "remaining_pending_bins": sum(
                1
                for bin_row in paragraph_level_shards
                if any(
                    (_string(member.get("routing_state")) or "pending") == "pending"
                    for member in atomized_by_bin.get(_string(bin_row.get("shard_id")), [])
                )
            ),
            "source_substrate_counts": dict(routing_stats.get("source_substrate_counts") or {}),
            "authored_by_counts": dict(routing_stats.get("authored_by_counts") or {}),
        },
        "proposals": merged_envelopes,
    }
    _write_json(review_path, review_payload)
    _write_json(extracted_path, extracted_payload)

    coverage = build_raw_seed_coverage(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards,
        extracted_shards_payload=extracted_payload,
        principles_payload=principles_payload,
        routing_review_payload=review_payload,
    )
    review_payload["stats"]["pending_review"] = int(coverage.get("counts", {}).get("review_queue_entries") or 0)
    review_payload["stats"]["pending_review_bins"] = int(coverage.get("counts", {}).get("review_queue_bins") or 0)
    review_payload["stats"]["remaining_pending_shards"] = int(coverage.get("counts", {}).get("pending_routing_shards") or 0)
    review_payload["stats"]["remaining_pending_bins"] = int(coverage.get("counts", {}).get("pending_routing_bins") or 0)
    review_payload["proposal_plane_bins"] = _proposal_plane_bins(
        merged_envelopes,
        review_plane_work_queue=review_plane_work_queue,
    )
    coverage_path = repo_root / family_raw_seed_coverage_path(family_dir)
    _write_json(review_path, review_payload)
    _write_json(coverage_path, coverage)

    return {
        "ok": True,
        "status": "completed" if selected_bins else "noop",
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate,
        "provider": provider,
        "cohort_size": requested_cohort_size,
        "selection_mode": selection_mode_token,
        "selection_kind": _string(selection_context.get("selection_kind")) or "selection_mode",
        "selection_context": selection_context,
        "shard_synthesis": shard_synthesis,
        "review_plane_work_queue": review_plane_work_queue,
        "proposal_plane_bins": proposal_plane_bins,
        "selected_count": len(selected_bins),
        "selected_bin_count": len(selected_bins),
        "wave_width_requested": requested_wave_width,
        "wave_width_effective": effective_active_workers,
        "provider_ceiling": provider_ceiling,
        "queue_depth": requested_cohort_size,
        "requested_active_workers": int(effective_active_workers if requested_wave_width == "auto" else requested_wave_width),
        "effective_active_workers": effective_active_workers,
        "safe_parallelism": provider_ceiling,
        "selected_pending_bins": len(selected_bins),
        "selected_pending_shards": len(selected_members),
        "pending_review": len(pending_review_members),
        "pending_review_bins": len(pending_review_bins),
        "remaining_pending_shards": review_payload["stats"]["remaining_pending_shards"],
        "remaining_pending_bins": review_payload["stats"]["remaining_pending_bins"],
        "raw_seed_routing_review_path": family_raw_seed_routing_review_path(family_dir),
        "raw_seed_coverage_path": family_raw_seed_coverage_path(family_dir),
    }


def load_raw_seed_pipeline_snapshot(
    repo_root: Path,
    *,
    family_dir: str | None,
    family_number: str | None,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    from system.lib.raw_seed_coverage_enrich import family_enriched_coverage_path
    from system.lib.raw_seed_routing_apply import family_codex_surface_queue_path

    resolved_family_dir = _string(family_dir).strip()
    resolved_family_number = _string(family_number).strip() or "09"
    if not resolved_family_dir:
        family_root = repo_root / "obsidian" / "okay lets do this"
        for candidate in family_root.glob(f"{resolved_family_number}*"):
            if candidate.is_dir():
                resolved_family_dir = candidate.relative_to(repo_root).as_posix()
                break
    if not resolved_family_dir:
        return {}

    raw_seed_payload = _load_json(repo_root / _seed_json_path_for_substrate(resolved_family_dir, substrate=substrate)) or {}
    raw_seed_shards = _seed_shards_payload_for_substrate(
        repo_root=repo_root,
        family_dir=resolved_family_dir,
        raw_seed_payload=raw_seed_payload,
        substrate=substrate,
    )
    extracted = _load_json(repo_root / family_extracted_shards_path(resolved_family_dir)) or {}
    coverage = _load_json(repo_root / family_raw_seed_coverage_path(resolved_family_dir)) or {}
    atomization_ledger = _load_json(repo_root / family_raw_seed_atomization_ledger_path(resolved_family_dir)) or {}
    review = normalize_routing_review_payload(
        _load_json(repo_root / family_raw_seed_routing_review_path(resolved_family_dir)) or {},
        raw_seed_shards_payload=raw_seed_shards,
        extracted_shards_payload=extracted,
    )
    enriched = _load_json(repo_root / family_enriched_coverage_path(resolved_family_dir)) or {}
    surface_queue = _load_json(repo_root / family_codex_surface_queue_path(resolved_family_dir)) or {}
    extracted_shards = [
        shard for shard in extracted.get("shards") or [] if isinstance(shard, Mapping)
    ]
    pending_review_entries = _pending_review_member_proposals(review)
    surface_queue_items = [
        item for item in surface_queue.get("items") or [] if isinstance(item, Mapping)
    ]

    review_dispatch_policy = review.get("dispatch_policy") if isinstance(review.get("dispatch_policy"), Mapping) else {}
    ledger_counts = atomization_ledger.get("counts") if isinstance(atomization_ledger.get("counts"), Mapping) else {}
    provider = _string(review_dispatch_policy.get("provider")) or DEFAULT_PROVIDER
    safe_parallelism = int(_safe_parallelism(repo_root, provider))
    effective_active_workers = int(
        review_dispatch_policy.get("wave_width_effective")
        or review_dispatch_policy.get("effective_active_workers")
        or min(DEFAULT_ACTIVE_WORKERS, safe_parallelism)
    )
    requested_wave_width = review_dispatch_policy.get("wave_width_requested")
    if requested_wave_width in (None, ""):
        requested_wave_width = review_dispatch_policy.get("requested_active_workers") or "auto"
    cohort_size = int(
        review_dispatch_policy.get("cohort_size")
        or review_dispatch_policy.get("queue_depth")
        or DEFAULT_QUEUE_DEPTH
    )

    counts = coverage.get("counts") if isinstance(coverage.get("counts"), Mapping) else {}
    bins_map = coverage.get("bins") if isinstance(coverage.get("bins"), Mapping) else {}
    enriched_totals = enriched.get("totals") if isinstance(enriched.get("totals"), Mapping) else {}
    agent_seed_payload = _load_json(repo_root / agent_seed_json_path_for_family(resolved_family_dir)) or {}
    raw_extracted_shards = [
        shard for shard in extracted_shards if (_string(shard.get("source_substrate")) or "raw_seed") == "raw_seed"
    ]
    agent_extracted_shards = [
        shard for shard in extracted_shards if (_string(shard.get("source_substrate")) or "") == "agent_seed"
    ]
    raw_seed_total_paragraphs = int(counts.get("total_paragraphs") or len(raw_seed_payload.get("paragraphs") or []))
    raw_seed_paragraphs_without_atoms = int(counts.get("paragraphs_without_atoms") or 0)
    agent_seed_total_paragraphs = len(agent_seed_payload.get("paragraphs") or [])
    agent_seed_atomized_paragraphs = len(
        {
            _string(shard.get("parent_paragraph_id"))
            for shard in agent_extracted_shards
            if _string(shard.get("parent_paragraph_id"))
        }
    )
    fresh_pending_bins = _fresh_pending_bin_ids(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards,
        extracted_shards=extracted_shards,
        routing_review_payload=review,
    )
    return {
        "family_dir": resolved_family_dir,
        "family_number": resolved_family_number,
        "substrate": substrate,
        "extracted_shards_path": family_extracted_shards_path(resolved_family_dir),
        "raw_seed_shards_path": raw_seed_shards_path_for_family(resolved_family_dir),
        "raw_seed_coverage_path": family_raw_seed_coverage_path(resolved_family_dir),
        "raw_seed_atomization_ledger_path": family_raw_seed_atomization_ledger_path(resolved_family_dir),
        "raw_seed_coverage_enriched_path": family_enriched_coverage_path(resolved_family_dir),
        "raw_seed_routing_review_path": family_raw_seed_routing_review_path(resolved_family_dir),
        "codex_surface_queue_path": family_codex_surface_queue_path(resolved_family_dir),
        "total_paragraphs": raw_seed_total_paragraphs if substrate == "raw_seed" else int(len(raw_seed_payload.get("paragraphs") or [])),
        "total_bins": int(counts.get("total_bins") or len(raw_seed_shards.get("shards") or [])),
        "paragraph_level_shards": int(counts.get("total_paragraph_level_shards") or len(raw_seed_shards.get("shards") or [])),
        "atomized_shards": int(counts.get("total_atomized_shards") or len(extracted_shards)),
        "paragraphs_without_atoms": raw_seed_paragraphs_without_atoms if substrate == "raw_seed" else max(
            0,
            len(raw_seed_payload.get("paragraphs") or [])
            - len(
                {
                    _string(shard.get("parent_paragraph_id"))
                    for shard in extracted_shards
                    if _string(shard.get("parent_paragraph_id"))
                }
            ),
        ),
        "raw_seed_total_paragraphs": raw_seed_total_paragraphs,
        "raw_seed_atomized_shards": len(raw_extracted_shards),
        "raw_seed_paragraphs_without_atoms": raw_seed_paragraphs_without_atoms,
        "agent_seed_total_paragraphs": agent_seed_total_paragraphs,
        "agent_seed_atomized_shards": len(agent_extracted_shards),
        "agent_seed_paragraphs_without_atoms": max(0, agent_seed_total_paragraphs - agent_seed_atomized_paragraphs),
        "pending_routing_shards": int(
            counts.get("pending_routing_shards")
            or sum(
                1
                for shard in extracted_shards
                if (_string(shard.get("routing_state")) or "pending") == "pending"
            )
        ),
        "pending_routing_bins": int(
            counts.get("pending_routing_bins")
            or sum(
                1
                for bin_card in bins_map.values()
                if isinstance(bin_card, Mapping) and _string(bin_card.get("routing_state")) == "pending"
            )
        ),
        "top_pending_routing_group": (
            dict(coverage.get("top_pending_routing_group") or {})
            if isinstance(coverage.get("top_pending_routing_group"), Mapping)
            else None
        ),
        "pending_routing_groups": [
            dict(item)
            for item in coverage.get("pending_routing_groups") or []
            if isinstance(item, Mapping)
        ],
        "max_pending_routing_group_shards": int(
            counts.get("max_pending_routing_group_shards") or 0
        ),
        "review_queue_entries": int(
            counts.get("review_queue_entries") or len(pending_review_entries)
        ),
        "review_queue_bins": int(
            counts.get("review_queue_bins")
            or sum(
                1
                for bin_card in bins_map.values()
                if isinstance(bin_card, Mapping) and int(bin_card.get("review_member_count") or 0) > 0
            )
        ),
        "fresh_pending_bins": len(fresh_pending_bins),
        "atomization_success_paragraphs": int(ledger_counts.get("success") or 0),
        "atomization_retryable_paragraphs": int(ledger_counts.get("retryable") or 0),
        "atomization_failed_paragraphs": int(ledger_counts.get("failed") or 0),
        "atomization_pending_paragraphs": int(ledger_counts.get("remaining_pending_paragraphs") or 0),
        "surface_queue_entries": len(surface_queue_items),
        "doctrine_with_no_provenance": int(enriched_totals.get("doctrine_with_no_provenance") or 0),
        "merge_candidate_count": int(enriched_totals.get("merge_candidates") or 0),
        "orphan_cluster_count": int(enriched_totals.get("orphan_clusters") or 0),
        "bins": bins_map,
        "provider": provider,
        "cohort_size": cohort_size,
        "wave_width_requested": requested_wave_width,
        "wave_width_effective": effective_active_workers,
        "provider_ceiling": int(safe_parallelism),
        "queue_depth": cohort_size,
        "effective_active_workers": effective_active_workers,
        "safe_parallelism": int(safe_parallelism),
        "last_updated": _string(
            enriched.get("generated_at")
            or surface_queue.get("last_updated_at")
            or coverage.get("generated_at")
            or review.get("last_apply_at")
            or review.get("generated_at")
            or extracted.get("extracted_at")
        ),
    }
