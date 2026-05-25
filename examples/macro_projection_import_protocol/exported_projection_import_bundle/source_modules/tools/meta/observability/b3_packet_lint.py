#!/usr/bin/env python3
"""Lint B3 Compact PACKET v=3.2 outputs.

This checks generated B3 packets, not the prompt body itself. The prompt-shelf
prompt lint verifies B3 is mirrored and footer-free; this linter verifies that a
packet emitted by B3 keeps the parser-coupled grammar, evidence, and section-role
discipline needed for restartability.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_VERSION = "b3_packet_lint_v0"
PACKET_START = "PACKET v=3.2"
PACKET_END = "END_PACKET"

TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "thread",
    "scope",
    "last_valid_state_per_source",
    "hot_path",
    "state_capsule",
    "produced_artifacts",
    "operator_intent_signals",
    "decision_axes",
    "source_stated_proposals",
    "affordance_surface",
    "surface_topology",
    "change_envelope",
    "behavioral_arcs",
    "proof_boundary",
    "native_compaction_relation",
    "edit_anchors",
    "decided",
    "done_major",
    "validation_matrix",
    "done_inspection",
    "authority_map",
    "workspace_state",
    "stated_open",
    "stated_blocked",
    "stated_risks",
    "stated_contradictions",
    "stated_freshness_or_staleness",
    "stated_postures",
    "verbatim_quotes",
    "facts_added",
    "evidence_pointers",
    "omitted",
)

HOT_PATH_FIELDS: tuple[str, ...] = (
    "terminal_state",
    "produced_artifacts",
    "active_decision_axes",
    "primary_affordance_surfaces",
    "validation_boundary",
    "workspace_boundary",
    "residuals",
)

FORBIDDEN_FIELD_RE = re.compile(
    r"^\s*(?:next_move|continuation_prompt|ask_type_a|verify_before_trusting|"
    r"availability_ladder_receipt|mission_evolution_signal|bridge_research_gaps|"
    r"recommended_[A-Za-z0-9_]+|look_around_[A-Za-z0-9_]+|deliverable_type|"
    r"depth_floor|authority_boundary|integration_target)\s*:",
)
EMPTY_EVIDENCE_RE = re.compile(r"\bevidence=\s*(?:$|::|;)")
PLACEHOLDER_EVIDENCE_RE = re.compile(r"\bevidence=<[^>]+>")
SOURCE_RE = re.compile(r"\bsource=([^:]+?)(?:\s*::|$)")
STATUS_RE = re.compile(r"\bstatus=([^:]+?)(?:\s*::|$)")

SENTINEL_FIELD_BY_SECTION: dict[str, str] = {
    "produced_artifacts": "artifact_type",
    "operator_intent_signals": "signal",
    "decision_axes": "axis",
    "source_stated_proposals": "proposal",
    "affordance_surface": "surface",
    "surface_topology": "surface",
    "change_envelope": "proposed_change",
    "behavioral_arcs": "problem",
    "proof_boundary": "proof",
    "native_compaction_relation": "provider",
    "edit_anchors": "path",
    "decided": "decision",
    "done_major": "ref",
    "validation_matrix": "evidence",
    "done_inspection": "result",
    "authority_map": "authority",
    "stated_open": "open",
    "stated_blocked": "blocked",
    "stated_risks": "risk",
    "stated_contradictions": "source_a",
    "stated_freshness_or_staleness": "freshness_note",
    "stated_postures": "posture",
    "facts_added": "fact",
    "evidence_pointers": "claim",
    "omitted": "topic",
}


@dataclass(frozen=True)
class Issue:
    code: str
    line: int | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"code": self.code}
        if self.line is not None:
            out["line"] = self.line
        if self.detail:
            out["detail"] = self.detail
        return out


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _nonempty_line_indices(lines: list[str]) -> list[int]:
    return [idx for idx, line in enumerate(lines) if line.strip()]


def _quote_mask(lines: list[str]) -> list[bool]:
    """Return True for lines inside triple-quote verbatim bodies."""
    mask: list[bool] = []
    in_quote = False
    for line in lines:
        mask.append(in_quote)
        if line.count('"""') % 2 == 1:
            in_quote = not in_quote
    return mask


