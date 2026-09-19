"""Shared public paper conversion and reader-index renderer.

This portable owner is copied byte for byte into each public paper corpus.
The publication exporter and native-clone refresher use the same functions.
"""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
import subprocess
from pathlib import Path
from typing import Any

CORPUS_DIR_REL = "docs/papers"
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

    def __init__(self) -> None:
        self.sections: list[dict[str, Any]] = []
        self.citations_rendered = 0

    def blocks(self, blocks: list[Any]) -> list[Any]:
        out: list[Any] = []
        for block in blocks:
            if isinstance(block, dict) and block.get("t") == "Header":
                level, attr, inlines = block["c"]
                anchor = attr[0]
                title = _stringify(inlines).strip()
                if anchor:
                    # A raw HTML anchor survives into GFM, where pandoc's header
                    # attributes do not. Without it the paper's own \label ids --
                    # the stable names everything else refers to -- would not
                    # exist in the generated file at all.
                    out.append({"t": "RawBlock", "c": ["html", f'<a id="{anchor}"></a>']})
                self.sections.append({"level": level, "id": anchor, "title": title})
            out.append(self.node(block))
        return out

    def node(self, node: Any) -> Any:
        if isinstance(node, list):
            return [self.node(x) for x in node]
        if not isinstance(node, dict):
            return node
        if node.get("t") == "Cite":
            self.citations_rendered += 1
            return _render_citation(node)
        return {k: (self.node(v) if k == "c" else v) for k, v in node.items()}


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
    """Split one complete physical GFM row, failing closed on continuations."""

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

        projected = [
            _LONG_GFM_TABLE_SOURCE.sub(replace_source, line)
            if row_index >= 2
            else line
            for row_index, line in enumerate(table_lines)
        ]

        # If another cell still has a hard inline-code floor, externalize the
        # complete cell rather than rewriting mathematics or inserting hidden
        # break characters. Source-note markers produced above remain as useful
        # short context in otherwise readable cells.
        parsed_header = _gfm_row_cells(projected[0])
        expected_cell_count = len(parsed_header[0]) if parsed_header else None
        for row_index in range(2, len(projected)):
            parsed = _gfm_row_cells(projected[row_index], expected_cell_count)
            if parsed is None:
                continue
            cells, newline = parsed
            changed = False
            for cell_index, cell in enumerate(cells):
                if not any(
                    len(match.group(1)) > _LONG_GFM_CODE_LIMIT
                    for match in _GFM_CODE_SPAN.finditer(cell)
                ):
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


def _convert(tex_path: Path, stem: str) -> dict[str, Any]:
    """LaTeX -> markdown, section index with line numbers, and front matter."""
    source = _preserve_path_macros(tex_path.read_text())
    source = _fold_custom_verbatim_environments(source)
    source = _preserve_declaration_macros(source)
    source, inlined = _inline_long_defs(source)
    ast = json.loads(
        _pandoc(
            ["-f", "latex", "-t", "json"],
            stdin=source,
            cwd=_manuscript_search_root(tex_path),
        )
    )
    front, title, subtitle = _meta_blocks(ast.get("meta") or {}, stem)
    walk = _AstWalk()
    ast["blocks"] = walk.blocks(front + ast["blocks"])
    markdown = _pandoc(["-f", "json", "-t", "gfm", "--wrap=none"], stdin=json.dumps(ast))
    markdown = _remove_immediate_duplicate_gfm_table_headers(markdown)
    markdown = _externalize_long_gfm_table_source_notes(markdown)

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
    """Keep source-owned signal prose on one Markdown line."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Palomar signal field {field} must be non-empty text")
    return " ".join(value.split())


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
        (record for record in active_records if record.get("subject_kind") == "system"),
        key=lambda record: record["paper_id"],
    )
    if system_papers:
        lines += [
            "## Project papers",
            "",
        ]
        lines += [
            f"- [{record['title']}]({_relative_to_corpus(record['local_full_text'])})"
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
            portfolio_path = repo_root / "docs" / "RELATED_PROBLEMS.md"
            if not portfolio_path.is_file():
                raise FileNotFoundError(
                    "Lean paper portfolio route requires "
                    f"{portfolio_path.relative_to(repo_root)}"
                )
            lines += [
                "The [problem summaries](../RELATED_PROBLEMS.md) introduce the "
                "mathematics. `docs/problems.json` contains the corresponding "
                "file paths and identifiers for programs and coding agents.",
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
        route = record.get("first_pass")
        if route:
            entries = route["sections"]
            named = ", ".join(f"[{e['title']}]({_section_link(record, e)})" for e in entries)
            lead = (
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
        "`python3 docs/papers/refresh_paper_corpus.py --write` from the repository root.",
        "This refreshes the text, section maps and this index. Rebuild changed PDFs",
        "and run the repository release checks separately. Companion copies retain",
        "their imported source identities; local edits do not publish a new revision.",
        "",
    ]
    return "\n".join(lines)
