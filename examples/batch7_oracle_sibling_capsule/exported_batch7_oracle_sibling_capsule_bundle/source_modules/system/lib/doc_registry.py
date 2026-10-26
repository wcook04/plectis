"""
[PURPOSE]
- Teleology: JSON-first documentation registry that ties documentation entries to code, raw seed
  paragraphs, principles, and each other via typed hierarchy (principles → concepts → mechanisms).
  Each entry carries structured summary, when_needed routing, raw_seed citations, and dependency edges.
- Mechanism: Reads/writes doc_registry.json at the family root. Provides CRUD, query, search,
  markdown projection, and validation. All mutations return new payloads (no in-place writes).
- Non-goal: Rendering documentation content (that belongs to markdown builders or obsidian tooling).

[INTERFACE]
- empty_registry(family_id, family_dir)               -> dict
- load_registry(path)                                  -> dict
- save_registry(registry, path)                        -> None
- add_entry(registry, entry)                           -> dict (updated registry)
- update_entry(registry, doc_id, fields)               -> dict
- remove_entry(registry, doc_id)                       -> dict
- get_entry(registry, doc_id)                          -> dict | None
- query_entries(registry, *, doc_type, tag, status, q) -> list[dict]
- search_entries(registry, query)                      -> list[dict]
- link_entries(registry, src, tgt, relation, gloss)    -> dict
- unlink_entries(registry, src, tgt)                   -> dict
- registry_stats(registry)                             -> dict
- validate_entry(entry)                                -> list[str] (errors)
- build_markdown_projection(registry)                  -> str
- migrate_v1_to_v2(registry)                           -> dict

[FLOW]
- Load or bootstrap the JSON registry envelope -> validate and normalize entry mutations -> update edges and queries against copied payloads -> emit stats and markdown projections from the authoritative registry state.
- Keep family documentation JSON-first so search, doctrine-reference packing, and markdown projection all derive from one canonical registry artifact.

[DEPENDENCIES]
- Python stdlib: json, pathlib, datetime, typing, textwrap.

[CONSTRAINTS]
- Reads/writes: doc_registry.json / doc_registry.md.
- No raw_seed.json mutation (that's substrate_ops territory).
- Entry IDs must start with doc_ prefix.
- When-needed: Open when family-scoped documentation entries or typed doctrine edges need the authoritative JSON-first CRUD, validation, and projection rules instead of editing registry artifacts by hand.
- Escalates-to: system/lib/doctrine_reference_context.py::build_doctrine_reference_pack; codex/standards/std_python.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DOC_REGISTRY_FILENAME = "doc_registry.json"
DOC_REGISTRY_MD_FILENAME = "doc_registry.md"
DOC_REGISTRY_SCHEMA_VERSION = "doc_registry_v2"

VALID_DOC_TYPES = (
    "principle", "concept", "mechanism", "guide", "flow", "module", "standard",
)
VALID_STATUSES = ("draft", "stable", "retired")
VALID_RELATIONS = (
    "depends_on", "enables", "governs", "refines", "tension",
    # v1 compat
    "implements", "extends", "documents", "derives_from", "related_to",
)

# Hierarchy: principles → concepts → mechanisms.  Guides/flows cut across.
HIERARCHY_ORDER = {
    "principle": 0,
    "standard": 1,
    "concept": 2,
    "flow": 3,
    "mechanism": 4,
    "module": 5,
    "guide": 6,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(v: Any) -> str:
    return str(v).strip() if v is not None else ""


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        s = _string(item)
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# Registry lifecycle
# ---------------------------------------------------------------------------

def empty_registry(family_id: str = "", family_dir: str = "") -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Bootstrap the canonical empty documentation-registry envelope for one family before any entries or edges exist.
    - Mechanism: Return a fresh dict containing the registry kind, schema version, family metadata, doc-type descriptions, and empty entries/edges lists with synchronized timestamps.
    - Guarantee: Returns a new v2 registry payload whose schema_version is `doc_registry_v2` and whose entries and edges are empty lists.
    - Fails: None.
    - When-needed: Open when scaffolding or resetting a family documentation registry to the canonical empty shape.
    - Escalates-to: codex/standards/std_python.py
    """
    return {
        "kind": "doc_registry",
        "schema_version": DOC_REGISTRY_SCHEMA_VERSION,
        "family_id": family_id,
        "family_dir": family_dir,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "doc_types": {
            "principle": "Durable architectural commitment traced from raw seed.",
            "concept": "Named design idea distilled from raw seed voice and evidence.",
            "mechanism": "Concrete implementation pattern tied to actual code.",
            "guide": "How-to documentation for a specific workflow or operation.",
            "flow": "End-to-end process connecting multiple mechanisms.",
            "module": "Documentation for a code module or subsystem.",
            "standard": "Schema or contract definition governing artifact shape.",
        },
        "entries": [],
        "edges": [],
    }


