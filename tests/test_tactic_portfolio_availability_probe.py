from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import tactic_portfolio_availability_probe
from microcosm_core.organs.tactic_portfolio_availability_probe import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_availability_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle"
)


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _sha256_prefixed(value: str) -> str:
    return value if value.startswith("sha256:") else f"sha256:{value}"


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


def test_tactic_portfolio_availability_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/tactic_portfolio_availability_probe_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["tactic_count"] == 8
    assert result["compile_status_counts"] == {
        "compile_pass": 7,
        "environment_fail": 1,
    }
    assert result["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]
    assert result["unavailable_tactic_ids"] == ["aesop"]
    assert result["mathlib_dependent_tactic_ids"] == ["aesop"]
    assert result["mathlib_lake_project_import_available"] is False
    assert result["mathlib_absence_gate_enforced"] is True
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["tactic_availability_status"] == (
        "real_lean_std_tactic_affordance_probe_rows"
    )
    assert result["probe_source_body_status"] == (
        "copied_non_secret_lean_probe_source_bodies_with_digest_verification"
    )
    assert result["source_artifact_count"] == 13
    assert result["copied_source_artifact_count"] == 13
    assert result["source_body_artifact_count"] == 3
    assert result["copied_source_body_artifact_count"] == 3
    assert all(row["body_copied"] for row in result["source_artifact_imports"])
    assert any(
        row["source_ref"]
        == "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json"
        and row["body_copied"]
        for row in result["source_artifact_imports"]
    )
    assert result["probe_source_digest_refs"][
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/rfl.lean"
    ] == "sha256:2d2b1800deb875c660693bd87af0715752316132da8a747c13487577feddc696"
    assert result["body_in_receipt"] is False
    assert result["source_digests"][
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json"
    ] == "sha256:20fdef8a53401f2bb21483002730895ca0295d2170bf148e8c328c041d8524c3"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["real_substrate_default"] is True
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        for code in codes:
            assert code in result["observed_negative_cases"][case_id]


def test_tactic_portfolio_availability_receipts_are_public_relative_and_real_substrate(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/tactic_portfolio_availability_probe",
        public_root / "fixtures/first_wave/tactic_portfolio_availability_probe",
    )
    result = run(
        public_root / "fixtures/first_wave/tactic_portfolio_availability_probe/input",
        public_root / "receipts/first_wave/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_path in result["receipt_paths"]:
        assert not Path(receipt_path).is_absolute()
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == (
            "copied_non_secret_macro_body_with_provenance"
        )
        assert payload["source_artifact_count"] == 13
        assert payload["copied_source_artifact_count"] == 13
        assert payload["source_body_artifact_count"] == 3
        assert payload["copied_source_body_artifact_count"] == 3
        assert all(row["body_copied"] for row in payload["source_artifact_imports"])
        assert payload["body_in_receipt"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_tactic_portfolio_availability_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/tactic_portfolio_availability_probe",
        public_root / "examples/tactic_portfolio_availability_probe",
    )
    result = run_availability_bundle(
        public_root
        / "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle",
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_tactic_portfolio_availability_bundle"
    assert result["bundle_id"] == "tactic_portfolio_availability_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["tactic_count"] == 8
    assert result["mathlib_absence_gate_enforced"] is True
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["tactic_availability_status"] == (
        "real_lean_std_tactic_affordance_probe_rows"
    )
    assert result["source_artifact_count"] == 13
    assert result["copied_source_artifact_count"] == 13
    assert result["source_body_artifact_count"] == 3
    assert result["copied_source_body_artifact_count"] == 3
    assert all(row["body_copied"] for row in result["source_artifact_imports"])
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["receipt_paths"] == [
        (
            "receipts/runtime_shell/demo_project/organs/"
            "tactic_portfolio_availability_probe/"
            "exported_tactic_portfolio_availability_bundle_validation_result.json"
        )
    ]


def test_tactic_portfolio_availability_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    out_dir = tmp_path / "bundle-card"
    args = [
        "run-availability-bundle",
        "--input",
        str(EXPORTED_BUNDLE_INPUT),
        "--out",
        str(out_dir),
    ]
    assert main(args) == 0
    assert not capsys.readouterr().out

    def fail_rebuild(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh availability bundle receipt should be reused")

    monkeypatch.setattr(
        tactic_portfolio_availability_probe,
        "_build_result",
        fail_rebuild,
    )
    assert main([*args, "--card"]) == 0
    card = json.loads(capsys.readouterr().out)
    full_receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text())

    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "exported_tactic_portfolio_availability_bundle"
    assert card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert card["receipt_summary"]["result_receipt_name"] == BUNDLE_RESULT_NAME
    assert card["availability_summary"]["tactic_count"] == 8
    assert card["availability_summary"]["available_tactic_count"] == 7
    assert card["availability_summary"]["unavailable_tactic_count"] == 1
    assert card["source_artifact_summary"]["source_artifact_rows_exported"] is False
    assert card["no_export_guards"]["source_artifact_imports_exported"] is False
    assert "source_artifact_imports" not in card
    assert "anti_claim" not in card
    assert "secret_exclusion_scan" not in card
    assert len(json.dumps(card, sort_keys=True)) < len(
        json.dumps(full_receipt, sort_keys=True)
    )


def test_tactic_portfolio_availability_exported_source_modules_are_digest_verified() -> None:
    manifest = json.loads((EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 13
    assert len(manifest["modules"]) == 13

    repo_root = MICROCOSM_ROOT.parent
    for module in manifest["modules"]:
        source = repo_root / module["source_ref"]
        target = repo_root / module["target_ref"]
        source_digest = _sha256_prefixed(module.get("source_sha256") or module["sha256"])
        target_digest = _sha256_prefixed(module.get("target_sha256") or module["sha256"])
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == source_digest
        assert _sha256(target) == target_digest
        if module["source_to_target_relation"] == "exact_copy":
            assert source_digest == target_digest
        else:
            assert module["source_to_target_relation"] == (
                "verified_public_safe_private_path_rewrite"
            )
            assert source_digest != target_digest
            assert module["verification_mode"] == "verified_light_edit_recipe"
            assert module["public_safe_transform"]["body_text_in_receipt"] is False
            assert Path.home().as_posix() not in target.read_text(encoding="utf-8")
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
