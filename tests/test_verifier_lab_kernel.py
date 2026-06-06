from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs import verifier_lab_kernel
from microcosm_core.organs.verifier_lab_kernel import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_kernel_bundle,
    validate_source_module_imports,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/verifier_lab_kernel/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
)
SUBSTRATE_BINDINGS = (
    MICROCOSM_ROOT.parent
    / "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
)
SUBSTRATE_BINDINGS_SHA256 = (
    "sha256:89bcca24997029114a8542eea930fb26ddc2bddb5759adfb37950c3684cec1ee"
)
EXPECTED_COMPONENTS = {
    "corpus_readiness_mathlib_absence_gate",
    "formal_math_lean_proof_witness",
    "formal_math_premise_retrieval",
    "formal_math_verifier_trace_repair_loop",
    "lean_std_premise_index",
    "proof_diagnostic_evidence_spine",
    "ring2_premise_retrieval_precision_recall_harness",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
}


@pytest.fixture(scope="module")
def verifier_kernel_fixture_run(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], Path, Path]:
    root = tmp_path_factory.mktemp("verifier_kernel_fixture")
    out = root / "receipts/first_wave/verifier_lab_kernel"
    acceptance = (
        root
        / "receipts/acceptance/first_wave/verifier_lab_kernel_fixture_acceptance.json"
    )
    result = run(
        FIXTURE_INPUT,
        out,
        command="pytest",
        acceptance_out=acceptance,
    )
    return result, out, acceptance


@pytest.fixture(scope="module")
def verifier_kernel_bundle_run(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], Path]:
    root = tmp_path_factory.mktemp("verifier_kernel_bundle")
    out = root / "receipts/runtime_shell/demo_project/organs/verifier_lab_kernel"
    result = run_kernel_bundle(BUNDLE_INPUT, out, command="pytest")
    return result, out


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


def test_verifier_lab_kernel_dependency_scan_streams_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    dependency_dir = tmp_path / "dependencies"
    nested = dependency_dir / "nested"
    cache = dependency_dir / "__pycache__"
    nested.mkdir(parents=True)
    cache.mkdir()
    (dependency_dir / "alpha.py").write_text("VALUE = 1\n", encoding="utf-8")
    (nested / "data.json").write_text("{}", encoding="utf-8")
    (nested / "skip.pyc").write_bytes(b"cache")
    (cache / "ignored.py").write_text("VALUE = 2\n", encoding="utf-8")
    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == dependency_dir:
            raise AssertionError("dependency scan should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    assert [
        path.relative_to(dependency_dir).as_posix()
        for path in verifier_lab_kernel._iter_dependency_files(dependency_dir)
    ] == [
        "alpha.py",
        "nested/data.json",
    ]


