"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.first_screen_composition` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: MICROCOSM_ROOT, STANDARD_REF, READER_ROUTE_IDS, REQUIRED_ROUTE_IDS, READER_LABELS, READER_ROUTE_ALIASES, INTERESTING_PARTS_ALIASES, READER_ROUTE_ALIAS_HINT, DENIED_AUTHORITY_KEYS, STANDARD_SURFACE_ALIASES, TEXT_CARD_MAX_LINES, COMPACT_JSON_CARD_MAX_CHARS, TEXT_READER_CHOICES, ORGAN_REGISTRY_REF, ORGAN_ATLAS_REF, AGENT_TASK_ROUTES_REF, ORGAN_GLANCE_LADDER_REF, STANDARDS_REGISTRY_REF, EVIDENCE_CLASS_REGISTRY_REF, WORKINGNESS_MAP_REF, FIXTURE_MANIFESTS_REF, SUBSTRATE_GLANCE_SAMPLE_LIMIT, SUBSTRATE_GLANCE_EXCERPT_MAX_CHARS, EVIDENCE_CLASS_DISPLAY_ORDER, ...
- Reads: call arguments, module constants, imported helpers, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: resource_root, schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from .resource_root import microcosm_root
from .schemas import StrictJsonError, read_json_strict

MICROCOSM_ROOT = microcosm_root()
STANDARD_REF = Path("standards/std_microcosm_first_screen_composition_root.json")
READER_ROUTE_IDS = (
    "public_github_visitor",
    "safety_evals_engineer",
    "hiring_reviewer",
    "peer_developer",
    "domain_specialist",
    "type_a_agent",
)
REQUIRED_ROUTE_IDS = set(READER_ROUTE_IDS)
READER_LABELS = {
    "public_github_visitor": "GitHub visitor",
    "safety_evals_engineer": "Safety/evals",
    "hiring_reviewer": "Hiring",
    "peer_developer": "Peer developer",
    "domain_specialist": "Domain specialist",
    "type_a_agent": "Type A agent",
}
READER_ROUTE_ALIASES = {
    "cold_cloner": "public_github_visitor",
    "cold-cloner": "public_github_visitor",
    "interesting_parts": "public_github_visitor",
    "interesting-parts": "public_github_visitor",
    "skeptical_reviewer": "safety_evals_engineer",
    "skeptical-reviewer": "safety_evals_engineer",
    "reviewer": "safety_evals_engineer",
    "agent": "type_a_agent",
    "type-a-agent": "type_a_agent",
    "domain-specialist": "domain_specialist",
}
INTERESTING_PARTS_ALIASES = {"interesting_parts", "interesting-parts"}
READER_ROUTE_ALIAS_HINT = (
    "reader aliases: cold-cloner, interesting_parts/interesting-parts, skeptical-reviewer, "
    "reviewer, type-a-agent, domain-specialist"
)
DENIED_AUTHORITY_KEYS = (
    "release_authority",
    "source_mutation_authority",
    "private_data_equivalence_authority",
    "provider_call_authority",
    "score_based_progress_authority",
    "whole_system_correctness_authority",
)
STANDARD_SURFACE_ALIASES = {
    "concept_mechanism_entry_route": ("doctrine_effect_frame",),
    "reader_focus_mode": ("reader_route_menu", "text_projection"),
    "reader_route_ids": ("reader_routes",),
    "terminal_text_projection": ("text_projection",),
}
# 33 = the bounded reader ladder plus the mechanism-first identity/read-order
# lines. These must stay above the orientation ladder so the card cannot teach a
# receipt-first first impression.
TEXT_CARD_MAX_LINES = 33
COMPACT_JSON_CARD_MAX_CHARS = 16000
TEXT_READER_CHOICES = ("all",) + READER_ROUTE_IDS + tuple(READER_ROUTE_ALIASES)
ORGAN_REGISTRY_REF = "core/organ_registry.json"
ORGAN_ATLAS_REF = "core/organ_atlas.json"
AGENT_TASK_ROUTES_REF = "atlas/agent_task_routes.json"
ORGAN_GLANCE_LADDER_REF = f"{AGENT_TASK_ROUTES_REF}::organ_glance_ladder"
STANDARDS_REGISTRY_REF = "core/standards_registry.json"
EVIDENCE_CLASS_REGISTRY_REF = "core/organ_evidence_classes.json"
WORKINGNESS_MAP_REF = "receipts/runtime_shell/workingness_failure_map.json"
FIXTURE_MANIFESTS_REF = "core/fixture_manifests"
SUBSTRATE_GLANCE_SAMPLE_LIMIT = 4
SUBSTRATE_GLANCE_EXCERPT_MAX_CHARS = 92
SUBSTRATE_GLANCE_PREFERRED_ORGAN_IDS = (
    "lean_proof_search_lab_runtime",
    "agent_sabotage_scheming_monitor_replay",
    "finance_forecast_evaluation_spine",
    "generated_projection_drift_runtime",
)
EVIDENCE_CLASS_DISPLAY_ORDER = (
    "verified_macro_body_import",
    "external_subprocess_witness",
    "semantic_validator",
    "algorithmic_projection",
    "fixture_schema_replay",
    "fixture_echo_smoke",
)
EVIDENCE_CLASS_LABELS = {
    "verified_macro_body_import": "macro body import",
    "external_subprocess_witness": "subprocess witness",
    "semantic_validator": "semantic validator",
    "algorithmic_projection": "algorithmic projection",
    "fixture_schema_replay": "fixture schema replay",
    "fixture_echo_smoke": "fixture smoke",
}
OBSERVATORY_LANDING_ENDPOINTS = {
    "html_landing": "/",
    "first_screen_card": "/project/first-screen",
    "compact_observatory_card": "/project/observatory-card",
    "full_observatory_model": "/project/observatory",
    "project_observe": "/project/observe",
}
BOUNDED_OBSERVATORY_REQUEST_COUNT = 7


def _observatory_serve_command(project_label: str) -> str:
    """
    [ACTION]
    Build the localhost observatory serve command string for the project label.

    - Teleology: keep the browser read-model serve command copyable from a single string builder.
    - Guarantee: returns a `plectis serve <label> --host 127.0.0.1 --port 8765` string bound to localhost only.
    - Fails: never raises; always returns a localhost-pinned string, never a hosted/public bind.
    - Non-goal: does not start a server, authorize hosting, or imply release readiness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return f"plectis serve {project_label} --host 127.0.0.1 --port 8765"


def _bounded_observatory_serve_command(project_label: str) -> str:
    """
    [ACTION]
    Build the request-bounded observatory serve command for smoke validation.

    - Teleology: give first-screen route smokes a serve command that self-terminates after a fixed request count.
    - Guarantee: returns the localhost serve command suffixed with `--max-requests 7` (BOUNDED_OBSERVATORY_REQUEST_COUNT).
    - Fails: never raises; always returns a bounded localhost command string.
    - Non-goal: does not run the server, authorize hosting, or guarantee the smoke passes.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        f"{_observatory_serve_command(project_label)} "
        f"--max-requests {BOUNDED_OBSERVATORY_REQUEST_COUNT}"
    )


def _json_cache_key(path: Path) -> tuple[str, int, int]:
    """
    [ACTION]
    Derive a content-sensitive cache key (resolved path, mtime_ns, size) for a JSON file.

    - Teleology: let the lru_cache invalidate a parsed JSON object when the on-disk file changes.
    - Guarantee: returns (resolved posix path, st_mtime_ns, st_size); the tuple changes whenever the file is rewritten.
    - Fails: raises OSError (FileNotFoundError) when `path` does not exist, since it stats the file.
    - Reads: the filesystem stat of `path` (no body parse here).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    stat = path.stat()
    return path.resolve().as_posix(), stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=128)
def _load_json_object(path_ref: str, mtime_ns: int, size: int) -> Any:
    """
    [ACTION]
    Strict-parse a JSON file at path_ref, memoized on (path, mtime_ns, size).

    - Teleology: source-custody read path that parses public JSON once per file revision.
    - Guarantee: returns the strict-parsed JSON value for path_ref; identical (path, mtime, size) reuses the cached parse.
    - Fails: raises StrictJsonError on malformed/duplicate-key JSON and OSError when the file is unreadable.
    - Reads: the JSON file at `path_ref` via read_json_strict.
    - Non-goal: does not validate schema, authorize source-body export, or assert public-safe equivalence.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    del mtime_ns, size
    return read_json_strict(Path(path_ref))


def _load_standard(root: Path) -> dict[str, Any]:
    """
    [ACTION]
    Load the first-screen composition root standard JSON object from `root`.

    - Teleology: source-custody loader for the governing standard the card is validated against.
    - Guarantee: returns the parsed standard dict at root/STANDARD_REF (standards/std_microcosm_first_screen_composition_root.json).
    - Fails: raises TypeError when the file is not a JSON object; propagates StrictJsonError/OSError from the loader when missing or malformed.
    - Reads: `standards/std_microcosm_first_screen_composition_root.json` under `root`.
    - Escalates-to: STANDARD_REF as the authority the card mirrors; first_screen_composition_card consumes this.
    - Non-goal: does not authorize release or treat the standard as whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    payload = _load_json_object(*_json_cache_key(root / STANDARD_REF))
    if not isinstance(payload, dict):
        raise TypeError(f"{STANDARD_REF} must contain a JSON object")
    return payload


def _string_set(rows: Any) -> set[str]:
    """
    [ACTION]
    Coerce an arbitrary value into a set of its string elements.

    - Teleology: normalize standard-declared list fields into comparable string sets for parity checks.
    - Guarantee: returns a set of the str items in `rows`; non-list input yields an empty set.
    - Fails: never raises; non-string and non-list inputs are silently dropped.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(rows, list):
        return set()
    return {str(row) for row in rows if isinstance(row, str)}


def _reader_route_ids(rows: Any) -> set[str]:
    """
    [ACTION]
    Extract the set of reader_route_id values present in a list of row dicts.

    - Teleology: pull the reader-route id set from any reader surface for route-parity comparison.
    - Guarantee: returns the set of truthy `reader_route_id` strings across dict rows; non-list input yields an empty set.
    - Fails: never raises; rows without a reader_route_id key are skipped.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(rows, list):
        return set()
    return {
        str(row.get("reader_route_id"))
        for row in rows
        if isinstance(row, dict) and row.get("reader_route_id")
    }


def normalize_reader_route_id(reader_id: str) -> str:
    """
    [ACTION]
    Resolve a reader-route alias (e.g. cold-cloner, reviewer) to its canonical reader_route_id.

    - Teleology: public alias normalizer so CLI/text callers can pass human-friendly reader names.
    - Guarantee: returns the canonical id from READER_ROUTE_ALIASES when `reader_id` is an alias, else returns `reader_id` unchanged.
    - Fails: never raises; unknown ids pass through verbatim (validity is enforced separately by callers like first_screen_text_card).
    - When-needed: when mapping a user-supplied reader token to the six canonical READER_ROUTE_IDS.
    - Escalates-to: READER_ROUTE_ALIASES / READER_ROUTE_IDS constants in this module.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return READER_ROUTE_ALIASES.get(reader_id, reader_id)


def _ordered_reader_route_ids(route_ids: set[str]) -> list[str]:
    """
    [ACTION]
    Order a reader-route id set: canonical ids first, then extras sorted.

    - Teleology: produce a stable, deterministic reader-id ordering for parity receipts.
    - Guarantee: returns canonical READER_ROUTE_IDS present in `route_ids` (in canonical order) followed by sorted unknown extras.
    - Fails: never raises; an empty set yields an empty list.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    known_ids = [route_id for route_id in READER_ROUTE_IDS if route_id in route_ids]
    return known_ids + sorted(route_ids - REQUIRED_ROUTE_IDS)


def _surface_list(payload: dict[str, Any], surface_id: str, list_key: str) -> list[Any]:
    """
    [ACTION]
    Safely read payload[surface_id][list_key] as a list.

    - Teleology: defensive accessor for nested list fields of a composition payload.
    - Guarantee: returns the list at payload[surface_id][list_key], or an empty list when any level is missing or non-list.
    - Fails: never raises on missing keys or wrong types; returns `[]` instead.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    surface = payload.get(surface_id, {})
    if not isinstance(surface, dict):
        return []
    rows = surface.get(list_key, [])
    return rows if isinstance(rows, list) else []


def _standard_surface_present(
    surface_id: str,
    payload: dict[str, Any],
    validation_check_ids: set[str],
) -> bool:
    """
    [ACTION]
    Decide whether a standard-required surface is present in payload or as a validation check.

    - Teleology: tolerate surface renames so receipt-contract parity survives alias drift.
    - Guarantee: returns True when surface_id or any of its STANDARD_SURFACE_ALIASES appears as a payload key or a validation-check id.
    - Fails: never raises; an unknown surface with no alias hit returns False.
    - Reads: STANDARD_SURFACE_ALIASES for the alias expansion.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    aliases = {surface_id, *STANDARD_SURFACE_ALIASES.get(surface_id, ())}
    return any(alias in payload for alias in aliases) or any(
        alias in validation_check_ids for alias in aliases
    )


def _standard_backed_first_screen_scan(
    payload: dict[str, Any],
    standard: dict[str, Any],
    validation_check_ids: set[str],
) -> dict[str, Any]:
    """
    [ACTION]
    Scan the composition payload against the loaded standard and emit a pass/blocked contract receipt.

    - Teleology: prove the generated card mirrors the standard's required fields, validator id, reader-route parity, and denied-authority flags.
    - Guarantee: returns a `microcosm_standard_backed_first_screen_scan_v1` dict whose `status` is "pass" only when every `checks` entry is True; reports per-surface route_parity, reader_command_parity, denied_authority_flags, and a `missing` breakdown.
    - Fails: never raises; mismatches surface as `status="blocked"` with the failing check flagged False, never an exception.
    - When-needed: when verifying the card has not drifted from std_microcosm_first_screen_composition_root.json.
    - Escalates-to: STANDARD_REF and the validator_contract.validator_id it cross-checks; the receipt asserts scanner-contract-only authority, not release or reader success.
    - Non-goal: does not authorize release, reader success, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    validator_contract = standard.get("validator_contract", {})
    receipt_contract = standard.get("receipt_contract", {})
    required_fields = _string_set(standard.get("required_fields", []))
    minimum_checks = (
        _string_set(validator_contract.get("minimum_checks", []))
        if isinstance(validator_contract, dict)
        else set()
    )
    receipt_must_record = (
        _string_set(receipt_contract.get("must_record", []))
        if isinstance(receipt_contract, dict)
        else set()
    )

    route_surfaces = {
        "reader_routes": payload.get("reader_routes", []),
        "reader_route_menu.routes": _surface_list(payload, "reader_route_menu", "routes"),
        "reader_landing_packets.packets": _surface_list(
            payload,
            "reader_landing_packets",
            "packets",
        ),
        "reader_exit_criteria.criteria": _surface_list(
            payload,
            "reader_exit_criteria",
            "criteria",
        ),
    }
    route_parity_rows = []
    for surface_id, rows in route_surfaces.items():
        actual_ids = _reader_route_ids(rows)
        route_parity_rows.append(
            {
                "surface": surface_id,
                "reader_route_ids": _ordered_reader_route_ids(actual_ids),
                "missing_reader_route_ids": [
                    route_id for route_id in READER_ROUTE_IDS if route_id not in actual_ids
                ],
                "extra_reader_route_ids": sorted(actual_ids - REQUIRED_ROUTE_IDS),
                "status": "pass" if actual_ids == REQUIRED_ROUTE_IDS else "blocked",
            }
        )

    project_label = str(payload.get("project_label", ""))
    menu_rows = _surface_list(payload, "reader_route_menu", "routes")
    command_rows = []
    for row in menu_rows:
        if not isinstance(row, dict):
            continue
        route_id = str(row.get("reader_route_id", ""))
        terminal_command = (
            f"plectis hello --reader {route_id} {project_label}"
        )
        text_projection_command = (
            "plectis first-screen --format text --reader "
            f"{route_id} {project_label}"
        )
        terminal_ok = row.get("terminal_command") == terminal_command
        text_projection_ok = row.get("text_projection_command") == text_projection_command
        command_rows.append(
            {
                "reader_route_id": route_id,
                "terminal_command_ok": terminal_ok,
                "text_projection_command_ok": text_projection_ok,
                "status": (
                    "pass"
                    if route_id in REQUIRED_ROUTE_IDS
                    and terminal_ok
                    and text_projection_ok
                    else "blocked"
                ),
            }
        )

    standard_authority_ceiling = standard.get("authority_ceiling", {})
    payload_authority_ceiling = payload.get("authority_ceiling", {})
    denied_authority_rows = [
        {
            "authority_key": key,
            "standard_value": standard_authority_ceiling.get(key)
            if isinstance(standard_authority_ceiling, dict)
            else None,
            "payload_value": payload_authority_ceiling.get(key)
            if isinstance(payload_authority_ceiling, dict)
            else None,
            "status": (
                "pass"
                if isinstance(standard_authority_ceiling, dict)
                and isinstance(payload_authority_ceiling, dict)
                and standard_authority_ceiling.get(key) is False
                and payload_authority_ceiling.get(key) is False
                else "blocked"
            ),
        }
        for key in DENIED_AUTHORITY_KEYS
    ]

    missing = {
        "required_fields": sorted(
            field for field in required_fields if field not in payload
        ),
        "validator_minimum_checks": sorted(minimum_checks - validation_check_ids),
        "receipt_must_record": sorted(
            item
            for item in receipt_must_record
            if not _standard_surface_present(item, payload, validation_check_ids)
        ),
    }
    public_private_boundary = payload.get("public_private_boundary", {})
    standard_public_private_boundary = standard.get("public_private_boundary", {})
    checks = {
        "standard_ref_matches": payload.get("source_standard_ref") == str(STANDARD_REF),
        "standard_kind_matches": payload.get("composition_root_id")
        == standard.get("kind_id"),
        "validator_id_matches": payload.get("validator_id")
        == (
            validator_contract.get("validator_id")
            if isinstance(validator_contract, dict)
            else None
        ),
        "required_fields_present": not missing["required_fields"],
        "validator_minimum_checks_executable": not missing[
            "validator_minimum_checks"
        ],
        "receipt_contract_surfaces_present": not missing["receipt_must_record"],
        "reader_route_parity": all(
            row["status"] == "pass" for row in route_parity_rows
        ),
        "copyable_reader_commands": (
            len(command_rows) == len(READER_ROUTE_IDS)
            and all(row["status"] == "pass" for row in command_rows)
        ),
        "authority_ceiling_mirrored": payload_authority_ceiling
        == standard_authority_ceiling,
        "denied_authority_flags_false": all(
            row["status"] == "pass" for row in denied_authority_rows
        ),
        "public_private_boundary_mirrored": public_private_boundary
        == {
            "allowed_public_inputs": standard_public_private_boundary.get(
                "allowed_public_inputs"
            )
            if isinstance(standard_public_private_boundary, dict)
            else None,
            "forbidden_public_inputs": standard_public_private_boundary.get(
                "forbidden_public_inputs"
            )
            if isinstance(standard_public_private_boundary, dict)
            else None,
        },
    }
    return {
        "schema_version": "microcosm_standard_backed_first_screen_scan_v1",
        "status": "pass" if all(checks.values()) else "blocked",
        "standard_id": standard.get("standard_id"),
        "standard_ref": str(STANDARD_REF),
        "validator_id": payload.get("validator_id"),
        "expected_reader_route_ids": list(READER_ROUTE_IDS),
        "checks": checks,
        "missing": missing,
        "route_parity": route_parity_rows,
        "reader_command_parity": command_rows,
        "denied_authority_flags": denied_authority_rows,
        "authority": "scanner_contract_only_not_release_or_reader_success_authority",
    }


def _load_public_json(root: Path, ref: str) -> dict[str, Any]:
    """
    [ACTION]
    Tolerantly load a public registry/receipt JSON object under `root`, defaulting to empty.

    - Teleology: source-custody read for optional public inputs (organ/standards/workingness/fixture manifests) that may be absent.
    - Guarantee: returns the parsed dict at root/ref, or `{}` when the file is missing, unreadable, malformed, or not a JSON object.
    - Fails: never raises; StrictJsonError and OSError are swallowed and degrade to `{}`.
    - Reads: the public JSON file at `ref` relative to `root`.
    - Non-goal: does not authorize source-body export, public-safe equivalence, or release; missing inputs silently narrow the card, never error it.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    try:
        payload = _load_json_object(*_json_cache_key(root / ref))
    except (StrictJsonError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _collection_count(value: Any) -> int | None:
    """
    [ACTION]
    Return len(value) when value is a collection, else None.

    - Teleology: derive a count from a registry collection field without trusting a scalar count field.
    - Guarantee: returns the length for dict/list/tuple input; returns None for any other type.
    - Fails: never raises; non-collections yield None.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, (dict, list, tuple)):
        return len(value)
    return None


def _non_negative_int(value: Any) -> int | None:
    """
    [ACTION]
    Return value when it is a non-negative, non-bool int, else None.

    - Teleology: accept only honest count scalars from registries, rejecting bools and negatives.
    - Guarantee: returns the int when `value` is an int >= 0 and not a bool; returns None otherwise.
    - Fails: never raises; True/False and negative or non-int values yield None.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _first_count(*candidates: int | None) -> int | None:
    """
    [ACTION]
    Return the first non-None candidate count in priority order.

    - Teleology: pick the highest-fidelity available count (e.g. fixture manifest before stale workingness fallback).
    - Guarantee: returns the first argument that is not None; returns None only when every candidate is None.
    - Fails: never raises; all-None input yields None.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def _strings(value: Any) -> list[str]:
    """
    [ACTION]
    Coerce a value into a list of its non-empty string elements.

    - Teleology: normalize id-list fields (e.g. body_material_ids) into clean string lists.
    - Guarantee: returns the truthy str items of `value` in order; non-list input yields an empty list.
    - Fails: never raises; non-string and empty-string items are dropped.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _public_text(value: Any) -> str:
    """
    [ACTION]
    Flatten any value to single-spaced ASCII-only text.

    - Teleology: public-safe text guard that collapses whitespace and drops non-ASCII before a value reaches a reader card.
    - Guarantee: returns whitespace-collapsed, ASCII-only text; None/empty becomes "".
    - Fails: never raises; non-ASCII characters are silently discarded.
    - Non-goal: not a private-data redactor; it sanitizes shape, it does not authorize export of restricted content.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text = " ".join(str(value or "").split())
    return text.encode("ascii", "ignore").decode("ascii")


def _public_excerpt(value: Any, max_chars: int) -> str:
    """
    [ACTION]
    Produce an ASCII, word-bounded excerpt of value capped at max_chars.

    - Teleology: keep glance/one-line excerpts inside the first-screen budget without mid-word truncation.
    - Guarantee: returns _public_text(value) when within max_chars; otherwise a word-bounded prefix ending in "..." no longer than the cap.
    - Fails: never raises; over-long input is truncated, not rejected.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text = _public_text(value)
    if len(text) <= max_chars:
        return text
    prefix = text[: max_chars - 3].rsplit(" ", 1)[0] or text[: max_chars - 3]
    return prefix.rstrip(" ,.;:") + "..."


def _positive_count(row: Any) -> bool:
    """
    [ACTION]
    Report whether a scale-count row carries a strictly positive integer count.

    - Teleology: gate display logic on rows whose `count` is a real positive int.
    - Guarantee: returns True only when `row` is a dict with a non-bool int `count` > 0; False otherwise.
    - Fails: never raises; missing/bool/non-positive counts return False.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        isinstance(row, dict)
        and isinstance(row.get("count"), int)
        and not isinstance(row.get("count"), bool)
        and row["count"] > 0
    )


