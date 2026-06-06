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


def _copy_bundle(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_memory_temporal_conflict_replay/"
        "exported_memory_temporal_conflict_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    return bundle


def _copy_first_wave_public_root(
    tmp_path: Path,
    *,
    include_examples: bool = True,
) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_memory_temporal_conflict_replay",
        public_root / "fixtures/first_wave/agent_memory_temporal_conflict_replay",
    )
    if include_examples:
        shutil.copytree(
            MICROCOSM_ROOT / "examples/agent_memory_temporal_conflict_replay",
            public_root / "examples/agent_memory_temporal_conflict_replay",
        )
    fixture_input = (
        public_root / "fixtures/first_wave/agent_memory_temporal_conflict_replay/input"
    )
    return public_root, fixture_input


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    acceptance_path = (
        tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_memory_temporal_conflict_replay_fixture_acceptance.json"
    )
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
        acceptance_out=acceptance_path,
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
    assert result["semantic_recompute"]["status"] == "pass"
    assert result["semantic_recompute"]["checked_conflict_count"] == 2
    assert result["semantic_recompute"]["rejected_conflict_count"] == 0
    assert result["prompt_adoption_observation_count"] == 1
    assert result["memory_enabled_replay_count"] == 1
    assert result["memory_disabled_replay_count"] == 1
    assert result["answer_delta_ref"]
    assert result["authority_ceiling"]["private_transcript_export_authorized"] is False
    assert result["authority_ceiling"]["memory_as_source_authority_authorized"] is False
    assert result["authority_ceiling"]["active_injection_authority_authorized"] is False
    assert result["source_evidence_posture"]["real_source_floor"] == (
        "copied_non_secret_macro_agent_memory_body_with_provenance"
    )
    assert result["body_material_status"] == (
        "copied_non_secret_macro_agent_memory_body_with_provenance"
    )
    assert result["body_copied_material_count"] == 5
    assert all(row["sanitized_real_episode"] is True for row in result["memory_rows"])
    assert all(row["source_artifact_ref"] for row in result["memory_rows"])
    assert all(row["source_event_ref"] for row in result["memory_rows"])
    assert all(row["source_event_verified"] is True for row in result["memory_rows"])
    assert all(row["event_timestamp"] for row in result["memory_rows"])
    assert all(row["memory_priority"] is not None for row in result["memory_rows"])
    assert all(row["source_trust_score"] is not None for row in result["memory_rows"])
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    acceptance = _json(acceptance_path)
    assert acceptance["schema_version"] == (
        "agent_memory_temporal_conflict_replay_fixture_acceptance_v1"
    )
    assert acceptance["validator_id"] == (
        "validator.microcosm.organs.agent_memory_temporal_conflict_replay"
    )
    assert set(acceptance["accepted_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert acceptance["missing_negative_cases"] == []
    assert acceptance["source_open_body_imports"]["status"] == "pass"
    assert acceptance["body_material_status"] == (
        "copied_non_secret_macro_agent_memory_body_with_provenance"
    )
    assert acceptance["body_copied_material_count"] == 5
    assert acceptance["source_open_body_imports"]["body_in_receipt"] is False


def test_agent_memory_first_wave_fixture_mirrors_exported_real_memory_stream() -> None:
    for name in (
        "memory_episodes.json",
        "memory_policy.json",
        "replay_observations.json",
    ):
        assert (FIXTURE_INPUT / name).read_bytes() == (BUNDLE_INPUT / name).read_bytes()

    memory_payload = _json(FIXTURE_INPUT / "memory_episodes.json")
    source_posture = memory_payload["source_evidence_posture"]
    assert source_posture == {
        "body_in_receipt": False,
        "private_bodies_exported": False,
        "real_source_floor": "copied_non_secret_macro_agent_memory_body_with_provenance",
        "source_module_manifest_ref": (
            "examples/agent_memory_temporal_conflict_replay/"
            "exported_memory_temporal_conflict_bundle/source_module_manifest.json"
        ),
    }
    assert {row["decision"] for row in memory_payload["memory_events"]} == {
        "ADD",
        "DELETE",
        "NOOP",
        "UPDATE",
    }
    assert all(
        row["sanitized_real_episode"] is True
        and row["source_artifact_ref"]
        and row["source_event_ref"]
        and row["event_timestamp"]
        and row["memory_priority"] is not None
        and row["source_trust_score"] is not None
        and row["metadata_only_ref"] is True
        and row["body_exported"] is False
        for row in memory_payload["memory_events"]
    )
    policy_payload = _json(FIXTURE_INPUT / "memory_policy.json")
    assert {
        "event_timestamp",
        "memory_priority",
        "source_trust_score",
    }.issubset(set(policy_payload["required_memory_event_fields"]))


def test_agent_memory_temporal_conflict_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_first_wave_public_root(tmp_path)

    result = run(
        fixture_input,
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


def test_agent_memory_temporal_conflict_first_wave_requires_real_source_manifest(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_first_wave_public_root(
        tmp_path,
        include_examples=False,
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SOURCE_MODULE_MANIFEST_MISSING" in result["error_codes"]
    assert result["source_open_body_imports"]["status"] == "blocked"


def test_agent_memory_temporal_conflict_first_wave_rejects_source_body_tamper(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_first_wave_public_root(tmp_path)
    source_artifact = (
        public_root
        / "examples/agent_memory_temporal_conflict_replay/"
        "exported_memory_temporal_conflict_bundle/source_artifacts/macro_state/"
        "microcosm_portfolio/extracted_patterns_ledger/"
        "agent_memory_temporal_conflict_replay_rows.json"
    )
    source_artifact.write_text(
        source_artifact.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_open_body_imports"]["status"] == "blocked"


def test_agent_memory_temporal_conflict_rejects_shape_only_synthetic_fixture(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_first_wave_public_root(tmp_path)
    episodes_path = fixture_input / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    del payload["source_evidence_posture"]
    for row in payload["memory_events"]:
        row.pop("sanitized_real_episode", None)
        row.pop("source_artifact_ref", None)
        row.pop("source_event_ref", None)
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_REAL_TRACE_SOURCE_EVIDENCE_MISSING" in result["error_codes"]
    assert "MEMORY_CONFLICT_REAL_TRACE_SOURCE_POSTURE_MISSING" in result["error_codes"]


def test_agent_memory_temporal_conflict_rejects_unresolved_replay_refs(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_first_wave_public_root(tmp_path)
    replay_path = fixture_input / "replay_observations.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    payload["replay_observations"][0]["episode_id"] = "missing_episode"
    payload["replay_observations"][0]["evidence_used_refs"] = ["missing_evidence"]
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_REPLAY_EPISODE_UNRESOLVED" in result["error_codes"]
    assert "MEMORY_CONFLICT_REPLAY_EVIDENCE_UNRESOLVED" in result["error_codes"]
    replay_row = next(
        row
        for row in result["replay_rows"]
        if row["observation_id"] == "episode_c_memory_enabled_replay"
    )
    assert "replay_episode_unresolved" in replay_row["reason_codes"]
    assert "replay_evidence_unresolved" in replay_row["reason_codes"]
    assert replay_row["episode_resolved"] is False
    assert replay_row["unresolved_evidence_refs"] == ["missing_evidence"]


def test_agent_memory_temporal_conflict_rejects_mutated_update_without_edge(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_first_wave_public_root(tmp_path)
    episodes_path = fixture_input / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    update_row = next(
        row
        for row in payload["memory_events"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    del update_row["conflict_edge_ref"]
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_UPDATE_DELETE_EDGE_MISSING" in result["error_codes"]
    assert result["conflict_edge_count"] == 1
    update_result = next(
        row
        for row in result["memory_rows"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    assert update_result["computed_verdict"] == "quarantine"
    assert "temporal_conflict_edge_missing" in update_result["reason_codes"]


def test_agent_memory_temporal_conflict_rejects_memory_replay_without_evidence(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_first_wave_public_root(tmp_path)
    replay_path = fixture_input / "replay_observations.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    enabled_row = next(
        row
        for row in payload["replay_observations"]
        if row["observation_id"] == "episode_c_memory_enabled_replay"
    )
    enabled_row["evidence_used_refs"] = []
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/agent_memory_temporal_conflict_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert (
        "MEMORY_CONFLICT_MEMORY_ENABLED_REPLAY_WITHOUT_EVIDENCE"
        in result["error_codes"]
    )
    replay_row = next(
        row
        for row in result["replay_rows"]
        if row["observation_id"] == "episode_c_memory_enabled_replay"
    )
    assert replay_row["computed_verdict"] == "quarantine"
    assert "memory_enabled_without_evidence" in replay_row["reason_codes"]


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
    assert result["semantic_recompute"]["status"] == "pass"
    assert result["semantic_recompute"]["checked_conflict_count"] == 2
    assert result["semantic_recompute"]["rejected_conflict_count"] == 0
    assert result["source_evidence_posture"]["real_source_floor"] == (
        "copied_non_secret_macro_agent_memory_body_with_provenance"
    )
    assert all(row["sanitized_real_episode"] is True for row in result["memory_rows"])
    assert all(row["source_artifact_ref"] for row in result["memory_rows"])
    assert all(row["source_event_ref"] for row in result["memory_rows"])
    assert all(row["source_event_verified"] is True for row in result["memory_rows"])
    assert all(row["event_timestamp"] for row in result["memory_rows"])
    assert all(row["memory_priority"] is not None for row in result["memory_rows"])
    assert all(row["source_trust_score"] is not None for row in result["memory_rows"])
    assert result["authority_ceiling"]["live_memory_product_claim_authorized"] is False


def test_agent_memory_exported_bundle_rejects_semantic_timestamp_perturbation(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = _json(episodes_path)
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    update_event["event_timestamp"] = "2026-05-20T00:00:00Z"
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SEMANTIC_TIMESTAMP_INCOHERENT" in result["error_codes"]
    assert result["conflict_edge_count"] == 1
    assert result["stale_downgrade_count"] == 1
    assert result["semantic_recompute"]["status"] == "blocked"
    assert result["semantic_recompute"]["rejected_conflict_count"] == 1
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "semantic_timestamp_not_after_prior" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_semantic_priority_regression(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = _json(episodes_path)
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    update_event["memory_priority"] = 10
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SEMANTIC_PRIORITY_REGRESSION" in result["error_codes"]
    assert result["conflict_edge_count"] == 1
    assert result["stale_downgrade_count"] == 1
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "semantic_priority_regression" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_semantic_source_trust_regression(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = _json(episodes_path)
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    update_event["source_trust_score"] = 0.7
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SEMANTIC_SOURCE_TRUST_REGRESSION" in result["error_codes"]
    assert result["conflict_edge_count"] == 1
    assert result["stale_downgrade_count"] == 1
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "semantic_source_trust_regression" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_shape_only_memory_events(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    event = next(
        row
        for row in payload["memory_events"]
        if row["event_id"] == "episode_a_preference_add"
    )
    del event["sanitized_real_episode"]
    del event["source_artifact_ref"]
    del event["source_event_ref"]
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["event_count"] == 5
    assert result["decision_counts"] == {
        "ADD": 2,
        "DELETE": 1,
        "NOOP": 1,
        "UPDATE": 1,
    }
    assert result["conflict_edge_count"] == 1
    assert result["semantic_recompute"]["status"] == "blocked"
    assert (
        "MEMORY_CONFLICT_REAL_TRACE_SOURCE_EVIDENCE_MISSING"
        in result["error_codes"]
    )
    assert "MEMORY_CONFLICT_SEMANTIC_PRIOR_EVENT_MISSING" in result["error_codes"]
    memory_row = next(
        row for row in result["memory_rows"] if row["event_id"] == event["event_id"]
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "real_trace_source_evidence_missing" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_temporal_order_perturbation(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["decision"] == "UPDATE"
    )
    update_event["episode_order"] = 1
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_EPISODE_ORDER_INCOHERENT" in result["error_codes"]
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["decision"] == "UPDATE"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "temporal_conflict_not_after_prior_episode" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_unverified_conflict_evidence(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["decision"] == "UPDATE"
    )
    update_event["conflict_edge_ref"] = update_event["evidence_handle_ref"]
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_EDGE_REF_UNVERIFIED" in result["error_codes"]
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["decision"] == "UPDATE"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "temporal_conflict_edge_unverified" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_source_event_drift(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["decision"] == "UPDATE"
    )
    update_event["source_event_ref"] = (
        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::lines_337"
    )
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SOURCE_EVENT_REF_UNVERIFIED" in result["error_codes"]
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["decision"] == "UPDATE"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert memory_row["source_event_verified"] is False
    assert "source_event_ref_unverified" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_stale_override_without_downgrade(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["decision"] == "UPDATE"
    )
    update_event["stale_preference_override"] = True
    del update_event["stale_downgrade_ref"]
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_STALE_OVERRIDE_FORBIDDEN" in result["error_codes"]
    assert "MEMORY_CONFLICT_STALE_OVERRIDE_DOWNGRADE_MISSING" in result["error_codes"]
    assert result["stale_downgrade_count"] == 1
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["decision"] == "UPDATE"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "stale_override_without_downgrade_receipt" in memory_row["reason_codes"]


def test_agent_memory_exported_bundle_rejects_real_downgrade_receipt_field_swap(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = _json(episodes_path)
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    update_event["stale_downgrade_ref"] = update_event["conflict_edge_ref"]
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_STALE_DOWNGRADE_RECEIPT_MISSING" in result["error_codes"]
    assert result["conflict_edge_count"] == 1
    assert result["stale_downgrade_count"] == 1
    assert result["real_runtime_receipt"] is False
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["event_id"] == "episode_b_preference_scope_update"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "stale_downgrade_receipt_missing" in memory_row["reason_codes"]
    assert memory_row["sanitized_real_episode"] is True
    assert memory_row["source_event_verified"] is True


def test_agent_memory_exported_bundle_rejects_positive_row_missing_evidence_handle(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    replay_path = bundle / "replay_observations.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    replay_payload = json.loads(replay_path.read_text(encoding="utf-8"))
    update_event = next(
        row
        for row in payload["memory_events"]
        if row["decision"] == "UPDATE"
    )
    missing_ref = update_event["evidence_handle_ref"]
    del update_event["evidence_handle_ref"]
    enabled_replay = next(
        row
        for row in replay_payload["replay_observations"]
        if row["memory_enabled"] is True
    )
    enabled_replay["evidence_used_refs"] = [
        ref for ref in enabled_replay["evidence_used_refs"] if ref != missing_ref
    ]
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    replay_path.write_text(
        json.dumps(replay_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_EVIDENCE_HANDLE_MISSING" in result["error_codes"]
    assert result["conflict_edge_count"] == 1
    assert result["stale_downgrade_count"] == 1
    memory_row = next(
        row
        for row in result["memory_rows"]
        if row["decision"] == "UPDATE"
    )
    assert memory_row["computed_verdict"] == "quarantine"
    assert "evidence_handle_missing" in memory_row["reason_codes"]
    assert memory_row["trace_backed"] is False


def test_agent_memory_exported_bundle_verdict_not_fixture_label_echo(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    replay_path = bundle / "replay_observations.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    replay_payload = json.loads(replay_path.read_text(encoding="utf-8"))
    episode_ids = {
        row["episode_id"]
        for row in payload["memory_events"]
    }
    episode_map = {
        episode_id: f"renamed_temporal_episode_{index}"
        for index, episode_id in enumerate(sorted(episode_ids), start=1)
    }
    for index, row in enumerate(payload["memory_events"], start=1):
        row["event_id"] = f"renamed_memory_event_{index}"
        row["episode_id"] = episode_map[row["episode_id"]]
    for row in replay_payload["replay_observations"]:
        row["observation_id"] = f"renamed_{row['memory_enabled']}_replay"
        row["episode_id"] = episode_map[row["episode_id"]]
    payload["fixture_id"] = "fixture::renamed_agent_memory_contract"
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    replay_path.write_text(
        json.dumps(replay_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["event_count"] == 5
    assert result["conflict_edge_count"] == 2
    assert result["stale_downgrade_count"] == 2
    assert {
        row["event_id"]
        for row in result["memory_rows"]
    } == {
        f"renamed_memory_event_{index}" for index in range(1, 6)
    }


def test_agent_memory_exported_bundle_rejects_missing_source_posture(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    episodes_path = bundle / "memory_episodes.json"
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    del payload["source_evidence_posture"]
    episodes_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["event_count"] == 5
    assert result["conflict_edge_count"] == 2
    assert result["stale_downgrade_count"] == 2
    assert "MEMORY_CONFLICT_REAL_TRACE_SOURCE_POSTURE_MISSING" in result["error_codes"]


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
    bundle = _copy_bundle(tmp_path)
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


def test_agent_memory_source_module_relation_tamper_blocks_bundle(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_to_target_relation"] = "summarized_copy"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SOURCE_MODULE_RELATION_UNVERIFIED" in result["error_codes"]
    assert result["source_open_body_imports"]["status"] == "blocked"


def test_agent_memory_source_modules_reject_body_text_in_receipt(
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["body_text_in_receipt"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_memory_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_memory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "MEMORY_CONFLICT_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN" in result[
        "error_codes"
    ]
    assert result["source_open_body_imports"]["status"] == "blocked"


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
