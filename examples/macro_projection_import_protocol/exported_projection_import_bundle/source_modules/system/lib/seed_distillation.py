"""
[PURPOSE]
- Teleology: Materialize, run, and assimilate the bridge-first raw-seed
  first-party source-indexing lane so raw-seed paragraphs can become
  higher-fidelity extracted-shard rows without introducing a second backlog
  store. Legacy function and schema names still say "distillation" because
  controller import paths and ledgers depend on them.

[INTERFACE]
- Exports: build_distillation_run_payload, materialize_distillation_mission,
  run_distillation_mission, import_distilled_shards,
  build_contextual_compression_run_payload,
  materialize_contextual_compression_mission,
  run_contextual_compression_mission,
  import_contextual_compression_rows, and resolve_distillation_artifact_path.
- Reads: family raw_seed.json, raw_seed/raw_seed_shards.json,
  raw_seed/raw_seed_principles.json, the existing extracted_shards.json
  backlog, and the authored observe mission pack
  `raw_seed_bridge_distillation`.
- Writes: mission run folders under
  state/meta_missions/raw_seed_bridge_distillation/runs/, observe plans under
  the same run root, bridge dump artifacts via the existing observe runtime,
  extracted_shards.json replacements for touched paragraphs, filtered
  raw_seed_routing_review.json proposals when local fallback shards are
  superseded, and refreshed raw_seed_coverage.json.

[FLOW]
- Select undistilled paragraphs, one focus paragraph per bridge group or a
  packed batch of focus paragraphs, with bounded option-surface context as
  disambiguation only.
- Write packet files, add only family-local context extras, and compile the
  authored mission pack into an ObserveSessionPlan.
- Optionally run the existing observe session runtime.
- Import the resulting synthesis surface back into family extracted_shards.json,
  replacing only prior machine-produced rows for the touched paragraphs.

[CONSTRAINTS]
- No doctrine mutation, routing mutation, or raw_seed.md edits happen here.
- Distillation rows land in family-root extracted_shards.json; no parallel shard
  store is introduced.
- Paragraph provenance stays stable through parent_paragraph_id and
  raw_seed_anchor on every imported row.
"""
from __future__ import annotations

import hashlib
import concurrent.futures
import json
import os
import re
from collections.abc import Iterable as IterableABC
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from system.lib import meta_mission_workspace as _mmw
from system.lib.autonomous_seed import build_autonomous_seed_payload, write_autonomous_seed
from system.lib.dispatch_policy import resolve_dispatch_policy
from system.lib.json_payloads import extract_json_object
from system.lib.markdown_routing import extract_observe_artifact_payload
from system.lib.bridge_routes import merge_bridge_config_with_route
from system.lib.observe_mission_templates import expand_mission_template, load_mission_template
from system.lib.observe_runtime import load_master_config
from system.lib.compression_profiles import (
    RAW_SEED_CONTEXT_PROFILE_ID,
    build_raw_seed_context_contract,
    contextual_row_from_contract,
)
from system.lib.raw_seed_atomization import (
    ATOMIZATION_SOURCE as LOCAL_ATOMIZATION_SOURCE,
    DEFAULT_ATOMIZE_SELECTION_MODE,
    SELECTION_MODE_FRESH_FIRST,
    SELECTION_MODE_MIXED,
    SELECTION_MODE_OLDEST_FIRST,
    REPO_ROOT,
    build_raw_seed_coverage,
    family_extracted_shards_path,
    family_raw_seed_coverage_path,
    family_raw_seed_routing_review_path,
)
from system.lib.raw_seed_registry import (
    agent_seed_json_path_for_family,
    build_raw_seed_shards,
    raw_seed_json_path_for_family,
    raw_seed_principles_path_for_family,
    raw_seed_shards_path_for_family,
    raw_seed_workspace_dir_for_family,
)
from system.lib.raw_seed_distillation_validator import (
    ValidatorResult,
    validate_distillation_bundle,
)
from system.lib.shard_browser import _browser_index_for_shards
from tools.meta.apply.observe_session_runner import run_session_once

MISSION_ID = "raw_seed_bridge_distillation"
CONTEXTUAL_MISSION_ID = "raw_seed_contextual_compression"
DISTILLATION_SOURCE = "raw_seed_distillation_bridge_v1"
CONTEXTUAL_COMPRESSION_SOURCE = "raw_seed_contextual_compression_bridge_v1"
DISTILLATION_SUBAGENT_SOURCE = "raw_seed_distillation_subagent_sonnet_v1"
DISTILLATION_OPUS_SEED_SOURCE = "raw_seed_distillation_opus_seed_v1"
DEFAULT_OUTPUT_ROOT = "state/meta_missions/raw_seed_bridge_distillation/runs"
DEFAULT_CONTEXTUAL_OUTPUT_ROOT = "state/meta_missions/raw_seed_contextual_compression/runs"
DEFAULT_DUMP_ROOT = "tools/meta/apply/observe_dumps"
DEFAULT_CONTEXT_WINDOW = 1
OPTIONAL_EXAMPLES_FILENAME = "raw_seed_distillation_examples.jsonl"
OPTION_SURFACE_CONTEXT_CAP = 8
# Sources that a fresh distillation run may overwrite in extracted_shards.json.
# Opus seed is intentionally NOT here — cheap-lane re-runs must not silently overwrite
# the canonical exemplar versions. To re-seed, run the explicit Opus path.
REPLACEABLE_ATOMIZATION_SOURCES = {
    "",
    LOCAL_ATOMIZATION_SOURCE,
    DISTILLATION_SOURCE,
    DISTILLATION_SUBAGENT_SOURCE,
}
LOWER_BRACKET_SHARD_PACKET_LIMIT = 40
PROVIDER_REVIEW_NOTICE = (
    "Provider review notice: this is an authorized first-party private-project "
    "documentation/indexing task over owner-authored raw notes from this repository. "
    "It is not model extraction, third-party corpus extraction, credential collection, "
    "or policy evasion. The worker sees bounded packet files plus injected local "
    "skill/context files and returns JSON rows only. Local controller import is "
    "schema-validated; valid rows are received as evidence, invalid boundary rows "
    "are quarantined, and doctrine apply remains gated. No provider output can "
    "directly mutate the repository. If this request needs human review, use "
    "account/support metadata rather than asking the model to infer identity."
)
LEGACY_SCHEMA_NOTICE = (
    "Compatibility note: local schema fields may still use legacy names such as "
    "shards or distillation_confidence; provider-facing semantics are first-party "
    "source-index rows over owner-authored notes."
)


def _seed_json_path_for_substrate(family_dir: str, *, substrate: str) -> str:
    return (
        raw_seed_json_path_for_family(family_dir)
        if substrate == "raw_seed"
        else agent_seed_json_path_for_family(family_dir)
    )


def _seed_shards_payload_for_substrate(
    *,
    repo_root: Path,
    family_dir: str,
    substrate: str,
    raw_seed_payload: Mapping[str, Any],
) -> dict[str, Any]:
    if substrate == "raw_seed":
        return _load_json(repo_root / raw_seed_shards_path_for_family(family_dir)) or {
            "shards": []
        }
    return build_raw_seed_shards(raw_seed_payload)
