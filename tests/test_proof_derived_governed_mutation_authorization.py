from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import proof_derived_governed_mutation_authorization
from microcosm_core.organs.proof_derived_governed_mutation_authorization import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_authorization_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/proof_derived_governed_mutation_authorization/"
    "exported_governed_mutation_authorization_bundle"
)
SOURCE_ROOT = MICROCOSM_ROOT.parent
REAL_RECORD_COMMIT = "67ac353d969750050ac4b46157dc4ba93a900ade"
REAL_RECORD_PARENT_COMMIT = "e6df7a88bf023c44e17348c570717ec0aee3dd9b"
REAL_RECORD_PARENT_SUBJECT = "Broaden Microcosm credential token policy gate"


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


def _proposal_row(result: dict[str, Any], proposal_id: str) -> dict[str, Any]:
    return next(
        row for row in result["proposal_rows"] if row["proposal_id"] == proposal_id
    )


def _real_record_row(result: dict[str, Any], proposal_id: str) -> dict[str, Any]:
    return next(
        row
        for row in result["governed_mutation_record_rows"]
        if row["proposal_id"] == proposal_id
    )


def _assert_authority_boundary_denies_overclaims(boundary: dict[str, Any]) -> None:
    assert boundary["live_cloud_account_authorized"] is False
    assert boundary["standing_credentials_authorized"] is False
    assert boundary["source_mutation_authorized"] is False
    assert boundary["irreversible_mutation_authorized"] is False
    assert boundary["policy_after_execution_authorized"] is False
    assert boundary["hidden_policy_votes_authorized"] is False
    assert boundary["provider_calls_authorized"] is False
    assert boundary["benchmark_score_claim_authorized"] is False
    assert boundary["release_authorized"] is False


