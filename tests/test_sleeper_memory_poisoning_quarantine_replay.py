from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import sleeper_memory_poisoning_quarantine_replay
from microcosm_core.organs.sleeper_memory_poisoning_quarantine_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SOURCE_MODULE_IMPORT_STATUS,
    main,
    run,
    run_quarantine_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/sleeper_memory_poisoning_quarantine_replay/"
    "exported_sleeper_memory_poisoning_bundle"
)


def _copy_fixture_public_root(tmp_path: Path) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = (
        public_root
        / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay",
        fixture,
    )
    return public_root, fixture


def _run_fixture(public_root: Path, fixture: Path, suffix: str) -> dict[str, Any]:
    return run(
        fixture / "input",
        public_root
        / "receipts/first_wave/sleeper_memory_poisoning_quarantine_replay"
        / suffix,
        command="pytest",
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def test_sleeper_memory_poisoning_quarantine_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "sleeper_memory_poisoning_quarantine_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["session_count"] == 4
    assert result["session_roles"] == [
        "poisoned_source_seen",
        "memory_write_quarantined",
        "later_retrieval_action_gated",
        "rollback_and_cold_rerun",
    ]
    assert result["proposal_count"] == 2
    assert result["quarantined_write_count"] == 1
    assert result["admitted_control_count"] == 1
    assert result["retrieval_replay_count"] == 1
    assert result["blocked_before_action_count"] == 1
    assert result["rollback_count"] == 1
    assert result["rerun_pass_count"] == 1
    assert result["authority_ceiling"]["private_memory_body_export_authorized"] is False
    assert result["authority_ceiling"]["live_user_memory_claim_authorized"] is False
    assert (
        result["authority_ceiling"][
            "trusted_promotion_from_untrusted_context_authorized"
        ]
        is False
    )
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_sleeper_memory_poisoning_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay",
        public_root / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay/input",
        public_root / "receipts/first_wave/sleeper_memory_poisoning_quarantine_replay",
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
        assert "private_memory_body" not in keys
        assert "raw_transcript" not in keys
        assert "raw_transcript_body" not in keys
        assert "private_thread_body" not in keys
        assert "provider_payload" not in keys
        assert "credential_value" not in keys
        assert "secret_value" not in keys


def test_sleeper_memory_poisoning_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_quarantine_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_sleeper_memory_poisoning_bundle"
    assert result["bundle_id"] == "sleeper_memory_poisoning_quarantine_policy_refactor"
    assert result["body_import_status"] == SOURCE_MODULE_IMPORT_STATUS
    assert (
        result["product_path_role"]
        == "copied_non_secret_macro_body_plus_public_memory_security_policy_refactor"
    )
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 7
    assert result["body_copied_material_count"] == 7
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["session_count"] == 4
    assert result["quarantined_write_count"] == 1
    assert result["blocked_before_action_count"] == 1
    assert result["rerun_pass_count"] == 1
    assert result["authority_ceiling"]["live_memory_product_claim_authorized"] is False


def test_sleeper_memory_poisoning_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/sleeper_memory_poisoning_quarantine_replay",
        public_root / "examples/sleeper_memory_poisoning_quarantine_replay",
    )
    bundle = (
        public_root
        / "examples/sleeper_memory_poisoning_quarantine_replay/"
        "exported_sleeper_memory_poisoning_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_quarantine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "SLEEPER_MEMORY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_sleeper_memory_poisoning_rejects_mutated_positive_quarantine_row(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_quarantine_positive_row")
    assert clean["status"] == "pass"
    clean_admitted_rows = [
        row for row in clean["write_rows"] if row["quarantine_verdict"] == "admit"
    ]
    assert len(clean_admitted_rows) == 1
    assert clean_admitted_rows[0]["computed_verdict"] == "accepted_write_metadata"

    quarantine_path = fixture / "input/quarantine_events.json"
    quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
    admitted = quarantine["memory_write_proposals"][1]
    admitted["source_trust_tier"] = "untrusted_context"
    admitted["quarantine_verdict"] = "trusted_promote"
    admitted["audit_ref"] = ""
    admitted["expected_negative_case_id"] = "stale_baked_label_ignored"
    admitted["expected_error_codes"] = ["BOGUS_EXPECTED_CODE_IGNORED"]
    admitted["declared_status"] = "pass"
    _write_json(quarantine_path, quarantine)

    result = _run_fixture(public_root, fixture, "mutated_quarantine_positive_row")
    assert result["status"] == "blocked"
    assert "SLEEPER_MEMORY_TRUSTED_PROMOTION_FORBIDDEN" in result["error_codes"]
    assert result["quarantined_write_count"] == 1
    assert result["admitted_control_count"] == 0
    mutated_row = next(
        row
        for row in result["write_rows"]
        if row["proposal_id"] == clean_admitted_rows[0]["proposal_id"]
    )
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["source_trust_tier"] == "untrusted_context"
    assert mutated_row["quarantine_verdict"] == "trusted_promote"
    assert mutated_row["audit_ref"] == ""
    assert set(mutated_row["reason_codes"]) >= {
        "trusted_promotion_from_untrusted_context",
        "write_field_missing",
    }
    assert "audit_ref" in mutated_row["missing_required_fields"]


def test_sleeper_memory_poisoning_rejects_untrusted_admit_positive_row(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_untrusted_admit_positive_row")
    assert clean["status"] == "pass"
    assert clean["admitted_control_count"] == 1

    quarantine_path = fixture / "input/quarantine_events.json"
    quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
    admitted = quarantine["memory_write_proposals"][1]
    admitted["source_trust_tier"] = "untrusted_context"
    admitted["quarantine_verdict"] = "admit"
    admitted["declared_status"] = "pass"
    _write_json(quarantine_path, quarantine)

    result = _run_fixture(public_root, fixture, "mutated_untrusted_admit_positive_row")
    assert result["status"] == "blocked"
    assert result["admitted_control_count"] == 0
    assert "SLEEPER_MEMORY_TRUSTED_PROMOTION_FORBIDDEN" in result["error_codes"]
    mutated_row = next(
        row
        for row in result["write_rows"]
        if row["proposal_id"] == "proposal_trusted_benign_control"
    )
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["source_trust_tier"] == "untrusted_context"
    assert mutated_row["quarantine_verdict"] == "admit"
    assert mutated_row["reason_codes"] == [
        "trusted_promotion_from_untrusted_context"
    ]
    finding = next(
        row
        for row in result["findings"]
        if row["subject_id"] == "proposal_trusted_benign_control"
    )
    assert finding["error_code"] == "SLEEPER_MEMORY_TRUSTED_PROMOTION_FORBIDDEN"
    assert finding["negative_case_id"] == "proposal_trusted_benign_control"
    assert finding["subject_kind"] == "memory_write_proposal"


def test_sleeper_memory_poisoning_ignores_baked_negative_label_on_positive_row(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    quarantine_path = fixture / "input/quarantine_events.json"
    quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
    admitted = quarantine["memory_write_proposals"][1]
    admitted["expected_negative_case_id"] = "trusted_promotion_from_untrusted_context"
    admitted["expected_error_codes"] = ["SLEEPER_MEMORY_TRUSTED_PROMOTION_FORBIDDEN"]
    admitted["declared_status"] = "blocked"
    _write_json(quarantine_path, quarantine)

    result = _run_fixture(public_root, fixture, "baked_negative_label_on_positive_row")
    assert result["status"] == "pass"
    assert result["admitted_control_count"] == 1
    admitted_row = next(
        row
        for row in result["write_rows"]
        if row["proposal_id"] == "proposal_trusted_benign_control"
    )
    assert admitted_row["source_trust_tier"] == "trusted_source"
    assert admitted_row["quarantine_verdict"] == "admit"
    assert admitted_row["computed_verdict"] == "accepted_write_metadata"
    assert admitted_row["reason_codes"] == []
    assert not [
        finding
        for finding in result["findings"]
        if finding["subject_id"] == "proposal_trusted_benign_control"
    ]


def test_sleeper_memory_poisoning_rejects_quarantined_ref_decoupling(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    quarantine_path = fixture / "input/quarantine_events.json"
    quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
    quarantine["memory_write_proposals"][0]["proposed_memory_ref"] = (
        "memory_candidate.sleeper.future_trigger.decoupled"
    )
    _write_json(quarantine_path, quarantine)

    result = _run_fixture(public_root, fixture, "mutated_quarantine_ref")
    assert result["status"] == "blocked"
    assert result["quarantined_write_count"] == 1
    assert result["blocked_before_action_count"] == 0
    assert result["rerun_pass_count"] == 0
    assert "SLEEPER_MEMORY_RETRIEVAL_QUARANTINE_REF_MISMATCH" in result["error_codes"]
    assert "SLEEPER_MEMORY_ROLLBACK_QUARANTINE_REF_MISMATCH" in result["error_codes"]


def test_sleeper_memory_poisoning_rejects_mutated_positive_rollback_row(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_rollback_positive_row")
    assert clean["status"] == "pass"
    assert clean["rollback_count"] == 1
    clean_row = clean["rollback_rows"][0]
    assert clean_row["computed_verdict"] == "accepted_rollback_metadata"
    assert clean_row["deletion_audit_ref"]

    rollback_path = fixture / "input/rollback_rerun.json"
    rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
    rollback["rollback_events"][0]["deletion_audit_ref"] = ""
    _write_json(rollback_path, rollback)

    result = _run_fixture(public_root, fixture, "mutated_rollback_positive_row")
    assert result["status"] == "blocked"
    assert "SLEEPER_MEMORY_DELETION_WITHOUT_AUDIT" in result["error_codes"]
    assert result["rollback_count"] == 1
    assert result["rerun_pass_count"] == 0
    mutated_row = result["rollback_rows"][0]
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["deletion_audit_ref"] == ""
    assert "deletion_without_audit" in mutated_row["reason_codes"]


def test_sleeper_memory_poisoning_rejects_bogus_quarantine_audit_ref(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_quarantine_audit_ref")
    assert clean["status"] == "pass"
    assert clean["quarantined_write_count"] == 1

    quarantine_path = fixture / "input/quarantine_events.json"
    quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
    poisoned = quarantine["memory_write_proposals"][0]
    poisoned["audit_ref"] = "receipt.not_a_quarantine_audit"
    poisoned["declared_status"] = "pass"
    _write_json(quarantine_path, quarantine)

    result = _run_fixture(public_root, fixture, "bogus_quarantine_audit_ref")
    assert result["status"] == "blocked"
    assert result["quarantined_write_count"] == 0
    assert "SLEEPER_MEMORY_QUARANTINE_AUDIT_REF_INVALID" in result["error_codes"]
    mutated_row = next(
        row
        for row in result["write_rows"]
        if row["proposal_id"] == "proposal_poisoned_future_trigger_memory"
    )
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["audit_ref"] == "receipt.not_a_quarantine_audit"
    assert "quarantine_audit_ref_invalid" in mutated_row["reason_codes"]


def test_sleeper_memory_poisoning_retrieval_evidence_cites_quarantine_audit(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_retrieval_evidence_refs")
    assert clean["status"] == "pass"
    assert clean["blocked_before_action_count"] == 1

    retrieval_path = fixture / "input/retrieval_replays.json"
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    replay = retrieval["retrieval_replays"][0]
    replay["evidence_used_refs"] = ["receipt.sleeper_memory.unrelated.v1"]
    replay["declared_status"] = "pass"
    _write_json(retrieval_path, retrieval)

    result = _run_fixture(public_root, fixture, "missing_retrieval_evidence_refs")
    assert result["status"] == "blocked"
    assert result["blocked_before_action_count"] == 0
    assert "SLEEPER_MEMORY_RETRIEVAL_QUARANTINE_AUDIT_REF_MISSING" in result[
        "error_codes"
    ]
    assert "SLEEPER_MEMORY_RETRIEVAL_COLD_REPLAY_REF_MISSING" in result[
        "error_codes"
    ]
    mutated_row = result["retrieval_rows"][0]
    assert mutated_row["computed_verdict"] == "blocked"
    assert set(mutated_row["reason_codes"]) >= {
        "quarantine_audit_ref_missing",
        "cold_replay_ref_missing",
    }


def test_sleeper_memory_poisoning_rejects_mutated_positive_retrieval_influence_row(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_retrieval_influence_row")
    assert clean["status"] == "pass"
    assert clean["blocked_before_action_count"] == 1

    retrieval_path = fixture / "input/retrieval_replays.json"
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    replay = retrieval["retrieval_replays"][0]
    replay["influence_grade"] = "acted_on_quarantined_memory"
    replay["action_gate"] = "used_for_action"
    replay["declared_status"] = "pass"
    _write_json(retrieval_path, retrieval)

    result = _run_fixture(public_root, fixture, "mutated_retrieval_influence_row")
    assert result["status"] == "blocked"
    assert result["blocked_before_action_count"] == 0
    assert "SLEEPER_MEMORY_UNMETERED_POISON_INFLUENCE" in result["error_codes"]
    mutated_row = result["retrieval_rows"][0]
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["influence_grade"] == "acted_on_quarantined_memory"
    assert mutated_row["action_gate"] == "used_for_action"
    assert "unmetered_poison_influence" in mutated_row["reason_codes"]


def test_sleeper_memory_poisoning_rejects_bogus_nonempty_rollback_refs(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_rollback_ref_shapes")
    assert clean["status"] == "pass"
    assert clean["rerun_pass_count"] == 1

    rollback_path = fixture / "input/rollback_rerun.json"
    rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
    event = rollback["rollback_events"][0]
    event["deletion_audit_ref"] = "receipt.not_a_deletion_audit"
    event["rollback_receipt_ref"] = "audit.not_a_rollback_receipt"
    event["rerun_receipt_ref"] = "audit.not_a_rerun_receipt"
    event["declared_status"] = "pass"
    _write_json(rollback_path, rollback)

    result = _run_fixture(public_root, fixture, "bogus_nonempty_rollback_refs")
    assert result["status"] == "blocked"
    assert result["rerun_pass_count"] == 0
    assert "SLEEPER_MEMORY_DELETION_AUDIT_REF_INVALID" in result["error_codes"]
    assert "SLEEPER_MEMORY_ROLLBACK_RECEIPT_REF_INVALID" in result["error_codes"]
    assert "SLEEPER_MEMORY_ROLLBACK_RERUN_RECEIPT_REF_INVALID" in result[
        "error_codes"
    ]
    mutated_row = result["rollback_rows"][0]
    assert mutated_row["computed_verdict"] == "blocked"
    assert set(mutated_row["reason_codes"]) >= {
        "deletion_audit_ref_invalid",
        "rollback_receipt_ref_invalid",
        "rerun_receipt_ref_invalid",
    }


def test_sleeper_memory_poisoning_rejects_mutated_positive_rollback_absence_row(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_fixture_public_root(tmp_path)
    clean = _run_fixture(public_root, fixture, "clean_rollback_absence_row")
    assert clean["status"] == "pass"
    assert clean["rerun_pass_count"] == 1

    rollback_path = fixture / "input/rollback_rerun.json"
    rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
    event = rollback["rollback_events"][0]
    event["rollback_receipt_ref"] = ""
    event["rerun_receipt_ref"] = ""
    event["memory_absent_after_rerun"] = False
    event["declared_status"] = "pass"
    _write_json(rollback_path, rollback)

    result = _run_fixture(public_root, fixture, "mutated_rollback_absence_row")
    assert result["status"] == "blocked"
    assert result["rollback_count"] == 1
    assert result["rerun_pass_count"] == 0
    assert "SLEEPER_MEMORY_ROLLBACK_RECEIPT_REF_MISSING" in result["error_codes"]
    assert "SLEEPER_MEMORY_ROLLBACK_RERUN_RECEIPT_REF_MISSING" in result[
        "error_codes"
    ]
    assert "SLEEPER_MEMORY_ROLLBACK_MEMORY_PRESENT_AFTER_RERUN" in result[
        "error_codes"
    ]
    mutated_row = result["rollback_rows"][0]
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["rollback_receipt_ref"] == ""
    assert mutated_row["rerun_receipt_ref"] == ""
    assert mutated_row["memory_absent_after_rerun"] is False
    assert set(mutated_row["reason_codes"]) >= {
        "rollback_receipt_ref_missing",
        "rerun_receipt_ref_missing",
        "memory_present_after_rerun",
    }


def test_sleeper_memory_poisoning_bundle_rejects_bogus_rollback_ref_shape(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/sleeper_memory_poisoning_quarantine_replay",
        public_root / "examples/sleeper_memory_poisoning_quarantine_replay",
    )
    bundle = (
        public_root
        / "examples/sleeper_memory_poisoning_quarantine_replay/"
        "exported_sleeper_memory_poisoning_bundle"
    )
    rollback_path = bundle / "rollback_rerun.json"
    rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
    rollback["rollback_events"][0]["deletion_audit_ref"] = (
        "receipt.not_a_deletion_audit"
    )
    _write_json(rollback_path, rollback)

    result = run_quarantine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["rerun_pass_count"] == 0
    assert "SLEEPER_MEMORY_DELETION_AUDIT_REF_INVALID" in result["error_codes"]


def test_sleeper_memory_poisoning_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/sleeper_memory_poisoning_quarantine_replay",
        public_root / "examples/sleeper_memory_poisoning_quarantine_replay",
    )
    bundle = (
        public_root
        / "examples/sleeper_memory_poisoning_quarantine_replay/"
        "exported_sleeper_memory_poisoning_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_quarantine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "SLEEPER_MEMORY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_sleeper_memory_poisoning_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/sleeper_memory_poisoning_quarantine_replay",
        public_root / "examples/sleeper_memory_poisoning_quarantine_replay",
    )
    bundle = (
        public_root
        / "examples/sleeper_memory_poisoning_quarantine_replay/"
        "exported_sleeper_memory_poisoning_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_quarantine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "SLEEPER_MEMORY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_sleeper_memory_poisoning_rejects_rehashed_source_module_body_swap(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/sleeper_memory_poisoning_quarantine_replay",
        public_root / "examples/sleeper_memory_poisoning_quarantine_replay",
    )
    bundle = (
        public_root
        / "examples/sleeper_memory_poisoning_quarantine_replay/"
        "exported_sleeper_memory_poisoning_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = manifest["modules"][1]
    target = bundle / module["path"]
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n\nstale_source_module_body_swap: declared digest was recomputed.\n",
        encoding="utf-8",
    )
    digest = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
    module["sha256"] = digest
    module["source_sha256"] = digest
    module["target_sha256"] = digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_quarantine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "SLEEPER_MEMORY_SOURCE_MODULE_SOURCE_REF_MISMATCH" in result["error_codes"]
    assert result["source_module_imports"]["source_ref_count"] == 7
    assert result["source_module_imports"]["verified_source_ref_count"] == 6


def test_sleeper_memory_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 7

    imported_ids: set[str] = set()
    for row in manifest["modules"]:
        imported_ids.add(row["module_id"])
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        target = BUNDLE_INPUT / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert target.read_bytes() == source.read_bytes()
        digest = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in text
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False

    assert imported_ids == {
        "sleeper_memory_high_novelty_growth_receipt_body_import",
        "claude_memory_plane_contract_body_import",
        "memory_injection_tiers_body_import",
        "operator_thread_memory_test_body_import",
        "agent_execution_trace_runtime_body_import",
        "strict_json_source_body_import",
        "agent_execution_trace_standard_body_import",
    }


def test_sleeper_memory_poisoning_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay"
    )
    args = [
        "run-quarantine-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 16
    assert first_card["sleeper_memory"]["session_count"] == 4
    assert first_card["sleeper_memory"]["proposal_count"] == 2
    assert first_card["sleeper_memory"]["quarantined_write_count"] == 1
    assert first_card["sleeper_memory"]["admitted_control_count"] == 1
    assert first_card["sleeper_memory"]["retrieval_replay_count"] == 1
    assert first_card["sleeper_memory"]["blocked_before_action_count"] == 1
    assert first_card["sleeper_memory"]["rollback_count"] == 1
    assert first_card["sleeper_memory"]["rerun_pass_count"] == 1
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert first_card["source_body_floor"]["body_material_count"] == 7
    assert first_card["source_body_floor"]["body_material_status"] == (
        SOURCE_MODULE_IMPORT_STATUS
    )
    assert "session_rows" not in _walk_keys(first_card)
    assert "write_rows" not in _walk_keys(first_card)
    assert "retrieval_rows" not in _walk_keys(first_card)
    assert "rollback_rows" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)
    assert "findings" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        sleeper_memory_poisoning_quarantine_replay,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
