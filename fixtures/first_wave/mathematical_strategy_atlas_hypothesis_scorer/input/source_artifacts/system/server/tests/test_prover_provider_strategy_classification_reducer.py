from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.meta.factory import reduce_prover_provider_receipts as reducer


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _receipt(tmp_path: Path, receipt_id: str) -> Path:
    path = tmp_path / f"{receipt_id}.json"
    _write_json(
        path,
        {
            "receipt_id": receipt_id,
            "provider_id": "nvidia_nim",
            "model_id": "deepseek-ai/deepseek-v4-pro",
            "task_class": "prover_strategy_classification",
            "status": "ok",
            "validation_result": {"passed": True, "violations": []},
            "latency_ms": 8,
            "cost": {"estimated_usd": 0},
            "usage": {"total_tokens": 4},
        },
    )
    return path


def _row_patch(
    tmp_path: Path,
    patch_id: str,
    receipt_id: str,
    *,
    proposed_value: dict,
) -> Path:
    path = tmp_path / f"{patch_id}.json"
    _write_json(
        path,
        {
            "patch_id": patch_id,
            "receipt_id": receipt_id,
            "target_row_id": "prover_problem:strategy_nat_succ_injective:strategy_classification_4kb",
            "target_facet": "strategy_id_advisory",
            "proposed_value": proposed_value,
        },
    )
    return path


def _transform_job(tmp_path: Path) -> Path:
    path = tmp_path / "tj_strategy_classification.json"
    _write_json(
        path,
        {
            "id": "tj_strategy_classification",
            "task_class": "prover_strategy_classification",
            "target_row_id": "prover_problem:strategy_nat_succ_injective:strategy_classification_4kb",
            "target_facet": "strategy_id_advisory",
            "input_packet": {
                "prover_context_pack": {
                    "context_pack_id": "pcp_strategy_test",
                    "target_problem_id": "strategy_nat_succ_injective",
                    "graph_role": "provider_strategy_classification",
                    "deliverable_type": "strategy_id_classification",
                    "context_budget": {"bytes": 4096, "kib": 4},
                    "forbidden_material": [
                        "candidate_body",
                        "ideal_body",
                        "repair_body",
                    ],
                }
            },
            "provider_selection_policy": {"context_recipe_id": "strategy_classification_4kb"},
        },
    )
    return path


def _valid_advisory(strategy_id: str = "constructor_injectivity") -> dict:
    return {
        "strategy_id": strategy_id,
        "confidence": 0.91,
        "reasons": ["Nat.succ equality target matches constructor injectivity card"],
        "decomposition_hint": "introduce hypothesis then apply Nat.succ.inj",
        "expected_tactic_family": ["intro", "exact Nat.succ.inj"],
        "expected_premise_ids": ["premise_nat_succ_inj"],
        "forbidden_output_audit": {
            "contains_lean_proof_body": False,
            "contains_full_tactic_script": False,
            "contains_oracle_material": False,
        },
        "omissions": [],
    }


def test_strategy_classification_reducer_accepts_valid_advisory(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, "rc_strategy_valid")
    row_patch = _row_patch(
        tmp_path,
        "rp_strategy_valid",
        "rc_strategy_valid",
        proposed_value=_valid_advisory("constructor_injectivity"),
    )
    transform_job = _transform_job(tmp_path)

    summary = reducer.reduce_receipt(
        receipt_path=receipt,
        row_patch_path=row_patch,
        transform_job_path=transform_job,
        run_root=tmp_path / "run",
        timeout_seconds=30,
    )

    latest = summary["latest_reduction"]
    assert latest["task_class"] == reducer.STRATEGY_CLASSIFICATION_TASK_CLASS
    assert latest["reducer_status"] == "ok"
    assert latest["accepted_by_reducer"] is True
    assert latest["strategy_id"] == "constructor_injectivity"

    advisory_path = tmp_path / "run" / latest["strategy_advisory_row"]
    advisory = json.loads(advisory_path.read_text(encoding="utf-8"))
    assert advisory["schema_version"] == "provider_strategy_advisory_row_v0"
    assert advisory["strategy_id"] == "constructor_injectivity"
    assert advisory["leakage_audit"]["status"] == "PASS"
    assert advisory["provider_results_counted"] is False
    assert advisory["reducer_status"] == "ok"
    assert advisory["accepted_by_reducer"] is True