def _section_positions(lines: list[str]) -> dict[str, int]:
    positions: dict[str, int] = {}
    for idx, line in enumerate(lines):
        for field in TOP_LEVEL_FIELDS:
            if field not in positions and line.startswith(f"{field}:"):
                positions[field] = idx
    return positions


def _section_lines(lines: list[str], positions: dict[str, int], section: str) -> list[tuple[int, str]]:
    start = positions.get(section)
    if start is None:
        return []
    later = [
        idx for key, idx in positions.items()
        if key != section and idx > start
    ]
    end = min(later) if later else len(lines)
    return [(idx, lines[idx]) for idx in range(start + 1, end)]


def _issue(code: str, line: int | None = None, detail: str = "") -> Issue:
    return Issue(code=code, line=(line + 1 if line is not None else None), detail=detail)


def lint_packet_text(text: str, *, name: str = "<memory>") -> dict[str, object]:
    lines = text.splitlines()
    issues: list[Issue] = []
    nonempty = _nonempty_line_indices(lines)

    if not nonempty:
        issues.append(_issue("empty_packet"))
        return _report(name, lines, issues, {})

    first = nonempty[0]
    last = nonempty[-1]
    if lines[first].strip() != PACKET_START:
        issues.append(_issue("packet_start_not_v3_2", first, lines[first].strip()))
    elif lines[first] != PACKET_START:
        issues.append(_issue("packet_start_not_column_1", first, lines[first]))
    if lines[last].strip() != PACKET_END:
        issues.append(_issue("packet_end_missing", last, lines[last].strip()))
    elif lines[last] != PACKET_END:
        issues.append(_issue("packet_end_not_column_1", last, lines[last]))

    start_indices = [idx for idx, line in enumerate(lines) if line.strip() == PACKET_START]
    end_indices = [idx for idx, line in enumerate(lines) if line.strip() == PACKET_END]
    if len(start_indices) != 1:
        issues.append(_issue("packet_start_count_invalid", detail=str(len(start_indices))))
    if len(end_indices) != 1:
        issues.append(_issue("packet_end_count_invalid", detail=str(len(end_indices))))
    for idx in start_indices:
        if idx != first and lines[idx] != PACKET_START:
            issues.append(_issue("packet_start_not_column_1", idx, lines[idx]))
    for idx in end_indices:
        if idx != last and lines[idx] != PACKET_END:
            issues.append(_issue("packet_end_not_column_1", idx, lines[idx]))
    if start_indices and end_indices:
        start = start_indices[0]
        end = end_indices[-1]
        for idx in range(0, start):
            if lines[idx].strip():
                issues.append(_issue("prose_before_packet", idx, lines[idx].strip()[:120]))
        for idx in range(end + 1, len(lines)):
            if lines[idx].strip():
                issues.append(_issue("prose_after_packet", idx, lines[idx].strip()[:120]))

    positions = _section_positions(lines)
    missing = [field for field in TOP_LEVEL_FIELDS if field not in positions]
    for field in missing:
        issues.append(_issue("required_field_missing", detail=field))

    last_seen = -1
    for field in TOP_LEVEL_FIELDS:
        pos = positions.get(field)
        if pos is None:
            continue
        if pos < last_seen:
            issues.append(_issue("field_order_invalid", pos, field))
        last_seen = pos

    quote_mask = _quote_mask(lines)
    for idx, line in enumerate(lines):
        if quote_mask[idx]:
            continue
        if re.match(r"^\s*\* ", line):
            issues.append(_issue("invalid_star_list_marker", idx, line.strip()[:120]))
        if FORBIDDEN_FIELD_RE.match(line):
            issues.append(_issue("forbidden_field", idx, line.strip()[:120]))
        if EMPTY_EVIDENCE_RE.search(line):
            issues.append(_issue("empty_evidence_value", idx, line.strip()[:120]))
        if PLACEHOLDER_EVIDENCE_RE.search(line):
            issues.append(_issue("placeholder_evidence_value", idx, line.strip()[:120]))

    issues.extend(_lint_hot_path(lines, positions))
    issues.extend(_lint_evidence_pointers(lines, positions))
    issues.extend(_lint_operator_intent(lines, positions))
    issues.extend(_lint_source_stated_proposals(lines, positions))
    issues.extend(_lint_sentinel_rows(lines, positions))
    issues.extend(_lint_state_capsule_consistency(lines, positions))
    issues.extend(_lint_authority_projection(lines, positions, text))
    return _report(name, lines, issues, positions)


