from __future__ import annotations

import argparse
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


ORGAN_ID = "cold_reader_route_map"
FIXTURE_ID = "first_wave.cold_reader_route_map"
VALIDATOR_ID = "validator.microcosm.organs.cold_reader_route_map"

RESULT_NAME = "cold_reader_route_map_result.json"
BOARD_NAME = "cold_reader_route_map_board.json"
VALIDATION_RECEIPT_NAME = "cold_reader_route_map_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_cold_reader_route_map_bundle_validation_result.json"

SOURCE_PATTERN_IDS = [
    "navigation_hologram_unified_route_plane",
    "compression_profile_governed_option_surface",
    "entry_agent_behavior_governance_suborgan",
]
SOURCE_REFS = [
    "microcosm-substrate/src/microcosm_core/runtime_shell.py",
    "microcosm-substrate/README.md",
    "microcosm-substrate/AGENTS.md",
]
PUBLIC_RUNTIME_REFS = [
    "fixtures/first_wave/cold_reader_route_map/input/route_map.json",
    "fixtures/first_wave/cold_reader_route_map/input/route_receipts.json",
    "fixtures/first_wave/cold_reader_route_map/input/route_policy.json",
    "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
    "paper_modules/cold_reader_route_map.md",
]

INPUT_NAMES = ("route_map.json", "route_receipts.json", "route_policy.json")
NEGATIVE_INPUT_NAMES = (
    "missing_command_ref.json",
    "missing_receipt_ref.json",
    "route_sequence_gap.json",
    "release_overclaim.json",
    "private_source_leakage.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "missing_command_ref": ["COLD_ROUTE_MISSING_COMMAND_REF"],
    "missing_receipt_ref": ["COLD_ROUTE_MISSING_RECEIPT_REF"],
    "route_sequence_gap": ["COLD_ROUTE_SEQUENCE_GAP"],
    "release_overclaim": ["COLD_ROUTE_AUTHORITY_OVERCLAIM"],
    "private_source_leakage": ["COLD_ROUTE_PRIVATE_SOURCE_FORBIDDEN"],
}

FRONT_DOOR_ROUTE_COMMANDS = {
    "tour_project": "microcosm tour <project>",
    "status_card": "microcosm status --card <project>",
    "proof_lab": "microcosm proof-lab --out /tmp/microcosm-proof-lab",
}
FRONT_DOOR_ROUTE_IDS = tuple(FRONT_DOOR_ROUTE_COMMANDS)

FORBIDDEN_PRIVATE_KEYS = (
    "private_source_body",
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
    "authority_ceiling": "cold_reader_route_map_projection_only_not_route_authority",
    "route_registry_authority": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "provider_calls_authorized": False,
    "private_data_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "The cold-reader route map validates a public ten-minute route projection only. "
    "It does not become route registry authority, expose private macro sources, "
    "authorize release, call providers, mutate source projects, or prove whole-system "
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


def _route_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "routes")
    if rows:
        return rows
    return _rows(payload, "rows")


def _receipt_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "route_receipts")
    if rows:
        return rows
    return _rows(payload, "rows")


def _route_id(row: dict[str, Any]) -> str:
    return str(row.get("route_id") or row.get("step_id") or "").strip()


