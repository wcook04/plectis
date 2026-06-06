from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import microcosm_core.organs.certificate_kernel_execution_lab as certificate_lab
from microcosm_core.organs.certificate_kernel_execution_lab import (
    BUNDLE_RESULT_NAME,
    EXPECTED_NEGATIVE_CASES,
    build_public_readout,
    run,
    run_certificate_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/certificate_kernel_execution_lab/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def test_certificate_kernel_execution_lab_tool_versions_skip_hot_path_subprocess(
    monkeypatch: Any,
) -> None:
    certificate_lab._cached_tool_versions.cache_clear()

    def fake_which(name: str) -> str | None:
        return f"/tmp/fake-{name}" if name in {"lean", "lake"} else None

    def fail_run_command(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("tool version metadata should not spawn subprocesses")

    monkeypatch.setattr(certificate_lab.shutil, "which", fake_which)
    monkeypatch.setattr(certificate_lab, "_run_command", fail_run_command)

    versions = certificate_lab._tool_versions()

    assert versions["lean_available"] is True
    assert versions["lake_available"] is True
    assert versions["lean_version_command"]["skipped"] is True
    assert versions["lake_version_command"]["skip_reason"] == "version_probe_skipped_hot_path"
    assert versions["lean_version_command"]["tool_path_available"] is True
    assert "tool_path" not in versions["lean_version_command"]
    certificate_lab._cached_tool_versions.cache_clear()


@pytest.fixture(scope="module")
def certificate_lab_fixture_run(tmp_path_factory: Any) -> dict[str, Any]:
    public_root = tmp_path_factory.mktemp("certificate-lab-root") / "microcosm-substrate"
    input_dir = public_root / "fixtures/first_wave/certificate_kernel_execution_lab/input"
    out = public_root / "receipts/first_wave/certificate_kernel_execution_lab"
    acceptance_out = public_root / certificate_lab.ACCEPTANCE_RECEIPT_REL
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(FIXTURE_INPUT, input_dir)
    result = run(
        input_dir,
        out,
        acceptance_out=acceptance_out,
        command="pytest",
    )
    return {
        "public_root": public_root,
        "input_dir": input_dir,
        "out": out,
        "acceptance_out": acceptance_out,
        "result": result,
    }


@pytest.fixture(scope="module")
def certificate_lab_bundle_run(tmp_path_factory: Any) -> dict[str, Any]:
    out = (
        tmp_path_factory.mktemp("certificate-lab-bundle")
        / "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab"
    )
    result = run_certificate_bundle(EXPORTED_BUNDLE, out, command="pytest")
    return {"out": out, "result": result}


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


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


def test_certificate_kernel_execution_lab_input_scan_streams_project_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    project_dir = input_dir / "lake_project"
    nested = project_dir / "MicrocosmCertificateLab"
    nested.mkdir(parents=True)
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmCertificateLab.Basic\n",
        encoding="utf-8",
    )
    (nested / "Basic.lean").write_text(
        "theorem certificate_smoke : True := by trivial\n",
        encoding="utf-8",
    )
    (nested / "notes.md").write_text("public notes\n", encoding="utf-8")
    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == project_dir:
            raise AssertionError("Lean project input scan should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    assert [
        path.relative_to(input_dir).as_posix()
        for path in certificate_lab._input_paths(input_dir, include_negative=False)
    ] == [
        "certificate_lab_packet.json",
        "certificate_manifest.json",
        "lake_project/lakefile.lean",
        "lake_project/MicrocosmCertificateLab/Basic.lean",
        "lake_project/lakefile.lean",
    ]


def test_certificate_kernel_execution_lab_analyzer_streams_project_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project_dir = tmp_path / "lake_project"
    nested = project_dir / "MicrocosmCertificateLab"
    nested.mkdir(parents=True)
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmCertificateLab.Basic\n",
        encoding="utf-8",
    )
    (nested / "Basic.lean").write_text(
        "def certificateWitness : Nat := 1\n"
        "theorem certificate_smoke : True := by trivial\n",
        encoding="utf-8",
    )
    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == project_dir:
            raise AssertionError("Lean project analyzer should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    analyzer = certificate_lab._analyze_lean_project(
        project_dir,
        public_root=tmp_path,
        source_project_dir=project_dir,
    )

    assert analyzer["lean_file_count"] == 2
    assert analyzer["declaration_count"] == 2
    assert [row["source_ref"] for row in analyzer["files"]] == [
        "lake_project/MicrocosmCertificateLab/Basic.lean",
        "lake_project/lakefile.lean",
    ]


