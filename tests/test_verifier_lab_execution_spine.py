from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs import verifier_lab_execution_spine as spine
from microcosm_core.organs.verifier_lab_execution_spine import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_execution_bundle,
    validate_source_module_imports,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/verifier_lab_execution_spine/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/verifier_lab_execution_spine/exported_verifier_lab_execution_spine_bundle"
)


def test_verifier_lab_execution_spine_tool_versions_skip_hot_path_subprocess(
    monkeypatch: Any,
) -> None:
    spine._cached_tool_versions.cache_clear()

    def fake_which(name: str) -> str | None:
        return f"/tmp/fake-{name}" if name in {"lean", "lake"} else None

    def fail_run_command(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("tool version metadata should not spawn subprocesses")

    monkeypatch.setattr(spine.shutil, "which", fake_which)
    monkeypatch.setattr(spine, "_run_command", fail_run_command)

    versions = spine._tool_versions()

    assert versions["lean_available"] is True
    assert versions["lake_available"] is True
    assert versions["lean_version_command"]["skipped"] is True
    assert versions["lake_version_command"]["skip_reason"] == "version_probe_skipped_hot_path"
    assert versions["lean_version_command"]["tool_path_available"] is True
    assert "tool_path" not in versions["lean_version_command"]
    spine._cached_tool_versions.cache_clear()


@pytest.fixture(scope="module")
def verifier_spine_fixture_run(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], Path]:
    root = tmp_path_factory.mktemp("verifier_spine_fixture")
    out = root / "receipts/first_wave/verifier_lab_execution_spine"
    acceptance = (
        root
        / "receipts/acceptance/first_wave/verifier_lab_execution_spine_fixture_acceptance.json"
    )
    result = run(
        FIXTURE_INPUT,
        out,
        acceptance_out=acceptance,
        command="pytest",
    )
    return result, out


@pytest.fixture(scope="module")
def verifier_spine_bundle_run(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], Path, list[str]]:
    root = tmp_path_factory.mktemp("verifier_spine_bundle")
    out = root / "receipts/runtime_shell/demo_project/organs/verifier_lab_execution_spine"
    argv = [
        "run-execution-bundle",
        "--input",
        str(EXPORTED_BUNDLE),
        "--out",
        str(out),
        "--card",
    ]
    command = (
        "python -m microcosm_core.organs.verifier_lab_execution_spine "
        f"run-execution-bundle --input {EXPORTED_BUNDLE} --out {out} --card"
    )
    result = run_execution_bundle(EXPORTED_BUNDLE, out, command=command)
    return result, out, argv


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


def test_verifier_lab_execution_spine_input_scan_streams_project_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    project_dir = input_dir / "lake_project"
    nested = project_dir / "MicrocosmVerifierLab"
    nested.mkdir(parents=True)
    (input_dir / "execution_spine_packet.json").write_text("{}", encoding="utf-8")
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmVerifierLab.Basic\n",
        encoding="utf-8",
    )
    (nested / "Basic.lean").write_text(
        "theorem verifier_smoke : True := by trivial\n",
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
        for path in spine._input_paths(input_dir, include_negative=False)
    ] == [
        "execution_spine_packet.json",
        "lake_project/lakefile.lean",
        "lake_project/MicrocosmVerifierLab/Basic.lean",
    ]


def test_verifier_lab_execution_spine_reuses_built_lake_project_cache(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    project_dir = input_dir / "lake_project"
    nested = project_dir / "MicrocosmProofWitness"
    nested.mkdir(parents=True)
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmProofWitness.Basic\n",
        encoding="utf-8",
    )
    lean_file = nested / "Basic.lean"
    lean_file.write_text("theorem verifier_smoke : True := by trivial\n", encoding="utf-8")
    monkeypatch.setattr(spine, "_LAKE_PROJECT_BUILD_CACHE", {})
    monkeypatch.setattr(spine, "_LAKE_PROJECT_BUILD_CACHE_HOLDERS", [])

    first_root = tmp_path / "first"
    first_root.mkdir()
    first_project = spine._copy_project_to_temp(input_dir, first_root)
    build_marker = first_project / ".lake/build.stamp"
    build_marker.parent.mkdir(parents=True)
    build_marker.write_text("built\n", encoding="utf-8")
    spine._remember_built_lake_project(
        input_dir,
        first_project,
        build_result={
            "argv": ["lake", "build", "MicrocosmProofWitness"],
            "cwd_name": first_project.name,
            "return_code": 0,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
        },
    )

    second_root = tmp_path / "second"
    second_root.mkdir()
    second_project = spine._copy_project_to_temp(input_dir, second_root)

    assert (second_project / ".lake/build.stamp").read_text(encoding="utf-8") == "built\n"
    lean_file.write_text(
        "theorem verifier_smoke_changed : True := by trivial\n",
        encoding="utf-8",
    )
    third_root = tmp_path / "third"
    third_root.mkdir()
    third_project = spine._copy_project_to_temp(input_dir, third_root)
    assert not (third_project / ".lake/build.stamp").exists()


