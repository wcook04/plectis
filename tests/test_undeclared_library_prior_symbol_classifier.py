from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import undeclared_library_prior_symbol_classifier
from microcosm_core.organs.undeclared_library_prior_symbol_classifier import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    RUN_SUMMARY_SOURCE_MODULE_ID,
    main,
    run,
    run_symbol_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/undeclared_library_prior_symbol_classifier/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle"
)
RUN_SUMMARY_MODULE_PATH = (
    BUNDLE_INPUT
    / "source_modules/state_sidecars/runs/"
    "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/run_summary.public_normalized.json"
)


def _source_backed_nat_add_comm_observation(input_dir: Path) -> dict[str, Any]:
    copied_run_summary = (
        input_dir
        / "source_modules/state_sidecars/runs/"
        "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/run_summary.public_normalized.json"
    )
    run_summary_path = (
        copied_run_summary if copied_run_summary.is_file() else RUN_SUMMARY_MODULE_PATH
    )
    run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    premise_index = json.loads((input_dir / "premise_index.json").read_text())
    premise_by_id = {
        row["premise_id"]: row for row in premise_index["premises"]
    }
    run_row = next(
        row
        for row in run_summary["problem_results"]
        if row["problem_id"] == "ring2_nat_add_comm"
    )
    retrieval = run_row["premise_retrieval"]
    candidate_ids = retrieval["candidate_premise_ids_used"]
    return {
        "receipt_id": "receipt.ring2_nat_add_comm_out_of_recipe_boundary",
        "problem_id": run_row["problem_id"],
        "lean_status": run_row["lean_compile_status"],
        "candidate_artifact_sha256": run_row["candidate_artifact_sha256"],
        "proof_symbol_refs": [
            premise_by_id[premise_id]["theorem_or_def_name"]
            for premise_id in candidate_ids
        ],
        "allowed_premise_ids": retrieval["extra_retrieved_premise_ids"],
        "cited_unallowed_premise_ids": [],
        "classified_failure_class": "UNDECLARED_LIBRARY_PRIOR",
        "review_outcome": "bridge_escalate",
        "source_observation_ref": {
            "module_id": RUN_SUMMARY_SOURCE_MODULE_ID,
            "problem_id": run_row["problem_id"],
            "allowed_premise_ids_from": "extra_retrieved_premise_ids",
        },
        "source_refs": [
            "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "premise_retrieval_graph_v0/run_summary.json"
        ],
    }


def _copy_fixture_with_source_modules(public_root: Path) -> Path:
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture_root = (
        public_root
        / "fixtures/first_wave/undeclared_library_prior_symbol_classifier"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/undeclared_library_prior_symbol_classifier",
        fixture_root,
    )
    input_dir = fixture_root / "input"
    shutil.copy2(BUNDLE_INPUT / "source_module_manifest.json", input_dir)
    shutil.copytree(BUNDLE_INPUT / "source_modules", input_dir / "source_modules")
    return input_dir


