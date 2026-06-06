from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_monitor_redteam_falsification_trace,
)
from microcosm_core.organs import agent_monitor_redteam_falsification_replay
from microcosm_core.organs.agent_monitor_redteam_falsification_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    _sha256,
    main,
    run,
    run_monitor_bundle,
    validate_public_trace,
)
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_monitor_redteam_falsification_replay/"
    "exported_monitor_redteam_bundle"
)
FIXTURE_MANIFEST = (
    MICROCOSM_ROOT
    / "core/fixture_manifests/"
    "agent_monitor_redteam_falsification_replay.fixture_manifest.json"
)
PUBLIC_DOGFOOD_TRACE_SOURCE = (
    REPO_ROOT
    / "state/meta_missions/type_a_autonomous_seed_loop/receipts/"
    "public_microcosm_product_dogfood_wave004_safety_evals_trace_20260528T0215Z.json"
)
PUBLIC_DOGFOOD_TRACE_SLICE = (
    BUNDLE_INPUT
    / "source_artifacts/macro_state/microcosm_portfolio/extracted_patterns_ledger/"
    "public_microcosm_product_dogfood_wave004_safety_evals_trace_20260528T0215Z."
    "sanitized_command_trace.json"
)
PUBLIC_DOGFOOD_TRACE_REF = (
    "examples/agent_monitor_redteam_falsification_replay/"
    "exported_monitor_redteam_bundle/source_artifacts/macro_state/"
    "microcosm_portfolio/extracted_patterns_ledger/"
    "public_microcosm_product_dogfood_wave004_safety_evals_trace_20260528T0215Z."
    "sanitized_command_trace.json"
)
PUBLIC_PATTERN_BODY_REF = (
    "examples/agent_monitor_redteam_falsification_replay/"
    "exported_monitor_redteam_bundle/source_artifacts/macro_state/"
    "microcosm_portfolio/extracted_patterns_ledger/"
    "agent_monitor_redteam_falsification_replay_compound.json"
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


def _source_target_path(target_ref: str) -> Path:
    prefix = "microcosm-substrate/"
    assert target_ref.startswith(prefix)
    return MICROCOSM_ROOT / target_ref.removeprefix(prefix)


def _sha256_ref(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_agent_monitor_redteam_sha256_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "monitor_observations.json"
    body = b'{"monitor_observations":[]}\n' * 1024
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("digest should stream monitor freshness input")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256(source) == "sha256:" + hashlib.sha256(body).hexdigest()


def test_agent_monitor_redteam_falsification_replay_source_modules_are_digest_verified() -> None:
    source_manifest = json.loads(
        (BUNDLE_INPUT / "source_module_manifest.json").read_text(encoding="utf-8")
    )
    fixture_manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    modules = {row["module_id"]: row for row in source_manifest["modules"]}
    module = modules["agent_monitor_redteam_extracted_pattern_ledger_row_body_import"]
    dogfood_module = modules[
        "agent_monitor_redteam_public_dogfood_safety_evals_trace_slice_import"
    ]
    target_path = _source_target_path(module["target_ref"])
    dogfood_target_path = _source_target_path(dogfood_module["target_ref"])
    copied_body = json.loads(target_path.read_text(encoding="utf-8"))
    dogfood_trace_slice = json.loads(dogfood_target_path.read_text(encoding="utf-8"))

    assert source_manifest["schema_version"] == "microcosm_source_module_manifest_v1"
    assert source_manifest["organ_id"] == "agent_monitor_redteam_falsification_replay"
    assert source_manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert source_manifest["body_in_receipt"] is False
    assert source_manifest["module_count"] == 2
    assert "do not authorize" in source_manifest["anti_claim"]
    assert module["module_id"] == "agent_monitor_redteam_extracted_pattern_ledger_row_body_import"
    assert module["material_class"] == "public_macro_pattern_body"
    assert module["source_to_target_relation"] == "source_faithful_json_slice"
    assert module["body_copied"] is True
    assert module["body_in_receipt"] is False
    assert module["sha256"] == _sha256_ref(target_path)
    assert copied_body["pattern_id"] == "agent_monitor_redteam_falsification_replay_compound"
    assert dogfood_module["material_class"] == "public_dogfood_command_trace_slice"
    assert dogfood_module["source_to_target_relation"] == "source_faithful_sanitized_json_slice"
    assert dogfood_module["body_in_receipt"] is False
    assert dogfood_module["body_text_in_receipt"] is False
    assert dogfood_module["source_trace_sha256"] == _sha256_ref(
        PUBLIC_DOGFOOD_TRACE_SOURCE
    )
    assert dogfood_module["sha256"] == _sha256_ref(dogfood_target_path)
    assert dogfood_trace_slice["source_sha256"] == _sha256_ref(PUBLIC_DOGFOOD_TRACE_SOURCE)
    assert dogfood_trace_slice["public_safe_boundary"]["argv_exported"] is False
    assert (
        dogfood_trace_slice["public_safe_boundary"][
            "raw_stdout_or_stderr_preview_exported"
        ]
        is False
    )
    assert dogfood_trace_slice["monitor_probe_summary"]["real_public_trace_kind"] == (
        "public_cli_dogfood_trace"
    )

    copied_keys = _walk_keys(copied_body)
    for forbidden_key in (
        "credential_value",
        "provider_payload",
        "private_chain_of_thought",
        "raw_transcript",
        "exploit_instructions",
        "browser_session",
        "account_cookie",
    ):
        assert forbidden_key not in copied_keys
        assert forbidden_key not in _walk_keys(dogfood_trace_slice)

    body_imports = fixture_manifest["source_open_body_imports"]
    assert body_imports["body_material_count"] == 2
    assert body_imports["body_in_receipt"] is False
    assert body_imports["aggregate_floor_ref"].endswith("source_module_manifest.json")
    assert module["module_id"] in body_imports["body_material_ids"]
    assert dogfood_module["module_id"] in body_imports["body_material_ids"]
    assert body_imports["authority_ceiling"]["release_authorized"] is False


def test_agent_monitor_redteam_public_dogfood_trace_slice_derives_from_source_receipt() -> None:
    source_trace = json.loads(PUBLIC_DOGFOOD_TRACE_SOURCE.read_text(encoding="utf-8"))
    trace_slice = json.loads(PUBLIC_DOGFOOD_TRACE_SLICE.read_text(encoding="utf-8"))
    selected_command_ids = {"authority_card", "workingness_card", "proof_lab_card"}
    source_selected = [
        {
            "event_id": row["event_id"],
            "command_id": row["command_id"],
            "persona_id": row["persona_id"],
            "evidence_origin": row["evidence_origin"],
            "public_observable": row["public_observable"],
            "exit_code": row["exit_code"],
            "parsed_json_ok": row["parsed_json_ok"],
            "duration_ms": row["duration_ms"],
            "stdout_char_count": row["stdout_char_count"],
            "stderr_char_count": row["stderr_char_count"],
        }
        for row in source_trace["events"]
        if row["command_id"] in selected_command_ids
    ]

    assert trace_slice["schema_version"] == (
        "microcosm_public_dogfood_safety_evals_trace_slice_v1"
    )
    assert trace_slice["source_trace_id"] == source_trace["trace_id"]
    assert trace_slice["source_trace_generated_at"] == source_trace["generated_at"]
    assert trace_slice["public_surface_boundary"] == source_trace[
        "public_surface_boundary"
    ]
    assert trace_slice["event_count"] == len(source_trace["events"])
    assert trace_slice["selected_events"] == source_selected
    assert trace_slice["selected_event_count"] == len(source_selected)
    assert "argv" not in _walk_keys(trace_slice)
    assert "stdout_preview" not in _walk_keys(trace_slice)
    assert "stderr_preview" not in _walk_keys(trace_slice)


def test_agent_monitor_redteam_falsification_replay_workingness_exposes_source_body_imports() -> None:
    workingness = RuntimeShell(MICROCOSM_ROOT).workingness_map()
    rows_by_id = {
        row["thing_id"]: row for row in workingness["thing_failure_map"]
    }
    row = rows_by_id["agent_monitor_redteam_falsification_replay"]
    body_imports = row["source_open_body_imports"]

    assert row["runtime_mode"] == "drilldown_only"
    assert row["workingness_state"] == "demoted_regression_drilldown"
    assert row["observed_workingness"]["evidence_class"] == "bounded_runtime_computation"
    assert row["observed_workingness"]["counts_as_real_substrate_progress"] is True
    assert body_imports["body_material_count"] == 2
    assert body_imports["body_text_exported_in_workingness"] is False
    assert body_imports["body_text_exported_in_receipts"] is False
    assert (
        "agent_monitor_redteam_extracted_pattern_ledger_row_body_import"
        in body_imports["body_material_ids"]
    )
    assert (
        "agent_monitor_redteam_public_dogfood_safety_evals_trace_slice_import"
        in body_imports["body_material_ids"]
    )


def test_agent_monitor_redteam_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_monitor_redteam_falsification_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["trajectory_case_count"] == 4
    assert result["observation_count"] == 4
    assert result["adversarial_probe_count"] == 6
    assert result["pass_count"] == 2
    assert result["escalate_count"] == 1
    assert result["block_count"] == 1
    assert result["high_severity_count"] == 2
    assert result["authority_ceiling"]["monitor_product_performance_claim_authorized"] is False
    assert result["authority_ceiling"]["live_agent_traffic_import_authorized"] is False
    assert result["authority_ceiling"]["exploit_instruction_export_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]

    # The organ now COMPUTES the monitor verdict from probe-span evidence
    # instead of echoing the declared fixture field.
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 4
    assert result["public_trace_coverage_backed_count"] == 4
    assert result["public_trace_verdict_match_count"] == 4
    assert result["public_trace_recomputed_pass_count"] == 2
    assert result["public_trace_recomputed_escalate_count"] == 1
    assert result["public_trace_recomputed_block_count"] == 1
    assert result["public_trace_finding_count"] == 0
    assert result["source_open_body_imports_status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["source_artifact_evidence_ref_count"] == 4
    assert result["source_artifact_evidence_verified_count"] == 4
    assert result["real_public_trace_evidence_ref_count"] == 1
    assert result["real_public_trace_evidence_verified_count"] == 1
    for row in result["monitor_rows"]:
        assert row["source_artifact_evidence_verified"] is True
        assert row["source_artifact_evidence_ref_count"] == 1
        if row["observation_id"] == "obs_real_public_safety_evals_authority_probe_pass":
            assert row["real_public_trace_evidence_verified"] is True
            assert len(row["real_public_trace_evidence_refs"]) == 1
        else:
            assert row["real_public_trace_evidence_verified"] is False
            assert row["real_public_trace_evidence_refs"] == []
    for span in result["public_agent_execution_trace"]["spans"]:
        assert span["coverage_backed_by_probe"] is True
        assert span["monitor_verdict_matches_declared"] is True
        assert span["computed_monitor_verdict"] == span["declared_monitor_verdict"]
    rows_by_id = {row["observation_id"]: row for row in result["monitor_rows"]}
    assert rows_by_id["obs_benign_route_review_pass"]["computed_verdict"] == "pass"
    assert (
        rows_by_id["obs_suppressed_failure_escalate"]["computed_verdict"]
        == "escalate"
    )
    assert rows_by_id["obs_tool_authority_escape_block"]["computed_verdict"] == "block"
    assert (
        rows_by_id["obs_real_public_safety_evals_authority_probe_pass"][
            "computed_verdict"
        ]
        == "pass"
    )


def test_agent_monitor_redteam_public_trace_recomputes_monitor_verdict() -> None:
    trace = build_public_monitor_redteam_falsification_trace(FIXTURE_INPUT)

    assert trace["status"] == "pass"
    assert trace["span_count"] == 4
    assert (
        trace["source_faithful_refactor"]["verification_mode"]
        == "extension_of_existing_public_refactor"
    )
    assert trace["audit"]["coverage"]["coverage_probe_span_coverage"] is True
    assert trace["audit"]["coverage"]["verdict_recompute_coverage"] is True
    assert trace["audit"]["coverage"]["body_in_receipt"] is False

    by_observation = {
        span["span_id"].replace("span:", ""): span for span in trace["spans"]
    }
    assert (
        by_observation["obs_benign_route_review_pass"]["computed_monitor_verdict"]
        == "pass"
    )
    assert (
        by_observation["obs_suppressed_failure_escalate"]["computed_monitor_verdict"]
        == "escalate"
    )
    assert (
        by_observation["obs_tool_authority_escape_block"]["computed_monitor_verdict"]
        == "block"
    )
    assert (
        by_observation[
            "obs_real_public_safety_evals_authority_probe_pass"
        ]["computed_monitor_verdict"]
        == "pass"
    )


def test_agent_monitor_redteam_probe_perturbation_moves_computed_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
    )
    obs_path = fixture_copy / "monitor_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["monitor_observations"]:
        if row["observation_id"] == "obs_benign_route_review_pass":
            assert row["monitor_verdict"] == "pass"
            row["adversarial_probe_ref"] = ""
            row["suspicious_action_span_ref"] = ""
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    trace = build_public_monitor_redteam_falsification_trace(fixture_copy)
    by_observation = {
        span["span_id"].replace("span:", ""): span for span in trace["spans"]
    }
    perturbed = by_observation["obs_benign_route_review_pass"]
    trace_codes = {row["error_code"] for row in trace["audit"]["findings"]}

    assert trace["status"] == "blocked"
    assert perturbed["declared_monitor_verdict"] == "pass"
    assert perturbed["coverage_backed_by_probe"] is False
    assert perturbed["computed_monitor_verdict"] == "escalate"
    assert perturbed["monitor_verdict_matches_declared"] is False
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_COVERAGE_WITHOUT_PROBE_SPAN" in trace_codes
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH" in trace_codes

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )
    result_span = {
        span["span_id"].replace("span:", ""): span
        for span in result["public_agent_execution_trace"]["spans"]
    }["obs_benign_route_review_pass"]

    assert result["status"] == "blocked"
    assert result_span["declared_monitor_verdict"] == "pass"
    assert result_span["computed_monitor_verdict"] == "escalate"
    assert result_span["monitor_verdict_matches_declared"] is False
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH" in result["error_codes"]
    assert result["public_trace_verdict_match_count"] == 3


def test_agent_monitor_redteam_suppressed_failure_facts_move_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
    )
    obs_path = fixture_copy / "monitor_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["monitor_observations"]:
        if row["observation_id"] == "obs_suppressed_failure_escalate":
            assert row["monitor_verdict"] == "escalate"
            row["severity_tier"] = "low"
            row["human_escalation_ref"] = (
                "escalations/not-required-suppressed-failure-control"
            )
            row["mitigation_diff_ref"] = (
                "mitigations/no-change-suppressed-failure-control"
            )
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )
    result_span = {
        span["span_id"].replace("span:", ""): span
        for span in result["public_agent_execution_trace"]["spans"]
    }["obs_suppressed_failure_escalate"]

    assert result["status"] == "blocked"
    assert result_span["declared_monitor_verdict"] == "escalate"
    assert result_span["computed_monitor_verdict"] == "pass"
    assert result_span["monitor_verdict_matches_declared"] is False
    assert result["public_trace_recomputed_pass_count"] == 3
    assert result["public_trace_recomputed_escalate_count"] == 0
    assert result["public_trace_recomputed_block_count"] == 1
    assert result["public_trace_verdict_match_count"] == 3
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH" in result["error_codes"]


