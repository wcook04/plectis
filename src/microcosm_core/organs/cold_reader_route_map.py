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
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
CARD_SCHEMA_VERSION = "cold_reader_route_map_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "source_module_results",
    "secret_exclusion_scan",
    "findings",
    "source_module_refs",
    "real_substrate_refs",
    "public_runtime_refs",
    "receipt_paths",
    "anti_claim",
    "authority_ceiling",
)
REAL_BODY_MATERIAL_STATUS = (
    "copied_non_secret_macro_cold_entry_route_substrate_with_provenance"
)
PUBLIC_SAFE_BODY_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_macro_proof_body",
    "public_standard_body",
}

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
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _line_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _source_module_target_path(
    input_dir: Path,
    row: dict[str, Any],
    *,
    public_root: Path,
) -> Path:
    row_path = str(row.get("path") or "")
    if row_path and not Path(row_path).is_absolute() and ".." not in Path(row_path).parts:
        return input_dir / row_path
    target_ref = str(row.get("target_ref") or "")
    if target_ref.startswith("microcosm-substrate/"):
        target_ref = target_ref.removeprefix("microcosm-substrate/")
    if target_ref and not Path(target_ref).is_absolute() and ".." not in Path(target_ref).parts:
        return public_root / target_ref
    return input_dir / "__invalid_source_module_target__"


def _source_module_paths(input_dir: Path, manifest_payload: object | None = None) -> list[Path]:
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    manifest = manifest_payload if isinstance(manifest_payload, dict) else None
    if manifest is None and manifest_path.is_file():
        manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        return []
    public_root = _public_root_for_path(input_dir)
    return [
        _source_module_target_path(input_dir, row, public_root=public_root)
        for row in _rows(manifest, "modules")
    ]


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


def _source_module_import_result(
    input_dir: Path,
    *,
    public_root: Path,
    required: bool,
) -> dict[str, Any]:
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    manifest = read_json_strict(manifest_path) if manifest_path.is_file() else {}
    rows = _rows(manifest, "modules")
    findings: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []

    if required and not manifest_path.is_file():
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported cold-reader route-map bundle must include copied source module provenance.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if manifest_path.is_file() and manifest.get("source_import_class") != (
        "copied_non_secret_macro_body"
    ):
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                "Cold-reader source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if manifest_path.is_file() and manifest.get("body_in_receipt") is True:
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                "Copied source bodies must live in the bundle source_modules tree, not in receipts.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if required and manifest_path.is_file() and not rows:
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_ROWS_MISSING",
                "Exported cold-reader route-map bundle must carry copied source module rows.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    expected_count = manifest.get("module_count")
    if manifest_path.is_file() and expected_count != len(rows):
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )

    for row in rows:
        module_id = str(row.get("module_id") or "source_module")
        target = _source_module_target_path(input_dir, row, public_root=public_root)
        target_exists = target.is_file()
        expected_digest = str(row.get("sha256") or "")
        actual_digest = _sha256(target) if target_exists else None
        material_class = str(row.get("material_class") or "")
        source_ref = str(row.get("source_ref") or "")
        required_anchors = [
            str(anchor)
            for anchor in row.get("required_anchors", [])
            if isinstance(anchor, str) and anchor
        ]
        text = target.read_text(encoding="utf-8") if target_exists else ""
        missing_anchors = [
            anchor for anchor in required_anchors if anchor not in text
        ]
        digest_match = target_exists and actual_digest == expected_digest
        anchor_status = PASS if not missing_anchors else "blocked"
        row_body_in_receipt = row.get("body_in_receipt") is True
        import_row = {
            "module_id": module_id,
            "source_ref": source_ref,
            "target_ref": _display(target, public_root=public_root),
            "material_class": material_class,
            "source_sha256": expected_digest,
            "target_sha256": actual_digest,
            "exists": target_exists,
            "digest_match": digest_match,
            "anchor_status": anchor_status,
            "missing_anchor_count": len(missing_anchors),
            "source_to_target_relation": str(
                row.get("source_to_target_relation") or "exact_copy"
            ),
            "source_line_count": row.get("line_count"),
            "target_line_count": _line_count(target) if target_exists else None,
            "body_in_receipt": False,
            "body_material_status": REAL_BODY_MATERIAL_STATUS,
        }
        imports.append(import_row)

        if str(row.get("source_import_class") or "") != "copied_non_secret_macro_body":
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                    "Copied source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_BODY_CLASSES:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_CLASS_UNSUPPORTED",
                    "Copied source module rows must use a public-safe macro body class.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row_body_in_receipt:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                    "Copied source module bodies may be bundled as files, not emitted in receipts.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if import_row["source_to_target_relation"] != "exact_copy":
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_RELATION_UNSUPPORTED",
                    "Cold-reader body-floor imports must currently be exact copied source bodies.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not target_exists:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_TARGET_MISSING",
                    "Copied source module target file is missing from the exported bundle.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif not digest_match:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied source module digest must match the source_module_manifest row.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if missing_anchors:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_ANCHOR_MISSING",
                    "Copied source module must preserve every required provenance anchor.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )

    status = PASS if not findings else "blocked"
    if not required and not manifest_path.is_file():
        status = "not_required"
    copied_count = sum(
        1
        for row in imports
        if row["exists"] and row["digest_match"] and row["anchor_status"] == PASS
    )
    return {
        "status": status,
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "body_material_status": REAL_BODY_MATERIAL_STATUS
        if imports
        else "no_source_module_import_required",
        "source_module_results": imports,
        "source_module_count": len(imports),
        "copied_source_module_count": copied_count,
        "source_module_refs": [row["target_ref"] for row in imports],
        "source_refs": sorted({row["source_ref"] for row in imports if row["source_ref"]}),
        "material_classes": sorted(
            {row["material_class"] for row in imports if row["material_class"]}
        ),
        "findings": findings,
    }


