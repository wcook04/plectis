from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_memory_conflict_trace,
)
from microcosm_core.organs.agent_memory_temporal_conflict_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_memory_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_memory_temporal_conflict_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_memory_temporal_conflict_replay/"
    "exported_memory_temporal_conflict_bundle"
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


def test_agent_memory_temporal_conflict_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_memory_temporal_conflict_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["event_count"] == 5
    assert result["episode_count"] == 3
    assert result["decision_counts"] == {
        "ADD": 2,
        "DELETE": 1,
        "NOOP": 1,
        "UPDATE": 1,
    }
    assert result["conflict_edge_count"] == 2
    assert result["stale_downgrade_count"] == 2
    assert result["prompt_adoption_observation_count"] == 1
    assert result["memory_enabled_replay_count"] == 1
    assert result["memory_disabled_replay_count"] == 1
    assert result["answer_delta_ref"]
    assert result["authority_ceiling"]["private_transcript_export_authorized"] is False
    assert result["authority_ceiling"]["memory_as_source_authority_authorized"] is False
    assert result["authority_ceiling"]["active_injection_authority_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_agent_memory_temporal_conflict_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_memory_temporal_conflict_replay",
        public_root / "fixtures/first_wave/agent_memory_temporal_conflict_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_memory_temporal_conflict_replay/input",
        public_root / "receipts/first_wave/agent_memory_temporal_conflict_replay",
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
        assert "raw_transcript" not in keys
        assert "raw_transcript_body" not in keys
        assert "private_thread_body" not in keys
        assert "provider_payload" not in keys
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "private_state_scan" not in keys
        assert "body_redacted" not in keys


def test_agent_memory_temporal_conflict_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_memory_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_memory_temporal_conflict_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_memory_temporal_conflict_bundle"
    assert result["bundle_id"] == "agent_memory_temporal_conflict_replay_runtime_example"
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 7
    assert result["public_agent_execution_trace"]["audit"]["coverage"][
        "metadata_only_private_thread_ref_coverage"
    ] is True
    assert result["public_agent_execution_trace"]["audit"]["coverage"][
        "cold_replay_receipt_coverage"
    ] is True
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "public_replacement_refs" not in result
    assert "private_state_scan" not in result
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["event_count"] == 5
    assert result["decision_counts"]["UPDATE"] == 1
    assert result["conflict_edge_count"] == 2
    assert result["stale_downgrade_count"] == 2
    assert result["authority_ceiling"]["live_memory_product_claim_authorized"] is False


def test_public_agent_execution_trace_refactor_builds_memory_conflict_spans() -> None:
    trace = build_public_memory_conflict_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert trace["span_count"] == 7
    assert trace["source_faithful_refactor"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
    assert trace["summary"]["action_kind_counts"] == {
        "memory_temporal_conflict_cold_replay": 2,
        "memory_temporal_conflict_event": 5,
    }
    assert trace["audit"]["coverage"]["no_private_memory_body_coverage"] is True
    assert trace["audit"]["coverage"]["memory_enabled_evidence_coverage"] is True
