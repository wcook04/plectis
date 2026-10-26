"""
[PURPOSE]
- Teleology: Per-source adapters that teach the embedding substrate how to enumerate every kind of durable plane artifact as faceted vector-field rows. Each adapter respects the controlled vocabulary that already governs its source — std_python.py contract atoms for Python modules, doctrine JSON shape for concepts/mechanisms/principles, paper-module markdown sections for subsystems, archaeological-shard sub-fields for voice substrate. Embedding the schema axes separately turns the plane into a vector field, not a flat search index.
- Mechanism: Each adapter subclasses SourceAdapter, walks the authoritative on-disk artifact, parses its controlled vocabulary into FacetedItem(facets={axis_name: text}), and optionally exposes schema_hash() so contract changes (e.g. std_python.py edited) force a full re-embed of every dependent artifact.

[INTERFACE]
- Exports: DoctrineSource, PaperModuleSource, SkillSource, RawSeedParagraphSource, RawSeedShardSource, RawSeedNavigationSource, ArchaeologyShardSource, PythonHolographicSource, parse_std_python_atoms, SOURCE_ADAPTERS, build_adapter, all_source_kinds.
- Reads: codex/doctrine/**, family raw_seed.json payloads, raw_seed/raw_seed_principles.json, raw_seed/raw_seed_navigation_runtime.json, codex/doctrine/paper_modules/*.md, codex/doctrine/skills/**/*.md, state/voice_archaeology/archaeological_shards.json, codex/standards/std_python.py, system/**/*.py.
- Writes: None (the substrate owns cache writes).

[FLOW]
- Construct adapter with repo_root -> iter_items() walks the source -> yields FacetedItem(id, source_path, facets, metadata) -> EmbeddingSubstrate.refresh decides which (id, facet) rows need re-embedding.
- When-needed: Adding a new artifact type or adding a new facet to an existing one (e.g. paper modules gaining a 'refresh_contract' axis) -> extend the adapter's iter_items().
- Escalates-to: codex/standards/std_python.py (Python facet contract), codex/standards/voice_archaeology/std_voice_archaeology.json (archaeological shard facet contract), system.lib.embedding_substrate.

[DEPENDENCIES]
- Required:
  - system.lib.embedding_substrate (SourceAdapter, FacetedItem, FACET_BODY)
  - json, re, ast, hashlib, pathlib (std)

[CONSTRAINTS]
- Guarantee: every adapter yields stable ids for the same repo state; facet names are stable per source; no duplicate (id, facet) within a single source_kind.
- Non-goal: adapters never mutate sources, never own freshness signals (the substrate does), never compute embeddings.
- Scope: plane-internal artifacts only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Iterator

from system.lib.embedding_substrate import FACET_BODY, FacetedItem, SourceAdapter
from system.lib.raw_seed_registry import build_raw_seed_payload_for_family, build_raw_seed_shards


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


STD_JSON_FACETS_REL_PATH = "codex/standards/std_json_facets.json"


def _derived_schema_hash(repo_root: Path, rel_path: str, *, salt: str) -> str | None:
    file_hash = _sha256_file(repo_root / rel_path)
    if not file_hash:
        return None
    return hashlib.sha256(f"{salt}:{file_hash}".encode("utf-8")).hexdigest()


def _join_text_parts(*parts: Any) -> str:
    flattened: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, str):
            text = re.sub(r"\s+", " ", part).strip()
            if text:
                flattened.append(text)
            continue
        if isinstance(part, dict):
            text = _join_text_parts(*part.values())
            if text:
                flattened.extend(text.split(" | "))
            continue
        if isinstance(part, Iterable) and not isinstance(part, (str, bytes, dict)):
            for item in part:
                text = _join_text_parts(item)
                if text:
                    flattened.extend(text.split(" | "))
            continue
        text = re.sub(r"\s+", " ", str(part)).strip()
        if text:
            flattened.append(text)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in flattened:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return " | ".join(deduped)


def _edge_glosses(entries: Any) -> str:
    if not isinstance(entries, list):
        return ""
    parts: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for key in ("forward_gloss", "gloss", "reverse_gloss"):
            text = str(entry.get(key) or "").strip()
            if text:
                parts.append(text)
                break
    return _join_text_parts(parts)


def _edge_targets(payload: dict[str, Any]) -> str:
    refs: list[str] = []
    for key in ("principle_edges", "mechanism_edges", "concept_edges", "reference_groups"):
        value = payload.get(key)
        if not isinstance(value, list):
            continue
        if key == "reference_groups":
            for group in value:
                if not isinstance(group, dict):
                    continue
                for shard in group.get("shards") or []:
                    if not isinstance(shard, dict):
                        continue
                    target = str(shard.get("target") or shard.get("extracted_shard_id") or "").strip()
                    relation = str(shard.get("relation") or "").strip()
                    if target:
                        refs.append(f"{relation}:{target}" if relation else target)
            continue
        for entry in value:
            if not isinstance(entry, dict):
                continue
            target = str(entry.get("target") or "").strip()
            relation = str(entry.get("relation") or "").strip()
            if target:
                refs.append(f"{relation}:{target}" if relation else target)
    return _join_text_parts(refs)


def _note_title(note_text: str, *, fallback: str) -> str:
    first_line = note_text.strip().splitlines()[0] if note_text.strip() else fallback
    for separator in (" — ", " - ", ": "):
        if separator in first_line:
            title = first_line.split(separator, 1)[0].strip()
            if title:
                return title
    return first_line.strip() or fallback


def _split_annex_note(note_text: str) -> tuple[str, str]:
    match = re.search(r"ai_workflow(?:\s+cross[- ]?ref)?\s*:\s*", note_text, re.IGNORECASE)
    if not match:
        return note_text.strip(), ""
    intent = note_text[: match.start()].strip()
    translation = note_text[match.end() :].strip()
    return intent, translation


def _load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return dict(payload) if isinstance(payload, dict) else None


def _phase_family_payloads(repo_root: Path) -> Iterator[dict[str, Any]]:
    obsidian_root = repo_root / "obsidian"
    if not obsidian_root.exists():
        return
    for marker in sorted(obsidian_root.rglob("phase_family.json")):
        payload = _load_json_object(marker)
        if not payload:
            continue
        yield payload


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


# --------------------------------------------------------------------------- #
# Doctrine
# --------------------------------------------------------------------------- #

class DoctrineSource(SourceAdapter):
    """Concepts + mechanisms (per-file JSONs) + principles (active phase JSON).

    Facets per node:
      - title: short name
      - statement: the claim itself
      - tags: comma-joined tag list (semantic tag-cloud axis)
    """

    source_kind = "doctrine"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def schema_hash(self) -> str | None:
        return _derived_schema_hash(self.repo_root, STD_JSON_FACETS_REL_PATH, salt=self.source_kind)

    def iter_items(self) -> Iterator[FacetedItem]:
        yield from self._iter_node_dir("codex/doctrine/concepts", "con_*.json", "concept")
        yield from self._iter_node_dir("codex/doctrine/mechanisms", "mech_*.json", "mechanism")
        yield from self._iter_principles()

    def _iter_node_dir(self, rel_dir: str, glob: str, kind: str) -> Iterator[FacetedItem]:
        directory = self.repo_root / rel_dir
        if not directory.exists():
            return
        for path in sorted(directory.glob(glob)):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            node_id = payload.get("id") or path.stem.split("_")[0]
            title = payload.get("title") or payload.get("slug") or node_id
            statement = payload.get("statement") or payload.get("summary") or ""
            tags = payload.get("tags") or []
            tag_text = ", ".join(str(t) for t in tags)
            teleology = payload.get("teleology") or statement
            mechanism = _join_text_parts(
                payload.get("mechanism"),
                payload.get("note"),
                _edge_glosses(payload.get("mechanism_edges")),
                statement if kind == "mechanism" else "",
            )
            guarantee = _join_text_parts(
                payload.get("guarantee"),
                _edge_glosses(payload.get("principle_edges")),
                payload.get("summary") if not statement else "",
                statement,
            )
            couples = _join_text_parts(
                payload.get("couples"),
                _edge_targets(payload),
            )
            yield FacetedItem(
                id=node_id,
                source_path=str(path.relative_to(self.repo_root)),
                facets={
                    "title": title,
                    "statement": statement,
                    "teleology": teleology,
                    "mechanism": mechanism,
                    "guarantee": guarantee,
                    "couples": couples,
                    "tags": tag_text,
                },
                metadata={
                    "kind": kind,
                    "slug": payload.get("slug"),
                    "title": title,
                    "status": payload.get("status"),
                    "tags": list(tags),
                },
            )

    def _iter_principles(self) -> Iterator[FacetedItem]:
        base = self.repo_root / "obsidian/okay lets do this"
        if not base.exists():
            return
        active = None
        active_num = -1
        for phase_dir in sorted(base.iterdir()):
            if not phase_dir.is_dir():
                continue
            principles_file = phase_dir / "raw_seed" / "raw_seed_principles.json"
            if not principles_file.exists():
                continue
            match = re.match(r"(\d+)", phase_dir.name)
            phase_num = int(match.group(1)) if match else 0
            if phase_num > active_num:
                active_num = phase_num
                active = principles_file
        if not active:
            return
        try:
            payload = json.loads(active.read_text(encoding="utf-8"))
        except Exception:
            return
        rel = str(active.relative_to(self.repo_root))
        for entry in payload.get("principles", []):
            node_id = entry.get("id")
            if not node_id:
                continue
            title = entry.get("title") or entry.get("slug") or node_id
            statement = entry.get("statement") or ""
            tags = entry.get("tags") or []
            tag_text = ", ".join(str(t) for t in tags)
            yield FacetedItem(
                id=node_id,
                source_path=rel,
                facets={
                    "title": title,
                    "statement": statement,
                    "teleology": entry.get("teleology") or statement,
                    "guarantee": entry.get("guarantee") or statement,
                    "couples": _join_text_parts(entry.get("couples")),
                    "tags": tag_text,
                },
                metadata={
                    "kind": "principle",
                    "slug": entry.get("slug"),
                    "title": title,
                    "status": entry.get("status"),
                    "tags": list(tags),
                },
            )


# --------------------------------------------------------------------------- #
# Paper modules
# --------------------------------------------------------------------------- #

PAPER_MODULE_FACET_HEADINGS = {
    "tldr": [r"##\s+TLDR[^\n]*"],
    "intent": [r"##\s+Intent\b"],
    "shape": [r"##\s+Shape\b"],
    "current_state": [r"##\s+Current state\b"],
    "deliverables": [r"##\s+Deliverables\b"],
    "gap": [r"##\s+Gap\b"],
}


class PaperModuleSource(SourceAdapter):
    """codex/doctrine/paper_modules/*.md split by canonical section headings.

    Facets:
      - title: H1
      - tldr: TLDR section
      - intent: Intent section
      - shape: Shape section
      - current_state: Current state section
      - gap: Gap section
      - deliverables: Deliverables section
    """

    source_kind = "paper_modules"
    text_version = "v1"  # bump on facet/section-mask change to force clean re-embed

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def iter_items(self) -> Iterator[FacetedItem]:
        root = self.repo_root / "codex/doctrine/paper_modules"
        if not root.exists():
            return
        for path in sorted(root.glob("*.md")):
            if path.name.startswith("_") or path.name == "README.md":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            slug = path.stem
            title = _first_heading(text) or slug
            facets: dict[str, str] = {"title": title}
            for facet_name, patterns in PAPER_MODULE_FACET_HEADINGS.items():
                section = _extract_section(text, patterns)
                if section:
                    facets[facet_name] = section[:2500]
            if "tldr" not in facets:
                facets["tldr"] = text[:1500]
            yield FacetedItem(
                id=slug,
                source_path=str(path.relative_to(self.repo_root)),
                facets=facets,
                metadata={"kind": "paper_module", "slug": slug, "title": title},
            )


def _extract_section(markdown: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        match = re.search(rf"({pat})\n+([\s\S]*?)(?=\n##\s|\Z)", markdown)
        if match:
            return match.group(2).strip()
    return None


def _first_heading(markdown: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else None


# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #

class SkillSource(SourceAdapter):
    """Skills under codex/doctrine/skills/**/*.md.

    Facets:
      - title: front-matter title
      - summary: front-matter summary
      - description: front-matter description (operational definition)
      - triggers: front-matter triggers, joined
    """

    source_kind = "skills"
    text_version = "v1"  # bump on facet/frontmatter-mask change to force clean re-embed

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def iter_items(self) -> Iterator[FacetedItem]:
        root = self.repo_root / "codex/doctrine/skills"
        if not root.exists():
            return
        for path in sorted(root.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            front = _parse_yaml_frontmatter(text)
            if not front:
                continue
            skill_id = front.get("id") or path.stem
            title = front.get("title") or skill_id
            summary = front.get("summary") or ""
            description = front.get("description") or ""
            triggers = front.get("triggers") or []
            trigger_text = " | ".join(triggers) if isinstance(triggers, list) else str(triggers)
            yield FacetedItem(
                id=skill_id,
                source_path=str(path.relative_to(self.repo_root)),
                facets={
                    "title": title,
                    "summary": summary,
                    "description": description,
                    "triggers": trigger_text,
                },
                metadata={"kind": "skill", "family": front.get("family"), "title": title},
            )


def _parse_yaml_frontmatter(markdown: str) -> dict | None:
    # Skip leading HTML comments / blank lines (some skills front-load <!-- purpose: ... -->)
    pos = 0
    while True:
        m = re.match(r"\s*<!--[\s\S]*?-->\s*", markdown[pos:])
        if not m:
            break
        pos += m.end()
    body_start = re.match(r"\s*---\s*\n", markdown[pos:])
    if not body_start:
        return None
    after_first = pos + body_start.end()
    end_marker = re.search(r"\n---\s*\n", markdown[after_first:])
    if not end_marker:
        return None
    body = markdown[after_first : after_first + end_marker.start()]
    out: dict = {}
    current_key: str | None = None
    for line in body.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            out.setdefault(current_key, []).append(line[4:].strip().strip('"'))
            continue
        kv = re.match(r"^([a-zA-Z_][\w-]*)\s*:\s*(.*)$", line)
        if not kv:
            continue
        key = kv.group(1).strip()
        value = kv.group(2).strip()
        current_key = key
        if value == "":
            out[key] = []
        elif value.startswith('"') and value.endswith('"'):
            out[key] = value.strip('"')
        else:
            out[key] = value
    return out


# --------------------------------------------------------------------------- #
# Standards JSON
# --------------------------------------------------------------------------- #


def _is_standard_payload(path: Path, payload: dict[str, Any]) -> bool:
    if path.name.startswith("std_"):
        return True
    kind = str(payload.get("kind") or payload.get("type") or "").strip().lower()
    if kind == "standard":
        return True
    ident = str(payload.get("id") or "").strip()
    return ident.startswith("std_")


def _standard_constraints(payload: dict[str, Any]) -> str:
    scope = payload.get("scope") or {}
    graph_contract = payload.get("graph_contract") or {}
    return _join_text_parts(
        payload.get("non_goals"),
        payload.get("invariants"),
        (scope.get("does_not_apply_to") if isinstance(scope, dict) else None),
        graph_contract.get("row_rule") if isinstance(graph_contract, dict) else None,
        graph_contract.get("rebuild_rule") if isinstance(graph_contract, dict) else None,
    )


def _standard_consumers(payload: dict[str, Any]) -> str:
    governance = payload.get("governance") or {}
    authority_surfaces = payload.get("authority_surfaces") or {}
    return _join_text_parts(
        governance.get("consumers") if isinstance(governance, dict) else None,
        payload.get("consumers"),
        authority_surfaces.values() if isinstance(authority_surfaces, dict) else None,
    )


class StandardsJsonFacetedSource(SourceAdapter):
    """Authored standard JSON documents under codex/standards/."""

    source_kind = "standards_json"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def schema_hash(self) -> str | None:
        return _derived_schema_hash(self.repo_root, STD_JSON_FACETS_REL_PATH, salt=self.source_kind)

    def iter_items(self) -> Iterator[FacetedItem]:
        root = self.repo_root / "codex/standards"
        if not root.exists():
            return
        for path in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict) or not _is_standard_payload(path, payload):
                continue
            ident = str(payload.get("id") or path.stem).strip()
            title = str(payload.get("title") or ident).strip()
            schema_intent = _join_text_parts(
                payload.get("purpose"),
                payload.get("description"),
                payload.get("summary"),
            )
            constraints = _standard_constraints(payload)
            consumers = _standard_consumers(payload)
            anti_patterns = _join_text_parts(payload.get("anti_patterns"))
            yield FacetedItem(
                id=ident,
                source_path=str(path.relative_to(self.repo_root)),
                facets={
                    "title": title,
                    "schema_intent": schema_intent,
                    "constraints": constraints,
                    "consumers": consumers,
                    "anti_patterns": anti_patterns,
                },
                metadata={
                    "kind": "standard_json",
                    "title": title,
                    "slug": payload.get("slug"),
                    "schema_version": payload.get("schema_version"),
                },
            )


# --------------------------------------------------------------------------- #
# Annex notes
# --------------------------------------------------------------------------- #


class AnnexNotesSource(SourceAdapter):
    """Curated annex notes as one faceted item per note row."""

    source_kind = "annex_notes"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def schema_hash(self) -> str | None:
        return _derived_schema_hash(self.repo_root, STD_JSON_FACETS_REL_PATH, salt=self.source_kind)

    def iter_items(self) -> Iterator[FacetedItem]:
        root = self.repo_root / "annexes"
        if not root.exists():
            return
        for path in sorted(root.glob("*/annex_notes.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            slug = str(payload.get("slug") or path.parent.name).strip()
            for note in payload.get("notes") or []:
                if not isinstance(note, dict):
                    continue
                note_id = str(note.get("id") or "").strip()
                note_text = str(note.get("note") or "").strip()
                if not note_id or not note_text:
                    continue
                title = _note_title(note_text, fallback=f"{slug}:{note_id}")
                pattern_intent, local_translation_text = _split_annex_note(note_text)
                routing = note.get("routing") or {}
                yield FacetedItem(
                    id=f"{slug}::{note_id}",
                    source_path=str(path.relative_to(self.repo_root)),
                    facets={
                        "title": title,
                        "pattern_intent": pattern_intent or note_text,
                        "local_translation": local_translation_text,
                        "problem_spaces": _join_text_parts(
                            routing.get("problem_spaces") if isinstance(routing, dict) else None,
                        ),
                    },
                    metadata={
                        "kind": "annex_note",
                        "slug": slug,
                        "note_id": note_id,
                        "title": title,
                        "tags": list(note.get("tags") or []),
                        "relevance": note.get("relevance"),
                    },
                )


# --------------------------------------------------------------------------- #
# Raw-seed shards
# --------------------------------------------------------------------------- #

class RawSeedShardSource(SourceAdapter):
    """Family atomized raw-seed shards from the authoritative extracted_shards.json.

    Facets:
      - clarified: clarified_statement
      - voice_anchor: preserved Will-voice
      - gestures: gestures_towards joined
    """

    source_kind = "raw_seed_shards"
    text_version = "v1"  # bump on shard-facet extraction change to force clean re-embed

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def iter_items(self) -> Iterator[FacetedItem]:
        for family_payload in _phase_family_payloads(self.repo_root):
            selected = self._shard_file_for_family(family_payload)
            if selected is None:
                continue
            shards_file, source_scope = selected
            payload = _load_json_object(shards_file)
            if not payload:
                continue
            rel = str(shards_file.relative_to(self.repo_root))
            family_number = str(family_payload.get("family_number") or "").strip()
            family_dir = str(family_payload.get("family_dir") or "").strip()
            for shard in payload.get("shards") or []:
                if not isinstance(shard, dict):
                    continue
                shard_id = str(shard.get("id") or shard.get("shard_id") or "").strip()
                if not shard_id:
                    continue
                clarified = str(shard.get("clarified_statement") or shard.get("statement") or "").strip()
                anchor = str(shard.get("voice_anchor") or shard.get("raw_seed_anchor") or "").strip()
                gestures = _string_list(shard.get("gestures_towards"))
                if not (clarified or anchor or gestures):
                    continue
                yield FacetedItem(
                    id=shard_id,
                    source_path=rel,
                    facets={
                        "clarified": clarified,
                        "voice_anchor": anchor,
                        "gestures": " | ".join(gestures),
                    },
                    metadata={
                        "kind": "raw_seed_shard",
                        "family_number": family_number,
                        "family_dir": family_dir,
                        "source_scope": source_scope,
                        "parent_paragraph_id": str(shard.get("parent_paragraph_id") or "").strip(),
                        "raw_paragraph_ids": _string_list(shard.get("raw_paragraph_ids")),
                        "gestures_towards": gestures,
                        "atomization_source": str(shard.get("atomization_source") or "").strip(),
                        "distillation_confidence": shard.get("distillation_confidence"),
                    },
                )

    def _shard_file_for_family(self, family_payload: dict[str, Any]) -> tuple[Path, str] | None:
        family_dir = str(family_payload.get("family_dir") or "").strip()
        active_phase_dir = str(family_payload.get("active_phase_dir") or "").strip()
        candidates: list[tuple[Path, str]] = []
        if family_dir:
            family_root = self.repo_root / family_dir
            candidates.append((family_root / "extracted_shards.json", "family_root"))
        if active_phase_dir:
            candidates.append((self.repo_root / active_phase_dir / "extracted_shards.json", "active_phase"))
        if family_dir:
            candidates.append((self.repo_root / family_dir / "raw_seed" / "extracted_shards.json", "legacy_raw_seed_dir"))
        for path, source_scope in candidates:
            if path.exists():
                return path, source_scope
        return None


# --------------------------------------------------------------------------- #
# Raw-seed paragraphs
# --------------------------------------------------------------------------- #


class RawSeedParagraphSource(SourceAdapter):
    """Live family raw-seed paragraphs with paragraph->shard lineage metadata.

    Facets:
      - section_heading: parent section heading
      - keywords: keyword_hints joined
      - mechanisms: mechanism_hints joined
      - body: plain_text
    """

    source_kind = "raw_seed_paragraphs"
    text_version = "v1"  # bump on paragraph-facet / lineage-projection change to force clean re-embed

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def iter_items(self) -> Iterator[FacetedItem]:
        for family_payload in _phase_family_payloads(self.repo_root):
            family_dir = str(family_payload.get("family_dir") or "").strip()
            if not family_dir:
                continue
            raw_seed_rel = str(family_payload.get("raw_seed_json_path") or "").strip()
            raw_seed_payload: dict[str, Any] | None = None
            if raw_seed_rel:
                raw_seed_payload = _load_json_object(self.repo_root / raw_seed_rel)
            if raw_seed_payload is None:
                try:
                    raw_seed_payload = build_raw_seed_payload_for_family(self.repo_root, family_payload)
                except Exception:
                    continue
            if not raw_seed_payload:
                continue
            raw_seed_path = str(raw_seed_payload.get("raw_seed_path") or family_payload.get("raw_seed_path") or raw_seed_rel)
            sections_by_id = {
                str(section.get("id") or "").strip(): dict(section)
                for section in raw_seed_payload.get("sections", [])
                if isinstance(section, dict) and str(section.get("id") or "").strip()
            }
            raw_seed_shards = build_raw_seed_shards(raw_seed_payload).get("shards") or []
            raw_shards_by_paragraph: dict[str, list[str]] = defaultdict(list)
            for shard in raw_seed_shards:
                if not isinstance(shard, dict):
                    continue
                parent_paragraph_id = str(shard.get("parent_paragraph_id") or "").strip()
                shard_id = str(shard.get("shard_id") or shard.get("id") or "").strip()
                if not parent_paragraph_id or not shard_id:
                    continue
                raw_shards_by_paragraph[parent_paragraph_id].append(shard_id)
            extracted_shards_by_paragraph = self._active_extracted_shards_by_paragraph(family_payload)

            for paragraph in raw_seed_payload.get("paragraphs", []):
                if not isinstance(paragraph, dict):
                    continue
                paragraph_id = str(paragraph.get("id") or "").strip()
                body = str(paragraph.get("plain_text") or "").strip()
                if not paragraph_id or not body:
                    continue
                section = sections_by_id.get(str(paragraph.get("section_id") or "").strip()) or {}
                raw_shard_ids = sorted(set(raw_shards_by_paragraph.get(paragraph_id) or []))
                extracted_shard_ids = sorted(set(extracted_shards_by_paragraph.get(paragraph_id) or []))
                yield FacetedItem(
                    id=paragraph_id,
                    source_path=raw_seed_path,
                    facets={
                        "section_heading": str(section.get("heading") or "").strip(),
                        "keywords": " | ".join(_string_list(paragraph.get("keyword_hints"))),
                        "mechanisms": " | ".join(_string_list(paragraph.get("mechanism_hints"))),
                        "body": body,
                    },
                    metadata={
                        "kind": "raw_seed_paragraph",
                        "family_number": str(raw_seed_payload.get("family_number") or family_payload.get("family_number") or "").strip(),
                        "family_dir": family_dir,
                        "section_id": str(paragraph.get("section_id") or "").strip(),
                        "section_path": str(paragraph.get("section_path") or "").strip(),
                        "line_start": paragraph.get("line_start"),
                        "line_end": paragraph.get("line_end"),
                        "source_substrate": str(paragraph.get("source_substrate") or "raw_seed").strip(),
                        "authored_by": str(paragraph.get("authored_by") or "operator").strip(),
                        "raw_shard_ids": raw_shard_ids,
                        "extracted_shard_ids": extracted_shard_ids,
                    },
                )

    def _active_extracted_shards_by_paragraph(self, family_payload: dict[str, Any]) -> dict[str, list[str]]:
        active_phase_dir = str(family_payload.get("active_phase_dir") or "").strip()
        if not active_phase_dir:
            return {}
        extracted_path = self.repo_root / active_phase_dir / "extracted_shards.json"
        payload = _load_json_object(extracted_path)
        if not payload:
            return {}
        mapping: dict[str, list[str]] = defaultdict(list)
        for shard in payload.get("shards", []):
            if not isinstance(shard, dict):
                continue
            shard_id = str(shard.get("id") or shard.get("shard_id") or "").strip()
            if not shard_id:
                continue
            paragraph_ids = _string_list(shard.get("raw_paragraph_ids"))
            parent_paragraph_id = str(shard.get("parent_paragraph_id") or "").strip()
            if parent_paragraph_id and parent_paragraph_id not in paragraph_ids:
                paragraph_ids.append(parent_paragraph_id)
            for paragraph_id in paragraph_ids:
                mapping[paragraph_id].append(shard_id)
        return {paragraph_id: sorted(set(ids)) for paragraph_id, ids in mapping.items()}


# --------------------------------------------------------------------------- #
# Raw-seed compressed navigation runtime
# --------------------------------------------------------------------------- #


def _neighbor_group_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = ""
        if isinstance(item, dict):
            token = str(item.get("group_id") or "").strip()
        else:
            token = str(item or "").strip()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _target_keys_from_cards(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        token = str(item.get("target_key") or item.get("id") or item.get("target") or "").strip()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


class RawSeedNavigationSource(SourceAdapter):
    """Family raw-seed compressed navigation runtime groups.

    Facets:
      - title: group title
      - gloss: structural group gloss
      - compression: cached NVIDIA/local seed sentences and compression summary
      - graph_context: keywords, mechanisms, sections, neighbors, entrypoint hints
      - lineage: paragraph ids, representative shards, target cards
    """

    source_kind = "raw_seed_navigation"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def schema_hash(self) -> str | None:
        return _derived_schema_hash(self.repo_root, STD_JSON_FACETS_REL_PATH, salt=self.source_kind)

    def iter_items(self) -> Iterator[FacetedItem]:
        for family_payload in _phase_family_payloads(self.repo_root):
            family_dir = str(family_payload.get("family_dir") or "").strip()
            if not family_dir:
                continue
            runtime_path = self.repo_root / family_dir / "raw_seed" / "raw_seed_navigation_runtime.json"
            runtime_payload = _load_json_object(runtime_path)
            if not runtime_payload:
                continue
            family_number = str(
                (runtime_payload.get("family") or {}).get("family_number")
                or family_payload.get("family_number")
                or ""
            ).strip()
            source_path = str(runtime_path.relative_to(self.repo_root))
            for group in runtime_payload.get("groups") or []:
                if not isinstance(group, dict):
                    continue
                group_id = str(group.get("group_id") or "").strip()
                if not group_id:
                    continue
                title = str(group.get("title") or group_id).strip()
                gloss = str(group.get("gloss") or "").strip()
                compression = group.get("compression") if isinstance(group.get("compression"), dict) else {}
                entrypoint = group.get("entrypoint") if isinstance(group.get("entrypoint"), dict) else {}
                representative_shards = group.get("representative_shards") or []
                target_cards = group.get("target_cards_top") or []
                neighbor_ids = sorted(
                    set(
                        _neighbor_group_ids(group.get("neighbor_groups_top"))
                        + _string_list(compression.get("neighbor_group_ids") if isinstance(compression, dict) else None)
                        + _string_list(entrypoint.get("next_group_ids") if isinstance(entrypoint, dict) else None)
                    )
                )
                target_keys = sorted(
                    set(
                        _target_keys_from_cards(target_cards)
                        + _string_list(compression.get("target_keys") if isinstance(compression, dict) else None)
                    )
                )
                paragraph_ids = sorted(
                    set(
                        _string_list(group.get("paragraph_ids_top"))
                        + _string_list(compression.get("paragraph_ref_ids") if isinstance(compression, dict) else None)
                    )
                )
                shard_lines: list[str] = []
                if isinstance(representative_shards, list):
                    for shard in representative_shards[:8]:
                        if not isinstance(shard, dict):
                            continue
                        shard_lines.append(
                            _join_text_parts(
                                shard.get("id"),
                                shard.get("statement"),
                                shard.get("voice_anchor"),
                            )
                        )
                source_sections = []
                for section in group.get("source_sections_top") or []:
                    if isinstance(section, dict):
                        source_sections.append(_join_text_parts(section.get("heading"), section.get("section_path")))
                compression_text = _join_text_parts(
                    compression.get("seed_sentences") if isinstance(compression, dict) else None,
                    compression.get("summary") if isinstance(compression, dict) else None,
                    compression.get("why_this_size") if isinstance(compression, dict) else None,
                )
                graph_context = _join_text_parts(
                    group.get("keyword_hints_top"),
                    group.get("mechanism_hints_top"),
                    source_sections,
                    neighbor_ids,
                    entrypoint,
                )
                lineage = _join_text_parts(
                    paragraph_ids,
                    shard_lines,
                    target_keys,
                    target_cards,
                )
                yield FacetedItem(
                    id=f"family_{family_number}__{group_id}" if family_number else group_id,
                    source_path=source_path,
                    facets={
                        "title": title,
                        "gloss": gloss,
                        "compression": compression_text,
                        "graph_context": graph_context,
                        "lineage": lineage,
                    },
                    metadata={
                        "kind": "raw_seed_navigation_group",
                        "family_number": family_number,
                        "family_dir": family_dir,
                        "group_id": group_id,
                        "title": title,
                        "shard_count": group.get("shard_count"),
                        "paragraph_count": group.get("paragraph_count"),
                        "cached": bool(compression),
                        "compression_mode": compression.get("compression_mode") if isinstance(compression, dict) else None,
                        "paragraph_ids": paragraph_ids,
                        "neighbor_group_ids": neighbor_ids,
                        "target_keys": target_keys,
                        "commands": dict(group.get("commands") or {}),
                        "source_bundle_path": compression.get("source_bundle_path") if isinstance(compression, dict) else None,
                        "source_result_path": compression.get("source_result_path") if isinstance(compression, dict) else None,
                    },
                )


# --------------------------------------------------------------------------- #
# Archaeological shards
# --------------------------------------------------------------------------- #

class ArchaeologyShardSource(SourceAdapter):
    """state/voice_archaeology/archaeological_shards.json.

    Facets:
      - clarified: clarified_statement
      - voice_anchor: preserved archaeological voice (verbatim or inferred)
      - gestures: gestures_towards joined
      - new_dimension: coverage_check.new_dimension (what THIS shard adds beyond covered nodes)
    """

    source_kind = "archaeology_shards"
    text_version = "v1"  # bump on archaeological-shard facet/sub-field change to force clean re-embed

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def iter_items(self) -> Iterator[FacetedItem]:
        path = self.repo_root / "state/voice_archaeology/archaeological_shards.json"
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        rel = str(path.relative_to(self.repo_root))
        for shard in payload.get("shards", []):
            shard_id = shard.get("id")
            if not shard_id:
                continue
            clarified = shard.get("clarified_statement") or ""
            anchor = shard.get("voice_anchor") or ""
            gestures = shard.get("gestures_towards") or []
            new_dim = (shard.get("coverage_check") or {}).get("new_dimension") or ""
            if not clarified:
                continue
            yield FacetedItem(
                id=shard_id,
                source_path=rel,
                facets={
                    "clarified": clarified,
                    "voice_anchor": anchor,
                    "gestures": " | ".join(gestures),
                    "new_dimension": new_dim,
                },
                metadata={
                    "kind": "archaeological_shard",
                    "source_file": shard.get("source_file_path"),
                    "voice_date": shard.get("voice_date"),
                    "depth": shard.get("archaeological_depth"),
                    "domain": shard.get("source_file_domain"),
                },
            )


# --------------------------------------------------------------------------- #
# Python holographic — std_python.py contract atoms parsed as facets
# --------------------------------------------------------------------------- #

STD_PYTHON_REL_PATH = "codex/standards/std_python.py"
PYTHON_HOLO_ROOTS = ["system/lib", "system/server", "tools/meta/factory", "tools/meta/control"]

# std_python.py module-level required tags
MODULE_TAGS = ("PURPOSE", "INTERFACE", "FLOW", "DEPENDENCIES", "CONSTRAINTS")

# Contract atoms inside [PURPOSE] / [ACTION] / [ROLE] payloads
CONTRACT_ATOMS = (
    "Teleology", "Mechanism", "Guarantee", "Forbid", "Fails",
    "Warns", "Reads", "Writes", "Locks", "Orders", "Schema",
    "Couples", "Non-goal", "When-needed", "Escalates-to", "Navigation-group",
)


def parse_std_python_atoms(docstring: str) -> dict[str, str]:
    """Parse a std_python.py-style module docstring into per-atom facets.

    Strategy:
      1. Split into [TAG] sections (PURPOSE / INTERFACE / FLOW / DEPENDENCIES / CONSTRAINTS).
      2. For each section, also split out contract atoms (Teleology:, Mechanism:, Guarantee:, Reads:, Writes:, Couples:, Non-goal:, Fails:, When-needed:, Escalates-to:).
      3. Return a flat facet map. Atom keys are lowercased and slugified ("non_goal", "when_needed", "escalates_to", "navigation_group").
    """
    if not docstring:
        return {}
    atoms: dict[str, str] = {}

    # Split by [TAG] headings; capture payload until next [TAG]
    tag_re = re.compile(r"\[(" + "|".join(MODULE_TAGS) + r"|ACTION|ROLE)\]\s*\n", re.MULTILINE)
    matches = list(tag_re.finditer(docstring))
    if matches:
        for i, m in enumerate(matches):
            tag = m.group(1).lower()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(docstring)
            body = docstring[start:end].strip()
            atoms[tag] = body[:1800]
            # mine contract atoms from the payload
            for atom in CONTRACT_ATOMS:
                pat = re.compile(
                    rf"(?:^|\n)\s*-?\s*\*{{0,2}}{re.escape(atom)}\*{{0,2}}\s*:\s*(.+?)(?=\n\s*-?\s*\*{{0,2}}(?:"
                    + "|".join(re.escape(a) for a in CONTRACT_ATOMS)
                    + r")\*{0,2}\s*:|\n\[|\Z)",
                    re.DOTALL,
                )
                am = pat.search(body)
                if am:
                    key = atom.lower().replace("-", "_")
                    text = re.sub(r"\s+", " ", am.group(1)).strip()
                    if text:
                        atoms[key] = text[:1200]
    else:
        # Fallback: whole docstring becomes a single "purpose" facet
        atoms["purpose"] = docstring.strip()[:1800]
    return atoms


def _module_signatures(tree: ast.Module) -> str:
    lines: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            lines.append(_signature_line(node))
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            lines.append(f"class {node.name}")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                    lines.append("  " + _signature_line(child))
    return "\n".join(lines)[:1500]


def _signature_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = []
    for arg in node.args.args:
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        args.append(f"{arg.arg}{ann}")
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    for arg in node.args.kwonlyargs:
        args.append(f"{arg.arg}")
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    return f"{prefix}{node.name}({', '.join(args)}){ret}"


class PythonHolographicSource(SourceAdapter):
    """Python files in PYTHON_HOLO_ROOTS, projected as a vector field of std_python.py contract atoms.

    Facets per module (whichever the docstring populates):
      - purpose, interface, flow, dependencies, constraints  (the five module-level tags)
      - teleology, mechanism, guarantee, fails, reads, writes, locks, orders, schema, couples, non_goal, when_needed, escalates_to, navigation_group  (contract atoms inside the tag payloads)
      - signatures: ast-derived signature listing (top-level public callables and classes)

    schema_hash() is sha256(std_python.py). Editing the standard forces a full
    re-embed across every Python module — `std_python enforcement and the
    holographic surface are the inhale and exhale of one self-awareness loop`
    (par_phase_05_4...001).
    """

    source_kind = "python_holographic"

    def __init__(self, repo_root: Path, roots: list[str] | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.roots = roots or PYTHON_HOLO_ROOTS

    def schema_hash(self) -> str | None:
        return _sha256_file(self.repo_root / STD_PYTHON_REL_PATH)

    def iter_items(self) -> Iterator[FacetedItem]:
        for root in self.roots:
            base = self.repo_root / root
            if not base.exists():
                continue
            for path in sorted(base.rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                try:
                    source = path.read_text(encoding="utf-8")
                except Exception:
                    continue
                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    continue
                docstring = ast.get_docstring(tree) or ""
                facets = parse_std_python_atoms(docstring)
                signatures = _module_signatures(tree)
                if signatures:
                    facets["signatures"] = signatures
                if not facets:
                    continue
                rel = str(path.relative_to(self.repo_root))
                yield FacetedItem(
                    id=rel,
                    source_path=rel,
                    facets=facets,
                    metadata={"kind": "python_holographic", "module_path": rel},
                )


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

SOURCE_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "doctrine": DoctrineSource,
    "paper_modules": PaperModuleSource,
    "skills": SkillSource,
    "raw_seed_paragraphs": RawSeedParagraphSource,
    "raw_seed_shards": RawSeedShardSource,
    "raw_seed_navigation": RawSeedNavigationSource,
    "archaeology_shards": ArchaeologyShardSource,
    "standards_json": StandardsJsonFacetedSource,
    "annex_notes": AnnexNotesSource,
    "python_holographic": PythonHolographicSource,
}


def build_adapter(name: str, repo_root: Path) -> SourceAdapter:
    cls = SOURCE_ADAPTERS.get(name)
    if cls is None:
        raise KeyError(f"unknown source adapter: {name}")
    return cls(repo_root)  # type: ignore[call-arg]


def all_source_kinds() -> list[str]:
    return sorted(SOURCE_ADAPTERS.keys())
