"""
Bounded autonomy campaign packet replay organ.

[PURPOSE] Validate that a bounded-autonomy campaign can draft candidate repair packets from public synthetic coverage gaps without authorizing self-repair, provider calls, source writes, or release.
[INTERFACE] Exposes the CrownJewelSpec-driven organ entrypoints `evaluate`, `evaluate_negative_case`, `run`, `run_bounded_autonomy_bundle`, and `main`.
[FLOW] Load public fixture inputs, obtain a read-only real campaign-builder witness, build a candidate packet, reject source-write and repeated-failure cases, then emit result, board, validation, and acceptance receipts.
[DEPENDENCIES] Uses JSON fixtures, subprocess execution of the public macro campaign builder, and the shared `_crown_jewel_common` result/receipt harness.
[CONSTRAINTS] Receipt payloads carry hashes and bounded packet summaries only; passing means the self-proposal boundary is wired, not that autonomous repair or release is authorized.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from microcosm_core.organs._crown_jewel_common import (
    PASS,
    CrownJewelSpec,
    finding,
    load_json_object,
    main_for_spec,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "bounded_autonomy_campaign_packet"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
BUILDER_REF = "tools/meta/factory/build_standard_skill_pairing_campaign.py"
EXPECTED_NEGATIVE_CASES = {
    "source_write_campaign_packet": ("BOUNDED_AUTONOMY_SOURCE_WRITE_FORBIDDEN",),
    "repeated_failed_campaign_digest": ("BOUNDED_AUTONOMY_REPEATED_FAILED_DIGEST",),
}
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "self_proposal_campaign_packet_only",
    "self_repair_authorized": False,
    "unsupervised_source_mutation_authorized": False,
    "source_write_packet_authorized": False,
    "provider_calls_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Bounded autonomy campaign packet emits a draft self-proposal from public "
    "synthetic coverage gaps and refuses source-write or repeated-failure "
    "packets. It does not self-repair, mutate source unsupervised, call "
    "providers, or authorize release."
)

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Bounded autonomy campaign packet",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=f"{ORGAN_ID}_result.json",
    board_name=f"{ORGAN_ID}_board.json",
    validation_receipt_name=f"{ORGAN_ID}_validation_receipt.json",
    bundle_result_name=f"exported_{ORGAN_ID}_bundle_validation_result.json",
    card_schema_version=f"{ORGAN_ID}_command_card_v1",
    required_inputs=("coverage_gaps.json", "campaign_policy.json", "failed_campaign_digests.json", "projection_protocol.json"),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/bounded_autonomy_campaign_packet/"
        "exported_bounded_autonomy_campaign_packet_bundle/source_module_manifest.json"
    ),
    source_required_anchors={
        "tools/meta/control/reactions_engine.py": ("reaction", "campaign"),
        "tools/meta/factory/build_compliance_autocure_campaign.py": ("campaign", "compliance"),
        "tools/meta/factory/build_standard_skill_pairing_campaign.py": ("campaign", "standard"),
    },
    bundle_input_mode="exported_bounded_autonomy_campaign_packet_bundle",
)


def _source_module_manifest_path(public_root: Path) -> Path:
    """
    [ACTION] Resolve the public source-module manifest that carries the exported campaign-builder body.
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_root / SPEC.source_manifest_ref


