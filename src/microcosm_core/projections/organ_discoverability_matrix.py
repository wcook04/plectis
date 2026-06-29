"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.projections.organ_discoverability_matrix` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, VALIDATION_SCHEMA_VERSION, DEFAULT_MATRIX_NAME, DEFAULT_RECEIPT_NAME, AUTHORITY_POSTURE, SOURCE_REFS, REQUIRED_ROW_KEYS, BANNED_TRUE_AUTHORITY_KEYS, build_organ_discoverability_matrix, validate_organ_discoverability_matrix, compile_paths, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.resource_root, microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import json
import shlex
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.receipts import write_json_atomic
from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import read_json_strict


SCHEMA_VERSION = "microcosm_organ_discoverability_matrix_v0"
VALIDATION_SCHEMA_VERSION = "microcosm_organ_discoverability_matrix_validation_v0"
DEFAULT_MATRIX_NAME = "organ_discoverability_matrix.json"
DEFAULT_RECEIPT_NAME = "organ_discoverability_matrix_receipt.json"
AUTHORITY_POSTURE = "derived_projection_not_source_or_release_authority"
SOURCE_REFS = (
    "atlas/entry_packet.json",
    "atlas/agent_task_routes.json::routes",
    "core/organ_registry.json::implemented_organs",
    "core/organ_atlas.json::organs",
    "core/organ_evidence_classes.json::organ_evidence_classes",
    "core/paper_module_capsules.json::paper_modules",
    "core/doctrine_lattice_coverage.json::organ_required_edge_coverage",
    "core/standards_registry.json::standards",
)
REQUIRED_ROW_KEYS = (
    "organ_id",
    "family",
    "first_command",
    "command_runnable_shape",
    "authority_ceiling",
    "evidence_class",
    "paper_module",
    "proof_receipts",
    "task_routes",
    "owner_build_route",
    "reentry_condition",
    "gap_codes",
    "authority_boundary",
)
BANNED_TRUE_AUTHORITY_KEYS = (
    "release_authorized",
    "source_mutation_authorized",
    "provider_call_authorized",
    "generated_projection_is_source_authority",
)


def _as_dict(value: Any) -> dict[str, Any]:
    """
    [ACTION]
    Coerce an arbitrary parsed-JSON value to a dict, defaulting empty.

    - Teleology: shape-guard so downstream row builders read mapping access safely on untrusted JSON.
    - Guarantee: returns value when it is a dict, else a new empty dict; never returns None.
    - Fails: never raises; non-dict input -> {}.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """
    [ACTION]
    Coerce an arbitrary parsed-JSON value to a list, defaulting empty.

    - Teleology: shape-guard so iteration over registry/atlas arrays is safe on untrusted JSON.
    - Guarantee: returns value when it is a list, else a new empty list; never returns None.
    - Fails: never raises; non-list input -> [].
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, list) else []