def test_strategy_classification_reducer_rejects_invalid_strategy_id(tmp_path: Path) -> None:
    bad_advisory = _valid_advisory()
    bad_advisory["strategy_id"] = "not_a_real_strategy"

    receipt = _receipt(tmp_path, "rc_strategy_bad_id")
    row_patch = _row_patch(
        tmp_path,
        "rp_strategy_bad_id",
        "rc_strategy_bad_id",
        proposed_value=bad_advisory,
    )
    transform_job = _transform_job(tmp_path)

    summary = reducer.reduce_receipt(
        receipt_path=receipt,
        row_patch_path=row_patch,
        transform_job_path=transform_job,
        run_root=tmp_path / "run",
        timeout_seconds=30,
    )

    latest = summary["latest_reduction"]
    assert latest["reducer_status"] == "invalid_strategy_id"
    assert latest["accepted_by_reducer"] is False
    assert latest["strategy_id"] == "not_a_real_strategy"


def test_strategy_classification_reducer_rejects_lean_proof_body_leakage(
    tmp_path: Path,
) -> None:
    leaking_advisory = _valid_advisory()
    leaking_advisory["lean_proof_body"] = "intro h; exact Nat.succ.inj h"

    receipt = _receipt(tmp_path, "rc_strategy_leak")
    row_patch = _row_patch(
        tmp_path,
        "rp_strategy_leak",
        "rc_strategy_leak",
        proposed_value=leaking_advisory,
    )
    transform_job = _transform_job(tmp_path)

    summary = reducer.reduce_receipt(
        receipt_path=receipt,
        row_patch_path=row_patch,
        transform_job_path=transform_job,
        run_root=tmp_path / "run",
        timeout_seconds=30,
    )

    latest = summary["latest_reduction"]
    assert latest["reducer_status"] == "invalid_leakage"
    assert latest["accepted_by_reducer"] is False

    advisory_path = tmp_path / "run" / latest["strategy_advisory_row"]
    advisory = json.loads(advisory_path.read_text(encoding="utf-8"))
    assert advisory["leakage_audit"]["status"] == "FAIL"
    assert advisory["leakage_audit"]["contains_lean_proof_body"] is True


def test_strategy_classification_reducer_rejects_explicit_audit_failure(tmp_path: Path) -> None:
    audit_failing_advisory = _valid_advisory()
    audit_failing_advisory["forbidden_output_audit"]["contains_oracle_material"] = True

    receipt = _receipt(tmp_path, "rc_strategy_audit_fail")
    row_patch = _row_patch(
        tmp_path,
        "rp_strategy_audit_fail",
        "rc_strategy_audit_fail",
        proposed_value=audit_failing_advisory,
    )
    transform_job = _transform_job(tmp_path)

    summary = reducer.reduce_receipt(
        receipt_path=receipt,
        row_patch_path=row_patch,
        transform_job_path=transform_job,
        run_root=tmp_path / "run",
        timeout_seconds=30,
    )

    latest = summary["latest_reduction"]
    assert latest["reducer_status"] == "invalid_leakage"
    assert latest["accepted_by_reducer"] is False

    advisory_path = tmp_path / "run" / latest["strategy_advisory_row"]
    advisory = json.loads(advisory_path.read_text(encoding="utf-8"))
    assert advisory["leakage_audit"]["status"] == "FAIL"
    assert advisory["leakage_audit"]["contains_oracle_material"] is True


def test_strategy_classification_reducer_handles_missing_strategy_id(tmp_path: Path) -> None:
    missing_id_advisory = _valid_advisory()
    missing_id_advisory.pop("strategy_id")

    receipt = _receipt(tmp_path, "rc_strategy_missing_id")
    row_patch = _row_patch(
        tmp_path,
        "rp_strategy_missing_id",
        "rc_strategy_missing_id",
        proposed_value=missing_id_advisory,
    )
    transform_job = _transform_job(tmp_path)

    summary = reducer.reduce_receipt(
        receipt_path=receipt,
        row_patch_path=row_patch,
        transform_job_path=transform_job,
        run_root=tmp_path / "run",
        timeout_seconds=30,
    )

    latest = summary["latest_reduction"]
    assert latest["reducer_status"] == "missing_strategy_id"
    assert latest["accepted_by_reducer"] is False


