"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.validators.entry_projection_faithfulness` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: CHECKER_ID, SCHEMA_VERSION, PASS, BLOCKED, RICH_FIELDS, ID_KEYS, ID_LIST_KEYS, DISPLAY_KEYS, COMMAND_KEYS, CEILING_KEYS, CARD_ROUTE_KEYS, CARD_ROUTE_TOKENS, ANTI_CLAIM, evaluate_entry_projection_faithfulness, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.entry_projection_faithfulness"
SCHEMA_VERSION = "entry_projection_faithfulness_card_v1"
PASS = "pass"
BLOCKED = "blocked"

RICH_FIELDS = (
    "human_gloss",
    "agent_gloss",
    "first_command",
    "claim_ceiling_restated",
)

ID_KEYS = (
    "organ_id",
    "primary_organ_id",
    "component_id",
)

ID_LIST_KEYS = (
    "organ_ids",
    "relevant_organs",
    "component_ids",
)

DISPLAY_KEYS = (
    "display_name",
    "source_display_name",
    "public_label",
    "primary_display_name",
    "name",
    "label",
)

COMMAND_KEYS = (
    "first_command",
    "route_command",
    "next_command",
    "validator_command",
    "acceptance_command",
)

CEILING_KEYS = (
    "claim_ceiling_restated",
    "claim_ceiling",
    "authority_boundary",
    "allowed_authority",
    "anti_claim",
    "anti_overread",
    "anti_misread",
)

CARD_ROUTE_KEYS = (
    "card_ref",
    "card_refs",
    "drilldown",
    "drilldown_ref",
    "drilldown_target",
    "drilldown_targets",
    "evidence_ref",
    "evidence_refs",
    "primary_card_ref",
    "receipt_ref",
    "source_ref",
    "source_refs",
)

CARD_ROUTE_TOKENS = (
    "ORGANS.md#",
    "core/organ_atlas.json",
    "organ_registry.json::implemented_organs",
    "accepted_current_authority_organs",
)

ANTI_CLAIM = (
    "This card checks whether a projection that names Microcosm organs preserves "
    "enough rich source-card affordance for a cold reader or agent. It does not "
    "certify publication readiness, source correctness, proof correctness, "
    "secret absence, release state, or live route behavior."
)


def _normalize_text(value: object) -> str:
    """
    [ACTION]
    Coerce any value to a stripped string for presence/equality checks.

    - Teleology: single normalization primitive so every field probe treats None/falsy/whitespace uniformly.
    - Guarantee: returns a str; None and falsy values become "", surrounding whitespace stripped.
    - Fails: never raises; non-string objects are coerced via str().
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(value or "").strip()


def _slug(value: object) -> str:
    """
    [ACTION]
    Lowercase a value and flatten separators to spaces for fuzzy display matching.

    - Teleology: tolerant display-name comparison key so "&", "/", "-", "_" do not block organ-id resolution.
    - Guarantee: returns a lowercased str with &->and and /-_ replaced by spaces.
    - Fails: never raises; empty/None input yields "".
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    return (
        _normalize_text(value)
        .lower()
        .replace("&", "and")
        .replace("/", " ")
        .replace("-", " ")
        .replace("_", " ")
    )


def _compact_slug(value: object) -> str:
    """
    [ACTION]
    Reduce a value to its alphanumeric-only lowercase fingerprint.

    - Teleology: whitespace/punctuation-insensitive join key for the display-name -> organ-id index.
    - Guarantee: returns a str containing only lowercase alphanumerics derived from _slug(value).
    - Fails: never raises; non-alnum chars and empty input collapse to "".
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return "".join(ch for ch in _slug(value) if ch.isalnum())


def _field_present(row: dict[str, Any], keys: Iterable[str]) -> bool:
    """
    [ACTION]
    Report whether any of the candidate keys holds a non-empty value on the row.

    - Teleology: affordance probe used to decide if a row carries a command, ceiling, or card-route field.
    - Guarantee: returns True iff at least one key resolves to a non-empty normalized string.
    - Fails: never raises; missing keys and whitespace-only values count as absent.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return any(_normalize_text(row.get(key)) for key in keys)


def _string_values(value: object) -> Iterator[str]:
    """
    [ACTION]
    Recursively yield every non-empty string nested anywhere inside a value.

    - Teleology: lets card-route token scanning see strings buried in nested dicts/lists, not just top keys.
    - Guarantee: yields each non-blank str leaf reachable through dict values and list items, depth-first.
    - Fails: never raises; scalars that are not str (int/None/bool) yield nothing.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, str):
        if value.strip():
            yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def _row_id(row: dict[str, Any], fallback: str) -> str:
    """
    [ACTION]
    Pick a stable human-facing identifier for a projection row, else the fallback path.

    - Teleology: gives each reported/under-projected row a deterministic id for sorting and operator triage.
    - Guarantee: returns the first non-empty value among the id/label key priority list, otherwise the fallback.
    - Fails: never raises; an all-empty row returns the supplied fallback unchanged.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for key in (
        "row_id",
        "route_id",
        "task_class",
        "component_id",
        "organ_id",
        "primary_organ_id",
        "public_label",
        "display_name",
        "name",
    ):
        value = _normalize_text(row.get(key))
        if value:
            return value
    return fallback


