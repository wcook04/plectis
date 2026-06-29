#!/usr/bin/env python3
"""[PURPOSE]
- Teleology: Compile source-body-free Plectis comprehension packets that let a
  cold agent move from a goal or package overview to bounded module, organ,
  claim, evidence, and validation surfaces without opening private context.
- Mechanism: Joins the public code-lens join index, organ atlas, and public
  synopses into presence-only read packs with explicit authority ceilings.
- Guarantee: Every public packet declares the active membrane band, refuses
  source-body export authority, and preserves validation/escalation routes.

[INTERFACE]
- Inputs: Public Plectis data under `core/` and `receipts/code_lens/`, plus
  caller-supplied goals, modes, organ ids, owned paths, or preloaded inputs.
- Outputs: Dict packets such as `microcosm_comprehension_read_pack_v0`,
  assay receipts, and optional cached JSON files from `build_cached_read_packs`.
- Exports: `comprehend`, the compile_* packet builders, assay runners, schema
  constants, and membrane/authority-ceiling declarations.

[FLOW]
- Resolve the Plectis resource root, load public metadata, guard the membrane,
  compile the requested packet, stamp packet identity/latency, and expose assay
  runners that prove first-contact routing without reading source bodies.
- Local semantic excerpts are only produced for owned source paths and remain
  separate from committed presence-only cache outputs.

[DEPENDENCIES]
- `microcosm_core.resource_root` locates the source checkout or installed public
  data root.
- Public data files: `core/organ_atlas.json`,
  `core/component_public_synopses.json`, and
  `receipts/code_lens/code_lens_join_index_v0.json`.

[CONSTRAINTS]
- Atomicity: Read-pack compilers are pure dict builders; only
  `build_cached_read_packs` writes files, and only to the selected cache dir.
- Determinism: Packet builders use stable sorting and bounded lists where the
  public route contract requires reproducible output.
- Forbid: Presence-only packets must not contain source bodies, raw private
  paths, release authorization, static-analysis authority, or whole-system
  correctness claims.

Microcosm Comprehension Plane: a source-body-free, goal-directed read-pack compiler.

A cold agent that clones this repo should not be met with "read the source." It
should be met with ``plectis comprehend``: a route that compiles bounded read
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
import posixpath
import re
import time
from pathlib import Path
from typing import Any

from microcosm_core import resource_root

READ_PACK_SCHEMA = "microcosm_comprehension_read_pack_v0"
ASSAY_SCHEMA = "microcosm_cold_agent_comprehension_assay_v0"
PACKET_ATLAS_SCHEMA = "microcosm_comprehension_packet_atlas_v0"
PACKET_ROUTE_ASSAY_SCHEMA = "microcosm_packet_route_assay_v0"
SELF_MODEL_SCHEMA = "microcosm_whole_system_self_model_v0"
WHOLE_SYSTEM_ASSAY_SCHEMA = "microcosm_whole_system_comprehension_assay_v0"
FIRST_ACTION_ASSAY_SCHEMA = "microcosm_first_action_assay_v0"

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

# Canonical first-contact routes a cold agent should run, in order. The goal-shaped
# entry leads: a cold agent with a concrete goal should get its first correct action
# before absorbing any inventory.
_START_HERE_ROUTES = [
    'plectis comprehend --first-action "<goal>"',
    "plectis comprehend --first-contact",
    "plectis comprehend --slice authority",
    "plectis comprehend --organ <organ_id>",
    "plectis comprehend --slice organs",
]

# --- atom_value_membrane_v1: the local_semantic_excerpt band -----------------------
# This band is the FIRST sanctioned exporter of authored docstring-atom prose, and it
# is deliberately bounded: owned source only (custody-gated), per-atom char cap, secret
# and private-path scrubbing, and NEVER written into the committed presence_only cache.
LOCAL_EXCERPT_SCHEMA = "microcosm_atom_value_excerpt_v1"
HARD_ASSAY_SCHEMA = "microcosm_hard_comprehension_assay_v1"
# The owned package root whose authored atoms may be excerpted locally.
OWNED_EXCERPT_ROOT = "src/microcosm_core/"
# Per-atom character cap, symbol cap, and total per-file pack byte budget for excerpts.
MAX_ATOM_CHARS = 240
MAX_EXCERPT_SYMBOLS = 48
MAX_EXCERPT_PACK_BYTES = 32000
# Secret-shape and private-home-path patterns: any atom value matching is DROPPED
# (never emitted), so an excerpt pack cannot leak a credential or an operator path.
_SECRET_SHAPE_RE = re.compile(
    r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY",
)
_PRIVATE_PATH_RE = re.compile(r"/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+")


def default_root() -> Path:
    """
    [ACTION]
    Resolve the substrate root that holds core/ and receipts/.

    - Teleology: let comprehend find its public inputs regardless of the caller's
      cwd, including from an installed package where the public data lives under
      share/plectis rather than a source checkout.
    - Guarantee: returns resource_root.microcosm_root() -- the source checkout
      when it carries the public manifest triple, else the installed share root.
    - Fails: never raises; pure path resolution.
    - Reads: the public manifest probe files via resource_root.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return resource_root.microcosm_root()


