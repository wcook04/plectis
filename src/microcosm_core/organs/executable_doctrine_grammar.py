from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command_name")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("validate-standards-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
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
    else:
        parser.error("expected subcommand: validate or validate-standards-bundle")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
