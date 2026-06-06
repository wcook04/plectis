from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    BLOCKED_SECRET_EXCLUSION,
    PASS,
    classify_public_safe_macro_import,
    is_text_scan_candidate,
    load_forbidden_classes,
    public_relative_path,
    scan_json_payload,
    scan_paths,
    scan_text,
)
from microcosm_core.validators.secret_exclusion_scan import _iter_scan_paths, validate_scan


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = MICROCOSM_ROOT / "core/private_state_forbidden_classes.json"
AUTHORITY_TRUE_FIELD_NAMES = (
    "release_authorized",
    "provider_calls_authorized",
    "source_mutation_authorized",
    "whole_system_correctness_claim",
    "proof_correctness_claim",
    "publication_authorized",
    "hosted_public_authorized",
    "credential_equivalent_payloads_exported",
    "provider_payload_bodies_exported",
    "unsafe_payload_bodies_in_receipt",
)
PUBLIC_SCAN_TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PUBLIC_SCAN_SKIPPED_PARTS = {
    ".microcosm",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
}


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


def _public_text_scan_candidate(path: Path) -> bool:
    if not path.is_file() or path.suffix not in PUBLIC_SCAN_TEXT_SUFFIXES:
        return False
    relative = path.relative_to(MICROCOSM_ROOT)
    if relative.parts[:2] == ("fixtures", "first_wave"):
        return False
    return not any(part in PUBLIC_SCAN_SKIPPED_PARTS for part in relative.parts)


def _iter_public_text_scan_candidates() -> list[Path]:
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(MICROCOSM_ROOT):
        current = Path(dirpath)
        relative = current.relative_to(MICROCOSM_ROOT)
        if relative.parts[:2] == ("fixtures", "first_wave"):
            dirnames[:] = []
            continue
        dirnames[:] = sorted(
            dirname for dirname in dirnames if dirname not in PUBLIC_SCAN_SKIPPED_PARTS
        )
        for filename in sorted(filenames):
            path = current / filename
            if _public_text_scan_candidate(path):
                paths.append(path)
    return paths


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


