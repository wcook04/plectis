"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch7_oracle_sibling_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, EXERCISE_MANIFEST_NAME, EXPECTED_ENGINES, EXPECTED_NEGATIVE_CASES, NEGATIVE_CASE_CODES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch7_oracle_sibling_bundle, result_card, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common, tools.oracle
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch7_oracle_sibling_capsule"
FIXTURE_ID = "first_wave.batch7_oracle_sibling_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch7_oracle_sibling_capsule"

RESULT_NAME = "batch7_oracle_sibling_capsule_result.json"
BOARD_NAME = "batch7_oracle_sibling_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch7_oracle_sibling_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch7_oracle_sibling_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch7_oracle_sibling_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch7_oracle_sibling_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch7_oracle_sibling_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "oracle_subject_index_grounding_map",
    "oracle_subject_snapshot_hydration",
    "oracle_truth_diff_macro_series_delta",
    "oracle_quartet_repair_alias_plan",
    "oracle_original_pytest_witness",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_subject_run_dir": ("BATCH7_ORACLE_SUBJECT_RUN_REQUIRED",),
    "missing_artifact_id": ("BATCH7_ORACLE_ARTIFACT_ID_REQUIRED",),
    "macro_truth_run_missing": ("BATCH7_ORACLE_TRUTH_RUN_REQUIRED",),
    "quartet_run_missing_excluded": ("BATCH7_ORACLE_RUN_MISSING_EXCLUDED",),
    "original_pytest_witness_required": (
        "BATCH7_ORACLE_ORIGINAL_PYTEST_WITNESS_REQUIRED",
    ),
}

NEGATIVE_CASE_CODES = {
    case_id: codes[0] for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch7_oracle_sibling_capsule_not_oracle_reasoning_or_provider_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "oracle_run_missing_authorized": False,
    "godmode_engine_invocation_authorized": False,
    "source_mutation_authorized": False,
    "operator_thread_authority": False,
    "semantic_truth_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 7 Oracle sibling imports public-safe source bodies for subject index, "
    "subject snapshot, macro truth-diff, and deterministic quartet repair planning. "
    "It is not an Oracle reasoning run, not provider or bridge authority, not "
    "GodModeEngine invocation, not source mutation authority, and not proof that "
    "all Oracle paths are covered."
)

