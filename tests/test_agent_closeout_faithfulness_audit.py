from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.organs.agent_closeout_faithfulness_audit import (
    EXPECTED_NEGATIVE_CASES,
    _select_pytest_python,
    run,
    run_agent_closeout_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/agent_closeout_faithfulness_audit/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_closeout_faithfulness_audit/"
    "exported_agent_closeout_faithfulness_audit_bundle"
)


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_closeout_faithfulness_audit",
        public_root / "examples/agent_closeout_faithfulness_audit",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_closeout_faithfulness_audit",
        public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit",
    )
    return public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit/input"


def test_agent_closeout_faithfulness_audit_runs_public_subprocess_witness(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_closeout_faithfulness_audit",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/agent_closeout_faithfulness_audit_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["exercise"]["external_witness"]["git_subprocess_count"] >= 5
    assert result["exercise"]["external_witness"]["pytest_subprocess_count"] == 1
    assert result["exercise"]["verified_claim_count"] == 3
    assert result["exercise"]["pytest_span_ran_count"] == 1
    assert result["exercise"]["pytest_pass_status_checked_count"] == 1
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["receipt_body_scan"]["status"] == "pass"


def test_agent_closeout_faithfulness_audit_rejects_fake_commit(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_closeout_faithfulness_audit",
        public_root / "examples/agent_closeout_faithfulness_audit",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_closeout_faithfulness_audit",
        public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit",
    )
    fixture = public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit/input"
    claims_path = fixture / "closeout_claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["commit_ref"] = "0000000000000000000000000000000000000000"
    claims_path.write_text(json.dumps(claims, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/agent_closeout_faithfulness_audit")

    assert result["status"] == "blocked"
    assert "CLOSEOUT_FAKE_COMMIT_CLAIM" in result["error_codes"]


def test_agent_closeout_faithfulness_audit_rejects_unchecked_pytest_pass_claim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_closeout_faithfulness_audit",
        public_root / "examples/agent_closeout_faithfulness_audit",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_closeout_faithfulness_audit",
        public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit",
    )
    fixture = public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit/input"
    claims_path = fixture / "closeout_claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][2]["pass_status_checked"] = False
    claims_path.write_text(json.dumps(claims, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/agent_closeout_faithfulness_audit")

    assert result["status"] == "blocked"
    assert "CLOSEOUT_PYTEST_PASS_STATUS_NOT_CHECKED" in result["error_codes"]


def test_agent_closeout_faithfulness_audit_rejects_fake_cap_claim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_closeout_faithfulness_audit",
        public_root / "examples/agent_closeout_faithfulness_audit",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_closeout_faithfulness_audit",
        public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit",
    )
    fixture = public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit/input"
    claims_path = fixture / "closeout_claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][1]["cap_id"] = "cap_missing_from_fixture_ledger"
    claims_path.write_text(json.dumps(claims, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/agent_closeout_faithfulness_audit")

    assert result["status"] == "blocked"
    assert "CLOSEOUT_FAKE_CAP_CLAIM" in result["error_codes"]


def test_agent_closeout_faithfulness_audit_rejects_fake_pytest_nodeid(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_closeout_faithfulness_audit",
        public_root / "examples/agent_closeout_faithfulness_audit",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_closeout_faithfulness_audit",
        public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit",
    )
    fixture = public_root / "fixtures/first_wave/agent_closeout_faithfulness_audit/input"
    claims_path = fixture / "closeout_claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][2]["nodeid"] = "tests/test_closeout_fixture.py::test_missing_node"
    claims_path.write_text(json.dumps(claims, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / "receipts/first_wave/agent_closeout_faithfulness_audit")

    assert result["status"] == "blocked"
    assert "CLOSEOUT_FAKE_TEST_CLAIM" in result["error_codes"]


def test_agent_closeout_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/agent_closeout_faithfulness_audit",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    for expected_codes in EXPECTED_NEGATIVE_CASES.values():
        for code in expected_codes:
            assert code in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_agent_closeout_bundle_uses_body_free_source_manifest(tmp_path: Path) -> None:
    result = run_agent_closeout_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_closeout_faithfulness_audit",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_agent_closeout_faithfulness_audit_bundle"
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["source_module_manifest"]["body_in_receipt"] is False


def test_agent_closeout_bundle_uses_public_subprocess_witness(tmp_path: Path) -> None:
    result = run_agent_closeout_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_closeout_faithfulness_audit",
        command="pytest",
    )

    assert result["status"] == "pass"
    witness = result["exercise"]["external_witness"]
    assert witness["git_subprocess_count"] >= 5
    assert witness["pytest_subprocess_count"] == 1
    assert witness["head_verified_by_subprocess"] is True
    assert result["exercise"]["pytest_span_ran_count"] == 1
    assert result["exercise"]["pytest_pass_status_checked_count"] == 1
    assert result["exercise"]["verified_claim_count"] == 3
    [span] = result["exercise"]["spans"]
    assert span["span_ran"] is True
    assert span["pass_status_checked"] is True
    assert span["passed"] is True
    assert span["returncode"] == 0


def test_agent_closeout_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_closeout_faithfulness_audit/"
        "exported_agent_closeout_faithfulness_audit_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_agent_closeout_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/agent_closeout_faithfulness_audit",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False


def test_agent_closeout_faithfulness_audit_selects_pytest_capable_python(tmp_path: Path) -> None:
    missing_pytest = tmp_path / "missing_pytest_python"
    missing_pytest.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    missing_pytest.chmod(0o755)

    pytest_capable = tmp_path / "pytest_capable_python"
    pytest_capable.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"pytest\" ] && [ \"$3\" = \"--version\" ]; then\n"
        "  echo 'pytest fake'\n"
        "  exit 0\n"
        "fi\n"
        "exit 7\n",
        encoding="utf-8",
    )
    pytest_capable.chmod(0o755)

    assert _select_pytest_python([missing_pytest, pytest_capable]) == pytest_capable
