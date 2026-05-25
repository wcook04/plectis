from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_computer_use_trace,
)
from microcosm_core.macro_tools.agent_trace_route_repair import (
    build_public_agent_trace_route_repair_view,
    load_public_agent_trace_route_repair_bundle,
)
from microcosm_core.macro_tools.agent_observability_store import (
    build_public_agent_observability_store_view,
    load_public_agent_observability_store_bundle,
)
from microcosm_core.macro_tools.finance_eval_spine import (
    REQUIRED_MODULES as FINANCE_EVAL_REQUIRED_MODULES,
)
from microcosm_core.organs.agent_route_observability_runtime import (
    run_agent_observability_store_bundle,
    run_agent_trace_route_repair_bundle,
    run_bridge_dispatch_yield_resume_bundle,
    run_controller_heartbeat_bundle,
    run_multi_agent_fanin_bundle,
    run_session_attribution_bundle,
)
from microcosm_core.macro_tools.work_landing import (
    build_public_work_landing_reconcile_plan,
    build_public_work_landing_status,
    build_public_workitem_write_admission,
)
from microcosm_core.organs.macro_projection_import_protocol import (
    EXPECTED_NEGATIVE_CASES,
    preview_import_plan,
    run,
    run_projection_bundle,
    validate_import_plan,
    validate_projection_protocol,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
)
COMPUTER_USE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_computer_use_action_trace_bundle"
)
SESSION_ATTRIBUTION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_session_attribution_bundle"
)
MULTI_AGENT_FANIN_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_multi_agent_fanin_replay_bundle"
)
BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_bridge_dispatch_yield_resume_bundle"
)
CONTROLLER_HEARTBEAT_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_controller_heartbeat_bundle"
)
AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_agent_trace_route_repair_bundle"
)
AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_agent_observability_store_bundle"
)
ROUTE_PLANE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/navigation_hologram_route_plane/exported_route_plane_bundle"
)
FINANCE_EVAL_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle"
)
DEPENDENCY_PREFLIGHT_RECEIPT = (
    MICROCOSM_ROOT / "receipts/preflight/dependency_preflight.json"
)
FINANCE_EVAL_BODY_MATERIAL_IDS = [
    f"finance_{Path(module).stem}_body_import"
    for module in FINANCE_EVAL_REQUIRED_MODULES
]
WORK_LANDING_CONTROL_BODY_MATERIAL_IDS = [
    "work_landing_status_body_import",
    "mission_transaction_landing_preflight_body_import",
    "work_landing_control_tool_body_import",
    "mission_transaction_preflight_tool_body_import",
    "scoped_commit_tool_body_import",
]
TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS = [
    "task_ledger_events_body_import",
    "task_ledger_apply_tool_body_import",
    "task_ledger_priority_body_import",
    "task_ledger_project_tool_body_import",
]
WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS = [
    "work_ledger_tool_body_import",
    "work_ledger_event_body_import",
    "work_ledger_runtime_body_import",
    "work_ledger_standard_body_import",
]


def _copy_dependency_preflight_receipt(public_root: Path) -> Path:
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEPENDENCY_PREFLIGHT_RECEIPT, receipt)
    return receipt


def _align_organ_registry_to_dependency_preflight(public_root: Path) -> None:
    receipt = json.loads(
        (public_root / "receipts/preflight/dependency_preflight.json").read_text(
            encoding="utf-8"
        )
    )
    expected_count = receipt["organ_lifecycle_coverage"]["coverage_counts"][
        "accepted_organ_count"
    ]
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    accepted_rows = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]
    keep_ids = {row["organ_id"] for row in accepted_rows[:expected_count]}
    registry["implemented_organs"] = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") != "accepted_current_authority" or row["organ_id"] in keep_ids
    ]
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_public_file(public_root: Path, rel_path: str) -> None:
    destination = public_root / rel_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / rel_path, destination)


