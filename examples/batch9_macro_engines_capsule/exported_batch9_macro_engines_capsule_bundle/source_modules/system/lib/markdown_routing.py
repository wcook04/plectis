"""
[PURPOSE]
- Teleology: Provide deterministic markdown-routing primitives for grouped observe plans so promotion targets, reference targets, and living-map patch candidates can be derived and validated without ad hoc text handling.
- Mechanism: Normalize route config fields, parse and render lightweight frontmatter, resolve markdown sections, extract observe payload blocks, derive deterministic reference or promotion text transforms, and validate reference-map routing against repo-root constraints.
- Non-goal: Execute live file mutations or observe dispatches; this module only prepares and validates markdown-oriented routing decisions and in-memory text rewrites.

[INTERFACE]
- Exports: `normalize_route_config`, `has_routing_fields`, `split_frontmatter`, `parse_frontmatter`, `render_frontmatter`, `render_markdown_document`, `extract_section`, `extract_section_block`, `find_section_bounds`, `propose_patch_map_from_observe_payload`, `extract_observe_artifact_payload`, `apply_reference_to_text`, `apply_promotion_to_text`, `resolve_reference_maps`, and `validate_route_payload`.
- Reads: Observe-plan routing dicts, markdown source text, repo-root paths, and living-map markdown notes under the repo root.
- Writes: None.
- Schema: Public validators return `(errors, warnings)` tuples or normalized route dicts; text mutators return `(text, status)` tuples.

[FLOW]
- Normalize routing fields -> parse markdown/frontmatter boundaries -> resolve sections and observe payload blocks -> build reference/promotion text inserts or patch-map candidates -> validate target paths, sections, and living-map references against repo-root state.
- When-needed: Open when grouped observe routing needs deterministic markdown parsing, living-map reference resolution, or route preflight within repo-root boundaries instead of bespoke note surgery.
- Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/kernel/commands/apply.py
- Couples: `tools/meta/apply/run_observe_plan.py` and `kernel.py` rely on these helpers to normalize, validate, and apply routed observe payloads before any live write path proceeds.
- Navigation-group: kernel_lib

[DEPENDENCIES]
- pathlib.Path: Resolve repo-root-relative paths and scan markdown notes.
- re: Parse headings, bullets, and metadata patterns.
- hashlib: Build stable markers for reference blocks.

[CONSTRAINTS]
- Guarantee: Public helpers stay deterministic for stable text and repo contents; repeated application of the same promotion or reference marker returns duplicate/no-op status instead of duplicating content.
- Orders: Living-map patch extraction is bounded to KNOWN, BROKEN, UNKNOWN, and HISTORY sections, and section matching is normalized through `normalize_heading_title()`.
- Fails: Unsupported routing combinations, missing sections, invalid reference targets, and out-of-root paths are surfaced as `ValueError` or accumulated validation errors depending on the entrypoint.
- Non-goal: This module does not write files, create apply receipts, or perform grouped observe execution by itself.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROUTING_FIELDS = (
    "result_note_path",
    "result_note_kind",
    "result_note_frontmatter",
    "embed_original_plan",
    "concatenate_group_outputs",
    "reference_maps",
    "promotion_target_path",
    "promotion_mode",
    "promotion_section",
    "promotion_gate",
)
PROMOTION_MODES = {
    "create_note",
    "append_note",
    "append_section",
    "replace_section",
    "reference_artifact",
}
PROMOTION_GATES = {"manual", "auto"}
RESULT_NOTE_KIND_DEFAULT = "observe_dump_note"
PROMOTION_GATE_DEFAULT = "manual"
REFERENCE_ARTIFACT_GENERIC_ROOT = "obsidian/"
REFERENCE_ARTIFACT_DISALLOWED_KINDS = {"observe_dump_note", "execution_map"}
_REFERENCE_MAP_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    "venv",
}
_LIVING_MAP_SECTIONS = ("KNOWN", "BROKEN", "UNKNOWN", "HISTORY")
_PATCH_SECTION_ALIASES = {
    "KNOWN": {"known", "locked facts", "facts", "confirmed facts"},
    "BROKEN": {"broken", "spec drift", "drift", "tensions", "risks", "failures"},
    "UNKNOWN": {"unknown", "open questions", "questions", "next-probe questions", "next probe questions"},
    "HISTORY": {"history", "resolutions", "change log"},
}
_PATCH_TAG_TO_SECTION = {
    "FACT": "KNOWN",
    "TENSION": "BROKEN",
    "BROKEN": "BROKEN",
    "UNKNOWN": "UNKNOWN",
}
_PATCH_METADATA_PREFIXES = {
    "response_file:",
    "dump_file:",
    "observe_id:",
    "group_label:",
    "generated_at:",
    "bridge_provider:",
    "bridge_prompt_chars:",
    "dump_truncated:",
    "status:",
    "continuation_source:",
    "result_note_path:",
    "promotion_target_path:",
    "promotion_target_kind:",
    "promotion_mode:",
    "promotion_section:",
    "promotion_gate:",
    "promotion_status:",
    "promotion_error:",
    "source_plan:",
    "source_history_entry:",
}


def _string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_or_default(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def normalize_route_config(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Collapse the optional routed-observe fields into one normalized config object that downstream validators and writers can consume consistently.
    - Mechanism: Sanitize frontmatter and reference-map containers, coerce booleans with defaults, normalize promotion mode/gate, and return one routing dict keyed by the supported route fields.
    - Reads: `plan` and the module-level routing constants such as `ROUTING_FIELDS`, `PROMOTION_GATES`, and the default note-kind/mode values.
    - Writes: None.
    - Guarantee: Returns every routed field with stable defaults for booleans and promotion gate/kind normalization.
    - Fails: None.
    - When-needed: Open when a grouped observe plan already carries routing fields and the caller needs the canonical normalized view before validation or writeback.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; kernel.py
    - Navigation-group: kernel_lib
    """
    frontmatter = plan.get("result_note_frontmatter")
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    raw_reference_maps = plan.get("reference_maps")
    reference_maps: List[str] = []
    if isinstance(raw_reference_maps, list):
        for item in raw_reference_maps:
            token = _string(item)
            if token is not None:
                reference_maps.append(token)

    mode = _string(plan.get("promotion_mode"))
    gate = _string(plan.get("promotion_gate")) or PROMOTION_GATE_DEFAULT
    return {
        "result_note_path": _string(plan.get("result_note_path")),
        "result_note_kind": _string(plan.get("result_note_kind")) or RESULT_NOTE_KIND_DEFAULT,
        "result_note_frontmatter": dict(frontmatter),
        "embed_original_plan": _bool_or_default(plan.get("embed_original_plan"), True),
        "concatenate_group_outputs": _bool_or_default(plan.get("concatenate_group_outputs"), True),
        "reference_maps": reference_maps,
        "promotion_target_path": _string(plan.get("promotion_target_path")),
        "promotion_mode": mode,
        "promotion_section": _string(plan.get("promotion_section")),
        "promotion_gate": gate if gate in PROMOTION_GATES else PROMOTION_GATE_DEFAULT,
    }