def _lint_hot_path(lines: list[str], positions: dict[str, int]) -> list[Issue]:
    issues: list[Issue] = []
    section = _section_lines(lines, positions, "hot_path")
    by_field: dict[str, tuple[int, str]] = {}
    for idx, line in section:
        unindented = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if unindented and unindented.group(1) in HOT_PATH_FIELDS:
            issues.append(_issue("hot_path_field_unindented", idx, unindented.group(1)))
            continue
        match = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*(.*)$", line)
        if match:
            by_field[match.group(1)] = (idx, match.group(2).strip())
    for field in HOT_PATH_FIELDS:
        row = by_field.get(field)
        if row is None:
            issues.append(_issue("hot_path_field_missing", detail=field))
            continue
        idx, value = row
        if not value:
            issues.append(_issue("hot_path_field_empty", idx, field))
        if len(value) > 800:
            issues.append(_issue("hot_path_field_overlong", idx, field))
    return issues


def _lint_evidence_pointers(lines: list[str], positions: dict[str, int]) -> list[Issue]:
    issues: list[Issue] = []
    for idx, line in _section_lines(lines, positions, "evidence_pointers"):
        stripped = line.strip()
        if not stripped or stripped in {"[]", "none"}:
            continue
        if not stripped.startswith("- "):
            continue
        if "claim=" not in stripped:
            issues.append(_issue("evidence_pointer_missing_claim", idx, stripped[:120]))
        if "evidence=" not in stripped:
            issues.append(_issue("evidence_pointer_missing_evidence", idx, stripped[:120]))
    return issues


def _lint_operator_intent(lines: list[str], positions: dict[str, int]) -> list[Issue]:
    issues: list[Issue] = []
    for idx, line in _section_lines(lines, positions, "operator_intent_signals"):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        source = SOURCE_RE.search(stripped)
        if source is None:
            issues.append(_issue("operator_intent_missing_source", idx, stripped[:120]))
            continue
        if "operator" not in source.group(1).lower():
            issues.append(_issue("operator_intent_source_not_operator", idx, source.group(1).strip()))
    return issues


def _lint_source_stated_proposals(lines: list[str], positions: dict[str, int]) -> list[Issue]:
    issues: list[Issue] = []
    for idx, line in _section_lines(lines, positions, "source_stated_proposals"):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        status = STATUS_RE.search(stripped)
        status_value = status.group(1).strip().lower() if status else ""
        if status_value == "not_stated":
            issues.append(_issue("source_stated_proposal_status_not_stated", idx, stripped[:120]))
        menu_like = bool(re.search(r"\b(?:NEXT|menu|recommended)\b", stripped, re.IGNORECASE))
        if menu_like and status_value not in {
            "accepted",
            "rejected",
            "pending_answers",
            "default",
            "proposed",
            "intended",
            "source_menu",
        }:
            issues.append(_issue("tool_menu_proposal_status_unclear", idx, stripped[:120]))
    return issues


def _primary_field_value(stripped: str, field: str) -> str | None:
    match = re.search(rf"\b{re.escape(field)}=([^:]+?)(?:\s*::|$)", stripped)
    if match:
        return match.group(1).strip().lower()
    if field == "decision":
        body = stripped[2:].strip() if stripped.startswith("- ") else stripped
        before_sep = body.split("::", 1)[0].strip().lower()
        return before_sep or None
    if field in {"open", "blocked", "risk", "posture", "fact"}:
        body = stripped[2:].strip() if stripped.startswith("- ") else stripped
        before_sep = body.split("::", 1)[0].strip().lower()
        return before_sep or None
    return None