def test_agent_monitor_redteam_wrong_trajectory_and_suppressed_failure_mutations_move_verdicts(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
    )
    obs_path = fixture_copy / "monitor_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["monitor_observations"]:
        if row["observation_id"] == "obs_benign_route_review_pass":
            assert row["monitor_verdict"] == "pass"
            row["trajectory_id"] = "traj_monitor_suppressed_failure"
        if row["observation_id"] == "obs_suppressed_failure_escalate":
            assert row["monitor_verdict"] == "escalate"
            row["severity_tier"] = "low"
            row["human_escalation_ref"] = (
                "escalations/not-required-suppressed-failure-control"
            )
            row["mitigation_diff_ref"] = (
                "mitigations/no-change-suppressed-failure-control"
            )
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )
    spans = {
        span["span_id"].replace("span:", ""): span
        for span in result["public_agent_execution_trace"]["spans"]
    }
    rows = {row["observation_id"]: row for row in result["monitor_rows"]}
    wrong_trajectory = spans["obs_benign_route_review_pass"]
    suppressed_failure = spans["obs_suppressed_failure_escalate"]

    assert result["status"] == "blocked"
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH" in result["error_codes"]
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_COVERAGE_WITHOUT_PROBE_SPAN" in result[
        "error_codes"
    ]
    assert wrong_trajectory["declared_monitor_verdict"] == "pass"
    assert wrong_trajectory["coverage_backed_by_probe"] is False
    assert wrong_trajectory["computed_monitor_verdict"] == "escalate"
    assert wrong_trajectory["monitor_verdict_matches_declared"] is False
    assert suppressed_failure["declared_monitor_verdict"] == "escalate"
    assert suppressed_failure["coverage_backed_by_probe"] is True
    assert suppressed_failure["computed_monitor_verdict"] == "pass"
    assert suppressed_failure["monitor_verdict_matches_declared"] is False
    assert rows["obs_benign_route_review_pass"]["computed_verdict"] == "quarantine"
    assert (
        rows["obs_benign_route_review_pass"]["recomputed_monitor_verdict"]
        == "escalate"
    )
    assert (
        rows["obs_suppressed_failure_escalate"]["computed_verdict"] == "quarantine"
    )
    assert (
        rows["obs_suppressed_failure_escalate"]["recomputed_monitor_verdict"]
        == "pass"
    )
    assert result["public_trace_verdict_match_count"] == 2
    assert result["public_trace_recomputed_pass_count"] == 2
    assert result["public_trace_recomputed_escalate_count"] == 1
    assert result["public_trace_recomputed_block_count"] == 1


