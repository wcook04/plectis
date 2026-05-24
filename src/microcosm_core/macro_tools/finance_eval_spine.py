from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
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


BUNDLE_RESULT_NAME = "exported_finance_eval_bundle_validation_result.json"
REPORT_SCHEMA = "microcosm_finance_eval_bundle_validation_report_v1"
MANIFEST_NAME = "bundle_manifest.json"
SOURCE_MANIFEST_NAME = "source_module_manifest.json"
CONTRACT_NAME = "finance_eval_runtime_contract.json"
OPERATING_PICTURE_NAME = "finance_eval_operating_picture.json"
SOURCE_MODULE_ROOT = Path("source_modules/tools/finance")
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_OPEN_BODY_POLICY = "source_bodies_copied_into_bundle_not_receipt"
REQUIRED_MODULES = (
    "event_keys.py",
    "admit_forecasts.py",
    "resolve_forecasts.py",
    "eval_replay.py",
    "historical_replay.py",
    "calibrate_forecast_probabilities.py",
    "variant_registry.py",
    "compare_variants.py",
    "build_eval_operating_picture.py",
)
REQUIRED_INPUTS = (
    *(SOURCE_MODULE_ROOT / name for name in REQUIRED_MODULES),
    Path(OPERATING_PICTURE_NAME),
    Path(CONTRACT_NAME),
    Path(SOURCE_MANIFEST_NAME),
)
REQUIRED_CLASSIFICATIONS = {
    "copied_non_secret_macro_body",
    "source_faithful_refactor",
    "real_macro_receipt",
    "diagnostic_or_routing_refactor",
    "secret_exclusion",
}
ALLOWED_MATERIAL_CLASSES = {
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_microcosm_runtime_contract",
    "public_microcosm_bundle_manifest",
}
REQUIRED_SOURCE_ANCHORS = {
    "event_keys.py": (
        "finance_comparison_event_key_v0",
        "comparison_event_key_authority",
    ),
    "admit_forecasts.py": (
        "finance_forecast_claim_v1",
        "comparison_event_key",
        "CP1",
    ),
    "resolve_forecasts.py": (
        "comparison_event_key",
        "Resolve matured CP1-admitted finance forecast claims",
    ),
    "eval_replay.py": (
        "MODE_CP1_ADMITTED_ONLY",
        "finance_forecast_scorecard_v1",
        "No optimizer mutation",
    ),
    "historical_replay.py": (
        "walk_forward_shadow",
        "optimizer_permission",
        "calculator_mutation_permission",
    ),
    "calibrate_forecast_probabilities.py": (
        "shadow_only",
        "finance_probability_calibrator_v0",
    ),
    "variant_registry.py": (
        "optimizer_permission",
        "calculator_mutation_permission",
        "shadow",
    ),
    "compare_variants.py": (
        "paired_by",
        "comparison_event_key",
        "optimizer_permission",
    ),
    "build_eval_operating_picture.py": (
        "finance_eval_operating_picture_v0",
        "calculator_mutation_permission",
        "optimizer_permission",
    ),
}
FALSE_AUTHORITY_FLAGS = (
    "trading_advice_authorized",
    "financial_advice_authorized",
    "investment_recommendation_authorized",
    "portfolio_action_authorized",
    "live_market_data_authorized",
    "provider_calls_authorized",
    "provider_payload_exported",
    "private_account_state_exported",
    "private_portfolio_exported",
    "forecast_performance_claim",
    "performance_guarantee_claim",
    "optimizer_mutation_authorized",
    "calculator_weight_mutation_authorized",
    "release_authorized",
    "publication_authorized",
    "hosted_public_authorized",
)
OPERATING_FALSE_GATES = (
    ("calibration_gate", "live_probability_mutation_allowed"),
    ("model_selection", "calculator_mutation_permission"),
    ("model_selection", "optimizer_permission"),
    ("model_selection", "mutation_permission"),
    ("variant_gate", "calculator_mutation_permission"),
)
ANTI_CLAIM = (
    "The finance forecast evaluation spine validates copied evaluator, replay, "
    "calibration, variant, and operating-picture machinery for local audit. It "
    "does not provide trading, financial, or investment advice; call live data "
    "providers; export private account or portfolio state; claim forecast "
    "performance; mutate optimizer or calculator weights; publish; host; or "
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
    text = path.read_text(encoding="utf-8")
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if isinstance(item, str) and item]


