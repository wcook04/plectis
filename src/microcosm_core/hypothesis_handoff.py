"""Validate and render typed hypothesis-to-expert handoff packets.

The packet is deliberately advisory. It makes a project's current guess,
alternatives, and discriminating evidence inspectable without promoting any
of them into a claim, probability, proof, or automatic status change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "plectis-hypothesis-handoff/1"
AUTHORITY_POSTURE = "working_hypothesis_not_claim_probability_or_proof"
EXPERT_RETURN_AUTHORITY = "expert_return_advisory_until_checked_and_landed"
STATUS_CHANGE_RULE = (
    "No claim status changes from an expert return until the return is "
    "independently checked, intended meaning is reviewed, the authority record "
    "is updated, and the declared release gate passes."
)
LANDING_ORDER = [
    "source evidence or argument with exact assumptions",
    "independent check or reproducible verification artifact",
    "authoritative claim and known-gap record update",
    "public projection refresh and declared release validation",
]


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _safe_relative_path(value: Any) -> bool:
    if not _nonempty_text(value):
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _require_text(
    row: dict[str, Any],
    field: str,
    context: str,
    errors: list[str],
) -> None:
    if not _nonempty_text(row.get(field)):
        errors.append(f"{context}.{field} is empty")


def _evidence_errors(
    rows: Any,
    *,
    context: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(rows, list) or not rows:
        return [f"{context} must be a nonempty list"]
    for index, row in enumerate(rows):
        row_context = f"{context}[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{row_context} must be an object")
            continue
        for field in ("ref", "observation", "supports", "authority_ceiling"):
            _require_text(row, field, row_context, errors)
    return errors


def validate_packet(packet: Any) -> list[str]:
    """Return all structural and authority-boundary errors in ``packet``."""

    if not isinstance(packet, dict):
        return ["packet must be a JSON object"]

    errors: list[str] = []
    if packet.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    for field in ("id", "question", "current_wall", "claim_ceiling"):
        _require_text(packet, field, "packet", errors)
    if packet.get("authority_posture") != AUTHORITY_POSTURE:
        errors.append("packet.authority_posture drifted")

    hypothesis_ids: set[str] = set()
    option_discriminator_refs: list[tuple[str, str, list[str]]] = []
    leading = packet.get("leading_hypothesis")
    if not isinstance(leading, dict):
        errors.append("leading_hypothesis must be an object")
    else:
        for field in ("id", "statement", "would_be_displaced_by"):
            _require_text(leading, field, "leading_hypothesis", errors)
        leading_id = leading.get("id")
        if _nonempty_text(leading_id):
            hypothesis_ids.add(leading_id)
        distinguished_by = leading.get("distinguished_by")
        if (
            not isinstance(distinguished_by, list)
            or not distinguished_by
            or not all(_nonempty_text(item) for item in distinguished_by)
        ):
            errors.append(
                "leading_hypothesis.distinguished_by must name discriminator ids"
            )
        elif _nonempty_text(leading_id):
            option_discriminator_refs.append(
                ("leading_hypothesis", leading_id, list(distinguished_by))
            )
        if leading.get("confidence") != "tentative":
            errors.append("leading_hypothesis.confidence must be tentative")
        errors.extend(
            _evidence_errors(
                leading.get("evidence_for"),
                context="leading_hypothesis.evidence_for",
            )
        )
        errors.extend(
            _evidence_errors(
                leading.get("evidence_against_or_missing"),
                context="leading_hypothesis.evidence_against_or_missing",
            )
        )

    alternatives = packet.get("alternatives")
    if not isinstance(alternatives, list) or not alternatives:
        errors.append("alternatives must be a nonempty list")
    else:
        for index, alternative in enumerate(alternatives):
            context = f"alternatives[{index}]"
            if not isinstance(alternative, dict):
                errors.append(f"{context} must be an object")
                continue
            for field in ("id", "statement"):
                _require_text(alternative, field, context, errors)
            alternative_id = alternative.get("id")
            if _nonempty_text(alternative_id):
                if alternative_id in hypothesis_ids:
                    errors.append(f"{context}.id is duplicated: {alternative_id}")
                hypothesis_ids.add(alternative_id)
            distinguished_by = alternative.get("distinguished_by")
            if not isinstance(distinguished_by, list) or not distinguished_by or not all(
                _nonempty_text(item) for item in distinguished_by
            ):
                errors.append(f"{context}.distinguished_by must name discriminator ids")
            else:
                if _nonempty_text(alternative_id):
                    option_discriminator_refs.append(
                        (context, alternative_id, list(distinguished_by))
                    )

    discriminator_ids: set[str] = set()
    discriminator_supported_options: dict[str, set[str]] = {}
    result_hypothesis_refs: list[tuple[str, list[str]]] = []
    discriminators = packet.get("discriminating_evidence")
    if not isinstance(discriminators, list) or not discriminators:
        errors.append("discriminating_evidence must be a nonempty list")
    else:
        for index, discriminator in enumerate(discriminators):
            context = f"discriminating_evidence[{index}]"
            if not isinstance(discriminator, dict):
                errors.append(f"{context} must be an object")
                continue
            for field in ("id", "evidence_needed", "claim_ceiling"):
                _require_text(discriminator, field, context, errors)
            discriminator_id = discriminator.get("id")
            if _nonempty_text(discriminator_id):
                if discriminator_id in discriminator_ids:
                    errors.append(f"{context}.id is duplicated: {discriminator_id}")
                discriminator_ids.add(discriminator_id)
                discriminator_supported_options.setdefault(discriminator_id, set())
            result_map = discriminator.get("result_map")
            if not isinstance(result_map, list) or len(result_map) < 2:
                errors.append(f"{context}.result_map needs at least two outcomes")
                continue
            for result_index, result in enumerate(result_map):
                result_context = f"{context}.result_map[{result_index}]"
                if not isinstance(result, dict):
                    errors.append(f"{result_context} must be an object")
                    continue
                for field in ("result", "interpretation"):
                    _require_text(result, field, result_context, errors)
                supports_ids = result.get("supports_hypothesis_ids")
                if (
                    not isinstance(supports_ids, list)
                    or not supports_ids
                    or not all(_nonempty_text(item) for item in supports_ids)
                ):
                    errors.append(
                        f"{result_context}.supports_hypothesis_ids must name options"
                    )
                    continue
                result_hypothesis_refs.append((result_context, list(supports_ids)))
                if _nonempty_text(discriminator_id):
                    discriminator_supported_options[discriminator_id].update(
                        supports_ids
                    )

    for context, refs in result_hypothesis_refs:
        unknown = sorted(set(refs) - hypothesis_ids)
        if unknown:
            errors.append(
                f"{context}.supports_hypothesis_ids has unknown ids: {unknown}"
            )
    for discriminator_id, supported_options in discriminator_supported_options.items():
        if len(supported_options & hypothesis_ids) < 2:
            errors.append(
                f"discriminator {discriminator_id} must distinguish at least two options"
            )
    for context, option_id, refs in option_discriminator_refs:
        unknown = sorted(set(refs) - discriminator_ids)
        if unknown:
            errors.append(f"{context}.distinguished_by has unknown ids: {unknown}")
        for discriminator_id in sorted(set(refs) & discriminator_ids):
            if option_id not in discriminator_supported_options.get(
                discriminator_id, set()
            ):
                errors.append(
                    f"{context}.distinguished_by names {discriminator_id}, but no "
                    f"outcome supports {option_id}"
                )

    expert_return = packet.get("expert_return")
    if not isinstance(expert_return, dict):
        errors.append("expert_return must be an object")
    else:
        if expert_return.get("authority_posture") != EXPERT_RETURN_AUTHORITY:
            errors.append("expert_return.authority_posture drifted")
        if expert_return.get("status_change_rule") != STATUS_CHANGE_RULE:
            errors.append("expert_return.status_change_rule permits automatic promotion")
        if expert_return.get("landing_order") != LANDING_ORDER:
            errors.append("expert_return.landing_order drifted")
        _require_text(expert_return, "request", "expert_return", errors)
        landing_targets = expert_return.get("landing_targets")
        if not isinstance(landing_targets, list) or not landing_targets:
            errors.append("expert_return.landing_targets must be a nonempty list")
        else:
            seen_paths: set[str] = set()
            for index, target in enumerate(landing_targets):
                context = f"expert_return.landing_targets[{index}]"
                if not isinstance(target, dict):
                    errors.append(f"{context} must be an object")
                    continue
                for field in ("role", "path", "purpose", "validator"):
                    _require_text(target, field, context, errors)
                target_path = target.get("path")
                if _nonempty_text(target_path):
                    if not _safe_relative_path(target_path):
                        errors.append(
                            f"{context}.path must be a safe repository-relative path"
                        )
                    elif target_path in seen_paths:
                        errors.append(f"{context}.path is duplicated: {target_path}")
                    seen_paths.add(target_path)
        required_validation = expert_return.get("required_validation")
        if (
            not isinstance(required_validation, list)
            or not required_validation
            or not all(_nonempty_text(item) for item in required_validation)
        ):
            errors.append("expert_return.required_validation must be a nonempty list")
        for list_field in ("decisive_returns", "route_only_returns"):
            rows = expert_return.get(list_field)
            if not isinstance(rows, list) or not rows:
                errors.append(f"expert_return.{list_field} must be a nonempty list")
                continue
            for index, row in enumerate(rows):
                context = f"expert_return.{list_field}[{index}]"
                if not isinstance(row, dict):
                    errors.append(f"{context} must be an object")
                    continue
                for field in ("id", "requested_input", "effect_if_verified"):
                    _require_text(row, field, context, errors)
                if list_field == "route_only_returns":
                    _require_text(row, "claim_ceiling", context, errors)

    return errors


def compile_packet(packet: Any, *, source: str | None = None) -> dict[str, Any]:
    """Return a bounded validation card without mutating the input."""

    errors = validate_packet(packet)
    result: dict[str, Any] = {
        "schema": "plectis-hypothesis-handoff-validation/1",
        "status": "pass" if not errors else "fail",
        "source": source,
        "authority_ceiling": (
            "The packet exposes a working research prior and an expert-return "
            "contract. It does not establish truth, probability, proof, expert "
            "agreement, or any claim-status change."
        ),
        "errors": errors,
    }
    if not isinstance(packet, dict):
        return result
    result.update(
        {
            "handoff_id": packet.get("id"),
            "question": packet.get("question"),
            "current_wall": packet.get("current_wall"),
            "leading_hypothesis": packet.get("leading_hypothesis"),
            "alternatives": packet.get("alternatives"),
            "discriminating_evidence": packet.get("discriminating_evidence"),
            "expert_return": packet.get("expert_return"),
            "claim_ceiling": packet.get("claim_ceiling"),
            "ready_for_expert": not errors,
        }
    )
    return result


def load_and_compile(path: str | Path) -> dict[str, Any]:
    """Read one JSON packet and return error-as-data on file or parse failure."""

    source = str(Path(path))
    try:
        packet = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "schema": "plectis-hypothesis-handoff-validation/1",
            "status": "fail",
            "source": source,
            "authority_ceiling": (
                "No hypothesis or expert-return claim is available because the "
                "input packet could not be read and validated."
            ),
            "errors": [f"{type(exc).__name__}: {exc}"],
            "ready_for_expert": False,
        }
    return compile_packet(packet, source=source)


def render_text(card: dict[str, Any]) -> str:
    """Render a valid or invalid packet as an answer-first terminal card."""

    if card.get("status") != "pass":
        errors = card.get("errors") if isinstance(card.get("errors"), list) else []
        lines = ["Hypothesis handoff: invalid"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines) + "\n"

    leading = card["leading_hypothesis"]
    lines = [
        f"Hypothesis handoff: {card['handoff_id']}",
        f"Question: {card['question']}",
        f"Current wall: {card['current_wall']}",
        "",
        "Working lead — tentative; not a claim or probability:",
        f"  {leading['statement']}",
        "Evidence for:",
    ]
    for row in leading["evidence_for"]:
        lines.append(f"  - {row['observation']} [{row['ref']}]")
        lines.append(f"      bearing: {row['supports']}")
        lines.append(f"      ceiling: {row['authority_ceiling']}")
    lines.append("Evidence against or still missing:")
    for row in leading["evidence_against_or_missing"]:
        lines.append(f"  - {row['observation']} [{row['ref']}]")
        lines.append(f"      bearing: {row['supports']}")
        lines.append(f"      ceiling: {row['authority_ceiling']}")
    lines.extend(["", "Plausible alternatives:"])
    lines.extend(
        f"  - {row['id']}: {row['statement']}" for row in card["alternatives"]
    )
    lines.extend(["", "Evidence that would distinguish them:"])
    for row in card["discriminating_evidence"]:
        lines.append(f"  - {row['id']}: {row['evidence_needed']}")
        for result in row["result_map"]:
            supported = ", ".join(result["supports_hypothesis_ids"])
            lines.append(
                f"      {result['result']} -> {result['interpretation']} "
                f"[supports: {supported}]"
            )
        lines.append(f"      ceiling: {row['claim_ceiling']}")
    expert_return = card["expert_return"]
    lines.extend(
        [
            "",
            f"Exact expert request: {expert_return['request']}",
            "Decisive returns if verified:",
        ]
    )
    lines.extend(
        f"  - {row['requested_input']} -> {row['effect_if_verified']}"
        for row in expert_return["decisive_returns"]
    )
    lines.append("Useful but route-only returns:")
    for row in expert_return["route_only_returns"]:
        lines.append(f"  - {row['requested_input']} -> {row['effect_if_verified']}")
        lines.append(f"      ceiling: {row['claim_ceiling']}")
    lines.append("Checked landing targets:")
    lines.extend(
        f"  - {row['path']} ({row['role']}): {row['purpose']} "
        f"[validate: {row['validator']}]"
        for row in expert_return["landing_targets"]
    )
    lines.append("Checked landing order:")
    lines.extend(
        f"  {index}. {step}"
        for index, step in enumerate(expert_return["landing_order"], start=1)
    )
    lines.extend(
        [
            "Required validation:",
            *(f"  - {command}" for command in expert_return["required_validation"]),
            f"Status rule: {expert_return['status_change_rule']}",
            f"Claim ceiling: {card['claim_ceiling']}",
            f"Authority ceiling: {card['authority_ceiling']}",
        ]
    )
    return "\n".join(lines) + "\n"
