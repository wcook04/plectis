"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.public_payload_boundary` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SOURCE_OPEN_BODY_POLICY, EXCLUDED_PUBLIC_PAYLOAD_CLASSES, OMITTED_PAYLOAD_SCHEMA_TERM_PARTS, omitted_payload_schema_terms, omitted_payload_schema_term_hits, public_payload_boundary
- Reads: call arguments, module constants, imported helpers.
- Writes: return values and any explicit side effects performed by exported entry points.
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

import json
from typing import Any


SOURCE_OPEN_BODY_POLICY = (
    "source_open_except_secret_credential_provider_account_session_and_live_access_payloads"
)

EXCLUDED_PUBLIC_PAYLOAD_CLASSES = [
    "secrets",
    "api_keys",
    "credentials",
    "cookies",
    "account_session_state",
    "provider_payload_bodies",
    "browser_or_hud_live_access_material",
    "recipient_send_state",
    "credential_equivalent_payloads",
]

OMITTED_PAYLOAD_SCHEMA_TERM_PARTS: tuple[tuple[str, ...], ...] = (
    ("body_", "red", "acted"),
    ("private_", "state", "_scan"),
    ("private_", "state", "_scan_posture"),
    ("public_", "replacement_ref"),
    ("public_", "replacement_refs"),
    ("red", "acted_hash"),
    ("source_cell_", "red", "acted_flag"),
)


def omitted_payload_schema_terms() -> tuple[str, ...]:
    """
    [ACTION]
    - Teleology: Implements `omitted_payload_schema_terms` for `microcosm_core.public_payload_boundary` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return tuple("".join(parts) for parts in OMITTED_PAYLOAD_SCHEMA_TERM_PARTS)


def omitted_payload_schema_term_hits(payload: Any) -> dict[str, int]:
    """
    [ACTION]
    - Teleology: Implements `omitted_payload_schema_term_hits` for `microcosm_core.public_payload_boundary` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return {
        term: hit_count
        for term in omitted_payload_schema_terms()
        if (hit_count := encoded.count(term))
    }


def public_payload_boundary(
    *,
    boundary_id: str,
    command: str,
    surface_ref: str | None = None,
    input_payload_schema_normalized: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `public_payload_boundary` for `microcosm_core.public_payload_boundary` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "microcosm_public_payload_boundary_v1",
        "boundary_id": boundary_id,
        "command": command,
        "surface_ref": surface_ref,
        "source_open_default": True,
        "body_policy": SOURCE_OPEN_BODY_POLICY,
        "unsafe_payload_bodies_in_receipt": False,
        "non_secret_macro_substrate_expected": True,
        "metadata_only_standin_authorized": False,
        "synthetic_fixture_policy": "negative_case_or_regression_harness_only",
        "public_refs_are_drilldowns_not_replacements": True,
        "excluded_public_payload_classes": list(EXCLUDED_PUBLIC_PAYLOAD_CLASSES),
        "secrets_exported": False,
        "credential_equivalent_payloads_exported": False,
        "provider_payload_bodies_exported": False,
        "account_session_state_exported": False,
        "browser_or_hud_live_access_exported": False,
        "recipient_send_state_exported": False,
        "input_payload_schema_normalized": input_payload_schema_normalized,
        "omitted_payload_schema_terms_exported": False,
    }
