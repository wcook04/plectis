"""Raw-seed registry, index, and projection helpers for family raw_seed surfaces.

[PURPOSE]
- Teleology: Compile family raw_seed markdown into the structured raw-seed registry, navigation index, and projection surfaces consumed by kernel routing.
- Mechanism: Normalize family-relative paths, parse markdown/frontmatter into sections and paragraphs, enrich paragraph hints from corpus statistics, and emit registry/index/projection artifacts.

[INTERFACE]
- Exports: family path helpers, load_raw_seed_payload, build_raw_seed_payload, build_raw_seed_payload_for_family, resolve_raw_seed_ref, build_raw_seed_index, project_raw_seed_index_slice, annotate_raw_seed_payload, render_raw_seed_markdown, project_raw_seed.
- Reads: family raw_seed markdown, existing raw_seed.json payloads, and supporting path/markdown/keyphrase/spelling helpers.
- Outputs: raw_seed registry payloads, compact navigation indexes, filtered projections, annotation updates, and markdown projections.

[FLOW]
- Family-relative path helpers compute stable raw-seed artifact locations.
- build_raw_seed_payload parses raw_seed markdown into sections/paragraphs and enriches hint lanes.
- build_raw_seed_index and project_raw_seed_index_slice derive compact routing surfaces from the registry payload.
- annotate_raw_seed_payload, render_raw_seed_markdown, and project_raw_seed support mutation-safe updates and downstream projections.

[DEPENDENCIES]
- system.lib.codex_paths: canonicalize_write_path for repo-safe artifact locations.
- system.lib.markdown_routing: frontmatter parsing and markdown rendering.
- system.lib.raw_seed_keyphrase: corpus stats, hint extraction, and term-ledger builders.
- system.lib.raw_seed_spelling: corpus lexicon and hint normalizer builders.

[CONSTRAINTS]
- Registry and index payloads are structural routing surfaces; the raw-seed markdown/JSON substrate remains the authority.
- Family path helpers return repo-relative strings only.
- When-needed: Open when raw-seed work needs the exact registry/index/projection contracts, family artifact paths, or annotation/render rules instead of reading the emitted JSON artifacts directly.
- Escalates-to: codex/standards/observe_apply/std_raw_seed.md; system/lib/raw_seed_keyphrase.py; system/lib/raw_seed_spelling.py; system/lib/kernel_nav_lens.py
- Navigation-group: kernel_lib
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.codex_paths import canonicalize_write_path
from system.lib.markdown_routing import parse_frontmatter, render_markdown_document, split_frontmatter
from system.lib.raw_seed_keyphrase import (
    build_corpus_token_stats,
    build_term_ledger_payload,
    high_df_omit_unigrams,
    merge_distinctive_keyword_hints,
    merged_stopwords,
)
from system.lib.raw_seed_spelling import (
    SPELLING_NORMALIZATION_VERSION,
    build_corpus_lexicon,
    build_corpus_hint_normalizer,
)

RAW_SEED_SCHEMA_VERSION = "raw_seed_v1"
RAW_SEED_INDEX_SCHEMA_VERSION = "raw_seed_index_v4"
RAW_SEED_SHARDS_SCHEMA_VERSION = "raw_seed_shards_v1"
RAW_SEED_NAVIGATION_GRAPH_SCHEMA_VERSION = "raw_seed_navigation_graph_v1"
AGENT_SEED_SCHEMA_VERSION = "agent_seed_v1"

# Cap inverted keyword lists in raw_seed_index.json only (full lists remain on each paragraph).
KEYWORD_HINT_INDEX_MAX_PARAGRAPH_IDS = 500
RAW_SEED_FILENAME = "raw_seed.md"
RAW_SEED_JSON_FILENAME = "raw_seed.json"
RAW_SEED_INDEX_FILENAME = "raw_seed_index.json"
RAW_SEED_SHARDS_FILENAME = "raw_seed_shards.json"
RAW_SEED_NAVIGATION_GRAPH_FILENAME = "raw_seed_navigation_graph.json"
RAW_SEED_PRINCIPLES_FILENAME = "raw_seed_principles.json"
RAW_SEED_SNAPSHOT_FILENAME = "raw_seed.snapshot.md"
RAW_SEED_META_FILENAME = "raw_seed_meta.md"
RAW_SEED_TRACING_SURFACES_FILENAME = "raw_seed_tracing_surfaces.md"
RAW_SEED_NAVIGATION_NOTES_FILENAME = "raw_seed_navigation_notes.md"
RAW_SEED_TERM_LEDGER_FILENAME = "raw_seed_term_ledger.json"
RAW_SEED_WORKSPACE_DIRNAME = "raw_seed"
RAW_SEED_MARKER_PREFIX = "<!-- RAW_SEED_"
AGENT_SEED_FILENAME = "agent_seed.md"
AGENT_SEED_JSON_FILENAME = "agent_seed.json"
AGENT_SEED_SNAPSHOT_FILENAME = "agent_seed.snapshot.md"
AGENT_SEED_MARKER_PREFIX = "<!-- AGENT_SEED_"

SUBSTRATE_PROFILES: dict[str, dict[str, Any]] = {
    "raw_seed": {
        "substrate": "raw_seed",
        "kind": "raw_seed_registry",
        "schema_version": RAW_SEED_SCHEMA_VERSION,
        "markdown_filename": RAW_SEED_FILENAME,
        "json_filename": RAW_SEED_JSON_FILENAME,
        "snapshot_filename": RAW_SEED_SNAPSHOT_FILENAME,
        "marker_prefix": RAW_SEED_MARKER_PREFIX,
        "sync_marker": "RAW_SEED_SYNC",
        "usage_marker": "RAW_SEED_USAGE",
        "usage_rule_marker": "RAW_SEED_USAGE_RULE",
        "usage_doc_marker": "RAW_SEED_USAGE_DOC",
        "usage_skill_marker": "RAW_SEED_USAGE_SKILL",
        "usage_command_marker": "RAW_SEED_USAGE_COMMAND",
        "section_marker": "RAW_SEED_SECTION",
        "paragraph_marker": "RAW_SEED_PARAGRAPH",
        "section_id_prefix": "sec",
        "paragraph_id_prefix": "par",
        "root_section_id": "sec_root",
        "root_heading": "ROOT",
        "source_substrate": "raw_seed",
        "supports_authored_by": False,
    },
    "agent_seed": {
        "substrate": "agent_seed",
        "kind": "agent_seed_registry",
        "schema_version": AGENT_SEED_SCHEMA_VERSION,
        "markdown_filename": AGENT_SEED_FILENAME,
        "json_filename": AGENT_SEED_JSON_FILENAME,
        "snapshot_filename": AGENT_SEED_SNAPSHOT_FILENAME,
        "marker_prefix": AGENT_SEED_MARKER_PREFIX,
        "sync_marker": "AGENT_SEED_SYNC",
        "usage_marker": "AGENT_SEED_USAGE",
        "usage_rule_marker": "AGENT_SEED_USAGE_RULE",
        "usage_doc_marker": "AGENT_SEED_USAGE_DOC",
        "usage_skill_marker": "AGENT_SEED_USAGE_SKILL",
        "usage_command_marker": "AGENT_SEED_USAGE_COMMAND",
        "section_marker": "AGENT_SEED_SECTION",
        "paragraph_marker": "AGENT_SEED_PARAGRAPH",
        "section_id_prefix": "sec_agent",
        "paragraph_id_prefix": "par_agent",
        "root_section_id": "sec_agent_root",
        "root_heading": "AGENT_ROOT",
        "source_substrate": "agent_seed",
        "supports_authored_by": True,
    },
}

# Paragraph hint lanes (see codex/standards/observe_apply/std_raw_seed.md, RAW_SEED_FRAMEWORK.md):
# - mechanism_hints: **Nav vocabulary** — stable repo jargon for raw_seed_index theme traversal
#   (`mechanism_to_ids`, --seed-index-mechanism). Not the same as doctrine `mech_*` artifacts.
# - keyword_hints: **Distinctive terms** — family-corpus salience from paragraph body text only;
#   pointer refs, URLs, and path-like tokens should not pollute this lane.
STOP_WORDS = {
    "the", "and", "that", "this", "with", "from", "into", "then", "than", "they", "them", "their", "there",
    "have", "has", "had", "what", "when", "where", "which", "while", "would", "could", "should", "just",
    "like", "kind", "sort", "really", "very", "also", "only", "even", "more", "much", "some", "such", "than",
    "your", "ours", "our", "you", "its", "it's", "i'm", "ive", "can't", "dont", "doesn't", "didn't", "because",
    "about", "through", "across", "around", "under", "over", "again", "still", "being", "been", "make", "made",
    "need", "needs", "want", "wants", "using", "used", "doing", "does", "done", "thing", "things", "idea", "ideas",
    "system", "seed", "raw", "phase",
}
MECHANISM_PHRASES = (
    "raw seed",
    "synth seed",
    "reference ledger",
    "meta ledger",
    "state machine",
    "control plane",
    "campaign runner",
    "observe apply",
    "observe plan",
    "factory runner",
    "seed pipeline",
    "doctrine surface",
    "typed receipt",
    "pipeline state",
    "bridge",
    "kernel",
    "mission",
    "missions",
    "oracle",
    "lab",
    "skills",
    "skill",
    "doctrine",
    "json",
    "markdown",
    "schema",
    "contract",
    "holographic",
    "builder",
    "vector",
    "vectors",
    "paragraph",
    "paragraphs",
    "section",
    "sections",
    "group",
    "groups",
    "node",
    "nodes",
    "graph",
    "context",
    "prompt",
    "prompts",
    "python",
    "ui",
    "frontend",
    "annex",
)

_MECHANISM_PHRASES_SORTED: tuple[str, ...] = tuple(sorted(MECHANISM_PHRASES, key=lambda p: (-len(p), p)))


def _mechanism_vocab_unigrams() -> frozenset[str]:
    out: set[str] = set()
    for phrase in MECHANISM_PHRASES:
        for w in phrase.split():
            t = w.strip().casefold()
            if len(t) >= 2:
                out.add(t)
    return frozenset(out)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _slugify(value: str) -> str:
    token = re.sub(r"[^\w\s-]+", " ", _string(value), flags=re.UNICODE)
    token = re.sub(r"[_\s]+", "-", token.strip().casefold())
    token = re.sub(r"-{2,}", "-", token).strip("-")
    return token or "untitled"


def _plain_text(block: str) -> str:
    return re.sub(r"\s+", " ", str(block or "").strip())


def _fingerprint(block: str) -> str:
    return hashlib.sha1(_plain_text(block).encode("utf-8")).hexdigest()[:16]


def _paragraph_sync_provenance(
    paragraph: Mapping[str, Any],
    existing_paragraph: Mapping[str, Any],
) -> dict[str, Any] | None:
    previous_fingerprint = _string(existing_paragraph.get("paragraph_fingerprint")) or _string(existing_paragraph.get("fingerprint"))
    current_fingerprint = _string(paragraph.get("paragraph_fingerprint")) or _string(paragraph.get("fingerprint"))
    if not previous_fingerprint or not current_fingerprint:
        return None

    prior = existing_paragraph.get("sync_provenance")
    prior_provenance = dict(prior) if isinstance(prior, Mapping) else {}
    previous_revision_count = int(prior_provenance.get("revision_count") or 0)

    if previous_fingerprint == current_fingerprint:
        if not prior_provenance:
            return None
        updated = dict(prior_provenance)
        updated["status"] = "in_sync"
        updated["current_fingerprint"] = current_fingerprint
        updated["current_line_start"] = int(paragraph.get("line_start") or 0)
        updated["current_line_end"] = int(paragraph.get("line_end") or 0)
        return updated

    history = [dict(item) for item in prior_provenance.get("history", []) if isinstance(item, Mapping)]
    history.append(
        {
            "fingerprint": previous_fingerprint,
            "line_start": int(existing_paragraph.get("line_start") or 0),
            "line_end": int(existing_paragraph.get("line_end") or 0),
            "raw_markdown": _string(existing_paragraph.get("raw_markdown")),
        }
    )
    history = history[-5:]

    return {
        "status": "modified_after_sync",
        "revision_count": previous_revision_count + 1,
        "detected_at": _utc_now(),
        "previous_fingerprint": previous_fingerprint,
        "current_fingerprint": current_fingerprint,
        "previous_line_start": int(existing_paragraph.get("line_start") or 0),
        "previous_line_end": int(existing_paragraph.get("line_end") or 0),
        "current_line_start": int(paragraph.get("line_start") or 0),
        "current_line_end": int(paragraph.get("line_end") or 0),
        "previous_raw_markdown": _string(existing_paragraph.get("raw_markdown")),
        "history": history,
    }


_LIST_ITEM_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_FENCE_START_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_MARKDOWN_LINK_RE = re.compile(r"^\[[^\]]+\]\([^)]+\)\s*$")
_URL_RE = re.compile(r"^(?:https?|file)://\S+$", re.IGNORECASE)
_PATH_LINE_RE = re.compile(
    r"^(?:~?/|\.{1,2}/|[A-Za-z]:[\\/]|(?:[A-Za-z0-9_. -]+/)+[A-Za-z0-9_. -]+(?:\.[A-Za-z0-9]{1,8})?)"
)
_INLINE_URL_RE = re.compile(r"(?:https?|file)://\S+", re.IGNORECASE)
_INLINE_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
_INLINE_PATH_RE = re.compile(
    r"(?:~?/|\.{1,2}/|[A-Za-z]:[\\/])\S+|(?:[A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_. -]+\.[A-Za-z0-9]{1,8}"
)
_APPENDED_MARKER_RE = re.compile(r"^\s*<!--\s*appended\b.*-->\s*$", re.IGNORECASE)
_PARAGRAPH_MARKER_RE = re.compile(
    r"^\s*<!--\s+(?:RAW_SEED|AGENT_SEED)_PARAGRAPH\b.*-->\s*$",
    re.IGNORECASE,
)
_HARD_PARAGRAPH_GAP_BLANK_LINES = 2
_BACKREF_STARTERS = {"this", "that", "these", "those", "it", "such", "here"}
_PATHISH_HINT_RE = re.compile(
    r"(?:/|\\|^(?:https?|file):|^\[.+\]\(.+\)$|\.(?:md|json|py|yaml|yml|toml|txt|tsx|ts|jsx|js|html|css)$)",
    re.IGNORECASE,
)
_VERBISH_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|being|have|has|had|do|does|did|can|could|should|would|must|"
    r"need|needs|needed|make|makes|made|run|runs|running|track|tracks|tracked|launch|launches|launched|"
    r"poll|polls|polled|merge|merges|merged|emit|emits|emitted|route|routes|routed|build|builds|built|"
    r"[A-Za-z]+ing|[A-Za-z]+ed|[A-Za-z]+s)\b",
    re.IGNORECASE,
)


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _fence_token(line: str) -> tuple[str, int] | None:
    match = _FENCE_START_RE.match(line)
    if not match:
        return None
    token = match.group(1)
    return token[0], len(token)


def _is_list_item(line: str) -> bool:
    return bool(_LIST_ITEM_RE.match(line))


def _is_blockquote_line(line: str) -> bool:
    return line.lstrip().startswith(">")


def _reference_line_kind(line: str) -> str:
    stripped = _string(line)
    if not stripped:
        return ""
    if _MARKDOWN_LINK_RE.match(stripped):
        return "markdown_link"
    if _URL_RE.match(stripped):
        return "url"
    if re.search(r"\s[/\\\\]\s", stripped):
        return ""
    if (_PATH_LINE_RE.match(stripped) and ("/" in stripped or "\\" in stripped)) or re.match(r"^[A-Za-z]:[\\/]", stripped):
        return "path"
    return ""


def _looks_like_pathish_hint(token: str) -> bool:
    value = _string(token)
    if not value:
        return False
    if _PATHISH_HINT_RE.search(value):
        return True
    return False


def _strip_reference_like_tokens(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in str(text or "").splitlines():
        if _reference_line_kind(raw_line):
            continue
        line = _INLINE_MARKDOWN_LINK_RE.sub(" ", raw_line)
        line = _INLINE_URL_RE.sub(" ", line)
        line = _INLINE_PATH_RE.sub(" ", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _semantic_text(block: str) -> str:
    return _plain_text(re.sub(r"[`*_>#-]+", " ", str(block or "")))


def _semantic_tokens(block: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_'-]+", _semantic_text(block))


def _is_inline_label_only(block: str) -> bool:
    lines = [line.strip() for line in str(block or "").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    line = lines[0]
    if line.endswith((".", "!", "?")):
        return False
    for pattern in (r"^\*\*(.+?)\*\*$", r"^__(.+?)__$", r"^\*(.+?)\*$", r"^_(.+?)_$"):
        match = re.match(pattern, line)
        if not match:
            continue
        inner = _plain_text(match.group(1))
        if inner and len(inner.split()) <= 10 and not inner.endswith((".", "!", "?")):
            return True
    return False


def _starts_with_backward_reference(block: str) -> bool:
    match = re.match(r"[A-Za-z']+", _semantic_text(block))
    if not match:
        return False
    return match.group(0).casefold() in _BACKREF_STARTERS


def _should_merge_backward_reference(block: Mapping[str, Any]) -> bool:
    text = _string(block.get("raw_markdown"))
    if not _starts_with_backward_reference(text):
        return False
    tokens = [token.casefold() for token in _semantic_tokens(text)]
    if len(tokens) < 40:
        return True
    if len(tokens) >= 2 and tokens[1] in {"is", "are", "was", "were", "has", "have", "had", "can", "could", "should", "would", "must", "need", "needs"}:
        return True
    return False


def _is_semantic_fragment(block: Mapping[str, Any]) -> bool:
    if _string(block.get("kind")) != "text":
        return False
    tokens = [token for token in _semantic_tokens(_string(block.get("raw_markdown"))) if token.casefold() not in STOP_WORDS]
    if len(tokens) >= 5:
        return False
    return not _VERBISH_RE.search(_semantic_text(_string(block.get("raw_markdown"))))


def _new_block(kind: str, lines: list[tuple[int, str]], *, references: list[str] | None = None) -> dict[str, Any]:
    raw_markdown = "\n".join(line for _, line in lines).rstrip()
    line_numbers = [line_no for line_no, _ in lines] or [0]
    return {
        "kind": kind,
        "line_start": min(line_numbers),
        "line_end": max(line_numbers),
        "raw_markdown": raw_markdown,
        "references": _dedupe_strings([_string(item) for item in references or [] if _string(item)]),
    }


def _merge_blocks(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    raw_parts = [_string(left.get("raw_markdown")), _string(right.get("raw_markdown"))]
    raw_markdown = "\n\n".join([part for part in raw_parts if part])
    kind = _string(left.get("kind")) or _string(right.get("kind")) or "text"
    if kind == "text" and _string(right.get("kind")) and _string(right.get("kind")) != "text":
        kind = _string(right.get("kind"))
    references = _dedupe_strings(
        [_string(item) for item in left.get("references", []) if _string(item)]
        + [_string(item) for item in right.get("references", []) if _string(item)]
    )
    return {
        "kind": kind,
        "line_start": min(int(left.get("line_start") or 0), int(right.get("line_start") or 0)),
        "line_end": max(int(left.get("line_end") or 0), int(right.get("line_end") or 0)),
        "raw_markdown": raw_markdown,
        "references": references,
        "_leading_blank_lines": int(left.get("_leading_blank_lines") or 0),
    }


def _with_leading_gap(block: Mapping[str, Any], blank_lines: int) -> dict[str, Any]:
    current = dict(block)
    if blank_lines > 0:
        current["_leading_blank_lines"] = int(blank_lines)
    return current


def _has_hard_leading_gap(block: Mapping[str, Any]) -> bool:
    return int(block.get("_leading_blank_lines") or 0) >= _HARD_PARAGRAPH_GAP_BLANK_LINES


def _consume_fence_block(lines: list[tuple[int, str]], start: int) -> tuple[dict[str, Any], int]:
    token = _fence_token(lines[start][1])
    consumed = [lines[start]]
    if not token:
        return _new_block("fence", consumed), start + 1
    char, min_len = token
    index = start + 1
    while index < len(lines):
        consumed.append(lines[index])
        stripped = lines[index][1].strip()
        if stripped.startswith(char * min_len):
            index += 1
            break
        index += 1
    return _new_block("fence", consumed), index


def _consume_list_block(lines: list[tuple[int, str]], start: int) -> tuple[dict[str, Any], int]:
    consumed = [lines[start]]
    base_indent = _leading_spaces(lines[start][1])
    index = start + 1
    while index < len(lines):
        _, line = lines[index]
        stripped = line.strip()
        if not stripped:
            lookahead = index + 1
            while lookahead < len(lines) and not lines[lookahead][1].strip():
                lookahead += 1
            if lookahead < len(lines):
                next_line = lines[lookahead][1]
                if _is_list_item(next_line) or _leading_spaces(next_line) > base_indent:
                    consumed.extend(lines[index:lookahead])
                    index = lookahead
                    continue
            break
        if _is_list_item(line) or _leading_spaces(line) > base_indent:
            consumed.append(lines[index])
            index += 1
            continue
        break
    return _new_block("list", consumed), index


def _consume_blockquote_block(lines: list[tuple[int, str]], start: int) -> tuple[dict[str, Any], int]:
    consumed = [lines[start]]
    index = start + 1
    while index < len(lines):
        _, line = lines[index]
        stripped = line.strip()
        if not stripped:
            lookahead = index + 1
            while lookahead < len(lines) and not lines[lookahead][1].strip():
                lookahead += 1
            if lookahead < len(lines) and _is_blockquote_line(lines[lookahead][1]):
                consumed.extend(lines[index:lookahead])
                index = lookahead
                continue
            break
        if _is_blockquote_line(line):
            consumed.append(lines[index])
            index += 1
            continue
        break
    return _new_block("blockquote", consumed), index


def _consume_text_block(lines: list[tuple[int, str]], start: int) -> tuple[dict[str, Any], int]:
    consumed: list[tuple[int, str]] = []
    index = start
    while index < len(lines):
        _, line = lines[index]
        if _PARAGRAPH_MARKER_RE.match(line):
            break
        if not line.strip():
            lookahead = index
            while lookahead < len(lines) and not lines[lookahead][1].strip():
                lookahead += 1
            if (
                lookahead >= len(lines)
                or lookahead - index >= 2
                or _reference_line_kind(lines[lookahead][1])
                or _APPENDED_MARKER_RE.match(lines[lookahead][1])
                or _PARAGRAPH_MARKER_RE.match(lines[lookahead][1])
                or _fence_token(lines[lookahead][1])
                or _is_list_item(lines[lookahead][1])
                or _is_blockquote_line(lines[lookahead][1])
            ):
                break
            consumed.extend(lines[index:lookahead])
            index = lookahead
            continue
        consumed.append(lines[index])
        index += 1
    return _new_block("text", consumed), index


def _collect_semantic_blocks(section_lines: list[tuple[int, str]]) -> list[dict[str, Any]]:
    raw_blocks: list[dict[str, Any]] = []
    index = 0
    leading_blank_lines = 0

    def _append_raw_block(block: Mapping[str, Any]) -> None:
        nonlocal leading_blank_lines
        raw_blocks.append(_with_leading_gap(block, leading_blank_lines))
        leading_blank_lines = 0

    while index < len(section_lines):
        line_no, line = section_lines[index]
        if not line.strip():
            leading_blank_lines += 1
            index += 1
            continue
        if _PARAGRAPH_MARKER_RE.match(line) or (
            _APPENDED_MARKER_RE.match(line)
            and index > 0
            and _PARAGRAPH_MARKER_RE.match(section_lines[index - 1][1])
        ):
            index += 1
            continue
        if _reference_line_kind(line):
            references = [_string(line)]
            end_line = line_no
            index += 1
            while index < len(section_lines) and section_lines[index][1].strip() and _reference_line_kind(section_lines[index][1]):
                references.append(_string(section_lines[index][1]))
                end_line = section_lines[index][0]
                index += 1
            raw_blocks.append(
                _with_leading_gap({
                    "kind": "pointer",
                    "line_start": line_no,
                    "line_end": end_line,
                    "raw_markdown": "",
                    "references": _dedupe_strings(references),
                }, leading_blank_lines)
            )
            leading_blank_lines = 0
            continue
        if _fence_token(line):
            block, index = _consume_fence_block(section_lines, index)
            _append_raw_block(block)
            continue
        if _is_list_item(line):
            block, index = _consume_list_block(section_lines, index)
            _append_raw_block(block)
            continue
        if _is_blockquote_line(line):
            block, index = _consume_blockquote_block(section_lines, index)
            _append_raw_block(block)
            continue
        block, index = _consume_text_block(section_lines, index)
        _append_raw_block(block)

    attached: list[dict[str, Any]] = []
    pending_refs: dict[str, Any] | None = None
    for block in raw_blocks:
        if _string(block.get("kind")) == "pointer":
            if pending_refs is None:
                pending_refs = dict(block)
            else:
                pending_refs = _merge_blocks(pending_refs, block)
            continue
        current = dict(block)
        if pending_refs is not None:
            current = _merge_blocks(pending_refs, current)
            pending_refs = None
        attached.append(current)
    if pending_refs is not None:
        if attached:
            attached[-1] = _merge_blocks(attached[-1], pending_refs)
        else:
            attached.append(
                {
                    "kind": "text",
                    "line_start": int(pending_refs.get("line_start") or 0),
                    "line_end": int(pending_refs.get("line_end") or 0),
                    "raw_markdown": "",
                    "references": list(pending_refs.get("references", [])),
                }
            )

    structural = attached
    while True:
        next_structural: list[dict[str, Any]] = []
        changed = False
        index = 0
        while index < len(structural):
            current = dict(structural[index])
            if index + 1 < len(structural):
                next_block = structural[index + 1]
                if _has_hard_leading_gap(next_block):
                    next_structural.append(current)
                    index += 1
                    continue
                if _is_inline_label_only(_string(current.get("raw_markdown"))):
                    next_structural.append(_merge_blocks(current, next_block))
                    index += 2
                    changed = True
                    continue
                if (
                    _string(current.get("kind")) == "text"
                    and _plain_text(_string(current.get("raw_markdown"))).endswith(":")
                    and _string(next_block.get("kind")) == "list"
                ):
                    next_structural.append(_merge_blocks(current, next_block))
                    index += 2
                    changed = True
                    continue
            next_structural.append(current)
            index += 1
        structural = next_structural
        if not changed:
            break

    merged_coref: list[dict[str, Any]] = []
    for block in structural:
        if (
            merged_coref
            and _string(block.get("kind")) == "text"
            and not _has_hard_leading_gap(block)
            and _should_merge_backward_reference(block)
        ):
            merged_coref[-1] = _merge_blocks(merged_coref[-1], block)
            continue
        merged_coref.append(block)

    compacted: list[dict[str, Any]] = []
    pending_prefix: dict[str, Any] | None = None
    for block in merged_coref:
        current = dict(block)
        if pending_prefix is not None:
            if _has_hard_leading_gap(current):
                compacted.append(pending_prefix)
                pending_prefix = None
            else:
                current = _merge_blocks(pending_prefix, current)
                pending_prefix = None
        if _is_semantic_fragment(current) and not _has_hard_leading_gap(current):
            if compacted:
                compacted[-1] = _merge_blocks(compacted[-1], current)
            else:
                pending_prefix = current
            continue
        compacted.append(current)
    if pending_prefix is not None:
        if compacted:
            compacted[-1] = _merge_blocks(compacted[-1], pending_prefix)
        else:
            compacted.append(pending_prefix)
    return compacted


def _compute_paragraph_id_migrations(
    existing_payload: Mapping[str, Any],
    paragraphs: list[dict[str, Any]],
) -> dict[str, str]:
    existing_paragraphs = [dict(item) for item in existing_payload.get("paragraphs", []) if isinstance(item, Mapping)]
    if not existing_paragraphs and not isinstance((existing_payload.get("document") or {}).get("paragraph_id_migrations"), Mapping):
        return {}

    new_ids = {_string(item.get("id")) for item in paragraphs if _string(item.get("id"))}
    by_fingerprint = {
        _string(item.get("fingerprint")): _string(item.get("id"))
        for item in paragraphs
        if _string(item.get("fingerprint")) and _string(item.get("id"))
    }
    fresh: dict[str, str] = {}
    for paragraph in existing_paragraphs:
        old_id = _string(paragraph.get("id"))
        if not old_id:
            continue
        if old_id in new_ids:
            fresh[old_id] = old_id
            continue
        fingerprint = _string(paragraph.get("fingerprint"))
        if fingerprint and by_fingerprint.get(fingerprint):
            fresh[old_id] = by_fingerprint[fingerprint]
            continue
        old_section = _string(paragraph.get("section_id"))
        old_start = int(paragraph.get("line_start") or 0)
        old_end = int(paragraph.get("line_end") or 0)
        candidates = [
            item
            for item in paragraphs
            if _string(item.get("section_id")) == old_section
            and int(item.get("line_start") or 0) <= old_start
            and int(item.get("line_end") or 0) >= old_end
        ]
        if not candidates:
            candidates = [
                item
                for item in paragraphs
                if int(item.get("line_start") or 0) <= old_start and int(item.get("line_end") or 0) >= old_end
            ]
        if candidates:
            candidates.sort(
                key=lambda item: (
                    (int(item.get("line_end") or 0) - int(item.get("line_start") or 0)),
                    int(item.get("line_start") or 0),
                    _string(item.get("id")),
                )
            )
            fresh[old_id] = _string(candidates[0].get("id"))

    prior = (existing_payload.get("document") or {}).get("paragraph_id_migrations")
    resolved: dict[str, str] = {}
    if isinstance(prior, Mapping):
        for old_id, mid_id in prior.items():
            source_id = _string(old_id)
            current_id = _string(mid_id)
            if not source_id or not current_id:
                continue
            target = fresh.get(current_id) or (current_id if current_id in new_ids else "")
            if target:
                resolved[source_id] = target
    for old_id, new_id in fresh.items():
        if _string(old_id) and _string(new_id):
            resolved[_string(old_id)] = _string(new_id)
    for paragraph in paragraphs:
        pid = _string(paragraph.get("id"))
        if pid:
            resolved.setdefault(pid, pid)
    return {key: resolved[key] for key in sorted(resolved)}


def _merge_migrated_paragraph_fields(
    paragraph: dict[str, Any],
    existing_paragraphs_by_id: Mapping[str, Mapping[str, Any]],
    paragraph_id_migrations: Mapping[str, str],
) -> dict[str, Any]:
    target_id = _string(paragraph.get("id"))
    if not target_id:
        return paragraph
    predecessors = [
        (_string(old_id), existing_paragraphs_by_id.get(old_id))
        for old_id, new_id in paragraph_id_migrations.items()
        if _string(new_id) == target_id and existing_paragraphs_by_id.get(old_id)
    ]
    if not predecessors:
        return paragraph

    tags = [_string(item) for item in paragraph.get("tags", []) if _string(item)]
    idea_groups = [_string(item) for item in paragraph.get("idea_group_ids", []) if _string(item)]
    related = [_string(item) for item in paragraph.get("related_paragraph_ids", []) if _string(item)]
    references = [_string(item) for item in paragraph.get("references", []) if _string(item)]
    citations = [dict(item) for item in paragraph.get("citations", []) if isinstance(item, Mapping)]
    seen_citations = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in citations}

    for predecessor_id, predecessor in sorted(
        predecessors,
        key=lambda item: (
            int(item[1].get("line_start") or 0),
            int(item[1].get("line_end") or 0),
            _string(item[1].get("id")),
        ),
    ):
        tags.extend([_string(item) for item in predecessor.get("tags", []) if _string(item)])
        idea_groups.extend([_string(item) for item in predecessor.get("idea_group_ids", []) if _string(item)])
        related.extend([_string(item) for item in predecessor.get("related_paragraph_ids", []) if _string(item)])
        # References are parsed from the markdown substrate. When a paragraph keeps the
        # same id across syncs, stale references should be removable by editing the
        # markdown source. Only preserve predecessor references across actual id
        # migrations, where the source paragraph identity changed underneath the sync.
        if predecessor_id != target_id:
            references.extend([_string(item) for item in predecessor.get("references", []) if _string(item)])
        for citation in predecessor.get("citations", []):
            if not isinstance(citation, Mapping):
                continue
            key = json.dumps(dict(citation), sort_keys=True, ensure_ascii=False)
            if key in seen_citations:
                continue
            seen_citations.add(key)
            citations.append(dict(citation))
        if not _string(paragraph.get("summary")) and _string(predecessor.get("summary")):
            paragraph["summary"] = _string(predecessor.get("summary"))
        if not _string(paragraph.get("note")) and _string(predecessor.get("note")):
            paragraph["note"] = _string(predecessor.get("note"))

    paragraph["tags"] = _dedupe_strings(tags)
    paragraph["idea_group_ids"] = _dedupe_strings(idea_groups)
    paragraph["related_paragraph_ids"] = _dedupe_strings(related)
    paragraph["references"] = _dedupe_strings(references)
    paragraph["citations"] = citations
    return paragraph


def _filter_keyword_hints(hints: list[str]) -> list[str]:
    return [hint for hint in hints if _string(hint) and not _looks_like_pathish_hint(hint)]


def substrate_profile(substrate: str | None = None) -> dict[str, Any]:
    token = _string(substrate) or "raw_seed"
    profile = SUBSTRATE_PROFILES.get(token)
    if profile is None:
        raise ValueError(f"Unknown substrate profile: {token}")
    return dict(profile)


def _substrate_path_for_family(family_dir: str, filename: str) -> str:
    return canonicalize_write_path(f"{_string(family_dir)}/{_string(filename)}") or ""


def substrate_json_path_for_family(family_dir: str, *, substrate: str = "raw_seed") -> str:
    profile = substrate_profile(substrate)
    return _substrate_path_for_family(family_dir, _string(profile.get("json_filename")))


def substrate_markdown_path_for_family(family_dir: str, *, substrate: str = "raw_seed") -> str:
    profile = substrate_profile(substrate)
    return _substrate_path_for_family(family_dir, _string(profile.get("markdown_filename")))


def substrate_snapshot_path_for_family(family_dir: str, *, substrate: str = "raw_seed") -> str:
    profile = substrate_profile(substrate)
    return _substrate_path_for_family(family_dir, _string(profile.get("snapshot_filename")))


def agent_seed_json_path_for_family(family_dir: str) -> str:
    return substrate_json_path_for_family(family_dir, substrate="agent_seed")


def agent_seed_markdown_path_for_family(family_dir: str) -> str:
    return substrate_markdown_path_for_family(family_dir, substrate="agent_seed")


def agent_seed_snapshot_path_for_family(family_dir: str) -> str:
    return substrate_snapshot_path_for_family(family_dir, substrate="agent_seed")


def _section_id_for_path(path: str, *, profile: Mapping[str, Any]) -> str:
    prefix = _string(profile.get("section_id_prefix")) or "sec"
    safe_path = _string(path).replace("/", "__").replace("-", "_")
    return f"{prefix}_{safe_path}" if safe_path else f"{prefix}_untitled"


def _paragraph_id_for_section(section_id: str, index: int, *, profile: Mapping[str, Any]) -> str:
    section_prefix = f"{_string(profile.get('section_id_prefix'))}_"
    paragraph_prefix = _string(profile.get("paragraph_id_prefix")) or "par"
    section_tail = _string(section_id)
    if section_prefix and section_tail.startswith(section_prefix):
        section_tail = section_tail[len(section_prefix):]
    return f"{paragraph_prefix}_{section_tail}_{int(index):03d}"


_PHASE_HEADING_RE = re.compile(r"^phase\s+(?P<phase>\d+(?:[._-]\d+)*)\b", re.IGNORECASE)
_AGENT_SECTION_HEADING_RE = re.compile(
    r"^(?P<author>claude_code|codex|agent_collective|claude_subagent_[a-z0-9_]+)\s+\d{4}\s+\d{2}\s+\d{2}\b",
    re.IGNORECASE,
)


def _canonical_phase_token(token: str) -> str:
    parts: list[str] = []
    for raw_part in re.split(r"[._-]+", _string(token)):
        part = _string(raw_part)
        if not part:
            continue
        try:
            parts.append(str(int(part)))
        except ValueError:
            parts.append(part.casefold())
    return ".".join(parts)


def _is_current_family_raw_seed_heading(heading: str, family_number: str) -> bool:
    family_token = _canonical_phase_token(family_number)
    if not family_token:
        return False
    match = _PHASE_HEADING_RE.match(_plain_text(heading))
    if not match:
        return False
    if _canonical_phase_token(match.group("phase")) != family_token:
        return False
    return "raw seed" in _plain_text(heading).casefold()


def _should_flatten_lineage_phase_heading(
    heading: str,
    *,
    family_number: str,
    substrate: str,
) -> bool:
    if _string(substrate) != "raw_seed":
        return False
    if not _PHASE_HEADING_RE.match(_plain_text(heading)):
        return False
    return not _is_current_family_raw_seed_heading(heading, family_number)


def _paragraph_authored_by(section_heading: str, existing_paragraph: Mapping[str, Any] | None = None) -> str:
    if isinstance(existing_paragraph, Mapping):
        authored_by = _string(existing_paragraph.get("authored_by"))
        if authored_by:
            return authored_by
    match = _AGENT_SECTION_HEADING_RE.match(_string(section_heading))
    if match:
        return _string(match.group("author")).casefold()
    return "agent_collective"


def raw_seed_json_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed.json path for one family directory.
    - Mechanism: Join the family dir with `RAW_SEED_JSON_FILENAME` and pass it through `canonicalize_write_path`.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    - When-needed: Open when another surface needs the authoritative raw_seed.json location for a family without reconstructing the path rules by hand.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload_for_family; codex/standards/observe_apply/std_raw_seed.md
    """
    return substrate_json_path_for_family(family_dir, substrate="raw_seed")


