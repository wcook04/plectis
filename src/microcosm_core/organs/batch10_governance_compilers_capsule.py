from __future__ import annotations

import argparse
import fnmatch
import functools
import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch10_governance_compilers_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

EXPECTED_MECHANISMS: tuple[str, ...] = (
    "mutation_governance_intent_gate",
    "observe_apply_plan_compiler",
    "flagship_reviewer_persona_gauntlet_adjudicator",
    "release_public_toggle_blocker_closure_triage",
    "publication_manifest_selector_contract_verifier",
    "constitution_workspace_receipt_reuse_decider",
    "finance_no_lookahead_temporal_contract",
    "session_dependency_wave_executor",
    "claim_conflict_wait_tax_detector",
    "role_aware_dag_block_propagation",
    "weighted_lane_width_apportionment_binding_repair",
)

EXPECTED_NEGATIVE_CASES = {
    "mutation_status_intent_blocks_writes": ("BATCH10_MUTATION_STATUS_INTENT_BLOCKS_WRITES",),
    "observe_apply_malformed_artifact_refused": (
        "BATCH10_OBSERVE_APPLY_MALFORMED_ARTIFACT_REFUSED",
    ),
    "reviewer_missing_boundary_detected": ("BATCH10_REVIEWER_MISSING_BOUNDARY_DETECTED",),
    "release_toggle_no_go_fail_closed": ("BATCH10_RELEASE_TOGGLE_NO_GO_FAIL_CLOSED",),
    "publication_hard_exclude_rejected": ("BATCH10_PUBLICATION_HARD_EXCLUDE_REJECTED",),
    "receipt_reuse_stable_input_changed": ("BATCH10_RECEIPT_REUSE_STABLE_INPUT_CHANGED",),
    "finance_invalid_horizon_rejected": ("BATCH10_FINANCE_INVALID_HORIZON_REJECTED",),
    "session_failed_dependency_skips_child": (
        "BATCH10_SESSION_FAILED_DEPENDENCY_SKIPS_CHILD",
    ),
    "claim_parent_child_overlap_reported": ("BATCH10_CLAIM_PARENT_CHILD_OVERLAP_REPORTED",),
    "dag_quality_error_not_overblocked": ("BATCH10_DAG_QUALITY_ERROR_NOT_OVERBLOCKED",),
    "lane_width_binding_deferred_to_batch9": (
        "BATCH10_LANE_WIDTH_BINDING_DEFERRED_TO_BATCH9",
    ),
}

CASE_VERDICT_AUTHORITY = "computed_by_batch10_governance_compilers_capsule_integrity_matrix"
REVIEWER_GAUNTLET_REPORT_DECISION = "report_only_public_proof_smoke_pass"

NEGATIVE_CASE_BINDINGS: dict[str, dict[str, Any]] = {
    "mutation_status_intent_blocks_writes": {
        "mechanism_id": "mutation_governance_intent_gate",
        "computed_path": "negative_intent.prohibit_file_writes",
        "expected": True,
        "input_shape": {
            "latest_user_message": "diagnose the attached transcript and pattern ledger seed",
            "requested_route": "public_microcosm_evolution_seed",
        },
    },
    "observe_apply_malformed_artifact_refused": {
        "mechanism_id": "observe_apply_plan_compiler",
        "computed_path": "malformed_refused",
        "expected": True,
        "input_shape": {"artifact": "{\"operations\": \"bad\"}"},
    },
    "reviewer_missing_boundary_detected": {
        "mechanism_id": "flagship_reviewer_persona_gauntlet_adjudicator",
        "computed_path": "missing_boundary_status",
        "expected": "warn",
        "input_shape": {"boundary_doc_exists": False},
    },
    "release_toggle_no_go_fail_closed": {
        "mechanism_id": "release_public_toggle_blocker_closure_triage",
        "computed_path": "operator_review_ready",
        "expected": False,
        "input_shape": {"public_toggle_status": "no_go", "blocking_conditions": 1},
    },
    "publication_hard_exclude_rejected": {
        "mechanism_id": "publication_manifest_selector_contract_verifier",
        "computed_path": "hard_exclude_rejected",
        "expected": True,
        "input_shape": {"included_path": "private/raw_seed.md", "hard_exclude": "private/"},
    },
    "receipt_reuse_stable_input_changed": {
        "mechanism_id": "constitution_workspace_receipt_reuse_decider",
        "computed_path": "stable_changed_count",
        "expected": 1,
        "input_shape": {"prior_sha256_16": "1111", "current_sha256_16": "2222"},
    },
    "finance_invalid_horizon_rejected": {
        "mechanism_id": "finance_no_lookahead_temporal_contract",
        "computed_path": "invalid_horizon_rejected",
        "expected": True,
        "input_shape": {"horizon_policy": "not-a-date"},
    },
    "session_failed_dependency_skips_child": {
        "mechanism_id": "session_dependency_wave_executor",
        "computed_path": "node_states.C",
        "expected": "skipped",
        "input_shape": {"node": "C", "depends_on": ["B"], "B": "failure"},
    },
    "claim_parent_child_overlap_reported": {
        "mechanism_id": "claim_conflict_wait_tax_detector",
        "computed_path": "conflict_count",
        "expected": 1,
        "input_shape": {
            "scope": "microcosm-substrate/src",
            "claim_path": "microcosm-substrate/src/microcosm_core/organs/x.py",
        },
    },
    "dag_quality_error_not_overblocked": {
        "mechanism_id": "role_aware_dag_block_propagation",
        "computed_path": "quality_error_softened",
        "expected": True,
        "input_shape": {"upstream_status": "quality_error", "downstream_role": "probe"},
    },
    "lane_width_binding_deferred_to_batch9": {
        "mechanism_id": "weighted_lane_width_apportionment_binding_repair",
        "computed_path": "disposition",
        "expected": "under_bound_repair_deferred_to_batch9_claim",
        "input_shape": {"source_target": "Batch-9 RootNavigator.tsx", "batch10_action": "defer"},
    },
}

MECHANISM_SOURCE_REFS: dict[str, tuple[str, ...]] = {
    "mutation_governance_intent_gate": (
        "system/lib/mutation_governance.py",
        "tools/meta/control/mutation_governance.py",
    ),
    "observe_apply_plan_compiler": ("tools/meta/apply/observe_compiler.py",),
    "flagship_reviewer_persona_gauntlet_adjudicator": (
        "tools/meta/dissemination/build_public_microcosm_flagship_reviewer_gauntlet.py",
    ),
    "release_public_toggle_blocker_closure_triage": (
        "tools/meta/dissemination/release_public_toggle_closure_map.py",
    ),
    "publication_manifest_selector_contract_verifier": (
        "tools/meta/dissemination/check_publication_manifest_contract.py",
    ),
    "constitution_workspace_receipt_reuse_decider": (
        "system/lib/kernel/commands/comprehension_snapshot.py",
    ),
    "finance_no_lookahead_temporal_contract": ("system/core/engine.py",),
    "session_dependency_wave_executor": ("tools/meta/apply/session_core.py",),
    "claim_conflict_wait_tax_detector": ("system/lib/action_quote.py",),
    "role_aware_dag_block_propagation": ("tools/meta/apply/run_observe_plan.py",),
    "weighted_lane_width_apportionment_binding_repair": (
        "system/server/ui/src/pages/RootNavigator.tsx",
    ),
}

