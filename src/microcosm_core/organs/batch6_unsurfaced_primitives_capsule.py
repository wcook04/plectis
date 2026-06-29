"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, PROBE_MANIFEST_NAME, EXPECTED_MECHANISMS, EXPECTED_MODULE_IDS, EXPECTED_NEGATIVE_CASES, NEGATIVE_CASE_MECHANISMS, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch6_bundle, result_card, main
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
import importlib
import importlib.util
import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch6_unsurfaced_primitives_capsule"
FIXTURE_ID = "first_wave.batch6_unsurfaced_primitives_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch6_unsurfaced_primitives_capsule"

RESULT_NAME = "batch6_unsurfaced_primitives_capsule_result.json"
BOARD_NAME = "batch6_unsurfaced_primitives_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch6_unsurfaced_primitives_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch6_unsurfaced_primitives_capsule_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "batch6_unsurfaced_primitives_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch6_unsurfaced_primitives_capsule_bundle"
PROBE_MANIFEST_NAME = "batch6_probe_manifest.json"

EXPECTED_MECHANISMS: tuple[str, ...] = (
    "raw_seed_keyphrase_engine",
    "schema_loose_distillation_index",
    "operator_handoff_linkage",
    "observed_turn_window_merge",
    "market_situation_graph",
    "finance_numeric_assurance",
    "fail_closed_status_judge",
    "idea_microcosm_concurrency_guard",
    "metabolism_market_clock",
    "population_lane_provider_recovery",
    "demo_take_temporal_join",
)

EXPECTED_MODULE_IDS: tuple[str, ...] = (
    "demo_take_capture",
    "idea_microcosm_package_init_dependency",
    "idea_microcosm_atlas_navigation_specimen_dependency",
    "idea_microcosm_concurrency_guard",
    "idea_microcosm_navigation_dependency",
    "idea_microcosm_release_candidates_dependency",
    "idea_microcosm_release_root_compiler_dependency",
    "idea_microcosm_validators",
    "system_package_init_dependency",
    "feed_quality_dependency",
    "finance_numeric_assurance",
    "market_feed_run_evidence_dependency",
    "market_fusion_readiness_dependency",
    "market_situation_graph",
    "metabolism_market_clock",
    "metabolism_store_dependency",
    "population_lane_provider_recovery",
    "quant_presentation_mart_dependency",
    "raw_seed_keyphrase",
    "raw_seed_smart_stoplist",
    "raw_seed_spelling",
    "system_utils_dependency",
    "schema_loose_distillation_index",
    "operator_handoff_linkage",
    "prompt_shelf_fingerprints",
    "operator_thread_memory",
)

EXPECTED_NEGATIVE_CASES = {
    "stopword_only_keyphrase_empty": (
        "BATCH6_KEYPHRASE_STOPWORD_ONLY_EMPTY",
    ),
    "schema_loose_voice_conflation": (
        "BATCH6_SCHEMA_LOOSE_ROLE_CONFLATION_REJECTED",
    ),
    "handoff_unrelated_below_floor": (
        "BATCH6_HANDOFF_UNRELATED_BELOW_FLOOR",
    ),
    "observed_turn_duplicate_rerender": (
        "BATCH6_OBSERVED_TURN_RERENDER_NOT_DUPLICATED",
    ),
    "market_situation_missing_counterevidence": (
        "BATCH6_MARKET_SITUATION_COUNTEREVIDENCE_REQUIRED",
    ),
    "finance_unit_scale_mismatch": (
        "BATCH6_FINANCE_UNIT_SCALE_MISMATCH_BLOCKED",
    ),
    "status_policy_poisoned": (
        "BATCH6_STATUS_POLICY_FAILS_CLOSED",
    ),
    "concurrency_parent_child_conflict": (
        "BATCH6_CONCURRENCY_PARENT_CHILD_CONFLICT",
    ),
    "market_clock_duplicate_fire_suppressed": (
        "BATCH6_MARKET_CLOCK_DUPLICATE_FIRE_SUPPRESSED",
    ),
    "provider_timeout_scope_narrow": (
        "BATCH6_PROVIDER_TIMEOUT_SCOPE_NARROW",
    ),
    "demo_take_pause_remap": (
        "BATCH6_DEMO_TAKE_PAUSE_REMAP_CORRECTED",
    ),
}

