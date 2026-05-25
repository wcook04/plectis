from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    classify_public_safe_macro_import,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "macro_projection_import_protocol"
FIXTURE_ID = "first_wave.macro_projection_import_protocol"
VALIDATOR_ID = "validator.microcosm.organs.macro_projection_import_protocol"

RESULT_NAME = "macro_projection_import_protocol_result.json"
BOARD_NAME = "projection_import_board.json"
INTAKE_BOARD_NAME = "projection_import_intake_board.json"
VALIDATION_RECEIPT_NAME = "projection_import_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "macro_projection_import_protocol_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_projection_import_bundle_validation_result.json"
DEPENDENCY_PREFLIGHT_RECEIPT_REL = Path("receipts/preflight/dependency_preflight.json")
ORGAN_REGISTRY_REL = Path("core/organ_registry.json")
ORGAN_LIFECYCLE_ACCEPTED_COUNT_FIELDS = (
    "accepted_organ_count",
    "runtime_step_count",
    "acceptance_plan_organ_count",
    "evidence_class_row_count",
    "fixture_check_count",
)
ORGAN_LIFECYCLE_PRODUCT_AUTHORITY_COUNT_FIELDS = (
    "public_authority_expected_organ_count",
    "organ_authority_row_count",
)
ORGAN_LIFECYCLE_COUNT_FIELDS = (
    *ORGAN_LIFECYCLE_ACCEPTED_COUNT_FIELDS,
    *ORGAN_LIFECYCLE_PRODUCT_AUTHORITY_COUNT_FIELDS,
)

INPUT_NAMES = (
    "projection_protocol.json",
    "cleaning_policy.json",
    "import_plan.json",
)
NEGATIVE_INPUT_NAMES = (
    "forbidden_body_import_overclaim.json",
    "missing_omission_receipt.json",
    "authority_upgrade_overclaim.json",
    "missing_validation_ref.json",
    "release_or_private_equivalence_overclaim.json",
    "standalone_dependency_leak.json",
)

EXPECTED_NEGATIVE_CASES = {
    "forbidden_body_import_overclaim": ["MACRO_PROJECTION_FORBIDDEN_BODY_IMPORT"],
    "missing_omission_receipt": ["MACRO_PROJECTION_OMISSION_RECEIPT_MISSING"],
    "authority_upgrade_overclaim": ["MACRO_PROJECTION_AUTHORITY_UPGRADE"],
    "missing_validation_ref": ["MACRO_PROJECTION_VALIDATION_REF_MISSING"],
    "release_or_private_equivalence_overclaim": [
        "MACRO_PROJECTION_RELEASE_OR_EQUIVALENCE_OVERCLAIM"
    ],
    "standalone_dependency_leak": ["MACRO_PROJECTION_STANDALONE_DEPENDENCY_LEAK"],
}

