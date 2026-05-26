from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[2]
STANDARD_REF = Path("standards/std_microcosm_first_screen_composition_root.json")
READER_ROUTE_IDS = (
    "safety_evals_engineer",
    "hiring_reviewer",
    "peer_developer",
)
REQUIRED_ROUTE_IDS = set(READER_ROUTE_IDS)
READER_LABELS = {
    "safety_evals_engineer": "Safety/evals",
    "hiring_reviewer": "Hiring",
    "peer_developer": "Peer developer",
}
DENIED_AUTHORITY_KEYS = (
    "release_authority",
    "source_mutation_authority",
    "private_data_equivalence_authority",
    "provider_call_authority",
    "score_based_progress_authority",
    "whole_system_correctness_authority",
)
TEXT_CARD_MAX_LINES = 32
TEXT_READER_CHOICES = ("all",) + READER_ROUTE_IDS
ORGAN_REGISTRY_REF = "core/organ_registry.json"
STANDARDS_REGISTRY_REF = "core/standards_registry.json"
WORKINGNESS_MAP_REF = "receipts/runtime_shell/workingness_failure_map.json"


def _load_standard(root: Path) -> dict[str, Any]:
    return json.loads((root / STANDARD_REF).read_text(encoding="utf-8"))


def _load_public_json(root: Path, ref: str) -> dict[str, Any]:
    try:
        payload = json.loads((root / ref).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _collection_count(value: Any) -> int | None:
    if isinstance(value, (dict, list, tuple)):
        return len(value)
    return None


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _first_count(*candidates: int | None) -> int | None:
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def _positive_count(row: Any) -> bool:
    return (
        isinstance(row, dict)
        and isinstance(row.get("count"), int)
        and not isinstance(row.get("count"), bool)
        and row["count"] > 0
    )


def _reader_routes(project_label: str) -> list[dict[str, Any]]:
    return [
        {
            "reader_route_id": "safety_evals_engineer",
            "first_question": "Does the evidence discipline survive contact with scale?",
            "next_commands": [
                f"microcosm status --card {project_label}",
                "microcosm authority",
                "microcosm workingness",
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
                "microcosm legibility-scorecard",
                f"microcosm tour --card {project_label}",
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
                f"microcosm tour --card {project_label}",
                f"microcosm observe {project_label}",
            ],
            "evidence_focus": [
                "folder-local .microcosm state",
                "route/work/event/evidence chain",
                "standards and receipt drilldowns behind the compact card",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
    ]


def _evidence_count_frame() -> dict[str, Any]:
    return {
        "interpretation": "accounting_not_maturity_score",
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
                "surface": "microcosm workingness",
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


def _scale_frame(root: Path) -> dict[str, Any]:
    organ_registry = _load_public_json(root, ORGAN_REGISTRY_REF)
    standards_registry = _load_public_json(root, STANDARDS_REGISTRY_REF)
    workingness_map = _load_public_json(root, WORKINGNESS_MAP_REF)
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
                "count": source_open_material_count,
                "source_field": "source_open_body_material_count",
                "source_ref": WORKINGNESS_MAP_REF,
                "read_as": "copy_boundary_accounting_not_maturity_score",
            },
            "rows_with_source_imports": {
                "count": _non_negative_int(
                    workingness_map.get("rows_with_source_body_imports")
                ),
                "source_field": "rows_with_source_body_imports",
                "source_ref": WORKINGNESS_MAP_REF,
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
                "command": "microcosm workingness",
                "ref": WORKINGNESS_MAP_REF,
            },
            {
                "handle": "authority boundary",
                "command": "microcosm authority",
            },
            {
                "handle": "localhost observatory",
                "endpoint_ref": "http://localhost:8765/workingness",
            },
        ],
        "scale_rule": (
            "Breadth should appear as a named composition root plus drilldown handles, "
            "not as a long first-screen inventory."
        ),
    }


def _comparison_frame() -> dict[str, Any]:
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


def _entry_surface_contract(project_label: str) -> dict[str, Any]:
    return {
        "shared_behavior_surface": f"microcosm tour --card {project_label}",
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
            "preserve the shared first command, reader route ids, evidence-count frame, "
            "omission receipt, and authority ceiling."
        ),
        "format_contract": {
            "json": "machine-readable public card",
            "text": "terminal-sized projection over the same authority ceiling",
        },
    }


def _runnable_structural_join(project_label: str) -> dict[str, Any]:
    return {
        "local_behavior": (
            f"`microcosm tour --card {project_label}` is the first folder-local behavior surface: "
            "it lets a reader see compact local state before choosing a route."
        ),
        "structural_context": (
            "That local run is one visible exercise of the larger public substrate: standards, "
            "receipts, authority boundaries, workingness, route maps, and observatory endpoints."
        ),
        "join_rule": "The first run must name the larger structure it exercised without copying the deeper bodies.",
    }


