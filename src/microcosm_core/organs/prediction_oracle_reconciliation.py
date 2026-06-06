from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import types
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


ORGAN_ID = "prediction_oracle_reconciliation"
FIXTURE_ID = "first_wave.prediction_oracle_reconciliation"
VALIDATOR_ID = "validator.microcosm.organs.prediction_oracle_reconciliation"
MODULE_PATH = "microcosm_core.organs.prediction_oracle_reconciliation"
CARD_SCHEMA_VERSION = "prediction_oracle_reconciliation_command_card_v1"

RESULT_NAME = "prediction_oracle_reconciliation_result.json"
BOARD_NAME = "prediction_reconciliation_board.json"
VALIDATION_RECEIPT_NAME = "prediction_oracle_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "prediction_oracle_reconciliation_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_prediction_oracle_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = "copied_non_secret_macro_prediction_oracle_body_with_provenance"
TRUTH_DIFF_EQUITY_MODULE_ID = "prediction_oracle_tool_truth_diff_equity_body_import"
TRUTH_DIFF_HELPERS = (
    "_build_prediction_reconciliation_rows",
    "_build_prediction_reconciliation_summary",
)

PACKET_NAME = "reconciliation_packet.json"
NEGATIVE_INPUT_NAMES = (
    "invalid_cp2_target.json",
    "missing_bifurcation_resolution.json",
    "post_t_evidence_ref.json",
    "unconfirmed_equity_lane_claim.json",
    "unsafe_dossier_mutation.json",
    "trading_advice_overclaim.json",
    "numeric_large_miss_direction_hit.json",
    "missing_realized_numeric_truth.json",
    "degraded_feed_health_gates_numeric_truth.json",
    "asset_class_split_required.json",
)

EXPECTED_NEGATIVE_CASES = {
    "invalid_cp2_target": ["PREDICTION_CP2_TARGET_OUT_OF_UNIVERSE"],
    "missing_bifurcation_resolution": [
        "PREDICTION_CP1_BIFURCATION_UNRESOLVED"
    ],
    "post_t_evidence_ref": ["PREDICTION_ORACLE_POST_T_EVIDENCE_FORBIDDEN"],
    "unconfirmed_equity_lane_claim": [
        "PREDICTION_EQUITY_CONFIRMATION_REQUIRED"
    ],
    "unsafe_dossier_mutation": ["PREDICTION_DOSSIER_MUTATION_UNSAFE"],
    "trading_advice_overclaim": ["PREDICTION_TRADING_OR_ADVICE_OVERCLAIM"],
    "numeric_large_miss_direction_hit": [
        "PREDICTION_ORACLE_NUMERIC_LARGE_MISS_SURFACED"
    ],
    "missing_realized_numeric_truth": [
        "PREDICTION_ORACLE_MISSING_REALIZED_TRUTH_NOT_GRADED"
    ],
    "degraded_feed_health_gates_numeric_truth": [
        "PREDICTION_ORACLE_DEGRADED_FEED_HEALTH_GATED"
    ],
    "asset_class_split_required": [
        "PREDICTION_ORACLE_ASSET_CLASS_SPLIT_PRESERVED"
    ],
}

FORBIDDEN_AUTHORITY_FLAGS = (
    "trading_authorized",
    "financial_advice_authorized",
    "investment_advice_authorized",
    "live_market_data_authorized",
    "live_provider_calls_authorized",
    "provider_calls_authorized",
    "release_authorized",
    "publication_authorized",
    "private_data_equivalence_claim",
    "private_root_equivalence_authorized",
)