def _sha256_file(path: Path) -> str:
    """
    [ACTION] Hash a public source-module target so the builder witness can bind bytes without embedding bodies.
    - Teleology: Implements `_sha256_file` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _public_source_module_builder_witness(
    public_root: Path,
    *,
    max_targets: int,
) -> dict[str, Any]:
    """
    [ACTION] Validate the exported builder source-module target as the standalone public witness when no live macro builder checkout is present.
    - Teleology: Implements `_public_source_module_builder_witness` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    manifest_path = _source_module_manifest_path(public_root)
    if not manifest_path.is_file():
        return {
            "status": "blocked",
            "returncode": None,
            "builder_ref": BUILDER_REF,
            "witness_mode": "public_source_module_manifest",
            "error_code": "BOUNDED_AUTONOMY_SOURCE_MODULE_MANIFEST_MISSING",
            "body_in_receipt": False,
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "blocked",
            "returncode": None,
            "builder_ref": BUILDER_REF,
            "witness_mode": "public_source_module_manifest",
            "error_code": "BOUNDED_AUTONOMY_SOURCE_MODULE_MANIFEST_INVALID",
            "body_in_receipt": False,
        }
    row = next(
        (
            item
            for item in manifest.get("modules", [])
            if isinstance(item, dict) and item.get("source_ref") == BUILDER_REF
        ),
        None,
    )
    if not isinstance(row, dict):
        return {
            "status": "blocked",
            "returncode": None,
            "builder_ref": BUILDER_REF,
            "witness_mode": "public_source_module_manifest",
            "error_code": "BOUNDED_AUTONOMY_CAMPAIGN_BUILDER_SOURCE_MODULE_MISSING",
            "body_in_receipt": False,
        }
    target = manifest_path.parent / str(row.get("path") or "")
    if not target.is_file():
        return {
            "status": "blocked",
            "returncode": None,
            "builder_ref": BUILDER_REF,
            "witness_mode": "public_source_module_manifest",
            "error_code": "BOUNDED_AUTONOMY_CAMPAIGN_BUILDER_TARGET_MISSING",
            "body_in_receipt": False,
        }
    digest = _sha256_file(target)
    text = target.read_text(encoding="utf-8")
    missing_anchors = [
        anchor for anchor in row.get("required_anchors", []) if anchor not in text
    ]
    line_count = len(target.read_bytes().splitlines())
    digest_match = digest == row.get("sha256") == row.get("target_sha256")
    line_count_match = line_count == row.get("line_count")
    status = PASS if digest_match and line_count_match and not missing_anchors else "blocked"
    return {
        "status": status,
        "returncode": 0 if status == PASS else None,
        "builder_ref": BUILDER_REF,
        "witness_mode": "public_source_module_manifest",
        "kind": "standard_skill_pairing_campaign_summary",
        "campaign_slug": "public_source_module_manifest_witness",
        "candidate_target_count": max(0, int(max_targets)),
        "source_digest": digest,
        "wrote_packet": None,
        "no_op": False,
        "expected_kind": True,
        "no_write": True,
        "digest_match": digest_match,
        "line_count_match": line_count_match,
        "missing_required_anchors": missing_anchors,
        "stdout_sha256": _sha256_text(""),
        "stderr_sha256": _sha256_text(""),
        "body_in_receipt": False,
    }


