from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

from microcosm_core.organs.pattern_binding_contract import validate as validate_pattern_binding
from microcosm_core.receipts import base_receipt, write_receipt
from microcosm_core.validators.secret_exclusion_scan import validate_scan as validate_secret_exclusion_scan


REQUIRED_INPUTS = [
    "fixtures/first_wave/pattern_binding_contract/input/patterns.jsonl",
    "fixtures/first_wave/pattern_binding_contract/input/source_capsules.json",
    "fixtures/first_wave/pattern_binding_contract/input/private_state_forbidden_terms.json",
    "fixtures/first_wave/pattern_binding_contract/input/authority_chain_handles.json",
]

PATTERN_RECEIPTS = [
    "receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json",
    "receipts/first_wave/pattern_binding_contract/source_capsules.json",
    "receipts/first_wave/pattern_binding_contract/omission_receipt.json",
    "receipts/first_wave/pattern_binding_contract/reference_capsule_resolver_receipt.json",
    "receipts/first_wave/pattern_binding_contract/authority_chain_handle_resolver_receipt.json",
]


def run_probe(root: str | Path, suite: str = "first-wave") -> dict[str, Any]:
    root_path = Path(root)
    receipt = base_receipt("cold_clone_probe", suite, command=f"./bootstrap.sh --suite {suite}")
    missing_inputs = [path for path in REQUIRED_INPUTS if not (root_path / path).is_file()]
    if missing_inputs:
        receipt.update(
            {
                "status": "blocked_dependency_missing",
                "blocked_dependency_codes": ["MISSING_FIXTURE_INPUT"],
                "missing_inputs": missing_inputs,
            }
        )
        return receipt
    try:
        scan_receipt = validate_secret_exclusion_scan(root_path)
    except Exception as exc:
        receipt.update(
            {
                "status": "blocked_command_unavailable",
                "blocked_dependency_codes": ["COMMAND_UNAVAILABLE"],
                "error": str(exc),
            }
        )
        return receipt
    if scan_receipt["status"] != "pass":
        secret_scan = scan_receipt.get("secret_exclusion_scan", {"status": scan_receipt["status"]})
        receipt.update(
            {
                "status": "blocked_secret_exclusion",
                "blocked_dependency_codes": ["SECRET_EXCLUSION_SCAN_BLOCKED"],
                "secret_exclusion_scan": secret_scan,
                "private_state_scan": {
                    "compatibility_alias_for": "secret_exclusion_scan",
                    **secret_scan,
                },
            }
        )
        return receipt

    with tempfile.TemporaryDirectory(prefix="microcosm-cold-clone-pattern-") as tmp_dir:
        pattern_result = validate_pattern_binding(
            root_path / "fixtures/first_wave/pattern_binding_contract/input",
            Path(tmp_dir) / "pattern_binding_contract",
            command="bootstrap pattern_binding_contract validate",
        )
    missing_receipts = [path for path in PATTERN_RECEIPTS if not (root_path / path).is_file()]
    if pattern_result["status"] != "pass" or missing_receipts:
        receipt.update(
            {
                "status": "blocked_dependency_missing",
                "blocked_dependency_codes": ["MISSING_PATTERN_BINDING_RECEIPT"],
                "missing_receipts": missing_receipts,
                "pattern_binding_status": pattern_result["status"],
            }
        )
        return receipt

    receipt.update(
        {
            "status": "pass",
            "secret_exclusion_scan": scan_receipt["secret_exclusion_scan"],
            "private_state_scan": {
                "compatibility_alias_for": "secret_exclusion_scan",
                **scan_receipt["secret_exclusion_scan"],
            },
            "first_wave_receipts_observed": PATTERN_RECEIPTS,
            "receipt_paths": ["receipts/cold_clone_probe.json", *PATTERN_RECEIPTS],
        }
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="first-wave")
    parser.add_argument("--emit", required=True)
    args = parser.parse_args(argv)
    receipt = run_probe(Path.cwd(), suite=args.suite)
    write_receipt(args.emit, receipt)
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
