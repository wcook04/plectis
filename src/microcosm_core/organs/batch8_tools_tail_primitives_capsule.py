"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch8_tools_tail_primitives_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, PROBE_MANIFEST_NAME, EXPECTED_MECHANISMS, EXPECTED_MODULE_IDS, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, RUNTIME_EXERCISES, evaluate_negative_case, evaluate, run, run_batch8_bundle, result_card, main
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


ORGAN_ID = "batch8_tools_tail_primitives_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

EXPECTED_MECHANISMS: tuple[str, ...] = (
    "observer_set_diff_kernel",
    "version_committer_json_patch_vm",
    "ledger_id_identity_hash_engine",
    "shadow_envelope_dsl_parser_coverage",
)

EXPECTED_MODULE_IDS: tuple[str, ...] = (
    "observer_diff_kernel",
    "version_committer_json_patch_vm",
    "ledger_id_identity_hash_engine",
    "shadow_envelope_dsl_parser_coverage",
)

EXPECTED_NEGATIVE_CASES = {
    "observer_diff_malformed_key_skipped": (
        "BATCH8_OBSERVER_DIFF_MALFORMED_ROW_SKIPPED",
    ),
    "version_committer_scalar_traversal_refused": (
        "BATCH8_VERSION_COMMITTER_SCALAR_TRAVERSAL_REFUSED",
    ),
    "ledger_id_missing_identity_refused": (
        "BATCH8_LEDGER_ID_MISSING_IDENTITY_REFUSED",
    ),
    "shadow_dsl_malformed_tuple_coverage_gap": (
        "BATCH8_SHADOW_DSL_MALFORMED_TUPLE_COVERAGE_GAP",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch8_tools_tail_public_substrate_capsule_not_live_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "standard_authority": "public_batch8_tools_tail_source_open_capsule_and_source_body_digest_contract_only",
    "godmode_run_missing_authorized": False,
    "provider_dispatch": False,
    "live_oracle_execution": False,
    "repo_mutation_authorized": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Batch 8 tools-tail capsule validates exact copied non-secret macro "
    "source bodies and public synthetic exercises for deterministic set diffs, "
    "JSON patch interpretation, stable ledger-id hashing, shadow envelope "
    "parse coverage. It is not oracle truth, not live bridge or GodMode "
    "execution, not repository mutation authority, not provider dispatch, not "
    "publication authority, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/lib/observer_diff.py": (
        "class EvidenceDiffResult",
        "def diff_evidence(",
        "def diff_predictions(",
    ),
    "tools/refinement/version_committer.py": (
        "def _apply_op(",
        "def _atomic_write(",
        "class VersionCommitter",
    ),
    "tools/diff/id_ledger.py": (
        "_LANE_ALIASES",
        "def normalize_lane(",
        "def generate_ledger_id(",
    ),
    "tools/shadow/shadow.py": (
        "OPERATOR_TOKENS",
        "def _parse_miner_text(",
        "def run(",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 8 Tools-Tail Primitives Capsule",
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
    - Teleology: Implements `_load_json` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_manifest_payload` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_rows` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_target_path` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    return public_root / str(row.get("path") or "")


@contextmanager
def _temporary_sys_path(paths: list[Path]) -> Iterator[None]:
    """
    [ACTION]
    - Teleology: Implements `_temporary_sys_path` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_modules_root` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_load_copied_module` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row = rows[module_id]
    target = _target_path(row, public_root=public_root)
    module_name = f"_batch8_tools_tail_{module_id}"
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise ImportError(module_id)
    module = importlib.util.module_from_spec(spec)
    with _temporary_sys_path([_source_modules_root(target), public_root.parent]):
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    return module


def _mechanism_status(
    mechanism: Mapping[str, Any],
    *,
    rows: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_mechanism_status` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    module_ids = [
        str(item)
        for item in mechanism.get("source_module_ids", [])
        if isinstance(item, str) and item
    ]
    missing_modules = [module_id for module_id in module_ids if module_id not in rows]
    missing_anchors: list[str] = []
    for module_id in module_ids:
        row = rows.get(module_id)
        if not row:
            continue
        target = _target_path(row, public_root=public_root)
        text = target.read_text(encoding="utf-8") if target.is_file() else ""
        for anchor in row.get("required_anchors", []):
            if isinstance(anchor, str) and anchor and anchor not in text:
                missing_anchors.append(f"{module_id}:{anchor}")
    return {
        "mechanism_id": str(mechanism.get("mechanism_id") or ""),
        "status": "pass" if not missing_modules and not missing_anchors else "blocked",
        "source_module_ids": module_ids,
        "claim_ceiling": mechanism.get("claim_ceiling"),
        "public_exercise": mechanism.get("public_exercise"),
        "negative_case": mechanism.get("negative_case"),
        "missing_modules": missing_modules,
        "missing_anchors": missing_anchors,
        "body_in_receipt": False,
    }


def _exercise_observer_diff(rows: Mapping[str, Mapping[str, Any]], public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exercise_observer_diff` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mod = _load_copied_module("observer_diff_kernel", rows, public_root)
    evidence = mod.diff_evidence(
        [
            {"ledger_id": "E1", "source": "lab"},
            {"bad_key": "skipped"},
            {"ledger_id": "E3", "source": "lab"},
        ],
        [
            {"ledger_id": "E1", "source": "oracle"},
            {"ledger_id": "E2", "source": "oracle"},
        ],
    ).to_json_dict()
    predictions = mod.diff_predictions(
        [
            {"target_id": "A", "direction": "up"},
            {"target_id": "B", "direction": "down"},
            {"bad_key": "skipped"},
        ],
        [
            {"target_id": "A", "direction": "up"},
            {"target_id": "B", "direction": "up"},
            {"target_id": "C", "direction": "down"},
        ],
    ).to_json_dict()
    malformed_skipped = "skipped" not in json.dumps(evidence, sort_keys=True)
    status = (
        evidence["missed_ledger_ids"] == ["E2"]
        and evidence["extra_ledger_ids"] == ["E3"]
        and evidence["overlap_ledger_ids"] == ["E1"]
        and [row["target_id"] for row in predictions["matching"]] == ["A"]
        and [row["target_id"] for row in predictions["divergent"]] == ["B"]
        and [row["target_id"] for row in predictions["missing_targets"]] == ["C"]
        and malformed_skipped
    )
    return {
        "exercise_id": "observer_set_diff_kernel",
        "status": "pass" if status else "blocked",
        "evidence_diff": evidence,
        "prediction_diff": predictions,
        "malformed_rows_skipped": malformed_skipped,
        "source_execution_relation": "copied_source_body_executed",
    }


def _exercise_version_committer(rows: Mapping[str, Mapping[str, Any]], public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exercise_version_committer` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mod = _load_copied_module("version_committer_json_patch_vm", rows, public_root)
    data: dict[str, Any] = {"profile": {"old": True}}
    applied = [
        mod._apply_op(data, "set", "/profile/name", "Microcosm"),
        mod._apply_op(data, "merge", "/profile/meta", {"kind": "fixture"}),
        mod._apply_op(data, "append", "/events", {"id": "E1"}),
        mod._apply_op(data, "set", "/profile/old", None),
    ]
    refused = False
    try:
        mod._apply_op({"profile": "scalar"}, "set", "/profile/name", "bad")
    except mod.VersionCommitterError:
        refused = True
    status = (
        data == {
            "profile": {"name": "Microcosm", "meta": {"kind": "fixture"}},
            "events": [{"id": "E1"}],
        }
        and all(item[0] is True for item in applied)
        and refused
    )
    return {
        "exercise_id": "version_committer_json_patch_vm",
        "status": "pass" if status else "blocked",
        "patched_document": data,
        "applied_reasons": [reason for _, reason in applied],
        "scalar_traversal_refused": refused,
        "source_execution_relation": "copied_source_body_executed",
    }


def _exercise_ledger_id(rows: Mapping[str, Mapping[str, Any]], public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exercise_ledger_id` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mod = _load_copied_module("ledger_id_identity_hash_engine", rows, public_root)
    record = {"slug": "public-fixture-market"}
    first = mod.generate_ledger_id("poly", record)
    second = mod.generate_ledger_id("POLYMARKET", record)
    unknown = mod.generate_ledger_id("new_lane", {"slug": "fixture"})
    refused = False
    try:
        mod.generate_ledger_id("STOCK", {"name": "missing ticker"})
    except ValueError:
        refused = True
    status = (
        mod.normalize_lane("poly") == "POLYMARKET"
        and first == second
        and first.startswith("P_")
        and unknown.startswith("X_")
        and refused
    )
    return {
        "exercise_id": "ledger_id_identity_hash_engine",
        "status": "pass" if status else "blocked",
        "poly_id": first,
        "repeat_id": second,
        "unknown_lane_id": unknown,
        "missing_identity_refused": refused,
        "source_execution_relation": "copied_source_body_executed",
    }


def _write_artifact(path: Path, node_id: str, data: Any) -> None:
    """
    [ACTION]
    - Teleology: Implements `_write_artifact` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"id": node_id, "data": data}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _exercise_shadow(rows: Mapping[str, Mapping[str, Any]], public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_exercise_shadow` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mod = _load_copied_module("shadow_envelope_dsl_parser_coverage", rows, public_root)
    with tempfile.TemporaryDirectory(prefix="microcosm-batch8-shadow-") as tmp:
        run_dir = Path(tmp)
        artifacts = run_dir / "artifacts"
        miner_text = "{ACME, momentum, public fixture}\n{bad, tuple}\n"
        for node_id in mod.MINER_NODE_TO_LANE:
            _write_artifact(artifacts / f"{node_id}.json", node_id, miner_text)
        spine_text = (
            "[H:public_fixture] CONFIRMED\n"
            "{ACME} <<>> [H:public_fixture] --> {ACME_UP}\n"
        )
        _write_artifact(artifacts / f"{mod.SPINE_NODE_ID}.json", mod.SPINE_NODE_ID, spine_text)
        for node_id in mod.PREDICT_NODE_TO_LANE:
            _write_artifact(
                artifacts / f"{node_id}.json",
                node_id,
                {"predictions_t": [{"target_id": "ACME", "direction": "up"}]},
            )
        result = mod.run({"config": {"strict": True, "emit_examples": True}}, str(run_dir))
    stats = result["data"]["parse_stats"]
    malformed_tuple_count = stats["miners"]["failures_by_type"].get("comma_arity", 0)
    status = (
        result["metadata"]["hard_failure"] is False
        and stats["miners"]["parsed_ok"] >= len(mod.MINER_NODE_TO_LANE)
        and stats["spine"]["parsed_ok"] >= 1
        and stats["predictions"]["parsed_ok"] >= 1
        and malformed_tuple_count >= 1
    )
    return {
        "exercise_id": "shadow_envelope_dsl_parser_coverage",
        "status": "pass" if status else "blocked",
        "hard_failure": result["metadata"]["hard_failure"],
        "miner_parsed_ok": stats["miners"]["parsed_ok"],
        "spine_parsed_ok": stats["spine"]["parsed_ok"],
        "prediction_parsed_ok": stats["predictions"]["parsed_ok"],
        "malformed_tuple_coverage_gap_count": malformed_tuple_count,
        "source_execution_relation": "copied_source_body_executed",
    }


RUNTIME_EXERCISES = {
    "observer_set_diff_kernel": _exercise_observer_diff,
    "version_committer_json_patch_vm": _exercise_version_committer,
    "ledger_id_identity_hash_engine": _exercise_ledger_id,
    "shadow_envelope_dsl_parser_coverage": _exercise_shadow,
}


def _semantic_negative_result(case_id: str, error_codes: tuple[str, ...]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_negative_result` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": list(error_codes),
        "body_in_receipt": False,
    }


def _semantic_negative_not_rejected(case_id: str, observed: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_negative_not_rejected` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "pass",
        "error_codes": [],
        "observed": observed,
        "body_in_receipt": False,
    }


def _semantic_negative_error(case_id: str, exc: Exception) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_negative_error` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [f"BATCH8_TOOLS_TAIL_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"],
        "body_in_receipt": False,
    }


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = public_root_for_path(input_dir)
    rows = _source_rows(input_dir, public_root)
    try:
        if case_id == "observer_diff_malformed_key_skipped":
            mod = _load_copied_module("observer_diff_kernel", rows, public_root)
            result = mod.diff_evidence(
                [{"bad_key": "missing-ledger-id"}],
                [{"ledger_id": "E1", "source": "fixture"}],
            ).to_json_dict()
            rejected = (
                result["missed_ledger_ids"] == ["E1"]
                and result["extra_ledger_ids"] == []
                and result["overlap_ledger_ids"] == []
            )
            if rejected:
                return _semantic_negative_result(case_id, expected_codes)
            return _semantic_negative_not_rejected(case_id, result)

        if case_id == "version_committer_scalar_traversal_refused":
            mod = _load_copied_module("version_committer_json_patch_vm", rows, public_root)
            try:
                mod._apply_op({"profile": "scalar"}, "set", "/profile/name", "bad")
            except mod.VersionCommitterError:
                return _semantic_negative_result(case_id, expected_codes)
            return _semantic_negative_not_rejected(case_id, "scalar traversal accepted")

        if case_id == "ledger_id_missing_identity_refused":
            mod = _load_copied_module("ledger_id_identity_hash_engine", rows, public_root)
            try:
                mod.generate_ledger_id("STOCK", {"name": "missing ticker"})
            except ValueError:
                return _semantic_negative_result(case_id, expected_codes)
            return _semantic_negative_not_rejected(case_id, "missing identity accepted")

        if case_id == "shadow_dsl_malformed_tuple_coverage_gap":
            result = _exercise_shadow(rows, public_root)
            if result.get("malformed_tuple_coverage_gap_count", 0) >= 1:
                return _semantic_negative_result(case_id, expected_codes)
            return _semantic_negative_not_rejected(case_id, result)
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)

    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [f"BATCH8_TOOLS_TAIL_UNKNOWN_NEGATIVE_CASE_{case_id.upper()}"],
        "body_in_receipt": False,
    }


def evaluate(input_dir: Path, public_root: Path, _source_manifest: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    manifest = _load_json(input_dir / PROBE_MANIFEST_NAME)
    mechanisms = manifest.get("mechanisms")
    if not isinstance(mechanisms, list):
        mechanisms = []
        findings.append(
            finding(
                "BATCH8_TOOLS_TAIL_PROBE_MANIFEST_INVALID",
                "Probe manifest must include mechanisms list.",
                subject_id=PROBE_MANIFEST_NAME,
            )
        )
    rows = _source_rows(input_dir, public_root)
    mechanism_rows = [
        _mechanism_status(row, rows=rows, public_root=public_root)
        for row in mechanisms
        if isinstance(row, Mapping)
    ]
    runtime_exercises: dict[str, dict[str, Any]] = {}
    for exercise_id, runner in RUNTIME_EXERCISES.items():
        try:
            runtime_exercises[exercise_id] = runner(rows, public_root)
        except Exception as exc:  # pragma: no cover - receipt captures exact class.
            runtime_exercises[exercise_id] = {
                "exercise_id": exercise_id,
                "status": "blocked",
                "exception_type": type(exc).__name__,
                "source_execution_relation": "copied_source_body_execution_failed",
            }
    missing_mechanisms = [
        mechanism_id
        for mechanism_id in EXPECTED_MECHANISMS
        if mechanism_id not in {row.get("mechanism_id") for row in mechanism_rows}
    ]
    if missing_mechanisms:
        findings.append(
            finding(
                "BATCH8_TOOLS_TAIL_MECHANISM_MISSING",
                "Probe manifest is missing expected Batch-8 mechanisms.",
                expected=list(EXPECTED_MECHANISMS),
                observed=[row.get("mechanism_id") for row in mechanism_rows],
            )
        )
    failed = [
        exercise_id
        for exercise_id, result in runtime_exercises.items()
        if result.get("status") != "pass"
    ]
    if failed:
        findings.append(
            finding(
                "BATCH8_TOOLS_TAIL_RUNTIME_EXERCISE_FAILED",
                "One or more copied source-body exercises failed.",
                observed=failed,
            )
        )
    blocked_mechanisms = [
        row.get("mechanism_id") for row in mechanism_rows if row.get("status") != "pass"
    ]
    if blocked_mechanisms:
        findings.append(
            finding(
                "BATCH8_TOOLS_TAIL_MECHANISM_ANCHOR_BLOCKED",
                "One or more mechanism rows is missing source modules or anchors.",
                observed=blocked_mechanisms,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "mechanism_count": len(mechanism_rows),
        "mechanisms": mechanism_rows,
        "runtime_exercises": runtime_exercises,
        "copied_macro_source_module_count": len(rows),
        "expected_module_ids": list(EXPECTED_MODULE_IDS),
        "error_codes": sorted(
            {
                code
                for codes in EXPECTED_NEGATIVE_CASES.values()
                for code in codes
            }
        ),
        "findings": findings,
        "body_in_receipt": False,
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
    - Teleology: Implements `run` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch8_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch8_bundle` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    card = card_for_result(SPEC, result)
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
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "standard_authority": ceiling.get("standard_authority"),
        "godmode_run_missing_authorized": ceiling.get(
            "godmode_run_missing_authorized"
        ),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "live_oracle_execution": ceiling.get("live_oracle_execution"),
        "repo_mutation_authorized": ceiling.get("repo_mutation_authorized"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "release_authorized": ceiling.get("release_authorized"),
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
    - Teleology: Implements `main` for `microcosm_core.organs.batch8_tools_tail_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
        evaluator=evaluate,
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
