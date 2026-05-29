from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

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


def test_work_landing_control_spine_rejects_live_mutation_overclaim(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(WORK_LANDING_CONTROL_BUNDLE, bundle)
    contract_path = bundle / "work_landing_control_runtime_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["authority_ceiling"]["live_git_mutation_authorized"] = True
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

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