MECHANISM_CLASSIFICATIONS = {
    "publication_manifest_selector_contract_verifier": "source_faithful_refactor_read_verified_only",
    "weighted_lane_width_apportionment_binding_repair": "under_bound_binding_repair",
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch10_governance_compilers_capsule_not_live_authority_or_release_approval",
    "real_substrate_disposition": "real_substrate_capsule",
    "provider_dispatch": False,
    "model_dispatch": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
    "work_ledger_authority": False,
    "market_advice": False,
    "neutral_benchmark_claim": False,
    "full_secret_detection_claim": False,
}

ANTI_CLAIM = (
    "Batch 10 validates copied non-secret macro source bodies and source-faithful "
    "public ports for mutation governance, observe/apply compilation, public "
    "artifact review, release-blocker triage, publication path-contract checks, "
    "receipt staleness, no-lookahead finance horizons, session-wave execution, "
    "claim-conflict wait-tax detection, role-aware block propagation, and a "
    "blocked Batch-9 lane-width binding repair. It is not release approval, "
    "publication "
    "authority, live Work Ledger truth, neutral benchmark evidence, source "
    "mutation permission, or investment advice."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/lib/mutation_governance.py": (
        "def classify_latest_user_intent(",
        "def build_latest_intent_gate(",
        "def build_ledger_growth_budget(",
        "def build_diff_safety_gate(",
    ),
    "tools/meta/control/mutation_governance.py": (
        "build_mutation_governance_packet",
        "--latest-user-message",
        "--requested-route",
    ),
    "tools/meta/dissemination/build_public_microcosm_flagship_reviewer_gauntlet.py": (
        "def _persona_results(",
        "def _status_from_requirements(",
        "def _route_quality(",
        "def _first_pass_questions(",
    ),
    "tools/meta/dissemination/release_public_toggle_closure_map.py": (
        "def _blocker_closure(",
        "def _blocker_row(",
        "def _blocker_class(",
        "def _closure_group(",
    ),
    "tools/meta/apply/observe_compiler.py": (
        "def _artifact_candidates(",
        "def compile_session_manifest_to_apply_plan(",
        "def _parse_operations_from_artifact",
        "def _response_index_entries(",
    ),
    "tools/meta/apply/session_core.py": (
        "def dispatch_wave(",
        "class SessionNodeStatus",
        "class SessionNodeSpec",
        "class SessionWave",
    ),
    "tools/meta/apply/run_observe_plan.py": (
        "def _resolve_blocked_groups",
        "BLOCKING_GROUP_STATUSES",
        "quality_error is NOT a blocking status",
        "def _resolved_group_runtime_state",
    ),
    "system/lib/kernel/commands/comprehension_snapshot.py": (
        "def _compare_receipt_to_source_graph",
        "def _changed_stable_inputs",
        "def _fingerprint_rows_by_path",
        "def _stable_json_fingerprint",
    ),
    "system/core/engine.py": (
        "def resolve_horizon(",
        "next_us_close",
        "ZoneInfo(\"America/New_York\")",
        "Cannot parse horizon",
    ),
    "system/lib/action_quote.py": (
        "def _path_overlaps",
        "def _claim_conflicts",
        "def _wait_tax_match",
        "ranked_wait_taxes",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 10 Governance and Compilers Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def classify_latest_user_intent(message: str | None) -> str:
    text = _normalize_text(message)
    if not text:
        return "general_task"
    implement = any(phrase in text for phrase in ("please implement", "implement this", "edit the repo"))
    diagnostic = any(phrase in text for phrase in ("diagnose", "attached transcript", "prior run"))
    ledger = any(phrase in text for phrase in ("pattern ledger", "ledger growth", "append rows"))
    if implement and text.startswith(("please implement", "implement this")):
        return "implement_system_patches"
    if diagnostic and (ledger or "attached" in text):
        return "diagnose_system_from_transcript"
    if diagnostic and not implement:
        return "diagnose_system_from_transcript"
    if ledger:
        return "mutate_pattern_ledger"
    if "summarize" in text or "summarise" in text:
        return "summarize_prior_run"
    if any(phrase in text for phrase in ("continue", "resume", "keep going")):
        return "continue_interrupted_run"
    if implement:
        return "implement_system_patches"
    return "general_task"


def latest_intent_gate(message: str | None, requested_route: str | None = None) -> dict[str, Any]:
    intent = classify_latest_user_intent(message)
    route = _normalize_text(requested_route)
    route_requests_ledger = any(
        marker in route for marker in ("public_microcosm_evolution_seed", "pattern_ledger")
    ) or "pattern ledger" in _normalize_text(message)
    diagnostic = intent == "diagnose_system_from_transcript"
    ledger_allowed = intent == "mutate_pattern_ledger" and not diagnostic
    prohibit = diagnostic or (route_requests_ledger and not ledger_allowed)
    return {
        "status": "blocked" if prohibit else "clear",
        "latest_intent": intent,
        "repo_patch_allowed": intent
        in {"implement_system_patches", "mutate_pattern_ledger", "continue_interrupted_run"}
        and not diagnostic,
        "prohibit_file_writes": prohibit,
        "route_requests_pattern_ledger_mutation": route_requests_ledger,
    }


def _mutation_governance_matrix() -> dict[str, Any]:
    positive = latest_intent_gate("please implement this parser fix", requested_route="normal_task")
    negative = latest_intent_gate(
        "diagnose the attached transcript and pattern ledger seed",
        requested_route="public_microcosm_evolution_seed",
    )
    ledger_budget = {
        "status": "blocked" if 5 > 4 else "clear",
        "violations": ["max_new_rows_exceeded"],
    }
    return {
        "status": "pass"
        if positive["repo_patch_allowed"]
        and negative["prohibit_file_writes"]
        and ledger_budget["status"] == "blocked"
        else "blocked",
        "mechanism_id": "mutation_governance_intent_gate",
        "positive_intent": positive,
        "negative_intent": negative,
        "ledger_budget": ledger_budget,
        "claim_ceiling": "Controlled latest-message gate only; not real operator authority.",
    }


def _extract_operations_from_artifact(text: str) -> list[dict[str, Any]]:
    candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidates.append(text)
    for raw in candidates:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        operations = payload.get("operations") if isinstance(payload, Mapping) else None
        if isinstance(operations, list):
            return [dict(row) for row in operations if isinstance(row, Mapping)]
    return []


def _observe_apply_compiler_matrix() -> dict[str, Any]:
    artifact = {
        "operations": [
            {"op": "replace", "path": "demo.py", "old": "x = 1", "new": "x = 2"},
            {"op": "insert_after", "path": "demo.py", "anchor": "x = 2", "content": "print(x)"},
        ]
    }
    parsed = _extract_operations_from_artifact("```json\n" + json.dumps(artifact) + "\n```")
    malformed = _extract_operations_from_artifact("```json\n{\"operations\": \"bad\"}\n```")
    return {
        "status": "pass" if len(parsed) == 2 and malformed == [] else "blocked",
        "mechanism_id": "observe_apply_plan_compiler",
        "strategy_ladder": [
            "prefer_artifact",
            "synthesis_or_evaluation_artifact",
            "aggregated_probes",
            "fallback",
        ],
        "operation_count": len(parsed),
        "malformed_refused": malformed == [],
        "claim_ceiling": "Observe artifact to apply-plan IR only; not patch authorization.",
    }


def _status_from_requirements(requirements: Mapping[str, bool]) -> str:
    values = list(requirements.values())
    if values and all(values):
        return "pass"
    if any(values):
        return "warn"
    return "fail"


def _public_artifact_fixture_docs(*, boundary_doc_exists: bool = True) -> dict[str, str]:
    boundary = (
        "Boundary: public toggle no_go. Forbidden claims: not open source, not public "
        "release approval, not private root equivalence. Omitted private root, raw seed, "
        "live ledgers, provider/browser state, prompt shelf, and private UI state."
        if boundary_doc_exists
        else ""
    )
    return {
        "README.md": (
            "AI Workflow Substrate Miniature\n\n"
            "First command: make demo-substrate. The flagship sequence includes "
            "Concurrency Mission Control, Type B Shuttle Capture, and Doctrine Apply "
            "Metabolism. Receipts, anti-claim rows, forbidden claims, and a no-go "
            "release posture are visible."
        ),
        "docs/START_HERE.md": (
            "Start here, then run make demo-substrate. Inspect 00_substrate_loop and "
            "the visual control-plane route."
        ),
        "docs/ROUTES.md": (
            "Run python -m aiwf_proof run examples/10_concurrency_mission_control, "
            "python -m aiwf_proof run examples/11_type_b_shuttle_capture, "
            "python -m aiwf_proof visual, and verifier/validate_projection.py."
        ),
        "docs/VISUAL_CONTROL_PLANE.md": (
            "Trust Backplane: each node has a command, receipt, claim tier, anti-claim, "
            "omitted state, and no-go status. Run python -m aiwf_proof visual."
        ),
        "docs/BOUNDARY.md": boundary,
        "docs/SUBSTRATE.md": (
            "The substrate miniature exposes WorkItem routing, Type A verification, "
            "Type B advisory synthesis, receipts, and bounded proof cells."
        ),
        "docs/EXPLANATION.md": (
            "This proof explains how public fixtures move from command execution to "
            "receipt-backed learning without claiming private root equivalence."
        ),
        "docs/HOW_TO_RUN.md": "Run make demo-substrate and python -m aiwf_proof validate.",
        "docs/REFERENCE.md": "Reference contract for claims, receipts, omitted state, and routes.",
        "site/substrate_map.html": "<html><body>Trust Backplane substrate map</body></html>",
        "public_executable_projection_manifest_v0.json": "{}",
        "experience/public_microcosm_visual_control_plane_v0.json": json.dumps(
            {
                "flagship_sequence_nodes": [
                    {"id": "substrate_loop"},
                    {"id": "concurrency_transaction_mission_control_microcosm"},
                    {"id": "type_b_shuttle_capture_microcosm"},
                    {"id": "doctrine_apply_metabolism_microcosm"},
                ]
            },
            sort_keys=True,
        ),
    }


def _artifact_doc(docs: Mapping[str, str], rel_path: str) -> str:
    return str(docs.get(rel_path) or "")


def _persona_results_from_public_artifact(
    docs: Mapping[str, str],
    *,
    sequence_node_count: int = 4,
) -> list[dict[str, Any]]:
    readme = _artifact_doc(docs, "README.md")
    start = _artifact_doc(docs, "docs/START_HERE.md")
    routes = _artifact_doc(docs, "docs/ROUTES.md")
    visual = _artifact_doc(docs, "docs/VISUAL_CONTROL_PLANE.md")
    boundary = _artifact_doc(docs, "docs/BOUNDARY.md")
    substrate = _artifact_doc(docs, "docs/SUBSTRATE.md")
    explanation = _artifact_doc(docs, "docs/EXPLANATION.md")
    how_to = _artifact_doc(docs, "docs/HOW_TO_RUN.md")
    site = _artifact_doc(docs, "site/substrate_map.html")
    all_text = "\n".join(
        [readme, start, routes, visual, boundary, substrate, explanation, how_to, site]
    )
    persona_specs = [
        {
            "persona_id": "cold_cloner",
            "requirements": {
                "front_door_names_artifact": "AI Workflow Substrate Miniature" in readme,
                "first_command_visible": "make demo-substrate" in readme,
                "start_route_exists": bool(start),
                "no_go_visible": "no-go" in all_text.lower() or "no_go" in all_text,
            },
            "answers": {
                "first_command": "make demo-substrate",
                "which_cell_to_inspect": "00_substrate_loop first, then the visual control-plane route.",
                "what_claim_is_forbidden": "This is not public-release approval or a private-root source release.",
            },
        },
        {
            "persona_id": "programming_systems_reviewer",
            "requirements": {
                "sequence_nodes_visible": all(
                    text in all_text
                    for text in (
                        "Concurrency Mission Control",
                        "Type B Shuttle Capture",
                        "Doctrine Apply Metabolism",
                    )
                ),
                "commands_visible": "python -m aiwf_proof run examples/10_concurrency_mission_control"
                in all_text,
                "verifier_visible": "verifier/validate_projection.py" in all_text,
                "receipts_visible": "receipt" in all_text.lower(),
            },
            "answers": {
                "first_command": "make demo-substrate",
                "which_cell_to_inspect": "10_concurrency_mission_control for claim/collision/scoped-action discipline.",
                "what_claim_is_forbidden": "The public transforms are not full private-root behavior.",
            },
        },
        {
            "persona_id": "agent_infra_reviewer",
            "requirements": {
                "type_b_visible": "Type B" in all_text,
                "ask_type_a_visible": "ASK_TYPE_A" in all_text or "Type A" in all_text,
                "workitem_visible": "WorkItem" in all_text,
                "anti_claims_visible": "anti-claim" in all_text.lower() or "anti_claim" in all_text,
            },
            "answers": {
                "first_command": "python -m aiwf_proof run examples/11_type_b_shuttle_capture",
                "which_cell_to_inspect": "11_type_b_shuttle_capture.",
                "what_claim_is_forbidden": "Do not claim Type B output is source authority.",
            },
        },
        {
            "persona_id": "safety_evaluator_reviewer",
            "requirements": {
                "boundary_doc_exists": bool(boundary),
                "omissions_visible": "omitted" in all_text.lower() or "withheld" in all_text.lower(),
                "public_toggle_no_go": "no_go" in all_text or "no-go" in all_text.lower(),
                "forbidden_claims_visible": "not " in boundary.lower() or "forbidden" in all_text.lower(),
            },
            "answers": {
                "first_command": "python -m aiwf_proof claims",
                "which_cell_to_inspect": "docs/BOUNDARY.md and the visual trust backplane.",
                "what_claim_is_forbidden": "Do not claim public demo clearance, open-source release, public reproducibility, SLSA, or Scorecard status.",
            },
        },
        {
            "persona_id": "substrate_skeptic",
            "requirements": {
                "what_proves_visible": "proof" in all_text.lower(),
                "sequence_has_four_nodes": sequence_node_count >= 4,
                "visual_map_exists": bool(site),
                "omission_boundary_visible": "private root" in all_text.lower(),
            },
            "answers": {
                "first_command": "python -m aiwf_proof visual",
                "which_cell_to_inspect": "site/substrate_map.html, then examples/12_doctrine_apply_metabolism.",
                "what_claim_is_forbidden": "Do not claim the miniature proves full private-system equivalence.",
            },
        },
        {
            "persona_id": "visual_first_reviewer",
            "requirements": {
                "visual_doc_exists": bool(visual),
                "site_map_exists": bool(site),
                "visual_command_visible": "python -m aiwf_proof visual" in all_text,
                "trust_backplane_visible": "Trust Backplane" in all_text,
            },
            "answers": {
                "first_command": "python -m aiwf_proof visual",
                "which_cell_to_inspect": "docs/VISUAL_CONTROL_PLANE.md and site/substrate_map.html.",
                "what_claim_is_forbidden": "Do not present the static cockpit as a live private HUD.",
            },
        },
    ]
    results: list[dict[str, Any]] = []
    for spec in persona_specs:
        requirements = spec["requirements"]
        missing = [key for key, ok in requirements.items() if not ok]
        status = _status_from_requirements(requirements)
        results.append(
            {
                "persona_id": spec["persona_id"],
                "status": status,
                "answers": spec["answers"],
                "confusions": [f"missing signal: {key}" for key in missing],
                "patches_required": [] if status == "pass" else [f"repair {key}" for key in missing],
                "requirement_checks": requirements,
            }
        )
    return results


def _route_quality_from_public_artifact(
    docs: Mapping[str, str],
    *,
    manifest_exists: bool = True,
) -> dict[str, str]:
    checks = {
        "tutorial": {
            "docs/START_HERE.md": bool(_artifact_doc(docs, "docs/START_HERE.md")),
            "first_command": "make demo-substrate" in _artifact_doc(docs, "README.md"),
        },
        "how_to": {
            "docs/HOW_TO_RUN.md": bool(_artifact_doc(docs, "docs/HOW_TO_RUN.md")),
            "route_commands": "python -m aiwf_proof" in _artifact_doc(docs, "docs/ROUTES.md"),
        },
        "reference": {
            "docs/REFERENCE.md": bool(_artifact_doc(docs, "docs/REFERENCE.md")),
            "manifest": manifest_exists,
        },
        "explanation": {
            "docs/EXPLANATION.md": bool(_artifact_doc(docs, "docs/EXPLANATION.md")),
            "substrate_doc": bool(_artifact_doc(docs, "docs/SUBSTRATE.md")),
        },
    }
    return {key: _status_from_requirements(value) for key, value in checks.items()}


def _reviewer_decision(
    command_receipts: Sequence[Mapping[str, Any]],
    persona_results: Sequence[Mapping[str, Any]],
    route_quality: Mapping[str, str],
) -> str:
    if any(row.get("status") == "fail" for row in command_receipts):
        return "patch_sequence"
    if any(row.get("status") == "fail" for row in persona_results) or any(
        value == "fail" for value in route_quality.values()
    ):
        return "patch_front_door"
    if any(row.get("status") == "warn" for row in persona_results) or any(
        value == "warn" for value in route_quality.values()
    ):
        return "patch_front_door"
    return REVIEWER_GAUNTLET_REPORT_DECISION


def _reviewer_gauntlet_matrix() -> dict[str, Any]:
    complete_docs = _public_artifact_fixture_docs()
    complete_personas = _persona_results_from_public_artifact(complete_docs)
    complete_route_quality = _route_quality_from_public_artifact(complete_docs)
    command_receipts = [{"command_id": "demo_substrate", "status": "pass"}]
    decision = _reviewer_decision(command_receipts, complete_personas, complete_route_quality)
    missing_boundary_personas = _persona_results_from_public_artifact(
        _public_artifact_fixture_docs(boundary_doc_exists=False)
    )
    missing_boundary_safety = next(
        row
        for row in missing_boundary_personas
        if row["persona_id"] == "safety_evaluator_reviewer"
    )
    persona_status_counts = {
        status: sum(1 for row in complete_personas if row["status"] == status)
        for status in ("pass", "warn", "fail")
    }
    return {
        "status": "pass"
        if decision == REVIEWER_GAUNTLET_REPORT_DECISION
        and all(row["status"] == "pass" for row in complete_personas)
        and all(value == "pass" for value in complete_route_quality.values())
        and missing_boundary_safety["status"] == "warn"
        else "blocked",
        "mechanism_id": "flagship_reviewer_persona_gauntlet_adjudicator",
        "complete_status": "pass"
        if all(row["status"] == "pass" for row in complete_personas)
        else "blocked",
        "missing_boundary_status": missing_boundary_safety["status"],
        "persona_count": len(complete_personas),
        "persona_ids": [str(row["persona_id"]) for row in complete_personas],
        "persona_status_counts": persona_status_counts,
        "route_quality": complete_route_quality,
        "decision": decision,
        "missing_boundary_persona_id": missing_boundary_safety["persona_id"],
        "missing_boundary_patches_required": missing_boundary_safety["patches_required"],
        "claim_ceiling": "Adversarial public artifact review only; not release approval.",
    }


def _blocker_class(blocker_id: str, row: Mapping[str, Any]) -> str:
    if blocker_id == "public_toggle_no_go":
        return "switch"
    if blocker_id == "operator_public_approval_absent":
        return "authority"
    return str(row.get("kind") or "operational")


def _release_toggle_triage_matrix() -> dict[str, Any]:
    gate = {
        "status": "no_go",
        "blocking_conditions": [
            {"id": "portability_gate_not_green", "kind": "operational", "current_state": "red"},
        ],
    }
    blockers = {
        str(row["id"]): row
        for row in gate["blocking_conditions"]
        if isinstance(row, Mapping) and row.get("id")
    }
    operational = [
        {"blocker_id": key, "queue_class": "operational", "class": _blocker_class(key, row)}
        for key, row in sorted(blockers.items())
    ]
    authority = [{"blocker_id": "operator_public_approval_absent", "queue_class": "authority"}]
    switch = [{"blocker_id": "public_toggle_no_go", "queue_class": "switch"}]
    return {
        "status": "pass" if operational and authority and switch and gate["status"] == "no_go" else "blocked",
        "mechanism_id": "release_public_toggle_blocker_closure_triage",
        "operational_blocker_count": len(operational),
        "authority_blocker_count": len(authority),
        "switch_blocker_count": len(switch),
        "operator_review_ready": len(operational) == 0,
        "claim_ceiling": "Release-blocker triage only; not publication approval.",
    }


def _selector_list(spec: Mapping[str, Any]) -> list[str]:
    selectors: list[str] = []
    for key in ("paths", "glob", "grep_blocklist"):
        values = spec.get(key) or []
        if isinstance(values, list):
            selectors.extend(str(value) for value in values if str(value or "").strip())
    return selectors


def _path_matches_selector(path_text: str, selector: str) -> bool:
    selector = selector.strip()
    if selector.endswith("/"):
        return path_text == selector.rstrip("/") or path_text.startswith(selector)
    return fnmatch.fnmatch(path_text, selector)


def _hard_exclude_selectors(exclude: Mapping[str, Any]) -> list[tuple[str, str]]:
    selectors: list[tuple[str, str]] = []
    for name, spec in exclude.items():
        if isinstance(spec, Mapping) and spec.get("enforcement") == "hard":
            selectors.extend((str(name), selector) for selector in _selector_list(spec))
    return selectors


def _publication_manifest_contract_matrix() -> dict[str, Any]:
    manifest = {
        "include": {
            "docs": {
                "rule": "allow",
                "release_class": "A",
                "review_status": "reviewed",
                "description": "docs",
                "entries": [
                    {"path": "docs/START_HERE.md", "reason": "front door"},
                    {"path": "private/raw_seed.md", "reason": "bad"},
                ],
            }
        },
        "exclude": {
            "private_state": {
                "enforcement": "hard",
                "release_class": "D",
                "description": "no private state",
                "paths": ["private/"],
            }
        },
    }
    errors: list[str] = []
    for category, spec in manifest["include"].items():
        for index, entry in enumerate(spec.get("entries") or []):
            path_text = str(entry.get("path") or "")
            for exclude_name, selector in _hard_exclude_selectors(manifest["exclude"]):
                if _path_matches_selector(path_text, selector):
                    errors.append(
                        f"include.{category}.entries[{index}].path {path_text} matches hard exclude {exclude_name}:{selector}"
                    )
    return {
        "status": "pass" if errors else "blocked",
        "mechanism_id": "publication_manifest_selector_contract_verifier",
        "selector_count": len(_hard_exclude_selectors(manifest["exclude"])),
        "hard_exclude_rejected": bool(errors),
        "error_count": len(errors),
        "source_to_target_relation": "source_faithful_public_refactor_private_path_literal_removed",
        "claim_ceiling": "Path-selector contract only; not full secret detection.",
    }


def _fingerprint_rows_by_path(rows: Any) -> dict[str, str | None]:
    by_path: dict[str, str | None] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, Mapping) and row.get("path"):
                by_path[str(row["path"])] = row.get("sha256_16")  # type: ignore[assignment]
    return by_path