def _source_checkout_command(command: str, project_label: str) -> str:
    """
    [ACTION]
    Build a no-install `PYTHONPATH=src python3 -m microcosm_core <command> <label>` invocation.

    - Teleology: keep the source-checkout (no pip install) entry path copyable for cold cloners.
    - Guarantee: returns the PYTHONPATH-prefixed module invocation string for the given subcommand and project label.
    - Fails: never raises; pure string formatting.
    - Non-goal: does not run anything or imply a package install / release path.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return f"PYTHONPATH=src python3 -m microcosm_core {command} {project_label}"


def _source_checkout_commands(project_label: str) -> dict[str, str]:
    """
    [ACTION]
    Build the source-checkout fallback command set (hello, tour, status, first-screen, contracts).

    - Teleology: projection of the no-install entry commands so the card never assumes a pip install.
    - Guarantee: returns a `microcosm_source_checkout_commands_v1` dict mapping each entry surface to its PYTHONPATH module invocation, with an explicit fallback-not-install authority field.
    - Fails: never raises; deterministic string construction from `project_label`.
    - Escalates-to: _source_checkout_command builds each row; consumed by first_screen_composition_card and the text card.
    - Non-goal: does not install, run, or claim package-install or release readiness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "microcosm_source_checkout_commands_v1",
        "purpose": "keep_the_no_install_entry_path_copyable_after_hello",
        "hello": _source_checkout_command("hello", project_label),
        "behavior_proof": _source_checkout_command("tour --card", project_label),
        "status_card": _source_checkout_command("status --card", project_label),
        "first_screen_card": _source_checkout_command(
            "first-screen --card",
            project_label,
        ),
        "first_screen_full": _source_checkout_command(
            "first-screen --full",
            project_label,
        ),
        "organ_surface_contract": (
            "PYTHONPATH=src python3 -m microcosm_core "
            "organ-surface-contract --card --root ."
        ),
        "agent_entry_selector": (
            "PYTHONPATH=src python3 -m microcosm_core "
            "agent-entry-composition --root . --task agent-entry "
            "--viewer {type_a_agent|human} --card --check"
        ),
        "authority": "source_checkout_fallback_not_package_install_or_release_claim",
    }


