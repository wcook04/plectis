"""Shared public paper conversion and reader-index renderer.

This portable owner is copied byte for byte into each public paper corpus.
The publication exporter and native-clone refresher use the same functions.
"""
from __future__ import annotations

import hashlib
import html
import json
import posixpath
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

CORPUS_DIR_REL = "docs/papers"
NATIVE_REFRESH_COMMAND = "python3 scripts/papers/refresh_paper_corpus.py --write"


def normalise_native_refresh_metadata(corpus: dict[str, Any]) -> dict[str, Any]:
    """Update only the generated clone-local command, preserving paper records."""
    result = dict(corpus)
    if "native_refresh_command" in result:
        result["native_refresh_command"] = NATIVE_REFRESH_COMMAND
    return result

FULL_TEXT_DIR = "full-text"

AUTHORITY_ORDER = (
    "checked Lean source is proof authority; the claims registry owns public "
    "status and coordinates; methodology owns transition rules; the paper owns "
    "exposition"
)

# --------------------------------------------------------------------------
# pandoc AST handling
# --------------------------------------------------------------------------

# Inline nodes whose content is a bare list of inlines.
_PLAIN_INLINE_CONTAINERS = {
    "Emph", "Strong", "Strikeout", "Superscript", "Subscript", "SmallCaps", "Para", "Plain",
}
# Inline nodes shaped [attr, [inline]] or [attr, [inline], target].
_ATTR_INLINE_CONTAINERS = {"Span", "Link", "Image"}


def _stringify(node: Any) -> str:
    """Plain text of a pandoc inline tree.

    Written out by node shape rather than by guessing, because pandoc's content
    field means different things per node: ``Code`` is ``[attr, str]`` while
    ``Emph`` is ``[inline]``, and a generic "recurse into lists of dicts" walk
    silently drops the former. That bug produced section titles with holes.
    """
    if isinstance(node, list):
        return "".join(_stringify(n) for n in node)
    if not isinstance(node, dict):
        return ""
    tag = node.get("t")
    content = node.get("c")
    if tag == "Str":
        return content if isinstance(content, str) else ""
    if tag in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if tag in _PLAIN_INLINE_CONTAINERS:
        return _stringify(content)
    if tag in _ATTR_INLINE_CONTAINERS:
        return _stringify(content[1]) if isinstance(content, list) and len(content) > 1 else ""
    if tag in ("Code", "Math", "RawInline"):
        # [attr_or_type, string]
        return content[1] if isinstance(content, list) and len(content) > 1 else ""
    if tag == "Quoted":
        return _stringify(content[1]) if isinstance(content, list) and len(content) > 1 else ""
    if tag == "Cite":
        return _stringify(content[1]) if isinstance(content, list) and len(content) > 1 else ""
    if tag == "Note":
        return ""
    if isinstance(content, list):
        return "".join(_stringify(n) for n in content if isinstance(n, (dict, list)))
    return ""


def _render_citation(node: dict[str, Any]) -> dict[str, Any]:
    """``Cite`` -> visible bracketed key, because GFM otherwise emits nothing.

    These papers declare their bibliography inline with ``thebibliography``
    rather than a ``.bib``, so pandoc has citation *data* in the AST but no
    citeproc database to format against, and its Markdown writer drops the node
    entirely -- turning "Erdos's 1948 theorem~\\cite{erdos1948}." into
    "Erdos's 1948 theorem ." with a dangling space. The keys are stable and
    resolvable against the bibliography section that does survive, so emitting
    the key is both honest and useful.
    """
    citations = node["c"][0]
    parts: list[str] = []
    for citation in citations:
        key = citation.get("citationId", "")
        prefix = _stringify(citation.get("citationPrefix")).strip()
        suffix = _stringify(citation.get("citationSuffix")).strip()
        text = f"{prefix} {key}".strip() if prefix else key
        if suffix:
            text = f"{text}, {suffix}"
        parts.append(text)
    return {"t": "Str", "c": "[" + "; ".join(parts) + "]"}


class _AstWalk:
    """One pass that fixes citations, anchors headers, and indexes sections."""

    _SHARED_STATEMENTS = {
        "theorem", "proposition", "lemma", "corollary", "definition", "example", "problem",
    }

    def __init__(self, *, section_numbered_statements: bool = False,
                 front_title_id: str = "") -> None:
        self.sections: list[dict[str, Any]] = []
        self.citations_rendered = 0
        self.section_numbered_statements = section_numbered_statements
        self.front_title_id = front_title_id
        self.section_number = 0
        self.statement_number = 0
        self.statement_numbers: dict[str, str] = {}
        self.equation_labels: set[str] = set()
        self.reference_labels: set[str] = set()

    def blocks(self, blocks: list[Any]) -> list[Any]:
        out: list[Any] = []
        for block in blocks:
            if isinstance(block, dict) and block.get("t") == "Header":
                level, attr, inlines = block["c"]
                anchor = attr[0]
                title = _stringify(inlines).strip()
                if (self.section_numbered_statements and level == 1
                        and anchor != self.front_title_id
                        and "unnumbered" not in attr[1]):
                    self.section_number += 1
                    self.statement_number = 0
                if anchor:
                    # A raw HTML anchor survives into GFM, where pandoc's header
                    # attributes do not. Without it the paper's own \label ids --
                    # the stable names everything else refers to -- would not
                    # exist in the generated file at all.
                    out.append({"t": "RawBlock", "c": ["html", f'<a id="{anchor}"></a>']})
                    self.reference_labels.add(anchor)
                self.sections.append({"level": level, "id": anchor, "title": title})
            if (self.section_numbered_statements and isinstance(block, dict)
                    and block.get("t") == "Div"):
                attr, body = block["c"]
                if attr[1] and attr[1][0] in self._SHARED_STATEMENTS:
                    self.statement_number += 1
                    number = f"{self.section_number}.{self.statement_number}"
                    first = body[0]["c"][0]["c"]
                    if (len(first) < 3 or first[2].get("t") != "Str"
                            or not re.fullmatch(r"\d+", first[2].get("c", ""))):
                        raise RuntimeError(f"cannot number statement {attr[0]}")
                    first[2]["c"] = number
                    if attr[0]:
                        self.statement_numbers[attr[0]] = number
            out.extend(self.node([block]))
        return out

    def node(self, node: Any) -> Any:
        if isinstance(node, list):
            out: list[Any] = []
            for item in node:
                if isinstance(item, dict) and item.get("t") == "Figure" and item["c"][0][0]:
                    label = item["c"][0][0]
                    # GitHub removes the figure wrapper and its id. Move the
                    # label to a surviving anchor without altering the caption.
                    out.append({"t": "RawBlock", "c": ["html", f'<a id="{html.escape(label, quote=True)}"></a>']})
                    self.reference_labels.add(label)
                    item["c"][0][0] = ""
                if isinstance(item, dict) and item.get("t") in {"Emph", "Strong"}:
                    styled = self.node(item)
                    if not any(child.get("t") == "Math" and child["c"][0].get("t") == "DisplayMath"
                               for child in styled["c"]):
                        out.append(styled)
                        continue
                    # Inline emphasis cannot wrap a fenced display in GFM:
                    # Pandoc otherwise writes an invalid closing line ```*.
                    # Keep prose styling on each side and leave math untouched.
                    run: list[Any] = []

                    def flush() -> None:
                        whitespace = {"Space", "SoftBreak", "LineBreak"}
                        while run and run[0].get("t") in whitespace:
                            out.append(run.pop(0))
                        trailing = []
                        while run and run[-1].get("t") in whitespace:
                            trailing.insert(0, run.pop())
                        if run:
                            out.append({"t": styled["t"], "c": run[:]})
                        out.extend(trailing)
                        run.clear()

                    for child in styled["c"]:
                        display = child.get("t") == "Math" and child["c"][0].get("t") == "DisplayMath"
                        anchor = (child.get("t") == "RawInline" and child["c"][0] == "html"
                                  and child["c"][1].startswith("\n\n<a id="))
                        if display or anchor:
                            flush()
                            out.append(child)
                        else:
                            run.append(child)
                    flush()
                    continue
                if (isinstance(item, dict) and item.get("t") == "Math"
                        and item["c"][0].get("t") == "DisplayMath"):
                    labels = list(dict.fromkeys(re.findall(
                        r"\\label\{([^{}]+)\}", _TEX_COMMENT_RE.sub("", item["c"][1])
                    )))
                    if labels:
                        # GitHub's math renderer does not expose TeX labels as
                        # DOM targets. Keep targets outside the unchanged math,
                        # with blank lines so GFM still recognises its fence.
                        anchors = "\n".join(
                            f'<a id="{html.escape(label, quote=True)}"></a>'
                            for label in labels
                        )
                        out.append({"t": "RawInline", "c": ["html", f"\n\n{anchors}\n\n"]})
                        self.equation_labels.update(labels)
                out.append(self.node(item))
            return out
        if not isinstance(node, dict):
            return node
        if node.get("t") == "Math" and node["c"][0].get("t") == "DisplayMath":
            return {**node, "c": [node["c"][0], _unwrap_display_layout(node["c"][1])]}
        if node.get("t") in {"Div", "Span"} and node["c"][0][0]:
            # GFM retains labelled block and inline HTML targets.
            self.reference_labels.add(node["c"][0][0])
        if node.get("t") == "Cite":
            self.citations_rendered += 1
            return _render_citation(node)
        return {k: (self.node(v) if k == "c" else v) for k, v in node.items()}


def _equation_rows(body: str) -> list[str]:
    """Separate numbered alignment rows, retaining nested aligned displays."""
    if not re.match(r"\s*\\begin\{(?:align|alignat|flalign|gather)\*?\}", body):
        return [body]
    rows: list[str] = []
    depth, start = 0, 0
    for token in re.finditer(r"\\(?:begin|end)\{[^{}]+\}|\\\\(?:\*?(?:\[[^\]]*\])?)", body):
        if token.group().startswith("\\begin"):
            depth += 1
        elif token.group().startswith("\\end"):
            depth -= 1
        elif depth == 1:
            rows.append(body[start:token.start()])
            start = token.end()
    return [*rows, body[start:]]


def _tagged_equation_numbers(node: Any) -> dict[str, str]:
    """Read author-supplied display tags; do not guess TeX's equation counter."""
    numbers: dict[str, str] = {}
    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if value.get("t") == "Math" and isinstance(value.get("c"), list):
                body = value["c"][1]
                if isinstance(body, str):
                    for row in _equation_rows(_TEX_COMMENT_RE.sub("", body)):
                        tag = re.search(r"\\tag(\*?)\{([^{}]+)\}", row)
                        if tag:
                            number = tag.group(2) if tag.group(1) else f"({tag.group(2)})"
                            for label in re.findall(r"\\label\{([^{}]+)\}", row):
                                numbers[label] = number
            for child in value.values():
                visit(child)
    visit(node)
    return numbers


def _declared_equation_numbers(tex: str) -> dict[str, str]:
    """Read display numbers recorded for untagged equations in paper source.

    TeX's equation counter may be affected by earlier tagged displays, which
    Pandoc does not reproduce. These source comments are checked against the
    compiled PDF when the paper is reviewed; the converter never invents a
    number from an incomplete counter reconstruction.
    """
    numbers: dict[str, str] = {}
    for label, number in re.findall(
        r"(?m)^% paper-text-number: ([A-Za-z0-9:_-]+)=([A-Za-z0-9.]+)$",
        tex,
    ):
        if f"\\label{{{label}}}" not in tex or label in numbers:
            raise RuntimeError(f"stale or duplicate paper-text-number for {label}")
        numbers[label] = f"({number})"
    return numbers