DEFAULT_COHORT_SIZE = 12
DEFAULT_WAVE_WIDTH = "auto"
# How many focus paragraphs to pack into a single bridge packet. ChatGPT Pro's
# rate limiter is count-and-burst shaped (not byte-shaped) — packing more
# paragraphs per probe trades bridge round-trips for fewer, fatter prompts.
# With a ~139k-char skill bundle and ~300-9000 chars per paragraph card,
# bin-packing (FFD) fits 5-40 paragraphs per probe depending on mix.
# Set to 1 for the classic one-paragraph-per-probe shape. Any value > 1
# engages bin-packing mode which ignores this exact number and uses
# PARAGRAPH_BUDGET_PER_PROBE_CHARS as the true packing constraint.
DEFAULT_PARAGRAPHS_PER_PROBE = 6
# Bin-packing model (empirical, 2026-04-17 measurements on Family 09).
#
# Actual observed dump structure (production, 2026-04-17):
#   dump_file = {__reading_guide + __meta + __toc + __context + observations}
#     __reading_guide       ~313 chars
#     __meta              ~14,958 chars (group meta, prompt contract, toc)
#     __toc                  ~447 chars
#     __context          ~168,770 chars (the 5 skill/context files embedded)
#     observations (packet)    X chars
#   + bridge prompt wrapper (~8-12k: question + acceptance + response_schema + constraints)
#   Total now targets the ChatGPT Pro Thinking ceiling through
#   provider_capabilities chatgpt runtime_prompt_budget_chars (~800k chars).
#   Input budget is no longer the first constraint for many batches; response
#   JSON reliability and shard-count explosion are still real constraints.
#
# 2026-04-18 REVISION v3: with 20 paragraphs in one probe, ChatGPT started
# producing invalid JSON — unescaped inner quotes in long string fields
# (clarified_statement, voice_anchor) triggered json.JSONDecodeError at
# arbitrary offsets in the response. Capping paragraphs per probe reduces
# the response surface area and makes well-formed JSON more reliable.
#
# 10 paragraphs × 2-3 shards × ~400 chars = ~10k response — within the
# range where ChatGPT consistently emits syntactically valid JSON.
PARAGRAPH_BUDGET_PER_PROBE_CHARS = 30000
# Per-paragraph JSON card overhead — includes JSON indent whitespace.
PARAGRAPH_CARD_OVERHEAD_CHARS = 1200
# Sanity cap on paragraphs per probe. The three-tier salvage (strict json
# → escape-repair → field extraction) recovers shards from malformed
# responses, so the old 10-cap set to avoid JSON errors can be raised.
# 15 balances probe count (fewer bridge round-trips) vs response size
# (ChatGPT's JSON reliability drops sharply above ~20 shards per reply).
MAX_PARAGRAPHS_PER_PROBE = 15
VALID_SELECTION_MODES = {
    SELECTION_MODE_FRESH_FIRST,
    SELECTION_MODE_OLDEST_FIRST,
    SELECTION_MODE_MIXED,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parent_owns_ledger(repo_root: Path, mission_id: str, run_id: str) -> bool:
    """Return True when a parent runner already stamped run.json=running for this run.

    The overnight chain runner stamps start_run before invoking a child, and calls
    finalize_run after the child returns. A standalone runtime must not stamp the
    ledger in that case, or the child's start_run overwrites parent-provided
    chain_ref/parent_run_id fields and the parent's subsequent finalize_run races
    the child's finalize_run. The guard lets both call sites share a helper
    without introducing a parent-signal environment variable.
    """
    run_dir = _mmw.resolve_run_dir(repo_root, mission_id, run_id)
    run_json = run_dir / _mmw.RUN_JSON_NAME
    if not run_json.exists():
        return False
    try:
        payload = json.loads(run_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(payload, dict) and _string(payload.get("status")) == "running"


def _launcher_owns_ledger(run_id: str) -> bool:
    owner = _string(os.environ.get("AIWF_META_MISSION_LIFECYCLE_OWNER")).lower()
    launcher_run_id = _string(os.environ.get("AIWF_META_MISSION_RUN_ID"))
    return owner == "launcher" and launcher_run_id == _string(run_id)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ").lower()


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", _string(text)).strip()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _controller_heartbeat_bundle(
    repo_root: Path,
    *,
    family_dir: str,
) -> dict[str, Any]:
    autonomous_seed = build_autonomous_seed_payload(repo_root, family_dir=family_dir)
    heartbeat = (
        dict(autonomous_seed.get("controller_heartbeat"))
        if isinstance(autonomous_seed.get("controller_heartbeat"), Mapping)
        else {}
    )
    heartbeat_ref = (
        dict(autonomous_seed.get("controller_heartbeat_ref"))
        if isinstance(autonomous_seed.get("controller_heartbeat_ref"), Mapping)
        else {}
    )
    return {
        "autonomous_seed_path": _string(autonomous_seed.get("autonomous_seed_path")),
        "controller_heartbeat": heartbeat,
        "controller_heartbeat_ref": heartbeat_ref,
    }


def _split_balanced_json_objects(text: str, *, target_depth: int = 1) -> list[str]:
    """
    Scan text and return balanced {...} object substrings at a target depth.

    target_depth=1 returns top-level objects (the default for normal JSON).
    target_depth=2 returns objects one level deep — useful for salvaging
    shard objects inside a malformed `{"shards":[{...},{...}]}` outer
    structure where the outer still has balanced braces but contains an
    inner string-escape error. The tracker respects string literals and
    escape sequences so a `"foo \\"bar\\""` inside the payload won't
    confuse the depth counter.
    """
    objects: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
            if depth == target_depth:
                start = i
        elif ch == "}":
            if depth == target_depth and start >= 0:
                objects.append(text[start : i + 1])
                start = -1
            if depth > 0:
                depth -= 1
    return objects


_SHARD_FIELD_PATTERNS = {
    "id": re.compile(r'"id"\s*:\s*"([^"]*?)"\s*[,}]'),
    "parent_paragraph_id": re.compile(r'"parent_paragraph_id"\s*:\s*"([^"]*?)"\s*[,}]'),
    "segment_ordinal": re.compile(r'"segment_ordinal"\s*:\s*"([^"]*?)"\s*[,}]'),
    "raw_seed_anchor": re.compile(r'"raw_seed_anchor"\s*:\s*"([^"]*?)"\s*[,}]'),
}
_SHARD_FIELD_STRING_LENIENT = {
    "clarified_statement": re.compile(
        r'"clarified_statement"\s*:\s*"(.*?)"\s*,\s*"(?:voice_anchor|support_excerpt|compression_ratio|segment_ordinal|raw_seed_anchor)"',
        re.DOTALL,
    ),
    "voice_anchor": re.compile(
        r'"voice_anchor"\s*:\s*"(.*?)"\s*,\s*"(?:support_excerpt|compression_ratio|distillation_confidence|clarified_statement|gestures_towards)"',
        re.DOTALL,
    ),
    "support_excerpt": re.compile(
        r'"support_excerpt"\s*:\s*"(.*?)"\s*,\s*"(?:compression_ratio|distillation_confidence|gestures_towards|compression_notes)"',
        re.DOTALL,
    ),
}


def _field_extract_shard(obj_text: str) -> dict[str, Any] | None:
    """
    Extract a shard's essential fields via regex when full JSON parsing fails.

    Why this is the last-resort path: ChatGPT sometimes embeds Python code
    with stray `"` or literal newlines inside `clarified_statement` or
    `voice_anchor` strings. Neither json.loads nor escape-repair can parse
    those safely because they require knowing where the string value ends.
    Here we use lenient lookahead to the next known field name as the
    string boundary — not perfect, but recovers the critical payload
    (id + parent_paragraph_id + clarified_statement) that downstream
    normalization needs.
    """
    if not obj_text or "parent_paragraph_id" not in obj_text:
        return None
    result: dict[str, Any] = {}
    for field, pattern in _SHARD_FIELD_PATTERNS.items():
        m = pattern.search(obj_text)
        if m:
            result[field] = m.group(1)
    for field, pattern in _SHARD_FIELD_STRING_LENIENT.items():
        m = pattern.search(obj_text)
        if m:
            result[field] = m.group(1)
    if not result.get("parent_paragraph_id"):
        return None
    # Fill sane defaults for optional fields so downstream normalize works.
    result.setdefault("clarified_statement", "")
    result.setdefault("voice_anchor", "")
    result.setdefault("compression_ratio", 0.7)
    result.setdefault("distillation_confidence", 0.6)
    result.setdefault("gestures_towards", [])
    result.setdefault("compression_notes", ["field_extracted_from_malformed_json"])
    return result


def _repair_and_parse_shard(obj_text: str) -> dict[str, Any] | None:
    """
    Three-tier shard parse:
      1. strict json.loads
      2. escape-inner-quotes repair pass (handles `"foo"bar"` → `"foo\"bar\"`)
      3. regex field extraction (last-resort, handles unescaped code or
         literal newlines inside long string values)
    """
    try:
        parsed = json.loads(obj_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    # Tier 2: escape pass
    repaired_chars: list[str] = []
    in_string = False
    for i, ch in enumerate(obj_text):
        if ch == '"':
            if in_string:
                j = i + 1
                while j < len(obj_text) and obj_text[j] in " \t\n\r":
                    j += 1
                following = obj_text[j] if j < len(obj_text) else ""
                if following in ",:}]" or following == "":
                    in_string = False
                    repaired_chars.append(ch)
                    continue
                repaired_chars.append("\\\"")
                continue
            else:
                in_string = True
                repaired_chars.append(ch)
                continue
        if ch == "\\" and in_string:
            repaired_chars.append(ch)
            if i + 1 < len(obj_text):
                repaired_chars.append(obj_text[i + 1])
            continue
        if in_string and ch in "\n\r\t":
            # literal control chars inside strings — escape them
            repaired_chars.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[ch])
            continue
        repaired_chars.append(ch)
    repaired = "".join(repaired_chars)
    try:
        parsed2 = json.loads(repaired)
        if isinstance(parsed2, dict):
            return parsed2
    except json.JSONDecodeError:
        pass
    # Tier 3: field-level regex extraction
    return _field_extract_shard(obj_text)


def _salvage_shards_from_malformed_json(text: str) -> dict[str, Any] | None:
    """
    Shard-level recovery when the outer JSON can't be parsed.

    Splits text into balanced {...} objects, tries to parse each, and repairs
    common errors (unescaped inner quotes). Keeps the good shards, drops the
    unrepairable ones. Preserves progress on probes where ChatGPT formatted
    most shards correctly but broke on one or two with embedded quotes.
    """
    if not text:
        return None
    salvaged: list[dict[str, Any]] = []
    # Try depth-2 first (inside an outer {"shards":[...]} wrapper), then
    # depth-1 (bare top-level shard objects), to cover both shapes ChatGPT
    # might emit.
    for depth in (2, 1):
        for obj_text in _split_balanced_json_objects(text, target_depth=depth):
            if "parent_paragraph_id" not in obj_text:
                continue
            parsed = _repair_and_parse_shard(obj_text)
            if parsed and parsed.get("parent_paragraph_id"):
                salvaged.append(parsed)
        if salvaged:
            break
    if not salvaged:
        return None
    # Dedupe by id preserving order
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for s in salvaged:
        sid = str(s.get("id") or s.get("parent_paragraph_id") or "")
        if sid in seen:
            continue
        seen.add(sid)
        deduped.append(s)
    return {"shards": deduped}


def _load_distillation_artifact_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.suffix.lower() == ".json":
        return _load_json(path)
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
                # extract_json_object is lenient — it can return just the first
                # nested object when the outer JSON is malformed (missing closing
                # quote, etc.). That gives us one shard when 30 were expected.
                # Detect this: if parsed has no `shards` list AND the raw text
                # clearly contains many shard objects, prefer regex salvage.
                parsed_has_shards = (
                    isinstance(payload, dict)
                    and isinstance(payload.get("shards"), list)
                    and len(payload.get("shards") or []) > 0
                )
                raw_shard_mentions = payload_markdown.count('"parent_paragraph_id"')
                if not parsed_has_shards and raw_shard_mentions >= 2:
                    salvaged = _salvage_shards_from_malformed_json(payload_markdown)
                    if salvaged and len(salvaged.get("shards") or []) > len(
                        (payload or {}).get("shards") or []
                        if isinstance(payload, dict)
                        else []
                    ):
                        return salvaged
                if isinstance(payload, dict):
                    return payload
                salvaged = _salvage_shards_from_malformed_json(payload_markdown)
                if salvaged:
                    return salvaged
    try:
        payload = extract_json_object(source)
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        return payload
    # Last resort: regex-salvage from raw source.
    return _salvage_shards_from_malformed_json(source)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _slugify(value: str, *, fallback: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", _string(value).strip().lower()).strip("_")
    return token or fallback


def _resolve_family_dir(repo_root: Path, family: str) -> str:
    family_token = _string(family).strip() or "09"
    raw_seed_root = repo_root / "obsidian" / "okay lets do this"
    for candidate in raw_seed_root.glob(f"{family_token}*"):
        if candidate.is_dir():
            return candidate.relative_to(repo_root).as_posix()
    raise FileNotFoundError(f"Could not resolve family dir for family={family_token!r}")


def _paragraph_text(paragraph: Mapping[str, Any]) -> str:
    for key in ("plain_text", "text", "summary", "note"):
        value = _string(paragraph.get(key))
        if value.strip():
            return value
    return ""


def _paragraph_anchor(paragraph: Mapping[str, Any]) -> str:
    paragraph_id = _string(paragraph.get("id"))
    if paragraph_id:
        return f"paragraph:{paragraph_id}"
    start = paragraph.get("line_start")
    end = paragraph.get("line_end")
    if isinstance(start, int) and isinstance(end, int):
        return f"lines:{start}-{end}"
    return "paragraph:unknown"


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


def _stable_contextual_row_id(source_ids: Iterable[Any], title: str, summary: str) -> str:
    source_part = "|".join(_dedupe_strings(source_ids))
    seed = f"{source_part}:{_normalize_whitespace(title)}:{_normalize_whitespace(summary)}".encode(
        "utf-8"
    )
    return f"rsc_{hashlib.sha1(seed).hexdigest()[:12]}"


def _existing_distilled_paragraph_ids(shards: Iterable[Mapping[str, Any]]) -> set[str]:
    paragraph_ids: set[str] = set()
    for shard in shards:
        if _string(shard.get("atomization_source")) != DISTILLATION_SOURCE:
            continue
        parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
        if parent_paragraph_id:
            paragraph_ids.add(parent_paragraph_id)
    return paragraph_ids


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",") if "," in value else [value]
    elif isinstance(value, IterableABC) and not isinstance(value, (str, bytes, Mapping)):
        raw_items = list(value)
    else:
        raw_items = [value]
    return _dedupe_strings(_string(item) for item in raw_items)


def _paragraph_section_token(paragraph: Mapping[str, Any]) -> str:
    return _string(
        paragraph.get("section_id")
        or paragraph.get("section")
        or paragraph.get("section_slug")
        or paragraph.get("section_heading")
        or paragraph.get("heading")
    )


def _paragraph_card(paragraph: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _string(paragraph.get("id")),
        "line_start": paragraph.get("line_start"),
        "line_end": paragraph.get("line_end"),
        "section_id": _string(
            paragraph.get("section_id")
            or paragraph.get("section")
            or paragraph.get("section_slug")
        ),
        "section_heading": _string(
            paragraph.get("section_heading")
            or paragraph.get("heading")
            or paragraph.get("section_title")
        ),
        "plain_text": _paragraph_text(paragraph),
        "summary": _string(paragraph.get("summary")),
        "idea_group_ids": _string_list(paragraph.get("idea_group_ids")),
        "related_paragraph_ids": _string_list(paragraph.get("related_paragraph_ids")),
        "keywords": _dedupe_strings(
            [*_string_list(paragraph.get("keywords")), *_string_list(paragraph.get("keyword_hints"))]
        ),
        "mechanisms": _dedupe_strings(
            [*_string_list(paragraph.get("mechanisms")), *_string_list(paragraph.get("mechanism_hints"))]
        ),
        "section_path": _string(paragraph.get("section_path") or paragraph.get("section_path_slug")),
        "semantic_batch_group_key": _string(paragraph.get("semantic_batch_group_key")),
        "semantic_batch_group_reason": _string(paragraph.get("semantic_batch_group_reason")),
        "semantic_batch_score": paragraph.get("semantic_batch_score"),
        "semantic_batch_features": _string_list(paragraph.get("semantic_batch_features")),
        "paragraph_fingerprint": _string(
            paragraph.get("paragraph_fingerprint") or paragraph.get("fingerprint")
        ),
    }


def _shared_tokens(left: Mapping[str, Any], right: Mapping[str, Any], key: str) -> list[str]:
    left_values = set(_string_list(left.get(key)))
    right_values = set(_string_list(right.get(key)))
    return sorted(left_values & right_values)


def _context_relationship_reasons(
    focus_card: Mapping[str, Any],
    context_card: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    focus_id = _string(focus_card.get("id"))
    context_id = _string(context_card.get("id"))
    if context_id and context_id in set(_string_list(focus_card.get("related_paragraph_ids"))):
        reasons.append("focus_declares_related_paragraph")
    if focus_id and focus_id in set(_string_list(context_card.get("related_paragraph_ids"))):
        reasons.append("context_declares_related_paragraph")
    for key, label in (
        ("idea_group_ids", "shared_idea_group"),
        ("mechanisms", "shared_mechanism"),
        ("keywords", "shared_keyword"),
    ):
        shared = _shared_tokens(focus_card, context_card, key)
        if shared:
            reasons.append(f"{label}:{','.join(shared[:3])}")
    focus_section = _paragraph_section_token(focus_card)
    context_section = _paragraph_section_token(context_card)
    if focus_section and focus_section == context_section:
        reasons.append("same_section")
    return reasons or ["line_neighbor"]


def _option_surface_context_rows(
    *,
    focus_card: Mapping[str, Any],
    context_cards: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in context_cards[:OPTION_SURFACE_CONTEXT_CAP]:
        rows.append(
            {
                "paragraph_id": _string(card.get("id")),
                "relationship": _context_relationship_reasons(focus_card, card),
                "line_start": card.get("line_start"),
                "line_end": card.get("line_end"),
                "section_id": _string(card.get("section_id")),
                "section_heading": _string(card.get("section_heading")),
                "idea_group_ids": _string_list(card.get("idea_group_ids")),
                "keywords": _string_list(card.get("keywords"))[:8],
                "mechanisms": _string_list(card.get("mechanisms"))[:8],
                "emit_shards": False,
                "use": "disambiguation_only",
            }
        )
    return rows


def _option_surface_rows_for_focus_cards(
    *,
    focus_cards: list[Mapping[str, Any]],
    context_cards: list[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    context_cards = context_cards or []
    if len(focus_cards) == 1:
        return _option_surface_context_rows(
            focus_card=focus_cards[0],
            context_cards=context_cards,
        )

    rows: list[dict[str, Any]] = []
    for focus_card in focus_cards:
        focus_id = _string(focus_card.get("id"))
        for peer_card in focus_cards:
            peer_id = _string(peer_card.get("id"))
            if not focus_id or not peer_id or peer_id == focus_id:
                continue
            rows.append(
                {
                    "focus_paragraph_id": focus_id,
                    "paragraph_id": peer_id,
                    "relationship": _context_relationship_reasons(focus_card, peer_card),
                    "line_start": peer_card.get("line_start"),
                    "line_end": peer_card.get("line_end"),
                    "section_id": _string(peer_card.get("section_id")),
                    "section_heading": _string(peer_card.get("section_heading")),
                    "idea_group_ids": _string_list(peer_card.get("idea_group_ids")),
                    "keywords": _string_list(peer_card.get("keywords"))[:8],
                    "mechanisms": _string_list(peer_card.get("mechanisms"))[:8],
                    "emit_shards": True,
                    "use": "cross_focus_disambiguation_and_grouping",
                }
            )
            if len(rows) >= OPTION_SURFACE_CONTEXT_CAP:
                return rows
    return rows


def _option_surface_payload(
    *,
    mode: str,
    focus_cards: list[Mapping[str, Any]],
    context_cards: list[Mapping[str, Any]] | None = None,
    context_rows: list[Mapping[str, Any]] | None = None,
    grouping_rows: list[Mapping[str, Any]] | None = None,
    compression_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context_cards = context_cards or []
    resolved_grouping_rows = list(grouping_rows or _batch_grouping_rows(focus_cards))
    resolved_context_rows = list(
        context_rows
        if context_rows is not None
        else _option_surface_rows_for_focus_cards(
            focus_cards=focus_cards,
            context_cards=context_cards,
        )
    )
    payload = {
        "schema_version": "raw_seed_distillation_option_surface_v1",
        "mode": mode,
        "provider_review_notice": PROVIDER_REVIEW_NOTICE,
        "legacy_schema_notice": LEGACY_SCHEMA_NOTICE,
        "visibility_boundary": {
            "bridge_can_see": "Only this packet plus injected skill/context files.",
            "bridge_cannot_see": (
                "The whole local row corpus, global novelty, coverage freshness, or downstream "
                "doctrine routing truth."
            ),
            "inference_rule": (
                "Use absent context as uncertainty; do not infer corpus-wide facts from a "
                "packet-local view."
            ),
        },
        "authority_boundary": {
            "emit_shards_for": [_string(card.get("id")) for card in focus_cards if _string(card.get("id"))],
            "context_only": [_string(card.get("id")) for card in context_cards if _string(card.get("id"))],
            "clarified_statement_rule": (
                "Rephrase the focus paragraph into a technically clearer, denser statement; "
                "do not preserve the operator's wording verbatim. State what the paragraph "
                "is gesturing at."
            ),
            "traceability_rule": (
                "Every shard must be traceable to its parent paragraph via at least one of "
                "(voice_anchor, support_excerpt). Either field may be a verbatim substring "
                "from the parent (after stripping ` * _ ~ markup). Backticks, italics, and "
                "whitespace are normalized away by the validator, so do not reformat the "
                "underlying text to match — just ensure the trace is anchored."
            ),
        },
        "focus_grouping_rows": resolved_grouping_rows,
        "context_rows": resolved_context_rows,
        "worker_rules": [
            "Treat grouping rows as navigation hints, not route decisions.",
            "Do not claim novelty or coverage against rows you cannot see.",
            "Do not emit rows for context-only paragraphs.",
            "Use the legacy JSON key `shards` because the local importer expects it; semantically these are first-party source-index rows.",
            "If a focus paragraph depends on missing context, lower the legacy distillation_confidence field and populate gestures_towards.",
        ],
    }
    if compression_contract:
        payload.update(
            {
                "profile_id": compression_contract.get("profile_id"),
                "creator_skill_id": compression_contract.get("creator_skill_id"),
                "navigator_skill_id": compression_contract.get("navigator_skill_id"),
                "band": compression_contract.get("band"),
                "source_state": compression_contract.get("source_state"),
                "band_reason": compression_contract.get("band_reason"),
                "compression_profile": compression_contract.get("compression_profile"),
                "context_horizon": compression_contract.get("context_horizon"),
                "context_space_refs": compression_contract.get("context_space_refs"),
                "drilldown_refs": compression_contract.get("drilldown_refs"),
                "dynamic_fact_rows": compression_contract.get("dynamic_fact_rows"),
                "omission_receipt": compression_contract.get("omission_receipt"),
            }
        )
    return payload


def _paragraph_group_key(paragraph: Mapping[str, Any]) -> str:
    semantic_key = _string(paragraph.get("semantic_batch_group_key"))
    if semantic_key:
        return semantic_key
    for prefix, key in (
        ("idea_group", "idea_group_ids"),
        ("mechanism", "mechanisms"),
        ("keyword", "keywords"),
    ):
        values = _string_list(paragraph.get(key))
        if values:
            return f"{prefix}:{values[0]}"
    section = _paragraph_section_token(paragraph)
    if section:
        return f"section:{section}"
    return "ungrouped"


def _batch_grouping_rows(paragraphs: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for paragraph in paragraphs:
        groups.setdefault(_paragraph_group_key(paragraph), []).append(paragraph)
    rows: list[dict[str, Any]] = []
    for group_key in sorted(groups):
        members = groups[group_key]
        rows.append(
            {
                "group_key": group_key,
                "focus_paragraph_ids": [
                    _string(paragraph.get("id"))
                    for paragraph in members
                    if _string(paragraph.get("id"))
                ],
                "member_count": len(members),
                "grouping_reason": _string(members[0].get("semantic_batch_group_reason"))
                or _grouping_reason_for_key(group_key),
                "grouping_features": _dedupe_strings(
                    feature
                    for member in members
                    for feature in _string_list(member.get("semantic_batch_features"))
                )[:12],
                "semantic_batch_score": max(
                    [
                        float(member.get("semantic_batch_score") or 0.0)
                        for member in members
                    ]
                    or [0.0]
                ),
                "read_as": "packet_local_continuity_hint",
                "not_a_route": True,
            }
        )
    return rows


def _grouping_reason_for_key(group_key: str) -> str:
    if group_key.startswith("idea_group:"):
        return "semantic_neighbor"
    if group_key.startswith("mechanism:"):
        return "mechanism_neighbor"
    if group_key.startswith("keyword:"):
        return "keyword_neighbor"
    if group_key.startswith("section:"):
        return "chronological_fallback"
    if group_key.startswith("orphan:") or group_key == "ungrouped":
        return "orphan"
    return "semantic_neighbor"


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


def _ordered_bin_candidates(
    bin_rows: list[dict[str, Any]],
    *,
    paragraph_index: Mapping[str, Mapping[str, Any]],
    selection_mode: str,
) -> list[dict[str, Any]]:
    mode = _normalize_selection_mode(selection_mode, default=SELECTION_MODE_OLDEST_FIRST)

    def _line(bin_row: Mapping[str, Any], *, prefer: str) -> int:
        paragraph = paragraph_index.get(_string(bin_row.get("parent_paragraph_id"))) or {}
        if prefer == "start":
            return int(paragraph.get("line_start") or paragraph.get("line_end") or 0)
        return int(paragraph.get("line_end") or paragraph.get("line_start") or 0)

    if mode == SELECTION_MODE_FRESH_FIRST:
        return sorted(
            bin_rows,
            key=lambda bin_row: (
                -_line(bin_row, prefer="end"),
                _string(bin_row.get("parent_paragraph_id")),
                _string(bin_row.get("shard_id")),
            ),
        )
    if mode == SELECTION_MODE_MIXED:
        freshest = sorted(
            bin_rows,
            key=lambda bin_row: (
                -_line(bin_row, prefer="end"),
                _string(bin_row.get("parent_paragraph_id")),
                _string(bin_row.get("shard_id")),
            ),
        )
        oldest = sorted(
            bin_rows,
            key=lambda bin_row: (
                _line(bin_row, prefer="start"),
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
            _line(bin_row, prefer="start"),
            _string(bin_row.get("parent_paragraph_id")),
            _string(bin_row.get("shard_id")),
        ),
    )


def _distillation_dispatch_policy(repo_root: Path) -> dict[str, Any]:
    try:
        payload = load_mission_template(repo_root, MISSION_ID)
    except ValueError:
        payload = load_mission_template(REPO_ROOT, MISSION_ID)
    dispatch_policy = payload.get("dispatch_policy") if isinstance(payload.get("dispatch_policy"), Mapping) else {}
    return {
        **dict(dispatch_policy or {}),
        "mission_id": MISSION_ID,
    }


def _resolve_wave_width(
    *,
    repo_root: Path,
    provider: str,
    requested_wave_width: Any,
) -> dict[str, Any]:
    return resolve_dispatch_policy(
        mission_dispatch_policy=_distillation_dispatch_policy(repo_root),
        provider=provider,
        requested_wave_width=requested_wave_width,
        provider_capabilities_path=repo_root / "tools/meta/bridge/provider_capabilities.json",
    )


def _additional_context_files(repo_root: Path, family_dir: str) -> list[str]:
    candidates = [
        f"{raw_seed_workspace_dir_for_family(family_dir)}/{OPTIONAL_EXAMPLES_FILENAME}",
    ]
    context_files: list[str] = []
    for rel in candidates:
        token = _string(rel).strip()
        if token and (repo_root / token).exists():
            context_files.append(token)
    return context_files


def _select_paragraphs(
    *,
    raw_seed_payload: Mapping[str, Any],
    raw_seed_shards_payload: Mapping[str, Any],
    existing_shards: list[Mapping[str, Any]],
    cohort_size: int,
    paragraph_ids: list[str] | None,
    selection_mode: str,
) -> list[dict[str, Any]]:
    all_paragraphs = [
        dict(paragraph)
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    ]
    explicit_ids = _dedupe_strings(paragraph_ids or [])
    by_id = {_string(paragraph.get("id")): paragraph for paragraph in all_paragraphs}
    if explicit_ids:
        selected = [dict(by_id[pid]) for pid in explicit_ids if pid in by_id]
    else:
        already_distilled = _existing_distilled_paragraph_ids(existing_shards)
        paragraph_index = {
            _string(paragraph.get("id")): dict(paragraph)
            for paragraph in all_paragraphs
            if _string(paragraph.get("id"))
        }
        candidate_bins = [
            dict(bin_row)
            for bin_row in (raw_seed_shards_payload.get("shards") or [])
            if isinstance(bin_row, Mapping)
            and _string(bin_row.get("shard_id"))
            and _string(bin_row.get("parent_paragraph_id")) in paragraph_index
            and _string(bin_row.get("parent_paragraph_id")) not in already_distilled
        ]
        if candidate_bins:
            ordered_bins = _ordered_bin_candidates(
                candidate_bins,
                paragraph_index=paragraph_index,
                selection_mode=selection_mode,
            )
            selected = [
                dict(paragraph_index[parent_paragraph_id])
                for parent_paragraph_id in [
                    _string(bin_row.get("parent_paragraph_id")) for bin_row in ordered_bins[: max(1, int(cohort_size))]
                ]
                if parent_paragraph_id in paragraph_index
            ]
        else:
            selected = [
                dict(paragraph)
                for paragraph in all_paragraphs
                if _string(paragraph.get("id")) not in already_distilled
            ]
            mode = _normalize_selection_mode(selection_mode, default=SELECTION_MODE_OLDEST_FIRST)
            if mode == SELECTION_MODE_FRESH_FIRST:
                selected.sort(
                    key=lambda paragraph: (
                        -int(paragraph.get("line_end") or paragraph.get("line_start") or 0),
                        _string(paragraph.get("id")),
                    )
                )
            else:
                selected.sort(
                    key=lambda paragraph: (
                        int(paragraph.get("line_start") or paragraph.get("line_end") or 0),
                        _string(paragraph.get("id")),
                    )
                )
            selected = selected[: max(1, int(cohort_size))]
    if not selected:
        raise ValueError("No raw-seed paragraphs matched the requested distillation selection.")
    return selected


def preview_distillation_selection(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    paragraph_ids: list[str] | None = None,
    selection_mode: str = SELECTION_MODE_OLDEST_FIRST,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    substrate_token = _string(substrate).strip() or "raw_seed"
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

    extracted = _load_json(repo_root / family_extracted_shards_path(family_dir)) or {"shards": []}
    existing_shards = [
        shard for shard in (extracted.get("shards") or []) if isinstance(shard, Mapping)
    ]
    try:
        selected = _select_paragraphs(
            raw_seed_payload=raw_seed_payload,
            raw_seed_shards_payload=raw_seed_shards_payload,
            existing_shards=existing_shards,
            cohort_size=max(1, int(cohort_size)),
            paragraph_ids=paragraph_ids,
            selection_mode=selection_mode,
        )
    except ValueError:
        selected = []

    return {
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "cohort_size": max(1, int(cohort_size)),
        "selection_mode": _normalize_selection_mode(selection_mode, default=SELECTION_MODE_OLDEST_FIRST),
        "selected_count": len(selected),
        "selected_paragraph_ids": [_string(paragraph.get("id")) for paragraph in selected],
        "status": "ready" if selected else "noop",
    }


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
    selected_count: int,
    total_paragraph_count: int,
    total_atomized_parent_count: int,
    source_paths: Mapping[str, str],
    observed_at: str,
) -> dict[str, Any]:
    focus_text = _paragraph_text(focus_paragraph)
    focus_card = _paragraph_card(focus_paragraph)
    context_rows = _option_surface_rows_for_focus_cards(
        focus_cards=[focus_card],
        context_cards=neighbor_paragraphs,
    )
    grouping_rows = _batch_grouping_rows([focus_card])
    compression_contract = build_raw_seed_context_contract(
        family=family,
        family_dir=family_dir,
        focus_cards=[focus_card],
        context_rows=context_rows,
        grouping_rows=grouping_rows,
        packet_kind="raw_seed_distillation_packet",
        selected_count=selected_count,
        total_paragraph_count=total_paragraph_count,
        total_atomized_parent_count=total_atomized_parent_count,
        source_paths=source_paths,
        observed_at=observed_at,
    )
    return {
        "kind": "raw_seed_distillation_packet",
        "schema_version": "raw_seed_distillation_packet_v2",
        "provider_facing_task_kind": "first_party_raw_seed_source_indexing",
        "provider_review_notice": PROVIDER_REVIEW_NOTICE,
        "legacy_schema_notice": LEGACY_SCHEMA_NOTICE,
        "family": {
            "family_number": family,
            "family_dir": family_dir,
        },
        "focus_paragraph": focus_card,
        "neighbor_paragraphs": neighbor_paragraphs,
        "profile_id": compression_contract["profile_id"],
        "creator_skill_id": compression_contract["creator_skill_id"],
        "navigator_skill_id": compression_contract["navigator_skill_id"],
        "band": compression_contract["band"],
        "source_state": compression_contract["source_state"],
        "band_reason": compression_contract["band_reason"],
        "context_space_refs": compression_contract["context_space_refs"],
        "drilldown_refs": compression_contract["drilldown_refs"],
        "dynamic_fact_rows": compression_contract["dynamic_fact_rows"],
        "omission_receipt": compression_contract["omission_receipt"],
        "option_surface": _option_surface_payload(
            mode="single_focus_with_context",
            focus_cards=[focus_card],
            context_cards=neighbor_paragraphs,
            context_rows=context_rows,
            grouping_rows=grouping_rows,
            compression_contract=compression_contract,
        ),
        "focus_text_length": len(focus_text),
        "operator_constraints": [
            "Output first-party source-index rows only for focus_paragraph.id.",
            "Use the legacy JSON key `shards` because the local importer expects it.",
            "Use neighbor_paragraphs only to disambiguate intent.",
            "Bridge visibility is packet-local: do not claim novelty, coverage, or global row state.",
            "Preserve voice while removing speech-to-text noise.",
            "Do not route or classify doctrine.",
        ],
    }


def _estimate_paragraph_card_chars(paragraph: Mapping[str, Any]) -> int:
    """
    Estimate a paragraph's contribution to probe prompt size.

    Empirical model (Family 09, 2026-04-17): a paragraph card's JSON
    serialization is its plain_text length plus a near-constant 302-char
    wrapper (id + line_start + line_end + summary fields).
    """
    text_len = len(_paragraph_text(paragraph))
    return text_len + PARAGRAPH_CARD_OVERHEAD_CHARS


def _paragraph_order_key(paragraph: Mapping[str, Any]) -> tuple[int, str]:
    line = paragraph.get("line_start") or paragraph.get("line_end") or 0
    try:
        line_number = int(line)
    except (TypeError, ValueError):
        line_number = 0
    return (line_number, _string(paragraph.get("id")))


def _semantic_values(paragraph: Mapping[str, Any], key: str) -> list[str]:
    if key == "mechanisms":
        return _dedupe_strings(
            [*_string_list(paragraph.get("mechanisms")), *_string_list(paragraph.get("mechanism_hints"))]
        )
    if key == "keywords":
        return _dedupe_strings(
            [*_string_list(paragraph.get("keywords")), *_string_list(paragraph.get("keyword_hints"))]
        )
    return _string_list(paragraph.get(key))


def _shared_semantic_features(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, list[str]]:
    features = {
        "idea_group_ids": sorted(
            set(_semantic_values(left, "idea_group_ids")) & set(_semantic_values(right, "idea_group_ids"))
        ),
        "mechanisms": sorted(
            set(_semantic_values(left, "mechanisms")) & set(_semantic_values(right, "mechanisms"))
        ),
        "keywords": sorted(
            set(_semantic_values(left, "keywords")) & set(_semantic_values(right, "keywords"))
        ),
        "related_paragraph_ids": [],
        "section_path": [],
    }
    left_id = _string(left.get("id"))
    right_id = _string(right.get("id"))
    if right_id and right_id in set(_string_list(left.get("related_paragraph_ids"))):
        features["related_paragraph_ids"].append(right_id)
    if left_id and left_id in set(_string_list(right.get("related_paragraph_ids"))):
        features["related_paragraph_ids"].append(left_id)
    left_section = _paragraph_section_token(left)
    right_section = _paragraph_section_token(right)
    left_path = _string(left.get("section_path"))
    right_path = _string(right.get("section_path"))
    if left_path and left_path == right_path:
        features["section_path"].append(left_path)
    elif left_section and left_section == right_section:
        features["section_path"].append(left_section)
    return features


def _semantic_pair_score(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    features = _shared_semantic_features(left, right)
    score = 0.0
    score += 9.0 * len(features["idea_group_ids"])
    score += 7.0 * len(features["related_paragraph_ids"])
    score += 5.0 * len(features["mechanisms"])
    score += 3.0 * len(features["keywords"])
    score += 2.0 * len(features["section_path"])
    left_line, _ = _paragraph_order_key(left)
    right_line, _ = _paragraph_order_key(right)
    if left_line and right_line:
        distance = abs(left_line - right_line)
        if distance <= 25:
            score += 1.5
        elif distance <= 100:
            score += 0.75
    return score


def _semantic_group_metadata(paragraphs: list[Mapping[str, Any]]) -> tuple[str, str, list[str], float]:
    if not paragraphs:
        return ("orphan:empty", "orphan", [], 0.0)
    if len(paragraphs) == 1:
        paragraph_id = _string(paragraphs[0].get("id")) or "unknown"
        return (f"orphan:{paragraph_id}", "orphan", [], 0.0)
    counters: dict[str, dict[str, int]] = {
        "idea_group": {},
        "mechanism": {},
        "keyword": {},
        "section": {},
    }
    for paragraph in paragraphs:
        for value in _semantic_values(paragraph, "idea_group_ids"):
            counters["idea_group"][value] = counters["idea_group"].get(value, 0) + 1
        for value in _semantic_values(paragraph, "mechanisms"):
            counters["mechanism"][value] = counters["mechanism"].get(value, 0) + 1
        for value in _semantic_values(paragraph, "keywords"):
            counters["keyword"][value] = counters["keyword"].get(value, 0) + 1
        section = _string(paragraph.get("section_path")) or _paragraph_section_token(paragraph)
        if section:
            counters["section"][section] = counters["section"].get(section, 0) + 1

    for prefix, reason in (
        ("idea_group", "semantic_neighbor"),
        ("mechanism", "mechanism_neighbor"),
        ("keyword", "keyword_neighbor"),
        ("section", "chronological_fallback"),
    ):
        values = counters[prefix]
        shared = [
            (value, count)
            for value, count in values.items()
            if count >= 2
        ]
        if not shared:
            continue
        shared.sort(key=lambda item: (-item[1], item[0]))
        value = shared[0][0]
        features = [f"{prefix}:{item[0]}" for item in shared[:8]]
        max_pair_score = max(
            _semantic_pair_score(left, right)
            for left_index, left in enumerate(paragraphs)
            for right in paragraphs[left_index + 1 :]
        )
        return (f"{prefix}:{value}", reason, features, max_pair_score)

    first_id = _string(paragraphs[0].get("id")) or "unknown"
    max_pair_score = max(
        _semantic_pair_score(left, right)
        for left_index, left in enumerate(paragraphs)
        for right in paragraphs[left_index + 1 :]
    )
    return (f"chronological:{first_id}", "chronological_fallback", [], max_pair_score)


def _annotate_semantic_neighborhood(
    paragraphs: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    group_key, reason, features, score = _semantic_group_metadata(paragraphs)
    annotated: list[dict[str, Any]] = []
    for paragraph in sorted(paragraphs, key=_paragraph_order_key):
        row = dict(paragraph)
        row["semantic_batch_group_key"] = group_key
        row["semantic_batch_group_reason"] = reason
        row["semantic_batch_features"] = features
        row["semantic_batch_score"] = round(float(score), 3)
        annotated.append(row)
    return annotated


def _semantic_neighborhoods(
    paragraphs: list[Mapping[str, Any]],
    *,
    budget_chars: int,
    max_per_chunk: int,
) -> list[list[dict[str, Any]]]:
    remaining = [dict(paragraph) for paragraph in sorted(paragraphs, key=_paragraph_order_key)]
    neighborhoods: list[list[dict[str, Any]]] = []
    budget = max(1, int(budget_chars))
    cap = max(1, int(max_per_chunk))
    while remaining:
        seed = remaining.pop(0)
        current: list[dict[str, Any]] = [seed]
        current_size = _estimate_paragraph_card_chars(seed)
        while len(current) < cap and remaining:
            best_index: int | None = None
            best_score = 0.0
            for index, candidate in enumerate(remaining):
                candidate_size = _estimate_paragraph_card_chars(candidate)
                if current_size <= budget and current_size + candidate_size > budget:
                    continue
                score = max(_semantic_pair_score(member, candidate) for member in current)
                if score > best_score:
                    best_score = score
                    best_index = index
            if best_index is None or best_score < 3.0:
                break
            candidate = remaining.pop(best_index)
            current_size += _estimate_paragraph_card_chars(candidate)
            current.append(candidate)
        neighborhoods.append(_annotate_semantic_neighborhood(current))
    return neighborhoods


def _bin_pack_paragraphs(
    paragraphs: list[Mapping[str, Any]],
    *,
    budget_chars: int = PARAGRAPH_BUDGET_PER_PROBE_CHARS,
    max_per_chunk: int = MAX_PARAGRAPHS_PER_PROBE,
) -> list[list[dict[str, Any]]]:
    """
    Semantic-neighborhood first, then first-fit probe packing.

    Grouping is a transport/context optimization only: every paragraph remains
    its own authority boundary and every emitted row must still point at one
    parent paragraph. Neighborhoods are formed from explicit registry hints
    before being fit into bridge-budget bins.

    Oversized paragraphs (single card > budget) get their own chunk
    regardless. This is the only case where a chunk exceeds budget, and it
    cannot be avoided without splitting paragraph bodies (which would break
    voice-preservation).
    """
    if not paragraphs:
        return []
    budget = max(1, int(budget_chars))
    cap = max(1, int(max_per_chunk))
    neighborhoods = _semantic_neighborhoods(
        paragraphs,
        budget_chars=budget,
        max_per_chunk=cap,
    )
    sized = [
        (
            sum(_estimate_paragraph_card_chars(paragraph) for paragraph in neighborhood),
            neighborhood,
        )
        for neighborhood in neighborhoods
    ]
    sized.sort(key=lambda item: -item[0])
    chunks: list[list[dict[str, Any]]] = []
    chunk_sizes: list[int] = []
    for size, neighborhood in sized:
        placed = False
        for index, current_size in enumerate(chunk_sizes):
            if len(chunks[index]) + len(neighborhood) > cap:
                continue
            if current_size + size <= budget:
                chunks[index].extend(neighborhood)
                chunk_sizes[index] = current_size + size
                placed = True
                break
        if not placed:
            chunks.append(list(neighborhood))
            chunk_sizes.append(size)
    return [sorted(chunk, key=_paragraph_order_key) for chunk in chunks]


def _multi_paragraph_packet_payload(
    *,
    family: str,
    family_dir: str,
    focus_paragraphs: list[Mapping[str, Any]],
    selected_count: int,
    total_paragraph_count: int,
    total_atomized_parent_count: int,
    source_paths: Mapping[str, str],
    observed_at: str,
) -> dict[str, Any]:
    cards = [_paragraph_card(paragraph) for paragraph in focus_paragraphs]
    focus_ids = [_string(paragraph.get("id")) for paragraph in focus_paragraphs]
    total_text_length = sum(len(_paragraph_text(paragraph)) for paragraph in focus_paragraphs)
    context_rows = _option_surface_rows_for_focus_cards(focus_cards=cards)
    grouping_rows = _batch_grouping_rows(cards)
    compression_contract = build_raw_seed_context_contract(
        family=family,
        family_dir=family_dir,
        focus_cards=cards,
        context_rows=context_rows,
        grouping_rows=grouping_rows,
        packet_kind="raw_seed_distillation_batch_packet",
        selected_count=selected_count,
        total_paragraph_count=total_paragraph_count,
        total_atomized_parent_count=total_atomized_parent_count,
        source_paths=source_paths,
        observed_at=observed_at,
    )
    return {
        "kind": "raw_seed_distillation_batch_packet",
        "schema_version": "raw_seed_distillation_batch_packet_v2",
        "provider_facing_task_kind": "first_party_raw_seed_source_indexing",
        "provider_review_notice": PROVIDER_REVIEW_NOTICE,
        "legacy_schema_notice": LEGACY_SCHEMA_NOTICE,
        "family": {
            "family_number": family,
            "family_dir": family_dir,
        },
        "focus_paragraphs": cards,
        "focus_paragraph_ids": [pid for pid in focus_ids if pid],
        "profile_id": compression_contract["profile_id"],
        "creator_skill_id": compression_contract["creator_skill_id"],
        "navigator_skill_id": compression_contract["navigator_skill_id"],
        "band": compression_contract["band"],
        "source_state": compression_contract["source_state"],
        "band_reason": compression_contract["band_reason"],
        "context_space_refs": compression_contract["context_space_refs"],
        "drilldown_refs": compression_contract["drilldown_refs"],
        "dynamic_fact_rows": compression_contract["dynamic_fact_rows"],
        "omission_receipt": compression_contract["omission_receipt"],
        "option_surface": _option_surface_payload(
            mode="multi_focus_semantic_batch",
            focus_cards=cards,
            context_rows=context_rows,
            grouping_rows=grouping_rows,
            compression_contract=compression_contract,
        ),
        "focus_count": len(focus_paragraphs),
        "focus_text_length": total_text_length,
        "operator_constraints": [
            "Index EVERY focus_paragraphs[*] independently. Do not skip any.",
            "Each row's parent_paragraph_id must match one of focus_paragraph_ids.",
            "Use sibling focus_paragraphs only for cross-reference when a focus paragraph is ambiguous; never blend their voices.",
            "Use option_surface.focus_grouping_rows as packet-local continuity hints only.",
            "Use option_surface.context_horizon and drilldown_refs to understand what is deliberately omitted.",
            f"Compression profile is {RAW_SEED_CONTEXT_PROFILE_ID}; creation and navigation must use the same profile.",
            "Bridge visibility is packet-local: do not claim novelty, coverage, or global row state.",
            "Preserve voice while removing speech-to-text noise.",
            "Do not route or classify doctrine.",
            "Output one legacy shards[] array containing source-index rows for all focus paragraphs, in the order they appear in focus_paragraphs.",
        ],
    }


def _focus_ids_from_packet_payload(packet_payload: Mapping[str, Any]) -> list[str]:
    focus_ids = _dedupe_strings(packet_payload.get("focus_paragraph_ids") or [])
    if focus_ids:
        return focus_ids
    focus_paragraph = packet_payload.get("focus_paragraph")
    if isinstance(focus_paragraph, Mapping):
        return _dedupe_strings([focus_paragraph.get("id")])
    focus_paragraphs = packet_payload.get("focus_paragraphs")
    if isinstance(focus_paragraphs, list):
        return _dedupe_strings(
            paragraph.get("id")
            for paragraph in focus_paragraphs
            if isinstance(paragraph, Mapping)
        )
    return []


def _shard_card(shard: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _string(shard.get("id")),
        "parent_paragraph_id": _string(shard.get("parent_paragraph_id")),
        "segment_ordinal": _string(shard.get("segment_ordinal")),
        "clarified_statement": _normalize_whitespace(_string(shard.get("clarified_statement"))),
        "voice_anchor": _normalize_whitespace(_string(shard.get("voice_anchor"))),
        "support_excerpt": _normalize_whitespace(_string(shard.get("support_excerpt"))),
        "gestures_towards": _string_list(shard.get("gestures_towards")),
        "compression_notes": _string_list(shard.get("compression_notes")),
        "atomization_source": _string(shard.get("atomization_source")),
        "source_line_span": dict(shard.get("source_line_span") or {}),
    }


def _lower_bracket_shards_for_focus_ids(
    *,
    repo_root: Path,
    family_dir: str,
    focus_ids: list[str],
    limit: int = LOWER_BRACKET_SHARD_PACKET_LIMIT,
) -> dict[str, Any]:
    focus = set(_dedupe_strings(focus_ids))
    if not focus:
        return {
            "source_state": "unknown",
            "total": 0,
            "included": 0,
            "omitted": 0,
            "shards": [],
        }
    extracted = _load_json(repo_root / family_extracted_shards_path(family_dir)) or {"shards": []}
    matches: list[dict[str, Any]] = []
    for shard in extracted.get("shards") or []:
        if not isinstance(shard, Mapping):
            continue
        parent = _string(shard.get("parent_paragraph_id"))
        raw_ids = set(_string_list(shard.get("raw_paragraph_ids")))
        if parent in focus or focus.intersection(raw_ids):
            matches.append(_shard_card(shard))
    matches.sort(
        key=lambda row: (
            _string(row.get("parent_paragraph_id")),
            _string(row.get("segment_ordinal")),
            _string(row.get("id")),
        )
    )
    parent_ids_with_shards = {
        _string(row.get("parent_paragraph_id"))
        for row in matches
        if _string(row.get("parent_paragraph_id"))
    }
    if not matches:
        source_state = "paragraph_only"
    elif parent_ids_with_shards >= focus:
        source_state = "sharded"
    else:
        source_state = "mixed"
    cap = max(1, int(limit))
    included = matches[:cap]
    omitted = max(0, len(matches) - len(included))
    return {
        "source_state": source_state,
        "total": len(matches),
        "included": len(included),
        "omitted": omitted,
        "limit": cap,
        "shards": included,
        "parent_ids_with_shards": sorted(parent_ids_with_shards),
    }


def _contextualize_packet_payload(
    packet_payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    family_dir: str = "",
) -> dict[str, Any]:
    """Retarget an atomization packet shell into a contextual-compression packet.

    The contextual lane intentionally reuses the distillation selector and
    bin-packer, but the worker contract is different: contextual rows are
    higher-bracket readings over paragraphs/shards, not atomized shards. Keep
    this transform local to the contextual lane so the faithful atomization
    mission remains unchanged.
    """

    packet = dict(packet_payload)
    original_kind = _string(packet.get("kind"))
    original_schema = _string(packet.get("schema_version"))
    focus_ids = _focus_ids_from_packet_payload(packet)
    lower_bracket = _lower_bracket_shards_for_focus_ids(
        repo_root=repo_root,
        family_dir=family_dir or _string((packet.get("family") or {}).get("family_dir")),
        focus_ids=focus_ids,
    )
    packet["kind"] = "raw_seed_contextual_compression_packet"
    packet["schema_version"] = "raw_seed_contextual_compression_packet_v1"
    if original_kind:
        packet["source_packet_kind"] = original_kind
    if original_schema:
        packet["source_packet_schema_version"] = original_schema
    packet["contextual_task"] = {
        "artifact_kind": "raw_seed",
        "profile_id": packet.get("profile_id") or RAW_SEED_CONTEXT_PROFILE_ID,
        "source_relation": "higher_bracket_reading_over_paragraphs_and_shards",
        "source_ids": focus_ids,
        "source_state": lower_bracket["source_state"],
        "lower_brackets": [
            "raw_paragraph",
            "voice_normalized_statement",
            "atomized_shard",
        ],
        "output_bracket": "contextual_row",
        "navigation_contract": "navigation must read profile_id, creator_skill_id, navigator_skill_id, band, source_state, drilldown_refs, dynamic_fact_rows, and omission_receipt from every row",
    }
    packet["output_contract"] = {
        "top_level_shape": {
            "heartbeat_ref": "echo the injected controller heartbeat metadata when present",
            "payload": "mission response body",
        },
        "payload_shape": {
            "contextual_rows": "array of profile-governed contextual rows",
            "notes": "optional warnings or omitted_bands",
            "_summary": "teleology, outcome, confidence",
        },
        "forbidden_outputs": [
            "shards",
            "doctrine_patch",
            "routing_decision",
            "apply_plan",
        ],
    }
    packet["source_state"] = lower_bracket["source_state"]
    packet["lower_bracket_shards"] = {
        "schema_version": "raw_seed_lower_bracket_shards_v1",
        "source_state": lower_bracket["source_state"],
        "total_shards_for_focus": lower_bracket["total"],
        "included_shards": lower_bracket["included"],
        "omitted_shards": lower_bracket["omitted"],
        "limit": lower_bracket["limit"],
        "shards": lower_bracket["shards"],
        "policy": (
            "Included shards are a bounded lower-bracket split map for focus paragraphs. "
            "They do not replace parent par_* authority; omitted shards reopen through extracted_shards."
        ),
    }
    packet["lower_bracket_drilldown_refs"] = [
        {
            "ref_id": "focus_lower_bracket_shards",
            "kind": "source_registry",
            "path": family_extracted_shards_path(
                family_dir or _string((packet.get("family") or {}).get("family_dir"))
            ),
            "parent_paragraph_ids": focus_ids,
            "included_shard_ids": [
                _string(row.get("id"))
                for row in lower_bracket["shards"]
                if _string(row.get("id"))
            ],
            "omitted_shards": lower_bracket["omitted"],
        }
    ]
    omission_receipt = dict(packet.get("omission_receipt") or {})
    omitted_context = list(omission_receipt.get("omitted_context") or [])
    if lower_bracket["omitted"]:
        omitted_context.append(
            {
                "kind": "lower_bracket_shards_beyond_packet_limit",
                "home": family_extracted_shards_path(
                    family_dir or _string((packet.get("family") or {}).get("family_dir"))
                ),
                "reason": (
                    "The packet carries a bounded shard split map; remaining shards reopen "
                    "by parent_paragraph_id."
                ),
                "omitted_count": lower_bracket["omitted"],
            }
        )
    omission_receipt["omitted_context"] = omitted_context
    omission_receipt["omitted_context_count"] = len(omitted_context)
    packet["omission_receipt"] = omission_receipt
    packet["operator_constraints"] = [
        "Produce contextual_rows only; do not emit shards[], doctrine ids, routing decisions, or apply plans.",
        "Rows are higher-bracket readings over focus paragraphs and any existing shard registries, not replacements for raw paragraphs or atomized shards.",
        "Each row's source_ids must include the relevant focus paragraph ids; any atomized shard ids must also appear in drilldown_refs or covered_subclaims.",
        "When lower_bracket_shards are present, use them as the split map for cascade paragraphs instead of flattening the source into one summary.",
        "Use neighbor_paragraphs or sibling focus paragraphs only as context-space/disambiguation evidence; do not blend separate voices into one claim unless they share a named context-space.",
        "Honor profile_id, creator_skill_id, navigator_skill_id, band, source_state, band_reason, context_space_refs, drilldown_refs, dynamic_fact_rows, and omission_receipt.",
        "Carry ids, proof heads, proof depth, and drilldown refs; leave long ancestry in the named ledgers and registries.",
        "Keep volatile facts in dynamic_fact_rows with observed_at, probe_command, source_path, and fingerprint when possible; do not copy them as timeless prose.",
        "If a band or context-space is not supported by the packet, record that in validation_notes or notes.omitted_bands instead of inventing it.",
        "Preserve Will's intent and voice at its cleanest while removing speech-to-text loops and filler.",
        "Bridge visibility is packet-local: do not claim global novelty, global coverage, or absence from doctrine.",
    ]
    return packet


def _distillation_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["shards", "_summary"],
        "properties": {
            "shards": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "parent_paragraph_id",
                        "segment_ordinal",
                        "clarified_statement",
                        "voice_anchor",
                        "compression_ratio",
                        "distillation_confidence",
                        "gestures_towards",
                        "compression_notes",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "parent_paragraph_id": {"type": "string"},
                        "segment_ordinal": {"type": "string"},
                        "raw_seed_anchor": {"type": "string"},
                        "raw_paragraph_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "clarified_statement": {"type": "string"},
                        "voice_anchor": {"type": "string"},
                        "support_excerpt": {"type": "string"},
                        "compression_ratio": {
                            "type": "number",
                            "minimum": 0.35,
                            "maximum": 0.95,
                        },
                        "distillation_confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "gestures_towards": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "compression_notes": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "notes": {
                "type": "object",
                "properties": {
                    "voice_signals": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "warnings": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "_summary": {
                "type": "object",
                "required": ["teleology", "outcome", "confidence"],
                "properties": {
                    "teleology": {"type": "string"},
                    "outcome": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["HIGH", "MEDIUM", "LOW"],
                    },
                },
            },
        },
    }


def _contextual_compression_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["contextual_rows", "_summary"],
        "properties": {
            "contextual_rows": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "row_id",
                        "profile_id",
                        "creator_skill_id",
                        "navigator_skill_id",
                        "band",
                        "source_ids",
                        "summary",
                        "drilldown_refs",
                        "dynamic_fact_rows",
                        "omission_receipt",
                    ],
                    "properties": {
                        "row_id": {"type": "string"},
                        "row_kind": {"type": "string"},
                        "profile_id": {"type": "string"},
                        "creator_skill_id": {"type": "string"},
                        "navigator_skill_id": {"type": "string"},
                        "skill_id": {"type": "string"},
                        "band": {
                            "type": "string",
                            "enum": ["flag", "card", "context", "deep"],
                        },
                        "source_ids": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                        "source_state": {
                            "type": "string",
                            "enum": ["paragraph_only", "sharded", "mixed", "unknown"],
                        },
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "covered_subclaims": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "band_reason": {"type": "string"},
                        "context_space_refs": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "context_horizon": {"type": "object"},
                        "drilldown_refs": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "dynamic_fact_rows": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "omission_receipt": {"type": "object"},
                        "navigation_use": {"type": "string"},
                        "next_moves": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "up_propagation_candidates": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "validation_notes": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "notes": {
                "type": "object",
                "properties": {
                    "warnings": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "omitted_bands": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "_summary": {
                "type": "object",
                "required": ["teleology", "outcome", "confidence"],
                "properties": {
                    "teleology": {"type": "string"},
                    "outcome": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["HIGH", "MEDIUM", "LOW"],
                    },
                },
            },
        },
    }


def _contextual_dispatch_policy(repo_root: Path) -> dict[str, Any]:
    try:
        template = load_mission_template(repo_root, CONTEXTUAL_MISSION_ID)
    except Exception:
        return _distillation_dispatch_policy(repo_root)
    policy = template.get("dispatch_policy")
    return dict(policy) if isinstance(policy, Mapping) else _distillation_dispatch_policy(repo_root)


def build_distillation_run_payload(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    limit: int | None = None,
    paragraph_ids: list[str] | None = None,
    mission_slug: str | None = None,
    provider: str = "chatgpt",
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    selection_mode: str = SELECTION_MODE_OLDEST_FIRST,
    output_root_rel: str = DEFAULT_OUTPUT_ROOT,
    dump_root_rel: str = DEFAULT_DUMP_ROOT,
    paragraphs_per_probe: int = 1,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    substrate_token = _string(substrate).strip() or "raw_seed"
    requested_cohort_size = max(1, int(limit if limit is not None else cohort_size))
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

    extracted = _load_json(repo_root / family_extracted_shards_path(family_dir)) or {"shards": []}
    existing_shards = [
        shard for shard in (extracted.get("shards") or []) if isinstance(shard, Mapping)
    ]
    selected = _select_paragraphs(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        existing_shards=existing_shards,
        cohort_size=requested_cohort_size,
        paragraph_ids=paragraph_ids,
        selection_mode=selection_mode,
    )

    default_slug = f"raw_seed_bridge_distillation_{family_token}_{_utc_stamp()}"
    resolved_slug = _slugify(mission_slug or default_slug, fallback=default_slug)
    run_root_rel = f"{output_root_rel.rstrip('/')}/{resolved_slug}"
    packet_root = repo_root / run_root_rel / "paragraph_packets"
    packet_root.mkdir(parents=True, exist_ok=True)

    all_paragraphs = [
        dict(paragraph)
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping)
    ]
    observed_at = _utc_now()
    total_atomized_parent_count = len(
        {
            _string(shard.get("parent_paragraph_id"))
            for shard in existing_shards
            if _string(shard.get("parent_paragraph_id"))
        }
    )
    source_paths = {
        "raw_seed_json_path": _seed_json_path_for_substrate(
            family_dir,
            substrate=substrate_token,
        ),
        "raw_seed_shards_path": raw_seed_shards_path_for_family(family_dir),
        "extracted_shards_path": family_extracted_shards_path(family_dir),
        "raw_seed_coverage_path": family_raw_seed_coverage_path(family_dir),
    }
    additional_context_files = _additional_context_files(repo_root, family_dir)
    paragraph_batches: list[dict[str, Any]] = []
    packet_manifest_rows: list[dict[str, Any]] = []
    paragraphs_per_probe_effective = max(1, int(paragraphs_per_probe or 1))
    if paragraphs_per_probe_effective == 1:
        for index, paragraph in enumerate(selected):
            paragraph_id = _string(paragraph.get("id"))
            packet_slug = _slugify(paragraph_id, fallback=f"paragraph_{index + 1:02d}")[:200]
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
                    selected_count=len(selected),
                    total_paragraph_count=len(all_paragraphs),
                    total_atomized_parent_count=total_atomized_parent_count,
                    source_paths=source_paths,
                    observed_at=observed_at,
                ),
            )
            packet_manifest_rows.append(
                {
                    "paragraph_id": paragraph_id,
                    "packet_path": packet_rel,
                    "neighbor_ids": [row["id"] for row in neighbors if _string(row.get("id"))],
                    "focus_text_length": len(_paragraph_text(paragraph)),
                }
            )
            paragraph_batches.append(
                {
                    "slug": packet_slug,
                    "notes": (
                        f"Index focus paragraph `{paragraph_id}` only. "
                        f"Neighbor paragraphs are context-only ({len(neighbors)} attached)."
                    ),
                    "question": (
                        f"Read the packet for `{paragraph_id}` and convert its focus paragraph into one "
                        "or more voice-preserving first-party source-index rows. Use neighbor context "
                        "only to clarify what the focus paragraph is gesturing toward."
                    ),
                    "acceptance": (
                        f"Return JSON only. Every row must keep `parent_paragraph_id` = `{paragraph_id}`, "
                        "use the legacy `shards[]` envelope, preserve voice, include the full voice envelope (`segment_ordinal`, `voice_anchor`, "
                        "`compression_ratio`, `distillation_confidence`, `gestures_towards`, "
                        "`compression_notes`), and avoid doctrine routing or system design. Do not claim "
                        "global row novelty or coverage from this packet-local view."
                    ),
                    "provider": provider,
                    "targets": [{"file": packet_rel, "scope": "full"}],
                    "context_files": list(additional_context_files),
                }
            )
    else:
        # Batch mode with FFD bin-packing.
        #
        # The naive fixed-N chunking (e.g. 6 paragraphs per probe) either
        # wastes bridge budget on small paragraphs (6 × 200 chars = 1.2k of
        # 50k budget used) or overflows it on large ones (6 × 10k = 60k >
        # 50k budget). First-Fit Decreasing packs by actual card size so
        # each probe approaches the ~50k paragraph payload budget without
        # exceeding it.
        #
        # Empirical gain (Family 09 backlog of 715): FFD produces ~18 probes
        # instead of 120 at fixed-6 — 6.7× fewer bridge round-trips.
        chunks = _bin_pack_paragraphs(
            selected,
            budget_chars=PARAGRAPH_BUDGET_PER_PROBE_CHARS,
            max_per_chunk=MAX_PARAGRAPHS_PER_PROBE,
        )
        for chunk_index, chunk in enumerate(chunks):
            chunk_paragraph_ids = [_string(paragraph.get("id")) for paragraph in chunk]
            chunk_paragraph_ids = [pid for pid in chunk_paragraph_ids if pid]
            first_id = chunk_paragraph_ids[0] if chunk_paragraph_ids else f"chunk_{chunk_index + 1:02d}"
            inner_slug = _slugify(first_id, fallback=f"packet_{chunk_index + 1:02d}")[:180]
            packet_slug = f"packet_{chunk_index + 1:02d}_{inner_slug}"
            packet_rel = f"{run_root_rel}/paragraph_packets/{chunk_index + 1:02d}_{packet_slug}.json"
            packet_path = repo_root / packet_rel
            _write_json(
                packet_path,
                _multi_paragraph_packet_payload(
                    family=family_token,
                    family_dir=family_dir,
                    focus_paragraphs=chunk,
                    selected_count=len(selected),
                    total_paragraph_count=len(all_paragraphs),
                    total_atomized_parent_count=total_atomized_parent_count,
                    source_paths=source_paths,
                    observed_at=observed_at,
                ),
            )
            for paragraph in chunk:
                paragraph_id = _string(paragraph.get("id"))
                packet_manifest_rows.append(
                    {
                        "paragraph_id": paragraph_id,
                        "packet_path": packet_rel,
                        "batch_slug": packet_slug,
                        "neighbor_ids": [],
                        "focus_text_length": len(_paragraph_text(paragraph)),
                    }
                )
            ids_joined = ", ".join(f"`{pid}`" for pid in chunk_paragraph_ids)
            paragraph_batches.append(
                {
                    "slug": packet_slug,
                    "notes": (
                        f"Index {len(chunk)} focus paragraphs in one bounded bridge packet. "
                        f"Each paragraph must yield its own rows tagged with its own "
                        f"`parent_paragraph_id`. Paragraph IDs: {ids_joined}."
                    ),
                    "question": (
                        f"Read the packet. It contains {len(chunk)} focus paragraphs "
                        f"({ids_joined}). Convert EACH one into one or more voice-preserving "
                        "first-party source-index rows. Do not skip any focus paragraph. Do not blend voices across "
                        "paragraphs. Output one legacy shards[] array carrying rows for ALL focus paragraphs, "
                        "in the order they appear in focus_paragraphs."
                    ),
                    "acceptance": (
                        "Return JSON only. The legacy shards[] array must include rows for every focus "
                        f"paragraph: {ids_joined}. Each row's `parent_paragraph_id` must match "
                        "one of the focus paragraph IDs. Preserve voice, include the full voice "
                        "envelope (`segment_ordinal`, `voice_anchor`, `compression_ratio`, "
                        "`distillation_confidence`, `gestures_towards`, `compression_notes`), "
                        "and avoid doctrine routing or system design. Use option-surface grouping "
                        "only as local continuity hints, never as route or coverage truth."
                    ),
                    "provider": provider,
                    "targets": [{"file": packet_rel, "scope": "full"}],
                    "context_files": list(additional_context_files),
                }
            )

    packet_manifest_rel = f"{run_root_rel}/paragraph_packets_manifest.json"
    _write_json(
        repo_root / packet_manifest_rel,
        {
            "kind": "raw_seed_distillation_packet_manifest",
            "schema_version": "raw_seed_distillation_packet_manifest_v1",
            "generated_at": _utc_now(),
            "family": family_token,
            "family_dir": family_dir,
            "substrate": substrate_token,
            "mission_slug": resolved_slug,
            "count": len(packet_manifest_rows),
            "packets": packet_manifest_rows,
        },
    )

    wave_resolution = _resolve_wave_width(
        repo_root=repo_root,
        provider=provider,
        requested_wave_width=DEFAULT_WAVE_WIDTH,
    )
    if _string(wave_resolution.get("status")) != "ok":
        raise ValueError(
            f"Default distillation wave width is invalid for provider {provider!r}: "
            f"{wave_resolution.get('error_code')}"
        )
    params = {
        "mission_slug": resolved_slug,
        "dump_dir": f"{dump_root_rel.rstrip('/')}/{resolved_slug}",
        "raw_seed_family": family_token,
        "compression_profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "provider_review_notice": PROVIDER_REVIEW_NOTICE,
        "legacy_schema_notice": LEGACY_SCHEMA_NOTICE,
        "goal_question": (
            f"How should the selected Family {family_token} owner-authored raw-seed paragraphs be "
            "converted into voice-preserving first-party source-index rows without routing or doctrine mutation?"
        ),
        "success_criteria": (
            "Each selected focus paragraph yields one or more canonical source-index rows with stable "
            "parent provenance, voice anchors, and no doctrine targets."
        ),
        "paragraph_batches": paragraph_batches,
        "distillation_response_schema": _distillation_response_schema(),
        "recommended_provider": provider,
        "recommended_wave_width": int(wave_resolution.get("effective_wave_width") or 1),
        "recommended_max_workers": int(wave_resolution.get("effective_wave_width") or 1),
        "dispatch_policy": _distillation_dispatch_policy(repo_root),
        "source_substrate": substrate_token,
    }
    return {
        "mission_id": MISSION_ID,
        "mission_slug": resolved_slug,
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "compression_profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "run_root": run_root_rel,
        "packet_manifest_path": packet_manifest_rel,
        "selected_paragraph_ids": [_string(paragraph.get("id")) for paragraph in selected],
        "cohort_size": requested_cohort_size,
        "selection_mode": _normalize_selection_mode(selection_mode, default=SELECTION_MODE_OLDEST_FIRST),
        "selected_count": len(selected),
        "wave_width_requested": DEFAULT_WAVE_WIDTH,
        "wave_width_effective": int(wave_resolution.get("effective_wave_width") or 1),
        "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
        "dispatch_policy": _distillation_dispatch_policy(repo_root),
        "selected_paragraphs": len(selected),
        "context_files": additional_context_files,
        "additional_context_files": additional_context_files,
        "provider": provider,
        "safe_parallelism": int(wave_resolution.get("provider_ceiling") or 0),
        "params": params,
    }


def materialize_distillation_mission(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    limit: int | None = None,
    paragraph_ids: list[str] | None = None,
    mission_slug: str | None = None,
    provider: str = "chatgpt",
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    selection_mode: str = SELECTION_MODE_OLDEST_FIRST,
    output_root_rel: str = DEFAULT_OUTPUT_ROOT,
    dump_root_rel: str = DEFAULT_DUMP_ROOT,
    paragraphs_per_probe: int = 1,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    payload = build_distillation_run_payload(
        family=family,
        repo_root=repo_root,
        cohort_size=cohort_size,
        limit=limit,
        paragraph_ids=paragraph_ids,
        mission_slug=mission_slug,
        provider=provider,
        context_window=context_window,
        selection_mode=selection_mode,
        output_root_rel=output_root_rel,
        dump_root_rel=dump_root_rel,
        paragraphs_per_probe=paragraphs_per_probe,
        substrate=substrate,
    )
    heartbeat_bundle = _controller_heartbeat_bundle(
        repo_root,
        family_dir=payload["family_dir"],
    )
    heartbeat_rel = f"{payload['run_root']}/controller_heartbeat.json"
    _write_json(
        repo_root / heartbeat_rel,
        heartbeat_bundle.get("controller_heartbeat") or {},
    )
    expansion = expand_mission_template(
        repo_root=repo_root,
        mission_id=MISSION_ID,
        params=payload["params"],
        family_context={
            "family_id": payload["family"],
            "family_dir": payload["family_dir"],
            "continuity": {
                "controller_heartbeat_path": heartbeat_rel,
                "controller_heartbeat_ref": heartbeat_bundle.get("controller_heartbeat_ref") or {},
                "path_refs": [
                    payload["packet_manifest_path"],
                    heartbeat_rel,
                    _string(heartbeat_bundle.get("autonomous_seed_path")),
                ],
            },
        },
    )
    run_root = repo_root / payload["run_root"]
    params_rel = f"{payload['run_root']}/mission_params.json"
    plan_rel = f"{payload['run_root']}/observe_session_plan.json"
    payload["controller_heartbeat_path"] = heartbeat_rel
    payload["controller_heartbeat_ref"] = heartbeat_bundle.get("controller_heartbeat_ref") or {}
    payload["params"]["controller_heartbeat_path"] = heartbeat_rel
    payload["params"]["controller_heartbeat_ref"] = heartbeat_bundle.get("controller_heartbeat_ref") or {}
    _write_json(repo_root / params_rel, payload["params"])
    _write_json(repo_root / plan_rel, expansion.plan)

    run_summary = {
        "status": "planned",
        "mission_id": expansion.mission_id,
        "mission_slug": payload["mission_slug"],
        "run_root": payload["run_root"],
        "template_path": expansion.template_path,
        "params_path": params_rel,
        "plan_path": plan_rel,
        "packet_manifest_path": payload["packet_manifest_path"],
        "dispatch_policy": dict(expansion.dispatch_policy),
        "cohort_size": payload["cohort_size"],
        "selection_mode": payload.get("selection_mode"),
        "selected_paragraph_ids": payload["selected_paragraph_ids"],
        "selected_count": payload["selected_count"],
        "wave_width_requested": payload["wave_width_requested"],
        "wave_width_effective": payload["wave_width_effective"],
        "provider_ceiling": payload["provider_ceiling"],
        "selected_paragraphs": payload["selected_paragraphs"],
        "provider": payload["provider"],
        "safe_parallelism": payload["safe_parallelism"],
        "family": payload["family"],
        "family_dir": payload["family_dir"],
        "substrate": payload.get("substrate") or "raw_seed",
        "controller_heartbeat_path": heartbeat_rel,
        "controller_heartbeat_ref": heartbeat_bundle.get("controller_heartbeat_ref") or {},
        "skill_files": list(expansion.skill_files),
        "shared_context_files": list(expansion.shared_context_files),
        "additional_context_files": list(payload.get("additional_context_files") or []),
        "effective_group_context_files": _dedupe_strings(
            [
                *list(expansion.injected_context_files),
                *list(payload.get("additional_context_files") or []),
            ]
        ),
        "review_commands": [
            (
                "./repo-python tools/meta/factory/raw_seed_pipeline.py "
                f"distill-run --run-root {payload['run_root']} --provider {payload['provider']}"
            ),
            (
                "./repo-python tools/meta/factory/raw_seed_pipeline.py "
                f"distill-import --family {payload['family']} --run-root {payload['run_root']} "
                f"--substrate {payload.get('substrate') or 'raw_seed'}"
            ),
        ],
    }
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def build_contextual_compression_run_payload(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    limit: int | None = None,
    paragraph_ids: list[str] | None = None,
    mission_slug: str | None = None,
    provider: str = "chatgpt",
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    selection_mode: str = SELECTION_MODE_OLDEST_FIRST,
    output_root_rel: str = DEFAULT_CONTEXTUAL_OUTPUT_ROOT,
    paragraphs_per_probe: int = DEFAULT_PARAGRAPHS_PER_PROBE,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    base_payload = build_distillation_run_payload(
        family=family,
        repo_root=repo_root,
        cohort_size=cohort_size,
        limit=limit,
        paragraph_ids=paragraph_ids,
        mission_slug=mission_slug,
        provider=provider,
        context_window=context_window,
        selection_mode=selection_mode,
        output_root_rel=output_root_rel,
        dump_root_rel=DEFAULT_DUMP_ROOT,
        paragraphs_per_probe=paragraphs_per_probe,
        substrate=substrate,
    )
    manifest = _load_json(repo_root / _string(base_payload.get("packet_manifest_path"))) or {}
    rows: list[dict[str, Any]] = []
    seen_packet_paths: set[str] = set()
    for index, packet_ref in enumerate(manifest.get("packets") or [], start=1):
        if not isinstance(packet_ref, Mapping):
            continue
        packet_rel = _string(packet_ref.get("packet_path"))
        if not packet_rel or packet_rel in seen_packet_paths:
            continue
        seen_packet_paths.add(packet_rel)
        packet_payload = _load_json(repo_root / packet_rel) if packet_rel else None
        if not isinstance(packet_payload, Mapping):
            continue
        packet_payload = _contextualize_packet_payload(
            packet_payload,
            repo_root=repo_root,
            family_dir=base_payload["family_dir"],
        )
        _write_json(repo_root / packet_rel, packet_payload)
        option_surface = dict(packet_payload.get("option_surface") or {})
        focus_ids = _focus_ids_from_packet_payload(packet_payload)
        contract = {
            "profile_id": packet_payload.get("profile_id") or option_surface.get("profile_id"),
            "creator_skill_id": packet_payload.get("creator_skill_id") or option_surface.get("creator_skill_id"),
            "navigator_skill_id": packet_payload.get("navigator_skill_id") or option_surface.get("navigator_skill_id"),
            "band": packet_payload.get("band") or option_surface.get("band") or "context",
            "source_state": packet_payload.get("source_state") or option_surface.get("source_state"),
            "band_reason": packet_payload.get("band_reason") or option_surface.get("band_reason"),
            "compression_profile": option_surface.get("compression_profile"),
            "context_horizon": option_surface.get("context_horizon"),
            "context_space_refs": packet_payload.get("context_space_refs") or option_surface.get("context_space_refs"),
            "drilldown_refs": packet_payload.get("drilldown_refs") or option_surface.get("drilldown_refs"),
            "dynamic_fact_rows": packet_payload.get("dynamic_fact_rows") or option_surface.get("dynamic_fact_rows"),
            "omission_receipt": packet_payload.get("omission_receipt") or option_surface.get("omission_receipt"),
        }
        grouping_rows = option_surface.get("focus_grouping_rows") or []
        title_parts = [
            _string(row.get("group_key"))
            for row in grouping_rows
            if isinstance(row, Mapping) and _string(row.get("group_key"))
        ]
        title = ", ".join(title_parts[:3]) or ", ".join(focus_ids[:3]) or f"raw seed contextual packet {index}"
        summary = (
            f"{len(focus_ids)} focus paragraph(s) compressed under "
            f"{contract.get('profile_id') or RAW_SEED_CONTEXT_PROFILE_ID}; navigation must use "
            f"{contract.get('navigator_skill_id') or 'raw_seed_navigation'} and drilldown refs before routing."
        )
        row = contextual_row_from_contract(
            row_id=f"rsc_{_stable_atom_id('_'.join(focus_ids) or packet_rel, str(index), title)}",
            source_ids=focus_ids,
            title=title,
            summary=summary,
            contract=contract,
        )
        row["source_packet_path"] = packet_rel
        row["packet_kind"] = packet_payload.get("kind")
        rows.append(row)

    output_rel = f"{base_payload['run_root']}/contextual_rows.json"
    projection_rel = f"{raw_seed_workspace_dir_for_family(base_payload['family_dir'])}/raw_seed_contextual_groups.json"
    contextual_payload = {
        "kind": "raw_seed_contextual_compression_run",
        "schema_version": "raw_seed_contextual_compression_run_v1",
        "generated_at": _utc_now(),
        "family": base_payload["family"],
        "family_dir": base_payload["family_dir"],
        "substrate": base_payload.get("substrate") or "raw_seed",
        "profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "source_run_root": base_payload["run_root"],
        "packet_manifest_path": base_payload["packet_manifest_path"],
        "contextual_row_count": len(rows),
        "rows": rows,
    }
    _write_json(repo_root / output_rel, contextual_payload)
    _write_json(repo_root / projection_rel, contextual_payload)
    contextual_batches: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        source_ids = [item for item in (row.get("source_ids") or []) if _string(item)]
        ids_joined = ", ".join(f"`{item}`" for item in source_ids)
        packet_rel = _string(row.get("source_packet_path"))
        batch_slug = f"context_{index:02d}_{_slugify(_string(row.get('row_id')) or str(index), fallback=str(index))}"
        contextual_batches.append(
            {
                "slug": batch_slug,
                "notes": (
                    "Create or refine profile-governed contextual compression rows over "
                    f"{len(source_ids)} source paragraph ids. Source ids: {ids_joined}."
                ),
                "question": (
                    "Read the target packet and the injected compression profile/skill. "
                    f"Produce contextual_rows[] under profile `{RAW_SEED_CONTEXT_PROFILE_ID}` "
                    "for the selected raw-seed source ids. These rows are higher-bracket "
                    "navigation/readings over paragraphs and shards, not replacement shards and "
                    "not doctrine routes. Preserve the declared drilldown_refs, dynamic_fact_rows, "
                    "omission_receipt, source_state, band_reason, and context_space_refs; improve "
                    "only the row summary/title/navigation_use when the packet gives enough evidence."
                ),
                "acceptance": (
                    "Return JSON only. Each contextual_rows[] item must carry `profile_id`, "
                    "`creator_skill_id`, `navigator_skill_id`, `band`, `source_ids`, "
                    "`source_state`, `band_reason`, `context_space_refs`, `drilldown_refs`, "
                    "`dynamic_fact_rows`, and `omission_receipt`. Do not emit shards, doctrine ids, "
                    "routing targets, or copied full ancestry. If the source packet is insufficient "
                    "for a band or context-space, say so in notes.omitted_bands or validation_notes "
                    "rather than inventing context."
                ),
                "provider": provider,
                "targets": [{"file": packet_rel, "scope": "full"}] if packet_rel else [],
                "context_files": [],
            }
        )

    contextual_policy = _contextual_dispatch_policy(repo_root)
    base_payload["mission_id"] = CONTEXTUAL_MISSION_ID
    base_payload["dispatch_policy"] = contextual_policy
    base_payload["params"] = {
        "mission_slug": base_payload["mission_slug"],
        "dump_dir": f"{DEFAULT_DUMP_ROOT.rstrip('/')}/{base_payload['mission_slug']}",
        "raw_seed_family": base_payload["family"],
        "compression_profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "goal_question": (
            f"How should selected Family {base_payload['family']} raw-seed paragraphs be "
            "represented as reversible profile-governed contextual compression rows?"
        ),
        "success_criteria": (
            "Each selected packet yields one or more contextual rows that preserve profile id, "
            "creator/navigator skill ids, band, source_state, band_reason, context_space_refs, "
            "drilldown refs, dynamic facts, and omission receipt, without mutating doctrine or "
            "replacing atomized shards."
        ),
        "contextual_batches": contextual_batches,
        "contextual_compression_response_schema": _contextual_compression_response_schema(),
        "grouping_policy": {
            "current_selector": base_payload.get("selection_mode"),
            "current_packing": (
                "Selected paragraphs are packetized through the existing paragraph bin-packer "
                "so bridge calls can carry more than one paragraph when the budget allows."
            ),
            "production_target": (
                "Use embedding/cosine neighbors to form semantically coherent candidate bins, "
                "then fit those bins chronologically into an adjustable bridge budget."
            ),
            "adaptive_budget_signal": [
                "contextual rows returned per packet",
                "json_validity",
                "source_state mix",
                "dynamic_fact/drilldown completeness",
                "operator inspection quality",
            ],
        },
        "recommended_provider": provider,
        "recommended_wave_width": int(base_payload.get("wave_width_effective") or 1),
        "recommended_max_workers": int(base_payload.get("wave_width_effective") or 1),
        "dispatch_policy": contextual_policy,
        "source_substrate": base_payload.get("substrate") or "raw_seed",
    }
    return {
        **base_payload,
        "kind": "raw_seed_contextual_compression",
        "status": "planned",
        "profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "contextual_rows_path": output_rel,
        "projection_path": projection_rel,
        "contextual_row_count": len(rows),
    }


def materialize_contextual_compression_mission(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_COHORT_SIZE,
    limit: int | None = None,
    paragraph_ids: list[str] | None = None,
    mission_slug: str | None = None,
    provider: str = "chatgpt",
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    selection_mode: str = SELECTION_MODE_OLDEST_FIRST,
    output_root_rel: str = DEFAULT_CONTEXTUAL_OUTPUT_ROOT,
    paragraphs_per_probe: int = DEFAULT_PARAGRAPHS_PER_PROBE,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    payload = build_contextual_compression_run_payload(
        family=family,
        repo_root=repo_root,
        cohort_size=cohort_size,
        limit=limit,
        paragraph_ids=paragraph_ids,
        mission_slug=mission_slug,
        provider=provider,
        context_window=context_window,
        selection_mode=selection_mode,
        output_root_rel=output_root_rel,
        paragraphs_per_probe=paragraphs_per_probe,
        substrate=substrate,
    )
    heartbeat_bundle = _controller_heartbeat_bundle(
        repo_root,
        family_dir=payload["family_dir"],
    )
    heartbeat_rel = f"{payload['run_root']}/controller_heartbeat.json"
    _write_json(
        repo_root / heartbeat_rel,
        heartbeat_bundle.get("controller_heartbeat") or {},
    )
    expansion = expand_mission_template(
        repo_root=repo_root,
        mission_id=CONTEXTUAL_MISSION_ID,
        params=payload["params"],
        family_context={
            "family_id": payload["family"],
            "family_dir": payload["family_dir"],
            "continuity": {
                "controller_heartbeat_path": heartbeat_rel,
                "controller_heartbeat_ref": heartbeat_bundle.get("controller_heartbeat_ref") or {},
                "path_refs": [
                    payload["packet_manifest_path"],
                    payload["contextual_rows_path"],
                    heartbeat_rel,
                    _string(heartbeat_bundle.get("autonomous_seed_path")),
                ],
            },
        },
    )
    run_root = repo_root / payload["run_root"]
    params_rel = f"{payload['run_root']}/mission_params.json"
    plan_rel = f"{payload['run_root']}/observe_session_plan.json"
    payload["controller_heartbeat_path"] = heartbeat_rel
    payload["controller_heartbeat_ref"] = heartbeat_bundle.get("controller_heartbeat_ref") or {}
    payload["params"]["controller_heartbeat_path"] = heartbeat_rel
    payload["params"]["controller_heartbeat_ref"] = heartbeat_bundle.get("controller_heartbeat_ref") or {}
    _write_json(repo_root / params_rel, payload["params"])
    _write_json(repo_root / plan_rel, expansion.plan)

    run_summary = {
        "status": "planned",
        "mission_id": expansion.mission_id,
        "mission_slug": payload["mission_slug"],
        "run_root": payload["run_root"],
        "template_path": expansion.template_path,
        "params_path": params_rel,
        "plan_path": plan_rel,
        "packet_manifest_path": payload["packet_manifest_path"],
        "contextual_rows_path": payload["contextual_rows_path"],
        "projection_path": payload["projection_path"],
        "dispatch_policy": dict(expansion.dispatch_policy),
        "cohort_size": payload["cohort_size"],
        "selection_mode": payload.get("selection_mode"),
        "selected_paragraph_ids": payload["selected_paragraph_ids"],
        "selected_count": payload["selected_count"],
        "wave_width_requested": payload["wave_width_requested"],
        "wave_width_effective": payload["wave_width_effective"],
        "provider_ceiling": payload["provider_ceiling"],
        "selected_paragraphs": payload["selected_paragraphs"],
        "provider": payload["provider"],
        "safe_parallelism": payload["safe_parallelism"],
        "family": payload["family"],
        "family_dir": payload["family_dir"],
        "substrate": payload.get("substrate") or "raw_seed",
        "controller_heartbeat_path": heartbeat_rel,
        "controller_heartbeat_ref": heartbeat_bundle.get("controller_heartbeat_ref") or {},
        "skill_files": list(expansion.skill_files),
        "shared_context_files": list(expansion.shared_context_files),
        "effective_group_context_files": list(expansion.injected_context_files),
        "review_commands": [
            (
                "./repo-python tools/meta/factory/raw_seed_pipeline.py "
                f"context-run --run-root {payload['run_root']} --provider {payload['provider']} "
                "--wave-width 1"
            ),
            (
                "./repo-python tools/meta/factory/raw_seed_pipeline.py "
                f"context-import --family {payload['family']} --run-root {payload['run_root']} "
                f"--substrate {payload.get('substrate') or 'raw_seed'}"
            ),
        ],
    }
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def run_distillation_mission(
    *,
    run_root: str | Path,
    repo_root: Path = REPO_ROOT,
    provider: str | None = None,
    wave_width: Any = DEFAULT_WAVE_WIDTH,
    max_workers: Any | None = None,
    timeout_s: float = 300.0,
    bridge_max_chars: int = 0,
    launch_profile: str = "experimental",
) -> dict[str, Any]:
    run_root_path = Path(run_root)
    if not run_root_path.is_absolute():
        run_root_path = (repo_root / run_root_path).resolve()
    params = _load_json(run_root_path / "mission_params.json")
    if not params:
        raise FileNotFoundError(f"mission_params.json missing in {run_root_path}")
    plan_path = run_root_path / "observe_session_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"observe_session_plan.json missing in {run_root_path}")

    resolved_provider = _string(provider).strip() or _string(params.get("recommended_provider")) or "chatgpt"
    requested_wave_width = wave_width
    if requested_wave_width in (None, "") and max_workers is not None:
        requested_wave_width = max_workers
    if requested_wave_width in (None, ""):
        requested_wave_width = DEFAULT_WAVE_WIDTH
    wave_resolution = _resolve_wave_width(
        repo_root=repo_root,
        provider=resolved_provider,
        requested_wave_width=requested_wave_width,
    )
    run_summary_path = run_root_path / "run_summary.json"
    run_summary = _load_json(run_summary_path) or {"status": "planned"}

    # Ledger seam: stamp canonical meta-mission workspace run.json/events.jsonl
    # when we own the lifecycle. Overnight chain runner parents already stamp
    # run.json=running before invoking us, so skip start_run/finalize_run in
    # that case to preserve their chain_ref and parent_run_id fields.
    run_id = run_root_path.name
    mission_entry = _mmw.resolve_mission_entry(repo_root, MISSION_ID)
    parent_owns = _parent_owns_ledger(repo_root, MISSION_ID, run_id)
    launcher_owns = _launcher_owns_ledger(run_id)
    owns_lifecycle = mission_entry is not None and not parent_owns and not launcher_owns
    if owns_lifecycle:
        try:
            _mmw.start_run(
                repo_root,
                mission_id=MISSION_ID,
                run_id=run_id,
                trigger="operator",
                provider=resolved_provider,
                dispatch_policy_resolved=_distillation_dispatch_policy(repo_root),
                selection_summary={
                    "family": _string(params.get("raw_seed_family")),
                    "mission_slug": _string(params.get("mission_slug")),
                    "requested_wave_width": requested_wave_width,
                },
                template_version=_string(mission_entry.get("template_version")) or None,
                notes=_string(params.get("goal_question")) or None,
            )
        except Exception:
            owns_lifecycle = False

    def _finalize(status: str, *, error: str | None = None, artifact_refs: list[str] | None = None) -> None:
        if not owns_lifecycle:
            return
        try:
            _mmw.finalize_run(
                repo_root,
                mission_id=MISSION_ID,
                run_id=run_id,
                status=status,
                error=error,
                artifact_refs=artifact_refs,
            )
        except Exception:
            pass

    if _string(wave_resolution.get("status")) != "ok":
        run_summary.update(
            {
                "status": "rejected",
                "ok": False,
                "provider": resolved_provider,
                "wave_width_requested": requested_wave_width,
                "wave_width_effective": None,
                "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
                "safe_parallelism": int(wave_resolution.get("provider_ceiling") or 0),
                "error_code": _string(wave_resolution.get("error_code")) or None,
                "error": (
                    f"wave_width {requested_wave_width} exceeds provider_ceiling "
                    f"{wave_resolution.get('provider_ceiling')} for provider '{resolved_provider}'"
                    if _string(wave_resolution.get("error_code")) == "wave_width_exceeds_provider_ceiling"
                    else "invalid wave_width request"
                ),
            }
        )
        _write_json(run_summary_path, run_summary)
        _finalize("failed", error=_string(run_summary.get("error")) or None)
        return run_summary

    try:
        summary = run_session_once(
            repo_root=repo_root,
            plan_path=plan_path,
            bridge_enabled=True,
            provider=resolved_provider,
            timeout_s=float(timeout_s),
            max_workers=int(wave_resolution.get("effective_wave_width") or 1),
            bridge_max_chars=int(bridge_max_chars),
            launch_profile=_string(launch_profile).strip() or "experimental",
            launch_metadata={"pid": None, "mission_id": MISSION_ID},
            resume_observe_id=None,
            retry_group_labels=None,
            run_kind="fresh",
        )
    except Exception as exc:
        _finalize("failed", error=str(exc))
        raise
    session_summary_rel = f"{run_root_path.relative_to(repo_root).as_posix()}/session_summary.json"
    _write_json(repo_root / session_summary_rel, summary)

    session_status = _string(summary.get("status")).lower()
    session_failed = session_status in {"error", "failed", "cancelled"}
    session_error = _string(summary.get("error")) or (
        f"Observe session ended with status '{session_status}' before emitting an importable distillation artifact."
        if session_failed
        else ""
    )

    run_summary.update(
        {
            "status": _string(summary.get("status")) or "completed",
            "ok": not session_failed,
            "provider": resolved_provider,
            "wave_width_requested": requested_wave_width,
            "wave_width_effective": int(summary.get("effective_workers") or wave_resolution.get("effective_wave_width") or 0),
            "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
            "safe_parallelism": int(wave_resolution.get("provider_ceiling") or 0),
            "effective_workers": int(summary.get("effective_workers") or 0),
            "session_summary_path": session_summary_rel,
            "session_manifest": _string(summary.get("session_manifest")) or None,
            "combined_json": _string(summary.get("combined_json")) or None,
            "combined_markdown": _string(summary.get("combined_markdown")) or None,
        }
    )
    if not session_failed:
        run_summary.pop("error", None)
        run_summary.pop("retryable", None)
    if session_error:
        run_summary["error"] = session_error
        run_summary["retryable"] = True

    if session_failed:
        _write_json(run_summary_path, run_summary)
        _finalize(
            "failed",
            error=session_error or None,
            artifact_refs=[session_summary_rel],
        )
        return run_summary

    try:
        artifact_paths = resolve_distillation_artifact_paths(
            repo_root=repo_root,
            run_root=run_root_path,
        )
    except FileNotFoundError as exc:
        run_summary.update(
            {
                "status": "error",
                "ok": False,
                "error": str(exc),
                "retryable": True,
            }
        )
        _write_json(run_summary_path, run_summary)
        _finalize(
            "failed",
            error=str(exc),
            artifact_refs=[session_summary_rel],
        )
        return run_summary

    run_summary["artifact_paths"] = [
        path.relative_to(repo_root).as_posix()
        for path in artifact_paths
        if path.is_relative_to(repo_root)
    ]
    _write_json(run_summary_path, run_summary)
    terminal_status = (
        "succeeded"
        if run_summary.get("ok") is not False
        and _string(run_summary.get("status")) not in {"rejected", "failed", "error", "cancelled"}
        else "failed"
    )
    _finalize(
        terminal_status,
        artifact_refs=[session_summary_rel],
    )
    return run_summary


def run_contextual_compression_mission(
    *,
    run_root: str | Path,
    repo_root: Path = REPO_ROOT,
    provider: str | None = None,
    wave_width: Any = DEFAULT_WAVE_WIDTH,
    max_workers: Any | None = None,
    timeout_s: float = 300.0,
    bridge_max_chars: int = 0,
    launch_profile: str = "experimental",
) -> dict[str, Any]:
    run_root_path = Path(run_root)
    if not run_root_path.is_absolute():
        run_root_path = (repo_root / run_root_path).resolve()
    params = _load_json(run_root_path / "mission_params.json")
    if not params:
        raise FileNotFoundError(f"mission_params.json missing in {run_root_path}")
    plan_path = run_root_path / "observe_session_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"observe_session_plan.json missing in {run_root_path}")

    resolved_provider = _string(provider).strip() or _string(params.get("recommended_provider")) or "chatgpt"
    requested_wave_width = wave_width
    if requested_wave_width in (None, "") and max_workers is not None:
        requested_wave_width = max_workers
    if requested_wave_width in (None, ""):
        requested_wave_width = DEFAULT_WAVE_WIDTH
    wave_resolution = _resolve_wave_width(
        repo_root=repo_root,
        provider=resolved_provider,
        requested_wave_width=requested_wave_width,
    )
    run_summary_path = run_root_path / "run_summary.json"
    run_summary = _load_json(run_summary_path) or {"status": "planned"}
    run_id = run_root_path.name
    mission_entry = _mmw.resolve_mission_entry(repo_root, CONTEXTUAL_MISSION_ID)
    parent_owns = _parent_owns_ledger(repo_root, CONTEXTUAL_MISSION_ID, run_id)
    launcher_owns = _launcher_owns_ledger(run_id)
    owns_lifecycle = mission_entry is not None and not parent_owns and not launcher_owns
    if owns_lifecycle:
        try:
            _mmw.start_run(
                repo_root,
                mission_id=CONTEXTUAL_MISSION_ID,
                run_id=run_id,
                trigger="operator",
                provider=resolved_provider,
                dispatch_policy_resolved=_contextual_dispatch_policy(repo_root),
                selection_summary={
                    "family": _string(params.get("raw_seed_family")),
                    "mission_slug": _string(params.get("mission_slug")),
                    "requested_wave_width": requested_wave_width,
                },
                template_version=_string(mission_entry.get("template_version")) or None,
                notes=_string(params.get("goal_question")) or None,
            )
        except Exception:
            owns_lifecycle = False

    def _finalize(status: str, *, error: str | None = None, artifact_refs: list[str] | None = None) -> None:
        if not owns_lifecycle:
            return
        try:
            _mmw.finalize_run(
                repo_root,
                mission_id=CONTEXTUAL_MISSION_ID,
                run_id=run_id,
                status=status,
                error=error,
                artifact_refs=artifact_refs,
            )
        except Exception:
            pass

    if _string(wave_resolution.get("status")) != "ok":
        run_summary.update(
            {
                "status": "rejected",
                "ok": False,
                "provider": resolved_provider,
                "wave_width_requested": requested_wave_width,
                "wave_width_effective": None,
                "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
                "safe_parallelism": int(wave_resolution.get("provider_ceiling") or 0),
                "error_code": _string(wave_resolution.get("error_code")) or None,
                "error": "invalid wave_width request",
            }
        )
        _write_json(run_summary_path, run_summary)
        _finalize("failed", error=_string(run_summary.get("error")) or None)
        return run_summary

    try:
        summary = run_session_once(
            repo_root=repo_root,
            plan_path=plan_path,
            bridge_enabled=True,
            provider=resolved_provider,
            timeout_s=float(timeout_s),
            max_workers=int(wave_resolution.get("effective_wave_width") or 1),
            bridge_max_chars=int(bridge_max_chars),
            launch_profile=_string(launch_profile).strip() or "experimental",
            launch_metadata={"pid": None, "mission_id": CONTEXTUAL_MISSION_ID},
            resume_observe_id=None,
            retry_group_labels=None,
            run_kind="fresh",
        )
    except Exception as exc:
        _finalize("failed", error=str(exc))
        raise

    session_summary_rel = f"{run_root_path.relative_to(repo_root).as_posix()}/session_summary.json"
    _write_json(repo_root / session_summary_rel, summary)
    session_status = _string(summary.get("status")).lower()
    session_failed = session_status in {"error", "failed", "cancelled"}
    session_error = _string(summary.get("error")) or (
        f"Observe session ended with status '{session_status}' before emitting contextual rows."
        if session_failed
        else ""
    )
    run_summary.update(
        {
            "status": _string(summary.get("status")) or "completed",
            "ok": not session_failed,
            "provider": resolved_provider,
            "wave_width_requested": requested_wave_width,
            "wave_width_effective": int(summary.get("effective_workers") or wave_resolution.get("effective_wave_width") or 0),
            "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
            "safe_parallelism": int(wave_resolution.get("provider_ceiling") or 0),
            "effective_workers": int(summary.get("effective_workers") or 0),
            "session_summary_path": session_summary_rel,
            "session_manifest": _string(summary.get("session_manifest")) or None,
            "combined_json": _string(summary.get("combined_json")) or None,
            "combined_markdown": _string(summary.get("combined_markdown")) or None,
        }
    )
    if not session_failed:
        run_summary.pop("error", None)
        run_summary.pop("retryable", None)
    if session_error:
        run_summary["error"] = session_error
        run_summary["retryable"] = True

    if session_failed:
        _write_json(run_summary_path, run_summary)
        _finalize("failed", error=session_error or None, artifact_refs=[session_summary_rel])
        return run_summary

    try:
        artifact_paths = resolve_contextual_artifact_paths(
            repo_root=repo_root,
            run_root=run_root_path,
        )
    except FileNotFoundError as exc:
        run_summary.update(
            {
                "status": "error",
                "ok": False,
                "error": str(exc),
                "retryable": True,
            }
        )
        _write_json(run_summary_path, run_summary)
        _finalize("failed", error=str(exc), artifact_refs=[session_summary_rel])
        return run_summary

    run_summary["artifact_paths"] = [
        path.relative_to(repo_root).as_posix()
        for path in artifact_paths
        if path.is_relative_to(repo_root)
    ]
    _write_json(run_summary_path, run_summary)
    terminal_status = (
        "succeeded"
        if run_summary.get("ok") is not False
        and _string(run_summary.get("status")) not in {"rejected", "failed", "error", "cancelled"}
        else "failed"
    )
    _finalize(terminal_status, artifact_refs=[session_summary_rel])
    return run_summary


def _direct_bridge_group_label(group: Mapping[str, Any], index: int) -> str:
    return _slugify(_string(group.get("label")), fallback=f"group_{index + 1:02d}")


def _read_prompt_file(repo_root: Path, rel_path: str) -> str:
    path = repo_root / rel_path
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"[UNREADABLE: {exc}]"


def _direct_bridge_prompt(
    *,
    repo_root: Path,
    plan: Mapping[str, Any],
    group: Mapping[str, Any],
) -> str:
    label = _string(group.get("label"))
    context_files = [
        _string(item).strip()
        for item in (group.get("context_files") or [])
        if _string(item).strip()
    ]
    targets = [
        item
        for item in (group.get("targets") or [])
        if isinstance(item, Mapping) and _string(item.get("file")).strip()
    ]
    response_schema = group.get("response_schema") if isinstance(group.get("response_schema"), Mapping) else {}
    display_label = label
    if display_label.lower().startswith("distill_"):
        display_label = "source_index_" + display_label[len("distill_") :]
    raw_role = _string(group.get("role")).strip() or _string(group.get("use")).strip()
    display_role = raw_role or "source_indexing"
    if "probe" in display_role.lower():
        display_role = "source_indexing"
    parts = [
        "# First-Party Raw-Seed Source Indexing Job",
        "",
        "Return JSON only. Do not include markdown fences or commentary.",
        "",
        "## Provider Review Notice",
        PROVIDER_REVIEW_NOTICE,
        "",
        "## Compatibility Note",
        LEGACY_SCHEMA_NOTICE,
        "",
        "## Goal",
        _string(plan.get("goal_question")) or (
            "Convert owner-authored raw-seed paragraph packets into voice-preserving "
            "first-party source-index rows."
        ),
        "",
        "## Group",
        f"label: {display_label}",
        f"role: {display_role}",
        "",
        "## Question",
        _string(group.get("question")),
        "",
        "## Acceptance",
        _string(group.get("acceptance")),
        "",
        "## Required Response Schema",
        json.dumps(response_schema, indent=2, ensure_ascii=False),
        "",
        "## Injected Context",
    ]
    for rel_path in context_files:
        parts.extend(
            [
                "",
                f"### FILE: {rel_path}",
                "```text",
                _read_prompt_file(repo_root, rel_path),
                "```",
            ]
        )
    parts.extend(["", "## Target Packet(s)"])
    for target in targets:
        rel_path = _string(target.get("file")).strip()
        parts.extend(
            [
                "",
                f"### TARGET: {rel_path}",
                "```json",
                _read_prompt_file(repo_root, rel_path),
                "```",
            ]
        )
    parts.extend(
        [
            "",
            "## Final Instruction",
            "Read provider_review_notice, legacy_schema_notice, and option_surface first. "
            "Emit rows only for allowed focus paragraph ids. Use the legacy JSON envelope "
            "required by the local importer and return it exactly.",
        ]
    )
    return "\n".join(parts).strip() + "\n"


def _direct_bridge_parse_response(response_text: str) -> dict[str, Any]:
    try:
        payload = extract_json_object(response_text)
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        return payload
    return {
        "payload": {
            "shards": [],
            "notes": {
                "warnings": ["bridge_response_json_parse_failed"],
                "raw_response_preview": response_text[:2000],
            },
            "_summary": {
                "teleology": "Bridge response could not be parsed as JSON.",
                "outcome": "No importable shards recovered.",
                "confidence": "LOW",
            },
        }
    }


def run_distillation_mission_direct_bridge(
    *,
    run_root: str | Path,
    repo_root: Path = REPO_ROOT,
    provider: str | None = None,
    wave_width: Any = DEFAULT_WAVE_WIDTH,
    max_workers: Any | None = None,
    timeout_s: float = 300.0,
    launch_profile: str = "experimental",
) -> dict[str, Any]:
    """Run raw-seed distillation packets through Bridge without observe-session dispatch.

    This is a mission-specific fallback for the raw-seed distillation lane. It keeps
    the authored mission packets, compact injected skills, response schema, Bridge
    provider, and import artifact contract, but bypasses the currently fragile
    observe-session handoff when that runtime wedges before provider selection.
    """

    run_root_path = Path(run_root)
    if not run_root_path.is_absolute():
        run_root_path = (repo_root / run_root_path).resolve()
    params = _load_json(run_root_path / "mission_params.json")
    if not params:
        raise FileNotFoundError(f"mission_params.json missing in {run_root_path}")
    plan_path = run_root_path / "observe_session_plan.json"
    plan = _load_json(plan_path)
    if not plan:
        raise FileNotFoundError(f"observe_session_plan.json missing in {run_root_path}")
    groups = [row for row in (plan.get("groups") or []) if isinstance(row, Mapping)]
    if not groups:
        raise ValueError(f"No groups found in {plan_path}")

    resolved_provider = _string(provider).strip() or _string(params.get("recommended_provider")) or "chatgpt"
    requested_wave_width = wave_width
    if requested_wave_width in (None, "") and max_workers is not None:
        requested_wave_width = max_workers
    if requested_wave_width in (None, ""):
        requested_wave_width = DEFAULT_WAVE_WIDTH
    wave_resolution = _resolve_wave_width(
        repo_root=repo_root,
        provider=resolved_provider,
        requested_wave_width=requested_wave_width,
    )
    if _string(wave_resolution.get("status")) != "ok":
        return {
            "status": "rejected",
            "ok": False,
            "provider": resolved_provider,
            "error_code": _string(wave_resolution.get("error_code")) or None,
            "error": "invalid wave_width request",
            "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
        }

    dump_dir = _string(params.get("dump_dir"))
    if not dump_dir:
        raise ValueError(f"Mission params in {run_root_path} do not declare dump_dir.")
    dump_root = repo_root / dump_dir
    dump_root.mkdir(parents=True, exist_ok=True)
    observe_id = f"DIRECT_RAW_SEED_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{run_root_path.name}"
    run_summary_path = run_root_path / "run_summary.json"
    run_summary = _load_json(run_summary_path) or {"status": "planned"}
    response_files: list[str] = []
    failures: list[dict[str, Any]] = []
    skipped_existing_count = 0

    def _dispatch(index_group: tuple[int, Mapping[str, Any]]) -> dict[str, Any]:
        index, group = index_group
        label_slug = _direct_bridge_group_label(group, index)
        surface_path = dump_root / f"{index + 1:02d}_{label_slug}_response.surface.json"
        existing_surface = _load_json(surface_path)
        existing_payload_ok = False
        if isinstance(existing_surface, Mapping):
            try:
                existing_distillation_payload = _extract_distillation_payload(existing_surface)
            except ValueError:
                existing_distillation_payload = {}
            existing_payload_ok = bool(existing_distillation_payload.get("shards"))
        if existing_payload_ok:
            return {"ok": True, "artifact": surface_path.relative_to(repo_root).as_posix(), "skipped_existing": True}
        prompt = _direct_bridge_prompt(repo_root=repo_root, plan=plan, group=group)
        prompt_path = dump_root / f"{index + 1:02d}_{label_slug}_direct_prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        merged_config, _route_name = merge_bridge_config_with_route(
            load_master_config(repo_root),
            explicit_route="kernel_probe",
        )
        bridge_cfg = dict(merged_config.get("bridge") if isinstance(merged_config.get("bridge"), Mapping) else {})
        bridge_cfg["default_target"] = resolved_provider
        bridge_cfg["monitor_timeout_s"] = float(timeout_s)
        meta = dict(bridge_cfg.get("meta") if isinstance(bridge_cfg.get("meta"), Mapping) else {})
        meta.update(
            {
                "session_id": observe_id,
                "node_id": _string(group.get("label")) or label_slug,
                "lane": "raw_seed_direct_distill",
                "run_kind": "fresh",
                "launch_profile": _string(launch_profile).strip() or "experimental",
            }
        )
        bridge_cfg["meta"] = meta
        config = {
            **dict(merged_config),
            "bridge": bridge_cfg,
            "platform": resolved_provider,
            "meta": meta,
        }
        from system.core.bridge import ask_ai

        started_at = _utc_now()
        try:
            response_text = ask_ai(prompt, config=config)
        except Exception as exc:
            error_payload = {
                "label": _string(group.get("label")) or label_slug,
                "status": "error",
                "error": str(exc),
                "started_at": started_at,
                "finished_at": _utc_now(),
                "prompt_path": prompt_path.relative_to(repo_root).as_posix(),
            }
            error_path = dump_root / f"{index + 1:02d}_{label_slug}_response.error.json"
            _write_json(error_path, error_payload)
            return {"ok": False, "error": error_payload}
        response_md_path = dump_root / f"{index + 1:02d}_{label_slug}_response.md"
        response_md_path.write_text(response_text, encoding="utf-8")
        parsed_payload = _direct_bridge_parse_response(response_text)
        surface_payload = {
            "source_kind": "raw_seed_direct_bridge_response",
            "label": _string(group.get("label")) or label_slug,
            "provider": resolved_provider,
            "observe_id": observe_id,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "prompt_path": prompt_path.relative_to(repo_root).as_posix(),
            "response_markdown_path": response_md_path.relative_to(repo_root).as_posix(),
            "payload": parsed_payload.get("payload") if isinstance(parsed_payload.get("payload"), Mapping) else parsed_payload,
            "heartbeat_ref": parsed_payload.get("heartbeat_ref") if isinstance(parsed_payload.get("heartbeat_ref"), Mapping) else {},
        }
        _write_json(surface_path, surface_payload)
        return {"ok": True, "artifact": surface_path.relative_to(repo_root).as_posix()}

    effective_workers = int(wave_resolution.get("effective_wave_width") or 1)
    indexed_groups = list(enumerate(groups))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, effective_workers)) as executor:
        for result in executor.map(_dispatch, indexed_groups):
            if result.get("ok"):
                response_files.append(_string(result.get("artifact")))
                if result.get("skipped_existing"):
                    skipped_existing_count += 1
            else:
                error = result.get("error")
                if isinstance(error, Mapping):
                    failures.append(dict(error))

    status = "completed" if response_files and not failures else "partial" if response_files else "error"
    run_summary.update(
        {
            "status": status,
            "ok": bool(response_files),
            "provider": resolved_provider,
            "runner": "direct_bridge",
            "observe_id": observe_id,
            "wave_width_requested": requested_wave_width,
            "wave_width_effective": effective_workers,
            "provider_ceiling": int(wave_resolution.get("provider_ceiling") or 0),
            "effective_workers": effective_workers,
            "artifact_paths": response_files,
            "skipped_existing_artifacts": skipped_existing_count,
            "failure_count": len(failures),
            "failures": failures,
        }
    )
    if failures and not response_files:
        run_summary["error"] = failures[0].get("error") if failures else "direct bridge run failed"
        run_summary["retryable"] = True
    else:
        run_summary.pop("error", None)
        run_summary.pop("retryable", None)
    _write_json(run_summary_path, run_summary)
    return run_summary


def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    ordered: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def _probe_response_base(path: Path) -> str:
    name = path.name
    for suffix in ("_response.surface.json", "_response.receipt.json", "_response.md"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _probe_response_rank(path: Path) -> int:
    name = path.name
    if name.endswith("_response.surface.json"):
        return 0
    if name.endswith("_response.receipt.json"):
        return 1
    if name.endswith("_response.md"):
        return 2
    return 9


def _prefer_structured_probe_artifacts(paths: Iterable[Path]) -> list[Path]:
    """Keep one response artifact per probe, preferring typed JSON over markdown."""
    selected: dict[str, Path] = {}
    for path in _dedupe_paths(paths):
        base = _probe_response_base(path)
        current = selected.get(base)
        if current is None or _probe_response_rank(path) < _probe_response_rank(current):
            selected[base] = path
    return [selected[key] for key in sorted(selected)]


def _resolve_probe_artifacts_from_session_manifest(
    *,
    repo_root: Path,
    run_root_path: Path,
) -> list[Path]:
    manifest_path = run_root_path / "session_summary.json"
    manifest_payload = _load_json(manifest_path) or {}
    session_manifest_rel = _string(manifest_payload.get("session_manifest"))
    if not session_manifest_rel:
        return []
    session_manifest_path = (repo_root / session_manifest_rel).resolve()
    session_manifest = _load_json(session_manifest_path) or {}
    response_index = (
        session_manifest.get("response_index")
        if isinstance(session_manifest.get("response_index"), list)
        else []
    )
    artifacts: list[Path] = []
    for item in response_index:
        if not isinstance(item, Mapping):
            continue
        if _string(item.get("role")) != "probe":
            continue
        for key in ("response_receipt_file", "response_surface_file", "artifact_path", "response_file"):
            token = _string(item.get(key)).strip()
            if not token:
                continue
            candidate = (repo_root / token).resolve()
            if candidate.exists():
                artifacts.append(candidate)
                break
    return _dedupe_paths(artifacts)


def resolve_distillation_artifact_paths(
    *,
    repo_root: Path = REPO_ROOT,
    run_root: str | Path | None = None,
    artifact_path: str | Path | None = None,
) -> list[Path]:
    if artifact_path is not None:
        candidate = Path(artifact_path)
        if not candidate.is_absolute():
            candidate = (repo_root / candidate).resolve()
        if candidate.exists():
            return [candidate]
        raise FileNotFoundError(f"Distillation artifact not found: {candidate}")

    if run_root is None:
        raise ValueError("Provide either run_root or artifact_path.")

    run_root_path = Path(run_root)
    if not run_root_path.is_absolute():
        run_root_path = (repo_root / run_root_path).resolve()
    params = _load_json(run_root_path / "mission_params.json")
    if not params:
        raise FileNotFoundError(f"mission_params.json missing in {run_root_path}")
    dump_dir = _string(params.get("dump_dir"))
    if not dump_dir:
        raise ValueError(f"Mission params in {run_root_path} do not declare dump_dir.")
    dump_root = (repo_root / dump_dir).resolve()
    if not dump_root.exists():
        raise FileNotFoundError(f"Observe dump dir not found: {dump_root}")

    manifest_artifacts = _resolve_probe_artifacts_from_session_manifest(
        repo_root=repo_root,
        run_root_path=run_root_path,
    )
    if manifest_artifacts:
        return manifest_artifacts

    probe_patterns = [
        "*_response.receipt.json",
        "*_response.surface.json",
        "*_response.md",
    ]
    probe_artifacts: list[Path] = []
    for pattern in probe_patterns:
        probe_artifacts.extend(sorted(dump_root.glob(pattern)))
    probe_artifacts = [
        path
        for path in _prefer_structured_probe_artifacts(probe_artifacts)
        if not path.name.startswith("_")
    ]
    if probe_artifacts:
        return probe_artifacts

    compatibility_patterns = [
        "_synthesis.surface.json",
        "_synthesis.json",
        "*synthesis*_response.surface.json",
        "*distillation_merge*_response.surface.json",
        "*merge*_response.surface.json",
        "*response.surface.json",
        "_synthesis.md",
        "*synthesis*.md",
        "_combined.json",
        "_combined.md",
    ]
    for pattern in compatibility_patterns:
        matches = sorted(dump_root.glob(pattern))
        if matches:
            return [matches[-1].resolve()]
    raise FileNotFoundError(
        "No distillation artifact found under "
        f"{dump_root}; expected probe response artifacts or a legacy synthesis surface."
    )


def resolve_distillation_artifact_path(
    *,
    repo_root: Path = REPO_ROOT,
    run_root: str | Path | None = None,
    artifact_path: str | Path | None = None,
) -> Path:
    return resolve_distillation_artifact_paths(
        repo_root=repo_root,
        run_root=run_root,
        artifact_path=artifact_path,
    )[-1]


def resolve_contextual_artifact_paths(
    *,
    repo_root: Path = REPO_ROOT,
    run_root: str | Path | None = None,
    artifact_path: str | Path | None = None,
) -> list[Path]:
    return resolve_distillation_artifact_paths(
        repo_root=repo_root,
        run_root=run_root,
        artifact_path=artifact_path,
    )


def import_contextual_compression_rows(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    run_root: str | Path | None = None,
    artifact_path: str | Path | None = None,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    substrate_token = _string(substrate).strip() or "raw_seed"
    artifacts = resolve_contextual_artifact_paths(
        repo_root=repo_root,
        run_root=run_root,
        artifact_path=artifact_path,
    )
    source_run_root = None
    if run_root is not None:
        run_root_path = Path(run_root)
        if not run_root_path.is_absolute():
            run_root_path = (repo_root / run_root_path).resolve()
        try:
            source_run_root = run_root_path.relative_to(repo_root).as_posix()
        except ValueError:
            source_run_root = run_root_path.as_posix()

    artifact_paths_rel: list[str] = []
    skipped_artifacts: list[dict[str, str]] = []
    normalized_rows: list[dict[str, Any]] = []
    imported_at = _utc_now()
    for artifact in artifacts:
        source_artifact_rel = artifact.resolve().relative_to(repo_root.resolve()).as_posix()
        payload = _load_contextual_artifact_payload(artifact)
        if not payload:
            skipped_artifacts.append({"artifact": source_artifact_rel, "reason": "unloadable"})
            continue
        try:
            contextual_payload = _extract_contextual_payload(payload)
        except ValueError as exc:
            skipped_artifacts.append({"artifact": source_artifact_rel, "reason": str(exc)})
            continue
        artifact_paths_rel.append(source_artifact_rel)
        normalized_rows.extend(
            _normalize_contextual_compression_rows(
                rows_payload=contextual_payload,
                source_artifact_rel=source_artifact_rel,
                source_run_root=source_run_root,
                imported_at=imported_at,
            )
        )

    if not normalized_rows:
        raise ValueError(
            "No contextual compression rows could be built from "
            f"{', '.join(artifact_paths_rel or [path.relative_to(repo_root).as_posix() for path in artifacts])}"
        )

    unique_rows = _dedupe_contextual_rows(normalized_rows)
    projection_rel = f"{raw_seed_workspace_dir_for_family(family_dir)}/raw_seed_contextual_groups.json"
    projection_path = repo_root / projection_rel
    existing_payload = _load_json(projection_path) or {
        "kind": "raw_seed_contextual_compression_run",
        "schema_version": "raw_seed_contextual_compression_run_v1",
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "rows": [],
    }
    existing_rows = [
        dict(row)
        for row in (existing_payload.get("rows") or [])
        if isinstance(row, Mapping)
    ]
    replacement_ids = {_string(row.get("row_id")) for row in unique_rows if _string(row.get("row_id"))}
    kept_rows = [
        row for row in existing_rows if _string(row.get("row_id")) not in replacement_ids
    ]
    merged_rows = _dedupe_contextual_rows([*kept_rows, *unique_rows])
    source_id_count = len(
        {
            source_id
            for row in unique_rows
            for source_id in _string_list(row.get("source_ids"))
        }
    )
    next_payload = {
        **dict(existing_payload),
        "kind": "raw_seed_contextual_compression_run",
        "schema_version": "raw_seed_contextual_compression_run_v1",
        "generated_at": imported_at,
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "source_run_root": source_run_root,
        "imported_artifacts": artifact_paths_rel,
        "contextual_row_count": len(merged_rows),
        "rows": merged_rows,
        "import_summary": {
            "imported_rows": len(unique_rows),
            "touched_source_ids": source_id_count,
            "skipped_artifacts": skipped_artifacts,
            "compression_source": CONTEXTUAL_COMPRESSION_SOURCE,
        },
    }
    _write_json(projection_path, next_payload)
    if run_root is not None:
        run_root_path = Path(run_root)
        if not run_root_path.is_absolute():
            run_root_path = (repo_root / run_root_path).resolve()
        run_summary_path = run_root_path / "run_summary.json"
        run_summary = _load_json(run_summary_path) or {}
        run_summary["contextual_import_summary"] = next_payload["import_summary"]
        run_summary["projection_path"] = projection_rel
        _write_json(run_summary_path, run_summary)
    return {
        "status": "imported",
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
        "projection_path": projection_rel,
        "imported_rows": len(unique_rows),
        "merged_row_count": len(merged_rows),
        "touched_source_ids": source_id_count,
        "artifact_paths": artifact_paths_rel,
        "skipped_artifacts": skipped_artifacts,
    }


def _confidence_score(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    token = _string(value).strip().upper()
    if token == "HIGH":
        return 0.95
    if token == "MEDIUM":
        return 0.75
    if token == "LOW":
        return 0.5
    return None


def _canonical_shards_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    summary_fields = payload.get("summary_fields")
    summary = summary_fields if isinstance(summary_fields, Mapping) else {}
    confidence = _string(summary.get("synthesis_confidence")).strip().upper() or "MEDIUM"
    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        confidence = "MEDIUM"
    shards: list[dict[str, Any]] = []
    for row in payload.get("canonical_shards") or []:
        if not isinstance(row, Mapping):
            continue
        parent_paragraph_id = _string(row.get("parent_paragraph_id")).strip() or _string(
            row.get("authority_boundary")
        ).strip()
        if not parent_paragraph_id:
            continue
        evidence = [
            _string(item)
            for item in (row.get("evidence") or [])
            if _string(item).strip()
        ]
        flags = [
            _string(item)
            for item in (row.get("flags") or [])
            if _string(item).strip()
        ]
        shards.append(
            {
                "id": _string(row.get("id")).strip(),
                "parent_paragraph_id": parent_paragraph_id,
                "segment_ordinal": _string(row.get("segment_ordinal")).strip(),
                "raw_seed_anchor": _string(row.get("raw_seed_anchor")).strip()
                or f"paragraph:{parent_paragraph_id}",
                "raw_paragraph_ids": [
                    _string(item)
                    for item in (row.get("raw_paragraph_ids") or [parent_paragraph_id])
                    if _string(item).strip()
                ]
                or [parent_paragraph_id],
                "clarified_statement": _string(row.get("clarified_statement")).strip()
                or _string(row.get("canonical_statement")).strip(),
                "voice_anchor": _string(row.get("voice_anchor")).strip(),
                "support_excerpt": evidence[0] if evidence else "",
                "distillation_confidence": _confidence_score(
                    row.get("distillation_confidence") or confidence
                ),
                "gestures_towards": list(flags),
                "compression_notes": ["canonical_synthesis_markdown_recovered_v1"],
            }
        )
    return {
        "shards": shards,
        "_summary": {
            "teleology": "Recovered canonical shard rows from synthesis markdown.",
            "outcome": (
                f"Import {len(shards)} shard row(s) across "
                f"{len({row.get('parent_paragraph_id') for row in shards if row.get('parent_paragraph_id')})} "
                "parent paragraph(s)."
            ),
            "confidence": confidence,
        },
    }


def _extract_distillation_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "shards" in payload and isinstance(payload.get("shards"), list):
        return dict(payload)
    if "canonical_shards" in payload and isinstance(payload.get("canonical_shards"), list):
        return _canonical_shards_payload(payload)
    nested = payload.get("payload")
    if isinstance(nested, Mapping):
        return _extract_distillation_payload(nested)
    for key in ("data", "response", "result"):
        nested_payload = payload.get(key)
        if isinstance(nested_payload, Mapping):
            extracted = _extract_distillation_payload(nested_payload)
            if extracted:
                return extracted
    if "parent_paragraph_id" in payload and "clarified_statement" in payload:
        return {"shards": [dict(payload)]}
    raise ValueError("Could not find a distillation payload with `shards` in the supplied artifact.")


def _authority_parent_ids_from_payload(payload: Mapping[str, Any]) -> set[str]:
    discovered: set[str] = set()

    def visit(value: Any, *, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(value, Mapping):
            option_surface = value.get("option_surface")
            if isinstance(option_surface, Mapping):
                authority = option_surface.get("authority_boundary")
                if isinstance(authority, Mapping):
                    discovered.update(_string_list(authority.get("emit_shards_for")))
            discovered.update(_string_list(value.get("focus_paragraph_ids")))
            focus_paragraph = value.get("focus_paragraph")
            if isinstance(focus_paragraph, Mapping):
                discovered.add(_string(focus_paragraph.get("id")))
            focus_paragraphs = value.get("focus_paragraphs")
            if isinstance(focus_paragraphs, list):
                for paragraph in focus_paragraphs:
                    if isinstance(paragraph, Mapping):
                        discovered.add(_string(paragraph.get("id")))
            for key in ("payload", "data", "response", "result", "packet", "context", "observations"):
                nested = value.get(key)
                if isinstance(nested, (Mapping, list)):
                    visit(nested, depth=depth + 1)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (Mapping, list)):
                    visit(item, depth=depth + 1)

    visit(payload)
    return {_string(parent_id) for parent_id in discovered if _string(parent_id)}


_VOICE_ANCHOR_MARKUP_RE = re.compile(r"[`*_~]+")


def _voice_anchor_normalize(text: str) -> str:
    """Normalize text for voice-anchor traceability comparison.

    The model can drop markdown markup (backticks around `reference.md`,
    italic underscores, etc.) while still reproducing voice verbatim. Treat
    those characters as equivalent to absence so a voice_preserving response
    is not quarantined for cosmetic markup loss.
    """
    stripped = _VOICE_ANCHOR_MARKUP_RE.sub("", _string(text))
    return _normalize_whitespace(stripped).lower()


def _voice_anchor_traceable(voice_anchor: str, paragraph: Mapping[str, Any]) -> bool:
    anchor = _voice_anchor_normalize(voice_anchor)
    if not anchor:
        return False
    source_text = _voice_anchor_normalize(
        " ".join(
            _string(paragraph.get(key))
            for key in ("plain_text", "text", "raw_markdown", "summary", "note")
            if _string(paragraph.get(key))
        )
    )
    if not source_text:
        return False
    return anchor in source_text


def _partition_distilled_shards_for_receive(
    *,
    raw_seed_payload: Mapping[str, Any],
    shards_payload: Mapping[str, Any],
    source_artifact_rel: str,
    allowed_parent_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paragraphs = {
        _string(paragraph.get("id")): paragraph
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    }
    allowed = {parent_id for parent_id in (allowed_parent_ids or set()) if parent_id}
    valid_rows: list[dict[str, Any]] = []
    quarantined_rows: list[dict[str, Any]] = []
    for index, row in enumerate(shards_payload.get("shards") or []):
        if not isinstance(row, Mapping):
            quarantined_rows.append(
                {
                    "source_artifact": source_artifact_rel,
                    "row_index": index,
                    "reason": "row_not_object",
                    "row": row,
                }
            )
            continue
        parent_paragraph_id = _string(row.get("parent_paragraph_id")).strip()
        clarified_statement = _normalize_whitespace(_string(row.get("clarified_statement")))
        voice_anchor_raw = _string(row.get("voice_anchor"))
        support_excerpt_raw = _string(row.get("support_excerpt"))
        traceability_candidate = _normalize_whitespace(voice_anchor_raw or support_excerpt_raw)
        reason = ""
        if not parent_paragraph_id:
            reason = "missing_parent_paragraph_id"
        elif allowed and parent_paragraph_id not in allowed:
            reason = "parent_outside_packet_authority_boundary"
        elif parent_paragraph_id not in paragraphs:
            reason = "parent_id_not_in_raw_seed_registry"
        elif not clarified_statement:
            reason = "missing_clarified_statement"
        elif not traceability_candidate:
            reason = "missing_voice_anchor"
        elif not (
            _voice_anchor_traceable(voice_anchor_raw, paragraphs[parent_paragraph_id])
            or _voice_anchor_traceable(support_excerpt_raw, paragraphs[parent_paragraph_id])
        ):
            reason = "voice_anchor_not_traceable_to_parent"
        if reason:
            quarantined_rows.append(
                {
                    "source_artifact": source_artifact_rel,
                    "row_index": index,
                    "parent_paragraph_id": parent_paragraph_id,
                    "reason": reason,
                    "row": dict(row),
                }
            )
            continue
        valid_rows.append(dict(row))
    return valid_rows, quarantined_rows


def _load_contextual_artifact_payload(path: Path) -> dict[str, Any] | None:
    return _load_distillation_artifact_payload(path)


def _extract_contextual_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "contextual_rows" in payload and isinstance(payload.get("contextual_rows"), list):
        return dict(payload)
    if "rows" in payload and isinstance(payload.get("rows"), list):
        return {
            "contextual_rows": list(payload.get("rows") or []),
            "_summary": dict(payload.get("_summary") or {}),
        }
    nested = payload.get("payload")
    if isinstance(nested, Mapping):
        return _extract_contextual_payload(nested)
    for key in ("data", "response", "result"):
        nested_payload = payload.get(key)
        if isinstance(nested_payload, Mapping):
            extracted = _extract_contextual_payload(nested_payload)
            if extracted:
                return extracted
    if "row_id" in payload and "source_ids" in payload:
        return {"contextual_rows": [dict(payload)]}
    raise ValueError("Could not find a contextual compression payload with `contextual_rows`.")


def _normalize_contextual_compression_rows(
    *,
    rows_payload: Mapping[str, Any],
    source_artifact_rel: str,
    source_run_root: str | None = None,
    imported_at: str | None = None,
) -> list[dict[str, Any]]:
    imported_at = imported_at or _utc_now()
    normalized: list[dict[str, Any]] = []
    for raw_row in rows_payload.get("contextual_rows") or []:
        if not isinstance(raw_row, Mapping):
            continue
        source_ids = _string_list(raw_row.get("source_ids"))
        summary = _normalize_whitespace(_string(raw_row.get("summary")))
        if not source_ids or not summary:
            continue
        band = _string(raw_row.get("band")).strip() or "context"
        if band not in {"flag", "card", "context", "deep"}:
            band = "context"
        source_state = _string(raw_row.get("source_state")).strip() or "unknown"
        if source_state not in {"paragraph_only", "sharded", "mixed", "unknown"}:
            source_state = "unknown"
        title = _normalize_whitespace(_string(raw_row.get("title"))) or ", ".join(source_ids[:3])
        row_id = _string(raw_row.get("row_id")).strip() or _stable_contextual_row_id(
            source_ids,
            title,
            summary,
        )
        normalized.append(
            {
                "row_id": row_id,
                "row_kind": _string(raw_row.get("row_kind")).strip()
                or "raw_seed_contextual_compression_row",
                "profile_id": _string(raw_row.get("profile_id")).strip() or RAW_SEED_CONTEXT_PROFILE_ID,
                "creator_skill_id": _string(raw_row.get("creator_skill_id")).strip()
                or "compression.raw_seed_contextual_compression",
                "navigator_skill_id": _string(raw_row.get("navigator_skill_id")).strip()
                or "raw_seed_navigation",
                "skill_id": _string(raw_row.get("skill_id")).strip()
                or _string(raw_row.get("creator_skill_id")).strip()
                or "compression.raw_seed_contextual_compression",
                "band": band,
                "source_state": source_state,
                "source_ids": source_ids,
                "title": title,
                "summary": summary,
                "covered_subclaims": [
                    dict(item)
                    for item in (raw_row.get("covered_subclaims") or [])
                    if isinstance(item, Mapping)
                ],
                "band_reason": _normalize_whitespace(_string(raw_row.get("band_reason")))
                or f"{band} band imported under {RAW_SEED_CONTEXT_PROFILE_ID}",
                "context_space_refs": [
                    dict(item)
                    for item in (raw_row.get("context_space_refs") or [])
                    if isinstance(item, Mapping)
                ],
                "context_horizon": dict(raw_row.get("context_horizon") or {}),
                "drilldown_refs": [
                    dict(item)
                    for item in (raw_row.get("drilldown_refs") or [])
                    if isinstance(item, Mapping)
                ],
                "dynamic_fact_rows": [
                    dict(item)
                    for item in (raw_row.get("dynamic_fact_rows") or [])
                    if isinstance(item, Mapping)
                ],
                "omission_receipt": dict(raw_row.get("omission_receipt") or {}),
                "navigation_use": _string(raw_row.get("navigation_use")),
                "next_moves": _string_list(raw_row.get("next_moves")),
                "up_propagation_candidates": [
                    dict(item)
                    for item in (raw_row.get("up_propagation_candidates") or [])
                    if isinstance(item, Mapping)
                ],
                "validation_notes": _string_list(raw_row.get("validation_notes")),
                "source_artifact": source_artifact_rel,
                "source_run_root": source_run_root,
                "imported_at": imported_at,
                "compression_source": CONTEXTUAL_COMPRESSION_SOURCE,
            }
        )
    return normalized


def _dedupe_contextual_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        item = dict(row)
        row_id = _string(item.get("row_id"))
        if not row_id or row_id in seen:
            continue
        seen.add(row_id)
        merged.append(item)
    return merged


def _normalize_distilled_shards(
    *,
    raw_seed_payload: Mapping[str, Any],
    shards_payload: Mapping[str, Any],
    source_artifact_rel: str,
    source_bin_ids_by_paragraph: Mapping[str, str],
    atomization_source: str = DISTILLATION_SOURCE,
) -> list[dict[str, Any]]:
    paragraphs = {
        _string(paragraph.get("id")): paragraph
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    }
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
        voice_anchor = _normalize_whitespace(
            _string(row.get("voice_anchor")) or _string(row.get("support_excerpt"))
        )
        compression_notes = [
            _string(item)
            for item in (row.get("compression_notes") or [])
            if _string(item)
        ]
        if "bridge_distilled_v1" not in compression_notes:
            compression_notes.append("bridge_distilled_v1")
        normalized.append(
            {
                "id": _stable_atom_id(
                    parent_paragraph_id,
                    ordinal,
                    clarified_statement,
                    voice_anchor=voice_anchor,
                    support_excerpt=_string(row.get("support_excerpt")) or voice_anchor or clarified_statement,
                ),
                "raw_seed_anchor": _string(row.get("raw_seed_anchor")) or _paragraph_anchor(paragraph),
                "clarified_statement": clarified_statement,
                "status": "pending",
                "raw_paragraph_ids": [
                    _string(item)
                    for item in (row.get("raw_paragraph_ids") or [parent_paragraph_id])
                    if _string(item)
                ]
                or [parent_paragraph_id],
                "parent_paragraph_id": parent_paragraph_id,
                "segment_ordinal": ordinal,
                "support_excerpt": _string(row.get("support_excerpt")) or voice_anchor or clarified_statement,
                "voice_anchor": voice_anchor or clarified_statement,
                "coverage_state": "atomized_unreviewed",
                "routing_state": "pending",
                "routing_targets": [],
                "compression_notes": compression_notes,
                "source_substrate": _string(paragraph.get("source_substrate")) or "raw_seed",
                "authored_by": _string(paragraph.get("authored_by")) or "operator",
                "idea_group_ids": [
                    _string(item)
                    for item in (paragraph.get("idea_group_ids") or [])
                    if _string(item)
                ],
                "relevant_files": [],
                "concept_ids": [],
                "intent_provenance": [],
                "atomization_source": atomization_source,
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
        )
    return normalized


def _dedupe_shards(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        shard = dict(row)
        shard_id = _string(shard.get("id"))
        if not shard_id or shard_id in seen:
            continue
        seen.add(shard_id)
        merged.append(shard)
    return merged


def _build_validator_report(
    *,
    normalized_rows: list[dict[str, Any]],
    raw_seed_payload: Mapping[str, Any],
    atomization_source: str,
) -> dict[str, Any]:
    """Run the distillation validator on normalized shards, grouped by paragraph.

    V1 posture is advisory: this function returns a structured report that the
    caller attaches to extracted_payload.validator_report. It never drops rows.
    Strict enforcement is the job of the subagent-import CLI before calling
    import_distilled_shards.
    """

    paragraphs_by_id = {
        _string(paragraph.get("id")): paragraph
        for paragraph in (raw_seed_payload.get("paragraphs") or [])
        if isinstance(paragraph, Mapping) and _string(paragraph.get("id"))
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in normalized_rows:
        par_id = _string(row.get("parent_paragraph_id"))
        if not par_id:
            continue
        grouped.setdefault(par_id, []).append(row)

    per_paragraph: list[dict[str, Any]] = []
    by_shard: dict[str, dict[str, list[str]]] = {}
    totals = {
        "paragraphs_validated": 0,
        "paragraphs_bundle_rejected": 0,
        "shards_accepted": 0,
        "shards_flagged": 0,
        "shards_rejected": 0,
        "paragraphs_with_warnings": 0,
    }
    force_accept = atomization_source == DISTILLATION_OPUS_SEED_SOURCE
    calibration_source = "opus_seed" if force_accept else None

    for par_id, shards in grouped.items():
        source = paragraphs_by_id.get(par_id) or {"id": par_id}
        bundle = {
            "shards": shards,
            "_summary": {
                "teleology": f"advisory_validator_check_for_{atomization_source}",
                "outcome": f"{len(shards)} shard(s) normalized",
                "confidence": "HIGH",
            },
        }
        result = validate_distillation_bundle(
            bundle,
            source,
            strict=False,
            force_accept=force_accept,
            calibration_source=calibration_source,
        )
        totals["paragraphs_validated"] += 1
        if result.bundle_rejected:
            totals["paragraphs_bundle_rejected"] += 1
        totals["shards_accepted"] += len(result.accepted)
        totals["shards_flagged"] += len(result.flagged)
        totals["shards_rejected"] += len(result.rejected)
        if result.warnings:
            totals["paragraphs_with_warnings"] += 1
        for shard, reason in result.flagged:
            shard_id = _string(shard.get("id"))
            if shard_id:
                by_shard.setdefault(shard_id, {"flags": [], "rejections": []})["flags"].append(reason)
        for shard, reason in result.rejected:
            shard_id = _string(shard.get("id"))
            if shard_id:
                by_shard.setdefault(shard_id, {"flags": [], "rejections": []})["rejections"].append(reason)
        per_paragraph.append(
            {
                "parent_paragraph_id": par_id,
                **result.to_report_payload(),
                "flagged_shard_ids": [
                    _string(shard.get("id"))
                    for shard, _ in result.flagged
                    if _string(shard.get("id"))
                ],
                "rejected_shard_ids": [
                    _string(shard.get("id"))
                    for shard, _ in result.rejected
                    if _string(shard.get("id"))
                ],
            }
        )

    return {
        "mode": "advisory",
        "atomization_source": atomization_source,
        "totals": totals,
        "per_paragraph": per_paragraph,
        "by_shard": by_shard,
    }


def _attach_receive_metadata(
    rows: list[dict[str, Any]],
    *,
    validator_report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_shard = validator_report.get("by_shard")
    by_shard = by_shard if isinstance(by_shard, Mapping) else {}
    received: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        shard_id = _string(item.get("id"))
        shard_report = by_shard.get(shard_id) if shard_id else None
        shard_report = shard_report if isinstance(shard_report, Mapping) else {}
        flags = _string_list(shard_report.get("flags"))
        rejections = _string_list(shard_report.get("rejections"))
        item["validator_flags"] = flags
        item["validator_rejections"] = rejections
        item["receive_state"] = "received_with_warnings" if flags or rejections else "received"
        item["audit_state"] = "audit_flagged" if flags or rejections else "pending_audit"
        received.append(item)
    return received


def import_distilled_shards(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    run_root: str | Path | None = None,
    artifact_path: str | Path | None = None,
    atomization_source: str = DISTILLATION_SOURCE,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = _string(family).strip() or "09"
    family_dir = _resolve_family_dir(repo_root, family_token)
    substrate_token = _string(substrate).strip() or "raw_seed"
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
    source_bin_ids_by_paragraph = {
        _string(bin_row.get("parent_paragraph_id")): _string(bin_row.get("shard_id"))
        for bin_row in (raw_seed_shards_payload.get("shards") or [])
        if isinstance(bin_row, Mapping)
        and _string(bin_row.get("parent_paragraph_id"))
        and _string(bin_row.get("shard_id"))
    }

    artifacts = resolve_distillation_artifact_paths(
        repo_root=repo_root,
        run_root=run_root,
        artifact_path=artifact_path,
    )
    artifact_paths_rel: list[str] = []
    skipped_artifacts: list[dict[str, str]] = []
    normalized_rows: list[dict[str, Any]] = []
    quarantined_rows: list[dict[str, Any]] = []
    for artifact in artifacts:
        source_artifact_rel = artifact.resolve().relative_to(repo_root.resolve()).as_posix()
        payload = _load_distillation_artifact_payload(artifact)
        if not payload:
            skipped_artifacts.append({"artifact": source_artifact_rel, "reason": "unloadable"})
            continue
        try:
            distilled_payload = _extract_distillation_payload(payload)
        except ValueError as exc:
            skipped_artifacts.append({"artifact": source_artifact_rel, "reason": str(exc)})
            continue
        artifact_paths_rel.append(source_artifact_rel)
        allowed_parent_ids = _authority_parent_ids_from_payload(payload)
        valid_shards, artifact_quarantines = _partition_distilled_shards_for_receive(
            raw_seed_payload=raw_seed_payload,
            shards_payload=distilled_payload,
            source_artifact_rel=source_artifact_rel,
            allowed_parent_ids=allowed_parent_ids,
        )
        quarantined_rows.extend(artifact_quarantines)
        normalized_rows.extend(
            _normalize_distilled_shards(
                raw_seed_payload=raw_seed_payload,
                shards_payload={**distilled_payload, "shards": valid_shards},
                source_artifact_rel=source_artifact_rel,
                source_bin_ids_by_paragraph=source_bin_ids_by_paragraph,
                atomization_source=atomization_source,
            )
        )
    if not normalized_rows:
        if quarantined_rows:
            return {
                "status": "quarantined",
                "family": family_token,
                "family_dir": family_dir,
                "substrate": substrate_token,
                "artifact_path": artifact_paths_rel[0] if len(artifact_paths_rel) == 1 else None,
                "artifact_paths": artifact_paths_rel,
                "normalized_shards": 0,
                "imported_shards": 0,
                "received_shards": 0,
                "received_with_warnings": 0,
                "quarantined_rows": len(quarantined_rows),
                "quarantine_receipt": {
                    "schema_version": "raw_seed_bridge_receive_quarantine_v1",
                    "quarantined_count": len(quarantined_rows),
                    "rows": quarantined_rows,
                },
                "skipped_artifacts": skipped_artifacts,
            }
        raise ValueError(
            "No normalized distilled shards could be built from "
            f"{', '.join(artifact_paths_rel)}"
        )

    unique_normalized_rows = _dedupe_shards(normalized_rows)

    validator_report = _build_validator_report(
        normalized_rows=unique_normalized_rows,
        raw_seed_payload=raw_seed_payload,
        atomization_source=atomization_source,
    )
    received_rows = _attach_receive_metadata(
        unique_normalized_rows,
        validator_report=validator_report,
    )
    received_with_warnings = sum(
        1 for row in received_rows if _string(row.get("receive_state")) == "received_with_warnings"
    )

    extracted_path = repo_root / family_extracted_shards_path(family_dir)
    extracted_payload = _load_json(extracted_path)
    if extracted_payload is None and extracted_path.exists():
        raise ValueError(f"Existing extracted shards file is unreadable: {extracted_path}")
    extracted_payload = extracted_payload or {"shards": []}
    existing_rows = [
        shard for shard in (extracted_payload.get("shards") or []) if isinstance(shard, Mapping)
    ]
    touched_paragraph_ids = {
        _string(row.get("parent_paragraph_id"))
        for row in normalized_rows
        if _string(row.get("parent_paragraph_id"))
    }
    replaced_rows = [
        dict(shard)
        for shard in existing_rows
        if _string(shard.get("parent_paragraph_id")) in touched_paragraph_ids
        and _string(shard.get("atomization_source")) in REPLACEABLE_ATOMIZATION_SOURCES
    ]
    kept_rows = [
        dict(shard)
        for shard in existing_rows
        if not (
            _string(shard.get("parent_paragraph_id")) in touched_paragraph_ids
            and _string(shard.get("atomization_source")) in REPLACEABLE_ATOMIZATION_SOURCES
        )
    ]
    merged_rows = _dedupe_shards([*kept_rows, *received_rows])
    if len(merged_rows) < len(kept_rows):
        raise ValueError(
            "Distilled shard import would drop kept rows "
            f"({len(kept_rows)} kept -> {len(merged_rows)} merged)."
        )
    extracted_payload.update(
        {
            "shards": merged_rows,
            "browser_index": _browser_index_for_shards(merged_rows),
            "extracted_at": _utc_now(),
            "source": atomization_source,
            "schema_version_family_shards": "extracted_shards_v0",
            "family_path": family_dir,
            "merge_note": (
                f"Received {len(received_rows)} distilled shard row(s) across "
                f"{len(touched_paragraph_ids)} paragraph(s) from {len(artifact_paths_rel)} artifact(s); "
                f"quarantined {len(quarantined_rows)} boundary-invalid row(s)."
            ),
            "source_content_sha256": hashlib.sha256(
                "\n".join(
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in artifacts
                ).encode("utf-8")
            ).hexdigest(),
            "validator_report": validator_report,
            "bridge_import_receipt": {
                "schema_version": "raw_seed_bridge_receive_v1",
                "received_shards": len(received_rows),
                "received_with_warnings": received_with_warnings,
                "quarantined_rows": len(quarantined_rows),
                "quarantine_rows": quarantined_rows,
                "audit_state_counts": {
                    "pending_audit": sum(
                        1 for row in received_rows if _string(row.get("audit_state")) == "pending_audit"
                    ),
                    "audit_flagged": sum(
                        1 for row in received_rows if _string(row.get("audit_state")) == "audit_flagged"
                    ),
                },
            },
        }
    )
    _write_json(extracted_path, extracted_payload)

    review_path = repo_root / family_raw_seed_routing_review_path(family_dir)
    review_payload = _load_json(review_path) or {
        "kind": "raw_seed_routing_review",
        "schema_version": "raw_seed_routing_review_v1",
        "generated_at": _utc_now(),
        "family_id": family_token,
        "family_number": family_token,
        "family_dir": family_dir,
        "dispatch_policy": {},
        "proposals": [],
        "stats": {},
    }
    replaced_shard_ids = {
        _string(shard.get("id")) for shard in replaced_rows if _string(shard.get("id"))
    }
    touched_bin_ids = {
        _string(row.get("source_bin_id"))
        for row in normalized_rows
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
                if any(_string(member.get("status")) in {"", "pending_review"} for member in kept_members)
                else _string(next_envelope.get("status")) or "completed"
            )
            filtered_proposals.append(next_envelope)
            continue
        if (
            _string(proposal.get("shard_id")) not in replaced_shard_ids
            and parent_paragraph_id not in touched_paragraph_ids
        ):
            filtered_proposals.append(dict(proposal))
    dropped_review_proposals = len(review_payload.get("proposals") or []) - len(filtered_proposals)
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
                isinstance(member, Mapping) and _string(member.get("status")) in {"", "pending_review"}
                for member in proposal.get("member_proposals") or []
            )
        ) or (
            not isinstance(proposal.get("member_proposals"), list)
            and _string(proposal.get("status")) in {"", "pending_review"}
        )
    ]
    review_payload["generated_at"] = _utc_now()
    review_payload["proposals"] = filtered_proposals
    review_payload["stats"] = {
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
        "remaining_pending_shards": sum(
            1 for shard in merged_rows if (_string(shard.get("routing_state")) or "pending") == "pending"
        ),
    }
    _write_json(review_path, review_payload)

    principles = _load_json(repo_root / raw_seed_principles_path_for_family(family_dir)) or {"principles": []}
    coverage = build_raw_seed_coverage(
        raw_seed_payload=raw_seed_payload,
        raw_seed_shards_payload=raw_seed_shards_payload,
        extracted_shards_payload=extracted_payload,
        principles_payload=principles,
        routing_review_payload=review_payload,
    )
    coverage_path = repo_root / family_raw_seed_coverage_path(family_dir)
    _write_json(coverage_path, coverage)

    autonomous_seed_json_path, autonomous_seed_markdown_path, autonomous_seed_payload = write_autonomous_seed(
        repo_root,
        family_dir=family_dir,
    )

    return {
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "artifact_path": artifact_paths_rel[0] if len(artifact_paths_rel) == 1 else None,
        "artifact_paths": artifact_paths_rel,
        "normalized_shards": len(normalized_rows),
        "imported_shards": len(received_rows),
        "received_shards": len(received_rows),
        "received_with_warnings": received_with_warnings,
        "quarantined_rows": len(quarantined_rows),
        "quarantine_receipt": {
            "schema_version": "raw_seed_bridge_receive_quarantine_v1",
            "quarantined_count": len(quarantined_rows),
            "rows": quarantined_rows,
        },
        "touched_paragraphs": len(touched_paragraph_ids),
        "replaced_existing_rows": len(replaced_rows),
        "dropped_review_proposals": dropped_review_proposals,
        "extracted_shards_path": family_extracted_shards_path(family_dir),
        "raw_seed_coverage_path": family_raw_seed_coverage_path(family_dir),
        "raw_seed_routing_review_path": family_raw_seed_routing_review_path(family_dir),
        "autonomous_seed_path": autonomous_seed_json_path,
        "autonomous_seed_markdown_path": autonomous_seed_markdown_path,
        "mission_blackboard_path": _string(autonomous_seed_payload.get("mission_blackboard_path")),
        "controller_heartbeat_ref": (
            dict(autonomous_seed_payload.get("controller_heartbeat_ref"))
            if isinstance(autonomous_seed_payload.get("controller_heartbeat_ref"), Mapping)
            else {}
        ),
        "paragraphs_remaining_without_atoms": int(coverage["counts"]["paragraphs_without_atoms"]),
        "skipped_artifacts": skipped_artifacts,
    }
