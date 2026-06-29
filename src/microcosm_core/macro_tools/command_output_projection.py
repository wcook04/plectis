"""
Command-output projection helper.

[PURPOSE]
- Teleology: Package known kernel command-output fields into a canonical Rosetta-Stone projection envelope governed by codex/standards/std_command_output_projection.json.
- Mechanism: Pure helper. Does not summarize. Does not synthesize bands. Validates required fields and emits structured envelopes for opt-in command projection and structured refusals for unsupported/unpopulated bands.
- When-needed: Open when a kernel command is opting into projected output via --output-band, when --row KIND:ID --band BAND is delegating to an option-surface, or when the command-output-projection audit is being computed.
- Escalates-to: codex/standards/std_command_output_projection.json (envelope contract); system/lib/standard_option_surface.py (option-surface adapter); system/lib/kind_atlas.py (kind atlas).
- Navigation-group: kernel_lib

Inherits from std_agent_entry_surface.json::compression_via_projection_contract (pri_121_candidate). Command outputs are runtime projections of the same Rosetta-Stone shape that governs entry-surface markdown.

[INTERFACE]
- Exports: STANDARD_REF, ROOT_CONTRACT_REF, ENVELOPE_KIND, ENVELOPE_SCHEMA_VERSION, REQUIRED_FIELDS, make_row_id, make_omission_receipt, make_validation_contract, make_currentness, command_projection, row_band_unavailable, envelope_required_fields, envelope_field_present
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, declared filesystem outputs and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
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
    [ACTION]
    - Teleology: Implements `_utc_now` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_row_id(command: str, selector: str, band: str) -> str:
    """
    [ACTION]
    Build a row_id following std_command_output_projection row_id_shape.

    Shape: kernel:<command>:<selector>::<band>
    - Teleology: Implements `make_row_id` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    Build a peer-level omission receipt.
    - Teleology: Implements `make_omission_receipt` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    Build a validation_contract block.
    - Teleology: Implements `make_validation_contract` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    Build a currentness block matching kind-atlas conventions.
    - Teleology: Implements `make_currentness` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    Package command-output fields into the canonical Rosetta projection envelope.

    This helper does not summarize and does not synthesize bands. It validates that
    the caller supplied the required envelope fields and emits a structured dict
    governed by codex/standards/std_command_output_projection.json.
    - Teleology: Implements `command_projection` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    Structured refusal for --row when the requested band is unsupported or unpopulated.

    Emitted instead of synthesizing a band the underlying adapter does not populate.
    Honors the Phase 09.45 routing-first reversal at the v0 safety level: if the
    option-surface adapter does not actually emit this band for this kind, refuse.
    - Teleology: Implements `row_band_unavailable` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    Return the required envelope field tuple. Used by the audit runtime.
    - Teleology: Implements `envelope_required_fields` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return REQUIRED_FIELDS


def envelope_field_present(envelope: Mapping[str, Any], field: str) -> bool:
    """
    [ACTION]
    Best-effort check that a field is present and non-empty on a projected envelope.
    - Teleology: Implements `envelope_field_present` for `microcosm_core.macro_tools.command_output_projection` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if field not in envelope:
        return False
    value = envelope[field]
    if value is None:
        return False
    if isinstance(value, (str, list, dict, tuple)) and not value:
        return False
    return True
