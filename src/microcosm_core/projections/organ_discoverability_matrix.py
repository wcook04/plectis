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
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _rows(value: Any, key: str) -> list[dict[str, Any]]:
    return [row for row in _as_list(_as_dict(value).get(key)) if isinstance(row, dict)]


def _strings(value: Any) -> list[str]:
    return [item for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _load_json(path: Path) -> dict[str, Any]:
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return _load_json(path)


def _by_organ_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("organ_id")): row
        for row in rows
        if isinstance(row.get("organ_id"), str) and row.get("organ_id")
    }


def _standard_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("standard_id")): row
        for row in _rows(payload, "standards")
        if isinstance(row.get("standard_id"), str) and row.get("standard_id")
    }


def _capsules_by_organ(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
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
    coverage = _as_dict(payload.get("organ_required_edge_coverage"))
    return {
        "without_paper_module_ref": set(_strings(coverage.get("without_paper_module_ref"))),
        "without_mechanism_ref": set(_strings(coverage.get("without_mechanism_ref"))),
        "without_code_loci": set(_strings(coverage.get("without_code_loci"))),
    }


def _route_organ_id_from_ref(value: str) -> str:
    marker = "organ_id="
    if marker not in value:
        return ""
    tail = value.split(marker, 1)[1]
    return tail.split("]", 1)[0].strip()


def _route_rows_by_organ(routes_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
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
    task_class = str(route.get("task_class") or "").strip()
    if not task_class:
        return "atlas/agent_task_routes.json::routes[task_class=<missing>]"
    return f"atlas/agent_task_routes.json::routes[task_class={task_class}]"


def _organ_route_role(route: dict[str, Any], organ_id: str) -> str:
    if str(route.get("primary_organ_id") or "").strip() == organ_id:
        return "primary"
    for organ in _as_list(route.get("relevant_organs")):
        if isinstance(organ, dict) and str(organ.get("organ_id") or "") == organ_id:
            return "relevant"
    if _route_organ_id_from_ref(str(route.get("evidence_ref") or "")) == organ_id:
        return "evidence_ref"
    return "matched"


def _organ_route_ref(route: dict[str, Any], organ_id: str) -> str:
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
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _is_runnable_public_command(command: str) -> bool:
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
    return str(atlas_row.get("first_command") or registry_row.get("validator_command") or "").strip()


def _authority_ceiling(registry_row: dict[str, Any], atlas_row: dict[str, Any]) -> str:
    return str(
        atlas_row.get("claim_ceiling_restated") or registry_row.get("claim_ceiling") or ""
    ).strip()


def _proof_receipts(registry_row: dict[str, Any], task_routes: list[dict[str, Any]]) -> list[str]:
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
    for organ in _as_list(route.get("relevant_organs")):
        if not isinstance(organ, dict) or str(organ.get("organ_id") or "") != organ_id:
            continue
        handle = organ.get("source_relation_handle")
        return handle if isinstance(handle, dict) else None
    return None


def _compact_source_relation_summary(route: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "owner_surface": "microcosm public organ substrate",
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