def _copy_macro_projection_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol",
        public_root / "fixtures/first_wave/macro_projection_import_protocol",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/macro_projection_import_protocol",
        public_root / "examples/macro_projection_import_protocol",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/organs/mission_transaction_work_spine.py",
    )
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/__init__.py")
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_execution_trace.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_trace_route_repair.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_observability_store.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_session_attribution.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/continuation_packet.py",
    )
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/bridge_resume.py")
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/controller_heartbeat.py")
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/work_landing.py")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )
    _copy_public_file(
        public_root,
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/finance_forecast_evaluation_spine",
        public_root / "examples/finance_forecast_evaluation_spine",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/work_landing_control_spine",
        public_root / "examples/work_landing_control_spine",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mission_transaction_work_spine",
        public_root / "examples/mission_transaction_work_spine",
    )
    _copy_public_file(
        public_root,
        "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/"
        "lake_project/MicrocosmProofWitness/CertificateKernel.lean",
    )
    _copy_dependency_preflight_receipt(public_root)
    _align_organ_registry_to_dependency_preflight(public_root)
    return public_root


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def test_macro_projection_import_protocol_observes_negative_cases(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        tmp_path / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/macro_projection_import_protocol_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["projection_cell_count"] == 14
    assert result["ready_projection_cell_count"] == 14
    assert result["blocked_projection_cell_count"] == 0
    assert result["source_ref_count"] >= 2
    assert result["public_runtime_ref_count"] >= 2
    assert result["validation_ref_count"] >= 2
    assert result["public_safe_body_material_count"] == 33
    assert result["public_safe_body_import_status"] == "pass"
    assert result["runtime_severance_status"] == "pass"
    assert result["runtime_dependency_status"] == "pass"
    assert result["dependency_preflight_gate_status"] == "pass"
    assert result["dependency_preflight_receipt_ref"] == (
        "receipts/preflight/dependency_preflight.json"
    )
    assert result["organ_lifecycle_coverage_status"] == "pass"
    assert result["organ_lifecycle_coverage_counts"]["accepted_organ_count"] == 46
    assert (
        result["organ_lifecycle_coverage_counts"][
            "public_authority_expected_organ_count"
        ]
        == 44
    )
    assert result["macro_runtime_dependency_count"] == 0
    assert result["authority_ceiling"]["credential_or_account_bound_bodies_exported"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["projection_board"]["next_best_lane"] == "real_substrate_import_path"
    assert result["projection_board"]["intake_board_ref"] == "projection_import_intake_board.json"
    assert result["projection_board"]["runtime_severance_board_embedded"] is True
    assert result["projection_intake_board"]["ready_cell_count"] == 14
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["landed_cell_count"] == 14
    assert result["projection_intake_board"]["projection_status_counts"] == {
        "public_runtime_import_landed": 12,
        "runtime_bridge_landed": 1,
        "self_hosted_status_protocol_landed": 1,
    }
    assert result["projection_intake_board"]["omitted_material_count"] == 2
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 33
    assert result["projection_intake_board"]["public_safe_body_import_routes"] == {
        "verified_light_edit": 33
    }
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert by_material["ledger_row_metadata_projection"]["material_class"] == (
        "public_macro_pattern_body"
    )
    assert by_material["ledger_row_metadata_projection"]["classification_status"] == "pass"
    assert by_material["ledger_row_metadata_projection"]["body_text_in_receipt"] is False
    assert by_material["ledger_row_metadata_projection"]["body_import_verification"][
        "verification_mode"
    ] == "exact_source_digest_match"
    assert by_material["lean_certificate_kernel_body_import"]["material_class"] == (
        "public_macro_proof_body"
    )
    assert by_material["lean_certificate_kernel_body_import"]["classification_status"] == "pass"
    assert by_material["lean_certificate_kernel_body_import"]["body_text_in_receipt"] is False
    assert by_material["lean_certificate_kernel_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "exact_source_digest_match"
    assert by_material["work_landing_tool_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["work_landing_tool_body_import"]["classification_status"] == "pass"
    assert by_material["work_landing_tool_body_import"]["body_text_in_receipt"] is False
    assert by_material["work_landing_tool_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/work_landing.py"
    )
    assert by_material["work_landing_tool_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["agent_execution_trace_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_execution_trace_body_import"]["classification_status"] == "pass"
    assert by_material["agent_execution_trace_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_execution_trace_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
    assert by_material["agent_trace_route_repair_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_trace_route_repair_body_import"]["classification_status"] == "pass"
    assert by_material["agent_trace_route_repair_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_trace_route_repair_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_trace_route_repair.py"
    )
    assert by_material["agent_trace_route_repair_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["agent_observability_store_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_observability_store_body_import"]["classification_status"] == "pass"
    assert by_material["agent_observability_store_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_observability_store_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_observability_store.py"
    )
    assert by_material["agent_observability_store_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["agent_session_attribution_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_session_attribution_body_import"]["classification_status"] == "pass"
    assert by_material["agent_session_attribution_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_session_attribution_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_session_attribution.py"
    )
    assert by_material["agent_session_attribution_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "exact_source_digest_match"
    assert by_material["continuation_packet_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["continuation_packet_body_import"]["classification_status"] == "pass"
    assert by_material["continuation_packet_body_import"]["body_text_in_receipt"] is False
    assert by_material["continuation_packet_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/continuation_packet.py"
    )
    assert by_material["continuation_packet_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["bridge_resume_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["bridge_resume_body_import"]["classification_status"] == "pass"
    assert by_material["bridge_resume_body_import"]["body_text_in_receipt"] is False
    assert by_material["bridge_resume_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/bridge_resume.py"
    )
    assert by_material["bridge_resume_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["controller_heartbeat_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["controller_heartbeat_body_import"]["classification_status"] == "pass"
    assert by_material["controller_heartbeat_body_import"]["body_text_in_receipt"] is False
    assert by_material["controller_heartbeat_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/controller_heartbeat.py"
    )
    assert by_material["controller_heartbeat_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["navigation_route_plane_body_import"]["material_class"] == (
        "public_macro_receipt_body"
    )
    assert by_material["navigation_route_plane_body_import"]["classification_status"] == "pass"
    assert by_material["navigation_route_plane_body_import"]["body_text_in_receipt"] is False
    assert by_material["navigation_route_plane_body_import"]["target_ref"] == (
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json"
    )
    for material_id in FINANCE_EVAL_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in WORK_LANDING_CONTROL_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
        assert (
            by_material[material_id]["body_import_verification"]["source_line_count"]
            == by_material[material_id]["body_import_verification"]["target_line_count"]
        )
    assert result["projection_intake_board"]["negative_case_coverage_status"] == "pass"
    assert (
        result["projection_intake_board"]["projection_status_protocol"]["status_field"]
        == "projection_status"
    )
    by_cell = {
        row["cell_id"]: row for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["formal_math_readiness_extensions"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["formal_math_readiness_extensions"]["public_safe_body_material_ids"] == [
        "lean_certificate_kernel_body_import"
    ]
    assert by_cell["projection_protocol_self_host"]["projection_status"] == (
        "self_hosted_status_protocol_landed"
    )
    assert by_cell["projection_protocol_self_host"]["action_required"] is False
    assert by_cell["projection_protocol_self_host"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["projection_protocol_self_host"]["public_safe_body_material_ids"] == [
        "ledger_row_metadata_projection"
    ]
    assert by_cell["runtime_reveal_import_bridge"]["projection_status"] == "runtime_bridge_landed"
    assert by_cell["runtime_reveal_import_bridge"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["runtime_reveal_import_bridge"]["public_safe_body_material_ids"] == [
        "work_landing_tool_body_import"
    ]
    assert by_cell["agent_execution_trace_refactor"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_execution_trace_refactor"]["public_safe_body_material_ids"] == [
        "agent_execution_trace_body_import"
    ]
    assert by_cell["agent_trace_route_repair_observability_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_trace_route_repair_observability_import"][
        "public_safe_body_material_ids"
    ] == [
        "agent_trace_route_repair_body_import"
    ]
    assert by_cell["agent_observability_store_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_observability_store_import"][
        "public_safe_body_material_ids"
    ] == [
        "agent_observability_store_body_import"
    ]
    assert by_cell["agent_session_attribution_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_session_attribution_import"]["public_safe_body_material_ids"] == [
        "agent_session_attribution_body_import"
    ]
    assert by_cell["multi_agent_fanin_replay_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["multi_agent_fanin_replay_import"]["public_safe_body_material_ids"] == [
        "continuation_packet_body_import",
        "bridge_resume_body_import",
    ]
    assert by_cell["controller_continuity_heartbeat_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["controller_continuity_heartbeat_import"][
        "public_safe_body_material_ids"
    ] == [
        "controller_heartbeat_body_import",
    ]
    assert by_cell["navigation_route_plane_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["navigation_route_plane_import"]["public_safe_body_material_ids"] == [
        "navigation_route_plane_body_import"
    ]
    assert by_cell["finance_eval_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["finance_eval_source_modules_import"][
        "public_safe_body_material_ids"
    ] == FINANCE_EVAL_BODY_MATERIAL_IDS
    assert by_cell["finance_eval_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["finance_eval_source_modules_import"]["action_required"] is False
    assert by_cell["work_landing_control_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["work_landing_control_source_modules_import"][
        "public_safe_body_material_ids"
    ] == WORK_LANDING_CONTROL_BODY_MATERIAL_IDS
    assert by_cell["work_landing_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_landing_control_source_modules_import"]["action_required"] is False
    severance_board = result["runtime_severance_board"]
    assert severance_board["standalone_runtime_candidate"] is True
    assert severance_board["dependency_preflight_gate_status"] == "pass"
    assert severance_board["dependency_preflight_gate"]["status"] == "pass"
    assert severance_board["dependency_preflight_gate"]["defect_count"] == 0
    assert severance_board["organ_lifecycle_coverage_status"] == "pass"
    assert severance_board["organ_lifecycle_coverage_counts"]["runtime_step_count"] == 46
    assert {
        row["check_id"]: row["status"]
        for row in severance_board["severance_checks"]
    }["organ_lifecycle_coverage_preflight_passes"] == "pass"
    assert severance_board["macro_origin_ref_policy"] == (
        "macro_origin_refs_are_provenance_only_not_runtime_dependencies"
    )
    assert severance_board["macro_origin_refs_runtime_required"] is False
    assert severance_board["macro_runtime_dependency_count"] == 0
    assert severance_board["blocked_runtime_dependencies"] == []
    assert "tools/meta/control/work_landing.py" in severance_board["macro_origin_refs"]
    assert (
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/"
        "CertificateKernel.lean"
        in severance_board["macro_origin_refs"]
    )
    assert all(not ref.startswith("state/") for ref in severance_board["runtime_dependency_refs"])
    assert all(not ref.startswith("formal_math/") for ref in severance_board["runtime_dependency_refs"])
    assert all(not ref.startswith("tools/meta/") for ref in severance_board["runtime_dependency_refs"])
    assert (
        "src/microcosm_core/macro_tools/work_landing.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "src/microcosm_core/macro_tools/bridge_resume.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "src/microcosm_core/macro_tools/agent_execution_trace.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "src/microcosm_core/macro_tools/agent_trace_route_repair.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json"
        in severance_board["runtime_dependency_refs"]
    )
    assert any(
        receipt_ref.endswith("projection_import_intake_board.json")
        for receipt_ref in result["receipt_paths"]
    )


def test_macro_projection_import_protocol_receipts_are_public_relative_and_secret_only(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["runtime_severance_board"]["standalone_runtime_candidate"] is True
    assert result["runtime_severance_board"]["macro_runtime_dependency_count"] == 0
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_macro_projection_release_severance_requires_lifecycle_preflight(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    lifecycle = payload["organ_lifecycle_coverage"]
    lifecycle["status"] = "blocked"
    lifecycle["defect_count"] = 1
    lifecycle["defects"] = [
        {
            "defect_code": "missing_public_lens",
            "organ_id": "verifier_lab_execution_spine",
        }
    ]
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["runtime_dependency_status"] == "pass"
    assert result["runtime_severance_status"] == "blocked"
    assert result["dependency_preflight_gate_status"] == "blocked"
    assert result["organ_lifecycle_coverage_status"] == "blocked"
    assert "MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_BLOCKED" in result["error_codes"]
    severance_board = result["runtime_severance_board"]
    assert severance_board["dependency_preflight_gate"]["defects"][0]["defect_code"] == (
        "organ_lifecycle_coverage_blocked"
    )
    assert {
        row["check_id"]: row["status"]
        for row in severance_board["severance_checks"]
    }["organ_lifecycle_coverage_preflight_passes"] == "blocked"


def test_macro_projection_release_severance_blocks_stale_lifecycle_counts(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["organ_lifecycle_coverage"]["coverage_counts"]["organ_authority_row_count"] -= 1
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["dependency_preflight_gate_status"] == "blocked"
    assert result["organ_lifecycle_coverage_status"] == "pass"
    assert "MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_STALE" in result["error_codes"]
    defects = result["runtime_severance_board"]["dependency_preflight_gate"]["defects"]
    assert {
        row["subject_id"]
        for row in defects
        if row["defect_code"] == "organ_lifecycle_coverage_stale_count"
    } == {"organ_authority_row_count"}


def test_macro_projection_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["bundle_id"] == "macro_projection_import_protocol_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["projection_cell_count"] == 14
    assert result["projection_intake_board"]["ready_cell_count"] == 14
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_board"]["release_authorized"] is False
    assert result["projection_board"]["private_data_equivalence_claim"] is False
    assert result["public_safe_body_material_count"] == 33
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 33
    assert result["runtime_severance_status"] == "pass"
    assert result["runtime_severance_board"]["macro_origin_refs_runtime_required"] is False
    assert result["runtime_severance_board"]["macro_runtime_dependency_count"] == 0
    assert {
        row["material_id"]
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    } == {
        "ledger_row_metadata_projection",
        "lean_certificate_kernel_body_import",
        "work_landing_tool_body_import",
        "agent_execution_trace_body_import",
        "agent_trace_route_repair_body_import",
        "agent_observability_store_body_import",
        "agent_session_attribution_body_import",
        "continuation_packet_body_import",
        "bridge_resume_body_import",
        "controller_heartbeat_body_import",
        "navigation_route_plane_body_import",
        *FINANCE_EVAL_BODY_MATERIAL_IDS,
        *WORK_LANDING_CONTROL_BODY_MATERIAL_IDS,
        *TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS,
        *WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS,
    }
    assert result["public_safe_body_target_status"] == "pass"
    assert result["public_safe_body_digest_count"] == 33


def test_projection_protocol_rejects_claimed_body_without_target_or_real_digest(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    protocol_path = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        / "projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for row in protocol["copied_material"]:
        if row["material_id"] == "lean_certificate_kernel_body_import":
            (public_root / row["target_ref"]).unlink()
            row["body_digest"] = (
                "sha256:placeholder-lean-certificate-kernel"
            )
            break

    result = validate_projection_protocol(
        protocol,
        import_policy=json.loads(
            (public_root / "core/private_state_forbidden_classes.json").read_text(
                encoding="utf-8"
            )
        ),
        public_root=public_root,
    )

    assert result["status"] == "blocked"
    assert result["public_safe_body_target_status"] == "blocked"
    error_codes = {row["error_code"] for row in result["findings"]}
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_TARGET_MISSING" in error_codes
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_DIGEST_PLACEHOLDER" in error_codes


def test_projection_protocol_rejects_body_import_without_verification(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    protocol_path = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        / "projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for row in protocol["copied_material"]:
        if row["material_id"] == "lean_certificate_kernel_body_import":
            row.pop("body_import_verification", None)
            break

    result = validate_projection_protocol(
        protocol,
        import_policy=json.loads(
            (public_root / "core/private_state_forbidden_classes.json").read_text(
                encoding="utf-8"
            )
        ),
        public_root=public_root,
    )

    assert result["status"] == "blocked"
    assert result["public_safe_body_target_status"] == "blocked"
    error_codes = {row["error_code"] for row in result["findings"]}
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_VERIFICATION_MISSING" in error_codes


def test_projection_protocol_rejects_exact_import_when_source_ref_digest_lies(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    protocol_path = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        / "projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for row in protocol["copied_material"]:
        if row["material_id"] == "lean_certificate_kernel_body_import":
            row["source_ref"] = "tools/meta/control/work_landing.py"
            row["source_refs"] = ["tools/meta/control/work_landing.py"]
            row["body_import_verification"]["source_body_digest"] = (
                row["body_import_verification"]["target_body_digest"]
            )
            break

    result = validate_projection_protocol(
        protocol,
        import_policy=json.loads(
            (public_root / "core/private_state_forbidden_classes.json").read_text(
                encoding="utf-8"
            )
        ),
        public_root=public_root,
    )

    assert result["status"] == "blocked"
    assert result["public_safe_body_target_status"] == "blocked"
    error_codes = {row["error_code"] for row in result["findings"]}
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISMATCH" in error_codes


def test_macro_projection_import_plan_preview_is_non_writing(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = preview_import_plan(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["schema_version"] == "macro_projection_import_intake_preview_v1"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["projection_intake_board"]["ready_cell_count"] == 14
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["release_authorized"] is False
    assert "pattern_metadata" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 33
    assert result["projection_intake_board"]["public_safe_body_import_classes"] == {
        "public_macro_pattern_body": 1,
        "public_macro_proof_body": 1,
        "public_macro_receipt_body": 1,
        "public_macro_tool_body": 30,
    }
    assert result["runtime_severance_board"]["runtime_dependency_status"] == "pass"
    assert result["runtime_severance_board"]["macro_origin_refs_runtime_required"] is False
    assert all(
        row["selected_pattern_ids"]
        for row in result["projection_intake_board"]["projection_cells"]
    )
    assert "receipt_paths" not in result


def test_public_safe_macro_proof_body_is_importable_with_verification(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["public_safe_body_material_count"] == 33
    assert result["public_safe_body_import_status"] == "pass"
    assert "MACRO_PROJECTION_FORBIDDEN_BODY_IMPORT" not in result["error_codes"]
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["authority_ceiling"]["private_data_equivalence_claim"] is False
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert by_material["lean_certificate_kernel_body_import"]["route"] == (
        "verified_light_edit"
    )
    assert by_material["lean_certificate_kernel_body_import"]["source_refs"] == [
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/CertificateKernel.lean"
    ]
    assert by_material["lean_certificate_kernel_body_import"]["body_import_verification"][
        "source_body_digest"
    ] == by_material["lean_certificate_kernel_body_import"]["body_digest"]
    assert result["runtime_severance_board"]["runtime_severance_status"] == "pass"
    assert (
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/"
        "CertificateKernel.lean"
        not in result["runtime_severance_board"]["runtime_dependency_refs"]
    )


def test_pattern_ledger_body_is_imported_as_exact_copy(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    body_import_ids = {
        row["material_id"]
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert "ledger_row_metadata_projection" in body_import_ids
    protocol_rows = {
        row["material_id"]: row
        for row in json.loads(
            (
                public_root
                / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
                / "projection_protocol.json"
            ).read_text(encoding="utf-8")
        )["copied_material"]
    }
    ledger_row = protocol_rows["ledger_row_metadata_projection"]
    target = public_root / ledger_row["target_ref"]
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    assert target.is_file()
    assert target.read_text(encoding="utf-8").count("\n") == 373
    assert ledger_row["body_copied"] is True
    assert ledger_row["material_class"] == "public_macro_pattern_body"
    assert ledger_row["public_safe_mode"] == "direct_verified_macro_body"
    assert ledger_row["body_digest"] == digest
    assert ledger_row["body_import_verification"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert ledger_row["body_import_verification"]["source_body_digest"] == digest
    assert ledger_row["body_import_verification"]["target_body_digest"] == digest
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["projection_protocol_self_host"]["public_safe_body_material_ids"] == [
        "ledger_row_metadata_projection"
    ]


def test_work_landing_tool_body_is_imported_as_light_edit(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    body_import_ids = {
        row["material_id"]
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert "work_landing_tool_body_import" in body_import_ids
    protocol_rows = {
        row["material_id"]: row
        for row in json.loads(
            (
                public_root
                / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
                / "projection_protocol.json"
            ).read_text(encoding="utf-8")
        )["copied_material"]
    }
    work_landing_row = protocol_rows["work_landing_tool_body_import"]
    assert work_landing_row["body_copied"] is True
    assert work_landing_row["material_class"] == "public_macro_tool_body"
    assert work_landing_row["target_ref"] == "src/microcosm_core/macro_tools/work_landing.py"
    assert work_landing_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    status = build_public_work_landing_status(
        subject_ids=["cap_demo"],
        owned_paths=["microcosm-substrate/tests/test_macro_projection_import_protocol.py"],
    )
    reconcile = build_public_work_landing_reconcile_plan(
        subject_ids=["cap_demo"],
        owned_paths=["microcosm-substrate/tests/test_macro_projection_import_protocol.py"],
    )
    admission = build_public_workitem_write_admission(
        subject_ids=["cap_demo"],
        owned_paths=["microcosm-substrate/tests/test_macro_projection_import_protocol.py"],
    )
    assert status["status"] == "pass"
    assert status["landing_lane"] == "scoped_commit"
    assert reconcile["work_landing_reconcile_status"] == "ordered_dry_run_plan_emitted"
    assert admission["write_admitted"] is True
    assert status["body_in_receipt"] is False
    assert status["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False


def test_agent_execution_trace_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    agent_row = by_material["agent_execution_trace_body_import"]
    target = public_root / agent_row["target_ref"]
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    trace = build_public_computer_use_trace(COMPUTER_USE_BUNDLE_INPUT)

    assert target.is_file()
    assert agent_row["material_class"] == "public_macro_tool_body"
    assert agent_row["body_digest"] == digest
    assert agent_row["body_import_verification"]["target_body_digest"] == digest
    assert agent_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert trace["status"] == "pass"
    assert trace["span_count"] > 0
    assert trace["authority_ceiling"]["provider_payload_read"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_execution_trace_refactor"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_execution_trace_refactor"]["action_required"] is False


def test_agent_trace_route_repair_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    route_repair_row = by_material["agent_trace_route_repair_body_import"]
    target = public_root / route_repair_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/navigation_route_intervention.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    view = build_public_agent_trace_route_repair_view(
        load_public_agent_trace_route_repair_bundle(AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT)
    )
    replay = run_agent_trace_route_repair_bundle(
        AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert route_repair_row["material_class"] == "public_macro_tool_body"
    assert route_repair_row["body_digest"] == digest
    assert route_repair_row["body_import_verification"]["source_body_digest"] == source_digest
    assert route_repair_row["body_import_verification"]["target_body_digest"] == digest
    assert route_repair_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert view["status"] == "pass"
    assert view["route_repair_summary"]["suggested_route_count"] == 4
    assert replay["status"] == "pass"
    assert replay["suggested_route_count"] == 4
    assert replay["authority_ceiling"]["live_hook_install_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_trace_route_repair_observability_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["agent_trace_route_repair_observability_import"][
        "action_required"
    ] is False


def test_agent_observability_store_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    store_row = by_material["agent_observability_store_body_import"]
    target = public_root / store_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/agent_observability.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    view = build_public_agent_observability_store_view(
        load_public_agent_observability_store_bundle(AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT)
    )
    replay = run_agent_observability_store_bundle(
        AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert store_row["material_class"] == "public_macro_tool_body"
    assert store_row["body_digest"] == digest
    assert store_row["body_import_verification"]["source_body_digest"] == source_digest
    assert store_row["body_import_verification"]["target_body_digest"] == digest
    assert store_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert view["status"] == "pass"
    assert view["store_summary"]["event_count"] == 6
    assert replay["status"] == "pass"
    assert replay["accepted_event_count"] == 6
    assert replay["authority_ceiling"]["live_home_session_logs_read"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_observability_store_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_observability_store_import"]["action_required"] is False


def test_agent_session_attribution_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    attribution_row = by_material["agent_session_attribution_body_import"]
    target = public_root / attribution_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/agent_session_attribution.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_session_attribution_bundle(
        SESSION_ATTRIBUTION_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert attribution_row["material_class"] == "public_macro_tool_body"
    assert attribution_row["body_digest"] == digest
    assert attribution_row["body_import_verification"]["source_body_digest"] == source_digest
    assert attribution_row["body_import_verification"]["target_body_digest"] == digest
    assert attribution_row["body_import_verification"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert replay["status"] == "pass"
    assert replay["matched_session_count"] == 2
    assert replay["authority_ceiling"]["raw_transcript_body_exported"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_session_attribution_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_session_attribution_import"]["action_required"] is False


def test_continuation_packet_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    continuation_row = by_material["continuation_packet_body_import"]
    target = public_root / continuation_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/continuation_packet.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_multi_agent_fanin_bundle(
        MULTI_AGENT_FANIN_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert continuation_row["material_class"] == "public_macro_tool_body"
    assert continuation_row["body_digest"] == digest
    assert continuation_row["body_import_verification"]["source_body_digest"] == source_digest
    assert continuation_row["body_import_verification"]["target_body_digest"] == digest
    assert continuation_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert replay["status"] == "pass"
    assert replay["continuation_packet_count"] == 2
    assert replay["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["multi_agent_fanin_replay_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["multi_agent_fanin_replay_import"]["action_required"] is False


def test_bridge_resume_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    bridge_row = by_material["bridge_resume_body_import"]
    target = public_root / bridge_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "tools/meta/bridge/bridge_resume.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_bridge_dispatch_yield_resume_bundle(
        BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert bridge_row["material_class"] == "public_macro_tool_body"
    assert bridge_row["body_digest"] == digest
    assert bridge_row["body_import_verification"]["source_body_digest"] == source_digest
    assert bridge_row["body_import_verification"]["target_body_digest"] == digest
    assert bridge_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert replay["status"] == "pass"
    assert replay["trigger_written_count"] == 2
    assert replay["no_send_trigger_count"] == 2
    assert replay["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["multi_agent_fanin_replay_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["multi_agent_fanin_replay_import"]["public_safe_body_material_ids"] == [
        "continuation_packet_body_import",
        "bridge_resume_body_import",
    ]


def test_controller_heartbeat_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    controller_row = by_material["controller_heartbeat_body_import"]
    target = public_root / controller_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/controller_heartbeat.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_controller_heartbeat_bundle(
        CONTROLLER_HEARTBEAT_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert controller_row["material_class"] == "public_macro_tool_body"
    assert controller_row["body_digest"] == digest
    assert controller_row["body_import_verification"]["source_body_digest"] == source_digest
    assert controller_row["body_import_verification"]["target_body_digest"] == digest
    assert controller_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert replay["status"] == "pass"
    assert replay["heartbeat_count"] == 2
    assert replay["exact_5x5_count"] == 2
    assert replay["dedupe_duplicate_count"] == 1
    assert replay["authority_ceiling"]["seed_or_blackboard_read_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["controller_continuity_heartbeat_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["controller_continuity_heartbeat_import"]["action_required"] is False
    assert by_cell["controller_continuity_heartbeat_import"][
        "public_safe_body_material_ids"
    ] == [
        "controller_heartbeat_body_import",
    ]


def test_navigation_route_plane_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    route_row = by_material["navigation_route_plane_body_import"]
    target = public_root / route_row["target_ref"]
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    route_payload = json.loads((ROUTE_PLANE_BUNDLE_INPUT / "route_rows.json").read_text())

    assert target.is_file()
    assert route_row["material_class"] == "public_macro_receipt_body"
    assert route_row["body_digest"] == digest
    assert route_row["body_import_verification"]["target_body_digest"] == digest
    assert route_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert route_payload["body_material_status"] == (
        "copied_non_secret_macro_route_substrate_with_provenance"
    )
    assert route_payload["row_count"] == 41
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["navigation_route_plane_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["navigation_route_plane_import"]["action_required"] is False


def test_work_landing_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in WORK_LANDING_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target = public_root / row["target_ref"]
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["work_landing_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == WORK_LANDING_CONTROL_BODY_MATERIAL_IDS


def test_task_ledger_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["task_ledger_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS


def test_work_ledger_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["work_ledger_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS


def test_import_plan_rejects_missing_public_safe_body_material_id() -> None:
    result = validate_import_plan(
        {
            "plan_id": "missing_public_safe_body_material",
            "next_best_lane": "real_substrate_import_path",
            "proposed_cells": [
                {
                    "cell_id": "cell_with_missing_material",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example.json"],
                    "validation_refs": ["receipts/example.json"],
                    "public_safe_body_material_ids": ["missing_body_material"],
                },
                {
                    "cell_id": "cell_two",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example-two.json"],
                    "validation_refs": ["receipts/example-two.json"],
                },
                {
                    "cell_id": "cell_three",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example-three.json"],
                    "validation_refs": ["receipts/example-three.json"],
                },
            ],
        },
        public_safe_material_ids={"known_body_material"},
    )

    assert result["status"] == "blocked"
    assert result["blocking_finding_count"] == 1
    assert result["findings"][0]["error_code"] == (
        "MACRO_PROJECTION_PUBLIC_SAFE_BODY_MATERIAL_MISSING"
    )