def _rows(value: Any, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    Extract the dict rows under a named key of a parsed-JSON mapping.

    - Teleology: single accessor for the array-of-objects shape every source registry uses.
    - Guarantee: returns only dict elements of value[key]; non-dict container or non-dict elements are dropped.
    - Fails: never raises; missing key or non-list value -> [].
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [row for row in _as_list(_as_dict(value).get(key)) if isinstance(row, dict)]


def _strings(value: Any) -> list[str]:
    """
    [ACTION]
    Filter a value to its non-blank string elements.

    - Teleology: normalize ref/code lists drawn from untrusted JSON to usable strings.
    - Guarantee: returns each str element whose strip() is truthy, preserving order.
    - Fails: never raises; non-list or non-string elements -> dropped.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [item for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _load_json(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    Strictly parse a required source-JSON file to a dict.

    - Teleology: source-custody read for a mandatory registry/atlas input of the matrix.
    - Guarantee: returns the parsed object when it is a dict, else {}.
    - Fails: read_json_strict raises on missing file or malformed JSON; a non-dict top level -> {}.
    - Reads: the JSON file at path (e.g. core/organ_registry.json, atlas/agent_task_routes.json).
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _optional_json(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    Parse an optional source-JSON file, tolerating absence.

    - Teleology: source-custody read for inputs (capsules, coverage, standards) that may not exist yet.
    - Guarantee: returns {} when path is not a file, else the strict-parsed dict from _load_json.
    - Fails: present-but-malformed JSON raises inside _load_json; absent file -> {}.
    - Reads: the JSON file at path when it exists.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    if not path.is_file():
        return {}
    return _load_json(path)


def _by_organ_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Index registry/atlas/evidence rows by their organ_id.

    - Teleology: O(1) join key so each accepted organ can pull its atlas/evidence row.
    - Guarantee: returns {organ_id: row} for rows whose organ_id is a non-empty string; later duplicates overwrite earlier.
    - Fails: never raises; rows without a string organ_id -> excluded.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        str(row.get("organ_id")): row
        for row in rows
        if isinstance(row.get("organ_id"), str) and row.get("organ_id")
    }


def _standard_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Index standards-registry rows by their standard_id.

    - Teleology: lets each organ row resolve whether its std_microcosm_<id> standard is registered.
    - Guarantee: returns {standard_id: row} for standards rows with a non-empty string standard_id.
    - Fails: never raises; missing standards array or rows without a string standard_id -> excluded.
    - Reads: payload["standards"] (from core/standards_registry.json).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return {
        str(row.get("standard_id")): row
        for row in _rows(payload, "standards")
        if isinstance(row.get("standard_id"), str) and row.get("standard_id")
    }


def _capsules_by_organ(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Index paper-module capsules by the first organ subject they cover.

    - Teleology: maps each organ to its paper-module capsule for paper_module_ref resolution.
    - Guarantee: returns {organ_id: capsule_row} keyed by subjects[kind=="organ"].ref; first capsule per organ wins.
    - Fails: never raises; non-dict subjects, non-organ kinds, or empty refs -> skipped.
    - Reads: payload["paper_modules"][*].subjects (from core/paper_module_capsules.json).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    capsules: dict[str, dict[str, Any]] = {}
    for row in _rows(payload, "paper_modules"):
        for subject in _as_list(row.get("subjects")):
            if not isinstance(subject, dict):
                continue
            if subject.get("kind") != "organ":
                continue
            organ_id = str(subject.get("ref") or "")
            if organ_id and organ_id not in capsules:
                capsules[organ_id] = row
    return capsules


def _coverage_sets(payload: dict[str, Any]) -> dict[str, set[str]]:
    """
    [ACTION]
    Lift doctrine-lattice coverage gaps into organ-id sets.

    - Teleology: source of the doctrine_missing_* gap codes per organ.
    - Guarantee: returns sets for without_paper_module_ref / without_mechanism_ref / without_code_loci, each a set of organ-id strings.
    - Fails: never raises; missing organ_required_edge_coverage -> three empty sets.
    - Reads: payload["organ_required_edge_coverage"] (from core/doctrine_lattice_coverage.json).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    coverage = _as_dict(payload.get("organ_required_edge_coverage"))
    return {
        "without_paper_module_ref": set(_strings(coverage.get("without_paper_module_ref"))),
        "without_mechanism_ref": set(_strings(coverage.get("without_mechanism_ref"))),
        "without_code_loci": set(_strings(coverage.get("without_code_loci"))),
    }


def _route_organ_id_from_ref(value: str) -> str:
    """
    [ACTION]
    Parse an organ_id out of an evidence_ref selector string.

    - Teleology: recover the organ a route's evidence_ref points at, for the route->organ join.
    - Guarantee: returns the stripped token between "organ_id=" and the next "]", else "".
    - Fails: never raises; ref without the organ_id= marker -> "".
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    marker = "organ_id="
    if marker not in value:
        return ""
    tail = value.split(marker, 1)[1]
    return tail.split("]", 1)[0].strip()


def _route_rows_by_organ(routes_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """
    [ACTION]
    Group agent task routes by every organ they reference.

    - Teleology: builds the organ->routes index that gives each row its task-route cards.
    - Guarantee: returns {organ_id: [route,...]} covering primary_organ_id, relevant_organs[].organ_id, and evidence_ref organ; no route duplicated per organ.
    - Fails: never raises; routes without organ references contribute nothing.
    - Reads: routes_payload["routes"] (from atlas/agent_task_routes.json).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for route in _rows(routes_payload, "routes"):
        primary_id = str(route.get("primary_organ_id") or "").strip()
        if primary_id:
            result[primary_id].append(route)
        for organ in _as_list(route.get("relevant_organs")):
            if isinstance(organ, dict) and organ.get("organ_id"):
                organ_id = str(organ["organ_id"])
                if route not in result[organ_id]:
                    result[organ_id].append(route)
        evidence_id = _route_organ_id_from_ref(str(route.get("evidence_ref") or ""))
        if evidence_id and route not in result[evidence_id]:
            result[evidence_id].append(route)
    return result


def _task_route_ref(route: dict[str, Any]) -> str:
    """
    [ACTION]
    Render the canonical generated-route selector ref for a route.

    - Teleology: stable source-ref handle a cold agent uses to re-find the route in the atlas.
    - Guarantee: returns "atlas/agent_task_routes.json::routes[task_class=<task_class>]", using <missing> when absent; the validator requires this exact prefix.
    - Fails: never raises; blank task_class -> "...[task_class=<missing>]".
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    task_class = str(route.get("task_class") or "").strip()
    if not task_class:
        return "atlas/agent_task_routes.json::routes[task_class=<missing>]"
    return f"atlas/agent_task_routes.json::routes[task_class={task_class}]"


def _organ_route_role(route: dict[str, Any], organ_id: str) -> str:
    """
    [ACTION]
    Classify how a route selected a given organ.

    - Teleology: records provenance of the route->organ edge so claims stay traceable.
    - Guarantee: returns "primary", "relevant", "evidence_ref", or "matched" (the validator's allowed set) per how organ_id appears in the route.
    - Fails: never raises; organ not found in any role -> "matched".
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if str(route.get("primary_organ_id") or "").strip() == organ_id:
        return "primary"
    for organ in _as_list(route.get("relevant_organs")):
        if isinstance(organ, dict) and str(organ.get("organ_id") or "") == organ_id:
            return "relevant"
    if _route_organ_id_from_ref(str(route.get("evidence_ref") or "")) == organ_id:
        return "evidence_ref"
    return "matched"


def _organ_route_ref(route: dict[str, Any], organ_id: str) -> str:
    """
    [ACTION]
    Build the organ-specific sub-ref anchored under the task-route ref.

    - Teleology: gives each organ row a precise selector into the route field that named it.
    - Guarantee: returns the task_route_ref suffixed by the role-specific field; always begins with _task_route_ref(route), as the validator's anchoring check requires.
    - Fails: never raises; role "matched" -> bare task_route_ref.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    task_route_ref = _task_route_ref(route)
    role = _organ_route_role(route, organ_id)
    if role == "primary":
        return f"{task_route_ref}.primary_organ_id"
    if role == "relevant":
        return f"{task_route_ref}.relevant_organs[organ_id={organ_id}]"
    if role == "evidence_ref":
        return f"{task_route_ref}.evidence_ref"
    return task_route_ref


def _command_tokens(command: str) -> list[str]:
    """
    [ACTION]
    Shell-tokenize a first-command string, tolerating malformed quoting.

    - Teleology: safe lexing for the runnable-command shape check.
    - Guarantee: returns shlex.split(command); on unbalanced quotes returns [].
    - Fails: never raises; shlex ValueError -> [].
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _is_runnable_public_command(command: str) -> bool:
    """
    [ACTION]
    Decide whether a command is a runnable, public-safe Microcosm invocation.

    - Teleology: release-boundary gate distinguishing a real `microcosm`/`-m microcosm_core` command from private-surface or placeholder text.
    - Guarantee: returns True only for a `microcosm ...`, `python[3] -m microcosm_core....`, or `PYTHONPATH= python[3] -m microcosm_core....` command with no private markers or angle-bracket placeholders; else False.
    - Fails: never raises; empty/blank, any of {raw_seed.md, obsidian/, "provider payload", "operator thread", "HUD/browser"}, or "<"/">" -> False.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond this token check, release, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not command or any(
        banned in command
        for banned in (
            "raw_seed.md",
            "obsidian/",
            "provider payload",
            "operator thread",
            "HUD/browser",
        )
    ):
        return False
    if "<" in command or ">" in command:
        return False
    tokens = _command_tokens(command)
    if not tokens:
        return False
    if tokens[0] == "microcosm":
        return True
    if len(tokens) >= 4 and tokens[0].startswith("PYTHONPATH="):
        return tokens[1] in {"python", "python3"} and tokens[2] == "-m" and tokens[3].startswith(
            "microcosm_core."
        )
    if len(tokens) >= 3 and tokens[0] in {"python", "python3"} and tokens[1] == "-m":
        return tokens[2].startswith("microcosm_core.")
    return False


def _existing_ref(root: Path, ref: str) -> bool:
    """
    [ACTION]
    Test whether a source/receipt ref resolves to a real file on disk.

    - Teleology: drives proof_receipt_hidden / owner_build_route_unclear gap detection by checking the cited evidence actually exists.
    - Guarantee: returns True iff the path part of ref (before "::"/"#") exists, checked absolute, then under root, then under root.parent.
    - Fails: never raises; empty path part -> False; a ref that exists nowhere -> False.
    - Reads: the filesystem path named by ref (no file contents read, only existence).
    - Non-goal: does not validate ref contents, authority, or public-safety; existence only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    ref_path = ref.split("::", 1)[0].split("#", 1)[0].strip()
    if not ref_path:
        return False
    path = Path(ref_path)
    if path.is_absolute():
        return path.exists()
    if (root / path).exists():
        return True
    return (root.parent / path).exists()


def _first_command(registry_row: dict[str, Any], atlas_row: dict[str, Any]) -> str:
    """
    [ACTION]
    Resolve an organ's canonical first command from atlas then registry.

    - Teleology: the single "run this first" handle each discoverability row exposes.
    - Guarantee: returns atlas_row.first_command, else registry_row.validator_command, else "" (stripped).
    - Fails: never raises; neither source present -> "".
    - Reads: atlas_row["first_command"], registry_row["validator_command"].
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return str(atlas_row.get("first_command") or registry_row.get("validator_command") or "").strip()


def _authority_ceiling(registry_row: dict[str, Any], atlas_row: dict[str, Any]) -> str:
    """
    [ACTION]
    Resolve an organ's claim ceiling from atlas then registry.

    - Teleology: surfaces the maximum claim an organ supports, kept verbatim from source.
    - Guarantee: returns atlas_row.claim_ceiling_restated, else registry_row.claim_ceiling, else "" (stripped).
    - Fails: never raises; neither source present -> "".
    - Reads: atlas_row["claim_ceiling_restated"], registry_row["claim_ceiling"].
    - Non-goal: does not widen or restate the ceiling; it only relays the source value.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return str(
        atlas_row.get("claim_ceiling_restated") or registry_row.get("claim_ceiling") or ""
    ).strip()


def _proof_receipts(registry_row: dict[str, Any], task_routes: list[dict[str, Any]]) -> list[str]:
    """
    [ACTION]
    Collect the proof-receipt refs for an organ from registry and its routes.

    - Teleology: enumerates the evidence handles an agent must open before broader claims.
    - Guarantee: returns the sorted unique set of current_authority_receipt + generated_receipts + each route receipt_ref.
    - Fails: never raises; no receipts anywhere -> [].
    - Reads: registry_row["current_authority_receipt"], registry_row["generated_receipts"], task_routes[*]["receipt_ref"].
    - Non-goal: does not check the receipts exist or are valid (see _existing_ref); ref collection only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    refs: list[str] = []
    current = str(registry_row.get("current_authority_receipt") or "").strip()
    if current:
        refs.append(current)
    refs.extend(_strings(registry_row.get("generated_receipts")))
    for route in task_routes:
        receipt_ref = str(route.get("receipt_ref") or "").strip()
        if receipt_ref:
            refs.append(receipt_ref)
    return sorted(set(refs))


def _paper_module_ref(
    *,
    root: Path,
    organ_id: str,
    atlas_row: dict[str, Any],
    capsule_by_organ: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    Resolve an organ's paper-module reference across declared, direct, and capsule sources.

    - Teleology: gives each row a status-tagged handle to its paper-module narrative for the matrix.
    - Guarantee: returns a dict with ref/status/source/resolved; status in {available, declared_unresolved, missing}; resolved True only when the target file exists under root.
    - Fails: never raises; declared ref whose file is absent -> status "declared_unresolved", resolved False; nothing found -> status "missing".
    - Reads: atlas_row["paper_module_ref"], paper_modules/<organ_id>.md, and capsule legacy_markdown_projection under root.
    - Non-goal: does not read or export the paper-module body; resolves the ref handle and existence only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    declared = str(atlas_row.get("paper_module_ref") or "").strip()
    if declared:
        declared_path, _, fragment = declared.partition("#")
        if declared_path and (root / declared_path).is_file():
            if declared_path == "core/paper_module_capsules.json":
                capsule = capsule_by_organ.get(organ_id)
                projection = str(_as_dict(capsule).get("legacy_markdown_projection") or "").strip()
                return {
                    "ref": projection or declared,
                    "capsule_ref": str(_as_dict(capsule).get("id") or fragment or ""),
                    "status": "available" if projection and (root / projection).is_file() else "declared_unresolved",
                    "source": "json_capsule",
                    "resolved": bool(projection and (root / projection).is_file()),
                    "declared_ref": declared,
                    "fragment": fragment or None,
                }
            source = "direct_file" if declared_path.startswith("paper_modules/") else "atlas_declared"
            return {
                "ref": declared,
                "status": "available",
                "source": source,
                "resolved": True,
            }
        return {
            "ref": declared,
            "status": "declared_unresolved",
            "source": "atlas_declared",
            "resolved": False,
            "fragment": fragment or None,
        }
    direct = Path("paper_modules") / f"{organ_id}.md"
    if (root / direct).is_file():
        return {
            "ref": direct.as_posix(),
            "status": "available",
            "source": "direct_file",
            "resolved": True,
        }
    capsule = capsule_by_organ.get(organ_id)
    if capsule:
        projection = str(capsule.get("legacy_markdown_projection") or "").strip()
        return {
            "ref": projection or str(capsule.get("id") or ""),
            "capsule_ref": str(capsule.get("id") or ""),
            "status": "available",
            "source": "json_capsule",
            "resolved": bool(projection and (root / projection).is_file()),
        }
    return {
        "ref": direct.as_posix(),
        "status": "missing",
        "source": "direct_file_expected",
        "resolved": False,
    }


def _source_relation_handle_for_organ(
    route: dict[str, Any],
    organ_id: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    Pull the per-organ source_relation_handle from a route's relevant_organs.

    - Teleology: carries an organ's specific source-relation handle onto its route card.
    - Guarantee: returns the dict handle for the matching relevant-organ entry, else None.
    - Fails: never raises; organ absent or handle not a dict -> None.
    - Reads: route["relevant_organs"][organ_id==organ_id]["source_relation_handle"].
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    for organ in _as_list(route.get("relevant_organs")):
        if not isinstance(organ, dict) or str(organ.get("organ_id") or "") != organ_id:
            continue
        handle = organ.get("source_relation_handle")
        return handle if isinstance(handle, dict) else None
    return None


def _compact_source_relation_summary(route: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Compact a route's source_relation_summary to counts plus a back-ref and sample queries.

    - Teleology: keeps a cold-agent-sized relation summary on each card without inlining full edge bodies.
    - Guarantee: returns a dict with a generated source_ref selector, integer edge/ref/shard/validation counts (0 when absent), and up to 3 query_examples.
    - Fails: never raises; missing summary -> zero counts and empty query_examples.
    - Reads: route["source_relation_summary"], route["task_class"].
    - Non-goal: does not emit full relation edges; preserves count handles only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    summary = _as_dict(route.get("source_relation_summary"))
    return {
        "source_ref": (
            "atlas/agent_task_routes.json::routes"
            f"[task_class={route.get('task_class')}].source_relation_summary"
        ),
        "edge_count": int(summary.get("edge_count") or 0),
        "source_ref_count": int(summary.get("source_ref_count") or 0),
        "target_ref_count": int(summary.get("target_ref_count") or 0),
        "source_shard_ref_count": int(summary.get("source_shard_ref_count") or 0),
        "target_shard_ref_count": int(summary.get("target_shard_ref_count") or 0),
        "validation_ref_count": int(summary.get("validation_ref_count") or 0),
        "query_examples": _strings(summary.get("query_examples"))[:3],
    }


def _task_route_cards(
    root: Path,
    routes: list[dict[str, Any]],
    *,
    organ_id: str,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    Build the per-organ task-route cards for one organ's routes.

    - Teleology: the matrix's runnable-route surface — how an agent reaches and runs each route that names this organ.
    - Guarantee: returns one card per route (sorted by task_class) carrying task_route_ref, role/anchored organ refs, runnable-shape flag, receipt_ref + existence, and the compact relation summary; source_ref equals task_route_ref (validator invariant).
    - Fails: never raises; empty routes -> [].
    - Reads: each route's fields plus receipt-ref existence under root.
    - Escalates-to: validate_organ_discoverability_matrix, which re-checks each card's refs/roles.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    cards: list[dict[str, Any]] = []
    for route in sorted(routes, key=lambda row: str(row.get("task_class") or "")):
        command = str(route.get("first_command") or "")
        task_route_ref = _task_route_ref(route)
        source_relation_handle = _source_relation_handle_for_organ(route, organ_id)
        cards.append(
            {
                "task_class": route.get("task_class"),
                "task_route_ref": task_route_ref,
                "route_role": route.get("route_role"),
                "organ_route_role": _organ_route_role(route, organ_id),
                "organ_route_ref": _organ_route_ref(route, organ_id),
                "primary_organ_id": route.get("primary_organ_id"),
                "organ_count": route.get("organ_count"),
                "first_command": command,
                "command_runnable_shape": _is_runnable_public_command(command),
                "evidence_ref": route.get("evidence_ref"),
                "receipt_ref": route.get("receipt_ref"),
                "receipt_ref_exists": _existing_ref(root, str(route.get("receipt_ref") or "")),
                "drilldown_target": route.get("drilldown_target"),
                "stop_condition": route.get("stop_condition"),
                "source_ref": task_route_ref,
                "source_relation_summary": _compact_source_relation_summary(route),
                "organ_source_relation_handle": source_relation_handle,
            }
        )
    return cards


def _owner_build_route(organ_id: str) -> dict[str, Any]:
    """
    [ACTION]
    Emit the owner/source-authority + builder-check block for an organ row.

    - Teleology: tells an agent which source rows to edit and which builder to re-run instead of hand-editing generated docs.
    - Guarantee: returns a dict naming the owner surface, the three source-authority selectors (registry/atlas/evidence for organ_id), the builder/check commands, and the do-not-hand-edit mutation_boundary.
    - Fails: never raises; pure data construction.
    - Non-goal: does not perform or authorize source mutation or the build; it only names the route.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "owner_surface": "Plectis public organ substrate",
        "source_authority": [
            f"core/organ_registry.json::implemented_organs[organ_id={organ_id}]",
            f"core/organ_atlas.json::organs[organ_id={organ_id}]",
            f"core/organ_evidence_classes.json::organ_evidence_classes[organ_id={organ_id}]",
        ],
        "builder_check_commands": [
            "PYTHONPATH=src python3 scripts/build_organ_atlas.py --check",
            "PYTHONPATH=src python3 -m microcosm_core.projections.organ_surface_contract --root . --card",
            "PYTHONPATH=src python3 -m microcosm_core.projections.organ_discoverability_matrix --root . --check",
        ],
        "mutation_boundary": (
            "Do not hand-edit generated ORGANS.md, ARCHITECTURE.md, AGENT_ROUTES.md, "
            "or atlas/agent_task_routes.json; update source rows and run the owning builder."
        ),
    }


def _gap_codes(
    *,
    root: Path,
    first_command: str,
    command_ok: bool,
    authority_ceiling: str,
    evidence_class: str,
    paper_module: dict[str, Any],
    proof_receipts: list[str],
    task_route_cards: list[dict[str, Any]],
    standard_ref: str,
    coverage_sets: dict[str, set[str]],
    organ_id: str,
) -> list[str]:
    """
    [ACTION]
    Derive the sorted gap-code set for one organ row.

    - Teleology: the matrix's defect detector — names exactly what is missing/unrunnable/hidden for an organ.
    - Guarantee: returns sorted unique gap codes drawn from a fixed vocabulary (missing_first_command, route_points_to_non_runnable_command, missing_authority_ceiling, missing_evidence_class, missing_paper_module_link, proof_receipt_hidden, missing_agent_task_route, owner_build_route_unclear, doctrine_missing_*); empty list means a complete row.
    - Fails: never raises; a fully-populated organ -> [].
    - Reads: receipt/standard ref existence under root, plus coverage_sets membership.
    - Escalates-to: validate_organ_discoverability_matrix, which re-asserts these gaps are declared where required.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    gaps: list[str] = []
    if not first_command:
        gaps.append("missing_first_command")
    elif not command_ok:
        gaps.append("route_points_to_non_runnable_command")
    if not authority_ceiling:
        gaps.append("missing_authority_ceiling")
    if not evidence_class:
        gaps.append("missing_evidence_class")
    if paper_module.get("status") in {"missing", "declared_unresolved"}:
        gaps.append("missing_paper_module_link")
    if not proof_receipts or not any(_existing_ref(root, ref) for ref in proof_receipts):
        gaps.append("proof_receipt_hidden")
    if not task_route_cards:
        gaps.append("missing_agent_task_route")
    elif any(not card.get("command_runnable_shape") for card in task_route_cards):
        gaps.append("route_points_to_non_runnable_command")
    if not standard_ref or not _existing_ref(root, standard_ref):
        gaps.append("owner_build_route_unclear")
    if organ_id in coverage_sets.get("without_paper_module_ref", set()):
        gaps.append("doctrine_missing_paper_module_ref")
    if organ_id in coverage_sets.get("without_mechanism_ref", set()):
        gaps.append("doctrine_missing_mechanism_ref")
    if organ_id in coverage_sets.get("without_code_loci", set()):
        gaps.append("doctrine_missing_code_loci")
    return sorted(set(gaps))


def build_organ_discoverability_matrix(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    Build the GENERATED discoverability-matrix projection over accepted organs.

    - Teleology: compile a cold-agent route map — first command, authority ceiling, evidence, paper module, proof receipts, task routes, owner-build route, and gap codes — for every accepted-current-authority organ, from the source registries only.
    - Guarantee: returns a projection dict with schema_version, status "pass", discoverability_status (complete/gaps_detected), all four authority flags hard-False, gap-sorted rows, gap_counts, omission_receipt, anti_claim, and an embedded validation block.
    - Fails: read_json_strict raises on a missing/malformed required input (entry_packet, agent_task_routes, organ_registry, organ_atlas, organ_evidence_classes); optional inputs absent -> {}; no accepted organs -> empty rows with discoverability_status "complete".
    - Reads: atlas/entry_packet.json, atlas/agent_task_routes.json, core/organ_registry.json, core/organ_atlas.json, core/organ_evidence_classes.json, and optional capsules/coverage/standards under root (or microcosm_root()).
    - When-needed: when an agent needs the ranked discoverability/gap view of accepted organs, or before trusting any organ's run/claim/evidence handles.
    - Escalates-to: the named source JSON + scripts/build_organ_atlas.py and the organ_surface_contract projection that own these rows; this output is a projection, not source-of-truth authority, and authorizes no release or source mutation.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values, declared filesystem outputs.
    """
    resolved_root = Path(root).resolve() if root is not None else microcosm_root()
    entry_packet = _load_json(resolved_root / "atlas/entry_packet.json")
    routes = _load_json(resolved_root / "atlas/agent_task_routes.json")
    registry = _load_json(resolved_root / "core/organ_registry.json")
    atlas = _load_json(resolved_root / "core/organ_atlas.json")
    evidence = _load_json(resolved_root / "core/organ_evidence_classes.json")
    capsules = _optional_json(resolved_root / "core/paper_module_capsules.json")
    coverage = _optional_json(resolved_root / "core/doctrine_lattice_coverage.json")
    standards_registry = _optional_json(resolved_root / "core/standards_registry.json")

    accepted = [
        row
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority" and row.get("organ_id")
    ]
    atlas_by_id = _by_organ_id(_rows(atlas, "organs"))
    evidence_by_id = _by_organ_id(_rows(evidence, "organ_evidence_classes"))
    routes_by_organ = _route_rows_by_organ(routes)
    capsules_by_organ = _capsules_by_organ(capsules)
    coverage_sets = _coverage_sets(coverage)
    standards_by_id = _standard_by_id(standards_registry)

    rows: list[dict[str, Any]] = []
    gap_counter: Counter[str] = Counter()
    for registry_row in accepted:
        organ_id = str(registry_row.get("organ_id"))
        atlas_row = atlas_by_id.get(organ_id, {})
        evidence_row = evidence_by_id.get(organ_id, {})
        organ_routes = routes_by_organ.get(organ_id, [])
        route_cards = _task_route_cards(
            resolved_root,
            organ_routes,
            organ_id=organ_id,
        )
        first_command = _first_command(registry_row, atlas_row)
        authority_ceiling = _authority_ceiling(registry_row, atlas_row)
        evidence_class = str(
            registry_row.get("evidence_class")
            or atlas_row.get("evidence_class")
            or evidence_row.get("evidence_class")
            or ""
        )
        paper_module = _paper_module_ref(
            root=resolved_root,
            organ_id=organ_id,
            atlas_row=atlas_row,
            capsule_by_organ=capsules_by_organ,
        )
        receipt_refs = _proof_receipts(registry_row, organ_routes)
        existing_receipts = [ref for ref in receipt_refs if _existing_ref(resolved_root, ref)]
        standard_ref = f"standards/std_microcosm_{organ_id}.json"
        standard_id = f"std_microcosm_{organ_id}"
        standard_row = standards_by_id.get(standard_id, {})
        command_ok = _is_runnable_public_command(first_command)
        gap_codes = _gap_codes(
            root=resolved_root,
            first_command=first_command,
            command_ok=command_ok,
            authority_ceiling=authority_ceiling,
            evidence_class=evidence_class,
            paper_module=paper_module,
            proof_receipts=receipt_refs,
            task_route_cards=route_cards,
            standard_ref=standard_ref,
            coverage_sets=coverage_sets,
            organ_id=organ_id,
        )
        gap_counter.update(gap_codes)
        rows.append(
            {
                "organ_id": organ_id,
                "display_name": atlas_row.get("display_name")
                or organ_id.replace("_", " ").title(),
                "family": atlas_row.get("family"),
                "first_command": first_command,
                "command_runnable_shape": command_ok,
                "authority_ceiling": authority_ceiling,
                "evidence_class": evidence_class,
                "evidence_strength_rank": registry_row.get("evidence_strength_rank"),
                "paper_module": paper_module,
                "proof_receipts": {
                    "refs": receipt_refs,
                    "existing_refs": existing_receipts,
                    "hidden_or_missing_count": len(receipt_refs) - len(existing_receipts),
                },
                "task_routes": route_cards,
                "standard": {
                    "standard_id": standard_id,
                    "standard_ref": standard_ref,
                    "standard_ref_exists": _existing_ref(resolved_root, standard_ref),
                    "standards_registry_ref": (
                        "core/standards_registry.json::standards"
                        f"[standard_id={standard_id}]"
                    )
                    if standard_row
                    else "",
                },
                "owner_build_route": _owner_build_route(organ_id),
                "reentry_condition": (
                    "If gap_codes is non-empty, populate the named source-authority rows "
                    "or run the owning builder/check route; if empty, run first_command and "
                    "open proof_receipts.existing_refs before making broader claims."
                ),
                "gap_codes": gap_codes,
                "source_refs": [
                    f"core/organ_registry.json::implemented_organs[organ_id={organ_id}]",
                    f"core/organ_atlas.json::organs[organ_id={organ_id}]",
                    f"core/organ_evidence_classes.json::organ_evidence_classes[organ_id={organ_id}]",
                    "atlas/agent_task_routes.json::routes",
                    "core/paper_module_capsules.json::paper_modules",
                ],
                "authority_boundary": (
                    "discoverability row only; source JSON, validator receipts, paper modules, "
                    "standards, and builder checks remain authority"
                ),
            }
        )

    rows.sort(
        key=lambda row: (
            -len(row["gap_codes"]),
            -int(row.get("evidence_strength_rank") or 0),
            str(row["organ_id"]),
        )
    )
    validation_targets = [
        "missing_first_command",
        "route_points_to_non_runnable_command",
        "missing_authority_ceiling",
        "missing_paper_module_link",
        "proof_receipt_hidden",
        "owner_build_route_unclear",
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "discoverability_status": "gaps_detected" if gap_counter else "complete",
        "authority_posture": AUTHORITY_POSTURE,
        "release_authorized": False,
        "source_mutation_authorized": False,
        "provider_call_authorized": False,
        "generated_projection_is_source_authority": False,
        "source_refs": list(SOURCE_REFS),
        "source_summary": {
            "type_a_first_screen_command": _as_dict(entry_packet.get("local_first_screen_route")).get(
                "command"
            )
            or entry_packet.get("first_command"),
            "accepted_organ_count": len(accepted),
            "task_route_count": len(_rows(routes, "routes")),
            "paper_module_capsule_count": len(_rows(capsules, "paper_modules")),
        },
        "gap_counts": dict(sorted(gap_counter.items())),
        "validation_target_gap_counts": {
            code: gap_counter.get(code, 0) for code in validation_targets
        },
        "row_count": len(rows),
        "complete_row_count": sum(1 for row in rows if not row["gap_codes"]),
        "top_gap_rows": [
            {
                "organ_id": row["organ_id"],
                "gap_codes": row["gap_codes"],
                "first_command": row["first_command"],
                "paper_module": row["paper_module"],
                "reentry_condition": row["reentry_condition"],
            }
            for row in rows[:12]
        ],
        "rows": rows,
        "omission_receipt": {
            "omitted": [
                "full receipt bodies",
                "full generated public docs",
                "full organ source bodies",
                "private Work Ledger state",
                "raw operator voice or provider/account/session payloads",
            ],
            "reason": (
                "This matrix preserves cold-agent route handles and gap codes only. "
                "Authority remains with the named source JSON, paper modules, standards, "
                "validators, and proof receipts."
            ),
            "reentry_condition": (
                "Rebuild this projection when organ registry, atlas, evidence classes, "
                "paper-module capsules, doctrine-lattice coverage, or task routes change."
            ),
        },
        "anti_claim": (
            "This matrix is not an organ registry, paper-module source, release receipt, "
            "source-mutation authority, provider-call authority, or proof of whole-system correctness."
        ),
    }
    payload["validation"] = validate_organ_discoverability_matrix(payload)
    return payload


def validate_organ_discoverability_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Validate a discoverability-matrix payload's shape and authority posture.

    - Teleology: the matrix's own gate — proves schema, projection-only posture, banned-authority absence, required row keys, gap-declaration honesty, and route-card ref anchoring before the payload is trusted.
    - Guarantee: returns {schema_version, status, error_count, errors[], row_count}; status is "pass" iff errors is empty, else "blocked"; each error carries path/code/message.
    - Fails: never raises; any violation (wrong schema_version, non-projection authority_posture, a banned authority key True, missing rows/keys, undeclared gap, mismatched route refs) -> appended error and status "blocked".
    - When-needed: to confirm a built or on-disk matrix is well-formed and authority-safe before consuming it.
    - Escalates-to: the named row source JSON and tests/standards for the matrix; this is a shape/posture check, not source or release authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    errors: list[dict[str, str]] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            {
                "path": "schema_version",
                "code": "unexpected_schema_version",
                "message": f"Expected {SCHEMA_VERSION}.",
            }
        )
    if payload.get("authority_posture") != AUTHORITY_POSTURE:
        errors.append(
            {
                "path": "authority_posture",
                "code": "authority_posture_not_projection_only",
                "message": "Matrix must identify itself as projection-only.",
            }
        )
    for key in BANNED_TRUE_AUTHORITY_KEYS:
        if payload.get(key) is True:
            errors.append(
                {
                    "path": key,
                    "code": "banned_authority_claim_true",
                    "message": f"Matrix cannot authorize {key}.",
                }
            )
    rows = _rows(payload, "rows")
    if not rows:
        errors.append(
            {
                "path": "rows",
                "code": "no_organ_rows",
                "message": "Matrix must include accepted organ rows.",
            }
        )
    for index, row in enumerate(rows):
        row_path = f"rows[{index}]"
        for key in REQUIRED_ROW_KEYS:
            if key not in row:
                errors.append(
                    {
                        "path": f"{row_path}.{key}",
                        "code": "missing_required_row_key",
                        "message": f"Row must preserve {key}.",
                    }
                )
        gap_codes = set(_strings(row.get("gap_codes")))
        first_command = str(row.get("first_command") or "")
        command_ok = bool(row.get("command_runnable_shape"))
        if first_command and not _is_runnable_public_command(first_command) and command_ok:
            errors.append(
                {
                    "path": f"{row_path}.command_runnable_shape",
                    "code": "command_shape_false_positive",
                    "message": "Non-runnable command cannot be marked runnable.",
                }
            )
        if not first_command and "missing_first_command" not in gap_codes:
            errors.append(
                {
                    "path": f"{row_path}.gap_codes",
                    "code": "missing_first_command_gap_not_declared",
                    "message": "Rows without a first command must declare the gap.",
                }
            )
        if first_command and not command_ok and "route_points_to_non_runnable_command" not in gap_codes:
            errors.append(
                {
                    "path": f"{row_path}.gap_codes",
                    "code": "non_runnable_command_gap_not_declared",
                    "message": "Rows with non-runnable commands must declare the gap.",
                }
            )
        if not str(row.get("authority_ceiling") or "") and "missing_authority_ceiling" not in gap_codes:
            errors.append(
                {
                    "path": f"{row_path}.gap_codes",
                    "code": "missing_authority_ceiling_gap_not_declared",
                    "message": "Rows without a claim ceiling must declare the gap.",
                }
            )
        paper = _as_dict(row.get("paper_module"))
        if paper.get("status") in {"missing", "declared_unresolved"} and "missing_paper_module_link" not in gap_codes:
            errors.append(
                {
                    "path": f"{row_path}.gap_codes",
                    "code": "missing_paper_module_gap_not_declared",
                    "message": "Missing paper-module links must be explicit.",
                }
            )
        receipts = _as_dict(row.get("proof_receipts"))
        if not _strings(receipts.get("refs")) and "proof_receipt_hidden" not in gap_codes:
            errors.append(
                {
                    "path": f"{row_path}.gap_codes",
                    "code": "missing_receipt_gap_not_declared",
                    "message": "Rows without proof receipts must declare the gap.",
                }
            )
        for route_index, route_card in enumerate(_as_list(row.get("task_routes"))):
            if not isinstance(route_card, dict):
                continue
            route_path = f"{row_path}.task_routes[{route_index}]"
            task_route_ref = str(route_card.get("task_route_ref") or "")
            source_ref = str(route_card.get("source_ref") or "")
            organ_route_role = str(route_card.get("organ_route_role") or "")
            organ_route_ref = str(route_card.get("organ_route_ref") or "")
            if not task_route_ref.startswith("atlas/agent_task_routes.json::routes[task_class="):
                errors.append(
                    {
                        "path": f"{route_path}.task_route_ref",
                        "code": "missing_task_route_ref",
                        "message": "Task route cards must expose the exact generated route selector ref.",
                    }
                )
            if source_ref != task_route_ref:
                errors.append(
                    {
                        "path": f"{route_path}.source_ref",
                        "code": "route_source_ref_mismatch",
                        "message": "Route card source_ref must match task_route_ref.",
                    }
                )
            if not str(route_card.get("route_role") or ""):
                errors.append(
                    {
                        "path": f"{route_path}.route_role",
                        "code": "missing_route_role",
                        "message": "Task route cards must preserve the generated route_role.",
                    }
                )
            if organ_route_role not in {"primary", "relevant", "evidence_ref", "matched"}:
                errors.append(
                    {
                        "path": f"{route_path}.organ_route_role",
                        "code": "unexpected_organ_route_role",
                        "message": "Task route cards must classify how the row selected this organ.",
                    }
                )
            if not task_route_ref or not organ_route_ref.startswith(task_route_ref):
                errors.append(
                    {
                        "path": f"{route_path}.organ_route_ref",
                        "code": "organ_route_ref_not_anchored",
                        "message": "Organ route refs must stay anchored to the task route ref.",
                    }
                )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "pass" if not errors else "blocked",
        "error_count": len(errors),
        "errors": errors,
        "row_count": len(rows),
    }


