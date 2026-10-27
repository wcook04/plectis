from __future__ import annotations

import hashlib
import json
import shutil
import shlex
from pathlib import Path
from typing import Any

import pytest

from microcosm_core import cli as microcosm_cli
from microcosm_core.organs.public_reveal_walkthrough import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    HASH_CHUNK_SIZE,
    _sha256,
    main,
    run,
    run_reveal_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/public_reveal_walkthrough/input"
BUNDLE_INPUT = MICROCOSM_ROOT / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"
FIXTURE_MANIFEST = (
    MICROCOSM_ROOT
    / "core/fixture_manifests/public_reveal_walkthrough.fixture_manifest.json"
)
STANDARD = MICROCOSM_ROOT / "standards/std_microcosm_public_reveal_walkthrough.json"
ORGAN_REGISTRY = MICROCOSM_ROOT / "core/organ_registry.json"
ORGAN_EVIDENCE_CLASSES = MICROCOSM_ROOT / "core/organ_evidence_classes.json"
PUBLIC_REVEAL_SOURCE_MODULE_IDS = {"public_reveal_walkthrough_control_plane_source_body_import"}
PUBLIC_REVEAL_OMITTED_SOURCE_IDS = {
    "public_reveal_first_slice_execution_receipt_body_import",
    "public_reveal_runtime_shell_reorientation_receipt_body_import",
    "public_reveal_clean_clone_state_fixture_receipt_body_import",
    "public_reveal_public_substrate_boundary_policy_body_import",
}
# Source references identify historical material; these fixed hashes are for
# the public substitution stubs, not for the withheld original bodies.
PUBLIC_REVEAL_OMISSION_REFS = {
    "public_reveal_first_slice_execution_receipt_body_import": ("state/microcosm_portfolio/reconstruction/public_first_slice_build_execution_receipt_v1.json", "dde545c0ed550d0dee81c764ce240569f2485ce23e71b17f1f298ccd37757541"),
    "public_reveal_runtime_shell_reorientation_receipt_body_import": ("state/microcosm_portfolio/reconstruction/public_microcosm_runtime_shell_reorientation_receipt_v1.json", "ce8826414ab1a08697fda172ccd476b90bb28949b0409e7de4c96e6c8075c7e4"),
    "public_reveal_clean_clone_state_fixture_receipt_body_import": ("state/microcosm_portfolio/reconstruction/public_clean_clone_state_fixture_repair_receipt_v1.json", "2651a95163fd727b18ca8b26316d33ec68210ffad0a4aa5cd93ac94aa3fc4007"),
    "public_reveal_public_substrate_boundary_policy_body_import": ("state/microcosm_portfolio/reconstruction/public_substrate_boundary_policy_v1.json", "63a7088e50d9338b873df4f05972db1f8878786b51ac9e63caa822239b30e153"),
}
SCRATCH_WALKTHROUGH_REF = "/tmp/microcosm-scratch"
LOCAL_PATH_MARKERS = ("/private/", "/tmp/", "/Users/", "src/ai_workflow")


def _assert_public_safe_receipt_refs(receipt_refs: list[str]) -> None:
    assert receipt_refs
    for receipt_ref in receipt_refs:
        assert not Path(receipt_ref).is_absolute()
        assert not any(marker in receipt_ref for marker in LOCAL_PATH_MARKERS)


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


def _commands_by_step(result: dict[str, Any]) -> dict[str, list[str]]:
    steps = result["reveal_board"]["steps"]
    return {
        str(step["step_id"]): list(step["commands"])
        for step in steps
        if isinstance(step, dict)
    }


def _source_checkout_commands_by_step(result: dict[str, Any]) -> dict[str, list[str]]:
    steps = result["reveal_board"]["steps"]
    return {
        str(step["step_id"]): list(step["source_checkout_commands"])
        for step in steps
        if isinstance(step, dict)
    }


