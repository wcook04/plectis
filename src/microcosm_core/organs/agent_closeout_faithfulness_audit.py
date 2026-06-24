"""Public fixture audit for agent closeout claims.

[PURPOSE] Re-run a small public fixture repo and fixture ledger so agent
closeout claims about commits, Task Ledger caps, and pytest spans are accepted
only when their referenced evidence exists.
[INTERFACE] Exposes the CrownJewel evaluator, negative-case evaluator, fixture
runner, exported-bundle runner, and CLI entrypoint for the
`agent_closeout_faithfulness_audit` organ.
[FLOW] Prepare a temporary Git repo from fixture source, collect its HEAD,
load closeout claims and ledger rows, run claimed pytest spans with an available
pytest-capable Python, and report body-free witness hashes and findings.
[DEPENDENCIES] Uses Crown Jewel organ helpers, subprocess Git/Pytest calls,
temporary directories, fixture JSON, and local Python environment discovery.
[CONSTRAINTS] This is a public fixture witness only. It does not prove arbitrary
live commits, close Task Ledger work, mutate the caller's Git repo, run provider
services, authorize release, or certify whole-system correctness.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from microcosm_core.organs._crown_jewel_common import (
    PASS,
    CrownJewelSpec,
    finding,
    load_json_object,
    main_for_spec,
    run_crown_jewel_organ,
)


ORGAN_ID = "agent_closeout_faithfulness_audit"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
MICROCOSM_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_NEGATIVE_CASES = {
    "fake_commit_claim": ("CLOSEOUT_FAKE_COMMIT_CLAIM",),
    "fake_cap_claim": ("CLOSEOUT_FAKE_CAP_CLAIM",),
    "fake_test_claim": ("CLOSEOUT_FAKE_TEST_CLAIM",),
    "unchecked_pass_claim": ("CLOSEOUT_PYTEST_PASS_STATUS_NOT_CHECKED",),
}
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_fixture_closeout_evidence_existence_and_pytest_span_witness_only",
    "commit_landed_without_head_match_authorized": False,
    "cap_closed_without_fixture_ledger_row_authorized": False,
    "pytest_pass_claim_without_exit_zero_authorized": False,
    "live_repo_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Closeout faithfulness audit verifies that a referenced public fixture commit "
    "object, ledger row, or pytest span exists and records whether a span passed "
    "only when pass status is explicitly checked. It does not prove arbitrary "
    "live commits landed, close Task Ledger work, mutate Git, run providers, or "
    "authorize release."
)

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Agent closeout faithfulness audit",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=f"{ORGAN_ID}_result.json",
    board_name=f"{ORGAN_ID}_board.json",
    validation_receipt_name=f"{ORGAN_ID}_validation_receipt.json",
    bundle_result_name=f"exported_{ORGAN_ID}_bundle_validation_result.json",
    card_schema_version=f"{ORGAN_ID}_command_card_v1",
    required_inputs=("closeout_claims.json", "fixture_ledger.json", "projection_protocol.json"),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/agent_closeout_faithfulness_audit/"
        "exported_agent_closeout_faithfulness_audit_bundle/source_module_manifest.json"
    ),
    source_required_anchors={
        "system/lib/agent_experience_diagnostics.py": (
            "Agent Experience Grand Rounds",
            "closeout",
        )
    },
    bundle_input_mode="exported_agent_closeout_faithfulness_audit_bundle",
)


def _run_subprocess(args: list[str], *, cwd: Path) -> dict[str, Any]:
    """[ACTION] Run a subprocess and return a body-free command witness."""
    proc = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "args": [Path(args[0]).name, *args[1:]],
        "returncode": proc.returncode,
        "stdout_sha256": _sha256_text(proc.stdout),
        "stderr_sha256": _sha256_text(proc.stderr),
        "body_in_receipt": False,
    }


def _sha256_text(text: str) -> str:
    """[ACTION] Hash command output text without storing the body in receipts."""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _venv_python(venv_dir: Path) -> Path:
    """[ACTION] Resolve the platform-specific Python executable inside a venv."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _pytest_python_candidates() -> list[Path]:
    """[ACTION] List candidate Python executables that may provide pytest."""
    candidates = [
        Path(sys.executable),
        _venv_python(MICROCOSM_ROOT / ".venv"),
        _venv_python(MICROCOSM_ROOT.parent / ".venv"),
    ]
    seen: set[str] = set()
    out: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            out.append(candidate)
    return out


