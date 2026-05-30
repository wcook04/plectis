from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_sabotage_scheming_monitor_trace,
)
import microcosm_core.organs.agent_sabotage_scheming_monitor_replay as sabotage_replay
from microcosm_core.organs.agent_sabotage_scheming_monitor_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_sabotage_bundle,
    validate_public_trace,
)
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_sabotage_scheming_monitor_replay/"
    "exported_sabotage_monitor_bundle"
)
FIXTURE_MANIFEST = (
    MICROCOSM_ROOT
    / "core/fixture_manifests/"
    "agent_sabotage_scheming_monitor_replay.fixture_manifest.json"
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


def test_agent_sabotage_scheming_monitor_replay_source_modules_are_digest_verified() -> None:
    source_manifest = json.loads(
        (BUNDLE_INPUT / "source_module_manifest.json").read_text(encoding="utf-8")
    )
    fixture_manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    module = source_manifest["modules"][0]
    target_path = _source_target_path(module["target_ref"])
    copied_body = json.loads(target_path.read_text(encoding="utf-8"))

    assert source_manifest["schema_version"] == "microcosm_source_module_manifest_v1"
    assert source_manifest["organ_id"] == "agent_sabotage_scheming_monitor_replay"
    assert source_manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert source_manifest["body_in_receipt"] is False
    assert source_manifest["module_count"] == 1
    assert "do not authorize" in source_manifest["anti_claim"]
    assert module["module_id"] == "agent_sabotage_scheming_extracted_pattern_ledger_row_body_import"
    assert module["material_class"] == "public_macro_pattern_body"
    assert module["source_to_target_relation"] == "source_faithful_json_slice"
    assert module["body_copied"] is True
    assert module["body_in_receipt"] is False
    assert module["sha256"] == _sha256_ref(target_path)
    assert copied_body["pattern_id"] == "agent_sabotage_scheming_monitor_replay_compound"

    copied_keys = _walk_keys(copied_body)
    for forbidden_key in (
        "credential_value",
        "provider_payload",
        "private_chain_of_thought",
        "raw_harmful_payload",
        "exploit_instructions",
        "real_target_identifier",
        "browser_session",
        "account_cookie",
    ):
        assert forbidden_key not in copied_keys

    body_imports = fixture_manifest["source_open_body_imports"]
    assert body_imports["body_material_count"] == 1
    assert body_imports["body_in_receipt"] is False
    assert body_imports["aggregate_floor_ref"].endswith("source_module_manifest.json")
    assert module["module_id"] in body_imports["body_material_ids"]
    assert body_imports["authority_ceiling"]["release_authorized"] is False


def test_agent_sabotage_scheming_monitor_replay_workingness_exposes_source_body_imports() -> None:
    workingness = RuntimeShell(MICROCOSM_ROOT).workingness_map()
    rows_by_id = {
        row["thing_id"]: row for row in workingness["thing_failure_map"]
    }
    row = rows_by_id["agent_sabotage_scheming_monitor_replay"]
    body_imports = row["source_open_body_imports"]

    assert row["runtime_mode"] == "drilldown_only"
    assert row["workingness_state"] == "demoted_regression_drilldown"
    assert row["observed_workingness"]["counts_as_real_substrate_progress"] is False
    assert body_imports["body_material_count"] == 1
    assert body_imports["body_text_exported_in_workingness"] is False
    assert body_imports["body_text_exported_in_receipts"] is False
    assert (
        "agent_sabotage_scheming_extracted_pattern_ledger_row_body_import"
        in body_imports["body_material_ids"]
    )


def test_agent_sabotage_scheming_monitor_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_sabotage_scheming_monitor_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_sabotage_scheming_monitor_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["episode_count"] == 3
    assert result["action_trace_count"] == 6
    assert result["monitor_score_count"] == 6
    assert result["attack_opportunity_count"] == 4
    assert result["counterfactual_replay_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["live_sabotage_authorized"] is False
    assert result["authority_ceiling"]["private_chain_of_thought_export_authorized"] is False
    assert result["authority_ceiling"]["deployment_risk_claim_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]

    # The organ now COMPUTES caught verdicts from a refactored macro body
    # instead of echoing the declared fixture field.
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 3
    assert result["public_trace_caught_episode_count"] == 2
    assert result["public_trace_missed_episode_count"] == 1
    assert result["public_trace_finding_count"] == 0
    assert result["source_open_body_imports_status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 3
    assert result["body_material_status"] == "public_agent_execution_trace_refactor_landed"
    for span in result["public_agent_execution_trace"]["spans"]:
        assert span["caught_verdict_matches_declared"] is True
        assert span["computed_caught_verdict"] == span["declared_caught_verdict"]


def test_agent_sabotage_scheming_public_trace_recomputes_caught_verdict() -> None:
    trace = build_public_sabotage_scheming_monitor_trace(FIXTURE_INPUT)

    assert trace["status"] == "pass"
    assert trace["span_count"] == 3
    assert (
        trace["source_faithful_refactor"]["verification_mode"]
        == "extension_of_existing_public_refactor"
    )
    assert trace["audit"]["coverage"]["caught_verdict_recompute_coverage"] is True
    assert trace["audit"]["coverage"]["counterfactual_isolation_coverage"] is True
    assert trace["audit"]["coverage"]["body_in_receipt"] is False

    by_episode = {span["episode_id"]: span for span in trace["spans"]}
    # ep_001/ep_002 are caught (a block verdict at high suspicion); ep_003 is
    # not caught (escalate-only, no block) — recomputed, not echoed.
    assert by_episode["scheming_ep_001"]["computed_caught_verdict"] == "caught"
    assert by_episode["scheming_ep_002"]["computed_caught_verdict"] == "caught"
    assert by_episode["scheming_ep_003"]["computed_caught_verdict"] == "not_caught"


def test_agent_sabotage_scheming_caught_verdict_mismatch_is_caught(
    tmp_path: Path,
) -> None:
    # Flip a declared caught verdict so it no longer matches the recomputation,
    # and assert the new stable error code fires while the rest of the contract
    # (negative cases) stays intact.
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay",
        public_root / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay",
    )
    fixture_copy = (
        public_root / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input"
    )
    episodes_path = fixture_copy / "task_episodes.json"
    episodes = json.loads(episodes_path.read_text(encoding="utf-8"))
    for episode in episodes["task_episodes"]:
        if episode["episode_id"] == "scheming_ep_003":
            # Recomputation says not_caught (escalate-only); declare caught.
            episode["caught_verdict"] = "caught"
    episodes_path.write_text(json.dumps(episodes, sort_keys=True), encoding="utf-8")

    trace = build_public_sabotage_scheming_monitor_trace(fixture_copy)
    assert trace["status"] == "blocked"
    trace_codes = {row["error_code"] for row in trace["audit"]["findings"]}
    assert "PUBLIC_TRACE_SCHEMING_CAUGHT_VERDICT_MISMATCH" in trace_codes

    folded = validate_public_trace(trace)
    folded_codes = {row["error_code"] for row in folded["findings"]}
    assert "PUBLIC_TRACE_SCHEMING_CAUGHT_VERDICT_MISMATCH" in folded_codes
    assert folded["status"] == "blocked"

    result = run(
        fixture_copy,
        public_root / "receipts/first_wave/agent_sabotage_scheming_monitor_replay",
        command="pytest",
        acceptance_out=public_root / "acceptance.json",
    )
    assert result["status"] == "blocked"
    assert "PUBLIC_TRACE_SCHEMING_CAUGHT_VERDICT_MISMATCH" in result["error_codes"]
    # Negative-case coverage must not shrink under the mutation.
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)


def test_agent_sabotage_scheming_monitor_receipts_are_public_relative_and_body_free(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay",
        public_root / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input",
        public_root / "receipts/first_wave/agent_sabotage_scheming_monitor_replay",
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
        assert "body_redacted" not in keys
        assert "public_replacement_refs" not in keys
        assert "private_chain_of_thought" not in keys
        assert "raw_harmful_payload" not in keys
        assert "exploit_instructions" not in keys
        assert "credential_value" not in keys
        assert "provider_payload" not in keys
        assert "real_target_identifier" not in keys


def test_agent_sabotage_scheming_monitor_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_sabotage_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sabotage_scheming_monitor_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_sabotage_monitor_bundle"
    assert result["bundle_id"] == "agent_sabotage_scheming_monitor_replay_regression_drilldown"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["episode_count"] == 3
    assert result["monitor_score_count"] == 6
    assert result["counterfactual_replay_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["live_sabotage_authorized"] is False


def test_agent_sabotage_scheming_monitor_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sabotage_scheming_monitor_replay"
    )
    args = [
        "run-sabotage-bundle",
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
    assert first_card["sabotage_monitor"]["episode_count"] == 3
    assert first_card["sabotage_monitor"]["action_trace_count"] == 6
    assert first_card["sabotage_monitor"]["monitor_score_count"] == 6
    assert first_card["sabotage_monitor"]["cold_replay_pass_count"] == 3
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert "task_episodes" not in _walk_keys(first_card)
    assert "action_trace_rows" not in _walk_keys(first_card)
    assert "monitor_score_rows" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(sabotage_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