def test_governed_mutation_authorization_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/proof_derived_governed_mutation_authorization",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "proof_derived_governed_mutation_authorization_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["proposal_count"] == 3
    assert result["authorized_mutation_count"] == 3
    assert result["write_or_rollback_count"] == 2
    assert result["real_record_status"] == (
        "real_public_safe_governed_mutation_record_bound"
    )
    assert result["real_record_count"] == 3
    assert result["accepted_real_record_count"] == 3
    assert result["anti_bake_positive_mutation_proof_status"] == (
        "real_record_refs_derived_from_git_scope_and_fixture_indices"
    )
    assert result["anti_bake_positive_record_count"] == 3
    assert result["missing_real_record_proposal_ids"] == []
    assert result["proof_cell_count"] == 3
    assert result["accepted_proof_cell_count"] == 3
    assert result["policy_verdict_count"] == 6
    assert result["visible_policy_verdict_count"] == 6
    assert result["logged_side_effect_count"] == 2
    assert result["rollback_pass_count"] == 2
    assert result["cold_replay_pass_count"] == 3
    _assert_authority_boundary_denies_overclaims(result["authority_ceiling"])
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_governed_mutation_authorization_resolves_real_commit_and_derives_refs(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    write_record = _real_record_row(result, "proposal.scoped_config_change")
    rollback_record = _real_record_row(result, "proposal.rollback_config_change")

    assert result["status"] == "pass"
    assert write_record["resolved_commit_ref"] == REAL_RECORD_COMMIT
    assert write_record["commit_scope_verified"] is True
    assert {
        "microcosm-substrate/src/microcosm_core/organs/"
        "proof_derived_governed_mutation_authorization.py",
        "microcosm-substrate/tests/"
        "test_proof_derived_governed_mutation_authorization.py",
    }.issubset(set(write_record["verified_commit_touched_paths"]))
    assert write_record["derived_proof_cell_refs"] == [
        "proof.write.scoped_config.v1"
    ]
    assert write_record["derived_policy_verdict_refs"] == [
        "verdict.write.policy.v1",
        "verdict.write.owner.v1",
    ]
    assert write_record["derived_rollback_receipt_ref"] == (
        "rollback.synthetic_config_write.v1"
    )
    assert write_record["resolved_proof_cell_record_refs"] == [
        "fixtures/first_wave/"
        "proof_derived_governed_mutation_authorization/input/"
        "proof_evidence_cells.json::proof_cell_id=proof.write.scoped_config.v1"
    ]
    assert write_record["resolved_policy_verdict_record_refs"] == [
        "fixtures/first_wave/"
        "proof_derived_governed_mutation_authorization/input/"
        "policy_verdicts.json::verdict_id=verdict.write.policy.v1",
        "fixtures/first_wave/"
        "proof_derived_governed_mutation_authorization/input/"
        "policy_verdicts.json::verdict_id=verdict.write.owner.v1",
    ]
    assert write_record["resolved_side_effect_record_ref"] == (
        "fixtures/first_wave/"
        "proof_derived_governed_mutation_authorization/input/"
        "side_effect_ledger.json::proposal_id=proposal.scoped_config_change"
    )
    assert write_record["resolved_rollback_record_ref"] == (
        "fixtures/first_wave/"
        "proof_derived_governed_mutation_authorization/input/"
        "rollback_receipts.json::rollback_receipt_ref="
        "rollback.synthetic_config_write.v1"
    )
    assert write_record["resolved_cold_replay_record_refs"] == [
        "fixtures/first_wave/"
        "proof_derived_governed_mutation_authorization/input/"
        "cold_replay.json::replay_id=cold.scoped_config_write.v1"
    ]
    assert write_record["resolved_record_digests"]["proof_cells"][
        "proof.write.scoped_config.v1"
    ].startswith("sha256:")
    assert write_record["resolved_record_digests"]["policy_verdicts"][
        "verdict.write.policy.v1"
    ].startswith("sha256:")
    assert write_record["resolved_record_digests"]["rollback"].startswith("sha256:")
    assert write_record["resolved_record_digests"]["cold_replay"][
        "cold.scoped_config_write.v1"
    ].startswith("sha256:")
    assert write_record["declared_refs_match_derived"] is True
    assert write_record["anti_bake_proof_status"] == (
        "real_record_refs_derived_from_git_scope_and_fixture_indices"
    )
    assert rollback_record["derived_rollback_receipt_ref"] == (
        "rollback.rollback_verification.v1"
    )
    assert write_record["real_evidence_ref_digest"].startswith("sha256:")


def test_governed_mutation_authorization_rejects_positive_proposal_without_proof_cell(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3

    proposal_path = input_dir / "mutation_proposals.json"
    proposals = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposals["mutation_proposals"][0]["proof_cell_refs"] = []
    proposal_path.write_text(
        json.dumps(proposals, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    mutated_row = next(
        row
        for row in result["proposal_rows"]
        if row["proposal_id"] == "proposal.inspect_repo_state"
    )

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert "GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE" in result["error_codes"]
    assert mutated_row["computed_verdict"] == "blocked"
    assert "consensus_without_evidence" in mutated_row["reason_codes"]


def test_governed_mutation_authorization_rejects_positive_proposal_with_one_visible_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3

    proposal_path = input_dir / "mutation_proposals.json"
    proposals = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposals["mutation_proposals"][0]["policy_verdict_refs"] = [
        proposals["mutation_proposals"][0]["policy_verdict_refs"][0]
    ]
    proposal_path.write_text(
        json.dumps(proposals, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    mutated_row = next(
        row
        for row in result["proposal_rows"]
        if row["proposal_id"] == "proposal.inspect_repo_state"
    )

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert "GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE" in result["error_codes"]
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["policy_verdict_refs"] == ["verdict.inspect.policy.v1"]
    assert "consensus_without_evidence" in mutated_row["reason_codes"]


def test_governed_mutation_authorization_rejects_claimant_self_approval(
    tmp_path: Path,
) -> None:
    # Evidentiary-counterparty invariant, claimant-disjointness arm: a proposal whose
    # claimant supplies one of its own releasing verdicts is not arms-length verified.
    # ephemeral_identity_ref is NOT part of the evidence-chain hash, so the block is
    # cleanly attributable to non-independence alone (the evidence floor still passes).
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3

    proposal_path = input_dir / "mutation_proposals.json"
    proposals = json.loads(proposal_path.read_text(encoding="utf-8"))
    # the claimant impersonates one of its own evaluators
    proposals["mutation_proposals"][0]["ephemeral_identity_ref"] = "policy_gate.synthetic"
    proposal_path.write_text(
        json.dumps(proposals, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    mutated_row = _proposal_row(result, "proposal.inspect_repo_state")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert "GOV_MUT_VERDICT_NOT_INDEPENDENT" in result["error_codes"]
    assert mutated_row["computed_verdict"] == "blocked"
    assert "verdict_not_independent" in mutated_row["reason_codes"]
    # clean attribution: proof refs, evidence-chain hash, and two visible verdicts all
    # still hold; the sole defect is that the claimant is its own verifier.
    assert "consensus_without_evidence" not in mutated_row["reason_codes"]


def test_governed_mutation_authorization_rejects_two_verdicts_from_one_evaluator_root(
    tmp_path: Path,
) -> None:
    # Evidentiary-counterparty invariant, evidence-root-collapse arm (the wash-trade
    # shape): two visible verdicts that collapse to a single evaluator root are one
    # provenance root wearing two hats, not two independent confirmations. Collapsing
    # evaluator_id also perturbs the evidence-chain hash, so consensus_without_evidence
    # co-fires; the independence finding is asserted as a subset.
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3

    verdict_path = input_dir / "policy_verdicts.json"
    verdicts = json.loads(verdict_path.read_text(encoding="utf-8"))
    for verdict in verdicts["verdicts"]:
        if verdict.get("proposal_id") == "proposal.inspect_repo_state":
            verdict["evaluator_id"] = "policy_gate.synthetic"
    verdict_path.write_text(
        json.dumps(verdicts, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    mutated_row = _proposal_row(result, "proposal.inspect_repo_state")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert "GOV_MUT_VERDICT_NOT_INDEPENDENT" in result["error_codes"]
    assert mutated_row["computed_verdict"] == "blocked"
    assert "verdict_not_independent" in mutated_row["reason_codes"]


def test_governed_mutation_authorization_rejects_cross_proposal_proof_cell(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3

    proposal_path = input_dir / "mutation_proposals.json"
    proposals = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposals["mutation_proposals"][0]["proof_cell_refs"] = [
        "proof.write.scoped_config.v1"
    ]
    proposal_path.write_text(
        json.dumps(proposals, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    mutated_row = next(
        row
        for row in result["proposal_rows"]
        if row["proposal_id"] == "proposal.inspect_repo_state"
    )

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert "GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE" in result["error_codes"]
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["proof_cell_refs"] == ["proof.write.scoped_config.v1"]
    assert "consensus_without_evidence" in mutated_row["reason_codes"]


def test_governed_mutation_authorization_rejects_cross_proposal_policy_verdicts(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3

    proposal_path = input_dir / "mutation_proposals.json"
    proposals = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposals["mutation_proposals"][0]["policy_verdict_refs"] = [
        "verdict.write.policy.v1",
        "verdict.write.owner.v1",
    ]
    proposal_path.write_text(
        json.dumps(proposals, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    mutated_row = next(
        row
        for row in result["proposal_rows"]
        if row["proposal_id"] == "proposal.inspect_repo_state"
    )

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert "GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE" in result["error_codes"]
    assert mutated_row["computed_verdict"] == "blocked"
    assert mutated_row["policy_verdict_refs"] == [
        "verdict.write.policy.v1",
        "verdict.write.owner.v1",
    ]
    assert "consensus_without_evidence" in mutated_row["reason_codes"]


def test_governed_mutation_authorization_rejects_policy_verdict_with_forged_proof_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3

    verdict_path = input_dir / "policy_verdicts.json"
    verdicts = json.loads(verdict_path.read_text(encoding="utf-8"))
    verdicts["verdicts"][0]["evidence_refs"] = ["proof.forged.policy.v1"]
    verdict_path.write_text(
        json.dumps(verdicts, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    mutated_row = next(
        row
        for row in result["proposal_rows"]
        if row["proposal_id"] == "proposal.inspect_repo_state"
    )
    verdict_row = next(
        row
        for row in result["policy_verdict_rows"]
        if row["verdict_id"] == "verdict.inspect.policy.v1"
    )
    real_record = _real_record_row(result, "proposal.inspect_repo_state")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert "GOV_MUT_POLICY_VERDICT_INVALID" in result["error_codes"]
    assert "GOV_MUT_REAL_RECORD_POLICY_REF_INVALID" in result["error_codes"]
    assert verdict_row["computed_verdict"] == "blocked"
    assert verdict_row["reason_codes"] == ["evidence_ref_unresolved"]
    assert mutated_row["computed_verdict"] == "blocked"
    assert "consensus_without_evidence" in mutated_row["reason_codes"]
    assert real_record["computed_verdict"] == "blocked"
    assert real_record["derived_policy_verdict_refs"] == [
        "verdict.inspect.owner.v1"
    ]
    assert "policy_verdict_ref_invalid" in real_record["reason_codes"]


def test_governed_mutation_authorization_rejects_forged_real_record_policy_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["accepted_real_record_count"] == 3

    records_path = input_dir / "governed_mutation_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    records["governed_mutation_records"][0]["policy_verdict_refs"] = [
        "verdict.forged.policy.v1",
        "verdict.inspect.owner.v1",
    ]
    records_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert "GOV_MUT_REAL_RECORD_POLICY_REF_INVALID" in result["error_codes"]
    assert "GOV_MUT_REAL_RECORD_FLOOR_MISSING" in result["error_codes"]
    assert result["missing_real_record_proposal_ids"] == [
        "proposal.inspect_repo_state"
    ]
    assert _proposal_row(result, "proposal.inspect_repo_state")[
        "computed_verdict"
    ] == "blocked"
    assert "real_governed_mutation_record_missing" in _proposal_row(
        result,
        "proposal.inspect_repo_state",
    )["reason_codes"]


def test_governed_mutation_authorization_rejects_baked_real_record_proof_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["anti_bake_positive_record_count"] == 3

    records_path = input_dir / "governed_mutation_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    records["governed_mutation_records"][1]["proof_cell_refs"] = [
        "proof.inspect.repo_state.v1"
    ]
    records_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    record = _real_record_row(result, "proposal.scoped_config_change")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert result["anti_bake_positive_mutation_proof_status"] == "blocked"
    assert result["anti_bake_positive_record_count"] == 2
    assert "GOV_MUT_REAL_RECORD_PROOF_REF_INVALID" in result["error_codes"]
    assert "GOV_MUT_REAL_RECORD_FLOOR_MISSING" in result["error_codes"]
    assert record["computed_verdict"] == "blocked"
    assert record["declared_refs_match_derived"] is False
    assert record["anti_bake_proof_status"] == "blocked"
    assert "proof_cell_ref_invalid" in record["reason_codes"]
    assert "real_governed_mutation_record_missing" in _proposal_row(
        result,
        "proposal.scoped_config_change",
    )["reason_codes"]


def test_governed_mutation_authorization_rejects_stale_evidence_chain_hash(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert _proposal_row(
        baseline,
        "proposal.scoped_config_change",
    )["evidence_chain_hash_matches"] is True

    proposal_path = input_dir / "mutation_proposals.json"
    proposals = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposals["mutation_proposals"][1]["evidence_chain_hash"] = (
        "sha256:" + ("0" * 64)
    )
    proposal_path.write_text(
        json.dumps(proposals, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    proposal = _proposal_row(result, "proposal.scoped_config_change")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert "GOV_MUT_EVIDENCE_CHAIN_HASH_MISMATCH" in result["error_codes"]
    assert proposal["computed_verdict"] == "blocked"
    assert proposal["evidence_chain_hash_matches"] is False
    assert proposal["derived_evidence_chain_hash"].startswith("sha256:")
    assert "evidence_chain_hash_mismatch" in proposal["reason_codes"]


def test_governed_mutation_authorization_removing_source_proof_cell_moves_authorization(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["authorized_mutation_count"] == 3
    assert baseline["accepted_real_record_count"] == 3

    proof_path = input_dir / "proof_evidence_cells.json"
    proof_cells = json.loads(proof_path.read_text(encoding="utf-8"))
    proof_cells["proof_cells"] = [
        row
        for row in proof_cells["proof_cells"]
        if row["proof_cell_id"] != "proof.write.scoped_config.v1"
    ]
    proof_path.write_text(
        json.dumps(proof_cells, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    proposal = _proposal_row(result, "proposal.scoped_config_change")
    record = _real_record_row(result, "proposal.scoped_config_change")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert "GOV_MUT_PROOF_CELL_FLOOR_MISSING" in result["error_codes"]
    assert "GOV_MUT_POLICY_VERDICT_INVALID" in result["error_codes"]
    assert "GOV_MUT_REAL_RECORD_PROOF_REF_INVALID" in result["error_codes"]
    assert "GOV_MUT_REAL_RECORD_FLOOR_MISSING" in result["error_codes"]
    assert proposal["computed_verdict"] == "blocked"
    assert proposal["evidence_chain_hash_matches"] is False
    assert "consensus_without_evidence" in proposal["reason_codes"]
    assert record["computed_verdict"] == "blocked"
    assert record["derived_proof_cell_refs"] == []
    assert record["derived_policy_verdict_refs"] == []
    assert "proof_cell_ref_invalid" in record["reason_codes"]


def test_governed_mutation_authorization_rejects_baked_real_label_without_commit(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    records_path = input_dir / "governed_mutation_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    records["governed_mutation_records"][1]["commit_ref"] = "f" * 40
    records["governed_mutation_records"][1]["commit_subject"] = (
        "Bind governed mutation evidence to proposals"
    )
    records_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    record = _real_record_row(result, "proposal.scoped_config_change")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert "GOV_MUT_REAL_RECORD_COMMIT_REF_UNVERIFIED" in result["error_codes"]
    assert record["computed_verdict"] == "blocked"
    assert "commit_ref_unverified" in record["reason_codes"]
    assert "real_governed_mutation_record_missing" in _proposal_row(
        result,
        "proposal.scoped_config_change",
    )["reason_codes"]


def test_governed_mutation_authorization_commit_scope_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert _proposal_row(
        baseline,
        "proposal.scoped_config_change",
    )["computed_verdict"] == "authorized_synthetic_mutation_metadata"

    records_path = input_dir / "governed_mutation_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    record = records["governed_mutation_records"][1]
    record["commit_ref"] = REAL_RECORD_PARENT_COMMIT
    record["commit_subject"] = REAL_RECORD_PARENT_SUBJECT
    record["source_refs"] = [
        REAL_RECORD_PARENT_COMMIT
        if ref.startswith("git:")
        else ref
        for ref in record["source_refs"]
    ]
    record["source_refs"][0] = f"git:{REAL_RECORD_PARENT_COMMIT}"
    records_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    proposal = _proposal_row(result, "proposal.scoped_config_change")
    real_record = _real_record_row(result, "proposal.scoped_config_change")

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert "GOV_MUT_REAL_RECORD_COMMIT_SCOPE_UNVERIFIED" in result["error_codes"]
    assert real_record["resolved_commit_ref"] == REAL_RECORD_PARENT_COMMIT
    assert real_record["commit_scope_verified"] is False
    assert "commit_scope_unverified" in real_record["reason_codes"]
    assert proposal["computed_verdict"] == "blocked"
    assert "real_governed_mutation_record_missing" in proposal["reason_codes"]


def test_governed_mutation_authorization_rejects_missing_real_record_rollback(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["rollback_pass_count"] == 2

    records_path = input_dir / "governed_mutation_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    records["governed_mutation_records"][1]["rollback_receipt_present"] = False
    records["governed_mutation_records"][1]["rollback_receipt_ref"] = ""
    records_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert "GOV_MUT_REAL_RECORD_ROLLBACK_RECEIPT_MISSING" in result["error_codes"]
    assert result["missing_real_record_proposal_ids"] == [
        "proposal.scoped_config_change"
    ]
    assert "real_governed_mutation_record_missing" in _proposal_row(
        result,
        "proposal.scoped_config_change",
    )["reason_codes"]


def test_governed_mutation_authorization_rejects_unlogged_real_record_side_effect(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)

    baseline = run(
        input_dir,
        public_root
        / "receipts/good/proof_derived_governed_mutation_authorization",
        command="pytest",
    )
    assert baseline["status"] == "pass"
    assert baseline["logged_side_effect_count"] == 2

    records_path = input_dir / "governed_mutation_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    records["governed_mutation_records"][2]["side_effect_logged"] = False
    records["governed_mutation_records"][2]["side_effect_diff_ref"] = ""
    records_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        input_dir,
        public_root
        / "receipts/bad/proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["authorized_mutation_count"] == 2
    assert result["accepted_real_record_count"] == 2
    assert "GOV_MUT_REAL_RECORD_SIDE_EFFECT_UNLOGGED" in result["error_codes"]
    assert result["missing_real_record_proposal_ids"] == [
        "proposal.rollback_config_change"
    ]
    assert "real_governed_mutation_record_missing" in _proposal_row(
        result,
        "proposal.rollback_config_change",
    )["reason_codes"]


def test_governed_mutation_authorization_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/proof_derived_governed_mutation_authorization",
        public_root / "fixtures/first_wave/proof_derived_governed_mutation_authorization",
    )

    result = run(
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input",
        public_root
        / "receipts/first_wave/proof_derived_governed_mutation_authorization",
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
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "token_value" not in keys
        assert "provider_payload" not in keys
        assert "private_account_id" not in keys
        assert "raw_policy_vote_body" not in keys
        assert "raw_proof_body" not in keys
        assert "cloud_account_id" not in keys


def test_governed_mutation_authorization_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_authorization_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_governed_mutation_authorization_bundle"
    assert (
        result["bundle_id"]
        == "proof_derived_governed_mutation_authorization_runtime_example"
    )
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["source_module_manifest_status"] == "pass"
    assert result["body_copied_material_count"] == 6
    assert (
        result["source_open_body_imports"]["body_material_status"]
        == "copied_non_secret_governed_mutation_authorization_macro_body_landed"
    )
    assert result["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert result["authorized_mutation_count"] == 3
    assert result["real_record_status"] == (
        "real_public_safe_governed_mutation_record_bound"
    )
    assert result["accepted_real_record_count"] == 3
    assert result["logged_side_effect_count"] == 2
    assert result["rollback_pass_count"] == 2
    assert result["cold_replay_pass_count"] == 3
    _assert_authority_boundary_denies_overclaims(result["authority_ceiling"])


def test_governed_mutation_authorization_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/proof_derived_governed_mutation_authorization",
        public_root / "examples/proof_derived_governed_mutation_authorization",
    )
    bundle = (
        public_root
        / "examples/proof_derived_governed_mutation_authorization/"
        "exported_governed_mutation_authorization_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_authorization_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "GOV_MUT_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_governed_mutation_authorization_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/proof_derived_governed_mutation_authorization",
        public_root / "examples/proof_derived_governed_mutation_authorization",
    )
    bundle = (
        public_root
        / "examples/proof_derived_governed_mutation_authorization/"
        "exported_governed_mutation_authorization_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_authorization_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "GOV_MUT_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_governed_mutation_authorization_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/proof_derived_governed_mutation_authorization",
        public_root / "examples/proof_derived_governed_mutation_authorization",
    )
    bundle = (
        public_root
        / "examples/proof_derived_governed_mutation_authorization/"
        "exported_governed_mutation_authorization_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_authorization_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "GOV_MUT_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_governed_mutation_authorization_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 6
    assert {
        row["module_id"] for row in manifest["modules"]
    } == {
        "proof_governed_mutation_extracted_patterns_ledger_body_import",
        "proof_governed_mutation_high_novelty_growth_receipt_body_import",
        "mission_transaction_preflight_control_body_import",
        "scoped_commit_private_index_control_body_import",
        "work_ledger_claim_runtime_body_import",
        "work_landing_reconcile_control_body_import",
    }

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix("microcosm-substrate/")
        text = target.read_text(encoding="utf-8")
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == row["source_sha256"]
        assert _sha256(target) == row["target_sha256"]
        assert row["source_sha256"] == row["target_sha256"]
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_governed_mutation_authorization_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "proof_derived_governed_mutation_authorization"
    )
    args = [
        "run-authorization-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 19
    assert (
        first_card["validation"]["bundle_id"]
        == "proof_derived_governed_mutation_authorization_runtime_example"
    )
    assert first_card["validation"]["source_module_manifest_status"] == "pass"
    assert first_card["validation"]["body_material_count"] == 6
    assert (
        first_card["validation"]["body_material_status"]
        == "copied_non_secret_governed_mutation_authorization_macro_body_landed"
    )
    auth = first_card["governed_mutation_authorization"]
    assert auth["proposal_count"] == 3
    assert auth["authorized_mutation_count"] == 3
    assert auth["write_or_rollback_count"] == 2
    assert auth["real_record_status"] == (
        "real_public_safe_governed_mutation_record_bound"
    )
    assert auth["real_record_count"] == 3
    assert auth["accepted_real_record_count"] == 3
    assert auth["proof_cell_count"] == 3
    assert auth["policy_verdict_count"] == 6
    assert auth["logged_side_effect_count"] == 2
    assert auth["rollback_pass_count"] == 2
    assert auth["cold_replay_pass_count"] == 3
    assert first_card["negative_case_coverage"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert (
        first_card["validation"]["real_record_status"]
        == "real_public_safe_governed_mutation_record_bound"
    )
    assert first_card["validation"]["missing_real_record_proposal_count"] == 0
    assert first_card["governed_mutation_authorization"][
        "anti_bake_positive_mutation_proof_status"
    ] == "real_record_refs_derived_from_git_scope_and_fixture_indices"
    assert first_card["governed_mutation_authorization"][
        "anti_bake_positive_record_count"
    ] == 3
    _assert_authority_boundary_denies_overclaims(first_card["authority_boundary"])
    assert "governed_mutation_record_rows" not in _walk_keys(first_card)
    assert "proof_cell_rows" not in _walk_keys(first_card)
    assert "policy_verdict_rows" not in _walk_keys(first_card)
    assert "proposal_rows" not in _walk_keys(first_card)
    assert "side_effect_rows" not in _walk_keys(first_card)
    assert "rollback_rows" not in _walk_keys(first_card)
    assert "cold_replay_rows" not in _walk_keys(first_card)
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)
    assert "authority_ceiling" not in _walk_keys(first_card)
    assert "anti_claim" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        proof_derived_governed_mutation_authorization,
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
