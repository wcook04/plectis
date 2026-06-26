from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_benchmark_integrity_anti_gaming_trace,
)
import microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay as benchmark_replay
from microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_benchmark_integrity_bundle,
    validate_public_trace,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_benchmark_integrity_anti_gaming_replay/"
    "exported_benchmark_integrity_bundle"
)
CHECKED_IN_RUNTIME_BUNDLE_RECEIPT_DIR = (
    MICROCOSM_ROOT
    / "receipts/runtime_shell/demo_project/organs/"
    "agent_benchmark_integrity_anti_gaming_replay"
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


def _sha256_ref(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_agent_benchmark_integrity_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["benchmark_case_count"] == 3
    assert result["known_benchmark_case_ids"] == [
        "repo_issue_public_001",
        "repo_issue_public_002",
        "repo_issue_public_003",
    ]
    assert result["replay_count"] == 3
    assert result["integrity_pass_count"] == 2
    assert result["quarantine_count"] == 1
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["source_modules_pass"] is True
    assert result["source_module_import_count"] == 4
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["source_open_body_imports"]["material_classes"] == [
        "public_macro_pattern_body",
        "public_sanitized_real_benchmark_trace",
    ]
    assert result["source_artifact_evidence_ref_count"] == 12
    assert result["source_artifact_evidence_verified_count"] == 3
    assert result["real_benchmark_trace_verified_count"] == 3
    for row in result["replay_rows"]:
        assert row["source_artifact_evidence_verified"] is True
        assert row["source_artifact_evidence_ref_count"] == 4
        assert row["real_benchmark_trace_verified"] is True
        assert row["real_benchmark_trace_artifact_status"] == "pass"
        evidence = row["real_session_integrity_evidence"]
        assert evidence["evidence_source"] == (
            "manifest_verified_public_sanitized_real_benchmark_trace"
        )
        assert evidence["session_evidence_passes"] is True
        assert evidence["command_passed"] is True
        assert evidence["pytest_passed"] is True
        assert evidence["focused_scope_bound"] is True
        assert evidence["source_material_refs_bound_to_run_id"] is True
        assert evidence["file_access_backed_by_real_session"] is True
        assert evidence["contamination_backed_by_real_session"] is True
        assert evidence["trusted_reference_backed_by_real_session"] is True
    assert len(result["public_regression_fixture_refs"]) >= 3
    assert "public_replacement_refs" not in result
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    assert result["observed_negative_cases"]["real_trace_train_test_leakage"] == [
        "BENCHMARK_INTEGRITY_TRAIN_TEST_LEAKAGE"
    ]

    # The organ now COMPUTES the integrity verdict from contamination /
    # file-access / locked-evaluator spans instead of echoing the declared field.
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 3
    assert result["public_trace_integrity_pass_count"] == 2
    assert result["public_trace_quarantine_count"] == 1
    assert result["public_trace_finding_count"] == 0
    assert result["public_trace_status"] == "pass"
    assert "validator_source_digests" in result["freshness_basis"]
    assert set(result["freshness_basis"]["validator_source_digests"]) == {
        "organ_validator",
        "public_trace_builder",
    }
    for span in result["public_agent_execution_trace"]["spans"]:
        assert span["integrity_verdict_matches_declared"] is True
        assert (
            span["computed_integrity_verdict"] == span["declared_integrity_verdict"]
        )
    first_screen_rows = result["first_screen_integrity_rows"]
    assert len(first_screen_rows) == 3
    assert {row["case_id"] for row in first_screen_rows} == set(
        result["known_benchmark_case_ids"]
    )
    assert all(row["body_in_receipt"] is False for row in first_screen_rows)
    assert all(
        "benchmark_score_claim" in row["blocked_claims"] for row in first_screen_rows
    )
    assert all(
        "release_authorized" in row["blocked_claims"] for row in first_screen_rows
    )
    assert all(
        row["authority_ceiling"]
        == result["authority_ceiling"]["authority_ceiling"]
        for row in first_screen_rows
    )
    clean_rows = [
        row for row in first_screen_rows if row["fixture_role"] == "integrity_pass_replay"
    ]
    quarantine_rows = [
        row for row in first_screen_rows if row["fixture_role"] == "quarantine_replay"
    ]
    assert len(clean_rows) == 2
    assert len(quarantine_rows) == 1
    assert all(row["evaluator_signal"] is True for row in clean_rows)
    assert quarantine_rows[0]["reason_codes"]


def test_agent_benchmark_integrity_public_trace_recomputes_integrity_verdict() -> None:
    trace = build_public_benchmark_integrity_anti_gaming_trace(FIXTURE_INPUT)

    assert trace["status"] == "pass"
    assert trace["span_count"] == 3
    assert (
        trace["source_faithful_refactor"]["verification_mode"]
        == "extension_of_existing_public_refactor"
    )
    assert trace["audit"]["coverage"]["integrity_verdict_recompute_coverage"] is True
    assert trace["audit"]["coverage"]["locked_evaluator_coverage"] is True
    assert trace["audit"]["coverage"]["body_in_receipt"] is False

    by_replay = {span["span_id"].replace("span:", ""): span for span in trace["spans"]}
    assert (
        by_replay["replay_repo_issue_public_001_clean"]["computed_integrity_verdict"]
        == "integrity_pass"
    )
    assert (
        by_replay["replay_repo_issue_public_003_quarantined"][
            "computed_integrity_verdict"
        ]
        == "quarantine"
    )


def test_agent_benchmark_integrity_verdict_mismatch_is_caught(tmp_path: Path) -> None:
    # Flip a declared integrity verdict so it no longer matches the recomputation
    # (the quarantined replay carries a quarantine_reason_ref, so recomputation
    # forces quarantine); assert the new stable error code fires.
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
    )
    obs_path = fixture_copy / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["replay_observations"]:
        if row["replay_id"] == "replay_repo_issue_public_003_quarantined":
            row["integrity_verdict"] = "integrity_pass"
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    trace = build_public_benchmark_integrity_anti_gaming_trace(fixture_copy)
    assert trace["status"] == "blocked"
    trace_codes = {row["error_code"] for row in trace["audit"]["findings"]}
    assert "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH" in trace_codes

    folded = validate_public_trace(trace)
    folded_codes = {row["error_code"] for row in folded["findings"]}
    assert "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH" in folded_codes
    assert folded["status"] == "blocked"

    result = run(
        fixture_copy,
        public_root
        / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )
    assert result["status"] == "blocked"
    assert "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH" in result["error_codes"]
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)