def has_routing_fields(plan: Dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Detect whether a grouped observe plan declares any routed markdown fields.
    - Guarantee: Returns True when at least one of the recognized routing fields is non-None, False otherwise.
    - Fails: None.
    """
    return any(plan.get(field) is not None for field in ROUTING_FIELDS)


def split_frontmatter(text: str) -> Tuple[str, str]:
    """
    [ACTION]
    - Teleology: Split a markdown document into its YAML frontmatter fence and body text.
    - Guarantee: Returns a `(frontmatter_fence, body)` tuple; documents without a leading `---` fence return `("", text)`.
    - Fails: None.
    """
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[: end + 5], text[end + 5 :]


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """
    [ACTION]
    - Teleology: Parse the lightweight frontmatter subset used by observe routing and markdown authority surfaces without depending on a full YAML parser.
    - Mechanism: Split the leading frontmatter fence, scan line-by-line for scalar or list-shaped keys, coerce simple YAML scalars, and return `(card, body)`.
    - Reads: `text`.
    - Writes: None.
    - Guarantee: Returns a `(dict, body_text)` tuple; malformed or absent frontmatter degrades to an empty dict plus the original body.
    - Fails: None.
    - When-needed: Open when a routing or digest surface needs the frontmatter/body split for markdown notes and observe artifacts without pulling in broader markdown machinery.
    - Escalates-to: system/lib/observe_apply_context.py::build_observe_context_digest; tools/meta/apply/run_observe_plan.py
    """
    frontmatter_text, body = split_frontmatter(text)
    if not frontmatter_text:
        return {}, body
    lines = frontmatter_text.splitlines()[1:-1]
    card: Dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith(" ") or line.startswith("\t") or ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "[]":
            card[key] = []
            index += 1
            continue
        if value:
            card[key] = _yaml_parse_scalar(value)
            index += 1
            continue
        index += 1
        list_items: List[Any] = []
        while index < len(lines):
            nested = lines[index]
            if nested.startswith("  - "):
                list_items.append(_yaml_parse_scalar(nested[4:].strip()))
                index += 1
                continue
            if nested.startswith(" ") or nested.startswith("\t"):
                index += 1
                continue
            break
        card[key] = list_items
    return card, body


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_parse_scalar(value: str) -> Any:
    token = _unquote_yaml_scalar(value)
    lowered = token.casefold()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", token):
        try:
            return int(token)
        except ValueError:
            return token
    if re.fullmatch(r"-?\d+\.\d+", token):
        try:
            return float(token)
        except ValueError:
            return token
    return token


def _yaml_lines(key: str, value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines = [f"{prefix}{key}:"]
        for child_key, child_value in value.items():
            lines.extend(_yaml_lines(str(child_key), child_value, indent + 2))
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}{key}: []"]
        lines = [f"{prefix}{key}:"]
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}  -")
                for child_key, child_value in item.items():
                    lines.extend(_yaml_lines(str(child_key), child_value, indent + 4))
            else:
                lines.append(f"{prefix}  - {_yaml_scalar(item)}")
        return lines
    return [f"{prefix}{key}: {_yaml_scalar(value)}"]


def render_frontmatter(frontmatter: Dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Serialize a frontmatter dictionary to a minimal YAML fence string.
    - Guarantee: Returns a `---\n…\n---\n` string for non-empty dicts, or `""` for empty dicts.
    - Fails: None.
    """
    if not frontmatter:
        return ""
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.extend(_yaml_lines(str(key), value))
    lines.append("---")
    return "\n".join(lines) + "\n"


def render_markdown_document(frontmatter: Dict[str, Any], body: str) -> str:
    """
    [ACTION]
    - Teleology: Compose a normalized markdown document from a frontmatter dict and a body string.
    - Guarantee: Returns the serialized frontmatter fence prepended to a trailing-newline-normalized body, or the body alone when frontmatter is empty.
    - Fails: None.
    """
    body_text = body.rstrip() + "\n"
    frontmatter_text = render_frontmatter(frontmatter)
    if not frontmatter_text:
        return body_text
    return frontmatter_text + body_text


def normalize_heading_title(title: str) -> str:
    """
    [ACTION]
    - Teleology: Normalize a markdown heading title to a stable, case-folded, collapsed-whitespace string for section lookups.
    - Guarantee: Returns a lowercased, single-spaced string with no leading/trailing whitespace.
    - Fails: None.
    """
    return re.sub(r"\s+", " ", str(title).strip()).casefold()


def extract_section(body: str, title: str) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Extract the content of a uniquely named markdown section by heading title.
    - Guarantee: Returns the stripped section content string when exactly one heading matches, or `None` when the section is absent or ambiguous.
    - Fails: None.
    """
    bounds = find_section_bounds(body, title)
    if bounds is None:
        return None
    _, _, content_start, content_end = bounds
    return body[content_start:content_end].strip()


def extract_section_block(
    body: str,
    title: str,
    *,
    next_titles: Optional[List[str]] = None,
) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Extract the content between a uniquely named heading and either a set of named stop headings or the next heading at the same or higher level.
    - Guarantee: Returns the stripped section content string for a unique heading match, or `None` when no unique match is found.
    - Fails: None.
    """
    heading_re = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)\s*$")
    matches = list(heading_re.finditer(body))
    target = normalize_heading_title(title)
    selected: Optional[re.Match[str]] = None
    for match in matches:
        if normalize_heading_title(match.group(2)) == target:
            if selected is not None:
                return None
            selected = match
    if selected is None:
        return None

    content_start = selected.end()
    content_end = len(body)
    if next_titles:
        stop_titles = {normalize_heading_title(item) for item in next_titles}
        for later in matches:
            if later.start() <= selected.start():
                continue
            if normalize_heading_title(later.group(2)) in stop_titles:
                content_end = later.start()
                break
    else:
        level = len(selected.group(1))
        for later in matches:
            if later.start() <= selected.start():
                continue
            if len(later.group(1)) <= level:
                content_end = later.start()
                break
    return body[content_start:content_end].strip()