def compile_paths(
    root: str | Path | None = None,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    Build the matrix projection and atomically write its GENERATED artifact + receipt.

    - Teleology: the write step that materializes the discoverability matrix and a body-free receipt to an output directory.
    - Guarantee: returns the built payload; when out is given, creates out and atomically writes organ_discoverability_matrix.json plus a body_in_receipt=False receipt mirroring status/counts/gap_counts/authority_posture.
    - Fails: build_organ_discoverability_matrix raises on a missing/malformed required source; mkdir/write surface OSError from the filesystem; out=None -> no files written.
    - Writes: <out>/organ_discoverability_matrix.json and <out>/organ_discoverability_matrix_receipt.json (only when out is provided).
    - When-needed: to regenerate the on-disk matrix + receipt as part of an organ-projection rebuild.
    - Escalates-to: scripts/build_organ_atlas.py and the source registries this projection derives from; writing this artifact authorizes neither release nor source mutation.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    """
    payload = build_organ_discoverability_matrix(root=root)
    if out is not None:
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        write_json_atomic(out_path / DEFAULT_MATRIX_NAME, payload)
        receipt = {
            "schema_version": "microcosm_organ_discoverability_matrix_receipt_v0",
            "status": payload["validation"]["status"],
            "discoverability_status": payload["discoverability_status"],
            "source_refs": payload["source_refs"],
            "row_count": payload["row_count"],
            "complete_row_count": payload["complete_row_count"],
            "gap_counts": payload["gap_counts"],
            "authority_posture": AUTHORITY_POSTURE,
            "body_in_receipt": False,
        }
        write_json_atomic(out_path / DEFAULT_RECEIPT_NAME, receipt)
    return payload


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entrypoint building the Microcosm accepted-organ discoverability matrix.

    - Teleology: regenerates/validates the discoverability matrix over accepted organs from the shell.
    - Guarantee: parses argv, calls compile_paths, prints the JSON payload, and returns 0 unless --check is set and validation.status != "pass" (then 1).
    - Fails: --check with non-pass validation -> exit code 1; missing/invalid root surfaces inside compile_paths.
    - Reads: argv and the substrate root compile_paths walks.
    - Writes: payload to --out when provided; stdout.
    - When-needed: regenerating or checking the organ discoverability matrix.
    - Escalates-to: compile_paths.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    parser = argparse.ArgumentParser(
        description="Build the Microcosm accepted-organ discoverability matrix."
    )
    parser.add_argument("--root", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = compile_paths(root=args.root, out=args.out)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["validation"]["status"] == "pass" or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
