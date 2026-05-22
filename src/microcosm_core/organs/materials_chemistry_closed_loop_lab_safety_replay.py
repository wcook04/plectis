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


ORGAN_ID = "materials_chemistry_closed_loop_lab_safety_replay"
FIXTURE_ID = "first_wave.materials_chemistry_closed_loop_lab_safety_replay"
VALIDATOR_ID = "validator.microcosm.organs.materials_chemistry_closed_loop_lab_safety_replay"

RESULT_NAME = "materials_chemistry_closed_loop_lab_safety_replay_result.json"
BOARD_NAME = "materials_chemistry_closed_loop_lab_safety_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "materials_chemistry_closed_loop_lab_safety_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_materials_lab_safety_bundle_validation_result.json"

INPUT_NAMES = (
    "lab_safety_protocol.json",
    "replay_policy.json",
    "candidate_materials.json",
    "experiment_dag.json",
    "simulator_assays.json",
    "active_learning_decisions.json",
)
NEGATIVE_INPUT_NAMES = (
    "wetlab_protocol_steps.json",
    "hazardous_synthesis_steps.json",
    "reagent_amounts.json",
    "controlled_or_bioactive_target.json",
    "live_lab_credentials.json",
    "robot_command_execution.json",
    "private_lab_notebook_export.json",
    "discovery_claim.json",
)
EXPECTED_NEGATIVE_CASES = {
    "wetlab_protocol_steps": ["MATERIALS_WETLAB_PROTOCOL_FORBIDDEN"],
    "hazardous_synthesis_steps": ["MATERIALS_HAZARDOUS_SYNTHESIS_FORBIDDEN"],
    "reagent_amounts": ["MATERIALS_REAGENT_AMOUNT_FORBIDDEN"],
    "controlled_or_bioactive_target": [
        "MATERIALS_CONTROLLED_OR_BIOACTIVE_TARGET_FORBIDDEN"
    ],
    "live_lab_credentials": ["MATERIALS_LIVE_LAB_CREDENTIAL_FORBIDDEN"],
    "robot_command_execution": ["MATERIALS_ROBOT_COMMAND_FORBIDDEN"],
    "private_lab_notebook_export": ["MATERIALS_PRIVATE_LAB_NOTEBOOK_FORBIDDEN"],
    "discovery_claim": ["MATERIALS_DISCOVERY_CLAIM_FORBIDDEN"],
}

