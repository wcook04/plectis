from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "executable_doctrine_grammar"
FIXTURE_ID = "first_wave.executable_doctrine_grammar"
STANDARDS_REPORT_NAME = "standards_validation_report.json"
GROUP_INDEX_NAME = "standards_group_index.json"
PAPER_REPORT_NAME = "paper_module_validation_report.json"
ACCEPTANCE_RECEIPT_REL = "receipts/acceptance/first_wave/executable_doctrine_grammar_fixture_acceptance.json"
STANDARDS_BUNDLE_RESULT_NAME = "exported_standards_bundle_validation_result.json"
METABOLISM_BUNDLE_RESULT_NAME = "exported_executable_grammar_metabolism_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = "copied_non_secret_executable_grammar_and_standards_macro_bodies_with_provenance"
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {
    "public_macro_standard_body",
    "public_macro_tool_body",
    "public_macro_receipt_body",
}
SOURCE_MODULE_RELATIONS = {"exact_copy"}
SOURCE_MODULE_SOURCE_REF_PREFIXES = (
    "self-indexing-cognitive-substrate/microcosms/executable_grammar_metabolism/",
)
SOURCE_MODULE_SOURCE_REF_EXACT = {
    "codex/standards/standards_registry.json",
    "codex/standards/std_standards_registry.json",
    "codex/standards/std_standards_group_index.json",
    "codex/standards/std_standard_type_plane.json",
    "codex/standards/core_authority_index.json",
    "codex/standards/lattice_registry.json",
    "codex/standards/std_lattice_registry.json",
    "system/lib/standard_option_surface.py",
    "system/lib/kind_atlas.py",
}

GRAMMAR_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "executable_doctrine_grammar_public_fixture_receipt_only_not_macro_doctrine_authority",
    "prose_runtime_authority_rejected": True,
    "doctrine_completeness_overclaim_rejected": True,
}
GRAMMAR_ANTI_CLAIM = (
    "Executable doctrine grammar validates public standards and paper-module structure only; "
    "it does not publish macro doctrine bodies, prove doctrine completeness, or authorize later organs."
)
MACRO_BODY_SENTINEL = "SYNTHETIC_MACRO_DOCTRINE_BODY_COPY"

EXPECTED_NEGATIVE_CASES = {
    "invalid_standard_and_module": [
        "MISSING_TELEOLOGY",
        "MISSING_RECEIPT_EXPECTATIONS",
        "MISSING_GOVERNING_STANDARD",
        "MISSING_ANTI_CLAIM",
    ],
    "prose_standard_claims_runtime_authority": ["PROSE_STANDARD_NOT_EXECUTABLE_AUTHORITY"],
    "macro_doctrine_body_copied_into_fixture": ["MACRO_DOCTRINE_BODY_IN_PUBLIC_FIXTURE"],
    "duplicate_standard_slug_conflict": ["DUPLICATE_STANDARD_SLUG_CONFLICT"],
    "grammar_index_pass_overclaims_doctrine_complete": [
        "GRAMMAR_PASS_OVERCLAIMS_DOCTRINE_COMPLETE"
    ],
}