def _load_json(path: Path) -> Any:
    """
    [ACTION]
    Parse a JSON file, returning None when it is absent or unreadable.

    - Teleology: one tolerant reader so a missing join index degrades instead of crashing.
    - Guarantee: returns the parsed value, or None when the path is missing/unparseable.
    - Fails: never raises; OSError/ValueError are swallowed into None.
    - Reads: the file at ``path``.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def load_inputs(root: Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    Load the three public inputs the compiler joins, tolerating absent ones.

    - Teleology: assemble the source-body-free input bundle for every compile call.
    - Guarantee: returns {root, join_index, atlas, synopses, atlas_by_organ,
      join_by_organ, synopsis_by_organ, join_index_present}; missing files become None
      and an empty index rather than an error.
    - Fails: ValueError only when the join index payload reports source_bodies_exported.
    - Reads: receipts/code_lens/code_lens_join_index_v0.json, core/organ_atlas.json,
      core/component_public_synopses.json under ``root``.
    - Non-goal: never opens source files or docstring atoms.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Refuse to compile from a join index that leaked source bodies.

    - Teleology: enforce the presence_only membrane at the input boundary, mirroring
      the join-index builder's own leak refusal.
    - Guarantee: returns None when the snapshot is clean or absent.
    - Fails: ValueError when join_index.source_bodies_exported is truthy.
    - Reads: only the in-memory snapshot.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    if isinstance(join_index, dict) and join_index.get("source_bodies_exported"):
        raise ValueError(
            "refusing to compose read packs from a join index that exports source bodies"
        )


def _pack_skeleton(mode: str, goal: str | None) -> dict[str, Any]:
    """
    [ACTION]
    Return the common read-pack envelope every mode fills in.

    - Teleology: guarantee one schema, membrane, and ceiling across all read packs.
    - Guarantee: returns a dict with schema_version, mode, goal, export_band,
      membrane, authority_ceiling, and empty selected_nodes/edges/refs/escalation lists.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    """
    [ACTION]
    Group atlas organ rows into a family roster with counts and members.

    - Teleology: give a cold agent the "what organs exist" map in one glance.
    - Guarantee: returns a list of {family, count, organs:[{organ_id, display_name,
      specialty}]} sorted by descending count then family name.
    - Fails: never raises; rows missing a family fall under "unspecified".
    - Reads: the in-memory atlas rows only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Count organs per evidence_class from join-index organ nodes.

    - Teleology: surface how much of the substrate is validator vs projection vs
      macro-import, the core authority question.
    - Guarantee: returns evidence_class -> count, using "unspecified" for None.
    - Fails: never raises.
    - Reads: the in-memory organ nodes only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    dist: dict[str, int] = {}
    for node in join_organs:
        cls = str(node.get("evidence_class") or "unspecified")
        dist[cls] = dist.get(cls, 0) + 1
    return dict(sorted(dist.items(), key=lambda kv: (-kv[1], kv[0])))


def compile_first_contact(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Compile the substrate-orientation read pack for a cold clone.

    - Teleology: answer "what is this substrate and where do I start?" from public
      metadata so the agent never has to grep the repo first.
    - Guarantee: returns a tutorial-mode pack whose summary states the organ/family
      counts and authority boundary, whose selected_nodes carry the family roster and
      evidence distribution, and whose what_not_to_trust is the atlas anti_claim.
    - Fails: never raises; absent atlas yields a degraded but valid pack.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: emits no source bodies and no per-symbol docstrings.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Summarize substrate-wide runner custody, the headline comprehension truth.

    - Teleology: tell a cold agent up front that most organ runners are exact-copy
      macro bodies, so organ comprehension must come from registry metadata.
    - Guarantee: returns {custody_split, runners_resolved, note} counted from the
      organ nodes' runner_custody_basis.
    - Fails: never raises.
    - Reads: the in-memory organ nodes only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Extract resolved reference strings from an atlas ref list.

    - Teleology: turn the atlas's {ref, resolution_status} rows into a flat ref list
      for the read pack's inspect-next surface.
    - Guarantee: returns the ref strings whose resolution_status is "resolved"; plain
      string rows pass through; non-list input yields [].
    - Fails: never raises.
    - Reads: only the supplied rows.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Select the join-index edges originating from one organ.

    - Teleology: give the organ pack its implemented_by_runner / emits_receipt edges.
    - Guarantee: returns the edge dicts whose ``from`` equals organ_id; [] when none.
    - Fails: never raises.
    - Reads: the in-memory join index only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    edges = (join_index or {}).get("edges") or []
    return [e for e in edges if isinstance(e, dict) and e.get("from") == organ_id]


def _edges_touching(join_index: Any, organ_id: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    Select every join-index edge that touches one organ's graph neighborhood.

    - Teleology: the v2 selection behind organ/claim/flow packets -- outgoing edges
      (runner, receipts, claim, family, wires, doctrine), the organ's claim-node
      edges, and inbound routes_to / wires_to edges, so a packet shows the organ's
      place in the topology instead of only what it emits.
    - Guarantee: returns the de-duplicated edge dicts whose ``from`` is the organ or
      its claim node, or whose ``to`` is the organ; [] when the join index is absent.
    - Fails: never raises.
    - Reads: the in-memory join index only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    edges = (join_index or {}).get("edges") or []
    claim_id = f"claim::{organ_id}"
    out: list[dict[str, Any]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("from") in (organ_id, claim_id) or edge.get("to") == organ_id:
            out.append(edge)
    return out


def _routes_serving(inputs: dict[str, Any], organ_id: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    Find the task-class routes whose fan-out lands on one organ.

    - Teleology: answer "which entry points reach this organ, and with what stop
      condition?" from the join index's route plane.
    - Guarantee: returns [{task_class, role, first_command, stop_condition,
      allowed_scope}] sorted primary-first then by task_class; allowed_scope is the
      route's own scope sentence (the per-route stopping information) when the
      route node carries one; [] when the route plane is absent.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    state = _graph_state(inputs)
    route_by = {str(r.get("task_class")): r for r in state["route_nodes"]}
    rows: list[dict[str, Any]] = []
    for edge in (inputs.get("join_index") or {}).get("edges") or []:
        if not isinstance(edge, dict) or edge.get("kind") != "routes_to":
            continue
        if edge.get("to") != organ_id:
            continue
        route = route_by.get(str(edge.get("from"))) or {}
        rows.append(
            {
                "task_class": edge.get("from"),
                "role": edge.get("role"),
                "first_command": route.get("first_command"),
                "stop_condition": route.get("stop_condition"),
                "allowed_scope": route.get("allowed_scope"),
            }
        )
    rows.sort(key=lambda r: (r.get("role") != "primary", str(r.get("task_class"))))
    return rows


def _reading_boundary(inputs: dict[str, Any], organ_id: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the organ's where-to-stop-reading block from the route plane.

    - Teleology: a cold agent needs a stopping rule, not just more material; this
      surfaces the strongest route-bound stop condition for the organ.
    - Guarantee: returns {stop_condition, allowed_scope, task_classes, source};
      allowed_scope is the primary-most route's own scope sentence (the route-
      specific stopping information); when no route lands on the organ,
      stop_condition is None and a fallback_guidance string (labelled as
      comprehension-layer guidance, not route data) is supplied.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    routes = _routes_serving(inputs, organ_id)
    boundary: dict[str, Any] = {
        "stop_condition": next(
            (r["stop_condition"] for r in routes if r.get("stop_condition")), None
        ),
        "allowed_scope": next(
            (r["allowed_scope"] for r in routes if r.get("allowed_scope")), None
        ),
        "task_classes": [r["task_class"] for r in routes],
        "source": "join_index nodes.route (atlas/agent_task_routes.json)",
    }
    if boundary["stop_condition"] is None:
        boundary["fallback_guidance"] = (
            "No task-class route binds a stop condition for this organ; stop once the "
            "first command's named result record is visible (comprehension-layer "
            "guidance, not route data)."
        )
    return boundary


def _runnable_command(command: Any) -> str:
    """
    [ACTION]
    Render a command in its cold-runnable form for a fresh source clone.

    - Teleology: a packet that says "run this" must hand over a command that works
      VERBATIM from a fresh clone; the registry stores bare `python -m ...`
      identities and the atlas stores `plectis ...` console-script forms that
      only exist after pip install.
    - Guarantee: rewrites a leading "plectis " or legacy "microcosm " to
      "PYTHONPATH=src python3 -m microcosm_core " (identical CLI per the
      project's console-script entry), prefixes bare
      "python/python3 -m microcosm_core" with "PYTHONPATH=src" and normalizes
      "python " to "python3 "; other commands and non-strings pass through as
      str(command or "").
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text = str(command or "")
    for console_name in ("plectis", "microcosm"):
        prefix = f"{console_name} "
        if text.startswith(prefix):
            return "PYTHONPATH=src python3 -m microcosm_core " + text[len(prefix) :]
    if text.startswith("python -m microcosm_core"):
        return "PYTHONPATH=src python3" + text[len("python"):]
    if text.startswith("python3 -m microcosm_core"):
        return "PYTHONPATH=src " + text
    return text


_NEGATION_MARKERS = ("ignore ", "not ", "except ", "skip ", "without ", "don't want ", "do not want ")


def _resolve_goal_organs(goal: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Resolve organ mentions in a goal: normalized, negation-aware, earliest-first.

    - Teleology: "is the Mission Transaction Work Spine safe to edit?" and
      "ignore X, I want Y" must both land on the organ the agent MEANT --
      display names count, negated mentions are excluded, and when several
      organs are named the earliest positive mention wins (never dict order).
    - Guarantee: returns {selected, also_named, excluded}; mentions are found by
      matching each organ's normalized id AND display name (hyphens/underscores
      -> spaces) inside the normalized goal; a mention whose preceding ~24 chars
      contain a negation marker (ignore/not/except/skip/without) is excluded;
      among positives the earliest (then longest) mention is selected and the
      rest are recorded in also_named.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    text = re.sub(r"[-_]", " ", (goal or "").lower())
    mentions: list[tuple[int, int, str]] = []  # (position, -length, organ_id)
    for oid, row in inputs.get("atlas_by_organ", {}).items():
        for phrase in {
            re.sub(r"[-_]", " ", oid.lower()),
            re.sub(r"[-_]", " ", str(row.get("display_name") or "").lower()),
        }:
            if not phrase:
                continue
            pos = text.find(phrase)
            if pos >= 0:
                mentions.append((pos, -len(phrase), oid))
    if not mentions:
        return {"selected": None, "also_named": [], "excluded": []}
    mentions.sort()
    positives: list[str] = []
    excluded: list[str] = []
    seen: set[str] = set()
    for pos, _neg_len, oid in mentions:
        if oid in seen:
            continue
        seen.add(oid)
        window = text[max(0, pos - 24):pos]
        if any(marker in window for marker in _NEGATION_MARKERS):
            excluded.append(oid)
        else:
            positives.append(oid)
    return {
        "selected": positives[0] if positives else None,
        "also_named": positives[1:],
        "excluded": excluded,
    }


def _match_organ_tokens(goal: str, inputs: dict[str, Any]) -> str | None:
    """
    [ACTION]
    Fuzzy subject-matter rung: match goal tokens against organ names.

    - Teleology: "evaluate prompt injection defenses" names no route or exact
      organ id, but the substrate HAS an owning organ -- token overlap against
      organ_id + display_name finds it before the generic orientation fallback.
    - Guarantee: returns the best organ_id when >= 2 distinct goal tokens match
      its id/display tokens (score = matched count, ties by organ_id); else None.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    tokens = _goal_tokens(goal)
    if not tokens:
        return None
    best: tuple[int, str] | None = None
    for oid, row in inputs.get("atlas_by_organ", {}).items():
        name_tokens = set(
            _goal_tokens(oid) + _goal_tokens(str(row.get("display_name") or ""))
        )
        matched = {
            g for g in tokens if any(_tokens_overlap(g, n) for n in name_tokens)
        }
        if len(matched) >= 2 and (best is None or (-len(matched), oid) < (-best[0], best[1])):
            best = (len(matched), oid)
    return best[1] if best else None


def _organ_token_match_count(goal_tokens: list[str], organ: dict[str, Any]) -> int:
    """
    [ACTION]
    Count distinct goal tokens that match an organ's name surface.

    - Teleology: when a route row groups many relevant organs, a goal such as
      "benchmark gaming" must keep the specific organ it names instead of being
      collapsed to the route's broad primary organ.
    - Guarantee: returns the count of distinct goal tokens matching organ_id or
      display_name tokens; only those stable name surfaces participate.
    - Fails: never raises.
    - Reads: call arguments only.
    - Writes: return values.
    """
    name_tokens = set(
        _goal_tokens(str(organ.get("organ_id") or ""))
        + _goal_tokens(str(organ.get("display_name") or ""))
    )
    if not name_tokens:
        return 0
    return len(
        {
            g
            for g in goal_tokens
            if any(_tokens_overlap(g, n) for n in name_tokens)
        }
    )


def _route_with_specific_relevant_organ(
    route: dict[str, Any], goal_tokens: list[str], inputs: dict[str, Any]
) -> dict[str, Any]:
    """
    [ACTION]
    Preserve a strongly matched relevant organ inside a matched task route.

    - Teleology: task routes are coarse groups, but the first-action contract is
      one concrete command. If the user's goal names a non-primary organ inside
      the matched route with at least two direct name-token hits, use that organ's
      runnable command and proof surfaces.
    - Guarantee: returns the original route unless a non-primary relevant organ
      from the route row or its join-index routes_to edges has a strictly
      stronger direct name match than the route primary; in that case returns a
      shallow route copy with primary_* and first_command fields rebound to the
      specific organ while preserving the task_class basis.
    - Fails: never raises.
    - Reads: call arguments only.
    - Writes: return values.
    """
    primary_id = str(route.get("primary_organ_id") or "")
    relevant = [o for o in (route.get("relevant_organs") or []) if isinstance(o, dict)]
    if not relevant:
        route_class = str(route.get("task_class") or "")
        organ_ids = [
            str(e.get("to") or "")
            for e in (inputs.get("join_index") or {}).get("edges") or []
            if isinstance(e, dict)
            and e.get("kind") == "routes_to"
            and str(e.get("from") or "") == route_class
            and e.get("to")
        ]
        for oid in organ_ids:
            row = dict((inputs.get("atlas_by_organ") or {}).get(oid) or {})
            row["organ_id"] = oid
            relevant.append(row)
    if not relevant:
        return route
    primary_row = next(
        (o for o in relevant if str(o.get("organ_id") or "") == primary_id),
        {
            "organ_id": primary_id,
            "display_name": route.get("primary_display_name"),
            "first_command": route.get("first_command"),
        },
    )
    primary_score = _organ_token_match_count(goal_tokens, primary_row)
    best_row = primary_row
    best_score = primary_score
    for row in relevant:
        score = _organ_token_match_count(goal_tokens, row)
        organ_id = str(row.get("organ_id") or "")
        best_id = str(best_row.get("organ_id") or "")
        if score > best_score or (
            score == best_score and score >= 2 and organ_id and organ_id < best_id
        ):
            best_score = score
            best_row = row
    best_id = str(best_row.get("organ_id") or "")
    if not best_id or best_id == primary_id or best_score < 2 or best_score <= primary_score:
        return route
    rebound = dict(route)
    rebound["route_primary_organ_id"] = primary_id
    rebound["matched_relevant_organ_id"] = best_id
    rebound["primary_organ_id"] = best_id
    rebound["primary_display_name"] = best_row.get("display_name") or best_id
    rebound["first_command"] = best_row.get("first_command") or route.get("first_command")
    rebound["drilldown_target"] = best_row.get("drilldown_target") or route.get(
        "drilldown_target"
    )
    rebound["receipt_ref"] = best_row.get("acceptance_ref") or route.get("receipt_ref")
    rebound["allowed_scope"] = (
        best_row.get("scope_limit")
        or best_row.get("claim_ceiling_restated")
        or route.get("allowed_scope")
    )
    return rebound


def _receipt_evidence(
    inputs: dict[str, Any], root: Path | None, organ_id: str
) -> dict[str, Any]:
    """
    [ACTION]
    Split an organ's receipt refs into shipped evidence vs provenance pointers.

    - Teleology: a contract must never tell a cold agent to expect a receipt the
      clone does not ship -- macrocosm adoption receipts (state/... paths) exist
      only upstream, and listing them as expected outputs makes a correct run
      look like a failure.
    - Guarantee: returns {committed_receipts (exist under root, authority first),
      provenance_receipts ([{path, exists_in_clone: False, note}]), all_refs};
      ordering is authority receipt first then emits_receipt edge targets,
      deduplicated.
    - Fails: never raises; a missing root existence-checks against the default root.
    - Reads: the in-memory inputs bundle + path existence under root.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    base = root or default_root()
    ordered = _organ_receipts(inputs, organ_id)
    committed: list[str] = []
    provenance: list[dict[str, Any]] = []
    for ref in ordered:
        if ref and (base / str(ref)).exists():
            committed.append(str(ref))
        elif ref:
            provenance.append(
                {
                    "path": str(ref),
                    "exists_in_clone": False,
                    "note": "provenance pointer (e.g. macrocosm adoption receipt); not shipped in this clone",
                }
            )
    return {
        "committed_receipts": committed,
        "provenance_receipts": provenance,
        "all_refs": ordered,
    }


_WRITE_FLAG_RE = re.compile(r"^--(?:[a-z0-9][a-z0-9-]*-)?out(?:=(?P<inline>.+))?$")


def _write_targets(command: str) -> list[tuple[str, str]]:
    """
    [ACTION]
    List every (flag, target) write destination a command names.

    - Teleology: footprint honesty must see EVERY write flag (--out,
      --acceptance-out, --out=DIR), not only the first --out, or a clean_run
      could claim a clean clone while a second flag still writes into
      committed paths.
    - Guarantee: returns (flag, target) pairs in argv order for every token
      matching --out / --<word>-out, accepting both the space and = forms;
      duplicate flags are all kept (argparse last-wins is the caller's
      concern).
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parts = str(command or "").split()
    targets: list[tuple[str, str]] = []
    for i, part in enumerate(parts):
        match = _WRITE_FLAG_RE.match(part)
        if not match:
            continue
        inline = match.group("inline")
        if inline is not None:
            targets.append((part.split("=", 1)[0], inline))
        elif i + 1 < len(parts):
            targets.append((part, parts[i + 1]))
    return targets


def _is_ignored_out_dir(path: str) -> bool:
    """
    [ACTION]
    Decide whether a write target stays outside the committed tree.

    - Teleology: the clean/dirty classification behind footprint honesty must
      be separator-aware and normalized, so `.microcosm/../receipts/x` or a
      hypothetical `.microcosm_extra/` cannot pass as clean.
    - Guarantee: True only for `<placeholder>` targets and normalized paths
      that are exactly .microcosm//tmp or sit under them.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    raw = str(path or "")
    if raw.startswith("<"):
        return True
    norm = posixpath.normpath(raw)
    return (
        norm == ".microcosm"
        or norm.startswith(".microcosm/")
        or norm == "/tmp"
        or norm.startswith("/tmp/")
    )


def _writes_outputs_under(command: str) -> str | None:
    """
    [ACTION]
    Extract the --out directory a first command writes fresh outputs under.

    - Teleology: distinguish "receipts this run will write" from committed
      prior-run evidence, so expected outputs are never conflated with shipped
      receipts.
    - Guarantee: returns the LAST --out target in the command (argparse
      last-wins), accepting both `--out DIR` and `--out=DIR`; None when the
      command names no --out flag.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    out_dir: str | None = None
    for flag, target in _write_targets(command):
        if flag == "--out":
            out_dir = target
    return out_dir


_CLEAN_RUN_OUT_ROOT = ".microcosm/first_action_runs"


def _clean_run_variant(command: str) -> dict[str, Any] | None:
    """
    [ACTION]
    Build the no-footprint variant of a first command that writes into the tree.

    - Teleology: the literal first action must not silently dirty a cold clone;
      when a first command's write flags land in committed receipt paths, the
      contract must carry a ready-to-run variant whose outputs land under the
      ignored .microcosm/ scratch tree instead.
    - Guarantee: returns {command, writes_outputs_under, note} with EVERY
      non-ignored write-flag target (--out / --<word>-out, space or = form)
      redirected to .microcosm/first_action_runs/<leaf>; returns None when the
      command names no write flag or every target is already ignored.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    targets = _write_targets(command)
    if not targets or all(_is_ignored_out_dir(t) for _f, t in targets):
        return None
    parts = str(command).split()
    for i, part in enumerate(parts):
        match = _WRITE_FLAG_RE.match(part)
        if not match:
            continue
        inline = match.group("inline")
        if inline is not None:
            if _is_ignored_out_dir(inline):
                continue
            leaf = inline.rstrip("/").rsplit("/", 1)[-1] or "run"
            parts[i] = f"{part.split('=', 1)[0]}={_CLEAN_RUN_OUT_ROOT}/{leaf}"
        elif i + 1 < len(parts):
            if _is_ignored_out_dir(parts[i + 1]):
                continue
            leaf = parts[i + 1].rstrip("/").rsplit("/", 1)[-1] or "run"
            parts[i + 1] = f"{_CLEAN_RUN_OUT_ROOT}/{leaf}"
    clean_command = " ".join(parts)
    return {
        "command": clean_command,
        "writes_outputs_under": _writes_outputs_under(clean_command)
        or _CLEAN_RUN_OUT_ROOT,
        "note": (
            "same run with outputs redirected to the ignored .microcosm/ tree; "
            "the committed receipts stay the comparison baseline and the clone "
            "stays clean"
        ),
    }


def _positive_why(inputs: dict[str, Any], organ_id: str, fallback: str = "") -> str:
    """
    [ACTION]
    Pick the POSITIVE purpose sentence for an organ (never a ceiling restatement).

    - Teleology: a first-action why must say what the action does FOR the goal;
      scope limits and ceilings belong in the boundary fields, not here.
    - Guarantee: returns the public synopsis, else the human gloss, else the
      agent gloss, else the supplied fallback.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    atlas_row = inputs.get("atlas_by_organ", {}).get(organ_id) or {}
    return str(
        inputs.get("synopsis_by_organ", {}).get(organ_id)
        or atlas_row.get("human_gloss")
        or atlas_row.get("agent_gloss")
        or fallback
    )


def compile_organ(inputs: dict[str, Any], organ_id: str) -> dict[str, Any]:
    """
    [ACTION]
    Compile the per-organ comprehension read pack.

    - Teleology: answer "what does this organ do, how do I run it, and what may I
      trust about it?" from the join index + atlas + synopsis, never the runner source.
    - Guarantee: returns an explanation-mode pack whose summary draws what_this_is from
      the synopsis + human_gloss, what_to_inspect_next from first_command + wires_to +
      resolved mechanism/concept refs, and what_not_to_trust from claim_ceiling_restated;
      selected_edges are every join edge touching the organ (runner/receipt/claim/
      family/wires/doctrine/inbound routes); reading_boundary carries the route-bound
      stop condition; source_span_escalation carries code_loci.
    - Fails: returns a not_found pack (mode reference) when the organ id is unknown.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never reads or returns runner source bodies or docstring atoms.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    atlas_row = inputs.get("atlas_by_organ", {}).get(organ_id)
    join_node = inputs.get("join_by_organ", {}).get(organ_id)
    synopsis = inputs.get("synopsis_by_organ", {}).get(organ_id, "")
    if atlas_row is None and join_node is None:
        pack = _pack_skeleton("reference", f"comprehend organ {organ_id}")
        pack["summary"]["what_this_is"] = f"No organ named {organ_id!r} in the atlas or join index."
        pack["summary"]["what_to_inspect_next"] = ["plectis comprehend --slice organs"]
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
    pack["selected_edges"] = _edges_touching(inputs.get("join_index"), organ_id)
    pack["evidence_refs"] = _organ_concept_refs(atlas_row)
    pack["receipt_refs"] = [
        e.get("to") for e in pack["selected_edges"] if e.get("kind") == "emits_receipt"
    ]
    pack["reading_boundary"] = _reading_boundary(inputs, organ_id)
    pack["specificity_risks"] = [_organ_specificity_risk(join_node)]
    pack["source_span_escalation"] = _organ_source_spans(atlas_row, join_node)
    return pack


def _organ_concept_refs(atlas_row: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    Collect an organ's resolved concept / paper-module / axiom / principle refs.

    - Teleology: give the organ pack its doctrine evidence handles for drilldown.
    - Guarantee: returns a flat, de-duplicated list of resolved ref strings plus the
      paper_module_ref when present.
    - Fails: never raises.
    - Reads: only the supplied atlas row.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Restate an organ's runner specificity + custody as a trust-risk note.

    - Teleology: tell the agent whether the organ's runner atoms are body-specific or
      whether the runner is an exact-copy macro body to be read only via metadata.
    - Guarantee: returns {runner_custody_basis, runner_specificity, note}; the note
      flags directory_coupling_marker runners as comprehend-via-metadata.
    - Fails: never raises.
    - Reads: only the supplied join node.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Build the organ's source-span escalation pointers from atlas code_loci.

    - Teleology: hand the agent exact path+symbol pointers to open ONLY when it must
      mutate or prove, keeping the default pack source-body-free.
    - Guarantee: returns a list of {path, symbols} from code_loci plus the resolved
      runner_source_ref; symbol lists are truncated to 12 names; no bodies included.
    - Fails: never raises.
    - Reads: only the supplied atlas row and join node.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Compile the authority/trust-boundary read pack.

    - Teleology: answer "what is authoritative vs projection, and what does passing
      NOT authorize?" -- the question a careful agent must resolve before acting.
    - Guarantee: returns a reference-mode pack carrying the evidence_class distribution,
      the per-organ claim ceilings, the global authority ceiling, the membrane bands,
      and the atlas authority_boundary + anti_claim.
    - Fails: never raises; absent inputs yield a degraded but valid pack.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never claims any release/source-export/whole-system authorization.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
        "plectis comprehend --organ <organ_id> for a single organ's ceiling",
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
    """
    [ACTION]
    Compile the organ roster read pack: one synopsis line per organ.

    - Teleology: give the agent the whole-category-at-a-glance roster so it can pick an
      organ to comprehend without scanning the registry.
    - Guarantee: returns a reference-mode pack whose selected_nodes list every organ's
      {organ_id, display_name, specialty, family, synopsis, evidence_class}.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    synopsis_by = inputs.get("synopsis_by_organ", {})
    organ_ids = sorted(set(atlas_by) | set(join_by))
    pack = _pack_skeleton("reference", "list all organs")
    pack["summary"]["what_this_is"] = f"{len(organ_ids)} organs, one synopsis line each."
    pack["summary"]["what_to_inspect_next"] = [
        "plectis comprehend --organ <organ_id>",
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


def _goal_path_token(token: str) -> str | None:
    """
    [ACTION]
    Return a normalized path-like token from a freeform goal, if present.
    - Teleology: Implements `_goal_path_token` for `microcosm_core.comprehension` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidate = token.strip("`'\".,;:!?()[]{}")
    if candidate.endswith(".py") or "/" in candidate:
        return candidate
    return None


def _is_path_target(target: Any) -> bool:
    """
    [ACTION]
    Return True when ``target`` is a source/path ref rather than an organ id.
    - Teleology: Implements `_is_path_target` for `microcosm_core.comprehension` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text = str(target or "")
    return bool(text) and (text.endswith(".py") or "/" in text)


def route_goal(goal: str, inputs: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """
    [ACTION]
    Route a freeform goal string to a comprehension packet mode + target.

    - Teleology: let a cold agent ask in words and still land on the right bounded
      packet -- the information-scent router behind --goal and the packet-route assay.
    - Guarantee: returns (mode, target, note); mode is a known packet mode; target is an
      organ id (organ/claim_trace/flow/mutation), a family (organ_cluster), or a path
      (path/mutation) when the goal names one; note is reserved for honest deferrals.
    - Fails: never raises; an empty/unknown goal routes to first-contact.
    - Reads: the in-memory inputs (organ id + family sets) only.
    - Non-goal: explicit CLI flags always override this fuzzy router.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values, declared filesystem outputs.
    """
    raw_text = goal or ""
    text = raw_text.lower()
    organ = next(
        (oid for oid in inputs.get("atlas_by_organ", {}) if oid.lower() in text), None
    )
    families = {str(r.get("family")) for r in inputs.get("atlas_by_organ", {}).values()}
    family = next(
        (f for f in families if f and (f in text or f.replace("_", " ") in text)), None
    )
    path = next(
        (path for tok in raw_text.split() if (path := _goal_path_token(tok))), None
    )
    if any(
        w in text
        for w in (
            "where do i start",
            "where should i start",
            "what should i do first",
            "what do i do first",
            "what should i run",
            "what do i run",
            "first action",
            "first command",
            "first step",
            "first correct action",
            "get started",
            "getting started",
            "start here",
        )
    ):
        return "first_action", goal, None
    if any(
        w in text
        for w in (
            "what should i work on",
            "what should we work on",
            "where should i work",
            "what part should",
            "most productive",
            "highest leverage",
            "high leverage",
            "best thing to improve",
            "what to improve",
            "next improvement",
            "improve microcosm",
            "microcosm release",
            "release comprehension",
            "release prep",
        )
    ):
        return "mutation_plan", organ or path, None
    # Word-boundary matching: house vocabulary like "fixture", "dispatch",
    # "exchange", and "editor" must NOT read as mutation intent.
    if re.search(r"\b(patch|change|fix|mutate|edit|modify|refactor)\b", text):
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
    """
    [ACTION]
    Extract ONE atom's bounded prose value from a docstring (local-band exporter).

    - Teleology: the sanctioned local exporter of a single authored atom's value, so
      a cold agent can read a symbol's Guarantee/Fails/Non-goal without opening source.
    - Guarantee: returns the stripped text following the first ``<atom>:`` line marker,
      joined across continuation lines up to the next atom marker or a blank line, then
      truncated to MAX_ATOM_CHARS with an ellipsis; "" when the atom is absent.
    - Fails: never raises (pure string scan).
    - Reads: only the supplied docstring.
    - Non-goal: never returns the whole docstring, the summary line, or source body;
      one bounded atom value only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Return a 12-hex provenance fingerprint over a symbol's emitted atom values.

    - Teleology: stamp each excerpt row so it is a drilldown hint tied to its source,
      not free-floating authority.
    - Guarantee: returns the first 12 hex chars of a sha256 over name + sorted values.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    blob = symbol_name + "|" + json.dumps(atom_values, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def extract_atom_excerpts(root: Path | None, rel_path: str) -> dict[str, Any]:
    """
    [ACTION]
    Extract bounded, custody-gated atom-value excerpts from ONE owned source file.

    - Teleology: activate the local_semantic_excerpt band -- turn a file's authored
      docstring atoms into a bounded local read model so the comprehend route is
      powered by real code semantics, not just atlas metadata.
    - Guarantee: returns a microcosm_atom_value_excerpt_v1 dict; emits symbol rows
      (name, source_span_ref, fingerprint, bounded atom_values) ONLY when the path is
      under src/microcosm_core/ AND the manifest custody oracle reports it owned
      (_custody_basis is None); secret-shaped or private-home-path atom values are
      dropped and counted, never emitted; emitted symbol rows are capped at
      MAX_EXCERPT_SYMBOLS and total row bytes are capped at MAX_EXCERPT_PACK_BYTES.
    - Fails: returns eligible=False with a reason for non-owned/custody-bound/unreadable
      paths; never raises.
    - Reads: the manifest custody oracle + the owned source file's docstrings only.
    - Writes: nothing.
    - Non-goal: never exports source bodies, the summary line, custody-bound runners,
      example/fixture/generated source, or anything into the public presence_only cache.
    - Escalates-to: project_substrate._load_manifest_custody_paths / _custody_basis as
      the authoritative custody signal.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
            "max_symbols": MAX_EXCERPT_SYMBOLS,
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
        atoms = ps._detect_docstring_atoms(doc)
        if not atoms:
            continue
        if len(result["symbols"]) >= MAX_EXCERPT_SYMBOLS:
            result["omitted_for_budget"] += 1
            continue
        atom_values: dict[str, str] = {}
        for atom in atoms:
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
    """
    [ACTION]
    Compile a local_semantic_excerpt read pack for one owned source file.

    - Teleology: the "read the code's self-description without opening the code"
      primitive -- surface an owned file's authored atoms as a bounded local read pack.
    - Guarantee: returns an explanation-mode pack with export_band=local_semantic_excerpt
      carrying semantic_excerpts (bounded atom values), a source-span escalation row, and
      an excerpt_guard; a non-eligible path yields found=False with the custody reason.
    - Fails: never raises.
    - Reads: extract_atom_excerpts for the file.
    - Non-goal: not a public-cache surface; this pack is local-only and never presence_only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
        pack["summary"]["what_to_inspect_next"] = ["plectis comprehend --slice organs"]
        pack["semantic_excerpts"] = []
        pack["excerpt_guard"] = {"custody_basis": excerpts["custody_basis"]}
        return pack
    pack["found"] = True
    count = excerpts["symbol_count"]
    omitted = int(excerpts.get("omitted_for_budget") or 0)
    budget_note = (
        f" ({omitted} additional symbol rows omitted by the local packet budget)"
        if omitted
        else ""
    )
    pack["summary"]["what_this_is"] = (
        f"{count} emitted authored-symbol excerpts in {rel}{budget_note}, read as "
        "bounded atom values (Teleology/Guarantee/Fails/...), no source bodies."
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
    """
    [ACTION]
    Enrich an organ pack with owned-source atom excerpts from its code_loci.

    - Teleology: let an organ pack carry the authored atoms of its OWNED governing
      code, while honestly noting that custody-bound runners stay behind the membrane.
    - Guarantee: flips export_band to local_semantic_excerpt and adds semantic_excerpts
      (owned code_loci paths with atom values) plus excerpt_custody_notes (the loci that
      are custody-bound / non-owned and therefore not excerpted).
    - Fails: never raises; an organ with no owned loci yields empty excerpts + notes.
    - Reads: extract_atom_excerpts per code_loci path.
    - Non-goal: never excerpts a custody-bound or non-owned locus.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    "full_local": {"target_bytes": 40000, "max_bytes": 64000},
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
        "command": "plectis comprehend --packet-atlas",
        "inputs": ["packet_specs"],
        "export_band": "presence_only",
        "cache_policy": "prebuilt",
        "cache_ref": "receipts/code_lens/read_packs/packet_atlas.json",
        "budget": "compact",
        "slo_ms": 200,
        "data_status": "full",
        "next_packets": ["first_action", "self_model", "first_contact", "authority", "organs_index"],
    },
    {
        "packet_id": "first_action",
        "packet_kind": "how_to",
        "mode": "first_action",
        "when_needed": "I have a goal: what is my FIRST correct action, who owns it, what proves it, where do I stop?",
        "command": 'plectis comprehend --first-action "<goal>"',
        "inputs": ["join_index", "organ_atlas", "synopses"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "compact",
        "slo_ms": 300,
        "data_status": "full",
        "next_packets": ["organ", "claim_trace", "flow", "mutation_plan", "packet_atlas"],
    },
    {
        "packet_id": "self_model",
        "packet_kind": "explanation",
        "mode": "self-model",
        "when_needed": "comprehend the WHOLE substrate at once: every family, what's real vs thin, what not to claim",
        "command": "plectis comprehend --self-model",
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
        "command": "plectis comprehend --first-contact",
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
        "command": "plectis comprehend --slice authority",
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
        "command": "plectis comprehend --slice organs",
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
        "command": "plectis comprehend --slice cluster --family <family>",
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
        "command": "plectis comprehend --organ <organ_id>",
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
        "command": "plectis comprehend --slice math",
        "inputs": ["join_index", "organ_atlas"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "standard",
        "slo_ms": 500,
        "data_status": "substantive_with_deferred_edges",
        "deferred_classes": ["proof_internal_structure"],
        "next_packets": ["organ", "claim_trace", "organ_cluster"],
    },
    {
        "packet_id": "claim_trace",
        "packet_kind": "proof_trace",
        "mode": "claim_trace",
        "when_needed": "how is a claim justified? claim -> validator -> receipt -> ceiling",
        "command": "plectis comprehend --slice claims --organ <organ_id>",
        "inputs": ["join_index", "organ_atlas"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "compact",
        "slo_ms": 300,
        "data_status": "substantive_with_deferred_edges",
        "deferred_classes": ["claim_node_ontology"],
        "next_packets": ["flow", "organ", "authority"],
    },
    {
        "packet_id": "flow",
        "packet_kind": "proof_trace",
        "mode": "flow",
        "when_needed": "how does execution flow? validator -> runner -> receipt",
        "command": "plectis comprehend --slice flows --organ <organ_id>",
        "inputs": ["join_index", "organ_atlas"],
        "export_band": "presence_only",
        "cache_policy": "on_demand",
        "cache_ref": None,
        "budget": "compact",
        "slo_ms": 300,
        "data_status": "substantive_with_deferred_edges",
        "deferred_classes": ["cross_organ_route_topology"],
        "next_packets": ["claim_trace", "organ", "mutation_plan"],
    },
    {
        "packet_id": "mutation_plan",
        "packet_kind": "how_to",
        "mode": "mutation_plan",
        "when_needed": "I want to change something safely: what to inspect, test, refresh",
        "command": "plectis comprehend --mutation <organ_id|path>",
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
        "command": "plectis comprehend --path <owned_file>",
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
    """
    [ACTION]
    Return the packet spec whose dispatch mode is ``mode`` (or None).

    - Teleology: let comprehend stamp a compiled pack with its packet identity/budget.
    - Guarantee: returns the spec dict for a known dispatch mode, else None.
    - Fails: never raises.
    - Reads: the in-memory _SPEC_BY_MODE map only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return _SPEC_BY_MODE.get(mode)


def _budget_for(spec: dict[str, Any]) -> dict[str, int]:
    """
    [ACTION]
    Resolve a spec's named budget band to {target_bytes, max_bytes}.

    - Teleology: turn the spec's symbolic budget band into concrete byte bounds.
    - Guarantee: returns the PACKET_BUDGETS entry, defaulting to the standard band.
    - Fails: never raises.
    - Reads: PACKET_BUDGETS only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return PACKET_BUDGETS.get(str(spec.get("budget")), PACKET_BUDGETS["standard"])


def _stamp_packet_identity(pack: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Stamp a compiled pack with its packet identity, byte-budget verdict, and scent.

    - Teleology: make every compiled pack self-describe as an atlas packet -- its id,
      kind, measured bytes vs budget, and the next_packets a reader should follow.
    - Guarantee: adds packet_id, packet_kind, next_packets, and a budget block with
      band/target/max/actual bytes and within_budget; returns the same pack.
    - Fails: never raises.
    - Reads: the spec and the pack's own serialized size.
    - Writes: mutates the pack in place.
    - Non-goal: never alters the pack's export_band or authority ceiling.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    """
    [ACTION]
    Collect the distinct resolved refs of ``key`` across organ rows, by frequency.

    - Teleology: surface the doctrine a family/cluster shares so its pack shows a spine.
    - Guarantee: returns resolved ref strings sorted by descending occurrence then name;
      handles list-valued fields (mechanism_refs) and scalar fields (paper_module_ref).
    - Fails: never raises.
    - Reads: only the supplied rows.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Compile the navigable packet menu -- the cold-agent first move.

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
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    root = inputs.get("root") or default_root()
    pack = _pack_skeleton("reference", "which comprehension packet should I use?")
    pack["schema_version"] = PACKET_ATLAS_SCHEMA
    pack["summary"]["what_this_is"] = (
        f"{len(PACKET_SPECS)} comprehension packets. Each is a bounded, source-body-free "
        "operating context for one situation. Have a goal? Enter through first_action "
        "(one graph-backed first correct action). Orienting cold? Enter through "
        "first_contact."
    )
    pack["summary"]["what_to_inspect_next"] = [
        _SPEC_BY_ID[i]["command"]
        for i in ("packet_atlas", "first_action", "self_model", "first_contact", "authority")
    ]
    pack["summary"]["what_not_to_trust"] = (
        "A packet is a navigation read model, never release/source-export/correctness "
        "authority; local_semantic_excerpt packets are local-only and never cached."
    )
    rows: list[dict[str, Any]] = []
    for spec in PACKET_SPECS:
        budget = _budget_for(spec)
        # data_status is COMPUTED from the live graph state when the spec names
        # deferred classes: a menu must not keep apologizing for edges the join
        # index now carries, nor advertise "full" over a degraded clone.
        deferred_classes = tuple(spec.get("deferred_classes") or ())
        if deferred_classes:
            still_deferred = _deferred_edges_for(inputs, deferred_classes)
            data_status = (
                "substantive_with_deferred_edges" if still_deferred else "full"
            )
        else:
            data_status = spec["data_status"]
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
            "data_status": data_status,
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
    # The goal-shaped entry: an agent that arrived WITH a goal should not read the
    # menu at all -- first_action converts the goal into one graph-backed contract.
    pack["goal_entry"] = "first_action"
    pack["slo_ms_by_packet"] = {s["packet_id"]: s["slo_ms"] for s in PACKET_SPECS}
    pack["sqlite_gate"] = SQLITE_GATE
    pack["evidence_refs"] = ["src/microcosm_core/comprehension.py#PACKET_SPECS"]
    return pack


def compile_organ_cluster(inputs: dict[str, Any], family: str) -> dict[str, Any]:
    """
    [ACTION]
    Compile the family/subsystem read pack -- the whole-family-at-once middle doll.

    - Teleology: answer "what is this subsystem and which organs compose it?" so an
      agent can grasp a family before drilling into one organ.
    - Guarantee: returns an explanation pack for the named family with member organs
      (id, display_name, specialty, evidence_class, synopsis), the shared mechanism/
      concept/paper refs, and the evidence-class distribution; returns a chooser pack
      (found False) listing all families when family is blank or unknown.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never reads runner source or docstring atoms.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
            f"plectis comprehend --slice cluster --family {entry['family']}"
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
        f"plectis comprehend --organ {m}" for m in members[:6]
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
        "axioms": _shared_refs(member_rows, "axiom_refs"),
        "principles": _shared_refs(member_rows, "principle_refs"),
        "paper_modules": _shared_refs(member_rows, "paper_module_ref"),
    }
    member_set = set(members)
    family_task_classes = sorted(
        {
            str(e.get("from"))
            for e in (inputs.get("join_index") or {}).get("edges") or []
            if isinstance(e, dict)
            and e.get("kind") == "routes_to"
            and e.get("to") in member_set
        }
    )
    if family_task_classes:
        pack["task_classes"] = family_task_classes
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
    """
    [ACTION]
    Compile the formal-math / proof surfaces read pack.

    - Teleology: answer "where is the mathematics/proof and what does it claim?" by
      gathering the formal_math_and_proof organs with their proof evidence and ceilings.
    - Guarantee: returns an explanation pack listing each proof-family organ's
      {organ_id, display_name, claim_ceiling, validator_command, paper_module_ref,
      evidence_class, receipt_count}, the shared proof mechanisms, and a deferred_edges
      block naming the proof-internal structure (theorem->lemma) still behind v1.
    - Fails: never raises; degrades to an empty member list if the family is absent.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never runs Lean, opens proof bodies, or asserts domain correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
        f"plectis comprehend --slice claims --organ {m}" for m in members[:4]
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
    pack["deferred_edges"] = _deferred_edges_for(inputs, ("proof_internal_structure",))
    return pack


def compile_claim_trace(inputs: dict[str, Any], target: str) -> dict[str, Any]:
    """
    [ACTION]
    Compile the claim-justification trace for one organ: claim -> validator -> receipt.

    - Teleology: answer "how is this organ's public claim justified, and what bounds it?"
      by chaining its claim ceiling to the validator command and the receipts it emits.
    - Guarantee: returns a proof_trace pack for ``target`` whose claim node is the
      join index's FIRST-CLASS claim node when the graph carries one (asserts_claim /
      validated_by / proven_by edges selected, graph_backed names the resolved class),
      degrading to a synthesized claim row -- with claim_node_ontology honestly
      re-deferred -- when the join index predates the v2 graph; always carries the
      validator_command, authority_receipt, emits_receipt edges, and evidence_class.
    - Fails: returns a chooser pack (found False) listing organs by ceiling when target
      is blank/unknown.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never opens validator source or receipt bodies; pointers only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    if not target or (target not in atlas_by and target not in join_by):
        pack = _pack_skeleton("reference", "choose an organ to trace")
        pack["found"] = False
        pack["summary"]["what_this_is"] = (
            "Name an organ to trace its claim -> validator -> receipt."
        )
        pack["summary"]["what_to_inspect_next"] = ["plectis comprehend --slice organs"]
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
        _runnable_command(join_node.get("validator_command"))
    ]
    pack["summary"]["what_not_to_trust"] = str(atlas_row.get("claim_ceiling_restated") or "")
    state = _graph_state(inputs)
    claim_node = next(
        (c for c in state["claim_nodes"] if c.get("organ_id") == target), None
    )
    # The POSITIVE claim statement: a cold reader must learn what is asserted, not
    # only what is disclaimed -- the ceiling fields are negative space.
    claim_statement = inputs.get("synopsis_by_organ", {}).get(target) or str(
        atlas_row.get("agent_gloss") or ""
    )
    if claim_node is not None:
        claim_row: dict[str, Any] = {
            "kind": "claim",
            "graph_backed": True,
            "claim_statement": claim_statement,
            **claim_node,
        }
    else:
        claim_row = {
            "kind": "claim",
            "graph_backed": False,
            "claim_statement": claim_statement,
            "organ_id": target,
            "claim_ceiling": join_node.get("claim_ceiling"),
            "claim_ceiling_restated": atlas_row.get("claim_ceiling_restated"),
            "evidence_class": join_node.get("evidence_class"),
            "evidence_strength_rank": join_node.get("evidence_strength_rank"),
            "truth_accounting_bucket": join_node.get("truth_accounting_bucket"),
        }
    pack["selected_nodes"] = [
        claim_row,
        {
            "kind": "validator",
            "validator_command": join_node.get("validator_command"),
            "runnable_command": _runnable_command(join_node.get("validator_command")),
            "note": "run this to re-establish the claim; it does not authorize release",
        },
    ]
    # Edge selection is purpose-filtered: the claim chain plus its receipts, not the
    # organ's whole neighborhood (that hub view belongs to the organ packet).
    claim_edge_kinds = ("asserts_claim", "validated_by", "proven_by", "emits_receipt")
    pack["edge_kinds_included"] = list(claim_edge_kinds)
    pack["selected_edges"] = [
        e
        for e in _edges_touching(inputs.get("join_index"), target)
        if e.get("kind") in claim_edge_kinds
    ]
    receipts = [
        e.get("to") for e in pack["selected_edges"] if e.get("kind") == "emits_receipt"
    ]
    authority = join_node.get("authority_receipt")
    if authority and authority not in receipts:
        receipts.insert(0, authority)
    pack["receipt_refs"] = receipts
    pack["source_span_escalation"] = _organ_source_spans(atlas_row, join_node)
    pack["graph_backed"] = _graph_backed_block(inputs, ("claim_node_ontology",))
    pack["deferred_edges"] = _deferred_edges_for(inputs, ("claim_node_ontology",))
    return pack


def compile_flow(inputs: dict[str, Any], target: str) -> dict[str, Any]:
    """
    [ACTION]
    Compile the execution-flow trace for one organ: validator -> runner -> receipt.

    - Teleology: answer "how does this organ run and what does it leave behind?" by
      ordering its validator command, runner module, and emitted receipts.
    - Guarantee: returns a proof_trace pack for ``target`` whose selected_nodes are the
      ordered flow stages (validator -> runner/custody -> receipts) PLUS, when the
      join index carries the v2 route plane, a route_context row (the task-class
      routes landing on the organ, with stop conditions) and a wired_neighbors row
      (wires_to topology in both directions); deferred_edges re-defers
      cross_organ_route_topology honestly when the route plane is absent.
    - Fails: returns a chooser pack (found False) when target is blank/unknown.
    - Reads: the in-memory inputs bundle only.
    - Non-goal: never opens runner source; it orders pointers, not bodies.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    if not target or (target not in atlas_by and target not in join_by):
        pack = _pack_skeleton("reference", "choose an organ flow")
        pack["found"] = False
        pack["summary"]["what_this_is"] = (
            "Name an organ to order its validator -> runner -> receipt flow."
        )
        pack["summary"]["what_to_inspect_next"] = ["plectis comprehend --slice organs"]
        pack["selected_nodes"] = [
            {"organ_id": oid} for oid in sorted(set(atlas_by) | set(join_by))[:20]
        ]
        return pack
    atlas_row = atlas_by.get(target) or {}
    join_node = join_by.get(target) or {}
    # Edge selection is purpose-filtered to the execution/topology kinds; the full
    # neighborhood (claim chain, doctrine refs) lives on the organ packet.
    flow_edge_kinds = ("implemented_by_runner", "emits_receipt", "wires_to", "routes_to")
    edges = [
        e
        for e in _edges_touching(inputs.get("join_index"), target)
        if e.get("kind") in flow_edge_kinds
    ]
    receipts = [e.get("to") for e in edges if e.get("kind") == "emits_receipt"]
    pack = _pack_skeleton("proof_trace", f"trace the flow for {target}")
    pack["found"] = True
    pack["organ_id"] = target
    pack["edge_kinds_included"] = list(flow_edge_kinds)
    pack["summary"]["what_this_is"] = (
        f"Execution flow for {target}: run the validator, it exercises the runner, which "
        f"emits {len(receipts)} receipt(s)."
    )
    pack["summary"]["what_to_inspect_next"] = [
        _runnable_command(join_node.get("validator_command"))
    ]
    pack["summary"]["what_not_to_trust"] = str(atlas_row.get("claim_ceiling_restated") or "")
    pack["selected_nodes"] = [
        {
            "kind": "flow_stage",
            "stage": 1,
            "role": "validator",
            "command": join_node.get("validator_command"),
            "runnable_command": _runnable_command(join_node.get("validator_command")),
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
    routes = _routes_serving(inputs, target)
    if routes:
        pack["selected_nodes"].append(
            {
                "kind": "route_context",
                "note": "task-class entry points whose fan-out lands on this organ",
                "routes": routes,
            }
        )
    wires_out = [e.get("to") for e in edges if e.get("kind") == "wires_to" and e.get("from") == target]
    wires_in = [e.get("from") for e in edges if e.get("kind") == "wires_to" and e.get("to") == target]
    if wires_out or wires_in:
        pack["selected_nodes"].append(
            {
                "kind": "wired_neighbors",
                "wires_to": wires_out,
                "wired_from": wires_in,
                "drilldown": "plectis comprehend --slice flows --organ <neighbor>",
            }
        )
    pack["selected_edges"] = edges
    pack["receipt_refs"] = receipts
    pack["reading_boundary"] = _reading_boundary(inputs, target)
    pack["source_span_escalation"] = _organ_source_spans(atlas_row, join_node)
    pack["graph_backed"] = _graph_backed_block(inputs, ("cross_organ_route_topology",))
    pack["deferred_edges"] = _deferred_edges_for(inputs, ("cross_organ_route_topology",))
    return pack


def _goal_tokens(text: str) -> list[str]:
    """
    [ACTION]
    Tokenize a freeform goal for route matching (lowercase, len >= 3).

    - Teleology: one tokenizer shared by the route matcher so scoring is
      deterministic and testable.
    - Guarantee: returns lowercase alphanumeric tokens of length >= 3 in order.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) >= 3]


def _tokens_overlap(a: str, b: str) -> bool:
    """
    [ACTION]
    Loose token match: equality, >=4-char prefix, or >=6-char common prefix.

    - Teleology: let "start" reach "started" AND "evaluate" reach "evaluation"
      without a stemmer dependency.
    - Guarantee: True iff tokens are equal, one is a >=4-char prefix of the other,
      or the two share a common prefix of length >= 6 (which bridges
      evaluate/evaluation while keeping short common words apart).
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if a == b:
        return True
    if (len(a) >= 4 and b.startswith(a)) or (len(b) >= 4 and a.startswith(b)):
        return True
    common = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        common += 1
    return common >= 6


# Verbs that signal the goal actually asks to RUN/CHECK something -- the evidence a
# single-token route match needs before it may fire (see _match_task_route).
_ACTION_VERB_RE = re.compile(
    r"\b(run|check|validate|inspect|test|replay|show|verify|exercise|dispatch)\b"
)


def _match_task_route(goal: str, inputs: dict[str, Any]) -> dict[str, Any] | None:
    """
    [ACTION]
    Match a freeform goal to the best task-class route node in the graph.

    - Teleology: the goal->route half of the first-action compiler -- the route
      plane already encodes 'which organ owns this kind of task', so a goal that
      names a task class (lean, security, finance, getting started...) should land
      on that route's first command, not on a generic orientation packet.
    - Guarantee: returns the best-scoring route node dict, scored by token overlap
      with task_class (weight 3), primary_display_name (2), primary_organ_id (2),
      and first_command (1). EVIDENCE BAR: a route fires when >= 2 DISTINCT goal
      tokens matched strong route fields, when exactly one strong token equals the
      full task_class name (len >= 5) AND the goal carries an action verb
      (run/check/validate/...), or when >= 2 tokens match the first command and
      the goal carries an action verb. That lets "dispatch the route bundle"
      reach the graph-owned route-map command while "does this work?" or "the
      security guard at my office building" fall to orientation fallback instead
      of a confident wrong fixture. When the matched route contains a relevant
      non-primary organ that the goal names more specifically, the returned route
      is rebound to that organ's first command while preserving the task-class
      route basis. Returns None below the bar or when the route plane is absent;
      ties break by score then task_class name for determinism.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    tokens = _goal_tokens(goal)
    if not tokens:
        return None
    has_action_verb = bool(_ACTION_VERB_RE.search((goal or "").lower()))
    best: tuple[int, str, dict[str, Any]] | None = None
    for route in _graph_state(inputs)["route_nodes"]:
        task_class = str(route.get("task_class") or "")
        score = 0
        matched_goal_tokens: set[str] = set()
        strong_matched_goal_tokens: set[str] = set()
        for field, weight in (
            ("task_class", 3),
            ("primary_display_name", 2),
            ("primary_organ_id", 2),
            ("first_command", 1),
        ):
            for ftok in _goal_tokens(str(route.get(field) or "")):
                hits = [g for g in tokens if _tokens_overlap(ftok, g)]
                if hits:
                    score += weight
                    matched_goal_tokens.update(hits)
                    if field != "first_command":
                        strong_matched_goal_tokens.update(hits)
        if not matched_goal_tokens:
            continue
        route_can_fire = len(strong_matched_goal_tokens) >= 2
        if not route_can_fire and len(strong_matched_goal_tokens) == 1:
            only = next(iter(strong_matched_goal_tokens))
            exact_class = only == task_class and len(only) >= 5
            route_can_fire = exact_class and has_action_verb
        if not route_can_fire and has_action_verb and len(matched_goal_tokens) >= 2:
            route_can_fire = True
        if not route_can_fire:
            continue
        if best is None or (-score, task_class) < (-best[0], best[1]):
            best = (
                score,
                task_class,
                _route_with_specific_relevant_organ(route, tokens, inputs),
            )
    return best[2] if best else None


def _custody_do_not_edit(join_node: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Build the do-not-edit boundary for an organ's runner custody.

    - Teleology: a first-action contract must say what the agent may NOT touch
      before it says what to run.
    - Guarantee: returns {paths, note}; a custody-bound runner lists its
      runner_source_ref and an exact-copy warning, an owned runner returns an
      empty list with the validator-required note.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if join_node.get("runner_custody_basis") == "directory_coupling_marker":
        paths = [p for p in [join_node.get("runner_source_ref")] if p]
        return {
            "paths": paths,
            "note": (
                "runner is an exact-copy macro body: do NOT edit it in place; "
                "change the upstream source module via the refresh lane"
            ),
        }
    return {
        "paths": [],
        "note": "runner is owned; edits still require the validator + refreshed receipts",
    }


def _organ_receipts(inputs: dict[str, Any], organ_id: str) -> list[str]:
    """
    [ACTION]
    Collect an organ's receipt refs (authority receipt first, deduplicated).

    - Teleology: the expected-receipts half of a first-action proof path.
    - Guarantee: returns the authority receipt (when present) followed by the
      organ's emits_receipt edge targets, without duplicates.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    join_node = inputs.get("join_by_organ", {}).get(organ_id) or {}
    receipts = [
        e.get("to")
        for e in _edges_touching(inputs.get("join_index"), organ_id)
        if e.get("kind") == "emits_receipt"
    ]
    authority = join_node.get("authority_receipt")
    if authority and authority not in receipts:
        receipts.insert(0, authority)
    return receipts


def _first_action_owner(
    inputs: dict[str, Any], organ_id: str, task_class: str | None
) -> dict[str, Any]:
    """
    [ACTION]
    Build the owner block for a first-action contract.

    - Teleology: name WHO owns the first action -- organ, display name, family,
      custody -- so the agent can localize before it runs anything.
    - Guarantee: returns {organ_id, display_name, family, runner_custody_basis,
      evidence_class, task_class}; absent fields become None.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    atlas_row = inputs.get("atlas_by_organ", {}).get(organ_id) or {}
    join_node = inputs.get("join_by_organ", {}).get(organ_id) or {}
    return {
        "organ_id": organ_id,
        "display_name": atlas_row.get("display_name"),
        "family": atlas_row.get("family") or join_node.get("family"),
        "runner_custody_basis": join_node.get("runner_custody_basis"),
        "evidence_class": join_node.get("evidence_class"),
        "task_class": task_class,
    }


def _first_action_path_contract(
    inputs: dict[str, Any], goal: str, path: str, *, mutation: bool
) -> dict[str, Any]:
    """
    [ACTION]
    Build a first-action contract that preserves a named path target.
    - Teleology: Implements `_first_action_path_contract` for `microcosm_core.comprehension` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mode = "mutation_plan" if mutation else "path"
    command_flag = "--mutation" if mutation else "--path"
    command = _runnable_command(f"plectis comprehend {command_flag} {path}")
    pack = _pack_skeleton("how_to", goal or path)
    pack["found"] = True
    pack["graph_backed"] = _graph_backed_block(inputs, _FIRST_ACTION_GRAPH_CLASSES)
    pack["deferred_edges"] = _deferred_edges_for(inputs, _FIRST_ACTION_GRAPH_CLASSES)
    pack["routing"] = {
        "basis": "path_mutation_goal" if mutation else "path_reference_goal",
        "mode": mode,
        "target": path,
    }
    pack["summary"]["what_this_is"] = (
        f"First-action contract for the named path {path}: open its "
        f"{mode} packet before drawing broader conclusions."
    )
    pack["summary"]["what_not_to_trust"] = (
        "This contract preserves a requested path target; it does not authorize "
        "release, source-body export, static-analysis correctness, or edits before "
        "a Work Ledger claim and validator run."
    )
    pack["summary"]["what_to_inspect_next"] = [path, command]
    if mutation:
        pack["first_action"] = {
            "action_kind": "inspect_mutation_target",
            "command": command,
            "target": path,
            "claim_paths": [path],
            "validation_commands": [
                "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --packet-route",
                "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --whole-system",
            ],
            "why": (
                "The goal names a concrete path with mutation intent; inspect that "
                "path's mutation plan before claiming or editing it."
            ),
            "committed_receipts": [],
        }
        pack["owner"] = {
            "scope": "path_mutation_plan",
            "target": path,
            "claim_paths": [path],
            "packet_id": "mutation_plan",
        }
        pack["proof_path"] = {
            "validation_commands": list(pack["first_action"]["validation_commands"]),
            "receipt_refs": [],
            "note": "the next mutation-plan packet names the concrete validators for this path",
        }
        pack["reading_boundary"] = {
            "stop_condition": (
                "Stop after the mutation plan names owned paths and validators; "
                "claim the path before editing."
            ),
            "task_classes": [],
            "source": "comprehension-layer path-target preservation",
        }
        pack["do_not_claim"] = (
            "A path-specific mutation first action is not edit authority, release "
            "approval, or correctness proof."
        )
        pack["do_not_edit"] = {
            "paths": [],
            "note": "do not edit the named path until a Work Ledger claim and preflight pass",
        }
    else:
        pack["first_action"] = {
            "action_kind": "open_packet",
            "command": command,
            "target": path,
            "why": (
                "The goal names a concrete path without mutation intent; open the "
                "bounded path packet instead of matching an unrelated task route."
            ),
            "committed_receipts": [],
        }
        pack["owner"] = {
            "scope": "owned_source_path",
            "target": path,
            "packet_id": "path",
        }
        pack["proof_path"] = {
            "validation_commands": [
                "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --packet-route",
            ],
            "receipt_refs": [],
            "note": "the path packet is the bounded local read surface; it remains source-body-free",
        }
        pack["reading_boundary"] = {
            "stop_condition": (
                "Stop at the bounded path packet; open source only to prove or mutate "
                "under the mutation contract."
            ),
            "task_classes": [],
            "source": "comprehension-layer path-target preservation",
        }
        pack["do_not_claim"] = (
            "A path first action is a bounded read route only; it is not release "
            "approval, source-body export, or static-analysis authority."
        )
        pack["do_not_edit"] = {
            "paths": [],
            "note": "read-only path contracts do not authorize edits",
        }
    pack["next_packet_commands"] = [command]
    return pack


def compile_first_action(
    inputs: dict[str, Any], root: Path | None, goal: str
) -> dict[str, Any]:
    """
    [ACTION]
    Compile the First Correct Action contract for a freeform cold-agent goal.

    - Teleology: convert a cold agent from "what is this?" to its FIRST CORRECT
      ACTION -- one graph-backed contract naming the action, the owner, the
      validator/receipt proof path, the stop condition, the authority ceiling,
      and the do-not-edit boundary -- instead of handing the agent a map pile.
    - Guarantee: returns a how_to pack with first_action {action_kind, command
      (cold-runnable), why, expected_receipts}, owner, proof_path, reading_boundary,
      do_not_claim, do_not_edit, if_this_is_wrong, routing (how the goal was
      resolved), graph_backed, and computed deferred_edges. Resolution order:
      organ named in the goal -> organ contract; improvement/patch-shaped goal ->
      inspect-the-ranked-target contract; task-class route match -> route-first-
      command contract; otherwise -> the routed packet as an open_packet contract.
      A blank goal returns a chooser (found False) listing the task classes.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only (plus filesystem existence via the
      improvement ranker).
    - Non-goal: never instructs an edit, never exports source bodies, never
      grants release/correctness authority; the contract is navigation + proof
      pointers only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    base = root or default_root()
    atlas = inputs.get("atlas") or {}
    atlas_by = inputs.get("atlas_by_organ", {})
    state = _graph_state(inputs)
    text = (goal or "").lower()

    pack = _pack_skeleton("how_to", goal or "choose a first action")
    pack["summary"]["what_not_to_trust"] = (
        "This contract routes and proves; it does not authorize release, edits, "
        "or correctness. Run the proof path before trusting the action's result."
    )
    pack["graph_backed"] = _graph_backed_block(
        inputs, ("cross_organ_route_topology", "claim_node_ontology")
    )
    pack["deferred_edges"] = _deferred_edges_for(
        inputs, ("cross_organ_route_topology", "claim_node_ontology")
    )
    pack["if_this_is_wrong"] = [
        "plectis comprehend --packet-atlas",
        'plectis comprehend --goal "<rephrase your goal>"',
    ]

    if not text.strip():
        pack["found"] = False
        pack["summary"]["what_this_is"] = (
            "Name a goal to get a first-action contract. The graph carries "
            f"{len(state['route_nodes'])} task-class routes."
        )
        pack["selected_nodes"] = [
            {
                "kind": "task_class",
                "task_class": r.get("task_class"),
                "primary_organ_id": r.get("primary_organ_id"),
                "primary_display_name": r.get("primary_display_name"),
            }
            for r in state["route_nodes"]
        ]
        pack["summary"]["what_to_inspect_next"] = [
            'plectis comprehend --first-action "where do I start?"'
        ]
        return pack

    pack["found"] = True

    # RUNG 1 -- destructive/publication intent routes to the AUTHORITY packet,
    # never to a fixture or mutation command: the substrate cannot grant what the
    # goal asks for, and the contract's first action is to read that boundary.
    if any(
        tok.startswith(("delet", "destroy", "wipe", "publish", "deploy", "production"))
        for tok in _goal_tokens(text)
    ) or any(ph in text for ph in ("force push", "force-push", "rm -rf", "make public")):
        auth_spec = _SPEC_BY_ID["authority"]
        cache_ref = auth_spec.get("cache_ref")
        cache_exists = bool(cache_ref) and (base / str(cache_ref)).exists()
        pack["routing"] = {"basis": "out_of_scope_authority_boundary"}
        pack["out_of_scope_note"] = (
            "Destructive or publication actions are outside this contract's "
            "authority (authority_ceiling is all false and cannot grant them). "
            "The named first action is a read-only comprehension move only."
        )
        pack["summary"]["what_this_is"] = (
            "This goal asks for an action the substrate cannot grant; the first "
            "correct action is to read the authority boundary."
        )
        pack["first_action"] = {
            "action_kind": "open_packet",
            "command": _runnable_command(auth_spec["command"]),
            "why": auth_spec["when_needed"],
            "committed_receipts": [str(cache_ref)] if cache_exists else [],
        }
        pack["owner"] = {"scope": "whole_substrate", "packet_id": "authority"}
        pack["proof_path"] = {
            "validation_commands": [
                "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --whole-system",
            ],
            "receipt_refs": [str(cache_ref)] if cache_exists else [],
            "note": "the authority packet IS the boundary evidence; the whole-system assay proves overclaim_count == 0",
        }
        pack["reading_boundary"] = {
            "stop_condition": (
                "Stop at the authority ceiling: this substrate cannot grant "
                "destructive or publication actions."
            ),
            "task_classes": [],
            "source": "comprehension-layer guidance",
        }
        pack["do_not_claim"] = str(atlas.get("anti_claim") or "")
        pack["do_not_edit"] = {
            "paths": [],
            "note": "no edit, deletion, or publication is authorized by this contract",
        }
        return pack

    organs = _resolve_goal_organs(goal, inputs)
    organ_target = organs["selected"]
    mode, _rg_target, _note = route_goal(goal, inputs)
    if not organ_target and mode in ("path", "mutation_plan") and _is_path_target(_rg_target):
        return _first_action_path_contract(
            inputs, goal, str(_rg_target), mutation=(mode == "mutation_plan")
        )
    # Start-shaped intent maps deterministically to the getting-started route
    # when the graph carries one; otherwise the generic matcher gets its chance.
    route = None
    if mode == "first_action":
        route = next(
            (
                r
                for r in state["route_nodes"]
                if r.get("task_class") == "getting-started"
            ),
            None,
        )
    if route is None:
        route = _match_task_route(goal, inputs)

    if organ_target:
        atlas_row = atlas_by.get(organ_target) or {}
        join_node = inputs.get("join_by_organ", {}).get(organ_target) or {}
        routes = _routes_serving(inputs, organ_target)
        first_command = atlas_row.get("first_command") or (
            routes[0].get("first_command") if routes else None
        )
        runnable = _runnable_command(first_command)
        evidence = _receipt_evidence(inputs, base, organ_target)
        pack["routing"] = {
            "basis": "organ_named_in_goal",
            "organ_id": organ_target,
            "also_named": organs["also_named"],
            "excluded_by_negation": organs["excluded"],
        }
        pack["summary"]["what_this_is"] = (
            f"First-action contract for organ {organ_target}: run its first "
            "command, prove it with the validator, stop at the route boundary."
        )
        pack["first_action"] = {
            "action_kind": "run_fixture_command",
            "command": runnable,
            "why": _positive_why(inputs, organ_target),
            "committed_receipts": evidence["committed_receipts"],
            "writes_outputs_under": _writes_outputs_under(runnable),
        }
        clean_run = _clean_run_variant(runnable)
        if clean_run:
            pack["first_action"]["clean_run"] = clean_run
        pack["owner"] = _first_action_owner(
            inputs, organ_target, routes[0]["task_class"] if routes else None
        )
        pack["proof_path"] = {
            "validator_command": join_node.get("validator_command"),
            "runnable_validator": _runnable_command(join_node.get("validator_command")),
            "receipt_refs": evidence["committed_receipts"],
            "provenance_receipts": evidence["provenance_receipts"],
            "authority_receipt": join_node.get("authority_receipt"),
        }
        pack["reading_boundary"] = _reading_boundary(inputs, organ_target)
        pack["do_not_claim"] = str(
            atlas_row.get("claim_ceiling_restated") or atlas.get("anti_claim") or ""
        )
        pack["do_not_edit"] = _custody_do_not_edit(join_node)
        pack["next_packet_commands"] = [
            f"plectis comprehend --slice claims --organ {organ_target}",
            f"plectis comprehend --slice flows --organ {organ_target}",
        ]
        return pack

    if route is not None:
        primary = str(route.get("primary_organ_id") or "")
        join_node = inputs.get("join_by_organ", {}).get(primary) or {}
        runnable = _runnable_command(route.get("first_command"))
        evidence = _receipt_evidence(inputs, base, primary)
        pack["routing"] = {
            "basis": "task_class_route_match",
            "task_class": route.get("task_class"),
        }
        pack["summary"]["what_this_is"] = (
            f"First-action contract via the {route.get('task_class')} route: run "
            "the route's first command against its primary organ, then stop at "
            "the route's stop condition."
        )
        pack["first_action"] = {
            "action_kind": "run_fixture_command",
            "command": runnable,
            "why": _positive_why(inputs, primary, fallback=str(route.get("allowed_scope") or "")),
            "committed_receipts": evidence["committed_receipts"],
            "writes_outputs_under": _writes_outputs_under(runnable),
        }
        clean_run = _clean_run_variant(runnable)
        if clean_run:
            pack["first_action"]["clean_run"] = clean_run
        pack["owner"] = _first_action_owner(inputs, primary, str(route.get("task_class")))
        pack["proof_path"] = {
            "validator_command": join_node.get("validator_command"),
            "runnable_validator": _runnable_command(join_node.get("validator_command")),
            "receipt_refs": evidence["committed_receipts"],
            "provenance_receipts": evidence["provenance_receipts"],
            "authority_receipt": join_node.get("authority_receipt"),
        }
        if route.get("matched_relevant_organ_id"):
            pack["reading_boundary"] = _reading_boundary(inputs, primary)
            if route.get("allowed_scope"):
                pack["reading_boundary"]["allowed_scope"] = route.get("allowed_scope")
            pack["reading_boundary"]["task_classes"] = [route.get("task_class")]
            pack["reading_boundary"]["source"] = (
                "join_index nodes.route (atlas/agent_task_routes.json)"
            )
        else:
            pack["reading_boundary"] = {
                "stop_condition": route.get("stop_condition"),
                "allowed_scope": route.get("allowed_scope"),
                "task_classes": [route.get("task_class")],
                "source": "join_index nodes.route (atlas/agent_task_routes.json)",
            }
        pack["do_not_claim"] = str(
            (atlas_by.get(primary) or {}).get("claim_ceiling_restated")
            or atlas.get("anti_claim")
            or ""
        )
        pack["do_not_edit"] = _custody_do_not_edit(join_node)
        pack["next_packet_commands"] = [
            f"plectis comprehend --organ {primary}",
            f"plectis comprehend --slice claims --organ {primary}",
        ]
        return pack

    if mode == "mutation_plan":
        targets = _release_improvement_targets(inputs, base)
        rank1 = targets[0]
        next_action = _improvement_next_action(rank1)
        pack["routing"] = {"basis": "improvement_goal", "rank1_target": rank1["target"]}
        pack["summary"]["what_this_is"] = (
            "First-action contract for an improvement goal: inspect the rank-1 "
            "target's mutation plan BEFORE editing anything."
        )
        pack["first_action"] = {
            **next_action,
            "why": rank1["why"],
            "committed_receipts": [],
        }
        pack["owner"] = {
            "scope": "release_improvement",
            "target": rank1["target"],
            "title": rank1["title"],
            "claim_paths": list(next_action["claim_paths"]),
        }
        pack["proof_path"] = {
            "validation_commands": list(rank1.get("validation_commands") or []),
            "receipt_refs": [],
            "note": "run every validation command after the change; assays must stay green",
        }
        pack["reading_boundary"] = {
            "stop_condition": (
                "Stop planning when the mutation plan names the owned paths, the "
                "validator, and the receipts to refresh; any edit beyond that "
                "point is governed by the mutation plan's custody flags, not by "
                "this contract."
            ),
            "task_classes": [],
            "source": "comprehension-layer guidance",
        }
        pack["do_not_claim"] = (
            "Improvement ranking is a work plan, not release approval or a claim "
            "that the substrate is complete."
        )
        pack["do_not_edit"] = {
            "paths": [],
            "note": "do not edit exact-copy macro runners; the mutation plan flags custody per file",
        }
        pack["next_packet_commands"] = [
            "PYTHONPATH=src python3 -m microcosm_core comprehend --improvements"
        ]
        return pack

    # RUNG: fuzzy subject-matter match against organ names -- "evaluate prompt
    # injection defenses" should reach the owning organ, not be told it is
    # orientation-shaped.
    token_organ = _match_organ_tokens(goal, inputs)
    if token_organ:
        join_node = inputs.get("join_by_organ", {}).get(token_organ) or {}
        atlas_row = atlas_by.get(token_organ) or {}
        runnable = _runnable_command(atlas_row.get("first_command"))
        evidence = _receipt_evidence(inputs, base, token_organ)
        routes = _routes_serving(inputs, token_organ)
        pack["routing"] = {"basis": "organ_token_match", "organ_id": token_organ}
        pack["summary"]["what_this_is"] = (
            f"First-action contract: the goal's subject matter matches organ "
            f"{token_organ}; run its first command and stop at its boundary."
        )
        pack["first_action"] = {
            "action_kind": "run_fixture_command",
            "command": runnable,
            "why": _positive_why(inputs, token_organ),
            "committed_receipts": evidence["committed_receipts"],
            "writes_outputs_under": _writes_outputs_under(runnable),
        }
        clean_run = _clean_run_variant(runnable)
        if clean_run:
            pack["first_action"]["clean_run"] = clean_run
        pack["owner"] = _first_action_owner(
            inputs, token_organ, routes[0]["task_class"] if routes else None
        )
        pack["proof_path"] = {
            "validator_command": join_node.get("validator_command"),
            "runnable_validator": _runnable_command(join_node.get("validator_command")),
            "receipt_refs": evidence["committed_receipts"],
            "provenance_receipts": evidence["provenance_receipts"],
            "authority_receipt": join_node.get("authority_receipt"),
        }
        pack["reading_boundary"] = _reading_boundary(inputs, token_organ)
        pack["do_not_claim"] = str(
            atlas_row.get("claim_ceiling_restated") or atlas.get("anti_claim") or ""
        )
        pack["do_not_edit"] = _custody_do_not_edit(join_node)
        pack["next_packet_commands"] = [
            f"plectis comprehend --organ {token_organ}",
        ]
        return pack

    spec = _SPEC_BY_MODE.get(mode) or _SPEC_BY_MODE["first-contact"]
    # A first action must be runnable VERBATIM: a routed packet whose command
    # still carries a <placeholder> (no target resolved) falls back to the
    # always-concrete packet atlas menu instead of handing out a template.
    if "<" in str(spec.get("command") or ""):
        spec = _SPEC_BY_ID["packet_atlas"]
    cache_ref = spec.get("cache_ref")
    cache_exists = bool(cache_ref) and (base / str(cache_ref)).exists()
    pack["routing"] = {"basis": "packet_fallback", "packet_id": spec["packet_id"]}
    # Honest fallback wording: no route matched -- do not assert the goal itself
    # was orientation-shaped.
    pack["summary"]["what_this_is"] = (
        "No task-class route or organ matched this goal; opening the "
        f"{spec['packet_id']} packet is the safe default first action."
    )
    pack["first_action"] = {
        "action_kind": "open_packet",
        "command": _runnable_command(spec["command"]),
        "why": spec["when_needed"],
        "committed_receipts": [str(cache_ref)] if cache_exists else [],
    }
    pack["owner"] = {"scope": "whole_substrate", "packet_id": spec["packet_id"]}
    pack["proof_path"] = {
        "validation_commands": [
            "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --packet-route",
        ],
        "receipt_refs": [str(cache_ref)] if cache_exists else [],
        "note": "the packet IS the evidence surface; the assay proves the menu routes",
    }
    pack["reading_boundary"] = {
        "stop_condition": (
            "Stop when the packet answers your question and you have chosen one "
            "next_packet; if it does not, open --packet-atlas."
        ),
        "task_classes": [],
        "source": "comprehension-layer guidance",
    }
    pack["do_not_claim"] = str(atlas.get("anti_claim") or "")
    pack["do_not_edit"] = {
        "paths": [],
        "note": "orientation goals never require edits",
    }
    # Explicit ids, not a positional slice: the fallback menu must stay
    # placeholder-free and must not suggest re-running the mode that just fell
    # back (first_action's own command carries "<goal>").
    pack["next_packet_commands"] = [
        _SPEC_BY_ID[i]["command"] for i in ("packet_atlas", "self_model", "first_contact")
    ]
    return pack


def _release_improvement_targets(
    inputs: dict[str, Any], root: Path | None
) -> list[dict[str, Any]]:
    """
    [ACTION]
    Return ranked concrete edit targets for release-comprehension work.

    - Teleology: make a vague "what should I work on?" prompt actionable for a cold
      agent by pointing at the real files and tests that change clone comprehension.
    - Guarantee: returns ranked target rows with path, reason, validation commands,
      and expected reader-visible effect; rows are derived from packet/deferred-edge
      state and fixed public front-door surfaces, never from source bodies.
    - Fails: never raises; path existence is advisory metadata only.
    - Reads: only in-memory inputs plus filesystem existence checks.
    - Non-goal: does not claim release authority or mutate anything.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    base = root or default_root()
    join_organs = list(inputs.get("join_by_organ", {}).values())
    rollup = ((inputs.get("join_index") or {}).get("rollup")) or {}
    organ_count = (
        len(inputs.get("atlas_by_organ", {}))
        or rollup.get("organ_count")
        or len(join_organs)
    )
    custody_split = rollup.get("runner_custody_split") or _count_by(
        join_organs, "runner_custody_basis"
    )
    exact_copy = custody_split.get("directory_coupling_marker", 0)

    rows = [
        {
            "rank": 1,
            "target_type": "owned_source",
            "target": "src/microcosm_core/comprehension.py",
            "title": "Cold-clone comprehension router and read packs",
            "why": (
                "Highest reader-visible leverage: this file decides what a cold agent "
                "sees for vague goals, whole-system comprehension, authority calibration, "
                "and safe mutation planning."
            ),
            "expected_reader_visible_change": (
                "A clone-side agent asking what to improve gets concrete targets and "
                "validation commands instead of another orientation packet."
            ),
            "validation_commands": [
                'PYTHONPATH=src python3 -m microcosm_core comprehend --goal "what should I work on for the Microcosm release?"',
                "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --packet-route",
                "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --whole-system",
            ],
        },
        {
            "rank": 2,
            "target_type": "owned_source",
            "target": "src/microcosm_core/cli.py",
            "title": "CLI first-contact affordance",
            "why": (
                "The CLI is the first tool surface after install. If the compiler gains "
                "a better comprehension behavior, the help text and named options should "
                "make that behavior discoverable without reading docs."
            ),
            "expected_reader_visible_change": (
                "The shortest local command path names the improvement-target behavior "
                "plainly for Type A agents."
            ),
            "validation_commands": [
                "PYTHONPATH=src python3 -m microcosm_core comprehend --help",
                "PYTHONPATH=src python3 -m microcosm_core comprehend --packet-atlas",
            ],
        },
        _join_index_improvement_row(inputs),
        {
            "rank": 4,
            "target_type": "docs",
            "target": "README.md / AGENTS.md / skills/cold_start_navigation.md",
            "title": "Cold-agent command ladder wording",
            "why": (
                "Docs are secondary to the CLI, but the release clone path should name "
                "the same command ladder the compiler actually routes."
            ),
            "expected_reader_visible_change": (
                "A reader skimming entry docs sees the exact commands that match the "
                "runtime comprehension packets."
            ),
            "validation_commands": [
                "PYTHONPATH=microcosm-substrate/src ./repo-pytest microcosm-substrate/tests/test_batch12_release_claim_language_gate.py -q --basetemp /tmp/microcosm-release-boundary",
            ],
        },
    ]
    context = {
        "organ_count": organ_count,
        "exact_copy_macro_runners": exact_copy,
        "packet_count": len(PACKET_SPECS),
        "deferred_edge_classes": [
            d["edge_class"]
            for d in _deferred_edges_for(inputs, _CANONICAL_EDGE_CLASSES)
        ],
    }
    for row in rows:
        target = str(row["target"]).split(" / ")[0]
        row["path_exists"] = (base / target).exists()
        row["ranking_basis"] = context
        row["claim_paths"] = _claim_paths_for_improvement_target(row["target"])
        next_command = _mutation_plan_command_for_improvement_target(row["target"])
        if next_command:
            row["next_command"] = next_command
    return rows


def _claim_paths_for_improvement_target(target: Any) -> list[str]:
    """
    [ACTION]
    Return the explicit owned paths a ranked improvement row asks an agent to claim.
    - Teleology: Implements `_claim_paths_for_improvement_target` for `microcosm_core.comprehension` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [part.strip() for part in str(target).split(" / ") if part.strip()]


def _mutation_plan_command_for_improvement_target(target: Any) -> str | None:
    """
    [ACTION]
    Return the local mutation-plan command when the target is a single owned path.
    - Teleology: Implements `_mutation_plan_command_for_improvement_target` for `microcosm_core.comprehension` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    paths = _claim_paths_for_improvement_target(target)
    if len(paths) != 1:
        return None
    path = paths[0]
    if path.endswith(".py") or "/" in path:
        return "PYTHONPATH=src python3 -m microcosm_core comprehend --mutation " + path
    return None


def _improvement_next_action(row: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Compile the machine-readable next action for the top improvement row.
    - Teleology: Implements `_improvement_next_action` for `microcosm_core.comprehension` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    command = row.get("next_command") or (
        "PYTHONPATH=src python3 -m microcosm_core comprehend --improvements"
    )
    return {
        "action_kind": "inspect_mutation_target",
        "target_rank": row["rank"],
        "target": row["target"],
        "title": row["title"],
        "command": command,
        "claim_paths": list(row.get("claim_paths") or []),
        "validation_commands": list(row.get("validation_commands") or []),
        "stop_condition": (
            "Stop after the target mutation plan names the owned paths and validators; "
            "claim those paths before editing."
        ),
    }


def _improvement_row_for_target(
    inputs: dict[str, Any], root: Path | None, target: str
) -> dict[str, Any] | None:
    """
    [ACTION]
    Return the ranked improvement row that owns ``target``, if any.

    - Teleology: keep a path-specific mutation plan connected to the ranked
      cold-clone improvement packet that sent the agent there.
    - Guarantee: exact-matches target against each ranked row's claim paths and
      target path string; returns a copy so callers can annotate safely.
    - Fails: never raises; returns None when the target is not an improvement row.
    - Reads: in-memory inputs plus the same existence checks as improvement ranking.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    for row in _release_improvement_targets(inputs, root):
        claim_paths = [str(p) for p in row.get("claim_paths") or []]
        row_target = str(row.get("target") or "")
        if target in claim_paths or target == row_target:
            return dict(row)
    return None


def _join_index_improvement_row(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Build the rank-3 join-index improvement row from the graph's ACTUAL state.

    - Teleology: keep the ranked improvement list honest across its own lifecycle --
      while route/claim topology is deferred the row says build it; once the v2
      graph resolves those classes the row advances to the genuinely-remaining
      proof-graph extraction instead of re-recommending finished work.
    - Guarantee: returns a rank-3 target row whose target is always
      scripts/build_code_lens_join_index.py (the owning builder) and whose
      title/why/expected change reflect the computed deferred set.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    deferred = {
        d["edge_class"] for d in _deferred_edges_for(inputs, _CANONICAL_EDGE_CLASSES)
    }
    if {"cross_organ_route_topology", "claim_node_ontology"} & deferred:
        title = "Join-index route and claim extraction"
        why = (
            "The self-model still declares cross_organ_route_topology and "
            "claim_node_ontology as deferred edges. Filling those edges would make "
            "claim_trace and flow packets less thin for all organs."
        )
        change = (
            "A cold reader can follow route and claim topology directly instead of "
            "seeing those relationships as deferred."
        )
    else:
        title = "Join-index proof-graph extraction (proof_internal_structure)"
        why = (
            "Route and claim topology are graph-backed now; the one remaining "
            "deferred edge class is proof_internal_structure -- theorem -> lemma -> "
            "tactic edges need a Lean-aware proof-graph builder feeding the join index."
        )
        change = (
            "A cold reader can walk INSIDE a proof organ's evidence instead of "
            "stopping at its receipts."
        )
    return {
        "rank": 3,
        "target_type": "builder",
        "target": "scripts/build_code_lens_join_index.py",
        "title": title,
        "why": why,
        "expected_reader_visible_change": change,
        "validation_commands": [
            "PYTHONPATH=src python3 scripts/build_code_lens_join_index.py --help",
            "PYTHONPATH=src python3 -m microcosm_core comprehend --self-model",
            "PYTHONPATH=src python3 -m microcosm_core comprehension-assay --whole-system",
        ],
    }


def compile_mutation_plan(
    inputs: dict[str, Any], root: Path | None, target: str
) -> dict[str, Any]:
    """
    [ACTION]
    Compile the safe-mutation plan for an organ or owned path (local band).

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
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    base = root or default_root()
    atlas_by = inputs.get("atlas_by_organ", {})
    join_by = inputs.get("join_by_organ", {})
    if target and (target.endswith(".py") or "/" in target):
        improvement_row = _improvement_row_for_target(inputs, base, target)
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
        if improvement_row:
            claim_paths = list(improvement_row.get("claim_paths") or [target])
            validation_commands = list(improvement_row.get("validation_commands") or [])
            pack["summary"]["what_this_is"] = (
                f"Mutation plan for ranked improvement target {target}: "
                f"{improvement_row.get('title')}."
            )
            pack["summary"]["what_to_inspect_next"] = [
                target,
                *validation_commands,
            ]
            pack["selected_nodes"] = [
                {
                    **improvement_row,
                    "current_mutation_plan": True,
                }
            ]
            pack["claim_paths"] = claim_paths
            pack["validation_commands"] = validation_commands
            pack["improvement_context"] = {
                "rank": improvement_row.get("rank"),
                "title": improvement_row.get("title"),
                "why": improvement_row.get("why"),
                "expected_reader_visible_change": improvement_row.get(
                    "expected_reader_visible_change"
                ),
                "ranking_basis": improvement_row.get("ranking_basis"),
            }
            pack["recommended_first_action"] = {
                "action_kind": "claim_then_edit_target",
                "target_rank": improvement_row.get("rank"),
                "target": target,
                "claim_paths": claim_paths,
                "validation_commands": validation_commands,
                "stop_condition": (
                    "Stop when the claimed path has a focused patch, the listed "
                    "validators pass, and the ratchet is logged."
                ),
            }
            pack["mutation_steps"] = [
                "claim every claim_paths entry before editing",
                "edit only this mutation-plan target and its focused tests",
                "run validation_commands",
                "rerun packet-route and whole-system comprehension assays before closeout",
            ]
            pack["warnings"] = [
                "this path plan is a local implementation route, not release approval",
                "do not widen into exact-copy macro runners from this packet",
            ]
        return pack
    if not target or (target not in atlas_by and target not in join_by):
        targets = _release_improvement_targets(inputs, base)
        next_action = _improvement_next_action(targets[0])
        pack = _pack_skeleton("how_to", "choose the highest-leverage Microcosm improvement")
        pack["found"] = True
        pack["target"] = None
        pack["export_band"] = "local_semantic_excerpt"
        pack["summary"]["what_this_is"] = (
            "Ranked concrete edit targets for improving Microcosm cold-clone "
            "comprehension. Start at rank 1 unless you already have a narrower failing "
            "surface."
        )
        pack["summary"]["what_to_inspect_next"] = [
            f"{row['rank']}. {row['target']} - {row['title']}" for row in targets
        ]
        pack["summary"]["first_command"] = next_action["command"]
        pack["summary"]["what_not_to_trust"] = (
            "These are local implementation priorities, not release approval or a claim "
            "that the substrate is complete."
        )
        pack["selected_nodes"] = targets
        pack["recommended_first_action"] = next_action
        pack["mutation_steps"] = [
            "run recommended_first_action.command to inspect the rank-1 mutation plan",
            "claim every recommended_first_action.claim_paths entry before editing",
            "edit only the owned source/docs path for that rank",
            "run that row's validation_commands",
            "rerun packet-route and whole-system comprehension assays before closeout",
        ]
        pack["warnings"] = [
            "target ranking is a comprehension work plan, not authority to publish",
            "do not edit exact-copy macro runners unless the refresh lane owns the copy",
        ]
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

# The canonical comprehension edge classes and their precise residual rows. Whether a
# class is DEFERRED is no longer asserted here -- it is COMPUTED from the join index's
# graph block (_graph_state), so a clone with a degraded/stale join index re-defers
# honestly and a clone with the v2 graph stops apologizing for edges it now has.
_CANONICAL_EDGE_CLASSES = (
    "proof_internal_structure",
    "cross_organ_route_topology",
    "claim_node_ontology",
)

_EDGE_CLASS_RESIDUALS: dict[str, dict[str, str]] = {
    "proof_internal_structure": {
        "edge_class": "proof_internal_structure",
        "missing": "theorem -> lemma -> tactic edges inside a proof organ",
        "missing_source_class": "lean_proof_term_graph_not_extracted",
        "owner_path": "scripts/build_code_lens_join_index.py",
        "blocked_on": "no Lean-aware proof-graph builder exists yet; see owner_path",
        "would_come_from": "a Lean-aware proof-graph builder feeding the join index",
        "next_packet": "math",
    },
    "cross_organ_route_topology": {
        "edge_class": "cross_organ_route_topology",
        "missing": "route nodes fanning one task-class entry across organs",
        "missing_source_class": "agent_task_routes_plane_absent_from_join_index",
        "owner_path": "scripts/build_code_lens_join_index.py",
        "re_entry_command": (
            "PYTHONPATH=src python3 scripts/build_code_lens_join_index.py"
            " --lens <python-lens --full snapshot> --routes atlas/agent_task_routes.json"
        ),
        "would_come_from": "rebuilding the join index with atlas/agent_task_routes.json",
        "next_packet": "claim_trace",
    },
    "claim_node_ontology": {
        "edge_class": "claim_node_ontology",
        "missing": "a first-class claim node distinct from the per-organ ceiling",
        "missing_source_class": "organ_registry_claim_fields_not_joined",
        "owner_path": "scripts/build_code_lens_join_index.py",
        "re_entry_command": (
            "PYTHONPATH=src python3 scripts/build_code_lens_join_index.py"
            " --lens <python-lens --full snapshot>"
        ),
        "would_come_from": "rebuilding the join index with the organ registry plane",
        "next_packet": "flow",
    },
}


def _graph_state(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Read the join index's graph contract, re-deriving resolution structurally.

    - Teleology: one accessor for "what topology does this clone's join index
      actually carry?" so packets derive deferral from graph truth, not prose.
    - Guarantee: returns {resolved: set[str], graph: dict, route_nodes, claim_nodes,
      family_nodes}; claim_node_ontology / cross_organ_route_topology count as
      resolved ONLY when the nodes AND their typed edges are actually present --
      the declared resolved_edge_classes label is never trusted for them (a
      corrupted index that declares resolution over empty planes re-defers);
      classes without a structural signature (proof_internal_structure) follow the
      declared label. An absent/old join index yields empty resolved + empty lists.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    join_index = inputs.get("join_index") or {}
    graph = join_index.get("graph") if isinstance(join_index, dict) else None
    graph = graph if isinstance(graph, dict) else {}
    nodes = (join_index.get("nodes") or {}) if isinstance(join_index, dict) else {}
    route_nodes = [r for r in nodes.get("route") or [] if isinstance(r, dict)]
    claim_nodes = [c for c in nodes.get("claim") or [] if isinstance(c, dict)]
    edge_kinds = {
        e.get("kind")
        for e in (join_index.get("edges") or [] if isinstance(join_index, dict) else [])
        if isinstance(e, dict)
    }
    resolved = {
        cls
        for cls in (graph.get("resolved_edge_classes") or [])
        if cls not in ("claim_node_ontology", "cross_organ_route_topology")
    }
    if claim_nodes and "asserts_claim" in edge_kinds:
        resolved.add("claim_node_ontology")
    if route_nodes and "routes_to" in edge_kinds:
        resolved.add("cross_organ_route_topology")
    return {
        "resolved": resolved,
        "graph": graph,
        "route_nodes": route_nodes,
        "claim_nodes": claim_nodes,
        "family_nodes": [f for f in nodes.get("family") or [] if isinstance(f, dict)],
    }


def _deferred_edges_for(
    inputs: dict[str, Any], classes: tuple[str, ...]
) -> list[dict[str, Any]]:
    """
    [ACTION]
    Compute the deferred-edge rows a packet must surface, from graph truth.

    - Teleology: keep deferred_edges honest in BOTH directions -- a packet neither
      hides a genuinely-missing edge class nor keeps apologizing for one the join
      index now materializes.
    - Guarantee: returns the precise residual rows (missing_source_class, owner_path,
      re_entry_command or blocked_on) for each requested class NOT structurally
      resolved; when the join index's graph block carries its own residual row for
      the class, that row is the source of truth (merged with the packet-only
      next_packet scent), so builder and packets never drift apart; [] when all
      requested classes are resolved.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    state = _graph_state(inputs)
    builder_rows = {
        row.get("edge_class"): row
        for row in state["graph"].get("deferred_edge_classes") or []
        if isinstance(row, dict)
    }
    out: list[dict[str, Any]] = []
    for cls in classes:
        if cls not in _EDGE_CLASS_RESIDUALS or cls in state["resolved"]:
            continue
        row = dict(_EDGE_CLASS_RESIDUALS[cls])
        if cls in builder_rows:
            row.update(builder_rows[cls])
            row.setdefault("next_packet", _EDGE_CLASS_RESIDUALS[cls].get("next_packet"))
        out.append(row)
    return out


def _graph_backed_block(
    inputs: dict[str, Any], classes: tuple[str, ...]
) -> dict[str, Any]:
    """
    [ACTION]
    Describe which requested edge classes this packet answers from the graph.

    - Teleology: the positive counterpart of _deferred_edges_for -- name what is
      now graph-backed so a reader can trust (and audit) the edges it follows.
    - Guarantee: returns {edge_classes_resolved, edge_kind_counts, source}; the
      resolved list contains only the requested classes the join index resolves;
      the source pointer names the #graph fragment (plus the inner schema_version,
      pre-answering the v0-filename/v2-schema scent) only when that fragment
      actually exists, and otherwise says the index predates the graph block.
    - Fails: never raises.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    state = _graph_state(inputs)
    block: dict[str, Any] = {
        "edge_classes_resolved": sorted(c for c in classes if c in state["resolved"]),
        "edge_kind_counts": dict(state["graph"].get("edge_kind_counts") or {}),
    }
    if state["graph"]:
        block["source"] = "receipts/code_lens/code_lens_join_index_v0.json#graph"
        block["source_schema"] = (inputs.get("join_index") or {}).get("schema_version")
        block["source_note"] = "the v0 filename is a stable artifact path; the schema_version inside is authoritative"
    else:
        block["source"] = (
            "join index predates the v2 graph block; rebuild via "
            "scripts/build_code_lens_join_index.py"
        )
    return block


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    """
    [ACTION]
    Count rows by a string field, returned high-to-low (shared distribution helper).

    - Teleology: the one counter behind the self-model's calibration rollup so evidence
      class / truth-accounting / strength distributions all read the same way.
    - Guarantee: returns {value: count} sorted by descending count then value; a missing
      field becomes "unspecified".
    - Fails: never raises.
    - Reads: only the supplied rows.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Build the per-organ essence roster grouped by family (the comprehend-all payload).

    - Teleology: let a cold agent read EVERY organ's essence + calibration in one pass --
      the literal "comprehend all 82 organs at once" body.
    - Guarantee: returns a list of {family, organ_count, organs:[{organ_id, essence,
      evidence_class, evidence_strength_rank, truth_accounting_bucket, claim_ceiling,
      first_command}]}; essence draws from the public synopsis then human gloss.
    - Fails: never raises.
    - Reads: only the supplied in-memory maps.
    - Non-goal: never reads runner source or docstring atoms.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    """
    [ACTION]
    Compile the public-safe, calibrated reader block (NOT a marketing summary).

    - Teleology: let a skeptical external reader see what the system demonstrates, what it
      explicitly does NOT, and where the known thinness is -- quality inferred from honesty.
    - Guarantee: returns {what_it_demonstrates, what_it_does_not_demonstrate,
      known_thinness, recommended_demo_path}; no house jargon, no release/correctness claim.
    - Fails: never raises.
    - Reads: only the supplied health rollup + atlas.
    - Non-goal: never asserts impressiveness, release, or domain correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
            "plectis comprehend --self-model",
            "plectis comprehend --slice math",
            "plectis comprehend --slice claims --organ <a proof organ>",
            "microcosm comprehension-assay --whole-system",
        ],
    }


def compile_self_model(inputs: dict[str, Any], profile: str = "operating_picture") -> dict[str, Any]:
    """
    [ACTION]
    Compile the whole-Plectis self-model: the entire substrate in one budgeted packet.

    - Teleology: let a cold agent comprehend the WHOLE substrate at once -- every family,
      what is real vs thin, what must not be claimed, and where to drill down -- instead of
      judging Plectis from whichever slice it opened.
    - Guarantee: returns a SELF_MODEL_SCHEMA pack with a front anchor (read_me_first), a
      section index, major_subsystems (families), code_lens_health (evidence/truth-
      accounting/strength/custody rollups), authority_membrane, thin_or_projection_surfaces
      (skepticism made navigable), deferred_edges, recommended_drilldowns (the hub routing
      to the specialized packets), and a tail_recap; profile whole_substrate_map adds the
      per-organ essence roster, public_reader adds the calibrated external-reader block.
    - Fails: never raises; an unknown profile falls back to operating_picture.
    - Reads: the in-memory inputs bundle only (atlas + join index + synopses).
    - Non-goal: never exports source bodies, asserts impressiveness, or grants release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
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
    state = _graph_state(inputs)
    health = {
        "organ_count": organ_count,
        "edge_count": rollup.get("edge_count"),
        "edge_kind_counts": dict(state["graph"].get("edge_kind_counts") or {}),
        "claim_node_count": rollup.get("claim_node_count", len(state["claim_nodes"])),
        "route_node_count": rollup.get("route_node_count", len(state["route_nodes"])),
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
        'Have a concrete goal? plectis comprehend --first-action "<goal>" converts it into ONE '
        "graph-backed first action -- owner, runnable command, validator, receipts, stop condition, "
        "do-not-edit boundary. FIRST_ACTION.md demonstrates this across a goal battery.",
    ]
    if {"cross_organ_route_topology", "claim_node_ontology"} <= state["resolved"]:
        routes_with_stop = sum(
            1 for r in state["route_nodes"] if r.get("stop_condition") and r.get("first_command")
        )
        route_total = len(state["route_nodes"])
        route_phrase = (
            "each with a first command and a stop condition"
            if routes_with_stop == route_total
            else f"{routes_with_stop} of {route_total} carrying a first command and a stop condition"
        )
        pack["read_me_first"].append(
            f"The join index is a typed graph: {route_total} task-class routes "
            f"({route_phrase}), first-class claim nodes chained "
            "claim -> validator -> receipt, wires_to topology, and doctrine refs. Only "
            "proof-internal structure remains deferred."
        )
    pack["summary"]["what_this_is"] = (
        str(atlas.get("authority_boundary") or "A self-describing organ substrate.")
    )
    pack["summary"]["what_to_inspect_next"] = ["plectis comprehend --slice organs"]
    pack["summary"]["what_not_to_trust"] = str(atlas.get("anti_claim") or "")
    pack["sections"] = [
        "read_me_first", "major_subsystems", "route_topology", "code_lens_health",
        "authority_membrane", "thin_or_projection_surfaces", "deferred_edges",
        "recommended_drilldowns", "tail_recap",
    ]
    pack["major_subsystems"] = [
        {
            "family": entry["family"],
            "organ_count": entry["count"],
            "drilldown": f"plectis comprehend --slice cluster --family {entry['family']}",
        }
        for entry in families
    ]
    # ROUTE TOPOLOGY -- how task-class entry points fan out across organs. Honest in
    # both directions: a join index without the route plane says so and names the fix.
    if state["route_nodes"]:
        pack["route_topology"] = {
            "route_node_count": len(state["route_nodes"]),
            "organs_reachable_from_routes": rollup.get("organs_reachable_from_routes"),
            "routes": [
                {
                    "task_class": r.get("task_class"),
                    "primary_organ_id": r.get("primary_organ_id"),
                    "primary_display_name": r.get("primary_display_name"),
                    "organ_count": r.get("organ_count"),
                }
                for r in state["route_nodes"]
            ],
            "drilldown": "plectis comprehend --slice flows --organ <primary_organ_id>",
            "note": "route nodes carry a first_command, a stop_condition, and an "
            "allowed_scope where the route plane binds them; the flow and organ "
            "packets surface them per organ",
        }
    else:
        pack["route_topology"] = {
            "route_node_count": 0,
            "note": "this clone's join index carries no route plane; rebuild it with "
            "scripts/build_code_lens_join_index.py --routes atlas/agent_task_routes.json",
        }
    pack["code_lens_health"] = health
    # Deduplicated on purpose: bands + ceiling already live verbatim on this pack
    # (membrane / authority_ceiling); re-embedding them mid-packet creates
    # lost-in-the-middle "did I lose my place?" friction for a cold reader.
    pack["authority_membrane"] = {
        "bands": "see membrane.bands (top of this packet)",
        "authority_ceiling": "see top-level authority_ceiling (all false)",
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
    pack["deferred_edges"] = _deferred_edges_for(inputs, _CANONICAL_EDGE_CLASSES)
    graph_backed = _graph_backed_block(inputs, _CANONICAL_EDGE_CLASSES)
    # The counts already live in code_lens_health; point rather than duplicate.
    graph_backed["edge_kind_counts"] = "see code_lens_health.edge_kind_counts"
    pack["graph_backed"] = graph_backed
    # The self-model is the HUB: it routes to the specialized packets rather than duplicating them.
    pack["recommended_drilldowns"] = [
        {"question": "what is my FIRST correct action for a goal?", "packet": "first_action",
         "command": 'plectis comprehend --first-action "<goal>"'},
        {"question": "what organs exist (one line each)?", "packet": "organs_index",
         "command": "plectis comprehend --slice organs"},
        {"question": "understand a whole family?", "packet": "organ_cluster",
         "command": "plectis comprehend --slice cluster --family <f>"},
        {"question": "where is the math / proof?", "packet": "math",
         "command": "plectis comprehend --slice math"},
        {"question": "what may I trust?", "packet": "authority",
         "command": "plectis comprehend --slice authority"},
        {"question": "how is a claim justified?", "packet": "claim_trace",
         "command": "plectis comprehend --slice claims --organ <id>"},
        {"question": "how does an organ run?", "packet": "flow",
         "command": "plectis comprehend --slice flows --organ <id>"},
        {"question": "change something safely?", "packet": "mutation_plan",
         "command": "plectis comprehend --mutation <id|path>"},
        {"question": "read a file's atoms without opening source?", "packet": "path",
         "command": "plectis comprehend --path <owned_file>"},
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
        "next_packet_if_lost": "plectis comprehend --packet-atlas",
        "to_comprehend_every_organ": "plectis comprehend --self-model --profile whole_substrate_map",
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
    """
    [ACTION]
    Compile one comprehension packet and stamp its identity, budget, and latency.

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
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    elif mode == "first_action":
        pack = compile_first_action(bundle, base_root, target or goal or "")
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
    """
    [ACTION]
    Materialize the prebuilt first-contact / authority / organs read packs.

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
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    """
    [ACTION]
    Return the fixed assay question set, parameterized by a sample organ.

    - Teleology: define the cold-agent questions whose answers must live in read packs.
    - Guarantee: returns a list of {q, mode, organ, must_key, evidence_token} rows.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
        {"q": f"Where do I stop reading for {sample_organ}?", "mode": "organ", "organ": sample_organ,
         "must_key": "reading_boundary", "evidence_token": "stop_condition"},
        {"q": f"How is {sample_organ}'s claim proven?", "mode": "claim_trace", "organ": sample_organ,
         "must_key": "selected_nodes", "evidence_token": "validator"},
    ]


def _dig(pack: dict[str, Any], dotted: str) -> Any:
    """
    [ACTION]
    Resolve a dotted key path into a pack, returning None when absent.

    - Teleology: let assay rows assert on nested pack fields by path.
    - Guarantee: returns the nested value or None; never raises on a missing key.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cur: Any = pack
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _pack_leaks_source_body(pack: dict[str, Any]) -> bool:
    """
    [ACTION]
    Detect whether a pack leaked a raw docstring atom bullet.

    - Teleology: enforce the presence_only membrane on compiled output, not just input.
    - Guarantee: returns True iff the serialized pack contains a "- Teleology:"-style
      raw atom bullet marker.
    - Fails: never raises.
    - Reads: only the in-memory pack.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    body = json.dumps(pack, ensure_ascii=True)
    return any(marker in body for marker in _ATOM_BULLET_MARKERS)


def run_comprehension_assay(
    root: Path | None = None, inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    [ACTION]
    Run the cold-agent comprehension assay over the compiled read packs.

    - Teleology: prove the read packs actually let a cold agent answer substrate /
      authority / organ questions without opening source -- the activation evidence.
    - Guarantee: returns an ASSAY_SCHEMA dict with answerable_without_source_pct,
      wrong_authority_claims, source_body_leaks, source_reads_avoided, max_pack_bytes,
      max_compile_ms, and a per-question result list; all metrics are computed, not asserted.
    - Fails: never raises on content; ValueError only on a leaking join index (via load).
    - Reads: the substrate inputs once.
    - Writes: nothing.
    - Non-goal: does not call any LLM; "answerable" means the answer material is present.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    """
    [ACTION]
    True when at least one excerpt symbol exposes a value for the named atom.

    - Teleology: the hard-assay predicate proving the local band actually carries a
      given authored atom's value, not merely that a symbol exists.
    - Guarantee: returns True iff some row's atom_values contains ``atom``.
    - Fails: never raises.
    - Reads: only the supplied excerpt rows.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return any(atom in (s.get("atom_values") or {}) for s in symbols)


def run_hard_comprehension_assay(root: Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    Run the hard assay that requires real authored atom-value content.

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
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    ("what should I work on for the Microcosm release?", "mutation_plan"),
    ("what is the most productive improvement?", "mutation_plan"),
    ("I want to change the import behaviour", "mutation_plan"),
    ("read the atom values in src/microcosm_core/comprehension.py", "path"),
    ("where do I start?", "first_action"),
    ("what is my first correct action here?", "first_action"),
]


def _assay_sample_target(mode: str, inputs: dict[str, Any]) -> str | None:
    """
    [ACTION]
    Pick a representative target so each parameterized packet can compile in the assay.

    - Teleology: let the route assay actually compile organ/cluster/claim/flow/mutation
      packets, not only the parameterless ones.
    - Guarantee: returns a family name for organ_cluster, an owned path for path/
      mutation_plan, a sample organ id for organ/claim_trace/flow, else None.
    - Fails: never raises; returns None when no sample is available.
    - Reads: the in-memory inputs bundle only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    if mode == "organ_cluster":
        roster = _family_roster(list(inputs.get("atlas_by_organ", {}).values()))
        return roster[0]["family"] if roster else None
    if mode in ("path", "mutation_plan"):
        return OWNED_EXCERPT_ROOT + "comprehension.py"
    if mode == "first_action":
        return "where do I start?"
    if mode in ("organ", "claim_trace", "flow"):
        return next(iter(inputs.get("join_by_organ", {})), None) or next(
            iter(inputs.get("atlas_by_organ", {})), None
        )
    return None


def run_packet_route_assay(
    root: Path | None = None, inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    [ACTION]
    Assay the packet atlas as a navigable product, not just an answer surface.

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
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    ("how do task-class entry points reach organs?", "route_topology", None),
    ("which surfaces are runtime vs projection vs custody/import?", "code_lens_health.by_evidence_class", None),
    ("what is the real-vs-copied calibration?", "code_lens_health.by_truth_accounting_bucket", None),
    ("what should NOT be claimed?", "authority_membrane.authority_ceiling", None),
    ("where is the thinness / where to be skeptical?", "thin_or_projection_surfaces", None),
    ("what remains deferred, and what would resolve it?", "deferred_edges", None),
    ("which packet inspects one organ next?", "recommended_drilldowns", "organ"),
    ("is there a front anchor?", "read_me_first", None),
    ("is there a tail recap?", "tail_recap", None),
]


def run_whole_system_comprehension_assay(
    root: Path | None = None, inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    [ACTION]
    Assay whether the self-model lets a cold reader comprehend the WHOLE substrate.

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
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    state = _graph_state(bundle)
    deferred_remaining = sorted(
        d.get("edge_class")
        for d in pack.get("deferred_edges") or []
        if isinstance(d, dict)
    )
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
        "deferred_edge_classes_remaining": deferred_remaining,
        "route_topology_present": bool(
            (pack.get("route_topology") or {}).get("route_node_count")
        ),
        "claim_nodes_present": bool(state["claim_nodes"]),
        "deferred_residuals_are_precise": bool(pack.get("deferred_edges"))
        and all(
            isinstance(d, dict)
            and d.get("missing_source_class")
            and d.get("owner_path")
            and (d.get("re_entry_command") or d.get("blocked_on"))
            for d in pack.get("deferred_edges") or []
        ),
        "front_anchor_present": bool(pack.get("read_me_first")),
        "tail_recap_present": bool(pack.get("tail_recap")),
        "packet_bytes": len(json.dumps(pack, ensure_ascii=True)),
        "results": results,
        "authority_ceiling": dict(AUTHORITY_CEILING),
    }


# --- first-action assay: does the graph operate an agent's FIRST move? -------------

# Cold-agent scenarios with the contract each must produce. expect keys:
#   owner_organ   -- the organ the contract must localize to
#   action_kind   -- the contract's action class
#   command_has   -- substring the first-action command must carry
#   routing_basis -- how the goal must have been resolved
#   do_not_edit_boundary -- the custody boundary must name paths or explain why
#                           there are no forbidden edit paths for this owner
# The adversarial rows came out of a red-team review: house vocabulary
# ("fixture", "dispatch", "exchange"), single-common-word traps ("does this
# work?"), negation, and destructive/publication intent must all resolve to
# SAFE contracts -- never a mutation plan or a confidently wrong fixture.
_FIRST_ACTION_FIXTURES: list[tuple[str, dict[str, Any]]] = [
    ("where do I start with this clone?",
     {"owner_organ": "cold_reader_route_map", "action_kind": "run_fixture_command"}),
    ("run the lean proof evidence checks",
     {"owner_organ": "lean_proof_search_lab_runtime", "action_kind": "run_fixture_command"}),
    ("evaluate agent benchmark gaming",
     {"owner_organ": "agent_benchmark_integrity_anti_gaming_replay",
      "action_kind": "run_fixture_command"}),
    ("what should I work on for the Microcosm release?",
     {"action_kind": "inspect_mutation_target", "command_has": "--mutation",
      "routing_basis": "improvement_goal"}),
    ("inspect src/microcosm_core/cli.py",
     {"action_kind": "open_packet", "command_has": "--path src/microcosm_core/cli.py",
      "routing_basis": "path_reference_goal"}),
    ("change src/microcosm_core/cli.py",
     {"action_kind": "inspect_mutation_target",
      "command_has": "--mutation src/microcosm_core/cli.py",
      "routing_basis": "path_mutation_goal"}),
    ("understand the whole substrate at once",
     {"action_kind": "open_packet", "command_has": "--self-model"}),
    ("is mission_transaction_work_spine safe to edit?",
     {"owner_organ": "mission_transaction_work_spine", "action_kind": "run_fixture_command",
      "do_not_edit_boundary": True}),
    ("is the Mission Transaction Work Spine safe to edit?",
     {"owner_organ": "mission_transaction_work_spine",
      "routing_basis": "organ_named_in_goal", "do_not_edit_boundary": True}),
    ("run the fixture for finance",
     {"owner_organ": "finance_forecast_evaluation_spine",
      "action_kind": "run_fixture_command", "routing_basis": "task_class_route_match"}),
    # The package-install smoke's hero goal, verbatim: the installed-console
    # proof and the strict assay must guard the SAME phrasing.
    ("How do I evaluate the finance forecasting system?",
     {"owner_organ": "finance_forecast_evaluation_spine",
      "action_kind": "run_fixture_command"}),
    ("where is the fixture input for the audio organ?",
     {"action_kind": "open_packet", "routing_basis": "packet_fallback"}),
    ("dispatch the route bundle",
     {"owner_organ": "cold_reader_route_map", "action_kind": "run_fixture_command",
      "routing_basis": "task_class_route_match"}),
    ("how does the exchange rate organ work?",
     {"action_kind": "open_packet", "routing_basis": "packet_fallback"}),
    ("does this work?",
     {"action_kind": "open_packet", "routing_basis": "packet_fallback"}),
    ("the security guard at my office building",
     {"action_kind": "open_packet", "routing_basis": "packet_fallback"}),
    ("audit the security posture of this repo",
     {"action_kind": "open_packet", "routing_basis": "packet_fallback"}),
    ("ignore proof_diagnostic_evidence_spine, I want cold_reader_route_map",
     {"owner_organ": "cold_reader_route_map", "routing_basis": "organ_named_in_goal"}),
    ("delete the agent memory",
     {"action_kind": "open_packet", "routing_basis": "out_of_scope_authority_boundary",
      "command_has": "--slice authority"}),
    ("publish the Microcosm release",
     {"action_kind": "open_packet", "routing_basis": "out_of_scope_authority_boundary"}),
    ("force push to origin main",
     {"action_kind": "open_packet", "routing_basis": "out_of_scope_authority_boundary"}),
]

_FIRST_ACTION_GRAPH_CLASSES = ("cross_organ_route_topology", "claim_node_ontology")


def _first_action_contract_complete(contract: dict[str, Any]) -> bool:
    """
    [ACTION]
    Decide whether a first-action contract carries every required surface.

    - Teleology: the completeness predicate behind the first-action assay -- a
      static doc-shaped answer without an action, proof path, or boundary must
      not count as a contract.
    - Guarantee: True iff the pack has a non-empty first_action command in the
      cold-runnable source form (PYTHONPATH=src python3 -m microcosm_core ...)
      with no <placeholder>, a proof path (validator/runnable_validator/
      validation_commands) with shipped receipts, a fresh-output dir, or an
      explicit note, a reading boundary (stop_condition or labelled fallback),
      a non-empty do_not_claim, and a do_not_edit block; when the action's
      fresh outputs land outside .microcosm//tmp, a clean_run variant whose
      --out really redirects under .microcosm/ is also required (footprint
      honesty).
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    action = contract.get("first_action") or {}
    command = str(action.get("command") or "")
    if not command.startswith("PYTHONPATH=src python3 -m microcosm_core"):
        return False
    if "<" in command:
        return False
    proof = contract.get("proof_path") or {}
    has_proof = bool(
        proof.get("validator_command")
        or proof.get("runnable_validator")
        or proof.get("validation_commands")
    )
    has_evidence = bool(
        action.get("committed_receipts")
        or action.get("writes_outputs_under")
        or proof.get("receipt_refs")
        or proof.get("note")
    )
    boundary = contract.get("reading_boundary") or {}
    has_boundary = bool(
        boundary.get("stop_condition") or boundary.get("fallback_guidance")
    )
    # Footprint honesty, recomputed from the COMMAND (fail closed): the
    # declared out-dir must match what the command actually writes, and any
    # non-ignored write-flag target obliges a clean_run variant whose own
    # command writes only under the ignored scratch tree.
    declared_out = str(action.get("writes_outputs_under") or "")
    if declared_out != str(_writes_outputs_under(command) or ""):
        return False
    if any(not _is_ignored_out_dir(t) for _f, t in _write_targets(command)):
        clean_run = action.get("clean_run") or {}
        clean_command = str(clean_run.get("command") or "")
        clean_out = str(clean_run.get("writes_outputs_under") or "")
        clean_targets = _write_targets(clean_command)
        if not clean_out.startswith(".microcosm"):
            return False
        if not clean_targets:
            return False
        if any(not _is_ignored_out_dir(t) for _f, t in clean_targets):
            return False
        if str(_writes_outputs_under(clean_command) or _CLEAN_RUN_OUT_ROOT) != clean_out:
            return False
    return (
        has_proof
        and has_evidence
        and has_boundary
        and bool(contract.get("do_not_claim"))
        and isinstance(contract.get("do_not_edit"), dict)
    )


def run_first_action_assay(
    root: Path | None = None, inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    [ACTION]
    Assay whether the graph converts cold-agent goals into first correct actions.

    - Teleology: prove the leap from self-comprehension to AGENT TRANSFER -- a
      freeform goal must yield one graph-backed contract (action, owner, proof,
      stop condition, ceiling, no-edit boundary), and a clone whose join index
      lacks the graph must FAIL this assay rather than degrade into doc answers.
    - Guarantee: returns a FIRST_ACTION_ASSAY_SCHEMA dict with
      first_action_selection_pct (owner/action/command expectations met),
      contract_completeness_pct, graph_backed_pct (contracts whose resolved
      classes cover route+claim topology -- the graph-bypass detector),
      boundary_pct, authority_overclaim_count, source_body_leaks, degraded
      (route/claim topology unresolved on this clone), and per-scenario rows;
      all metrics computed, never asserted.
    - Fails: never raises on content; ValueError only on a leaking join index.
    - Reads: the substrate inputs once.
    - Writes: nothing.
    - Non-goal: does not call any LLM; "selection" is the deterministic contract
      compiler's output measured against fixture expectations.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    bundle = inputs if inputs is not None else load_inputs(root)
    base = bundle.get("root") or default_root()
    state = _graph_state(bundle)
    degraded = not set(_FIRST_ACTION_GRAPH_CLASSES) <= state["resolved"]

    results: list[dict[str, Any]] = []
    selected = 0
    complete = 0
    graph_backed = 0
    boundary_ok = 0
    overclaim = 0
    leaks = 0
    for goal, expect in _FIRST_ACTION_FIXTURES:
        contract = compile_first_action(bundle, base, goal)
        action = contract.get("first_action") or {}
        owner = contract.get("owner") or {}
        ok_owner = (
            expect.get("owner_organ") is None
            or owner.get("organ_id") == expect["owner_organ"]
        )
        ok_kind = (
            expect.get("action_kind") is None
            or action.get("action_kind") == expect["action_kind"]
        )
        ok_command = (
            expect.get("command_has") is None
            or expect["command_has"] in str(action.get("command") or "")
        )
        ok_basis = (
            expect.get("routing_basis") is None
            or (contract.get("routing") or {}).get("basis") == expect["routing_basis"]
        )
        do_not_edit = contract.get("do_not_edit") or {}
        ok_edit = not expect.get("do_not_edit_boundary") or bool(
            do_not_edit.get("paths") or do_not_edit.get("note")
        )
        ok = (
            bool(contract.get("found"))
            and ok_owner
            and ok_kind
            and ok_command
            and ok_basis
            and ok_edit
        )
        selected += 1 if ok else 0
        is_complete = _first_action_contract_complete(contract)
        complete += 1 if is_complete else 0
        resolved = set(
            (contract.get("graph_backed") or {}).get("edge_classes_resolved") or []
        )
        is_graph_backed = set(_FIRST_ACTION_GRAPH_CLASSES) <= resolved
        graph_backed += 1 if is_graph_backed else 0
        b = contract.get("reading_boundary") or {}
        boundary_ok += 1 if (b.get("stop_condition") or b.get("fallback_guidance")) else 0
        ceiling = contract.get("authority_ceiling") or {}
        overclaim += 1 if any(ceiling.get(k) for k in AUTHORITY_CEILING) else 0
        leaks += 1 if _pack_leaks_source_body(contract) else 0
        results.append(
            {
                "goal": goal,
                "routing_basis": (contract.get("routing") or {}).get("basis"),
                "owner": owner.get("organ_id") or owner.get("scope"),
                "action_kind": action.get("action_kind"),
                "selected": ok,
                "complete": is_complete,
                "graph_backed": is_graph_backed,
            }
        )
    total = len(_FIRST_ACTION_FIXTURES) or 1
    return {
        "schema_version": FIRST_ACTION_ASSAY_SCHEMA,
        "scenarios": total,
        "first_action_selection_pct": round(100.0 * selected / total, 1),
        "contract_completeness_pct": round(100.0 * complete / total, 1),
        "graph_backed_pct": round(100.0 * graph_backed / total, 1),
        "boundary_pct": round(100.0 * boundary_ok / total, 1),
        "authority_overclaim_count": overclaim,
        "source_body_leaks": leaks,
        "degraded": degraded,
        "results": results,
        "authority_ceiling": dict(AUTHORITY_CEILING),
    }
