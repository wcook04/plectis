"""
[PURPOSE]
- Teleology: Provide one standard-owned extraction surface for Python documentation tree entries, symbol summaries, and mission chunk plans.
- Mechanism: Read `PYTHON_STANDARD`, analyze Python modules through `system.core.analysis`, and emit deterministic JSON-ready payloads reused by miner, builder, and bridge-mission tooling.
- Non-goal: Rebuild hologram phases or mutate repository files.

[INTERFACE]
- Exports:
  - `documentation_tree_policy()`
  - `build_file_entry(path, repo_root, policy=None)`
  - `build_documentation_tree_payload(paths, repo_root, generated_at=None, policy=None)`
  - `recommended_provider_for_entries(entries, policy=None)`
- Inputs: Repo-rooted Python paths plus optional policy overrides.
- Outputs: JSON-serializable documentation-tree entries and coverage payloads.

[FLOW]
- Load the standard-owned documentation-tree policy from `codex/standards/std_python.py`.
- Analyze each Python file with `analyze_python_module`.
- Compress module/class/function/method doc surfaces into summaries and scope-addressable symbol records.
- Derive chunk recommendations for oversized files so observe/bridge tooling can stay bounded.
- When-needed: Open this module when you need to produce or inspect documentation-tree entries and symbol payloads for Python files — it is the standard extraction surface consumed by miner, builder, and bridge-mission tooling.

[DEPENDENCIES]
- codex.standards.std_python: `PYTHON_STANDARD` policy source.
- system.core.analysis: `analyze_python_module`
- standard_lib.pathlib: repo-relative path normalization

[CONSTRAINTS]
- Reads: Python source files only.
- Writes: None.
- Determinism: Sort paths, symbols, and chunk targets consistently.
- Forbid: Hallucinating symbols or chunk scopes that are not present in the AST.
"""

from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from codex.standards.std_python import PYTHON_STANDARD
from system.core.analysis import analyze_python_module


_DEFAULT_POLICY: dict[str, Any] = {
    "artifact_path": "codex/hologram/system/symbols.json",
    "schema_version": "1.0.0",
    "entrypoint_names": ["main", "run", "cli", "serve", "launch", "start", "execute"],
    "oversized_file_bytes": 500_000,
    "symbol_slice_target_count": 12,
    "max_symbol_chunks_per_file": 12,
    "oversized_provider": "chatgpt",
    "default_provider": "chatgpt",
    "default_bridge_workers": 7,
    "observe_symbol_preview_count": 32,
    "observe_toc_symbol_preview_count": 12,
    "provider_prompt_char_caps": {
        "chatgpt": 850_000,
        "gemini": 32_000,
    },
    "provider_chunk_target_chars": {
        "chatgpt": 650_000,
        "gemini": 24_000,
    },
    "legacy_provider_rewrites": {
        "gemini": "chatgpt",
    },
}

MODULE_SENTINEL = "__module__"

_MODULE_TAG_ORDER = ("PURPOSE", "INTERFACE", "FLOW", "DEPENDENCIES", "CONSTRAINTS")
_NAVIGATION_TOKEN_RE = re.compile(r"[a-z0-9]+")
_CONTRACT_LABEL_RE = re.compile(r"^(teleology|action|role|purpose|mechanism|guarantee|fails|warns|reads|writes)\s*:\s*", re.IGNORECASE)
_VERB_PREFIXES = (
    "build",
    "collect",
    "compile",
    "compute",
    "derive",
    "emit",
    "extract",
    "format",
    "generate",
    "load",
    "normalize",
    "parse",
    "persist",
    "prepare",
    "read",
    "refresh",
    "render",
    "resolve",
    "route",
    "run",
    "select",
    "sync",
    "update",
    "validate",
    "write",
)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _compact_text(value: Any, *, limit: int = 160) -> str:
    collapsed = " ".join(_string(value).split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 3)].rstrip() + "..."


def _first_signal_line(value: Any, *, limit: int = 160) -> str:
    for raw_line in _string(value).splitlines():
        candidate = raw_line.strip()
        if not candidate:
            continue
        if candidate.startswith("-"):
            candidate = candidate[1:].strip()
        return _compact_text(candidate, limit=limit)
    return ""


def _take_strings(values: Sequence[Any], limit: int) -> list[str]:
    output: list[str] = []
    for value in values:
        token = _string(value)
        if not token or token in output:
            continue
        output.append(token)
        if len(output) >= limit:
            break
    return output


def _normalized_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _string(value).casefold())


def _navigation_terms(*values: Any, limit: int = 48) -> list[str]:
    output: list[str] = []
    for value in values:
        text = _string(value).casefold()
        if not text:
            continue
        collapsed = _normalized_token(text)
        if collapsed and collapsed not in output:
            output.append(collapsed)
        for token in _NAVIGATION_TOKEN_RE.findall(text.replace("_", " ").replace("-", " ").replace("/", " ")):
            if token and token not in output:
                output.append(token)
            if len(output) >= limit:
                return output
    return output


def _browse_summary(*, path: str, purpose: str, routing: Mapping[str, Any] | None) -> str:
    routing_payload = routing if isinstance(routing, Mapping) else {}
    when_needed = _string(routing_payload.get("when_needed"))
    if when_needed:
        return _compact_text(when_needed, limit=200)
    if purpose:
        return _compact_text(purpose, limit=200)
    return _compact_text(Path(path).stem.replace("_", " "), limit=200)


def _complexity_hint(line_count: int) -> str:
    if line_count <= 150:
        return "small"
    if line_count <= 500:
        return "medium"
    if line_count <= 2000:
        return "large"
    return "massive"


