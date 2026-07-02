"""
Implements macro tools command output projection for the public Plectis package.

Callers enter through `make_row_id`, `make_omission_receipt`, `make_validation_contract`,
`make_currentness`, `command_projection`, `row_band_unavailable`, and 2 more; constants such
as `STANDARD_REF`, `ROOT_CONTRACT_REF`, `ENVELOPE_KIND`, `ENVELOPE_SCHEMA_VERSION`, and 1
more pin local fixture names; dependencies include `datetime` and `typing`. The helpers are
invoked explicitly by CLI or fixture code; importing the module only declares the available
machinery.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


STANDARD_REF = "codex/standards/std_command_output_projection.json"
ROOT_CONTRACT_REF = (
    "codex/standards/std_agent_entry_surface.json::compression_via_projection_contract"
)
ENVELOPE_KIND = "kernel.command_output_projection"
ENVELOPE_SCHEMA_VERSION = "command_output_projection_v0"

REQUIRED_FIELDS: tuple[str, ...] = (
    "kind",
    "command",
    "band",
    "row_id",
    "summary",
    "currentness",
    "drilldown_command",
    "evidence_command",
    "omission_receipt",
    "validation_contract",
)


def _utc_now() -> str:
    """
    Produce the utc now value used by
    `microcosm_core.macro_tools.command_output_projection`.

    Notable helpers are `replace`, `isoformat`, and `now`.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_row_id(command: str, selector: str, band: str) -> str:
    """
    Derive make row ID without touching module import state.

    Inputs are `command`, `selector`, and `band`; notable helpers are `lstrip` and `strip`.
    """
    cmd = str(command or "").strip().lstrip("-")
    sel = str(selector or "").strip() or "default"
    bnd = str(band or "").strip() or "card"
    return f"kernel:{cmd}:{sel}::{bnd}"


