"""
[PURPOSE]
- Teleology: Provide the shared paired-loss differential kernel for finance
  variant admission receipts.
- Mechanism: Convert already-paired finance forecast scorecards into an ordered
  loss-differential series, diagnose event-window dependence, and compute
  minimum-sample-gated HAC/Bartlett Diebold-Mariano style statistics.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

LOSS_DIFFERENTIAL_SERIES_SCHEMA = "finance_loss_differential_series_v0"
LOSS_DIFFERENTIAL_AUTHORITY = "tools/finance/loss_differentials.py"
VARIANCE_ESTIMATOR_HAC_BARTLETT = "hac_bartlett"
EXCLUDED_SPLITS_DEFAULT = {"purged", "embargoed"}
VARIANCE_EPSILON = 1e-15
HLN_AUTHORITY = "harvey_leybourne_newbold_1997"


def harvey_leybourne_newbold_correction(
    dm_statistic: Optional[float],
    sample_size: int,
    horizon_days: int,
) -> dict[str, Any]:
    """Harvey-Leybourne-Newbold (1997) small-sample modification of the
    Diebold-Mariano statistic with t(n-1) reference distribution.

    DM* = DM * sqrt((n + 1 - 2h + h(h-1)/n) / n); two-sided p via t(n-1).
    Returns ``status="computed"`` when admissible, ``status="refused"`` with
    a typed reason otherwise. Never raises.
    """
    if dm_statistic is None or not math.isfinite(float(dm_statistic)):
        return {
            "status": "refused",
            "reason": "dm_statistic_unavailable",
            "authority": HLN_AUTHORITY,
        }
    n = int(sample_size or 0)
    h = int(horizon_days or 0)
    if n < 2:
        return {
            "status": "refused",
            "reason": "paired_sample_size_below_two",
            "authority": HLN_AUTHORITY,
            "paired_sample_size": n,
        }
    if h <= 0:
        return {
            "status": "refused",
            "reason": "non_positive_horizon_steps",
            "authority": HLN_AUTHORITY,
            "horizon_days": h,
        }
    if h >= n:
        return {
            "status": "refused",
            "reason": "horizon_at_or_above_sample_size",
            "authority": HLN_AUTHORITY,
            "paired_sample_size": n,
            "horizon_days": h,
        }
    factor_numerator = n + 1 - 2 * h + (h * (h - 1)) / n
    if factor_numerator <= 0:
        return {
            "status": "refused",
            "reason": "non_positive_correction_factor_numerator",
            "authority": HLN_AUTHORITY,
            "paired_sample_size": n,
            "horizon_days": h,
        }
    factor = math.sqrt(factor_numerator / n)
    hln_stat = float(dm_statistic) * factor
    df = n - 1
    try:
        from scipy import stats as _scipy_stats

        p_two_sided = float(2.0 * _scipy_stats.t.sf(abs(hln_stat), df))
    except ImportError:
        return {
            "status": "refused",
            "reason": "scipy_unavailable_for_t_distribution",
            "authority": HLN_AUTHORITY,
            "hln_statistic": round(hln_stat, 10),
            "degrees_of_freedom": df,
            "correction_factor": round(factor, 10),
        }
    return {
        "status": "computed",
        "authority": HLN_AUTHORITY,
        "hln_statistic": round(hln_stat, 10),
        "correction_factor": round(factor, 10),
        "degrees_of_freedom": df,
        "reference_distribution": f"t(df={df})",
        "p_value_two_sided": round(p_two_sided, 10),
        "paired_sample_size": n,
        "horizon_days": h,
        "dm_statistic": round(float(dm_statistic), 10),
    }


@dataclass(frozen=True)
class LossDifferentialRow:
    comparison_event_key: str
    subject_as_of: str
    event_start: str
    event_end: str
    horizon: str
    baseline_loss: float
    candidate_loss: float
    loss_delta_candidate_minus_baseline: float
    split: Optional[str] = None
    split_membership: Optional[Mapping[str, Any]] = None


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    return None


def _parse_dt(value: Any) -> Optional[datetime]:
    text = _as_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _horizon_days(value: Any) -> int:
    text = _as_text(value).lower()
    if not text.endswith("d"):
        return 0
    try:
        return max(int(text[:-1]), 0)
    except ValueError:
        return 0


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _sample_std(values: Sequence[float]) -> Optional[float]:
    if len(values) <= 1:
        return None
    mean_value = float(_mean(values))
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _row_sort_key(row: LossDifferentialRow) -> tuple[str, str, str, str]:
    return (row.subject_as_of, row.event_start, row.event_end, row.comparison_event_key)


def _row_from_pair(pair: Mapping[str, Any]) -> Optional[LossDifferentialRow]:
    baseline_loss = _as_float(pair.get("baseline_loss"))
    candidate_loss = _as_float(pair.get("candidate_loss"))
    if baseline_loss is None or candidate_loss is None:
        return None
    delta = _as_float(pair.get("loss_delta_candidate_minus_baseline"))
    if delta is None:
        delta = candidate_loss - baseline_loss
    split_membership = pair.get("split_membership") if isinstance(pair.get("split_membership"), Mapping) else None
    return LossDifferentialRow(
        comparison_event_key=_as_text(pair.get("comparison_event_key") or pair.get("event_key")),
        subject_as_of=_as_text(pair.get("subject_as_of")),
        event_start=_as_text(pair.get("event_start")),
        event_end=_as_text(pair.get("event_end")),
        horizon=_as_text(pair.get("horizon")),
        baseline_loss=baseline_loss,
        candidate_loss=candidate_loss,
        loss_delta_candidate_minus_baseline=delta,
        split=_as_text(pair.get("split")) or _as_text((split_membership or {}).get("split")) or None,
        split_membership=dict(split_membership) if split_membership is not None else None,
    )


def _split_tokens(value: Any) -> set[str]:
    text = _as_text(value).lower()
    if not text:
        return set()
    tokens = text.replace(",", "|").split("|")
    return {_as_text(token).lower() for token in tokens if _as_text(token)}


def _split_membership_bound(row: LossDifferentialRow) -> bool:
    membership = row.split_membership
    return bool(isinstance(membership, Mapping) and membership.get("bound") is True)


def _split_membership_usable(row: LossDifferentialRow) -> bool:
    membership = row.split_membership
    if not isinstance(membership, Mapping):
        return True
    usable = membership.get("usable_for_variant_comparison")
    return bool(usable) if isinstance(usable, bool) else True


def _event_window_overlap_count(rows: Sequence[LossDifferentialRow]) -> int:
    intervals: list[tuple[datetime, datetime]] = []
    for row in rows:
        start = _parse_dt(row.event_start)
        end = _parse_dt(row.event_end)
        if start is not None and end is not None:
            intervals.append((start, end))
    overlap_count = 0
    for index, (start, end) in enumerate(intervals):
        for other_start, other_end in intervals[index + 1 :]:
            if start < other_end and other_start < end:
                overlap_count += 1
    return overlap_count


def recommended_hac_lag(rows: Sequence[LossDifferentialRow]) -> int:
    if len(rows) <= 1:
        return 0
    overlap_count = _event_window_overlap_count(rows)
    if overlap_count <= 0:
        return 0
    horizon_days = max((_horizon_days(row.horizon) for row in rows), default=0)
    return min(max(horizon_days - 1, 1), len(rows) - 1)


def _autocorrelation(values: Sequence[float], lag: int) -> Optional[float]:
    if lag <= 0 or len(values) <= lag:
        return None
    mean_value = float(_mean(values))
    numerator = sum((values[i] - mean_value) * (values[i - lag] - mean_value) for i in range(lag, len(values)))
    denominator = sum((value - mean_value) ** 2 for value in values)
    if denominator <= 0.0:
        return None
    return numerator / denominator


def build_loss_differential_series(
    pairs: Sequence[Mapping[str, Any]],
    *,
    baseline_variant_id: str,
    candidate_variant_id: str,
    loss_metric: str,
    comparison_key_schema: str,
    include_excluded_splits: bool = False,
) -> dict[str, Any]:
    rows: list[LossDifferentialRow] = []
    excluded_split_count = 0
    missing_split_membership_count = 0
    bound_row_count = 0
    purged_pair_count = 0
    embargoed_pair_count = 0
    dropped_row_count = 0
    for pair in pairs:
        row = _row_from_pair(pair)
        if row is None or not row.comparison_event_key:
            dropped_row_count += 1
            continue
        if _split_membership_bound(row):
            bound_row_count += 1
        else:
            missing_split_membership_count += 1
        split_tokens = _split_tokens(row.split)
        if "purged" in split_tokens:
            purged_pair_count += 1
        if "embargoed" in split_tokens:
            embargoed_pair_count += 1
        excluded_by_split = bool(split_tokens.intersection(EXCLUDED_SPLITS_DEFAULT))
        excluded_by_membership = not _split_membership_usable(row)
        if not include_excluded_splits and (excluded_by_split or excluded_by_membership):
            excluded_split_count += 1
            continue
        rows.append(row)

    rows = sorted(rows, key=_row_sort_key)
    deltas = [row.loss_delta_candidate_minus_baseline for row in rows]
    overlap_count = _event_window_overlap_count(rows)
    selected_lag = recommended_hac_lag(rows)
    autocorrelation: dict[str, Optional[float]] = {}
    if len(deltas) > 2:
        max_lag = min(selected_lag or 1, len(deltas) - 1)
        autocorrelation = {
            f"lag_{lag}": round(value, 10) if value is not None else None
            for lag in range(1, max_lag + 1)
            for value in [_autocorrelation(deltas, lag)]
        }

    return {
        "schema_version": LOSS_DIFFERENTIAL_SERIES_SCHEMA,
        "authority": LOSS_DIFFERENTIAL_AUTHORITY,
        "baseline_variant_id": baseline_variant_id,
        "candidate_variant_id": candidate_variant_id,
        "loss_metric": loss_metric,
        "comparison_key_schema": comparison_key_schema,
        "rows": [asdict(row) for row in rows],
        "dependence_diagnostics": {
            "paired_sample_size": len(rows),
            "horizon_days": max((_horizon_days(row.horizon) for row in rows), default=0),
            "event_window_overlap_count": overlap_count,
            "recommended_lag": selected_lag,
            "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
            "loss_delta_autocorrelation": autocorrelation,
            "split_binding": {
                "bound_row_count": bound_row_count,
                "missing_split_membership_count": missing_split_membership_count,
                "excluded_split_count": excluded_split_count,
                "purged_pair_count": purged_pair_count,
                "embargoed_pair_count": embargoed_pair_count,
                "usable_pair_count": len(rows),
            },
            "bound_split_membership_count": bound_row_count,
            "missing_split_membership_count": missing_split_membership_count,
            "excluded_split_count": excluded_split_count,
            "purged_pair_count": purged_pair_count,
            "embargoed_pair_count": embargoed_pair_count,
            "usable_pair_count": len(rows),
            "dropped_row_count": dropped_row_count,
        },
    }


def hac_long_run_variance(
    deltas: Sequence[float],
    *,
    lag: int,
    kernel: str = "bartlett",
) -> dict[str, Any]:
    if kernel != "bartlett":
        raise ValueError(f"unsupported HAC kernel: {kernel}")
    n = len(deltas)
    if n == 0:
        return {
            "status": "not_computed_empty_sample",
            "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
            "lag": int(lag),
            "long_run_variance": None,
            "standard_error_mean": None,
        }
    mean_value = float(_mean(deltas))
    centered = [delta - mean_value for delta in deltas]
    gamma0 = sum(value * value for value in centered) / n
    selected_lag = min(max(int(lag), 0), max(n - 1, 0))
    long_run_variance = gamma0
    for offset in range(1, selected_lag + 1):
        covariance = sum(centered[index] * centered[index - offset] for index in range(offset, n)) / n
        weight = 1.0 - offset / (selected_lag + 1.0)
        long_run_variance += 2.0 * weight * covariance
    long_run_variance = max(long_run_variance, 0.0)
    if long_run_variance <= VARIANCE_EPSILON:
        return {
            "status": "not_computed_zero_variance",
            "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
            "lag": selected_lag,
            "long_run_variance": 0.0,
            "standard_error_mean": None,
        }
    return {
        "status": "computed",
        "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
        "lag": selected_lag,
        "long_run_variance": long_run_variance,
        "standard_error_mean": math.sqrt(long_run_variance / n),
    }


def diebold_mariano_summary(
    deltas: Sequence[float],
    *,
    lag: int,
    min_paired: int,
    test: str = "diebold_mariano",
) -> dict[str, Any]:
    n = len(deltas)
    block: dict[str, Any] = {
        "status": "not_computed_minimum_sample" if n < min_paired else "reserved_not_requested",
        "test": test,
        "minimum_sample": min_paired,
        "paired_sample_size": n,
        "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
        "lag": min(max(int(lag), 0), max(n - 1, 0)) if n else 0,
        "statistic": None,
        "p_value_two_sided_normal_approx": None,
    }
    if test != "diebold_mariano":
        block["status"] = "not_requested"
        return block
    if n < min_paired:
        return block
    mean_delta = _mean(deltas)
    variance = hac_long_run_variance(deltas, lag=lag)
    block["lag"] = variance["lag"]
    if variance["status"] != "computed" or mean_delta is None:
        block["status"] = "not_computed_zero_variance"
        return block
    stderr = variance.get("standard_error_mean")
    if not isinstance(stderr, (int, float)) or stderr <= 0.0:
        block["status"] = "not_computed_zero_variance"
        return block
    statistic = float(mean_delta) / float(stderr)
    block.update(
        {
            "status": "computed_hac_normal_approximation",
            "statistic": round(statistic, 10),
            "p_value_two_sided_normal_approx": round(math.erfc(abs(statistic) / math.sqrt(2.0)), 10),
        }
    )
    return block


def paired_loss_summary(
    loss_series: Mapping[str, Any],
    *,
    test: str = "diebold_mariano",
    min_paired: int = 30,
) -> dict[str, Any]:
    rows = [row for row in loss_series.get("rows", []) if isinstance(row, Mapping)]
    baseline_losses = [
        float(row["baseline_loss"])
        for row in rows
        if isinstance(row.get("baseline_loss"), (int, float))
    ]
    candidate_losses = [
        float(row["candidate_loss"])
        for row in rows
        if isinstance(row.get("candidate_loss"), (int, float))
    ]
    deltas = [
        float(row["loss_delta_candidate_minus_baseline"])
        for row in rows
        if isinstance(row.get("loss_delta_candidate_minus_baseline"), (int, float))
    ]
    diagnostics = loss_series.get("dependence_diagnostics") if isinstance(loss_series.get("dependence_diagnostics"), Mapping) else {}
    lag = int(diagnostics.get("recommended_lag") or 0)
    variance = hac_long_run_variance(deltas, lag=lag)
    dm_block = diebold_mariano_summary(deltas, lag=lag, min_paired=min_paired, test=test)
    mean_baseline = _mean(baseline_losses)
    mean_candidate = _mean(candidate_losses)
    mean_delta = _mean(deltas)
    std = _sample_std(deltas)
    stderr = variance.get("standard_error_mean") if variance.get("status") == "computed" else None
    return {
        "paired_sample_size": len(deltas),
        "mean_loss_baseline": round(mean_baseline, 10) if mean_baseline is not None else None,
        "mean_loss_candidate": round(mean_candidate, 10) if mean_candidate is not None else None,
        "mean_loss_delta": round(mean_delta, 10) if mean_delta is not None else None,
        "loss_delta_std": round(std, 10) if std is not None else None,
        "loss_delta_std_error": round(float(stderr), 10) if isinstance(stderr, (int, float)) else None,
        "variance_estimator": VARIANCE_ESTIMATOR_HAC_BARTLETT,
        "selected_lag": lag,
        "event_window_overlap_count": int(diagnostics.get("event_window_overlap_count") or 0),
        "dependence_diagnostics": dict(diagnostics),
        "loss_differential_series": dict(loss_series),
        "diebold_mariano": dm_block,
        "hln_small_sample_correction": harvey_leybourne_newbold_correction(
            dm_statistic=dm_block.get("statistic") if isinstance(dm_block, Mapping) else None,
            sample_size=len(deltas),
            horizon_days=int(diagnostics.get("horizon_days") or 0),
        ),
    }