def test_certificate_kernel_execution_lab_reuses_built_lake_project_cache(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    project_dir = input_dir / "lake_project"
    nested = project_dir / "MicrocosmCertificateLab"
    nested.mkdir(parents=True)
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmCertificateLab.Basic\n",
        encoding="utf-8",
    )
    lean_file = nested / "Basic.lean"
    lean_file.write_text("theorem certificate_smoke : True := by trivial\n", encoding="utf-8")
    monkeypatch.setattr(certificate_lab, "_LAKE_PROJECT_BUILD_CACHE", {})
    monkeypatch.setattr(certificate_lab, "_LAKE_PROJECT_BUILD_CACHE_HOLDERS", [])

    first_root = tmp_path / "first"
    first_root.mkdir()
    first_project = certificate_lab._copy_project_to_temp(input_dir, first_root)
    build_marker = first_project / ".lake/build.stamp"
    build_marker.parent.mkdir(parents=True)
    build_marker.write_text("built\n", encoding="utf-8")
    certificate_lab._remember_built_lake_project(input_dir, first_project)

    second_root = tmp_path / "second"
    second_root.mkdir()
    second_project = certificate_lab._copy_project_to_temp(input_dir, second_root)

    assert (second_project / ".lake/build.stamp").read_text(encoding="utf-8") == "built\n"
    lean_file.write_text(
        "theorem certificate_smoke_changed : True := by trivial\n",
        encoding="utf-8",
    )
    third_root = tmp_path / "third"
    third_root.mkdir()
    third_project = certificate_lab._copy_project_to_temp(input_dir, third_root)
    assert not (third_project / ".lake/build.stamp").exists()


