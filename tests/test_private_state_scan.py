from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from microcosm_core import private_state_scan
from microcosm_core.validators import private_state_scan as private_state_scan_validator
from microcosm_core.private_state_scan import (
    BLOCKED_PRIVATE,
    BLOCKED_PUBLIC_WRITE,
    PASS,
    classify_public_safe_macro_import,
    load_forbidden_classes,
    scan_paths,
    scan_text,
)
from microcosm_core.validators.private_state_scan import (
    validate_scan as validate_private_state_scan,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = MICROCOSM_ROOT / "core/private_state_forbidden_classes.json"


def test_scanner_blocks_synthetic_forbidden_token_without_excerpt(tmp_path: Path) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixture = tmp_path / "body.txt"
    fixture.write_text("SYNTHETIC_RAW_SEED_BODY_SENTINEL", encoding="utf-8")

    result = scan_paths([fixture], forbidden_classes=policy)

    assert result["status"] == BLOCKED_PRIVATE
    assert result["scan_scope"]["not_a_complete_secret_scan"] is True
    assert result["scan_scope"]["body_text_exported_in_findings"] is False
    assert "complete secret scan" in result["anti_claim"]
    assert result["hits"][0]["term_id"] == "raw_seed_body_sentinel"
    assert "matched_excerpt" not in result["hits"][0]
    assert result["hits"][0]["body_redacted"] is True


def test_scan_paths_reuses_forbidden_terms_across_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixtures = []
    for index in range(3):
        fixture = tmp_path / f"clean_{index}.txt"
        fixture.write_text(f"public body {index}\n", encoding="utf-8")
        fixtures.append(fixture)

    calls = 0
    original_terms = private_state_scan._terms

    def counted_terms(forbidden_classes):
        nonlocal calls
        calls += 1
        return original_terms(forbidden_classes)

    monkeypatch.setattr(private_state_scan, "_terms", counted_terms)

    result = scan_paths(fixtures, forbidden_classes=policy)

    assert result["status"] == PASS
    assert result["scanned_path_count"] == 3
    assert calls == 1


def test_scan_paths_streams_file_without_materializing_text(
    monkeypatch,
    tmp_path: Path,
) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixture = tmp_path / "streamed.txt"
    fixture.write_text("prefix SYNTHETIC_RAW_SEED_BODY_SENTINEL suffix", encoding="utf-8")
    monkeypatch.setattr(private_state_scan, "SCAN_CHUNK_SIZE", 7)

    with patch.object(
        Path,
        "read_text",
        side_effect=AssertionError("scan_paths must not materialize file text"),
    ):
        result = scan_paths([fixture], forbidden_classes=policy)

    assert result["status"] == BLOCKED_PRIVATE
    assert result["scanned_path_count"] == 1
    assert result["hits"][0]["term_id"] == "raw_seed_body_sentinel"
    assert "matched_excerpt" not in result["hits"][0]


def test_scan_paths_reuses_inferred_display_root_across_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    public_root = tmp_path / "microcosm-substrate"
    public_root.mkdir()
    fixtures = []
    for index in range(3):
        fixture = public_root / f"clean_{index}.txt"
        fixture.write_text(f"public body {index}\n", encoding="utf-8")
        fixtures.append(fixture.resolve())

    calls = 0
    original_public_root_for_path = private_state_scan._public_root_for_path

    def counted_public_root_for_path(path):
        nonlocal calls
        calls += 1
        return original_public_root_for_path(path)

    monkeypatch.setattr(
        private_state_scan,
        "_public_root_for_path",
        counted_public_root_for_path,
    )

    result = scan_paths(fixtures, forbidden_classes=policy)

    assert result["status"] == PASS
    assert result["scanned_path_count"] == 3
    assert calls == 1


def test_scan_paths_streams_generator_when_display_root_is_known(
    monkeypatch,
    tmp_path: Path,
) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    public_root = tmp_path / "microcosm-substrate"
    public_root.mkdir()
    first = public_root / "first.txt"
    second = public_root / "second.txt"
    first.write_text("public body first\n", encoding="utf-8")
    second.write_text("public body second\n", encoding="utf-8")
    first_scanned = False
    original_scan_path_with_terms = private_state_scan._scan_path_with_terms

    def counted_scan_path_with_terms(path, *args, **kwargs):
        nonlocal first_scanned
        result = original_scan_path_with_terms(path, *args, **kwargs)
        if path == first:
            first_scanned = True
        return result

    def fail_infer_display_root(paths):
        raise AssertionError("display_root should bypass path-list inference")

    def candidate_paths():
        yield first
        assert first_scanned, "scan_paths must stream known-root path iterables"
        yield second

    monkeypatch.setattr(
        private_state_scan,
        "_scan_path_with_terms",
        counted_scan_path_with_terms,
    )
    monkeypatch.setattr(
        private_state_scan,
        "_infer_display_root",
        fail_infer_display_root,
    )

    result = scan_paths(
        candidate_paths(),
        forbidden_classes=policy,
        display_root=public_root,
    )

    assert result["status"] == PASS
    assert result["scanned_path_count"] == 2


def test_scan_paths_skips_symlinked_file_candidates(tmp_path: Path) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    public_root = tmp_path / "microcosm-substrate"
    public_root.mkdir()
    outside_target = tmp_path / "outside_target.txt"
    outside_target.write_text(
        "SYNTHETIC_RAW_SEED_BODY_SENTINEL\n",
        encoding="utf-8",
    )
    symlinked_candidate = public_root / "linked_target.txt"
    symlinked_candidate.symlink_to(outside_target)

    result = scan_paths(
        [symlinked_candidate],
        forbidden_classes=policy,
        display_root=public_root,
    )

    assert result["status"] == PASS
    assert result["scanned_path_count"] == 0
    assert result["hits"] == []


def test_scan_paths_merges_clean_results_without_per_file_result_list(
    monkeypatch,
    tmp_path: Path,
) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixtures = []
    for index in range(3):
        fixture = tmp_path / f"clean_{index}.txt"
        fixture.write_text(f"public body {index}\n", encoding="utf-8")
        fixtures.append(fixture)

    def fail_per_file_result_merge(*_args, **_kwargs):
        raise AssertionError("scan_paths should merge hits incrementally")

    monkeypatch.setattr(
        private_state_scan,
        "_merge_scan_results",
        fail_per_file_result_merge,
    )

    result = scan_paths(
        (fixture for fixture in fixtures),
        forbidden_classes=policy,
        display_root=tmp_path,
    )

    assert result["status"] == PASS
    assert result["scanned_path_count"] == 3
    assert result["hits"] == []


def test_scanner_blocks_unreadable_text_candidate_without_body(tmp_path: Path) -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    fixture = tmp_path / "bad.txt"
    fixture.write_bytes(b"\xff\xfe\xfa")

    result = scan_paths([fixture], forbidden_classes=policy)

    assert result["status"] == BLOCKED_PRIVATE
    assert result["scanned_path_count"] == 1
    assert result["blocking_hit_count"] == 1
    assert result["hits"][0]["forbidden_class"] == "unreadable_text_candidate"
    assert result["hits"][0]["term_id"] == "utf8_decode_failed"
    assert result["hits"][0]["error_class"] == "UnicodeDecodeError"
    assert result["hits"][0]["body_redacted"] is True
    assert "matched_excerpt" not in result["hits"][0]
    assert "body" not in result["hits"][0]


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


def test_public_relative_path_falls_back_to_inferred_public_root(
    tmp_path: Path,
) -> None:
    display_root = tmp_path / "microcosm-substrate"
    display_root.mkdir()
    source_path = MICROCOSM_ROOT / "src/microcosm_core/private_state_scan.py"

    result = private_state_scan.public_relative_path(
        source_path,
        display_root=display_root,
    )

    assert result == "src/microcosm_core/private_state_scan.py"
    assert "/Users/" not in result
    assert "src/ai_workflow" not in result


def test_expected_negative_fixture_does_not_block_root_scan() -> None:
    policy = load_forbidden_classes(POLICY_PATH)
    text = '{"expected_negative_case": true, "body": "SYNTHETIC_RAW_SEED_BODY_SENTINEL"}'

    result = scan_text(
        text,
        path="fixtures/first_wave/pattern_binding_contract/input/example.json",
        forbidden_classes=policy,
    )

    assert result["status"] == PASS
    assert result["scan_scope"]["does_not_certify_absence_of_secrets"] is True
    assert result["hits"][0]["expected_negative_case"] is True


def test_private_state_validator_skips_local_runtime_residue(tmp_path: Path) -> None:
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
        ".microcosm/test-tmp/pytest/copied/microcosm-substrate/README.md",
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

    iterator = private_state_scan_validator._iter_scan_paths(root)

    assert not isinstance(iterator, list)

    receipt = validate_private_state_scan(root)

    assert receipt["status"] == PASS
    assert receipt["private_state_scan"]["blocking_hit_count"] == 0
    assert receipt["private_state_scan"]["scanned_path_count"] == 2

    (root / "public_sentinel.txt").write_text(
        "SYNTHETIC_RAW_SEED_BODY_SENTINEL\n",
        encoding="utf-8",
    )

    blocked = validate_private_state_scan(root)

    assert blocked["status"] == BLOCKED_PRIVATE
    assert blocked["private_state_scan"]["blocking_hit_count"] == 1
    assert blocked["private_state_scan"]["hits"][0]["path"] == "public_sentinel.txt"


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
            "credential_exposure_risk": "low",
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
            "credential_exposure_risk": "low",
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
    assert tool["scan_scope"]["not_a_complete_secret_scan"] is True
    assert "complete secret scan" in tool["anti_claim"]
    assert proof["status"] == PASS
    assert proof["route"] == "verified_light_edit"


def test_verified_macro_import_still_blocks_credential_bound_classes() -> None:
    policy = load_forbidden_classes(POLICY_PATH)

    result = classify_public_safe_macro_import(
        {
            "material_class": "raw_seed_body",
            "credential_exposure_risk": "none",
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