def _get_path(payload: Mapping[str, Any], keys: Iterable[str]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


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
    except Exception as exc:  # pragma: no cover - strict parser message varies.
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


def _source_manifest(input_dir: Path, manifest: Mapping[str, Any], *, public_root: Path) -> dict[str, Any]:
    declared = _declared_files(manifest)
    rows: list[dict[str, Any]] = []
    for rel in REQUIRED_INPUTS:
        path = input_dir / rel
        declared_row = declared.get(rel.as_posix(), {})
        sha256 = _file_sha256(path)
        expected_sha256 = declared_row.get("sha256")
        actual_line_count = _line_count(path)
        expected_line_count = declared_row.get("line_count")
        rows.append(
            {
                "path": rel.as_posix(),
                "display_ref": _display(path, public_root=public_root),
                "source_ref": declared_row.get("source_ref"),
                "material_class": declared_row.get("material_class"),
                "source_import_class": declared_row.get("source_import_class"),
                "exists": path.is_file(),
                "sha256": sha256,
                "expected_sha256": expected_sha256,
                "digest_status": "match" if sha256 and sha256 == expected_sha256 else "mismatch",
                "line_count": actual_line_count,
                "expected_line_count": expected_line_count,
                "line_count_status": (
                    "match" if actual_line_count == expected_line_count else "mismatch"
                ),
                "body_in_receipt": False,
            }
        )
    return {
        "inputs": rows,
        "declared_file_count": len(declared),
        "required_input_count": len(REQUIRED_INPUTS),
        "all_expected_digests_matched": all(row["digest_status"] == "match" for row in rows),
        "all_expected_line_counts_matched": all(
            row["line_count_status"] == "match" for row in rows
        ),
        "body_in_receipt": False,
    }


def _validate_manifest(
    manifest: Mapping[str, Any],
    source_manifest_payload: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    if manifest.get("schema_version") != "microcosm_finance_eval_exported_bundle_manifest_v1":
        findings.append(
            _finding(
                "UNEXPECTED_MANIFEST_SCHEMA",
                "Bundle manifest schema must be the finance eval exported bundle schema.",
                source=MANIFEST_NAME,
                expected="microcosm_finance_eval_exported_bundle_manifest_v1",
                observed=manifest.get("schema_version"),
            )
        )
    if manifest.get("source_open_body_policy") != SOURCE_OPEN_BODY_POLICY:
        findings.append(
            _finding(
                "SOURCE_OPEN_BODY_POLICY_MISMATCH",
                "Bundle must state that copied bodies live in the bundle, not in the receipt.",
                source=MANIFEST_NAME,
                expected=SOURCE_OPEN_BODY_POLICY,
                observed=manifest.get("source_open_body_policy"),
            )
        )
    classifications = set(_strings(manifest.get("classification")))
    missing_classifications = sorted(REQUIRED_CLASSIFICATIONS - classifications)
    if missing_classifications:
        findings.append(
            _finding(
                "MISSING_CLASSIFICATION",
                "Bundle manifest is missing required import classifications.",
                source=MANIFEST_NAME,
                expected=sorted(REQUIRED_CLASSIFICATIONS),
                observed=sorted(classifications),
            )
        )
    if manifest.get("expected_source_module_count") != len(REQUIRED_MODULES):
        findings.append(
            _finding(
                "SOURCE_MODULE_COUNT_MISMATCH",
                "Manifest source module count must match the required evaluator body set.",
                source=MANIFEST_NAME,
                expected=len(REQUIRED_MODULES),
                observed=manifest.get("expected_source_module_count"),
            )
        )
    if manifest.get("real_substrate_used") is not True:
        findings.append(
            _finding(
                "REAL_SUBSTRATE_NOT_DECLARED",
                "Finance eval bundle must declare real substrate use.",
                source=MANIFEST_NAME,
            )
        )
    if manifest.get("synthetic_fixture_standin_allowed") is not False:
        findings.append(
            _finding(
                "SYNTHETIC_STANDIN_ALLOWED",
                "Synthetic stand-ins are not authority for this finance import.",
                source=MANIFEST_NAME,
            )
        )
    for row in _as_list(manifest.get("files")):
        if not isinstance(row, Mapping):
            findings.append(
                _finding(
                    "INVALID_MANIFEST_FILE_ROW",
                    "Manifest files must be object rows.",
                    source=MANIFEST_NAME,
                )
            )
            continue
        path = str(row.get("path") or "")
        if row.get("material_class") not in ALLOWED_MATERIAL_CLASSES:
            findings.append(
                _finding(
                    "UNSUPPORTED_MATERIAL_CLASS",
                    "Bundle file declares an unsupported material class.",
                    source=path or MANIFEST_NAME,
                    expected=sorted(ALLOWED_MATERIAL_CLASSES),
                    observed=row.get("material_class"),
                )
            )
        if row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "BODY_IN_RECEIPT_NOT_FALSE",
                    "Bundle file rows must keep source bodies out of receipts.",
                    source=path or MANIFEST_NAME,
                )
            )
    if source_manifest_payload.get("schema_version") != "microcosm_finance_eval_source_module_manifest_v1":
        findings.append(
            _finding(
                "UNEXPECTED_SOURCE_MANIFEST_SCHEMA",
                "Source module manifest schema must be the finance eval source module manifest.",
                source=SOURCE_MANIFEST_NAME,
                expected="microcosm_finance_eval_source_module_manifest_v1",
                observed=source_manifest_payload.get("schema_version"),
            )
        )
    if source_manifest_payload.get("module_count") != len(REQUIRED_MODULES):
        findings.append(
            _finding(
                "SOURCE_MANIFEST_MODULE_COUNT_MISMATCH",
                "Source manifest module count must match the required evaluator body set.",
                source=SOURCE_MANIFEST_NAME,
                expected=len(REQUIRED_MODULES),
                observed=source_manifest_payload.get("module_count"),
            )
        )


