#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
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


def _load_standard(root: Path) -> dict[str, Any]:
    return json.loads((root / STANDARD_REF).read_text(encoding="utf-8"))


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


def _scale_frame() -> dict[str, Any]:
    return {
        "composition_root": (
            "The shared first command is the landing surface; standards, receipts, organs, and "
            "observatory views are drilldowns."
        ),
        "scale_handles": [
            {
                "handle": "standards registry",
                "ref": "core/standards_registry.json",
            },
            {
                "handle": "workingness map",
                "command": "microcosm workingness",
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
    return {
        "shared_first_command": payload.get("shared_first_command", "").startswith(
            "microcosm tour --card "
        ),
        "reader_route_ids": route_ids == REQUIRED_ROUTE_IDS,
        "evidence_count_frame": (
            payload.get("evidence_count_frame", {}).get("interpretation")
            == "accounting_not_maturity_score"
        ),
        "scale_frame": bool(payload.get("scale_frame", {}).get("scale_handles")),
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
        "scale_frame": _scale_frame(),
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


def first_screen_text_card(payload: dict[str, Any], *, reader_id: str = "all") -> str:
    if reader_id not in TEXT_READER_CHOICES:
        raise ValueError(f"unknown first-screen reader route: {reader_id}")
    route_by_id = _reader_route_map(payload)
    lines = [
        "Microcosm first screen",
        f"First run: {payload['shared_first_command']}",
        "",
        "What it is:",
        "  A local evidence router for a folder: run one compact command, then choose the drilldown.",
        "",
        "Why the counts are honest:",
        "  Evidence counts are accounting fields, not maturity, readiness, or progress scores.",
        "",
        *_reader_branch_lines(route_by_id, reader_id),
        "",
        "Runnable-to-structural join:",
        "  The local run is one visible exercise of the larger public substrate:",
        "  standards, receipts, authority boundaries, workingness, route maps, and observatory views.",
        "",
        "Drilldowns:",
        "  authority: microcosm authority",
        "  workingness: microcosm workingness",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="first_screen_composition_card",
        description="Emit the Microcosm first-screen composition card.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=MICROCOSM_ROOT,
        help="Microcosm public root; defaults to the script's parent tree.",
    )
    parser.add_argument(
        "--project-label",
        default="<project>",
        help="Label to place in the shared first command.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output JSON contract or terminal-sized text card.",
    )
    parser.add_argument(
        "--reader",
        choices=TEXT_READER_CHOICES,
        default="all",
        help="Reader branch to focus when emitting the terminal text card.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = first_screen_composition_card(args.root, project_label=args.project_label)
    if args.format == "text":
        print(first_screen_text_card(payload, reader_id=args.reader), end="")
    else:
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