def test_agent_benchmark_integrity_train_test_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
    )
    obs_path = fixture_copy / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["replay_observations"]:
        if row["replay_id"] == "replay_repo_issue_public_001_clean":
            row["training_material_contains_test_case"] = True
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root
        / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert "BENCHMARK_INTEGRITY_TRAIN_TEST_LEAKAGE" in result["error_codes"]
    assert "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH" in result["error_codes"]
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["declared_integrity_verdict"] == "integrity_pass"
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert "train_test_leakage" in corrupted["reason_codes"]


def test_agent_benchmark_integrity_rejects_invalid_declared_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
    )
    obs_path = fixture_copy / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["replay_observations"]:
        if row["replay_id"] == "replay_repo_issue_public_001_clean":
            row["integrity_verdict"] = "claimed_benchmark_win"
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root
        / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert "BENCHMARK_INTEGRITY_DECLARED_VERDICT_INVALID" in result["error_codes"]
    findings = [
        row
        for row in result["findings"]
        if row["error_code"] == "BENCHMARK_INTEGRITY_DECLARED_VERDICT_INVALID"
    ]
    assert findings
    assert {row["subject_kind"] for row in findings} == {"replay_observation"}
    replay_rows = {
        row["replay_id"]: row
        for row in result["replay_rows"]
    }
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["declared_integrity_verdict"] == "claimed_benchmark_win"
    assert corrupted["declared_integrity_verdict_valid"] is False
    assert corrupted["allowed_integrity_verdicts"] == [
        "integrity_pass",
        "quarantine",
    ]