def _render_numbered_references(node: Any, numbers: dict[str, str],
                                anchored_labels: set[str] | frozenset[str] = frozenset()) -> None:
    """Use recorded numbers and native GFM links only to emitted targets."""
    if isinstance(node, list):
        for item in node:
            _render_numbered_references(item, numbers, anchored_labels)
    elif isinstance(node, dict):
        if node.get("t") == "Link":
            attr, inlines, target = node["c"]
            metadata = dict(attr[2])
            label = metadata.get("reference")
            if (metadata.get("reference-type") in {"ref", "eqref"}
                    and target[0] == f"#{label}"):
                if label in numbers:
                    inlines[:] = [{"t": "Str", "c": numbers[label]}]
                if label in anchored_labels:
                    # Drop Pandoc-only metadata so its writer emits a native
                    # GFM link rather than an attributed raw HTML reference.
                    attr[2][:] = [pair for pair in attr[2]
                                  if pair[0] not in {"reference-type", "reference"}]
                    # A literal colon fragment also loses its href on GitHub;
                    # URI encoding keeps it linked to the unchanged DOM id.
                    target[0] = "#" + quote(label, safe="")
        for child in node.values():
            _render_numbered_references(child, numbers, anchored_labels)


_HTML_TARGET_TAG_RE = re.compile(
    r'''<!--.*?-->|<(?:a|div|span)\b(?:[^>"']|"[^"]*"|'[^']*')*>''', re.DOTALL | re.I
)
_HTML_ATTRIBUTE_RE = re.compile(
    r'''(?<!\S)([^\s"'<>/=]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))'''
)


def _html_attribute_value(attr: re.Match[str]) -> tuple[int, str]:
    for group in (2, 3, 4):
        if attr[group] is not None:
            return group, html.unescape(attr[group])
    raise ValueError("HTML attribute has no value")


def _rendered_anchor_labels(node: Any) -> set[str]:
    """Collect emitted targets, excluding code and mathematical literals."""
    labels: set[str] = set()
    if isinstance(node, list):
        for item in node:
            labels.update(_rendered_anchor_labels(item))
    elif isinstance(node, dict):
        tag, content = node.get("t"), node.get("c")
        if tag in {"Code", "CodeBlock", "Math"}:
            return labels
        if tag in {"Header", "Div", "Span", "Figure"}:
            attr = content[1] if tag == "Header" else content[0]
            if attr[0]:
                labels.add(attr[0])
        if tag in {"RawInline", "RawBlock"} and content[0] == "html":
            for target in _HTML_TARGET_TAG_RE.finditer(content[1]):
                if not target.group().startswith("<!--"):
                    labels.update(_html_attribute_value(attr)[1]
                                  for attr in _HTML_ATTRIBUTE_RE.finditer(target.group())
                                  if attr[1].lower() == "id")
        else:
            labels.update(_rendered_anchor_labels(content))
    return labels


def _case_safe_anchor_ids(labels: set[str]) -> dict[str, str]:
    """Disambiguate case-distinct targets that GitHub lowercases on delivery."""
    groups: dict[str, list[str]] = {}
    for label in sorted(labels):
        groups.setdefault(label.lower(), []).append(label)
    occupied = set(groups)
    renamed: dict[str, str] = {}
    for folded, group in sorted(groups.items()):
        if len(group) < 2:
            continue
        retained = folded if folded in group else group[0]
        for label in group:
            if label == retained:
                continue
            digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:8]
            base = f"{folded}--case-{digest}"
            candidate, suffix = base, 2
            while candidate in occupied:
                candidate = f"{base}-{suffix}"
                suffix += 1
            occupied.add(candidate)
            renamed[label] = candidate
    return renamed


def _remap_delivery_anchors(node: Any, renamed: dict[str, str]) -> None:
    """Change target coordinates and local links, preserving their contents."""
    if not renamed:
        return

    def fragment(target: str) -> str:
        if target.startswith("#") and (label := unquote(target[1:])) in renamed:
            return "#" + quote(renamed[label], safe="")
        return target

    def html_tag(match: re.Match[str]) -> str:
        tag = match.group()
        if tag.startswith("<!--"):
            return tag
        def attribute(attr: re.Match[str]) -> str:
            group, value = _html_attribute_value(attr)
            if attr[1].lower() == "id":
                replacement = renamed.get(value, value)
            elif attr[1].lower() == "href":
                replacement = fragment(value)
            else:
                replacement = value
            if replacement == value:
                return attr.group()
            start, end = attr.start(group) - attr.start(), attr.end(group) - attr.start()
            return attr.group()[:start] + html.escape(replacement, quote=True) + attr.group()[end:]
        return _HTML_ATTRIBUTE_RE.sub(attribute, tag)

    if isinstance(node, list):
        for item in node:
            _remap_delivery_anchors(item, renamed)
    elif isinstance(node, dict):
        tag, content = node.get("t"), node.get("c")
        if tag in {"Code", "CodeBlock", "Math"}:
            return
        if tag in {"Header", "Div", "Span", "Figure"}:
            attr = content[1] if tag == "Header" else content[0]
            attr[0] = renamed.get(attr[0], attr[0])
        if tag == "Link":
            content[2][0] = fragment(content[2][0])
        if tag in {"RawInline", "RawBlock"} and content[0] == "html":
            content[1] = _HTML_TARGET_TAG_RE.sub(html_tag, content[1])
        else:
            _remap_delivery_anchors(content, renamed)


