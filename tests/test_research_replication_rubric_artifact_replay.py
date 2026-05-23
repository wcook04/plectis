from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_research_replication_trace,
)
from microcosm_core.organs.research_replication_rubric_artifact_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_replication_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/research_replication_rubric_artifact_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/research_replication_rubric_artifact_replay/"
    "exported_research_replication_bundle"
)


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


def test_research_replication_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/research_replication_rubric_artifact_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "research_replication_rubric_artifact_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["paper_count"] == 2
    assert result["replay_count"] == 2
    assert result["artifact_replay_count"] == 2
    assert result["cold_rerun_count"] == 2
    assert result["declared_artifact_hash_ref_count"] == 2
    assert result["declared_artifact_hash_refs"] == [
        "artifacts/model_trace.sha256",
        "artifacts/result_table.sha256",
    ]
    assert result["authority_ceiling"]["benchmark_performance_claim_authorized"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_research_replication_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/research_replication_rubric_artifact_replay",
        public_root / "fixtures/first_wave/research_replication_rubric_artifact_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/research_replication_rubric_artifact_replay/input",
        public_root / "receipts/first_wave/research_replication_rubric_artifact_replay",
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
        assert "private_paper_body" not in keys
        assert "hidden_rubric_body" not in keys
        assert "provider_payload" not in keys
        assert "private_state_scan" not in keys
        assert "body_redacted" not in keys


def test_research_replication_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_replication_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "research_replication_rubric_artifact_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_research_replication_bundle"
    assert result["bundle_id"] == "research_replication_rubric_artifact_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["paper_count"] == 2
    assert result["replay_count"] == 2
    assert result["declared_artifact_hash_ref_count"] == 2
    assert result["authority_ceiling"]["publication_authorized"] is False
    assert "public_replacement_refs" not in result
    assert "private_state_scan" not in result
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert result["body_import_verification"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
    assert (
        result["public_agent_execution_trace"]["source_faithful_refactor"][
            "verification_mode"
        ]
        == "extension_of_existing_public_refactor"
    )
    assert result["public_agent_execution_trace"]["span_count"] == 2
    assert result["public_agent_execution_trace"]["audit"]["coverage"][
        "cold_rerun_coverage"
    ] is True


def test_public_agent_execution_trace_refactor_builds_research_replay_spans() -> None:
    trace = build_public_research_replication_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert trace["bundle_id"] == "research_replication_rubric_artifact_replay_runtime_example"
    assert trace["span_count"] == 2
    assert trace["summary"]["action_kind_counts"] == {
        "research_replication_artifact_replay": 2
    }
    assert trace["summary"]["outcome_counts"] == {"success": 2}
    assert {
        span["tool_name"] for span in trace["spans"]
    } == {"research_replication_replay"}
    assert trace["audit"]["coverage"]["rubric_tree_coverage"] is True
    assert trace["audit"]["coverage"]["declared_artifact_hash_roster_coverage"] is True
    assert trace["audit"]["coverage"]["metric_script_coverage"] is True
    assert trace["audit"]["coverage"]["grader_report_coverage"] is True
    assert trace["audit"]["coverage"]["budget_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["failure_taxonomy_coverage"] is True
    assert trace["audit"]["coverage"]["cold_rerun_coverage"] is True
    assert "system/lib/agent_execution_trace.py" in trace["source_refs"]
