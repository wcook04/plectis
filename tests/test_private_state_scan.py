from __future__ import annotations

from pathlib import Path

from microcosm_core.private_state_scan import (
    BLOCKED_PRIVATE,
    BLOCKED_PUBLIC_WRITE,
    PASS,
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