def raw_seed_markdown_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed.md path for one family directory.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    return substrate_markdown_path_for_family(family_dir, substrate="raw_seed")


def raw_seed_snapshot_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed snapshot markdown path for one family directory.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    return substrate_snapshot_path_for_family(family_dir, substrate="raw_seed")


def raw_seed_workspace_dir_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw-seed workspace directory path for one family.
    - Guarantee: Returns a repo-relative directory path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    return canonicalize_write_path(f"{_string(family_dir)}/{RAW_SEED_WORKSPACE_DIRNAME}") or ""


def raw_seed_index_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_index.json path for one family.
    - Mechanism: Derive the raw-seed workspace dir for the family and append `RAW_SEED_INDEX_FILENAME` through `canonicalize_write_path`.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    - When-needed: Open when a caller needs the family-specific navigation-index path rather than the full registry builder.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_index; system/lib/kernel_nav_lens.py
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_INDEX_FILENAME}") or ""


def raw_seed_shards_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_shards.json path for one family's derived shard surface.
    - Mechanism: Derive the raw-seed workspace dir for the family and append `RAW_SEED_SHARDS_FILENAME` through `canonicalize_write_path`.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    - When-needed: Open when emitting or reading the derived shard surface that layers paragraph fingerprints and sibling adjacency around the family raw seed without mutating the append-only blackboard.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_shards; system/lib/kernel/commands/substrate.py::cmd_sync_raw_seed_index
    - Navigation-group: kernel_lib
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_SHARDS_FILENAME}") or ""


def raw_seed_navigation_graph_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_navigation_graph.json path for one family's compressed shard-neighborhood layer.
    - Mechanism: Derive the raw-seed workspace dir for the family and append `RAW_SEED_NAVIGATION_GRAPH_FILENAME` through `canonicalize_write_path`.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    - When-needed: Open when emitting or reading the derived navigation graph that compresses shard neighborhoods between the narrative paper lane and the full shard corpus.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_navigation_graph; system/lib/kernel/commands/substrate.py::cmd_sync_raw_seed_index
    - Navigation-group: kernel_lib
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_NAVIGATION_GRAPH_FILENAME}") or ""


def raw_seed_principles_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_principles.json path for one family.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_PRINCIPLES_FILENAME}") or ""


def raw_seed_meta_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_meta.md path for one family.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_META_FILENAME}") or ""


def raw_seed_tracing_surfaces_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_tracing_surfaces.md path for one family.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_TRACING_SURFACES_FILENAME}") or ""


def raw_seed_navigation_notes_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_navigation_notes.md path for one family.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_NAVIGATION_NOTES_FILENAME}") or ""


def raw_seed_term_ledger_path_for_family(family_dir: str) -> str:
    """[ACTION]
    - Teleology: Compute the canonical raw_seed_term_ledger.json path for one family.
    - Guarantee: Returns a repo-relative path string or an empty string when canonicalization fails.
    - Fails: None.
    """
    workspace_dir = raw_seed_workspace_dir_for_family(family_dir)
    return canonicalize_write_path(f"{workspace_dir}/{RAW_SEED_TERM_LEDGER_FILENAME}") or ""


def raw_seed_documentation_paths_for_family(family_dir: str) -> list[str]:
    """[ACTION]
    - Teleology: Return the stable human-documentation paths that explain one family's raw-seed navigation surfaces.
    - Mechanism: Gather the family principles/meta/tracing/navigation-notes paths and dedupe them.
    - Guarantee: Returns a stable repo-relative path list with duplicates removed.
    - Fails: None.
    - When-needed: Open when a routing surface needs the human doc companions for a raw-seed family rather than only the machine artifacts.
    - Escalates-to: system/lib/raw_seed_registry.py::raw_seed_documentation_records_for_family; codex/standards/observe_apply/std_raw_seed.md
    """
    paths = [
        raw_seed_principles_path_for_family(family_dir),
        raw_seed_meta_path_for_family(family_dir),
        raw_seed_tracing_surfaces_path_for_family(family_dir),
        raw_seed_navigation_notes_path_for_family(family_dir),
    ]
    return _dedupe_strings([p for p in paths if p])


def raw_seed_documentation_records_for_family(family_dir: str) -> list[dict[str, str]]:
    """[ACTION]
    - Teleology: Return structured documentation records describing each human-facing raw-seed navigation surface for one family.
    - Guarantee: Returns a list of id/path/role dicts for the principles, meta, tracing-surfaces, and navigation-notes artifacts.
    - Fails: None.
    """
    return [
        {
            "id": "principles",
            "path": raw_seed_principles_path_for_family(family_dir),
            "role": "Curated principle graph that interprets routes, tensions, and naming doctrine without pretending to be generated.",
        },
        {
            "id": "raw_seed_meta",
            "path": raw_seed_meta_path_for_family(family_dir),
            "role": "Stable family house view and workspace pointers for the raw-seed surface.",
        },
        {
            "id": "tracing_surfaces",
            "path": raw_seed_tracing_surfaces_path_for_family(family_dir),
            "role": "Human contract for navigation surfaces, operators, and pressure diagnostics.",
        },
        {
            "id": "navigation_notes",
            "path": raw_seed_navigation_notes_path_for_family(family_dir),
            "role": "Open design notes and future refinements for the raw-seed navigation layer.",
        },
    ]


