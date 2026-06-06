from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from microcosm_core.organs.bounded_autonomy_campaign_packet import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_bounded_autonomy_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/bounded_autonomy_campaign_packet/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/bounded_autonomy_campaign_packet/"
    "exported_bounded_autonomy_campaign_packet_bundle"
)


def test_bounded_autonomy_campaign_packet_drafts_only(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/bounded_autonomy_campaign_packet",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["exercise"]["candidate_count"] == 2
    assert result["exercise"]["self_proposal_only"] is True
    assert result["exercise"]["source_mutation_authorized"] is False
    assert result["exercise"]["external_witness"]["subprocess_returncode"] == 0
    builder_witness = result["exercise"]["real_campaign_builder_witness"]
    assert builder_witness["status"] == "pass"
    assert (
        builder_witness["builder_ref"]
        == "tools/meta/factory/build_standard_skill_pairing_campaign.py"
    )
    assert builder_witness["candidate_target_count"] == 2
    assert builder_witness["source_digest"]
    assert builder_witness["wrote_packet"] is None
    assert (
        result["exercise"]["candidate_packet"]["real_campaign_builder_witness_status"]
        == "pass"
    )
    assert "BOUNDED_AUTONOMY_REAL_BUILDER_WITNESS_BLOCKED" not in result["error_codes"]
    assert "BOUNDED_AUTONOMY_CANDIDATE_PACKET_EMPTY" not in result["error_codes"]
    assert result["source_module_manifest"]["module_count"] == 3


def _attach_builder_witness_tools(public_root: Path) -> None:
    tools_target = public_root.parent / "tools"
    if not tools_target.exists():
        tools_target.symlink_to(SOURCE_ROOT / "tools", target_is_directory=True)
    repo_python_target = public_root.parent / "repo-python"
    if not repo_python_target.exists():
        repo_python_target.symlink_to(SOURCE_ROOT / "repo-python")


def test_bounded_autonomy_candidate_count_moves_with_policy(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/bounded_autonomy_campaign_packet",
        public_root / "examples/bounded_autonomy_campaign_packet",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/bounded_autonomy_campaign_packet",
        public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet",
    )
    fixture = public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet/input"
    policy_path = fixture / "campaign_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["max_candidate_count"] = 1
    policy_path.write_text(json.dumps(policy, sort_keys=True), encoding="utf-8")

    _attach_builder_witness_tools(public_root)

    result = run(
        fixture,
        public_root / "receipts/first_wave/bounded_autonomy_campaign_packet",
    )

    assert result["status"] == "pass"
    assert result["exercise"]["candidate_count"] == 1
    assert result["exercise"]["real_campaign_builder_witness"]["candidate_target_count"] == 1


def test_bounded_autonomy_campaign_packet_rejects_source_write_policy(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/bounded_autonomy_campaign_packet",
        public_root / "examples/bounded_autonomy_campaign_packet",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/bounded_autonomy_campaign_packet",
        public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet",
    )
    fixture = public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet/input"
    _attach_builder_witness_tools(public_root)
    policy_path = fixture / "campaign_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["allowed_actions"].append("write_source")
    policy_path.write_text(json.dumps(policy, sort_keys=True), encoding="utf-8")

    result = run(
        fixture,
        public_root / "receipts/first_wave/bounded_autonomy_campaign_packet",
    )

    assert result["status"] == "blocked"
    assert "BOUNDED_AUTONOMY_SOURCE_WRITE_FORBIDDEN" in result["error_codes"]


def test_bounded_autonomy_campaign_packet_blocks_without_real_builder(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/bounded_autonomy_campaign_packet",
        public_root / "examples/bounded_autonomy_campaign_packet",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/bounded_autonomy_campaign_packet",
        public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet",
    )
    fixture = public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet/input"

    result = run(
        fixture,
        public_root / "receipts/first_wave/bounded_autonomy_campaign_packet",
    )

    assert result["status"] == "blocked"
    assert "BOUNDED_AUTONOMY_REAL_BUILDER_WITNESS_BLOCKED" in result["error_codes"]
    assert (
        result["exercise"]["real_campaign_builder_witness"]["error_code"]
        == "BOUNDED_AUTONOMY_CAMPAIGN_BUILDER_MISSING"
    )


def test_bounded_autonomy_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/bounded_autonomy_campaign_packet",
        public_root / "examples/bounded_autonomy_campaign_packet",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/bounded_autonomy_campaign_packet",
        public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet",
    )
    fixture = public_root / "fixtures/first_wave/bounded_autonomy_campaign_packet/input"
    _attach_builder_witness_tools(public_root)
    for name in (
        "source_write_campaign_packet.json",
        "repeated_failed_campaign_digest.json",
    ):
        path = fixture / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run(
        fixture,
        public_root / "receipts/first_wave/bounded_autonomy_campaign_packet",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(
        row["semantic_evaluator_used"] for row in result["negative_case_semantics"]
    )
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "BOUNDED_AUTONOMY_SOURCE_WRITE_FORBIDDEN" in result["error_codes"]
    assert "BOUNDED_AUTONOMY_REPEATED_FAILED_DIGEST" in result["error_codes"]
    assert "BOUNDED_AUTONOMY_REAL_BUILDER_WITNESS_BLOCKED" not in result["error_codes"]


def test_bounded_autonomy_bundle_runs(tmp_path: Path) -> None:
    result = run_bounded_autonomy_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/bounded_autonomy_campaign_packet",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_bounded_autonomy_campaign_packet_bundle"


def test_bounded_autonomy_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(
        (BUNDLE_INPUT / "source_module_manifest.json").read_text(encoding="utf-8")
    )
    macro_root = MICROCOSM_ROOT.parent

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False

    for row in manifest["modules"]:
        assert row["source_to_target_relation"] == "exact_copy"
        source = macro_root / row["source_ref"]
        target = BUNDLE_INPUT / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        source_bytes = source.read_bytes()
        target_bytes = target.read_bytes()
        digest = hashlib.sha256(source_bytes).hexdigest()

        assert source_bytes == target_bytes, row["source_ref"]
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        assert row["line_count"] == len(source_bytes.splitlines())
        assert row["byte_count"] == len(source_bytes)
