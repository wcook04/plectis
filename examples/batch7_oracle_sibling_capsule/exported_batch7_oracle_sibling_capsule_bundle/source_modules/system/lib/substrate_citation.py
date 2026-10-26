"""
[PURPOSE]
- Teleology: Universal citation syntax for referencing entities across the documentation substrate —
  raw seed paragraphs, sections, sources, idea groups, routes, tags, mechanisms, documentation entries,
  and code files — via compact @kind:id tokens.
- Mechanism: Regex-based parser that extracts, validates, and resolves citation refs against
  raw_seed.json and doc_registry.json payloads.
- Non-goal: Mutating any payload (that belongs to substrate_ops.py).

[INTERFACE]
- parse_citation(token)              -> CitationRef | None
- extract_citations(text)            -> list[CitationRef]
- resolve_citation(ref, context)     -> dict | None
- citation_kinds()                   -> list[str]
- format_citation(kind, id)          -> str

[CITATION SYNTAX]
    @par:<paragraph_id>          paragraph (par_phase_08_raw_seed_042 or shorthand 042)
    @sec:<section_id>            section (sec_source_1_next_ideas or shorthand source_1_next_ideas)
    @src:<source_id>             source document (sec_phase_08_raw_seed__source_1_next_ideas_md)
    @grp:<group_id>              idea group (grp_bridge_native_execution or shorthand bridge_native_execution)
    @route:<route_hash>          claim route (route_ed9c5faf6a7d54e9 or shorthand ed9c5faf6a7d54e9)
    @tag:<tag_name>              tag (bridge, json, observe-apply)
    @mech:<mechanism>            mechanism hint (bridge, kernel, observe_apply)
    @doc:<doc_id>                documentation registry entry (doc_bridge_overview)
    @file:<path>                 code/repo file (system/core/bridge.py)

[DEPENDENCIES]
- Caller-provided raw_seed.json and doc_registry.json payloads for typed citation resolution.

[CONSTRAINTS]
- Pure computation, no I/O. Resolution uses pre-loaded payloads.
- Shorthand expansion is best-effort: if the short form is ambiguous, returns None with a diagnostic.
- When-needed: Open when a kernel or bridge surface needs the canonical `@kind:id` citation grammar and resolution rules instead of hand-parsing raw-seed or doc-registry references.
- Escalates-to: system/lib/kernel/commands/substrate.py; system/lib/substrate_ops.py; system/lib/observe_mission_templates.py
- Navigation-group: kernel_lib

[FLOW]
- Parse and deduplicate @kind:id references, validate supported kinds and resolve identities against supplied raw-seed/doc-registry dictionaries.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, NamedTuple

# ---------------------------------------------------------------------------
# Citation ref
# ---------------------------------------------------------------------------

CITATION_KINDS = ("par", "sec", "src", "grp", "route", "tag", "mech", "doc", "file")

_CITATION_RE = re.compile(
    r"@(par|sec|src|grp|route|tag|mech|doc|file):([^\s,;)\]}>]+)"
)


class CitationRef(NamedTuple):
    """
    [ROLE]
    - Teleology: Immutable record representing one parsed and normalized substrate citation token.
    - Ownership: Owns the kind, raw_id, and canonical_id strings produced by parse_citation or extract_citations.
    - Mutability: Immutable (NamedTuple).
    - Concurrency: Safe to share across threads with no locking.
    """
    kind: str
    raw_id: str
    canonical_id: str  # expanded from shorthand where possible


def citation_kinds() -> list[str]:
    """
    [ACTION]
    - Teleology: Return the ordered list of all valid citation kind prefixes recognized by the parser.
    - Guarantee: Returns a new list copy of CITATION_KINDS on every call.
    - Fails: None.
    """
    return list(CITATION_KINDS)


def format_citation(kind: str, id_value: str) -> str:
    """
    [ACTION]
    - Teleology: Produce the canonical @kind:id citation token string from separate kind and id components.
    - Guarantee: Returns a non-empty string of the form `@kind:id_value` on every call.
    - Fails: None.
    """
    return f"@{kind}:{id_value}"


def parse_citation(token: str) -> CitationRef | None:
    """
    [ACTION]
    - Teleology: Parse one substrate citation token into its normalized reference form.
    - Mechanism: Match the token against the citation regex, accept bare `kind:id` forms by adding `@`, and expand shorthand ids into canonical prefixed ids.
    - Guarantee: Returns a CitationRef with canonical_id expanded where supported, or None when the token is invalid.
    - Fails: None.
    - When-needed: Open when a caller has one citation token and needs the authoritative parse-and-normalize rule before resolution.
    - Escalates-to: system/lib/kernel/commands/substrate.py::cmd_resolve_citation; system/lib/substrate_citation.py::resolve_citation
    """
    token = token.strip()
    m = _CITATION_RE.fullmatch(token)
    if not m:
        # Try without the @ prefix for bare kind:id
        m = _CITATION_RE.fullmatch("@" + token)
    if not m:
        return None
    kind, raw_id = m.group(1), m.group(2)
    canonical = _expand_shorthand(kind, raw_id)
    return CitationRef(kind=kind, raw_id=raw_id, canonical_id=canonical)


def extract_citations(text: str) -> list[CitationRef]:
    """
    [ACTION]
    - Teleology: Recover the unique substrate citations mentioned in one freeform text surface.
    - Mechanism: Scan the text with the shared citation regex, dedupe by raw `(kind, id)` pairs, and emit CitationRef records with shorthand expansion.
    - Guarantee: Returns citation refs in first-seen order with duplicates removed.
    - Fails: None.
    - When-needed: Open when a prompt, note, or bridge artifact may contain multiple substrate citations that need to be harvested before validation or mutation.
    - Escalates-to: system/lib/kernel/commands/substrate.py; system/lib/substrate_citation.py::resolve_citations_batch
    """
    if not text:
        return []
    seen: set[tuple[str, str]] = set()
    results: list[CitationRef] = []
    for m in _CITATION_RE.finditer(text):
        kind, raw_id = m.group(1), m.group(2)
        key = (kind, raw_id)
        if key in seen:
            continue
        seen.add(key)
        canonical = _expand_shorthand(kind, raw_id)
        results.append(CitationRef(kind=kind, raw_id=raw_id, canonical_id=canonical))
    return results


def resolve_citation(
    ref: CitationRef,
    *,
    raw_seed_payload: Mapping[str, Any] | None = None,
    doc_registry_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Resolve one parsed citation against the loaded raw-seed or doc-registry substrate.
    - Mechanism: Dispatch by citation kind to the matching resolver and return a compact target entity dict when the payload contains that entity.
    - Guarantee: Returns a target dict for resolvable citations, a file stub for `@file:...`, or None when the cited entity cannot be found.
    - Fails: None.
    - When-needed: Open when a caller already has a CitationRef and needs the exact substrate-lookup rule before using or mutating the target.
    - Escalates-to: system/lib/kernel/commands/substrate.py::cmd_resolve_citation; system/lib/substrate_ops.py::apply_op_batch
    """
    if ref.kind == "par" and raw_seed_payload:
        return _resolve_paragraph(ref, raw_seed_payload)
    if ref.kind == "sec" and raw_seed_payload:
        return _resolve_section(ref, raw_seed_payload)
    if ref.kind == "src" and raw_seed_payload:
        return _resolve_source(ref, raw_seed_payload)
    if ref.kind == "grp" and raw_seed_payload:
        return _resolve_by_index(ref, raw_seed_payload, "idea_groups_by_id", "grp_")
    if ref.kind == "route" and raw_seed_payload:
        return _resolve_by_index(ref, raw_seed_payload, "routes_by_id", "route_")
    if ref.kind in ("tag", "mech") and raw_seed_payload:
        return _resolve_theme(ref, raw_seed_payload)
    if ref.kind == "doc" and doc_registry_payload:
        return _resolve_doc(ref, doc_registry_payload)
    if ref.kind == "file":
        return {"kind": "file", "path": ref.canonical_id}
    return None