def build_substrate_framework_usage(
    *,
    substrate: str,
    family_id: str,
    family_number: str,
    family_dir: str,
    substrate_path: str,
) -> dict[str, Any]:
    """Emit the top-level usage map for a seed substrate and its registry companion."""
    profile = substrate_profile(substrate)
    substrate_token = _string(profile.get("substrate")) or "raw_seed"
    family_token = _string(family_id) or _string(family_number) or "<FAMILY>"
    substrate_json_path = substrate_json_path_for_family(family_dir, substrate=substrate_token) if family_dir else (
        f"{substrate_path[:-3]}.json" if substrate_path.endswith(".md") else ""
    )
    if substrate_token == "agent_seed":
        return {
            "family_id": _string(family_id),
            "family_number": _string(family_number),
            "family_dir": _string(family_dir),
            "artifact_usage": [
                {
                    "artifact_path": _string(substrate_path),
                    "artifact_kind": "agent_seed_markdown",
                    "role": "family_agent_seed",
                    "authority_level": "supplementary_substrate",
                    "paired_artifact_path": _string(substrate_json_path),
                    "operating_rules": [
                        "Agent-only sibling substrate; preserve agent voice verbatim and never paraphrase operator voice into this file.",
                        "Write through `kernel.py --append-agent-seed --author <agent_id>` so headings, authored_by, and source_substrate stay deterministic.",
                    ],
                    "documentation": [
                        {
                            "id": "agent_seed_substrate",
                            "path": "codex/doctrine/paper_modules/agent_seed_substrate.md",
                            "purpose": "House view for the AI-voice sibling substrate and its authority posture.",
                        },
                        {
                            "id": "raw_seed_sibling",
                            "path": "codex/doctrine/paper_modules/raw_seed_substrate.md",
                            "purpose": "Operator-voice sibling substrate that agent seed must cite instead of impersonating.",
                        },
                    ],
                    "skills": [
                        {
                            "id": "agent_seed_authoring",
                            "path": "codex/doctrine/skills/raw_seed/agent_seed_authoring.md",
                            "purpose": "Canonical authoring protocol for agent_seed.md and anti-voice-theft rules.",
                        }
                    ],
                    "commands": [
                        {
                            "id": "help",
                            "command": "python3 kernel.py --agent-seed-help",
                            "purpose": "Emit the agent-seed substrate packet before writing or syncing.",
                        },
                        {
                            "id": "append",
                            "command": f"python3 kernel.py --append-agent-seed {family_token} --author <agent_id> \"<TEXT>\"",
                            "purpose": "Sanctioned append path for agent-authored seed prose.",
                        },
                        {
                            "id": "sync_registry",
                            "command": f"python3 kernel.py --sync-agent-seed {family_token} --live",
                            "purpose": "Rebuild agent_seed.json from agent_seed.md and re-wrap with sec_agent_/par_agent_ ids.",
                        },
                    ],
                },
                {
                    "artifact_path": _string(substrate_json_path),
                    "artifact_kind": "agent_seed_registry",
                    "role": "machine_companion_registry",
                    "authority_level": "supplementary_substrate",
                    "paired_artifact_path": _string(substrate_path),
                    "operating_rules": [
                        "Canonical machine registry for agent_seed.md with authored_by and source_substrate on every paragraph.",
                        "Agent-seed prose is mineable and citeable as AI voice, but it is not operator-authority-equivalent and cannot mint doctrine solo.",
                    ],
                    "documentation": [
                        {
                            "id": "json_standard",
                            "path": "codex/standards/observe_apply/std_agent_seed.json",
                            "purpose": "Machine contract for the agent_seed.json schema and agent-author invariants.",
                        },
                        {
                            "id": "agent_seed_substrate",
                            "path": "codex/doctrine/paper_modules/agent_seed_substrate.md",
                            "purpose": "Authority posture, sibling-substrate relationship, and CLI surface.",
                        },
                    ],
                    "skills": [
                        {
                            "id": "agent_seed_authoring",
                            "path": "codex/doctrine/skills/raw_seed/agent_seed_authoring.md",
                            "purpose": "Explains the only sanctioned write path and the attribution discipline.",
                        }
                    ],
                    "commands": [
                        {
                            "id": "sync_registry",
                            "command": f"python3 kernel.py --sync-agent-seed {family_token} --live",
                            "purpose": "Regenerate the registry after manual migration or a sanctioned append.",
                        },
                    ],
                },
            ],
        }

    raw_seed_meta_path = raw_seed_meta_path_for_family(family_dir) if family_dir else ""
    raw_seed_tracing_path = raw_seed_tracing_surfaces_path_for_family(family_dir) if family_dir else ""

    return {
        "family_id": _string(family_id),
        "family_number": _string(family_number),
        "family_dir": _string(family_dir),
        "artifact_usage": [
            {
                "artifact_path": _string(substrate_path),
                "artifact_kind": "raw_seed_markdown",
                "role": "family_blackboard",
                "authority_level": "substrate",
                "paired_artifact_path": _string(substrate_json_path),
                "operating_rules": [
                    "Append-only intake surface; preserve operator voice, contradictions, and unfinished thought.",
                    "Do not compress or hand-clean the blackboard in place; sync it into raw_seed.json when machine surfaces need the new state.",
                    "Agent-authored headings are contract violations here; move them to agent_seed.md instead of preserving mixed authority in one file.",
                ],
                "documentation": [
                    {
                        "id": "house_view",
                        "path": _string(raw_seed_meta_path),
                        "purpose": "Canonical house view for the family raw-seed substrate and companion artifacts.",
                    },
                    {
                        "id": "derivation_playbook",
                        "path": "docs/raw_seed_doctrine_derivation.md",
                        "purpose": "Human procedure for turning raw-seed material into doctrine without losing traceability.",
                    },
                    {
                        "id": "sibling_agent_seed",
                        "path": "codex/doctrine/paper_modules/agent_seed_substrate.md",
                        "purpose": "AI-voice sibling substrate. Agent prose belongs there, not in raw_seed.md.",
                    },
                ],
                "skills": [
                    {
                        "id": "kernel_phase_note_lifecycle",
                        "path": "codex/doctrine/skills/kernel/phase_note_lifecycle.md",
                        "purpose": "Defines raw_seed.md as append-only family intake and distinguishes it from synth/reference surfaces.",
                    },
                    {
                        "id": "kernel_navigate",
                        "path": "codex/doctrine/skills/kernel/navigate.md",
                        "purpose": "Kernel navigation skill for browsing the substrate without defaulting to raw grep-first file walking.",
                    },
                    {
                        "id": "kernel_raw_seed_contextualize",
                        "path": "codex/doctrine/skills/kernel/raw_seed_contextualize.md",
                        "purpose": "Compact workflow for contextualizing one entry against the wider raw seed, principles, projections, and governing docs.",
                    },
                ],
                "commands": [
                    {
                        "id": "docs_route",
                        "command": "python3 kernel.py --docs-route raw_seed substrate",
                        "purpose": "Resolve the active-family raw-seed house view and governing documentation before browsing linearly.",
                    },
                    {
                        "id": "append",
                        "command": f"python3 kernel.py --append-raw-seed {family_token} \"<TEXT>\"",
                        "purpose": "Append new blackboard material without rewriting older intake blocks.",
                    },
                    {
                        "id": "sync_registry",
                        "command": f"python3 kernel.py --sync-raw-seed {family_token} --live",
                        "purpose": "Rebuild raw_seed.json from raw_seed.md while preserving section and paragraph annotations.",
                    },
                    {
                        "id": "browse",
                        "command": f"python3 kernel.py --raw-seed-browse {family_token} --query \"<topic>\"",
                        "purpose": "Targeted recall from the blackboard when the question starts from raw-seed intent rather than the registry structure.",
                    },
                ],
            },
            {
                "artifact_path": _string(substrate_json_path),
                "artifact_kind": "raw_seed_registry",
                "role": "machine_companion_registry",
                "authority_level": "substrate",
                "paired_artifact_path": _string(substrate_path),
                "operating_rules": [
                    "Canonical machine registry for sections, paragraphs, annotations, and enrichment fields derived from raw_seed.md.",
                    "Prefer kernel annotation and sync commands over ad hoc manual mutation so resyncs preserve stable ids and fill fields.",
                ],
                "documentation": [
                    {
                        "id": "house_view",
                        "path": _string(raw_seed_meta_path),
                        "purpose": "Explains how the raw-seed markdown, registry, index, and principle layers fit together.",
                    },
                    {
                        "id": "principles_curation",
                        "path": "docs/raw_seed_principles_curation.md",
                        "purpose": "Curated principles layer and promotion discipline for durable commitments extracted from raw seed.",
                    },
                    {
                        "id": "navigation_contract",
                        "path": _string(raw_seed_tracing_path),
                        "purpose": "Navigation contract for traversing sections, themes, routes, and companion surfaces derived from raw_seed.json.",
                    },
                    {
                        "id": "json_standard",
                        "path": "codex/standards/observe_apply/std_raw_seed.json",
                        "purpose": "Machine contract for the raw_seed.json schema and enrichment fields.",
                    },
                    {
                        "id": "markdown_standard",
                        "path": "codex/standards/observe_apply/std_raw_seed.md",
                        "purpose": "Human-readable standard describing the relationship between raw_seed.md and raw_seed.json.",
                    },
                ],
                "skills": [
                    {
                        "id": "kernel_phase_note_lifecycle",
                        "path": "codex/doctrine/skills/kernel/phase_note_lifecycle.md",
                        "purpose": "Explains the raw-seed substrate role in the broader phase-family lifecycle so the registry is not mistaken for the active synth surface.",
                    },
                    {
                        "id": "kernel_navigate",
                        "path": "codex/doctrine/skills/kernel/navigate.md",
                        "purpose": "Kernel navigation skill for resolving refs, scoped browse questions, and bounded raw-seed queries.",
                    },
                    {
                        "id": "kernel_raw_seed_contextualize",
                        "path": "codex/doctrine/skills/kernel/raw_seed_contextualize.md",
                        "purpose": "One bounded workflow for placing an entry inside the wider substrate, principles graph, and projection surfaces.",
                    },
                ],
                "commands": [
                    {
                        "id": "docs_route",
                        "command": "python3 kernel.py --docs-route raw_seed substrate",
                        "purpose": "Resolve the active-family registry authority and house view before deeper navigation.",
                    },
                    {
                        "id": "annotate",
                        "command": f"python3 kernel.py --annotate-raw-seed {family_token} \"paragraph:<ID>\" <field> <value> --live",
                        "purpose": "Write summary, note, tag, relation, or section fill annotations through the sanctioned kernel surface.",
                    },
                    {
                        "id": "resolve_ref",
                        "command": f"python3 kernel.py --resolve-raw-seed-ref {family_token} \"<REF>\"",
                        "purpose": "Resolve a paragraph, section, or path ref to the exact registry object before citing or editing it.",
                    },
                    {
                        "id": "index_paragraph",
                        "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-paragraph \"paragraph:<ID>\"",
                        "purpose": "Inspect one paragraph's section, source, and relation context without opening the whole registry manually.",
                    },
                    {
                        "id": "index",
                        "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-diagnostics",
                        "purpose": "Inspect the navigation and diagnostics projection compiled from the registry.",
                    },
                    {
                        "id": "principles",
                        "command": "python3 kernel.py --docs-route raw_seed_principles",
                        "purpose": "Jump directly from the registry to the curated principles layer grounded in the same family substrate.",
                    },
                    {
                        "id": "project",
                        "command": f"python3 kernel.py --raw-seed-project {family_token} --project-profile structural",
                        "purpose": "Emit a bounded projection over the enriched registry for downstream browsing or injection.",
                    },
                ],
            },
        ],
    }


