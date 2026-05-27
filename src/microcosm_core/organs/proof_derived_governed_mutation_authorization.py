from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "proof_derived_governed_mutation_authorization"
FIXTURE_ID = "first_wave.proof_derived_governed_mutation_authorization"
VALIDATOR_ID = (
    "validator.microcosm.organs.proof_derived_governed_mutation_authorization"
)

RESULT_NAME = "proof_derived_governed_mutation_authorization_result.json"
BOARD_NAME = "proof_derived_governed_mutation_authorization_board.json"
VALIDATION_RECEIPT_NAME = (
    "proof_derived_governed_mutation_authorization_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "proof_derived_governed_mutation_authorization_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_governed_mutation_authorization_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "governed_mutation_authorization_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "private_state_scan",
    "authority_ceiling",
    "anti_claim",
    "proof_cell_rows",
    "policy_verdict_rows",
    "proposal_rows",
    "side_effect_rows",
    "rollback_rows",
    "cold_replay_rows",
    "authorization_board",
)

INPUT_NAMES = (
    "projection_protocol.json",
    "authorization_policy.json",
    "mutation_proposals.json",
    "proof_evidence_cells.json",
    "policy_verdicts.json",
    "side_effect_ledger.json",
    "rollback_receipts.json",
    "cold_replay.json",
)
NEGATIVE_INPUT_NAMES = (
    "standing_credential_authority.json",
    "policy_after_execution.json",
    "hidden_policy_vote.json",
    "live_cloud_credential.json",
    "irreversible_mutation.json",
    "unlogged_side_effect.json",
    "consensus_without_evidence.json",
    "final_answer_only_success.json",
)

EXPECTED_NEGATIVE_CASES = {
    "standing_credential_authority": ["GOV_MUT_STANDING_CREDENTIAL_AUTHORITY"],
    "policy_after_execution": ["GOV_MUT_POLICY_AFTER_EXECUTION"],
    "hidden_policy_vote": ["GOV_MUT_HIDDEN_POLICY_VOTE"],
    "live_cloud_credential": ["GOV_MUT_LIVE_CLOUD_CREDENTIAL"],
    "irreversible_mutation": ["GOV_MUT_IRREVERSIBLE_MUTATION"],
    "unlogged_side_effect": ["GOV_MUT_UNLOGGED_SIDE_EFFECT"],
    "consensus_without_evidence": ["GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE"],
    "final_answer_only_success": ["GOV_MUT_FINAL_ANSWER_ONLY_SUCCESS"],
}

