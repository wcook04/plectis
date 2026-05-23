from __future__ import annotations

from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    BLOCKED_SECRET_EXCLUSION,
    PASS,
    classify_public_safe_macro_import,
    load_forbidden_classes,
    scan_paths,
    scan_text,
)
from microcosm_core.validators.secret_exclusion_scan import validate_scan


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = MICROCOSM_ROOT / "core/private_state_forbidden_classes.json"


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


def test_secret_exclusion_scan_is_receipt_owner_not_redaction_contract(
    tmp_path: Path,
) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixture = tmp_path / "body.txt"
    fixture.write_text("SYNTHETIC_RAW_SEED_BODY_SENTINEL", encoding="utf-8")

    result = scan_paths([fixture], forbidden_classes=policy)

    assert result["status"] == BLOCKED_SECRET_EXCLUSION
    assert result["hits"][0]["term_id"] == "raw_seed_body_sentinel"
    assert result["body_in_receipt"] is False
    assert result["real_substrate_default"] is True
    assert "body_redacted" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)


def test_secret_exclusion_expected_negative_fixture_does_not_block() -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    text = '{"expected_negative_case": true, "body": "SYNTHETIC_RAW_SEED_BODY_SENTINEL"}'

    result = scan_text(
        text,
        path="fixtures/first_wave/pattern_binding_contract/input/example.json",
        forbidden_classes=policy,
    )

    assert result["status"] == PASS
    assert result["hits"][0]["expected_negative_case"] is True
    assert result["hits"][0]["body_in_receipt"] is False
    assert "body_redacted" not in _walk_keys(result)


def test_secret_exclusion_macro_import_defaults_to_real_substrate() -> None:
    policy = load_forbidden_classes(POLICY_PATH)

    result = classify_public_safe_macro_import(
        {
            "material_class": "public_macro_proof_body",
            "credential_exposure_risk": "low",
            "public_safe_mode": "verified_public_macro_proof_body_exact_copy",
            "source_refs": [
                "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/"
                "CertificateKernel.lean"
            ],
            "provenance_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
            "validation_refs": ["microcosm-substrate/tests/test_secret_exclusion_scan.py"],
            "claim_ceiling": "proof body import only",
            "body_import_verification": {
                "verification_status": "verified",
                "verification_mode": "exact_source_digest_match",
            },
        },
        forbidden_classes=policy,
    )

    assert result["status"] == PASS
    assert result["route"] == "verified_light_edit"
    assert result["real_substrate_default"] is True
    assert result["synthetic_receipt_policy"] == "not_a_substitute_for_available_real_substrate"
    assert result["body_in_receipt"] is False
    assert "body_redacted" not in _walk_keys(result)


def test_secret_exclusion_validator_emits_new_receipt_contract(tmp_path: Path) -> None:
    root = tmp_path / "microcosm-substrate"
    (root / "core").mkdir(parents=True)
    (root / "core/private_state_forbidden_classes.json").write_text(
        POLICY_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "README.md").write_text("real substrate only\n", encoding="utf-8")

    receipt = validate_scan(root)

    assert receipt["status"] == PASS
    assert receipt["organ_id"] == "secret_exclusion_scan"
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["receipt_paths"] == ["receipts/first_wave/secret_exclusion_scan.json"]
    assert "private_state_scan" not in receipt
    assert "body_redacted" not in _walk_keys(receipt)
