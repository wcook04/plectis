from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "standards_meta_diagnostics"
FIXTURE_ID = "first_wave.standards_meta_diagnostics"
VALIDATOR_ID = "validator.microcosm.organs.standards_meta_diagnostics"

RESULT_NAME = "standards_meta_diagnostics_result.json"
BOARD_NAME = "standards_meta_diagnostics_board.json"
VALIDATION_RECEIPT_NAME = "standards_meta_diagnostics_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "standards_meta_diagnostics_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_standards_meta_diagnostics_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "standards_meta_diagnostics_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "covered_organ_ids",
    "findings",
    "secret_exclusion_scan",
    "expected_negative_cases",
    "observed_negative_cases",
    "source_refs",
    "public_runtime_refs",
    "anti_claim",
    "authority_ceiling",
)

SOURCE_PATTERN_IDS = [
    "standards_meta_diagnostics",
    "checkpoint_solo_dev_three_lanes",
    "compression_profile_governed_option_surface",
]
SOURCE_REFS = [
    "microcosm-substrate/core/standards_registry.json",
    "microcosm-substrate/core/organ_registry.json",
    "microcosm-substrate/core/preflight_support/organ_fixture_validator_readiness_v1.json",
]
PUBLIC_RUNTIME_REFS = [
    "core/standards_registry.json",
    "core/organ_registry.json",
    "core/acceptance/first_wave_acceptance.json",
    "core/preflight_support/organ_fixture_validator_readiness_v1.json",
    "fixtures/first_wave/standards_meta_diagnostics/input/standards_inventory.json",
    "fixtures/first_wave/standards_meta_diagnostics/input/organ_runtime_contracts.json",
    "fixtures/first_wave/standards_meta_diagnostics/input/diagnostic_policy.json",
    "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle",
    "paper_modules/standards_meta_diagnostics.md",
]

INPUT_NAMES = (
    "standards_inventory.json",
    "organ_runtime_contracts.json",
    "diagnostic_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "missing_standard_ref.json",
    "unmapped_accepted_organ.json",
    "missing_receipt_ref.json",
    "release_overclaim.json",
    "private_source_leakage.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "missing_standard_ref": ["STANDARDS_META_MISSING_STANDARD_REF"],
    "unmapped_accepted_organ": ["STANDARDS_META_UNMAPPED_ACCEPTED_ORGAN"],
    "missing_receipt_ref": ["STANDARDS_META_MISSING_RECEIPT_REF"],
    "release_overclaim": ["STANDARDS_META_AUTHORITY_OVERCLAIM"],
    "private_source_leakage": ["STANDARDS_META_PRIVATE_SOURCE_FORBIDDEN"],
}

FORBIDDEN_PRIVATE_KEYS = (
    "private_source_body",
    "private_source_body_present",
    "raw_seed_body",
    "provider_payload_body",
    "secret_value",
)
OVERCLAIM_KEYS = (
    "release_authorized",
    "publication_authorized",
    "provider_calls_authorized",
    "private_data_equivalence_claim",
    "whole_system_correctness_claim",
    "trading_or_financial_advice_authorized",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "standards_meta_diagnostics_projection_only_not_registry_authority",
    "standards_registry_authority": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "provider_calls_authorized": False,
    "private_data_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Standards meta diagnostics summarizes public Microcosm standard, organ, "
    "runtime-contract, and receipt coverage only. It does not become source "
    "authority for the registries, expose private macro sources, authorize "
    "release, call providers, prove theorem correctness, or claim whole-system "
    "correctness."
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
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _freshness_input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    paths = _input_paths(input_dir, include_negative=include_negative)
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for path in _freshness_input_paths(source, include_negative=include_negative):
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
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": (
                    "standards_meta_diagnostics_result_v1"
                    if include_negative
                    else "exported_standards_meta_diagnostics_bundle_validation_result_v1"
                ),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "standards_meta_diagnostics_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": (
            "standards_meta_diagnostics_result_v1"
            if include_negative
            else "exported_standards_meta_diagnostics_bundle_validation_result_v1"
        ),
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
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
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for child in value.values():
            rows.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_walk_dicts(child))
    return rows


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
        "body_in_receipt": False,
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


