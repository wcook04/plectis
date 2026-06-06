from __future__ import annotations

import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import microcosm_core.engine_room.lean_proof_search_lab as lean_lab
from microcosm_core.engine_room.lean_proof_search_lab import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    LeanProblem,
    check_candidate_with_lean,
    evaluate_case,
    evaluate_fixture_dir,
    main as lean_lab_main,
    run_and_or_search,
    run_blind_policy_ablation,
    run_statement_only_hammer,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_lean_proof_search_lab/input"
FAST_CLI_FIXTURE = INPUT_DIR / "oracle_field_negative.json"


def _and_intro_problem() -> LeanProblem:
    return LeanProblem(
        problem_id="unit_and_intro",
        theorem_name="unit_and_intro",
        theorem_signature="theorem unit_and_intro (p q : Prop) : p -> q -> And p q := by",
        target_shape="and_intro",
    )


def _fast_cli_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "lean_cli_input"
    input_dir.mkdir()
    shutil.copy2(FAST_CLI_FIXTURE, input_dir / FAST_CLI_FIXTURE.name)
    return input_dir


def test_and_or_search_finds_clean_lean_checked_proof() -> None:
    result = run_and_or_search(_and_intro_problem(), beam_width=4, max_depth=2)
    assert result["accepted"] is True
    assert result["selected"]["tactic_id"] == "constructor"
    assert result["selected"]["axiom_audit"]["clean"] is True
    assert result["proof_reconstruction"]["reconstructed_from_closed_search"] is True


def test_statement_only_hammer_records_action_values_without_oracle_credit() -> None:
    result = run_statement_only_hammer(_and_intro_problem())
    assert result["accepted"] is True
    assert result["adapter_direct_candidate_allowed"] is False
    assert result["oracle_repair_allowed"] is False
    assert any(row["posterior_score"] > 1 for row in result["action_value_table"])
    assert all(row["truth_side_body_used"] is False for row in result["action_manifest"])


def test_oracle_firewall_rejects_forward_candidate_body() -> None:
    case = {
        "case_id": "unit_oracle_firewall",
        "expected_status": "fail",
        "expected_failure_kind": "oracle_firewall_violation",
        "lab": {
            "problems": [
                {
                    "problem_id": "leaky",
                    "theorem_name": "leaky",
                    "theorem_signature": "theorem leaky (p : Prop) : p -> p := by",
                    "candidate_body": ["intro h0", "exact h0"],
                }
            ]
        },
    }
    receipt = evaluate_case(case)
    assert receipt["expectation_met"] is True
    assert receipt["receipt"]["forward_oracle_firewall_report"]["violation_count"] == 1


def test_oracle_firewall_rejects_nested_payload_fields() -> None:
    case = {
        "case_id": "unit_nested_oracle_firewall",
        "expected_status": "fail",
        "expected_failure_kind": "oracle_firewall_violation",
        "lab": {
            "problems": [
                {
                    "problem_id": "nested_leaky",
                    "theorem_name": "nested_leaky",
                    "theorem_signature": "theorem nested_leaky (p : Prop) : p -> p := by",
                    "metadata": {
                        "provider_text": "provider payload",
                        "repair": {"oracle_needed_premise_ids": ["private"]},
                    },
                }
            ]
        },
    }
    receipt = evaluate_case(case)
    report = receipt["receipt"]["forward_oracle_firewall_report"]
    assert receipt["expectation_met"] is True
    assert report["violation_count"] == 1
    assert report["findings"][0]["forbidden_field_paths"] == [
        "metadata.provider_text",
        "metadata.repair.oracle_needed_premise_ids",
    ]


def test_problem_id_memorized_policy_fails_ablation() -> None:
    problem = LeanProblem(
        problem_id="ps_fake_or_comm_but_goal_is_and_intro",
        theorem_name="ablation_unit",
        theorem_signature="theorem ablation_unit (p q : Prop) : p -> q -> And p q := by",
        target_shape="and_intro",
    )
    report = run_blind_policy_ablation([problem], policy_kind="memorized_by_id")
    assert report["problem_id_conditioned_policy_used"] is True
    assert report["problem_id_ablation_passed"] is False
    assert report["mismatch_count"] == 1
    assert report["lean_check_skipped_count"] == 2