def test_agent_monitor_redteam_verdict_mismatch_is_caught(tmp_path: Path) -> None:
    # Flip a declared monitor verdict so it no longer matches the span-derived
    # recomputation; assert the new stable error code fires.
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
    )
    obs_path = fixture_copy / "monitor_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["monitor_observations"]:
        if row["observation_id"] == "obs_tool_authority_escape_block":
            # Span evidence (critical + escalation + mitigation) recomputes to
            # block; declare pass to force a mismatch.
            row["monitor_verdict"] = "pass"
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    trace = build_public_monitor_redteam_falsification_trace(fixture_copy)
    assert trace["status"] == "blocked"
    trace_codes = {row["error_code"] for row in trace["audit"]["findings"]}
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH" in trace_codes

    folded = validate_public_trace(trace)
    folded_codes = {row["error_code"] for row in folded["findings"]}
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH" in folded_codes
    assert folded["status"] == "blocked"

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )
    assert result["status"] == "blocked"
    assert "PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH" in result["error_codes"]
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)


def test_agent_monitor_redteam_fixture_requires_real_public_trace_evidence(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
    )
    obs_path = fixture_copy / "monitor_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["monitor_observations"]:
        if row["observation_id"] == "obs_real_public_safety_evals_authority_probe_pass":
            row["source_artifact_evidence_refs"] = [PUBLIC_PATTERN_BODY_REF]
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    monitor_rows = {row["observation_id"]: row for row in result["monitor_rows"]}
    real_row = monitor_rows["obs_real_public_safety_evals_authority_probe_pass"]

    assert result["status"] == "blocked"
    assert result["source_artifact_evidence_verified_count"] == 4
    assert result["real_public_trace_evidence_ref_count"] == 0
    assert result["real_public_trace_evidence_verified_count"] == 0
    assert "MONITOR_REDTEAM_REAL_PUBLIC_TRACE_EVIDENCE_MISSING" in result[
        "error_codes"
    ]
    assert real_row["source_artifact_evidence_verified"] is True
    assert real_row["real_public_trace_evidence_verified"] is False
    assert real_row["computed_verdict"] == "pass"
    assert real_row["recomputed_monitor_verdict"] == "pass"


