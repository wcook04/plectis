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
EVIDENCE_CLASS_REGISTRY_REF = "core/organ_evidence_classes.json"
WORKINGNESS_MAP_REF = "receipts/runtime_shell/workingness_failure_map.json"
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


def _reader_landing_packets(project_label: str) -> dict[str, Any]:
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
                "reader_route_id": "safety_evals_engineer",
                "first_action": f"Run `microcosm status --card {project_label}`.",
                "proof_surface": (
                    "`microcosm authority` plus `microcosm workingness`"
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
                    f"Run `microcosm hello {project_label}` before the longer tour."
                ),
                "proof_surface": f"`microcosm tour --card {project_label}`",
                "success_criterion": (
                    "Can distinguish runnable local behavior from the claims this "
                    "public card explicitly refuses to make."
                ),
                "next_drilldown": "microcosm legibility-scorecard",
                "authority": "inspection_order_only_not_candidate_assessment",
            },
            {
                "reader_route_id": "peer_developer",
                "first_action": f"Run `microcosm tour --card {project_label}`.",
                "proof_surface": f"`microcosm observe {project_label}`",
                "success_criterion": (
                    "Can inspect folder-local .microcosm state and follow the "
                    "route/work/event/evidence chain without provider calls."
                ),
                "next_drilldown": "paper_modules/cold_reader_route_map.md",
                "authority": "inspection_order_only_not_integration_guarantee",
            },
        ],
    }


def _evidence_count_frame() -> dict[str, Any]:
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