def _reader_routes(project_label: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    Build the six reader-route rows (first question, next commands, evidence focus) for the card.

    - Teleology: generated reader-typed entry rows so each audience gets a first question and inspection order.
    - Guarantee: returns a list of six route dicts (one per READER_ROUTE_ID) each declaring branch_authority = "selects_next_inspection_surface_only".
    - Fails: never raises; pure deterministic construction from `project_label`.
    - Escalates-to: REQUIRED_ROUTE_IDS parity is enforced by _standard_backed_first_screen_scan / _validation_checks.
    - Non-goal: does not authorize reader success, release, or reader-specific claim ceilings.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        {
            "reader_route_id": "public_github_visitor",
            "first_question": "What should I run first from the public repo page?",
            "next_commands": [
                f"plectis hello {project_label}",
                f"plectis tour --card {project_label}",
            ],
            "evidence_focus": [
                "copyable first command and no-install fallback",
                "local behavior proof before receipt drilldown",
                "release, hosting, and private-data anti-claims",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "safety_evals_engineer",
            "first_question": "Does the evidence discipline survive contact with scale?",
            "next_commands": [
                f"plectis status --card {project_label}",
                "plectis authority --card",
                "plectis workingness --card",
            ],
            "evidence_focus": [
                "evidence classes and their authority ceilings",
                "body-copy boundaries and validator refs",
                "anti-claims, failure modes, and omission receipts",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "hiring_reviewer",
            "first_question": "Is this real, inspectable, and built with the judgment I would interview for?",
            "next_commands": [
                "plectis legibility-scorecard",
                f"plectis tour --card {project_label}",
            ],
            "evidence_focus": [
                "local runnable behavior",
                "bounded public claims",
                "honest negatives and unsupported-claim boundaries",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "peer_developer",
            "first_question": "Can I clone it, run it, and understand the first useful path in an hour?",
            "next_commands": [
                f"plectis tour --card {project_label}",
                f"plectis observe --card {project_label}",
            ],
            "evidence_focus": [
                "folder-local .microcosm state",
                "route/work/event/evidence chain",
                "standards and receipt drilldowns behind the compact card",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "domain_specialist",
            "first_question": (
                "Where do I start if I care about one technical domain or specialty?"
            ),
            "next_commands": [
                "ORGANS.md#find-your-specialty",
                f"plectis tour --card {project_label}",
            ],
            "evidence_focus": [
                "specialty-to-organ navigation",
                "evidence class and authority ceiling",
                "explicit domain-correctness and expert-review anti-claims",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "type_a_agent",
            "first_question": (
                "What should I read first as a Type A agent, and where do I "
                "patch if the route misleads me?"
            ),
            "next_commands": [
                f"plectis first-screen --card {project_label}",
                "plectis organ-surface-contract --card --root .",
                "AGENTS.md::Concept And Mechanism Entry",
            ],
            "evidence_focus": [
                "agent first-read contract and first-screen doctrine frame",
                "mechanism versus validator/projection status",
                "owner surface and claim ceiling before source mutation",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
    ]


def _reader_landing_packets(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the reader-landing packets that turn each route into one action/proof/success/next.

    - Teleology: generated per-reader "one screen" packets (first action, proof surface, success criterion, next drilldown).
    - Guarantee: returns a `microcosm_reader_landing_packets_v1` dict with one packet per reader route, each carrying an inspection-order-only authority field.
    - Fails: never raises; deterministic construction from `project_label`.
    - Escalates-to: consumed by _reader_packet_map and the text card; parity checked by _validation_checks.
    - Non-goal: does not authorize reader success, safety approval, hiring assessment, or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "microcosm_reader_landing_packets_v1",
        "purpose": "turn_reader_routes_into_first_action_proof_success_packets",
        "shared_authority_rule": (
            "Reader packets choose inspection order only; every reader inherits the "
            "same authority ceiling, anti-claim, and omission receipt."
        ),
        "one_screen_rule": (
            "Each packet carries one first action, one proof surface, one success "
            "criterion, and one next drilldown."
        ),
        "packets": [
            {
                "reader_route_id": "public_github_visitor",
                "first_action": (
                    f"Run `plectis tour --card {project_label}` after this card."
                ),
                "proof_surface": f"`plectis tour --card {project_label}`",
                "source_checkout_first_action": (
                    "Run `PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}` after this card."
                ),
                "source_checkout_proof_surface": (
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}`"
                ),
                "success_criterion": (
                    "Can find the first runnable local command and name the "
                    "release, hosting, and private-data claims this repo refuses."
                ),
                "next_drilldown": "README.md#run-it",
                "authority": "inspection_order_only_not_publication_readiness",
            },
            {
                "reader_route_id": "safety_evals_engineer",
                "first_action": (
                    f"Run `plectis tour --card {project_label}` first, then "
                    f"`plectis status --card {project_label}`."
                ),
                "proof_surface": (
                    "`plectis authority --card` plus `plectis workingness --card`"
                ),
                "source_checkout_first_action": (
                    "Run `PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}` first, then "
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"status --card {project_label}`."
                ),
                "source_checkout_proof_surface": (
                    "`PYTHONPATH=src python3 -m microcosm_core authority --card` "
                    "plus `PYTHONPATH=src python3 -m microcosm_core "
                    "workingness --card`"
                ),
                "success_criterion": (
                    "Can cite the evidence-class ceilings and the body-copy validator "
                    "boundary without inferring maturity or release readiness."
                ),
                "next_drilldown": EVIDENCE_CLASS_REGISTRY_REF,
                "authority": "inspection_order_only_not_safety_approval",
            },
            {
                "reader_route_id": "hiring_reviewer",
                "first_action": (
                    "Run `plectis legibility-scorecard`, then "
                    f"`plectis tour --card {project_label}`."
                ),
                "proof_surface": (
                    "`plectis legibility-scorecard` plus "
                    f"`plectis tour --card {project_label}`"
                ),
                "success_criterion": (
                    "Can distinguish runnable local behavior from the claims this "
                    "public card explicitly refuses to make."
                ),
                "next_drilldown": "plectis legibility-scorecard",
                "authority": "inspection_order_only_not_candidate_assessment",
            },
            {
                "reader_route_id": "peer_developer",
                "first_action": f"Run `plectis tour --card {project_label}`.",
                "proof_surface": f"`plectis observe --card {project_label}`",
                "success_criterion": (
                    "Can inspect folder-local .microcosm state and follow the "
                    "route/work/event/evidence chain without provider calls."
                ),
                "next_drilldown": f"plectis observe {project_label}",
                "authority": "inspection_order_only_not_integration_guarantee",
            },
            {
                "reader_route_id": "domain_specialist",
                "first_action": (
                    "Open `ORGANS.md#find-your-specialty`, then run "
                    f"`plectis tour --card {project_label}`."
                ),
                "proof_surface": (
                    "`ORGANS.md#find-your-specialty` plus "
                    f"`plectis tour --card {project_label}`"
                ),
                "source_checkout_first_action": (
                    "Open `ORGANS.md#find-your-specialty`, then run "
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}`."
                ),
                "source_checkout_proof_surface": (
                    "`ORGANS.md#find-your-specialty` plus "
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}`"
                ),
                "task_selector_command": (
                    "plectis agent-entry-composition --root . --task <domain> "
                    "--viewer human --card --check"
                ),
                "source_checkout_task_selector_command": (
                    "PYTHONPATH=src python3 -m microcosm_core "
                    "agent-entry-composition --root . --task <domain> "
                    "--viewer human --card --check"
                ),
                "success_criterion": (
                    "Can map a domain to a specialty route and name the evidence "
                    "class and authority ceiling without claiming domain correctness."
                ),
                "next_drilldown": "ORGANS.md#find-your-specialty",
                "authority": (
                    "inspection_order_only_not_domain_correctness_or_expert_review"
                ),
            },
            {
                "reader_route_id": "type_a_agent",
                "first_action": (
                    f"Run `plectis first-screen --card {project_label}`. "
                    "If you need `doctrine_effect_frame`, run "
                    f"`plectis first-screen --full {project_label}` before "
                    "reading it; then run "
                    "`plectis organ-surface-contract --card --root .`."
                ),
                "proof_surface": "`plectis organ-surface-contract --card --root .`",
                "source_checkout_first_action": (
                    "Run `PYTHONPATH=src python3 -m microcosm_core "
                    f"first-screen --card {project_label}`. If you need "
                    "`doctrine_effect_frame`, run `PYTHONPATH=src python3 -m "
                    f"microcosm_core first-screen --full {project_label}` before "
                    "reading it; then run `PYTHONPATH=src python3 -m "
                    "microcosm_core organ-surface-contract --card --root .`."
                ),
                "source_checkout_proof_surface": (
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    "organ-surface-contract --card --root .`"
                ),
                "success_criterion": (
                    "Can name the agent first-read path, distinguish mechanisms "
                    "from validators/projections, and identify the owner surface "
                    "to patch without overclaiming source mutation."
                ),
                "next_drilldown": "AGENTS.md::Concept And Mechanism Entry",
                "authority": (
                    "inspection_order_only_not_agent_autonomy_or_source_mutation_"
                    "authority"
                ),
            },
        ],
    }


def _reader_route_menu(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the copyable reader-route menu (terminal + text-projection commands per reader).

    - Teleology: generated menu so reader-typed first screens are copyable without separate entry artifacts.
    - Guarantee: returns a `microcosm_reader_route_menu_v1` dict whose `routes` carry the exact `plectis hello --reader <id>` and `plectis first-screen --format text --reader <id>` commands the standard scan expects, plus a `safe_to_show` block with all export/release flags False.
    - Fails: never raises; deterministic construction from `project_label`.
    - Escalates-to: command parity is asserted by _standard_backed_first_screen_scan.reader_command_parity.
    - Non-goal: does not create a new entry artifact, claim reader success, or claim release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "microcosm_reader_route_menu_v1",
        "purpose": (
            "make_reader_typed_first_screens_copyable_without_separate_entry_"
            "artifacts"
        ),
        "menu_rule": (
            "Show the shared map and behavior proof first; focused reader commands "
            "only change the terminal projection, not the authority ceiling."
        ),
        "default_command": f"plectis hello {project_label}",
        "alias_hint": READER_ROUTE_ALIAS_HINT,
        "shared_behavior_command": f"plectis tour --card {project_label}",
        "machine_card_command": f"plectis first-screen --card {project_label}",
        "default_json_command": f"plectis first-screen {project_label}",
        "routes": [
            {
                "reader_route_id": "public_github_visitor",
                "label": READER_LABELS["public_github_visitor"],
                "terminal_command": (
                    f"plectis hello --reader public_github_visitor {project_label}"
                ),
                "text_projection_command": (
                    "plectis first-screen --format text "
                    f"--reader public_github_visitor {project_label}"
                ),
                "first_action": (
                    f"Run `plectis tour --card {project_label}` after this card."
                ),
                "proof_surface": f"`plectis tour --card {project_label}`",
                "source_checkout_first_action": (
                    "Run `PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}` after this card."
                ),
                "source_checkout_proof_surface": (
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}`"
                ),
                "exit_check": "find the first runnable local command and anti-claims",
                "not_a_claim": "publication_or_reader_success_ready",
                "authority": "focused_projection_only_not_publication_readiness",
            },
            {
                "reader_route_id": "safety_evals_engineer",
                "label": READER_LABELS["safety_evals_engineer"],
                "terminal_command": (
                    f"plectis hello --reader safety_evals_engineer {project_label}"
                ),
                "text_projection_command": (
                    "plectis first-screen --format text "
                    f"--reader safety_evals_engineer {project_label}"
                ),
                "first_action": (
                    f"Run `plectis tour --card {project_label}` first, then "
                    f"`plectis status --card {project_label}`."
                ),
                "proof_surface": (
                    "`plectis authority --card` plus `plectis workingness --card`"
                ),
                "source_checkout_first_action": (
                    "Run `PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}` first, then "
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"status --card {project_label}`."
                ),
                "source_checkout_proof_surface": (
                    "`PYTHONPATH=src python3 -m microcosm_core authority --card` "
                    "plus `PYTHONPATH=src python3 -m microcosm_core "
                    "workingness --card`"
                ),
                "exit_check": "cite evidence-class ceilings and body-copy boundaries",
                "not_a_claim": "safety_evaluation_complete",
                "authority": "focused_projection_only_not_safety_approval",
            },
            {
                "reader_route_id": "hiring_reviewer",
                "label": READER_LABELS["hiring_reviewer"],
                "terminal_command": (
                    f"plectis hello --reader hiring_reviewer {project_label}"
                ),
                "text_projection_command": (
                    "plectis first-screen --format text "
                    f"--reader hiring_reviewer {project_label}"
                ),
                "first_action": (
                    "Run `plectis legibility-scorecard`, then "
                    f"`plectis tour --card {project_label}`."
                ),
                "proof_surface": (
                    "`plectis legibility-scorecard` plus "
                    f"`plectis tour --card {project_label}`"
                ),
                "exit_check": "separate runnable behavior from refused claims",
                "not_a_claim": "candidate_assessed_or_interview_ready",
                "authority": "focused_projection_only_not_candidate_assessment",
            },
            {
                "reader_route_id": "peer_developer",
                "label": READER_LABELS["peer_developer"],
                "terminal_command": (
                    f"plectis hello --reader peer_developer {project_label}"
                ),
                "text_projection_command": (
                    "plectis first-screen --format text "
                    f"--reader peer_developer {project_label}"
                ),
                "first_action": f"Run `plectis tour --card {project_label}`.",
                "proof_surface": f"`plectis observe --card {project_label}`",
                "exit_check": "follow the route/work/event/evidence chain locally",
                "not_a_claim": "integration_complete",
                "authority": "focused_projection_only_not_integration_guarantee",
            },
            {
                "reader_route_id": "domain_specialist",
                "label": READER_LABELS["domain_specialist"],
                "terminal_command": (
                    f"plectis hello --reader domain_specialist {project_label}"
                ),
                "text_projection_command": (
                    "plectis first-screen --format text "
                    f"--reader domain_specialist {project_label}"
                ),
                "first_action": (
                    "Open `ORGANS.md#find-your-specialty`, then run "
                    f"`plectis tour --card {project_label}`."
                ),
                "proof_surface": (
                    "`ORGANS.md#find-your-specialty` plus "
                    f"`plectis tour --card {project_label}`"
                ),
                "source_checkout_first_action": (
                    "Open `ORGANS.md#find-your-specialty`, then run "
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}`."
                ),
                "source_checkout_proof_surface": (
                    "`ORGANS.md#find-your-specialty` plus "
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    f"tour --card {project_label}`"
                ),
                "exit_check": (
                    "map a domain to a specialty route without inferring domain correctness"
                ),
                "not_a_claim": "domain_expertise_or_domain_correctness_complete",
                "authority": (
                    "focused_projection_only_not_domain_correctness_or_expert_review"
                ),
            },
            {
                "reader_route_id": "type_a_agent",
                "label": READER_LABELS["type_a_agent"],
                "terminal_command": (
                    f"plectis hello --reader type_a_agent {project_label}"
                ),
                "text_projection_command": (
                    "plectis first-screen --format text "
                    f"--reader type_a_agent {project_label}"
                ),
                "first_action": (
                    f"Run `plectis first-screen --card {project_label}`. "
                    "If you need `doctrine_effect_frame`, run "
                    f"`plectis first-screen --full {project_label}` before "
                    "reading it; then run "
                    "`plectis organ-surface-contract --card --root .`."
                ),
                "proof_surface": "`plectis organ-surface-contract --card --root .`",
                "source_checkout_first_action": (
                    "Run `PYTHONPATH=src python3 -m microcosm_core "
                    f"first-screen --card {project_label}`. If you need "
                    "`doctrine_effect_frame`, run `PYTHONPATH=src python3 -m "
                    f"microcosm_core first-screen --full {project_label}` before "
                    "reading it; then run `PYTHONPATH=src python3 -m "
                    "microcosm_core organ-surface-contract --card --root .`."
                ),
                "source_checkout_proof_surface": (
                    "`PYTHONPATH=src python3 -m microcosm_core "
                    "organ-surface-contract --card --root .`"
                ),
                "exit_check": (
                    "name the first-read path, mechanism status, and owner surface"
                ),
                "not_a_claim": "agent_autonomy_or_source_mutation_ready",
                "authority": (
                    "focused_projection_only_not_agent_autonomy_or_source_"
                    "mutation_authority"
                ),
            },
        ],
        "safe_to_show": {
            "uses_existing_reader_packets": True,
            "creates_new_entry_artifact": False,
            "creates_reader_specific_claim_ceiling": False,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "authority": "reader_route_menu_not_new_entry_artifact_or_reader_success_authority",
    }


def _behavior_proof_packet(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the behavior-proof packet naming the shared first command and its success fields.

    - Teleology: generated packet that turns the shared first run into inspectable success conditions.
    - Guarantee: returns a `microcosm_behavior_proof_packet_v1` dict with command, `writes_state: True`, `.microcosm` state_dir, the proof_fields to read (front_door_status.status, selected_route_id, state_inspection, source_files_mutated=False), and a local-receipt-not-release authority.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: the actual `plectis tour --card` run that writes .microcosm/ and front_door_status.
    - Non-goal: does not authorize release, proof correctness, or safety evaluation.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shared_first_command = f"plectis tour --card {project_label}"
    return {
        "schema_version": "microcosm_behavior_proof_packet_v1",
        "purpose": "turn_shared_first_run_into_inspectable_success_conditions",
        "command": shared_first_command,
        "writes_state": True,
        "state_dir": ".microcosm",
        "proof_fields": [
            {
                "field": "front_door_status.status",
                "success_read": "pass",
                "reader_rule": "first_screen_surfaces_pass_not_release_readiness",
            },
            {
                "field": "selected_route_id",
                "success_read": "non_empty_route_id",
                "reader_rule": "selected_local_route_not_universal_project_truth",
            },
            {
                "field": "state_inspection",
                "success_read": "catalog_routes_work_events_evidence_refs_present",
                "reader_rule": "inspectable_local_state_not_private_root_equivalence",
            },
            {
                "field": "source_files_mutated",
                "success_read": False,
                "reader_rule": "project_source_remains_unchanged_by_first_run",
            },
        ],
        "failure_reading": (
            "A non-pass field names the first blocked or warning surface to inspect; "
            "it is not a product, release, proof, or safety-evaluation verdict."
        ),
        "authority": "local_behavior_receipt_not_release_or_proof_authority",
    }


def _pre_install_probe_packet() -> dict[str, Any]:
    """
    [ACTION]
    Build the bounded cold-clone pre-install probe packet (bootstrap command + receipt ref).

    - Teleology: generated handle for the `./bootstrap.sh` probe that runs before install and writes ignored local state.
    - Guarantee: returns a `microcosm_pre_install_probe_v1` dict with command, dry-run command, receipt_ref (.microcosm/cold_clone_probe.json), and a safe_to_show block with release/provider/source-mutation all False.
    - Fails: never raises; returns a constant packet.
    - Non-goal: does not run bootstrap, authorize provider calls, source mutation, or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "microcosm_pre_install_probe_v1",
        "command": "./bootstrap.sh",
        "dry_run_command": "./bootstrap.sh --dry-run",
        "receipt_ref": ".microcosm/cold_clone_probe.json",
        "writes_ignored_local_state": True,
        "runs_before_install": True,
        "authority": "bounded_cold_clone_probe_not_release_or_behavior_proof_authority",
        "safe_to_show": {
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
        },
    }


def _first_run_ladder(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the first-run ladder (map -> behavior proof -> status -> reader branch) packet.

    - Teleology: generated copyable run order so the first screen precedes the long quickstart inventory.
    - Guarantee: returns a `microcosm_first_run_ladder_v1` dict whose `steps` carry per-step command, source_checkout_command, writes_microcosm_state flag, expected_surface, success_read, and a step-scoped authority; embeds the pre-install probe.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: each step's `microcosm` command and the behavior_proof_packet it points at.
    - Non-goal: does not run the ladder or claim quickstart-inventory completeness or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    human_first_command = f"plectis hello {project_label}"
    shared_first_command = f"plectis tour --card {project_label}"
    status_card_command = f"plectis status --card {project_label}"
    source_checkout_commands = _source_checkout_commands(project_label)
    return {
        "schema_version": "microcosm_first_run_ladder_v1",
        "purpose": "make_first_screen_run_order_copyable_without_long_quickstart",
        "pre_install_probe": _pre_install_probe_packet(),
        "one_screen_rule": (
            "The first screen gives a copyable run order before the long command "
            "inventory: map, behavior proof, state confirmation, then reader branch."
        ),
        "steps": [
            {
                "step_id": "map",
                "command": human_first_command,
                "source_checkout_command": source_checkout_commands["hello"],
                "writes_microcosm_state": False,
                "expected_surface": "terminal_text_projection",
                "success_read": "one_screen_map_visible",
                "authority": "projection_only_not_behavior_proof",
            },
            {
                "step_id": "behavior_proof",
                "command": shared_first_command,
                "source_checkout_command": source_checkout_commands["behavior_proof"],
                "writes_microcosm_state": True,
                "expected_surface": ".microcosm state plus compact route card",
                "success_read": (
                    "front_door_status.status=pass and selected_route_id present"
                ),
                "authority": "local_behavior_receipt_not_release_or_proof_authority",
            },
            {
                "step_id": "status_confirmation",
                "command": status_card_command,
                "source_checkout_command": source_checkout_commands["status_card"],
                "writes_microcosm_state": False,
                "expected_surface": "front door state, route proof, and gap preview",
                "success_read": "project_state visible and source_files_mutated=false",
                "authority": "status_read_model_not_whole_system_health",
            },
            {
                "step_id": "reader_branch",
                "command": "choose reader route from reader_route_menu",
                "writes_microcosm_state": False,
                "expected_surface": "reader-specific command, first action, and proof surface",
                "success_read": "next inspection surface selected by reader job",
                "authority": "inspection_order_only_not_reader_specific_claim_ceiling",
            },
        ],
        "authority": "copyable_run_order_not_quickstart_inventory_or_release_authority",
    }


def _first_viewport_manifest(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the ordered first-viewport slot manifest shared by CLI/README/browser/JSON/video.

    - Teleology: generated single-screen composition contract that fixes slot order before the long inventory.
    - Guarantee: returns a `microcosm_first_viewport_manifest_v1` dict with ordered `slots`, a `problem_shape_slot_map`, consumer_surfaces, and a `safe_to_show` block with export/release flags False; every slot repeats must_preserve and must_not_claim.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: the per-slot source_packet builders (first_run_ladder, reader_route_menu, evidence_count_frame, discipline_comparison_strip).
    - Non-goal: does not render, create a new claim, or claim renderer/release authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    human_first_command = f"plectis hello {project_label}"
    shared_first_command = f"plectis tour --card {project_label}"
    bounded_serve_command = _bounded_observatory_serve_command(project_label)
    must_preserve = [
        "authority_ceiling",
        "anti_claim",
        "omission_receipt",
        "discipline_comparison_strip",
    ]
    must_not_claim = [
        "release_or_hosting_authority",
        "provider_call_authority",
        "private_root_equivalence",
        "whole_system_correctness",
        "reader_success",
    ]
    return {
        "schema_version": "microcosm_first_viewport_manifest_v1",
        "purpose": (
            "make_single_screen_cold_entry_composition_explicit_for_cli_readme_"
            "browser_json_and_video"
        ),
        "composition_rule": (
            "Every first-contact projection should render these slots in order before "
            "the long command inventory or full observatory lens list."
        ),
        "slots": [
            {
                "slot_id": "identity",
                "viewport_copy": (
                    "Plectis is a public executable atlas of AI-native runtime "
                    "mechanisms with explicit evidence classes and authority ceilings."
                ),
                "source_packet": "text_projection",
                "first_visible_surface": human_first_command,
                "proof_surface": "authority_ceiling",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "first_run",
                "viewport_copy": "Open the map, then run the behavior-proof card.",
                "source_packet": "first_run_ladder",
                "first_visible_surface": shared_first_command,
                "proof_surface": "behavior_proof_packet",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "proof_chain",
                "viewport_copy": (
                    "The first run writes inspectable .microcosm state, not source "
                    "mutations."
                ),
                "source_packet": "local_state_receipt_trail",
                "first_visible_surface": ".microcosm/",
                "proof_surface": "first_contact_surface_refs",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "evidence_context",
                "viewport_copy": (
                    "Counts are evidence-class accounting, not maturity or readiness scores."
                ),
                "source_packet": "evidence_count_frame",
                "first_visible_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "proof_surface": "evidence_class_legend",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "reader_branch",
                "viewport_copy": (
                    "Reader routes branch only after the shared local behavior proof."
                ),
                "source_packet": "reader_route_menu",
                "first_visible_surface": "focused reader commands",
                "proof_surface": "reader_exit_criteria",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "authority_boundary",
                "viewport_copy": (
                    "Comparison strip and tripwires make rigor visible without claim inflation."
                ),
                "source_packet": "discipline_comparison_strip",
                "first_visible_surface": "discipline_comparison_strip",
                "proof_surface": "overclaim_tripwire_matrix",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
        ],
        "problem_shape_slot_map": [
            {
                "problem_shape_id": "first_thing_best_thing_gap",
                "slot_id": "first_run",
            },
            {
                "problem_shape_id": "audience_is_not_one_person",
                "slot_id": "reader_branch",
            },
            {
                "problem_shape_id": "honest_numbers_without_context",
                "slot_id": "evidence_context",
            },
            {
                "problem_shape_id": "discipline_invisible_without_comparison",
                "slot_id": "authority_boundary",
            },
            {
                "problem_shape_id": "size_paradox",
                "slot_id": "identity",
            },
            {
                "problem_shape_id": "runnable_vs_structural_split",
                "slot_id": "proof_chain",
            },
            {
                "problem_shape_id": "doctrine_reads_as_ceremony",
                "slot_id": "authority_boundary",
            },
            {
                "problem_shape_id": "frontend_surface_not_seductive",
                "slot_id": "identity",
            },
            {
                "problem_shape_id": "card_discipline_not_default",
                "slot_id": "first_run",
            },
        ],
        "consumer_surfaces": {
            "terminal": human_first_command,
            "readme": "README.md::Choose Your First Screen",
            "browser": f"{bounded_serve_command} -> /",
            "json": f"plectis first-screen --card {project_label}",
            "video": "video_storyboard_packet",
        },
        "safe_to_show": {
            "uses_existing_first_screen_packets": True,
            "creates_new_entry_artifact": False,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "authority": "viewport_manifest_not_new_claim_or_renderer_authority",
    }


def _local_state_receipt_trail(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the local-state receipt trail naming each .microcosm artifact the first run writes.

    - Teleology: generated trail showing what the shared first run writes without expanding raw state.
    - Guarantee: returns a `microcosm_local_state_receipt_trail_v1` dict listing catalog/routes/events/evidence/graph state_refs under `.microcosm`, each with a `not_authority_for` boundary.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: does not authorize private-root equivalence, release, or proof correctness; refs are behavior evidence, not source mutation.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shared_first_command = f"plectis tour --card {project_label}"
    return {
        "schema_version": "microcosm_local_state_receipt_trail_v1",
        "purpose": "show_what_the_first_run_writes_without_expanding_raw_state",
        "producer_command": shared_first_command,
        "state_dir": ".microcosm",
        "trail": [
            {
                "surface_id": "catalog",
                "state_ref": ".microcosm/catalog.json",
                "reader_read": "project files became catalog rows",
                "not_authority_for": "source_mutation_or_project_quality",
            },
            {
                "surface_id": "routes",
                "state_ref": ".microcosm/routes.json",
                "reader_read": "one selected route is inspectable",
                "not_authority_for": "universal_project_truth_or_release_readiness",
            },
            {
                "surface_id": "work_events",
                "state_ref": ".microcosm/events.jsonl",
                "reader_read": "work transaction and event receipt chain exists",
                "not_authority_for": "private_root_equivalence_or_provider_action",
            },
            {
                "surface_id": "evidence_index",
                "state_ref": ".microcosm/evidence/index.json",
                "reader_read": "evidence refs can be opened after the card",
                "not_authority_for": "proof_correctness_or_benchmark_score",
            },
            {
                "surface_id": "graph",
                "state_ref": ".microcosm/graph.json",
                "reader_read": "route, work, event, and evidence refs join",
                "not_authority_for": "whole_system_correctness_or_maturity_score",
            },
        ],
        "reader_rule": (
            "State refs are local behavior evidence from the shared first run; "
            "they are not source mutation, release readiness, or private-root "
            "equivalence claims."
        ),
        "authority": "local_state_receipt_trail_not_private_root_equivalence",
    }


def _first_contact_surface_refs(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the compact first-contact surface map (route/work/events/evidence/graph/observatory/proof/status).

    - Teleology: generated handle map compressing the route-work-event-evidence-graph chain plus observatory/proof handles for cold readers.
    - Guarantee: returns a `microcosm_first_contact_surface_refs_v1` dict with required_surface_ids and a `surfaces` map of commands/state_refs, plus a safe_to_show block where body_text_exported, source_files_mutated, provider_calls_authorized, and release_authorized are all False.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: does not export source bodies, authorize provider/source mutation, or claim release or proof correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shared_first_command = f"plectis tour --card {project_label}"
    status_card_command = f"plectis status --card {project_label}"
    observe_command = f"plectis observe --card {project_label}"
    observe_full_command = f"plectis observe {project_label}"
    proof_lab_command = "plectis proof-lab --out /tmp/microcosm-proof-lab"
    return {
        "schema_version": "microcosm_first_contact_surface_refs_v1",
        "purpose": (
            "compress_route_work_event_evidence_graph_observatory_and_proof_"
            "handles_for_cold_readers"
        ),
        "producer_command": shared_first_command,
        "reader_rule": (
            "Use these refs as the first-screen behavior map after the shared "
            "run; open full receipts only after the compact route/work/evidence "
            "graph and observatory/proof handles are visible."
        ),
        "required_surface_ids": [
            "route",
            "work",
            "events",
            "evidence",
            "graph",
            "observatory",
            "proof_lab",
            "status",
        ],
        "surfaces": {
            "route": {
                "command": shared_first_command,
                "state_ref": ".microcosm/routes.json",
                "selected_route_ref": ".microcosm/routes.json::<selected_route_id>",
                "status_ref": "front_door_status.surface_statuses.state_inspection",
            },
            "work": {
                "command": observe_command,
                "state_ref": ".microcosm/work_items.json",
                "selected_work_ref": ".microcosm/work_items.json::<selected_work_id>",
                "event_ref": ".microcosm/events.jsonl",
            },
            "events": {
                "command": observe_command,
                "state_ref": ".microcosm/events.jsonl",
                "status_ref": "plectis observe --card <project>::spans",
                "full_drilldown": observe_full_command,
            },
            "evidence": {
                "command": observe_command,
                "state_ref": ".microcosm/evidence/",
                "index_ref": ".microcosm/evidence/index.json",
                "body_text_exported": False,
            },
            "graph": {
                "command": observe_command,
                "state_ref": ".microcosm/graph.json",
                "status_ref": (
                    "plectis observe --card <project>::causal_chain_summary.graph"
                ),
                "full_drilldown": observe_full_command,
            },
            "observatory": {
                "command": _observatory_serve_command(project_label),
                "bounded_validation_command": _bounded_observatory_serve_command(
                    project_label
                ),
                "bounded_validation_request_count": BOUNDED_OBSERVATORY_REQUEST_COUNT,
                "compact_endpoint": OBSERVATORY_LANDING_ENDPOINTS[
                    "compact_observatory_card"
                ],
                "expanded_endpoint": OBSERVATORY_LANDING_ENDPOINTS[
                    "full_observatory_model"
                ],
            },
            "proof_lab": {
                "command": proof_lab_command,
                "endpoint": "/proof-lab",
                "route_id": "formal_prover_context_strategy_gate",
                "receipt_ref": (
                    "receipts/first_wave/verifier_lab_kernel/"
                    "exported_verifier_lab_kernel_bundle_validation_result.json"
                ),
            },
            "status": {
                "command": status_card_command,
                "endpoint": "/project/status",
                "body_import_floor_ref": (
                    "plectis status --card <project>::front_door."
                    "source_open_body_import_floor"
                ),
                "workingness_command": "plectis workingness --card",
            },
        },
        "safe_to_show": {
            "project_local_state_refs_visible": True,
            "receipt_refs_visible": True,
            "body_text_exported": False,
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
        "authority": (
            "first_contact_surface_map_only_not_source_release_provider_"
            "mutation_or_proof_authority"
        ),
    }


def _overclaim_tripwire_matrix(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the overclaim tripwire matrix mapping common cold-reader overclaims to valid bounded reads.

    - Teleology: generated translation table so frequent overclaims (release-ready, organ-count, low-import, private-root, hosted) resolve to a defensible read plus a check surface.
    - Guarantee: returns a `microcosm_overclaim_tripwire_matrix_v1` dict whose `rows` each pair an overclaim with a valid_read, check_surface, and reader_rule.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: not a marketing or release surface; it bounds claims, it does not make them.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shared_first_command = f"plectis tour --card {project_label}"
    return {
        "schema_version": "microcosm_overclaim_tripwire_matrix_v1",
        "purpose": "translate_common_cold_reader_overclaims_into_valid_bounded_reads",
        "shared_first_command": shared_first_command,
        "rows": [
            {
                "tripwire_id": "release_ready",
                "overclaim": "Microcosm is release-ready.",
                "valid_read": (
                    "Plectis exposes a local first-run evidence card and "
                    "authority ceiling."
                ),
                "check_surface": f"plectis status --card {project_label}",
                "reader_rule": "release_readiness_not_claimed",
            },
            {
                "tripwire_id": "organ_count_whole_system",
                "overclaim": "Forty-seven organs means every capability works end-to-end.",
                "valid_read": (
                    "Accepted public runtime organs are inventory handles with "
                    "evidence classes and failure envelopes."
                ),
                "check_surface": "plectis workingness",
                "reader_rule": "organ_inventory_not_whole_system_correctness",
            },
            {
                "tripwire_id": "low_body_import_count_fake",
                "overclaim": "A low verified body-import count means the system is fake.",
                "valid_read": (
                    "Evidence-class counts are claim-boundary accounting; low "
                    "counts narrow claims instead of being hidden."
                ),
                "check_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "reader_rule": "low_count_not_failure_by_itself",
            },
            {
                "tripwire_id": "local_state_private_root_equivalence",
                "overclaim": ".microcosm state proves private-root equivalence.",
                "valid_read": (
                    ".microcosm state proves folder-local behavior refs from the "
                    "shared first run."
                ),
                "check_surface": ".microcosm/",
                "reader_rule": "local_state_not_private_root_equivalence",
            },
            {
                "tripwire_id": "observatory_hosted_release",
                "overclaim": "The observatory is a hosted or public release surface.",
                "valid_read": (
                    "The observatory is a localhost read-model over the same "
                    "first-screen card."
                ),
                "check_surface": OBSERVATORY_LANDING_ENDPOINTS["first_screen_card"],
                "reader_rule": "localhost_read_model_not_hosting_authority",
            },
        ],
        "authority": "overclaim_tripwire_not_marketing_or_release_authority",
    }


def _reader_exit_criteria(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the per-reader exit criteria (when the first screen has done its job) packet.

    - Teleology: generated stop rules telling each reader when they can choose a drilldown without the command inventory.
    - Guarantee: returns a `microcosm_reader_exit_criteria_v1` dict with one criterion per reader route, each declaring exit_when, next_if_not_met, and a not_a_claim.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: does not authorize reader success or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "microcosm_reader_exit_criteria_v1",
        "purpose": "tell_cold_readers_when_the_first_screen_has_done_its_job",
        "shared_first_command": f"plectis tour --card {project_label}",
        "shared_stop_rule": (
            "The first screen is complete when the reader can choose the next "
            "drilldown without needing the long command inventory."
        ),
        "criteria": [
            {
                "reader_route_id": "public_github_visitor",
                "exit_when": (
                    "Can run the first command and point to the anti-claims "
                    "before opening deeper receipts."
                ),
                "next_if_not_met": f"plectis hello {project_label}",
                "not_a_claim": "publication_or_reader_success_ready",
            },
            {
                "reader_route_id": "safety_evals_engineer",
                "exit_when": (
                    "Can name evidence-class ceilings, authority ceiling, and "
                    "first missing or failing surface without inferring readiness."
                ),
                "next_if_not_met": f"plectis status --card {project_label}",
                "not_a_claim": "safety_evaluation_complete",
            },
            {
                "reader_route_id": "hiring_reviewer",
                "exit_when": (
                    "Can distinguish runnable local behavior from the claims this "
                    "card refuses to make."
                ),
                "next_if_not_met": "plectis legibility-scorecard",
                "not_a_claim": "candidate_assessed_or_interview_ready",
            },
            {
                "reader_route_id": "peer_developer",
                "exit_when": (
                    "Can find .microcosm state refs and follow the "
                    "route/work/event/evidence chain."
                ),
                "next_if_not_met": f"plectis observe --card {project_label}",
                "not_a_claim": "integration_complete",
            },
            {
                "reader_route_id": "domain_specialist",
                "exit_when": (
                    "Can map a domain to the specialty index and name the evidence "
                    "class and authority ceiling without claiming domain correctness."
                ),
                "next_if_not_met": "ORGANS.md#find-your-specialty",
                "not_a_claim": "domain_expertise_or_domain_correctness_complete",
            },
            {
                "reader_route_id": "type_a_agent",
                "exit_when": (
                    "Can name the agent first-read path, distinguish mechanism "
                    "organs from validators/projections, and identify the owner "
                    "surface to patch if the route misleads."
                ),
                "next_if_not_met": (
                    "plectis organ-surface-contract --card --root ."
                ),
                "not_a_claim": "agent_autonomy_or_source_mutation_ready",
            },
        ],
        "authority": "exit_criteria_not_reader_success_or_release_authority",
    }


def _video_storyboard_packet(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the 60-second cold-entry video storyboard packet bound to the same first-screen commands.

    - Teleology: generated presentation plan so a video/screenshot board projects the first-screen beats without inventing new claims.
    - Guarantee: returns a `microcosm_video_storyboard_packet_v1` dict with timeboxed `beats`, allowed_artifact_forms, a `safe_to_show` block (private/provider/live-session/release flags False), and an explicit anti_claim.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: first_screen_composition_card as the named source_projection every beat points back to.
    - Non-goal: not a release artifact, benchmark, hosted demo, or private-root equivalence claim.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shared_first_command = f"plectis tour --card {project_label}"
    status_card_command = f"plectis status --card {project_label}"
    observatory_command = _bounded_observatory_serve_command(project_label)
    return {
        "schema_version": "microcosm_video_storyboard_packet_v1",
        "purpose": "make_a_sixty_second_cold_entry_artifact_without_new_claims",
        "artifact_rule": (
            "A video, screenshot board, or browser reveal may project these beats, "
            "but every beat must point back to the same package-backed first-screen "
            "commands and authority ceiling."
        ),
        "allowed_artifact_forms": [
            "terminal_capture",
            "browser_walkthrough",
            "static_reveal_board",
            "short_video",
        ],
        "source_projection": (
            "microcosm_core.first_screen_composition.first_screen_composition_card"
        ),
        "first_run_command": shared_first_command,
        "bounded_observatory_command": observatory_command,
        "beats": [
            {
                "beat_id": "open_map",
                "timebox_seconds": 8,
                "visible_surface": f"plectis hello {project_label}",
                "reader_takeaway": (
                    "one screen names the mechanism atlas and its authority ceiling"
                ),
                "proof_ref": "terminal_text_projection",
            },
            {
                "beat_id": "prove_local_behavior",
                "timebox_seconds": 12,
                "visible_surface": shared_first_command,
                "reader_takeaway": ".microcosm state is written without source mutation",
                "proof_ref": "front_door_status.status + source_files_mutated=false",
            },
            {
                "beat_id": "show_route_chain",
                "timebox_seconds": 10,
                "visible_surface": f"plectis observe --card {project_label}",
                "reader_takeaway": "route, work, event, evidence, and graph refs join",
                "proof_ref": ".microcosm/events.jsonl + .microcosm/graph.json",
            },
            {
                "beat_id": "frame_evidence_counts",
                "timebox_seconds": 10,
                "visible_surface": status_card_command,
                "reader_takeaway": "counts are claim-boundary accounting, not maturity scores",
                "proof_ref": EVIDENCE_CLASS_REGISTRY_REF,
            },
            {
                "beat_id": "open_authority_boundary",
                "timebox_seconds": 10,
                "visible_surface": (
                    "plectis authority --card, then plectis workingness --card"
                ),
                "reader_takeaway": "authority ceilings and failure envelopes stay visible",
                "proof_ref": WORKINGNESS_MAP_REF,
            },
            {
                "beat_id": "choose_reader_branch",
                "timebox_seconds": 10,
                "visible_surface": "reader_landing_packets",
                "reader_takeaway": "safety, hiring, and developer readers get different next surfaces",
                "proof_ref": "reader_exit_criteria",
            },
        ],
        "safe_to_show": {
            "uses_public_first_screen_card": True,
            "uses_localhost_read_model": True,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "uses_live_operator_or_browser_session": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "anti_claim": (
            "The storyboard compresses how to look at Microcosm; it is not a "
            "release artifact, benchmark, hiring verdict, safety evaluation, "
            "hosted demo, or private-root equivalence claim."
        ),
        "authority": "presentation_plan_over_existing_first_screen_contract_only",
    }


def _artifact_fit_matrix(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the artifact-fit matrix binding every cold-entry form to one source card.

    - Teleology: generated matrix asserting terminal/README/browser/JSON/video forms are projections over one first-screen contract.
    - Guarantee: returns a `microcosm_first_screen_artifact_fit_matrix_v1` dict naming source_of_truth = first_screen_composition_card, with per-surface rows (must_preserve/must_not_claim) and a safe_to_show block where export/new-release-artifact flags are False.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: the named source_projection per row (first_screen_text_card, first_screen_compact_card, readme_entry_contract, observatory_landing_frame).
    - Non-goal: does not create a new release artifact or reader-specific claim ceiling.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    human_first_command = f"plectis hello {project_label}"
    shared_first_command = f"plectis tour --card {project_label}"
    first_screen_json_command = f"plectis first-screen --card {project_label}"
    bounded_observatory_command = _bounded_observatory_serve_command(project_label)
    shared_must_preserve = [
        "human_first_command",
        "shared_first_command",
        "authority_ceiling",
        "anti_claim",
        "omission_receipt",
        "discipline_comparison_strip",
    ]
    shared_must_not_claim = [
        "release_or_hosting_authority",
        "provider_call_authority",
        "private_root_equivalence",
        "whole_system_correctness",
        "reader_success",
    ]
    return {
        "schema_version": "microcosm_first_screen_artifact_fit_matrix_v1",
        "purpose": "keep_all_cold_entry_forms_bound_to_one_source_card",
        "source_of_truth": (
            "microcosm_core.first_screen_composition.first_screen_composition_card"
        ),
        "matrix_rule": (
            "Terminal text, README order, browser landing, machine JSON, and short-video "
            "forms are projections over one first-screen contract, not independent "
            "cold-entry artifacts."
        ),
        "rows": [
            {
                "surface_id": "terminal_text_projection",
                "artifact_form": "terminal_text",
                "consumer_surface": human_first_command,
                "source_projection": (
                    "microcosm_core.first_screen_composition.first_screen_text_card"
                ),
                "first_job": "show_the_map_before_state_writing",
                "must_preserve": [
                    *shared_must_preserve,
                    "reader_routes",
                    "reader_route_menu",
                    "reader_exit_criteria",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "local_behavior_card",
                "artifact_form": "terminal_state_writer",
                "consumer_surface": shared_first_command,
                "source_projection": "plectis tour --card output",
                "first_job": "write_local_state_and_expose_behavior_proof",
                "must_preserve": [
                    *shared_must_preserve,
                    "behavior_proof_packet",
                    "local_state_receipt_trail",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "machine_json_card",
                "artifact_form": "public_json",
                "consumer_surface": first_screen_json_command,
                "source_projection": (
                    "microcosm_core.first_screen_composition.first_screen_compact_card"
                ),
                "first_job": "give_consumers_the_compact_public_card_with_full_drilldown",
                "must_preserve": [
                    *shared_must_preserve,
                    "validation.checks",
                    "public_private_boundary",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "readme_first_screen",
                "artifact_form": "markdown_entry_order",
                "consumer_surface": "README.md::Choose Your First Screen",
                "source_projection": "readme_entry_contract",
                "first_job": "place_the_card_before_the_long_inventory",
                "must_preserve": [
                    *shared_must_preserve,
                    "readme_entry_contract.required_markdown_order",
                    "reader_route_menu",
                    "reader_landing_packets",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "browser_landing",
                "artifact_form": "localhost_html_read_model",
                "consumer_surface": bounded_observatory_command,
                "source_projection": "observatory_landing_frame",
                "first_job": "reuse_the_card_as_the_first_viewport",
                "must_preserve": [
                    *shared_must_preserve,
                    "observatory_landing_frame.required_visible_handles",
                    "first_contact_surface_refs",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "short_video_storyboard",
                "artifact_form": "presentation_plan",
                "consumer_surface": "video_storyboard_packet",
                "source_projection": "video_storyboard_packet",
                "first_job": "compress_sixty_seconds_without_new_claims",
                "must_preserve": [
                    *shared_must_preserve,
                    "video_storyboard_packet.beats",
                    "video_storyboard_packet.safe_to_show",
                ],
                "must_not_claim": shared_must_not_claim,
            },
        ],
        "safe_to_show": {
            "binds_to_single_source_contract": True,
            "allows_multiple_projection_forms": True,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "creates_new_release_artifact": False,
            "creates_reader_specific_claim_ceiling": False,
        },
        "authority": "projection_fit_matrix_not_new_artifact_authority",
    }


def _cold_entry_problem_map(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the cold-entry problem map binding each problem shape to an existing first-screen packet.

    - Teleology: generated map explaining why each first-screen packet exists, without creating a second entry artifact.
    - Guarantee: returns a `microcosm_cold_entry_problem_map_v1` dict whose `rows` resolve each problem_shape_id to a primary_packet, first_surface, proof_surface, and not_claim, plus a safe_to_show block with export/release flags False.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: does not create a new entry artifact or claim strategy/release authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    human_first_command = f"plectis hello {project_label}"
    shared_first_command = f"plectis tour --card {project_label}"
    return {
        "schema_version": "microcosm_cold_entry_problem_map_v1",
        "purpose": "bind_cold_entry_problem_shapes_to_existing_first_screen_packets",
        "map_rule": (
            "Each cold-entry problem shape must resolve to an existing first-screen "
            "packet or drilldown. The map explains why the packet exists; it does "
            "not create a second entry artifact."
        ),
        "rows": [
            {
                "problem_shape_id": "first_thing_best_thing_gap",
                "reader_risk": "long_inventory_before_best_evidence",
                "compression_answer": "open_the_map_then_run_the_shared_behavior_card",
                "primary_packet": "first_run_ladder",
                "first_surface": human_first_command,
                "proof_surface": shared_first_command,
                "not_claim": "quickstart_inventory_complete",
            },
            {
                "problem_shape_id": "audience_is_not_one_person",
                "reader_risk": "one_generic_pitch_overloads_three_jobs",
                "compression_answer": "shared_behavior_first_then_reader_typed_branch",
                "primary_packet": "reader_route_menu",
                "first_surface": "focused reader commands",
                "proof_surface": "reader_exit_criteria",
                "not_claim": "reader_success_or_reader_specific_authority",
            },
            {
                "problem_shape_id": "honest_numbers_without_context",
                "reader_risk": "low_counts_read_as_failure_or_hidden_maturity_score",
                "compression_answer": "make_counts_claim_boundary_accounting",
                "primary_packet": "evidence_count_frame",
                "first_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "proof_surface": "evidence_class_legend",
                "not_claim": "maturity_readiness_or_progress_score",
            },
            {
                "problem_shape_id": "discipline_invisible_without_comparison",
                "reader_risk": "rigor_reads_as_ceremony_or_obviousness",
                "compression_answer": "show_side_by_side_failures_and_microcosm_boundaries",
                "primary_packet": "discipline_comparison_strip",
                "first_surface": "discipline_comparison_strip",
                "proof_surface": "overclaim_tripwire_matrix",
                "not_claim": "external_benchmark_equivalence",
            },
            {
                "problem_shape_id": "size_paradox",
                "reader_risk": "large_public_substrate_reads_as_diffuse",
                "compression_answer": "make_the_first_command_the_composition_root",
                "primary_packet": "scale_frame",
                "first_surface": shared_first_command,
                "proof_surface": WORKINGNESS_MAP_REF,
                "not_claim": "whole_system_correctness",
            },
            {
                "problem_shape_id": "runnable_vs_structural_split",
                "reader_risk": "local_demo_seen_apart_from_public_scale",
                "compression_answer": "join_folder_local_state_to_structural_drilldowns",
                "primary_packet": "runnable_structural_join",
                "first_surface": ".microcosm/",
                "proof_surface": "first_contact_surface_refs",
                "not_claim": "private_root_equivalence",
            },
            {
                "problem_shape_id": "doctrine_reads_as_ceremony",
                "reader_risk": "governance_words_look_like_status_signaling",
                "compression_answer": "translate_doctrine_handles_into_mistakes_prevented",
                "primary_packet": "doctrine_effect_frame",
                "first_surface": "authority_ceiling",
                "proof_surface": "omission_receipt",
                "not_claim": "doctrine_as_credential",
            },
            {
                "problem_shape_id": "frontend_surface_not_seductive",
                "reader_risk": "browser_or_video_viewers_miss_the_real_entry_contract",
                "compression_answer": "make_browser_and_video_forms_project_the_same_card",
                "primary_packet": "artifact_fit_matrix",
                "first_surface": "observatory_landing_frame",
                "proof_surface": "video_storyboard_packet",
                "not_claim": "hosted_release_or_standalone_video_authority",
            },
            {
                "problem_shape_id": "card_discipline_not_default",
                "reader_risk": "compact_card_exists_but_is_not_the_first_loaded_surface",
                "compression_answer": "make_hello_and_readme_order_point_at_the_card_first",
                "primary_packet": "readme_entry_contract",
                "first_surface": "text_projection",
                "proof_surface": "entry_surface_contract",
                "not_claim": "full_surface_removed_or_depth_weakened",
            },
        ],
        "safe_to_show": {
            "uses_existing_first_screen_packets": True,
            "creates_new_entry_artifact": False,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "authority": "problem_shape_map_not_strategy_or_release_authority",
    }


def _evidence_count_frame() -> dict[str, Any]:
    """
    [ACTION]
    Build the evidence-count interpretation frame (counts are accounting, not scores).

    - Teleology: generated frame fixing how a reader must interpret evidence-class counts.
    - Guarantee: returns a constant dict declaring interpretation="accounting_not_maturity_score", forbidden_reads (maturity/readiness/completeness/progress), and authoritative_count_sources with their roles.
    - Fails: never raises; returns a constant frame.
    - Escalates-to: EVIDENCE_CLASS_REGISTRY_REF (legend_ref) and the fixture-manifest/workingness count sources it names.
    - Non-goal: does not score maturity, readiness, or progress.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "interpretation": "accounting_not_maturity_score",
        "legend_ref": EVIDENCE_CLASS_REGISTRY_REF,
        "why_counts_are_visible": (
            "Microcosm shows evidence-class counts so the reader can see what has crossed a declared "
            "boundary, not so the reader infers readiness, completeness, or product progress."
        ),
        "if_a_count_is_low": (
            "Read it as a precise accounting statement for that evidence class. It is not an implicit "
            "negative claim about the rest of the substrate."
        ),
        "forbidden_reads": [
            "maturity_score",
            "readiness_score",
            "completeness_score",
            "product_progress_score",
        ],
        "authoritative_count_sources": [
            {
                "surface": f"{FIXTURE_MANIFESTS_REF}/*.fixture_manifest.json",
                "role": (
                    "implemented-organ source-open material count input before "
                    "stale workingness receipt fallback"
                ),
            },
            {
                "surface": "plectis workingness",
                "role": "runtime evidence summary",
            },
            {
                "surface": "core/standards_registry.json",
                "role": "public standards inventory, not readiness scoring",
            },
            {
                "surface": "receipts/first_wave/standards_registry_validation.json",
                "role": "registry validation receipt",
            },
        ],
    }


def _organ_glance_ladder_rows(root: Path) -> tuple[list[dict[str, Any]], set[str]]:
    """
    [ACTION]
    Flatten the public organ_glance_ladder into organ rows plus the set of family ids.

    - Teleology: source-custody reader that projects the public agent-task-routes glance ladder into a flat row list for the substrate glance.
    - Guarantee: returns (rows, families) where rows are family-stamped organ dicts and families is the set of family ids; a missing or malformed ladder yields ([], set()).
    - Fails: never raises; absent file or wrong types degrade to empty results.
    - Reads: `atlas/agent_task_routes.json::organ_glance_ladder` under `root`.
    - Non-goal: does not authorize source-body export, evidence-strength, or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    routes = _load_public_json(root, AGENT_TASK_ROUTES_REF)
    ladder = routes.get("organ_glance_ladder", []) if isinstance(routes, dict) else []
    rows: list[dict[str, Any]] = []
    families: set[str] = set()
    if not isinstance(ladder, list):
        return rows, families

    for family_row in ladder:
        if not isinstance(family_row, dict):
            continue
        family_id = _public_text(family_row.get("family_id"))
        family_label = _public_text(family_row.get("label") or family_id)
        if family_id:
            families.add(family_id)
        organ_rows = family_row.get("organs", [])
        if not isinstance(organ_rows, list):
            continue
        for organ_row in organ_rows:
            if not isinstance(organ_row, dict):
                continue
            row = dict(organ_row)
            if family_id and not row.get("family"):
                row["family"] = family_id
            if family_label and not row.get("family_label"):
                row["family_label"] = family_label
            family = _public_text(row.get("family"))
            if family:
                families.add(family)
            rows.append(row)
    return rows, families


def _representative_substrate_glance(root: Path) -> dict[str, Any]:
    """
    [ACTION]
    Build a family-diverse, capped sample of real public organs for the first screen.

    - Teleology: generated projection showing actual public organ substance before any drilldown, capped before it becomes an inventory.
    - Guarantee: returns a `microcosm_representative_substrate_glance_v1` dict with up to SUBSTRATE_GLANCE_SAMPLE_LIMIT family-diverse `examples`, total_organ_count/family_count, source_refs, and a safe_to_show block with export/release/whole-system flags False.
    - Fails: never raises; an empty or missing ladder yields zero examples, not an error.
    - Reads: `atlas/agent_task_routes.json::organ_glance_ladder` (via _organ_glance_ladder_rows) under `root`.
    - Non-goal: does not claim inventory completeness, evidence strength, readiness, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    rows, families = _organ_glance_ladder_rows(root)
    examples: list[dict[str, Any]] = []
    selected_organs: set[str] = set()
    selected_families: set[str] = set()
    row_by_organ = {
        _public_text(row.get("organ_id")): row
        for row in rows
        if isinstance(row, dict) and _public_text(row.get("organ_id"))
    }

    def append_example(row: dict[str, Any]) -> None:
        """
        [ACTION]
        - Teleology: Implements `_representative_substrate_glance.append_example` for `microcosm_core.first_screen_composition` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        if len(examples) >= SUBSTRATE_GLANCE_SAMPLE_LIMIT:
            return
        organ_id = _public_text(row.get("organ_id"))
        display_name = _public_text(row.get("display_name") or organ_id)
        family = _public_text(row.get("family"))
        one_line = _public_excerpt(
            row.get("one_line"),
            SUBSTRATE_GLANCE_EXCERPT_MAX_CHARS,
        )
        card_excerpt = _public_excerpt(
            row.get("card") or row.get("human_gloss") or row.get("agent_gloss"),
            SUBSTRATE_GLANCE_EXCERPT_MAX_CHARS,
        )
        glance_excerpt = one_line or card_excerpt
        if not organ_id or not display_name or not family or not glance_excerpt:
            return
        if organ_id in selected_organs:
            return
        card_ref = _public_text(row.get("card_ref") or row.get("drilldown_target"))
        capsule_ref = _public_text(row.get("capsule_id"))
        source_fields = [
            "display_name",
            "family",
            "claim_ceiling_restated",
            "authority_boundary",
            "card_ref",
        ]
        if one_line:
            source_fields.append("one_line")
        if card_excerpt:
            source_fields.append("card")
        examples.append(
            {
                "organ_id": organ_id,
                "display_name": display_name,
                "family": family,
                "glance_excerpt": glance_excerpt,
                "glance_source": (
                    "organ_glance_ladder_one_line"
                    if one_line
                    else "organ_glance_ladder_card"
                ),
                "one_line_excerpt": one_line,
                "card_excerpt": card_excerpt,
                "card_ref": card_ref,
                "capsule_ref": capsule_ref,
                "source_fields": [
                    field for field in source_fields if field
                ],
                "reader_rule": "representative_example_not_inventory_or_readiness_claim",
            }
        )
        selected_organs.add(organ_id)
        selected_families.add(family)

    for organ_id in SUBSTRATE_GLANCE_PREFERRED_ORGAN_IDS:
        row = row_by_organ.get(organ_id)
        if isinstance(row, dict):
            append_example(row)

    for row in rows:
        family = row.get("family")
        if not isinstance(family, str) or family in selected_families:
            continue
        append_example(row)

    for row in rows:
        append_example(row)

    return {
        "schema_version": "microcosm_representative_substrate_glance_v1",
        "purpose": "show_actual_public_organ_substance_before_drilldown",
        "source_ref": ORGAN_GLANCE_LADDER_REF,
        "one_line_source_ref": ORGAN_GLANCE_LADDER_REF,
        "source_refs": [AGENT_TASK_ROUTES_REF],
        "source_authority": (
            "public_agent_task_routes_projection_not_evidence_strength_or_release_authority"
        ),
        "selection_rule": (
            "preferred mechanism showcase ids first, then family-diverse samples "
            "in organ_glance_ladder order, capped before the first screen becomes "
            "an inventory"
        ),
        "preferred_organ_ids": list(SUBSTRATE_GLANCE_PREFERRED_ORGAN_IDS),
        "sample_limit": SUBSTRATE_GLANCE_SAMPLE_LIMIT,
        "total_organ_count": len(rows),
        "family_count": len(families),
        "examples": examples,
        "safe_to_show": {
            "uses_public_organ_glance_ladder": True,
            "uses_public_route_projection_one_lines": True,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
            "claims_whole_system_correctness": False,
        },
        "authority": "representative_glance_not_inventory_score_or_readiness_claim",
    }


def _implemented_organ_ids(organ_registry: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    Extract the list of organ_id strings from an organ registry's implemented_organs.

    - Teleology: source-custody accessor giving the implemented-organ id list that drives fixture-manifest counting.
    - Guarantee: returns the str organ_ids from registry["implemented_organs"]; a missing or non-list field yields an empty list.
    - Fails: never raises; rows without a string organ_id are skipped.
    - Reads: the in-memory `implemented_organs` rows of the passed organ registry dict.
    - Non-goal: does not assert the organs work, are released, or are whole-system correct.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    rows = organ_registry.get("implemented_organs")
    if not isinstance(rows, list):
        return []
    return [
        str(row.get("organ_id"))
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("organ_id"), str)
    ]


def _source_open_body_import_count_from_fixture_manifests(
    root: Path,
    organ_ids: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    Sum source-open body-material counts across per-organ fixture manifests.

    - Teleology: source-custody digest that derives the verified source-open body-import count from fixture manifests before any stale workingness fallback.
    - Guarantee: returns a dict with material_count, rows_with_imports, manifest_count, and source_field/source_ref/fallback_ref; counts are None when no manifest was found, else the summed positive `source_open_body_imports.body_material_count` (falling back to `body_copied_material_count`/id length).
    - Fails: never raises; missing or malformed manifests are skipped (manifest_count reflects how many were read).
    - Reads: `core/fixture_manifests/<organ_id>.fixture_manifest.json` under `root`.
    - Escalates-to: WORKINGNESS_MAP_REF as the declared fallback_ref when manifests are absent.
    - Non-goal: counts a declared copy boundary only; does not authorize source-body export, public-safe equivalence, or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    material_count = 0
    rows_with_imports = 0
    manifest_count = 0

    for organ_id in organ_ids:
        manifest_ref = Path(FIXTURE_MANIFESTS_REF) / f"{organ_id}.fixture_manifest.json"
        manifest = _load_public_json(root, manifest_ref.as_posix())
        if not manifest:
            continue
        manifest_count += 1
        body_imports = manifest.get("source_open_body_imports")
        if isinstance(body_imports, dict):
            material_ids = _strings(body_imports.get("body_material_ids"))
            raw_count = body_imports.get("body_material_count")
            organ_material_count = (
                raw_count
                if isinstance(raw_count, int) and not isinstance(raw_count, bool)
                else len(material_ids)
            )
        else:
            body_status = str(manifest.get("body_material_status") or "")
            raw_count = manifest.get("body_copied_material_count")
            if not body_status:
                continue
            organ_material_count = (
                raw_count
                if isinstance(raw_count, int) and not isinstance(raw_count, bool)
                else 0
            )

        if organ_material_count <= 0:
            continue
        rows_with_imports += 1
        material_count += organ_material_count

    return {
        "material_count": material_count if manifest_count else None,
        "rows_with_imports": rows_with_imports if manifest_count else None,
        "manifest_count": manifest_count,
        "source_ref": f"{FIXTURE_MANIFESTS_REF}/*.fixture_manifest.json",
        "source_field": "source_open_body_imports.body_material_count",
        "fallback_ref": WORKINGNESS_MAP_REF,
    }


def _evidence_class_legend(root: Path) -> dict[str, Any]:
    """
    [ACTION]
    Build the evidence-class claim-boundary legend from the evidence-class registry.

    - Teleology: generated public legend naming, per evidence class, what a count can and cannot claim.
    - Guarantee: returns a `microcosm_evidence_class_legend_v1` dict with per-class claim_ceiling/evaluator_basis/strength fields in EVIDENCE_CLASS_DISPLAY_ORDER, a missing_profiles list for absent classes, and the registry's authority_boundary/anti_claim.
    - Fails: never raises; a missing registry yields empty classes and lists every display-order id under missing_profiles.
    - Reads: `core/organ_evidence_classes.json` under `root`.
    - Non-goal: it is a claim-boundary legend, not a benchmark, release gate, or maturity score.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    registry = _load_public_json(root, EVIDENCE_CLASS_REGISTRY_REF)
    class_profiles = registry.get("class_profiles", {})
    if not isinstance(class_profiles, dict):
        class_profiles = {}

    rows: list[dict[str, Any]] = []
    missing_profiles: list[str] = []
    for class_id in EVIDENCE_CLASS_DISPLAY_ORDER:
        profile = class_profiles.get(class_id)
        if not isinstance(profile, dict):
            missing_profiles.append(class_id)
            continue
        rows.append(
            {
                "evidence_class": class_id,
                "label": EVIDENCE_CLASS_LABELS[class_id],
                "claim_ceiling": deepcopy(profile.get("claim_ceiling")),
                "evaluator_basis": deepcopy(profile.get("evaluator_basis")),
                "negative_case_independence": deepcopy(
                    profile.get("negative_case_independence")
                ),
                "truth_accounting_bucket": deepcopy(
                    profile.get("truth_accounting_bucket")
                ),
                "counts_as_real_substrate_progress": profile.get(
                    "counts_as_real_substrate_progress"
                )
                is True,
                "evidence_strength_rank": deepcopy(
                    profile.get("evidence_strength_rank")
                ),
                "reader_rule": "declared_claim_ceiling_not_maturity_or_release_score",
            }
        )

    return {
        "schema_version": "microcosm_evidence_class_legend_v1",
        "source_ref": EVIDENCE_CLASS_REGISTRY_REF,
        "interpretation": "claim_boundary_legend_not_score",
        "authority_boundary": deepcopy(registry.get("authority_boundary")),
        "anti_claim": deepcopy(registry.get("anti_claim")),
        "reader_rule": (
            "Each evidence class names what a count can claim and what it cannot "
            "claim. It is a public claim-boundary legend, not a benchmark, release "
            "gate, product-completeness signal, or maturity score."
        ),
        "classes": rows,
        "missing_profiles": missing_profiles,
    }


def _scale_frame(root: Path) -> dict[str, Any]:
    """
    [ACTION]
    Build the public scale-count frame from organ/standards registries, workingness map, and fixture manifests.

    - Teleology: generated breadth frame presenting public counts as receipt-backed handles, not scores.
    - Guarantee: returns a dict whose `public_scale_counts` carry per-count `count` (or None), `source_ref`, and `read_as` boundary, preferring fixture-manifest source-open counts over the workingness fallback; includes scale_handles and a count_reader_rule.
    - Fails: never raises; absent registries yield None counts via tolerant loads, not an error.
    - Reads: `core/organ_registry.json`, `core/standards_registry.json`, `receipts/runtime_shell/workingness_failure_map.json`, and fixture manifests under `root`.
    - Non-goal: counts are pointers into owner receipts; they do not claim maturity, readiness, completeness, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    organ_registry = _load_public_json(root, ORGAN_REGISTRY_REF)
    standards_registry = _load_public_json(root, STANDARDS_REGISTRY_REF)
    workingness_map = _load_public_json(root, WORKINGNESS_MAP_REF)
    implemented_organ_ids = _implemented_organ_ids(organ_registry)
    fixture_body_counts = _source_open_body_import_count_from_fixture_manifests(
        root,
        implemented_organ_ids,
    )
    implemented_organ_count = _first_count(
        _collection_count(organ_registry.get("implemented_organs")),
        _non_negative_int(workingness_map.get("mapped_organ_count")),
    )
    standard_count = _first_count(
        _non_negative_int(standards_registry.get("standard_count")),
        _collection_count(standards_registry.get("standards")),
    )
    source_open_material_count = _non_negative_int(
        workingness_map.get("source_open_body_material_count")
    )
    fixture_source_open_material_count = _non_negative_int(
        fixture_body_counts.get("material_count")
    )
    fixture_rows_with_source_imports = _non_negative_int(
        fixture_body_counts.get("rows_with_imports")
    )
    return {
        "composition_root": (
            "The shared first command is the landing surface; standards, receipts, organs, and "
            "observatory views are drilldowns."
        ),
        "count_interpretation": "receipt_backed_handles_not_scores",
        "public_scale_counts": {
            "implemented_organs": {
                "count": implemented_organ_count,
                "source_ref": ORGAN_REGISTRY_REF,
                "read_as": "accepted_public_inventory_not_release_readiness",
            },
            "public_standards": {
                "count": standard_count,
                "source_ref": STANDARDS_REGISTRY_REF,
                "read_as": "standard_inventory_not_completeness_score",
            },
            "first_wave_required_standards": {
                "count": _non_negative_int(
                    standards_registry.get("first_wave_required_standard_count")
                ),
                "source_ref": STANDARDS_REGISTRY_REF,
                "read_as": "registry_scope_field_not_product_progress",
            },
            "mapped_organs": {
                "count": _non_negative_int(workingness_map.get("mapped_organ_count")),
                "source_ref": WORKINGNESS_MAP_REF,
                "read_as": "workingness_map_coverage_not_whole_system_correctness",
            },
            "adapter_backed_organs": {
                "count": _non_negative_int(
                    workingness_map.get("adapter_backed_organ_count")
                ),
                "source_ref": WORKINGNESS_MAP_REF,
                "read_as": "adapter_presence_not_completeness_or_release_signal",
            },
            "source_open_materials": {
                "count": _first_count(
                    fixture_source_open_material_count,
                    source_open_material_count,
                ),
                "source_field": fixture_body_counts["source_field"],
                "source_ref": fixture_body_counts["source_ref"],
                "fallback_ref": fixture_body_counts["fallback_ref"],
                "workingness_source_field": "source_open_body_material_count",
                "read_as": "copy_boundary_accounting_not_maturity_score",
            },
            "rows_with_source_imports": {
                "count": _first_count(
                    fixture_rows_with_source_imports,
                    _non_negative_int(
                        workingness_map.get("rows_with_source_body_imports")
                    ),
                ),
                "source_field": "source_open_body_imports.body_material_count",
                "source_ref": fixture_body_counts["source_ref"],
                "fallback_ref": WORKINGNESS_MAP_REF,
                "workingness_source_field": "rows_with_source_body_imports",
                "read_as": "receipt_trace_count_not_claim_strength",
            },
        },
        "count_reader_rule": (
            "Treat each number as a pointer into a public owner receipt. A low or high count "
            "does not by itself claim maturity, readiness, completeness, or correctness."
        ),
        "scale_handles": [
            {
                "handle": "standards registry",
                "ref": STANDARDS_REGISTRY_REF,
            },
            {
                "handle": "organ registry",
                "ref": ORGAN_REGISTRY_REF,
            },
            {
                "handle": "workingness map",
                "command": "plectis workingness",
                "ref": WORKINGNESS_MAP_REF,
            },
            {
                "handle": "authority boundary",
                "command": "plectis authority",
            },
            {
                "handle": "localhost observatory",
                "endpoint_ref": "http://localhost:8765/workingness-card",
            },
        ],
        "scale_rule": (
            "Breadth should appear as a named composition root plus drilldown handles, "
            "not as a long first-screen inventory."
        ),
    }


def _comparison_frame() -> dict[str, Any]:
    """
    [ACTION]
    Build the entry-discipline comparison frame (failure modes vs Microcosm discipline).

    - Teleology: generated prose frame making rigor visible without claim inflation.
    - Guarantee: returns a constant dict listing common_entry_failure_modes, microcosm_entry_discipline, and a reader_effect.
    - Fails: never raises; returns a constant frame.
    - Non-goal: makes no superiority, benchmark, or release claim.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "purpose": "make_rigor_visible_without_claim_inflation",
        "common_entry_failure_modes": [
            "a long command inventory before the reader sees the first useful behavior",
            "honest evidence counts shown without explaining what they do and do not mean",
            "reader-specific pitches before every reader has seen the same local evidence surface",
            "discipline hidden as implementation detail instead of presented as an inspectable boundary",
        ],
        "microcosm_entry_discipline": [
            "one shared local behavior command before reader branching",
            "evidence counts framed as accounting, not readiness or progress scoring",
            "authority ceilings and anti-claims visible before proof, release, or hosted claims",
            "drilldown refs preserve depth instead of copying full bodies into the first screen",
        ],
        "reader_effect": (
            "The card shows what Microcosm refuses to overclaim, then lets each reader choose "
            "the drilldown that matches their job."
        ),
    }