REQUIRED_CANDIDATE_FIELDS = (
    "candidate_material_id",
    "target_property_label",
    "literature_capsule_ref",
    "safety_screen_ref",
    "non_actionable_literature_capsule",
    "controlled_substance_target",
    "bioactivity_target",
    "discovery_claim",
    "body_redacted",
)
REQUIRED_EXPERIMENT_FIELDS = (
    "experiment_id",
    "candidate_material_ref",
    "safety_screen_ref",
    "action_class",
    "assay_ref",
    "result_table_ref",
    "failure_taxonomy_ref",
    "budget_ref",
    "cold_replay_ref",
    "simulator_only",
    "wetlab_protocol_exported",
    "hazardous_synthesis_steps_exported",
    "reagent_amounts_included",
    "robot_command_authorized",
    "live_lab_credentials_present",
    "private_lab_notebook_exported",
    "release_authorized",
    "body_redacted",
)
REQUIRED_ASSAY_FIELDS = (
    "assay_id",
    "experiment_ref",
    "candidate_material_ref",
    "simulator_only",
    "property_proxy",
    "result_table_ref",
    "uncertainty_label",
    "live_assay_data_exported",
    "discovery_claim",
    "body_redacted",
)
REQUIRED_DECISION_FIELDS = (
    "decision_id",
    "experiment_ref",
    "candidate_material_ref",
    "next_action_class",
    "decision_rationale_ref",
    "uncertainty_label",
    "cold_replay_ref",
    "simulator_only",
    "live_robot_command_emitted",
    "discovery_claim",
    "body_redacted",
)
REQUIRED_PROJECTION_PROTOCOL_FIELDS = (
    "copied",
    "reimplemented",
    "cleaned",
    "omitted",
    "public_replacement",
    "authority_ceiling",
    "validation_proves",
)
ALLOWED_ACTION_CLASSES = {
    "screen_candidate",
    "simulate_assay",
    "update_surrogate_model",
    "choose_next_simulation",
}
PRIVATE_NEEDLES = (
    "/Users/",
    "src/ai_workflow",
    "sk-",
    "PRIVATE_LAB_NOTEBOOK",
    "wetlab_step_body",
    "reagent_quantity_body",
    "robot_command_payload",
    "credential_secret",
)
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "simulator_only_materials_chemistry_lab_safety_metadata",
    "metadata_projection_only": True,
    "simulator_only": True,
    "wetlab_protocol_authorized": False,
    "hazardous_synthesis_authorized": False,
    "reagent_amounts_authorized": False,
    "controlled_substance_target_authorized": False,
    "bioactivity_target_authorized": False,
    "live_lab_credentials_authorized": False,
    "robot_command_authorized": False,
    "private_lab_notebook_exported": False,
    "live_assay_data_exported": False,
    "discovery_claim_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
    "hosted_public_authorized": False,
    "publication_authorized": False,
    "provider_calls_authorized": False,
}
ANTI_CLAIM = (
    "Materials chemistry closed-loop lab-safety replay validates synthetic, "
    "simulator-only metadata rows that bind candidate materials, safety screens, "
    "simulated assays, active-learning decisions, and cold replay refs. It does "
    "not export wetlab protocols, hazardous synthesis steps, reagent amounts, "
    "controlled or bioactive targets, live lab credentials, robot commands, "
    "private lab notebooks, live assay data, discovery claims, benchmark scores, "
    "or release authority."
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


def _missing_fields(
    row: dict[str, Any],
    fields: tuple[str, ...],
    *,
    code: str,
    kind: str,
    row_id: str,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for field in fields:
        if field not in row:
            _record(
                findings,
                observed,
                code,
                f"{kind} row is missing required field {field}",
                case_id=case_id,
                subject_id=row_id,
                subject_kind=kind,
            )
    return findings


def _has_private_body(row: dict[str, Any]) -> bool:
    encoded = json.dumps(row, sort_keys=True)
    return any(needle in encoded for needle in PRIVATE_NEEDLES)


def _candidate_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("candidate_material_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_CANDIDATE_FIELDS,
            code="MATERIALS_CANDIDATE_FIELD_REQUIRED",
            kind="candidate_material",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if not row.get("literature_capsule_ref") or not row.get("safety_screen_ref"):
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_LINEAGE_REQUIRED",
            "candidate rows must bind literature-capsule and safety-screen refs",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("controlled_substance_target") is True or row.get("bioactivity_target") is True:
        _record(
            findings,
            observed,
            "MATERIALS_CONTROLLED_OR_BIOACTIVE_TARGET_FORBIDDEN",
            "controlled-substance and bioactivity targets are outside this public contract",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("discovery_claim") is True:
        _record(
            findings,
            observed,
            "MATERIALS_DISCOVERY_CLAIM_FORBIDDEN",
            "candidate rows cannot claim discovery",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("private_lab_notebook_exported") is True:
        _record(
            findings,
            observed,
            "MATERIALS_PRIVATE_LAB_NOTEBOOK_FORBIDDEN",
            "private lab notebooks cannot enter public candidate rows",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("body_redacted") is not True or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_REDACTION_REQUIRED",
            "candidate rows must be body-redacted metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    return findings


def _experiment_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    candidate_ids: set[str],
    assay_ids: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("experiment_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_EXPERIMENT_FIELDS,
            code="MATERIALS_EXPERIMENT_FIELD_REQUIRED",
            kind="experiment",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if row.get("candidate_material_ref") not in candidate_ids:
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_REF_REQUIRED",
            "experiment rows must reference a known candidate material",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    if assay_ids and row.get("assay_ref") not in assay_ids:
        _record(
            findings,
            observed,
            "MATERIALS_ASSAY_REF_REQUIRED",
            "experiment rows must reference a known simulator assay",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    if row.get("action_class") not in ALLOWED_ACTION_CLASSES:
        _record(
            findings,
            observed,
            "MATERIALS_ACTION_CLASS_REQUIRED",
            "experiment rows must use an allowed non-actionable action class",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    if row.get("simulator_only") is not True:
        _record(
            findings,
            observed,
            "MATERIALS_SIMULATOR_ONLY_REQUIRED",
            "experiment rows must be simulator-only",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    forbidden_fields = {
        "wetlab_protocol_exported": "MATERIALS_WETLAB_PROTOCOL_FORBIDDEN",
        "hazardous_synthesis_steps_exported": "MATERIALS_HAZARDOUS_SYNTHESIS_FORBIDDEN",
        "reagent_amounts_included": "MATERIALS_REAGENT_AMOUNT_FORBIDDEN",
        "live_lab_credentials_present": "MATERIALS_LIVE_LAB_CREDENTIAL_FORBIDDEN",
        "private_lab_notebook_exported": "MATERIALS_PRIVATE_LAB_NOTEBOOK_FORBIDDEN",
        "release_authorized": "MATERIALS_RELEASE_AUTHORITY_FORBIDDEN",
    }
    for field, code in forbidden_fields.items():
        if row.get(field) is True:
            _record(
                findings,
                observed,
                code,
                f"{field} must be false for public lab-safety replay rows",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="experiment",
            )
    if row.get("robot_command_authorized") is True:
        _record(
            findings,
            observed,
            "MATERIALS_ROBOT_COMMAND_FORBIDDEN",
            "experiment rows cannot authorize live robot commands",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    if row.get("body_redacted") is not True or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_REDACTION_REQUIRED",
            "experiment rows must be body-redacted metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    return findings


def _assay_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    candidate_ids: set[str],
    experiment_ids: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("assay_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_ASSAY_FIELDS,
            code="MATERIALS_ASSAY_FIELD_REQUIRED",
            kind="simulator_assay",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if row.get("experiment_ref") not in experiment_ids:
        _record(
            findings,
            observed,
            "MATERIALS_EXPERIMENT_REF_REQUIRED",
            "assay rows must reference a known experiment",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("candidate_material_ref") not in candidate_ids:
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_REF_REQUIRED",
            "assay rows must reference a known candidate material",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("simulator_only") is not True:
        _record(
            findings,
            observed,
            "MATERIALS_SIMULATOR_ONLY_REQUIRED",
            "assay rows must be simulator-only",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("live_assay_data_exported") is True:
        _record(
            findings,
            observed,
            "MATERIALS_LIVE_ASSAY_DATA_FORBIDDEN",
            "live assay data cannot enter public simulator assay rows",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("discovery_claim") is True:
        _record(
            findings,
            observed,
            "MATERIALS_DISCOVERY_CLAIM_FORBIDDEN",
            "assay rows cannot claim discovery",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("body_redacted") is not True or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_REDACTION_REQUIRED",
            "assay rows must be body-redacted metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    return findings


def _decision_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    candidate_ids: set[str],
    experiment_ids: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("decision_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_DECISION_FIELDS,
            code="MATERIALS_DECISION_FIELD_REQUIRED",
            kind="active_learning_decision",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if row.get("experiment_ref") not in experiment_ids:
        _record(
            findings,
            observed,
            "MATERIALS_EXPERIMENT_REF_REQUIRED",
            "decision rows must reference a known experiment",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("candidate_material_ref") not in candidate_ids:
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_REF_REQUIRED",
            "decision rows must reference a known candidate material",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("next_action_class") not in ALLOWED_ACTION_CLASSES:
        _record(
            findings,
            observed,
            "MATERIALS_ACTION_CLASS_REQUIRED",
            "decision rows must use an allowed non-actionable action class",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("simulator_only") is not True:
        _record(
            findings,
            observed,
            "MATERIALS_SIMULATOR_ONLY_REQUIRED",
            "decision rows must be simulator-only",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("live_robot_command_emitted") is True:
        _record(
            findings,
            observed,
            "MATERIALS_ROBOT_COMMAND_FORBIDDEN",
            "decision rows cannot emit live robot commands",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("discovery_claim") is True:
        _record(
            findings,
            observed,
            "MATERIALS_DISCOVERY_CLAIM_FORBIDDEN",
            "decision rows cannot claim discovery",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("body_redacted") is not True or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_REDACTION_REQUIRED",
            "decision rows must be body-redacted metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    return findings


def _required_policy_ok(policy: dict[str, Any]) -> bool:
    ceiling = policy.get("authority_ceiling")
    if not isinstance(ceiling, dict):
        return False
    expected_false = (
        "wetlab_protocol_authorized",
        "hazardous_synthesis_authorized",
        "reagent_amounts_authorized",
        "controlled_substance_target_authorized",
        "bioactivity_target_authorized",
        "live_lab_credentials_authorized",
        "robot_command_authorized",
        "private_lab_notebook_exported",
        "live_assay_data_exported",
        "discovery_claim_authorized",
        "benchmark_score_claim_authorized",
        "release_authorized",
        "hosted_public_authorized",
        "publication_authorized",
        "provider_calls_authorized",
    )
    return (
        ceiling.get("metadata_projection_only") is True
        and ceiling.get("simulator_only") is True
        and all(ceiling.get(key) is False for key in expected_false)
    )


def _projection_protocol_ok(protocol: dict[str, Any]) -> bool:
    projection = protocol.get("projection_protocol")
    if not isinstance(projection, dict):
        return False
    return all(field in projection for field in REQUIRED_PROJECTION_PROTOCOL_FIELDS)


def _negative_rows(payload: object) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return [], [], [], []
    candidates = _rows(payload, "candidate_materials")
    experiments = _rows(payload, "experiments")
    assays = _rows(payload, "simulator_assays")
    decisions = _rows(payload, "active_learning_decisions")
    for key, target in (
        ("candidate_material", candidates),
        ("experiment", experiments),
        ("simulator_assay", assays),
        ("active_learning_decision", decisions),
    ):
        row = payload.get(key)
        if isinstance(row, dict):
            target.append(row)
    return candidates, experiments, assays, decisions


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    public_root = _public_root_for_path(input_dir)
    lab_safety_protocol = payloads.get("lab_safety_protocol", {})
    replay_policy = payloads.get("replay_policy", {})
    candidates = _rows(payloads.get("candidate_materials", {}), "candidate_materials")
    experiments = _rows(payloads.get("experiment_dag", {}), "experiments")
    assays = _rows(payloads.get("simulator_assays", {}), "simulator_assays")
    decisions = _rows(payloads.get("active_learning_decisions", {}), "active_learning_decisions")
    candidate_ids = {
        str(row.get("candidate_material_id"))
        for row in candidates
        if row.get("candidate_material_id")
    }
    experiment_ids = {
        str(row.get("experiment_id")) for row in experiments if row.get("experiment_id")
    }
    assay_ids = {str(row.get("assay_id")) for row in assays if row.get("assay_id")}
    observed_negative_codes: dict[str, set[str]] = defaultdict(set)
    positive_findings: list[dict[str, Any]] = []

    if (
        not isinstance(lab_safety_protocol, dict)
        or lab_safety_protocol.get("selected_route_id") != ORGAN_ID
    ):
        positive_findings.append(
            _finding(
                "MATERIALS_PROTOCOL_ROUTE_REQUIRED",
                f"lab safety protocol must select {ORGAN_ID}",
                case_id="positive_fixture",
                subject_id="lab_safety_protocol",
                subject_kind="protocol",
            )
        )
    if not _projection_protocol_ok(
        lab_safety_protocol if isinstance(lab_safety_protocol, dict) else {}
    ):
        positive_findings.append(
            _finding(
                "MATERIALS_PROJECTION_PROTOCOL_REQUIRED",
                "lab safety protocol must declare projection copied/reimplemented/omitted controls",
                case_id="positive_fixture",
                subject_id="lab_safety_protocol",
                subject_kind="protocol",
            )
        )
    if not _required_policy_ok(replay_policy if isinstance(replay_policy, dict) else {}):
        positive_findings.append(
            _finding(
                "MATERIALS_AUTHORITY_CEILING_REQUIRED",
                "replay policy must declare simulator-only authority ceiling",
                case_id="positive_fixture",
                subject_id="replay_policy",
                subject_kind="policy",
            )
        )
    for row in candidates:
        positive_findings.extend(
            _candidate_findings(row, case_id="positive_fixture", observed=observed_negative_codes)
        )
    for row in experiments:
        positive_findings.extend(
            _experiment_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
                candidate_ids=candidate_ids,
                assay_ids=assay_ids,
            )
        )
    for row in assays:
        positive_findings.extend(
            _assay_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
                candidate_ids=candidate_ids,
                experiment_ids=experiment_ids,
            )
        )
    for row in decisions:
        positive_findings.extend(
            _decision_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
                candidate_ids=candidate_ids,
                experiment_ids=experiment_ids,
            )
        )
    selected_pattern_ids = _strings(
        lab_safety_protocol.get("selected_pattern_ids")
        if isinstance(lab_safety_protocol, dict)
        else []
    )
    experiment_id_list = [
        str(row.get("experiment_id")) for row in experiments if row.get("experiment_id")
    ]
    if selected_pattern_ids and selected_pattern_ids != experiment_id_list:
        positive_findings.append(
            _finding(
                "MATERIALS_SELECTED_PATTERN_IDS_MISMATCH",
                "selected_pattern_ids must exactly match validated experiment ids",
                case_id="positive_fixture",
                subject_id="lab_safety_protocol",
                subject_kind="protocol",
            )
        )

    negative_findings: list[dict[str, Any]] = []
    if include_negative:
        for name in NEGATIVE_INPUT_NAMES:
            case_id = Path(name).stem
            neg_candidates, neg_experiments, neg_assays, neg_decisions = _negative_rows(
                payloads.get(case_id, {})
            )
            for row in neg_candidates:
                negative_findings.extend(
                    _candidate_findings(row, case_id=case_id, observed=observed_negative_codes)
                )
            for row in neg_experiments:
                negative_findings.extend(
                    _experiment_findings(
                        row,
                        case_id=case_id,
                        observed=observed_negative_codes,
                        candidate_ids=candidate_ids | {
                            str(candidate.get("candidate_material_id"))
                            for candidate in neg_candidates
                            if candidate.get("candidate_material_id")
                        },
                        assay_ids=assay_ids | {
                            str(assay.get("assay_id"))
                            for assay in neg_assays
                            if assay.get("assay_id")
                        },
                    )
                )
            neg_experiment_ids = experiment_ids | {
                str(experiment.get("experiment_id"))
                for experiment in neg_experiments
                if experiment.get("experiment_id")
            }
            neg_candidate_ids = candidate_ids | {
                str(candidate.get("candidate_material_id"))
                for candidate in neg_candidates
                if candidate.get("candidate_material_id")
            }
            for row in neg_assays:
                negative_findings.extend(
                    _assay_findings(
                        row,
                        case_id=case_id,
                        observed=observed_negative_codes,
                        candidate_ids=neg_candidate_ids,
                        experiment_ids=neg_experiment_ids,
                    )
                )
            for row in neg_decisions:
                negative_findings.extend(
                    _decision_findings(
                        row,
                        case_id=case_id,
                        observed=observed_negative_codes,
                        candidate_ids=neg_candidate_ids,
                        experiment_ids=neg_experiment_ids,
                    )
                )

    expected_cases = EXPECTED_NEGATIVE_CASES if include_negative else {}
    expected_missing = {
        case_id: sorted(set(codes) - observed_negative_codes.get(case_id, set()))
        for case_id, codes in expected_cases.items()
    }
    expected_missing = {case_id: codes for case_id, codes in expected_missing.items() if codes}
    encoded_positive = json.dumps(
        [candidates, experiments, assays, decisions], sort_keys=True
    )
    body_redacted = not any(needle in encoded_positive for needle in PRIVATE_NEEDLES)
    policy_passed = (
        bool(candidates)
        and bool(experiments)
        and bool(assays)
        and bool(decisions)
        and not positive_findings
        and body_redacted
        and not expected_missing
        and all(row.get("body_redacted") is True for row in candidates)
        and all(row.get("body_redacted") is True for row in experiments)
        and all(row.get("body_redacted") is True for row in assays)
        and all(row.get("body_redacted") is True for row in decisions)
        and all(row.get("simulator_only") is True for row in experiments)
        and all(row.get("simulator_only") is True for row in assays)
        and all(row.get("simulator_only") is True for row in decisions)
        and all(row.get("controlled_substance_target") is False for row in candidates)
        and all(row.get("bioactivity_target") is False for row in candidates)
        and all(row.get("discovery_claim") is False for row in candidates)
        and all(row.get("wetlab_protocol_exported") is False for row in experiments)
        and all(row.get("hazardous_synthesis_steps_exported") is False for row in experiments)
        and all(row.get("reagent_amounts_included") is False for row in experiments)
        and all(row.get("robot_command_authorized") is False for row in experiments)
        and all(row.get("live_lab_credentials_present") is False for row in experiments)
        and all(row.get("private_lab_notebook_exported") is False for row in experiments)
        and all(row.get("live_assay_data_exported") is False for row in assays)
        and all(row.get("discovery_claim") is False for row in assays)
        and all(row.get("live_robot_command_emitted") is False for row in decisions)
        and all(row.get("discovery_claim") is False for row in decisions)
    )
    scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    status = PASS if policy_passed and scan.get("status") == PASS else "blocked"
    summary = {
        "candidate_material_count": len(candidates),
        "experiment_count": len(experiments),
        "simulator_assay_count": len(assays),
        "active_learning_decision_count": len(decisions),
        "safety_screen_count": len(
            {
                str(row.get("safety_screen_ref"))
                for row in candidates + experiments
                if row.get("safety_screen_ref")
            }
        ),
        "simulator_only_experiment_count": sum(
            1 for row in experiments if row.get("simulator_only") is True
        ),
        "simulator_only_assay_count": sum(
            1 for row in assays if row.get("simulator_only") is True
        ),
        "cold_replay_count": sum(
            1 for row in experiments + decisions if row.get("cold_replay_ref")
        ),
        "wetlab_protocol_export_count": sum(
            1 for row in experiments if row.get("wetlab_protocol_exported") is True
        ),
        "hazardous_synthesis_export_count": sum(
            1
            for row in experiments
            if row.get("hazardous_synthesis_steps_exported") is True
        ),
        "reagent_amount_export_count": sum(
            1 for row in experiments if row.get("reagent_amounts_included") is True
        ),
        "controlled_or_bioactive_target_count": sum(
            1
            for row in candidates
            if row.get("controlled_substance_target") is True
            or row.get("bioactivity_target") is True
        ),
        "live_lab_credential_count": sum(
            1 for row in experiments if row.get("live_lab_credentials_present") is True
        ),
        "robot_command_count": sum(
            1
            for row in experiments + decisions
            if row.get("robot_command_authorized") is True
            or row.get("live_robot_command_emitted") is True
        ),
        "discovery_claim_count": sum(
            1
            for row in candidates + assays + decisions
            if row.get("discovery_claim") is True
        ),
    }
    return {
        "schema_version": "materials_chemistry_closed_loop_lab_safety_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "input_ref": _display(input_dir, public_root=public_root),
        "selected_route_id": ORGAN_ID,
        "selected_pattern_ids": experiment_id_list,
        "candidate_materials": candidates,
        "experiments": experiments,
        "simulator_assays": assays,
        "active_learning_decisions": decisions,
        "materials_lab_safety_summary": summary,
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
            "simulator_only": True,
            "wetlab_protocols_omitted": True,
            "hazardous_synthesis_steps_omitted": True,
            "reagent_amounts_omitted": True,
            "live_lab_credentials_omitted": True,
            "robot_commands_omitted": True,
            "private_lab_notebooks_omitted": True,
        },
        "release_authorized": False,
        "body_redacted": True,
        "private_state_scan": scan,
    }


def _board(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("materials_lab_safety_summary", {})
    negatives = result.get("negative_case_summary", {})
    return {
        "schema_version": "materials_chemistry_closed_loop_lab_safety_replay_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "materials_chemistry_lab_safety_public_board",
        "route": ORGAN_ID,
        "candidate_material_count": summary.get("candidate_material_count", 0)
        if isinstance(summary, dict)
        else 0,
        "experiment_count": summary.get("experiment_count", 0)
        if isinstance(summary, dict)
        else 0,
        "simulator_assay_count": summary.get("simulator_assay_count", 0)
        if isinstance(summary, dict)
        else 0,
        "active_learning_decision_count": summary.get("active_learning_decision_count", 0)
        if isinstance(summary, dict)
        else 0,
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
    summary = result.get("materials_lab_safety_summary") or {}
    negatives = result.get("negative_case_summary") or {}
    validation = {
        "schema_version": (
            "materials_chemistry_closed_loop_lab_safety_replay_validation_receipt_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "receipt_paths": receipt_paths,
        "candidate_material_count": summary.get("candidate_material_count"),
        "experiment_count": summary.get("experiment_count"),
        "simulator_assay_count": summary.get("simulator_assay_count"),
        "active_learning_decision_count": summary.get("active_learning_decision_count"),
        "expected_negative_case_count": negatives.get("expected_negative_case_count"),
        "observed_negative_case_count": negatives.get("observed_negative_case_count"),
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
        "schema_version": (
            "materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance_v1"
        ),
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
    return {**result, "materials_lab_safety_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs."
        "materials_chemistry_closed_loop_lab_safety_replay run"
    ),
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


def run_lab_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "materials_chemistry_closed_loop_lab_safety_replay run-lab-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_materials_lab_safety_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_materials_lab_safety_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="materials_chemistry_closed_loop_lab_safety_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-lab-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-lab-bundle":
        result = run_lab_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