def test_agent_monitor_redteam_rejects_trace_class_without_public_trace_content(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
    )
    copied_trace_path = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle/source_artifacts/macro_state/"
        "microcosm_portfolio/extracted_patterns_ledger/"
        "public_microcosm_product_dogfood_wave004_safety_evals_trace_20260528T0215Z."
        "sanitized_command_trace.json"
    )
    copied_trace = json.loads(copied_trace_path.read_text(encoding="utf-8"))
    copied_trace["monitor_probe_summary"]["real_public_trace_kind"] = (
        "static_label_only"
    )
    copied_trace_path.write_text(
        json.dumps(copied_trace, sort_keys=True),
        encoding="utf-8",
    )
    manifest_path = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle/source_module_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["modules"]:
        if row["material_class"] == "public_dogfood_command_trace_slice":
            row["sha256"] = _sha256(copied_trace_path)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    trace_modules = [
        row
        for row in result["source_module_manifest"]["observed_modules"]
        if row["material_class"] == "public_dogfood_command_trace_slice"
    ]

    assert result["status"] == "blocked"
    assert result["source_artifact_evidence_verified_count"] == 4
    assert result["real_public_trace_evidence_ref_count"] == 0
    assert result["real_public_trace_evidence_verified_count"] == 0
    assert "MONITOR_REDTEAM_PUBLIC_TRACE_KIND_MISMATCH" in result["error_codes"]
    assert "MONITOR_REDTEAM_REAL_PUBLIC_TRACE_EVIDENCE_MISSING" in result[
        "error_codes"
    ]
    assert trace_modules[0]["digest_status"] == "match"
    assert trace_modules[0]["content_validation_status"] == "blocked"


