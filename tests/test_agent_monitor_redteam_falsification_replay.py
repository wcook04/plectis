from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import agent_monitor_redteam_falsification_replay
from microcosm_core.organs.agent_monitor_redteam_falsification_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_monitor_bundle,
)
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
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


def test_agent_monitor_redteam_falsification_replay_source_modules_are_digest_verified() -> None:
    source_manifest = json.loads(
        (BUNDLE_INPUT / "source_module_manifest.json").read_text(encoding="utf-8")
    )
    fixture_manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    module = source_manifest["modules"][0]
    target_path = _source_target_path(module["target_ref"])
    copied_body = json.loads(target_path.read_text(encoding="utf-8"))

    assert source_manifest["schema_version"] == "microcosm_source_module_manifest_v1"
    assert source_manifest["organ_id"] == "agent_monitor_redteam_falsification_replay"
    assert source_manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert source_manifest["body_in_receipt"] is False
    assert source_manifest["module_count"] == 1
    assert "do not authorize" in source_manifest["anti_claim"]
    assert module["module_id"] == "agent_monitor_redteam_extracted_pattern_ledger_row_body_import"
    assert module["material_class"] == "public_macro_pattern_body"
    assert module["source_to_target_relation"] == "source_faithful_json_slice"
    assert module["body_copied"] is True
    assert module["body_in_receipt"] is False
    assert module["sha256"] == _sha256_ref(target_path)
    assert copied_body["pattern_id"] == "agent_monitor_redteam_falsification_replay_compound"

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

    body_imports = fixture_manifest["source_open_body_imports"]
    assert body_imports["body_material_count"] == 1
    assert body_imports["body_in_receipt"] is False
    assert body_imports["aggregate_floor_ref"].endswith("source_module_manifest.json")
    assert module["module_id"] in body_imports["body_material_ids"]
    assert body_imports["authority_ceiling"]["release_authorized"] is False


def test_agent_monitor_redteam_falsification_replay_workingness_exposes_source_body_imports() -> None:
    workingness = RuntimeShell(MICROCOSM_ROOT).workingness_map()
    rows_by_id = {
        row["thing_id"]: row for row in workingness["thing_failure_map"]
    }
    row = rows_by_id["agent_monitor_redteam_falsification_replay"]
    body_imports = row["source_open_body_imports"]

    assert row["runtime_mode"] == "drilldown_only"
    assert row["workingness_state"] == "demoted_regression_drilldown"
    assert row["observed_workingness"]["counts_as_real_substrate_progress"] is False
    assert body_imports["body_material_count"] == 1
    assert body_imports["body_text_exported_in_workingness"] is False
    assert body_imports["body_text_exported_in_receipts"] is False
    assert (
        "agent_monitor_redteam_extracted_pattern_ledger_row_body_import"
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
    assert result["trajectory_case_count"] == 3
    assert result["observation_count"] == 3
    assert result["adversarial_probe_count"] == 5
    assert result["pass_count"] == 1
    assert result["escalate_count"] == 1
    assert result["block_count"] == 1
    assert result["high_severity_count"] == 2
    assert result["authority_ceiling"]["monitor_product_performance_claim_authorized"] is False
    assert result["authority_ceiling"]["live_agent_traffic_import_authorized"] is False
    assert result["authority_ceiling"]["exploit_instruction_export_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_agent_monitor_redteam_receipts_are_public_relative_and_body_free(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
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
    assert result["trajectory_case_count"] == 3
    assert result["observation_count"] == 3
    assert "public_regression_fixture_refs" in result
    assert ("public_" + "replace" + "ment_refs") not in result
    assert result["private_state_scan"]["body_in_receipt"] is False
    assert result["authority_ceiling"]["monitor_product_performance_claim_authorized"] is False


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
    assert first_card["command_speed"]["freshness_input_count"] == 6
    assert first_card["monitor_redteam"]["trajectory_case_count"] == 3
    assert first_card["monitor_redteam"]["observation_count"] == 3
    assert first_card["monitor_redteam"]["adversarial_probe_count"] == 5
    assert first_card["monitor_redteam"]["pass_count"] == 1
    assert first_card["monitor_redteam"]["escalate_count"] == 1
    assert first_card["monitor_redteam"]["block_count"] == 1
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert "trajectory_cases" not in _walk_keys(first_card)
    assert "monitor_rows" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)
    assert "findings" not in _walk_keys(first_card)

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