def test_verifier_lab_kernel_receipt_normalization_streams_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    component_dir = tmp_path / "components"
    nested = component_dir / "proof"
    nested.mkdir(parents=True)
    receipt = nested / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "private_state_scan": {"blocking_hit_count": 0},
                "body_redacted": True,
                "path_ref": "/private/tmp/verifier",
            }
        ),
        encoding="utf-8",
    )
    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == component_dir:
            raise AssertionError("receipt normalization should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    verifier_lab_kernel._normalize_component_receipt_surface(component_dir)
    payload = json.loads(receipt.read_text(encoding="utf-8"))

    assert "private_state_scan" not in payload
    assert "body_redacted" not in payload
    assert payload["secret_exclusion_scan"] == {"blocking_hit_count": 0}
    assert payload["path_ref"] == "/tmp/verifier"


def test_verifier_lab_kernel_runs_component_stack_and_separates_claims(
    verifier_kernel_fixture_run: tuple[dict[str, Any], Path, Path],
) -> None:
    result, _out, _acceptance = verifier_kernel_fixture_run

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert set(result["component_statuses"]) == EXPECTED_COMPONENTS
    assert all(status == "pass" for status in result["component_statuses"].values())
    assert result["lean_lake_return_code"] == 0
    assert result["lean_compiled_declaration_count"] == 8
    assert result["target_shape_route_case_count"] >= 4
    assert result["verifier_trace_attempt_count"] >= 3
    metrics = result["proof_lab_component_metrics"]
    assert metrics["corpus_count"] == 7
    assert metrics["lean_std_premise_count"] == 11
    assert metrics["retrieval_query_count"] == 4
    assert metrics["ring2_problem_count"] == 10
    assert metrics["ring2_mean_precision_at_k"] == 0.36
    assert metrics["proof_diagnostic_accepted_count"] >= 2
    assert set(result["claim_separation"]) == {
        "lean_verified",
        "provider_suggested",
        "oracle_compared",
        "contract_rejected",
        "retrieval_miss",
        "cp2_translated",
        "evolve_candidate",
    }
    assert len(result["claim_separation"]["cp2_translated"]) == 2
    assert len(result["claim_separation"]["evolve_candidate"]) == 1
    assert result["authority_counters"][
        "oracle_forward_success_increment_count"
    ] == 0
    assert result["authority_counters"]["provider_results_counted"] == 0
    assert result["authority_ceiling"]["provider_text_counts_as_proof"] is False
    assert result["authority_ceiling"]["oracle_success_counts_as_forward_success"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_verifier_lab_kernel_fixture_reuses_fresh_receipt(
    verifier_kernel_fixture_run: tuple[dict[str, Any], Path, Path],
    monkeypatch,
) -> None:
    result, out_dir, acceptance_out = verifier_kernel_fixture_run
    assert result["status"] == "pass"
    assert result["cache_status"] == "rebuilt"

    def fail_rebuild(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh fixture receipt should be reused")

    monkeypatch.setattr(verifier_lab_kernel, "_build_result", fail_rebuild)
    cached = run(
        FIXTURE_INPUT,
        out_dir,
        command="pytest",
        acceptance_out=acceptance_out,
    )

    assert cached["status"] == "pass"
    assert cached["cache_status"] == "fresh_receipt_reused"
    assert cached["freshness_basis"]["input_mode"] == "first_wave_fixture"
    assert cached["freshness_basis"]["tracked_dependency_count"] > 10
    assert cached["receipt_paths"] == result["receipt_paths"]


def test_verifier_lab_kernel_receipts_are_public_relative_and_transparent_without_bodies(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")

    result = run(
        public_root / "fixtures/first_wave/verifier_lab_kernel/input",
        public_root / "receipts/first_wave/verifier_lab_kernel",
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
        assert "matched_excerpt" not in text
        assert '"proof_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
        assert payload["receipt_transparency_contract"]["omitted_payload_scope"] == (
            "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only"
        )
        assert payload["receipt_transparency_contract"]["body_in_receipt"] is False
        assert payload["receipt_transparency_contract"]["real_substrate_default"] is True
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "public_replacement_refs" not in payload
        assert "proof_body" not in _walk_keys(payload)

    for component_receipt in (
        public_root / "receipts/first_wave/verifier_lab_kernel/components"
    ).rglob("*.json"):
        text = component_receipt.read_text(encoding="utf-8")
        assert "private_state_scan" not in text
        assert "body_redacted" not in text
        assert "public_replacement_ref" not in text


def test_verifier_lab_kernel_exported_bundle_validates_runtime_shape(
    verifier_kernel_bundle_run: tuple[dict[str, Any], Path],
    monkeypatch,
) -> None:
    result, out_dir = verifier_kernel_bundle_run

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_verifier_lab_kernel_bundle"
    assert result["bundle_id"] == "verifier_lab_kernel_runtime_example"
    assert result["proof_lab_route"]["status"] == "pass"
    assert result["proof_lab_route_id"] == "formal_prover_context_strategy_gate"
    assert result["proof_lab_route_source_sha256"] == SUBSTRATE_BINDINGS_SHA256
    assert result["proof_lab_route_component_count"] == len(EXPECTED_COMPONENTS)
    assert result["source_module_imports"]["status"] == "pass"
    assert result["source_module_imports"]["module_count"] == 14
    assert result["source_module_imports"]["body_text_in_receipt"] is False
    assert all(
        row["body_text_in_receipt"] is False
        for row in result["source_module_imports"]["modules"]
    )
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 14
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["source_open_body_imports"]["body_text_in_receipt"] is False
    assert result["body_copied_material_count"] == 14
    assert set(result["component_statuses"]) == EXPECTED_COMPONENTS
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert all(status == "pass" for status in result["component_statuses"].values())
    assert result["lean_lake_return_code"] == 0
    assert result["lean_compiled_declaration_count"] == 8
    assert result["proof_lab_component_metrics"]["corpus_count"] == 7
    assert result["proof_lab_component_metrics"]["lean_std_premise_count"] == 11
    assert result["proof_lab_component_metrics"]["retrieval_query_count"] == 4
    assert result["proof_lab_component_metrics"]["ring2_mean_recall_at_k"] == 0.9
    assert result["proof_lab_component_metrics"]["proof_diagnostic_accepted_count"] == 1
    assert len(result["claim_separation"]["provider_suggested"]) == 1
    assert len(result["claim_separation"]["cp2_translated"]) == 2
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
    assert result["cache_status"] == "rebuilt"
    assert result["freshness_basis"]["tracked_dependency_count"] > 10

    def fail_rebuild(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh exported verifier-lab receipt should be reused")

    monkeypatch.setattr(verifier_lab_kernel, "_build_result", fail_rebuild)
    cached = run_kernel_bundle(
        BUNDLE_INPUT,
        out_dir,
        command="pytest",
    )
    assert cached["cache_status"] == "fresh_receipt_reused"
    assert cached["status"] == "pass"
    assert cached["receipt_paths"] == result["receipt_paths"]


def test_verifier_lab_kernel_exported_bundle_uses_standalone_component_contract(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fail_component(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("exported verifier kernel should not rerun component organs")

    patched = {
        organ_id: {mode: fail_component for mode in runners}
        for organ_id, runners in verifier_lab_kernel.COMPONENT_RUNNERS.items()
    }
    monkeypatch.setattr(verifier_lab_kernel, "COMPONENT_RUNNERS", patched)

    result = run_kernel_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/verifier_lab_kernel",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["component_witness_mode"] == "standalone_exported_receipt_ref_contract"
    assert set(result["component_statuses"]) == EXPECTED_COMPONENTS
    assert all(result["component_receipt_refs"].values())
    assert result["lean_lake_return_code"] == 0
    assert result["lean_compiled_declaration_count"] == 8


def test_verifier_lab_kernel_exported_bundle_blocks_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    bundle_input = tmp_path / "exported_verifier_lab_kernel_bundle"
    shutil.copytree(BUNDLE_INPUT, bundle_input)
    manifest_path = bundle_input / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_module = manifest["modules"][0]
    first_module["sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_kernel_bundle(
        bundle_input,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/verifier_lab_kernel",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_imports"]["status"] == "blocked"
    assert result["source_module_imports"]["module_count"] == 14
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["body_copied_material_count"] == 14
    assert result["body_in_receipt"] is False
    assert result["source_module_imports"]["body_text_in_receipt"] is False
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["source_open_body_imports"]["body_text_in_receipt"] is False
    source_findings = result["source_module_imports"]["findings"]
    assert [row["error_code"] for row in source_findings] == [
        "VERIFIER_LAB_SOURCE_MODULE_DIGEST_MISMATCH"
    ]
    assert source_findings[0]["subject_kind"] == "source_module"
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_verifier_lab_kernel_source_module_manifest_is_exact_public_body_floor() -> None:
    manifest_path = BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_imports = validate_source_module_imports(
        BUNDLE_INPUT,
        public_root=MICROCOSM_ROOT,
    )

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["body_text_in_receipt"] is False
    assert manifest["module_count"] == 14
    assert source_imports["status"] == "pass"
    assert source_imports["module_count"] == 14
    assert source_imports["body_text_in_receipt"] is False

    module_ids = {row["module_id"] for row in source_imports["modules"]}
    assert "verifier_lab_kernel_source_body_import" in module_ids
    assert "prover_statement_only_hammer_bandit_runner_body_import" in module_ids
    assert "prover_proof_state_search_curriculum_runner_body_import" in module_ids
    for row in manifest["modules"]:
        source_ref = str(row["source_ref"])
        source_root = (
            MICROCOSM_ROOT
            if source_ref.startswith("src/microcosm_core/")
            else MICROCOSM_ROOT.parent
        )
        source_path = source_root / source_ref
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target_path = MICROCOSM_ROOT / target_ref
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        assert row["material_class"] == "public_macro_tool_body"
        assert source_path.read_bytes() == target_path.read_bytes()
    assert all(
        row["body_text_in_receipt"] is False for row in source_imports["modules"]
    )


def test_verifier_lab_kernel_blocks_source_module_body_text_receipt_flags(
    tmp_path: Path,
) -> None:
    cases = {
        "manifest_missing": "VERIFIER_LAB_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
        "manifest_true": "VERIFIER_LAB_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
        "row_missing": "VERIFIER_LAB_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
        "row_true": "VERIFIER_LAB_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
    }

    for case_id, expected_error in cases.items():
        bundle_input = tmp_path / case_id / "exported_verifier_lab_kernel_bundle"
        shutil.copytree(BUNDLE_INPUT, bundle_input)
        manifest_path = bundle_input / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if case_id == "manifest_missing":
            manifest.pop("body_text_in_receipt")
        elif case_id == "manifest_true":
            manifest["body_text_in_receipt"] = True
        elif case_id == "row_missing":
            manifest["modules"][0].pop("body_text_in_receipt")
        elif case_id == "row_true":
            manifest["modules"][0]["body_text_in_receipt"] = True
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        result = run_kernel_bundle(
            bundle_input,
            tmp_path
            / f"receipts/runtime_shell/demo_project/organs/verifier_lab_kernel/{case_id}",
            command="pytest",
        )

        assert result["status"] == "blocked"
        assert result["source_module_imports"]["status"] == "blocked"
        assert result["source_module_imports"]["body_text_in_receipt"] is False
        assert result["source_open_body_imports"]["status"] == "blocked"
        assert result["source_open_body_imports"]["body_text_in_receipt"] is False
        assert result["body_in_receipt"] is False
        source_findings = result["source_module_imports"]["findings"]
        assert expected_error in {row["error_code"] for row in source_findings}
        assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "proof_body" not in _walk_keys(result)


def test_verifier_lab_kernel_copied_prover_runners_have_public_smoke_commands() -> None:
    source_modules = BUNDLE_INPUT / "source_modules"
    runners = {
        "tools/meta/factory/run_prover_statement_only_hammer_bandit.py": [
            "--problem-limit",
            "--timeout-seconds",
            "--check",
            "--json",
        ],
        "tools/meta/factory/run_prover_proof_state_search_curriculum.py": [
            "--external-limit",
            "--local-limit",
            "--timeout-seconds",
            "--check",
            "--json",
        ],
    }

    for runner_ref, expected_args in runners.items():
        runner = source_modules / runner_ref
        result = subprocess.run(
            ["python3", str(runner), "--help"],
            cwd=MICROCOSM_ROOT,
            env={**os.environ, "PYTHONPATH": str(source_modules)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        help_text = result.stdout + result.stderr
        for arg in expected_args:
            assert arg in help_text


def test_verifier_lab_kernel_route_slice_is_source_faithful() -> None:
    route = json.loads((BUNDLE_INPUT / "proof_lab_route.json").read_text(encoding="utf-8"))
    source = json.loads(SUBSTRATE_BINDINGS.read_text(encoding="utf-8"))
    source_route = next(
        row
        for row in source["foundation_combination_routes"]
        if row["route_id"] == "formal_prover_context_strategy_gate"
    )

    assert route["schema_version"] == "formal_prover_context_strategy_gate_public_route_slice_v1"
    assert route["source_ref"] == "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
    assert route["source_sha256"] == SUBSTRATE_BINDINGS_SHA256
    assert route["classification"] == "source_faithful_refactor"
    assert route["foundation_route"] == source_route
    assert set(route["required_component_organs"]) == EXPECTED_COMPONENTS
    assert route["body_in_receipt"] is False