def _contract_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "runtime_contracts")
    if rows:
        return rows
    return _rows(payload, "rows")


def _inventory_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "standards_inventory")
    if rows:
        return rows
    return _rows(payload, "rows")


def _positive_findings(
    *,
    inventory_rows: list[dict[str, Any]],
    runtime_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    accepted_organs = [
        str(organ_id)
        for organ_id in policy.get("accepted_organ_ids", [])
        if isinstance(organ_id, str)
    ]
    inventory_by_id = {
        str(row.get("organ_id") or ""): row
        for row in inventory_rows
        if row.get("organ_id")
    }
    runtime_by_id = {
        str(row.get("organ_id") or ""): row
        for row in runtime_rows
        if row.get("organ_id")
    }
    for organ_id in accepted_organs:
        row = inventory_by_id.get(organ_id)
        runtime = runtime_by_id.get(organ_id)
        if row is None:
            _record(
                findings,
                observed,
                "STANDARDS_META_UNMAPPED_ACCEPTED_ORGAN",
                "Every accepted organ must have a standards inventory row.",
                case_id="positive_inventory",
                subject_id=organ_id,
                subject_kind="organ_id",
            )
            continue
        for field in ("standard_id", "standard_ref", "registry_row_ref"):
            if not row.get(field):
                _record(
                    findings,
                    observed,
                    "STANDARDS_META_MISSING_STANDARD_REF",
                    "Each accepted organ must map to standard_id, standard_ref, and registry row.",
                    case_id="positive_inventory",
                    subject_id=organ_id,
                    subject_kind=field,
                )
        receipts = row.get("receipt_refs", [])
        if not isinstance(receipts, list) or not receipts:
            _record(
                findings,
                observed,
                "STANDARDS_META_MISSING_RECEIPT_REF",
                "Each accepted organ must carry at least one current receipt ref.",
                case_id="positive_inventory",
                subject_id=organ_id,
                subject_kind="receipt_refs",
            )
        if runtime is None or not runtime.get("cli_command") or not runtime.get("runtime_step"):
            _record(
                findings,
                observed,
                "STANDARDS_META_RUNTIME_CONTRACT_MISSING",
                "Every accepted organ must have a CLI command and runtime step contract.",
                case_id="positive_inventory",
                subject_id=organ_id,
                subject_kind="runtime_contract",
            )
    for field in OVERCLAIM_KEYS:
        if policy.get(field) is True:
            _record(
                findings,
                observed,
                "STANDARDS_META_AUTHORITY_OVERCLAIM",
                "Diagnostic policy cannot authorize release, provider calls, or global correctness.",
                case_id="positive_policy",
                subject_id=field,
                subject_kind="authority_ceiling",
            )
    return findings


def _negative_findings(payloads: dict[str, Any], *, known_organs: set[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        payload = payloads.get(stem)
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("expected_negative_case_id") or stem)
        if stem == "missing_standard_ref":
            for row in _inventory_rows(payload) or _walk_dicts(payload):
                organ_id = str(row.get("organ_id") or "organ")
                if not row.get("standard_ref") or not row.get("standard_id"):
                    _record(
                        findings,
                        observed,
                        "STANDARDS_META_MISSING_STANDARD_REF",
                        "Accepted organ standards inventory row omitted a standard reference.",
                        case_id=case_id,
                        subject_id=organ_id,
                        subject_kind="standard_ref",
                    )
        elif stem == "unmapped_accepted_organ":
            accepted = {
                str(organ_id)
                for organ_id in payload.get("accepted_organ_ids", [])
                if isinstance(organ_id, str)
            }
            mapped = {
                str(row.get("organ_id") or "")
                for row in _inventory_rows(payload)
                if row.get("organ_id")
            }
            for organ_id in sorted((accepted - mapped) | (mapped - known_organs)):
                _record(
                    findings,
                    observed,
                    "STANDARDS_META_UNMAPPED_ACCEPTED_ORGAN",
                    "Accepted organ set and standards inventory mapping diverged.",
                    case_id=case_id,
                    subject_id=organ_id,
                    subject_kind="organ_id",
                )
        elif stem == "missing_receipt_ref":
            for row in _inventory_rows(payload) or _walk_dicts(payload):
                organ_id = str(row.get("organ_id") or "organ")
                receipt_refs = row.get("receipt_refs", [])
                if not isinstance(receipt_refs, list) or not receipt_refs:
                    _record(
                        findings,
                        observed,
                        "STANDARDS_META_MISSING_RECEIPT_REF",
                        "Standards diagnostic rows must keep current receipt refs.",
                        case_id=case_id,
                        subject_id=organ_id,
                        subject_kind="receipt_refs",
                    )
        elif stem == "release_overclaim":
            fields = [field for field in OVERCLAIM_KEYS if payload.get(field) is True]
            if fields:
                _record(
                    findings,
                    observed,
                    "STANDARDS_META_AUTHORITY_OVERCLAIM",
                    "Diagnostics cannot authorize release, publication, providers, or global correctness.",
                    case_id=case_id,
                    subject_id=",".join(sorted(fields)),
                    subject_kind="authority_ceiling",
                )
        elif stem == "private_source_leakage":
            for row in _walk_dicts(payload):
                fields = [field for field in FORBIDDEN_PRIVATE_KEYS if row.get(field)]
                if fields:
                    _record(
                        findings,
                        observed,
                        "STANDARDS_META_PRIVATE_SOURCE_FORBIDDEN",
                        "Public diagnostics must carry public refs, not private source bodies.",
                        case_id=case_id,
                        subject_id=str(row.get("organ_id") or row.get("case_id") or "payload"),
                        subject_kind="private_source",
                    )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "standards_meta_diagnostics_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "diagnostic_projection": {
            "accepted_organ_count": result["accepted_organ_count"],
            "standard_mapping_count": result["standard_mapping_count"],
            "runtime_contract_count": result["runtime_contract_count"],
            "receipt_ref_count": result["receipt_ref_count"],
            "pressure_row_count": result["pressure_row_count"],
            "body_in_receipt": False,
        },
        "public_contract": {
            "standards_are_mapped_to_organs": True,
            "runtime_contracts_are_mapped_to_organs": True,
            "receipt_refs_are_required": True,
            "private_source_bodies_forbidden": True,
            "release_overclaims_rejected": True,
            "body_in_receipt": False,
            "real_runtime_receipt": result["real_runtime_receipt"],
            "synthetic_receipt_standin_allowed": False,
        },
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "input_mode",
        "bundle_id",
        "source_pattern_ids",
        "source_refs",
        "public_runtime_refs",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "accepted_organ_count",
        "standard_mapping_count",
        "runtime_contract_count",
        "receipt_ref_count",
        "pressure_row_count",
        "covered_organ_ids",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
        "freshness_basis",
        "receipt_reused",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [_display(path, public_root=public_root) for path in paths.values()]


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    negative_payloads = {
        name: payloads[name] for name in NEGATIVE_INPUT_STEMS if name in payloads
    }
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )

    inventory_payload = payloads["standards_inventory"]
    contracts_payload = payloads["organ_runtime_contracts"]
    diagnostic_policy = payloads["diagnostic_policy"]
    if not isinstance(diagnostic_policy, dict):
        diagnostic_policy = {}
    inventory_rows = _inventory_rows(inventory_payload)
    runtime_rows = _contract_rows(contracts_payload)
    positive_findings = _positive_findings(
        inventory_rows=inventory_rows,
        runtime_rows=runtime_rows,
        policy=diagnostic_policy,
    )
    covered_organs = sorted(
        {
            str(row.get("organ_id") or "")
            for row in inventory_rows
            if row.get("organ_id")
        }
    )
    negative = _negative_findings(negative_payloads, known_organs=set(covered_organs))
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed = negative["observed_negative_cases"]
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [*positive_findings, *negative["findings"]]
    error_codes = sorted({finding["error_code"] for finding in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    receipt_ref_count = sum(
        len(row.get("receipt_refs", []))
        for row in inventory_rows
        if isinstance(row.get("receipt_refs", []), list)
    )
    pressure_row_count = sum(1 for row in inventory_rows if row.get("pressure_row_ref"))
    status = (
        PASS
        if not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        else "blocked"
    )
    return {
        "schema_version": "standards_meta_diagnostics_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": SOURCE_REFS,
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "accepted_organ_count": len(diagnostic_policy.get("accepted_organ_ids", [])),
        "standard_mapping_count": len(inventory_rows),
        "runtime_contract_count": len(runtime_rows),
        "receipt_ref_count": receipt_ref_count,
        "pressure_row_count": pressure_row_count,
        "covered_organ_ids": covered_organs,
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    public_root = _public_root_for_path(out_dir)
    paths = {
        "result": out_dir / RESULT_NAME,
        "board": out_dir / BOARD_NAME,
        "validation": out_dir / VALIDATION_RECEIPT_NAME,
    }
    if acceptance_out is not None:
        paths["acceptance"] = acceptance_out
    relative_paths = _relative_receipt_paths(paths, public_root)
    board = _build_board(result=result, secret_scan=result["secret_exclusion_scan"])
    result_receipt = _common_receipt(
        result,
        schema_version="standards_meta_diagnostics_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    board["receipt_paths"] = relative_paths
    validation = _common_receipt(
        result,
        schema_version="standards_meta_diagnostics_validation_receipt_v1",
        receipt_paths=relative_paths,
    )
    validation["board_ref"] = _display(paths["board"], public_root=public_root)
    validation["result_ref"] = _display(paths["result"], public_root=public_root)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board)
    write_json_atomic(paths["validation"], validation)
    if acceptance_out is not None:
        acceptance = _common_receipt(
            result,
            schema_version="standards_meta_diagnostics_fixture_acceptance_v1",
            receipt_paths=relative_paths,
        )
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.standards_meta_diagnostics run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    target = Path(out_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_diagnostics_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.standards_meta_diagnostics "
        "run-diagnostics-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    target = Path(out_dir)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, target)
        if cached is not None:
            return cached
    public_root = _public_root_for_path(target)
    result = _build_result(
        source,
        command=command,
        input_mode="exported_standards_meta_diagnostics_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_standards_meta_diagnostics_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": (
                result.get("freshness_basis", {}).get("basis_digest")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
            "freshness_input_count": (
                result.get("freshness_basis", {}).get("input_count")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
            "freshness_missing_path_count": (
                result.get("freshness_basis", {}).get("missing_path_count")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
        },
        "diagnostic_projection": {
            "accepted_organ_count": result.get("accepted_organ_count"),
            "standard_mapping_count": result.get("standard_mapping_count"),
            "runtime_contract_count": result.get("runtime_contract_count"),
            "receipt_ref_count": result.get("receipt_ref_count"),
            "pressure_row_count": result.get("pressure_row_count"),
        },
        "validation": {
            "missing_negative_case_count": len(result.get("missing_negative_cases") or []),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "real_runtime_receipt": result.get("real_runtime_receipt") is True,
            "synthetic_receipt_standin_allowed": (
                result.get("synthetic_receipt_standin_allowed") is True
            ),
        },
        "authority_boundary": {
            "standards_registry_authority": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_claim": False,
            "whole_system_correctness_claim": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public standards meta diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-diagnostics-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.standards_meta_diagnostics run "
            f"--input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.standards_meta_diagnostics "
            f"run-diagnostics-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_diagnostics_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