NEGATIVE_CASE_MECHANISMS: dict[str, tuple[str, str]] = {
    "stopword_only_keyphrase_empty": (
        "raw_seed_keyphrase_engine",
        "BATCH6_KEYPHRASE_STOPWORD_ONLY_EMPTY",
    ),
    "schema_loose_voice_conflation": (
        "schema_loose_distillation_index",
        "BATCH6_SCHEMA_LOOSE_ROLE_CONFLATION_REJECTED",
    ),
    "handoff_unrelated_below_floor": (
        "operator_handoff_linkage",
        "BATCH6_HANDOFF_UNRELATED_BELOW_FLOOR",
    ),
    "observed_turn_duplicate_rerender": (
        "observed_turn_window_merge",
        "BATCH6_OBSERVED_TURN_RERENDER_NOT_DUPLICATED",
    ),
    "market_situation_missing_counterevidence": (
        "market_situation_graph",
        "BATCH6_MARKET_SITUATION_COUNTEREVIDENCE_REQUIRED",
    ),
    "finance_unit_scale_mismatch": (
        "finance_numeric_assurance",
        "BATCH6_FINANCE_UNIT_SCALE_MISMATCH_BLOCKED",
    ),
    "status_policy_poisoned": (
        "fail_closed_status_judge",
        "BATCH6_STATUS_POLICY_FAILS_CLOSED",
    ),
    "concurrency_parent_child_conflict": (
        "idea_microcosm_concurrency_guard",
        "BATCH6_CONCURRENCY_PARENT_CHILD_CONFLICT",
    ),
    "market_clock_duplicate_fire_suppressed": (
        "metabolism_market_clock",
        "BATCH6_MARKET_CLOCK_DUPLICATE_FIRE_SUPPRESSED",
    ),
    "provider_timeout_scope_narrow": (
        "population_lane_provider_recovery",
        "BATCH6_PROVIDER_TIMEOUT_SCOPE_NARROW",
    ),
    "demo_take_pause_remap": (
        "demo_take_temporal_join",
        "BATCH6_DEMO_TAKE_PAUSE_REMAP_CORRECTED",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch6_public_substrate_capsule_not_live_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "launch_authorized": False,
    "model_dispatch": False,
    "provider_dispatch": False,
    "runtime_execution": False,
    "live_operator_transcript_export_authorized": False,
    "live_provider_browser_state_export_authorized": False,
    "live_market_data_fetch_authorized": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Batch 6 validates exact copied non-secret macro source bodies and public "
    "synthetic exercises for keyphrase scoring, schema-loose distillation, "
    "operator handoff scoring, observed-turn merging, market situation graphs, "
    "finance numeric assurance, fail-closed status judgment, clone-local "
    "concurrency, market-clock scheduling, provider-recovery scoping, and "
    "demo-take temporal remapping. It is not live operator memory, not raw "
    "prompt-shelf content, not live market data, not provider/browser state, "
    "not publication authority, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    "apps/demo-take-console/support/demo_take_capture.py": (
        "def video_t_seconds(",
        "pause_events",
        "def build_speech_blocks(",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/__init__.py": (),
    "self-indexing-cognitive-substrate/src/idea_microcosm/atlas_navigation_specimen.py": (
        "EXPECTED_BANDS",
        "def build_atlas_navigation_specimen",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/concurrency_guard.py": (
        "def _paths_overlap(",
        "def git_landing_plan(",
        "SCHEMA_VERSION",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/navigation.py": (
        "ROOT_ENTRY_CONTRACT",
        "def build_microcosm_implementation_atlas",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/release_candidates.py": (
        "ALLOWED_SPECIMEN_STATUSES",
        "def candidate_shape_failures",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/release_root_compiler.py": (
        "ROOT_CONTRACT_PATH",
        "def compile_release_root",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/validators.py": (
        "def judge_status_request(",
        "def policy_wellformedness_failures(",
        "malformed_policy_blocks_judgment",
    ),
    "system/__init__.py": (
        "system",
    ),
    "system/lib/feed_quality.py": (
        "def artifact_quality_from_mapping",
        "def normalize_quality_tone",
    ),
    "system/lib/finance_numeric_assurance.py": (
        "def build_finance_numeric_assurance(",
        "stockgrid_flow_unit_scale_mismatch",
        "probability_representation",
    ),
    "system/lib/market_feed_run_evidence.py": (
        "SCHEMA_VERSION",
        "DEFAULT_LATEST_FILENAME",
    ),
    "system/lib/market_fusion_readiness.py": (
        "SCHEMA_VERSION",
        "def build_readiness_gate",
    ),
    "system/lib/market_situation_graph.py": (
        "def build_market_situation_graph(",
        "def validate_market_situation_graph(",
        "counterevidence_edges",
    ),
    "system/lib/metabolism_market_clock.py": (
        "def due_fire_points(",
        "MARKET_HOURS_HOURLY_FIRE_POINTS",
        "def fire_key(",
    ),
    "system/lib/metabolism_store.py": (
        "SCHEMA_VERSION",
        "def get_setting",
    ),
    "system/lib/population_lane_provider_recovery.py": (
        "def transport_suppression_scope(",
        "provider_model",
        "blocked_duplicate",
    ),
    "system/lib/quant_presentation_mart.py": (
        "SCHEMA_VERSION",
        "DEFAULT_LATEST_FILENAME",
    ),
    "system/lib/raw_seed_keyphrase.py": (
        "def merged_stopwords(",
        "def rake_ranked_phrases(",
        "def salvage_tokens(",
    ),
    "system/lib/raw_seed_smart_stoplist.txt": (
        "about",
        "through",
    ),
    "system/lib/raw_seed_spelling.py": (
        "SPELLING_NORMALIZATION_VERSION",
        "def build_corpus_hint_normalizer(",
    ),
    "system/lib/utils.py": (
        "def resolve_runs_dir",
    ),
    "tools/meta/observability/operator_handoff_linkage.py": (
        "class TypeBCapture",
        "class TypeAUserInput",
        "def score_pair(",
    ),
    "tools/meta/observability/operator_thread_memory.py": (
        "def merge_observed_turn_window(",
        "def _suffix_prefix_overlap(",
        "def _observed_updates_streaming_tail(",
    ),
    "tools/meta/observability/prompt_shelf_fingerprints.py": (
        "def _normalize(",
        "def _tokenize(",
        "def _anchor_position(",
    ),
    "tools/meta/observability/prompt_shelf_schema_loose_distillation_index.py": (
        "def distill_diagnostic(",
        "source_role",
        "pair_combined",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 6 Unsurfaced Primitives Capsule",
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
        "microcosm-substrate/examples/batch6_unsurfaced_primitives_capsule/"
        "exported_batch6_unsurfaced_primitives_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _finding(code: str, message: str, *, subject_id: str | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_finding` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = {"error_code": code, "message": message, "body_in_receipt": False}
    if subject_id:
        payload["subject_id"] = subject_id
    return payload


def _load_manifest(input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_load_manifest` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    path = input_path / PROBE_MANIFEST_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [_finding("BATCH6_PROBE_MANIFEST_INVALID", type(exc).__name__, subject_id=path.name)]
    if not isinstance(payload, dict):
        return {}, [_finding("BATCH6_PROBE_MANIFEST_NOT_OBJECT", "Probe manifest must be an object.")]
    return payload, []


def _original_source_manifest(source_manifest: Mapping[str, Any], *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_original_source_manifest` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_ref = str(source_manifest.get("manifest_ref") or "")
    if not manifest_ref:
        return {}
    path = public_root / manifest_ref
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _module_rows(source_manifest: Mapping[str, Any], *, public_root: Path) -> dict[str, Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_module_rows` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    original = _original_source_manifest(source_manifest, public_root=public_root)
    rows = original.get("modules")
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
    - Teleology: Implements `_target_path` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    path = str(row.get("path") or "")
    return public_root / path


def _target_text(row: Mapping[str, Any], *, public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_target_text` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    path = _target_path(row, public_root=public_root)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _source_modules_root(target_path: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_modules_root` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
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


@contextmanager
def _temporary_sys_path(paths: list[Path]) -> Iterator[None]:
    """
    [ACTION]
    - Teleology: Implements `_temporary_sys_path` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_temporary_import_namespaces` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
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


def _source_module_import_paths(target_path: Path, *, public_root: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_import_paths` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_modules = _source_modules_root(target_path)
    return [
        source_modules,
        source_modules / "self-indexing-cognitive-substrate/src",
        public_root.parent / "self-indexing-cognitive-substrate/src",
        public_root.parent,
    ]


def _load_copied_module(
    module_id: str,
    modules: Mapping[str, Mapping[str, Any]],
    *,
    public_root: Path,
):
    """
    [ACTION]
    - Teleology: Implements `_load_copied_module` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row = modules[module_id]
    target = _target_path(row, public_root=public_root)
    module_name = f"_batch6_copied_{module_id}"
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise ImportError(module_id)
    module = importlib.util.module_from_spec(spec)
    with _temporary_sys_path(_source_module_import_paths(target, public_root=public_root)):
        with _temporary_import_namespaces(("idea_microcosm", "system", "tools")):
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
    return module


def _import_copied_package_module(
    module_name: str,
    module_id: str,
    modules: Mapping[str, Mapping[str, Any]],
    *,
    public_root: Path,
):
    """
    [ACTION]
    - Teleology: Implements `_import_copied_package_module` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target = _target_path(modules[module_id], public_root=public_root)
    with _temporary_sys_path(_source_module_import_paths(target, public_root=public_root)):
        with _temporary_import_namespaces(("idea_microcosm",)):
            return importlib.import_module(module_name)


def _mechanism_status(
    mechanism: Mapping[str, Any],
    *,
    modules: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_mechanism_status` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mechanism_id = str(mechanism.get("mechanism_id") or "")
    module_ids = [
        str(item)
        for item in mechanism.get("source_module_ids", [])
        if isinstance(item, str) and item
    ]
    missing_modules = [module_id for module_id in module_ids if module_id not in modules]
    missing_anchors: list[str] = []
    for module_id in module_ids:
        row = modules.get(module_id)
        if not row:
            continue
        text = _target_text(row, public_root=public_root)
        for anchor in row.get("required_anchors", []):
            if isinstance(anchor, str) and anchor and anchor not in text:
                missing_anchors.append(f"{module_id}:{anchor}")
    return {
        "mechanism_id": mechanism_id,
        "status": "pass" if not missing_modules and not missing_anchors else "blocked",
        "source_module_ids": module_ids,
        "claim_ceiling": mechanism.get("claim_ceiling"),
        "public_exercise": mechanism.get("public_exercise"),
        "negative_case": mechanism.get("negative_case"),
        "missing_modules": missing_modules,
        "missing_anchors": missing_anchors,
        "body_in_receipt": False,
    }


def _utc(value: str) -> datetime:
    """
    [ACTION]
    - Teleology: Implements `_utc` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _run_source_exercise(
    exercise_id: str,
    modules: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_run_source_exercise` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        if exercise_id == "raw_seed_keyphrase_engine":
            mod = _load_copied_module("raw_seed_keyphrase", modules, public_root=public_root)
            stopwords = mod.merged_stopwords({"the", "and"})
            phrases = mod.rake_ranked_phrases(
                "Microcosm imports real substrate receipts and substrate routes.",
                stopwords,
                max_phrases=5,
            )
            stopword_only = mod.rake_ranked_phrases("the and or but", stopwords, max_phrases=5)
            salvage = mod.salvage_tokens(
                "system/lib/raw_seed_keyphrase.py cap_quick_microcosm_0f7ade281d7d"
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass" if phrases and not stopword_only and salvage else "blocked",
                "ranked_phrase_count": len(phrases),
                "stopword_only_phrase_count": len(stopword_only),
                "salvage_token_count": len(salvage),
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "schema_loose_distillation_index":
            mod = _load_copied_module(
                "schema_loose_distillation_index", modules, public_root=public_root
            )
            records = mod.distill_diagnostic(
                {
                    "kind": "prompt_shelf_capture_diagnostic",
                    "slot": "B6",
                    "conversation_id": "public-synthetic",
                    "created_at": "2026-05-31T10:00:00Z",
                    "signature": "public-synthetic",
                    "skipped_reason": "schema_absent",
                    "assistant_text": "lesson: preserve role boundaries\nconfidence: high",
                    "user_text_tail": (
                        "Next action: import system/lib/raw_seed_keyphrase.py. "
                        "Do not conflate assistant text with operator tail. "
                        "cap_quick_microcosm_crown_jewel_controller_batch_6_0f7ade281d7d"
                    ),
                },
                source_path=public_root / "fixtures/public_synthetic_schema_loose.json",
            )
            roles = sorted({str(row.get("source_role")) for row in records})
            return {
                "exercise_id": exercise_id,
                "status": "pass" if {"assistant_text", "user_tail"} <= set(roles) else "blocked",
                "record_count": len(records),
                "source_roles": roles,
                "body_persisted": any(row.get("body_persisted") for row in records),
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "operator_handoff_linkage":
            mod = _load_copied_module("operator_handoff_linkage", modules, public_root=public_root)
            assistant = (
                "Batch 6 should import real macro substrate into Microcosm, "
                "validate copied source modules, and keep private bodies out of receipts."
            )
            typeb = mod.TypeBCapture(
                prompt_run_id="run-public",
                prompt_slot="B6",
                prompt_slug="batch6",
                captured_at="2026-05-31T10:00:00Z",
                conversation_id="conv-public",
                conversation_url="https://example.invalid/c/public",
                assistant_sha256="sha256:public",
                assistant_raw_text=assistant,
                source="capture_diagnostic",
                source_completeness="best_observed_in_group",
            )
            typea = mod.TypeAUserInput(
                surface="codex",
                session_id="session-public",
                session_started_at="2026-05-31T10:00:20Z",
                session_ended_at=None,
                source_path="public/session.jsonl",
                cwd="microcosm-substrate",
                timestamp="2026-05-31T10:00:45Z",
                raw_text=f"Please apply this:\n{assistant}\nAlso wire the CLI.",
            )
            score, evidence, delta = mod.score_pair(typeb, typea)
            unrelated = mod.TypeAUserInput(
                surface="codex",
                session_id="session-public-unrelated",
                session_started_at="2026-05-31T10:05:00Z",
                session_ended_at=None,
                source_path="public/session-unrelated.jsonl",
                cwd="microcosm-substrate",
                timestamp="2026-05-31T10:05:45Z",
                raw_text="Please summarize the weather forecast and do nothing else.",
            )
            unrelated_score, _unrelated_evidence, _unrelated_delta = mod.score_pair(
                typeb,
                unrelated,
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass"
                if score >= 0.8 and evidence.containment and unrelated_score < 0.3
                else "blocked",
                "score": round(float(score), 4),
                "confidence_floor_met": score >= 0.8,
                "unrelated_score": round(float(unrelated_score), 4),
                "unrelated_below_floor": unrelated_score < 0.3,
                "containment": bool(evidence.containment),
                "anchor_match": bool(evidence.anchor_match),
                "operator_delta_position": delta.position,
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "observed_turn_window_merge":
            mod = _load_copied_module("operator_thread_memory", modules, public_root=public_root)
            existing = [
                {"role": "user", "text_sha256": "a", "ordinal": 0, "char_count": 10},
                {"role": "assistant", "text_sha256": "b", "ordinal": 1, "char_count": 20},
            ]
            observed = [
                {"role": "assistant", "text_sha256": "b", "ordinal": 1, "char_count": 20},
                {"role": "user", "text_sha256": "c", "ordinal": 2, "char_count": 12},
            ]
            merged, reason = mod.merge_observed_turn_window(
                existing, observed, now="2026-05-31T10:01:00Z"
            )
            merged_again, duplicate_reason = mod.merge_observed_turn_window(
                merged, [merged[1], merged[2]], now="2026-05-31T10:02:00Z"
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass"
                if reason == "observed_appended_tail" and len(merged_again) == 3
                else "blocked",
                "merge_reason": reason,
                "duplicate_window_reason": duplicate_reason,
                "merged_count": len(merged_again),
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "market_situation_graph":
            mod = _load_copied_module("market_situation_graph", modules, public_root=public_root)
            source_ref = {
                "kind": "fixture_public_synthetic",
                "path": "fixtures/first_wave/batch6_unsurfaced_primitives_capsule/input/batch6_probe_manifest.json",
            }
            mart = {
                "schema_version": "quant_presentation_mart_v0_1",
                "source_fingerprint": "sha256:batch6-public-synthetic",
                "run": {"run_id": "RUN_BATCH6_PUBLIC_SYNTHETIC"},
                "input_watermark": {"source": "public_synthetic"},
                "quality_gates": {"safe_use_level": "artifact_specimen_only"},
                "entity_index": [
                    {
                        "entity_id": "equity:ACME",
                        "entity_type": "equity",
                        "quality": {"category": "Technology"},
                        "source_refs": [source_ref],
                    },
                    {
                        "entity_id": "macro:CPI",
                        "entity_type": "macro",
                        "quality": {"category": "inflation"},
                        "source_refs": [source_ref],
                    },
                ],
                "features": [
                    {
                        "feature_family": "price",
                        "entity_id": "equity:ACME",
                        "metrics": {"chg_5d": 3.5, "vol_20d": 0.31},
                        "source_refs": [source_ref],
                    }
                ],
                "stockgrid_flow_board": [
                    {
                        "ticker": "ACME",
                        "entity_id": "equity:ACME",
                        "sector": "Technology",
                        "flow": 125.0,
                        "flow_usd": 125_000_000.0,
                        "flow_score": 125_000_000.0,
                        "flow_unit": "usd_millions",
                        "source_refs": [source_ref],
                    }
                ],
                "macro_regime_board": [
                    {
                        "bucket": "inflation",
                        "average_z_score": 1.4,
                        "series_count": 1,
                        "vintage_status": "missing",
                        "release_calendar_status": "missing",
                        "interpretation_level": "observation",
                        "top_series": [{"entity_id": "macro:CPI"}],
                    }
                ],
            }
            graph = mod.build_market_situation_graph(
                public_root,
                mart_payload=mart,
                validation_refs=("public_synthetic_batch6",),
            )
            errors = mod.validate_market_situation_graph(graph, strict=True)
            situation_count = len(graph.get("situations") or [])
            has_counterevidence = all(
                bool(row.get("counterevidence_edges"))
                for row in graph.get("situations") or []
                if isinstance(row, Mapping)
            )
            missing_counterevidence_graph = dict(graph)
            missing_counterevidence_graph["situations"] = [
                dict(row)
                for row in graph.get("situations") or []
                if isinstance(row, Mapping)
            ]
            if missing_counterevidence_graph["situations"]:
                missing_counterevidence_graph["situations"][0][
                    "counterevidence_edges"
                ] = []
            missing_counterevidence_errors = mod.validate_market_situation_graph(
                missing_counterevidence_graph,
                strict=True,
            )
            safe = all(
                ((row.get("thesis") or {}).get("not_investment_advice") is True)
                for row in graph.get("situations") or []
                if isinstance(row, Mapping)
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass" if not errors and situation_count >= 2 and has_counterevidence and safe else "blocked",
                "situation_count": situation_count,
                "edge_count": len(graph.get("edges") or []),
                "strict_error_count": len(errors),
                "all_situations_have_counterevidence": has_counterevidence,
                "missing_counterevidence_rejected": any(
                    "counterevidence_edges is required" in error
                    for error in missing_counterevidence_errors
                ),
                "missing_counterevidence_error_count": len(missing_counterevidence_errors),
                "not_investment_advice_guard": safe,
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "finance_numeric_assurance":
            mod = _load_copied_module("finance_numeric_assurance", modules, public_root=public_root)
            source_ref = {"kind": "fixture_public_synthetic", "path": "batch6_probe_manifest.json"}
            receipt = mod.build_finance_numeric_assurance(
                quant_mart={
                    "stockgrid_flow_board": [
                        {
                            "ticker": "ACME",
                            "flow": 125.0,
                            "flow_usd": 1.0,
                            "flow_unit": "usd_millions",
                            "source_refs": [source_ref],
                        },
                        {
                            "ticker": "ACME",
                            "flow": 125.0,
                            "flow_usd": 125_000_000.0,
                            "flow_unit": "usd_millions",
                            "source_refs": [source_ref],
                        },
                    ],
                    "prediction_market_event_board": [
                        {"probability": 70.2, "source_refs": [source_ref]}
                    ],
                }
            )
            check_ids = sorted(
                {
                    str(row.get("check_id"))
                    for row in receipt.get("findings") or []
                    if isinstance(row, Mapping)
                }
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass"
                if receipt.get("display_state") == "blocked"
                and "stockgrid_flow_unit_scale_mismatch" in check_ids
                and "probability_bounds" in check_ids
                else "blocked",
                "display_state": receipt.get("display_state"),
                "check_ids": check_ids,
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "fail_closed_status_judge":
            mod = _import_copied_package_module(
                "idea_microcosm.validators",
                "idea_microcosm_validators",
                modules,
                public_root=public_root,
            )
            policy = {
                "policy_wellformedness": {
                    "policy_poisoning_default": "malformed_policy_blocks_judgment"
                },
                "tier_model": {
                    "model_type": "product_tiers_with_fixture_ordering_projection"
                },
                "allowed_transitions": [
                    {
                        "from": "fixture_constructed",
                        "to": "fit_for_public_claim",
                        "reason": "public fixture has evidence refs",
                    }
                ],
                "prohibited_upgrades": [
                    {
                        "from": "receipt_observed",
                        "to": "truth_authority",
                        "decision": "block",
                        "reason": "receipt is not truth authority",
                    }
                ],
                "required_evidence": [
                    {
                        "from": "fixture_constructed",
                        "to": "fit_for_public_claim",
                        "refs": ["receipt:batch6"],
                        "decision_if_missing": "downgrade",
                        "reason": "public claim needs a receipt",
                    }
                ],
                "required_gates": [],
                "downgrade_rules": [],
                "default_decision": {
                    "decision": "block",
                    "reason": "transition_not_in_policy",
                },
            }
            allow = mod.judge_status_request(
                policy,
                {
                    "from": "fixture_constructed",
                    "to": "fit_for_public_claim",
                    "evidence_refs": ["receipt:batch6"],
                },
            )
            missing = mod.judge_status_request(
                policy,
                {
                    "from": "fixture_constructed",
                    "to": "fit_for_public_claim",
                    "evidence_refs": [],
                },
            )
            forbidden = mod.judge_status_request(
                policy,
                {"from": "receipt_observed", "to": "truth_authority"},
            )
            poisoned = mod.judge_status_request(
                {"policy_wellformedness": {"policy_poisoning_default": "allow"}},
                {"from": "receipt_observed", "to": "truth_authority"},
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass"
                if allow.get("decision") == "allow"
                and missing.get("decision") == "downgrade"
                and forbidden.get("decision") == "block"
                and poisoned.get("decision") == "block"
                else "blocked",
                "allowed_decision": allow.get("decision"),
                "missing_evidence_decision": missing.get("decision"),
                "forbidden_decision": forbidden.get("decision"),
                "poisoned_policy_decision": poisoned.get("decision"),
                "source_execution_relation": "macro_package_executed_after_exact_copy_validation",
            }

        if exercise_id == "idea_microcosm_concurrency_guard":
            mod = _load_copied_module(
                "idea_microcosm_concurrency_guard", modules, public_root=public_root
            )
            parent_child = mod._paths_overlap("src/microcosm_core/organs", "src/microcosm_core/organs/batch6.py")
            siblings = mod._paths_overlap("src/a.py", "src/b.py")
            normalized = mod._normalize_paths(public_root, ["src/./microcosm_core/organs/batch6.py"])
            return {
                "exercise_id": exercise_id,
                "status": "pass" if parent_child and not siblings and normalized else "blocked",
                "parent_child_overlap": bool(parent_child),
                "parent_child_conflict_detected": bool(parent_child),
                "sibling_overlap": bool(siblings),
                "normalized_path_count": len(normalized),
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "metabolism_market_clock":
            mod = _load_copied_module("metabolism_market_clock", modules, public_root=public_root)
            config = mod.market_hours_hourly_config()
            now = _utc("2026-05-29T15:31:00Z")
            date_key = "2026-05-29"
            due = mod.due_fire_points(
                now,
                config,
                last_fired={f"open:{date_key}": "2026-05-29T13:31:00Z"},
            )
            names = [point.name for point in due]
            duplicate_suppressed = "open" not in names
            return {
                "exercise_id": exercise_id,
                "status": "pass"
                if {"hour_10_30", "hour_11_30"} <= set(names) and duplicate_suppressed
                else "blocked",
                "due_count": len(due),
                "open_duplicate_suppressed": duplicate_suppressed,
                "close_not_due": "close" not in names,
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "population_lane_provider_recovery":
            mod = _load_copied_module(
                "population_lane_provider_recovery", modules, public_root=public_root
            )
            timeout = mod.transport_suppression_scope(
                "timeout", "nvidia_nim", "deepseek-ai/deepseek-v4-flash"
            )
            dedupe = mod.transport_suppression_scope(
                "blocked_duplicate",
                "nvidia_nim",
                "deepseek-ai/deepseek-v4-flash",
                row_job_id="row-1",
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass"
                if timeout.get("scope") == "provider_model"
                and dedupe.get("scope") == "row_fingerprint"
                else "blocked",
                "timeout_scope": timeout.get("scope"),
                "timeout_key": timeout.get("key"),
                "blocked_duplicate_scope": dedupe.get("scope"),
                "source_execution_relation": "copied_source_body_executed",
            }

        if exercise_id == "demo_take_temporal_join":
            mod = _load_copied_module("demo_take_capture", modules, public_root=public_root)
            pause_events = [
                {"kind": "pause", "at_iso": "2026-05-31T10:00:10+00:00"},
                {"kind": "resume", "at_iso": "2026-05-31T10:00:25+00:00"},
            ]
            video_t = mod.video_t_seconds(
                120.0, pause_events, "2026-05-31T10:02:00+00:00"
            )
            active_pause_t = mod.video_t_seconds(
                35.0,
                [{"kind": "pause", "at_iso": "2026-05-31T10:00:10+00:00"}],
                "2026-05-31T10:00:30+00:00",
            )
            return {
                "exercise_id": exercise_id,
                "status": "pass" if video_t == 105.0 and active_pause_t == 15.0 else "blocked",
                "paused_duration_removed_seconds": 15.0,
                "closed_pause_video_t_seconds": video_t,
                "active_pause_video_t_seconds": active_pause_t,
                "source_execution_relation": "copied_source_body_executed",
            }
    except Exception as exc:  # pragma: no cover - receipt shape is asserted by tests.
        return {
            "exercise_id": exercise_id,
            "status": "blocked",
            "error_type": exc.__class__.__name__,
            "body_in_receipt": False,
        }
    return {
        "exercise_id": exercise_id,
        "status": "blocked",
        "error_type": "unknown_exercise_id",
        "body_in_receipt": False,
    }


@lru_cache(maxsize=8)
def _semantic_runtime_exercises(input_ref: str) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_runtime_exercises` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_ref)
    public_root = public_root_for_path(input_path)
    source_manifest = validate_source_manifest(input_path, SPEC, public_root=public_root)
    modules = _module_rows(source_manifest, public_root=public_root)
    if any(module_id not in modules for module_id in EXPECTED_MODULE_IDS):
        return {}
    return {
        mechanism_id: _run_source_exercise(mechanism_id, modules, public_root)
        for mechanism_id in EXPECTED_MECHANISMS
    }


def _observed_negative_case(
    case_id: str,
    runtime_exercises: Mapping[str, Mapping[str, Any]],
) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_observed_negative_case` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row_spec = NEGATIVE_CASE_MECHANISMS.get(case_id)
    if row_spec is None:
        return False
    mechanism_id, _code = row_spec
    result = runtime_exercises.get(mechanism_id)
    if not isinstance(result, Mapping) or result.get("status") != "pass":
        return False
    if case_id == "stopword_only_keyphrase_empty":
        return result.get("stopword_only_phrase_count") == 0
    if case_id == "schema_loose_voice_conflation":
        return (
            {"assistant_text", "user_tail"} <= set(result.get("source_roles") or [])
            and result.get("body_persisted") is False
        )
    if case_id == "handoff_unrelated_below_floor":
        return result.get("confidence_floor_met") is True and result.get(
            "unrelated_below_floor"
        ) is True
    if case_id == "observed_turn_duplicate_rerender":
        return (
            result.get("duplicate_window_reason") == "observed_window_within_memory"
            and result.get("merged_count") == 3
        )
    if case_id == "market_situation_missing_counterevidence":
        return result.get("missing_counterevidence_rejected") is True
    if case_id == "finance_unit_scale_mismatch":
        return (
            result.get("display_state") == "blocked"
            and "stockgrid_flow_unit_scale_mismatch" in (result.get("check_ids") or [])
        )
    if case_id == "status_policy_poisoned":
        return result.get("poisoned_policy_decision") == "block"
    if case_id == "concurrency_parent_child_conflict":
        return result.get("parent_child_conflict_detected") is True
    if case_id == "market_clock_duplicate_fire_suppressed":
        return result.get("open_duplicate_suppressed") is True
    if case_id == "provider_timeout_scope_narrow":
        return result.get("timeout_scope") == "provider_model"
    if case_id == "demo_take_pause_remap":
        return (
            result.get("closed_pause_video_t_seconds") == 105.0
            and result.get("active_pause_video_t_seconds") == 15.0
        )
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row_spec = NEGATIVE_CASE_MECHANISMS.get(case_id)
    if row_spec is None:
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    _mechanism_id, expected_code = row_spec
    runtime_exercises = _semantic_runtime_exercises(str(input_dir.resolve(strict=False)))
    if not _observed_negative_case(case_id, runtime_exercises):
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    return {
        "status": "blocked",
        "error_codes": [expected_code],
        "body_in_receipt": False,
    }


def _evaluate(input_path: Path, public_root: Path, source_manifest: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    probe, findings = _load_manifest(input_path)
    modules = _module_rows(source_manifest, public_root=public_root)
    expected_module_missing = [
        module_id for module_id in EXPECTED_MODULE_IDS if module_id not in modules
    ]
    if expected_module_missing:
        findings.append(
            _finding(
                "BATCH6_SOURCE_MODULES_MISSING",
                "Batch 6 source module manifest is missing required copied modules.",
                subject_id=",".join(expected_module_missing),
            )
        )

    mechanisms = [
        row for row in probe.get("mechanisms", []) if isinstance(row, Mapping)
    ]
    mechanism_ids = [str(row.get("mechanism_id") or "") for row in mechanisms]
    missing_mechanisms = [
        mechanism_id for mechanism_id in EXPECTED_MECHANISMS if mechanism_id not in mechanism_ids
    ]
    extra_mechanisms = [
        mechanism_id for mechanism_id in mechanism_ids if mechanism_id not in EXPECTED_MECHANISMS
    ]
    if missing_mechanisms or extra_mechanisms:
        findings.append(
            _finding(
                "BATCH6_MECHANISM_SET_MISMATCH",
                "Batch 6 probe manifest must cover exactly the selected source-open primitives.",
                subject_id="mechanisms",
            )
        )

    mechanism_rows = [
        _mechanism_status(row, modules=modules, public_root=public_root)
        for row in mechanisms
    ]
    for row in mechanism_rows:
        if row["status"] != "pass":
            findings.append(
                _finding(
                    "BATCH6_MECHANISM_SOURCE_ANCHOR_MISSING",
                    "Mechanism source modules or anchors are missing.",
                    subject_id=row["mechanism_id"],
                )
            )

    runtime_exercises: dict[str, dict[str, Any]] = {}
    if not expected_module_missing:
        for mechanism_id in EXPECTED_MECHANISMS:
            runtime_exercises[mechanism_id] = _run_source_exercise(
                mechanism_id,
                modules,
                public_root,
            )
            if runtime_exercises[mechanism_id].get("status") != "pass":
                findings.append(
                    _finding(
                        "BATCH6_SOURCE_EXERCISE_FAILED",
                        "Batch 6 copied source exercise did not pass.",
                        subject_id=mechanism_id,
                    )
                )

    return {
        "status": "pass" if not findings else "blocked",
        "schema_version": "batch6_unsurfaced_primitives_capsule_exercise_v1",
        "mechanism_count": len(mechanism_rows),
        "expected_mechanism_count": len(EXPECTED_MECHANISMS),
        "mechanisms": mechanism_rows,
        "copied_macro_source_module_count": len(modules),
        "runtime_exercises": runtime_exercises,
        "claim_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "error_codes": [str(row.get("error_code")) for row in findings if row.get("error_code")],
        "findings": findings,
        "body_in_receipt": False,
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
    - Teleology: Implements `run` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
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


def run_batch6_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch6_bundle` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["mechanism_count"] = exercise.get("mechanism_count")
    card["copied_macro_source_module_count"] = exercise.get("copied_macro_source_module_count")
    card["omission_receipt"] = {
        "omitted": [
            "copied source body text",
            "raw operator transcripts",
            "prompt-shelf private logs",
            "provider/browser/session payloads",
            "live market data responses",
        ],
        "reason": "Batch 6 receipts carry source refs, digests, anchors, public exercise outcomes, and anti-claims, not raw private bodies or live state.",
    }
    return card


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` while keeping the callable contract visible to source-module readers.
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
    if args.action == "validate-bundle":
        result = run_batch6_bundle(
            args.input,
            args.out,
            acceptance_out=args.acceptance_out,
            command=f"{ORGAN_ID} validate-bundle",
        )
    else:
        result = run(
            args.input,
            args.out,
            acceptance_out=args.acceptance_out,
            command=f"{ORGAN_ID} run",
        )
    payload = result_card(result) if args.card else result
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