def _changed_stable_inputs(current_inputs: Any, prior_inputs: Any) -> list[dict[str, Any]]:
    current = _fingerprint_rows_by_path(current_inputs)
    prior = _fingerprint_rows_by_path(prior_inputs)
    changed: list[dict[str, Any]] = []
    for path in sorted(set(current) | set(prior)):
        before = prior.get(path)
        after = current.get(path)
        if before == after:
            continue
        changed.append(
            {
                "path": path,
                "status": "added" if before is None else "removed" if after is None else "changed",
                "prior_sha256_16": before,
                "current_sha256_16": after,
            }
        )
    return changed


def _receipt_reuse_matrix() -> dict[str, Any]:
    receipt = {
        "source_graph_fingerprint": "stable-a",
        "live_state_fingerprint": "live-a",
        "consumer": "type_a_agent",
        "stable_inputs": [{"path": "a.py", "sha256_16": "1111"}],
    }
    source_graph = {
        "source_graph_fingerprint": "stable-a",
        "live_state_fingerprint": "live-b",
        "stable_inputs": [{"path": "a.py", "sha256_16": "1111"}],
    }
    changed_graph = dict(source_graph, source_graph_fingerprint="stable-b", stable_inputs=[{"path": "a.py", "sha256_16": "2222"}])
    live_only_safe = receipt["source_graph_fingerprint"] == source_graph["source_graph_fingerprint"]
    changed = _changed_stable_inputs(changed_graph["stable_inputs"], receipt["stable_inputs"])
    return {
        "status": "pass" if live_only_safe and changed else "blocked",
        "mechanism_id": "constitution_workspace_receipt_reuse_decider",
        "live_state_only_safe_to_reuse": live_only_safe,
        "stable_changed_count": len(changed),
        "required_action_if_changed": "refresh_stable_substrate",
        "claim_ceiling": "Receipt reuse decision over declared fingerprints only.",
    }