SOURCE_REQUIRED_ANCHORS = {
    "tools/oracle/subject_index.py": (
        "def _require_subject_run_dir",
        "def _is_admissible_target_entry",
        "phase2_lane_summaries",
        "oracle_subject_index",
    ),
    "tools/oracle/subject_snapshot.py": (
        "def _require_artifact_id",
        "hydrated_from_subject",
        "oracle_subject_snapshot",
    ),
    "tools/oracle/truth_diff_macro.py": (
        "_ID_KEYS",
        "changed_series",
        "new_series",
        "dropped_series",
        "oracle_truth_diff_macro",
    ),
    "tools/oracle/run_quartet.py": (
        "QUARTET = [",
        "def build_quartet_repair_plan",
        "def materialize_missing_aliases",
        "def run_missing_quartet",
        "GodModeEngine",
    ),
    "system/server/tests/test_oracle_v1_tools.py": (
        "test_oracle_subject_index_builds_subject_grounding_map",
        "test_oracle_subject_snapshot_loads_subject_artifact",
        "test_oracle_truth_diff_macro_emits_changed_series_without_as_of_equality",
    ),
    "system/server/tests/test_evolve_runner.py": (
        "test_oracle_quartet_repair_plan_materializes_existing_legacy_alias",
        "test_oracle_quartet_plan_stdout_publishes_compact_launcher_field",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 7 Oracle Sibling Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch7_oracle_sibling_capsule/"
        "exported_batch7_oracle_sibling_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_repo_root` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_root.parent


def _copied_source(public_root: Path, source_ref: str) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_copied_source` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        public_root
        / "examples/batch7_oracle_sibling_capsule/"
        "exported_batch7_oracle_sibling_capsule_bundle/source_modules"
        / source_ref
    )


def _load_oracle_modules(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_oracle_modules` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    repo_ref = str(repo_root)
    if repo_ref not in sys.path:
        sys.path.insert(0, repo_ref)
    from tools.oracle import run_quartet
    from tools.oracle import subject_index
    from tools.oracle import subject_snapshot
    from tools.oracle import truth_diff_macro

    return {
        "run_quartet": run_quartet,
        "subject_index": subject_index,
        "subject_snapshot": subject_snapshot,
        "truth_diff_macro": truth_diff_macro,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """
    [ACTION]
    - Teleology: Implements `_write_json` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def _feed(
    columns: list[str],
    rows: list[list[object]],
    *,
    as_of: str = "2026-03-03T14:00:00+00:00",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_feed` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "metadata": {"as_of": as_of},
        "data": {
            "topic": {
                "row": {
                    "columns": columns,
                    "rows": rows,
                }
            }
        },
    }


def _artifact(data: Mapping[str, Any], *, artifact_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_artifact` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "id": artifact_id,
        "metadata": {"artifact_id": artifact_id, "status": "success"},
        "data": dict(data),
    }


def _exception_negative_observation(
    action: Any,
    *,
    expected_fragment: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exception_negative_observation` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        action()
    except Exception as exc:  # noqa: BLE001 - receipt records type, not body.
        value_error = isinstance(exc, ValueError)
        fragment_observed = expected_fragment in str(exc)
        return {
            "status": "blocked" if value_error and fragment_observed else "pass",
            "exception_type": type(exc).__name__,
            "value_error_observed": value_error,
            "expected_fragment_observed": fragment_observed,
            "body_in_receipt": False,
        }
    return {
        "status": "pass",
        "exception_type": None,
        "value_error_observed": False,
        "expected_fragment_observed": False,
        "body_in_receipt": False,
    }


def _manifest_excludes_run_missing(input_path: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_manifest_excludes_run_missing` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = input_path / EXERCISE_MANIFEST_NAME
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    excluded = payload.get("explicitly_excluded") if isinstance(payload, dict) else []
    if not isinstance(excluded, list):
        return False
    return any(
        isinstance(row, Mapping)
        and row.get("source_ref") == "tools/oracle/run_quartet.py"
        and row.get("symbol") == "run_missing_quartet"
        for row in excluded
    )


def _lab_director_payload() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_lab_director_payload` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "metadata": {
            "as_of": "2026-03-03T14:00:00+00:00",
            "target_time_iso": "2026-03-03T21:00:00+00:00",
            "horizon_label": "Custom target",
        },
        "data": {
            "evidence_dictionary": [
                {
                    "ref_id": "[1]",
                    "ledger_id": "S_CAFEBABE",
                    "subject": "XOM",
                    "signal_summary": "Stock support.",
                },
                {
                    "ref_id": "[2]",
                    "ledger_id": "E_DEADBEEF",
                    "subject": "XLE",
                    "signal_summary": "ETF support.",
                },
            ],
            "epicentre_thesis": "word " * 160,
            "trade_rationale": "word " * 120,
            "predictions_t": [
                {
                    "target_id": "XOM",
                    "direction": "UP",
                    "snapshot_price": 100.0,
                    "target_price": 110.0,
                    "invalidation": "Lose trend support.",
                }
            ],
        },
    }


def _lab_decide_payload() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_lab_decide_payload` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "metadata": {"as_of": "2026-03-03T14:00:00+00:00"},
        "data": {
            "evidence_dictionary": [
                {
                    "ref_id": "[1]",
                    "ledger_id": "S_CAFEBABE",
                    "subject": "XOM",
                    "signal_summary": "Stock support.",
                },
            ],
            "epicentre_thesis": "word " * 160,
            "dominant_evidence_track": "FLOW_LED",
            "pre_pricing_assessment": "Most headline continuation was already visible in flow.",
        },
    }


def _seed_subject_run(subject_run: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_seed_subject_run` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    lab_director = _lab_director_payload()
    lab_director["data"]["evidence_dictionary"].append(
        {
            "ref_id": "[3]",
            "ledger_id": "M_FEEDBEEF",
            "subject": "TLT",
            "signal_summary": "Macro context only; no admissible T-n ETF grounding.",
        }
    )
    _write_json(
        subject_run / "runtime_context.json",
        {
            "as_of": "2026-03-03T14:00:00+00:00",
            "temporal_contract": {
                "target_time_iso": "2026-03-03T21:00:00+00:00"
            },
        },
    )
    _write_json(subject_run / "artifacts" / "lab_decide.json", _lab_decide_payload())
    _write_json(subject_run / "artifacts" / "lab_director.json", lab_director)
    _write_json(
        subject_run / "artifacts" / "lab_cross_corr_v2.json",
        {"metadata": {}, "data": {"valid_prediction_targets": ["XOM", "XLE", "TLT"]}},
    )
    _write_json(
        subject_run / "artifacts" / "global_stock_feed.json",
        _feed(["Ticker", "Price"], [["XOM", "100.0"]]),
    )
    _write_json(
        subject_run / "artifacts" / "global_etf_feed.json",
        _feed(["Ticker", "Price"], [["XLE", "90.0"]]),
    )


def _subject_index_engine(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_subject_index_engine` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    modules = _load_oracle_modules(repo_root)
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_subject_index_") as tmp:
        subject_run = Path(tmp) / "subject"
        _seed_subject_run(subject_run)
        try:
            result = modules["subject_index"].run(
                {"runtime": {"oracle_subject_run_dir": str(subject_run)}}
            )
        except Exception as exc:  # pragma: no cover - defensive receipt shaping.
            return {
                "status": "blocked",
                "engine_id": "oracle_subject_index_grounding_map",
                "error_code": "BATCH7_ORACLE_SUBJECT_INDEX_EXCEPTION",
                "error_type": type(exc).__name__,
                "body_in_receipt": False,
            }
    data = result.get("data") if isinstance(result, dict) else {}
    if not isinstance(data, dict):
        data = {}
    admissible = data.get("admissible_evidence_by_subject", {})
    contextual = data.get("contextual_evidence_by_subject", {})
    price_map = data.get("subject_equity_price_map", {})
    required = {
        "metadata_success": result.get("metadata", {}).get("status") == "success",
        "valid_prediction_targets_sorted": data.get("valid_prediction_targets")
        == ["TLT", "XLE", "XOM"],
        "xom_has_stock_support": (
            isinstance(admissible, dict)
            and admissible.get("XOM", [{}])[0].get("ledger_id") == "S_CAFEBABE"
        ),
        "xle_has_etf_support": (
            isinstance(admissible, dict)
            and admissible.get("XLE", [{}])[0].get("ledger_id") == "E_DEADBEEF"
        ),
        "tlt_stays_contextual": (
            isinstance(contextual, dict)
            and contextual.get("TLT", [{}])[0].get("ledger_id") == "M_FEEDBEEF"
        ),
        "missing_admissible_support_target_preserved": data.get(
            "missing_admissible_support_targets"
        )
        == ["TLT"],
        "subject_price_map_hydrated": (
            isinstance(price_map, dict)
            and price_map.get("XOM") == 100.0
            and price_map.get("XLE") == 90.0
        ),
    }
    return {
        "status": "pass" if all(required.values()) else "blocked",
        "engine_id": "oracle_subject_index_grounding_map",
        "source_tool": "tools.oracle.subject_index.run",
        **required,
        "claim_ceiling": "Subject-side grounding map only; no Oracle reasoning or provider dispatch.",
    }


def _subject_snapshot_engine(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_subject_snapshot_engine` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    modules = _load_oracle_modules(repo_root)
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_subject_snapshot_") as tmp:
        subject_run = Path(tmp) / "subject"
        _write_json(subject_run / "artifacts" / "lab_director.json", _lab_director_payload())
        try:
            result = modules["subject_snapshot"].run(
                {
                    "artifact_id": "lab_director",
                    "runtime": {"oracle_subject_run_dir": str(subject_run)},
                }
            )
        except Exception as exc:  # pragma: no cover - defensive receipt shaping.
            return {
                "status": "blocked",
                "engine_id": "oracle_subject_snapshot_hydration",
                "error_code": "BATCH7_ORACLE_SUBJECT_SNAPSHOT_EXCEPTION",
                "error_type": type(exc).__name__,
                "body_in_receipt": False,
            }
    metadata = result.get("metadata") if isinstance(result, dict) else {}
    data = result.get("data") if isinstance(result, dict) else {}
    predictions = data.get("predictions_t") if isinstance(data, dict) else []
    required = {
        "metadata_success": isinstance(metadata, dict)
        and metadata.get("status") == "success",
        "source_artifact_id_preserved": isinstance(metadata, dict)
        and metadata.get("source_artifact_id") == "lab_director",
        "subject_run_id_preserved": isinstance(metadata, dict)
        and metadata.get("subject_run_id") == "subject",
        "prediction_payload_hydrated": isinstance(predictions, list)
        and predictions
        and predictions[0].get("target_id") == "XOM",
    }
    return {
        "status": "pass" if all(required.values()) else "blocked",
        "engine_id": "oracle_subject_snapshot_hydration",
        "source_tool": "tools.oracle.subject_snapshot.run",
        **required,
        "claim_ceiling": "Subject artifact hydration only; no artifact body is copied into receipts.",
    }


def _truth_diff_macro_engine(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_truth_diff_macro_engine` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    modules = _load_oracle_modules(repo_root)
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_truth_diff_macro_") as tmp:
        subject_run = Path(tmp) / "subject"
        truth_run = Path(tmp) / "truth"
        _write_json(
            subject_run / "artifacts" / "global_macro_feed.json",
            _feed(
                ["slug", "value"],
                [["US10Y", "4.10"], ["DXY", "104.0"], ["OIL", "80.0"]],
                as_of="2026-03-03T14:00:00+00:00",
            ),
        )
        _write_json(
            truth_run / "artifacts" / "global_macro_feed.json",
            _feed(
                ["slug", "value"],
                [["US10Y", "4.35"], ["DXY", "104.0"], ["CPI", "3.1"]],
                as_of="2026-03-03T22:00:00+00:00",
            ),
        )
        try:
            result = modules["truth_diff_macro"].run(
                {
                    "runtime": {
                        "oracle_subject_run_dir": str(subject_run),
                        "oracle_truth_run_dir": str(truth_run),
                    }
                }
            )
        except Exception as exc:  # pragma: no cover - defensive receipt shaping.
            return {
                "status": "blocked",
                "engine_id": "oracle_truth_diff_macro_series_delta",
                "error_code": "BATCH7_ORACLE_TRUTH_DIFF_MACRO_EXCEPTION",
                "error_type": type(exc).__name__,
                "body_in_receipt": False,
            }
    data = result.get("data") if isinstance(result, dict) else {}
    changed = data.get("changed_series") if isinstance(data, dict) else []
    first_change = changed[0] if changed else {}
    changes = first_change.get("changes") if isinstance(first_change, dict) else []
    required = {
        "metadata_success": result.get("metadata", {}).get("status") == "success",
        "subject_as_of_preserved": data.get("subject_as_of")
        == "2026-03-03T14:00:00+00:00",
        "truth_as_of_preserved": data.get("truth_as_of")
        == "2026-03-03T22:00:00+00:00",
        "changed_series_ranked": first_change.get("series_id") == "US10Y",
        "value_field_changed": bool(changes) and changes[0].get("field") == "value",
        "new_series_detected": data.get("new_series") == ["CPI"],
        "dropped_series_detected": data.get("dropped_series") == ["OIL"],
    }
    return {
        "status": "pass" if all(required.values()) else "blocked",
        "engine_id": "oracle_truth_diff_macro_series_delta",
        "source_tool": "tools.oracle.truth_diff_macro.run",
        **required,
        "claim_ceiling": "Deterministic macro before/after diff only; no market feed access occurs.",
    }


def _quartet_repair_engine(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_quartet_repair_engine` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, declared filesystem outputs.
    """
    modules = _load_oracle_modules(repo_root)
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_quartet_") as tmp:
        subject_run = Path(tmp) / "subject"
        truth_run = Path(tmp) / "truth"
        subject_run.mkdir(parents=True)
        _write_json(
            truth_run / "artifacts" / "oracle_truth_diff_equity.json",
            _artifact(
                {
                    "status": "AVAILABLE",
                    "feed_health": {"status": "READY", "diagnostics": []},
                },
                artifact_id="oracle_truth_diff_equity",
            ),
        )
        try:
            plan = modules["run_quartet"].build_quartet_repair_plan(
                subject_run, truth_run
            )
            receipt = modules["run_quartet"].materialize_missing_aliases(
                subject_run, truth_run
            )
        except Exception as exc:  # pragma: no cover - defensive receipt shaping.
            return {
                "status": "blocked",
                "engine_id": "oracle_quartet_repair_alias_plan",
                "error_code": "BATCH7_ORACLE_QUARTET_REPAIR_EXCEPTION",
                "error_type": type(exc).__name__,
                "body_in_receipt": False,
            }
        alias_path = truth_run / "artifacts" / "prediction_reconciliation.json"
        alias_payload = json.loads(alias_path.read_text(encoding="utf-8"))
    readiness = plan.get("readiness", {}) if isinstance(plan, dict) else {}
    artifacts = plan.get("artifacts", []) if isinstance(plan, dict) else []
    status_counts: dict[str, int] = {}
    for artifact in artifacts:
        if isinstance(artifact, dict):
            status_counts[str(artifact.get("status"))] = (
                status_counts.get(str(artifact.get("status")), 0) + 1
            )
    required = {
        "plan_status_blocked_until_source_nodes_exist": readiness.get("status")
        == "BLOCKED",
        "prediction_reconciliation_aliasable": "prediction_reconciliation"
        in readiness.get("aliasable_artifacts", []),
        "deepest_missing_target_preserved": readiness.get("deepest_missing_target")
        == "oracle_cp2_emitter",
        "materialize_alias_written": len(receipt.get("written_paths", [])) == 1,
        "alias_metadata_preserved": alias_payload.get("metadata", {}).get(
            "artifact_alias_of"
        )
        == "oracle_truth_diff_equity",
        "run_missing_quartet_excluded": True,
        "godmode_engine_not_invoked": True,
    }
    return {
        "status": "pass" if all(required.values()) else "blocked",
        "engine_id": "oracle_quartet_repair_alias_plan",
        "source_tool": "tools.oracle.run_quartet.build_quartet_repair_plan",
        "materializer": "tools.oracle.run_quartet.materialize_missing_aliases",
        "status_counts": status_counts,
        **required,
        "claim_ceiling": "Deterministic quartet plan and temp-run alias materialization only; run_missing_quartet is not invoked.",
    }


def _run_original_pytest_witness(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_run_original_pytest_witness` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    command = [
        "./repo-python",
        "-m",
        "pytest",
        "-q",
        "system/server/tests/test_oracle_v1_tools.py",
        (
            "system/server/tests/test_evolve_runner.py::"
            "test_oracle_quartet_repair_plan_materializes_existing_legacy_alias"
        ),
        (
            "system/server/tests/test_evolve_runner.py::"
            "test_oracle_quartet_plan_stdout_publishes_compact_launcher_field"
        ),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except FileNotFoundError as exc:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_ORACLE_PYTEST_COMMAND_MISSING",
            "error_type": type(exc).__name__,
            "body_in_receipt": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_ORACLE_ORIGINAL_PYTEST_TIMEOUT",
            "body_in_receipt": False,
        }
    text = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"(\d+) passed", text)
    passed_count = int(match.group(1)) if match else None
    return {
        "status": "pass"
        if completed.returncode == 0 and passed_count is not None and passed_count >= 7
        else "blocked",
        "returncode": completed.returncode,
        "expected_min_passed_count": 7,
        "passed_test_count_observed": passed_count,
        "stdout_byte_count": len(completed.stdout.encode("utf-8")),
        "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        "body_in_receipt": False,
    }


def _original_pytest_engine(repo_root: Path, witness: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_original_pytest_engine` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "status": "pass" if witness.get("status") == "pass" else "blocked",
        "engine_id": "oracle_original_pytest_witness",
        "original_witness": dict(witness),
        "claim_ceiling": "Original focused pytest witness only; stdout and stderr bodies stay out of receipts.",
    }


def _missing_subject_run_dir_negative(modules: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_missing_subject_run_dir_negative` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    observed = _exception_negative_observation(
        lambda: modules["subject_index"].run({"runtime": {}}),
        expected_fragment="oracle_subject_run_dir is required",
    )
    observed.update(
        {
            "case_id": "missing_subject_run_dir",
            "subject_run_dir_required": observed["status"] == "blocked",
        }
    )
    return observed


def _missing_artifact_id_negative(modules: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_missing_artifact_id_negative` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_missing_artifact_") as tmp:
        subject_run = Path(tmp) / "subject"
        subject_run.mkdir(parents=True)
        observed = _exception_negative_observation(
            lambda: modules["subject_snapshot"].run(
                {"runtime": {"oracle_subject_run_dir": str(subject_run)}}
            ),
            expected_fragment="artifact_id is required",
        )
    observed.update(
        {
            "case_id": "missing_artifact_id",
            "artifact_id_required": observed["status"] == "blocked",
        }
    )
    return observed


def _macro_truth_run_missing_negative(modules: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_macro_truth_run_missing_negative` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_truth_run_missing_") as tmp:
        subject_run = Path(tmp) / "subject"
        subject_run.mkdir(parents=True)
        observed = _exception_negative_observation(
            lambda: modules["truth_diff_macro"].run(
                {"runtime": {"oracle_subject_run_dir": str(subject_run)}}
            ),
            expected_fragment="oracle_truth_run_dir is required",
        )
    observed.update(
        {
            "case_id": "macro_truth_run_missing",
            "truth_run_dir_required": observed["status"] == "blocked",
        }
    )
    return observed


def _quartet_run_missing_excluded_negative(
    modules: Mapping[str, Any],
    input_path: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_quartet_run_missing_excluded_negative` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_quartet_missing_") as tmp:
        subject_run = Path(tmp) / "subject"
        truth_run = Path(tmp) / "truth"
        subject_run.mkdir(parents=True)
        truth_run.mkdir(parents=True)
        plan = modules["run_quartet"].build_quartet_repair_plan(subject_run, truth_run)
    readiness = plan.get("readiness") if isinstance(plan, Mapping) else {}
    repair_actions = plan.get("repair_actions") if isinstance(plan, Mapping) else []
    run_missing_actions = (
        [
            row
            for row in repair_actions
            if isinstance(row, Mapping) and row.get("action_kind") == "run_oracle_node"
        ]
        if isinstance(repair_actions, list)
        else []
    )
    manifest_exclusion_present = _manifest_excludes_run_missing(input_path)
    observed = (
        isinstance(readiness, Mapping)
        and readiness.get("status") == "BLOCKED"
        and readiness.get("deepest_missing_target") == "oracle_cp2_emitter"
        and len(run_missing_actions) >= 1
        and manifest_exclusion_present
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "quartet_run_missing_excluded",
        "readiness_status": readiness.get("status") if isinstance(readiness, Mapping) else None,
        "deepest_missing_target": (
            readiness.get("deepest_missing_target")
            if isinstance(readiness, Mapping)
            else None
        ),
        "run_missing_action_count": len(run_missing_actions),
        "manifest_exclusion_present": manifest_exclusion_present,
        "run_missing_quartet_excluded": observed,
        "godmode_engine_invoked": False,
        "body_in_receipt": False,
    }


def _original_pytest_witness_required_negative() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_original_pytest_witness_required_negative` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with tempfile.TemporaryDirectory(prefix="batch7_oracle_missing_witness_repo_") as tmp:
        witness = _run_original_pytest_witness(Path(tmp))
    observed = witness.get("status") != "pass"
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "original_pytest_witness_required",
        "witness_status": witness.get("status"),
        "witness_error_code": witness.get("error_code"),
        "original_pytest_witness_required": observed,
        "body_in_receipt": False,
    }


@lru_cache(maxsize=16)
def _semantic_runtime_exercises(input_ref: str) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_runtime_exercises` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_ref)
    public_root = public_root_for_path(input_path)
    modules = _load_oracle_modules(_repo_root(public_root))
    return {
        "negative_exercises": {
            "missing_subject_run_dir": _missing_subject_run_dir_negative(modules),
            "missing_artifact_id": _missing_artifact_id_negative(modules),
            "macro_truth_run_missing": _macro_truth_run_missing_negative(modules),
            "quartet_run_missing_excluded": _quartet_run_missing_excluded_negative(
                modules,
                input_path,
            ),
            "original_pytest_witness_required": _original_pytest_witness_required_negative(),
        },
        "body_in_receipt": False,
    }


def _negative_exercise(runtime: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_exercise` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cases = (
        runtime.get("negative_exercises")
        if isinstance(runtime.get("negative_exercises"), Mapping)
        else {}
    )
    case = cases.get(case_id)
    return case if isinstance(case, Mapping) else {}


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_observed_negative_case` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    exercise = _negative_exercise(runtime, case_id)
    if case_id == "missing_subject_run_dir":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("subject_run_dir_required") is True
        )
    if case_id == "missing_artifact_id":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("artifact_id_required") is True
        )
    if case_id == "macro_truth_run_missing":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("truth_run_dir_required") is True
        )
    if case_id == "quartet_run_missing_excluded":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("run_missing_quartet_excluded") is True
            and exercise.get("godmode_engine_invoked") is False
        )
    if case_id == "original_pytest_witness_required":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("original_pytest_witness_required") is True
        )
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    expected_code = NEGATIVE_CASE_CODES.get(case_id, "")
    observed = _observed_negative_case(
        case_id,
        _semantic_runtime_exercises(str(Path(input_dir))),
    )
    return {
        "status": "blocked" if observed else "pass",
        "error_codes": [expected_code] if observed and expected_code else [],
        "body_in_receipt": False,
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    del input_path
    repo_root = _repo_root(public_root)
    pytest_witness = _run_original_pytest_witness(repo_root)
    engines = [
        _subject_index_engine(repo_root),
        _subject_snapshot_engine(repo_root),
        _truth_diff_macro_engine(repo_root),
        _quartet_repair_engine(repo_root),
        _original_pytest_engine(repo_root, pytest_witness),
    ]
    findings: list[dict[str, Any]] = []
    if source_manifest.get("status") != "pass":
        findings.append(
            finding(
                "BATCH7_ORACLE_SOURCE_MANIFEST_BLOCKED",
                "Oracle sibling source manifest must validate before exercise can pass.",
                observed=source_manifest.get("status"),
            )
        )
    if pytest_witness.get("status") != "pass":
        findings.append(
            finding(
                "BATCH7_ORACLE_ORIGINAL_PYTEST_WITNESS_REQUIRED",
                "Oracle sibling capsule requires the focused original pytest witness to pass.",
                observed=pytest_witness.get("returncode"),
            )
        )
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH7_ORACLE_ENGINE_BLOCKED",
                    "Oracle sibling capsule engine did not satisfy its public contract.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(engines),
        "engine_ids": [str(row["engine_id"]) for row in engines],
        "engines": engines,
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "original_pytest_witness": pytest_witness,
        "run_missing_quartet_excluded": True,
        "body_in_receipt": False,
        "findings": findings,
        "error_codes": [
            str(row["error_code"]) for row in findings if row.get("error_code")
        ],
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch7_oracle_sibling_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch7_oracle_sibling_bundle` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
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
    card["original_pytest_witness_status"] = exercise.get(
        "original_pytest_witness", {}
    ).get("status")
    card["run_missing_quartet_excluded"] = exercise.get("run_missing_quartet_excluded")
    card["copied_macro_source_module_count"] = exercise.get(
        "copied_macro_source_module_count"
    )
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "release_authorized": ceiling.get("release_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "model_dispatch": ceiling.get("model_dispatch"),
        "browser_or_wallet_access": ceiling.get("browser_or_wallet_access"),
        "oracle_run_missing_authorized": ceiling.get("oracle_run_missing_authorized"),
        "godmode_engine_invocation_authorized": ceiling.get(
            "godmode_engine_invocation_authorized"
        ),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "operator_thread_authority": ceiling.get("operator_thread_authority"),
        "semantic_truth_authority": ceiling.get("semantic_truth_authority"),
        "test_completeness_proof": ceiling.get("test_completeness_proof"),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "original_pytest_stdout_in_receipt": False,
        "original_pytest_stderr_in_receipt": False,
        "source_bodies_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.batch7_oracle_sibling_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle", "run-batch7-oracle-sibling-bundle"):
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
            if args.action in {"validate-bundle", "run-batch7-oracle-sibling-bundle"}
            else "fixture_input"
        ),
        evaluator=_evaluate,
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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
