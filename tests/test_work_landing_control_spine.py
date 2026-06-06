from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.macro_tools.work_landing_control_spine as work_landing_control_spine
from microcosm_core import cli
from microcosm_core.macro_tools.work_landing_control_spine import (
    BUNDLE_RESULT_NAME,
    REQUIRED_SOURCE_REFS,
    SOURCE_OPEN_BODY_POLICY,
    validate_work_landing_control_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
WORK_LANDING_CONTROL_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/work_landing_control_spine/exported_work_landing_control_bundle"
)
MUTATED_SOURCE_PATH = "source_modules/tools/meta/control/work_landing.py"


def _walk_keys(payload: object) -> list[str]:
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


def _copy_work_landing_control_bundle(tmp_path: Path, name: str) -> Path:
    bundle = tmp_path / name / "bundle"
    shutil.copytree(WORK_LANDING_CONTROL_BUNDLE, bundle)
    return bundle


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _bundle_manifest_row(payload: dict[str, Any], path: str) -> dict[str, Any]:
    return next(row for row in payload["files"] if row["path"] == path)


def test_work_landing_line_count_streams_without_materializing_file(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    empty_source = tmp_path / "empty_source.py"
    missing_source = tmp_path / "missing_source.py"
    source.write_text("one\n\ntwo", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    guarded_paths = {source, empty_source}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert work_landing_control_spine._line_count(source) == 3
    assert work_landing_control_spine._line_count(empty_source) == 1
    assert work_landing_control_spine._line_count(missing_source) is None


def test_work_landing_control_spine_accepts_copied_macro_sources(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "receipts"

    result = validate_work_landing_control_bundle(
        WORK_LANDING_CONTROL_BUNDLE,
        out_dir,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_work_landing_control_bundle"
    assert result["source_import_class"] == "copied_non_secret_macro_body"
    assert result["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert result["copied_macro_source_count"] == len(REQUIRED_SOURCE_REFS)
    assert result["counts_as_real_substrate_progress"] is True
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["body_in_receipt"] is False
    assert result["unsafe_payload_bodies_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["source_manifest"]["all_expected_digests_matched"] is True
    assert result["source_manifest"]["all_expected_line_counts_matched"] is True
    source_manifest = json.loads(
        (WORK_LANDING_CONTROL_BUNDLE / "source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    source_rows = {row["source_ref"]: row for row in source_manifest["modules"]}
    assert set(source_rows) == set(REQUIRED_SOURCE_REFS)
    for source_ref, row in source_rows.items():
        assert row["source_to_target_relation"] == "exact_copy"
        assert row["target_ref"].startswith(
            "microcosm-substrate/examples/work_landing_control_spine/"
        )
        source_path = MICROCOSM_ROOT.parent / source_ref
        target_path = MICROCOSM_ROOT.parent / row["target_ref"]
        assert source_path.read_bytes() == target_path.read_bytes()
        digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
    assert result["anchor_summary"]["missing_anchor_count"] == 0
    assert result["contract_summary"]["authority_overclaim_count"] == 0
    assert result["authority_ceiling"]["live_git_mutation_authorized"] is False
    assert result["authority_ceiling"]["private_index_commit_execution_authorized"] is False
    assert result["blocked_overclaim_workitem_ref"] == (
        "cap_quick_microcosm_work_landing_body_import_overc_eba9812296f8"
    )
    assert result["error_codes"] == []
    assert len(result["public_runtime_refs"]) == len(REQUIRED_SOURCE_REFS) + 2

    receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))
    assert receipt["status"] == "pass"
    assert receipt["body_in_receipt"] is False
    assert "body" not in _walk_keys(receipt)
    encoded = json.dumps(receipt, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement" not in encoded
    assert "metadata_only" not in encoded


def test_work_landing_control_spine_rejects_manifest_and_contract_drift(
    tmp_path: Path,
) -> None:
    def run_mutated(name: str, mutate: Any) -> dict[str, Any]:
        bundle = _copy_work_landing_control_bundle(tmp_path, name)
        mutate(bundle)
        return validate_work_landing_control_bundle(
            bundle,
            tmp_path / name / "receipts",
            command="pytest",
        )

    def mutate_digest(bundle: Path) -> None:
        manifest_path = bundle / "bundle_manifest.json"
        manifest = _read_json(manifest_path)
        _bundle_manifest_row(manifest, MUTATED_SOURCE_PATH)["expected_sha256"] = "0" * 64
        _write_json(manifest_path, manifest)

    def mutate_material_class(bundle: Path) -> None:
        manifest_path = bundle / "bundle_manifest.json"
        manifest = _read_json(manifest_path)
        _bundle_manifest_row(manifest, MUTATED_SOURCE_PATH)[
            "material_class"
        ] = "private_macro_tool_body"
        _write_json(manifest_path, manifest)

    def mutate_import_class(bundle: Path) -> None:
        manifest_path = bundle / "bundle_manifest.json"
        manifest = _read_json(manifest_path)
        _bundle_manifest_row(manifest, MUTATED_SOURCE_PATH)[
            "source_import_class"
        ] = "metadata_only_not_source_open"
        _write_json(manifest_path, manifest)

    def mutate_contract_classification(bundle: Path) -> None:
        contract_path = bundle / "work_landing_control_runtime_contract.json"
        contract = _read_json(contract_path)
        contract["required_classifications"] = [
            value
            for value in contract["required_classifications"]
            if value != "secret_exclusion"
        ]
        _write_json(contract_path, contract)

    digest_result = run_mutated("digest", mutate_digest)
    material_result = run_mutated("material_class", mutate_material_class)
    import_result = run_mutated("import_class", mutate_import_class)
    classification_result = run_mutated(
        "contract_classification",
        mutate_contract_classification,
    )

    assert digest_result["status"] == "blocked"
    assert "SOURCE_DIGEST_MISMATCH" in digest_result["error_codes"]
    assert MUTATED_SOURCE_PATH in digest_result["source_manifest"]["digest_mismatch_paths"]

    assert material_result["status"] == "blocked"
    assert "MATERIAL_CLASS_NOT_ALLOWED" in material_result["error_codes"]
    assert (
        MUTATED_SOURCE_PATH
        in material_result["source_manifest"]["material_class_violations"]
    )

    assert import_result["status"] == "blocked"
    assert "SOURCE_IMPORT_CLASS_MISMATCH" in import_result["error_codes"]
    assert (
        MUTATED_SOURCE_PATH
        in import_result["source_manifest"]["source_import_class_violations"]
    )

    assert classification_result["status"] == "blocked"
    assert "CLASSIFICATION_FLOOR_MISSING" in classification_result["error_codes"]
    assert "secret_exclusion" in classification_result["contract_summary"][
        "missing_required_classifications"
    ]


def test_work_landing_control_spine_rejects_live_mutation_overclaim(
    tmp_path: Path,
) -> None:
    bundle = _copy_work_landing_control_bundle(tmp_path, "authority_overclaim")
    contract_path = bundle / "work_landing_control_runtime_contract.json"
    contract = _read_json(contract_path)
    contract["authority_ceiling"]["live_git_mutation_authorized"] = True
    _write_json(contract_path, contract)

    result = validate_work_landing_control_bundle(
        bundle,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "AUTHORITY_CEILING_OVERCLAIM" in result["error_codes"]
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False


def test_cli_work_landing_control_spine_smoke(
    tmp_path: Path,
    capsys,
) -> None:
    out_dir = tmp_path / "receipts"

    status = cli.main(
        [
            "work-landing-control-spine",
            "validate-control-bundle",
            "--input",
            str(WORK_LANDING_CONTROL_BUNDLE),
            "--out",
            str(out_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["status"] == "pass"
    assert payload["command"].startswith("microcosm work-landing-control-spine")
    assert payload["copied_macro_source_count"] == len(REQUIRED_SOURCE_REFS)
    assert (out_dir / BUNDLE_RESULT_NAME).is_file()
