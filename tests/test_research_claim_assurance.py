from __future__ import annotations

import copy
import json
from pathlib import Path

from microcosm_core.validators.research_claim_assurance import (
    EXPECTED_OUTCOMES,
    EXPECTED_VERDICTS,
    audit_research_claim_assurance,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent


def _std_microcosm() -> dict:
    return json.loads(
        (REPO_ROOT / "codex/standards/std_microcosm.json").read_text(
            encoding="utf-8"
        )
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str = "placeholder\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    contract = copy.deepcopy(_std_microcosm()["research_mechanism_cluster_contract"])
    _write_json(
        repo / "codex/standards/std_microcosm.json",
        {"research_mechanism_cluster_contract": contract},
    )
    for row in contract["rows"]:
        for ref in [
            row["paper_module"],
            *row["source_loci"],
            row.get("sibling_standard"),
            *row.get("supporting_standards", []),
        ]:
            if ref:
                _write_text(repo / ref)
        _write_json(
            repo / row["standard"],
            {
                "standard_id": Path(row["standard"]).stem,
                "authority_ceiling": {
                    "release_authority": False,
                    "source_mutation_authority": False,
                    "status": "pass",
                },
                "research_bet_contract": {
                    "governing_mechanism": "mech_036",
                    "positive_claim": row["positive_claim"],
                    "required_witnesses": ["fixture witness"],
                    "negative_floor": [row["required_negative_floor"]],
                    "denied_authority": ["release authority"],
                },
                "anti_claim": "This fixture is not release authority.",
                "validator_contract": {"validator_id": f"validator.{row['organ_id']}"},
            },
        )
    return repo


def _contract(repo: Path) -> dict:
    return json.loads(
        (repo / "codex/standards/std_microcosm.json").read_text(encoding="utf-8")
    )["research_mechanism_cluster_contract"]


def _store_contract(repo: Path, contract: dict) -> None:
    _write_json(
        repo / "codex/standards/std_microcosm.json",
        {"research_mechanism_cluster_contract": contract},
    )


def _first_issue(receipt: dict, code: str) -> dict:
    for issue in receipt["issues"]:
        if issue["code"] == code:
            return issue
    raise AssertionError(f"missing issue code: {code}")


def _assert_issue_outcome(receipt: dict, code: str, outcome: str) -> dict:
    issue = _first_issue(receipt, code)
    assert issue["outcome"] == outcome
    assert receipt["outcome_counts"][outcome] >= 1
    return issue


def test_live_research_claim_assurance_matrix_passes() -> None:
    receipt = audit_research_claim_assurance(REPO_ROOT)

    assert receipt["status"] == "pass"
    assert receipt["row_count"] == 6
    assert receipt["issue_count"] == 0
    assert receipt["expected_verdicts"] == list(EXPECTED_VERDICTS)
    assert receipt["expected_outcomes"] == list(EXPECTED_OUTCOMES)
    assert receipt["verdict_counts"]["allowed"] == 6
    assert set(receipt["outcome_counts"]) == set(EXPECTED_OUTCOMES)
    assert all(count == 0 for count in receipt["outcome_counts"].values())
    assert {row["cluster_id"] for row in receipt["rows"]} == {
        "certificate_kernel_execution",
        "proof_derived_governed_mutation_authorization",
        "doctrine_fact_claim_audit",
        "command_run_singleflight",
        "finance_forecast_evaluation",
        "evidence_as_accounting",
    }


def test_assurance_flags_missing_witness_path(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    missing_ref = contract["rows"][0]["source_loci"][0]
    (repo / missing_ref).unlink()

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "ROW_WITNESS_PATH_MISSING", "missing_source_locus"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "missing_witness"
    assert issue["refs"] == [missing_ref]


def test_assurance_flags_missing_paper_module(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    missing_ref = contract["rows"][0]["paper_module"]
    (repo / missing_ref).unlink()

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "ROW_WITNESS_PATH_MISSING", "missing_paper_module"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "missing_witness"
    assert issue["refs"] == [missing_ref]


def test_assurance_flags_missing_standard(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    missing_ref = contract["rows"][0]["standard"]
    (repo / missing_ref).unlink()

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "ROW_WITNESS_PATH_MISSING", "missing_standard"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "missing_witness"
    assert issue["refs"] == [missing_ref]


def test_assurance_maps_missing_required_row_fields_to_outcomes(
    tmp_path: Path,
) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    expected_outcomes = {
        "paper_module": "missing_paper_module",
        "standard": "missing_standard",
        "source_loci": "missing_source_locus",
        "required_negative_floor": "missing_negative_floor",
        "authority_ceiling": "missing_authority_ceiling",
    }
    for field in expected_outcomes:
        contract["rows"][0].pop(field)
    _store_contract(repo, contract)

    receipt = audit_research_claim_assurance(repo)

    required_field_issues = [
        issue
        for issue in receipt["issues"]
        if issue["code"] == "ROW_REQUIRED_FIELDS_MISSING"
    ]
    observed = {
        (issue["refs"][0], issue["outcome"], issue["verdict"])
        for issue in required_field_issues
    }
    assert receipt["status"] == "blocked"
    assert observed == {
        (field, outcome, "missing_witness")
        for field, outcome in expected_outcomes.items()
    }
    for outcome in expected_outcomes.values():
        assert receipt["outcome_counts"][outcome] >= 1


def test_assurance_flags_missing_negative_floor(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    contract["rows"][0]["required_negative_floor"] = "happy path only"
    _store_contract(repo, contract)

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "ROW_NEGATIVE_FLOOR_MISSING", "missing_negative_floor"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "missing_negative_floor"


def test_assurance_flags_missing_authority_ceiling(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    contract["rows"][0]["authority_ceiling"] = ""
    _store_contract(repo, contract)

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "ROW_AUTHORITY_CEILING_MISSING", "missing_authority_ceiling"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "missing_authority_ceiling"


def test_assurance_flags_overclaim(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    contract["rows"][0][
        "positive_claim"
    ] = "This is production-ready proof correctness and release authority."
    _store_contract(repo, contract)

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "ROW_POSITIVE_CLAIM_OVERCLAIM", "overclaim_public_copy"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "overclaim"


def test_assurance_flags_unavailable_validation_probe(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    contract.pop("validation_probe")
    _store_contract(repo, contract)

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "CLUSTER_VALIDATION_PROBE_MISSING", "staged_but_unvalidated"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "blocked_by_unavailable_validation"


def test_assurance_flags_owner_claim_blocker(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    contract = _contract(repo)
    contract["rows"][0]["blocked_by_owner_claim"] = True
    _store_contract(repo, contract)

    receipt = audit_research_claim_assurance(repo)

    issue = _assert_issue_outcome(
        receipt, "ROW_OWNER_CLAIM_BLOCKS_VALIDATION", "blocked_by_owner_claim"
    )
    assert receipt["status"] == "blocked"
    assert issue["verdict"] == "blocked_by_unavailable_validation"