def resolve_citations_batch(
    refs: list[CitationRef],
    *,
    raw_seed_payload: Mapping[str, Any] | None = None,
    doc_registry_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Resolve a citation batch into bridge- and CLI-friendly result envelopes.
    - Mechanism: Reuse resolve_citation() for each ref and emit per-citation records with raw token, canonical token, resolved flag, target kind, and target payload.
    - Guarantee: Returns one result row per input citation in input order.
    - Fails: None.
    - When-needed: Open when a kernel or bridge surface needs a structured batch resolution receipt instead of resolving citations one by one.
    - Escalates-to: system/lib/kernel/commands/substrate.py; system/lib/substrate_citation.py::resolve_citation
    """
    results: list[dict[str, Any]] = []
    for ref in refs:
        target = resolve_citation(
            ref,
            raw_seed_payload=raw_seed_payload,
            doc_registry_payload=doc_registry_payload,
        )
        results.append({
            "citation": format_citation(ref.kind, ref.raw_id),
            "canonical": format_citation(ref.kind, ref.canonical_id),
            "resolved": target is not None,
            "target_kind": ref.kind,
            "target": target,
        })
    return results


# ---------------------------------------------------------------------------
# Shorthand expansion
# ---------------------------------------------------------------------------

_PREFIX_MAP = {
    "par": "par_",
    "sec": "sec_",
    "src": "sec_",
    "grp": "grp_",
    "route": "route_",
    "doc": "doc_",
}


def _expand_shorthand(kind: str, raw_id: str) -> str:
    """Expand shorthand IDs to their canonical prefixed form."""
    prefix = _PREFIX_MAP.get(kind, "")
    if prefix and not raw_id.startswith(prefix):
        return prefix + raw_id
    if kind == "file":
        return raw_id
    if kind in ("tag", "mech"):
        return raw_id
    return raw_id


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _string(v: Any) -> str:
    return str(v).strip() if v is not None else ""


def _resolve_paragraph(ref: CitationRef, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    cid = ref.canonical_id
    for p in payload.get("paragraphs", []):
        if _string(p.get("id")) == cid:
            return {
                "kind": "paragraph",
                "id": _string(p.get("id")),
                "section_id": _string(p.get("section_id")),
                "summary": _string(p.get("summary")),
                "tags": list(p.get("tags") or []),
                "idea_group_ids": list(p.get("idea_group_ids") or []),
            }
    return None


def _resolve_section(ref: CitationRef, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    cid = ref.canonical_id
    for s in payload.get("sections", []):
        if _string(s.get("id")) == cid:
            return {
                "kind": "section",
                "id": _string(s.get("id")),
                "heading": _string(s.get("heading")),
                "path": _string(s.get("path")),
                "paragraph_count": len(s.get("paragraph_ids") or []),
                "tags": list(s.get("tags") or []),
            }
    return None


def _resolve_source(ref: CitationRef, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    # Sources are top-level sections (children of sec_root)
    cid = ref.canonical_id
    for s in payload.get("sections", []):
        sid = _string(s.get("id"))
        if sid == cid or _string(s.get("parent_id")) == "sec_root" and sid == cid:
            return {
                "kind": "source",
                "id": sid,
                "heading": _string(s.get("heading")),
                "path": _string(s.get("path")),
                "paragraph_count": len(s.get("paragraph_ids") or []),
            }
    return None


def _resolve_by_index(
    ref: CitationRef,
    payload: Mapping[str, Any],
    index_key: str,
    prefix: str,
) -> dict[str, Any] | None:
    """Resolve via the index if it has been loaded into the payload (raw_seed_index.json shape)."""
    indexes = payload.get("indexes", {})
    idx = indexes.get(index_key, {})
    cid = ref.canonical_id
    if cid in idx:
        return {"kind": ref.kind, "id": cid, "paragraph_ids": idx[cid]}
    # Try without prefix
    bare = cid.removeprefix(prefix)
    for key, val in idx.items():
        if key.removeprefix(prefix) == bare:
            return {"kind": ref.kind, "id": key, "paragraph_ids": val}
    return None


def _resolve_theme(ref: CitationRef, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Resolve tag or mechanism by scanning paragraph metadata."""
    target = ref.canonical_id
    field = "tags" if ref.kind == "tag" else "mechanism_hints"
    matching_ids: list[str] = []
    for p in payload.get("paragraphs", []):
        values = [_string(v) for v in (p.get(field) or [])]
        if target in values:
            matching_ids.append(_string(p.get("id")))
    if not matching_ids:
        return None
    return {
        "kind": ref.kind,
        "value": target,
        "paragraph_count": len(matching_ids),
        "sample_paragraph_ids": matching_ids[:6],
    }


def _resolve_doc(ref: CitationRef, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    cid = ref.canonical_id
    for entry in payload.get("entries", []):
        if _string(entry.get("id")) == cid:
            return dict(entry)
    return None
