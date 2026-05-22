from __future__ import annotations

import argparse
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


ORGAN_ID = "world_model_projection_drift_control_room"
FIXTURE_ID = "first_wave.world_model_projection_drift_control_room"
VALIDATOR_ID = "validator.microcosm.organs.world_model_projection_drift_control_room"

RESULT_NAME = "world_model_projection_drift_control_room_result.json"
BOARD_NAME = "world_model_projection_drift_control_room_board.json"
VALIDATION_RECEIPT_NAME = "world_model_projection_drift_control_room_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "world_model_projection_drift_control_room_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_projection_drift_control_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "drift_policy.json",
    "drift_rows.json",
)
NEGATIVE_INPUT_NAMES = (
    "drift_row_without_source_ref.json",
    "repair_route_without_validation_ref.json",
    "projection_claiming_source_authority.json",
    "live_repair_action_authorized.json",
    "private_runtime_data_export.json",
    "provider_payload_export.json",
    "automatic_doctrine_promotion.json",
    "release_from_drift_projection.json",
)

EXPECTED_NEGATIVE_CASES = {
    "drift_row_without_source_ref": ["DRIFT_SOURCE_REF_REQUIRED"],
    "repair_route_without_validation_ref": ["DRIFT_VALIDATION_REF_REQUIRED"],
    "projection_claiming_source_authority": ["DRIFT_SOURCE_AUTHORITY_FORBIDDEN"],
    "live_repair_action_authorized": ["DRIFT_LIVE_REPAIR_FORBIDDEN"],
    "private_runtime_data_export": ["DRIFT_PRIVATE_RUNTIME_EXPORT_FORBIDDEN"],
    "provider_payload_export": ["DRIFT_PROVIDER_PAYLOAD_FORBIDDEN"],
    "automatic_doctrine_promotion": ["DRIFT_AUTOMATIC_DOCTRINE_PROMOTION_FORBIDDEN"],
    "release_from_drift_projection": ["DRIFT_RELEASE_AUTHORITY_FORBIDDEN"],
}