TRUE_FORBIDDEN_MATERIAL_CLASSES = {
    "raw_seed_body",
    "operator_thread_body",
    "provider_payload_body",
    "non_public_evidence_body",
    "private_operator_source_body",
    "credential",
    "secret",
    "recipient_packet_body",
    "release_packet_body",
}
PUBLIC_SAFE_BODY_MATERIAL_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_macro_proof_body",
}
PUBLIC_SAFE_BODY_COPY_POLICY = "verified_macro_body_with_claim_floor"
METADATA_COPY_POLICY = "metadata_or_regression_wrapper_no_body_import"
MACRO_ORIGIN_REF_POLICY = "macro_origin_refs_are_provenance_only_not_runtime_dependencies"
STANDALONE_RUNTIME_ROOT_REF = "microcosm-substrate"
STANDALONE_RUNTIME_ALLOWED_PREFIXES = (
    "AGENTS.md",
    "README.md",
    "core/",
    "examples/",
    "fixtures/",
    "paper_modules/",
    "pyproject.toml",
    "receipts/",
    "src/",
    "standards/",
    "tests/",
)
STANDALONE_RUNTIME_BLOCKED_PREFIXES = (
    "/",
    "../",
    "codex/ledger/",
    "formal_math/",
    "obsidian/",
    "state/",
    "tools/meta/",
)
STANDALONE_RUNTIME_BLOCKED_TOKENS = (
    "credential",
    "operator_thread",
    "private_root",
    "provider_payload",
    "raw_seed",
    "recipient_packet",
    "release_packet",
)
FORBIDDEN_MATERIAL_CLASSES = TRUE_FORBIDDEN_MATERIAL_CLASSES
FORBIDDEN_AUTHORITY_FLAGS = (
    "source_authority_above_macro_contracts",
    "live_macro_source_authority",
    "private_root_equivalence_authorized",
    "whole_system_correctness_claim",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "macro_projection_protocol_verified_body_import_or_secret_exclusion_only",
    "public_safe_bodies_imported_with_provenance": True,
    "credential_or_account_bound_bodies_exported": False,
    "raw_seed_body_read": False,
    "operator_thread_body_read": False,
    "provider_payload_body_read": False,
    "release_authorized": False,
    "publication_authorized": False,
    "recipient_work_authorized": False,
    "private_data_equivalence_claim": False,
    "source_authority_above_macro_contracts": False,
    "live_macro_source_authority": False,
    "whole_system_correctness_claim": False,
}
BODY_DIGEST_PREFIX = "sha256:"
BODY_DIGEST_HEX_LENGTH = 64
PLACEHOLDER_DIGEST_TOKENS = ("placeholder", "todo", "example")
BODY_IMPORT_VERIFICATION_MODES = {
    "exact_source_digest_match",
    "verified_light_edit_recipe",
}
ANTI_CLAIM = (
    "The macro projection import protocol validates verified non-secret macro "
    "body imports and honest demotions. Metadata, provenance, and public runtime "
    "refs are not body imports. The only hard omissions are secrets, credentials, "
    "operator conversation bodies, provider payloads, and account-bound material; "
    "hosted publication remains a separate action."
)
CELL_STATUS_PROTOCOL = {
    "schema_version": "macro_projection_cell_status_protocol_v1",
    "status_field": "projection_status",
    "cell_state_field": "cell_state",
    "open_action_field": "action_required",
    "closed_statuses": [
        "public_runtime_import_landed",
        "self_hosted_status_protocol_landed",
        "runtime_bridge_landed",
    ],
    "open_statuses": [
        "ready_for_projection",
        "blocked",
    ],
    "authority_ceiling": "cell_status_only_not_body_import_or_secret_exclusion",
    "anti_claim": (
        "Cell status is intake coordination. It is not an imported macro body, "
        "a capability proof, or a reason to avoid importing real non-secret substrate."
    ),
}
LANDING_PROJECTION_STATUSES = set(CELL_STATUS_PROTOCOL["closed_statuses"])
CELL_STATUS_OVERRIDES: dict[str, dict[str, Any]] = {
    "formal_math_readiness_extensions": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The formal-math readiness extension cell has a public runtime import board "
            "with premise, tactic, routing, provider-context, source-intake, and validation refs."
        ),
        "landed_evidence_refs": [
            "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_extension_board.json",
            "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_validation_receipt.json",
            "paper_modules/formal_math_readiness_gate.md",
        ],
        "next_runtime_surface": (
            "microcosm formal-math-readiness-gate plan --input "
            "fixtures/first_wave/formal_math_readiness_gate/input"
        ),
    },
    "projection_protocol_self_host": {
        "projection_status": "self_hosted_status_protocol_landed",
        "cell_state": "consumed_protocol_self_host",
        "action_required": False,
        "status_reason": (
            "The macro projection protocol now emits this cell-status state machine "
            "directly in plan, run, receipts, and runtime intake views."
        ),
        "landed_evidence_refs": [
            "standards/std_microcosm_macro_projection_import_protocol.json",
            "paper_modules/macro_projection_import_protocol.md",
            "receipts/first_wave/macro_projection_import_protocol/projection_import_intake_board.json",
            "receipts/first_wave/macro_projection_import_protocol/projection_import_validation_receipt.json",
        ],
        "next_runtime_surface": (
            "microcosm macro-projection-import-protocol plan --input "
            "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        ),
    },
    "runtime_reveal_import_bridge": {
        "projection_status": "runtime_bridge_landed",
        "cell_state": "bridged_runtime_surface",
        "action_required": False,
        "status_reason": (
            "The reveal/import bridge is landed as microcosm intake with a runtime receipt "
            "and first-run path through spine, intake, reveal, and evidence."
        ),
        "landed_evidence_refs": [
            "receipts/runtime_shell/intake_bridge/runtime_reveal_import_bridge.json",
            "receipts/runtime_shell/intake_bridge/organs/public_reveal_walkthrough/exported_public_reveal_bundle_validation_result.json",
            "paper_modules/public_reveal_walkthrough.md",
        ],
        "next_runtime_surface": "microcosm intake",
    },
    "agent_execution_trace_refactor": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The agent execution trace refactor is landed as a public macro tool body "
            "and consumed by the route observability runtime bundle."
        ),
        "landed_evidence_refs": [
            "src/microcosm_core/macro_tools/agent_execution_trace.py",
            "examples/agent_route_observability_runtime/exported_computer_use_action_trace_bundle/projection_protocol.json",
            "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime/exported_computer_use_action_trace_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm agent-route-observability-runtime validate-computer-use-bundle "
            "--input examples/agent_route_observability_runtime/exported_computer_use_action_trace_bundle"
        ),
    },
    "agent_trace_route_repair_observability_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The agent trace-to-route-repair observability lane is landed as a "
            "source-faithful public route-repair macro tool and consumed by the "
            "route observability runtime bundle."
        ),
        "landed_evidence_refs": [
            "src/microcosm_core/macro_tools/agent_trace_route_repair.py",
            "examples/agent_route_observability_runtime/exported_agent_trace_route_repair_bundle",
            "receipts/first_wave/agent_route_observability_runtime/exported_agent_trace_route_repair_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm agent-route-observability-runtime "
            "validate-agent-trace-route-repair-bundle --input "
            "examples/agent_route_observability_runtime/exported_agent_trace_route_repair_bundle"
        ),
    },
    "agent_observability_store_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The agent observability store is landed as a source-faithful public "
            "AgentTraceStore macro tool and consumed by the route observability "
            "runtime bundle."
        ),
        "landed_evidence_refs": [
            "src/microcosm_core/macro_tools/agent_observability_store.py",
            "examples/agent_route_observability_runtime/exported_agent_observability_store_bundle",
            "receipts/first_wave/agent_route_observability_runtime/exported_agent_observability_store_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm agent-route-observability-runtime "
            "validate-agent-observability-store-bundle --input "
            "examples/agent_route_observability_runtime/exported_agent_observability_store_bundle"
        ),
    },
    "agent_session_attribution_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The agent session-attribution join is landed as an exact public macro tool "
            "body and consumed by the route observability runtime session-attribution bundle."
        ),
        "landed_evidence_refs": [
            "src/microcosm_core/macro_tools/agent_session_attribution.py",
            "examples/agent_route_observability_runtime/exported_session_attribution_bundle",
            "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime/exported_session_attribution_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm agent-route-observability-runtime validate-session-attribution-bundle "
            "--input examples/agent_route_observability_runtime/exported_session_attribution_bundle"
        ),
    },
    "multi_agent_fanin_replay_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The multi-agent fan-in replay lane is landed as source-faithful public "
            "continuation-packet and bridge-resume macro tools plus exported fan-in "
            "and dispatch/yield/resume metadata bundles."
        ),
        "landed_evidence_refs": [
            "src/microcosm_core/macro_tools/continuation_packet.py",
            "src/microcosm_core/macro_tools/bridge_resume.py",
            "examples/agent_route_observability_runtime/exported_multi_agent_fanin_replay_bundle",
            "examples/agent_route_observability_runtime/exported_bridge_dispatch_yield_resume_bundle",
            "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime/exported_multi_agent_fanin_replay_bundle_validation_result.json",
            "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime/exported_bridge_dispatch_yield_resume_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm agent-route-observability-runtime validate-bridge-dispatch-yield-resume-bundle "
            "--input examples/agent_route_observability_runtime/exported_bridge_dispatch_yield_resume_bundle"
        ),
    },
    "controller_continuity_heartbeat_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The controller-continuity heartbeat is landed as a source-faithful public "
            "macro tool body plus an exported runtime replay bundle covering 5x5 "
            "heartbeat validation, event identity, response-schema wrapping, dedupe, "
            "and stale generic problem regeneration."
        ),
        "landed_evidence_refs": [
            "src/microcosm_core/macro_tools/controller_heartbeat.py",
            "examples/agent_route_observability_runtime/exported_controller_heartbeat_bundle",
            "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime/exported_controller_heartbeat_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm agent-route-observability-runtime validate-controller-heartbeat-bundle "
            "--input examples/agent_route_observability_runtime/exported_controller_heartbeat_bundle"
        ),
    },
    "navigation_route_plane_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The navigation route plane now carries copied non-secret macro route rows "
            "inside Microcosm and validates them through the route-plane runtime consumer."
        ),
        "landed_evidence_refs": [
            "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json",
            "receipts/first_wave/navigation_hologram_route_plane/exported_route_plane_bundle_validation_result.json",
            "src/microcosm_core/organs/navigation_hologram_route_plane.py",
        ],
        "next_runtime_surface": (
            "microcosm navigation-hologram-route-plane validate-route-plane-bundle "
            "--input examples/navigation_hologram_route_plane/exported_route_plane_bundle"
        ),
    },
    "finance_eval_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The finance forecast evaluation spine carries exact copied tools/finance "
            "source modules inside Microcosm and validates them through the finance "
            "eval bundle without trading, advice, provider-call, account, optimizer, "
            "calculator-mutation, publication, or release authority."
        ),
        "landed_evidence_refs": [
            "examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle",
            "receipts/first_wave/finance_forecast_evaluation_spine/exported_finance_eval_bundle_validation_result.json",
            "src/microcosm_core/macro_tools/finance_eval_spine.py",
        ],
        "next_runtime_surface": (
            "microcosm finance-eval-spine validate-finance-eval-bundle "
            "--input examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle"
        ),
    },
    "work_landing_control_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The work-landing control spine carries exact copied control-plane "
            "source modules inside Microcosm and validates them through the "
            "work-landing control bundle without live Task Ledger, Work Ledger, "
            "Git, private-index execution, provider, publication, or release authority."
        ),
        "landed_evidence_refs": [
            "examples/work_landing_control_spine/exported_work_landing_control_bundle",
            "receipts/first_wave/work_landing_control_spine/exported_work_landing_control_bundle_validation_result.json",
            "src/microcosm_core/macro_tools/work_landing_control_spine.py",
        ],
        "next_runtime_surface": (
            "microcosm work-landing-control-spine validate-control-bundle "
            "--input examples/work_landing_control_spine/exported_work_landing_control_bundle"
        ),
    },
    "task_ledger_control_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The Task Ledger control-plane source modules are landed as exact copied "
            "non-secret macro bodies inside the mission transaction bundle and "
            "consumed by the mission transaction work spine runtime."
        ),
        "landed_evidence_refs": [
            "examples/mission_transaction_work_spine/exported_mission_transaction_bundle",
            "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_module_manifest.json",
            "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/task_ledger_control_runtime_contract.json",
            "receipts/first_wave/mission_transaction_work_spine/exported_mission_transaction_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm mission-transaction-work-spine validate-mission-bundle "
            "--input examples/mission_transaction_work_spine/exported_mission_transaction_bundle"
        ),
    },
    "work_ledger_control_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The Work Ledger control-plane source modules are landed as exact copied "
            "non-secret macro bodies inside the mission transaction bundle and "
            "consumed by the mission transaction work spine runtime."
        ),
        "landed_evidence_refs": [
            "examples/mission_transaction_work_spine/exported_mission_transaction_bundle",
            "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/work_ledger_source_module_manifest.json",
            "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/work_ledger_control_runtime_contract.json",
            "receipts/first_wave/mission_transaction_work_spine/exported_mission_transaction_bundle_validation_result.json",
        ],
        "next_runtime_surface": (
            "microcosm mission-transaction-work-spine validate-mission-bundle "
            "--input examples/mission_transaction_work_spine/exported_mission_transaction_bundle"
        ),
    },
    "command_output_projection_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The command-output projection and sidecar substrate is landed as "
            "exact copied non-secret macro source inside Microcosm, with the "
            "standalone projection and sidecar helpers available as public "
            "macro tools and the macro audit/standard bodies carried in the "
            "projection bundle."
        ),
        "landed_evidence_refs": [
            "src/microcosm_core/macro_tools/command_output_projection.py",
            "src/microcosm_core/macro_tools/command_output_sidecar.py",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/command_output_source_module_manifest.json",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/command_output_projection_runtime_contract.json",
            "receipts/first_wave/macro_projection_import_protocol/projection_import_validation_receipt.json",
        ],
        "next_runtime_surface": (
            "microcosm macro-projection-import-protocol plan --input "
            "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        ),
    },
    "trace_capsule_prompt_edit_capture_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The trace-capsule prompt/edit-capture lane carries exact copied "
            "non-secret cli_prompt_trace and Agent Trace Structurer source "
            "modules inside the projection bundle, and validates them through "
            "public fixture rendering plus the deterministic parser test suite "
            "without reading live provider payloads, browser/HUD state, "
            "account/session state, cookies, credentials, or recipient-send "
            "material."
        ),
        "landed_evidence_refs": [
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/trace_capsule_source_module_manifest.json",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/source_modules/tools/meta/observability/cli_prompt_trace.py",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/source_modules/tools/agent_trace_structurer/parser.mjs",
            "tests/test_command_output_projection_runtime.py",
        ],
        "next_runtime_surface": (
            "pytest microcosm-substrate/tests/test_command_output_projection_runtime.py"
        ),
    },
    "route_selection_control_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The route-selection control plane carries exact copied non-secret "
            "entry packet, context-pack, option-surface, route-intervention, "
            "and navigation-contract source bodies inside the projection bundle, "
            "validated by digest/anchor checks plus a fixture route-repair call "
            "without live macro kernel execution or private/provider/session "
            "payload access."
        ),
        "landed_evidence_refs": [
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/route_selection_control_source_module_manifest.json",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/source_modules/system/lib/navigation_context_pack.py",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/source_modules/system/lib/kernel/commands/comprehension_snapshot.py",
            "tests/test_command_output_projection_runtime.py",
        ],
        "next_runtime_surface": (
            "pytest microcosm-substrate/tests/test_command_output_projection_runtime.py"
        ),
    },
    "bootstrap_route_surface_source_modules_import": {
        "projection_status": "public_runtime_import_landed",
        "cell_state": "consumed_verified_import",
        "action_required": False,
        "status_reason": (
            "The bootstrap route surface now carries exact copied non-secret "
            "agent_bootstrap_live, routing_hologram, agent_bootstrap_projection, "
            "and routing_projection bodies inside the projection bundle, "
            "validated by digest/anchor checks, route-row assertions, and "
            "syntax compilation without live macro projection refresh authority."
        ),
        "landed_evidence_refs": [
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/bootstrap_route_surface_source_module_manifest.json",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/source_modules/codex/doctrine/agent_bootstrap_live.json",
            "examples/macro_projection_import_protocol/exported_projection_import_bundle/source_modules/system/lib/agent_bootstrap_projection.py",
            "tests/test_command_output_projection_runtime.py",
        ],
        "next_runtime_surface": (
            "pytest microcosm-substrate/tests/test_command_output_projection_runtime.py"
        ),
    },
}


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _accepted_organ_count(public_root: Path) -> int | None:
    registry_path = public_root / ORGAN_REGISTRY_REL
    if not registry_path.is_file():
        return None
    registry = read_json_strict(registry_path)
    rows = registry.get("implemented_organs", []) if isinstance(registry, dict) else []
    if not isinstance(rows, list):
        return None
    return sum(
        1
        for row in rows
        if isinstance(row, dict) and str(row.get("status") or "") == "accepted_current_authority"
    )


