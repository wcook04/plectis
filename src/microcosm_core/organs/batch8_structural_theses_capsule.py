"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch8_structural_theses_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, PROBE_MANIFEST_NAME, SOURCE_REF, EXPECTED_SOURCE_MODULE_IDS, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch8_structural_theses_bundle, result_card, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
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
import copy
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
    load_json_object,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch8_structural_theses_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

SOURCE_REF = "tools/finance/structural_theses.py"
EXPECTED_SOURCE_MODULE_IDS: tuple[str, ...] = (
    "system_package_init_dependency",
    "feed_envelope_dependency",
    "system_types_dependency",
    "tools_package_init_dependency",
    "tools_finance_package_init_dependency",
    "finance_admit_forecasts_dependency",
    "finance_eval_replay_dependency",
    "finance_event_keys_dependency",
    "finance_historical_replay_dependency",
    "finance_resolve_forecasts_dependency",
    "structural_theses_cp1_cp2_family",
    "finance_variant_registry_dependency",
)

EXPECTED_NEGATIVE_CASES = {
    "structural_theses_control_leak_rejected": (
        "BATCH8_STRUCTURAL_THESES_CONTROL_LEAK_REJECTED",
    ),
    "structural_theses_forward_gate_breach_rejected": (
        "BATCH8_STRUCTURAL_THESES_FORWARD_GATE_BREACH_REJECTED",
    ),
    "structural_theses_survivor_only_rejected": (
        "BATCH8_STRUCTURAL_THESES_SURVIVOR_ONLY_REJECTED",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch8_structural_theses_public_fixture_not_financial_advice_or_release_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "python_import": True,
    "financial_advice_authorized": False,
    "investment_recommendation_authorized": False,
    "live_market_data_authorized": False,
    "portfolio_action_authorized": False,
    "provider_calls_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Batch 8 structural_theses capsule validates exact copied non-secret macro "
    "source and public synthetic winner/loser/control exercises through the "
    "real CP1/CP2 finance spine. It is not financial advice, not investment "
    "recommendation, not live market data, not provider dispatch, not portfolio "
    "action, not publication authority, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    SOURCE_REF: (
        "STRUCTURAL_THESIS_CARD_SCHEMA",
        "def horizon_to_days",
        "def build_structural_thesis_family",
        "def validate_structural_thesis_family",
        "AUTHORITY_CEILING",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 8 Structural Theses Capsule",
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


@contextmanager
def _temporary_sys_path(paths: list[Path]) -> Iterator[None]:
    """
    [ACTION]
    - Teleology: Implements `_temporary_sys_path` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
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


@contextmanager
def _temporary_import_namespaces(prefixes: tuple[str, ...]) -> Iterator[None]:
    """
    [ACTION]
    - Teleology: Implements `_temporary_import_namespaces` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    saved = {
        name: module
        for name, module in list(sys.modules.items())
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes)
    }
    for name in saved:
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
                sys.modules.pop(name, None)
        sys.modules.update(saved)


def _load_copied_structural_module(public_root: Path, source_manifest: Mapping[str, Any]):
    """
    [ACTION]
    - Teleology: Implements `_load_copied_structural_module` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = source_manifest.get("source_manifest_path")
    if isinstance(manifest_path, str) and manifest_path:
        target = Path(manifest_path).parent / "source_modules/tools/finance/structural_theses.py"
        source_modules_root = Path(manifest_path).parent / "source_modules"
    else:
        target = (
            public_root
            / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules/tools/finance/structural_theses.py"
        )
        source_modules_root = target.parents[2]
    spec = importlib.util.spec_from_file_location("_batch8_structural_theses_copy", target)
    if spec is None or spec.loader is None:
        raise ImportError("structural_theses copied source module")
    module = importlib.util.module_from_spec(spec)
    with _temporary_sys_path([source_modules_root, public_root.parent]):
        with _temporary_import_namespaces(("system", "tools")):
            sys.modules["_batch8_structural_theses_copy"] = module
            spec.loader.exec_module(module)
    return module


def _family_inputs(probe: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], Mapping[str, Mapping[str, float]], Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_family_inputs` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    theses = probe.get("theses")
    realized = probe.get("realized_returns")
    sampling_frame = probe.get("sampling_frame")
    return (
        [row for row in theses if isinstance(row, Mapping)] if isinstance(theses, list) else [],
        realized if isinstance(realized, Mapping) else {},
        sampling_frame if isinstance(sampling_frame, Mapping) else {},
    )


def _build_family(module: Any, probe: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_family` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    theses, realized, sampling_frame = _family_inputs(probe)
    with tempfile.TemporaryDirectory(prefix="batch8_structural_theses_") as tmp:
        return module.build_structural_thesis_family(
            theses,
            realized,
            run_dir=Path(tmp),
            benchmark=str(probe.get("benchmark") or "BMK"),
            sampling_frame=sampling_frame,
            split_policy=str(probe.get("split_policy") or "purged_holdout"),
            embargo_days=int(probe.get("embargo_days") or 0),
        )


def _by_id(family: Mapping[str, Any], thesis_id: str) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_by_id` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for row in family.get("thesis_results", []):
        if isinstance(row, Mapping) and row.get("thesis_id") == thesis_id:
            return row
    return {}


def _codes(findings: list[Mapping[str, Any]]) -> set[str]:
    """
    [ACTION]
    - Teleology: Implements `_codes` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {str(row.get("error_code")) for row in findings if row.get("error_code")}


def _evaluate_negative_exercises(module: Any, probe: Mapping[str, Any], input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate_negative_exercises` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    survivor_payload = load_json_object(
        input_path / "structural_theses_survivor_only_rejected.json",
        findings,
        label="survivor-only negative",
    )
    forward_payload = load_json_object(
        input_path / "structural_theses_forward_gate_breach_rejected.json",
        findings,
        label="forward-gate negative",
    )
    control_payload = load_json_object(
        input_path / "structural_theses_control_leak_rejected.json",
        findings,
        label="control-leak negative",
    )
    theses, realized, sampling_frame = _family_inputs(probe)
    winners = [row for row in theses if str(row.get("thesis_id", "")).startswith("sob_")]
    realized_winners = {
        key: value for key, value in realized.items() if str(key).startswith("sob_")
    }
    survivor_frame = dict(sampling_frame)
    survivor_frame.update(
        {
            "considered_count": len(winners),
            "admitted_count": len(winners),
            "excluded_count": 0,
            "includes_failed_thesis": False,
        }
    )
    with tempfile.TemporaryDirectory(prefix="batch8_structural_survivor_") as tmp:
        survivor_family = module.build_structural_thesis_family(
            winners,
            realized_winners,
            run_dir=Path(tmp),
            benchmark=str(probe.get("benchmark") or "BMK"),
            sampling_frame=survivor_frame,
            split_policy="purged_holdout",
        )
    survivor_codes = _codes(module.validate_structural_thesis_family(survivor_family))
    expected_survivor = {"NO_LOSER_FLOWED_THROUGH", "NO_NEGATIVE_CONTROL", "SURVIVORSHIP_SAMPLE"}
    if not expected_survivor.issubset(survivor_codes) or survivor_payload.get("expected_decision") != "reject":
        findings.append(
            finding(
                "BATCH8_STRUCTURAL_THESES_SURVIVOR_ONLY_REJECTED",
                "Survivor-only structural-thesis corpora must be rejected.",
                expected=sorted(expected_survivor),
                observed=sorted(survivor_codes),
            )
        )

    family = _build_family(module, probe)
    breached = copy.deepcopy(family)
    breached["forward_lens"]["candidates"].append(
        {
            "structural_pattern": "regulatory_moat_divergence",
            "current_situation_descriptor": "smuggled forward candidate",
            "research_state": "review_candidate",
            "winner_language_allowed": False,
        }
    )
    forward_codes = _codes(module.validate_structural_thesis_family(breached))
    if "FORWARD_GATE_BREACH" not in forward_codes or forward_payload.get("expected_decision") != "reject":
        findings.append(
            finding(
                "BATCH8_STRUCTURAL_THESES_FORWARD_GATE_BREACH_REJECTED",
                "Refuted patterns must not be promoted into forward review candidates.",
                expected="FORWARD_GATE_BREACH",
                observed=sorted(forward_codes),
            )
        )

    leaked = copy.deepcopy(family)
    for row in leaked.get("thesis_results", []):
        if isinstance(row, dict) and row.get("is_control"):
            row["correctness"] = "claim_confirmed_forward"
    control_codes = _codes(module.validate_structural_thesis_family(leaked))
    if "CONTROL_LEAK" not in control_codes or control_payload.get("expected_decision") != "reject":
        findings.append(
            finding(
                "BATCH8_STRUCTURAL_THESES_CONTROL_LEAK_REJECTED",
                "Negative controls must not leak into confirmed-claim state.",
                expected="CONTROL_LEAK",
                observed=sorted(control_codes),
            )
        )

    return (
        {
            "survivor_only_codes": sorted(survivor_codes),
            "forward_gate_codes": sorted(forward_codes),
            "control_leak_codes": sorted(control_codes),
            "status": "pass" if not findings else "blocked",
            "body_in_receipt": False,
        },
        findings,
    )


def _semantic_module_and_probe(input_dir: Path) -> tuple[Any, Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_module_and_probe` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = public_root_for_path(input_dir)
    manifest_path = input_dir / "source_module_manifest.json"
    source_manifest = (
        {"source_manifest_path": str(manifest_path)} if manifest_path.is_file() else {}
    )
    module = _load_copied_structural_module(public_root, source_manifest)
    probe = load_json_object(input_dir / PROBE_MANIFEST_NAME, [], label=PROBE_MANIFEST_NAME)
    return module, probe


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    module, probe = _semantic_module_and_probe(input_dir)
    if case_id == "structural_theses_survivor_only_rejected":
        theses, realized, sampling_frame = _family_inputs(probe)
        winners = [
            row for row in theses if str(row.get("thesis_id", "")).startswith("sob_")
        ]
        realized_winners = {
            key: value
            for key, value in realized.items()
            if str(key).startswith("sob_")
        }
        survivor_frame = dict(sampling_frame)
        survivor_frame.update(
            {
                "considered_count": len(winners),
                "admitted_count": len(winners),
                "excluded_count": 0,
                "includes_failed_thesis": False,
            }
        )
        with tempfile.TemporaryDirectory(prefix="batch8_structural_survivor_") as tmp:
            survivor_family = module.build_structural_thesis_family(
                winners,
                realized_winners,
                run_dir=Path(tmp),
                benchmark=str(probe.get("benchmark") or "BMK"),
                sampling_frame=survivor_frame,
                split_policy="purged_holdout",
            )
        survivor_codes = _codes(module.validate_structural_thesis_family(survivor_family))
        expected = {
            "NO_LOSER_FLOWED_THROUGH",
            "NO_NEGATIVE_CONTROL",
            "SURVIVORSHIP_SAMPLE",
        }
        rejected = expected.issubset(survivor_codes)
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_STRUCTURAL_THESES_SURVIVOR_ONLY_REJECTED"]
                if rejected
                else []
            ),
            "observed": {"survivor_only_codes": sorted(survivor_codes)},
            "derived_from": "copied_structural_theses_validation",
            "body_in_receipt": False,
        }
    if case_id == "structural_theses_forward_gate_breach_rejected":
        family = _build_family(module, probe)
        breached = copy.deepcopy(family)
        breached["forward_lens"]["candidates"].append(
            {
                "structural_pattern": "regulatory_moat_divergence",
                "current_situation_descriptor": "smuggled forward candidate",
                "research_state": "review_candidate",
                "winner_language_allowed": False,
            }
        )
        forward_codes = _codes(module.validate_structural_thesis_family(breached))
        rejected = "FORWARD_GATE_BREACH" in forward_codes
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_STRUCTURAL_THESES_FORWARD_GATE_BREACH_REJECTED"]
                if rejected
                else []
            ),
            "observed": {"forward_gate_codes": sorted(forward_codes)},
            "derived_from": "copied_structural_theses_validation",
            "body_in_receipt": False,
        }
    if case_id == "structural_theses_control_leak_rejected":
        family = _build_family(module, probe)
        leaked = copy.deepcopy(family)
        for row in leaked.get("thesis_results", []):
            if isinstance(row, dict) and row.get("is_control"):
                row["correctness"] = "claim_confirmed_forward"
        control_codes = _codes(module.validate_structural_thesis_family(leaked))
        rejected = "CONTROL_LEAK" in control_codes
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_STRUCTURAL_THESES_CONTROL_LEAK_REJECTED"]
                if rejected
                else []
            ),
            "observed": {"control_leak_codes": sorted(control_codes)},
            "derived_from": "copied_structural_theses_validation",
            "body_in_receipt": False,
        }
    return {
        "status": "pass",
        "case_id": case_id,
        "error_codes": [],
        "body_in_receipt": False,
    }


