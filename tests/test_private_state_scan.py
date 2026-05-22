from __future__ import annotations

from pathlib import Path

from microcosm_core.private_state_scan import (
    BLOCKED_PRIVATE,
    BLOCKED_PUBLIC_WRITE,
    PASS,
    classify_public_safe_macro_import,
    load_forbidden_classes,
    scan_paths,
    scan_text,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = MICROCOSM_ROOT / "core/private_state_forbidden_classes.json"


def test_scanner_blocks_synthetic_forbidden_token_without_excerpt(tmp_path: Path) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixture = tmp_path / "body.txt"
    fixture.write_text("SYNTHETIC_RAW_SEED_BODY_SENTINEL", encoding="utf-8")

    result = scan_paths([fixture], forbidden_classes=policy)

    assert result["status"] == BLOCKED_PRIVATE
    assert result["hits"][0]["term_id"] == "raw_seed_body_sentinel"
    assert "matched_excerpt" not in result["hits"][0]
    assert result["hits"][0]["body_redacted"] is True


def test_public_root_scan_paths_are_public_relative() -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixture = (
        MICROCOSM_ROOT
        / "fixtures/first_wave/pattern_binding_contract/input/private_state_forbidden_terms.json"
    )

    result = scan_paths([fixture.resolve()], forbidden_classes=policy)

    assert result["status"] == PASS
    assert result["hits"]
    for hit in result["hits"]:
        assert hit["path"] == "fixtures/first_wave/pattern_binding_contract/input/private_state_forbidden_terms.json"
        assert not Path(hit["path"]).is_absolute()
        assert "/Users/" not in hit["path"]
        assert "src/ai_workflow" not in hit["path"]
        assert hit["body_redacted"] is True
        assert "matched_excerpt" not in hit
        assert "body" not in hit


def test_expected_negative_fixture_does_not_block_root_scan() -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    text = '{"expected_negative_case": true, "body": "SYNTHETIC_RAW_SEED_BODY_SENTINEL"}'

    result = scan_text(
        text,
        path="fixtures/first_wave/pattern_binding_contract/input/example.json",
        forbidden_classes=policy,
    )

    assert result["status"] == PASS
    assert result["hits"][0]["expected_negative_case"] is True


def test_public_root_is_allowed_as_target_and_blocked_as_source() -> None:
    policy = load_forbidden_classes(POLICY_PATH)

    target = scan_text("", path="microcosm-substrate/README.md", forbidden_classes=policy)
    source = scan_text(
        "",
        path="microcosm-substrate/README.md",
        forbidden_classes=policy,
        source_context="source_authority",
    )

    assert target["status"] == PASS
    assert source["status"] == BLOCKED_PUBLIC_WRITE
    assert source["hits"][0]["forbidden_class"] == "target_only_not_source"


def test_public_safe_macro_import_allows_verified_tool_and_proof_bodies() -> None:
    policy = load_forbidden_classes(POLICY_PATH)

    tool = classify_public_safe_macro_import(
        {
            "material_class": "public_macro_tool_body",
            "private_state_risk": "low",
            "public_safe_mode": "verified_public_macro_body_light_edit",
            "source_refs": ["tools/meta/control/work_landing.py"],
            "provenance_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
            "validation_refs": ["microcosm-substrate/tests/test_private_state_scan.py"],
            "claim_ceiling": "algorithmic body import only",
            "body_import_verification": {
                "verification_status": "verified",
                "verification_mode": "verified_light_edit_recipe",
            },
        },
        forbidden_classes=policy,
    )
    proof = classify_public_safe_macro_import(
        {
            "material_class": "public_macro_proof_body",
            "private_state_risk": "low",
            "public_safe_mode": "verified_public_macro_proof_body_exact_copy",
            "source_refs": [
                "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/CertificateKernel.lean"
            ],
            "provenance_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
            "validation_refs": ["microcosm-substrate/tests/test_private_state_scan.py"],
            "claim_ceiling": "proof body import only",
            "body_import_verification": {
                "verification_status": "verified",
                "verification_mode": "exact_source_digest_match",
            },
        },
        forbidden_classes=policy,
    )

    assert tool["status"] == PASS
    assert tool["route"] == "verified_light_edit"
    assert proof["status"] == PASS
    assert proof["route"] == "verified_light_edit"


def test_verified_macro_import_still_blocks_credential_bound_classes() -> None:
    policy = load_forbidden_classes(POLICY_PATH)

    result = classify_public_safe_macro_import(
        {
            "material_class": "raw_seed_body",
            "private_state_risk": "none",
            "public_safe_mode": "direct_verified_macro_body",
            "source_refs": ["raw_seed.md"],
            "provenance_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
            "validation_refs": ["microcosm-substrate/tests/test_private_state_scan.py"],
            "claim_ceiling": "not allowed",
            "body_import_verification": {
                "verification_status": "verified",
                "verification_mode": "exact_source_digest_match",
            },
        },
        forbidden_classes=policy,
    )

    assert result["status"] == BLOCKED_PRIVATE
    assert result["findings"][0]["error_code"] == "PUBLIC_SAFE_IMPORT_TRUE_FORBIDDEN_CLASS"