EXPECTED_RECEIPT_PATHS = [
    "receipts/first_wave/executable_doctrine_grammar/paper_module_validation_report.json",
    "receipts/first_wave/executable_doctrine_grammar/standards_group_index.json",
    "receipts/first_wave/executable_doctrine_grammar/standards_validation_report.json",
    ACCEPTANCE_RECEIPT_REL,
]
METABOLISM_REQUIRED_FILES = (
    "bundle_manifest.json",
    "README.md",
    "grammar_board.json",
    "receipt.json",
)
METABOLISM_REQUIRED_BOARD_KEYS = (
    "schema_version",
    "status",
    "grammar_rules",
    "cases",
    "grammar_loop",
    "provider_replay_bridge",
    "source_capsule_provenance",
    "public_safety_boundary",
    "claim_boundary",
    "anti_claims",
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _json_rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(
    code: str,
    message: str,
    *,
    case_id: str | None = None,
    subject_id: str | None = None,
    subject_kind: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error_code": code,
        "message": message,
        "body_redacted": True,
    }
    if case_id:
        payload["negative_case_id"] = case_id
    if subject_id:
        payload["subject_id"] = subject_id
    if subject_kind:
        payload["subject_kind"] = subject_kind
    return payload


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str | None = None,
    subject_id: str | None = None,
    subject_kind: str | None = None,
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
    if case_id:
        observed[case_id].add(code)


def _standard_rows(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("standards", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _row_id(row: dict[str, Any]) -> str:
    for key in ("standard_id", "row_id", "slug"):
        value = row.get(key)
        if _is_non_empty_string(value):
            return str(value).strip()
    return "standard_row"


def _standard_has_governing_ref(row: dict[str, Any]) -> bool:
    return _is_non_empty_string(row.get("governing_standard")) or bool(
        _string_list(row.get("governing_standard_refs"))
    )


def _standard_has_receipt_expectations(row: dict[str, Any]) -> bool:
    return bool(_string_list(row.get("receipt_expectations")))


def _standard_has_anti_claim(row: dict[str, Any]) -> bool:
    return _is_non_empty_string(row.get("anti_claim")) or _is_non_empty_string(row.get("anti_claim_ref"))


def validate_standard_registry(payload: object) -> dict[str, Any]:
    rows = _standard_rows(payload)
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    accepted_rows: list[dict[str, Any]] = []
    rejected_ids: set[str] = set()

    slug_counts = Counter(str(row.get("slug") or "").strip() for row in rows)
    duplicate_slugs = sorted(slug for slug, count in slug_counts.items() if slug and count > 1)

    for row in rows:
        standard_id = _row_id(row)
        case_id = row.get("expected_negative_case_id")
        if not isinstance(case_id, str):
            case_id = None
        row_error_count = len(findings)

        if not _is_non_empty_string(row.get("teleology")):
            _record(
                findings,
                observed,
                "MISSING_TELEOLOGY",
                "Standard row lacks a teleology field.",
                case_id=case_id,
                subject_id=standard_id,
                subject_kind="standard",
            )
        if not _standard_has_receipt_expectations(row):
            _record(
                findings,
                observed,
                "MISSING_RECEIPT_EXPECTATIONS",
                "Standard row lacks receipt expectations.",
                case_id=case_id,
                subject_id=standard_id,
                subject_kind="standard",
            )
        if not _standard_has_governing_ref(row):
            _record(
                findings,
                observed,
                "MISSING_GOVERNING_STANDARD",
                "Standard row lacks governing standard binding.",
                case_id=case_id,
                subject_id=standard_id,
                subject_kind="standard",
            )
        if not _standard_has_anti_claim(row):
            _record(
                findings,
                observed,
                "MISSING_ANTI_CLAIM",
                "Standard row lacks anti-claim binding.",
                case_id=case_id,
                subject_id=standard_id,
                subject_kind="standard",
            )

        if str(row.get("slug") or "").strip() in duplicate_slugs:
            _record(
                findings,
                observed,
                "DUPLICATE_STANDARD_SLUG_CONFLICT",
                "Duplicate standard slug rejected deterministically.",
                case_id=case_id or "duplicate_standard_slug_conflict",
                subject_id=standard_id,
                subject_kind="standard",
            )

        if str(row.get("standard_kind") or "").strip() == "prose" and row.get(
            "claims_executable_authority"
        ):
            _record(
                findings,
                observed,
                "PROSE_STANDARD_NOT_EXECUTABLE_AUTHORITY",
                "Prose-only standard attempted to claim executable authority.",
                case_id=case_id or "prose_standard_claims_runtime_authority",
                subject_id=standard_id,
                subject_kind="standard",
            )

        if row.get("claims_doctrine_complete"):
            _record(
                findings,
                observed,
                "GRAMMAR_PASS_OVERCLAIMS_DOCTRINE_COMPLETE",
                "Grammar fixture attempted to claim doctrine completeness.",
                case_id=case_id or "grammar_index_pass_overclaims_doctrine_complete",
                subject_id=standard_id,
                subject_kind="standard",
            )

        if len(findings) == row_error_count and not case_id:
            accepted_rows.append(row)
        else:
            rejected_ids.add(standard_id)

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "accepted_rows": accepted_rows,
        "rejected_standard_ids": sorted(rejected_ids),
        "duplicate_standard_slugs": duplicate_slugs,
    }


def _frontmatter_value(markdown_text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", markdown_text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _has_heading(markdown_text: str, heading: str) -> bool:
    return bool(re.search(rf"^##\s+{re.escape(heading)}\s*$", markdown_text, flags=re.MULTILINE))


def _module_id(path: Path, markdown_text: str) -> str:
    return _frontmatter_value(markdown_text, "module_id") or path.stem


def validate_paper_module_shape(path: str | Path) -> dict[str, Any]:
    module_path = Path(path)
    markdown_text = module_path.read_text(encoding="utf-8")
    module_id = _module_id(module_path, markdown_text)
    case_id = _frontmatter_value(markdown_text, "expected_negative_case_id")
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    if not _has_heading(markdown_text, "Teleology"):
        _record(
            findings,
            observed,
            "MISSING_TELEOLOGY",
            "Paper module lacks a Teleology section.",
            case_id=case_id,
            subject_id=module_id,
            subject_kind="paper_module",
        )
    if not _has_heading(markdown_text, "Governing Standard"):
        _record(
            findings,
            observed,
            "MISSING_GOVERNING_STANDARD",
            "Paper module lacks a Governing Standard section.",
            case_id=case_id,
            subject_id=module_id,
            subject_kind="paper_module",
        )
    if not _has_heading(markdown_text, "Receipt Expectations"):
        _record(
            findings,
            observed,
            "MISSING_RECEIPT_EXPECTATIONS",
            "Paper module lacks a Receipt Expectations section.",
            case_id=case_id,
            subject_id=module_id,
            subject_kind="paper_module",
        )
    if not _has_heading(markdown_text, "Anti-Claim"):
        _record(
            findings,
            observed,
            "MISSING_ANTI_CLAIM",
            "Paper module lacks an Anti-Claim section.",
            case_id=case_id,
            subject_id=module_id,
            subject_kind="paper_module",
        )
    if MACRO_BODY_SENTINEL in markdown_text:
        _record(
            findings,
            observed,
            "MACRO_DOCTRINE_BODY_IN_PUBLIC_FIXTURE",
            "Paper module fixture contains the synthetic macro-body-copy marker.",
            case_id="macro_doctrine_body_copied_into_fixture",
            subject_id=module_id,
            subject_kind="paper_module",
        )
    if "CLAIMS_DOCTRINE_COMPLETE" in markdown_text:
        _record(
            findings,
            observed,
            "GRAMMAR_PASS_OVERCLAIMS_DOCTRINE_COMPLETE",
            "Paper module attempted to claim doctrine completeness.",
            case_id="grammar_index_pass_overclaims_doctrine_complete",
            subject_id=module_id,
            subject_kind="paper_module",
        )

    return {
        "module_id": module_id,
        "path": public_relative_path(module_path),
        "status": PASS if not findings else "expected_negative_failure_observed",
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_paper_modules(input_dir: str | Path) -> dict[str, Any]:
    paper_dir = Path(input_dir) / "paper_modules"
    module_paths = sorted(paper_dir.glob("*.md"))
    module_results = [validate_paper_module_shape(path) for path in module_paths]
    observed: dict[str, set[str]] = defaultdict(set)
    findings: list[dict[str, Any]] = []
    valid_module_slugs: list[str] = []
    invalid_module_slugs: list[str] = []

    for result in module_results:
        findings.extend(result["findings"])
        module_id = str(result["module_id"])
        if result["findings"]:
            invalid_module_slugs.append(module_id)
        else:
            valid_module_slugs.append(module_id)
        for case_id, codes in result["observed_negative_cases"].items():
            for code in codes:
                observed[case_id].add(code)

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "module_results": module_results,
        "valid_module_slugs": sorted(valid_module_slugs),
        "invalid_module_slugs": sorted(invalid_module_slugs),
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _standard_group_index(accepted_rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in accepted_rows:
        group = str(row.get("standard_group") or ORGAN_ID)
        groups[group].append(
            {
                "standard_id": row["standard_id"],
                "slug": row["slug"],
                "governing_standard": row["governing_standard"],
                "receipt_expectations": _string_list(row.get("receipt_expectations")),
                "anti_claim_ref": row.get("anti_claim_ref"),
            }
        )
    return {
        group: sorted(rows, key=lambda item: str(item["standard_id"]))
        for group, rows in sorted(groups.items())
    }


def _receipt_expectation_coverage(accepted_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in accepted_rows:
        counts.update(_string_list(row.get("receipt_expectations")))
    return dict(sorted(counts.items()))


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    paths = [input_dir / "standards_registry.json", *sorted((input_dir / "paper_modules").glob("*.md"))]
    return scan_paths(paths, forbidden_classes=policy, display_root=public_root)


def _receipt_safe_scan_result(scan_result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan_result)
    safe.pop("forbidden_output_fields", None)
    return safe


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [public_relative_path(path, display_root=public_root) for path in paths.values()]


def _common_receipt(result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "command",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "private_state_scan",
        "authority_ceiling",
        "anti_claim",
        "valid_module_slugs",
        "invalid_module_slugs",
        "rejected_module_ids",
        "rejected_standard_ids",
        "source_pattern_ids",
        "input_mode",
        "bundle_id",
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


def write_receipts(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    acceptance_path = Path(acceptance_out) if acceptance_out is not None else public_root / ACCEPTANCE_RECEIPT_REL
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "paper_module_validation_report": target / PAPER_REPORT_NAME,
        "standards_group_index": target / GROUP_INDEX_NAME,
        "standards_validation_report": target / STANDARDS_REPORT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root)

    standards_report = _common_receipt(
        validation_result,
        schema_version="executable_doctrine_grammar_standards_validation_report_v1",
        receipt_paths=receipt_paths,
    )
    standards_report.update(
        {
            "accepted_standard_ids": validation_result["accepted_standard_ids"],
            "duplicate_standard_slugs": validation_result["duplicate_standard_slugs"],
            "grammar_error_counts": validation_result["grammar_error_counts"],
            "receipt_expectation_coverage": validation_result["receipt_expectation_coverage"],
        }
    )

    group_index = _common_receipt(
        validation_result,
        schema_version="executable_doctrine_grammar_standards_group_index_v1",
        receipt_paths=receipt_paths,
    )
    group_index.update(
        {
            "standard_group_index": validation_result["standard_group_index"],
            "standard_group_count": len(validation_result["standard_group_index"]),
            "receipt_expectation_coverage": validation_result["receipt_expectation_coverage"],
        }
    )

    paper_report = _common_receipt(
        validation_result,
        schema_version="executable_doctrine_grammar_paper_module_validation_report_v1",
        receipt_paths=receipt_paths,
    )
    paper_report.update(
        {
            "paper_module_results": validation_result["paper_module_results"],
            "valid_module_slugs": validation_result["valid_module_slugs"],
            "invalid_module_slugs": validation_result["invalid_module_slugs"],
        }
    )

    acceptance = _common_receipt(
        validation_result,
        schema_version="executable_doctrine_grammar_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "fixture_acceptance_status": validation_result["status"],
            "generated_receipts": receipt_paths,
            "expected_receipt_paths": EXPECTED_RECEIPT_PATHS,
        }
    )

    write_json_atomic(paths["paper_module_validation_report"], paper_report)
    write_json_atomic(paths["standards_group_index"], group_index)
    write_json_atomic(paths["standards_validation_report"], standards_report)
    write_json_atomic(paths["fixture_acceptance"], acceptance)

    return {key: public_relative_path(path, display_root=public_root) for key, path in paths.items()}


def _write_standards_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> str:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    path = target / STANDARDS_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="executable_doctrine_grammar_exported_standards_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "accepted_standard_ids": validation_result["accepted_standard_ids"],
            "valid_module_slugs": validation_result["valid_module_slugs"],
            "standard_group_index": validation_result["standard_group_index"],
            "receipt_expectation_coverage": validation_result["receipt_expectation_coverage"],
            "fixture_regression_required_elsewhere": True,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def validate(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    standards_path = input_path / "standards_registry.json"
    standards_payload = read_json_strict(standards_path)

    scan_result = _receipt_safe_scan_result(_scan_fixture_inputs(input_path, public_root))
    standards_result = validate_standard_registry(standards_payload)
    paper_result = validate_paper_modules(input_path)
    observed = _merge_observed(standards_result, paper_result)
    error_codes = sorted({code for codes in observed.values() for code in codes})
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    all_findings = sorted(
        [*standards_result["findings"], *paper_result["findings"]],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    grammar_error_counts = dict(
        sorted(Counter(str(finding["error_code"]) for finding in all_findings).items())
    )
    accepted_rows = standards_result["accepted_rows"]
    standard_group_index = _standard_group_index(accepted_rows)
    receipt_expectation_coverage = _receipt_expectation_coverage(accepted_rows)

    private_scan = dict(scan_result)
    private_scan["synthetic_private_boundary_negative_cases_observed"] = sorted(
        case_id for case_id in observed if case_id == "macro_doctrine_body_copied_into_fixture"
    )

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "anti_claim": GRAMMAR_ANTI_CLAIM,
            "authority_ceiling": GRAMMAR_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": all_findings,
            "private_state_scan": private_scan,
            "accepted_standard_ids": sorted(str(row["standard_id"]) for row in accepted_rows),
            "rejected_standard_ids": standards_result["rejected_standard_ids"],
            "duplicate_standard_slugs": standards_result["duplicate_standard_slugs"],
            "standard_group_index": standard_group_index,
            "grammar_error_counts": grammar_error_counts,
            "receipt_expectation_coverage": receipt_expectation_coverage,
            "paper_module_results": paper_result["module_results"],
            "valid_module_slugs": paper_result["valid_module_slugs"],
            "invalid_module_slugs": paper_result["invalid_module_slugs"],
            "rejected_module_ids": paper_result["invalid_module_slugs"],
            "source_pattern_ids": ["standards_registry", "paper_modules"],
            "fixture_inputs": [
                public_relative_path(standards_path, display_root=public_root),
                *[
                    public_relative_path(path, display_root=public_root)
                    for path in sorted((input_path / "paper_modules").glob("*.md"))
                ],
            ],
        }
    )
    paths = write_receipts(out_dir, result, public_root=public_root, acceptance_out=acceptance_out)
    result["receipt_paths"] = list(paths.values())
    return result


def validate_standards_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    manifest_path = input_path / "bundle_manifest.json"
    standards_path = input_path / "standards_registry.json"
    manifest = read_json_strict(manifest_path)
    standards_payload = read_json_strict(standards_path)

    scan_result = _receipt_safe_scan_result(_scan_fixture_inputs(input_path, public_root))
    standards_result = validate_standard_registry(standards_payload)
    paper_result = validate_paper_modules(input_path)
    observed = _merge_observed(standards_result, paper_result)
    all_findings = sorted(
        [*standards_result["findings"], *paper_result["findings"]],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    accepted_rows = standards_result["accepted_rows"]
    standard_group_index = _standard_group_index(accepted_rows)
    receipt_expectation_coverage = _receipt_expectation_coverage(accepted_rows)
    bundle_id = str(manifest.get("bundle_id") or "executable_doctrine_grammar_exported_standards_bundle")
    status = (
        PASS
        if scan_result["status"] == PASS and not all_findings and accepted_rows and paper_result["valid_module_slugs"]
        else "blocked"
    )

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.exported_standards_bundle",
        command=command,
    )
    result.update(
        {
            "status": status,
            "input_mode": "exported_standards_bundle",
            "bundle_id": bundle_id,
            "anti_claim": (
                "The exported standards bundle validates public runtime-shaped standards metadata. "
                "It does not publish macro doctrine bodies, prove doctrine completeness, or authorize later organs."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": "executable_doctrine_grammar_exported_bundle_validation_not_doctrine_authority",
                "doctrine_completeness_overclaim_rejected": True,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": observed,
            "missing_negative_cases": [],
            "error_codes": sorted({str(finding["error_code"]) for finding in all_findings}),
            "findings": all_findings,
            "private_state_scan": scan_result,
            "accepted_standard_ids": sorted(str(row["standard_id"]) for row in accepted_rows),
            "rejected_standard_ids": standards_result["rejected_standard_ids"],
            "duplicate_standard_slugs": standards_result["duplicate_standard_slugs"],
            "standard_group_index": standard_group_index,
            "grammar_error_counts": dict(
                sorted(Counter(str(finding["error_code"]) for finding in all_findings).items())
            ),
            "receipt_expectation_coverage": receipt_expectation_coverage,
            "paper_module_results": paper_result["module_results"],
            "valid_module_slugs": paper_result["valid_module_slugs"],
            "invalid_module_slugs": paper_result["invalid_module_slugs"],
            "rejected_module_ids": paper_result["invalid_module_slugs"],
            "source_pattern_ids": ["exported_standards_registry", "exported_paper_modules"],
            "bundle_inputs": [
                public_relative_path(manifest_path, display_root=public_root),
                public_relative_path(standards_path, display_root=public_root),
                *[
                    public_relative_path(path, display_root=public_root)
                    for path in sorted((input_path / "paper_modules").glob("*.md"))
                ],
            ],
        }
    )
    receipt_path = _write_standards_bundle_receipt(out_dir, result, public_root=public_root)
    result["receipt_paths"] = [receipt_path]
    return result


def _strip_microcosm_prefix(ref: str) -> str:
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _source_module_manifest_path(input_dir: str | Path) -> Path:
    return Path(input_dir) / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    row_path = str(row.get("path") or "")
    if target_ref:
        target = public_root / target_ref
        if target.exists() or not row_path:
            return target, target_ref
        relocated = manifest_path.parent / row_path
        return relocated, public_relative_path(relocated, display_root=public_root)
    if row_path:
        target = manifest_path.parent / row_path
        return target, public_relative_path(target, display_root=public_root)
    return public_root, ""


def _source_artifact_paths(input_dir: str | Path, *, public_root: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    paths = [manifest_path]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return paths
    for row in _json_rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def validate_source_module_imports(input_dir: str | Path, *, public_root: Path) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = public_relative_path(manifest_path, display_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "EXECUTABLE_GRAMMAR_SOURCE_MODULE_MANIFEST_MISSING",
                "Executable-grammar metabolism bundle requires source_module_manifest.json for copied macro specimen bodies.",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
        return {
            "status": "blocked",
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "modules": [],
            "findings": findings,
            "observed_negative_cases": {},
        }

    manifest = read_json_strict(manifest_path)
    module_rows = _json_rows(manifest, "modules")
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "EXECUTABLE_GRAMMAR_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "EXECUTABLE_GRAMMAR_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied executable-grammar macro bodies may live in the bundle, not in receipts.",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("module_count") != len(module_rows):
        findings.append(
            _finding(
                "EXECUTABLE_GRAMMAR_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )

    for row in module_rows:
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        material_class = str(row.get("material_class") or "")
        relation = str(row.get("source_to_target_relation") or "")
        expected_digest = str(row.get("sha256") or "")
        source_ref = str(row.get("source_ref") or "")
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "EXECUTABLE_GRAMMAR_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "EXECUTABLE_GRAMMAR_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Executable-grammar body imports may include only public macro standard, tool, or receipt bodies.",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "EXECUTABLE_GRAMMAR_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if relation not in SOURCE_MODULE_RELATIONS:
            findings.append(
                _finding(
                    "EXECUTABLE_GRAMMAR_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy.",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not (
            source_ref in SOURCE_MODULE_SOURCE_REF_EXACT
            or any(source_ref.startswith(prefix) for prefix in SOURCE_MODULE_SOURCE_REF_PREFIXES)
        ):
            findings.append(
                _finding(
                    "EXECUTABLE_GRAMMAR_SOURCE_REF_UNEXPECTED",
                    "Source module rows must point at the executable grammar specimen or its governed standards-registry/type-plane support bodies.",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "EXECUTABLE_GRAMMAR_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the public metabolism bundle.",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
            continue
        actual_digest = _sha256_file(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "EXECUTABLE_GRAMMAR_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "body_in_receipt": False,
            }
        )

    return {
        "status": PASS if not findings and modules else "blocked",
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "modules": modules,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _source_open_body_import_summary(source_imports: dict[str, Any]) -> dict[str, Any]:
    modules = _json_rows(source_imports, "modules")
    module_ids = [str(row.get("module_id")) for row in modules if row.get("module_id")]
    return {
        "schema_version": "executable_doctrine_grammar_source_open_body_imports_v1",
        "status": source_imports.get("status"),
        "source_import_class": SOURCE_IMPORT_CLASS if modules else "",
        "body_material_status": SOURCE_BODY_STATUS if modules else "",
        "body_material_count": len(modules),
        "body_material_ids": module_ids,
        "material_classes": sorted(
            {str(row.get("material_class")) for row in modules if row.get("material_class")}
        ),
        "source_manifest_refs": [
            source_imports["source_module_manifest_ref"]
        ]
        if source_imports.get("source_module_manifest_ref")
        else [],
        "aggregate_floor_ref": (
            f"{source_imports['source_module_manifest_ref']}::modules"
            if source_imports.get("source_module_manifest_ref")
            else ""
        ),
        "body_in_receipt": False,
        "authority_ceiling": {
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "public_leaf_authority_authorized": False,
            "private_data_equivalence_authorized": False,
            "private_standards_engine_exported": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus copied executable-grammar specimen, "
            "standards-registry/type-plane, lattice-registry, kind-atlas, and standards "
            "option-surface bodies; receipts carry refs, digests, counts, and verdicts only."
        )
        if modules
        else "",
    }


def _scan_metabolism_bundle_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    paths: list[Path] = [input_dir / filename for filename in METABOLISM_REQUIRED_FILES]
    paths.extend(_source_artifact_paths(input_dir, public_root=public_root))
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return scan_paths(
        deduped,
        forbidden_classes=policy,
        display_root=public_root,
    )


def _metabolism_bundle_findings(
    *,
    manifest: dict[str, Any],
    board: dict[str, Any],
    receipt: dict[str, Any],
    readme_text: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if manifest.get("organ_id") != ORGAN_ID:
        findings.append(_finding("METABOLISM_BUNDLE_ORGAN_MISMATCH", "Bundle manifest does not target executable_doctrine_grammar."))
    if manifest.get("bundle_kind") != "exported_executable_grammar_metabolism_bundle":
        findings.append(_finding("METABOLISM_BUNDLE_KIND_MISSING", "Bundle manifest lacks the expected exported executable-grammar metabolism bundle kind."))
    if "private standards engine" not in str(manifest.get("anti_claim") or "").lower():
        findings.append(_finding("METABOLISM_BUNDLE_ANTI_CLAIM_WEAK", "Bundle manifest anti-claim must reject private standards-engine export."))

    missing_board_keys = [
        key for key in METABOLISM_REQUIRED_BOARD_KEYS if key not in board
    ]
    if missing_board_keys:
        findings.append(
            _finding(
                "METABOLISM_BOARD_REQUIRED_KEYS_MISSING",
                "Grammar board is missing required public specimen keys.",
                subject_id=",".join(missing_board_keys),
                subject_kind="grammar_board",
            )
        )
    if board.get("schema_version") != "executable_grammar_metabolism_specimen_v0":
        findings.append(_finding("METABOLISM_BOARD_SCHEMA_UNEXPECTED", "Grammar board schema is not the executable grammar metabolism specimen schema."))
    if board.get("status") not in {PASS, "ok"}:
        findings.append(_finding("METABOLISM_BOARD_STATUS_NOT_OK", "Grammar board does not carry an ok/pass status."))
    if not _string_list(board.get("grammar_rules")):
        findings.append(_finding("METABOLISM_BOARD_RULES_MISSING", "Grammar board has no executable grammar rules."))
    if not _string_list(board.get("cases")):
        findings.append(_finding("METABOLISM_BOARD_CASES_MISSING", "Grammar board has no public fixture cases."))
    if not _string_list(board.get("provider_replay_bridge")):
        findings.append(_finding("METABOLISM_PROVIDER_REPLAY_BRIDGE_MISSING", "Provider replay bridge rows are absent."))
    source_capsules = board.get("source_capsule_provenance")
    if not isinstance(source_capsules, dict) or not source_capsules:
        findings.append(_finding("METABOLISM_SOURCE_CAPSULES_MISSING", "Source capsule provenance is absent."))
    if "not a public release" not in str(board.get("claim_boundary") or "").lower():
        findings.append(_finding("METABOLISM_CLAIM_BOUNDARY_WEAK", "Claim boundary must reject public-release authority."))
    if "private registry" not in str(board.get("public_safety_boundary") or "").lower():
        findings.append(_finding("METABOLISM_PUBLIC_SAFETY_BOUNDARY_WEAK", "Public safety boundary must reject private registry export."))
    if not _string_list(board.get("anti_claims")):
        findings.append(_finding("METABOLISM_ANTI_CLAIMS_MISSING", "Grammar board has no anti-claim rows."))

    if receipt.get("schema_version") != "receipt_v0":
        findings.append(_finding("METABOLISM_RECEIPT_SCHEMA_UNEXPECTED", "Macro specimen receipt schema is unexpected."))
    if receipt.get("status") not in {PASS, "ok"} or receipt.get("result") not in {PASS, "ok"}:
        findings.append(_finding("METABOLISM_RECEIPT_STATUS_NOT_OK", "Macro specimen receipt does not carry ok/pass status and result."))
    if not _string_list(receipt.get("evidence_refs")):
        findings.append(_finding("METABOLISM_RECEIPT_EVIDENCE_REFS_MISSING", "Macro specimen receipt has no evidence refs."))
    if not _string_list(receipt.get("omissions")):
        findings.append(_finding("METABOLISM_RECEIPT_OMISSIONS_MISSING", "Macro specimen receipt has no omission anti-claims."))
    summary = receipt.get("summary")
    if not isinstance(summary, dict) or int(summary.get("source_capsule_count") or 0) <= 0:
        findings.append(_finding("METABOLISM_RECEIPT_SOURCE_CAPSULE_COUNT_MISSING", "Macro specimen receipt summary does not count source capsules."))
    if "private standards engine" not in readme_text.lower():
        findings.append(_finding("METABOLISM_README_BOUNDARY_MISSING", "Specimen README does not state the private-standards-engine boundary."))
    return findings


def _write_metabolism_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: Path,
) -> str:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    path = target / METABOLISM_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="executable_doctrine_grammar_metabolism_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "artifact_refs": validation_result["artifact_refs"],
            "artifact_digests": validation_result["artifact_digests"],
            "source_root": validation_result["source_root"],
            "source_refs": validation_result["source_refs"],
            "source_module_imports": validation_result["source_module_imports"],
            "source_open_body_imports": validation_result["source_open_body_imports"],
            "body_material_status": validation_result["body_material_status"],
            "body_copied_material_count": validation_result["body_copied_material_count"],
            "grammar_rule_count": validation_result["grammar_rule_count"],
            "grammar_case_count": validation_result["grammar_case_count"],
            "source_capsule_count": validation_result["source_capsule_count"],
            "provider_replay_bridge_case_count": validation_result[
                "provider_replay_bridge_case_count"
            ],
            "body_text_in_receipt": False,
            "fixture_regression_required_elsewhere": True,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def validate_executable_grammar_metabolism_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    manifest_path = input_path / "bundle_manifest.json"
    readme_path = input_path / "README.md"
    board_path = input_path / "grammar_board.json"
    receipt_path = input_path / "receipt.json"
    manifest = read_json_strict(manifest_path)
    board = read_json_strict(board_path)
    receipt = read_json_strict(receipt_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"{manifest_path}: manifest must be a JSON object")
    if not isinstance(board, dict):
        raise ValueError(f"{board_path}: grammar board must be a JSON object")
    if not isinstance(receipt, dict):
        raise ValueError(f"{receipt_path}: receipt must be a JSON object")
    readme_text = readme_path.read_text(encoding="utf-8")

    source_imports = validate_source_module_imports(input_path, public_root=public_root)
    scan_result = _receipt_safe_scan_result(
        _scan_metabolism_bundle_inputs(input_path, public_root)
    )
    findings = [
        *_metabolism_bundle_findings(
            manifest=manifest,
            board=board,
            receipt=receipt,
            readme_text=readme_text,
        ),
        *source_imports["findings"],
    ]
    source_open_body_imports = _source_open_body_import_summary(source_imports)
    source_capsules = board.get("source_capsule_provenance")
    source_capsule_count = len(source_capsules) if isinstance(source_capsules, dict) else 0
    artifact_paths = [readme_path, board_path, receipt_path]
    artifact_refs = [
        public_relative_path(path, display_root=public_root) for path in artifact_paths
    ]

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.executable_grammar_metabolism_bundle",
        command=command,
    )
    result.update(
        {
            "status": (
                PASS
                if not findings
                and scan_result["status"] == PASS
                and source_imports["status"] == PASS
                else "blocked"
            ),
            "input_mode": "exported_executable_grammar_metabolism_bundle",
            "bundle_id": str(manifest.get("bundle_id") or ""),
            "anti_claim": (
                "The exported executable-grammar metabolism bundle validates an exact "
                "public macro specimen plus standards-registry/type-plane support copy. "
                "It does not publish private standards engines, raw operator notes, "
                "provider transcripts, account/session state, doctrine completeness, "
                "or release authority."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": "executable_doctrine_grammar_macro_specimen_validation_not_doctrine_authority",
                "doctrine_completeness_authority": False,
                "private_standards_engine_exported": False,
                "provider_payload_bodies_exported": False,
                "publication_authorized": False,
                "release_authorized": False,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": {},
            "missing_negative_cases": [],
            "error_codes": sorted(str(finding["error_code"]) for finding in findings),
            "findings": findings,
            "private_state_scan": scan_result,
            "artifact_refs": artifact_refs,
            "artifact_digests": {
                public_relative_path(path, display_root=public_root): _sha256_file(path)
                for path in artifact_paths
            },
            "source_module_imports": {
                "status": source_imports["status"],
                "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
                "module_count": source_imports["module_count"],
                "modules": source_imports["modules"],
                "findings": source_imports["findings"],
            },
            "source_open_body_imports": source_open_body_imports,
            "body_material_status": source_open_body_imports["body_material_status"],
            "body_copied_material_count": source_open_body_imports["body_material_count"],
            "source_root": str(manifest.get("source_root") or ""),
            "source_refs": [
                str(module.get("source_ref"))
                for module in source_imports["modules"]
                if module.get("source_ref")
            ],
            "grammar_rule_count": len(_string_list(board.get("grammar_rules"))),
            "grammar_case_count": len(_string_list(board.get("cases"))),
            "source_capsule_count": source_capsule_count,
            "provider_replay_bridge_case_count": len(
                _string_list(board.get("provider_replay_bridge"))
            ),
            "body_text_in_receipt": False,
        }
    )
    receipt_ref = _write_metabolism_bundle_receipt(
        out_dir,
        result,
        public_root=public_root,
    )
    result["receipt_paths"] = [receipt_ref]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command_name")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("validate-standards-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    metabolism_parser = subparsers.add_parser("validate-executable-grammar-metabolism-bundle")
    metabolism_parser.add_argument("--input", required=True)
    metabolism_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command_name == "validate":
        command = (
            "python -m microcosm_core.organs.executable_doctrine_grammar "
            f"validate --input {args.input} --out {args.out}"
        )
        result = validate(args.input, args.out, command=command)
    elif args.command_name == "validate-standards-bundle":
        command = (
            "python -m microcosm_core.organs.executable_doctrine_grammar "
            f"validate-standards-bundle --input {args.input} --out {args.out}"
        )
        result = validate_standards_bundle(args.input, args.out, command=command)
    elif args.command_name == "validate-executable-grammar-metabolism-bundle":
        command = (
            "python -m microcosm_core.organs.executable_doctrine_grammar "
            "validate-executable-grammar-metabolism-bundle "
            f"--input {args.input} --out {args.out}"
        )
        result = validate_executable_grammar_metabolism_bundle(
            args.input,
            args.out,
            command=command,
        )
    else:
        parser.error(
            "expected subcommand: validate, validate-standards-bundle, "
            "or validate-executable-grammar-metabolism-bundle"
        )
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
