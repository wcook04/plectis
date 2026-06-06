from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import microcosm_core.organs.batch4_proof_authority_runtime as batch4_runtime
from microcosm_core.organs.batch4_proof_authority_runtime import (
    AUTHORITY_CEILING,
    EXPECTED_MECHANISMS,
    EXPECTED_MODULE_IDS,
    EXPECTED_NEGATIVE_CASES,
    NEGATIVE_CASE_OVERCLAIM_SHAPES,
    NEGATIVE_CASE_RUNTIME_PROBES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch4_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch4_proof_authority_runtime/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch4_proof_authority_runtime/exported_batch4_proof_authority_runtime_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"

EXPECTED_NEGATIVE_CASES_LITERAL = {
    "weak_skeleton_synthesis_failure": (
        "BATCH4_WEAK_SKELETON_MUST_NOT_SILENT_PASS",
    ),
    "foundry_low_repair_quarantine": (
        "BATCH4_FOUNDRY_REPAIRED_COUNT_BELOW_THRESHOLD",
    ),
    "verisoft_truth_leak": (
        "BATCH4_VERISOFT_TRUTH_LEAK_REJECTED",
    ),
    "verisoft_prefix_answer_leakage": (
        "BATCH4_VERISOFT_PREFIX_ANSWER_LEAKAGE_REJECTED",
    ),
    "erdos_solution_overclaim": (
        "BATCH4_ERDOS257_SOLUTION_OVERCLAIM_REJECTED",
    ),
    "packet_sha256_corruption": (
        "BATCH4_PACKET_SHA256_CORRUPTION_REJECTED",
    ),
    "grant_forbidden_context": (
        "BATCH4_GRANT_FORBIDDEN_CONTEXT_DENIED",
    ),
    "forward_dirty_unknown_target": (
        "BATCH4_FORWARD_POLICY_DIRTY_UNKNOWN_TARGET_BLOCKED",
    ),
    "closeout_stale_head": (
        "BATCH4_CLOSEOUT_STALE_HEAD_DEFERS",
    ),
    "codex_driver_absent_port": (
        "BATCH4_CODEX_DRIVER_ABSENT_PORT_TYPED_UNREACHABLE",
    ),
    "idle_stale_snapshot": (
        "BATCH4_IDLE_HEARTBEAT_STALE_SNAPSHOT_REJECTED",
    ),
    "bitemporal_expired_claim": (
        "BATCH4_BITEMPORAL_EXPIRED_CLAIM_NOT_CURRENT",
    ),
    "taskpolicy_missing_binary": (
        "BATCH4_TASKPOLICY_UNAVAILABLE_PASSTHROUGH",
    ),
    "context_accepted_read_guard": (
        "BATCH4_CONTEXT_ACCEPTED_SCOPED_READ_NOT_FLAGGED",
    ),
}

EXPECTED_MECHANISM_NEGATIVE_CASES_LITERAL = {
    "lean_strategy_control_benchmark": "weak_skeleton_synthesis_failure",
    "prover_skill_foundry": "foundry_low_repair_quarantine",
    "verisoftbench_harness_differential": "verisoft_truth_leak",
    "verisoftbench_calibration_executor": "verisoft_prefix_answer_leakage",
    "erdos257_certificate_kernel": "erdos_solution_overclaim",
    "lean_full_fidelity_packet_verifier": "packet_sha256_corruption",
    "reasoning_execution_authority_grant": "grant_forbidden_context",
    "forward_integration_policy_fence": "forward_dirty_unknown_target",
    "closeout_executor_state_machine": "closeout_stale_head",
    "codex_cdp_driver": "codex_driver_absent_port",
    "codex_idle_heartbeat_fsm": "idle_stale_snapshot",
    "metabolism_bitemporal_claim_log": "bitemporal_expired_claim",
    "macos_taskpolicy_actuator": "taskpolicy_missing_binary",
    "context_yield_attribution": "context_accepted_read_guard",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    if public_root.exists():
        shutil.rmtree(public_root)
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch4_proof_authority_runtime",
        public_root / "examples/batch4_proof_authority_runtime",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch4_proof_authority_runtime",
        public_root / "fixtures/first_wave/batch4_proof_authority_runtime",
    )
    return public_root / "fixtures/first_wave/batch4_proof_authority_runtime/input"


def _bundle_for_fixture(fixture: Path) -> Path:
    return (
        fixture.parents[3]
        / "examples/batch4_proof_authority_runtime/exported_batch4_proof_authority_runtime_bundle"
    )


def _module_path(bundle: Path, module_id: str) -> Path:
    manifest = json.loads((bundle / "source_module_manifest.json").read_text(encoding="utf-8"))
    row = next(item for item in manifest["modules"] if item["module_id"] == module_id)
    return bundle / row["path"]


def _install_fake_source_lake_project(public_root: Path) -> None:
    project = public_root.parent / "formal_math/erdos257_period_noncollapse"
    project.mkdir(parents=True, exist_ok=True)
    (project / "lakefile.toml").write_text(
        'name = "Erdos257PeriodNoncollapse"\n', encoding="utf-8"
    )
    (project / "lean-toolchain").write_text(
        "leanprover/lean4:v4.29.1\n", encoding="utf-8"
    )


def _fake_command_result(status: str = "pass") -> dict[str, Any]:
    return {
        "status": status,
        "return_code": 0 if status == "pass" else 1,
        "timed_out": False,
        "stdout_line_count": 0,
        "stderr_line_count": 1 if status == "blocked" else 0,
        "combined_output": "",
        "error_class": None if status == "pass" else "nonzero_exit_redacted",
    }


@pytest.fixture(autouse=True)
def _clear_batch4_probe_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    batch4_runtime._LEAN_LAKE_PROBE_CACHE.clear()
    monkeypatch.setattr(
        batch4_runtime,
        "_run_command",
        lambda *args, **kwargs: {
            "status": "unavailable",
            "return_code": None,
            "timed_out": False,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "combined_output": "",
            "error_class": "test_default_probe_unavailable",
        },
    )
    yield
    batch4_runtime._LEAN_LAKE_PROBE_CACHE.clear()


def test_batch4_proof_authority_runtime_runs_all_mechanisms(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch4_proof_authority_runtime",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch4_proof_authority_runtime_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    assert (
        result["exercise"]["semantic_negative_case_computed_rejection_count"]
        == len(EXPECTED_NEGATIVE_CASES)
    )
    assert all(
        row["computed_rejection"] is True
        for row in result["exercise"]["semantic_negative_case_proofs"]
    )
    assert all(
        row["overclaim_shape"]["status"] == "pass"
        for row in result["exercise"]["semantic_negative_case_proofs"]
    )

    exercise = result["exercise"]
    assert exercise["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert {row["mechanism_id"] for row in exercise["mechanisms"]} == set(EXPECTED_MECHANISMS)
    assert {
        row["mechanism_id"]: row["negative_case"]
        for row in exercise["mechanisms"]
    } == EXPECTED_MECHANISM_NEGATIVE_CASES_LITERAL
    assert all(row["status"] == "pass" for row in exercise["mechanisms"])
    assert exercise["runtime_exercises"]["proof_bundle"]["status"] == "pass"
    assert exercise["runtime_exercises"]["proof_bundle"]["erdos_static_scan"]["status"] == "pass"
    lean_lake_probe = exercise["runtime_exercises"]["proof_bundle"]["lean_lake_probe"]
    assert lean_lake_probe["status"] in {"pass", "unavailable"}
    assert lean_lake_probe["probe_class"] == "optional_local_toolchain_probe"
    assert lean_lake_probe["input_scope"] == "copied_public_certificate_kernel_only"
    assert lean_lake_probe["proof_authority_class"] == (
        "non_authoritative_runtime_availability_signal"
    )
    assert lean_lake_probe["compile_boundary_status"] in {
        "live_compile_pass",
        "recorded_probe_unavailable",
    }
    assert lean_lake_probe["compile_boundary_realness_level"] in {
        "r3_live_compile_probe_boundary",
        "r3_recorded_probe_dependency_boundary",
    }
    assert (
        lean_lake_probe["compile_boundary_load_bearing"]
        is (lean_lake_probe["status"] == "pass")
    )
    assert lean_lake_probe["stdout_stderr_in_receipt"] is False
    assert lean_lake_probe["body_in_receipt"] is False
    assert exercise["runtime_exercises"]["proof_bundle"]["proof_authority_delta"] == "none"
    assert exercise["runtime_exercises"]["proof_bundle"][
        "lean_lake_compile_boundary_status"
    ] == lean_lake_probe["compile_boundary_status"]
    assert exercise["runtime_exercises"]["authority_bundle"]["launch_authorized"] is False
    assert exercise["runtime_exercises"]["authority_bundle"]["model_dispatch"] is False
    assert exercise["runtime_exercises"]["authority_bundle"]["runtime_execution"] is False
    assert exercise["runtime_exercises"]["runtime_bundle"]["taskpolicy_unavailable_passthrough"] is True
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["body_in_receipt"] is False


def test_batch4_proof_authority_runtime_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_batch4_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch4_proof_authority_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch4_proof_authority_runtime_bundle"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["exercise"]["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch4_lean_lake_probe_good_witness_is_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(batch4_runtime.shutil, "which", lambda name: f"/redacted/{name}")
    monkeypatch.setattr(batch4_runtime, "_run_command", lambda *args, **kwargs: _fake_command_result())

    result = run_batch4_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch4_probe_good",
        command="pytest",
    )

    probe = result["exercise"]["runtime_exercises"]["proof_bundle"]["lean_lake_probe"]
    assert result["status"] == "pass"
    assert probe["status"] == "pass"
    assert probe["command"] == [
        "lake",
        "env",
        "lean",
        "examples/batch4_proof_authority_runtime/exported_batch4_proof_authority_runtime_bundle/source_modules/formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/CertificateKernel.lean",
    ]
    assert probe["return_code"] == 0
    assert probe["stdout_stderr_in_receipt"] is False
    assert "stdout" not in probe
    assert "stderr" not in probe
    assert probe["compile_boundary_status"] == "live_compile_pass"
    assert probe["compile_boundary_realness_level"] == "r3_live_compile_probe_boundary"
    assert probe["compile_boundary_load_bearing"] is True
    assert probe["compile_boundary_load_bearing_for"] == (
        "copied_certificate_kernel_zero_exit_elaboration"
    )
    assert "not theorem correctness" in probe["compile_boundary_claim"]
    assert "not a solution" in probe["compile_boundary_claim"]
    assert probe["proof_authority_delta"] == "none"
    assert probe["source_lake_project_ref"] == "formal_math/erdos257_period_noncollapse"
    assert probe["proof_authority_delta"] == "none"
    assert probe["authority_delta"] == "none"


def test_batch4_lean_lake_probe_unavailable_is_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        batch4_runtime.shutil,
        "which",
        lambda name: None if name == "lake" else f"/redacted/{name}",
    )

    result = run_batch4_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch4_probe_unavailable",
        command="pytest",
    )

    probe = result["exercise"]["runtime_exercises"]["proof_bundle"]["lean_lake_probe"]
    assert result["status"] == "pass"
    assert probe["status"] == "unavailable"
    assert probe["error_class"] == "lake_unavailable"
    assert probe["tool_versions"]["lean_available"] is True
    assert probe["tool_versions"]["lake_available"] is False
    assert probe["compile_boundary_status"] == "recorded_probe_unavailable"
    assert probe["compile_boundary_realness_level"] == (
        "r3_recorded_probe_dependency_boundary"
    )
    assert probe["compile_boundary_load_bearing"] is False
    assert probe["proof_authority_delta"] == "none"


