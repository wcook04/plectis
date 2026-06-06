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
    return str(value or "").strip()


def _slug(value: object) -> str:
    return (
        _normalize_text(value)
        .lower()
        .replace("&", "and")
        .replace("/", " ")
        .replace("-", " ")
        .replace("_", " ")
    )


def _compact_slug(value: object) -> str:
    return "".join(ch for ch in _slug(value) if ch.isalnum())


def _field_present(row: dict[str, Any], keys: Iterable[str]) -> bool:
    return any(_normalize_text(row.get(key)) for key in keys)


def _string_values(value: object) -> Iterator[str]:
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
    if isinstance(payload, dict):
        yield path, payload
        for key, child in payload.items():
            child_path = f"{path}.{key}"
            yield from _iter_objects(child, path=child_path)
    elif isinstance(payload, list):
        for index, child in enumerate(payload):
            yield from _iter_objects(child, path=f"{path}[{index}]")


def _atlas_maps(atlas_payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
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
    if _field_present(row, CARD_ROUTE_KEYS):
        return True
    return any(
        token in value
        for value in _string_values(row)
        for token in CARD_ROUTE_TOKENS
    )


def _projection_mode(row: dict[str, Any]) -> str:
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
    return [(path, read_json_strict(Path(path))) for path in paths]


def main(argv: list[str] | None = None) -> int:
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
