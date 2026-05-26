from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_math_readiness_gate import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SELECTED_PATTERN_IDS,
    main,
    plan_readiness_extensions,
    run,
    run_readiness_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate/input"
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle"
)
PROVER_SMOKE_RUN_REF = "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke"
SOURCE_ARTIFACT_REFS = [
    f"{PROVER_SMOKE_RUN_REF}/corpus_readiness.json",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe.json",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/mathlib_probe.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/trace_state_probe.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/aesop.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/decide.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/grind.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/native_decide.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/omega.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/rfl.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/simp.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/simp_all.lean",
    (
        f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/"
        "tactic_portfolio_availability.json"
    ),
]


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


def test_formal_math_readiness_gate_covers_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["blocked_capabilities"] == ["lean_std_synthetic_core:mathlib"]
    assert "aesop" in result["unavailable_tactic_ids"]
    assert result["premise_count"] == 11
    assert result["route_case_count"] == 5
    assert result["recipe_count"] == 3
    assert result["projection_cell_id"] == "formal_math_readiness_extensions"
    assert result["selected_pattern_ids"] == SELECTED_PATTERN_IDS
    extension = result["readiness_extension_board"]
    assert extension["source_intake_ref"].endswith("#formal_math_readiness_extensions")
    assert extension["projection_status"] == "public_runtime_import_landed"
    assert extension["projection_contract"]["real_substrate_receipt"] is True
    assert extension["projection_contract"]["synthetic_receipt_standin_allowed"] is False
    assert extension["premise_index_projection"]["namespace_counts"] == {
        "Bool": 2,
        "Iff": 3,
        "List": 3,
        "Nat": 3,
    }
    assert extension["premise_index_projection"]["split_eligibility_counts"] == {
        "dev": 11,
        "test": 11,
        "train": 11,
    }
    assert extension["tactic_portfolio_projection"]["available_tactic_count"] == 6
    assert extension["tactic_portfolio_projection"][
        "mathlib_dependent_unavailable_tactic_ids"
    ] == ["aesop"]
    assert extension["target_shape_routing_projection"]["blocked_route_case_ids"] == [
        "mathlib_search_uses_aesop_without_probe"
    ]
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_readiness_gate_accepts_exported_bundle(tmp_path: Path) -> None:
    result = run_readiness_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_formal_math_readiness_bundle"
    assert result["bundle_id"] == "public_formal_math_readiness_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["blocked_capabilities"] == ["lean_std_synthetic_core:mathlib"]
    assert result["readiness_board"]["lean_lake_execution_authorized"] is False
    assert result["readiness_board"]["formal_proof_authority"] is False
    assert result["readiness_extension_board"]["cell_id"] == "formal_math_readiness_extensions"
    assert result["readiness_extension_board"]["target_shape_routing_projection"][
        "blocked_route_case_count"
    ] == 0
    assert result["body_material_status"] == (
        "copied_non_secret_macro_readiness_probe_body_with_provenance"
    )
    assert (
        result["source_module_import_status"]
        == "copied_formal_readiness_source_modules_verified"
    )
    assert result["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["source_modules_pass"] is True
    assert all(row["exists"] is True for row in result["source_module_imports"])
    assert all(row["digest_match"] is True for row in result["source_module_imports"])
    assert result["readiness_extension_board"]["projection_contract"][
        "body_copied"
    ] is True
    assert result["readiness_extension_board"]["source_body_import_projection"][
        "copied_source_artifact_count"
    ] == len(SOURCE_ARTIFACT_REFS)
    assert result["receipt_paths"] == [
        "receipts/exported_formal_math_readiness_bundle_validation_result.json"
    ]


def test_formal_math_readiness_exported_bundle_card_bounds_stdout(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "run-readiness-bundle",
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
    assert card["input_mode"] == "exported_formal_math_readiness_bundle"
    assert card["counts"]["premise_count"] == 11
    assert card["counts"]["route_case_count"] == 4
    assert card["source_module_import"]["source_modules_pass"] is True
    assert card["source_module_import"]["source_module_import_count"] == len(
        SOURCE_ARTIFACT_REFS
    )
    assert card["source_module_import"]["digest_match_count"] == len(
        SOURCE_ARTIFACT_REFS
    )
    assert card["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert card["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert card["body_in_receipt"] is False
    assert "readiness_board" not in card
    assert "readiness_extension_board" not in card
    assert "source_module_imports" not in card
    receipt = tmp_path / card["receipt_paths"][0]
    assert receipt.is_file()


def test_formal_math_readiness_exported_source_modules_are_exact_copies() -> None:
    manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    modules = {row["source_ref"]: row for row in manifest["modules"]}
    assert sorted(modules) == sorted(SOURCE_ARTIFACT_REFS)
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False

    bundle_manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert bundle_manifest["source_module_manifest_ref"] == "source_module_manifest.json"
    assert len(bundle_manifest["copied_macro_body_artifacts"]) == len(
        SOURCE_ARTIFACT_REFS
    )

    for source_ref in SOURCE_ARTIFACT_REFS:
        source = MICROCOSM_ROOT.parent / source_ref
        target = EXPORTED_BUNDLE_INPUT / "source_artifacts" / source_ref
        assert target.is_file()
        source_bytes = source.read_bytes()
        target_bytes = target.read_bytes()
        digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
        assert source_bytes == target_bytes
        assert modules[source_ref]["sha256"] == digest
        assert modules[source_ref]["body_in_receipt"] is False


def test_formal_math_readiness_exported_bundle_receipt_omits_source_bodies(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/formal_math_readiness_gate",
        public_root / "examples/formal_math_readiness_gate",
    )

    result = run_readiness_bundle(
        public_root / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle",
        public_root / "receipts/formal_math_readiness_gate",
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
        assert "import Mathlib" not in text
        assert "\n  trace_state" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["source_modules_pass"] is True
        assert "body_redacted" not in _walk_keys(payload)
        assert "private_state_scan" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_math_readiness_receipts_use_secret_exclusion_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate",
        public_root / "fixtures/first_wave/formal_math_readiness_gate",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_math_readiness_gate/input",
        public_root / "receipts/first_wave/formal_math_readiness_gate",
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
        assert "synthetic redacted proof payload" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "body_redacted" not in _walk_keys(payload)
        assert "private_state_scan" not in _walk_keys(payload)
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
        if payload["schema_version"] == "formal_math_readiness_extension_board_receipt_v1":
            assert payload["cell_id"] == "formal_math_readiness_extensions"
            assert payload["projection_contract"]["body_copied"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_math_readiness_plan_is_non_writing_extension_preview(
    tmp_path: Path,
) -> None:
    result = plan_readiness_extensions(FIXTURE_INPUT, command="pytest")

    assert result["status"] == "pass"
    assert result["schema_version"] == "formal_math_readiness_extension_preview_v1"
    assert result["projection_cell_id"] == "formal_math_readiness_extensions"
    assert result["selected_pattern_ids"] == SELECTED_PATTERN_IDS
    assert result["readiness_extension_board"]["projection_status"] == "public_runtime_import_landed"
    assert result["readiness_extension_board"]["provider_context_projection"][
        "provider_calls_authorized"
    ] is False
    assert not any(tmp_path.iterdir())
