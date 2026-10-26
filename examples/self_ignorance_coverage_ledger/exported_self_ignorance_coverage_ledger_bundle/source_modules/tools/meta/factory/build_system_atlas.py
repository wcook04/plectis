#!/usr/bin/env python3
"""Build the generated System Atlas v1 graph and public-safe markdown views."""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from system.lib import generated_projection_registry, task_ledger_events, work_ledger_runtime


REPO_ROOT = Path(__file__).resolve().parents[3]

STANDARD_PATH = Path("codex/standards/std_system_atlas.json")
STANDARD_TYPE_PLANE_PATH = Path("codex/standards/std_standard_type_plane.json")
GRAPH_PATH = Path("state/system_atlas/system_atlas.graph.json")
SUMMARY_PATH = Path("state/system_atlas/system_atlas_summary.json")
FACTS_PATH = Path("state/system_atlas/system_facts_at_a_glance.json")
SNAPSHOT_PATH = Path("docs/system_atlas/generated_system_atlas_snapshot.md")
FACTS_MARKDOWN_PATH = Path("docs/system_atlas/generated_system_facts_at_a_glance.md")
UNKNOWNS_PATH = Path("docs/system_atlas/unknown_unknowns_queue.generated.md")
GOVERNING_DOCTRINE_PATH = Path("docs/system_atlas/atlas_governing_doctrine.generated.md")
DISSEMINATION_GATE_REPORT_PATH = Path("state/system_atlas/dissemination_gate_report.json")
DISSEMINATION_GATE_MARKDOWN_PATH = Path("docs/system_atlas/dissemination_gate_report.generated.md")
COMPUTE_RECEIPTS_GLOB = "state/compute_workers/receipts/**/*.json"
LIVE_TASK_LEDGER_SOURCE_IDS = frozenset({"task_ledger_ledger", "task_ledger_views"})
LIVE_RUNTIME_COUNT_ONLY_SOURCE_IDS = frozenset(
    {
        "compute_cache",
        "compute_receipts",
        "compute_run_fingerprints",
    }
)

BUILDER_ID = "tools/meta/factory/build_system_atlas.py"
GRAPH_SCHEMA_VERSION = "system_atlas_graph_v1"

GENERATED_DOC_NAMES = {
    "atlas_governing_doctrine.generated.md",
    "dissemination_gate_report.generated.md",
    "generated_system_atlas_snapshot.md",
    "generated_system_facts_at_a_glance.md",
    "unknown_unknowns_queue.generated.md",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b"),
]

FORBIDDEN_SNAPSHOT_MARKERS = [
    "provider prompt",
    "provider output",
    "browser session",
    "chatgpt thread",
    "gemini thread",
    "finance artifact contents",
    "private correspondence",
    "private log",
]


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    path: str
    kind: str
    glob: bool = False
    count_only: bool = False


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec("paper_module_index", "codex/doctrine/paper_modules/_index.json", "paper_module_index"),
    SourceSpec("paper_module_validation", "codex/doctrine/paper_modules/_validation_report.json", "paper_module_validation"),
    SourceSpec("paper_module_route_coverage", "codex/doctrine/paper_modules/_route_coverage.json", "paper_module_route_coverage"),
    SourceSpec("kind_atlas_builder", "system/lib/kind_atlas.py", "kind_atlas_builder"),
    SourceSpec("standard_type_plane", str(STANDARD_TYPE_PLANE_PATH), "standard_type_plane"),
    SourceSpec("standards", "codex/standards/**/std_*.json", "standards", glob=True),
    SourceSpec("skills_registry", "codex/doctrine/skills/skill_registry.json", "skills_registry"),
    SourceSpec("principles", "<private-raw-seed-root> - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json", "principles"),
    SourceSpec("axiom_candidates", "<private-raw-seed-root> - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json", "axiom_candidates"),
    SourceSpec("concepts", "codex/doctrine/concepts/con_*.json", "concept", glob=True),
    SourceSpec("mechanisms", "codex/doctrine/mechanisms/mech_*.json", "mechanism", glob=True),
    SourceSpec("task_ledger_ledger", "state/task_ledger/ledger.json", "task_ledger_projection"),
    SourceSpec("task_ledger_views", "state/task_ledger/views/*.json", "task_ledger_view", glob=True),
    SourceSpec("frontend_navigation_graph", "state/frontend_navigation/navigation_graph.json", "frontend_navigation_graph"),
    SourceSpec("frontend_component_index", "state/frontend_navigation/component_index.json", "frontend_component_index"),
    SourceSpec("provider_registry", "codex/doctrine/compute/provider_registry.json", "provider_registry"),
    SourceSpec("compute_receipts", COMPUTE_RECEIPTS_GLOB, "compute_receipt", glob=True, count_only=True),
    SourceSpec("compute_cache", "state/compute_workers/cache/*.json", "compute_cache", glob=True, count_only=True),
    SourceSpec(
        "compute_run_fingerprints",
        "state/compute_workers/run_fingerprints/*.json",
        "compute_run_fingerprint",
        glob=True,
        count_only=True,
    ),
    SourceSpec("substrate_feed_nodes", "codex/substrate/nodes/feeds/*.json", "feed_node", glob=True),
    SourceSpec("feed_node_mirrors", "codex/nodes/feeds/*.json", "feed_node_mirror", glob=True),
    SourceSpec("feed_run_artifacts", "state/runs/*/artifacts/global_*_feed.json", "feed_run_artifact", glob=True, count_only=True),
    SourceSpec("annex_distillation_index", "annexes/annex_distillation_index.json", "annex_distillation_index"),
    SourceSpec("annex_sync_digest", "annexes/annex_sync_digest.json", "annex_sync_digest"),
    SourceSpec("disclosure_registry", "docs/dissemination/disclosure_artifact_registry.md", "dissemination_registry"),
    SourceSpec("manual_system_atlas_docs", "docs/system_atlas/*.md", "manual_atlas_doc", glob=True),
)

GOVERNING_STANDARDS = {
    "std_standard_type_plane": {
        "path": "codex/standards/std_standard_type_plane.json",
        "why": "Owns the standards-first artifact type plane that System Atlas projects as ArtifactKind neighborhoods.",
        "behavior": "Project type rows with source authority, standards, option surfaces, validators, and mutation back to standards.",
    },
    "std_system_atlas": {
        "path": "codex/standards/std_system_atlas.json",
        "why": "Owns the generated atlas graph, thin-band, redaction, and context-pack contracts.",
        "behavior": "Validate atlas rows and keep bands drilldown-first instead of body dumps.",
    },
    "std_agent_entry_surface": {
        "path": "codex/standards/std_agent_entry_surface.json",
        "why": "Defines first-contact entry surfaces and keeps atlas drilldowns downstream of entry/context-pack.",
        "behavior": "Expose atlas as a selected drilldown hint, not first-contact control authority.",
    },
    "std_kind_atlas": {
        "path": "codex/standards/std_kind_atlas.json",
        "why": "Governs the kind inventory that makes system_atlas discoverable.",
        "behavior": "Register atlas as an option-surface kind with bounded row counts and commands.",
    },
    "std_lifecycle_surface_budget": {
        "path": "codex/standards/std_lifecycle_surface_budget.json",
        "why": "Governs resource budgets for automatically invoked lifecycle and control-plane surfaces.",
        "behavior": "Expose lifecycle membrane affordances, forbidden dynamic state, and drift receipts without widening hook hot paths.",
    },
    "std_skill": {
        "path": "codex/standards/std_skill.json",
        "why": "Owns skill compression passports and how-to surfaces that atlas cards cite.",
        "behavior": "Preserve skill drilldowns and omission receipts instead of copying skill bodies.",
    },
    "std_paper_module": {
        "path": "codex/standards/std_paper_module.json",
        "why": "Owns paper-module reference surfaces that atlas rows cite as explanation memory.",
        "behavior": "Route to selected paper modules by slug; never inline the paper-module library.",
    },
    "std_navigation_rosetta_grammar": {
        "path": "codex/standards/std_navigation_rosetta_grammar.json",
        "why": "Defines the navigation grammar for compressed bands and drilldowns.",
        "behavior": "Keep atlas commands as hints with explicit band and id selection.",
    },
    "std_task_ledger": {
        "path": "codex/standards/std_task_ledger.json",
        "why": "Owns WorkItem planning and closure contracts for atlas gaps.",
        "behavior": "Route stale or missing atlas coverage into WorkItems instead of polished claims.",
    },
    "std_uppropagation_intake": {
        "path": "codex/standards/std_uppropagation_intake.json",
        "why": "Owns reusable lesson intake when atlas/control-plane work teaches the system.",
        "behavior": "Treat self-uppropagation as an atlas-backed specialization of existing intake lanes.",
    },
}

GOVERNING_SKILLS = {
    "profile_governed_compression": (
        "Prevents ad-hoc summaries from becoming context bombs.",
        "Atlas rows need band contracts, omission receipts, and selected drilldowns.",
    ),
    "navigation_seed": (
        "Owns cold-start route discipline before raw file search.",
        "Context-pack may point to atlas drilldowns after first-contact orientation.",
    ),
    "navigation_metabolism": (
        "Routes navigation/context bloat into measurable surface debt.",
        "Atlas stale and unknown findings should become drilldown hints or repair rows.",
    ),
    "type_a_autonomous_seed_loop": (
        "Controls Type A execution behavior and continuation obligations.",
        "Accepted atlas specs must become Work Ledger-backed mutations before more synthesis.",
    ),
    "local_to_general_propagation": (
        "Owns local lesson to general artifact propagation.",
        "Atlas-control-plane lessons must up-propagate through existing owners.",
    ),
}

GOVERNING_PAPER_MODULES = {
    "system_self_comprehension_root": (
        "Canonical root contract for the system_self_comprehension_packet family.",
        "Atlas and packet renders are drilldowns under this root, not competing roofs.",
    ),
    "system_self_comprehension_spine": (
        "Compatibility/evidence spine for the system understanding itself.",
        "Atlas remains a generated control-plane substrate under the canonical root.",
    ),
    "navigation_rosetta_math": (
        "Defines context atoms and budgeted navigation packing.",
        "Atlas appears as compact atoms with explicit drilldowns.",
    ),
    "holographic_navigation_compression": (
        "Defines Russian-doll compression for navigation surfaces.",
        "Atlas cluster/flag/card bands must preserve omission receipts and zoom levels.",
    ),
    "navigation_hologram_theory": (
        "Root option-surface and holographic navigation theory.",
        "Atlas bands should expose coverage and gaps without replacing source authority.",
    ),
    "unified_navigation_layer": (
        "Connects route surfaces across the repo.",
        "Atlas is one routed control-plane input, not a parallel navigation stack.",
    ),
    "recursive_self_improvement_operating_loop": (
        "Owns the Monitor/Analyze/Plan/Execute loop over system knowledge.",
        "Atlas supplies the generated Knowledge substrate for self-uppropagation.",
    ),
    "local_to_general_propagation": (
        "Defines generalise-uppropagate and owner-artifact routing.",
        "Atlas findings should produce owner patches or WorkItems, not freeform reflection.",
    ),
}

GOVERNANCE_KEYWORDS = {
    "atlas",
    "compression",
    "context",
    "coverage",
    "documentation",
    "drilldown",
    "epistemic",
    "holographic",
    "navigation",
    "projection",
    "route",
    "standard",
    "surface",
    "self",
}

STATE_GRAVITY_PATHS: tuple[tuple[str, str, str], ...] = (
    ("state/observability/agent_trace/events.jsonl", "forbidden_in_hook", "observability history JSONL"),
    ("state/metabolism/metabolism.sqlite", "forbidden_in_hook", "lock-bearing metabolism SQLite store"),
    ("state/embeddings/annex_notes.json", "explicit_only", "large embeddings projection"),
    ("state/embeddings/raw_seed_paragraphs.json", "explicit_only", "raw-seed paragraph embedding projection"),
    ("state/task_ledger/events.jsonl", "forbidden_in_hook", "task ledger event stream"),
    ("state/task_ledger/ledger.json", "explicit_only", "Task Ledger projection"),
    ("codex/ledger/*/work_ledger.jsonl", "forbidden_in_hook", "Work Ledger JSONL stream"),
    ("state/work_ledger/runtime_status.json", "hook_safe_sidecar", "compact Work Ledger runtime status"),
    ("tools/meta/control/orchestration_events.jsonl", "forbidden_in_hook", "orchestration event stream"),
    ("tools/meta/control/runtime_hook_agent_observability.jsonl", "hook_safe_sidecar", "compact hook telemetry row sink"),
    ("tools/meta/control/runtime_hook_navigation_hints.json", "hook_safe_sidecar", "precomputed runtime-hook navigation hint card"),
)