def _add_dependency_preflight_defect(
    defects: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    *,
    defect_code: str,
    error_code: str,
    message: str,
    subject_id: str,
    subject_kind: str = "dependency_preflight_receipt",
) -> None:
    defects.append(
        {
            "defect_code": defect_code,
            "error_code": error_code,
            "message": message,
            "subject_id": subject_id,
            "subject_kind": subject_kind,
            "body_in_receipt": False,
        }
    )
    findings.append(
        _finding(
            error_code,
            message,
            case_id="dependency_preflight_lifecycle_gate",
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )


def _dependency_preflight_lifecycle_gate(public_root: Path) -> dict[str, Any]:
    receipt_path = public_root / DEPENDENCY_PREFLIGHT_RECEIPT_REL
    receipt_ref = _display(receipt_path, public_root=public_root)
    defects: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    receipt: dict[str, Any] = {}
    lifecycle: dict[str, Any] = {}
    coverage_counts: dict[str, Any] = {}
    expected_count = _accepted_organ_count(public_root)

    if not receipt_path.is_file():
        _add_dependency_preflight_defect(
            defects,
            findings,
            defect_code="dependency_preflight_receipt_missing",
            error_code="MACRO_PROJECTION_DEPENDENCY_PREFLIGHT_MISSING",
            message="Runtime severance requires the dependency preflight receipt.",
            subject_id=receipt_ref,
        )
    else:
        receipt = read_json_strict(receipt_path)
        if not isinstance(receipt, dict):
            _add_dependency_preflight_defect(
                defects,
                findings,
                defect_code="dependency_preflight_receipt_invalid",
                error_code="MACRO_PROJECTION_DEPENDENCY_PREFLIGHT_INVALID",
                message="Dependency preflight receipt must be a JSON object.",
                subject_id=receipt_ref,
            )
        elif receipt.get("status") != PASS:
            _add_dependency_preflight_defect(
                defects,
                findings,
                defect_code="dependency_preflight_status_blocked",
                error_code="MACRO_PROJECTION_DEPENDENCY_PREFLIGHT_BLOCKED",
                message="Dependency preflight must pass before runtime severance can pass.",
                subject_id=receipt_ref,
            )
        lifecycle_value = receipt.get("organ_lifecycle_coverage") if isinstance(receipt, dict) else None
        if not isinstance(lifecycle_value, dict):
            _add_dependency_preflight_defect(
                defects,
                findings,
                defect_code="organ_lifecycle_coverage_missing",
                error_code="MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_MISSING",
                message="Dependency preflight receipt must include organ_lifecycle_coverage_v1.",
                subject_id=receipt_ref,
            )
        else:
            lifecycle = lifecycle_value
            coverage_counts_value = lifecycle.get("coverage_counts", {})
            coverage_counts = coverage_counts_value if isinstance(coverage_counts_value, dict) else {}
            if lifecycle.get("status") != PASS:
                _add_dependency_preflight_defect(
                    defects,
                    findings,
                    defect_code="organ_lifecycle_coverage_blocked",
                    error_code="MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_BLOCKED",
                    message="Organ lifecycle coverage must pass before runtime severance can pass.",
                    subject_id=receipt_ref,
                )
            if lifecycle.get("defect_count", 0) not in (0, "0"):
                _add_dependency_preflight_defect(
                    defects,
                    findings,
                    defect_code="organ_lifecycle_coverage_defects_present",
                    error_code="MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_BLOCKED",
                    message="Organ lifecycle coverage reports blocking lifecycle defects.",
                    subject_id=receipt_ref,
                )
            if expected_count is None:
                _add_dependency_preflight_defect(
                    defects,
                    findings,
                    defect_code="accepted_organ_registry_missing",
                    error_code="MACRO_PROJECTION_ACCEPTED_ORGAN_REGISTRY_MISSING",
                    message="Runtime severance must compare lifecycle coverage against accepted organs.",
                    subject_id=str(ORGAN_REGISTRY_REL),
                    subject_kind="organ_registry",
                )
            else:
                for field in ORGAN_LIFECYCLE_ACCEPTED_COUNT_FIELDS:
                    count = coverage_counts.get(field)
                    if count != expected_count:
                        _add_dependency_preflight_defect(
                            defects,
                            findings,
                            defect_code="organ_lifecycle_coverage_stale_count",
                            error_code="MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_STALE",
                            message=(
                                "Organ lifecycle coverage count must match the accepted "
                                "organ count for runtime severance."
                            ),
                            subject_id=field,
                            subject_kind="organ_lifecycle_count",
                        )
                product_authority_count = coverage_counts.get(
                    "public_authority_expected_organ_count"
                )
                if not isinstance(product_authority_count, int):
                    _add_dependency_preflight_defect(
                        defects,
                        findings,
                        defect_code="organ_lifecycle_coverage_stale_count",
                        error_code="MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_STALE",
                        message=(
                            "Organ lifecycle coverage must name the expected "
                            "product authority count for runtime severance."
                        ),
                        subject_id="public_authority_expected_organ_count",
                        subject_kind="organ_lifecycle_count",
                    )
                else:
                    for field in ORGAN_LIFECYCLE_PRODUCT_AUTHORITY_COUNT_FIELDS:
                        count = coverage_counts.get(field)
                        if count != product_authority_count:
                            _add_dependency_preflight_defect(
                                defects,
                                findings,
                                defect_code="organ_lifecycle_coverage_stale_count",
                                error_code="MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_STALE",
                                message=(
                                    "Product authority lifecycle coverage count must "
                                    "match the expected product-spine organ count for "
                                    "runtime severance."
                                ),
                                subject_id=field,
                                subject_kind="organ_lifecycle_count",
                            )

    return {
        "schema_version": "macro_projection_dependency_preflight_gate_v1",
        "status": PASS if not defects else "blocked",
        "receipt_ref": receipt_ref,
        "dependency_preflight_status": receipt.get("status") if receipt else "missing",
        "organ_lifecycle_coverage_status": lifecycle.get("status") if lifecycle else "missing",
        "expected_accepted_organ_count": expected_count,
        "coverage_counts": coverage_counts,
        "required_count_fields": list(ORGAN_LIFECYCLE_COUNT_FIELDS),
        "defect_count": len(defects),
        "defects": defects,
        "findings": findings,
        "anti_claim": (
            "This check proves runtime severance consumed the preflight lifecycle "
            "receipt. It is not a substitute for an imported macro body, provider "
            "execution, or proof of organ semantics."
        ),
        "body_in_receipt": False,
    }


def _authority_upgrade(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    ceiling = payload.get("authority_ceiling", payload)
    if not isinstance(ceiling, dict):
        return False
    return any(ceiling.get(flag) is True for flag in FORBIDDEN_AUTHORITY_FLAGS)


def _release_or_equivalence_overclaim(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    ceiling = payload.get("authority_ceiling", payload)
    if not isinstance(ceiling, dict):
        return False
    return any(
        ceiling.get(flag) is True
        for flag in (
            "release_authorized",
            "hosted_public_authorized",
            "publication_authorized",
            "recipient_work_authorized",
            "private_data_equivalence_claim",
            "private_root_equivalence_authorized",
        )
    )


def _public_safe_import_status(
    row: dict[str, Any],
    *,
    import_policy: dict[str, Any],
) -> dict[str, Any] | None:
    material_class = str(row.get("material_class") or "")
    if material_class not in PUBLIC_SAFE_BODY_MATERIAL_CLASSES:
        return None
    return classify_public_safe_macro_import(row, forbidden_classes=import_policy)


def _sha256_digest(path: Path) -> str:
    return f"{BODY_DIGEST_PREFIX}{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _body_digest_is_placeholder(value: str) -> bool:
    lowered = value.lower()
    if not value.startswith(BODY_DIGEST_PREFIX):
        return True
    digest = value.removeprefix(BODY_DIGEST_PREFIX)
    if len(digest) != BODY_DIGEST_HEX_LENGTH:
        return True
    if any(token in lowered for token in PLACEHOLDER_DIGEST_TOKENS):
        return True
    return any(char not in "0123456789abcdef" for char in digest.lower())


def _source_ref_file_candidates(source_ref: str, *, public_root: Path | None) -> list[Path]:
    ref_path = Path(source_ref.split("::", 1)[0])
    if ref_path.is_absolute() or ".." in ref_path.parts:
        return []
    candidates: list[Path] = []
    if public_root is not None:
        candidates.extend([public_root / ref_path, public_root.parent / ref_path])
    candidates.append(Path.cwd() / ref_path)
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _first_existing_source_ref(source_refs: list[str], *, public_root: Path | None) -> tuple[str, Path] | None:
    for source_ref in source_refs:
        for candidate in _source_ref_file_candidates(source_ref, public_root=public_root):
            if candidate.is_file():
                return source_ref, candidate
    return None


def _body_import_verification_findings(
    row: dict[str, Any],
    *,
    material_id: str,
    declared_digest: str,
    public_root: Path | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    verification = row.get("body_import_verification")
    if not isinstance(verification, dict):
        return [
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_VERIFICATION_MISSING",
                "body_copied verified macro material must carry a verified source-to-target import record.",
                case_id="public_safe_body_import_floor",
                subject_id=material_id,
                subject_kind="copied_material",
            )
        ]

    mode = str(verification.get("verification_mode") or "")
    status = str(verification.get("verification_status") or "")
    if status != "verified":
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_VERIFICATION_UNVERIFIED",
                "body_copied verified macro material must be marked verified after source-to-target checking.",
                case_id="public_safe_body_import_floor",
                subject_id=material_id,
                subject_kind="copied_material",
            )
        )
    if mode not in BODY_IMPORT_VERIFICATION_MODES:
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_VERIFICATION_MODE_INVALID",
                "body_copied verified macro material must use a known verification mode.",
                case_id="public_safe_body_import_floor",
                subject_id=material_id,
                subject_kind="copied_material",
            )
        )

    target_digest = str(verification.get("target_body_digest") or "")
    if _body_digest_is_placeholder(target_digest) or target_digest != declared_digest:
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_VERIFICATION_DIGEST_MISMATCH",
                "body import verification must bind the target body digest to the declared target digest.",
                case_id="public_safe_body_import_floor",
                subject_id=material_id,
                subject_kind="copied_material",
            )
        )

    if mode == "exact_source_digest_match":
        source_digest = str(verification.get("source_body_digest") or "")
        source_refs = _source_refs_for_material(row)
        if _body_digest_is_placeholder(source_digest):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISSING",
                    "exact body imports must include the source body sha256 digest.",
                    case_id="public_safe_body_import_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )
        elif not source_refs:
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_REF_MISSING",
                    "exact body imports must name the macro source ref whose bytes were copied.",
                    case_id="public_safe_body_import_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )
        elif source_digest != target_digest:
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_TARGET_MISMATCH",
                    "exact body imports must prove source and target body digests match.",
                    case_id="public_safe_body_import_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )
        else:
            existing_source = _first_existing_source_ref(source_refs, public_root=public_root)
            if existing_source is not None and _sha256_digest(existing_source[1]) != source_digest:
                findings.append(
                    _finding(
                        "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISMATCH",
                        "exact body imports must match the actual local source file digest when the source is available.",
                        case_id="public_safe_body_import_floor",
                        subject_id=existing_source[0],
                        subject_kind="copied_material",
                    )
                )
    elif mode == "verified_light_edit_recipe":
        if not isinstance(verification.get("rewrite_recipe_ref"), str):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PUBLIC_SAFE_BODY_REWRITE_RECIPE_MISSING",
                    "light-edit imports must cite a public rewrite recipe instead of relying on provenance prose.",
                    case_id="public_safe_body_import_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )
        if not _strings(verification.get("source_symbol_refs")):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_SYMBOLS_MISSING",
                    "light-edit imports must name source symbols carried into the public target.",
                    case_id="public_safe_body_import_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )
        if not _strings(verification.get("target_symbol_refs")):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PUBLIC_SAFE_BODY_TARGET_SYMBOLS_MISSING",
                    "light-edit imports must name target symbols that carry the macro mechanism.",
                    case_id="public_safe_body_import_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )

    if not _strings(verification.get("runtime_consumed_by")):
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_RUNTIME_CONSUMER_MISSING",
                "body_copied verified macro material must name the command or test that consumes the imported target.",
                case_id="public_safe_body_import_floor",
                subject_id=material_id,
                subject_kind="copied_material",
            )
        )
    return findings