def test_verifier_lab_execution_spine_reuses_lake_build_result_cache(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    project_dir = input_dir / "lake_project"
    nested = project_dir / "MicrocosmProofWitness"
    nested.mkdir(parents=True)
    (input_dir / "execution_spine_packet.json").write_text("{}", encoding="utf-8")
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmProofWitness.Basic\n",
        encoding="utf-8",
    )
    (nested / "Basic.lean").write_text(
        "theorem verifier_smoke : True := by trivial\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(spine, "_LAKE_PROJECT_BUILD_CACHE", {})
    monkeypatch.setattr(spine, "_LAKE_PROJECT_BUILD_CACHE_HOLDERS", [])
    monkeypatch.setattr(spine, "_LAKE_PROJECT_BUILD_RESULT_CACHE", {})

    first_root = tmp_path / "first"
    first_root.mkdir()
    first_project = spine._copy_project_to_temp(input_dir, first_root)
    build_result = {
        "argv": ["lake", "build", "MicrocosmProofWitness"],
        "cwd_name": first_project.name,
        "return_code": 0,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "timed_out": False,
        "stdout_stderr_in_receipt": False,
    }
    spine._remember_built_lake_project(
        input_dir,
        first_project,
        build_result=build_result,
    )

    second_root = tmp_path / "second"
    second_root.mkdir()
    second_project = spine._copy_project_to_temp(input_dir, second_root)
    cached_result = spine._cached_lake_project_build_result(
        input_dir,
        project_dir=second_project,
    )

    assert cached_result is not None
    assert cached_result["return_code"] == 0
    assert cached_result["cwd_name"] == second_project.name
    assert cached_result["cache_status"] == "built_lake_project_reused"


def test_verifier_lab_execution_spine_batches_expected_positive_transitions(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    packet = json.loads((EXPORTED_BUNDLE / "execution_spine_packet.json").read_text())
    project_dir = tmp_path / "lake_project"
    project_dir.mkdir()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(
        argv: list[str],
        *,
        cwd: Path,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        calls.append(tuple(argv))
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": 0 if argv[-1] == "PositiveTransitionBatch.lean" else 1,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
        }

    monkeypatch.setattr(spine, "_TRANSITION_EXECUTION_CACHE", {})
    monkeypatch.setattr(spine, "_run_command", fake_run_command)

    receipts = spine._execute_transitions(
        packet["transition_candidates"],
        project_dir=project_dir,
        findings=[],
        observed={},
    )

    assert [receipt.accepted for receipt in receipts] == [
        True,
        True,
        False,
        True,
        False,
        True,
    ]
    assert calls[0] == ("lake", "env", "lean", "PositiveTransitionBatch.lean")
    assert set(calls[1:]) == {
        ("lake", "env", "lean", "baseline_add_comm_missing_premise.lean"),
        ("lake", "env", "lean", "residual_unsolved_unknown_premise.lean"),
    }


def test_verifier_lab_execution_spine_runs_lean_cp2_and_evolve(
    verifier_spine_fixture_run: tuple[dict[str, Any], Path],
) -> None:
    result, out = verifier_spine_fixture_run

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["authority_counters"]["transition_count"] == 6
    assert result["authority_counters"]["accepted_transition_count"] == 4
    assert result["authority_counters"]["residual_transition_count"] == 2
    assert result["authority_counters"]["cp2_translation_count"] == 1
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 1
    assert result["authority_counters"]["evolve_candidate_count"] == 1
    assert result["authority_counters"]["evolve_accepted_count"] == 1
    assert result["authority_counters"]["oracle_forward_success_increment_count"] == 0
    assert result["authority_counters"]["provider_results_counted"] == 0
    assert result["authority_counters"]["proof_body_export_count"] == 0
    assert result["authority_counters"]["source_mutation_count"] == 0

    claim_separation = result["claim_separation"]
    assert len(claim_separation["lean_verified"]) == 4
    assert len(claim_separation["provider_suggested"]) == 1
    assert len(claim_separation["oracle_compared"]) == 1
    assert len(claim_separation["cp2_translated"]) == 1
    assert len(claim_separation["retrieval_miss"]) == 1
    assert len(claim_separation["evolve_accepted"]) == 1
    assert all(row["proof_body_exported"] is False for row in result["transition_trace"])
    assert all(row["stdout_stderr_in_receipt"] is False for row in result["transition_trace"])
    assert all(row["provider_visible"] is False for row in result["transition_trace"])
    assert all(row["oracle_visible"] is False for row in result["transition_trace"])
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert all(
        ref.startswith("fixtures/first_wave/verifier_lab_execution_spine/input/")
        for ref in result["public_runtime_refs"]
    )

    board_path = out / "verifier_lab_execution_spine_board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    assert board["lean_verified_count"] == 4
    assert board["cp2_downstream_effect_count"] == 1
    assert board["evolve_accepted_count"] == 1


def test_verifier_lab_execution_spine_bundle_is_public_structured(
    verifier_spine_bundle_run: tuple[dict[str, Any], Path, list[str]],
) -> None:
    result, _out, _argv = verifier_spine_bundle_run

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_verifier_lab_execution_spine_bundle"
    assert result["bundle_id"] == "public_verifier_lab_execution_spine_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["authority_counters"]["accepted_transition_count"] == 4
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 1
    assert result["authority_counters"]["evolve_accepted_count"] == 1
    assert result["source_module_imports"]["status"] == "pass"
    assert result["source_module_imports"]["module_count"] == 5
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 5
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["body_copied_material_count"] == 5
    assert result["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert all(
        ref.startswith(
            "examples/verifier_lab_execution_spine/"
            "exported_verifier_lab_execution_spine_bundle/"
        )
        for ref in result["public_runtime_refs"]
    )


def test_verifier_lab_execution_spine_exported_bundle_uses_standalone_contract(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fail_run_command(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("exported bundle should not spawn Lean or Lake")

    monkeypatch.setattr(spine, "_run_command", fail_run_command)

    result = run_execution_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/verifier_lab_execution_spine",
        command="pytest standalone exported verifier execution spine",
    )

    assert result["status"] == "pass"
    assert result["execution_witness_mode"] == "standalone_exported_receipt_contract"
    assert result["tool_versions"]["standalone_exported_receipt_contract"] is True
    assert result["lake_project_build"]["skipped"] is True
    assert result["lake_project_build"]["skip_reason"] == (
        "standalone_exported_receipt_contract"
    )
    assert result["authority_counters"]["transition_count"] == 6
    assert result["authority_counters"]["accepted_transition_count"] == 4
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 1
    assert result["authority_counters"]["evolve_accepted_count"] == 1
    assert all(row["lean_return_code"] in {0, 1} for row in result["transition_trace"])
    assert all(row["proof_body_exported"] is False for row in result["transition_trace"])


def test_verifier_lab_execution_spine_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = (
        public_root
        / "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle"
    )
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(EXPORTED_BUNDLE, bundle)

    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_execution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/verifier_lab_execution_spine",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_imports"]["status"] == "blocked"
    assert result["source_module_imports"]["module_count"] == 5
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["source_open_body_imports"]["body_material_count"] == 5
    digest_findings = [
        row
        for row in result["source_module_imports"]["findings"]
        if row["error_code"] == "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_DIGEST_MISMATCH"
    ]
    assert len(digest_findings) == 1
    assert digest_findings[0]["subject_id"].endswith(
        "source_modules/microcosm_core/organs/verifier_lab_execution_spine.py"
    )
    assert digest_findings[0]["subject_kind"] == "source_module"


def test_verifier_lab_execution_spine_bundle_card_reuses_fresh_receipt(
    capsys: Any,
    monkeypatch: Any,
    verifier_spine_bundle_run: tuple[dict[str, Any], Path, list[str]],
) -> None:
    _result, out, argv = verifier_spine_bundle_run

    assert main(argv) == 0
    first_stdout = capsys.readouterr().out
    first_card = json.loads(first_stdout)

    assert len(first_stdout.encode("utf-8")) < 5000
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["input_mode"] == "exported_verifier_lab_execution_spine_bundle"
    assert first_card["execution_summary"]["transition_count"] == 6
    assert first_card["execution_summary"]["accepted_transition_count"] == 4
    assert first_card["execution_summary"]["cp2_downstream_effect_count"] == 1
    assert first_card["execution_summary"]["evolve_accepted_count"] == 1
    assert first_card["source_open_body_import_summary"]["status"] == "pass"
    assert first_card["source_open_body_import_summary"]["body_material_count"] == 5
    assert first_card["source_open_body_import_summary"]["body_text_exported"] is False
    assert first_card["negative_case_coverage"]["expected_negative_case_count"] == 0
    assert first_card["negative_case_coverage"]["missing_negative_case_count"] == 0
    assert first_card["secret_exclusion_summary"]["blocking_hit_count"] == 0
    assert first_card["receipt_summary"]["receipt_count"] == 1
    assert first_card["no_export_guards"]["transition_trace_exported"] is False
    assert first_card["no_export_guards"]["claim_separation_exported"] is False
    assert first_card["no_export_guards"]["receipt_paths_exported"] is False

    card_keys = set(_walk_keys(first_card))
    assert "transition_trace" not in card_keys
    assert "claim_separation" not in card_keys
    assert "receipt_paths" not in card_keys
    assert "findings" not in card_keys
    assert "anti_claim" not in card_keys
    assert "body_material_ids" not in card_keys
    assert "source_manifest_refs" not in card_keys

    full_receipt = json.loads((out / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))
    assert full_receipt["status"] == "pass"
    assert full_receipt["transition_trace"][0]["problem_id"] == "closed_nat_mod_public"
    assert "claim_separation" in full_receipt
    assert full_receipt["source_open_body_imports"]["body_material_count"] == 5

    def fail_build_result(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh exported-bundle card should reuse the receipt")

    monkeypatch.setattr(spine, "_build_result", fail_build_result)

    assert main(argv) == 0
    second_stdout = capsys.readouterr().out
    second_card = json.loads(second_stdout)

    assert len(second_stdout.encode("utf-8")) < 5000
    assert second_card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert second_card["execution_summary"] == first_card["execution_summary"]
    assert second_card["source_open_body_import_summary"] == first_card[
        "source_open_body_import_summary"
    ]


def test_verifier_lab_execution_spine_receipts_are_transparent_without_bodies(
    verifier_spine_fixture_run: tuple[dict[str, Any], Path],
) -> None:
    _result, out = verifier_spine_fixture_run

    receipt_file = out / "verifier_lab_execution_spine_validation_receipt.json"
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
    assert payload["transition_trace"][0]["problem_id"] == "closed_nat_mod_public"
    assert payload["transition_trace"][0]["lean_return_code"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["receipts_include_proof_bodies"] is False
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


def test_verifier_lab_execution_spine_source_module_manifest_is_exact_public_body_floor() -> None:
    manifest_path = EXPORTED_BUNDLE / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_imports = validate_source_module_imports(
        EXPORTED_BUNDLE,
        public_root=MICROCOSM_ROOT,
    )

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 5
    assert source_imports["status"] == "pass"
    assert source_imports["module_count"] == 5

    module_ids = {row["module_id"] for row in source_imports["modules"]}
    assert "verifier_lab_execution_spine_source_body_import" in module_ids
    assert "execution_spine_basic_lean_body_import" in module_ids
    for row in manifest["modules"]:
        source_path = MICROCOSM_ROOT / str(row["source_ref"]).removeprefix(
            "microcosm-substrate/"
        )
        target_path = MICROCOSM_ROOT / str(row["target_ref"]).removeprefix(
            "microcosm-substrate/"
        )
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["material_class"] in {
            "public_macro_tool_body",
            "public_macro_proof_body",
        }
        assert source_path.read_bytes() == target_path.read_bytes()
