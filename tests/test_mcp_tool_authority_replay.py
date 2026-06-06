from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_mcp_tool_authority_trace,
)
import microcosm_core.organs.mcp_tool_authority_replay as mcp_tool_authority_replay
from microcosm_core.organs.mcp_tool_authority_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SOURCE_MODULE_IMPORT_STATUS,
    main,
    run,
    run_tool_authority_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
)


def _committed_source_bytes(repo_root: Path, source_ref: str) -> bytes:
    """Read the committed macro source so sibling worktree dirt cannot redefine provenance."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"HEAD:{source_ref}"],
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        return result.stdout
    return (repo_root / source_ref).read_bytes()


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


def _copy_fixture_input(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = public_root / "fixtures/first_wave/mcp_tool_authority_replay/input"
    shutil.copytree(FIXTURE_INPUT, input_dir)
    return input_dir


def _copy_bundle_input(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "src/microcosm_core/organs",
        public_root / "src/microcosm_core/organs",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mcp_tool_authority_replay",
        public_root / "examples/mcp_tool_authority_replay",
    )
    return (
        public_root
        / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
    )


def _rewrite_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_mcp_tool_authority_source_module_digests_stream_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    source_root = public_root.parent
    input_dir = (
        public_root
        / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
    )
    target = input_dir / "source_modules/tools/meta/example_tool.py"
    target.parent.mkdir(parents=True)
    body = b"def enforce_tool_authority():\n    return 'public'\n"
    target.write_bytes(body)
    source_path = source_root / "tools/meta/example_tool.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(body)
    expected_digest = "sha256:" + hashlib.sha256(body).hexdigest()
    manifest = {
        "source_import_class": mcp_tool_authority_replay.SOURCE_IMPORT_CLASS,
        "module_count": 1,
        "body_in_receipt": False,
        "modules": [
            {
                "module_id": "example_tool_authority",
                "source_ref": "tools/meta/example_tool.py",
                "target_ref": "source_modules/tools/meta/example_tool.py",
                "source_import_class": mcp_tool_authority_replay.SOURCE_IMPORT_CLASS,
                "material_class": sorted(
                    mcp_tool_authority_replay.PUBLIC_SAFE_SOURCE_BODY_CLASSES
                )[0],
                "body_copied": True,
                "body_in_receipt": False,
                "body_text_in_receipt": False,
                "sha256": expected_digest,
                "source_sha256": expected_digest,
                "target_sha256": expected_digest,
                "required_anchors": ["enforce_tool_authority"],
            }
        ],
    }
    (input_dir / "source_module_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    guarded_paths = {target}
    original_read_bytes = Path.read_bytes

    def fail_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self in guarded_paths:
            raise AssertionError("MCP source-module digests should stream bytes")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    module_result = mcp_tool_authority_replay._source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=True,
    )
    freshness = mcp_tool_authority_replay._freshness_basis(
        input_dir,
        include_negative=False,
    )

    assert mcp_tool_authority_replay._sha256(target) == expected_digest
    assert module_result["status"] == "pass"
    assert module_result["verified_module_count"] == 1
    assert module_result["source_module_import_status"] == SOURCE_MODULE_IMPORT_STATUS
    target_ref = mcp_tool_authority_replay.public_relative_path(
        target,
        display_root=public_root,
    )
    freshness_rows = {
        row["path"]: row
        for row in freshness["inputs"]
        if isinstance(row, dict) and "path" in row
    }
    assert freshness_rows[target_ref]["sha256"] == expected_digest


def test_mcp_tool_authority_replay_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/mcp_tool_authority_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "mcp_tool_authority_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["tool_count"] == 3
    assert result["tool_classes"] == [
        "readonly_lookup",
        "untrusted_result",
        "write_side_effect",
    ]
    assert result["realness_rank"] == 3
    assert result["realness_rung"] == "R3"
    assert result["realness_state"] == "fixture_runtime_authority_replay"
    assert (
        result["realness_evidence"]["evidence_source"]
        == "runtime_recomputed_public_provider_tool_rows"
    )
    assert (
        result["realness_evidence"]["verdict_rederived_from_runtime_evidence"]
        is True
    )
    assert result["realness_evidence"]["expected_labels_used_for_verdict"] is False
    assert result["realness_evidence"]["baked_transcript_ids_used_for_verdict"] is False
    assert result["realness_evidence"]["counts"]["cross_reference_blocker_count"] == 0
    assert result["call_count"] == 3
    assert result["write_side_effect_count"] == 1
    assert result["approved_side_effect_count"] == 1
    assert result["untrusted_result_count"] == 1
    assert result["output_instruction_ignored_count"] == 1
    assert result["rollback_receipt_count"] == 1
    assert result["cold_replay_pass_count"] == 3
    assert (
        result["authority_ceiling"]["live_mcp_account_access_authorized"] is False
    )
    assert result["authority_ceiling"]["credential_export_authorized"] is False
    assert (
        result["authority_ceiling"][
            "untrusted_tool_output_instruction_authorized"
        ]
        is False
    )
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_mcp_tool_authority_rejects_call_with_undeclared_tool_id() -> None:
    manifest_payload = json.loads((FIXTURE_INPUT / "tool_manifest.json").read_text())
    calls_payload = json.loads((FIXTURE_INPUT / "tool_calls.json").read_text())
    declared_tool_ids = {
        str(row["tool_id"])
        for row in manifest_payload["tools"]
        if str(row.get("tool_id") or "")
    }
    tampered_rows = [dict(row) for row in calls_payload["tool_calls"]]
    tampered_rows[0]["tool_id"] = "tool_not_declared_in_manifest"
    tampered_payload = {**calls_payload, "tool_calls": tampered_rows}

    result = mcp_tool_authority_replay.validate_tool_calls(
        tampered_payload,
        {},
        declared_tool_ids=declared_tool_ids,
    )

    tampered_call = next(
        row for row in result["call_rows"] if row["tool_id"] == "tool_not_declared_in_manifest"
    )
    assert result["status"] == "blocked"
    assert result["declared_tool_id_count"] == 3
    assert "undeclared_tool_id" in tampered_call["reason_codes"]
    assert "MCP_TOOL_UNDECLARED_TOOL_ID" in {
        finding["error_code"] for finding in result["findings"]
    }


def test_mcp_tool_authority_rejects_result_for_undeclared_runtime_call_id(
    tmp_path: Path,
) -> None:
    good = run(FIXTURE_INPUT, tmp_path / "good", command="pytest")
    input_dir = _copy_fixture_input(tmp_path)
    result_payload = json.loads((input_dir / "tool_results.json").read_text())
    result_payload["tool_results"][2]["call_id"] = "call_not_in_public_call_ledger"
    _rewrite_json(input_dir / "tool_results.json", result_payload)

    mutated = run(input_dir, tmp_path / "mutated", command="pytest")

    assert good["status"] == "pass"
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["realness_rung"] == "blocked"
    assert "MCP_TOOL_RESULT_UNDECLARED_CALL_ID" in mutated["error_codes"]
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"]
        >= 1
    )
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_rejects_approved_side_effect_missing_rollback_evidence(
    tmp_path: Path,
) -> None:
    good = run(FIXTURE_INPUT, tmp_path / "good", command="pytest")
    input_dir = _copy_fixture_input(tmp_path)
    side_effect_payload = json.loads((input_dir / "side_effect_ledger.json").read_text())
    approved_write = side_effect_payload["side_effects"][0]
    assert approved_write["side_effect_id"] == "side_effect_ticket_update_001"
    approved_write.pop("rollback_receipt_ref")
    _rewrite_json(input_dir / "side_effect_ledger.json", side_effect_payload)

    mutated = run(input_dir, tmp_path / "mutated", command="pytest")

    assert good["status"] == "pass"
    assert good["approved_side_effect_count"] == 1
    assert good["rollback_receipt_count"] == 1
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["realness_rung"] == "blocked"
    assert mutated["approved_side_effect_count"] == 0
    assert mutated["rollback_receipt_count"] == 0
    assert (
        mutated["realness_evidence"]["counts"]["approved_side_effect_count"]
        == 0
    )
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"]
        >= 2
    )
    assert "MCP_TOOL_MISSING_ROLLBACK_RECEIPT" in mutated["error_codes"]
    assert "MCP_TOOL_COLD_REPLAY_EVIDENCE_INCOMPLETE" in mutated["error_codes"]
    side_effect = next(
        row
        for row in mutated["side_effect_rows"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )
    assert side_effect["computed_verdict"] == "blocked"
    assert side_effect["reason_codes"] == [
        "missing_rollback_receipt",
        "rollback_receipt_ref_mismatch",
    ]
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_rejects_approved_write_side_effect_without_authority_refs(
    tmp_path: Path,
) -> None:
    good = run(FIXTURE_INPUT, tmp_path / "good", command="pytest")
    input_dir = _copy_fixture_input(tmp_path)
    side_effect_payload = json.loads((input_dir / "side_effect_ledger.json").read_text())
    approved_write = side_effect_payload["side_effects"][0]
    assert approved_write["side_effect_id"] == "side_effect_ticket_update_001"
    assert approved_write["side_effect_class"] == "write"
    approved_write["approval_token_ref"] = "missing"
    approved_write["ledger_diff_ref"] = ""
    _rewrite_json(input_dir / "side_effect_ledger.json", side_effect_payload)

    mutated = run(input_dir, tmp_path / "mutated", command="pytest")

    assert good["status"] == "pass"
    assert good["approved_side_effect_count"] == 1
    assert good["write_side_effect_count"] == 1
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["realness_rung"] == "blocked"
    assert mutated["approved_side_effect_count"] == 0
    assert mutated["write_side_effect_count"] == 1
    assert (
        mutated["realness_evidence"]["counts"]["approved_side_effect_count"]
        == 0
    )
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"]
        >= 1
    )
    assert "MCP_TOOL_UNAPPROVED_SIDE_EFFECT" in mutated["error_codes"]
    assert "MCP_TOOL_MISSING_ROLLBACK_RECEIPT" in mutated["error_codes"]
    side_effect = next(
        row
        for row in mutated["side_effect_rows"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )
    assert side_effect["computed_verdict"] == "blocked"
    assert set(side_effect["reason_codes"]) >= {"unapproved_side_effect"}
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_rejects_cold_replay_with_baked_pass_label_only(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    cold_replay_payload = json.loads((input_dir / "cold_replay.json").read_text())
    cold_replay_payload["cold_replays"][0]["status"] = "pass"
    cold_replay_payload["cold_replays"][0]["evidence_refs"] = [
        "expected_label:pass"
    ]
    _rewrite_json(input_dir / "cold_replay.json", cold_replay_payload)

    result = run(input_dir, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert result["cold_replay_pass_count"] == 2
    assert "MCP_TOOL_COLD_REPLAY_EVIDENCE_INCOMPLETE" in result["error_codes"]
    replay = next(
        row
        for row in result["cold_replay_rows"]
        if row["replay_id"] == "cold_replay_docs_lookup_001"
    )
    assert replay["computed_verdict"] == "blocked"
    assert set(replay["reason_codes"]) == {
        "missing_runtime_evidence_ref",
        "missing_tool_manifest_evidence_ref",
        "runtime_ref_mismatch",
        "tool_manifest_ref_mismatch",
    }


def test_mcp_tool_authority_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/mcp_tool_authority_replay",
        public_root / "fixtures/first_wave/mcp_tool_authority_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/mcp_tool_authority_replay/input",
        public_root / "receipts/first_wave/mcp_tool_authority_replay",
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
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "token_value" not in keys
        assert "provider_payload" not in keys
        assert "raw_tool_payload" not in keys
        assert "raw_tool_result" not in keys
        assert "private_account_id" not in keys
        assert "private_state_scan" not in keys
        assert "body_redacted" not in keys


def test_mcp_tool_authority_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_tool_authority_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_mcp_tool_authority_bundle"
    assert result["bundle_id"] == "mcp_tool_authority_public_trace_refactor"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["tool_count"] == 3
    assert result["call_count"] == 3
    assert result["approved_side_effect_count"] == 1
    assert result["output_instruction_ignored_count"] == 1
    assert result["cold_replay_pass_count"] == 3
    assert result["body_import_status"] == SOURCE_MODULE_IMPORT_STATUS
    assert result["body_import_classification"] == (
        "copied_non_secret_public_mcp_tool_authority_macro_body_import"
    )
    assert result["product_path_role"] == (
        "copied_non_secret_macro_body_plus_public_agent_execution_trace_refactor"
    )
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] >= 6
    assert result["body_material_status"] == SOURCE_MODULE_IMPORT_STATUS
    assert result["body_copied_material_count"] >= 6
    assert result["realness_rank"] == 4
    assert result["realness_rung"] == "R4"
    assert (
        result["realness_state"]
        == "source_body_backed_runtime_authority_replay"
    )
    assert result["realness_evidence"]["source_body_backed"] is True
    verification = result["body_import_verification"]
    assert verification["verification_status"] == "verified"
    assert verification["verification_mode"] == (
        "extension_of_existing_public_refactor_with_live_digest_relation"
    )
    assert verification["classification"] == "extension_of_existing_public_refactor"
    assert verification["body_import_classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert verification["source_to_target_relation"] == (
        "source_faithful_public_refactor"
    )
    assert verification["digest_relation"] == "source_target_refactor_digests_recorded"
    assert verification["source_ref"] == "system/lib/agent_execution_trace.py"
    assert verification["target_file_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
    assert verification["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/"
        "agent_execution_trace.py::build_public_mcp_tool_authority_trace"
    )
    assert verification["source_body_digest"] == (
        "sha256:"
        + hashlib.sha256(
            (SOURCE_ROOT / "system/lib/agent_execution_trace.py").read_bytes()
        ).hexdigest()
    )
    assert verification["target_body_digest"] == (
        "sha256:"
        + hashlib.sha256(
            (
                MICROCOSM_ROOT
                / "src/microcosm_core/macro_tools/agent_execution_trace.py"
            ).read_bytes()
        ).hexdigest()
    )
    assert verification["source_module_digest_relation"] == (
        "manifest_target_digests_verified"
    )
    assert verification["source_module_digest_count"] >= 6
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 3
    assert (
        result["public_agent_execution_trace"]["audit"]["coverage"][
            "untrusted_output_data_boundary_coverage"
        ]
        is True
    )
    assert "public_replacement_refs" not in result
    assert "private_state_scan" not in result
    assert (
        result["authority_ceiling"]["live_mcp_account_access_authorized"] is False
    )


def test_mcp_tool_authority_exported_bundle_r4_good_binds_declared_tool_side_effect_and_cold_replay_evidence(
    tmp_path: Path,
) -> None:
    result = run_tool_authority_bundle(BUNDLE_INPUT, tmp_path / "good", command="pytest")

    write_call = next(
        row for row in result["call_rows"] if row["call_id"] == "call_ticket_update_001"
    )
    write_side_effect = next(
        row
        for row in result["side_effect_rows"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )
    write_replay = next(
        row
        for row in result["cold_replay_rows"]
        if row["replay_id"] == "cold_replay_ticket_update_001"
    )

    assert result["status"] == "pass"
    assert result["realness_rank"] == 4
    assert result["realness_rung"] == "R4"
    assert result["realness_evidence"]["source_body_backed"] is True
    assert result["realness_evidence"]["counts"]["cross_reference_blocker_count"] == 0
    assert write_call["computed_verdict"] == "accepted_tool_call_metadata"
    assert write_call["reason_codes"] == []
    assert write_side_effect["computed_verdict"] == "accepted_side_effect_metadata"
    assert write_side_effect["reason_codes"] == []
    assert write_replay["computed_verdict"] == "accepted_cold_replay_metadata"
    assert write_replay["reason_codes"] == []


def test_mcp_tool_authority_exported_bundle_rejects_write_call_with_undeclared_tool_id(
    tmp_path: Path,
) -> None:
    good = run_tool_authority_bundle(BUNDLE_INPUT, tmp_path / "good", command="pytest")
    bundle = _copy_bundle_input(tmp_path)
    calls_path = bundle / "tool_calls.json"
    calls = json.loads(calls_path.read_text(encoding="utf-8"))
    write_call = next(
        row for row in calls["tool_calls"] if row["call_id"] == "call_ticket_update_001"
    )
    write_call["tool_id"] = "tool_not_declared_in_manifest"
    _rewrite_json(calls_path, calls)

    mutated = run_tool_authority_bundle(
        bundle,
        bundle.parents[3]
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    call_row = next(
        row
        for row in mutated["call_rows"]
        if row["call_id"] == "call_ticket_update_001"
    )
    side_effect = next(
        row
        for row in mutated["side_effect_rows"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )

    assert good["status"] == "pass"
    assert good["realness_rank"] == 4
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["realness_rung"] == "blocked"
    assert "MCP_TOOL_UNDECLARED_TOOL_ID" in mutated["error_codes"]
    assert "MCP_TOOL_SIDE_EFFECT_UNDECLARED_CALL_ID" in mutated["error_codes"]
    assert call_row["computed_verdict"] == "blocked"
    assert call_row["reason_codes"] == ["undeclared_tool_id"]
    assert side_effect["computed_verdict"] == "blocked"
    assert side_effect["reason_codes"] == ["undeclared_call_id"]
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"] >= 2
    )
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_exported_bundle_rejects_side_effect_receipt_ref_mismatch(
    tmp_path: Path,
) -> None:
    good = run_tool_authority_bundle(BUNDLE_INPUT, tmp_path / "good", command="pytest")
    bundle = _copy_bundle_input(tmp_path)
    side_effect_path = bundle / "side_effect_ledger.json"
    side_effects = json.loads(side_effect_path.read_text(encoding="utf-8"))
    side_effects["side_effects"][0]["approval_token_ref"] = (
        "approval/wrong_ticket_update_001"
    )
    _rewrite_json(side_effect_path, side_effects)

    mutated = run_tool_authority_bundle(
        bundle,
        bundle.parents[3]
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    side_effect = next(
        row
        for row in mutated["side_effect_rows"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )

    assert good["status"] == "pass"
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["approved_side_effect_count"] == 0
    assert "MCP_TOOL_SIDE_EFFECT_RECEIPT_REF_MISMATCH" in mutated["error_codes"]
    assert side_effect["computed_verdict"] == "blocked"
    assert side_effect["reason_codes"] == ["approval_token_ref_mismatch"]
    assert "MCP_TOOL_COLD_REPLAY_EVIDENCE_INCOMPLETE" in mutated["error_codes"]
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"]
        >= 2
    )
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_exported_bundle_rejects_write_side_effect_missing_approval_ref(
    tmp_path: Path,
) -> None:
    good = run_tool_authority_bundle(BUNDLE_INPUT, tmp_path / "good", command="pytest")
    bundle = _copy_bundle_input(tmp_path)
    side_effect_path = bundle / "side_effect_ledger.json"
    side_effects = json.loads(side_effect_path.read_text(encoding="utf-8"))
    write_side_effect = next(
        row
        for row in side_effects["side_effects"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )
    write_side_effect.pop("approval_token_ref")
    _rewrite_json(side_effect_path, side_effects)

    mutated = run_tool_authority_bundle(
        bundle,
        bundle.parents[3]
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    side_effect = next(
        row
        for row in mutated["side_effect_rows"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )

    assert good["status"] == "pass"
    assert good["realness_rank"] == 4
    assert good["realness_rung"] == "R4"
    assert good["approved_side_effect_count"] == 1
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["realness_rung"] == "blocked"
    assert mutated["approved_side_effect_count"] == 0
    assert (
        mutated["realness_evidence"]["counts"]["approved_side_effect_count"]
        == 0
    )
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"]
        >= 2
    )
    assert "MCP_TOOL_UNAPPROVED_SIDE_EFFECT" in mutated["error_codes"]
    assert "MCP_TOOL_SIDE_EFFECT_RECEIPT_REF_MISMATCH" in mutated["error_codes"]
    assert side_effect["computed_verdict"] == "blocked"
    assert side_effect["reason_codes"] == [
        "approval_token_ref_mismatch",
        "unapproved_side_effect",
    ]
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_exported_bundle_rejects_write_cold_replay_missing_side_effect_authority_ref(
    tmp_path: Path,
) -> None:
    good = run_tool_authority_bundle(BUNDLE_INPUT, tmp_path / "good", command="pytest")
    bundle = _copy_bundle_input(tmp_path)
    replay_path = bundle / "cold_replay.json"
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    write_replay = next(
        row
        for row in replay["cold_replays"]
        if row["replay_id"] == "cold_replay_ticket_update_001"
    )
    write_replay["evidence_refs"] = [
        "tool_manifest:tool_ticket_update",
        "tool_calls:call_ticket_update_001",
    ]
    _rewrite_json(replay_path, replay)

    mutated = run_tool_authority_bundle(
        bundle,
        bundle.parents[3]
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    replay_row = next(
        row
        for row in mutated["cold_replay_rows"]
        if row["replay_id"] == "cold_replay_ticket_update_001"
    )

    assert good["status"] == "pass"
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["cold_replay_pass_count"] == 2
    assert "MCP_TOOL_COLD_REPLAY_EVIDENCE_INCOMPLETE" in mutated["error_codes"]
    assert "MCP_TOOL_COLD_REPLAY_RECEIPT_REF_MISMATCH" in mutated["error_codes"]
    assert replay_row["computed_verdict"] == "blocked"
    assert replay_row["reason_codes"] == [
        "missing_runtime_evidence_ref",
        "write_replay_bound_to_call_without_side_effect_ref",
    ]
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"]
        == 1
    )
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_exported_bundle_rejects_private_projection_protocol_ref(
    tmp_path: Path,
) -> None:
    good = run_tool_authority_bundle(BUNDLE_INPUT, tmp_path / "good", command="pytest")
    bundle = _copy_bundle_input(tmp_path)
    protocol_path = bundle / "projection_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["target_refs"].append(
        "/Users/operator/src/ai_workflow/private/provider_payload.json"
    )
    _rewrite_json(protocol_path, protocol)

    mutated = run_tool_authority_bundle(
        bundle,
        bundle.parents[3]
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert good["status"] == "pass"
    assert mutated["status"] == "blocked"
    assert "MCP_TOOL_PROJECTION_PROTOCOL_PRIVATE_REF_SHAPE" in mutated["error_codes"]
    finding = next(
        row
        for row in mutated["findings"]
        if row["error_code"] == "MCP_TOOL_PROJECTION_PROTOCOL_PRIVATE_REF_SHAPE"
    )
    assert finding["subject_kind"] == "projection_protocol"
    assert finding["private_ref_shapes"] == [
        "target_refs:/Users/operator/src/ai_workflow/private/provider_payload.json"
    ]


def test_mcp_tool_authority_exported_bundle_rejects_approved_side_effect_missing_rollback_evidence(
    tmp_path: Path,
) -> None:
    good = run_tool_authority_bundle(BUNDLE_INPUT, tmp_path / "good", command="pytest")
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mcp_tool_authority_replay",
        public_root / "examples/mcp_tool_authority_replay",
    )
    bundle = (
        public_root
        / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
    )
    side_effect_path = bundle / "side_effect_ledger.json"
    side_effect_payload = json.loads(side_effect_path.read_text(encoding="utf-8"))
    approved_write = side_effect_payload["side_effects"][0]
    assert approved_write["side_effect_id"] == "side_effect_ticket_update_001"
    approved_write.pop("rollback_receipt_ref")
    side_effect_path.write_text(
        json.dumps(side_effect_payload, sort_keys=True),
        encoding="utf-8",
    )

    mutated = run_tool_authority_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert good["status"] == "pass"
    assert good["realness_rank"] == 4
    assert good["realness_rung"] == "R4"
    assert good["approved_side_effect_count"] == 1
    assert good["rollback_receipt_count"] == 1
    assert mutated["status"] == "blocked"
    assert mutated["realness_rank"] == 0
    assert mutated["realness_rung"] == "blocked"
    assert mutated["approved_side_effect_count"] == 0
    assert mutated["rollback_receipt_count"] == 0
    assert (
        mutated["realness_evidence"]["counts"]["approved_side_effect_count"]
        == 0
    )
    assert (
        mutated["realness_evidence"]["counts"]["cross_reference_blocker_count"]
        >= 2
    )
    assert "MCP_TOOL_MISSING_ROLLBACK_RECEIPT" in mutated["error_codes"]
    assert "MCP_TOOL_COLD_REPLAY_EVIDENCE_INCOMPLETE" in mutated["error_codes"]
    side_effect = next(
        row
        for row in mutated["side_effect_rows"]
        if row["side_effect_id"] == "side_effect_ticket_update_001"
    )
    assert side_effect["computed_verdict"] == "blocked"
    assert side_effect["reason_codes"] == [
        "missing_rollback_receipt",
        "rollback_receipt_ref_mismatch",
    ]
    assert (
        mutated["realness_evidence"]["provider_tool_evidence_digest"]
        != good["realness_evidence"]["provider_tool_evidence_digest"]
    )


def test_mcp_tool_authority_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mcp_tool_authority_replay",
        public_root / "examples/mcp_tool_authority_replay",
    )
    bundle = (
        public_root
        / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_tool_authority_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "MCP_TOOL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_mcp_tool_authority_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mcp_tool_authority_replay",
        public_root / "examples/mcp_tool_authority_replay",
    )
    bundle = (
        public_root
        / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_tool_authority_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "MCP_TOOL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_mcp_tool_authority_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mcp_tool_authority_replay",
        public_root / "examples/mcp_tool_authority_replay",
    )
    bundle = (
        public_root
        / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_tool_authority_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "MCP_TOOL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_mcp_tool_authority_rejects_self_consistent_source_module_body_swap(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mcp_tool_authority_replay",
        public_root / "examples/mcp_tool_authority_replay",
    )
    bundle = (
        public_root
        / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = next(
        module
        for module in manifest["modules"]
        if module["module_id"] == "agent_execution_trace_runtime_body_import"
    )
    target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
    target = (
        bundle / target_ref
        if target_ref.startswith("source_modules/")
        else public_root / target_ref
    )
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# self-consistent body swap\n",
        encoding="utf-8",
    )
    target_digest = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
    row["sha256"] = target_digest
    row["source_sha256"] = target_digest
    row["target_sha256"] = target_digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_tool_authority_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["realness_rank"] == 0
    assert result["realness_rung"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "MCP_TOOL_SOURCE_MODULE_SOURCE_REF_MISMATCH" in result["error_codes"]


def test_mcp_tool_authority_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay"
    )
    args = [
        "run-tool-authority-bundle",
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
    assert first_card["tool_authority"]["tool_count"] == 3
    assert first_card["tool_authority"]["call_count"] == 3
    assert first_card["source_body_floor"]["body_material_count"] >= 6
    assert first_card["source_body_floor"]["body_material_status"] == (
        SOURCE_MODULE_IMPORT_STATUS
    )
    assert "call_rows" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "public_agent_execution_trace" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(mcp_tool_authority_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_mcp_tool_authority_source_modules_are_exact_macro_body_imports() -> None:
    manifest_path = BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] >= 6
    assert manifest["body_in_receipt"] is False

    repo_root = MICROCOSM_ROOT.parent
    for row in manifest["modules"]:
        source = repo_root / row["source_ref"]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref

        assert source.is_file(), row["module_id"]
        assert target.is_file(), row["module_id"]
        source_digest = "sha256:" + hashlib.sha256(
            _committed_source_bytes(repo_root, row["source_ref"])
        ).hexdigest()
        target_digest = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
        assert source_digest == target_digest == row["sha256"]
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        body = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in body


def test_public_agent_execution_trace_refactor_builds_mcp_tool_authority_spans() -> None:
    trace = build_public_mcp_tool_authority_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert trace["span_count"] == 3
    assert trace["source_faithful_refactor"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
    assert trace["audit"]["coverage"]["capability_scope_coverage"] is True
    assert trace["audit"]["coverage"]["write_side_effect_approval_coverage"] is True
    assert trace["audit"]["coverage"]["rollback_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["cold_replay_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["body_in_receipt"] is False
