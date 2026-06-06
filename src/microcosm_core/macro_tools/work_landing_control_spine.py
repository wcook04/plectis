from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)


BUNDLE_RESULT_NAME = "exported_work_landing_control_bundle_validation_result.json"
REPORT_SCHEMA = "microcosm_work_landing_control_bundle_validation_report_v1"
MANIFEST_NAME = "bundle_manifest.json"
SOURCE_MANIFEST_NAME = "source_module_manifest.json"
CONTRACT_NAME = "work_landing_control_runtime_contract.json"
SOURCE_MODULE_ROOT = Path("source_modules")
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_OPEN_BODY_POLICY = "source_bodies_copied_into_bundle_not_receipt"
REQUIRED_SOURCE_REFS = {
    "tools/meta/control/work_landing.py": (
        "build_parser",
        "admission-check",
        "begin",
        "build_work_landing_status",
    ),
    "system/lib/work_landing_status.py": (
        "ORDERED_CONTROLLER_ACTION_IDS",
        "FINALIZER_POLICIES",
        "build_work_landing_status",
        "build_work_landing_reconcile_plan",
        "build_workitem_write_admission",
    ),
    "tools/meta/control/mission_transaction_preflight.py": (
        "build_mission_transaction_landing_preflight",
        "--owned-path",
        "--session-id",
        "shared_index_quarantine",
    ),
    "system/lib/mission_transaction_landing_preflight.py": (
        "SHARED_INDEX_QUARANTINE_SCHEMA",
        "build_mission_transaction_landing_preflight",
        "private_index_scoped_commit_allowed",
        "LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON",
    ),
    "tools/meta/control/scoped_commit.py": (
        "Scoped-commit actuator using a private index and HEAD CAS",
        "perform_scoped_commit",
        "full-paths",
        "private-index scoped commit",
        "Never invokes `git commit` against the shared index",
    ),
}
REQUIRED_INPUTS = (
    *(SOURCE_MODULE_ROOT / source_ref for source_ref in REQUIRED_SOURCE_REFS),
    Path(CONTRACT_NAME),
    Path(SOURCE_MANIFEST_NAME),
)
REQUIRED_CLASSIFICATIONS = {
    "copied_non_secret_macro_body",
    "source_faithful_refactor",
    "real_runtime_receipt",
    "diagnostic_or_routing_refactor",
    "secret_exclusion",
}
ALLOWED_MATERIAL_CLASSES = {
    "public_macro_tool_body",
    "public_microcosm_bundle_manifest",
    "public_microcosm_runtime_contract",
}
FALSE_AUTHORITY_FLAGS = (
    "live_git_mutation_authorized",
    "live_task_ledger_mutation_authorized",
    "live_work_ledger_mutation_authorized",
    "live_claim_release_authorized",
    "shared_index_mutation_authorized",
    "private_index_commit_execution_authorized",
    "broad_stage_authorized",
    "broad_checkpoint_authorized",
    "provider_calls_authorized",
    "credential_export_authorized",
    "private_root_required",
    "publication_authorized",
    "release_authorized",
)
ANTI_CLAIM = (
    "The work-landing control spine validates copied non-secret macro "
    "control-plane source for local inspection. It does not run live Git "
    "mutations, mutate Task Ledger or Work Ledger state, release claims, stage "
    "broadly, call providers, export credentials, publish, or authorize release."
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


def _policy_path(public_root: Path) -> Path:
    candidate = public_root / "core/private_state_forbidden_classes.json"
    if candidate.is_file():
        return candidate
    for parent in Path(__file__).resolve(strict=False).parents:
        fallback = parent / "core/private_state_forbidden_classes.json"
        if fallback.is_file():
            return fallback
    return candidate


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if isinstance(item, str) and item]


def _finding(
    code: str,
    message: str,
    *,
    source: str | None = None,
    expected: Any | None = None,
    observed: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error_code": code,
        "message": message,
        "body_in_receipt": False,
    }
    if source:
        payload["source"] = source
    if expected is not None:
        payload["expected"] = expected
    if observed is not None:
        payload["observed"] = observed
    return payload


def _load_json_input(
    path: Path, findings: list[dict[str, Any]], *, label: str
) -> dict[str, Any]:
    if not path.is_file():
        findings.append(_finding("MISSING_INPUT", f"Missing {label}.", source=path.name))
        return {}
    try:
        payload = read_json_strict(path)
    except Exception as exc:  # pragma: no cover - strict parser wording varies.
        findings.append(
            _finding(
                "INVALID_JSON_INPUT",
                f"{label} is not valid strict JSON: {exc}",
                source=path.name,
            )
        )
        return {}
    if not isinstance(payload, dict):
        findings.append(
            _finding(
                "JSON_INPUT_NOT_OBJECT",
                f"{label} must be a JSON object.",
                source=path.name,
            )
        )
        return {}
    return payload


