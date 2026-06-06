from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs._crown_jewel_common import (
    _dirty_worktree_source_ref,
    validate_source_manifest,
)
from microcosm_core.organs.batch5_authority_systems_capsule import (
    AUTHORITY_CEILING,
    CASE_VERDICT_AUTHORITY,
    EXPECTED_MECHANISMS,
    EXPECTED_MODULE_IDS,
    EXPECTED_NEGATIVE_CASES,
    NEGATIVE_CASE_COMPUTED_PATHS,
    NEGATIVE_CASE_PROBE_SCHEMA,
    SPEC,
    evaluate_negative_case,
    result_card,
    run,
    run_batch5_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch5_authority_systems_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch5_authority_systems_capsule/exported_batch5_authority_systems_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


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
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch5_authority_systems_capsule",
        public_root / "examples/batch5_authority_systems_capsule",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch5_authority_systems_capsule",
        public_root / "fixtures/first_wave/batch5_authority_systems_capsule",
    )
    return public_root / "fixtures/first_wave/batch5_authority_systems_capsule/input"


def test_batch5_authority_systems_capsule_runs_all_mechanisms(tmp_path: Path) -> None:
    acceptance_out = (
        tmp_path
        / "receipts/acceptance/first_wave/batch5_authority_systems_capsule_fixture_acceptance.json"
    )
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch5_authority_systems_capsule",
        acceptance_out=acceptance_out,
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

    exercise = result["exercise"]
    assert exercise["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert {row["mechanism_id"] for row in exercise["mechanisms"]} == set(EXPECTED_MECHANISMS)
    assert all(row["status"] == "pass" for row in exercise["mechanisms"])
    assert exercise["runtime_exercises"]["reasoning_execution_receipt_validator"]["drifted_receipt_codes"]
    assert (
        exercise["runtime_exercises"]["reasoning_execution_replay_scope_lineage"]["classification"]
        == "no_replay"
    )
    assert (
        exercise["runtime_exercises"]["lean_provider_repair_loop"]["contract_gate"]
        == "rejected_before_lean"
    )
    assert (
        exercise["runtime_exercises"]["process_orphan_reaper"]["signal_sent"]
        is False
    )
    assert (
        exercise["runtime_exercises"]["generated_state_fixpoint_drainer"]["classification"]
        == "settlement_residual_source_moved"
    )
    assert (
        exercise["runtime_exercises"]["agent_trace_tape_compactor"]["omission_receipt"][
            "omitted_byte_count"
        ]
        > 0
    )
    assert (
        exercise["runtime_exercises"]["system_blast_radius"]["honest_empty_leaf_bucket"]
        is True
    )
    assert exercise["runtime_exercises"]["doctrine_graph_compiler"]["drift_findings"]
    assert exercise["negative_case_probe_summary"]["probe_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert exercise["negative_case_probe_summary"]["computed_probe_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert exercise["negative_case_probe_summary"]["fixture_verdict_echo_risk_count"] == 0
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["body_in_receipt"] is False
    acceptance = json.loads(acceptance_out.read_text(encoding="utf-8"))
    assert acceptance["semantic_negative_case_evaluator_used"] is True
    assert acceptance["observed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert acceptance["negative_case_probe_summary"]["computed_probe_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )


def test_batch5_authority_systems_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_batch5_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch5_authority_systems_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch5_authority_systems_capsule_bundle"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["exercise"]["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch5_authority_systems_source_modules_are_exact_macro_body_imports() -> None:
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
        if source.read_bytes() != target.read_bytes():
            assert _dirty_worktree_source_ref(row["source_ref"], repo_root=SOURCE_ROOT)
            continue
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch5_source_manifest_demotes_active_claimed_live_source_drift(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    public_root.mkdir(parents=True)
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch5_authority_systems_capsule/"
        "exported_batch5_authority_systems_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    (tmp_path / ".git").mkdir()

    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    manifest["modules"] = [row]
    manifest["module_count"] = 1
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    live_source = tmp_path / row["source_ref"]
    live_source.parent.mkdir(parents=True, exist_ok=True)
    live_source.write_text(
        "live source changed under an active sibling claim\n",
        encoding="utf-8",
    )
    claim_snapshot = tmp_path / "state/work_ledger/active_claims_snapshot.json"
    claim_snapshot.parent.mkdir(parents=True, exist_ok=True)
    claim_snapshot.write_text(
        json.dumps(
            {
                "active_claims": [
                    {
                        "scope_kind": "path",
                        "scope_id": row["source_ref"],
                        "path": row["source_ref"],
                        "released_at": None,
                        "expired_at": None,
                    }
                ]
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = validate_source_manifest(bundle, SPEC, public_root=public_root)

    assert result["status"] == "pass"
    assert result["all_expected_digests_matched"] is True
    assert result["all_live_source_refs_current"] is False
    assert result["active_claimed_live_source_drift_count"] == 1
    assert result["modules"][0]["digest_status"] == "match"
    assert result["modules"][0]["live_source_claimed"] is True
    assert result["modules"][0]["live_source_digest_status"] == "active_claim_drift"
    assert (
        result["modules"][0]["source_ref_verification"]
        == "manifest_target_digest_pass_live_source_claimed_drift"
    )


def test_batch5_authority_systems_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch5_authority_systems_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert card["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "proof_body" not in _walk_keys(result)


def test_batch5_negative_cases_are_stable() -> None:
    matrix_mechanisms = set(EXPECTED_MECHANISMS)
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["schema_version"] == NEGATIVE_CASE_PROBE_SCHEMA
        assert payload["case_id"] == case_id
        assert payload["error_codes"] == list(expected_codes)
        assert payload["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert payload["verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert payload["mechanism_id"] in matrix_mechanisms
        assert payload["computed_path"] == NEGATIVE_CASE_COMPUTED_PATHS[case_id][
            "computed_path"
        ]
        assert isinstance(payload["probe_input"], dict)
        assert payload["probe_input"]
        assert payload["body_in_receipt"] is False


def test_batch5_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        payload["computed_path"] = "bogus_declared_computed_path"
        payload["fixture_role"] = "forged_fixture_verdict"
        payload["verdict_authority"] = "declared_label_attempt"
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/batch5_authority_systems_capsule",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    for expected_codes in EXPECTED_NEGATIVE_CASES.values():
        for code in expected_codes:
            assert code in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch5_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]


def test_batch5_negative_case_probe_input_change_blocks_fixture_run(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    case_id = "proof_contract_sorry"
    case_path = fixture / f"{case_id}.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["probe_input"]["bad_proof"] = "exact proof for micro10_public_target"
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    direct = evaluate_negative_case(case_id, fixture, EXPECTED_NEGATIVE_CASES[case_id])
    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/batch5_authority_systems_capsule",
    )
    semantic_row = next(
        row for row in result["negative_case_semantics"] if row["case_id"] == case_id
    )

    assert direct["status"] == "pass"
    assert result["status"] == "blocked"
    assert semantic_row["status"] == "pass"
    assert case_id not in result["observed_negative_cases"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in result["error_codes"]