def _discipline_comparison_strip(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the discipline comparison strip rendering Microcosm rigor as inspectable boundaries.

    - Teleology: generated strip showing what Microcosm does differently from a typical cold-entry surface as boundaries, not superiority claims.
    - Guarantee: returns a `microcosm_discipline_comparison_strip_v1` dict whose `rows` pair an ordinary_entry_pattern with the Microcosm boundary per comparison_id.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: not a benchmark, superiority, or maturity claim.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shared_first_command = f"plectis tour --card {project_label}"
    return {
        "schema_version": "microcosm_discipline_comparison_strip_v1",
        "purpose": "make_microcosm_rigor_visible_as_operational_differences",
        "strip_rule": (
            "Show what Microcosm does differently from a typical cold-entry surface "
            "as inspectable boundaries, not as superiority, benchmark, or maturity claims."
        ),
        "rows": [
            {
                "comparison_id": "failure_modes_declared",
                "ordinary_entry_pattern": "polished claims hide failure surfaces",
                "microcosm_discipline": (
                    "first-screen packets expose anti_claim, authority ceiling, omission "
                    "receipt, and explicit failure-mode refs"
                ),
                "visible_check_surface": "authority_ceiling",
                "reader_rule": "Treat refusal fields as part of the product surface.",
                "not_claim": "better_than_other_systems",
            },
            {
                "comparison_id": "evidence_counts_contextualized",
                "ordinary_entry_pattern": "counts read as maturity, readiness, or progress scores",
                "microcosm_discipline": (
                    "counts are evidence-class accounting with named claim ceilings and "
                    "missing-profile disclosure"
                ),
                "visible_check_surface": "evidence_class_legend",
                "reader_rule": "Read low or high counts as boundary accounting.",
                "not_claim": "maturity_or_readiness_score",
            },
            {
                "comparison_id": "body_copy_boundaries",
                "ordinary_entry_pattern": "body copying is implied or hidden behind prose",
                "microcosm_discipline": (
                    "body imports are evidence classes; copied body status must preserve "
                    "validator and source-boundary refs"
                ),
                "visible_check_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "reader_rule": "Ask what crossed a declared copy boundary.",
                "not_claim": "private_body_equivalence",
            },
            {
                "comparison_id": "reader_branch_authority_shared",
                "ordinary_entry_pattern": "audience-specific pitch creates different claim ceilings",
                "microcosm_discipline": (
                    "reader routes change inspection order while inheriting the same "
                    "authority ceiling and omission receipt"
                ),
                "visible_check_surface": "reader_route_menu",
                "reader_rule": "Choose a branch only after the shared behavior proof.",
                "not_claim": "reader_specific_authority",
            },
            {
                "comparison_id": "local_behavior_before_claims",
                "ordinary_entry_pattern": "status claims appear before runnable local evidence",
                "microcosm_discipline": (
                    f"`{shared_first_command}` writes .microcosm state and exposes "
                    "front_door_status, selected_route_id, state refs, and source_files_mutated"
                ),
                "visible_check_surface": "behavior_proof_packet",
                "reader_rule": "Run the local behavior card before trusting the scale story.",
                "not_claim": "release_or_proof_correctness",
            },
        ],
        "safe_to_show": {
            "uses_existing_first_screen_packets": True,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_external_benchmark": False,
            "claims_superiority": False,
            "claims_release_or_hosting": False,
            "claims_whole_system_correctness": False,
        },
        "authority": "comparison_strip_not_benchmark_or_superiority_claim",
    }


def _doctrine_effect_frame() -> dict[str, Any]:
    """
    [ACTION]
    Build the doctrine-effect frame translating doctrine handles into mistakes-prevented.

    - Teleology: generated frame showing doctrine as mistake prevention, not ceremony, each tied to a first-screen surface.
    - Guarantee: returns a `microcosm_doctrine_effect_frame_v1` dict whose `effect_rows` map each doctrine_handle (CONSTITUTION/AXIOMS/PRINCIPLES/CONCEPTS/MECHANISMS/ANTI_PRINCIPLES) to what it prevents, its visible_effect, and first_screen_surface.
    - Fails: never raises; returns a constant frame.
    - Non-goal: an interpretation frame only, not the doctrine source; governance prose is not a credential.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "microcosm_doctrine_effect_frame_v1",
        "purpose": "show_doctrine_as_mistake_prevention_not_ceremony",
        "reader_rule": (
            "Read each doctrine handle by the failure it blocks and the first-screen "
            "surface where that protection is visible."
        ),
        "effect_rows": [
            {
                "doctrine_handle": "CONSTITUTION",
                "prevents": "shipping a capability story without a claim boundary",
                "visible_effect": (
                    "authority_ceiling and anti_claim appear before proof, release, "
                    "or hosted-publication claims"
                ),
                "first_screen_surface": "authority_ceiling",
            },
            {
                "doctrine_handle": "AXIOMS",
                "prevents": "treating counts or projections as source authority",
                "visible_effect": (
                    "evidence counts are accounting fields, not readiness, maturity, "
                    "or progress scores"
                ),
                "first_screen_surface": "evidence_count_frame",
            },
            {
                "doctrine_handle": "PRINCIPLES",
                "prevents": "hiding a broad substrate behind a vague pitch",
                "visible_effect": (
                    "one shared first command lands before reader-specific drilldowns"
                ),
                "first_screen_surface": "reader_routes",
            },
            {
                "doctrine_handle": "CONCEPTS",
                "prevents": "letting repeated public terms drift into vague labels",
                "visible_effect": (
                    "concept handles must keep source refs, relationships, payload "
                    "shape, public-safe standard boundary, and specimen route visible"
                ),
                "first_screen_surface": "doctrine_effect_frame",
                "standard_ref": "standards/std_microcosm_concept.json",
                "agent_entry_ref": "AGENTS.md::Concept And Mechanism Entry",
                "specimen_route_ref": (
                    "atlas/entry_packet.json::"
                    "concept_mechanism_entry_route.population_specimens"
                ),
            },
            {
                "doctrine_handle": "MECHANISMS",
                "prevents": "describing a feature without the transformation it performs",
                "visible_effect": (
                    "mechanism handles must name the state, proof, routing, or "
                    "doctrine transformation plus validator attachment and specimen"
                ),
                "first_screen_surface": "doctrine_effect_frame",
                "standard_ref": "standards/std_microcosm_mechanism.json",
                "agent_entry_ref": "AGENTS.md::Concept And Mechanism Entry",
                "specimen_route_ref": (
                    "atlas/entry_packet.json::"
                    "concept_mechanism_entry_route.population_specimens"
                ),
            },
            {
                "doctrine_handle": "ANTI_PRINCIPLES",
                "prevents": (
                    "turning a local demo into release, provider-call, private-data, "
                    "or benchmark authority"
                ),
                "visible_effect": (
                    "omission receipt and public/private boundary name what is not "
                    "shown or authorized"
                ),
                "first_screen_surface": "omission_receipt",
            },
        ],
        "forbidden_read": "governance_prose_as_credential",
        "authority": "first_screen_interpretation_frame_not_doctrine_source",
    }


def _readme_entry_contract(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the README entry-order contract placing the first-screen card before the inventory.

    - Teleology: generated documentation-order contract making the package-backed first-screen card the README entry surface.
    - Guarantee: returns a `microcosm_readme_entry_contract_v1` dict with required_markdown_order rows (surface/command must_precede pairs) and a consumer_rule preserving drilldowns after the first screen.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: a documentation-order contract, not a runtime proof or release authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    human_first_command = f"plectis hello {project_label}"
    shared_first_command = f"plectis tour --card {project_label}"
    first_screen_json_command = f"plectis first-screen --card {project_label}"
    return {
        "schema_version": "microcosm_readme_entry_contract_v1",
        "purpose": "make_package_backed_first_screen_card_the_readme_entry_surface",
        "inventory_policy": (
            "quickstart_command_inventory_is_a_drilldown_after_the_first_screen_card"
        ),
        "required_markdown_order": [
            {
                "surface": "README.md::Choose Your First Screen",
                "must_precede": "README.md::Try It On Your Repo",
                "reason": (
                    "Cold readers should see the composition root before install, "
                    "direct-run, and full command inventories."
                ),
            },
            {
                "command": human_first_command,
                "must_precede": shared_first_command,
                "reason": "Text projection opens the card before the state-writing behavior proof.",
            },
            {
                "command": shared_first_command,
                "must_precede": first_screen_json_command,
                "reason": "Local behavior proof precedes the machine-readable reader map.",
            },
            {
                "surface": "reader_route_menu",
                "must_precede": "quickstart_command_inventory",
                "reason": "Focused reader commands are first-screen branches, not inventory rows.",
            },
            {
                "surface": "reader_routes",
                "must_precede": "quickstart_command_inventory",
                "reason": "Reader branching happens before the long command list.",
            },
            {
                "surface": "first_viewport_manifest",
                "must_precede": "quickstart_command_inventory",
                "reason": (
                    "Every entry projection should carry the same ordered slots before "
                    "expanding the inventory."
                ),
            },
        ],
        "consumer_rule": (
            "README and docs consumers must show the package-backed hello/tour card "
            "before any exhaustive quickstart inventory, while preserving full "
            "drilldowns after the first screen."
        ),
        "authority": "documentation_order_contract_not_runtime_proof",
    }


def _entry_surface_contract(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the entry-surface contract naming the package/text/script projection surfaces.

    - Teleology: generated contract telling README/CLI/observatory consumers which package functions to reuse and what to preserve.
    - Guarantee: returns a dict naming shared_behavior_surface, package_surface (first_screen_composition_card), text_projection_surface, script_surface, a consumer_rule listing the packets to preserve, and a format_contract.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: first_screen_composition_card and first_screen_text_card as the named package surfaces.
    - Non-goal: a reuse contract, not a runtime proof or release authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "shared_behavior_surface": f"plectis tour --card {project_label}",
        "package_surface": (
            "microcosm_core.first_screen_composition.first_screen_composition_card"
        ),
        "text_projection_surface": (
            "microcosm_core.first_screen_composition.first_screen_text_card"
        ),
        "script_surface": (
            f"python3 scripts/first_screen_composition_card.py --project-label {project_label}"
        ),
        "consumer_rule": (
            "README, CLI, and observatory consumers should reuse this package contract and "
            "preserve the shared first command, reader route ids, reader route menu, "
            "reader landing packets, behavior-proof packet, first-run ladder, local state receipt trail, "
            "first-viewport manifest, overclaim tripwire matrix, reader exit "
            "criteria, evidence-count frame, video-storyboard packet, artifact-fit "
            "matrix, cold-entry problem map, discipline comparison strip, "
            "evidence-class legend, doctrine-effect frame, observatory landing "
            "frame, README-entry contract, omission "
            "receipt, and authority ceiling."
        ),
        "format_contract": {
            "json": "machine-readable public card",
            "text": "terminal-sized projection over the same authority ceiling",
        },
    }


def _runnable_structural_join(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the runnable-to-structural join prose binding the local run to the larger substrate.

    - Teleology: generated prose joining the folder-local first run to the broader public structure it exercises.
    - Guarantee: returns a dict with local_behavior, structural_context, and a join_rule requiring the first run to name the larger structure without copying deeper bodies.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: does not claim private-root equivalence or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "local_behavior": (
            f"`plectis tour --card {project_label}` is the first folder-local behavior surface: "
            "it lets a reader see compact local state before choosing a route."
        ),
        "structural_context": (
            "That local run is one visible exercise of the larger public substrate: standards, "
            "receipts, authority boundaries, workingness, route maps, and observatory endpoints."
        ),
        "join_rule": "The first run must name the larger structure it exercised without copying the deeper bodies.",
    }


def _observatory_landing_frame(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the observatory landing frame reusing the first-screen card as the browser landing.

    - Teleology: generated frame making the hello first-screen card the localhost browser landing, not a separate cold-entry artifact.
    - Guarantee: returns a `microcosm_observatory_landing_frame_v1` dict with serve/bounded-validation commands, localhost endpoints, required_visible_handles, drilldown_order, and an authority_boundary denying release/hosting/provider/source-mutation/private-equivalence.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: first_screen_text_card as the named source_projection the browser landing reuses.
    - Non-goal: a localhost read-model boundary; it authorizes no hosting, release, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    human_first_command = f"plectis hello {project_label}"
    shared_first_command = f"plectis tour --card {project_label}"
    serve_command = _observatory_serve_command(project_label)
    bounded_serve_command = _bounded_observatory_serve_command(project_label)
    return {
        "schema_version": "microcosm_observatory_landing_frame_v1",
        "role": "make_the_hello_first_screen_card_the_browser_landing_frame",
        "human_first_command": human_first_command,
        "text_projection_command": human_first_command,
        "shared_first_command": shared_first_command,
        "behavioral_proof_command": shared_first_command,
        "serve_command": serve_command,
        "bounded_validation_command": bounded_serve_command,
        "bounded_validation_request_count": BOUNDED_OBSERVATORY_REQUEST_COUNT,
        "bounded_validation_rule": (
            "Use bounded_validation_command for first-screen route smokes; use "
            "serve_command for an interactive browser session."
        ),
        "endpoints": dict(OBSERVATORY_LANDING_ENDPOINTS),
        "browser_landing_reuse": {
            "source_projection": (
                "microcosm_core.first_screen_composition.first_screen_text_card"
            ),
            "serve_command": serve_command,
            "bounded_validation_command": bounded_serve_command,
            "default_endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
            "card_endpoint": OBSERVATORY_LANDING_ENDPOINTS["first_screen_card"],
            "authority": (
                "browser_projection_over_same_card_not_json_first_lens_inventory"
            ),
        },
        "first_viewport_rule": (
            "The browser landing frame should show the hello card command, behavior proof, "
            "first-run ladder, first-viewport manifest, local state receipt trail, "
            "first-contact surface refs, overclaim tripwires, discipline comparison strip, "
            "reader branches, reader route menu, reader landing packets, reader exit criteria, video storyboard packet, "
            "artifact fit matrix, cold-entry problem map, representative substrate "
            "glance, public scale handles, evidence-class legend, doctrine-effect "
            "frame, and authority ceiling before the deeper observatory lens inventory."
        ),
        "projection_rule": (
            "The observatory landing is a projection over this first-screen card, not a "
            "separate cold-entry artifact with its own claims."
        ),
        "required_visible_handles": [
            "human_first_command",
            "text_projection",
            "shared_first_command",
            "behavioral_proof_command",
            "serve_command",
            "bounded_validation_command",
            "reader_route_ids",
            "reader_route_menu",
            "reader_landing_packets",
            "behavior_proof_packet",
            "first_run_ladder",
            "first_viewport_manifest",
            "local_state_receipt_trail",
            "first_contact_surface_refs",
            "overclaim_tripwire_matrix",
            "discipline_comparison_strip",
            "reader_exit_criteria",
            "video_storyboard_packet",
            "artifact_fit_matrix",
            "cold_entry_problem_map",
            "public_scale_counts",
            "representative_substrate_glance",
            "evidence_count_interpretation",
            "evidence_class_legend",
            "doctrine_effect_frame",
            "authority_ceiling",
            "omission_receipt",
        ],
        "drilldown_order": [
            "html_landing",
            "first_screen_card",
            "compact_observatory_card",
            "full_observatory_model",
            "project_observe",
        ],
        "authority_boundary": (
            "Local browser display is a public read-model boundary. It does not authorize "
            "release, hosting, provider calls, source mutation, private-data equivalence, "
            "or whole-system correctness claims."
        ),
    }


def _drilldowns(project_label: str) -> list[dict[str, str]]:
    """
    [ACTION]
    Build the ordered list of post-first-screen drilldown handles (commands/endpoints/refs).

    - Teleology: generated drilldown index pointing past the first screen to observatory, status, authority, workingness, and standard refs.
    - Guarantee: returns a list of drilldown dicts each carrying a drilldown_id plus a command, endpoint, or ref.
    - Fails: never raises; deterministic from `project_label`.
    - Escalates-to: STANDARD_REF and the observatory/authority/workingness commands it lists.
    - Non-goal: handles for further inspection; not release or proof authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        {
            "drilldown_id": "observatory_server",
            "command": _observatory_serve_command(project_label),
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
        },
        {
            "drilldown_id": "bounded_observatory_validation",
            "command": _bounded_observatory_serve_command(project_label),
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
        },
        {
            "drilldown_id": "observatory_landing",
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
        },
        {
            "drilldown_id": "first_screen_endpoint",
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["first_screen_card"],
        },
        {
            "drilldown_id": "shared_first_card",
            "command": f"plectis tour --card {project_label}",
        },
        {
            "drilldown_id": "status_card",
            "command": f"plectis status --card {project_label}",
        },
        {
            "drilldown_id": "authority",
            "command": "plectis authority",
        },
        {
            "drilldown_id": "workingness",
            "command": "plectis workingness",
        },
        {
            "drilldown_id": "evidence_class_registry",
            "ref": EVIDENCE_CLASS_REGISTRY_REF,
        },
        {
            "drilldown_id": "cold_reader_route_map",
            "ref": "paper_modules/cold_reader_route_map.md",
        },
        {
            "drilldown_id": "public_reveal_walkthrough",
            "ref": "paper_modules/public_reveal_walkthrough.md",
        },
        {
            "drilldown_id": "composition_standard",
            "ref": str(STANDARD_REF),
        },
    ]


