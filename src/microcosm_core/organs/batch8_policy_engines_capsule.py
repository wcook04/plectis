"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch8_policy_engines_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, PROBE_MANIFEST_NAME, EXPECTED_ENGINES, EXPECTED_MODULE_IDS, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch8_policy_engines_bundle, result_card, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch8_policy_engines_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "lab_contract_audit_deterministic_red_gate",
    "market_fusion_readiness_fail_closed_gate",
    "campaign_dispatch_status_transition_adjudicator",
)

EXPECTED_MODULE_IDS: tuple[str, ...] = (
    "lab_contract_audit_deterministic_red_gate",
    "market_fusion_readiness_fail_closed_gate",
    "campaign_dispatch_status_transition_adjudicator",
)

EXPECTED_NEGATIVE_CASES = {
    "lab_contract_question_mark_red_gate": (
        "BATCH8_LAB_CONTRACT_QUESTION_MARK_RED_GATE",
    ),
    "market_fusion_missing_gate_refused": (
        "BATCH8_MARKET_FUSION_MISSING_GATE_REFUSED",
    ),
    "campaign_completed_to_running_refused": (
        "BATCH8_CAMPAIGN_COMPLETED_TO_RUNNING_REFUSED",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch8_policy_engine_public_substrate_capsule_not_runtime_or_release_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "provider_dispatch": False,
    "model_dispatch": False,
    "repo_mutation_authorized": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
    "live_campaign_execution_authorized": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Batch 8 policy-engine capsule validates exact copied non-secret macro "
    "source bodies and public synthetic exercises for Lab contract red/green "
    "gating, market-fusion fail-closed claim preflight, and campaign dispatch "
    "transition adjudication. It is not Lab correctness, not live campaign "
    "authority, not market validation, not provider dispatch, not repository "
    "mutation authority, not publication authority, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/lib/lab_contract_audit.py": (
        "def compute_lab_contract_audit(",
        "QUESTION_MARK_SCAN_NODES",
        "MARKET_FUSION_READINESS_REFUSAL",
    ),
    "system/lib/market_fusion_readiness.py": (
        "def preflight_candidate_situation(",
        "def preflight_consumer_claims(",
        "CANDIDATE_SITUATION_GATES",
    ),
    "system/lib/campaign_state_transition.py": (
        "LEGAL_DISPATCH_TRANSITIONS",
        "def validate_dispatch_transition(",
        "class CampaignTransitionError",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 8 Policy Engines Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _load_json(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_json` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_manifest_payload(input_path: Path, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_manifest_payload` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    local = input_path / "source_module_manifest.json"
    if local.is_file():
        return _load_json(local)
    return _load_json(public_root / SPEC.source_manifest_ref)


def _source_rows(input_path: Path, public_root: Path) -> dict[str, Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_rows` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _source_manifest_payload(input_path, public_root).get("modules")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("module_id")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("module_id")
    }


def _target_path(row: Mapping[str, Any], *, public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_target_path` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target_ref = str(row.get("target_ref") or "")
    if target_ref.startswith("microcosm-substrate/"):
        target_ref = target_ref[len("microcosm-substrate/") :]
    if target_ref:
        return public_root / target_ref
    manifest = public_root / SPEC.source_manifest_ref
    return manifest.parent / str(row.get("path") or "")


@contextmanager
def _temporary_sys_path(paths: list[Path]) -> Iterator[None]:
    """
    [ACTION]
    - Teleology: Implements `_temporary_sys_path` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    old_path = list(sys.path)
    for path in reversed([str(p) for p in paths if p]):
        if path not in sys.path:
            sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path[:] = old_path


def _source_modules_root(target_path: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_modules_root` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for candidate in (target_path.parent, *target_path.parents):
        if candidate.name == "source_modules":
            return candidate
    return target_path.parent


def _load_copied_module(module_id: str, rows: Mapping[str, Mapping[str, Any]], public_root: Path):
    """
    [ACTION]
    - Teleology: Implements `_load_copied_module` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row = rows[module_id]
    target = _target_path(row, public_root=public_root)
    module_name = f"_batch8_policy_engines_{module_id}"
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise ImportError(module_id)
    module = importlib.util.module_from_spec(spec)
    with _temporary_sys_path([_source_modules_root(target), public_root.parent]):
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    return module


def _write_lab_artifact(artifacts_dir: Path, node_id: str, data: Any) -> None:
    """
    [ACTION]
    - Teleology: Implements `_write_lab_artifact` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / f"{node_id}.json").write_text(
        json.dumps({"id": node_id, "data": data}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_green_lab_artifacts(artifacts_dir: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_write_green_lab_artifacts` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    _write_lab_artifact(
        artifacts_dir,
        "lab_cross_corr_v1",
        {
            "swarms": [],
            "bifurcations": [],
            "orphans": [],
            "confidence_asymmetries": [],
        },
    )
    _write_lab_artifact(
        artifacts_dir,
        "lab_cross_corr_v2",
        {
            "target_swarms": [],
            "directional_conflicts": [],
            "solo_targets": [],
            "thesis_stress": [],
            "valid_prediction_targets": ["XOM"],
        },
    )
    _write_lab_artifact(artifacts_dir, "lab_decide", {"epicentre_thesis": "locked thesis"})
    _write_lab_artifact(
        artifacts_dir,
        "lab_director",
        {
            "epicentre_thesis": "locked thesis",
            "predictions_t": [{"target_id": "XOM"}],
        },
    )


def _exercise_lab_contract_audit(
    rows: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exercise_lab_contract_audit` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    market = _load_copied_module("market_fusion_readiness_fail_closed_gate", rows, public_root)
    market_module_name = "system.lib.market_fusion_readiness"
    previous_market_module = sys.modules.get(market_module_name)
    sys.modules[market_module_name] = market
    try:
        lab = _load_copied_module("lab_contract_audit_deterministic_red_gate", rows, public_root)
    finally:
        if previous_market_module is None:
            sys.modules.pop(market_module_name, None)
        else:
            sys.modules[market_module_name] = previous_market_module
    lab.preflight_consumer_claims = market.preflight_consumer_claims
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        green_artifacts = root / "green"
        _write_green_lab_artifacts(green_artifacts)
        green = lab.compute_lab_contract_audit(green_artifacts)

        red_artifacts = root / "red"
        _write_green_lab_artifacts(red_artifacts)
        _write_lab_artifact(
            red_artifacts,
            "lab_cross_corr_v1",
            {
                "swarms": [{"summary": "This public fixture carries a banned question mark?"}],
                "bifurcations": [],
                "orphans": [],
                "confidence_asymmetries": [],
            },
        )
        red = lab.compute_lab_contract_audit(red_artifacts)

    hard_fails = list(red.get("hard_fails") or [])
    return {
        "status": "pass"
        if green.get("status") == "green"
        and red.get("status") == "red"
        and "QUESTION_MARK_OUTPUT" in hard_fails
        else "blocked",
        "engine_id": "lab_contract_audit_deterministic_red_gate",
        "green_status": green.get("status"),
        "red_status": red.get("status"),
        "red_hard_fails": hard_fails,
        "negative_case_code": "BATCH8_LAB_CONTRACT_QUESTION_MARK_RED_GATE",
        "claim_ceiling": "Lab contract audit mechanics over synthetic public artifacts only.",
        "body_in_receipt": False,
    }


def _exercise_market_fusion(
    rows: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exercise_market_fusion` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    market = _load_copied_module("market_fusion_readiness_fail_closed_gate", rows, public_root)
    known = market.preflight_candidate_situation(
        situation_id="macro_event_x_equity_response",
        lanes=["MACRO", "STOCK"],
        attempted_claim="Macro event validates equity response.",
        consumer_name="microcosm_fixture",
        claim_id="known_gate",
    )
    unknown = market.preflight_candidate_situation(
        lanes=["NEWS", "CALC"],
        attempted_claim="Unregistered cross-feed claim.",
        consumer_name="microcosm_fixture",
        claim_id="missing_gate",
    )
    malformed = market.preflight_consumer_claims(
        {"consumer_name": "microcosm_fixture", "claims": "not a list"}
    )[0]
    known_reasons = tuple(known.get("refusal_reasons") or ())
    unknown_reasons = tuple(unknown.get("refusal_reasons") or ())
    malformed_reasons = tuple(malformed.get("refusal_reasons") or ())
    return {
        "status": "pass"
        if known.get("decision") == "refuse"
        and known_reasons
        and "candidate_situation_gate_missing" not in known_reasons
        and unknown.get("decision") == "refuse"
        and "candidate_situation_gate_missing" in unknown_reasons
        and malformed.get("decision") == "refuse"
        and "candidate_situation_gate_missing" in malformed_reasons
        else "blocked",
        "engine_id": "market_fusion_readiness_fail_closed_gate",
        "known_gate_decision": known.get("decision"),
        "known_gate_refusal_reasons": list(known_reasons),
        "missing_gate_decision": unknown.get("decision"),
        "missing_gate_refusal_reasons": list(unknown_reasons),
        "malformed_payload_decision": malformed.get("decision"),
        "malformed_payload_refusal_reasons": list(malformed_reasons),
        "negative_case_code": "BATCH8_MARKET_FUSION_MISSING_GATE_REFUSED",
        "claim_ceiling": "Market-fusion readiness gate mechanics over public fixture claims only.",
        "body_in_receipt": False,
    }


def _exercise_campaign_transition(
    rows: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exercise_campaign_transition` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    campaign = _load_copied_module(
        "campaign_dispatch_status_transition_adjudicator",
        rows,
        public_root,
    )
    legal = campaign.validate_dispatch_transition("candidate", "blocked")
    idempotent = campaign.validate_dispatch_transition("completed", "completed")
    illegal_message = ""
    illegal_refused = False
    try:
        campaign.validate_dispatch_transition("completed", "running")
    except campaign.CampaignTransitionError as exc:
        illegal_refused = True
        illegal_message = str(exc)
    return {
        "status": "pass"
        if legal == "legal_transition"
        and idempotent == "already_target"
        and illegal_refused
        and "terminal" in illegal_message
        else "blocked",
        "engine_id": "campaign_dispatch_status_transition_adjudicator",
        "candidate_to_blocked": legal,
        "completed_to_completed": idempotent,
        "completed_to_running_refused": illegal_refused,
        "completed_to_running_message": illegal_message,
        "negative_case_code": "BATCH8_CAMPAIGN_COMPLETED_TO_RUNNING_REFUSED",
        "claim_ceiling": "Campaign dispatch status transition adjudicator only.",
        "body_in_receipt": False,
    }


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = public_root_for_path(input_dir)
    rows = _source_rows(input_dir, public_root)
    if case_id == "lab_contract_question_mark_red_gate":
        exercise = _exercise_lab_contract_audit(rows, public_root)
        hard_fails = list(exercise.get("red_hard_fails") or [])
        rejected = exercise.get("red_status") == "red" and "QUESTION_MARK_OUTPUT" in hard_fails
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_LAB_CONTRACT_QUESTION_MARK_RED_GATE"] if rejected else []
            ),
            "observed": {
                "green_status": exercise.get("green_status"),
                "red_status": exercise.get("red_status"),
                "red_hard_fails": hard_fails,
            },
            "derived_from": "copied_lab_contract_audit",
            "body_in_receipt": False,
        }
    if case_id == "market_fusion_missing_gate_refused":
        exercise = _exercise_market_fusion(rows, public_root)
        missing_reasons = list(exercise.get("missing_gate_refusal_reasons") or [])
        rejected = (
            exercise.get("missing_gate_decision") == "refuse"
            and "candidate_situation_gate_missing" in missing_reasons
        )
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_MARKET_FUSION_MISSING_GATE_REFUSED"] if rejected else []
            ),
            "observed": {
                "missing_gate_decision": exercise.get("missing_gate_decision"),
                "missing_gate_refusal_reasons": missing_reasons,
            },
            "derived_from": "copied_market_fusion_readiness",
            "body_in_receipt": False,
        }
    if case_id == "campaign_completed_to_running_refused":
        exercise = _exercise_campaign_transition(rows, public_root)
        rejected = exercise.get("completed_to_running_refused") is True
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_CAMPAIGN_COMPLETED_TO_RUNNING_REFUSED"] if rejected else []
            ),
            "observed": {
                "completed_to_running_refused": rejected,
                "completed_to_running_message": exercise.get(
                    "completed_to_running_message"
                ),
            },
            "derived_from": "copied_campaign_transition_adjudicator",
            "body_in_receipt": False,
        }
    return {
        "status": "pass",
        "case_id": case_id,
        "error_codes": [],
        "body_in_receipt": False,
    }


def _capsule_evaluator(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_capsule_evaluator` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    probe = _load_json(input_path / PROBE_MANIFEST_NAME)
    mechanisms = [
        row
        for row in probe.get("mechanisms", [])
        if isinstance(row, Mapping) and row.get("engine_id")
    ]
    rows = _source_rows(input_path, public_root)
    findings: list[dict[str, Any]] = []
    engine_ids = [str(row.get("engine_id")) for row in mechanisms]
    if set(engine_ids) != set(EXPECTED_ENGINES):
        findings.append(
            finding(
                "BATCH8_POLICY_ENGINE_SET_MISMATCH",
                "Policy-engine probe manifest must enumerate the three Batch-8 policy engines.",
                expected=list(EXPECTED_ENGINES),
                observed=engine_ids,
            )
        )
    missing_modules = [module_id for module_id in EXPECTED_MODULE_IDS if module_id not in rows]
    if missing_modules:
        findings.append(
            finding(
                "BATCH8_POLICY_ENGINE_SOURCE_MODULE_MISSING",
                "Policy-engine capsule source module manifest is missing required modules.",
                expected=list(EXPECTED_MODULE_IDS),
                observed=sorted(rows),
            )
        )

    runtime_exercises: dict[str, dict[str, Any]] = {}
    if not missing_modules:
        runtime_exercises["lab_contract_audit_deterministic_red_gate"] = (
            _exercise_lab_contract_audit(rows, public_root)
        )
        runtime_exercises["market_fusion_readiness_fail_closed_gate"] = (
            _exercise_market_fusion(rows, public_root)
        )
        runtime_exercises["campaign_dispatch_status_transition_adjudicator"] = (
            _exercise_campaign_transition(rows, public_root)
        )
    blocked = [row for row in runtime_exercises.values() if row.get("status") != "pass"]
    for row in blocked:
        findings.append(
            finding(
                "BATCH8_POLICY_ENGINE_RUNTIME_BLOCKED",
                "Policy-engine copied source exercise did not pass.",
                subject_id=str(row.get("engine_id")),
                observed=row.get("status"),
            )
        )

    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(mechanisms),
        "engine_ids": sorted(engine_ids),
        "expected_engine_ids": list(EXPECTED_ENGINES),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "runtime_exercises": runtime_exercises,
        "error_codes": [
            row["negative_case_code"]
            for row in runtime_exercises.values()
            if row.get("negative_case_code")
        ],
        "body_in_receipt": False,
        "findings": findings,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_capsule_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch8_policy_engines_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch8_policy_engines_bundle` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_capsule_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    ceiling = (
        result.get("authority_ceiling")
        if isinstance(result.get("authority_ceiling"), Mapping)
        else {}
    )
    card["engine_count"] = exercise.get("engine_count")
    card["engine_ids"] = exercise.get("engine_ids")
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "model_dispatch": ceiling.get("model_dispatch"),
        "repo_mutation_authorized": ceiling.get("repo_mutation_authorized"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "release_authorized": ceiling.get("release_authorized"),
        "live_campaign_execution_authorized": ceiling.get(
            "live_campaign_execution_authorized"
        ),
        "whole_system_correctness_claim": ceiling.get(
            "whole_system_correctness_claim"
        ),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.batch8_policy_engines_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=(
            BUNDLE_INPUT_MODE
            if args.action == "validate-bundle"
            else "fixture_input"
        ),
        evaluator=_capsule_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(
        json.dumps(
            result_card(result) if args.card else result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
