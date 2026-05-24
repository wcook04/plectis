from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core import cli
from microcosm_core.macro_tools.finance_eval_spine import (
    BUNDLE_RESULT_NAME,
    REQUIRED_MODULES,
    SOURCE_OPEN_BODY_POLICY,
    validate_finance_eval_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FINANCE_EVAL_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle"
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


def test_finance_eval_spine_accepts_copied_real_macro_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "receipts"

    result = validate_finance_eval_bundle(FINANCE_EVAL_BUNDLE, out_dir, command="pytest")

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_finance_eval_bundle"
    assert result["source_import_class"] == "copied_non_secret_macro_body"
    assert result["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert result["copied_macro_source_count"] == len(REQUIRED_MODULES)
    assert result["real_macro_receipt_count"] == 1
    assert result["counts_as_real_substrate_progress"] is True
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["body_in_receipt"] is False
    assert result["unsafe_payload_bodies_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["source_manifest"]["all_expected_digests_matched"] is True
    assert result["source_manifest"]["all_expected_line_counts_matched"] is True
    assert result["anchor_summary"]["missing_anchor_count"] == 0
    assert result["contract_summary"]["authority_overclaim_count"] == 0
    assert result["operating_picture_gate_summary"]["comparison_key_authority"] == (
        "tools/finance/event_keys.py"
    )
    assert all(
        row["observed"] is False
        for row in result["operating_picture_gate_summary"]["false_gate_rows"]
    )
    assert result["authority_ceiling"]["financial_advice_authorized"] is False
    assert result["authority_ceiling"]["optimizer_mutation_authorized"] is False
    assert result["authority_ceiling"]["calculator_weight_mutation_authorized"] is False
    assert result["error_codes"] == []
    assert len(result["public_runtime_refs"]) == len(REQUIRED_MODULES) + 3

    receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))
    assert receipt["status"] == "pass"
    assert receipt["body_in_receipt"] is False
    assert "body" not in _walk_keys(receipt)
    encoded = json.dumps(receipt, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement" not in encoded
    assert "metadata_only" not in encoded


def test_finance_eval_spine_rejects_finance_authority_overclaim(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    contract_path = bundle / "finance_eval_runtime_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["authority_ceiling"]["financial_advice_authorized"] = True
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "AUTHORITY_CEILING_OVERCLAIM" in result["error_codes"]
    assert result["authority_ceiling"]["financial_advice_authorized"] is True
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False


def test_cli_finance_eval_spine_smoke(
    tmp_path: Path, capsys
) -> None:
    out_dir = tmp_path / "receipts"

    status = cli.main(
        [
            "finance-eval-spine",
            "validate-finance-eval-bundle",
            "--input",
            str(FINANCE_EVAL_BUNDLE),
            "--out",
            str(out_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["status"] == "pass"
    assert payload["command"].startswith("microcosm finance-eval-spine")
    assert payload["copied_macro_source_count"] == len(REQUIRED_MODULES)
    assert (out_dir / BUNDLE_RESULT_NAME).is_file()