def _refresh_manifest_digest(manifest_path: Path, *, module_id: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = next(row for row in manifest["modules"] if row["module_id"] == module_id)
    target = manifest_path.parent / row["path"]
    data = target.read_bytes()
    row["target_sha256"] = f"sha256:{hashlib.sha256(data).hexdigest()}"
    row["target_line_count"] = target.read_text(encoding="utf-8").count("\n")
    row["target_byte_count"] = len(data)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


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


def test_undeclared_library_prior_symbol_classifier_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/undeclared_library_prior_symbol_classifier",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["premise_count"] == 11
    assert result["classification_count"] == 3
    assert result["undeclared_library_prior_count"] == 1
    assert result["premise_budget_precedence_count"] == 1
    assert result["bridge_escalation_count"] == 1
    assert result["retry_count"] == 1
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["symbol_boundary_status"] == (
        "real_lean_std_symbol_boundary_and_mathlib_absence_context"
    )
    assert result["toolchain_boundary_status"] == "real_lean_4_29_1_std_mathlib_absence_probe"
    assert result["body_in_receipt"] is False
    assert result["source_modules_pass"] is True
    assert result["source_open_body_imports"] == {}
    assert result["source_digests"][
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json"
    ] == "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1"
    assert "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_retrieval_graph_v0/run_summary.json" in result["source_refs"]
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_symbol_classifier_recomputes_source_backed_symbols_not_baked_labels(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    input_dir = _copy_fixture_with_source_modules(public_root)
    observations_path = input_dir / "symbol_observations.json"
    observations = json.loads(observations_path.read_text())
    observations["symbol_observations"][0] = _source_backed_nat_add_comm_observation(
        input_dir
    )
    observations_path.write_text(json.dumps(observations, indent=2) + "\n")

    good = run(
        input_dir,
        public_root / "receipts/first_wave/undeclared_library_prior_symbol_classifier_good",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_good.json",
    )
    assert good["status"] == "pass"
    assert good["source_backed_observation_count"] == 1
    assert good["source_observation_derivation_status"] == "pass"
    assert good["undeclared_library_prior_count"] == 1
    assert good["bridge_escalation_count"] == 1

    premise_index = json.loads((input_dir / "premise_index.json").read_text())
    nat_add_comm = next(
        row
        for row in premise_index["premises"]
        if row["theorem_or_def_name"] == "Nat.add_comm"
    )
    assert nat_add_comm["source_ref"] == (
        "lean-toolchain://leanprover/lean4/v4.29.1/src/lean/Init/Data/Nat/"
        "Lemmas.lean"
    )
    assert nat_add_comm["body_material_status"] == "imported_premise_index_row"
    mutated_row = observations["symbol_observations"][0]
    assert mutated_row["proof_symbol_refs"] == ["Nat.add_comm"]
    assert mutated_row["allowed_premise_ids"] == [
        "premise_nat_add_assoc",
        "premise_nat_add_zero",
    ]
    assert mutated_row["classified_failure_class"] == "UNDECLARED_LIBRARY_PRIOR"
    assert mutated_row["review_outcome"] == "bridge_escalate"
    mutated_row["proof_symbol_refs"] = ["Nat.add_comm_mutated"]
    observations_path.write_text(json.dumps(observations, indent=2) + "\n")

    mutated = run(
        input_dir,
        public_root
        / "receipts/first_wave/undeclared_library_prior_symbol_classifier_mutated",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_mutated.json",
    )

    assert mutated["status"] == "blocked"
    assert mutated["missing_negative_cases"] == []
    assert mutated["classification_count"] == good["classification_count"]
    assert mutated["source_backed_observation_count"] == 0
    assert mutated["source_observation_derivation_status"] == "blocked"
    assert mutated["premise_count"] == good["premise_count"]
    assert mutated["undeclared_library_prior_count"] == 0
    assert mutated["bridge_escalation_count"] == 0
    assert mutated["premise_budget_precedence_count"] == 1
    assert "SYMBOL_CLASSIFIER_SOURCE_OBSERVATION_DERIVATION_MISMATCH" in mutated[
        "error_codes"
    ]

    mutated_classification = next(
        row
        for row in mutated["classification_rows"]
        if row["receipt_id"] == "receipt.ring2_nat_add_comm_out_of_recipe_boundary"
    )
    assert mutated_classification["observed_qualified_symbols"] == [
        "Nat.add_comm_mutated"
    ]
    assert mutated_classification["observed_known_symbols"] == []
    assert mutated_classification["undeclared_library_prior_symbols"] == []
    assert mutated_classification["computed_failure_class"] == "NONE"
    assert mutated_classification["computed_review_outcome"] == "accept_as_advisory"
    assert mutated_classification["asserted_failure_class"] == (
        "UNDECLARED_LIBRARY_PRIOR"
    )
    assert mutated_classification["asserted_review_outcome"] == "bridge_escalate"
    assert mutated_classification["source_observation_status"] == "blocked"
    assert mutated_classification["source_observation_mismatches"] == [
        {
            "field": "proof_symbol_refs",
            "expected": ["Nat.add_comm"],
            "actual": ["Nat.add_comm_mutated"],
        }
    ]


def test_symbol_classifier_rejects_wrong_assertion_on_real_source_symbol(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    input_dir = _copy_fixture_with_source_modules(public_root)
    observations_path = input_dir / "symbol_observations.json"
    observations = json.loads(observations_path.read_text())
    observations["symbol_observations"][0] = _source_backed_nat_add_comm_observation(
        input_dir
    )
    wrong_row = observations["symbol_observations"][0]
    wrong_row["classified_failure_class"] = "NONE"
    wrong_row["review_outcome"] = "accept_as_advisory"
    observations_path.write_text(json.dumps(observations, indent=2) + "\n")

    result = run(
        input_dir,
        public_root
        / "receipts/first_wave/undeclared_library_prior_symbol_classifier_wrong",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_wrong.json",
    )

    assert result["status"] == "blocked"
    assert result["missing_negative_cases"] == []
    assert result["source_backed_observation_count"] == 1
    assert result["source_observation_derivation_status"] == "pass"
    assert result["undeclared_library_prior_count"] == 1
    assert result["bridge_escalation_count"] == 1
    assert "SYMBOL_CLASSIFIER_ASSERTED_CLASSIFICATION_MISMATCH" in result[
        "error_codes"
    ]
    wrong_classification = next(
        row
        for row in result["classification_rows"]
        if row["receipt_id"] == "receipt.ring2_nat_add_comm_out_of_recipe_boundary"
    )
    assert wrong_classification["observed_known_symbols"] == ["Nat.add_comm"]
    assert wrong_classification["undeclared_library_prior_symbols"] == [
        "Nat.add_comm"
    ]
    assert wrong_classification["computed_failure_class"] == (
        "UNDECLARED_LIBRARY_PRIOR"
    )
    assert wrong_classification["computed_review_outcome"] == "bridge_escalate"
    assert wrong_classification["asserted_failure_class"] == "NONE"
    assert wrong_classification["asserted_review_outcome"] == "accept_as_advisory"
    assert wrong_classification["source_observation_status"] == "pass"
    findings = [
        row
        for row in result["findings"]
        if row["error_code"] == "SYMBOL_CLASSIFIER_ASSERTED_CLASSIFICATION_MISMATCH"
    ]
    assert [row["negative_case_id"] for row in findings] == [
        "symbol_observation_assertion_floor"
    ]


def test_symbol_classifier_premise_index_symbol_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    input_dir = _copy_fixture_with_source_modules(public_root)
    observations_path = input_dir / "symbol_observations.json"
    observations = json.loads(observations_path.read_text())
    observations["symbol_observations"][0] = _source_backed_nat_add_comm_observation(
        input_dir
    )
    observations_path.write_text(json.dumps(observations, indent=2) + "\n")

    good = run(
        input_dir,
        public_root
        / "receipts/first_wave/undeclared_library_prior_symbol_classifier_good",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_good.json",
    )
    good_classification = next(
        row
        for row in good["classification_rows"]
        if row["receipt_id"] == "receipt.ring2_nat_add_comm_out_of_recipe_boundary"
    )
    assert good["status"] == "pass"
    assert good_classification["observed_known_symbols"] == ["Nat.add_comm"]
    assert good_classification["undeclared_library_prior_symbols"] == [
        "Nat.add_comm"
    ]
    assert good_classification["computed_failure_class"] == "UNDECLARED_LIBRARY_PRIOR"
    assert good_classification["computed_review_outcome"] == "bridge_escalate"
    assert good_classification["source_observation_status"] == "pass"

    premise_index_path = input_dir / "premise_index.json"
    premise_index = json.loads(premise_index_path.read_text())
    premise_row = next(
        row
        for row in premise_index["premises"]
        if row["premise_id"] == "premise_nat_add_comm"
    )
    premise_row["theorem_or_def_name"] = "Nat.add_comm_perturbed"
    premise_index_path.write_text(json.dumps(premise_index, indent=2) + "\n")

    perturbed = run(
        input_dir,
        public_root
        / "receipts/first_wave/undeclared_library_prior_symbol_classifier_perturbed",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_perturbed.json",
    )
    perturbed_classification = next(
        row
        for row in perturbed["classification_rows"]
        if row["receipt_id"] == "receipt.ring2_nat_add_comm_out_of_recipe_boundary"
    )

    assert perturbed["status"] == "blocked"
    assert perturbed["classification_count"] == good["classification_count"]
    assert perturbed["source_backed_observation_count"] == 0
    assert perturbed["source_observation_derivation_status"] == "blocked"
    assert perturbed["undeclared_library_prior_count"] == 0
    assert perturbed["bridge_escalation_count"] == 0
    assert "SYMBOL_CLASSIFIER_SOURCE_OBSERVATION_DERIVATION_MISMATCH" in perturbed[
        "error_codes"
    ]
    assert "SYMBOL_CLASSIFIER_ASSERTED_CLASSIFICATION_MISMATCH" in perturbed[
        "error_codes"
    ]
    assert perturbed_classification["observed_qualified_symbols"] == ["Nat.add_comm"]
    assert perturbed_classification["observed_known_symbols"] == []
    assert perturbed_classification["undeclared_library_prior_symbols"] == []
    assert perturbed_classification["computed_failure_class"] == "NONE"
    assert perturbed_classification["computed_review_outcome"] == "accept_as_advisory"
    assert perturbed_classification["asserted_failure_class"] == (
        "UNDECLARED_LIBRARY_PRIOR"
    )
    assert perturbed_classification["asserted_review_outcome"] == "bridge_escalate"
    assert perturbed_classification["source_observation_status"] == "blocked"
    assert perturbed_classification["source_observation_mismatches"] == [
        {
            "field": "proof_symbol_refs",
            "expected": ["Nat.add_comm_perturbed"],
            "actual": ["Nat.add_comm"],
        }
    ]


def test_symbol_classifier_wrong_assertion_tracks_source_symbol_perturbation(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    input_dir = _copy_fixture_with_source_modules(public_root)
    observations_path = input_dir / "symbol_observations.json"
    observations = json.loads(observations_path.read_text())
    wrong_row = _source_backed_nat_add_comm_observation(input_dir)
    wrong_row["classified_failure_class"] = "NONE"
    wrong_row["review_outcome"] = "accept_as_advisory"
    observations["symbol_observations"][0] = wrong_row
    observations_path.write_text(json.dumps(observations, indent=2) + "\n")

    wrong = run(
        input_dir,
        public_root
        / "receipts/first_wave/undeclared_library_prior_symbol_classifier_wrong",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_wrong.json",
    )
    wrong_classification = next(
        row
        for row in wrong["classification_rows"]
        if row["receipt_id"] == "receipt.ring2_nat_add_comm_out_of_recipe_boundary"
    )
    assert wrong["status"] == "blocked"
    assert wrong["source_observation_derivation_status"] == "pass"
    assert "SYMBOL_CLASSIFIER_ASSERTED_CLASSIFICATION_MISMATCH" in wrong[
        "error_codes"
    ]
    assert wrong_classification["observed_known_symbols"] == ["Nat.add_comm"]
    assert wrong_classification["undeclared_library_prior_symbols"] == [
        "Nat.add_comm"
    ]
    assert wrong_classification["computed_failure_class"] == "UNDECLARED_LIBRARY_PRIOR"
    assert wrong_classification["asserted_failure_class"] == "NONE"

    run_summary_path = (
        input_dir
        / "source_modules/state_sidecars/runs/"
        "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/run_summary.public_normalized.json"
    )
    run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    run_row = next(
        row
        for row in run_summary["problem_results"]
        if row["problem_id"] == "ring2_nat_add_comm"
    )
    run_row["premise_retrieval"]["candidate_premise_ids_used"] = [
        "premise_nat_add_zero"
    ]
    run_summary_path.write_text(json.dumps(run_summary, indent=2) + "\n")
    _refresh_manifest_digest(
        input_dir / "source_module_manifest.json",
        module_id=RUN_SUMMARY_SOURCE_MODULE_ID,
    )

    perturbed_observations = json.loads(observations_path.read_text())
    perturbed_row = _source_backed_nat_add_comm_observation(input_dir)
    perturbed_row["classified_failure_class"] = "NONE"
    perturbed_row["review_outcome"] = "accept_as_advisory"
    perturbed_observations["symbol_observations"][0] = perturbed_row
    observations_path.write_text(json.dumps(perturbed_observations, indent=2) + "\n")

    perturbed = run(
        input_dir,
        public_root
        / "receipts/first_wave/undeclared_library_prior_symbol_classifier_perturbed",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_perturbed.json",
    )
    perturbed_classification = next(
        row
        for row in perturbed["classification_rows"]
        if row["receipt_id"] == "receipt.ring2_nat_add_comm_out_of_recipe_boundary"
    )

    assert perturbed["status"] == "blocked"
    assert perturbed["source_backed_observation_count"] == 1
    assert perturbed["source_observation_derivation_status"] == "pass"
    assert "SYMBOL_CLASSIFIER_ASSERTED_CLASSIFICATION_MISMATCH" not in perturbed[
        "error_codes"
    ]
    assert perturbed_classification["observed_qualified_symbols"] == ["Nat.add_zero"]
    assert perturbed_classification["observed_known_symbols"] == ["Nat.add_zero"]
    assert perturbed_classification["allowed_premise_ids"] == [
        "premise_nat_add_assoc",
        "premise_nat_add_zero",
    ]
    assert perturbed_classification["undeclared_library_prior_symbols"] == []
    assert perturbed_classification["computed_failure_class"] == "NONE"
    assert perturbed_classification["computed_review_outcome"] == "accept_as_advisory"
    assert perturbed_classification["asserted_failure_class"] == "NONE"
    assert perturbed_classification["asserted_review_outcome"] == "accept_as_advisory"
    assert perturbed_classification["source_observation_status"] == "pass"
    assert perturbed_classification["source_observation_mismatches"] == []


def test_symbol_classifier_receipts_are_real_substrate_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/undeclared_library_prior_symbol_classifier",
        public_root / "fixtures/first_wave/undeclared_library_prior_symbol_classifier",
    )

    result = run(
        public_root / "fixtures/first_wave/undeclared_library_prior_symbol_classifier/input",
        public_root / "receipts/first_wave/undeclared_library_prior_symbol_classifier",
        command="pytest",
        acceptance_out=(
            public_root
            / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_fixture_acceptance.json"
        ),
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        assert "macro-private:formal-lab" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
        assert payload["body_in_receipt"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["secret_exclusion_scan"]["real_substrate_default"] is True
        assert "proof_body" not in _walk_keys(payload)
        assert "private_source_ref" not in _walk_keys(payload)


def test_symbol_classifier_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_symbol_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/undeclared_library_prior_symbol_classifier",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_symbol_classifier_bundle"
    assert result["bundle_id"] == "undeclared_library_prior_symbol_classifier_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["classification_count"] == 3
    assert result["premise_count"] == 11
    assert result["undeclared_library_prior_count"] == 1
    assert result["premise_budget_precedence_count"] == 1
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["symbol_boundary_status"] == (
        "real_lean_std_symbol_boundary_and_mathlib_absence_context"
    )
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
    assert result["source_modules_pass"] is True
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 6
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 6
    imported_ids = set(result["source_open_body_imports"]["body_material_ids"])
    assert "provider_receipt_reducer_source_body_import" in imported_ids
    assert "provider_batch_receipt_reduction_matrix_body_import" in imported_ids
    assert all(row["body_in_receipt"] is False for row in result["source_modules"])
    assert all(row["digest_matches"] is True for row in result["source_modules"])
    assert all(row["missing_required_anchors"] == [] for row in result["source_modules"])
    normalized_rows = [
        row
        for row in result["source_modules"]
        if row["source_to_target_relation"]
        == "source_faithful_public_safe_path_normalized_copy"
    ]
    assert {row["module_id"] for row in normalized_rows} == {
        "ring2_premise_index_state_body_import",
        "ring2_premise_retrieval_run_summary_body_import",
    }
    for path in BUNDLE_INPUT.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md", ".py"}:
            text = path.read_text(encoding="utf-8")
            assert "/Users/example" not in text
            assert "SYNTHETIC_PROVIDER_PAYLOAD_BODY_SENTINEL" not in text


def test_symbol_classifier_exported_bundle_blocks_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle_input = (
        public_root
        / "examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle_input)
    manifest_path = bundle_input / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_module = manifest["modules"][0]
    first_module["sha256"] = "sha256:" + ("0" * 64)
    first_module["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_symbol_bundle(
        bundle_input,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/undeclared_library_prior_symbol_classifier",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 5
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["source_open_body_imports"]["body_material_count"] == 5
    assert "SYMBOL_CLASSIFIER_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    source_findings = [
        row
        for row in result["findings"]
        if row["error_code"] == "SYMBOL_CLASSIFIER_SOURCE_MODULE_DIGEST_MISMATCH"
    ]
    assert len(source_findings) == 1
    assert source_findings[0]["subject_kind"] == "source_module"
    mismatched_rows = [
        row for row in result["source_modules"] if row["digest_matches"] is False
    ]
    assert [row["module_id"] for row in mismatched_rows] == [
        first_module["module_id"]
    ]
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False


def test_symbol_classifier_exported_bundle_blocks_source_module_manifest_boundaries(
    tmp_path: Path,
) -> None:
    cases = [
        (
            "missing_manifest",
            "SYMBOL_CLASSIFIER_SOURCE_MODULE_MANIFEST_MISSING",
            "source_module_manifest",
        ),
        (
            "manifest_import_class_invalid",
            "SYMBOL_CLASSIFIER_SOURCE_MODULE_IMPORT_CLASS_INVALID",
            "source_module_manifest",
        ),
        (
            "manifest_body_in_receipt",
            "SYMBOL_CLASSIFIER_SOURCE_MODULE_BODY_IN_RECEIPT_FORBIDDEN",
            "source_module_manifest",
        ),
        (
            "row_import_class_invalid",
            "SYMBOL_CLASSIFIER_SOURCE_MODULE_ROW_IMPORT_CLASS_INVALID",
            "source_module",
        ),
        (
            "row_relation_invalid",
            "SYMBOL_CLASSIFIER_SOURCE_MODULE_RELATION_INVALID",
            "source_module",
        ),
        (
            "row_body_in_receipt",
            "SYMBOL_CLASSIFIER_SOURCE_MODULE_ROW_BODY_IN_RECEIPT_FORBIDDEN",
            "source_module",
        ),
        (
            "target_missing",
            "SYMBOL_CLASSIFIER_SOURCE_MODULE_TARGET_MISSING",
            "source_module",
        ),
    ]

    for case_id, expected_code, expected_subject_kind in cases:
        public_root = tmp_path / case_id / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        bundle_input = (
            public_root
            / "examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle"
        )
        shutil.copytree(BUNDLE_INPUT, bundle_input)
        manifest_path = bundle_input / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        first_module = manifest["modules"][0]

        if case_id == "missing_manifest":
            manifest_path.unlink()
        elif case_id == "manifest_import_class_invalid":
            manifest["source_import_class"] = "private_macro_body"
        elif case_id == "manifest_body_in_receipt":
            manifest["body_in_receipt"] = True
        elif case_id == "row_import_class_invalid":
            first_module["source_import_class"] = "private_macro_body"
        elif case_id == "row_relation_invalid":
            first_module["source_to_target_relation"] = "unverified_copy"
        elif case_id == "row_body_in_receipt":
            first_module["body_in_receipt"] = True
        elif case_id == "target_missing":
            (bundle_input / first_module["path"]).unlink()

        if manifest_path.exists():
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )

        result = run_symbol_bundle(
            bundle_input,
            tmp_path
            / "receipts/runtime_shell/demo_project/organs/"
            f"undeclared_library_prior_symbol_classifier/{case_id}",
            command="pytest",
        )

        assert result["status"] == "blocked"
        assert result["source_modules_pass"] is False
        assert expected_code in result["error_codes"]
        findings = [
            row for row in result["findings"] if row["error_code"] == expected_code
        ]
        assert findings
        assert {row["subject_kind"] for row in findings} == {expected_subject_kind}
        assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert result["body_in_receipt"] is False
        receipt_text = json.dumps(result, sort_keys=True)
        assert (
            "from tools.meta.factory import run_prover_graph_benchmark as harness"
            not in receipt_text
        )
        assert "TRUTH_SIDE_FORBIDDEN_MARKERS =" not in receipt_text
        assert "SYNTHETIC_PROVIDER_PAYLOAD_BODY_SENTINEL" not in receipt_text


def test_symbol_classifier_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "undeclared_library_prior_symbol_classifier"
    )
    args = [
        "run-symbol-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 13
    assert first_card["symbol_classifier"]["classification_count"] == 3
    assert first_card["symbol_classifier"]["premise_count"] == 11
    assert first_card["symbol_classifier"]["undeclared_library_prior_count"] == 1
    assert first_card["symbol_classifier"]["premise_budget_precedence_count"] == 1
    assert first_card["symbol_classifier"]["source_module_count"] == 6
    assert first_card["symbol_classifier"]["verified_source_module_count"] == 6
    assert first_card["source_body_floor"]["status"] == "pass"
    assert first_card["source_body_floor"]["body_material_count"] == 6
    assert first_card["source_body_floor"]["body_material_id_count"] == 6
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert "source_modules" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "body_material_ids" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "source_digests" not in _walk_keys(first_card)
    assert "proof_body" not in _walk_keys(first_card)
    assert "private_source_ref" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        undeclared_library_prior_symbol_classifier,
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