REQUIRED_ROW_FIELDS = (
    "drift_row_id",
    "source_signal",
    "source_ref",
    "repair_route",
    "validation_ref",
    "public_replacement_ref",
    "body_redacted",
    "source_authority_claim",
    "live_repair_authorized",
    "source_mutation_authorized",
    "automatic_doctrine_promotion_authorized",
)
PRIVATE_NEEDLES = (
    "/Users/",
    "src/ai_workflow",
    "Library/Application Support/Google",
    "sk-",
    "private_runtime_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_projection_drift_control_metadata_only",
    "metadata_projection_only": True,
    "release_authorized": False,
    "hosted_public_authorized": False,
    "publication_authorized": False,
    "provider_calls_authorized": False,
    "provider_payload_exported": False,
    "source_authority_claim": False,
    "source_mutation_authorized": False,
    "live_route_repair_authorized": False,
    "live_task_ledger_mutation_authorized": False,
    "private_runtime_data_exported": False,
    "proof_body_exported": False,
    "automatic_doctrine_promotion_authorized": False,
}
ANTI_CLAIM = (
    "World-model projection drift control validates synthetic metadata rows that "
    "name source signals, repair routes, validation refs, and omission boundaries. "
    "It does not inspect private runtime bodies, repair live routes, mutate source, "
    "promote doctrine, export provider payloads, claim source authority, or "
    "authorize release."
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
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


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
    if case_id in EXPECTED_NEGATIVE_CASES:
        observed[case_id].add(code)


def _row_policy_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("drift_row_id") or case_id)
    for field in REQUIRED_ROW_FIELDS:
        if field not in row:
            code = "DRIFT_SOURCE_REF_REQUIRED" if field == "source_ref" else "DRIFT_ROW_FIELD_REQUIRED"
            _record(
                findings,
                observed,
                code,
                f"drift row is missing required field {field}",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="drift_row",
            )
    if not row.get("source_ref"):
        _record(
            findings,
            observed,
            "DRIFT_SOURCE_REF_REQUIRED",
            "drift rows must cite a public-safe source reference",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if not row.get("repair_route") or not row.get("validation_ref"):
        _record(
            findings,
            observed,
            "DRIFT_VALIDATION_REF_REQUIRED",
            "drift rows must cite both a repair route and a validation reference",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    bool_forbidden = {
        "source_authority_claim": "DRIFT_SOURCE_AUTHORITY_FORBIDDEN",
        "live_repair_authorized": "DRIFT_LIVE_REPAIR_FORBIDDEN",
        "source_mutation_authorized": "DRIFT_SOURCE_MUTATION_FORBIDDEN",
        "automatic_doctrine_promotion_authorized": "DRIFT_AUTOMATIC_DOCTRINE_PROMOTION_FORBIDDEN",
        "release_authorized": "DRIFT_RELEASE_AUTHORITY_FORBIDDEN",
    }
    for field, code in bool_forbidden.items():
        if row.get(field) is True:
            _record(
                findings,
                observed,
                code,
                f"{field} must be false for public projection drift rows",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="drift_row",
            )
    if row.get("body_redacted") is not True:
        _record(
            findings,
            observed,
            "DRIFT_BODY_REDACTION_REQUIRED",
            "drift rows must be body-redacted metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if row.get("private_runtime_data") or any(
        needle in json.dumps(row, sort_keys=True) for needle in PRIVATE_NEEDLES
    ):
        _record(
            findings,
            observed,
            "DRIFT_PRIVATE_RUNTIME_EXPORT_FORBIDDEN",
            "private runtime data cannot enter the public drift control room",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    if row.get("provider_payload") or row.get("provider_payload_exported") is True:
        _record(
            findings,
            observed,
            "DRIFT_PROVIDER_PAYLOAD_FORBIDDEN",
            "provider payloads cannot enter the public drift control room",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="drift_row",
        )
    return findings


def _required_policy_ok(policy: dict[str, Any]) -> bool:
    ceiling = policy.get("authority_ceiling")
    if not isinstance(ceiling, dict):
        return False
    return (
        ceiling.get("metadata_projection_only") is True
        and all(
            value is False
            for key, value in ceiling.items()
            if key != "metadata_projection_only"
        )
    )


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    public_root = _public_root_for_path(input_dir)
    projection_protocol = payloads.get("projection_protocol", {})
    drift_policy = payloads.get("drift_policy", {})
    drift_rows = _rows(payloads.get("drift_rows", {}), "drift_rows")
    observed_negative_codes: dict[str, set[str]] = defaultdict(set)
    positive_findings: list[dict[str, Any]] = []

    if not isinstance(projection_protocol, dict) or projection_protocol.get("selected_route_id") != "world_model_projection_drift_control_room":
        positive_findings.append(
            _finding(
                "DRIFT_PROTOCOL_ROUTE_REQUIRED",
                "projection protocol must select world_model_projection_drift_control_room",
                case_id="positive_fixture",
                subject_id="projection_protocol",
                subject_kind="protocol",
            )
        )
    if not _required_policy_ok(drift_policy if isinstance(drift_policy, dict) else {}):
        positive_findings.append(
            _finding(
                "DRIFT_AUTHORITY_CEILING_REQUIRED",
                "drift policy must declare metadata-only authority ceiling",
                case_id="positive_fixture",
                subject_id="drift_policy",
                subject_kind="policy",
            )
        )
    for row in drift_rows:
        row_findings = _row_policy_findings(
            row,
            case_id="positive_fixture",
            observed=observed_negative_codes,
        )
        positive_findings.extend(row_findings)
    selected_pattern_ids = _strings(projection_protocol.get("selected_pattern_ids"))
    row_ids = [str(row.get("drift_row_id")) for row in drift_rows if row.get("drift_row_id")]
    if selected_pattern_ids and selected_pattern_ids != row_ids:
        positive_findings.append(
            _finding(
                "DRIFT_SELECTED_PATTERN_IDS_MISMATCH",
                "selected_pattern_ids must exactly match validated drift row ids",
                case_id="positive_fixture",
                subject_id="projection_protocol",
                subject_kind="protocol",
            )
        )

    negative_findings: list[dict[str, Any]] = []
    if include_negative:
        for name in NEGATIVE_INPUT_NAMES:
            case_id = Path(name).stem
            payload = payloads.get(case_id, {})
            row_payload = payload.get("drift_row", payload) if isinstance(payload, dict) else {}
            if isinstance(row_payload, dict):
                negative_findings.extend(
                    _row_policy_findings(
                        row_payload,
                        case_id=case_id,
                        observed=observed_negative_codes,
                    )
                )

    expected_cases = EXPECTED_NEGATIVE_CASES if include_negative else {}
    expected_missing = {
        case_id: sorted(set(codes) - observed_negative_codes.get(case_id, set()))
        for case_id, codes in expected_cases.items()
    }
    expected_missing = {case_id: codes for case_id, codes in expected_missing.items() if codes}
    encoded_positive = json.dumps(drift_rows, sort_keys=True)
    body_redacted = not any(needle in encoded_positive for needle in PRIVATE_NEEDLES)
    policy_passed = (
        bool(drift_rows)
        and not positive_findings
        and body_redacted
        and not expected_missing
        and all(row.get("body_redacted") is True for row in drift_rows)
        and all(row.get("source_authority_claim") is False for row in drift_rows)
        and all(row.get("live_repair_authorized") is False for row in drift_rows)
        and all(row.get("source_mutation_authorized") is False for row in drift_rows)
        and all(
            row.get("automatic_doctrine_promotion_authorized") is False
            for row in drift_rows
        )
    )

    scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    status = PASS if policy_passed and scan.get("status") == PASS else "blocked"
    return {
        "schema_version": "world_model_projection_drift_control_room_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "input_ref": _display(input_dir, public_root=public_root),
        "selected_route_id": "world_model_projection_drift_control_room",
        "selected_pattern_ids": row_ids,
        "drift_rows": drift_rows,
        "drift_summary": {
            "row_count": len(drift_rows),
            "source_ref_count": sum(1 for row in drift_rows if row.get("source_ref")),
            "repair_route_count": sum(1 for row in drift_rows if row.get("repair_route")),
            "validation_ref_count": sum(1 for row in drift_rows if row.get("validation_ref")),
            "source_authority_claim_count": sum(1 for row in drift_rows if row.get("source_authority_claim") is True),
            "live_repair_authorized_count": sum(1 for row in drift_rows if row.get("live_repair_authorized") is True),
            "source_mutation_authorized_count": sum(1 for row in drift_rows if row.get("source_mutation_authorized") is True),
            "automatic_doctrine_promotion_count": sum(1 for row in drift_rows if row.get("automatic_doctrine_promotion_authorized") is True),
            "private_runtime_data_export_count": 0,
            "provider_payload_export_count": 0,
        },
        "negative_case_summary": {
            "expected_negative_case_count": len(expected_cases),
            "observed_negative_case_count": sum(
                1 for case_id in expected_cases if observed_negative_codes.get(case_id)
            ),
            "expected_missing": expected_missing,
            "observed_codes": {
                case_id: sorted(codes)
                for case_id, codes in sorted(observed_negative_codes.items())
                if case_id in expected_cases
            },
        },
        "finding_count": len(positive_findings),
        "positive_findings": positive_findings,
        "negative_case_findings": negative_findings,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "safe_to_show": {
            "body_redacted": body_redacted,
            "metadata_only": True,
            "private_runtime_bodies_omitted": True,
            "provider_payloads_omitted": True,
            "live_repair_actions_omitted": True,
            "source_mutation_omitted": True,
        },
        "release_authorized": False,
        "body_redacted": True,
        "private_state_scan": scan,
    }


def _board(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("drift_summary", {})
    negatives = result.get("negative_case_summary", {})
    return {
        "schema_version": "world_model_projection_drift_control_room_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "world_model_projection_drift_control_public_board",
        "route": "world_model_projection_drift_control_room",
        "row_count": summary.get("row_count", 0) if isinstance(summary, dict) else 0,
        "source_ref_count": summary.get("source_ref_count", 0) if isinstance(summary, dict) else 0,
        "repair_route_count": summary.get("repair_route_count", 0) if isinstance(summary, dict) else 0,
        "validation_ref_count": summary.get("validation_ref_count", 0) if isinstance(summary, dict) else 0,
        "negative_case_count": negatives.get("expected_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "observed_negative_case_count": negatives.get("observed_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
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
    board = _board(result)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
    ]
    validation = {
        "schema_version": "world_model_projection_drift_control_room_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "receipt_paths": receipt_paths,
        "row_count": (result.get("drift_summary") or {}).get("row_count"),
        "expected_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "expected_negative_case_count"
        ),
        "observed_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "observed_negative_case_count"
        ),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "release_authorized": False,
    }
    write_json_atomic(result_path, result)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    if acceptance_out is not None:
        acceptance_path = acceptance_out
        acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        acceptance_path = public_root / ACCEPTANCE_RECEIPT_REL
    acceptance = {
        "schema_version": "world_model_projection_drift_control_room_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "validation_ref": receipt_paths[2],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "release_authorized": False,
        "body_redacted": True,
    }
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "drift_control_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.world_model_projection_drift_control_room run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_drift_control_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.world_model_projection_drift_control_room "
        "run-drift-control-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_projection_drift_control_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_projection_drift_control_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="world_model_projection_drift_control_room")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-drift-control-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-drift-control-bundle":
        result = run_drift_control_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