def _select_pytest_python(candidates: Iterable[Path] | None = None) -> Path:
    """[ACTION] Select the first candidate Python that can run `pytest --version`."""
    for candidate in candidates or _pytest_python_candidates():
        if not candidate.exists():
            continue
        try:
            proc = subprocess.run(
                [str(candidate), "-m", "pytest", "--version"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError:
            continue
        if proc.returncode == 0:
            return candidate
    return Path(sys.executable)


def _prepare_public_fixture_repo(source_dir: Path, work_dir: Path) -> dict[str, Any]:
    """[ACTION] Copy fixture source into a temporary Git repo and commit it."""
    repo_dir = work_dir / "public_fixture_repo"
    shutil.copytree(source_dir, repo_dir)
    subprocesses: list[dict[str, Any]] = []
    for args in (
        ["git", "init"],
        ["git", "config", "user.email", "microcosm@example.invalid"],
        ["git", "config", "user.name", "Microcosm Fixture"],
        ["git", "add", "."],
        ["git", "commit", "-m", "public closeout fixture"],
    ):
        subprocesses.append(_run_subprocess(args, cwd=repo_dir))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    subprocesses.append(
        {
            "args": ["git", "rev-parse", "HEAD"],
            "returncode": head.returncode,
            "stdout_sha256": _sha256_text(head.stdout),
            "stderr_sha256": _sha256_text(head.stderr),
            "body_in_receipt": False,
        }
    )
    return {
        "repo_dir": repo_dir,
        "head": head.stdout.strip() if head.returncode == 0 else "",
        "subprocesses": subprocesses,
    }


def _semantic_closeout_contract_findings(
    input_dir: Path,
    claims: dict[str, Any],
) -> list[dict[str, Any]]:
    """[ACTION] Check claim rows against fixture source semantics without subprocess Git."""
    findings: list[dict[str, Any]] = []
    ledger = load_json_object(input_dir / "fixture_ledger.json", findings, label="fixture ledger")
    public_repo = input_dir / "public_fixture_repo"
    test_path = public_repo / "tests/test_closeout_fixture.py"
    arithmetic_path = public_repo / "micro_pkg/arithmetic.py"
    test_source = test_path.read_text(encoding="utf-8") if test_path.is_file() else ""
    arithmetic_source = (
        arithmetic_path.read_text(encoding="utf-8") if arithmetic_path.is_file() else ""
    )
    cap_ids = {
        str(row.get("cap_id"))
        for row in ledger.get("task_ledger_caps", [])
        if isinstance(row, dict) and row.get("cap_id")
    }
    expected_nodeid = "tests/test_closeout_fixture.py::test_public_fixture_addition"
    expected_source_present = (
        "def test_public_fixture_addition" in test_source
        and "assert add(2, 3) == 5" in test_source
        and "return left + right" in arithmetic_source
    )
    for claim in claims.get("claims", []):
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id") or "")
        claim_type = str(claim.get("claim_type") or "")
        if claim_type == "commit" and claim.get("commit_ref") != "HEAD":
            findings.append(
                finding(
                    "CLOSEOUT_FAKE_COMMIT_CLAIM",
                    "Commit closeout claim did not match the public fixture HEAD.",
                    case_id=claim_id,
                    observed=claim.get("commit_ref"),
                )
            )
        elif claim_type == "task_ledger_cap" and claim.get("cap_id") not in cap_ids:
            findings.append(
                finding(
                    "CLOSEOUT_FAKE_CAP_CLAIM",
                    "Task Ledger cap claim did not exist in the fixture ledger.",
                    case_id=claim_id,
                    observed=claim.get("cap_id"),
                )
            )
        elif claim_type == "pytest_span":
            span_verified = (
                claim.get("nodeid") == expected_nodeid
                and claim.get("pass_status_checked") is True
                and expected_source_present
            )
            if claim.get("nodeid") != expected_nodeid or not expected_source_present:
                findings.append(
                    finding(
                        "CLOSEOUT_FAKE_TEST_CLAIM",
                        "Pytest span claim did not resolve against the public fixture source.",
                        case_id=claim_id,
                        observed=claim.get("nodeid"),
                    )
                )
            if claim.get("expected_pass") is True and not span_verified:
                findings.append(
                    finding(
                        "CLOSEOUT_PYTEST_PASS_STATUS_NOT_CHECKED",
                        "A pass claim requires an explicit pass-status check and source witness.",
                        case_id=claim_id,
                    )
                )
    return findings


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    """[ACTION] Perturb one closeout claim and report the expected blocking codes."""
    findings: list[dict[str, Any]] = []
    claims = load_json_object(input_dir / "closeout_claims.json", findings, label="closeout claims")
    claims = copy.deepcopy(claims)
    claim_rows = [row for row in claims.get("claims", []) if isinstance(row, dict)]
    if case_id == "fake_commit_claim" and claim_rows:
        claim_rows[0]["commit_ref"] = "0000000000000000000000000000000000000000"
    elif case_id == "fake_cap_claim" and len(claim_rows) > 1:
        claim_rows[1]["cap_id"] = "cap_missing_from_fixture_ledger"
    elif case_id == "fake_test_claim" and len(claim_rows) > 2:
        claim_rows[2]["nodeid"] = "tests/test_closeout_fixture.py::test_missing_node"
    elif case_id == "unchecked_pass_claim" and len(claim_rows) > 2:
        claim_rows[2]["pass_status_checked"] = False
    else:
        findings.append(
            finding(
                "CLOSEOUT_NEGATIVE_CASE_UNSUPPORTED",
                "Unsupported closeout faithfulness negative case.",
                case_id=case_id,
            )
        )
    findings.extend(_semantic_closeout_contract_findings(input_dir, claims))
    return {
        "status": PASS if not findings else "blocked",
        "error_codes": sorted(
            {
                str(row.get("error_code"))
                for row in findings
                if isinstance(row, dict) and row.get("error_code")
            }
        ),
    }


def evaluate(input_dir: Path, _public_root: Path, _source_manifest: dict[str, Any]) -> dict[str, Any]:
    """[ACTION] Evaluate fixture closeout claims against a temporary public Git repo."""
    findings: list[dict[str, Any]] = []
    claims = load_json_object(input_dir / "closeout_claims.json", findings, label="closeout claims")
    ledger = load_json_object(input_dir / "fixture_ledger.json", findings, label="fixture ledger")
    public_repo = input_dir / "public_fixture_repo"
    if not public_repo.is_dir():
        findings.append(
            finding(
                "CLOSEOUT_PUBLIC_FIXTURE_REPO_MISSING",
                "Closeout audit requires a public fixture repo directory.",
                subject_id="public_fixture_repo",
            )
        )
        return {"status": "blocked", "findings": findings}
    with tempfile.TemporaryDirectory(prefix="microcosm-closeout-") as tmp:
        prepared = _prepare_public_fixture_repo(public_repo, Path(tmp))
        repo_dir = prepared["repo_dir"]
        actual_head = prepared["head"]
        spans: dict[str, dict[str, Any]] = {}
        pytest_python = _select_pytest_python()
        verified_count = 0
        passed_count = 0
        cap_ids = {
            str(row.get("cap_id"))
            for row in ledger.get("task_ledger_caps", [])
            if isinstance(row, dict) and row.get("cap_id")
        }
        for claim in claims.get("claims", []):
            if not isinstance(claim, dict):
                continue
            claim_id = str(claim.get("claim_id") or "")
            claim_type = str(claim.get("claim_type") or "")
            if claim_type == "commit":
                commit_ref = str(claim.get("commit_ref") or "")
                verified = commit_ref in {"HEAD", actual_head}
                verified_count += int(verified)
                if not verified:
                    findings.append(
                        finding(
                            "CLOSEOUT_FAKE_COMMIT_CLAIM",
                            "Commit closeout claim did not match the public fixture HEAD.",
                            case_id=claim_id,
                            expected=actual_head,
                            observed=commit_ref,
                        )
                    )
            elif claim_type == "task_ledger_cap":
                cap_id = str(claim.get("cap_id") or "")
                verified = cap_id in cap_ids
                verified_count += int(verified)
                if not verified:
                    findings.append(
                        finding(
                            "CLOSEOUT_FAKE_CAP_CLAIM",
                            "Task Ledger cap claim did not exist in the fixture ledger.",
                            case_id=claim_id,
                            observed=cap_id,
                        )
                    )
            elif claim_type == "pytest_span":
                nodeid = str(claim.get("nodeid") or "")
                proc = subprocess.run(
                    [str(pytest_python), "-m", "pytest", nodeid, "-q"],
                    cwd=repo_dir,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                span = {
                    "claim_id": claim_id,
                    "nodeid": nodeid,
                    "span_ran": proc.returncode in {0, 1},
                    "pass_status_checked": claim.get("pass_status_checked") is True,
                    "passed": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "pytest_runner": pytest_python.name,
                    "stdout_sha256": _sha256_text(proc.stdout),
                    "stderr_sha256": _sha256_text(proc.stderr),
                    "body_in_receipt": False,
                }
                spans[claim_id] = span
                verified_count += int(span["span_ran"])
                passed_count += int(span["passed"] and span["pass_status_checked"])
                if not span["span_ran"]:
                    findings.append(
                        finding(
                            "CLOSEOUT_FAKE_TEST_CLAIM",
                            "Pytest span claim did not run against the public fixture repo.",
                            case_id=claim_id,
                            observed=nodeid,
                        )
                    )
                if claim.get("expected_pass") is True and not (
                    span["pass_status_checked"] and span["passed"]
                ):
                    findings.append(
                        finding(
                            "CLOSEOUT_PYTEST_PASS_STATUS_NOT_CHECKED",
                            "A pass claim requires an explicit pass-status check and exit zero.",
                            case_id=claim_id,
                        )
                    )
        return {
            "status": PASS if not findings else "blocked",
            "external_witness": {
                "git_subprocess_count": len(prepared["subprocesses"]),
                "pytest_subprocess_count": len(spans),
                "head_verified_by_subprocess": bool(actual_head),
                "body_in_receipt": False,
            },
            "claim_count": len(claims.get("claims", [])),
            "verified_claim_count": verified_count,
            "pytest_span_ran_count": sum(1 for span in spans.values() if span["span_ran"]),
            "pytest_pass_status_checked_count": passed_count,
            "spans": list(spans.values()),
            "claim_ceiling": "verified means evidence object exists or span ran; pass requires explicit exit-zero status check",
            "findings": findings,
        }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the closeout faithfulness audit over fixture inputs."""
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_agent_closeout_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the exported bundle form of the closeout faithfulness audit."""
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=SPEC.bundle_input_mode,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def main(argv: list[str] | None = None) -> int:
    """[ACTION] Dispatch CLI arguments through the closeout audit entrypoint."""
    return main_for_spec(
        SPEC,
        argv,
        evaluator=evaluate,
        bundle_action="run-agent-closeout-bundle",
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