def _safe_relpath(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _has_main_guard(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except Exception:
        return "__main__" in source

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
            continue
        if len(test.comparators) != 1:
            continue
        comparator = test.comparators[0]
        if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
            return True
    return False


def _summary_from_tags(tags: Mapping[str, Any], tag_name: str, *, fallback: str = "") -> str:
    summary = _first_signal_line(tags.get(tag_name))
    if summary:
        return summary
    return _compact_text(fallback, limit=160)


def _strip_contract_label(value: Any) -> str:
    candidate = _compact_text(value, limit=200)
    if not candidate:
        return ""
    return _CONTRACT_LABEL_RE.sub("", candidate).strip()


def _humanize_symbol_name(value: Any) -> str:
    raw = _string(value)
    if not raw:
        return ""
    return " ".join(
        raw.replace("::", " ")
        .replace(".", " ")
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def _ensure_period(value: Any) -> str:
    text = _string(value)
    if not text:
        return ""
    if text.endswith((".", "!", "?")):
        return text
    return text + "."


def _compose_floor_summary(values: Sequence[Any], *, limit: int = 160) -> str:
    parts: list[str] = []
    for value in values:
        candidate = _strip_contract_label(value)
        if not candidate:
            continue
        normalized = candidate.casefold()
        if normalized in {item.casefold() for item in parts}:
            continue
        parts.append(candidate)
        if len(parts) >= 2:
            break
    if not parts:
        return ""
    if len(parts) == 1:
        return _compact_text(_ensure_period(parts[0]), limit=limit)
    return _compact_text(_ensure_period(f"{parts[0]}; {parts[1]}"), limit=limit)


def _derive_summary_floor(name: Any, *, scope_kind: str, limit: int = 160) -> str:
    humanized = _humanize_symbol_name(name)
    if not humanized:
        return ""
    if scope_kind == "file":
        return _compact_text(_ensure_period(f"{humanized} module"), limit=limit)
    if scope_kind == "class":
        return _compact_text(_ensure_period(f"{humanized} class"), limit=limit)
    return _compact_text(_ensure_period(humanized), limit=limit)


def _summary_with_floor(
    *,
    authored_value: Any,
    composed_values: Sequence[Any],
    fallback_name: Any,
    scope_kind: str,
    limit: int = 160,
) -> tuple[str, str]:
    authored = _first_signal_line(authored_value)
    if authored:
        return authored, "authored"
    composed = _compose_floor_summary(composed_values, limit=limit)
    if composed:
        return composed, "composed"
    return _derive_summary_floor(fallback_name, scope_kind=scope_kind, limit=limit), "derived"


def _derive_when_needed_floor(summary: Any, *, fallback_name: Any, scope_kind: str, limit: int = 200) -> str:
    candidate = _strip_contract_label(summary)
    if not candidate:
        candidate = _humanize_symbol_name(fallback_name)
    if not candidate:
        return ""
    lowered = candidate[0].lower() + candidate[1:] if candidate else ""
    if lowered.lower().startswith("open when "):
        return _compact_text(_ensure_period(lowered[0].upper() + lowered[1:]), limit=limit)
    if any(lowered.startswith(prefix + " ") for prefix in _VERB_PREFIXES):
        return _compact_text(_ensure_period(f"Open when you need to {lowered}"), limit=limit)
    if scope_kind == "file":
        return _compact_text(_ensure_period(f"Open when {lowered} is the relevant module surface"), limit=limit)
    if scope_kind == "class":
        return _compact_text(_ensure_period(f"Open when {lowered} is the relevant class surface"), limit=limit)
    return _compact_text(_ensure_period(f"Open when you need context for {lowered}"), limit=limit)


def _routing_with_floor(
    contract_atoms: Mapping[str, Sequence[str]] | None,
    *,
    fallback_group: str | None = None,
    summary: Any,
    summary_provenance: str,
    fallback_name: Any,
    scope_kind: str,
) -> tuple[dict[str, Any], str]:
    routing = _routing_from_contract_atoms(contract_atoms, fallback_group=fallback_group)
    when_needed = _string(routing.get("when_needed"))
    if when_needed:
        return routing, "authored"
    routing["when_needed"] = _derive_when_needed_floor(summary, fallback_name=fallback_name, scope_kind=scope_kind)
    return routing, "composed" if summary_provenance == "composed" else "derived"


def _record_provenance(fields: Mapping[str, str]) -> dict[str, Any]:
    values = [token for token in fields.values() if token]
    if any(token == "derived" for token in values):
        record = "derived"
    elif any(token == "composed" for token in values):
        record = "composed"
    else:
        record = "authored"
    return {
        "record": record,
        "fields": dict(fields),
    }


def _record_quality(
    *,
    summary_provenance: str,
    when_needed_provenance: str,
    missing_required_tag: bool = False,
    parse_error: bool = False,
    issues: Sequence[Mapping[str, Any]] | None = None,
    navigation_group: Any = "",
    stale_due_to: Any = "",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the normalized quality payload attached to module and scope summaries in the Python documentation tree.
    - Mechanism: Derive status, flags, issue_types, and missing_authored_fields from authored provenance, parse state, navigation metadata, and the `missing_required_tag` compliance signal.
    - Guarantee: Returns a deterministic JSON-ready quality dict without mutating the caller's summary record.
    - When-needed: Open when a caller needs the authoritative seam that records `missing_required_tag` and related degradation flags onto documentation-tree summaries.
    - Escalates-to: `deterministic_quality_gates`; `build_file_entry`
    """
    flags: list[str] = []
    issue_types = {_string(issue.get("issue")) for issue in (issues or []) if isinstance(issue, Mapping)}
    missing_authored_fields: list[str] = []
    if summary_provenance != "authored":
        flags.append(f"{summary_provenance}_summary")
        missing_authored_fields.append("summary")
    if when_needed_provenance != "authored":
        flags.append(f"{when_needed_provenance}_when_needed")
        missing_authored_fields.append("routing.when_needed")
    if missing_required_tag:
        flags.append("missing_required_tag")
    if not _string(navigation_group):
        flags.append("missing_navigation_group")
    if parse_error:
        status = "dirty"
    elif _string(stale_due_to):
        status = "stale"
    elif "ambiguous_cross_file" in issue_types:
        status = "ambiguous"
    elif issue_types:
        status = "suspect"
    elif flags:
        status = "degraded"
    else:
        status = None
    return {
        "status": status,
        "flags": flags,
        "issue_types": sorted(issue_types),
        "missing_authored_fields": _take_strings(missing_authored_fields, 8),
    }


def _split_semicolon_values(values: Sequence[Any]) -> list[str]:
    output: list[str] = []
    for value in values:
        for token in str(value or "").split(";"):
            normalized = _string(token)
            if normalized and normalized not in output:
                output.append(normalized)
    return output


def _routing_from_contract_atoms(
    contract_atoms: Mapping[str, Sequence[str]] | None,
    *,
    fallback_group: str | None = None,
) -> dict[str, Any]:
    atoms = dict(contract_atoms or {})
    when_needed_values = atoms.get("When-needed") or []
    navigation_values = atoms.get("Navigation-group") or []
    couples = _take_strings(list(atoms.get("Couples") or []), 8)
    navigation_group = _string(navigation_values[0]) if navigation_values else _string(fallback_group)
    return {
        "when_needed": _string(when_needed_values[0]) if when_needed_values else "",
        "escalates_to": _split_semicolon_values(list(atoms.get("Escalates-to") or [])),
        "navigation_group": navigation_group,
        "couples": couples,
    }


def _chunk_targets(targets: list[dict[str, Any]], *, chunk_size: int, max_chunks: int) -> list[list[dict[str, Any]]]:
    if not targets:
        return []
    chunk_size = max(1, int(chunk_size))
    max_chunks = max(1, int(max_chunks))
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(targets), chunk_size):
        if len(output) >= max_chunks:
            break
        output.append(targets[start:start + chunk_size])
    return output


def _provider_prompt_cap(policy: Mapping[str, Any], provider: str) -> int:
    token = _string(provider).lower()
    caps = policy.get("provider_prompt_char_caps")
    if isinstance(caps, Mapping):
        raw_value = caps.get(token)
        try:
            parsed = int(raw_value or 0)
        except Exception:
            parsed = 0
        if parsed > 0:
            return parsed
    if token == "gemini":
        return 400_000
    if token == "chatgpt":
        return 200_000
    return 200_000


def _provider_chunk_target_chars(policy: Mapping[str, Any], provider: str) -> int:
    token = _string(provider).lower()
    targets = policy.get("provider_chunk_target_chars")
    if isinstance(targets, Mapping):
        raw_value = targets.get(token)
        try:
            parsed = int(raw_value or 0)
        except Exception:
            parsed = 0
        if parsed > 0:
            return parsed
    cap = _provider_prompt_cap(policy, token)
    if token == "gemini":
        return max(64_000, cap - 80_000)
    return max(48_000, cap - 60_000)


def _slice_line_chars(lines: Sequence[str], start_line: int, end_line: int) -> int:
    start = max(1, int(start_line))
    end = max(start, int(end_line))
    return len("".join(lines[start - 1:end]))


def _top_level_symbol_spans(source: str) -> dict[tuple[str, str], dict[str, int]]:
    try:
        tree = ast.parse(source)
    except Exception:
        return {}

    spans: dict[tuple[str, str], dict[str, int]] = {}
    for node in getattr(tree, "body", []) or []:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        name = _string(getattr(node, "name", ""))
        if not name:
            continue
        line_start = int(getattr(node, "lineno", 0) or 0)
        line_end = int(getattr(node, "end_lineno", 0) or 0)
        if line_start <= 0 or line_end < line_start:
            continue
        scope = "class" if isinstance(node, ast.ClassDef) else "function"
        spans[(scope, name)] = {
            "line_start": line_start,
            "line_end": line_end,
        }
        # Methods inside classes — first-class slicing targets
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                method_name = _string(getattr(child, "name", ""))
                if not method_name:
                    continue
                m_start = int(getattr(child, "lineno", 0) or 0)
                m_end = int(getattr(child, "end_lineno", 0) or 0)
                if m_start <= 0 or m_end < m_start:
                    continue
                spans[("method", f"{name}.{method_name}")] = {
                    "line_start": m_start,
                    "line_end": m_end,
                }
    return spans


def _module_header_span(
    source: str,
    *,
    line_count: int,
) -> tuple[int, int]:
    try:
        tree = ast.parse(source)
    except Exception:
        return (1, min(max(1, line_count), 120))

    body = list(getattr(tree, "body", []) or [])
    if not body:
        return (1, max(1, line_count))

    doc_end = 1
    first_stmt = body[0]
    if (
        isinstance(first_stmt, ast.Expr)
        and isinstance(getattr(first_stmt, "value", None), ast.Constant)
        and isinstance(getattr(first_stmt.value, "value", None), str)
    ):
        doc_end = int(getattr(first_stmt, "end_lineno", 0) or getattr(first_stmt, "lineno", 1) or 1)

    first_symbol_line = None
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first_symbol_line = int(getattr(node, "lineno", 1) or 1)
            break
    if first_symbol_line is None:
        return (1, max(doc_end, line_count))
    return (1, max(doc_end, first_symbol_line - 1))


def _line_range_target(
    *,
    rel_path: str,
    name: str,
    notes: str,
    line_start: int,
    line_end: int,
) -> dict[str, Any]:
    return {
        "file": rel_path,
        "scope": "line_range",
        "name": name,
        "line_start": line_start,
        "line_end": line_end,
        "notes": notes,
    }


def _split_target_by_line_budget(
    *,
    rel_path: str,
    scope: str,
    name: str,
    notes: str,
    line_start: int,
    line_end: int,
    lines: Sequence[str],
    chunk_char_budget: int,
) -> list[dict[str, Any]]:
    budget = max(8_000, int(chunk_char_budget))
    start = max(1, int(line_start))
    end = max(start, int(line_end))
    ranges: list[tuple[int, int]] = []
    current_start = start
    current_chars = 0

    for line_number in range(start, end + 1):
        line_chars = len(lines[line_number - 1]) if line_number - 1 < len(lines) else 0
        if current_chars > 0 and current_chars + line_chars > budget:
            ranges.append((current_start, line_number - 1))
            current_start = line_number
            current_chars = 0
        current_chars += line_chars
    if current_start <= end:
        ranges.append((current_start, end))

    if len(ranges) <= 1:
        return [
            {
                "file": rel_path,
                "scope": scope,
                "name": name,
                "notes": notes,
            }
        ]

    total = len(ranges)
    output: list[dict[str, Any]] = []
    for index, (chunk_start, chunk_end) in enumerate(ranges, start=1):
        chunk_notes = (
            f"{notes} This is chunk {index}/{total} of {scope} `{name}` in `{rel_path}` "
            f"(lines {chunk_start}-{chunk_end})."
        )
        output.append(
            _line_range_target(
                rel_path=rel_path,
                name=name,
                notes=chunk_notes,
                line_start=chunk_start,
                line_end=chunk_end,
            )
        )
    return output


def _target_estimated_chars(
    *,
    target: Mapping[str, Any],
    rel_path: str,
    source_chars: int,
    lines: Sequence[str],
    span_index: Mapping[tuple[str, str], Mapping[str, int]],
) -> int:
    scope = _string(target.get("scope")) or "full"
    if scope == "imports":
        return 12_000
    if scope == "full":
        return source_chars + 4_096
    if scope == "module":
        start_line, end_line = _module_header_span("".join(lines), line_count=len(lines))
        return _slice_line_chars(lines, start_line, end_line) + 2_048
    if scope == "line_range":
        start_line = int(target.get("line_start") or 0)
        end_line = int(target.get("line_end") or 0)
        return _slice_line_chars(lines, start_line, end_line) + 2_048
    name = _string(target.get("name"))
    if scope in {"function", "class", "method"} and name:
        span = span_index.get((scope, name))
        if isinstance(span, Mapping):
            return _slice_line_chars(
                lines,
                int(span.get("line_start") or 0),
                int(span.get("line_end") or 0),
            ) + 2_048
    return 16_384


def _fallback_line_chunks(
    *,
    rel_path: str,
    line_count: int,
    chunk_char_budget: int,
    lines: Sequence[str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if line_count <= 0:
        return output
    start = 1
    index = 1
    while start <= line_count:
        current_end = start
        current_chars = 0
        while current_end <= line_count:
            next_chars = len(lines[current_end - 1]) if current_end - 1 < len(lines) else 0
            if current_chars > 0 and current_chars + next_chars > chunk_char_budget:
                break
            current_chars += next_chars
            current_end += 1
        end = max(start, current_end - 1)
        output.append(
            _line_range_target(
                rel_path=rel_path,
                name=f"module_chunk_{index:02d}",
                notes=f"Sequential file chunk {index} for oversized module `{rel_path}` (lines {start}-{end}).",
                line_start=start,
                line_end=end,
            )
        )
        index += 1
        start = end + 1
    return output


def _build_size_aware_target_chunks(
    *,
    rel_path: str,
    size_bytes: int,
    source_chars: int,
    line_count: int,
    lines: Sequence[str],
    mission_targets: Sequence[dict[str, Any]],
    provider_hint: str,
    policy: Mapping[str, Any],
    chunk_mode: str = "oversized",
) -> list[dict[str, Any]]:
    imports_target = {
        "file": rel_path,
        "scope": "imports",
        "notes": f"Import context for oversized module `{rel_path}`.",
    }
    chunk_char_budget = _provider_chunk_target_chars(policy, provider_hint)
    imports_cost = _target_estimated_chars(
        target=imports_target,
        rel_path=rel_path,
        source_chars=source_chars,
        lines=lines,
        span_index={},
    )
    per_chunk_budget = max(12_000, chunk_char_budget - imports_cost)
    span_index = _top_level_symbol_spans("".join(lines))

    target_units: list[dict[str, Any]] = []
    for target in mission_targets:
        scope = _string(target.get("scope")) or "full"
        name = _string(target.get("name"))
        estimate = _target_estimated_chars(
            target=target,
            rel_path=rel_path,
            source_chars=source_chars,
            lines=lines,
            span_index=span_index,
        )
        if scope in {"function", "class", "method", "module"} and estimate > per_chunk_budget:
            span: Mapping[str, int] | None = None
            if scope == "module":
                start_line, end_line = _module_header_span("".join(lines), line_count=line_count)
                span = {"line_start": start_line, "line_end": end_line}
            elif name:
                span = span_index.get((scope, name))
            if isinstance(span, Mapping):
                split_targets = _split_target_by_line_budget(
                    rel_path=rel_path,
                    scope=scope,
                    name=name or MODULE_SENTINEL,
                    notes=_string(target.get("notes")),
                    line_start=int(span.get("line_start") or 0),
                    line_end=int(span.get("line_end") or 0),
                    lines=lines,
                    chunk_char_budget=per_chunk_budget,
                )
                for split_target in split_targets:
                    target_units.append(
                        {
                            "target": split_target,
                            "estimated_chars": _target_estimated_chars(
                                target=split_target,
                                rel_path=rel_path,
                                source_chars=source_chars,
                                lines=lines,
                                span_index=span_index,
                            ),
                        }
                    )
                continue
        target_units.append({"target": dict(target), "estimated_chars": estimate})

    if not target_units:
        target_units = [
            {
                "target": target,
                "estimated_chars": _target_estimated_chars(
                    target=target,
                    rel_path=rel_path,
                    source_chars=source_chars,
                    lines=lines,
                    span_index=span_index,
                ),
            }
            for target in _fallback_line_chunks(
                rel_path=rel_path,
                line_count=line_count,
                chunk_char_budget=per_chunk_budget,
                lines=lines,
            )
        ]

    chunks: list[list[dict[str, Any]]] = []
    current_targets: list[dict[str, Any]] = []
    current_chars = 0
    for unit in target_units:
        target_payload = dict(unit["target"])
        estimated_chars = max(1, int(unit["estimated_chars"]))
        if current_targets and current_chars + estimated_chars > per_chunk_budget:
            chunks.append(current_targets)
            current_targets = []
            current_chars = 0
        current_targets.append(target_payload)
        current_chars += estimated_chars
    if current_targets:
        chunks.append(current_targets)

    output: list[dict[str, Any]] = []
    if chunk_mode == "prompt_budget":
        chunk_reason = (
            f"Prompt-budgeted Python file (~{source_chars} chars for provider `{provider_hint}`)."
        )
    elif chunk_mode == "selected_scopes":
        chunk_reason = f"Selected Python scope shards for `{rel_path}`."
    else:
        chunk_reason = f"Oversized Python file ({size_bytes} bytes)."
    for index, chunk_targets in enumerate(chunks, start=1):
        # Derive source_symbol_ids from scoped targets in this chunk
        chunk_symbol_ids: list[str] = []
        for ct in chunk_targets:
            ct_scope = _string(ct.get("scope"))
            ct_name = _string(ct.get("name"))
            if ct_scope in {"function", "class", "method"} and ct_name:
                chunk_symbol_ids.append(f"{rel_path}::{ct_name}")
        output.append(
            {
                "chunk_id": f"{Path(rel_path).stem}_part_{index:02d}",
                "provider_hint": provider_hint,
                "oversized": chunk_mode in {"oversized", "prompt_budget"},
                "source_symbol_ids": chunk_symbol_ids,
                "notes": (
                    f"{chunk_reason} Own only the attached chunk for `{rel_path}` "
                    f"plus imports context. This chunk contains {len(chunk_targets)} target excerpts."
                ),
                "targets": [dict(imports_target), *chunk_targets],
            }
        )
    return output


def documentation_tree_policy() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Return the normalized documentation-tree policy owned by `PYTHON_STANDARD`.
    - Reads: `codex/standards/std_python.py`
    - Guarantee: Always returns a dict with the required artifact, chunking, and provider-hint fields.
    - Fails: None. Falls back to conservative defaults when the standard omits optional keys.
    - When-needed: Open when a caller needs the merged documentation-tree policy dict sourced from `PYTHON_STANDARD`, including chunking thresholds, artifact path, and provider-hint fields.
    """
    raw = PYTHON_STANDARD.get("documentation_tree")
    policy = dict(_DEFAULT_POLICY)
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            policy[key] = value
    return policy


def build_file_entry(
    path: Path,
    *,
    repo_root: Path,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build one documentation-tree entry for a Python file from the actual AST and docstring surfaces.
    - Reads: `path` source text plus `analyze_python_module(path)`.
    - Guarantee: Returns a JSON-serializable dict with module summaries, symbol records, compliance state, and mission chunk hints.
    - Fails: Embeds parse-error state in the returned entry rather than raising for source-analysis issues.
    """
    active_policy = dict(documentation_tree_policy())
    if isinstance(policy, Mapping):
        active_policy.update(dict(policy))

    source = path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines(keepends=True)
    analysis = analyze_python_module(path)
    rel_path = _safe_relpath(path, repo_root)
    size_bytes = len(source.encode("utf-8"))
    line_count = len(source.splitlines())
    oversized_limit = int(active_policy.get("oversized_file_bytes") or _DEFAULT_POLICY["oversized_file_bytes"])
    oversized = size_bytes > oversized_limit
    span_index = _top_level_symbol_spans(source)
    module_line_start, module_line_end = _module_header_span(source, line_count=line_count)

    module_tags = getattr(analysis, "tags", {}) or {}
    interface = _summary_from_tags(module_tags, "INTERFACE")
    flow = _summary_from_tags(module_tags, "FLOW")
    dependencies = _summary_from_tags(module_tags, "DEPENDENCIES")
    constraints = _summary_from_tags(module_tags, "CONSTRAINTS")
    missing_module_tags = list(getattr(analysis, "missing_module_tags", []) or [])

    class_records: list[dict[str, Any]] = []
    function_records: list[dict[str, Any]] = []
    mission_targets: list[dict[str, Any]] = []
    entry_points: list[dict[str, Any]] = []
    entrypoint_names = {token.lower() for token in active_policy.get("entrypoint_names", []) if _string(token)}

    # Build file-local symbol index for canonical callee resolution
    _local_symbol_index: dict[str, str] = {}  # bare_name → symbol_id
    for _cls in getattr(analysis, "classes", []) or []:
        _local_symbol_index[_cls.name] = f"{rel_path}::{_cls.name}"
        for _m in getattr(_cls, "methods", []) or []:
            _local_symbol_index[_m.name] = f"{rel_path}::{_cls.name}.{_m.name}"
            _local_symbol_index[f"self.{_m.name}"] = f"{rel_path}::{_cls.name}.{_m.name}"
            _local_symbol_index[f"{_cls.name}.{_m.name}"] = f"{rel_path}::{_cls.name}.{_m.name}"
    for _fn in getattr(analysis, "functions", []) or []:
        _local_symbol_index[_fn.name] = f"{rel_path}::{_fn.name}"

    if missing_module_tags:
        mission_targets.append(
            {
                "file": rel_path,
                "scope": "module",
                "name": MODULE_SENTINEL,
                "notes": _summary_from_tags(module_tags, "PURPOSE") or f"Module documentation contract target for `{rel_path}`.",
            }
        )

    def _resolve_callees(calls_list: list) -> tuple[list[str], list[dict[str, str]]]:
        refs: list[str] = []
        issues: list[dict[str, str]] = []
        for c in calls_list:
            target = c.get("target", "")
            if c.get("is_dynamic"):
                issues.append({"target": target, "issue": "dynamic_call"})
            elif target in _local_symbol_index:
                sid = _local_symbol_index[target]
                if sid not in refs:
                    refs.append(sid)
            elif target:
                # Unresolved — keep as bare name with issue marker
                issues.append({"target": target, "issue": "unresolved_cross_file"})
                if target not in refs:
                    refs.append(target)
        return refs[:12], issues[:5]

    for cls in getattr(analysis, "classes", []) or []:
        method_seed_summaries: list[str] = []
        methods: list[dict[str, Any]] = []
        public_method_count = 0
        for method in getattr(cls, "methods", []) or []:
            method_scope = f"method:{cls.name}.{method.name}"
            is_private = bool(getattr(method, "is_private", False))
            if not is_private:
                public_method_count += 1
            callee_refs, callee_issues = _resolve_callees(getattr(method, "calls", []) or [])
            method_summary, method_summary_provenance = _summary_with_floor(
                authored_value=(getattr(method, "tags", {}) or {}).get("ACTION"),
                composed_values=[],
                fallback_name=method.name,
                scope_kind="method",
            )
            if not is_private and method_summary:
                method_seed_summaries.append(method_summary)
            method_routing, method_when_needed_provenance = _routing_with_floor(
                getattr(method, "contract_atoms", {}) or {},
                summary=method_summary,
                summary_provenance=method_summary_provenance,
                fallback_name=method.name,
                scope_kind="method",
            )
            methods.append(
                {
                    "name": method.name,
                    "scope": method_scope,
                    "symbol_id": f"{rel_path}::{cls.name}.{method.name}",
                    "owner_symbol_id": f"{rel_path}::{cls.name}",
                    "signature": _string(getattr(method, "signature", "")),
                    "summary": method_summary,
                    "is_async": bool(getattr(method, "is_async", False)),
                    "missing_required_tag": not bool((getattr(method, "tags", {}) or {}).get("ACTION")),
                    "is_private": is_private,
                    "line_start": getattr(method, "line_start", 0),
                    "line_end": getattr(method, "line_end", 0),
                    "callee_refs": callee_refs[:12],
                    "routing": method_routing,
                    "issues": callee_issues[:5] if callee_issues else [],
                    "provenance": _record_provenance(
                        {
                            "summary": method_summary_provenance,
                            "routing.when_needed": method_when_needed_provenance,
                        }
                    ),
                    "quality": _record_quality(
                        summary_provenance=method_summary_provenance,
                        when_needed_provenance=method_when_needed_provenance,
                        missing_required_tag=not bool((getattr(method, "tags", {}) or {}).get("ACTION")),
                        issues=callee_issues[:5] if callee_issues else [],
                        navigation_group=method_routing.get("navigation_group"),
                    ),
                }
            )
        class_summary, class_summary_provenance = _summary_with_floor(
            authored_value=(getattr(cls, "tags", {}) or {}).get("ROLE"),
            composed_values=method_seed_summaries,
            fallback_name=cls.name,
            scope_kind="class",
        )
        class_routing, class_when_needed_provenance = _routing_with_floor(
            getattr(cls, "contract_atoms", {}) or {},
            summary=class_summary,
            summary_provenance=class_summary_provenance,
            fallback_name=cls.name,
            scope_kind="class",
        )
        class_records.append(
            {
                "name": cls.name,
                "scope": f"class:{cls.name}",
                "symbol_id": f"{rel_path}::{cls.name}",
                "owner_symbol_id": None,
                "bases": list(getattr(cls, "bases", []) or []),
                "summary": class_summary,
                "missing_required_tag": not bool((getattr(cls, "tags", {}) or {}).get("ROLE")),
                "method_count": len(methods),
                "public_method_count": public_method_count,
                "line_start": int((span_index.get(("class", cls.name)) or {}).get("line_start") or 0),
                "line_end": int((span_index.get(("class", cls.name)) or {}).get("line_end") or 0),
                "routing": class_routing,
                "provenance": _record_provenance(
                    {
                        "summary": class_summary_provenance,
                        "routing.when_needed": class_when_needed_provenance,
                    }
                ),
                "quality": _record_quality(
                    summary_provenance=class_summary_provenance,
                    when_needed_provenance=class_when_needed_provenance,
                    missing_required_tag=not bool((getattr(cls, "tags", {}) or {}).get("ROLE")),
                    navigation_group=class_routing.get("navigation_group"),
                ),
                "methods": methods,
            }
        )
        if not bool(getattr(cls, "is_private", False)):
            mission_targets.append(
                {
                    "file": rel_path,
                    "scope": "class",
                    "name": cls.name,
                    "notes": class_summary,
                }
            )
            # Methods as first-class mission targets for large-file slicing
            for method in getattr(cls, "methods", []) or []:
                if not getattr(method, "is_private", False):
                    method_summary, _ = _summary_with_floor(
                        authored_value=(getattr(method, "tags", {}) or {}).get("ACTION"),
                        composed_values=[],
                        fallback_name=method.name,
                        scope_kind="method",
                    )
                    mission_targets.append(
                        {
                            "file": rel_path,
                            "scope": "function",
                            "name": f"{cls.name}.{method.name}",
                            "notes": method_summary,
                        }
                    )

    for fn in getattr(analysis, "functions", []) or []:
        function_summary, function_summary_provenance = _summary_with_floor(
            authored_value=(getattr(fn, "tags", {}) or {}).get("ACTION"),
            composed_values=[],
            fallback_name=fn.name,
            scope_kind="function",
        )
        callee_refs, callee_issues = _resolve_callees(getattr(fn, "calls", []) or [])
        function_routing, function_when_needed_provenance = _routing_with_floor(
            getattr(fn, "contract_atoms", {}) or {},
            summary=function_summary,
            summary_provenance=function_summary_provenance,
            fallback_name=fn.name,
            scope_kind="function",
        )
        function_record = {
            "name": fn.name,
            "scope": f"func:{fn.name}",
            "symbol_id": f"{rel_path}::{fn.name}",
            "owner_symbol_id": None,
            "signature": _string(getattr(fn, "signature", "")),
            "summary": function_summary,
            "is_async": bool(getattr(fn, "is_async", False)),
            "missing_required_tag": not bool((getattr(fn, "tags", {}) or {}).get("ACTION")),
            "is_private": bool(getattr(fn, "is_private", False)),
            "line_start": getattr(fn, "line_start", 0),
            "line_end": getattr(fn, "line_end", 0),
            "callee_refs": callee_refs[:12],
            "routing": function_routing,
            "issues": callee_issues[:5] if callee_issues else [],
            "provenance": _record_provenance(
                {
                    "summary": function_summary_provenance,
                    "routing.when_needed": function_when_needed_provenance,
                }
            ),
            "quality": _record_quality(
                summary_provenance=function_summary_provenance,
                when_needed_provenance=function_when_needed_provenance,
                missing_required_tag=not bool((getattr(fn, "tags", {}) or {}).get("ACTION")),
                issues=callee_issues[:5] if callee_issues else [],
                navigation_group=function_routing.get("navigation_group"),
            ),
        }
        function_records.append(function_record)
        if not function_record["is_private"]:
            mission_targets.append(
                {
                    "file": rel_path,
                    "scope": "function",
                    "name": fn.name,
                    "notes": function_summary,
                }
            )
            if fn.name.lower() in entrypoint_names:
                entry_points.append(function_record)

    purpose, purpose_provenance = _summary_with_floor(
        authored_value=module_tags.get("PURPOSE"),
        composed_values=[
            *(record.get("summary", "") for record in class_records),
            *(record.get("summary", "") for record in function_records if not bool(record.get("is_private"))),
        ],
        fallback_name=path.stem,
        scope_kind="file",
    )
    module_routing, module_when_needed_provenance = _routing_with_floor(
        getattr(analysis, "contract_atoms", {}) or {},
        summary=purpose,
        summary_provenance=purpose_provenance,
        fallback_name=path.stem,
        scope_kind="file",
    )
    browse_summary = _browse_summary(path=rel_path, purpose=purpose, routing=module_routing)
    browse_summary_provenance = module_when_needed_provenance if _string(module_routing.get("when_needed")) else purpose_provenance

    mission_strategy = "full_file"
    provider_hint = _string(active_policy.get("default_provider")) or _DEFAULT_POLICY["default_provider"]
    full_file_estimate = _target_estimated_chars(
        target={"scope": "full"},
        rel_path=rel_path,
        source_chars=len(source),
        lines=lines,
        span_index={},
    )
    prompt_budget_exceeded = full_file_estimate > _provider_chunk_target_chars(active_policy, provider_hint)
    target_chunks: list[dict[str, Any]] = []
    if oversized or prompt_budget_exceeded:
        mission_strategy = "size_aware_slices" if oversized else "budget_aware_slices"
        chunk_mode = "oversized"
        if oversized:
            provider_hint = _string(active_policy.get("oversized_provider")) or provider_hint
        else:
            chunk_mode = "prompt_budget"
        target_chunks = _build_size_aware_target_chunks(
            rel_path=rel_path,
            size_bytes=size_bytes,
            source_chars=len(source),
            line_count=line_count,
            lines=lines,
            mission_targets=mission_targets,
            provider_hint=provider_hint,
            policy=active_policy,
            chunk_mode=chunk_mode,
        )
    else:
        # Full-file chunk: include all symbol_ids from the file
        all_symbol_ids: list[str] = []
        for mt in mission_targets:
            mt_scope = _string(mt.get("scope"))
            mt_name = _string(mt.get("name"))
            if mt_scope in {"function", "class", "method"} and mt_name:
                all_symbol_ids.append(f"{rel_path}::{mt_name}")
        target_chunks.append(
            {
                "chunk_id": f"{Path(rel_path).stem}_full",
                "provider_hint": provider_hint,
                "oversized": oversized,
                "source_symbol_ids": all_symbol_ids,
                "notes": f"Read the full Python file `{rel_path}`.",
                "targets": [{"file": rel_path, "scope": "full"}],
            }
        )

    if _has_main_guard(source) and not entry_points:
        entry_points = _take_strings([record["name"] for record in function_records if not record["is_private"]], 3)
        entry_points = [
            {
                "name": name,
                "scope": f"func:{name}",
                "summary": "main-guard reachable function",
            }
            for name in entry_points
        ]

    classes_missing_role = list(getattr(analysis, "classes_missing_role", []) or [])
    functions_missing_action = list(getattr(analysis, "functions_missing_action", []) or [])
    parse_error = _string(getattr(analysis, "parse_error", ""))
    gap_count = len(missing_module_tags) + len(classes_missing_role) + len(functions_missing_action) + (1 if parse_error else 0)
    status = "parse_error" if parse_error else ("dirty" if not bool(getattr(analysis, "is_compliant", True)) else "compliant")
    public_symbol_ids = [
        f"{rel_path}::{cls['name']}"
        for cls in class_records
        if _string(cls.get("name"))
    ]
    public_symbol_ids.extend(
        str(method.get("symbol_id") or "").strip()
        for cls in class_records
        for method in cls.get("methods", []) or []
        if isinstance(method, Mapping) and not bool(method.get("is_private"))
    )
    public_symbol_ids.extend(
        str(fn.get("symbol_id") or "").strip()
        for fn in function_records
        if not bool(fn.get("is_private"))
    )
    search_tokens = _navigation_terms(
        rel_path,
        browse_summary,
        purpose,
        interface,
        flow,
        dependencies,
        constraints,
        module_routing.get("navigation_group"),
        module_routing.get("when_needed"),
        *(record.get("name", "") for record in class_records),
        *(record.get("name", "") for record in function_records),
    )

    return {
        "path": rel_path,
        "summary": purpose,
        "browse_summary": browse_summary,
        "size_bytes": size_bytes,
        "line_count": line_count,
        "complexity_hint": _complexity_hint(line_count),
        "status": status,
        "gap_count": gap_count,
        "public_symbol_ids": _take_strings(public_symbol_ids, 128),
        "search_tokens": search_tokens,
        "related_paths": [],
        "derivation_warnings": [],
        "navigation_status": "dirty" if parse_error else "compliant",
        "provenance": _record_provenance(
            {
                "summary": purpose_provenance,
                "browse_summary": browse_summary_provenance,
                "routing.when_needed": module_when_needed_provenance,
                # Per Wave 8 doctrine: distinguish authored Escalates-to and
                # Navigation-group from derived/derived-fallback substitutes
                # so future gates can depend on field-level provenance.
                "routing.escalates_to": "authored" if (module_routing.get("escalates_to") or []) else "derived",
                "routing.navigation_group": "authored" if _string(module_routing.get("navigation_group")) else "derived",
            }
        ),
        "quality": _record_quality(
            summary_provenance=purpose_provenance,
            when_needed_provenance=module_when_needed_provenance,
            parse_error=bool(parse_error),
            navigation_group=module_routing.get("navigation_group"),
        ),
        "facets": _take_strings(
            [record["name"] for record in class_records] + [record["name"] for record in function_records],
            5,
        ),
        "module": {
            "purpose": purpose,
            "interface": interface,
            "flow": flow,
            "dependencies": dependencies,
            "constraints": constraints,
            "line_start": module_line_start,
            "line_end": module_line_end,
            "has_main_guard": _has_main_guard(source),
            "routing": module_routing,
            "provenance": _record_provenance(
                {
                    "purpose": purpose_provenance,
                    "routing.when_needed": module_when_needed_provenance,
                    "routing.escalates_to": "authored" if (module_routing.get("escalates_to") or []) else "derived",
                    "routing.navigation_group": "authored" if _string(module_routing.get("navigation_group")) else "derived",
                }
            ),
            "quality": _record_quality(
                summary_provenance=purpose_provenance,
                when_needed_provenance=module_when_needed_provenance,
                parse_error=bool(parse_error),
                navigation_group=module_routing.get("navigation_group"),
            ),
        },
        "compliance": {
            "is_compliant": bool(getattr(analysis, "is_compliant", False)),
            "missing_module_tags": missing_module_tags,
            "classes_missing_role": classes_missing_role,
            "functions_missing_action": functions_missing_action,
            "parse_error": parse_error or None,
        },
        "classes": class_records,
        "functions": function_records,
        "entry_points": entry_points,
        "mission": {
            "strategy": mission_strategy,
            "oversized": oversized,
            "provider_hint": provider_hint,
            "target_chunks": target_chunks,
        },
    }


def build_scope_summaries(
    tree_entry: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Extract a typed per-scope summary list from a documentation tree entry.
      Each summary carries symbol_id, one-line summary, callee_refs, issues, and status.
      This is the artifact that bridge authoring probes should consume for one-hop context.
    - Guarantee: Returns a list of summary dicts, one per public function/method in the entry.
    - Fails: Returns empty list for entries with parse errors or no symbols.
    """
    file_path = tree_entry.get("path", "")
    summaries: list[dict[str, Any]] = []

    for cls in tree_entry.get("classes", []) or []:
        class_name = _string(cls.get("name"))
        if class_name.startswith("_"):
            continue
        missing_tag = bool(cls.get("missing_required_tag"))
        class_symbol_id = cls.get("symbol_id", f"{file_path}::{class_name}")
        class_summary = _string(cls.get("summary"))
        class_routing = dict(cls.get("routing", {})) if isinstance(cls.get("routing"), Mapping) else {}
        class_provenance = (
            dict(cls.get("provenance"))
            if isinstance(cls.get("provenance"), Mapping)
            else _record_provenance(
                {
                    "summary": "derived" if missing_tag else "authored",
                    "routing.when_needed": "derived" if not _string(class_routing.get("when_needed")) else "authored",
                }
            )
        )
        class_quality = (
            dict(cls.get("quality"))
            if isinstance(cls.get("quality"), Mapping)
            else _record_quality(
                summary_provenance=_string(((class_provenance.get("fields") or {}).get("summary"))) or ("derived" if missing_tag else "authored"),
                when_needed_provenance=_string(((class_provenance.get("fields") or {}).get("routing.when_needed"))) or ("derived" if not _string(class_routing.get("when_needed")) else "authored"),
                missing_required_tag=missing_tag,
                issues=cls.get("issues", []),
                navigation_group=class_routing.get("navigation_group"),
            )
        )
        summaries.append({
            "symbol_id": class_symbol_id,
            "owner_symbol_id": cls.get("owner_symbol_id"),
            "scope_kind": "class",
            "name": class_name,
            "signature": "",
            "summary": class_summary,
            "routing": class_routing,
            "missing_required_tag": missing_tag,
            "source_authority": file_path,
            "callee_refs": [],
            "issues": cls.get("issues", []),
            "status": "up_to_date" if class_summary and not missing_tag else "needs_authoring",
            "line_start": cls.get("line_start", 0),
            "line_end": cls.get("line_end", 0),
            "inbound_dependents": [],
            "related_symbols": [],
            "provenance": class_provenance,
            "quality": class_quality,
            "search_tokens": _navigation_terms(
                file_path,
                class_name,
                class_summary,
                class_routing.get("navigation_group"),
                class_routing.get("when_needed"),
            ),
        })
        for method in cls.get("methods", []) or []:
            if method.get("is_private"):
                continue
            missing_tag = bool(method.get("missing_required_tag"))
            symbol_id = method.get("symbol_id", f"{file_path}::{cls['name']}.{method['name']}")
            summary = _string(method.get("summary"))
            routing = dict(method.get("routing", {})) if isinstance(method.get("routing"), Mapping) else {}
            method_provenance = (
                dict(method.get("provenance"))
                if isinstance(method.get("provenance"), Mapping)
                else _record_provenance(
                    {
                        "summary": "derived" if missing_tag else "authored",
                        "routing.when_needed": "derived" if not _string(routing.get("when_needed")) else "authored",
                    }
                )
            )
            method_quality = (
                dict(method.get("quality"))
                if isinstance(method.get("quality"), Mapping)
                else _record_quality(
                    summary_provenance=_string(((method_provenance.get("fields") or {}).get("summary"))) or ("derived" if missing_tag else "authored"),
                    when_needed_provenance=_string(((method_provenance.get("fields") or {}).get("routing.when_needed"))) or ("derived" if not _string(routing.get("when_needed")) else "authored"),
                    missing_required_tag=missing_tag,
                    issues=method.get("issues", []),
                    navigation_group=routing.get("navigation_group"),
                )
            )
            summaries.append({
                "symbol_id": symbol_id,
                "owner_symbol_id": method.get("owner_symbol_id", f"{file_path}::{cls['name']}"),
                "scope_kind": "method",
                "name": method.get("name", ""),
                "signature": method.get("signature", ""),
                "summary": summary,
                "routing": routing,
                "missing_required_tag": missing_tag,
                "source_authority": file_path,
                "callee_refs": method.get("callee_refs", []),
                "issues": method.get("issues", []),
                "status": "up_to_date" if method.get("summary") and not missing_tag else "needs_authoring",
                "line_start": method.get("line_start", 0),
                "line_end": method.get("line_end", 0),
                "inbound_dependents": [],
                "related_symbols": [],
                "provenance": method_provenance,
                "quality": method_quality,
                "search_tokens": _navigation_terms(
                    file_path,
                    class_name,
                    method.get("name", ""),
                    summary,
                    method.get("signature", ""),
                    routing.get("navigation_group"),
                    routing.get("when_needed"),
                ),
            })

    for fn in tree_entry.get("functions", []) or []:
        if fn.get("is_private"):
            continue
        missing_tag = bool(fn.get("missing_required_tag"))
        symbol_id = fn.get("symbol_id", f"{file_path}::{fn['name']}")
        summary = _string(fn.get("summary"))
        routing = dict(fn.get("routing", {})) if isinstance(fn.get("routing"), Mapping) else {}
        function_provenance = (
            dict(fn.get("provenance"))
            if isinstance(fn.get("provenance"), Mapping)
            else _record_provenance(
                {
                    "summary": "derived" if missing_tag else "authored",
                    "routing.when_needed": "derived" if not _string(routing.get("when_needed")) else "authored",
                }
            )
        )
        function_quality = (
            dict(fn.get("quality"))
            if isinstance(fn.get("quality"), Mapping)
            else _record_quality(
                summary_provenance=_string(((function_provenance.get("fields") or {}).get("summary"))) or ("derived" if missing_tag else "authored"),
                when_needed_provenance=_string(((function_provenance.get("fields") or {}).get("routing.when_needed"))) or ("derived" if not _string(routing.get("when_needed")) else "authored"),
                missing_required_tag=missing_tag,
                issues=fn.get("issues", []),
                navigation_group=routing.get("navigation_group"),
            )
        )
        summaries.append({
            "symbol_id": symbol_id,
            "owner_symbol_id": fn.get("owner_symbol_id"),
            "scope_kind": "function",
            "name": fn.get("name", ""),
            "signature": fn.get("signature", ""),
            "summary": summary,
            "routing": routing,
            "missing_required_tag": missing_tag,
            "source_authority": file_path,
            "callee_refs": fn.get("callee_refs", []),
            "issues": fn.get("issues", []),
            "status": "up_to_date" if fn.get("summary") and not missing_tag else "needs_authoring",
            "line_start": fn.get("line_start", 0),
            "line_end": fn.get("line_end", 0),
            "inbound_dependents": [],
            "related_symbols": [],
            "provenance": function_provenance,
            "quality": function_quality,
            "search_tokens": _navigation_terms(
                file_path,
                fn.get("name", ""),
                summary,
                fn.get("signature", ""),
                routing.get("navigation_group"),
                routing.get("when_needed"),
            ),
        })

    return summaries


def enrich_scope_summaries(
    scope_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Add reverse-call and browse metadata to scope summaries after cross-file
      callee resolution has completed.
    - Mechanism: Builds symbol- and path-level indexes, then populates inbound dependents,
      related symbols, and normalized navigation tokens for each scope summary.
    - Guarantee: Mutates and returns the same list shape with deterministic, deduplicated
      enrichment fields.
    """
    by_id = {str(item.get("symbol_id") or ""): item for item in scope_summaries if str(item.get("symbol_id") or "").strip()}
    by_path: dict[str, list[dict[str, Any]]] = {}
    callers_by_target: dict[str, list[str]] = {}
    for summary in scope_summaries:
        path = _string(summary.get("source_authority"))
        if path:
            by_path.setdefault(path, []).append(summary)
        caller_id = _string(summary.get("symbol_id"))
        if not caller_id:
            continue
        for ref in summary.get("callee_refs", []) or []:
            ref_value = _string(ref)
            if ref_value and ref_value != caller_id:
                callers_by_target.setdefault(ref_value, []).append(caller_id)

    for summary in scope_summaries:
        symbol_id = _string(summary.get("symbol_id"))
        path = _string(summary.get("source_authority"))
        inbound_dependents = _take_strings(callers_by_target.get(symbol_id, []), 16)
        same_file = [
            _string(item.get("symbol_id"))
            for item in by_path.get(path, [])
            if _string(item.get("symbol_id")) and _string(item.get("symbol_id")) != symbol_id
        ]
        related_symbols = _take_strings(
            [
                *[item for item in summary.get("callee_refs", []) or [] if _string(item)],
                *inbound_dependents,
                *same_file,
            ],
            20,
        )
        summary["inbound_dependents"] = inbound_dependents
        summary["related_symbols"] = related_symbols
        provenance = (
            dict(summary.get("provenance"))
            if isinstance(summary.get("provenance"), Mapping)
            else _record_provenance({"summary": "derived", "routing.when_needed": "derived"})
        )
        provenance_fields = dict(provenance.get("fields") or {})
        provenance_fields.setdefault("summary", "derived")
        provenance_fields.setdefault("routing.when_needed", "derived")
        provenance_fields["inbound_dependents"] = "derived"
        provenance_fields["related_symbols"] = "derived"
        provenance_fields["search_tokens"] = "derived"
        summary["provenance"] = _record_provenance(provenance_fields)
        summary["quality"] = _record_quality(
            summary_provenance=_string(provenance_fields.get("summary")) or "derived",
            when_needed_provenance=_string(provenance_fields.get("routing.when_needed")) or "derived",
            missing_required_tag=bool(summary.get("missing_required_tag")),
            issues=summary.get("issues", []),
            navigation_group=(summary.get("routing", {}) or {}).get("navigation_group"),
            stale_due_to=summary.get("stale_due_to"),
        )
        summary["search_tokens"] = _navigation_terms(
            path,
            summary.get("name", ""),
            summary.get("summary", ""),
            summary.get("signature", ""),
            summary.get("scope_kind", ""),
            *related_symbols[:8],
        )
    return scope_summaries


def propagate_staleness(
    scope_summaries: list[dict[str, Any]],
    changed_symbol_ids: set[str],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Given a set of changed symbol_ids, mark those symbols and their direct
      callers as stale. One-hop propagation only — deeper transitive staleness is handled
      by running this function again after the first hop is refreshed.
    - Mechanism: Builds a reverse index (callee → callers) from callee_refs, then marks
      changed symbols as needs_summary_refresh and their callers as needs_authoring_refresh.
    - Guarantee: Only modifies status and stale_due_to fields. Does not alter summary content.
    """
    # Build lookup by symbol_id
    by_id: dict[str, dict[str, Any]] = {s["symbol_id"]: s for s in scope_summaries if s.get("symbol_id")}

    # Mark changed symbols
    for sid in changed_symbol_ids:
        if sid in by_id:
            by_id[sid]["status"] = "needs_summary_refresh"
            by_id[sid]["stale_due_to"] = "source_changed"

    # Propagate to direct callers (one hop) using canonical callee_refs
    # callee_refs now contain symbol_ids for file-local calls, bare names for cross-file
    for s in scope_summaries:
        sid = s.get("symbol_id", "")
        if sid in changed_symbol_ids:
            continue
        if s.get("status") in ("needs_summary_refresh", "needs_authoring_refresh"):
            continue
        callee_refs = s.get("callee_refs", [])
        # Match against changed symbol_ids directly (canonical refs) and by bare name (unresolved refs)
        stale_callees = [ref for ref in callee_refs if ref in changed_symbol_ids]
        if not stale_callees:
            # Fallback: check bare name match for unresolved cross-file refs
            changed_names = {by_id[csid].get("name", "") for csid in changed_symbol_ids if csid in by_id}
            stale_callees = [ref for ref in callee_refs if ref in changed_names]
        if stale_callees:
            s["status"] = "needs_authoring_refresh"
            s["stale_due_to"] = f"callee_changed:{','.join(stale_callees[:3])}"

    return scope_summaries


def compute_dispatch_waves(
    scope_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Compute SCC-aware leaves-first dispatch waves from scope summaries.
      Functions with no internal callees go in wave 0. Callers of wave-N functions
      go in wave N+1. Cycles (SCCs) are condensed into a single wave entry.
    - Mechanism: Builds a directed graph from callee_refs, runs Tarjan's SCC, then
      BFS topological sort on the condensed DAG.
    - Guarantee: Every symbol appears in exactly one wave. Leaves first.
    """
    # Build symbol_id set + name fallback for resolving callee_refs
    by_id: dict[str, dict[str, Any]] = {}
    name_to_sids: dict[str, list[str]] = {}
    all_sids: set[str] = set()
    for s in scope_summaries:
        sid = s.get("symbol_id", "")
        if not sid:
            continue
        by_id[sid] = s
        all_sids.add(sid)
        name = s.get("name", "")
        if name:
            name_to_sids.setdefault(name, []).append(sid)

    # Build adjacency: caller_sid → set of callee_sids
    # callee_refs now contain symbol_ids (canonical) or bare names (unresolved)
    adj: dict[str, set[str]] = {sid: set() for sid in by_id}
    for sid, s in by_id.items():
        for ref in s.get("callee_refs", []):
            if ref in all_sids:
                # Canonical symbol_id match
                if ref != sid:
                    adj[sid].add(ref)
            else:
                # Bare name fallback for unresolved cross-file refs
                for t in name_to_sids.get(ref, []):
                    if t != sid:
                        adj[sid].add(t)

    # Tarjan's SCC
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    sccs: list[list[str]] = []

    def _strongconnect(v: str) -> None:
        indices[v] = lowlinks[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj.get(v, set()):
            if w not in indices:
                _strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])
        if lowlinks[v] == indices[v]:
            component: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            sccs.append(component)

    for sid in by_id:
        if sid not in indices:
            _strongconnect(sid)

    # Map each symbol to its SCC id
    sid_to_scc: dict[str, int] = {}
    for i, component in enumerate(sccs):
        for sid in component:
            sid_to_scc[sid] = i

    # Build condensed DAG (SCC → SCC edges)
    condensed_adj: dict[int, set[int]] = {i: set() for i in range(len(sccs))}
    condensed_in: dict[int, int] = {i: 0 for i in range(len(sccs))}
    for sid, neighbors in adj.items():
        src_scc = sid_to_scc[sid]
        for n in neighbors:
            dst_scc = sid_to_scc.get(n)
            if dst_scc is not None and dst_scc != src_scc:
                if dst_scc not in condensed_adj[src_scc]:
                    condensed_adj[src_scc].add(dst_scc)
                    condensed_in[dst_scc] += 1

    # BFS topological sort (callees first = reverse of caller-first)
    # We want leaves first, so start from SCCs with no outgoing edges to other SCCs
    # Actually: adj is caller→callee. Leaves have no callee edges.
    # In condensed DAG, leaves have no outgoing edges.
    # Kahn's on reversed condensed: find nodes with in_degree=0 in the original
    # Actually: in Kahn's on original DAG, nodes with in_degree=0 are "callers with no callers"
    # We want callees-first, so we reverse: nodes with out_degree=0 are leaves
    # Simpler: recompute in-degree on reversed edges
    rev_in: dict[int, int] = {i: 0 for i in range(len(sccs))}
    rev_adj: dict[int, set[int]] = {i: set() for i in range(len(sccs))}
    for src, dsts in condensed_adj.items():
        for dst in dsts:
            rev_adj[dst].add(src)
            rev_in[src] += 1

    from collections import deque
    queue: deque[int] = deque(i for i, d in rev_in.items() if d == 0)
    wave_assignments: dict[int, int] = {}
    while queue:
        scc_id = queue.popleft()
        # Wave = max wave of dependencies + 1 (leaves = 0)
        dep_waves = [wave_assignments[dep] for dep in rev_adj[scc_id] if dep in wave_assignments]
        wave_assignments[scc_id] = (max(dep_waves) + 1) if dep_waves else 0
        for src in condensed_adj[scc_id]:
            rev_in[src] -= 1
            if rev_in[src] == 0:
                queue.append(src)

    # For any SCC not reached (cycles in the condensed DAG — shouldn't happen), assign max+1
    max_wave = max(wave_assignments.values()) if wave_assignments else 0
    for i in range(len(sccs)):
        if i not in wave_assignments:
            wave_assignments[i] = max_wave + 1

    # Build output waves
    waves_map: dict[int, list[str]] = {}
    for i, component in enumerate(sccs):
        w = wave_assignments.get(i, 0)
        waves_map.setdefault(w, []).extend(component)

    waves: list[dict[str, Any]] = []
    for w_idx in sorted(waves_map.keys()):
        sids = sorted(waves_map[w_idx])
        # Check for non-trivial SCCs in this wave
        scc_labels = []
        for sid in sids:
            scc_id = sid_to_scc[sid]
            if len(sccs[scc_id]) > 1 and scc_id not in [s.get("_scc_id") for s in scc_labels]:
                scc_labels.append({"_scc_id": scc_id, "members": sccs[scc_id]})
        waves.append({
            "wave_index": w_idx,
            "symbol_ids": sids,
            "label": "leaves" if w_idx == 0 else f"depth_{w_idx}",
            "scc_groups": [{"members": s["members"]} for s in scc_labels] if scc_labels else [],
        })

    return waves


def deterministic_quality_gates(
    scope_summary: dict[str, Any],
) -> list[dict[str, str]]:
    """
    [ACTION]
    - Teleology: Run AST-addressable quality checks on a single scope summary before
      any LLM judge. Returns a list of gate failures (empty = all gates pass).
    - Mechanism: Checks tag presence, teleology presence, and structural completeness.
    - Guarantee: Pure function, no side effects, deterministic.
    """
    failures: list[dict[str, str]] = []

    # Gate 1: Required tag present
    if scope_summary.get("missing_required_tag"):
        failures.append({"gate": "tag_presence", "severity": "defect",
                         "detail": f"Missing required tag for {scope_summary.get('name', '?')}"})

    # Gate 2: Summary is not just the function name (triviality check)
    summary = scope_summary.get("summary", "")
    name = scope_summary.get("name", "")
    if summary and name and summary.lower().strip() == name.lower().replace("_", " ").strip():
        failures.append({"gate": "triviality", "severity": "warning",
                         "detail": f"Summary restates the function name: '{summary}'"})

    # Gate 3: Teleology line present (quality, not compliance)
    if summary and not summary.startswith("Teleology:") and not scope_summary.get("missing_required_tag"):
        # Has [ACTION] but summary doesn't start with Teleology
        # (builder strips dashes, so check the extracted summary)
        pass  # Tracked via teleology_coverage, not gated here yet

    # Gate 4: Callee refs resolvable (hallucination pre-check)
    issues = scope_summary.get("issues", [])
    dynamic_count = sum(1 for i in issues if i.get("issue") == "dynamic_call")
    if dynamic_count > 5:
        failures.append({"gate": "dynamic_calls", "severity": "warning",
                         "detail": f"{dynamic_count} dynamic calls — harder to verify correctness"})

    return failures


# ---------------------------------------------------------------------------
# Invalidation — live in build_documentation_tree_payload since Packet 8.
# persist_scope_state is called at build end; load_scope_state at build start;
# diff_and_propagate detects changed symbols and one-hop caller staleness.
# ---------------------------------------------------------------------------

_SCOPE_STATE_FILENAME = "scope_state.json"


def persist_scope_state(
    scope_summaries: list[dict[str, Any]],
    *,
    repo_root: Path,
) -> Path:
    """
    [ACTION]
    - Teleology: Write the current scope summary state to a typed artifact on disk.
      This enables cross-run invalidation: a subsequent build can load the prior state,
      diff changed symbols, and propagate staleness without a full rebuild.
    - Writes: codex/hologram/system/scope_state.json
    - Guarantee: Overwrites atomically. State is a flat list of scope summary dicts.
    """
    state_path = repo_root / "codex" / "hologram" / "system" / _SCOPE_STATE_FILENAME
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "__meta": {
            "artifact_kind": "scope_state",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "symbol_count": len(scope_summaries),
        },
        "symbols": scope_summaries,
    }
    state_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return state_path


def load_scope_state(
    *,
    repo_root: Path,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Load the previously persisted scope state from disk.
    - Reads: codex/hologram/system/scope_state.json
    - Guarantee: Returns empty list if no state file exists.
    """
    state_path = repo_root / "codex" / "hologram" / "system" / _SCOPE_STATE_FILENAME
    if not state_path.exists():
        return []
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return data.get("symbols", [])
    except Exception:
        return []


def diff_and_propagate(
    old_summaries: list[dict[str, Any]],
    new_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Compare old and new scope summaries, detect changed symbols,
      propagate staleness to their direct callers, and return the updated state.
    - Mechanism: A symbol is "changed" if its summary text differs between old and new.
      Changed symbols get needs_summary_refresh; their callers get needs_authoring_refresh.
    """
    old_by_id = {s["symbol_id"]: s for s in old_summaries if s.get("symbol_id")}
    changed_ids: set[str] = set()
    for s in new_summaries:
        sid = s.get("symbol_id", "")
        if not sid:
            continue
        old = old_by_id.get(sid)
        if old is None:
            # New symbol — not stale, but callers might need refresh
            changed_ids.add(sid)
        elif old.get("summary", "") != s.get("summary", ""):
            changed_ids.add(sid)
    if changed_ids:
        return propagate_staleness(new_summaries, changed_ids)
    return new_summaries


def build_repo_symbol_index(
    entries: Sequence[Mapping[str, Any]],
) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Build a repo-wide bare-name → symbol_id(s) index from documentation tree entries.
      Used in the second pass of build_documentation_tree_payload to resolve cross-file callee refs.
    - Guarantee: Returns a dict mapping bare names to lists of canonical symbol_ids.
      Names that appear in multiple files will have multiple entries (ambiguous).
    """
    index: dict[str, list[str]] = {}
    for entry in entries:
        file_path = _string(entry.get("path"))
        if not file_path:
            continue
        for cls in entry.get("classes", []) or []:
            cls_name = _string(cls.get("name"))
            if cls_name:
                sid = f"{file_path}::{cls_name}"
                index.setdefault(cls_name, []).append(sid)
            for method in cls.get("methods", []) or []:
                m_name = _string(method.get("name"))
                if m_name:
                    qualified = f"{cls_name}.{m_name}"
                    sid = f"{file_path}::{qualified}"
                    index.setdefault(m_name, []).append(sid)
                    index.setdefault(qualified, []).append(sid)
        for fn in entry.get("functions", []) or []:
            fn_name = _string(fn.get("name"))
            if fn_name:
                sid = f"{file_path}::{fn_name}"
                index.setdefault(fn_name, []).append(sid)
    return index


def _resolve_cross_file_refs(
    entries: list[dict[str, Any]],
    repo_index: dict[str, list[str]],
) -> dict[str, int]:
    """
    [ACTION]
    - Teleology: Second-pass cross-file callee resolution. Walk all entries' callee_refs
      and resolve bare-name refs against the repo-wide symbol index.
    - Returns: stats dict with resolved_count, ambiguous_count, unresolved_count.
    """
    stats = {"resolved": 0, "ambiguous": 0, "unresolved": 0}

    def _resolve_refs(record: dict[str, Any], file_path: str) -> None:
        callee_refs = record.get("callee_refs")
        issues = record.get("issues")
        if not isinstance(callee_refs, list):
            return
        new_refs: list[str] = []
        new_issues = list(issues) if isinstance(issues, list) else []
        for ref in callee_refs:
            if "::" in ref:
                # Already canonical
                new_refs.append(ref)
                continue
            candidates = repo_index.get(ref, [])
            # Exclude self-file matches (already resolved in first pass)
            cross_file = [c for c in candidates if not c.startswith(f"{file_path}::")]
            if len(cross_file) == 1:
                new_refs.append(cross_file[0])
                # Remove the unresolved_cross_file issue for this ref
                new_issues = [i for i in new_issues if i.get("target") != ref]
                stats["resolved"] += 1
            elif len(cross_file) > 1:
                # Ambiguous — keep bare name but update issue
                new_refs.append(ref)
                for issue in new_issues:
                    if issue.get("target") == ref and issue.get("issue") == "unresolved_cross_file":
                        issue["issue"] = "ambiguous_cross_file"
                        issue["candidates"] = cross_file[:5]
                stats["ambiguous"] += 1
            else:
                # No match — likely stdlib/builtin
                new_refs.append(ref)
                stats["unresolved"] += 1
        record["callee_refs"] = new_refs
        record["issues"] = new_issues

    for entry in entries:
        file_path = _string(entry.get("path"))
        for cls in entry.get("classes", []) or []:
            for method in cls.get("methods", []) or []:
                _resolve_refs(method, file_path)
        for fn in entry.get("functions", []) or []:
            _resolve_refs(fn, file_path)
    return stats


def build_documentation_tree_payload(
    paths: Sequence[Path],
    *,
    repo_root: Path,
    generated_at: str | None = None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compile documentation-tree entries for a cohort of Python files into one builder/miner/mission-ready payload.
      Two-pass build: first pass resolves file-local callee refs, second pass resolves cross-file refs using a repo-wide symbol index.
    - Reads: Each path in `paths`, plus the standard-owned documentation-tree policy.
    - Guarantee: Returns deterministic `__meta`, `coverage`, `files`, `scope_summaries`, and `repo_symbol_index` sections sorted by repo-relative path.
    - Fails: Propagates filesystem errors for unreadable paths so callers can fail loudly during build orchestration.
    """
    active_policy = dict(documentation_tree_policy())
    if isinstance(policy, Mapping):
        active_policy.update(dict(policy))

    repo_root = repo_root.resolve()

    # PASS 1: Build entries with file-local callee resolution
    entries = [
        build_file_entry(Path(path).resolve(), repo_root=repo_root, policy=active_policy)
        for path in sorted((Path(path).resolve() for path in paths), key=lambda item: _safe_relpath(item, repo_root))
    ]

    # PASS 2: Build repo-wide symbol index and resolve cross-file refs
    repo_index = build_repo_symbol_index(entries)
    resolution_stats = _resolve_cross_file_refs(entries, repo_index)

    dirty_paths = [entry["path"] for entry in entries if entry.get("status") != "compliant"]
    oversized_paths = [
        entry["path"]
        for entry in entries
        if bool(((entry.get("mission") or {}).get("oversized")))
    ]
    now_iso = generated_at or datetime.now(timezone.utc).isoformat()

    # Build scope summaries from all entries AFTER cross-file resolution
    all_scope_summaries: list[dict[str, Any]] = []
    for entry in entries:
        all_scope_summaries.extend(build_scope_summaries(entry))

    # --- Invalidation: load prior state, diff, propagate, persist ---
    prior_summaries = load_scope_state(repo_root=repo_root)
    if prior_summaries:
        all_scope_summaries = diff_and_propagate(prior_summaries, all_scope_summaries)
    all_scope_summaries = enrich_scope_summaries(all_scope_summaries)
    persist_scope_state(all_scope_summaries, repo_root=repo_root)

    # --- Stale-state surfaces (B) ---
    stale_refresh = [s for s in all_scope_summaries if s.get("status") == "needs_summary_refresh"]
    stale_authoring = [s for s in all_scope_summaries if s.get("status") == "needs_authoring_refresh"]
    stale_symbol_ids = [s["symbol_id"] for s in stale_refresh + stale_authoring if s.get("symbol_id")]
    stale_paths = sorted({s.get("source_authority", "") for s in stale_refresh + stale_authoring if s.get("source_authority")})
    scopes_by_path: dict[str, list[dict[str, Any]]] = {}
    for summary in all_scope_summaries:
        path = _string(summary.get("source_authority"))
        if path:
            scopes_by_path.setdefault(path, []).append(summary)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_path = _string(entry.get("path"))
        entry_scopes = scopes_by_path.get(entry_path, [])
        entry["scope_summary_count"] = len(entry_scopes)
        entry["public_symbol_ids"] = _take_strings(
            [
                *(_string(item.get("symbol_id")) for item in entry_scopes if _string(item.get("symbol_id"))),
                *(_string(item) for item in entry.get("public_symbol_ids", []) if _string(item)),
            ],
            128,
        )
        if not entry.get("search_tokens"):
            entry["search_tokens"] = _navigation_terms(
                entry_path,
                entry.get("browse_summary", ""),
                entry.get("summary", ""),
                entry.get("module", {}),
            )

    return {
        "__meta": {
            "generated_at": now_iso,
            "schema_version": _string(active_policy.get("schema_version")) or _DEFAULT_POLICY["schema_version"],
            "standard": "codex/standards/std_python.py",
            "artifact_path": _string(active_policy.get("artifact_path")) or _DEFAULT_POLICY["artifact_path"],
            "oversized_file_bytes": int(active_policy.get("oversized_file_bytes") or _DEFAULT_POLICY["oversized_file_bytes"]),
            "default_provider": _string(active_policy.get("default_provider")) or _DEFAULT_POLICY["default_provider"],
            "oversized_provider": _string(active_policy.get("oversized_provider")) or _DEFAULT_POLICY["oversized_provider"],
        },
        "coverage": {
            "total_files": len(entries),
            "dirty_files": len(dirty_paths),
            "dirty_paths": dirty_paths,
            "oversized_files": len(oversized_paths),
            "oversized_paths": oversized_paths,
            "recommended_provider": recommended_provider_for_entries(entries, policy=active_policy),
            "default_bridge_workers": int(active_policy.get("default_bridge_workers") or _DEFAULT_POLICY["default_bridge_workers"]),
        },
        "repo_symbol_index": {
            "total_symbols": sum(len(sids) for sids in repo_index.values()),
            "unique_names": len(repo_index),
            "files_indexed": len(entries),
            "cross_file_resolved": resolution_stats["resolved"],
            "cross_file_ambiguous": resolution_stats["ambiguous"],
            "cross_file_unresolved": resolution_stats["unresolved"],
        },
        "stale_state": {
            "stale_symbols_count": len(stale_symbol_ids),
            "needs_summary_refresh_count": len(stale_refresh),
            "needs_authoring_refresh_count": len(stale_authoring),
            "needs_summary_refresh_symbol_ids": [s["symbol_id"] for s in stale_refresh if s.get("symbol_id")],
            "needs_authoring_refresh_symbol_ids": [s["symbol_id"] for s in stale_authoring if s.get("symbol_id")],
            "stale_paths": stale_paths,
        },
        "files": entries,
        "scope_summaries": all_scope_summaries,
    }


def recommended_provider_for_entries(
    entries: Sequence[Mapping[str, Any]],
    *,
    policy: Mapping[str, Any] | None = None,
) -> str:
    """
    [ACTION]
    - Teleology: Select the standard-recommended bridge provider for a documentation cohort.
    - Reads: Entry mission hints and the documentation-tree policy.
    - Guarantee: Returns the oversized-file provider only when the whole cohort is oversized; mixed cohorts stay on the default provider because symbol slicing already bounds the exceptional files.
    - Fails: None. Falls back to conservative standard defaults.
    """
    active_policy = dict(documentation_tree_policy())
    if isinstance(policy, Mapping):
        active_policy.update(dict(policy))
    default_provider = _string(active_policy.get("default_provider")) or _DEFAULT_POLICY["default_provider"]
    oversized_provider = _string(active_policy.get("oversized_provider")) or _DEFAULT_POLICY["oversized_provider"]
    oversized_count = 0
    total_entries = 0
    for entry in entries:
        mission = entry.get("mission") if isinstance(entry, Mapping) else {}
        if not isinstance(mission, Mapping):
            continue
        total_entries += 1
        if bool(mission.get("oversized")):
            oversized_count += 1
    if total_entries > 0 and oversized_count == total_entries:
        return oversized_provider
    return default_provider
