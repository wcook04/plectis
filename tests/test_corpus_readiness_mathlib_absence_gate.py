from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.corpus_readiness_mathlib_absence_gate import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SOURCE_PATTERN_IDS,
    main,
    run,
    run_projection_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input"
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle"
)
SOURCE_ARTIFACT_REFS = [
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
]
PRIVATE_HOME_PREFIX = "/" + "Users" + "/"
OPERATOR_HOME_SAMPLE = PRIVATE_HOME_PREFIX + "willcook"


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


def test_corpus_readiness_mathlib_absence_gate_covers_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["source_pattern_ids"] == SOURCE_PATTERN_IDS
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["mathlib_lake_project_import_available"] is False
    assert result["translation_smoke_only_ids"] == ["miniF2F_lean3_annex"]
    assert result["absent_corpus_ids"] == [
        "LeanDojo",
        "Pantograph",
        "ProofNet",
        "PutnamBench_lean4",
        "mathlib",
        "miniF2F_lean4_mathlib_package",
    ]
    assert result["corpus_count"] == 7
    assert result["consumer_case_count"] == 7
    assert result["allowed_case_ids"] == ["miniF2F_lean3_translation_smoke_allowed"]
    assert result["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_import_blocked_until_probe",
        "miniF2F_lean4_mathlib_search_blocked_absent",
        "pantograph_state_search_blocked_absent",
        "proofnet_blocked_absent",
        "putnambench_lean4_blocked_absent",
    ]
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["corpus_readiness_status"] == (
        "real_lean_std_corpus_readiness_and_mathlib_absence_boundary"
    )
    assert result["toolchain_boundary_status"] == "real_lean_4_29_1_std_mathlib_absence_probe"
    assert result["body_in_receipt"] is False
    assert result["source_digests"][
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json"
    ] == "sha256:c413608118229bea32062ce9b8b5af393bcd5f63bbf1030983e98ffa6d07778d"
    assert result["readiness_board"]["public_contract"][
        "mathlib_probe_required_before_mathlib_proof_work"
    ] is True
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_corpus_readiness_mathlib_absence_gate_accepts_exported_bundle(
    tmp_path: Path,
) -> None:
    result = run_projection_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_corpus_readiness_bundle"
    assert result["bundle_id"] == "public_corpus_readiness_mathlib_absence_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["mathlib_lake_project_import_available"] is False
    assert result["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_import_blocked_until_probe",
        "miniF2F_lean4_mathlib_search_blocked_absent",
    ]
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["corpus_readiness_status"] == (
        "real_lean_std_corpus_readiness_and_mathlib_absence_boundary"
    )
    assert result["source_module_import_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    assert result["source_modules_pass"] is True
    assert result["receipt_paths"] == [
        "receipts/exported_corpus_readiness_bundle_validation_result.json"
    ]


def test_corpus_readiness_exported_bundle_card_bounds_stdout(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "run-projection-bundle",
            "--input",
            str(EXPORTED_BUNDLE_INPUT),
            "--out",
            str(tmp_path / "receipts"),
            "--card",
        ]
    )
    stdout = capsys.readouterr().out
    card = json.loads(stdout)

    assert exit_code == 0
    assert len(stdout.encode("utf-8")) < 6000
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "exported_corpus_readiness_bundle"
    assert card["counts"]["corpus_count"] == 7
    assert card["counts"]["consumer_case_count"] == 4
    assert card["source_module_import"]["source_modules_pass"] is True
    assert card["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert card["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert card["body_in_receipt"] is False
    assert "readiness_board" not in card
    assert "source_module_imports" not in card
    receipt = tmp_path / card["receipt_paths"][0]
    assert receipt.is_file()


def test_corpus_readiness_exported_source_modules_are_digest_verified() -> None:
    manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    rows = {row["source_ref"]: row for row in manifest["modules"]}
    assert sorted(rows) == SOURCE_ARTIFACT_REFS
    for source_ref in SOURCE_ARTIFACT_REFS:
        source = MICROCOSM_ROOT.parent / source_ref
        target = EXPORTED_BUNDLE_INPUT / rows[source_ref]["path"]
        target_text = target.read_text(encoding="utf-8")
        target_digest = "sha256:" + hashlib.sha256(target_text.encode("utf-8")).hexdigest()
        row = rows[source_ref]
        source_exists = source.is_file()
        relation = row.get("source_to_target_relation")
        row_source_digest = str(row.get("source_sha256", row["sha256"]))
        row_target_digest = str(row.get("target_sha256", row["sha256"]))
        row_digest = str(row["sha256"])
        if not row_source_digest.startswith("sha256:"):
            row_source_digest = f"sha256:{row_source_digest}"
        if not row_target_digest.startswith("sha256:"):
            row_target_digest = f"sha256:{row_target_digest}"
        if not row_digest.startswith("sha256:"):
            row_digest = f"sha256:{row_digest}"
        source_digest = (
            "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
            if source_exists
            else row_source_digest
            if relation == "verified_public_safe_private_path_rewrite"
            else target_digest
        )
        assert row_source_digest == source_digest
        assert row_target_digest == target_digest
        assert row_digest == target_digest
        if relation == "verified_public_safe_private_path_rewrite":
            assert source_digest != target_digest
            assert row["verification_mode"] == "verified_light_edit_recipe"
            assert row["public_safe_transform"] == "private_absolute_path_rewrite_only"
            assert OPERATOR_HOME_SAMPLE not in target_text
        else:
            if source_exists:
                assert target.read_bytes() == source.read_bytes()
            assert row.get("source_to_target_relation", "exact_copy") == "exact_copy"
        assert rows[source_ref]["body_copied"] is True
        assert rows[source_ref]["body_in_receipt"] is False


def test_corpus_readiness_exported_receipt_omits_source_bodies(tmp_path: Path) -> None:
    result = run_projection_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )
    receipt_path = tmp_path / result["receipt_paths"][0]
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert payload["source_module_import_count"] == 4
    assert payload["copied_source_artifact_count"] == 4
    assert payload["source_modules_pass"] is True
    assert payload["body_in_receipt"] is False
    assert "import Mathlib" not in receipt_path.read_text(encoding="utf-8")
    for row in payload["source_module_imports"]:
        assert row["exists"] is True
        assert row["digest_match"] is True
        assert row["body_in_receipt"] is False
        assert row["source_ref"] in SOURCE_ARTIFACT_REFS


def test_corpus_readiness_receipts_are_real_substrate_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
    )

    result = run(
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input",
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert PRIVATE_HOME_PREFIX not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == (
            "copied_non_secret_macro_body_with_provenance"
        )
        assert payload["body_in_receipt"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert payload["secret_exclusion_scan"]["real_substrate_default"] is True
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