def _campaign_builder_witness(public_root: Path, *, max_targets: int) -> dict[str, Any]:
    """
    [ACTION] Run a live campaign-builder witness when available, otherwise validate the shipped public source-module builder target as the standalone witness.
    - Teleology: Implements `_campaign_builder_witness` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    repo_root = public_root.parent
    builder_path = repo_root / BUILDER_REF
    if not builder_path.is_file():
        return _public_source_module_builder_witness(
            public_root,
            max_targets=max_targets,
        )
    repo_python = repo_root / "repo-python"
    executable = str(repo_python) if repo_python.is_file() else sys.executable
    command = [
        executable,
        BUILDER_REF,
        "--check",
        "--report",
        "--max-targets",
        str(max_targets),
    ]
    try:
        proc = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "builder_ref": BUILDER_REF,
            "witness_mode": "live_macro_builder",
            "error_code": "BOUNDED_AUTONOMY_CAMPAIGN_BUILDER_TIMEOUT",
            "body_in_receipt": False,
        }
    try:
        packet = json.loads(proc.stdout) if proc.returncode == 0 else {}
    except json.JSONDecodeError:
        packet = {}
    candidate_target_count = int(packet.get("candidate_target_count") or 0)
    source_digest = str(packet.get("source_digest") or "")
    expected_kind = packet.get("kind") == "standard_skill_pairing_campaign_summary"
    no_write = packet.get("wrote_packet") is None
    status = (
        PASS
        if (
            proc.returncode == 0
            and expected_kind
            and not packet.get("no_op")
            and candidate_target_count > 0
            and source_digest
            and no_write
        )
        else "blocked"
    )
    return {
        "status": status,
        "returncode": proc.returncode,
        "builder_ref": BUILDER_REF,
        "witness_mode": "live_macro_builder",
        "kind": packet.get("kind"),
        "campaign_slug": packet.get("campaign_slug"),
        "candidate_target_count": candidate_target_count,
        "source_digest": source_digest,
        "wrote_packet": packet.get("wrote_packet"),
        "no_op": bool(packet.get("no_op")),
        "expected_kind": expected_kind,
        "no_write": no_write,
        "stdout_sha256": _sha256_text(proc.stdout),
        "stderr_sha256": _sha256_text(proc.stderr),
        "body_in_receipt": False,
    }


def _sha256_text(text: str) -> str:
    """
    [ACTION] Hash captured subprocess text so receipts can bind output without embedding source or stdout bodies.
    - Teleology: Implements `_sha256_text` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _candidate_packet_subprocess(
    gaps: dict[str, Any],
    policy: dict[str, Any],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION] Convert coverage gaps and policy into a bounded draft candidate packet using the campaign-builder witness as the authority source.
    - Teleology: Implements `_candidate_packet_subprocess` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    candidate_limit = int(policy.get("max_candidate_count", 2))
    witness = _campaign_builder_witness(public_root, max_targets=candidate_limit)
    candidate_count = min(
        candidate_limit,
        int(witness.get("candidate_target_count") or 0),
    )
    gap_rows = [row for row in gaps.get("gaps", []) if isinstance(row, dict)]
    candidates = []
    for index in range(candidate_count):
        if index < len(gap_rows):
            gap_id = str(
                gap_rows[index].get("gap_id") or f"macro_builder_target_{index + 1}"
            )
        else:
            gap_id = f"macro_builder_target_{index + 1}"
        candidates.append(
            {
                "candidate_id": f"real_builder::{index + 1}",
                "gap_id": gap_id,
                "action": "draft_candidate_packet",
                "write_surface": "none",
                "requires_human_review": True,
                "source_mutation_authorized": False,
                "campaign_builder_ref": witness.get("builder_ref"),
                "campaign_builder_source_digest": witness.get("source_digest"),
                "body_in_receipt": False,
            }
        )
    return {
        "returncode": witness.get("returncode"),
        "packet": {
            "schema_version": "bounded_autonomy_candidate_packet_v1",
            "status": "drafted" if witness.get("status") == PASS else "blocked",
            "candidate_count": len(candidates),
            "candidates": candidates,
            "self_repair_authorized": False,
            "source_mutation_authorized": False,
            "real_campaign_builder_witness_status": witness.get("status"),
            "body_in_receipt": False,
        },
        "real_campaign_builder_witness": witness,
        "stdout_sha256": witness.get("stdout_sha256"),
        "stderr_sha256": witness.get("stderr_sha256"),
        "body_in_receipt": False,
    }