def _public_safe_body_target_findings(
    row: dict[str, Any],
    *,
    public_root: Path | None,
) -> list[dict[str, Any]]:
    if public_root is None or row.get("body_copied") is not True:
        return []

    material_id = str(row.get("material_id") or "public_safe_body_material")
    target_ref = row.get("target_ref")
    findings: list[dict[str, Any]] = []
    if not isinstance(target_ref, str) or not target_ref.strip():
        return [
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_TARGET_REF_MISSING",
                "body_copied verified macro material must name the Microcosm target_ref that contains the copied body.",
                case_id="public_safe_body_import_floor",
                subject_id=material_id,
                subject_kind="copied_material",
            )
        ]

    target_path = Path(_normalize_runtime_root_ref(target_ref.split("::", 1)[0]))
    if target_path.is_absolute() or ".." in target_path.parts:
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_TARGET_REF_UNSAFE",
                "body_copied verified macro material must target a relative path inside microcosm-substrate.",
                case_id="public_safe_body_import_floor",
                subject_id=target_ref,
                subject_kind="copied_material",
            )
        )
        return findings

    resolved_target = public_root / target_path
    declared_digest = str(row.get("body_digest") or "")
    if not resolved_target.is_file():
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_TARGET_MISSING",
                "body_copied verified macro material must point at a real file inside microcosm-substrate.",
                case_id="public_safe_body_import_floor",
                subject_id=target_ref,
                subject_kind="copied_material",
            )
        )
    if _body_digest_is_placeholder(declared_digest):
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_DIGEST_PLACEHOLDER",
                "body_copied verified macro material must carry a real sha256 digest, not a placeholder.",
                case_id="public_safe_body_import_floor",
                subject_id=material_id,
                subject_kind="copied_material",
            )
        )
    elif resolved_target.is_file() and declared_digest != _sha256_digest(resolved_target):
        findings.append(
            _finding(
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_DIGEST_MISMATCH",
                "body_copied verified macro material digest must match the target_ref file.",
                case_id="public_safe_body_import_floor",
                subject_id=target_ref,
                subject_kind="copied_material",
            )
        )
    findings.extend(
        _body_import_verification_findings(
            row,
            material_id=material_id,
            declared_digest=declared_digest,
            public_root=public_root,
        )
    )
    return findings


def _forbidden_body_request(payload: object, *, import_policy: dict[str, Any] | None = None) -> list[str]:
    policy = import_policy or {}
    subjects: list[str] = []
    for key in ("copied_material", "material_requests", "source_refs"):
        for row in _rows(payload, key):
            if _public_safe_import_status(row, import_policy=policy) is not None:
                continue
            material_id = str(row.get("material_id") or row.get("source_ref") or key)
            material_class = str(row.get("material_class") or "")
            if (
                row.get("body_copied") is True
                or row.get("body_included") is True
                or row.get("forbidden_body_requested") is True
                or material_class in FORBIDDEN_MATERIAL_CLASSES
            ):
                subjects.append(material_id)
    if isinstance(payload, dict):
        material_class = str(payload.get("material_class") or "")
        if _public_safe_import_status(payload, import_policy=policy) is not None:
            return sorted(set(subjects))
        if (
            payload.get("body_copied") is True
            or payload.get("body_included") is True
            or payload.get("forbidden_body_requested") is True
            or material_class in FORBIDDEN_MATERIAL_CLASSES
        ):
            subjects.append(str(payload.get("material_id") or payload.get("case_id") or "material"))
    return sorted(set(subjects))