def _iter_objects(payload: object, *, path: str = "$") -> Iterator[tuple[str, dict[str, Any]]]:
    """
    [ACTION]
    Walk a JSON payload and yield every dict object with its JSONPath-like location.

    - Teleology: turns an arbitrarily-shaped projection file into a flat stream of inspectable organ rows.
    - Guarantee: yields (path, dict) for each dict reached through nested dicts/lists; paths use .key and [index].
    - Fails: never raises; non-container leaves yield nothing.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(payload, dict):
        yield path, payload
        for key, child in payload.items():
            child_path = f"{path}.{key}"
            yield from _iter_objects(child, path=child_path)
    elif isinstance(payload, list):
        for index, child in enumerate(payload):
            yield from _iter_objects(child, path=f"{path}[{index}]")


def _atlas_maps(atlas_payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """
    [ACTION]
    Index the organ atlas into id->card and display-fingerprint->id lookup maps.

    - Teleology: the source-of-truth side of the check; lets projection rows be resolved back to their rich card.
    - Guarantee: returns (cards_by_id, ids_by_display) covering every atlas organ that has a non-empty organ_id.
    - Fails: never raises; non-dict cards and id-less cards are skipped silently; missing "organs" yields empty maps.
    - When-needed: inspect when a projection row fails to match an organ you expect it to.
    - Escalates-to: core/organ_atlas.json (the atlas payload these maps index).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cards_by_id: dict[str, dict[str, Any]] = {}
    ids_by_display: dict[str, str] = {}
    for card in atlas_payload.get("organs", []):
        if not isinstance(card, dict):
            continue
        organ_id = _normalize_text(card.get("organ_id"))
        if not organ_id:
            continue
        cards_by_id[organ_id] = card
        display = _normalize_text(card.get("display_name"))
        if display:
            ids_by_display[_compact_slug(display)] = organ_id
    return cards_by_id, ids_by_display


