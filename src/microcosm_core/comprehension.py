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

import json
import time
from pathlib import Path
from typing import Any

READ_PACK_SCHEMA = "microcosm_comprehension_read_pack_v0"
ASSAY_SCHEMA = "microcosm_cold_agent_comprehension_assay_v0"

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
    """Route a freeform goal string to a comprehension mode.

    - Teleology: let a cold agent ask in words and still land on a bounded pack.
    - Guarantee: returns (mode, organ_id, note) where mode is one of first-contact,
      organ, authority, organs; organ_id is set when the goal names a known organ; note
      flags deferred slices (math/claims/flows) honestly.
    - Fails: never raises; an empty/unknown goal routes to first-contact.
    - Reads: the in-memory inputs (organ id set) only.
    """
    text = (goal or "").lower()
    for oid in inputs.get("atlas_by_organ", {}):
        if oid.lower() in text:
            return "organ", oid, None
    if any(word in text for word in ("authority", "trust", "ceiling", "allowed", "safe to")):
        return "authority", None, None
    if any(word in text for word in ("list", "roster", "inventory", "all organs", "what organs")):
        return "organs", None, None
    note = None
    if any(word in text for word in ("math", "proof", "claim", "flow", "trace")):
        note = (
            "math/claims/flows slices are deferred to a later strike (need join-index v1 "
            "organ->mechanism/standard and claim->validator->receipt edges); returning "
            "first-contact."
        )
    return "first-contact", None, note


_MODE_COMPILERS = {
    "first-contact": lambda inputs, organ_id: compile_first_contact(inputs),
    "authority": lambda inputs, organ_id: compile_authority(inputs),
    "organs": lambda inputs, organ_id: compile_organs_index(inputs),
    "organ": lambda inputs, organ_id: compile_organ(inputs, organ_id or ""),
}


def comprehend(
    *,
    root: Path | None = None,
    mode: str = "first-contact",
    organ_id: str | None = None,
    goal: str | None = None,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one read pack and stamp its compile latency.

    - Teleology: the single dispatch a CLI or test calls to get a goal-specific pack.
    - Guarantee: returns the compiled pack with an added compile_ms float; a goal string
      overrides mode/organ_id via route_goal and records the routing note.
    - Fails: ValueError on an unknown mode or a source-body-leaking join index.
    - Reads: the substrate inputs (loaded here unless ``inputs`` is supplied).
    - Writes: nothing.
    """
    start = time.perf_counter()
    bundle = inputs if inputs is not None else load_inputs(root)
    routing_note = None
    if goal:
        mode, organ_id, routing_note = route_goal(goal, bundle)
    compiler = _MODE_COMPILERS.get(mode)
    if compiler is None:
        raise ValueError(f"unknown comprehension mode: {mode!r}")
    pack = compiler(bundle, organ_id)
    if routing_note:
        pack["routing_note"] = routing_note
    pack["compile_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return pack


def build_cached_read_packs(
    root: Path | None = None, out_dir: Path | None = None
) -> dict[str, Any]:
    """Materialize the prebuilt first-contact / authority / organs read packs.

    - Teleology: Level-1 cache -- commit the entry packs so a cold clone can read them
      without running the compiler, and so the comprehension surface is inspectable.
    - Guarantee: writes first_contact.json, authority.json, organs_index.json under
      receipts/code_lens/read_packs/ and returns a manifest of {path, bytes} per pack.
    - Fails: OSError if the output directory cannot be created/written.
    - Reads: the substrate inputs once.
    - Writes: the three prebuilt read-pack receipts.
    - Non-goal: does not prebuild per-organ packs (82 of them stay on-demand).
    """
    base = root or default_root()
    target = out_dir or (base / "receipts/code_lens/read_packs")
    target.mkdir(parents=True, exist_ok=True)
    bundle = load_inputs(base)
    manifest: dict[str, Any] = {"schema_version": READ_PACK_SCHEMA, "packs": []}
    for name, mode in (
        ("first_contact", "first-contact"),
        ("authority", "authority"),
        ("organs_index", "organs"),
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
