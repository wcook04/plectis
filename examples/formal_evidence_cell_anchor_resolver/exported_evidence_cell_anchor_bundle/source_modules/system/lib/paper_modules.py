"""
[PURPOSE]
- Teleology: Centralize paper-module parsing, validation, projection, freshness,
  and browse rendering so every consumer reads the same ontology contract.
- Mechanism: Parse authored markdown modules, validate them against
  `codex/standards/std_paper_module.json`, compute the depends_on DAG and queue
  semantics, render the generated browse projection for README, and compare the
  expected generated surfaces against what is currently on disk.

[INTERFACE]
- Exports: load_standard, load_candidates, load_index_modules_by_slug,
  parse_paper_module_header, build_outputs, load_paper_module_runtime,
  render_readme_projection, replace_marked_region, extract_marked_region.
- Inputs: Repo root, paper modules directory, candidates backlog, standard, and
  optional existing generated surfaces for freshness comparison.
- Outputs: Generated `_index.json`, `_validation_report.json`,
  `_doctrine_to_paper_modules.json`, `_route_coverage.json`, README managed
  projection content, plus runtime freshness metadata for in-process consumers.

[CONSTRAINTS]
- Markdown paper modules remain the authored source of truth.
- `_index.json` and `_validation_report.json` remain generated projections.
- `_rediscovery_findings.json` is intentionally not owned here; it is secondary
  evidence emitted by `tools/meta/factory/rediscovery_miner.py`.

Rosetta routing header (std_navigation_rosetta_grammar.json::noun_shape):
  kind: python_module
  role: paper-module ontology runtime; parses authored markdown modules, validates them against std_paper_module.json, computes the depends_on DAG, renders the README browse projection, and emits the generated _index / _validation_report / _doctrine_to_paper_modules / _route_coverage projections that every other surface (kind atlas, option surface, rosetta packet, frontend lens) consumes.
  depends_on:
    - codex/standards/std_paper_module.json: governs - schema_version, required_sections, depends_on contract, status_enum, freshness rules, validation rules; this module enforces them at parse / build time.
    - codex/doctrine/paper_modules/*.md: feeds - authored markdown is the source of truth; this module reads but never mutates author-owned bodies.
    - codex/doctrine/paper_modules/paper_module_candidates.json: feeds - the typed under-projection backlog flows into _validation_report.json::first_author_queue.
    - codex/doctrine/paper_modules/_index.json: populates - the generated ontology projection; THIS module is the sole writer.
    - codex/doctrine/paper_modules/_validation_report.json: populates - the generated freshness / refresh_queue / split_queue / first_author_queue projection; THIS module is the sole writer.
    - codex/doctrine/paper_modules/README.md: populates - the managed-region browse rendering; replace_marked_region / extract_marked_region preserve the surrounding handcrafted prose.
    - tools/meta/factory/build_paper_module_index.py: routes_to - the CLI builder is the entry point that calls this module.
    - system/lib/derived_fact_hologram.py: feeds - markdown fact-claim audit feeds the paper-module validation pipeline (audit_markdown_fact_claims).
    - system/lib/standard_option_surface.py: routes_to - the rung-1 paper-module option-surface emitter consumes the projections written here.
  governed_by:
    - codex/standards/std_paper_module.json
  code_loci:
    - load_standard: load std_paper_module.json (the schema authority).
    - load_candidates: load paper_module_candidates.json (the under-projection backlog).
    - load_index_modules_by_slug: indexed access into _index.json by slug.
    - parse_paper_module_header: strict frontmatter parser; rejects malformed frontmatter rather than tolerating drift.
    - build_outputs: top-level build entrypoint; emits the four generated projections + README managed region in one pass.
    - load_paper_module_runtime: in-process consumer entry; returns runtime freshness metadata.
    - render_readme_projection: renders the README browse projection.
    - replace_marked_region / extract_marked_region: managed-region helpers (preserve surrounding handcrafted prose).
  evidence_command: ./repo-python tools/meta/factory/build_paper_module_index.py --check --report (validate without writing); ./repo-python kernel.py --paper-module "<query>" (read one module's TLDR-first packet).
  source_authority: codex/standards/std_paper_module.json for the schema; codex/doctrine/paper_modules/*.md for authored bodies; this module owns the generated projection contract only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from system.lib.derived_fact_hologram import (
    AUDIT_PATH as FACT_AUDIT_PATH,
    LEDGER_PATH as FACT_LEDGER_PATH,
    NAVIGATION_CACHE_PATH as FACT_NAVIGATION_CACHE_PATH,
    audit_markdown_fact_claims,
    build_fact_hologram,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_paper_module.json"
PAPER_MODULES_DIR = REPO_ROOT / "codex" / "doctrine" / "paper_modules"
INDEX_PATH = PAPER_MODULES_DIR / "_index.json"
REPORT_PATH = PAPER_MODULES_DIR / "_validation_report.json"
DOCTRINE_TO_PAPER_MODULES_PATH = PAPER_MODULES_DIR / "_doctrine_to_paper_modules.json"
PAPER_MODULE_ROUTE_COVERAGE_PATH = PAPER_MODULES_DIR / "_route_coverage.json"
CANDIDATES_PATH = PAPER_MODULES_DIR / "paper_module_candidates.json"
README_PATH = PAPER_MODULES_DIR / "README.md"
BUILDER_GENERATED_SURFACE_PATHS = {
    "AGENTS.md",
    "CLAUDE.md",
    "CODEX.md",
    "codex/doctrine/agent_bootstrap_live.json",
    "codex/doctrine/agent_bootstrap_injection_strip.json",
    "codex/doctrine/routing_hologram.json",
    "codex/doctrine/skills/skill_map.md",
    str(INDEX_PATH.relative_to(REPO_ROOT)),
    str(REPORT_PATH.relative_to(REPO_ROOT)),
    str(DOCTRINE_TO_PAPER_MODULES_PATH.relative_to(REPO_ROOT)),
    str(PAPER_MODULE_ROUTE_COVERAGE_PATH.relative_to(REPO_ROOT)),
    str(README_PATH.relative_to(REPO_ROOT)),
    str(PAPER_MODULES_DIR.relative_to(REPO_ROOT)),
    "annexes/annex_catalog.json",
    "annexes/annex_distillation_index.json",
    str(FACT_LEDGER_PATH.relative_to(REPO_ROOT)),
    str(FACT_AUDIT_PATH.relative_to(REPO_ROOT)),
    str(FACT_NAVIGATION_CACHE_PATH.relative_to(REPO_ROOT)),
    "docs/annex_registry.md",
    "codex/standards/std_python_scope_index.json",
    "tools/meta/bridge/claude_active_session.json",
    "tools/meta/control/orchestration_brief.json",
    "tools/meta/control/orchestration_brief.md",
    "tools/meta/control/orchestration_events.jsonl",
    "tools/meta/control/orchestration_state.json",
}
BUILDER_GENERATED_SURFACE_PREFIXES = (
    f"{PAPER_MODULES_DIR.relative_to(REPO_ROOT)}/",
    "codex/derived/",
    "codex/hologram/system/",
    "codex/hologram/facts/",
    "raw/",
    "state/embeddings/",
    # Per-run ledger / observation dumps under the apply lane are not source
    # code; excluding them keeps paper-module freshness walks from stat-ing
    # gigabytes of record dirs on every cold /api/station/launcher build.
    "tools/meta/apply/observe_dumps/",
    "tools/meta/apply/observe_history/",
    "tools/meta/apply/observe_plans/",
    "tools/meta/apply/phase_packets/",
    "tools/meta/apply/snapshots/",
    # Branch worktrees under .claude are independent checkouts; a nested
    # commit on another branch is not a freshness signal for THIS tree.
    ".claude/worktrees/",
)
BROAD_CODE_LOCI_FRESHNESS_ROOTS = {
    "annexes",
    "obsidian",
    "state/meta_missions",
}

SKIP_FILES = {"README.md", "_deprecated.md"}
SKIP_PREFIX = "_"

FRONTMATTER_KEYS = {
    "projection_class": ["Projection class", "Projection Class"],
    "authored": ["Authored"],
    "governing_principles": ["Governing principles", "Governing principle"],
    "governing_concepts": ["Governing concepts", "Governing concept"],
    "governing_mechanisms": ["Governing mechanisms", "Governing mechanism"],
    "depends_on": ["Depends on"],
    "search_aliases": ["Search aliases", "Aliases"],
    "subsystem_slug": ["Subsystem slug"],
    "snapshot_cadence": ["Snapshot cadence"],
    "primary_subdomain": ["Primary subdomain"],
    "secondary_subdomains": ["Secondary subdomains"],
    "compression_atom": ["Compression atom"],
    "compression_flag": ["Compression flag"],
    "compression_keys": ["Compression keys"],
    "open_when": ["Open when"],
    "do_not_open_when": ["Do not open when"],
    "safe_drilldown": ["Safe drilldown"],
}

# Per std_paper_module.json::compression_authoring_contract.field_budgets.
COMPRESSION_ATOM_MAX_WORDS = 8
COMPRESSION_ATOM_MAX_CHARS = 80
COMPRESSION_FLAG_MAX_CHARS = 220

CON_PRI_MECH_RE = re.compile(r"`?(pri|con|mech)_[0-9A-Za-z_]+`?")
ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
ABBREV_TAIL_RE = re.compile(r"\b(e\.g|i\.e|etc|vs|cf|al|Fig|No)\.$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\*\(\[`\"'])")
PATH_EXTENSION_RE = re.compile(
    r"[A-Za-z0-9_./\-]+\.(?:py|json|md|ts|tsx|css|html|sql|yml|yaml|mdc|jsonl|flag|toml|sqlite|rs|swift|js|jsx|txt|xml|ini|sh|zsh|bash|plist)"
)
DATE_SUFFIX_RE = re.compile(r"_\d{4}-\d{2}-\d{2}$")
PLANNED_SURFACES_HEADING = "Planned surfaces (NOT YET BUILT)"

# Code-family coverage policy (CAP cap_quick_paper_module_coverage_false_negative_cle_87d3ece5d8b4 /
# event wie_20260517T061820Z_484f5726). `first_author_queue=0` must no longer imply full
# Python-substrate paper-module coverage unless `unmapped_code_family_queue=0`.
CODE_FAMILY_COVERAGE_SCHEMA_VERSION = "paper_module_code_family_coverage_v0"
CODE_FAMILY_ROOTS: tuple[str, ...] = ("system", "tools")
CODE_FAMILY_MIN_PY_FILES = 2
CODE_FAMILY_MIN_PY_LOC = 300
CODE_FAMILY_LARGE_PY_FILES = 6
CODE_FAMILY_LARGE_PY_LOC = 1500
CODE_FAMILY_INDEX_PROJECTION_CLASSES = {"index", "root"}
CODE_FAMILY_REPRESENTATIVE_FILE_CAP = 4
CODE_FAMILY_DECOMPOSITION_ROOT_MIN_OWNERS = 100
CODE_FAMILY_EXCLUDED_SEGMENTS = {
    "__pycache__",
    ".venv",
    "node_modules",
    "snapshots",
    "_archive",
    "archive",
    "vendor",
    "vendored",
    "generated",
    "build",
    "dist",
}
CODE_FAMILY_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "tools/meta/apply/observe_dumps/",
    "tools/meta/apply/observe_history/",
    "tools/meta/apply/observe_plans/",
    "tools/meta/apply/phase_packets/",
    "tools/meta/apply/snapshots/",
)

REPO_TOP_DIRS = (
    "codex/",
    "tools/",
    "system/",
    "annexes/",
    "obsidian/",
    "docs/",
    "apps/",
    "configs/",
    "scripts/",
    "state/",
    ".claude/",
    ".codex/",
    ".cursor/",
    "AGENTS.md",
    "CLAUDE.md",
    "CODEX.md",
    "README.md",
    "kernel.py",
    "reactions.yaml",
)


@dataclass
class Finding:
    severity: str
    rule: str
    message: str


@dataclass
class ParsedModule:
    slug: str
    title: str
    file: Path
    frontmatter: dict[str, Any]
    sections: dict[str, str]
    section_order: list[str]
    raw_text: str
    findings: list[Finding] = field(default_factory=list)
    analysis: dict[str, Any] = field(default_factory=dict)

    @property
    def projection_class(self) -> str:
        return str(self.frontmatter.get("projection_class") or "").strip()

    @property
    def depends_on(self) -> list[str]:
        return list(self.frontmatter.get("depends_on", []))

    @property
    def governing_principles(self) -> list[str]:
        return list(self.frontmatter.get("governing_principles", []))

    @property
    def governing_concepts(self) -> list[str]:
        return list(self.frontmatter.get("governing_concepts", []))

    @property
    def governing_mechanisms(self) -> list[str]:
        return list(self.frontmatter.get("governing_mechanisms", []))

    @property
    def authored(self) -> str | None:
        return self.frontmatter.get("authored")

    @property
    def search_aliases(self) -> list[str]:
        return list(self.frontmatter.get("search_aliases", []))

    @property
    def compression_atom(self) -> str:
        return str(self.frontmatter.get("compression_atom") or "").strip()

    @property
    def compression_flag(self) -> str:
        return str(self.frontmatter.get("compression_flag") or "").strip()

    @property
    def compression_keys(self) -> list[str]:
        return list(self.frontmatter.get("compression_keys", []))

    @property
    def open_when(self) -> str:
        return str(self.frontmatter.get("open_when") or "").strip()

    @property
    def do_not_open_when(self) -> str:
        return str(self.frontmatter.get("do_not_open_when") or "").strip()

    @property
    def safe_drilldown(self) -> str:
        return str(self.frontmatter.get("safe_drilldown") or "").strip()


@dataclass
class PaperModuleRuntime:
    repo_root: Path
    standard: dict[str, Any]
    candidates: list[dict[str, Any]]
    modules: list[ParsedModule]
    index: dict[str, Any]
    report: dict[str, Any]
    doctrine_to_paper_modules: dict[str, Any]
    route_coverage: dict[str, Any]
    fact_ledger: dict[str, Any]
    source_manifest: dict[str, Any]
    generated_freshness: dict[str, Any]
    current_freshness: dict[str, Any]
    readme_projection: str
    readme_content: str | None


def _utc_iso(timespec: str = "seconds") -> str:
    return datetime.now(timezone.utc).isoformat(timespec=timespec)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def load_standard(path: Path = STANDARD_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_candidates(path: Path = CANDIDATES_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("candidates")
    if not isinstance(rows, list):
        return []
    return [dict(item) for item in rows if isinstance(item, Mapping)]


def load_index_modules_by_slug(path: Path = INDEX_PATH) -> dict[str, dict[str, Any]]:
    payload = _safe_load_json(path)
    rows = payload.get("modules") if isinstance(payload, Mapping) else []
    indexed: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return indexed
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        slug = str(item.get("slug") or "").strip()
        if slug:
            indexed[slug] = dict(item)
    return indexed


def _normalize_list_value(raw: str) -> list[str]:
    values: list[str] = []
    for token in re.split(r"[,;]", raw):
        token = token.strip().strip("`").strip()
        if token:
            values.append(token)
    return values


def _clean_depends_on_token(token: str) -> str:
    token = token.strip().strip("`").strip()
    paren_idx = token.find("(")
    if paren_idx > 0:
        token = token[:paren_idx].strip()
    return token.strip("`").strip()


def parse_frontmatter(raw_text: str) -> dict[str, Any]:
    head_lines: list[str] = []
    for line in raw_text.splitlines():
        if line.startswith("## "):
            break
        head_lines.append(line)

    result: dict[str, Any] = {}
    bold_re = re.compile(r"^\s*\*\*([^:]+):\*\*\s*(.+?)\s*$")
    plain_re = re.compile(r"^\s*([A-Z][A-Za-z ]+?):\s+(.+?)\s*$")
    projection_classes = {"subsystem", "index", "snapshot", "root"}

    for line in head_lines:
        match = bold_re.match(line) or plain_re.match(line)
        if not match:
            continue
        raw_key, raw_value = match.group(1).strip(), match.group(2).strip()
        for canonical, aliases in FRONTMATTER_KEYS.items():
            if raw_key not in aliases:
                continue
            if canonical == "depends_on":
                tokens = [_clean_depends_on_token(item) for item in _normalize_list_value(raw_value)]
                result[canonical] = [item for item in tokens if item]
            elif canonical in {"governing_principles", "governing_concepts", "governing_mechanisms"}:
                ids = [m.group(0).strip("`") for m in CON_PRI_MECH_RE.finditer(raw_value)]
                result[canonical] = ids or _normalize_list_value(raw_value)
            elif canonical in {"secondary_subdomains", "search_aliases", "compression_keys"}:
                result[canonical] = _normalize_list_value(raw_value)
            elif canonical == "authored":
                iso_match = ISO_DATE_RE.search(raw_value)
                result[canonical] = iso_match.group(1) if iso_match else raw_value
            elif canonical == "projection_class":
                value = raw_value.split()[0].strip("`").strip().lower()
                result[canonical] = value if value in projection_classes else raw_value.strip("`").strip().lower()
            else:
                result[canonical] = raw_value.strip("`").strip()
            break
    return result


def parse_paper_module_header(path: Path) -> dict[str, Any]:
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def parse_title(raw_text: str, fallback_slug: str) -> str:
    match = TITLE_RE.search(raw_text)
    return str(match.group(1)).strip() if match else fallback_slug.replace("_", " ")


def parse_sections(raw_text: str, heading_by_slug: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    lines = raw_text.splitlines()
    heading_norm = {slug: heading.lower() for slug, heading in heading_by_slug.items()}
    positions: list[tuple[int, str | None]] = []
    for idx, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        heading_text = line[3:].strip().lower()
        matched: str | None = None
        for slug, expected in heading_norm.items():
            if heading_text == expected:
                matched = slug
                break
        positions.append((idx, matched))

    sections: dict[str, str] = {}
    section_order: list[str] = []
    for index, (line_idx, slug) in enumerate(positions):
        if slug is None:
            continue
        start = line_idx + 1
        end = positions[index + 1][0] if index + 1 < len(positions) else len(lines)
        sections[slug] = "\n".join(lines[start:end]).strip()
        section_order.append(slug)
    return sections, section_order


def parse_h2_sequence(raw_text: str, heading_by_slug: dict[str, str]) -> list[str | None]:
    sequence: list[str | None] = []
    heading_norm = {slug: heading.lower() for slug, heading in heading_by_slug.items()}
    for line in raw_text.splitlines():
        if not line.startswith("## "):
            continue
        heading_text = line[3:].strip().lower()
        matched: str | None = None
        for slug, expected in heading_norm.items():
            if heading_text == expected:
                matched = slug
                break
        sequence.append(matched)
    return sequence


def extract_h2_body(raw_text: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = raw_text.splitlines()
    body: list[str] = []
    capturing = False
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip().lower()
            if capturing:
                break
            if current == target:
                capturing = True
                continue
        if capturing:
            body.append(line)
    return "\n".join(body).strip()


def remove_h2_section(raw_text: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = raw_text.splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip().lower()
            if skipping:
                skipping = False
            if current == target:
                skipping = True
                continue
        if not skipping:
            kept.append(line)
    return "\n".join(kept)


def count_sentences(text: str) -> int:
    if not text:
        return 0
    cleaned = CODE_FENCE_RE.sub(" ", text)
    cleaned = INLINE_CODE_RE.sub(" ", cleaned)
    cleaned = MD_LINK_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    pieces = SENTENCE_SPLIT_RE.split(cleaned)
    count = 0
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if ABBREV_TAIL_RE.search(piece):
            continue
        count += 1
    return count


def _normalize_token(raw: str) -> str:
    token = raw.strip().strip("`")
    if not token or " " in token:
        return ""
    for bad in ("<", ">", "{", "}", "*"):
        if bad in token:
            return ""
    if "#" in token:
        token = token.split("#", 1)[0]
    if token.startswith(("http://", "https://", "mailto:")):
        return ""
    if "::" in token:
        token = token.split("::", 1)[0]
    token = re.sub(r":\d+(-\d+)?$", "", token)
    token = token.rstrip(".,;:)")
    if token.startswith("./"):
        token = token[2:]
    return token


def _looks_like_repo_path(token: str) -> bool:
    if not token:
        return False
    stripped = token
    walk_match = re.match(r"^(\.\./)+", stripped)
    if walk_match:
        stripped = stripped[walk_match.end():]
    if PATH_EXTENSION_RE.fullmatch(stripped):
        return True
    return any(stripped == prefix or stripped.startswith(prefix) for prefix in REPO_TOP_DIRS)


def extract_code_loci_paths(body: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", body):
        candidates.append(match.group(1))
    for match in re.finditer(r"`([^`]+)`", body):
        candidates.append(match.group(1))

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        token = _normalize_token(raw)
        if not token or not _looks_like_repo_path(token) or token in seen:
            continue
        cleaned.append(token)
        seen.add(token)
    return cleaned


def extract_repo_path_mentions(markdown: str) -> list[str]:
    """Return repo-path mentions from prose/link/code spans, excluding fenced code blocks."""
    return extract_code_loci_paths(CODE_FENCE_RE.sub("", markdown))


def resolve_loci_path(repo_root: Path, module_file: Path, candidate: str) -> Path | None:
    repo_candidate = (repo_root / candidate).resolve()
    try:
        repo_candidate.relative_to(repo_root)
    except ValueError:
        repo_candidate = None
    if repo_candidate and repo_candidate.exists():
        return repo_candidate

    relative_candidate = (module_file.parent / candidate).resolve()
    try:
        relative_candidate.relative_to(repo_root)
    except ValueError:
        return None
    return relative_candidate if relative_candidate.exists() else None


def _section_has_table(body: str) -> bool:
    return bool(re.search(r"^\s*\|.+\|.+\|\s*$", body, re.MULTILINE))


def _count_bullet_lines(body: str) -> int:
    return len([line for line in body.splitlines() if re.match(r"^\s*[-*]\s+\S", line)])


def _extract_bullet_values(body: str, limit: int = 3) -> list[str]:
    values: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if not match:
            continue
        values.append(match.group(1).strip())
        if len(values) >= limit:
            break
    return values


def _count_table_rows(body: str) -> int:
    rows = 0
    seen_header = False
    for line in body.splitlines():
        if re.match(r"^\s*\|.+\|\s*$", line):
            if not seen_header:
                seen_header = True
                continue
            if re.match(r"^\s*\|\s*:?-+:?\s*\|", line):
                continue
            rows += 1
    return rows


def _split_markdown_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _parse_markdown_table(body: str) -> list[dict[str, str]]:
    table_lines = [line for line in body.splitlines() if re.match(r"^\s*\|.+\|\s*$", line)]
    if len(table_lines) < 3:
        return []
    header = [_tokenize(cell)[0] if _tokenize(cell) else "" for cell in _split_markdown_table_row(table_lines[0])]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        if re.match(r"^\s*\|\s*:?-+:?\s*\|", line):
            continue
        cells = _split_markdown_table_row(line)
        row: dict[str, str] = {}
        for idx, cell in enumerate(cells):
            key = header[idx] if idx < len(header) and header[idx] else f"column_{idx + 1}"
            row[key] = cell
        rows.append(row)
    return rows


def extract_planned_surfaces(raw_text: str) -> list[dict[str, Any]]:
    body = extract_h2_body(raw_text, PLANNED_SURFACES_HEADING)
    if not body:
        return []
    planned: list[dict[str, Any]] = []
    seen: set[str] = set()
    rows = _parse_markdown_table(body)
    if rows:
        for row in rows:
            candidates = extract_code_loci_paths(" ".join(row.values()))
            for candidate in candidates:
                if candidate in seen:
                    continue
                planned.append(
                    {
                        "path": candidate,
                        "surface": row.get("surface") or row.get("name") or "",
                        "status": row.get("status") or "NOT YET BUILT",
                        "promotion_trigger": row.get("promotion") or row.get("trigger") or row.get("column_4") or "",
                    }
                )
                seen.add(candidate)
        return planned

    for candidate in extract_code_loci_paths(body):
        if candidate in seen:
            continue
        planned.append(
            {
                "path": candidate,
                "surface": "",
                "status": "NOT YET BUILT",
                "promotion_trigger": "",
            }
        )
        seen.add(candidate)
    return planned


def _projection_policy(standard: dict[str, Any], projection_class: str) -> dict[str, Any]:
    policies = standard.get("projection_classes")
    if not isinstance(policies, Mapping):
        return {}
    policy = policies.get(projection_class)
    return dict(policy) if isinstance(policy, Mapping) else {}


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return round(numerator / denominator, 3)


def _mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return None


@lru_cache(maxsize=16384)
def _is_builder_generated_surface(rel_path: str) -> bool:
    normalized = str(rel_path).strip().rstrip("/")
    if normalized in BUILDER_GENERATED_SURFACE_PATHS:
        return True
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in BUILDER_GENERATED_SURFACE_PREFIXES)


def _is_runtime_cache_surface(path: Path, *, repo_root: Path) -> bool:
    try:
        rel_parts = path.relative_to(repo_root).parts
    except ValueError:
        rel_parts = path.parts
    if "__pycache__" in rel_parts or ".pytest_cache" in rel_parts or "node_modules" in rel_parts:
        return True
    return path.suffix in {".pyc", ".pyo"}


def _freshness_source_mtime(
    *,
    repo_root: Path,
    rel_path: str,
    cache: dict[tuple[str, str], tuple[float, str] | None] | None = None,
) -> tuple[float, str] | None:
    # Same rel_path resolves to the same mtime within one runtime build; many
    # paper modules share loci (`codex/doctrine/paper_modules/`, `system/server/ui/`),
    # so a per-call cache collapses hundreds of `rglob("*")` walks on the hot
    # `/api/station/launcher` path.
    if cache is not None:
        key = (str(repo_root), rel_path)
        if key in cache:
            return cache[key]
    source_path = repo_root / rel_path
    if source_path.is_dir():
        normalized_rel = str(rel_path).strip().rstrip("/")
        if normalized_rel in BROAD_CODE_LOCI_FRESHNESS_ROOTS:
            try:
                coarse_mtime_raw = source_path.stat().st_mtime
            except OSError:
                result = None
            else:
                result = (
                    coarse_mtime_raw,
                    datetime.fromtimestamp(coarse_mtime_raw, tz=timezone.utc).isoformat(timespec="seconds"),
                )
            if cache is not None:
                cache[(str(repo_root), rel_path)] = result
            return result
        newest = 0.0
        # os.walk lets us prune entire generated / cache subtrees without
        # descending into them. Skipping `tools/meta/apply/observe_dumps/`
        # alone avoids ~1.9GB of per-run record walks on every cold build.
        repo_str = str(repo_root)
        for dirpath, dirnames, filenames in os.walk(source_path):
            # Prune runtime-cache dirs in place (modifies dirnames).
            dirnames[:] = [
                d for d in dirnames
                if d not in {"__pycache__", ".pytest_cache", "node_modules"}
            ]
            # Prune generated-surface subtrees by rel-path match.
            try:
                dir_rel = os.path.relpath(dirpath, repo_str)
            except ValueError:
                dir_rel = ""
            kept: list[str] = []
            for d in dirnames:
                child_rel = f"{dir_rel}/{d}" if dir_rel and dir_rel != "." else d
                if _is_builder_generated_surface(child_rel):
                    continue
                kept.append(d)
            dirnames[:] = kept
            for fname in filenames:
                if fname.endswith((".pyc", ".pyo")):
                    continue
                file_rel = f"{dir_rel}/{fname}" if dir_rel and dir_rel != "." else fname
                # Generated subtrees are pruned from dirnames above. At file
                # level only exact generated-file paths remain possible, so do
                # not pay the prefix scan for every file in large directories.
                if file_rel.strip().rstrip("/") in BUILDER_GENERATED_SURFACE_PATHS:
                    continue
                try:
                    mtime = os.stat(os.path.join(dirpath, fname)).st_mtime
                except OSError:
                    continue
                if mtime > newest:
                    newest = mtime
        if newest <= 0:
            result: tuple[float, str] | None = None
        else:
            result = newest, datetime.fromtimestamp(newest, tz=timezone.utc).isoformat(timespec="seconds")
        if cache is not None:
            cache[(str(repo_root), rel_path)] = result
        return result
    try:
        source_mtime_raw = source_path.stat().st_mtime
    except OSError:
        if cache is not None:
            cache[(str(repo_root), rel_path)] = None
        return None
    source_mtime = datetime.fromtimestamp(source_mtime_raw, tz=timezone.utc).isoformat(timespec="seconds")
    result = source_mtime_raw, source_mtime
    if cache is not None:
        cache[(str(repo_root), rel_path)] = result
    return result


def _code_loci_freshness_packet(
    module: ParsedModule,
    *,
    repo_root: Path,
    mtime_cache: dict[tuple[str, str], tuple[float, str] | None] | None = None,
) -> dict[str, Any]:
    resolved_paths = [str(path) for path in module.analysis.get("code_loci_resolved_paths", []) if str(path).strip()]
    module_mtime = _mtime_iso(module.file)
    try:
        module_mtime_raw = module.file.stat().st_mtime
    except OSError:
        module_mtime_raw = 0.0

    source_rows: list[dict[str, Any]] = []
    source_newer_rows: list[dict[str, Any]] = []
    ignored_generated_surface_count = 0
    newest_source_path: str | None = None
    newest_source_mtime: str | None = None
    newest_source_mtime_raw = 0.0

    for rel_path in resolved_paths:
        if _is_builder_generated_surface(rel_path):
            ignored_generated_surface_count += 1
            continue
        source_mtime_pair = _freshness_source_mtime(
            repo_root=repo_root, rel_path=rel_path, cache=mtime_cache
        )
        if source_mtime_pair is None:
            continue
        source_mtime_raw, source_mtime = source_mtime_pair
        row = {"path": rel_path, "source_mtime": source_mtime}
        source_rows.append(row)
        if source_mtime_raw > newest_source_mtime_raw:
            newest_source_mtime_raw = source_mtime_raw
            newest_source_path = rel_path
            newest_source_mtime = source_mtime
        if source_mtime_raw > module_mtime_raw:
            source_newer_rows.append(row)

    if not resolved_paths:
        status = "no_resolved_code_loci"
    elif source_newer_rows:
        status = "source_changed"
    else:
        status = "source_current"

    # pattern: RepoAgent incremental documentation status — expose source freshness
    # next to each paper module without forcing a full documentation rebuild.
    return {
        "status": status,
        "module_mtime": module_mtime,
        "resolved_code_loci_count": len(resolved_paths),
        "checked_code_loci_count": len(source_rows),
        "ignored_generated_surface_count": ignored_generated_surface_count,
        "source_newer_than_module_count": len(source_newer_rows),
        "source_newer_than_module": source_newer_rows[:10],
        "newest_source_path": newest_source_path,
        "newest_source_mtime": newest_source_mtime,
    }


def _documentation_quality_packet(
    module: ParsedModule,
    *,
    repo_root: Path,
    required_slugs: list[str],
    deliverable_rows: int,
    tldr_count: int,
    ontology_body: str,
) -> dict[str, Any]:
    missing_sections = [slug for slug in required_slugs if slug not in module.sections]
    planned_surfaces = extract_planned_surfaces(module.raw_text)
    markdown_for_truthfulness = remove_h2_section(module.raw_text, PLANNED_SURFACES_HEADING)
    path_mentions = extract_repo_path_mentions(markdown_for_truthfulness)
    resolved_mentions: list[str] = []
    unresolved_mentions: list[str] = []
    for candidate in path_mentions:
        if "/" not in candidate:
            continue
        resolved = resolve_loci_path(repo_root, module.file, candidate)
        if resolved is None:
            unresolved_mentions.append(candidate)
        else:
            resolved_mentions.append(str(resolved.relative_to(repo_root)))

    # pattern: DocAgent-style documentation evaluation — completeness + actionability + existence ratio.
    return {
        "completeness": {
            "required_sections_present": len(required_slugs) - len(missing_sections),
            "required_sections_total": len(required_slugs),
            "ratio": _ratio(len(required_slugs) - len(missing_sections), len(required_slugs)),
            "missing_sections": missing_sections,
        },
        "helpfulness_proxy": {
            "deliverable_rows": deliverable_rows,
            "has_ontology_table": _section_has_table(ontology_body),
            "tldr_sentence_count": tldr_count,
        },
        "truthfulness_proxy": {
            "repo_path_mentions": len(path_mentions),
            "resolved_repo_path_mentions": len(resolved_mentions),
            "planned_repo_path_mentions": len(planned_surfaces),
            "existence_ratio": _ratio(len(resolved_mentions), len(path_mentions)),
            "unresolved_repo_path_mentions": unresolved_mentions[:10],
        },
    }


def load_paper_modules(directory: Path, standard: dict[str, Any]) -> list[ParsedModule]:
    heading_by_slug = {item["slug"]: item["heading"] for item in standard["required_sections"]}
    modules: list[ParsedModule] = []
    for path in sorted(directory.glob("*.md")):
        if path.name in SKIP_FILES or path.name.startswith(SKIP_PREFIX):
            continue
        raw_text = path.read_text(encoding="utf-8")
        slug = path.stem
        sections, section_order = parse_sections(raw_text, heading_by_slug)
        modules.append(
            ParsedModule(
                slug=slug,
                title=parse_title(raw_text, slug),
                file=path,
                frontmatter=parse_frontmatter(raw_text),
                sections=sections,
                section_order=section_order,
                raw_text=raw_text,
            )
        )
    return modules


def compute_dag(modules: list[ParsedModule]) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, int], list[list[str]]]:
    slugs = {module.slug for module in modules}
    adjacency: dict[str, list[str]] = {
        module.slug: [dep for dep in module.depends_on if dep in slugs]
        for module in modules
    }
    reverse: dict[str, list[str]] = {slug: [] for slug in slugs}
    fan_in: dict[str, int] = {slug: 0 for slug in slugs}
    for slug, deps in adjacency.items():
        for dep in deps:
            reverse.setdefault(dep, []).append(slug)
            fan_in[dep] += 1

    white, grey, black = 0, 1, 2
    color: dict[str, int] = {slug: white for slug in slugs}
    cycles: list[list[str]] = []

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = grey
        stack.append(node)
        for neighbor in adjacency.get(node, []):
            if color.get(neighbor, black) == grey:
                if neighbor in stack:
                    idx = stack.index(neighbor)
                    cycles.append(stack[idx:] + [neighbor])
            elif color.get(neighbor, black) == white:
                dfs(neighbor, stack)
        stack.pop()
        color[node] = black

    for slug in sorted(slugs):
        if color[slug] == white:
            dfs(slug, [])

    for slug in reverse:
        reverse[slug] = sorted(reverse[slug])
    return adjacency, reverse, fan_in, cycles


def compute_hierarchy_metrics(
    adjacency: dict[str, list[str]],
    reverse: dict[str, list[str]],
) -> tuple[dict[str, int], dict[str, int]]:
    slugs = sorted(set(adjacency) | set(reverse))
    roots = [slug for slug in slugs if not reverse.get(slug)]
    depth_from_root: dict[str, int] = {slug: 0 for slug in roots}
    queue = list(roots)
    while queue:
        node = queue.pop(0)
        for child in adjacency.get(node, []):
            next_depth = depth_from_root.get(node, 0) + 1
            if child not in depth_from_root or next_depth < depth_from_root[child]:
                depth_from_root[child] = next_depth
                queue.append(child)
    for slug in slugs:
        depth_from_root.setdefault(slug, 0)

    distance_cache: dict[str, int] = {}

    def distance_to_leaf(node: str, seen: set[str]) -> int:
        if node in distance_cache:
            return distance_cache[node]
        if node in seen:
            return 0
        children = adjacency.get(node, [])
        if not children:
            distance_cache[node] = 0
            return 0
        distance_cache[node] = 1 + max(distance_to_leaf(child, seen | {node}) for child in children)
        return distance_cache[node]

    distance_to_leaf_by_slug = {slug: distance_to_leaf(slug, set()) for slug in slugs}
    return depth_from_root, distance_to_leaf_by_slug


def bracket_for_module(standard: dict[str, Any], module: ParsedModule, fan_in_inbound: int) -> int:
    policy = _projection_policy(standard, module.projection_class)
    fixed = policy.get("fixed_tldr_budget")
    if isinstance(fixed, int) and fixed > 0:
        return fixed
    if fan_in_inbound >= 3:
        return 8
    if fan_in_inbound >= 1:
        return 5
    return 3


def _boundary_pressure(row_count: int, cap: int, recommended_action: str) -> str:
    if cap <= 0:
        return "normal"
    if recommended_action == "split":
        return "split_required"
    ratio = row_count / cap
    if ratio > 1.0:
        return "high"
    if ratio >= 0.75:
        return "elevated"
    return "normal"


def _first_paragraph(body: str) -> str:
    pieces = re.split(r"\n\s*\n", body.strip(), maxsplit=1)
    return pieces[0].strip() if pieces else ""


def _word_count(text: str) -> int:
    return len([token for token in re.split(r"\s+", text.strip()) if token])


def _first_sentence_clean(body: str) -> str:
    paragraph = _first_paragraph(body)
    if not paragraph:
        return ""
    cleaned = INLINE_CODE_RE.sub(" ", paragraph)
    cleaned = MD_LINK_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"[*_`#>|]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    pieces = SENTENCE_SPLIT_RE.split(cleaned)
    return pieces[0].strip() if pieces else cleaned


def _truncate_to_atom(text: str) -> str:
    if not text:
        return ""
    words = [token for token in re.split(r"\s+", text.strip()) if token]
    if len(words) > COMPRESSION_ATOM_MAX_WORDS:
        words = words[:COMPRESSION_ATOM_MAX_WORDS]
    candidate = " ".join(words)
    if len(candidate) > COMPRESSION_ATOM_MAX_CHARS:
        candidate = candidate[:COMPRESSION_ATOM_MAX_CHARS].rstrip()
    return candidate.rstrip(".,;:")


def _truncate_to_flag(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) > COMPRESSION_FLAG_MAX_CHARS:
        cleaned = cleaned[:COMPRESSION_FLAG_MAX_CHARS].rstrip()
    return cleaned


def _validate_safe_drilldown(value: str, *, slug: str) -> tuple[str, str]:
    """Return (validated_command, source_marker). Authored values must match exact allowlist.

    Exact-match (not prefix-match) is intentional: agents copy commands out of these rows, so a
    trailing token must not be smuggled past validation. To extend the allowlist, add an exact
    template here and update std_paper_module.json::compression_authoring_contract.fallback_policy.
    """
    default = f"./repo-python kernel.py --option-surface paper_modules --band card --ids {slug}"
    allowed = {
        default,
        f"./repo-python kernel.py --paper-module {slug}",
    }
    candidate = (value or "").strip()
    if not candidate:
        return default, "default_from_slug"
    if candidate in allowed:
        return candidate, "authored_validated"
    return default, "invalid_authored_replaced_with_default"


def build_compression_packet(module: ParsedModule, *, tldr_preview: str) -> dict[str, Any]:
    """Build the typed compression projection per std_paper_module.json::compression_authoring_contract.

    Authored fields take priority. Missing fields fall back to legacy substrate (tldr first
    sentence, search_aliases) with explicit per-field source markers, never silently. Budget
    violations are emitted as findings; authored-over-budget is reported `invalid` rather than
    truncated, so operator voice is never silently rewritten.
    """
    findings: list[dict[str, Any]] = []
    sources: dict[str, str] = {}

    authored_atom = module.compression_atom
    if authored_atom:
        atom_value = authored_atom
        if _word_count(authored_atom) > COMPRESSION_ATOM_MAX_WORDS:
            sources["atom"] = "invalid"
            findings.append(
                {
                    "rule": "compression_atom_words_over_budget",
                    "actual": _word_count(authored_atom),
                    "limit": COMPRESSION_ATOM_MAX_WORDS,
                    "value": authored_atom,
                }
            )
        elif len(authored_atom) > COMPRESSION_ATOM_MAX_CHARS:
            sources["atom"] = "invalid"
            findings.append(
                {
                    "rule": "compression_atom_chars_over_budget",
                    "actual": len(authored_atom),
                    "limit": COMPRESSION_ATOM_MAX_CHARS,
                    "value": authored_atom,
                }
            )
        else:
            sources["atom"] = "authored"
    else:
        fallback = _truncate_to_atom(_first_sentence_clean(tldr_preview))
        atom_value = fallback
        sources["atom"] = "fallback_from_tldr" if fallback else "missing"

    authored_flag = module.compression_flag
    if authored_flag:
        flag_value = authored_flag
        if len(authored_flag) > COMPRESSION_FLAG_MAX_CHARS:
            sources["flag"] = "invalid"
            findings.append(
                {
                    "rule": "compression_flag_chars_over_budget",
                    "actual": len(authored_flag),
                    "limit": COMPRESSION_FLAG_MAX_CHARS,
                    "value": authored_flag,
                }
            )
        else:
            sources["flag"] = "authored"
    elif module.open_when:
        flag_value = _truncate_to_flag(module.open_when)
        sources["flag"] = "fallback_from_open_when"
    elif tldr_preview:
        flag_value = _truncate_to_flag(_first_sentence_clean(tldr_preview))
        sources["flag"] = "fallback_from_tldr" if flag_value else "missing"
    else:
        flag_value = ""
        sources["flag"] = "missing"

    cluster_keys = list(module.compression_keys)
    if cluster_keys:
        sources["cluster_keys"] = "authored"
    elif module.search_aliases:
        cluster_keys = list(module.search_aliases)
        sources["cluster_keys"] = "fallback_from_search_aliases"
    else:
        sources["cluster_keys"] = "missing"

    open_when = module.open_when
    sources["open_when"] = "authored" if open_when else "missing"

    do_not_open_when = module.do_not_open_when
    sources["do_not_open_when"] = "authored" if do_not_open_when else "missing"

    safe_drilldown, drilldown_source = _validate_safe_drilldown(
        module.safe_drilldown, slug=module.slug
    )
    sources["safe_drilldown"] = drilldown_source
    if drilldown_source == "invalid_authored_replaced_with_default":
        findings.append(
            {
                "rule": "safe_drilldown_value_not_in_allowlist",
                "value": module.safe_drilldown,
            }
        )

    # Status roll-up:
    #   authored - every load-bearing field (atom, flag, cluster_keys) is authored.
    #   invalid  - any field is over budget or otherwise rejected.
    #   fallback - at least one load-bearing field used a non-authored fallback.
    #   missing  - atom itself has no source (no authored field, no fallback content).
    load_bearing_sources = {sources["atom"], sources["flag"], sources["cluster_keys"]}
    if "invalid" in load_bearing_sources:
        status = "invalid"
    elif sources["atom"] == "missing":
        status = "missing"
    elif load_bearing_sources == {"authored"}:
        status = "authored"
    else:
        status = "fallback"

    return {
        "atom": atom_value,
        "flag": flag_value,
        "cluster_keys": cluster_keys,
        "open_when": open_when,
        "do_not_open_when": do_not_open_when,
        "safe_drilldown": safe_drilldown,
        "compression_status": status,
        "compression_sources": sources,
        "findings": findings,
    }


def _tokenize(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if token]


def _search_tokens(module: ParsedModule) -> list[str]:
    tokens: set[str] = set()
    for source in (
        module.slug,
        module.title,
        " ".join(module.search_aliases),
        " ".join(module.depends_on),
        " ".join(module.governing_principles),
        " ".join(module.governing_concepts),
        " ".join(module.analysis.get("deliverables_preview", [])),
    ):
        tokens.update(_tokenize(str(source)))
    return sorted(tokens)


def _load_governing_ids(repo_root: Path) -> dict[str, set[str]]:
    concept_ids: set[str] = set()
    apex_concept_ids: set[str] = set()
    for path in (repo_root / "codex" / "doctrine" / "concepts").glob("*.json"):
        payload = _safe_load_json(path)
        concept_id = str((payload or {}).get("id") or "").strip()
        if concept_id:
            concept_ids.add(concept_id)
            if bool((payload or {}).get("is_apex")):
                apex_concept_ids.add(concept_id)

    mechanism_ids: set[str] = set()
    for path in (repo_root / "codex" / "doctrine" / "mechanisms").glob("*.json"):
        payload = _safe_load_json(path)
        mechanism_id = str((payload or {}).get("id") or "").strip()
        if mechanism_id:
            mechanism_ids.add(mechanism_id)

    principle_ids: set[str] = set()
    apex_principle_ids: set[str] = set()
    for path in (repo_root / "obsidian").glob("**/raw_seed/raw_seed_principles.json"):
        payload = _safe_load_json(path)
        rows = (payload or {}).get("principles")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            principle_id = str(row.get("id") or "").strip()
            if principle_id:
                principle_ids.add(principle_id)
                if bool(row.get("is_apex")):
                    apex_principle_ids.add(principle_id)

    return {
        "principles": principle_ids,
        "concepts": concept_ids,
        "mechanisms": mechanism_ids,
        "apex_concepts": apex_concept_ids,
        "apex_principles": apex_principle_ids,
    }


FORMAL_EVIDENCE_CELL_ID_PATTERN = re.compile(
    r"\berdos\d+\.[a-z0-9_.]+\b", re.IGNORECASE
)


def _load_cells_from_registry(
    *, repo_root: Path | None = None, registry_path: Path | None = None
) -> dict[str, dict[str, Any]] | None:
    """Load cell_id -> cell map from the formal-evidence cell registry.

    The registry path is resolved from
    ``std_paper_module.json::formal_evidence_cells.registry_source``
    if present, with the historical sibling default of
    ``state/formal_math_research_operations/formal_evidence_cell_registry.json``
    as a fallback. Returns ``None`` when no registry is found so the
    caller can use the bootstrap-direct-manifest loader instead.

    Registry-loaded cells carry ``can_satisfy_paper_module_anchor`` from the
    registry. When that flag is False (manifest receipt failed, anchors
    incomplete, etc.), the cell's ``status`` is coerced to
    ``missing_source`` so the existing audit pathway emits the right
    formal_evidence_cell_id_missing_source error rather than silently
    counting it as an anchor supplier.
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    if registry_path is None:
        standard_path = root / "codex/standards/std_paper_module.json"
        registry_rel: str | None = None
        if standard_path.exists():
            try:
                standard = json.loads(standard_path.read_text(encoding="utf-8"))
                contract = (standard or {}).get("formal_evidence_cells", {}) or {}
                source = contract.get("registry_source")
                if isinstance(source, str) and source:
                    registry_rel = source
            except json.JSONDecodeError:
                pass
        if registry_rel is None:
            registry_rel = (
                "state/formal_math_research_operations/"
                "formal_evidence_cell_registry.json"
            )
        registry_path = (
            Path(registry_rel)
            if Path(registry_rel).is_absolute()
            else (root / registry_rel)
        )
    if not registry_path.exists():
        return None
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(registry, dict):
        return None
    cells: dict[str, dict[str, Any]] = {}
    for cell in registry.get("cells", []) or []:
        if not isinstance(cell, dict):
            continue
        cell_id = cell.get("cell_id")
        if not isinstance(cell_id, str) or not cell_id:
            continue
        cell_copy = dict(cell)
        if cell_copy.get("can_satisfy_paper_module_anchor") is False:
            cell_copy["status"] = "missing_source"
        cells[cell_id] = cell_copy
    return cells


