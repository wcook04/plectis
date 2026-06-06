from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.organs.standards_meta_diagnostics as standards_meta_diagnostics
from microcosm_core.organs.standards_meta_diagnostics import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    _sha256,
    main,
    run,
    run_diagnostics_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/standards_meta_diagnostics/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"
STANDARDS_META_SOURCE_MODULE_IDS = {
    "standards_meta_diagnostics_macro_generator_body_import",
    "standards_meta_diagnostics_macro_receipt_body_import",
    "standards_meta_diagnostics_macro_test_body_import",
}


def _fixture_accepted_organ_count(input_dir: Path = FIXTURE_INPUT) -> int:
    payload = json.loads((input_dir / "diagnostic_policy.json").read_text(encoding="utf-8"))
    return len(
        [
            organ_id
            for organ_id in payload.get("accepted_organ_ids", [])
            if isinstance(organ_id, str)
        ]
    )


def _accepted_organs_from_registry() -> list[str]:
    return _accepted_organs_from_registry_root(MICROCOSM_ROOT)


def _accepted_organs_from_registry_root(public_root: Path) -> list[str]:
    registry = json.loads(
        (public_root / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    return [
        str(row["organ_id"])
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]


def _assert_diagnostics_inputs_track_registry(input_dir: Path) -> None:
    expected_organs = _accepted_organs_from_registry()
    policy = json.loads((input_dir / "diagnostic_policy.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (input_dir / "standards_inventory.json").read_text(encoding="utf-8")
    )
    runtime = json.loads(
        (input_dir / "organ_runtime_contracts.json").read_text(encoding="utf-8")
    )

    inventory_rows = inventory["standards_inventory"]
    runtime_rows = runtime["runtime_contracts"]

    assert policy["accepted_organ_ids"] == expected_organs
    assert policy["minimum_standard_mapping_count"] == len(expected_organs)
    assert policy["minimum_runtime_contract_count"] == len(expected_organs)
    assert [row["organ_id"] for row in inventory_rows] == expected_organs
    assert [row["organ_id"] for row in runtime_rows] == expected_organs

    for row in inventory_rows:
        assert (MICROCOSM_ROOT / row["standard_ref"]).is_file()
        assert row["standard_id"] == f"std_microcosm_{row['organ_id']}"
        assert row["registry_row_ref"].endswith(f"[{row['standard_id']}]")
        assert row["registry_standard_id"] == row["standard_id"]
        assert row["registry_path"] == row["standard_ref"]
        assert isinstance(row["registry_used_by_organ"], bool)
        assert row["standard_payload_standard_id"] == row["standard_id"]
        assert isinstance(row["standard_payload_used_by_organ"], bool)
        assert row["receipt_refs"]
        assert row["body_in_receipt"] is False

    for row in runtime_rows:
        assert row["cli_command"]
        assert row["runtime_step"] == (
            f"microcosm_core.runtime_shell.RUNTIME_STEPS::{row['organ_id']}"
        )
        assert row["runtime_receipt_count"] > 0
        assert row["body_in_receipt"] is False


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


def _copy_standards_meta_public_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "standards", public_root / "standards")
    runtime_shell = public_root / "src/microcosm_core/runtime_shell.py"
    runtime_shell.parent.mkdir(parents=True)
    shutil.copy2(MICROCOSM_ROOT / "src/microcosm_core/runtime_shell.py", runtime_shell)
    fixture_root = public_root / "fixtures/first_wave/standards_meta_diagnostics"
    shutil.copytree(FIXTURE_INPUT.parent, fixture_root)
    return public_root


def _copy_standards_meta_bundle_public_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    example_root = public_root / "examples/standards_meta_diagnostics"
    shutil.copytree(EXPORTED_BUNDLE.parent, example_root)
    manifest = json.loads(
        (
            example_root
            / "exported_standards_meta_diagnostics_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    for row in manifest["modules"]:
        source_ref = row["source_ref"]
        source = MICROCOSM_ROOT.parent / source_ref
        target = tmp_path / source_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return public_root


def test_standards_meta_diagnostics_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/standards_meta_diagnostics_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    expected_count = len(_accepted_organs_from_registry())
    assert result["accepted_organ_count"] == expected_count
    assert result["standard_mapping_count"] == expected_count
    assert result["runtime_contract_count"] == expected_count
    assert "certificate_kernel_execution_lab" in result["covered_organ_ids"]
    assert "materials_chemistry_closed_loop_lab_safety_replay" in result["covered_organ_ids"]
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["authority_ceiling"]["standards_registry_authority"] is False
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert any(
        ref.endswith("core/standards_registry.json")
        for ref in result["public_runtime_refs"]
    )
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_standards_meta_diagnostics_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_diagnostics_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_standards_meta_diagnostics_bundle"
    assert result["bundle_id"] == "public_standards_meta_diagnostics_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["accepted_organ_count"] == _fixture_accepted_organ_count(EXPORTED_BUNDLE)
    assert "lean_std_premise_index" in result["covered_organ_ids"]
    assert "formal_math_verifier_trace_repair_loop" in result["covered_organ_ids"]
    assert "verifier_lab_execution_spine" in result["covered_organ_ids"]
    assert "certificate_kernel_execution_lab" in result["covered_organ_ids"]
    assert "formal_evidence_cell_anchor_resolver" in result["covered_organ_ids"]
    assert "undeclared_library_prior_symbol_classifier" in result["covered_organ_ids"]
    assert "agent_benchmark_integrity_anti_gaming_replay" in result["covered_organ_ids"]
    assert "durable_agent_work_landing_replay" in result["covered_organ_ids"]
    assert "standards_meta_diagnostics" in result["covered_organ_ids"]
    assert "cold_reader_route_map" in result["covered_organ_ids"]
    assert "agent_monitor_redteam_falsification_replay" in result["covered_organ_ids"]
    assert "agent_sabotage_scheming_monitor_replay" in result["covered_organ_ids"]
    assert "agent_sandbox_policy_escape_replay" in result["covered_organ_ids"]
    assert "indirect_prompt_injection_information_flow_policy_replay" in result["covered_organ_ids"]
    assert "agent_memory_temporal_conflict_replay" in result["covered_organ_ids"]
    assert "sleeper_memory_poisoning_quarantine_replay" in result["covered_organ_ids"]
    assert "mcp_tool_authority_replay" in result["covered_organ_ids"]
    assert "proof_derived_governed_mutation_authorization" in result["covered_organ_ids"]
    assert "belief_state_process_reward_replay" in result["covered_organ_ids"]
    assert "materials_chemistry_closed_loop_lab_safety_replay" in result["covered_organ_ids"]
    assert result["authority_ceiling"]["whole_system_correctness_claim"] is False
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["body_copied_material_count"] == 3
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 3
    assert source_imports["source_authority_ref_count"] == 3
    assert set(source_imports["body_material_ids"]) == STANDARDS_META_SOURCE_MODULE_IDS
    assert source_imports["body_material_classes"] == {
        "public_macro_receipt_body": 1,
        "public_macro_tool_body": 2,
    }
    assert source_imports["body_in_receipt"] is False
    assert source_imports["body_text_in_receipt"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)


def test_standards_meta_diagnostics_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_bundle_public_root(tmp_path)
    bundle = (
        public_root
        / "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "0" * 64
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_diagnostics_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "STANDARDS_META_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_standards_meta_diagnostics_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_bundle_public_root(tmp_path)
    bundle = (
        public_root
        / "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_diagnostics_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "STANDARDS_META_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH" in result["error_codes"]


def test_standards_meta_diagnostics_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_bundle_public_root(tmp_path)
    bundle = (
        public_root
        / "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_diagnostics_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "STANDARDS_META_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_standards_meta_diagnostics_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics"
    args = [
        "run-diagnostics-bundle",
        "--input",
        str(EXPORTED_BUNDLE),
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
    assert first_card["diagnostic_projection"]["accepted_organ_count"] == (
        _fixture_accepted_organ_count(EXPORTED_BUNDLE)
    )
    assert first_card["source_open_body_imports"]["status"] == "pass"
    assert first_card["source_open_body_imports"]["body_material_count"] == 3
    assert "covered_organ_ids" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(standards_meta_diagnostics, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
    assert cached_card["source_open_body_imports"] == first_card["source_open_body_imports"]


def test_standards_meta_diagnostics_sha256_streams_source_modules(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    payload = b"standards meta diagnostics body\n" * 4096
    source.write_bytes(payload)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == source:
            raise AssertionError("source modules should be hashed without read_bytes")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256(source) == hashlib.sha256(payload).hexdigest()


def test_standards_meta_diagnostics_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    modules = manifest["modules"]

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 3
    assert {row["module_id"] for row in modules} == STANDARDS_META_SOURCE_MODULE_IDS

    for row in modules:
        source_path = MICROCOSM_ROOT.parent / row["source_ref"]
        target_path = MICROCOSM_ROOT.parent / row["target_ref"]
        source_bytes = source_path.read_bytes()
        target_bytes = target_path.read_bytes()
        digest = hashlib.sha256(source_bytes).hexdigest()

        assert source_bytes == target_bytes
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        text = target_bytes.decode("utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_standards_meta_diagnostics_rejects_forged_source_module_ref(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_bundle_public_root(tmp_path)
    bundle = (
        public_root
        / "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_ref"] = "self-indexing-cognitive-substrate/forged.py"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_diagnostics_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "STANDARDS_META_SOURCE_MODULE_SOURCE_REF_MISSING" in result["error_codes"]


def test_standards_meta_diagnostics_rejects_stale_bundle_copy_when_live_source_changes(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_bundle_public_root(tmp_path)
    bundle = (
        public_root
        / "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle"
    )
    manifest = json.loads(
        (bundle / "source_module_manifest.json").read_text(encoding="utf-8")
    )
    live_source = tmp_path / manifest["modules"][0]["source_ref"]
    live_source.write_text(
        live_source.read_text(encoding="utf-8") + "\n# live source drift\n",
        encoding="utf-8",
    )

    result = run_diagnostics_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "STANDARDS_META_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["freshness_basis"]["missing_path_count"] == 0


def test_standards_meta_diagnostics_receipts_use_secret_exclusion(tmp_path: Path) -> None:
    out = tmp_path / "receipts/first_wave/standards_meta_diagnostics"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "standards_meta_diagnostics_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["body_in_receipt"] is False
    assert payload["real_runtime_receipt"] is True
    assert payload["synthetic_receipt_standin_allowed"] is False
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    assert "private_state_scan" not in payload
    assert "body_redacted" not in _walk_keys(payload)


def test_standards_meta_diagnostics_input_builder_tracks_live_registry(
    tmp_path: Path,
) -> None:
    build_result = standards_meta_diagnostics.write_diagnostics_input_payloads(
        MICROCOSM_ROOT,
        tmp_path,
    )

    assert build_result["status"] == "pass"
    assert build_result["accepted_organ_count"] == len(_accepted_organs_from_registry())
    _assert_diagnostics_inputs_track_registry(tmp_path)


def test_standards_meta_diagnostics_run_uses_live_positive_projection(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    fixture_input = (
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input"
    )
    (fixture_input / "diagnostic_policy.json").write_text(
        json.dumps(
            {
                "schema_version": "standards_meta_diagnostics_policy_v1",
                "accepted_organ_ids": [],
                "minimum_runtime_contract_count": 0,
                "minimum_standard_mapping_count": 0,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (fixture_input / "standards_inventory.json").write_text(
        json.dumps(
            {
                "schema_version": "standards_meta_diagnostics_inventory_v1",
                "standards_inventory": [],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (fixture_input / "organ_runtime_contracts.json").write_text(
        json.dumps(
            {
                "schema_version": "standards_meta_diagnostics_runtime_contracts_v1",
                "runtime_contracts": [],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        command="pytest",
    )

    expected_count = len(_accepted_organs_from_registry())
    assert result["status"] == "pass"
    assert result["accepted_organ_count"] == expected_count
    assert result["standard_mapping_count"] == expected_count
    assert result["runtime_contract_count"] == expected_count
    assert result["freshness_basis"]["missing_path_count"] == 0


def test_standards_meta_diagnostics_run_does_not_depend_on_static_positive_inputs(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    fixture_input = (
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input"
    )
    for filename in standards_meta_diagnostics.INPUT_NAMES:
        (fixture_input / filename).unlink()

    result = run(
        fixture_input,
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        command="pytest",
    )

    expected_count = len(_accepted_organs_from_registry_root(public_root))
    freshness_paths = {
        row["path"] for row in result["freshness_basis"]["inputs"]
    }
    assert result["status"] == "pass"
    assert result["accepted_organ_count"] == expected_count
    assert result["standard_mapping_count"] == expected_count
    assert result["runtime_contract_count"] == expected_count
    assert result["freshness_basis"]["project_positive_from_live"] is True
    assert result["freshness_basis"]["missing_path_count"] == 0
    assert not any(
        path.endswith(filename)
        for path in freshness_paths
        for filename in standards_meta_diagnostics.INPUT_NAMES
    )
    assert any(path.endswith("core/organ_registry.json") for path in freshness_paths)
    assert any(path.endswith("core/standards_registry.json") for path in freshness_paths)


def test_standards_meta_diagnostics_run_card_reports_live_positive_projection(
    tmp_path: Path,
    capsys: Any,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    fixture_input = (
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input"
    )
    for filename in standards_meta_diagnostics.INPUT_NAMES:
        (fixture_input / filename).unlink()
    out = tmp_path / "receipts/first_wave/standards_meta_diagnostics"

    assert main(["run", "--input", str(fixture_input), "--out", str(out), "--card"]) == 0
    card = json.loads(capsys.readouterr().out)

    assert card["status"] == "pass"
    assert card["command_speed"]["project_positive_from_live"] is True
    assert card["command_speed"]["freshness_missing_path_count"] == 0
    assert card["diagnostic_projection"]["accepted_organ_count"] == len(
        _accepted_organs_from_registry_root(public_root)
    )


def test_standards_meta_diagnostics_run_projects_positive_inputs_from_live_registry(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    fixture_input = (
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input"
    )
    payloads = standards_meta_diagnostics.build_diagnostics_input_payloads(public_root)
    row = payloads["standards_inventory.json"]["standards_inventory"][0]
    missing_standard = public_root / row["standard_ref"]
    missing_standard.unlink()

    result = run(
        fixture_input,
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "STANDARDS_META_MISSING_STANDARD_REF" in result["error_codes"]
    assert any(
        finding["error_code"] == "STANDARDS_META_MISSING_STANDARD_REF"
        and finding["negative_case_id"] == "positive_inventory"
        and finding["subject_id"] == row["organ_id"]
        for finding in result["findings"]
    )
    assert result["accepted_organ_count"] == len(_accepted_organs_from_registry())
    assert result["freshness_basis"]["missing_path_count"] >= 1
    assert any(
        row["standard_ref"] in path
        for path in result["freshness_basis"]["missing_inputs"]
    )


def test_standards_meta_diagnostics_registry_receipt_perturbation_blocks(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    accepted_rows = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]
    accepted_rows[0]["generated_receipts"] = []
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8"
    )
    fixture_input = (
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input"
    )

    result = run(
        fixture_input,
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "STANDARDS_META_MISSING_RECEIPT_REF" in result["error_codes"]
    assert any(
        finding["subject_id"] == accepted_rows[0]["organ_id"]
        and finding["negative_case_id"] == "positive_inventory"
        for finding in result["findings"]
    )


def test_standards_meta_diagnostics_registry_standard_row_perturbation_blocks(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    payloads = standards_meta_diagnostics.build_diagnostics_input_payloads(public_root)
    row = payloads["standards_inventory.json"]["standards_inventory"][0]
    standards_registry_path = public_root / "core/standards_registry.json"
    standards_registry = json.loads(
        standards_registry_path.read_text(encoding="utf-8")
    )
    registry_row = next(
        item
        for item in standards_registry["standards"]
        if item["standard_id"] == row["standard_id"]
    )
    registry_row["path"] = "standards/forged_standard.json"
    standards_registry_path.write_text(
        json.dumps(standards_registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run(
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input",
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "STANDARDS_META_STANDARD_REGISTRY_MISMATCH" in result["error_codes"]
    assert any(
        finding["subject_id"] == row["organ_id"]
        and finding["subject_kind"] == "standards_registry"
        for finding in result["findings"]
    )


def test_standards_meta_diagnostics_standard_payload_perturbation_blocks(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    payloads = standards_meta_diagnostics.build_diagnostics_input_payloads(public_root)
    row = payloads["standards_inventory.json"]["standards_inventory"][0]
    standard_path = public_root / row["standard_ref"]
    standard_payload = json.loads(standard_path.read_text(encoding="utf-8"))
    standard_payload["standard_id"] = "std_microcosm_forged_standard"
    standard_path.write_text(
        json.dumps(standard_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run(
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input",
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "STANDARDS_META_STANDARD_PAYLOAD_MISMATCH" in result["error_codes"]
    assert any(
        finding["subject_id"] == row["organ_id"]
        and finding["subject_kind"] == "standard_payload"
        for finding in result["findings"]
    )


def test_standards_meta_diagnostics_registry_status_perturbation_moves_count(
    tmp_path: Path,
) -> None:
    public_root = _copy_standards_meta_public_root(tmp_path)
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    accepted_rows = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]
    removed_organ_id = accepted_rows[0]["organ_id"]
    accepted_rows[0]["status"] = "draft"
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run(
        public_root / "fixtures/first_wave/standards_meta_diagnostics/input",
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        command="pytest",
    )

    expected_organs = _accepted_organs_from_registry_root(public_root)
    assert result["status"] == "pass"
    assert result["accepted_organ_count"] == len(expected_organs)
    assert removed_organ_id not in result["covered_organ_ids"]
    assert result["standard_mapping_count"] == len(expected_organs)
    assert result["freshness_basis"]["missing_path_count"] == 0


def test_standards_meta_diagnostics_input_builder_emits_live_payloads(
    tmp_path: Path,
) -> None:
    build_result = standards_meta_diagnostics.write_diagnostics_input_payloads(
        MICROCOSM_ROOT,
        tmp_path,
    )

    assert build_result["status"] == "pass"
    assert build_result["accepted_organ_count"] == len(_accepted_organs_from_registry())
    for filename in standards_meta_diagnostics.INPUT_NAMES:
        built = json.loads((tmp_path / filename).read_text(encoding="utf-8"))
        assert isinstance(built, dict)
        assert built["generated_from"] == standards_meta_diagnostics.DIAGNOSTICS_INPUT_SCHEMA