def _declared_files(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("path") or ""): row
        for row in _as_list(manifest.get("files"))
        if isinstance(row, Mapping) and row.get("path")
    }


def _source_manifest_summary(
    input_dir: Path,
    manifest: Mapping[str, Any],
    *,
    public_root: Path,
) -> dict[str, Any]:
    declared = _declared_files(manifest)
    rows: list[dict[str, Any]] = []
    missing_required: list[str] = []
    digest_mismatches: list[str] = []
    line_count_mismatches: list[str] = []
    material_class_violations: list[str] = []
    import_class_violations: list[str] = []

    for rel_path in REQUIRED_INPUTS:
        declared_row = declared.get(rel_path.as_posix())
        target = input_dir / rel_path
        sha256 = _file_sha256(target)
        line_count = _line_count(target)
        expected_sha256 = str(_as_dict(declared_row).get("expected_sha256") or "")
        expected_line_count = _as_dict(declared_row).get("expected_line_count")
        material_class = str(_as_dict(declared_row).get("material_class") or "")
        source_import_class = str(_as_dict(declared_row).get("source_import_class") or "")

        if declared_row is None or not target.is_file():
            missing_required.append(rel_path.as_posix())
        if sha256 and expected_sha256 and sha256 != expected_sha256:
            digest_mismatches.append(rel_path.as_posix())
        if line_count is not None and expected_line_count not in (line_count, str(line_count)):
            line_count_mismatches.append(rel_path.as_posix())
        if declared_row is not None and material_class not in ALLOWED_MATERIAL_CLASSES:
            material_class_violations.append(rel_path.as_posix())
        if (
            declared_row is not None
            and rel_path.as_posix().startswith("source_modules/")
            and source_import_class != SOURCE_IMPORT_CLASS
        ):
            import_class_violations.append(rel_path.as_posix())

        rows.append(
            {
                "path": rel_path.as_posix(),
                "display_ref": _display(target, public_root=public_root),
                "source_ref": _as_dict(declared_row).get("source_ref"),
                "exists": target.is_file(),
                "sha256": sha256,
                "expected_sha256": expected_sha256,
                "digest_status": (
                    "match"
                    if sha256 and expected_sha256 and sha256 == expected_sha256
                    else "missing_or_mismatch"
                ),
                "line_count": line_count,
                "expected_line_count": expected_line_count,
                "line_count_status": (
                    "match" if line_count is not None and expected_line_count == line_count else "mismatch"
                ),
                "material_class": material_class,
                "source_import_class": source_import_class,
                "body_in_receipt": False,
            }
        )

    return {
        "required_input_count": len(REQUIRED_INPUTS),
        "declared_file_count": len(declared),
        "all_expected_digests_matched": not missing_required and not digest_mismatches,
        "all_expected_line_counts_matched": not missing_required and not line_count_mismatches,
        "missing_required_inputs": sorted(missing_required),
        "digest_mismatch_paths": sorted(digest_mismatches),
        "line_count_mismatch_paths": sorted(line_count_mismatches),
        "material_class_violations": sorted(material_class_violations),
        "source_import_class_violations": sorted(import_class_violations),
        "inputs": rows,
        "body_in_receipt": False,
    }


