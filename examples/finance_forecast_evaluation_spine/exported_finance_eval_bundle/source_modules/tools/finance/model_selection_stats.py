"""
[PURPOSE]
- Teleology: Provide sample-gated family-level statistical blocks for finance
  model-selection receipts without granting optimizer or calculator mutation.
- Mechanism: Convert a finance family loss matrix into candidate-minus-baseline
  loss differentials and run a deterministic stationary-bootstrap Reality
  Check summary when sample gates pass.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import math
import random
from typing import Any, Mapping, Optional, Sequence

from tools.finance.family_loss_matrix import BOOTSTRAP_METHOD_STATIONARY
from tools.finance.loss_differentials import hac_long_run_variance

MODEL_SELECTION_STATS_AUTHORITY = "tools/finance/model_selection_stats.py"
DEFAULT_BOOTSTRAP_REPS = 1000
DEFAULT_BOOTSTRAP_SEED = 1729
DEFAULT_MIN_BOOTSTRAP_SAMPLE = 30
DEFAULT_MCS_ALPHA = 0.10
BOOTSTRAP_CONFORMANCE_SCHEMA = "finance_bootstrap_conformance_v0"
MODEL_CONFIDENCE_SET_SCHEMA = "finance_model_confidence_set_v0"
REALITY_CHECK_STATISTIC = "max_positive_baseline_improvement"
MCS_STATISTIC = "tmax_sequential_elimination"
LOSS_ORIENTATION = "candidate_minus_baseline_lower_is_better"
CENTERING_CONVENTION = "candidate_loss_differentials_centered_by_candidate_mean"
EVIDENCE_ONLY_AUTHORITY = "evidence_only_no_mutation_permission"


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def bootstrap_p_value_resolution(p_value: Optional[float], bootstrap_reps: int) -> dict[str, Any]:
    if p_value is None or bootstrap_reps <= 0:
        return {
            "status": "not_available",
            "bootstrap_reps": bootstrap_reps,
            "zero_exceedance": None,
            "resolution_floor": None,
        }
    floor = 1.0 / float(bootstrap_reps)
    zero_exceedance = float(p_value) == 0.0
    return {
        "status": "zero_exceedance_floor" if zero_exceedance else "resolved_fraction",
        "bootstrap_reps": bootstrap_reps,
        "zero_exceedance": zero_exceedance,
        "resolution_floor": round(floor, 10),
        "display": f"<{floor:.10g}" if zero_exceedance else round(float(p_value), 10),
    }


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def loss_differential_matrix(family_loss_matrix: Mapping[str, Any]) -> dict[str, list[float]]:
    baseline_id = _as_text(family_loss_matrix.get("baseline_variant_id"))
    candidate_ids = [_as_text(value) for value in family_loss_matrix.get("candidate_variant_ids", []) if _as_text(value)]
    rows = [row for row in family_loss_matrix.get("rows", []) if isinstance(row, Mapping)]
    matrix: dict[str, list[float]] = {candidate_id: [] for candidate_id in candidate_ids}
    for row in rows:
        losses = row.get("losses") if isinstance(row.get("losses"), Mapping) else {}
        baseline_loss = _as_float(losses.get(baseline_id))
        if baseline_loss is None:
            continue
        for candidate_id in candidate_ids:
            candidate_loss = _as_float(losses.get(candidate_id))
            if candidate_loss is None:
                continue
            matrix[candidate_id].append(candidate_loss - baseline_loss)
    return matrix


def _stationary_bootstrap_indices(
    sample_size: int,
    *,
    block_length: int,
    reps: int,
    seed: int,
) -> list[list[int]]:
    if sample_size <= 0 or reps <= 0:
        return []
    rng = random.Random(seed)
    selected_block_length = max(int(block_length), 1)
    restart_probability = 1.0 / selected_block_length
    all_indices: list[list[int]] = []
    for _ in range(reps):
        index = rng.randrange(sample_size)
        sample: list[int] = []
        for _position in range(sample_size):
            if sample and rng.random() < restart_probability:
                index = rng.randrange(sample_size)
            sample.append(index)
            index = (index + 1) % sample_size
        all_indices.append(sample)
    return all_indices


def stationary_bootstrap_indices(
    sample_size: int,
    *,
    block_length: int,
    reps: int,
    seed: int,
) -> list[list[int]]:
    return _stationary_bootstrap_indices(sample_size, block_length=block_length, reps=reps, seed=seed)


def _best_improvement(mean_deltas: Mapping[str, float]) -> tuple[Optional[str], Optional[float], float]:
    if not mean_deltas:
        return None, None, 0.0
    best_variant_id, best_delta = min(mean_deltas.items(), key=lambda item: item[1])
    return best_variant_id, best_delta, max(0.0, -best_delta)


def centered_loss_differentials(matrix: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    centered: dict[str, list[float]] = {}
    for candidate_id, deltas in matrix.items():
        mean_delta = _mean(list(deltas))
        if mean_delta is None:
            continue
        centered[candidate_id] = [delta - mean_delta for delta in deltas]
    return centered


def _centered_mean_abs_max(centered: Mapping[str, Sequence[float]]) -> Optional[float]:
    means = [abs(float(_mean(list(values)) or 0.0)) for values in centered.values() if values]
    return max(means) if means else None


def _model_loss_matrix(family_loss_matrix: Mapping[str, Any]) -> dict[str, list[float]]:
    baseline_id = _as_text(family_loss_matrix.get("baseline_variant_id"))
    candidate_ids = [_as_text(value) for value in family_loss_matrix.get("candidate_variant_ids", []) if _as_text(value)]
    model_ids = [model_id for model_id in [baseline_id, *candidate_ids] if model_id]
    rows = [row for row in family_loss_matrix.get("rows", []) if isinstance(row, Mapping)]
    matrix: dict[str, list[float]] = {model_id: [] for model_id in model_ids}
    for row in rows:
        losses = row.get("losses") if isinstance(row.get("losses"), Mapping) else {}
        if not all(isinstance(losses.get(model_id), (int, float)) for model_id in model_ids):
            continue
        for model_id in model_ids:
            matrix[model_id].append(float(losses[model_id]))
    sample_size = len(rows)
    return {model_id: values for model_id, values in matrix.items() if len(values) == sample_size and sample_size > 0}


def _average_loss_difference_series(
    losses: Mapping[str, Sequence[float]],
    active_model_ids: Sequence[str],
) -> dict[str, list[float]]:
    active_ids = [model_id for model_id in active_model_ids if model_id in losses]
    if not active_ids:
        return {}
    sample_size = len(next(iter(losses.values())))
    series: dict[str, list[float]] = {model_id: [] for model_id in active_ids}
    for index in range(sample_size):
        average_loss = sum(float(losses[model_id][index]) for model_id in active_ids) / len(active_ids)
        for model_id in active_ids:
            series[model_id].append(float(losses[model_id][index]) - average_loss)
    return series


def _mcs_step_statistics(
    losses: Mapping[str, Sequence[float]],
    active_model_ids: Sequence[str],
    *,
    block_length: int,
    bootstrap_reps: int,
    seed: int,
) -> dict[str, Any]:
    active_ids = [model_id for model_id in active_model_ids if model_id in losses]
    sample_size = len(next(iter(losses.values()))) if losses else 0
    if len(active_ids) < 2 or sample_size <= 0:
        return {
            "status": "not_computed_insufficient_active_set",
            "active_model_ids": active_ids,
            "sample_size": sample_size,
        }

    lag = max(int(block_length or 1) - 1, 0)
    difference_series = _average_loss_difference_series(losses, active_ids)
    candidate_stats: dict[str, dict[str, Any]] = {}
    centered_series: dict[str, list[float]] = {}
    denominator_by_model: dict[str, float] = {}
    for model_id in active_ids:
        series = difference_series[model_id]
        mean_difference = float(_mean(series) or 0.0)
        variance = hac_long_run_variance(series, lag=lag)
        stderr = variance.get("standard_error_mean")
        if isinstance(stderr, (int, float)) and float(stderr) > 0.0:
            statistic = mean_difference / float(stderr)
            denominator = float(stderr)
            status = "studentized"
        elif abs(mean_difference) <= 1e-15:
            statistic = 0.0
            denominator = 1.0
            status = "zero_variance_tie"
        else:
            statistic = math.inf if mean_difference > 0.0 else -math.inf
            denominator = 1.0
            status = "zero_variance_directional"
        candidate_stats[model_id] = {
            "status": status,
            "mean_loss_relative_to_active_average": round(mean_difference, 10),
            "long_run_variance": variance.get("long_run_variance"),
            "standard_error_mean": round(float(stderr), 10) if isinstance(stderr, (int, float)) else None,
            "t_statistic": round(statistic, 10) if math.isfinite(statistic) else ("inf" if statistic > 0 else "-inf"),
        }
        denominator_by_model[model_id] = denominator
        centered_series[model_id] = [float(value) - mean_difference for value in series]

    observed_statistics = {
        model_id: (
            math.inf
            if candidate_stats[model_id]["t_statistic"] == "inf"
            else -math.inf
            if candidate_stats[model_id]["t_statistic"] == "-inf"
            else float(candidate_stats[model_id]["t_statistic"])
        )
        for model_id in active_ids
    }
    observed_statistic = max(observed_statistics.values())
    worst_model_id = max(active_ids, key=lambda model_id: observed_statistics[model_id])
    bootstrap_indices = _stationary_bootstrap_indices(
        sample_size,
        block_length=max(int(block_length or 1), 1),
        reps=bootstrap_reps,
        seed=seed,
    )
    bootstrap_statistics: list[float] = []
    for indices in bootstrap_indices:
        replicate_stats: list[float] = []
        for model_id in active_ids:
            replicate_mean = sum(centered_series[model_id][index] for index in indices) / len(indices)
            denominator = denominator_by_model.get(model_id) or 1.0
            replicate_stats.append(replicate_mean / denominator)
        bootstrap_statistics.append(max(replicate_stats) if replicate_stats else 0.0)
    p_value = None
    if bootstrap_statistics and math.isfinite(observed_statistic):
        p_value = sum(1 for statistic in bootstrap_statistics if statistic >= observed_statistic) / len(bootstrap_statistics)
    elif bootstrap_statistics and observed_statistic == math.inf:
        p_value = 0.0

    return {
        "status": "computed_bootstrap",
        "active_model_ids": active_ids,
        "sample_size": sample_size,
        "block_length": max(int(block_length or 1), 1),
        "lag": lag,
        "observed_statistic": round(observed_statistic, 10) if math.isfinite(observed_statistic) else ("inf" if observed_statistic > 0 else "-inf"),
        "p_value": round(float(p_value), 10) if p_value is not None else None,
        "p_value_resolution": bootstrap_p_value_resolution(p_value, len(bootstrap_statistics)),
        "elimination_model_id": worst_model_id,
        "candidate_statistics": candidate_stats,
    }


def _conformance_status(status: str, *, sample_size: int, minimum_sample: int) -> str:
    if status == "computed_bootstrap":
        return "pass"
    if status == "not_computed_minimum_sample" or sample_size < minimum_sample:
        return "sample_gated"
    return "blocked"


def bootstrap_conformance_receipt(
    *,
    status: str,
    sample_size: int,
    minimum_sample: int,
    bootstrap_reps: int,
    seed: int,
    block_length: Optional[int],
    centered_mean_abs_max: Optional[float] = None,
) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_CONFORMANCE_SCHEMA,
        "status": _conformance_status(status, sample_size=sample_size, minimum_sample=minimum_sample),
        "statistic": REALITY_CHECK_STATISTIC,
        "loss_orientation": LOSS_ORIENTATION,
        "centering": CENTERING_CONVENTION,
        "replicate_statistic": "max(0, -min(centered_replicate_mean_delta_i))",
        "resampling": {
            "method": BOOTSTRAP_METHOD_STATIONARY,
            "seed": seed,
            "bootstrap_reps": bootstrap_reps,
            "block_length": block_length,
        },
        "sample_gate": {
            "minimum_sample": minimum_sample,
            "sample_size": sample_size,
            "passed": sample_size >= minimum_sample,
        },
        "null": "no_candidate_outperforms_baseline",
        "centered_series_mean_abs_max": round(centered_mean_abs_max, 12) if centered_mean_abs_max is not None else None,
        "decision_authority": EVIDENCE_ONLY_AUTHORITY,
    }


def blocked_reality_check(
    *,
    status: str,
    reason: str,
    sample_size: int,
    minimum_sample: int,
    bootstrap_reps: int,
    seed: int,
    block_length: Optional[int] = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "implemented": False,
        "authority": MODEL_SELECTION_STATS_AUTHORITY,
        "bootstrap_method": BOOTSTRAP_METHOD_STATIONARY,
        "bootstrap_reps": bootstrap_reps,
        "seed": seed,
        "minimum_sample": minimum_sample,
        "sample_size": sample_size,
        "null": "no_candidate_outperforms_baseline",
        "best_observed_mean_delta": None,
        "best_observed_variant_id": None,
        "observed_statistic": None,
        "p_value": None,
        "reason": reason,
        "bootstrap_conformance": bootstrap_conformance_receipt(
            status=status,
            sample_size=sample_size,
            minimum_sample=minimum_sample,
            bootstrap_reps=bootstrap_reps,
            seed=seed,
            block_length=block_length,
        ),
    }


def reality_check_summary(
    family_loss_matrix: Mapping[str, Any],
    *,
    min_sample: int = DEFAULT_MIN_BOOTSTRAP_SAMPLE,
    bootstrap_reps: int = DEFAULT_BOOTSTRAP_REPS,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    allow_tiny_sample: bool = False,
) -> dict[str, Any]:
    rows = [row for row in family_loss_matrix.get("rows", []) if isinstance(row, Mapping)]
    sample_size = len(rows)
    if sample_size <= 0:
        return blocked_reality_check(
            status="not_computed_empty_matrix",
            reason="family_loss_matrix_empty",
            sample_size=sample_size,
            minimum_sample=min_sample,
            bootstrap_reps=bootstrap_reps,
            seed=seed,
            block_length=None,
        )
    if sample_size < min_sample and not allow_tiny_sample:
        block_length = int((family_loss_matrix.get("dependence_diagnostics") or {}).get("recommended_block_length") or 1)
        return blocked_reality_check(
            status="not_computed_minimum_sample",
            reason="minimum_sample_not_met",
            sample_size=sample_size,
            minimum_sample=min_sample,
            bootstrap_reps=bootstrap_reps,
            seed=seed,
            block_length=block_length,
        )
    matrix = loss_differential_matrix(family_loss_matrix)
    matrix = {candidate_id: deltas for candidate_id, deltas in matrix.items() if len(deltas) == sample_size}
    if not matrix:
        return blocked_reality_check(
            status="not_computed_no_complete_candidate_series",
            reason="no_complete_candidate_series",
            sample_size=sample_size,
            minimum_sample=min_sample,
            bootstrap_reps=bootstrap_reps,
            seed=seed,
            block_length=int((family_loss_matrix.get("dependence_diagnostics") or {}).get("recommended_block_length") or 1),
        )
    mean_deltas = {candidate_id: float(_mean(deltas)) for candidate_id, deltas in matrix.items() if _mean(deltas) is not None}
    best_variant_id, best_delta, observed_statistic = _best_improvement(mean_deltas)
    block_length = int((family_loss_matrix.get("dependence_diagnostics") or {}).get("recommended_block_length") or 1)
    bootstrap_indices = _stationary_bootstrap_indices(
        sample_size,
        block_length=block_length,
        reps=bootstrap_reps,
        seed=seed,
    )
    centered = centered_loss_differentials({candidate_id: deltas for candidate_id, deltas in matrix.items() if candidate_id in mean_deltas})
    bootstrap_stats: list[float] = []
    for indices in bootstrap_indices:
        replicate_means = {
            candidate_id: sum(values[index] for index in indices) / len(indices)
            for candidate_id, values in centered.items()
        }
        _variant_id, _delta, statistic = _best_improvement(replicate_means)
        bootstrap_stats.append(statistic)
    p_value = None
    if bootstrap_stats:
        p_value = sum(1 for statistic in bootstrap_stats if statistic >= observed_statistic) / len(bootstrap_stats)
    return {
        "status": "computed_bootstrap",
        "implemented": True,
        "authority": MODEL_SELECTION_STATS_AUTHORITY,
        "bootstrap_method": BOOTSTRAP_METHOD_STATIONARY,
        "bootstrap_reps": bootstrap_reps,
        "seed": seed,
        "minimum_sample": min_sample,
        "sample_size": sample_size,
        "block_length": block_length,
        "null": "no_candidate_outperforms_baseline",
        "best_observed_mean_delta": round(best_delta, 10) if best_delta is not None else None,
        "best_observed_variant_id": best_variant_id,
        "observed_statistic": round(observed_statistic, 10),
        "p_value": round(float(p_value), 10) if p_value is not None else None,
        "p_value_resolution": bootstrap_p_value_resolution(p_value, len(bootstrap_stats)),
        "candidate_mean_deltas": {candidate_id: round(value, 10) for candidate_id, value in sorted(mean_deltas.items())},
        "bootstrap_conformance": bootstrap_conformance_receipt(
            status="computed_bootstrap",
            sample_size=sample_size,
            minimum_sample=min_sample,
            bootstrap_reps=bootstrap_reps,
            seed=seed,
            block_length=block_length,
            centered_mean_abs_max=_centered_mean_abs_max(centered),
        ),
    }


def model_confidence_set_summary(
    family_loss_matrix: Optional[Mapping[str, Any]] = None,
    *,
    candidate_variant_ids: Sequence[str],
    blocked_status: Optional[str] = None,
    min_sample: int = DEFAULT_MIN_BOOTSTRAP_SAMPLE,
    bootstrap_reps: int = DEFAULT_BOOTSTRAP_REPS,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    alpha: float = DEFAULT_MCS_ALPHA,
    allow_tiny_sample: bool = False,
) -> dict[str, Any]:
    if blocked_status:
        return {
            "status": blocked_status,
            "implemented": False,
            "authority": MODEL_SELECTION_STATS_AUTHORITY,
            "schema_version": MODEL_CONFIDENCE_SET_SCHEMA,
            "retained_variants": [],
            "reason": "family_contract_blocker_prevents_mcs",
        }
    matrix = family_loss_matrix if isinstance(family_loss_matrix, Mapping) else {}
    rows = [row for row in matrix.get("rows", []) if isinstance(row, Mapping)]
    sample_size = len(rows)
    baseline_id = _as_text(matrix.get("baseline_variant_id"))
    candidate_ids = [_as_text(value) for value in candidate_variant_ids if _as_text(value)]
    model_ids = [model_id for model_id in [baseline_id, *candidate_ids] if model_id]
    if len(candidate_ids) < 2:
        return {
            "schema_version": MODEL_CONFIDENCE_SET_SCHEMA,
            "status": "not_computed_insufficient_variant_family",
            "implemented": False,
            "authority": MODEL_SELECTION_STATS_AUTHORITY,
            "retained_variants": model_ids,
            "reason": "insufficient_variant_family",
            "minimum_candidate_count": 2,
            "candidate_count": len(candidate_ids),
        }
    if sample_size < min_sample and not allow_tiny_sample:
        return {
            "schema_version": MODEL_CONFIDENCE_SET_SCHEMA,
            "status": "not_computed_minimum_sample",
            "implemented": False,
            "authority": MODEL_SELECTION_STATS_AUTHORITY,
            "retained_variants": model_ids,
            "reason": "minimum_sample_not_met",
            "minimum_sample": min_sample,
            "sample_size": sample_size,
        }
    losses = _model_loss_matrix(matrix)
    if len(losses) != len(model_ids):
        return {
            "schema_version": MODEL_CONFIDENCE_SET_SCHEMA,
            "status": "not_computed_incomplete_model_loss_matrix",
            "implemented": False,
            "authority": MODEL_SELECTION_STATS_AUTHORITY,
            "retained_variants": list(losses),
            "reason": "incomplete_model_loss_matrix",
            "expected_model_ids": model_ids,
            "complete_model_ids": sorted(losses),
        }
    diagnostics = matrix.get("dependence_diagnostics") if isinstance(matrix.get("dependence_diagnostics"), Mapping) else {}
    block_length = max(int(diagnostics.get("recommended_block_length") or 1), 1)
    active = list(model_ids)
    eliminated: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    step_index = 0
    while len(active) > 1:
        step_index += 1
        step = _mcs_step_statistics(
            losses,
            active,
            block_length=block_length,
            bootstrap_reps=bootstrap_reps,
            seed=seed + step_index - 1,
        )
        public_step = {
            key: value
            for key, value in step.items()
            if key != "candidate_statistics"
        }
        public_step["step"] = step_index
        public_step["candidate_statistics"] = step.get("candidate_statistics", {})
        steps.append(public_step)
        if step.get("status") != "computed_bootstrap":
            return {
                "schema_version": MODEL_CONFIDENCE_SET_SCHEMA,
                "status": step.get("status", "not_computed"),
                "implemented": True,
                "authority": MODEL_SELECTION_STATS_AUTHORITY,
                "retained_variants": active,
                "eliminated_variants": eliminated,
                "steps": steps,
                "reason": "mcs_step_not_computed",
                "decision_authority": EVIDENCE_ONLY_AUTHORITY,
            }
        p_value = _as_float(step.get("p_value"))
        if p_value is not None and p_value < alpha and len(active) > 1:
            eliminated_model_id = _as_text(step.get("elimination_model_id"))
            eliminated.append(
                {
                    "step": step_index,
                    "variant_id": eliminated_model_id,
                    "p_value": p_value,
                    "p_value_resolution": step.get("p_value_resolution"),
                    "observed_statistic": step.get("observed_statistic"),
                    "reason": "equal_predictive_ability_rejected_for_active_set",
                }
            )
            active = [model_id for model_id in active if model_id != eliminated_model_id]
            continue
        break

    return {
        "schema_version": MODEL_CONFIDENCE_SET_SCHEMA,
        "status": "computed_bootstrap",
        "implemented": True,
        "authority": MODEL_SELECTION_STATS_AUTHORITY,
        "statistic": MCS_STATISTIC,
        "loss_orientation": "lower_loss_is_better",
        "equal_predictive_ability_null": "active_models_have_equal_predictive_ability",
        "alpha": alpha,
        "confidence_level": round(1.0 - alpha, 10),
        "bootstrap_method": BOOTSTRAP_METHOD_STATIONARY,
        "bootstrap_reps": bootstrap_reps,
        "seed": seed,
        "minimum_sample": min_sample,
        "sample_size": sample_size,
        "block_length": block_length,
        "initial_variants": model_ids,
        "retained_variants": active,
        "eliminated_variants": eliminated,
        "step_count": len(steps),
        "steps": steps,
        "decision_authority": EVIDENCE_ONLY_AUTHORITY,
    }


def spa_readiness_summary(
    family_loss_matrix: Mapping[str, Any],
    *,
    reality_check_status: str,
    min_sample: int,
    blocked_status: Optional[str] = None,
    spa_block: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    rows = [row for row in family_loss_matrix.get("rows", []) if isinstance(row, Mapping)]
    sample_size = len(rows)
    matrix = loss_differential_matrix(family_loss_matrix)
    mean_deltas = {
        candidate_id: float(_mean(deltas))
        for candidate_id, deltas in matrix.items()
        if deltas and _mean(deltas) is not None
    }
    poor_or_irrelevant_ids = [
        candidate_id
        for candidate_id, mean_delta in sorted(mean_deltas.items())
        if mean_delta >= 0.0
    ]
    spa_status = _as_text(spa_block.get("status")) if isinstance(spa_block, Mapping) else ""
    if blocked_status:
        status = "blocked"
        reason = "family_contract_blocker_prevents_spa"
    elif sample_size < min_sample:
        status = "blocked"
        reason = "minimum_sample_not_met"
    elif len(matrix) < 2:
        status = "blocked"
        reason = "insufficient_variant_family"
    elif spa_status == "computed_bootstrap":
        status = "reserved_ready"
        reason = "SPA kernel computed evidence-only statistic"
    elif spa_status == "not_computed_no_studentization":
        status = "blocked"
        reason = "no_candidate_passed_studentization"
    elif spa_status:
        status = "reserved_ready"
        reason = "SPA kernel available but statistic did not compute"
    else:
        status = "reserved_ready"
        reason = "SPA requires studentization and sample-dependent null implementation"
    studentization = spa_block.get("studentization") if isinstance(spa_block, Mapping) and isinstance(spa_block.get("studentization"), Mapping) else {}
    sample_dependent_null = (
        spa_block.get("sample_dependent_null")
        if isinstance(spa_block, Mapping) and isinstance(spa_block.get("sample_dependent_null"), Mapping)
        else {}
    )
    studentized_available = bool(spa_status and not blocked_status and spa_status != "blocked")
    sample_dependent_available = bool(spa_status and not blocked_status and sample_dependent_null)
    return {
        "status": status,
        "authority": MODEL_SELECTION_STATS_AUTHORITY,
        "reality_check_status": reality_check_status,
        "poor_or_irrelevant_alternative_count": len(poor_or_irrelevant_ids),
        "poor_or_irrelevant_alternative_ids": poor_or_irrelevant_ids,
        "studentized_loss_differentials_available": studentized_available,
        "sample_dependent_null_available": sample_dependent_available,
        "studentized_candidate_count": int(studentization.get("studentized_candidate_count") or 0),
        "dropped_zero_variance_count": int(studentization.get("dropped_zero_variance_count") or 0),
        "spa_status": spa_status or "reserved",
        "sample_size": sample_size,
        "minimum_sample": min_sample,
        "candidate_count": len(matrix),
        "candidate_mean_deltas": {
            candidate_id: round(mean_delta, 10)
            for candidate_id, mean_delta in sorted(mean_deltas.items())
        },
        "reason": reason,
    }