def test_problem_id_policy_mismatch_short_circuits_lean_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    problem = LeanProblem(
        problem_id="ps_fake_or_comm_but_goal_is_and_intro",
        theorem_name="ablation_unit",
        theorem_signature="theorem ablation_unit (p q : Prop) : p -> q -> And p q := by",
        target_shape="and_intro",
    )

    def fail_lean_check(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("policy mismatch should not invoke Lean checks")

    monkeypatch.setattr(lean_lab, "check_candidate_with_lean", fail_lean_check)
    report = run_blind_policy_ablation([problem], policy_kind="memorized_by_id")
    assert report["problem_id_ablation_passed"] is False
    assert report["mismatch_count"] == 1
    assert report["lean_check_skipped_count"] == 2


def test_sorry_candidate_is_rejected_by_axiom_gate() -> None:
    problem = LeanProblem(
        problem_id="sorry_unit",
        theorem_name="sorry_unit",
        theorem_signature="theorem sorry_unit : True := by",
        target_shape="true_intro",
    )
    result = check_candidate_with_lean(problem, ["sorry"])
    assert result["accepted"] is False
    assert result["axiom_audit"]["sorry_present"] is True


def test_sorry_candidate_static_rejection_avoids_lean_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    problem = LeanProblem(
        problem_id="sorry_unit",
        theorem_name="sorry_unit",
        theorem_signature="theorem sorry_unit : True := by",
        target_shape="true_intro",
    )

    def fail_subprocess(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("static sorry rejection should not invoke subprocess.run")

    monkeypatch.setattr(lean_lab.subprocess, "run", fail_subprocess)
    result = check_candidate_with_lean(problem, ["sorry"])
    assert result["accepted"] is False
    assert result["lean_status"] == "STATIC_REJECT"
    assert result["axiom_audit"]["sorry_present"] is True


def test_lean_version_probe_uses_path_lookup_without_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lean_lab._lean_version.cache_clear()
    monkeypatch.setattr(lean_lab.shutil, "which", lambda _name: "/tmp/fake-lean")

    def fail_subprocess(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("lean availability probe should not spawn lean --version")

    monkeypatch.setattr(lean_lab.subprocess, "run", fail_subprocess)

    result = lean_lab._lean_version()

    assert result == {
        "available": True,
        "path": "/tmp/fake-lean",
        "version": "not_probed_on_hot_path",
        "version_check_status": "skipped_hot_path",
        "version_probe_skipped": True,
    }
    lean_lab._lean_version.cache_clear()


def test_equivalent_lean_checks_singleflight_concurrent_cache_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache: dict[tuple[object, ...], dict[str, object]] = {}
    call_count = 0
    entered = threading.Event()
    release = threading.Event()

    def fake_cached(*args: object) -> dict[str, object]:
        nonlocal call_count
        if args not in cache:
            call_count += 1
            entered.set()
            assert release.wait(1.0)
            cache[args] = {
                "lean_status": "PASS",
                "accepted": True,
                "returncode": 0,
                "stdout": "does not depend on any axioms",
                "stderr": "",
                "duration_ms": 1,
                "axiom_audit": {"status": "clean", "clean": True},
            }
        return cache[args]

    monkeypatch.setattr(lean_lab, "_check_candidate_with_lean_cached", fake_cached)
    problem = _and_intro_problem()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                lean_lab.check_candidate_with_lean,
                problem,
                ("intro hp", "intro hq", "constructor", "exact hp", "exact hq"),
            )
            for _ in range(2)
        ]
        assert entered.wait(1.0)
        release.set()
        results = [future.result(timeout=1.0) for future in futures]

    assert [result["accepted"] for result in results] == [True, True]
    assert call_count == 1


def test_fixture_dir_parallelizes_cases_and_preserves_sorted_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("b_case.json", "a_case.json", "c_case.json"):
        (tmp_path / name).write_text(json.dumps({"case_id": name}), encoding="utf-8")
    first_pair = {"a_case", "b_case"}
    started: list[str] = []
    lock = threading.Lock()
    release = threading.Event()

    def fake_evaluate_case(case: object, *, path: str = "") -> dict[str, object]:
        case_id = Path(path).stem
        if case_id in first_pair:
            with lock:
                started.append(case_id)
                if len(started) == len(first_pair):
                    release.set()
            assert release.wait(1.0)
        return {"case_id": case_id, "expectation_met": True}

    monkeypatch.setattr(lean_lab, "FIXTURE_EVALUATION_MAX_WORKERS", 2)
    monkeypatch.setattr(lean_lab, "evaluate_case", fake_evaluate_case)

    result = lean_lab.evaluate_fixture_dir(tmp_path)

    assert result["status"] == "pass"
    assert [case["case_id"] for case in result["cases"]] == [
        "a_case",
        "b_case",
        "c_case",
    ]
    assert set(started) == first_pair


def test_fixture_matrix_matches_lean_lab_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 5
    assert receipt["passed_case_count"] == 5
    assert "not_neural_theorem_prover" in ANTI_CLAIMS
    assert "not neural theorem proving" in CLAIM_CEILING


def test_module_cli_emits_json_receipt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    input_dir = _fast_cli_input(tmp_path)
    assert lean_lab_main(
        [
            "evaluate-fixtures",
            "--input",
            str(input_dir),
            "--json",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["organ_id"] == "engine_room_lean_proof_search_lab"
    assert payload["status"] == "pass"
    assert payload["case_count"] == 1
