from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_sandbox_policy_trace,
)
import microcosm_core.organs.agent_sandbox_policy_escape_replay as sandbox_replay
from microcosm_core.organs.agent_sandbox_policy_escape_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_sandbox_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/agent_sandbox_policy_escape_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_sandbox_policy_escape_replay/"
    "exported_sandbox_policy_escape_bundle"
)
FIXTURE_MANIFESTS = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_sandbox_policy_escape_replay/fixture_manifest.json",
    MICROCOSM_ROOT
    / "core/fixture_manifests/agent_sandbox_policy_escape_replay.fixture_manifest.json",
)
SOURCE_ROOT = MICROCOSM_ROOT.parent


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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


def _copy_fixture_public_root(tmp_path: Path) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    copied_fixture = (
        public_root / "fixtures/first_wave/agent_sandbox_policy_escape_replay"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_sandbox_policy_escape_replay",
        copied_fixture,
    )
    return public_root, copied_fixture / "input"


def test_agent_sandbox_policy_escape_rejects_semantic_policy_side_effect_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    copied_fixture = (
        public_root / "fixtures/first_wave/agent_sandbox_policy_escape_replay"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_sandbox_policy_escape_replay",
        copied_fixture,
    )
    input_dir = copied_fixture / "input"

    verdict_path = input_dir / "policy_verdicts.json"
    verdict_payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    for row in verdict_payload["policy_verdicts"]:
        if row["request_id"] == "req_network_exfil_attempt":
            row["verdict"] = "allow"
            row["rule_refs"] = ["rule:public_fixture_write_with_diff_receipt"]
            row["decision_reason_ref"] = "decision_reason/semantic_mismatch_allow"
    verdict_path.write_text(
        json.dumps(verdict_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    effect_path = input_dir / "side_effect_receipts.json"
    effect_payload = json.loads(effect_path.read_text(encoding="utf-8"))
    for row in effect_payload["side_effect_receipts"]:
        if row["request_id"] == "req_network_exfil_attempt":
            row["execution_attempted"] = True
            row["filesystem_diff_ref"] = "diff/none_local_only"
            row["network_diff_ref"] = "diff/synthetic_network_exfil_attempt"
            row["side_effect_diff_count"] = 1
            row["rollback_receipt_ref"] = "rollback_network_exfil_semantic_mismatch"
    effect_path.write_text(
        json.dumps(effect_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rollback_path = input_dir / "rollback_receipts.json"
    rollback_payload = json.loads(rollback_path.read_text(encoding="utf-8"))
    rollback_payload["rollback_receipts"].append(
        {
            "body_redacted": True,
            "request_id": "req_network_exfil_attempt",
            "rollback_command_ref": "rollback_command/ref/synthetic_network_revert",
            "rollback_id": "rollback_network_exfil_semantic_mismatch",
            "rollback_required": True,
            "rollback_verified": True,
        }
    )
    rollback_path.write_text(
        json.dumps(rollback_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert "SANDBOX_POLICY_VERDICT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert "SANDBOX_POLICY_SIDE_EFFECT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert result["derived_policy_verdict_mismatch_count"] == 1
    derivations = {
        row["request_id"]: row for row in result["derived_policy_verdict_rows"]
    }
    network_derivation = derivations["req_network_exfil_attempt"]
    assert network_derivation["derived_policy_verdict"] == "block"
    assert network_derivation["declared_policy_verdict"] == "allow"
    assert network_derivation["policy_derivation_passed"] is False
    mismatch_findings = [
        row
        for row in result["findings"]
        if row["subject_id"] == "req_network_exfil_attempt"
    ]
    assert {
        row["error_code"]
        for row in mismatch_findings
    } >= {
        "SANDBOX_POLICY_VERDICT_SEMANTIC_MISMATCH",
        "SANDBOX_POLICY_SIDE_EFFECT_SEMANTIC_MISMATCH",
    }


def test_agent_sandbox_policy_escape_rejects_positive_allow_row_declared_blocked(
    tmp_path: Path,
) -> None:
    public_root, input_dir = _copy_fixture_public_root(tmp_path)

    verdict_path = input_dir / "policy_verdicts.json"
    verdict_payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    for row in verdict_payload["policy_verdicts"]:
        if row["request_id"] == "req_safe_file_edit":
            row["verdict"] = "block"
            row["rule_refs"] = ["rule:no_destructive_filesystem_mutation"]
            row["decision_reason_ref"] = "decision_reason/stale_recorded_block"
    verdict_path.write_text(
        json.dumps(verdict_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "SANDBOX_POLICY_VERDICT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert "SANDBOX_POLICY_BLOCKED_ACTION_EXECUTED" in result["error_codes"]
    assert result["allow_count"] == 0
    assert result["block_count"] == 5
    assert result["review_count"] == 1
    assert result["derived_allow_count"] == 1
    assert result["derived_block_count"] == 4
    assert result["derived_review_count"] == 1
    assert result["blocked_without_execution_count"] == 4
    assert result["derived_policy_verdict_mismatch_count"] == 1
    derivations = {
        row["request_id"]: row for row in result["derived_policy_verdict_rows"]
    }
    safe_edit = derivations["req_safe_file_edit"]
    assert safe_edit["derived_policy_verdict"] == "allow"
    assert safe_edit["declared_policy_verdict"] == "block"
    assert safe_edit["policy_derivation_passed"] is False


def test_agent_sandbox_policy_escape_rejects_positive_allow_row_missing_diff(
    tmp_path: Path,
) -> None:
    public_root, input_dir = _copy_fixture_public_root(tmp_path)

    effect_path = input_dir / "side_effect_receipts.json"
    effect_payload = json.loads(effect_path.read_text(encoding="utf-8"))
    for row in effect_payload["side_effect_receipts"]:
        if row["request_id"] == "req_safe_file_edit":
            row["execution_attempted"] = False
            row["filesystem_diff_ref"] = "diff/none_blocked"
            row["side_effect_diff_count"] = 0
            row["rollback_receipt_ref"] = "rollback/not_required_blocked"
    effect_path.write_text(
        json.dumps(effect_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "SANDBOX_POLICY_SIDE_EFFECT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert "SANDBOX_POLICY_ALLOWED_ACTION_MISSING_DIFF" in result["error_codes"]
    assert result["derived_policy_verdict_mismatch_count"] == 0
    assert result["blocked_without_execution_count"] == 4


def test_agent_sandbox_policy_escape_input_shape_perturbation_moves_derived_counts(
    tmp_path: Path,
) -> None:
    public_root, input_dir = _copy_fixture_public_root(tmp_path)

    action_path = input_dir / "action_requests.json"
    action_payload = json.loads(action_path.read_text(encoding="utf-8"))
    for row in action_payload["action_requests"]:
        if row["request_id"] == "req_safe_file_edit":
            row["risk_class"] = "secret_access"
    action_path.write_text(
        json.dumps(action_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "SANDBOX_POLICY_ACTION_POLICY_SHAPE_MISMATCH" in result["error_codes"]
    assert "SANDBOX_POLICY_VERDICT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert "SANDBOX_POLICY_SIDE_EFFECT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert result["allow_count"] == 1
    assert result["block_count"] == 4
    assert result["derived_allow_count"] == 0
    assert result["derived_block_count"] == 5
    assert result["derived_review_count"] == 1
    derivations = {
        row["request_id"]: row for row in result["derived_policy_verdict_rows"]
    }
    safe_edit = derivations["req_safe_file_edit"]
    assert safe_edit["derived_policy_verdict"] == "block"
    assert safe_edit["derived_rule_ref"] == (
        "rule:sandbox_policy_fail_closed_unrecognized_action"
    )
    assert safe_edit["declared_policy_verdict"] == "allow"
    assert safe_edit["policy_derivation_passed"] is False


def test_agent_sandbox_policy_escape_stale_cold_replay_label_cannot_override_failure(
    tmp_path: Path,
) -> None:
    public_root, input_dir = _copy_fixture_public_root(tmp_path)

    verdict_path = input_dir / "policy_verdicts.json"
    verdict_payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    for row in verdict_payload["policy_verdicts"]:
        if row["request_id"] == "req_network_exfil_attempt":
            row["verdict"] = "allow"
            row["rule_refs"] = ["rule:public_fixture_write_with_diff_receipt"]
    verdict_path.write_text(
        json.dumps(verdict_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["cold_replay_pass_count"] == 6
    assert "SANDBOX_POLICY_VERDICT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert result["derived_policy_verdict_mismatch_count"] == 1


def test_agent_sandbox_policy_escape_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_sandbox_policy_escape_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["action_request_count"] == 6
    assert result["policy_verdict_count"] == 6
    assert result["block_count"] == 4
    assert result["allow_count"] == 1
    assert result["review_count"] == 1
    assert result["derived_block_count"] == 4
    assert result["derived_allow_count"] == 1
    assert result["derived_review_count"] == 1
    assert result["derived_policy_verdict_mismatch_count"] == 0
    assert result["side_effect_receipt_count"] == 6
    assert result["blocked_without_execution_count"] == 4
    assert result["rollback_verified_count"] == 2
    assert result["cold_replay_pass_count"] == 6
    assert result["authority_ceiling"]["live_sandbox_escape_authorized"] is False
    assert result["authority_ceiling"]["live_network_access_authorized"] is False
    assert result["authority_ceiling"]["host_filesystem_mutation_authorized"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert (
        result["body_import_classification"]
        == "extension_of_existing_public_refactor"
    )
    assert result["product_path_role"] == (
        "source_faithful_public_agent_execution_trace_refactor"
    )
    assert result["body_in_receipt"] is False
    assert result["body_import_verification"]["classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 6
    assert result["public_agent_execution_trace"]["summary"]["outcome_counts"] == {
        "blocked": 4,
        "executed": 2,
    }
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_agent_sandbox_policy_escape_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_sandbox_policy_escape_replay",
        public_root / "fixtures/first_wave/agent_sandbox_policy_escape_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_sandbox_policy_escape_replay/input",
        public_root / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        keys = _walk_keys(json.loads(text))
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "raw_environment" not in keys
        assert "raw_tool_output_body" not in keys
        assert "executable_payload" not in keys
        assert "provider_payload" not in keys
        assert "host_absolute_path" not in keys
        assert "private_state_scan" not in keys


def test_agent_sandbox_policy_escape_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_sandbox_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_sandbox_policy_escape_bundle"
    assert (
        result["bundle_id"]
        == "agent_sandbox_policy_escape_replay_public_trace_refactor_bundle"
    )
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["action_request_count"] == 6
    assert result["policy_verdict_count"] == 6
    assert result["blocked_without_execution_count"] == 4
    assert result["cold_replay_pass_count"] == 6
    assert result["authority_ceiling"]["live_sandbox_escape_authorized"] is False
    assert "public_replacement_refs" not in result
    assert "omitted_private_material" not in result
    assert result["body_import_verification"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["body_import_verification"]["classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["body_import_verification"]["status"] == "pass"
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert (
        result["body_import_classification"]
        == "extension_of_existing_public_refactor"
    )
    assert result["source_module_manifest_status"] == "pass"
    assert result["body_copied_material_count"] == 7
    assert (
        result["source_open_body_imports"]["body_material_status"]
        == "copied_non_secret_agent_sandbox_policy_escape_macro_body_landed"
    )
    assert result["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert result["body_in_receipt"] is False
    assert (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        in result["target_refs"]
    )
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["source_faithful_refactor"][
        "verification_mode"
    ] == "extension_of_existing_public_refactor"
    assert {
        span["tool_name"] for span in result["public_agent_execution_trace"]["spans"]
    } == {"sandbox_policy_action"}


def test_agent_sandbox_policy_escape_bundle_rejects_blocked_action_execution(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_sandbox_policy_escape_replay",
        public_root / "examples/agent_sandbox_policy_escape_replay",
    )
    bundle = (
        public_root
        / "examples/agent_sandbox_policy_escape_replay/"
        "exported_sandbox_policy_escape_bundle"
    )
    effect_path = bundle / "side_effect_receipts.json"
    effect_payload = json.loads(effect_path.read_text(encoding="utf-8"))
    for row in effect_payload["side_effect_receipts"]:
        if row["request_id"] == "req_network_exfil_attempt":
            row["execution_attempted"] = True
            row["network_diff_ref"] = "diff/synthetic_network_exfil_attempt"
            row["side_effect_diff_count"] = 1
    effect_path.write_text(
        json.dumps(effect_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_sandbox_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "pass"
    assert result["side_effect_receipt_count"] == 6
    assert result["blocked_without_execution_count"] == 3
    assert "SANDBOX_POLICY_SIDE_EFFECT_SEMANTIC_MISMATCH" in result["error_codes"]
    assert "SANDBOX_POLICY_BLOCKED_ACTION_EXECUTED" in result["error_codes"]


def test_agent_sandbox_policy_escape_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["body_in_receipt"] is False
    assert manifest["body_text_in_receipt"] is False
    assert manifest["module_count"] == 7
    assert {
        row["module_id"] for row in manifest["modules"]
    } == {
        "sandbox_policy_extracted_patterns_ledger_body_import",
        "sandbox_policy_high_novelty_growth_receipt_body_import",
        "sandbox_policy_canonical_organ_model_body_import",
        "agent_execution_trace_runtime_body_import",
        "strict_json_source_body_import",
        "agent_execution_trace_standard_body_import",
        "extracted_pattern_route_readiness_tool_body_import",
    }

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix(
            "microcosm-substrate/"
        )
        text = target.read_text(encoding="utf-8")
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == row["source_sha256"]
        assert _sha256(target) == row["target_sha256"]
        assert row["source_sha256"] == row["target_sha256"]
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_agent_sandbox_policy_escape_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_sandbox_policy_escape_replay",
        public_root / "examples/agent_sandbox_policy_escape_replay",
    )
    bundle = (
        public_root
        / "examples/agent_sandbox_policy_escape_replay/exported_sandbox_policy_escape_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_sandbox_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "SANDBOX_POLICY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_agent_sandbox_policy_escape_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_sandbox_policy_escape_replay",
        public_root / "examples/agent_sandbox_policy_escape_replay",
    )
    bundle = (
        public_root
        / "examples/agent_sandbox_policy_escape_replay/exported_sandbox_policy_escape_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_sandbox_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "SANDBOX_POLICY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_agent_sandbox_policy_escape_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_sandbox_policy_escape_replay",
        public_root / "examples/agent_sandbox_policy_escape_replay",
    )
    bundle = (
        public_root
        / "examples/agent_sandbox_policy_escape_replay/exported_sandbox_policy_escape_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_sandbox_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "SANDBOX_POLICY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_agent_sandbox_policy_escape_rejects_source_module_manifest_boundaries(
    tmp_path: Path,
) -> None:
    cases = [
        (
            "missing_manifest",
            "SANDBOX_POLICY_SOURCE_MODULE_MANIFEST_REQUIRED",
            "source_module_manifest",
        ),
        (
            "manifest_class_invalid",
            "SANDBOX_POLICY_SOURCE_MODULE_CLASS_REQUIRED",
            "source_import_class",
        ),
        (
            "manifest_body_in_receipt",
            "SANDBOX_POLICY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
            "body_in_receipt",
        ),
        (
            "manifest_body_text_in_receipt",
            "SANDBOX_POLICY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
            "body_text_in_receipt",
        ),
        (
            "manifest_count_mismatch",
            "SANDBOX_POLICY_SOURCE_MODULE_COUNT_MISMATCH",
            "module_count",
        ),
        (
            "row_class_invalid",
            "SANDBOX_POLICY_SOURCE_MODULE_CLASS_REQUIRED",
            "source_import_class",
        ),
        (
            "row_material_class_invalid",
            "SANDBOX_POLICY_SOURCE_MODULE_CLASS_REQUIRED",
            "material_class",
        ),
        (
            "row_body_boundary",
            "SANDBOX_POLICY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
            "source_module",
        ),
        (
            "target_missing",
            "SANDBOX_POLICY_SOURCE_MODULE_TARGET_MISSING",
            "source_module",
        ),
    ]

    for case_id, expected_code, expected_subject_kind in cases:
        public_root = tmp_path / case_id / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        shutil.copytree(
            MICROCOSM_ROOT / "examples/agent_sandbox_policy_escape_replay",
            public_root / "examples/agent_sandbox_policy_escape_replay",
        )
        bundle = (
            public_root
            / "examples/agent_sandbox_policy_escape_replay/"
            "exported_sandbox_policy_escape_bundle"
        )
        manifest_path = bundle / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        first_module = manifest["modules"][0]

        if case_id == "missing_manifest":
            manifest_path.unlink()
        elif case_id == "manifest_class_invalid":
            manifest["source_import_class"] = "private_macro_body"
        elif case_id == "manifest_body_in_receipt":
            manifest["body_in_receipt"] = True
        elif case_id == "manifest_body_text_in_receipt":
            manifest["body_text_in_receipt"] = True
        elif case_id == "manifest_count_mismatch":
            manifest["module_count"] += 1
        elif case_id == "row_class_invalid":
            first_module["source_import_class"] = "private_macro_body"
        elif case_id == "row_material_class_invalid":
            first_module["material_class"] = "private_macro_body"
        elif case_id == "row_body_boundary":
            first_module["body_in_receipt"] = True
        elif case_id == "target_missing":
            (bundle / first_module["path"]).unlink()

        if manifest_path.exists():
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        result = run_sandbox_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            f"agent_sandbox_policy_escape_replay/{case_id}",
            command="pytest",
        )
        source_modules = result["source_module_imports"]

        assert result["status"] == "blocked"
        assert result["source_module_manifest_status"] == "blocked"
        assert source_modules["status"] == "blocked"
        assert source_modules["body_in_receipt"] is False
        assert source_modules["body_text_in_receipt"] is False
        assert expected_code in result["error_codes"]
        findings = [
            row
            for row in source_modules["findings"]
            if row["error_code"] == expected_code
        ]
        assert findings
        assert {row["subject_kind"] for row in findings} == {expected_subject_kind}
        assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert result["body_in_receipt"] is False
        receipt_text = json.dumps(result, sort_keys=True)
        assert "TRACE_OUTPUT_PRIVACY_BOUNDARY =" not in receipt_text
        assert "def build_public_sandbox_policy_trace(" not in receipt_text


def test_agent_sandbox_policy_escape_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sandbox_policy_escape_replay"
    )
    args = [
        "run-sandbox-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["sandbox_policy"]["action_request_count"] == 6
    assert first_card["sandbox_policy"]["policy_verdict_count"] == 6
    assert first_card["sandbox_policy"]["blocked_without_execution_count"] == 4
    assert first_card["sandbox_policy"]["derived_block_count"] == 4
    assert first_card["sandbox_policy"]["derived_allow_count"] == 1
    assert first_card["sandbox_policy"]["derived_review_count"] == 1
    assert first_card["sandbox_policy"]["derived_policy_verdict_mismatch_count"] == 0
    assert first_card["validation"]["public_agent_execution_trace_span_count"] == 6
    assert first_card["validation"]["source_module_manifest_status"] == "pass"
    assert first_card["validation"]["body_material_count"] == 7
    assert (
        first_card["validation"]["body_material_status"]
        == "copied_non_secret_agent_sandbox_policy_escape_macro_body_landed"
    )
    assert first_card["body_floor"]["source_module_imports_in_card"] is False
    assert first_card["body_floor"]["source_open_body_imports_in_card"] is False
    assert "request_rows" not in _walk_keys(first_card)
    assert "policy_verdict_rows" not in _walk_keys(first_card)
    assert "derived_policy_verdict_rows" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "public_agent_execution_trace" not in _walk_keys(first_card)
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(sandbox_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_public_agent_execution_trace_refactor_builds_sandbox_policy_spans() -> None:
    trace = build_public_sandbox_policy_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert (
        trace["bundle_id"]
        == "agent_sandbox_policy_escape_replay_public_trace_refactor_bundle"
    )
    assert trace["span_count"] == 6
    assert trace["summary"]["action_kind_counts"] == {
        "environment_secret_read": 1,
        "filesystem_delete": 1,
        "filesystem_write": 1,
        "mock_database_update": 1,
        "network_request": 1,
        "shell_command": 1,
    }
    assert trace["audit"]["coverage"]["policy_verdict_coverage"] is True
    assert trace["audit"]["coverage"]["side_effect_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["cold_replay_coverage"] is True
    assert "system/lib/agent_execution_trace.py" in trace["source_refs"]


def test_agent_sandbox_policy_fixture_manifests_bind_public_trace_refactor() -> None:
    for manifest_path in FIXTURE_MANIFESTS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert "body_redacted" not in manifest
        assert "public_replacement_refs" not in manifest
        assert "private_state_scan" not in manifest
        assert not manifest["authority_ceiling"].startswith(
            "synthetic_agent_sandbox_policy_escape_replay_receipts_only"
        )
        assert (
            manifest["body_import_status"]
            == "extension_of_existing_public_refactor_landed"
        )
        assert (
            manifest["product_path_role"]
            == "source_faithful_public_agent_execution_trace_refactor"
        )
        assert manifest["body_copied_material_count"] == 7
        assert (
            manifest["body_material_status"]
            == "copied_non_secret_agent_sandbox_policy_escape_macro_body_landed"
        )
        assert manifest["source_open_body_imports"]["status"] == "pass"
        assert manifest["source_open_body_imports"]["body_material_count"] == 7
        assert manifest["source_open_body_imports"]["body_text_exported_in_receipts"] is False
        assert manifest["body_in_receipt"] is False
        assert manifest["body_import_verification"] == {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": (
                "microcosm-substrate/src/microcosm_core/macro_tools/"
                "agent_execution_trace.py"
            ),
            "validation_refs": [
                "microcosm-substrate/tests/test_agent_sandbox_policy_escape_replay.py"
            ],
            "verification_mode": "extension_of_existing_public_refactor",
            "verification_status": "verified",
        }
        assert (
            "microcosm_core.macro_tools.agent_execution_trace::"
            "build_public_sandbox_policy_trace"
            in manifest["fixture_runtime_refs"]
        )
        assert (
            "microcosm-substrate/src/microcosm_core/macro_tools/"
            "agent_execution_trace.py"
            in manifest["target_refs"]
        )
        assert set(manifest["negative_case_ids"]) == set(EXPECTED_NEGATIVE_CASES)