REQUIRED_ACTION_CLASSES = (
    "read_only_inspection",
    "scoped_config_write",
    "rollback",
)
REQUIRED_PROPOSAL_FIELDS = (
    "proposal_id",
    "action_class",
    "intent_capsule_ref",
    "authority_ceiling_ref",
    "proof_cell_refs",
    "policy_verdict_refs",
    "ephemeral_identity_ref",
    "side_effect_class",
    "policy_evaluated_before_execution",
    "execution_state",
    "evidence_chain_hash",
    "cold_replay_ref",
    "body_redacted",
    "private_ref_metadata_only",
)
FORBIDDEN_KEYS = (
    "credential_value",
    "secret_value",
    "token_value",
    "provider_payload",
    "private_account_id",
    "raw_policy_vote_body",
    "raw_proof_body",
    "cloud_account_id",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "synthetic_proof_derived_governed_mutation_authorization_receipts_only"
    ),
    "live_cloud_account_authorized": False,
    "standing_credentials_authorized": False,
    "source_mutation_authorized": False,
    "irreversible_mutation_authorized": False,
    "policy_after_execution_authorized": False,
    "hidden_policy_votes_authorized": False,
    "provider_calls_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Proof-derived governed mutation authorization validates a synthetic "
    "mutation-authorization contract: intent capsules, proof evidence cells, "
    "independent policy verdicts, ephemeral execution identity refs, logged "
    "side-effect diffs, rollback receipts, cold replay, negative cases, private "
    "state scan, and authority ceilings. It does not use standing credentials, "
    "access live cloud/accounts, mutate source, export proof bodies or provider "
    "payloads, claim benchmark safety, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        Path(__file__).resolve(),
        public_root / "core/private_state_forbidden_classes.json",
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "proof_derived_governed_mutation_authorization_result_v1"
        if include_negative
        else "exported_governed_mutation_authorization_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": validator_schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": (
            "governed_mutation_authorization_freshness_basis_v1"
        ),
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_authorization_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != (
        "exported_governed_mutation_authorization_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_governed_mutation_authorization_bundle":
        return None
    if payload.get("command") != command:
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_redacted": True,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[str(case_id)].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def _negative_rows(payloads: dict[str, object], key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in payloads.values():
        nested = _rows(payload, key)
        if nested:
            rows.extend(nested)
        elif isinstance(payload, dict):
            rows.append(payload)
    return rows


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_replacements = _strings(protocol.get("public_replacement_refs"))
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 5
        or "proof_derived_governed_mutation_authorization_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or len(public_replacements) < 3
        or not _strings(protocol.get("reimplemented"))
        or not _strings(protocol.get("omitted"))
    ):
        findings.append(
            _finding(
                "GOV_MUT_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, projection receipts, public replacements, reimplemented pieces, and omissions.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if protocol.get("copied_private_proof_bodies") is not False:
        findings.append(
            _finding(
                "GOV_MUT_PRIVATE_PROOF_BODY_COPY_CLAIM",
                "Projection protocol must explicitly deny copying private proof bodies or provider payloads.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_replacement_refs": public_replacements,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_authorization_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    allowed_classes = set(_strings(policy.get("allowed_action_classes")))
    required_fields = set(_strings(policy.get("required_proposal_fields")))
    findings: list[dict[str, Any]] = []
    if not set(REQUIRED_ACTION_CLASSES).issubset(allowed_classes):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_CLASSES_INCOMPLETE",
                "Policy must define read-only, scoped write, and rollback action classes.",
                case_id="authorization_policy_floor",
                subject_id=str(policy.get("policy_id") or "authorization_policy"),
                subject_kind="authorization_policy",
            )
        )
    if not set(REQUIRED_PROPOSAL_FIELDS).issubset(required_fields):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Policy must require intent, proof, verdict, side-effect, rollback, cold-replay, redaction, and anti-overclaim fields.",
                case_id="authorization_policy_floor",
                subject_id=str(policy.get("policy_id") or "authorization_policy"),
                subject_kind="authorization_policy",
            )
        )
    if int(policy.get("minimum_independent_verdicts") or 0) < 2:
        findings.append(
            _finding(
                "GOV_MUT_POLICY_CONSENSUS_FLOOR_MISSING",
                "Policy must require at least two visible independent policy verdicts before execution identity is minted.",
                case_id="authorization_policy_floor",
                subject_id="minimum_independent_verdicts",
                subject_kind="authorization_policy",
            )
        )
    for field in (
        "standing_credentials_authorized",
        "live_cloud_account_authorized",
        "policy_after_execution_authorized",
        "hidden_policy_votes_authorized",
        "irreversible_mutation_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "GOV_MUT_POLICY_AUTHORITY_OVERCLAIM",
                    "Governed mutation policy cannot authorize standing credentials, live cloud/account mutation, policy-after-execution, hidden policy votes, irreversible mutation, provider calls, or release.",
                    case_id="authorization_policy_floor",
                    subject_id=field,
                    subject_kind="authorization_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_action_classes": sorted(allowed_classes),
        "required_proposal_fields": sorted(required_fields),
        "minimum_independent_verdicts": int(
            policy.get("minimum_independent_verdicts") or 0
        ),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _build_proof_index(payload: object) -> dict[str, dict[str, Any]]:
    return {str(row.get("proof_cell_id") or ""): row for row in _rows(payload, "proof_cells")}


def _build_verdict_index(payload: object) -> dict[str, dict[str, Any]]:
    return {str(row.get("verdict_id") or ""): row for row in _rows(payload, "verdicts")}


def _visible_allowing_verdict_count(
    refs: list[str],
    verdict_index: dict[str, dict[str, Any]],
) -> int:
    count = 0
    for ref in refs:
        row = verdict_index.get(ref, {})
        if (
            row.get("visible_to_receipt") is True
            and row.get("hidden_policy_vote") is not True
            and row.get("verdict") in {"allow", "warn"}
        ):
            count += 1
    return count


def _proposal_has_evidence(
    refs: list[str],
    proof_index: dict[str, dict[str, Any]],
) -> bool:
    for ref in refs:
        row = proof_index.get(ref, {})
        if (
            _strings(row.get("evidence_refs"))
            and _strings(row.get("validator_receipt_refs"))
            and row.get("body_redacted") is True
            and row.get("private_ref_metadata_only") is True
            and row.get("proof_body_exported") is False
        ):
            return True
    return False


def _validate_proposal_row(
    row: dict[str, Any],
    *,
    proof_index: dict[str, dict[str, Any]],
    verdict_index: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(
        row.get("expected_negative_case_id") or row.get("proposal_id") or "proposal"
    )
    proposal_id = str(row.get("proposal_id") or case_id)
    subject_kind = "negative_case" if negative else "mutation_proposal"
    proof_refs = _strings(row.get("proof_cell_refs"))
    verdict_refs = _strings(row.get("policy_verdict_refs"))
    action_class = str(row.get("action_class") or "")
    side_effect_class = str(row.get("side_effect_class") or "")
    side_effect_ref = str(row.get("side_effect_diff_ref") or "")
    rollback_ref = str(row.get("rollback_receipt_ref") or "")
    reasons: list[str] = []
    missing = [
        field
        for field in REQUIRED_PROPOSAL_FIELDS
        if field not in row or row.get(field) is None
    ]

    if row.get("standing_credential_claimed") is True or row.get(
        "authorization_basis"
    ) == "standing_credential":
        reasons.append("standing_credential_authority")
        _record(
            findings,
            observed,
            "GOV_MUT_STANDING_CREDENTIAL_AUTHORITY",
            "Standing credentials are not mutation authority; authorization must derive from replayable proof and visible verdicts.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("policy_evaluated_before_execution") is not True or row.get(
        "executed_before_policy"
    ) is True:
        reasons.append("policy_after_execution")
        _record(
            findings,
            observed,
            "GOV_MUT_POLICY_AFTER_EXECUTION",
            "Policy evaluation must occur before any execution identity or side-effect metadata is admitted.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("hidden_policy_vote") is True or not verdict_refs:
        reasons.append("hidden_policy_vote")
        _record(
            findings,
            observed,
            "GOV_MUT_HIDDEN_POLICY_VOTE",
            "Policy verdicts must be visible receipt refs; hidden consensus cannot authorize mutation.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("live_cloud_credential_ref") is True or _has_forbidden_key(row):
        reasons.append("live_cloud_credential")
        _record(
            findings,
            observed,
            "GOV_MUT_LIVE_CLOUD_CREDENTIAL",
            "Public governed-mutation fixtures cannot carry live cloud/account credentials or private account refs.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("irreversible_side_effect") is True or (
        side_effect_class in {"scoped_config_write", "rollback"}
        and not rollback_ref
    ):
        reasons.append("irreversible_mutation")
        _record(
            findings,
            observed,
            "GOV_MUT_IRREVERSIBLE_MUTATION",
            "Write or rollback proposals require rollback/verifiability refs and cannot claim irreversible mutation authority.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if side_effect_class in {"scoped_config_write", "rollback"} and (
        not side_effect_ref or row.get("side_effect_logged") is not True
    ):
        reasons.append("unlogged_side_effect")
        _record(
            findings,
            observed,
            "GOV_MUT_UNLOGGED_SIDE_EFFECT",
            "Side effects must be logged with a synthetic diff ref before claim admission.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if (
        not proof_refs
        or not row.get("evidence_chain_hash")
        or not _proposal_has_evidence(proof_refs, proof_index)
        or _visible_allowing_verdict_count(verdict_refs, verdict_index) < 2
    ):
        reasons.append("consensus_without_evidence")
        _record(
            findings,
            observed,
            "GOV_MUT_CONSENSUS_WITHOUT_EVIDENCE",
            "Consensus must cite proof evidence cells, validator receipts, an evidence-chain hash, and two visible verdicts.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("final_answer_only_success") is True:
        reasons.append("final_answer_only_success")
        _record(
            findings,
            observed,
            "GOV_MUT_FINAL_ANSWER_ONLY_SUCCESS",
            "Mutation authorization cannot be graded by final-answer success without proof, verdict, side-effect, rollback, and replay evidence.",
            case_id=case_id,
            subject_id=proposal_id,
            subject_kind=subject_kind,
        )
    if row.get("body_redacted") is not True or row.get("private_ref_metadata_only") is not True:
        reasons.append("unredacted_public_fixture")
    if action_class not in REQUIRED_ACTION_CLASSES:
        reasons.append("unknown_action_class")
    if missing:
        reasons.append("proposal_field_missing")

    return {
        "proposal_id": proposal_id,
        "action_class": action_class,
        "intent_capsule_ref": row.get("intent_capsule_ref"),
        "authority_ceiling_ref": row.get("authority_ceiling_ref"),
        "proof_cell_refs": proof_refs,
        "policy_verdict_refs": verdict_refs,
        "ephemeral_identity_ref": row.get("ephemeral_identity_ref"),
        "side_effect_class": side_effect_class,
        "side_effect_diff_ref": side_effect_ref,
        "rollback_receipt_ref": rollback_ref,
        "policy_evaluated_before_execution": (
            row.get("policy_evaluated_before_execution") is True
        ),
        "execution_state": str(row.get("execution_state") or ""),
        "evidence_chain_hash": row.get("evidence_chain_hash"),
        "cold_replay_ref": row.get("cold_replay_ref"),
        "computed_verdict": (
            "authorized_synthetic_mutation_metadata" if not reasons else "blocked"
        ),
        "reason_codes": sorted(set(reasons)),
        "missing_required_fields": missing,
        "body_redacted": True,
    }


def validate_proof_evidence_cells(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "proof_cells")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        proof_id = str(row.get("proof_cell_id") or "")
        reasons: list[str] = []
        if not row.get("proposal_id"):
            reasons.append("missing_proposal_ref")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        if not _strings(row.get("validator_receipt_refs")):
            reasons.append("missing_validator_receipt_refs")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if row.get("private_ref_metadata_only") is not True:
            reasons.append("private_ref_not_metadata_only")
        if row.get("proof_body_exported") is not False:
            reasons.append("proof_body_exported")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "proof_cell_id": proof_id,
                "proposal_id": row.get("proposal_id"),
                "evidence_kind": row.get("evidence_kind"),
                "evidence_ref_count": len(_strings(row.get("evidence_refs"))),
                "validator_receipt_ref_count": len(
                    _strings(row.get("validator_receipt_refs"))
                ),
                "computed_verdict": "accepted_proof_cell" if not reasons else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) < 3 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_PROOF_CELL_FLOOR_MISSING",
                "Positive fixture must expose redacted proof cells with evidence refs and validator receipt refs for each proposed action.",
                case_id="proof_cell_floor",
                subject_id="proof_evidence_cells",
                subject_kind="proof_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "proof_cell_count": len(rows),
        "accepted_proof_cell_count": sum(1 for row in accepted if not row["reason_codes"]),
        "proof_cell_rows": sorted(accepted, key=lambda row: row["proof_cell_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_policy_verdicts(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "verdicts")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    by_proposal: dict[str, int] = defaultdict(int)
    for row in rows:
        verdict_id = str(row.get("verdict_id") or "")
        proposal_id = str(row.get("proposal_id") or "")
        reasons: list[str] = []
        if row.get("verdict") not in {"allow", "warn", "block", "review"}:
            reasons.append("unknown_verdict")
        if row.get("visible_to_receipt") is not True:
            reasons.append("hidden_vote")
        if row.get("hidden_policy_vote") is True:
            reasons.append("hidden_policy_vote")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if not reasons and row.get("verdict") in {"allow", "warn"}:
            by_proposal[proposal_id] += 1
        accepted.append(
            {
                "verdict_id": verdict_id,
                "proposal_id": proposal_id,
                "evaluator_id": row.get("evaluator_id"),
                "verdict": row.get("verdict"),
                "visible_to_receipt": row.get("visible_to_receipt") is True,
                "computed_verdict": "accepted_policy_verdict" if not reasons else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) < 6 or any(count < 2 for count in by_proposal.values()):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_VERDICT_FLOOR_MISSING",
                "Positive fixture must carry at least two visible allow/warn verdicts per authorized proposal.",
                case_id="policy_verdict_floor",
                subject_id="policy_verdicts",
                subject_kind="policy_verdict_fixture",
            )
        )
    if any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_POLICY_VERDICT_INVALID",
                "Positive policy verdict rows must be visible, redacted, evidence-backed receipt refs.",
                case_id="policy_verdict_floor",
                subject_id="policy_verdicts",
                subject_kind="policy_verdict_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "policy_verdict_count": len(rows),
        "visible_policy_verdict_count": sum(
            1 for row in accepted if row["visible_to_receipt"]
        ),
        "proposal_consensus_counts": dict(sorted(by_proposal.items())),
        "policy_verdict_rows": sorted(accepted, key=lambda row: row["verdict_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_mutation_proposals(
    payload: object,
    proof_payload: object,
    verdict_payload: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    proof_index = _build_proof_index(proof_payload)
    verdict_index = _build_verdict_index(verdict_payload)
    rows = [
        _validate_proposal_row(
            row,
            proof_index=proof_index,
            verdict_index=verdict_index,
            findings=findings,
            observed=observed,
            negative=False,
        )
        for row in _rows(payload, "mutation_proposals")
    ]
    for row in _negative_rows(negative_payloads, "mutation_proposals"):
        _validate_proposal_row(
            row,
            proof_index=proof_index,
            verdict_index=verdict_index,
            findings=findings,
            observed=observed,
            negative=True,
        )

    authorized = [row for row in rows if not row["reason_codes"]]
    write_or_rollback = [
        row
        for row in authorized
        if row["side_effect_class"] in {"scoped_config_write", "rollback"}
    ]
    action_classes = {row["action_class"] for row in authorized}
    floor_blocked = (
        len(authorized) != 3
        or not set(REQUIRED_ACTION_CLASSES).issubset(action_classes)
        or len(write_or_rollback) != 2
    )
    positive_findings = [row for row in rows if row["reason_codes"]]
    if floor_blocked and not positive_findings:
        findings.append(
            _finding(
                "GOV_MUT_PROPOSAL_FLOOR_MISSING",
                "Positive fixture must authorize read-only, scoped write, and rollback proposal metadata with proof, visible verdict, side-effect, rollback, and replay refs.",
                case_id="mutation_proposal_floor",
                subject_id="mutation_proposals",
                subject_kind="mutation_proposal_fixture",
            )
        )
    return {
        "status": PASS if not floor_blocked and not positive_findings else "blocked",
        "proposal_count": len(rows),
        "authorized_mutation_count": len(authorized),
        "write_or_rollback_count": len(write_or_rollback),
        "action_classes": sorted(action_classes),
        "proposal_rows": sorted(rows, key=lambda row: row["proposal_id"]),
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def validate_side_effect_ledger(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "side_effects")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if row.get("synthetic_side_effect") is not True:
            reasons.append("not_synthetic")
        if row.get("side_effect_logged") is not True:
            reasons.append("not_logged")
        if row.get("reversible") is not True:
            reasons.append("not_reversible")
        if not row.get("diff_ref"):
            reasons.append("missing_diff_ref")
        if not row.get("rollback_receipt_ref"):
            reasons.append("missing_rollback_receipt_ref")
        if row.get("live_cloud_account_touched") is True:
            reasons.append("live_cloud_account_touched")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "side_effect_id": str(row.get("side_effect_id") or ""),
                "proposal_id": row.get("proposal_id"),
                "side_effect_class": row.get("side_effect_class"),
                "diff_ref": row.get("diff_ref"),
                "rollback_receipt_ref": row.get("rollback_receipt_ref"),
                "synthetic_side_effect": row.get("synthetic_side_effect") is True,
                "computed_verdict": "accepted_side_effect_metadata"
                if not reasons
                else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) != 2 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_SIDE_EFFECT_LEDGER_FLOOR_MISSING",
                "Positive fixture must expose two logged, reversible synthetic side-effect refs: scoped write and rollback.",
                case_id="side_effect_floor",
                subject_id="side_effect_ledger",
                subject_kind="side_effect_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "side_effect_count": len(rows),
        "logged_side_effect_count": sum(
            1 for row in accepted if row["computed_verdict"] == "accepted_side_effect_metadata"
        ),
        "side_effect_rows": sorted(accepted, key=lambda row: row["side_effect_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_rollback_receipts(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "rollback_receipts")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if row.get("rollback_status") != PASS:
            reasons.append("rollback_not_pass")
        if not row.get("rollback_receipt_ref"):
            reasons.append("missing_rollback_receipt_ref")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        if row.get("irreversible_mutation_authorized") is not False:
            reasons.append("irreversible_authority_overclaim")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "rollback_id": str(row.get("rollback_id") or ""),
                "proposal_id": row.get("proposal_id"),
                "rollback_status": row.get("rollback_status"),
                "rollback_receipt_ref": row.get("rollback_receipt_ref"),
                "evidence_ref_count": len(_strings(row.get("evidence_refs"))),
                "computed_verdict": "accepted_rollback_receipt"
                if not reasons
                else "blocked",
                "reason_codes": sorted(reasons),
                "body_redacted": True,
            }
        )
    if len(rows) < 2 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "GOV_MUT_ROLLBACK_RECEIPT_FLOOR_MISSING",
                "Positive fixture must carry passing rollback receipts for scoped write and rollback verification.",
                case_id="rollback_floor",
                subject_id="rollback_receipts",
                subject_kind="rollback_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "rollback_receipt_count": len(rows),
        "rollback_pass_count": sum(
            1 for row in accepted if row["computed_verdict"] == "accepted_rollback_receipt"
        ),
        "rollback_rows": sorted(accepted, key=lambda row: row["rollback_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_cold_replay(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "cold_replays")
    findings: list[dict[str, Any]] = []
    passing = [
        row
        for row in rows
        if row.get("status") == PASS
        and row.get("body_redacted") is True
        and row.get("private_ref_metadata_only") is True
    ]
    if len(passing) < 3:
        findings.append(
            _finding(
                "GOV_MUT_COLD_REPLAY_FLOOR_MISSING",
                "Positive fixture must include redacted cold replay receipts for read-only, write, and rollback proposal paths.",
                case_id="cold_replay_floor",
                subject_id="cold_replay",
                subject_kind="cold_replay_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "cold_replay_count": len(rows),
        "cold_replay_pass_count": len(passing),
        "cold_replay_rows": [
            {
                "replay_id": str(row.get("replay_id") or ""),
                "proposal_id": str(row.get("proposal_id") or ""),
                "status": row.get("status"),
                "evidence_refs": _strings(row.get("evidence_refs")),
                "body_redacted": row.get("body_redacted") is True,
                "private_ref_metadata_only": row.get("private_ref_metadata_only") is True,
            }
            for row in rows
        ],
        "findings": findings,
        "observed_negative_cases": {},
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    private_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    projection = validate_projection_protocol(payloads["projection_protocol"])
    auth_policy = validate_authorization_policy(payloads["authorization_policy"])
    proof_cells = validate_proof_evidence_cells(payloads["proof_evidence_cells"])
    verdicts = validate_policy_verdicts(payloads["policy_verdicts"])
    proposals = validate_mutation_proposals(
        payloads["mutation_proposals"],
        payloads["proof_evidence_cells"],
        payloads["policy_verdicts"],
        negative_payloads,
    )
    side_effects = validate_side_effect_ledger(payloads["side_effect_ledger"])
    rollbacks = validate_rollback_receipts(payloads["rollback_receipts"])
    cold_replay = validate_cold_replay(payloads["cold_replay"])

    observed = _merge_observed(
        projection,
        auth_policy,
        proof_cells,
        verdicts,
        proposals,
        side_effects,
        rollbacks,
        cold_replay,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        auth_policy,
        proof_cells,
        verdicts,
        proposals,
        side_effects,
        rollbacks,
        cold_replay,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and auth_policy["status"] == PASS
        and proof_cells["status"] == PASS
        and verdicts["status"] == PASS
        and proposals["status"] == PASS
        and side_effects["status"] == PASS
        and rollbacks["status"] == PASS
        and cold_replay["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "proof_derived_governed_mutation_authorization_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id")
        if isinstance(bundle_manifest, dict)
        else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_replacement_refs": projection["public_replacement_refs"],
        "authorization_policy_id": auth_policy["policy_id"],
        "allowed_action_classes": auth_policy["allowed_action_classes"],
        "minimum_independent_verdicts": auth_policy["minimum_independent_verdicts"],
        "proof_cell_count": proof_cells["proof_cell_count"],
        "accepted_proof_cell_count": proof_cells["accepted_proof_cell_count"],
        "policy_verdict_count": verdicts["policy_verdict_count"],
        "visible_policy_verdict_count": verdicts["visible_policy_verdict_count"],
        "proposal_consensus_counts": verdicts["proposal_consensus_counts"],
        "proposal_count": proposals["proposal_count"],
        "authorized_mutation_count": proposals["authorized_mutation_count"],
        "write_or_rollback_count": proposals["write_or_rollback_count"],
        "action_classes": proposals["action_classes"],
        "side_effect_count": side_effects["side_effect_count"],
        "logged_side_effect_count": side_effects["logged_side_effect_count"],
        "rollback_receipt_count": rollbacks["rollback_receipt_count"],
        "rollback_pass_count": rollbacks["rollback_pass_count"],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "proof_cell_rows": proof_cells["proof_cell_rows"],
        "policy_verdict_rows": verdicts["policy_verdict_rows"],
        "proposal_rows": proposals["proposal_rows"],
        "side_effect_rows": side_effects["side_effect_rows"],
        "rollback_rows": rollbacks["rollback_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "proof_derived_governed_mutation_authorization_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "proof_derived_governed_mutation_authorization_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "standing_credentials_rejected_before_authorization",
                "count": result["authorized_mutation_count"],
                "authority": "mutation authority derives from proof cells and visible verdicts, not credential possession",
            },
            {
                "mechanic_id": "consensus_before_ephemeral_identity",
                "count": result["visible_policy_verdict_count"],
                "authority": "at least two visible verdict refs precede synthetic execution identity refs",
            },
            {
                "mechanic_id": "side_effects_need_diff_and_rollback",
                "count": result["logged_side_effect_count"],
                "authority": "write and rollback proposal metadata needs logged diffs and rollback receipts",
            },
            {
                "mechanic_id": "cold_replay_before_claim_admission",
                "count": result["cold_replay_pass_count"],
                "authority": "governed-mutation language requires cold replay receipts",
            },
        ],
        "proposal_rows": result["proposal_rows"],
        "proof_cell_rows": result["proof_cell_rows"],
        "policy_verdict_rows": result["policy_verdict_rows"],
        "side_effect_rows": result["side_effect_rows"],
        "rollback_rows": result["rollback_rows"],
        "cold_replay_rows": result["cold_replay_rows"],
        "body_redacted": True,
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": (
            "proof_derived_governed_mutation_authorization_result_receipt_v1"
        ),
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": (
            "proof_derived_governed_mutation_authorization_validation_receipt_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "proposal_count": result["proposal_count"],
        "authorized_mutation_count": result["authorized_mutation_count"],
        "proof_cell_count": result["proof_cell_count"],
        "visible_policy_verdict_count": result["visible_policy_verdict_count"],
        "logged_side_effect_count": result["logged_side_effect_count"],
        "rollback_pass_count": result["rollback_pass_count"],
        "cold_replay_pass_count": result["cold_replay_pass_count"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": (
            "proof_derived_governed_mutation_authorization_fixture_acceptance_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "authorization_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs."
        "proof_derived_governed_mutation_authorization run"
    ),
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_authorization_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "proof_derived_governed_mutation_authorization run-authorization-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    source = Path(input_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if reuse_fresh_receipt:
        cached = _fresh_authorization_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_governed_mutation_authorization_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": (
            "exported_governed_mutation_authorization_bundle_validation_result_v1"
        ),
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    private_scan_payload = result.get("private_state_scan")
    private_scan = private_scan_payload if isinstance(private_scan_payload, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "governed_mutation_authorization": {
            "proposal_count": result.get("proposal_count"),
            "authorized_mutation_count": result.get("authorized_mutation_count"),
            "write_or_rollback_count": result.get("write_or_rollback_count"),
            "proof_cell_count": result.get("proof_cell_count"),
            "accepted_proof_cell_count": result.get("accepted_proof_cell_count"),
            "policy_verdict_count": result.get("policy_verdict_count"),
            "visible_policy_verdict_count": result.get(
                "visible_policy_verdict_count"
            ),
            "logged_side_effect_count": result.get("logged_side_effect_count"),
            "rollback_pass_count": result.get("rollback_pass_count"),
            "cold_replay_pass_count": result.get("cold_replay_pass_count"),
        },
        "negative_case_coverage": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "observed_negative_case_count": len(
                result.get("observed_negative_cases") or {}
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
        },
        "validation": {
            "private_state_blocking_hit_count": private_scan.get(
                "blocking_hit_count"
            ),
            "bundle_id": result.get("bundle_id"),
        },
        "body_floor": {
            "proof_cell_rows_in_card": False,
            "policy_verdict_rows_in_card": False,
            "proposal_rows_in_card": False,
            "side_effect_rows_in_card": False,
            "rollback_rows_in_card": False,
            "cold_replay_rows_in_card": False,
            "private_state_scan_in_card": False,
            "authority_ceiling_in_card": False,
            "anti_claim_in_card": False,
            "authorization_board_in_card": False,
        },
        "authority_boundary": {
            "synthetic_receipts_only": True,
            "live_cloud_account_authorized": False,
            "standing_credentials_authorized": False,
            "source_mutation_authorized": False,
            "irreversible_mutation_authorized": False,
            "policy_after_execution_authorized": False,
            "hidden_policy_votes_authorized": False,
            "provider_calls_authorized": False,
            "benchmark_score_claim_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": (
                "rerun without --card or inspect the written receipt file"
            ),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proof_derived_governed_mutation_authorization"
    )
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-authorization-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        command = (
            "proof_derived_governed_mutation_authorization run"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-authorization-bundle":
        command = (
            "proof_derived_governed_mutation_authorization "
            f"run-authorization-bundle{card_suffix}"
        )
        result = run_authorization_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    output = result_card(result) if args.card else result["status"]
    print(json.dumps(output, indent=2, sort_keys=True) if args.card else output)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
