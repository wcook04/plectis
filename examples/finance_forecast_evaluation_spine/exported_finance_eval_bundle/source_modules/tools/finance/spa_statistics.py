"""
[PURPOSE]
- Teleology: Compute a sample-gated, studentized Hansen-SPA-style statistic
  block for finance model-selection receipts without granting optimizer or
  calculator mutation permission.
- Mechanism: Consume finance_family_loss_matrix_v0, build candidate-minus-
  baseline loss differentials, estimate HAC/Bartlett long-run variance per
  candidate, and run stationary-bootstrap replicates over centered series.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional, Sequence

from tools.finance.family_loss_matrix import BOOTSTRAP_METHOD_STATIONARY
from tools.finance.loss_differentials import (
    VARIANCE_ESTIMATOR_HAC_BARTLETT,
    hac_long_run_variance,
)
from tools.finance.model_selection_stats import (
    DEFAULT_BOOTSTRAP_REPS,
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_MIN_BOOTSTRAP_SAMPLE,
    EVIDENCE_ONLY_AUTHORITY,
    LOSS_ORIENTATION,
    bootstrap_p_value_resolution,
    loss_differential_matrix,
    stationary_bootstrap_indices,
)

SPA_STATISTIC_SCHEMA = "finance_spa_statistic_v0"
SPA_STATISTICS_AUTHORITY = "tools/finance/spa_statistics.py"
SPA_NULL = "no_candidate_has_superior_predictive_ability"
SPA_SAMPLE_DEPENDENT_NULL_METHOD = "hansen_spa_reserved_implementation_v0"
DEFAULT_VARIANCE_FLOOR = 1e-12


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _sample_size(family_loss_matrix: Mapping[str, Any]) -> int:
    rows = family_loss_matrix.get("rows")
    return len(rows) if isinstance(rows, list) else 0


def _block_length(family_loss_matrix: Mapping[str, Any]) -> int:
    diagnostics = (
        family_loss_matrix.get("dependence_diagnostics")
        if isinstance(family_loss_matrix.get("dependence_diagnostics"), Mapping)
        else {}
    )
    try:
        return max(int(diagnostics.get("recommended_block_length") or 1), 1)
    except (TypeError, ValueError):
        return 1


def _complete_loss_matrix(family_loss_matrix: Mapping[str, Any]) -> dict[str, list[float]]:
    sample_size = _sample_size(family_loss_matrix)
    matrix = loss_differential_matrix(family_loss_matrix)
    return {
        candidate_id: [float(value) for value in deltas]
        for candidate_id, deltas in matrix.items()
        if len(deltas) == sample_size and sample_size > 0
    }


def _empty_spa_block(
    *,
    status: str,
    reason: str,
    sample_size: int,
    min_sample: int,
    bootstrap_reps: int,
    seed: int,
    block_length: Optional[int],
    variance_floor: float,
    poor_or_irrelevant_ids: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    poor_ids = list(poor_or_irrelevant_ids or [])
    return {
        "schema_version": SPA_STATISTIC_SCHEMA,
        "status": status,
        "implemented": status == "not_computed_minimum_sample",
        "authority": SPA_STATISTICS_AUTHORITY,
        "null": SPA_NULL,
        "loss_orientation": LOSS_ORIENTATION,
        "studentization": {
            "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
            "minimum_variance_floor": variance_floor,
            "studentized_candidate_count": 0,
            "dropped_zero_variance_count": 0,
            "dropped_incomplete_series_count": 0,
            "lag": max(int(block_length or 1) - 1, 0),
            "candidate_statistics": {},
        },
        "sample_dependent_null": {
            "method": SPA_SAMPLE_DEPENDENT_NULL_METHOD,
            "poor_or_irrelevant_alternative_count": len(poor_ids),
            "poor_or_irrelevant_alternative_ids": poor_ids,
            "included_candidate_count": 0,
            "included_candidate_ids": [],
            "computed": False,
        },
        "bootstrap": {
            "method": BOOTSTRAP_METHOD_STATIONARY,
            "reps": bootstrap_reps,
            "seed": seed,
            "block_length": block_length,
        },
        "sample_gate": {
            "minimum_sample": min_sample,
            "sample_size": sample_size,
            "passed": sample_size >= min_sample,
        },
        "observed_statistic": None,
        "best_observed_variant_id": None,
        "best_observed_mean_delta": None,
        "p_value": None,
        "reason": reason,
        "decision_authority": EVIDENCE_ONLY_AUTHORITY,
    }


def studentized_loss_differentials(
    family_loss_matrix: Mapping[str, Any],
    *,
    variance_floor: float = DEFAULT_VARIANCE_FLOOR,
) -> dict[str, Any]:
    sample_size = _sample_size(family_loss_matrix)
    matrix = _complete_loss_matrix(family_loss_matrix)
    block_length = _block_length(family_loss_matrix)
    lag = max(block_length - 1, 0)
    candidate_statistics: dict[str, dict[str, Any]] = {}
    dropped_zero_variance_count = 0
    dropped_incomplete_series_count = 0
    raw_matrix = loss_differential_matrix(family_loss_matrix)
    for candidate_id, deltas in sorted(raw_matrix.items()):
        if len(deltas) != sample_size or sample_size <= 0:
            dropped_incomplete_series_count += 1
            candidate_statistics[candidate_id] = {
                "status": "dropped_incomplete_series",
                "sample_size": len(deltas),
                "required_sample_size": sample_size,
            }
            continue
        mean_delta = float(_mean([float(value) for value in deltas]) or 0.0)
        variance = hac_long_run_variance([float(value) for value in deltas], lag=lag)
        long_run_variance = variance.get("long_run_variance")
        if not isinstance(long_run_variance, (int, float)) or float(long_run_variance) <= variance_floor:
            dropped_zero_variance_count += 1
            candidate_statistics[candidate_id] = {
                "status": "dropped_zero_variance",
                "mean_delta": round(mean_delta, 10),
                "variance_status": variance.get("status"),
                "long_run_variance": long_run_variance,
            }
            continue
        denominator = math.sqrt(float(long_run_variance))
        statistic = max(0.0, -math.sqrt(sample_size) * mean_delta / denominator)
        candidate_statistics[candidate_id] = {
            "status": "studentized",
            "mean_delta": round(mean_delta, 10),
            "long_run_variance": round(float(long_run_variance), 12),
            "standard_error_mean": variance.get("standard_error_mean"),
            "studentized_improvement_statistic": round(statistic, 10),
            "series": [float(value) for value in matrix[candidate_id]],
            "centered_series": [float(value) - mean_delta for value in matrix[candidate_id]],
        }
    return {
        "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
        "minimum_variance_floor": variance_floor,
        "lag": lag,
        "sample_size": sample_size,
        "block_length": block_length,
        "studentized_candidate_count": sum(
            1 for stats in candidate_statistics.values() if stats.get("status") == "studentized"
        ),
        "dropped_zero_variance_count": dropped_zero_variance_count,
        "dropped_incomplete_series_count": dropped_incomplete_series_count,
        "candidate_statistics": candidate_statistics,
    }


def _mean_deltas_from_studentized(studentized: Mapping[str, Any]) -> dict[str, float]:
    candidate_statistics = (
        studentized.get("candidate_statistics")
        if isinstance(studentized.get("candidate_statistics"), Mapping)
        else {}
    )
    return {
        candidate_id: float(stats.get("mean_delta"))
        for candidate_id, stats in candidate_statistics.items()
        if isinstance(stats, Mapping) and isinstance(stats.get("mean_delta"), (int, float))
    }


def _bootstrap_statistic(
    *,
    indices: Sequence[int],
    included_candidate_ids: Sequence[str],
    candidate_statistics: Mapping[str, Mapping[str, Any]],
    sample_size: int,
) -> float:
    replicate_stats: list[float] = []
    for candidate_id in included_candidate_ids:
        stats = candidate_statistics[candidate_id]
        centered = stats.get("centered_series") if isinstance(stats.get("centered_series"), list) else []
        long_run_variance = stats.get("long_run_variance")
        if not centered or not isinstance(long_run_variance, (int, float)) or float(long_run_variance) <= 0.0:
            continue
        replicate_mean = sum(float(centered[index]) for index in indices) / len(indices)
        replicate_stats.append(max(0.0, -math.sqrt(sample_size) * replicate_mean / math.sqrt(float(long_run_variance))))
    return max(replicate_stats) if replicate_stats else 0.0


def spa_summary(
    family_loss_matrix: Mapping[str, Any],
    *,
    min_sample: int = DEFAULT_MIN_BOOTSTRAP_SAMPLE,
    bootstrap_reps: int = DEFAULT_BOOTSTRAP_REPS,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    allow_tiny_sample: bool = False,
    blocked_status: Optional[str] = None,
    variance_floor: float = DEFAULT_VARIANCE_FLOOR,
) -> dict[str, Any]:
    sample_size = _sample_size(family_loss_matrix)
    block_length = _block_length(family_loss_matrix) if sample_size > 0 else None
    matrix = _complete_loss_matrix(family_loss_matrix)
    mean_deltas = {
        candidate_id: float(_mean(deltas))
        for candidate_id, deltas in matrix.items()
        if deltas and _mean(deltas) is not None
    }
    poor_ids = [candidate_id for candidate_id, mean_delta in sorted(mean_deltas.items()) if mean_delta >= 0.0]
    if blocked_status:
        return _empty_spa_block(
            status=blocked_status,
            reason="family_contract_blocker_prevents_spa",
            sample_size=sample_size,
            min_sample=min_sample,
            bootstrap_reps=bootstrap_reps,
            seed=seed,
            block_length=block_length,
            variance_floor=variance_floor,
            poor_or_irrelevant_ids=poor_ids,
        )
    if sample_size < min_sample and not allow_tiny_sample:
        return _empty_spa_block(
            status="not_computed_minimum_sample",
            reason="minimum_sample_not_met",
            sample_size=sample_size,
            min_sample=min_sample,
            bootstrap_reps=bootstrap_reps,
            seed=seed,
            block_length=block_length,
            variance_floor=variance_floor,
            poor_or_irrelevant_ids=poor_ids,
        )
    studentized = studentized_loss_differentials(family_loss_matrix, variance_floor=variance_floor)
    candidate_statistics = {
        candidate_id: stats
        for candidate_id, stats in studentized["candidate_statistics"].items()
        if isinstance(stats, Mapping)
    }
    studentized_ids = [
        candidate_id
        for candidate_id, stats in candidate_statistics.items()
        if stats.get("status") == "studentized"
    ]
    if not studentized_ids:
        return {
            **_empty_spa_block(
                status="not_computed_no_studentization",
                reason="no_candidate_passed_studentization",
                sample_size=sample_size,
                min_sample=min_sample,
                bootstrap_reps=bootstrap_reps,
                seed=seed,
                block_length=block_length,
                variance_floor=variance_floor,
                poor_or_irrelevant_ids=poor_ids,
            ),
            "studentization": {
                "variance_estimator": studentized["variance_estimator"],
                "minimum_variance_floor": variance_floor,
                "studentized_candidate_count": 0,
                "dropped_zero_variance_count": studentized["dropped_zero_variance_count"],
                "dropped_incomplete_series_count": studentized["dropped_incomplete_series_count"],
                "lag": studentized["lag"],
                "candidate_statistics": {
                    candidate_id: {
                        key: value
                        for key, value in stats.items()
                        if key not in {"series", "centered_series"}
                    }
                    for candidate_id, stats in candidate_statistics.items()
                },
            },
        }

    mean_deltas = _mean_deltas_from_studentized(studentized)
    best_variant_id, best_delta = min(mean_deltas.items(), key=lambda item: item[1])
    observed_stats = [
        float(candidate_statistics[candidate_id]["studentized_improvement_statistic"])
        for candidate_id in studentized_ids
    ]
    observed_statistic = max(observed_stats) if observed_stats else 0.0
    included_candidate_ids = [
        candidate_id
        for candidate_id in studentized_ids
        if float(candidate_statistics[candidate_id].get("mean_delta", 0.0)) < 0.0
    ] or studentized_ids
    bootstrap_indices = stationary_bootstrap_indices(
        sample_size,
        block_length=int(block_length or 1),
        reps=bootstrap_reps,
        seed=seed,
    )
    bootstrap_stats = [
        _bootstrap_statistic(
            indices=indices,
            included_candidate_ids=included_candidate_ids,
            candidate_statistics=candidate_statistics,
            sample_size=sample_size,
        )
        for indices in bootstrap_indices
    ]
    p_value = (
        sum(1 for statistic in bootstrap_stats if statistic >= observed_statistic) / len(bootstrap_stats)
        if bootstrap_stats
        else None
    )
    public_candidate_statistics = {
        candidate_id: {
            key: value
            for key, value in stats.items()
            if key not in {"series", "centered_series"}
        }
        for candidate_id, stats in candidate_statistics.items()
    }
    return {
        "schema_version": SPA_STATISTIC_SCHEMA,
        "status": "computed_bootstrap",
        "implemented": True,
        "authority": SPA_STATISTICS_AUTHORITY,
        "null": SPA_NULL,
        "loss_orientation": LOSS_ORIENTATION,
        "studentization": {
            "variance_estimator": studentized["variance_estimator"],
            "minimum_variance_floor": variance_floor,
            "studentized_candidate_count": len(studentized_ids),
            "dropped_zero_variance_count": studentized["dropped_zero_variance_count"],
            "dropped_incomplete_series_count": studentized["dropped_incomplete_series_count"],
            "lag": studentized["lag"],
            "candidate_statistics": public_candidate_statistics,
        },
        "sample_dependent_null": {
            "method": SPA_SAMPLE_DEPENDENT_NULL_METHOD,
            "poor_or_irrelevant_alternative_count": len(poor_ids),
            "poor_or_irrelevant_alternative_ids": poor_ids,
            "included_candidate_count": len(included_candidate_ids),
            "included_candidate_ids": included_candidate_ids,
            "computed": True,
        },
        "bootstrap": {
            "method": BOOTSTRAP_METHOD_STATIONARY,
            "reps": bootstrap_reps,
            "seed": seed,
            "block_length": block_length,
        },
        "sample_gate": {
            "minimum_sample": min_sample,
            "sample_size": sample_size,
            "passed": sample_size >= min_sample,
        },
        "observed_statistic": round(observed_statistic, 10),
        "best_observed_variant_id": best_variant_id,
        "best_observed_mean_delta": round(best_delta, 10),
        "p_value": round(float(p_value), 10) if p_value is not None else None,
        "p_value_resolution": bootstrap_p_value_resolution(p_value, len(bootstrap_stats)),
        "decision_authority": EVIDENCE_ONLY_AUTHORITY,
    }