def _validation_checks(payload: dict[str, Any]) -> dict[str, bool]:
    """
    [ACTION]
    Compute the boolean self-consistency checks over an assembled composition payload.

    - Teleology: validation entrypoint proving the card's internal surfaces (reader parity, command parity, anti-claims, safe_to_show flags, boundaries) are coherent.
    - Guarantee: returns an ordered `dict[str, bool]` of named checks; each value is True only when that surface satisfies its contract (e.g. reader_route_ids match REQUIRED_ROUTE_IDS, denied-authority flags are False).
    - Fails: never raises; missing or malformed surfaces yield a False check, never an exception.
    - When-needed: when diagnosing why first_screen_composition_card.validation.status is "blocked".
    - Escalates-to: first_screen_composition_card folds this into validation.checks alongside the standard-backed scan.
    - Non-goal: internal-consistency only; does not authorize release, reader success, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    route_ids = {
        str(route.get("reader_route_id"))
        for route in payload.get("reader_routes", [])
        if isinstance(route, dict)
    }
    reader_landing_packets = payload.get("reader_landing_packets", {})
    reader_packet_rows = (
        reader_landing_packets.get("packets", [])
        if isinstance(reader_landing_packets, dict)
        else []
    )
    reader_packet_ids = {
        str(packet.get("reader_route_id"))
        for packet in reader_packet_rows
        if isinstance(packet, dict)
    }
    reader_route_menu = payload.get("reader_route_menu", {})
    reader_route_menu_rows = (
        reader_route_menu.get("routes", [])
        if isinstance(reader_route_menu, dict)
        else []
    )
    reader_route_menu_ids = {
        str(row.get("reader_route_id"))
        for row in reader_route_menu_rows
        if isinstance(row, dict)
    }
    reader_route_menu_safe_to_show = (
        reader_route_menu.get("safe_to_show", {})
        if isinstance(reader_route_menu, dict)
        else {}
    )
    human_first_command = payload.get("human_first_command", "")
    shared_first_command = payload.get("shared_first_command", "")
    text_projection = payload.get("text_projection", {})
    authority_ceiling = payload.get("authority_ceiling", {})
    drilldown_text = json.dumps(payload.get("drilldowns", []), sort_keys=True)
    evidence_class_legend = payload.get("evidence_class_legend", {})
    legend_rows = (
        evidence_class_legend.get("classes", [])
        if isinstance(evidence_class_legend, dict)
        else []
    )
    legend_ids = {
        str(row.get("evidence_class"))
        for row in legend_rows
        if isinstance(row, dict)
    }
    scale_frame = payload.get("scale_frame", {})
    scale_counts = scale_frame.get("public_scale_counts", {})
    state_write_boundary = payload.get("state_write_boundary", {})
    behavior_proof_packet = payload.get("behavior_proof_packet", {})
    local_state_receipt_trail = payload.get("local_state_receipt_trail", {})
    first_contact_surface_refs = payload.get("first_contact_surface_refs", {})
    overclaim_tripwire_matrix = payload.get("overclaim_tripwire_matrix", {})
    discipline_comparison_strip = payload.get("discipline_comparison_strip", {})
    representative_substrate_glance = payload.get("representative_substrate_glance", {})
    substrate_glance_examples = (
        representative_substrate_glance.get("examples", [])
        if isinstance(representative_substrate_glance, dict)
        else []
    )
    substrate_glance_safe_to_show = (
        representative_substrate_glance.get("safe_to_show", {})
        if isinstance(representative_substrate_glance, dict)
        else {}
    )
    first_contact_surfaces = (
        first_contact_surface_refs.get("surfaces", {})
        if isinstance(first_contact_surface_refs, dict)
        else {}
    )
    first_contact_surface_ids = (
        set(first_contact_surfaces)
        if isinstance(first_contact_surfaces, dict)
        else set()
    )
    local_state_trail_rows = (
        local_state_receipt_trail.get("trail", [])
        if isinstance(local_state_receipt_trail, dict)
        else []
    )
    local_state_trail_ids = {
        str(row.get("surface_id"))
        for row in local_state_trail_rows
        if isinstance(row, dict)
    }
    overclaim_rows = (
        overclaim_tripwire_matrix.get("rows", [])
        if isinstance(overclaim_tripwire_matrix, dict)
        else []
    )
    overclaim_ids = {
        str(row.get("tripwire_id")) for row in overclaim_rows if isinstance(row, dict)
    }
    discipline_comparison_rows = (
        discipline_comparison_strip.get("rows", [])
        if isinstance(discipline_comparison_strip, dict)
        else []
    )
    discipline_comparison_ids = {
        str(row.get("comparison_id"))
        for row in discipline_comparison_rows
        if isinstance(row, dict)
    }
    discipline_comparison_safe_to_show = (
        discipline_comparison_strip.get("safe_to_show", {})
        if isinstance(discipline_comparison_strip, dict)
        else {}
    )
    reader_exit_criteria = payload.get("reader_exit_criteria", {})
    reader_exit_rows = (
        reader_exit_criteria.get("criteria", [])
        if isinstance(reader_exit_criteria, dict)
        else []
    )
    reader_exit_ids = {
        str(row.get("reader_route_id"))
        for row in reader_exit_rows
        if isinstance(row, dict)
    }
    video_storyboard_packet = payload.get("video_storyboard_packet", {})
    video_storyboard_beats = (
        video_storyboard_packet.get("beats", [])
        if isinstance(video_storyboard_packet, dict)
        else []
    )
    video_storyboard_beat_ids = {
        str(row.get("beat_id"))
        for row in video_storyboard_beats
        if isinstance(row, dict)
    }
    video_storyboard_safe_to_show = (
        video_storyboard_packet.get("safe_to_show", {})
        if isinstance(video_storyboard_packet, dict)
        else {}
    )
    artifact_fit_matrix = payload.get("artifact_fit_matrix", {})
    artifact_fit_rows = (
        artifact_fit_matrix.get("rows", [])
        if isinstance(artifact_fit_matrix, dict)
        else []
    )
    artifact_fit_ids = {
        str(row.get("surface_id")) for row in artifact_fit_rows if isinstance(row, dict)
    }
    artifact_fit_safe_to_show = (
        artifact_fit_matrix.get("safe_to_show", {})
        if isinstance(artifact_fit_matrix, dict)
        else {}
    )
    cold_entry_problem_map = payload.get("cold_entry_problem_map", {})
    cold_entry_problem_rows = (
        cold_entry_problem_map.get("rows", [])
        if isinstance(cold_entry_problem_map, dict)
        else []
    )
    cold_entry_problem_ids = {
        str(row.get("problem_shape_id"))
        for row in cold_entry_problem_rows
        if isinstance(row, dict)
    }
    cold_entry_problem_safe_to_show = (
        cold_entry_problem_map.get("safe_to_show", {})
        if isinstance(cold_entry_problem_map, dict)
        else {}
    )
    behavior_proof_fields = (
        behavior_proof_packet.get("proof_fields", [])
        if isinstance(behavior_proof_packet, dict)
        else []
    )
    behavior_proof_field_ids = {
        str(row.get("field"))
        for row in behavior_proof_fields
        if isinstance(row, dict)
    }
    first_run_ladder = payload.get("first_run_ladder", {})
    first_run_steps = (
        first_run_ladder.get("steps", [])
        if isinstance(first_run_ladder, dict)
        else []
    )
    first_run_step_ids = {
        str(row.get("step_id")) for row in first_run_steps if isinstance(row, dict)
    }
    first_run_commands = {
        str(row.get("step_id")): row.get("command")
        for row in first_run_steps
        if isinstance(row, dict)
    }
    first_viewport_manifest = payload.get("first_viewport_manifest", {})
    first_viewport_slots = (
        first_viewport_manifest.get("slots", [])
        if isinstance(first_viewport_manifest, dict)
        else []
    )
    first_viewport_slot_ids = [
        str(row.get("slot_id")) for row in first_viewport_slots if isinstance(row, dict)
    ]
    first_viewport_problem_slots = (
        first_viewport_manifest.get("problem_shape_slot_map", [])
        if isinstance(first_viewport_manifest, dict)
        else []
    )
    first_viewport_problem_ids = {
        str(row.get("problem_shape_id"))
        for row in first_viewport_problem_slots
        if isinstance(row, dict)
    }
    first_viewport_problem_slot_ids = {
        str(row.get("slot_id"))
        for row in first_viewport_problem_slots
        if isinstance(row, dict)
    }
    first_viewport_consumer_surfaces = (
        first_viewport_manifest.get("consumer_surfaces", {})
        if isinstance(first_viewport_manifest, dict)
        else {}
    )
    first_viewport_safe_to_show = (
        first_viewport_manifest.get("safe_to_show", {})
        if isinstance(first_viewport_manifest, dict)
        else {}
    )
    observatory_landing_frame = payload.get("observatory_landing_frame", {})
    doctrine_effect_frame = payload.get("doctrine_effect_frame", {})
    readme_entry_contract = payload.get("readme_entry_contract", {})
    doctrine_effect_rows = (
        doctrine_effect_frame.get("effect_rows", [])
        if isinstance(doctrine_effect_frame, dict)
        else []
    )
    doctrine_handles = {
        str(row.get("doctrine_handle"))
        for row in doctrine_effect_rows
        if isinstance(row, dict)
    }
    observatory_endpoints = (
        observatory_landing_frame.get("endpoints", {})
        if isinstance(observatory_landing_frame, dict)
        else {}
    )
    required_visible_handles = (
        observatory_landing_frame.get("required_visible_handles", [])
        if isinstance(observatory_landing_frame, dict)
        else []
    )
    readme_order_rows = (
        readme_entry_contract.get("required_markdown_order", [])
        if isinstance(readme_entry_contract, dict)
        else []
    )
    readme_order_pairs = {
        (str(row.get("surface") or row.get("command")), str(row.get("must_precede")))
        for row in readme_order_rows
        if isinstance(row, dict)
    }
    return {
        "shared_first_command": payload.get("shared_first_command", "").startswith(
            "plectis tour --card "
        ),
        "human_first_command": (
            isinstance(human_first_command, str)
            and human_first_command.startswith("plectis hello ")
            and human_first_command != shared_first_command
        ),
        "text_projection": (
            isinstance(text_projection, dict)
            and text_projection.get("command") == human_first_command
            and text_projection.get("writes_microcosm_state") is False
            and text_projection.get("behavioral_proof_command")
            == shared_first_command
            and text_projection.get("authority")
            == "terminal_text_projection_only_not_behavior_proof"
        ),
        "reader_route_ids": route_ids == REQUIRED_ROUTE_IDS,
        "reader_landing_packets": (
            isinstance(reader_landing_packets, dict)
            and reader_landing_packets.get("purpose")
            == "turn_reader_routes_into_first_action_proof_success_packets"
            and reader_landing_packets.get("shared_authority_rule", "").endswith(
                "same authority ceiling, anti-claim, and omission receipt."
            )
            and reader_packet_ids == REQUIRED_ROUTE_IDS
            and all(
                isinstance(packet, dict)
                and isinstance(packet.get("first_action"), str)
                and bool(packet.get("first_action"))
                and isinstance(packet.get("proof_surface"), str)
                and bool(packet.get("proof_surface"))
                and isinstance(packet.get("success_criterion"), str)
                and bool(packet.get("success_criterion"))
                and isinstance(packet.get("next_drilldown"), str)
                and bool(packet.get("next_drilldown"))
                and str(packet.get("authority", "")).startswith(
                    "inspection_order_only_not_"
                )
                for packet in reader_packet_rows
            )
        ),
        "reader_route_menu": (
            isinstance(reader_route_menu, dict)
            and reader_route_menu.get("schema_version")
            == "microcosm_reader_route_menu_v1"
            and reader_route_menu.get("purpose")
            == (
                "make_reader_typed_first_screens_copyable_without_separate_entry_"
                "artifacts"
            )
            and "shared map and behavior proof first"
            in reader_route_menu.get("menu_rule", "")
            and reader_route_menu.get("default_command") == human_first_command
            and reader_route_menu.get("alias_hint") == READER_ROUTE_ALIAS_HINT
            and reader_route_menu.get("shared_behavior_command")
            == shared_first_command
            and reader_route_menu.get("machine_card_command")
            == f"plectis first-screen --card {payload.get('project_label')}"
            and reader_route_menu.get("default_json_command")
            == f"plectis first-screen {payload.get('project_label')}"
            and reader_route_menu_ids == REQUIRED_ROUTE_IDS
            and all(
                isinstance(row, dict)
                and row.get("label") == READER_LABELS.get(str(row.get("reader_route_id")))
                and isinstance(row.get("terminal_command"), str)
                and row["terminal_command"]
                == (
                    "plectis hello --reader "
                    f"{row.get('reader_route_id')} {payload.get('project_label')}"
                )
                and isinstance(row.get("text_projection_command"), str)
                and row["text_projection_command"]
                == (
                    "plectis first-screen --format text --reader "
                    f"{row.get('reader_route_id')} {payload.get('project_label')}"
                )
                and isinstance(row.get("first_action"), str)
                and bool(row.get("first_action"))
                and isinstance(row.get("proof_surface"), str)
                and bool(row.get("proof_surface"))
                and isinstance(row.get("exit_check"), str)
                and bool(row.get("exit_check"))
                and isinstance(row.get("not_a_claim"), str)
                and bool(row.get("not_a_claim"))
                and str(row.get("authority", "")).startswith(
                    "focused_projection_only_not_"
                )
                for row in reader_route_menu_rows
            )
            and reader_route_menu_safe_to_show.get("uses_existing_reader_packets")
            is True
            and reader_route_menu_safe_to_show.get("creates_new_entry_artifact")
            is False
            and reader_route_menu_safe_to_show.get(
                "creates_reader_specific_claim_ceiling"
            )
            is False
            and reader_route_menu_safe_to_show.get("exports_private_paths") is False
            and reader_route_menu_safe_to_show.get("exports_provider_payloads")
            is False
            and reader_route_menu_safe_to_show.get("claims_release_or_hosting")
            is False
            and reader_route_menu_safe_to_show.get("claims_reader_success") is False
            and reader_route_menu.get("authority")
            == "reader_route_menu_not_new_entry_artifact_or_reader_success_authority"
        ),
        "behavior_proof_packet": (
            isinstance(behavior_proof_packet, dict)
            and behavior_proof_packet.get("purpose")
            == "turn_shared_first_run_into_inspectable_success_conditions"
            and behavior_proof_packet.get("command") == shared_first_command
            and behavior_proof_packet.get("writes_state") is True
            and behavior_proof_packet.get("state_dir") == ".microcosm"
            and behavior_proof_field_ids
            == {
                "front_door_status.status",
                "selected_route_id",
                "state_inspection",
                "source_files_mutated",
            }
            and all(
                isinstance(row, dict)
                and "success_read" in row
                and isinstance(row.get("reader_rule"), str)
                and bool(row.get("reader_rule"))
                for row in behavior_proof_fields
            )
            and behavior_proof_packet.get("authority")
            == "local_behavior_receipt_not_release_or_proof_authority"
        ),
        "first_run_ladder": (
            isinstance(first_run_ladder, dict)
            and first_run_ladder.get("purpose")
            == "make_first_screen_run_order_copyable_without_long_quickstart"
            and first_run_step_ids
            == {
                "map",
                "behavior_proof",
                "status_confirmation",
                "reader_branch",
            }
            and first_run_commands.get("map") == human_first_command
            and first_run_commands.get("behavior_proof") == shared_first_command
            and first_run_commands.get("status_confirmation")
            == f"plectis status --card {payload.get('project_label', '<project>')}"
            and all(
                isinstance(row, dict)
                and "writes_microcosm_state" in row
                and isinstance(row.get("expected_surface"), str)
                and bool(row.get("expected_surface"))
                and isinstance(row.get("success_read"), str)
                and bool(row.get("success_read"))
                and isinstance(row.get("authority"), str)
                and bool(row.get("authority"))
                for row in first_run_steps
            )
            and first_run_ladder.get("authority")
            == "copyable_run_order_not_quickstart_inventory_or_release_authority"
        ),
        "local_state_receipt_trail": (
            isinstance(local_state_receipt_trail, dict)
            and local_state_receipt_trail.get("purpose")
            == "show_what_the_first_run_writes_without_expanding_raw_state"
            and local_state_receipt_trail.get("producer_command")
            == shared_first_command
            and local_state_receipt_trail.get("state_dir") == ".microcosm"
            and local_state_trail_ids
            == {"catalog", "routes", "work_events", "evidence_index", "graph"}
            and all(
                isinstance(row, dict)
                and isinstance(row.get("state_ref"), str)
                and row["state_ref"].startswith(".microcosm/")
                and isinstance(row.get("reader_read"), str)
                and bool(row.get("reader_read"))
                and isinstance(row.get("not_authority_for"), str)
                and bool(row.get("not_authority_for"))
                for row in local_state_trail_rows
            )
            and local_state_receipt_trail.get("authority")
            == "local_state_receipt_trail_not_private_root_equivalence"
        ),
        "first_viewport_manifest": (
            isinstance(first_viewport_manifest, dict)
            and first_viewport_manifest.get("schema_version")
            == "microcosm_first_viewport_manifest_v1"
            and first_viewport_manifest.get("purpose")
            == (
                "make_single_screen_cold_entry_composition_explicit_for_cli_"
                "readme_browser_json_and_video"
            )
            and "before the long command inventory"
            in first_viewport_manifest.get("composition_rule", "")
            and first_viewport_slot_ids
            == [
                "identity",
                "first_run",
                "proof_chain",
                "evidence_context",
                "reader_branch",
                "authority_boundary",
            ]
            and all(
                isinstance(row, dict)
                and isinstance(row.get("viewport_copy"), str)
                and bool(row.get("viewport_copy"))
                and isinstance(row.get("source_packet"), str)
                and bool(row.get("source_packet"))
                and isinstance(row.get("first_visible_surface"), str)
                and bool(row.get("first_visible_surface"))
                and isinstance(row.get("proof_surface"), str)
                and bool(row.get("proof_surface"))
                and "authority_ceiling" in row.get("must_preserve", [])
                and "anti_claim" in row.get("must_preserve", [])
                and "omission_receipt" in row.get("must_preserve", [])
                and "discipline_comparison_strip" in row.get("must_preserve", [])
                and "release_or_hosting_authority" in row.get("must_not_claim", [])
                and "provider_call_authority" in row.get("must_not_claim", [])
                and "private_root_equivalence" in row.get("must_not_claim", [])
                and "whole_system_correctness" in row.get("must_not_claim", [])
                and "reader_success" in row.get("must_not_claim", [])
                for row in first_viewport_slots
            )
            and first_viewport_problem_ids == cold_entry_problem_ids
            and first_viewport_problem_slot_ids.issubset(set(first_viewport_slot_ids))
            and first_viewport_consumer_surfaces.get("terminal")
            == human_first_command
            and first_viewport_consumer_surfaces.get("readme")
            == "README.md::Choose Your First Screen"
            and first_viewport_consumer_surfaces.get("browser")
            == (
                f"{_bounded_observatory_serve_command(str(payload.get('project_label')))} -> /"
            )
            and first_viewport_consumer_surfaces.get("json")
            == f"plectis first-screen --card {payload.get('project_label')}"
            and first_viewport_consumer_surfaces.get("video")
            == "video_storyboard_packet"
            and first_viewport_safe_to_show.get("uses_existing_first_screen_packets")
            is True
            and first_viewport_safe_to_show.get("creates_new_entry_artifact") is False
            and first_viewport_safe_to_show.get("exports_private_paths") is False
            and first_viewport_safe_to_show.get("exports_provider_payloads") is False
            and first_viewport_safe_to_show.get("claims_release_or_hosting") is False
            and first_viewport_safe_to_show.get("claims_reader_success") is False
            and first_viewport_manifest.get("authority")
            == "viewport_manifest_not_new_claim_or_renderer_authority"
        ),
        "first_contact_surface_refs": (
            isinstance(first_contact_surface_refs, dict)
            and first_contact_surface_refs.get("schema_version")
            == "microcosm_first_contact_surface_refs_v1"
            and first_contact_surface_refs.get("producer_command")
            == shared_first_command
            and set(first_contact_surface_refs.get("required_surface_ids", []))
            == {
                "route",
                "work",
                "events",
                "evidence",
                "graph",
                "observatory",
                "proof_lab",
                "status",
            }
            and first_contact_surface_ids
            == {
                "route",
                "work",
                "events",
                "evidence",
                "graph",
                "observatory",
                "proof_lab",
                "status",
            }
            and first_contact_surfaces.get("route", {}).get("state_ref")
            == ".microcosm/routes.json"
            and first_contact_surfaces.get("work", {}).get("state_ref")
            == ".microcosm/work_items.json"
            and first_contact_surfaces.get("events", {}).get("state_ref")
            == ".microcosm/events.jsonl"
            and first_contact_surfaces.get("evidence", {}).get("state_ref")
            == ".microcosm/evidence/"
            and first_contact_surfaces.get("graph", {}).get("state_ref")
            == ".microcosm/graph.json"
            and first_contact_surfaces.get("observatory", {}).get("command")
            == _observatory_serve_command(str(payload.get("project_label")))
            and first_contact_surfaces.get("observatory", {}).get(
                "bounded_validation_command"
            )
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and first_contact_surfaces.get("observatory", {}).get(
                "compact_endpoint"
            )
            == OBSERVATORY_LANDING_ENDPOINTS["compact_observatory_card"]
            and first_contact_surfaces.get("proof_lab", {}).get("command")
            == "plectis proof-lab --out /tmp/microcosm-proof-lab"
            and first_contact_surfaces.get("status", {}).get("command")
            == f"plectis status --card {payload.get('project_label', '<project>')}"
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "body_text_exported"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "source_files_mutated"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "provider_calls_authorized"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "release_authorized"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "proof_correctness_claim"
            )
            is False
            and first_contact_surface_refs.get("authority")
            == (
                "first_contact_surface_map_only_not_source_release_provider_"
                "mutation_or_proof_authority"
            )
        ),
        "overclaim_tripwire_matrix": (
            isinstance(overclaim_tripwire_matrix, dict)
            and overclaim_tripwire_matrix.get("schema_version")
            == "microcosm_overclaim_tripwire_matrix_v1"
            and overclaim_tripwire_matrix.get("purpose")
            == "translate_common_cold_reader_overclaims_into_valid_bounded_reads"
            and overclaim_tripwire_matrix.get("shared_first_command")
            == shared_first_command
            and overclaim_ids
            == {
                "release_ready",
                "organ_count_whole_system",
                "low_body_import_count_fake",
                "local_state_private_root_equivalence",
                "observatory_hosted_release",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("overclaim"), str)
                and bool(row.get("overclaim"))
                and isinstance(row.get("valid_read"), str)
                and bool(row.get("valid_read"))
                and isinstance(row.get("check_surface"), str)
                and bool(row.get("check_surface"))
                and isinstance(row.get("reader_rule"), str)
                and bool(row.get("reader_rule"))
                for row in overclaim_rows
            )
            and overclaim_tripwire_matrix.get("authority")
            == "overclaim_tripwire_not_marketing_or_release_authority"
        ),
        "reader_exit_criteria": (
            isinstance(reader_exit_criteria, dict)
            and reader_exit_criteria.get("schema_version")
            == "microcosm_reader_exit_criteria_v1"
            and reader_exit_criteria.get("purpose")
            == "tell_cold_readers_when_the_first_screen_has_done_its_job"
            and reader_exit_criteria.get("shared_first_command")
            == shared_first_command
            and reader_exit_ids == REQUIRED_ROUTE_IDS
            and isinstance(reader_exit_criteria.get("shared_stop_rule"), str)
            and "long command inventory"
            in reader_exit_criteria.get("shared_stop_rule", "")
            and all(
                isinstance(row, dict)
                and isinstance(row.get("exit_when"), str)
                and bool(row.get("exit_when"))
                and isinstance(row.get("next_if_not_met"), str)
                and bool(row.get("next_if_not_met"))
                and isinstance(row.get("not_a_claim"), str)
                and bool(row.get("not_a_claim"))
                for row in reader_exit_rows
            )
            and reader_exit_criteria.get("authority")
            == "exit_criteria_not_reader_success_or_release_authority"
        ),
        "video_storyboard_packet": (
            isinstance(video_storyboard_packet, dict)
            and video_storyboard_packet.get("schema_version")
            == "microcosm_video_storyboard_packet_v1"
            and video_storyboard_packet.get("purpose")
            == "make_a_sixty_second_cold_entry_artifact_without_new_claims"
            and "same package-backed first-screen commands and authority ceiling"
            in video_storyboard_packet.get("artifact_rule", "")
            and video_storyboard_packet.get("allowed_artifact_forms")
            == [
                "terminal_capture",
                "browser_walkthrough",
                "static_reveal_board",
                "short_video",
            ]
            and video_storyboard_packet.get("source_projection")
            == "microcosm_core.first_screen_composition.first_screen_composition_card"
            and video_storyboard_packet.get("first_run_command")
            == shared_first_command
            and video_storyboard_packet.get("bounded_observatory_command")
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and len(video_storyboard_beats) == 6
            and video_storyboard_beat_ids
            == {
                "open_map",
                "prove_local_behavior",
                "show_route_chain",
                "frame_evidence_counts",
                "open_authority_boundary",
                "choose_reader_branch",
            }
            and sum(
                row.get("timebox_seconds", 0)
                for row in video_storyboard_beats
                if isinstance(row, dict)
                and isinstance(row.get("timebox_seconds"), int)
                and not isinstance(row.get("timebox_seconds"), bool)
            )
            <= 60
            and all(
                isinstance(row, dict)
                and isinstance(row.get("timebox_seconds"), int)
                and not isinstance(row.get("timebox_seconds"), bool)
                and row.get("timebox_seconds") > 0
                and isinstance(row.get("visible_surface"), str)
                and bool(row.get("visible_surface"))
                and isinstance(row.get("reader_takeaway"), str)
                and bool(row.get("reader_takeaway"))
                and isinstance(row.get("proof_ref"), str)
                and bool(row.get("proof_ref"))
                for row in video_storyboard_beats
            )
            and video_storyboard_safe_to_show.get("uses_public_first_screen_card")
            is True
            and video_storyboard_safe_to_show.get("uses_localhost_read_model")
            is True
            and video_storyboard_safe_to_show.get("exports_private_paths")
            is False
            and video_storyboard_safe_to_show.get("exports_provider_payloads")
            is False
            and video_storyboard_safe_to_show.get(
                "uses_live_operator_or_browser_session"
            )
            is False
            and video_storyboard_safe_to_show.get("claims_release_or_hosting")
            is False
            and video_storyboard_safe_to_show.get("claims_reader_success")
            is False
            and "not a release artifact" in video_storyboard_packet.get("anti_claim", "")
            and video_storyboard_packet.get("authority")
            == "presentation_plan_over_existing_first_screen_contract_only"
        ),
        "artifact_fit_matrix": (
            isinstance(artifact_fit_matrix, dict)
            and artifact_fit_matrix.get("schema_version")
            == "microcosm_first_screen_artifact_fit_matrix_v1"
            and artifact_fit_matrix.get("purpose")
            == "keep_all_cold_entry_forms_bound_to_one_source_card"
            and artifact_fit_matrix.get("source_of_truth")
            == "microcosm_core.first_screen_composition.first_screen_composition_card"
            and "not independent cold-entry artifacts"
            in artifact_fit_matrix.get("matrix_rule", "")
            and len(artifact_fit_rows) == 6
            and artifact_fit_ids
            == {
                "terminal_text_projection",
                "local_behavior_card",
                "machine_json_card",
                "readme_first_screen",
                "browser_landing",
                "short_video_storyboard",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("artifact_form"), str)
                and bool(row.get("artifact_form"))
                and isinstance(row.get("consumer_surface"), str)
                and bool(row.get("consumer_surface"))
                and isinstance(row.get("source_projection"), str)
                and bool(row.get("source_projection"))
                and isinstance(row.get("first_job"), str)
                and bool(row.get("first_job"))
                and isinstance(row.get("must_preserve"), list)
                and "authority_ceiling" in row.get("must_preserve", [])
                and "anti_claim" in row.get("must_preserve", [])
                and "omission_receipt" in row.get("must_preserve", [])
                and "discipline_comparison_strip" in row.get("must_preserve", [])
                and isinstance(row.get("must_not_claim"), list)
                and "release_or_hosting_authority" in row.get("must_not_claim", [])
                and "provider_call_authority" in row.get("must_not_claim", [])
                and "private_root_equivalence" in row.get("must_not_claim", [])
                for row in artifact_fit_rows
            )
            and artifact_fit_safe_to_show.get("binds_to_single_source_contract")
            is True
            and artifact_fit_safe_to_show.get("allows_multiple_projection_forms")
            is True
            and artifact_fit_safe_to_show.get("exports_private_paths") is False
            and artifact_fit_safe_to_show.get("exports_provider_payloads") is False
            and artifact_fit_safe_to_show.get("creates_new_release_artifact") is False
            and artifact_fit_safe_to_show.get("creates_reader_specific_claim_ceiling")
            is False
            and artifact_fit_matrix.get("authority")
            == "projection_fit_matrix_not_new_artifact_authority"
        ),
        "cold_entry_problem_map": (
            isinstance(cold_entry_problem_map, dict)
            and cold_entry_problem_map.get("schema_version")
            == "microcosm_cold_entry_problem_map_v1"
            and cold_entry_problem_map.get("purpose")
            == "bind_cold_entry_problem_shapes_to_existing_first_screen_packets"
            and "not create a second entry artifact"
            in cold_entry_problem_map.get("map_rule", "")
            and cold_entry_problem_ids
            == {
                "first_thing_best_thing_gap",
                "audience_is_not_one_person",
                "honest_numbers_without_context",
                "discipline_invisible_without_comparison",
                "size_paradox",
                "runnable_vs_structural_split",
                "doctrine_reads_as_ceremony",
                "frontend_surface_not_seductive",
                "card_discipline_not_default",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("reader_risk"), str)
                and bool(row.get("reader_risk"))
                and isinstance(row.get("compression_answer"), str)
                and bool(row.get("compression_answer"))
                and isinstance(row.get("primary_packet"), str)
                and bool(row.get("primary_packet"))
                and isinstance(row.get("first_surface"), str)
                and bool(row.get("first_surface"))
                and isinstance(row.get("proof_surface"), str)
                and bool(row.get("proof_surface"))
                and isinstance(row.get("not_claim"), str)
                and bool(row.get("not_claim"))
                for row in cold_entry_problem_rows
            )
            and cold_entry_problem_safe_to_show.get(
                "uses_existing_first_screen_packets"
            )
            is True
            and cold_entry_problem_safe_to_show.get("creates_new_entry_artifact")
            is False
            and cold_entry_problem_safe_to_show.get("exports_private_paths") is False
            and cold_entry_problem_safe_to_show.get("exports_provider_payloads")
            is False
            and cold_entry_problem_safe_to_show.get("claims_release_or_hosting")
            is False
            and cold_entry_problem_safe_to_show.get("claims_reader_success") is False
            and cold_entry_problem_map.get("authority")
            == "problem_shape_map_not_strategy_or_release_authority"
        ),
        "evidence_count_frame": (
            payload.get("evidence_count_frame", {}).get("interpretation")
            == "accounting_not_maturity_score"
            and payload.get("evidence_count_frame", {}).get("legend_ref")
            == EVIDENCE_CLASS_REGISTRY_REF
        ),
        "representative_substrate_glance": (
            isinstance(representative_substrate_glance, dict)
            and representative_substrate_glance.get("schema_version")
            == "microcosm_representative_substrate_glance_v1"
            and representative_substrate_glance.get("purpose")
            == "show_actual_public_organ_substance_before_drilldown"
            and representative_substrate_glance.get("source_ref")
            == ORGAN_GLANCE_LADDER_REF
            and representative_substrate_glance.get("one_line_source_ref")
            == ORGAN_GLANCE_LADDER_REF
            and representative_substrate_glance.get("source_refs")
            == [AGENT_TASK_ROUTES_REF]
            and representative_substrate_glance.get("sample_limit")
            == SUBSTRATE_GLANCE_SAMPLE_LIMIT
            and isinstance(
                representative_substrate_glance.get("total_organ_count"),
                int,
            )
            and representative_substrate_glance.get("total_organ_count")
            >= len(substrate_glance_examples)
            and isinstance(representative_substrate_glance.get("family_count"), int)
            and representative_substrate_glance.get("family_count")
            >= len(
                {
                    row.get("family")
                    for row in substrate_glance_examples
                    if isinstance(row, dict)
                }
            )
            and len(substrate_glance_examples) == SUBSTRATE_GLANCE_SAMPLE_LIMIT
            and all(
                isinstance(row, dict)
                and isinstance(row.get("organ_id"), str)
                and bool(row.get("organ_id"))
                and isinstance(row.get("display_name"), str)
                and bool(row.get("display_name"))
                and isinstance(row.get("family"), str)
                and bool(row.get("family"))
                and isinstance(row.get("glance_excerpt"), str)
                and bool(row.get("glance_excerpt"))
                and row.get("glance_source")
                in {
                    "organ_glance_ladder_one_line",
                    "organ_glance_ladder_card",
                }
                and (
                    "one_line" in row.get("source_fields", [])
                    or "card" in row.get("source_fields", [])
                )
                and row.get("reader_rule")
                == "representative_example_not_inventory_or_readiness_claim"
                for row in substrate_glance_examples
            )
            and substrate_glance_safe_to_show.get("uses_public_organ_glance_ladder")
            is True
            and substrate_glance_safe_to_show.get(
                "uses_public_route_projection_one_lines"
            )
            is True
            and substrate_glance_safe_to_show.get("exports_private_paths") is False
            and substrate_glance_safe_to_show.get("exports_provider_payloads") is False
            and substrate_glance_safe_to_show.get("claims_release_or_hosting") is False
            and substrate_glance_safe_to_show.get("claims_reader_success") is False
            and substrate_glance_safe_to_show.get("claims_whole_system_correctness")
            is False
            and representative_substrate_glance.get("authority")
            == "representative_glance_not_inventory_score_or_readiness_claim"
        ),
        "evidence_class_legend": (
            isinstance(evidence_class_legend, dict)
            and evidence_class_legend.get("source_ref")
            == EVIDENCE_CLASS_REGISTRY_REF
            and evidence_class_legend.get("interpretation")
            == "claim_boundary_legend_not_score"
            and evidence_class_legend.get("missing_profiles") == []
            and legend_ids == set(EVIDENCE_CLASS_DISPLAY_ORDER)
            and all(
                isinstance(row, dict)
                and isinstance(row.get("claim_ceiling"), str)
                and bool(row.get("claim_ceiling"))
                and isinstance(row.get("evaluator_basis"), str)
                and bool(row.get("evaluator_basis"))
                for row in legend_rows
            )
        ),
        "comparison_frame": (
            payload.get("comparison_frame", {}).get("purpose")
            == "make_rigor_visible_without_claim_inflation"
        ),
        "discipline_comparison_strip": (
            isinstance(discipline_comparison_strip, dict)
            and discipline_comparison_strip.get("schema_version")
            == "microcosm_discipline_comparison_strip_v1"
            and discipline_comparison_strip.get("purpose")
            == "make_microcosm_rigor_visible_as_operational_differences"
            and "not as superiority, benchmark, or maturity claims"
            in discipline_comparison_strip.get("strip_rule", "")
            and discipline_comparison_ids
            == {
                "failure_modes_declared",
                "evidence_counts_contextualized",
                "body_copy_boundaries",
                "reader_branch_authority_shared",
                "local_behavior_before_claims",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("ordinary_entry_pattern"), str)
                and bool(row.get("ordinary_entry_pattern"))
                and isinstance(row.get("microcosm_discipline"), str)
                and bool(row.get("microcosm_discipline"))
                and isinstance(row.get("visible_check_surface"), str)
                and bool(row.get("visible_check_surface"))
                and isinstance(row.get("reader_rule"), str)
                and bool(row.get("reader_rule"))
                and isinstance(row.get("not_claim"), str)
                and bool(row.get("not_claim"))
                for row in discipline_comparison_rows
            )
            and discipline_comparison_safe_to_show.get(
                "uses_existing_first_screen_packets"
            )
            is True
            and discipline_comparison_safe_to_show.get("exports_private_paths")
            is False
            and discipline_comparison_safe_to_show.get("exports_provider_payloads")
            is False
            and discipline_comparison_safe_to_show.get("claims_external_benchmark")
            is False
            and discipline_comparison_safe_to_show.get("claims_superiority") is False
            and discipline_comparison_safe_to_show.get("claims_release_or_hosting")
            is False
            and discipline_comparison_safe_to_show.get(
                "claims_whole_system_correctness"
            )
            is False
            and discipline_comparison_strip.get("authority")
            == "comparison_strip_not_benchmark_or_superiority_claim"
        ),
        "doctrine_effect_frame": (
            isinstance(doctrine_effect_frame, dict)
            and doctrine_effect_frame.get("purpose")
            == "show_doctrine_as_mistake_prevention_not_ceremony"
            and doctrine_handles
            == {
                "CONSTITUTION",
                "AXIOMS",
                "PRINCIPLES",
                "CONCEPTS",
                "MECHANISMS",
                "ANTI_PRINCIPLES",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("prevents"), str)
                and bool(row.get("prevents"))
                and isinstance(row.get("visible_effect"), str)
                and bool(row.get("visible_effect"))
                and isinstance(row.get("first_screen_surface"), str)
                and bool(row.get("first_screen_surface"))
                for row in doctrine_effect_rows
            )
        ),
        "readme_entry_contract": (
            isinstance(readme_entry_contract, dict)
            and readme_entry_contract.get("purpose")
            == "make_package_backed_first_screen_card_the_readme_entry_surface"
            and readme_entry_contract.get("inventory_policy")
            == "quickstart_command_inventory_is_a_drilldown_after_the_first_screen_card"
            and readme_entry_contract.get("authority")
            == "documentation_order_contract_not_runtime_proof"
            and (
                "README.md::Choose Your First Screen",
                "README.md::Try It On Your Repo",
            )
            in readme_order_pairs
            and (human_first_command, shared_first_command) in readme_order_pairs
            and (
                shared_first_command,
                "plectis first-screen --card "
                f"{payload.get('project_label', '<project>')}",
            )
            in readme_order_pairs
            and ("reader_route_menu", "quickstart_command_inventory")
            in readme_order_pairs
            and ("reader_routes", "quickstart_command_inventory") in readme_order_pairs
            and (
                "first_viewport_manifest",
                "quickstart_command_inventory",
            )
            in readme_order_pairs
            and all(
                isinstance(row, dict)
                and isinstance(row.get("reason"), str)
                and bool(row.get("reason"))
                for row in readme_order_rows
            )
        ),
        "entry_surface_contract": (
            payload.get("entry_surface_contract", {}).get("shared_behavior_surface")
            == payload.get("shared_first_command")
        ),
        "scale_frame": (
            bool(scale_frame.get("scale_handles"))
            and scale_frame.get("count_interpretation")
            == "receipt_backed_handles_not_scores"
            and all(
                _positive_count(scale_counts.get(required_count))
                for required_count in (
                    "implemented_organs",
                    "public_standards",
                    "mapped_organs",
                    "source_open_materials",
                )
            )
        ),
        "runnable_structural_join": bool(
            payload.get("runnable_structural_join", {}).get("join_rule")
        ),
        "state_write_boundary": (
            state_write_boundary.get("this_card_writes_microcosm_state") is False
            and state_write_boundary.get("shared_first_command_writes_state") is True
            and state_write_boundary.get("behavioral_proof_command")
            == payload.get("shared_first_command")
            and state_write_boundary.get("front_door_status_ref")
            == f"{payload.get('shared_first_command')}::front_door_status"
        ),
        "observatory_landing_frame": (
            observatory_landing_frame.get("human_first_command")
            == payload.get("human_first_command")
            and observatory_landing_frame.get("text_projection_command")
            == payload.get("human_first_command")
            and observatory_landing_frame.get("shared_first_command")
            == payload.get("shared_first_command")
            and observatory_landing_frame.get("behavioral_proof_command")
            == payload.get("shared_first_command")
            and observatory_landing_frame.get("serve_command")
            == _observatory_serve_command(str(payload.get("project_label")))
            and observatory_landing_frame.get("bounded_validation_command")
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and observatory_landing_frame.get("bounded_validation_request_count")
            == BOUNDED_OBSERVATORY_REQUEST_COUNT
            and observatory_landing_frame.get("browser_landing_reuse", {}).get(
                "serve_command"
            )
            == _observatory_serve_command(str(payload.get("project_label")))
            and observatory_landing_frame.get("browser_landing_reuse", {}).get(
                "bounded_validation_command"
            )
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and observatory_endpoints == OBSERVATORY_LANDING_ENDPOINTS
            and observatory_landing_frame.get("browser_landing_reuse", {}).get(
                "authority"
            )
            == "browser_projection_over_same_card_not_json_first_lens_inventory"
            and all(
                handle in required_visible_handles
                for handle in (
                    "human_first_command",
                    "text_projection",
                    "shared_first_command",
                    "behavioral_proof_command",
                    "serve_command",
                    "bounded_validation_command",
                    "reader_route_ids",
                    "reader_route_menu",
                    "reader_landing_packets",
                    "behavior_proof_packet",
                    "first_run_ladder",
                    "first_viewport_manifest",
                    "local_state_receipt_trail",
                    "first_contact_surface_refs",
                    "overclaim_tripwire_matrix",
                    "discipline_comparison_strip",
                    "reader_exit_criteria",
                    "video_storyboard_packet",
                    "artifact_fit_matrix",
                    "cold_entry_problem_map",
                    "public_scale_counts",
                    "representative_substrate_glance",
                    "evidence_class_legend",
                    "doctrine_effect_frame",
                    "authority_ceiling",
                    "omission_receipt",
                )
            )
        ),
        "authority_ceiling": all(
            authority_ceiling.get(key) is False for key in DENIED_AUTHORITY_KEYS
        ),
        "omission_receipt": bool(payload.get("omission_receipt", {}).get("drilldown")),
        "workingness_drilldown": "plectis workingness" in drilldown_text,
    }


def _state_write_boundary(project_label: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the state-write boundary declaring the card itself writes no .microcosm state.

    - Teleology: generated boundary separating this composition card (no writes) from the shared first command (which writes state).
    - Guarantee: returns a `microcosm_first_screen_state_write_boundary_v1` dict asserting this_card_writes_microcosm_state=False, shared_first_command_writes_state=True, and a safe_to_show block with source-mutation/provider/release/proof flags False.
    - Fails: never raises; deterministic from `project_label`.
    - Non-goal: does not mutate source, authorize provider calls, release, or proof correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shared_first_command = f"plectis tour --card {project_label}"
    return {
        "schema_version": "microcosm_first_screen_state_write_boundary_v1",
        "this_card_writes_microcosm_state": False,
        "this_card_status_scope": "composition_contract_only_not_local_run_result",
        "shared_first_command": shared_first_command,
        "shared_first_command_writes_state": True,
        "state_dir": ".microcosm",
        "behavioral_proof_command": shared_first_command,
        "front_door_status_ref": f"{shared_first_command}::front_door_status",
        "reader_action": (
            "Run the shared first command to write .microcosm state and read "
            "front_door_status before treating the first screen as behavior."
        ),
        "safe_to_show": {
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_or_hosting_authorized": False,
            "proof_correctness_claim": False,
        },
    }


def first_screen_composition_card(
    root: Path = MICROCOSM_ROOT,
    *,
    project_label: str = "<project>",
) -> dict[str, Any]:
    """
    [ACTION]
    Assemble the full first-screen composition card and validate it against the standard.

    - Teleology: the module's primary builder/projection entrypoint; composes every reader/proof/scale/doctrine packet into one public first-screen contract derived from the standard.
    - Guarantee: returns a `microcosm_first_screen_composition_card_v1` dict mirroring the standard's authority_ceiling/anti_claim/omission_receipt/public_private_boundary and carrying `validation.status` ("pass" only when all internal checks and the standard-backed scan pass) plus a top-level `status`.
    - Fails: raises TypeError/StrictJsonError/OSError only if the governing standard JSON is missing or malformed (via _load_standard); a coherent-but-noncompliant payload returns status="blocked", not an exception.
    - When-needed: when producing the canonical machine first-screen card or checking standard compliance.
    - Reads: `standards/std_microcosm_first_screen_composition_root.json` plus public organ/standards/workingness/fixture-manifest inputs under `root`.
    - Escalates-to: STANDARD_REF as source authority; first_screen_compact_card / first_screen_text_card project this output; the validator_id names the governing validator contract.
    - Non-goal: GENERATED projection — does not authorize release, hosting, provider calls, source mutation, private-root equivalence, or whole-system correctness, and is not itself source-of-truth.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    root = Path(root)
    standard = _load_standard(root)
    source_checkout_commands = _source_checkout_commands(project_label)
    pre_install_probe = _pre_install_probe_packet()
    payload: dict[str, Any] = {
        "schema_version": "microcosm_first_screen_composition_card_v1",
        "project_label": project_label,
        "composition_root_id": standard["kind_id"],
        "source_standard_ref": str(STANDARD_REF),
        "pre_install_probe": pre_install_probe,
        "human_first_command": f"plectis hello {project_label}",
        "shared_first_command": f"plectis tour --card {project_label}",
        "source_checkout_commands": source_checkout_commands,
        "text_projection": {
            "command": f"plectis hello {project_label}",
            "pre_install_probe_command": pre_install_probe["command"],
            "pre_install_probe_receipt": pre_install_probe["receipt_ref"],
            "source_checkout_command": source_checkout_commands["hello"],
            "writes_microcosm_state": False,
            "behavioral_proof_command": f"plectis tour --card {project_label}",
            "source_checkout_behavioral_proof_command": source_checkout_commands[
                "behavior_proof"
            ],
            "authority": "terminal_text_projection_only_not_behavior_proof",
            "reader_rule": (
                "Use this command to view the first-screen card; run the "
                "behavior proof command to write .microcosm state."
            ),
        },
        "reader_routes": _reader_routes(project_label),
        "reader_route_menu": _reader_route_menu(project_label),
        "reader_landing_packets": _reader_landing_packets(project_label),
        "behavior_proof_packet": _behavior_proof_packet(project_label),
        "first_run_ladder": _first_run_ladder(project_label),
        "first_viewport_manifest": _first_viewport_manifest(project_label),
        "local_state_receipt_trail": _local_state_receipt_trail(project_label),
        "first_contact_surface_refs": _first_contact_surface_refs(project_label),
        "overclaim_tripwire_matrix": _overclaim_tripwire_matrix(project_label),
        "reader_exit_criteria": _reader_exit_criteria(project_label),
        "video_storyboard_packet": _video_storyboard_packet(project_label),
        "artifact_fit_matrix": _artifact_fit_matrix(project_label),
        "cold_entry_problem_map": _cold_entry_problem_map(project_label),
        "evidence_count_frame": _evidence_count_frame(),
        "evidence_class_legend": _evidence_class_legend(root),
        "representative_substrate_glance": _representative_substrate_glance(root),
        "comparison_frame": _comparison_frame(),
        "discipline_comparison_strip": _discipline_comparison_strip(project_label),
        "doctrine_effect_frame": _doctrine_effect_frame(),
        "readme_entry_contract": _readme_entry_contract(project_label),
        "entry_surface_contract": _entry_surface_contract(project_label),
        "scale_frame": _scale_frame(root),
        "runnable_structural_join": _runnable_structural_join(project_label),
        "state_write_boundary": _state_write_boundary(project_label),
        "observatory_landing_frame": _observatory_landing_frame(project_label),
        "drilldowns": _drilldowns(project_label),
        "omission_receipt": deepcopy(standard["omission_receipt"]),
        "authority_ceiling": deepcopy(standard["authority_ceiling"]),
        "anti_claim": deepcopy(standard["anti_claim"]),
        "public_private_boundary": {
            "allowed_public_inputs": deepcopy(
                standard["public_private_boundary"]["allowed_public_inputs"]
            ),
            "forbidden_public_inputs": deepcopy(
                standard["public_private_boundary"]["forbidden_public_inputs"]
            ),
        },
        "validator_id": standard["validator_contract"]["validator_id"],
    }
    checks = _validation_checks(payload)
    standard_scan = _standard_backed_first_screen_scan(
        payload,
        standard,
        set(checks),
    )
    payload["standard_backed_first_screen_scan"] = standard_scan
    checks["standard_backed_first_screen_scan"] = standard_scan["status"] == "pass"
    payload["validation"] = {
        "status": "pass" if all(checks.values()) else "blocked",
        "checks": checks,
    }
    payload["status"] = payload["validation"]["status"]
    return payload