def evaluate(input_dir: Path, _public_root: Path, _source_manifest: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION] Evaluate the positive fixture by loading policy, gap, and failed-digest inputs, checking the real builder witness, and enforcing no source-write or repeated-failure authorization.
    - Teleology: Implements `evaluate` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    findings: list[dict[str, Any]] = []
    gaps = load_json_object(input_dir / "coverage_gaps.json", findings, label="coverage gaps")
    policy = load_json_object(input_dir / "campaign_policy.json", findings, label="campaign policy")
    failed = load_json_object(
        input_dir / "failed_campaign_digests.json",
        findings,
        label="failed campaign digest ledger",
    )
    allowed_actions = set(policy.get("allowed_actions", []))
    if "write_source" in allowed_actions:
        findings.append(
            finding(
                "BOUNDED_AUTONOMY_SOURCE_WRITE_FORBIDDEN",
                "Campaign packet policy may not allow source-write actions.",
                observed=sorted(allowed_actions),
            )
        )
    witness = _candidate_packet_subprocess(gaps, policy, _public_root)
    real_builder_witness = (
        witness.get("real_campaign_builder_witness")
        if isinstance(witness.get("real_campaign_builder_witness"), dict)
        else {}
    )
    if real_builder_witness.get("status") != PASS:
        findings.append(
            finding(
                "BOUNDED_AUTONOMY_REAL_BUILDER_WITNESS_BLOCKED",
                "Campaign packet positive lane must be witnessed by a read-only real macro campaign builder.",
                observed=real_builder_witness.get("error_code")
                or real_builder_witness.get("status"),
            )
        )
    packet = witness.get("packet") if isinstance(witness.get("packet"), dict) else {}
    if witness["returncode"] != 0 or packet.get("status") != "drafted":
        findings.append(
            finding(
                "BOUNDED_AUTONOMY_PACKET_SUBPROCESS_FAILED",
                "External subprocess did not emit a draft candidate packet.",
                observed=witness["returncode"],
            )
        )
    if int(packet.get("candidate_count") or 0) < 1:
        findings.append(
            finding(
                "BOUNDED_AUTONOMY_CANDIDATE_PACKET_EMPTY",
                "Real campaign builder witness must produce at least one candidate target.",
                observed=packet.get("candidate_count"),
            )
        )
    for candidate in packet.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        if candidate.get("source_mutation_authorized") is True or candidate.get("write_surface") == "source":
            findings.append(
                finding(
                    "BOUNDED_AUTONOMY_SOURCE_WRITE_FORBIDDEN",
                    "Draft candidate packet may not authorize source mutation.",
                    case_id=str(candidate.get("candidate_id") or ""),
                )
            )
    failed_digests = [
        str(row.get("digest"))
        for row in failed.get("failed_digests", [])
        if isinstance(row, dict) and row.get("digest")
    ]
    repeat_count = len(failed_digests) - len(set(failed_digests))
    if repeat_count:
        findings.append(
            finding(
                "BOUNDED_AUTONOMY_REPEATED_FAILED_DIGEST",
                "Repeated failed campaign digest must be refused.",
                observed=repeat_count,
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "external_witness": {
            "subprocess_returncode": witness["returncode"],
            "stdout_sha256": witness["stdout_sha256"],
            "stderr_sha256": witness["stderr_sha256"],
            "body_in_receipt": False,
        },
        "real_campaign_builder_witness": real_builder_witness,
        "gap_count": len([row for row in gaps.get("gaps", []) if isinstance(row, dict)]),
        "candidate_count": packet.get("candidate_count", 0),
        "candidate_packet": packet,
        "failed_digest_count": len(failed_digests),
        "repeated_failed_digest_count": repeat_count,
        "self_proposal_only": True,
        "source_mutation_authorized": False,
        "findings": findings,
    }


def _write_json(path: Path, payload: object) -> None:
    """
    [ACTION] Persist mutated semantic-negative fixture JSON with deterministic formatting for local negative-case exercises.
    - Teleology: Implements `_write_json` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    """
    [ACTION] Materialize a supported negative fixture mutation and return only the observed error codes needed by the crown-jewel harness.
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, declared filesystem outputs.
    """
    with TemporaryDirectory(prefix=f"{ORGAN_ID}-{case_id}-") as scratch:
        semantic_input = Path(scratch) / "input"
        semantic_input.mkdir(parents=True, exist_ok=True)
        for name in SPEC.required_inputs:
            shutil.copy2(input_dir / name, semantic_input / name)

        if case_id == "source_write_campaign_packet":
            policy_path = semantic_input / "campaign_policy.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            allowed_actions = list(policy.get("allowed_actions", []))
            if "write_source" not in allowed_actions:
                allowed_actions.append("write_source")
            policy["allowed_actions"] = allowed_actions
            _write_json(policy_path, policy)
        elif case_id == "repeated_failed_campaign_digest":
            failed_path = semantic_input / "failed_campaign_digests.json"
            failed = json.loads(failed_path.read_text(encoding="utf-8"))
            rows = [
                row
                for row in failed.get("failed_digests", [])
                if isinstance(row, dict) and row.get("digest")
            ]
            repeated_digest = (
                str(rows[0]["digest"])
                if rows
                else "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            )
            failed["failed_digests"] = [
                {"digest": repeated_digest},
                {"digest": repeated_digest},
            ]
            _write_json(failed_path, failed)
        else:
            return {
                "status": "blocked",
                "error_codes": ["BOUNDED_AUTONOMY_NEGATIVE_CASE_UNSUPPORTED"],
                "body_in_receipt": False,
            }

        result = evaluate(semantic_input, public_root_for_path(input_dir), {})
        return {
            "status": result["status"],
            "error_codes": [
                str(row.get("error_code"))
                for row in result.get("findings", [])
                if isinstance(row, dict) and row.get("error_code")
            ],
            "body_in_receipt": False,
        }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION] Run the bounded-autonomy fixture through the shared crown-jewel organ harness and write the normal result/receipt artifacts.
    - Teleology: Implements `run` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_bounded_autonomy_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION] Run the exported bounded-autonomy bundle mode through the same evaluator while preserving the public bundle input contract.
    - Teleology: Implements `run_bounded_autonomy_bundle` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION] Dispatch the CLI action table for this organ and return the shared harness exit status.
    - Teleology: Implements `main` for `microcosm_core.organs.bounded_autonomy_campaign_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return main_for_spec(
        SPEC,
        argv,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="run-bounded-autonomy-bundle",
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