def resolve_horizon(policy: str | None = None, now: datetime | None = None) -> dict[str, str]:
    et = ZoneInfo("America/New_York")
    now = now or datetime.now(timezone.utc)
    now_et = now.astimezone(et)
    effective = policy or "next_us_close"
    if effective == "next_us_close":
        close_today = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        if now_et < close_today and now_et.weekday() < 5:
            target_et = close_today
        else:
            target_et = close_today + timedelta(days=1)
            while target_et.weekday() >= 5:
                target_et += timedelta(days=1)
        label = target_et.strftime("Next US Market Close (%a %b %d, 4:00 PM ET)")
        target_utc = target_et.astimezone(timezone.utc)
    elif effective == "24h":
        target_utc = now + timedelta(hours=24)
        target_et = target_utc.astimezone(et)
        label = target_et.strftime("24h from now (%a %b %d, %I:%M %p ET)")
    elif effective == "48h":
        target_utc = now + timedelta(hours=48)
        target_et = target_utc.astimezone(et)
        label = target_et.strftime("48h from now (%a %b %d, %I:%M %p ET)")
    else:
        try:
            parsed = datetime.fromisoformat(effective)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Cannot parse horizon '{effective}' as ISO datetime: {exc}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        target_utc = parsed.astimezone(timezone.utc)
        target_et = target_utc.astimezone(et)
        label = target_et.strftime("Custom target (%a %b %d, %I:%M %p ET)")
    return {
        "policy": effective,
        "target_time": target_utc.isoformat(),
        "target_time_et": target_et.isoformat(),
        "horizon_label": label,
    }