def test_public_surfaces_do_not_emit_true_authority_fields_outside_negative_fixtures() -> None:
    field_pattern = re.compile(
        r'"('
        + "|".join(re.escape(field) for field in AUTHORITY_TRUE_FIELD_NAMES)
        + r')"\s*:\s*true'
    )

    violations: list[str] = []
    for path in _iter_public_text_scan_candidates():
        relative = path.relative_to(MICROCOSM_ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = field_pattern.search(line)
            if match:
                violations.append(f"{relative}:{line_number}:{match.group(1)}")

    assert violations == []


def test_committed_receipts_do_not_carry_host_absolute_paths() -> None:
    forbidden_markers = ("/private/tmp", "/Users/", "src/ai_workflow")
    violations: list[str] = []
    receipts_root = MICROCOSM_ROOT / "receipts"

    for path in sorted(receipts_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".json", ".jsonl"}:
            continue
        relative = path.relative_to(MICROCOSM_ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for marker in forbidden_markers:
                if marker in line:
                    violations.append(f"{relative}:{line_number}:{marker}")

    assert violations == []


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


def test_secret_exclusion_json_payload_blocks_receipt_body_fields() -> None:
    policy = load_forbidden_classes(POLICY_PATH)

    result = scan_json_payload(
        {
            "receipt_id": "example_receipt",
            "payload": {
                "body": "public macro body belongs in source modules, not receipts",
                "matched_excerpt": "raw excerpts stay out of receipt metadata",
                "body_in_receipt": False,
            },
        },
        path="receipts/first_wave/example_receipt.json",
        forbidden_classes=policy,
    )

    assert result["status"] == BLOCKED_SECRET_EXCLUSION
    assert result["receipt_payload_field_guard"]["status"] == BLOCKED_SECRET_EXCLUSION
    assert result["receipt_payload_field_guard"]["blocking_field_count"] == 2
    assert result["blocking_hit_count"] == 2
    assert {hit["term_id"] for hit in result["hits"]} == {
        "receipt_payload_field:body",
        "receipt_payload_field:matched_excerpt",
    }
    assert {hit["field_path"] for hit in result["hits"]} == {
        "payload.body",
        "payload.matched_excerpt",
    }
    assert all(hit["body_in_receipt"] is False for hit in result["hits"])
    assert "body" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)


def test_secret_exclusion_json_payload_allows_expected_negative_body_fields() -> None:
    policy = load_forbidden_classes(POLICY_PATH)

    result = scan_json_payload(
        {
            "expected_negative_case": True,
            "body": "expected negative fixture body marker",
        },
        path="fixtures/first_wave/example/input/body_field_negative.json",
        forbidden_classes=policy,
    )

    assert result["status"] == PASS
    assert result["receipt_payload_field_guard"]["forbidden_field_count"] == 1
    assert result["receipt_payload_field_guard"]["blocking_field_count"] == 0
    assert result["hits"][0]["expected_negative_case"] is True
    assert result["hits"][0]["body_in_receipt"] is False
    assert "body" not in _walk_keys(result)


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


def test_secret_exclusion_validator_skips_local_runtime_residue(tmp_path: Path) -> None:
    root = tmp_path / "microcosm-substrate"
    (root / "core").mkdir(parents=True)
    (root / "core/private_state_forbidden_classes.json").write_text(
        POLICY_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "README.md").write_text("real substrate only\n", encoding="utf-8")
    for residue_path in (
        ".DS_Store",
        ".microcosm/project_manifest.json",
        ".pytest_cache/README.md",
        ".venv/pyvenv.cfg",
        "build/lib.txt",
        "dist/microcosm.whl",
        "microcosm-substrate/.microcosm/events.jsonl",
        "node_modules/package/index.js",
        "src/microcosm_substrate.egg-info/PKG-INFO",
    ):
        path = root / residue_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("SYNTHETIC_RAW_SEED_BODY_SENTINEL\n", encoding="utf-8")

    receipt = validate_scan(root)

    assert receipt["status"] == PASS
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0

    (root / "public_sentinel.txt").write_text(
        "SYNTHETIC_RAW_SEED_BODY_SENTINEL\n",
        encoding="utf-8",
    )

    blocked = validate_scan(root)

    assert blocked["status"] == BLOCKED_SECRET_EXCLUSION
    assert blocked["secret_exclusion_scan"]["blocking_hit_count"] == 1
    assert blocked["secret_exclusion_scan"]["hits"][0]["path"] == "public_sentinel.txt"


def test_secret_exclusion_validator_collects_scannable_text_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "microcosm-substrate"
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("scan me\n", encoding="utf-8")
    (root / "src/module.py").write_text("print('scan me')\n", encoding="utf-8")
    (root / "image.bin").write_bytes(b"SYNTHETIC_RAW_SEED_BODY_SENTINEL\n")
    (root / "Makefile").write_text("SYNTHETIC_RAW_SEED_BODY_SENTINEL\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "SYNTHETIC_RAW_SEED_BODY_SENTINEL\n",
        encoding="utf-8",
    )
    (root / "node_modules/pkg").mkdir(parents=True)
    (root / "node_modules/pkg/index.txt").write_text(
        "SYNTHETIC_RAW_SEED_BODY_SENTINEL\n",
        encoding="utf-8",
    )

    iterator = _iter_scan_paths(root)

    assert not isinstance(iterator, list)

    paths = {path.relative_to(root).as_posix() for path in iterator}

    assert paths == {"Makefile", "README.md", "src/module.py"}


def test_secret_exclusion_scan_paths_catches_extensionless_public_text(
    tmp_path: Path,
) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    makefile = tmp_path / "Makefile"
    makefile.write_text("SYNTHETIC_RAW_SEED_BODY_SENTINEL\n", encoding="utf-8")

    result = scan_paths([makefile], forbidden_classes=policy)

    assert is_text_scan_candidate(makefile)
    assert result["status"] == BLOCKED_SECRET_EXCLUSION
    assert result["scanned_path_count"] == 1
    assert result["hits"][0]["path"] == public_relative_path(makefile)
    assert "/Users/" not in result["hits"][0]["path"]
    assert "/home/" not in result["hits"][0]["path"]