def test_batch4_lean_lake_probe_blocks_real_nonzero_compile_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch4_proof_authority_runtime",
        public_root / "examples/batch4_proof_authority_runtime",
    )
    bundle = (
        public_root
        / "examples/batch4_proof_authority_runtime/exported_batch4_proof_authority_runtime_bundle"
    )
    _install_fake_source_lake_project(public_root)
    kernel_path = _module_path(bundle, "erdos257_certificate_kernel")
    kernel_path.write_text(
        kernel_path.read_text(encoding="utf-8").replace(
            "theorem no_prime_drop_implies_eq",
            "theorem no_prime_drop_implies_zz",
            1,
        ),
        encoding="utf-8",
    )

    def fake_run(argv: list[str], *, cwd: Path, timeout_seconds: int = 20) -> dict[str, Any]:
        copied_text = Path(argv[-1]).read_text(encoding="utf-8")
        return _fake_command_result(
            "blocked"
            if "theorem no_prime_drop_implies_zz" in copied_text
            else "pass"
        )

    monkeypatch.setattr(batch4_runtime.shutil, "which", lambda name: f"/redacted/{name}")
    monkeypatch.setattr(batch4_runtime, "_run_command", fake_run)

    result = run_batch4_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/batch4_probe_bad",
        command="pytest",
    )

    proof_bundle = result["exercise"]["runtime_exercises"]["proof_bundle"]
    probe = proof_bundle["lean_lake_probe"]
    assert result["status"] == "blocked"
    assert proof_bundle["status"] == "blocked"
    assert probe["status"] == "blocked"
    assert probe["error_class"] == "nonzero_exit_redacted"
    assert probe["compile_boundary_status"] == "live_compile_reject"
    assert probe["compile_boundary_realness_level"] == "r3_live_compile_failure_boundary"
    assert probe["compile_boundary_load_bearing"] is True
    assert probe["compile_boundary_load_bearing_for"] == (
        "copied_certificate_kernel_nonzero_exit_blocks_acceptance"
    )
    assert proof_bundle["lean_lake_compile_boundary_status"] == "live_compile_reject"
    assert proof_bundle["erdos_static_scan"]["status"] == "pass"
    assert "BATCH4_LEAN_LAKE_PROBE_FAILED" in result["error_codes"]