def load_registry(path: Path | str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Materialize the effective documentation registry from disk while preserving backward compatibility for v1 payloads and missing files.
    - Mechanism: Read JSON from the supplied path, accept only `kind == "doc_registry"`, migrate v1 payloads through migrate_v1_to_v2(), and fall back to empty_registry() on absence or invalid data.
    - Guarantee: Returns a registry-shaped dict and never raises for missing files, parse errors, or wrong-kind payloads.
    - Fails: None.
    - When-needed: Open when a caller needs the canonical load-and-fallback behavior for `doc_registry.json`, including v1 migration.
    - Escalates-to: codex/standards/std_python.py
    """
    p = Path(path)
    if not p.exists():
        return empty_registry()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("kind") == "doc_registry":
            if data.get("schema_version") == "doc_registry_v1":
                return migrate_v1_to_v2(data)
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return empty_registry()


def save_registry(registry: dict[str, Any], path: Path | str) -> None:
    """
    [ACTION]
    - Teleology: Persist one documentation registry snapshot as the authoritative JSON artifact on disk.
    - Mechanism: Ensure the parent directory exists, refresh updated_at, and write the registry as indented UTF-8 JSON with a trailing newline.
    - Guarantee: Writes the supplied registry payload to the requested path with an updated timestamp when filesystem operations succeed.
    - Fails: Propagates filesystem exceptions from mkdir() or write_text().
    - When-needed: Open when a caller needs the canonical persistence rule for `doc_registry.json` before writing family documentation state.
    - Escalates-to: codex/standards/std_python.py
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = _utc_now()
    p.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Migration v1 → v2
# ---------------------------------------------------------------------------

def migrate_v1_to_v2(registry: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Upgrade legacy v1 documentation-registry payloads into the canonical v2 shape expected by current tooling.
    - Mechanism: Copy the registry, replace schema metadata, synthesize doc_types, convert legacy entry fields into v2 summary/raw_seed_refs/upstream/downstream form, and refresh updated timestamps.
    - Guarantee: Returns a new dict shaped like a v2 registry while preserving recoverable entry content from the v1 payload.
    - Fails: None.
    - When-needed: Open when a loader or repair pass needs the exact field-level translation from legacy `doc_registry_v1` payloads into v2.
    - Escalates-to: codex/standards/std_python.py
    """
    migrated = dict(registry)
    migrated["schema_version"] = DOC_REGISTRY_SCHEMA_VERSION
    migrated["doc_types"] = empty_registry()["doc_types"]
    migrated["updated_at"] = _utc_now()
    new_entries = []
    for entry in migrated.get("entries", []):
        v1_kind = _string(entry.get("kind"))
        doc_type = v1_kind if v1_kind in VALID_DOC_TYPES else "concept"
        v1_summary = entry.get("summary", "")
        if isinstance(v1_summary, str):
            summary = {"problem": "", "mechanism": v1_summary, "why_this_matters": ""}
        else:
            summary = v1_summary
        v1_anchors = entry.get("anchors", [])
        paragraph_ids = [a.replace("@par:", "") for a in v1_anchors if str(a).startswith("@par:")]
        section_ids = [a.replace("@sec:", "") for a in v1_anchors if str(a).startswith("@sec:")]
        new_entry = {
            "id": _string(entry.get("id")),
            "title": _string(entry.get("title")),
            "doc_type": doc_type,
            "status": _string(entry.get("status")) or "draft",
            "summary": summary,
            "when_needed": "",
            "tags": list(entry.get("tags") or []),
            "raw_seed_refs": {
                "paragraph_ids": paragraph_ids,
                "section_ids": section_ids,
                "principle_ids": [],
            },
            "code_refs": list(entry.get("code_refs") or []),
            "upstream_ids": list(entry.get("upstream") or []),
            "downstream_ids": list(entry.get("downstream") or []),
            "claims": [],
            "lens": dict(entry.get("lens") or {}),
            "created_at": _string(entry.get("created_at")) or _utc_now(),
            "updated_at": _utc_now(),
        }
        new_entries.append(new_entry)
    migrated["entries"] = new_entries
    return migrated


# ---------------------------------------------------------------------------
# Entry validation
# ---------------------------------------------------------------------------

def validate_entry(entry: Mapping[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Reject malformed documentation entries before they enter the registry and contaminate downstream search or projection surfaces.
    - Mechanism: Check id/title presence, doc_type/status membership, summary shape, and raw_seed_refs coverage, appending one descriptive error string per violation.
    - Guarantee: Returns a list of validation error strings and returns [] only when the entry satisfies the v2 registry contract.
    - Fails: None.
    - When-needed: Open when a caller needs the authoritative rejection criteria for a candidate registry entry before adding or updating it.
    - Escalates-to: codex/standards/std_python.py
    """
    errors: list[str] = []
    doc_id = _string(entry.get("id"))
    if not doc_id:
        errors.append("Missing required field: id")
    elif not doc_id.startswith("doc_"):
        errors.append(f"Entry id must start with 'doc_' prefix, got: {doc_id!r}")
    if not _string(entry.get("title")):
        errors.append("Missing required field: title")
    doc_type = _string(entry.get("doc_type"))
    if doc_type and doc_type not in VALID_DOC_TYPES:
        errors.append(f"Invalid doc_type: {doc_type!r}. Valid: {', '.join(VALID_DOC_TYPES)}")
    status = _string(entry.get("status"))
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status: {status!r}. Valid: {', '.join(VALID_STATUSES)}")
    summary = entry.get("summary")
    if isinstance(summary, dict):
        for field in ("problem", "mechanism", "why_this_matters"):
            if field not in summary:
                errors.append(f"Missing summary field: {field}")
    elif summary is not None and not isinstance(summary, str):
        errors.append("summary must be a dict with problem/mechanism/why_this_matters or a string")
    refs = entry.get("raw_seed_refs")
    if isinstance(refs, dict):
        pids = refs.get("paragraph_ids", [])
        sids = refs.get("section_ids", [])
        if not pids and not sids:
            errors.append("raw_seed_refs must contain at least one paragraph_id or section_id")
    return errors


def _normalize_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an entry to canonical v2 shape."""
    now = _utc_now()
    summary = entry.get("summary")
    if isinstance(summary, str):
        summary = {"problem": "", "mechanism": summary, "why_this_matters": ""}
    elif not isinstance(summary, dict):
        summary = {"problem": "", "mechanism": "", "why_this_matters": ""}
    refs = entry.get("raw_seed_refs")
    if not isinstance(refs, dict):
        refs = {"paragraph_ids": [], "section_ids": [], "principle_ids": []}
    else:
        refs = {
            "paragraph_ids": _dedupe([_string(p) for p in (refs.get("paragraph_ids") or [])]),
            "section_ids": _dedupe([_string(s) for s in (refs.get("section_ids") or [])]),
            "principle_ids": _dedupe([_string(p) for p in (refs.get("principle_ids") or [])]),
        }
    return {
        "id": _string(entry.get("id")),
        "title": _string(entry.get("title")),
        "doc_type": _string(entry.get("doc_type")) or "concept",
        "status": _string(entry.get("status")) or "draft",
        "summary": summary,
        "when_needed": _string(entry.get("when_needed")),
        "tags": _dedupe([_string(t) for t in (entry.get("tags") or [])]),
        "raw_seed_refs": refs,
        "code_refs": _dedupe([_string(c) for c in (entry.get("code_refs") or [])]),
        "upstream_ids": _dedupe([_string(u) for u in (entry.get("upstream_ids") or [])]),
        "downstream_ids": _dedupe([_string(d) for d in (entry.get("downstream_ids") or [])]),
        "claims": list(entry.get("claims") or []),
        "lens": dict(entry.get("lens") or {}),
        "created_at": _string(entry.get("created_at")) or now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def add_entry(registry: Mapping[str, Any], entry: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Append one validated documentation entry to a registry without mutating the caller's existing registry object.
    - Mechanism: Validate the entry, reject duplicate ids, normalize the entry to canonical v2 shape, append it to a copied entries list, and refresh updated_at.
    - Guarantee: Returns a new registry dict containing the added entry when validation passes and the id is new.
    - Fails: Raises ValueError when the entry is invalid or its id already exists.
    - When-needed: Open when a caller needs the canonical add-one-entry mutation path for a documentation registry.
    - Escalates-to: codex/standards/std_python.py
    """
    errors = validate_entry(entry)
    if errors:
        raise ValueError(f"Invalid entry: {'; '.join(errors)}")
    doc_id = _string(entry["id"])
    existing_ids = {_string(e.get("id")) for e in registry.get("entries", [])}
    if doc_id in existing_ids:
        raise ValueError(f"Entry already exists: {doc_id!r}")
    updated = dict(registry)
    updated["entries"] = list(registry.get("entries", [])) + [_normalize_entry(entry)]
    updated["updated_at"] = _utc_now()
    return updated


def update_entry(
    registry: Mapping[str, Any],
    doc_id: str,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Apply a partial field update to one existing documentation entry while preserving the registry's append-and-copy mutation model.
    - Mechanism: Locate the entry by id, merge list-shaped and raw_seed_refs fields with deduplication rules, overwrite other keys directly, and refresh both entry and registry updated_at timestamps.
    - Guarantee: Returns a new registry dict with the requested entry updated in place inside the copied entries list.
    - Fails: Raises ValueError when the target entry id is absent.
    - When-needed: Open when a caller must merge new tags, code refs, claims, or raw seed refs onto an existing registry entry without hand-editing JSON.
    - Escalates-to: codex/standards/std_python.py
    """
    doc_id = _string(doc_id)
    updated = dict(registry)
    entries = [dict(e) for e in registry.get("entries", [])]
    found = False
    for entry in entries:
        if _string(entry.get("id")) != doc_id:
            continue
        found = True
        for key, value in fields.items():
            if key == "id":
                continue
            if key in ("tags", "code_refs", "upstream_ids", "downstream_ids"):
                existing = list(entry.get(key) or [])
                if isinstance(value, list):
                    for v in value:
                        s = _string(v)
                        if s and s not in existing:
                            existing.append(s)
                entry[key] = _dedupe(existing)
            elif key == "raw_seed_refs" and isinstance(value, dict):
                refs = dict(entry.get("raw_seed_refs") or {})
                for subkey in ("paragraph_ids", "section_ids", "principle_ids"):
                    if subkey in value:
                        existing = list(refs.get(subkey) or [])
                        for v in (value[subkey] or []):
                            s = _string(v)
                            if s and s not in existing:
                                existing.append(s)
                        refs[subkey] = _dedupe(existing)
                entry["raw_seed_refs"] = refs
            elif key == "lens" and isinstance(value, dict):
                lens = dict(entry.get("lens") or {})
                lens.update(value)
                entry["lens"] = lens
            elif key == "claims" and isinstance(value, list):
                existing = list(entry.get("claims") or [])
                existing_ids = {c.get("id") for c in existing}
                for claim in value:
                    if claim.get("id") not in existing_ids:
                        existing.append(claim)
                entry["claims"] = existing
            else:
                entry[key] = value
        entry["updated_at"] = _utc_now()
        break
    if not found:
        raise ValueError(f"Entry not found: {doc_id!r}")
    updated["entries"] = entries
    updated["updated_at"] = _utc_now()
    return updated


def remove_entry(registry: Mapping[str, Any], doc_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Remove one documentation entry and every attached edge so the registry cannot retain dangling doctrine relationships.
    - Mechanism: Filter the copied entries list by id, reject missing ids, drop all edges whose source or target is the removed entry, and refresh updated_at.
    - Guarantee: Returns a new registry dict with the entry removed and all attached edges deleted.
    - Fails: Raises ValueError when the target entry id is absent.
    - When-needed: Open when a caller needs the canonical delete path for one documentation entry instead of hand-editing entries and edges separately.
    - Escalates-to: codex/standards/observe_apply/std_doc_registry.json; system/server/tests/test_doc_registry.py
    - Navigation-group: kernel_lib
    """
    doc_id = _string(doc_id)
    entries = list(registry.get("entries", []))
    before_count = len(entries)
    entries = [e for e in entries if _string(e.get("id")) != doc_id]
    if len(entries) == before_count:
        raise ValueError(f"Entry not found: {doc_id!r}")
    edges = [
        e for e in registry.get("edges", [])
        if _string(e.get("source")) != doc_id and _string(e.get("target")) != doc_id
    ]
    updated = dict(registry)
    updated["entries"] = entries
    updated["edges"] = edges
    updated["updated_at"] = _utc_now()
    return updated


def get_entry(registry: Mapping[str, Any], doc_id: str) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Retrieve one documentation entry by id without exposing the caller to the registry's internal list structure.
    - Mechanism: Normalize the requested id, linearly scan the entries list, and return a copied entry dict on the first exact id match.
    - Guarantee: Returns a copied entry dict for an exact id match and None when the entry is absent.
    - Fails: None.
    - When-needed: Open when a caller needs the canonical by-id lookup rule for one documentation entry before updating, projecting, or linking it.
    - Escalates-to: codex/standards/observe_apply/std_doc_registry.json; system/server/tests/test_doc_registry.py
    - Navigation-group: kernel_lib
    """
    doc_id = _string(doc_id)
    for entry in registry.get("entries", []):
        if _string(entry.get("id")) == doc_id:
            return dict(entry)
    return None


# ---------------------------------------------------------------------------
# Query & Search
# ---------------------------------------------------------------------------

def query_entries(
    registry: Mapping[str, Any],
    *,
    doc_type: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    code_ref: str | None = None,
    principle_id: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Pull the subset of registry entries that satisfy a bounded set of structured filters.
    - Mechanism: Walk every entry and AND-combine the supplied doc_type, tag, status, code_ref, principle_id, and free-text query checks before copying matching rows into the result.
    - Guarantee: Returns a list of copied entry dicts whose members satisfy every provided filter.
    - Fails: None.
    - When-needed: Open when a caller needs the exact structured-filter semantics for slicing one family documentation registry.
    - Escalates-to: codex/standards/std_python.py
    """
    results: list[dict[str, Any]] = []
    for entry in registry.get("entries", []):
        if doc_type and _string(entry.get("doc_type")) != doc_type:
            continue
        if status and _string(entry.get("status")) != status:
            continue
        if tag and tag not in [_string(t) for t in (entry.get("tags") or [])]:
            continue
        if code_ref:
            refs = [_string(c) for c in (entry.get("code_refs") or [])]
            if not any(code_ref in r for r in refs):
                continue
        if principle_id:
            pids = (entry.get("raw_seed_refs") or {}).get("principle_ids", [])
            if principle_id not in [_string(p) for p in pids]:
                continue
        if q:
            if not _matches_query(entry, q):
                continue
        results.append(dict(entry))
    return results


def search_entries(registry: Mapping[str, Any], query: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Provide the registry's built-in relevance-ranked full-text search without making callers hand-score entry fields.
    - Mechanism: Lowercase the query, score each entry across id/title/when_needed/doc_type/summary/tags/claims via _relevance_score(), and return matching copied entries sorted by descending score.
    - Guarantee: Returns only entries with positive relevance scores, ordered from highest to lowest relevance.
    - Fails: None.
    - When-needed: Open when a caller needs the registry's canonical free-text search behavior and ranking weights.
    - Escalates-to: codex/standards/std_python.py
    """
    q_lower = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in registry.get("entries", []):
        score = _relevance_score(entry, q_lower)
        if score > 0:
            scored.append((score, dict(entry)))
    scored.sort(key=lambda x: -x[0])
    return [entry for _, entry in scored]


def _matches_query(entry: dict[str, Any], q: str) -> bool:
    return _relevance_score(entry, q.lower()) > 0


def _relevance_score(entry: dict[str, Any], q_lower: str) -> int:
    """Score an entry against a query. Higher = better match."""
    score = 0
    fields = [
        (5, _string(entry.get("id"))),
        (5, _string(entry.get("title"))),
        (3, _string(entry.get("when_needed"))),
        (2, _string(entry.get("doc_type"))),
    ]
    summary = entry.get("summary")
    if isinstance(summary, dict):
        fields.append((3, _string(summary.get("problem"))))
        fields.append((3, _string(summary.get("mechanism"))))
        fields.append((2, _string(summary.get("why_this_matters"))))
    elif isinstance(summary, str):
        fields.append((3, summary))
    for tag in (entry.get("tags") or []):
        fields.append((4, _string(tag)))
    for claim in (entry.get("claims") or []):
        fields.append((1, _string(claim.get("text"))))
    for weight, text in fields:
        if q_lower in text.lower():
            score += weight
    return score


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

def link_entries(
    registry: Mapping[str, Any],
    source_id: str,
    target_id: str,
    relation: str = "depends_on",
    gloss: str = "",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Attach one typed directed relationship between two documentation entries without introducing duplicate edges.
    - Mechanism: Validate the relation name, check for an existing identical edge, append a new edge record with created_at when needed, and refresh registry updated_at.
    - Guarantee: Returns the original registry unchanged for duplicate edges and otherwise returns a new registry dict with one appended edge.
    - Fails: Raises ValueError when the requested relation is outside VALID_RELATIONS.
    - When-needed: Open when a caller needs the canonical edge-creation rule for doctrine relationships such as `depends_on`, `governs`, or `refines`.
    - Escalates-to: codex/standards/std_python.py
    """
    source_id = _string(source_id)
    target_id = _string(target_id)
    if relation not in VALID_RELATIONS:
        raise ValueError(f"Invalid relation: {relation!r}. Valid: {', '.join(VALID_RELATIONS)}")
    edges = list(registry.get("edges", []))
    for edge in edges:
        if (
            _string(edge.get("source")) == source_id
            and _string(edge.get("target")) == target_id
            and _string(edge.get("relation")) == relation
        ):
            return dict(registry)
    edge_obj: dict[str, Any] = {
        "source": source_id,
        "target": target_id,
        "relation": relation,
        "created_at": _utc_now(),
    }
    if gloss:
        edge_obj["gloss"] = gloss
    edges.append(edge_obj)
    updated = dict(registry)
    updated["edges"] = edges
    updated["updated_at"] = _utc_now()
    return updated


def unlink_entries(
    registry: Mapping[str, Any],
    source_id: str,
    target_id: str,
    relation: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Remove one or more doctrine edges between two documentation entries without mutating the caller's registry object.
    - Mechanism: Filter the copied edge list to drop edges whose source and target match the requested ids and whose relation matches when one is supplied, then refresh updated_at.
    - Guarantee: Returns a new registry dict whose edges list omits the requested edge or edge family.
    - Fails: None.
    - When-needed: Open when a caller needs the canonical unlink rule for typed documentation edges between two ids.
    - Escalates-to: codex/standards/observe_apply/std_doc_registry.json; system/server/tests/test_doc_registry.py
    - Navigation-group: kernel_lib
    """
    source_id = _string(source_id)
    target_id = _string(target_id)
    edges = [
        e for e in registry.get("edges", [])
        if not (
            _string(e.get("source")) == source_id
            and _string(e.get("target")) == target_id
            and (relation is None or _string(e.get("relation")) == relation)
        )
    ]
    updated = dict(registry)
    updated["edges"] = edges
    updated["updated_at"] = _utc_now()
    return updated


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def registry_stats(registry: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Summarize one documentation registry into counts that projection and status surfaces can display without recomputing them ad hoc.
    - Mechanism: Count entries by type and status, accumulate top tags and relations, total raw-seed citations, and total code refs across the registry payload.
    - Guarantee: Returns a stats dict containing entry_count, edge_count, doc_types, statuses, tags_top, relations, total_raw_seed_citations, and total_code_refs.
    - Fails: None.
    - When-needed: Open when a caller needs the registry's canonical summary-count computation before rendering or auditing it.
    - Escalates-to: codex/standards/std_python.py
    """
    entries = registry.get("entries", [])
    edges = registry.get("edges", [])
    type_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    citation_count = 0
    for entry in entries:
        dt = _string(entry.get("doc_type")) or "unknown"
        type_counts[dt] = type_counts.get(dt, 0) + 1
        s = _string(entry.get("status")) or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
        for t in (entry.get("tags") or []):
            ts = _string(t)
            if ts:
                tag_counts[ts] = tag_counts.get(ts, 0) + 1
        refs = entry.get("raw_seed_refs") or {}
        citation_count += len(refs.get("paragraph_ids", []))
        citation_count += len(refs.get("section_ids", []))
    relation_counts: dict[str, int] = {}
    for edge in edges:
        r = _string(edge.get("relation")) or "unknown"
        relation_counts[r] = relation_counts.get(r, 0) + 1
    return {
        "entry_count": len(entries),
        "edge_count": len(edges),
        "doc_types": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
        "statuses": dict(sorted(status_counts.items(), key=lambda x: -x[1])),
        "tags_top": dict(sorted(tag_counts.items(), key=lambda x: -x[1])[:20]),
        "relations": dict(sorted(relation_counts.items(), key=lambda x: -x[1])),
        "total_raw_seed_citations": citation_count,
        "total_code_refs": sum(len(e.get("code_refs") or []) for e in entries),
    }


# ---------------------------------------------------------------------------
# Markdown projection
# ---------------------------------------------------------------------------

def build_markdown_projection(registry: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Render the human-readable markdown projection of one authoritative JSON documentation registry.
    - Mechanism: Compute registry stats, group entries by hierarchical doc_type order, and emit the contents, per-type sections, citations, code refs, claims, and optional tag index into one markdown string.
    - Guarantee: Returns a complete `doc_registry.md` projection string derived solely from the supplied JSON registry payload.
    - Fails: None.
    - When-needed: Open when a caller needs the canonical JSON-to-markdown projection rules for a family documentation registry.
    - Escalates-to: codex/standards/std_python.py
    """
    lines: list[str] = []
    family_id = registry.get("family_id", "?")
    family_dir = registry.get("family_dir", "?")
    entries = registry.get("entries", [])
    edges = registry.get("edges", [])
    stats = registry_stats(registry)

    lines.append(f"# Documentation Registry — Family {family_id}")
    lines.append("")
    lines.append("> **Generated projection.** Do not hand-edit. Authority: `doc_registry.json`")
    lines.append(f"> Family dir: `{family_dir}`")
    lines.append(f"> Entries: {stats['entry_count']} | Edges: {stats['edge_count']} | Raw seed citations: {stats['total_raw_seed_citations']}")
    lines.append("")

    # Group by doc_type in hierarchy order
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        dt = _string(entry.get("doc_type")) or "concept"
        grouped.setdefault(dt, []).append(entry)

    sorted_types = sorted(grouped.keys(), key=lambda t: HIERARCHY_ORDER.get(t, 99))

    # Table of contents
    lines.append("## Contents")
    lines.append("")
    for dt in sorted_types:
        count = len(grouped[dt])
        type_desc = (registry.get("doc_types") or {}).get(dt, "")
        lines.append(f"- **{dt}** ({count}) — {type_desc}")
    lines.append("")

    # Per-type sections
    for dt in sorted_types:
        dt_entries = grouped[dt]
        lines.append(f"## {dt.title()}s")
        lines.append("")
        for entry in dt_entries:
            eid = entry.get("id", "?")
            title = entry.get("title", "?")
            status = entry.get("status", "draft")
            lines.append(f"### `{eid}` — {title}")
            lines.append(f"**Status:** {status}")
            lines.append("")

            summary = entry.get("summary")
            if isinstance(summary, dict):
                if summary.get("problem"):
                    lines.append(f"**Problem:** {summary['problem']}")
                if summary.get("mechanism"):
                    lines.append(f"**Mechanism:** {summary['mechanism']}")
                if summary.get("why_this_matters"):
                    lines.append(f"**Why this matters:** {summary['why_this_matters']}")
            elif isinstance(summary, str) and summary:
                lines.append(f"**Summary:** {summary}")
            lines.append("")

            wn = entry.get("when_needed", "")
            if wn:
                lines.append(f"**When needed:** {wn}")
                lines.append("")

            tags = entry.get("tags", [])
            if tags:
                lines.append(f"**Tags:** {', '.join(tags)}")
                lines.append("")

            refs = entry.get("raw_seed_refs") or {}
            pids = refs.get("paragraph_ids", [])
            sids = refs.get("section_ids", [])
            prids = refs.get("principle_ids", [])
            if pids or sids or prids:
                lines.append("**Raw seed citations:**")
                for pid in pids:
                    lines.append(f"- paragraph: `{pid}`")
                for sid in sids:
                    lines.append(f"- section: `{sid}`")
                for prid in prids:
                    lines.append(f"- principle: `{prid}`")
                lines.append("")

            code_refs = entry.get("code_refs", [])
            if code_refs:
                lines.append("**Code refs:**")
                for cr in code_refs:
                    lines.append(f"- `{cr}`")
                lines.append("")

            upstream = entry.get("upstream_ids", [])
            downstream = entry.get("downstream_ids", [])
            if upstream or downstream:
                chain_parts = []
                if upstream:
                    chain_parts.append(" + ".join(f"`{u}`" for u in upstream))
                chain_parts.append(f"**`{eid}`**")
                if downstream:
                    chain_parts.append(" + ".join(f"`{d}`" for d in downstream))
                lines.append(f"**Hierarchy:** {' → '.join(chain_parts)}")
                lines.append("")

            claims = entry.get("claims", [])
            if claims:
                lines.append("**Claims:**")
                for claim in claims:
                    cid = claim.get("id", "?")
                    ctext = claim.get("text", "")
                    lines.append(f"- `{cid}`: {ctext}")
                lines.append("")

            lines.append("---")
            lines.append("")

    # Tag index
    if stats.get("tags_top"):
        lines.append("## Tag Index")
        lines.append("")
        tag_to_entries: dict[str, list[str]] = {}
        for entry in entries:
            eid = entry.get("id", "?")
            for tag in (entry.get("tags") or []):
                tag_to_entries.setdefault(tag, []).append(eid)
        for tag in sorted(tag_to_entries.keys()):
            eids = tag_to_entries[tag]
            lines.append(f"- **{tag}**: {', '.join(f'`{e}`' for e in eids)}")
        lines.append("")

    return "\n".join(lines)