def _copy_public_reveal_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    public_root.mkdir()
    shutil.copy2(MICROCOSM_ROOT / "pyproject.toml", public_root / "pyproject.toml")
    (public_root / "src/microcosm_core").mkdir(parents=True)
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/public_reveal_walkthrough",
        public_root / "fixtures/first_wave/public_reveal_walkthrough",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/public_reveal_walkthrough",
        public_root / "examples/public_reveal_walkthrough",
    )
    return public_root


def _microcosm_command_argv(command: str, scratch: Path) -> list[str]:
    parts = shlex.split(command.replace(SCRATCH_WALKTHROUGH_REF, scratch.as_posix()))
    assert parts[0] == "microcosm"
    return parts[1:]


def _source_checkout_command_argv(command: str, scratch: Path) -> list[str]:
    parts = shlex.split(command.replace(SCRATCH_WALKTHROUGH_REF, scratch.as_posix()))
    assert parts[:4] == ["PYTHONPATH=src", "python3", "-m", "microcosm_core"]
    return parts[4:]


def test_public_reveal_sha256_streams_source_module_digest(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source_module = tmp_path / "source_module.py"
    body = (b"public-reveal-source-module\n" * (HASH_CHUNK_SIZE // 28 + 2)) + b"tail\n"
    source_module.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == source_module:
            raise AssertionError("public reveal digest should stream source modules")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256(source_module) == f"sha256:{hashlib.sha256(body).hexdigest()}"


def test_public_reveal_walkthrough_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/public_reveal_walkthrough",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/public_reveal_walkthrough_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["observed_negative_cases"] == EXPECTED_NEGATIVE_CASES
    assert result["missing_negative_cases"] == []
    assert result["step_count"] == 5
    assert result["command_count"] >= 4
    assert "microcosm run --card examples/runtime_shell/demo_project" in result["commands"]
    assert "microcosm intake --card" in result["commands"]
    assert "microcosm authority --card" in result["commands"]
    assert "microcosm intake" not in result["commands"]
    assert "microcosm status" not in result["commands"]
    assert result["evidence_ref_count"] >= 4
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["reveal_board"]["primary_loop"].startswith("repo -> .microcosm")
    assert result["reveal_board"]["first_command"] == "python -m pip install -e '.[test]'"
    assert result["reveal_board"]["source_checkout_first_command"] == (
        "PYTHONPATH=src python3 -m microcosm_core compile /tmp/microcosm-scratch"
    )
    assert result["reveal_board"]["steps"][0]["source_checkout_commands"] == [
        "PYTHONPATH=src python3 -m microcosm_core compile /tmp/microcosm-scratch"
    ]
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["real_lane_witness"]["status"] == "pass"
    assert result["real_lane_witness"]["current_source_body_import_status"] == "pass"
    assert result["real_lane_witness"]["current_body_material_count"] == 1
    assert result["public_runtime_refs"]
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_public_reveal_walkthrough_receipts_are_public_relative_and_secret_excluded(tmp_path: Path) -> None:
    public_root = _copy_public_reveal_root(tmp_path)

    result = run(
        public_root / "fixtures/first_wave/public_reveal_walkthrough/input",
        public_root / "receipts/first_wave/public_reveal_walkthrough",
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
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert payload["real_lane_witness"]["status"] == "pass"
        assert payload["real_lane_witness"]["current_source_body_import_status"] == "pass"
        assert payload["real_lane_witness"]["current_body_material_count"] == 1
        assert payload["public_runtime_refs"]
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_public_reveal_audience_floor_perturbation_changes_verdict(tmp_path: Path) -> None:
    public_root = _copy_public_reveal_root(tmp_path)
    input_dir = public_root / "fixtures/first_wave/public_reveal_walkthrough/input"

    baseline = run(
        input_dir,
        public_root / "receipts/baseline/public_reveal_walkthrough",
        command="pytest",
    )

    floor_path = input_dir / "audience_claim_floor.json"
    floor = json.loads(floor_path.read_text(encoding="utf-8"))
    floor["public_claim"] = floor["public_claim"].replace("routes, ", "")
    floor_path.write_text(
        json.dumps(floor, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    perturbed = run(
        input_dir,
        public_root / "receipts/perturbed/public_reveal_walkthrough",
        command="pytest",
    )

    assert baseline["status"] == "pass"
    assert perturbed["status"] == "blocked"
    assert perturbed["real_runtime_receipt"] is False
    assert baseline["public_claim"] != perturbed["public_claim"]
    assert "PUBLIC_REVEAL_CLAIM_FLOOR_MISSING" in perturbed["error_codes"]
    assert perturbed["real_lane_witness"]["status"] == "pass"


def test_public_reveal_evidence_map_perturbation_changes_verdict(tmp_path: Path) -> None:
    public_root = _copy_public_reveal_root(tmp_path)
    input_dir = public_root / "fixtures/first_wave/public_reveal_walkthrough/input"

    baseline = run(
        input_dir,
        public_root / "receipts/baseline/public_reveal_walkthrough",
        command="pytest",
    )

    evidence_path = input_dir / "substrate_evidence_map.json"
    evidence_map = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence_map["evidence"][0]["projection_not_authority"] = False
    evidence_map["evidence"][0]["ref"] = ""
    evidence_path.write_text(
        json.dumps(evidence_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    perturbed = run(
        input_dir,
        public_root / "receipts/perturbed/public_reveal_walkthrough",
        command="pytest",
    )

    assert baseline["status"] == "pass"
    assert perturbed["status"] == "blocked"
    assert perturbed["real_runtime_receipt"] is False
    assert "PUBLIC_REVEAL_EVIDENCE_MAP_INCOMPLETE" in perturbed["error_codes"]
    assert any(
        finding["error_code"] == "PUBLIC_REVEAL_EVIDENCE_MAP_INCOMPLETE"
        and finding["subject_id"] == "product_loop_readme"
        for finding in perturbed["findings"]
    )
    assert perturbed["real_lane_witness"]["status"] == "pass"


def test_public_reveal_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_reveal_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_public_reveal_bundle"
    assert result["bundle_id"] == "public_reveal_walkthrough_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert "microcosm intake --card" in result["commands"]
    assert "microcosm authority --card" in result["commands"]
    assert "microcosm intake" not in result["commands"]
    assert "microcosm status" not in result["commands"]
    assert result["reveal_board"]["release_authorized"] is False
    assert result["reveal_board"]["first_command"] == "python -m pip install -e '.[test]'"
    assert result["reveal_board"]["source_checkout_first_command"] == (
        "PYTHONPATH=src python3 -m microcosm_core compile /tmp/microcosm-scratch"
    )
    assert (
        "PYTHONPATH=src python3 -m microcosm_core authority --card"
        in result["source_checkout_commands"]
    )
    assert result["public_claim"].startswith("Microcosm turns a repo")
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["body_copied_material_count"] == 1
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 1
    assert set(source_imports["body_material_ids"]) == PUBLIC_REVEAL_SOURCE_MODULE_IDS
    assert source_imports["body_material_classes"] == {"public_python_source_body": 1}
    assert source_imports["body_in_receipt"] is False
    assert source_imports["body_text_in_receipt"] is False
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["public_runtime_refs"]
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_public_reveal_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_reveal_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_verified_count"] == len(
        PUBLIC_REVEAL_SOURCE_MODULE_IDS
    ) - 1
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert "PUBLIC_REVEAL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_public_reveal_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_reveal_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_verified_count"] == len(
        PUBLIC_REVEAL_SOURCE_MODULE_IDS
    ) - 1
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert "PUBLIC_REVEAL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_public_reveal_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_reveal_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_verified_count"] == len(
        PUBLIC_REVEAL_SOURCE_MODULE_IDS
    ) - 1
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert "PUBLIC_REVEAL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_public_reveal_fixture_command_rejects_tampered_real_lane_witness(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_reveal_root(tmp_path)
    manifest_path = (
        public_root
        / "examples/public_reveal_walkthrough/exported_public_reveal_bundle/source_module_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        public_root / "fixtures/first_wave/public_reveal_walkthrough/input",
        public_root / "receipts/first_wave/public_reveal_walkthrough",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["real_runtime_receipt"] is False
    assert result["missing_negative_cases"] == []
    assert result["real_lane_witness"]["status"] == "blocked"
    assert result["real_lane_witness"]["current_source_body_import_status"] == "blocked"
    assert "PUBLIC_REVEAL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert "PUBLIC_REVEAL_REAL_LANE_WITNESS_BLOCKED" in result["error_codes"]
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_public_reveal_scratch_compile_explain_commands_are_copy_paste_valid(
    tmp_path: Path,
    capsys: Any,
) -> None:
    result = run_reveal_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough",
        command="pytest",
    )
    commands_by_step = _commands_by_step(result)
    source_commands_by_step = _source_checkout_commands_by_step(result)
    compile_command = next(
        command
        for command in commands_by_step["install_and_compile"]
        if command.startswith("microcosm compile ")
    )
    source_compile_command = source_commands_by_step["install_and_compile"][0]
    explain_command = commands_by_step["inspect_route_explanation"][0]
    scratch = tmp_path / "microcosm-scratch"
    scratch.mkdir()

    assert compile_command == f"microcosm compile {SCRATCH_WALKTHROUGH_REF}"
    assert source_compile_command == (
        f"PYTHONPATH=src python3 -m microcosm_core compile {SCRATCH_WALKTHROUGH_REF}"
    )
    assert explain_command == (
        f"microcosm explain {SCRATCH_WALKTHROUGH_REF} missing_tests_route"
    )

    assert microcosm_cli.main(_microcosm_command_argv(compile_command, scratch)) == 0
    compiled = json.loads(capsys.readouterr().out)
    assert compiled["selected_route_id"] == "missing_tests_route"

    assert (
        microcosm_cli.main(_source_checkout_command_argv(source_compile_command, scratch))
        == 0
    )
    source_compiled = json.loads(capsys.readouterr().out)
    assert source_compiled["selected_route_id"] == compiled["selected_route_id"]

    assert microcosm_cli.main(_microcosm_command_argv(explain_command, scratch)) == 0
    explanation = json.loads(capsys.readouterr().out)
    assert explanation["status"] == "pass"
    assert explanation["route_id"] == compiled["selected_route_id"]
    assert (scratch / ".microcosm/explanations/missing_tests_route.json").is_file()


def test_public_reveal_exported_bundle_card_is_compact(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "bundle-card"

    rc = main(
        [
            "run-reveal-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = out_dir / "exported_public_reveal_bundle_validation_result.json"

    assert rc == 0
    assert len(captured.encode("utf-8")) < 4000
    assert full_receipt.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == "public_reveal_walkthrough"
    assert card["input_mode"] == "exported_public_reveal_bundle"
    assert card["bundle_id"] == "public_reveal_walkthrough_runtime_example"
    assert card["real_lane_witness"] == {
        "current_input_is_exported_bundle_witness": True,
        "witness_action": "run-reveal-bundle",
        "witness_input_ref": "examples/public_reveal_walkthrough/exported_public_reveal_bundle",
        "source_module_manifest_ref": "examples/public_reveal_walkthrough/exported_public_reveal_bundle/source_module_manifest.json",
        "source_body_imports_required_for_witness": True,
        "current_source_body_import_status": "pass",
        "current_body_material_count": 1,
    }
    assert card["reveal_summary"]["step_count"] == 5
    assert card["reveal_summary"]["command_count"] == 8
    assert card["reveal_summary"]["evidence_ref_count"] == 11
    assert card["negative_case_coverage"]["expected_case_count"] == 0
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["secret_exclusion_scan_summary"]["hits_exported"] is False
    assert card["receipt_paths"] == [
        "external_receipt/exported_public_reveal_bundle_validation_result.json"
    ]
    _assert_public_safe_receipt_refs(card["receipt_paths"])
    assert card["source_open_body_imports"]["status"] == "pass"
    assert card["source_open_body_imports"]["body_material_count"] == 1
    assert card["source_open_body_imports"]["evidence_source"] == "current_input"
    assert card["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert card["authority_ceiling"]["release_authorized"] is False
    assert card["no_export_guards"]["step_rows_exported"] is False
    assert card["no_export_guards"]["commands_exported"] is False
    assert card["no_export_guards"]["public_runtime_refs_exported"] is False
    assert card["output_economy"]["full_payload_drilldown"] == "rerun without --card"
    assert "steps" not in card
    assert "commands" not in card
    assert "evidence_refs" not in card
    assert "public_runtime_refs" not in card


def test_public_reveal_source_modules_are_exact_macro_body_imports() -> None:
    from microcosm_core.release_export import _source_module_private_body_substitution_text

    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == len(manifest["modules"]) == 1
    row = manifest["modules"][0]
    assert row["module_id"] in PUBLIC_REVEAL_SOURCE_MODULE_IDS
    assert row["source_ref"] == "microcosm-substrate/src/microcosm_core/organs/public_reveal_walkthrough.py"
    assert row["path"] == "source_modules/microcosm_core/organs/public_reveal_walkthrough.py"
    assert row["material_class"] == "public_python_source_body"
    assert row["source_import_class"] == "copied_non_secret_macro_body"
    assert row["body_copied"] is True and row["body_in_receipt"] is False
    assert row["body_text_in_receipt"] is False
    target = BUNDLE_INPUT / row["path"]
    expected_digest = "sha256:7a0988e1f361d06ddbba2b548a598bfd37d67bc6748f7255ec1215c5038c2ab9"
    assert _sha256(target) == row["sha256"] == row["source_sha256"] == row["target_sha256"] == expected_digest
    assert row["target_ref"] == "microcosm-substrate/" + target.relative_to(MICROCOSM_ROOT).as_posix()
    body = target.read_bytes()
    assert len(body) == row["byte_count"] == 84152
    assert len(body.splitlines()) == row["line_count"] == 1772
    assert len(row["required_anchors"]) == row["anchor_count"] == 3
    assert row["required_anchors"] == [
        "def run_reveal_bundle", "PUBLIC_SAFE_SOURCE_BODY_CLASSES",
        "synthetic_receipt_standin_allowed",
    ]
    assert all(anchor in body.decode("utf-8") for anchor in row["required_anchors"])

    # The omitted identities describe historical provenance; their public files
    # are stubs and are not counted as copied bodies.
    fixture = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    omissions = manifest["release_substitution_omissions"]
    expected = fixture["public_source_inventory"]["release_substitution_omissions"]
    assert len(omissions) == len(expected) == 4
    assert {item["module_id"] for item in omissions} == PUBLIC_REVEAL_OMITTED_SOURCE_IDS
    for actual, declared in zip(omissions, expected, strict=True):
        assert actual == {key: value for key, value in declared.items() if key != "stub_sha256"}
        source_ref, expected_stub_sha = PUBLIC_REVEAL_OMISSION_REFS[actual["module_id"]]
        assert actual["source_ref"] == source_ref
        assert actual["path"] == "source_modules/ai_workflow/" + source_ref
        assert declared["stub_sha256"] == "sha256:" + expected_stub_sha
        replacement = actual["release_substitution"]
        assert replacement == {"substitution": "public_safe_stub", "matched_private_ref": actual["source_ref"],
                               "contamination_class": "restricted_private_source_ref", "body_in_receipt": False}
        stub = BUNDLE_INPUT / actual["path"]
        assert _sha256(stub) == declared["stub_sha256"]
        assert stub.read_text(encoding="utf-8") == _source_module_private_body_substitution_text(
            rel=actual["path"], match_row=replacement)



@pytest.mark.parametrize("corruption", ["missing_retained", "tampered_retained", "missing_omission", "tampered_stub", "extra_malformed_module"])
def test_public_reveal_rejects_missing_or_changed_release_material(tmp_path: Path, corruption: str) -> None:
    public_root = _copy_public_reveal_root(tmp_path)
    bundle = public_root / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if corruption == "missing_retained":
        (bundle / manifest["modules"][0]["path"]).unlink()
    elif corruption == "tampered_retained":
        with (bundle / manifest["modules"][0]["path"]).open("ab") as stream:
            stream.write(b"\n")
    elif corruption == "missing_omission":
        manifest["release_substitution_omissions"].pop()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    elif corruption == "extra_malformed_module":
        manifest["modules"].append(None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    else:
        (bundle / manifest["release_substitution_omissions"][0]["path"]).write_text("tampered\n", encoding="utf-8")
    result = run_reveal_bundle(bundle, tmp_path / "result", command="pytest")
    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    expected = {
        "missing_retained": "PUBLIC_REVEAL_SOURCE_MODULE_TARGET_MISSING",
        "tampered_retained": "PUBLIC_REVEAL_SOURCE_MODULE_DIGEST_MISMATCH",
        "missing_omission": "PUBLIC_REVEAL_SOURCE_INVENTORY_MISMATCH",
        "tampered_stub": "PUBLIC_REVEAL_SOURCE_INVENTORY_MISMATCH",
        "extra_malformed_module": "PUBLIC_REVEAL_SOURCE_INVENTORY_MISMATCH",
    }[corruption]
    assert expected in result["error_codes"]


def test_public_reveal_fixture_card_honors_acceptance_out(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "fixture-card"
    acceptance_out = tmp_path / "acceptance.json"

    rc = main(
        [
            "run",
            "--input",
            str(FIXTURE_INPUT),
            "--out",
            str(out_dir),
            "--acceptance-out",
            str(acceptance_out),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)

    assert rc == 0
    assert len(captured.encode("utf-8")) < 4000
    assert acceptance_out.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["input_mode"] == "first_wave_fixture"
    assert card["real_lane_witness"] == {
        "current_input_is_exported_bundle_witness": False,
        "witness_action": "run-reveal-bundle",
        "witness_input_ref": "examples/public_reveal_walkthrough/exported_public_reveal_bundle",
        "source_module_manifest_ref": "examples/public_reveal_walkthrough/exported_public_reveal_bundle/source_module_manifest.json",
        "source_body_imports_required_for_witness": True,
        "current_source_body_import_status": "pass",
        "current_body_material_count": 1,
    }
    assert card["negative_case_coverage"]["expected_case_count"] == 4
    assert card["negative_case_coverage"]["observed_case_count"] == 4
    assert card["negative_case_coverage"]["missing_negative_cases"] == []
    assert card["receipt_paths"] == [
        "external_receipt/public_reveal_walkthrough_result.json",
        "external_receipt/ten_minute_reveal_board.json",
        "external_receipt/public_reveal_validation_receipt.json",
        "external_receipt/acceptance.json",
    ]
    _assert_public_safe_receipt_refs(card["receipt_paths"])
    assert card["source_open_body_imports"]["status"] == "pass"
    assert card["source_open_body_imports"]["body_material_count"] == 1
    assert (
        card["source_open_body_imports"]["manifest_ref"]
        == "examples/public_reveal_walkthrough/exported_public_reveal_bundle/source_module_manifest.json"
    )
    assert card["source_open_body_imports"]["evidence_source"] == "real_lane_witness"
    assert card["no_export_guards"]["step_rows_exported"] is False


def test_public_reveal_fixture_manifest_tracks_real_lane_witness_body_floor() -> None:
    fixture_manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    source_manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    source_module_ids = {row["module_id"] for row in source_manifest["modules"]}

    source_open = fixture_manifest["source_open_body_imports"]
    assert source_open["body_material_count"] == source_manifest["module_count"] == 1
    assert fixture_manifest["body_copied_material_count"] == 1
    assert set(source_open["body_material_ids"]) == source_module_ids == PUBLIC_REVEAL_SOURCE_MODULE_IDS
    assert set(source_open["historical_source_identities"]) == PUBLIC_REVEAL_SOURCE_MODULE_IDS | PUBLIC_REVEAL_OMITTED_SOURCE_IDS
    assert {row["module_id"] for row in fixture_manifest["public_source_inventory"]["release_substitution_omissions"]} == PUBLIC_REVEAL_OMITTED_SOURCE_IDS
    assert source_open["body_material_classes"] == {"public_python_source_body": 1}
    assert source_open["material_classes"] == ["public_python_source_body"]
    assert fixture_manifest["real_lane_witness"] == {
        "status": "required",
        "witness_action": "run-reveal-bundle",
        "witness_input_ref": "examples/public_reveal_walkthrough/exported_public_reveal_bundle",
        "source_body_imports_required_for_witness": True,
        "current_body_material_count": 1,
        "tamper_rejection_error_code": "PUBLIC_REVEAL_REAL_LANE_WITNESS_BLOCKED",
    }
    assert "real_lane_witness" in fixture_manifest["receipt_field_floor"]


def test_public_reveal_standard_and_registry_rank_match_real_lane_witness_ceiling() -> None:
    standard = json.loads(STANDARD.read_text(encoding="utf-8"))
    registry = json.loads(ORGAN_REGISTRY.read_text(encoding="utf-8"))
    acceptance = json.loads(
        (MICROCOSM_ROOT / "core/acceptance/first_wave_acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    evidence_classes = json.loads(ORGAN_EVIDENCE_CLASSES.read_text(encoding="utf-8"))

    registry_row = next(
        row
        for row in registry["implemented_organs"]
        if row["organ_id"] == "public_reveal_walkthrough"
    )
    acceptance_row = next(
        row
        for row in acceptance["accepted_current_authority_organs"]
        if row["organ_id"] == "public_reveal_walkthrough"
    )
    evidence_row = next(
        row
        for row in evidence_classes["organ_evidence_classes"]
        if row["organ_id"] == "public_reveal_walkthrough"
    )
    projection_basis = standard["standard_payload"]["contract_projection_basis"]

    assert registry_row["evidence_class"] == "bounded_runtime_computation"
    assert registry_row["evidence_strength_rank"] == 4
    assert registry_row["truth_accounting_bucket"] == "real_runtime_receipt"
    assert "run-reveal-bundle" in registry_row["validator_command"]
    assert "examples/public_reveal_walkthrough/exported_public_reveal_bundle" in registry_row["validator_command"]
    assert "fixtures/first_wave/public_reveal_walkthrough/input" not in registry_row["validator_command"]
    assert (
        "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough/exported_public_reveal_bundle_validation_result.json"
        in registry_row["generated_receipts"]
    )
    assert acceptance_row["validator_command"] == registry_row["validator_command"]
    assert acceptance_row["generated_receipts"] == registry_row["generated_receipts"]
    assert evidence_row["evidence_class"] == registry_row["evidence_class"]
    assert projection_basis["organ_evidence_class"] == registry_row["evidence_class"]
    assert projection_basis["organ_evidence_strength_rank"] == registry_row["evidence_strength_rank"]
    assert projection_basis["truth_accounting_bucket"] == registry_row["truth_accounting_bucket"]
    assert (
        "release" in registry_row["claim_ceiling"]
        and "whole-system correctness" in registry_row["claim_ceiling"]
    )