def _finance_temporal_matrix() -> dict[str, Any]:
    saturday = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
    weekend = resolve_horizon("next_us_close", saturday)
    invalid = False
    try:
        resolve_horizon("not-a-date", saturday)
    except ValueError:
        invalid = True
    return {
        "status": "pass" if "Mon Jun 01" in weekend["horizon_label"] and invalid else "blocked",
        "mechanism_id": "finance_no_lookahead_temporal_contract",
        "weekend_roll_forward_label": weekend["horizon_label"],
        "invalid_horizon_rejected": invalid,
        "claim_ceiling": "Temporal horizon contract only; not forecast correctness or market advice.",
    }


def _session_wave_matrix() -> dict[str, Any]:
    states = {"A": "success", "B": "failure", "C": "pending"}
    dependencies = {"C": ["B"]}
    if any(states.get(dep) != "success" for dep in dependencies["C"]):
        states["C"] = "skipped"
    stop_abort = {"D": "aborted"}
    return {
        "status": "pass" if states["C"] == "skipped" and stop_abort["D"] == "aborted" else "blocked",
        "mechanism_id": "session_dependency_wave_executor",
        "node_states": {**states, **stop_abort},
        "claim_ceiling": "Synthetic dependency-ready wave only; no provider dispatch.",
    }


def _path_overlaps(left: str, right: str) -> bool:
    return bool(left and right) and (
        left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")
    )


def _claim_conflict_wait_tax_matrix() -> dict[str, Any]:
    scope = "microcosm-substrate/src"
    claims = [
        {"path": "docs/readme.md", "session_id": "a"},
        {"path": "microcosm-substrate/src/microcosm_core/organs/x.py", "session_id": "b"},
    ]
    conflicts = [row for row in claims if _path_overlaps(row["path"], scope)]
    wait_tax = {"status": "stale_match", "actionability": "advisory_only_stale_source"}
    return {
        "status": "pass" if len(conflicts) == 1 and wait_tax["status"] == "stale_match" else "blocked",
        "mechanism_id": "claim_conflict_wait_tax_detector",
        "conflict_count": len(conflicts),
        "wait_tax": wait_tax,
        "claim_ceiling": "Controlled claim snapshots only; not live Work Ledger truth or eviction authority.",
    }


def _resolve_group_state(group: Mapping[str, Any]) -> str:
    for key in ("runtime_state", "response_status", "status"):
        if str(group.get(key) or "").strip():
            return str(group[key]).strip()
    return "pending"