def find_section_bounds(body: str, title: str) -> Optional[Tuple[int, int, int, int]]:
    """
    [ACTION]
    - Teleology: Locate the byte-offset bounds of a uniquely named markdown section heading and its content.
    - Guarantee: Returns `(heading_start, heading_end, content_start, content_end)` for a unique match, or `None` when absent or ambiguous.
    - Fails: None.
    """
    target = normalize_heading_title(title)
    heading_re = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)\s*$")
    matches = list(heading_re.finditer(body))
    selected = []
    for match in matches:
        if normalize_heading_title(match.group(2)) == target:
            selected.append(match)
    if len(selected) != 1:
        return None

    match = selected[0]
    level = len(match.group(1))
    content_start = match.end()
    content_end = len(body)
    for later in matches:
        if later.start() <= match.start():
            continue
        later_level = len(later.group(1))
        if later_level <= level:
            content_end = later.start()
            break
    return match.start(), match.end(), content_start, content_end


def split_markdown_entries(section_text: str) -> List[str]:
    """
    [ACTION]
    - Teleology: Segment a markdown section into individual bullet or paragraph entries for patch candidate extraction.
    - Guarantee: Returns a list of non-empty trimmed entry strings split on blank lines and top-level bullet starts.
    - Fails: None.
    """
    lines = section_text.strip().splitlines()
    entries: List[str] = []
    current: List[str] = []
    bullet_re = re.compile(r"^([-*+]\s+|\d+\.\s+)")

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append("\n".join(current).rstrip())
                current = []
            continue
        if bullet_re.match(stripped) and current:
            entries.append("\n".join(current).rstrip())
            current = [line]
            continue
        current.append(line)

    if current:
        entries.append("\n".join(current).rstrip())
    return entries