def build_raw_seed_framework_usage(
    *,
    family_id: str,
    family_number: str,
    family_dir: str,
    raw_seed_path: str,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Emit the top-level usage map for the raw-seed markdown and registry artifacts so commands, docs, and skills are recoverable from the substrate itself.
    - Mechanism: Pair each top-level artifact with its role, operating rules, docs, skills, and kernel commands using stable family-relative paths and command templates.
    - Guarantee: Returns a deterministic framework-usage bundle suitable for storage on raw_seed.json and projection into raw_seed.md marker comments.
    - Fails: None.
    """
    return build_substrate_framework_usage(
        substrate="raw_seed",
        family_id=family_id,
        family_number=family_number,
        family_dir=family_dir,
        substrate_path=raw_seed_path,
    )


def load_raw_seed_payload(path: Path) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Load an existing raw-seed registry payload from disk.
    - Mechanism: Read JSON text, coerce mapping payloads to dict, and degrade to `{}` on parse or shape failure.
    - Guarantee: Returns a dict payload or `{}`.
    - Fails: None.
    - When-needed: Open when raw-seed regeneration or annotation logic needs the existing payload but should degrade safely on missing or malformed JSON.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload_for_family; system/lib/raw_seed_registry.py::annotate_raw_seed_payload
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def normalize_raw_seed_notes(value: Any) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Normalize the raw notes list from a raw-seed payload into the canonical note-record shape.
    - Guarantee: Returns a list of normalized note dicts with id, targets, note, tags, and added_at; non-mapping items are dropped.
    - Fails: None.
    """
    if not isinstance(value, list):
        return []
    output: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue
        note_id = _string(item.get("id")) or f"r{index:03d}"
        output.append(
            {
                "id": note_id,
                "targets": _dedupe_strings([_string(target) for target in item.get("targets", [])]),
                "note": _string(item.get("note")),
                "tags": _dedupe_strings([_string(tag) for tag in item.get("tags", [])]),
                "added_at": _string(item.get("added_at")) or _utc_now(),
            }
        )
    return output


def _phrase_matches_mechanism_vocab(text_lower: str, phrase: str) -> bool:
    """Match multiword phrases by substring; single-token phrases use non-alphanumeric boundaries."""
    p = phrase.strip().casefold()
    if not p:
        return False
    if " " in p:
        return p in text_lower
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", text_lower))


def _mechanism_hints_nav_vocab(block: str, *, max_items: int = 6) -> list[str]:
    """Nav vocabulary lane: longest phrases first, word-boundary match for single-token entries."""
    lowered = str(block or "").casefold()
    hints: list[str] = []
    for phrase in _MECHANISM_PHRASES_SORTED:
        if _phrase_matches_mechanism_vocab(lowered, phrase) and phrase not in hints:
            hints.append(phrase)
        if len(hints) >= max_items:
            break
    return hints


def _section_boost_tokens(section: Mapping[str, Any]) -> frozenset[str]:
    """Weak boost: slug/path segments (length >= 4) for TF-IDF tie-break, not semantic truth."""
    path = _string(section.get("path"))
    slug = _string(section.get("heading_slug"))
    out: set[str] = set()
    for part in re.split(r"[/_\s]+", f"{path} {slug}"):
        t = part.strip().casefold()
        if len(t) >= 4:
            out.add(t)
    return frozenset(out)


def _compute_group_relevance_scores(paragraphs: list[dict[str, Any]]) -> None:
    """[ACTION]
    - Teleology: Annotate each paragraph with per-idea-group dedication scores so derived shard surfaces can rank paragraph centrality within every group it belongs to.
    - Mechanism: For each paragraph with N idea_group_ids, emit group_relevance[g] = 1.0 / N for each group g. A paragraph dedicated to a single group scores 1.0 there; a paragraph spread across 6 groups scores ~0.167 in each.
    - Guarantee: Mutates paragraphs in place so each one carries `group_relevance: {group_id: dedication_score}`. Paragraphs with no idea_group_ids keep `{}`.
    - Fails: None.
    - When-needed: Open when per-paragraph idea-group dedication must be queryable without a separate keyphrase-scoring pass, especially for derived shard-surface consumers.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_shards; system/lib/raw_seed_registry.py::build_raw_seed_index
    - Navigation-group: kernel_lib
    """
    for paragraph in paragraphs:
        groups = [_string(g) for g in paragraph.get("idea_group_ids") or [] if _string(g)]
        unique = _dedupe_strings(groups)
        if not unique:
            paragraph["group_relevance"] = {}
            continue
        dedication = round(1.0 / len(unique), 6)
        paragraph["group_relevance"] = {g: dedication for g in unique}


def _enrich_paragraph_hints(paragraphs: list[dict[str, Any]], sections: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Post-pass: topic-weighted keyword_hints + nav mechanism_hints. Returns term ledger dict for optional disk write."""
    if not paragraphs:
        return None
    sections_by_id = {_string(s.get("id")): s for s in sections if _string(s.get("id"))}
    stop = merged_stopwords(STOP_WORDS)
    plain_list = [
        _plain_text(_strip_reference_like_tokens(str(p.get("plain_text") or p.get("raw_markdown") or "")))
        for p in paragraphs
    ]
    corpus = build_corpus_token_stats(plain_list, stop)
    omit_diag = high_df_omit_unigrams(corpus)
    mech_uni = _mechanism_vocab_unigrams()
    lex = build_corpus_lexicon(dict(corpus.cf_unigram), dict(corpus.df_unigram), stop, mech_uni)
    normalize = build_corpus_hint_normalizer(lex, stop, mech_uni)
    correction_counter: list[int] = [0]
    for index, paragraph in enumerate(paragraphs):
        sid = _string(paragraph.get("section_id"))
        sec = sections_by_id.get(sid, {})
        boost = _section_boost_tokens(sec)
        raw_block = _strip_reference_like_tokens(str(paragraph.get("raw_markdown") or ""))
        plain = _strip_reference_like_tokens(str(paragraph.get("plain_text") or ""))
        paragraph["keyword_hints"] = _filter_keyword_hints(
            merge_distinctive_keyword_hints(
                raw_block,
                plain,
                index,
                corpus,
                stop,
                boost,
                mech_uni,
                normalize,
                correction_counter,
            )
        )
        paragraph["mechanism_hints"] = _mechanism_hints_nav_vocab(str(paragraph.get("raw_markdown") or ""))
    return build_term_ledger_payload(
        corpus,
        stop_words=stop,
        high_df_omit=omit_diag,
        spelling_corrections_applied=correction_counter[0],
        profile_version="nav_topic_v3",
        spelling_normalization_version=SPELLING_NORMALIZATION_VERSION,
    )


def build_raw_seed_payload(
    *,
    raw_seed_text: str,
    raw_seed_path: str,
    family_payload: Mapping[str, Any] | None = None,
    existing_payload: Mapping[str, Any] | None = None,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Compile family raw_seed markdown into the structured raw-seed registry payload.
    - Mechanism: Parse frontmatter/headings/paragraph blocks, preserve existing section and paragraph annotations, enrich paragraph hint lanes, and emit the registry dict.
    - Guarantee: Returns a `raw_seed_registry` payload containing sections, paragraphs, notes, and optional ephemeral term-ledger diagnostics.
    - Fails: None for valid caller-supplied text and payload inputs.
    - When-needed: Open when raw-seed markdown must be turned into the authoritative registry substrate or its parsing/enrichment rules need inspection.
    - Escalates-to: system/lib/raw_seed_keyphrase.py::merge_distinctive_keyword_hints; system/lib/raw_seed_spelling.py::build_corpus_hint_normalizer; codex/standards/observe_apply/std_raw_seed.md
    - Navigation-group: kernel_lib
    """
    profile = substrate_profile(substrate)
    family = dict(family_payload or {})
    existing = dict(existing_payload or {})

    frontmatter_text, _ = split_frontmatter(raw_seed_text)
    frontmatter, body = parse_frontmatter(raw_seed_text)
    line_offset = len(frontmatter_text.splitlines()) if frontmatter_text else 0
    body_lines = body.splitlines()

    existing_sections = {
        _string(item.get("id")): dict(item)
        for item in existing.get("sections", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    }
    existing_sections_by_path = {
        _string(item.get("path")): dict(item)
        for item in existing.get("sections", [])
        if isinstance(item, Mapping) and _string(item.get("path"))
    }
    existing_paragraphs = {
        _string(item.get("id")): dict(item)
        for item in existing.get("paragraphs", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    }
    existing_paragraphs_by_fingerprint = {
        _string(item.get("fingerprint")): dict(item)
        for item in existing.get("paragraphs", [])
        if isinstance(item, Mapping) and _string(item.get("fingerprint"))
    }

    sections: list[dict[str, Any]] = []
    paragraphs: list[dict[str, Any]] = []
    section_path_counts: dict[tuple[str, str], int] = {}
    paragraph_counts_by_section: dict[str, int] = {}
    family_root_scope_path = ""

    root_section = {
        "id": _string(profile.get("root_section_id")) or "sec_root",
        "order": 0,
        "level": 0,
        "heading": _string(profile.get("root_heading")) or "ROOT",
        "heading_slug": "root",
        "path": "__root__",
        "path_scope": "__root__",
        "parent_id": None,
        "line_start": line_offset + 1 if body_lines else max(1, line_offset),
        "line_end": line_offset + len(body_lines) if body_lines else max(1, line_offset),
        "paragraph_ids": [],
        "aliases": [],
        "tags": [],
        "note": "",
        "fill": {
            "purpose": "",
            "grouping_hints": [],
            "related_section_ids": [],
        },
    }
    sections.append(root_section)
    current_section = root_section
    section_stack: list[dict[str, Any]] = [root_section]
    existing_paragraphs_by_id = {
        _string(item.get("id")): dict(item)
        for item in existing.get("paragraphs", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    }
    section_lines: list[tuple[int, str]] = []
    active_fence: tuple[str, int] | None = None

    def _merge_section_fields(section: dict[str, Any]) -> dict[str, Any]:
        existing_section = existing_sections.get(section["id"]) or existing_sections_by_path.get(section["path"]) or {}
        if isinstance(existing_section.get("aliases"), list):
            section["aliases"] = _dedupe_strings([_string(item) for item in existing_section.get("aliases", [])])
        if isinstance(existing_section.get("tags"), list):
            section["tags"] = _dedupe_strings([_string(item) for item in existing_section.get("tags", [])])
        section["note"] = _string(existing_section.get("note"))
        fill = dict(existing_section.get("fill") or {})
        section["fill"] = {
            "purpose": _string(fill.get("purpose")),
            "grouping_hints": _dedupe_strings([_string(item) for item in fill.get("grouping_hints", [])]),
            "related_section_ids": _dedupe_strings([_string(item) for item in fill.get("related_section_ids", [])]),
        }
        return section

    def _merge_paragraph_fields(paragraph: dict[str, Any]) -> dict[str, Any]:
        existing_paragraph = (
            existing_paragraphs.get(paragraph["id"])
            or existing_paragraphs_by_fingerprint.get(paragraph["fingerprint"])
            or {}
        )
        sync_provenance = _paragraph_sync_provenance(paragraph, existing_paragraph)
        if sync_provenance:
            paragraph["sync_provenance"] = sync_provenance
        paragraph["tags"] = _dedupe_strings([_string(item) for item in existing_paragraph.get("tags", [])])
        paragraph["idea_group_ids"] = _dedupe_strings([_string(item) for item in existing_paragraph.get("idea_group_ids", [])])
        paragraph["related_paragraph_ids"] = _dedupe_strings(
            [_string(item) for item in existing_paragraph.get("related_paragraph_ids", [])]
        )
        citations = existing_paragraph.get("citations")
        paragraph["citations"] = [dict(item) for item in citations if isinstance(item, Mapping)] if isinstance(citations, list) else []
        references = [_string(item) for item in paragraph.get("references", []) if _string(item)]
        predecessor_id = _string(existing_paragraph.get("id"))
        # When the same paragraph id survives a sync, stale references should be
        # removable by editing the markdown substrate. Only preserve predecessor
        # references across actual id migrations.
        if predecessor_id and predecessor_id != paragraph["id"]:
            references.extend([_string(item) for item in existing_paragraph.get("references", []) if _string(item)])
        paragraph["references"] = _dedupe_strings(references)
        paragraph["summary"] = _string(existing_paragraph.get("summary"))
        paragraph["note"] = _string(existing_paragraph.get("note"))
        paragraph["source_substrate"] = _string(existing_paragraph.get("source_substrate")) or _string(profile.get("source_substrate"))
        if bool(profile.get("supports_authored_by")):
            paragraph["authored_by"] = _paragraph_authored_by(
                _string(current_section.get("heading")),
                existing_paragraph,
            )
        return paragraph

    def _flush_section_lines() -> None:
        nonlocal section_lines, current_section
        blocks = _collect_semantic_blocks(section_lines)
        section_lines = []
        if not blocks:
            return
        section_id = _string(current_section.get("id")) or "sec_root"
        for block in blocks:
            raw_block = _string(block.get("raw_markdown"))
            paragraph_index = paragraph_counts_by_section.get(section_id, 0) + 1
            paragraph_counts_by_section[section_id] = paragraph_index
            paragraph_id = _paragraph_id_for_section(section_id, paragraph_index, profile=profile)
            paragraph = {
                "id": paragraph_id,
                "section_id": section_id,
                "order": paragraph_index,
                "section_path": _string(current_section.get("path")) or "__root__",
                "line_start": int(block.get("line_start") or 0),
                "line_end": max(int(block.get("line_start") or 0), int(block.get("line_end") or 0)),
                "raw_markdown": raw_block,
                "plain_text": _plain_text(raw_block),
                "fingerprint": _fingerprint(raw_block),
                "paragraph_fingerprint": _fingerprint(raw_block),
                "group_relevance": {},
                "keyword_hints": [],
                "mechanism_hints": [],
                "tags": [],
                "idea_group_ids": [],
                "related_paragraph_ids": [],
                "citations": [],
                "references": _dedupe_strings([_string(item) for item in block.get("references", []) if _string(item)]),
                "summary": "",
                "note": "",
                "source_substrate": _string(profile.get("source_substrate")),
            }
            paragraph = _merge_paragraph_fields(paragraph)
            paragraphs.append(paragraph)
            current_section["paragraph_ids"].append(paragraph_id)
            current_section["line_end"] = max(int(current_section.get("line_end") or 0), paragraph["line_end"])
            root_section["line_end"] = max(int(root_section.get("line_end") or 0), paragraph["line_end"])

    for index, line in enumerate(body_lines, start=line_offset + 1):
        if (
            active_fence is None
            and line.strip().startswith(_string(profile.get("marker_prefix")))
            and not _PARAGRAPH_MARKER_RE.match(line)
        ):
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line) if active_fence is None else None
        if heading_match:
            _flush_section_lines()
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            while section_stack and int(section_stack[-1].get("level") or 0) >= level:
                section_stack.pop()
            parent = section_stack[-1] if section_stack else root_section
            parent_path = _string(parent.get("path")) or "__root__"
            parent_scope_path = _string(parent.get("path_scope")) or parent_path
            flatten_lineage_heading = _should_flatten_lineage_phase_heading(
                heading,
                family_number=_string(family.get("family_number")),
                substrate=_string(profile.get("substrate")) or "raw_seed",
            )
            path_parent = parent_scope_path
            base_slug = _slugify(heading)
            if flatten_lineage_heading:
                base_slug = "phase-lineage-heading"
                if path_parent == "__root__" and family_root_scope_path:
                    path_parent = family_root_scope_path
            key = (path_parent, base_slug)
            count = section_path_counts.get(key, 0) + 1
            section_path_counts[key] = count
            heading_slug = base_slug if count == 1 else f"{base_slug}-{count}"
            path = heading_slug if path_parent == "__root__" else f"{path_parent}/{heading_slug}"
            section = {
                "id": _section_id_for_path(path, profile=profile),
                "order": len(sections),
                "level": level,
                "heading": heading,
                "heading_slug": heading_slug,
                "path": path,
                "path_scope": path_parent if flatten_lineage_heading else path,
                "parent_id": parent["id"],
                "line_start": index,
                "line_end": index,
                "paragraph_ids": [],
                "aliases": [],
                "tags": [],
                "note": "",
                "fill": {
                    "purpose": "",
                    "grouping_hints": [],
                    "related_section_ids": [],
                },
            }
            section = _merge_section_fields(section)
            sections.append(section)
            section_stack.append(section)
            current_section = section
            if _is_current_family_raw_seed_heading(heading, _string(family.get("family_number"))):
                family_root_scope_path = path
            continue
        section_lines.append((index, line))
        if active_fence is not None:
            char, min_len = active_fence
            if line.strip().startswith(char * min_len):
                active_fence = None
        else:
            active_fence = _fence_token(line)

    _flush_section_lines()

    for section in sections:
        section.pop("path_scope", None)

    if not paragraphs:
        root_section["line_end"] = max(root_section["line_start"], line_offset + len(body_lines))

    paragraph_id_migrations = _compute_paragraph_id_migrations(existing, paragraphs)
    if paragraph_id_migrations:
        paragraphs = [
            _merge_migrated_paragraph_fields(dict(paragraph), existing_paragraphs_by_id, paragraph_id_migrations)
            for paragraph in paragraphs
        ]

    term_ledger = _enrich_paragraph_hints(paragraphs, sections)
    _compute_group_relevance_scores(paragraphs)

    paragraphs.sort(
        key=lambda p: (
            -int(p.get("line_end") or 0),
            -int(p.get("line_start") or 0),
            _string(p.get("id")),
        )
    )

    notes = normalize_raw_seed_notes(existing.get("notes", []))
    document = dict(existing.get("document") or {})
    document.update(
        {
            "source_format": "markdown",
            "frontmatter": dict(frontmatter),
            "heading_mode": "markdown_headings_plus_root_fallback",
            "paragraph_mode": "markdown_semantic_units_v1",
            "source_substrate": _string(profile.get("source_substrate")),
            "total_sections": len(sections),
            "total_paragraphs": len(paragraphs),
            "paragraph_array_order": "line_end_desc",
            "hint_extraction": {"profile": "nav_topic_v3", "version": 3},
        }
    )
    if paragraph_id_migrations or "paragraph_id_migrations" in document:
        document["paragraph_id_migrations"] = paragraph_id_migrations
    # Key order is intentional: metadata and paragraphs (recency-first) before sections for human scanning.
    path_field = f"{_string(profile.get('substrate'))}_path"
    payload_out: dict[str, Any] = {
        "kind": _string(profile.get("kind")) or "raw_seed_registry",
        "schema_version": _string(profile.get("schema_version")) or RAW_SEED_SCHEMA_VERSION,
        "family_id": _string(family.get("family_id")),
        "family_number": _string(family.get("family_number")),
        "family_title": _string(family.get("family_title")),
        "family_dir": _string(family.get("family_dir")),
        "framework_usage": build_substrate_framework_usage(
            substrate=_string(profile.get("substrate")) or "raw_seed",
            family_id=_string(family.get("family_id")),
            family_number=_string(family.get("family_number")),
            family_dir=_string(family.get("family_dir")),
            substrate_path=_string(raw_seed_path),
        ),
        "generated_at": _string(existing.get("generated_at")) or _utc_now(),
        "updated_at": _utc_now(),
        "document": document,
        "paragraphs": paragraphs,
        "sections": sections,
        "notes": notes,
    }
    payload_out[path_field] = _string(raw_seed_path)
    if term_ledger:
        payload_out["_ephemeral_term_ledger"] = term_ledger
    return payload_out


def build_raw_seed_payload_for_family(root: Path, family_payload: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Build the raw-seed registry payload for one family directly from repo root plus family metadata.
    - Mechanism: Resolve family-relative raw-seed and existing registry paths, read the markdown, and delegate to `build_raw_seed_payload`.
    - Guarantee: Returns a compiled raw-seed registry payload for the requested family.
    - Fails: Raises ValueError when required family metadata is missing or the raw_seed markdown file does not exist.
    - When-needed: Open when kernel or scaffold code needs the family-scoped registry builder instead of supplying raw markdown manually.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload; system/lib/raw_seed_registry.py::raw_seed_json_path_for_family
    """
    root = Path(root).resolve()
    family = dict(family_payload or {})
    family_dir = _string(family.get("family_dir"))
    if not family_dir:
        raise ValueError("family_dir is required.")
    raw_seed_path = _string(family.get("raw_seed_path")) or raw_seed_markdown_path_for_family(family_dir)
    if not raw_seed_path:
        raise ValueError("raw_seed_path is required.")
    raw_seed_abs = root / raw_seed_path
    if not raw_seed_abs.exists():
        raise ValueError(f"raw_seed.md not found: {raw_seed_path}")
    raw_seed_json_path = _string(family.get("raw_seed_json_path")) or raw_seed_json_path_for_family(family_dir)
    existing_payload = load_raw_seed_payload(root / raw_seed_json_path) if raw_seed_json_path and (root / raw_seed_json_path).exists() else {}
    return build_raw_seed_payload(
        raw_seed_text=raw_seed_abs.read_text(encoding="utf-8"),
        raw_seed_path=raw_seed_path,
        family_payload=family,
        existing_payload=existing_payload,
        substrate="raw_seed",
    )


def build_agent_seed_payload_for_family(root: Path, family_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build the agent-seed registry payload for one family from repo root plus family metadata."""
    root = Path(root).resolve()
    family = dict(family_payload or {})
    family_dir = _string(family.get("family_dir"))
    if not family_dir:
        raise ValueError("family_dir is required.")
    agent_seed_path = _string(family.get("agent_seed_path")) or agent_seed_markdown_path_for_family(family_dir)
    if not agent_seed_path:
        raise ValueError("agent_seed_path is required.")
    agent_seed_abs = root / agent_seed_path
    if not agent_seed_abs.exists():
        raise ValueError(f"agent_seed.md not found: {agent_seed_path}")
    agent_seed_json_path = _string(family.get("agent_seed_json_path")) or agent_seed_json_path_for_family(family_dir)
    existing_payload = (
        load_raw_seed_payload(root / agent_seed_json_path)
        if agent_seed_json_path and (root / agent_seed_json_path).exists()
        else {}
    )
    return build_raw_seed_payload(
        raw_seed_text=agent_seed_abs.read_text(encoding="utf-8"),
        raw_seed_path=agent_seed_path,
        family_payload=family,
        existing_payload=existing_payload,
        substrate="agent_seed",
    )


def resolve_raw_seed_ref(payload: Mapping[str, Any], ref: str) -> dict[str, Any] | None:
    """[ACTION]
    - Teleology: Resolve a user-facing raw-seed reference token to its document, section, or paragraph target.
    - Mechanism: Match wildcard/document refs, explicit section/paragraph/path prefixes, section ids/paths/slugs/headings, and paragraph ids against the payload.
    - Guarantee: Returns a `raw_seed_ref` record or `None` when the ref cannot be resolved.
    - Fails: None.
    - When-needed: Open when kernel `--resolve-raw-seed-ref` style work needs the exact lookup rules for section and paragraph references.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_index; codex/standards/observe_apply/std_raw_seed.md
    """
    token = _string(ref)
    if not token or not isinstance(payload, Mapping):
        return None

    sections = [dict(item) for item in payload.get("sections", []) if isinstance(item, Mapping)]
    paragraphs = [dict(item) for item in payload.get("paragraphs", []) if isinstance(item, Mapping)]
    paragraphs_by_id = {
        _string(item.get("id")): dict(item)
        for item in paragraphs
        if _string(item.get("id"))
    }
    document = payload.get("document") if isinstance(payload.get("document"), Mapping) else {}
    paragraph_id_migrations = (
        document.get("paragraph_id_migrations")
        if isinstance(document.get("paragraph_id_migrations"), Mapping)
        else {}
    )
    if token in {"*", "all"}:
        return {
            "kind": "raw_seed_ref",
            "target_kind": "document",
            "target": {
                "family_id": _string(payload.get("family_id")),
                "raw_seed_path": _string(payload.get("raw_seed_path")),
            },
        }
    if token.startswith("section:"):
        token = token.split(":", 1)[1].strip()
    elif token.startswith("paragraph:"):
        token = token.split(":", 1)[1].strip()
    elif token.startswith("path:"):
        target = token.split(":", 1)[1].strip()
        for section in sections:
            if _string(section.get("path")) == target:
                return {"kind": "raw_seed_ref", "target_kind": "section", "target": section}
        return None

    migrated_token = _string(paragraph_id_migrations.get(token))
    if migrated_token:
        token = migrated_token

    if token.startswith("sec_"):
        paragraph_prefix = token.replace("sec_", "par_", 1)
        inferred_sections: list[str] = []
        for old_id, new_id in paragraph_id_migrations.items():
            old_paragraph_id = _string(old_id)
            if old_paragraph_id != paragraph_prefix and not old_paragraph_id.startswith(paragraph_prefix + "_"):
                continue
            target_section = _string(paragraphs_by_id.get(_string(new_id), {}).get("section_id"))
            if target_section:
                inferred_sections.append(target_section)
        if inferred_sections:
            inferred_sections.sort(key=lambda value: (-inferred_sections.count(value), value))
            token = inferred_sections[0]

    for section in sections:
        if token in {_string(section.get("id")), _string(section.get("path")), _string(section.get("heading_slug"))}:
            return {"kind": "raw_seed_ref", "target_kind": "section", "target": section}
    normalized = _plain_text(token).casefold()
    for section in sections:
        if _plain_text(section.get("heading")).casefold() == normalized:
            return {"kind": "raw_seed_ref", "target_kind": "section", "target": section}
    for paragraph in paragraphs:
        if token == _string(paragraph.get("id")):
            return {"kind": "raw_seed_ref", "target_kind": "paragraph", "target": paragraph}
    return None


def _para_line_key(paragraph: Mapping[str, Any]) -> tuple[int, str]:
    return (int(paragraph.get("line_start") or 0), _string(paragraph.get("id")))


def _trim_text(value: Any, *, max_chars: int = 240) -> str:
    text = _plain_text(_string(value))
    if not text or len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _humanize_token(token: str, *, prefix: str | None = None) -> str:
    value = _string(token)
    if prefix and value.startswith(prefix):
        value = value[len(prefix):]
    value = re.sub(r"[_-]+", " ", value).strip()
    value = re.sub(r"\s{2,}", " ", value)
    return value.title() if value else ""


def _counter_records(counter: Counter[str], *, key_name: str, value_name: str, limit: int = 6) -> list[dict[str, Any]]:
    return [{key_name: key, value_name: count} for key, count in counter.most_common(limit) if _string(key)]


def _pair_neighbor_records(
    token: str,
    pair_counts: Mapping[tuple[str, str], int],
    *,
    key_name: str,
    value_name: str = "shared_paragraphs",
    limit: int = 6,
) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for pair, count in pair_counts.items():
        if len(pair) != 2:
            continue
        left, right = pair
        if left == token:
            counter[right] += int(count or 0)
        elif right == token:
            counter[left] += int(count or 0)
    return _counter_records(counter, key_name=key_name, value_name=value_name, limit=limit)


def _section_counter_records(
    counter: Counter[str],
    sections_by_id: Mapping[str, Mapping[str, Any]],
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for section_id, count in counter.most_common(limit):
        section = sections_by_id.get(section_id) or {}
        output.append(
            {
                "section_id": _string(section_id),
                "heading": _string(section.get("heading")),
                "path": _string(section.get("path")),
                "paragraph_refs": int(count or 0),
            }
        )
    return output


def _document_counter_records(
    counter: Counter[str],
    documents_by_id: Mapping[str, Mapping[str, Any]],
    *,
    value_name: str = "paragraph_refs",
    limit: int = 6,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for document_id, count in counter.most_common(limit):
        document = documents_by_id.get(document_id) or {}
        output.append(
            {
                "source_id": _string(document_id),
                "heading": _string(document.get("heading")),
                "path": _string(document.get("path")),
                value_name: int(count or 0),
            }
        )
    return output


def _representative_paragraph_ids(
    paragraph_ids: list[str],
    paragraphs_by_id: Mapping[str, Mapping[str, Any]],
    incoming_relations: Mapping[str, list[str]],
    *,
    limit: int = 6,
) -> list[str]:
    if limit <= 0:
        return _dedupe_strings(list(paragraph_ids))

    def _score(paragraph_id: str) -> tuple[int, int, int, str]:
        paragraph = paragraphs_by_id.get(paragraph_id) or {}
        outgoing = len(paragraph.get("related_paragraph_ids", [])) if isinstance(paragraph.get("related_paragraph_ids"), list) else 0
        incoming = len(incoming_relations.get(paragraph_id, []))
        return (
            -(outgoing + incoming),
            -outgoing,
            int(paragraph.get("line_start") or 0),
            _string(paragraph_id),
        )

    ordered = sorted(_dedupe_strings(list(paragraph_ids)), key=_score)
    selected: list[str] = []
    seen_summaries: set[str] = set()
    for paragraph_id in ordered:
        paragraph = paragraphs_by_id.get(paragraph_id) or {}
        summary_key = _trim_text(paragraph.get("summary"), max_chars=200).casefold() or f"id:{paragraph_id}"
        if summary_key in seen_summaries:
            continue
        seen_summaries.add(summary_key)
        selected.append(paragraph_id)
        if len(selected) >= limit:
            return selected
    for paragraph_id in ordered:
        if paragraph_id in selected:
            continue
        selected.append(paragraph_id)
        if len(selected) >= limit:
            break
    return selected


def _route_id_for_summary(summary: str) -> str:
    return f"route_{_fingerprint(summary)}"


def _paragraph_stub(
    paragraph: Mapping[str, Any],
    *,
    section_heading: str = "",
    incoming_related_ids: list[str] | None = None,
) -> dict[str, Any]:
    tags = _dedupe_strings([_string(tag) for tag in paragraph.get("tags", [])]) if isinstance(paragraph.get("tags"), list) else []
    groups = (
        _dedupe_strings([_string(group) for group in paragraph.get("idea_group_ids", [])])
        if isinstance(paragraph.get("idea_group_ids"), list)
        else []
    )
    mechanisms = (
        _dedupe_strings([_string(item) for item in paragraph.get("mechanism_hints", [])])
        if isinstance(paragraph.get("mechanism_hints"), list)
        else []
    )
    keywords = (
        _dedupe_strings([_string(item) for item in paragraph.get("keyword_hints", [])])
        if isinstance(paragraph.get("keyword_hints"), list)
        else []
    )
    outgoing = (
        _dedupe_strings([_string(item) for item in paragraph.get("related_paragraph_ids", [])])
        if isinstance(paragraph.get("related_paragraph_ids"), list)
        else []
    )
    incoming = _dedupe_strings(list(incoming_related_ids or []))
    return {
        "id": _string(paragraph.get("id")),
        "section_id": _string(paragraph.get("section_id")),
        "section_path": _string(paragraph.get("section_path")),
        "section_heading": _string(section_heading),
        "order": int(paragraph.get("order") or 0),
        "line_start": int(paragraph.get("line_start") or 0),
        "line_end": int(paragraph.get("line_end") or 0),
        "summary": _trim_text(paragraph.get("summary"), max_chars=240),
        "note": _trim_text(paragraph.get("note"), max_chars=180),
        "tags": tags[:8],
        "idea_group_ids": groups[:6],
        "mechanism_hints": mechanisms[:6],
        "keyword_hints": keywords[:8],
        "related_paragraph_count": len(outgoing),
        "incoming_related_paragraph_count": len(incoming),
    }


def build_raw_seed_index(payload: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Derive a compact navigation index and statistics from a loaded raw_seed.json registry.
    - Guarantee: Returns the full raw_seed_index dict including inverted indexes, theme cards, source cards, sections TOC, routes, crosslinks, and diagnostics.
    - Fails: None.
    - When-needed: Open when raw-seed routing needs the compact inverted index, theme summaries, or claim-route cards derived from the full registry payload.
    - Escalates-to: system/lib/raw_seed_registry.py::project_raw_seed_index_slice; system/lib/kernel_nav_lens.py; codex/standards/observe_apply/std_raw_seed.md
    - Navigation-group: kernel_lib
    """
    paragraphs = [dict(p) for p in payload.get("paragraphs", []) if isinstance(p, Mapping) and _string(p.get("id"))]
    sections = [dict(s) for s in payload.get("sections", []) if isinstance(s, Mapping) and _string(s.get("id"))]
    paragraphs_by_id = {_string(p["id"]): p for p in paragraphs}
    sections_by_id = {_string(s["id"]): s for s in sections}
    root_section_id = next(
        (
            _string(section.get("id"))
            for section in sections
            if _string(section.get("path")) == "__root__" or int(section.get("level") or 0) == 0
        ),
        "sec_root",
    )

    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for section in sections:
        sid = _string(section.get("id"))
        children_by_parent[_string(section.get("parent_id"))].append(sid)
    for parent_id, child_ids in list(children_by_parent.items()):
        child_ids.sort(
            key=lambda sid: (
                int(sections_by_id.get(sid, {}).get("line_start") or 0),
                _string(sid),
            )
        )
        children_by_parent[parent_id] = child_ids

    descendants_cache: dict[str, tuple[str, ...]] = {}

    def _descendant_section_ids(root_id: str) -> list[str]:
        if root_id in descendants_cache:
            return list(descendants_cache[root_id])
        ordered = [root_id]
        for child_id in children_by_parent.get(root_id, []):
            ordered.extend(_descendant_section_ids(child_id))
        descendants_cache[root_id] = tuple(_dedupe_strings(ordered))
        return list(descendants_cache[root_id])

    source_document_ids = [sid for sid in children_by_parent.get(root_section_id, []) if sid and sid != root_section_id]
    if not source_document_ids:
        source_document_ids = [
            _string(section.get("id"))
            for section in sorted(sections, key=lambda item: (int(item.get("line_start") or 0), _string(item.get("id"))))
            if int(section.get("level") or 0) <= 1 and _string(section.get("id")) != root_section_id
        ]

    source_to_section_ids: dict[str, list[str]] = {}
    section_to_source_id: dict[str, str] = {}
    for source_id in source_document_ids:
        source_sections = _descendant_section_ids(source_id)
        source_to_section_ids[source_id] = source_sections
        for section_id in source_sections:
            section_to_source_id[section_id] = source_id

    tag_to_ids: dict[str, list[str]] = defaultdict(list)
    group_to_ids: dict[str, list[str]] = defaultdict(list)
    mechanism_to_ids: dict[str, list[str]] = defaultdict(list)
    section_to_ids: dict[str, list[str]] = defaultdict(list)
    source_to_ids: dict[str, list[str]] = defaultdict(list)
    tag_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    mechanism_counts: Counter[str] = Counter()
    tag_section_counts: dict[str, Counter[str]] = defaultdict(Counter)
    group_section_counts: dict[str, Counter[str]] = defaultdict(Counter)
    mechanism_section_counts: dict[str, Counter[str]] = defaultdict(Counter)
    tag_source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    group_source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    mechanism_source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    section_tag_counts: dict[str, Counter[str]] = defaultdict(Counter)
    section_group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    section_mechanism_counts: dict[str, Counter[str]] = defaultdict(Counter)
    tag_group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    group_tag_counts: dict[str, Counter[str]] = defaultdict(Counter)
    mechanism_group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    incoming_relations: dict[str, list[str]] = defaultdict(list)
    summary_to_ids: dict[str, list[str]] = defaultdict(list)
    group_pair_counts: Counter[tuple[str, str]] = Counter()
    tag_pair_counts: Counter[tuple[str, str]] = Counter()
    mechanism_pair_counts: Counter[tuple[str, str]] = Counter()
    keyword_to_ids: dict[str, list[str]] = defaultdict(list)
    keyword_counts: Counter[str] = Counter()
    keyword_section_counts: dict[str, Counter[str]] = defaultdict(Counter)
    keyword_source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    keyword_pair_counts: Counter[tuple[str, str]] = Counter()
    source_pair_counts: Counter[tuple[str, str]] = Counter()
    fragment_section_counts: Counter[str] = Counter()
    paragraph_source_id: dict[str, str] = {}

    relation_edges = 0
    missing_relation_targets = 0
    degree_buckets = {"0": 0, "1-2": 0, "3-5": 0, "6+": 0}
    paragraphs_with_tags = 0
    paragraphs_with_idea_groups = 0
    paragraphs_with_mechanism_hints = 0
    paragraphs_with_keyword_hints = 0
    paragraphs_with_relations = 0

    for paragraph in paragraphs:
        pid = _string(paragraph.get("id"))
        section_id = _string(paragraph.get("section_id"))
        source_id = section_to_source_id.get(section_id, "")
        if section_id:
            section_to_ids[section_id].append(pid)
        if source_id:
            source_to_ids[source_id].append(pid)
            paragraph_source_id[pid] = source_id

        tags = _dedupe_strings([_string(tag) for tag in paragraph.get("tags", [])]) if isinstance(paragraph.get("tags"), list) else []
        groups = (
            _dedupe_strings([_string(gid) for gid in paragraph.get("idea_group_ids", [])])
            if isinstance(paragraph.get("idea_group_ids"), list)
            else []
        )
        mechanisms = (
            _dedupe_strings([_string(hint) for hint in paragraph.get("mechanism_hints", [])])
            if isinstance(paragraph.get("mechanism_hints"), list)
            else []
        )
        rels = (
            _dedupe_strings([_string(rid) for rid in paragraph.get("related_paragraph_ids", [])])
            if isinstance(paragraph.get("related_paragraph_ids"), list)
            else []
        )
        summary = _string(paragraph.get("summary"))
        if summary:
            summary_to_ids[summary].append(pid)
        if tags:
            paragraphs_with_tags += 1
        if groups:
            paragraphs_with_idea_groups += 1
        if mechanisms:
            paragraphs_with_mechanism_hints += 1
        keywords_norm: list[str] = []
        if isinstance(paragraph.get("keyword_hints"), list):
            for k in paragraph.get("keyword_hints", []):
                kn = _string(k).casefold()
                if kn:
                    keywords_norm.append(kn)
        keywords_norm = _dedupe_strings(keywords_norm)
        if keywords_norm:
            paragraphs_with_keyword_hints += 1
        if "fragment" in tags or "grp_fragment" in groups:
            fragment_section_counts[section_id] += 1

        for tag in tags:
            t = _string(tag)
            if not t:
                continue
            tag_to_ids[t].append(pid)
            tag_counts[t] += 1
            if section_id:
                tag_section_counts[t][section_id] += 1
                section_tag_counts[section_id][t] += 1
            if source_id:
                tag_source_counts[t][source_id] += 1
        for gid in groups:
            g = _string(gid)
            if not g:
                continue
            group_to_ids[g].append(pid)
            group_counts[g] += 1
            if section_id:
                group_section_counts[g][section_id] += 1
                section_group_counts[section_id][g] += 1
            if source_id:
                group_source_counts[g][source_id] += 1
        for tag in tags:
            for gid in groups:
                tag_group_counts[tag][gid] += 1
                group_tag_counts[gid][tag] += 1
        for mh in mechanisms:
            m = _string(mh)
            if not m:
                continue
            mechanism_to_ids[m].append(pid)
            mechanism_counts[m] += 1
            if section_id:
                mechanism_section_counts[m][section_id] += 1
                section_mechanism_counts[section_id][m] += 1
            if source_id:
                mechanism_source_counts[m][source_id] += 1
            for gid in groups:
                mechanism_group_counts[m][gid] += 1
        sorted_tags = sorted(tags)
        for index, left in enumerate(sorted_tags):
            for right in sorted_tags[index + 1:]:
                tag_pair_counts[(left, right)] += 1
        sorted_groups = sorted(groups)
        for index, left in enumerate(sorted_groups):
            for right in sorted_groups[index + 1:]:
                group_pair_counts[(left, right)] += 1
        sorted_mechanisms = sorted(mechanisms)
        for index, left in enumerate(sorted_mechanisms):
            for right in sorted_mechanisms[index + 1:]:
                mechanism_pair_counts[(left, right)] += 1

        for kw in keywords_norm:
            keyword_to_ids[kw].append(pid)
            keyword_counts[kw] += 1
            if section_id:
                keyword_section_counts[kw][section_id] += 1
            if source_id:
                keyword_source_counts[kw][source_id] += 1
        sorted_kw = sorted(keywords_norm)
        for index, left in enumerate(sorted_kw):
            for right in sorted_kw[index + 1:]:
                keyword_pair_counts[(left, right)] += 1

        degree = len(rels)
        relation_edges += degree
        if rels:
            paragraphs_with_relations += 1
        if degree == 0:
            degree_buckets["0"] += 1
        elif degree <= 2:
            degree_buckets["1-2"] += 1
        elif degree <= 5:
            degree_buckets["3-5"] += 1
        else:
            degree_buckets["6+"] += 1
        for rid in rels:
            if _string(rid) not in paragraphs_by_id:
                missing_relation_targets += 1
            incoming_relations[_string(rid)].append(pid)

    for paragraph in paragraphs:
        pid = _string(paragraph.get("id"))
        source_id = paragraph_source_id.get(pid, "")
        rels = (
            _dedupe_strings([_string(rid) for rid in paragraph.get("related_paragraph_ids", [])])
            if isinstance(paragraph.get("related_paragraph_ids"), list)
            else []
        )
        for rid in rels:
            related_source_id = paragraph_source_id.get(rid, "")
            if source_id and related_source_id and source_id != related_source_id:
                pair = tuple(sorted((source_id, related_source_id)))
                source_pair_counts[pair] += 1

    for bucket in tag_to_ids.values():
        bucket.sort(key=lambda i: _para_line_key(paragraphs_by_id[i]))
    for bucket in group_to_ids.values():
        bucket.sort(key=lambda i: _para_line_key(paragraphs_by_id[i]))
    for bucket in mechanism_to_ids.values():
        bucket.sort(key=lambda i: _para_line_key(paragraphs_by_id[i]))
    for bucket in keyword_to_ids.values():
        bucket.sort(key=lambda i: _para_line_key(paragraphs_by_id[i]))
    keyword_hint_index_truncated = sum(
        1 for _kw, ids in keyword_to_ids.items() if len(ids) > KEYWORD_HINT_INDEX_MAX_PARAGRAPH_IDS
    )
    for bucket in section_to_ids.values():
        bucket.sort(key=lambda i: _para_line_key(paragraphs_by_id[i]))
    for bucket in source_to_ids.values():
        bucket.sort(key=lambda i: _para_line_key(paragraphs_by_id[i]))
    for bucket in incoming_relations.values():
        bucket.sort(key=lambda i: _para_line_key(paragraphs_by_id.get(i, {"id": i})))

    section_rel_index: dict[str, list[str]] = {}
    for section in sections:
        sid = _string(section.get("id"))
        fill = section.get("fill") if isinstance(section.get("fill"), Mapping) else {}
        rels = fill.get("related_section_ids", []) if isinstance(fill, Mapping) else []
        if isinstance(rels, list) and rels:
            section_rel_index[sid] = _dedupe_strings([_string(x) for x in rels])

    doc = dict(payload.get("document") or {})
    family_dir = _string(payload.get("family_dir"))
    family_token = _string(payload.get("family_id")) or _string(payload.get("family_number")) or "<FAMILY>"

    raw_md_path = _string(payload.get("raw_seed_path") or "")
    raw_json_path = ""
    if raw_md_path.endswith(".md"):
        raw_json_path = raw_md_path[: -len(".md")] + ".json"
    elif family_dir:
        raw_json_path = raw_seed_json_path_for_family(family_dir)

    frontmatter = doc.get("frontmatter") if isinstance(doc.get("frontmatter"), Mapping) else {}
    source_seeds = _dedupe_strings([_string(item) for item in frontmatter.get("source_seeds", [])]) if isinstance(frontmatter.get("source_seeds"), list) else []

    source_cards_by_id: dict[str, dict[str, Any]] = {}
    for source_id in source_document_ids:
        source_section = sections_by_id.get(source_id) or {}
        descendant_section_ids = source_to_section_ids.get(source_id, [source_id])
        paragraph_ids = _dedupe_strings(
            [pid for section_id in descendant_section_ids for pid in section_to_ids.get(section_id, [])]
        )
        nested_source_sections = [
            sections_by_id.get(section_id) or {}
            for section_id in descendant_section_ids
            if section_id != source_id and _string((sections_by_id.get(section_id) or {}).get("heading")).startswith("SOURCE ")
        ]
        top_sections_counter = Counter(
            {
                section_id: len(section_to_ids.get(section_id, []))
                for section_id in descendant_section_ids
                if section_id != source_id and len(section_to_ids.get(section_id, [])) > 0
            }
        )
        if not top_sections_counter and paragraph_ids:
            top_sections_counter[source_id] = len(paragraph_ids)
        representative_section_ids = [section_id for section_id, _ in top_sections_counter.most_common(4)] or [source_id]
        top_tags_counter = Counter(
            tag
            for pid in paragraph_ids
            for tag in paragraphs_by_id.get(pid, {}).get("tags", [])
            if _string(tag)
        )
        top_groups_counter = Counter(
            group
            for pid in paragraph_ids
            for group in paragraphs_by_id.get(pid, {}).get("idea_group_ids", [])
            if _string(group)
        )
        top_mechanisms_counter = Counter(
            mechanism
            for pid in paragraph_ids
            for mechanism in paragraphs_by_id.get(pid, {}).get("mechanism_hints", [])
            if _string(mechanism)
        )
        fill = source_section.get("fill") if isinstance(source_section.get("fill"), Mapping) else {}
        source_cards_by_id[source_id] = {
            "id": source_id,
            "path": _string(source_section.get("path")),
            "heading": _string(source_section.get("heading")),
            "heading_slug": _string(source_section.get("heading_slug")),
            "level": int(source_section.get("level") or 0),
            "line_start": int(source_section.get("line_start") or 0),
            "line_end": int(source_section.get("line_end") or 0),
            "paragraph_count": len(paragraph_ids),
            "section_count": len(descendant_section_ids),
            "note": _trim_text(source_section.get("note"), max_chars=180),
            "purpose": _trim_text(fill.get("purpose"), max_chars=200),
            "top_tags": _counter_records(top_tags_counter, key_name="tag", value_name="paragraph_refs", limit=6),
            "top_idea_groups": _counter_records(
                top_groups_counter,
                key_name="idea_group_id",
                value_name="paragraph_refs",
                limit=6,
            ),
            "top_mechanism_hints": _counter_records(
                top_mechanisms_counter,
                key_name="mechanism_hint",
                value_name="paragraph_refs",
                limit=6,
            ),
            "source_sections": [
                {
                    "section_id": _string(section.get("id")),
                    "heading": _string(section.get("heading")),
                    "path": _string(section.get("path")),
                    "paragraph_count": len(section_to_ids.get(_string(section.get("id")), [])),
                }
                for section in nested_source_sections[:6]
            ],
            "top_sections": _section_counter_records(top_sections_counter, sections_by_id, limit=6),
            "representative_section_ids": representative_section_ids,
            "representative_paragraph_ids": _representative_paragraph_ids(
                paragraph_ids,
                paragraphs_by_id,
                incoming_relations,
                limit=6,
            ),
            "related_sources": [],
        }

    def _source_neighbor_counter(token: str) -> Counter[str]:
        counter: Counter[str] = Counter()
        for pair, count in source_pair_counts.items():
            if len(pair) != 2:
                continue
            left, right = pair
            if left == token:
                counter[right] += int(count or 0)
            elif right == token:
                counter[left] += int(count or 0)
        return counter

    for source_id, card in source_cards_by_id.items():
        card["related_sources"] = _document_counter_records(
            _source_neighbor_counter(source_id),
            source_cards_by_id,
            value_name="cross_document_edges",
            limit=6,
        )

    source_cards = [dict(source_cards_by_id[source_id]) for source_id in source_document_ids if source_id in source_cards_by_id]

    sections_toc: list[dict[str, Any]] = []
    for section in sorted(sections, key=lambda s: (int(s.get("line_start") or 0), _string(s.get("id")))):
        sid = _string(section.get("id"))
        source_id = section_to_source_id.get(sid, "")
        source_card = source_cards_by_id.get(source_id) or {}
        pids = section_to_ids.get(sid, [])
        stags = _dedupe_strings([_string(t) for t in section.get("tags", []) if isinstance(section.get("tags"), list)])
        fill = section.get("fill") if isinstance(section.get("fill"), Mapping) else {}
        sections_toc.append(
            {
                "id": sid,
                "path": _string(section.get("path")),
                "heading": _string(section.get("heading")),
                "heading_slug": _string(section.get("heading_slug")),
                "level": int(section.get("level") or 0),
                "parent_id": _string(section.get("parent_id")),
                "line_start": int(section.get("line_start") or 0),
                "line_end": int(section.get("line_end") or 0),
                "paragraph_count": len(pids),
                "source_id": source_id,
                "source_heading": _string(source_card.get("heading")),
                "source_path": _string(source_card.get("path")),
                "tags": stags[:12],
                "note": _trim_text(section.get("note"), max_chars=180),
                "purpose": _trim_text(fill.get("purpose"), max_chars=200),
                "grouping_hints": _dedupe_strings([_string(item) for item in fill.get("grouping_hints", [])])[:8]
                if isinstance(fill.get("grouping_hints"), list)
                else [],
                "related_section_ids": section_rel_index.get(sid, []),
                "top_tags": _counter_records(section_tag_counts.get(sid, Counter()), key_name="tag", value_name="paragraph_refs", limit=6),
                "top_idea_groups": _counter_records(
                    section_group_counts.get(sid, Counter()),
                    key_name="idea_group_id",
                    value_name="paragraph_refs",
                    limit=6,
                ),
                "top_mechanism_hints": _counter_records(
                    section_mechanism_counts.get(sid, Counter()),
                    key_name="mechanism_hint",
                    value_name="paragraph_refs",
                    limit=6,
                ),
                "representative_paragraph_ids": _representative_paragraph_ids(
                    pids,
                    paragraphs_by_id,
                    incoming_relations,
                    limit=4,
                ),
            }
        )

    tags_top = [{"tag": t, "paragraph_refs": c} for t, c in tag_counts.most_common(80)]
    groups_top = [{"idea_group_id": g, "paragraph_refs": c} for g, c in group_counts.most_common(80)]
    mechanisms_top = [{"mechanism_hint": m, "paragraph_refs": c} for m, c in mechanism_counts.most_common(40)]
    keywords_top = [{"keyword_hint": k, "paragraph_refs": c} for k, c in keyword_counts.most_common(60)]
    sections_top = [
        {
            "section_id": sid,
            "heading": _string(sections_by_id.get(sid, {}).get("heading")),
            "path": _string(sections_by_id.get(sid, {}).get("path")),
            "paragraphs": len(ids),
        }
        for sid, ids in sorted(section_to_ids.items(), key=lambda item: (-len(item[1]), item[0]))[:20]
    ]
    sources_top = [
        {
            "source_id": source_card.get("id"),
            "heading": source_card.get("heading"),
            "path": source_card.get("path"),
            "paragraphs": int(source_card.get("paragraph_count") or 0),
        }
        for source_card in sorted(
            source_cards,
            key=lambda item: (-int(item.get("paragraph_count") or 0), _string(item.get("id"))),
        )[:10]
    ]

    summaries_filled = sum(1 for p in paragraphs if _string(p.get("summary")))
    notes_filled = sum(1 for p in paragraphs if _string(p.get("note")))

    navigation_cli = [
        {
            "id": "sync_registry",
            "command": f"python3 kernel.py --sync-raw-seed {family_token} --live",
            "does": "Rebuild raw_seed.json from raw_seed.md while preserving semantic fill fields.",
        },
        {
            "id": "sync_index",
            "command": f"python3 kernel.py --sync-raw-seed-index {family_token} --live",
            "does": "Regenerate raw_seed_index.json from raw_seed.json (this file).",
        },
        {
            "id": "resolve_ref",
            "command": f"python3 kernel.py --resolve-raw-seed-ref {family_token} \"<REF>\"",
            "does": "Resolve a section id, path:, paragraph id, or heading text to the registry object.",
        },
        {
            "id": "index_query",
            "command": f"python3 kernel.py --raw-seed-index {family_token}",
            "does": "Emit this index or a filtered slice (see optional flags on --raw-seed-index).",
        },
        {
            "id": "index_source_slice",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-source \"<SOURCE REF>\"",
            "does": "Inspect one top-level source document with dominant themes, nested source sections, and representative paragraphs.",
        },
        {
            "id": "index_tag_slice",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-tag <kebab-tag>",
            "does": "Inspect one tag card and representative matching paragraphs.",
        },
        {
            "id": "index_group_slice",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-group <grp_id>",
            "does": "Inspect one idea-group card and representative matching paragraphs.",
        },
        {
            "id": "index_mechanism_slice",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-mechanism <hint>",
            "does": "Inspect one mechanism card and representative matching paragraphs.",
        },
        {
            "id": "index_keyword_slice",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-keyword <hint>",
            "does": "Inspect one derived keyword_hint card (corpus-distinctive terms) and representative matching paragraphs.",
        },
        {
            "id": "index_section_card",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-section \"<SECTION REF>\"",
            "does": "Return one section card with purpose, dominant themes, source lineage, related sections, and representative paragraph stubs.",
        },
        {
            "id": "index_route_card",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-route \"<ROUTE REF>\"",
            "does": "Inspect one repeated-claim route by route id or exact summary text.",
        },
        {
            "id": "index_paragraph_card",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-paragraph \"paragraph:<ID>\"",
            "does": "Return one paragraph neighborhood with outbound/inbound links, local section neighbors, and thematic neighbors.",
        },
        {
            "id": "index_diagnostics",
            "command": f"python3 kernel.py --raw-seed-index {family_token} --seed-index-diagnostics",
            "does": "Expose compression watchlists, repeated-claim routes, fragment-heavy sections, and top paragraph hubs.",
        },
        {
            "id": "annotate",
            "command": f"python3 kernel.py --annotate-raw-seed {family_token} \"paragraph:<ID>\" tags <value> --live",
            "does": "Append one annotation field (repeatable pattern); merges like --sync-raw-seed.",
        },
    ]

    navigation_surfaces = [
        {
            "id": "sources",
            "question": "Which source document or imported blackboard should I traverse first?",
            "cli_flag": "--seed-index-source",
        },
        {
            "id": "sections",
            "question": "What is this section for, and where should I jump next?",
            "cli_flag": "--seed-index-section",
        },
        {
            "id": "themes",
            "question": "Which tag, idea group, mechanism cluster, or derived keyword carries this idea?",
            "cli_flag": "--seed-index-tag / --seed-index-group / --seed-index-mechanism / --seed-index-keyword",
        },
        {
            "id": "claim_routes",
            "question": "Which repeated claims dominate the corpus or indicate over-compression?",
            "cli_flag": "--seed-index-route / --seed-index-diagnostics",
        },
        {
            "id": "paragraph_neighborhoods",
            "question": "What nearby and thematic paragraphs deepen this one claim?",
            "cli_flag": "--seed-index-paragraph",
        },
    ]
    ref_hints = [
        "Source: pass the top-level document section id, path:<slug>, heading slug, or exact heading text.",
        "Section: pass section id, path:<slug/path>, or exact heading text.",
        "Paragraph: pass the full par_* id from markers or this index.",
        "Route: pass route_<hash> from routes.claim_routes_top or the exact repeated summary text.",
        "Document root: ref * or all returns document metadata only.",
    ]

    idea_group_cards: list[dict[str, Any]] = []
    for group_id, count in group_counts.most_common():
        ids = group_to_ids[group_id]
        idea_group_cards.append(
            {
                "id": group_id,
                "label": _humanize_token(group_id, prefix="grp_"),
                "paragraph_count": int(count or 0),
                "section_count": len(group_section_counts.get(group_id, Counter())),
                "source_count": len(group_source_counts.get(group_id, Counter())),
                "top_sections": _section_counter_records(group_section_counts.get(group_id, Counter()), sections_by_id, limit=6),
                "top_sources": _document_counter_records(
                    group_source_counts.get(group_id, Counter()),
                    source_cards_by_id,
                    limit=4,
                ),
                "top_tags": _counter_records(group_tag_counts.get(group_id, Counter()), key_name="tag", value_name="paragraph_refs", limit=6),
                "related_idea_groups": _pair_neighbor_records(
                    group_id,
                    group_pair_counts,
                    key_name="idea_group_id",
                    value_name="shared_paragraphs",
                    limit=6,
                ),
                "representative_paragraph_ids": _representative_paragraph_ids(
                    ids,
                    paragraphs_by_id,
                    incoming_relations,
                    limit=6,
                ),
            }
        )

    tag_cards: list[dict[str, Any]] = []
    for tag, count in tag_counts.most_common():
        ids = tag_to_ids[tag]
        tag_cards.append(
            {
                "tag": tag,
                "paragraph_count": int(count or 0),
                "section_count": len(tag_section_counts.get(tag, Counter())),
                "source_count": len(tag_source_counts.get(tag, Counter())),
                "top_sections": _section_counter_records(tag_section_counts.get(tag, Counter()), sections_by_id, limit=6),
                "top_sources": _document_counter_records(tag_source_counts.get(tag, Counter()), source_cards_by_id, limit=4),
                "top_idea_groups": _counter_records(
                    tag_group_counts.get(tag, Counter()),
                    key_name="idea_group_id",
                    value_name="paragraph_refs",
                    limit=6,
                ),
                "related_tags": _pair_neighbor_records(tag, tag_pair_counts, key_name="tag", value_name="shared_paragraphs", limit=6),
                "representative_paragraph_ids": _representative_paragraph_ids(
                    ids,
                    paragraphs_by_id,
                    incoming_relations,
                    limit=6,
                ),
            }
        )

    mechanism_cards: list[dict[str, Any]] = []
    for mechanism, count in mechanism_counts.most_common():
        ids = mechanism_to_ids[mechanism]
        mechanism_cards.append(
            {
                "mechanism_hint": mechanism,
                "paragraph_count": int(count or 0),
                "section_count": len(mechanism_section_counts.get(mechanism, Counter())),
                "source_count": len(mechanism_source_counts.get(mechanism, Counter())),
                "top_sections": _section_counter_records(
                    mechanism_section_counts.get(mechanism, Counter()),
                    sections_by_id,
                    limit=6,
                ),
                "top_sources": _document_counter_records(
                    mechanism_source_counts.get(mechanism, Counter()),
                    source_cards_by_id,
                    limit=4,
                ),
                "top_idea_groups": _counter_records(
                    mechanism_group_counts.get(mechanism, Counter()),
                    key_name="idea_group_id",
                    value_name="paragraph_refs",
                    limit=6,
                ),
                "related_mechanism_hints": _pair_neighbor_records(
                    mechanism,
                    mechanism_pair_counts,
                    key_name="mechanism_hint",
                    value_name="shared_paragraphs",
                    limit=6,
                ),
                "representative_paragraph_ids": _representative_paragraph_ids(
                    ids,
                    paragraphs_by_id,
                    incoming_relations,
                    limit=6,
                ),
            }
        )

    keyword_cards: list[dict[str, Any]] = []
    for kw, count in keyword_counts.most_common():
        ids = keyword_to_ids[kw]
        keyword_cards.append(
            {
                "keyword_hint": kw,
                "paragraph_count": int(count or 0),
                "section_count": len(keyword_section_counts.get(kw, Counter())),
                "source_count": len(keyword_source_counts.get(kw, Counter())),
                "top_sections": _section_counter_records(
                    keyword_section_counts.get(kw, Counter()),
                    sections_by_id,
                    limit=6,
                ),
                "top_sources": _document_counter_records(
                    keyword_source_counts.get(kw, Counter()),
                    source_cards_by_id,
                    limit=4,
                ),
                "related_keyword_hints": _pair_neighbor_records(
                    kw,
                    keyword_pair_counts,
                    key_name="keyword_hint",
                    value_name="shared_paragraphs",
                    limit=6,
                ),
                "representative_paragraph_ids": _representative_paragraph_ids(
                    ids,
                    paragraphs_by_id,
                    incoming_relations,
                    limit=6,
                ),
            }
        )

    paragraph_hubs = sorted(
        paragraphs,
        key=lambda paragraph: (
            -(
                len(paragraph.get("related_paragraph_ids", [])) if isinstance(paragraph.get("related_paragraph_ids"), list) else 0
            ) - len(incoming_relations.get(_string(paragraph.get("id")), [])),
            -(len(paragraph.get("related_paragraph_ids", [])) if isinstance(paragraph.get("related_paragraph_ids"), list) else 0),
            int(paragraph.get("line_start") or 0),
            _string(paragraph.get("id")),
        ),
    )
    top_paragraph_hubs = [
        _paragraph_stub(
            paragraph,
            section_heading=_string(sections_by_id.get(_string(paragraph.get("section_id")), {}).get("heading")),
            incoming_related_ids=incoming_relations.get(_string(paragraph.get("id")), []),
        )
        for paragraph in paragraph_hubs[:20]
    ]

    claim_route_cards: list[dict[str, Any]] = []
    route_to_ids: dict[str, list[str]] = {}
    for summary, ids in sorted(summary_to_ids.items(), key=lambda item: (-len(item[1]), item[0])):
        normalized_summary = _string(summary)
        if not normalized_summary or len(ids) <= 1:
            continue
        route_id = _route_id_for_summary(normalized_summary)
        route_to_ids[route_id] = _dedupe_strings(list(ids))
        section_counter = Counter(
            _string(paragraphs_by_id.get(pid, {}).get("section_id"))
            for pid in ids
            if _string(paragraphs_by_id.get(pid, {}).get("section_id"))
        )
        source_counter = Counter(
            paragraph_source_id.get(pid, "")
            for pid in ids
            if paragraph_source_id.get(pid, "")
        )
        claim_route_cards.append(
            {
                "id": route_id,
                "summary": _trim_text(normalized_summary, max_chars=180),
                "paragraph_count": len(ids),
                "section_count": len(section_counter),
                "source_count": len(source_counter),
                "top_sections": _section_counter_records(section_counter, sections_by_id, limit=5),
                "top_sources": _document_counter_records(source_counter, source_cards_by_id, limit=4),
                "top_tags": _counter_records(
                    Counter(tag for pid in ids for tag in paragraphs_by_id.get(pid, {}).get("tags", []) if _string(tag)),
                    key_name="tag",
                    value_name="paragraph_refs",
                    limit=5,
                ),
                "top_idea_groups": _counter_records(
                    Counter(group for pid in ids for group in paragraphs_by_id.get(pid, {}).get("idea_group_ids", []) if _string(group)),
                    key_name="idea_group_id",
                    value_name="paragraph_refs",
                    limit=5,
                ),
                "sample_paragraph_ids": _representative_paragraph_ids(ids, paragraphs_by_id, incoming_relations, limit=6),
            }
        )

    section_duplicate_pressure_top: list[dict[str, Any]] = []
    for sid, ids in section_to_ids.items():
        if not ids:
            continue
        duplicated_ids = [
            pid
            for pid in ids
            if _string(paragraphs_by_id.get(pid, {}).get("summary"))
            and len(summary_to_ids.get(_string(paragraphs_by_id.get(pid, {}).get("summary")), [])) > 1
        ]
        if not duplicated_ids:
            continue
        summary_counter = Counter(_string(paragraphs_by_id.get(pid, {}).get("summary")) for pid in duplicated_ids)
        dominant_summary, dominant_count = summary_counter.most_common(1)[0]
        section_duplicate_pressure_top.append(
            {
                "section_id": sid,
                "heading": _string(sections_by_id.get(sid, {}).get("heading")),
                "path": _string(sections_by_id.get(sid, {}).get("path")),
                "paragraph_count": len(ids),
                "duplicated_paragraph_count": len(duplicated_ids),
                "duplicated_ratio": round(len(duplicated_ids) / max(1, len(ids)), 3),
                "dominant_claim": _trim_text(dominant_summary, max_chars=140),
                "dominant_claim_count": int(dominant_count or 0),
            }
        )
    section_duplicate_pressure_top.sort(
        key=lambda item: (
            -float(item.get("duplicated_ratio") or 0.0),
            -int(item.get("duplicated_paragraph_count") or 0),
            _string(item.get("section_id")),
        )
    )

    fragment_heavy_sections_top = [
        {
            "section_id": sid,
            "heading": _string(sections_by_id.get(sid, {}).get("heading")),
            "path": _string(sections_by_id.get(sid, {}).get("path")),
            "paragraph_count": len(section_to_ids.get(sid, [])),
            "fragment_paragraph_count": int(count or 0),
            "fragment_ratio": round(int(count or 0) / max(1, len(section_to_ids.get(sid, []))), 3),
        }
        for sid, count in fragment_section_counts.items()
        if sid and int(count or 0) > 0
    ]
    fragment_heavy_sections_top.sort(
        key=lambda item: (
            -float(item.get("fragment_ratio") or 0.0),
            -int(item.get("fragment_paragraph_count") or 0),
            _string(item.get("section_id")),
        )
    )

    documentation_records = [record for record in raw_seed_documentation_records_for_family(family_dir) if _string(record.get("path"))]

    return {
        "kind": "raw_seed_index",
        "schema_version": RAW_SEED_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "raw_seed_markdown_path": raw_md_path,
            "raw_seed_json_path": raw_json_path,
            "raw_seed_workspace_dir": raw_seed_workspace_dir_for_family(family_dir),
            "documentation_paths": raw_seed_documentation_paths_for_family(family_dir),
            "documentation": documentation_records,
            "registry_updated_at": _string(payload.get("updated_at")),
            "family_id": _string(payload.get("family_id")),
            "family_dir": family_dir,
            "source_seeds": source_seeds,
            "document": {
                "total_sections": int(doc.get("total_sections") or 0),
                "total_paragraphs": int(doc.get("total_paragraphs") or 0),
                "paragraph_array_order": _string(doc.get("paragraph_array_order")),
            },
        },
        "navigation": {
            "cli": navigation_cli,
            "surfaces": navigation_surfaces,
            "ref_syntax_hints": ref_hints,
        },
        "statistics": {
            "paragraphs": len(paragraphs),
            "sections": len(sections),
            "sources": len(source_cards),
            "registry_notes": len(payload.get("notes", [])) if isinstance(payload.get("notes"), list) else 0,
            "unique_tags": len(tag_counts),
            "unique_idea_groups": len(group_counts),
            "unique_mechanism_hints": len(mechanism_counts),
            "unique_keyword_hints": len(keyword_counts),
            "keyword_hint_index_entries_truncated": int(keyword_hint_index_truncated),
            "paragraphs_with_tags": paragraphs_with_tags,
            "paragraphs_with_idea_groups": paragraphs_with_idea_groups,
            "paragraphs_with_mechanism_hints": paragraphs_with_mechanism_hints,
            "paragraphs_with_keyword_hints": paragraphs_with_keyword_hints,
            "paragraphs_with_related_paragraphs": paragraphs_with_relations,
            "paragraphs_with_non_empty_summary": summaries_filled,
            "paragraphs_with_non_empty_note": notes_filled,
            "related_paragraph_edges_directed": relation_edges,
            "related_paragraph_edges_missing_target_id": missing_relation_targets,
            "related_paragraph_degree_histogram": degree_buckets,
            "duplicate_summary_clusters": len(claim_route_cards),
            "tags_top": tags_top,
            "idea_groups_top": groups_top,
            "mechanism_hints_top": mechanisms_top,
            "keyword_hints_top": keywords_top,
            "sections_top": sections_top,
            "sources_top": sources_top,
        },
        "sections_toc": sections_toc,
        "sources": source_cards,
        "themes": {
            "idea_groups": idea_group_cards,
            "tags": tag_cards,
            "mechanism_hints": mechanism_cards,
            "keyword_hints": keyword_cards,
        },
        "routes": {
            "claim_routes_top": claim_route_cards[:25],
        },
        "crosslinks": {
            "source_pairs_top": [
                {
                    "source_ids": [left, right],
                    "shared_relation_edges": int(count or 0),
                }
                for (left, right), count in source_pair_counts.most_common(20)
            ],
            "idea_group_pairs_top": [
                {"idea_group_ids": [left, right], "shared_paragraphs": int(count or 0)}
                for (left, right), count in group_pair_counts.most_common(20)
            ],
            "tag_pairs_top": [
                {"tags": [left, right], "shared_paragraphs": int(count or 0)}
                for (left, right), count in tag_pair_counts.most_common(20)
            ],
            "mechanism_hint_pairs_top": [
                {"mechanism_hints": [left, right], "shared_paragraphs": int(count or 0)}
                for (left, right), count in mechanism_pair_counts.most_common(20)
            ],
            "keyword_hint_pairs_top": [
                {"keyword_hints": [left, right], "shared_paragraphs": int(count or 0)}
                for (left, right), count in keyword_pair_counts.most_common(20)
            ],
            "term_cooccurrence_top": [
                {"terms": [left, right], "co_paragraph_count": int(count or 0)}
                for (left, right), count in keyword_pair_counts.most_common(200)
            ],
        },
        "diagnostics": {
            "top_paragraph_hubs": top_paragraph_hubs,
            "duplicate_summary_clusters_top": claim_route_cards[:25],
            "section_duplicate_pressure_top": section_duplicate_pressure_top[:20],
            "fragment_heavy_sections_top": fragment_heavy_sections_top[:20],
            "sections_without_related_sections": [
                {
                    "section_id": _string(section.get("id")),
                    "heading": _string(section.get("heading")),
                    "path": _string(section.get("path")),
                    "paragraph_count": len(section_to_ids.get(_string(section.get("id")), [])),
                }
                for section in sorted(sections, key=lambda item: (int(item.get("line_start") or 0), _string(item.get("id"))))
                if _string(section.get("id")) != root_section_id and not section_rel_index.get(_string(section.get("id")))
            ],
        },
        "indexes": {
            "tag_to_paragraph_ids": {k: tag_to_ids[k] for k in sorted(tag_to_ids.keys())},
            "idea_group_to_paragraph_ids": {k: group_to_ids[k] for k in sorted(group_to_ids.keys())},
            "mechanism_hint_to_paragraph_ids": {k: mechanism_to_ids[k] for k in sorted(mechanism_to_ids.keys())},
            "keyword_hint_to_paragraph_ids": {
                k: keyword_to_ids[k][:KEYWORD_HINT_INDEX_MAX_PARAGRAPH_IDS]
                for k in sorted(keyword_to_ids.keys())
            },
            "source_id_to_paragraph_ids": {k: source_to_ids[k] for k in sorted(source_to_ids.keys())},
            "route_id_to_paragraph_ids": {k: route_to_ids[k] for k in sorted(route_to_ids.keys())},
            "section_id_to_paragraph_ids": {k: section_to_ids[k] for k in sorted(section_to_ids.keys())},
            "section_id_to_related_section_ids": section_rel_index,
            "section_id_to_source_id": {k: v for k, v in sorted(section_to_source_id.items()) if _string(v)},
            "section_path_to_section_id": {
                _string(section.get("path")): _string(section.get("id"))
                for section in sections
                if _string(section.get("path"))
            },
        },
    }


def build_raw_seed_shards(payload: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Emit a derived shard surface over the family raw seed so paragraph-fingerprint-backed shards, per-group dedication scores, and sibling shard adjacency are queryable without mutating the append-only blackboard.
    - Mechanism: One shard per paragraph carrying at least one idea_group_id. Shard id = "sh_" + paragraph_fingerprint. Sibling shard ids come from idea_group overlap: every other paragraph sharing at least one idea_group_id contributes its shard id to sibling_shard_ids. Dedication scores are read from the paragraph `group_relevance` map written during compile.
    - Guarantee: Returns a dict {kind, schema_version, generated_at, family_id, family_number, source, counts, shards[]} where shards is sorted by shard_id. Paragraphs without idea_group_ids do not appear. Sibling shard ids are deduped and sorted.
    - Fails: None.
    - When-needed: Open when a derived shard surface is needed (sibling adjacency, dedication rankings, bridge-scoped shard selection) and the family raw seed must stay append-only.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_index; system/lib/kernel/commands/substrate.py::cmd_sync_raw_seed_index
    - Navigation-group: kernel_lib
    """
    paragraphs = [
        dict(p)
        for p in payload.get("paragraphs", [])
        if isinstance(p, Mapping) and _string(p.get("id"))
    ]
    family_id = _string(payload.get("family_id"))
    family_number = _string(payload.get("family_number"))

    paragraph_fp: dict[str, str] = {}
    for paragraph in paragraphs:
        pid = _string(paragraph.get("id"))
        fp = _string(paragraph.get("paragraph_fingerprint")) or _string(paragraph.get("fingerprint"))
        if not pid or not fp:
            continue
        paragraph_fp[pid] = fp

    group_to_paragraph_ids: dict[str, list[str]] = defaultdict(list)
    paragraph_to_groups: dict[str, list[str]] = {}
    for paragraph in paragraphs:
        pid = _string(paragraph.get("id"))
        if not pid:
            continue
        groups = _dedupe_strings([_string(g) for g in paragraph.get("idea_group_ids") or [] if _string(g)])
        if not groups:
            continue
        paragraph_to_groups[pid] = groups
        for group_id in groups:
            group_to_paragraph_ids[group_id].append(pid)

    shards: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        pid = _string(paragraph.get("id"))
        if not pid:
            continue
        groups = paragraph_to_groups.get(pid) or []
        if not groups:
            continue
        fingerprint = paragraph_fp.get(pid)
        if not fingerprint:
            continue
        shard_id = f"sh_{fingerprint}"

        dedication_map = paragraph.get("group_relevance") or {}
        if isinstance(dedication_map, Mapping):
            dedication_scores = {
                _string(group): float(dedication_map.get(group))
                for group in groups
                if isinstance(dedication_map.get(group), (int, float))
            }
        else:
            dedication_scores = {}

        sibling_ids: list[str] = []
        for group_id in groups:
            for other_pid in group_to_paragraph_ids.get(group_id, []):
                if other_pid == pid:
                    continue
                other_fp = paragraph_fp.get(other_pid)
                if not other_fp:
                    continue
                sibling_ids.append(f"sh_{other_fp}")
        sibling_shard_ids = sorted(set(sibling_ids))

        shards.append(
            {
                "shard_id": shard_id,
                "parent_paragraph_id": pid,
                "paragraph_fingerprint": fingerprint,
                "source_substrate": _string(paragraph.get("source_substrate")) or "raw_seed",
                "authored_by": _string(paragraph.get("authored_by")) or "operator",
                "idea_group_ids": groups,
                "sibling_shard_ids": sibling_shard_ids,
                "dedication_scores": dedication_scores,
                "dedication_max": max(dedication_scores.values()) if dedication_scores else 0.0,
                "status": "open",
            }
        )

    shards.sort(key=lambda s: _string(s.get("shard_id")))

    return {
        "kind": "raw_seed_shards",
        "schema_version": RAW_SEED_SHARDS_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "family_id": family_id,
        "family_number": family_number,
        "source": {
            "raw_seed_json_path": _string(payload.get("raw_seed_json_path"))
            or raw_seed_json_path_for_family(_string(payload.get("family_dir"))),
            "raw_seed_markdown_path": raw_seed_markdown_path_for_family(
                _string(payload.get("family_dir"))
            ),
            "registry_updated_at": _string(payload.get("updated_at")),
        },
        "counts": {
            "total_paragraphs": len(paragraphs),
            "total_shards": len(shards),
            "total_idea_groups": len(group_to_paragraph_ids),
        },
        "shards": shards,
    }


def _navigation_target_records(values: Any) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    if not isinstance(values, list):
        return records
    for item in values:
        if not isinstance(item, Mapping):
            continue
        kind = _string(item.get("kind"))
        target_id = _string(item.get("id"))
        title = _string(item.get("title"))
        key_basis = target_id or title or kind
        if not key_basis:
            continue
        key = f"{kind}:{key_basis}" if kind else key_basis
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "key": key,
                "kind": kind,
                "id": target_id,
                "title": title,
            }
        )
    return records


def _navigation_statement(
    shard: Mapping[str, Any],
    *,
    paragraphs_by_id: Mapping[str, Mapping[str, Any]],
    paragraph_ids: list[str],
) -> str:
    for field in (
        "clarified_statement",
        "statement",
        "gloss",
        "summary",
        "voice_anchor",
        "text",
        "plain_text",
    ):
        token = _trim_text(shard.get(field), max_chars=220)
        if token:
            return token
    for paragraph_id in paragraph_ids:
        paragraph = paragraphs_by_id.get(paragraph_id) or {}
        token = _trim_text(paragraph.get("summary") or paragraph.get("plain_text"), max_chars=220)
        if token:
            return token
    return ""


def build_raw_seed_navigation_graph(
    payload: Mapping[str, Any],
    shard_rows: list[Mapping[str, Any]] | None = None,
    *,
    shard_surface_kind: str = "raw_seed_shards",
    shard_surface_path: str = "",
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Emit the compressed neighborhood graph that sits between narrative raw-seed compressions and the full shard field.
    - Mechanism: Aggregate shard rows by `idea_group_ids`, derive group co-membership edges, collect paragraph hubs, and preserve compact route-target / section / mechanism hints without duplicating the whole shard corpus.
    - Guarantee: Returns a dict {kind, schema_version, generated_at, source, counts, groups, edges, paragraph_hubs, target_cards, indexes} with deterministic ordering.
    - Fails: None.
    - When-needed: Open when an agent needs a navigation-grade shard projection instead of the full `extracted_shards.json` / `raw_seed_shards.json` surface.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_shards; system/lib/kernel/commands/substrate.py::cmd_raw_seed_navigation
    - Navigation-group: kernel_lib
    """
    paragraphs = [
        dict(item)
        for item in payload.get("paragraphs", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    ]
    sections = [
        dict(item)
        for item in payload.get("sections", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    ]
    paragraphs_by_id = {
        _string(item.get("id")): item
        for item in paragraphs
        if _string(item.get("id"))
    }
    document = payload.get("document") if isinstance(payload.get("document"), Mapping) else {}
    paragraph_id_migrations = (
        document.get("paragraph_id_migrations")
        if isinstance(document.get("paragraph_id_migrations"), Mapping)
        else {}
    )

    def _normalize_navigation_paragraph_id(value: Any) -> str:
        token = _string(value)
        if not token:
            return ""
        migrated = _string(paragraph_id_migrations.get(token))
        return migrated or token

    sections_by_id = {
        _string(item.get("id")): item
        for item in sections
        if _string(item.get("id"))
    }
    if shard_rows is None:
        shard_rows = build_raw_seed_shards(payload).get("shards") or []

    group_memberships = 0
    group_acc: dict[str, dict[str, Any]] = {}
    edge_counts: Counter[tuple[str, str]] = Counter()
    target_acc: dict[str, dict[str, Any]] = {}
    paragraph_acc: dict[str, dict[str, Any]] = {}
    shards_considered = 0

    for item in shard_rows:
        if not isinstance(item, Mapping):
            continue
        shard_id = _string(item.get("id") or item.get("shard_id"))
        if not shard_id:
            continue
        groups = _dedupe_strings([_string(group_id) for group_id in item.get("idea_group_ids") or [] if _string(group_id)])
        if not groups:
            continue
        shards_considered += 1
        group_memberships += len(groups)

        paragraph_ids = _dedupe_strings(
            [
                _normalize_navigation_paragraph_id(paragraph_id)
                for paragraph_id in item.get("raw_paragraph_ids") or []
                if _normalize_navigation_paragraph_id(paragraph_id)
            ]
        )
        parent_paragraph_id = _normalize_navigation_paragraph_id(item.get("parent_paragraph_id"))
        if parent_paragraph_id and parent_paragraph_id not in paragraph_ids:
            paragraph_ids.append(parent_paragraph_id)

        target_records = _navigation_target_records(item.get("routing_targets"))
        statement = _navigation_statement(item, paragraphs_by_id=paragraphs_by_id, paragraph_ids=paragraph_ids)
        shard_stub = {
            "id": shard_id,
            "statement": statement,
            "voice_anchor": _trim_text(item.get("voice_anchor"), max_chars=180),
            "paragraph_ids": paragraph_ids[:6],
            "status": _string(item.get("status")) or "unknown",
            "coverage_state": _string(item.get("coverage_state")) or "unknown",
            "routing_state": _string(item.get("routing_state")) or "unknown",
            "target_keys": [record["key"] for record in target_records[:4]],
            "_priority": (
                -len(groups),
                -len(target_records),
                -len(paragraph_ids),
                shard_id,
            ),
        }

        for paragraph_id in paragraph_ids:
            paragraph = paragraphs_by_id.get(paragraph_id) or {}
            paragraph_card = paragraph_acc.setdefault(
                paragraph_id,
                {
                    "paragraph_id": paragraph_id,
                    "shard_ids": set(),
                    "group_ids": set(),
                    "section_id": _string(paragraph.get("section_id")),
                    "section_path": _string(paragraph.get("section_path")),
                    "section_heading": "",
                    "summary": _trim_text(paragraph.get("summary") or paragraph.get("plain_text"), max_chars=220),
                    "line_start": int(paragraph.get("line_start") or 0),
                },
            )
            paragraph_card["shard_ids"].add(shard_id)
            paragraph_card["group_ids"].update(groups)
            section = sections_by_id.get(_string(paragraph_card.get("section_id"))) or {}
            paragraph_card["section_heading"] = _string(section.get("heading"))

        for left_index, left_group in enumerate(groups):
            group_card = group_acc.setdefault(
                left_group,
                {
                    "group_id": left_group,
                    "title": _humanize_token(left_group, prefix="grp_"),
                    "shard_ids": set(),
                    "paragraph_ids": set(),
                    "status_counts": Counter(),
                    "coverage_counts": Counter(),
                    "routing_counts": Counter(),
                    "keyword_counts": Counter(),
                    "mechanism_counts": Counter(),
                    "section_counts": Counter(),
                    "target_counts": Counter(),
                    "target_meta": {},
                    "representative_shards": [],
                },
            )
            group_card["shard_ids"].add(shard_id)
            group_card["paragraph_ids"].update(paragraph_ids)
            group_card["status_counts"][shard_stub["status"]] += 1
            group_card["coverage_counts"][shard_stub["coverage_state"]] += 1
            group_card["routing_counts"][shard_stub["routing_state"]] += 1
            group_card["representative_shards"].append(dict(shard_stub))

            for paragraph_id in paragraph_ids:
                paragraph = paragraphs_by_id.get(paragraph_id) or {}
                for keyword in _dedupe_strings([_string(value).casefold() for value in paragraph.get("keyword_hints") or [] if _string(value)]):
                    group_card["keyword_counts"][keyword] += 1
                for mechanism in _dedupe_strings([_string(value) for value in paragraph.get("mechanism_hints") or [] if _string(value)]):
                    group_card["mechanism_counts"][mechanism] += 1
                section_id = _string(paragraph.get("section_id"))
                if section_id:
                    group_card["section_counts"][section_id] += 1

            for target in target_records:
                key = target["key"]
                group_card["target_counts"][key] += 1
                group_card["target_meta"][key] = target
                target_card = target_acc.setdefault(
                    key,
                    {
                        "key": key,
                        "kind": target["kind"],
                        "id": target["id"],
                        "title": target["title"],
                        "group_ids": set(),
                        "paragraph_ids": set(),
                        "shard_ids": set(),
                    },
                )
                target_card["group_ids"].add(left_group)
                target_card["paragraph_ids"].update(paragraph_ids)
                target_card["shard_ids"].add(shard_id)

            for right_group in groups[left_index + 1:]:
                pair = tuple(sorted((left_group, right_group)))
                edge_counts[pair] += 1

    groups_payload: list[dict[str, Any]] = []
    for group_id, card in group_acc.items():
        representative_rows = sorted(
            (dict(row) for row in card["representative_shards"]),
            key=lambda row: row.get("_priority"),
        )[:5]
        for row in representative_rows:
            row.pop("_priority", None)

        paragraph_ids_sorted = sorted(
            list(card["paragraph_ids"]),
            key=lambda paragraph_id: _para_line_key(paragraphs_by_id.get(paragraph_id, {"id": paragraph_id})),
        )
        section_cards: list[dict[str, Any]] = []
        for section_id, count in card["section_counts"].most_common(5):
            section = sections_by_id.get(section_id) or {}
            section_cards.append(
                {
                    "section_id": section_id,
                    "section_path": _string(section.get("path")),
                    "heading": _string(section.get("heading")),
                    "paragraph_count": count,
                }
            )
        target_cards_top = []
        for key, count in card["target_counts"].most_common(6):
            meta = card["target_meta"].get(key) or {}
            target_cards_top.append(
                {
                    "key": key,
                    "kind": _string(meta.get("kind")),
                    "id": _string(meta.get("id")),
                    "title": _string(meta.get("title")),
                    "shard_count": count,
                }
            )

        neighbor_groups_top = [
            {
                "group_id": right if left == group_id else left,
                "shared_shard_count": count,
            }
            for (left, right), count in edge_counts.items()
            if group_id in {left, right}
        ]
        neighbor_groups_top.sort(
            key=lambda item: (-int(item.get("shared_shard_count") or 0), _string(item.get("group_id")))
        )

        groups_payload.append(
            {
                "group_id": group_id,
                "title": card["title"] or group_id,
                "gloss": representative_rows[0]["statement"] if representative_rows else "",
                "shard_count": len(card["shard_ids"]),
                "paragraph_count": len(card["paragraph_ids"]),
                "paragraph_ids_top": paragraph_ids_sorted[:8],
                "keyword_hints_top": [keyword for keyword, _count in card["keyword_counts"].most_common(6)],
                "mechanism_hints_top": [mechanism for mechanism, _count in card["mechanism_counts"].most_common(6)],
                "source_sections_top": section_cards,
                "representative_shards": representative_rows,
                "neighbor_groups_top": neighbor_groups_top[:8],
                "target_cards_top": target_cards_top,
                "status_summary": dict(card["status_counts"]),
                "coverage_summary": dict(card["coverage_counts"]),
                "routing_summary": dict(card["routing_counts"]),
            }
        )

    groups_payload.sort(key=lambda item: (-int(item.get("shard_count") or 0), _string(item.get("group_id"))))

    edges_payload = [
        {
            "left_group_id": left,
            "right_group_id": right,
            "shared_shard_count": count,
        }
        for (left, right), count in sorted(edge_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    ]

    paragraph_hubs = []
    for paragraph_id, card in paragraph_acc.items():
        if len(card["group_ids"]) <= 1 and len(card["shard_ids"]) <= 1:
            continue
        paragraph_hubs.append(
            {
                "paragraph_id": paragraph_id,
                "group_count": len(card["group_ids"]),
                "shard_count": len(card["shard_ids"]),
                "group_ids": sorted(card["group_ids"]),
                "section_id": _string(card.get("section_id")),
                "section_path": _string(card.get("section_path")),
                "section_heading": _string(card.get("section_heading")),
                "summary": _string(card.get("summary")),
                "_sort": (
                    -len(card["group_ids"]),
                    -len(card["shard_ids"]),
                    int(card.get("line_start") or 0),
                    paragraph_id,
                ),
            }
        )
    paragraph_hubs.sort(key=lambda item: item.get("_sort"))
    for item in paragraph_hubs:
        item.pop("_sort", None)

    target_cards_payload = []
    for key, target in target_acc.items():
        target_cards_payload.append(
            {
                "key": key,
                "kind": _string(target.get("kind")),
                "id": _string(target.get("id")),
                "title": _string(target.get("title")),
                "group_ids": sorted(target["group_ids"]),
                "group_count": len(target["group_ids"]),
                "paragraph_count": len(target["paragraph_ids"]),
                "shard_count": len(target["shard_ids"]),
            }
        )
    target_cards_payload.sort(
        key=lambda item: (
            -int(item.get("group_count") or 0),
            -int(item.get("shard_count") or 0),
            _string(item.get("key")),
        )
    )

    return {
        "kind": "raw_seed_navigation_graph",
        "schema_version": RAW_SEED_NAVIGATION_GRAPH_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "family_id": _string(payload.get("family_id")),
        "family_number": _string(payload.get("family_number")),
        "source": {
            "raw_seed_json_path": _string(payload.get("raw_seed_json_path"))
            or raw_seed_json_path_for_family(_string(payload.get("family_dir"))),
            "raw_seed_markdown_path": raw_seed_markdown_path_for_family(_string(payload.get("family_dir"))),
            "raw_seed_index_path": raw_seed_index_path_for_family(_string(payload.get("family_dir"))),
            "shard_surface_path": _string(shard_surface_path),
            "shard_surface_kind": _string(shard_surface_kind),
            "registry_updated_at": _string(payload.get("updated_at")),
        },
        "counts": {
            "total_groups": len(groups_payload),
            "total_edges": len(edges_payload),
            "total_paragraph_hubs": len(paragraph_hubs),
            "total_target_cards": len(target_cards_payload),
            "total_shards_considered": shards_considered,
            "total_group_memberships": group_memberships,
        },
        "groups": groups_payload,
        "edges": edges_payload,
        "paragraph_hubs": paragraph_hubs[:120],
        "target_cards": target_cards_payload[:120],
        "indexes": {
            "group_id_to_neighbor_ids": {
                item["group_id"]: [neighbor["group_id"] for neighbor in item["neighbor_groups_top"]]
                for item in groups_payload
            },
            "paragraph_id_to_group_ids": {
                paragraph_id: sorted(card["group_ids"])
                for paragraph_id, card in sorted(paragraph_acc.items())
                if card["group_ids"]
            },
            "target_key_to_group_ids": {
                item["key"]: item["group_ids"]
                for item in target_cards_payload
            },
        },
    }


def project_raw_seed_index_slice(
    index: Mapping[str, Any],
    *,
    source: str | None = None,
    tag: str | None = None,
    idea_group: str | None = None,
    mechanism: str | None = None,
    keyword: str | None = None,
    section: str | None = None,
    route: str | None = None,
    paragraph: str | None = None,
    diagnostics: bool = False,
    limit: int = 12,
    paragraphs_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    sections_by_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Project one bounded JSON slice from the raw-seed navigation index for kernel queries.
    - Mechanism: Resolve the requested source/tag/group/mechanism/keyword/section/route/paragraph selector, limit ids, and emit the matching cards and paragraph stubs.
    - Guarantee: Returns a small dict view without dumping the full inverted indexes.
    - Fails: None.
    - When-needed: Open when a kernel raw-seed query needs the bounded slice logic instead of the full index payload.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_index; system/lib/kernel_nav_lens.py
    - Navigation-group: kernel_lib
    """
    indexes = dict(index.get("indexes") or {})
    sources_lookup = {
        _string(source_card.get("id")): dict(source_card)
        for source_card in index.get("sources", [])
        if isinstance(source_card, Mapping) and _string(source_card.get("id"))
    }
    themes = dict(index.get("themes") or {})
    routes_payload = dict(index.get("routes") or {})
    route_lookup = {
        _string(route_card.get("id")): dict(route_card)
        for route_card in routes_payload.get("claim_routes_top", [])
        if isinstance(route_card, Mapping) and _string(route_card.get("id"))
    }
    diagnostics_payload = dict(index.get("diagnostics") or {})
    sections_lookup = {
        _string(section_card.get("id")): dict(section_card)
        for section_card in index.get("sections_toc", [])
        if isinstance(section_card, Mapping) and _string(section_card.get("id"))
    }
    ordered_section_ids = [
        _string(section_card.get("id"))
        for section_card in sorted(
            sections_lookup.values(),
            key=lambda item: (int(item.get("line_start") or 0), _string(item.get("id"))),
        )
    ]
    incoming_map: dict[str, list[str]] = defaultdict(list)
    if paragraphs_by_id:
        for paragraph_id, paragraph_payload in paragraphs_by_id.items():
            related_ids = (
                _dedupe_strings([_string(item) for item in paragraph_payload.get("related_paragraph_ids", [])])
                if isinstance(paragraph_payload.get("related_paragraph_ids"), list)
                else []
            )
            for related_id in related_ids:
                incoming_map[related_id].append(paragraph_id)
        for bucket in incoming_map.values():
            if paragraphs_by_id:
                bucket.sort(key=lambda item: _para_line_key(paragraphs_by_id.get(item, {"id": item})))
    source_q = _string(source)
    tag_q = _string(tag).casefold()
    group_q = _string(idea_group).casefold()
    mech_q = _string(mechanism).casefold()
    kw_q = _string(keyword).casefold()
    section_q = _string(section)
    route_q = _string(route)
    paragraph_q = _string(paragraph)
    max_items = max(0, int(limit or 0))
    route_map = {
        _string(route_id): _dedupe_strings(list(ids))
        for route_id, ids in (indexes.get("route_id_to_paragraph_ids") or {}).items()
        if _string(route_id)
    }
    section_map = {
        _string(section_id): _dedupe_strings(list(ids))
        for section_id, ids in (indexes.get("section_id_to_paragraph_ids") or {}).items()
        if _string(section_id)
    }
    source_map = {
        _string(source_id): _dedupe_strings(list(ids))
        for source_id, ids in (indexes.get("source_id_to_paragraph_ids") or {}).items()
        if _string(source_id)
    }
    section_to_source = {
        _string(section_id): _string(source_id)
        for section_id, source_id in (indexes.get("section_id_to_source_id") or {}).items()
        if _string(section_id) and _string(source_id)
    }

    def _limit_ids(ids: list[str]) -> list[str]:
        deduped = _dedupe_strings(ids)
        return deduped if max_items <= 0 else deduped[:max_items]

    def _paragraph_stubs(ids: list[str]) -> list[dict[str, Any]]:
        if not paragraphs_by_id:
            return [{"id": pid} for pid in _limit_ids(ids)]
        output: list[dict[str, Any]] = []
        for pid in _limit_ids(ids):
            paragraph_payload = paragraphs_by_id.get(pid)
            if not isinstance(paragraph_payload, Mapping):
                output.append({"id": pid})
                continue
            section_id = _string(paragraph_payload.get("section_id"))
            section_heading = ""
            if sections_by_id and section_id in sections_by_id:
                section_heading = _string(sections_by_id[section_id].get("heading"))
            output.append(
                _paragraph_stub(
                    paragraph_payload,
                    section_heading=section_heading,
                    incoming_related_ids=incoming_map.get(pid, []),
                )
            )
        return output

    def _section_cards(section_ids: list[str]) -> list[dict[str, Any]]:
        return [
            dict(sections_lookup.get(section_id) or {})
            for section_id in _limit_ids(section_ids)
            if _string(section_id) in sections_lookup
        ]

    def _match_source_card(token: str) -> tuple[str | None, dict[str, Any] | None]:
        normalized = _plain_text(token).casefold()
        for source_id, source_card in sources_lookup.items():
            if token in {
                _string(source_card.get("id")),
                _string(source_card.get("path")),
                _string(source_card.get("heading_slug")),
            } or _plain_text(source_card.get("heading")).casefold() == normalized:
                return source_id, dict(source_card)
        return None, None

    def _match_route_card(token: str) -> tuple[str | None, dict[str, Any] | None]:
        normalized = _plain_text(token).casefold()
        for route_id, route_card in route_lookup.items():
            if token == _string(route_card.get("id")) or _plain_text(route_card.get("summary")).casefold() == normalized:
                return route_id, dict(route_card)
        return None, None

    def _route_cards_for_ids(paragraph_ids: list[str], *, limit_items: int = 4) -> list[dict[str, Any]]:
        selected = set(_dedupe_strings(paragraph_ids))
        scored: list[tuple[int, int, str, dict[str, Any]]] = []
        for route_id, route_paragraph_ids in route_map.items():
            matched = [pid for pid in route_paragraph_ids if pid in selected]
            if not matched:
                continue
            route_card = dict(route_lookup.get(route_id) or {"id": route_id})
            route_card["matched_paragraph_count"] = len(matched)
            scored.append(
                (
                    -len(matched),
                    -int(route_card.get("paragraph_count") or 0),
                    route_id,
                    route_card,
                )
            )
        scored.sort()
        limit_size = max_items if limit_items <= 0 else limit_items
        return [item[-1] for item in scored[:limit_size]]

    def _local_section_neighbors(paragraph_id: str, *, window: int = 2) -> dict[str, list[dict[str, Any]]]:
        if not paragraphs_by_id:
            return {"previous": [], "next": []}
        paragraph_payload = paragraphs_by_id.get(paragraph_id)
        if not isinstance(paragraph_payload, Mapping):
            return {"previous": [], "next": []}
        section_id = _string(paragraph_payload.get("section_id"))
        ordered_ids = section_map.get(section_id, [])
        if paragraph_id not in ordered_ids:
            return {"previous": [], "next": []}
        idx = ordered_ids.index(paragraph_id)
        previous_ids = ordered_ids[max(0, idx - window):idx]
        next_ids = ordered_ids[idx + 1:idx + 1 + window]
        return {
            "previous": _paragraph_stubs(previous_ids),
            "next": _paragraph_stubs(next_ids),
        }

    def _thematic_neighbors(paragraph_id: str) -> list[dict[str, Any]]:
        if not paragraphs_by_id:
            return []
        current = paragraphs_by_id.get(paragraph_id)
        if not isinstance(current, Mapping):
            return []
        current_tags = set(_dedupe_strings([_string(tag) for tag in current.get("tags", [])])) if isinstance(current.get("tags"), list) else set()
        current_groups = set(_dedupe_strings([_string(group) for group in current.get("idea_group_ids", [])])) if isinstance(current.get("idea_group_ids"), list) else set()
        current_mechanisms = set(_dedupe_strings([_string(item) for item in current.get("mechanism_hints", [])])) if isinstance(current.get("mechanism_hints"), list) else set()
        current_section_id = _string(current.get("section_id"))
        current_source_id = section_to_source.get(current_section_id, "")
        related = set(_dedupe_strings([_string(item) for item in current.get("related_paragraph_ids", [])])) if isinstance(current.get("related_paragraph_ids"), list) else set()
        related.update(incoming_map.get(paragraph_id, []))
        scored: list[tuple[int, int, str, dict[str, Any]]] = []
        for other_id, other in paragraphs_by_id.items():
            if other_id == paragraph_id or other_id in related:
                continue
            other_tags = set(_dedupe_strings([_string(tag) for tag in other.get("tags", [])])) if isinstance(other.get("tags"), list) else set()
            other_groups = set(_dedupe_strings([_string(group) for group in other.get("idea_group_ids", [])])) if isinstance(other.get("idea_group_ids"), list) else set()
            other_mechanisms = set(_dedupe_strings([_string(item) for item in other.get("mechanism_hints", [])])) if isinstance(other.get("mechanism_hints"), list) else set()
            shared_tags = sorted(current_tags & other_tags)
            shared_groups = sorted(current_groups & other_groups)
            shared_mechanisms = sorted(current_mechanisms & other_mechanisms)
            score = len(shared_groups) * 4 + len(shared_tags) * 2 + len(shared_mechanisms)
            if current_source_id and section_to_source.get(_string(other.get("section_id")), "") == current_source_id:
                score += 1
            if score <= 0:
                continue
            stub = _paragraph_stub(
                other,
                section_heading=_string((sections_by_id or {}).get(_string(other.get("section_id")), {}).get("heading")),
                incoming_related_ids=incoming_map.get(other_id, []),
            )
            stub["shared_tags"] = shared_tags[:6]
            stub["shared_idea_groups"] = shared_groups[:6]
            stub["shared_mechanism_hints"] = shared_mechanisms[:6]
            stub["thematic_score"] = score
            scored.append(
                (
                    -score,
                    int(other.get("line_start") or 0),
                    other_id,
                    stub,
                )
            )
        scored.sort()
        return [item[-1] for item in scored[: max_items or 12]]

    def _section_neighbors(section_id: str, *, window: int = 2) -> dict[str, list[dict[str, Any]]]:
        if section_id not in ordered_section_ids:
            return {"previous": [], "next": []}
        idx = ordered_section_ids.index(section_id)
        previous_ids = ordered_section_ids[max(0, idx - window):idx]
        next_ids = ordered_section_ids[idx + 1:idx + 1 + window]
        return {
            "previous": _section_cards(previous_ids),
            "next": _section_cards(next_ids),
        }

    mode = "all"
    matched_key: str | None = None
    selected_ids: list[str] | None = None
    card: dict[str, Any] | None = None
    match_count = 0
    if source_q:
        mode = "source"
        token = source_q
        if token.startswith("source:"):
            token = token.split(":", 1)[1].strip()
        matched_key, card = _match_source_card(token)
        selected_ids = list(source_map.get(matched_key or "", [])) if matched_key else []
    elif tag_q:
        mode = "tag"
        tag_map = indexes.get("tag_to_paragraph_ids") or {}
        matched_key = next((k for k in tag_map if k.casefold() == tag_q), None)
        selected_ids = list(tag_map.get(matched_key or "", [])) if matched_key else []
        card = next(
            (
                dict(item)
                for item in themes.get("tags", [])
                if isinstance(item, Mapping) and _string(item.get("tag")).casefold() == tag_q
            ),
            None,
        )
    elif group_q:
        mode = "idea_group"
        grp_map = indexes.get("idea_group_to_paragraph_ids") or {}
        matched_key = next((k for k in grp_map if k.casefold() == group_q), None)
        selected_ids = list(grp_map.get(matched_key or "", [])) if matched_key else []
        card = next(
            (
                dict(item)
                for item in themes.get("idea_groups", [])
                if isinstance(item, Mapping) and _string(item.get("id")).casefold() == group_q
            ),
            None,
        )
    elif mech_q:
        mode = "mechanism_hint"
        mech_map = indexes.get("mechanism_hint_to_paragraph_ids") or {}
        matched_key = next((k for k in mech_map if k.casefold() == mech_q), None)
        selected_ids = list(mech_map.get(matched_key or "", [])) if matched_key else []
        card = next(
            (
                dict(item)
                for item in themes.get("mechanism_hints", [])
                if isinstance(item, Mapping) and _string(item.get("mechanism_hint")).casefold() == mech_q
            ),
            None,
        )
    elif kw_q:
        mode = "keyword_hint"
        kw_map = indexes.get("keyword_hint_to_paragraph_ids") or {}
        matched_key = next((k for k in kw_map if k.casefold() == kw_q), None)
        selected_ids = list(kw_map.get(matched_key or "", [])) if matched_key else []
        card = next(
            (
                dict(item)
                for item in themes.get("keyword_hints", [])
                if isinstance(item, Mapping) and _string(item.get("keyword_hint")).casefold() == kw_q
            ),
            None,
        )
    elif section_q:
        mode = "section"
        token = section_q
        if token.startswith("section:"):
            token = token.split(":", 1)[1].strip()
        elif token.startswith("path:"):
            token = token.split(":", 1)[1].strip()
        normalized = _plain_text(token).casefold()
        matched_key = next(
            (
                key
                for key, section_card in sections_lookup.items()
                if token in {
                    _string(section_card.get("id")),
                    _string(section_card.get("path")),
                    _string(section_card.get("heading_slug")),
                }
                or _plain_text(section_card.get("heading")).casefold() == normalized
            ),
            None,
        )
        card = dict(sections_lookup.get(matched_key or "") or {})
        if matched_key and paragraphs_by_id:
            selected_ids = list(section_map.get(matched_key, []))
        else:
            selected_ids = list(card.get("representative_paragraph_ids", [])) if matched_key else []
    elif route_q:
        mode = "route"
        token = route_q
        if token.startswith("route:"):
            token = token.split(":", 1)[1].strip()
        matched_key, card = _match_route_card(token)
        selected_ids = list(route_map.get(matched_key or "", [])) if matched_key else []
    elif paragraph_q:
        mode = "paragraph"
        token = paragraph_q
        if token.startswith("paragraph:"):
            token = token.split(":", 1)[1].strip()
        matched_key = token if paragraphs_by_id and token in paragraphs_by_id else None
    elif diagnostics:
        mode = "diagnostics"

    if mode == "diagnostics":
        return {
            "kind": "raw_seed_index_slice",
            "mode": mode,
            "matched_key": None,
            "diagnostics": {
                "top_paragraph_hubs": diagnostics_payload.get("top_paragraph_hubs", [])[: max_items or 12],
                "duplicate_summary_clusters_top": diagnostics_payload.get("duplicate_summary_clusters_top", [])[: max_items or 12],
                "section_duplicate_pressure_top": diagnostics_payload.get("section_duplicate_pressure_top", [])[: max_items or 12],
                "fragment_heavy_sections_top": diagnostics_payload.get("fragment_heavy_sections_top", [])[: max_items or 12],
                "sections_without_related_sections": diagnostics_payload.get("sections_without_related_sections", []),
            },
        }

    if mode == "paragraph":
        if not matched_key or not paragraphs_by_id or matched_key not in paragraphs_by_id:
            return {"kind": "raw_seed_index_slice", "mode": mode, "matched_key": None}
        paragraph_payload = paragraphs_by_id[matched_key]
        section_id = _string(paragraph_payload.get("section_id"))
        section_heading = _string((sections_by_id or {}).get(section_id, {}).get("heading"))
        outgoing_ids = (
            _dedupe_strings([_string(item) for item in paragraph_payload.get("related_paragraph_ids", [])])
            if isinstance(paragraph_payload.get("related_paragraph_ids"), list)
            else []
        )
        incoming_ids = _dedupe_strings(incoming_map.get(matched_key, []))
        source_id = section_to_source.get(section_id, "")
        return {
            "kind": "raw_seed_index_slice",
            "mode": mode,
            "matched_key": matched_key,
            "paragraph": _paragraph_stub(
                paragraph_payload,
                section_heading=section_heading,
                incoming_related_ids=incoming_ids,
            ),
            "section": dict(sections_lookup.get(section_id) or {}),
            "source": dict(sources_lookup.get(source_id) or {}),
            "claim_routes": _route_cards_for_ids([matched_key], limit_items=3),
            "related_paragraphs": _paragraph_stubs(outgoing_ids),
            "incoming_related_paragraphs": _paragraph_stubs(incoming_ids),
            "local_section_neighbors": _local_section_neighbors(matched_key),
            "thematic_neighbors": _thematic_neighbors(matched_key),
            "additional_related_paragraphs": max(0, len(outgoing_ids) - len(_limit_ids(outgoing_ids))),
            "additional_incoming_related_paragraphs": max(0, len(incoming_ids) - len(_limit_ids(incoming_ids))),
        }

    if selected_ids is None:
        return {"kind": "raw_seed_index_slice", "mode": mode, "matched_key": None}

    match_count = len(selected_ids)
    preferred_ids: list[str] = []
    if isinstance(card, Mapping):
        preferred_ids = _dedupe_strings([_string(item) for item in card.get("representative_paragraph_ids", [])])
    paragraph_ids = _dedupe_strings(preferred_ids + list(selected_ids))
    paragraph_stubs = _paragraph_stubs(paragraph_ids)
    related_section_ids = []
    if isinstance(card, Mapping):
        related_section_ids = _dedupe_strings([_string(item) for item in card.get("related_section_ids", [])])
    extra_section_ids: list[str] = []
    if mode == "source":
        extra_section_ids = _dedupe_strings(
            [*_dedupe_strings([_string(item) for item in card.get("representative_section_ids", [])]), *[
                _string(item.get("section_id"))
                for item in card.get("source_sections", [])
                if isinstance(item, Mapping) and _string(item.get("section_id"))
            ]]
        )
    elif mode == "route":
        extra_section_ids = _dedupe_strings(
            [
                _string(item.get("section_id"))
                for item in card.get("top_sections", [])
                if isinstance(item, Mapping) and _string(item.get("section_id"))
            ]
        )
    elif mode in {"tag", "idea_group", "mechanism_hint", "keyword_hint"}:
        extra_section_ids = _dedupe_strings(
            [
                _string(item.get("section_id"))
                for item in card.get("top_sections", [])
                if isinstance(item, Mapping) and _string(item.get("section_id"))
            ]
        )
    source_id = ""
    if mode == "source":
        source_id = matched_key or ""
    elif isinstance(card, Mapping):
        source_id = _string(card.get("source_id"))
    sections_block = _section_cards(extra_section_ids)

    return {
        "kind": "raw_seed_index_slice",
        "mode": mode,
        "matched_key": matched_key,
        "match_count": match_count,
        "card": card or {},
        "source": dict(sources_lookup.get(source_id) or {}),
        "paragraph_stubs": paragraph_stubs,
        "sections": sections_block,
        "claim_routes": _route_cards_for_ids(selected_ids, limit_items=4),
        "additional_matches": max(0, match_count - len(_limit_ids(paragraph_ids))),
        "related_sections": _section_cards(related_section_ids),
        "section_neighbors": _section_neighbors(_string(card.get("id")) if mode == "section" and isinstance(card, Mapping) else ""),
    }


def annotate_raw_seed_payload(
    payload: Mapping[str, Any],
    ref: str,
    field: str,
    value: str,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Return a copy of a raw-seed registry payload with one annotation field updated on the target section or paragraph.
    - Guarantee: Returns the updated payload dict; list fields are appended (deduped), string fields are overwritten.
    - Fails: Raises ValueError for unknown fields, unresolvable refs, or mismatched field/target-kind combinations.
    - When-needed: Open when a raw-seed section or paragraph annotation must be applied deterministically without editing markdown directly.
    - Escalates-to: system/lib/raw_seed_registry.py::resolve_raw_seed_ref; system/lib/raw_seed_registry.py::render_raw_seed_markdown
    """
    PARAGRAPH_STRING_FIELDS = {"summary", "note"}
    PARAGRAPH_LIST_FIELDS = {"tags", "idea_group_ids", "related_paragraph_ids"}
    SECTION_STRING_FIELDS = {"note", "fill.purpose"}
    SECTION_LIST_FIELDS = {"aliases", "tags", "fill.grouping_hints", "fill.related_section_ids"}
    ALL_VALID = PARAGRAPH_STRING_FIELDS | PARAGRAPH_LIST_FIELDS | SECTION_STRING_FIELDS | SECTION_LIST_FIELDS

    if field not in ALL_VALID:
        raise ValueError(
            f"Unknown annotation field '{field}'. "
            f"Valid fields: {', '.join(sorted(ALL_VALID))}"
        )

    resolved = resolve_raw_seed_ref(payload, ref)
    if resolved is None:
        raise ValueError(f"Could not resolve raw seed ref: {ref!r}")

    target_kind = resolved["target_kind"]
    target = resolved["target"]
    target_id = _string(target.get("id"))

    updated = dict(payload)
    updated["updated_at"] = _utc_now()

    if target_kind == "paragraph":
        if field not in PARAGRAPH_STRING_FIELDS | PARAGRAPH_LIST_FIELDS:
            raise ValueError(f"Field '{field}' is not valid for a paragraph target.")
        updated["paragraphs"] = [
            dict(item) for item in payload.get("paragraphs", []) if isinstance(item, Mapping)
        ]
        for p in updated["paragraphs"]:
            if _string(p.get("id")) != target_id:
                continue
            if field in PARAGRAPH_STRING_FIELDS:
                p[field] = value
            else:
                existing = _dedupe_strings([_string(x) for x in p.get(field, [])])
                if value not in existing:
                    existing.append(value)
                p[field] = existing
            break
        else:
            raise ValueError(f"Paragraph id not found after resolving ref: {target_id!r}")

    elif target_kind == "section":
        if field not in SECTION_STRING_FIELDS | SECTION_LIST_FIELDS:
            raise ValueError(f"Field '{field}' is not valid for a section target.")
        updated["sections"] = [
            dict(item) for item in payload.get("sections", []) if isinstance(item, Mapping)
        ]
        for s in updated["sections"]:
            if _string(s.get("id")) != target_id:
                continue
            if field == "note":
                s["note"] = value
            elif field == "fill.purpose":
                fill = dict(s.get("fill") or {})
                fill["purpose"] = value
                s["fill"] = fill
            elif field == "fill.grouping_hints":
                fill = dict(s.get("fill") or {})
                existing = _dedupe_strings([_string(x) for x in fill.get("grouping_hints", [])])
                if value not in existing:
                    existing.append(value)
                fill["grouping_hints"] = existing
                s["fill"] = fill
            elif field == "fill.related_section_ids":
                fill = dict(s.get("fill") or {})
                existing = _dedupe_strings([_string(x) for x in fill.get("related_section_ids", [])])
                if value not in existing:
                    existing.append(value)
                fill["related_section_ids"] = existing
                s["fill"] = fill
            elif field in {"aliases", "tags"}:
                existing = _dedupe_strings([_string(x) for x in s.get(field, [])])
                if value not in existing:
                    existing.append(value)
                s[field] = existing
            break
        else:
            raise ValueError(f"Section id not found after resolving ref: {target_id!r}")

    else:
        raise ValueError(f"Cannot annotate target_kind '{target_kind}'; only 'paragraph' and 'section' are supported.")

    return updated


def render_raw_seed_markdown(payload: Mapping[str, Any], *, substrate: str = "raw_seed") -> str:
    """[ACTION]
    - Teleology: Render the registry payload back into its marker-preserving raw_seed markdown projection.
    - Mechanism: Rebuild frontmatter, section markers, paragraph markers, and paragraph bodies from the structured payload using markdown routing helpers.
    - Guarantee: Returns a markdown document string suitable for writing back to raw_seed.md.
    - Fails: None.
    - When-needed: Open when a structured raw-seed payload needs to be projected back to markdown after annotations or sync work.
    - Escalates-to: system/lib/markdown_routing.py; system/lib/raw_seed_registry.py::annotate_raw_seed_payload
    """
    profile = substrate_profile(substrate)
    frontmatter = dict((payload.get("document") or {}).get("frontmatter") or {})
    sections = [dict(item) for item in payload.get("sections", []) if isinstance(item, Mapping)]
    paragraphs = {
        _string(item.get("id")): dict(item)
        for item in payload.get("paragraphs", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    }
    body_lines = [
        (
            f"<!-- {_string(profile.get('sync_marker'))}: generated from "
            f"{_string(profile.get('json_filename'))}; append freely, then rerun "
            f"`kernel.py --sync-{_string(profile.get('substrate')).replace('_', '-')}` to preserve and re-wrap. -->"
        ),
        "",
    ]
    framework_usage = payload.get("framework_usage") if isinstance(payload.get("framework_usage"), Mapping) else {}
    artifact_usage = framework_usage.get("artifact_usage", []) if isinstance(framework_usage, Mapping) else []
    for artifact in artifact_usage:
        if not isinstance(artifact, Mapping):
            continue
        body_lines.append(
            f"<!-- {_string(profile.get('usage_marker'))} "
            + json.dumps(
                {
                    "artifact_path": _string(artifact.get("artifact_path")),
                    "artifact_kind": _string(artifact.get("artifact_kind")),
                    "role": _string(artifact.get("role")),
                    "authority_level": _string(artifact.get("authority_level")),
                    "paired_artifact_path": _string(artifact.get("paired_artifact_path")),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + " -->"
        )
        for rule in artifact.get("operating_rules", []):
            body_lines.append(
                f"<!-- {_string(profile.get('usage_rule_marker'))} "
                + json.dumps(
                    {
                        "artifact_path": _string(artifact.get("artifact_path")),
                        "rule": _string(rule),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + " -->"
            )
        for doc in artifact.get("documentation", []):
            if not isinstance(doc, Mapping):
                continue
            body_lines.append(
                f"<!-- {_string(profile.get('usage_doc_marker'))} {json.dumps(dict(doc), ensure_ascii=False, sort_keys=True)} -->"
            )
        for skill in artifact.get("skills", []):
            if not isinstance(skill, Mapping):
                continue
            body_lines.append(
                f"<!-- {_string(profile.get('usage_skill_marker'))} {json.dumps(dict(skill), ensure_ascii=False, sort_keys=True)} -->"
            )
        for command in artifact.get("commands", []):
            if not isinstance(command, Mapping):
                continue
            body_lines.append(
                f"<!-- {_string(profile.get('usage_command_marker'))} {json.dumps(dict(command), ensure_ascii=False, sort_keys=True)} -->"
            )
        body_lines.append("")

    def _append_paragraph_projection(paragraph: Mapping[str, Any]) -> None:
        body_lines.append(_render_paragraph_marker(paragraph, profile=profile))
        body_lines.extend(str(paragraph.get("raw_markdown") or "").splitlines() or [""])
        references = [_string(item) for item in paragraph.get("references", []) if _string(item)]
        if references:
            body_lines.append("")
            body_lines.extend(references)
        body_lines.append("")
        body_lines.append("")

    root_section_id = next(
        (
            _string(section.get("id"))
            for section in sections
            if _string(section.get("path")) == "__root__" or int(section.get("level") or 0) == 0
        ),
        "sec_root",
    )
    root_section = next((item for item in sections if _string(item.get("id")) == root_section_id), None)
    if root_section:
        for paragraph_id in root_section.get("paragraph_ids", []):
            paragraph = paragraphs.get(_string(paragraph_id))
            if not paragraph:
                continue
            _append_paragraph_projection(paragraph)

    for section in sections:
        section_id = _string(section.get("id"))
        if section_id == root_section_id:
            continue
        level = max(1, int(section.get("level") or 1))
        heading = _string(section.get("heading")) or "Untitled"
        body_lines.append(
            (
                f"<!-- {_string(profile.get('section_marker'))} id={section_id} "
                f"path={_string(section.get('path'))} "
                f"lines={int(section.get('line_start') or 0)}-{int(section.get('line_end') or 0)} -->"
            )
        )
        body_lines.append(f"{'#' * level} {heading}")
        body_lines.append("")
        for paragraph_id in section.get("paragraph_ids", []):
            paragraph = paragraphs.get(_string(paragraph_id))
            if not paragraph:
                continue
            _append_paragraph_projection(paragraph)

    return render_markdown_document(frontmatter, "\n".join(body_lines).rstrip() + "\n")


def render_agent_seed_markdown(payload: Mapping[str, Any]) -> str:
    return render_raw_seed_markdown(payload, substrate="agent_seed")


PROJECTION_PROFILES = {
    "holographic": {
        "fields": ["id", "section_path", "summary", "importance", "tags"],
        "description": "id + 1-line summary — smallest useful view (~30KB for 657 paragraphs)",
    },
    "structural": {
        "fields": [
            "id", "section_id", "section_path", "summary", "tags", "importance",
            "importance_rationale", "extraction_status", "doctrine_route_candidates",
            "keyword_hints", "mechanism_hints", "idea_group_ids",
        ],
        "description": "summary + tags + importance + routes — structural navigation view",
    },
    "full": {
        "fields": None,  # all fields
        "description": "everything including plain_text — full substrate export",
    },
    "bridge": {
        "fields": [
            "id", "section_id", "section_path", "summary", "tags", "importance",
            "importance_rationale", "extraction_status", "doctrine_route_candidates",
            "keyword_hints", "mechanism_hints", "idea_group_ids", "principle_backrefs",
        ],
        "description": "structural + doctrine_route_candidates + principle_backrefs — for bridge injection",
    },
}


def project_raw_seed(
    payload: Mapping[str, Any],
    profile: str = "structural",
    importance_min: int | None = None,
    extraction_status: str | None = None,
    principle: str | None = None,
    doctrine_route: str | None = None,
    section: str | None = None,
    limit: int = 0,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Compile a filtered field projection from an enriched raw_seed.json registry.
    - Guarantee: Returns a projection dict (authority level 5) with the requested profile's fields, applied filters, and enrichment coverage stats.
    - Fails: Raises ValueError for unknown profile names.
    - When-needed: Open when a consumer needs a filtered holographic/structural/full/bridge projection from raw_seed.json instead of the full substrate.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload; system/lib/raw_seed_registry.py::build_raw_seed_index; codex/standards/observe_apply/std_raw_seed.md
    - Navigation-group: kernel_lib
    """
    profile_spec = PROJECTION_PROFILES.get(profile)
    if not profile_spec:
        raise ValueError(f"Unknown profile: {profile}. Available: {list(PROJECTION_PROFILES.keys())}")

    paragraphs = payload.get("paragraphs", [])
    selected_fields = profile_spec["fields"]

    # ── Filters ──
    filtered = list(paragraphs)

    if importance_min is not None:
        filtered = [p for p in filtered if (p.get("importance") or 0) >= importance_min]

    if extraction_status:
        filtered = [
            p for p in filtered
            if isinstance(p.get("extraction_status"), dict)
            and p["extraction_status"].get("status") == extraction_status
        ]

    if principle:
        filtered = [
            p for p in filtered
            if any(
                br.get("principle_id") == principle or br.get("principle_slug") == principle
                for br in (p.get("principle_backrefs") or [])
                if isinstance(br, dict)
            )
        ]

    if doctrine_route:
        filtered = [
            p for p in filtered
            if any(
                rc.get("target_kind") == doctrine_route
                for rc in (p.get("doctrine_route_candidates") or [])
                if isinstance(rc, dict)
            )
        ]

    if section:
        filtered = [
            p for p in filtered
            if p.get("section_id") == section or section in (p.get("section_path") or "")
        ]

    if limit > 0:
        filtered = filtered[:limit]

    # ── Project fields ──
    if selected_fields is None:
        projected = [dict(p) for p in filtered]
    else:
        projected = [{k: p.get(k) for k in selected_fields if k in p} for p in filtered]

    # ── Enrichment coverage stats ──
    total = len(paragraphs)
    coverage = {
        "total": total,
        "with_summary": sum(1 for p in paragraphs if p.get("summary")),
        "with_importance": sum(1 for p in paragraphs if p.get("importance") is not None),
        "with_extraction_status": sum(1 for p in paragraphs if p.get("extraction_status")),
        "with_doctrine_routes": sum(1 for p in paragraphs if p.get("doctrine_route_candidates")),
        "with_principle_backrefs": sum(1 for p in paragraphs if p.get("principle_backrefs")),
    }
    importance_dist = Counter()
    extraction_dist = Counter()
    route_dist = Counter()
    for p in paragraphs:
        imp = p.get("importance")
        if imp is not None:
            importance_dist[str(imp)] += 1
        es = p.get("extraction_status")
        if isinstance(es, dict):
            extraction_dist[es.get("status", "unknown")] += 1
        for rc in (p.get("doctrine_route_candidates") or []):
            if isinstance(rc, dict):
                route_dist[rc.get("target_kind", "unknown")] += 1

    coverage["importance_distribution"] = dict(importance_dist)
    coverage["extraction_distribution"] = dict(extraction_dist)
    coverage["doctrine_route_distribution"] = dict(route_dist)

    return {
        "kind": "raw_seed_projection",
        "profile": profile,
        "profile_description": profile_spec["description"],
        "filters": {
            "importance_min": importance_min,
            "extraction_status": extraction_status,
            "principle": principle,
            "doctrine_route": doctrine_route,
            "section": section,
            "limit": limit,
        },
        "matched": len(projected),
        "total": total,
        "enrichment_coverage": coverage,
        "paragraphs": projected,
    }


def _render_paragraph_marker(paragraph: Mapping[str, Any], *, profile: Mapping[str, Any] | None = None) -> str:
    profile = profile or substrate_profile("raw_seed")
    keyword_hints = ",".join([_string(item) for item in paragraph.get("keyword_hints", []) if _string(item)])
    mechanism_hints = ",".join([_string(item) for item in paragraph.get("mechanism_hints", []) if _string(item)])
    parts = [
        f"<!-- {_string(profile.get('paragraph_marker'))}",
        f"id={_string(paragraph.get('id'))}",
        f"section={_string(paragraph.get('section_id'))}",
        f"lines={int(paragraph.get('line_start') or 0)}-{int(paragraph.get('line_end') or 0)}",
        f"keywords={json.dumps(keyword_hints)}",
        f"mechanisms={json.dumps(mechanism_hints)}",
    ]
    if bool(profile.get("supports_authored_by")):
        parts.append(f"authored_by={json.dumps(_string(paragraph.get('authored_by')))}")
        parts.append(f"source_substrate={json.dumps(_string(paragraph.get('source_substrate')))}")
    return " ".join(parts) + " -->"
