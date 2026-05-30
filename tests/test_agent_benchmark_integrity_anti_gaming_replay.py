from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_benchmark_integrity_anti_gaming_trace,
)
import microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay as benchmark_replay
from microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_benchmark_integrity_bundle,
    validate_public_trace,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_benchmark_integrity_anti_gaming_replay/"
    "exported_benchmark_integrity_bundle"
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


def test_agent_benchmark_integrity_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["benchmark_case_count"] == 3
    assert result["known_benchmark_case_ids"] == [
        "repo_issue_public_001",
        "repo_issue_public_002",
        "repo_issue_public_003",
    ]
    assert result["replay_count"] == 3
    assert result["integrity_pass_count"] == 2
    assert result["quarantine_count"] == 1
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["source_modules_pass"] is True
    assert result["source_module_import_count"] == 3
    assert result["source_open_body_imports"]["body_material_count"] == 3
    assert result["source_open_body_imports"]["material_classes"] == [
        "public_macro_pattern_body"
    ]
    assert len(result["public_regression_fixture_refs"]) >= 3
    assert "public_replacement_refs" not in result
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]

    # The organ now COMPUTES the integrity verdict from contamination /
    # file-access / locked-evaluator spans instead of echoing the declared field.
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 3
    assert result["public_trace_integrity_pass_count"] == 2
    assert result["public_trace_quarantine_count"] == 1
    assert result["public_trace_finding_count"] == 0
    assert result["public_trace_status"] == "pass"
    for span in result["public_agent_execution_trace"]["spans"]:
        assert span["integrity_verdict_matches_declared"] is True
        assert (
            span["computed_integrity_verdict"] == span["declared_integrity_verdict"]
        )


def test_agent_benchmark_integrity_public_trace_recomputes_integrity_verdict() -> None:
    trace = build_public_benchmark_integrity_anti_gaming_trace(FIXTURE_INPUT)

    assert trace["status"] == "pass"
    assert trace["span_count"] == 3
    assert (
        trace["source_faithful_refactor"]["verification_mode"]
        == "extension_of_existing_public_refactor"
    )
    assert trace["audit"]["coverage"]["integrity_verdict_recompute_coverage"] is True
    assert trace["audit"]["coverage"]["locked_evaluator_coverage"] is True
    assert trace["audit"]["coverage"]["body_in_receipt"] is False

    by_replay = {span["span_id"].replace("span:", ""): span for span in trace["spans"]}
    assert (
        by_replay["replay_repo_issue_public_001_clean"]["computed_integrity_verdict"]
        == "integrity_pass"
    )
    assert (
        by_replay["replay_repo_issue_public_003_quarantined"][
            "computed_integrity_verdict"
        ]
        == "quarantine"
    )


def test_agent_benchmark_integrity_verdict_mismatch_is_caught(tmp_path: Path) -> None:
    # Flip a declared integrity verdict so it no longer matches the recomputation
    # (the quarantined replay carries a quarantine_reason_ref, so recomputation
    # forces quarantine); assert the new stable error code fires.
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input"
    )
    obs_path = fixture_copy / "replay_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["replay_observations"]:
        if row["replay_id"] == "replay_repo_issue_public_003_quarantined":
            row["integrity_verdict"] = "integrity_pass"
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    trace = build_public_benchmark_integrity_anti_gaming_trace(fixture_copy)
    assert trace["status"] == "blocked"
    trace_codes = {row["error_code"] for row in trace["audit"]["findings"]}
    assert "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH" in trace_codes

    folded = validate_public_trace(trace)
    folded_codes = {row["error_code"] for row in folded["findings"]}
    assert "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH" in folded_codes
    assert folded["status"] == "blocked"

    result = run(
        fixture_copy,
        public_root
        / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )
    assert result["status"] == "blocked"
    assert "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH" in result["error_codes"]
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)


def test_agent_benchmark_integrity_receipts_are_public_relative_and_body_free(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "examples/agent_benchmark_integrity_anti_gaming_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        public_root / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input",
        public_root / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
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
        assert "provider_payload" not in _walk_keys(json.loads(text))
        assert "private_issue_body" not in _walk_keys(json.loads(text))
        assert "body_redacted" not in _walk_keys(json.loads(text))


def test_agent_benchmark_integrity_source_modules_are_digest_verified(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["source_module_manifest_ref"] == (
        "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle/source_module_manifest.json"
    )
    assert result["source_module_import_count"] == 3
    assert result["copied_source_artifact_count"] == 3
    for row in result["source_module_imports"]:
        assert row["sha256"] == row["actual_sha256"]
        assert row["body_in_receipt"] is False
        assert row["material_class"] == "public_macro_pattern_body"
        assert row["source_to_target_relation"] == "source_faithful_json_slice"
        assert row["target_ref"].startswith(
            "examples/agent_benchmark_integrity_anti_gaming_replay/"
            "exported_benchmark_integrity_bundle/source_artifacts/"
        )


def test_agent_benchmark_integrity_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_benchmark_integrity_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_benchmark_integrity_bundle"
    assert result["bundle_id"] == "agent_benchmark_integrity_anti_gaming_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["benchmark_case_count"] == 3
    assert result["known_benchmark_case_ids"] == [
        "repo_issue_public_001",
        "repo_issue_public_002",
        "repo_issue_public_003",
    ]
    assert result["replay_count"] == 3
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["source_modules_pass"] is True
    assert result["source_module_import_count"] == 3
    assert result["source_open_body_imports"]["body_material_count"] == 3


def test_agent_benchmark_integrity_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_benchmark_integrity_anti_gaming_replay"
    )
    args = [
        "run-benchmark-integrity-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 9
    assert first_card["benchmark_integrity"]["benchmark_case_count"] == 3
    assert first_card["benchmark_integrity"]["known_benchmark_case_count"] == 3
    assert first_card["benchmark_integrity"]["replay_count"] == 3
    assert first_card["benchmark_integrity"]["integrity_pass_count"] == 2
    assert first_card["benchmark_integrity"]["quarantine_count"] == 1
    assert first_card["benchmark_integrity"]["source_module_import_count"] == 3
    assert first_card["benchmark_integrity"]["copied_source_artifact_count"] == 3
    assert first_card["benchmark_integrity"]["source_modules_pass"] is True
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert "benchmark_cases" not in _walk_keys(first_card)
    assert "replay_rows" not in _walk_keys(first_card)
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(benchmark_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
