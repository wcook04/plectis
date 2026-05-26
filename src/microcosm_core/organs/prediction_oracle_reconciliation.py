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

PACKET_NAME = "reconciliation_packet.json"
NEGATIVE_INPUT_NAMES = (
    "invalid_cp2_target.json",
    "missing_bifurcation_resolution.json",
    "post_t_evidence_ref.json",
    "unconfirmed_equity_lane_claim.json",
    "unsafe_dossier_mutation.json",
    "trading_advice_overclaim.json",
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


def _validate_oracle_diff(packet: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(packet, "oracle_diff")
    graded_rows: list[dict[str, Any]] = []
    for row in rows:
        row_id = str(row.get("row_id") or row.get("prediction_id") or "oracle_diff")
        prediction_id = str(row.get("prediction_id") or "")
        predicted = str(row.get("predicted_direction") or "")
        realized = str(row.get("realized_direction") or "")
        degraded = realized == DEGRADED_DIRECTION or row.get("feed_health") == "degraded"
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
    oracle = _validate_oracle_diff(packet)
    mutations = _validate_mutations(packet, case_id=case_id, observed=observed)
    findings.extend(cp1["findings"])
    findings.extend(cp2["findings"])
    findings.extend(oracle["findings"])
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
        "dossier_mutation_count": mutations["dossier_mutation_count"],
        "dossier_mutation_ids": mutations["dossier_mutation_ids"],
        "reconciliation_rows": _reconciliation_rows(
            cp1["selected_branch_by_target"],
            cp2["prediction_by_id"],
            oracle["oracle_diff_rows"],
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
    mutation_ids: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    oracle_by_prediction = {
        str(row.get("prediction_id")): row for row in oracle_rows if row.get("prediction_id")
    }
    for prediction_id, prediction in sorted(prediction_by_id.items()):
        target_id = str(prediction.get("target_id") or "")
        branch = selected_branch_by_target.get(target_id, {})
        oracle = oracle_by_prediction.get(prediction_id, {})
        rows.append(
            {
                "prediction_id": prediction_id,
                "target_id": target_id,
                "cp1_branch_id": branch.get("branch_id"),
                "direction": prediction.get("direction"),
                "confidence_band": prediction.get("confidence_band"),
                "oracle_feed_health": oracle.get("feed_health"),
                "direction_hit": oracle.get("direction_hit"),
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
    packet = validate_reconciliation_packet(payloads["reconciliation_packet"])
    negative_results = [
        validate_reconciliation_packet(payloads[name], case_id=name)
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
        "dossier_mutation_count": packet["dossier_mutation_count"],
        "dossier_mutation_ids": packet["dossier_mutation_ids"],
        "reconciliation_rows": packet["reconciliation_rows"],
        "prediction_reconciliation_board": {
            "headline": "Synthetic prediction reasoning is reconciled through CP1, CP2, oracle diff, and dossier mutation receipts.",
            "source_pattern_count": len(packet["source_pattern_ids"]),
            "valid_prediction_target_count": len(packet["valid_prediction_targets"]),
            "cp2_prediction_count": packet["cp2_prediction_count"],
            "oracle_diff_graded_count": packet["oracle_diff_graded_count"],
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