def test_batch4_proof_authority_runtime_rejects_source_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch4_proof_authority_runtime",
        public_root / "examples/batch4_proof_authority_runtime",
    )
    bundle = (
        public_root
        / "examples/batch4_proof_authority_runtime/exported_batch4_proof_authority_runtime_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_id = manifest["modules"][0]["module_id"]
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch4_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/batch4_proof_authority_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["modules"][0]["digest_status"] == "mismatch"
    assert result["source_module_manifest"]["modules"][0]["source_ref"]
    assert module_id in {row["module_id"] for row in manifest["modules"]}
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_batch4_proof_authority_runtime_rejects_mutated_copied_module_body_digest_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    public_root = fixture.parents[3]
    bundle = _bundle_for_fixture(fixture)
    module_path = _module_path(bundle, "prover_graph_benchmark")
    original_text = module_path.read_text(encoding="utf-8")
    original_token = "PROVER_BENCHMARK_20260510_graph_harness_v0"
    mutated_token = "PROVER_BENCHMARK_20260510_graph_harness_x0"
    assert original_token in original_text
    module_path.write_text(
        original_text.replace(original_token, mutated_token, 1),
        encoding="utf-8",
    )

    result = run_batch4_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch4_proof_authority_runtime/body_digest",
        command="pytest",
    )

    module_receipt = next(
        row
        for row in result["source_module_manifest"]["modules"]
        if row["module_id"] == "prover_graph_benchmark"
    )
    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_LINE_COUNT_MISMATCH" not in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_ANCHOR_MISSING" not in result["error_codes"]
    assert module_receipt["digest_status"] == "mismatch"
    assert module_receipt["line_count_status"] == "match"
    assert module_receipt["missing_required_anchors"] == []
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