def test_agent_benchmark_integrity_rejects_negative_case_label_swap(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
    )
    negative_path = fixture_copy / "train_test_leakage.json"
    negative = json.loads(negative_path.read_text(encoding="utf-8"))
    negative["expected_negative_case_id"] = "hidden_gold_access"
    negative_path.write_text(json.dumps(negative, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert "train_test_leakage" in result["missing_negative_cases"]
    assert "BENCHMARK_INTEGRITY_NEGATIVE_CASE_SEMANTIC_MISMATCH" in result[
        "error_codes"
    ]
    findings = [
        row
        for row in result["findings"]
        if row["error_code"] == "BENCHMARK_INTEGRITY_NEGATIVE_CASE_SEMANTIC_MISMATCH"
    ]
    assert findings
    assert findings[0]["negative_case_id"] == "hidden_gold_access"
    assert findings[0]["subject_id"] == "neg_train_test"


def test_agent_benchmark_integrity_rejects_evaluator_config_hash_swap(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
    )
    obs_path = fixture_copy / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["replay_observations"]:
        if row["replay_id"] == "replay_repo_issue_public_001_clean":
            row["evaluator_config_hash"] = "sha256:tampered-config"
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root
        / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["locked_evaluator_config_hash_count"] == 3
    assert "BENCHMARK_INTEGRITY_EVALUATOR_CONFIG_HASH_MISMATCH" in result[
        "error_codes"
    ]
    assert (
        "PUBLIC_TRACE_BENCHMARK_INTEGRITY_EVALUATOR_CONFIG_HASH_MISMATCH"
        in result["error_codes"]
    )
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["evaluator_id"] == "locked_repo_repair_scorer_v1"
    assert corrupted["evaluator_config_hash"] == "sha256:tampered-config"
    assert corrupted["evaluator_config_hash_matches_policy"] is False
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert "evaluator_config_hash_mismatch" in corrupted["reason_codes"]
    public_trace_findings = [
        row
        for row in result["findings"]
        if row["error_code"]
        == "PUBLIC_TRACE_BENCHMARK_INTEGRITY_EVALUATOR_CONFIG_HASH_MISMATCH"
    ]
    assert public_trace_findings
    assert {row["subject_kind"] for row in public_trace_findings} == {
        "public_agent_execution_trace"
    }


def test_agent_benchmark_integrity_rejects_missing_source_artifact_evidence(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    bundle = (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )
    obs_path = bundle / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["replay_observations"]:
        if row["replay_id"] == "replay_repo_issue_public_001_clean":
            row.pop("source_artifact_evidence_refs")
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run_benchmark_integrity_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "pass"
    assert "BENCHMARK_INTEGRITY_SOURCE_ARTIFACT_EVIDENCE_MISSING" in result[
        "error_codes"
    ]
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert corrupted["declared_integrity_verdict"] == "integrity_pass"
    assert corrupted["source_artifact_evidence_ref_count"] == 0
    assert corrupted["source_artifact_evidence_verified"] is False
    assert "source_artifact_evidence_missing" in corrupted["reason_codes"]


def test_agent_benchmark_integrity_requires_real_benchmark_trace(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    bundle = (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )
    obs_path = bundle / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["replay_observations"]:
        if row["replay_id"] == "replay_repo_issue_public_001_clean":
            row.pop("real_benchmark_trace_ref")
            row["source_artifact_evidence_refs"] = [
                ref
                for ref in row["source_artifact_evidence_refs"]
                if "source_artifacts/real_traces/" not in ref
            ]
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run_benchmark_integrity_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "BENCHMARK_INTEGRITY_REAL_TRACE_EVIDENCE_MISSING" in result[
        "error_codes"
    ]
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert corrupted["declared_integrity_verdict"] == "integrity_pass"
    assert corrupted["real_benchmark_trace_verified"] is False
    assert "real_benchmark_trace_missing" in corrupted["reason_codes"]


def test_agent_benchmark_integrity_parsed_evidence_mutation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    bundle = (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )
    contamination_path = (
        bundle / "receipts/benchmark_integrity/contamination_001.json"
    )
    contamination = json.loads(contamination_path.read_text(encoding="utf-8"))
    contamination["training_material_contains_test_case"] = True
    contamination_path.write_text(
        json.dumps(contamination, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_benchmark_integrity_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["declared_integrity_verdict"] == "integrity_pass"
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert corrupted["parsed_evidence_integrity"]["evidence_passes"] is False
    assert corrupted["parsed_evidence_integrity"][
        "contamination_check_passes"
    ] is False
    assert corrupted["parsed_evidence_integrity"]["contamination_flags"][
        "training_material_contains_test_case"
    ] is True
    assert "parsed_evidence_unverified" in corrupted["reason_codes"]
    assert "contamination_evidence_failed" in corrupted["reason_codes"]
    assert "train_test_leakage" in corrupted["reason_codes"]


def test_agent_benchmark_integrity_requires_replay_for_each_case(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
    )
    obs_path = fixture_copy / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    observations["replay_observations"] = [
        row
        for row in observations["replay_observations"]
        if row["case_id"] != "repo_issue_public_002"
    ]
    obs_path.write_text(
        json.dumps(observations, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_copy,
        public_root
        / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["benchmark_case_count"] == 3
    assert result["replay_count"] == 2
    assert result["missing_replay_case_ids"] == ["repo_issue_public_002"]
    assert "BENCHMARK_INTEGRITY_CASE_REPLAY_MISSING" in result["error_codes"]
    findings = [
        row
        for row in result["findings"]
        if row["error_code"] == "BENCHMARK_INTEGRITY_CASE_REPLAY_MISSING"
    ]
    assert findings
    assert {row["subject_kind"] for row in findings} == {"benchmark_case"}
    assert result["benchmark_integrity_board"]["missing_replay_case_ids"] == [
        "repo_issue_public_002"
    ]


def test_agent_benchmark_integrity_receipts_are_public_relative_and_body_free(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input",
        public_root / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
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
        assert "provider_payload" not in _walk_keys(json.loads(text))
        assert "private_issue_body" not in _walk_keys(json.loads(text))
        assert "body_redacted" not in _walk_keys(json.loads(text))


def test_agent_benchmark_integrity_source_modules_are_digest_verified(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["source_module_manifest_ref"] == (
        "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle/source_module_manifest.json"
    )
    assert result["source_module_import_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    material_classes = {row["material_class"] for row in result["source_module_imports"]}
    assert material_classes == {
        "public_macro_pattern_body",
        "public_sanitized_real_benchmark_trace",
    }
    for row in result["source_module_imports"]:
        assert row["sha256"] == row["actual_sha256"]
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        assert row["material_class"] in material_classes
        assert row["source_to_target_relation"] == "source_faithful_json_slice"
        assert row["target_ref"].startswith(
            "examples/agent_benchmark_integrity_anti_gaming_replay/"
            "exported_benchmark_integrity_bundle/source_artifacts/"
        )


def test_agent_benchmark_integrity_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_benchmark_integrity_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_benchmark_integrity_bundle"
    assert result["bundle_id"] == "agent_benchmark_integrity_anti_gaming_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["benchmark_case_count"] == 3
    assert result["known_benchmark_case_ids"] == [
        "repo_issue_public_001",
        "repo_issue_public_002",
        "repo_issue_public_003",
    ]
    assert result["replay_count"] == 3
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["source_modules_pass"] is True
    assert result["source_module_import_count"] == 4
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["source_artifact_evidence_ref_count"] == 12
    assert result["source_artifact_evidence_verified_count"] == 3
    assert result["real_benchmark_trace_verified_count"] == 3


def test_agent_benchmark_integrity_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    bundle = (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_benchmark_integrity_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "BENCHMARK_INTEGRITY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_agent_benchmark_integrity_rejects_digest_matched_fake_real_trace(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    bundle = (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trace_module = next(
        row
        for row in manifest["modules"]
        if row["material_class"] == "public_sanitized_real_benchmark_trace"
    )
    trace_path = bundle / trace_module["path"]
    fake_trace = {
        "schema_version": "public_sanitized_real_benchmark_trace_v1",
        "material_class": "public_sanitized_real_benchmark_trace",
        "body_in_receipt": False,
        "status": "completed",
        "exit_code": 0,
        "real_episode_id": "fake_trace_not_command_run",
        "run_id": "fake_trace_not_command_run",
        "command_run_metadata_sha256": "sha256:" + ("1" * 64),
        "stdout_sha256": "sha256:" + ("2" * 64),
        "stderr_sha256": "sha256:" + ("3" * 64),
        "source_material_refs": ["fixtures/not_a_command_run.json"],
        "omitted_live_material": ["raw provider payloads"],
    }
    trace_path.write_text(
        json.dumps(fake_trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_module["sha256"] = _sha256_ref(trace_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_benchmark_integrity_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert result["source_modules_pass"] is False
    trace_rows = [
        row
        for row in result["source_module_imports"]
        if row["material_class"] == "public_sanitized_real_benchmark_trace"
    ]
    assert trace_rows
    assert trace_rows[0]["sha256"] == trace_rows[0]["actual_sha256"]
    assert trace_rows[0]["real_trace_artifact_status"] == "blocked"
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert corrupted["declared_integrity_verdict"] == "integrity_pass"
    assert corrupted["real_benchmark_trace_verified"] is False
    assert corrupted["real_benchmark_trace_artifact_status"] == "blocked"
    evidence = corrupted["real_session_integrity_evidence"]
    assert evidence["session_evidence_passes"] is False
    assert evidence["source_material_refs_bound_to_run_id"] is False
    assert evidence["public_boundary_declared"] is False
    assert "real_benchmark_trace_unverified" in corrupted["reason_codes"]
    assert "BENCHMARK_INTEGRITY_SOURCE_MODULE_DIGEST_MISMATCH" not in result["error_codes"]
    assert "BENCHMARK_INTEGRITY_REAL_TRACE_SOURCE_MATERIAL_REFS_INVALID" in result[
        "error_codes"
    ]
    assert "BENCHMARK_INTEGRITY_REAL_TRACE_PUBLIC_BOUNDARY_INCOMPLETE" in result[
        "error_codes"
    ]


def test_agent_benchmark_integrity_rejects_digest_matched_semantic_trace_mutation(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    bundle = (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trace_module = next(
        row
        for row in manifest["modules"]
        if row["material_class"] == "public_sanitized_real_benchmark_trace"
    )
    trace_path = bundle / trace_module["path"]
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["trace_role"] = "generic_command_run"
    trace["argv_shape"] = [
        "repo-python",
        "-m",
        "pytest",
        "microcosm-substrate/tests/test_unrelated.py",
        "-q",
    ]
    trace["scope_paths"] = ["microcosm-substrate/tests/test_unrelated.py"]
    trace["pytest_summary"] = {"failed": 0, "passed": 0, "warning_count": 0}
    trace_path.write_text(
        json.dumps(trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_module["sha256"] = _sha256_ref(trace_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_benchmark_integrity_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert "BENCHMARK_INTEGRITY_SOURCE_MODULE_DIGEST_MISMATCH" not in result["error_codes"]
    for code in (
        "BENCHMARK_INTEGRITY_REAL_TRACE_ROLE_MISMATCH",
        "BENCHMARK_INTEGRITY_REAL_TRACE_ARGV_SHAPE_INVALID",
        "BENCHMARK_INTEGRITY_REAL_TRACE_SCOPE_MISMATCH",
        "BENCHMARK_INTEGRITY_REAL_TRACE_PYTEST_SUMMARY_INVALID",
    ):
        assert code in result["error_codes"]
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["declared_integrity_verdict"] == "integrity_pass"
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert corrupted["real_benchmark_trace_verified"] is False
    assert corrupted["real_benchmark_trace_artifact_status"] == "blocked"
    evidence = corrupted["real_session_integrity_evidence"]
    assert evidence["session_evidence_passes"] is False
    assert evidence["focused_scope_bound"] is False
    assert evidence["pytest_passed"] is False
    assert "real_benchmark_trace_unverified" in corrupted["reason_codes"]


def test_agent_benchmark_integrity_rejects_digest_matched_stale_real_trace_binding(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    bundle = (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trace_module = next(
        row
        for row in manifest["modules"]
        if row["material_class"] == "public_sanitized_real_benchmark_trace"
    )
    trace_path = bundle / trace_module["path"]
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["source_material_refs"] = [
        "state/command_runs/runs/cmdrun_20260604T000000Z_stale.json",
        "state/command_runs/outputs/cmdrun_20260604T000000Z_stale.stdout",
        "state/command_runs/outputs/cmdrun_20260604T000000Z_stale.stderr",
    ]
    trace["real_episode_id"] = "benchmark_integrity_pytest_cmdrun_20260604T000000Z_stale"
    trace_path.write_text(
        json.dumps(trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_module["sha256"] = _sha256_ref(trace_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_benchmark_integrity_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert "BENCHMARK_INTEGRITY_SOURCE_MODULE_DIGEST_MISMATCH" not in result["error_codes"]
    assert "BENCHMARK_INTEGRITY_REAL_TRACE_SOURCE_MATERIAL_REFS_INVALID" not in result[
        "error_codes"
    ]
    assert "BENCHMARK_INTEGRITY_REAL_TRACE_RUN_ID_SOURCE_REF_MISMATCH" in result[
        "error_codes"
    ]
    assert "BENCHMARK_INTEGRITY_REAL_TRACE_EPISODE_RUN_ID_MISMATCH" in result[
        "error_codes"
    ]
    replay_rows = {row["replay_id"]: row for row in result["replay_rows"]}
    corrupted = replay_rows["replay_repo_issue_public_001_clean"]
    assert corrupted["declared_integrity_verdict"] == "integrity_pass"
    assert corrupted["computed_integrity_verdict"] == "quarantine"
    assert corrupted["real_benchmark_trace_verified"] is False
    assert corrupted["real_benchmark_trace_artifact_status"] == "blocked"
    evidence = corrupted["real_session_integrity_evidence"]
    assert evidence["session_evidence_passes"] is False
    assert evidence["source_material_refs_bound_to_run_id"] is False
    assert evidence["real_episode_bound_to_run_id"] is False
    assert "real_benchmark_trace_unverified" in corrupted["reason_codes"]


def test_agent_benchmark_integrity_rejects_source_module_manifest_boundaries(
    tmp_path: Path,
) -> None:
    cases = [
        (
            "missing_manifest",
            "BENCHMARK_INTEGRITY_SOURCE_MODULE_MANIFEST_MISSING",
            "source_module_manifest",
        ),
        (
            "manifest_import_class_mismatch",
            "BENCHMARK_INTEGRITY_SOURCE_IMPORT_CLASS_MISMATCH",
            "source_module_manifest",
        ),
        (
            "manifest_body_in_receipt",
            "BENCHMARK_INTEGRITY_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
            "source_module_manifest",
        ),
        (
            "manifest_body_text_in_receipt",
            "BENCHMARK_INTEGRITY_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
            "source_module_manifest",
        ),
        (
            "row_import_class_mismatch",
            "BENCHMARK_INTEGRITY_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
            "source_module",
        ),
        (
            "row_material_class_forbidden",
            "BENCHMARK_INTEGRITY_SOURCE_MODULE_CLASS_FORBIDDEN",
            "source_module",
        ),
        (
            "row_body_boundary_invalid",
            "BENCHMARK_INTEGRITY_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
            "source_module",
        ),
        (
            "row_body_text_in_receipt",
            "BENCHMARK_INTEGRITY_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
            "source_module",
        ),
        (
            "row_relation_unverified",
            "BENCHMARK_INTEGRITY_SOURCE_MODULE_RELATION_UNVERIFIED",
            "source_module",
        ),
        (
            "target_missing",
            "BENCHMARK_INTEGRITY_SOURCE_MODULE_TARGET_MISSING",
            "source_module",
        ),
    ]

    for case_id, expected_code, expected_subject_kind in cases:
        public_root = tmp_path / case_id / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        shutil.copytree(
            MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
            public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
        )
        bundle = (
            public_root
            / "examples/agent_benchmark_integrity_anti_gaming_replay/"
            "exported_benchmark_integrity_bundle"
        )
        manifest_path = bundle / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        first_module = manifest["modules"][0]

        if case_id == "missing_manifest":
            manifest_path.unlink()
        elif case_id == "manifest_import_class_mismatch":
            manifest["source_import_class"] = "private_macro_body"
        elif case_id == "manifest_body_in_receipt":
            manifest["body_in_receipt"] = True
        elif case_id == "manifest_body_text_in_receipt":
            manifest["body_text_in_receipt"] = True
        elif case_id == "row_import_class_mismatch":
            first_module["source_import_class"] = "private_macro_body"
        elif case_id == "row_material_class_forbidden":
            first_module["material_class"] = "private_macro_body"
        elif case_id == "row_body_boundary_invalid":
            first_module["body_in_receipt"] = True
        elif case_id == "row_body_text_in_receipt":
            first_module["body_text_in_receipt"] = True
        elif case_id == "row_relation_unverified":
            first_module["source_to_target_relation"] = "unverified_copy"
        elif case_id == "target_missing":
            (bundle / first_module["path"]).unlink()

        if manifest_path.exists():
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        result = run_benchmark_integrity_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            f"agent_benchmark_integrity_anti_gaming_replay/{case_id}",
            command="pytest",
        )

        assert result["status"] == "blocked"
        assert result["source_module_import_status"] == "blocked"
        assert result["source_modules_pass"] is False
        assert expected_code in result["error_codes"]
        findings = [
            row for row in result["findings"] if row["error_code"] == expected_code
        ]
        assert findings
        assert {row["subject_kind"] for row in findings} == {expected_subject_kind}
        assert result["private_state_scan"]["blocking_hit_count"] == 0
        receipt_text = json.dumps(result, sort_keys=True)
        assert "def build_public_benchmark_integrity_anti_gaming_trace(" not in receipt_text
        assert "TRACE_OUTPUT_PRIVACY_BOUNDARY =" not in receipt_text


def test_agent_benchmark_integrity_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay"
    )
    args = [
        "run-benchmark-integrity-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 22
    assert first_card["benchmark_integrity"]["benchmark_case_count"] == 3
    assert first_card["benchmark_integrity"]["known_benchmark_case_count"] == 3
    assert first_card["benchmark_integrity"]["replay_count"] == 3
    assert first_card["benchmark_integrity"]["integrity_pass_count"] == 2
    assert first_card["benchmark_integrity"]["quarantine_count"] == 1
    assert first_card["benchmark_integrity"]["source_artifact_evidence_ref_count"] == 12
    assert first_card["benchmark_integrity"][
        "source_artifact_evidence_verified_count"
    ] == 3
    assert first_card["benchmark_integrity"]["real_benchmark_trace_verified_count"] == 3
    assert first_card["benchmark_integrity"]["source_module_import_count"] == 4
    assert first_card["benchmark_integrity"]["copied_source_artifact_count"] == 4
    assert first_card["benchmark_integrity"]["source_modules_pass"] is True
    assert first_card["first_screen"]["integrity_row_count"] == 3
    assert set(first_card["first_screen"]["blocked_claim_ids"]) >= {
        "benchmark_score_claim",
        "release_authorized",
    }
    assert first_card["first_screen"]["body_in_receipt"] is False
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert "benchmark_cases" not in _walk_keys(first_card)
    assert "replay_rows" not in _walk_keys(first_card)
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(benchmark_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_agent_benchmark_integrity_stale_checked_in_receipt_is_not_reused(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    stale_receipt_path = (
        CHECKED_IN_RUNTIME_BUNDLE_RECEIPT_DIR / benchmark_replay.BUNDLE_RESULT_NAME
    )
    stale_receipt = json.loads(stale_receipt_path.read_text(encoding="utf-8"))
    stale_basis = stale_receipt["freshness_basis"]
    current_basis = benchmark_replay._freshness_basis(
        BUNDLE_INPUT,
        include_negative=False,
    )

    assert stale_basis["input_count"] == 9
    assert stale_receipt["source_module_import_count"] == 3
    assert current_basis["input_count"] == 22
    assert current_basis["basis_digest"] != stale_basis["basis_digest"]
    assert (
        benchmark_replay._fresh_bundle_receipt(
            BUNDLE_INPUT,
            CHECKED_IN_RUNTIME_BUNDLE_RECEIPT_DIR,
        )
        is None
    )

    out = tmp_path / "receipts/runtime_shell/demo_project/organs"
    out = out / "agent_benchmark_integrity_anti_gaming_replay"
    shutil.copytree(CHECKED_IN_RUNTIME_BUNDLE_RECEIPT_DIR, out)
    original_build_result = benchmark_replay._build_result
    rebuilt = {"called": False}

    def tracking_build_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
        rebuilt["called"] = True
        return original_build_result(*args, **kwargs)

    monkeypatch.setattr(benchmark_replay, "_build_result", tracking_build_result)

    result = run_benchmark_integrity_bundle(
        BUNDLE_INPUT,
        out,
        reuse_fresh_receipt=True,
    )

    assert rebuilt["called"] is True
    assert result["receipt_reused"] is False
    assert result["freshness_basis"]["basis_digest"] == current_basis["basis_digest"]
    assert result["freshness_basis"]["input_count"] == 22
    assert result["source_module_import_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    assert result["source_artifact_evidence_verified_count"] == 3
    assert result["real_benchmark_trace_verified_count"] == 3

    rewritten = json.loads(
        (out / benchmark_replay.BUNDLE_RESULT_NAME).read_text(encoding="utf-8")
    )
    assert rewritten["freshness_basis"]["basis_digest"] == current_basis["basis_digest"]
