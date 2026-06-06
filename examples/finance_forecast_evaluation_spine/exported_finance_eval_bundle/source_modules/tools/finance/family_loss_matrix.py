"""
[PURPOSE]
- Teleology: Build the family-level loss matrix that turns many pairwise
  finance variant gates into one shared-event statistical input.
- Mechanism: Consume split-bound finance_variant_admission receipts, intersect
  comparison_event_key rows across candidate variants, and materialize
  event_key x variant_id losses with coverage and dependence diagnostics.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

FAMILY_LOSS_MATRIX_SCHEMA = "finance_family_loss_matrix_v0"
FAMILY_LOSS_MATRIX_AUTHORITY = "tools/finance/family_loss_matrix.py"
BOOTSTRAP_METHOD_STATIONARY = "stationary_bootstrap"
EXCLUDED_SPLITS = {"purged", "embargoed"}
LOSS_EPSILON = 1e-12


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


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


def _split_tokens(value: Any) -> set[str]:
    text = _as_text(value).lower()
    if not text:
        return set()
    return {_as_text(token).lower() for token in text.replace(",", "|").split("|") if _as_text(token)}


def _event_window_overlap_count(rows: Sequence[Mapping[str, Any]]) -> int:
    intervals: list[tuple[datetime, datetime]] = []
    for row in rows:
        start = _parse_dt(row.get("event_start"))
        end = _parse_dt(row.get("event_end"))
        if start is not None and end is not None:
            intervals.append((start, end))
    overlap_count = 0
    for index, (start, end) in enumerate(intervals):
        for other_start, other_end in intervals[index + 1 :]:
            if start < other_end and other_start < end:
                overlap_count += 1
    return overlap_count


def _candidate_id(receipt: Mapping[str, Any]) -> str:
    return _as_text(receipt.get("candidate_variant_id"))


def _series_rows(receipt: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = _nested(receipt, "statistics", "loss_differential_series", "rows")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def _split_membership(row: Mapping[str, Any]) -> Mapping[str, Any]:
    membership = row.get("split_membership")
    return membership if isinstance(membership, Mapping) else {}


def _row_split(row: Mapping[str, Any]) -> str:
    membership = _split_membership(row)
    return _as_text(row.get("split") or membership.get("split"))


def _split_bound(row: Mapping[str, Any]) -> bool:
    return _split_membership(row).get("bound") is True


def _split_usable(row: Mapping[str, Any]) -> bool:
    membership = _split_membership(row)
    usable = membership.get("usable_for_variant_comparison")
    return bool(usable) if isinstance(usable, bool) else True


def _row_is_usable(row: Mapping[str, Any]) -> tuple[bool, str]:
    if not _split_bound(row):
        return False, "split_membership_unbound"
    split_tokens = _split_tokens(_row_split(row))
    if split_tokens.intersection(EXCLUDED_SPLITS):
        return False, "excluded_split"
    if not _split_usable(row):
        return False, "split_not_usable_for_variant_comparison"
    if not _as_text(row.get("comparison_event_key")):
        return False, "missing_comparison_event_key"
    if _as_float(row.get("baseline_loss")) is None or _as_float(row.get("candidate_loss")) is None:
        return False, "missing_loss"
    return True, ""


def _usable_candidate_rows(receipt: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, int]]:
    rows_by_key: dict[str, Mapping[str, Any]] = {}
    blocked: dict[str, int] = {}
    for row in _series_rows(receipt):
        usable, reason = _row_is_usable(row)
        if not usable:
            blocked[reason] = blocked.get(reason, 0) + 1
            continue
        key = _as_text(row.get("comparison_event_key"))
        rows_by_key[key] = row
    return rows_by_key, blocked


def _row_for_matrix(
    event_key: str,
    *,
    candidate_maps: Mapping[str, Mapping[str, Mapping[str, Any]]],
    baseline_variant_id: str,
) -> tuple[dict[str, Any], int]:
    first_row = next(iter(candidate_maps.values()))[event_key]
    baseline_loss = float(first_row["baseline_loss"])
    losses: dict[str, float] = {baseline_variant_id: round(baseline_loss, 10)}
    baseline_mismatch_count = 0
    for candidate_id, rows_by_key in candidate_maps.items():
        row = rows_by_key[event_key]
        row_baseline_loss = float(row["baseline_loss"])
        if abs(row_baseline_loss - baseline_loss) > LOSS_EPSILON:
            baseline_mismatch_count += 1
        losses[candidate_id] = round(float(row["candidate_loss"]), 10)
    membership = dict(_split_membership(first_row))
    split = _row_split(first_row)
    return (
        {
            "comparison_event_key": event_key,
            "subject_as_of": _as_text(first_row.get("subject_as_of")),
            "event_start": _as_text(first_row.get("event_start")),
            "event_end": _as_text(first_row.get("event_end")),
            "horizon": _as_text(first_row.get("horizon")),
            "split": split or membership.get("split"),
            "split_membership": membership,
            "losses": losses,
        },
        baseline_mismatch_count,
    )


def build_family_loss_matrix(
    receipts: Sequence[Mapping[str, Any]],
    *,
    baseline_variant_id: Optional[str],
    candidate_variant_ids: Sequence[str],
    loss_metric: Optional[str],
    comparison_key_schema: Optional[str],
    split_policy: Optional[str],
) -> dict[str, Any]:
    candidate_maps: dict[str, dict[str, Mapping[str, Any]]] = {}
    candidate_event_counts: dict[str, int] = {}
    blocked_reason_counts: dict[str, int] = {}
    for receipt in receipts:
        candidate_id = _candidate_id(receipt)
        if not candidate_id:
            blocked_reason_counts["missing_candidate_variant_id"] = blocked_reason_counts.get("missing_candidate_variant_id", 0) + 1
            continue
        rows_by_key, blocked = _usable_candidate_rows(receipt)
        candidate_maps[candidate_id] = rows_by_key
        candidate_event_counts[candidate_id] = len(rows_by_key)
        for reason, count in blocked.items():
            blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + count

    candidate_ids = [candidate_id for candidate_id in candidate_variant_ids if candidate_id in candidate_maps]
    event_sets = [set(candidate_maps[candidate_id]) for candidate_id in candidate_ids]
    shared_keys = sorted(set.intersection(*event_sets)) if event_sets and all(event_sets) else []
    union_keys = set.union(*event_sets) if event_sets else set()

    rows: list[dict[str, Any]] = []
    baseline_loss_mismatch_count = 0
    baseline_id = _as_text(baseline_variant_id)
    for event_key in shared_keys:
        row, mismatch_count = _row_for_matrix(event_key, candidate_maps=candidate_maps, baseline_variant_id=baseline_id)
        rows.append(row)
        baseline_loss_mismatch_count += mismatch_count

    rows.sort(key=lambda row: (_as_text(row.get("subject_as_of")), _as_text(row.get("event_start")), _as_text(row.get("event_end")), _as_text(row.get("comparison_event_key"))))
    overlap_count = _event_window_overlap_count(rows)
    horizon_days = max((_horizon_days(row.get("horizon")) for row in rows), default=0)
    recommended_block_length = max(1, min(max(horizon_days, 1), max(len(rows), 1))) if rows else None
    if rows and overlap_count <= 0:
        recommended_block_length = 1

    return {
        "schema_version": FAMILY_LOSS_MATRIX_SCHEMA,
        "authority": FAMILY_LOSS_MATRIX_AUTHORITY,
        "status": "built" if rows else "blocked",
        "baseline_variant_id": baseline_id or None,
        "candidate_variant_ids": candidate_ids,
        "loss_metric": loss_metric,
        "comparison_key_schema": comparison_key_schema,
        "split_policy": split_policy,
        "rows": rows,
        "coverage": {
            "shared_event_count": len(rows),
            "dropped_unshared_event_count": max(len(union_keys) - len(shared_keys), 0),
            "variant_count": len(candidate_ids) + (1 if baseline_id else 0),
            "candidate_count": len(candidate_ids),
            "candidate_event_counts": candidate_event_counts,
            "blocked_reason_counts": dict(sorted(blocked_reason_counts.items())),
            "missing_split_membership_count": _as_int(blocked_reason_counts.get("split_membership_unbound")),
            "excluded_split_count": _as_int(blocked_reason_counts.get("excluded_split")),
            "dropped_missing_loss_count": _as_int(blocked_reason_counts.get("missing_loss")),
            "baseline_loss_mismatch_count": baseline_loss_mismatch_count,
        },
        "dependence_diagnostics": {
            "event_window_overlap_count": overlap_count,
            "horizon_days": horizon_days,
            "recommended_block_length": recommended_block_length,
            "bootstrap_method": BOOTSTRAP_METHOD_STATIONARY,
        },
    }