def _structural_evaluator(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_structural_evaluator` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    probe = load_json_object(input_path / PROBE_MANIFEST_NAME, [], label=PROBE_MANIFEST_NAME)
    try:
        module = _load_copied_structural_module(public_root, source_manifest)
        family = _build_family(module, probe)
    except Exception as exc:
        return {
            "status": "blocked",
            "engine_id": "structural_theses_public_fixture_cp1_cp2",
            "findings": [
                finding(
                    "BATCH8_STRUCTURAL_THESES_RUNTIME_EXCEPTION",
                    "Copied structural_theses source failed to execute the public fixture.",
                    observed=str(exc),
                )
            ],
            "body_in_receipt": False,
        }
    validation_findings = module.validate_structural_thesis_family(family)
    findings: list[dict[str, Any]] = [
        finding(
            "BATCH8_STRUCTURAL_THESES_VALID_FAMILY_FINDING",
            "Winner/loser/control public fixture must validate cleanly.",
            observed=validation_findings,
        )
    ] if validation_findings else []
    negative_results, negative_findings = _evaluate_negative_exercises(module, probe, input_path)
    findings.extend(negative_findings)

    winner = _by_id(family, "sob_2015")
    loser = _by_id(family, "rmd_2018_loser")
    control = _by_id(family, "ctrl_2020")
    memory = {
        row.get("family_id"): row
        for row in family.get("family_memory", [])
        if isinstance(row, Mapping)
    }
    expected_clean = (
        winner.get("correctness") == "claim_confirmed_forward"
        and loser.get("correctness") == "claim_refuted_forward"
        and loser.get("loser_is_valid_evidence") is True
        and control.get("is_control") is True
        and control.get("correctness") != "claim_confirmed_forward"
        and memory.get("second_order_beneficiary", {}).get("memory_state") == "candidate_set"
        and family.get("authority_boundary", {}).get("investment_recommendation_authorized") is False
    )
    if not expected_clean:
        findings.append(
            finding(
                "BATCH8_STRUCTURAL_THESES_REFERENCE_CASE_MISMATCH",
                "Structural thesis fixture must preserve winner/loser/control semantics.",
                observed={
                    "winner": winner.get("correctness"),
                    "loser": loser.get("correctness"),
                    "control": control.get("correctness"),
                },
            )
        )

    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "structural_theses_public_fixture_cp1_cp2",
        "source_language": "Python",
        "source_ref": SOURCE_REF,
        "thesis_result_count": len(family.get("thesis_results", [])),
        "family_memory_count": len(family.get("family_memory", [])),
        "forward_surviving_pattern_count": family.get("forward_lens", {}).get("surviving_pattern_count"),
        "winner_correctness": winner.get("correctness"),
        "loser_correctness": loser.get("correctness"),
        "loser_is_valid_evidence": loser.get("loser_is_valid_evidence"),
        "control_correctness": control.get("correctness"),
        "control_is_control": control.get("is_control"),
        "authority_boundary": family.get("authority_boundary"),
        "negative_exercises": negative_results,
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "error_codes": sorted(
            {
                "BATCH8_STRUCTURAL_THESES_CONTROL_LEAK_REJECTED",
                "BATCH8_STRUCTURAL_THESES_FORWARD_GATE_BREACH_REJECTED",
                "BATCH8_STRUCTURAL_THESES_SURVIVOR_ONLY_REJECTED",
            }
        ),
        "claim_ceiling": "Public synthetic structural-thesis replay only; no advice, provider, portfolio, publication, or release authority.",
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
    - Teleology: Implements `run` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=_structural_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch8_structural_theses_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch8_structural_theses_bundle` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=_structural_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
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
    card["thesis_result_count"] = exercise.get("thesis_result_count")
    card["family_memory_count"] = exercise.get("family_memory_count")
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "python_import": ceiling.get("python_import"),
        "financial_advice_authorized": ceiling.get("financial_advice_authorized"),
        "investment_recommendation_authorized": ceiling.get(
            "investment_recommendation_authorized"
        ),
        "live_market_data_authorized": ceiling.get("live_market_data_authorized"),
        "portfolio_action_authorized": ceiling.get("portfolio_action_authorized"),
        "provider_calls_authorized": ceiling.get("provider_calls_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "release_authorized": ceiling.get("release_authorized"),
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
    - Teleology: Implements `main` for `microcosm_core.organs.batch8_structural_theses_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=_structural_evaluator,
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