def _anchor_summary(input_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing_anchor_count = 0
    for source_ref, anchors in REQUIRED_SOURCE_REFS.items():
        rel_path = SOURCE_MODULE_ROOT / source_ref
        path = input_dir / rel_path
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        missing = [anchor for anchor in anchors if anchor not in text]
        missing_anchor_count += len(missing)
        rows.append(
            {
                "module": source_ref,
                "anchor_count": len(anchors),
                "missing_anchor_count": len(missing),
                "missing_anchors": missing,
                "body_in_receipt": False,
            }
        )
    return {
        "checked_module_count": len(REQUIRED_SOURCE_REFS),
        "missing_anchor_count": missing_anchor_count,
        "module_anchor_rows": rows,
        "body_in_receipt": False,
    }


def _contract_summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    ceiling = _as_dict(contract.get("authority_ceiling"))
    false_flag_rows = [
        {
            "flag": flag,
            "observed": ceiling.get(flag),
            "required_false": True,
            "body_in_receipt": False,
        }
        for flag in FALSE_AUTHORITY_FLAGS
    ]
    overclaims = [row for row in false_flag_rows if row["observed"] is not False]
    classifications = set(_strings(contract.get("required_classifications")))
    missing_classifications = sorted(REQUIRED_CLASSIFICATIONS - classifications)
    return {
        "contract_id": contract.get("contract_id"),
        "source_open_body_policy": contract.get("source_open_body_policy"),
        "required_module_count": contract.get("required_module_count"),
        "false_authority_flag_count": len(false_flag_rows),
        "authority_overclaim_count": len(overclaims),
        "authority_overclaim_flags": [str(row["flag"]) for row in overclaims],
        "false_authority_rows": false_flag_rows,
        "missing_required_classifications": missing_classifications,
        "body_in_receipt": False,
    }


def _material_class_counts(source_manifest: Mapping[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    rows = _as_list(source_manifest.get("files")) or _as_list(source_manifest.get("modules"))
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        material_class = str(row.get("material_class") or "unknown")
        counts[material_class] = counts.get(material_class, 0) + 1
    counts["public_microcosm_runtime_contract"] = counts.get(
        "public_microcosm_runtime_contract", 0
    ) + 1
    counts["public_microcosm_bundle_manifest"] = counts.get(
        "public_microcosm_bundle_manifest", 0
    ) + 1
    return dict(sorted(counts.items()))


def validate_work_landing_control_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    target = Path(out_dir)
    public_root = _public_root_for_path(input_path)
    findings: list[dict[str, Any]] = []

    manifest = _load_json_input(input_path / MANIFEST_NAME, findings, label="bundle manifest")
    source_manifest = _load_json_input(
        input_path / SOURCE_MANIFEST_NAME, findings, label="source module manifest"
    )
    contract = _load_json_input(
        input_path / CONTRACT_NAME, findings, label="runtime contract"
    )

    source_summary = _source_manifest_summary(input_path, manifest, public_root=public_root)
    anchor_summary = _anchor_summary(input_path)
    contract_summary = _contract_summary(contract)

    if manifest.get("bundle_id") != "public_work_landing_control_spine_bundle":
        findings.append(
            _finding(
                "BUNDLE_ID_MISMATCH",
                "Bundle manifest must identify the work-landing control spine bundle.",
                source=MANIFEST_NAME,
                expected="public_work_landing_control_spine_bundle",
                observed=manifest.get("bundle_id"),
            )
        )
    if manifest.get("source_open_body_policy") != SOURCE_OPEN_BODY_POLICY:
        findings.append(
            _finding(
                "SOURCE_OPEN_POLICY_MISMATCH",
                "Bundle manifest must keep source bodies in the bundle, not receipts.",
                source=MANIFEST_NAME,
                expected=SOURCE_OPEN_BODY_POLICY,
                observed=manifest.get("source_open_body_policy"),
            )
        )
    if source_manifest.get("schema_version") != (
        "microcosm_work_landing_control_source_module_manifest_v1"
    ):
        findings.append(
            _finding(
                "UNEXPECTED_SOURCE_MANIFEST_SCHEMA",
                "Source module manifest schema must identify the work-landing control module inventory.",
                source=SOURCE_MANIFEST_NAME,
                expected="microcosm_work_landing_control_source_module_manifest_v1",
                observed=source_manifest.get("schema_version"),
            )
        )
    if source_manifest.get("module_count") != len(REQUIRED_SOURCE_REFS):
        findings.append(
            _finding(
                "SOURCE_MANIFEST_MODULE_COUNT_MISMATCH",
                "Source module manifest module count must match the required control-plane body set.",
                source=SOURCE_MANIFEST_NAME,
                expected=len(REQUIRED_SOURCE_REFS),
                observed=source_manifest.get("module_count"),
            )
        )
    if source_summary["missing_required_inputs"]:
        findings.append(
            _finding(
                "MISSING_REQUIRED_SOURCE_INPUT",
                "The work-landing control bundle is missing required copied sources.",
                source=SOURCE_MANIFEST_NAME,
                observed=source_summary["missing_required_inputs"],
            )
        )
    if source_summary["digest_mismatch_paths"]:
        findings.append(
            _finding(
                "SOURCE_DIGEST_MISMATCH",
                "Copied source body digests must match the source module manifest.",
                source=SOURCE_MANIFEST_NAME,
                observed=source_summary["digest_mismatch_paths"],
            )
        )
    if source_summary["line_count_mismatch_paths"]:
        findings.append(
            _finding(
                "SOURCE_LINE_COUNT_MISMATCH",
                "Copied source body line counts must match the source module manifest.",
                source=SOURCE_MANIFEST_NAME,
                observed=source_summary["line_count_mismatch_paths"],
            )
        )
    if source_summary["material_class_violations"]:
        findings.append(
            _finding(
                "MATERIAL_CLASS_NOT_ALLOWED",
                "Copied source inputs must stay inside the public-safe material-class floor.",
                source=SOURCE_MANIFEST_NAME,
                expected=sorted(ALLOWED_MATERIAL_CLASSES),
                observed=source_summary["material_class_violations"],
            )
        )
    if source_summary["source_import_class_violations"]:
        findings.append(
            _finding(
                "SOURCE_IMPORT_CLASS_MISMATCH",
                "Copied source modules must be classified as copied non-secret macro bodies.",
                source=SOURCE_MANIFEST_NAME,
                expected=SOURCE_IMPORT_CLASS,
                observed=source_summary["source_import_class_violations"],
            )
        )
    if anchor_summary["missing_anchor_count"]:
        findings.append(
            _finding(
                "SOURCE_ANCHOR_MISSING",
                "Copied control-plane modules must preserve required work-landing anchors.",
                observed=anchor_summary["module_anchor_rows"],
            )
        )
    if contract_summary["authority_overclaim_count"]:
        findings.append(
            _finding(
                "AUTHORITY_CEILING_OVERCLAIM",
                "Work-landing control runtime contract must keep live mutation authority false.",
                source=CONTRACT_NAME,
                observed=contract_summary["authority_overclaim_flags"],
            )
        )
    if contract_summary["missing_required_classifications"]:
        findings.append(
            _finding(
                "CLASSIFICATION_FLOOR_MISSING",
                "Runtime contract must include the source-open import classification floor.",
                source=CONTRACT_NAME,
                observed=contract_summary["missing_required_classifications"],
            )
        )

    scan_targets = [str(input_path / rel_path) for rel_path in REQUIRED_INPUTS]
    secret_scan = scan_paths(
        scan_targets,
        forbidden_classes=load_forbidden_classes(_policy_path(public_root)),
        source_context="target",
        display_root=public_root,
    )
    if secret_scan.get("blocking_hit_count", 0):
        findings.append(
            _finding(
                "SECRET_EXCLUSION_BLOCKING_HIT",
                "Copied work-landing control bundle contains credential/account-bound material.",
                observed=secret_scan.get("blocking_hit_count"),
            )
        )

    error_codes = sorted({str(row.get("error_code") or "") for row in findings})
    status = PASS if not findings else "blocked"
    public_refs = [
        _display(input_path / rel_path, public_root=public_root)
        for rel_path in REQUIRED_INPUTS
    ]
    report = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": status,
        "command": command
        or (
            "microcosm work-landing-control-spine validate-control-bundle "
            f"--input {input_path} --out {target}"
        ),
        "input_mode": "exported_work_landing_control_bundle",
        "bundle_id": manifest.get("bundle_id"),
        "classification": sorted(REQUIRED_CLASSIFICATIONS),
        "source_import_class": SOURCE_IMPORT_CLASS,
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "copied_macro_source_count": len(REQUIRED_SOURCE_REFS),
        "counts_as_real_substrate_progress": True,
        "real_runtime_receipt": True,
        "synthetic_receipt_standin_allowed": False,
        "body_in_receipt": False,
        "unsafe_payload_bodies_in_receipt": False,
        "material_class_counts": _material_class_counts(source_manifest),
        "source_manifest": source_summary,
        "anchor_summary": anchor_summary,
        "contract_summary": contract_summary,
        "authority_ceiling": contract.get("authority_ceiling", {}),
        "secret_exclusion_scan": secret_scan,
        "public_runtime_refs": public_refs,
        "blocked_overclaim_workitem_ref": (
            contract.get("blocked_overclaim_workitem_ref")
            or manifest.get("blocked_overclaim_workitem_ref")
        ),
        "anti_claim": ANTI_CLAIM,
        "finding_count": len(findings),
        "findings": findings,
        "error_codes": error_codes,
        "receipt_paths": [f"receipts/{BUNDLE_RESULT_NAME}"],
    }
    target.mkdir(parents=True, exist_ok=True)
    write_json_atomic(target / BUNDLE_RESULT_NAME, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    validate_parser = subparsers.add_parser("validate-control-bundle")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate_work_landing_control_bundle(
        args.input,
        args.out,
        command=(
            "microcosm work-landing-control-spine validate-control-bundle "
            f"--input {args.input} --out {args.out}"
        ),
    )
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