@pytest.mark.parametrize("placeholder", ("sorry", "admit", "axiom"))
def test_batch4_proof_authority_runtime_rejects_each_mutated_lean_placeholder_token(
    tmp_path: Path,
    placeholder: str,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch4_proof_authority_runtime",
        public_root / "examples/batch4_proof_authority_runtime",
    )
    bundle = (
        public_root
        / "examples/batch4_proof_authority_runtime/exported_batch4_proof_authority_runtime_bundle"
    )
    manifest = json.loads((bundle / "source_module_manifest.json").read_text(encoding="utf-8"))
    kernel_row = next(
        row for row in manifest["modules"] if row["module_id"] == "erdos257_certificate_kernel"
    )
    kernel_path = bundle / kernel_row["path"]
    kernel_path.write_text(
        kernel_path.read_text(encoding="utf-8")
        + f"\n{placeholder} batch4_mutation_test_placeholder\n",
        encoding="utf-8",
    )

    result = run_batch4_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/batch4_proof_authority_runtime",
        command="pytest",
    )

    erdos_scan = result["exercise"]["runtime_exercises"]["proof_bundle"]["erdos_static_scan"]
    proof_pressure = result["exercise"]["runtime_exercises"]["proof_bundle"][
        "copied_proof_source_pressure"
    ]
    assert result["status"] == "blocked"
    assert result["exercise"]["runtime_exercises"]["proof_bundle"]["status"] == "blocked"
    assert proof_pressure["status"] == "blocked"
    assert erdos_scan["status"] == "blocked"
    assert erdos_scan["banned_token_hits"] == [placeholder]
    assert "BATCH4_ERDOS_STATIC_TOKEN_SCAN_FAILED" in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_LINE_COUNT_MISMATCH" in result["error_codes"]
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_batch4_proof_authority_runtime_rejects_corrupted_lean_body_without_placeholder_token(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch4_proof_authority_runtime",
        public_root / "examples/batch4_proof_authority_runtime",
    )
    bundle = (
        public_root
        / "examples/batch4_proof_authority_runtime/exported_batch4_proof_authority_runtime_bundle"
    )
    manifest = json.loads((bundle / "source_module_manifest.json").read_text(encoding="utf-8"))
    kernel_row = next(
        row for row in manifest["modules"] if row["module_id"] == "erdos257_certificate_kernel"
    )
    kernel_path = bundle / kernel_row["path"]
    kernel_text = kernel_path.read_text(encoding="utf-8")
    kernel_path.write_text(
        kernel_text.replace(
            "theorem no_prime_drop_implies_eq",
            "theorem no_prime_drop_implies_zz",
            1,
        ),
        encoding="utf-8",
    )

    result = run_batch4_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/batch4_proof_authority_runtime",
        command="pytest",
    )

    proof_bundle = result["exercise"]["runtime_exercises"]["proof_bundle"]
    erdos_scan = proof_bundle["erdos_static_scan"]
    proof_pressure = proof_bundle["copied_proof_source_pressure"]
    kernel_receipt = next(
        row
        for row in result["source_module_manifest"]["modules"]
        if row["source_ref"].endswith("Erdos257PeriodNoncollapse/CertificateKernel.lean")
    )
    assert result["status"] == "blocked"
    assert proof_bundle["status"] == "blocked"
    assert proof_pressure["status"] == "blocked"
    assert "theorem no_prime_drop_implies_eq" in proof_pressure["missing_required_anchors"]
    assert erdos_scan["status"] == "pass"
    assert erdos_scan["banned_token_hits"] == []
    assert "BATCH4_ERDOS_STATIC_TOKEN_SCAN_FAILED" not in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_ANCHOR_MISSING" in result["error_codes"]
    assert result["source_module_manifest"]["status"] == "blocked"
    assert kernel_receipt["digest_status"] == "mismatch"
    assert "theorem no_prime_drop_implies_eq" in kernel_receipt[
        "missing_required_anchors"
    ]
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_batch4_proof_authority_runtime_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == len(EXPECTED_MODULE_IDS)
    assert manifest["body_in_receipt"] is False
    assert {row["module_id"] for row in manifest["modules"]} == set(EXPECTED_MODULE_IDS)

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        assert row["source_to_target_relation"] == "exact_copy"
        assert row["body_copied"] is True
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        assert row["body_text_in_receipt"] is False
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])
        if row["module_id"] == "erdos257_certificate_kernel":
            assert row["material_class"] == "public_macro_proof_body"


def test_batch4_proof_authority_runtime_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch4_proof_authority_runtime",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert card["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert card["authority_ceiling"] == AUTHORITY_CEILING
    assert card["authority_ceiling"]["proof_authority_delta"] == "none"
    assert card["authority_ceiling"]["publication_authorized"] is False
    assert card["authority_ceiling"]["release_authorized"] is False
    assert card["authority_ceiling"]["runtime_execution"] is False
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "proof_body" not in _walk_keys(result)