def _load_known_formal_evidence_cells(
    *, repo_root: Path | None = None
) -> dict[str, dict[str, Any]]:
    """Load cell_id -> cell map.

    Registry-first: try ``_load_cells_from_registry``; if it returns a non-
    empty map, that is the operational inventory authority. Falls back to
    reading every manifest declared in
    ``std_paper_module.json::formal_evidence_cells.known_manifests``
    (bootstrap path; the registry is the long-term authority).

    Errors are tolerated (missing manifest path, malformed JSON, non-dict
    cell) so the validator stays usable while manifests or the registry are
    being authored. Cells without a ``cell_id`` field are skipped.
    """
    registry_cells = _load_cells_from_registry(repo_root=repo_root)
    if registry_cells:
        return registry_cells

    root = repo_root if repo_root is not None else REPO_ROOT
    standard_path = root / "codex/standards/std_paper_module.json"
    if not standard_path.exists():
        return {}
    try:
        standard = json.loads(standard_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    contract = (standard or {}).get("formal_evidence_cells", {}) or {}
    manifest_refs = contract.get("known_manifests", []) or []
    cells: dict[str, dict[str, Any]] = {}
    for rel in manifest_refs:
        if not isinstance(rel, str):
            continue
        candidate = Path(rel) if Path(rel).is_absolute() else (root / rel)
        if not candidate.exists():
            continue
        try:
            manifest = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(manifest, dict):
            continue
        for cell in manifest.get("cells", []) or []:
            if not isinstance(cell, dict):
                continue
            cell_id = cell.get("cell_id")
            if isinstance(cell_id, str) and cell_id:
                cells[cell_id] = cell
    return cells


def _cell_anchor_presence(cell: dict[str, Any]) -> set[str]:
    """Which of the three required anchor classes does this cell carry?"""
    present: set[str] = set()
    if cell.get("claim_boundary"):
        present.add("claim_boundary")
    receipts = cell.get("receipt_refs")
    if isinstance(receipts, list) and receipts:
        present.add("receipt")
    if cell.get("work_item_id"):
        present.add("work_item")
    return present


FORMAL_EVIDENCE_HIGH_SIGNAL_PHRASES: tuple[str, ...] = (
    "formal proof",
    "formally proved",
    "formally-proved",
    "lean-proved",
    "lean-checked",
    "no-sorry",
    "#print axioms",
    "sorryax",
)

FORMAL_EVIDENCE_MEDIUM_SIGNAL_PHRASES: tuple[str, ...] = (
    "mathlib",
    "theorem proved",
    "theorem-proved",
)

FORMAL_EVIDENCE_ANCHOR_CLASSES: dict[str, tuple[str, ...]] = {
    "claim_boundary": ("claim_boundary",),
    "receipt": ("receipt_ref", "receipt_refs", "receipt.json"),
    "work_item": (
        "work_item_id",
        "workitem anchor",
        "cap_quick_",
        "cap_dissemination_",
        "cap_quick_mathematics_",
    ),
}


def audit_formal_evidence_cells(
    module: ParsedModule,
    *,
    known_cells: dict[str, dict[str, Any]] | None = None,
) -> list[Finding]:
    """Refuse paper-module formal-proof language without evidence-cell anchors.

    Per ``mathematics_mission_pipeline.md`` (`### Formal Evidence Cells`), any
    paper module using formal-proof verbs (``formal proof``, ``Lean-proved``,
    ``no-sorry``, ``#print axioms``, ``sorryAx`` etc.) must carry evidence-cell
    anchors: ``claim_boundary``, ``receipt_ref``, and ``work_item_id`` (or
    equivalent cap anchor). Without all three, the language must downgrade to
    narrative-only or be omitted.

    Classifications (all severity ``warning`` in this first slice; ``info`` for
    compliant cells):

    - ``formal_evidence_cell_present`` — vocabulary appears AND all three
      anchor classes are present somewhere in the module body.
    - ``formal_evidence_cell_missing_anchor`` — vocabulary appears but at
      least one (not all) anchor class is missing.
    - ``formal_evidence_overclaim`` — high-signal vocabulary appears AND all
      three anchor classes are missing. Stays at ``warning`` in this first
      slice so existing drift is surfaced without hard-failing CI; promote to
      ``error`` in a follow-on slice once authors have annotated.

    Bare tokens ``Lean`` and ``theorem`` are intentionally NOT in the signal
    list because they appear in section headings, metaphor (``proof surface``,
    ``proof of concept``), and routine navigation prose. Only high-signal
    multi-word phrases trigger the check.
    """
    findings: list[Finding] = []
    lower = module.raw_text.lower()

    high_signal_hits = sorted(
        {phrase for phrase in FORMAL_EVIDENCE_HIGH_SIGNAL_PHRASES if phrase in lower}
    )
    medium_signal_hits = sorted(
        {phrase for phrase in FORMAL_EVIDENCE_MEDIUM_SIGNAL_PHRASES if phrase in lower}
    )
    if not high_signal_hits and not medium_signal_hits:
        return findings

    anchor_present: dict[str, bool] = {}
    for class_name, vocab in FORMAL_EVIDENCE_ANCHOR_CLASSES.items():
        anchor_present[class_name] = any(token in lower for token in vocab)

    if known_cells is None:
        known_cells = _load_known_formal_evidence_cells()

    raw_text = module.raw_text
    # Detection authority: any known cell_id literally present in the body
    # resolves, regardless of namespace shape. This decouples resolution from
    # the legacy erdos-only regex so future pilots adopt the registry without
    # editing the regex. The regex still surfaces dotted-id-looking strings
    # that did NOT resolve (for the unknown-id warning).
    literal_resolved = {cid for cid in known_cells if cid in raw_text}
    regex_dotted = {
        match.group(0)
        for match in FORMAL_EVIDENCE_CELL_ID_PATTERN.finditer(raw_text)
    }
    cited_dotted = literal_resolved | regex_dotted

    resolved_ids: list[str] = []
    unresolved_ids: list[str] = []
    incomplete_ids: list[str] = []
    missing_source_ids: list[str] = []
    for cited in sorted(cited_dotted):
        cell = known_cells.get(cited)
        if cell is None:
            unresolved_ids.append(cited)
            continue
        if cell.get("status") == "missing_source":
            missing_source_ids.append(cited)
            continue
        cell_anchors = _cell_anchor_presence(cell)
        for cls in cell_anchors:
            anchor_present[cls] = True
        resolved_ids.append(cited)
        if cell_anchors != set(FORMAL_EVIDENCE_ANCHOR_CLASSES.keys()):
            incomplete_ids.append(cited)

    if resolved_ids:
        findings.append(
            Finding(
                "info",
                "formal_evidence_cell_id_present",
                "Resolved formal-evidence cell ids supplying anchor classes: "
                f"{resolved_ids[:6]}. Cell-id citation is the preferred anchor "
                "form per std_paper_module::formal_evidence_cells.",
            )
        )
    for uid in unresolved_ids:
        findings.append(
            Finding(
                "warning",
                "formal_evidence_cell_id_unknown",
                f"Cited dotted cell id '{uid}' did not resolve against any "
                "known formal-evidence cell manifest (see "
                "std_paper_module::formal_evidence_cells.known_manifests). "
                "Either fix the id, regenerate the relevant manifest, or "
                "remove the citation if not load-bearing.",
            )
        )
    for iid in incomplete_ids:
        cell = known_cells.get(iid, {})
        missing = sorted(
            set(FORMAL_EVIDENCE_ANCHOR_CLASSES.keys())
            - _cell_anchor_presence(cell)
        )
        findings.append(
            Finding(
                "warning",
                "formal_evidence_cell_id_incomplete",
                f"Resolved cell id '{iid}' is missing anchor classes "
                f"{missing} on the manifest side. Repair the manifest cell "
                "to carry claim_boundary + receipt_refs + work_item_id, or "
                "do not rely on this cell id as the sole anchor.",
            )
        )
    for mid in missing_source_ids:
        findings.append(
            Finding(
                "error",
                "formal_evidence_cell_id_missing_source",
                f"Resolved cell id '{mid}' is marked status=missing_source "
                "in its manifest. A cell whose source receipt is missing "
                "MUST NOT be used to satisfy formal-proof anchor "
                "requirements; restore the source receipt or downgrade the "
                "citing module's language.",
            )
        )

    missing_classes = sorted(
        [name for name, present in anchor_present.items() if not present]
    )

    signals_preview = (high_signal_hits + medium_signal_hits)[:6]

    if not missing_classes:
        findings.append(
            Finding(
                "info",
                "formal_evidence_cell_present",
                "Formal-proof vocabulary appears "
                f"(signals={signals_preview}); all evidence-cell anchor classes "
                "present (claim_boundary, receipt, work_item).",
            )
        )
    elif (
        len(missing_classes) == len(FORMAL_EVIDENCE_ANCHOR_CLASSES)
        and high_signal_hits
    ):
        findings.append(
            Finding(
                "error",
                "formal_evidence_overclaim",
                "High-signal formal-proof vocabulary appears "
                f"(signals={high_signal_hits[:6]}) but NO evidence-cell anchors "
                "found in this module (missing all of claim_boundary, receipt, "
                "work_item). Per mathematics_mission_pipeline::Formal Evidence "
                "Cells and std_paper_module::formal_evidence_cells (promotion "
                "ratched to error 2026-05-17 after corpus reached zero "
                "overclaim findings), downgrade to narrative-only or add "
                "claim_boundary + receipt_ref + work_item_id anchors.",
            )
        )
    else:
        findings.append(
            Finding(
                "warning",
                "formal_evidence_cell_missing_anchor",
                "Formal-proof vocabulary appears "
                f"(signals={signals_preview}) but missing evidence-cell anchor "
                f"classes: {missing_classes}. Per mathematics_mission_pipeline::"
                "Formal Evidence Cells, add the missing anchor(s) or move the "
                "language into a clearly bounded narrative section.",
            )
        )

    return findings


def validate_module(
    module: ParsedModule,
    standard: dict[str, Any],
    *,
    repo_root: Path,
    known_slugs: set[str],
    fan_in_inbound: int,
    total_modules: int,
    governing_ids: dict[str, set[str]],
    fact_ledger: dict[str, Any] | None = None,
    strict_fact_audit: bool = False,
    mtime_cache: dict[tuple[str, str], tuple[float, str] | None] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    required = standard["required_sections"]
    required_slugs = [item["slug"] for item in required]
    heading_by_slug = {item["slug"]: item["heading"] for item in required}

    projection_class = module.projection_class
    policy = _projection_policy(standard, projection_class)
    code_loci_body = module.sections.get("code_loci", "")
    code_loci_paths = extract_code_loci_paths(code_loci_body)
    code_loci_rows = _count_table_rows(code_loci_body) or _count_bullet_lines(code_loci_body)
    planned_surfaces = extract_planned_surfaces(module.raw_text)
    cap = int(policy.get("code_loci_cap") or 0)
    deliverables_body = module.sections.get("deliverables", "")
    deliverable_rows = _count_bullet_lines(deliverables_body)
    tldr_body = module.sections.get("tldr", "")
    tldr_count = count_sentences(tldr_body)
    tldr_budget = bracket_for_module(standard, module, fan_in_inbound)
    ontology_body = module.sections.get("ontology", "")
    fact_audit = audit_markdown_fact_claims(
        module.raw_text,
        ledger=fact_ledger or {"facts": []},
        module_slug=module.slug,
        module_file=str(module.file.relative_to(repo_root)),
        strict=strict_fact_audit,
    )

    tldr_preview_text = _first_paragraph(tldr_body)[:320]
    compression_packet = build_compression_packet(module, tldr_preview=tldr_preview_text)

    module.analysis = {
        "code_loci_paths": code_loci_paths,
        "code_loci_rows": code_loci_rows,
        "code_loci_cap": cap,
        "planned_surfaces": planned_surfaces,
        "deliverable_rows": deliverable_rows,
        "tldr_sentence_count": tldr_count,
        "tldr_budget": tldr_budget,
        "deliverables_preview": _extract_bullet_values(deliverables_body, limit=3),
        "tldr_preview": tldr_preview_text,
        "compression": compression_packet,
        "projection_boundary_posture": str(policy.get("boundary_posture") or "").strip() or None,
        "grouped_loci_allowed": bool(policy.get("allows_grouped_loci")),
        "documentation_quality": _documentation_quality_packet(
            module,
            repo_root=repo_root,
            required_slugs=required_slugs,
            deliverable_rows=deliverable_rows,
            tldr_count=tldr_count,
            ontology_body=ontology_body,
        ),
        "fact_audit": fact_audit,
    }
    for compression_finding in compression_packet.get("findings") or []:
        if not isinstance(compression_finding, Mapping):
            continue
        rule = str(compression_finding.get("rule") or "compression_finding")
        actual = compression_finding.get("actual")
        limit = compression_finding.get("limit")
        if actual is not None and limit is not None:
            message = f"Compression budget violation: {rule} actual={actual} limit={limit}."
        else:
            message = f"Compression authoring violation: {rule}."
        findings.append(Finding("warning", rule, message))
    for fact_finding in fact_audit.get("findings") or []:
        if not isinstance(fact_finding, Mapping):
            continue
        findings.append(
            Finding(
                str(fact_finding.get("severity") or "warning"),
                str(fact_finding.get("rule") or "fact_audit_finding"),
                str(fact_finding.get("message") or "Fact audit finding."),
            )
        )

    if not projection_class:
        findings.append(Finding("error", "missing_frontmatter", "Missing 'Projection class:' frontmatter."))
    elif not policy:
        findings.append(Finding("error", "invalid_projection_class", f"Unknown projection_class: {projection_class!r}."))

    if "authored" not in module.frontmatter:
        findings.append(Finding("error", "missing_frontmatter", "Missing 'Authored:' frontmatter."))
    else:
        try:
            datetime.strptime(str(module.frontmatter["authored"]), "%Y-%m-%d")
        except ValueError:
            findings.append(Finding("error", "invalid_authored", f"Authored is not ISO YYYY-MM-DD: {module.frontmatter['authored']!r}."))

    if not module.governing_principles:
        findings.append(Finding("error", "missing_frontmatter", "Missing 'Governing principles:' frontmatter."))
    if not module.governing_concepts:
        findings.append(Finding("error", "missing_frontmatter", "Missing 'Governing concepts:' frontmatter."))

    if policy.get("requires_snapshot_cadence") and not str(module.frontmatter.get("snapshot_cadence") or "").strip():
        findings.append(Finding("error", "snapshot_cadence_required", "Projection class snapshot requires 'Snapshot cadence:' frontmatter."))
    if projection_class == "snapshot" and not DATE_SUFFIX_RE.search(module.slug):
        findings.append(Finding("warning", "snapshot_slug_missing_date", "Snapshot module slug does not end in _YYYY-MM-DD."))
    if policy.get("requires_depends_on") and total_modules > 1 and not module.depends_on:
        findings.append(Finding("error", "root_requires_dependencies", "Projection class root requires a non-empty Depends on: header."))

    for spec in required:
        slug = spec["slug"]
        if slug not in module.sections:
            findings.append(Finding("error", "missing_section", f"Missing required section '## {spec['heading']}' (slug: {slug})."))

    encountered_required = [slug for slug in module.section_order if slug in required_slugs]
    expected_order = [slug for slug in required_slugs if slug in module.sections]
    if encountered_required and encountered_required != expected_order:
        findings.append(
            Finding(
                "warning",
                "section_order_drift",
                f"Required section order drifted: expected {expected_order}, saw {encountered_required}.",
            )
        )

    full_h2_sequence = parse_h2_sequence(module.raw_text, heading_by_slug)
    if full_h2_sequence:
        for idx, slug in enumerate(full_h2_sequence):
            if slug is not None:
                continue
            previous_required = next(
                (item for item in reversed(full_h2_sequence[:idx]) if item is not None),
                None,
            )
            next_required = next(
                (item for item in full_h2_sequence[idx + 1 :] if item is not None),
                None,
            )
            allowed_gap = (
                (previous_required, next_required) == ("code_loci", "current_state")
                or (previous_required, next_required) == ("current_state", "deliverables")
            )
            if not allowed_gap:
                findings.append(
                    Finding(
                        "warning",
                        "section_order_drift",
                        "Supplementary sections may only appear between Code loci and Current state or between Current state and Deliverables.",
                    )
                )
                break

    if not code_loci_body:
        findings.append(Finding("error", "code_loci_empty", "Code loci section is empty."))
    else:
        unresolved: list[str] = []
        preview_paths: list[str] = []
        resolved_paths: list[str] = []
        for candidate in code_loci_paths:
            if (
                "/" not in candidate
                and candidate not in BUILDER_GENERATED_SURFACE_PATHS
                and candidate not in BROAD_CODE_LOCI_FRESHNESS_ROOTS
            ):
                continue
            resolved = resolve_loci_path(repo_root, module.file, candidate)
            if resolved is None:
                unresolved.append(candidate)
                preview_paths.append(candidate)
            else:
                rel_path = str(resolved.relative_to(repo_root))
                preview_paths.append(rel_path)
                resolved_paths.append(rel_path)
        module.analysis["code_loci_unresolved"] = unresolved
        module.analysis["code_loci_preview_paths"] = preview_paths
        module.analysis["code_loci_resolved_paths"] = resolved_paths
        module.analysis["code_loci_freshness"] = _code_loci_freshness_packet(
            module, repo_root=repo_root, mtime_cache=mtime_cache
        )
        if unresolved:
            findings.append(Finding("error", "code_loci_unresolved", f"Code loci path(s) did not resolve ({len(unresolved)}): {unresolved[:5]}"))
        if cap and code_loci_rows > cap:
            findings.append(Finding("warning", "code_loci_cap_exceeded", f"Code loci rows={code_loci_rows} > cap={cap} for projection_class={projection_class}."))

    for row in planned_surfaces:
        candidate = str(row.get("path") or "").strip()
        if not candidate:
            continue
        resolved = resolve_loci_path(repo_root, module.file, candidate)
        row["exists"] = resolved is not None
        if resolved is not None:
            row["resolved_path"] = str(resolved.relative_to(repo_root))
            findings.append(
                Finding(
                    "warning",
                    "planned_surface_resolved",
                    f"Planned surface now resolves and should be promoted out of '{PLANNED_SURFACES_HEADING}': {candidate}",
                )
            )

    min_rows = next((item.get("min_rows") for item in required if item["slug"] == "deliverables"), 3) or 3
    if deliverable_rows < int(min_rows):
        findings.append(Finding("error", "deliverables_below_minimum", f"Deliverables has {deliverable_rows} bullets, minimum is {min_rows}."))

    if ontology_body and not _section_has_table(ontology_body):
        findings.append(Finding("warning", "ontology_prose_only", "Ontology / Types & Invariants contains no markdown table."))

    fixed_budget = policy.get("fixed_tldr_budget")
    if isinstance(fixed_budget, int) and fixed_budget > 0:
        if tldr_count > tldr_budget:
            findings.append(Finding("warning", "tldr_over_budget", f"TLDR has ~{tldr_count} sentences; fixed budget={tldr_budget}."))
        elif tldr_count < tldr_budget:
            findings.append(Finding("warning", "tldr_under_fixed_budget", f"TLDR has ~{tldr_count} sentences; fixed budget={tldr_budget}."))
    else:
        tolerance = 2
        if tldr_count > tldr_budget + tolerance:
            findings.append(Finding("warning", "tldr_over_budget", f"TLDR has ~{tldr_count} sentences; budget={tldr_budget}."))
        elif tldr_budget >= 5 and tldr_count < max(tldr_budget - tolerance, 2):
            findings.append(Finding("info", "tldr_under_bracket", f"TLDR has ~{tldr_count} sentences; budget could support {tldr_budget}."))

    for dep in module.depends_on:
        if dep not in known_slugs:
            findings.append(Finding("error", "depends_on_unknown_slug", f"Depends on '{dep}' but no paper module with that slug exists."))

    lower_body = module.raw_text.lower()
    for heading in ("## proposal", "## redesign", "## roadmap"):
        if heading in lower_body:
            findings.append(Finding("warning", "proposal_smell", f"Found '{heading}' heading; paper modules are projection, not design."))

    known_principles = governing_ids.get("principles", set())
    for principle_id in module.governing_principles:
        if principle_id not in known_principles:
            findings.append(Finding("warning", "unknown_governing_principle", f"Governing principle '{principle_id}' was not found in any raw_seed_principles.json surface."))
    known_concepts = governing_ids.get("concepts", set())
    for concept_id in module.governing_concepts:
        if concept_id not in known_concepts:
            findings.append(Finding("warning", "unknown_governing_concept", f"Governing concept '{concept_id}' was not found under codex/doctrine/concepts/."))
    known_mechanisms = governing_ids.get("mechanisms", set())
    for mechanism_id in module.governing_mechanisms:
        if mechanism_id not in known_mechanisms:
            findings.append(Finding("warning", "unknown_governing_mechanism", f"Governing mechanism '{mechanism_id}' was not found under codex/doctrine/mechanisms/."))

    findings.extend(audit_formal_evidence_cells(module))

    return findings


def classify_status(module: ParsedModule, findings: list[Finding]) -> str:
    error_rules = {item.rule for item in findings if item.severity == "error"}
    warning_rules = {item.rule for item in findings if item.severity == "warning"}

    if "code_loci_unresolved" in error_rules or "depends_on_unknown_slug" in error_rules or "depends_on_cycle" in error_rules:
        return "stale_code_changed"
    if {
        "missing_frontmatter",
        "invalid_projection_class",
        "invalid_authored",
        "snapshot_cadence_required",
        "root_requires_dependencies",
        "missing_section",
    } & error_rules:
        return "stale_schema_v0"
    if "deliverables_below_minimum" in error_rules:
        return "stale_density"
    if {
        "ontology_prose_only",
        "tldr_over_budget",
        "tldr_under_fixed_budget",
        "code_loci_cap_exceeded",
        "section_order_drift",
    } & warning_rules:
        return "stale_density"
    return "up_to_date"


def classify_recommended_action(module: ParsedModule, status: str, findings: list[Finding]) -> tuple[str, str]:
    warning_rules = {item.rule for item in findings if item.severity == "warning"}
    error_rules = {item.rule for item in findings if item.severity == "error"}

    if status == "deprecated":
        return "deprecate", "Module is explicitly deprecated."
    if module.projection_class == "subsystem" and (
        "code_loci_cap_exceeded" in warning_rules or "tldr_over_budget" in warning_rules
    ):
        return "split", "Subsystem boundary exceeds the strict subsystem projection-class budget."
    if status == "stale_current_state":
        return "verify_current_state", "Current-state claims should be revalidated before acting."
    if status in {"stale_schema_v0", "stale_code_changed", "stale_gap_shift"}:
        reason = next((item.message for item in findings if item.severity == "error"), "Structural refresh required.")
        return "refresh", reason
    if status == "stale_density":
        if "code_loci_cap_exceeded" in warning_rules and module.projection_class in {"index", "snapshot", "root"}:
            return "refresh", "Grouped loci or prose density should be tightened without forcing a split."
        reason = next(
            (
                item.message
                for item in findings
                if item.rule in {"ontology_prose_only", "tldr_over_budget", "deliverables_below_minimum", "section_order_drift"}
            ),
            "Density refresh required.",
        )
        return "refresh", reason
    if error_rules:
        return "refresh", next((item.message for item in findings if item.severity == "error"), "Refresh required.")
    return "trust", "Module passes its current projection-class contract."


def classify_action_cause(module: ParsedModule, status: str, findings: list[Finding], recommended_action: str) -> str:
    error_rules = {item.rule for item in findings if item.severity == "error"}
    warning_rules = {item.rule for item in findings if item.severity == "warning"}

    if recommended_action == "deprecate":
        return "deprecated_surface"
    if recommended_action == "first_author":
        return "candidate_gap"
    if recommended_action == "split":
        return "boundary_too_wide"
    if {"depends_on_unknown_slug", "depends_on_cycle"} & error_rules:
        return "dependency_broken"
    if "code_loci_unresolved" in error_rules:
        return "code_loci_broken"
    if status in {"stale_current_state", "stale_gap_shift"}:
        return "freshness_drift"
    if status == "stale_schema_v0" or {
        "missing_frontmatter",
        "invalid_projection_class",
        "invalid_authored",
        "snapshot_cadence_required",
        "root_requires_dependencies",
        "missing_section",
    } & error_rules:
        return "schema_drift"
    if status == "stale_density" or {
        "ontology_prose_only",
        "tldr_over_budget",
        "tldr_under_fixed_budget",
        "code_loci_cap_exceeded",
        "deliverables_below_minimum",
        "section_order_drift",
    } & warning_rules:
        return "density_drift"
    return "trusted"


def _build_boundary_evidence(module: ParsedModule, policy: dict[str, Any], recommended_action: str) -> dict[str, Any]:
    resolved_paths = [str(path) for path in module.analysis.get("code_loci_resolved_paths", []) if str(path).strip()]
    unique_dirs = sorted({str(Path(path).parent) for path in resolved_paths if "/" in path})
    top_level_roots = sorted({path.split("/", 1)[0] for path in resolved_paths if "/" in path})
    row_count = int(module.analysis.get("code_loci_rows") or 0)
    cap = int(module.analysis.get("code_loci_cap") or 0)
    over_cap_by = max(row_count - cap, 0) if cap else 0
    hint = "bounded"
    if recommended_action == "split":
        hint = "split_candidate"
    elif bool(policy.get("allows_grouped_loci")):
        hint = "grouped_browse_surface"
    elif row_count >= cap > 0:
        hint = "at_cap"
    return {
        "code_loci_rows": row_count,
        "code_loci_cap": cap,
        "code_loci_path_count": len(resolved_paths),
        "code_loci_directory_span": len(unique_dirs),
        "code_loci_root_span": len(top_level_roots),
        "grouped_loci_allowed": bool(policy.get("allows_grouped_loci")),
        "projection_boundary_posture": str(policy.get("boundary_posture") or "").strip() or None,
        "over_cap_by": over_cap_by,
        "grouped_loci_hint": hint,
    }


def _hierarchy_context(
    module: ParsedModule,
    *,
    depended_on_by: list[str],
    adjacency: dict[str, list[str]],
    depth_from_root: int,
    distance_to_leaf: int,
) -> dict[str, Any]:
    assembly_input_modules = sorted(adjacency.get(module.slug, []))
    assembled_into_modules = sorted(depended_on_by)
    if assembly_input_modules and not assembled_into_modules:
        assembly_role = "root"
    elif assembly_input_modules and assembled_into_modules:
        assembly_role = "internal"
    elif not assembly_input_modules and assembled_into_modules:
        assembly_role = "leaf"
    else:
        assembly_role = "standalone"

    # pattern: CodeWiki hierarchical documentation — expose the bottom-up assembly packet
    # directly in generated rows so workers can use the module DAG without re-deriving it.
    return {
        "assembly_role": assembly_role,
        "depth_from_root": depth_from_root,
        "distance_to_leaf": distance_to_leaf,
        "assembly_input_modules": assembly_input_modules,
        "assembled_into_modules": assembled_into_modules,
        "dependency_context_available": bool(assembly_input_modules or assembled_into_modules),
        "bottom_up_ready": bool(assembly_input_modules),
        "context_source": "child_modules_plus_code_loci" if assembly_input_modules else "code_loci",
    }


def _module_entry(
    module: ParsedModule,
    *,
    fan_in_inbound: int,
    depended_on_by: list[str],
    adjacency: dict[str, list[str]],
    hierarchy_depths: dict[str, int],
    hierarchy_distances: dict[str, int],
    status: str,
    recommended_action: str,
    action_reason: str,
    action_cause: str,
    repo_root: Path,
    standard: dict[str, Any],
) -> dict[str, Any]:
    cap = int(module.analysis.get("code_loci_cap") or 0)
    rows = int(module.analysis.get("code_loci_rows") or 0)
    boundary_pressure = _boundary_pressure(rows, cap, recommended_action)
    policy = _projection_policy(standard, module.projection_class)
    return {
        "slug": module.slug,
        "title": module.title,
        "file": str(module.file.relative_to(repo_root)),
        "projection_class": module.projection_class,
        "authored": module.authored,
        "depends_on": module.depends_on,
        "depended_on_by": depended_on_by,
        "fan_in_inbound": fan_in_inbound,
        "fan_out_outbound": len(adjacency.get(module.slug, [])),
        "hierarchy_context": _hierarchy_context(
            module,
            depended_on_by=depended_on_by,
            adjacency=adjacency,
            depth_from_root=int(hierarchy_depths.get(module.slug, 0)),
            distance_to_leaf=int(hierarchy_distances.get(module.slug, 0)),
        ),
        "governing_principles": module.governing_principles,
        "governing_concepts": module.governing_concepts,
        "governing_mechanisms": module.governing_mechanisms,
        "search_aliases": module.search_aliases,
        "search_tokens": _search_tokens(module),
        "boundary_pressure": boundary_pressure,
        "boundary_evidence": _build_boundary_evidence(module, policy, recommended_action),
        "status": status,
        "recommended_action": recommended_action,
        "action_reason": action_reason,
        "action_cause": action_cause,
        "tldr_sentence_count_estimate": module.analysis.get("tldr_sentence_count", 0),
        "tldr_budget_bracket": module.analysis.get("tldr_budget", 0),
        "documentation_quality": dict(module.analysis.get("documentation_quality") or {}),
        "fact_audit": dict(module.analysis.get("fact_audit") or {}),
        "code_loci_freshness": dict(module.analysis.get("code_loci_freshness") or {}),
        "planned_surfaces": list(module.analysis.get("planned_surfaces") or []),
        "previews": {
            "tldr": module.analysis.get("tldr_preview", ""),
            "deliverables": list(module.analysis.get("deliverables_preview", [])),
            "code_loci": list(module.analysis.get("code_loci_preview_paths", []))[:10],
            "planned_surfaces": [
                str(row.get("path") or "")
                for row in list(module.analysis.get("planned_surfaces") or [])[:10]
                if str(row.get("path") or "").strip()
            ],
        },
        "compression": dict(module.analysis.get("compression") or {}),
    }


def build_source_manifest(
    *,
    repo_root: Path,
    modules: list[ParsedModule],
    standard_path: Path,
    candidates_path: Path,
) -> dict[str, Any]:
    module_rows = [
        {
            "slug": module.slug,
            "file": str(module.file.relative_to(repo_root)),
            "content_sha256": _sha256_text(module.raw_text),
        }
        for module in modules
    ]
    payload = {
        "schema_version": "paper_module_source_manifest_v1",
        "standard": {
            "path": str(standard_path.relative_to(repo_root)),
            "content_sha256": _sha256_path(standard_path),
        },
        "candidates": {
            "path": str(candidates_path.relative_to(repo_root)),
            "content_sha256": _sha256_path(candidates_path),
        },
        "modules": module_rows,
    }
    payload["source_fingerprint"] = _sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return payload


def _stable_code_loci_freshness_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "resolved_code_loci_count": packet.get("resolved_code_loci_count"),
        "checked_code_loci_count": packet.get("checked_code_loci_count"),
        "ignored_generated_surface_count": packet.get("ignored_generated_surface_count"),
    }


def _code_loci_freshness_fingerprint(modules: list[ParsedModule]) -> str:
    rows = [
        {
            "slug": module.slug,
            "code_loci_freshness": _stable_code_loci_freshness_packet(dict(module.analysis.get("code_loci_freshness") or {})),
        }
        for module in sorted(modules, key=lambda item: item.slug)
    ]
    return _sha256_text(json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def build_generated_freshness(
    *,
    source_manifest: dict[str, Any],
    authored_module_count: int,
    generated_module_count: int,
    standard: dict[str, Any],
    modules: list[ParsedModule],
    timestamp: str,
) -> dict[str, Any]:
    readme_contract = standard.get("readme_projection_contract") if isinstance(standard.get("readme_projection_contract"), Mapping) else {}
    managed_regions = [
        {
            "region_id": str(region.get("region_id") or "").strip(),
            "begin_marker": str(region.get("begin_marker") or "").strip(),
            "end_marker": str(region.get("end_marker") or "").strip(),
        }
        for region in (readme_contract.get("managed_regions") or [])
        if isinstance(region, Mapping)
    ]
    return {
        "sync_status": "in_sync",
        "generated_at": timestamp,
        "generated_at_semantics": "UTC ISO timestamp for when this generated surface was rebuilt from the current authored paper-module source manifest.",
        "source_fingerprint": str(source_manifest.get("source_fingerprint") or "").strip(),
        "code_loci_freshness_fingerprint": _code_loci_freshness_fingerprint(modules),
        "code_loci_freshness_semantics": "Fingerprint of generated module-vs-code-loci resolution structure. Mtime-derived freshness state remains visible advisory metadata but does not make checked-in sidecars stale by itself.",
        "authored_module_count": authored_module_count,
        "generated_module_count": generated_module_count,
        "missing_from_index": [],
        "missing_from_report": [],
        "generated_surface_targets": [
            str(INDEX_PATH.relative_to(REPO_ROOT)),
            str(REPORT_PATH.relative_to(REPO_ROOT)),
            str(DOCTRINE_TO_PAPER_MODULES_PATH.relative_to(REPO_ROOT)),
            str(PAPER_MODULE_ROUTE_COVERAGE_PATH.relative_to(REPO_ROOT)),
        ],
        "managed_readme_projection": {
            "path": str(readme_contract.get("target_path") or "").strip() or str(README_PATH.relative_to(REPO_ROOT)),
            "managed_regions": managed_regions,
        },
    }


def build_doctrine_to_paper_modules_index(
    modules: list[ParsedModule],
    *,
    repo_root: Path,
    timestamp: str,
    source_manifest: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    doctrine_to_paper_modules: dict[str, list[str]] = {}
    paper_module_to_doctrine: dict[str, dict[str, list[str]]] = {}
    doctrine_kind_counts: Counter[str] = Counter()

    for module in modules:
        paper_module_to_doctrine[module.slug] = {
            "governing_principles": list(module.governing_principles),
            "governing_concepts": list(module.governing_concepts),
            "governing_mechanisms": list(module.governing_mechanisms),
        }
        for doctrine_id in module.governing_principles:
            doctrine_to_paper_modules.setdefault(doctrine_id, [])
            if module.slug not in doctrine_to_paper_modules[doctrine_id]:
                doctrine_to_paper_modules[doctrine_id].append(module.slug)
                doctrine_kind_counts["principle"] += 1
        for doctrine_id in module.governing_concepts:
            doctrine_to_paper_modules.setdefault(doctrine_id, [])
            if module.slug not in doctrine_to_paper_modules[doctrine_id]:
                doctrine_to_paper_modules[doctrine_id].append(module.slug)
                doctrine_kind_counts["concept"] += 1
        for doctrine_id in module.governing_mechanisms:
            doctrine_to_paper_modules.setdefault(doctrine_id, [])
            if module.slug not in doctrine_to_paper_modules[doctrine_id]:
                doctrine_to_paper_modules[doctrine_id].append(module.slug)
                doctrine_kind_counts["mechanism"] += 1

    for doctrine_id in list(doctrine_to_paper_modules.keys()):
        doctrine_to_paper_modules[doctrine_id] = sorted(doctrine_to_paper_modules[doctrine_id])

    return {
        "schema_version": "doctrine_to_paper_modules_v1",
        "generated_at": timestamp,
        "source_manifest": source_manifest,
        "freshness": freshness,
        "summary": {
            "doctrine_id_count": len(doctrine_to_paper_modules),
            "paper_module_count": len(modules),
            "edge_count": sum(len(slugs) for slugs in doctrine_to_paper_modules.values()),
            "doctrine_kind_edge_counts": dict(sorted(doctrine_kind_counts.items())),
        },
        "doctrine_to_paper_modules": dict(sorted(doctrine_to_paper_modules.items())),
        "paper_module_to_doctrine": dict(sorted(paper_module_to_doctrine.items())),
    }


ROUTE_SUBDOMAIN_RULES: tuple[dict[str, Any], ...] = (
    {
        "target": "authority_projection",
        "patterns": (
            "raw_seed",
            "raw seed",
            "paper_module",
            "paper module",
            "std_paper_module",
            "codex/doctrine",
            "doctrine",
            "tools/meta/factory",
            "builder",
            "projection",
            "work_ledger",
            "ledger",
        ),
    },
    {
        "target": "navigation_fidelity",
        "patterns": (
            "kernel.py",
            "kernel/",
            "kernel navigation",
            "docs-route",
            "--navigate",
            "hologram",
            "scope_tree",
            "navigation_cache",
            "semantic_routing",
            "semantic routing",
            "query_driven",
            "embedding",
        ),
    },
    {
        "target": "runtime_cockpit",
        "patterns": (
            "station",
            "world_model",
            "system/server",
            "home station",
            "bridge",
            "observe_plan",
            "run_observe_plan",
            "provider",
            "orchestration",
            "control plane",
            "control_plane",
            "reactions",
            "pipeline",
            "apps/",
            "zenith",
            "macos",
        ),
    },
    {
        "target": "visual_observability",
        "patterns": ("frontend", "ui/src", ".tsx", "vite", "react", "visual", "observability"),
    },
    {
        "target": "external_reference_transfer",
        "patterns": ("annex", "annexes/", "annex_", "external", "oss", "import"),
    },
    {
        "target": "observability_safety",
        "patterns": ("watcher", "signal", "telemetry", "approval", "guard", "safety"),
    },
    {
        "target": "surface_language",
        "patterns": ("markdown", "skill", "skill_registry", "skill_map", "prompt", "voice", "agent_seed"),
    },
)

ROUTE_MECHANISM_RULES: tuple[dict[str, Any], ...] = (
    {"target": "mech_003", "patterns": ("bridge", "observe_plan", "provider", "dispatch")},
    {"target": "mech_004", "patterns": ("kernel.py", "kernel/", "--apply", "apply substrate")},
    {"target": "mech_005", "patterns": ("raw_seed_index", "raw_seed.json", "raw seed index", "raw_seed")},
    {"target": "mech_006", "patterns": ("synth_seed", "synth seed", "seed compilation")},
    {"target": "mech_007", "patterns": ("phase_scaffold", "phase lifecycle", "--phase", "wave")},
    {"target": "mech_011", "patterns": ("pipeline_signal", "signal watcher", "watcher")},
    {"target": "mech_012", "patterns": ("resume", "context recovery", "continuation", "handoff")},
    {"target": "mech_015", "patterns": ("annex", "annexes/", "annex assimilation")},
    {"target": "mech_016", "patterns": ("doctrine self", "doctrine improvement", "self-improvement")},
    {"target": "mech_017", "patterns": ("family raw seed", "raw_seed.md", "raw_seed_substrate")},
    {"target": "mech_019", "patterns": ("paper_module", "paper module", "docs-route", "route coverage", "routing")},
    {"target": "mech_021", "patterns": ("orchestration", "control plane", "control_plane", "reactions")},
    {"target": "mech_022", "patterns": ("documentation plane", "artifact routing", "docs route", "paper modules")},
    {"target": "mech_023", "patterns": ("station", "world_model", "frontend", "ui/src")},
    {"target": "mech_027", "patterns": ("skill", "skill_registry", "skill_map")},
    {"target": "mech_028", "patterns": ("hologram", "semantic", "query_driven", "navigation_cache")},
    {"target": "mech_029", "patterns": ("blackboard", "compression", "raw seed")},
)


SATURATED_ROUTE_RESIDUALS: dict[str, dict[str, Any]] = {
    "governing_mechanism:mech_019": {
        "status": "already_captured_residual",
        "recommended_action": "requires_narrower_route",
        "cap_refs": ["cap_quick_split_or_narrow_saturated_mech_019_doctr_826716c90621"],
        "reason": (
            "mech_019 is near the saturation threshold; direct broad additions are blocked by a "
            "captured split/narrow residual until a narrower mechanism or explicit saturation policy lands."
        ),
    },
    "secondary_subdomain:runtime_cockpit": {
        "status": "already_captured_residual",
        "recommended_action": "requires_narrower_route",
        "cap_refs": ["cap_quick_split_or_narrow_saturated_runtime_cockpi_9e00728b4634"],
        "reason": (
            "runtime_cockpit is near the saturation threshold; direct broad secondary edges are blocked by a "
            "captured split/narrow residual until a narrower subdomain or explicit saturation policy lands."
        ),
    },
}


def _route_inference_signal(module: ParsedModule) -> str:
    parts = [
        module.slug,
        module.title,
        " ".join(module.depends_on),
        " ".join(str(item) for item in module.analysis.get("code_loci_preview_paths", [])),
        " ".join(str(item) for item in module.analysis.get("code_loci_resolved_paths", [])),
    ]
    return "\n".join(part for part in parts if str(part).strip()).lower()


def _score_route_rules(signal: str, rules: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for rule in rules:
        target = str(rule.get("target") or "").strip()
        patterns = [str(item).lower() for item in (rule.get("patterns") or []) if str(item).strip()]
        evidence = [pattern for pattern in patterns if pattern in signal]
        if not target or not evidence:
            continue
        score = len(evidence)
        confidence = min(0.95, 0.55 + (score * 0.1))
        scored.append(
            {
                "target": target,
                "confidence": round(confidence, 2),
                "evidence": evidence[:5],
                "score": score,
            }
        )
    return sorted(scored, key=lambda item: (-int(item["score"]), str(item["target"])))


def _infer_route_metadata(module: ParsedModule) -> list[dict[str, Any]]:
    signal = _route_inference_signal(module)
    subdomain_scores = _score_route_rules(signal, ROUTE_SUBDOMAIN_RULES)
    mechanism_scores = _score_route_rules(signal, ROUTE_MECHANISM_RULES)
    suggestions: list[dict[str, Any]] = []
    current_subdomains = [
        str(module.frontmatter.get("primary_subdomain") or "").strip(),
        *[str(item).strip() for item in module.frontmatter.get("secondary_subdomains", []) if str(item).strip()],
    ]
    current_mechanisms = {str(item).strip() for item in module.governing_mechanisms if str(item).strip()}

    missing_primary = not str(module.frontmatter.get("primary_subdomain") or "").strip()
    if missing_primary and subdomain_scores:
        best = subdomain_scores[0]
        suggestions.append(
            {
                "field": "primary_subdomain",
                "suggested_value": best["target"],
                "confidence": best["confidence"],
                "evidence": best["evidence"],
                "reason": "No authored primary subdomain; generated from slug/title/code-loci signals.",
            }
        )

    secondary_candidates = [
        item for item in subdomain_scores[1:4]
        if str(item.get("target") or "") not in current_subdomains
    ]
    if secondary_candidates and len(current_subdomains) < 2:
        suggestions.append(
            {
                "field": "secondary_subdomains",
                "suggested_value": [item["target"] for item in secondary_candidates[:3]],
                "confidence": round(max(float(item["confidence"]) for item in secondary_candidates[:3]), 2),
                "evidence": sorted({evidence for item in secondary_candidates[:3] for evidence in item["evidence"]})[:8],
                "reason": "Secondary route tags would narrow saturated principle/concept routes.",
            }
        )

    mechanism_candidates = [
        item for item in mechanism_scores[:3]
        if str(item.get("target") or "") not in current_mechanisms
    ]
    if not current_mechanisms and mechanism_candidates:
        suggestions.append(
            {
                "field": "governing_mechanisms",
                "suggested_value": [item["target"] for item in mechanism_candidates[:2]],
                "confidence": round(max(float(item["confidence"]) for item in mechanism_candidates[:2]), 2),
                "evidence": sorted({evidence for item in mechanism_candidates[:2] for evidence in item["evidence"]})[:8],
                "reason": "No authored governing mechanism; generated from route and code-loci signals.",
            }
        )
    return suggestions


def build_route_coverage(
    modules: list[ParsedModule],
    *,
    index: dict[str, Any],
    report: dict[str, Any],
    timestamp: str,
    source_manifest: dict[str, Any],
    freshness: dict[str, Any],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    route_to_modules: dict[str, dict[str, Any]] = {}
    suggested_route_to_modules: dict[str, dict[str, Any]] = {}
    paper_module_routes: dict[str, list[dict[str, str]]] = {}
    axis_edge_counts: Counter[str] = Counter()
    suggested_axis_edge_counts: Counter[str] = Counter()
    suggestion_field_counts: Counter[str] = Counter()
    semantic_axes = {
        "governing_principle",
        "governing_concept",
        "governing_mechanism",
        "primary_subdomain",
        "secondary_subdomain",
        "dependency_upstream",
        "dependency_downstream",
    }

    entry_by_slug = {
        str(item.get("slug") or "").strip(): dict(item)
        for item in (index.get("modules") or [])
        if isinstance(item, Mapping) and str(item.get("slug") or "").strip()
    }
    report_by_slug = {
        str(item.get("slug") or "").strip(): dict(item)
        for item in (report.get("modules") or [])
        if isinstance(item, Mapping) and str(item.get("slug") or "").strip()
    }

    def _values(raw: Any) -> list[str]:
        if isinstance(raw, list):
            values = raw
        elif isinstance(raw, str):
            values = [raw]
        else:
            values = []
        return [str(item).strip().strip("`") for item in values if str(item).strip()]

    def _route_key(axis: str, target: str) -> str:
        normalized = re.sub(r"\s+", "_", target.strip())
        normalized = normalized.strip("`")
        return f"{axis}:{normalized}"

    def _add_route(slug: str, axis: str, target: str, *, source: str) -> None:
        target = target.strip().strip("`")
        if not slug or not target:
            return
        key = _route_key(axis, target)
        row = route_to_modules.setdefault(
            key,
            {
                "route_key": key,
                "axis": axis,
                "target": target,
                "source": source,
                "paper_modules": [],
            },
        )
        if slug not in row["paper_modules"]:
            row["paper_modules"].append(slug)
            axis_edge_counts[axis] += 1
        edge = {
            "route_key": key,
            "axis": axis,
            "target": target,
            "source": source,
        }
        bucket = paper_module_routes.setdefault(slug, [])
        if edge not in bucket:
            bucket.append(edge)

    def _add_suggested_route(slug: str, axis: str, target: str, *, suggestion: Mapping[str, Any]) -> dict[str, Any] | None:
        target = target.strip().strip("`")
        if not slug or not target:
            return None
        key = _route_key(axis, target)
        disposition = _suggestion_value_disposition(suggestion, target)
        row = suggested_route_to_modules.setdefault(
            key,
            {
                "route_key": key,
                "axis": axis,
                "target": target,
                "source": "generated_route_inference",
                "paper_modules": [],
                "confidence_by_module": {},
                "status_by_module": {},
            },
        )
        if slug not in row["paper_modules"]:
            row["paper_modules"].append(slug)
            suggested_axis_edge_counts[axis] += 1
        row["confidence_by_module"][slug] = suggestion.get("confidence")
        if disposition:
            row["status_by_module"][slug] = {
                key: value
                for key, value in disposition.items()
                if key
                in {
                    "status",
                    "recommended_action",
                    "route_key",
                    "route_module_count",
                    "saturation_threshold",
                    "saturation_ratio",
                    "reason",
                    "cap_refs",
                }
            }
        edge = {
            "route_key": key,
            "axis": axis,
            "target": target,
            "source": "generated_route_inference",
            "confidence": suggestion.get("confidence"),
            "field": suggestion.get("field"),
        }
        if disposition:
            edge.update(
                {
                    key: value
                    for key, value in disposition.items()
                    if key
                    in {
                        "status",
                        "recommended_action",
                        "route_module_count",
                        "saturation_threshold",
                        "saturation_ratio",
                        "reason",
                        "cap_refs",
                    }
                }
            )
        return edge

    for module in modules:
        entry = entry_by_slug.get(module.slug, {})
        _add_route(module.slug, "projection_class", module.projection_class, source="frontmatter")
        for doctrine_id in module.governing_principles:
            _add_route(module.slug, "governing_principle", doctrine_id, source="frontmatter")
        for doctrine_id in module.governing_concepts:
            _add_route(module.slug, "governing_concept", doctrine_id, source="frontmatter")
        for doctrine_id in module.governing_mechanisms:
            _add_route(module.slug, "governing_mechanism", doctrine_id, source="frontmatter")
        for dependency in module.depends_on:
            _add_route(module.slug, "dependency_upstream", dependency, source="frontmatter")
        for downstream in _values(entry.get("depended_on_by")):
            _add_route(module.slug, "dependency_downstream", downstream, source="derived_dependency_graph")
        for subdomain in _values(module.frontmatter.get("primary_subdomain")):
            _add_route(module.slug, "primary_subdomain", subdomain, source="frontmatter")
        for subdomain in _values(module.frontmatter.get("secondary_subdomains")):
            _add_route(module.slug, "secondary_subdomain", subdomain, source="frontmatter")
        for axis, field in (
            ("status", "status"),
            ("recommended_action", "recommended_action"),
            ("action_cause", "action_cause"),
            ("boundary_pressure", "boundary_pressure"),
        ):
            _add_route(module.slug, axis, str(entry.get(field) or ""), source="generated_validation")

    routes = {
        key: {
            **row,
            "paper_modules": sorted(row["paper_modules"]),
            "module_count": len(row["paper_modules"]),
        }
        for key, row in sorted(route_to_modules.items())
    }
    route_target_counts_by_axis = Counter(str(row["axis"]) for row in routes.values())
    saturation_threshold = max(8, (len(modules) + 3) // 4)
    saturated_route_keys = {
        key
        for key, row in routes.items()
        if str(row.get("axis") or "") in semantic_axes
        and int(row.get("module_count") or 0) >= saturation_threshold
    }

    coverage_by_slug: dict[str, dict[str, Any]] = {}
    missing_mechanism_queue: list[dict[str, Any]] = []
    unclassified_subdomain_queue: list[dict[str, Any]] = []
    thin_route_queue: list[dict[str, Any]] = []
    route_metadata_suggestion_queue: list[dict[str, Any]] = []

    def _suggestion_authority_axis(field: str) -> str:
        if field == "primary_subdomain":
            return "primary_subdomain"
        if field == "secondary_subdomains":
            return "secondary_subdomain"
        if field == "governing_mechanisms":
            return "governing_mechanism"
        return field

    def _suggestion_values(raw_value: Any) -> list[str]:
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        return [str(value).strip().strip("`") for value in values if str(value).strip()]

    def _suggestion_value_disposition(suggestion: Mapping[str, Any], value: str) -> dict[str, Any]:
        field = str(suggestion.get("field") or "").strip()
        axis = _suggestion_authority_axis(field)
        if not axis or not value:
            return {}
        route_key = _route_key(axis, value)
        route = routes.get(route_key) or {}
        if axis in {"primary_subdomain", "secondary_subdomain"}:
            alternate_axis = "secondary_subdomain" if axis == "primary_subdomain" else "primary_subdomain"
            alternate_route_key = _route_key(alternate_axis, value)
            alternate_route = routes.get(alternate_route_key) or {}
            if int(alternate_route.get("module_count") or 0) > int(route.get("module_count") or 0):
                route_key = alternate_route_key
                route = alternate_route
        module_count = int(route.get("module_count") or 0)
        ratio = round(module_count / saturation_threshold, 2) if saturation_threshold else None
        base = {
            "route_key": route_key,
            "route_module_count": module_count,
            "saturation_threshold": saturation_threshold,
            "saturation_ratio": ratio,
        }
        if route_key in SATURATED_ROUTE_RESIDUALS:
            return {**base, **SATURATED_ROUTE_RESIDUALS[route_key]}
        if module_count >= saturation_threshold:
            return {
                **base,
                "status": "blocked_by_saturation",
                "recommended_action": "requires_narrower_route",
                "reason": (
                    "The suggested route target is already at or above the saturation threshold; "
                    "adding more broad edges would reduce route fitness."
                ),
            }
        if module_count >= max(1, saturation_threshold - 2):
            return {
                **base,
                "status": "requires_narrower_route",
                "recommended_action": "use_narrower_route",
                "reason": (
                    "The suggested route target is within two modules of the saturation threshold; "
                    "verify a narrower route before authoring another broad edge."
                ),
            }
        return {}

    def _annotate_route_metadata_suggestion(suggestion: Mapping[str, Any]) -> dict[str, Any]:
        annotated = dict(suggestion)
        dispositions = [
            _suggestion_value_disposition(annotated, value)
            for value in _suggestion_values(annotated.get("suggested_value"))
        ]
        dispositions = [item for item in dispositions if item]
        if not dispositions:
            return annotated
        statuses = {str(item.get("status") or "").strip() for item in dispositions if item.get("status")}
        if statuses == {"already_captured_residual"}:
            suggestion_status = "already_captured_residual"
        elif "blocked_by_saturation" in statuses:
            suggestion_status = "blocked_by_saturation"
        elif "requires_narrower_route" in statuses:
            suggestion_status = "requires_narrower_route"
        else:
            suggestion_status = "partially_reclassified"
        annotated["suggestion_status"] = suggestion_status
        annotated["recommended_action"] = "requires_narrower_route"
        annotated["value_dispositions"] = dispositions
        cap_refs = sorted(
            {
                str(cap_ref)
                for disposition in dispositions
                for cap_ref in (disposition.get("cap_refs") or [])
                if str(cap_ref).strip()
            }
        )
        if cap_refs:
            annotated["cap_refs"] = cap_refs
        return annotated

    def _suggestion_statuses(item: Mapping[str, Any]) -> list[str]:
        statuses: list[str] = []
        for suggestion in item.get("route_metadata_suggestions") or []:
            if not isinstance(suggestion, Mapping):
                continue
            status = str(suggestion.get("suggestion_status") or "").strip()
            if status:
                statuses.append(status)
            for disposition in suggestion.get("value_dispositions") or []:
                if isinstance(disposition, Mapping) and str(disposition.get("status") or "").strip():
                    statuses.append(str(disposition.get("status") or "").strip())
        return statuses

    def _suggestion_cap_refs(item: Mapping[str, Any]) -> list[str]:
        refs: set[str] = set()
        for suggestion in item.get("route_metadata_suggestions") or []:
            if not isinstance(suggestion, Mapping):
                continue
            for cap_ref in suggestion.get("cap_refs") or []:
                if str(cap_ref).strip():
                    refs.add(str(cap_ref).strip())
            for disposition in suggestion.get("value_dispositions") or []:
                if not isinstance(disposition, Mapping):
                    continue
                for cap_ref in disposition.get("cap_refs") or []:
                    if str(cap_ref).strip():
                        refs.add(str(cap_ref).strip())
        return sorted(refs)

    def _route_metadata_suggestion_action(item: Mapping[str, Any]) -> tuple[str, str]:
        statuses = set(_suggestion_statuses(item))
        if "blocked_by_saturation" in statuses:
            return (
                "requires_narrower_route",
                "Generated route metadata includes a saturated target; inspect value_dispositions before authoring.",
            )
        if "already_captured_residual" in statuses:
            return (
                "already_captured_residual",
                "Generated route metadata overlaps a captured saturation residual; resolve the CAP or choose a narrower route before authoring.",
            )
        if "requires_narrower_route" in statuses:
            return (
                "requires_narrower_route",
                "Generated route metadata is near saturation; choose a narrower route before authoring another broad edge.",
            )
        return (
            "author_route_metadata",
            "Generated metadata suggestions exist but are not authored truth.",
        )

    for module in sorted(modules, key=lambda item: item.slug):
        entry = entry_by_slug.get(module.slug, {})
        report_row = report_by_slug.get(module.slug, {})
        route_edges = sorted(paper_module_routes.get(module.slug, []), key=lambda item: item["route_key"])
        semantic_edges = [edge for edge in route_edges if edge["axis"] in semantic_axes]
        saturated_edges = [edge for edge in semantic_edges if edge["route_key"] in saturated_route_keys]
        mechanisms = list(module.governing_mechanisms)
        subdomains = [
            *_values(module.frontmatter.get("primary_subdomain")),
            *_values(module.frontmatter.get("secondary_subdomains")),
        ]
        findings: list[str] = []
        score = 100
        if not mechanisms:
            findings.append("missing_governing_mechanism")
            score -= 20
        if not subdomains:
            findings.append("missing_subdomain_classification")
            score -= 10
        if saturated_edges:
            findings.append("routes_through_saturated_targets")
            score -= min(30, len(saturated_edges) * 5)
        if len(semantic_edges) <= 3:
            findings.append("thin_semantic_route_set")
            score -= 10
        score = max(0, min(100, score))
        suggestions = [
            _annotate_route_metadata_suggestion(suggestion)
            for suggestion in _infer_route_metadata(module)
        ]
        suggested_route_edges: list[dict[str, Any]] = []
        for suggestion in suggestions:
            field = str(suggestion.get("field") or "").strip()
            suggestion_field_counts[field] += 1
            raw_value = suggestion.get("suggested_value")
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            if field == "primary_subdomain":
                axis = "suggested_primary_subdomain"
            elif field == "secondary_subdomains":
                axis = "suggested_secondary_subdomain"
            elif field == "governing_mechanisms":
                axis = "suggested_governing_mechanism"
            else:
                axis = f"suggested_{field}"
            for value in values:
                edge = _add_suggested_route(module.slug, axis, str(value or ""), suggestion=suggestion)
                if edge is not None:
                    suggested_route_edges.append(edge)
        coverage = {
            "slug": module.slug,
            "title": str(entry.get("title") or module.title or "").strip() or None,
            "file": str(entry.get("file") or "").strip() or None,
            "projection_class": module.projection_class,
            "status": str(entry.get("status") or "").strip() or None,
            "recommended_action": str(entry.get("recommended_action") or "").strip() or None,
            "action_cause": str(entry.get("action_cause") or "").strip() or None,
            "boundary_pressure": str(entry.get("boundary_pressure") or "").strip() or None,
            "code_loci_freshness": dict(entry.get("code_loci_freshness") or {}),
            "route_edge_count": len(route_edges),
            "semantic_route_edge_count": len(semantic_edges),
            "saturated_semantic_routes": sorted(edge["route_key"] for edge in saturated_edges),
            "route_metadata_integrity_score": score,
            "route_metadata_findings": findings,
            "route_metadata_suggestions": suggestions,
            "routes": route_edges,
            "suggested_routes": sorted(suggested_route_edges, key=lambda item: str(item.get("route_key") or "")),
            "validation_findings": [
                dict(item)
                for item in (report_row.get("findings") or [])
                if isinstance(item, Mapping)
            ],
        }
        coverage_by_slug[module.slug] = coverage
        if "missing_governing_mechanism" in findings:
            missing_mechanism_queue.append(coverage)
        if "missing_subdomain_classification" in findings:
            unclassified_subdomain_queue.append(coverage)
        if score < 75:
            thin_route_queue.append(coverage)
        if suggestions:
            route_metadata_suggestion_queue.append(coverage)

    def _queue_projection(item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "slug": str(item.get("slug") or "").strip(),
            "title": item.get("title"),
            "file": item.get("file"),
            "projection_class": item.get("projection_class"),
            "status": item.get("status"),
            "recommended_action": item.get("recommended_action"),
            "action_cause": item.get("action_cause"),
            "boundary_pressure": item.get("boundary_pressure"),
            "route_metadata_integrity_score": item.get("route_metadata_integrity_score"),
            "route_metadata_findings": list(item.get("route_metadata_findings") or []),
            "saturated_semantic_routes": list(item.get("saturated_semantic_routes") or []),
            "route_metadata_suggestions": [
                dict(suggestion)
                for suggestion in (item.get("route_metadata_suggestions") or [])
                if isinstance(suggestion, Mapping)
            ],
            "suggested_routes": [
                dict(edge)
                for edge in (item.get("suggested_routes") or [])
                if isinstance(edge, Mapping)
            ],
        }

    def _sort_coverage(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            (_queue_projection(item) for item in items),
            key=lambda item: (
                int(item.get("route_metadata_integrity_score") or 0),
                str(item.get("slug") or ""),
            ),
        )

    split_queue_by_route_pressure: list[dict[str, Any]] = []
    for item in report.get("split_queue") or []:
        if not isinstance(item, Mapping):
            continue
        slug = str(item.get("slug") or "").strip()
        coverage = coverage_by_slug.get(slug)
        if not coverage:
            continue
        split_queue_by_route_pressure.append(
            {
                **_queue_projection(coverage),
                "split_reason": str(item.get("reason") or "").strip() or None,
                "priority": item.get("priority"),
            }
        )
    split_queue_by_route_pressure.sort(
        key=lambda item: (
            int(item.get("priority") or 99),
            int(item.get("route_metadata_integrity_score") or 0),
            str(item.get("slug") or ""),
        )
    )

    # By-construction saturated routes: canonical references named in
    # codex/standards/std_paper_module.json::example and at the corpus-wide
    # posture level (CLAUDE.md anchors pri_049). High module_count on these
    # keys is the intended shape, not drift; suppress them from the
    # operator-facing queue while preserving analytical signal in
    # saturated_route_keys (per-module findings, route_health, pressure).
    #
    # Apex flagging composes two sources:
    #   1. The legacy hardcoded set below (retained for pri_049/pri_111 etc.
    #      where the apex source lives in raw_seed_principles.json).
    #   2. `is_apex: true` on doctrine concept/principle JSON files. The
    #      route_key is derived as `governing_concept:<id>` /
    #      `governing_principle:<id>` so the route_coverage builder can
    #      pick up new apex flags without code changes.
    legacy_hardcoded_apex = frozenset({
        "governing_principle:pri_111",
        "governing_principle:pri_049",
        "governing_concept:con_001",
        "governing_concept:con_028",
    })
    apex_governing_ids: dict[str, set[str]] = {}
    if repo_root is not None:
        try:
            apex_governing_ids = _load_governing_ids(repo_root)
        except Exception:
            apex_governing_ids = {}
    apex_concept_route_keys = {
        f"governing_concept:{concept_id}"
        for concept_id in apex_governing_ids.get("apex_concepts") or set()
    }
    apex_principle_route_keys = {
        f"governing_principle:{principle_id}"
        for principle_id in apex_governing_ids.get("apex_principles") or set()
    }
    by_construction_saturated = frozenset(
        legacy_hardcoded_apex | apex_concept_route_keys | apex_principle_route_keys
    )
    route_saturation_queue = [
        {
            "route_key": key,
            "axis": str(row.get("axis") or ""),
            "target": str(row.get("target") or ""),
            "module_count": int(row.get("module_count") or 0),
            "saturation_threshold": saturation_threshold,
            "paper_modules": list(row.get("paper_modules") or []),
            "is_apex": False,
        }
        for key, row in routes.items()
        if key in saturated_route_keys and key not in by_construction_saturated
    ]
    route_saturation_queue.sort(key=lambda item: (-int(item["module_count"]), item["route_key"]))
    # Apex saturation queue (info-only): rows suppressed from the repair
    # queue because the saturation is by-construction at apex routes.
    # Distinguishes apex-from-flag (doctrine `is_apex: true`) vs
    # apex-from-legacy-hardcode for transparency during migration.
    apex_saturation_queue = [
        {
            "route_key": key,
            "axis": str(row.get("axis") or ""),
            "target": str(row.get("target") or ""),
            "module_count": int(row.get("module_count") or 0),
            "saturation_threshold": saturation_threshold,
            "paper_modules": list(row.get("paper_modules") or []),
            "is_apex": True,
            "apex_source": (
                "doctrine_is_apex_flag"
                if key in (apex_concept_route_keys | apex_principle_route_keys)
                else "legacy_hardcoded_apex"
            ),
        }
        for key, row in routes.items()
        if key in saturated_route_keys and key in by_construction_saturated
    ]
    apex_saturation_queue.sort(key=lambda item: (-int(item["module_count"]), item["route_key"]))

    def _route_health_module_projection(item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "slug": str(item.get("slug") or "").strip(),
            "title": item.get("title"),
            "file": item.get("file"),
            "status": item.get("status"),
            "recommended_action": item.get("recommended_action"),
            "boundary_pressure": item.get("boundary_pressure"),
            "route_metadata_integrity_score": item.get("route_metadata_integrity_score"),
            "route_metadata_findings": list(item.get("route_metadata_findings") or []),
            "suggestion_count": len(
                [
                    suggestion
                    for suggestion in (item.get("route_metadata_suggestions") or [])
                    if isinstance(suggestion, Mapping)
                ]
            ),
        }

    def _route_health_action(
        *,
        saturated: bool,
        split_required_count: int,
        missing_metadata_count: int,
        suggestion_count: int,
        stale_density_count: int,
        refresh_count: int,
        thin_route_count: int,
    ) -> str:
        if split_required_count:
            return "split_or_reclassify_route"
        if missing_metadata_count and suggestion_count:
            return "author_route_metadata"
        if stale_density_count or refresh_count:
            return "refresh_modules"
        if saturated:
            return "add_more_specific_routes"
        if thin_route_count:
            return "tighten_route_metadata"
        return "trust_route"

    route_health: dict[str, dict[str, Any]] = {}
    for key, row in routes.items():
        module_coverages = [
            coverage_by_slug[slug]
            for slug in (row.get("paper_modules") or [])
            if slug in coverage_by_slug
        ]
        if not module_coverages:
            continue
        module_count = len(module_coverages)
        split_required_count = sum(
            1
            for item in module_coverages
            if str(item.get("recommended_action") or "") == "split"
            or str(item.get("boundary_pressure") or "") == "split_required"
        )
        refresh_count = sum(
            1
            for item in module_coverages
            if str(item.get("recommended_action") or "") in {"refresh", "verify_current_state"}
        )
        stale_density_count = sum(
            1
            for item in module_coverages
            if str(item.get("status") or "") == "stale_density"
        )
        missing_mechanism_count = sum(
            1
            for item in module_coverages
            if "missing_governing_mechanism" in set(item.get("route_metadata_findings") or [])
        )
        missing_subdomain_count = sum(
            1
            for item in module_coverages
            if "missing_subdomain_classification" in set(item.get("route_metadata_findings") or [])
        )
        thin_route_count = sum(
            1
            for item in module_coverages
            if "thin_semantic_route_set" in set(item.get("route_metadata_findings") or [])
            or int(item.get("route_metadata_integrity_score") or 100) < 75
        )
        suggestion_count = sum(
            len(
                [
                    suggestion
                    for suggestion in (item.get("route_metadata_suggestions") or [])
                    if isinstance(suggestion, Mapping)
                ]
            )
            for item in module_coverages
        )
        trusted_count = sum(
            1
            for item in module_coverages
            if str(item.get("recommended_action") or "") == "trust"
            and str(item.get("status") or "") == "up_to_date"
        )
        route_integrity_average = round(
            sum(int(item.get("route_metadata_integrity_score") or 0) for item in module_coverages) / module_count,
            2,
        )
        saturated = key in saturated_route_keys
        pressure_reasons: list[str] = []
        if saturated:
            pressure_reasons.append("route_saturation")
        if split_required_count:
            pressure_reasons.append("split_required_modules")
        if missing_mechanism_count:
            pressure_reasons.append("missing_governing_mechanism")
        if missing_subdomain_count:
            pressure_reasons.append("missing_subdomain_classification")
        if stale_density_count or refresh_count:
            pressure_reasons.append("stale_or_refresh_pressure")
        if thin_route_count:
            pressure_reasons.append("thin_route_metadata")
        saturation_penalty = 20 if saturated else 0
        health_score = max(
            0,
            min(
                100,
                100
                - saturation_penalty
                - round(30 * split_required_count / module_count)
                - round(15 * stale_density_count / module_count)
                - round(10 * refresh_count / module_count)
                - round(15 * missing_mechanism_count / module_count)
                - round(10 * missing_subdomain_count / module_count)
                - round(10 * thin_route_count / module_count),
            ),
        )
        missing_metadata_count = missing_mechanism_count + missing_subdomain_count
        recommended_next_action = _route_health_action(
            saturated=saturated,
            split_required_count=split_required_count,
            missing_metadata_count=missing_metadata_count,
            suggestion_count=suggestion_count,
            stale_density_count=stale_density_count,
            refresh_count=refresh_count,
            thin_route_count=thin_route_count,
        )
        ranked_modules = sorted(
            (_route_health_module_projection(item) for item in module_coverages),
            key=lambda item: (
                int(item.get("route_metadata_integrity_score") or 0),
                0 if item.get("boundary_pressure") == "split_required" else 1,
                str(item.get("slug") or ""),
            ),
        )
        route_health[key] = {
            "route_key": key,
            "axis": str(row.get("axis") or ""),
            "target": str(row.get("target") or ""),
            "source": str(row.get("source") or ""),
            "semantic_axis": str(row.get("axis") or "") in semantic_axes,
            "saturated": saturated,
            "module_count": module_count,
            "saturation_threshold": saturation_threshold,
            "saturation_ratio": round(module_count / saturation_threshold, 2) if saturation_threshold else None,
            "health_score": health_score,
            "recommended_next_action": recommended_next_action,
            "pressure_reasons": pressure_reasons,
            "route_integrity_average": route_integrity_average,
            "split_required_count": split_required_count,
            "refresh_count": refresh_count,
            "stale_density_count": stale_density_count,
            "trusted_count": trusted_count,
            "missing_mechanism_count": missing_mechanism_count,
            "missing_subdomain_count": missing_subdomain_count,
            "thin_route_count": thin_route_count,
            "suggestion_count": suggestion_count,
            "top_modules": ranked_modules[:10],
        }

    route_health_queue = [
        dict(row)
        for row in route_health.values()
        if row.get("recommended_next_action") != "trust_route"
    ]
    route_health_queue.sort(
        key=lambda item: (
            int(item.get("health_score") or 100),
            -int(item.get("module_count") or 0),
            str(item.get("route_key") or ""),
        )
    )

    suggested_routes = {
        key: {
            **row,
            "paper_modules": sorted(row["paper_modules"]),
            "module_count": len(row["paper_modules"]),
            "confidence_by_module": dict(sorted(row.get("confidence_by_module", {}).items())),
            "status_by_module": dict(sorted(row.get("status_by_module", {}).items())),
        }
        for key, row in sorted(suggested_route_to_modules.items())
    }
    route_metadata_suggestion_queue_sorted = sorted(
        (_queue_projection(item) for item in route_metadata_suggestion_queue),
        key=lambda item: (
            int(item.get("route_metadata_integrity_score") or 0),
            -max(
                [float(suggestion.get("confidence") or 0) for suggestion in item.get("route_metadata_suggestions") or []]
                or [0.0]
            ),
            str(item.get("slug") or ""),
        ),
    )

    semantic_routed_count = sum(
        1
        for item in coverage_by_slug.values()
        if int(item.get("semantic_route_edge_count") or 0) > 0
    )
    attention = {
        "route_saturation_queue": route_saturation_queue[:24],
        "apex_saturation_queue": apex_saturation_queue[:24],
        "thin_route_queue": _sort_coverage(thin_route_queue)[:24],
        "missing_mechanism_queue": _sort_coverage(missing_mechanism_queue)[:24],
        "unclassified_subdomain_queue": _sort_coverage(unclassified_subdomain_queue)[:24],
        "split_queue_by_route_pressure": split_queue_by_route_pressure[:24],
        "route_metadata_suggestion_queue": route_metadata_suggestion_queue_sorted[:24],
        "route_health_queue": route_health_queue[:24],
    }
    route_metadata_scores = [
        int(item.get("route_metadata_integrity_score") or 0)
        for item in coverage_by_slug.values()
    ]
    route_metadata_integrity_average = (
        round(sum(route_metadata_scores) / len(route_metadata_scores), 2)
        if route_metadata_scores
        else 0.0
    )
    suggestion_status_counts: Counter[str] = Counter()
    suggestion_value_status_counts: Counter[str] = Counter()
    for item in coverage_by_slug.values():
        for suggestion in item.get("route_metadata_suggestions") or []:
            if not isinstance(suggestion, Mapping):
                continue
            suggestion_status_counts[str(suggestion.get("suggestion_status") or "generated_unreviewed")] += 1
            for disposition in suggestion.get("value_dispositions") or []:
                if not isinstance(disposition, Mapping):
                    continue
                status = str(disposition.get("status") or "").strip()
                if status:
                    suggestion_value_status_counts[status] += 1
    low_integrity_module_count = sum(1 for score in route_metadata_scores if score < 75)
    missing_route_metadata_module_count = len(
        {
            str(item.get("slug") or "").strip()
            for item in (*missing_mechanism_queue, *unclassified_subdomain_queue)
            if str(item.get("slug") or "").strip()
        }
    )
    split_required_module_count = sum(
        1
        for item in coverage_by_slug.values()
        if str(item.get("recommended_action") or "") == "split"
        or str(item.get("boundary_pressure") or "") == "split_required"
    )
    stale_density_module_count = sum(
        1
        for item in coverage_by_slug.values()
        if str(item.get("status") or "") == "stale_density"
    )
    route_population_score = int(round(route_metadata_integrity_average))

    population_targets: list[dict[str, Any]] = []
    seen_population_targets: set[str] = set()

    def _append_population_target(
        *,
        target_kind: str,
        item: Mapping[str, Any],
        source_queue: str,
        recommended_action: str,
        reason: str,
    ) -> None:
        if len(population_targets) >= 12:
            return
        route_key = str(item.get("route_key") or "").strip()
        slug = str(item.get("slug") or "").strip()
        identity = route_key or slug
        if not identity:
            return
        dedupe_key = f"{target_kind}:{identity}"
        if dedupe_key in seen_population_targets:
            return
        seen_population_targets.add(dedupe_key)
        command = (
            f"python3 kernel.py --paper-module-route {route_key}"
            if route_key
            else f"python3 kernel.py --paper-module {slug}"
        )
        row = {
            "rank": len(population_targets) + 1,
            "target_kind": target_kind,
            "route_key": route_key or None,
            "slug": slug or None,
            "title": item.get("title"),
            "source_queue": source_queue,
            "recommended_action": recommended_action,
            "reason": reason,
            "score": item.get("health_score") or item.get("route_metadata_integrity_score"),
            "pressure_reasons": list(item.get("pressure_reasons") or item.get("route_metadata_findings") or [])[:6],
            "command": command,
        }
        suggestion_statuses = sorted(set(_suggestion_statuses(item)))
        if suggestion_statuses:
            row["route_metadata_suggestion_statuses"] = suggestion_statuses
        cap_refs = _suggestion_cap_refs(item)
        if cap_refs:
            row["cap_refs"] = cap_refs
        population_targets.append(row)

    for item in route_metadata_suggestion_queue_sorted[:6]:
        recommended_action, reason = _route_metadata_suggestion_action(item)
        _append_population_target(
            target_kind="module",
            item=item,
            source_queue="route_metadata_suggestion_queue",
            recommended_action=recommended_action,
            reason=reason,
        )
    for item in route_health_queue[:6]:
        _append_population_target(
            target_kind="route",
            item=item,
            source_queue="route_health_queue",
            recommended_action=str(item.get("recommended_next_action") or "inspect_route"),
            reason="Route health is below trust threshold or carries pressure reasons.",
        )
    for item in split_queue_by_route_pressure[:6]:
        _append_population_target(
            target_kind="module",
            item=item,
            source_queue="split_queue_by_route_pressure",
            recommended_action="split_or_reclassify_route",
            reason="Module boundary pressure affects route quality.",
        )
    for item in _sort_coverage(thin_route_queue)[:6]:
        _append_population_target(
            target_kind="module",
            item=item,
            source_queue="thin_route_queue",
            recommended_action="tighten_route_metadata",
            reason="Module has a thin semantic route set or low route metadata integrity.",
        )

    metabolism_worklist = {
        "schema_version": "paper_module_metabolism_worklist_v1",
        "metric": {
            "name": "paper_module_route_population_score",
            "score": route_population_score,
            "score_semantics": "Average module route_metadata_integrity_score, rounded to an integer. Higher is better; pressure queues explain what to populate next.",
            "route_metadata_integrity_average": route_metadata_integrity_average,
            "low_integrity_module_count": low_integrity_module_count,
            "missing_route_metadata_module_count": missing_route_metadata_module_count,
            "split_required_module_count": split_required_module_count,
            "stale_density_module_count": stale_density_module_count,
            "next_population_target_count": len(population_targets),
        },
        "separation_of_concerns": {
            "describing_source": "codex/doctrine/paper_modules/*.md",
            "routing_source": "codex/doctrine/paper_modules/_route_coverage.json",
            "semantic_retrieval_source": "state/embeddings/paper_modules.json",
        },
        "consumer_commands": {
            "coverage": "python3 kernel.py --paper-module-coverage",
            "route_lookup": "python3 kernel.py --paper-module-route <route_key-or-target>",
            "refresh_sidecars": "./repo-python tools/meta/factory/build_paper_module_index.py",
            "refresh_embeddings": "python3 kernel.py --embed-refresh paper_modules",
        },
        "next_population_targets": population_targets,
    }
    route_graph_fingerprint = _sha256_text(
        json.dumps(
            {
                "routes": routes,
                "suggested_routes": suggested_routes,
                "paper_module_routes": {
                    slug: {
                        "routes": item.get("routes"),
                        "suggested_routes": item.get("suggested_routes"),
                        "route_metadata_findings": item.get("route_metadata_findings"),
                        "route_metadata_suggestions": item.get("route_metadata_suggestions"),
                    }
                    for slug, item in sorted(coverage_by_slug.items())
                },
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    code_family_coverage = build_code_family_coverage(
        modules,
        repo_root=repo_root if repo_root is not None else REPO_ROOT,
        timestamp=timestamp,
    )
    route_attention_queue_fingerprint = _sha256_text(
        json.dumps(attention, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )
    route_health_fingerprint = _sha256_text(
        json.dumps(route_health, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )
    metabolism_worklist_fingerprint = _sha256_text(
        json.dumps(metabolism_worklist, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )

    return {
        "schema_version": "paper_module_route_coverage_v4",
        "generated_at": timestamp,
        "source_manifest": source_manifest,
        "freshness": freshness,
        "fingerprints": {
            "route_graph_fingerprint": route_graph_fingerprint,
            "route_attention_queue_fingerprint": route_attention_queue_fingerprint,
            "route_health_fingerprint": route_health_fingerprint,
            "metabolism_worklist_fingerprint": metabolism_worklist_fingerprint,
        },
        "summary": {
            "module_count": len(modules),
            "routed_module_count": semantic_routed_count,
            "unrouted_module_count": len(modules) - semantic_routed_count,
            "route_target_count": len(routes),
            "route_edge_count": sum(len(items) for items in paper_module_routes.values()),
            "route_health_target_count": len(route_health),
            "route_health_attention_count": len(route_health_queue),
            "semantic_route_edge_count": sum(
                int(item.get("semantic_route_edge_count") or 0)
                for item in coverage_by_slug.values()
            ),
            "suggested_route_target_count": len(suggested_routes),
            "suggested_route_edge_count": sum(len(items.get("suggested_routes") or []) for items in coverage_by_slug.values()),
            "route_axis_edge_counts": dict(sorted(axis_edge_counts.items())),
            "suggested_route_axis_edge_counts": dict(sorted(suggested_axis_edge_counts.items())),
            "route_target_counts_by_axis": dict(sorted(route_target_counts_by_axis.items())),
            "suggestion_counts_by_field": dict(sorted(suggestion_field_counts.items())),
            "suggestion_status_counts": dict(sorted(suggestion_status_counts.items())),
            "suggestion_value_status_counts": dict(sorted(suggestion_value_status_counts.items())),
            "suggestable_missing_mechanism_count": len(
                [
                    item for item in missing_mechanism_queue
                    if item.get("route_metadata_suggestions")
                ]
            ),
            "suggestable_unclassified_subdomain_count": len(
                [
                    item for item in unclassified_subdomain_queue
                    if item.get("route_metadata_suggestions")
                ]
            ),
            "saturation_threshold": saturation_threshold,
            "route_metadata_integrity_average": route_metadata_integrity_average,
            "route_population_score": route_population_score,
            "low_integrity_module_count": low_integrity_module_count,
            "missing_route_metadata_module_count": missing_route_metadata_module_count,
            "split_required_module_count": split_required_module_count,
            "stale_density_module_count": stale_density_module_count,
            "next_population_target_count": len(population_targets),
            "attention_queue_counts": {
                "route_saturation_queue": len(route_saturation_queue),
                "apex_saturation_queue": len(apex_saturation_queue),
                "thin_route_queue": len(thin_route_queue),
                "missing_mechanism_queue": len(missing_mechanism_queue),
                "unclassified_subdomain_queue": len(unclassified_subdomain_queue),
                "split_queue_by_route_pressure": len(split_queue_by_route_pressure),
                "route_metadata_suggestion_queue": len(route_metadata_suggestion_queue),
                "route_health_queue": len(route_health_queue),
                "unmapped_code_family_queue": len(
                    code_family_coverage.get("queues", {}).get("unmapped_code_family_queue", [])
                ),
                "weakly_mapped_code_family_queue": len(
                    code_family_coverage.get("queues", {}).get("weakly_mapped_code_family_queue", [])
                ),
                "large_family_needs_index_queue": len(
                    code_family_coverage.get("queues", {}).get("large_family_needs_index_queue", [])
                ),
            },
            "code_family_coverage_counts": dict(
                (code_family_coverage.get("summary") or {}).get("status_counts") or {}
            ),
            "code_family_material_count": int(
                (code_family_coverage.get("summary") or {}).get("material_family_count") or 0
            ),
        },
        "routes": routes,
        "route_health": route_health,
        "suggested_routes": suggested_routes,
        "paper_module_routes": coverage_by_slug,
        "attention": attention,
        "metabolism_worklist": metabolism_worklist,
        "code_family_coverage": code_family_coverage,
    }


def _count_python_loc(path: Path) -> int:
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def _iter_python_families(repo_root: Path, roots: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    """Enumerate directories under each root that directly contain `.py` files.

    Materiality filtering happens in the classifier; this helper just counts files,
    sums LOC, and exposes representative file names. Excluded segments and prefixes
    are pruned during the walk so generated / vendored / observe-dump roots cannot
    inflate the gap counts.
    """
    families: dict[str, dict[str, Any]] = {}
    resolved_root = repo_root.resolve()
    for root_name in roots:
        root_path = resolved_root / root_name
        if not root_path.is_dir():
            continue
        for current, dirnames, filenames in os.walk(root_path):
            current_path = Path(current)
            try:
                rel_dir = current_path.resolve().relative_to(resolved_root)
            except ValueError:
                dirnames.clear()
                continue
            rel_str = rel_dir.as_posix()
            if any(seg in CODE_FAMILY_EXCLUDED_SEGMENTS for seg in rel_dir.parts):
                dirnames.clear()
                continue
            if any(
                rel_str == prefix.rstrip("/") or rel_str.startswith(prefix)
                for prefix in CODE_FAMILY_EXCLUDED_PREFIXES
            ):
                dirnames.clear()
                continue
            dirnames[:] = [d for d in dirnames if d not in CODE_FAMILY_EXCLUDED_SEGMENTS]
            py_files = sorted(name for name in filenames if name.endswith(".py"))
            if not py_files:
                continue
            py_loc = 0
            representatives: list[str] = []
            for name in py_files:
                py_loc += _count_python_loc(current_path / name)
                if len(representatives) < CODE_FAMILY_REPRESENTATIVE_FILE_CAP:
                    representatives.append((rel_dir / name).as_posix())
            families[rel_str] = {
                "family_path": rel_str,
                "py_file_count": len(py_files),
                "py_loc": py_loc,
                "representative_files": representatives,
            }
    return families


def _build_loci_ownership(
    modules: list[ParsedModule], repo_root: Path
) -> dict[str, list[dict[str, Any]]]:
    """Map family_path -> list of module ownership rows from authored code_loci.

    Each entry's `evidence_paths` is the list of repo-relative file paths from the
    module's code_loci that resolved into that family directory. The family key is
    the parent directory of the resolved file, so a module that cites
    `tools/meta/testing/test_inventory.py` becomes an owner of family
    `tools/meta/testing`. Directory tokens (e.g. `tools/meta/`) are intentionally
    ignored here — they overclaim parent-ownership of every sibling subtree, which
    is exactly the false-negative shape this builder is here to expose.
    """
    ownership: dict[str, dict[str, dict[str, Any]]] = {}
    resolved_root = repo_root.resolve()
    for module in modules:
        slug = module.slug
        projection_class = module.projection_class
        resolved = module.analysis.get("code_loci_resolved_paths") or []
        for resolved_path in resolved:
            # code_loci_resolved_paths are repo-relative strings (see validate_module).
            # Anchor at repo_root before resolving so the is_file() check works under
            # tests / alternate repo roots, not just CWD-rooted runs.
            absolute_pathobj = (resolved_root / resolved_path).resolve()
            try:
                rel = absolute_pathobj.relative_to(resolved_root)
            except (ValueError, OSError):
                continue
            rel_str = rel.as_posix()
            if not rel_str:
                continue
            try:
                if not absolute_pathobj.is_file():
                    # Skip directory tokens; they generate spurious parent-ownership.
                    continue
            except OSError:
                continue
            parent = rel.parent.as_posix()
            if parent in {"", "."}:
                continue
            family_record = ownership.setdefault(parent, {})
            entry = family_record.setdefault(
                slug,
                {
                    "slug": slug,
                    "projection_class": projection_class,
                    "evidence_paths": [],
                },
            )
            entry["evidence_paths"].append(rel_str)
    return {key: list(value.values()) for key, value in ownership.items()}


def build_code_family_coverage(
    modules: list[ParsedModule],
    *,
    repo_root: Path,
    timestamp: str,
) -> dict[str, Any]:
    """Enumerate material Python code families and classify their paper-module ownership.

    Implements the bidirectional half of paper-module coverage governance per CAP
    `cap_quick_paper_module_coverage_false_negative_cle_87d3ece5d8b4` (event
    `wie_20260517T061820Z_484f5726`). The existing `_validation_report.json` queues
    validate authored documentation against generated sidecars; this function
    validates the inverse direction by enumerating Python implementation families
    under `system/` and `tools/` and classifying each against authored
    `code_loci` ownership.

    Status FSM per family:
      - `owned_by_module`: a subsystem module's code_loci file lives inside the family.
      - `owned_by_index`: an index/root module's code_loci file lives inside the family.
      - `owned_by_refinement`: only a strict parent directory is cited; the family
        itself isn't directly mentioned in any module's code_loci.
      - `candidate_gap`: material family with no owner; suggestable for first authoring.
      - `unknown_unmapped`: material family that is also large by file/LOC and has no
        owner — the coverage failure class. Invariant: `first_author_queue=0` cannot
        imply full Python-substrate coverage unless `unmapped_code_family_queue=0`.
      - `intentional_exclusion`: directory is below the materiality threshold.

    Saturation routing (`blocked_by_saturation`) is reserved for a later wave once
    route-saturation policy is wired in.
    """
    families = _iter_python_families(repo_root, CODE_FAMILY_ROOTS)
    loci_ownership = _build_loci_ownership(modules, repo_root)

    materiality_policy: dict[str, Any] = {
        "min_py_files": CODE_FAMILY_MIN_PY_FILES,
        "min_py_loc": CODE_FAMILY_MIN_PY_LOC,
        "large_threshold_files": CODE_FAMILY_LARGE_PY_FILES,
        "large_threshold_loc": CODE_FAMILY_LARGE_PY_LOC,
        "excluded_segments": sorted(CODE_FAMILY_EXCLUDED_SEGMENTS),
        "excluded_prefixes": list(CODE_FAMILY_EXCLUDED_PREFIXES),
        "index_projection_classes": sorted(CODE_FAMILY_INDEX_PROJECTION_CLASSES),
    }

    classified_families: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()

    for family_path, family_info in sorted(families.items()):
        py_files = int(family_info["py_file_count"])
        py_loc = int(family_info["py_loc"])
        is_material = (
            py_files >= CODE_FAMILY_MIN_PY_FILES or py_loc >= CODE_FAMILY_MIN_PY_LOC
        )
        is_large = (
            py_files >= CODE_FAMILY_LARGE_PY_FILES or py_loc >= CODE_FAMILY_LARGE_PY_LOC
        )
        is_fixture_subtree = (
            any(
                segment in ("fixtures", "fixture")
                for segment in family_path.split("/")
            )
            and not is_large
        )

        direct_owners: list[dict[str, Any]] = []
        nested_owners: list[dict[str, Any]] = []
        for owning_dir, owners in loci_ownership.items():
            if owning_dir == family_path:
                direct_owners.extend(owners)
            elif owning_dir.startswith(family_path + "/"):
                nested_owners.extend(owners)

        parts = family_path.split("/")
        parent_owners: list[dict[str, Any]] = []
        for index in range(1, len(parts)):
            candidate_parent = "/".join(parts[:index])
            if candidate_parent in loci_ownership:
                parent_owners.extend(loci_ownership[candidate_parent])

        all_direct = direct_owners + nested_owners
        index_owners = [
            owner
            for owner in all_direct
            if owner.get("projection_class") in CODE_FAMILY_INDEX_PROJECTION_CLASSES
        ]
        subsystem_owners = [
            owner
            for owner in all_direct
            if owner.get("projection_class") not in CODE_FAMILY_INDEX_PROJECTION_CLASSES
        ]

        if not is_material:
            status = "intentional_exclusion"
            evidence = ["below_materiality_threshold"]
            recommended_action = "record_exclusion"
        elif is_fixture_subtree and not subsystem_owners and not index_owners:
            status = "intentional_exclusion"
            evidence = ["fixture_subtree_below_large_threshold"]
            recommended_action = "record_exclusion"
        elif subsystem_owners:
            status = "owned_by_module"
            evidence = ["code_loci_path_containment", "subsystem_module_slug_match"]
            recommended_action = "trust"
        elif index_owners:
            status = "owned_by_index"
            evidence = ["code_loci_path_containment", "index_module_routes_family"]
            recommended_action = "trust_index"
        elif parent_owners:
            status = "owned_by_refinement"
            evidence = ["parent_directory_owned", "family_path_not_directly_cited"]
            recommended_action = "refine_module"
        elif is_large:
            status = "unknown_unmapped"
            evidence = ["no_direct_or_parent_owner", "exceeds_large_threshold"]
            recommended_action = "coverage_failure"
        else:
            status = "candidate_gap"
            evidence = ["no_direct_or_parent_owner", "meets_materiality"]
            recommended_action = "author_or_candidate"

        owner_module_slugs = sorted({owner["slug"] for owner in all_direct})
        parent_owner_slugs = sorted({owner["slug"] for owner in parent_owners})
        index_owner_slugs = sorted({owner["slug"] for owner in index_owners})
        subsystem_owner_slugs = sorted({owner["slug"] for owner in subsystem_owners})

        classified_families.append(
            {
                "family_path": family_path,
                "py_file_count": py_files,
                "py_loc": py_loc,
                "representative_files": list(family_info["representative_files"]),
                "owner_modules": owner_module_slugs,
                "parent_owner_modules": parent_owner_slugs,
                "index_owner_modules": index_owner_slugs,
                "subsystem_owner_modules": subsystem_owner_slugs,
                "ownership_status": status,
                "evidence": evidence,
                "recommended_action": recommended_action,
                "is_material": is_material,
                "is_large": is_large,
            }
        )
        status_counts[status] += 1

    unmapped_queue = [
        {
            "family_path": item["family_path"],
            "py_file_count": item["py_file_count"],
            "py_loc": item["py_loc"],
            "representative_files": item["representative_files"][:2],
            "ownership_status": item["ownership_status"],
            "recommended_action": item["recommended_action"],
        }
        for item in classified_families
        if item["ownership_status"] in {"candidate_gap", "unknown_unmapped"}
    ]
    weakly_mapped_queue = [
        {
            "family_path": item["family_path"],
            "py_file_count": item["py_file_count"],
            "py_loc": item["py_loc"],
            "parent_owner_modules": item["parent_owner_modules"],
            "recommended_action": item["recommended_action"],
        }
        for item in classified_families
        if item["ownership_status"] == "owned_by_refinement"
    ]
    large_family_needs_index_queue = [
        {
            "family_path": item["family_path"],
            "py_file_count": item["py_file_count"],
            "py_loc": item["py_loc"],
            "owner_modules": item["owner_modules"],
            "index_owner_modules": item["index_owner_modules"],
            "subsystem_owner_modules": item["subsystem_owner_modules"],
            "large_family_attention_status": (
                "decomposition_root"
                if len(item["owner_modules"]) >= CODE_FAMILY_DECOMPOSITION_ROOT_MIN_OWNERS
                else (
                    "already_indexed_but_still_saturated"
                    if item["index_owner_modules"]
                    else (
                        "bounded_subsystem_owned_no_index_needed"
                        if item["subsystem_owner_modules"]
                        else "needs_index"
                    )
                )
            ),
            "recommended_action": (
                "inspect_child_indexes_or_child_queues"
                if len(item["owner_modules"]) >= CODE_FAMILY_DECOMPOSITION_ROOT_MIN_OWNERS
                else (
                    "verify_index_sufficiency"
                    if item["index_owner_modules"]
                    else (
                        "verify_subsystem_boundary"
                        if item["subsystem_owner_modules"]
                        else "author_index"
                    )
                )
            ),
        }
        for item in classified_families
        if item["is_large"]
        and len(item["owner_modules"]) >= 3
        and item["ownership_status"] == "owned_by_module"
    ]
    intentional_exclusion_queue = [
        {
            "family_path": item["family_path"],
            "py_file_count": item["py_file_count"],
            "py_loc": item["py_loc"],
        }
        for item in classified_families
        if item["ownership_status"] == "intentional_exclusion"
    ]

    queues = {
        "unmapped_code_family_queue": unmapped_queue,
        "weakly_mapped_code_family_queue": weakly_mapped_queue,
        "large_family_needs_index_queue": large_family_needs_index_queue,
        "intentional_exclusion_queue": intentional_exclusion_queue,
    }
    queue_counts = {name: len(rows) for name, rows in queues.items()}
    fingerprint = _sha256_text(
        json.dumps(
            classified_families,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return {
        "schema_version": CODE_FAMILY_COVERAGE_SCHEMA_VERSION,
        "generated_at": timestamp,
        "roots": list(CODE_FAMILY_ROOTS),
        "materiality_policy": materiality_policy,
        "fingerprint": fingerprint,
        "summary": {
            "family_count": len(classified_families),
            "material_family_count": sum(
                1 for item in classified_families if item["is_material"]
            ),
            "large_family_count": sum(
                1 for item in classified_families if item["is_large"]
            ),
            "status_counts": dict(sorted(status_counts.items())),
            "queue_counts": queue_counts,
        },
        "queues": queues,
        "families": classified_families,
    }


def build_index(
    modules: list[ParsedModule],
    *,
    repo_root: Path,
    adjacency: dict[str, list[str]],
    reverse: dict[str, list[str]],
    fan_in_inbound: dict[str, int],
    cycles: list[list[str]],
    standard: dict[str, Any],
    candidates: list[dict[str, Any]],
    timestamp: str,
    source_manifest: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    projection_class_counts: Counter[str] = Counter()
    action_cause_counts: Counter[str] = Counter()
    code_loci_freshness_counts: Counter[str] = Counter()
    compression_status_counts: Counter[str] = Counter()
    compression_budget_violation_count = 0
    module_slug_set = {module.slug for module in modules}
    candidate_count = len(
        [
            item
            for item in candidates
            if str(item.get("status") or "").strip() != "deprecated"
            and str(item.get("slug") or "").strip() not in module_slug_set
        ]
    )

    hierarchy_depths, hierarchy_distances = compute_hierarchy_metrics(adjacency, reverse)
    for module in modules:
        status = classify_status(module, module.findings)
        recommended_action, action_reason = classify_recommended_action(module, status, module.findings)
        action_cause = classify_action_cause(module, status, module.findings, recommended_action)
        status_counts[status] += 1
        projection_class_counts[module.projection_class or "unknown"] += 1
        action_cause_counts[action_cause] += 1
        entry = _module_entry(
            module,
            fan_in_inbound=fan_in_inbound.get(module.slug, 0),
            depended_on_by=reverse.get(module.slug, []),
            adjacency=adjacency,
            hierarchy_depths=hierarchy_depths,
            hierarchy_distances=hierarchy_distances,
            status=status,
            recommended_action=recommended_action,
            action_reason=action_reason,
            action_cause=action_cause,
            repo_root=repo_root,
            standard=standard,
        )
        freshness_status = str((entry.get("code_loci_freshness") or {}).get("status") or "unknown")
        code_loci_freshness_counts[freshness_status] += 1
        compression_packet = module.analysis.get("compression") or {}
        compression_status_counts[
            str(compression_packet.get("compression_status") or "missing")
        ] += 1
        compression_budget_violation_count += sum(
            1
            for f in (compression_packet.get("findings") or [])
            if isinstance(f, Mapping) and "over_budget" in str(f.get("rule") or "")
        )
        entries.append(entry)

    sorted_entries = sorted(entries, key=lambda item: item["slug"])
    outbound_adjacency = {slug: sorted(deps) for slug, deps in sorted(adjacency.items())}
    inbound_adjacency = {slug: sorted(parents) for slug, parents in sorted(reverse.items())}
    roots = sorted([slug for slug, inbound in fan_in_inbound.items() if inbound == 0])
    leaves = sorted([slug for slug, deps in adjacency.items() if not deps])
    return {
        "schema_version": standard["schema_version"],
        "generated_at": timestamp,
        "standard": "codex/standards/std_paper_module.json",
        "source_manifest": source_manifest,
        "freshness": freshness,
        "module_count": len(sorted_entries),
        "candidate_count": candidate_count,
        "summary": {
            "module_count": len(sorted_entries),
            "candidate_count": candidate_count,
            "edge_count": sum(len(deps) for deps in adjacency.values()),
            "root_count": len(roots),
            "leaf_count": len(leaves),
            "projection_class_counts": dict(sorted(projection_class_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "action_cause_counts": dict(sorted(action_cause_counts.items())),
            "code_loci_freshness_counts": dict(sorted(code_loci_freshness_counts.items())),
            "compression_status_counts": dict(sorted(compression_status_counts.items())),
            "compression_atom_authored_count": int(compression_status_counts.get("authored", 0)),
            "compression_atom_fallback_count": int(compression_status_counts.get("fallback", 0)),
            "compression_atom_missing_count": int(compression_status_counts.get("missing", 0)),
            "compression_atom_invalid_count": int(compression_status_counts.get("invalid", 0)),
            "compression_budget_violation_count": int(compression_budget_violation_count),
        },
        "status_counts": dict(sorted(status_counts.items())),
        "graph": {
            "cycles": [" -> ".join(cycle) for cycle in cycles],
            "roots": roots,
            "leaves": leaves,
            "edge_count": sum(len(deps) for deps in adjacency.values()),
            "adjacency_outbound": outbound_adjacency,
            "adjacency_inbound": inbound_adjacency,
        },
        "modules": sorted_entries,
    }


def _queue_item(entry: dict[str, Any], *, priority: int, reason: str) -> dict[str, Any]:
    return {
        "slug": entry["slug"],
        "title": entry["title"],
        "projection_class": entry["projection_class"],
        "status": entry["status"],
        "recommended_action": entry["recommended_action"],
        "action_cause": entry["action_cause"],
        "priority": priority,
        "reason": reason,
        "file": entry["file"],
        "fan_in_inbound": entry["fan_in_inbound"],
        "boundary_pressure": entry["boundary_pressure"],
        "boundary_evidence": dict(entry.get("boundary_evidence") or {}),
    }


def render_validation_report(
    modules: list[ParsedModule],
    *,
    index: dict[str, Any],
    candidates: list[dict[str, Any]],
    standard: dict[str, Any],
    timestamp: str,
    source_manifest: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    entry_by_slug = {entry["slug"]: entry for entry in index["modules"]}
    per_module: list[dict[str, Any]] = []
    severity_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    action_cause_counts: Counter[str] = Counter()
    code_loci_freshness_counts: Counter[str] = Counter()
    fact_assertion_status_counts: Counter[str] = Counter()
    fact_finding_rule_counts: Counter[str] = Counter()
    fact_assertion_count = 0

    for module in modules:
        entry = entry_by_slug[module.slug]
        findings = [{"severity": item.severity, "rule": item.rule, "message": item.message} for item in module.findings]
        fact_audit = dict(entry.get("fact_audit") or {})
        fact_summary = dict(fact_audit.get("summary") or {})
        fact_assertion_count += int(fact_summary.get("assertion_count") or 0)
        for status, count in (fact_summary.get("status_counts") or {}).items():
            fact_assertion_status_counts[str(status)] += int(count or 0)
        for fact_finding in fact_audit.get("findings") or []:
            if isinstance(fact_finding, Mapping):
                fact_finding_rule_counts[str(fact_finding.get("rule") or "unknown")] += 1
        action_cause_counts[str(entry.get("action_cause") or "trusted")] += 1
        code_loci_freshness_counts[str((entry.get("code_loci_freshness") or {}).get("status") or "unknown")] += 1
        for item in module.findings:
            severity_counts[item.severity] += 1
            rule_counts[item.rule] += 1
        per_module.append(
            {
                "slug": module.slug,
                "file": entry["file"],
                "projection_class": entry["projection_class"],
                "status": entry["status"],
                "recommended_action": entry["recommended_action"],
                "action_reason": entry["action_reason"],
                "action_cause": entry["action_cause"],
                "boundary_pressure": entry["boundary_pressure"],
                "boundary_evidence": dict(entry.get("boundary_evidence") or {}),
                "documentation_quality": dict(entry.get("documentation_quality") or {}),
                "fact_audit": fact_audit,
                "code_loci_freshness": dict(entry.get("code_loci_freshness") or {}),
                "planned_surfaces": list(entry.get("planned_surfaces") or []),
                "hierarchy_context": dict(entry.get("hierarchy_context") or {}),
                "findings": findings,
            }
        )

    split_queue: list[dict[str, Any]] = []
    refresh_queue: list[dict[str, Any]] = []
    deprecate_queue: list[dict[str, Any]] = []
    for entry in index["modules"]:
        if entry["recommended_action"] == "split":
            split_queue.append(_queue_item(entry, priority=1, reason=entry["action_reason"]))
        elif entry["recommended_action"] in {"refresh", "verify_current_state"}:
            refresh_queue.append(_queue_item(entry, priority=2, reason=entry["action_reason"]))
        elif entry["recommended_action"] == "deprecate":
            deprecate_queue.append(_queue_item(entry, priority=3, reason=entry["action_reason"]))

    module_slugs = {module.slug for module in modules}
    first_author_queue: list[dict[str, Any]] = []
    for candidate in candidates:
        slug = str(candidate.get("slug") or "").strip()
        if not slug or slug in module_slugs:
            continue
        if str(candidate.get("status") or "").strip() == "deprecated":
            continue
        first_author_queue.append(
            {
                "slug": slug,
                "projection_class": str(candidate.get("projection_class") or "").strip() or "subsystem",
                "status": str(candidate.get("status") or "never_authored"),
                "recommended_action": "first_author",
                "action_cause": "candidate_gap",
                "priority": 1,
                "reason": str(candidate.get("rationale") or "Typed backlog candidate awaiting first-authoring."),
                "suggested_file_set": list(candidate.get("suggested_file_set") or []),
                "intent_sources": list(candidate.get("intent_sources") or []),
            }
        )
        action_cause_counts["candidate_gap"] += 1

    def _split_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        slug = str(item.get("slug") or "")
        if slug == "raw_seed_metabolism":
            return (0, 0, slug)
        return (1, -int(item.get("fan_in_inbound") or 0), slug)

    split_queue.sort(key=_split_sort_key)
    refresh_queue.sort(key=lambda item: (-int(item.get("fan_in_inbound") or 0), str(item["slug"])))
    first_author_queue.sort(key=lambda item: str(item["slug"]))
    deprecate_queue.sort(key=lambda item: str(item["slug"]))

    summary = {
        "module_count": index["module_count"],
        "candidate_count": index["candidate_count"],
        "projection_class_counts": dict(sorted((index.get("summary") or {}).get("projection_class_counts", {}).items())),
        "status_counts": dict(index["status_counts"]),
        "action_cause_counts": dict(sorted(action_cause_counts.items())),
        "code_loci_freshness_counts": dict(sorted(code_loci_freshness_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "rule_counts": dict(sorted(rule_counts.items())),
        "queue_counts": {
            "refresh_queue": len(refresh_queue),
            "split_queue": len(split_queue),
            "first_author_queue": len(first_author_queue),
            "deprecate_queue": len(deprecate_queue),
        },
        "fact_audit": {
            "assertion_count": fact_assertion_count,
            "finding_count": sum(fact_finding_rule_counts.values()),
            "assertion_status_counts": dict(sorted(fact_assertion_status_counts.items())),
            "finding_rule_counts": dict(sorted(fact_finding_rule_counts.items())),
        },
    }
    return {
        "schema_version": standard["schema_version"],
        "generated_at": timestamp,
        "source_manifest": source_manifest,
        "freshness": freshness,
        "summary": summary,
        "rule_counts": dict(sorted(rule_counts.items())),
        "drift_findings": [],
        "graph": dict(index.get("graph") or {}),
        "refresh_queue": refresh_queue,
        "split_queue": split_queue,
        "first_author_queue": first_author_queue,
        "deprecate_queue": deprecate_queue,
        "modules": sorted(per_module, key=lambda item: item["slug"]),
    }


def _readme_projection_contract(standard: dict[str, Any]) -> dict[str, Any]:
    contract = standard.get("readme_projection_contract")
    return dict(contract) if isinstance(contract, Mapping) else {}


def render_readme_projection(index: dict[str, Any], report: dict[str, Any], standard: dict[str, Any]) -> str:
    contract = _readme_projection_contract(standard)
    next_limit = int(contract.get("next_attention_limit") or 6)
    module_limit = int(contract.get("inventory_limit") or 99)
    modules = [item for item in (index.get("modules") or []) if isinstance(item, Mapping)]
    summary = index.get("summary") if isinstance(index.get("summary"), Mapping) else {}
    queue_counts = ((report.get("summary") or {}).get("queue_counts") or {}) if isinstance(report.get("summary"), Mapping) else {}
    freshness = index.get("freshness") if isinstance(index.get("freshness"), Mapping) else {}

    lines: list[str] = [
        "## Generated Browse Snapshot",
        "",
        "_Auto-projected from the paper-module runtime. Do not edit inside this region; rerun_ `./repo-python tools/meta/factory/build_paper_module_index.py` _instead._",
        "",
        f"- Source fingerprint: `{str(freshness.get('source_fingerprint') or '')[:16]}`",
        f"- Authored modules: `{freshness.get('authored_module_count')}`",
        f"- Generated modules: `{freshness.get('generated_module_count')}`",
        "",
        "### Counts",
        "",
        "| Surface | Count |",
        "|---|---:|",
    ]
    for projection_class, count in sorted((summary.get("projection_class_counts") or {}).items()):
        lines.append(f"| `class:{projection_class}` | {count} |")
    for status, count in sorted((summary.get("status_counts") or {}).items()):
        lines.append(f"| `status:{status}` | {count} |")
    for queue_name, count in sorted(queue_counts.items()):
        lines.append(f"| `queue:{queue_name}` | {count} |")

    lines.extend(["", "### Next Attention", "", "| Queue | Slug | Reason |", "|---|---|---|"])
    next_rows: list[tuple[str, Mapping[str, Any]]] = []
    for queue_name in ("split_queue", "refresh_queue", "first_author_queue", "deprecate_queue"):
        for row in (report.get(queue_name) or [])[:next_limit]:
            if isinstance(row, Mapping):
                next_rows.append((queue_name, row))
    for queue_name, row in next_rows[:next_limit]:
        reason = " ".join(str(row.get("reason") or "").split())
        if len(reason) > 108:
            reason = reason[:107].rstrip() + "…"
        lines.append(f"| `{queue_name}` | `{str(row.get('slug') or '').strip()}` | {reason} |")
    if not next_rows:
        lines.append("| _none_ |  | Generated queues are empty. |")

    lines.extend(["", "### Inventory", "", "| Class | Slug | Status | Action |", "|---|---|---|---|"])
    for row in modules[:module_limit]:
        lines.append(
            f"| `{row.get('projection_class')}` | `{row.get('slug')}` | `{row.get('status')}` | `{row.get('recommended_action')}` |"
        )
    return "\n".join(lines) + "\n"


def replace_marked_region(content: str, new_inner: str, begin: str, end: str) -> str:
    if begin not in content or end not in content:
        raise ValueError(f"Missing managed markers: {begin} / {end}")
    before, remainder = content.split(begin, 1)
    _old, after = remainder.split(end, 1)
    inner = new_inner.rstrip() + "\n"
    return f"{before}{begin}\n{inner}{end}{after}"


def extract_marked_region(content: str, begin: str, end: str) -> str | None:
    if begin not in content or end not in content:
        return None
    _before, remainder = content.split(begin, 1)
    inner, _after = remainder.split(end, 1)
    return inner.strip()


def render_readme_content(existing_readme: str, projection: str, standard: dict[str, Any]) -> str:
    contract = _readme_projection_contract(standard)
    regions = [dict(region) for region in (contract.get("managed_regions") or []) if isinstance(region, Mapping)]
    updated = existing_readme
    for region in regions:
        begin = str(region.get("begin_marker") or "").strip()
        end = str(region.get("end_marker") or "").strip()
        if not begin or not end:
            continue
        updated = replace_marked_region(updated, projection, begin, end)
    return updated


def _compare_payload_without_generated_at(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        if {
            "resolved_code_loci_count",
            "checked_code_loci_count",
            "ignored_generated_surface_count",
        }.issubset(set(payload.keys())):
            return _stable_code_loci_freshness_packet(payload)
        out: dict[str, Any] = {}
        for key, value in payload.items():
            if key in {"generated_at", "module_mtime", "source_mtime", "newest_source_mtime", "code_loci_freshness_counts"}:
                continue
            out[str(key)] = _compare_payload_without_generated_at(value)
        return out
    if isinstance(payload, list):
        return [_compare_payload_without_generated_at(item) for item in payload]
    return payload


def _truncate_repr(value: Any, max_len: int) -> str:
    try:
        if isinstance(value, (Mapping, list, tuple)):
            rendered = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        else:
            rendered = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        rendered = repr(value)
    if len(rendered) > max_len:
        return rendered[: max(1, max_len - 1)] + "…"
    return rendered


def _walk_diff(
    actual: Any,
    expected: Any,
    *,
    path: str,
    depth: int,
    max_depth: int,
    max_value_repr: int,
) -> tuple[str, str, str] | None:
    if depth > max_depth:
        return None
    if isinstance(actual, Mapping) and isinstance(expected, Mapping):
        actual_keys = set(actual.keys())
        expected_keys = set(expected.keys())
        only_in_expected = sorted(expected_keys - actual_keys)
        only_in_actual = sorted(actual_keys - expected_keys)
        if only_in_expected:
            key = only_in_expected[0]
            sub_path = f"{path}.{key}" if path else key
            return (sub_path, _truncate_repr(expected[key], max_value_repr), "<missing>")
        if only_in_actual:
            key = only_in_actual[0]
            sub_path = f"{path}.{key}" if path else key
            return (sub_path, "<missing>", _truncate_repr(actual[key], max_value_repr))
        for key in sorted(actual_keys):
            sub_path = f"{path}.{key}" if path else key
            found = _walk_diff(
                actual[key],
                expected[key],
                path=sub_path,
                depth=depth + 1,
                max_depth=max_depth,
                max_value_repr=max_value_repr,
            )
            if found is not None:
                return found
        return None
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return (
                f"{path or '<root>'}.length",
                str(len(expected)),
                str(len(actual)),
            )
        for idx, (a_item, e_item) in enumerate(zip(actual, expected)):
            sub_path = f"{path}[{idx}]" if path else f"[{idx}]"
            found = _walk_diff(
                a_item,
                e_item,
                path=sub_path,
                depth=depth + 1,
                max_depth=max_depth,
                max_value_repr=max_value_repr,
            )
            if found is not None:
                return found
        return None
    if actual != expected:
        return (
            path or "<root>",
            _truncate_repr(expected, max_value_repr),
            _truncate_repr(actual, max_value_repr),
        )
    return None


CODE_FAMILY_ROUTE_COVERAGE_ATTENTION_KEYS = {
    "unmapped_code_family_queue",
    "weakly_mapped_code_family_queue",
    "large_family_needs_index_queue",
}
CODE_FAMILY_ROUTE_COVERAGE_SUMMARY_KEYS = {
    "code_family_coverage_counts",
    "code_family_material_count",
}


def _route_coverage_freshness_projection(payload: Any) -> Any:
    """Return the default freshness view for `_route_coverage.json`.

    `_route_coverage.json` carries two different things: the paper-module route
    graph/read model and a broad code-family diagnostic. The latter intentionally
    observes live `system/` and `tools/` Python families, so unrelated source
    movement can change LOC/count diagnostics while authored paper-module inputs
    remain clean. Default paper-module freshness must not chase that broad
    diagnostic; strict code-family coverage remains the explicit gate for it.
    """
    normalized = _compare_payload_without_generated_at(payload)
    if not isinstance(normalized, Mapping):
        return normalized
    out = dict(normalized)
    out.pop("code_family_coverage", None)
    summary = out.get("summary")
    if isinstance(summary, Mapping):
        summary_out = dict(summary)
        for key in CODE_FAMILY_ROUTE_COVERAGE_SUMMARY_KEYS:
            summary_out.pop(key, None)
        attention_counts = summary_out.get("attention_queue_counts")
        if isinstance(attention_counts, Mapping):
            attention_out = dict(attention_counts)
            for key in CODE_FAMILY_ROUTE_COVERAGE_ATTENTION_KEYS:
                attention_out.pop(key, None)
            summary_out["attention_queue_counts"] = attention_out
        out["summary"] = summary_out
    return out


def _first_differing_path(
    actual: Any,
    expected: Any,
    *,
    max_depth: int = 6,
    max_value_repr: int = 40,
    normalizer=_compare_payload_without_generated_at,
) -> tuple[str, str, str] | None:
    actual_norm = normalizer(actual)
    expected_norm = normalizer(expected)
    return _walk_diff(
        actual_norm,
        expected_norm,
        path="",
        depth=0,
        max_depth=max_depth,
        max_value_repr=max_value_repr,
    )


def _fingerprint_drift_message(
    actual_payload: Mapping[str, Any] | None,
    expected_freshness: Mapping[str, Any],
    expected_payload: Mapping[str, Any] | None = None,
) -> str:
    expected = str(expected_freshness.get("source_fingerprint") or "").strip()
    actual_freshness = (actual_payload or {}).get("freshness") or {}
    actual = str(actual_freshness.get("source_fingerprint") or "").strip()
    expected_code_loci = str(expected_freshness.get("code_loci_freshness_fingerprint") or "").strip()
    actual_code_loci = str(actual_freshness.get("code_loci_freshness_fingerprint") or "").strip()
    if not expected and not actual:
        return "source_fingerprint unavailable"
    if expected == actual:
        if expected_code_loci and expected_code_loci != actual_code_loci:
            return (
                f"source_fingerprint unchanged ({expected[:16] or 'missing'}); "
                f"code_loci_freshness_fingerprint expected={expected_code_loci[:16]} "
                f"actual={actual_code_loci[:16] or 'missing'}"
            )
        base = f"source_fingerprint unchanged ({expected[:16] or 'missing'}); generated projection content changed"
        if expected_payload is not None and actual_payload is not None:
            diff = _first_differing_path(actual_payload, expected_payload)
            if diff is not None:
                path, expected_repr, actual_repr = diff
                return f"{base}; first drift at {path} (expected={expected_repr}, actual={actual_repr})"
        return base
    return f"source_fingerprint expected={expected[:16] or 'missing'} actual={actual[:16] or 'missing'}"


def _route_graph_payload_fingerprint(payload: Mapping[str, Any]) -> str:
    paper_module_routes: dict[str, Any] = {}
    for slug, item in sorted((payload.get("paper_module_routes") or {}).items()):
        if not isinstance(item, Mapping):
            continue
        paper_module_routes[str(slug)] = {
            "routes": item.get("routes"),
            "suggested_routes": item.get("suggested_routes"),
            "route_metadata_findings": item.get("route_metadata_findings"),
            "route_metadata_suggestions": item.get("route_metadata_suggestions"),
        }
    graph = {
        "routes": payload.get("routes") if isinstance(payload.get("routes"), Mapping) else {},
        "suggested_routes": payload.get("suggested_routes") if isinstance(payload.get("suggested_routes"), Mapping) else {},
        "paper_module_routes": paper_module_routes,
    }
    return _sha256_text(json.dumps(graph, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def _route_attention_payload_fingerprint(payload: Mapping[str, Any]) -> str:
    attention = payload.get("attention") if isinstance(payload.get("attention"), Mapping) else {}
    return _sha256_text(json.dumps(attention, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def _route_coverage_drift_message(
    actual_payload: Mapping[str, Any] | None,
    expected_payload: Mapping[str, Any],
    expected_freshness: Mapping[str, Any],
) -> str:
    base = _fingerprint_drift_message(actual_payload, expected_freshness)
    diff = _first_differing_path(
        actual_payload or {},
        expected_payload,
        normalizer=_route_coverage_freshness_projection,
    )
    if diff is not None:
        path, expected_repr, actual_repr = diff
        base = f"{base}; first drift at {path} (expected={expected_repr}, actual={actual_repr})"
    actual_route_graph = _route_graph_payload_fingerprint(actual_payload or {})
    expected_route_graph = _route_graph_payload_fingerprint(expected_payload)
    if actual_route_graph != expected_route_graph:
        return f"{base}; route_graph_fingerprint expected={expected_route_graph[:16]} actual={actual_route_graph[:16]}"
    actual_attention = _route_attention_payload_fingerprint(actual_payload or {})
    expected_attention = _route_attention_payload_fingerprint(expected_payload)
    if actual_attention != expected_attention:
        return f"{base}; route_attention_queue_fingerprint expected={expected_attention[:16]} actual={actual_attention[:16]}"
    return base


def assess_current_freshness(
    *,
    repo_root: Path,
    modules: list[ParsedModule],
    expected_index: dict[str, Any],
    expected_report: dict[str, Any],
    expected_doctrine_to_paper_modules: dict[str, Any],
    expected_route_coverage: dict[str, Any],
    expected_readme_projection: str,
    standard: dict[str, Any],
    readme_path: Path,
) -> dict[str, Any]:
    contract = _readme_projection_contract(standard)
    try:
        readme_target = str(readme_path.relative_to(repo_root))
    except ValueError:
        readme_target = str(contract.get("target_path") or str(readme_path))
    regions = [dict(region) for region in (contract.get("managed_regions") or []) if isinstance(region, Mapping)]
    begin_marker = str(regions[0].get("begin_marker") or "").strip() if regions else ""
    end_marker = str(regions[0].get("end_marker") or "").strip() if regions else ""

    actual_index = _safe_load_json(repo_root / INDEX_PATH.relative_to(REPO_ROOT))
    actual_report = _safe_load_json(repo_root / REPORT_PATH.relative_to(REPO_ROOT))
    actual_doctrine_to_paper_modules = _safe_load_json(repo_root / DOCTRINE_TO_PAPER_MODULES_PATH.relative_to(REPO_ROOT))
    actual_route_coverage = _safe_load_json(repo_root / PAPER_MODULE_ROUTE_COVERAGE_PATH.relative_to(REPO_ROOT))
    actual_readme_path = readme_path
    actual_readme = actual_readme_path.read_text(encoding="utf-8") if actual_readme_path.exists() else None

    authored_slugs = sorted(module.slug for module in modules)
    actual_index_slugs = sorted(
        str(item.get("slug") or "").strip()
        for item in ((actual_index or {}).get("modules") or [])
        if isinstance(item, Mapping) and str(item.get("slug") or "").strip()
    )
    actual_report_slugs = sorted(
        str(item.get("slug") or "").strip()
        for item in ((actual_report or {}).get("modules") or [])
        if isinstance(item, Mapping) and str(item.get("slug") or "").strip()
    )
    missing_from_index = sorted(set(authored_slugs) - set(actual_index_slugs))
    missing_from_report = sorted(set(authored_slugs) - set(actual_report_slugs))
    extra_in_index = sorted(set(actual_index_slugs) - set(authored_slugs))
    extra_in_report = sorted(set(actual_report_slugs) - set(authored_slugs))

    index_in_sync = bool(actual_index) and _compare_payload_without_generated_at(actual_index) == _compare_payload_without_generated_at(expected_index)
    report_in_sync = bool(actual_report) and _compare_payload_without_generated_at(actual_report) == _compare_payload_without_generated_at(expected_report)
    doctrine_to_paper_modules_in_sync = bool(actual_doctrine_to_paper_modules) and _compare_payload_without_generated_at(actual_doctrine_to_paper_modules) == _compare_payload_without_generated_at(expected_doctrine_to_paper_modules)
    route_coverage_in_sync = (
        bool(actual_route_coverage)
        and _route_coverage_freshness_projection(actual_route_coverage)
        == _route_coverage_freshness_projection(expected_route_coverage)
    )
    actual_code_family_coverage = (
        (actual_route_coverage or {}).get("code_family_coverage")
        if isinstance(actual_route_coverage, Mapping)
        else None
    )
    expected_code_family_coverage = (
        expected_route_coverage.get("code_family_coverage")
        if isinstance(expected_route_coverage, Mapping)
        else None
    )
    code_family_coverage_in_sync = (
        bool(actual_code_family_coverage)
        and _compare_payload_without_generated_at(actual_code_family_coverage)
        == _compare_payload_without_generated_at(expected_code_family_coverage)
    )

    actual_readme_projection = extract_marked_region(actual_readme or "", begin_marker, end_marker) if actual_readme is not None and begin_marker and end_marker else None
    readme_projection_in_sync = actual_readme_projection == expected_readme_projection.strip()
    expected_freshness = expected_index.get("freshness") if isinstance(expected_index.get("freshness"), Mapping) else {}

    drift_findings: list[dict[str, str]] = []
    if actual_index is None:
        drift_findings.append({"severity": "error", "rule": "missing_index_surface", "message": "_index.json is missing or unreadable."})
    elif not index_in_sync:
        drift_findings.append(
            {
                "severity": "error",
                "rule": "stale_index_surface",
                "message": f"_index.json is out of sync with the authored paper-module corpus; missing={missing_from_index[:5]}, extra={extra_in_index[:5]}; {_fingerprint_drift_message(actual_index, expected_freshness, expected_index)}.",
            }
        )
    if actual_report is None:
        drift_findings.append({"severity": "error", "rule": "missing_validation_report_surface", "message": "_validation_report.json is missing or unreadable."})
    elif not report_in_sync:
        drift_findings.append(
            {
                "severity": "error",
                "rule": "stale_validation_report_surface",
                "message": f"_validation_report.json is out of sync with the authored paper-module corpus; missing={missing_from_report[:5]}, extra={extra_in_report[:5]}; {_fingerprint_drift_message(actual_report, expected_freshness, expected_report)}.",
            }
        )
    if actual_doctrine_to_paper_modules is None:
        drift_findings.append(
            {
                "severity": "error",
                "rule": "missing_doctrine_to_paper_modules_surface",
                "message": "_doctrine_to_paper_modules.json is missing or unreadable.",
            }
        )
    elif not doctrine_to_paper_modules_in_sync:
        drift_findings.append(
            {
                "severity": "error",
                "rule": "stale_doctrine_to_paper_modules_surface",
                "message": f"_doctrine_to_paper_modules.json is out of sync with the authored paper-module corpus; {_fingerprint_drift_message(actual_doctrine_to_paper_modules, expected_freshness, expected_doctrine_to_paper_modules)}.",
            }
        )
    if actual_route_coverage is None:
        drift_findings.append(
            {
                "severity": "error",
                "rule": "missing_route_coverage_surface",
                "message": "_route_coverage.json is missing or unreadable.",
            }
        )
    elif not route_coverage_in_sync:
        drift_findings.append(
            {
                "severity": "error",
                "rule": "stale_route_coverage_surface",
                "message": f"_route_coverage.json is out of sync with the authored paper-module corpus; {_route_coverage_drift_message(actual_route_coverage, expected_route_coverage, expected_freshness)}.",
            }
        )
    if actual_readme is None:
        drift_findings.append({"severity": "error", "rule": "missing_readme_surface", "message": f"{readme_target} is missing or unreadable."})
    elif actual_readme_projection is None:
        drift_findings.append({"severity": "error", "rule": "missing_readme_projection_markers", "message": f"{readme_target} is missing the managed paper-module projection markers."})
    elif not readme_projection_in_sync:
        drift_findings.append({"severity": "error", "rule": "stale_readme_projection", "message": f"{readme_target} managed paper-module browse region is out of sync with the generated runtime."})

    if index_in_sync and report_in_sync and doctrine_to_paper_modules_in_sync and route_coverage_in_sync and readme_projection_in_sync:
        sync_status = "in_sync"
    elif not actual_index and not actual_report and not actual_doctrine_to_paper_modules and not actual_route_coverage:
        sync_status = "missing_sidecars"
    elif not readme_projection_in_sync and (
        not index_in_sync or not report_in_sync or not doctrine_to_paper_modules_in_sync or not route_coverage_in_sync
    ):
        sync_status = "stale_sidecars_and_readme"
    elif not index_in_sync or not report_in_sync or not doctrine_to_paper_modules_in_sync or not route_coverage_in_sync:
        sync_status = "stale_sidecars"
    else:
        sync_status = "stale_readme_projection"

    return {
        "sync_status": sync_status,
        "source_fingerprint": str(expected_freshness.get("source_fingerprint") or "").strip(),
        "authored_module_count": len(authored_slugs),
        "generated_module_count": len(expected_index.get("modules") or []),
        "index_generated_module_count": len(actual_index_slugs),
        "report_generated_module_count": len(actual_report_slugs),
        "doctrine_to_paper_modules_generated_at": str((actual_doctrine_to_paper_modules or {}).get("generated_at") or "").strip() or None,
        "route_coverage_generated_at": str((actual_route_coverage or {}).get("generated_at") or "").strip() or None,
        "index_generated_at": str((actual_index or {}).get("generated_at") or "").strip() or None,
        "report_generated_at": str((actual_report or {}).get("generated_at") or "").strip() or None,
        "doctrine_to_paper_modules_source_fingerprint": str((((actual_doctrine_to_paper_modules or {}).get("freshness") or {}).get("source_fingerprint") or "")).strip() or None,
        "route_coverage_source_fingerprint": str((((actual_route_coverage or {}).get("freshness") or {}).get("source_fingerprint") or "")).strip() or None,
        "index_source_fingerprint": str((((actual_index or {}).get("freshness") or {}).get("source_fingerprint") or "")).strip() or None,
        "report_source_fingerprint": str((((actual_report or {}).get("freshness") or {}).get("source_fingerprint") or "")).strip() or None,
        "doctrine_to_paper_modules_in_sync": doctrine_to_paper_modules_in_sync,
        "route_coverage_in_sync": route_coverage_in_sync,
        "route_coverage_compare_mode": "paper_route_surface_excluding_code_family_diagnostics",
        "code_family_coverage_in_sync": code_family_coverage_in_sync,
        "index_in_sync": index_in_sync,
        "report_in_sync": report_in_sync,
        "readme_projection_in_sync": readme_projection_in_sync,
        "managed_readme_path": readme_target,
        "missing_from_index": missing_from_index,
        "missing_from_report": missing_from_report,
        "extra_in_index": extra_in_index,
        "extra_in_report": extra_in_report,
        "drift_findings": drift_findings,
    }


def build_outputs(
    *,
    repo_root: Path = REPO_ROOT,
    standard_path: Path | None = None,
    paper_modules_dir: Path | None = None,
    candidates_path: Path | None = None,
    timestamp: str | None = None,
    strict_fact_audit: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], list[ParsedModule]]:
    standard_path = standard_path or (repo_root / STANDARD_PATH.relative_to(REPO_ROOT))
    paper_modules_dir = paper_modules_dir or (repo_root / PAPER_MODULES_DIR.relative_to(REPO_ROOT))
    candidates_path = candidates_path or (repo_root / CANDIDATES_PATH.relative_to(REPO_ROOT))
    runtime = load_paper_module_runtime(
        repo_root=repo_root,
        standard_path=standard_path,
        paper_modules_dir=paper_modules_dir,
        candidates_path=candidates_path,
        readme_path=repo_root / README_PATH.relative_to(REPO_ROOT),
        timestamp=timestamp,
        compare_existing=False,
        strict_fact_audit=strict_fact_audit,
    )
    return runtime.index, runtime.report, runtime.modules


def load_paper_module_runtime(
    *,
    repo_root: Path = REPO_ROOT,
    standard_path: Path | None = None,
    paper_modules_dir: Path | None = None,
    candidates_path: Path | None = None,
    readme_path: Path | None = None,
    timestamp: str | None = None,
    compare_existing: bool = True,
    strict_fact_audit: bool = False,
) -> PaperModuleRuntime:
    standard_path = standard_path or (repo_root / STANDARD_PATH.relative_to(REPO_ROOT))
    paper_modules_dir = paper_modules_dir or (repo_root / PAPER_MODULES_DIR.relative_to(REPO_ROOT))
    candidates_path = candidates_path or (repo_root / CANDIDATES_PATH.relative_to(REPO_ROOT))
    readme_path = readme_path or (repo_root / README_PATH.relative_to(REPO_ROOT))
    standard = load_standard(standard_path)
    candidates = load_candidates(candidates_path)
    modules = load_paper_modules(paper_modules_dir, standard)
    adjacency, reverse, fan_in_inbound, cycles = compute_dag(modules)
    known_slugs = {module.slug for module in modules}
    governing_ids = _load_governing_ids(repo_root)
    fact_ledger = build_fact_hologram(repo_root=repo_root).get("ledger") or {"facts": []}

    # One freshness-mtime cache shared across all per-module validates; many
    # paper modules share code loci (e.g. `codex/doctrine/paper_modules/`),
    # and without this each validate re-walks the same directory subtree.
    mtime_cache: dict[tuple[str, str], tuple[float, str] | None] = {}
    for module in modules:
        module.findings = validate_module(
            module,
            standard,
            repo_root=repo_root,
            known_slugs=known_slugs,
            fan_in_inbound=fan_in_inbound.get(module.slug, 0),
            total_modules=len(modules),
            governing_ids=governing_ids,
            fact_ledger=fact_ledger,
            strict_fact_audit=strict_fact_audit,
            mtime_cache=mtime_cache,
        )

    if cycles:
        cycle_members = {slug for cycle in cycles for slug in cycle}
        for module in modules:
            if module.slug in cycle_members:
                relevant = [cycle for cycle in cycles if module.slug in cycle]
                module.findings.append(Finding("error", "depends_on_cycle", f"This module participates in a depends_on cycle: {relevant}"))

    stamp = timestamp or _utc_iso()
    source_manifest = build_source_manifest(
        repo_root=repo_root,
        modules=modules,
        standard_path=standard_path,
        candidates_path=candidates_path,
    )
    generated_freshness = build_generated_freshness(
        source_manifest=source_manifest,
        authored_module_count=len(modules),
        generated_module_count=len(modules),
        standard=standard,
        modules=modules,
        timestamp=stamp,
    )
    index = build_index(
        modules,
        repo_root=repo_root,
        adjacency=adjacency,
        reverse=reverse,
        fan_in_inbound=fan_in_inbound,
        cycles=cycles,
        standard=standard,
        candidates=candidates,
        timestamp=stamp,
        source_manifest=source_manifest,
        freshness=generated_freshness,
    )
    report = render_validation_report(
        modules,
        index=index,
        candidates=candidates,
        standard=standard,
        timestamp=stamp,
        source_manifest=source_manifest,
        freshness=generated_freshness,
    )
    doctrine_to_paper_modules = build_doctrine_to_paper_modules_index(
        modules,
        repo_root=repo_root,
        timestamp=stamp,
        source_manifest=source_manifest,
        freshness=generated_freshness,
    )
    route_coverage = build_route_coverage(
        modules,
        index=index,
        report=report,
        timestamp=stamp,
        source_manifest=source_manifest,
        freshness=generated_freshness,
        repo_root=repo_root,
    )
    readme_projection = render_readme_projection(index, report, standard)

    current_freshness = assess_current_freshness(
        repo_root=repo_root,
        modules=modules,
        expected_index=index,
        expected_report=report,
        expected_doctrine_to_paper_modules=doctrine_to_paper_modules,
        expected_route_coverage=route_coverage,
        expected_readme_projection=readme_projection,
        standard=standard,
        readme_path=readme_path,
    ) if compare_existing else {
        "sync_status": "not_compared",
        "source_fingerprint": generated_freshness["source_fingerprint"],
        "authored_module_count": len(modules),
        "generated_module_count": len(index.get("modules") or []),
        "index_generated_module_count": None,
        "report_generated_module_count": None,
        "doctrine_to_paper_modules_generated_at": None,
        "route_coverage_generated_at": None,
        "index_generated_at": None,
        "report_generated_at": None,
        "doctrine_to_paper_modules_source_fingerprint": None,
        "route_coverage_source_fingerprint": None,
        "index_source_fingerprint": None,
        "report_source_fingerprint": None,
        "doctrine_to_paper_modules_in_sync": None,
        "route_coverage_in_sync": None,
        "index_in_sync": None,
        "report_in_sync": None,
        "readme_projection_in_sync": None,
        "managed_readme_path": str(readme_path),
        "missing_from_index": [],
        "missing_from_report": [],
        "extra_in_index": [],
        "extra_in_report": [],
        "drift_findings": [],
    }

    readme_content = None
    if readme_path.exists():
        readme_content = render_readme_content(readme_path.read_text(encoding="utf-8"), readme_projection, standard)

    return PaperModuleRuntime(
        repo_root=repo_root,
        standard=standard,
        candidates=candidates,
        modules=modules,
        index=index,
        report=report,
        doctrine_to_paper_modules=doctrine_to_paper_modules,
        route_coverage=route_coverage,
        fact_ledger=fact_ledger,
        source_manifest=source_manifest,
        generated_freshness=generated_freshness,
        current_freshness=current_freshness,
        readme_projection=readme_projection,
        readme_content=readme_content,
    )
