"""
Dynamic paper-as-navigation-lattice view.

This live-computed route reads an already-selected paper-module slug from
authored source, emits source-anchored affordance rows, and keeps paper prose as
one view over the row lattice rather than the canonical machine container.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_SLUG = "navigation_hologram_theory"
PAPER_ROOT = Path("codex/doctrine/paper_modules")
STD_NAVIGATION_CONTRACT = Path("codex/standards/std_navigation_contract.json")
STD_PAPER_MODULE = Path("codex/standards/std_paper_module.json")
RAW_SEED_PATH = Path("obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.json")

SECTION_FACET_HINTS = {
    "tldr_compressed_view": "claim",
    "intent": "intent",
    "self_application_header_this_module_as_affordance_row": "identity",
    "refinement_option_surface_not_trigger_zoo": "mechanism",
    "deeper_refinement_field_level_dolls_and_connector_vocabulary": "connector",
    "deeper_refinement_bands_are_schemas_not_lengths": "band_schema",
    "deeper_refinement_same_grammar_across_artifact_kinds": "cross_kind_grammar",
    "shape": "mechanism",
    "code_loci": "evidence",
    "current_state": "currentness",
    "deliverables_what_this_subsystem_lets_a_cold_agent_do": "triggers",
    "gap": "gap",
    "gap_what_will_is_signaling": "voice",
    "refresh_contract": "currentness",
}

SELF_ROW_FACETS = {
    "nav_hologram.root_thesis": "claim",
    "nav_hologram.option_surface": "mechanism",
    "nav_hologram.field_dolls": "connector",
    "nav_hologram.band_schema": "band_schema",
    "nav_hologram.cross_kind_grammar": "cross_kind_grammar",
    "nav_hologram.bridge_dispatch_packet": "worker_packet",
    "nav_hologram.file_header_experiments": "validation",
    "nav_hologram.cognitive_asset_lifecycle": "lifecycle",
    "nav_hologram.provider_metabolism": "metabolism",
    "nav_hologram.contract_tail": "evidence",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _compact(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _trim(text: Any, *, max_chars: int = 360) -> str:
    compact = _compact(text)
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _slugify(text: str) -> str:
    token = re.sub(r"`([^`]+)`", r"\1", _compact(text).casefold())
    token = re.sub(r"[^a-z0-9]+", "_", token).strip("_")
    return token or "section"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(data) if isinstance(data, dict) else {}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))


def _estimated_tokens(value: Any) -> int:
    return max(1, (_json_bytes(value) + 3) // 4)


def _frontmatter_line(text: str, label: str) -> str:
    pattern = re.compile(rf"^\*?\*?{re.escape(label)}\*?\*?:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(text)
    return _compact(match.group(1)) if match else ""


def _frontmatter_ids(text: str, label: str, prefix: str) -> list[str]:
    value = _frontmatter_line(text, label)
    return list(dict.fromkeys(re.findall(rf"{re.escape(prefix)}_\d+", value)))


def _frontmatter_slugs(text: str, label: str) -> list[str]:
    value = _frontmatter_line(text, label)
    if not value:
        return []
    backticks = re.findall(r"`([^`]+)`", value)
    if backticks:
        return [item for item in backticks if item]
    return [
        item.strip().strip("[]()")
        for item in value.split(",")
        if re.fullmatch(r"[a-z0-9_]+", item.strip().strip("[]()"))
    ]


def _markdown_sections(text: str) -> list[dict[str, Any]]:
    matches = list(re.finditer(r"^(#{2,3})\s+(.+?)\s*$", text, flags=re.MULTILINE))
    rows: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    line_starts = [0]
    for match in re.finditer("\n", text):
        line_starts.append(match.end())

    def line_for(offset: int) -> int:
        line = 1
        for index, start in enumerate(line_starts, start=1):
            if start > offset:
                break
            line = index
        return line

    for index, match in enumerate(matches):
        heading = _compact(match.group(2))
        if not heading:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        base_slug = _slugify(heading)
        seen[base_slug] = seen.get(base_slug, 0) + 1
        slug = base_slug if seen[base_slug] == 1 else f"{base_slug}_{seen[base_slug]}"
        rows.append(
            {
                "slug": slug,
                "heading": heading,
                "level": len(match.group(1)),
                "line": line_for(match.start()),
                "body": text[start:end].strip(),
            }
        )
    return rows


def _first_h1(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    return _compact(match.group(1)) if match else fallback


def _find_section(sections: Sequence[Mapping[str, Any]], slug: str) -> Mapping[str, Any] | None:
    for section in sections:
        if section.get("slug") == slug:
            return section
    return None


def _selected_section_slugs(sections: Sequence[Mapping[str, Any]], *, slug: str) -> list[str]:
    if slug == DEFAULT_SLUG:
        return [
            "tldr_compressed_view",
            "self_application_header_this_module_as_affordance_row",
            "refinement_option_surface_not_trigger_zoo",
            "deeper_refinement_field_level_dolls_and_connector_vocabulary",
            "deeper_refinement_bands_are_schemas_not_lengths",
            "deeper_refinement_same_grammar_across_artifact_kinds",
            "shape",
            "code_loci",
            "current_state",
            "deliverables_what_this_subsystem_lets_a_cold_agent_do",
            "gap_what_will_is_signaling",
            "refresh_contract",
        ]

    priority = [
        "tldr_compressed_view",
        "intent",
        "current_state",
        "code_loci",
        "gap",
        "gap_what_will_is_signaling",
        "refresh_contract",
    ]
    existing = [str(section.get("slug") or "") for section in sections if section.get("slug")]
    selected: list[str] = []
    for section_slug in [*priority, *existing]:
        if section_slug and section_slug not in selected and section_slug in existing:
            selected.append(section_slug)
        if len(selected) >= 12:
            break
    return selected


def _parse_self_rows(text: str, *, source_path: str, fingerprint: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("| `nav_hologram."):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        row_id = cells[0].strip("`")
        native_band = cells[1].strip("`")
        flag = cells[2]
        open_when = cells[3]
        evidence = cells[4].replace("`", "")
        facet = SELF_ROW_FACETS.get(row_id, "claim")
        rows.append(
            {
                "row_id": row_id,
                "kind": "paper_module_affordance_row",
                "source_anchor": {"path": source_path, "line": line_number},
                "scope": "section",
                "facet": facet,
                "native_band": native_band,
                "authority_state": "authored_self_application_fixture",
                "freshness": {"source_fingerprint": fingerprint},
                "flag": flag,
                "open_when": open_when,
                "evidence_hint": evidence,
                "band_packets": {
                    "flag": {"text": _trim(flag, max_chars=180), "drilldown_to": "card"},
                    "card": {
                        "text": _trim(f"{flag} Open when: {open_when}", max_chars=620),
                        "drilldown_to": "context",
                    },
                    "context": {
                        "text": _trim(f"{flag} Evidence or section hint: {evidence}. Open when: {open_when}", max_chars=1100),
                        "drilldown_to": "evidence",
                    },
                    "evidence": {
                        "text": f"{source_path}:{line_number}",
                        "drilldown_to": source_path,
                    },
                },
                "expansion_commands": [
                    "./repo-python kernel.py --paper-lattice navigation_hologram_theory --band card",
                    "./repo-python kernel.py --paper-module navigation_hologram_theory",
                ],
                "connectors": [
                    {
                        "verb": "part_of",
                        "target_ref": "paper_module:navigation_hologram_theory",
                        "reverse_verb": "contains",
                        "forward_gloss": "Self-application row belongs to the navigation hologram theory paper view.",
                    }
                ],
            }
        )
    return rows


def _section_rows(
    sections: Sequence[Mapping[str, Any]],
    *,
    source_path: str,
    slug: str,
    title: str,
    fingerprint: str,
) -> list[dict[str, Any]]:
    selected = _selected_section_slugs(sections, slug=slug)
    rows: list[dict[str, Any]] = []
    for section_slug in selected:
        section = _find_section(sections, section_slug)
        if not section:
            continue
        heading = str(section.get("heading") or section_slug)
        body = str(section.get("body") or "")
        facet = SECTION_FACET_HINTS.get(section_slug, "claim")
        row_id = f"paper_section:{slug}:{section_slug}"
        rows.append(
            {
                "row_id": row_id,
                "kind": "paper_module_section",
                "source_anchor": {"path": source_path, "line": section.get("line")},
                "scope": "section",
                "facet": facet,
                "native_band": "card",
                "authority_state": "authored_source_projected_row",
                "freshness": {"source_fingerprint": fingerprint},
                "heading": heading,
                "flag": _trim(body or heading, max_chars=180),
                "band_packets": {
                    "flag": {"text": _trim(body or heading, max_chars=180), "drilldown_to": "card"},
                    "card": {"text": _trim(body or heading, max_chars=760), "drilldown_to": "context"},
                    "context": {"text": _trim(body or heading, max_chars=1500), "drilldown_to": "evidence"},
                    "evidence": {"text": f"{source_path}:{section.get('line')}", "drilldown_to": source_path},
                },
                "expansion_commands": [
                    f"./repo-python kernel.py --paper-lattice {slug} --lattice-scope section --lattice-facet {facet} --band card",
                    f"./repo-python kernel.py --paper-module {slug}",
                ],
                "connectors": [
                    {
                        "verb": "part_of",
                        "target_ref": f"paper_module:{slug}",
                        "reverse_verb": "contains",
                        "forward_gloss": f"{heading} is a selectable section facet in {title}.",
                    }
                ],
            }
        )
    return rows


def _principle_insert_rows(
    principle_ids: Sequence[str],
    *,
    source_path: str,
    slug: str,
    fingerprint: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for principle_id in principle_ids:
        rows.append(
            {
                "row_id": f"paper_principle_insert:{slug}:{principle_id}",
                "kind": "paper_module_governing_insert",
                "source_anchor": {"path": source_path, "line": 8},
                "scope": "governing_insert",
                "facet": "principle",
                "native_band": "flag",
                "authority_state": "projected_reference_not_pasted_authority",
                "freshness": {"source_fingerprint": fingerprint},
                "flag": f"{principle_id} governs this dynamic paper view without being pasted as prose authority.",
                "band_packets": {
                    "flag": {
                        "text": f"{principle_id} governs this paper view.",
                        "drilldown_to": "card",
                    },
                    "card": {
                        "text": (
                            f"{principle_id} is projected into {slug} as a governing row. "
                            "Authority remains in the principle source surface."
                        ),
                        "drilldown_to": "evidence",
                    },
                    "context": {
                        "text": (
                            f"Dynamic paper views include {principle_id} as an edge-connected "
                            "governing insert so principles become part of the paper without "
                            "duplicating principle prose."
                        ),
                        "drilldown_to": "evidence",
                    },
                    "evidence": {
                        "text": str(RAW_SEED_PATH),
                        "drilldown_to": f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
                    },
                },
                "expansion_commands": [
                    f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
                    f"./repo-python kernel.py --paper-lattice {slug} --band card",
                ],
                "connectors": [
                    {
                        "verb": "governs",
                        "target_ref": f"paper_module:{slug}",
                        "reverse_verb": "is_governed_by",
                        "forward_gloss": f"{principle_id} constrains the paper view as a governing insert.",
                    }
                ],
            }
        )
    return rows


def _edge_rows(
    *,
    slug: str,
    depends_on: Sequence[str],
    principle_ids: Sequence[str],
    self_rows: Sequence[Mapping[str, Any]],
    section_rows: Sequence[Mapping[str, Any]],
    code_paths: Sequence[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dep in depends_on:
        rows.append(
            {
                "edge_id": f"edge:{slug}:depends_on:{dep}",
                "source_ref": f"paper_module:{slug}",
                "target_ref": f"paper_module:{dep}",
                "verb": "depends_on",
                "reverse_verb": "supports",
                "forward_gloss": f"{slug} needs {dep} as first-order paper-module context.",
                "reverse_gloss": f"{dep} supports the dynamic paper view for {slug}.",
                "authority_posture": "authored_frontmatter",
                "confidence": 0.92,
                "evidence_ref": f"codex/doctrine/paper_modules/{slug}.md::Depends on",
                "drilldown_ref": f"./repo-python kernel.py --paper-module {dep}",
                "band": "card",
                "neighborhood_order": 1,
            }
        )
    for principle_id in principle_ids:
        rows.append(
            {
                "edge_id": f"edge:{principle_id}:governs:{slug}",
                "source_ref": f"principle:{principle_id}",
                "target_ref": f"paper_module:{slug}",
                "verb": "governs",
                "reverse_verb": "is_governed_by",
                "forward_gloss": f"{principle_id} is projected into the paper as a governing row.",
                "reverse_gloss": f"{slug} cites {principle_id} through frontmatter and a dynamic insert row.",
                "authority_posture": "projected_reference_not_pasted_authority",
                "confidence": 0.88,
                "evidence_ref": f"codex/doctrine/paper_modules/{slug}.md::Governing principles",
                "drilldown_ref": f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
                "band": "flag",
                "neighborhood_order": 1,
            }
        )
    for row in [*self_rows, *section_rows]:
        row_id = str(row.get("row_id") or "")
        if row_id:
            rows.append(
                {
                    "edge_id": f"edge:{slug}:contains:{row_id}",
                    "source_ref": f"paper_module:{slug}",
                    "target_ref": row_id,
                    "verb": "contains",
                    "reverse_verb": "part_of",
                    "forward_gloss": "The dynamic paper view contains this selectable affordance row.",
                    "reverse_gloss": "The row expands back to the parent paper view and source module.",
                    "authority_posture": str(row.get("authority_state") or "authored_source"),
                    "confidence": 0.86,
                    "evidence_ref": (row.get("source_anchor") or {}).get("path"),
                    "drilldown_ref": f"./repo-python kernel.py --paper-lattice {slug} --band card",
                    "band": str(row.get("native_band") or "card"),
                    "neighborhood_order": 1,
                }
            )
    for path in code_paths[:8]:
        rows.append(
            {
                "edge_id": f"edge:{slug}:evidenced_by:{path}",
                "source_ref": f"paper_module:{slug}",
                "target_ref": f"code_locus:{path}",
                "verb": "evidenced_by",
                "reverse_verb": "evidences",
                "forward_gloss": f"{path} is implementation evidence cited by the paper module.",
                "reverse_gloss": f"{path} is one code locus that can verify or falsify the paper view.",
                "authority_posture": "authored_code_locus_reference",
                "confidence": 0.76,
                "evidence_ref": f"codex/doctrine/paper_modules/{slug}.md::Code loci",
                "drilldown_ref": f"./repo-python kernel.py --compile {path}",
                "band": "flag",
                "neighborhood_order": 1,
            }
        )
    return rows


def _code_paths(code_loci_body: str) -> list[str]:
    paths = re.findall(r"\]\(\.\./\.\./\.\./([^)]+)\)", code_loci_body)
    paths.extend(re.findall(r"`([^`]+?\.(?:py|json|md|tsx|ts))`", code_loci_body))
    return list(dict.fromkeys(_compact(path) for path in paths if _compact(path)))[:18]


def _packet_for_band(row: Mapping[str, Any], band: str) -> dict[str, Any]:
    packets = row.get("band_packets") if isinstance(row.get("band_packets"), Mapping) else {}
    packet = packets.get(band) or packets.get("card") or packets.get("flag") or {}
    return dict(packet) if isinstance(packet, Mapping) else {}


def _filter_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    scope: str | None,
    facet: str | None,
    band: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if scope and str(row.get("scope")) != scope:
            continue
        if facet and str(row.get("facet")) != facet:
            continue
        projected = {
            key: value
            for key, value in row.items()
            if key not in {"band_packets", "connectors"}
        }
        projected["selected_band"] = band
        projected["band_packet"] = _packet_for_band(row, band)
        projected["connector_count"] = len(row.get("connectors") or [])
        out.append(projected)
    return out


def _budget_trim(packet: dict[str, Any], *, context_budget: int) -> dict[str, Any]:
    budget_bytes = max(1000, int(context_budget or 12000)) * 4
    if _json_bytes(packet) <= budget_bytes:
        packet["budget"]["estimated_tokens"] = _estimated_tokens(packet)
        return packet

    query = packet.get("query") if isinstance(packet.get("query"), Mapping) else {}
    slug = str(query.get("slug") or DEFAULT_SLUG)

    def row_priority(row: Mapping[str, Any]) -> tuple[int, str]:
        row_id = str(row.get("row_id") or "")
        if row_id == f"paper_module:{slug}":
            return (0, row_id)
        if row_id.startswith("nav_hologram."):
            return (10, row_id)
        if row_id == "paper_section:navigation_hologram_theory:shape":
            return (20, row_id)
        if row_id.endswith(":pri_049"):
            return (25, row_id)
        if row_id.startswith("paper_principle_insert:"):
            return (30, row_id)
        return (40, row_id)

    def compact_row(row: Mapping[str, Any]) -> dict[str, Any]:
        out = dict(row)
        if isinstance(out.get("band_packet"), Mapping):
            packet = dict(out["band_packet"])
            if "text" in packet:
                packet["text"] = _trim(packet.get("text"), max_chars=420)
            out["band_packet"] = packet
        if "flag" in out:
            out["flag"] = _trim(out.get("flag"), max_chars=180)
        if "evidence_hint" in out:
            out["evidence_hint"] = _trim(out.get("evidence_hint"), max_chars=120)
        commands = out.get("expansion_commands")
        if isinstance(commands, list) and len(commands) > 1:
            out["expansion_commands"] = commands[:1]
        return out

    def edge_priority(edge: Mapping[str, Any]) -> tuple[int, str]:
        verb = str(edge.get("verb") or "")
        edge_id = str(edge.get("edge_id") or "")
        priority = {
            "depends_on": 0,
            "governs": 30,
            "contains": 20,
            "evidenced_by": 16,
        }.get(verb, 50)
        if "edge:pri_049:" in edge_id:
            priority = 8
        if verb == "contains" and "nav_hologram.option_surface" in edge_id:
            priority = 15
        if verb == "evidenced_by" and "system/lib/navigation_hologram.py" in edge_id:
            priority = 14
        return (priority, edge_id)

    packet = dict(packet)
    rows = [compact_row(row) for row in sorted(packet.get("rows", []), key=row_priority)]
    packet["rows"] = rows[:18]
    packet["edge_rows"] = sorted(packet.get("edge_rows", []), key=edge_priority)[:12]
    axes = packet.get("contract", {}).get("axes") if isinstance(packet.get("contract"), Mapping) else None
    if isinstance(axes, dict) and isinstance(axes.get("edge_shape"), list):
        axes["edge_shape"] = axes["edge_shape"][:8]
    packet["paper_view"]["sections"] = packet.get("paper_view", {}).get("sections", [])[:6]
    packet["budget"]["trimmed_for_budget"] = True
    packet["budget"]["trim_note"] = "Rows/edges were priority-trimmed; rerun with a larger --context-budget or narrower scope/facet."
    packet["budget"]["estimated_tokens"] = _estimated_tokens(packet)
    if _json_bytes(packet) > budget_bytes:
        packet["rows"] = packet["rows"][:14]
        packet["edge_rows"] = sorted(packet.get("edge_rows", []), key=edge_priority)[:8]
        packet["paper_view"]["sections"] = packet.get("paper_view", {}).get("sections", [])[:4]
        packet["budget"]["estimated_tokens"] = _estimated_tokens(packet)
    return packet


def build_dynamic_paper_lattice(
    repo_root: Path | str,
    *,
    slug: str = DEFAULT_SLUG,
    band: str = "card",
    scope: str | None = None,
    facet: str | None = None,
    edge_neighborhood: int = 1,
    context_budget: int = 12000,
) -> dict[str, Any]:
    root = Path(repo_root)
    normalized_slug = _compact(slug or DEFAULT_SLUG)
    if normalized_slug in {"", "root", "__root__"}:
        normalized_slug = DEFAULT_SLUG
    if not re.fullmatch(r"[a-z0-9_]+", normalized_slug):
        return {
            "kind": "dynamic_paper_lattice",
            "schema_version": "dynamic_paper_lattice_v0",
            "error": "invalid_paper_module_slug",
            "requested_slug": normalized_slug,
            "slug_format": "stable paper-module slug: lowercase letters, digits, and underscores",
            "selection_routes": [
                "./repo-python kernel.py --context-pack \"<paper or doctrine task>\" --context-budget 12000",
                "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            ],
            "reason": "Paper lattice is a drilldown for a stable selected paper-module slug, not a free-text search route.",
        }

    rel_path = PAPER_ROOT / f"{normalized_slug}.md"
    path = root / rel_path
    if not path.exists():
        return {
            "kind": "dynamic_paper_lattice",
            "schema_version": "dynamic_paper_lattice_v0",
            "error": "unknown_paper_module_slug",
            "requested_slug": normalized_slug,
            "selection_routes": [
                "./repo-python kernel.py --context-pack \"<paper or doctrine task>\" --context-budget 12000",
                "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            ],
            "reason": "No authored paper module exists for this stable slug; select a row before opening the lattice.",
        }
    text = path.read_text(encoding="utf-8")
    fingerprint = _sha(path)
    title = _first_h1(text, normalized_slug)
    sections = _markdown_sections(text)
    tldr = _find_section(sections, "tldr_compressed_view")
    code_loci = _find_section(sections, "code_loci")
    depends_on = _frontmatter_slugs(text, "Depends on")
    principle_ids = _frontmatter_ids(text, "Governing principles", "pri")
    concept_ids = _frontmatter_ids(text, "Governing concepts", "con")
    mechanism_ids = _frontmatter_ids(text, "Governing mechanisms", "mech")
    source_path = str(rel_path)
    self_rows = _parse_self_rows(text, source_path=source_path, fingerprint=fingerprint)
    section_rows = _section_rows(
        sections,
        source_path=source_path,
        slug=normalized_slug,
        title=title,
        fingerprint=fingerprint,
    )
    principle_rows = _principle_insert_rows(
        principle_ids,
        source_path=source_path,
        slug=normalized_slug,
        fingerprint=fingerprint,
    )
    root_row = {
        "row_id": f"paper_module:{normalized_slug}",
        "kind": "paper_module",
        "source_anchor": {"path": source_path, "line": 1},
        "scope": "module",
        "facet": "identity",
        "native_band": "card",
        "authority_state": "authored_source",
        "freshness": {"source_fingerprint": fingerprint},
        "flag": _trim((tldr or {}).get("body") or title, max_chars=240),
        "band_packets": {
            "flag": {"text": _trim((tldr or {}).get("body") or title, max_chars=180), "drilldown_to": "card"},
            "card": {"text": _trim((tldr or {}).get("body") or title, max_chars=760), "drilldown_to": "context"},
            "context": {"text": _trim((tldr or {}).get("body") or title, max_chars=1500), "drilldown_to": "evidence"},
            "evidence": {"text": source_path, "drilldown_to": source_path},
        },
        "expansion_commands": [
            f"./repo-python kernel.py --paper-lattice {normalized_slug} --band card",
            f"./repo-python kernel.py --paper-module {normalized_slug}",
        ],
        "connectors": [
            {"verb": "depends_on", "target_ref": f"paper_module:{dep}"}
            for dep in depends_on
        ],
    }
    all_rows = [root_row, *self_rows, *section_rows, *principle_rows]
    code_paths = _code_paths(str((code_loci or {}).get("body") or ""))
    edges = _edge_rows(
        slug=normalized_slug,
        depends_on=depends_on,
        principle_ids=principle_ids,
        self_rows=self_rows,
        section_rows=section_rows,
        code_paths=code_paths,
    )
    if edge_neighborhood <= 0:
        edges = []
    selected_rows = _filter_rows(all_rows, scope=scope, facet=facet, band=band)
    source_contract = _load_json(root / STD_NAVIGATION_CONTRACT)
    paper_standard = _load_json(root / STD_PAPER_MODULE)
    paper_contract = paper_standard.get("navigation_contract") if isinstance(paper_standard.get("navigation_contract"), Mapping) else {}
    packet = {
        "kind": "dynamic_paper_lattice",
        "schema_version": "dynamic_paper_lattice_v0",
        "generated_at": _utc_now(),
        "query": {
            "slug": normalized_slug,
            "band": band,
            "scope": scope,
            "facet": facet,
            "edge_neighborhood": edge_neighborhood,
        },
        "budget": {
            "context_budget_tokens": max(1000, int(context_budget or 12000)),
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "contract": {
            "navigation_contract_standard": str(STD_NAVIGATION_CONTRACT),
            "navigation_contract_status": source_contract.get("status"),
            "paper_module_profile_id": paper_contract.get("profile_id"),
            "axes": {
                "bands": paper_contract.get("navigable_bands") or ["tldr", "card", "context", "evidence"],
                "scopes": [row.get("scope") for row in paper_contract.get("navigable_scopes") or []],
                "facets": [row.get("facet") for row in paper_contract.get("navigable_facets") or []],
                "edge_shape": (source_contract.get("edge_row_shape") or {}).get("required_fields") or [],
            },
        },
        "source": {
            "path": source_path,
            "source_fingerprint": fingerprint,
            "authority_state": "authored_source",
            "generated_sidecar_posture": "not_used_for_authority",
            "stable_slug_support": "generic_existing_paper_module_slug",
        },
        "summary": {
            "row_count": len(all_rows),
            "selected_row_count": len(selected_rows),
            "edge_count": len(edges),
            "principle_insert_count": len(principle_rows),
            "self_application_row_count": len(self_rows),
            "code_locus_count": len(code_paths),
        },
        "root_row": _filter_rows([root_row], scope=None, facet=None, band=band)[0],
        "rows": selected_rows,
        "edge_rows": edges,
        "paper_view": {
            "title": title,
            "view_kind": "human_readable_dynamic_paper",
            "sections": [
                {
                    "slot": "thesis",
                    "from_row": f"paper_module:{normalized_slug}",
                    "band": band,
                    "text": _trim((tldr or {}).get("body") or title, max_chars=520),
                },
                {
                    "slot": "governing_principles",
                    "from_rows": [row["row_id"] for row in principle_rows],
                    "band": "flag",
                    "ids": principle_ids,
                },
                {
                    "slot": "self_application_rows",
                    "from_rows": [row["row_id"] for row in self_rows[:10]],
                    "band": "card",
                },
                {
                    "slot": "implementation_evidence",
                    "from_edges": [edge["edge_id"] for edge in edges if edge["verb"] == "evidenced_by"][:8],
                    "band": "flag",
                },
            ],
        },
        "omission_receipt": {
            "omitted": [
                "full paper-module body",
                "full generated paper-module sidecars",
                "full principle registry prose",
                "second-order dependency neighborhoods",
            ],
            "why": "This command proves the row lattice live from authored source; source/evidence remains behind drilldown commands.",
            "drilldowns": [
                f"./repo-python kernel.py --paper-module {normalized_slug}",
                f"./repo-python kernel.py --paper-lattice {normalized_slug} --band context --context-budget 20000",
            ],
        },
        "next_commands": [
            f"./repo-python kernel.py --paper-lattice {normalized_slug} --band card",
            f"./repo-python kernel.py --paper-lattice {normalized_slug} --lattice-facet mechanism --band card",
            f"./repo-python kernel.py --paper-lattice {normalized_slug} --lattice-scope governing_insert --band card",
            f"./repo-python kernel.py --paper-module {normalized_slug}",
        ],
    }
    return _budget_trim(packet, context_budget=max(1000, int(context_budget or 12000)))