def _validate_digests(
    source_manifest: Mapping[str, Any], findings: list[dict[str, Any]]
) -> None:
    for row in _as_list(source_manifest.get("inputs")):
        if not isinstance(row, Mapping):
            continue
        if row.get("exists") is not True:
            findings.append(
                _finding(
                    "MISSING_REQUIRED_BUNDLE_INPUT",
                    "Required finance eval bundle input is missing.",
                    source=str(row.get("path") or ""),
                )
            )
        if row.get("digest_status") != "match":
            findings.append(
                _finding(
                    "BUNDLE_DIGEST_MISMATCH",
                    "Required finance eval bundle input digest does not match the manifest.",
                    source=str(row.get("path") or ""),
                    expected=row.get("expected_sha256"),
                    observed=row.get("sha256"),
                )
            )
        if row.get("line_count_status") != "match":
            findings.append(
                _finding(
                    "BUNDLE_LINE_COUNT_MISMATCH",
                    "Required finance eval bundle input line count does not match the manifest.",
                    source=str(row.get("path") or ""),
                    expected=row.get("expected_line_count"),
                    observed=row.get("line_count"),
                )
            )
        if row.get("material_class") not in ALLOWED_MATERIAL_CLASSES:
            findings.append(
                _finding(
                    "REQUIRED_INPUT_MATERIAL_CLASS_MISMATCH",
                    "Required finance eval input must declare an allowed public material class.",
                    source=str(row.get("path") or ""),
                    expected=sorted(ALLOWED_MATERIAL_CLASSES),
                    observed=row.get("material_class"),
                )
            )


