"""
[PURPOSE]
- Teleology: Enforce the distillation rubric's mechanical checks on worker
  output before shards land in extracted_shards.json. Both Type B (bridge)
  and Type A (subagent) lanes pass through this validator so quality does
  not depend on which worker produced the bundle.

[INTERFACE]
- Exports: ValidatorResult, validate_distillation_bundle, and the individual
  check functions so callers can reuse the predicates outside the bundle
  context.
- Reads: the bundle dict (as authored in distillation_response_schema) and
  the source paragraph dict (from raw_seed.json).
- Writes: nothing. Returns a structured result the caller interprets.

[FLOW]
- Run bundle-level checks first (structural; fail the whole bundle fast).
- For each shard in bundle.shards, run the six per-shard checks in order.
- Classify each failure as reject or flag per severity.
- In advisory mode (default), every shard is returned in `accepted` with
  the failure surfaced alongside in `flagged` or `rejected` for the caller
  to log; `force_accept=True` suppresses rejection entirely.
- In strict mode, `rejected` shards are excluded from `accepted`.

[CONSTRAINTS]
- Checks never mutate the bundle or source.
- All regex work is case-insensitive and whitespace-normalized.
- Rules are codified in codex/doctrine/skills/raw_seed/distillation_validator_rules.md.
- Adding a check here requires refreshing that doctrine file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPRESSION_RATIO_MIN = 0.35
COMPRESSION_RATIO_MAX = 0.95

CONFIDENCE_HIGH_THRESHOLD = 0.8
HEDGE_COUNT_FLAG_THRESHOLD = 3

REVERSAL_MARKERS = (
    "but actually",
    "wait no",
    "or maybe",
    "actually wait",
    "no wait",
    "hmm actually",
    "or actually",
)

HEDGE_PATTERN = re.compile(
    r"\b(maybe|I guess|kind of|I don't know|I dont know|I think|sort of|I might|possibly|perhaps)\b",
    re.IGNORECASE,
)

ROUTING_REFERENCE_PATTERN = re.compile(r"\b(pri|con|mech)_\d+\b", re.IGNORECASE)
ROUTING_LEXICAL_PATTERN = re.compile(r"\b(doctrine|route)\b", re.IGNORECASE)

ARCHITECTURE_LEAK_PATTERN = re.compile(
    r"\b("
    r"we should build|we need to build|the system should|we should add|"
    r"let'?s implement|should be implemented|we should have|we need to have"
    r")\b",
    re.IGNORECASE,
)

# Severity classification.
_REJECT_SEVERITY = "reject"
_FLAG_SEVERITY = "flag"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ValidatorResult:
    """Outcome of validating one distillation bundle against one source paragraph."""

    accepted: list[dict[str, Any]] = field(default_factory=list)
    flagged: list[tuple[dict[str, Any], str]] = field(default_factory=list)
    rejected: list[tuple[dict[str, Any], str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bundle_rejected: bool = False
    bundle_rejection_reason: Optional[str] = None
    mode: str = "advisory"
    force_accept: bool = False
    calibration_source: Optional[str] = None

    def to_report_payload(self) -> dict[str, Any]:
        """Shape suitable for embedding in extracted_payload.validator_report."""
        return {
            "mode": self.mode,
            "force_accept": self.force_accept,
            "calibration_source": self.calibration_source,
            "bundle_rejected": self.bundle_rejected,
            "bundle_rejection_reason": self.bundle_rejection_reason,
            "accepted_count": len(self.accepted),
            "flagged_count": len(self.flagged),
            "rejected_count": len(self.rejected),
            "warnings": list(self.warnings),
            "flagged_reasons": [reason for _, reason in self.flagged],
            "rejected_reasons": [reason for _, reason in self.rejected],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_whitespace_lower(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _string_field(shard: Mapping[str, Any], key: str) -> str:
    value = shard.get(key)
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _source_text(source: Mapping[str, Any]) -> str:
    for key in (
        "text",
        "plain_text",
        "raw_markdown",
        "source_text",
        "body",
        "content",
        "paragraph_text",
    ):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


# ---------------------------------------------------------------------------
# Per-shard checks
# Each returns (severity, message) on failure or None on pass.
# ---------------------------------------------------------------------------


def check_voice_anchor_substring(
    shard: Mapping[str, Any], source: Mapping[str, Any]
) -> Optional[tuple[str, str]]:
    anchor = _string_field(shard, "voice_anchor")
    if not anchor.strip():
        return (_REJECT_SEVERITY, "voice_anchor_empty")
    text = _source_text(source)
    if not text:
        return None
    normalized_anchor = _normalize_whitespace_lower(anchor)
    normalized_source = _normalize_whitespace_lower(text)
    if normalized_anchor in normalized_source:
        return None
    par_id = _string_field(source, "id") or _string_field(shard, "parent_paragraph_id")
    excerpt = anchor.strip()
    if len(excerpt) > 80:
        excerpt = excerpt[:77] + "..."
    return (
        _REJECT_SEVERITY,
        f'voice_anchor_not_in_source: "{excerpt}" not found in source paragraph {par_id}',
    )


def check_compression_ratio_bounds(
    shard: Mapping[str, Any], source: Mapping[str, Any]
) -> Optional[tuple[str, str]]:
    raw = shard.get("compression_ratio")
    if raw is None:
        return None
    try:
        ratio = float(raw)
    except (TypeError, ValueError):
        return (_FLAG_SEVERITY, f"compression_ratio_non_numeric: {raw!r}")
    if ratio < COMPRESSION_RATIO_MIN or ratio > COMPRESSION_RATIO_MAX:
        return (
            _FLAG_SEVERITY,
            f"compression_ratio_out_of_bounds: {ratio:.2f} not in "
            f"[{COMPRESSION_RATIO_MIN}, {COMPRESSION_RATIO_MAX}]",
        )
    return None


def check_no_routing_references(
    shard: Mapping[str, Any], source: Mapping[str, Any]
) -> Optional[tuple[str, str]]:
    clarified = _string_field(shard, "clarified_statement")
    if not clarified:
        return None
    match = ROUTING_REFERENCE_PATTERN.search(clarified)
    if match is not None:
        return (
            _REJECT_SEVERITY,
            f'routing_reference_leaked: "{match.group(0)}" in clarified_statement',
        )
    lex_match = ROUTING_LEXICAL_PATTERN.search(clarified)
    if lex_match is not None:
        return (
            _REJECT_SEVERITY,
            f'routing_reference_leaked: "{lex_match.group(0)}" in clarified_statement',
        )
    return None


def check_no_architecture_leak(
    shard: Mapping[str, Any], source: Mapping[str, Any]
) -> Optional[tuple[str, str]]:
    clarified = _string_field(shard, "clarified_statement")
    if not clarified:
        return None
    match = ARCHITECTURE_LEAK_PATTERN.search(clarified)
    if match is not None:
        return (
            _REJECT_SEVERITY,
            f'architecture_leak: proposal-style phrasing "{match.group(0)}" in clarified_statement',
        )
    return None


def check_confidence_calibration(
    shard: Mapping[str, Any], source: Mapping[str, Any]
) -> Optional[tuple[str, str]]:
    raw_conf = shard.get("distillation_confidence")
    if raw_conf is None:
        return None
    try:
        conf = float(raw_conf)
    except (TypeError, ValueError):
        return None
    if conf <= CONFIDENCE_HIGH_THRESHOLD:
        return None
    gestures = shard.get("gestures_towards") or []
    if isinstance(gestures, str):
        gestures = [gestures] if gestures.strip() else []
    if gestures:
        return None
    text = _source_text(source)
    if not text:
        return None
    hedge_matches = HEDGE_PATTERN.findall(text)
    if len(hedge_matches) < HEDGE_COUNT_FLAG_THRESHOLD:
        return None
    # Calibration refinement (2026-04-17): a hedge-dense source is fine when
    # the shard itself preserves at least one hedge — the worker is being
    # faithful, not fabricating. Only flag when the shard has fully flattened
    # the hedges AND claims high confidence AND offers no alternative reading.
    clarified = _string_field(shard, "clarified_statement")
    shard_hedges = HEDGE_PATTERN.findall(clarified) if clarified else []
    if shard_hedges:
        return None
    return (
        _FLAG_SEVERITY,
        f"confidence_calibration_mismatch: high confidence {conf:.2f} + "
        f"empty gestures_towards + {len(hedge_matches)} hedges in source and "
        f"zero preserved in shard",
    )


def check_agent_seed_source_has_hedge(source: Mapping[str, Any]) -> Optional[str]:
    if str(source.get("source_substrate") or "").strip() != "agent_seed":
        return None
    text = _source_text(source)
    if not text:
        return "agent_seed_source_missing_text"
    if HEDGE_PATTERN.search(text):
        return None
    return "agent_seed_requires_hedge"


# ---------------------------------------------------------------------------
# Bundle-scoped checks
# ---------------------------------------------------------------------------


def check_reversal_preservation(
    bundle: Mapping[str, Any], source: Mapping[str, Any]
) -> Optional[str]:
    text = _source_text(source)
    if not text:
        return None
    lowered = _normalize_whitespace_lower(text)
    markers_present = [marker for marker in REVERSAL_MARKERS if marker in lowered]
    if not markers_present:
        return None
    shards = bundle.get("shards") or []
    par_id = _string_field(source, "id")
    same_parent_shards = [
        shard
        for shard in shards
        if isinstance(shard, Mapping)
        and (
            not par_id
            or _string_field(shard, "parent_paragraph_id") == par_id
        )
    ]
    if len(same_parent_shards) >= 2:
        return None
    return (
        f"reversal_not_preserved: source contains reversal marker(s) "
        f"{markers_present!r} but only {len(same_parent_shards)} shard(s) returned"
    )


def check_bundle_has_shards(bundle: Mapping[str, Any]) -> Optional[str]:
    shards = bundle.get("shards")
    if not isinstance(shards, list) or len(shards) == 0:
        return "empty_bundle: shards missing or empty"
    return None


def check_summary_present(bundle: Mapping[str, Any]) -> Optional[str]:
    summary = bundle.get("_summary")
    if not isinstance(summary, Mapping):
        return "summary_missing: _summary block absent"
    missing = [
        key for key in ("teleology", "outcome", "confidence") if not summary.get(key)
    ]
    if missing:
        return f"summary_incomplete: missing keys {missing!r}"
    return None


def check_parent_paragraph_id_consistent(
    bundle: Mapping[str, Any], source: Mapping[str, Any]
) -> Optional[str]:
    expected = _string_field(source, "id")
    if not expected:
        return None
    for shard in bundle.get("shards") or []:
        if not isinstance(shard, Mapping):
            continue
        parent = _string_field(shard, "parent_paragraph_id")
        if parent and parent != expected:
            return (
                f"parent_paragraph_id_mismatch: shard claims {parent!r} "
                f"but source is {expected!r}"
            )
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_SHARD_CHECKS = (
    check_voice_anchor_substring,
    check_compression_ratio_bounds,
    check_no_routing_references,
    check_no_architecture_leak,
    check_confidence_calibration,
)


def validate_distillation_bundle(
    bundle: Mapping[str, Any],
    source_paragraph: Mapping[str, Any],
    *,
    strict: bool = False,
    force_accept: bool = False,
    calibration_source: Optional[str] = None,
) -> ValidatorResult:
    """Validate a single distillation bundle against its source paragraph.

    Args:
        bundle: the worker-returned JSON object with ``shards`` and ``_summary``.
        source_paragraph: the corresponding paragraph from ``raw_seed.json``.
        strict: when True, rejected shards are excluded from ``accepted``; when
            False (default), every shard lands in ``accepted`` and the failure
            is surfaced alongside in ``flagged``/``rejected`` for the caller.
        force_accept: when True, no shard is rejected regardless of check
            outcomes. Used for Opus gold-seed entries during calibration.
        calibration_source: optional tag recorded in the result for provenance
            (e.g. ``"opus_seed"``).
    """

    mode = "strict" if strict and not force_accept else "advisory"
    result = ValidatorResult(
        mode=mode, force_accept=force_accept, calibration_source=calibration_source
    )

    bundle_issue = check_bundle_has_shards(bundle)
    if bundle_issue is not None:
        result.bundle_rejected = True
        result.bundle_rejection_reason = bundle_issue
        return result

    summary_issue = check_summary_present(bundle)
    if summary_issue is not None:
        result.warnings.append(summary_issue)

    agent_seed_issue = check_agent_seed_source_has_hedge(source_paragraph)
    if agent_seed_issue is not None:
        result.bundle_rejected = True
        result.bundle_rejection_reason = agent_seed_issue
        return result

    parent_issue = check_parent_paragraph_id_consistent(bundle, source_paragraph)
    if parent_issue is not None:
        result.bundle_rejected = True
        result.bundle_rejection_reason = parent_issue
        return result

    reversal_issue = check_reversal_preservation(bundle, source_paragraph)
    if reversal_issue is not None:
        result.warnings.append(reversal_issue)

    for raw_shard in bundle.get("shards") or []:
        if not isinstance(raw_shard, Mapping):
            continue
        shard = dict(raw_shard)
        issues: list[tuple[str, str]] = []
        for check in _SHARD_CHECKS:
            outcome = check(shard, source_paragraph)
            if outcome is not None:
                issues.append(outcome)
        reject_reasons = [msg for sev, msg in issues if sev == _REJECT_SEVERITY]
        flag_reasons = [msg for sev, msg in issues if sev == _FLAG_SEVERITY]
        combined_reject = "; ".join(reject_reasons) if reject_reasons else None
        combined_flag = "; ".join(flag_reasons) if flag_reasons else None

        if force_accept:
            if combined_reject or combined_flag:
                warn_parts = [part for part in (combined_reject, combined_flag) if part]
                result.warnings.append(
                    f"force_accept: shard {shard.get('id') or shard.get('segment_ordinal')!r} "
                    f"had issues ({'; '.join(warn_parts)})"
                )
            result.accepted.append(shard)
            continue

        if combined_reject:
            if strict:
                result.rejected.append((shard, combined_reject))
            else:
                # advisory: still surface as rejected but also keep in accepted
                # so the existing import lane can ingest. Caller decides whether
                # to honor the rejection flag.
                result.rejected.append((shard, combined_reject))
                result.accepted.append(shard)
            continue

        if combined_flag:
            result.flagged.append((shard, combined_flag))
        result.accepted.append(shard)

    return result


__all__ = [
    "ValidatorResult",
    "validate_distillation_bundle",
    "check_voice_anchor_substring",
    "check_compression_ratio_bounds",
    "check_no_routing_references",
    "check_no_architecture_leak",
    "check_confidence_calibration",
    "check_agent_seed_source_has_hedge",
    "check_reversal_preservation",
    "check_bundle_has_shards",
    "check_summary_present",
    "check_parent_paragraph_id_consistent",
    "COMPRESSION_RATIO_MIN",
    "COMPRESSION_RATIO_MAX",
    "REVERSAL_MARKERS",
]