def _scan_inputs(
    input_dir: Path,
    *,
    include_negative: bool,
    public_root: Path,
    extra_paths: list[Path] | None = None,
) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(
        [*_input_paths(input_dir, include_negative=include_negative), *(extra_paths or [])],
        forbidden_classes=policy,
        display_root=public_root,
    )
    scan.pop("forbidden_output_fields", None)
    return scan


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [_display(path, public_root=public_root) for path in paths.values()]


def _freshness_input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    paths = _input_paths(input_dir, include_negative=include_negative)
    bundle_manifest_path = input_dir / "bundle_manifest.json"
    if bundle_manifest_path.is_file():
        paths.append(bundle_manifest_path)
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if manifest_path.is_file():
        manifest = read_json_strict(manifest_path)
        paths.extend([manifest_path, *_source_module_paths(input_dir, manifest)])
    forbidden_policy_path = (
        _public_root_for_path(input_dir) / "core/private_state_forbidden_classes.json"
    )
    if forbidden_policy_path.is_file():
        paths.append(forbidden_policy_path)
    return paths


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    paths = _freshness_input_paths(input_dir, include_negative=include_negative)
    existing = [path for path in paths if path.is_file()]
    latest_mtime = max((path.stat().st_mtime for path in existing), default=0.0)
    return {
        "mode": "input_file_mtime_guard",
        "checked_path_count": len(paths),
        "existing_path_count": len(existing),
        "missing_path_count": len(paths) - len(existing),
        "latest_input_mtime": latest_mtime,
    }