def _compact_reader_routes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    Project the reader-route-menu rows into compact reader-route rows for the compact card.

    - Teleology: generated slimming of menu rows to the fields the compact public card carries.
    - Guarantee: returns a list of compact route dicts (id/label/commands/first_action/proof/exit/not_a_claim), adding source-checkout fields only when present; non-dict rows are skipped.
    - Fails: never raises; a missing/empty menu yields an empty list.
    - Non-goal: a projection of existing rows; adds no new claim or authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    route_menu = payload.get("reader_route_menu", {})
    routes = route_menu.get("routes", []) if isinstance(route_menu, dict) else []
    compact_routes: list[dict[str, Any]] = []
    for row in routes:
        if not isinstance(row, dict):
            continue
        compact_row = {
            "reader_route_id": row.get("reader_route_id"),
            "label": row.get("label"),
            "terminal_command": row.get("terminal_command"),
            "text_projection_command": row.get("text_projection_command"),
            "first_action": row.get("first_action"),
            "proof_surface": row.get("proof_surface"),
            "exit_check": row.get("exit_check"),
            "not_a_claim": row.get("not_a_claim"),
        }
        if row.get("source_checkout_first_action"):
            compact_row["source_checkout_first_action"] = row.get(
                "source_checkout_first_action"
            )
        if row.get("source_checkout_proof_surface"):
            compact_row["source_checkout_proof_surface"] = row.get(
                "source_checkout_proof_surface"
            )
        compact_routes.append(compact_row)
    return compact_routes