def validate_projection_protocol(
    payload: object,
    forbidden_body_negative: object | None = None,
    omission_negative: object | None = None,
    authority_negative: object | None = None,
    release_negative: object | None = None,
    import_policy: dict[str, Any] | None = None,
    public_root: Path | None = None,
) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    policy = import_policy or {}
    source_refs = _strings(protocol.get("source_refs"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    validation_refs = _strings(protocol.get("validation_refs"))
    copied_material = _rows(protocol, "copied_material")
    omitted_material = _rows(protocol, "omitted_material")
    cleaned_material = _rows(protocol, "cleaned_material")
    steps = _rows(protocol, "steps")

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if len(source_refs) < 2 or len(public_runtime_refs) < 2 or len(validation_refs) < 2:
        findings.append(
            _finding(
                "MACRO_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, public runtime refs, and validation refs.",
                case_id="density_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in copied_material:
        material_id = str(row.get("material_id") or "copied_material")
        material_class = str(row.get("material_class") or "")
        public_safe_status = _public_safe_import_status(row, import_policy=policy)
        if public_safe_status is not None:
            for finding in public_safe_status["findings"]:
                findings.append(
                    _finding(
                        str(finding.get("error_code") or "PUBLIC_SAFE_IMPORT_BLOCKED"),
                        str(finding.get("message") or "Verified macro import classification blocked."),
                        case_id="public_safe_body_import_floor",
                        subject_id=material_id,
                        subject_kind="copied_material",
                    )
                )
            findings.extend(_public_safe_body_target_findings(row, public_root=public_root))
            continue
        if material_class in TRUE_FORBIDDEN_MATERIAL_CLASSES or row.get("body_copied") is True:
            findings.append(
                _finding(
                    "MACRO_PROJECTION_FORBIDDEN_BODY_IMPORT",
                    "Copied material may carry metadata, fixture shape, or verified macro bodies only; credential-bound and raw operator/provider bodies remain forbidden.",
                    case_id="protocol_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )
    for row in omitted_material:
        if not row.get("omission_receipt_ref"):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_OMISSION_RECEIPT_MISSING",
                    "Omitted macro material must carry an omission receipt ref.",
                    case_id="protocol_floor",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="omitted_material",
                )
            )
    for negative in (forbidden_body_negative,):
        for subject in _forbidden_body_request(negative, import_policy=policy):
            _record(
                findings,
                observed,
                "MACRO_PROJECTION_FORBIDDEN_BODY_IMPORT",
                "Projection import rejects credential/account-bound body import requests.",
                case_id="forbidden_body_import_overclaim",
                subject_id=subject,
                subject_kind="negative_case",
            )
    if isinstance(omission_negative, dict):
        rows = _rows(omission_negative, "omitted_material")
        if not rows:
            rows = [omission_negative]
        for row in rows:
            if not row.get("omission_receipt_ref"):
                _record(
                    findings,
                    observed,
                    "MACRO_PROJECTION_OMISSION_RECEIPT_MISSING",
                    "Projection import rejects omitted material without omission receipts.",
                    case_id="missing_omission_receipt",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="negative_case",
                )
    if _authority_upgrade(authority_negative):
        _record(
            findings,
            observed,
            "MACRO_PROJECTION_AUTHORITY_UPGRADE",
            "Projection import cannot upgrade public metadata into live macro source authority.",
            case_id="authority_upgrade_overclaim",
            subject_id=str(
                authority_negative.get("case_id") if isinstance(authority_negative, dict) else "authority"
            ),
            subject_kind="negative_case",
        )
    if _release_or_equivalence_overclaim(release_negative):
        _record(
            findings,
            observed,
            "MACRO_PROJECTION_RELEASE_OR_EQUIVALENCE_OVERCLAIM",
            "Projection import rejects release, publication, recipient, and private-equivalence claims.",
            case_id="release_or_private_equivalence_overclaim",
            subject_id=str(
                release_negative.get("case_id") if isinstance(release_negative, dict) else "release"
            ),
            subject_kind="negative_case",
        )

    blocking_findings = [
        row
        for row in findings
        if row.get("negative_case_id") in {"density_floor", "protocol_floor", "public_safe_body_import_floor"}
    ]
    public_safe_body_count = sum(
        1
        for row in copied_material
        if _public_safe_import_status(row, import_policy=policy) is not None
        and not _public_safe_import_status(row, import_policy=policy)["findings"]
    )
    public_safe_body_target_refs = [
        str(row.get("target_ref"))
        for row in copied_material
        if _public_safe_import_status(row, import_policy=policy) is not None
        and row.get("body_copied") is True
        and isinstance(row.get("target_ref"), str)
    ]
    public_safe_body_digest_count = sum(
        1
        for row in copied_material
        if _public_safe_import_status(row, import_policy=policy) is not None
        and row.get("body_copied") is True
        and not _body_digest_is_placeholder(str(row.get("body_digest") or ""))
    )
    public_safe_body_target_findings = [
        row
        for row in blocking_findings
        if str(row.get("error_code") or "").startswith("MACRO_PROJECTION_PUBLIC_SAFE_BODY_")
    ]
    return {
        "status": PASS
        if len(source_refs) >= 2
        and len(public_runtime_refs) >= 2
        and len(validation_refs) >= 2
        and copied_material
        and omitted_material
        and cleaned_material
        and steps
        and not blocking_findings
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "public_runtime_refs": public_runtime_refs,
        "validation_refs": validation_refs,
        "copied_material_count": len(copied_material),
        "public_safe_body_material_count": public_safe_body_count,
        "public_safe_body_target_status": PASS
        if not public_safe_body_target_findings
        and public_safe_body_count == len(public_safe_body_target_refs) == public_safe_body_digest_count
        else "blocked",
        "public_safe_body_target_refs": sorted(public_safe_body_target_refs),
        "public_safe_body_digest_count": public_safe_body_digest_count,
        "blocking_finding_count": len(blocking_findings),
        "cleaned_material_count": len(cleaned_material),
        "omitted_material_count": len(omitted_material),
        "step_count": len(steps),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_cleaning_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    forbidden = set(_strings(policy.get("forbidden_material_classes")))
    actions = _strings(policy.get("required_cleaning_actions"))
    required_forbidden = {
        "raw_seed_body",
        "operator_thread_body",
        "provider_payload_body",
        "non_public_evidence_body",
        "credential",
    }
    missing_forbidden = sorted(required_forbidden - forbidden)
    findings: list[dict[str, Any]] = []
    if missing_forbidden:
        findings.append(
            _finding(
                "MACRO_PROJECTION_CLEANING_POLICY_INCOMPLETE",
                "Cleaning policy must forbid private body and credential classes.",
                case_id="cleaning_policy_floor",
                subject_id="forbidden_material_classes",
                subject_kind="cleaning_policy",
            )
        )
    if policy.get("requires_omission_receipt") is not True:
        findings.append(
            _finding(
                "MACRO_PROJECTION_CLEANING_POLICY_INCOMPLETE",
                "Cleaning policy must require omission receipts.",
                case_id="cleaning_policy_floor",
                subject_id="requires_omission_receipt",
                subject_kind="cleaning_policy",
            )
        )
    return {
        "status": PASS
        if not findings
        and policy.get("default_copy_mode") == "verified_macro_body_or_honest_regression_fixture"
        and len(actions) >= 4
        else "blocked",
        "policy_id": policy.get("policy_id"),
        "default_copy_mode": policy.get("default_copy_mode"),
        "forbidden_material_classes": sorted(forbidden),
        "required_cleaning_actions": actions,
        "requires_omission_receipt": policy.get("requires_omission_receipt") is True,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_import_plan(
    payload: object,
    missing_validation_negative: object | None = None,
    public_safe_material_ids: set[str] | None = None,
) -> dict[str, Any]:
    plan = payload if isinstance(payload, dict) else {}
    cells = _rows(plan, "proposed_cells")
    known_public_safe_material_ids = public_safe_material_ids or set()
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    cell_ids: list[str] = []
    target_refs: list[str] = []
    validation_refs: list[str] = []
    for row in cells:
        cell_id = str(row.get("cell_id") or "projection_cell")
        cell_ids.append(cell_id)
        target_refs.extend(_strings(row.get("target_refs")))
        validation_refs.extend(_strings(row.get("validation_refs")))
        missing_body_material_ids = sorted(
            material_id
            for material_id in _strings(row.get("public_safe_body_material_ids"))
            if material_id not in known_public_safe_material_ids
        )
        if not _strings(row.get("source_refs")) or not _strings(row.get("target_refs")):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_CELL_ROUTE_MISSING",
                    "Projection cell must name source and target refs.",
                    case_id="import_plan_floor",
                    subject_id=cell_id,
                    subject_kind="projection_cell",
                )
            )
        if missing_body_material_ids:
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PUBLIC_SAFE_BODY_MATERIAL_MISSING",
            "Projection cell references verified macro body material not present in the projection protocol.",
                    case_id="import_plan_floor",
                    subject_id=cell_id,
                    subject_kind="projection_cell",
                )
            )
        if not _strings(row.get("validation_refs")):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_VALIDATION_REF_MISSING",
                    "Projection cell must name validation refs.",
                    case_id="import_plan_floor",
                    subject_id=cell_id,
                    subject_kind="projection_cell",
                )
            )
    if isinstance(missing_validation_negative, dict):
        rows = _rows(missing_validation_negative, "proposed_cells")
        if not rows:
            rows = [missing_validation_negative]
        for row in rows:
            if not _strings(row.get("validation_refs")):
                _record(
                    findings,
                    observed,
                    "MACRO_PROJECTION_VALIDATION_REF_MISSING",
                    "Projection import rejects cells without validation refs.",
                    case_id="missing_validation_ref",
                    subject_id=str(row.get("cell_id") or "projection_cell"),
                    subject_kind="negative_case",
                )
    blocking_findings = [
        row for row in findings if row.get("negative_case_id") == "import_plan_floor"
    ]
    return {
        "status": PASS
        if len(cells) >= 3 and target_refs and validation_refs and not blocking_findings
        else "blocked",
        "plan_id": plan.get("plan_id"),
        "projection_cell_count": len(cells),
        "projection_cell_ids": sorted(cell_ids),
        "target_refs": sorted(set(target_refs)),
        "validation_refs": sorted(set(validation_refs)),
        "next_best_lane": plan.get("next_best_lane"),
        "blocking_finding_count": len(blocking_findings),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _source_refs_for_material(row: dict[str, Any]) -> list[str]:
    source_refs = _strings(row.get("source_refs"))
    source_ref = row.get("source_ref")
    if isinstance(source_ref, str) and source_ref and source_ref not in source_refs:
        source_refs.insert(0, source_ref)
    return source_refs


def _classification_values(value: object) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    return _strings(value)


def _normalize_runtime_root_ref(ref: str) -> str:
    if ref.startswith(f"{STANDALONE_RUNTIME_ROOT_REF}/"):
        return ref[len(STANDALONE_RUNTIME_ROOT_REF) + 1 :]
    return ref


def _runtime_ref_leak_reason(ref: str) -> str | None:
    normalized = _normalize_runtime_root_ref(ref)
    if not normalized:
        return "empty_runtime_ref"
    if any(normalized.startswith(prefix) for prefix in STANDALONE_RUNTIME_BLOCKED_PREFIXES):
        return "blocked_runtime_prefix"
    if any(token in normalized for token in STANDALONE_RUNTIME_BLOCKED_TOKENS):
        return "blocked_runtime_token"
    if not any(normalized == prefix or normalized.startswith(prefix) for prefix in STANDALONE_RUNTIME_ALLOWED_PREFIXES):
        return "outside_microcosm_tree"
    return None


def _standalone_runtime_ref_rows(refs: list[str], *, role: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ref in refs:
        normalized = _normalize_runtime_root_ref(ref)
        leak_reason = _runtime_ref_leak_reason(ref)
        rows.append(
            {
                "ref": ref,
                "normalized_ref": normalized,
                "dependency_role": role,
                "status": PASS if leak_reason is None else "blocked",
                "leak_reason": leak_reason,
            }
        )
    return rows


def _runtime_dependency_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "runtime_dependencies")
    if rows:
        return rows
    if isinstance(payload, dict):
        ref = payload.get("runtime_ref") or payload.get("ref") or payload.get("path")
        if isinstance(ref, str) and ref:
            return [payload]
    return []


def _standalone_dependency_leaks(payload: object) -> list[dict[str, Any]]:
    leaks: list[dict[str, Any]] = []
    for row in _runtime_dependency_rows(payload):
        ref = str(row.get("runtime_ref") or row.get("ref") or row.get("path") or "")
        reason = _runtime_ref_leak_reason(ref)
        if row.get("macro_runtime_dependency") is True:
            reason = reason or "declared_macro_runtime_dependency"
        if reason is not None:
            leaks.append(
                {
                    "dependency_id": str(row.get("dependency_id") or row.get("case_id") or ref),
                    "ref": ref,
                    "dependency_role": str(row.get("dependency_role") or "runtime_required"),
                    "leak_reason": reason,
                    "body_in_receipt": False,
                }
            )
    return leaks


def validate_standalone_runtime_severance(
    standalone_negative: object | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for leak in _standalone_dependency_leaks(standalone_negative):
        _record(
            findings,
            observed,
            "MACRO_PROJECTION_STANDALONE_DEPENDENCY_LEAK",
            "Runtime severance rejects runtime dependencies on the live macro root.",
            case_id="standalone_dependency_leak",
            subject_id=str(leak["dependency_id"]),
            subject_kind="negative_case",
        )
    return {
        "status": PASS,
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _public_safe_body_import_rows(
    protocol_payload: dict[str, Any],
    *,
    import_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _rows(protocol_payload, "copied_material"):
        classification = _public_safe_import_status(row, import_policy=import_policy)
        if classification is None:
            continue
        findings = classification.get("findings", [])
        rows.append(
            {
                "material_id": str(row.get("material_id") or "public_safe_body_material"),
                "material_class": classification["material_class"],
                "source_refs": _source_refs_for_material(row),
                "target_ref": row.get("target_ref"),
                "credential_exposure_risk": classification["credential_exposure_risk"],
                "route": classification["route"],
                "public_safe_mode": classification["public_safe_mode"],
                "provenance_refs": _strings(row.get("provenance_refs")),
                "validation_refs": _strings(row.get("validation_refs")),
                "applied_edits": _strings(row.get("applied_edits")),
                "claim_ceiling": row.get("claim_ceiling"),
                "body_digest": row.get("body_digest"),
                "body_import_verification": row.get("body_import_verification")
                if isinstance(row.get("body_import_verification"), dict)
                else None,
                "classification": _classification_values(row.get("classification")),
                "body_copied": row.get("body_copied") is True,
                "body_text_in_receipt": False,
                "classification_status": classification["status"],
                "flow_allowed": classification["flow_allowed"] is True,
                "finding_count": len(findings),
                "error_codes": sorted(str(item.get("error_code") or "") for item in findings),
            }
        )
    return rows


def _projection_cell_rows(
    plan_payload: dict[str, Any],
    *,
    public_safe_imports_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for row in _rows(plan_payload, "proposed_cells"):
        cell_id = str(row.get("cell_id") or "projection_cell")
        source_refs = _strings(row.get("source_refs"))
        target_refs = _strings(row.get("target_refs"))
        validation_refs = _strings(row.get("validation_refs"))
        selected_pattern_ids = _strings(row.get("selected_pattern_ids"))
        body_material_ids = _strings(row.get("public_safe_body_material_ids"))
        missing_body_material_ids = sorted(
            material_id
            for material_id in body_material_ids
            if material_id not in public_safe_imports_by_id
        )
        body_material_rows = [
            public_safe_imports_by_id[material_id]
            for material_id in body_material_ids
            if material_id in public_safe_imports_by_id
        ]
        blocking_reasons: list[str] = []
        if not source_refs:
            blocking_reasons.append("source_refs_missing")
        if not target_refs:
            blocking_reasons.append("target_refs_missing")
        if not validation_refs:
            blocking_reasons.append("validation_refs_missing")
        if row.get("body_copied") is True or row.get("body_included") is True:
            blocking_reasons.append("body_copy_requested")
        if missing_body_material_ids:
            blocking_reasons.append("public_safe_body_material_missing")
        ready_to_project = not blocking_reasons
        copy_policy = PUBLIC_SAFE_BODY_COPY_POLICY if body_material_rows else METADATA_COPY_POLICY
        if ready_to_project:
            state = dict(
                CELL_STATUS_OVERRIDES.get(
                    cell_id,
                    {
                        "projection_status": "ready_for_projection",
                        "cell_state": "ready_import_cell",
                        "action_required": True,
                        "status_reason": (
                            "Cell has source, target, and validation refs but has no landed "
                            "public runtime import recorded in the projection status protocol."
                        ),
                        "landed_evidence_refs": [],
                        "next_runtime_surface": row.get("next_runtime_surface"),
                    },
                )
            )
        else:
            state = {
                "projection_status": "blocked",
                "cell_state": "blocked_import_cell",
                "action_required": True,
                "status_reason": "Cell cannot enter public projection until blocking reasons clear.",
                "landed_evidence_refs": [],
                "next_runtime_surface": row.get("next_runtime_surface"),
            }
        cells.append(
            {
                "cell_id": cell_id,
                "selected_pattern_ids": selected_pattern_ids,
                "source_refs": source_refs,
                "target_refs": target_refs,
                "validation_refs": validation_refs,
                "source_ref_count": len(source_refs),
                "target_ref_count": len(target_refs),
                "validation_ref_count": len(validation_refs),
                "copy_policy": copy_policy,
                "public_safe_body_material_ids": body_material_ids,
                "public_safe_body_material_count": len(body_material_rows),
                "public_safe_body_material_classes": sorted(
                    {
                        str(material.get("material_class") or "")
                        for material in body_material_rows
                        if material.get("material_class")
                    }
                ),
                "public_safe_body_import_routes": sorted(
                    {
                        str(material.get("route") or "")
                        for material in body_material_rows
                        if material.get("route")
                    }
                ),
                "classification": _classification_values(row.get("classification")),
                "missing_public_safe_body_material_ids": missing_body_material_ids,
                "authority_ceiling": row.get("authority_ceiling"),
                "body_copied": row.get("body_copied") is True,
                "body_in_receipt": False,
                "ready_to_project": ready_to_project,
                "blocking_reasons": blocking_reasons,
                "projection_status": state["projection_status"],
                "cell_state": state["cell_state"],
                "action_required": state["action_required"] is True,
                "status_reason": state["status_reason"],
                "landed_evidence_refs": _strings(state.get("landed_evidence_refs")),
                "next_runtime_surface": state.get("next_runtime_surface"),
            }
        )
    return cells


def _omitted_material_rows(protocol_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "material_id": str(row.get("material_id") or "omitted_material"),
            "omitted_class": str(row.get("omitted_class") or ""),
            "public_runtime_ref": row.get("public_runtime_ref"),
            "omission_receipt_ref": row.get("omission_receipt_ref"),
            "body_in_receipt": False,
        }
        for row in _rows(protocol_payload, "omitted_material")
    ]


def _build_projection_intake_board(
    payloads: dict[str, Any],
    *,
    protocol: dict[str, Any],
    cleaning_policy: dict[str, Any],
    import_plan: dict[str, Any],
    secret_scan: dict[str, Any],
    import_policy: dict[str, Any],
    input_mode: str,
    expected_negative_cases: dict[str, list[str]],
    observed_negative_cases: dict[str, list[str]],
    missing_negative_cases: list[str],
) -> dict[str, Any]:
    protocol_payload = (
        payloads.get("projection_protocol")
        if isinstance(payloads.get("projection_protocol"), dict)
        else {}
    )
    plan_payload = (
        payloads.get("import_plan") if isinstance(payloads.get("import_plan"), dict) else {}
    )
    public_safe_body_imports = _public_safe_body_import_rows(
        protocol_payload,
        import_policy=import_policy,
    )
    imports_by_id = {
        str(row.get("material_id")): row
        for row in public_safe_body_imports
        if row.get("material_id")
    }
    cell_rows = _projection_cell_rows(plan_payload, public_safe_imports_by_id=imports_by_id)
    ready_count = sum(1 for row in cell_rows if row["ready_to_project"])
    blocked_count = len(cell_rows) - ready_count
    status_counts = dict(
        sorted(Counter(str(row.get("projection_status") or "unknown") for row in cell_rows).items())
    )
    import_route_counts = dict(
        sorted(Counter(str(row.get("route") or "unknown") for row in public_safe_body_imports).items())
    )
    import_class_counts = dict(
        sorted(
            Counter(str(row.get("material_class") or "unknown") for row in public_safe_body_imports).items()
        )
    )
    open_actionable_count = sum(1 for row in cell_rows if row.get("action_required") is True)
    landed_count = sum(
        1 for row in cell_rows if str(row.get("projection_status") or "") in LANDING_PROJECTION_STATUSES
    )
    return {
        "schema_version": "macro_projection_import_intake_board_v1",
        "headline": "Macro source refs become import candidates; verified non-secret macro bodies flow only with source-to-target evidence and claim floors.",
        "input_mode": input_mode,
        "protocol_id": protocol["protocol_id"],
        "policy_id": cleaning_policy["policy_id"],
        "plan_id": import_plan["plan_id"],
        "allowed_material": [
            "metadata",
            "fixture shape",
            "standard schema",
            "receipt summary",
            "public-root replacement ref",
            "verified non-secret macro body",
        ],
        "allowed_material_classes": _strings(protocol_payload.get("material_classes")),
        "forbidden_material_classes": cleaning_policy["forbidden_material_classes"],
        "omitted_material": _omitted_material_rows(protocol_payload),
        "omitted_material_count": len(_omitted_material_rows(protocol_payload)),
        "public_safe_body_imports": public_safe_body_imports,
        "public_safe_body_import_count": len(public_safe_body_imports),
        "public_safe_body_import_routes": import_route_counts,
        "public_safe_body_import_classes": import_class_counts,
        "projection_cells": cell_rows,
        "projection_cell_count": len(cell_rows),
        "ready_cell_count": ready_count,
        "blocked_cell_count": blocked_count,
        "projection_status_protocol": CELL_STATUS_PROTOCOL,
        "projection_status_counts": status_counts,
        "open_actionable_cell_count": open_actionable_count,
        "landed_cell_count": landed_count,
        "consumed_cell_count": landed_count,
        "negative_case_coverage_status": PASS if not missing_negative_cases else "blocked",
        "expected_negative_case_count": len(expected_negative_cases),
        "observed_negative_case_count": len(observed_negative_cases),
        "missing_negative_cases": missing_negative_cases,
        "secret_exclusion_blocking_hit_count": secret_scan.get("blocking_hit_count"),
        "next_best_lane": import_plan["next_best_lane"],
        "authority_ceiling": AUTHORITY_CEILING,
        "release_authorized": False,
        "publication_authorized": False,
        "private_data_equivalence_claim": False,
        "body_in_receipt": False,
    }


def _build_runtime_severance_board(
    projection_intake_board: dict[str, Any],
    *,
    protocol: dict[str, Any],
    import_plan: dict[str, Any],
    dependency_preflight_gate: dict[str, Any],
) -> dict[str, Any]:
    runtime_rows: list[dict[str, Any]] = []
    seen_runtime: set[tuple[str, str]] = set()

    def add_runtime_refs(refs: list[str], *, role: str) -> None:
        for row in _standalone_runtime_ref_rows(refs, role=role):
            key = (str(row["ref"]), role)
            if key in seen_runtime:
                continue
            seen_runtime.add(key)
            runtime_rows.append(row)

    origin_refs: set[str] = set(protocol["source_refs"])
    for row in projection_intake_board["public_safe_body_imports"]:
        origin_refs.update(_strings(row.get("source_refs")))
        origin_refs.update(_strings(row.get("provenance_refs")))
        target_ref = row.get("target_ref")
        add_runtime_refs([target_ref] if isinstance(target_ref, str) else [], role="imported_body_target")
        add_runtime_refs(_strings(row.get("validation_refs")), role="import_validation")

    for row in projection_intake_board["projection_cells"]:
        origin_refs.update(_strings(row.get("source_refs")))
        add_runtime_refs(_strings(row.get("target_refs")), role="projection_cell_target")
        add_runtime_refs(_strings(row.get("validation_refs")), role="projection_cell_validation")
        add_runtime_refs(_strings(row.get("landed_evidence_refs")), role="landed_evidence")

    leaked_runtime_rows = [
        row for row in runtime_rows if row.get("status") != PASS
    ]
    findings = [
        _finding(
            "MACRO_PROJECTION_STANDALONE_DEPENDENCY_LEAK",
            "Runtime refs must resolve inside the Microcosm tree; macro-origin refs are provenance only.",
            case_id="runtime_severance_floor",
            subject_id=str(row.get("ref") or "runtime_dependency"),
            subject_kind="runtime_severance_dependency",
        )
        for row in leaked_runtime_rows
    ]
    findings.extend(dependency_preflight_gate.get("findings", []))
    runtime_dependency_status = PASS if not leaked_runtime_rows else "blocked"
    status = (
        PASS
        if runtime_dependency_status == PASS and dependency_preflight_gate.get("status") == PASS
        else "blocked"
    )
    return {
        "schema_version": "macro_projection_runtime_severance_board_v1",
        "status": status,
        "runtime_severance_status": status,
        "standalone_runtime_candidate": status == PASS,
        "standalone_runtime_root": STANDALONE_RUNTIME_ROOT_REF,
        "source_to_standalone_policy": "copy_vendor_rewrite_or_replace_then_run_without_private_root",
        "macro_origin_ref_policy": MACRO_ORIGIN_REF_POLICY,
        "macro_origin_refs": sorted(origin_refs),
        "macro_origin_ref_count": len(origin_refs),
        "macro_origin_refs_runtime_required": False,
        "runtime_dependency_status": runtime_dependency_status,
        "runtime_dependency_refs": sorted({str(row["ref"]) for row in runtime_rows}),
        "runtime_dependency_count": len(runtime_rows),
        "macro_runtime_dependency_count": len(leaked_runtime_rows),
        "runtime_dependencies": sorted(
            runtime_rows,
            key=lambda row: (str(row.get("dependency_role") or ""), str(row.get("ref") or "")),
        ),
        "blocked_runtime_dependencies": leaked_runtime_rows,
        "public_safe_body_import_count": projection_intake_board["public_safe_body_import_count"],
        "public_safe_body_import_routes": projection_intake_board["public_safe_body_import_routes"],
        "public_safe_body_import_classes": projection_intake_board["public_safe_body_import_classes"],
        "projection_cell_count": import_plan["projection_cell_count"],
        "ready_projection_cell_count": projection_intake_board["ready_cell_count"],
        "dependency_preflight_gate_status": dependency_preflight_gate["status"],
        "dependency_preflight_receipt_ref": dependency_preflight_gate["receipt_ref"],
        "organ_lifecycle_coverage_status": dependency_preflight_gate[
            "organ_lifecycle_coverage_status"
        ],
        "organ_lifecycle_coverage_counts": dependency_preflight_gate["coverage_counts"],
        "dependency_preflight_gate": dependency_preflight_gate,
        "claim_ceiling": AUTHORITY_CEILING,
        "release_authorized": False,
        "publication_authorized": False,
        "private_data_equivalence_claim": False,
        "severance_checks": [
            {
                "check_id": "macro_origin_refs_are_provenance_only",
                "status": PASS,
            },
            {
                "check_id": "runtime_refs_stay_inside_microcosm_tree",
                "status": runtime_dependency_status,
            },
            {
                "check_id": "organ_lifecycle_coverage_preflight_passes",
                "status": dependency_preflight_gate["status"],
            },
            {
                "check_id": "claim_ceiling_remains_false_for_release_and_private_equivalence",
                "status": PASS,
            },
        ],
        "findings": findings,
        "body_in_receipt": False,
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    dependency_preflight_gate = _dependency_preflight_lifecycle_gate(public_root)

    protocol = validate_projection_protocol(
        payloads["projection_protocol"],
        payloads.get("forbidden_body_import_overclaim"),
        payloads.get("missing_omission_receipt"),
        payloads.get("authority_upgrade_overclaim"),
        payloads.get("release_or_private_equivalence_overclaim"),
        import_policy=policy,
        public_root=public_root,
    )
    cleaning_policy = validate_cleaning_policy(payloads["cleaning_policy"])
    standalone_negative = validate_standalone_runtime_severance(
        payloads.get("standalone_dependency_leak")
    )
    public_safe_material_ids = {
        str(row.get("material_id"))
        for row in _public_safe_body_import_rows(payloads["projection_protocol"], import_policy=policy)
        if row.get("material_id")
    }
    import_plan = validate_import_plan(
        payloads["import_plan"],
        payloads.get("missing_validation_ref"),
        public_safe_material_ids=public_safe_material_ids,
    )
    observed = _merge_observed(
        protocol,
        cleaning_policy,
        import_plan,
        standalone_negative,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(protocol, cleaning_policy, import_plan, standalone_negative)
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    projection_intake_board = _build_projection_intake_board(
        payloads,
        protocol=protocol,
        cleaning_policy=cleaning_policy,
        import_plan=import_plan,
        secret_scan=secret_scan,
        import_policy=policy,
        input_mode=input_mode,
        expected_negative_cases=expected,
        observed_negative_cases=observed,
        missing_negative_cases=missing,
    )
    runtime_severance_board = _build_runtime_severance_board(
        projection_intake_board,
        protocol=protocol,
        import_plan=import_plan,
        dependency_preflight_gate=dependency_preflight_gate,
    )
    findings = sorted(
        [
            *findings,
            *runtime_severance_board["findings"],
        ],
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and protocol["status"] == PASS
        and cleaning_policy["status"] == PASS
        and import_plan["status"] == PASS
        and runtime_severance_board["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "macro_projection_import_protocol_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": protocol["protocol_id"],
        "policy_id": cleaning_policy["policy_id"],
        "plan_id": import_plan["plan_id"],
        "source_ref_count": len(protocol["source_refs"]),
        "public_runtime_ref_count": len(protocol["public_runtime_refs"]),
        "validation_ref_count": len(set(protocol["validation_refs"] + import_plan["validation_refs"])),
        "public_safe_body_material_count": protocol["public_safe_body_material_count"],
        "public_safe_body_import_status": (
            "pass"
            if protocol["public_safe_body_material_count"]
            and protocol["public_safe_body_target_status"] == PASS
            else "blocked"
            if protocol["public_safe_body_material_count"]
            else "not_present"
        ),
        "public_safe_body_target_status": protocol["public_safe_body_target_status"],
        "public_safe_body_target_refs": protocol["public_safe_body_target_refs"],
        "public_safe_body_digest_count": protocol["public_safe_body_digest_count"],
        "public_safe_body_import_count": projection_intake_board["public_safe_body_import_count"],
        "public_safe_body_import_routes": projection_intake_board["public_safe_body_import_routes"],
        "runtime_severance_status": runtime_severance_board["runtime_severance_status"],
        "runtime_dependency_status": runtime_severance_board["runtime_dependency_status"],
        "dependency_preflight_gate_status": runtime_severance_board[
            "dependency_preflight_gate_status"
        ],
        "dependency_preflight_receipt_ref": runtime_severance_board[
            "dependency_preflight_receipt_ref"
        ],
        "organ_lifecycle_coverage_status": runtime_severance_board[
            "organ_lifecycle_coverage_status"
        ],
        "organ_lifecycle_coverage_counts": runtime_severance_board[
            "organ_lifecycle_coverage_counts"
        ],
        "macro_runtime_dependency_count": runtime_severance_board[
            "macro_runtime_dependency_count"
        ],
        "macro_origin_ref_count": runtime_severance_board["macro_origin_ref_count"],
        "projection_cell_count": import_plan["projection_cell_count"],
        "ready_projection_cell_count": projection_intake_board["ready_cell_count"],
        "blocked_projection_cell_count": projection_intake_board["blocked_cell_count"],
        "projection_cell_ids": import_plan["projection_cell_ids"],
        "source_refs": protocol["source_refs"],
        "public_runtime_refs": sorted(
            set(protocol["public_runtime_refs"] + import_plan["target_refs"])
        ),
        "validation_refs": sorted(set(protocol["validation_refs"] + import_plan["validation_refs"])),
        "forbidden_material_classes": cleaning_policy["forbidden_material_classes"],
        "next_best_lane": import_plan["next_best_lane"],
        "projection_board": {
            "headline": "Macro material enters Microcosm as verified non-secret substrate; only secrets, credentials, operator conversation bodies, provider payloads, and account-bound material stay blocked.",
            "protocol_id": protocol["protocol_id"],
            "allowed_material": [
                "metadata",
                "fixture shape",
                "standard schema",
                "receipt summary",
                "public-root replacement ref",
                "verified non-secret macro body",
            ],
            "forbidden_material_classes": cleaning_policy["forbidden_material_classes"],
            "public_safe_body_material_count": protocol["public_safe_body_material_count"],
            "public_safe_body_import_count": projection_intake_board["public_safe_body_import_count"],
            "public_safe_body_import_routes": projection_intake_board["public_safe_body_import_routes"],
            "runtime_severance_status": runtime_severance_board["runtime_severance_status"],
            "runtime_dependency_status": runtime_severance_board["runtime_dependency_status"],
            "dependency_preflight_gate_status": runtime_severance_board[
                "dependency_preflight_gate_status"
            ],
            "organ_lifecycle_coverage_status": runtime_severance_board[
                "organ_lifecycle_coverage_status"
            ],
            "runtime_severance_board_embedded": True,
            "projection_cell_count": import_plan["projection_cell_count"],
            "next_best_lane": import_plan["next_best_lane"],
            "release_authorized": False,
            "private_data_equivalence_claim": False,
            "body_in_receipt": False,
            "intake_board_ref": INTAKE_BOARD_NAME,
        },
        "projection_intake_board": projection_intake_board,
        "runtime_severance_board": runtime_severance_board,
        "body_in_receipt": False,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "input_mode",
        "bundle_id",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "protocol_id",
        "policy_id",
        "plan_id",
        "source_ref_count",
        "public_runtime_ref_count",
        "validation_ref_count",
        "public_safe_body_material_count",
        "public_safe_body_import_status",
        "public_safe_body_import_count",
        "public_safe_body_import_routes",
        "runtime_severance_status",
        "runtime_dependency_status",
        "dependency_preflight_gate_status",
        "dependency_preflight_receipt_ref",
        "organ_lifecycle_coverage_status",
        "organ_lifecycle_coverage_counts",
        "macro_runtime_dependency_count",
        "macro_origin_ref_count",
        "projection_cell_count",
        "ready_projection_cell_count",
        "blocked_projection_cell_count",
        "projection_cell_ids",
        "source_refs",
        "public_runtime_refs",
        "validation_refs",
        "forbidden_material_classes",
        "next_best_lane",
        "runtime_severance_board",
        "body_in_receipt",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "macro_projection_import_protocol_result": target / RESULT_NAME,
        "projection_import_board": target / BOARD_NAME,
        "projection_import_intake_board": target / INTAKE_BOARD_NAME,
        "projection_import_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = [_display(path, public_root=public_root_path) for path in paths.values()]

    result_receipt = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["projection_board"])
    intake_board = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_intake_board_v1",
        receipt_paths=receipt_paths,
    )
    intake_board.update(result["projection_intake_board"])
    validation = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "forbidden_body_import_rejected": "forbidden_body_import_overclaim"
            in result["observed_negative_cases"],
            "omission_receipts_required": "missing_omission_receipt"
            in result["observed_negative_cases"],
            "authority_upgrades_rejected": "authority_upgrade_overclaim"
            in result["observed_negative_cases"],
            "validation_refs_required": "missing_validation_ref"
            in result["observed_negative_cases"],
            "release_and_equivalence_overclaims_rejected": "release_or_private_equivalence_overclaim"
            in result["observed_negative_cases"],
            "standalone_dependency_leaks_rejected": "standalone_dependency_leak"
            in result["observed_negative_cases"],
            "projection_intake_board_ref": _display(
                paths["projection_import_intake_board"], public_root=public_root_path
            ),
            "ready_projection_cell_count": result["ready_projection_cell_count"],
            "blocked_projection_cell_count": result["blocked_projection_cell_count"],
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "projection_import_boundary": "verified_body_import_or_secret_exclusion_only",
            "runtime_severance_boundary": (
                "macro_origin_provenance_only_public_runtime_tree_required"
            ),
            "runtime_severance_status": result["runtime_severance_status"],
        }
    )

    write_json_atomic(paths["macro_projection_import_protocol_result"], result_receipt)
    write_json_atomic(paths["projection_import_board"], board)
    write_json_atomic(paths["projection_import_intake_board"], intake_board)
    write_json_atomic(paths["projection_import_validation_receipt"], validation)
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.macro_projection_import_protocol run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_projection_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.macro_projection_import_protocol "
        f"run-projection-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_projection_import_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    receipt_path = target / BUNDLE_RESULT_NAME
    result["receipt_paths"] = [_display(receipt_path, public_root=public_root)]
    write_json_atomic(receipt_path, result)
    return result


def preview_import_plan(input_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    input_path = Path(input_dir)
    include_negative = all((input_path / name).is_file() for name in NEGATIVE_INPUT_NAMES)
    command_text = command or (
        "python -m microcosm_core.organs.macro_projection_import_protocol "
        f"plan --input {input_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture" if include_negative else "exported_projection_import_bundle",
        include_negative=include_negative,
    )
    return {
        "schema_version": "macro_projection_import_intake_preview_v1",
        "created_at": result["created_at"],
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "validator_id": VALIDATOR_ID,
        "command": command_text,
        "input_mode": result["input_mode"],
        "projection_intake_board": result["projection_intake_board"],
        "runtime_severance_board": result["runtime_severance_board"],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "release_authorized": False,
        "publication_authorized": False,
        "private_data_equivalence_claim": False,
        "body_in_receipt": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate macro projection import protocol")
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("run-projection-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--input", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out)
    elif args.action == "plan":
        result = preview_import_plan(args.input)
    else:
        result = run_projection_bundle(args.input, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