def _lint_sentinel_rows(lines: list[str], positions: dict[str, int]) -> list[Issue]:
    issues: list[Issue] = []
    sentinel_values = {"none", "not_stated", "[]", "(none)", "_(none)_"}
    for section, primary_field in SENTINEL_FIELD_BY_SECTION.items():
        for idx, line in _section_lines(lines, positions, section):
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            lower = stripped.lower()
            primary = _primary_field_value(stripped, primary_field)
            primary_is_empty = primary in sentinel_values
            source_is_empty = "source=not_stated" in lower
            payload_is_empty = any(
                token in lower for token in (
                    "preserved_as=not_stated",
                    "status=not_stated",
                    "result=not_stated",
                    "evidence=not_stated",
                )
            )
            if primary_is_empty and (source_is_empty or payload_is_empty):
                issues.append(_issue("sentinel_empty_row", idx, f"{section}.{primary_field}"))
    return issues


def _lint_state_capsule_consistency(lines: list[str], positions: dict[str, int]) -> list[Issue]:
    issues: list[Issue] = []
    section = _section_lines(lines, positions, "state_capsule")
    pushed_unknown: int | None = None
    explicit_push_not_stated = False
    for idx, line in section:
        stripped = line.strip().lower()
        if stripped == "pushed: unknown":
            pushed_unknown = idx
        if stripped.startswith("explicit_not_done:") and "push not stated" in stripped:
            explicit_push_not_stated = True
    if pushed_unknown is not None and explicit_push_not_stated:
        issues.append(_issue("pushed_unknown_conflicts_with_push_not_stated", pushed_unknown))
    return issues


def _lint_authority_projection(lines: list[str], positions: dict[str, int], text: str) -> list[Issue]:
    meaningful_text = "\n".join(
        line for line in lines
        if not re.match(r"^\s*[A-Za-z0-9_]+:\s*(?:\[|none|not_stated)?\s*$", line)
    )
    if not re.search(r"\bauthority\b", meaningful_text, re.IGNORECASE):
        return []
    if not re.search(
        r"\bprojection\b|\blive runtime\b|\bLaunchAgent\b|\bCDP\b|\bclipboard\b",
        meaningful_text,
        re.IGNORECASE,
    ):
        return []
    section = [
        line.strip()
        for _idx, line in _section_lines(lines, positions, "authority_map")
        if line.strip()
    ]
    if not section or section == ["[]"] or section == ["none"]:
        return [_issue("authority_projection_boundary_missing", positions.get("authority_map"))]
    return []


def _report(
    name: str,
    lines: list[str],
    issues: list[Issue],
    positions: dict[str, int],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "line_count": len(lines),
        "packet_version": PACKET_START if any(line.strip() == PACKET_START for line in lines) else "unknown",
        "field_count": len(positions),
        "issue_count": len(issues),
        "issues": [issue.to_dict() for issue in issues],
    }


def lint_packet_path(path: Path) -> dict[str, object]:
    text = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    return lint_packet_text(text, name="stdin" if str(path) == "-" else _display_path(path))


def build_report(paths: Iterable[Path]) -> dict[str, object]:
    packets = [lint_packet_path(path) for path in paths]
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_count": len(packets),
        "issue_count": sum(int(packet["issue_count"]) for packet in packets),
        "packets": packets,
    }


def render_report(report: dict[str, object]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("paths", nargs="+", help="B3 packet text files, or - for stdin")
    parser.add_argument("--print", action="store_true", help="emit JSON report")
    parser.add_argument("--check", action="store_true", help="exit non-zero on lint issues")
    args = parser.parse_args()

    if not args.print and not args.check:
        parser.error("pick --print or --check")
    report = build_report(Path(path) for path in args.paths)
    if args.print:
        sys.stdout.write(render_report(report))
    if args.check:
        if int(report["issue_count"]):
            for packet in report["packets"]:
                for issue in packet["issues"]:
                    line = f":{issue['line']}" if "line" in issue else ""
                    detail = f" {issue['detail']}" if issue.get("detail") else ""
                    print(f"{packet['name']}{line}: {issue['code']}{detail}")
            return 1
        print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