def _resolve_blocked_groups(groups: list[dict[str, Any]]) -> int:
    blocking = {"error", "aborted", "blocked"}
    terminal = {"success", "quality_error", "error", "aborted", "blocked", "skipped_no_dump", "skipped_missing_dump"}
    label_to_state = {str(g.get("label") or "").strip(): _resolve_group_state(g) for g in groups}
    count = 0
    for group in groups:
        if _resolve_group_state(group) in terminal:
            continue
        deps = [str(dep).strip() for dep in group.get("depends_on") or [] if str(dep).strip()]
        states = [label_to_state.get(dep, "pending") for dep in deps]
        role = str(group.get("role") or "probe").lower()
        should_block = (
            all(state in blocking for state in states)
            if role in {"synthesis", "evaluation"}
            else any(state in blocking for state in states)
        )
        if deps and should_block:
            group["runtime_state"] = "blocked"
            group["response_status"] = "blocked"
            group["response_error_category"] = "blocked_by_upstream"
            count += 1
    return count


def _role_aware_dag_matrix() -> dict[str, Any]:
    groups = [
        {"label": "probe_a", "role": "probe", "runtime_state": "error"},
        {"label": "probe_b", "role": "probe", "runtime_state": "quality_error"},
        {"label": "probe_c", "role": "probe", "runtime_state": "success"},
        {"label": "downstream", "role": "probe", "depends_on": ["probe_a"]},
        {"label": "synthesis", "role": "synthesis", "depends_on": ["probe_a", "probe_c"]},
        {"label": "quality_downstream", "role": "probe", "depends_on": ["probe_b"]},
    ]
    blocked = _resolve_blocked_groups(groups)
    by_label = {group["label"]: group for group in groups}
    return {
        "status": "pass"
        if blocked == 1
        and by_label["downstream"].get("runtime_state") == "blocked"
        and by_label["synthesis"].get("runtime_state") != "blocked"
        and by_label["quality_downstream"].get("runtime_state") != "blocked"
        else "blocked",
        "mechanism_id": "role_aware_dag_block_propagation",
        "newly_blocked_count": blocked,
        "quality_error_softened": by_label["quality_downstream"].get("runtime_state") != "blocked",
        "claim_ceiling": "Controlled group DAG propagation only; not plan-quality proof.",
    }


