from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.organs.doctrine_fact_claim_audit import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_doctrine_fact_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/doctrine_fact_claim_audit/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/doctrine_fact_claim_audit/exported_doctrine_fact_claim_audit_bundle"
)


def test_doctrine_fact_claim_audit_validates_fact_loci_and_dag(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/doctrine_fact_claim_audit",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["exercise"]["fact_count"] == 3
    assert result["exercise"]["verified_code_locus_count"] == 3
    assert result["exercise"]["dag_edge_count"] == 2
    assert result["exercise"]["numeric_claim_case_count"] == 2
    assert result["exercise"]["unbound_numeric_detector_case_count"] == 1
    assert result["exercise"]["unbound_numeric_detection_count"] == 1
    assert result["exercise"]["unbound_numeric_blocking_count"] == 0
    assert result["exercise"]["comprehension_engine_claim_authorized"] is False
    assert result["source_module_manifest"]["module_count"] == 2
    assert result["source_module_manifest"]["all_required_anchors_present"] is True


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/doctrine_fact_claim_audit",
        public_root / "examples/doctrine_fact_claim_audit",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/doctrine_fact_claim_audit",
        public_root / "fixtures/first_wave/doctrine_fact_claim_audit",
    )
    return public_root / "fixtures/first_wave/doctrine_fact_claim_audit/input"


def test_doctrine_fact_claim_audit_rejects_dead_code_locus(tmp_path: Path) -> None:
    fixture = _copy_public_fixture(tmp_path)
    public_root = fixture.parents[3]
    assertions_path = fixture / "fact_assertions.json"
    assertions = json.loads(assertions_path.read_text(encoding="utf-8"))
    assertions["facts"][0]["code_loci"][0]["anchor"] = "not_present_in_copied_body"
    assertions_path.write_text(json.dumps(assertions, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/doctrine_fact_claim_audit")

    assert result["status"] == "blocked"
    assert "DOCTRINE_CODE_LOCUS_ANCHOR_MISSING" in result["error_codes"]


def test_doctrine_fact_claim_audit_rejects_missing_code_locus(tmp_path: Path) -> None:
    fixture = _copy_public_fixture(tmp_path)
    public_root = fixture.parents[3]
    assertions_path = fixture / "fact_assertions.json"
    assertions = json.loads(assertions_path.read_text(encoding="utf-8"))
    assertions["facts"][0]["code_loci"] = []
    assertions_path.write_text(json.dumps(assertions, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/doctrine_fact_claim_audit")

    assert result["status"] == "blocked"
    assert "DOCTRINE_CODE_LOCUS_MISSING" in result["error_codes"]


def test_doctrine_fact_claim_audit_rejects_dead_dag_ref(tmp_path: Path) -> None:
    fixture = _copy_public_fixture(tmp_path)
    public_root = fixture.parents[3]
    dag_path = fixture / "fact_dag.json"
    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    dag["edges"][0]["to"] = "missing_fact_id"
    dag_path.write_text(json.dumps(dag, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/doctrine_fact_claim_audit")

    assert result["status"] == "blocked"
    assert "DOCTRINE_FACT_DAG_DEAD_REF" in result["error_codes"]


def test_doctrine_fact_claim_audit_rejects_unbound_numeric_claim(tmp_path: Path) -> None:
    fixture = _copy_public_fixture(tmp_path)
    public_root = fixture.parents[3]
    numeric_claims_path = fixture / "numeric_claims.json"
    numeric_claims = json.loads(numeric_claims_path.read_text(encoding="utf-8"))
    numeric_claims["cases"][0]["asserted_sections"] = []
    numeric_claims_path.write_text(json.dumps(numeric_claims, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/doctrine_fact_claim_audit")

    assert result["status"] == "blocked"
    assert "DOCTRINE_UNBOUND_NUMERIC_CLAIM" in result["error_codes"]
    assert "DOCTRINE_VOLATILE_NUMERIC_UNBOUND" in result["error_codes"]


def test_doctrine_fact_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/doctrine_fact_claim_audit",
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


def test_doctrine_fact_bundle_runs(tmp_path: Path) -> None:
    result = run_doctrine_fact_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/doctrine_fact_claim_audit",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_doctrine_fact_claim_audit_bundle"