def test_certificate_kernel_execution_lab_batches_positive_transition_checks(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project_dir = tmp_path / "lake_project"
    project_dir.mkdir()
    monkeypatch.setattr(certificate_lab, "_TRANSITION_EXECUTION_CACHE", {})
    calls: list[list[str]] = []

    def fake_run_command(
        argv: list[str],
        *,
        cwd: Path,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        calls.append(argv)
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": 1
            if argv[-1] == "missing_certificate_row_residual.lean"
            else 0,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
        }

    monkeypatch.setattr(certificate_lab, "_run_command", fake_run_command)
    rows = [
        {
            "transition_id": "direct_certificate_check_2_3_5",
            "problem_id": "p1",
            "target_shape": "nat_sum",
            "action_class": "direct_certificate_check",
            "candidate_kind": "public_certificate",
            "allowed_certificate_refs": ["cert_2_3_5"],
        },
        {
            "transition_id": "cp2_add_certificate_row_rerun",
            "problem_id": "p2",
            "target_shape": "nat_sum",
            "action_class": "add_certificate_row",
            "candidate_kind": "public_certificate",
            "allowed_certificate_refs": ["cert_8_13_21"],
        },
        {
            "transition_id": "missing_certificate_row_residual",
            "problem_id": "p3",
            "target_shape": "nat_sum",
            "action_class": "select_certificate_row",
            "candidate_kind": "public_certificate",
            "allowed_certificate_refs": [],
            "expected_outcome": "fail_missing_certificate_row",
            "expected_failure_class": "PREMISE_RETRIEVAL_MISS",
        },
    ]

    receipts = certificate_lab._execute_transitions(
        rows,
        project_dir=project_dir,
        findings=[],
        observed={},
    )

    called_sources = [call[-1] for call in calls]
    assert sorted(called_sources) == sorted(
        [
            certificate_lab.LEAN_TRANSITION_BATCH_NAME,
            "missing_certificate_row_residual.lean",
        ]
    )
    batch_source = (
        project_dir / certificate_lab.LEAN_TRANSITION_BATCH_NAME
    ).read_text(encoding="utf-8")
    assert batch_source.count("namespace MicrocosmCertificateLabExecution") == 1
    assert "direct_certificate_check_2_3_5" in batch_source
    assert "cp2_add_certificate_row_rerun" in batch_source
    assert "missing_certificate_row_residual" not in batch_source
    assert [receipt.transition_id for receipt in receipts] == [
        row["transition_id"] for row in rows
    ]
    assert [receipt.accepted for receipt in receipts] == [True, True, False]
    assert receipts[2].verifier_failure_class == "PREMISE_RETRIEVAL_MISS"


def test_certificate_kernel_execution_lab_runs_lean_cp2_evolve_and_analyzer(
    certificate_lab_fixture_run: dict[str, Any],
) -> None:
    result = certificate_lab_fixture_run["result"]

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    counters = result["authority_counters"]
    assert counters["transition_count"] == 10
    assert counters["accepted_transition_count"] == 7
    assert counters["residual_transition_count"] == 3
    assert counters["cp2_translation_count"] == 2
    assert counters["cp2_downstream_effect_count"] == 2
    assert counters["evolve_candidate_count"] == 2
    assert counters["evolve_accepted_count"] == 2
    assert counters["analyzed_lean_file_count"] == 5
    assert counters["analyzed_declaration_count"] >= 20
    assert counters["oracle_forward_success_increment_count"] == 0
    assert counters["provider_results_counted"] == 0
    assert counters["proof_body_export_count"] == 0
    assert counters["source_mutation_count"] == 0
    assert counters["macro_private_body_import_count"] == 0

    transparency = result["receipt_transparency_contract"]
    assert transparency["receipt_body_is_public_evidence"] is True
    assert transparency["omitted_payload_scope"] == (
        "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only"
    )
    assert transparency["body_in_receipt"] is False
    assert "theorem_or_declaration_names" in transparency["required_public_evidence_fields"]
    assert "proof_body" in transparency["forbidden_payload_fields"]
    assert "provider_text" in transparency["forbidden_payload_fields"]

    analyzer = result["lean_analyzer_receipt"]
    assert all(
        file_row["source_ref"].startswith(
            "fixtures/first_wave/certificate_kernel_execution_lab/input/lake_project/"
        )
        for file_row in analyzer["files"]
    )
    assert all("/private/" not in file_row["source_ref"] for file_row in analyzer["files"])
    assert all(not Path(file_row["source_ref"]).is_absolute() for file_row in analyzer["files"])
    declarations = {
        declaration
        for file_row in analyzer["files"]
        for declaration in file_row["declarations"]
    }
    assert "NatSumCertificate" in declarations
    assert "validateNatSumCertificate" in declarations
    assert "BoundedOrderCertificate" in declarations
    assert "validateBoundedOrderCertificate" in declarations
    assert "cert_8_13_21_valid" in declarations
    assert "order_cert_3_4_mod5_valid" in declarations
    assert analyzer["generated_certificates_separate_from_kernel"] is True

    claim_separation = result["claim_separation"]
    assert len(claim_separation["lean_verified"]) == 7
    assert len(claim_separation["provider_suggested"]) == 2
    assert len(claim_separation["oracle_compared"]) == 2
    assert len(claim_separation["cp2_translated"]) == 2
    assert len(claim_separation["retrieval_miss"]) == 2
    assert len(claim_separation["proof_synthesis_fail"]) == 1
    assert len(claim_separation["evolve_accepted"]) == 2


def test_certificate_kernel_execution_lab_bundle_is_public_structured(
    certificate_lab_bundle_run: dict[str, Any],
) -> None:
    result = certificate_lab_bundle_run["result"]

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_certificate_kernel_execution_lab_bundle"
    assert result["execution_witness_mode"] == "standalone_exported_certificate_contract"
    assert result["bundle_id"] == "public_certificate_kernel_execution_lab_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["authority_counters"]["accepted_transition_count"] == 7
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 2
    assert result["authority_counters"]["evolve_accepted_count"] == 2
    assert result["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith(
        "exported_certificate_kernel_execution_lab_bundle/source_module_manifest.json"
    )
    assert result["source_module_count"] == 9
    assert result["verified_source_module_count"] == 9
    assert result["body_copied_material_count"] == 9
    source_open = result["source_open_body_imports"]
    assert source_open["status"] == "pass"
    assert source_open["body_material_status"] == (
        "copied_non_secret_certificate_kernel_macro_body_landed"
    )
    assert source_open["body_material_count"] == 9
    assert source_open["body_text_exported_in_receipts"] is False
    assert source_open["body_text_exported_in_workingness"] is False
    assert "public_macro_proof_body" in source_open["material_classes"]
    assert "public_macro_tool_body" in source_open["material_classes"]
    assert "public_macro_receipt_body" in source_open["material_classes"]
    source_modules = result["source_module_imports"]
    assert source_modules["status"] == "pass"
    assert source_modules["verified_module_count"] == 9
    assert source_modules["findings"] == []
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert all(
        ref.startswith(
            "examples/certificate_kernel_execution_lab/"
            "exported_certificate_kernel_execution_lab_bundle/"
        )
        for ref in result["public_runtime_refs"]
    )


def test_certificate_kernel_execution_lab_exported_bundle_uses_standalone_contract(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fail_run_command(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("exported certificate bundle should not spawn Lean/Lake")

    monkeypatch.setattr(certificate_lab, "_run_command", fail_run_command)

    result = run_certificate_bundle(
        EXPORTED_BUNDLE,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab",
        command="pytest standalone certificate bundle",
    )

    assert result["status"] == "pass"
    assert result["execution_witness_mode"] == "standalone_exported_certificate_contract"
    assert result["tool_versions"]["lean_available"] is True
    assert result["tool_versions"]["lake_available"] is True
    assert result["tool_versions"]["lean_version_command"]["skipped"] is True
    assert result["tool_versions"]["lake_version_command"]["skip_reason"] == (
        "standalone_exported_certificate_contract"
    )
    assert result["lake_project_build"]["skipped"] is True
    assert result["lake_project_build"]["return_code"] == 0
    assert result["lake_project_build"]["skip_reason"] == (
        "standalone_exported_certificate_contract"
    )
    assert result["authority_counters"]["transition_count"] == 10
    assert result["authority_counters"]["accepted_transition_count"] == 7
    assert result["authority_counters"]["residual_transition_count"] == 3
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 2
    assert result["authority_counters"]["evolve_accepted_count"] == 2
    assert result["lean_analyzer_receipt"]["declaration_count"] >= 8
    assert result["source_module_imports"]["status"] == "pass"
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_certificate_kernel_execution_lab_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = (
        public_root
        / "examples/certificate_kernel_execution_lab/"
        "exported_certificate_kernel_execution_lab_bundle"
    )
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(EXPORTED_BUNDLE, bundle)

    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_certificate_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["lake_project_build"]["skipped"] is True
    assert result["lake_project_build"]["skip_reason"] == "source_module_manifest_blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_count"] == 9
    assert result["body_copied_material_count"] == 0
    assert result["verified_source_module_count"] == 8
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["source_open_body_imports"]["body_material_count"] == 0
    assert "CERTIFICATE_KERNEL_SOURCE_MODULE_SHA256_MISMATCH" in result["error_codes"]
    digest_findings = [
        row
        for row in result["source_module_imports"]["findings"]
        if row["error_code"] == "CERTIFICATE_KERNEL_SOURCE_MODULE_SHA256_MISMATCH"
    ]
    assert len(digest_findings) == 1
    assert digest_findings[0]["negative_case_id"] == (
        "period_noncollapse_strike_runner_body_import"
    )
    assert digest_findings[0]["subject_kind"] == "source_module_target"


def test_certificate_kernel_execution_lab_bundle_rejects_partial_target_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = (
        public_root
        / "examples/certificate_kernel_execution_lab/"
        "exported_certificate_kernel_execution_lab_bundle"
    )
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(EXPORTED_BUNDLE, bundle)

    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_certificate_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["lake_project_build"]["skipped"] is True
    assert result["lake_project_build"]["skip_reason"] == "source_module_manifest_blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_count"] == 9
    assert result["verified_source_module_count"] == 8
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert "CERTIFICATE_KERNEL_SOURCE_MODULE_SHA256_MISMATCH" in result["error_codes"]
    digest_findings = [
        row
        for row in result["source_module_imports"]["findings"]
        if row["error_code"] == "CERTIFICATE_KERNEL_SOURCE_MODULE_SHA256_MISMATCH"
    ]
    assert len(digest_findings) == 1
    assert digest_findings[0]["negative_case_id"] == (
        "period_noncollapse_strike_runner_body_import"
    )
    assert digest_findings[0]["subject_kind"] == "source_module_target"


def test_certificate_kernel_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == 9
    assert manifest["body_in_receipt"] is False
    assert manifest["body_text_in_receipt"] is False
    assert manifest["blocked_source_refs"] == []

    modules = manifest["modules"]
    assert len(modules) == manifest["module_count"]
    assert {row["material_class"] for row in modules} == {
        "public_macro_proof_body",
        "public_macro_receipt_body",
        "public_macro_tool_body",
    }
    for row in modules:
        source_path = SOURCE_ROOT / row["source_ref"]
        target_path = EXPORTED_BUNDLE / row["target_ref"]
        assert target_path.is_file(), row["target_ref"]
        if source_path.is_file():
            assert target_path.read_bytes() == source_path.read_bytes()
            assert _sha256(source_path).removeprefix("sha256:") == row["source_sha256"]
        else:
            assert row["source_sha256"] == row["target_sha256"]
        assert _sha256(target_path).removeprefix("sha256:") == row["target_sha256"]
        assert _sha256(target_path).removeprefix("sha256:") == row["sha256"]
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        target_text = target_path.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_certificate_kernel_execution_lab_bundle_card_reads_cached_receipt(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    out_dir = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab"
    )
    out_dir.mkdir(parents=True)
    receipt_path = out_dir / BUNDLE_RESULT_NAME
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": (
                    "exported_certificate_kernel_execution_lab_bundle_validation_result_v1"
                ),
                "status": "pass",
                "organ_id": "certificate_kernel_execution_lab",
                "command": "pytest",
                "input_mode": "exported_certificate_kernel_execution_lab_bundle",
                "bundle_id": "public_certificate_kernel_execution_lab_runtime_example",
                "certificate_lab_id": "public_certificate_kernel_execution_lab",
                "certificate_manifest_id": "public_certificate_kernel_manifest",
                "source_module_manifest_status": "pass",
                "source_module_manifest_ref": (
                    "examples/certificate_kernel_execution_lab/"
                    "exported_certificate_kernel_execution_lab_bundle/"
                    "source_module_manifest.json"
                ),
                "body_copied_material_count": 9,
                "source_open_body_imports": {
                    "status": "pass",
                    "body_material_count": 9,
                    "body_text_exported_in_receipts": False,
                },
                "authority_counters": {
                    "transition_count": 10,
                    "accepted_transition_count": 7,
                    "residual_transition_count": 3,
                    "cp2_downstream_effect_count": 2,
                    "evolve_accepted_count": 2,
                    "analyzed_declaration_count": 23,
                    "oracle_forward_success_increment_count": 0,
                    "provider_results_counted": 0,
                    "proof_body_export_count": 0,
                    "source_mutation_count": 0,
                    "macro_private_body_import_count": 0,
                },
                "secret_exclusion_scan": {
                    "status": "pass",
                    "blocking_hit_count": 0,
                    "body_in_receipt": False,
                },
                "tool_versions": {"lean_available": True, "lake_available": True},
                "lake_project_build": {"return_code": 0},
                "authority_ceiling": {"formal_prover_execution_authorized": False},
                "anti_claim": "receipt-only cached card",
                "body_in_receipt": False,
                "real_runtime_receipt": True,
                "synthetic_receipt_standin_allowed": False,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def fail_build_result(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("cached certificate-kernel card must not rerun validation")

    monkeypatch.setattr(certificate_lab, "_build_result", fail_build_result)

    status = certificate_lab.main(
        [
            "run-certificate-bundle",
            "--input",
            str(EXPORTED_BUNDLE),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert payload["schema_version"] == "certificate_kernel_execution_lab_command_card_v1"
    assert payload["cached_receipt_used"] is True
    assert payload["cache_status"] == "current"
    assert payload["cache_freshness"]["tracked_input_count"] >= 3
    assert payload["authority_counters"]["accepted_transition_count"] == 7
    assert payload["runtime_summary"]["lake_return_code"] == 0
    assert payload["body_floor"]["source_module_manifest_status"] == "pass"
    assert payload["body_floor"]["source_open_body_import_status"] == "pass"
    assert payload["body_floor"]["source_open_body_import_count"] == 9
    assert payload["body_floor"]["body_copied_material_count"] == 9
    assert payload["body_floor"]["body_text_exported_in_receipts"] is False
    assert payload["output_economy"]["full_transition_trace_exported"] is False
    assert payload["output_economy"]["claim_separation_rows_exported"] is False
    assert len(encoded.encode("utf-8")) < 3600
    assert "transition_trace" not in payload
    assert "claim_separation" not in payload
    assert "source_open_body_imports" not in payload
    assert "proof_body" not in _walk_keys(payload)
    assert "provider_text" not in _walk_keys(payload)
    assert str(tmp_path) not in encoded
    assert "/Users/" not in encoded


def test_certificate_kernel_execution_lab_public_readout_uses_receipt_manifest_summary(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    receipt_dir = public_root / "receipts/first_wave/certificate_kernel_execution_lab"
    receipt_dir.mkdir(parents=True)
    acceptance_path = public_root / certificate_lab.ACCEPTANCE_RECEIPT_REL
    acceptance_path.parent.mkdir(parents=True)
    families = [
        {
            "family_id": "nat_sum_certificate",
            "schema": "NatSumCertificate(left,right,total)",
            "row_count": 4,
            "valid_row_count": 3,
            "negative_row_count": 1,
        }
    ]
    counters = {
        "accepted_transition_count": 7,
        "residual_transition_count": 3,
        "cp2_downstream_effect_count": 2,
        "evolve_accepted_count": 2,
        "oracle_forward_success_increment_count": 0,
        "provider_results_counted": 0,
        "proof_body_export_count": 0,
        "source_mutation_count": 0,
        "macro_private_body_import_count": 0,
    }
    result = {
        "status": "pass",
        "certificate_lab_id": "public_certificate_kernel_execution_lab",
        "certificate_manifest_id": "public_certificate_kernel_v2",
        "certificate_manifest_summary": {
            "manifest_id": "public_certificate_kernel_v2",
            "generated_certificate_count": 7,
            "certificate_families": families,
        },
        "authority_counters": counters,
        "receipt_transparency_contract": {
            "receipt_body_is_public_evidence": True,
            "omitted_payload_scope": (
                "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only"
            ),
        },
        "missing_negative_cases": [],
        "expected_negative_cases": [],
    }
    (receipt_dir / "certificate_kernel_execution_lab_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (receipt_dir / "certificate_kernel_execution_lab_board.json").write_text(
        json.dumps({"status": "pass"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    validation_path = receipt_dir / "certificate_kernel_execution_lab_validation_receipt.json"
    validation_path.write_text(
        json.dumps({"status": "pass"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    acceptance_path.write_text(
        json.dumps({"status": "pass"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    readout = build_public_readout(public_root)

    assert readout["status"] == "pass"
    assert readout["certificate_manifest_id"] == "public_certificate_kernel_v2"
    certificate_rows = readout["public_flow"][1]
    assert certificate_rows["generated_certificate_count"] == 7
    assert certificate_rows["certificate_families"] == families


def test_certificate_kernel_execution_lab_receipts_are_transparent_without_bodies(
    certificate_lab_fixture_run: dict[str, Any],
) -> None:
    out = certificate_lab_fixture_run["out"]

    receipt_file = out / "certificate_kernel_execution_lab_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    assert payload["receipt_transparency_contract"]["omitted_payload_scope"] == (
        "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only"
    )
    assert payload["body_in_receipt"] is False
    assert payload["real_runtime_receipt"] is True
    assert payload["synthetic_receipt_standin_allowed"] is False
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["lean_analyzer_receipt"]["declaration_count"] >= 20
    assert all(
        "/private/" not in row["source_ref"]
        for row in payload["lean_analyzer_receipt"]["files"]
    )
    assert payload["transition_trace"][0]["problem_id"] == "cert_2_3_5"
    assert payload["transition_trace"][0]["lean_return_code"] == 0
    assert payload["provider_calls_authorized"] is False
    assert payload["source_mutation_authorized"] is False
    assert "private_state_scan" not in payload
    assert "body_redacted" not in payload
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)


def test_certificate_kernel_execution_lab_public_readout_is_cold_reader_route(
    tmp_path: Path,
    certificate_lab_fixture_run: dict[str, Any],
) -> None:
    readout = build_public_readout(
        certificate_lab_fixture_run["public_root"],
        out=tmp_path
        / "receipts/first_wave/certificate_kernel_execution_lab/"
        "certificate_kernel_execution_lab_public_readout.json",
    )

    assert readout["status"] == "pass"
    assert readout["schema_version"] == "certificate_kernel_execution_lab_public_readout_v1"
    assert readout["readout_id"] == "certificate_kernel_execution_lab_runtime_readout"
    assert [
        stage["stage_id"]
        for stage in readout["public_flow"]
    ] == [
        "public_certificate_kernel",
        "generated_certificate_rows",
        "lean_lake_execution",
        "transition_adjudication",
        "cp2_translation_rerun",
        "bounded_evolve_policy_rerun",
        "authority_counter_boundary",
    ]
    families = {
        family["family_id"]: family for family in readout["public_flow"][1]["certificate_families"]
    }
    assert families["nat_sum_certificate"]["valid_row_count"] == 3
    assert families["bounded_order_certificate"]["valid_row_count"] == 2
    counters = readout["authority_counters"]
    assert counters["accepted_transition_count"] == 7
    assert counters["residual_transition_count"] == 3
    assert counters["cp2_downstream_effect_count"] == 2
    assert counters["evolve_accepted_count"] == 2
    assert counters["provider_results_counted"] == 0
    assert counters["oracle_forward_success_increment_count"] == 0
    assert counters["proof_body_export_count"] == 0
    assert counters["source_mutation_count"] == 0
    assert readout["dangerous_payload_absent"] is True
    assert readout["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    assert readout["body_in_receipt"] is False
    assert readout["real_runtime_receipt"] is True
    assert readout["synthetic_receipt_standin_allowed"] is False
    text = json.dumps(readout, sort_keys=True)
    assert "/private/" not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "proof_body" not in _walk_keys(readout)
    assert "provider_text" not in _walk_keys(readout)
    assert "body_redacted" not in _walk_keys(readout)


def test_certificate_kernel_execution_lab_readout_out_keeps_repo_root_path(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    output_path = (
        Path("microcosm-substrate")
        / "receipts/first_wave/certificate_kernel_execution_lab/"
        / "certificate_kernel_execution_lab_public_readout.json"
    )
    monkeypatch.chdir(tmp_path)

    build_public_readout(public_root, out=output_path)

    assert (public_root / output_path.relative_to("microcosm-substrate")).is_file()
    assert not (public_root / output_path).exists()