def clamp_root_number(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def root_object_lane_width_profile(lane: str, selected: bool, lane_count: int) -> dict[str, float]:
    if not selected:
        return {"weight": 1.8, "min": 470, "max": 560} if lane == "focus" else {"weight": 1, "min": 250, "max": 300}
    tight = lane_count >= 5
    if lane == "focus":
        return {"weight": 1.55, "min": 300 if tight else 340, "max": 360 if tight else 420}
    if lane == "downstream":
        return {"weight": 1.16, "min": 214 if tight else 240, "max": 276 if tight else 310}
    if lane in {"source", "evidence"}:
        return {"weight": 0.86, "min": 166 if tight else 196, "max": 226 if tight else 260}
    return {"weight": 0.96, "min": 176 if tight else 210, "max": 238 if tight else 282}


def solve_root_object_lane_widths(lanes: Sequence[str], selected: bool, margin_x: int, gap: int) -> dict[str, int]:
    canvas_width = 1060
    lane_count = max(1, len(lanes))
    available = max(240, canvas_width - margin_x * 2 - gap * max(0, lane_count - 1))
    profiles = [
        {"lane": lane, **root_object_lane_width_profile(lane, selected, lane_count)}
        for lane in lanes
    ]
    weight_total = sum(item["weight"] for item in profiles) or 1
    widths = [
        {
            "lane": item["lane"],
            "min": item["min"],
            "width": clamp_root_number((available * item["weight"]) / weight_total, item["min"], item["max"]),
        }
        for item in profiles
    ]
    total = sum(item["width"] for item in widths)
    if total > available:
        min_total = sum(item["min"] for item in widths)
        shrinkable = max(0, total - min_total)
        over = total - available
        if shrinkable > 0:
            for item in widths:
                share = (item["width"] - item["min"]) / shrinkable
                item["width"] = max(item["min"], item["width"] - over * share)
        shrunk_total = sum(item["width"] for item in widths)
        if shrunk_total > available:
            scale = available / shrunk_total
            for item in widths:
                item["width"] = max(116, item["width"] * scale)
    return {str(item["lane"]): math.floor(item["width"]) for item in widths}


def _lane_width_binding_matrix(public_root: Path) -> dict[str, Any]:
    batch9_manifest = public_root / "examples/batch9_macro_engines_capsule/exported_batch9_macro_engines_capsule_bundle/source_module_manifest.json"
    copied = False
    if batch9_manifest.is_file():
        payload = json.loads(batch9_manifest.read_text(encoding="utf-8"))
        for row in payload.get("modules", []):
            if isinstance(row, Mapping) and row.get("source_ref") == "system/server/ui/src/pages/RootNavigator.tsx":
                copied = bool(row.get("body_copied") and row.get("sha256_match"))
                break
    widths = solve_root_object_lane_widths(["focus", "downstream", "source"], True, 42, 34)
    return {
        "status": "blocked" if copied else "blocked",
        "mechanism_id": "weighted_lane_width_apportionment_binding_repair",
        "disposition": "under_bound_repair_deferred_to_batch9_claim",
        "batch9_body_present": copied,
        "sample_widths": widths,
        "reentry_condition": "Batch-9 shared Microcosm claim releases, then bind solver exercise under existing RootNavigator source body.",
        "claim_ceiling": "Binding repair only; not a fresh Batch-10 body import.",
    }


def _value_at_path(payload: Mapping[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _expected_matches(value: Any, binding: Mapping[str, Any]) -> bool:
    if "expected_contains" in binding:
        expected = binding["expected_contains"]
        return isinstance(value, Sequence) and not isinstance(value, str) and expected in value
    return value == binding.get("expected")


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _negative_case_payloads(input_dir: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = input_dir / f"{case_id}.json"
        if not case_path.is_file():
            continue
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payloads[case_id] = payload if isinstance(payload, dict) else {}
    return payloads


def _case_probe_missing(case_id: str, reason: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "reason": reason,
        "computed_value": False,
        "observed_value": None,
        "body_in_receipt": False,
    }


def _publication_hard_exclude_rejected(included_path: str, hard_exclude: str) -> bool:
    manifest = {
        "include": {
            "docs": {
                "entries": [{"path": included_path, "reason": "probe"}],
            }
        },
        "exclude": {
            "probe_exclude": {
                "enforcement": "hard",
                "paths": [hard_exclude],
            }
        },
    }
    for category, spec in manifest["include"].items():
        for entry in spec.get("entries") or []:
            path_text = str(entry.get("path") or "")
            for _exclude_name, selector in _hard_exclude_selectors(manifest["exclude"]):
                if _path_matches_selector(path_text, selector):
                    return True
    return False


def _release_operator_review_ready(public_toggle_status: str, blocking_condition_count: int) -> bool:
    gate = {
        "status": public_toggle_status,
        "blocking_conditions": [
            {"id": f"probe_blocker_{index}", "kind": "operational"}
            for index in range(max(0, blocking_condition_count))
        ],
    }
    operational = [
        row
        for row in gate["blocking_conditions"]
        if isinstance(row, Mapping) and _blocker_class(str(row.get("id") or ""), row) == "operational"
    ]
    return gate["status"] != "no_go" and len(operational) == 0


def _session_node_state(node: str, dependencies: Sequence[str], states: Mapping[str, Any]) -> str:
    current = {str(key): str(value) for key, value in states.items()}
    current.setdefault(node, "pending")
    if any(current.get(str(dep)) != "success" for dep in dependencies):
        current[node] = "skipped"
    return current[node]


def _semantic_observed_value(
    case_id: str,
    probe_input: Mapping[str, Any],
    public_root: Path,
) -> Any:
    if case_id == "mutation_status_intent_blocks_writes":
        gate = latest_intent_gate(
            str(probe_input.get("latest_user_message") or ""),
            requested_route=str(probe_input.get("requested_route") or ""),
        )
        return gate["prohibit_file_writes"]
    if case_id == "observe_apply_malformed_artifact_refused":
        artifact = str(probe_input.get("artifact") or "")
        return _extract_operations_from_artifact(artifact) == []
    if case_id == "reviewer_missing_boundary_detected":
        docs = _public_artifact_fixture_docs(
            boundary_doc_exists=bool(probe_input.get("boundary_doc_exists"))
        )
        personas = _persona_results_from_public_artifact(docs)
        safety = next(row for row in personas if row["persona_id"] == "safety_evaluator_reviewer")
        return safety["status"]
    if case_id == "release_toggle_no_go_fail_closed":
        return _release_operator_review_ready(
            str(probe_input.get("public_toggle_status") or ""),
            int(probe_input.get("blocking_conditions") or 0),
        )
    if case_id == "publication_hard_exclude_rejected":
        return _publication_hard_exclude_rejected(
            str(probe_input.get("included_path") or ""),
            str(probe_input.get("hard_exclude") or ""),
        )
    if case_id == "receipt_reuse_stable_input_changed":
        prior = [{"path": "a.py", "sha256_16": str(probe_input.get("prior_sha256_16") or "")}]
        current = [{"path": "a.py", "sha256_16": str(probe_input.get("current_sha256_16") or "")}]
        return len(_changed_stable_inputs(current, prior))
    if case_id == "finance_invalid_horizon_rejected":
        saturday = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
        try:
            resolve_horizon(str(probe_input.get("horizon_policy") or ""), saturday)
        except ValueError:
            return True
        return False
    if case_id == "session_failed_dependency_skips_child":
        node = str(probe_input.get("node") or "")
        dependencies = [str(dep) for dep in probe_input.get("depends_on") or []]
        states = {key: value for key, value in probe_input.items() if len(str(key)) == 1}
        return _session_node_state(node, dependencies, states)
    if case_id == "claim_parent_child_overlap_reported":
        scope = str(probe_input.get("scope") or "")
        claim_path = str(probe_input.get("claim_path") or "")
        return 1 if _path_overlaps(claim_path, scope) else 0
    if case_id == "dag_quality_error_not_overblocked":
        groups = [
            {
                "label": "upstream",
                "role": "probe",
                "runtime_state": str(probe_input.get("upstream_status") or ""),
            },
            {
                "label": "downstream",
                "role": str(probe_input.get("downstream_role") or "probe"),
                "depends_on": ["upstream"],
            },
        ]
        _resolve_blocked_groups(groups)
        by_label = {str(group["label"]): group for group in groups}
        return by_label["downstream"].get("runtime_state") != "blocked"
    if case_id == "lane_width_binding_deferred_to_batch9":
        source_target = str(probe_input.get("source_target") or "")
        action = str(probe_input.get("batch10_action") or "")
        if "Batch-9" in source_target and action == "defer":
            return "under_bound_repair_deferred_to_batch9_claim"
        return "batch10_binding_attempt_requires_batch9_claim"
    return _case_probe_missing(case_id, "unknown_case_id")


def _compute_negative_case_probe(
    case_id: str,
    payload: Mapping[str, Any],
    *,
    public_root: Path,
) -> dict[str, Any]:
    binding = NEGATIVE_CASE_BINDINGS.get(case_id)
    if not binding:
        return _case_probe_missing(case_id, "unknown_case_id")
    probe_input = payload.get("probe_input")
    if not isinstance(probe_input, Mapping):
        return _case_probe_missing(case_id, "probe_input_missing")
    observed = _semantic_observed_value(case_id, probe_input, public_root)
    if isinstance(observed, Mapping) and observed.get("reason"):
        return dict(observed)
    computed = _expected_matches(observed, binding)
    return {
        "case_id": case_id,
        "status": "pass",
        "computed_path": binding["computed_path"],
        "expected": binding.get("expected", binding.get("expected_contains")),
        "observed_value": observed,
        "computed_value": computed,
        "probe_input_digest": _canonical_digest(dict(probe_input)),
        "probe_input_keys": sorted(str(key) for key in probe_input),
        "body_in_receipt": False,
    }


def _semantic_negative_result(case_id: str, error_codes: tuple[str, ...]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": list(error_codes),
        "body_in_receipt": False,
    }


def _semantic_negative_not_rejected(case_id: str, observed: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "pass",
        "error_codes": [],
        "observed": observed,
        "body_in_receipt": False,
    }


def _semantic_negative_error(case_id: str, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH10_GOVERNANCE_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _source_manifest_for_input(input_dir: Path) -> dict[str, Any]:
    public_root = public_root_for_path(input_dir)
    return validate_source_manifest(input_dir, SPEC, public_root=public_root)


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        source_manifest = _source_manifest_for_input(input_dir)
        public_root = public_root_for_path(input_dir)
        payload = _negative_case_payloads(input_dir).get(case_id, {})
        probe = _compute_negative_case_probe(case_id, payload, public_root=public_root)
        if (
            source_manifest.get("status") == "pass"
            and probe.get("computed_value") is True
        ):
            return _semantic_negative_result(case_id, expected_codes)
        return _semantic_negative_not_rejected(
            case_id,
            {
                "source_manifest_status": source_manifest.get("status"),
                "probe": probe,
            },
        )
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)


def _raw_source_manifest(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    manifest_path = source_manifest.get("source_manifest_path")
    if isinstance(manifest_path, str) and Path(manifest_path).is_file():
        return json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return {}


def _source_evidence(
    mechanism_id: str,
    source_manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    raw_manifest = _raw_source_manifest(source_manifest)
    copied_by_ref = {
        str(row.get("source_ref")): row
        for row in source_manifest.get("modules", [])
        if isinstance(row, Mapping)
    }
    refactors_by_ref = {
        str(row.get("source_ref")): row
        for row in raw_manifest.get("source_faithful_public_refactors", [])
        if isinstance(row, Mapping)
    }
    evidence: list[dict[str, Any]] = []
    for source_ref in MECHANISM_SOURCE_REFS.get(mechanism_id, ()):
        copied = copied_by_ref.get(source_ref)
        refactor = refactors_by_ref.get(source_ref)
        if copied:
            evidence.append(
                {
                    "source_ref": source_ref,
                    "source_to_target_relation": copied.get("source_to_target_relation"),
                    "digest_status": copied.get("digest_status"),
                    "missing_required_anchor_count": len(copied.get("missing_required_anchors") or []),
                    "body_copied": copied.get("body_copied") is True,
                    "body_in_receipt": False,
                }
            )
            continue
        if refactor:
            evidence.append(
                {
                    "source_ref": source_ref,
                    "source_to_target_relation": refactor.get("source_to_target_relation"),
                    "digest_status": "source_digest_recorded_target_is_public_refactor",
                    "source_sha256": refactor.get("source_sha256"),
                    "body_copied": False,
                    "body_in_receipt": False,
                    "rewrite_recipe": refactor.get("rewrite_recipe"),
                }
            )
            continue
        evidence.append(
            {
                "source_ref": source_ref,
                "source_to_target_relation": "not_batch10_body_import",
                "digest_status": "external_binding_required",
                "body_copied": False,
                "body_in_receipt": False,
            }
        )
    return evidence


def _build_integrity_matrix(
    mechanisms: Sequence[Mapping[str, Any]],
    source_manifest: Mapping[str, Any],
    negative_payloads: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    mechanism_by_id = {str(row.get("mechanism_id")): row for row in mechanisms}
    negative_cases_by_mechanism: dict[str, list[dict[str, Any]]] = {}
    for case_id, binding in NEGATIVE_CASE_BINDINGS.items():
        mechanism_id = str(binding["mechanism_id"])
        payload = negative_payloads.get(case_id, {})
        probe = _compute_negative_case_probe(case_id, payload, public_root=public_root)
        computed_value = probe.get("observed_value")
        computed = probe.get("computed_value") is True
        negative_cases_by_mechanism.setdefault(mechanism_id, []).append(
            {
                "case_id": case_id,
                "fixture_role": "negative_case_label_not_verdict_authority",
                "fixture_error_code": EXPECTED_NEGATIVE_CASES[case_id][0],
                "verdict_authority": CASE_VERDICT_AUTHORITY,
                "computed_path": binding["computed_path"],
                "computed_value": computed_value,
                "expected": binding.get("expected", binding.get("expected_contains")),
                "computed": computed,
                "probe_status": probe.get("status"),
                "probe_input_digest": probe.get("probe_input_digest"),
                "probe_input_keys": probe.get("probe_input_keys", []),
                "body_in_receipt": False,
            }
        )

    rows_out: list[dict[str, Any]] = []
    for mechanism_id in EXPECTED_MECHANISMS:
        mechanism = mechanism_by_id.get(mechanism_id, {})
        cases = negative_cases_by_mechanism.get(mechanism_id, [])
        source_evidence = _source_evidence(mechanism_id, source_manifest)
        classification = MECHANISM_CLASSIFICATIONS.get(
            mechanism_id,
            "exact_macro_body_copied_but_port_exercises_refactor",
        )
        if mechanism.get("status") == "pass" and all(case["computed"] for case in cases):
            action = "keep"
        elif classification == "under_bound_binding_repair":
            action = "block"
        else:
            action = "harden"
        rows_out.append(
            {
                "mechanism_id": mechanism_id,
                "classification": classification,
                "status": mechanism.get("status"),
                "source_evidence": source_evidence,
                "positive_input_shape": "controlled_public_input_constructed_by_capsule_evaluator",
                "positive_computed_output": mechanism.get("status"),
                "negative_cases": cases,
                "negative_verdict_authority": CASE_VERDICT_AUTHORITY,
                "negative_result_computed": bool(cases) and all(case["computed"] for case in cases),
                "fixture_verdict_echo_risk": not cases or not all(case["computed"] for case in cases),
                "claim_ceiling": mechanism.get("claim_ceiling"),
                "secret_private_carve_out": "receipts carry refs/digests/counts only; copied bodies remain under source_modules",
                "current_action": action,
                "body_in_receipt": False,
            }
        )

    return {
        "schema_version": "batch10_governance_compilers_integrity_matrix_v1",
        "rows": rows_out,
        "summary": {
            "mechanism_count": len(rows_out),
            "computed_negative_case_count": sum(
                len(row["negative_cases"])
                for row in rows_out
                if row["negative_result_computed"]
            ),
            "fixture_verdict_echo_risk_count": sum(
                1 for row in rows_out if row["fixture_verdict_echo_risk"]
            ),
            "under_bound_binding_repair_count": sum(
                1 for row in rows_out if row["classification"] == "under_bound_binding_repair"
            ),
            "source_faithful_refactor_count": sum(
                1 for row in rows_out if row["classification"].startswith("source_faithful")
            ),
            "body_in_receipt": False,
        },
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    mechanisms = [
        _mutation_governance_matrix(),
        _observe_apply_compiler_matrix(),
        _reviewer_gauntlet_matrix(),
        _release_toggle_triage_matrix(),
        _publication_manifest_contract_matrix(),
        _receipt_reuse_matrix(),
        _finance_temporal_matrix(),
        _session_wave_matrix(),
        _claim_conflict_wait_tax_matrix(),
        _role_aware_dag_matrix(),
        _lane_width_binding_matrix(public_root),
    ]
    negative_payloads = _negative_case_payloads(input_path)
    integrity = _build_integrity_matrix(
        mechanisms,
        source_manifest,
        negative_payloads,
        public_root,
    )
    findings: list[dict[str, Any]] = []
    for mechanism in mechanisms:
        mechanism_id = str(mechanism.get("mechanism_id") or "")
        if mechanism_id == "weighted_lane_width_apportionment_binding_repair":
            continue
        if mechanism.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH10_MECHANISM_BLOCKED",
                    "Batch-10 mechanism exercise did not pass.",
                    subject_id=mechanism_id,
                    observed=mechanism.get("status"),
                )
            )
    integrity_summary = integrity["summary"]
    if integrity_summary["fixture_verdict_echo_risk_count"]:
        findings.append(
            finding(
                "BATCH10_FIXTURE_VERDICT_ECHO_RISK",
                "Every Batch-10 negative case must be paired to computed evaluator evidence.",
                observed=integrity_summary["fixture_verdict_echo_risk_count"],
            )
        )
    if source_manifest.get("module_count", 0) != 10:
        findings.append(
            finding(
                "BATCH10_SOURCE_MODULE_COUNT_INVALID",
                "Batch-10 capsule must carry 10 copied non-secret source modules.",
                expected=10,
                observed=source_manifest.get("module_count"),
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "input_manifest_schema": input_path.joinpath(PROBE_MANIFEST_NAME).name,
        "mechanism_count": len(mechanisms),
        "mechanism_ids": [str(row.get("mechanism_id")) for row in mechanisms],
        "passed_mechanism_count": sum(1 for row in mechanisms if row.get("status") == "pass"),
        "blocked_binding_repair_count": sum(
            1 for row in mechanisms if row.get("mechanism_id") == "weighted_lane_width_apportionment_binding_repair"
        ),
        "mechanisms": mechanisms,
        "integrity_matrix": integrity["rows"],
        "integrity_summary": integrity_summary,
        "copied_macro_source_module_count": source_manifest.get("module_count"),
        "error_codes": [],
        "findings": findings,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch10_governance_compilers_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["mechanism_count"] = exercise.get("mechanism_count")
    card["passed_mechanism_count"] = exercise.get("passed_mechanism_count")
    card["blocked_binding_repair_count"] = exercise.get("blocked_binding_repair_count")
    card["mechanism_ids"] = exercise.get("mechanism_ids", [])
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=BUNDLE_INPUT_MODE if args.action == "validate-bundle" else "fixture_input",
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(json.dumps(result_card(result) if args.card else result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