def _size_class(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "empty_or_missing"
    mb = size_bytes / (1024 * 1024)
    if mb >= 1024:
        return "gt_1gb"
    if mb >= 100:
        return "gt_100mb"
    if mb >= 10:
        return "gt_10mb"
    if mb >= 1:
        return "gt_1mb"
    return "lt_1mb"


def _repo(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _iso_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(rel_path: str | Path) -> Any:
    path = _repo(rel_path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _compact_text(value: Any, *, max_chars: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _keyword_match(*values: Any) -> bool:
    text = " ".join(str(value or "") for value in values).lower()
    return any(keyword in text for keyword in GOVERNANCE_KEYWORDS)


def _stat_state_gravity_paths() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern, access_class, description in STATE_GRAVITY_PATHS:
        paths = sorted(REPO_ROOT.glob(pattern)) if any(token in pattern for token in ("*", "?", "[")) else [_repo(pattern)]
        for path in paths[:24]:
            exists = path.exists()
            size_bytes = 0
            if exists:
                try:
                    stat = path.stat()
                    size_bytes = int(stat.st_size)
                except OSError:
                    exists = False
            rows.append(
                {
                    "path": _rel(path),
                    "pattern": pattern,
                    "exists": exists,
                    "_sort_size_bytes": size_bytes,
                    "size_class": _size_class(size_bytes),
                    "access_class": access_class,
                    "description": description,
                }
            )
    sorted_rows = sorted(rows, key=lambda row: int(row.get("_sort_size_bytes") or 0), reverse=True)
    for row in sorted_rows:
        row.pop("_sort_size_bytes", None)
    return sorted_rows


def _state_gravity_entity() -> dict[str, Any]:
    rows = _stat_state_gravity_paths()
    existing = [row for row in rows if row.get("exists")]
    largest = existing[:5]
    largest_summary = ", ".join(
        f"{row['path']}={row['size_class']}" for row in largest[:3]
    ) or "no nominated dynamic state paths observed"
    return _entity(
        "state_gravity",
        kind="Surface",
        title="State gravity projection",
        summary=(
            "Stat-only projection of nominated dynamic state roots for lifecycle-surface budget work; "
            f"largest observed paths: {largest_summary}."
        ),
        authority_class="runtime_observation",
        source_of_truth=[
            "disk stat over nominated dynamic state roots",
            "codex/standards/std_lifecycle_surface_budget.json",
        ],
        evidence_paths=[
            "codex/standards/std_lifecycle_surface_budget.json",
            "tools/meta/factory/build_system_atlas.py",
        ],
        maturity="partial",
        risk_level="high",
        disclosure_class="private_root_only",
        freshness_status="fresh",
        related_workitems=["observability-recursion-and-state-gravity-audit"],
        owning_module="std_lifecycle_surface_budget",
        safe_agent_actions=[
            "read this stat-only card before touching dynamic state roots",
            "use hook-safe sidecars or explicit owner commands for evidence reads",
        ],
        forbidden_agent_actions=[
            "read raw JSONL or SQLite roots from lifecycle hooks",
            "treat file-size projection as source content evidence",
            "hand-edit generated system_atlas outputs",
        ],
        next_drilldowns=[
            "./repo-python kernel.py --option-surface system_atlas --band card --ids state_gravity",
            "./repo-python tools/meta/factory/build_system_atlas.py --check",
            "./repo-python kernel.py --option-surface standards --band card --ids std_lifecycle_surface_budget",
        ],
        metrics={
            "observed_path_count": len(existing),
            "missing_path_count": len(rows) - len(existing),
            "largest_dynamic_files": largest,
            "forbidden_in_hook": [
                row["path"] for row in rows if row.get("access_class") == "forbidden_in_hook"
            ],
            "hook_safe_sidecars": [
                row["path"] for row in rows if row.get("access_class") == "hook_safe_sidecar"
            ],
        },
    )


def _skill_lookup() -> dict[str, dict[str, Any]]:
    registry = _read_json("codex/doctrine/skills/skill_registry.json")
    out: dict[str, dict[str, Any]] = {}
    families = registry.get("families") if isinstance(registry, dict) else []
    if not isinstance(families, list):
        return out
    for family in families:
        if not isinstance(family, dict):
            continue
        for skill in family.get("skills") or []:
            if not isinstance(skill, dict):
                continue
            skill_id = str(skill.get("id") or "").strip()
            if skill_id:
                out[skill_id] = skill
    return out


def _paper_module_lookup() -> dict[str, dict[str, Any]]:
    data = _read_json("codex/doctrine/paper_modules/_index.json")
    modules = data.get("modules") if isinstance(data, dict) else []
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(modules, list):
        return out
    for module in modules:
        if not isinstance(module, dict):
            continue
        slug = str(module.get("slug") or "").strip()
        if slug:
            out[slug] = module
    return out


def _governance_row(
    ref: str,
    *,
    kind: str,
    title: str,
    why: str,
    behavior: str,
    source_ref: str,
    drilldown_command: str,
    authority_class: str = "derived_projection",
    status: str = "observed",
) -> dict[str, Any]:
    return {
        "ref": ref,
        "kind": kind,
        "title": _compact_text(title, max_chars=120),
        "why_it_governs_atlas": _compact_text(why, max_chars=220),
        "required_atlas_behavior": _compact_text(behavior, max_chars=220),
        "source_ref": source_ref,
        "drilldown_command": drilldown_command,
        "authority_class": authority_class,
        "status": status,
    }


def _standard_governance_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for standard_id, contract in GOVERNING_STANDARDS.items():
        source_ref = str(contract["path"])
        payload = _read_json(source_ref)
        title = payload.get("title") if isinstance(payload, dict) else None
        rows.append(
            _governance_row(
                standard_id,
                kind="Standard",
                title=str(title or standard_id),
                why=str(contract["why"]),
                behavior=str(contract["behavior"]),
                source_ref=source_ref,
                drilldown_command=f"./repo-python kernel.py --option-surface standards --band card --ids {standard_id}",
                authority_class="manual_interpretation",
                status="present" if _repo(source_ref).exists() else "missing",
            )
        )
    return rows


def _skill_governance_rows() -> list[dict[str, Any]]:
    lookup = _skill_lookup()
    rows: list[dict[str, Any]] = []
    for skill_id, (why, behavior) in GOVERNING_SKILLS.items():
        skill = lookup.get(skill_id, {})
        source_ref = str(skill.get("file") or f"codex/doctrine/skills/{skill_id}.md")
        rows.append(
            _governance_row(
                skill_id,
                kind="Skill",
                title=str(skill.get("title") or skill_id),
                why=why,
                behavior=behavior,
                source_ref=source_ref,
                drilldown_command=f"./repo-python kernel.py --option-surface skills --band card --ids {skill_id}",
                authority_class="manual_interpretation",
                status=str(skill.get("status") or ("present" if skill else "missing")),
            )
        )
    return rows


def _paper_module_governance_rows() -> list[dict[str, Any]]:
    lookup = _paper_module_lookup()
    rows: list[dict[str, Any]] = []
    for slug, (why, behavior) in GOVERNING_PAPER_MODULES.items():
        module = lookup.get(slug, {})
        source_ref = str(module.get("file") or f"codex/doctrine/paper_modules/{slug}.md")
        rows.append(
            _governance_row(
                slug,
                kind="PaperModule",
                title=str(module.get("title") or slug),
                why=why,
                behavior=behavior,
                source_ref=source_ref,
                drilldown_command=f"./repo-python kernel.py --paper-module {slug}",
                authority_class="manual_interpretation",
                status=str(module.get("status") or ("present" if module else "missing")),
            )
        )
    return rows


def _doctrine_json_governance_rows(
    *,
    kind: str,
    pattern: str,
    option_surface: str,
    limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _existing_paths(pattern, glob=True):
        payload = _read_json(_rel(path))
        if not isinstance(payload, dict):
            continue
        ref = str(payload.get("id") or payload.get("slug") or path.stem)
        title = str(payload.get("title") or payload.get("slug") or ref)
        tags = payload.get("tags")
        statement = payload.get("statement") or payload.get("summary") or payload.get("synthesis")
        if not _keyword_match(ref, title, tags, statement):
            continue
        rows.append(
            _governance_row(
                ref,
                kind=kind,
                title=title,
                why=f"Selected by compact governance keyword overlap for atlas routing and compression ({kind.lower()}).",
                behavior="Cite the row as governing context and route to a card drilldown; do not inline the doctrine body.",
                source_ref=_rel(path),
                drilldown_command=f"./repo-python kernel.py --option-surface {option_surface} --band card --ids {ref}",
                authority_class="manual_interpretation",
                status=str(payload.get("status") or "observed"),
            )
        )
    rows.sort(key=lambda row: (row["kind"], row["ref"]))
    return rows[:limit]


def _principle_governance_rows(limit: int = 6) -> list[dict[str, Any]]:
    payload = _read_json(
        "<private-raw-seed-root> - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json"
    )
    principles = payload.get("principles") if isinstance(payload, dict) else []
    rows: list[dict[str, Any]] = []
    if not isinstance(principles, list):
        return rows
    for principle in principles:
        if not isinstance(principle, dict):
            continue
        ref = str(principle.get("id") or principle.get("slug") or "").strip()
        title = str(principle.get("title") or principle.get("slug") or ref)
        tags = principle.get("tags")
        statement = principle.get("statement")
        if not ref or not _keyword_match(ref, title, tags, statement):
            continue
        rows.append(
            _governance_row(
                ref,
                kind="Principle",
                title=title,
                why="Selected from the principle registry as compact governance context for atlas evidence, routing, or compression.",
                behavior="Use only as a drilldown reference; do not copy raw-seed-derived principle bodies into atlas bands.",
                source_ref=(
                    "<private-raw-seed-root> - Raw-Seed Preservation, Semantic Reset, "
                    "and Fresh Execution Spine/raw_seed/raw_seed_principles.json"
                ),
                drilldown_command=f"./repo-python kernel.py --option-surface principles --band card --ids {ref}",
                authority_class="manual_interpretation",
                status=str(principle.get("status") or "observed"),
            )
        )
    rows.sort(key=lambda row: row["ref"])
    return rows[:limit]


def _axiom_governance_rows(limit: int = 6) -> list[dict[str, Any]]:
    payload = _read_json(
        "<private-raw-seed-root> - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json"
    )
    candidates = payload.get("axiom_candidates") if isinstance(payload, dict) else []
    rows: list[dict[str, Any]] = []
    if not isinstance(candidates, list):
        return rows
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        ref = str(candidate.get("id") or candidate.get("slug") or "").strip()
        title = str(candidate.get("title") or candidate.get("slug") or ref)
        tags = candidate.get("tags")
        clause = candidate.get("dense_clause") or candidate.get("formal_clause")
        if not ref or not _keyword_match(ref, title, tags, clause):
            continue
        rows.append(
            _governance_row(
                ref,
                kind="AxiomCandidate",
                title=title,
                why="Selected from axiom candidates as compact context for atlas self-documentation or compression behavior.",
                behavior="Route to the axiom candidate surface for evidence; do not inline raw-seed-derived clauses.",
                source_ref=(
                    "<private-raw-seed-root> - Raw-Seed Preservation, Semantic Reset, "
                    "and Fresh Execution Spine/raw_seed/system_axiom_candidates.json"
                ),
                drilldown_command=f"./repo-python kernel.py --option-surface axiom_candidates --band card --ids {ref}",
                authority_class="manual_interpretation",
                status=str(candidate.get("status") or "observed"),
            )
        )
    rows.sort(key=lambda row: row["ref"])
    return rows[:limit]


def _governing_doctrine_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_standard_governance_rows())
    rows.extend(_skill_governance_rows())
    rows.extend(_paper_module_governance_rows())
    rows.extend(_principle_governance_rows())
    rows.extend(
        _doctrine_json_governance_rows(
            kind="Concept",
            pattern="codex/doctrine/concepts/con_*.json",
            option_surface="concepts",
            limit=8,
        )
    )
    rows.extend(
        _doctrine_json_governance_rows(
            kind="Mechanism",
            pattern="codex/doctrine/mechanisms/mech_*.json",
            option_surface="mechanisms",
            limit=8,
        )
    )
    rows.extend(_axiom_governance_rows())
    return rows


def _existing_paths(pattern: str, *, glob: bool) -> list[Path]:
    if not glob:
        path = _repo(pattern)
        return [path] if path.exists() else []
    paths = sorted(REPO_ROOT.glob(pattern))
    if pattern == "docs/system_atlas/*.md":
        paths = [
            path
            for path in paths
            if path.name not in GENERATED_DOC_NAMES and not path.name.endswith(".generated.md")
        ]
    return [path for path in paths if path.is_file()]


def collect_source_inputs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in SOURCE_SPECS:
        paths = _existing_paths(spec.path, glob=spec.glob)
        if spec.glob:
            mtimes = [_iso_from_timestamp(path.stat().st_mtime) for path in paths]
            rows.append(
                {
                    "source_id": spec.source_id,
                    "path": spec.path,
                    "kind": spec.kind,
                    "exists": bool(paths),
                    "count": len(paths),
                    "count_only": spec.count_only,
                    "latest_mtime": max(mtimes) if mtimes else None,
                    "paths": [_rel(path) for path in paths] if not spec.count_only else [],
                }
            )
        else:
            path = _repo(spec.path)
            rows.append(
                {
                    "source_id": spec.source_id,
                    "path": spec.path,
                    "kind": spec.kind,
                    "exists": path.exists(),
                    "count": 1 if path.exists() else 0,
                    "count_only": spec.count_only,
                    "latest_mtime": _iso_from_timestamp(path.stat().st_mtime) if path.exists() else None,
                    "paths": [spec.path] if path.exists() and not spec.count_only else [],
                }
            )
    return rows


def _generated_at(source_inputs: list[dict[str, Any]]) -> str:
    mtimes = [row.get("latest_mtime") for row in source_inputs if row.get("latest_mtime")]
    if not mtimes:
        return "1970-01-01T00:00:00Z"
    return str(max(mtimes))


def _count_standard_files() -> int:
    return len(_existing_paths("codex/standards/**/std_*.json", glob=True))


def _manual_atlas_docs() -> list[str]:
    return [_rel(path) for path in _existing_paths("docs/system_atlas/*.md", glob=True)]


def _paper_module_count() -> int:
    data = _read_json("codex/doctrine/paper_modules/_index.json")
    modules = data.get("modules") if isinstance(data, dict) else None
    return len(modules) if isinstance(modules, list) else 0


def _paper_module_freshness() -> str:
    data = _read_json("codex/doctrine/paper_modules/_index.json")
    freshness = data.get("freshness") if isinstance(data, dict) else {}
    if isinstance(freshness, dict):
        return str(freshness.get("status") or freshness.get("sync_status") or "unknown")
    return "unknown"


def _task_ledger_counts() -> dict[str, int]:
    ledger = _read_json("state/task_ledger/ledger.json")
    work_items = ledger.get("work_items") if isinstance(ledger, dict) else None
    views = _existing_paths("state/task_ledger/views/*.json", glob=True)
    return {
        "work_items": len(work_items) if isinstance(work_items, list) else 0,
        "views": len(views),
    }


def _frontend_counts() -> dict[str, int]:
    graph = _read_json("state/frontend_navigation/navigation_graph.json")
    component_index = _read_json("state/frontend_navigation/component_index.json")
    views = graph.get("views") if isinstance(graph, dict) else None
    components = component_index.get("components") if isinstance(component_index, dict) else None
    return {
        "views": len(views) if isinstance(views, (list, dict)) else 0,
        "components": len(components) if isinstance(components, list) else 0,
    }


def _frontend_view_entities() -> list[dict[str, Any]]:
    graph = _read_json("state/frontend_navigation/navigation_graph.json")
    views = graph.get("views") if isinstance(graph, dict) else []
    if not isinstance(views, list):
        return []

    entities: list[dict[str, Any]] = []
    for row in views:
        if not isinstance(row, dict):
            continue
        view_id = str(row.get("id") or "").strip()
        if not view_id:
            continue
        label = str(row.get("label") or view_id)
        purpose = _compact_text(row.get("purpose") or label, max_chars=260)
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        source_file = str(evidence.get("file") or "").strip()
        source_line = evidence.get("line")
        capture = row.get("capture") if isinstance(row.get("capture"), dict) else {}
        surface_audit = row.get("surface_audit") if isinstance(row.get("surface_audit"), dict) else {}
        evidence_refs = [
            ref
            for ref in list(surface_audit.get("evidence_refs") or [])
            if isinstance(ref, str) and ref.strip()
        ]
        evidence_paths = [
            "state/frontend_navigation/navigation_graph.json",
            "state/frontend_navigation/component_index.json",
        ]
        if source_file:
            evidence_paths.append(source_file)
        evidence_paths.extend(ref for ref in evidence_refs if "/" in ref and not ref.startswith("/"))
        evidence_paths = list(dict.fromkeys(evidence_paths))[:12]
        semantic_health = str(surface_audit.get("semantic_health") or "").strip()
        maturity = "working" if semantic_health in {"live", "healthy", "available"} else "partial"
        route = str(row.get("route") or row.get("entry_route") or "").strip()
        aliases = [
            alias
            for alias in list(row.get("route_aliases") or [])
            if isinstance(alias, str) and alias.strip()
        ]
        capture_slug = str(capture.get("slug") or "").strip()
        source_ref = f"{source_file}:{source_line}" if source_file and source_line else source_file
        entities.append(
            _entity(
                view_id,
                kind="FrontendView",
                title=label,
                summary=purpose,
                authority_class="derived_projection",
                source_of_truth=[
                    "state/frontend_navigation/navigation_graph.json",
                    "system/server/ui/src",
                    "tools/meta/observability/frontend_nav_graph.py",
                ],
                evidence_paths=evidence_paths,
                maturity=maturity,
                risk_level="medium",
                disclosure_class="controlled_private_review",
                freshness_status="fresh",
                owning_module="frontend_navigation_plane",
                safe_agent_actions=[
                    "open the frontend_views option-surface card before reading UI source",
                    "use the view-agent packet for view contract, render evidence, and authority boundary",
                    "run frontend navigation graph and root coverage checks before treating counts as current",
                ],
                forbidden_agent_actions=[
                    "treat TSX prose, screenshots, or generated images as ontology authority",
                    "hand-edit generated frontend navigation graph rows",
                    "publish private view evidence without disclosure review",
                ],
                next_drilldowns=[
                    f"./repo-python kernel.py --option-surface frontend_views --band card --ids {view_id}",
                    f"./repo-python kernel.py --view-agent-packet {view_id}",
                    f"./repo-python kernel.py --view {view_id}",
                    "./repo-python tools/meta/observability/frontend_nav_graph.py --check",
                    "./repo-python tools/meta/factory/build_root_coverage_state.py --check --compact",
                ],
                metrics={
                    "view_id": view_id,
                    "route": route,
                    "entry_route": row.get("entry_route"),
                    "route_aliases": aliases,
                    "capture_slug": capture_slug,
                    "fanout_count": int(row.get("fanout_count") or 0),
                    "fanin_count": int(row.get("fanin_count") or 0),
                    "shell_group": row.get("shell_group"),
                    "station_group": row.get("station_group"),
                    "semantic_health": semantic_health or "unknown",
                    "source_component_ref": {
                        "file": source_file,
                        "line": source_line,
                    },
                    "source_ref": source_ref,
                    "projection_boundary": (
                        "FrontendView atlas rows project the generated navigation graph; "
                        "UI implementation remains in system/server/ui/src and graph refresh remains owner-tool generated."
                    ),
                    "validation_route": [
                        f"./repo-python kernel.py --option-surface frontend_views --band card --ids {view_id}",
                        f"./repo-python kernel.py --view-agent-packet {view_id}",
                        "./repo-python tools/meta/observability/frontend_nav_graph.py --check",
                        "./repo-python tools/meta/factory/build_root_coverage_state.py --check --compact",
                    ],
                    "mutation_route": [
                        "Edit system/server/ui/src under the frontend navigation plane and view-contract standards.",
                        "Regenerate/check frontend navigation graph through tools/meta/observability/frontend_nav_graph.py.",
                        "Do not edit state/frontend_navigation/navigation_graph.json by hand.",
                    ],
                    "disclosure_posture": "controlled_private_review",
                    "governing_doctrine": [
                        "codex/doctrine/paper_modules/frontend_navigation_plane.md",
                        "codex/standards/std_view_contract.json",
                        "codex/standards/std_ui_receipt.json",
                    ],
                },
            )
        )
    return entities


def _provider_count() -> int:
    data = _read_json("codex/doctrine/compute/provider_registry.json")
    providers = data.get("providers") if isinstance(data, dict) else None
    return len(providers) if isinstance(providers, (list, dict)) else 0


def _compute_counts() -> dict[str, int]:
    return {
        "receipts": len(_existing_paths(COMPUTE_RECEIPTS_GLOB, glob=True)),
        "cache_rows": len(_existing_paths("state/compute_workers/cache/*.json", glob=True)),
        "run_fingerprints": len(_existing_paths("state/compute_workers/run_fingerprints/*.json", glob=True)),
    }


def _feed_counts() -> dict[str, int]:
    substrate = _existing_paths("codex/substrate/nodes/feeds/*.json", glob=True)
    mirrors = _existing_paths("codex/nodes/feeds/*.json", glob=True)
    artifacts = _existing_paths("state/runs/*/artifacts/global_*_feed.json", glob=True)
    return {
        "substrate_nodes": len(substrate),
        "mirror_nodes": len(mirrors),
        "run_artifacts": len(artifacts),
    }


def _annex_counts() -> dict[str, int]:
    distillation = _read_json("annexes/annex_distillation_index.json")
    sync_digest = _read_json("annexes/annex_sync_digest.json")
    patterns = distillation.get("patterns") if isinstance(distillation, dict) else None
    annexes = sync_digest.get("annexes") if isinstance(sync_digest, dict) else None
    sync_rows = sync_digest.get("rows") if isinstance(sync_digest, dict) else None
    return {
        "distillation_patterns": (
            int(distillation.get("pattern_count") or 0)
            if isinstance(distillation, dict)
            else 0
        )
        or (len(patterns) if isinstance(patterns, (list, dict)) else 0),
        "sync_digest_annexes": (
            int(sync_digest.get("annex_count") or 0)
            if isinstance(sync_digest, dict)
            else 0
        )
        or (len(annexes) if isinstance(annexes, (list, dict)) else 0)
        or (len(sync_rows) if isinstance(sync_rows, list) else 0),
    }


def _dissemination_count() -> int:
    return len(_existing_paths("docs/dissemination/*.md", glob=True))


def _dissemination_gate_report() -> dict[str, Any]:
    report = _read_json(DISSEMINATION_GATE_REPORT_PATH)
    return report if isinstance(report, dict) else {}


def _dissemination_gate_summary() -> dict[str, Any]:
    report = _dissemination_gate_report()
    summary = report.get("summary") if isinstance(report, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    return {
        "exists": bool(report),
        "ok": bool(report.get("ok")) if report else False,
        "row_count": int(summary.get("row_count") or 0),
        "send_ready_row_count": int(summary.get("send_ready_row_count") or 0),
        "blocking_violation_count": int(summary.get("blocking_violation_count") or 0),
        "warning_count": int(summary.get("warning_count") or 0),
        "report_path": str(DISSEMINATION_GATE_REPORT_PATH),
        "markdown_path": str(DISSEMINATION_GATE_MARKDOWN_PATH),
    }


def _safe_id(value: Any, *, fallback: str = "unknown") -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_").lower()
    return text or fallback


def _paper_module_entity_id(slug: str) -> str:
    return f"pm_{_safe_id(slug)}"


def _principle_entity_id(ref: str) -> str:
    return f"principle_{_safe_id(ref)}"


def _concept_entity_id(ref: str) -> str:
    return f"concept_{_safe_id(ref)}"


def _mechanism_entity_id(ref: str) -> str:
    return f"mechanism_{_safe_id(ref)}"


def _subdomain_entity_id(ref: str) -> str:
    return f"subdomain_{_safe_id(ref)}"


def _workitem_entity_id(ref: str) -> str:
    return f"workitem_{_safe_id(ref)}"


def _dissemination_artifact_entity_id(ref: str) -> str:
    return f"dissemination_artifact_{_safe_id(ref)}"


def _sidecar_entity_id(path: str | Path) -> str:
    return f"sidecar_{_safe_id(str(path).removesuffix('.json').removesuffix('.md'))}"


def _artifact_kind_entity_id(kind_id: str) -> str:
    return f"kind_{_safe_id(kind_id)}"


def _type_plane_surface_entity_id(type_id: str) -> str:
    return f"surface_type_plane_{_safe_id(type_id)}_option_surface"


def _type_plane_validator_entity_id(type_id: str) -> str:
    return f"validator_type_plane_{_safe_id(type_id)}"


def _standard_id_from_ref(ref: str) -> str:
    return Path(str(ref or "")).stem


def _type_plane_rows() -> list[dict[str, Any]]:
    standard = _read_json(STANDARD_TYPE_PLANE_PATH)
    rows = standard.get("type_plane_rows") if isinstance(standard, dict) else []
    return [
        row
        for row in rows
        if isinstance(row, dict) and str(row.get("type_id") or "").strip()
    ]


def _type_plane_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("type_id") or "").strip(): row for row in rows}


def _type_plane_evidence(row: dict[str, Any]) -> list[str]:
    refs: list[str] = [str(STANDARD_TYPE_PLANE_PATH)]
    refs.extend(str(ref) for ref in row.get("governing_standard_refs") or [] if str(ref).strip())
    refs.extend(str(ref) for ref in row.get("projection_refs") or [] if str(ref).strip())
    seen: set[str] = set()
    out: list[str] = []
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        out.append(ref)
    return out


def _type_plane_metrics(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "status": "ingested",
        "type_id": row.get("type_id"),
        "artifact_family": row.get("artifact_family"),
        "governing_standard_refs": list(row.get("governing_standard_refs") or []),
        "source_authority": row.get("source_authority"),
        "write_contract": row.get("write_contract"),
        "read_contract": row.get("read_contract"),
        "option_surface_command": row.get("option_surface_command"),
        "atlas_projection_policy": row.get("atlas_projection_policy"),
        "currentness_policy": row.get("currentness_policy"),
        "validation_probe": list(row.get("validation_probe") or []),
        "mutation_lane": row.get("mutation_lane"),
        "projection_refs": list(row.get("projection_refs") or []),
        "known_gaps": list(row.get("known_gaps") or []),
    }


def _add_unique_entities(entities: list[dict[str, Any]], additions: list[dict[str, Any]]) -> None:
    seen = {str(entity.get("id") or "") for entity in entities if isinstance(entity, dict)}
    for entity in additions:
        entity_id = str(entity.get("id") or "")
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        entities.append(entity)


def _type_plane_standard_entities(type_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: set[str] = {str(STANDARD_TYPE_PLANE_PATH)}
    for row in type_rows:
        refs.update(str(ref) for ref in row.get("governing_standard_refs") or [] if str(ref).strip())

    entities: list[dict[str, Any]] = []
    for ref in sorted(refs):
        payload = _read_json(ref)
        standard_id = _standard_id_from_ref(ref)
        exists = _repo(ref).exists()
        title = payload.get("title") if isinstance(payload, dict) else None
        summary = payload.get("summary") if isinstance(payload, dict) else None
        entities.append(
            _entity(
                standard_id,
                kind="Standard",
                title=str(title or standard_id),
                summary=_compact_text(
                    summary
                    or f"Governing standard {standard_id} referenced by the standards type plane.",
                    max_chars=220,
                ),
                authority_class="manual_interpretation",
                source_of_truth=[ref],
                evidence_paths=[ref, str(STANDARD_TYPE_PLANE_PATH)],
                maturity="working" if exists else "planned",
                risk_level="low" if exists else "medium",
                disclosure_class="public_open_source",
                freshness_status="fresh" if exists else "generated_missing",
                owning_module="std_standard_type_plane",
                next_drilldowns=[
                    f"./repo-python kernel.py --option-surface standards --band card --ids {standard_id}",
                    f"jq '.' {ref}",
                ],
                metrics={
                    "standard_ref": ref,
                    "projection_source": str(STANDARD_TYPE_PLANE_PATH),
                    "referenced_by_type_plane": True,
                },
            )
        )
    return entities


def _type_plane_artifact_entities(
    type_rows: list[dict[str, Any]],
    *,
    existing_entity_ids: set[str],
) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for row in sorted(type_rows, key=lambda item: str(item.get("type_id") or "")):
        type_id = str(row.get("type_id") or "").strip()
        entity_id = _artifact_kind_entity_id(type_id)
        if not type_id or entity_id in existing_entity_ids:
            continue
        evidence = _type_plane_evidence(row)
        entities.append(
            _entity(
                entity_id,
                kind="ArtifactKind",
                title=str(row.get("title") or type_id),
                summary=(
                    f"Standards type-plane artifact kind {type_id}: "
                    f"artifact_family={row.get('artifact_family') or 'unknown'}; "
                    "source authority and mutation lane come from std_standard_type_plane."
                ),
                authority_class="derived_projection",
                source_of_truth=evidence,
                evidence_paths=evidence[:12],
                maturity="observed",
                risk_level="medium",
                disclosure_class="controlled_private_review",
                freshness_status="fresh",
                related_workitems=["cap_atlas_standard_type_plane_ingestion"],
                owning_module="std_standard_type_plane",
                safe_agent_actions=[
                    "use this row to find the governing standard and browse command for the artifact type",
                    "route mutation back to the governing standard and source authority",
                    "open the navigation_type_plane card before promoting exact type claims",
                ],
                forbidden_agent_actions=[
                    "treat the System Atlas projection as the type contract authority",
                    "hand-edit generated atlas state to change type-plane rows",
                ],
                next_drilldowns=[
                    f"./repo-python kernel.py --option-surface navigation_type_plane --band card --ids {type_id}",
                    str(row.get("option_surface_command") or ""),
                ],
                metrics={
                    "kind_id": type_id,
                    "standard_type_plane": _type_plane_metrics(row),
                },
            )
        )
    return entities


def _type_plane_surface_entities(type_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for row in sorted(type_rows, key=lambda item: str(item.get("type_id") or "")):
        type_id = str(row.get("type_id") or "").strip()
        command = str(row.get("option_surface_command") or "").strip()
        if not type_id or not command:
            continue
        evidence = _type_plane_evidence(row)
        entities.append(
            _entity(
                _type_plane_surface_entity_id(type_id),
                kind="Surface",
                title=f"{row.get('title') or type_id} option surface",
                summary=f"Browse surface declared by std_standard_type_plane for artifact type {type_id}: {command}.",
                authority_class="derived_projection",
                source_of_truth=evidence,
                evidence_paths=evidence[:12],
                maturity="working" if "--option-surface" in command or command.startswith("./repo-python") else "observed",
                risk_level="medium",
                disclosure_class="controlled_private_review",
                freshness_status="fresh",
                related_workitems=["cap_atlas_standard_type_plane_ingestion"],
                owning_module="std_standard_type_plane",
                safe_agent_actions=[
                    "use the command as a browse route after entry/context selects the artifact type",
                    "keep low-band rows thin and reopen card drilldowns for evidence",
                ],
                forbidden_agent_actions=[
                    "treat the command output as mutation authority",
                    "use the surface as first-contact control without entry selection",
                ],
                next_drilldowns=[command],
                metrics={
                    "type_id": type_id,
                    "option_surface_command": command,
                    "read_contract": row.get("read_contract"),
                },
            )
        )
    return entities


def _type_plane_validator_entities(type_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for row in sorted(type_rows, key=lambda item: str(item.get("type_id") or "")):
        type_id = str(row.get("type_id") or "").strip()
        probes = [str(probe) for probe in row.get("validation_probe") or [] if str(probe).strip()]
        if not type_id or not probes:
            continue
        evidence = _type_plane_evidence(row)
        entities.append(
            _entity(
                _type_plane_validator_entity_id(type_id),
                kind="Validator",
                title=f"{row.get('title') or type_id} validation probes",
                summary=f"Validation probes declared by std_standard_type_plane for artifact type {type_id}.",
                authority_class="derived_projection",
                source_of_truth=evidence,
                evidence_paths=evidence[:12],
                maturity="observed",
                risk_level="medium",
                disclosure_class="controlled_private_review",
                freshness_status="fresh",
                related_workitems=["cap_atlas_standard_type_plane_ingestion"],
                owning_module="std_standard_type_plane",
                safe_agent_actions=[
                    "run the probes named by the governing standard before closing type-plane claims",
                    "treat probe commands as validation hints until focused output is observed",
                ],
                forbidden_agent_actions=[
                    "declare atlas freshness from the validator row alone",
                    "replace builder checks with source-body inspection",
                ],
                next_drilldowns=probes[:8],
                metrics={
                    "type_id": type_id,
                    "validation_probe": probes,
                },
            )
        )
    return entities


def _kind_atlas_rows() -> list[dict[str, Any]]:
    try:
        from system.lib.kind_atlas import build_kind_atlas
    except ImportError:
        return []
    payload = build_kind_atlas(REPO_ROOT, band="flag")
    rows = payload.get("rows") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict) and str(row.get("kind_id") or "").strip()]


def _atlas_materialized_count(kind_id: str, entities: list[dict[str, Any]]) -> int:
    """Count row-level System Atlas materialization for one browsable kind.

    Domains often carry count-only summaries for large surfaces. This metric is
    deliberately stricter: it asks whether the atlas has selectable entity rows
    for the same underlying items exposed by the Kind Atlas/option surface.
    """
    entity_ids = [str(entity.get("id") or "") for entity in entities if isinstance(entity, dict)]
    entity_kinds = [str(entity.get("kind") or "") for entity in entities if isinstance(entity, dict)]
    if kind_id == "paper_modules":
        return sum(1 for entity_id in entity_ids if entity_id.startswith("pm_"))
    if kind_id == "standards":
        return sum(1 for entity_id in entity_ids if entity_id.startswith("std_"))
    if kind_id == "task_ledger":
        return sum(1 for entity_id in entity_ids if entity_id.startswith("workitem_"))
    if kind_id == "principles":
        return sum(1 for entity_id in entity_ids if entity_id.startswith("principle_"))
    if kind_id == "concepts":
        return sum(1 for entity_id in entity_ids if entity_id.startswith("concept_"))
    if kind_id == "mechanisms":
        return sum(1 for entity_id in entity_ids if entity_id.startswith("mechanism_"))
    if kind_id == "frontend_views":
        return entity_kinds.count("FrontendView")
    if kind_id == "frontend_components":
        return entity_kinds.count("FrontendComponent")
    if kind_id == "raw_seed_shards":
        return entity_kinds.count("RawSeedShard")
    if kind_id in {"annex_patterns", "annex_distillation_patterns"}:
        return entity_kinds.count("Annex")
    return 0


def _cluster_command_from_kind_row(kind_row: dict[str, Any]) -> str | None:
    """Resolve the cluster_flag option-surface command from a Kind Atlas row.

    Some kind_atlas rows (e.g. transform_job_receipts, row_patches,
    skill_compression_debt, github_import_candidates) declare ``cluster_flag``
    in their ``bands`` but ship ``cluster_command=null`` because they are
    constructed by ``system.lib.kernel.commands.generated_artifact_surfaces``
    rather than the canonical ``_row()`` helper that auto-derives
    ``cluster_command`` from ``option_surface_command``. The atlas
    materialization layer has to read both fields to find the cluster command,
    otherwise an actionable cluster surface is hidden behind an erroneous
    ``no_option_surface_cluster_command`` skip.
    """
    candidates = [
        kind_row.get("cluster_command"),
        kind_row.get("option_surface_command"),
    ]
    for candidate in candidates:
        command = str(candidate or "").strip()
        if "--option-surface" in command and "--band cluster_flag" in command:
            return command
    return None


def _kind_cluster_projection(
    repo_root: Path,
    kind_row: dict[str, Any],
    *,
    max_clusters: int = 8,
    max_top_ids_per_cluster: int = 4,
) -> dict[str, Any]:
    """Fetch a compact cluster_flag digest for one ArtifactKind row.

    High-cardinality kinds historically presented as ``count_or_surface_only``
    with row-level materialization=0 even when their cluster_flag option
    surface already exposes actionable group rows (server_backend, kernel_lib,
    derive_flag, ...). This helper turns that hidden surface into an inline
    atlas affordance for the ArtifactKind card and projection-gap finding.
    Failures degrade to ``available=False``; the row falls back to count-only.
    """
    kind_id = str(kind_row.get("kind_id") or "").strip()
    cluster_command = _cluster_command_from_kind_row(kind_row)

    def _empty(reason: str) -> dict[str, Any]:
        return {
            "available": False,
            "cluster_count": 0,
            "top_clusters": [],
            "summary_text": "",
            "cluster_command": cluster_command,
            "skip_reason": reason,
        }

    if not kind_id or kind_id == "system_atlas":
        return _empty("self_referential_or_blank")
    if not cluster_command:
        return _empty("no_option_surface_cluster_command")
    try:
        from system.lib.standard_option_surface import build_option_surface

        payload = build_option_surface(repo_root, kind_id, band="cluster_flag")
    except Exception as exc:  # noqa: BLE001 - guard the atlas build path
        return _empty(f"build_option_surface_error:{type(exc).__name__}")
    if not isinstance(payload, dict) or payload.get("profile_status") != "supported":
        status = payload.get("profile_status") if isinstance(payload, dict) else "non_dict_payload"
        return _empty(f"profile_status:{status}")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        return _empty("no_cluster_rows")

    cluster_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cluster_id = str(
            row.get("cluster_id")
            or row.get("group_id")
            or row.get("row_id")
            or row.get("id")
            or ""
        ).strip()
        if not cluster_id:
            continue
        label = str(
            row.get("label")
            or row.get("group_label")
            or row.get("title")
            or cluster_id
        )
        count = 0
        for key in ("count", "scope_count", "file_count", "row_count", "annex_count"):
            try:
                value = int(row.get(key) or 0)
            except (TypeError, ValueError):
                continue
            if value > 0:
                count = value
                break
        top_ids = [
            str(item)
            for item in list(row.get("top_ids") or [])[:max_top_ids_per_cluster]
            if str(item).strip()
        ]
        cluster_rows.append(
            {
                "cluster_id": cluster_id,
                "label": label,
                "count": count,
                "top_ids": top_ids,
            }
        )
    if not cluster_rows:
        return _empty("no_named_clusters")
    cluster_rows.sort(
        key=lambda item: (-int(item.get("count") or 0), str(item.get("cluster_id") or ""))
    )
    top_clusters = cluster_rows[:max_clusters]
    cluster_count = len(cluster_rows)
    summary_parts = [f"{item['cluster_id']} [{item['count']}]" for item in top_clusters[:3]]
    summary_text = (
        f"{cluster_count} cluster group(s) browsable; top: {', '.join(summary_parts)}"
        if summary_parts
        else f"{cluster_count} cluster group(s) browsable"
    )
    return {
        "available": True,
        "cluster_count": cluster_count,
        "top_clusters": top_clusters,
        "summary_text": summary_text,
        "cluster_command": cluster_command,
        "skip_reason": None,
    }


def _kind_cluster_projections(
    repo_root: Path,
    kind_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Pre-compute cluster_flag digests for every ArtifactKind row, by kind_id."""
    out: dict[str, dict[str, Any]] = {}
    for row in kind_rows:
        kind_id = str(row.get("kind_id") or "").strip()
        if not kind_id:
            continue
        out[kind_id] = _kind_cluster_projection(repo_root, row)
    return out


def _cluster_descriptor_top_ids(top_clusters: list[dict[str, Any]], *, limit: int = 3) -> str:
    parts = [
        f"{item.get('cluster_id')} [{int(item.get('count') or 0)}]"
        for item in list(top_clusters or [])[:limit]
        if str(item.get("cluster_id") or "").strip()
    ]
    return ", ".join(parts)


def _freshness_from_kind_row(row: dict[str, Any]) -> str:
    if str(row.get("kind_id") or "") == "system_atlas":
        return "fresh"
    currentness = row.get("currentness") if isinstance(row.get("currentness"), dict) else {}
    status = str(currentness.get("status") or "").lower()
    if "missing" in status:
        return "generated_missing"
    if "stale" in status:
        return "stale"
    if "source_changed" in status:
        return "source_changed"
    if "unknown" in status:
        return "unknown"
    if status:
        return "fresh"
    return "unknown"


def _artifact_kind_entities(
    kind_rows: list[dict[str, Any]],
    base_entities: list[dict[str, Any]],
    cluster_projections: dict[str, dict[str, Any]] | None = None,
    type_plane_lookup: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    cluster_projections = cluster_projections or {}
    type_plane_lookup = type_plane_lookup or {}
    entities: list[dict[str, Any]] = []
    for row in sorted(kind_rows, key=lambda item: str(item.get("kind_id") or "")):
        kind_id = str(row.get("kind_id") or "").strip()
        if not kind_id:
            continue
        type_plane_row = type_plane_lookup.get(kind_id) or {}
        row_count = 0 if kind_id == "system_atlas" else int(row.get("row_count") or 0)
        materialized_count = _atlas_materialized_count(kind_id, base_entities)
        cluster_projection = cluster_projections.get(kind_id) or {}
        cluster_available = bool(cluster_projection.get("available"))
        cluster_count = int(cluster_projection.get("cluster_count") or 0)
        top_clusters = list(cluster_projection.get("top_clusters") or [])
        top_clusters_descriptor = _cluster_descriptor_top_ids(top_clusters)
        materialization_status = (
            "self_referential_count_deferred"
            if kind_id == "system_atlas"
            else "row_level_materialized"
            if row_count and materialized_count >= row_count
            else "partial_row_level_materialization"
            if materialized_count
            else "cluster_materialized"
            if row_count and cluster_available
            else "count_or_surface_only"
            if row_count
            else "empty_or_unknown_source"
        )
        maturity = "working" if materialization_status == "row_level_materialized" else "partial"
        risk_level = "low" if maturity == "working" else "medium"
        commands = [
            str(row.get("cluster_command") or ""),
            str(row.get("option_surface_command") or ""),
            str(row.get("card_command") or ""),
            str(row.get("evidence_command") or ""),
        ]
        next_drilldowns = [command for command in commands if command]
        source_refs = [
            str(ref)
            for ref in list(row.get("governing_standard_refs") or []) + list(row.get("projection_refs") or [])
            if str(ref).strip()
        ]
        if type_plane_row:
            source_refs = _type_plane_evidence(type_plane_row) + source_refs
        source_refs.append("system/lib/kind_atlas.py")
        source_refs = list(dict.fromkeys(source_refs))
        if cluster_available and top_clusters_descriptor:
            cluster_clause = (
                f" and surfaces {cluster_count} cluster group(s) (top: {top_clusters_descriptor})"
            )
        elif cluster_available:
            cluster_clause = f" and surfaces {cluster_count} cluster group(s)"
        else:
            cluster_clause = ""
        summary = (
            f"Artifact kind {kind_id}: Kind Atlas exposes {row_count} browse row(s); "
            f"System Atlas materializes {materialized_count} row-level entity row(s)"
            f"{cluster_clause}; "
            f"status={materialization_status}."
        )
        currentness = row.get("currentness") if isinstance(row.get("currentness"), dict) else {}
        if kind_id == "system_atlas":
            currentness = {
                "status": "self_referential_currentness_deferred",
                "generated_at": None,
                "source_refs_checked": [
                    "codex/standards/std_system_atlas.json",
                    "tools/meta/factory/build_system_atlas.py",
                ],
                "defer_reason": "Avoid recursive graph mtime churn while the atlas indexes its own ArtifactKind row.",
            }
        entities.append(
            _entity(
                _artifact_kind_entity_id(kind_id),
                kind="ArtifactKind",
                title=str(row.get("title") or kind_id),
                summary=summary,
                authority_class="derived_projection",
                source_of_truth=source_refs,
                evidence_paths=source_refs[:12],
                maturity=maturity,
                risk_level=risk_level,
                disclosure_class="controlled_private_review",
                freshness_status=_freshness_from_kind_row(row),
                owning_module="system_self_comprehension_root",
                safe_agent_actions=[
                    "use the named option surface or legacy command to browse this artifact kind",
                    "treat atlas materialization metrics as coverage diagnostics, not source truth",
                    "open selected row cards before promoting claims",
                ],
                forbidden_agent_actions=[
                    "infer row-level source absence from an atlas materialization gap",
                    "hand-edit generated System Atlas state to close a coverage gap",
                ],
                next_drilldowns=next_drilldowns,
                metrics={
                    "kind_id": kind_id,
                    "kind_atlas_row_count": row_count,
                    "kind_atlas_row_count_source": "self_referential_count_deferred"
                    if kind_id == "system_atlas"
                    else "kind_atlas.row_count",
                    "atlas_materialized_entity_count": materialized_count,
                    "atlas_materialized_cluster_count": cluster_count,
                    "atlas_materialization_status": materialization_status,
                    "support_status": row.get("support_status"),
                    "bands": list(row.get("bands") or []),
                    "governing_standard_refs": list(row.get("governing_standard_refs") or []),
                    "projection_refs": list(row.get("projection_refs") or []),
                    "currentness": currentness,
                    "row_count_semantics": row.get("row_count_semantics")
                    if isinstance(row.get("row_count_semantics"), dict)
                    else {},
                    "profile_gap": row.get("profile_gap") if isinstance(row.get("profile_gap"), dict) else None,
                    "cluster_summary": {
                        "available": cluster_available,
                        "cluster_count": cluster_count,
                        "top_clusters": top_clusters,
                        "summary_text": str(cluster_projection.get("summary_text") or ""),
                        "cluster_command": cluster_projection.get("cluster_command"),
                        "skip_reason": cluster_projection.get("skip_reason"),
                    },
                    "standard_type_plane": _type_plane_metrics(type_plane_row),
                },
            )
        )
    return entities


def _artifact_kind_projection_gap_findings(
    kind_rows: list[dict[str, Any]],
    base_entities: list[dict[str, Any]],
    cluster_projections: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    cluster_projections = cluster_projections or {}
    findings: list[dict[str, Any]] = []
    for row in sorted(kind_rows, key=lambda item: str(item.get("kind_id") or "")):
        kind_id = str(row.get("kind_id") or "").strip()
        if not kind_id or kind_id == "system_atlas":
            continue
        row_count = int(row.get("row_count") or 0)
        materialized_count = _atlas_materialized_count(kind_id, base_entities)
        if row_count <= 0:
            semantics = row.get("row_count_semantics") if isinstance(row.get("row_count_semantics"), dict) else {}
            if semantics.get("zero_means") == "unknown_not_empty":
                findings.append(
                    _finding(
                        f"unknown_{kind_id}_row_count",
                        kind="coverage_gap",
                        severity="warning",
                        title=f"Unknown row count for artifact kind: {kind_id}",
                        summary=(
                            f"Kind Atlas marks {kind_id} as unknown rather than empty; "
                            "System Atlas cannot classify coverage without a refreshable count."
                        ),
                        evidence_paths=list(row.get("projection_refs") or [])[:8],
                        related_entity_ids=[_artifact_kind_entity_id(kind_id), "dom_system_atlas"],
                        recommended_action=str(
                            semantics.get("drilldown_command")
                            or row.get("evidence_command")
                            or "Add a refreshable count source for this artifact kind."
                        ),
                    )
                )
            continue
        if materialized_count >= row_count:
            continue
        cluster_projection = cluster_projections.get(kind_id) or {}
        cluster_available = bool(cluster_projection.get("available"))
        cluster_count = int(cluster_projection.get("cluster_count") or 0)
        top_clusters = list(cluster_projection.get("top_clusters") or [])
        top_clusters_descriptor = _cluster_descriptor_top_ids(top_clusters)
        cluster_command = str(cluster_projection.get("cluster_command") or row.get("cluster_command") or "")
        if cluster_available:
            descriptor = (
                f" but records {cluster_count} cluster group(s)"
                + (f" (top: {top_clusters_descriptor})" if top_clusters_descriptor else "")
            )
            finding_summary = (
                f"Kind Atlas exposes {row_count} {kind_id} row(s); System Atlas materializes "
                f"{materialized_count} row-level entity row(s){descriptor}. Cluster-tier projection "
                "is browsable; row-level materialization remains a coverage debt."
            )
            recommended_action = (
                (
                    f"Browse the cluster surface for orientation: {cluster_command}. "
                    if cluster_command
                    else ""
                )
                + "To close the row-level gap, extend tools/meta/factory/build_system_atlas.py "
                "ingestion for this kind or mark the ArtifactKind row as intentionally count-only "
                "with a governing-standard reason."
            )
        else:
            finding_summary = (
                f"Kind Atlas exposes {row_count} {kind_id} row(s), but System Atlas currently "
                f"materializes {materialized_count} row-level entity row(s). The option surface may still be complete; "
                "this finding means the unified atlas has not ingested that row set as atlas entities."
            )
            recommended_action = (
                "Extend tools/meta/factory/build_system_atlas.py ingestion for this kind or mark the ArtifactKind row "
                "as intentionally count-only with a governing-standard reason."
            )
        findings.append(
            _finding(
                f"atlas_projection_gap_{kind_id}",
                kind="coverage_gap",
                severity="warning",
                title=f"Atlas row-level projection gap: {kind_id}",
                summary=finding_summary,
                evidence_paths=list(row.get("projection_refs") or [])[:8] or ["system/lib/kind_atlas.py"],
                related_entity_ids=[_artifact_kind_entity_id(kind_id), "dom_system_atlas"],
                recommended_action=recommended_action,
            )
        )
    return findings


def _metabolism_component_entities() -> list[dict[str, Any]]:
    status_path = "state/metabolism/metabolism_status.json"
    blackboard_path = "state/metabolism/blackboard.json"
    sqlite_path = "state/metabolism/metabolism.sqlite"
    status_exists = _repo(status_path).exists()
    blackboard_exists = _repo(blackboard_path).exists()
    sqlite_exists = _repo(sqlite_path).exists()
    return [
        _entity(
            "metabolismd",
            kind="RuntimeCommand",
            title="metabolismd metabolic backplane",
            summary=(
                "Resident deferrable-work coordinator: owns queue state, pressure/provider gates, "
                "blackboard/runtime projections, claim recovery, and safe launch of allowlisted work; "
                "does not own operator intent, doctrine truth, WorkItem ranking, or semantic judgment."
            ),
            authority_class="runtime_observation",
            source_of_truth=[
                "docs/metabolismd.md",
                "codex/doctrine/paper_modules/continuous_runtime_layer.md",
                "codex/doctrine/paper_modules/autonomy_always_on_daemon_contract.md",
                "codex/standards/std_metabolism_status.json",
                "tools/meta/control/metabolismd.py",
                "system/lib/metabolism_scheduler.py",
                "system/lib/metabolism_governor.py",
                "system/lib/metabolism_store.py",
            ],
            evidence_paths=[
                "docs/metabolismd.md",
                "codex/doctrine/paper_modules/continuous_runtime_layer.md",
                "codex/doctrine/paper_modules/autonomy_always_on_daemon_contract.md",
                "codex/standards/std_metabolism_status.json",
                "tools/meta/control/metabolismd.py",
                status_path,
                blackboard_path,
                sqlite_path,
            ],
            maturity="working",
            risk_level="medium",
            disclosure_class="controlled_private_review",
            freshness_status="fresh" if status_exists and blackboard_exists else "unknown",
            related_workitems=[
                "cap_quick_launchable_operations_landing_surface_contract",
                "cap_quick_workitem_candidate_provider_metabolism_m_80859bd83e05",
                "cap_quick_metabolism_as_first_class_doctrine_primi_fda72f457bdf",
            ],
            owning_module="continuous_runtime_layer",
            safe_agent_actions=[
                "read status, doctor, and blackboard projections before dispatch decisions",
                "treat metabolismd as a coordinator over authorized work, not as a semantic owner",
                "add automatic jobs only through the launchable-operation allowlist and landing contract",
            ],
            forbidden_agent_actions=[
                "treat metabolismd as a second brain or WorkItem-ranking authority",
                "dispatch arbitrary shell outside system/lib/launchable_operations.py",
                "use markdown projections as authority over JSON, SQLite, or owner tools",
            ],
            next_drilldowns=[
                "./repo-python -m tools.meta.control.metabolismd status --json",
                "./repo-python -m tools.meta.control.metabolismd doctor --json",
                "./repo-python -m tools.meta.control.metabolismd blackboard",
                "./repo-python kernel.py --option-surface paper_modules --band card --ids continuous_runtime_layer",
                "./repo-python kernel.py --option-surface paper_modules --band card --ids autonomy_always_on_daemon_contract",
            ],
            metrics={
                "component_class": "metabolic_backplane",
                "role": "deferrable-work coordinator",
                "live_state_refs": [status_path, blackboard_path, sqlite_path],
                "status_fields": [
                    "mode",
                    "dispatch_enabled",
                    "local_pressure",
                    "active_children",
                    "waiting_jobs",
                    "running_jobs",
                    "blocked_reasons",
                ],
                "authority_owns": [
                    "durable queue",
                    "scheduler",
                    "provider budgets",
                    "local pressure gates",
                    "blackboard/runtime projections",
                    "claim recovery",
                    "safe launch of allowlisted work",
                ],
                "authority_does_not_own": [
                    "operator intent",
                    "doctrine truth",
                    "WorkItem ranking",
                    "autonomy plan compilation",
                    "semantic interpretation",
                ],
                "status_exists": status_exists,
                "blackboard_exists": blackboard_exists,
                "sqlite_exists": sqlite_exists,
            },
        ),
        _entity(
            "std_metabolism_status",
            kind="Standard",
            title="Metabolism status standard",
            summary="Status projection contract for metabolismd foreground-loop health, queue liveness, and runtime tick fields.",
            authority_class="manual_interpretation",
            source_of_truth=["codex/standards/std_metabolism_status.json"],
            evidence_paths=["codex/standards/std_metabolism_status.json"],
            maturity="working",
            risk_level="low",
            disclosure_class="public_open_source",
            freshness_status="fresh",
            owning_module="continuous_runtime_layer",
            next_drilldowns=["jq '.' codex/standards/std_metabolism_status.json"],
        ),
    ]


def _route_report() -> dict[str, Any]:
    report = _read_json("codex/doctrine/paper_modules/_route_coverage.json")
    return report if isinstance(report, dict) else {}


def _paper_module_routes_by_slug() -> dict[str, dict[str, Any]]:
    routes = _route_report().get("paper_module_routes")
    if not isinstance(routes, dict):
        return {}
    return {str(slug): row for slug, row in routes.items() if isinstance(row, dict)}


def _route_report_summary() -> dict[str, Any]:
    summary = _route_report().get("summary")
    return summary if isinstance(summary, dict) else {}


def _route_targets(route_row: dict[str, Any], axis: str) -> list[str]:
    targets: list[str] = []
    routes = route_row.get("routes")
    if not isinstance(routes, list):
        return targets
    for route in routes:
        if not isinstance(route, dict) or route.get("axis") != axis:
            continue
        target = str(route.get("target") or "").strip()
        if target and target not in targets:
            targets.append(target)
    return targets


def _first_route_target(route_row: dict[str, Any], axis: str) -> str | None:
    targets = _route_targets(route_row, axis)
    return targets[0] if targets else None


def _title_from_ref(ref: str) -> str:
    return str(ref or "").replace("_", " ").replace("-", " ").title()


def _compound_microcosm_cell_entities() -> list[dict[str, Any]]:
    """Ingest constellation compound cells as System Atlas card-band entities.

    Reads state/system_atlas/self_comprehension_microcosm_constellation.json
    (built by tools/meta/factory/build_self_comprehension_microcosm_constellation.py)
    and emits one entity per compound cell. Each entity carries cross-link refs
    to the deeper Wave 009 composition receipt / proof card / graph node when
    the constellation cell populates them, so a cold agent routing through
    `--option-surface system_atlas --band card --ids <cell_id>` can chain to
    the typed contract owner without scraping selection_reason prose.
    """
    constellation_path = "state/system_atlas/self_comprehension_microcosm_constellation.json"
    constellation_doc_path = (
        "docs/system_atlas/self_comprehension_microcosm_constellation.generated.md"
    )
    constellation_full = _repo(constellation_path)
    if not constellation_full.exists():
        return []
    try:
        data = json.loads(constellation_full.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    cells = data.get("cells") or []
    if not isinstance(cells, list):
        return []
    keystone_id = data.get("selected_keystone_cell")
    owner_cap = data.get("owner_workitem_or_cap") or "cap_microcosm_constellation_keystone_proof_cell_001"
    entities: list[dict[str, Any]] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        cell_id = str(cell.get("cell_id") or "").strip()
        if not cell_id:
            continue
        decision = str(cell.get("decision") or "unknown")
        microcosm_role = str(cell.get("microcosm_role") or "unknown")
        cluster = str(cell.get("pattern_cluster") or "unknown")
        boundary = str(cell.get("public_private_boundary") or "")
        is_keystone = cell_id == keystone_id
        existing_microcosm_count = len(cell.get("existing_microcosms") or [])
        proof_evidence_count = len(cell.get("proof_evidence") or [])
        included_pattern_count = len(cell.get("included_patterns") or [])
        composition_receipt_ref = cell.get("composition_receipt_ref")
        composition_proof_card_ref = cell.get("composition_proof_card_ref")
        composition_graph_ref = cell.get("composition_graph_ref")
        composition_graph_node_id = cell.get("composition_graph_node_id")
        evidence: list[str] = [constellation_path, constellation_doc_path]
        for ref in (
            composition_receipt_ref,
            composition_proof_card_ref,
            composition_graph_ref,
        ):
            if isinstance(ref, str) and ref and ref not in evidence:
                evidence.append(ref)
        for microcosm in cell.get("existing_microcosms") or []:
            if not isinstance(microcosm, dict):
                continue
            ref = microcosm.get("receipt_ref")
            if isinstance(ref, str) and ref:
                full_ref = f"private-macro-source/{ref}"
                if full_ref not in evidence:
                    evidence.append(full_ref)
        if decision == "blocked_until_receipt":
            maturity, risk = "partial", "medium"
        elif decision == "private_only":
            maturity, risk = "partial", "high"
        elif decision == "improve_existing":
            maturity, risk = "working", "low"
        else:  # use_existing or unknown
            maturity, risk = "working", "low"
        drilldowns: list[str] = []
        if composition_receipt_ref:
            drilldowns.append(f"./repo-python kernel.py --compile {composition_receipt_ref}")
        if composition_proof_card_ref:
            drilldowns.append(f"./repo-python kernel.py --compile {composition_proof_card_ref}")
        drilldowns.append(
            "./repo-python tools/meta/factory/build_self_comprehension_microcosm_constellation.py --check --compact"
        )
        keystone_marker = " (keystone)" if is_keystone else ""
        summary = (
            f"Compound microcosm cell {cell_id}{keystone_marker}: cluster={cluster}, "
            f"decision={decision}, role={microcosm_role}, microcosms={existing_microcosm_count}, "
            f"proof_evidence={proof_evidence_count}, included_patterns={included_pattern_count}."
        )
        title = str(cell.get("display_name") or cell_id)
        entities.append(
            _entity(
                cell_id,
                kind="CompoundMicrocosmCell",
                title=title,
                summary=summary,
                authority_class="derived_projection",
                source_of_truth=[
                    constellation_path,
                    "tools/meta/factory/build_self_comprehension_microcosm_constellation.py",
                ],
                evidence_paths=evidence,
                maturity=maturity,
                risk_level=risk,
                disclosure_class="controlled_private_review",
                freshness_status="fresh",
                related_workitems=[owner_cap],
                owning_module="self_comprehension_microcosm_constellation",
                safe_agent_actions=[
                    "open the constellation JSON or composition receipt before promoting any composition claim",
                    "treat compound cell rows as routing index, not as authority over private substrate",
                ],
                forbidden_agent_actions=[
                    "treat compound cell row as private-root equivalence",
                    "treat compound cell row as public release permission",
                    "duplicate Wave 009 composition receipt schema into the constellation cell",
                ],
                next_drilldowns=drilldowns,
                metrics={
                    "is_keystone": is_keystone,
                    "decision": decision,
                    "microcosm_role": microcosm_role,
                    "pattern_cluster": cluster,
                    "public_private_boundary": boundary,
                    "existing_microcosm_count": existing_microcosm_count,
                    "proof_evidence_count": proof_evidence_count,
                    "included_pattern_count": included_pattern_count,
                    "composition_receipt_ref": composition_receipt_ref,
                    "composition_proof_card_ref": composition_proof_card_ref,
                    "composition_graph_ref": composition_graph_ref,
                    "composition_graph_node_id": composition_graph_node_id,
                },
            )
        )
    return entities


def _paper_module_entities(
    paper_modules: dict[str, dict[str, Any]],
    route_rows: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for slug, module in sorted(paper_modules.items()):
        route_row = route_rows.get(slug, {})
        route_count = int(route_row.get("route_edge_count") or 0)
        semantic_route_count = int(route_row.get("semantic_route_edge_count") or 0)
        integrity_score = route_row.get("route_metadata_integrity_score")
        primary_subdomain = _first_route_target(route_row, "primary_subdomain")
        secondary_subdomains = _route_targets(route_row, "secondary_subdomain")
        hierarchy_context = module.get("hierarchy_context") if isinstance(module.get("hierarchy_context"), dict) else {}
        status = str(module.get("status") or route_row.get("status") or "unknown")
        freshness = (
            "source_changed"
            if str((module.get("code_loci_freshness") or {}).get("status") if isinstance(module.get("code_loci_freshness"), dict) else "")
            == "source_changed"
            else "fresh"
            if status == "up_to_date"
            else "unknown"
        )
        entities.append(
            _entity(
                _paper_module_entity_id(slug),
                kind="PaperModule",
                title=str(module.get("title") or route_row.get("title") or slug),
                summary=(
                    f"Paper module {slug}: status={status}; route_edges={route_count}; "
                    f"primary_subdomain={primary_subdomain or 'unclassified'}."
                ),
                authority_class="derived_projection",
                source_of_truth=[
                    "codex/doctrine/paper_modules/_index.json",
                    "codex/doctrine/paper_modules/_route_coverage.json",
                    str(module.get("file") or route_row.get("file") or f"codex/doctrine/paper_modules/{slug}.md"),
                ],
                evidence_paths=[
                    str(module.get("file") or route_row.get("file") or f"codex/doctrine/paper_modules/{slug}.md"),
                    "codex/doctrine/paper_modules/_index.json",
                    "codex/doctrine/paper_modules/_route_coverage.json",
                ],
                maturity="working" if status == "up_to_date" else "partial",
                risk_level="medium" if status.startswith("stale") else "low",
                disclosure_class="public_open_source",
                freshness_status=freshness,
                owning_module=slug,
                next_drilldowns=[
                    f"./repo-python kernel.py --option-surface paper_modules --band card --ids {slug}",
                    f"./repo-python kernel.py --paper-module {slug}",
                ],
                metrics={
                    "route_edge_count": route_count,
                    "semantic_route_edge_count": semantic_route_count,
                    "route_metadata_integrity_score": integrity_score,
                    "primary_subdomain": primary_subdomain,
                    "secondary_subdomains": secondary_subdomains[:8],
                    "dependency_upstream_count": len(_route_targets(route_row, "dependency_upstream")),
                    "dependency_downstream_count": len(_route_targets(route_row, "dependency_downstream")),
                    "hierarchy_assembly_role": hierarchy_context.get("assembly_role"),
                    "hierarchy_depth_from_root": hierarchy_context.get("depth_from_root"),
                    "boundary_pressure": route_row.get("boundary_pressure") or module.get("boundary_pressure"),
                    "recommended_action": module.get("recommended_action") or route_row.get("recommended_action"),
                },
            )
        )
    return entities


def _route_target_entities(route_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    principles: set[str] = set()
    concepts: set[str] = set()
    mechanisms: set[str] = set()
    subdomains: set[str] = set()
    for route_row in route_rows.values():
        principles.update(_route_targets(route_row, "governing_principle"))
        concepts.update(_route_targets(route_row, "governing_concept"))
        mechanisms.update(_route_targets(route_row, "governing_mechanism"))
        subdomains.update(_route_targets(route_row, "primary_subdomain"))
        subdomains.update(_route_targets(route_row, "secondary_subdomain"))

    entities: list[dict[str, Any]] = []
    for ref in sorted(principles):
        entities.append(
            _entity(
                _principle_entity_id(ref),
                kind="Principle",
                title=ref,
                summary=f"Principle reference {ref} materialized from paper-module governing routes.",
                authority_class="derived_projection",
                source_of_truth=[
                    "<private-raw-seed-root> - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
                    "codex/doctrine/paper_modules/_route_coverage.json",
                ],
                evidence_paths=["codex/doctrine/paper_modules/_route_coverage.json"],
                maturity="observed",
                risk_level="low",
                disclosure_class="public_open_source",
                freshness_status="fresh",
                next_drilldowns=[f"./repo-python kernel.py --option-surface principles --band card --ids {ref}"],
            )
        )
    for ref in sorted(concepts):
        entities.append(
            _entity(
                _concept_entity_id(ref),
                kind="Concept",
                title=ref,
                summary=f"Concept reference {ref} materialized from paper-module governing routes.",
                authority_class="derived_projection",
                source_of_truth=["codex/doctrine/concepts", "codex/doctrine/paper_modules/_route_coverage.json"],
                evidence_paths=["codex/doctrine/paper_modules/_route_coverage.json"],
                maturity="observed",
                risk_level="low",
                disclosure_class="public_open_source",
                freshness_status="fresh",
                next_drilldowns=[f"./repo-python kernel.py --option-surface concepts --band card --ids {ref}"],
            )
        )
    for ref in sorted(mechanisms):
        entities.append(
            _entity(
                _mechanism_entity_id(ref),
                kind="Mechanism",
                title=ref,
                summary=f"Mechanism reference {ref} materialized from paper-module governing routes.",
                authority_class="derived_projection",
                source_of_truth=["codex/doctrine/mechanisms", "codex/doctrine/paper_modules/_route_coverage.json"],
                evidence_paths=["codex/doctrine/paper_modules/_route_coverage.json"],
                maturity="observed",
                risk_level="low",
                disclosure_class="public_open_source",
                freshness_status="fresh",
                next_drilldowns=[f"./repo-python kernel.py --option-surface mechanisms --band card --ids {ref}"],
            )
        )
    for ref in sorted(subdomains):
        entities.append(
            _entity(
                _subdomain_entity_id(ref),
                kind="Domain",
                title=f"Paper-module subdomain: {_title_from_ref(ref)}",
                summary=f"Paper-module subdomain route target {ref}; classification comes from paper-module route coverage.",
                authority_class="derived_projection",
                source_of_truth=["codex/doctrine/paper_modules/_route_coverage.json", "codex/standards/std_paper_module.json"],
                evidence_paths=["codex/doctrine/paper_modules/_route_coverage.json", "codex/standards/std_paper_module.json"],
                maturity="observed",
                risk_level="low",
                disclosure_class="public_open_source",
                freshness_status="fresh",
                next_drilldowns=["./repo-python kernel.py --option-surface paper_modules --band cluster_flag"],
                metrics={"route_axis": "paper_module_subdomain", "route_target": ref},
            )
        )
    return entities


def _selected_workitems() -> list[dict[str, Any]]:
    ledger = _read_json("state/task_ledger/ledger.json")
    work_items = ledger.get("work_items") if isinstance(ledger, dict) else []
    if not isinstance(work_items, list):
        return []
    needles = (
        "system_self_comprehension_root",
        "system self-comprehension root",
        "system_self_comprehension_packet",
        "system packet",
        "system_self_comprehension_spine",
        "system self-comprehension",
        "system atlas",
        "system_atlas",
        "substrate atlas",
        "paper module",
        "paper-module",
        "dissemination",
    )
    out: list[dict[str, Any]] = []
    for item in work_items:
        if not isinstance(item, dict):
            continue
        text = json.dumps(item, sort_keys=True).casefold()
        item_id = str(item.get("id") or "")
        if item_id == "system_self_comprehension_spine_p0" or any(needle in text for needle in needles):
            out.append(item)
    return out


def _workitem_entities(workitems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for item in sorted(workitems, key=lambda row: str(row.get("id") or "")):
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        entities.append(
            _entity(
                _workitem_entity_id(item_id),
                kind="WorkItem",
                title=str(item.get("title") or item_id),
                summary=f"Task Ledger WorkItem {item_id}: state={item.get('state') or item.get('status') or 'unknown'}.",
                authority_class="derived_projection",
                source_of_truth=["state/task_ledger/ledger.json"],
                evidence_paths=["state/task_ledger/ledger.json"],
                maturity="working" if str(item.get("state") or item.get("status") or "") in {"claimed", "done"} else "observed",
                risk_level="medium",
                disclosure_class="private_root_only",
                freshness_status="fresh",
                related_workitems=[item_id],
                owning_module="operational_work_item_spine",
                next_drilldowns=[f"./repo-python kernel.py --option-surface task_ledger --band card --ids {item_id}"],
                metrics={
                    "rank": item.get("rank"),
                    "state": item.get("state") or item.get("status"),
                    "work_item_type": item.get("work_item_type"),
                },
            )
        )
    return entities


def _dissemination_artifact_entities(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    entities: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        artifact_id = str(row.get("artifact_id") or "").strip()
        if not artifact_id:
            continue
        entity_id = _dissemination_artifact_entity_id(artifact_id)
        if entity_id in seen_ids:
            continue
        seen_ids.add(entity_id)
        entities.append(
            _entity(
                entity_id,
                kind="DisseminationArtifact",
                title=artifact_id,
                summary=(
                    f"Dissemination gate row {artifact_id}: gate_status={row.get('gate_status') or 'unknown'}; "
                    f"atlas_refs={len(row.get('atlas_entity_ids') or [])}."
                ),
                authority_class="derived_projection",
                source_of_truth=[str(DISSEMINATION_GATE_REPORT_PATH), str(DISSEMINATION_GATE_MARKDOWN_PATH)],
                evidence_paths=[str(row.get("source_path") or DISSEMINATION_GATE_REPORT_PATH), str(DISSEMINATION_GATE_REPORT_PATH)],
                maturity="partial",
                risk_level="high",
                disclosure_class="controlled_private_review",
                freshness_status="fresh",
                owning_module="dissemination_strategy",
                next_drilldowns=["./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check"],
                metrics={
                    "gate_status": row.get("gate_status"),
                    "capability_ids": list(row.get("capability_ids") or [])[:8],
                    "atlas_entity_ids": list(row.get("atlas_entity_ids") or [])[:8],
                },
            )
        )
    return entities


def _sidecar_entities() -> list[dict[str, Any]]:
    specs: list[tuple[str | Path, str, str, str]] = [
        ("codex/doctrine/paper_modules/_index.json", "Paper-module index", "source", "generated_fact"),
        ("codex/doctrine/paper_modules/_route_coverage.json", "Paper-module route coverage", "source", "generated_fact"),
        ("codex/doctrine/paper_modules/_validation_report.json", "Paper-module validation report", "source", "generated_fact"),
        (GRAPH_PATH, "System Atlas graph", "output", "derived_projection"),
        (SUMMARY_PATH, "System Atlas summary", "output", "derived_projection"),
        (FACTS_PATH, "System facts at a glance", "output", "derived_projection"),
        (SNAPSHOT_PATH, "Generated System Atlas snapshot", "output", "derived_projection"),
        (FACTS_MARKDOWN_PATH, "Generated facts markdown", "output", "derived_projection"),
        (UNKNOWNS_PATH, "Generated unknowns queue", "output", "derived_projection"),
        (GOVERNING_DOCTRINE_PATH, "Generated governing doctrine", "output", "derived_projection"),
        (DISSEMINATION_GATE_REPORT_PATH, "Dissemination gate report", "source", "generated_fact"),
    ]
    entities: list[dict[str, Any]] = []
    for path_value, title, role, authority in specs:
        path = str(path_value)
        exists = _repo(path_value).exists()
        entities.append(
            _entity(
                _sidecar_entity_id(path),
                kind="GeneratedSidecar",
                title=title,
                summary=f"{title}: {role} sidecar at {path}; exists={exists}.",
                authority_class=authority,
                source_of_truth=[path],
                evidence_paths=[path],
                maturity="working" if exists else "planned",
                risk_level="medium",
                disclosure_class="controlled_private_review",
                freshness_status="fresh" if exists else "generated_missing",
                owning_module="system_self_comprehension_root",
                next_drilldowns=[f"test -f {path} && sed -n '1,120p' {path}"],
                metrics={"sidecar_role": role, "exists": exists},
            )
        )
    return entities


def _entity(
    entity_id: str,
    *,
    kind: str,
    title: str,
    summary: str,
    authority_class: str,
    source_of_truth: list[str],
    evidence_paths: list[str],
    maturity: str = "observed",
    risk_level: str = "medium",
    disclosure_class: str = "controlled_private_review",
    freshness_status: str = "unknown",
    related_workitems: list[str] | None = None,
    owning_module: str | None = None,
    safe_agent_actions: list[str] | None = None,
    forbidden_agent_actions: list[str] | None = None,
    next_drilldowns: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": entity_id,
        "kind": kind,
        "title": title,
        "summary": summary,
        "authority_class": authority_class,
        "source_of_truth": source_of_truth,
        "generated_by": BUILDER_ID,
        "evidence_paths": evidence_paths,
        "related_workitems": related_workitems or [],
        "owning_module": owning_module,
        "maturity": maturity,
        "risk_level": risk_level,
        "disclosure_class": disclosure_class,
        "freshness_status": freshness_status,
        "safe_agent_actions": safe_agent_actions or [
            "read compact option-surface rows",
            "open cited evidence paths before promoting claims",
        ],
        "forbidden_agent_actions": forbidden_agent_actions or [
            "treat atlas rows as source authority",
            "publish private-root evidence without disclosure review",
        ],
        "next_drilldowns": next_drilldowns or [],
        "metrics": metrics or {},
    }


def _edge(edge_id: str, source_id: str, target_id: str, relation: str, evidence_paths: list[str]) -> dict[str, Any]:
    return {
        "id": edge_id,
        "source_id": source_id,
        "target_id": target_id,
        "relation": relation,
        "authority_class": "derived_projection",
        "evidence_paths": evidence_paths,
    }


def _finding(
    finding_id: str,
    *,
    kind: str,
    severity: str,
    title: str,
    summary: str,
    evidence_paths: list[str],
    related_entity_ids: list[str],
    recommended_action: str,
    authority_class: str = "derived_projection",
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "kind": kind,
        "severity": severity,
        "title": title,
        "summary": summary,
        "authority_class": authority_class,
        "evidence_paths": evidence_paths,
        "related_entity_ids": related_entity_ids,
        "recommended_action": recommended_action,
    }


def build_graph(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    del repo_root  # The stage-1 builder is repo-root fixed by design.
    source_inputs = collect_source_inputs()
    generated_at = _generated_at(source_inputs)
    paper_count = _paper_module_count()
    task_counts = _task_ledger_counts()
    frontend_counts = _frontend_counts()
    feed_counts = _feed_counts()
    compute_counts = _compute_counts()
    annex_counts = _annex_counts()
    manual_docs = _manual_atlas_docs()
    governing_doctrine = _governing_doctrine_rows()
    dissemination_gate = _dissemination_gate_summary()
    dissemination_report = _dissemination_gate_report()
    paper_modules = _paper_module_lookup()
    paper_route_rows = _paper_module_routes_by_slug()
    paper_route_summary = _route_report_summary()
    selected_workitems = _selected_workitems()
    kind_rows = _kind_atlas_rows()
    kind_cluster_projections = _kind_cluster_projections(REPO_ROOT, kind_rows)
    type_plane_rows = _type_plane_rows()
    type_plane_by_id = _type_plane_lookup(type_plane_rows)

    entities = [
        _entity(
            "dom_system_atlas",
            kind="Domain",
            title="System Atlas control plane",
            summary=f"Generated System Atlas v1 over {len(manual_docs)} manual v0 atlas docs and local generated surfaces.",
            authority_class="derived_projection",
            source_of_truth=[str(STANDARD_PATH), BUILDER_ID],
            evidence_paths=[str(path) for path in manual_docs[:12]],
            maturity="partial",
            risk_level="medium",
            disclosure_class="controlled_private_review",
            freshness_status="fresh",
            related_workitems=["system_self_comprehension_spine_p0"],
            owning_module="system_self_comprehension_root",
            next_drilldowns=[
                "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                "./repo-python kernel.py --option-surface system_atlas --band card --ids dom_system_atlas",
            ],
            metrics={"manual_doc_count": len(manual_docs)},
        ),
        _entity(
            "dom_governing_doctrine",
            kind="Domain",
            title="Atlas governing doctrine alignment",
            summary=(
                f"{len(governing_doctrine)} compact standards, skills, paper modules, concepts, mechanisms, "
                "principles, and axiom candidates govern atlas routing and compression behavior."
            ),
            authority_class="derived_projection",
            source_of_truth=[
                "codex/standards",
                "codex/doctrine/skills/skill_registry.json",
                "codex/doctrine/paper_modules/_index.json",
                "codex/doctrine/concepts",
                "codex/doctrine/mechanisms",
            ],
            evidence_paths=[str(GOVERNING_DOCTRINE_PATH)],
            maturity="working",
            risk_level="low",
            disclosure_class="public_open_source",
            freshness_status="fresh",
            owning_module="system_self_comprehension_root",
            safe_agent_actions=[
                "read the generated governing-doctrine table",
                "open only selected card drilldowns for the governing row needed",
            ],
            forbidden_agent_actions=[
                "dump all principles, concepts, mechanisms, standards, or paper modules into context",
                "treat compact governance references as full doctrine evidence",
            ],
            next_drilldowns=[
                "./repo-python kernel.py --option-surface system_atlas --band card --ids dom_governing_doctrine",
                "./repo-python kernel.py --option-surface standards --band cluster_flag",
                "./repo-python kernel.py --option-surface skills --band cluster_flag",
            ],
            metrics={
                "governing_doctrine_row_count": len(governing_doctrine),
                "governing_kind_counts": dict(sorted(Counter(row["kind"] for row in governing_doctrine).items())),
            },
        ),
        _entity(
            "dom_paper_modules",
            kind="Domain",
            title="Paper module coverage",
            summary=f"{paper_count} paper modules observed from the generated paper-module index.",
            authority_class="generated_fact",
            source_of_truth=["codex/doctrine/paper_modules/_index.json"],
            evidence_paths=["codex/doctrine/paper_modules/_index.json"],
            maturity="working",
            risk_level="low",
            disclosure_class="public_open_source",
            freshness_status="fresh" if _paper_module_freshness() in {"in_sync", "fresh"} else "source_changed",
            owning_module="system_self_comprehension_root",
            next_drilldowns=["./repo-python kernel.py --option-surface paper_modules --band cluster_flag"],
            metrics={"paper_module_count": paper_count, "freshness": _paper_module_freshness()},
        ),
        _entity(
            "dom_standards",
            kind="Domain",
            title="Standards registry",
            summary=f"{_count_standard_files()} standard JSON files observed under codex/standards.",
            authority_class="generated_fact",
            source_of_truth=["codex/standards"],
            evidence_paths=["codex/standards"],
            maturity="working",
            risk_level="low",
            disclosure_class="public_open_source",
            freshness_status="fresh",
            next_drilldowns=["./repo-python kernel.py --option-surface standards --band cluster_flag"],
            metrics={"standard_count": _count_standard_files()},
        ),
        _entity(
            "dom_task_ledger",
            kind="Domain",
            title="Task Ledger WorkItem spine",
            summary=f"{task_counts['work_items']} WorkItems and {task_counts['views']} Task Ledger views observed.",
            authority_class="generated_fact",
            source_of_truth=["state/task_ledger/ledger.json", "state/task_ledger/views"],
            evidence_paths=["state/task_ledger/ledger.json", "state/task_ledger/views"],
            maturity="working",
            risk_level="medium",
            disclosure_class="private_root_only",
            freshness_status="fresh",
            owning_module="operational_work_item_spine",
            next_drilldowns=["./repo-python kernel.py --option-surface task_ledger --band cluster_flag"],
            metrics=task_counts,
        ),
        _entity(
            "dom_frontend_cockpit",
            kind="Domain",
            title="Frontend cockpit surfaces",
            summary=f"{frontend_counts['views']} frontend views and {frontend_counts['components']} indexed frontend components observed.",
            authority_class="generated_fact",
            source_of_truth=["state/frontend_navigation/navigation_graph.json", "state/frontend_navigation/component_index.json"],
            evidence_paths=["state/frontend_navigation/navigation_graph.json", "state/frontend_navigation/component_index.json"],
            maturity="working",
            risk_level="medium",
            disclosure_class="controlled_private_review",
            freshness_status="fresh",
            next_drilldowns=[
                "./repo-python kernel.py --option-surface frontend_views --band flag",
                "./repo-python kernel.py --option-surface frontend_components --band cluster_flag",
            ],
            metrics=frontend_counts,
        ),
        _entity(
            "dom_data_feeds",
            kind="Domain",
            title="Data feed lanes",
            summary=(
                f"{feed_counts['substrate_nodes']} substrate feed nodes, {feed_counts['mirror_nodes']} mirrored feed nodes, "
                f"and {feed_counts['run_artifacts']} run artifacts observed by count only."
            ),
            authority_class="runtime_observation",
            source_of_truth=["codex/substrate/nodes/feeds", "codex/nodes/feeds", "state/runs/*/artifacts/global_*_feed.json"],
            evidence_paths=["codex/substrate/nodes/feeds", "codex/nodes/feeds"],
            maturity="observed",
            risk_level="high",
            disclosure_class="private_root_only",
            freshness_status="unknown",
            next_drilldowns=["find codex/substrate/nodes/feeds codex/nodes/feeds -maxdepth 1 -type f -name '*.json'"],
            metrics=feed_counts,
        ),
        _entity(
            "dom_provider_lanes",
            kind="Domain",
            title="Provider lanes",
            summary=f"{_provider_count()} provider lanes observed from provider registry metadata.",
            authority_class="generated_fact",
            source_of_truth=["codex/doctrine/compute/provider_registry.json"],
            evidence_paths=["codex/doctrine/compute/provider_registry.json"],
            maturity="observed",
            risk_level="high",
            disclosure_class="private_root_only",
            freshness_status="unknown",
            next_drilldowns=["jq '.providers | keys' codex/doctrine/compute/provider_registry.json"],
            metrics={"provider_count": _provider_count()},
        ),
        _entity(
            "dom_compute_workers",
            kind="Domain",
            title="Compute worker receipts",
            summary=(
                f"{compute_counts['receipts']} receipts, {compute_counts['cache_rows']} cache rows, "
                f"and {compute_counts['run_fingerprints']} run fingerprints observed by count only."
            ),
            authority_class="runtime_observation",
            source_of_truth=["state/compute_workers"],
            evidence_paths=["state/compute_workers"],
            maturity="observed",
            risk_level="high",
            disclosure_class="private_root_only",
            freshness_status="unknown",
            metrics=compute_counts,
        ),
        _entity(
            "dom_annexes",
            kind="Domain",
            title="Annex import and distillation",
            summary=(
                f"{annex_counts['distillation_patterns']} annex distillation patterns and "
                f"{annex_counts['sync_digest_annexes']} sync-digest annex rows observed."
            ),
            authority_class="generated_fact",
            source_of_truth=["annexes/annex_distillation_index.json", "annexes/annex_sync_digest.json"],
            evidence_paths=["annexes/annex_distillation_index.json", "annexes/annex_sync_digest.json"],
            maturity="partial",
            risk_level="medium",
            disclosure_class="controlled_private_review",
            freshness_status="unknown",
            next_drilldowns=["./repo-python kernel.py --option-surface annex_patterns --band cluster_flag"],
            metrics=annex_counts,
        ),
        _entity(
            "dom_dissemination_gates",
            kind="Domain",
            title="Dissemination gates",
            summary=(
                f"{_dissemination_count()} dissemination markdown surfaces observed; "
                f"atlas gate checker {'passes' if dissemination_gate['ok'] else 'is not passing or missing'} "
                f"over {dissemination_gate['row_count']} gate rows."
            ),
            authority_class="generated_fact" if dissemination_gate["exists"] else "manual_interpretation",
            source_of_truth=["docs/dissemination", str(DISSEMINATION_GATE_REPORT_PATH)],
            evidence_paths=["docs/dissemination", str(DISSEMINATION_GATE_MARKDOWN_PATH)],
            maturity="working" if dissemination_gate["ok"] else "partial",
            risk_level="high",
            disclosure_class="controlled_private_review",
            freshness_status="fresh" if dissemination_gate["ok"] else "unknown",
            related_workitems=["system_self_comprehension_spine_p0"],
            owning_module="dissemination_strategy",
            next_drilldowns=[
                "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
                "find docs/dissemination -maxdepth 1 -type f -name '*.md'",
            ],
            metrics={"dissemination_doc_count": _dissemination_count(), **dissemination_gate},
        ),
        _entity(
            "std_system_atlas",
            kind="Standard",
            title="System Atlas standard",
            summary="Standard-owned schema and validation vocabulary for the generated System Atlas graph.",
            authority_class="manual_interpretation",
            source_of_truth=[str(STANDARD_PATH)],
            evidence_paths=[str(STANDARD_PATH)],
            maturity="working",
            risk_level="low",
            disclosure_class="public_open_source",
            freshness_status="fresh",
            next_drilldowns=["jq '.' codex/standards/std_system_atlas.json"],
        ),
        _entity(
            "std_lifecycle_surface_budget",
            kind="Standard",
            title="Lifecycle surface budget standard",
            summary=(
                "Resource-budget and state-access membrane for automatically invoked lifecycle hooks "
                "and adjacent control-plane surfaces."
            ),
            authority_class="manual_interpretation",
            source_of_truth=["codex/standards/std_lifecycle_surface_budget.json"],
            evidence_paths=["codex/standards/std_lifecycle_surface_budget.json"],
            maturity="working",
            risk_level="low",
            disclosure_class="public_open_source",
            freshness_status="fresh",
            related_workitems=["runtime-lifecycle-surface-budget-constitution", "lifecycle-surface-tck"],
            owning_module="std_lifecycle_surface_budget",
            next_drilldowns=[
                "./repo-python kernel.py --option-surface standards --band card --ids std_lifecycle_surface_budget",
                "jq '.budget_profile_manifest_shape' codex/standards/std_lifecycle_surface_budget.json",
            ],
            metrics={
                "governs": [
                    "lifecycle_surface_budget",
                    "runtime_hook_membrane",
                    "state_gravity",
                ]
            },
        ),
        _entity(
            "builder_system_atlas_stage1",
            kind="Builder",
            title="System Atlas stage-1 builder",
            summary="Deterministic local harvester that emits the private graph, summary, and public-safe generated markdown views.",
            authority_class="generated_fact",
            source_of_truth=[BUILDER_ID],
            evidence_paths=[BUILDER_ID],
            maturity="working",
            risk_level="medium",
            disclosure_class="controlled_private_review",
            freshness_status="fresh",
            next_drilldowns=[
                "./repo-python tools/meta/factory/build_system_atlas.py --check",
                "./repo-python tools/meta/factory/build_system_atlas.py",
            ],
        ),
    ]
    entities.extend(
        [
            _entity(
                "std_paper_module",
                kind="Standard",
                title="Paper Module standard",
                summary="Standard-owned schema for paper-module frontmatter, route axes, hierarchy context, and generated route coverage.",
                authority_class="manual_interpretation",
                source_of_truth=["codex/standards/std_paper_module.json"],
                evidence_paths=["codex/standards/std_paper_module.json"],
                maturity="working",
                risk_level="low",
                disclosure_class="public_open_source",
                freshness_status="fresh",
                next_drilldowns=["jq '.' codex/standards/std_paper_module.json"],
            )
        ]
    )
    entities.extend(_paper_module_entities(paper_modules, paper_route_rows))
    entities.append(
        _entity(
            "runtime_hook_ladder",
            kind="PaperModule",
            title="Runtime Hook Ladder alias",
            summary=(
                "Bare-card alias for canonical System Atlas entity pm_runtime_hook_ladder; "
                "paper-module entities normally use the pm_<slug> id convention."
            ),
            authority_class="derived_projection",
            source_of_truth=[
                "codex/doctrine/paper_modules/runtime_hook_ladder.md",
                "codex/doctrine/paper_modules/_index.json",
            ],
            evidence_paths=[
                "codex/doctrine/paper_modules/runtime_hook_ladder.md",
                "codex/doctrine/paper_modules/_index.json",
            ],
            maturity="working",
            risk_level="low",
            disclosure_class="public_open_source",
            freshness_status="fresh" if _paper_module_freshness() in {"in_sync", "fresh"} else "source_changed",
            owning_module="std_lifecycle_surface_budget",
            next_drilldowns=[
                "./repo-python kernel.py --option-surface system_atlas --band card --ids pm_runtime_hook_ladder",
                "./repo-python kernel.py --paper-module runtime_hook_ladder",
            ],
            metrics={"canonical_entity_id": "pm_runtime_hook_ladder", "paper_module_slug": "runtime_hook_ladder"},
        )
    )
    entities.extend(_route_target_entities(paper_route_rows))
    entities.append(_state_gravity_entity())
    entities.extend(_metabolism_component_entities())
    entities.extend(_workitem_entities(selected_workitems))
    entities.extend(_dissemination_artifact_entities(dissemination_report))
    entities.extend(_sidecar_entities())
    entities.extend(_compound_microcosm_cell_entities())
    frontend_view_entities = _frontend_view_entities()
    entities.extend(frontend_view_entities)
    _add_unique_entities(entities, _type_plane_standard_entities(type_plane_rows))
    existing_entity_ids = {
        str(entity.get("id") or "")
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("id") or "")
    }
    existing_entity_ids.update(
        _artifact_kind_entity_id(str(row.get("kind_id") or ""))
        for row in kind_rows
        if str(row.get("kind_id") or "").strip()
    )
    _add_unique_entities(
        entities,
        _type_plane_artifact_entities(type_plane_rows, existing_entity_ids=existing_entity_ids),
    )
    _add_unique_entities(entities, _type_plane_surface_entities(type_plane_rows))
    _add_unique_entities(entities, _type_plane_validator_entities(type_plane_rows))
    base_entities_for_kind_coverage = list(entities)
    entities.extend(
        _artifact_kind_entities(
            kind_rows,
            base_entities_for_kind_coverage,
            cluster_projections=kind_cluster_projections,
            type_plane_lookup=type_plane_by_id,
        )
    )

    edges = [
        _edge("edge_builder_generates_graph", "builder_system_atlas_stage1", "dom_system_atlas", "generates", [BUILDER_ID]),
        _edge("edge_builder_generates_governing_doctrine", "builder_system_atlas_stage1", "dom_governing_doctrine", "generates", [BUILDER_ID]),
        _edge("edge_system_atlas_depends_on_governing_doctrine", "dom_system_atlas", "dom_governing_doctrine", "depends_on", [str(GOVERNING_DOCTRINE_PATH)]),
        _edge("edge_system_atlas_covered_by_standard", "dom_system_atlas", "std_system_atlas", "covered_by_standard", [str(STANDARD_PATH)]),
        _edge(
            "edge_state_gravity_covered_by_lifecycle_surface_budget",
            "state_gravity",
            "std_lifecycle_surface_budget",
            "covered_by_standard",
            ["codex/standards/std_lifecycle_surface_budget.json"],
        ),
        _edge(
            "edge_runtime_hook_ladder_aliases_pm_runtime_hook_ladder",
            "runtime_hook_ladder",
            "pm_runtime_hook_ladder",
            "references",
            ["codex/doctrine/paper_modules/runtime_hook_ladder.md"],
        ),
        _edge(
            "edge_runtime_hook_ladder_covered_by_lifecycle_surface_budget",
            "runtime_hook_ladder",
            "std_lifecycle_surface_budget",
            "covered_by_standard",
            ["codex/standards/std_lifecycle_surface_budget.json"],
        ),
        _edge("edge_atlas_reads_paper_modules", "builder_system_atlas_stage1", "dom_paper_modules", "reads", ["codex/doctrine/paper_modules/_index.json"]),
        _edge("edge_atlas_reads_task_ledger", "builder_system_atlas_stage1", "dom_task_ledger", "reads", ["state/task_ledger/ledger.json"]),
        _edge("edge_atlas_reads_frontend", "builder_system_atlas_stage1", "dom_frontend_cockpit", "reads", ["state/frontend_navigation/navigation_graph.json"]),
        _edge(
            "edge_atlas_projects_state_gravity",
            "builder_system_atlas_stage1",
            "state_gravity",
            "exposes",
            ["tools/meta/factory/build_system_atlas.py", "codex/standards/std_lifecycle_surface_budget.json"],
        ),
        _edge("edge_dissemination_depends_on_atlas", "dom_dissemination_gates", "dom_system_atlas", "depends_on", ["docs/dissemination"]),
    ]
    for view_entity in frontend_view_entities:
        view_id = str(view_entity.get("id") or "").strip()
        if not view_id:
            continue
        safe_view_id = _safe_id(view_id)
        edges.extend(
            [
                _edge(
                    f"edge_frontend_domain_exposes_{safe_view_id}",
                    "dom_frontend_cockpit",
                    view_id,
                    "exposes",
                    ["state/frontend_navigation/navigation_graph.json"],
                ),
                _edge(
                    f"edge_frontend_view_classified_{safe_view_id}",
                    view_id,
                    "kind_frontend_views",
                    "classified_by",
                    ["state/frontend_navigation/navigation_graph.json", "codex/standards/std_standard_type_plane.json"],
                ),
                _edge(
                    f"edge_frontend_view_governed_{safe_view_id}",
                    view_id,
                    "frontend_navigation_plane",
                    "covered_by_standard",
                    ["codex/doctrine/paper_modules/frontend_navigation_plane.md"],
                ),
            ]
        )
    entity_ids = {str(entity.get("id") or "") for entity in entities if isinstance(entity, dict)}
    seen_edge_ids = {str(edge.get("id") or "") for edge in edges}

    def add_edge(source_id: str, target_id: str, relation: str, evidence_paths: list[str], *, prefix: str) -> None:
        if source_id not in entity_ids or target_id not in entity_ids:
            return
        edge_id = f"edge_{_safe_id(prefix)}_{_safe_id(source_id)}_{_safe_id(relation)}_{_safe_id(target_id)}"
        if edge_id in seen_edge_ids:
            return
        seen_edge_ids.add(edge_id)
        edges.append(_edge(edge_id, source_id, target_id, relation, evidence_paths))

    for path_value in (
        "codex/doctrine/paper_modules/_index.json",
        "codex/doctrine/paper_modules/_route_coverage.json",
        "codex/doctrine/paper_modules/_validation_report.json",
        str(DISSEMINATION_GATE_REPORT_PATH),
    ):
        add_edge(
            "builder_system_atlas_stage1",
            _sidecar_entity_id(path_value),
            "reads",
            [path_value],
            prefix="builder_reads_sidecar",
        )
    for path_value in (
        str(GRAPH_PATH),
        str(SUMMARY_PATH),
        str(FACTS_PATH),
        str(SNAPSHOT_PATH),
        str(FACTS_MARKDOWN_PATH),
        str(UNKNOWNS_PATH),
        str(GOVERNING_DOCTRINE_PATH),
    ):
        add_edge(
            "builder_system_atlas_stage1",
            _sidecar_entity_id(path_value),
            "generates",
            [BUILDER_ID, path_value],
            prefix="builder_generates_sidecar",
        )

    add_edge(
        "dom_paper_modules",
        _sidecar_entity_id("codex/doctrine/paper_modules/_route_coverage.json"),
        "depends_on",
        ["codex/doctrine/paper_modules/_route_coverage.json"],
        prefix="paper_modules_depends_route_coverage",
    )
    add_edge(
        "dom_paper_modules",
        "std_paper_module",
        "covered_by_standard",
        ["codex/standards/std_paper_module.json"],
        prefix="paper_modules_covered_by_standard",
    )
    for row in kind_rows:
        kind_id = str(row.get("kind_id") or "").strip()
        if not kind_id:
            continue
        artifact_kind_id = _artifact_kind_entity_id(kind_id)
        evidence = list(row.get("projection_refs") or [])[:6] or ["system/lib/kind_atlas.py"]
        add_edge(
            "dom_system_atlas",
            artifact_kind_id,
            "exposes",
            evidence,
            prefix="system_atlas_exposes_artifact_kind",
        )
        add_edge(
            "builder_system_atlas_stage1",
            artifact_kind_id,
            "reads",
            evidence,
            prefix="builder_reads_artifact_kind",
        )
        for standard_ref in row.get("governing_standard_refs") or []:
            standard_id = Path(str(standard_ref)).stem
            add_edge(
                artifact_kind_id,
                standard_id,
                "governed_by",
                [str(standard_ref)],
                prefix="artifact_kind_governed_by_standard",
            )
    for row in type_plane_rows:
        type_id = str(row.get("type_id") or "").strip()
        if not type_id:
            continue
        artifact_kind_id = _artifact_kind_entity_id(type_id)
        evidence = _type_plane_evidence(row)
        add_edge(
            "builder_system_atlas_stage1",
            artifact_kind_id,
            "reads",
            evidence,
            prefix="builder_reads_standard_type_plane",
        )
        add_edge(
            "dom_system_atlas",
            artifact_kind_id,
            "exposes",
            evidence,
            prefix="system_atlas_exposes_standard_type_plane",
        )
        add_edge(
            artifact_kind_id,
            "std_standard_type_plane",
            "covered_by_standard",
            [str(STANDARD_TYPE_PLANE_PATH)],
            prefix="type_plane_artifact_covered_by_type_plane_standard",
        )
        for standard_ref in row.get("governing_standard_refs") or []:
            standard_id = _standard_id_from_ref(str(standard_ref))
            add_edge(
                artifact_kind_id,
                standard_id,
                "governed_by",
                [str(standard_ref), str(STANDARD_TYPE_PLANE_PATH)],
                prefix="type_plane_artifact_governed_by_standard",
            )
        if str(row.get("option_surface_command") or "").strip():
            add_edge(
                artifact_kind_id,
                _type_plane_surface_entity_id(type_id),
                "exposes",
                evidence,
                prefix="type_plane_artifact_exposes_surface",
            )
        if row.get("validation_probe"):
            add_edge(
                artifact_kind_id,
                _type_plane_validator_entity_id(type_id),
                "validates",
                evidence,
                prefix="type_plane_artifact_validates_probe",
            )
        annex_text = " ".join(
            str(value or "")
            for value in (
                row.get("type_id"),
                row.get("annex_adaptation_policy"),
                row.get("atlas_projection_policy"),
            )
        ).lower()
        if "annex" in annex_text:
            add_edge(
                artifact_kind_id,
                "dom_annexes",
                "references",
                evidence,
                prefix="type_plane_artifact_references_annexes",
            )
    add_edge(
        "metabolismd",
        _paper_module_entity_id("continuous_runtime_layer"),
        "covered_by_paper_module",
        ["codex/doctrine/paper_modules/continuous_runtime_layer.md"],
        prefix="metabolismd_continuous_runtime",
    )
    add_edge(
        "metabolismd",
        _paper_module_entity_id("autonomy_always_on_daemon_contract"),
        "governed_by",
        ["codex/doctrine/paper_modules/autonomy_always_on_daemon_contract.md"],
        prefix="metabolismd_daemon_contract",
    )
    add_edge(
        "metabolismd",
        "std_metabolism_status",
        "covered_by_standard",
        ["codex/standards/std_metabolism_status.json"],
        prefix="metabolismd_status_standard",
    )

    for slug, route_row in sorted(paper_route_rows.items()):
        source_id = _paper_module_entity_id(slug)
        evidence = [
            str(route_row.get("file") or f"codex/doctrine/paper_modules/{slug}.md"),
            "codex/doctrine/paper_modules/_route_coverage.json",
        ]
        add_edge(source_id, "std_paper_module", "covered_by_standard", evidence, prefix="paper_module_standard")
        for target_slug in _route_targets(route_row, "dependency_upstream"):
            add_edge(
                source_id,
                _paper_module_entity_id(target_slug),
                "depends_on",
                evidence,
                prefix="paper_module_dependency_upstream",
            )
        for ref in _route_targets(route_row, "governing_principle"):
            add_edge(source_id, _principle_entity_id(ref), "governed_by", evidence, prefix="paper_module_principle")
        for ref in _route_targets(route_row, "governing_concept"):
            add_edge(source_id, _concept_entity_id(ref), "governed_by", evidence, prefix="paper_module_concept")
        for ref in _route_targets(route_row, "governing_mechanism"):
            add_edge(source_id, _mechanism_entity_id(ref), "governed_by", evidence, prefix="paper_module_mechanism")
        for ref in _route_targets(route_row, "primary_subdomain") + _route_targets(route_row, "secondary_subdomain"):
            add_edge(source_id, _subdomain_entity_id(ref), "classified_by", evidence, prefix="paper_module_subdomain")

    paper_slugs = sorted(paper_modules)
    for item in selected_workitems:
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        source_id = _workitem_entity_id(item_id)
        text = json.dumps(item, sort_keys=True).casefold()
        if any(token in text for token in ("system atlas", "system_atlas", "self-comprehension", "substrate atlas")):
            add_edge(source_id, "dom_system_atlas", "references", ["state/task_ledger/ledger.json"], prefix="workitem_atlas_ref")
        matched = 0
        for slug in paper_slugs:
            if slug.casefold() not in text:
                continue
            add_edge(
                source_id,
                _paper_module_entity_id(slug),
                "references",
                ["state/task_ledger/ledger.json"],
                prefix="workitem_paper_module_ref",
            )
            matched += 1
            if matched >= 16:
                break
        if item_id == "system_self_comprehension_spine_p0":
            add_edge(
                source_id,
                _paper_module_entity_id("system_self_comprehension_root"),
                "references",
                ["state/task_ledger/ledger.json"],
                prefix="workitem_root_owner_ref",
            )
            add_edge(
                source_id,
                _paper_module_entity_id("system_self_comprehension_spine"),
                "references",
                ["state/task_ledger/ledger.json"],
                prefix="workitem_spine_owner_ref",
            )

    for row in dissemination_report.get("rows") or []:
        if not isinstance(row, dict):
            continue
        artifact_id = str(row.get("artifact_id") or "")
        if not artifact_id:
            continue
        source_id = _dissemination_artifact_entity_id(artifact_id)
        add_edge(source_id, "dom_dissemination_gates", "depends_on", [str(DISSEMINATION_GATE_REPORT_PATH)], prefix="dissemination_gate_domain")
        for atlas_entity_id in row.get("atlas_entity_ids") or []:
            add_edge(
                source_id,
                str(atlas_entity_id),
                "depends_on",
                [str(row.get("source_path") or DISSEMINATION_GATE_REPORT_PATH), str(DISSEMINATION_GATE_REPORT_PATH)],
                prefix="dissemination_gate_atlas_ref",
            )

    findings: list[dict[str, Any]] = []
    findings.extend(
        _artifact_kind_projection_gap_findings(
            kind_rows,
            base_entities_for_kind_coverage,
            cluster_projections=kind_cluster_projections,
        )
    )
    for row in source_inputs:
        if not row["exists"]:
            findings.append(
                _finding(
                    f"missing_{row['source_id']}",
                    kind="missing_source_input",
                    severity="warning",
                    title=f"Missing atlas source input: {row['source_id']}",
                    summary=f"{row['path']} was not present during stage-1 atlas harvest.",
                    evidence_paths=[row["path"]],
                    related_entity_ids=["dom_system_atlas"],
                    recommended_action="Create the source surface or mark it intentionally unavailable in the next atlas builder pass.",
                )
            )

    if _dissemination_count() > 0 and not dissemination_gate["exists"]:
        findings.append(
            _finding(
                "atlas_gate_not_yet_enforced",
                kind="dissemination_gate_gap",
                severity="warning",
                title="Dissemination gates are not yet mechanically atlas-backed",
                summary="Dissemination docs exist, but this stage-1 builder does not yet enforce send-ready failure on stale or missing atlas rows.",
                evidence_paths=["docs/dissemination"],
                related_entity_ids=["dom_dissemination_gates", "dom_system_atlas"],
                recommended_action="Patch dissemination validators after the graph and option-surface slice are stable.",
            )
        )
    elif dissemination_gate["exists"] and not dissemination_gate["ok"]:
        findings.append(
            _finding(
                "atlas_gate_blocking_violations",
                kind="dissemination_gate_gap",
                severity="error",
                title="Dissemination atlas gate has blocking violations",
                summary=(
                    f"The dissemination atlas gate report found {dissemination_gate['blocking_violation_count']} "
                    "blocking violation(s)."
                ),
                evidence_paths=[str(DISSEMINATION_GATE_REPORT_PATH), str(DISSEMINATION_GATE_MARKDOWN_PATH)],
                related_entity_ids=["dom_dissemination_gates", "dom_system_atlas"],
                recommended_action="./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
            )
        )

    summary = _summary_for(entities=entities, edges=edges, findings=findings, source_inputs=source_inputs)
    summary["governing_doctrine_count"] = len(governing_doctrine)
    summary["governing_doctrine_kinds"] = dict(
        sorted(Counter(row["kind"] for row in governing_doctrine).items())
    )
    summary["paper_module_route_graph"] = {
        "route_edge_count": int(paper_route_summary.get("route_edge_count") or 0),
        "routed_module_count": int(paper_route_summary.get("routed_module_count") or 0),
        "route_target_count": int(paper_route_summary.get("route_target_count") or 0),
        "route_axis_edge_counts": paper_route_summary.get("route_axis_edge_counts") or {},
        "route_population_score": paper_route_summary.get("route_population_score"),
        "route_metadata_integrity_average": paper_route_summary.get("route_metadata_integrity_average"),
    }
    summary["integration_stage"] = "stage_2_route_graph_ingestion"
    summary["artifact_kind_projection"] = {
        "kind_atlas_row_count": len(kind_rows),
        "artifact_kind_entity_count": sum(1 for entity in entities if entity.get("kind") == "ArtifactKind"),
        "row_level_projection_gap_count": sum(
            1
            for finding in findings
            if str(finding.get("id") or "").startswith("atlas_projection_gap_")
        ),
        "unknown_row_count_gap_count": sum(
            1
            for finding in findings
            if str(finding.get("id") or "").startswith("unknown_")
            and str(finding.get("id") or "").endswith("_row_count")
        ),
    }
    summary["standard_type_plane_projection"] = {
        "type_plane_row_count": len(type_plane_rows),
        "artifact_kind_entity_count": sum(
            1
            for row in type_plane_rows
            if _artifact_kind_entity_id(str(row.get("type_id") or "")) in {
                str(entity.get("id") or "") for entity in entities if isinstance(entity, dict)
            }
        ),
        "surface_entity_count": sum(
            1
            for entity in entities
            if str(entity.get("id") or "").startswith("surface_type_plane_")
        ),
        "validator_entity_count": sum(
            1
            for entity in entities
            if str(entity.get("id") or "").startswith("validator_type_plane_")
        ),
        "source_ref": str(STANDARD_TYPE_PLANE_PATH),
        "authority_posture": "standard_rows_are_source_system_atlas_rows_are_projection",
    }
    return {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "standard_ref": str(STANDARD_PATH),
        "generated_at": generated_at,
        "generated_by": BUILDER_ID,
        "source_inputs": source_inputs,
        "summary": summary,
        "governing_doctrine": governing_doctrine,
        "entities": entities,
        "edges": edges,
        "findings": findings,
    }


def _summary_for(
    *,
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    source_inputs: list[dict[str, Any]],
) -> dict[str, Any]:
    by_kind = Counter(str(entity.get("kind") or "unknown") for entity in entities)
    by_authority = Counter(str(entity.get("authority_class") or "unknown") for entity in entities)
    by_disclosure = Counter(str(entity.get("disclosure_class") or "unknown") for entity in entities)
    findings_by_severity = Counter(str(finding.get("severity") or "unknown") for finding in findings)
    return {
        "entity_count": len(entities),
        "edge_count": len(edges),
        "finding_count": len(findings),
        "source_input_count": len(source_inputs),
        "present_source_input_count": sum(1 for row in source_inputs if row.get("exists")),
        "entity_kinds": dict(sorted(by_kind.items())),
        "authority_classes": dict(sorted(by_authority.items())),
        "disclosure_classes": dict(sorted(by_disclosure.items())),
        "findings_by_severity": dict(sorted(findings_by_severity.items())),
    }


def load_standard() -> dict[str, Any]:
    standard = _read_json(STANDARD_PATH)
    return standard if isinstance(standard, dict) else {}


def validate_graph(graph: dict[str, Any], standard: dict[str, Any] | None = None) -> list[str]:
    standard = standard or load_standard()
    errors: list[str] = []
    required_top = list((standard.get("graph_contract") or {}).get("required_top_level_fields") or [])
    entity_required = list((standard.get("graph_contract") or {}).get("entity_required_fields") or [])
    edge_required = list((standard.get("graph_contract") or {}).get("edge_required_fields") or [])
    finding_required = list((standard.get("graph_contract") or {}).get("finding_required_fields") or [])
    authority_enum = set(standard.get("authority_class_enum") or [])
    kind_enum = set(standard.get("entity_kind_enum") or [])
    maturity_enum = set(standard.get("maturity_enum") or [])
    risk_enum = set(standard.get("risk_level_enum") or [])
    disclosure_enum = set(standard.get("disclosure_class_enum") or [])
    freshness_enum = set(standard.get("freshness_status_enum") or [])
    relation_enum = set(standard.get("edge_relation_enum") or [])

    for key in required_top:
        if key not in graph:
            errors.append(f"missing top-level field: {key}")

    entities = graph.get("entities")
    if not isinstance(entities, list):
        errors.append("entities must be a list")
        entities = []
    seen_ids: set[str] = set()
    for index, entity in enumerate(entities):
        if not isinstance(entity, dict):
            errors.append(f"entity[{index}] must be an object")
            continue
        entity_id = str(entity.get("id") or "")
        if not entity_id:
            errors.append(f"entity[{index}] missing id")
        elif entity_id in seen_ids:
            errors.append(f"duplicate entity id: {entity_id}")
        seen_ids.add(entity_id)
        for key in entity_required:
            if key not in entity:
                errors.append(f"entity {entity_id or index} missing field: {key}")
        if authority_enum and entity.get("authority_class") not in authority_enum:
            errors.append(f"entity {entity_id} has invalid authority_class: {entity.get('authority_class')}")
        if kind_enum and entity.get("kind") not in kind_enum:
            errors.append(f"entity {entity_id} has invalid kind: {entity.get('kind')}")
        if maturity_enum and entity.get("maturity") not in maturity_enum:
            errors.append(f"entity {entity_id} has invalid maturity: {entity.get('maturity')}")
        if risk_enum and entity.get("risk_level") not in risk_enum:
            errors.append(f"entity {entity_id} has invalid risk_level: {entity.get('risk_level')}")
        if disclosure_enum and entity.get("disclosure_class") not in disclosure_enum:
            errors.append(f"entity {entity_id} has invalid disclosure_class: {entity.get('disclosure_class')}")
        if freshness_enum and entity.get("freshness_status") not in freshness_enum:
            errors.append(f"entity {entity_id} has invalid freshness_status: {entity.get('freshness_status')}")

    edges = graph.get("edges")
    if not isinstance(edges, list):
        errors.append("edges must be a list")
        edges = []
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge[{index}] must be an object")
            continue
        edge_id = str(edge.get("id") or index)
        for key in edge_required:
            if key not in edge:
                errors.append(f"edge {edge_id} missing field: {key}")
        if relation_enum and edge.get("relation") not in relation_enum:
            errors.append(f"edge {edge_id} has invalid relation: {edge.get('relation')}")
        for endpoint in ("source_id", "target_id"):
            value = str(edge.get(endpoint) or "")
            if value and value not in seen_ids:
                errors.append(f"edge {edge_id} {endpoint} does not resolve: {value}")

    findings = graph.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
        findings = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"finding[{index}] must be an object")
            continue
        finding_id = str(finding.get("id") or index)
        for key in finding_required:
            if key not in finding:
                errors.append(f"finding {finding_id} missing field: {key}")
        if authority_enum and finding.get("authority_class") not in authority_enum:
            errors.append(f"finding {finding_id} has invalid authority_class: {finding.get('authority_class')}")
    return errors


def _entity_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entity.get("id") or ""): entity
        for entity in graph.get("entities", [])
        if isinstance(entity, dict) and str(entity.get("id") or "")
    }


def _entity_metric(entity: dict[str, Any] | None, key: str, default: int = 0) -> int:
    metrics = entity.get("metrics") if isinstance(entity, dict) else None
    if not isinstance(metrics, dict):
        return default
    try:
        return int(metrics.get(key) or default)
    except (TypeError, ValueError):
        return default


def build_facts_at_a_glance(graph: dict[str, Any]) -> dict[str, Any]:
    """Build the compact, audience-safe facts card consumed by prompts and UIs."""
    summary = graph.get("summary") if isinstance(graph.get("summary"), dict) else {}
    entities = _entity_by_id(graph)
    paper_count = _entity_metric(entities.get("dom_paper_modules"), "paper_module_count")
    standard_count = _entity_metric(entities.get("dom_standards"), "standard_count")
    task_items = _entity_metric(entities.get("dom_task_ledger"), "work_items")
    task_views = _entity_metric(entities.get("dom_task_ledger"), "views")
    frontend_views = _entity_metric(entities.get("dom_frontend_cockpit"), "views")
    frontend_components = _entity_metric(entities.get("dom_frontend_cockpit"), "components")
    provider_count = _entity_metric(entities.get("dom_provider_lanes"), "provider_count")
    annex_patterns = _entity_metric(entities.get("dom_annexes"), "distillation_patterns")

    facts = [
        {
            "id": "projection_not_authority",
            "label": "Projection, not authority",
            "summary": "System Atlas rows are harvested control-plane projections; source files, event ledgers, generated sidecars, and owner tools remain authority.",
            "type_b_use": "Use the atlas as the compact map. Ask Type A for cited evidence when exact private state would change the answer.",
            "agent_entry_use": "Open atlas rows only after task entry or context-pack selects the relevant kind.",
            "operator_ui_use": "Use counts and warnings as orientation, then jump to the cited drilldown.",
            "source_refs": [
                "codex/standards/std_system_atlas.json",
                "state/system_atlas/system_atlas.graph.json",
            ],
        },
        {
            "id": "actor_axes",
            "label": "Type A/B axes",
            "summary": "Type A/B is substrate authority, not intelligence level. Class tier, surface, delegation role, context mode, lane, and thinking budget are independent axes.",
            "type_b_use": "Do not classify subagents as Type B just because they are delegated; do not treat provider lanes as globally low-class.",
            "agent_entry_use": "Route actor ontology claims through con_016::actor_axes and operational_work_item_spine.",
            "operator_ui_use": "Read Type B prompt output as shape guidance unless Type A has verified the substrate.",
            "source_refs": [
                "codex/doctrine/concepts/con_016_intelligence_delegation_cascade.json",
                "codex/doctrine/paper_modules/operational_work_item_spine.md",
            ],
        },
        {
            "id": "availability_ladder",
            "label": "Availability ladder",
            "summary": "Before greenfield authoring, check local option surfaces, half-built or uncommitted substrate, raw-seed/operator anchors, annex prior art, then public research.",
            "type_b_use": "Convert missing-capability claims into ASK_TYPE_A evidence requests or explicit reuse/finish/import/research/build-new branches.",
            "agent_entry_use": "Start with ./repo-python kernel.py --entry \"<task>\" --context-budget 12000 (canonical front door per std_agent_entry_surface.json::canonical_option_surface_routes.first_move_contract); --context-pack is the downstream cross-kind packet route after entry selects it; drill into option surfaces with --kind-atlas and --option-surface.",
            "operator_ui_use": "Prefer the existing route/button/atlas row when it already covers the need.",
            "source_refs": [
                "AGENTS.override.md",
                "codex/doctrine/paper_modules/navigation_hologram_theory.md",
            ],
        },
        {
            "id": "dynamic_facts_live_elsewhere",
            "label": "Dynamic facts live elsewhere",
            "summary": "Volatile current state belongs in kernel output, builder-owned regions, JSON sidecars, and runtime ledgers, not prose.",
            "type_b_use": "Treat pasted counts and old summaries as dated unless the paste includes fresh command output.",
            "agent_entry_use": "Use ./repo-python kernel.py --pulse, --entry, --phase, --context-pack, and builder --check commands.",
            "operator_ui_use": "Refresh Station or the owning builder before trusting a stale count.",
            "source_refs": [
                "AGENTS.override.md",
                "codex/doctrine/agent_bootstrap_live.json",
            ],
        },
        {
            "id": "private_state_boundary",
            "label": "Private state boundary",
            "summary": "Raw seed, Task Ledger, provider/browser outputs, feed artifacts, and ignored state are private-root evidence unless redacted or synthetic.",
            "type_b_use": "Do not infer private state beyond provided traces; request Type A evidence or keep claims at method level.",
            "agent_entry_use": "Use generated summaries and evidence paths; do not paste private bodies into public-safe artifacts.",
            "operator_ui_use": "Use disclosure class and risk level before sharing, recording, or demoing.",
            "source_refs": [
                "docs/system_atlas/generated_system_atlas_snapshot.md",
                "docs/system_atlas/substrate_inventory_register.md",
            ],
        },
        {
            "id": "work_and_learning_spines",
            "label": "Work and learning spines",
            "summary": "Durable work belongs in WorkItems/Task Ledger; prompt lessons belong in Prompt Ledger or up-propagation intake; reusable doctrine lessons propagate to the owning standard, skill, or paper module.",
            "type_b_use": "Return WorkItem contours, ASK_TYPE_A packets, or prompt-patch contours instead of loose TODOs.",
            "agent_entry_use": "Capture residuals through task-ledger/apply/up-propagation lanes rather than chat-only memory.",
            "operator_ui_use": "Use Prompt Shelf digest before editing prompts and WorkItem views before ranking work.",
            "source_refs": [
                "codex/doctrine/paper_modules/operational_work_item_spine.md",
                "state/prompt_shelf/uppropagation_digest.md",
            ],
        },
    ]

    return {
        "kind": "system_facts_at_a_glance",
        "schema_version": "system_facts_at_a_glance_v1",
        "generated_at": graph.get("generated_at"),
        "generated_by": BUILDER_ID,
        "authority_posture": "generated_control_plane_projection_not_source_authority",
        "source_refs": [
            str(STANDARD_PATH),
            str(GRAPH_PATH),
            BUILDER_ID,
        ],
        "summary": {
            "entity_count": int(summary.get("entity_count") or 0),
            "source_input_count": int(summary.get("source_input_count") or 0),
            "finding_count": int(summary.get("finding_count") or 0),
            "paper_module_count": paper_count,
            "standard_count": standard_count,
            "task_ledger_work_items": task_items,
            "task_ledger_views": task_views,
            "frontend_views": frontend_views,
            "frontend_components": frontend_components,
            "provider_lane_count": provider_count,
            "annex_distillation_patterns": annex_patterns,
        },
        "facts": facts,
        "prompt_insert": {
            "title": "System facts at-a-glance",
            "source_json": str(FACTS_PATH),
            "source_markdown": str(FACTS_MARKDOWN_PATH),
            "text": (
                "System facts at-a-glance: treat docs/system_atlas/generated_system_facts_at_a_glance.md "
                "and state/system_atlas/system_facts_at_a_glance.json as the compact projected map, not source authority. "
                "Carry these defaults unless newer evidence overrides them: Type A/B is substrate authority, not quality; "
                "missing-capability claims walk the availability ladder before greenfielding; dynamic facts live in kernel "
                "output and builder-owned sidecars; raw seed, WorkItems, provider/browser/feed state, and ignored state are "
                "private-root evidence; durable residuals route through WorkItem, Prompt Ledger, up-propagation, or the owning doctrine artifact. "
                "When exact private state changes the decision, ask Type A for ./repo-python kernel.py --context-pack \"<task>\" "
                "or ./repo-python kernel.py --option-surface system_atlas --band card --ids <entity_id>."
            ),
        },
    }


def render_facts_markdown(facts: dict[str, Any]) -> str:
    summary = facts.get("summary") if isinstance(facts.get("summary"), dict) else {}
    lines = [
        "# Generated System Facts At A Glance",
        "",
        "_Generated by `tools/meta/factory/build_system_atlas.py`. This is a compact projection for Type B prompts, agent entry, Station, and the Obsidian prompt shelf. Reopen cited sources before promoting claims._",
        "",
        "## Snapshot",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Atlas entities | {summary.get('entity_count', 0)} |",
        f"| Findings | {summary.get('finding_count', 0)} |",
        f"| Paper modules | {summary.get('paper_module_count', 0)} |",
        f"| Standards | {summary.get('standard_count', 0)} |",
        f"| WorkItems | {summary.get('task_ledger_work_items', 0)} |",
        f"| Frontend views | {summary.get('frontend_views', 0)} |",
        f"| Provider lanes | {summary.get('provider_lane_count', 0)} |",
        "",
        "## Facts",
        "",
        "| ID | Fact | Type B use |",
        "|---|---|---|",
    ]
    for fact in facts.get("facts", []):
        if not isinstance(fact, dict):
            continue
        lines.append(
            "| {id} | {summary} | {type_b_use} |".format(
                id=_md_cell(str(fact.get("id") or "")),
                summary=_md_cell(str(fact.get("summary") or "")),
                type_b_use=_md_cell(str(fact.get("type_b_use") or "")),
            )
        )
    lines.extend(
        [
            "",
            "## Prompt Insert",
            "",
            str((facts.get("prompt_insert") or {}).get("text") or ""),
            "",
            "## Drilldowns",
            "",
            "```bash",
            "./repo-python tools/meta/factory/build_system_atlas.py --check",
            "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
            "./repo-python kernel.py --option-surface system_atlas --band unknowns",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_snapshot(graph: dict[str, Any]) -> str:
    summary = graph.get("summary") if isinstance(graph.get("summary"), dict) else {}
    lines = [
        "# Generated System Atlas Snapshot",
        "",
        "_Generated by `tools/meta/factory/build_system_atlas.py`. This is a public-safe projection over private generated state; reopen cited source surfaces before promoting claims._",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Entities | {summary.get('entity_count', 0)} |",
        f"| Edges | {summary.get('edge_count', 0)} |",
        f"| Findings | {summary.get('finding_count', 0)} |",
        f"| Source input classes | {summary.get('source_input_count', 0)} |",
        f"| Governing doctrine rows | {summary.get('governing_doctrine_count', 0)} |",
        "",
        "## Entity Rows",
        "",
        "| ID | Kind | Authority | Disclosure | Freshness | Summary |",
        "|---|---|---|---|---|---|",
    ]
    for entity in graph.get("entities", []):
        if not isinstance(entity, dict):
            continue
        lines.append(
            "| {id} | {kind} | {authority} | {disclosure} | {freshness} | {summary} |".format(
                id=_md_cell(str(entity.get("id") or "")),
                kind=_md_cell(str(entity.get("kind") or "")),
                authority=_md_cell(str(entity.get("authority_class") or "")),
                disclosure=_md_cell(str(entity.get("disclosure_class") or "")),
                freshness=_md_cell(str(entity.get("freshness_status") or "")),
                summary=_md_cell(str(entity.get("summary") or "")),
            )
        )
    lines.extend(
        [
            "",
            "## Redaction Boundary",
            "",
            "This snapshot contains counts, entity summaries, authority classes, disclosure classes, and drilldown directions only.",
            "It intentionally omits private artifact bodies, provider prompt/output bodies, browser session state, finance artifact contents, private logs, and private correspondence.",
            "",
            "## Drilldowns",
            "",
            "```bash",
            "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
            "./repo-python kernel.py --option-surface system_atlas --band card --ids dom_system_atlas",
            "./repo-python tools/meta/factory/build_system_atlas.py --check",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_governing_doctrine(graph: dict[str, Any]) -> str:
    rows = [row for row in graph.get("governing_doctrine", []) if isinstance(row, dict)]
    lines = [
        "# Generated Atlas Governing Doctrine",
        "",
        "_Generated by `tools/meta/factory/build_system_atlas.py`. This is a compact alignment map; it cites drilldowns and intentionally omits doctrine bodies._",
        "",
        "## Band Contract",
        "",
        "The System Atlas is a thin, drilldown-first control plane. Cluster and flag bands orient; card bands show selected evidence and omission receipts; bands omit raw seed text, provider outputs, browser sessions, feed artifact bodies, private logs, and full source bodies.",
        "",
        "## Governing Rows",
        "",
        "| Ref | Kind | Why it governs atlas | Required atlas behavior | Drilldown |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {ref} | {kind} | {why} | {behavior} | `{drilldown}` |".format(
                ref=_md_cell(str(row.get("ref") or "")),
                kind=_md_cell(str(row.get("kind") or "")),
                why=_md_cell(str(row.get("why_it_governs_atlas") or "")),
                behavior=_md_cell(str(row.get("required_atlas_behavior") or "")),
                drilldown=str(row.get("drilldown_command") or "").replace("`", "\\`"),
            )
        )
    lines.extend(
        [
            "",
            "## Omission Receipt",
            "",
            "Full doctrine bodies, source JSON bodies, raw-seed-derived clauses, private state, provider outputs, browser sessions, and runtime artifact contents are omitted. Use the drilldown command for the selected row when stronger evidence is needed.",
            "",
        ]
    )
    return "\n".join(lines)


def render_unknowns(graph: dict[str, Any]) -> str:
    findings = [finding for finding in graph.get("findings", []) if isinstance(finding, dict)]
    lines = [
        "# Generated System Atlas Unknowns Queue",
        "",
        "_Generated from `state/system_atlas/system_atlas.graph.json`; do not hand-edit as source truth._",
        "",
    ]
    if not findings:
        lines.extend(["No generated unknown rows in the current stage-1 graph.", ""])
        return "\n".join(lines)
    lines.extend(["| ID | Severity | Kind | Summary | Recommended action |", "|---|---|---|---|---|"])
    for finding in findings:
        lines.append(
            "| {id} | {severity} | {kind} | {summary} | {action} |".format(
                id=_md_cell(str(finding.get("id") or "")),
                severity=_md_cell(str(finding.get("severity") or "")),
                kind=_md_cell(str(finding.get("kind") or "")),
                summary=_md_cell(str(finding.get("summary") or "")),
                action=_md_cell(str(finding.get("recommended_action") or "")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _md_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value).replace("|", "\\|").strip()


def redaction_errors(text: str) -> list[str]:
    errors: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"snapshot matched forbidden secret pattern: {pattern.pattern}")
    lower = "\n".join(
        line
        for line in text.lower().splitlines()
        if "omit" not in line and "redaction boundary" not in line
    )
    for marker in FORBIDDEN_SNAPSHOT_MARKERS:
        if marker in lower:
            errors.append(f"snapshot contains forbidden marker: {marker}")
    return errors


def write_outputs(graph: dict[str, Any]) -> None:
    summary = graph.get("summary") if isinstance(graph.get("summary"), dict) else {}
    facts = build_facts_at_a_glance(graph)
    snapshot = render_snapshot(graph)
    facts_markdown = render_facts_markdown(facts)
    unknowns = render_unknowns(graph)
    governing = render_governing_doctrine(graph)
    for path in (
        GRAPH_PATH,
        SUMMARY_PATH,
        FACTS_PATH,
        SNAPSHOT_PATH,
        FACTS_MARKDOWN_PATH,
        UNKNOWNS_PATH,
        GOVERNING_DOCTRINE_PATH,
    ):
        _repo(path).parent.mkdir(parents=True, exist_ok=True)
    _repo(GRAPH_PATH).write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _repo(SUMMARY_PATH).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _repo(FACTS_PATH).write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _repo(SNAPSHOT_PATH).write_text(snapshot, encoding="utf-8")
    _repo(FACTS_MARKDOWN_PATH).write_text(facts_markdown, encoding="utf-8")
    _repo(UNKNOWNS_PATH).write_text(unknowns, encoding="utf-8")
    _repo(GOVERNING_DOCTRINE_PATH).write_text(governing, encoding="utf-8")


def _source_input_key(row: dict[str, Any]) -> str:
    return f"{row.get('source_id') or ''}\0{row.get('path') or ''}"


SOURCE_OWNER_ROUTE_HINTS = {
    "axiom_candidates": "Settle the raw-seed axiom candidate owner lane before refreshing generated Atlas outputs.",
    "principles": "Settle the raw-seed principles owner lane before refreshing generated Atlas outputs.",
    "standards": "Settle the owning standard or standard-builder lane before refreshing generated Atlas outputs.",
    "kind_atlas_builder": "Settle the Kind Atlas builder lane before refreshing generated Atlas outputs.",
    "skills_registry": "Settle the skill registry owner lane before refreshing generated Atlas outputs.",
    "paper_module_index": "./repo-python tools/meta/factory/build_paper_module_index.py --check",
    "paper_module_validation": "./repo-python tools/meta/factory/build_paper_module_index.py --check",
    "paper_module_route_coverage": "./repo-python tools/meta/factory/build_paper_module_index.py --check",
    "compute_cache": "Wait for the compute worker lane to settle, then refresh generated Atlas outputs.",
    "compute_run_fingerprints": "Wait for the compute worker lane to settle, then refresh generated Atlas outputs.",
}

SOURCE_OWNER_PROJECTION_IDS = {
    "task_ledger_ledger": "task_ledger_projection",
    "task_ledger_views": "task_ledger_projection",
}


def _command_text(argv: tuple[str, ...]) -> str:
    return " ".join(str(part) for part in argv)


def _git_status_pathspec(source_path: str) -> str:
    if not source_path:
        return "."
    meta_positions = [source_path.find(ch) for ch in ("*", "?", "[") if source_path.find(ch) >= 0]
    if not meta_positions:
        return source_path
    raw_prefix = source_path[: min(meta_positions)]
    prefix = raw_prefix.rstrip("/")
    if not prefix:
        return "."
    if raw_prefix.endswith("/"):
        return prefix
    if "/" in prefix:
        return prefix.rsplit("/", 1)[0] or "."
    return prefix


def _git_status_for_source_path(source_path: str) -> dict[str, Any]:
    pathspec = _git_status_pathspec(source_path)
    return _git_status_for_pathspecs([pathspec], display_pathspec=pathspec)


def _git_status_for_pathspecs(pathspecs: list[str], *, display_pathspec: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--", *pathspecs],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "git_status": "unknown",
            "git_pathspec": pathspec,
            "git_status_error": str(exc),
        }
    if result.returncode != 0:
        return {
            "git_status": "unknown",
            "git_pathspec": pathspec,
            "git_status_error": result.stderr.strip() or f"git status exited {result.returncode}",
        }
    entries = [line for line in result.stdout.splitlines() if line.strip()]
    return {
        "git_status": "dirty" if entries else "clean",
        "git_pathspec": display_pathspec,
        "git_status_entry_count": len(entries),
        "git_status_entries": entries[:8],
        "truncated_git_status_entries": max(0, len(entries) - 8),
    }


def _git_status_for_source_row(row: dict[str, Any]) -> dict[str, Any]:
    paths = [str(path) for path in list(row.get("paths") or []) if str(path)]
    if paths:
        return _git_status_for_pathspecs(paths, display_pathspec=", ".join(paths[:8]))
    return _git_status_for_source_path(str(row.get("path") or ""))


def _source_owner_route_hint(source_id: str | None) -> str:
    projection_owner_id = SOURCE_OWNER_PROJECTION_IDS.get(source_id or "")
    if projection_owner_id:
        return _command_text(generated_projection_registry.get_projection_owner(projection_owner_id).check_command)
    return SOURCE_OWNER_ROUTE_HINTS.get(
        source_id or "",
        "Settle the source owner lane or scoped source commit before refreshing generated Atlas outputs.",
    )


def _normalize_repo_path_for_claim_match(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            raw = candidate.resolve(strict=False).relative_to(REPO_ROOT.resolve(strict=False)).as_posix()
        except ValueError:
            return ""
    normalized = PurePosixPath(raw).as_posix().strip("/")
    return "" if normalized in ("", ".") else normalized


def _repo_path_scopes_overlap(left: str, right: str) -> bool:
    left_norm = _normalize_repo_path_for_claim_match(left)
    right_norm = _normalize_repo_path_for_claim_match(right)
    if not left_norm or not right_norm:
        return False
    left_parts = PurePosixPath(left_norm).parts
    right_parts = PurePosixPath(right_norm).parts
    if left_parts == right_parts:
        return True
    if len(left_parts) < len(right_parts):
        return right_parts[: len(left_parts)] == left_parts
    return left_parts[: len(right_parts)] == right_parts


def _compact_source_path_claim(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": str(claim.get("claim_id") or ""),
        "session_id": str(claim.get("session_id") or ""),
        "actor": str(claim.get("actor") or ""),
        "phase_id": str(claim.get("phase_id") or ""),
        "scope_kind": str(claim.get("scope_kind") or ""),
        "scope_id": str(claim.get("scope_id") or ""),
        "path": str(claim.get("path") or claim.get("scope_id") or ""),
        "work_item_id": str(claim.get("work_item_id") or ""),
        "claimed_at": claim.get("claimed_at"),
        "leased_until": claim.get("leased_until"),
    }


def _active_path_claims_for_source_path(source_path: str) -> dict[str, Any]:
    pathspec = _git_status_pathspec(source_path)
    try:
        snapshot = work_ledger_runtime.load_active_claims_snapshot(REPO_ROOT, limit=200, allow_stale=True)
    except Exception as exc:
        return {
            "claim_status": "unavailable",
            "claim_pathspec": pathspec,
            "active_claim_count": 0,
            "active_claims": [],
            "truncated_active_claims": 0,
            "work_ledger_claim_error": str(exc),
            "owner_action_hint": "refresh Work Ledger active claims before deciding whether Atlas source inputs are settled.",
        }

    matches: list[dict[str, Any]] = []
    for claim in snapshot.get("active_claims") or []:
        if not isinstance(claim, dict):
            continue
        if str(claim.get("scope_kind") or "") != "path":
            continue
        claim_path = str(claim.get("path") or claim.get("scope_id") or "")
        if _repo_path_scopes_overlap(pathspec, claim_path):
            matches.append(_compact_source_path_claim(claim))

    source_freshness = snapshot.get("source_freshness")
    freshness_status = (
        source_freshness.get("status")
        if isinstance(source_freshness, dict)
        else str(snapshot.get("status") or "unknown")
    )
    return {
        "claim_status": "active_claims_found" if matches else "no_active_claims",
        "claim_pathspec": pathspec,
        "work_ledger_snapshot_status": str(snapshot.get("status") or "unknown"),
        "work_ledger_snapshot_freshness": str(freshness_status or "unknown"),
        "active_claim_count": len(matches),
        "active_claims": matches[:5],
        "truncated_active_claims": max(0, len(matches) - 5),
        "owner_action_hint": (
            "wait_for_or_join_active_owner_lane_before_refreshing_atlas"
            if matches
            else "no_active_work_ledger_claims_for_source_path"
        ),
    }


def _with_source_coupled_blocker(receipt: dict[str, Any]) -> dict[str, Any]:
    """Add the settlement classification consumers need before deciding refresh order."""
    status = str(receipt.get("status") or "unknown")
    blocking_sources = [
        row
        for row in receipt.get("blocking_changed_sources", [])
        if isinstance(row, dict)
    ]

    if status == "source_inputs_changed_since_artifact_generation":
        first = blocking_sources[0] if blocking_sources else {}
        receipt.update(
            {
                "source_coupled_blocker_status": "blocked",
                "source_coupled_blocker_count": int(
                    receipt.get("blocking_changed_source_count") or len(blocking_sources)
                ),
                "first_source_coupled_blocker": {
                    "blocker_class": "source_input_changed_since_artifact_generation",
                    "source_id": str(first.get("source_id") or ""),
                    "path": str(first.get("path") or ""),
                    "git_status": str(first.get("git_status") or "unknown"),
                    "owner_route_hint": str(first.get("owner_route_hint") or ""),
                    "owner_action_hint": str(
                        (first.get("work_ledger_claims") or {}).get("owner_action_hint") or ""
                    ),
                },
            }
        )
        return receipt

    if status in {"missing_artifact", "unreadable_artifact"}:
        receipt.update(
            {
                "source_coupled_blocker_status": "artifact_unavailable",
                "source_coupled_blocker_count": 1,
                "first_source_coupled_blocker": {
                    "blocker_class": status,
                    "path": str(GRAPH_PATH),
                    "owner_route_hint": "./repo-python tools/meta/factory/build_system_atlas.py --check",
                },
            }
        )
        return receipt

    receipt.update(
        {
            "source_coupled_blocker_status": "none",
            "source_coupled_blocker_count": 0,
            "first_source_coupled_blocker": None,
        }
    )
    return receipt


def _source_input_drift_from_rows(current_source_inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Explain stale atlas outputs that are caused by moving inputs."""
    graph_path = _repo(GRAPH_PATH)
    if not graph_path.exists():
        return _with_source_coupled_blocker({
            "status": "missing_artifact",
            "changed_source_count": 0,
            "changed_sources": [],
            "safe_to_commit_generated_outputs_without_sources": False,
            "reason": "System Atlas graph is missing, so source coupling cannot be established.",
        })
    try:
        existing_graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _with_source_coupled_blocker({
            "status": "unreadable_artifact",
            "changed_source_count": 0,
            "changed_sources": [],
            "safe_to_commit_generated_outputs_without_sources": False,
            "reason": f"System Atlas graph is not valid JSON: {exc}",
        })
    if not isinstance(existing_graph, dict):
        return _with_source_coupled_blocker({
            "status": "unreadable_artifact",
            "changed_source_count": 0,
            "changed_sources": [],
            "safe_to_commit_generated_outputs_without_sources": False,
            "reason": "System Atlas graph is not a JSON object.",
        })

    existing_rows = {
        _source_input_key(row): row
        for row in existing_graph.get("source_inputs", [])
        if isinstance(row, dict)
    }
    current_rows = {
        _source_input_key(row): row
        for row in current_source_inputs
        if isinstance(row, dict)
    }
    changed: list[dict[str, Any]] = []
    for key in sorted(set(existing_rows) | set(current_rows)):
        before = existing_rows.get(key)
        after = current_rows.get(key)
        if before == after:
            continue
        row = after or before or {}
        source_id = str(row.get("source_id") or "")
        source_path = str(row.get("path") or "")
        git_status = _git_status_for_source_row(row)
        work_ledger_claims = _active_path_claims_for_source_path(source_path)
        changed.append(
            {
                "source_id": source_id,
                "path": source_path,
                "previous_latest_mtime": before.get("latest_mtime") if before else None,
                "current_latest_mtime": after.get("latest_mtime") if after else None,
                "previous_count": before.get("count") if before else None,
                "current_count": after.get("count") if after else None,
                "owner_route_hint": _source_owner_route_hint(source_id),
                "work_ledger_claims": work_ledger_claims,
                **git_status,
            }
        )

    if changed:
        dirty_sources = [row for row in changed if row.get("git_status") == "dirty"]
        claimed_dirty_sources = [
            row
            for row in dirty_sources
            if int((row.get("work_ledger_claims") or {}).get("active_claim_count") or 0) > 0
        ]
        unknown_git_sources = [row for row in changed if row.get("git_status") == "unknown"]
        task_ledger_health_cache: dict[str, Any] = {}
        tolerated_live_sources = [
            row
            for row in changed
            if _is_tolerated_live_source_churn(
                row,
                task_ledger_health_cache=task_ledger_health_cache,
            )
        ]
        blocking_changed_sources = [
            row for row in changed if row not in tolerated_live_sources
        ]
        if not blocking_changed_sources:
            tolerated_source_ids = {str(row.get("source_id") or "") for row in tolerated_live_sources}
            only_task_ledger_churn = tolerated_source_ids <= LIVE_TASK_LEDGER_SOURCE_IDS
            status = (
                "live_task_ledger_source_churn_tolerated"
                if only_task_ledger_churn
                else "clean_live_count_only_source_churn_tolerated"
            )
            refresh_policy = (
                "stable_snapshot_check_tolerates_clean_task_ledger_churn_rebuild_before_atlas_output_commit"
                if only_task_ledger_churn
                else "stable_snapshot_check_tolerates_clean_live_count_only_churn_rebuild_before_atlas_output_commit"
            )
            reason = (
                "Only clean live Task Ledger source inputs changed after the checked artifact was generated; "
                "the saved Atlas snapshot remains valid for --check, and append-exempt landing may omit "
                "the live Task Ledger source paths from the Atlas commit."
                if only_task_ledger_churn
                else "Only clean live count-only source inputs changed after the checked artifact was generated; "
                "the saved Atlas snapshot remains valid for --check, and append-exempt landing may omit "
                "the live count-only source paths from the Atlas commit."
            )
            return _with_source_coupled_blocker({
                "status": status,
                "changed_source_count": len(changed),
                "changed_sources": changed[:12],
                "truncated_changed_sources": max(0, len(changed) - 12),
                "blocking_changed_source_count": 0,
                "blocking_changed_sources": [],
                "tolerated_live_ledger_source_count": len(tolerated_live_sources),
                "tolerated_live_ledger_sources": tolerated_live_sources[:8],
                "truncated_tolerated_live_ledger_sources": max(0, len(tolerated_live_sources) - 8),
                "dirty_changed_source_count": len(dirty_sources),
                "dirty_changed_sources": dirty_sources[:8],
                "truncated_dirty_changed_sources": max(0, len(dirty_sources) - 8),
                "claimed_dirty_source_count": len(claimed_dirty_sources),
                "claimed_dirty_sources": claimed_dirty_sources[:8],
                "truncated_claimed_dirty_sources": max(0, len(claimed_dirty_sources) - 8),
                "unknown_git_status_source_count": len(unknown_git_sources),
                "safe_to_commit_generated_outputs_without_sources": True,
                "refresh_policy": refresh_policy,
                "reason": reason,
            })
        refresh_policy = (
            "do_not_refresh_or_commit_generated_atlas_until_active_source_claims_release_or_settle_dirty_inputs"
            if claimed_dirty_sources
            else (
                "do_not_refresh_or_commit_generated_atlas_until_dirty_source_inputs_are_owned_or_settled"
                if dirty_sources
                else "rebuild_generated_atlas_with_owner_builder_then_check"
            )
        )
        return _with_source_coupled_blocker({
            "status": "source_inputs_changed_since_artifact_generation",
            "changed_source_count": len(changed),
            "changed_sources": changed[:12],
            "truncated_changed_sources": max(0, len(changed) - 12),
            "blocking_changed_source_count": len(blocking_changed_sources),
            "blocking_changed_sources": blocking_changed_sources[:12],
            "truncated_blocking_changed_sources": max(0, len(blocking_changed_sources) - 12),
            "tolerated_live_ledger_source_count": len(tolerated_live_sources),
            "tolerated_live_ledger_sources": tolerated_live_sources[:8],
            "truncated_tolerated_live_ledger_sources": max(0, len(tolerated_live_sources) - 8),
            "dirty_changed_source_count": len(dirty_sources),
            "dirty_changed_sources": dirty_sources[:8],
            "truncated_dirty_changed_sources": max(0, len(dirty_sources) - 8),
            "claimed_dirty_source_count": len(claimed_dirty_sources),
            "claimed_dirty_sources": claimed_dirty_sources[:8],
            "truncated_claimed_dirty_sources": max(0, len(claimed_dirty_sources) - 8),
            "unknown_git_status_source_count": len(unknown_git_sources),
            "safe_to_commit_generated_outputs_without_sources": False,
            "refresh_policy": refresh_policy,
            "reason": "System Atlas source inputs changed after the checked artifact was generated; rebuild after the moving source lane settles.",
        })
    return _with_source_coupled_blocker({
        "status": "source_inputs_match_checked_artifact",
        "changed_source_count": 0,
        "changed_sources": [],
        "blocking_changed_source_count": 0,
        "blocking_changed_sources": [],
        "tolerated_live_ledger_source_count": 0,
        "tolerated_live_ledger_sources": [],
        "dirty_changed_source_count": 0,
        "dirty_changed_sources": [],
        "truncated_dirty_changed_sources": 0,
        "claimed_dirty_source_count": 0,
        "claimed_dirty_sources": [],
        "truncated_claimed_dirty_sources": 0,
        "unknown_git_status_source_count": 0,
        "safe_to_commit_generated_outputs_without_sources": True,
        "refresh_policy": "no_refresh_needed",
        "reason": "System Atlas source inputs in the checked artifact match the current builder inputs.",
    })


def _is_tolerated_live_source_churn(
    row: dict[str, Any],
    *,
    task_ledger_health_cache: dict[str, Any] | None = None,
) -> bool:
    source_id = str(row.get("source_id") or "")
    if source_id not in LIVE_TASK_LEDGER_SOURCE_IDS | LIVE_RUNTIME_COUNT_ONLY_SOURCE_IDS:
        return False
    claims = row.get("work_ledger_claims") or {}
    if str(claims.get("claim_status") or "") != "no_active_claims":
        return False
    git_status = str(row.get("git_status") or "")
    if source_id in LIVE_RUNTIME_COUNT_ONLY_SOURCE_IDS:
        return git_status == "clean"
    if git_status == "clean":
        return True
    if git_status != "dirty":
        return False
    health = _task_ledger_authority_projection_health(task_ledger_health_cache)
    is_clean_append_tail = _task_ledger_authority_projection_is_clean(health)
    _annotate_task_ledger_source_health(row, health, clean_append_tail=is_clean_append_tail)
    return is_clean_append_tail


def _task_ledger_authority_projection_health(
    cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if cache is None:
        cache = {}
    if "health" not in cache:
        try:
            cache["health"] = task_ledger_events.authority_health(
                REPO_ROOT,
                projection_check=True,
            )
        except Exception as exc:  # pragma: no cover - defensive diagnostic path
            cache["health"] = {
                "ok": False,
                "status": "unavailable",
                "error": str(exc),
                "projection_check": {
                    "ok": False,
                    "status": "unavailable",
                },
            }
    health = cache.get("health")
    return health if isinstance(health, dict) else {}


def _task_ledger_authority_projection_is_clean(health: dict[str, Any]) -> bool:
    projection_check = health.get("projection_check")
    if not isinstance(projection_check, dict):
        return False
    return (
        bool(health.get("ok"))
        and str(health.get("status") or "") == "clean"
        and bool(projection_check.get("ok"))
        and str(projection_check.get("status") or "") == "clean"
    )


def _annotate_task_ledger_source_health(
    row: dict[str, Any],
    health: dict[str, Any],
    *,
    clean_append_tail: bool,
) -> None:
    projection_check = health.get("projection_check")
    projection_check = projection_check if isinstance(projection_check, dict) else {}
    event_count_comparison = projection_check.get("event_count_comparison")
    event_count_comparison = event_count_comparison if isinstance(event_count_comparison, dict) else {}
    row.update(
        {
            "task_ledger_clean_append_tail": clean_append_tail,
            "task_ledger_authority_status": str(health.get("status") or ""),
            "task_ledger_projection_status": str(projection_check.get("status") or ""),
            "task_ledger_authority_event_count": health.get("authority_event_count"),
            "task_ledger_projection_event_count": event_count_comparison.get(
                "projection_event_count"
            ),
            "task_ledger_authority_projection_delta": event_count_comparison.get("delta"),
        }
    )


def _is_tolerated_live_source_churn_status(source_coupling: dict[str, Any]) -> bool:
    return str(source_coupling.get("status") or "") in {
        "live_task_ledger_source_churn_tolerated",
        "clean_live_count_only_source_churn_tolerated",
    }


def _source_input_drift(current_graph: dict[str, Any]) -> dict[str, Any]:
    return _source_input_drift_from_rows(
        [row for row in current_graph.get("source_inputs", []) if isinstance(row, dict)]
    )


def _normalize_graph_for_check(value: Any, path: tuple[str, ...] = ()) -> Any:
    """Normalize volatile owner-read timestamps before graph freshness comparison.

    The atlas graph is source-coupled by ``source_inputs``. Some embedded owner
    rows, such as derived facts currentness, carry their own live read-model
    ``generated_at`` timestamp. Those prove the sibling owner was consulted but
    must not make ``build_system_atlas.py --check`` fail immediately after a
    successful atlas rebuild.
    """
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key == "generated_at" and "currentness" in path:
                normalized[key] = "<owner-currentness-generated-at>"
                continue
            normalized[key] = _normalize_graph_for_check(item, path + (key,))
        return normalized
    if isinstance(value, list):
        return [_normalize_graph_for_check(item, path) for item in value]
    return value


def _stale_source_input_errors(source_coupling: dict[str, Any]) -> list[str]:
    if source_coupling.get("status") == "missing_artifact":
        return [f"missing output: {GRAPH_PATH}"]
    if source_coupling.get("status") == "unreadable_artifact":
        return [str(source_coupling.get("reason") or "System Atlas graph is unreadable.")]
    if source_coupling.get("status") != "source_inputs_changed_since_artifact_generation":
        return []
    blocking_sources = source_coupling.get("blocking_changed_sources") or source_coupling.get("changed_sources", [])
    changed = ", ".join(
        str(row.get("path") or row.get("source_id") or "")
        for row in blocking_sources[:5]
    )
    dirty = ", ".join(
        str(row.get("path") or row.get("source_id") or "")
        for row in source_coupling.get("dirty_changed_sources", [])[:5]
    )
    claimed = ", ".join(
        str(row.get("path") or row.get("source_id") or "")
        for row in source_coupling.get("claimed_dirty_sources", [])[:5]
    )
    if dirty:
        active_claim_clause = (
            f"; active source claims require owner-lane settlement before Atlas refresh: {claimed}"
            if claimed
            else ""
        )
        return [
            "source inputs changed since artifact generation: "
            f"{changed}; dirty source inputs block generated-only refresh: {dirty}"
            f"{active_claim_clause}"
        ]
    return [f"source inputs changed since artifact generation: {changed}"]


def check_outputs(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_coupling = _source_input_drift(graph)
    facts = build_facts_at_a_glance(graph)
    expected = {
        GRAPH_PATH: json.dumps(graph, indent=2, sort_keys=True) + "\n",
        SUMMARY_PATH: json.dumps(graph["summary"], indent=2, sort_keys=True) + "\n",
        FACTS_PATH: json.dumps(facts, indent=2, sort_keys=True) + "\n",
        SNAPSHOT_PATH: render_snapshot(graph),
        FACTS_MARKDOWN_PATH: render_facts_markdown(facts),
        UNKNOWNS_PATH: render_unknowns(graph),
        GOVERNING_DOCTRINE_PATH: render_governing_doctrine(graph),
    }
    for rel_path, expected_text in expected.items():
        path = _repo(rel_path)
        if not path.exists():
            errors.append(f"missing output: {rel_path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if rel_path == GRAPH_PATH:
            try:
                actual_graph = json.loads(actual)
            except json.JSONDecodeError:
                errors.append(f"output is stale: {rel_path}")
                continue
            if _normalize_graph_for_check(actual_graph) != _normalize_graph_for_check(graph):
                errors.append(f"output is stale: {rel_path}")
            continue
        if actual != expected_text:
            errors.append(f"output is stale: {rel_path}")
    if errors and source_coupling.get("status") == "source_inputs_changed_since_artifact_generation":
        changed = ", ".join(
            str(row.get("path") or row.get("source_id") or "")
            for row in source_coupling.get("changed_sources", [])[:5]
        )
        errors.append(f"source inputs changed since artifact generation: {changed}")
    return errors


def _check_saved_outputs_from_graph() -> tuple[dict[str, Any], list[str]]:
    graph_path = _repo(GRAPH_PATH)
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [str(exc)]
    facts = build_facts_at_a_glance(graph)
    errors = validate_graph(graph)
    errors.extend(redaction_errors(render_snapshot(graph)))
    errors.extend(redaction_errors(render_facts_markdown(facts)))
    errors.extend(redaction_errors(render_unknowns(graph)))
    errors.extend(redaction_errors(render_governing_doctrine(graph)))
    errors.extend(check_outputs(graph))
    return graph, errors


def build_and_validate() -> tuple[dict[str, Any], list[str]]:
    graph = build_graph(REPO_ROOT)
    facts = build_facts_at_a_glance(graph)
    errors = validate_graph(graph)
    errors.extend(redaction_errors(render_snapshot(graph)))
    errors.extend(redaction_errors(render_facts_markdown(facts)))
    errors.extend(redaction_errors(render_unknowns(graph)))
    errors.extend(redaction_errors(render_governing_doctrine(graph)))
    return graph, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate generated graph and fail if outputs are missing or stale.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility no-op; --check output and normal result output are already JSON.",
    )
    args = parser.parse_args(argv)

    if args.check:
        source_coupling = _source_input_drift_from_rows(collect_source_inputs())
        errors = _stale_source_input_errors(source_coupling)
        if errors:
            payload = {
                "ok": False,
                "schema_version": "system_atlas_builder_check_v1",
                "graph_path": str(GRAPH_PATH),
                "source_coupling": source_coupling,
                "summary": {},
                "errors": errors,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 1
        if _is_tolerated_live_source_churn_status(source_coupling):
            graph, errors = _check_saved_outputs_from_graph()
            payload = {
                "ok": not errors,
                "schema_version": "system_atlas_builder_check_v1",
                "graph_path": str(GRAPH_PATH),
                "source_coupling": source_coupling,
                "summary": graph.get("summary", {}) if isinstance(graph, dict) else {},
                "errors": errors,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if not errors else 1

    graph, errors = build_and_validate()
    if args.check:
        errors.extend(check_outputs(graph))
        source_coupling = _source_input_drift(graph)
        payload = {
            "ok": not errors,
            "schema_version": "system_atlas_builder_check_v1",
            "graph_path": str(GRAPH_PATH),
            "source_coupling": source_coupling,
            "summary": graph.get("summary", {}),
            "errors": errors,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if not errors else 1

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    write_outputs(graph)
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": "system_atlas_builder_result_v1",
                "outputs": [
                    str(GRAPH_PATH),
                    str(SUMMARY_PATH),
                    str(FACTS_PATH),
                    str(SNAPSHOT_PATH),
                    str(FACTS_MARKDOWN_PATH),
                    str(UNKNOWNS_PATH),
                    str(GOVERNING_DOCTRINE_PATH),
                ],
                "summary": graph["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())