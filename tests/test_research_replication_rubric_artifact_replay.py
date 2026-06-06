from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_research_replication_trace,
)
from microcosm_core.organs import research_replication_rubric_artifact_replay
from microcosm_core.organs.research_replication_rubric_artifact_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_replication_bundle,
    validate_research_replays,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/research_replication_rubric_artifact_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/research_replication_rubric_artifact_replay/"
    "exported_research_replication_bundle"
)
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"
RESEARCH_REPLICATION_SOURCE_MODULE_IDS = {
    "research_replication_deterministic_pattern_order_body_import",
    "research_replication_extracted_pattern_ledger_row_body_import",
    "research_replication_high_novelty_growth_receipt_body_import",
    "research_replication_replay_control_plane_source_body_import",
}
RESEARCH_REPLICATION_PATTERN_SOURCE_MODULE_IDS = {
    "research_replication_deterministic_pattern_order_body_import",
    "research_replication_extracted_pattern_ledger_row_body_import",
    "research_replication_high_novelty_growth_receipt_body_import",
}
RESEARCH_REPLICATION_CONTROL_PLANE_SOURCE_MODULE_ID = (
    "research_replication_replay_control_plane_source_body_import"
)
EXECUTION_ARTIFACT_RESULT_REF = "execution_artifacts/artifacts/result_table.json"
EXECUTION_ARTIFACT_HASH_REF = "execution_artifacts/artifacts/result_table.sha256.json"
EXECUTION_ARTIFACT_METRIC_REF = "execution_artifacts/metrics/public_sum_metric.json"
EXECUTION_ARTIFACT_METRIC_HASH_REF = (
    "execution_artifacts/metrics/public_sum_metric.sha256.json"
)
EXECUTION_ARTIFACT_INPUT_REF = "execution_artifacts/inputs/public_synthetic_table.json"
EXECUTION_ARTIFACT_INPUT_HASH_REF = (
    "execution_artifacts/inputs/public_synthetic_table.sha256.json"
)


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