def _fresh_exported_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    public_root = _public_root_for_path(out_dir)
    receipt_path = out_dir / BUNDLE_RESULT_NAME
    if not receipt_path.is_file():
        return None
    try:
        receipt = read_json_strict(receipt_path)
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(receipt, dict):
        return None
    if receipt.get("schema_version") != (
        "exported_cold_reader_route_map_bundle_validation_result_v1"
    ):
        return None
    if receipt.get("organ_id") != ORGAN_ID:
        return None
    if receipt.get("status") != PASS:
        return None
    if receipt.get("input_mode") != "exported_cold_reader_route_map_bundle":
        return None
    if receipt.get("command") != command:
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    if basis["missing_path_count"]:
        return None
    if receipt_path.stat().st_mtime < basis["latest_input_mtime"]:
        return None
    cached = dict(receipt)
    cached["cache_status"] = "fresh_exported_bundle_receipt_reused"
    cached["freshness_basis"] = {
        **basis,
        "receipt_ref": _display(receipt_path, public_root=public_root),
    }
    cached["receipt_paths"] = [_display(receipt_path, public_root=public_root)]
    return cached


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
        "bundle_id": result.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": SOURCE_REFS,
        "public_runtime_refs": result["public_runtime_refs"],
        "real_substrate_refs": result["real_substrate_refs"],
        "body_material_status": result["body_material_status"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_count": result["source_module_count"],
        "copied_source_module_count": result["copied_source_module_count"],
        "source_module_refs": result["source_module_refs"],
        "source_module_results": result["source_module_results"],
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
        "covered_route_ids": result.get("covered_route_ids", []),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "receipt_paths": receipt_paths,
        "cache_status": result.get("cache_status", "not_applicable"),
        "freshness_basis": result.get("freshness_basis", {}),
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
        "real_substrate_refs": result["real_substrate_refs"],
        "body_material_status": result["body_material_status"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_count": result["source_module_count"],
        "copied_source_module_count": result["copied_source_module_count"],
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
    source_manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    source_manifest_payload = (
        read_json_strict(source_manifest_path) if source_manifest_path.is_file() else {}
    )
    source_module_extra_paths = []
    if source_manifest_path.is_file():
        source_module_extra_paths = [
            source_manifest_path,
            *_source_module_paths(input_dir, source_manifest_payload),
        ]
    secret_scan = _scan_inputs(
        input_dir,
        include_negative=include_negative,
        public_root=public_root,
        extra_paths=source_module_extra_paths,
    )
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
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    source_modules = _source_module_import_result(
        input_dir,
        public_root=public_root,
        required=input_mode == "exported_cold_reader_route_map_bundle",
    )
    findings = [*positive_findings, *negative["findings"], *source_modules["findings"]]
    error_codes = sorted({finding["error_code"] for finding in findings})
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
    source_modules_pass = source_modules["status"] in (PASS, "not_required")
    status = (
        PASS
        if not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        and source_modules_pass
        else "blocked"
    )
    real_substrate_refs = [
        *PUBLIC_RUNTIME_REFS,
        *source_modules["source_refs"],
        *source_modules["source_module_refs"],
    ]
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
        "real_substrate_refs": real_substrate_refs,
        "body_material_status": source_modules["body_material_status"],
        "body_import_verification": {
            "verification_status": PASS if source_modules_pass else "blocked",
            "verification_mode": "exact_source_digest_match_plus_required_anchor_check",
            "source_module_manifest_ref": source_modules[
                "source_module_manifest_ref"
            ],
            "source_to_target_relation": "exact_copy",
            "body_in_receipt": False,
        },
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_count": source_modules["source_module_count"],
        "copied_source_module_count": source_modules["copied_source_module_count"],
        "source_module_refs": source_modules["source_module_refs"],
        "source_module_results": source_modules["source_module_results"],
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
    result["cache_status"] = "not_applicable_fixture_run"
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_route_map_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.cold_reader_route_map run-route-map-bundle",
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    target = Path(out_dir)
    public_root = _public_root_for_path(target)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_exported_bundle_receipt(source, target, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_cold_reader_route_map_bundle",
        include_negative=False,
    )
    result["cache_status"] = "rebuilt"
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
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


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "command": result["command"],
        "route_map": {
            "route_count": result["route_count"],
            "command_count": result["command_count"],
            "receipt_ref_count": result["receipt_ref_count"],
            "covered_route_count": len(result.get("covered_route_ids", [])),
            "first_run_sequence_head": result["first_run_sequence"][:3],
            "front_door_route_ids": result["front_door_route_ids"],
            "front_door_command_count": result["front_door_command_count"],
        },
        "source_import_floor": {
            "status": result["source_module_manifest_status"],
            "source_module_count": result["source_module_count"],
            "copied_source_module_count": result["copied_source_module_count"],
            "body_material_status": result["body_material_status"],
            "verification_status": result["body_import_verification"][
                "verification_status"
            ],
            "body_in_receipt": result["body_import_verification"]["body_in_receipt"],
        },
        "negative_case_summary": {
            "expected_negative_case_count": len(result["expected_negative_cases"]),
            "observed_negative_case_count": len(result["observed_negative_cases"]),
            "missing_negative_case_count": len(result["missing_negative_cases"]),
            "error_code_count": len(result["error_codes"]),
        },
        "secret_exclusion_summary": {
            "status": result["secret_exclusion_scan"].get("status"),
            "blocking_hit_count": result["secret_exclusion_scan"].get(
                "blocking_hit_count"
            ),
            "body_in_receipt": result["secret_exclusion_scan"].get("body_in_receipt"),
        },
        "authority_ceiling": {
            "route_registry_authority": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "provider_calls_authorized": False,
            "whole_system_correctness_claim": False,
        },
        "runtime_receipt": {
            "real_runtime_receipt": result["real_runtime_receipt"],
            "synthetic_receipt_standin_allowed": result[
                "synthetic_receipt_standin_allowed"
            ],
        },
        "cache_status": result.get("cache_status", "not_applicable"),
        "freshness_basis": result.get("freshness_basis", {}),
        "receipt_paths": result.get("receipt_paths", []),
        "output_economy": {
            "full_payload_drilldown": "rerun without --card or inspect the written receipt files",
            "omitted_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "source_bodies_exported": False,
            "provider_payloads_exported": False,
            "private_state_exported": False,
            "raw_stdout_stderr_bodies_exported": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public cold-reader route map")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-route-map-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.command == "run":
        command = (
            "python -m microcosm_core.organs.cold_reader_route_map run "
            f"--input {args.input} --out {args.out}{card_suffix}"
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
            f"run-route-map-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_route_map_bundle(
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