def _evidence_class_legend(root: Path) -> dict[str, Any]:
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
                "claim_ceiling": profile.get("claim_ceiling"),
                "evaluator_basis": profile.get("evaluator_basis"),
                "negative_case_independence": profile.get(
                    "negative_case_independence"
                ),
                "truth_accounting_bucket": profile.get("truth_accounting_bucket"),
                "counts_as_real_substrate_progress": profile.get(
                    "counts_as_real_substrate_progress"
                )
                is True,
                "evidence_strength_rank": profile.get("evidence_strength_rank"),
                "reader_rule": "declared_claim_ceiling_not_maturity_or_release_score",
            }
        )

    return {
        "schema_version": "microcosm_evidence_class_legend_v1",
        "source_ref": EVIDENCE_CLASS_REGISTRY_REF,
        "interpretation": "claim_boundary_legend_not_score",
        "authority_boundary": registry.get("authority_boundary"),
        "anti_claim": registry.get("anti_claim"),
        "reader_rule": (
            "Each evidence class names what a count can claim and what it cannot "
            "claim. It is a public claim-boundary legend, not a benchmark, release "
            "gate, product-completeness signal, or maturity score."
        ),
        "classes": rows,
        "missing_profiles": missing_profiles,
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


def _doctrine_effect_frame() -> dict[str, Any]:
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
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    first_screen_json_command = f"microcosm first-screen {project_label}"
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
                "surface": "reader_routes",
                "must_precede": "quickstart_command_inventory",
                "reason": "Reader branching happens before the long command list.",
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
            "preserve the shared first command, reader route ids, reader landing packets, "
            "evidence-count frame, evidence-class legend, doctrine-effect frame, "
            "observatory landing frame, README-entry contract, omission receipt, and "
            "authority ceiling."
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


def _observatory_landing_frame(project_label: str) -> dict[str, Any]:
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    return {
        "schema_version": "microcosm_observatory_landing_frame_v1",
        "role": "make_the_hello_first_screen_card_the_browser_landing_frame",
        "human_first_command": human_first_command,
        "text_projection_command": human_first_command,
        "shared_first_command": shared_first_command,
        "behavioral_proof_command": shared_first_command,
        "endpoints": dict(OBSERVATORY_LANDING_ENDPOINTS),
        "browser_landing_reuse": {
            "source_projection": (
                "microcosm_core.first_screen_composition.first_screen_text_card"
            ),
            "default_endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
            "card_endpoint": OBSERVATORY_LANDING_ENDPOINTS["first_screen_card"],
            "authority": (
                "browser_projection_over_same_card_not_json_first_lens_inventory"
            ),
        },
        "first_viewport_rule": (
            "The browser landing frame should show the hello card command, behavior proof, "
            "reader branches, reader landing packets, public scale handles, evidence-class "
            "legend, doctrine-effect frame, and authority ceiling before the deeper "
            "observatory lens inventory."
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
            "reader_route_ids",
            "reader_landing_packets",
            "public_scale_counts",
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
    return [
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
            "microcosm tour --card "
        ),
        "human_first_command": (
            isinstance(human_first_command, str)
            and human_first_command.startswith("microcosm hello ")
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
        "evidence_count_frame": (
            payload.get("evidence_count_frame", {}).get("interpretation")
            == "accounting_not_maturity_score"
            and payload.get("evidence_count_frame", {}).get("legend_ref")
            == EVIDENCE_CLASS_REGISTRY_REF
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
        "doctrine_effect_frame": (
            isinstance(doctrine_effect_frame, dict)
            and doctrine_effect_frame.get("purpose")
            == "show_doctrine_as_mistake_prevention_not_ceremony"
            and doctrine_handles
            == {"CONSTITUTION", "AXIOMS", "PRINCIPLES", "ANTI_PRINCIPLES"}
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
                f"microcosm first-screen {payload.get('project_label', '<project>')}",
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
                    "reader_route_ids",
                    "reader_landing_packets",
                    "public_scale_counts",
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
        "workingness_drilldown": "microcosm workingness" in drilldown_text,
    }


def _state_write_boundary(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
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
    root = Path(root)
    standard = _load_standard(root)
    payload: dict[str, Any] = {
        "schema_version": "microcosm_first_screen_composition_card_v1",
        "project_label": project_label,
        "composition_root_id": standard["kind_id"],
        "source_standard_ref": str(STANDARD_REF),
        "human_first_command": f"microcosm hello {project_label}",
        "shared_first_command": f"microcosm tour --card {project_label}",
        "text_projection": {
            "command": f"microcosm hello {project_label}",
            "writes_microcosm_state": False,
            "behavioral_proof_command": f"microcosm tour --card {project_label}",
            "authority": "terminal_text_projection_only_not_behavior_proof",
            "reader_rule": (
                "Use this command to view the first-screen card; run the "
                "behavior proof command to write .microcosm state."
            ),
        },
        "reader_routes": _reader_routes(project_label),
        "reader_landing_packets": _reader_landing_packets(project_label),
        "evidence_count_frame": _evidence_count_frame(),
        "evidence_class_legend": _evidence_class_legend(root),
        "comparison_frame": _comparison_frame(),
        "doctrine_effect_frame": _doctrine_effect_frame(),
        "readme_entry_contract": _readme_entry_contract(project_label),
        "entry_surface_contract": _entry_surface_contract(project_label),
        "scale_frame": _scale_frame(root),
        "runnable_structural_join": _runnable_structural_join(project_label),
        "state_write_boundary": _state_write_boundary(project_label),
        "observatory_landing_frame": _observatory_landing_frame(project_label),
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


def _reader_packet_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    landing_packets = payload.get("reader_landing_packets", {})
    if not isinstance(landing_packets, dict):
        return {}
    return {
        str(packet.get("reader_route_id")): packet
        for packet in landing_packets.get("packets", [])
        if isinstance(packet, dict)
    }


def _reader_branch_lines(
    route_by_id: dict[str, dict[str, Any]],
    packet_by_id: dict[str, dict[str, Any]],
    reader_id: str,
) -> list[str]:
    if reader_id == "all":
        return [
            "Reader branches:",
            *[
                (
                    f"  {READER_LABELS[route_id]}: "
                    f"{packet_by_id[route_id]['first_action']} Proof: "
                    f"{packet_by_id[route_id]['proof_surface']}"
                )
                for route_id in READER_ROUTE_IDS
            ],
        ]

    route = route_by_id[reader_id]
    packet = packet_by_id[reader_id]
    return [
        f"Reader branch: {READER_LABELS[reader_id]}",
        f"  Question: {route['first_question']}",
        f"  First action: {packet['first_action']}",
        f"  Proof: {packet['proof_surface']}",
        f"  Success: {packet['success_criterion']}",
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


def _evidence_class_summary_line(payload: dict[str, Any]) -> str:
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


def first_screen_text_card(payload: dict[str, Any], *, reader_id: str = "all") -> str:
    if reader_id not in TEXT_READER_CHOICES:
        raise ValueError(f"unknown first-screen reader route: {reader_id}")
    route_by_id = _reader_route_map(payload)
    packet_by_id = _reader_packet_map(payload)
    human_first_command = payload.get(
        "human_first_command", "microcosm hello <project>"
    )
    lines = [
        "Microcosm first screen",
        (
            f"Open card: {human_first_command} | "
            f"First run: {payload['shared_first_command']}"
        ),
        "",
        "What it is:",
        "  A local evidence router, not a maturity brochure; doctrine appears as prevented mistakes; README inventory waits.",
        "",
        "Why the counts are honest:",
        _scale_summary_line(payload),
        "  Counts are receipt-backed handles, not maturity, readiness, or progress scores.",
        _evidence_class_summary_line(payload),
        "",
        *_reader_branch_lines(route_by_id, packet_by_id, reader_id),
        "",
        "Runnable-to-structural join:",
        "  This card is the map; the first run writes .microcosm and exercises the larger public substrate:",
        "  standards, receipts, authority boundaries, workingness, route maps, and observatory views.",
        "",
        "Drilldowns:",
        "  browser landing: / -> /project/first-screen -> /project/observatory-card",
        "  authority/workingness: microcosm authority / microcosm workingness",
        f"  route/contract: paper_modules/cold_reader_route_map.md / {payload['source_standard_ref']}",
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