def _drilldowns(project_label: str) -> list[dict[str, str]]:
    return [
        {
            "drilldown_id": "shared_first_card",
            "command": f"microcosm tour --card {project_label}",
        },
        {
            "drilldown_id": "status_card",
            "command": f"microcosm status --card {project_label}",
        },
        {
            "drilldown_id": "authority",
            "command": "microcosm authority",
        },
        {
            "drilldown_id": "workingness",
            "command": "microcosm workingness",
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
    route_ids = {
        str(route.get("reader_route_id"))
        for route in payload.get("reader_routes", [])
        if isinstance(route, dict)
    }
    authority_ceiling = payload.get("authority_ceiling", {})
    drilldown_text = json.dumps(payload.get("drilldowns", []), sort_keys=True)
    scale_frame = payload.get("scale_frame", {})
    scale_counts = scale_frame.get("public_scale_counts", {})
    return {
        "shared_first_command": payload.get("shared_first_command", "").startswith(
            "microcosm tour --card "
        ),
        "reader_route_ids": route_ids == REQUIRED_ROUTE_IDS,
        "evidence_count_frame": (
            payload.get("evidence_count_frame", {}).get("interpretation")
            == "accounting_not_maturity_score"
        ),
        "comparison_frame": (
            payload.get("comparison_frame", {}).get("purpose")
            == "make_rigor_visible_without_claim_inflation"
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
        "authority_ceiling": all(
            authority_ceiling.get(key) is False for key in DENIED_AUTHORITY_KEYS
        ),
        "omission_receipt": bool(payload.get("omission_receipt", {}).get("drilldown")),
        "workingness_drilldown": "microcosm workingness" in drilldown_text,
    }


def first_screen_composition_card(
    root: Path = MICROCOSM_ROOT,
    *,
    project_label: str = "<project>",
) -> dict[str, Any]:
    root = Path(root)
    standard = _load_standard(root)
    payload: dict[str, Any] = {
        "schema_version": "microcosm_first_screen_composition_card_v1",
        "composition_root_id": standard["kind_id"],
        "source_standard_ref": str(STANDARD_REF),
        "shared_first_command": f"microcosm tour --card {project_label}",
        "reader_routes": _reader_routes(project_label),
        "evidence_count_frame": _evidence_count_frame(),
        "comparison_frame": _comparison_frame(),
        "entry_surface_contract": _entry_surface_contract(project_label),
        "scale_frame": _scale_frame(root),
        "runnable_structural_join": _runnable_structural_join(project_label),
        "drilldowns": _drilldowns(project_label),
        "omission_receipt": standard["omission_receipt"],
        "authority_ceiling": standard["authority_ceiling"],
        "anti_claim": standard["anti_claim"],
        "public_private_boundary": {
            "allowed_public_inputs": standard["public_private_boundary"][
                "allowed_public_inputs"
            ],
            "forbidden_public_inputs": standard["public_private_boundary"][
                "forbidden_public_inputs"
            ],
        },
        "validator_id": standard["validator_contract"]["validator_id"],
    }
    checks = _validation_checks(payload)
    payload["validation"] = {
        "status": "pass" if all(checks.values()) else "blocked",
        "checks": checks,
    }
    payload["status"] = payload["validation"]["status"]
    return payload


def _reader_route_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(route.get("reader_route_id")): route
        for route in payload.get("reader_routes", [])
        if isinstance(route, dict)
    }


def _reader_branch_lines(
    route_by_id: dict[str, dict[str, Any]],
    reader_id: str,
) -> list[str]:
    if reader_id == "all":
        return [
            "Reader branches:",
            *[
                f"  {READER_LABELS[route_id]}: {' -> '.join(route_by_id[route_id]['next_commands'])}"
                for route_id in READER_ROUTE_IDS
            ],
        ]

    route = route_by_id[reader_id]
    focus_lines = [f"    - {focus}" for focus in route["evidence_focus"][:3]]
    return [
        f"Reader branch: {READER_LABELS[reader_id]}",
        f"  Question: {route['first_question']}",
        f"  Next: {' -> '.join(route['next_commands'])}",
        "  Focus:",
        *focus_lines,
    ]


def _scale_summary_line(payload: dict[str, Any]) -> str:
    counts = payload["scale_frame"]["public_scale_counts"]
    organs = counts["implemented_organs"]["count"]
    standards = counts["public_standards"]["count"]
    source_open_materials = counts["source_open_materials"]["count"]
    return (
        f"  Public scale: {organs} organs, {standards} standards, "
        f"{source_open_materials} source-open materials."
    )


def first_screen_text_card(payload: dict[str, Any], *, reader_id: str = "all") -> str:
    if reader_id not in TEXT_READER_CHOICES:
        raise ValueError(f"unknown first-screen reader route: {reader_id}")
    route_by_id = _reader_route_map(payload)
    lines = [
        "Microcosm first screen",
        f"First run: {payload['shared_first_command']}",
        "",
        "What it is:",
        "  A local evidence router, not a maturity brochure: one command, then a drilldown.",
        "",
        "Why the counts are honest:",
        _scale_summary_line(payload),
        "  Counts are receipt-backed handles, not maturity, readiness, or progress scores.",
        "",
        *_reader_branch_lines(route_by_id, reader_id),
        "",
        "Runnable-to-structural join:",
        "  The local run is one visible exercise of the larger public substrate:",
        "  standards, receipts, authority boundaries, workingness, route maps, and observatory views.",
        "",
        "Drilldowns:",
        "  authority/workingness: microcosm authority / microcosm workingness",
        "  route map: paper_modules/cold_reader_route_map.md",
        f"  composition contract: {payload['source_standard_ref']}",
        "",
        "Authority ceiling:",
        "  No release, hosted publication, provider-call, source-mutation, private-equivalence,",
        "  score-progress, or whole-system-correctness authority.",
        "",
        f"Omission receipt: deeper evidence remains behind {payload['omission_receipt']['drilldown']}.",
    ]
    if len(lines) > TEXT_CARD_MAX_LINES:
        raise ValueError("first-screen text card exceeded its line budget")
    return "\n".join(lines) + "\n"