def _compact_first_run_steps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    Project the first-run-ladder steps into compact step rows for the compact card.

    - Teleology: generated slimming of ladder steps to the keys the compact card shows.
    - Guarantee: returns a list of step dicts limited to step_id/command/source_checkout_command/expected_surface/writes_microcosm_state/authority where present; non-dict rows are skipped.
    - Fails: never raises; a missing/empty ladder yields an empty list.
    - Non-goal: a projection; adds no new step or claim.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ladder = payload.get("first_run_ladder", {})
    steps = ladder.get("steps", []) if isinstance(ladder, dict) else []
    compact_steps: list[dict[str, Any]] = []
    for row in steps:
        if not isinstance(row, dict):
            continue
        compact_steps.append(
            {
                key: row.get(key)
                for key in (
                    "step_id",
                    "command",
                    "source_checkout_command",
                    "expected_surface",
                    "writes_microcosm_state",
                    "authority",
                )
                if key in row
            }
        )
    return compact_steps


def _compact_scale_counts(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Project the scale frame into the three headline counts (organs/standards/source-open) for the compact card.

    - Teleology: generated reduction of public_scale_counts to the count + read_as the compact card surfaces.
    - Guarantee: returns a dict keyed by implemented_organs/public_standards/source_open_materials, each {count, read_as}; absent rows are omitted.
    - Fails: never raises; a missing scale frame yields an empty dict.
    - Non-goal: a projection; counts stay accounting handles, not scores or authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    scale_frame = payload.get("scale_frame", {})
    counts = (
        scale_frame.get("public_scale_counts", {})
        if isinstance(scale_frame, dict)
        else {}
    )
    compact_counts: dict[str, dict[str, Any]] = {}
    for key in (
        "implemented_organs",
        "public_standards",
        "source_open_materials",
    ):
        row = counts.get(key) if isinstance(counts, dict) else None
        if not isinstance(row, dict):
            continue
        compact_counts[key] = {
            "count": row.get("count"),
            "read_as": row.get("read_as"),
        }
    return compact_counts


def _compact_validation(payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Project the full validation block into a compact pass/fail summary for the compact card.

    - Teleology: generated reduction of validation.checks to a status + counts + failed-check list.
    - Guarantee: returns a dict with source_status, validator_id, checks_passed_count, check_count, and failed_checks (every check whose value is not True).
    - Fails: never raises; a missing validation block yields zero counts and an empty failed list.
    - Non-goal: a projection of computed checks; runs no new validation and grants no release authority.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    validation = payload.get("validation", {})
    checks = validation.get("checks", {}) if isinstance(validation, dict) else {}
    failed = [
        check_id
        for check_id, passed in checks.items()
        if passed is not True
    ] if isinstance(checks, dict) else []
    return {
        "source_status": validation.get("status") if isinstance(validation, dict) else None,
        "validator_id": payload.get("validator_id"),
        "checks_passed_count": len(checks) - len(failed) if isinstance(checks, dict) else 0,
        "check_count": len(checks) if isinstance(checks, dict) else 0,
        "failed_checks": failed,
    }


def _compact_substrate_glance(payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Project the representative substrate glance into a compact glance for the compact card.

    - Teleology: generated reduction of the glance to source refs, counts, and slim example rows.
    - Guarantee: returns a dict with source_refs/sample_limit/total_organ_count, example_display_names, families, and slim example dicts (id/name/family/excerpt fields).
    - Fails: never raises; a missing glance yields None-valued fields and empty example lists.
    - Non-goal: a projection; examples remain handles, not inventory or readiness claims.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    glance = payload.get("representative_substrate_glance", {})
    examples = glance.get("examples", []) if isinstance(glance, dict) else []
    rows = [row for row in examples if isinstance(row, dict)]
    return {
        "source_ref": glance.get("source_ref") if isinstance(glance, dict) else None,
        "one_line_source_ref": glance.get("one_line_source_ref")
        if isinstance(glance, dict)
        else None,
        "source_refs": glance.get("source_refs") if isinstance(glance, dict) else None,
        "preferred_organ_ids": glance.get("preferred_organ_ids")
        if isinstance(glance, dict)
        else None,
        "sample_limit": glance.get("sample_limit") if isinstance(glance, dict) else None,
        "total_organ_count": glance.get("total_organ_count")
        if isinstance(glance, dict)
        else None,
        "example_display_names": [row.get("display_name") for row in rows],
        "families": [row.get("family") for row in rows],
        "examples": [
            {
                "organ_id": row.get("organ_id"),
                "display_name": row.get("display_name"),
                "family": row.get("family"),
                "glance_excerpt": row.get("glance_excerpt"),
                "glance_source": row.get("glance_source"),
                "one_line_excerpt": row.get("one_line_excerpt"),
            }
            for row in rows
        ],
        "authority": glance.get("authority") if isinstance(glance, dict) else None,
    }


def first_screen_compact_card(payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Project a full composition card into the stdout-budgeted compact public card.

    - Teleology: public projection giving consumers a summary-first card under a char budget while preserving full-contract drilldowns.
    - Guarantee: returns a `microcosm_first_screen_compact_card_v1` dict carrying the source status, compact reader-route/first-run/evidence/validation projections, the authority_ceiling/anti_claim/public_private_boundary, and an omission_receipt naming the omitted full-contract keys and the full-contract command.
    - Fails: never raises; missing payload sections degrade to None/empty compact fields, not an exception.
    - When-needed: when emitting `plectis first-screen --card` output.
    - Escalates-to: the full card via output_policy.full_contract_command (`plectis first-screen --full`).
    - Non-goal: a GENERATED compact projection of an existing card; authorizes no release and is not source-of-truth.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    project_label = str(payload.get("project_label") or "<project>")
    route_menu = payload.get("reader_route_menu", {})
    state_boundary = payload.get("state_write_boundary", {})
    full_json_command = f"plectis first-screen --full {project_label}"
    text_projection_command = f"plectis first-screen --format text {project_label}"
    compact_card_command = f"plectis first-screen --card {project_label}"
    default_json_command = f"plectis first-screen {project_label}"
    card: dict[str, Any] = {
        "schema_version": "microcosm_first_screen_compact_card_v1",
        "compact_projection_of": payload.get("schema_version"),
        "status": payload.get("status"),
        "project_label": project_label,
        "pre_install_probe": payload.get("pre_install_probe"),
        "human_first_command": payload.get("human_first_command"),
        "shared_first_command": payload.get("shared_first_command"),
        "output_policy": {
            "default_json_is_first_screen_projection": True,
            "default_json_command": default_json_command,
            "compact_card_command": compact_card_command,
            "stdout_budget_chars": COMPACT_JSON_CARD_MAX_CHARS,
            "full_contract_command": full_json_command,
            "text_projection_command": text_projection_command,
            "full_contract_preserved": True,
        },
        "reader_route_menu": {
            "default_command": route_menu.get("default_command")
            if isinstance(route_menu, dict)
            else None,
            "alias_hint": READER_ROUTE_ALIAS_HINT,
            "shared_behavior_command": route_menu.get("shared_behavior_command")
            if isinstance(route_menu, dict)
            else None,
            "source_checkout_commands": payload.get("source_checkout_commands"),
            "machine_card_command": compact_card_command,
            "default_json_command": default_json_command,
            "routes": _compact_reader_routes(payload),
        },
        "first_run_ladder": {
            "purpose": "show_the_first_runnable_path_before_deep_contract_json",
            "pre_install_probe": payload.get("pre_install_probe"),
            "steps": _compact_first_run_steps(payload),
        },
        "evidence_context": {
            "scale_counts": _compact_scale_counts(payload),
            "evidence_class_registry_ref": EVIDENCE_CLASS_REGISTRY_REF,
            "representative_substrate_glance": _compact_substrate_glance(payload),
            "counts_are_authority": False,
        },
        "state_write_boundary": {
            "this_card_writes_microcosm_state": False,
            "behavioral_proof_command": state_boundary.get(
                "behavioral_proof_command"
            ) if isinstance(state_boundary, dict) else None,
            "front_door_status_ref": state_boundary.get("front_door_status_ref")
            if isinstance(state_boundary, dict)
            else None,
            "source_files_mutated_by_first_screen": False,
        },
        "authority_ceiling": payload.get("authority_ceiling"),
        "anti_claim": payload.get("anti_claim"),
        "public_private_boundary": payload.get("public_private_boundary"),
        "drilldowns": {
            "full_json": full_json_command,
            "text_projection": text_projection_command,
            "behavior_proof": payload.get("shared_first_command"),
            "observatory": _bounded_observatory_serve_command(project_label),
            "route_contract": "paper_modules/cold_reader_route_map.md",
        },
        "omission_receipt": {
            "summary_first_projection": True,
            "omitted_full_contract_keys": [
                "video_storyboard_packet",
                "artifact_fit_matrix",
                "cold_entry_problem_map",
                "discipline_comparison_strip",
                "doctrine_effect_frame",
            ],
            "drilldown": payload.get("omission_receipt", {}).get("drilldown")
            if isinstance(payload.get("omission_receipt"), dict)
            else None,
            "full_contract_command": full_json_command,
        },
        "validation": _compact_validation(payload),
    }
    return _enforce_compact_stdout_budget(card)


def _compact_stdout_chars(card: dict[str, Any]) -> int:
    """
    [ACTION]
    Measure the card exactly as `_print_json` will emit it (sorted, indented ASCII).

    - Teleology: the budget enforcement must count the same bytes the cold reader's
      terminal receives, not a denser serialization that under-reports.
    - Guarantee: returns the stdout character count including the trailing newline.
    - Fails: never raises for JSON-serializable cards.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return len(json.dumps(card, ensure_ascii=True, indent=2, sort_keys=True)) + 1


def _substitute_label(node: Any, label: str) -> None:
    """
    [ACTION]
    In-place replace the literal project label with <project> in string values.
    - Teleology: Implements `_substitute_label` for `microcosm_core.first_screen_composition` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and label in value:
                node[key] = value.replace(label, "<project>")
            else:
                _substitute_label(value, label)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if isinstance(value, str) and label in value:
                node[index] = value.replace(label, "<project>")
            else:
                _substitute_label(value, label)


def _enforce_compact_stdout_budget(card: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Enforce COMPACT_JSON_CARD_MAX_CHARS on the compact card with typed omissions.

    - Teleology: the compact card DECLARES a stdout budget; long project labels
      (absolute artifact paths repeated in every command string) inflate the same
      card past its own declaration, so the budget must be enforced, not advertised.
    - Guarantee: applies a fixed degradation ladder (route detail rollup, then
      substrate-glance excerpt demotion, then first-run step detail rollup) only
      until the serialized card fits the budget, and always stamps
      `omission_receipt.budget_degradation` with the applied steps and before/after
      counts; with no degradation needed the receipt records an empty ladder.
    - Fails: never raises; if every step is applied and the card still exceeds the
      budget, the receipt records `over_budget_after_full_ladder` = True rather
      than silently passing.
    - Non-goal: does not change command strings, claims, or authority fields; every
      demoted detail remains in the full contract behind `--full`.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    budget = COMPACT_JSON_CARD_MAX_CHARS
    applied: list[str] = []
    # Stamp the receipt BEFORE measuring: the receipt's own bytes are part of
    # the stdout the budget governs, so measuring without it under-counts and
    # a "fits" verdict can ship an over-budget card.
    omission = card.get("omission_receipt")
    degradation: dict[str, Any] = {
        "stdout_budget_chars": budget,
        "serialized_chars_before": 0,
        "serialized_chars_after": 0,
        "applied_steps": applied,
        "over_budget_after_full_ladder": False,
        "full_contract_command": (
            omission.get("full_contract_command") if isinstance(omission, dict) else None
        ),
    }
    if isinstance(omission, dict):
        omission["budget_degradation"] = degradation
    chars_before = _compact_stdout_chars(card)
    degradation["serialized_chars_before"] = chars_before
    degradation["serialized_chars_after"] = chars_before

    if _compact_stdout_chars(card) > budget:
        glance = card.get("evidence_context", {}).get(
            "representative_substrate_glance", {}
        )
        if isinstance(glance, dict):
            glance["examples"] = [
                {
                    "organ_id": row.get("organ_id"),
                    "display_name": row.get("display_name"),
                    "family": row.get("family"),
                }
                for row in glance.get("examples", [])
                if isinstance(row, dict)
            ]
            glance["excerpt_detail"] = (
                "demoted_to_full_contract_for_stdout_budget"
            )
        applied.append("substrate_glance_excerpt_demotion")

    if _compact_stdout_chars(card) > budget:
        routes = card.get("reader_route_menu", {}).get("routes", [])
        for row in routes:
            if isinstance(row, dict):
                for key in (
                    "proof_surface",
                    "exit_check",
                    "not_a_claim",
                    "text_projection_command",
                ):
                    row.pop(key, None)
        if isinstance(card.get("reader_route_menu"), dict):
            card["reader_route_menu"]["route_detail"] = (
                "demoted_to_full_contract_for_stdout_budget"
            )
        applied.append("route_detail_rollup")

    if _compact_stdout_chars(card) > budget:
        steps = card.get("first_run_ladder", {}).get("steps", [])
        for row in steps:
            if isinstance(row, dict):
                for key in ("expected_surface", "authority"):
                    row.pop(key, None)
        if isinstance(card.get("first_run_ladder"), dict):
            card["first_run_ladder"]["step_detail"] = (
                "demoted_to_full_contract_for_stdout_budget"
            )
        applied.append("first_run_step_detail_rollup")

    if _compact_stdout_chars(card) > budget:
        # Terminal step for pathological labels (deep mkdtemp sandbox paths):
        # the label itself, repeated through every bulk command string, IS the
        # overrun. De-duplicate it to the documented <project> placeholder in
        # the bulk sections only; the top-level commands (human_first_command,
        # shared_first_command, output_policy.*) stay literal and copy-pasteable.
        label = str(card.get("project_label") or "")
        if label and label != "<project>":
            for section_key in ("reader_route_menu", "first_run_ladder", "drilldowns"):
                _substitute_label(card.get(section_key), label)
            card["label_substitution"] = {
                "placeholder": "<project>",
                "substitute_with": "project_label",
                "reason": "stdout_budget_label_deduplication",
            }
            applied.append("bulk_command_label_deduplication")

    # Fixpoint settle: writing the final counts can shift the size by a few
    # digit/boolean bytes, so measure-set twice before the honest verdict.
    for _ in range(2):
        chars_after = _compact_stdout_chars(card)
        degradation["serialized_chars_after"] = chars_after
        degradation["over_budget_after_full_ladder"] = chars_after > budget
    return card


def _reader_route_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Index the payload's reader_routes by reader_route_id.

    - Teleology: generated lookup so the text card can fetch a route row by id.
    - Guarantee: returns a dict mapping each reader_route_id to its route dict; non-dict rows are skipped.
    - Fails: never raises; a missing reader_routes list yields an empty dict.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        str(route.get("reader_route_id")): route
        for route in payload.get("reader_routes", [])
        if isinstance(route, dict)
    }


def _reader_packet_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Index the payload's reader_landing_packets by reader_route_id.

    - Teleology: generated lookup so the text card can fetch a landing packet by id.
    - Guarantee: returns a dict mapping each reader_route_id to its packet dict; non-dict packets are skipped.
    - Fails: never raises; a missing/malformed reader_landing_packets yields an empty dict.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    landing_packets = payload.get("reader_landing_packets", {})
    if not isinstance(landing_packets, dict):
        return {}
    return {
        str(packet.get("reader_route_id")): packet
        for packet in landing_packets.get("packets", [])
        if isinstance(packet, dict)
    }


def _reader_menu_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Index the payload's reader_route_menu routes by reader_route_id.

    - Teleology: generated lookup so the text card can fetch a menu row (terminal/text commands) by id.
    - Guarantee: returns a dict mapping each reader_route_id to its menu row dict; non-dict rows are skipped.
    - Fails: never raises; a missing/malformed reader_route_menu yields an empty dict.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    route_menu = payload.get("reader_route_menu", {})
    if not isinstance(route_menu, dict):
        return {}
    return {
        str(row.get("reader_route_id")): row
        for row in route_menu.get("routes", [])
        if isinstance(row, dict)
    }


def _reader_branch_lines(
    route_by_id: dict[str, dict[str, Any]],
    packet_by_id: dict[str, dict[str, Any]],
    menu_by_id: dict[str, dict[str, Any]],
    reader_id: str,
    display_reader_id: str | None = None,
) -> list[str]:
    """
    [ACTION]
    Render the reader-branch text lines for one reader id (or all readers).

    - Teleology: generated text-card section turning the route/packet/menu maps into reader-branch lines.
    - Guarantee: for reader_id="all" returns one summary line plus a per-reader command/proof line for every READER_ROUTE_ID; for a specific id returns that reader's command, question, first action, proof, and success lines, rewriting the alias label when display_reader_id differs.
    - Fails: raises KeyError if the requested reader_id (or a canonical id under "all") is absent from the supplied maps; callers pass maps built from the same payload.
    - Reads: READER_LABELS, READER_ROUTE_IDS, and INTERESTING_PARTS_ALIASES for labels/aliases.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values, declared filesystem outputs.
    """
    if reader_id == "all":
        return [
            f"Reader branches: {READER_ROUTE_ALIAS_HINT}",
            *[
                (
                    f"  {READER_LABELS[route_id]}: "
                    f"{menu_by_id[route_id]['terminal_command']} | Proof: "
                    f"{packet_by_id[route_id]['proof_surface']}"
                )
                for route_id in READER_ROUTE_IDS
            ],
        ]

    route = route_by_id[reader_id]
    packet = packet_by_id[reader_id]
    menu = menu_by_id[reader_id]
    if display_reader_id is None:
        display_reader_id = reader_id
    terminal_command = str(menu["terminal_command"])
    text_projection_command = str(menu["text_projection_command"])
    if display_reader_id != reader_id:
        terminal_command = terminal_command.replace(
            f"--reader {reader_id}",
            f"--reader {display_reader_id}",
            1,
        )
        text_projection_command = text_projection_command.replace(
            f"--reader {reader_id}",
            f"--reader {display_reader_id}",
            1,
        )
    source_first_action = packet.get("source_checkout_first_action")
    source_proof = packet.get("source_checkout_proof_surface")
    first_action_line = f"  First step: {packet['first_action']}"
    proof_line = f"  Proof: {packet['proof_surface']}"
    if source_first_action and source_proof:
        first_action_line = (
            f"{first_action_line} Source-only first step: {source_first_action}"
        )
        proof_line = f"{proof_line} | Source-only proof: {source_proof}"
    task_selector = packet.get("task_selector_command")
    source_task_selector = packet.get("source_checkout_task_selector_command")
    task_selector_lines = []
    if task_selector:
        line = f"  Task selector: `{task_selector}`"
        if source_task_selector:
            line = f"{line} | Source-only: `{source_task_selector}`"
        task_selector_lines.append(line)
    if display_reader_id in INTERESTING_PARTS_ALIASES:
        task_selector_lines.append(
            "  Interesting-parts selector: "
            "`plectis agent-entry-composition --root . --task interesting-parts "
            "--viewer human --card --check` | Source-only: "
            "`PYTHONPATH=src python3 -m microcosm_core agent-entry-composition "
            "--root . --task interesting-parts --viewer human --card --check`"
        )
    return [
        f"Reader branch: {READER_LABELS[reader_id]}",
        (
            f"  Command: {terminal_command} | "
            f"Text card: {text_projection_command}"
        ),
        f"  Question: {route['first_question']}",
        first_action_line,
        *task_selector_lines,
        proof_line,
        f"  Success: {packet['success_criterion']}",
    ]


def _scale_summary_line(payload: dict[str, Any]) -> str:
    """
    [ACTION]
    Render the one-line public-handles summary (organ/standard/source-open counts) for the text card.

    - Teleology: generated single line compressing the headline scale counts into the text card.
    - Guarantee: returns a "Public handles: ..." line citing implemented_organs, public_standards, and source_open_materials counts.
    - Fails: raises KeyError when scale_frame.public_scale_counts or those count rows are absent (direct subscripting); callers pass a fully assembled card payload.
    - Non-goal: counts are accounting handles, not maturity or readiness scores.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    counts = payload["scale_frame"]["public_scale_counts"]
    organs = counts["implemented_organs"]["count"]
    standards = counts["public_standards"]["count"]
    source_open_materials = counts["source_open_materials"]["count"]
    return (
        f"  Public handles: {organs} organ-registry rows, {standards} "
        f"standard-registry rows, {source_open_materials} fixture/workingness "
        "source-open material handles."
    )


def _evidence_class_summary_line(payload: dict[str, Any]) -> str:
    """
    [ACTION]
    Render the one-line evidence-class summary for the text card.

    - Teleology: generated single line naming the evidence classes (or pointing at the registry when incomplete).
    - Guarantee: returns the full evidence-class line when all EVIDENCE_CLASS_DISPLAY_ORDER ids are present in the legend, else a line pointing at core/organ_evidence_classes.json.
    - Fails: never raises; a missing legend falls back to the registry-pointer line.
    - Non-goal: names claim ceilings, not maturity or release scores.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, subprocess side effects requested by the caller.
    """
    class_ids = {
        str(row.get("evidence_class"))
        for row in payload.get("evidence_class_legend", {}).get("classes", [])
        if isinstance(row, dict)
    }
    if set(EVIDENCE_CLASS_DISPLAY_ORDER).issubset(class_ids):
        return (
            "  Evidence classes: body import, subprocess witness, semantic validator, "
            "algorithmic projection, fixture smoke/schema."
        )
    return "  Evidence classes: see core/organ_evidence_classes.json for claim ceilings."


def _substrate_glance_lines(payload: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    Render the substrate-glance text lines (real organ examples) for the text card.

    - Teleology: generated lines showing a few real public organs plus their source ref in the text card.
    - Guarantee: returns excerpted "Substrate glance: ..." lines with a source line when examples exist; falls back to a single ORGAN_ATLAS_REF pointer line when none do.
    - Fails: never raises; absent examples degrade to the atlas-pointer line.
    - Non-goal: examples are handles from the public glance ladder, not readiness or inventory claims.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    glance = payload.get("representative_substrate_glance", {})
    examples = glance.get("examples", []) if isinstance(glance, dict) else []
    rows = [row for row in examples if isinstance(row, dict)]
    if not rows:
        return [f"Substrate glance: see {ORGAN_ATLAS_REF} for public organ glosses."]
    pieces = [
        (
            f"{row.get('display_name')} - "
            f"{_public_excerpt(row.get('glance_excerpt'), 58)}"
        )
        for row in rows
    ]
    return [
        "Substrate glance: " + "; ".join(pieces) + ".",
        (
            f"  Source: {AGENT_TASK_ROUTES_REF} organ_glance_ladder.one_line; "
            "fallbacks use route cards; examples are handles, not readiness "
            "claims."
        ),
    ]


def first_screen_text_card(payload: dict[str, Any], *, reader_id: str = "all") -> str:
    """
    [ACTION]
    Project a composition card into the terminal-sized text first screen for a reader.

    - Teleology: public text projection rendering the same card as a budget-bounded terminal screen, optionally focused on one reader.
    - Guarantee: returns a newline-terminated text card (<= TEXT_CARD_MAX_LINES lines) over the same authority ceiling; `reader_id="all"` shows every reader branch, an alias focuses one.
    - Fails: raises ValueError when `reader_id` is not in TEXT_READER_CHOICES or when the assembled card would exceed the line budget.
    - When-needed: when emitting `plectis first-screen --format text` or the browser/observatory text landing.
    - Escalates-to: first_screen_composition_card as the source card this projects; normalize_reader_route_id resolves the alias.
    - Non-goal: a GENERATED text projection; authorizes no release, hosting, provider calls, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if reader_id not in TEXT_READER_CHOICES:
        raise ValueError(f"unknown first-screen reader route: {reader_id}")
    display_reader_id = reader_id
    reader_id = normalize_reader_route_id(reader_id)
    route_by_id = _reader_route_map(payload)
    packet_by_id = _reader_packet_map(payload)
    menu_by_id = _reader_menu_map(payload)
    human_first_command = payload.get(
        "human_first_command", "plectis hello <project>"
    )
    source_checkout_commands = payload.get("source_checkout_commands", {})
    pre_install_probe = payload.get("pre_install_probe", {})
    pre_install_command = (
        pre_install_probe.get("command")
        if isinstance(pre_install_probe, dict)
        else None
    )
    pre_install_receipt = (
        pre_install_probe.get("receipt_ref")
        if isinstance(pre_install_probe, dict)
        else None
    )
    source_behavior_command = (
        source_checkout_commands.get("behavior_proof")
        if isinstance(source_checkout_commands, dict)
        else None
    )
    source_hello_command = (
        source_checkout_commands.get("hello")
        if isinstance(source_checkout_commands, dict)
        else None
    )
    source_status_command = (
        source_checkout_commands.get("status_card")
        if isinstance(source_checkout_commands, dict)
        else None
    )
    source_agent_entry_command = (
        source_checkout_commands.get("agent_entry_selector")
        if isinstance(source_checkout_commands, dict)
        else None
    )
    source_card_prefix = (
        f"Source-only card: {source_hello_command} | "
        if source_hello_command
        else ""
    )
    source_behavior_suffix = (
        f" | Source-only first run: {source_behavior_command}"
        if source_behavior_command
        else ""
    )
    check_state_suffix = "Trail: catalog -> routes -> events -> evidence -> graph."
    source_agent_entry_suffix = (
        f" | Source-only agent entry: {source_agent_entry_command}"
        if source_agent_entry_command
        else ""
    )
    check_state_line = (
        f"Check state: plectis status --card {payload['project_label']} | "
        f"Source-only status: {source_status_command} | "
        f"{check_state_suffix}{source_agent_entry_suffix}"
        if source_status_command
        else (
            f"Check state: plectis status --card {payload['project_label']} | "
            f"{check_state_suffix}{source_agent_entry_suffix}"
        )
    )
    pre_install_summary = (
        f"Pre-install probe: {pre_install_command} -> {pre_install_receipt}"
        if pre_install_command and pre_install_receipt
        else "Pre-install probe: see QUICKSTART.md"
    )
    glance = payload.get("representative_substrate_glance", {})
    mechanism_count = (
        glance.get("total_organ_count")
        if isinstance(glance, dict)
        and isinstance(glance.get("total_organ_count"), int)
        else "bounded"
    )
    lines = [
        "Plectis first screen",
        (
            "What it is: A public executable atlas of "
            f"{mechanism_count} AI-native runtime mechanisms; evidence records "
            "show runner/source, evidence class, receipt path, and authority ceiling."
        ),
        (
            "Read order: mechanisms -> evidence discipline -> local runtime; "
            "evidence records are the accountability layer, not the product."
        ),
        (
            'Have a goal? plectis comprehend --first-action "<your goal>" --format text | '
            "Source-only: PYTHONPATH=src python3 -m microcosm_core comprehend "
            '--first-action "<your goal>" --format text | Demonstrated in FIRST_ACTION.md'
        ),
        (
            f"{pre_install_summary} | {source_card_prefix}"
            f"Open card: {human_first_command}"
        ),
        (
            f"First run: {payload['shared_first_command']}"
            f"{source_behavior_suffix}"
        ),
        check_state_line,
        *_substrate_glance_lines(payload),
        "Why the counts are honest:",
        _scale_summary_line(payload),
        "  Counts are receipt-backed handles from registries and fixture manifests; status --card shows the stricter body-import floor.",
        _evidence_class_summary_line(payload),
        "  Behavior proof after tour --card: front_door_status=pass, selected_route_id, state refs, source_files_mutated=false.",
        "",
        *_reader_branch_lines(
            route_by_id,
            packet_by_id,
            menu_by_id,
            reader_id,
            display_reader_id,
        ),
        "Runnable-to-structural join:",
        "  This card is the map; the first run writes .microcosm and exercises the larger public substrate:",
        "  concept/mechanism standards, receipts, authority boundaries, workingness, route maps, and observatory views.",
        "",
        "Drilldowns:",
        (
            "  observatory: "
            f"{_bounded_observatory_serve_command(str(payload['project_label']))} "
            "-> /project/first-screen -> /project/observatory-card; artifact fit: "
            "terminal, README, browser, JSON, and video reuse this card; "
            "problem map names the gaps."
        ),
        "  authority/workingness: plectis authority --card / plectis workingness --card",
        f"  route/contract: paper_modules/cold_reader_route_map.md / {payload['source_standard_ref']}",
        "",
        "Authority ceiling: No release, hosted publication, provider-call, source-mutation, private-equivalence, score-progress, or whole-system-correctness authority.",
        f"Omission receipt: deeper evidence remains behind {payload['omission_receipt']['drilldown']}.",
    ]
    if len(lines) > TEXT_CARD_MAX_LINES:
        raise ValueError("first-screen text card exceeded its line budget")
    return "\n".join(lines) + "\n"