def _positive_findings(
    *,
    route_rows: list[dict[str, Any]],
    receipt_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    route_by_id = {_route_id(row): row for row in route_rows if _route_id(row)}
    receipts_by_id = {
        str(row.get("route_id") or ""): row
        for row in receipt_rows
        if row.get("route_id")
    }
    required_route_ids = [
        str(route_id)
        for route_id in policy.get("required_route_ids", [])
        if isinstance(route_id, str)
    ]
    for route_id in required_route_ids:
        row = route_by_id.get(route_id)
        if row is None:
            _record(
                findings,
                observed,
                "COLD_ROUTE_SEQUENCE_GAP",
                "Every required cold-reader route must exist in the route map.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="route_id",
            )
            continue
        if not row.get("command"):
            _record(
                findings,
                observed,
                "COLD_ROUTE_MISSING_COMMAND_REF",
                "Every cold-reader route must name its runnable command.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="command",
            )
        if not row.get("docs_refs"):
            _record(
                findings,
                observed,
                "COLD_ROUTE_MISSING_DOC_REF",
                "Every cold-reader route must name a public docs reference.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="docs_refs",
            )
        receipt_row = receipts_by_id.get(route_id)
        receipt_refs = []
        if receipt_row is not None and isinstance(receipt_row.get("receipt_refs"), list):
            receipt_refs = receipt_row["receipt_refs"]
        if not receipt_refs:
            _record(
                findings,
                observed,
                "COLD_ROUTE_MISSING_RECEIPT_REF",
                "Every cold-reader route must point at at least one evidence receipt.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="receipt_refs",
            )

    sequence = [
        str(route_id)
        for route_id in policy.get("first_run_sequence", [])
        if isinstance(route_id, str)
    ]
    if sequence[: len(FRONT_DOOR_ROUTE_IDS)] != list(FRONT_DOOR_ROUTE_IDS):
        _record(
            findings,
            observed,
            "COLD_ROUTE_SEQUENCE_GAP",
            "The first-run route sequence must start with tour, status card, and proof lab.",
            case_id="positive_route_map",
            subject_id="first_run_sequence",
            subject_kind="sequence",
        )
    for route_id, expected_command in FRONT_DOOR_ROUTE_COMMANDS.items():
        row = route_by_id.get(route_id)
        if row is not None and row.get("command") != expected_command:
            _record(
                findings,
                observed,
                "COLD_ROUTE_FRONT_DOOR_COMMAND_DRIFT",
                "Front-door route commands must match the live first-screen command path.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="command",
            )
    ordinals = {
        route_id: route_by_id.get(route_id, {}).get("ordinal")
        for route_id in sequence
        if route_id in route_by_id
    }
    if len(ordinals) != len(sequence) or sorted(ordinals.values()) != list(ordinals.values()):
        _record(
            findings,
            observed,
            "COLD_ROUTE_SEQUENCE_GAP",
            "The first-run route sequence must be present and ordinal sorted.",
            case_id="positive_route_map",
            subject_id="first_run_sequence",
            subject_kind="sequence",
        )
    return findings


def _negative_findings(payloads: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for case_id, payload in payloads.items():
        if case_id not in NEGATIVE_INPUT_STEMS:
            continue
        for row in _walk_dicts(payload):
            subject_id = str(
                row.get("route_id")
                or row.get("case_id")
                or row.get("id")
                or case_id
            )
            if case_id == "missing_command_ref" and not row.get("command"):
                _record(
                    findings,
                    observed,
                    "COLD_ROUTE_MISSING_COMMAND_REF",
                    "A route card without a command cannot guide a cold reader.",
                    case_id=case_id,
                    subject_id=subject_id,
                    subject_kind="command",
                )
            if case_id == "missing_receipt_ref" and not row.get("receipt_refs"):
                _record(
                    findings,
                    observed,
                    "COLD_ROUTE_MISSING_RECEIPT_REF",
                    "A route card without receipt refs is not evidence-backed.",
                    case_id=case_id,
                    subject_id=subject_id,
                    subject_kind="receipt_refs",
            )
            if case_id == "route_sequence_gap":
                sequence = row.get("first_run_sequence", [])
                if isinstance(sequence, list) and sequence[:1] != ["tour_project"]:
                    _record(
                        findings,
                        observed,
                        "COLD_ROUTE_SEQUENCE_GAP",
                        "The first-run sequence must start from tour_project.",
                        case_id=case_id,
                        subject_id=subject_id,
                        subject_kind="first_run_sequence",
                    )
            if case_id == "private_source_leakage" and any(
                key in row for key in FORBIDDEN_PRIVATE_KEYS
            ):
                _record(
                    findings,
                    observed,
                    "COLD_ROUTE_PRIVATE_SOURCE_FORBIDDEN",
                    "Cold-reader route maps must not carry private source bodies.",
                    case_id=case_id,
                    subject_id=subject_id,
                    subject_kind="private_source",
                )
            if case_id == "release_overclaim":
                for key in OVERCLAIM_KEYS:
                    if row.get(key) is True:
                        _record(
                            findings,
                            observed,
                            "COLD_ROUTE_AUTHORITY_OVERCLAIM",
                            "Cold-reader route maps cannot authorize release or global authority.",
                            case_id=case_id,
                            subject_id=subject_id,
                            subject_kind=key,
                        )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _scan_inputs(input_dir: Path, *, include_negative: bool, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    scan.pop("forbidden_output_fields", None)
    return scan


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [_display(path, public_root=public_root) for path in paths.values()]


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": result["command"],
        "input_mode": result["input_mode"],
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": SOURCE_REFS,
        "public_runtime_refs": result["public_runtime_refs"],
        "error_codes": result["error_codes"],
        "expected_negative_cases": result["expected_negative_cases"],
        "observed_negative_cases": result["observed_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "finding_count": len(result["findings"]),
        "route_count": result["route_count"],
        "command_count": result["command_count"],
        "receipt_ref_count": result["receipt_ref_count"],
        "first_run_sequence": result["first_run_sequence"],
        "front_door_route_ids": result["front_door_route_ids"],
        "front_door_command_count": result["front_door_command_count"],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "receipt_paths": receipt_paths,
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
    }


def _build_board(
    *,
    result: dict[str, Any],
    secret_scan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "cold_reader_route_map_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "cold_reader_route_map_first_run_board",
        "route_map": {
            "route_count": result["route_count"],
            "command_count": result["command_count"],
            "receipt_ref_count": result["receipt_ref_count"],
            "first_run_sequence": result["first_run_sequence"],
            "covered_route_ids": result["covered_route_ids"],
            "front_door_route_ids": result["front_door_route_ids"],
            "front_door_command_count": result["front_door_command_count"],
        },
        "cold_reader_goal": "legible_under_10_minutes_without_private_macro_context",
        "public_runtime_refs": result["public_runtime_refs"],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": secret_scan,
        "finding_count": len(result["findings"]),
        "findings": result["findings"],
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
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
    secret_scan = _scan_inputs(input_dir, include_negative=include_negative, public_root=public_root)
    route_map = payloads.get("route_map", {})
    route_receipts = payloads.get("route_receipts", {})
    route_policy = payloads.get("route_policy", {})
    if not isinstance(route_policy, dict):
        route_policy = {}
    route_rows = _route_rows(route_map)
    receipt_rows = _receipt_rows(route_receipts)
    route_by_id = {_route_id(row): row for row in route_rows if _route_id(row)}
    positive_findings = _positive_findings(
        route_rows=route_rows,
        receipt_rows=receipt_rows,
        policy=route_policy,
    )
    negative_payloads = {
        key: value for key, value in payloads.items() if key in NEGATIVE_INPUT_STEMS
    }
    negative = _negative_findings(negative_payloads)
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
        for row in receipt_rows
        if isinstance(row.get("receipt_refs", []), list)
    )
    first_run_sequence = [
        str(route_id)
        for route_id in route_policy.get("first_run_sequence", [])
        if isinstance(route_id, str)
    ]
    covered_route_ids = sorted(_route_id(row) for row in route_rows if _route_id(row))
    front_door_command_count = sum(
        1
        for route_id, expected_command in FRONT_DOOR_ROUTE_COMMANDS.items()
        if route_by_id.get(route_id, {}).get("command") == expected_command
    )
    status = (
        PASS
        if not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        else "blocked"
    )
    return {
        "schema_version": "cold_reader_route_map_result_v1",
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
        "route_count": len(route_rows),
        "command_count": sum(1 for row in route_rows if row.get("command")),
        "receipt_ref_count": receipt_ref_count,
        "first_run_sequence": first_run_sequence,
        "front_door_route_ids": list(FRONT_DOOR_ROUTE_IDS),
        "front_door_command_count": front_door_command_count,
        "covered_route_ids": covered_route_ids,
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
        schema_version="cold_reader_route_map_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    board["receipt_paths"] = relative_paths
    validation = _common_receipt(
        result,
        schema_version="cold_reader_route_map_validation_receipt_v1",
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
            schema_version="cold_reader_route_map_fixture_acceptance_v1",
            receipt_paths=relative_paths,
        )
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.cold_reader_route_map run",
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
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_route_map_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.cold_reader_route_map run-route-map-bundle",
) -> dict[str, Any]:
    target = Path(out_dir)
    public_root = _public_root_for_path(target)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_cold_reader_route_map_bundle",
        include_negative=False,
    )
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_cold_reader_route_map_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public cold-reader route map")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-route-map-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        command = (
            "python -m microcosm_core.organs.cold_reader_route_map run "
            f"--input {args.input} --out {args.out}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        command = (
            "python -m microcosm_core.organs.cold_reader_route_map "
            f"run-route-map-bundle --input {args.input} --out {args.out}"
        )
        result = run_route_map_bundle(args.input, args.out, command=command)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
