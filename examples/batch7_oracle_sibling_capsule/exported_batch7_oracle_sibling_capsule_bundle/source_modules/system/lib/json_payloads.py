"""

[PURPOSE]
- Teleology: Recover valid JSON payloads from mixed markdown, prose, or malformed AI output without forcing each caller to reimplement repair heuristics.
- Mechanism: Strip fenced wrappers, generate parse candidates from the source text, repair common inner-quote breakage, and expose extractors for any JSON value or object.

[INTERFACE]
- Exports: strip_json_code_fence, repair_unescaped_inner_quotes, json_candidate_blocks, extract_json_value, extract_json_object.
- Reads: Caller-provided text only.
- Writes: None.

[FLOW]
- Normalize the raw text -> derive candidate blocks -> try direct JSON parses -> repair the full source or candidate fragments when needed -> return the first valid value or object.

[DEPENDENCIES]
- Couples: Standard JSON decoding determines syntactic validity; object-only extraction additionally requires a mapping result.

[CONSTRAINTS]
- Fails: extract_json_value/object raise ValueError when no candidate decodes to the required JSON shape.
- Guarantee: Functions are side-effect free and only transform caller-supplied strings into cleaned text, candidate blocks, or parsed JSON values.
- Non-goal: This module does not validate the semantic schema of parsed JSON payloads; it only recovers syntactically valid JSON.
- When-needed: Open when a kernel or server surface needs the repo-standard JSON recovery heuristics for AI-generated text instead of calling `json.loads()` directly.
- Escalates-to: system/lib/kernel/commands/observe.py; system/server/main.py
- Navigation-group: kernel_lib

"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def strip_json_code_fence(text: str) -> str:
    """
    [ACTION]
    - Teleology: Remove outer markdown code-fence framing so downstream JSON parsing sees only the payload body.
    - Mechanism: Trim the text, peel a leading and trailing triple-backtick fence when present, and drop a standalone `json` language marker line.
    - Reads: Caller-provided text only.
    - Guarantee: Returns the original stripped text when no outer fence is present and otherwise returns the de-fenced payload body.
    - Fails: None.
    - When-needed: Open when a caller has markdown-wrapped JSON and needs the exact fence-stripping behavior before further recovery passes.
    - Escalates-to: system/lib/kernel/commands/observe.py; system/server/main.py
    """
    stripped = str(text or "").strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if not lines:
        return stripped
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    if lines and lines[0].strip().casefold() == "json":
        lines = lines[1:]
    return "\n".join(lines).strip()


def repair_unescaped_inner_quotes(text: str) -> str:
    """
    [ACTION]
    - Teleology: Repair a common AI-output failure mode where valid JSON structure is broken by unescaped inner double quotes inside string values.
    - Mechanism: Run a character-wise state machine that tracks JSON string context, container shape, and likely closing delimiters, escaping quotes that look embedded rather than structural.
    - Reads: Caller-provided text only.
    - Guarantee: Returns a transformed string that preserves the original text except for quote escapes inserted where the heuristic classifies a quote as embedded.
    - Fails: None.
    - When-needed: Open when `json.loads()` is failing on likely inner-quote corruption and you need the repo-standard repair heuristic rather than a one-off regex.
    - Escalates-to: system/lib/kernel/commands/observe.py; system/server/main.py

    ChatGPT commonly generates anchor strings like::

        "<private-obsidian-root>/.../synth_seed.json :: "success_criteria""

    where the inner quotes are not escaped.  This function uses a simple
    state-machine to detect embedded quotes inside string values and escape
    them, producing valid JSON.

    Algorithm (per character):
    - Track whether we are inside a JSON string plus the current container
      stack (object/array) so we can distinguish object-key strings from
      value strings.
    - When a ``"`` is seen outside a string it opens a new string and records
      whether that string is acting as an object key or a value.
    - When a ``"`` is seen inside a string we look one character ahead
      (skipping whitespace) to decide whether it legitimately closes the
      string:
        * Object-key strings may close before ``:``.
        * Value strings may close before ``,``, ``}``, ``]``, or end-of-text.
        * If the next two non-whitespace characters are ``"`` followed by a
          legitimate closer, the first quote is treated as embedded and is
          escaped.
        * Otherwise the quote is assumed to be embedded and is escaped to
          ``\"``.
    - Backslash-escaped characters (``\\x``) inside strings are forwarded
      verbatim and do not trigger the above logic.
    """
    result: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape_next = False
    string_role = "value"
    string_container_type = ""
    inner_brace_depth = 0
    inner_bracket_depth = 0
    inner_paren_depth = 0
    container_stack: list[dict[str, str]] = []

    while i < n:
        ch = text[i]

        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue

        if ch == "\\" and in_string:
            result.append(ch)
            escape_next = True
            i += 1
            continue

        if not in_string:
            if ch == '"':
                top = container_stack[-1] if container_stack else None
                if top and top.get("type") == "object" and top.get("expect") in {"key", "key_or_end"}:
                    string_role = "key"
                else:
                    string_role = "value"
                string_container_type = str(top.get("type") or "") if top else ""
                inner_brace_depth = 0
                inner_bracket_depth = 0
                inner_paren_depth = 0
                in_string = True
                result.append(ch)
                i += 1
                continue
            if ch == "{":
                container_stack.append({"type": "object", "expect": "key_or_end"})
            elif ch == "[":
                container_stack.append({"type": "array", "expect": "value_or_end"})
            elif ch == ":":
                top = container_stack[-1] if container_stack else None
                if top and top.get("type") == "object":
                    top["expect"] = "value"
            elif ch == ",":
                top = container_stack[-1] if container_stack else None
                if top and top.get("type") == "object":
                    top["expect"] = "key"
                elif top and top.get("type") == "array":
                    top["expect"] = "value"
            elif ch == "}":
                if container_stack and container_stack[-1].get("type") == "object":
                    container_stack.pop()
            elif ch == "]":
                if container_stack and container_stack[-1].get("type") == "array":
                    container_stack.pop()
            result.append(ch)
            i += 1
            continue

        # --- inside a string ---
        if ch != '"':
            if string_role == "value":
                if ch == "{":
                    inner_brace_depth += 1
                elif ch == "}" and inner_brace_depth > 0:
                    inner_brace_depth -= 1
                elif ch == "[":
                    inner_bracket_depth += 1
                elif ch == "]" and inner_bracket_depth > 0:
                    inner_bracket_depth -= 1
                elif ch == "(":
                    inner_paren_depth += 1
                elif ch == ")" and inner_paren_depth > 0:
                    inner_paren_depth -= 1
            result.append(ch)
            i += 1
            continue

        # We hit a '"' while inside a string.  Look ahead to classify it.
        j = i + 1
        while j < n and text[j] in " \t\r\n":
            j += 1
        next_ch = text[j] if j < n else ""

        if string_role == "key":
            terminators = {":"}
        elif string_container_type == "array":
            terminators = {",", "]", ""}
        else:
            terminators = {",", "}", ""}

        nested_code_open = inner_brace_depth > 0 or inner_bracket_depth > 0 or inner_paren_depth > 0
        if string_role == "value" and nested_code_open and next_ch in {",", "}", "]"}:
            result.append('\\"')
            i += 1
            continue

        if next_ch in terminators:
            # Looks like a legitimate string closer.
            in_string = False
            result.append('"')
            i += 1
            continue

        if next_ch == '"':
            # Two consecutive quotes: check what follows the second one.
            j2 = j + 1
            while j2 < n and text[j2] in " \t\r\n":
                j2 += 1
            after_pair = text[j2] if j2 < n else ""
            if after_pair in terminators or after_pair == "":
                # Pattern: <content>"" <terminator>
                # The first '"' is an embedded quote; the second closes.
                result.append('\\"')
                i += 1
                continue
            else:
                # Ambiguous — treat as string closer.
                in_string = False
                result.append('"')
                i += 1
                continue

        # next_ch is not a terminator or '"' — assume this is an embedded quote.
        result.append('\\"')
        i += 1

    return "".join(result)


def _repair_candidates(candidates: list[str]) -> list[str]:
    """Return repaired versions of *candidates* that failed direct JSON parse."""
    repaired: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        fixed = repair_unescaped_inner_quotes(candidate)
        token = fixed.strip()
        if token and token not in seen:
            seen.add(token)
            repaired.append(fixed)
    return repaired


def json_candidate_blocks(text: str, *, max_candidates: int = 64) -> list[str]:
    """
    [ACTION]
    - Teleology: Generate a ranked set of likely JSON fragments from mixed markdown or prose so callers can try parses in a deliberate order.
    - Mechanism: Collect fenced blocks, line-oriented `JSON` sections, `raw_decode` fragments from `{` and `[` offsets, and the full source text as a final fallback.
    - Reads: Caller-provided text, `_FENCED_JSON_RE`, and `json.JSONDecoder.raw_decode()`.
    - Guarantee: Returns candidate strings in the documented priority order with duplicates removed and total raw-decode probes capped by `max_candidates`.
    - Fails: None.
    - When-needed: Open when a recovery path needs the repo-standard JSON candidate ordering before parse or repair retries.
    - Escalates-to: system/lib/kernel/commands/observe.py; system/server/main.py

    Ordering is deliberate:
    1. fenced JSON/code blocks
    2. line-oriented `JSON` blocks
    3. raw_decode hits from every `{` / `[` sorted largest-first
    4. full source text as the final fallback
    """
    source = str(text or "")
    if not source.strip():
        return []

    decoder = json.JSONDecoder()
    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        cleaned = strip_json_code_fence(candidate)
        token = cleaned.strip()
        if not token or token in seen:
            return
        seen.add(token)
        candidates.append(token)

    for match in _FENCED_JSON_RE.finditer(source):
        add(match.group(1))

    lines = source.splitlines()
    for index, line in enumerate(lines):
        if line.strip().casefold() != "json":
            continue
        block: list[str] = []
        for inner in lines[index + 1 :]:
            if inner.startswith("## "):
                break
            block.append(inner)
        add("\n".join(block))

    raw_hits: list[tuple[int, str]] = []
    for match in re.finditer(r"[\{\[]", source):
        if len(raw_hits) >= max_candidates:
            break
        try:
            _, end = decoder.raw_decode(source, match.start())
        except json.JSONDecodeError:
            continue
        fragment = source[match.start():end]
        raw_hits.append((len(fragment), fragment))
    for _size, fragment in sorted(raw_hits, key=lambda item: item[0], reverse=True):
        add(fragment)

    add(source.strip())
    return candidates


def extract_json_value(text: str) -> Any:
    """
    [ACTION]
    - Teleology: Recover the first syntactically valid JSON value from mixed text using the module's candidate and repair strategy.
    - Mechanism: Try raw candidates first, then re-scan the fully repaired source, then repair each original candidate individually until one parses.
    - Reads: `json_candidate_blocks()`, `repair_unescaped_inner_quotes()`, `_repair_candidates()`, and `json.loads()`.
    - Guarantee: Returns the first successfully parsed JSON value from the recovery passes.
    - Fails: Raises `ValueError` when no valid JSON value can be recovered.
    - When-needed: Open when a caller needs the module's full multi-pass JSON recovery path for any JSON value, not just objects.
    - Escalates-to: system/lib/kernel/commands/observe.py; system/server/main.py

    Extraction strategy (in order):

    1. Collect candidate blocks from the raw source text (fenced blocks,
       line-level JSON blocks, ``raw_decode`` fragments sorted largest-first,
       full source text).  Try to parse each candidate directly.

    2. Repair the *entire* source text using
       :func:`repair_unescaped_inner_quotes` (handles the common ChatGPT
       pattern where an AI emits a large top-level JSON object containing
       embedded unescaped double-quotes inside string values — the top-level
       ``{`` fails ``raw_decode`` so it never makes it into the candidates
       list in pass 1).  Re-collect candidates from the repaired source and
       try each.

    3. Repair every individual candidate from pass 1 and retry.
    """
    source = str(text or "").strip()
    candidates = json_candidate_blocks(source)
    last_error: str | None = None

    # Pass 1: try raw candidates (largest valid fragment first)
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            continue

    # Pass 2: repair the whole source and re-scan for candidates.
    # This handles top-level JSON objects that contain unescaped quotes —
    # raw_decode never finds them because the outer { fails to parse, so
    # they never appear in the pass-1 candidate list.
    repaired_source = repair_unescaped_inner_quotes(source)
    if repaired_source != source:
        for candidate in json_candidate_blocks(repaired_source):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as exc:
                last_error = str(exc)
                continue

    # Pass 3: repair each original candidate individually
    for candidate in _repair_candidates(candidates):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            continue

    raise ValueError(last_error or "text did not contain valid JSON")


def extract_json_object(text: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Recover the first mapping-shaped JSON object from mixed text without letting inner arrays or scalar fragments win prematurely.
    - Mechanism: Prefer a fully repaired top-level source parse, then scan raw candidates, repaired-source candidates, and repaired individual candidates while accepting only `Mapping` results.
    - Reads: `repair_unescaped_inner_quotes()`, `json_candidate_blocks()`, `_repair_candidates()`, and `json.loads()`.
    - Guarantee: Returns the first parsed JSON object as a plain dict and skips valid non-object JSON values in every pass.
    - Fails: Raises `ValueError` when no JSON object can be recovered.
    - When-needed: Open when a caller must recover a top-level JSON object from noisy AI output and cannot accept arrays or scalar fragments as success.
    - Escalates-to: system/lib/kernel/commands/observe.py; system/server/main.py

    Unlike :func:`extract_json_value`, this function skips JSON arrays and
    scalars in every pass and only returns when it finds a ``dict``.  This
    prevents a valid inner list from being returned prematurely while a
    top-level JSON object that just needs quote-repair is available.

    Passes:

    1. Try each raw candidate from :func:`json_candidate_blocks`; accept only
       dicts.
    2. Repair the full source text and re-collect candidates; accept only
       dicts.
    3. Repair each original candidate individually; accept only dicts.
    """
    source = str(text or "").strip()
    candidates = json_candidate_blocks(source)
    last_error: str | None = None

    # Pass 0: repair the full source text and try it *directly* first.
    # This takes priority over inner fragments so that a large top-level
    # object that merely needs quote-repair is not beaten by a small valid
    # inner dict that was picked up by raw_decode.
    repaired_source = repair_unescaped_inner_quotes(source)
    if repaired_source != source:
        try:
            val = json.loads(repaired_source)
            if isinstance(val, Mapping):
                return dict(val)
        except json.JSONDecodeError as exc:
            last_error = str(exc)

    # Pass 1: raw candidates, objects only
    for candidate in candidates:
        try:
            val = json.loads(candidate)
            if isinstance(val, Mapping):
                return dict(val)
        except json.JSONDecodeError as exc:
            last_error = str(exc)

    # Pass 2: re-scan repaired source for object candidates
    if repaired_source != source:
        for candidate in json_candidate_blocks(repaired_source):
            try:
                val = json.loads(candidate)
                if isinstance(val, Mapping):
                    return dict(val)
            except json.JSONDecodeError as exc:
                last_error = str(exc)

    # Pass 3: repair each original candidate individually
    for candidate in _repair_candidates(candidates):
        try:
            val = json.loads(candidate)
            if isinstance(val, Mapping):
                return dict(val)
        except json.JSONDecodeError as exc:
            last_error = str(exc)

    raise ValueError(last_error or "text did not contain a JSON object")