def _copy_bundle(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/research_replication_rubric_artifact_replay/"
        "exported_research_replication_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    return bundle


def _copy_fixture_input(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/research_replication_rubric_artifact_replay",
        public_root / "examples/research_replication_rubric_artifact_replay",
    )
    fixture = (
        public_root
        / "fixtures/first_wave/research_replication_rubric_artifact_replay"
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/research_replication_rubric_artifact_replay",
        fixture,
    )
    return fixture / "input"


def _mutate_json(path: Path, mutate: Any) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_research_replication_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/research_replication_rubric_artifact_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "research_replication_rubric_artifact_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["paper_count"] == 2
    assert result["replay_count"] == 2
    assert result["artifact_replay_count"] == 2
    assert result["cold_rerun_count"] == 2
    assert result["declared_artifact_hash_ref_count"] == 1
    assert result["declared_artifact_hash_refs"] == [EXECUTION_ARTIFACT_HASH_REF]
    assert result["execution_artifact_replay_status"] == "pass"
    assert result["execution_artifact_metric_count"] == 1
    assert result["execution_artifact_computed_output_count"] == 1
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["negative_case_verdict_basis"]["verdict_source"] == (
        "semantic_replay_row_fields"
    )
    assert result["negative_case_verdict_basis"]["coverage_case_id_source"] == (
        "derived_error_code_semantics_not_fixture_filename"
    )
    assert (
        result["negative_case_verdict_basis"]["declared_fixture_labels_used"]
        is False
    )
    assert result["authority_ceiling"]["benchmark_performance_claim_authorized"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["source_modules_pass"] is True
    assert result["source_module_import_count"] == len(RESEARCH_REPLICATION_SOURCE_MODULE_IDS)
    assert result["source_open_body_imports"]["body_material_count"] == len(
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )
    assert result["source_open_body_imports"]["material_classes"] == [
        "public_macro_pattern_body",
        "public_python_source_body",
    ]
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_research_replication_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/research_replication_rubric_artifact_replay",
        public_root / "fixtures/first_wave/research_replication_rubric_artifact_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/research_replication_rubric_artifact_replay",
        public_root / "examples/research_replication_rubric_artifact_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/research_replication_rubric_artifact_replay/input",
        public_root / "receipts/first_wave/research_replication_rubric_artifact_replay",
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
        assert "private_paper_body" not in keys
        assert "hidden_rubric_body" not in keys
        assert "provider_payload" not in keys
        assert "private_state_scan" not in keys
        assert "body_redacted" not in keys


def test_research_replication_source_modules_are_digest_verified(tmp_path: Path) -> None:
    result = run_replication_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["source_module_manifest_ref"] == (
        "examples/research_replication_rubric_artifact_replay/"
        "exported_research_replication_bundle/source_module_manifest.json"
    )
    assert result["source_module_import_count"] == len(RESEARCH_REPLICATION_SOURCE_MODULE_IDS)
    assert result["copied_source_artifact_count"] == len(
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )
    assert set(row["module_id"] for row in result["source_module_imports"]) == (
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )
    for row in result["source_module_imports"]:
        assert row["sha256"] == row["actual_sha256"]
        assert row["body_in_receipt"] is False
        if row["module_id"] == RESEARCH_REPLICATION_CONTROL_PLANE_SOURCE_MODULE_ID:
            assert row["material_class"] == "public_python_source_body"
            assert row["source_to_target_relation"] == "exact_copy"
            assert row["target_ref"].endswith(
                "source_modules/microcosm_core/organs/"
                "research_replication_rubric_artifact_replay.py"
            )
            assert row["source_path_exists"] is True
            assert row["source_current"] is True
            assert row["source_target_exact_copy"] is True
            assert row["source_sha256"] == row["target_sha256"]
            assert row["actual_source_sha256"] == row["actual_sha256"]
        else:
            assert row["module_id"] in RESEARCH_REPLICATION_PATTERN_SOURCE_MODULE_IDS
            assert row["material_class"] == "public_macro_pattern_body"
            assert row["source_to_target_relation"] == "source_faithful_json_slice"
            assert row["target_ref"].startswith(
                "examples/research_replication_rubric_artifact_replay/"
                "exported_research_replication_bundle/source_artifacts/"
            )

    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == len(RESEARCH_REPLICATION_SOURCE_MODULE_IDS)
    assert set(row["module_id"] for row in manifest["modules"]) == (
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )


def test_research_replication_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/research_replication_rubric_artifact_replay",
        public_root / "examples/research_replication_rubric_artifact_replay",
    )
    bundle = (
        public_root
        / "examples/research_replication_rubric_artifact_replay/"
        "exported_research_replication_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_replication_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "REPLICATION_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_research_replication_rejects_bundle_local_source_module_body_tamper(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/research_replication_rubric_artifact_replay",
        public_root / "examples/research_replication_rubric_artifact_replay",
    )
    bundle = (
        public_root
        / "verifier_mutations/research_replication_rubric_artifact_replay/"
        "exported_research_replication_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    source_module = (
        bundle
        / "source_modules/microcosm_core/organs/"
        "research_replication_rubric_artifact_replay.py"
    )
    source_module.write_text(
        source_module.read_text(encoding="utf-8")
        + "\nBUNDLE_LOCAL_TAMPER_SENTINEL = True\n",
        encoding="utf-8",
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "REPLICATION_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    control_plane_row = next(
        row
        for row in result["source_module_imports"]
        if row["module_id"] == RESEARCH_REPLICATION_CONTROL_PLANE_SOURCE_MODULE_ID
    )
    assert "verifier_mutations/research_replication_rubric_artifact_replay" in (
        control_plane_row["target_ref"]
    )
    assert control_plane_row["sha256"] != control_plane_row["actual_sha256"]


def test_research_replication_rejects_rehashed_source_module_body_swap(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    source_module = (
        bundle
        / "source_modules/microcosm_core/organs/"
        "research_replication_rubric_artifact_replay.py"
    )
    source_module.write_text(
        source_module.read_text(encoding="utf-8")
        + "\nBUNDLE_LOCAL_SELF_CONSISTENT_SWAP = True\n",
        encoding="utf-8",
    )
    rehashed_digest = _sha256(source_module)

    def mutate(payload: dict[str, Any]) -> None:
        for row in payload["modules"]:
            if row["module_id"] == RESEARCH_REPLICATION_CONTROL_PLANE_SOURCE_MODULE_ID:
                row["sha256"] = rehashed_digest
                row["source_sha256"] = rehashed_digest
                row["target_sha256"] = rehashed_digest

    _mutate_json(bundle / "source_module_manifest.json", mutate)

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "REPLICATION_SOURCE_MODULE_DIGEST_MISMATCH" not in result["error_codes"]
    assert "REPLICATION_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert (
        "REPLICATION_SOURCE_MODULE_SOURCE_TARGET_COPY_MISMATCH"
        in result["error_codes"]
    )
    control_plane_row = next(
        row
        for row in result["source_module_imports"]
        if row["module_id"] == RESEARCH_REPLICATION_CONTROL_PLANE_SOURCE_MODULE_ID
    )
    assert control_plane_row["sha256"] == control_plane_row["actual_sha256"]
    assert control_plane_row["target_sha256"] == control_plane_row["actual_sha256"]
    assert control_plane_row["source_current"] is False
    assert control_plane_row["source_target_exact_copy"] is False
    assert control_plane_row["actual_source_sha256"] != control_plane_row["actual_sha256"]


def test_research_replication_fixture_manifest_counts_source_open_body_floor() -> None:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/"
            "research_replication_rubric_artifact_replay.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )

    source_imports = manifest["source_open_body_imports"]
    assert manifest["body_copied_material_count"] == len(
        RESEARCH_REPLICATION_PATTERN_SOURCE_MODULE_IDS
    )
    assert source_imports["status"] == "pass"
    assert source_imports["source_import_class"] == "copied_non_secret_macro_body"
    assert source_imports["body_material_count"] == len(
        RESEARCH_REPLICATION_PATTERN_SOURCE_MODULE_IDS
    )
    assert set(source_imports["body_material_ids"]) == (
        RESEARCH_REPLICATION_PATTERN_SOURCE_MODULE_IDS
    )
    assert source_imports["body_in_receipt"] is False
    assert (
        source_imports["aggregate_floor_ref"]
        == "examples/research_replication_rubric_artifact_replay/exported_research_replication_bundle/source_module_manifest.json::modules"
    )


def test_research_replication_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_replication_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_research_replication_bundle"
    assert result["bundle_id"] == "research_replication_rubric_artifact_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["paper_count"] == 2
    assert result["replay_count"] == 2
    assert result["declared_artifact_hash_ref_count"] == 1
    replay = result["execution_artifact_replay"]
    assert result["execution_artifact_replay_status"] == "pass"
    assert replay["status"] == "pass"
    assert replay["verdict_source"] == (
        "local_metric_script_execution_over_allowed_public_inputs"
    )
    assert result["replay_evidence_rung"] == "R3"
    assert result["replay_evidence_state"] == "real_metric_hash_replay"
    assert replay["evidence_rung"] == "R3"
    assert replay["evidence_state"] == "real_metric_hash_replay"
    assert replay["rung_evidence"]["rank_rederived_from"] == [
        "local_metric_script_execution",
        "allowed_public_input_body_hash",
        "metric_script_body_hash",
        "declared_output_artifact_hash",
    ]
    assert replay["rung_evidence"]["metric_script_executed_count"] == 1
    assert replay["rung_evidence"]["input_body_hash_verified_count"] == 1
    assert replay["rung_evidence"]["metric_body_hash_verified_count"] == 1
    assert replay["declared_fixture_labels_used"] is False
    assert replay["hash_verification_basis"] == (
        "input_metric_body_hash_refs_plus_output_artifact_ref_and_sha256"
    )
    assert replay["computed_output_refs"] == [EXECUTION_ARTIFACT_RESULT_REF]
    assert replay["declared_artifact_hash_refs"] == [EXECUTION_ARTIFACT_HASH_REF]
    assert replay["declared_public_input_hash_refs"] == [
        EXECUTION_ARTIFACT_INPUT_HASH_REF
    ]
    assert replay["declared_metric_script_hash_refs"] == [
        EXECUTION_ARTIFACT_METRIC_HASH_REF
    ]
    assert replay["allowed_public_input_refs"] == [
        "execution_artifacts/inputs/public_synthetic_table.json"
    ]
    assert replay["cited_metric_script_refs"] == [EXECUTION_ARTIFACT_METRIC_REF]
    assert replay["cited_allowed_public_input_refs"] == [EXECUTION_ARTIFACT_INPUT_REF]
    assert replay["cited_declared_artifact_hash_refs"] == [EXECUTION_ARTIFACT_HASH_REF]
    metric = replay["metric_results"][0]
    assert metric["metric_id"] == "public_sum_metric"
    assert metric["execution_mode"] == "local_metric_script_over_allowed_public_input"
    assert metric["metric_script_executed"] is True
    assert metric["metric_ref"] == EXECUTION_ARTIFACT_METRIC_REF
    assert metric["metric_hash_ref"] == EXECUTION_ARTIFACT_METRIC_HASH_REF
    assert metric["metric_script_refs"] == [EXECUTION_ARTIFACT_METRIC_REF]
    assert metric["metric_body_hash_matches_declared"] is True
    assert metric["declared_metric_file_sha256"] == _sha256(
        BUNDLE_INPUT / EXECUTION_ARTIFACT_METRIC_REF
    )
    assert metric["input_ref"] == EXECUTION_ARTIFACT_INPUT_REF
    assert metric["input_hash_ref"] == EXECUTION_ARTIFACT_INPUT_HASH_REF
    assert metric["input_body_hash_matches_declared"] is True
    assert metric["declared_input_file_sha256"] == _sha256(
        BUNDLE_INPUT / EXECUTION_ARTIFACT_INPUT_REF
    )
    assert metric["allowed_public_input_refs"] == [EXECUTION_ARTIFACT_INPUT_REF]
    assert metric["produced_output_payload"] == {"public_sum": 5, "row_count": 2}
    assert metric["declared_hash_ref"] == EXECUTION_ARTIFACT_HASH_REF
    assert metric["declared_output_matches_produced_output"] is True
    assert metric["declared_hash_matches_produced_output"] is True
    assert metric["input_metric_hashes_match_declared"] is True
    assert metric["produced_output_file_sha256"] == metric["declared_output_file_sha256"]
    assert metric["actual_output_file_sha256"] == metric["declared_output_file_sha256"]
    assert (
        metric["computed_output_canonical_sha256"]
        == metric["output_payload_canonical_sha256"]
    )
    assert result["authority_ceiling"]["publication_authorized"] is False
    assert "public_replacement_refs" not in result
    assert "private_state_scan" not in result
    assert result["source_modules_pass"] is True
    assert result["source_module_import_count"] == len(RESEARCH_REPLICATION_SOURCE_MODULE_IDS)
    assert result["source_open_body_imports"]["body_material_count"] == len(
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )
    verification = result["body_import_verification"]
    assert verification["verification_status"] == "verified"
    assert verification["verification_mode"] == (
        "extension_of_existing_public_refactor_with_live_digest_relation"
    )
    assert verification["body_import_classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert verification["source_to_target_relation"] == (
        "source_faithful_public_refactor"
    )
    assert verification["digest_relation"] == "source_target_refactor_digests_recorded"
    assert verification["source_ref"] == "system/lib/agent_execution_trace.py"
    assert verification["target_file_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
    assert verification["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/"
        "agent_execution_trace.py::build_public_research_replication_trace"
    )
    assert verification["source_body_digest"] == _sha256(
        SOURCE_ROOT / "system/lib/agent_execution_trace.py"
    )
    assert verification["target_body_digest"] == _sha256(
        MICROCOSM_ROOT / "src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
    assert verification["source_module_digest_relation"] == (
        "manifest_target_digests_verified"
    )
    assert verification["source_module_digest_count"] == len(
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert result["body_import_verification"]["verification_mode"] == (
        "extension_of_existing_public_refactor_with_live_digest_relation"
    )
    assert (
        result["public_agent_execution_trace"]["source_faithful_refactor"][
            "verification_mode"
        ]
        == "extension_of_existing_public_refactor"
    )
    assert result["public_agent_execution_trace"]["span_count"] == 2
    assert result["public_agent_execution_trace"]["audit"]["coverage"][
        "cold_rerun_coverage"
    ] is True


def test_research_replication_rejects_wrong_execution_artifact_hash(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    _mutate_json(
        bundle / EXECUTION_ARTIFACT_HASH_REF,
        lambda payload: payload.update({"sha256": "sha256:" + ("0" * 64)}),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_ARTIFACT_HASH_MISMATCH" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["declared_hash_matches_produced_output"] is False
    assert metric["declared_output_matches_produced_output"] is True


def test_research_replication_rejects_wrong_artifact_ref_with_matching_hash(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    _mutate_json(
        bundle / EXECUTION_ARTIFACT_HASH_REF,
        lambda payload: payload.update(
            {"artifact_ref": "execution_artifacts/artifacts/other_result_table.json"}
        ),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_ARTIFACT_HASH_MISMATCH" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["declared_output_matches_produced_output"] is True
    assert metric["declared_hash_matches_produced_output"] is True


def test_research_replication_rejects_report_only_exported_replay(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        row = payload["research_replays"][0]
        row["report_only_success"] = True
        row["metric_script_refs"] = []
        row["artifact_hash_refs"] = []
        row["cold_rerun_receipt_ref"] = ""

    _mutate_json(bundle / "research_replays.json", mutate)

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["execution_artifact_replay_status"] == "pass"
    assert "REPLICATION_REPORT_ONLY_SUCCESS" in result["error_codes"]


def test_research_replication_exported_bundle_ignores_self_declared_pass_labels(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        row = payload["research_replays"][0]
        row["report_only_success"] = True
        row["metric_script_refs"] = []
        row["artifact_hash_refs"] = []
        row["cold_rerun_receipt_ref"] = ""
        row["status"] = "pass"
        row["declared_status"] = "pass"
        row["expected_status"] = "pass"
        row["error_codes"] = []
        row["expected_error_codes"] = []

    _mutate_json(bundle / "research_replays.json", mutate)

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "REPLICATION_REPORT_ONLY_SUCCESS" in result["error_codes"]
    assert (
        result["negative_case_verdict_basis"]["declared_fixture_labels_used"]
        is False
    )
    assert result["execution_artifact_replay"]["declared_fixture_labels_used"] is False


def test_research_replication_rejects_metric_perturbation(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    _mutate_json(
        bundle / "execution_artifacts/metrics/public_sum_metric.json",
        lambda payload: payload.update({"input_field": "perturbed_value"}),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_INPUT_INVALID" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["metric_script_executed"] is False
    assert metric["produced_output_payload"] is None


def test_research_replication_rejects_valid_metric_script_body_swap(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    _mutate_json(
        bundle / "execution_artifacts/metrics/public_sum_metric.json",
        lambda payload: payload.update({"output_key": "tampered_public_sum"}),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_METRIC_OUTPUT_MISMATCH" in result["error_codes"]
    assert "REPLICATION_EXECUTION_ARTIFACT_HASH_MISMATCH" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["metric_script_executed"] is True
    assert metric["produced_output_payload"] == {
        "tampered_public_sum": 5,
        "row_count": 2,
    }
    assert metric["declared_output_matches_produced_output"] is False
    assert metric["declared_hash_matches_produced_output"] is False
    assert metric["metric_file_sha256"] == _sha256(
        bundle / "execution_artifacts/metrics/public_sum_metric.json"
    )
    assert metric["input_file_sha256"] == _sha256(
        bundle / "execution_artifacts/inputs/public_synthetic_table.json"
    )
    assert metric["declared_hash_file_sha256"] == _sha256(
        bundle / EXECUTION_ARTIFACT_HASH_REF
    )


def test_research_replication_rejects_replay_metric_script_ref_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        for row in payload["research_replays"]:
            row["metric_script_refs"] = [
                "execution_artifacts/metrics/tampered_metric.json"
            ]

    _mutate_json(bundle / "research_replays.json", mutate)

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_METRIC_REF_NOT_CITED" in result["error_codes"]
    assert "REPLICATION_EXECUTION_METRIC_REF_NOT_REPLAYED" in result["error_codes"]


def test_research_replication_rejects_replay_allowed_input_ref_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        for row in payload["research_replays"]:
            row["allowed_public_input_refs"] = [
                "execution_artifacts/inputs/tampered_input.json"
            ]

    _mutate_json(bundle / "research_replays.json", mutate)

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_INPUT_REF_NOT_CITED" in result["error_codes"]
    assert "REPLICATION_EXECUTION_INPUT_REF_NOT_REPLAYED" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["metric_script_executed"] is True
    assert metric["allowed_public_input_refs"] == [
        "execution_artifacts/inputs/public_synthetic_table.json"
    ]


def test_research_replication_rejects_manifest_unallowed_metric_input(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    _mutate_json(
        bundle / "execution_artifacts/execution_artifact_manifest.json",
        lambda payload: payload.update({"allowed_public_input_refs": []}),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_INPUT_NOT_ALLOWED" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["metric_script_executed"] is True
    assert metric["allowed_public_input_refs"] == []


def test_research_replication_rejects_input_perturbation(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    clean_result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay_clean",
        command="pytest",
    )
    clean_replay = clean_result["execution_artifact_replay"]

    assert clean_result["status"] == "pass"
    assert clean_result["replay_evidence_rung"] == "R3"
    assert clean_result["replay_evidence_state"] == "real_metric_hash_replay"
    assert clean_replay["evidence_rung"] == "R3"
    assert clean_replay["rung_evidence"]["rank_rederived_from"] == [
        "local_metric_script_execution",
        "allowed_public_input_body_hash",
        "metric_script_body_hash",
        "declared_output_artifact_hash",
    ]
    assert clean_replay["rung_evidence"]["metric_script_executed_count"] == 1

    def mutate(payload: dict[str, Any]) -> None:
        payload["rows"][1]["value"] = 4

    _mutate_json(
        bundle / "execution_artifacts/inputs/public_synthetic_table.json",
        mutate,
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert result["replay_evidence_rung"] == "R2"
    assert result["replay_evidence_state"] == "blocked_replay"
    assert "REPLICATION_EXECUTION_METRIC_OUTPUT_MISMATCH" in result["error_codes"]
    assert "REPLICATION_EXECUTION_ARTIFACT_HASH_MISMATCH" in result["error_codes"]
    replay = result["execution_artifact_replay"]
    assert replay["evidence_rung"] == "R2"
    assert replay["evidence_state"] == "blocked_replay"
    assert replay["rung_evidence"]["metric_script_executed_count"] == 1
    metric = replay["metric_results"][0]
    assert metric["metric_script_executed"] is True
    assert metric["produced_output_payload"] == {"public_sum": 6, "row_count": 2}
    assert metric["declared_output_matches_produced_output"] is False
    assert metric["declared_hash_matches_produced_output"] is False
    assert (
        metric["computed_output_canonical_sha256"]
        != metric["output_payload_canonical_sha256"]
    )


def test_research_replication_rejects_output_artifact_body_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    _mutate_json(
        bundle / EXECUTION_ARTIFACT_RESULT_REF,
        lambda payload: payload.update({"public_sum": 6}),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_METRIC_OUTPUT_MISMATCH" in result["error_codes"]
    assert "REPLICATION_EXECUTION_ARTIFACT_HASH_MISMATCH" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["produced_output_payload"] == {"public_sum": 5, "row_count": 2}
    assert metric["declared_output_matches_produced_output"] is False
    assert metric["declared_hash_matches_produced_output"] is True
    assert (
        metric["computed_output_canonical_sha256"]
        != metric["output_payload_canonical_sha256"]
    )
    assert metric["declared_output_file_sha256"] != metric["actual_output_file_sha256"]


def test_research_replication_rejects_output_artifact_baked_swap(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    output_path = bundle / EXECUTION_ARTIFACT_RESULT_REF
    hash_path = bundle / EXECUTION_ARTIFACT_HASH_REF
    _mutate_json(output_path, lambda payload: payload.update({"public_sum": 6}))
    _mutate_json(
        hash_path,
        lambda payload: payload.update({"sha256": _sha256(output_path)}),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert result["error_codes"] == [
        "REPLICATION_EXECUTION_ARTIFACT_HASH_MISMATCH",
        "REPLICATION_EXECUTION_METRIC_OUTPUT_MISMATCH",
    ]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["produced_output_payload"] == {"public_sum": 5, "row_count": 2}
    assert metric["declared_output_matches_produced_output"] is False
    assert metric["declared_hash_matches_produced_output"] is False
    assert (
        metric["computed_output_canonical_sha256"]
        != metric["output_payload_canonical_sha256"]
    )
    assert metric["declared_output_file_sha256"] == metric["actual_output_file_sha256"]


def test_research_replication_rejects_self_consistent_input_output_hash_rewrite(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    output_path = bundle / EXECUTION_ARTIFACT_RESULT_REF
    hash_path = bundle / EXECUTION_ARTIFACT_HASH_REF
    _mutate_json(
        bundle / EXECUTION_ARTIFACT_INPUT_REF,
        lambda payload: payload["rows"][1].update({"value": 4}),
    )
    _mutate_json(output_path, lambda payload: payload.update({"public_sum": 6}))
    _mutate_json(
        hash_path,
        lambda payload: payload.update({"sha256": _sha256(output_path)}),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_INPUT_BODY_HASH_MISMATCH" in result["error_codes"]
    metric = result["execution_artifact_replay"]["metric_results"][0]
    assert metric["produced_output_payload"] == {"public_sum": 6, "row_count": 2}
    assert metric["declared_output_matches_produced_output"] is True
    assert metric["declared_hash_matches_produced_output"] is True
    assert metric["input_body_hash_matches_declared"] is False


def test_research_replication_ignores_forged_negative_case_labels(
    tmp_path: Path,
) -> None:
    fixture_input = _copy_fixture_input(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        payload["original_author_code_reused"] = False
        payload["status"] = "blocked"
        payload["error_codes"] = ["REPLICATION_AUTHOR_CODE_REUSE_FORBIDDEN"]
        payload["expected_error_codes"] = [
            "REPLICATION_AUTHOR_CODE_REUSE_FORBIDDEN"
        ]

    _mutate_json(
        fixture_input / "original_author_code_reuse_forbidden.json",
        mutate,
    )

    result = run(
        fixture_input,
        tmp_path / "receipts/first_wave/research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "original_author_code_reuse_forbidden" in result["missing_negative_cases"]
    assert "original_author_code_reuse_forbidden" not in result["observed_negative_cases"]
    assert "REPLICATION_AUTHOR_CODE_REUSE_FORBIDDEN" not in result["error_codes"]
    basis = result["negative_case_verdict_basis"]
    assert basis["declared_fixture_labels_used"] is False
    label_case = next(
        row
        for row in basis["ignored_declared_label_cases"]
        if row["case_id"] == "original_author_code_reuse_forbidden"
    )
    assert set(label_case["ignored_keys"]) == {
        "error_codes",
        "expected_error_codes",
        "status",
    }


def test_research_replication_negative_case_id_follows_semantics_not_filename() -> None:
    payload = json.loads(
        (FIXTURE_INPUT / "research_replays.json").read_text(encoding="utf-8")
    )
    neutral_row = dict(payload["research_replays"][0])
    neutral_row["paper_id"] = "neutral_semantic_case"
    neutral_row["benchmark_performance_claim_authorized"] = True
    neutral_row["benchmark_score_claim"] = "forged-leaderboard-claim"

    result = validate_research_replays(
        payload,
        {"neutral_filename": neutral_row},
    )

    assert result["status"] == "pass"
    assert result["observed_negative_cases"] == {
        "benchmark_performance_claim": [
            "REPLICATION_BENCHMARK_PERFORMANCE_OVERCLAIM"
        ]
    }
    finding = result["findings"][0]
    assert finding["negative_case_id"] == "benchmark_performance_claim"
    assert finding["subject_id"] == "neutral_semantic_case"
    assert result["negative_case_verdict_basis"]["coverage_case_id_source"] == (
        "derived_error_code_semantics_not_fixture_filename"
    )


def test_research_replication_rejects_metadata_only_bundle(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    shutil.rmtree(bundle / "execution_artifacts")

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["execution_artifact_replay_status"] == "blocked"
    assert "REPLICATION_EXECUTION_ARTIFACT_MANIFEST_MISSING" in result["error_codes"]


def test_research_replication_secret_scan_covers_execution_artifact_bodies(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    _mutate_json(
        bundle / "execution_artifacts/inputs/public_synthetic_table.json",
        lambda payload: payload.update(
            {"provider_payload": "SYNTHETIC_PROVIDER_PAYLOAD_BODY_SENTINEL"}
        ),
    )

    result = run_replication_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is True
    assert result["secret_exclusion_scan"]["blocking_hit_count"] > 0
    assert any(
        hit["path"].endswith("execution_artifacts/inputs/public_synthetic_table.json")
        for hit in result["secret_exclusion_scan"]["hits"]
    )


def test_research_replication_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay"
    )
    args = [
        "run-replication-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 18
    assert first_card["research_replication"]["paper_count"] == 2
    assert first_card["research_replication"]["replay_count"] == 2
    assert first_card["research_replication"]["declared_artifact_hash_ref_count"] == 1
    assert first_card["execution_artifact_replay"]["status"] == "pass"
    assert first_card["execution_artifact_replay"]["verdict_source"] == (
        "local_metric_script_execution_over_allowed_public_inputs"
    )
    assert first_card["execution_artifact_replay"]["evidence_rung"] == "R3"
    assert first_card["execution_artifact_replay"]["evidence_state"] == (
        "real_metric_hash_replay"
    )
    assert first_card["execution_artifact_replay"]["hash_verification_basis"] == (
        "input_metric_body_hash_refs_plus_output_artifact_ref_and_sha256"
    )
    assert (
        first_card["execution_artifact_replay"]["declared_fixture_labels_used"]
        is False
    )
    assert first_card["execution_artifact_replay"]["metric_count"] == 1
    assert first_card["execution_artifact_replay"]["computed_output_count"] == 1
    assert first_card["public_agent_execution_trace"]["span_count"] == 2
    assert first_card["source_body_floor"]["status"] == "pass"
    assert first_card["source_body_floor"]["body_material_count"] == len(
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )
    assert first_card["source_body_floor"]["body_material_id_count"] == len(
        RESEARCH_REPLICATION_SOURCE_MODULE_IDS
    )
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["semantic_negative_case_evaluator_used"] is False
    assert first_card["validation"]["declared_fixture_labels_used"] is False
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "body_material_ids" not in _walk_keys(first_card)
    assert "metric_results" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "research_replays" not in _walk_keys(first_card)
    assert "declared_artifact_hash_refs" not in _walk_keys(first_card)
    assert "spans" not in _walk_keys(first_card)
    assert "private_paper_body" not in _walk_keys(first_card)
    assert "hidden_rubric_body" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        research_replication_rubric_artifact_replay,
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


def test_research_replication_bundle_card_rejects_stale_receipt_after_input_mutation(
    tmp_path: Path,
    capsys: Any,
) -> None:
    bundle = _copy_bundle(tmp_path)
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay"
    )
    args = [
        "run-replication-bundle",
        "--input",
        str(bundle),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False

    _mutate_json(
        bundle / "execution_artifacts/inputs/public_synthetic_table.json",
        lambda payload: payload["rows"][1].update({"value": 4}),
    )

    assert main(args) == 1
    mutated_card = json.loads(capsys.readouterr().out)
    assert mutated_card["status"] == "blocked"
    assert mutated_card["command_speed"]["receipt_reused"] is False
    assert mutated_card["command_speed"]["freshness_digest"] != (
        first_card["command_speed"]["freshness_digest"]
    )
    result = json.loads(
        (
            out
            / "exported_research_replication_bundle_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert "REPLICATION_EXECUTION_METRIC_OUTPUT_MISMATCH" in result["error_codes"]
    assert "REPLICATION_EXECUTION_ARTIFACT_HASH_MISMATCH" in result["error_codes"]


def test_public_agent_execution_trace_refactor_builds_research_replay_spans() -> None:
    trace = build_public_research_replication_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert trace["bundle_id"] == "research_replication_rubric_artifact_replay_runtime_example"
    assert trace["span_count"] == 2
    assert trace["summary"]["action_kind_counts"] == {
        "research_replication_artifact_replay": 2
    }
    assert trace["summary"]["outcome_counts"] == {"success": 2}
    assert {
        span["tool_name"] for span in trace["spans"]
    } == {"research_replication_replay"}
    assert trace["audit"]["coverage"]["rubric_tree_coverage"] is True
    assert trace["audit"]["coverage"]["declared_artifact_hash_roster_coverage"] is True
    assert trace["audit"]["coverage"]["metric_script_coverage"] is True
    assert trace["audit"]["coverage"]["grader_report_coverage"] is True
    assert trace["audit"]["coverage"]["budget_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["failure_taxonomy_coverage"] is True
    assert trace["audit"]["coverage"]["cold_rerun_coverage"] is True
    assert "system/lib/agent_execution_trace.py" in trace["source_refs"]
