from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_memory_conflict_trace,
)
import microcosm_core.organs.agent_memory_temporal_conflict_replay as agent_memory_replay
from microcosm_core.organs.agent_memory_temporal_conflict_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
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


def test_agent_memory_sha256_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "memory_episodes.json"
    body = b'{"memory_episodes":[]}\n' * 1024
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("digest should stream memory freshness input")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert agent_memory_replay._sha256(source) == (
        "sha256:" + hashlib.sha256(body).hexdigest()
    )


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
    assert result["bundle_id"] == "agent_memory_temporal_conflict_replay_trace_refactor"
    assert result["body_import_status"] == "real_macro_body_floor_landed"
    assert result["body_material_status"] == (
        "copied_non_secret_macro_agent_memory_body_with_provenance"
    )
    assert result["body_copied_material_count"] == 5
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 5
    assert source_imports["body_in_receipt"] is False
    assert source_imports["source_manifest_refs"] == [
        "examples/agent_memory_temporal_conflict_replay/"
        "exported_memory_temporal_conflict_bundle/source_module_manifest.json"
    ]
    assert set(source_imports["material_classes"]) == {
        "public_macro_doctrine_body",
        "public_macro_pattern_body",
        "public_macro_standard_body",
        "public_macro_tool_body",
    }
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 7
    assert result["public_agent_execution_trace"]["audit"]["coverage"][
        "metadata_only_private_thread_ref_coverage"
    ] is True
    assert result["public_agent_execution_trace"]["audit"]["coverage"][
        "cold_replay_receipt_coverage"
    ] is True
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["scanned_path_count"] >= 11
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


def test_agent_memory_source_modules_are_digest_verified() -> None:
    manifest_path = BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 5
    assert [row["module_id"] for row in manifest["modules"]]
    for row in manifest["modules"]:
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target_path = MICROCOSM_ROOT / target_ref
        assert target_path.is_file()
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["sha256"].startswith("sha256:")
        assert row["source_to_target_relation"] in {
            "exact_copy",
            "source_faithful_json_slice",
        }


def test_agent_memory_source_module_digest_mismatch_blocks_bundle(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_memory_temporal_conflict_replay/"
        "exported_memory_temporal_conflict_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    source_artifact = (
        bundle
        / "source_artifacts/macro_state/microcosm_portfolio/"
        "extracted_patterns_ledger/agent_memory_temporal_conflict_replay_rows.json"
    )
    source_artifact.write_text(
        source_artifact.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["body_copied_material_count"] == 5


def test_agent_memory_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_memory_temporal_conflict_replay"
    )
    args = [
        "run-memory-bundle",
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
    assert first_card["memory_conflict"]["event_count"] == 5
    assert first_card["memory_conflict"]["conflict_edge_count"] == 2
    assert first_card["body_floor"]["body_copied_material_count"] == 5
    assert "memory_rows" not in _walk_keys(first_card)
    assert "replay_rows" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "public_agent_execution_trace" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(agent_memory_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


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