ALLOWED_DIRECTIONS = {"up", "down", "flat"}
DEGRADED_DIRECTION = "degraded"
ALLOWED_MUTATIONS = {"add_contradiction", "revise_confidence", "retire_claim"}
ALLOWED_ASSET_CLASSES = {"STOCK", "ETF"}
NUMERIC_LARGE_MISS_ABSOLUTE_FLOOR = 10.0
NUMERIC_LARGE_MISS_PERCENT_FLOOR = 5.0
NUMERIC_RECOMPUTE_TOLERANCE = 1e-9
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_prediction_reconciliation_fixture_only",
    "trading_authorized": False,
    "financial_advice_authorized": False,
    "investment_advice_authorized": False,
    "live_market_data_authorized": False,
    "live_provider_calls_authorized": False,
    "provider_calls_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
    "private_data_equivalence_claim": False,
    "dossier_mutation_authority": "public_fixture_delta_only",
}
ANTI_CLAIM = (
    "Prediction oracle reconciliation validates synthetic fixture mechanics for "
    "CP1 bifurcation resolution, CP2 target-universe gating, oracle grounding, "
    "diff grading, and bounded dossier mutation. It does not trade, give "
    "financial or investment advice, call live market providers, publish "
    "predictions, claim performance, import private data, or authorize release."
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
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (PACKET_NAME, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _strip_microcosm_prefix(ref: str) -> str:
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _source_module_manifest_path(input_dir: Path) -> Path:
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    row_path = str(row.get("path") or "")
    if target_ref:
        return public_root / target_ref, target_ref
    if row_path:
        target = manifest_path.parent / row_path
        return target, _display(target, public_root=public_root)
    return public_root, ""


def _prediction_oracle_source_manifest_path(
    input_dir: Path,
    *,
    public_root: Path,
) -> Path | None:
    direct = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if direct.is_file():
        return direct
    bundled = (
        public_root
        / "examples/prediction_oracle_reconciliation"
        / "exported_prediction_oracle_bundle"
        / SOURCE_MODULE_MANIFEST_NAME
    )
    return bundled if bundled.is_file() else None


def _truth_diff_equity_source_path(
    input_dir: Path | None,
    *,
    public_root: Path | None,
) -> tuple[Path, str, str] | None:
    if input_dir is None or public_root is None:
        return None
    manifest_path = _prediction_oracle_source_manifest_path(
        input_dir,
        public_root=public_root,
    )
    if manifest_path is None:
        return None
    manifest = read_json_strict(manifest_path)
    for row in _rows(manifest, "modules"):
        if row.get("module_id") != TRUTH_DIFF_EQUITY_MODULE_ID:
            continue
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        if target_path.is_file():
            return target_path, target_ref, _display(manifest_path, public_root=public_root)
    return None


def _source_artifact_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    paths = [manifest_path]
    for row in _rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def validate_source_module_imports(
    input_dir: Path,
    *,
    public_root: Path,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = _display(manifest_path, public_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "PREDICTION_SOURCE_MODULE_MANIFEST_MISSING",
                "Prediction oracle body floor requires a source_module_manifest.json for copied macro source bodies.",
                case_id="source_module_manifest_floor",
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
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "PREDICTION_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "PREDICTION_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied prediction-oracle macro bodies may live in source_artifacts, not in receipts.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_text_in_receipt") is True:
        findings.append(
            _finding(
                "PREDICTION_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                "Copied prediction-oracle macro body text may not be exported in receipts.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("module_count") != len(_rows(manifest, "modules")):
        findings.append(
            _finding(
                "PREDICTION_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )

    for row in _rows(manifest, "modules"):
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        material_class = str(row.get("material_class") or "")
        expected_digest = str(row.get("sha256") or "")
        relation = str(row.get("source_to_target_relation") or "")
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "PREDICTION_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "PREDICTION_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Prediction oracle may import only public macro pattern/tool bodies.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "PREDICTION_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_text_in_receipt") is True:
            findings.append(
                _finding(
                    "PREDICTION_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                    "Source module rows must not export copied macro body text in receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if relation not in {"exact_copy", "source_faithful_json_slice"}:
            findings.append(
                _finding(
                    "PREDICTION_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy or source_faithful_json_slice.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "PREDICTION_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
            continue
        actual_digest = _sha256(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "PREDICTION_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": str(row.get("source_ref") or ""),
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "body_in_receipt": False,
                "body_text_in_receipt": False,
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


def _empty_source_module_imports() -> dict[str, Any]:
    return {
        "status": PASS,
        "source_module_manifest_ref": "",
        "module_count": 0,
        "modules": [],
        "findings": [],
        "observed_negative_cases": {},
    }


def _source_open_body_import_summary(source_imports: dict[str, Any]) -> dict[str, Any]:
    modules = _rows(source_imports, "modules")
    module_ids = [str(row.get("module_id")) for row in modules if row.get("module_id")]
    return {
        "schema_version": "prediction_oracle_source_open_body_imports_v1",
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
        "reader_action": (
            "Open source_module_manifest.json and source_artifacts/ for copied "
            "prediction-oracle macro bodies; receipts carry digests and status only."
        )
        if modules
        else "",
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
    if case_id in EXPECTED_NEGATIVE_CASES:
        observed[case_id].add(code)


def _to_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _numeric_equal(left: float, right: float) -> bool:
    return abs(left - right) <= NUMERIC_RECOMPUTE_TOLERANCE


def _target_asset_classes(packet: dict[str, Any]) -> dict[str, str]:
    by_target: dict[str, str] = {}
    for row in _rows(packet, "target_universe"):
        target_id = str(row.get("target_id") or "").upper().strip()
        asset_class = str(
            row.get("asset_class")
            or row.get("target_asset_class")
            or row.get("market_asset_class")
            or ""
        ).upper()
        if target_id and asset_class in ALLOWED_ASSET_CLASSES:
            by_target[target_id] = asset_class
    return by_target


def _oracle_asset_class(
    row: dict[str, Any],
    *,
    target_id: str,
    target_asset_by_id: dict[str, str],
) -> str:
    asset_class = str(
        row.get("asset_class")
        or row.get("target_asset_class")
        or target_asset_by_id.get(target_id)
        or "STOCK"
    ).upper()
    return asset_class if asset_class in ALLOWED_ASSET_CLASSES else ""


def _truth_diff_import_stubs() -> dict[str, types.ModuleType]:
    system_module = types.ModuleType("system")
    system_module.__path__ = []  # type: ignore[attr-defined]
    lib_module = types.ModuleType("system.lib")
    lib_module.__path__ = []  # type: ignore[attr-defined]
    run_compare = types.ModuleType("system.lib.run_compare")

    def _empty_dict(*_args: object, **_kwargs: object) -> dict[str, Any]:
        return {}

    run_compare.compare_equity_runs = _empty_dict  # type: ignore[attr-defined]
    run_compare.equity_feed_health = _empty_dict  # type: ignore[attr-defined]
    run_compare.grade_predictions = _empty_dict  # type: ignore[attr-defined]
    run_compare.load_feed_prices = _empty_dict  # type: ignore[attr-defined]
    return {
        "system": system_module,
        "system.lib": lib_module,
        "system.lib.run_compare": run_compare,
    }


def _load_truth_diff_equity_module(source_path: Path) -> Any:
    module_name = (
        "_microcosm_prediction_oracle_truth_diff_equity_"
        + hashlib.sha256(str(source_path).encode("utf-8")).hexdigest()[:12]
    )
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise ImportError("truth_diff_equity_source_loader_unavailable")
    module = importlib.util.module_from_spec(spec)
    stubs = _truth_diff_import_stubs()
    previous = {name: sys.modules.get(name) for name in stubs}
    try:
        sys.modules.update(stubs)
        spec.loader.exec_module(module)
    finally:
        for name, previous_module in previous.items():
            if previous_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous_module
    return module


def _source_faithful_numeric_rows(
    grading: dict[str, Any],
    feed_price_maps: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stock_rows = feed_price_maps.get("global_stock_feed", {})
    etf_rows = feed_price_maps.get("global_etf_feed", {})
    for result in _rows(grading, "results"):
        if result.get("status") != "GRADED":
            continue
        target_id = str(result.get("target_id") or "").upper().strip()
        if not target_id:
            continue
        asset_class = "STOCK" if target_id in stock_rows else ""
        if not asset_class and target_id in etf_rows:
            asset_class = "ETF"
        if not asset_class:
            continue
        snapshot_price = _to_float(result.get("snapshot_price"))
        predicted_price = _to_float(result.get("predicted_price"))
        realized_price = _to_float(result.get("realized_price"))
        absolute_delta = _to_float(result.get("abs_error"))
        percent_delta = _to_float(result.get("pred_error_pct"))
        direction_hit = result.get("direction_hit")
        if (
            snapshot_price is None
            or predicted_price is None
            or realized_price is None
            or absolute_delta is None
            or percent_delta is None
            or not isinstance(direction_hit, bool)
        ):
            continue
        rows.append(
            {
                "target_id": target_id,
                "asset_class": asset_class,
                "prediction_direction": str(
                    result.get("predicted_direction") or ""
                ).upper().strip(),
                "subject_snapshot_price": snapshot_price,
                "predicted_target_price": predicted_price,
                "realized_truth_price": realized_price,
                "absolute_delta": absolute_delta,
                "percent_delta": percent_delta,
                "directional_correct": direction_hit,
            }
        )
    rows.sort(
        key=lambda item: (
            -abs(float(item.get("absolute_delta", 0.0))),
            -abs(float(item.get("percent_delta", 0.0))),
            str(item.get("target_id") or ""),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    summary: dict[str, Any] = {
        "row_count": len(rows),
        "directionally_correct_count": sum(
            1 for row in rows if row.get("directional_correct") is True
        ),
        "directionally_incorrect_count": sum(
            1 for row in rows if row.get("directional_correct") is False
        ),
    }
    if rows:
        summary["largest_absolute_miss_target"] = rows[0]["target_id"]
        largest_percent = max(
            rows,
            key=lambda item: abs(float(item.get("percent_delta", 0.0))),
        )
        summary["largest_percent_miss_target"] = largest_percent["target_id"]
    return rows, summary


def _source_numeric_rows(
    grading: dict[str, Any],
    feed_price_maps: dict[str, dict[str, Any]],
    *,
    input_dir: Path | None,
    public_root: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    source = _truth_diff_equity_source_path(input_dir, public_root=public_root)
    provenance: dict[str, Any] = {
        "schema_version": "prediction_oracle_numeric_source_provenance_v1",
        "source_body_invoked": False,
        "source_helper_names": [],
        "source_module_ref": "",
        "source_module_manifest_ref": "",
        "source_faithful_fallback_used": True,
        "body_in_receipt": False,
    }
    if source is not None:
        source_path, source_ref, manifest_ref = source
        try:
            module = _load_truth_diff_equity_module(source_path)
            module.load_feed_prices = (  # type: ignore[attr-defined]
                lambda _run_dir, feed_name: feed_price_maps.get(str(feed_name), {})
            )
            rows = module._build_prediction_reconciliation_rows(  # type: ignore[attr-defined]
                Path("."),
                grading,
            )
            summary = module._build_prediction_reconciliation_summary(rows)  # type: ignore[attr-defined]
            provenance.update(
                {
                    "source_body_invoked": True,
                    "source_helper_names": list(TRUTH_DIFF_HELPERS),
                    "source_module_ref": source_ref,
                    "source_module_manifest_ref": manifest_ref,
                    "source_faithful_fallback_used": False,
                }
            )
            return rows, summary, provenance
        except Exception as exc:
            provenance["source_helper_error_class"] = type(exc).__name__

    rows, summary = _source_faithful_numeric_rows(grading, feed_price_maps)
    return rows, summary, provenance


def _numeric_grading_inputs(
    packet: dict[str, Any],
    prediction_by_id: dict[str, dict[str, Any]],
    *,
    case_id: str,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> dict[str, Any]:
    target_asset_by_id = _target_asset_classes(packet)
    feed_price_maps: dict[str, dict[str, Any]] = {
        "global_stock_feed": {},
        "global_etf_feed": {},
    }
    grading_results: list[dict[str, Any]] = []
    large_miss_count = 0
    missing_realized_count = 0
    degraded_gate_count = 0
    rows = _rows(packet, "oracle_diff")
    has_numeric_surface = any(
        any(
            key in row
            for key in (
                "snapshot_price",
                "subject_snapshot_price",
                "predicted_price",
                "predicted_target_price",
                "realized_price",
                "realized_truth_price",
                "abs_error",
                "pred_error_pct",
            )
        )
        for row in rows
    )
    numeric_case_ids = {
        "numeric_large_miss_direction_hit",
        "missing_realized_numeric_truth",
        "degraded_feed_health_gates_numeric_truth",
        "asset_class_split_required",
    }
    if not has_numeric_surface and case_id not in {
        "reconciliation_packet_floor",
        *numeric_case_ids,
    }:
        return {
            "grading": {"results": []},
            "feed_price_maps": feed_price_maps,
            "large_miss_count": 0,
            "missing_realized_count": 0,
            "degraded_gate_count": 0,
            "active_numeric_surface": False,
        }

    for row in rows:
        prediction_id = str(row.get("prediction_id") or "")
        prediction = prediction_by_id.get(prediction_id, {})
        target_id = str(row.get("target_id") or prediction.get("target_id") or "")
        target_id = target_id.upper().strip()
        row_id = str(row.get("row_id") or prediction_id or "oracle_diff")
        asset_class = _oracle_asset_class(
            row,
            target_id=target_id,
            target_asset_by_id=target_asset_by_id,
        )
        if asset_class:
            feed_name = (
                "global_stock_feed" if asset_class == "STOCK" else "global_etf_feed"
            )
            feed_price_maps[feed_name][target_id] = {"fixture_only": True}
        predicted_direction = str(
            row.get("predicted_direction") or prediction.get("direction") or ""
        ).lower()
        realized_direction = str(row.get("realized_direction") or "").lower()
        degraded = (
            realized_direction == DEGRADED_DIRECTION
            or row.get("feed_health") == "degraded"
        )
        if degraded:
            degraded_gate_count += 1
            if case_id in EXPECTED_NEGATIVE_CASES:
                _record(
                    findings,
                    observed,
                    "PREDICTION_ORACLE_DEGRADED_FEED_HEALTH_GATED",
                    "Degraded feed-health rows must be gated out of numeric truth grading.",
                    case_id=case_id,
                    subject_id=row_id,
                    subject_kind="oracle_numeric_reconciliation",
                )
            continue

        snapshot_price = _to_float(row.get("snapshot_price"))
        if snapshot_price is None:
            snapshot_price = _to_float(row.get("subject_snapshot_price"))
        predicted_price = _to_float(row.get("predicted_price"))
        if predicted_price is None:
            predicted_price = _to_float(row.get("predicted_target_price"))
        realized_price = _to_float(row.get("realized_price"))
        if realized_price is None:
            realized_price = _to_float(row.get("realized_truth_price"))
        if realized_price is None:
            missing_realized_count += 1
            if case_id in EXPECTED_NEGATIVE_CASES:
                _record(
                    findings,
                    observed,
                    "PREDICTION_ORACLE_MISSING_REALIZED_TRUTH_NOT_GRADED",
                    "Rows missing realized numeric truth must not be fabricated into graded reconciliation rows.",
                    case_id=case_id,
                    subject_id=row_id,
                    subject_kind="oracle_numeric_reconciliation",
                )
            continue
        if snapshot_price is None or predicted_price is None:
            if case_id == "reconciliation_packet_floor":
                findings.append(
                    _finding(
                        "PREDICTION_ORACLE_NUMERIC_RECONCILIATION_INCOMPLETE",
                        "Numeric oracle rows need snapshot, predicted, and realized prices before ranking.",
                        case_id="numeric_reconciliation_floor",
                        subject_id=row_id,
                        subject_kind="oracle_numeric_reconciliation",
                    )
                )
            continue
        recomputed_absolute_delta = abs(predicted_price - realized_price)
        claimed_absolute_delta = _to_float(row.get("abs_error"))
        if claimed_absolute_delta is not None and not _numeric_equal(
            abs(claimed_absolute_delta),
            recomputed_absolute_delta,
        ):
            findings.append(
                _finding(
                    "PREDICTION_ORACLE_CLAIMED_ABS_ERROR_CONTRADICTS_RECOMPUTE",
                    "Claimed numeric error must match the recomputed subject-vs-truth delta.",
                    case_id="oracle_truth_recompute_floor",
                    subject_id=row_id,
                    subject_kind="oracle_numeric_reconciliation",
                )
            )
        absolute_delta = recomputed_absolute_delta
        recomputed_percent_delta = (
            (absolute_delta / snapshot_price) * 100.0
            if snapshot_price
            else 0.0
        )
        claimed_percent_delta = _to_float(row.get("pred_error_pct"))
        if claimed_percent_delta is not None and not _numeric_equal(
            abs(claimed_percent_delta),
            recomputed_percent_delta,
        ):
            findings.append(
                _finding(
                    "PREDICTION_ORACLE_CLAIMED_PERCENT_ERROR_CONTRADICTS_RECOMPUTE",
                    "Claimed percent error must match the recomputed subject-vs-truth delta.",
                    case_id="oracle_truth_recompute_floor",
                    subject_id=row_id,
                    subject_kind="oracle_numeric_reconciliation",
                )
            )
        percent_delta = recomputed_percent_delta
        recomputed_direction_hit = (
            predicted_direction == realized_direction
            if realized_direction in ALLOWED_DIRECTIONS
            else None
        )
        claimed_direction_hit = row.get("direction_hit")
        if (
            isinstance(claimed_direction_hit, bool)
            and isinstance(recomputed_direction_hit, bool)
            and claimed_direction_hit != recomputed_direction_hit
        ):
            findings.append(
                _finding(
                    "PREDICTION_ORACLE_CLAIMED_DIRECTION_HIT_CONTRADICTS_RECOMPUTE",
                    "Claimed direction_hit must match the recomputed predicted-vs-realized direction.",
                    case_id="oracle_truth_recompute_floor",
                    subject_id=row_id,
                    subject_kind="oracle_numeric_reconciliation",
                )
            )
        direction_hit = (
            recomputed_direction_hit
            if isinstance(recomputed_direction_hit, bool)
            else claimed_direction_hit
        )
        if not isinstance(direction_hit, bool):
            continue
        large_miss = (
            direction_hit is True
            and (
                abs(absolute_delta) >= NUMERIC_LARGE_MISS_ABSOLUTE_FLOOR
                or abs(percent_delta) >= NUMERIC_LARGE_MISS_PERCENT_FLOOR
            )
        )
        if large_miss:
            large_miss_count += 1
            if case_id in EXPECTED_NEGATIVE_CASES:
                _record(
                    findings,
                    observed,
                    "PREDICTION_ORACLE_NUMERIC_LARGE_MISS_SURFACED",
                    "Direction-only hits must still surface large numeric misses.",
                    case_id=case_id,
                    subject_id=row_id,
                    subject_kind="oracle_numeric_reconciliation",
                )
        grading_results.append(
            {
                "status": "GRADED",
                "target_id": target_id,
                "predicted_direction": predicted_direction,
                "snapshot_price": snapshot_price,
                "predicted_price": predicted_price,
                "realized_price": realized_price,
                "abs_error": absolute_delta,
                "pred_error_pct": percent_delta,
                "direction_hit": direction_hit,
            }
        )

    return {
        "grading": {"results": grading_results},
        "feed_price_maps": feed_price_maps,
        "large_miss_count": large_miss_count,
        "missing_realized_count": missing_realized_count,
        "degraded_gate_count": degraded_gate_count,
        "active_numeric_surface": has_numeric_surface,
    }


def _numeric_reconciliation_rows(
    packet: dict[str, Any],
    prediction_by_id: dict[str, dict[str, Any]],
    *,
    case_id: str,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    input_dir: Path | None,
    public_root: Path | None,
) -> dict[str, Any]:
    numeric_inputs = _numeric_grading_inputs(
        packet,
        prediction_by_id,
        case_id=case_id,
        findings=findings,
        observed=observed,
    )
    source_rows, source_summary, source_provenance = _source_numeric_rows(
        numeric_inputs["grading"],
        numeric_inputs["feed_price_maps"],
        input_dir=input_dir,
        public_root=public_root,
    )
    prediction_by_target = {
        str(prediction.get("target_id") or "").upper().strip(): prediction_id
        for prediction_id, prediction in prediction_by_id.items()
    }
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        target_id = str(row.get("target_id") or "").upper().strip()
        absolute_delta = _to_float(row.get("absolute_delta")) or 0.0
        percent_delta = _to_float(row.get("percent_delta")) or 0.0
        rows.append(
            {
                "rank": row.get("rank"),
                "prediction_id": prediction_by_target.get(target_id, ""),
                "target_id": target_id,
                "asset_class": row.get("asset_class"),
                "prediction_direction": row.get("prediction_direction"),
                "subject_snapshot_price": row.get("subject_snapshot_price"),
                "predicted_target_price": row.get("predicted_target_price"),
                "realized_truth_price": row.get("realized_truth_price"),
                "absolute_delta": absolute_delta,
                "percent_delta": percent_delta,
                "directional_correct": row.get("directional_correct"),
                "large_numeric_miss": (
                    abs(absolute_delta) >= NUMERIC_LARGE_MISS_ABSOLUTE_FLOOR
                    or abs(percent_delta) >= NUMERIC_LARGE_MISS_PERCENT_FLOOR
                ),
                "body_in_receipt": False,
            }
        )
    asset_class_counts = {
        asset_class: len([row for row in rows if row.get("asset_class") == asset_class])
        for asset_class in sorted(ALLOWED_ASSET_CLASSES)
    }
    if (
        case_id in EXPECTED_NEGATIVE_CASES
        and numeric_inputs["active_numeric_surface"]
        and (asset_class_counts.get("STOCK", 0) == 0 or asset_class_counts.get("ETF", 0) == 0)
    ):
        _record(
            findings,
            observed,
            "PREDICTION_ORACLE_ASSET_CLASS_SPLIT_PRESERVED",
            "Numeric reconciliation must preserve STOCK and ETF asset-class splits.",
            case_id=case_id,
            subject_id=str(packet.get("packet_id") or "reconciliation_packet"),
            subject_kind="oracle_numeric_reconciliation",
        )
    summary = dict(source_summary)
    summary.update(
        {
            "row_count": len(rows),
            "asset_class_counts": asset_class_counts,
            "large_numeric_miss_count": len(
                [row for row in rows if row.get("large_numeric_miss") is True]
            ),
            "direction_hit_numeric_miss_count": numeric_inputs["large_miss_count"],
            "missing_realized_truth_count": numeric_inputs["missing_realized_count"],
            "degraded_feed_gate_count": numeric_inputs["degraded_gate_count"],
            "source_body_invoked": source_provenance["source_body_invoked"],
            "source_faithful_fallback_used": source_provenance[
                "source_faithful_fallback_used"
            ],
            "body_in_receipt": False,
        }
    )
    return {
        "rows": rows,
        "summary": summary,
        "source": source_provenance,
        "findings": findings,
        "observed_negative_cases": observed,
    }


def _authority_overclaim(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    ceiling = payload.get("authority_ceiling", payload)
    if not isinstance(ceiling, dict):
        return False
    return any(ceiling.get(flag) is True for flag in FORBIDDEN_AUTHORITY_FLAGS)


def _target_universe(packet: dict[str, Any]) -> set[str]:
    direct = set(_strings(packet.get("valid_prediction_targets")))
    rows = _rows(packet, "target_universe")
    from_rows = {str(row.get("target_id")) for row in rows if row.get("target_id")}
    return direct | from_rows


def _evidence_is_pre_t(ref: str) -> bool:
    return ref.startswith("T-") or ref.startswith("t-")


def _validate_cp1(
    packet: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    branches = _rows(packet, "cp1_branches")
    branch_by_target: dict[str, dict[str, Any]] = {}
    selected_branch_ids: list[str] = []
    for branch in branches:
        branch_id = str(branch.get("branch_id") or "cp1_branch")
        target_id = str(branch.get("target_id") or "")
        lane = str(branch.get("lane") or "")
        if branch.get("selected_side"):
            selected_branch_ids.append(branch_id)
            if target_id:
                branch_by_target[target_id] = branch
        if not branch.get("selected_side") or not branch.get("rationale_refs") or not branch.get(
            "opposite_side_invalidation_ref"
        ):
            _record(
                findings,
                observed,
                "PREDICTION_CP1_BIFURCATION_UNRESOLVED",
                "CP1 branches must resolve the chosen side and retain why the opposite side lost.",
                case_id=case_id,
                subject_id=branch_id,
                subject_kind="cp1_branch",
            )
        if lane in {"equity", "market", "finance"} and branch.get(
            "equity_lane_confirmation"
        ) is not True:
            _record(
                findings,
                observed,
                "PREDICTION_EQUITY_CONFIRMATION_REQUIRED",
                "Equity or market-lane claims require an explicit confirmation bit before use.",
                case_id=case_id,
                subject_id=branch_id,
                subject_kind="cp1_branch",
            )
    return {
        "status": PASS if branches and not findings else "blocked",
        "findings": findings,
        "observed_negative_cases": observed,
        "branch_count": len(branches),
        "selected_branch_ids": selected_branch_ids,
        "selected_branch_by_target": branch_by_target,
    }


def _validate_cp2(
    packet: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    universe = _target_universe(packet)
    predictions = _rows(packet, "cp2_predictions")
    prediction_by_id: dict[str, dict[str, Any]] = {}
    for prediction in predictions:
        prediction_id = str(prediction.get("prediction_id") or "cp2_prediction")
        prediction_by_id[prediction_id] = prediction
        target_id = str(prediction.get("target_id") or "")
        if target_id not in universe:
            _record(
                findings,
                observed,
                "PREDICTION_CP2_TARGET_OUT_OF_UNIVERSE",
                "CP2 predictions must stay inside the declared valid target universe.",
                case_id=case_id,
                subject_id=prediction_id,
                subject_kind="cp2_prediction",
            )
        evidence_refs = _strings(prediction.get("evidence_refs"))
        for ref in evidence_refs:
            if not _evidence_is_pre_t(ref):
                _record(
                    findings,
                    observed,
                    "PREDICTION_ORACLE_POST_T_EVIDENCE_FORBIDDEN",
                    "Oracle predictions may not use post-target evidence refs.",
                    case_id=case_id,
                    subject_id=prediction_id,
                    subject_kind="cp2_prediction",
                )
        if prediction.get("direction") not in ALLOWED_DIRECTIONS or not evidence_refs:
            findings.append(
                _finding(
                    "PREDICTION_CP2_PREDICTION_INCOMPLETE",
                    "CP2 rows must name direction and pre-target evidence.",
                    case_id="prediction_floor",
                    subject_id=prediction_id,
                    subject_kind="cp2_prediction",
                )
            )
        if not _strings(prediction.get("grounding_ids")):
            findings.append(
                _finding(
                    "PREDICTION_ORACLE_GROUNDING_MISSING",
                    "Prediction rows must name synthetic grounding ids.",
                    case_id="prediction_floor",
                    subject_id=prediction_id,
                    subject_kind="cp2_prediction",
                )
            )
    return {
        "status": PASS if predictions and universe and not findings else "blocked",
        "findings": findings,
        "observed_negative_cases": observed,
        "prediction_count": len(predictions),
        "prediction_by_id": prediction_by_id,
        "valid_prediction_targets": sorted(universe),
    }


def _validate_oracle_diff(
    packet: dict[str, Any],
    prediction_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(packet, "oracle_diff")
    graded_rows: list[dict[str, Any]] = []
    for row in rows:
        row_id = str(row.get("row_id") or row.get("prediction_id") or "oracle_diff")
        prediction_id = str(row.get("prediction_id") or "")
        prediction = prediction_by_id.get(prediction_id)
        target_id = str(row.get("target_id") or "")
        predicted = str(row.get("predicted_direction") or "")
        realized = str(row.get("realized_direction") or "")
        degraded = realized == DEGRADED_DIRECTION or row.get("feed_health") == "degraded"
        if prediction is None:
            findings.append(
                _finding(
                    "PREDICTION_ORACLE_UNKNOWN_PREDICTION",
                    "Oracle diff rows must grade an existing CP2 prediction row.",
                    case_id="oracle_diff_floor",
                    subject_id=row_id,
                    subject_kind="oracle_diff",
                )
            )
        else:
            expected_target = str(prediction.get("target_id") or "")
            expected_direction = str(prediction.get("direction") or "")
            if target_id and target_id != expected_target:
                findings.append(
                    _finding(
                        "PREDICTION_ORACLE_TARGET_MISMATCH",
                        "Oracle diff rows must keep the target id from the CP2 prediction they grade.",
                        case_id="oracle_diff_floor",
                        subject_id=row_id,
                        subject_kind="oracle_diff",
                    )
                )
            if predicted and predicted != expected_direction:
                findings.append(
                    _finding(
                        "PREDICTION_ORACLE_PREDICTED_DIRECTION_MISMATCH",
                        "Oracle diff rows must keep the predicted direction from the CP2 prediction they grade.",
                        case_id="oracle_diff_floor",
                        subject_id=row_id,
                        subject_kind="oracle_diff",
                    )
                )
        if predicted not in ALLOWED_DIRECTIONS or realized not in {*ALLOWED_DIRECTIONS, DEGRADED_DIRECTION}:
            findings.append(
                _finding(
                    "PREDICTION_ORACLE_DIFF_INCOMPLETE",
                    "Oracle diff rows must carry predicted and realized directions or a degraded-feed marker.",
                    case_id="oracle_diff_floor",
                    subject_id=row_id,
                    subject_kind="oracle_diff",
                )
            )
        graded_rows.append(
            {
                "row_id": row_id,
                "prediction_id": prediction_id,
                "predicted_direction": predicted,
                "realized_direction": realized,
                "feed_health": row.get("feed_health", "ok"),
                "graded": not degraded,
                "direction_hit": (predicted == realized) if not degraded else None,
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "findings": findings,
        "oracle_diff_rows": graded_rows,
        "oracle_diff_row_count": len(rows),
        "oracle_diff_graded_count": len([row for row in graded_rows if row["graded"]]),
        "oracle_diff_hit_count": len(
            [row for row in graded_rows if row["graded"] and row["direction_hit"] is True]
        ),
    }


def _validate_mutations(
    packet: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    mutations = _rows(packet, "dossier_mutations")
    prediction_ids = {
        str(row.get("prediction_id"))
        for row in _rows(packet, "cp2_predictions")
        if row.get("prediction_id")
    }
    for mutation in mutations:
        mutation_id = str(mutation.get("mutation_id") or "dossier_mutation")
        operation = str(mutation.get("operation") or "")
        evidence_refs = _strings(mutation.get("evidence_run_refs"))
        if operation not in ALLOWED_MUTATIONS or mutation.get("target_claim_id") not in prediction_ids:
            findings.append(
                _finding(
                    "PREDICTION_DOSSIER_MUTATION_INCOMPLETE",
                    "Dossier mutations must target a known synthetic claim and use an allowed operation.",
                    case_id="dossier_mutation_floor",
                    subject_id=mutation_id,
                    subject_kind="dossier_mutation",
                )
            )
        if (
            str(mutation.get("severity") or "").lower() == "high"
            and (len(evidence_refs) < 2 or mutation.get("allowed_public_delta") is not True)
        ):
            _record(
                findings,
                observed,
                "PREDICTION_DOSSIER_MUTATION_UNSAFE",
                "High-severity dossier mutation needs two evidence refs and a public-delta allowlist.",
                case_id=case_id,
                subject_id=mutation_id,
                subject_kind="dossier_mutation",
            )
    return {
        "status": PASS if mutations and not findings else "blocked",
        "findings": findings,
        "observed_negative_cases": observed,
        "dossier_mutation_count": len(mutations),
        "dossier_mutation_ids": sorted(
            str(row.get("mutation_id")) for row in mutations if row.get("mutation_id")
        ),
    }


def validate_reconciliation_packet(
    payload: object,
    *,
    case_id: str = "reconciliation_packet_floor",
    input_dir: Path | None = None,
    public_root: Path | None = None,
) -> dict[str, Any]:
    packet = payload if isinstance(payload, dict) else {}
    observed: dict[str, set[str]] = defaultdict(set)
    findings: list[dict[str, Any]] = []
    source_pattern_ids = _strings(packet.get("source_pattern_ids"))
    source_refs = _strings(packet.get("source_refs"))
    projection_receipts = _strings(packet.get("projection_receipt_refs"))
    public_runtime_refs = _strings(packet.get("public_runtime_refs"))

    if len(source_pattern_ids) < 5 or len(source_refs) < 4 or not projection_receipts:
        findings.append(
            _finding(
                "PREDICTION_RECONCILIATION_SOURCE_DENSITY_MISSING",
                "Prediction reconciliation packets need pattern ids, source refs, and projection receipts.",
                case_id="reconciliation_packet_floor",
                subject_id=str(packet.get("packet_id") or "reconciliation_packet"),
                subject_kind="reconciliation_packet",
            )
        )
    if len(public_runtime_refs) < 3:
        findings.append(
            _finding(
                "PREDICTION_RECONCILIATION_RUNTIME_REFS_MISSING",
                "Prediction reconciliation must cite public runtime refs for the real fixture and bundle substrate.",
                case_id="reconciliation_packet_floor",
                subject_id=str(packet.get("packet_id") or "reconciliation_packet"),
                subject_kind="reconciliation_packet",
            )
        )
    if _authority_overclaim(packet):
        _record(
            findings,
            observed,
            "PREDICTION_TRADING_OR_ADVICE_OVERCLAIM",
            "Prediction reconciliation rejects trading, advice, live provider, release, publication, and private-equivalence authority.",
            case_id=case_id,
            subject_id=str(packet.get("packet_id") or "reconciliation_packet"),
            subject_kind="authority_ceiling",
        )

    cp1 = _validate_cp1(packet, case_id=case_id, observed=observed)
    cp2 = _validate_cp2(packet, case_id=case_id, observed=observed)
    oracle = _validate_oracle_diff(packet, cp2["prediction_by_id"])
    numeric_findings: list[dict[str, Any]] = []
    numeric = _numeric_reconciliation_rows(
        packet,
        cp2["prediction_by_id"],
        case_id=case_id,
        findings=numeric_findings,
        observed=observed,
        input_dir=input_dir,
        public_root=public_root,
    )
    mutations = _validate_mutations(packet, case_id=case_id, observed=observed)
    findings.extend(cp1["findings"])
    findings.extend(cp2["findings"])
    findings.extend(oracle["findings"])
    findings.extend(numeric_findings)
    findings.extend(mutations["findings"])

    positive_findings = [
        row for row in findings if row.get("negative_case_id") not in EXPECTED_NEGATIVE_CASES
    ]
    status = (
        PASS
        if not positive_findings
        and cp1["branch_count"] >= 2
        and cp2["prediction_count"] >= 2
        and oracle["oracle_diff_row_count"] >= 2
        and numeric["summary"]["row_count"] >= 2
        and numeric["summary"]["asset_class_counts"].get("STOCK", 0) >= 1
        and numeric["summary"]["asset_class_counts"].get("ETF", 0) >= 1
        and mutations["dossier_mutation_count"] >= 1
        else "blocked"
    )
    return {
        "status": status,
        "packet_id": packet.get("packet_id"),
        "source_pattern_ids": source_pattern_ids,
        "source_refs": source_refs,
        "projection_receipt_refs": projection_receipts,
        "public_runtime_refs": public_runtime_refs,
        "valid_prediction_targets": cp2["valid_prediction_targets"],
        "cp1_branch_count": cp1["branch_count"],
        "cp1_selected_branch_ids": cp1["selected_branch_ids"],
        "cp2_prediction_count": cp2["prediction_count"],
        "oracle_diff_rows": oracle["oracle_diff_rows"],
        "oracle_diff_graded_count": oracle["oracle_diff_graded_count"],
        "oracle_diff_hit_count": oracle["oracle_diff_hit_count"],
        "numeric_reconciliation_rows": numeric["rows"],
        "numeric_reconciliation_summary": numeric["summary"],
        "numeric_reconciliation_source": numeric["source"],
        "dossier_mutation_count": mutations["dossier_mutation_count"],
        "dossier_mutation_ids": mutations["dossier_mutation_ids"],
        "reconciliation_rows": _reconciliation_rows(
            cp1["selected_branch_by_target"],
            cp2["prediction_by_id"],
            oracle["oracle_diff_rows"],
            numeric["rows"],
            mutations["dossier_mutation_ids"],
        ),
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in sorted(observed.items())
        },
    }


def _reconciliation_rows(
    selected_branch_by_target: dict[str, dict[str, Any]],
    prediction_by_id: dict[str, dict[str, Any]],
    oracle_rows: list[dict[str, Any]],
    numeric_rows: list[dict[str, Any]],
    mutation_ids: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    oracle_by_prediction = {
        str(row.get("prediction_id")): row for row in oracle_rows if row.get("prediction_id")
    }
    numeric_by_prediction = {
        str(row.get("prediction_id")): row
        for row in numeric_rows
        if row.get("prediction_id")
    }
    for prediction_id, prediction in sorted(prediction_by_id.items()):
        target_id = str(prediction.get("target_id") or "")
        branch = selected_branch_by_target.get(target_id, {})
        oracle = oracle_by_prediction.get(prediction_id, {})
        numeric = numeric_by_prediction.get(prediction_id, {})
        rows.append(
            {
                "prediction_id": prediction_id,
                "target_id": target_id,
                "cp1_branch_id": branch.get("branch_id"),
                "direction": prediction.get("direction"),
                "confidence_band": prediction.get("confidence_band"),
                "oracle_feed_health": oracle.get("feed_health"),
                "direction_hit": oracle.get("direction_hit"),
                "numeric_graded": bool(numeric),
                "numeric_rank": numeric.get("rank"),
                "asset_class": numeric.get("asset_class"),
                "subject_snapshot_price": numeric.get("subject_snapshot_price"),
                "predicted_target_price": numeric.get("predicted_target_price"),
                "realized_truth_price": numeric.get("realized_truth_price"),
                "absolute_delta": numeric.get("absolute_delta"),
                "percent_delta": numeric.get("percent_delta"),
                "large_numeric_miss": numeric.get("large_numeric_miss"),
                "mutation_ids": mutation_ids,
                "body_in_receipt": False,
            }
        )
    return rows


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
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


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


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
    source_artifact_paths = (
        _source_artifact_paths(input_dir, public_root=public_root)
        if input_mode == "exported_prediction_oracle_bundle"
        else []
    )
    secret_scan = _receipt_safe_scan(
        scan_paths(
            [
                *_input_paths(input_dir, include_negative=include_negative),
                *source_artifact_paths,
            ],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    packet = validate_reconciliation_packet(
        payloads["reconciliation_packet"],
        input_dir=input_dir,
        public_root=public_root,
    )
    negative_results = [
        validate_reconciliation_packet(
            payloads[name],
            case_id=name,
            input_dir=input_dir,
            public_root=public_root,
        )
        for name in (path.removesuffix(".json") for path in NEGATIVE_INPUT_NAMES)
        if include_negative
    ]
    observed = _merge_observed(packet, *negative_results)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    source_imports = (
        validate_source_module_imports(input_dir, public_root=public_root)
        if input_mode == "exported_prediction_oracle_bundle"
        else _empty_source_module_imports()
    )
    source_open_body_imports = _source_open_body_import_summary(source_imports)
    findings = _merge_findings(packet, *negative_results, source_imports)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    status = (
        PASS
        if packet["status"] == PASS
        and not missing
        and secret_scan["blocking_hit_count"] == 0
        and source_imports["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "prediction_oracle_reconciliation_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "packet_id": packet["packet_id"],
        "source_pattern_ids": packet["source_pattern_ids"],
        "source_refs": packet["source_refs"],
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "projection_receipt_refs": packet["projection_receipt_refs"],
        "public_runtime_refs": packet["public_runtime_refs"],
        "valid_prediction_targets": packet["valid_prediction_targets"],
        "cp1_branch_count": packet["cp1_branch_count"],
        "cp1_selected_branch_ids": packet["cp1_selected_branch_ids"],
        "cp2_prediction_count": packet["cp2_prediction_count"],
        "oracle_diff_graded_count": packet["oracle_diff_graded_count"],
        "oracle_diff_hit_count": packet["oracle_diff_hit_count"],
        "numeric_reconciliation_row_count": packet["numeric_reconciliation_summary"][
            "row_count"
        ],
        "numeric_reconciliation_summary": packet["numeric_reconciliation_summary"],
        "numeric_reconciliation_source": packet["numeric_reconciliation_source"],
        "numeric_reconciliation_rows": packet["numeric_reconciliation_rows"],
        "dossier_mutation_count": packet["dossier_mutation_count"],
        "dossier_mutation_ids": packet["dossier_mutation_ids"],
        "reconciliation_rows": packet["reconciliation_rows"],
        "prediction_reconciliation_board": {
            "headline": "Synthetic prediction reasoning is reconciled through CP1, CP2, oracle diff, ranked numeric truth rows, and dossier mutation receipts.",
            "source_pattern_count": len(packet["source_pattern_ids"]),
            "valid_prediction_target_count": len(packet["valid_prediction_targets"]),
            "cp2_prediction_count": packet["cp2_prediction_count"],
            "oracle_diff_graded_count": packet["oracle_diff_graded_count"],
            "numeric_reconciliation_row_count": packet[
                "numeric_reconciliation_summary"
            ]["row_count"],
            "numeric_asset_class_counts": packet["numeric_reconciliation_summary"][
                "asset_class_counts"
            ],
            "largest_absolute_miss_target": packet[
                "numeric_reconciliation_summary"
            ].get("largest_absolute_miss_target"),
            "largest_percent_miss_target": packet[
                "numeric_reconciliation_summary"
            ].get("largest_percent_miss_target"),
            "source_body_invoked": packet["numeric_reconciliation_summary"][
                "source_body_invoked"
            ],
            "dossier_mutation_count": packet["dossier_mutation_count"],
            "trading_authorized": False,
            "financial_advice_authorized": False,
            "live_market_data_authorized": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "body_in_receipt": False,
        },
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
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
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "packet_id",
        "source_pattern_ids",
        "source_refs",
        "source_open_body_imports",
        "body_material_status",
        "body_copied_material_count",
        "projection_receipt_refs",
        "public_runtime_refs",
        "valid_prediction_targets",
        "cp1_branch_count",
        "cp1_selected_branch_ids",
        "cp2_prediction_count",
        "oracle_diff_graded_count",
        "oracle_diff_hit_count",
        "numeric_reconciliation_row_count",
        "numeric_reconciliation_summary",
        "numeric_reconciliation_source",
        "numeric_reconciliation_rows",
        "dossier_mutation_count",
        "dossier_mutation_ids",
        "reconciliation_rows",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
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
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "prediction_oracle_reconciliation_result": target / RESULT_NAME,
        "prediction_reconciliation_board": target / BOARD_NAME,
        "prediction_oracle_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = [_display(path, public_root=public_root_path) for path in paths.values()]

    result_receipt = _common_receipt(
        result,
        schema_version="prediction_oracle_reconciliation_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _common_receipt(
        result,
        schema_version="prediction_oracle_reconciliation_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["prediction_reconciliation_board"])
    validation = _common_receipt(
        result,
        schema_version="prediction_oracle_reconciliation_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "cp2_target_universe_gate_rejected": "invalid_cp2_target"
            in result["observed_negative_cases"],
            "cp1_unresolved_bifurcation_rejected": "missing_bifurcation_resolution"
            in result["observed_negative_cases"],
            "post_t_evidence_rejected": "post_t_evidence_ref"
            in result["observed_negative_cases"],
            "equity_confirmation_required": "unconfirmed_equity_lane_claim"
            in result["observed_negative_cases"],
            "unsafe_dossier_mutation_rejected": "unsafe_dossier_mutation"
            in result["observed_negative_cases"],
            "trading_or_advice_overclaim_rejected": "trading_advice_overclaim"
            in result["observed_negative_cases"],
            "numeric_large_miss_direction_hit_surfaced": (
                "numeric_large_miss_direction_hit"
                in result["observed_negative_cases"]
            ),
            "missing_realized_numeric_truth_not_graded": (
                "missing_realized_numeric_truth"
                in result["observed_negative_cases"]
            ),
            "degraded_feed_health_gated": (
                "degraded_feed_health_gates_numeric_truth"
                in result["observed_negative_cases"]
            ),
            "asset_class_split_preserved": (
                "asset_class_split_required" in result["observed_negative_cases"]
            ),
            "trading_authorized": False,
            "financial_advice_authorized": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="prediction_oracle_reconciliation_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "accepted_scope": "synthetic_prediction_reconciliation_fixture_only",
            "trading_or_advice_authorized": False,
        }
    )

    write_json_atomic(paths["prediction_oracle_reconciliation_result"], result_receipt)
    write_json_atomic(paths["prediction_reconciliation_board"], board)
    write_json_atomic(paths["prediction_oracle_validation_receipt"], validation)
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.prediction_oracle_reconciliation run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_prediction_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.prediction_oracle_reconciliation "
        f"run-prediction-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_prediction_oracle_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    receipt_path = target / BUNDLE_RESULT_NAME
    receipt = _common_receipt(
        result,
        schema_version="exported_prediction_oracle_bundle_validation_result_v1",
        receipt_paths=[_display(receipt_path, public_root=public_root)],
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [_display(receipt_path, public_root=public_root)]
    return result


def _scan_card(scan: object) -> dict[str, Any]:
    scan_row = scan if isinstance(scan, dict) else {}
    return {
        "status": scan_row.get("status"),
        "blocking_hit_count": scan_row.get("blocking_hit_count"),
        "hit_count": scan_row.get("hit_count"),
        "scanned_path_count": scan_row.get("scanned_path_count"),
        "body_in_receipt": scan_row.get("body_in_receipt") is True,
        "hits_exported": False,
        "scan_scope_exported": False,
        "source_excerpt_exported": False,
    }


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    ceiling = result.get("authority_ceiling", {})
    if not isinstance(ceiling, dict):
        ceiling = {}
    return {
        "status": ceiling.get("status"),
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "trading_authorized": ceiling.get("trading_authorized") is True,
        "financial_advice_authorized": (
            ceiling.get("financial_advice_authorized") is True
        ),
        "investment_advice_authorized": (
            ceiling.get("investment_advice_authorized") is True
        ),
        "live_market_data_authorized": (
            ceiling.get("live_market_data_authorized") is True
        ),
        "live_provider_calls_authorized": (
            ceiling.get("live_provider_calls_authorized") is True
        ),
        "provider_calls_authorized": ceiling.get("provider_calls_authorized") is True,
        "publication_authorized": ceiling.get("publication_authorized") is True,
        "release_authorized": ceiling.get("release_authorized") is True,
        "private_data_equivalence_claim": (
            ceiling.get("private_data_equivalence_claim") is True
        ),
        "dossier_mutation_authority": ceiling.get("dossier_mutation_authority"),
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    input_mode = result.get("input_mode")
    action = (
        "run-prediction-bundle"
        if input_mode == "exported_prediction_oracle_bundle"
        else "run"
    )
    expected_cases = result.get("expected_negative_cases", [])
    observed_cases = result.get("observed_negative_cases", {})
    receipt_name = BUNDLE_RESULT_NAME if action == "run-prediction-bundle" else RESULT_NAME
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "input_mode": input_mode,
        "bundle_id": result.get("bundle_id"),
        "card_id": (
            "prediction_oracle_exported_bundle_card"
            if action == "run-prediction-bundle"
            else "prediction_oracle_fixture_card"
        ),
        "output_profile": "compact_card_no_findings_tables_source_refs_or_scan_scope",
        "full_output_available": True,
        "full_output_drilldown": f"rerun {action} without --card",
        "receipt_summary": {
            "receipt_count": len(result.get("receipt_paths", [])),
            "receipt_paths_exported": False,
            "result_receipt_name": receipt_name,
            "board_receipt_name": None
            if action == "run-prediction-bundle"
            else BOARD_NAME,
            "validation_receipt_name": None
            if action == "run-prediction-bundle"
            else VALIDATION_RECEIPT_NAME,
        },
        "prediction_reconciliation_summary": {
            "packet_id": result.get("packet_id"),
            "source_pattern_count": len(result.get("source_pattern_ids", [])),
            "source_ref_count": len(result.get("source_refs", [])),
            "projection_receipt_ref_count": len(
                result.get("projection_receipt_refs", [])
            ),
            "public_runtime_ref_count": len(result.get("public_runtime_refs", [])),
            "valid_prediction_target_count": len(
                result.get("valid_prediction_targets", [])
            ),
            "cp1_branch_count": result.get("cp1_branch_count"),
            "cp1_selected_branch_count": len(
                result.get("cp1_selected_branch_ids", [])
            ),
            "cp2_prediction_count": result.get("cp2_prediction_count"),
            "oracle_diff_graded_count": result.get("oracle_diff_graded_count"),
            "oracle_diff_hit_count": result.get("oracle_diff_hit_count"),
            "numeric_reconciliation_row_count": result.get(
                "numeric_reconciliation_row_count"
            ),
            "numeric_large_miss_count": (
                result.get("numeric_reconciliation_summary", {})
                if isinstance(result.get("numeric_reconciliation_summary"), dict)
                else {}
            ).get("large_numeric_miss_count"),
            "numeric_asset_class_counts": (
                result.get("numeric_reconciliation_summary", {})
                if isinstance(result.get("numeric_reconciliation_summary"), dict)
                else {}
            ).get("asset_class_counts"),
            "largest_absolute_miss_target": (
                result.get("numeric_reconciliation_summary", {})
                if isinstance(result.get("numeric_reconciliation_summary"), dict)
                else {}
            ).get("largest_absolute_miss_target"),
            "source_body_invoked": (
                result.get("numeric_reconciliation_source", {})
                if isinstance(result.get("numeric_reconciliation_source"), dict)
                else {}
            ).get("source_body_invoked")
            is True,
            "dossier_mutation_count": result.get("dossier_mutation_count"),
            "reconciliation_row_count": len(result.get("reconciliation_rows", [])),
        },
        "source_open_body_imports_summary": {
            "status": (
                result.get("source_open_body_imports", {})
                if isinstance(result.get("source_open_body_imports"), dict)
                else {}
            ).get("status"),
            "body_material_status": result.get("body_material_status"),
            "body_material_count": result.get("body_copied_material_count"),
            "source_manifest_count": len(
                (
                    result.get("source_open_body_imports", {})
                    if isinstance(result.get("source_open_body_imports"), dict)
                    else {}
                ).get("source_manifest_refs", [])
            ),
            "body_in_receipt": (
                result.get("source_open_body_imports", {})
                if isinstance(result.get("source_open_body_imports"), dict)
                else {}
            ).get("body_in_receipt")
            is True,
        },
        "negative_case_coverage": {
            "expected_case_count": len(expected_cases)
            if isinstance(expected_cases, list)
            else 0,
            "observed_case_count": len(observed_cases)
            if isinstance(observed_cases, dict)
            else 0,
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_code_count": len(result.get("error_codes", [])),
        },
        "secret_exclusion_scan_summary": _scan_card(
            result.get("secret_exclusion_scan")
        ),
        "authority_ceiling": _authority_ceiling_card(result),
        "runtime_authority": {
            "body_in_receipt": result.get("body_in_receipt") is True,
            "real_runtime_receipt": result.get("real_runtime_receipt") is True,
            "synthetic_receipt_standin_allowed": (
                result.get("synthetic_receipt_standin_allowed") is True
            ),
        },
        "no_export_guards": {
            "findings_exported": False,
            "error_codes_exported": False,
            "source_refs_exported": False,
            "receipt_paths_exported": False,
            "observed_negative_cases_exported": False,
            "prediction_targets_exported": False,
            "reconciliation_rows_exported": False,
            "numeric_reconciliation_rows_exported": False,
            "numeric_source_refs_exported": False,
            "dossier_mutation_ids_exported": False,
            "secret_scan_hits_exported": False,
            "secret_scan_scope_exported": False,
            "anti_claim_exported": False,
            "private_bodies_exported": False,
            "provider_payloads_exported": False,
        },
        "output_economy": {
            "stdout_mode": "card",
            "full_payload_drilldown": "rerun without --card",
            "omitted_full_payload_keys": [
                "findings",
                "error_codes",
                "expected_negative_cases",
                "observed_negative_cases",
                "source_pattern_ids",
                "source_refs",
                "source_open_body_imports.body_material_ids",
                "projection_receipt_refs",
                "public_runtime_refs",
                "valid_prediction_targets",
                "dossier_mutation_ids",
                "reconciliation_rows",
                "numeric_reconciliation_rows",
                "prediction_reconciliation_board",
                "receipt_paths",
                "secret_exclusion_scan.hits",
                "secret_exclusion_scan.scan_scope",
                "anti_claim",
            ],
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate prediction oracle reconciliation")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-prediction-bundle"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument(
            "--card",
            action="store_true",
            help="Print a compact command card; write the full receipt to --out.",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        result = run(
            args.input,
            args.out,
            command=(
                f"python -m {MODULE_PATH} run --input {args.input} "
                f"--out {args.out}{card_suffix}"
            ),
        )
    else:
        result = run_prediction_bundle(
            args.input,
            args.out,
            command=(
                f"python -m {MODULE_PATH} run-prediction-bundle "
                f"--input {args.input} --out {args.out}{card_suffix}"
            ),
        )
    output = result_card(result) if args.card else result
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
