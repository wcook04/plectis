"""Canonical doctrine graph compiler and query helpers.

[PURPOSE]
- Teleology: Compile authored doctrine inputs into one machine-readable doctrine graph plus the first review/projection artifacts that consume it.
- Mechanism: Read active-family principles, doctrine concepts, doctrine mechanisms, and component seeds; normalize them into graph nodes and edges; derive additive lineage; emit drift-aware operator/query packets; and materialize graph-adjacent projections such as compiler IR and section units.
- Non-goal: Replacing authored doctrine inputs or silently mutating them. The compiler preserves raw_seed_principles.json, con_*.json, and mech_*.json as authored sources.

[INTERFACE]
- build_doctrine_bundle(repo_root) -> dict
- build_doctrine_graph(repo_root) -> dict
- build_doctrine_compiler_ir(repo_root, graph, section_units) -> dict
- build_doctrine_surface_projection(repo_root, graph, compiler_ir, section_units, operator_packet) -> dict
- build_doctrine_index_projection(repo_root, graph) -> dict
- build_doctrine_routing_projection(repo_root, graph, compiler_ir) -> dict
- build_doctrine_ir_proposal(repo_root, *, selected_shards, graph, section_units, base_ir=None, proposal_path=None) -> dict
- build_doctrine_section_units(repo_root, graph) -> dict
- build_doctrine_operator_packet(repo_root, graph, section_units, compiler_ir) -> dict
- load_doctrine_graph(repo_root, rebuild_if_missing=False) -> dict | None
- load_doctrine_approved_overlay(repo_root, active_family=None) -> dict
- load_doctrine_section_units(repo_root, rebuild_if_missing=False) -> dict | None
- write_compiled_doctrine_artifacts(repo_root, bundle=None) -> dict
- find_doctrine_node(graph, node_id) -> dict | None
- query_doctrine_graph(graph, *, query, section_units=None, limit=12, runtime_state=None) -> dict

[FLOW]
1. Resolve the active family and authored doctrine inputs.
2. Compile principles, concepts, and mechanisms into normalized nodes with explicit identity, epistemic facet, lineage, projection, and runtime metadata.
3. Derive additive lineage for principles without breaking the flat principles source.
4. Seed section-unit projections from component markdown files.
5. Emit a compiler IR that records drift findings and projection updates even when there are no raw-seed mutation proposals yet.
6. Feed query and operator packets from the same compiled substrate.

[DEPENDENCIES]
- system.lib.phase_lifecycle.resolve_preferred_phase_activation: active-family routing.
- system.lib.raw_seed_registry.raw_seed_principles_path_for_family: canonical family principles path resolution.

[CONSTRAINTS]
- Read-only over authored doctrine inputs. The compiler may write generated projection artifacts only when the explicit materialization helper is called.
- Query packets must degrade gracefully when the generated graph file is missing by rebuilding from authored sources.
- Concept narrowing is additive: the compiler may mark projection_candidate concepts, but it must not delete or relocate authored concept files.
- When-needed: Open when a caller needs the canonical doctrine graph, doctrine query packet, or first operator-facing doctrine projection instead of re-deriving doctrine relations ad hoc.
- Escalates-to: tools/meta/factory/generate_system_map.py; system/server/world_model.py; codex/standards/principles/std_doctrine_graph.json
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.phase_lifecycle import resolve_preferred_phase_activation
from system.lib.raw_seed_registry import raw_seed_principles_path_for_family

DOCTRINE_GRAPH_REL = "codex/doctrine/doctrine_graph.json"
DOCTRINE_COMPILER_IR_REL = "codex/doctrine/doctrine_compiler_ir.json"
DOCTRINE_SECTION_UNITS_REL = "codex/doctrine/doctrine_section_units.json"
DOCTRINE_APPROVED_OVERLAY_REL = "codex/doctrine/doctrine_approved_overlay.json"

_DEFAULT_FIDELITIES = [
    "briefing",
    "node_card",
    "traversal_packet",
    "operator_card",
]
_PROJECTION_PATHS = {
    "doctrine_surface": "codex/doctrine/doctrine_surface.json",
    "doctrine_index": "codex/doctrine/doctrine_index.json",
    "doctrine_routing": "codex/doctrine/doctrine_routing.json",
    "documentation_theory_index": "codex/doctrine/documentation_theory_index.json",
    "system_map": "codex/doctrine/system_map.json",
}
_RESOURCE_DIR_REL = "codex/resources"
_REFERENCE_DIR_REL = "codex/doctrine/references"
_OPERATIONS_DIR_REL = "codex/doctrine/operations"
_FLOWS_DIR_REL = "codex/doctrine/flows"
_COMPONENTS_DIR_REL = "codex/doctrine/components"
_SKILL_REGISTRY_REL = "codex/doctrine/skills/skill_registry.json"
_ORCHESTRATION_STATE_REL = "tools/meta/control/orchestration_state.json"
_DOCS_FOCUS_REL = "tools/meta/control/documentation_route_focus.json"
_SYSTEM_VIEW_REL = "codex/doctrine/system_map.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _file_mtime_iso(path: Path) -> str | None:
    try:
        if not path.exists():
            return None
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _dedupe_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _normalized_text(value: Any) -> str:
    token = re.sub(r"[^a-z0-9]+", " ", _string(value).casefold())
    return re.sub(r"\s+", " ", token).strip()


def _slugify(value: Any) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", _string(value).casefold())
    token = re.sub(r"-{2,}", "-", token).strip("-")
    return token or "untitled"


def _tokenize(value: Any) -> list[str]:
    return [part for part in _normalized_text(value).split(" ") if len(part) >= 3]


def _parse_iso(value: Any) -> datetime | None:
    token = _string(value)
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _freshness(updated_at_iso: Any) -> dict[str, Any]:
    dt = _parse_iso(updated_at_iso)
    if dt is None:
        return {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": _string(updated_at_iso) or None}
    delta = (datetime.now(timezone.utc) - dt).total_seconds()
    hours = delta / 3600.0
    if hours < 4:
        tone = "fresh"
    elif hours < 24:
        tone = "stale"
    else:
        tone = "expired"
    if delta < 60:
        label = "just now"
    elif delta < 3600:
        label = f"{int(delta // 60)}m ago"
    elif delta < 86_400:
        label = f"{int(delta // 3600)}h ago"
    else:
        label = f"{int(delta // 86_400)}d ago"
    return {"tone": tone, "age_seconds": int(delta), "label": label, "iso": dt.isoformat()}


def _resolve_active_family_dir(repo_root: Path) -> str | None:
    activation = resolve_preferred_phase_activation(repo_root, eligibility="routing") or {}
    family_dir = _string(activation.get("family_dir"))
    if family_dir:
        return family_dir
    root = repo_root / "obsidian" / "okay lets do this"
    if not root.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        match = re.match(r"^(\d+)(?:\s|$)", child.name)
        if not match:
            continue
        candidates.append((int(match.group(1)), child))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return _rel(repo_root, candidates[0][1])


def _load_active_family_meta(repo_root: Path) -> dict[str, Any]:
    family_dir = _resolve_active_family_dir(repo_root)
    if not family_dir:
        return {
            "family_id": None,
            "family_number": None,
            "family_title": None,
            "family_dir": None,
            "principles_source_path": None,
        }
    family_path = repo_root / family_dir / "phase_family.json"
    family_payload = _safe_read_json(family_path)
    family = dict(family_payload) if isinstance(family_payload, Mapping) else {}
    return {
        "family_id": family.get("family_id") or family.get("id"),
        "family_number": family.get("family_number") or family.get("family_id"),
        "family_title": family.get("family_title") or family.get("title") or Path(family_dir).name,
        "family_dir": family_dir,
        "principles_source_path": raw_seed_principles_path_for_family(family_dir) or None,
    }


def _principle_parent_ids(principle: Mapping[str, Any]) -> tuple[list[str], str]:
    declared = [_string(item) for item in (principle.get("parent_ids") or []) if _string(item).startswith("pri_")]
    if declared:
        return _dedupe_strings(declared), "declared"
    parents: list[str] = []
    for edge in _list_of_dicts(principle.get("edges")):
        relation = _string(edge.get("relation"))
        target = _string(edge.get("target"))
        if target == "pri_014":
            # pri_014 is the curation discipline anchor, not the hierarchy parent
            # for every principle that happens to cite it.
            continue
        if relation in {"requires", "refines", "implements"} and target.startswith("pri_"):
            parents.append(target)
    return _dedupe_strings(parents), "compiled_from_edges"


def _derive_principle_lineage(principles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    adjacency: dict[str, list[str]] = {}
    source_mode: dict[str, str] = {}
    ids = {_string(item.get("id")) for item in principles if _string(item.get("id"))}
    for principle in principles:
        pid = _string(principle.get("id"))
        parent_ids, mode = _principle_parent_ids(principle)
        adjacency[pid] = [parent for parent in parent_ids if parent in ids]
        source_mode[pid] = mode

    cache: dict[str, tuple[str, int]] = {}

    def resolve(pid: str, stack: set[str]) -> tuple[str, int]:
        if pid in cache:
            return cache[pid]
        if pid in stack:
            cache[pid] = (pid, 0)
            return cache[pid]
        parents = adjacency.get(pid) or []
        if not parents:
            cache[pid] = (pid, 0)
            return cache[pid]
        resolved = [resolve(parent, stack | {pid}) for parent in parents]
        root_id = sorted({root for root, _ in resolved})[0]
        tier = min(level for _, level in resolved) + 1
        cache[pid] = (root_id, tier)
        return cache[pid]

    lineage: dict[str, dict[str, Any]] = {}
    for principle in principles:
        pid = _string(principle.get("id"))
        root_id, tier = resolve(pid, set())
        parent_ids = adjacency.get(pid) or []
        role = _string(principle.get("role")) or ("foundational" if not parent_ids else "derived")
        lineage[pid] = {
            "parent_ids": parent_ids,
            "root_id": _string(principle.get("root_id")) or root_id,
            "tier": principle.get("tier") if isinstance(principle.get("tier"), int) else tier,
            "role": role,
            "source": source_mode.get(pid) or "compiled_from_edges",
        }
    return lineage


def _principle_authority_mode(principle: Mapping[str, Any]) -> str:
    status = _string(principle.get("authority_status")) or "active_authority"
    if status == "compatibility_only":
        return "compatibility_only"
    return "peer_authority"


def _section_unit_fidelities(kind: str) -> list[str]:
    values = list(_DEFAULT_FIDELITIES)
    if kind in {"principle", "module_seed"}:
        values.append("module_section")
    if kind == "mechanism":
        values.append("code_grounded_view")
    if kind == "skill":
        values.append("procedure_card")
    if kind == "resource":
        values.append("resource_card")
    return values


def _projection_briefing(statement: Any) -> str:
    text = _string(statement)
    return text[:220]


def _title_from_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", _string(value)).strip(" .")
    if not text:
        return "Untitled Candidate"
    words = text.split(" ")
    return " ".join(words[:8]).strip() or "Untitled Candidate"


def _load_legacy_projection(repo_root: Path, projection_id: str) -> dict[str, Any]:
    rel_path = _PROJECTION_PATHS.get(projection_id)
    if not rel_path:
        return {}
    payload = _safe_read_json(repo_root / rel_path)
    return dict(payload) if isinstance(payload, Mapping) else {}


def _empty_doctrine_approved_overlay(active_family: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "kind": "doctrine_approved_overlay",
        "schema_version": "doctrine_approved_overlay_v0",
        "generated_at": _utc_now(),
        "compiler_target": DOCTRINE_GRAPH_REL,
        "active_family": dict(active_family or {}),
        "sources": [],
        "decisions": {
            "nodes": [],
            "edges": [],
            "merges": [],
            "splits": [],
        },
        "overlay": {
            "nodes": [],
            "edges": [],
            "merge_directives": [],
            "split_directives": [],
        },
    }


def load_doctrine_approved_overlay(
    repo_root: Path,
    active_family: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _safe_read_json(repo_root / DOCTRINE_APPROVED_OVERLAY_REL)
    if isinstance(payload, Mapping):
        overlay = dict(payload)
        if not isinstance(overlay.get("active_family"), Mapping):
            overlay["active_family"] = dict(active_family or {})
        return overlay
    return _empty_doctrine_approved_overlay(active_family)


def _stable_candidate_edge_id(source: Any, target: Any, relation: Any) -> str:
    return f"edge_{_slugify(f'{_string(source)} {relation} {_string(target)}')}"


def _stable_merge_candidate_id(survivor_id: Any, absorbed_ids: list[str]) -> str:
    token = f"{_string(survivor_id)} {' '.join(sorted(_dedupe_strings(absorbed_ids)))}"
    return f"merge_{_slugify(token)}"


def _stable_split_candidate_id(source_id: Any, proposed_ids: list[str]) -> str:
    token = f"{_string(source_id)} {' '.join(sorted(_dedupe_strings(proposed_ids)))}"
    return f"split_{_slugify(token)}"


def _stable_tombstone_candidate_id(legacy_kind: Any, legacy_id: Any, replacement_ids: list[str]) -> str:
    token = f"{_string(legacy_kind)} {_string(legacy_id)} {' '.join(sorted(_dedupe_strings(replacement_ids)))}"
    return f"tombstone_{_slugify(token)}"


def annotate_doctrine_ir_candidate_ids(proposal: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(proposal)
    out["candidate_nodes"] = [
        dict(item)
        for item in (proposal.get("candidate_nodes") or [])
        if isinstance(item, Mapping)
    ]
    out["candidate_edges"] = [
        {
            **dict(item),
            "id": _string(item.get("id")) or _stable_candidate_edge_id(item.get("source"), item.get("target"), item.get("relation")),
        }
        for item in (proposal.get("candidate_edges") or [])
        if isinstance(item, Mapping)
    ]
    out["merge_candidates"] = [
        {
            **dict(item),
            "id": _string(item.get("id")) or _stable_merge_candidate_id(
                item.get("survivor_id"),
                [_string(value) for value in (item.get("absorbed_ids") or []) if _string(value)],
            ),
        }
        for item in (proposal.get("merge_candidates") or [])
        if isinstance(item, Mapping)
    ]
    out["split_candidates"] = [
        {
            **dict(item),
            "id": _string(item.get("id")) or _stable_split_candidate_id(
                item.get("source_id"),
                [_string(value) for value in (item.get("proposed_ids") or []) if _string(value)],
            ),
        }
        for item in (proposal.get("split_candidates") or [])
        if isinstance(item, Mapping)
    ]
    out["tombstone_candidates"] = [
        {
            **dict(item),
            "id": _string(item.get("id")) or _stable_tombstone_candidate_id(
                item.get("legacy_kind"),
                item.get("legacy_id"),
                [_string(value) for value in (item.get("replacement_ids") or []) if _string(value)],
            ),
        }
        for item in (proposal.get("tombstone_candidates") or [])
        if isinstance(item, Mapping)
    ]
    return out


def _load_principles_payload(repo_root: Path, family_meta: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    rel = _string(family_meta.get("principles_source_path"))
    if not rel:
        return {}, [], None
    payload = _safe_read_json(repo_root / rel)
    if not isinstance(payload, Mapping):
        return {}, [], rel
    principles = _list_of_dicts(payload.get("principles"))
    return dict(payload), principles, rel


def _load_concepts(repo_root: Path) -> list[dict[str, Any]]:
    root = repo_root / "codex" / "doctrine" / "concepts"
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("con_*.json")):
        payload = _safe_read_json(path)
        if isinstance(payload, Mapping):
            item = dict(payload)
            item["__path__"] = _rel(repo_root, path)
            out.append(item)
    return out


def _load_mechanisms(repo_root: Path) -> list[dict[str, Any]]:
    root = repo_root / "codex" / "doctrine" / "mechanisms"
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("mech_*.json")):
        payload = _safe_read_json(path)
        if isinstance(payload, Mapping):
            item = dict(payload)
            item["__path__"] = _rel(repo_root, path)
            out.append(item)
    return out


def _load_skill_entries(repo_root: Path) -> list[dict[str, Any]]:
    payload = _safe_read_json(repo_root / _SKILL_REGISTRY_REL)
    if not isinstance(payload, Mapping):
        return []
    out: list[dict[str, Any]] = []
    for family in payload.get("families") or []:
        if not isinstance(family, Mapping):
            continue
        family_id = _string(family.get("family_id"))
        family_title = _string(family.get("title"))
        for skill in family.get("skills") or []:
            if not isinstance(skill, Mapping):
                continue
            item = dict(skill)
            item["__family_id__"] = family_id
            item["__family_title__"] = family_title
            item["__path__"] = _string(skill.get("file")) or None
            out.append(item)
    return out


def _load_markdown_cards(repo_root: Path, rel_dir: str, *, source_surface: str) -> list[dict[str, Any]]:
    root = repo_root / rel_dir
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta = _parse_markdown_frontmatter(text)
        item = dict(meta)
        item["__path__"] = _rel(repo_root, path)
        item["__text__"] = text
        item["__body__"] = _markdown_body(text)
        item["__summary__"] = _string(meta.get("summary")) or _markdown_summary(text)
        item["__source_surface__"] = source_surface
        out.append(item)
    return out


def _load_resource_cards(repo_root: Path) -> list[dict[str, Any]]:
    cards = _load_markdown_cards(repo_root, _RESOURCE_DIR_REL, source_surface="resource_card")
    cards.extend(_load_markdown_cards(repo_root, _REFERENCE_DIR_REL, source_surface="legacy_reference"))
    return cards


def _load_component_seeds(repo_root: Path) -> list[dict[str, Any]]:
    items = _load_markdown_cards(repo_root, _COMPONENTS_DIR_REL, source_surface="component_seed")
    out: list[dict[str, Any]] = []
    for item in items:
        path = repo_root / _string(item.get("__path__"))
        text = _string(item.get("__text__"))
        title = _component_title(path, item, text)
        out.append(
            {
                **item,
                "id": _string(item.get("id")) or f"module_seed_{path.stem}",
                "title": title,
                "summary": _string(item.get("summary")) or _markdown_summary(text),
                "focus_paths": [_string(value) for value in (item.get("focus_paths") or []) if _string(value)],
                "doc_links": [_string(value) for value in (item.get("doc_links") or []) if _string(value)],
            }
        )
    return out


def _load_legacy_tombstone_surfaces(repo_root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for rel_dir, legacy_kind in (
        (_OPERATIONS_DIR_REL, "operation"),
        (_FLOWS_DIR_REL, "flow"),
        (_REFERENCE_DIR_REL, "reference"),
    ):
        for item in _load_markdown_cards(repo_root, rel_dir, source_surface=legacy_kind):
            items.append(
                {
                    "legacy_kind": legacy_kind,
                    "id": _string(item.get("id")) or Path(_string(item.get("__path__"))).stem,
                    "title": _string(item.get("title")) or Path(_string(item.get("__path__"))).stem.replace("_", " ").replace("-", " ").title(),
                    "summary": _string(item.get("__summary__")),
                    "path": _string(item.get("__path__")),
                    "focus_paths": [_string(value) for value in (item.get("focus_paths") or []) if _string(value)],
                }
            )
    return items


def _normalize_local_edges(source_id: str, raw_edges: Any) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for edge in _list_of_dicts(raw_edges):
        target = _string(edge.get("target") or edge.get("id"))
        relation = _string(edge.get("relation"))
        if not target or not relation:
            continue
        edges.append(
            {
                "source": source_id,
                "target": target,
                "relation": relation,
                "gloss": _string(edge.get("gloss")),
            }
        )
    return edges


def _concept_authority_mode(
    concept: Mapping[str, Any],
    principle_by_id: Mapping[str, Mapping[str, Any]],
) -> str:
    principle_targets = [
        _string(edge.get("target"))
        for edge in _list_of_dicts(concept.get("principle_edges"))
        if _string(edge.get("target")).startswith("pri_")
    ]
    if not principle_targets:
        return "peer_authority"
    statement = _normalized_text(concept.get("statement"))
    for target in principle_targets:
        principle = principle_by_id.get(target)
        if principle and statement and statement == _normalized_text(principle.get("statement")):
            return "projection_candidate"
    if len(principle_targets) == 1 and not _list_of_dicts(concept.get("mechanism_edges")):
        return "projection_candidate"
    return "peer_authority"


def _principle_node(
    principle: Mapping[str, Any],
    *,
    lineage: Mapping[str, Any],
    source_path: str | None,
    source_mtime: str | None,
) -> dict[str, Any]:
    pid = _string(principle.get("id"))
    return {
        "id": pid,
        "kind": "principle",
        "identity": {
            "id": pid,
            "slug": _string(principle.get("slug")),
            "title": _string(principle.get("title")),
        },
        "statement": _string(principle.get("statement")),
        "scope": _string(principle.get("scope")) or None,
        "status": _string(principle.get("status")) or None,
        "provenance": _string(principle.get("provenance")) or None,
        "epistemic_facet": "commitment",
        "authority_mode": _principle_authority_mode(principle),
        "tags": principle.get("tags") if isinstance(principle.get("tags"), list) else [],
        "lineage": dict(lineage),
        "projection": {
            "briefing": _projection_briefing(principle.get("statement")),
            "default_fidelity": "node_card",
            "available_fidelities": _section_unit_fidelities("principle"),
            "section_unit_ids": [],
        },
        "runtime": {
            "source_kind": "raw_seed_principles",
            "source_path": source_path,
            "source_mtime": source_mtime,
            "drift_sensitivity": "low",
            "active_family_authority": True,
        },
        "content": {
            "authored_kind": _string(principle.get("kind")) or None,
            "note": _string(principle.get("note")),
            "evidence": _list_of_dicts(principle.get("evidence")),
            "tests": _list_of_dicts(principle.get("tests")),
            "failure_modes": principle.get("failure_modes") if isinstance(principle.get("failure_modes"), list) else [],
            "decision_examples": principle.get("decision_examples") if isinstance(principle.get("decision_examples"), list) else [],
            "inheritance": dict(principle.get("inheritance") or {}) if isinstance(principle.get("inheritance"), Mapping) else {},
            "authority_status": _string(principle.get("authority_status")) or "active_authority",
            "demotion_target": dict(principle.get("demotion_target") or {}) if isinstance(principle.get("demotion_target"), Mapping) else {},
        },
        "reference_groups": _list_of_dicts(principle.get("reference_groups")),
        "edges": _normalize_local_edges(pid, principle.get("edges")),
    }


def _concept_node(
    concept: Mapping[str, Any],
    *,
    principle_by_id: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    cid = _string(concept.get("id"))
    edges = _normalize_local_edges(cid, concept.get("principle_edges"))
    edges.extend(_normalize_local_edges(cid, concept.get("mechanism_edges")))
    source_path = _string(concept.get("__path__")) or None
    return {
        "id": cid,
        "kind": "concept",
        "identity": {
            "id": cid,
            "slug": _string(concept.get("slug")),
            "title": _string(concept.get("title")),
        },
        "statement": _string(concept.get("statement")),
        "scope": _string(concept.get("scope")) or None,
        "status": _string(concept.get("status")) or None,
        "provenance": _string(concept.get("provenance")) or None,
        "epistemic_facet": "theory",
        "authority_mode": _concept_authority_mode(concept, principle_by_id),
        "tags": concept.get("tags") if isinstance(concept.get("tags"), list) else [],
        "lineage": {
            "parent_ids": [
                _string(edge.get("target"))
                for edge in _list_of_dicts(concept.get("principle_edges"))
                if _string(edge.get("target"))
            ],
            "root_id": cid,
            "tier": 1,
            "role": "theory",
            "source": "compiled_from_edges",
        },
        "projection": {
            "briefing": _projection_briefing(concept.get("statement")),
            "default_fidelity": "node_card",
            "available_fidelities": _section_unit_fidelities("concept"),
            "section_unit_ids": [],
        },
        "runtime": {
            "source_kind": "concept",
            "source_path": source_path,
            "source_mtime": _file_mtime_iso(repo_root / source_path) if source_path else None,
            "drift_sensitivity": "low",
            "active_family_authority": False,
        },
        "content": {
            "note": _string(concept.get("note")),
            "evidence": _list_of_dicts(concept.get("evidence")),
            "tests": _list_of_dicts(concept.get("tests")),
            "failure_modes": concept.get("failure_modes") if isinstance(concept.get("failure_modes"), list) else [],
            "decision_examples": concept.get("decision_examples") if isinstance(concept.get("decision_examples"), list) else [],
        },
        "reference_groups": _list_of_dicts(concept.get("reference_groups")),
        "edges": edges,
    }


def _mechanism_node(mechanism: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    mid = _string(mechanism.get("id"))
    edges = _normalize_local_edges(mid, mechanism.get("concept_edges"))
    edges.extend(
        _normalize_local_edges(
            mid,
            [
                {"target": target, "relation": "upstream", "gloss": ""}
                for target in (mechanism.get("upstream") or [])
            ],
        )
    )
    edges.extend(
        _normalize_local_edges(
            mid,
            [
                {"target": target, "relation": "downstream", "gloss": ""}
                for target in (mechanism.get("downstream") or [])
            ],
        )
    )
    source_path = _string(mechanism.get("__path__")) or None
    return {
        "id": mid,
        "kind": "mechanism",
        "identity": {
            "id": mid,
            "slug": _string(mechanism.get("slug")),
            "title": _string(mechanism.get("title")),
        },
        "statement": _string(mechanism.get("statement") or mechanism.get("purpose") or mechanism.get("description")),
        "scope": _string(mechanism.get("scope")) or None,
        "status": _string(mechanism.get("status")) or None,
        "provenance": _string(mechanism.get("provenance")) or None,
        "epistemic_facet": "grounding",
        "authority_mode": "peer_authority",
        "tags": mechanism.get("tags") if isinstance(mechanism.get("tags"), list) else [],
        "lineage": {
            "parent_ids": [
                _string(edge.get("target"))
                for edge in _list_of_dicts(mechanism.get("concept_edges"))
                if _string(edge.get("target"))
            ],
            "root_id": mid,
            "tier": 2,
            "role": "implementation",
            "source": "compiled_from_edges",
        },
        "projection": {
            "briefing": _projection_briefing(mechanism.get("statement") or mechanism.get("purpose")),
            "default_fidelity": "code_grounded_view",
            "available_fidelities": _section_unit_fidelities("mechanism"),
            "section_unit_ids": [],
        },
        "runtime": {
            "source_kind": "mechanism",
            "source_path": source_path,
            "source_mtime": _file_mtime_iso(repo_root / source_path) if source_path else None,
            "drift_sensitivity": _string(mechanism.get("drift_sensitivity")) or "medium",
            "active_family_authority": False,
        },
        "content": {
            "note": _string(mechanism.get("note")),
            "evidence": _list_of_dicts(mechanism.get("evidence")),
            "tests": _list_of_dicts(mechanism.get("tests")),
            "failure_modes": mechanism.get("failure_modes") if isinstance(mechanism.get("failure_modes"), list) else [],
            "decision_examples": mechanism.get("decision_examples") if isinstance(mechanism.get("decision_examples"), list) else [],
            "code_loci": _list_of_dicts(mechanism.get("code_loci")),
        },
        "reference_groups": _list_of_dicts(mechanism.get("reference_groups")),
        "edges": edges,
    }


def _skill_node(skill: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    sid = _string(skill.get("id") or skill.get("name"))
    doctrine_edges = skill.get("doctrine_edges") if isinstance(skill.get("doctrine_edges"), Mapping) else {}
    agent_surface = skill.get("agent_surface") if isinstance(skill.get("agent_surface"), Mapping) else {}
    use_when = agent_surface.get("use_when")
    use_when_tokens = [use_when] if isinstance(use_when, str) else list(use_when or [])
    edges: list[dict[str, Any]] = []
    lineage_parents: list[str] = []
    for target in doctrine_edges.get("principles") or []:
        token = _string(target)
        if not token:
            continue
        lineage_parents.append(token)
        edges.append(
            {
                "source": sid,
                "target": token,
                "relation": "guided_by",
                "gloss": "Skill registry doctrine_edges.principles links this procedure to governing commitments.",
            }
        )
    for target in doctrine_edges.get("concepts") or []:
        token = _string(target)
        if token:
            edges.append(
                {
                    "source": sid,
                    "target": token,
                    "relation": "informed_by",
                    "gloss": "Skill registry doctrine_edges.concepts links this procedure to governing theory.",
                }
            )
    for target in doctrine_edges.get("mechanisms") or []:
        token = _string(target)
        if token:
            edges.append(
                {
                    "source": sid,
                    "target": token,
                    "relation": "uses",
                    "gloss": "Skill registry doctrine_edges.mechanisms links this procedure to implementing runtime surfaces.",
                }
            )
    source_path = _string(skill.get("__path__")) or None
    return {
        "id": sid,
        "kind": "skill",
        "identity": {
            "id": sid,
            "slug": _slugify(skill.get("title") or skill.get("name") or sid),
            "title": _string(skill.get("title") or skill.get("name") or sid),
        },
        "statement": _string(skill.get("description") or skill.get("summary") or skill.get("title")),
        "scope": "repository-wide",
        "status": _string(skill.get("status")) or "active",
        "provenance": "declared",
        "epistemic_facet": "procedure",
        "authority_mode": "peer_authority",
        "tags": _dedupe_strings(
            [_string(skill.get("__family_id__"))]
            + [_string(item) for item in (skill.get("triggers") or []) if _string(item)]
            + [_string(item) for item in use_when_tokens if _string(item)]
        ),
        "lineage": {
            "parent_ids": _dedupe_strings(lineage_parents),
            "root_id": sid,
            "tier": 4,
            "role": "procedure",
            "source": "skill_registry",
        },
        "projection": {
            "briefing": _projection_briefing(skill.get("description") or skill.get("summary") or skill.get("title")),
            "default_fidelity": "procedure_card",
            "available_fidelities": _section_unit_fidelities("skill"),
            "section_unit_ids": [],
        },
        "runtime": {
            "source_kind": "skill_registry",
            "source_path": source_path,
            "source_mtime": _file_mtime_iso(repo_root / source_path) if source_path else _file_mtime_iso(repo_root / _SKILL_REGISTRY_REL),
            "drift_sensitivity": "medium",
            "active_family_authority": False,
        },
        "content": {
            "note": _string(skill.get("description")),
            "summary": _string(skill.get("summary")),
            "triggers": list(skill.get("triggers") or []),
            "governing_principles": list(skill.get("governing_principles") or []),
            "focus_paths": list(skill.get("focus_paths") or []),
            "entry": _string(agent_surface.get("entry")),
            "composes_with": list(skill.get("composes_with") or []),
        },
        "reference_groups": [],
        "edges": edges,
    }


def _resource_node(resource: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    source_path = _string(resource.get("__path__")) or None
    resource_id = _string(resource.get("id"))
    source_surface = _string(resource.get("__source_surface__"))
    if not resource_id:
        stem = Path(source_path or "resource").stem
        prefix = "res_ref_" if source_surface == "legacy_reference" else "res_"
        resource_id = f"{prefix}{_slugify(stem).replace('-', '_')}"
    title = _string(resource.get("title")) or Path(source_path or resource_id).stem.replace("_", " ").replace("-", " ").title()
    summary = _string(resource.get("__summary__"))
    tags = _dedupe_strings(
        [_string(resource.get("domain")), _string(resource.get("group")), _string(resource.get("resource_type"))]
        + [_string(item) for item in (resource.get("tags") or []) if _string(item)]
        + [_string(item) for item in (resource.get("applicable_when") or []) if _string(item)]
    )
    edges = _normalize_local_edges(
        resource_id,
        [
            {"target": target, "relation": "extends", "gloss": "Resource extends another imported knowledge card."}
            for target in (resource.get("extends") or [])
        ],
    )
    return {
        "id": resource_id,
        "kind": "resource",
        "identity": {
            "id": resource_id,
            "slug": _slugify(resource.get("slug") or title),
            "title": title,
        },
        "statement": summary or _markdown_summary(_string(resource.get("__text__"))),
        "scope": "repository-wide",
        "status": "active",
        "provenance": "imported",
        "epistemic_facet": "imported_knowledge",
        "authority_mode": "imported_context",
        "tags": tags,
        "lineage": {
            "parent_ids": [],
            "root_id": resource_id,
            "tier": 5,
            "role": "imported_knowledge",
            "source": source_surface or "resource_card",
        },
        "projection": {
            "briefing": _projection_briefing(summary),
            "default_fidelity": "resource_card",
            "available_fidelities": _section_unit_fidelities("resource"),
            "section_unit_ids": [],
        },
        "runtime": {
            "source_kind": source_surface or "resource_card",
            "source_path": source_path,
            "source_mtime": _file_mtime_iso(repo_root / source_path) if source_path else None,
            "drift_sensitivity": "low",
            "active_family_authority": False,
        },
        "content": {
            "note": _string(resource.get("__body__"))[:4000],
            "summary": summary,
            "domain": _string(resource.get("domain")),
            "group": _string(resource.get("group")),
            "resource_type": _string(resource.get("resource_type") or resource.get("kind")),
            "applicable_when": list(resource.get("applicable_when") or []),
            "sources": list(resource.get("sources") or ([resource.get("source")] if _string(resource.get("source")) else [])),
        },
        "reference_groups": [],
        "edges": edges,
    }


def _module_seed_node(
    seed: Mapping[str, Any],
    *,
    repo_root: Path,
    doctrine_refs: list[str],
    raw_seed_refs: list[str],
) -> dict[str, Any]:
    sid = _string(seed.get("id"))
    source_path = _string(seed.get("__path__")) or None
    focus_paths = [_string(value) for value in (seed.get("focus_paths") or []) if _string(value)]
    doc_links = [_string(value) for value in (seed.get("doc_links") or []) if _string(value)]
    return {
        "id": sid,
        "kind": "module_seed",
        "identity": {
            "id": sid,
            "slug": _slugify(seed.get("title") or sid),
            "title": _string(seed.get("title") or sid),
        },
        "statement": _string(seed.get("summary")),
        "scope": "repository-wide",
        "status": "active",
        "provenance": "derived",
        "epistemic_facet": "module_seed",
        "authority_mode": "projection_seed",
        "tags": _dedupe_strings([Path(source_path or sid).stem, "module", "component"]),
        "lineage": {
            "parent_ids": [],
            "root_id": sid,
            "tier": 4,
            "role": "module_seed",
            "source": "component_seed",
        },
        "projection": {
            "briefing": _projection_briefing(seed.get("summary")),
            "default_fidelity": "module_section",
            "available_fidelities": _section_unit_fidelities("module_seed"),
            "section_unit_ids": [sid],
        },
        "runtime": {
            "source_kind": "component_seed",
            "source_path": source_path,
            "source_mtime": _file_mtime_iso(repo_root / source_path) if source_path else None,
            "drift_sensitivity": "medium",
            "active_family_authority": False,
        },
        "content": {
            "note": _string(seed.get("__body__"))[:4000],
            "summary": _string(seed.get("summary")),
            "focus_paths": focus_paths,
            "doc_links": doc_links,
            "substrate_anchors": focus_paths or ([source_path] if source_path else []),
            "doctrine_refs": list(doctrine_refs),
            "raw_seed_refs": list(raw_seed_refs),
        },
        "reference_groups": [],
        "edges": [
            {
                "source": sid,
                "target": target,
                "relation": "covers",
                "gloss": "Module seed covers this doctrine node in compiled paper/operator projections.",
            }
            for target in doctrine_refs
        ],
    }


def _frontmatter_block(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    return match.group(1) if match else ""


def _parse_markdown_frontmatter(text: str) -> dict[str, Any]:
    block = _frontmatter_block(text)
    if not block:
        return {}
    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        list_match = re.match(r"^\s*-\s+(.*)$", line)
        if list_match and current_list:
            data.setdefault(current_list, []).append(list_match.group(1).strip().strip('"'))
            continue
        current_list = None
        key_match = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not key_match:
            continue
        key = key_match.group(1).strip()
        value = key_match.group(2).strip()
        if value == "":
            current_list = key
            data.setdefault(key, [])
        else:
            data[key] = value.strip('"')
    return data


def _markdown_body(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    match = re.match(r"^---\n.*?\n---\n(.*)$", text, flags=re.DOTALL)
    return match.group(1) if match else text


def _markdown_summary(text: str) -> str:
    body = _markdown_body(text)
    paragraphs = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("#")]
    return paragraphs[0] if paragraphs else ""


def _component_title(path: Path, metadata: Mapping[str, Any], text: str) -> str:
    title = _string(metadata.get("title"))
    if title:
        return title
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def _match_section_unit_refs(
    unit_title: str,
    summary: str,
    focus_paths: list[str],
    nodes: list[dict[str, Any]],
) -> list[str]:
    haystack = " ".join([unit_title, summary, " ".join(focus_paths)])
    query_tokens = set(_tokenize(haystack))
    scored: list[tuple[int, str]] = []
    for node in nodes:
        node_tokens = set(
            _tokenize(node.get("statement"))
            + _tokenize((node.get("identity") or {}).get("title"))
            + _tokenize((node.get("identity") or {}).get("slug"))
            + _tokenize(" ".join(node.get("tags") or []))
        )
        overlap = len(query_tokens & node_tokens)
        if overlap == 0:
            continue
        scored.append((overlap, _string(node.get("id"))))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [node_id for _, node_id in scored[:6]]


def build_doctrine_section_units(repo_root: Path, graph: Mapping[str, Any]) -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    nodes = [dict(item) for item in (graph.get("nodes") or []) if isinstance(item, Mapping)]
    module_seed_nodes = [node for node in nodes if _string(node.get("kind")) == "module_seed"]
    for node in module_seed_nodes:
        content = node.get("content") if isinstance(node.get("content"), Mapping) else {}
        runtime = node.get("runtime") if isinstance(node.get("runtime"), Mapping) else {}
        units.append(
            {
                "id": _string(node.get("id")),
                "title": _string(((node.get("identity") or {}) if isinstance(node.get("identity"), Mapping) else {}).get("title")),
                "source_kind": "module_seed",
                "source_path": _string(runtime.get("source_path")),
                "summary": _string(content.get("summary") or node.get("statement")),
                "bounded_scope": {
                    "focus_paths": list(content.get("focus_paths") or []),
                    "doc_links": list(content.get("doc_links") or []),
                },
                "substrate_anchors": list(content.get("substrate_anchors") or []),
                "doctrine_refs": list(content.get("doctrine_refs") or []),
                "raw_seed_refs": list(content.get("raw_seed_refs") or []),
                "fidelity": "module_stub",
                "drift_status": {
                    "source_updated_at": runtime.get("source_mtime"),
                    "compiler_generated_at": graph.get("generated_at"),
                    "status": "seeded",
                },
            }
        )
    return {
        "kind": "doctrine_section_units",
        "schema_version": "doctrine_section_units_v0",
        "generated_at": graph.get("generated_at") or _utc_now(),
        "units": units,
    }


def _filtered_matches(
    title: str,
    summary: str,
    focus_paths: list[str],
    nodes: list[dict[str, Any]],
    *,
    preferred_kinds: set[str],
) -> list[str]:
    refs = _match_section_unit_refs(title, summary, focus_paths, nodes)
    filtered = [
        ref
        for ref in refs
        if _string(next((node.get("kind") for node in nodes if _string(node.get("id")) == ref), "")) in preferred_kinds
    ]
    return filtered or refs[:1]


def _build_compatibility_tombstones(
    nodes: list[dict[str, Any]],
    legacy_surfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tombstones: list[dict[str, Any]] = []
    kind_preferences = {
        "operation": {"skill"},
        "flow": {"mechanism", "module_seed"},
        "reference": {"resource"},
    }
    for item in legacy_surfaces:
        if not isinstance(item, Mapping):
            continue
        legacy_kind = _string(item.get("legacy_kind"))
        matches = _filtered_matches(
            _string(item.get("title")),
            _string(item.get("summary")),
            [_string(value) for value in (item.get("focus_paths") or []) if _string(value)],
            nodes,
            preferred_kinds=kind_preferences.get(legacy_kind, set()),
        )
        if not matches:
            continue
        tombstones.append(
            {
                "id": f"tombstone_{legacy_kind}_{_slugify(item.get('id') or item.get('path'))}",
                "legacy_kind": legacy_kind,
                "legacy_id": _string(item.get("id")),
                "legacy_path": _string(item.get("path")),
                "status": "tombstoned",
                "replacement_ids": matches,
                "summary": _string(item.get("summary")) or _string(item.get("title")),
            }
        )
    return tombstones


def _overlay_node_defaults(kind: str) -> tuple[str, str, str]:
    normalized_kind = kind if kind in {"principle", "concept", "mechanism"} else "concept"
    if normalized_kind == "principle":
        return normalized_kind, "commitment", "peer_authority"
    if normalized_kind == "mechanism":
        return normalized_kind, "grounding", "peer_authority"
    return normalized_kind, "theory", "peer_authority"


def _normalize_overlay_node(
    node: Mapping[str, Any],
    *,
    overlay_generated_at: str | None,
) -> dict[str, Any]:
    out = dict(node)
    node_id = _string(out.get("id"))
    requested_kind = _string(out.get("kind"))
    normalized_kind, default_facet, default_authority = _overlay_node_defaults(requested_kind)
    identity = dict(out.get("identity")) if isinstance(out.get("identity"), Mapping) else {}
    runtime = dict(out.get("runtime")) if isinstance(out.get("runtime"), Mapping) else {}
    lineage = dict(out.get("lineage")) if isinstance(out.get("lineage"), Mapping) else {}
    projection = dict(out.get("projection")) if isinstance(out.get("projection"), Mapping) else {}
    content = dict(out.get("content")) if isinstance(out.get("content"), Mapping) else {}

    identity.setdefault("id", node_id)
    identity.setdefault("slug", _slugify(identity.get("title") or node_id))
    identity.setdefault("title", _title_from_text(out.get("statement") or identity.get("slug") or node_id))

    runtime.setdefault("source_kind", "approved_ir")
    runtime.setdefault("source_path", DOCTRINE_APPROVED_OVERLAY_REL)
    runtime.setdefault("source_mtime", overlay_generated_at)
    runtime.setdefault("drift_sensitivity", "medium")
    runtime.setdefault("active_family_authority", False)

    lineage.setdefault("parent_ids", [])
    lineage.setdefault("root_id", node_id)
    lineage.setdefault("tier", 0 if normalized_kind == "principle" else 1)
    lineage.setdefault("role", "foundational" if normalized_kind == "principle" else ("implementation" if normalized_kind == "mechanism" else "theory"))
    lineage.setdefault("source", "approved_ir")

    projection.setdefault("briefing", _projection_briefing(out.get("statement")))
    projection.setdefault("default_fidelity", "code_grounded_view" if normalized_kind == "mechanism" else "node_card")
    projection.setdefault("available_fidelities", _section_unit_fidelities(normalized_kind))
    projection.setdefault("section_unit_ids", [])

    content.setdefault("note", "")
    content.setdefault("evidence", [])
    content.setdefault("tests", [])
    content.setdefault("failure_modes", [])
    content.setdefault("decision_examples", [])
    if normalized_kind == "mechanism":
        content.setdefault("code_loci", [])

    out["kind"] = normalized_kind
    out["identity"] = identity
    out["statement"] = _string(out.get("statement"))
    out["scope"] = _string(out.get("scope")) or None
    out["status"] = _string(out.get("status")) or "draft"
    out["provenance"] = _string(out.get("provenance")) or "derived"
    out["epistemic_facet"] = _string(out.get("epistemic_facet")) or default_facet
    out["authority_mode"] = _string(out.get("authority_mode")) or default_authority
    out["tags"] = list(out.get("tags") or [])
    out["lineage"] = lineage
    out["projection"] = projection
    out["runtime"] = runtime
    out["content"] = content
    out["reference_groups"] = _list_of_dicts(out.get("reference_groups"))
    out["edges"] = _normalize_local_edges(node_id, out.get("edges"))
    return out


def _overlay_summary(overlay: Mapping[str, Any]) -> dict[str, Any]:
    decisions = overlay.get("decisions") if isinstance(overlay.get("decisions"), Mapping) else {}
    overlay_payload = overlay.get("overlay") if isinstance(overlay.get("overlay"), Mapping) else {}
    return {
        "path": DOCTRINE_APPROVED_OVERLAY_REL,
        "generated_at": overlay.get("generated_at"),
        "freshness": _freshness(overlay.get("generated_at")),
        "sources": len(overlay.get("sources") or []),
        "accepted_nodes": len(overlay_payload.get("nodes") or []),
        "accepted_edges": len(overlay_payload.get("edges") or []),
        "accepted_merges": len(overlay_payload.get("merge_directives") or []),
        "accepted_splits": len(overlay_payload.get("split_directives") or []),
        "accepted_tombstones": len(overlay_payload.get("tombstones") or []),
        "decision_counts": {
            "nodes": len(decisions.get("nodes") or []),
            "edges": len(decisions.get("edges") or []),
            "merges": len(decisions.get("merges") or []),
            "splits": len(decisions.get("splits") or []),
            "tombstones": len(decisions.get("tombstones") or []),
        },
    }


def build_doctrine_graph(repo_root: Path) -> dict[str, Any]:
    family_meta = _load_active_family_meta(repo_root)
    principles_payload, principles_raw, principles_source = _load_principles_payload(repo_root, family_meta)
    concepts_raw = _load_concepts(repo_root)
    mechanisms_raw = _load_mechanisms(repo_root)
    skills_raw = _load_skill_entries(repo_root)
    resources_raw = _load_resource_cards(repo_root)
    module_seeds_raw = _load_component_seeds(repo_root)
    legacy_tombstone_surfaces = _load_legacy_tombstone_surfaces(repo_root)
    approved_overlay = load_doctrine_approved_overlay(repo_root, family_meta)
    principle_lineage = _derive_principle_lineage(principles_raw)
    principle_by_id = {
        _string(item.get("id")): item
        for item in principles_raw
        if _string(item.get("id"))
    }
    principle_source_mtime = _file_mtime_iso(repo_root / principles_source) if principles_source else None

    nodes: list[dict[str, Any]] = []
    for principle in principles_raw:
        pid = _string(principle.get("id"))
        nodes.append(
            _principle_node(
                principle,
                lineage=principle_lineage.get(pid) or {
                    "parent_ids": [],
                    "root_id": pid,
                    "tier": 0,
                    "role": "foundational",
                    "source": "compiled_from_edges",
                },
                source_path=principles_source,
                source_mtime=principle_source_mtime,
            )
        )
    for concept in concepts_raw:
        nodes.append(_concept_node(concept, principle_by_id=principle_by_id, repo_root=repo_root))
    for mechanism in mechanisms_raw:
        nodes.append(_mechanism_node(mechanism, repo_root=repo_root))
    for skill in skills_raw:
        nodes.append(_skill_node(skill, repo_root=repo_root))
    for resource in resources_raw:
        nodes.append(_resource_node(resource, repo_root=repo_root))
    for seed in module_seeds_raw:
        doctrine_refs = _match_section_unit_refs(
            _string(seed.get("title")),
            _string(seed.get("summary")),
            [_string(value) for value in (seed.get("focus_paths") or []) if _string(value)],
            nodes,
        )
        raw_seed_refs: list[str] = []
        for node in nodes:
            if _string(node.get("id")) not in doctrine_refs:
                continue
            for evidence in _list_of_dicts((node.get("content") or {}).get("evidence")):
                ref = _string(evidence.get("ref"))
                if ref.startswith(("par_", "sec_")):
                    raw_seed_refs.append(ref)
        nodes.append(
            _module_seed_node(
                seed,
                repo_root=repo_root,
                doctrine_refs=doctrine_refs,
                raw_seed_refs=_dedupe_strings(raw_seed_refs)[:12],
            )
        )
    overlay_nodes = [
        _normalize_overlay_node(item, overlay_generated_at=_string(approved_overlay.get("generated_at")) or _file_mtime_iso(repo_root / DOCTRINE_APPROVED_OVERLAY_REL))
        for item in (approved_overlay.get("overlay") or {}).get("nodes", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    ]
    nodes.extend(overlay_nodes)

    compatibility_tombstones = _build_compatibility_tombstones(nodes, legacy_tombstone_surfaces)
    compatibility_tombstones.extend(
        [
            dict(item)
            for item in ((approved_overlay.get("overlay") or {}) if isinstance(approved_overlay.get("overlay"), Mapping) else {}).get("tombstones", [])
            if isinstance(item, Mapping)
        ]
    )

    section_units = build_doctrine_section_units(repo_root, {"generated_at": _utc_now(), "nodes": nodes})
    section_index: dict[str, list[str]] = defaultdict(list)
    for unit in section_units.get("units") or []:
        if not isinstance(unit, Mapping):
            continue
        unit_id = _string(unit.get("id"))
        for ref in unit.get("doctrine_refs") or []:
            ref_id = _string(ref)
            if unit_id and ref_id:
                section_index[ref_id].append(unit_id)

    for node in nodes:
        node["projection"]["section_unit_ids"] = sorted(section_index.get(_string(node.get("id"))) or [])

    edges: list[dict[str, Any]] = []
    for node in nodes:
        for edge in _list_of_dicts(node.get("edges")):
            edges.append(dict(edge))
    for edge in (approved_overlay.get("overlay") or {}).get("edges", []):
        if not isinstance(edge, Mapping):
            continue
        source = _string(edge.get("source"))
        target = _string(edge.get("target"))
        relation = _string(edge.get("relation"))
        if not source or not target or not relation:
            continue
        edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "gloss": _string(edge.get("gloss")),
            }
        )
    for tombstone in compatibility_tombstones:
        if not isinstance(tombstone, Mapping):
            continue
        target_handle = f"{_string(tombstone.get('legacy_kind'))}:{_string(tombstone.get('legacy_id')) or Path(_string(tombstone.get('legacy_path'))).stem}"
        for replacement_id in tombstone.get("replacement_ids") or []:
            if not _string(replacement_id):
                continue
            edges.append(
                {
                    "source": _string(replacement_id),
                    "target": target_handle,
                    "relation": "tombstones",
                    "gloss": "Canonical node replaces a retired compatibility surface during migration.",
                }
            )

    top_tags = Counter()
    by_kind: dict[str, list[str]] = defaultdict(list)
    by_facet: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        node_id = _string(node.get("id"))
        kind = _string(node.get("kind"))
        facet = _string(node.get("epistemic_facet"))
        if node_id:
            by_kind[kind].append(node_id)
            by_facet[facet].append(node_id)
        for tag in node.get("tags") or []:
            token = _string(tag)
            if token:
                top_tags[token] += 1

    freshest_inputs: list[datetime] = []
    for rel in [principles_source] + [
        _string(item.get("__path__"))
        for item in concepts_raw + mechanisms_raw + skills_raw + resources_raw + module_seeds_raw
        if _string(item.get("__path__"))
    ]:
        if not rel:
            continue
        dt = _parse_iso(_file_mtime_iso(repo_root / rel))
        if dt is not None:
            freshest_inputs.append(dt)

    generated_at = _utc_now()
    graph = {
        "kind": "doctrine_graph",
        "schema_version": "doctrine_graph_v0",
        "generated_at": generated_at,
        "generator": "system.lib.doctrine_graph.build_doctrine_graph",
        "active_family": family_meta,
        "compiler": {
            "mode": "compiled_from_authored_sources",
            "preserves_current_consumers": True,
            "source_counts": {
                "principles": len(principles_raw),
                "concepts": len(concepts_raw),
                "mechanisms": len(mechanisms_raw),
                "skills": len(skills_raw),
                "resources": len(resources_raw),
                "module_seeds": len(module_seeds_raw),
                "approved_overlay_nodes": len(overlay_nodes),
                "approved_overlay_edges": len((approved_overlay.get("overlay") or {}).get("edges") or []),
            },
            "freshest_input_at": max(freshest_inputs).isoformat() if freshest_inputs else None,
            "compatibility": [
                "raw_seed_principles.json remains the family-local flat authority for current readers",
                "concept and mechanism JSON files remain authored in place",
                "skill_registry.json remains the canonical doctrine-edge contract for skills",
                "codex/resources remains the canonical imported-knowledge container during migration",
                "components compile forward as module seeds while legacy component markdown stays on disk",
                "flows, operations, and doctrine references remain tombstoned compatibility surfaces for one migration cycle",
                "compiled lineage is additive and does not rewrite authored doctrine",
                "reviewed overlay doctrine remains additive and does not mutate authored doctrine",
            ],
            "warnings": [],
        },
        "nodes": nodes,
        "edges": edges,
        "compatibility_tombstones": compatibility_tombstones,
        "review_overlay": _overlay_summary(approved_overlay),
        "indexes": {
            "counts_by_kind": {kind: len(ids) for kind, ids in by_kind.items()},
            "counts_by_facet": {facet: len(ids) for facet, ids in by_facet.items()},
            "roots": sorted(
                [
                    _string(node.get("id"))
                    for node in nodes
                    if _string(node.get("kind")) == "principle"
                    and isinstance(node.get("lineage"), Mapping)
                    and int((node.get("lineage") or {}).get("tier") or 0) == 0
                ]
            ),
            "by_kind": {kind: sorted(ids) for kind, ids in by_kind.items()},
            "by_epistemic_facet": {facet: sorted(ids) for facet, ids in by_facet.items()},
            "top_tags": [
                {"tag": tag, "count": count}
                for tag, count in top_tags.most_common(20)
            ],
        },
    }
    # Rebuild section units with the final graph timestamp now that the node list is stable.
    section_units = build_doctrine_section_units(repo_root, graph)
    section_index = defaultdict(list)
    for unit in section_units.get("units") or []:
        if not isinstance(unit, Mapping):
            continue
        unit_id = _string(unit.get("id"))
        for ref in unit.get("doctrine_refs") or []:
            ref_id = _string(ref)
            if unit_id and ref_id:
                section_index[ref_id].append(unit_id)
    for node in graph["nodes"]:
        node["projection"]["section_unit_ids"] = sorted(section_index.get(_string(node.get("id"))) or [])
    return graph


def build_doctrine_compiler_ir(
    repo_root: Path,
    graph: Mapping[str, Any],
    section_units: Mapping[str, Any],
    *,
    planned_projection_ids: set[str] | None = None,
) -> dict[str, Any]:
    freshest_input = _parse_iso((graph.get("compiler") or {}).get("freshest_input_at"))
    planned = set(planned_projection_ids or set())
    drift_findings: list[dict[str, Any]] = []
    tombstone_candidates: list[dict[str, Any]] = []
    projection_updates: list[dict[str, Any]] = [
        {
            "projection_id": "doctrine_graph",
            "path": DOCTRINE_GRAPH_REL,
            "status": "generated",
            "reason": "Canonical compiled doctrine graph rebuilt from authored doctrine inputs.",
        },
        {
            "projection_id": "doctrine_section_units",
            "path": DOCTRINE_SECTION_UNITS_REL,
            "status": "generated",
            "reason": "Section-unit projection regenerated from component seeds and graph linkage.",
        },
    ]
    for projection_id, rel_path in _PROJECTION_PATHS.items():
        if projection_id in planned:
            projection_updates.append(
                {
                    "projection_id": projection_id,
                    "path": rel_path,
                    "status": "generated",
                    "reason": "Projection regenerated from the canonical doctrine graph in this compiler pass.",
                }
            )
            continue
        mtime = _parse_iso(_file_mtime_iso(repo_root / rel_path))
        if freshest_input is not None and (mtime is None or mtime < freshest_input):
            drift_findings.append(
                {
                    "id": f"drift_{projection_id}",
                    "kind": "projection_stale",
                    "severity": "high" if projection_id in {"doctrine_surface", "doctrine_index", "doctrine_routing"} else "medium",
                    "target": rel_path,
                    "summary": f"{projection_id} is older than the freshest doctrine input used for graph compilation.",
                    "details": f"freshest_input_at={graph.get('compiler', {}).get('freshest_input_at')}, projection_mtime={_file_mtime_iso(repo_root / rel_path)}",
                }
            )
            projection_updates.append(
                {
                    "projection_id": projection_id,
                    "path": rel_path,
                    "status": "stale",
                    "reason": "Projection predates current doctrine compiler inputs.",
                }
            )
    for node in graph.get("nodes") or []:
        if not isinstance(node, Mapping):
            continue
        if _string(node.get("kind")) == "concept" and _string(node.get("authority_mode")) == "projection_candidate":
            drift_findings.append(
                {
                    "id": f"classification_{_string(node.get('id'))}",
                    "kind": "classification_gap",
                    "severity": "medium",
                    "target": _string(node.get("id")),
                    "summary": "Concept looks like a projection candidate rather than a strong theory node.",
                    "details": _string(node.get("statement"))[:220],
                }
            )
            parents = [_string(item) for item in ((node.get("lineage") or {}).get("parent_ids") or []) if _string(item)]
            tombstone_candidates.append(
                {
                    "legacy_kind": "concept_projection",
                    "legacy_id": _string(node.get("id")),
                    "legacy_path": _string(((node.get("runtime") or {}) if isinstance(node.get("runtime"), Mapping) else {}).get("source_path")),
                    "replacement_ids": parents[:1],
                    "reason": "Projection-candidate concept should resolve as a compatibility alias rather than active peer doctrine authority.",
                }
            )
    for unit in section_units.get("units") or []:
        if not isinstance(unit, Mapping):
            continue
        if not unit.get("doctrine_refs"):
            drift_findings.append(
                {
                    "id": f"section_unit_{_string(unit.get('id'))}_ungrounded",
                    "kind": "authority_gap",
                    "severity": "medium",
                    "target": _string(unit.get("source_path") or unit.get("id")),
                    "summary": "Section unit has no doctrine refs yet.",
                    "details": "Component seed exists, but no bounded doctrine subgraph linkage was compiled.",
                }
            )
    for tombstone in graph.get("compatibility_tombstones") or []:
        if not isinstance(tombstone, Mapping):
            continue
        tombstone_candidates.append(
            {
                "legacy_kind": _string(tombstone.get("legacy_kind")),
                "legacy_id": _string(tombstone.get("legacy_id")),
                "legacy_path": _string(tombstone.get("legacy_path")),
                "replacement_ids": list(tombstone.get("replacement_ids") or []),
                "reason": "Legacy compatibility surface should remain resolvable while authority moves to the canonical graph.",
            }
        )
    return {
        "kind": "doctrine_compiler_ir",
        "schema_version": "doctrine_compiler_ir_v0",
        "generated_at": graph.get("generated_at") or _utc_now(),
        "compiler_target": DOCTRINE_GRAPH_REL,
        "mode": "proposal_queue" if tombstone_candidates else "projection_only",
        "active_family": graph.get("active_family") or {},
        "candidate_nodes": [],
        "candidate_edges": [],
        "merge_candidates": [],
        "split_candidates": [],
        "tombstone_candidates": tombstone_candidates,
        "projection_updates": projection_updates,
        "drift_findings": drift_findings,
        "compile_warnings": [],
        "unresolved_refs": [],
    }


def _edge_summary(graph: Mapping[str, Any]) -> dict[str, Any]:
    nodes = [item for item in (graph.get("nodes") or []) if isinstance(item, Mapping)]
    kind_by_id = {_string(node.get("id")): _string(node.get("kind")) for node in nodes if _string(node.get("id"))}
    principle_to_concept: dict[str, list[str]] = defaultdict(list)
    concept_to_mechanism: dict[str, list[str]] = defaultdict(list)
    mechanism_dependency_graph: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"upstream": [], "downstream": []})

    for edge in (graph.get("edges") or []):
        if not isinstance(edge, Mapping):
            continue
        source = _string(edge.get("source"))
        target = _string(edge.get("target"))
        relation = _string(edge.get("relation"))
        source_kind = kind_by_id.get(source)
        target_kind = kind_by_id.get(target)
        if source_kind == "principle" and target_kind == "concept":
            principle_to_concept[source].append(target)
        if source_kind == "concept" and target_kind == "principle":
            principle_to_concept[target].append(source)
        if source_kind == "concept" and target_kind == "mechanism":
            concept_to_mechanism[source].append(target)
        if source_kind == "mechanism" and target_kind == "concept":
            concept_to_mechanism[target].append(source)
        if source_kind == "mechanism" and target_kind == "mechanism" and relation in {"upstream", "downstream"}:
            mechanism_dependency_graph[source][relation].append(target)

    return {
        "principle_to_concept": {key: sorted(_dedupe_strings(value)) for key, value in principle_to_concept.items()},
        "concept_to_mechanism": {key: sorted(_dedupe_strings(value)) for key, value in concept_to_mechanism.items()},
        "mechanism_dependency_graph": {
            key: {
                "upstream": sorted(_dedupe_strings(value.get("upstream") or [])),
                "downstream": sorted(_dedupe_strings(value.get("downstream") or [])),
            }
            for key, value in mechanism_dependency_graph.items()
        },
    }


def _code_to_doctrine(graph: Mapping[str, Any], section_units: Mapping[str, Any]) -> dict[str, Any]:
    mappings: dict[str, list[str]] = defaultdict(list)
    for node in graph.get("nodes") or []:
        if not isinstance(node, Mapping):
            continue
        node_id = _string(node.get("id"))
        content = node.get("content") if isinstance(node.get("content"), Mapping) else {}
        for locus in content.get("code_loci") or []:
            if not isinstance(locus, Mapping):
                continue
            path = _string(locus.get("path"))
            if path and node_id:
                mappings[path].append(node_id)
    for unit in section_units.get("units") or []:
        if not isinstance(unit, Mapping):
            continue
        unit_id = _string(unit.get("id"))
        refs = [_string(ref) for ref in (unit.get("doctrine_refs") or []) if _string(ref)]
        for anchor in unit.get("substrate_anchors") or []:
            path = _string(anchor)
            if path:
                mappings[path].extend(refs or ([unit_id] if unit_id else []))
    return {
        "note": "Repo file or anchor path to governing doctrine node ids, generated from mechanism code grounding and section-unit substrate anchors.",
        "mappings": {path: sorted(_dedupe_strings(node_ids)) for path, node_ids in sorted(mappings.items())},
    }


def build_doctrine_surface_projection(
    repo_root: Path,
    graph: Mapping[str, Any],
    compiler_ir: Mapping[str, Any],
    section_units: Mapping[str, Any],
    operator_packet: Mapping[str, Any],
) -> dict[str, Any]:
    legacy = _load_legacy_projection(repo_root, "doctrine_surface")
    legacy_keys = [
        "problems_to_solutions",
        "staircase",
        "theme_clusters",
        "navigation_flows",
        "raw_seed_assimilation",
        "self_audit",
    ]
    nodes = [item for item in (graph.get("nodes") or []) if isinstance(item, Mapping)]
    by_kind = {
        "principle": [node for node in nodes if _string(node.get("kind")) == "principle"],
        "concept": [node for node in nodes if _string(node.get("kind")) == "concept"],
        "mechanism": [node for node in nodes if _string(node.get("kind")) == "mechanism"],
        "skill": [node for node in nodes if _string(node.get("kind")) == "skill"],
        "resource": [node for node in nodes if _string(node.get("kind")) == "resource"],
        "module_seed": [node for node in nodes if _string(node.get("kind")) == "module_seed"],
    }
    principle_cards = sorted(
        [_node_card(node) for node in by_kind["principle"]],
        key=lambda item: (
            1 if item.get("authority_mode") == "compatibility_only" else 0,
            int(((item.get("lineage") or {}).get("tier") or 99)),
            _string(item.get("title")) or _string(item.get("id")),
        ),
    )
    concept_cards = sorted(
        [_node_card(node) for node in by_kind["concept"]],
        key=lambda item: _string(item.get("title")) or _string(item.get("id")),
    )
    mechanism_cards = sorted(
        [_node_card(node) for node in by_kind["mechanism"]],
        key=lambda item: _string(item.get("title")) or _string(item.get("id")),
    )

    compressed_briefing = {
        "note": "Graph-backed doctrine briefing. Principles are ordered by lineage tier; concepts and mechanisms remain full-fidelity doctrine peers.",
        "principles": {item["id"]: item.get("projection", {}).get("briefing") for item in principle_cards[:24]},
        "concepts": {item["id"]: item.get("projection", {}).get("briefing") for item in concept_cards[:32]},
        "mechanisms": {item["id"]: item.get("projection", {}).get("briefing") for item in mechanism_cards[:32]},
        "skills": {
            _string(node.get("id")): _string((node.get("projection") or {}).get("briefing"))
            for node in by_kind["skill"][:24]
        },
        "resources": {
            _string(node.get("id")): _string((node.get("projection") or {}).get("briefing"))
            for node in by_kind["resource"][:24]
        },
    }

    surface = {
        "kind": "doctrine_surface",
        "schema_version": "doctrine_surface_v1",
        "generated_at": graph.get("generated_at") or _utc_now(),
        "compiler_target": DOCTRINE_GRAPH_REL,
        "compiler_ir_path": DOCTRINE_COMPILER_IR_REL,
        "section_units_path": DOCTRINE_SECTION_UNITS_REL,
        "projection_mode": "graph_projection_with_legacy_overlay",
        "purpose": "Compatibility doctrine surface generated from the canonical doctrine graph. Preserves legacy navigation blocks while making freshness and authority explicit.",
        "self_reference": "The canonical authority is doctrine_graph.json. This file is a generated operator-facing compatibility lens over that graph plus preserved legacy navigation overlays.",
        "freshness": {
            "graph": _freshness(graph.get("generated_at")),
            "inputs": _freshness((graph.get("compiler") or {}).get("freshest_input_at")),
            "approved_overlay": _freshness(((graph.get("review_overlay") or {}) if isinstance(graph.get("review_overlay"), Mapping) else {}).get("generated_at")),
            "legacy_overlay": _freshness(_file_mtime_iso(repo_root / _PROJECTION_PATHS["doctrine_surface"])),
        },
        "compressed_briefing": compressed_briefing,
        "principle_hierarchy": list((operator_packet.get("principle_hierarchy") or [])),
        "principle_authority": {
            "active_principles": (operator_packet.get("counts") or {}).get("active_principles"),
            "compatibility_principles": (operator_packet.get("counts") or {}).get("compatibility_principles"),
        },
        "projection_status": list((operator_packet.get("projection_status") or [])),
        "attention": list((operator_packet.get("attention") or [])),
        "review_overlay": dict(graph.get("review_overlay") or {}) if isinstance(graph.get("review_overlay"), Mapping) else {},
        "code_to_doctrine": _code_to_doctrine(graph, section_units),
        "authority_chain": {
            "canonical_graph": DOCTRINE_GRAPH_REL,
            "compiled_ir": DOCTRINE_COMPILER_IR_REL,
            "approved_overlay": DOCTRINE_APPROVED_OVERLAY_REL,
            "section_units": DOCTRINE_SECTION_UNITS_REL,
            "legacy_overlay_keys": [key for key in legacy_keys if key in legacy],
        },
        "compatibility_tombstones": list(graph.get("compatibility_tombstones") or []),
    }
    for key in legacy_keys:
        value = legacy.get(key)
        if isinstance(value, Mapping):
            surface[key] = dict(value)
        elif isinstance(value, list):
            surface[key] = list(value)
        elif value is not None:
            surface[key] = value
    surface.setdefault("theme_clusters", {})
    surface.setdefault("raw_seed_assimilation", {})
    surface.setdefault("self_audit", {})
    return surface


def build_doctrine_index_projection(repo_root: Path, graph: Mapping[str, Any]) -> dict[str, Any]:
    legacy = _load_legacy_projection(repo_root, "doctrine_index")
    nodes = [item for item in (graph.get("nodes") or []) if isinstance(item, Mapping)]
    edge_summary = _edge_summary(graph)

    principles = []
    concepts = []
    mechanisms = []
    skills = []
    resources = []
    module_seeds = []
    for node in nodes:
        node_id = _string(node.get("id"))
        identity = node.get("identity") if isinstance(node.get("identity"), Mapping) else {}
        record = {
            "id": node_id,
            "slug": _string(identity.get("slug")),
            "title": _string(identity.get("title")),
            "status": _string(node.get("status")) or None,
            "tags": list(node.get("tags") or []),
            "file": _string((node.get("runtime") or {}).get("source_path")),
        }
        if _string(node.get("kind")) == "principle":
            lineage = node.get("lineage") if isinstance(node.get("lineage"), Mapping) else {}
            record["parent_ids"] = [_string(item) for item in (lineage.get("parent_ids") or []) if _string(item)]
            record["root_id"] = _string(lineage.get("root_id")) or None
            record["tier"] = lineage.get("tier")
            record["role"] = _string(lineage.get("role")) or None
            record["authority_mode"] = _string(node.get("authority_mode")) or "peer_authority"
            record["authority_status"] = _string(((node.get("content") or {}) if isinstance(node.get("content"), Mapping) else {}).get("authority_status")) or None
            record["concept_edges"] = edge_summary["principle_to_concept"].get(node_id, [])
            principles.append(record)
        elif _string(node.get("kind")) == "concept":
            record["principle_edges"] = [_string(item) for item in ((node.get("lineage") or {}).get("parent_ids") or []) if _string(item)]
            record["mechanism_edges"] = edge_summary["concept_to_mechanism"].get(node_id, [])
            concepts.append(record)
        elif _string(node.get("kind")) == "mechanism":
            deps = edge_summary["mechanism_dependency_graph"].get(node_id, {"upstream": [], "downstream": []})
            record["concept_edges"] = [_string(item) for item in ((node.get("lineage") or {}).get("parent_ids") or []) if _string(item)]
            record["upstream"] = deps.get("upstream") or []
            record["downstream"] = deps.get("downstream") or []
            record["drift_sensitivity"] = _string((node.get("runtime") or {}).get("drift_sensitivity")) or None
            mechanisms.append(record)
        elif _string(node.get("kind")) == "skill":
            record["principle_edges"] = [
                _string(edge.get("target"))
                for edge in (node.get("edges") or [])
                if isinstance(edge, Mapping) and _string(edge.get("relation")) == "guided_by"
            ]
            record["mechanism_edges"] = [
                _string(edge.get("target"))
                for edge in (node.get("edges") or [])
                if isinstance(edge, Mapping) and _string(edge.get("relation")) == "uses"
            ]
            skills.append(record)
        elif _string(node.get("kind")) == "resource":
            record["source_kind"] = _string((node.get("runtime") or {}).get("source_kind"))
            resources.append(record)
        elif _string(node.get("kind")) == "module_seed":
            record["doctrine_refs"] = list(((node.get("content") or {}) if isinstance(node.get("content"), Mapping) else {}).get("doctrine_refs") or [])
            module_seeds.append(record)

    statistics = {
        "total_principles": len(principles),
        "active_principles": len([item for item in principles if _string(item.get("authority_mode")) != "compatibility_only"]),
        "compatibility_principles": len([item for item in principles if _string(item.get("authority_mode")) == "compatibility_only"]),
        "total_concepts": len(concepts),
        "total_mechanisms": len(mechanisms),
        "total_skills": len(skills),
        "total_resources": len(resources),
        "total_module_seeds": len(module_seeds),
        "total_edges": {
            "principle_to_concept": sum(len(v) for v in edge_summary["principle_to_concept"].values()),
            "concept_to_mechanism": sum(len(v) for v in edge_summary["concept_to_mechanism"].values()),
            "mechanism_to_mechanism": sum(
                len(v.get("upstream") or []) + len(v.get("downstream") or [])
                for v in edge_summary["mechanism_dependency_graph"].values()
            ),
        },
    }

    projection = {
        "kind": "doctrine_index",
        "schema_version": "doctrine_index_v1",
        "generated_at": graph.get("generated_at") or _utc_now(),
        "compiler_target": DOCTRINE_GRAPH_REL,
        "source": {
            "registry": "codex/doctrine/doctrine_registry.json",
            "graph": DOCTRINE_GRAPH_REL,
            "principles_path": _string((graph.get("active_family") or {}).get("principles_source_path")) or None,
        },
        "note": "Full edge projection regenerated from the canonical doctrine graph while preserving compatibility fields expected by older doctrine consumers.",
        "statistics": statistics,
        "principles": principles,
        "concepts": concepts,
        "mechanisms": mechanisms,
        "skills": skills,
        "resources": resources,
        "module_seeds": module_seeds,
        "edge_summary": edge_summary,
        "freshness": {
            "graph": _freshness(graph.get("generated_at")),
            "inputs": _freshness((graph.get("compiler") or {}).get("freshest_input_at")),
        },
    }
    if isinstance(legacy.get("coverage_map"), Mapping):
        projection["coverage_map"] = dict(legacy["coverage_map"])
    else:
        projection["coverage_map"] = {}
    return projection


def build_doctrine_routing_projection(
    repo_root: Path,
    graph: Mapping[str, Any],
    compiler_ir: Mapping[str, Any],
) -> dict[str, Any]:
    legacy = _load_legacy_projection(repo_root, "doctrine_routing")
    nodes = [item for item in (graph.get("nodes") or []) if isinstance(item, Mapping)]
    by_id = {_string(node.get("id")): dict(node) for node in nodes if _string(node.get("id"))}
    kind_by_id = {node_id: _string(node.get("kind")) for node_id, node in by_id.items()}
    adjacent: dict[str, list[str]] = defaultdict(list)
    for edge in graph.get("edges") or []:
        if not isinstance(edge, Mapping):
            continue
        source = _string(edge.get("source"))
        target = _string(edge.get("target"))
        if source and target:
            adjacent[source].append(target)

    def _explore_targets(node_id: str) -> list[str]:
        return sorted(_dedupe_strings(adjacent.get(node_id) or []))[:8]

    concept_routing: dict[str, Any] = {}
    mechanism_routing: dict[str, Any] = {}
    for node_id, node in by_id.items():
        identity = node.get("identity") if isinstance(node.get("identity"), Mapping) else {}
        explore = _explore_targets(node_id)
        improve = [
            f"Review {_string((node.get('runtime') or {}).get('source_path')) or node_id} against {DOCTRINE_GRAPH_REL}"
        ]
        if _string(node.get("authority_mode")) == "projection_candidate":
            improve.append("Check whether this concept should collapse into a projection over another doctrine node.")
        if kind_by_id[node_id] == "concept":
            concept_routing[node_id] = {
                "explore": explore,
                "improve": improve,
                "reference": [_string(identity.get("slug")) or node_id],
            }
        elif kind_by_id[node_id] == "mechanism":
            content = node.get("content") if isinstance(node.get("content"), Mapping) else {}
            loci = [
                _string(item.get("path"))
                for item in (content.get("code_loci") or [])
                if isinstance(item, Mapping) and _string(item.get("path"))
            ]
            mechanism_routing[node_id] = {
                "concept": (_string((node.get("lineage") or {}).get("parent_ids")[0]) if (node.get("lineage") or {}).get("parent_ids") else None),
                "code": loci,
                "annex_patterns": [],
            }

    projection = {
        "kind": "doctrine_routing",
        "schema_version": "doctrine_routing_v1",
        "generated_at": graph.get("generated_at") or _utc_now(),
        "compiler_target": DOCTRINE_GRAPH_REL,
        "purpose": "Generated routing compatibility layer over the canonical doctrine graph. Keeps legacy routing narratives while refreshing concept and mechanism routes from live graph edges.",
        "self_reference": "This routing surface is downstream of doctrine_graph.json and compiler IR. Any preserved legacy routing blocks are compatibility overlays, not separate authorities.",
        "runtime_spec": legacy.get("runtime_spec") if isinstance(legacy.get("runtime_spec"), Mapping) else {
            "path": "codex/doctrine/doctrine_runtime.json",
            "role": "Kernel-emitted doctrine control plane.",
            "emit": "python3 kernel.py --doctrine-runtime",
        },
        "routing_principles": list(legacy.get("routing_principles") or [
            "Routes are projections over the canonical doctrine graph.",
            "Compatibility overlays may remain, but authority flows from doctrine_graph.json and doctrine_compiler_ir.json.",
            "Agents should prefer generated routes over ad hoc doctrine tree reads.",
        ]),
        "concept_routing": concept_routing,
        "mechanism_routing": mechanism_routing,
        "projection_status": list(compiler_ir.get("projection_updates") or []),
        "freshness": {
            "graph": _freshness(graph.get("generated_at")),
            "inputs": _freshness((graph.get("compiler") or {}).get("freshest_input_at")),
        },
    }
    for key in (
        "metaphor_routing",
        "stable_deliberation_ir",
        "annex_assimilation_ladder",
        "handoff_routing",
        "response_surface_taxonomy",
        "dynamic_probe_routing",
    ):
        value = legacy.get(key)
        if isinstance(value, Mapping):
            projection[key] = dict(value)
        elif isinstance(value, list):
            projection[key] = list(value)
        elif value is not None:
            projection[key] = value
    projection.setdefault("dynamic_probe_routing", {"rules": []})
    return projection


def build_doctrine_ir_proposal(
    repo_root: Path,
    *,
    selected_shards: list[Mapping[str, Any]],
    graph: Mapping[str, Any],
    section_units: Mapping[str, Any],
    base_ir: Mapping[str, Any] | None = None,
    proposal_path: str | None = None,
) -> dict[str, Any]:
    base = dict(base_ir) if isinstance(base_ir, Mapping) else build_doctrine_compiler_ir(repo_root, graph, section_units)
    candidate_nodes: list[dict[str, Any]] = []
    candidate_edges: list[dict[str, Any]] = []
    merge_candidates: list[dict[str, Any]] = []
    split_candidates = list(base.get("split_candidates") or [])
    seen_matches: set[tuple[str, str]] = set()

    for shard in selected_shards:
        if not isinstance(shard, Mapping):
            continue
        shard_id = _string(shard.get("id") or shard.get("shard_id"))
        statement = _string(shard.get("statement") or shard.get("gloss") or shard.get("text") or shard.get("plain_text"))
        if not shard_id or not statement:
            continue
        lower = statement.casefold()
        has_existing_concepts = [_string(item) for item in (shard.get("concept_ids") or []) if _string(item).startswith("con_")]
        if has_existing_concepts:
            proposed_kind = "projection"
        elif any(token in lower for token in (" must ", " should ", " never ", " always ", " preserve ", " treat ")):
            proposed_kind = "principle"
        elif any(token in lower for token in ("loop", "pipeline", "protocol", "state machine", "surface", "compiler", "dispatch")):
            proposed_kind = "mechanism"
        else:
            proposed_kind = "concept"

        proposal_id = f"prop_{proposed_kind}_{_slugify(shard_id)}"
        tags = _dedupe_strings(
            [_string(item) for item in (shard.get("tags") or []) if _string(item)]
            + [_string(item) for item in (shard.get("mechanisms") or []) if _string(item)]
            + [_string(item) for item in (shard.get("idea_group_ids") or []) if _string(item)]
        )
        candidate_nodes.append(
            {
                "id": proposal_id,
                "proposed_kind": proposed_kind,
                "source_refs": [
                    {"kind": "shard", "id": shard_id},
                    *[
                        {"kind": "raw_seed_paragraph", "id": _string(item)}
                        for item in (shard.get("raw_paragraph_ids") or [])
                        if _string(item)
                    ],
                    *([{"kind": "raw_seed_anchor", "id": _string(shard.get("raw_seed_anchor"))}] if _string(shard.get("raw_seed_anchor")) else []),
                ],
                "proposed_fields": {
                    "title": _title_from_text(statement),
                    "slug": _slugify(statement),
                    "statement": statement,
                    "scope": "family",
                    "status": "draft",
                    "tags": tags,
                    "fidelity": "candidate_node",
                },
                "reason": "Compiled from selected raw-seed shard evidence into a reviewable doctrine proposal.",
            }
        )

        related_ids = has_existing_concepts
        if not related_ids:
            search_terms = " ".join(tags[:4]) or statement
            query_packet = query_doctrine_graph(graph, query=search_terms, limit=4)
            related_ids = [
                _string(item.get("id"))
                for bucket in ("commitment_nodes", "theory_nodes", "grounding_nodes")
                for item in (query_packet.get(bucket) or [])
                if isinstance(item, Mapping) and _string(item.get("id"))
            ]
        for related_id in related_ids[:3]:
            relation = "implements" if proposed_kind in {"mechanism", "projection"} else "refines"
            dedupe_key = (proposal_id, related_id)
            if dedupe_key in seen_matches:
                continue
            seen_matches.add(dedupe_key)
            candidate_edges.append(
                {
                    "id": _stable_candidate_edge_id(proposal_id, related_id, relation),
                    "source": proposal_id,
                    "target": related_id,
                    "relation": relation,
                    "reason": "Shard tags, group hints, or statement overlap suggest this proposal should connect to an existing doctrine node.",
                }
            )
        if proposed_kind == "projection" and related_ids:
            merge_candidates.append(
                {
                    "id": _stable_merge_candidate_id(related_ids[0], [proposal_id]),
                    "survivor_id": related_ids[0],
                    "absorbed_ids": [proposal_id],
                    "reason": "Selected shard appears to deepen an existing concept rather than establish peer doctrine authority.",
                }
            )

    projection_updates = list(base.get("projection_updates") or [])
    if proposal_path:
        projection_updates.append(
            {
                "projection_id": "doctrine_ir_proposal",
                "path": proposal_path,
                "status": "pending_review",
                "reason": "Proposal-only IR artifact emitted from selected shard evidence; durable graph mutation remains gated on review.",
            }
        )
    proposal = {
        **base,
        "generated_at": _utc_now(),
        "mode": "proposal_queue"
        if candidate_nodes
        or candidate_edges
        or merge_candidates
        or split_candidates
        or list(base.get("tombstone_candidates") or [])
        else "projection_only",
        "candidate_nodes": candidate_nodes,
        "candidate_edges": candidate_edges,
        "merge_candidates": merge_candidates,
        "split_candidates": split_candidates,
        "projection_updates": projection_updates,
    }
    return annotate_doctrine_ir_candidate_ids(proposal)


def _node_card(node: Mapping[str, Any]) -> dict[str, Any]:
    runtime = node.get("runtime") if isinstance(node.get("runtime"), Mapping) else {}
    lineage = node.get("lineage") if isinstance(node.get("lineage"), Mapping) else {}
    identity = node.get("identity") if isinstance(node.get("identity"), Mapping) else {}
    content = node.get("content") if isinstance(node.get("content"), Mapping) else {}
    return {
        "id": _string(node.get("id")),
        "kind": _string(node.get("kind")),
        "epistemic_facet": _string(node.get("epistemic_facet")),
        "authority_mode": _string(node.get("authority_mode")) or "peer_authority",
        "authority_status": _string(content.get("authority_status")) or None,
        "title": _string(identity.get("title")),
        "slug": _string(identity.get("slug")),
        "statement": _string(node.get("statement")),
        "scope": _string(node.get("scope")) or None,
        "status": _string(node.get("status")) or None,
        "tags": node.get("tags") if isinstance(node.get("tags"), list) else [],
        "lineage": {
            "root_id": _string(lineage.get("root_id")) or None,
            "parent_ids": [_string(item) for item in (lineage.get("parent_ids") or []) if _string(item)],
            "tier": lineage.get("tier"),
            "role": _string(lineage.get("role")) or None,
        },
        "runtime": {
            "drift_sensitivity": _string(runtime.get("drift_sensitivity")) or None,
            "source_path": _string(runtime.get("source_path")) or None,
            "freshness": _freshness(runtime.get("source_mtime")),
        },
        "projection": {
            "briefing": _string((node.get("projection") or {}).get("briefing")),
            "available_fidelities": list((node.get("projection") or {}).get("available_fidelities") or []),
            "section_unit_ids": list((node.get("projection") or {}).get("section_unit_ids") or []),
        },
    }


def build_doctrine_operator_packet(
    repo_root: Path,
    graph: Mapping[str, Any],
    section_units: Mapping[str, Any],
    compiler_ir: Mapping[str, Any],
) -> dict[str, Any]:
    nodes = [item for item in (graph.get("nodes") or []) if isinstance(item, Mapping)]
    principles = [node for node in nodes if _string(node.get("kind")) == "principle"]
    active_principles = [node for node in principles if _string(node.get("authority_mode")) != "compatibility_only"]
    compatibility_principles = [node for node in principles if _string(node.get("authority_mode")) == "compatibility_only"]
    orchestration_state = _safe_read_json(repo_root / _ORCHESTRATION_STATE_REL)
    docs_focus = _safe_read_json(repo_root / _DOCS_FOCUS_REL)
    orchestration_driver = (orchestration_state or {}).get("driver") if isinstance(orchestration_state, Mapping) else {}
    orchestration_gate = (orchestration_state or {}).get("gate") if isinstance(orchestration_state, Mapping) else {}
    orchestration_next_action = (orchestration_state or {}).get("next_action") if isinstance(orchestration_state, Mapping) else {}
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in active_principles:
        lineage = node.get("lineage") if isinstance(node.get("lineage"), Mapping) else {}
        for parent_id in lineage.get("parent_ids") or []:
            token = _string(parent_id)
            if token:
                children[token].append(dict(node))
    roots = sorted(
        [
            dict(node)
            for node in active_principles
            if int(((node.get("lineage") or {}).get("tier") or 0)) == 0
        ],
        key=lambda node: _string((node.get("identity") or {}).get("title")) or _string(node.get("id")),
    )
    hierarchy = []
    for root in roots[:18]:
        root_id = _string(root.get("id"))
        direct_children = sorted(
            children.get(root_id) or [],
            key=lambda node: (
                int(((node.get("lineage") or {}).get("tier") or 0)),
                _string((node.get("identity") or {}).get("title")) or _string(node.get("id")),
            ),
        )
        hierarchy.append(
            {
                "id": root_id,
                "title": _string((root.get("identity") or {}).get("title")),
                "statement": _projection_briefing(root.get("statement")),
                "children": [
                    {
                        "id": _string(node.get("id")),
                        "title": _string((node.get("identity") or {}).get("title")),
                        "tier": (node.get("lineage") or {}).get("tier"),
                        "role": _string((node.get("lineage") or {}).get("role")),
                    }
                    for node in direct_children[:10]
                ],
                "child_count": len(direct_children),
            }
        )

    attention: list[dict[str, Any]] = []
    for finding in compiler_ir.get("drift_findings") or []:
        if not isinstance(finding, Mapping):
            continue
        attention.append(
            {
                "id": _string(finding.get("id")),
                "kind": _string(finding.get("kind")),
                "severity": _string(finding.get("severity")) or "medium",
                "target": _string(finding.get("target")),
                "summary": _string(finding.get("summary")),
            }
        )
    return {
        "kind": "doctrine_operator_packet",
        "schema_version": "doctrine_operator_packet_v0",
        "generated_at": graph.get("generated_at") or _utc_now(),
        "graph_path": DOCTRINE_GRAPH_REL,
        "compiler_ir_path": DOCTRINE_COMPILER_IR_REL,
        "approved_overlay_path": DOCTRINE_APPROVED_OVERLAY_REL,
        "section_units_path": DOCTRINE_SECTION_UNITS_REL,
        "active_family": graph.get("active_family") or {},
        "counts": {
            "nodes": len(nodes),
            "principles": len([node for node in nodes if _string(node.get("kind")) == "principle"]),
            "active_principles": len(active_principles),
            "compatibility_principles": len(compatibility_principles),
            "concepts": len([node for node in nodes if _string(node.get("kind")) == "concept"]),
            "mechanisms": len([node for node in nodes if _string(node.get("kind")) == "mechanism"]),
            "skills": len([node for node in nodes if _string(node.get("kind")) == "skill"]),
            "resources": len([node for node in nodes if _string(node.get("kind")) == "resource"]),
            "module_seeds": len([node for node in nodes if _string(node.get("kind")) == "module_seed"]),
            "section_units": len(section_units.get("units") or []),
            "compatibility_tombstones": len(graph.get("compatibility_tombstones") or []),
        },
        "freshness": {
            "graph": _freshness(graph.get("generated_at")),
            "inputs": _freshness((graph.get("compiler") or {}).get("freshest_input_at")),
            "system_view": _freshness(_file_mtime_iso(repo_root / _SYSTEM_VIEW_REL)),
        },
        "control_state": {
            "active_driver": _string((orchestration_state or {}).get("active_driver")),
            "current_driver": _string((orchestration_driver or {}).get("current_driver")),
            "gate_reason": _string((orchestration_gate or {}).get("gate_reason")) if isinstance(orchestration_gate, Mapping) else None,
            "next_action": _string((orchestration_next_action or {}).get("command")) if isinstance(orchestration_next_action, Mapping) else None,
        },
        "docs_focus": {
            "active_preset_id": _string((docs_focus or {}).get("active_preset_id")) or "neutral",
            "label": _string((docs_focus or {}).get("label")) or "Neutral",
        },
        "review_overlay": dict(graph.get("review_overlay") or {}) if isinstance(graph.get("review_overlay"), Mapping) else {},
        "principle_hierarchy": hierarchy,
        "attention": attention[:12],
        "projection_status": [
            {
                "projection_id": _string(item.get("projection_id")),
                "path": _string(item.get("path")),
                "status": _string(item.get("status")),
                "reason": _string(item.get("reason")),
            }
            for item in (compiler_ir.get("projection_updates") or [])
            if isinstance(item, Mapping)
        ],
        "compatibility_tombstones": list(graph.get("compatibility_tombstones") or [])[:24],
        "node_cards": [_node_card(node) for node in nodes[:120]],
    }


def build_doctrine_bundle(repo_root: Path) -> dict[str, Any]:
    graph = build_doctrine_graph(repo_root)
    section_units = build_doctrine_section_units(repo_root, graph)
    compiler_ir = build_doctrine_compiler_ir(
        repo_root,
        graph,
        section_units,
        planned_projection_ids={"doctrine_surface", "doctrine_index", "doctrine_routing"},
    )
    operator_packet = build_doctrine_operator_packet(repo_root, graph, section_units, compiler_ir)
    surface_projection = build_doctrine_surface_projection(repo_root, graph, compiler_ir, section_units, operator_packet)
    index_projection = build_doctrine_index_projection(repo_root, graph)
    routing_projection = build_doctrine_routing_projection(repo_root, graph, compiler_ir)
    return {
        "graph": graph,
        "section_units": section_units,
        "compiler_ir": compiler_ir,
        "operator_packet": operator_packet,
        "surface_projection": surface_projection,
        "index_projection": index_projection,
        "routing_projection": routing_projection,
    }


def load_doctrine_graph(repo_root: Path, rebuild_if_missing: bool = False) -> dict[str, Any] | None:
    payload = _safe_read_json(repo_root / DOCTRINE_GRAPH_REL)
    if isinstance(payload, Mapping):
        return dict(payload)
    if rebuild_if_missing:
        return build_doctrine_graph(repo_root)
    return None


def load_doctrine_section_units(repo_root: Path, rebuild_if_missing: bool = False) -> dict[str, Any] | None:
    payload = _safe_read_json(repo_root / DOCTRINE_SECTION_UNITS_REL)
    if isinstance(payload, Mapping):
        return dict(payload)
    if rebuild_if_missing:
        graph = load_doctrine_graph(repo_root, rebuild_if_missing=True)
        if graph is None:
            return None
        return build_doctrine_section_units(repo_root, graph)
    return None


def write_compiled_doctrine_artifacts(
    repo_root: Path,
    bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(bundle) if isinstance(bundle, Mapping) else build_doctrine_bundle(repo_root)
    graph = payload.get("graph")
    compiler_ir = payload.get("compiler_ir")
    section_units = payload.get("section_units")
    surface_projection = payload.get("surface_projection")
    index_projection = payload.get("index_projection")
    routing_projection = payload.get("routing_projection")
    for rel_path, value in [
        (DOCTRINE_GRAPH_REL, graph),
        (DOCTRINE_COMPILER_IR_REL, compiler_ir),
        (DOCTRINE_SECTION_UNITS_REL, section_units),
        (_PROJECTION_PATHS["doctrine_surface"], surface_projection),
        (_PROJECTION_PATHS["doctrine_index"], index_projection),
        (_PROJECTION_PATHS["doctrine_routing"], routing_projection),
    ]:
        if not isinstance(value, Mapping):
            continue
        target = repo_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def find_doctrine_node(graph: Mapping[str, Any], node_id: str) -> dict[str, Any] | None:
    token = _string(node_id)
    for node in graph.get("nodes") or []:
        if isinstance(node, Mapping) and _string(node.get("id")) == token:
            return dict(node)
    return None


def query_doctrine_graph(
    graph: Mapping[str, Any],
    *,
    query: str,
    section_units: Mapping[str, Any] | None = None,
    limit: int = 12,
    runtime_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    query_token = _string(query)
    normalized = _normalized_text(query_token)
    nodes = [dict(node) for node in (graph.get("nodes") or []) if isinstance(node, Mapping)]
    ranked: list[tuple[int, dict[str, Any]]] = []
    for node in nodes:
        score = 0
        node_id = _string(node.get("id"))
        identity = node.get("identity") if isinstance(node.get("identity"), Mapping) else {}
        authority_mode = _string(node.get("authority_mode")) or "peer_authority"
        if not normalized:
            lineage = node.get("lineage") if isinstance(node.get("lineage"), Mapping) else {}
            score = 100 if _string(node.get("kind")) == "principle" and int(lineage.get("tier") or 0) == 0 else 10
        else:
            haystacks = {
                "id": _normalized_text(node_id),
                "slug": _normalized_text(identity.get("slug")),
                "title": _normalized_text(identity.get("title")),
                "statement": _normalized_text(node.get("statement")),
                "tags": " ".join(_tokenize(" ".join(node.get("tags") or []))),
            }
            if haystacks["id"] == normalized:
                score += 120
            if normalized and normalized in haystacks["slug"]:
                score += 95
            if normalized and normalized in haystacks["title"]:
                score += 85
            if normalized and normalized in haystacks["statement"]:
                score += 60
            if normalized and normalized in haystacks["tags"]:
                score += 40
            norm_tokens = set(normalized.split())
            overlap = len(norm_tokens & set(_tokenize(" ".join(haystacks.values()))))
            score += overlap * 12
        if authority_mode == "compatibility_only":
            score -= 20
        if score > 0:
            ranked.append((score, node))
    ranked.sort(
        key=lambda item: (
            -item[0],
            int(((item[1].get("lineage") or {}).get("tier") or 99)),
            _string((item[1].get("identity") or {}).get("title")) or _string(item[1].get("id")),
        )
    )
    selected = [_node_card(node) for _, node in ranked[: max(1, min(limit, 50))]]
    selected_ids = {_string(card.get("id")) for card in selected if _string(card.get("id"))}

    related_operational_cards: list[dict[str, Any]] = []
    if selected_ids:
        for node in nodes:
            kind = _string(node.get("kind"))
            if kind not in {"skill", "resource", "module_seed"}:
                continue
            node_id = _string(node.get("id"))
            if not node_id or node_id in selected_ids:
                continue
            content = node.get("content") if isinstance(node.get("content"), Mapping) else {}
            related_targets: set[str] = set()
            for edge in node.get("edges") or []:
                if not isinstance(edge, Mapping):
                    continue
                target = _string(edge.get("target"))
                if target:
                    related_targets.add(target)
            for ref in content.get("doctrine_refs") or []:
                ref_token = _string(ref)
                if ref_token:
                    related_targets.add(ref_token)
            if related_targets & selected_ids:
                related_operational_cards.append(_node_card(node))

    def _merge_cards(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for group in groups:
            for card in group:
                token = _string(card.get("id"))
                if not token or token in seen:
                    continue
                seen.add(token)
                merged.append(card)
        return merged

    grouped = {
        "commitment_nodes": [
            card
            for card in selected
            if card.get("epistemic_facet") == "commitment" and card.get("authority_mode") != "compatibility_only"
        ],
        "theory_nodes": [
            card
            for card in selected
            if card.get("epistemic_facet") == "theory" and card.get("authority_mode") != "projection_candidate"
        ],
        "grounding_nodes": [card for card in selected if card.get("epistemic_facet") == "grounding"],
        "procedures": _merge_cards(
            [card for card in selected if card.get("epistemic_facet") == "procedure"],
            [card for card in related_operational_cards if card.get("epistemic_facet") == "procedure"],
        ),
        "resources": _merge_cards(
            [card for card in selected if card.get("epistemic_facet") == "imported_knowledge"],
            [card for card in related_operational_cards if card.get("epistemic_facet") == "imported_knowledge"],
        ),
        "module_seeds": _merge_cards(
            [card for card in selected if card.get("epistemic_facet") == "module_seed"],
            [card for card in related_operational_cards if card.get("epistemic_facet") == "module_seed"],
        ),
        "compatibility_aliases": [
            card
            for card in selected
            if card.get("authority_mode") in {"projection_candidate", "compatibility_only"}
        ],
    }
    relevant_units = []
    if isinstance(section_units, Mapping):
        matched_ids = selected_ids | {_string(card.get("id")) for card in related_operational_cards if _string(card.get("id"))}
        for unit in section_units.get("units") or []:
            if not isinstance(unit, Mapping):
                continue
            refs = {_string(item) for item in (unit.get("doctrine_refs") or []) if _string(item)}
            text_hit = normalized and normalized in _normalized_text(
                " ".join(
                    [
                        _string(unit.get("title")),
                        _string(unit.get("summary")),
                        " ".join(unit.get("substrate_anchors") or []),
                    ]
                )
            )
            if refs & matched_ids or text_hit:
                relevant_units.append(
                    {
                        "id": _string(unit.get("id")),
                        "title": _string(unit.get("title")),
                        "source_path": _string(unit.get("source_path")),
                        "fidelity": _string(unit.get("fidelity")),
                        "doctrine_refs": list(unit.get("doctrine_refs") or []),
                    }
                )
    return {
        "kind": "doctrine_query_packet",
        "schema_version": "doctrine_query_packet_v0",
        "generated_at": _utc_now(),
        "query": query_token or None,
        "summary": {
            "total_matches": len(ranked),
            "returned": len(selected),
            "graph_generated_at": graph.get("generated_at"),
        },
        "commitment_nodes": grouped["commitment_nodes"],
        "theory_nodes": grouped["theory_nodes"],
        "grounding_nodes": grouped["grounding_nodes"],
        "procedures": grouped["procedures"],
        "resources": grouped["resources"],
        "module_seeds": grouped["module_seeds"],
        "compatibility_aliases": grouped["compatibility_aliases"],
        "runtime_state": dict(runtime_state) if isinstance(runtime_state, Mapping) else {},
        "freshness": {
            "graph": _freshness(graph.get("generated_at")),
            "inputs": _freshness((graph.get("compiler") or {}).get("freshest_input_at")),
        },
        "authority_chain": {
            "graph": DOCTRINE_GRAPH_REL,
            "compiler_ir": DOCTRINE_COMPILER_IR_REL,
            "section_units": DOCTRINE_SECTION_UNITS_REL,
        },
        "relevant_projections": relevant_units[:8],
    }
