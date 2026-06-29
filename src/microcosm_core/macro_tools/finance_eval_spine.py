"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.finance_eval_spine` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: BUNDLE_RESULT_NAME, REPORT_SCHEMA, MANIFEST_NAME, SOURCE_MANIFEST_NAME, CONTRACT_NAME, OPERATING_PICTURE_NAME, ASSURANCE_SURFACE_NAME, ASSURANCE_SURFACE_SCHEMA, QUANT_RESEARCH_SPINE_SCHEMA, SOURCE_MODULE_ROOT, SOURCE_IMPORT_CLASS, SOURCE_TO_TARGET_RELATION, SOURCE_OPEN_BODY_POLICY, REQUIRED_MODULES, TOOLS_FINANCE_MODULES, ALLOWED_COVERAGE_STATUSES, ALLOWED_AUTHORITY_CLASSIFICATIONS, FEED_FRESHNESS_STATUSES, STATISTICAL_DISCIPLINE_SEQUENCE, QUANT_RESEARCH_OUTPUT_STATES, QUANT_RESEARCH_AGENDA_STATES, REQUIRED_INPUTS, REQUIRED_CLASSIFICATIONS, ALLOWED_MATERIAL_CLASSES, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
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
ASSURANCE_SURFACE_NAME = "finance_research_assurance_surface.json"
ASSURANCE_SURFACE_SCHEMA = "finance_research_assurance_surface_v0"
QUANT_RESEARCH_SPINE_SCHEMA = "finance_quant_research_experiment_spine_v0"
SOURCE_MODULE_ROOT = Path("source_modules/tools/finance")
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_TO_TARGET_RELATION = "exact_copy"
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
    "family_loss_matrix.py",
    "loss_differentials.py",
    "model_selection_stats.py",
    "spa_statistics.py",
)
TOOLS_FINANCE_MODULES = (
    "__init__.py",
    "admit_forecasts.py",
    "bootstrap_reference.py",
    "build_effective_evidence.py",
    "build_eval_operating_picture.py",
    "build_price_history.py",
    "calibrate_forecast_probabilities.py",
    "compare_variants.py",
    "eval_replay.py",
    "event_keys.py",
    "family_loss_matrix.py",
    "historical_replay.py",
    "loss_differentials.py",
    "model_selection.py",
    "model_selection_stats.py",
    "refresh_feeds.py",
    "resolve_forecasts.py",
    "spa_statistics.py",
    "variant_registry.py",
)
ALLOWED_COVERAGE_STATUSES = {
    "imported_public_body",
    "deferred_public_safe_core",
    "deferred_public_safe_statistical",
    "operational_receipt_only",
    "operational_only",
}
ALLOWED_AUTHORITY_CLASSIFICATIONS = {
    "core_public_safe_evidence_body",
    "public_safe_statistical_discipline",
    "operational_feed_runtime_dependency",
    "operational_only",
}
FEED_FRESHNESS_STATUSES = {
    "fresh_green_feed",
    "stale_green_feed",
    "scheduled_shell",
    "blocked_missing_artifact",
}
STATISTICAL_DISCIPLINE_SEQUENCE = (
    "proper_scoring_rules",
    "pairwise_equal_loss",
    "multiple_comparison_guard",
    "review_gated_evolve_implication",
)
QUANT_RESEARCH_OUTPUT_STATES = {
    "awaiting_evidence",
    "insufficient_evidence",
    "candidate_set",
    "review_candidate",
    "rejected",
    "blocked_authority_overclaim",
}
QUANT_RESEARCH_AGENDA_STATES = {
    "selected_for_next_test",
    "deferred_data_snooping_risk",
    "control_candidate",
    "needs_more_evidence",
    "completed_insufficient_evidence",
}
REQUIRED_INPUTS = (
    *(SOURCE_MODULE_ROOT / name for name in REQUIRED_MODULES),
    Path(OPERATING_PICTURE_NAME),
    Path(ASSURANCE_SURFACE_NAME),
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
    "public_microcosm_assurance_surface",
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
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_display` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def _policy_path(public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_policy_path` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidate = public_root / "core/private_state_forbidden_classes.json"
    if candidate.is_file():
        return candidate
    for parent in Path(__file__).resolve(strict=False).parents:
        fallback = parent / "core/private_state_forbidden_classes.json"
        if fallback.is_file():
            return fallback
    return candidate


def _file_sha256(path: Path) -> str | None:
    """
    [ACTION]
    - Teleology: Implements `_file_sha256` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int | None:
    """
    [ACTION]
    - Teleology: Implements `_line_count` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if not path.is_file():
        return None
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _as_list(value: Any) -> list[Any]:
    """
    [ACTION]
    - Teleology: Implements `_as_list` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_as_dict` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [str(item) for item in _as_list(value) if isinstance(item, str) and item]


def _get_path(payload: Mapping[str, Any], keys: Iterable[str]) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_get_path` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _quant_registry_summary(quant: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_quant_registry_summary` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    registry = [
        row for row in _as_list(quant.get("experiment_registry")) if isinstance(row, Mapping)
    ]
    output_counts: Counter[str] = Counter()
    negative_control_count = 0
    registry_problem_count = 0
    for row in registry:
        if str(row.get("stress_role") or "").startswith("negative_control"):
            negative_control_count += 1
        comparison = _as_dict(row.get("model_comparison"))
        state = str(comparison.get("output_state") or "")
        output_counts[state] += 1
        split = _as_dict(row.get("split_discipline"))
        bridge = _as_dict(row.get("oracle_evolve_implication"))
        advice = _as_dict(row.get("no_advice_mode"))
        if (
            not row.get("experiment_id")
            or not row.get("public_safe_hypothesis")
            or state not in QUANT_RESEARCH_OUTPUT_STATES
            or comparison.get("winner_language_allowed") is not False
            or split.get("random_kfold_allowed") is not False
            or not split.get("split_policy")
            or bridge.get("review_gated") is not True
            or bridge.get("auto_apply_allowed") is not False
            or advice.get("enabled") is not True
            or advice.get("non_advisory_research_only") is not True
        ):
            registry_problem_count += 1
    negative_or_insufficient_count = sum(
        output_counts.get(state, 0)
        for state in ("insufficient_evidence", "rejected", "blocked_authority_overclaim")
    )
    lineage = _as_dict(quant.get("lineage_summary"))
    lineage_status = str(lineage.get("lineage_status") or "")
    lineage_problem_count = 0
    if lineage.get("registry_count") != len(registry):
        lineage_problem_count += 1
    if lineage.get("minimum_registry_count") and int(lineage.get("minimum_registry_count") or 0) > len(registry):
        lineage_problem_count += 1
    if lineage.get("auto_apply_allowed_any") is True:
        lineage_problem_count += 1
    if lineage.get("winner_language_allowed_any") is True:
        lineage_problem_count += 1
    if lineage.get("random_kfold_allowed_any") is True:
        lineage_problem_count += 1
    if lineage.get("review_gated_all") is False or lineage.get("no_advice_enabled_all") is False:
        lineage_problem_count += 1
    return {
        "registry_count": len(registry),
        "minimum_registry_count": lineage.get("minimum_registry_count"),
        "lineage_status": lineage_status,
        "output_state_counts": dict(output_counts),
        "negative_control_count": negative_control_count,
        "negative_or_insufficient_count": negative_or_insufficient_count,
        "registry_problem_count": registry_problem_count,
        "lineage_problem_count": lineage_problem_count,
        "stress_validated": (
            len(registry) >= 2
            and negative_control_count >= 1
            and negative_or_insufficient_count >= 1
            and registry_problem_count == 0
            and lineage_problem_count == 0
            and lineage_status == "stress_validated_public_demo"
        ),
    }


def _quant_agenda_summary(quant: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_quant_agenda_summary` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    agenda = _as_dict(quant.get("research_agenda"))
    policy = _as_dict(agenda.get("selection_policy"))
    budget = _as_dict(agenda.get("search_budget"))
    candidates = [
        row for row in _as_list(agenda.get("candidate_agenda")) if isinstance(row, Mapping)
    ]
    family_ids = {str(row.get("family_id") or "") for row in candidates if row.get("family_id")}
    state_counts: Counter[str] = Counter(str(row.get("agenda_state") or "") for row in candidates)
    candidate_problem_count = 0
    for row in candidates:
        state = str(row.get("agenda_state") or "")
        if (
            not row.get("candidate_id")
            or not row.get("family_id")
            or not row.get("public_safe_hypothesis")
            or not row.get("expected_failure_mode")
            or state not in QUANT_RESEARCH_AGENDA_STATES
            or row.get("authority_ceiling") != "non_advisory_research_evaluation_only"
            or row.get("review_gated") is not True
            or row.get("auto_apply_allowed") is not False
            or row.get("no_advice_enabled") is not True
            or row.get("winner_language_allowed") is not False
        ):
            candidate_problem_count += 1
    policy_problem_count = 0
    if policy.get("prefer_falsifiable") is not True:
        policy_problem_count += 1
    if policy.get("prefer_family_diversity") is not True:
        policy_problem_count += 1
    if policy.get("penalize_parameter_fishing") is not True:
        policy_problem_count += 1
    if policy.get("penalize_duplicate_prior_family") is not True:
        policy_problem_count += 1
    if policy.get("require_negative_or_control_candidate") is not True:
        policy_problem_count += 1
    if policy.get("performance_metric_optimization_allowed") is not False:
        policy_problem_count += 1
    if policy.get("winner_language_allowed") is not False:
        policy_problem_count += 1
    budget_problem_count = 0
    if int(budget.get("candidate_count") or 0) != len(candidates):
        budget_problem_count += 1
    if int(budget.get("family_count") or 0) != len(family_ids):
        budget_problem_count += 1
    if int(budget.get("selected_for_next_test_count") or 0) < 1:
        budget_problem_count += 1
    if int(budget.get("deferred_data_snooping_count") or 0) < 1:
        budget_problem_count += 1
    if int(budget.get("negative_or_control_candidate_count") or 0) < 1:
        budget_problem_count += 1
    if int(budget.get("needs_more_evidence_count") or 0) < 1:
        budget_problem_count += 1
    if budget.get("data_snooping_guard_active") is not True:
        budget_problem_count += 1
    if budget.get("max_selected_next") not in {0, 1}:
        budget_problem_count += 1
    bridge = _as_dict(agenda.get("oracle_evolve_implication"))
    advice = _as_dict(agenda.get("no_advice_mode"))
    gate_problem_count = 0
    if bridge.get("review_gated") is not True or bridge.get("auto_apply_allowed") is not False:
        gate_problem_count += 1
    if advice.get("enabled") is not True or advice.get("non_advisory_research_only") is not True:
        gate_problem_count += 1
    return {
        "schema_version": agenda.get("schema_version"),
        "status": agenda.get("status"),
        "candidate_count": len(candidates),
        "family_count": len(family_ids),
        "state_counts": dict(sorted(state_counts.items())),
        "selected_for_next_test_count": state_counts.get("selected_for_next_test", 0),
        "deferred_data_snooping_count": state_counts.get("deferred_data_snooping_risk", 0),
        "negative_or_control_candidate_count": state_counts.get("control_candidate", 0),
        "needs_more_evidence_count": state_counts.get("needs_more_evidence", 0),
        "completed_insufficient_evidence_count": state_counts.get(
            "completed_insufficient_evidence", 0
        ),
        "candidate_problem_count": candidate_problem_count,
        "policy_problem_count": policy_problem_count,
        "budget_problem_count": budget_problem_count,
        "gate_problem_count": gate_problem_count,
        "compiled": (
            agenda.get("schema_version") == "finance_quant_research_agenda_v0"
            and agenda.get("status") == "compiled_public_safe"
            and len(candidates) >= 4
            and len(family_ids) >= 3
            and state_counts.get("selected_for_next_test", 0) >= 1
            and state_counts.get("deferred_data_snooping_risk", 0) >= 1
            and state_counts.get("control_candidate", 0) >= 1
            and state_counts.get("needs_more_evidence", 0) >= 1
            and candidate_problem_count == 0
            and policy_problem_count == 0
            and budget_problem_count == 0
            and gate_problem_count == 0
        ),
    }


def _quant_execution_cycle_summary(quant: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_quant_execution_cycle_summary` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cycle = _as_dict(quant.get("agenda_execution_cycle"))
    plan = _as_dict(cycle.get("pre_analysis_plan"))
    execution = _as_dict(cycle.get("execution"))
    registry_update = _as_dict(cycle.get("registry_update"))
    family_update = _as_dict(cycle.get("family_memory_update"))
    agenda_recompile = _as_dict(cycle.get("agenda_recompile"))
    bridge = _as_dict(cycle.get("oracle_evolve_implication"))
    advice = _as_dict(cycle.get("no_advice_mode"))
    registry = [
        row for row in _as_list(quant.get("experiment_registry")) if isinstance(row, Mapping)
    ]
    experiment_ids = {str(row.get("experiment_id") or "") for row in registry}
    result_state = str(execution.get("result_state") or registry_update.get("result_state") or "")
    problem_count = 0
    if cycle.get("schema_version") != "finance_quant_agenda_execution_cycle_v0":
        problem_count += 1
    if not cycle.get("cycle_id") or not cycle.get("selected_candidate_id"):
        problem_count += 1
    if plan.get("registered_before_execution") is not True:
        problem_count += 1
    if plan.get("analysis_plan_locked") is not True:
        problem_count += 1
    if plan.get("post_hoc_plan_mutation_allowed") is not False:
        problem_count += 1
    if execution.get("used_existing_evaluator") is not True:
        problem_count += 1
    if execution.get("winner_language_allowed") is not False:
        problem_count += 1
    if result_state not in QUANT_RESEARCH_OUTPUT_STATES:
        problem_count += 1
    appended_id = str(registry_update.get("appended_experiment_id") or "")
    previous_count = int(registry_update.get("previous_registry_count") or 0)
    new_count = int(registry_update.get("new_registry_count") or 0)
    if not appended_id or appended_id not in experiment_ids:
        problem_count += 1
    if new_count <= previous_count or new_count != len(registry):
        problem_count += 1
    if not family_update.get("family_id") or not family_update.get("new_memory_state"):
        problem_count += 1
    if agenda_recompile.get("status") != "recompiled_after_cycle":
        problem_count += 1
    if not agenda_recompile.get("next_selected_candidate_id"):
        problem_count += 1
    if bridge.get("review_gated") is not True or bridge.get("auto_apply_allowed") is not False:
        problem_count += 1
    if advice.get("enabled") is not True or advice.get("non_advisory_research_only") is not True:
        problem_count += 1
    return {
        "schema_version": cycle.get("schema_version"),
        "cycle_id": cycle.get("cycle_id"),
        "selected_candidate_id": cycle.get("selected_candidate_id"),
        "pre_analysis_plan_id": plan.get("plan_id"),
        "registered_before_execution": plan.get("registered_before_execution"),
        "analysis_plan_locked": plan.get("analysis_plan_locked"),
        "post_hoc_plan_mutation_allowed": plan.get("post_hoc_plan_mutation_allowed"),
        "execution_status": execution.get("status"),
        "used_existing_evaluator": execution.get("used_existing_evaluator"),
        "result_state": result_state,
        "appended_experiment_id": appended_id,
        "previous_registry_count": previous_count,
        "new_registry_count": new_count,
        "family_memory_state": family_update.get("new_memory_state"),
        "agenda_recompile_status": agenda_recompile.get("status"),
        "next_selected_candidate_id": agenda_recompile.get("next_selected_candidate_id"),
        "review_gated": bridge.get("review_gated"),
        "auto_apply_allowed": bridge.get("auto_apply_allowed"),
        "no_advice_enabled": advice.get("enabled"),
        "problem_count": problem_count,
        "closed_loop": problem_count == 0,
    }


def _finding(
    code: str,
    message: str,
    *,
    source: str | None = None,
    expected: Any | None = None,
    observed: Any | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_finding` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_load_json_input` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_declared_files` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        str(row.get("path") or ""): row
        for row in _as_list(manifest.get("files"))
        if isinstance(row, Mapping) and row.get("path")
    }


def _source_manifest(input_dir: Path, manifest: Mapping[str, Any], *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_manifest` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    declared = _declared_files(manifest)
    rows: list[dict[str, Any]] = []
    for rel in REQUIRED_INPUTS:
        path = input_dir / rel
        declared_row = declared.get(rel.as_posix(), {})
        expected_target_ref = _expected_public_target_ref(rel.as_posix())
        sha256 = _file_sha256(path)
        expected_sha256 = declared_row.get("sha256")
        actual_line_count = _line_count(path)
        expected_line_count = declared_row.get("line_count")
        rows.append(
            {
                "path": rel.as_posix(),
                "display_ref": _display(path, public_root=public_root),
                "source_ref": declared_row.get("source_ref"),
                "target_ref": declared_row.get("target_ref"),
                "expected_target_ref": expected_target_ref,
                "target_ref_matches_path": declared_row.get("target_ref")
                == expected_target_ref,
                "source_to_target_relation": declared_row.get("source_to_target_relation"),
                "sha256_match": declared_row.get("sha256_match"),
                "source_sha256": declared_row.get("source_sha256"),
                "target_sha256": declared_row.get("target_sha256"),
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


def _expected_public_target_ref(path: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_expected_public_target_ref` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        "microcosm-substrate/examples/finance_forecast_evaluation_spine/"
        f"exported_finance_eval_bundle/{path}"
    )


def _validate_copied_body_import_row(
    row: Mapping[str, Any],
    findings: list[dict[str, Any]],
    *,
    source: str,
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_validate_copied_body_import_row` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = str(row.get("path") or "")
    expected_target_ref = _expected_public_target_ref(path) if path else None
    sha256 = row.get("sha256")
    if not path:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_PATH_MISSING",
                "Copied finance evaluator body row must name its bundle target path.",
                source=source,
            )
        )
        return
    if row.get("target_ref") != expected_target_ref:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_TARGET_REF_MISMATCH",
                "Copied finance evaluator body row must point at its public bundle target.",
                source=source,
                expected=expected_target_ref,
                observed=row.get("target_ref"),
            )
        )
    if row.get("source_to_target_relation") != SOURCE_TO_TARGET_RELATION:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_RELATION_MISMATCH",
                "Copied finance evaluator body row must declare an exact source-to-target relation.",
                source=source,
                expected=SOURCE_TO_TARGET_RELATION,
                observed=row.get("source_to_target_relation"),
            )
        )
    if row.get("sha256_match") is not True:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_SHA256_MATCH_MISMATCH",
                "Copied finance evaluator body row must declare matching source and target digests.",
                source=source,
                expected=True,
                observed=row.get("sha256_match"),
            )
        )
    if row.get("source_sha256") != sha256 or row.get("target_sha256") != sha256:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_SOURCE_TARGET_DIGEST_MISMATCH",
                "Copied finance evaluator body row must bind source and target digests to the declared body digest.",
                source=source,
                expected=sha256,
                observed={
                    "source_sha256": row.get("source_sha256"),
                    "target_sha256": row.get("target_sha256"),
                },
            )
        )


def _validate_required_source_manifest_paths(
    rows: Iterable[Mapping[str, Any]],
    findings: list[dict[str, Any]],
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_validate_required_source_manifest_paths` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    required_paths = {
        (SOURCE_MODULE_ROOT / module_name).as_posix()
        for module_name in REQUIRED_MODULES
    }
    observed_paths = [
        str(row.get("path") or "")
        for row in rows
        if row.get("source_import_class") == SOURCE_IMPORT_CLASS
    ]
    observed_nonempty = [path for path in observed_paths if path]
    observed_counts = Counter(observed_nonempty)
    missing_paths = sorted(required_paths - set(observed_nonempty))
    unexpected_paths = sorted(set(observed_nonempty) - required_paths)
    duplicate_paths = sorted(
        path for path, count in observed_counts.items() if count > 1
    )
    if missing_paths:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_REQUIRED_PATH_MISSING",
                "Source module manifest must cover each required copied finance evaluator body exactly once.",
                source=SOURCE_MANIFEST_NAME,
                expected=sorted(required_paths),
                observed=sorted(set(observed_nonempty)),
            )
        )
    if unexpected_paths:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_UNEXPECTED_PATH",
                "Source module manifest copied body rows must stay within the required finance evaluator body set.",
                source=SOURCE_MANIFEST_NAME,
                expected=sorted(required_paths),
                observed=unexpected_paths,
            )
        )
    if duplicate_paths:
        findings.append(
            _finding(
                "SOURCE_MANIFEST_REQUIRED_PATH_DUPLICATE",
                "Source module manifest copied body rows must not duplicate a required finance evaluator body path.",
                source=SOURCE_MANIFEST_NAME,
                observed=duplicate_paths,
            )
        )


def _validate_manifest(
    manifest: Mapping[str, Any],
    source_manifest_payload: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_validate_manifest` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
        if row.get("source_import_class") == SOURCE_IMPORT_CLASS:
            _validate_copied_body_import_row(
                row,
                findings,
                source=f"{MANIFEST_NAME}::{path or '<missing_path>'}",
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
    source_module_rows = _as_list(source_manifest_payload.get("modules"))
    for row in source_module_rows:
        if not isinstance(row, Mapping):
            findings.append(
                _finding(
                    "INVALID_SOURCE_MANIFEST_MODULE_ROW",
                    "Source module manifest modules must be object rows.",
                    source=SOURCE_MANIFEST_NAME,
                )
            )
            continue
        if row.get("source_import_class") == SOURCE_IMPORT_CLASS:
            _validate_copied_body_import_row(
                row,
                findings,
                source=f"{SOURCE_MANIFEST_NAME}::{row.get('path') or '<missing_path>'}",
            )
    _validate_required_source_manifest_paths(
        [row for row in source_module_rows if isinstance(row, Mapping)],
        findings,
    )


def _validate_digests(
    source_manifest: Mapping[str, Any], findings: list[dict[str, Any]]
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_validate_digests` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_validate_source_anchors` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_validate_contract` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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


def _validate_module_coverage(
    contract: Mapping[str, Any],
    assurance_surface: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_module_coverage` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    assurance_contract = _as_dict(contract.get("finance_research_assurance"))
    rows = [
        row
        for row in _as_list(assurance_contract.get("module_coverage"))
        if isinstance(row, Mapping)
    ]
    expected_refs = {f"tools/finance/{name}" for name in TOOLS_FINANCE_MODULES}
    required_import_refs = {f"tools/finance/{name}" for name in REQUIRED_MODULES}
    observed_refs = {str(row.get("source_ref") or "") for row in rows}
    missing_refs = sorted(expected_refs - observed_refs)
    unexpected_refs = sorted(ref for ref in observed_refs - expected_refs if ref)
    if missing_refs:
        findings.append(
            _finding(
                "MODULE_COVERAGE_GAP",
                "Finance assurance module coverage contract must classify every tools/finance module.",
                source=f"{CONTRACT_NAME}::finance_research_assurance.module_coverage",
                expected=sorted(expected_refs),
                observed=sorted(observed_refs),
            )
        )
    if unexpected_refs:
        findings.append(
            _finding(
                "MODULE_COVERAGE_UNKNOWN_SOURCE",
                "Finance assurance module coverage contract contains a source outside tools/finance inventory.",
                source=f"{CONTRACT_NAME}::finance_research_assurance.module_coverage",
                expected=sorted(expected_refs),
                observed=unexpected_refs,
            )
        )
    imported_refs: set[str] = set()
    status_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    rows_out: list[dict[str, Any]] = []
    for row in rows:
        source_ref = str(row.get("source_ref") or "")
        status = str(row.get("coverage_status") or "")
        classification = str(row.get("authority_classification") or "")
        decision = str(row.get("decision") or "")
        public_safe = row.get("public_safe")
        status_counts[status] += 1
        classification_counts[classification] += 1
        if status not in ALLOWED_COVERAGE_STATUSES:
            findings.append(
                _finding(
                    "MODULE_COVERAGE_STATUS_UNKNOWN",
                    "Finance assurance module coverage status must use the public status vocabulary.",
                    source=f"{CONTRACT_NAME}::{source_ref}",
                    expected=sorted(ALLOWED_COVERAGE_STATUSES),
                    observed=status,
                )
            )
        if classification not in ALLOWED_AUTHORITY_CLASSIFICATIONS:
            findings.append(
                _finding(
                    "MODULE_COVERAGE_CLASSIFICATION_UNKNOWN",
                    "Finance assurance module authority classification must use the public classification vocabulary.",
                    source=f"{CONTRACT_NAME}::{source_ref}",
                    expected=sorted(ALLOWED_AUTHORITY_CLASSIFICATIONS),
                    observed=classification,
                )
            )
        if not decision or decision in {"unknown", "pending"}:
            findings.append(
                _finding(
                    "MODULE_COVERAGE_DECISION_MISSING",
                    "Finance assurance module coverage rows must carry an explicit import/defer decision.",
                    source=f"{CONTRACT_NAME}::{source_ref}",
                    observed=decision,
                )
            )
        if public_safe is not True and status != "operational_only":
            findings.append(
                _finding(
                    "MODULE_COVERAGE_PUBLIC_SAFE_NOT_TRUE",
                    "Finance assurance module rows that affect the public spine must be explicitly public-safe.",
                    source=f"{CONTRACT_NAME}::{source_ref}",
                    expected=True,
                    observed=public_safe,
                )
            )
        if status == "imported_public_body":
            imported_refs.add(source_ref)
        rows_out.append(
            {
                "source_ref": source_ref,
                "coverage_status": status,
                "authority_classification": classification,
                "decision": decision,
                "public_safe": public_safe,
                "body_in_receipt": False,
            }
        )
    if imported_refs != required_import_refs:
        findings.append(
            _finding(
                "IMPORTED_MODULE_SET_MISMATCH",
                "Rows marked imported_public_body must match the copied evaluator source body set.",
                source=f"{CONTRACT_NAME}::finance_research_assurance.module_coverage",
                expected=sorted(required_import_refs),
                observed=sorted(imported_refs),
            )
        )
    surface_coverage = _as_dict(assurance_surface.get("module_coverage"))
    if surface_coverage.get("silent_omission_count") not in {0, None}:
        findings.append(
            _finding(
                "ASSURANCE_SURFACE_SILENT_OMISSIONS",
                "Finance assurance surface must not hide omitted macro finance modules.",
                source=f"{ASSURANCE_SURFACE_NAME}::module_coverage.silent_omission_count",
                expected=0,
                observed=surface_coverage.get("silent_omission_count"),
            )
        )
    total_count = len(expected_refs)
    silent_omission_count = len(missing_refs)
    return {
        "total_macro_finance_module_count": total_count,
        "covered_source_ref_count": len(observed_refs & expected_refs),
        "imported_public_body_count": status_counts.get("imported_public_body", 0),
        "deferred_public_safe_core_count": status_counts.get("deferred_public_safe_core", 0),
        "deferred_public_safe_statistical_count": status_counts.get(
            "deferred_public_safe_statistical", 0
        ),
        "operational_receipt_only_count": status_counts.get("operational_receipt_only", 0),
        "operational_only_count": status_counts.get("operational_only", 0),
        "silent_omission_count": silent_omission_count,
        "status_counts": dict(sorted(status_counts.items())),
        "classification_counts": dict(sorted(classification_counts.items())),
        "rows": rows_out,
        "body_in_receipt": False,
    }


def _validate_assurance_surface(
    assurance_surface: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_assurance_surface` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if assurance_surface.get("schema_version") != ASSURANCE_SURFACE_SCHEMA:
        findings.append(
            _finding(
                "UNEXPECTED_ASSURANCE_SURFACE_SCHEMA",
                "Finance assurance surface must use the assurance surface schema.",
                source=ASSURANCE_SURFACE_NAME,
                expected=ASSURANCE_SURFACE_SCHEMA,
                observed=assurance_surface.get("schema_version"),
            )
        )
    demo = _as_dict(assurance_surface.get("demonstration_run"))
    required_demo_counts = {
        "target_universe_count",
        "feed_freshness_state_count",
        "evidence_construction_path_count",
        "scoring_rule_count",
        "pairwise_comparison_count",
        "multiple_comparison_guard_count",
        "oracle_reconciliation_count",
        "evolve_decision_count",
        "no_advice_boundary_receipt_count",
    }
    demo_counts = _as_dict(demo.get("counts"))
    missing_non_empty = [
        key for key in sorted(required_demo_counts) if not demo_counts.get(key)
    ]
    if demo.get("public_safe_non_empty_fixture") is not True or missing_non_empty:
        findings.append(
            _finding(
                "ASSURANCE_DEMO_EMPTY_OR_INCOMPLETE",
                "Finance assurance surface must carry a non-empty public-safe demonstration run.",
                source=f"{ASSURANCE_SURFACE_NAME}::demonstration_run",
                expected=sorted(required_demo_counts),
                observed={"missing_or_zero": missing_non_empty},
            )
        )
    feed = _as_dict(assurance_surface.get("feed_freshness"))
    feed_state = feed.get("current_state")
    if feed_state not in FEED_FRESHNESS_STATUSES:
        findings.append(
            _finding(
                "FEED_FRESHNESS_STATE_UNKNOWN",
                "Finance assurance feed freshness state must use the public freshness vocabulary.",
                source=f"{ASSURANCE_SURFACE_NAME}::feed_freshness.current_state",
                expected=sorted(FEED_FRESHNESS_STATUSES),
                observed=feed_state,
            )
        )
    if feed_state == "stale_green_feed":
        latest_green = _as_dict(feed.get("latest_green_run"))
        if not latest_green.get("run_id") or not latest_green.get("staleness_days"):
            findings.append(
                _finding(
                    "STALE_GREEN_FEED_UNDATED",
                    "Stale green feed state must preserve the dated latest green run.",
                    source=f"{ASSURANCE_SURFACE_NAME}::feed_freshness.latest_green_run",
                    observed=latest_green,
                )
            )
    stats = _as_dict(assurance_surface.get("statistical_discipline"))
    sequence = tuple(_strings(stats.get("sequence")))
    if sequence != STATISTICAL_DISCIPLINE_SEQUENCE:
        findings.append(
            _finding(
                "STATISTICAL_DISCIPLINE_SEQUENCE_MISMATCH",
                "Finance assurance surface must order forecast evaluation from scoring to pairwise comparison to multiple-comparison guard to review-gated learning.",
                source=f"{ASSURANCE_SURFACE_NAME}::statistical_discipline.sequence",
                expected=list(STATISTICAL_DISCIPLINE_SEQUENCE),
                observed=list(sequence),
            )
        )
    evolve = _as_dict(_as_dict(assurance_surface.get("oracle_evolve")).get("evolve_decision"))
    if evolve.get("review_gated") is not True or evolve.get("auto_apply_allowed") is not False:
        findings.append(
            _finding(
                "EVOLVE_REVIEW_GATE_MISMATCH",
                "Finance assurance surface must keep Evolve review-gated and block auto-apply.",
                source=f"{ASSURANCE_SURFACE_NAME}::oracle_evolve.evolve_decision",
                expected={"review_gated": True, "auto_apply_allowed": False},
                observed=evolve,
            )
        )
    authority = _as_dict(assurance_surface.get("authority_boundary"))
    overclaims = {
        key: authority.get(key)
        for key in FALSE_AUTHORITY_FLAGS
        if authority.get(key) is not False
    }
    for key, value in overclaims.items():
        findings.append(
            _finding(
                "ASSURANCE_AUTHORITY_OVERCLAIM",
                "Finance assurance authority flag must be false.",
                source=f"{ASSURANCE_SURFACE_NAME}::authority_boundary.{key}",
                expected=False,
                observed=value,
            )
        )
    quant = _as_dict(assurance_surface.get("quant_research_experiment_spine"))
    quant_hypothesis = _as_dict(quant.get("hypothesis_ledger"))
    quant_anti_overfit = _as_dict(quant.get("anti_overfit_evaluator"))
    quant_comparison = _as_dict(quant.get("model_comparison_discipline"))
    quant_bridge = _as_dict(quant.get("oracle_evolve_bridge"))
    quant_no_advice = _as_dict(quant.get("no_advice_mode"))
    quant_registry = _quant_registry_summary(quant)
    quant_agenda = _quant_agenda_summary(quant)
    quant_cycle = _quant_execution_cycle_summary(quant)
    quant_output_state = str(quant_comparison.get("output_state") or "")
    required_quant_markers = {
        "hypothesis_ledger": bool(quant_hypothesis.get("experiment_id"))
        and bool(quant_hypothesis.get("public_safe_hypothesis")),
        "anti_overfit_evaluator": quant_anti_overfit.get("random_kfold_allowed") is False
        and bool(quant_anti_overfit.get("selection_bias_guard")),
        "model_comparison_discipline": quant_comparison.get("winner_language_allowed") is False
        and quant_output_state in QUANT_RESEARCH_OUTPUT_STATES,
        "oracle_evolve_bridge": quant_bridge.get("review_gated") is True
        and quant_bridge.get("auto_apply_allowed") is False,
        "no_advice_mode": quant_no_advice.get("enabled") is True
        and quant_no_advice.get("non_advisory_research_only") is True,
    }
    missing_quant_markers = [
        key for key, present in sorted(required_quant_markers.items()) if not present
    ]
    if quant.get("schema_version") != QUANT_RESEARCH_SPINE_SCHEMA or missing_quant_markers:
        findings.append(
            _finding(
                "QUANT_RESEARCH_SPINE_INCOMPLETE",
                "Finance assurance must include a non-advisory quant research experiment spine with hypothesis, anti-overfit, comparison, review gate, and no-advice markers.",
                source=f"{ASSURANCE_SURFACE_NAME}::quant_research_experiment_spine",
                expected={
                    "schema_version": QUANT_RESEARCH_SPINE_SCHEMA,
                    "markers": sorted(required_quant_markers),
                },
                observed={
                    "schema_version": quant.get("schema_version"),
                    "missing": missing_quant_markers,
                    "output_state": quant_output_state,
                },
            )
        )
    if not quant_registry["stress_validated"]:
        findings.append(
            _finding(
                "QUANT_RESEARCH_LINEAGE_INCOMPLETE",
                "Finance assurance must include a reusable experiment registry with at least one negative/insufficient public-safe stress case and closed authority gates.",
                source=f"{ASSURANCE_SURFACE_NAME}::quant_research_experiment_spine.experiment_registry",
                expected={
                    "minimum_registry_count": 2,
                    "negative_control_count": 1,
                    "negative_or_insufficient_count": 1,
                    "lineage_status": "stress_validated_public_demo",
                    "review_gated_all": True,
                    "auto_apply_allowed_any": False,
                    "winner_language_allowed_any": False,
                    "random_kfold_allowed_any": False,
                    "no_advice_enabled_all": True,
                },
                observed=quant_registry,
            )
        )
    if not quant_agenda["compiled"]:
        findings.append(
            _finding(
                "QUANT_RESEARCH_AGENDA_INCOMPLETE",
                "Finance assurance must compile a public-safe quant research agenda with selected, deferred, control, and needs-evidence candidates plus closed authority gates.",
                source=f"{ASSURANCE_SURFACE_NAME}::quant_research_experiment_spine.research_agenda",
                expected={
                    "schema_version": "finance_quant_research_agenda_v0",
                    "status": "compiled_public_safe",
                    "minimum_candidate_count": 4,
                    "selected_for_next_test_count": 1,
                    "deferred_data_snooping_count": 1,
                    "negative_or_control_candidate_count": 1,
                    "needs_more_evidence_count": 1,
                    "review_gated": True,
                    "auto_apply_allowed": False,
                    "winner_language_allowed": False,
                },
                observed=quant_agenda,
            )
        )
    if not quant_cycle["closed_loop"]:
        findings.append(
            _finding(
                "QUANT_RESEARCH_EXECUTION_CYCLE_INCOMPLETE",
                "Finance assurance must consume the selected agenda candidate through a locked pre-analysis plan, existing evaluator execution, registry update, family-memory update, agenda recompilation, and closed authority gates.",
                source=f"{ASSURANCE_SURFACE_NAME}::quant_research_experiment_spine.agenda_execution_cycle",
                expected={
                    "schema_version": "finance_quant_agenda_execution_cycle_v0",
                    "registered_before_execution": True,
                    "analysis_plan_locked": True,
                    "post_hoc_plan_mutation_allowed": False,
                    "used_existing_evaluator": True,
                    "registry_count_increases": True,
                    "agenda_recompile_status": "recompiled_after_cycle",
                    "review_gated": True,
                    "auto_apply_allowed": False,
                    "no_advice_enabled": True,
                },
                observed=quant_cycle,
            )
        )
    return {
        "schema_version": assurance_surface.get("schema_version"),
        "surface_id": assurance_surface.get("surface_id"),
        "public_safe_non_empty_fixture": demo.get("public_safe_non_empty_fixture"),
        "demo_counts": dict(demo_counts),
        "feed_freshness_state": feed_state,
        "latest_green_run_id": _get_path(feed, ("latest_green_run", "run_id")),
        "scheduled_shell_count": len(_as_list(feed.get("scheduled_shells"))),
        "statistical_discipline_sequence": list(sequence),
        "evolve_review_gated": evolve.get("review_gated"),
        "evolve_auto_apply_allowed": evolve.get("auto_apply_allowed"),
        "authority_overclaim_count": len(overclaims),
        "quant_research_experiment_spine": {
            "schema_version": quant.get("schema_version"),
            "status": quant.get("status"),
            "experiment_id": quant_hypothesis.get("experiment_id"),
            "hypothesis_type": quant_hypothesis.get("hypothesis_type"),
            "anti_overfit_status": quant_anti_overfit.get("status"),
            "selection_bias_guard": quant_anti_overfit.get("selection_bias_guard"),
            "model_comparison_output_state": quant_output_state,
            "review_gated": quant_bridge.get("review_gated"),
            "auto_apply_allowed": quant_bridge.get("auto_apply_allowed"),
            "no_advice_enabled": quant_no_advice.get("enabled"),
            "registry_count": quant_registry["registry_count"],
            "negative_control_count": quant_registry["negative_control_count"],
            "negative_or_insufficient_count": quant_registry[
                "negative_or_insufficient_count"
            ],
            "lineage_status": quant_registry["lineage_status"],
            "output_state_counts": quant_registry["output_state_counts"],
            "agenda_status": quant_agenda["status"],
            "agenda_candidate_count": quant_agenda["candidate_count"],
            "agenda_family_count": quant_agenda["family_count"],
            "agenda_selected_for_next_test_count": quant_agenda[
                "selected_for_next_test_count"
            ],
            "agenda_deferred_data_snooping_count": quant_agenda[
                "deferred_data_snooping_count"
            ],
            "agenda_negative_or_control_candidate_count": quant_agenda[
                "negative_or_control_candidate_count"
            ],
            "agenda_needs_more_evidence_count": quant_agenda["needs_more_evidence_count"],
            "agenda_completed_insufficient_evidence_count": quant_agenda[
                "completed_insufficient_evidence_count"
            ],
            "cycle_status": quant_cycle["execution_status"],
            "cycle_selected_candidate_id": quant_cycle["selected_candidate_id"],
            "cycle_pre_analysis_plan_id": quant_cycle["pre_analysis_plan_id"],
            "cycle_result_state": quant_cycle["result_state"],
            "cycle_registry_new_count": quant_cycle["new_registry_count"],
            "cycle_next_selected_candidate_id": quant_cycle["next_selected_candidate_id"],
        },
        "body_in_receipt": False,
    }


def _validate_operating_picture(
    operating_picture: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_operating_picture` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    quant = _as_dict(operating_picture.get("quant_research_experiment_spine"))
    quant_bridge = _as_dict(quant.get("oracle_evolve_bridge"))
    quant_no_advice = _as_dict(quant.get("no_advice_mode"))
    quant_registry = _quant_registry_summary(quant)
    quant_agenda = _quant_agenda_summary(quant)
    quant_cycle = _quant_execution_cycle_summary(quant)
    if quant.get("schema_version") != QUANT_RESEARCH_SPINE_SCHEMA:
        findings.append(
            _finding(
                "OPERATING_PICTURE_QUANT_RESEARCH_SPINE_MISSING",
                "Finance eval operating picture must expose the quant research experiment spine projection.",
                source=f"{OPERATING_PICTURE_NAME}::quant_research_experiment_spine",
                expected=QUANT_RESEARCH_SPINE_SCHEMA,
                observed=quant.get("schema_version"),
            )
        )
    if quant_bridge.get("review_gated") is not True or quant_bridge.get("auto_apply_allowed") is not False:
        findings.append(
            _finding(
                "OPERATING_PICTURE_QUANT_EVOLVE_GATE_OPEN",
                "Quant research experiment spine must remain review-gated and deny auto-apply.",
                source=f"{OPERATING_PICTURE_NAME}::quant_research_experiment_spine.oracle_evolve_bridge",
                expected={"review_gated": True, "auto_apply_allowed": False},
                observed=quant_bridge,
            )
        )
    if quant_no_advice.get("enabled") is not True or quant_no_advice.get("non_advisory_research_only") is not True:
        findings.append(
            _finding(
                "OPERATING_PICTURE_QUANT_NO_ADVICE_MISSING",
                "Quant research experiment spine must remain non-advisory research only.",
                source=f"{OPERATING_PICTURE_NAME}::quant_research_experiment_spine.no_advice_mode",
                expected={"enabled": True, "non_advisory_research_only": True},
                observed=quant_no_advice,
            )
        )
    if not quant_registry["stress_validated"]:
        findings.append(
            _finding(
                "OPERATING_PICTURE_QUANT_LINEAGE_INCOMPLETE",
                "Finance eval operating picture must expose repeatable quant experiment lineage with a negative/insufficient stress case.",
                source=f"{OPERATING_PICTURE_NAME}::quant_research_experiment_spine.experiment_registry",
                expected={
                    "minimum_registry_count": 2,
                    "negative_control_count": 1,
                    "negative_or_insufficient_count": 1,
                    "lineage_status": "stress_validated_public_demo",
                },
                observed=quant_registry,
            )
        )
    if not quant_agenda["compiled"]:
        findings.append(
            _finding(
                "OPERATING_PICTURE_QUANT_AGENDA_INCOMPLETE",
                "Finance eval operating picture must expose the quant research agenda compiler with selection-budget discipline.",
                source=f"{OPERATING_PICTURE_NAME}::quant_research_experiment_spine.research_agenda",
                expected={
                    "minimum_candidate_count": 4,
                    "selected_for_next_test_count": 1,
                    "deferred_data_snooping_count": 1,
                    "negative_or_control_candidate_count": 1,
                    "needs_more_evidence_count": 1,
                },
                observed=quant_agenda,
            )
        )
    if not quant_cycle["closed_loop"]:
        findings.append(
            _finding(
                "OPERATING_PICTURE_QUANT_EXECUTION_CYCLE_INCOMPLETE",
                "Finance eval operating picture must expose the selected-agenda-to-experiment cycle with pre-analysis registration, evaluator execution, registry update, family-memory update, and agenda recompilation.",
                source=f"{OPERATING_PICTURE_NAME}::quant_research_experiment_spine.agenda_execution_cycle",
                expected={
                    "schema_version": "finance_quant_agenda_execution_cycle_v0",
                    "registered_before_execution": True,
                    "analysis_plan_locked": True,
                    "used_existing_evaluator": True,
                    "agenda_recompile_status": "recompiled_after_cycle",
                    "review_gated": True,
                    "auto_apply_allowed": False,
                    "no_advice_enabled": True,
                },
                observed=quant_cycle,
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
        "quant_research_experiment_spine": {
            "schema_version": quant.get("schema_version"),
            "status": quant.get("status"),
            "model_comparison_output_state": _get_path(
                quant, ("model_comparison", "output_state")
            ),
            "review_gated": quant_bridge.get("review_gated"),
            "auto_apply_allowed": quant_bridge.get("auto_apply_allowed"),
            "no_advice_enabled": quant_no_advice.get("enabled"),
            "registry_count": quant_registry["registry_count"],
            "negative_control_count": quant_registry["negative_control_count"],
            "negative_or_insufficient_count": quant_registry[
                "negative_or_insufficient_count"
            ],
            "lineage_status": quant_registry["lineage_status"],
            "output_state_counts": quant_registry["output_state_counts"],
            "agenda_status": quant_agenda["status"],
            "agenda_candidate_count": quant_agenda["candidate_count"],
            "agenda_family_count": quant_agenda["family_count"],
            "agenda_selected_for_next_test_count": quant_agenda[
                "selected_for_next_test_count"
            ],
            "agenda_deferred_data_snooping_count": quant_agenda[
                "deferred_data_snooping_count"
            ],
            "agenda_negative_or_control_candidate_count": quant_agenda[
                "negative_or_control_candidate_count"
            ],
            "agenda_needs_more_evidence_count": quant_agenda["needs_more_evidence_count"],
            "agenda_completed_insufficient_evidence_count": quant_agenda[
                "completed_insufficient_evidence_count"
            ],
            "cycle_status": quant_cycle["execution_status"],
            "cycle_selected_candidate_id": quant_cycle["selected_candidate_id"],
            "cycle_pre_analysis_plan_id": quant_cycle["pre_analysis_plan_id"],
            "cycle_result_state": quant_cycle["result_state"],
            "cycle_registry_new_count": quant_cycle["new_registry_count"],
            "cycle_next_selected_candidate_id": quant_cycle["next_selected_candidate_id"],
        },
        "body_in_receipt": False,
    }


def _scan_required_inputs(
    input_dir: Path, *, public_root: Path, findings: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_scan_required_inputs` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `validate_finance_eval_bundle` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
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
    assurance_surface = _load_json_input(
        input_path / ASSURANCE_SURFACE_NAME,
        findings,
        label="finance research assurance surface",
    )

    source_inventory = _source_manifest(input_path, manifest, public_root=public_root)
    _validate_manifest(manifest, source_manifest_payload, findings)
    _validate_digests(source_inventory, findings)
    anchor_summary = _validate_source_anchors(input_path, findings)
    contract_summary = _validate_contract(contract, findings)
    module_coverage_summary = _validate_module_coverage(
        contract, assurance_surface, findings
    )
    assurance_surface_summary = _validate_assurance_surface(assurance_surface, findings)
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
        "module_coverage_summary": module_coverage_summary,
        "finance_research_assurance": assurance_surface_summary,
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
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.macro_tools.finance_eval_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
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
    "TOOLS_FINANCE_MODULES",
    "validate_finance_eval_bundle",
]