def test_strategy_classification_recipe_round_trips_through_recipe_registry() -> None:
    from tools.meta.factory import run_prover_graph_benchmark as harness

    recipe = harness._provider_context_recipe("strategy_classification_4kb")
    assert recipe["graph_role"] == "provider_strategy_classification"
    assert recipe["deliverable_type"] == "strategy_id_classification"
    assert "strategy_atlas" in recipe["sections"]

    schema = harness._strategy_classification_output_schema()
    assert schema["properties"]["strategy_id"]["enum"]
    enum_ids = set(schema["properties"]["strategy_id"]["enum"])
    expected = set(harness._known_strategy_ids())
    assert enum_ids == expected
    assert "lean_proof_body" not in schema["properties"]
    assert "lean_proof_body" not in schema["required"]


def test_known_strategy_ids_match_strategy_atlas() -> None:
    from tools.meta.factory import run_prover_graph_benchmark as harness

    atlas = harness._strategy_cards()
    atlas_ids = tuple(card["strategy_id"] for card in atlas["cards"])
    assert harness._known_strategy_ids() == atlas_ids
    assert len(atlas_ids) == 8


def test_strategy_match_comparison_computes_match_rate_and_anti_cheat_fields() -> None:
    advisories = [
        {
            "problem_id": "strategy_nat_succ_injective",
            "strategy_id": "constructor_injectivity",
            "reducer_status": "ok",
            "accepted_by_reducer": True,
            "leakage_audit": {"status": "PASS"},
            "receipt_id": "rc_a",
            "confidence": 0.9,
        },
        {
            "problem_id": "strategy_nat_add_comm",
            "strategy_id": "equality_normal_form",
            "reducer_status": "ok",
            "accepted_by_reducer": True,
            "leakage_audit": {"status": "PASS"},
            "receipt_id": "rc_b",
            "confidence": 0.7,
        },
        {
            "problem_id": "strategy_bool_not_not",
            "strategy_id": "not_a_real_strategy",
            "reducer_status": "invalid_strategy_id",
            "accepted_by_reducer": False,
            "leakage_audit": {"status": "PASS"},
            "receipt_id": "rc_c",
            "confidence": 0.5,
        },
        {
            "problem_id": "strategy_list_reverse",
            "strategy_id": "symmetry_or_orientation",
            "reducer_status": "invalid_leakage",
            "accepted_by_reducer": False,
            "leakage_audit": {"status": "FAIL"},
            "receipt_id": "rc_d",
            "confidence": 0.8,
        },
    ]
    deterministic_by_problem = {
        "strategy_nat_succ_injective": "constructor_injectivity",
        "strategy_nat_add_comm": "recursive_data_induction",
        "strategy_bool_not_not": "equality_normal_form",
        "strategy_list_reverse": "symmetry_or_orientation",
    }
    comparison = reducer.compute_strategy_match_comparison(
        provider_advisory_rows=advisories,
        deterministic_strategy_by_problem=deterministic_by_problem,
        matched_problem_manifest_digest="sha256:test",
    )

    assert comparison["schema_version"] == "provider_strategy_match_comparison_v0"
    assert comparison["provider_results_counted"] is False
    assert comparison["comparable_count"] == 2
    assert comparison["match_count"] == 1
    assert comparison["strategy_match_rate"] == 0.5
    assert comparison["accepted_provider_count"] == 2
    assert comparison["rejected_provider_count"] == 2
    assert comparison["invalid_provider_strategy_count"] == 1
    assert comparison["leakage_rejection_count"] == 1
    assert comparison["missing_provider_strategy_count"] == 0

    by_problem = {row["problem_id"]: row for row in comparison["rows"]}
    assert by_problem["strategy_nat_succ_injective"]["strategy_match"] is True
    assert by_problem["strategy_nat_add_comm"]["strategy_match"] is False
    assert by_problem["strategy_bool_not_not"]["strategy_match"] is False
    assert by_problem["strategy_list_reverse"]["strategy_match"] is False


def test_strategy_match_comparison_handles_empty_input() -> None:
    comparison = reducer.compute_strategy_match_comparison(
        provider_advisory_rows=[],
        deterministic_strategy_by_problem={},
    )
    assert comparison["comparable_count"] == 0
    assert comparison["match_count"] == 0
    assert comparison["strategy_match_rate"] is None
    assert comparison["provider_results_counted"] is False
    assert comparison["rows"] == []
