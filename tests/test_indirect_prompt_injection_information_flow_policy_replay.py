from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_prompt_injection_trace,
)
from microcosm_core.organs import (
    indirect_prompt_injection_information_flow_policy_replay,
)
from microcosm_core.organs.indirect_prompt_injection_information_flow_policy_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_prompt_injection_bundle,
    validate_information_flow_graph,
    validate_source_documents,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/"
    "indirect_prompt_injection_information_flow_policy_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/indirect_prompt_injection_information_flow_policy_replay/"
    "exported_prompt_injection_flow_bundle"
)
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"
FIXTURE_MANIFESTS = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/"
    "indirect_prompt_injection_information_flow_policy_replay/fixture_manifest.json",
    MICROCOSM_ROOT
    / "core/fixture_manifests/"
    "indirect_prompt_injection_information_flow_policy_replay.fixture_manifest.json",
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _digest_value(value: str) -> str:
    return value.removeprefix("sha256:")


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


def test_indirect_prompt_injection_flow_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_document_count"] == 5
    assert result["untrusted_source_count"] == 3
    assert result["trusted_source_count"] == 2
    assert result["information_flow_count"] == 5
    assert result["taint_propagation"]["status"] == "pass"
    assert result["taint_propagation_path_count"] == 5
    assert result["taint_propagation"]["derived_taint_mismatch_count"] == 0
    assert result["derived_policy_verdict_mismatch_count"] == 0
    taint_rows = {
        row["flow_id"]: row
        for row in result["taint_propagation"]["flow_path_rows"]
    }
    assert taint_rows["flow_block_hidden_policy_promotion"][
        "derived_taint_labels"
    ] == ["hidden_policy_claim", "untrusted_tool_output"]
    assert taint_rows["flow_block_web_to_email"]["source_to_sink_paths"] == [
        ["src_web_page_injection", "sink_email_send"]
    ]
    assert {
        row["flow_id"]: row["derived_policy_verdict"]
        for row in result["flow_rows"]
    } == {
        row["flow_id"]: row["policy_verdict"]
        for row in result["flow_rows"]
    }
    assert result["policy_verdict_count"] == 5
    assert result["allow_count"] == 1
    assert result["warn_count"] == 1
    assert result["block_count"] == 2
    assert result["review_count"] == 1
    assert result["blocked_without_external_action_count"] == 2
    assert result["trusted_context_disclosure_count"] == 0
    assert result["untrusted_instruction_obeyed_count"] == 0
    assert result["cold_replay_pass_count"] == 5
    assert result["authority_ceiling"]["tool_output_instruction_authority_authorized"] is False
    assert result["authority_ceiling"]["raw_prompt_body_export_authorized"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert (
        result["body_import_classification"]
        == "extension_of_existing_public_refactor"
    )
    assert result["product_path_role"] == (
        "source_faithful_public_agent_execution_trace_refactor"
    )
    assert result["body_in_receipt"] is False
    assert result["body_import_verification"]["classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 5
    assert result["public_agent_execution_trace"]["summary"]["outcome_counts"] == {
        "allowed_sanitized": 1,
        "blocked": 2,
        "review_required": 1,
        "sanitized_warning": 1,
    }
    assert result["live_input_promotion"]["status"] == "pass"
    assert result["live_input_promotion"]["promotion_kind"] == (
        "public_tool_call_trace_to_taint_graph"
    )
    assert result["live_tool_call_trace_count"] == 1
    assert result["live_tool_call_taint_path_count"] == 1
    assert result["live_input_promotion"]["taint_propagation"][
        "derived_policy_verdict_mismatch_count"
    ] == 0
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_indirect_prompt_injection_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
        public_root
        / "fixtures/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay/input",
        public_root
        / "receipts/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
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
        assert "raw_email_body" not in keys
        assert "raw_document_body" not in keys
        assert "raw_prompt_body" not in keys
        assert "raw_system_prompt" not in keys
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "provider_payload" not in keys
        assert "hidden_system_message_body" not in keys
        assert "private_state_scan" not in keys


def test_indirect_prompt_injection_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_prompt_injection_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_prompt_injection_flow_bundle"
    assert (
        result["bundle_id"]
        == "indirect_prompt_injection_information_flow_policy_replay_public_trace_refactor_bundle"
    )
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["source_document_count"] == 5
    assert result["information_flow_count"] == 5
    assert result["block_count"] == 2
    assert result["review_count"] == 1
    assert result["cold_replay_pass_count"] == 5
    assert result["authority_ceiling"]["live_tool_call_authorized"] is False
    assert "public_replacement_refs" not in result
    assert "omitted_private_material" not in result
    verification = result["body_import_verification"]
    assert verification["verification_status"] == "verified"
    assert verification["verification_mode"] == (
        "extension_of_existing_public_refactor_with_live_digest_relation"
    )
    assert verification["classification"] == "extension_of_existing_public_refactor"
    assert verification["body_import_classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert verification["status"] == "pass"
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
        "agent_execution_trace.py::build_public_prompt_injection_trace"
    )
    assert verification["source_body_digest"] == _sha256(
        SOURCE_ROOT / "system/lib/agent_execution_trace.py"
    )
    assert verification["target_body_digest"] == _sha256(
        MICROCOSM_ROOT / "src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
    assert verification["source_module_digest_relation"] == (
        "manifest_target_digests_verified"
    )
    assert verification["source_module_digest_count"] == 5
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert (
        result["body_import_classification"]
        == "extension_of_existing_public_refactor"
    )
    assert result["body_in_receipt"] is False
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["body_material_status"] == (
        "copied_non_secret_prompt_injection_macro_body_landed"
    )
    assert result["body_copied_material_count"] == 5
    assert result["source_module_imports"]["verified_module_count"] == 5
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 5
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert (
        result["source_open_body_imports"]["body_text_exported_in_receipts"]
        is False
    )
    assert len(result["source_open_body_import_refs"]) == 5
    assert (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        in result["target_refs"]
    )
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["source_faithful_refactor"][
        "verification_mode"
    ] == "extension_of_existing_public_refactor"
    assert result["live_input_promotion"]["input_origin"] == (
        "generated_public_trace_span"
    )
    assert result["live_input_promotion"]["source_tool_name"] == (
        "prompt_injection_information_flow_policy"
    )
    assert {
        span["tool_name"] for span in result["public_agent_execution_trace"]["spans"]
    } == {"prompt_injection_information_flow_policy"}


def test_indirect_prompt_injection_rejects_hand_written_edge_taint() -> None:
    sources = validate_source_documents(
        json.loads((BUNDLE_INPUT / "source_documents.json").read_text())
    )
    graph = json.loads((BUNDLE_INPUT / "information_flow_graph.json").read_text())
    graph["information_flows"][0]["taint_labels"] = ["trusted_instruction"]

    result = validate_information_flow_graph(graph, sources["source_rows"])

    assert result["status"] == "blocked"
    assert result["taint_propagation"]["derived_taint_mismatch_count"] == 1
    assert {
        finding["error_code"] for finding in result["findings"]
    } >= {"PROMPT_INJECTION_TAINT_PROPAGATION_MISMATCH"}


def test_indirect_prompt_injection_rejects_hand_written_flow_verdict() -> None:
    sources = validate_source_documents(
        json.loads((BUNDLE_INPUT / "source_documents.json").read_text())
    )
    graph = json.loads((BUNDLE_INPUT / "information_flow_graph.json").read_text())
    graph["information_flows"][0]["policy_verdict"] = "allow"

    result = validate_information_flow_graph(graph, sources["source_rows"])

    assert result["status"] == "blocked"
    assert result["derived_policy_verdict_mismatch_count"] == 1
    assert result["taint_propagation"][
        "derived_policy_verdict_mismatch_count"
    ] == 1
    assert {
        finding["error_code"] for finding in result["findings"]
    } >= {"PROMPT_INJECTION_POLICY_VERDICT_DERIVATION_MISMATCH"}


def test_indirect_prompt_injection_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/indirect_prompt_injection_information_flow_policy_replay",
        public_root / "examples/indirect_prompt_injection_information_flow_policy_replay",
    )
    bundle = (
        public_root
        / "examples/indirect_prompt_injection_information_flow_policy_replay/"
        "exported_prompt_injection_flow_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_prompt_injection_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "PROMPT_INJECTION_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_indirect_prompt_injection_rejects_source_module_target_ref_path_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/indirect_prompt_injection_information_flow_policy_replay",
        public_root / "examples/indirect_prompt_injection_information_flow_policy_replay",
    )
    bundle = (
        public_root
        / "examples/indirect_prompt_injection_information_flow_policy_replay/"
        "exported_prompt_injection_flow_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["path"] = manifest["modules"][1]["path"]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_prompt_injection_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
    )

    first_module = result["source_module_imports"]["modules"][0]
    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert first_module["digest_match"] is True
    assert first_module["target_ref_matches_path"] is False
    assert (
        "PROMPT_INJECTION_SOURCE_MODULE_TARGET_REF_PATH_MISMATCH"
        in result["error_codes"]
    )
    assert (
        "PROMPT_INJECTION_SOURCE_MODULE_DIGEST_MISMATCH"
        not in result["error_codes"]
    )


def test_indirect_prompt_injection_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/indirect_prompt_injection_information_flow_policy_replay",
        public_root / "examples/indirect_prompt_injection_information_flow_policy_replay",
    )
    bundle = (
        public_root
        / "examples/indirect_prompt_injection_information_flow_policy_replay/"
        "exported_prompt_injection_flow_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_prompt_injection_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "PROMPT_INJECTION_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_indirect_prompt_injection_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/indirect_prompt_injection_information_flow_policy_replay",
        public_root / "examples/indirect_prompt_injection_information_flow_policy_replay",
    )
    bundle = (
        public_root
        / "examples/indirect_prompt_injection_information_flow_policy_replay/"
        "exported_prompt_injection_flow_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_prompt_injection_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "PROMPT_INJECTION_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_indirect_prompt_injection_rejects_source_module_manifest_body_text_boundary(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/indirect_prompt_injection_information_flow_policy_replay",
        public_root / "examples/indirect_prompt_injection_information_flow_policy_replay",
    )
    bundle = (
        public_root
        / "examples/indirect_prompt_injection_information_flow_policy_replay/"
        "exported_prompt_injection_flow_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["body_text_in_receipt"] = True
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_prompt_injection_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
    )
    source_modules = result["source_module_imports"]

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert source_modules["body_in_receipt"] is False
    assert source_modules["body_text_in_receipt"] is False
    assert "PROMPT_INJECTION_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED" in result[
        "error_codes"
    ]
    assert {
        row["subject_kind"]
        for row in source_modules["findings"]
        if row["error_code"] == "PROMPT_INJECTION_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED"
    } == {"body_text_in_receipt"}


def test_indirect_prompt_injection_source_module_digests_stream_without_read_bytes(
    monkeypatch,
) -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    module_row = manifest["modules"][0]
    module_path = MICROCOSM_ROOT / module_row["target_ref"].removeprefix(
        "microcosm-substrate/"
    )
    module_key = module_path.resolve()
    original_read_bytes = Path.read_bytes

    def fail_for_copied_module(path: Path) -> bytes:
        if path.resolve() == module_key:
            raise AssertionError("source-module digest should stream without read_bytes")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_for_copied_module)

    manifest_result = (
        indirect_prompt_injection_information_flow_policy_replay
        ._source_module_manifest_result(
            BUNDLE_INPUT,
            public_root=MICROCOSM_ROOT,
            require_manifest=True,
        )
    )
    freshness = (
        indirect_prompt_injection_information_flow_policy_replay
        ._freshness_basis(BUNDLE_INPUT, include_negative=False)
    )

    assert manifest_result["status"] == "pass"
    assert manifest_result["verified_module_count"] == 5
    assert (
        indirect_prompt_injection_information_flow_policy_replay._sha256(module_path)
        == module_row["sha256"]
    )
    expected_path = module_row["target_ref"].removeprefix("microcosm-substrate/")
    assert any(
        row["path"] == expected_path
        and row["sha256"] == module_row["sha256"]
        for row in freshness["inputs"]
    )


def test_indirect_prompt_injection_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["body_text_in_receipt"] is False
    assert manifest["module_count"] == 5
    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix(
            "microcosm-substrate/"
        )

        assert source.is_file()
        assert target.is_file()
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        source_digest = _sha256(source)
        target_digest = _sha256(target)
        assert source_digest == target_digest == row["sha256"]
        assert _digest_value(row["source_sha256"]) == _digest_value(source_digest)
        assert _digest_value(row["target_sha256"]) == _digest_value(target_digest)
        text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_indirect_prompt_injection_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay"
    )
    args = [
        "run-prompt-injection-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 16
    assert first_card["prompt_injection_flow"]["source_document_count"] == 5
    assert first_card["prompt_injection_flow"]["information_flow_count"] == 5
    assert first_card["prompt_injection_flow"]["block_count"] == 2
    assert first_card["prompt_injection_flow"]["review_count"] == 1
    assert first_card["prompt_injection_flow"]["cold_replay_pass_count"] == 5
    assert first_card["public_trace"]["span_count"] == 5
    assert first_card["live_input_promotion"]["status"] == "pass"
    assert first_card["live_input_promotion"]["live_tool_call_trace_count"] == 1
    assert first_card["live_input_promotion"]["taint_propagation_path_count"] == 1
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert first_card["validation"]["source_module_manifest_status"] == "pass"
    assert first_card["body_floor"]["body_material_status"] == (
        "copied_non_secret_prompt_injection_macro_body_landed"
    )
    assert first_card["body_floor"]["body_copied_material_count"] == 5
    assert first_card["body_floor"]["source_open_body_import_status"] == "pass"
    assert "source_rows" not in _walk_keys(first_card)
    assert "flow_rows" not in _walk_keys(first_card)
    assert "policy_verdict_rows" not in _walk_keys(first_card)
    assert "sanitized_output_rows" not in _walk_keys(first_card)
    assert "cold_replay_rows" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "spans" not in _walk_keys(first_card)
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        indirect_prompt_injection_information_flow_policy_replay,
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


def test_public_agent_execution_trace_refactor_builds_prompt_injection_spans() -> None:
    trace = build_public_prompt_injection_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert (
        trace["bundle_id"]
        == "indirect_prompt_injection_information_flow_policy_replay_public_trace_refactor_bundle"
    )
    assert trace["span_count"] == 5
    assert trace["summary"]["action_kind_counts"] == {
        "answer": 2,
        "external_action": 1,
        "instruction_channel": 1,
        "state_mutation": 1,
    }
    assert trace["audit"]["coverage"]["source_document_coverage"] is True
    assert trace["audit"]["coverage"]["policy_verdict_coverage"] is True
    assert trace["audit"]["coverage"]["sanitized_output_coverage"] is True
    assert trace["audit"]["coverage"]["cold_replay_coverage"] is True
    assert trace["audit"]["coverage"]["trusted_context_non_disclosure"] is True
    assert trace["audit"]["coverage"]["untrusted_instruction_non_adoption"] is True
    assert "system/lib/agent_execution_trace.py" in trace["source_refs"]


def test_indirect_prompt_injection_fixture_manifests_bind_public_trace_refactor() -> None:
    for manifest_path in FIXTURE_MANIFESTS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert "body_redacted" not in manifest
        assert "public_replacement_refs" not in manifest
        assert "private_state_scan" not in manifest
        assert not manifest["authority_ceiling"].startswith(
            "synthetic_indirect_prompt_injection_information_flow_replay_receipts_only"
        )
        assert (
            manifest["body_import_status"]
            == "extension_of_existing_public_refactor_landed"
        )
        assert (
            manifest["product_path_role"]
            == "source_faithful_public_agent_execution_trace_refactor"
        )
        assert manifest["body_in_receipt"] is False
        assert manifest["body_import_verification"] == {
            "body_import_classification": "extension_of_existing_public_refactor",
            "source_ref": "system/lib/agent_execution_trace.py",
            "source_module_manifest_ref": (
                "examples/indirect_prompt_injection_information_flow_policy_replay/"
                "exported_prompt_injection_flow_bundle/source_module_manifest.json"
            ),
            "source_open_body_import_count": 5,
            "target_ref": (
                "microcosm-substrate/src/microcosm_core/macro_tools/"
                "agent_execution_trace.py"
            ),
            "validation_refs": [
                (
                    "microcosm-substrate/tests/"
                    "test_indirect_prompt_injection_information_flow_policy_replay.py"
                )
            ],
            "verification_mode": "extension_of_existing_public_refactor",
            "verification_status": "verified",
        }
        assert manifest["source_module_manifest_ref"].endswith(
            "source_module_manifest.json"
        )
        assert manifest["body_material_status"] == (
            "copied_non_secret_prompt_injection_macro_body_landed"
        )
        assert manifest["body_copied_material_count"] == 5
        assert manifest["source_open_body_imports"]["status"] == "pass"
        assert manifest["source_open_body_imports"]["body_material_count"] == 5
        assert manifest["source_open_body_imports"]["body_in_receipt"] is False
        assert (
            "microcosm_core.macro_tools.agent_execution_trace::"
            "build_public_prompt_injection_trace"
            in manifest["fixture_runtime_refs"]
        )
        assert (
            "microcosm-substrate/src/microcosm_core/macro_tools/"
            "agent_execution_trace.py"
            in manifest["target_refs"]
        )
        assert set(manifest["negative_case_ids"]) == set(EXPECTED_NEGATIVE_CASES)
