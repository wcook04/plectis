#!/usr/bin/env python3
"""Microcosm Comprehension Plane: a source-body-free, goal-directed read-pack compiler.

A cold agent that clones this repo should not be met with "read the source." It
should be met with ``microcosm comprehend``: a route that compiles bounded read
packs from already-public substrate facts so the agent can answer "what is this?",
"what does this organ do?", and "what may I trust?" without rereading code.

The compiler joins three public-safe, source-body-free inputs:
  - the code-lens join index (organ governance + runner custody + specificity rollups),
  - core/organ_atlas.json (adversarially-verified glosses, families, refs, first commands),
  - core/component_public_synopses.json (one-line, public-site-linted organ synopses).

It never reads source bodies or raw docstring atoms. The atom_value_membrane_v0
makes that boundary explicit:

  presence_only          -- ACTIVE. public-safe: names, glosses, counts, refs, ceilings.
  local_semantic_excerpt -- DORMANT. bounded owned-source excerpts behind explicit local auth.
  source_span_escalation -- ON-DEMAND. exact path+symbol pointers; open source only to mutate/prove.

- Teleology: turn the populated code-lens IR plus the public organ atlas into a
  first-contact comprehension runtime so the queryable graph becomes the default
  entry move, not a dormant artifact.
- Guarantee: every compiled pack is schema microcosm_comprehension_read_pack_v0,
  carries export_band="presence_only" and a non-authorizing authority ceiling, and
  contains no source bodies or "- Teleology:"-style raw atom bullets.
- Fails: refuses (ValueError) to compile from a join index whose payload reports
  source_bodies_exported; degrades to atlas-only packs when the join index is absent.
- Reads: receipts/code_lens/code_lens_join_index_v0.json, core/organ_atlas.json,
  core/component_public_synopses.json under the resolved substrate root.
- Writes: nothing by default; build_cached_read_packs writes prebuilt receipts.
- Non-goal: does not authorize release, source-body export, static-analysis
  correctness, or whole-system correctness; it is a navigation read model only.
- Escalates-to: scripts/build_code_lens_join_index.py to (re)build the IR it reads.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

READ_PACK_SCHEMA = "microcosm_comprehension_read_pack_v0"
ASSAY_SCHEMA = "microcosm_cold_agent_comprehension_assay_v0"
PACKET_ATLAS_SCHEMA = "microcosm_comprehension_packet_atlas_v0"
PACKET_ROUTE_ASSAY_SCHEMA = "microcosm_packet_route_assay_v0"
SELF_MODEL_SCHEMA = "microcosm_whole_system_self_model_v0"
WHOLE_SYSTEM_ASSAY_SCHEMA = "microcosm_whole_system_comprehension_assay_v0"

# atom_value_membrane_v0 -- the export contract every read pack declares. Only the
# presence_only band is active in v0; the richer bands are declared but dormant so a
# later strike can light them up without changing the pack schema.
MEMBRANE_V0: dict[str, Any] = {
    "membrane_version": "atom_value_membrane_v0",
    "active_band": "presence_only",
    "bands": {
        "presence_only": {
            "state": "active",
            "exports": "names, public glosses, counts, refs, ceilings",
            "source_bodies": False,
        },
        "local_semantic_excerpt": {
            "state": "dormant",
            "exports": "bounded owned-source excerpts behind explicit local authority",
            "source_bodies": False,
            "requires": "source_body_export_authorized is False even when active",
        },
        "source_span_escalation": {
            "state": "on_demand",
            "exports": "exact path + symbol pointers only; open source to mutate or prove",
            "source_bodies": False,
        },
    },
}

# Non-authorizing ceiling stamped on every pack -- comprehension never grants release,
# source export, static-analysis authority, or whole-system correctness.
AUTHORITY_CEILING: dict[str, bool] = {
    "release_authorized": False,
    "source_body_export_authorized": False,
    "static_analysis_authority": False,
    "whole_system_correctness_authorized": False,
}

# Markers that must never appear in a presence_only pack -- their presence would mean a
# raw docstring atom (not a public gloss) leaked into the read model.
_ATOM_BULLET_MARKERS = (
    "- Teleology:",
    "- Guarantee:",
    "- Fails:",
    "- Reads:",
    "- Writes:",
    "- Non-goal:",
)

# Canonical first-contact routes a cold agent should run, in order.
_START_HERE_ROUTES = [
    "microcosm comprehend --first-contact",
    "microcosm comprehend --slice authority",
    "microcosm comprehend --organ <organ_id>",
    "microcosm comprehend --slice organs",
]

# --- atom_value_membrane_v1: the local_semantic_excerpt band -----------------------
# This band is the FIRST sanctioned exporter of authored docstring-atom prose, and it
# is deliberately bounded: owned source only (custody-gated), per-atom char cap, secret
# and private-path scrubbing, and NEVER written into the committed presence_only cache.
LOCAL_EXCERPT_SCHEMA = "microcosm_atom_value_excerpt_v1"
HARD_ASSAY_SCHEMA = "microcosm_hard_comprehension_assay_v1"
# The owned package root whose authored atoms may be excerpted locally.
OWNED_EXCERPT_ROOT = "src/microcosm_core/"
# Per-atom character cap and total per-file pack byte budget for excerpts.
MAX_ATOM_CHARS = 240
MAX_EXCERPT_PACK_BYTES = 60000
# Secret-shape and private-home-path patterns: any atom value matching is DROPPED
# (never emitted), so an excerpt pack cannot leak a credential or an operator path.
_SECRET_SHAPE_RE = re.compile(
    r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY",
)
_PRIVATE_PATH_RE = re.compile(r"/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+")


def default_root() -> Path:
    """Resolve the substrate root that holds core/ and receipts/.

    - Teleology: let comprehend find its public inputs regardless of the caller's cwd.
    - Guarantee: returns the microcosm-substrate directory (this file's parents[2]).
    - Fails: never raises; pure path arithmetic.
    - Reads: only __file__.
    """
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    """Parse a JSON file, returning None when it is absent or unreadable.

    - Teleology: one tolerant reader so a missing join index degrades instead of crashing.
    - Guarantee: returns the parsed value, or None when the path is missing/unparseable.
    - Fails: never raises; OSError/ValueError are swallowed into None.
    - Reads: the file at ``path``.
    """
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def load_inputs(root: Path | None = None) -> dict[str, Any]:
    """Load the three public inputs the compiler joins, tolerating absent ones.

    - Teleology: assemble the source-body-free input bundle for every compile call.
    - Guarantee: returns {root, join_index, atlas, synopses, atlas_by_organ,
      join_by_organ, synopsis_by_organ, join_index_present}; missing files become None
      and an empty index rather than an error.
    - Fails: ValueError only when the join index payload reports source_bodies_exported.
    - Reads: receipts/code_lens/code_lens_join_index_v0.json, core/organ_atlas.json,
      core/component_public_synopses.json under ``root``.
    - Non-goal: never opens source files or docstring atoms.
    """
    base = root or default_root()
    join_index = _load_json(base / "receipts/code_lens/code_lens_join_index_v0.json")
    atlas = _load_json(base / "core/organ_atlas.json")
    synopses_doc = _load_json(base / "core/component_public_synopses.json")
    _membrane_guard(join_index)
    atlas_rows = (atlas or {}).get("organs") or []
    join_organs = ((join_index or {}).get("nodes") or {}).get("organ") or []
    synopses = (synopses_doc or {}).get("synopses") or {}
    return {
        "root": base,
        "join_index": join_index,
        "atlas": atlas,
        "synopses": synopses,
        "join_index_present": isinstance(join_index, dict),
        "atlas_by_organ": {
            str(r.get("organ_id")): r for r in atlas_rows if isinstance(r, dict)
        },
        "join_by_organ": {
            str(n.get("organ_id")): n for n in join_organs if isinstance(n, dict)
        },
        "synopsis_by_organ": {str(k): str(v) for k, v in synopses.items()},
    }


def _membrane_guard(join_index: Any) -> None:
    """Refuse to compile from a join index that leaked source bodies.

    - Teleology: enforce the presence_only membrane at the input boundary, mirroring
      the join-index builder's own leak refusal.
    - Guarantee: returns None when the snapshot is clean or absent.
    - Fails: ValueError when join_index.source_bodies_exported is truthy.
    - Reads: only the in-memory snapshot.
    """
    if isinstance(join_index, dict) and join_index.get("source_bodies_exported"):
        raise ValueError(
            "refusing to compose read packs from a join index that exports source bodies"
        )


def _pack_skeleton(mode: str, goal: str | None) -> dict[str, Any]:
    """Return the common read-pack envelope every mode fills in.

    - Teleology: guarantee one schema, membrane, and ceiling across all read packs.
    - Guarantee: returns a dict with schema_version, mode, goal, export_band,
      membrane, authority_ceiling, and empty selected_nodes/edges/refs/escalation lists.
    - Fails: never raises.
    """
    return {
        "schema_version": READ_PACK_SCHEMA,
        "mode": mode,
        "goal": goal,
        "export_band": "presence_only",
        "membrane": MEMBRANE_V0,
        "summary": {
            "what_this_is": "",
            "what_to_inspect_next": [],
            "what_not_to_trust": "",
        },
        "selected_nodes": [],
        "selected_edges": [],
        "evidence_refs": [],
        "receipt_refs": [],
        "specificity_risks": [],
        "source_span_escalation": [],
        "open_source_when": [
            "you must mutate the organ's owned code",
            "you must prove or reproduce a claim from source",
            "the read pack marks a needs_spot_review or unresolved ref",
        ],
        "authority_ceiling": dict(AUTHORITY_CEILING),
        "non_goals": [
            "not source-body export",
            "not a control-flow / data-flow graph",
            "not release approval",
            "not whole-system correctness",
        ],
    }


def _family_roster(atlas_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group atlas organ rows into a family roster with counts and members.

    - Teleology: give a cold agent the "what organs exist" map in one glance.
    - Guarantee: returns a list of {family, count, organs:[{organ_id, display_name,
      specialty}]} sorted by descending count then family name.
    - Fails: never raises; rows missing a family fall under "unspecified".
    - Reads: the in-memory atlas rows only.
    """
    families: dict[str, list[dict[str, Any]]] = {}
    for row in atlas_rows:
        family = str(row.get("family") or "unspecified")
        families.setdefault(family, []).append(
            {
                "organ_id": row.get("organ_id"),
                "display_name": row.get("display_name"),
                "specialty": row.get("specialty"),
            }
        )
    roster = [
        {"family": fam, "count": len(members), "organs": members}
        for fam, members in families.items()
    ]
    roster.sort(key=lambda entry: (-entry["count"], entry["family"]))
    return roster


def _evidence_distribution(join_organs: list[dict[str, Any]]) -> dict[str, int]:
    """Count organs per evidence_class from join-index organ nodes.

    - Teleology: surface how much of the substrate is validator vs projection vs
      macro-import, the core authority question.
    - Guarantee: returns evidence_class -> count, using "unspecified" for None.
    - Fails: never raises.
    - Reads: the in-memory organ nodes only.
    """
    dist: dict[str, int] = {}
    for node in join_organs:
        cls = str(node.get("evidence_class") or "unspecified")
        dist[cls] = dist.get(cls, 0) + 1
    return dict(sorted(dist.items(), key=lambda kv: (-kv[1], kv[0])))


def compile_first_contact(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compile the substrate-orientation read pack for a cold clone.

    - Teleology: answer "what is this substrate and where do I start?" from public
      metadata so the agent never has to grep the repo first.
    - Guarantee: returns a tutorial-mode pack whose summary states the organ/family
      counts and authority boundary, whose selected_nodes carry the family roster and
      evidence distribution, and whose what_not_to_trust is the atlas anti_claim.
    - Fails: never raises; absent atlas yields a degraded but valid pack.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: emits no source bodies and no per-symbol docstrings.
    """
    atlas = inputs.get("atlas") or {}
    atlas_rows = list(inputs.get("atlas_by_organ", {}).values())
    join_organs = list(inputs.get("join_by_organ", {}).values())
    roster = _family_roster(atlas_rows)
    pack = _pack_skeleton("tutorial", "understand this substrate")
    organ_count = len(atlas_rows) or len(join_organs)
    boundary = str(atlas.get("authority_boundary") or "")
    pack["summary"]["what_this_is"] = (
        f"Microcosm is a local-first, source-open substrate of {organ_count} runtime "
        f"organs across {len(roster)} families. Comprehend it through governed "
        "metadata -- glosses, evidence classes, receipts, and authority ceilings -- "
        "rather than by reading source. " + boundary
    ).strip()
    pack["summary"]["what_to_inspect_next"] = list(_START_HERE_ROUTES)
    pack["summary"]["what_not_to_trust"] = str(atlas.get("anti_claim") or "")
    pack["selected_nodes"] = [
        {"kind": "family_roster", "families": roster},
        {
            "kind": "evidence_distribution",
            "by_evidence_class": _evidence_distribution(join_organs),
        },
    ]
    pack["evidence_refs"] = [
        "core/organ_atlas.json",
        "core/component_public_synopses.json",
        "receipts/code_lens/code_lens_join_index_v0.json",
    ]
    pack["specificity_risks"] = [_substrate_specificity_note(join_organs)]
    if not inputs.get("join_index_present"):
        pack["summary"]["what_to_inspect_next"].append(
            "join index absent: run scripts/build_code_lens_join_index.py to enrich"
        )
    return pack


def _substrate_specificity_note(join_organs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize substrate-wide runner custody, the headline comprehension truth.

    - Teleology: tell a cold agent up front that most organ runners are exact-copy
      macro bodies, so organ comprehension must come from registry metadata.
    - Guarantee: returns {custody_split, runners_resolved, note} counted from the
      organ nodes' runner_custody_basis.
    - Fails: never raises.
    - Reads: the in-memory organ nodes only.
    """
    split: dict[str, int] = {}
    resolved = 0
    for node in join_organs:
        if node.get("runner_source_resolved"):
            resolved += 1
        basis = str(node.get("runner_custody_basis") or "unresolved")
        split[basis] = split.get(basis, 0) + 1
    return {
        "kind": "runner_custody",
        "custody_split": split,
        "runners_resolved": resolved,
        "note": (
            "Most organ runners are exact-copy macro bodies (directory_coupling_marker); "
            "comprehend them via registry metadata + receipts, not by reading the runner."
        ),
    }


def _resolved_refs(rows: Any, ref_key: str = "ref") -> list[str]:
    """Extract resolved reference strings from an atlas ref list.

    - Teleology: turn the atlas's {ref, resolution_status} rows into a flat ref list
      for the read pack's inspect-next surface.
    - Guarantee: returns the ref strings whose resolution_status is "resolved"; plain
      string rows pass through; non-list input yields [].
    - Fails: never raises.
    - Reads: only the supplied rows.
    """
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if isinstance(row, str):
            out.append(row)
        elif isinstance(row, dict):
            if row.get("resolution_status") in (None, "resolved"):
                ref = row.get(ref_key) or row.get("ref")
                if ref:
                    out.append(str(ref))
    return out


def _organ_edges(join_index: Any, organ_id: str) -> list[dict[str, Any]]:
    """Select the join-index edges originating from one organ.

    - Teleology: give the organ pack its implemented_by_runner / emits_receipt edges.
    - Guarantee: returns the edge dicts whose ``from`` equals organ_id; [] when none.
    - Fails: never raises.
    - Reads: the in-memory join index only.
    """
    edges = (join_index or {}).get("edges") or []
    return [e for e in edges if isinstance(e, dict) and e.get("from") == organ_id]


def compile_organ(inputs: dict[str, Any], organ_id: str) -> dict[str, Any]:
    """Compile the per-organ comprehension read pack.

    - Teleology: answer "what does this organ do, how do I run it, and what may I
      trust about it?" from the join index + atlas + synopsis, never the runner source.
    - Guarantee: returns an explanation-mode pack whose summary draws what_this_is from
      the synopsis + human_gloss, what_to_inspect_next from first_command + wires_to +
      resolved mechanism/concept refs, and what_not_to_trust from claim_ceiling_restated;
      selected_edges are the organ's join edges; source_span_escalation carries code_loci.
    - Fails: returns a not_found pack (mode reference) when the organ id is unknown.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never reads or returns runner source bodies or docstring atoms.
    """
    atlas_row = inputs.get("atlas_by_organ", {}).get(organ_id)
    join_node = inputs.get("join_by_organ", {}).get(organ_id)
    synopsis = inputs.get("synopsis_by_organ", {}).get(organ_id, "")
    if atlas_row is None and join_node is None:
        pack = _pack_skeleton("reference", f"comprehend organ {organ_id}")
        pack["summary"]["what_this_is"] = f"No organ named {organ_id!r} in the atlas or join index."
        pack["summary"]["what_to_inspect_next"] = ["microcosm comprehend --slice organs"]
        pack["organ_id"] = organ_id
        pack["found"] = False
        return pack
    atlas_row = atlas_row or {}
    join_node = join_node or {}
    pack = _pack_skeleton("explanation", f"comprehend organ {organ_id}")
    pack["organ_id"] = organ_id
    pack["found"] = True
    human = str(atlas_row.get("human_gloss") or "")
    pack["summary"]["what_this_is"] = (synopsis + (" " + human if human else "")).strip()
    inspect_next: list[str] = []
    first_command = atlas_row.get("first_command")
    if first_command:
        inspect_next.append(str(first_command))
    wires = atlas_row.get("wires_to") or []
    if isinstance(wires, list) and wires:
        inspect_next.append("wires_to: " + ", ".join(str(w) for w in wires[:8]))
    mechanisms = _resolved_refs(atlas_row.get("mechanism_refs"))
    if mechanisms:
        inspect_next.append("mechanisms: " + ", ".join(mechanisms[:6]))
    pack["summary"]["what_to_inspect_next"] = inspect_next
    pack["summary"]["what_not_to_trust"] = str(atlas_row.get("claim_ceiling_restated") or "")
    pack["selected_nodes"] = [
        {
            "kind": "organ",
            "organ_id": organ_id,
            "display_name": atlas_row.get("display_name"),
            "specialty": atlas_row.get("specialty"),
            "family": atlas_row.get("family"),
            "agent_gloss": atlas_row.get("agent_gloss"),
            "evidence_class": join_node.get("evidence_class") or atlas_row.get("evidence_class"),
            "claim_ceiling": join_node.get("claim_ceiling"),
            "status": join_node.get("status"),
            "standalone_or_wired": atlas_row.get("standalone_or_wired"),
            "runner_module": join_node.get("runner_module"),
            "runner_custody_basis": join_node.get("runner_custody_basis"),
            "authority_receipt": join_node.get("authority_receipt"),
        }
    ]
    pack["selected_edges"] = _organ_edges(inputs.get("join_index"), organ_id)
    pack["evidence_refs"] = _organ_concept_refs(atlas_row)
    pack["receipt_refs"] = [
        e.get("to") for e in pack["selected_edges"] if e.get("kind") == "emits_receipt"
    ]
    pack["specificity_risks"] = [_organ_specificity_risk(join_node)]
    pack["source_span_escalation"] = _organ_source_spans(atlas_row, join_node)
    return pack


def _organ_concept_refs(atlas_row: dict[str, Any]) -> list[str]:
    """Collect an organ's resolved concept / paper-module / axiom / principle refs.

    - Teleology: give the organ pack its doctrine evidence handles for drilldown.
    - Guarantee: returns a flat, de-duplicated list of resolved ref strings plus the
      paper_module_ref when present.
    - Fails: never raises.
    - Reads: only the supplied atlas row.
    """
    refs: list[str] = []
    for key in ("concept_refs", "axiom_refs", "principle_refs"):
        refs.extend(_resolved_refs(atlas_row.get(key)))
    pmr = atlas_row.get("paper_module_ref")
    if pmr:
        refs.append(str(pmr))
    seen: set[str] = set()
    return [r for r in refs if not (r in seen or seen.add(r))]


def _organ_specificity_risk(join_node: dict[str, Any]) -> dict[str, Any]:
    """Restate an organ's runner specificity + custody as a trust-risk note.

    - Teleology: tell the agent whether the organ's runner atoms are body-specific or
      whether the runner is an exact-copy macro body to be read only via metadata.
    - Guarantee: returns {runner_custody_basis, runner_specificity, note}; the note
      flags directory_coupling_marker runners as comprehend-via-metadata.
    - Fails: never raises.
    - Reads: only the supplied join node.
    """
    basis = join_node.get("runner_custody_basis")
    note = (
        "Runner is an exact-copy macro body; comprehend via registry metadata + "
        "receipts and do not treat runner source as owned."
        if basis == "directory_coupling_marker"
        else "Runner source is owned; specificity counts reflect its authored atoms."
    )
    return {
        "runner_custody_basis": basis,
        "runner_specificity": join_node.get("runner_specificity"),
        "note": note,
    }


def _organ_source_spans(
    atlas_row: dict[str, Any], join_node: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build the organ's source-span escalation pointers from atlas code_loci.

    - Teleology: hand the agent exact path+symbol pointers to open ONLY when it must
      mutate or prove, keeping the default pack source-body-free.
    - Guarantee: returns a list of {path, symbols} from code_loci plus the resolved
      runner_source_ref; symbol lists are truncated to 12 names; no bodies included.
    - Fails: never raises.
    - Reads: only the supplied atlas row and join node.
    """
    spans: list[dict[str, Any]] = []
    loci = atlas_row.get("code_loci") or []
    if isinstance(loci, list):
        for locus in loci:
            if isinstance(locus, dict) and locus.get("path"):
                syms = locus.get("symbols") or []
                spans.append(
                    {
                        "path": str(locus["path"]),
                        "symbols": [str(s) for s in syms][:12] if isinstance(syms, list) else [],
                    }
                )
    runner_ref = join_node.get("runner_source_ref")
    if runner_ref and not any(s["path"] == runner_ref for s in spans):
        spans.append({"path": str(runner_ref), "symbols": []})
    return spans


def compile_authority(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compile the authority/trust-boundary read pack.

    - Teleology: answer "what is authoritative vs projection, and what does passing
      NOT authorize?" -- the question a careful agent must resolve before acting.
    - Guarantee: returns a reference-mode pack carrying the evidence_class distribution,
      the per-organ claim ceilings, the global authority ceiling, the membrane bands,
      and the atlas authority_boundary + anti_claim.
    - Fails: never raises; absent inputs yield a degraded but valid pack.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never claims any release/source-export/whole-system authorization.
    """
    atlas = inputs.get("atlas") or {}
    join_organs = list(inputs.get("join_by_organ", {}).values())
    pack = _pack_skeleton("reference", "inspect the authority boundary")
    pack["summary"]["what_this_is"] = (
        "Authority map of the substrate: every organ carries an evidence class and a "
        "restated claim ceiling. Glosses and projections are navigation metadata, not "
        "source authority."
    )
    pack["summary"]["what_to_inspect_next"] = [
        "microcosm comprehend --organ <organ_id> for a single organ's ceiling",
        "core/organ_evidence_classes.json for evidence-class definitions",
    ]
    pack["summary"]["what_not_to_trust"] = str(atlas.get("anti_claim") or "")
    pack["selected_nodes"] = [
        {
            "kind": "evidence_distribution",
            "by_evidence_class": _evidence_distribution(join_organs),
        },
        {
            "kind": "claim_ceilings",
            "by_organ": [
                {
                    "organ_id": node.get("organ_id"),
                    "evidence_class": node.get("evidence_class"),
                    "claim_ceiling": node.get("claim_ceiling"),
                }
                for node in join_organs
            ],
        },
        {"kind": "authority_boundary", "text": atlas.get("authority_boundary")},
    ]
    pack["evidence_refs"] = ["core/organ_atlas.json", "core/organ_evidence_classes.json"]
    return pack


def compile_organs_index(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compile the organ roster read pack: one synopsis line per organ.

    - Teleology: give the agent the whole-category-at-a-glance roster so it can pick an
      organ to comprehend without scanning the registry.
    - Guarantee: returns a reference-mode pack whose selected_nodes list every organ's
      {organ_id, display_name, specialty, family, synopsis, evidence_class}.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    """
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    synopsis_by = inputs.get("synopsis_by_organ", {})
    organ_ids = sorted(set(atlas_by) | set(join_by))
    pack = _pack_skeleton("reference", "list all organs")
    pack["summary"]["what_this_is"] = f"{len(organ_ids)} organs, one synopsis line each."
    pack["summary"]["what_to_inspect_next"] = [
        "microcosm comprehend --organ <organ_id>",
    ]
    pack["selected_nodes"] = [
        {
            "kind": "organ_synopsis",
            "organ_id": oid,
            "display_name": (atlas_by.get(oid) or {}).get("display_name"),
            "specialty": (atlas_by.get(oid) or {}).get("specialty"),
            "family": (atlas_by.get(oid) or {}).get("family"),
            "evidence_class": (join_by.get(oid) or {}).get("evidence_class"),
            "synopsis": synopsis_by.get(oid, ""),
        }
        for oid in organ_ids
    ]
    return pack


def route_goal(goal: str, inputs: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """Route a freeform goal string to a comprehension packet mode + target.

    - Teleology: let a cold agent ask in words and still land on the right bounded
      packet -- the information-scent router behind --goal and the packet-route assay.
    - Guarantee: returns (mode, target, note); mode is a known packet mode; target is an
      organ id (organ/claim_trace/flow/mutation), a family (organ_cluster), or a path
      (path/mutation) when the goal names one; note is reserved for honest deferrals.
    - Fails: never raises; an empty/unknown goal routes to first-contact.
    - Reads: the in-memory inputs (organ id + family sets) only.
    - Non-goal: explicit CLI flags always override this fuzzy router.
    """
    text = (goal or "").lower()
    organ = next(
        (oid for oid in inputs.get("atlas_by_organ", {}) if oid.lower() in text), None
    )
    families = {str(r.get("family")) for r in inputs.get("atlas_by_organ", {}).values()}
    family = next(
        (f for f in families if f and (f in text or f.replace("_", " ") in text)), None
    )
    path = next(
        (tok for tok in text.split() if tok.endswith(".py") or "/" in tok), None
    )
    if any(w in text for w in ("patch", "change", "fix", "mutate", "edit", "modify", "refactor")):
        return "mutation_plan", organ or path, None
    if path:
        return "path", path, None
    if any(
        w in text
        for w in (
            "whole system", "whole microcosm", "everything", "self model", "self-model",
            "entire substrate", "operating picture", "all at once", "comprehend the whole",
            "comprehend all", "understand the whole", "comprehend everything",
        )
    ):
        return "self-model", None, None
    if any(w in text for w in ("math", "proof", "lean", "formal", "theorem", "mathlib")):
        return "math", None, None
    if any(w in text for w in ("claim", "prove", "proven", "receipt", "justif", "validate")):
        return "claim_trace", organ, None
    if any(w in text for w in ("flow", "how does", "pipeline", "execution", "run order")):
        return "flow", organ, None
    if any(w in text for w in ("cluster", "family", "subsystem", "group of", "category")):
        return "organ_cluster", family, None
    if any(w in text for w in ("authority", "trust", "ceiling", "allowed", "safe to")):
        return "authority", None, None
    if any(w in text for w in ("list", "roster", "inventory", "all organs", "what organs")):
        return "organs", None, None
    if any(w in text for w in ("atlas", "menu", "which packet", "what packets", "packets")):
        return "packet-atlas", None, None
    if organ:
        return "organ", organ, None
    return "first-contact", None, None


# --- atom_value_membrane_v1: bounded, custody-gated local excerpt extraction -------

def _atom_value(docstring: str, atom: str, vocab: tuple[str, ...]) -> str:
    """Extract ONE atom's bounded prose value from a docstring (local-band exporter).

    - Teleology: the sanctioned local exporter of a single authored atom's value, so
      a cold agent can read a symbol's Guarantee/Fails/Non-goal without opening source.
    - Guarantee: returns the stripped text following the first ``<atom>:`` line marker,
      joined across continuation lines up to the next atom marker or a blank line, then
      truncated to MAX_ATOM_CHARS with an ellipsis; "" when the atom is absent.
    - Fails: never raises (pure string scan).
    - Reads: only the supplied docstring.
    - Non-goal: never returns the whole docstring, the summary line, or source body;
      one bounded atom value only.
    """
    stop_markers = tuple(f"{a}:" for a in vocab)
    collected: list[str] = []
    capturing = False
    for raw in docstring.splitlines():
        stripped = raw.strip().lstrip("-*").strip()
        if not capturing:
            if stripped.startswith(f"{atom}:"):
                collected.append(stripped[len(atom) + 1:].strip())
                capturing = True
            continue
        if not stripped or any(stripped.startswith(m) for m in stop_markers):
            break
        collected.append(stripped)
    value = " ".join(part for part in collected if part).strip()
    if len(value) > MAX_ATOM_CHARS:
        value = value[: MAX_ATOM_CHARS - 1].rstrip() + "…"
    return value


def _excerpt_fingerprint(symbol_name: str, atom_values: dict[str, str]) -> str:
    """Return a 12-hex provenance fingerprint over a symbol's emitted atom values.

    - Teleology: stamp each excerpt row so it is a drilldown hint tied to its source,
      not free-floating authority.
    - Guarantee: returns the first 12 hex chars of a sha256 over name + sorted values.
    - Fails: never raises.
    """
    blob = symbol_name + "|" + json.dumps(atom_values, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def extract_atom_excerpts(root: Path | None, rel_path: str) -> dict[str, Any]:
    """Extract bounded, custody-gated atom-value excerpts from ONE owned source file.

    - Teleology: activate the local_semantic_excerpt band -- turn a file's authored
      docstring atoms into a bounded local read model so the comprehend route is
      powered by real code semantics, not just atlas metadata.
    - Guarantee: returns a microcosm_atom_value_excerpt_v1 dict; emits symbol rows
      (name, source_span_ref, fingerprint, bounded atom_values) ONLY when the path is
      under src/microcosm_core/ AND the manifest custody oracle reports it owned
      (_custody_basis is None); secret-shaped or private-home-path atom values are
      dropped and counted, never emitted; total bytes are capped at MAX_EXCERPT_PACK_BYTES.
    - Fails: returns eligible=False with a reason for non-owned/custody-bound/unreadable
      paths; never raises.
    - Reads: the manifest custody oracle + the owned source file's docstrings only.
    - Writes: nothing.
    - Non-goal: never exports source bodies, the summary line, custody-bound runners,
      example/fixture/generated source, or anything into the public presence_only cache.
    - Escalates-to: project_substrate._load_manifest_custody_paths / _custody_basis as
      the authoritative custody signal.
    """
    from . import project_substrate as ps

    base = root or default_root()
    rel = str(rel_path).strip().lstrip("./")
    result: dict[str, Any] = {
        "schema_version": LOCAL_EXCERPT_SCHEMA,
        "export_band": "local_semantic_excerpt",
        "path": rel,
        "eligible": False,
        "custody_basis": None,
        "symbols": [],
        "symbol_count": 0,
        "limits": {
            "max_atom_chars": MAX_ATOM_CHARS,
            "max_pack_bytes": MAX_EXCERPT_PACK_BYTES,
            "source_body_export_authorized": False,
        },
        "leak_guard": {"secret_shapes_dropped": 0, "private_paths_dropped": 0},
        "omitted_for_budget": 0,
        "authority_ceiling": dict(AUTHORITY_CEILING),
    }
    manifest_custody = ps._load_manifest_custody_paths(base)
    basis = ps._custody_basis(rel, manifest_custody)
    result["custody_basis"] = basis or "owned"
    if not rel.startswith(OWNED_EXCERPT_ROOT) or basis is not None:
        result["reason"] = (
            f"not owned-excerpt-eligible (custody_basis={basis or 'outside_owned_root'})"
        )
        return result
    try:
        source = (base / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, ValueError) as exc:
        result["reason"] = f"unreadable: {exc.__class__.__name__}"
        return result
    result["eligible"] = True
    vocab = ps.STD_PYTHON_CONTRACT_ATOMS
    total_bytes = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        doc = ast.get_docstring(node)
        if not doc:
            continue
        atom_values: dict[str, str] = {}
        for atom in ps._detect_docstring_atoms(doc):
            value = _atom_value(doc, atom, vocab)
            if not value:
                continue
            if _SECRET_SHAPE_RE.search(value):
                result["leak_guard"]["secret_shapes_dropped"] += 1
                continue
            if _PRIVATE_PATH_RE.search(value):
                result["leak_guard"]["private_paths_dropped"] += 1
                continue
            atom_values[atom] = value
        if not atom_values:
            continue
        row = {
            "symbol_name": node.name,
            "source_span_ref": f"{rel}:{node.lineno}",
            "fingerprint": _excerpt_fingerprint(node.name, atom_values),
            "atom_values": atom_values,
        }
        row_bytes = len(json.dumps(row, ensure_ascii=True))
        if total_bytes + row_bytes > MAX_EXCERPT_PACK_BYTES:
            result["omitted_for_budget"] += 1
            continue
        total_bytes += row_bytes
        result["symbols"].append(row)
    result["symbol_count"] = len(result["symbols"])
    return result


def compile_path_excerpts(root: Path | None, rel_path: str) -> dict[str, Any]:
    """Compile a local_semantic_excerpt read pack for one owned source file.

    - Teleology: the "read the code's self-description without opening the code"
      primitive -- surface an owned file's authored atoms as a bounded local read pack.
    - Guarantee: returns an explanation-mode pack with export_band=local_semantic_excerpt
      carrying semantic_excerpts (bounded atom values), a source-span escalation row, and
      an excerpt_guard; a non-eligible path yields found=False with the custody reason.
    - Fails: never raises.
    - Reads: extract_atom_excerpts for the file.
    - Non-goal: not a public-cache surface; this pack is local-only and never presence_only.
    """
    base = root or default_root()
    excerpts = extract_atom_excerpts(base, rel_path)
    rel = excerpts["path"]
    pack = _pack_skeleton("explanation", f"read the authored atoms of {rel}")
    pack["export_band"] = "local_semantic_excerpt"
    pack["intent_class"] = "reference"
    pack["path"] = rel
    if not excerpts["eligible"]:
        pack["found"] = False
        pack["summary"]["what_this_is"] = (
            f"{rel} is not owned-excerpt-eligible ({excerpts.get('reason')}); its atoms "
            "stay behind the membrane. Comprehend it via organ/registry metadata instead."
        )
        pack["summary"]["what_to_inspect_next"] = ["microcosm comprehend --slice organs"]
        pack["semantic_excerpts"] = []
        pack["excerpt_guard"] = {"custody_basis": excerpts["custody_basis"]}
        return pack
    pack["found"] = True
    count = excerpts["symbol_count"]
    pack["summary"]["what_this_is"] = (
        f"{count} authored symbols in {rel}, read as bounded atom-value excerpts "
        "(Teleology/Guarantee/Fails/...), no source bodies."
    )
    pack["summary"]["what_to_inspect_next"] = [
        f"open {rel} only to mutate or prove; the atoms are the read model"
    ]
    pack["summary"]["what_not_to_trust"] = (
        "Atom excerpts are the symbols' own authored claims -- bounded and local-only. "
        "They are not proof and not a release or authority signal."
    )
    pack["semantic_excerpts"] = excerpts["symbols"]
    pack["source_span_escalation"] = [
        {
            "path": rel,
            "symbols": [s["symbol_name"] for s in excerpts["symbols"]][:20],
        }
    ]
    pack["excerpt_guard"] = {
        **excerpts["leak_guard"],
        "omitted_for_budget": excerpts["omitted_for_budget"],
        "custody_basis": excerpts["custody_basis"],
    }
    return pack


def _attach_organ_excerpts(
    pack: dict[str, Any], root: Path | None, organ_id: str, inputs: dict[str, Any]
) -> dict[str, Any]:
    """Enrich an organ pack with owned-source atom excerpts from its code_loci.

    - Teleology: let an organ pack carry the authored atoms of its OWNED governing
      code, while honestly noting that custody-bound runners stay behind the membrane.
    - Guarantee: flips export_band to local_semantic_excerpt and adds semantic_excerpts
      (owned code_loci paths with atom values) plus excerpt_custody_notes (the loci that
      are custody-bound / non-owned and therefore not excerpted).
    - Fails: never raises; an organ with no owned loci yields empty excerpts + notes.
    - Reads: extract_atom_excerpts per code_loci path.
    - Non-goal: never excerpts a custody-bound or non-owned locus.
    """
    atlas_row = inputs.get("atlas_by_organ", {}).get(organ_id) or {}
    loci = atlas_row.get("code_loci") or []
    excerpts: list[dict[str, Any]] = []
    custody_notes: list[dict[str, Any]] = []
    for locus in loci if isinstance(loci, list) else []:
        if not isinstance(locus, dict) or not locus.get("path"):
            continue
        path = str(locus["path"])
        extracted = extract_atom_excerpts(root, path)
        if extracted["eligible"] and extracted["symbols"]:
            excerpts.append(
                {
                    "path": path,
                    "symbols": extracted["symbols"],
                    "guard": {
                        **extracted["leak_guard"],
                        "omitted_for_budget": extracted["omitted_for_budget"],
                    },
                }
            )
        else:
            custody_notes.append(
                {"path": path, "custody_basis": extracted["custody_basis"]}
            )
    pack["export_band"] = "local_semantic_excerpt"
    pack["semantic_excerpts"] = excerpts
    pack["excerpt_custody_notes"] = custody_notes
    return pack


# === comprehension_packet_atlas_v0 ================================================
# A comprehension packet is an attested, source-body-free OPERATING CONTEXT, not just a
# response: a named, byte-budgeted, atlas-linked read pack for one situation a cold
# agent actually enters. The packet atlas is the navigable menu over these packets.
# PACKET_SPECS below is the single source of truth -- the dispatcher, the atlas
# projection, and the packet-route assay all read it, so the menu can never advertise a
# packet that does not compile, and every next_packet scent link is checkable on disk.

# Compile-configuration byte bands (the "what size is each packet?" question). A spec
# names the band it targets; the compiler stamps actual bytes and a within/over verdict.
PACKET_BUDGETS: dict[str, dict[str, int]] = {
    "compact": {"target_bytes": 8000, "max_bytes": 16000},
    "standard": {"target_bytes": 24000, "max_bytes": 72000},
    "full_local": {"target_bytes": 150000, "max_bytes": 240000},
}

# The SQLite/FTS5 backend gate stays CLOSED while JSON + the read-pack cache meet every
# packet's SLO. It opens only on measured pressure, never on instinct.
SQLITE_GATE = (
    "closed: JSON read-pack cache meets SLO; build SQLite/FTS5 only when freeform goal "
    "routing or atom-excerpt search misses an SLO or needs ranked full-text search"
)

# The packet registry. packet_id is the public name; mode is the dispatch key; budget
# names a PACKET_BUDGETS band; next_packets are the information-scent links a reader
# follows (each must resolve to a packet_id -- the route assay enforces it).
PACKET_SPECS: list[dict[str, Any]] = [
    {
        "packet_id": "packet_atlas",
        "packet_kind": "reference",
        "mode": "packet-atlas",
        "when_needed": "cold clone, first move: which packet answers my question?",
        "command": "microcosm comprehend --packet-atlas",
        "inputs": ["packet_specs"],
        "export_band": "presence_only",
        "cache_policy": "prebuilt",
        "cache_ref": "receipts/code_lens/read_packs/packet_atlas.json",
        "budget": "compact",
        "slo_ms": 200,
        "data_status": "full",
        "next_packets": ["self_model", "first_contact", "authority", "organs_index"],
    },
    {
        "packet_id": "self_model",
        "packet_kind": "explanation",
        "mode": "self-model",
        "when_needed": "comprehend the WHOLE substrate at once: every family, what's real vs thin, what not to claim",
        "command": "microcosm comprehend --self-model",
        "inputs": ["join_index", "organ_atlas", "synopses"],
        "export_band": "presence_only",
        "cache_policy": "prebuilt",
        "cache_ref": "receipts/code_lens/read_packs/self_model.json",
        "budget": "standard",
        "slo_ms": 500,
        "data_status": "full",
        "next_packets": ["organs_index", "organ_cluster", "math", "authority", "mutation_plan"],
    },
    {
        "packet_id": "first_contact",
        "packet_kind": "explanation",
        "mode": "first-contact",
        "when_needed": "new clone: what is this substrate and where do I start?",
        "command": "microcosm comprehend --first-contact",
        "inputs": ["join_index", "organ_atlas", "synopses"],
        "export_band": "presence_only",
        "cache_policy": "prebuilt",
        "cache_ref": "receipts/code_lens/read_packs/first_contact.json",
        "budget": "standard",
        "slo_ms": 300,
        "data_status": "full",
        "next_packets": ["self_model", "authority", "organ_cluster", "organs_index", "mutation_plan"],
    },
    {
        "packet_id": "authority",
        "packet_kind": "reference",
        "mode": "authority",
        "when_needed": "before acting: what is authoritative vs projection, and what does passing NOT authorize?",
        "command": "microcosm comprehend --slice authority",
        "inputs": ["join_index", "organ_atlas"],
        "export_band": "presence_only",
        "cache_policy": "prebuilt",
        "cache_ref": "receipts/code_lens/read_packs/authority.json",
        "budget": "standard",
        "slo_ms": 300,
        "data_status": "full",
        "next_packets": ["organ", "claim_trace"],
    },
    {
        "packet_id": "organs_index",
        "packet_kind": "reference",
        "mode": "organs",
        "when_needed": "what organs exist? one synopsis line each",
        "command": "microcosm comprehend --slice organs",
        "inputs": ["join_index", "organ_atlas", "synopses"],
        "export_band": "presence_only",
        "cache_policy": "prebuilt",
        "cache_ref": "receipts/code_lens/read_packs/organs_index.json",
        "budget": "standard",
        "slo_ms": 300,
        "data_status": "full",
        "next_packets": ["organ", "organ_cluster"],
    },
    {
        "packet_id": "organ_cluster",
        "packet_kind": "explanation",
        "mode": "organ_cluster",
        "when_needed": "understand a whole family/subsystem at once (the middle doll)",
        "command": "microcosm comprehend --slice cluster --family <family>",
        "inputs": ["join_index", "organ_atlas", "synopses"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "standard",
        "slo_ms": 500,
        "data_status": "full",
        "next_packets": ["organ", "math", "claim_trace"],
    },
    {
        "packet_id": "organ",
        "packet_kind": "explanation",
        "mode": "organ",
        "when_needed": "understand one organ: purpose, first command, custody, ceiling",
        "command": "microcosm comprehend --organ <organ_id>",
        "inputs": ["join_index", "organ_atlas", "synopses"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "compact",
        "slo_ms": 200,
        "data_status": "full",
        "next_packets": ["claim_trace", "flow", "mutation_plan"],
    },
    {
        "packet_id": "math",
        "packet_kind": "explanation",
        "mode": "math",
        "when_needed": "where are the formal-math / proof surfaces and what do they claim?",
        "command": "microcosm comprehend --slice math",
        "inputs": ["join_index", "organ_atlas"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "standard",
        "slo_ms": 500,
        "data_status": "substantive_with_deferred_edges",
        "next_packets": ["organ", "claim_trace", "organ_cluster"],
    },
    {
        "packet_id": "claim_trace",
        "packet_kind": "proof_trace",
        "mode": "claim_trace",
        "when_needed": "how is a claim justified? claim -> validator -> receipt -> ceiling",
        "command": "microcosm comprehend --slice claims --organ <organ_id>",
        "inputs": ["join_index", "organ_atlas"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "compact",
        "slo_ms": 300,
        "data_status": "substantive_with_deferred_edges",
        "next_packets": ["flow", "organ", "authority"],
    },
    {
        "packet_id": "flow",
        "packet_kind": "proof_trace",
        "mode": "flow",
        "when_needed": "how does execution flow? validator -> runner -> receipt",
        "command": "microcosm comprehend --slice flows --organ <organ_id>",
        "inputs": ["join_index", "organ_atlas"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "compact",
        "slo_ms": 300,
        "data_status": "substantive_with_deferred_edges",
        "next_packets": ["claim_trace", "organ", "mutation_plan"],
    },
    {
        "packet_id": "mutation_plan",
        "packet_kind": "how_to",
        "mode": "mutation_plan",
        "when_needed": "I want to change something safely: what to inspect, test, refresh",
        "command": "microcosm comprehend --mutation <organ_id|path>",
        "inputs": ["join_index", "organ_atlas", "local_excerpts"],
        "export_band": "local_semantic_excerpt",
        "cache_policy": "local_on_demand",
        "cache_ref": None,
        "budget": "full_local",
        "slo_ms": 800,
        "data_status": "substantive_local",
        "next_packets": ["organ", "claim_trace", "path"],
    },
    {
        "packet_id": "path",
        "packet_kind": "reference",
        "mode": "path",
        "when_needed": "read a file's authored atom values without opening source",
        "command": "microcosm comprehend --path <owned_file>",
        "inputs": ["owned_source"],
        "export_band": "local_semantic_excerpt",
        "cache_policy": "local_on_demand",
        "cache_ref": None,
        "budget": "full_local",
        "slo_ms": 800,
        "data_status": "full",
        "next_packets": ["mutation_plan", "organ"],
    },
]

_SPEC_BY_MODE: dict[str, dict[str, Any]] = {s["mode"]: s for s in PACKET_SPECS}
_SPEC_BY_ID: dict[str, dict[str, Any]] = {s["packet_id"]: s for s in PACKET_SPECS}


def packet_spec_for_mode(mode: str) -> dict[str, Any] | None:
    """Return the packet spec whose dispatch mode is ``mode`` (or None).

    - Teleology: let comprehend stamp a compiled pack with its packet identity/budget.
    - Guarantee: returns the spec dict for a known dispatch mode, else None.
    - Fails: never raises.
    - Reads: the in-memory _SPEC_BY_MODE map only.
    """
    return _SPEC_BY_MODE.get(mode)


def _budget_for(spec: dict[str, Any]) -> dict[str, int]:
    """Resolve a spec's named budget band to {target_bytes, max_bytes}.

    - Teleology: turn the spec's symbolic budget band into concrete byte bounds.
    - Guarantee: returns the PACKET_BUDGETS entry, defaulting to the standard band.
    - Fails: never raises.
    - Reads: PACKET_BUDGETS only.
    """
    return PACKET_BUDGETS.get(str(spec.get("budget")), PACKET_BUDGETS["standard"])


def _stamp_packet_identity(pack: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Stamp a compiled pack with its packet identity, byte-budget verdict, and scent.

    - Teleology: make every compiled pack self-describe as an atlas packet -- its id,
      kind, measured bytes vs budget, and the next_packets a reader should follow.
    - Guarantee: adds packet_id, packet_kind, next_packets, and a budget block with
      band/target/max/actual bytes and within_budget; returns the same pack.
    - Fails: never raises.
    - Reads: the spec and the pack's own serialized size.
    - Writes: mutates the pack in place.
    - Non-goal: never alters the pack's export_band or authority ceiling.
    """
    budget = _budget_for(spec)
    actual = len(json.dumps(pack, ensure_ascii=True))
    pack["packet_id"] = spec["packet_id"]
    pack["packet_kind"] = spec["packet_kind"]
    pack["next_packets"] = list(spec.get("next_packets") or [])
    pack["budget"] = {
        "band": spec.get("budget"),
        "target_bytes": budget["target_bytes"],
        "max_bytes": budget["max_bytes"],
        "actual_bytes": actual,
        "within_budget": actual <= budget["max_bytes"],
    }
    return pack


def _shared_refs(rows: list[dict[str, Any]], key: str) -> list[str]:
    """Collect the distinct resolved refs of ``key`` across organ rows, by frequency.

    - Teleology: surface the doctrine a family/cluster shares so its pack shows a spine.
    - Guarantee: returns resolved ref strings sorted by descending occurrence then name;
      handles list-valued fields (mechanism_refs) and scalar fields (paper_module_ref).
    - Fails: never raises.
    - Reads: only the supplied rows.
    """
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if isinstance(value, list):
            refs = _resolved_refs(value)
        elif value:
            refs = [str(value)]
        else:
            refs = []
        for ref in refs:
            counts[ref] = counts.get(ref, 0) + 1
    return [r for r, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def compile_packet_atlas(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compile the navigable packet menu -- the cold-agent first move.

    - Teleology: answer "which packet answers my question?" by projecting the packet
      registry into a presence_only menu with byte budgets, cache state, and scent links.
    - Guarantee: returns a PACKET_ATLAS_SCHEMA pack whose selected_nodes list every
      PACKET_SPEC's {packet_id, packet_kind, when_needed, command, export_band,
      cache_policy, budget band+bytes, slo_ms, data_status, next_packets}; carries
      default_entry, the per-packet SLO table, and the (closed) SQLite gate; a cached
      packet reports its real on-disk byte size.
    - Fails: never raises; a missing cache file simply omits cached_bytes.
    - Reads: PACKET_SPECS and any prebuilt cache files under the resolved root.
    - Non-goal: never compiles or inlines the packets themselves (it is the index).
    """
    root = inputs.get("root") or default_root()
    pack = _pack_skeleton("reference", "which comprehension packet should I use?")
    pack["schema_version"] = PACKET_ATLAS_SCHEMA
    pack["summary"]["what_this_is"] = (
        f"{len(PACKET_SPECS)} comprehension packets. Each is a bounded, source-body-free "
        "operating context for one situation. Enter through first_contact, or pick the "
        "packet that matches your goal."
    )
    pack["summary"]["what_to_inspect_next"] = [s["command"] for s in PACKET_SPECS[:5]]
    pack["summary"]["what_not_to_trust"] = (
        "A packet is a navigation read model, never release/source-export/correctness "
        "authority; local_semantic_excerpt packets are local-only and never cached."
    )
    rows: list[dict[str, Any]] = []
    for spec in PACKET_SPECS:
        budget = _budget_for(spec)
        row = {
            "kind": "packet",
            "packet_id": spec["packet_id"],
            "packet_kind": spec["packet_kind"],
            "when_needed": spec["when_needed"],
            "command": spec["command"],
            "export_band": spec["export_band"],
            "cache_policy": spec["cache_policy"],
            "budget_band": spec["budget"],
            "target_bytes": budget["target_bytes"],
            "max_bytes": budget["max_bytes"],
            "slo_ms": spec["slo_ms"],
            "data_status": spec["data_status"],
            "next_packets": list(spec.get("next_packets") or []),
        }
        cache_ref = spec.get("cache_ref")
        if cache_ref:
            row["cache_ref"] = cache_ref
            cached = root / cache_ref
            if cached.exists():
                row["cached_bytes"] = len(cached.read_text())
        rows.append(row)
    pack["selected_nodes"] = rows
    pack["default_entry"] = "first_contact"
    pack["slo_ms_by_packet"] = {s["packet_id"]: s["slo_ms"] for s in PACKET_SPECS}
    pack["sqlite_gate"] = SQLITE_GATE
    pack["evidence_refs"] = ["src/microcosm_core/comprehension.py#PACKET_SPECS"]
    return pack


def compile_organ_cluster(inputs: dict[str, Any], family: str) -> dict[str, Any]:
    """Compile the family/subsystem read pack -- the whole-family-at-once middle doll.

    - Teleology: answer "what is this subsystem and which organs compose it?" so an
      agent can grasp a family before drilling into one organ.
    - Guarantee: returns an explanation pack for the named family with member organs
      (id, display_name, specialty, evidence_class, synopsis), the shared mechanism/
      concept/paper refs, and the evidence-class distribution; returns a chooser pack
      (found False) listing all families when family is blank or unknown.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never reads runner source or docstring atoms.
    """
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    synopsis_by = inputs.get("synopsis_by_organ", {})
    roster = _family_roster(list(atlas_by.values()))
    known = {entry["family"] for entry in roster}
    if not family or family not in known:
        pack = _pack_skeleton("reference", "choose an organ family")
        pack["found"] = False
        pack["summary"]["what_this_is"] = f"Name a family. {len(known)} exist."
        pack["summary"]["what_to_inspect_next"] = [
            f"microcosm comprehend --slice cluster --family {entry['family']}"
            for entry in roster
        ]
        pack["selected_nodes"] = roster
        return pack
    members = sorted(
        oid for oid, r in atlas_by.items() if str(r.get("family")) == family
    )
    pack = _pack_skeleton("explanation", f"comprehend the {family} family")
    pack["found"] = True
    pack["family"] = family
    pack["summary"]["what_this_is"] = (
        f"The {family} family: {len(members)} organs sharing a specialty."
    )
    pack["summary"]["what_to_inspect_next"] = [
        f"microcosm comprehend --organ {m}" for m in members[:6]
    ]
    pack["summary"]["what_not_to_trust"] = (
        "Family grouping is navigation metadata; each organ carries its own claim ceiling."
    )
    pack["selected_nodes"] = [
        {
            "kind": "organ",
            "organ_id": m,
            "display_name": (atlas_by.get(m) or {}).get("display_name"),
            "specialty": (atlas_by.get(m) or {}).get("specialty"),
            "evidence_class": (join_by.get(m) or {}).get("evidence_class"),
            "synopsis": synopsis_by.get(m, ""),
        }
        for m in members
    ]
    member_rows = [atlas_by.get(m) or {} for m in members]
    pack["shared_refs"] = {
        "mechanisms": _shared_refs(member_rows, "mechanism_refs"),
        "concepts": _shared_refs(member_rows, "concept_refs"),
        "paper_modules": _shared_refs(member_rows, "paper_module_ref"),
    }
    pack["selected_nodes"].append(
        {
            "kind": "evidence_distribution",
            "by_evidence_class": _evidence_distribution(
                [join_by.get(m) or {} for m in members]
            ),
        }
    )
    return pack


def compile_math(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compile the formal-math / proof surfaces read pack.

    - Teleology: answer "where is the mathematics/proof and what does it claim?" by
      gathering the formal_math_and_proof organs with their proof evidence and ceilings.
    - Guarantee: returns an explanation pack listing each proof-family organ's
      {organ_id, display_name, claim_ceiling, validator_command, paper_module_ref,
      evidence_class, receipt_count}, the shared proof mechanisms, and a deferred_edges
      block naming the proof-internal structure (theorem->lemma) still behind v1.
    - Fails: never raises; degrades to an empty member list if the family is absent.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never runs Lean, opens proof bodies, or asserts domain correctness.
    """
    family = "formal_math_and_proof"
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    members = sorted(
        oid for oid, r in atlas_by.items() if str(r.get("family")) == family
    )
    pack = _pack_skeleton("explanation", "where are the math/proof surfaces?")
    pack["family"] = family
    pack["summary"]["what_this_is"] = (
        f"{len(members)} formal-math / proof organs. Each records diagnostics or gates "
        "over proof evidence; none runs Lean or asserts domain correctness here."
    )
    pack["summary"]["what_to_inspect_next"] = [
        f"microcosm comprehend --slice claims --organ {m}" for m in members[:4]
    ]
    pack["summary"]["what_not_to_trust"] = (
        "Passing a proof-evidence gate is projection mechanics, not proof of any theorem."
    )
    pack["selected_nodes"] = [
        {
            "kind": "proof_organ",
            "organ_id": m,
            "display_name": (atlas_by.get(m) or {}).get("display_name"),
            "claim_ceiling": (join_by.get(m) or {}).get("claim_ceiling"),
            "validator_command": (join_by.get(m) or {}).get("validator_command"),
            "paper_module_ref": (atlas_by.get(m) or {}).get("paper_module_ref"),
            "evidence_class": (join_by.get(m) or {}).get("evidence_class"),
            "receipt_count": (join_by.get(m) or {}).get("receipt_count"),
        }
        for m in members
    ]
    member_rows = [atlas_by.get(m) or {} for m in members]
    pack["shared_refs"] = {
        "mechanisms": _shared_refs(member_rows, "mechanism_refs"),
        "paper_modules": _shared_refs(member_rows, "paper_module_ref"),
    }
    pack["deferred_edges"] = [
        {
            "edge_class": "proof_internal_structure",
            "missing": "theorem -> lemma -> tactic edges inside a proof organ",
            "would_come_from": "a Lean-aware proof-graph builder (join-index v2)",
            "next_packet": "claim_trace",
        }
    ]
    return pack


def compile_claim_trace(inputs: dict[str, Any], target: str) -> dict[str, Any]:
    """Compile the claim-justification trace for one organ: claim -> validator -> receipt.

    - Teleology: answer "how is this organ's public claim justified, and what bounds it?"
      by chaining its claim ceiling to the validator command and the receipts it emits.
    - Guarantee: returns a proof_trace pack for ``target`` with the claim ceiling (atlas
      restated + join), the validator_command that re-establishes it, the
      authority_receipt, the emits_receipt edges, and evidence_class; carries a
      deferred_edges block for the first-class claim-node ontology still behind v1.
    - Fails: returns a chooser pack (found False) listing organs by ceiling when target
      is blank/unknown.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never opens validator source or receipt bodies; pointers only.
    """
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    if not target or (target not in atlas_by and target not in join_by):
        pack = _pack_skeleton("reference", "choose an organ to trace")
        pack["found"] = False
        pack["summary"]["what_this_is"] = (
            "Name an organ to trace its claim -> validator -> receipt."
        )
        pack["summary"]["what_to_inspect_next"] = ["microcosm comprehend --slice organs"]
        pack["selected_nodes"] = [
            {"organ_id": oid, "claim_ceiling": (join_by.get(oid) or {}).get("claim_ceiling")}
            for oid in sorted(set(atlas_by) | set(join_by))[:20]
        ]
        return pack
    atlas_row = atlas_by.get(target) or {}
    join_node = join_by.get(target) or {}
    pack = _pack_skeleton("proof_trace", f"trace the claim for {target}")
    pack["found"] = True
    pack["organ_id"] = target
    pack["summary"]["what_this_is"] = (
        f"Claim trace for {target}: what it claims, how to re-establish it, what bounds it."
    )
    pack["summary"]["what_to_inspect_next"] = [
        str(join_node.get("validator_command") or "")
    ]
    pack["summary"]["what_not_to_trust"] = str(atlas_row.get("claim_ceiling_restated") or "")
    pack["selected_nodes"] = [
        {
            "kind": "claim",
            "organ_id": target,
            "claim_ceiling": join_node.get("claim_ceiling"),
            "claim_ceiling_restated": atlas_row.get("claim_ceiling_restated"),
            "evidence_class": join_node.get("evidence_class"),
            "evidence_strength_rank": join_node.get("evidence_strength_rank"),
            "truth_accounting_bucket": join_node.get("truth_accounting_bucket"),
        },
        {
            "kind": "validator",
            "validator_command": join_node.get("validator_command"),
            "note": "run this to re-establish the claim; it does not authorize release",
        },
    ]
    pack["selected_edges"] = _organ_edges(inputs.get("join_index"), target)
    receipts = [
        e.get("to") for e in pack["selected_edges"] if e.get("kind") == "emits_receipt"
    ]
    if join_node.get("authority_receipt"):
        receipts.insert(0, join_node.get("authority_receipt"))
    pack["receipt_refs"] = receipts
    pack["source_span_escalation"] = _organ_source_spans(atlas_row, join_node)
    pack["deferred_edges"] = [
        {
            "edge_class": "claim_node_ontology",
            "missing": "a first-class claim node distinct from the per-organ ceiling",
            "would_come_from": "join-index v2 claim extraction",
            "next_packet": "flow",
        }
    ]
    return pack


def compile_flow(inputs: dict[str, Any], target: str) -> dict[str, Any]:
    """Compile the execution-flow trace for one organ: validator -> runner -> receipt.

    - Teleology: answer "how does this organ run and what does it leave behind?" by
      ordering its validator command, runner module, and emitted receipts.
    - Guarantee: returns a proof_trace pack for ``target`` whose selected_nodes are the
      ordered flow stages (validator -> runner/custody -> receipts) and whose
      deferred_edges names the cross-organ ROUTE topology still behind v1.
    - Fails: returns a chooser pack (found False) when target is blank/unknown.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never opens runner source; it orders pointers, not bodies.
    """
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    if not target or (target not in atlas_by and target not in join_by):
        pack = _pack_skeleton("reference", "choose an organ flow")
        pack["found"] = False
        pack["summary"]["what_this_is"] = (
            "Name an organ to order its validator -> runner -> receipt flow."
        )
        pack["summary"]["what_to_inspect_next"] = ["microcosm comprehend --slice organs"]
        pack["selected_nodes"] = [
            {"organ_id": oid} for oid in sorted(set(atlas_by) | set(join_by))[:20]
        ]
        return pack
    atlas_row = atlas_by.get(target) or {}
    join_node = join_by.get(target) or {}
    edges = _organ_edges(inputs.get("join_index"), target)
    receipts = [e.get("to") for e in edges if e.get("kind") == "emits_receipt"]
    pack = _pack_skeleton("proof_trace", f"trace the flow for {target}")
    pack["found"] = True
    pack["organ_id"] = target
    pack["summary"]["what_this_is"] = (
        f"Execution flow for {target}: run the validator, it exercises the runner, which "
        f"emits {len(receipts)} receipt(s)."
    )
    pack["summary"]["what_to_inspect_next"] = [str(join_node.get("validator_command") or "")]
    pack["summary"]["what_not_to_trust"] = str(atlas_row.get("claim_ceiling_restated") or "")
    pack["selected_nodes"] = [
        {
            "kind": "flow_stage",
            "stage": 1,
            "role": "validator",
            "command": join_node.get("validator_command"),
        },
        {
            "kind": "flow_stage",
            "stage": 2,
            "role": "runner",
            "runner_module": join_node.get("runner_module"),
            "runner_source_ref": join_node.get("runner_source_ref"),
            "runner_custody_basis": join_node.get("runner_custody_basis"),
        },
        {"kind": "flow_stage", "stage": 3, "role": "receipts", "receipts": receipts},
    ]
    pack["selected_edges"] = edges
    pack["receipt_refs"] = receipts
    pack["source_span_escalation"] = _organ_source_spans(atlas_row, join_node)
    pack["deferred_edges"] = [
        {
            "edge_class": "cross_organ_route_topology",
            "missing": "a route node fanning one entry point across multiple organs",
            "would_come_from": "join-index v2 route extraction",
            "next_packet": "claim_trace",
        }
    ]
    return pack


def compile_mutation_plan(
    inputs: dict[str, Any], root: Path | None, target: str
) -> dict[str, Any]:
    """Compile the safe-mutation plan for an organ or owned path (local band).

    - Teleology: answer "I want to change this safely -- what do I inspect, test, and
      refresh, and what must I not touch?" before editing.
    - Guarantee: returns a how_to pack (export_band local_semantic_excerpt) with the
      code_loci to open, owned atom excerpts for owned loci, the validator_command to
      run after editing, the receipts to refresh, and custody/authority warnings;
      resolves ``target`` as a source path (has / or .py) or an organ id.
    - Fails: returns a chooser pack (found False) when target is blank/unknown.
    - Reads: the inputs bundle plus extract_atom_excerpts on owned loci.
    - Writes: nothing.
    - Non-goal: never excerpts a custody-bound runner; never authorizes the change.
    """
    base = root or default_root()
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    if target and (target.endswith(".py") or "/" in target):
        pack = _pack_skeleton("how_to", f"plan a mutation to {target}")
        pack["found"] = True
        pack["target"] = target
        pack["export_band"] = "local_semantic_excerpt"
        extracted = extract_atom_excerpts(base, target)
        pack["summary"]["what_this_is"] = f"Mutation plan for the file {target}."
        pack["summary"]["what_to_inspect_next"] = [target]
        pack["summary"]["what_not_to_trust"] = (
            "A read pack does not authorize the change; run the owning organ's validator "
            "and refresh its receipts after editing."
        )
        if extracted["eligible"] and extracted["symbols"]:
            pack["semantic_excerpts"] = [
                {
                    "path": target,
                    "symbols": extracted["symbols"],
                    "guard": {
                        **extracted["leak_guard"],
                        "omitted_for_budget": extracted["omitted_for_budget"],
                    },
                }
            ]
        else:
            pack["excerpt_custody_notes"] = [
                {"path": target, "custody_basis": extracted["custody_basis"]}
            ]
        pack["source_span_escalation"] = [{"path": target, "symbols": []}]
        return pack
    if not target or (target not in atlas_by and target not in join_by):
        pack = _pack_skeleton("reference", "choose a mutation target")
        pack["found"] = False
        pack["summary"]["what_this_is"] = (
            "Name an organ id or an owned source path to plan a safe change."
        )
        pack["summary"]["what_to_inspect_next"] = ["microcosm comprehend --slice organs"]
        return pack
    atlas_row = atlas_by.get(target) or {}
    join_node = join_by.get(target) or {}
    pack = _pack_skeleton("how_to", f"plan a mutation to organ {target}")
    pack["found"] = True
    pack["organ_id"] = target
    pack["export_band"] = "local_semantic_excerpt"
    pack["summary"]["what_this_is"] = f"Safe-mutation plan for organ {target}."
    pack["summary"]["what_not_to_trust"] = str(atlas_row.get("claim_ceiling_restated") or "")
    inspect = [f"validator (run after editing): {join_node.get('validator_command')}"]
    if join_node.get("runner_custody_basis") == "directory_coupling_marker":
        inspect.append(
            "WARNING: the runner is an exact-copy macro body -- do NOT edit the runner; "
            "change the source module it imports, then refresh the copy."
        )
    pack["summary"]["what_to_inspect_next"] = inspect
    _attach_organ_excerpts(pack, base, target, inputs)
    edges = _organ_edges(inputs.get("join_index"), target)
    pack["receipt_refs"] = [e.get("to") for e in edges if e.get("kind") == "emits_receipt"]
    pack["source_span_escalation"] = _organ_source_spans(atlas_row, join_node)
    pack["mutation_steps"] = [
        "open the source_span_escalation paths below (owned loci only)",
        f"run the validator: {join_node.get('validator_command')}",
        "refresh the receipts the organ emits (receipt_refs)",
    ]
    pack["warnings"] = [
        "this plan is local-only and is never cached into the committed presence_only cache",
        "editing does not bypass the authority ceiling; validation + receipts are required",
    ]
    return pack


# === whole_system_self_model_v0 ===================================================
# The self-model is the ENTIRE substrate compiled into one budgeted, source-body-free
# packet a cold agent can read in a single context window -- so it comprehends the whole
# Microcosm at once instead of judging it from whichever slice it happened to open. It
# is deliberately calibrated, not promotional: the most load-bearing fields are
# what_not_to_claim and thin_or_projection_surfaces, so quality is INFERRED from honest
# self-understanding rather than asserted. Front anchor (read_me_first) + section index +
# tail_recap mitigate the "lost in the middle" long-context failure mode.
_SELF_MODEL_PROFILES = ("operating_picture", "whole_substrate_map", "public_reader")

# The genuinely-missing edges, surfaced honestly in every self-model (not faked).
_ALL_DEFERRED_EDGES = [
    {"edge_class": "proof_internal_structure",
     "missing": "theorem -> lemma -> tactic edges inside a proof organ",
     "would_come_from": "join-index v2 Lean-aware proof-graph builder"},
    {"edge_class": "cross_organ_route_topology",
     "missing": "a route node fanning one entry point across multiple organs",
     "would_come_from": "join-index v2 route extraction"},
    {"edge_class": "claim_node_ontology",
     "missing": "a first-class claim node distinct from the per-organ ceiling",
     "would_come_from": "join-index v2 claim extraction"},
]


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    """Count rows by a string field, returned high-to-low (shared distribution helper).

    - Teleology: the one counter behind the self-model's calibration rollup so evidence
      class / truth-accounting / strength distributions all read the same way.
    - Guarantee: returns {value: count} sorted by descending count then value; a missing
      field becomes "unspecified".
    - Fails: never raises.
    - Reads: only the supplied rows.
    """
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unspecified")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _whole_substrate_rows(
    families: list[dict[str, Any]],
    atlas_by: dict[str, Any],
    join_by: dict[str, Any],
    synopsis_by: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build the per-organ essence roster grouped by family (the comprehend-all payload).

    - Teleology: let a cold agent read EVERY organ's essence + calibration in one pass --
      the literal "comprehend all 82 organs at once" body.
    - Guarantee: returns a list of {family, organ_count, organs:[{organ_id, essence,
      evidence_class, evidence_strength_rank, truth_accounting_bucket, claim_ceiling,
      first_command}]}; essence draws from the public synopsis then human gloss.
    - Fails: never raises.
    - Reads: only the supplied in-memory maps.
    - Non-goal: never reads runner source or docstring atoms.
    """
    out: list[dict[str, Any]] = []
    for entry in families:
        rows: list[dict[str, Any]] = []
        for organ_id in sorted(o["organ_id"] for o in entry["organs"]):
            atlas_row = atlas_by.get(organ_id) or {}
            join_node = join_by.get(organ_id) or {}
            rows.append(
                {
                    "organ_id": organ_id,
                    "essence": synopsis_by.get(organ_id, "") or atlas_row.get("human_gloss", ""),
                    "evidence_class": join_node.get("evidence_class"),
                    "evidence_strength_rank": join_node.get("evidence_strength_rank"),
                    "truth_accounting_bucket": join_node.get("truth_accounting_bucket"),
                    "claim_ceiling": join_node.get("claim_ceiling"),
                    "first_command": atlas_row.get("first_command"),
                }
            )
        out.append({"family": entry["family"], "organ_count": len(rows), "organs": rows})
    return out


def _public_reader_block(
    health: dict[str, Any], atlas: dict[str, Any]
) -> dict[str, Any]:
    """Compile the public-safe, calibrated reader block (NOT a marketing summary).

    - Teleology: let a skeptical external reader see what the system demonstrates, what it
      explicitly does NOT, and where the known thinness is -- quality inferred from honesty.
    - Guarantee: returns {what_it_demonstrates, what_it_does_not_demonstrate,
      known_thinness, recommended_demo_path}; no house jargon, no release/correctness claim.
    - Fails: never raises.
    - Reads: only the supplied health rollup + atlas.
    - Non-goal: never asserts impressiveness, release, or domain correctness.
    """
    macro_runners = (health.get("runner_custody_split") or {}).get("directory_coupling_marker", 0)
    return {
        "what_it_demonstrates": [
            "A substrate that compiles a source-body-free, calibrated self-model a cold agent reads in one context window.",
            "Per-organ authority ceilings + validator commands + receipts: every claim names how it is checked and what it does not authorize.",
            "An anti-overclaim membrane: comprehension never exports source bodies or grants release / correctness.",
        ],
        "what_it_does_not_demonstrate": [
            "Deep domain correctness: it does not run Lean or assert any theorem here.",
            f"Owned-code depth across all organs: {macro_runners} of {health.get('organ_count')} runners are exact-copy macro bodies.",
            "Production readiness, provider calls, or financial / safety advice.",
        ],
        "known_thinness": health.get("by_truth_accounting_bucket"),
        "recommended_demo_path": [
            "microcosm comprehend --self-model",
            "microcosm comprehend --slice math",
            "microcosm comprehend --slice claims --organ <a proof organ>",
            "microcosm comprehension-assay --whole-system",
        ],
    }


def compile_self_model(inputs: dict[str, Any], profile: str = "operating_picture") -> dict[str, Any]:
    """Compile the whole-Microcosm self-model: the entire substrate in one budgeted packet.

    - Teleology: let a cold agent comprehend the WHOLE substrate at once -- every family,
      what is real vs thin, what must not be claimed, and where to drill down -- instead of
      judging Microcosm from whichever slice it opened.
    - Guarantee: returns a SELF_MODEL_SCHEMA pack with a front anchor (read_me_first), a
      section index, major_subsystems (families), code_lens_health (evidence/truth-
      accounting/strength/custody rollups), authority_membrane, thin_or_projection_surfaces
      (skepticism made navigable), deferred_edges, recommended_drilldowns (the hub routing
      to the specialized packets), and a tail_recap; profile whole_substrate_map adds the
      per-organ essence roster, public_reader adds the calibrated external-reader block.
    - Fails: never raises; an unknown profile falls back to operating_picture.
    - Reads: the in-memory inputs bundle only (atlas + join index + synopses).
    - Non-goal: never exports source bodies, asserts impressiveness, or grants release.
    """
    profile = profile if profile in _SELF_MODEL_PROFILES else "operating_picture"
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    synopsis_by = inputs.get("synopsis_by_organ", {})
    atlas = inputs.get("atlas") or {}
    join_organs = list(join_by.values())
    rollup = ((inputs.get("join_index") or {}).get("rollup")) or {}
    families = _family_roster(list(atlas_by.values()))
    organ_count = len(atlas_by) or rollup.get("organ_count") or 0
    custody_split = rollup.get("runner_custody_split") or _count_by(join_organs, "runner_custody_basis")
    health = {
        "organ_count": organ_count,
        "edge_count": rollup.get("edge_count"),
        "by_evidence_class": _count_by(join_organs, "evidence_class"),
        "by_truth_accounting_bucket": _count_by(join_organs, "truth_accounting_bucket"),
        "by_evidence_strength_rank": _count_by(join_organs, "evidence_strength_rank"),
        "runner_custody_split": custody_split,
        "synopsis_coverage": len(synopsis_by),
    }
    exact_copy = custody_split.get("directory_coupling_marker", 0)

    pack = _pack_skeleton("explanation", "comprehend the whole Microcosm")
    pack["schema_version"] = SELF_MODEL_SCHEMA
    pack["context_profile"] = profile
    pack["target_reader"] = "cold Type A / cold codebase reader"
    # FRONT ANCHOR -- the strongest, load-bearing facts first (lost-in-the-middle guard).
    pack["read_me_first"] = [
        f"Microcosm is a {organ_count}-organ self-describing substrate; each organ is a bounded "
        "capability with a runner, a validator command, an authority ceiling, and emitted receipts.",
        f"Custody truth: {exact_copy}/{organ_count} organ runners are EXACT-COPY macro bodies -- "
        "comprehend them via registry metadata + receipts, not runner source.",
        "Every read here is source-body-free (presence_only); nothing in this packet authorizes "
        "release, source export, or whole-system correctness.",
        f"{len(families)} organ families. This packet IS the hub: open --slice cluster --family <f> "
        "for one family, --organ <id> for one organ, --slice math/claims/flows for proof/claim/flow.",
    ]
    pack["summary"]["what_this_is"] = (
        str(atlas.get("authority_boundary") or "A self-describing organ substrate.")
    )
    pack["summary"]["what_to_inspect_next"] = ["microcosm comprehend --slice organs"]
    pack["summary"]["what_not_to_trust"] = str(atlas.get("anti_claim") or "")
    pack["sections"] = [
        "read_me_first", "major_subsystems", "code_lens_health", "authority_membrane",
        "thin_or_projection_surfaces", "deferred_edges", "recommended_drilldowns", "tail_recap",
    ]
    pack["major_subsystems"] = [
        {
            "family": entry["family"],
            "organ_count": entry["count"],
            "drilldown": f"microcosm comprehend --slice cluster --family {entry['family']}",
        }
        for entry in families
    ]
    pack["code_lens_health"] = health
    pack["authority_membrane"] = {
        "bands": MEMBRANE_V0["bands"],
        "authority_ceiling": dict(AUTHORITY_CEILING),
        "boundary": atlas.get("authority_boundary"),
        "anti_claim": atlas.get("anti_claim"),
    }
    # THINNESS MADE NAVIGABLE -- where a skeptic should be skeptical, and how to probe it.
    pack["thin_or_projection_surfaces"] = {
        "note": "Where to be skeptical: these are projection / import surfaces, not deep domain capability.",
        "exact_copy_macro_runners": exact_copy,
        "copied_non_secret_macro_body_organs": health["by_truth_accounting_bucket"].get(
            "copied_non_secret_macro_body", 0
        ),
        "projection_or_import_evidence_classes": {
            k: v for k, v in health["by_evidence_class"].items()
            if "projection" in k or "import" in k
        },
        "how_to_probe": "For any organ run --slice claims --organ <id> to see its validator_command + "
        "receipts; an algorithmic_projection organ asserts projection mechanics only, not domain truth.",
    }
    pack["deferred_edges"] = _ALL_DEFERRED_EDGES
    # The self-model is the HUB: it routes to the specialized packets rather than duplicating them.
    pack["recommended_drilldowns"] = [
        {"question": "what organs exist (one line each)?", "packet": "organs_index",
         "command": "microcosm comprehend --slice organs"},
        {"question": "understand a whole family?", "packet": "organ_cluster",
         "command": "microcosm comprehend --slice cluster --family <f>"},
        {"question": "where is the math / proof?", "packet": "math",
         "command": "microcosm comprehend --slice math"},
        {"question": "what may I trust?", "packet": "authority",
         "command": "microcosm comprehend --slice authority"},
        {"question": "how is a claim justified?", "packet": "claim_trace",
         "command": "microcosm comprehend --slice claims --organ <id>"},
        {"question": "how does an organ run?", "packet": "flow",
         "command": "microcosm comprehend --slice flows --organ <id>"},
        {"question": "change something safely?", "packet": "mutation_plan",
         "command": "microcosm comprehend --mutation <id|path>"},
        {"question": "read a file's atoms without opening source?", "packet": "path",
         "command": "microcosm comprehend --path <owned_file>"},
    ]
    if profile == "whole_substrate_map":
        pack["whole_substrate_map"] = _whole_substrate_rows(
            families, atlas_by, join_by, synopsis_by
        )
    if profile == "public_reader":
        pack["public_reader"] = _public_reader_block(health, atlas)
    # TAIL RECAP -- repeat the core frame at the end (lost-in-the-middle guard).
    pack["tail_recap"] = {
        "core_frame": f"{organ_count} organs, {len(families)} families; {exact_copy}/{organ_count} "
        "runners are exact-copy macro bodies; presence_only; authorizes nothing.",
        "next_packet_if_lost": "microcosm comprehend --packet-atlas",
        "to_comprehend_every_organ": "microcosm comprehend --self-model --profile whole_substrate_map",
    }
    pack["evidence_refs"] = [
        "core/organ_atlas.json",
        "receipts/code_lens/code_lens_join_index_v0.json",
        "core/component_public_synopses.json",
        "src/microcosm_core/comprehension.py#PACKET_SPECS",
    ]
    return pack


_MODE_COMPILERS = {
    "first-contact": lambda inputs, target: compile_first_contact(inputs),
    "authority": lambda inputs, target: compile_authority(inputs),
    "organs": lambda inputs, target: compile_organs_index(inputs),
    "organ": lambda inputs, target: compile_organ(inputs, target or ""),
    "packet-atlas": lambda inputs, target: compile_packet_atlas(inputs),
    "self-model": lambda inputs, target: compile_self_model(inputs, target or "operating_picture"),
    "organ_cluster": lambda inputs, target: compile_organ_cluster(inputs, target or ""),
    "math": lambda inputs, target: compile_math(inputs),
    "claim_trace": lambda inputs, target: compile_claim_trace(inputs, target or ""),
    "flow": lambda inputs, target: compile_flow(inputs, target or ""),
}


def comprehend(
    *,
    root: Path | None = None,
    mode: str = "first-contact",
    organ_id: str | None = None,
    target: str | None = None,
    goal: str | None = None,
    path: str | None = None,
    with_excerpts: bool = False,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one comprehension packet and stamp its identity, budget, and latency.

    - Teleology: the single dispatch a CLI or test calls to get a goal-shaped packet --
      first-contact, the packet atlas, an organ/cluster/math/claim_trace/flow read, or a
      local_semantic_excerpt path/mutation_plan packet.
    - Guarantee: returns the compiled pack with packet_id/packet_kind/next_packets and a
      budget verdict (when the mode is a registered packet) plus a compile_ms float;
      ``target`` (falling back to organ_id) carries the organ/family/path argument; a
      goal string overrides mode/target via route_goal.
    - Fails: ValueError on an unknown mode or a source-body-leaking join index.
    - Reads: the substrate inputs (loaded here unless ``inputs`` is supplied).
    - Writes: nothing.
    - Non-goal: never writes excerpts into the committed presence_only cache.
    """
    start = time.perf_counter()
    base_root = root or default_root()
    bundle = inputs if inputs is not None else load_inputs(base_root)
    target = target if target is not None else organ_id
    routing_note = None
    if goal:
        mode, target, routing_note = route_goal(goal, bundle)
    if mode == "path":
        pack = compile_path_excerpts(base_root, path or target or "")
    elif mode == "mutation_plan":
        pack = compile_mutation_plan(bundle, base_root, target or path or "")
    else:
        compiler = _MODE_COMPILERS.get(mode)
        if compiler is None:
            raise ValueError(f"unknown comprehension mode: {mode!r}")
        pack = compiler(bundle, target)
        if mode == "organ" and with_excerpts and pack.get("found"):
            _attach_organ_excerpts(pack, base_root, target or "", bundle)
    if routing_note:
        pack["routing_note"] = routing_note
    spec = packet_spec_for_mode(mode)
    if spec is not None:
        _stamp_packet_identity(pack, spec)
    pack["compile_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return pack


def build_cached_read_packs(
    root: Path | None = None, out_dir: Path | None = None
) -> dict[str, Any]:
    """Materialize the prebuilt first-contact / authority / organs read packs.

    - Teleology: Level-1 cache -- commit the presence_only entry packs (including the
      packet atlas) so a cold clone can read them without running the compiler.
    - Guarantee: writes first_contact.json, authority.json, organs_index.json, and
      packet_atlas.json under receipts/code_lens/read_packs/ and returns a manifest of
      {name, path, bytes} per pack; packet_atlas is built last so it reports the other
      caches' real on-disk sizes.
    - Fails: OSError if the output directory cannot be created/written.
    - Reads: the substrate inputs once.
    - Writes: the four prebuilt presence_only read-pack receipts.
    - Non-goal: never prebuilds local_semantic_excerpt packs (path/mutation_plan stay
      on-demand and local-only) or per-organ packs (82 of them stay on-demand).
    """
    base = root or default_root()
    target = out_dir or (base / "receipts/code_lens/read_packs")
    target.mkdir(parents=True, exist_ok=True)
    bundle = load_inputs(base)
    bundle["root"] = base
    manifest: dict[str, Any] = {"schema_version": READ_PACK_SCHEMA, "packs": []}
    for name, mode in (
        ("first_contact", "first-contact"),
        ("authority", "authority"),
        ("organs_index", "organs"),
        ("self_model", "self-model"),
        ("packet_atlas", "packet-atlas"),
    ):
        pack = comprehend(mode=mode, inputs=bundle)
        body = json.dumps(pack, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        path = target / f"{name}.json"
        path.write_text(body)
        manifest["packs"].append(
            {"name": name, "path": str(path.relative_to(base)), "bytes": len(body)}
        )
    return manifest


# --- cold-agent comprehension assay -----------------------------------------------

# Each assay row is answerable purely from a presence_only pack: it names the mode, the
# JSON dotted path that must be non-empty, and (optionally) an evidence token that must
# appear in the rendered pack. No row requires opening source.
def _assay_rows(sample_organ: str | None) -> list[dict[str, Any]]:
    """Return the fixed assay question set, parameterized by a sample organ.

    - Teleology: define the cold-agent questions whose answers must live in read packs.
    - Guarantee: returns a list of {q, mode, organ, must_key, evidence_token} rows.
    - Fails: never raises.
    """
    return [
        {"q": "What is Microcosm?", "mode": "first-contact", "organ": None,
         "must_key": "summary.what_this_is", "evidence_token": "substrate"},
        {"q": "What organ families exist?", "mode": "first-contact", "organ": None,
         "must_key": "selected_nodes", "evidence_token": "family_roster"},
        {"q": "What must I not trust?", "mode": "first-contact", "organ": None,
         "must_key": "summary.what_not_to_trust", "evidence_token": None},
        {"q": "What is the authority ceiling?", "mode": "authority", "organ": None,
         "must_key": "authority_ceiling", "evidence_token": "release_authorized"},
        {"q": "Which organs are validators vs projections?", "mode": "authority", "organ": None,
         "must_key": "selected_nodes", "evidence_token": "evidence_distribution"},
        {"q": f"What does organ {sample_organ} do?", "mode": "organ", "organ": sample_organ,
         "must_key": "summary.what_this_is", "evidence_token": None},
        {"q": f"Should I read {sample_organ}'s runner source?", "mode": "organ", "organ": sample_organ,
         "must_key": "specificity_risks", "evidence_token": "runner_custody_basis"},
        {"q": f"When do I open source for {sample_organ}?", "mode": "organ", "organ": sample_organ,
         "must_key": "source_span_escalation", "evidence_token": None},
    ]


def _dig(pack: dict[str, Any], dotted: str) -> Any:
    """Resolve a dotted key path into a pack, returning None when absent.

    - Teleology: let assay rows assert on nested pack fields by path.
    - Guarantee: returns the nested value or None; never raises on a missing key.
    - Fails: never raises.
    """
    cur: Any = pack
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _pack_leaks_source_body(pack: dict[str, Any]) -> bool:
    """Detect whether a pack leaked a raw docstring atom bullet.

    - Teleology: enforce the presence_only membrane on compiled output, not just input.
    - Guarantee: returns True iff the serialized pack contains a "- Teleology:"-style
      raw atom bullet marker.
    - Fails: never raises.
    - Reads: only the in-memory pack.
    """
    body = json.dumps(pack, ensure_ascii=True)
    return any(marker in body for marker in _ATOM_BULLET_MARKERS)


def run_comprehension_assay(
    root: Path | None = None, inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Run the cold-agent comprehension assay over the compiled read packs.

    - Teleology: prove the read packs actually let a cold agent answer substrate /
      authority / organ questions without opening source -- the activation evidence.
    - Guarantee: returns an ASSAY_SCHEMA dict with answerable_without_source_pct,
      wrong_authority_claims, source_body_leaks, source_reads_avoided, max_pack_bytes,
      max_compile_ms, and a per-question result list; all metrics are computed, not asserted.
    - Fails: never raises on content; ValueError only on a leaking join index (via load).
    - Reads: the substrate inputs once.
    - Writes: nothing.
    - Non-goal: does not call any LLM; "answerable" means the answer material is present.
    """
    bundle = inputs if inputs is not None else load_inputs(root)
    join_by = bundle.get("join_by_organ", {})
    # Prefer a custody-bound organ so the runner-source question exercises the finding.
    sample_organ = next(
        (oid for oid, n in join_by.items()
         if n.get("runner_custody_basis") == "directory_coupling_marker"),
        next(iter(join_by), None) or next(iter(bundle.get("atlas_by_organ", {})), None),
    )
    rows = _assay_rows(sample_organ)
    results: list[dict[str, Any]] = []
    answered = 0
    wrong_authority = 0
    leaks = 0
    reads_avoided = 0
    max_bytes = 0
    max_ms = 0.0
    for row in rows:
        pack = comprehend(mode=row["mode"], organ_id=row["organ"], inputs=bundle)
        value = _dig(pack, row["must_key"])
        body = json.dumps(pack, ensure_ascii=True)
        token_ok = row["evidence_token"] is None or row["evidence_token"] in body
        answerable = bool(value) and token_ok
        if answerable:
            answered += 1
        if _pack_leaks_source_body(pack):
            leaks += 1
        ceiling = pack.get("authority_ceiling") or {}
        if any(ceiling.get(k) for k in AUTHORITY_CEILING):
            wrong_authority += 1
        if row["mode"] == "organ" and answerable:
            reads_avoided += 1
        max_bytes = max(max_bytes, len(body))
        max_ms = max(max_ms, float(pack.get("compile_ms") or 0.0))
        results.append(
            {
                "q": row["q"],
                "mode": row["mode"],
                "must_key": row["must_key"],
                "answerable_without_source": answerable,
            }
        )
    total = len(rows) or 1
    return {
        "schema_version": ASSAY_SCHEMA,
        "sample_organ": sample_organ,
        "questions": len(rows),
        "answerable_without_source_pct": round(100.0 * answered / total, 1),
        "wrong_authority_claims": wrong_authority,
        "source_body_leaks": leaks,
        "source_reads_avoided": reads_avoided,
        "max_pack_bytes": max_bytes,
        "max_compile_ms": round(max_ms, 3),
        "results": results,
        "authority_ceiling": dict(AUTHORITY_CEILING),
    }


def _symbols_expose_atom(symbols: list[dict[str, Any]], atom: str) -> bool:
    """True when at least one excerpt symbol exposes a value for the named atom.

    - Teleology: the hard-assay predicate proving the local band actually carries a
      given authored atom's value, not merely that a symbol exists.
    - Guarantee: returns True iff some row's atom_values contains ``atom``.
    - Fails: never raises.
    - Reads: only the supplied excerpt rows.
    """
    return any(atom in (s.get("atom_values") or {}) for s in symbols)


def run_hard_comprehension_assay(root: Path | None = None) -> dict[str, Any]:
    """Run the hard assay that requires real authored atom-value content.

    - Teleology: prove the local_semantic_excerpt band carries actual code semantics
      (Teleology/Guarantee/Fails/Non-goal values) AND that its guards hold -- the v0
      assay only proved presence_only orientation; this proves the rail carries fuel.
    - Guarantee: returns a HARD_ASSAY_SCHEMA dict with answerable_with_atom_values_pct
      over questions that each require an emitted atom value, plus excerpt_leak_count
      (secret/private shapes found in the emitted excerpts -- must be 0) and
      custody_violation_count (custody-bound files that wrongly produced excerpts --
      must be 0); all metrics are computed, not asserted.
    - Fails: never raises on content; ValueError only on a leaking join index (via load).
    - Reads: the owned comprehension module's atoms + one custody-bound runner.
    - Writes: nothing.
    - Non-goal: does not call any LLM; "answerable" means the atom value is present.
    """
    base = root or default_root()
    owned_target = "src/microcosm_core/comprehension.py"
    owned = extract_atom_excerpts(base, owned_target)
    inputs = load_inputs(base)
    custody_target = next(
        (
            n.get("runner_source_ref")
            for n in inputs.get("join_by_organ", {}).values()
            if n.get("runner_custody_basis") == "directory_coupling_marker"
            and n.get("runner_source_ref")
        ),
        None,
    )
    custody = (
        extract_atom_excerpts(base, custody_target)
        if custody_target
        else {"eligible": False, "symbols": []}
    )

    symbols = owned["symbols"]
    custody_clean = not (custody.get("eligible") and custody.get("symbols"))
    questions = [
        ("owned file yields >=10 excerpted symbols", owned.get("symbol_count", 0) >= 10),
        ("some symbol exposes a Teleology value", _symbols_expose_atom(symbols, "Teleology")),
        ("some symbol exposes a Guarantee value", _symbols_expose_atom(symbols, "Guarantee")),
        ("some symbol exposes a Fails value", _symbols_expose_atom(symbols, "Fails")),
        ("some symbol exposes a Non-goal value", _symbols_expose_atom(symbols, "Non-goal")),
        ("a custody-bound runner yields zero excerpts", custody_clean),
    ]
    answered = sum(1 for _q, ok in questions if ok)
    emitted = json.dumps(owned, ensure_ascii=True)
    leak_count = len(_SECRET_SHAPE_RE.findall(emitted)) + len(_PRIVATE_PATH_RE.findall(emitted))
    return {
        "schema_version": HARD_ASSAY_SCHEMA,
        "owned_target": owned_target,
        "owned_symbols_excerpted": owned.get("symbol_count", 0),
        "custody_target": custody_target,
        "custody_target_excerpted_symbols": len(custody.get("symbols", [])),
        "questions": len(questions),
        "answerable_with_atom_values_pct": round(100.0 * answered / len(questions), 1),
        "excerpt_leak_count": leak_count,
        "custody_violation_count": 0 if custody_clean else 1,
        "guard_drops": owned.get("leak_guard", {}),
        "results": [{"q": q, "ok": ok} for q, ok in questions],
        "authority_ceiling": dict(AUTHORITY_CEILING),
    }


# --- packet-route assay: does the atlas actually navigate? -------------------------

# Routing fixtures: a goal a cold agent might type, and the packet_id it must land on.
# These double as the "will it navigate" proof and guard route_goal against drift.
_PACKET_ROUTE_FIXTURES: list[tuple[str, str]] = [
    ("I just cloned this repo, what is it?", "first_contact"),
    ("comprehend the whole microcosm at once", "self_model"),
    ("where are the math and proof surfaces?", "math"),
    ("how is this claim justified, what receipt proves it?", "claim_trace"),
    ("how does execution flow here", "flow"),
    ("what may I trust here?", "authority"),
    ("list all organs", "organs_index"),
    ("which packet should I use?", "packet_atlas"),
    ("I want to change the import behaviour", "mutation_plan"),
    ("read the atom values in src/microcosm_core/comprehension.py", "path"),
]


def _assay_sample_target(mode: str, inputs: dict[str, Any]) -> str | None:
    """Pick a representative target so each parameterized packet can compile in the assay.

    - Teleology: let the route assay actually compile organ/cluster/claim/flow/mutation
      packets, not only the parameterless ones.
    - Guarantee: returns a family name for organ_cluster, an owned path for path/
      mutation_plan, a sample organ id for organ/claim_trace/flow, else None.
    - Fails: never raises; returns None when no sample is available.
    - Reads: the in-memory inputs bundle only.
    """
    if mode == "organ_cluster":
        roster = _family_roster(list(inputs.get("atlas_by_organ", {}).values()))
        return roster[0]["family"] if roster else None
    if mode in ("path", "mutation_plan"):
        return OWNED_EXCERPT_ROOT + "comprehension.py"
    if mode in ("organ", "claim_trace", "flow"):
        return next(iter(inputs.get("join_by_organ", {})), None) or next(
            iter(inputs.get("atlas_by_organ", {})), None
        )
    return None


def run_packet_route_assay(
    root: Path | None = None, inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Assay the packet atlas as a navigable product, not just an answer surface.

    - Teleology: prove the atlas NAVIGATES -- goals route to the right packet, every
      advertised packet compiles in-band/in-budget/leak-free, scent links resolve, and
      the committed cache carries no excerpts -- so the menu can be trusted as the entry.
    - Guarantee: returns a PACKET_ROUTE_ASSAY_SCHEMA dict with packet_route_accuracy_pct,
      wrong_packet_count, authority_overclaim_count, public_excerpt_leak_count (packet +
      cache), budget_violations, slo_violations, next_packet_link_coverage_pct,
      first_contact_has_scent, packet_bytes_by_kind, the (closed) sqlite_gate, and per-
      route / per-packet / per-cache result rows; all metrics are computed, not asserted.
    - Fails: never raises on content; ValueError only on a leaking join index (via load).
    - Reads: the substrate inputs once and any prebuilt cache files.
    - Writes: nothing.
    - Non-goal: does not call any LLM; routing is the deterministic route_goal mapping.
    """
    bundle = inputs if inputs is not None else load_inputs(root)
    base = bundle.get("root") or default_root()
    known_ids = set(_SPEC_BY_ID)

    route_results: list[dict[str, Any]] = []
    correct = 0
    for goal, expected in _PACKET_ROUTE_FIXTURES:
        mode, _t, _n = route_goal(goal, bundle)
        got = (_SPEC_BY_MODE.get(mode) or {}).get("packet_id")
        ok = got == expected
        correct += 1 if ok else 0
        route_results.append({"goal": goal, "expected": expected, "got": got, "ok": ok})

    packet_checks: list[dict[str, Any]] = []
    overclaim = 0
    packet_leaks = 0
    budget_violations = 0
    slo_violations = 0
    scent_resolved = 0
    bytes_by_kind: dict[str, int] = {}
    max_ms = 0.0
    for spec in PACKET_SPECS:
        mode = spec["mode"]
        sample = _assay_sample_target(mode, bundle)
        pack = comprehend(mode=mode, target=sample, inputs=bundle, root=base)
        body = json.dumps(pack, ensure_ascii=True)
        band_ok = pack.get("export_band") == spec["export_band"]
        ceiling = pack.get("authority_ceiling") or {}
        overclaimed = any(ceiling.get(k) for k in AUTHORITY_CEILING)
        leaked = spec["export_band"] == "presence_only" and _pack_leaks_source_body(pack)
        within = (pack.get("budget") or {}).get("within_budget", True)
        nexts = pack.get("next_packets") or []
        scent_ok = bool(nexts) and all(n in known_ids for n in nexts)
        ms = float(pack.get("compile_ms") or 0.0)
        overclaim += 1 if overclaimed else 0
        packet_leaks += 1 if leaked else 0
        budget_violations += 0 if within else 1
        slo_violations += 0 if ms <= spec["slo_ms"] else 1
        scent_resolved += 1 if scent_ok else 0
        max_ms = max(max_ms, ms)
        bytes_by_kind[spec["packet_id"]] = len(body)
        packet_checks.append(
            {
                "packet_id": spec["packet_id"],
                "mode": mode,
                "band_ok": band_ok,
                "overclaim": overclaimed,
                "leaked": leaked,
                "within_budget": within,
                "scent_resolves": scent_ok,
                "compile_ms": ms,
                "bytes": len(body),
            }
        )

    cache_checks: list[dict[str, Any]] = []
    cache_leaks = 0
    for spec in PACKET_SPECS:
        ref = spec.get("cache_ref")
        if not ref:
            continue
        cache_path = base / ref
        if not cache_path.exists():
            cache_checks.append({"cache_ref": ref, "present": False})
            continue
        doc = _load_json(cache_path) or {}
        has_excerpts = bool(doc.get("semantic_excerpts"))
        cache_leaks += 1 if has_excerpts else 0
        cache_checks.append(
            {
                "cache_ref": ref,
                "present": True,
                "export_band": doc.get("export_band"),
                "has_excerpts": has_excerpts,
            }
        )

    total_routes = len(_PACKET_ROUTE_FIXTURES) or 1
    return {
        "schema_version": PACKET_ROUTE_ASSAY_SCHEMA,
        "packets": len(PACKET_SPECS),
        "packet_route_accuracy_pct": round(100.0 * correct / total_routes, 1),
        "wrong_packet_count": total_routes - correct,
        "authority_overclaim_count": overclaim,
        "public_excerpt_leak_count": packet_leaks + cache_leaks,
        "budget_violations": budget_violations,
        "slo_violations": slo_violations,
        "max_compile_ms": round(max_ms, 3),
        "next_packet_link_coverage_pct": round(100.0 * scent_resolved / len(PACKET_SPECS), 1),
        "first_contact_has_scent": bool(_SPEC_BY_ID["first_contact"].get("next_packets")),
        "packet_bytes_by_kind": bytes_by_kind,
        "sqlite_gate": SQLITE_GATE,
        "route_results": route_results,
        "packet_checks": packet_checks,
        "cache_checks": cache_checks,
        "authority_ceiling": dict(AUTHORITY_CEILING),
    }


# --- whole-system comprehension assay: can a cold reader comprehend ALL of it? -----

# Each row is a global question whose answer must live in the self-model packet, keyed by
# the dotted path that must be non-empty (+ an optional token that must appear under it).
_WHOLE_SYSTEM_QUESTIONS: list[tuple[str, str, str | None]] = [
    ("what is Microcosm?", "summary.what_this_is", None),
    ("what are the major organ families?", "major_subsystems", None),
    ("which surfaces are runtime vs projection vs custody/import?", "code_lens_health.by_evidence_class", None),
    ("what is the real-vs-copied calibration?", "code_lens_health.by_truth_accounting_bucket", None),
    ("what should NOT be claimed?", "authority_membrane.authority_ceiling", None),
    ("where is the thinness / where to be skeptical?", "thin_or_projection_surfaces", None),
    ("what remains deferred?", "deferred_edges", None),
    ("which packet inspects one organ next?", "recommended_drilldowns", "organ"),
    ("is there a front anchor?", "read_me_first", None),
    ("is there a tail recap?", "tail_recap", None),
]


def run_whole_system_comprehension_assay(
    root: Path | None = None, inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Assay whether the self-model lets a cold reader comprehend the WHOLE substrate.

    - Teleology: prove the self-model causes calibrated whole-system understanding -- a
      cold reader can answer global questions, map every organ, see the thinness and the
      caveats, and pick the right drilldown -- WITHOUT raw repo archaeology. This is the
      show-don't-tell replacement for any "is it impressive?" question.
    - Guarantee: returns a WHOLE_SYSTEM_ASSAY_SCHEMA dict with whole_system_answerability_pct,
      every_organ_mapped (whole_substrate_map covers all atlas organs), overclaim_count,
      source_body_leaks, thinness_surfaced, deferred_surfaced, front_anchor_present,
      tail_recap_present, packet_bytes, and per-question rows; all metrics computed.
    - Fails: never raises on content; ValueError only on a leaking join index (via load).
    - Reads: the substrate inputs once.
    - Writes: nothing.
    - Non-goal: does not call any LLM and does not score "impressiveness".
    """
    bundle = inputs if inputs is not None else load_inputs(root)
    base = bundle.get("root") or default_root()
    pack = comprehend(mode="self-model", target="whole_substrate_map", inputs=bundle, root=base)
    answered = 0
    results: list[dict[str, Any]] = []
    for question, key, token in _WHOLE_SYSTEM_QUESTIONS:
        value = _dig(pack, key)
        ok = bool(value) and (token is None or token in json.dumps(value, ensure_ascii=True))
        answered += 1 if ok else 0
        results.append({"q": question, "key": key, "answerable": ok})
    ceiling = pack.get("authority_ceiling") or {}
    overclaim = sum(1 for k in AUTHORITY_CEILING if ceiling.get(k))
    leak = 1 if _pack_leaks_source_body(pack) else 0
    mapped = sum(len(fam.get("organs", [])) for fam in pack.get("whole_substrate_map", []))
    organ_total = len(bundle.get("atlas_by_organ", {}))
    total_q = len(_WHOLE_SYSTEM_QUESTIONS) or 1
    return {
        "schema_version": WHOLE_SYSTEM_ASSAY_SCHEMA,
        "profile": pack.get("context_profile"),
        "whole_system_answerability_pct": round(100.0 * answered / total_q, 1),
        "organs_mapped": mapped,
        "organ_total": organ_total,
        "every_organ_mapped": mapped >= organ_total and mapped > 0,
        "overclaim_count": overclaim,
        "wrong_authority_claims": overclaim,
        "source_body_leaks": leak,
        "public_excerpt_leak_count": leak,
        "thinness_surfaced": bool(pack.get("thin_or_projection_surfaces")),
        "deferred_surfaced": bool(pack.get("deferred_edges")),
        "front_anchor_present": bool(pack.get("read_me_first")),
        "tail_recap_present": bool(pack.get("tail_recap")),
        "packet_bytes": len(json.dumps(pack, ensure_ascii=True)),
        "results": results,
        "authority_ceiling": dict(AUTHORITY_CEILING),
    }
