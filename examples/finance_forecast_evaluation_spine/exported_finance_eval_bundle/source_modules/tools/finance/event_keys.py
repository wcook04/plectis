"""
[PURPOSE]
- Teleology: Provide the single canonical comparison-event key primitive for
  finance forecast evaluation.
- Mechanism: Normalize event-contract fields, build a stable event-equivalence
  payload, and hash it into `fin_evt_*` ids shared by admission, resolution,
  replay, and variant comparison.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

COMPARISON_EVENT_KEY_SCHEMA = "finance_comparison_event_key_v0"
COMPARISON_EVENT_KEY_AUTHORITY = "tools/finance/event_keys.py"


@dataclass(frozen=True)
class FinanceComparisonEventKeyParts:
    subject_as_of: str
    lane: str
    group: str
    members: tuple[str, ...]
    event_start: str
    event_end: str
    horizon: str
    benchmark: str
    event_type: str
    outcome_basis: str
    benchmark_member_policy: str


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_timestamp(value: Any) -> str:
    text = _as_text(value)
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def normalize_members(members: Any) -> tuple[str, ...]:
    if isinstance(members, str):
        raw: Iterable[Any] = members.split(",")
    elif isinstance(members, Iterable):
        raw = members
    else:
        raw = []
    return tuple(sorted({_as_text(member).upper() for member in raw if _as_text(member)}))


def members_signature(members: Any) -> str:
    return ",".join(normalize_members(members))


def normalize_key_parts(
    *,
    subject_as_of: Any,
    lane: Any,
    group: Any,
    members: Any,
    event_start: Any,
    event_end: Any,
    horizon: Any,
    benchmark: Any,
    event_type: Any,
    outcome_basis: Any,
    benchmark_member_policy: Any,
) -> FinanceComparisonEventKeyParts:
    return FinanceComparisonEventKeyParts(
        subject_as_of=_normalize_timestamp(subject_as_of),
        lane=_as_text(lane).lower(),
        group=_as_text(group).lower(),
        members=normalize_members(members),
        event_start=_normalize_timestamp(event_start),
        event_end=_normalize_timestamp(event_end),
        horizon=_as_text(horizon).lower(),
        benchmark=_as_text(benchmark).upper(),
        event_type=_as_text(event_type).lower(),
        outcome_basis=_as_text(outcome_basis).lower(),
        benchmark_member_policy=_as_text(benchmark_member_policy).lower(),
    )


def _stable_digest(*parts: Any, length: int = 20) -> str:
    text = "|".join(_as_text(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def build_comparison_event_key(parts: FinanceComparisonEventKeyParts) -> str:
    if not all(
        [
            parts.subject_as_of,
            parts.lane,
            parts.group,
            parts.members,
            parts.event_start,
            parts.event_end,
            parts.horizon,
            parts.benchmark,
            parts.event_type,
            parts.outcome_basis,
            parts.benchmark_member_policy,
        ]
    ):
        return ""
    return "fin_evt_" + _stable_digest(
        COMPARISON_EVENT_KEY_SCHEMA,
        parts.subject_as_of,
        parts.lane,
        parts.group,
        members_signature(parts.members),
        parts.event_start,
        parts.event_end,
        parts.horizon,
        parts.benchmark,
        parts.event_type,
        parts.outcome_basis,
        parts.benchmark_member_policy,
        length=20,
    )


def comparison_event_key_payload(parts: FinanceComparisonEventKeyParts) -> dict[str, Any]:
    return {
        "comparison_event_key": build_comparison_event_key(parts),
        "comparison_event_key_schema": COMPARISON_EVENT_KEY_SCHEMA,
        "comparison_event_key_authority": COMPARISON_EVENT_KEY_AUTHORITY,
        "comparison_event_key_parts": {
            **asdict(parts),
            "members_signature": members_signature(parts.members),
        },
    }


def parts_from_event_contract(card: Mapping[str, Any]) -> FinanceComparisonEventKeyParts:
    contract = card.get("event_contract") if isinstance(card.get("event_contract"), Mapping) else {}
    target = card.get("target") if isinstance(card.get("target"), Mapping) else {}
    members = contract.get("members_signature") or target.get("members") or []
    return normalize_key_parts(
        subject_as_of=contract.get("subject_as_of") or target.get("as_of"),
        lane=contract.get("lane") or target.get("lane") or target.get("universe"),
        group=contract.get("group") or target.get("group") or target.get("entity_or_group"),
        members=members,
        event_start=contract.get("event_start"),
        event_end=contract.get("event_end"),
        horizon=contract.get("horizon"),
        benchmark=contract.get("benchmark"),
        event_type=contract.get("event_type"),
        outcome_basis=contract.get("outcome_basis"),
        benchmark_member_policy=contract.get("benchmark_member_policy"),
    )