def _pandoc(args: list[str], stdin: str | None = None, cwd: Path | None = None) -> str:
    """Run pandoc, and treat every potentially lossy warning as fatal.

    Both halves of this matter. ``cwd`` must be the manuscript's own directory,
    because these papers ``\\input`` a macro file by relative name; handing
    pandoc an absolute path from elsewhere makes that include unresolvable.

    Pandoc reports that failure as a *warning* on stderr while still exiting
    0. Every macro the missing file defined then expands to nothing, so whole
    passages disappear from the output with no error anywhere -- which is
    exactly what happened here, silently dropping the half-value subsections
    while the build reported success. A conversion that loses text is not a
    successful conversion, so warnings are escalated rather than printed.

    One warning class is explicitly non-lossy in the JSON-to-GFM pass:
    ``Could not convert TeX math ..., rendering as TeX``. In that case pandoc
    preserves the complete formula as a TeX math node in Markdown. The full
    reasoning papers use valid formula fragments that the GFM math writer does
    not simplify, so rejecting this fallback would make those real manuscripts
    impossible to export. No other warning is admitted.
    """
    result = subprocess.run(
        ["pandoc", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed ({result.returncode}): {result.stderr.strip()}")
    warnings = [
        line.strip()
        for line in result.stderr.splitlines()
        if line.strip()
    ]
    json_to_gfm = "-f" in args and args[args.index("-f") + 1] == "json"
    nonlossy_math_warning = re.compile(
        r"^\[WARNING\] Could not convert TeX math .+, rendering as TeX$"
    )
    fatal_warnings = [
        warning
        for warning in warnings
        if not (json_to_gfm and nonlossy_math_warning.fullmatch(warning))
    ]
    if fatal_warnings:
        raise RuntimeError(
            "pandoc emitted warnings; refusing to ship a possibly lossy conversion:\n"
            + "\n".join(fatal_warnings)
        )
    return result.stdout


def _meta_blocks(meta: dict[str, Any], stem: str) -> tuple[list[Any], str, str | None]:
    """Title, subtitle, and abstract as leading blocks, plus the plain title.

    Pandoc parks ``\\title``, ``\\subtitle`` and ``\\abstract`` in document
    metadata, and its Markdown writer emits none of them without a template. The
    result was a 64-page paper whose generated text began at "Introduction" --
    no title, no abstract. For a reader deciding whether this is the paper they
    want, that is the worst possible thing to drop.
    """
    title = _stringify(meta.get("title", {}).get("c")) if "title" in meta else ""
    subtitle = _stringify(meta.get("subtitle", {}).get("c")) if "subtitle" in meta else ""
    # Headers only -- the anchor for each is emitted by the walk that indexes
    # them, so adding one here too would double it.
    blocks: list[Any] = []
    if title:
        blocks.append({"t": "Header", "c": [1, [stem, [], []], [{"t": "Str", "c": title}]]})
    if subtitle:
        blocks.append({"t": "Para", "c": [{"t": "Emph", "c": [{"t": "Str", "c": subtitle}]}]})
    abstract = meta.get("abstract")
    if abstract is not None:
        blocks.append({"t": "Header", "c": [2, ["abstract", [], []], [{"t": "Str", "c": "Abstract"}]]})
        body = abstract.get("c")
        blocks.extend(body if isinstance(body, list) else [body])
    return blocks, title, subtitle or None


_DEF_RE = re.compile(r"\\long\\def\\([A-Za-z]+)\{")
_PATH_RE = re.compile(r"\\path\{")
_PDECL_RE = re.compile(r"\\pdecl\{([A-Za-z0-9_']+)\}")


def _matching_brace(text: str, open_index: int) -> int:
    """Index of the brace closing the one at ``open_index``.

    TeX-aware enough for these manuscripts: a backslash escapes the next
    character, and a percent starts a comment that runs to end of line. Both
    would otherwise let a stray brace unbalance the scan.
    """
    depth = 0
    i = open_index
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "%":
            newline = text.find("\n", i)
            if newline == -1:
                break
            i = newline + 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced brace while expanding a \\long\\def macro")


def _unwrap_display_layout(body: str) -> str:
    """Remove a complete, known PDF layout wrapper from a display payload.

    GitHub's math renderer does not implement these text-layout commands.
    Retain unknown, partial and mixed bodies; the recognized wrapper must
    contain exactly one dollar-delimited mathematical interior. Its bytes,
    including comments, newlines and labels, are returned unchanged.
    """
    text = body.strip()
    command = re.match(r"\\(adjustbox|resizebox)(?![A-Za-z*])", text)
    if command is None:
        return body
    count = 2 if command.group(1) == "adjustbox" else 3
    arguments: list[str] = []
    index = command.end()
    for _ in range(count):
        while index < len(text) and text[index].isspace():
            index += 1
        if text[index:index + 1] != "{":
            return body
        try:
            end = _matching_brace(text, index)
        except ValueError:
            return body
        arguments.append(text[index + 1:end])
        index = end + 1
    if text[index:].strip():
        return body
    options = [_TEX_COMMENT_RE.sub("", argument).strip() for argument in arguments[:-1]]
    if command.group(1) == "adjustbox":
        if not re.fullmatch(r"max\s+width\s*=\s*\\linewidth", options[0]):
            return body
    elif options != [r"\linewidth", "!"]:
        return body
    math = arguments[-1]
    if not (math.startswith("$") and math.endswith("$") and len(math) > 2):
        return body
    payload = math[1:-1]
    if not payload.strip():
        return body
    index = 0
    while index < len(payload):
        if payload[index] == "\\":
            index += 2
        elif payload[index] == "%":
            newline = payload.find("\n", index)
            index = len(payload) if newline < 0 else newline + 1
        elif payload[index] == "$":
            return body
        else:
            index += 1
    return payload


def _path_argument_end(text: str, open_index: int) -> int:
    """Return the close brace for a ``\\path`` argument.

    ``url``-package path arguments give characters such as ``%`` their literal
    meaning, so the ordinary TeX scanner above is deliberately not reused.
    Backslash escapes and nested braces are still honoured.
    """
    depth = 0
    index = open_index
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError("unbalanced brace in \\path argument")


def _preserve_path_macros(tex: str) -> str:
    """Translate ``\\path{...}`` to Pandoc-readable literal code.

    Pandoc's LaTeX reader silently removes ``\\path`` and its argument before
    producing an AST.  That left exported sentences with missing filenames and
    tool names even though conversion exited successfully.  ``\\verb`` has the
    same literal-text semantics needed by the Markdown projection and Pandoc
    emits it as inline code.
    """
    chunks: list[str] = []
    cursor = 0
    while True:
        match = _PATH_RE.search(tex, cursor)
        if match is None:
            chunks.append(tex[cursor:])
            return "".join(chunks)
        open_index = match.end() - 1
        close_index = _path_argument_end(tex, open_index)
        literal = tex[open_index + 1 : close_index]
        delimiter = next(
            (candidate for candidate in "|!+;:@?" if candidate not in literal),
            None,
        )
        if delimiter is None:
            raise ValueError(
                "\\path argument uses every supported literal delimiter"
            )
        chunks.extend(
            (
                tex[cursor : match.start()],
                f"\\verb{delimiter}{literal}{delimiter}",
            )
        )
        cursor = close_index + 1


def _preserve_layout_adjustbox(tex: str) -> str:
    """Keep the contents of the demonstrated layout-only ``\\adjustbox``.

    Pandoc silently discards both arguments outside math. Only the paper's
    ``max width=\\linewidth`` option is removed; other options may carry
    semantics. Comments, literal code and existing math bodies stay untouched.
    """
    protected_environments = {
        "verbatim", "verbatim*", "Verbatim", "BVerbatim", "LVerbatim",
        "lstlisting", "minted", "alltt", "comment", "math", "displaymath",
        "equation", "equation*", "align", "align*", "alignat", "alignat*",
        "flalign", "flalign*", "gather", "gather*", "multline", "multline*",
    }
    command_pattern = re.compile(r"\\([A-Za-z]+)\*?")

    def skip_space(index: int) -> int:
        while index < len(tex):
            if tex[index].isspace():
                index += 1
            elif tex[index] == "%":
                newline = tex.find("\n", index)
                index = len(tex) if newline < 0 else newline + 1
            else:
                break
        return index

    def skip_math(index: int, closing: str) -> int:
        while index < len(tex):
            if tex.startswith(closing, index):
                return index + len(closing)
            if tex[index] == "\\":
                index += 2
            elif tex[index] == "%":
                newline = tex.find("\n", index)
                index = len(tex) if newline < 0 else newline + 1
            else:
                index += 1
        return len(tex)

    chunks: list[str] = []
    cursor = index = 0
    while index < len(tex):
        if tex[index] == "%":
            index = skip_space(index)
            continue
        if tex[index] == "$":
            delimiter = "$$" if tex.startswith("$$", index) else "$"
            index = skip_math(index + len(delimiter), delimiter)
            continue
        if tex[index] != "\\":
            index += 1
            continue
        if tex.startswith((r"\(", r"\["), index):
            closing = r"\)" if tex[index + 1] == "(" else r"\]"
            index = skip_math(index + 2, closing)
            continue
        command = command_pattern.match(tex, index)
        if command is None:
            index += 2  # Includes escaped percent, dollar and backslash.
            continue
        name = command.group(1)
        argument = command.end()
        if name == "verb" and argument < len(tex):
            end = tex.find(tex[argument], argument + 1)
            index = len(tex) if end < 0 else end + 1
            continue
        argument = skip_space(argument)
        if name in {"begin", "texttt", "url", "path"} and tex[argument:argument + 1] == "{":
            close = (_path_argument_end(tex, argument) if name in {"url", "path"}
                     else _matching_brace(tex, argument))
            if name != "begin":
                index = close + 1
                continue
            environment = tex[argument + 1:close]
            if environment in protected_environments:
                closing = rf"\end{{{environment}}}"
                end = tex.find(closing, close + 1)
                index = len(tex) if end < 0 else end + len(closing)
                continue
        if (name != "adjustbox" or command.group().endswith("*")
                or tex[argument:argument + 1] != "{"):
            index = command.end()
            continue
        options_end = _matching_brace(tex, argument)
        body_start = skip_space(options_end + 1)
        if tex[body_start:body_start + 1] != "{":
            raise ValueError("missing body argument in \\adjustbox")
        body_end = _matching_brace(tex, body_start)
        options = _TEX_COMMENT_RE.sub("", tex[argument + 1:options_end])
        if re.fullmatch(r"\s*max\s+width\s*=\s*\\linewidth\s*", options):
            chunks.extend((tex[cursor:index], tex[body_start + 1:body_end]))
            cursor = body_end + 1
        index = body_end + 1
    chunks.append(tex[cursor:])
    return "".join(chunks)


def _readable_lean_label(identifier: str) -> str:
    """Reproduce the paper preamble's human-readable declaration label.

    The ``\\pdecl`` helper is intentionally presentation-only: unlike
    ``\\lword`` it carries no source coordinate. Pandoc silently drops an
    unknown one-argument macro and its argument, which previously turned lists
    of declarations into runs of empty commas. Preserve the manuscript's
    lower-case, spaced label rather than promoting it to a source link.
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", identifier)
    spaced = re.sub(r"_+", " ", spaced)
    return " ".join(spaced.split()).lower()


def _preserve_declaration_macros(tex: str) -> str:
    """Expand presentation-only ``\\pdecl`` uses before Pandoc sees them."""

    return _PDECL_RE.sub(
        lambda match: rf"\emph{{{_readable_lean_label(match.group(1))}}}",
        tex,
    )


_LEDGER_COMMIT_RE = re.compile(r"\\newcommand\{\\ledgercommit\}\{([0-9a-f]{40})\}")
_LPROOF_RE = re.compile(r"\\lproof\{([^{}]+)\}\{(\d+)\}\{([^{}]+)\}")
_LEANNOTE_RE = re.compile(r"\\leannote\{")
_PAPERSECTIONLINK_RE = re.compile(
    r"\\papersectionlink\{([^{}]+)\}\{([^{}]+)\}\{([^{}]+)\}"
)
_LEDGER_REPO = "https://github.com/wcook04/plectis-erdos/blob"


def _ledger_commit(tex: str, tex_path: Path) -> str | None:
    """The pin the manuscript's generated statement notes resolve at.

    The problem notes reach it through the shared preamble, which Pandoc never
    reads, so the shared file is consulted when the manuscript does not declare
    one itself.
    """

    match = _LEDGER_COMMIT_RE.search(tex)
    if match is not None:
        return match.group(1)
    for parent in tex_path.resolve().parents:
        shared = parent / "problem-note-preamble.tex"
        if shared.is_file():
            match = _LEDGER_COMMIT_RE.search(shared.read_text(encoding="utf-8"))
            return None if match is None else match.group(1)
    return None


def _preserve_generated_note_macros(tex: str, tex_path: Path) -> str:
    """Expand the generated statement note into links Pandoc can read.

    ``\\leannote`` and ``\\lproof`` are defined in a preamble Pandoc does not
    see, so without this the Markdown mirror would silently lose the line that
    carries each statement's Lean proof.  The rendered text matches the PDF:
    monospace declaration names in the two reasoning records, and the shared
    spaced reading everywhere else.
    """

    commit = _ledger_commit(tex, tex_path)
    monospace = "\\texttt{#3}" in tex

    def link(match: re.Match[str]) -> str:
        source, line, declaration = match.groups()
        label = (
            rf"\texttt{{{declaration}}}" if monospace
            else _readable_lean_label(declaration)
        )
        if commit is None:
            return label
        url = f"{_LEDGER_REPO}/{commit}/lean/{source}\\#L{line}"
        return rf"\href{{{url}}}{{{label}}}"

    tex = _LPROOF_RE.sub(link, tex)
    tex = _PAPERSECTIONLINK_RE.sub(
        lambda match: (
            rf"\href{{{match.group(1)}\#nameddest={match.group(2)}}}{{{match.group(3)}}}"
        ),
        tex,
    )
    chunks: list[str] = []
    cursor = 0
    while True:
        match = _LEANNOTE_RE.search(tex, cursor)
        if match is None:
            chunks.append(tex[cursor:])
            return "".join(chunks)
        open_index = match.end() - 1
        close_index = _matching_brace(tex, open_index)
        chunks.extend(
            (tex[cursor : match.start()], "\n\n", tex[open_index + 1 : close_index], "\n\n")
        )
        cursor = close_index + 1


# The #249 and #257 reasoning records cite a Lean declaration inline as
# \lean{declaration}{file:line}. Their own preamble defines \lean as
# \leanlink{#2}, and \leanlink is expl3 that builds the pinned source URL.
# Pandoc executes neither, so it dropped every citation and kept the
# punctuation around it: empty "()" in the prose. The expansion applies only
# where that definition is present, because the definition fixes the meaning.
_LEAN_CITATION_RE = re.compile(r"\\lean(?![A-Za-z])")
_LEAN_CITATION_DEFINITION_RE = re.compile(
    r"\\(?:re)?newcommand\s*\{\\lean\}\s*\[2\]\s*\{\\leanlink\{#2\}\}"
)
# The macros \leanlink builds its URL from. Their values are read from the
# manuscript, so no pin is ever copied into this renderer.
_LEANLINK_MACRO_DEFINITION_RE = re.compile(
    r"\\(?:re)?newcommand\s*\{\\(commit|repobase|latecommit|laterepobase|PK)\}"
    r"\s*\{([^{}]*)\}"
)
_LEANLINK_MACRO_USE_RE = re.compile(
    r"\\(commit|repobase|latecommit|laterepobase|PK)(?![A-Za-z])"
)
# \leanlink links a coordinate under one of these library roots from the
# repository root, and any other coordinate from the \PK tree. This transcribes
# the records' own test "\A (ErdosProblems|Erdos249257)/".
_LEANLINK_REPOSITORY_ROOTS_RE = re.compile(r"(?:ErdosProblems|Erdos249257)/")
_ALLOWBREAK_OR_SPACE_RE = re.compile(r"\\allowbreak(?![A-Za-z])|\s+")
_TEX_COMMENT_RE = re.compile(r"(?<!\\)%[^\n]*")
_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")
_UNESCAPED_DOLLAR_RE = re.compile(r"(?<!\\)\$")


def _tex_group(text: str, index: int) -> tuple[str, int] | None:
    """One ``{...}`` argument starting at ``index`` (after optional spaces).

    Returns the argument and the index after its closing brace, or ``None``
    when no complete group starts there.
    """
    while index < len(text) and text[index] in " \t\n":
        index += 1
    if index >= len(text) or text[index] != "{":
        return None
    try:
        close = _matching_brace(text, index)
    except ValueError:
        return None
    return text[index + 1 : close], close + 1


def _leanlink_definitions(tex: str) -> dict[str, str]:
    """The manuscript's own values of the macros ``\\leanlink`` expands.

    A later definition wins, as in TeX. Commented-out definitions are ignored.
    Each value is expanded through the others, so ``\\repobase`` becomes the
    URL at the manuscript's ``\\commit`` pin.
    """
    raw: dict[str, str] = {}
    for name, value in _LEANLINK_MACRO_DEFINITION_RE.findall(_TEX_COMMENT_RE.sub("", tex)):
        raw[name] = value.strip()
    resolved: dict[str, str] = {}
    for name, value in raw.items():
        for _depth in range(5):
            expanded = _LEANLINK_MACRO_USE_RE.sub(
                lambda match: raw.get(match.group(1), match.group(0)), value
            )
            if expanded == value:
                break
            value = expanded
        if not _LEANLINK_MACRO_USE_RE.search(value):
            resolved[name] = value
    return resolved


def _lean_citation_url(coordinate: str, macros: dict[str, str]) -> str:
    """The URL the reasoning records' ``\\leanlink`` builds from a coordinate.

    This transcribes the expl3 in their preamble. ``\\allowbreak`` and spaces
    are stripped. A ``lean/`` coordinate resolves at ``\\laterepobase``, a
    library-rooted one at ``\\repobase``, and any other one under
    ``\\repobase/\\PK``. ``file.lean:N`` anchors ``#LN``; ``:N-M`` and ``:N--M``
    anchor ``#LN-LM``; a list of lines links its first line; a coordinate with
    no ``.lean`` file links the path as written. The ``#`` is escaped for the
    TeX that Pandoc reads.
    """
    target = _ALLOWBREAK_OR_SPACE_RE.sub("", coordinate)
    if target.startswith("lean/"):
        needed: tuple[str, ...] = ("laterepobase",)
    elif _LEANLINK_REPOSITORY_ROOTS_RE.match(target):
        needed = ("repobase",)
    else:
        needed = ("repobase", "PK")
    missing = [name for name in needed if name not in macros]
    if missing:
        raise ValueError(
            "a \\lean citation needs the manuscript to define "
            + ", ".join(f"\\{name}" for name in missing)
            + f" (coordinate {target!r})"
        )
    url = "/".join(macros[name] for name in needed)
    located = re.match(r"(.*\.lean):?(.*)", target)
    if located is None:
        return f"{url}/{target}"
    url = f"{url}/{located.group(1)}"
    lines = re.search(r"([0-9]+)(?:-([0-9]+))?", located.group(2).replace("--", "-"))
    if lines is None:
        return url
    url += "\\#L" + lines.group(1)
    if lines.group(2):
        url += "-L" + lines.group(2)
    return url


def _lean_citation_label(declaration: str) -> str:
    """The cited declaration as literal code.

    The PDF prints only a "Lean source" link at each citation, so the Markdown
    names the declaration it cites. ``\\verb`` keeps the name exact for copying,
    and ``\\allowbreak`` is a print line-break hint that would split one name
    into several code spans. A name that still carries TeX markup is left to
    Pandoc inside ``\\texttt``.
    """
    name = _ALLOWBREAK_OR_SPACE_RE.sub("", declaration).replace("\\_", "_")
    if not name:
        return "Lean source"
    delimiter = next((mark for mark in "|!+;:@?" if mark not in name), None)
    if delimiter is None or re.search(r"[\\{}$]", name):
        return "\\texttt{" + re.sub(r"\\allowbreak(?![A-Za-z])\s*", "", declaration) + "}"
    return f"\\verb{delimiter}{name}{delimiter}"


def _sole_inline_formula(
    tex: str, start: int, end: int, floor: int
) -> tuple[int, int] | None:
    """The ``$...$`` bounds when the citation at ``start:end`` is its only content.

    One #257 citation is typed as a whole inline formula. The PDF still sets a
    text-mode link there, while Pandoc would keep ``\\leanlink`` as raw TeX
    inside the formula. The opening dollar must be unescaped, single and
    opening, so a citation between two formulas is never merged into them.
    """
    opening = start - 1
    while opening >= floor and tex[opening].isspace():
        opening -= 1
    closing = end
    while closing < len(tex) and tex[closing].isspace():
        closing += 1
    if opening < floor or closing >= len(tex):
        return None
    if tex[opening] != "$" or tex[closing] != "$":
        return None
    if tex[opening - 1 : opening] in ("\\", "$") or tex[closing + 1 : closing + 2] == "$":
        return None
    paragraph = 0
    for blank in _BLANK_LINE_RE.finditer(tex, 0, opening):
        paragraph = blank.end()
    if len(_UNESCAPED_DOLLAR_RE.findall(tex, paragraph, opening)) % 2:
        return None
    return opening, closing + 1


def _preserve_lean_citation_macros(tex: str) -> str:
    """Turn ``\\lean{declaration}{file:line}`` into a link Pandoc renders.

    The link resolves where the PDF's does, at the pins the manuscript itself
    defines, and its text is the declaration name in code, so a sentence that
    read "the gap lemma ()" names the lemma and links its source line. Only a
    manuscript that defines ``\\lean`` as ``\\leanlink{#2}`` is rewritten.
    """
    if not _LEAN_CITATION_DEFINITION_RE.search(_TEX_COMMENT_RE.sub("", tex)):
        return tex
    macros = _leanlink_definitions(tex)
    chunks: list[str] = []
    cursor = 0
    for match in _LEAN_CITATION_RE.finditer(tex):
        if match.start() < cursor:
            continue
        first = _tex_group(tex, match.end())
        if first is None:
            continue
        second = _tex_group(tex, first[1])
        if second is None:
            continue
        (declaration, _), (coordinate, end) = first, second
        if declaration.startswith("#"):
            continue
        start = match.start()
        formula = _sole_inline_formula(tex, start, end, cursor)
        if formula is not None:
            start, end = formula
        chunks.append(tex[cursor:start])
        chunks.append(
            "\\href{"
            + _lean_citation_url(coordinate, macros)
            + "}{"
            + _lean_citation_label(declaration)
            + "}"
        )
        cursor = end
    chunks.append(tex[cursor:])
    return "".join(chunks)


def _remove_immediate_duplicate_gfm_table_headers(markdown: str) -> str:
    """Remove the repeated header row emitted for a LaTeX ``longtable``.

    Pandoc correctly selects the first ``longtable`` header as the GFM table
    header, but it can also emit the identical ``\\endhead`` row as the first
    body row. The only row removed here is an exact duplicate immediately after
    the GFM alignment delimiter, so ordinary repeated data rows are untouched.
    """

    lines = markdown.splitlines(keepends=True)
    out: list[str] = []
    index = 0
    delimiter = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
    while index < len(lines):
        if (
            index + 2 < len(lines)
            and lines[index].lstrip().startswith("|")
            and delimiter.fullmatch(lines[index + 1].rstrip("\r\n"))
            and lines[index].strip() == lines[index + 2].strip()
        ):
            out.extend((lines[index], lines[index + 1]))
            index += 3
            continue
        out.append(lines[index])
        index += 1
    return "".join(out)


_GFM_TABLE_DELIMITER = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
_LONG_GFM_TABLE_SOURCE = re.compile(
    r"\(source:\s*`(?P<code>[^`\r\n]+)`(?P<tail>[^)\r\n]*)\)"
)
_LONG_GFM_CODE_LIMIT = 40
_HTML_ID = re.compile(r'<a\s+id="([^"]+)"')
_GFM_CODE_SPAN = re.compile(r"`([^`]+)`")


def _gfm_row_cells(
    line: str, expected_cell_count: int | None = None
) -> tuple[list[str], str] | None:
    """Split one complete GFM row, retaining any cell continuation bytes."""

    newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    body = line[: -len(newline)] if newline else line
    if not body.lstrip().startswith("|"):
        return None
    trimmed = body.rstrip()
    if not trimmed.endswith("|"):
        return None
    closing_index = len(trimmed) - 1
    preceding_backslashes = 0
    while (
        closing_index - preceding_backslashes - 1 >= 0
        and trimmed[closing_index - preceding_backslashes - 1] == "\\"
    ):
        preceding_backslashes += 1
    if preceding_backslashes % 2:
        return None
    cells: list[str] = []
    buffer: list[str] = []
    in_code = False
    escaped = False
    for char in body:
        if escaped:
            buffer.append(char)
            escaped = False
        elif char == "\\":
            buffer.append(char)
            escaped = True
        elif char == "`":
            buffer.append(char)
            in_code = not in_code
        elif char == "|" and not in_code:
            cells.append("".join(buffer))
            buffer = []
        else:
            buffer.append(char)
    cells.append("".join(buffer))
    if in_code:
        return None
    if cells and not cells[0].strip():
        cells.pop(0)
    if cells and not cells[-1].strip():
        cells.pop()
    if expected_cell_count is not None and len(cells) != expected_cell_count:
        return None
    return cells, newline


def _externalize_long_gfm_table_source_notes(markdown: str) -> str:
    """Move long, exact source coordinates below constrained GFM tables.

    GitHub does not wrap underscored filenames inside inline code. Invisible
    break characters corrupt copied identifiers, while ``<wbr>`` is stripped
    by GitHub. Keep the source coordinate byte-for-byte copyable in nearby
    prose and leave a compact link in the table cell. The position-bound digest
    makes anchors deterministic; the occupied-id check also prevents collisions
    with manuscript-authored anchors.
    """

    lines = markdown.splitlines(keepends=True)
    occupied_ids = set(_HTML_ID.findall(markdown))
    out: list[str] = []
    table_index = 0
    index = 0
    in_fence = False
    fence_char = ""
    fence_length = 0
    while index < len(lines):
        stripped = lines[index].lstrip()
        if in_fence:
            out.append(lines[index])
            if re.fullmatch(
                re.escape(fence_char) + rf"{{{fence_length},}}\s*", stripped
            ):
                in_fence = False
            index += 1
            continue
        opening_fence = re.match(r"(`{3,}|~{3,})", stripped)
        if opening_fence:
            in_fence = True
            fence_char = opening_fence.group(1)[0]
            fence_length = len(opening_fence.group(1))
            out.append(lines[index])
            index += 1
            continue
        if not (
            index + 1 < len(lines)
            and lines[index].lstrip().startswith("|")
            and _GFM_TABLE_DELIMITER.fullmatch(lines[index + 1].rstrip("\r\n"))
        ):
            out.append(lines[index])
            index += 1
            continue

        table_index += 1
        end = index + 2
        # Pandoc may physically wrap one logical row across several lines. A
        # continuation can contain no pipe at all (for example, a long TeX set
        # split after a comma), so only the blank line that Pandoc emits after
        # the table is a safe note-placement boundary. Without this, notes can
        # be inserted into the middle of the following row.
        while end < len(lines) and lines[end].strip():
            end += 1
        table_lines = lines[index:end]
        notes: list[tuple[str, str, str]] = []

        def add_note(kind: str, content: str) -> tuple[int, str]:
            note_number = len(notes) + 1
            identity = f"{table_index}:{note_number}:{kind}:{content}"
            base = "paper-table-note-" + hashlib.sha256(
                identity.encode("utf-8")
            ).hexdigest()[:16]
            anchor = base
            suffix = 2
            while anchor in occupied_ids:
                anchor = f"{base}-{suffix}"
                suffix += 1
            occupied_ids.add(anchor)
            notes.append((kind, anchor, content))
            return note_number, anchor

        def replace_source(match: re.Match[str]) -> str:
            if len(match.group("code")) <= _LONG_GFM_CODE_LIMIT:
                return match.group(0)
            note_number, anchor = add_note("Source", match.group(0))
            return f"[source note {note_number}](#{anchor})"

        parsed_header = _gfm_row_cells(table_lines[0])
        expected_cell_count = len(parsed_header[0]) if parsed_header else None
        # Pandoc preserves newlines inside inline math, but a physical newline
        # splits a GFM table row. Collect only complete logical rows, without
        # absorbing a following row when a malformed one remains incomplete.
        logical_rows = table_lines[:2]
        row_index = 2
        while row_index < len(table_lines):
            row = table_lines[row_index]
            row_index += 1
            if row.lstrip().startswith("|") and _gfm_row_cells(row, expected_cell_count) is None:
                while row_index < len(table_lines) and not table_lines[row_index].lstrip().startswith("|"):
                    row += table_lines[row_index]
                    row_index += 1
                    if _gfm_row_cells(row, expected_cell_count) is not None:
                        break
            logical_rows.append(row)
        projected = [
            _LONG_GFM_TABLE_SOURCE.sub(replace_source, row)
            if row_index >= 2 and _gfm_row_cells(row, expected_cell_count) is not None
            else row
            for row_index, row in enumerate(logical_rows)
        ]

        # Move multiline cells and hard inline-code floors intact into notes.
        # This keeps formulas, source coordinates and their literal newlines
        # rather than rewriting them to fit the table's physical row.
        for row_index in range(2, len(projected)):
            parsed = _gfm_row_cells(projected[row_index], expected_cell_count)
            if parsed is None:
                continue
            cells, newline = parsed
            changed = False
            for cell_index, cell in enumerate(cells):
                if not ("\n" in cell or "\r" in cell or any(
                    len(match.group(1)) > _LONG_GFM_CODE_LIMIT
                    for match in _GFM_CODE_SPAN.finditer(cell)
                )):
                    continue
                content = cell.strip()
                note_number, anchor = add_note("Detail", content)
                leading = cell[: len(cell) - len(cell.lstrip())]
                trailing = cell[len(cell.rstrip()) :]
                cells[cell_index] = (
                    f"{leading}[detail note {note_number}](#{anchor}){trailing}"
                )
                changed = True
            if changed:
                projected[row_index] = "|" + "|".join(cells) + "|" + newline
        out.extend(projected)
        if notes:
            newline = "\r\n" if table_lines[0].endswith("\r\n") else "\n"
            out.append(newline)
            for note_number, (kind, anchor, content) in enumerate(notes, start=1):
                out.append(
                    f'<a id="{anchor}"></a> **{kind} note {note_number}.** '
                    f"{content}{newline}{newline}"
                )
        index = end
    return "".join(out)


_LOCAL_PDF_LINK = re.compile(
    r"(?P<open>\]\()(?P<target>[^)\s]+\.pdf)(?P<fragment>#[^)]*)?(?P<close>\))"
)




def _rewrite_exported_pdf_links(markdown: str, targets: dict[str, str]) -> str:
    """Make local PDF crosslinks resolve from ``docs/papers/full-text``."""

    def replace(match: re.Match[str]) -> str:
        raw_target = match.group("target")
        if "://" in raw_target:
            return match.group(0)
        basename = Path(raw_target).name
        destination = targets.get(basename)
        if destination is None:
            return match.group(0)
        fragment = match.group("fragment") or ""
        # Hyperref's local PDF GoToR target is a bare destination name.
        # In the browser-readable projection that same name needs the PDF
        # viewer's nameddest parameter. Preserve existing viewer parameters.
        if fragment and fragment != "#" and "=" not in fragment:
            fragment = "#nameddest=" + fragment[1:]
        return (
            f"{match.group('open')}{destination}"
            f"{fragment}{match.group('close')}"
        )

    return _LOCAL_PDF_LINK.sub(replace, markdown)


def _inline_long_defs(tex: str) -> tuple[str, list[str]]:
    """Inline ``\\long\\def\\Name{...}`` bodies at the point they are invoked.

    The mathematics paper defines three technical appendices as no-argument TeX
    macros near the material they extend, then places them at the back of the
    document by invoking the macro. TeX expands that; pandoc does not, and it
    does not warn -- it reads the definition, keeps nothing, and silently emits
    a document missing three appendices and roughly a fifth of its text.

    Rewriting the definition to its use site is a faithful transformation for
    argument-free macros: it is what TeX itself does. The count is reported so a
    caller can assert something was expanded rather than assume it.
    """
    expanded: list[str] = []
    while True:
        match = _DEF_RE.search(tex)
        if match is None:
            return tex, expanded
        name = match.group(1)
        open_index = match.end() - 1
        close_index = _matching_brace(tex, open_index)
        body = tex[open_index + 1 : close_index]
        tex = tex[: match.start()] + tex[close_index + 1 :]
        # Replace the single invocation. \Name must not match \NameOther.
        tex, count = re.subn(rf"\\{name}(?![A-Za-z])", lambda _m: body, tex, count=1)
        if count == 0:
            raise RuntimeError(f"\\long\\def\\{name} is defined but never invoked")
        expanded.append(name)


def _sectioning_titles(tex: str) -> int:
    """How many sectioning commands the manuscript will actually typeset."""
    body = tex
    start = body.find("\\iffalse")
    if start != -1:
        end = body.find("\\fi", start)
        body = body[:start] + body[end:] if end != -1 else body[:start]
    return len(re.findall(r"\\(?:sub)*section\*?\{", body))


def _header_block_count(blocks: list[dict[str, Any]]) -> int:
    """Count only injected headings, not title-page prose such as authors."""
    return sum(block.get("t") == "Header" for block in blocks)


def _manuscript_search_root(tex_path: Path) -> Path:
    """Directory pandoc should use to resolve ``\\input`` by relative name.

    Nested storage puts manuscripts under ``paper/<id>/`` while shared
    ``module-aliases.tex`` and ``paper-house-style.sty`` stay in ``paper/``.
    The public Makefile builds from ``paper/`` via VPATH; using the
    manuscript's own subdirectory makes pandoc warn (exit 0) and drop the
    include, which this exporter treats as a failed conversion.
    """
    current = tex_path.parent.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "module-aliases.tex").is_file() or (
            candidate / "paper-house-style.sty"
        ).is_file():
            return candidate
    return tex_path.parent


_DEFINE_VERBATIM_RE = re.compile(
    r"\\DefineVerbatimEnvironment\{(?P<name>[A-Za-z]+)\}\{Verbatim\}\{"
)


def _fold_custom_verbatim_environments(tex: str) -> str:
    """Rewrite fancyvrb environments declared in the manuscript to plain Verbatim.

    ``\\DefineVerbatimEnvironment{routeblock}{Verbatim}{...}`` is TeX-only: pandoc
    does not learn the new name, reads the body as prose, joins its lines and turns
    every ``--`` flag prefix into an en dash. A reader copying a command from the
    rendered page then gets a shell error. Pandoc does know ``Verbatim``, so the
    declared name is folded onto it before conversion; the PDF is unaffected.
    """
    names: set[str] = set()
    while True:
        match = _DEFINE_VERBATIM_RE.search(tex)
        if match is None:
            break
        names.add(match.group('name'))
        # The option block nests braces (\\color{...}); drop it by brace matching.
        close_index = _matching_brace(tex, match.end() - 1)
        tex = tex[: match.start()] + tex[close_index + 1 :]
    for name in names:
        tex = tex.replace(f'\\begin{{{name}}}', '\\begin{Verbatim}')
        tex = tex.replace(f'\\end{{{name}}}', '\\end{Verbatim}')
    return tex


_DESCRIPTION_OPTIONS_RE = re.compile(r'\\begin\{description\}[ \t]*\n?[ \t]*\[')


def _strip_description_list_options(tex: str) -> str:
    """Drop the enumitem option list that follows ``\\begin{description}``.

    Pandoc reads ``\\begin{description}[leftmargin=*,style=nextline]`` as a
    generic div and discards every ``\\item[...]`` label, so the rendered list
    keeps each body and loses the term it describes. The eight labels of the
    closing description list of the #249 reasoning surface went missing this
    way. The options only set PDF layout, so they are removed before
    conversion; the PDF is unaffected.
    """
    parts: list[str] = []
    index = 0
    for match in _DESCRIPTION_OPTIONS_RE.finditer(tex):
        if match.start() < index:
            continue
        depth = 0
        close_index = None
        for position in range(match.end(), len(tex)):
            char = tex[position]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
            elif char == ']' and depth == 0:
                close_index = position
                break
        if close_index is None:
            raise ValueError('unterminated option list after \\begin{description}')
        parts.append(tex[index : match.start()])
        parts.append('\\begin{description}')
        index = close_index + 1
    parts.append(tex[index:])
    return ''.join(parts)


_EVIDENCE_INPUT_RE = re.compile(r"^\\input\{(evidence/[^}]+|paper-evidence)\}[ \t]*%?[^\n]*\n", re.M)
_EVIDENCE_DECLARE_RE = re.compile(
    r"\\DeclareResultEvidence\{([^}]*)\}\{((?:[^{}]|\{[^{}]*\})*)\}\{([^}]*)\}\{([^}]*)\}")
_EVIDENCE_RECORD_RE = re.compile(r"\\newcommand\{\\evidencerecordurl\}\{([^}]*)\}")


def _evidence_marks(tex: str, tex_path: Path) -> tuple[dict[str, tuple[str, str, str]], str | None]:
    """The margin marks one manuscript declares, and its evidence-record URL.

    The marks are generated into ``paper/evidence/<paper>.tex`` (scripts/paper_evidence.py)
    and placed in the PDF's margin by ``paper/paper-evidence.tex``.  Pandoc reads neither,
    so the Markdown edition places them itself, beside each statement.
    """
    root = _manuscript_search_root(tex_path)
    marks: dict[str, tuple[str, str, str]] = {}
    record = None
    for match in re.finditer(r"\\input\{(evidence/[^}]+)\}", tex):
        path = root / f"{match.group(1)}.tex"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        found = _EVIDENCE_RECORD_RE.search(text)
        if found:
            record = found.group(1).replace("\\#", "#")
        for label, mark, lean, comparator in _EVIDENCE_DECLARE_RE.findall(text):
            marks[label] = (
                "Lean\u2020" if "dag" in mark else "Lean",
                lean.replace("\\#", "#").replace("\\%", "%"),
                comparator.replace("\\#", "#").replace("\\%", "%"),
            )
    return marks, record


def _macro_body(name: str, tex_path: Path) -> str | None:
    """The body of a one-argument macro defined in paper/paper-evidence.tex."""
    shared = _manuscript_search_root(tex_path) / "paper-evidence.tex"
    if not shared.is_file():
        return None
    text = shared.read_text(encoding="utf-8")
    match = re.search(r"\\newcommand\{\\" + name + r"\}\[1\]\{", text)
    if match is None:
        return None
    close = _matching_brace(text, match.end() - 1)
    return text[match.end():close]


def _preserve_evidence_macros(tex: str, tex_path: Path) -> str:
    """Render the once-per-paper evidence paragraph and the evidence remarks as prose."""
    _marks, record = _evidence_marks(tex, tex_path)
    tex = _EVIDENCE_INPUT_RE.sub("", tex)
    paragraph = _macro_body("evidenceparagraph", tex_path)
    if paragraph is not None:
        paragraph = paragraph.replace("\\par\\smallskip\\noindent", "").strip()
        body = paragraph.replace("#1", (record or "").replace("#", "\\#"))
        tex = re.sub(r"\\evidenceparagraph\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}",
                     lambda _m: "\n\n" + body + "\n\n", tex)
    if record is not None:
        # A paper may also link its record directly, as \href{\evidencerecordurl}{...}.
        tex = re.sub(r"\\evidencerecordurl(?![A-Za-z])",
                     lambda _m: record.replace("#", "\\#"), tex)
    chunks: list[str] = []
    cursor = 0
    while True:
        match = re.compile(r"\\evidenceremark\{").search(tex, cursor)
        if match is None:
            chunks.append(tex[cursor:])
            break
        close = _matching_brace(tex, match.end() - 1)
        chunks.extend((tex[cursor:match.start()], "\n\n", tex[match.end():close], "\n\n"))
        cursor = close + 1
    return "".join(chunks)


def _place_evidence_marks(markdown: str, marks: dict[str, tuple[str, str, str]]) -> str:
    """Put each result's Lean and Comparator links first inside its statement block."""
    for label, (text, lean, comparator) in marks.items():
        links = f'<a href="{lean}">{text}</a>'
        if comparator:
            links += f' · <a href="{comparator}">Comparator</a>'
        line = f'<p class="evidence-marks">{links}</p>\n'
        opener = re.compile(r'^<div id="' + re.escape(label) + r'" class="[a-z]+">\n', re.M)
        found = opener.search(markdown)
        if found is not None:
            markdown = markdown[:found.end()] + line + markdown[found.end():]
            continue
        # A labelled claim span has no block of its own: the links follow its paragraph.
        at = markdown.find(f'id="{label}"')
        if at >= 0:
            end = markdown.find("\n\n", at)
            end = len(markdown) if end < 0 else end
            markdown = markdown[:end] + "\n\n" + line.rstrip("\n") + markdown[end:]
    return markdown


def _convert(tex_path: Path, stem: str) -> dict[str, Any]:
    """LaTeX -> markdown, section index with line numbers, and front matter."""
    source = _preserve_path_macros(tex_path.read_text())
    source = _fold_custom_verbatim_environments(source)
    source = _preserve_layout_adjustbox(source)
    source = _strip_description_list_options(source)
    source = _preserve_declaration_macros(source)
    source = _preserve_lean_citation_macros(source)
    source = _preserve_generated_note_macros(source, tex_path)
    marks, _record = _evidence_marks(source, tex_path)
    source = _preserve_evidence_macros(source, tex_path)
    source, inlined = _inline_long_defs(source)
    ast = json.loads(
        _pandoc(
            ["-f", "latex", "-t", "json"],
            stdin=source,
            cwd=_manuscript_search_root(tex_path),
        )
    )
    front, title, subtitle = _meta_blocks(ast.get("meta") or {}, stem)
    # This manuscript's section counter and tagged equations have been checked
    # against its PDF. Other paper families define counters differently and
    # need their own source-to-renderer review before changing their text.
    preserve_pdf_numbers = stem == "optimal-sparse-perturbations"
    tagged_equations = ({
        **_tagged_equation_numbers(ast["blocks"]),
        **_declared_equation_numbers(source),
    } if preserve_pdf_numbers else {})
    walk = _AstWalk(
        section_numbered_statements=preserve_pdf_numbers,
        front_title_id=stem,
    )
    ast["blocks"] = walk.blocks(front + ast["blocks"])
    _render_numbered_references(ast["blocks"],
                                {**walk.statement_numbers, **tagged_equations},
                                walk.equation_labels | walk.reference_labels)
    anchor_ids = _case_safe_anchor_ids(_rendered_anchor_labels(ast["blocks"]))
    _remap_delivery_anchors(ast["blocks"], anchor_ids)
    for section in walk.sections:
        section["id"] = anchor_ids.get(section["id"], section["id"])
    markdown = _pandoc(["-f", "json", "-t", "gfm", "--wrap=none"], stdin=json.dumps(ast))
    markdown = _remove_immediate_duplicate_gfm_table_headers(markdown)
    markdown = _externalize_long_gfm_table_source_notes(markdown)
    markdown = _place_evidence_marks(
        markdown, {anchor_ids.get(label, label): mark for label, mark in marks.items()}
    )

    # Bind each section to a line in the file it actually landed in. An index
    # that only names sections makes an agent scan; one that names lines lets it
    # seek.
    line_of: dict[str, int] = {}
    for number, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith('<a id="') and stripped.endswith('"></a>'):
            line_of.setdefault(stripped[7:-6], number)
    for section in walk.sections:
        section["line"] = line_of.get(section["id"])
    # Every sectioning command the manuscript typesets must survive into the
    # output. This is the check that was missing when three \long\def appendices
    # silently vanished: pandoc exited 0, the file looked plausible, and a fifth
    # of the paper was gone. Counting is enough to catch a whole block dropping,
    # and is far cheaper than comparing rendered text.
    expected = _sectioning_titles(source)
    # Remove only emitted headers added by _meta_blocks.  Some manuscripts also
    # receive an author Para in ``front``; subtracting every injected block made
    # a complete 131-section conversion look one section short.
    produced = len(walk.sections) - _header_block_count(front)
    if produced < expected:
        raise RuntimeError(
            f"{tex_path.name}: conversion lost content -- the manuscript typesets "
            f"{expected} sections but the output has {produced}. "
            "Check for macro-wrapped or conditionally-included blocks that pandoc "
            "does not expand."
        )
    return {
        "markdown": markdown,
        "sections": walk.sections,
        "citations_rendered": walk.citations_rendered,
        "title": title,
        "subtitle": subtitle,
        "macros_inlined": inlined,
        "sections_expected": expected,
    }


def _relative_to_corpus(repo_rel: str) -> str:
    """Repository-relative path -> link that works from inside the corpus dir.

    The corpus README lives at ``docs/papers/``; a native PDF lives at the
    repository root. Both appear in the same list, so the depth is resolved here
    once rather than guessed per link.
    """
    if repo_rel.startswith(f"{CORPUS_DIR_REL}/"):
        return repo_rel.removeprefix(f"{CORPUS_DIR_REL}/")
    return "../../" + repo_rel


def _section_link(record: dict[str, Any], entry: dict[str, Any]) -> str:
    return f"{_relative_to_corpus(record['local_full_text'])}#{entry['id']}"


def _signal_text(value: Any, *, field: str) -> str:
    """Relocate source-owned signal prose from ``docs/`` to the catalogue."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Palomar signal field {field} must be non-empty text")

    def relocate(match: re.Match[str]) -> str:
        target = match.group("target")
        if target is None:
            return match.group(0)
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path or parts.path.startswith("/"):
            return match.group(0)
        # Both authored inventories live in docs/. Their prose links share
        # that base with docs/RESULTS.md and docs/EXTERNAL_VERIFICATION.md.
        repository_path = posixpath.normpath(posixpath.join("docs", parts.path))
        relocated = posixpath.relpath(repository_path, CORPUS_DIR_REL)
        return f"]({relocated}{target[len(parts.path):]})"

    # Use the reading-edition owner's literal guards: mathematical coefficient
    # notation and code examples can resemble Markdown links without being one.
    return re.sub(
        r"(?P<ticks>`+).*?(?P=ticks)|(?P<tildes>~{3,}).*?(?P=tildes)"
        r"|(?P<dollars>\${1,2}).*?(?P=dollars)|\]\((?P<target>[^)\s]+)\)",
        relocate, " ".join(value.split()), flags=re.DOTALL,
    )


def _signal_paper_record(
    records: list[dict[str, Any]], problem: int
) -> dict[str, Any]:
    """Choose the dedicated problem note for a ranked mathematical family."""
    subject_token = f"#{problem}"
    matches = [
        record
        for record in records
        if subject_token in str(record.get("subject") or "")
        and record.get("publication_state") == "active"
        and record.get("local_full_text")
    ]
    if not matches:
        raise ValueError(
            f"Palomar signal family for Erdős #{problem} lacks an active paper route"
        )
    # Prefer the dedicated note to a longer reasoning surface. The registry
    # remains the authority for the full inventory; this only chooses the first
    # useful route for a signal item.
    matches.sort(
        key=lambda record: (
            0 if str(record.get("paper_id", "")).startswith(f"erdos-{problem}-") else 1,
            str(record.get("paper_id", "")),
        )
    )
    return matches[0]


def _signal_source_link(source: str) -> str:
    """Make a repository-root source path reachable from ``docs/papers``."""
    # Claim records retain logical module coordinates; the public checkout
    # stores both supported libraries under lean/. Already physical paths
    # (including research and verification consumers) must stay unchanged.
    if source.startswith(("Erdos249257/", "ErdosProblems/")):
        source = f"lean/{source}"
    return f"[Lean source](../../{source})"


def _signal_hierarchy_lines(
    records: list[dict[str, Any]], target_repo: str, repo_root: Path
) -> list[str]:
    """Project Palomar's mathematical judgement before the paper inventory.

    ``docs/PALOMAR_RESULT_SHOWCASE.json`` is the source of the rank and
    disposition judgement. ``docs/claims.json`` supplies the exact checked
    interface, source declaration, problem, and boundary. Paper records only
    supply navigational links. Keeping these joins here makes the generated
    README useful without creating a second mathematical ranking authority.
    """
    showcase_path = repo_root / "docs" / "PALOMAR_RESULT_SHOWCASE.json"
    if not showcase_path.is_file():
        return []
    claims_path = repo_root / "docs" / "claims.json"
    if not claims_path.is_file():
        raise FileNotFoundError(
            f"Palomar signal projection requires {claims_path.relative_to(repo_root)}"
        )
    showcase = json.loads(showcase_path.read_text(encoding="utf-8"))
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    ranking = showcase.get("candidate_ranking")
    screening = showcase.get("candidate_screening")
    contract = showcase.get("selection_contract")
    disposition_source = showcase.get("candidate_value_dispositions")
    universe = showcase.get("candidate_universe")
    packet = claims.get("external_verification_packet")
    main_results = packet.get("main_results") if isinstance(packet, dict) else None
    if not isinstance(ranking, list) or not ranking:
        raise ValueError("Palomar showcase lacks candidate_ranking")
    ranks = [row.get("rank") for row in ranking]
    if sorted(ranks) != list(range(1, len(ranking) + 1)):
        raise ValueError("Palomar candidate_ranking must use contiguous ranks")
    if len({row.get("family_id") for row in ranking}) != len(ranking):
        raise ValueError("Palomar candidate_ranking must use unique family ids")
    if not isinstance(screening, list):
        raise ValueError("Palomar showcase lacks candidate_screening")
    if not isinstance(contract, dict) or not contract.get("ranking_axes"):
        raise ValueError("Palomar showcase lacks selection_contract.ranking_axes")
    if not isinstance(disposition_source, dict) or not isinstance(universe, dict):
        raise ValueError("Palomar showcase lacks candidate-value disposition authority")
    if not isinstance(main_results, list) or not main_results:
        raise ValueError("claims external_verification_packet lacks main_results")

    by_wrapper: dict[str, dict[str, Any]] = {}
    for result in main_results:
        wrapper = result.get("wrapper_declaration")
        if not isinstance(wrapper, str) or wrapper in by_wrapper:
            raise ValueError("main_results wrapper declarations must be unique")
        by_wrapper[wrapper] = result

    review_by_family: dict[str, dict[str, Any]] = {}
    for problem_row in packet.get("review_matrix", []) if isinstance(packet, dict) else []:
        if not isinstance(problem_row, dict):
            continue
        problem = problem_row.get("problem")
        for family in problem_row.get("families", []):
            if isinstance(family, dict) and isinstance(family.get("id"), str):
                review_by_family[family["id"]] = {
                    "problem": problem,
                    **family,
                }

    dispositions = universe.get("source_family_dispositions")
    if not isinstance(dispositions, dict):
        dispositions = disposition_source.get("source_family_dispositions")
    if not isinstance(dispositions, dict):
        raise ValueError("Palomar showcase lacks source_family_dispositions")

    def checked_result(wrapper: str) -> dict[str, Any]:
        result = by_wrapper.get(wrapper)
        if result is None:
            raise ValueError(
                "Palomar signal declaration lacks a claims main_results row: "
                f"{wrapper}"
            )
        if not isinstance(result.get("problem"), int):
            raise ValueError(f"claims result lacks integer problem for {wrapper}")
        if result.get("review_family") is None:
            raise ValueError(f"claims result lacks review_family for {wrapper}")
        return result

    def screening_identity(
        declaration: str, family_id: str
    ) -> tuple[int, dict[str, Any] | None]:
        result = by_wrapper.get(declaration)
        if result is not None:
            if not isinstance(result.get("problem"), int):
                raise ValueError(f"claims result lacks integer problem for {declaration}")
            return int(result["problem"]), result
        review = review_by_family.get(family_id)
        if review is None or not isinstance(review.get("problem"), int):
            raise ValueError(
                "Palomar screening declaration lacks claims/review-family identity: "
                f"{declaration}"
            )
        # A source-current review family can predate its ExternalVerification
        # wrapper by one projection turn. It is still safe to display as
        # represented natural friction, but not to invent a checked wrapper row.
        return int(review["problem"]), None

    def disposition_family(declaration: str) -> str:
        """Resolve a disposition row without requiring claims to lead Palomar.

        Ranked checked interfaces still require ``main_results``.  The lower
        disposition roster makes no source, statement, or boundary claim, so a
        source-current Palomar screening row is sufficient identity while the
        slower claims projection catches up.
        """
        result = by_wrapper.get(declaration)
        if result is not None:
            family_id = result.get("review_family")
            if not isinstance(family_id, str) or not family_id:
                raise ValueError(
                    f"claims result lacks review_family for {declaration}"
                )
            return family_id
        families = {
            row.get("family_id")
            for row in screening
            if isinstance(row, dict) and row.get("declaration") == declaration
        }
        if len(families) != 1 or not all(
            isinstance(family_id, str) and family_id for family_id in families
        ):
            raise ValueError(
                "Palomar disposition declaration lacks unique screening-family "
                f"identity: {declaration}"
            )
        return next(iter(families))

    lines = [
        "## Mathematical signal first",
        "",
        "This reader order is the existing Palomar `candidate_ranking`, joined",
        "to exact source/current claims and their paper routes. It is a value",
        "judgement about consequence, endpoint proximity, mechanism depth,",
        "distinctness, usefulness, digestion value, evidence certainty, natural",
        "friction, and overclaim risk—not a proof, novelty, or closure claim.",
        "The complete paper inventory follows only after this ranked and",
        "disposition-aware spine.",
        "",
        "### Ranked frontier",
        "",
    ]
    ranked_families: set[str] = set()
    for candidate in sorted(ranking, key=lambda row: row["rank"]):
        wrapper = candidate.get("declaration")
        result = checked_result(wrapper)
        family_id = candidate.get("family_id")
        if result.get("review_family") != family_id:
            raise ValueError(
                "Palomar candidate family does not match claims review_family: "
                f"{family_id}"
            )
        ranked_families.add(family_id)
        paper = _signal_paper_record(records, int(result["problem"]))
        source = result.get("original_source")
        source_declaration = result.get("original_declaration")
        if not isinstance(source, str) or not isinstance(source_declaration, str):
            raise ValueError(f"claims result lacks source identity for {wrapper}")
        route = _relative_to_corpus(str(paper["local_full_text"]))
        lines.extend(
            [
                f"#### {candidate['rank']}. Erdős #{result['problem']} — `{family_id}`",
                "",
                f"**Paper route:** [{paper['paper_id']}]({route})",
                f"  **Checked interface:** `{wrapper}`",
                f"  **Source declaration:** `{source_declaration}` via {_signal_source_link(source)}",
                f"  **Result:** {_signal_text(candidate.get('consequence_and_endpoint_proximity'), field='consequence_and_endpoint_proximity')}",
                f"  **Hard mechanism:** {_signal_text(candidate.get('mechanism_depth_and_natural_friction'), field='mechanism_depth_and_natural_friction')}",
                f"  **Evidence:** {_signal_text(candidate.get('evidence_certainty'), field='evidence_certainty')}",
                f"  **Boundary:** {_signal_text(result.get('boundary'), field='boundary')}",
                "",
            ]
        )

    lines.extend(
        [
            "### Represented natural friction",
            "",
            "These source-current families are represented because they expose",
            "the obstruction, missing producer, or reusable mechanism that a",
            "reader needs to understand the frontier. They are not silently",
            "promoted to endpoint results.",
            "",
        ]
    )
    represented: dict[str, dict[str, Any]] = {}
    for row in screening:
        family_id = row.get("family_id")
        if dispositions.get(family_id) != "represented" or family_id in ranked_families:
            continue
        declaration = row.get("declaration")
        if not isinstance(family_id, str) or not isinstance(declaration, str):
            raise ValueError("Palomar candidate_screening row lacks family/declaration")
        problem, result = screening_identity(declaration, family_id)
        slot = represented.setdefault(
            family_id,
            {
                "declarations": [],
                "reasons": [],
                "problem": problem,
                "paper": _signal_paper_record(records, problem),
            },
        )
        if declaration not in slot["declarations"]:
            slot["declarations"].append(declaration)
        reason = row.get("reason")
        if isinstance(reason, str) and reason not in slot["reasons"]:
            slot["reasons"].append(reason)
    for family_id, row in represented.items():
        declarations = ", ".join(f"`{value}`" for value in row["declarations"])
        reasons = " ".join(_signal_text(value, field="screening.reason") for value in row["reasons"])
        route = _relative_to_corpus(str(row["paper"]["local_full_text"]))
        lines.append(
            f"- `{family_id}` (Erdős #{row['problem']}; [{row['paper']['paper_id']}]({route})): "
            f"{declarations}. {reasons}"
        )
    lines.append("")

    lines.extend(
        [
            "### Explicitly subordinate, rejected, and long tail",
            "",
            "The remaining families stay discoverable in the exhaustive roster",
            "with their disposition visible. Subordinate and rejected entries",
            "are useful boundaries or reductions; long-tail entries are exact",
            "support, identities, finite instances, or auxiliary routes that do",
            "not currently earn scarce first-contact attention.",
            "",
        ]
    )
    eligible_groups = disposition_source.get("eligible_groups")
    if not isinstance(eligible_groups, list):
        raise ValueError("Palomar candidate_value_dispositions lacks eligible_groups")
    for group in eligible_groups:
        disposition = group.get("disposition")
        if disposition not in {"subordinate", "rejected", "long_tail"}:
            continue
        declarations = group.get("declarations")
        if not isinstance(declarations, list):
            raise ValueError(f"Palomar disposition group lacks declarations: {disposition}")
        lines.append(f"#### {disposition.replace('_', ' ').title()}")
        lines.append("")
        reason = _signal_text(group.get("reason"), field=f"{disposition}.reason")
        by_family: dict[str, list[str]] = {}
        for declaration in declarations:
            if not isinstance(declaration, str) or not declaration:
                raise ValueError(
                    f"Palomar {disposition} group contains an invalid declaration"
                )
            family_id = disposition_family(declaration)
            by_family.setdefault(family_id, []).append(declaration)
        for family_id, family_declarations in by_family.items():
            joined = ", ".join(f"`{value}`" for value in family_declarations)
            lines.append(f"- `{family_id}`: {joined}. {reason}")
        lines.append("")
    return lines


def _readme(
    records: list[dict[str, Any]], target_repo: str, repo_root: Path
) -> str:
    """The orientation band as prose. Deliberately short.

    A cold reader should finish this file knowing which paper answers their
    question and where it is. Everything else is a link.
    """
    active_count = sum(
        record.get("publication_state") == "active" for record in records
    )
    retired_count = sum(
        record.get("publication_state") == "retired" for record in records
    )
    retained_pending_count = sum(record.get("publication_state") == "pending_source_publication" for record in records)
    active_problem_subjects: list[str] = []
    for record in records:
        subject = str(record.get("subject") or "").strip()
        if (
            record.get("publication_state") == "active"
            and record.get("subject_kind") == "problem"
            and subject
            and subject not in active_problem_subjects
        ):
            active_problem_subjects.append(subject)

    active_records = [
        record for record in records if record.get("publication_state") == "active"
    ]
    non_active_records = [
        record for record in records if record.get("publication_state") != "active"
    ]
    ordered_records = active_records + non_active_records
    lines: list[str] = [
        "# The papers",
        "",
        "<!-- Generated by the shared paper-corpus renderer.",
        "     Edit the manuscripts, then run the native refresh command below. -->",
        "",
        "This directory contains the papers as searchable text, with links to",
        "PDFs and LaTeX source. Both public repositories include the active papers.",
        "Older, retired papers are kept only in the repository that published them.",
        "Some papers may be available in the repository before they appear on the website.",
        "The website is agent-readable through its [navigation guide](https://wcook04.github.io/plectis/llms.txt)",
        "and [maths map manifest](https://wcook04.github.io/plectis/lean/experience/manifest.json).",
        "",
        (
            f"This checkout contains {active_count} active "
            f"{'paper' if active_count == 1 else 'papers'}"
            + (
                f" and {retired_count} retired "
                f"{'paper' if retired_count == 1 else 'papers'}"
                if retired_count
                else ""
            )
            + (f" and {retained_pending_count} " + ("paper" if retained_pending_count == 1 else "papers") + " awaiting website publication" if retained_pending_count else "")
            + "."
        ),
        "",
    ]
    system_papers = sorted(
        (record for record in active_records
         if record.get("subject_kind") == "system"
         and record.get("relation_to_this_repository") == "native"),
        key=lambda record: record["paper_id"],
    )
    if system_papers:
        lines += [
            "## System and exposition papers",
            "",
        ]
        lines += [
            f"- [{record['title']}]({_relative_to_corpus(record['local_full_text'])})"
            + (f" — {record['form']}" if record.get("form") else "")
            for record in system_papers
        ]
        lines.append("")
        if active_problem_subjects:
            lines += [
                "The mathematical papers are listed below, "
                "[by Erdős problem number](#problem-portfolio).",
                "",
            ]
        lines += [
            "The links above open the full papers as text. The catalogue below",
            "also links to PDFs, LaTeX sources and individual sections.",
            "",
        ]
    companion_systems = sorted(
        (record for record in active_records
         if record.get("subject_kind") == "system"
         and record.get("relation_to_this_repository") == "mirror"),
        key=lambda record: record["paper_id"],
    )
    if companion_systems:
        lines += ["## Companion system papers", "",
                  "These are companion copies; the named home repository owns each manuscript.", ""]
        lines += [
            f"- [{record['title']}]({_relative_to_corpus(record['local_full_text'])})"
            + f" — companion copy from `{record.get('home_repository', 'the source repository')}`"
            for record in companion_systems
        ]
        lines.append("")
    earlier_systems = [record for record in non_active_records
                       if record.get("subject_kind") == "system"
                       and record.get("publication_state") == "retired"
                       and record.get("relation_to_this_repository") == "native"]
    if earlier_systems:
        lines += [
            "Earlier systems papers are retained below as historical background.",
            "Their dates, superseding paper and source records distinguish them",
            "from the current account and instructions.",
            "",
        ]
    if target_repo == "plectis-erdos":
        lines += [
            "## Choose a reading route", "",
            "Start with the [human paper catalogue](../../paper/README.md) or",
            "[results and limits](../RESULTS.md) for the current mathematical conclusions.",
            "This index owns searchable paper text and section links; it does not",
            "confer claim status.", "",
        ]
    lines.extend(_signal_hierarchy_lines(records, target_repo, repo_root))
    if active_problem_subjects:
        lines += [
            '<a id="problem-portfolio"></a>',
            "",
            f"## All papers ({len(records)})",
            "",
            f"The mathematical papers cover {', '.join(active_problem_subjects)}. "
            "They state the results obtained and what remains unproved. "
            "Retired papers are marked below.",
            "",
        ]
        if target_repo == "plectis-erdos":
            portfolio_path = repo_root / "docs" / "RESULTS.md"
            if not portfolio_path.is_file():
                raise FileNotFoundError(
                    "Lean paper portfolio route requires "
                    f"{portfolio_path.relative_to(repo_root)}"
                )
            lines += [
                "[Results and limits](../RESULTS.md) gives the current mathematical account. "
                "`docs/problems.json` contains programme identifiers for coding agents.",
                "",
            ]
    for record in ordered_records:
        lines.append(f"### {record['question_this_paper_answers']}")
        lines.append("")
        subtitle = f" — *{record['subtitle']}*" if record.get("subtitle") else ""
        state = record.get("publication_state", "active")
        state_label = (
            " · **retired manuscript**" if state == "retired" else
            " · **included here; not yet published on the website**" if state == "pending_source_publication" else ""
        )
        lines.append(f"**{record['title']}**{subtitle}{state_label}")
        lines.append("")
        links = [f"[full text]({_relative_to_corpus(record['local_full_text'])})"]
        if record.get("local_pdf"):
            links.append(f"[PDF]({_relative_to_corpus(record['local_pdf'])})")
        links.append(f"[LaTeX source]({_relative_to_corpus(record['local_source'])})")
        lines.append(
            f"{' · '.join(links)} · {record['section_count']} sections · "
            f"`{record['paper_id']}` · {record['relation_to_this_repository']} to this repository"
        )
        lines.append("")
        superseding = next((row for row in records
                            if row["paper_id"] == record.get("superseded_by")), None)
        if superseding:
            lines += [
                f"Superseded by [{superseding['title']}]"
                f"({_relative_to_corpus(superseding['local_full_text'])}). "
                "Retained for historical context; use the current paper and "
                "repository guides for present practice.",
                "",
            ]
        for archived in record.get("archived_versions", []):
            label = f"{archived['identifier']}v{archived['version']}"
            source_url = (f"{archived['source_repository']}/blob/"
                          f"{archived['source_commit']}/{archived['source_path']}")
            lines += [
                f"Archived edition: [{label}]({archived['url']}) "
                f"([PDF]({archived['pdf_url']}), [source archive]({archived['source_url']})); "
                f"published {archived['published']} from "
                f"[source `{archived['source_commit'][:12]}`]({source_url}).",
                "",
                ("The current source and PDF match this archived edition."
                 if archived["relation_to_current_manuscript"] == "same_source_and_pdf"
                 else "The current source or PDF differs from this frozen edition; the archive record does not cover later changes."),
                "Archive publication does not establish independent mathematical review.",
                "",
            ]
        route = record.get("first_pass")
        if route:
            entries = route["sections"]
            named = ", ".join(f"[{e['title']}]({_section_link(record, e)})" for e in entries)
            lead = (
                "Selected sections of this historical account:"
                if state == "retired"
                else
                "The author recommends starting with"
                if route["stated_by_the_paper"]
                else "Start here (selected for this guide):"
            )
            lines.append(f"{lead} {named}.")
            lines.append("")

    lines += [
        "## Evidence and limitations",
        "",
        "The papers explain the results. To verify a formal proof, use the linked",
        "Lean source and verification instructions. The repositories assign",
        "responsibility for proof verification, status and explanation as follows:",
        "",
        f"> {AUTHORITY_ORDER}.",
        "",
    ]
    lines += [
        "Each paper's evidence ceiling and publication state remain in",
        "[the corpus record](corpus.json), including `not_authority_for` and",
        "the source identity of every imported or archived edition.",
    ]
    for record in records:
        lines.append(
            f"- `{record['paper_id']}` is not authority for {record['not_authority_for']}."
        )
    lines += [
        "",
        "## For agents",
        "",
        "`corpus.json` lists every paper, every section with its",
        "`\\label` id and its line number in the generated Markdown, every source",
        "hash, and the limitations above. Use it to find the required file or section.",
        "",
        "Each generated Markdown file keeps the manuscript's own section labels as",
        "HTML anchors, so a section can be reached by name rather than by scanning:",
        "",
        "```",
        f'grep -n \'<a id="sec:intro">\' {FULL_TEXT_DIR}/*.md',
        "```",
        "",
        "The Markdown is generated from LaTeX. It expands theorem numbers and",
        "cross-references and adds Lean source URLs for the recorded commit.",
        "The `.tex` file is the original manuscript. If the generated text differs,",
        "consult that source and report the conversion error.",
        "",
        "After editing a native manuscript, install Pandoc and run",
        f"`{NATIVE_REFRESH_COMMAND}` from the repository root.",
        "This refreshes the text, section maps and this index. Rebuild changed PDFs",
        "and run the repository release checks separately. Companion copies retain",
        "their imported source identities; local edits do not publish a new revision.",
        "",
    ]
    return "\n".join(lines)



def render_record_navigation(pair: dict[str, Any], boundary: str) -> str:
    """A source-bound short/long guide. No summarization or status inference."""
    from urllib.parse import quote

    def file_link(loc: dict[str, Any]) -> str:
        path = loc['path']
        target = f"../../../{quote(path, safe='/')}#L{loc['line']}-L{loc['end_line']}"
        return f"[{path}]({target}) lines {loc['line']}-{loc['end_line']}"

    def paper_link(paper: dict[str, Any], anchor: str = '') -> str:
        target = '../../../' + quote(paper['local_full_text'], safe='/')
        if anchor:
            target += '#' + quote(anchor, safe=':.-_')
        return target

    short, long = pair['short_paper'], pair['long_paper']
    s = pair['summary']
    lines = [f"# Erdős #{pair['problem']}: from the short paper to its record", '',
             '<!-- Generated by scripts/build_reading_edition.py --records. -->', '',
             f"Start with [{short['title']}]({paper_link(short)}). "
             f"The longer account is [{long['title']}]({paper_link(long)}).", '',
             f"Registered assertions: {s['short_claims']} short, {s['long_claims']} long. "
             f"Located long-record links: {s['linked_short_claims']}. "
             f"Proofs retained in the short paper: {s.get('explained_in_short', 0)}. "
             f"Long correspondences still open: {s.get('long_correspondence_open', s['unresolved_short_claims'])}.", '',
             boundary, '', '## Reading routes', '',
             'These are the existing paper-corpus editorial routes. Their headings retain the authors’ scope; '
             'a section about a failed route is not an impossibility result for the parent problem.', '']
    for section in long.get('first_pass', {}).get('sections', []):
        lines += [f"- [{section['title']}]({paper_link(long, section['id'])}) ({section['id']})."]
    lines += ['', '## Claim to support', '',
              'A complete registered-evidence match locates the same full declaration set in the long record. '
              'It does not independently prove that two differently worded statements are equivalent. '
              'An authored proof link checks the pinned passage exists unchanged, without reviewing the proof. '
              'An explained-in-short disposition locates its accepted short-paper argument and keeps the long correspondence open.', '']
    for claim in pair['claims']:
        lines += [f"### {claim['label']}", '', f"State: **{claim['state']}**.", '']
        if claim['short_location']:
            lines += ['Short statement: ' + file_link(claim['short_location']) + '.', '']
        lines += [f"Ledger evidence: Lean `{claim['ledger_lean_status']}`; Comparator `{claim['ledger_comparator_status']}`. "
                  'These statuses are copied from the evidence ledger; this build reruns neither checker.', '']
        if claim['long_locations']:
            lines += ['Long-record location: ' + '; '.join(file_link(x) for x in claim['long_locations']) + '.', '']
        for match in claim['matches']:
            support = match['support']
            if support['kind'] == 'ordinary_proof_text':
                lines += [match['rationale'], '', 'Review status: ' + support['review_status'] + '.', '']
            else:
                for loc in support['locators']:
                    lines += [f"- `{loc['declaration']}`: {file_link(loc)}."]
                lines += ['']
        if claim.get('short_proof'):
            support = claim['short_proof']
            lines += ['Retained short-paper argument: ' + file_link(support['locator']) + '.', '',
                      support['rationale'], '', 'Review status: ' + support['review_status'] + '.', '',
                      'This hash-bound passage records proof availability; its mathematical correctness is not checked by this audit. '
                      'No accepted long-record correspondence is established by this disposition.', '']
        if claim['state'] in ('unresolved', 'short_proof_explained_long_link_open'):
            lines += ['No accepted correspondence is recorded. Check the candidates below; '
                      'none is silently treated as a proof of this short statement.', '']
            for candidate in claim['candidates']:
                lines += [f"- `{candidate['basis']}`: {file_link(candidate['location'])}."]
            if not claim['candidates']:
                lines += ['No candidate was found by the bounded label/declaration rules. Read the long record before declaring the result absent.']
            lines += ['']
    lines += ['## Long-record material retained outside these links', '',
              'These registered long assertions are not used by an accepted short-paper link. '
              'They may be supporting lemmas, broader results, route-local obstructions, or unresolved matches. '
              'They are retained and are not deletion candidates.', '']
    for row in pair['long_only_or_unmatched']:
        lines += [f"- `{row['long_claim'].split('#',1)[-1]}`: {file_link(row['location'])}."]
    reviews = [f for f in pair['findings'] if f['severity'] == 'review']
    lines += ['', '## Passage-review queue', '',
              f"{len(reviews)} lexical review findings. No automated deletion or mathematical contradiction judgment.", '']
    for finding in reviews:
        lines += [f"- `{finding['code']}`: {finding['detail']}"]
    return '\n'.join(lines).rstrip() + '\n'