def make_omission_receipt(
    *,
    omitted: Sequence[str],
    reason: str,
    drilldown: str,
) -> dict[str, Any]:
    """
    Serialize `microcosm_core.macro_tools.command_output_projection.make_omission_receipt`
    into the payload shape expected by macro tools command output projection.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "omitted": [str(item) for item in omitted if str(item).strip()],
        "reason": str(reason or "").strip(),
        "drilldown": str(drilldown or "").strip(),
    }


def make_validation_contract(
    *,
    freshness_probe: str | None = None,
    schema_probe: str | None = None,
    failure_modes: Sequence[str] | None = None,
    standard: str = STANDARD_REF,
) -> dict[str, Any]:
    """
    Return make validation contract for the macro tools command output projection flow.

    Inputs are `freshness_probe`, `schema_probe`, `failure_modes`, and `standard`; notable
    helpers are `strip`.
    """
    contract: dict[str, Any] = {"standard": standard}
    if freshness_probe:
        contract["freshness_probe"] = str(freshness_probe).strip()
    if schema_probe:
        contract["schema_probe"] = str(schema_probe).strip()
    if failure_modes:
        contract["failure_modes"] = [str(m) for m in failure_modes if str(m).strip()]
    return contract


def make_currentness(
    *,
    status: str = "live_computed",
    generated_at: str | None = None,
    source_refs_checked: Sequence[str] | None = None,
    source_mtimes: Mapping[str, str] | None = None,
    recommended_action: str = "trust",
    action_reason: str | None = None,
) -> dict[str, Any]:
    """
    Compute make currentness from `status`, `generated_at`, `source_refs_checked`,
    `source_mtimes`, `recommended_action`, and 1 more.

    Inputs are `status`, `generated_at`, `source_refs_checked`, `source_mtimes`,
    `recommended_action`, and 1 more; notable helpers are `strip`, `_utc_now`, and `items`.
    """
    block: dict[str, Any] = {
        "status": str(status or "live_computed"),
        "generated_at": generated_at or _utc_now(),
        "recommended_action": str(recommended_action or "trust"),
    }
    if source_refs_checked:
        block["source_refs_checked"] = [str(p) for p in source_refs_checked if str(p).strip()]
    if source_mtimes:
        block["source_mtimes"] = {str(k): str(v) for k, v in source_mtimes.items()}
    if action_reason:
        block["action_reason"] = str(action_reason).strip()
    return block


def command_projection(
    *,
    command: str,
    band: str,
    row_id: str | None = None,
    selector: str = "default",
    summary: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    currentness: Mapping[str, Any] | None = None,
    drilldown_command: str,
    evidence_command: str | None = None,
    omission_receipt: Mapping[str, Any],
    validation_contract: Mapping[str, Any] | None = None,
    sources: Mapping[str, Any] | None = None,
    next_steps: Sequence[Mapping[str, Any]] | None = None,
    warnings: Sequence[Mapping[str, Any]] | None = None,
    schema_version: str = ENVELOPE_SCHEMA_VERSION,
    extra_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return command projection for the macro tools command output projection flow.

    Inputs are `command`, `band`, `row_id`, `selector`, `summary`, and 11 more; notable
    helpers are `lstrip`, `strip`, `ValueError`, `make_row_id`, and 3 more; invalid cases
    raise from the explicit checks in the body.
    """
    cmd = str(command or "").strip().lstrip("-")
    bnd = str(band or "").strip()
    if not cmd:
        raise ValueError("command_projection: command is required")
    if not bnd:
        raise ValueError("command_projection: band is required")
    if not drilldown_command:
        raise ValueError("command_projection: drilldown_command is required")
    if not omission_receipt or not isinstance(omission_receipt, Mapping):
        raise ValueError("command_projection: omission_receipt is required and must be a mapping")

    rid = row_id or make_row_id(cmd, selector, bnd)
    envelope: dict[str, Any] = {
        "kind": ENVELOPE_KIND,
        "schema_version": schema_version,
        "command": cmd,
        "band": bnd,
        "row_id": rid,
        "summary": dict(summary or {}),
        "currentness": dict(currentness or make_currentness()),
        "drilldown_command": str(drilldown_command),
        "evidence_command": str(evidence_command or drilldown_command),
        "omission_receipt": dict(omission_receipt),
        "validation_contract": dict(validation_contract or make_validation_contract()),
        "governing_standard": STANDARD_REF,
        "inherits_from": ROOT_CONTRACT_REF,
    }
    if payload is not None:
        envelope["payload"] = dict(payload)
    if sources:
        envelope["sources"] = dict(sources)
    if next_steps:
        envelope["next"] = [dict(step) for step in next_steps]
    if warnings:
        envelope["warnings"] = [dict(w) for w in warnings]
    if extra_fields:
        for key, value in extra_fields.items():
            if key in envelope:
                continue
            envelope[key] = value
    missing = [field for field in REQUIRED_FIELDS if field not in envelope]
    if missing:
        raise ValueError(
            f"command_projection: missing required envelope fields: {sorted(missing)}"
        )
    return envelope


def row_band_unavailable(
    *,
    kind_id: str,
    row_id_value: str,
    requested_band: str,
    reason: str,
    legal_bands: Sequence[str],
    populated_bands: Sequence[str],
    next_safe_commands: Sequence[str],
) -> dict[str, Any]:
    """
    Serialize `microcosm_core.macro_tools.command_output_projection.row_band_unavailable`
    into the payload shape expected by macro tools command output projection.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "kind": "row_band_unavailable",
        "schema_version": "row_band_unavailable_v0",
        "governing_standard": STANDARD_REF,
        "phase_09_45_anchor": (
            "par_phase_09_raw_seed__naming_a_structural_drift_signal_is_not_the_same_as_routing_it_003"
        ),
        "requested": {
            "kind_id": str(kind_id),
            "id": str(row_id_value),
            "band": str(requested_band),
        },
        "reason": str(reason or "").strip(),
        "legal_bands": [str(b) for b in legal_bands if str(b).strip()],
        "populated_bands": [str(b) for b in populated_bands if str(b).strip()],
        "next_safe_commands": [str(c) for c in next_safe_commands if str(c).strip()],
    }


def envelope_required_fields() -> tuple[str, ...]:
    """
    Derive envelope required fields without touching module import state.

    The returned value is consumed directly by the caller.
    """
    return REQUIRED_FIELDS


def envelope_field_present(envelope: Mapping[str, Any], field: str) -> bool:
    """
    Return whether envelope field present holds for the macro tools command output
    projection flow.

    The result is derived from `envelope` and `field`; failing evidence is returned or
    raised exactly where the body says so.
    """
    if field not in envelope:
        return False
    value = envelope[field]
    if value is None:
        return False
    if isinstance(value, (str, list, dict, tuple)) and not value:
        return False
    return True