def _iter_markdown_sections(body: str) -> List[Tuple[str, str]]:
    heading_re = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)\s*$")
    matches = list(heading_re.finditer(body))
    sections: List[Tuple[str, str]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        content_start = match.end()
        content_end = len(body)
        for later in matches[index + 1 :]:
            if len(later.group(1)) <= level:
                content_end = later.start()
                break
        sections.append((match.group(2).strip(), body[content_start:content_end].strip()))
    return sections


def _normalize_patch_entry(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def _clean_patch_candidate(entry: str) -> Optional[str]:
    lines = [line.strip() for line in str(entry or "").splitlines() if line.strip()]
    if not lines:
        return None
    first = re.sub(r"^([-*+]\s+|\d+\.\s+)", "", lines[0].strip())
    remainder = [line.strip() for line in lines[1:]]
    text = " ".join([first, *remainder]).strip()
    if not text:
        return None
    text = re.sub(r"\[(FACT|INFERENCE|TENSION|UNKNOWN|BROKEN)\]\s*", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return None
    lowered = text.casefold()
    if lowered.startswith("next_action:"):
        return None
    if any(lowered.startswith(prefix) for prefix in _PATCH_METADATA_PREFIXES):
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def _existing_living_map_entries(existing_map_text: Optional[str]) -> Dict[str, List[str]]:
    entries: Dict[str, List[str]] = {section: [] for section in _LIVING_MAP_SECTIONS}
    if not existing_map_text:
        return entries
    _, body = parse_frontmatter(existing_map_text)
    for section in _LIVING_MAP_SECTIONS:
        content = extract_section(body, section)
        if content is None:
            continue
        entries[section] = [
            _normalize_patch_entry(item)
            for item in split_markdown_entries(content)
            if _normalize_patch_entry(item)
        ]
    return entries


def propose_patch_map_from_observe_payload(
    *,
    payload_markdown: str,
    existing_map_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Derive deterministic living-map patch candidates from observe payload markdown so operators can append only the KNOWN/BROKEN/UNKNOWN/HISTORY facts that are actually new.
    - Mechanism: Scan headings and tagged entries, normalize candidate bullets into section buckets, suppress duplicates already present in the living map, and emit a patch proposal summary.
    - Reads: `payload_markdown`, optional `existing_map_text`, and the living-map section/tag alias tables in this module.
    - Writes: None.
    - Guarantee: Returns a dict with `status`, sectioned candidates, suppressed entries, patches, signal summary, and warnings.
    - Fails: None.
    - When-needed: Open when an observe response needs deterministic living-map patch extraction before any operator review or apply step.
    - Escalates-to: system/lib/kernel/commands/apply.py; tools/meta/apply/run_observe_plan.py
    """
    extracted: Dict[str, List[str]] = {section: [] for section in _LIVING_MAP_SECTIONS}
    suppressed: Dict[str, List[str]] = {section: [] for section in _LIVING_MAP_SECTIONS}
    warnings: List[str] = []
    seen: Dict[str, set[str]] = {section: set() for section in _LIVING_MAP_SECTIONS}

    def _push(section: str, raw_entry: str) -> None:
        cleaned = _clean_patch_candidate(raw_entry)
        if cleaned is None:
            return
        normalized = _normalize_patch_entry(cleaned)
        if not normalized or normalized in seen[section]:
            return
        seen[section].add(normalized)
        extracted[section].append(cleaned)

    heading_matches: List[str] = []
    for title, content in _iter_markdown_sections(payload_markdown):
        default_section = None
        normalized_title = normalize_heading_title(title)
        for section, aliases in _PATCH_SECTION_ALIASES.items():
            if normalized_title in aliases:
                default_section = section
                heading_matches.append(title)
                break
        if default_section is None:
            continue
        for entry in split_markdown_entries(content):
            tags = re.findall(r"\[(FACT|TENSION|UNKNOWN|BROKEN)\]", entry, flags=re.IGNORECASE)
            section = _PATCH_TAG_TO_SECTION.get(tags[0].upper(), default_section) if tags else default_section
            _push(section, entry)

    tagged_hits = 0
    for entry in split_markdown_entries(payload_markdown):
        tags = re.findall(r"\[(FACT|TENSION|UNKNOWN|BROKEN)\]", entry, flags=re.IGNORECASE)
        if not tags:
            continue
        tagged_hits += 1
        section = _PATCH_TAG_TO_SECTION.get(tags[0].upper())
        if section is None:
            continue
        _push(section, entry)

    existing_entries = _existing_living_map_entries(existing_map_text)
    patches: List[Dict[str, str]] = []
    for section in _LIVING_MAP_SECTIONS:
        for entry in extracted[section]:
            normalized = _normalize_patch_entry(entry)
            if normalized in existing_entries.get(section, []):
                suppressed[section].append(entry)
                continue
            patches.append(
                {
                    "section": section,
                    "action": "append",
                    "entry": entry,
                }
            )

    status = "ready"
    if not any(extracted[section] for section in _LIVING_MAP_SECTIONS):
        status = "no_deterministic_candidates"
        warnings.append(
            "No deterministic patch_map candidates were extracted. Use explicit KNOWN/BROKEN/UNKNOWN/HISTORY headings or [FACT]/[TENSION]/[UNKNOWN] tags in the observe payload."
        )
    elif not patches:
        status = "already_present"
        warnings.append("All deterministic patch_map candidates were already present in the living map.")

    return {
        "status": status,
        "candidate_sections": extracted,
        "suppressed_candidates": suppressed,
        "patches": patches,
        "signal_summary": {
            "heading_matches": heading_matches,
            "tagged_entry_count": tagged_hits,
        },
        "warnings": warnings,
    }


def build_promotion_block(
    *,
    observe_id: str,
    source_artifact: str,
    generated_at: str,
    payload_markdown: str,
) -> str:
    """
    [ACTION]
    - Teleology: Build the formatted observe-promotion block string that gets inserted into a target markdown document.
    - Guarantee: Returns a newline-terminated string containing the promotion HTML comment marker, blockquote citation, and payload content.
    - Fails: None.
    """
    payload = payload_markdown.strip()
    lines = [
        f"<!-- observe-promotion:{observe_id} -->",
        (
            f"> Observe promotion from `{source_artifact}` "
            f"(`{observe_id}` at `{generated_at}`)."
        ),
        "",
        payload if payload else "_No promotion payload generated._",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _artifact_metadata_bullet(body: str, key: str) -> Optional[str]:
    pattern = re.compile(rf"(?m)^-\s*{re.escape(key)}:\s*(.+?)\s*$")
    match = pattern.search(body)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw.startswith("`") and raw.endswith("`") and len(raw) >= 2:
        raw = raw[1:-1].strip()
    return raw or None


def extract_observe_artifact_payload(
    *,
    source_text: str,
    source_artifact: str,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Normalize supported observe artifact shapes into one payload block that reference and promotion routing can consume uniformly.
    - Mechanism: Parse frontmatter and headings, recognize `observe_dump_note` or `# Observe Group Response` sources, and extract the observe id, generated timestamp, payload markdown, and routing summary fields.
    - Reads: `source_text` and `source_artifact`.
    - Writes: None.
    - Guarantee: Returns a dict with `source_kind`, `observe_id`, `generated_at`, `payload_markdown`, `source_key`, and `summary` for supported artifact shapes.
    - Fails: Raises `ValueError` when the source artifact is missing required metadata or does not match a supported observe artifact shape.
    - When-needed: Open when routed observe writeback needs to turn a note or group-response artifact into a normalized promotion/reference payload.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/kernel/commands/apply.py
    """
    card, body = parse_frontmatter(source_text)
    kind = _string(card.get("kind"))
    if kind == "observe_dump_note":
        observe_id = _string(card.get("observe_id") or card.get("id"))
        generated_at = _string(card.get("generated_at")) or ""
        payload = extract_section_block(body, "Promotion Payload", next_titles=["Routing"])
        if not observe_id:
            raise ValueError("observe_dump_note source is missing observe_id frontmatter")
        if payload is None:
            raise ValueError("observe_dump_note source is missing the Promotion Payload section")
        return {
            "source_kind": "observe_dump_note",
            "observe_id": observe_id,
            "generated_at": generated_at,
            "payload_markdown": payload.strip(),
            "source_key": observe_id,
            "summary": None,
        }

    title_match = re.match(r"(?m)^#\s+(.+?)\s*$", body or source_text)
    title = title_match.group(1).strip() if title_match else ""
    if title == "Observe Group Response":
        observe_id = _artifact_metadata_bullet(body, "observe_id")
        generated_at = _artifact_metadata_bullet(body, "generated_at") or ""
        group_label = _artifact_metadata_bullet(body, "group_label")
        payload = extract_section(body, "Response")
        if not observe_id:
            raise ValueError("observe response source is missing the observe_id metadata bullet")
        if payload is None:
            raise ValueError("observe response source is missing the Response section")
        source_key = observe_id if not group_label else f"{observe_id}:{group_label}"
        summary = None if not group_label else f"group `{group_label}`"
        return {
            "source_kind": "observe_response",
            "observe_id": observe_id,
            "generated_at": generated_at,
            "payload_markdown": payload.strip(),
            "source_key": source_key,
            "summary": summary,
        }

    raise ValueError(
        f"Unsupported source artifact for reference routing: {source_artifact}. "
        "Expected kind: observe_dump_note or # Observe Group Response."
    )


def build_reference_block(
    *,
    source_key: str,
    source_artifact: str,
    observe_id: str,
    generated_at: str,
    payload_markdown: str,
    summary: Optional[str] = None,
) -> Tuple[str, str]:
    """
    [ACTION]
    - Teleology: Build a stable-marker reference block and its idempotency marker string for observe reference insertion.
    - Guarantee: Returns `(marker, block_text)` where `marker` is a deterministic SHA-256-keyed HTML comment and `block_text` is the formatted reference block.
    - Fails: None.
    """
    marker_hash = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:12]
    marker = f"<!-- observe-reference:{marker_hash} -->"
    payload = payload_markdown.strip()
    detail = f", {summary}" if summary else ""
    lines = [
        marker,
        (
            f"> Observe reference from `{source_artifact}` "
            f"(`{observe_id}` at `{generated_at}`{detail})."
        ),
        "",
        payload if payload else "_No reference payload generated._",
    ]
    return marker, "\n".join(lines).rstrip() + "\n"


def resolve_reference_artifact_target_family(
    *,
    target_text: str,
    target_path: Optional[str] = None,
) -> Tuple[str, str]:
    """
    [ACTION]
    - Teleology: Determine the target family (`living_map`, `idea_packet`, or `authored_obsidian_note`) for a reference-artifact routing target.
    - Guarantee: Returns `(family, resolved_kind)` when the target text satisfies a supported family constraint.
    - Fails: Raises `ValueError` when the target does not match any supported reference-artifact family.
    """
    kind = _string(markdown_kind(target_text)) or ""
    normalized_path = (_string(target_path) or "").replace("\\", "/")
    if kind == "living_map":
        return "living_map", kind
    if kind == "idea_packet":
        return "idea_packet", kind
    if (
        kind
        and kind not in REFERENCE_ARTIFACT_DISALLOWED_KINDS
        and normalized_path.startswith(REFERENCE_ARTIFACT_GENERIC_ROOT)
    ):
        return "authored_obsidian_note", kind
    raise ValueError(
        "reference_artifact target must declare kind: living_map or kind: idea_packet, "
        "or be an authored obsidian note with frontmatter and a named section"
    )


def apply_reference_to_text(
    *,
    existing_text: str,
    target_kind: str,
    target_path: Optional[str] = None,
    source_key: str,
    source_artifact: str,
    observe_id: str,
    generated_at: str,
    payload_markdown: str,
    section_title: Optional[str] = None,
    summary: Optional[str] = None,
) -> Tuple[str, str]:
    """
    [ACTION]
    - Teleology: Apply a normalized observe reference block into an existing markdown target while enforcing target-family and section constraints.
    - Mechanism: Build a stable marker block, reject duplicates, resolve the target family, patch the requested section content in-memory, and return the rewritten text plus status.
    - Reads: Existing target text, reference metadata, and optional target path/section information.
    - Writes: None.
    - Guarantee: Returns `(new_text, "applied")` for a valid new insertion or `(existing_text, "duplicate")` when the same reference marker already exists.
    - Fails: Raises `ValueError` for unsupported target kinds, missing required sections, ambiguous sections, or invalid family-specific routing rules.
    - When-needed: Open when a grouped observe plan must inject a durable reference block into a living map, idea packet, or authored note before any file write occurs.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/kernel/commands/apply.py
    - Navigation-group: kernel_lib
    """
    marker, block = build_reference_block(
        source_key=source_key,
        source_artifact=source_artifact,
        observe_id=observe_id,
        generated_at=generated_at,
        payload_markdown=payload_markdown,
        summary=summary,
    )
    if marker in existing_text:
        return existing_text, "duplicate"

    card, body = parse_frontmatter(existing_text)
    body = body or ""
    target_family, resolved_kind = resolve_reference_artifact_target_family(
        target_text=existing_text,
        target_path=target_path,
    )
    kind = normalize_heading_title(target_family)
    target_section = _string(section_title)
    if kind == "living_map":
        target_section = target_section or "HISTORY"
        if normalize_heading_title(target_section) not in {
            normalize_heading_title("KNOWN"),
            normalize_heading_title("BROKEN"),
            normalize_heading_title("UNKNOWN"),
            normalize_heading_title("HISTORY"),
        }:
            raise ValueError("living_map reference target section must be one of KNOWN, BROKEN, UNKNOWN, HISTORY")
        if observe_id:
            card["last_observe_id"] = observe_id
        if generated_at:
            card["last_worked_at"] = generated_at[:10]
    elif kind == "idea_packet":
        if not target_section:
            raise ValueError("section_title is required when referencing an idea_packet")
    elif kind == normalize_heading_title("authored_obsidian_note"):
        if not target_section:
            raise ValueError("section_title is required when referencing an authored obsidian note")
    else:
        raise ValueError(f"Unsupported reference target kind: {resolved_kind or target_kind}")

    bounds = find_section_bounds(body, str(target_section))
    if bounds is None:
        raise ValueError(f"Section not found or ambiguous: {target_section}")
    _, _, content_start, content_end = bounds
    section_content = body[content_start:content_end].rstrip()
    new_section = section_content
    if new_section:
        new_section = new_section + "\n\n" + block.rstrip()
    else:
        new_section = block.rstrip()
    new_body = body[:content_start] + "\n" + new_section + "\n" + body[content_end:]
    return render_markdown_document(card, new_body), "applied"


def apply_promotion_to_text(
    *,
    existing_text: str,
    mode: str,
    observe_id: str,
    source_artifact: str,
    generated_at: str,
    payload_markdown: str,
    section_title: Optional[str] = None,
) -> Tuple[str, str]:
    """
    [ACTION]
    - Teleology: Apply an observe promotion block into an existing markdown target for append-note or section-scoped promotion modes.
    - Mechanism: Build the promotion marker block, reject duplicates, and rewrite the requested note or section body in-memory according to the selected promotion mode.
    - Reads: Existing target text plus the promotion metadata and optional section title.
    - Writes: None.
    - Guarantee: Returns `(text, "applied")` for a valid new promotion or `(existing_text, "duplicate")` if the observe marker is already present.
    - Fails: Raises `ValueError` for unsupported modes, missing required section titles, or unresolved target sections.
    - When-needed: Open when a routed observe payload needs the exact in-memory promotion transform before the caller writes the updated markdown target.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/kernel/commands/apply.py
    """
    marker = f"<!-- observe-promotion:{observe_id} -->"
    if marker in existing_text:
        return existing_text, "duplicate"

    block = build_promotion_block(
        observe_id=observe_id,
        source_artifact=source_artifact,
        generated_at=generated_at,
        payload_markdown=payload_markdown,
    )
    frontmatter_text, body = split_frontmatter(existing_text)
    body = body or ""

    if mode == "append_note":
        base = existing_text.rstrip()
        if base:
            return base + "\n\n" + block, "applied"
        return block, "applied"

    if mode not in {"append_section", "replace_section"}:
        raise ValueError(f"Unsupported in-text promotion mode: {mode}")
    if not section_title:
        raise ValueError("section_title is required for section promotion modes")

    bounds = find_section_bounds(body, section_title)
    if bounds is None:
        raise ValueError(f"Section not found or ambiguous: {section_title}")
    _, _, content_start, content_end = bounds
    section_content = body[content_start:content_end].rstrip()

    if mode == "append_section":
        new_section = section_content
        if new_section:
            new_section = new_section + "\n\n" + block.rstrip()
        else:
            new_section = block.rstrip()
        new_body = body[:content_start] + "\n" + new_section + "\n" + body[content_end:]
        return frontmatter_text + new_body, "applied"

    new_body = body[:content_start] + "\n" + block.rstrip() + "\n" + body[content_end:]
    return frontmatter_text + new_body, "applied"


def create_note_from_payload(
    *,
    observe_id: str,
    source_artifact: str,
    generated_at: str,
    payload_markdown: str,
) -> str:
    """
    [ACTION]
    - Teleology: Render a new standalone note body from an observe payload for create-note promotion mode.
    - Guarantee: Returns the formatted promotion block string that becomes the initial content of a newly created note.
    - Fails: None.
    """
    return build_promotion_block(
        observe_id=observe_id,
        source_artifact=source_artifact,
        generated_at=generated_at,
        payload_markdown=payload_markdown,
    )


def format_repo_path(path: Path, root: Path) -> str:
    """
    [ACTION]
    - Teleology: Format an absolute path as a repo-relative string for display and error messages.
    - Guarantee: Returns the relative path string when `path` is under `root`, or the absolute string otherwise.
    - Fails: None.
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _validate_rooted_path(raw_path: Any, *, repo_root: Path, field_name: str) -> Optional[str]:
    token = _string(raw_path)
    if token is None:
        return None
    normalized = normalize_repo_relative_path(raw_path, repo_root=repo_root)
    if normalized is None:
        return f"{field_name} must resolve inside repo root ({repo_root})"
    if not normalized or normalized == ".":
        return f"{field_name} must resolve to a file path under repo root"
    return None


def normalize_repo_relative_path(raw_path: Any, *, repo_root: Path) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Resolve and normalize an arbitrary path reference to a forward-slash repo-relative string within the repo root.
    - Guarantee: Returns the normalized relative path string when the resolved path is inside `repo_root`, or `None` when the path escapes the root or is empty.
    - Fails: None.
    """
    token = _string(raw_path)
    if token is None:
        return None
    repo_root_resolved = repo_root.resolve()
    candidate = Path(token).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root_resolved / candidate).resolve()
    try:
        rel = resolved.relative_to(repo_root_resolved)
    except ValueError:
        return None
    return str(rel).replace("\\", "/")


def _unquote_yaml_scalar(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        inner = text[1:-1]
        if text[0] == '"':
            return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner.replace("''", "'")
    return text


def _frontmatter_scalar(text: str, key: str) -> Optional[str]:
    card, _ = parse_frontmatter(text)
    value = card.get(key)
    if value is None or isinstance(value, (list, dict)):
        return None
    return _string(value)


def markdown_kind(text: str) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Extract the `kind` frontmatter value from a markdown document string.
    - Guarantee: Returns the kind string when frontmatter declares a scalar `kind` field, or `None` when absent or non-scalar.
    - Fails: None.
    """
    return _frontmatter_scalar(text, "kind")


def _is_path_like_reference(token: str) -> bool:
    return Path(token).is_absolute() or "/" in token or "\\" in token or token.endswith(".md")


def _living_map_catalog(repo_root: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for path in sorted(repo_root.rglob("*.md")):
        try:
            rel_path = path.relative_to(repo_root)
        except ValueError:
            continue
        if any(part in _REFERENCE_MAP_SKIP_DIRS for part in rel_path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        kind = _frontmatter_scalar(text, "kind")
        if kind != "living_map":
            continue
        entries.append(
            {
                "path": str(rel_path).replace("\\", "/"),
                "id": _frontmatter_scalar(text, "id"),
                "boundary": _frontmatter_scalar(text, "boundary"),
                "summary": _frontmatter_scalar(text, "summary"),
            }
        )
    return entries


def resolve_reference_maps(raw_references: Any, *, repo_root: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    [ACTION]
    - Teleology: Resolve authored `reference_maps` tokens into concrete living-map targets inside the repo so grouped observe routing can bind to real notes instead of loose identifiers.
    - Mechanism: Catalog living-map markdown files, resolve each token by path or living-map id, reject ambiguous or out-of-root references, and return the resolved rows plus errors and warnings.
    - Reads: `raw_references`, `repo_root`, and all markdown files under `repo_root` that declare `kind: living_map`.
    - Writes: None.
    - Guarantee: Returns `(resolved, errors, warnings)` with duplicate paths suppressed into warnings and each successful result including path/id/boundary/summary metadata.
    - Fails: None by raising; malformed or ambiguous references are accumulated in the returned `errors`.
    - When-needed: Open when a routed observe plan names `reference_maps` or a legacy singular `reference_map` and the caller needs real living-map targets before validation or writeback.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; kernel.py
    """
    errors: List[str] = []
    warnings: List[str] = []
    resolved: List[Dict[str, Any]] = []
    if raw_references is None:
        return resolved, errors, warnings
    if not isinstance(raw_references, list):
        errors.append("reference_maps must be an array of strings when provided")
        return resolved, errors, warnings
    if not raw_references:
        errors.append("reference_maps must not be empty when provided")
        return resolved, errors, warnings

    catalog = _living_map_catalog(repo_root)
    by_path = {str(entry.get("path")): entry for entry in catalog if str(entry.get("path") or "").strip()}
    by_id: Dict[str, List[Dict[str, Any]]] = {}
    for entry in catalog:
        entry_id = _string(entry.get("id"))
        if entry_id:
            by_id.setdefault(entry_id, []).append(entry)

    seen_paths: set[str] = set()
    for idx, raw_item in enumerate(raw_references):
        token = _string(raw_item)
        if token is None:
            errors.append(f"reference_maps[{idx}] must be a non-empty string")
            continue

        match: Optional[Dict[str, Any]] = None
        resolution = ""
        if _is_path_like_reference(token):
            normalized_path = normalize_repo_relative_path(token, repo_root=repo_root)
            if normalized_path is None:
                errors.append(f"reference_maps[{idx}] must resolve inside repo root ({repo_root})")
                continue
            match = by_path.get(normalized_path)
            if match is None:
                candidate = (repo_root / normalized_path).resolve()
                if candidate.exists():
                    errors.append(
                        f"reference_maps[{idx}] must point to a markdown note with kind: living_map: {normalized_path}"
                    )
                else:
                    errors.append(f"reference_maps[{idx}] path not found: {normalized_path}")
                continue
            resolution = "path"
        else:
            id_matches = by_id.get(token, [])
            if len(id_matches) == 1:
                match = id_matches[0]
                resolution = "id"
            elif len(id_matches) > 1:
                dup_paths = ", ".join(sorted(str(entry.get("path")) for entry in id_matches))
                errors.append(f"reference_maps[{idx}] id is ambiguous across living maps: {token} -> {dup_paths}")
                continue
            else:
                errors.append(f"reference_maps[{idx}] must be a repo-relative path or living_map id: {token}")
                continue

        resolved_path = str(match.get("path") or "").strip()
        if resolved_path in seen_paths:
            warnings.append(f"reference_maps[{idx}] resolves to a duplicate living map and will be ignored: {resolved_path}")
            continue
        seen_paths.add(resolved_path)
        resolved.append(
            {
                "reference": token,
                "path": resolved_path,
                "id": _string(match.get("id")),
                "boundary": _string(match.get("boundary")),
                "summary": _string(match.get("summary")),
                "resolution": resolution,
            }
        )

    return resolved, errors, warnings


def validate_route_payload(payload: Dict[str, Any], *, repo_root: Path) -> Tuple[List[str], List[str]]:
    """
    [ACTION]
    - Teleology: Preflight the routed-observe fields on one grouped observe plan so invalid routing combinations are caught before execution or markdown writeback.
    - Mechanism: Detect whether routing is declared, normalize the route config, validate booleans/frontmatter/reference maps/promotion coupling/path rooting, and return accumulated errors and warnings.
    - Reads: `payload`, `repo_root`, `has_routing_fields()`, `normalize_route_config()`, and `resolve_reference_maps()`.
    - Writes: None.
    - Guarantee: Returns `(errors, warnings)`; non-routed plans return two empty lists without further work.
    - Fails: None by raising for validation issues; problems are accumulated in the returned error and warning lists.
    - When-needed: Open when a grouped observe plan includes routed markdown fields and must be accepted or rejected before `run_observe_plan` touches any targets.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; kernel.py
    - Navigation-group: kernel_lib
    """
    errors: List[str] = []
    warnings: List[str] = []
    grouped_mode = isinstance(payload.get("groups"), list) and bool(payload.get("groups"))
    route_declared = has_routing_fields(payload)
    if not route_declared:
        return errors, warnings

    if not grouped_mode:
        errors.append("Routing fields are only supported for grouped observe plans")
        return errors, warnings

    route = normalize_route_config(payload)
    bool_fields = ("embed_original_plan", "concatenate_group_outputs")
    for field in bool_fields:
        raw_value = payload.get(field)
        if raw_value is not None and not isinstance(raw_value, bool):
            errors.append(f"{field} must be a boolean when provided")

    if payload.get("result_note_frontmatter") is not None and not isinstance(payload.get("result_note_frontmatter"), dict):
        errors.append("result_note_frontmatter must be a JSON object when provided")

    result_note_path = route["result_note_path"]
    if result_note_path is None:
        errors.append("result_note_path is required when using routed observe fields")
    else:
        path_error = _validate_rooted_path(result_note_path, repo_root=repo_root, field_name="result_note_path")
        if path_error:
            errors.append(path_error)

    raw_kind = payload.get("result_note_kind")
    if raw_kind is not None and not isinstance(raw_kind, str):
        errors.append("result_note_kind must be a string when provided")

    _, reference_errors, reference_warnings = resolve_reference_maps(
        payload.get("reference_maps"),
        repo_root=repo_root,
    )
    errors.extend(reference_errors)
    warnings.extend(reference_warnings)

    promotion_target = route["promotion_target_path"]
    promotion_mode = route["promotion_mode"]
    promotion_section = route["promotion_section"]
    promotion_gate = route["promotion_gate"]

    if bool(promotion_target) != bool(promotion_mode):
        errors.append("promotion_target_path and promotion_mode must be provided together")

    if payload.get("promotion_mode") is not None and promotion_mode not in PROMOTION_MODES:
        errors.append(
            "promotion_mode must be one of: create_note, append_note, append_section, replace_section, reference_artifact"
        )

    if payload.get("promotion_gate") is not None and promotion_gate not in PROMOTION_GATES:
        errors.append("promotion_gate must be one of: manual, auto")

    if promotion_mode in {"append_section", "replace_section"} and not promotion_section:
        errors.append("promotion_section is required for append_section and replace_section")
    if promotion_mode in {"create_note", "append_note"} and promotion_section:
        errors.append("promotion_section is only valid for append_section and replace_section")

    if promotion_target:
        path_error = _validate_rooted_path(
            promotion_target,
            repo_root=repo_root,
            field_name="promotion_target_path",
        )
        if path_error:
            errors.append(path_error)

        target_path = (repo_root / promotion_target).resolve()
        auto_gate = promotion_gate == "auto"
        if promotion_mode == "create_note":
            if target_path.exists():
                message = f"promotion target already exists for create_note: {promotion_target}"
                (errors if auto_gate else warnings).append(message)
        elif promotion_mode:
            if not target_path.exists():
                message = f"promotion target not found for {promotion_mode}: {promotion_target}"
                (errors if auto_gate else warnings).append(message)
            elif promotion_mode == "reference_artifact":
                try:
                    target_text = target_path.read_text(encoding="utf-8")
                except Exception as exc:
                    errors.append(f"promotion target could not be read for reference_artifact: {promotion_target} ({exc})")
                else:
                    try:
                        target_family, target_kind = resolve_reference_artifact_target_family(
                            target_text=target_text,
                            target_path=promotion_target,
                        )
                    except ValueError as exc:
                        errors.append(str(exc))
                        target_family = None
                    if target_family == "idea_packet" and not promotion_section:
                        errors.append("promotion_section is required for reference_artifact when target kind is idea_packet")
                    elif target_family == "authored_obsidian_note" and not promotion_section:
                        errors.append("promotion_section is required for reference_artifact when target is an authored obsidian note")
                    if target_family == "living_map" and promotion_section:
                        normalized_section = normalize_heading_title(promotion_section)
                        if normalized_section not in {
                            normalize_heading_title("KNOWN"),
                            normalize_heading_title("BROKEN"),
                            normalize_heading_title("UNKNOWN"),
                            normalize_heading_title("HISTORY"),
                        }:
                            errors.append(
                                "promotion_section for reference_artifact living_map targets must be one of: KNOWN, BROKEN, UNKNOWN, HISTORY"
                            )
                    elif target_family in {"idea_packet", "authored_obsidian_note"} and promotion_section:
                        _, target_body = parse_frontmatter(target_text)
                        if find_section_bounds(target_body or "", promotion_section) is None:
                            errors.append(
                                f"promotion_section for reference_artifact target was not found or was ambiguous: {promotion_section}"
                            )

    return errors, warnings