def test_batch4_proof_authority_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    assert EXPECTED_NEGATIVE_CASES == EXPECTED_NEGATIVE_CASES_LITERAL
    assert set(NEGATIVE_CASE_RUNTIME_PROBES) == set(EXPECTED_NEGATIVE_CASES)

    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        payload["verdict"] = "reject"
        payload["realness_rank"] = "R3"
        payload["realness_rung"] = "baked_fixture_label"
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3]
        / "receipts/first_wave/batch4_proof_authority_runtime",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    semantics = {row["case_id"]: row for row in result["negative_case_semantics"]}
    proof_rows = {
        row["case_id"]: row
        for row in result["exercise"]["semantic_negative_case_proofs"]
    }
    assert set(semantics) == set(EXPECTED_NEGATIVE_CASES_LITERAL)
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES_LITERAL.items():
        assert semantics[case_id]["status"] == "blocked"
        assert semantics[case_id]["error_codes"] == list(expected_codes)
        assert proof_rows[case_id]["realness_rank"] == "R3"
        assert proof_rows[case_id]["realness_rung"] == "derived_runtime_negative_verdict"
        assert proof_rows[case_id]["negative_case_verdict"] == "computed_reject"
        assert proof_rows[case_id]["rejection_basis"] == (
            "computed_runtime_case_observer_and_fixture_probe"
        )
        assert proof_rows[case_id]["verdict_signature_source"] == (
            "derived_runtime_case_overclaim_shape_and_source_probe"
        )
        assert proof_rows[case_id]["fixture_runtime_probe"]["status"] == "pass"
        assert proof_rows[case_id]["rank_rung_evidence_rederived"] is True
        assert len(proof_rows[case_id]["verdict_signature"]) == 64
        assert "BOGUS_DECLARED_ERROR" not in semantics[case_id]["error_codes"]
        for code in expected_codes:
            assert code in result["error_codes"]
        direct = evaluate_negative_case(case_id, fixture, ("BOGUS_DECLARED_ERROR",))
        assert direct["status"] == "blocked"
        assert direct["realness_rank"] == "R3"
        assert direct["realness_rung"] == "derived_runtime_negative_verdict"
        assert direct["negative_case_verdict"] == "computed_reject"
        assert direct["expected_codes_input_used"] is False
        assert direct["declared_fixture_error_codes_used"] is False
        assert direct["stable_codes_source"] == (
            "batch4_runtime_semantic_map_gated_by_derived_verdict_signature"
        )
        assert direct["evidence"]["fixture_runtime_probe"]["status"] == "pass"
        assert direct["evidence"]["fixture_runtime_probe"][
            "source_text_check_uses_fixture_required_text"
        ] is False
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch4_old_baked_negative_fixtures_without_runtime_probes_fail(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload.pop("runtime_probe", None)
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(fixture, fixture.parents[3] / "receipts/batch4_old_baked")

    assert result["status"] == "blocked"
    assert result["observed_negative_cases"] == []
    assert set(result["missing_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in result["error_codes"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in result["error_codes"]
    assert all(row["status"] == "pass" for row in result["negative_case_semantics"])


def test_batch4_negative_fixture_runtime_probe_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    case_path = fixture / "grant_forbidden_context.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["runtime_probe"]["required_text"] = "benign_context_only"
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    direct = evaluate_negative_case(
        "grant_forbidden_context",
        fixture,
        EXPECTED_NEGATIVE_CASES["grant_forbidden_context"],
    )
    result = run(fixture, fixture.parents[3] / "receipts/batch4_bad_probe")
    proof_rows = {
        row["case_id"]: row
        for row in result["exercise"]["semantic_negative_case_proofs"]
    }

    assert direct["status"] == "pass"
    assert direct["observed"]["fixture_runtime_probe"]["status"] == "blocked"
    assert direct["observed"]["fixture_runtime_probe"]["checks"]["required_text_matches"] is False
    assert result["status"] == "blocked"
    assert "grant_forbidden_context" in result["missing_negative_cases"]
    assert proof_rows["grant_forbidden_context"]["computed_rejection"] is False
    assert proof_rows["grant_forbidden_context"]["negative_case_verdict"] == "not_rejected"
    assert proof_rows["grant_forbidden_context"]["realness_rank"] == "below_r3"
    assert proof_rows["grant_forbidden_context"]["fixture_runtime_probe"]["status"] == "blocked"
    assert proof_rows["grant_forbidden_context"]["fixture_runtime_probe"]["checks"][
        "required_text_matches"
    ] is False


def test_batch4_fixture_runtime_probe_cannot_choose_wrong_source_anchor(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    case_path = fixture / "grant_forbidden_context.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["runtime_probe"] = {
        "observer_id": "grant_denial_no_dispatch",
        "source_module_id": "forward_integration_policy",
        "required_text": "dirty_unknown_target",
    }
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    direct = evaluate_negative_case(
        "grant_forbidden_context",
        fixture,
        EXPECTED_NEGATIVE_CASES["grant_forbidden_context"],
    )

    assert direct["status"] == "pass"
    assert direct["error_codes"] == []
    probe = direct["observed"]["fixture_runtime_probe"]
    assert probe["source_module_id"] == "forward_integration_policy"
    assert probe["derived_source_module_id"] == "reasoning_grant_lease"
    assert probe["checks"]["source_module_id_matches"] is False
    assert probe["checks"]["required_text_matches"] is False
    assert probe["checks"]["required_text_present"] is True
    assert probe["source_text_check_uses_fixture_required_text"] is False
    assert direct["realness_rank"] == "below_r3"
    assert direct["realness_rung"] == "negative_case_not_rejected"
    assert direct["negative_case_verdict"] == "not_rejected"


def test_batch4_proof_authority_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        assert result["source_backed"] is True
        assert result["declared_fixture_ignored"] is True
        assert result["declared_fixture_error_codes_used"] is False
        assert result["expected_codes_input_used"] is False
        assert result["fixture_payload_used"] == "runtime_probe_only"
        assert result["stable_codes_source"] == (
            "batch4_runtime_semantic_map_gated_by_derived_verdict_signature"
        )
        assert result["rejection_basis"] == "computed_runtime_case_observer_and_fixture_probe"
        assert result["realness_rank"] == "R3"
        assert result["realness_rung"] == "derived_runtime_negative_verdict"
        assert result["negative_case_verdict"] == "computed_reject"
        assert result["rank_rung_evidence_rederived"] is True
        assert len(result["verdict_signature"]) == 64
        assert result["evidence"]["runtime_case"]["computed"] is True
        assert result["evidence"]["runtime_case"]["observer_id"] == (
            NEGATIVE_CASE_RUNTIME_PROBES[case_id]["observer_id"]
        )
        assert result["evidence"]["overclaim_shape"]["status"] == "pass"
        assert result["evidence"]["overclaim_shape"]["observer_id"] == (
            "bounded_overclaim_shape"
        )
        assert result["evidence"]["fixture_runtime_probe"]["status"] == "pass"
        for code in expected_codes:
            assert code in result["error_codes"]


@pytest.mark.parametrize("case_id", sorted(EXPECTED_NEGATIVE_CASES))
def test_batch4_proof_authority_ignores_injected_expected_error_code_labels(
    case_id: str,
) -> None:
    result = evaluate_negative_case(
        case_id,
        FIXTURE_INPUT,
        ("BOGUS_STATIC_EXPECTED_LABEL",),
    )

    assert result["status"] == "blocked"
    assert result["error_codes"] == list(EXPECTED_NEGATIVE_CASES[case_id])
    assert result["expected_codes_input_ignored"] is True
    assert result["expected_codes_input_used"] is False
    assert "BOGUS_STATIC_EXPECTED_LABEL" not in result["error_codes"]
    assert result["evidence"]["runtime_case"]["computed"] is True
    assert result["evidence"]["fixture_runtime_probe"]["status"] == "pass"


@pytest.mark.parametrize("case_id", sorted(EXPECTED_NEGATIVE_CASES))
def test_batch4_stable_error_codes_ignore_expected_codes_input_order_and_content(
    case_id: str,
) -> None:
    result = evaluate_negative_case(
        case_id,
        FIXTURE_INPUT,
        ("BOGUS_STATIC_EXPECTED_LABEL", *reversed(EXPECTED_NEGATIVE_CASES[case_id])),
    )

    assert result["status"] == "blocked"
    assert result["error_codes"] == list(EXPECTED_NEGATIVE_CASES[case_id])
    assert result["expected_codes_input_used"] is False
    assert result["expected_codes_input_ignored"] is True


def test_batch4_context_accepted_read_guard_tracks_copied_runtime_source(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    bundle = _bundle_for_fixture(fixture)
    manifest = json.loads((bundle / "source_module_manifest.json").read_text(encoding="utf-8"))
    trace_row = next(
        row for row in manifest["modules"] if row["module_id"] == "agent_execution_trace"
    )
    trace_path = bundle / trace_row["path"]
    trace_path.write_text(
        trace_path.read_text(encoding="utf-8").replace("scoped_diff_paths", "scope_diff_paths"),
        encoding="utf-8",
    )

    result = evaluate_negative_case(
        "context_accepted_read_guard",
        fixture,
        EXPECTED_NEGATIVE_CASES["context_accepted_read_guard"],
    )

    assert result["status"] == "pass"
    assert result["error_codes"] == []
    assert result["observed"]["runtime_case"]["computed"] is False
    assert result["observed"]["runtime_case"]["observed"][
        "context_yield_attribution_present"
    ] is True
    assert result["observed"]["runtime_case"]["observed"][
        "accepted_scoped_read_guard"
    ] is False


def test_batch4_forward_policy_observer_tracks_copied_runtime_source(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    bundle = _bundle_for_fixture(fixture)
    forward_path = _module_path(bundle, "forward_integration_policy")
    forward_path.write_text(
        forward_path.read_text(encoding="utf-8").replace(
            "dirty_unknown_target",
            "clean_known_target",
            1,
        ),
        encoding="utf-8",
    )

    result = evaluate_negative_case(
        "forward_dirty_unknown_target",
        fixture,
        EXPECTED_NEGATIVE_CASES["forward_dirty_unknown_target"],
    )

    assert result["status"] == "pass"
    assert result["error_codes"] == []
    assert result["observed"]["runtime_case"]["computed"] is False
    assert result["observed"]["runtime_case"]["observer_id"] == (
        "forward_dirty_unknown_target_policy_anchor"
    )
    assert result["observed"]["runtime_case"]["observed"][
        "forward_dirty_unknown_target_blocks"
    ] is False
    assert result["observed"]["fixture_runtime_probe"]["status"] == "blocked"
    assert result["observed"]["fixture_runtime_probe"]["checks"][
        "required_text_present"
    ] is False


@pytest.mark.parametrize("case_id", sorted(EXPECTED_NEGATIVE_CASES))
def test_batch4_each_negative_case_tracks_mutated_copied_runtime_source(
    tmp_path: Path,
    case_id: str,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    bundle = _bundle_for_fixture(fixture)
    probe = NEGATIVE_CASE_RUNTIME_PROBES[case_id]
    module_path = _module_path(bundle, probe["source_module_id"])
    original_text = module_path.read_text(encoding="utf-8")
    assert probe["required_text"] in original_text
    if case_id == "erdos_solution_overclaim":
        module_path.write_text(
            original_text + "\naxiom batch4_mutated_runtime_observer : True\n",
            encoding="utf-8",
        )
    else:
        module_path.write_text(
            original_text.replace(probe["required_text"], "batch4_mutated_anchor"),
            encoding="utf-8",
        )

    result = evaluate_negative_case(
        case_id,
        fixture,
        EXPECTED_NEGATIVE_CASES[case_id],
    )

    assert result["status"] == "pass"
    assert result["error_codes"] == []
    assert result["observed"]["runtime_case"]["computed"] is False
    assert result["observed"]["runtime_case"]["observer_id"] == probe["observer_id"]
    if case_id == "erdos_solution_overclaim":
        assert result["observed"]["runtime_case"]["observed"][
            "erdos_static_scan_status"
        ] == "blocked"
        assert result["observed"]["fixture_runtime_probe"]["status"] == "pass"
    else:
        assert result["observed"]["fixture_runtime_probe"]["status"] == "blocked"
        assert result["observed"]["fixture_runtime_probe"]["checks"][
            "required_text_present"
        ] is False


def test_batch4_overclaim_shape_mutation_changes_recomputed_verdict(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    case_id = "erdos_solution_overclaim"
    baseline = evaluate_negative_case(
        case_id,
        fixture,
        EXPECTED_NEGATIVE_CASES[case_id],
    )
    assert baseline["status"] == "blocked"
    assert baseline["evidence"]["overclaim_shape"]["status"] == "pass"

    manifest_path = fixture / "batch4_probe_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mechanism = next(
        row
        for row in manifest["mechanisms"]
        if row["mechanism_id"]
        == NEGATIVE_CASE_OVERCLAIM_SHAPES[case_id]["mechanism_id"]
    )
    mechanism["claim_ceiling"] = (
        "Machine-checkable certificate-kernel scope only; solution and publication "
        "authority are intentionally overclaimed here."
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    mutated = evaluate_negative_case(
        case_id,
        fixture,
        EXPECTED_NEGATIVE_CASES[case_id],
    )
    result = run(fixture, fixture.parents[3] / "receipts/batch4_overclaim_shape")

    assert mutated["status"] == "pass"
    assert mutated["error_codes"] == []
    assert mutated["observed"]["runtime_case"]["computed"] is True
    assert mutated["observed"]["fixture_runtime_probe"]["status"] == "pass"
    assert mutated["observed"]["overclaim_shape"]["status"] == "blocked"
    assert mutated["observed"]["overclaim_shape"]["checks"][
        "claim_ceiling_anchors_present"
    ] is False
    semantics = {
        row["case_id"]: row
        for row in result["exercise"]["semantic_negative_case_proofs"]
    }
    assert result["status"] == "blocked"
    assert case_id in result["missing_negative_cases"]
    assert semantics[case_id]["computed_rejection"] is False
    assert semantics[case_id]["fixture_runtime_probe"]["status"] == "pass"
    assert semantics[case_id]["overclaim_shape"]["status"] == "blocked"


def test_batch4_lean_lake_probe_perturbation_moves_erdos_overclaim_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    _install_fake_source_lake_project(fixture.parents[3])
    case_id = "erdos_solution_overclaim"
    monkeypatch.setattr(batch4_runtime.shutil, "which", lambda name: f"/redacted/{name}")
    monkeypatch.setattr(batch4_runtime, "_run_command", lambda *args, **kwargs: _fake_command_result())

    baseline = evaluate_negative_case(
        case_id,
        fixture,
        EXPECTED_NEGATIVE_CASES[case_id],
    )
    assert baseline["status"] == "blocked"
    assert baseline["evidence"]["runtime_case"]["computed"] is True
    assert baseline["evidence"]["runtime_case"]["observed"]["lean_lake_probe_status"] == "pass"
    assert baseline["evidence"]["runtime_case"]["observed"][
        "lean_lake_compile_boundary_status"
    ] == "live_compile_pass"
    assert baseline["evidence"]["runtime_case"]["observed"][
        "lean_lake_compile_boundary_load_bearing"
    ] is True

    batch4_runtime._LEAN_LAKE_PROBE_CACHE.clear()
    monkeypatch.setattr(
        batch4_runtime,
        "_run_command",
        lambda *args, **kwargs: _fake_command_result("blocked"),
    )
    perturbed = evaluate_negative_case(
        case_id,
        fixture,
        EXPECTED_NEGATIVE_CASES[case_id],
    )
    result = run(fixture, fixture.parents[3] / "receipts/batch4_lean_probe_perturbed")

    assert perturbed["status"] == "pass"
    assert perturbed["observed"]["runtime_case"]["computed"] is False
    assert perturbed["observed"]["runtime_case"]["observed"]["lean_lake_probe_status"] == "blocked"
    assert perturbed["observed"]["runtime_case"]["observed"][
        "lean_lake_compile_boundary_status"
    ] == "live_compile_reject"
    assert perturbed["observed"]["runtime_case"]["observed"][
        "lean_lake_compile_boundary_load_bearing"
    ] is True
    assert result["status"] == "blocked"
    assert case_id in result["missing_negative_cases"]
    assert "BATCH4_LEAN_LAKE_PROBE_FAILED" in result["error_codes"]


def test_batch4_mutated_runtime_source_moves_verdict_and_negative_count(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    public_root = fixture.parents[3]
    bundle = _bundle_for_fixture(fixture)

    baseline = run(fixture, public_root / "receipts/batch4_baseline", command="pytest")
    assert baseline["status"] == "pass"
    assert len(baseline["observed_negative_cases"]) == len(EXPECTED_NEGATIVE_CASES)
    assert (
        baseline["exercise"]["semantic_negative_case_computed_rejection_count"]
        == len(EXPECTED_NEGATIVE_CASES)
    )

    manifest = json.loads((bundle / "source_module_manifest.json").read_text(encoding="utf-8"))
    grant_row = next(
        row for row in manifest["modules"] if row["module_id"] == "reasoning_grant_lease"
    )
    grant_path = bundle / grant_row["path"]
    grant_path.write_text(
        grant_path.read_text(encoding="utf-8").replace(
            "forbidden_effective_context",
            "removed_effective_context",
            1,
        ),
        encoding="utf-8",
    )

    mutated = run(fixture, public_root / "receipts/batch4_mutated", command="pytest")

    assert mutated["status"] == "blocked"
    assert mutated["observed_negative_cases"] == []
    assert mutated["exercise"]["semantic_negative_case_computed_rejection_count"] == 0
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in mutated["error_codes"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in mutated["error_codes"]


def test_batch4_authority_packet_mutations_change_recomputed_verdict(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    public_root = fixture.parents[3]
    bundle = _bundle_for_fixture(fixture)
    receipt_root = (
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch4_proof_authority_runtime"
    )

    baseline_bundle = run_batch4_bundle(bundle, receipt_root / "baseline", command="pytest")
    assert baseline_bundle["status"] == "pass"
    baseline_semantic = evaluate_negative_case(
        "grant_forbidden_context",
        fixture,
        EXPECTED_NEGATIVE_CASES_LITERAL["grant_forbidden_context"],
    )
    assert baseline_semantic["status"] == "blocked"
    assert baseline_semantic["error_codes"] == [
        "BATCH4_GRANT_FORBIDDEN_CONTEXT_DENIED"
    ]

    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grant_row = next(
        row for row in manifest["modules"] if row["module_id"] == "reasoning_grant_lease"
    )
    for key in ("sha256", "source_sha256", "target_sha256"):
        grant_row[key] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    corrupted_hash = run_batch4_bundle(
        bundle,
        receipt_root / "corrupted_hash",
        command="pytest",
    )

    assert corrupted_hash["status"] == "blocked"
    assert corrupted_hash["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in corrupted_hash["error_codes"]
    grant_receipt = next(
        row
        for row in corrupted_hash["source_module_manifest"]["modules"]
        if row["source_ref"].endswith("build_reasoning_execution_grant_lease.py")
    )
    assert grant_receipt["digest_status"] == "mismatch"

    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    grant_row = next(
        row for row in manifest["modules"] if row["module_id"] == "reasoning_grant_lease"
    )
    grant_path = bundle / grant_row["path"]
    grant_path.write_text(
        grant_path.read_text(encoding="utf-8").replace(
            "forbidden_effective_context",
            "removed_effective_context",
        ),
        encoding="utf-8",
    )

    corrupted_authority = evaluate_negative_case(
        "grant_forbidden_context",
        fixture,
        EXPECTED_NEGATIVE_CASES_LITERAL["grant_forbidden_context"],
    )

    assert corrupted_authority["status"] == "pass"
    assert corrupted_authority["error_codes"] == []
    assert corrupted_authority["observed"]["runtime_case"]["computed"] is False
    assert corrupted_authority["observed"]["runtime_case"]["observed"][
        "grant_forbidden_context_denies"
    ] is False