def _source_rich_coverage(cards_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    Summarize how completely the atlas itself populates the required rich fields.

    - Teleology: baseline-coverage receipt so a projection failure is read against actual source richness.
    - Guarantee: returns per-field counts, fully-rich-card count, total organ count, and the required-field list.
    - Fails: never raises; returns zeroed counts and organ_count 0 for an empty atlas map.
    - When-needed: inspect to tell "projection dropped affordance" from "source never had it".
    - Escalates-to: RICH_FIELDS constant + core/organ_atlas.json card bodies.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    counts = {
        field: sum(1 for card in cards_by_id.values() if _normalize_text(card.get(field)))
        for field in RICH_FIELDS
    }
    complete = [
        organ_id
        for organ_id, card in cards_by_id.items()
        if all(_normalize_text(card.get(field)) for field in RICH_FIELDS)
    ]
    return {
        "organ_count": len(cards_by_id),
        "complete_rich_card_count": len(complete),
        "field_counts": counts,
        "required_fields": list(RICH_FIELDS),
    }


def _candidate_organ_ids(
    row: dict[str, Any],
    *,
    cards_by_id: dict[str, dict[str, Any]],
    ids_by_display: dict[str, str],
) -> list[str]:
    """
    [ACTION]
    Resolve which atlas organ ids a single projection row actually names.

    - Teleology: the join step; only rows that name a real organ are subject to the faithfulness check.
    - Guarantee: returns a sorted deduped list of organ ids present in cards_by_id, matched via id keys, id-lists, or display fingerprint.
    - Fails: never raises; a row naming no resolvable organ returns []; unmatched display labels contribute nothing.
    - When-needed: inspect when a row is unexpectedly skipped or attributed to the wrong organ.
    - Escalates-to: ID_KEYS / ID_LIST_KEYS / DISPLAY_KEYS constants + _atlas_maps.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidates: list[str] = []
    for key in ID_KEYS:
        value = _normalize_text(row.get(key))
        if value in cards_by_id:
            candidates.append(value)
    for key in ID_LIST_KEYS:
        value = row.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    item_id = _normalize_text(item.get("organ_id") or item.get("id"))
                    item_label = _normalize_text(
                        item.get("display_name") or item.get("name") or item.get("label")
                    )
                else:
                    item_id = _normalize_text(item)
                    item_label = item_id
                if item_id in cards_by_id:
                    candidates.append(item_id)
                else:
                    display_match = ids_by_display.get(_compact_slug(item_label))
                    if display_match:
                        candidates.append(display_match)
    for key in DISPLAY_KEYS:
        display_match = ids_by_display.get(_compact_slug(row.get(key)))
        if display_match:
            candidates.append(display_match)
    return sorted(set(candidates))


def _has_card_route(row: dict[str, Any]) -> bool:
    """
    [ACTION]
    Decide whether a row carries an explicit route back to the rich organ card.

    - Teleology: lets a compressed row pass when it points at the rich card instead of inlining it.
    - Guarantee: returns True iff a CARD_ROUTE_KEYS field is present or any nested string contains a CARD_ROUTE_TOKENS marker.
    - Fails: never raises; a row with no route key and no marker token returns False.
    - When-needed: inspect when a compressed row is unexpectedly flagged under_projected despite a drilldown.
    - Escalates-to: CARD_ROUTE_KEYS / CARD_ROUTE_TOKENS constants.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if _field_present(row, CARD_ROUTE_KEYS):
        return True
    return any(
        token in value
        for value in _string_values(row)
        for token in CARD_ROUTE_TOKENS
    )


def _projection_mode(row: dict[str, Any]) -> str:
    """
    [ACTION]
    Classify a row's affordance posture into inline / compressed-route / under-projected.

    - Teleology: the verdict primitive; this label is what flips an organ-naming row to blocked.
    - Guarantee: returns "inline_rich_card" when >=2 rich fields present, "compressed_route_to_rich_card" when command+ceiling+card-route all present, else "under_projected".
    - Fails: never raises; a row with neither inline richness nor a complete compressed route returns "under_projected".
    - When-needed: inspect when deciding why a specific row passed or blocked.
    - Escalates-to: RICH_FIELDS / COMMAND_KEYS / CEILING_KEYS thresholds + _has_card_route.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rich_count = sum(1 for field in RICH_FIELDS if _normalize_text(row.get(field)))
    has_command = _field_present(row, COMMAND_KEYS)
    has_ceiling = _field_present(row, CEILING_KEYS)
    has_card_route = _has_card_route(row)
    if rich_count >= 2:
        return "inline_rich_card"
    if has_command and has_ceiling and has_card_route:
        return "compressed_route_to_rich_card"
    return "under_projected"


def evaluate_entry_projection_faithfulness(
    atlas_payload: dict[str, Any],
    projection_payloads: Iterable[tuple[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    Assert every organ-naming projection row preserves rich-card affordance or routes back to it.

    - Teleology: the payload-boundary gate guarding entry projections from silently stripping cold-reader affordance off named organs.
    - Guarantee: returns a card dict (schema_version, checker_id, status, coverage, row inventories, anti_claim); status is "pass" iff no under_projected rows, else "blocked" with per-row error_code "rich_card_suppressed_by_projection" and owner mutation guidance.
    - Fails: never raises on payload shape; non-organ rows are ignored; any organ row that is neither inline-rich nor a complete compressed route lands in under_projected_rows and forces "blocked".
    - When-needed: inspect before trusting that an entry/task-route projection still lets a cold agent reach each named organ's gloss/command/ceiling.
    - Escalates-to: under_projected_rows[].owner_surface_mutation_guidance, core/organ_atlas.json, tests/ for entry_projection_faithfulness.
    - Non-goal: passing does NOT certify publication readiness, source/proof correctness, secret absence, release state, or live route behavior (see ANTI_CLAIM).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cards_by_id, ids_by_display = _atlas_maps(atlas_payload)
    projection_rows: list[dict[str, Any]] = []
    under_projected: list[dict[str, Any]] = []
    inspected_refs: list[str] = []

    for projection_ref, payload in projection_payloads:
        inspected_refs.append(projection_ref)
        for object_path, row in _iter_objects(payload):
            organ_ids = _candidate_organ_ids(
                row,
                cards_by_id=cards_by_id,
                ids_by_display=ids_by_display,
            )
            if not organ_ids:
                continue
            mode = _projection_mode(row)
            row_card = {
                "projection_ref": projection_ref,
                "object_path": object_path,
                "row_id": _row_id(row, object_path),
                "organ_ids": organ_ids,
                "display_label": _normalize_text(
                    row.get("public_label")
                    or row.get("primary_display_name")
                    or row.get("display_name")
                    or row.get("name")
                    or row.get("label")
                ),
                "projection_mode": mode,
                "present_rich_fields": [
                    field for field in RICH_FIELDS if _normalize_text(row.get(field))
                ],
                "has_first_command": _field_present(row, COMMAND_KEYS),
                "has_authority_ceiling": _field_present(row, CEILING_KEYS),
                "has_rich_card_route": _has_card_route(row),
            }
            projection_rows.append(row_card)
            if mode == "under_projected":
                under_projected.append(
                    {
                        **row_card,
                        "error_code": "rich_card_suppressed_by_projection",
                        "missing_affordance": (
                            "projection names a rich organ card but exposes neither "
                            "inline gloss/command/ceiling fields nor a compressed route "
                            "back to the rich card"
                        ),
                        "source_rich_fields_available": {
                            organ_id: [
                                field
                                for field in RICH_FIELDS
                                if _normalize_text(cards_by_id[organ_id].get(field))
                            ]
                            for organ_id in organ_ids
                        },
                        "owner_surface_mutation_guidance": (
                            "Carry human_gloss, agent_gloss, first_command, and "
                            "claim_ceiling_restated from core/organ_atlas.json, or "
                            "make the projection explicitly route to the rich organ card "
                            "while preserving first command and authority ceiling."
                        ),
                    }
                )

    status = PASS if not under_projected else BLOCKED
    return {
        "schema_version": SCHEMA_VERSION,
        "checker_id": CHECKER_ID,
        "status": status,
        "atlas_ref": "core/organ_atlas.json",
        "source_rich_coverage": _source_rich_coverage(cards_by_id),
        "projection_ref_count": len(inspected_refs),
        "projection_refs": sorted(inspected_refs),
        "organ_projection_row_count": len(projection_rows),
        "under_projected_count": len(under_projected),
        "under_projected_rows": sorted(
            under_projected,
            key=lambda row: (row["projection_ref"], row["object_path"], row["row_id"]),
        ),
        "projection_rows": sorted(
            projection_rows,
            key=lambda row: (row["projection_ref"], row["object_path"], row["row_id"]),
        ),
        "next_action": (
            "projection_can_remain_compressed_or_inline"
            if status == PASS
            else "patch_projection_owner_or_generator_to_preserve_rich_card_affordance"
        ),
        "reentry_condition": (
            "Resume when a projection that names Microcosm organs has either "
            "inline rich card fields or an explicit rich-card drilldown plus command "
            "and authority ceiling for each named organ row."
        ),
        "anti_claim": ANTI_CLAIM,
    }


def _load_projection_payloads(paths: Iterable[str]) -> list[tuple[str, Any]]:
    """
    [ACTION]
    Strictly load each projection path into (ref, parsed-json) pairs for evaluation.

    - Teleology: source-custody loader binding each inspected payload to its on-disk path for traceable receipts.
    - Guarantee: returns a list of (path, parsed_json) tuples, one per input path, parsed via read_json_strict.
    - Fails: propagates read_json_strict errors (missing file / invalid JSON); does not swallow them.
    - When-needed: inspect when a projection path is unreadable or its parse fails before the check runs.
    - Escalates-to: microcosm_core.schemas.read_json_strict.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [(path, read_json_strict(Path(path))) for path in paths]


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entry: run the faithfulness check over an atlas + projection set and print the card.

    - Teleology: command-line surface that wires --root/--atlas/--projection-json into the evaluator for CI and operators.
    - Guarantee: prints the JSON card to stdout; returns 0 when status is "pass" or --check is absent, 1 when blocked under --check.
    - Fails: returns 1 only on blocked-under-check; propagates read_json_strict errors for unreadable atlas/projection files; argparse exits on bad flags.
    - When-needed: invoke to gate a build or audit a projection file from the shell.
    - Escalates-to: evaluate_entry_projection_faithfulness card output + --check exit code.
    - Non-goal: a passing exit does NOT authorize release, publication, or source mutation; it only attests rich-card affordance preservation.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Check whether Microcosm organ entry projections preserve rich atlas-card "
            "affordance or explicitly route back to it."
        )
    )
    parser.add_argument("--root", default=".", help="Microcosm repository root.")
    parser.add_argument(
        "--atlas",
        help="Atlas JSON path. Defaults to <root>/core/organ_atlas.json.",
    )
    parser.add_argument(
        "--projection-json",
        action="append",
        default=[],
        help="Projection JSON to inspect. Repeatable.",
    )
    parser.add_argument("--check", action="store_true", help="Exit nonzero if blocked.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    atlas_path = Path(args.atlas) if args.atlas else root / "core/organ_atlas.json"
    projection_paths = args.projection_json or [str(root / "atlas/agent_task_routes.json")]
    card = evaluate_entry_projection_faithfulness(
        read_json_strict(atlas_path),
        _load_projection_payloads(projection_paths),
    )
    print(json.dumps(card, indent=2, sort_keys=True))
    return 0 if card["status"] == PASS or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
