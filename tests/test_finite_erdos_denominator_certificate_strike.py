from __future__ import annotations

import json
from fractions import Fraction
from math import gcd, lcm
from pathlib import Path

from microcosm_core.engine_room.finite_denominator_order_certificate import (
    ERROR_CODES,
    compute_finite_denominator_order_certificate,
    multiplicative_order,
    verify_finite_denominator_order_certificate,
)
from microcosm_core.organs.finite_erdos_denominator_certificate_strike import (
    ANTI_CLAIM,
    AUTHORITY_CEILING,
    CLAIM_CEILING,
    EXPECTED_NEGATIVE_CASES,
    ORGAN_ID,
    build_result,
    result_card,
    run,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/finite_erdos_denominator_certificate_strike/input"


def test_fixture_matrix_passes_over_all_cases() -> None:
    result = build_result(INPUT_DIR)
    assert result["status"] == "pass"
    assert result["organ_id"] == ORGAN_ID
    assert result["case_count"] == 4
    assert result["positive_case_count"] == 2
    assert result["negative_case_count"] == 2
    assert result["passed_positive_case_count"] == 2
    assert result["observed_negative_case_count"] == 2


def test_every_declared_negative_case_is_present_and_observed() -> None:
    result = build_result(INPUT_DIR)
    negative_ids = {row["case_id"] for row in result["cases"] if row["case_type"] == "negative"}
    assert set(EXPECTED_NEGATIVE_CASES).issubset(negative_ids)
    by_id = {row["case_id"]: row for row in result["cases"]}
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        row = by_id[case_id]
        assert row["observed_ok"] is True
        for code in expected_codes:
            assert code in row["observed_error_codes"]


def test_positive_case_reports_the_certificate_facts() -> None:
    result = build_result(INPUT_DIR)
    by_id = {row["case_id"]: row for row in result["cases"]}
    simple = by_id["certificate_holds"]
    assert simple["certificate_holds"] is True
    assert simple["numerator"] == 1
    assert simple["denominator"] == 3
    assert simple["order"] == 2
    assert simple["lcm"] == 2
    reduced = by_id["certificate_holds_after_reduction"]
    assert reduced["certificate_holds"] is True
    assert reduced["reduced"] is True
    assert reduced["denominator"] == 21
    assert reduced["order"] == reduced["lcm"] == 6


def test_capsule_computes_exact_arithmetic_not_baked_numbers() -> None:
    # Independently recompute the identity for a grid of inputs and require the
    # capsule to agree exactly. This proves the organ computes at runtime.
    for base in (2, 3, 5, 10):
        for support in ([2], [3], [1, 2], [2, 3], [2, 4], [3, 6], [1, 2, 3]):
            cert = compute_finite_denominator_order_certificate(support, base)
            members = sorted(set(support))
            value = sum((Fraction(1, base**n - 1) for n in members), Fraction(0, 1))
            assert cert["numerator"] == value.numerator
            assert cert["denominator"] == value.denominator
            expected_order = multiplicative_order(base, value.denominator)
            assert cert["order"] == expected_order
            assert cert["lcm"] == lcm(*members)
            # The certified identity holds across this finite grid.
            assert cert["holds"] is True
            assert cert["order"] == cert["lcm"]


def test_closed_form_denominator_cross_checks_the_fraction_denominator() -> None:
    for base in (2, 3, 7):
        for support in ([2, 3], [2, 4], [1, 2, 3], [3, 6]):
            cert = compute_finite_denominator_order_certificate(support, base)
            big_b = base ** cert["lcm"] - 1
            a_l = sum(big_b // (base**n - 1) for n in sorted(set(support)))
            assert cert["closed_form_b"] == big_b
            assert cert["closed_form_a_l"] == a_l
            assert cert["closed_form_denominator"] == big_b // gcd(a_l, big_b)
            assert cert["denominator"] == cert["closed_form_denominator"]


def test_forged_order_is_rejected_by_recomputation() -> None:
    verdict = verify_finite_denominator_order_certificate(
        [1, 2], 2, {"numerator": 4, "denominator": 3, "order": 5}
    )
    assert verdict["valid"] is False
    assert ERROR_CODES["order"] in verdict["error_codes"]
    assert verdict["recomputed"]["order"] == 2


def test_forged_denominator_is_rejected_by_recomputation() -> None:
    verdict = verify_finite_denominator_order_certificate(
        [3], 2, {"numerator": 1, "denominator": 5, "order": 3}
    )
    assert verdict["valid"] is False
    assert ERROR_CODES["denominator"] in verdict["error_codes"]
    assert verdict["recomputed"]["denominator"] == 7


def test_true_certificate_verifies_clean() -> None:
    verdict = verify_finite_denominator_order_certificate(
        [2, 3], 2, {"numerator": 10, "denominator": 21, "order": 6}
    )
    assert verdict["valid"] is True
    assert verdict["error_codes"] == []


def test_degenerate_inputs_are_rejected() -> None:
    empty = compute_finite_denominator_order_certificate([], 2)
    assert empty["holds"] is False
    assert ERROR_CODES["empty_support"] in empty["error_codes"]
    bad_base = compute_finite_denominator_order_certificate([2], 1)
    assert bad_base["holds"] is False
    assert ERROR_CODES["bad_base"] in bad_base["error_codes"]


def test_claim_ceiling_is_negated_and_anti_claim_is_present() -> None:
    low = CLAIM_CEILING.lower()
    assert any(cue in low for cue in ("not ", "does not ", "never", "without", "no "))
    assert "erdos #257" in low
    assert "does not prove" in low
    assert ANTI_CLAIM.strip()
    assert AUTHORITY_CEILING["release_authorized"] is False
    assert AUTHORITY_CEILING["solves_erdos257"] is False
    assert AUTHORITY_CEILING["machine_checked_proof"] is False


def test_result_card_projects_status_without_bodies() -> None:
    result = build_result(INPUT_DIR)
    card = result_card(result)
    assert card["organ_id"] == ORGAN_ID
    assert card["status"] == "pass"
    assert card["case_count"] == 4
    assert "cases" not in card


def test_run_writes_body_free_receipts(tmp_path: Path) -> None:
    out = tmp_path / "receipts"
    acceptance = tmp_path / "acceptance.json"
    result = run(INPUT_DIR, out, acceptance_out=acceptance)
    assert result["status"] == "pass"
    assert result["body_in_receipt"] is False
    written = json.loads((out / f"{ORGAN_ID}_result.json").read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    acceptance_payload = json.loads(acceptance.read_text(encoding="utf-8"))
    assert acceptance_payload["real_substrate_disposition"] == "real_substrate_capsule"
    assert acceptance_payload["body_in_receipt"] is False