def _validate_source_anchors(input_dir: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for module_name, anchors in REQUIRED_SOURCE_ANCHORS.items():
        path = input_dir / SOURCE_MODULE_ROOT / module_name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        missing = [anchor for anchor in anchors if anchor not in text]
        if missing:
            findings.append(
                _finding(
                    "SOURCE_ANCHOR_MISSING",
                    "Copied finance evaluator body is missing a required public anchor.",
                    source=(SOURCE_MODULE_ROOT / module_name).as_posix(),
                    expected=list(anchors),
                    observed={"missing": missing},
                )
            )
        rows.append(
            {
                "module": f"tools/finance/{module_name}",
                "anchor_count": len(anchors),
                "missing_anchor_count": len(missing),
                "body_in_receipt": False,
            }
        )
    return {
        "module_anchor_rows": rows,
        "checked_module_count": len(rows),
        "missing_anchor_count": sum(row["missing_anchor_count"] for row in rows),
        "body_in_receipt": False,
    }


def _validate_contract(contract: Mapping[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    if contract.get("schema_version") != "microcosm_finance_eval_runtime_contract_v1":
        findings.append(
            _finding(
                "UNEXPECTED_CONTRACT_SCHEMA",
                "Runtime contract schema must match the finance eval contract.",
                source=CONTRACT_NAME,
                expected="microcosm_finance_eval_runtime_contract_v1",
                observed=contract.get("schema_version"),
            )
        )
    if contract.get("source_open_body_policy") != SOURCE_OPEN_BODY_POLICY:
        findings.append(
            _finding(
                "CONTRACT_SOURCE_OPEN_POLICY_MISMATCH",
                "Runtime contract must state that bodies are copied into the bundle, not receipts.",
                source=CONTRACT_NAME,
                expected=SOURCE_OPEN_BODY_POLICY,
                observed=contract.get("source_open_body_policy"),
            )
        )
    required_modules = set(_strings(contract.get("required_modules")))
    expected_modules = {f"tools/finance/{name}" for name in REQUIRED_MODULES}
    if required_modules != expected_modules:
        findings.append(
            _finding(
                "CONTRACT_REQUIRED_MODULES_MISMATCH",
                "Runtime contract must name the complete finance evaluator module set.",
                source=CONTRACT_NAME,
                expected=sorted(expected_modules),
                observed=sorted(required_modules),
            )
        )
    authority = _as_dict(contract.get("authority_ceiling"))
    false_flags = {
        key: authority.get(key)
        for key in FALSE_AUTHORITY_FLAGS
        if authority.get(key) is not False
    }
    for key, value in false_flags.items():
        findings.append(
            _finding(
                "AUTHORITY_CEILING_OVERCLAIM",
                "Finance eval authority ceiling flag must be false.",
                source=f"{CONTRACT_NAME}::authority_ceiling.{key}",
                expected=False,
                observed=value,
            )
        )
    return {
        "contract_id": contract.get("contract_id"),
        "source_open_body_policy": contract.get("source_open_body_policy"),
        "required_module_count": len(required_modules),
        "false_authority_flag_count": len(FALSE_AUTHORITY_FLAGS) - len(false_flags),
        "authority_overclaim_count": len(false_flags),
        "body_in_receipt": False,
    }


def _validate_operating_picture(
    operating_picture: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    if operating_picture.get("schema_version") != "finance_eval_operating_picture_v0":
        findings.append(
            _finding(
                "UNEXPECTED_OPERATING_PICTURE_SCHEMA",
                "Operating picture must be the real finance eval operating picture schema.",
                source=OPERATING_PICTURE_NAME,
                expected="finance_eval_operating_picture_v0",
                observed=operating_picture.get("schema_version"),
            )
        )
    false_gate_rows: list[dict[str, Any]] = []
    for keys in OPERATING_FALSE_GATES:
        value = _get_path(operating_picture, keys)
        if value is not False:
            findings.append(
                _finding(
                    "OPERATING_PICTURE_MUTATION_GATE_OPEN",
                    "Finance eval operating picture must not authorize mutation.",
                    source=f"{OPERATING_PICTURE_NAME}::{'.'.join(keys)}",
                    expected=False,
                    observed=value,
                )
            )
        false_gate_rows.append(
            {
                "gate_ref": f"{OPERATING_PICTURE_NAME}::{'.'.join(keys)}",
                "observed": value,
                "required_false": True,
                "body_in_receipt": False,
            }
        )
    comparison_authority = _get_path(
        operating_picture, ("variant_gate", "comparison_key_authority")
    )
    if comparison_authority != "tools/finance/event_keys.py":
        findings.append(
            _finding(
                "COMPARISON_KEY_AUTHORITY_MISMATCH",
                "Finance variant gate must point comparison-event-key authority at tools/finance/event_keys.py.",
                source=f"{OPERATING_PICTURE_NAME}::variant_gate.comparison_key_authority",
                expected="tools/finance/event_keys.py",
                observed=comparison_authority,
            )
        )
    return {
        "schema_version": operating_picture.get("schema_version"),
        "generated_at": operating_picture.get("generated_at"),
        "production_cp1_admitted_count": _get_path(
            operating_picture, ("integrity", "production_cp1_admitted_count")
        ),
        "lifecycle_admitted_count": _get_path(
            operating_picture, ("lifecycle", "admitted_count")
        ),
        "false_gate_rows": false_gate_rows,
        "comparison_key_authority": comparison_authority,
        "comparison_key_schema": _get_path(
            operating_picture, ("variant_gate", "comparison_key_schema")
        ),
        "body_in_receipt": False,
    }


def _scan_required_inputs(
    input_dir: Path, *, public_root: Path, findings: list[dict[str, Any]]
) -> dict[str, Any]:
    paths = [input_dir / rel for rel in REQUIRED_INPUTS if (input_dir / rel).is_file()]
    policy_path = _policy_path(public_root)
    scan = scan_paths(
        paths,
        forbidden_classes=load_forbidden_classes(policy_path),
        source_context="target",
        display_root=public_root,
    )
    if scan.get("blocking_hit_count", 0) != 0:
        findings.append(
            _finding(
                "SECRET_EXCLUSION_BLOCKING_HIT",
                "Secret-exclusion scan found blocking credential/account-bound material.",
                source="secret_exclusion_scan",
                expected=0,
                observed=scan.get("blocking_hit_count"),
            )
        )
    return scan


def validate_finance_eval_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "microcosm finance-eval-spine validate-finance-eval-bundle",
) -> dict[str, Any]:
    input_path = Path(input_dir)
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    findings: list[dict[str, Any]] = []

    manifest = _load_json_input(input_path / MANIFEST_NAME, findings, label="bundle manifest")
    source_manifest_payload = _load_json_input(
        input_path / SOURCE_MANIFEST_NAME, findings, label="source module manifest"
    )
    contract = _load_json_input(input_path / CONTRACT_NAME, findings, label="runtime contract")
    operating_picture = _load_json_input(
        input_path / OPERATING_PICTURE_NAME,
        findings,
        label="finance eval operating picture",
    )

    source_inventory = _source_manifest(input_path, manifest, public_root=public_root)
    _validate_manifest(manifest, source_manifest_payload, findings)
    _validate_digests(source_inventory, findings)
    anchor_summary = _validate_source_anchors(input_path, findings)
    contract_summary = _validate_contract(contract, findings)
    operating_gate_summary = _validate_operating_picture(operating_picture, findings)
    secret_scan = _scan_required_inputs(input_path, public_root=public_root, findings=findings)

    error_codes = [row["error_code"] for row in findings if row.get("error_code")]
    status = PASS if not error_codes else "blocked"
    source_module_refs = [
        (SOURCE_MODULE_ROOT / name).as_posix() for name in REQUIRED_MODULES
    ]
    material_counts = Counter(
        str(row.get("material_class") or "unknown")
        for row in _as_list(manifest.get("files"))
        if isinstance(row, Mapping)
    )
    public_runtime_refs = [
        row["display_ref"]
        for row in _as_list(source_inventory.get("inputs"))
        if isinstance(row, Mapping) and row.get("display_ref")
    ]

    result = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": status,
        "input_mode": "exported_finance_eval_bundle",
        "bundle_id": manifest.get("bundle_id")
        or "public_finance_forecast_evaluation_spine_bundle",
        "command": command,
        "source_import_class": SOURCE_IMPORT_CLASS,
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "classification": sorted(REQUIRED_CLASSIFICATIONS),
        "copied_macro_source_count": len(source_module_refs),
        "real_macro_receipt_count": 1,
        "counts_as_real_substrate_progress": status == PASS,
        "real_runtime_receipt": True,
        "synthetic_receipt_standin_allowed": False,
        "body_in_receipt": False,
        "source_module_refs": source_module_refs,
        "public_runtime_refs": public_runtime_refs,
        "material_class_counts": dict(sorted(material_counts.items())),
        "source_manifest": source_inventory,
        "anchor_summary": anchor_summary,
        "contract_summary": contract_summary,
        "operating_picture_gate_summary": operating_gate_summary,
        "authority_ceiling": _as_dict(contract.get("authority_ceiling")),
        "secret_exclusion_scan": secret_scan,
        "finding_count": len(findings),
        "error_codes": sorted(set(error_codes)),
        "findings": findings,
        "unsafe_payload_bodies_in_receipt": False,
        "receipt_paths": [f"receipts/{BUNDLE_RESULT_NAME}"],
        "anti_claim": ANTI_CLAIM,
    }
    write_json_atomic(target / BUNDLE_RESULT_NAME, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="finance_eval_spine",
        description="Validate the public finance forecast evaluation spine bundle.",
    )
    subparsers = parser.add_subparsers(dest="action")
    validate_parser = subparsers.add_parser("validate-finance-eval-bundle")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.action == "validate-finance-eval-bundle":
        command = (
            "microcosm finance-eval-spine validate-finance-eval-bundle "
            f"--input {args.input} --out {args.out}"
        )
        result = validate_finance_eval_bundle(args.input, args.out, command=command)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == PASS else 1

    parser.error("expected subcommand: validate-finance-eval-bundle")
    return 2


__all__ = [
    "BUNDLE_RESULT_NAME",
    "REQUIRED_MODULES",
    "SOURCE_IMPORT_CLASS",
    "SOURCE_OPEN_BODY_POLICY",
    "validate_finance_eval_bundle",
]