def test_agent_monitor_redteam_negative_semantics_reject_declared_case_spoof(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    fixture_copy = (
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input"
    )
    negative_path = fixture_copy / "private_chain_of_thought_leakage.json"
    payload = json.loads(negative_path.read_text(encoding="utf-8"))
    payload["expected_negative_case_id"] = "internal_code_export"
    negative_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["missing_negative_cases"] == []
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert "MONITOR_REDTEAM_PRIVATE_COT_FORBIDDEN" in result["error_codes"]
    assert "MONITOR_REDTEAM_NEGATIVE_CASE_SEMANTIC_MISMATCH" in result["error_codes"]
    assert result["negative_case_semantic_failure_count"] == 1
    semantics = {row["case_id"]: row for row in result["negative_case_semantics"]}
    spoofed = semantics["private_chain_of_thought_leakage"]
    assert spoofed["semantic_evaluator_used"] is True
    assert spoofed["verified"] is False
    assert spoofed["declared_case_id_matches_file"] is False


def test_agent_monitor_redteam_rejects_missing_source_artifact_evidence(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    obs_path = bundle / "monitor_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["monitor_observations"]:
        if row["observation_id"] == "obs_benign_route_review_pass":
            row.pop("source_artifact_evidence_refs")
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run_monitor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert "MONITOR_REDTEAM_SOURCE_ARTIFACT_EVIDENCE_MISSING" in result[
        "error_codes"
    ]
    monitor_rows = {row["observation_id"]: row for row in result["monitor_rows"]}
    corrupted = monitor_rows["obs_benign_route_review_pass"]
    assert corrupted["computed_verdict"] == "quarantine"
    assert corrupted["monitor_verdict"] == "pass"
    assert corrupted["source_artifact_evidence_ref_count"] == 0
    assert corrupted["source_artifact_evidence_verified"] is False
    assert "source_artifact_evidence_missing" in corrupted["reason_codes"]


def test_agent_monitor_redteam_requires_real_public_trace_evidence(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    obs_path = bundle / "monitor_observations.json"
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    for row in observations["monitor_observations"]:
        if row["observation_id"] == "obs_real_public_safety_evals_authority_probe_pass":
            row["source_artifact_evidence_refs"] = [PUBLIC_PATTERN_BODY_REF]
    obs_path.write_text(json.dumps(observations, sort_keys=True), encoding="utf-8")

    result = run_monitor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_artifact_evidence_verified_count"] == 4
    assert result["real_public_trace_evidence_verified_count"] == 0
    assert "MONITOR_REDTEAM_REAL_PUBLIC_TRACE_EVIDENCE_MISSING" in result[
        "error_codes"
    ]
    monitor_rows = {row["observation_id"]: row for row in result["monitor_rows"]}
    corrupted = monitor_rows["obs_real_public_safety_evals_authority_probe_pass"]
    assert corrupted["source_artifact_evidence_verified"] is True
    assert corrupted["source_artifact_evidence_ref_count"] == 1
    assert corrupted["real_public_trace_evidence_verified"] is False
    assert corrupted["reason_codes"] == []


def test_agent_monitor_redteam_receipts_are_public_relative_and_body_free(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_monitor_redteam_falsification_replay",
        public_root / "examples/agent_monitor_redteam_falsification_replay",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
        public_root / "fixtures/first_wave/agent_monitor_redteam_falsification_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/agent_monitor_redteam_falsification_replay/input",
        public_root / "receipts/first_wave/agent_monitor_redteam_falsification_replay",
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
        assert "private_chain_of_thought" not in keys
        assert "internal_code_text" not in keys
        assert "credential_value" not in keys
        assert "exploit_instructions" not in keys
        assert "raw_transcript" not in keys
        assert ("body_" + "red" + "acted") not in keys
        assert ("public_" + "replace" + "ment_refs") not in keys
        assert ("privacy_" + "red" + "action_ref") not in keys
        assert "body_in_receipt" in keys


def test_agent_monitor_redteam_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_monitor_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_monitor_redteam_bundle"
    assert result["bundle_id"] == (
        "agent_monitor_redteam_falsification_replay_regression_drilldown"
    )
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["trajectory_case_count"] == 4
    assert result["observation_count"] == 4
    assert "public_regression_fixture_refs" in result
    assert ("public_" + "replace" + "ment_refs") not in result
    assert result["private_state_scan"]["body_in_receipt"] is False
    assert result["authority_ceiling"]["monitor_product_performance_claim_authorized"] is False
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["module_count"] == 2
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["copied_macro_source_count"] == 2
    assert result["source_artifact_evidence_ref_count"] == 4
    assert result["source_artifact_evidence_verified_count"] == 4
    assert result["real_public_trace_evidence_ref_count"] == 1
    assert result["real_public_trace_evidence_verified_count"] == 1
    monitor_rows = {row["observation_id"]: row for row in result["monitor_rows"]}
    real_public_row = monitor_rows[
        "obs_real_public_safety_evals_authority_probe_pass"
    ]
    assert real_public_row["monitor_verdict"] == "pass"
    assert real_public_row["computed_verdict"] == "pass"
    assert real_public_row["recomputed_monitor_verdict"] == "pass"
    assert real_public_row["source_artifact_evidence_verified"] is True
    assert real_public_row["real_public_trace_evidence_verified"] is True


def test_agent_monitor_redteam_exported_bundle_scans_source_artifact_targets(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    copied_trace_path = (
        bundle
        / "source_artifacts/macro_state/microcosm_portfolio/extracted_patterns_ledger/"
        "public_microcosm_product_dogfood_wave004_safety_evals_trace_20260528T0215Z."
        "sanitized_command_trace.json"
    )
    copied_trace = json.loads(copied_trace_path.read_text(encoding="utf-8"))
    copied_trace["scan_sentinel"] = "SYNTHETIC_PROVIDER_PAYLOAD_BODY_SENTINEL"
    copied_trace_path.write_text(
        json.dumps(copied_trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_monitor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["private_state_scan"]["blocking_hit_count"] >= 1
    assert "MONITOR_REDTEAM_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    private_scan_text = json.dumps(result["private_state_scan"], sort_keys=True)
    assert "provider_payload_body_sentinel" in private_scan_text
    assert "forbidden_content_body" in private_scan_text
    assert "SYNTHETIC_PROVIDER_PAYLOAD_BODY_SENTINEL" not in private_scan_text


def test_agent_monitor_redteam_exported_bundle_rejects_source_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_monitor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "MONITOR_REDTEAM_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["private_state_scan"]["status"] == "pass"


def test_agent_monitor_redteam_exported_bundle_rejects_target_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_monitor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay",
        command="pytest",
    )

    observed_module = result["source_module_manifest"]["observed_modules"][0]
    declaration_statuses = {
        row["field"]: row["digest_status"]
        for row in observed_module["digest_declarations"]
    }

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "MONITOR_REDTEAM_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert observed_module["digest_status"] == "mismatch"
    assert declaration_statuses == {"sha256": "match", "target_sha256": "mismatch"}
    assert result["private_state_scan"]["status"] == "pass"


def test_agent_monitor_redteam_exported_bundle_rejects_body_text_in_receipt(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_monitor_redteam_falsification_replay/"
        "exported_monitor_redteam_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["body_text_in_receipt"] = True
    manifest["modules"][0]["body_text_in_receipt"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_monitor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "MONITOR_REDTEAM_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN" in result[
        "error_codes"
    ]
    assert (
        "MONITOR_REDTEAM_SOURCE_MODULE_ROW_BODY_TEXT_IN_RECEIPT_FORBIDDEN"
        in result["error_codes"]
    )
    assert result["private_state_scan"]["status"] == "pass"


def test_agent_monitor_redteam_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_monitor_redteam_falsification_replay"
    )
    args = [
        "run-monitor-bundle",
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
    assert first_card["monitor_redteam"]["trajectory_case_count"] == 4
    assert first_card["monitor_redteam"]["observation_count"] == 4
    assert first_card["monitor_redteam"]["adversarial_probe_count"] == 6
    assert first_card["monitor_redteam"]["pass_count"] == 2
    assert first_card["monitor_redteam"]["escalate_count"] == 1
    assert first_card["monitor_redteam"]["block_count"] == 1
    assert first_card["monitor_redteam"]["source_artifact_evidence_ref_count"] == 4
    assert first_card["monitor_redteam"][
        "source_artifact_evidence_verified_count"
    ] == 4
    assert first_card["monitor_redteam"][
        "real_public_trace_evidence_ref_count"
    ] == 1
    assert first_card["monitor_redteam"][
        "real_public_trace_evidence_verified_count"
    ] == 1
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert first_card["validation"]["source_module_manifest_status"] == "pass"
    assert "trajectory_cases" not in _walk_keys(first_card)
    assert "monitor_rows" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)
    assert "findings" not in _walk_keys(first_card)
    receipt_payload = json.loads(
        (
            out
            / agent_monitor_redteam_falsification_replay.BUNDLE_RESULT_NAME
        ).read_text(encoding="utf-8")
    )
    assert "<repo-root>" in receipt_payload["command"]

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        agent_monitor_redteam_falsification_replay,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
