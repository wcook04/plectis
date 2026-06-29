"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.secret_exclusion_scan` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: BLOCKED_SECRET_EXCLUSION, TEXT_SUFFIXES, TEXT_FILENAMES, RECEIPT_BODY_FIELD_KEYS, EXPECTED_NEGATIVE_MARKER_KEYS, normalize_secret_exclusion_scan, classify_public_safe_macro_import, scan_text, scan_paths, scan_json_payload
- Reads: call arguments, module constants, imported helpers.
- Writes: return values and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: private_state_scan, relative package imports
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import private_state_scan as _legacy
from .private_state_scan import (
    BLOCKED_CASE_REVIEW,
    BLOCKED_PRIVATE,
    BLOCKED_PUBLIC_WRITE,
    PASS,
    TEXT_FILENAMES as _TEXT_FILENAMES,
    is_text_scan_candidate,
    load_forbidden_classes,
    public_relative_path,
)

BLOCKED_SECRET_EXCLUSION = BLOCKED_PRIVATE
TEXT_SUFFIXES = frozenset(_legacy.TEXT_SUFFIXES)
TEXT_FILENAMES = frozenset(_TEXT_FILENAMES)
RECEIPT_BODY_FIELD_KEYS = frozenset(
    {
        "body",
        "matched_excerpt",
        "source_body",
        "source_text",
        "payload_body",
        "provider_payload",
        "session_payload",
        "operator_thread_body",
        "credential_payload",
    }
)
EXPECTED_NEGATIVE_MARKER_KEYS = frozenset(
    {
        "expected_negative_case",
        "expected_negative_case_id",
        "negative_case_id",
        "synthetic_negative_fixture",
    }
)


def _without_legacy_body_fields(row: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Strip raw-body keys before a row enters a receipt.

    - Teleology: enforce the body-out-of-receipt contract by dropping the legacy
      body-bearing keys from any hit/finding/scan row before it is surfaced.
    - Guarantee: returns a new dict copy of `row` with `body_redacted`,
      `matched_excerpt`, and `body` removed; all other keys/values pass through.
    - Fails: never raises; a row lacking those keys returns an equivalent copy.
    - Reads: in-memory `row` dict only; no manifest/digest/source-ref path.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    - Escalates-to: `private_state_scan.py` for the upstream hit shape these keys come from.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return {
        key: value
        for key, value in row.items()
        if key not in {"body_redacted", "matched_excerpt", "body"}
    }


def _refresh_scan_counts(scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Recompute the scan verdict and counts from current hits.

    - Teleology: single chokepoint that derives the secret-exclusion verdict from
      the live hit list so status can never drift from the hits it reports.
    - Guarantee: sets `scan["status"]` to `BLOCKED_PUBLIC_WRITE` if any non-expected
      hit has `forbidden_class == "target_only_not_source"`, else `BLOCKED_SECRET_EXCLUSION`
      (alias of `BLOCKED_PRIVATE`) if any non-expected hit remains, else `PASS`; also
      sets `hits`, `hit_count`, and `blocking_hit_count`; expected-negative hits never block.
    - Fails: never raises; an empty/all-expected hit list yields `status == PASS`.
    - Reads: in-memory `scan` dict only; no manifest/digest/source-ref path.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    - Escalates-to: `private_state_scan.py` status constants and the same verdict logic in its scanners.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    hits = [dict(hit) for hit in scan.get("hits", []) if isinstance(hit, dict)]
    blocking_hits = [hit for hit in hits if not hit.get("expected_negative_case")]
    if any(hit.get("forbidden_class") == "target_only_not_source" for hit in blocking_hits):
        status = BLOCKED_PUBLIC_WRITE
    elif blocking_hits:
        status = BLOCKED_SECRET_EXCLUSION
    else:
        status = PASS
    scan["status"] = status
    scan["hits"] = hits
    scan["hit_count"] = len(hits)
    scan["blocking_hit_count"] = len(blocking_hits)
    return scan


def normalize_secret_exclusion_scan(raw_scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Return the receipt-facing secret-exclusion shape.

    Legacy scanner internals still know how to find sentinel terms, but the
    public receipt contract is source-open by default: the scanner proves that
    secrets/account-bound payload bodies are excluded, not that ordinary macro
    substrate was redacted.

    - Teleology: convert a legacy private-state scan into the source-open
      secret-exclusion receipt shape consumed by public-safe import flows.
    - Guarantee: returns a new scan dict with legacy body keys dropped, fixed
      policy fields stamped (`scan_purpose`, `body_in_receipt=False`,
      `real_substrate_default=True`, `omitted_output_fields`, `exclusion_policy`,
      `synthetic_receipt_policy`), every hit body-stripped with `body_in_receipt=False`,
      and `status`/counts re-derived via `_refresh_scan_counts`.
    - Fails: never raises; a `raw_scan` with no hits yields `status == PASS` and zero counts.
    - Reads: in-memory `raw_scan` dict only; no manifest/digest/source-ref path.
    - When-needed: inspect when a public receipt's status, omitted fields, or body-exclusion claim must be explained.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond secret exclusion, release, or whole-system correctness.
    - Escalates-to: `private_state_scan.py` scanners that produce `raw_scan`, and `_refresh_scan_counts` for the verdict.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """

    legacy_scan_keys = {
        "body_redacted",
        "forbidden_output_fields",
        "redacted_output_field_labels_omitted",
    }
    scan = {key: value for key, value in raw_scan.items() if key not in legacy_scan_keys}
    scan["scan_purpose"] = "credential_account_bound_and_operator_payload_exclusion"
    scan["omitted_output_fields"] = ["source_excerpt", "body"]
    scan["body_in_receipt"] = False
    scan["real_substrate_default"] = True
    scan["synthetic_receipt_policy"] = (
        "Synthetic receipts are admissible only as regression or negative-case "
        "harness artifacts, or as named blocked-import debt. They are not "
        "substitutes for non-secret macro substrate, real runtime receipts, "
        "real copied bodies, or source-faithful refactors."
    )
    scan["exclusion_policy"] = (
        "Open-source macro substrate by default; exclude only secrets, "
        "credentials, operator conversation bodies, provider payloads, "
        "account/session state, and credential-equivalent live-access material."
    )
    scan["hits"] = [
        _without_legacy_body_fields(dict(hit)) | {"body_in_receipt": False}
        for hit in raw_scan.get("hits", [])
        if isinstance(hit, dict)
    ]
    return _refresh_scan_counts(scan)


def _payload_has_expected_negative_marker(payload: object) -> bool:
    """
    [ACTION]
    Detect whether a payload self-declares as a negative-case fixture.

    - Teleology: let known regression/negative-case harness payloads carry
      sentinel body fields without their hits counting as blocking violations.
    - Guarantee: returns True iff any dict key anywhere in the nested
      `payload` (recursing dicts and lists) is in `EXPECTED_NEGATIVE_MARKER_KEYS`,
      else False.
    - Fails: never raises; scalars and unmarked structures return False.
    - Reads: in-memory `payload` object only; no manifest/digest/source-ref path.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    - Escalates-to: `EXPECTED_NEGATIVE_MARKER_KEYS` for the marker vocabulary.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in EXPECTED_NEGATIVE_MARKER_KEYS:
                return True
            if _payload_has_expected_negative_marker(value):
                return True
    elif isinstance(payload, list):
        return any(_payload_has_expected_negative_marker(item) for item in payload)
    return False


def _receipt_payload_field_hits(
    payload: object,
    *,
    path: str,
    expected_negative: bool,
    prefix: str = "",
) -> list[dict[str, Any]]:
    """
    [ACTION]
    Collect receipt-body-field violations from a nested payload.

    - Teleology: find every place a receipt payload carries a raw-body field
      (`body`, `matched_excerpt`, `source_body`, ...) that must live in source, not receipts.
    - Guarantee: returns a list of hit dicts, one per nested key in
      `RECEIPT_BODY_FIELD_KEYS`, each with `forbidden_class="receipt_payload_body_field"`,
      `term_id`, dotted/indexed `field_path`, `body_in_receipt=False`, a `remediation`
      string, and `expected_negative_case=True` only when `expected_negative` is set;
      returns `[]` when no such field is present.
    - Fails: never raises; scalars and clean structures yield `[]`.
    - Reads: in-memory `payload` object only; no manifest/digest/source-ref path.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    - Escalates-to: `RECEIPT_BODY_FIELD_KEYS` for the forbidden field vocabulary.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    hits: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            field_path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in RECEIPT_BODY_FIELD_KEYS:
                hit = {
                    "path": path,
                    "forbidden_class": "receipt_payload_body_field",
                    "term_id": f"receipt_payload_field:{key_text}",
                    "field_path": field_path,
                    "body_in_receipt": False,
                    "remediation": (
                        "Move raw payload material to public source modules or fixtures "
                        "and keep receipts to public refs, hashes, counts, and anchors."
                    ),
                }
                if expected_negative:
                    hit["expected_negative_case"] = True
                hits.append(hit)
                continue
            hits.extend(
                _receipt_payload_field_hits(
                    value,
                    path=path,
                    expected_negative=expected_negative,
                    prefix=field_path,
                )
            )
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            field_path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            hits.extend(
                _receipt_payload_field_hits(
                    item,
                    path=path,
                    expected_negative=expected_negative,
                    prefix=field_path,
                )
            )
    return hits


def _merge_receipt_payload_boundary(
    scan: dict[str, Any],
    payload: object,
    *,
    path: str,
) -> dict[str, Any]:
    """
    [ACTION]
    Fold receipt-payload body-field hits into a scan and re-derive verdict.

    - Teleology: extend a normalized scan with the receipt-payload-field guard so
      a receipt that smuggles raw body fields is recorded as a secret-exclusion violation.
    - Guarantee: appends every `_receipt_payload_field_hits` hit to `scan["hits"]`,
      sets `scan["receipt_payload_field_guard"]` with `status` (`PASS` when zero
      blocking fields else `BLOCKED_SECRET_EXCLUSION`), `forbidden_field_count`,
      `blocking_field_count`, and `body_in_receipt=False`, then returns the scan with
      counts/status refreshed via `_refresh_scan_counts`.
    - Fails: never raises; a payload with no body fields leaves the prior verdict and adds a `PASS` guard.
    - Reads: in-memory `scan` and `payload` only; `path` is a display label, not a path read from disk.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    - Escalates-to: `_receipt_payload_field_hits` for the hits and `_refresh_scan_counts` for the verdict.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    expected_negative = _payload_has_expected_negative_marker(payload)
    hits = _receipt_payload_field_hits(
        payload,
        path=path,
        expected_negative=expected_negative,
    )
    blocking_count = len([hit for hit in hits if not hit.get("expected_negative_case")])
    scan.setdefault("hits", [])
    scan["hits"].extend(hits)
    scan["receipt_payload_field_guard"] = {
        "status": PASS if blocking_count == 0 else BLOCKED_SECRET_EXCLUSION,
        "forbidden_field_count": len(hits),
        "blocking_field_count": blocking_count,
        "body_in_receipt": False,
    }
    return _refresh_scan_counts(scan)


def classify_public_safe_macro_import(
    row: dict[str, Any],
    *,
    forbidden_classes: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    Classify one import row for public-safe macro import, body-stripped.

    - Teleology: public custody surface that decides whether a single import row is
      public-safe, returning a receipt with no raw bodies.
    - Guarantee: returns the legacy classification dict with body keys removed,
      `body_in_receipt=False`, `real_substrate_default=True`,
      `synthetic_receipt_policy="not_a_substitute_for_available_real_substrate"`, and a
      `findings` list whose every entry is body-stripped with `body_in_receipt=False`;
      preserves the legacy verdict/status fields otherwise.
    - Fails: never raises; propagates whatever status the legacy classifier set; a clean row carries no blocking findings.
    - Reads: the `forbidden_classes` mapping (loaded via `load_forbidden_classes`) and the in-memory `row`.
    - When-needed: inspect when deciding/explaining whether a specific macro import row may cross the public boundary.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond secret exclusion, release, or whole-system correctness.
    - Escalates-to: `private_state_scan.classify_public_safe_macro_import` for the underlying classification.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    raw = _legacy.classify_public_safe_macro_import(
        row,
        forbidden_classes=forbidden_classes,
    )
    result = _without_legacy_body_fields(dict(raw))
    result["body_in_receipt"] = False
    result["real_substrate_default"] = True
    result["synthetic_receipt_policy"] = "not_a_substitute_for_available_real_substrate"
    result["findings"] = [
        _without_legacy_body_fields(dict(finding)) | {"body_in_receipt": False}
        for finding in raw.get("findings", [])
        if isinstance(finding, dict)
    ]
    return result


def scan_text(
    text: str,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    """
    [ACTION]
    Scan an in-memory text blob for excluded secret/account-bound material.

    - Teleology: public custody surface that proves a text body excludes secrets
      before it is treated as public-safe, without echoing the body into the receipt.
    - Guarantee: returns the normalized secret-exclusion scan of `text` (legacy body
      keys dropped, policy fields stamped, hits body-stripped, status/counts derived);
      `status` is `BLOCKED_PUBLIC_WRITE` for a `target`-context source-leak, else
      `BLOCKED_SECRET_EXCLUSION` for remaining hits, else `PASS`.
    - Fails: never raises; clean text returns `status == PASS`.
    - Reads: the `forbidden_classes` mapping and the in-memory `text`; `path` is a display label.
    - When-needed: inspect when a literal string must be cleared for public exposure.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond secret exclusion, release, or whole-system correctness.
    - Escalates-to: `normalize_secret_exclusion_scan` and `private_state_scan.scan_text`.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return normalize_secret_exclusion_scan(
        _legacy.scan_text(
            text,
            path=path,
            forbidden_classes=forbidden_classes,
            source_context=source_context,
        )
    )


def scan_paths(
    paths: list[str | Path],
    *,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
    display_root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    Scan a set of filesystem paths for excluded secret/account-bound material.

    - Teleology: public custody surface that clears a batch of files for public
      exposure, reporting only public refs/counts and never raw file bodies.
    - Guarantee: returns the normalized secret-exclusion scan over `paths` (legacy
      body keys dropped, hits body-stripped, paths shown relative to `display_root`
      via the legacy public-path logic, status/counts derived); `status` is
      `BLOCKED_PUBLIC_WRITE` for a target-only source leak, else `BLOCKED_SECRET_EXCLUSION`,
      else `PASS`.
    - Fails: never raises here; unreadable files surface as legacy unreadable-text results, not exceptions; clean paths return `PASS`.
    - Reads: the `forbidden_classes` mapping and the file contents at each path in `paths`.
    - When-needed: inspect when a file batch must be cleared before publication/import.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond secret exclusion, release, or whole-system correctness.
    - Escalates-to: `normalize_secret_exclusion_scan` and `private_state_scan.scan_paths`.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return normalize_secret_exclusion_scan(
        _legacy.scan_paths(
            paths,
            forbidden_classes=forbidden_classes,
            source_context=source_context,
            display_root=display_root,
        )
    )


def scan_json_payload(
    payload: object,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    """
    [ACTION]
    Scan a JSON receipt payload for excluded material AND raw-body fields.

    - Teleology: public custody surface for structured receipts: proves a JSON
      payload excludes secrets and carries no raw-body fields before it is published.
    - Guarantee: returns the normalized secret-exclusion scan of `payload` with the
      receipt-payload-field guard merged in (via `_merge_receipt_payload_boundary`),
      so `status` is `BLOCKED_SECRET_EXCLUSION` if any blocking receipt-body field or
      sentinel hit is present, `BLOCKED_PUBLIC_WRITE` for a target-only source leak,
      else `PASS`; adds `receipt_payload_field_guard` with field counts; `body_in_receipt=False`.
    - Fails: never raises; a clean payload returns `status == PASS` with a `PASS` field guard.
    - Reads: the `forbidden_classes` mapping and the in-memory `payload`; `path` is a display label.
    - When-needed: inspect when a structured JSON receipt must be cleared for public exposure.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond secret exclusion, release, or whole-system correctness.
    - Escalates-to: `normalize_secret_exclusion_scan`, `_merge_receipt_payload_boundary`, and `private_state_scan.scan_json_payload`.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    scan = normalize_secret_exclusion_scan(
        _legacy.scan_json_payload(
            payload,
            path=path,
            forbidden_classes=forbidden_classes,
            source_context=source_context,
        )
    )
    return _merge_receipt_payload_boundary(scan, payload, path=path)


__all__ = [
    "BLOCKED_CASE_REVIEW",
    "BLOCKED_PRIVATE",
    "BLOCKED_PUBLIC_WRITE",
    "BLOCKED_SECRET_EXCLUSION",
    "PASS",
    "TEXT_FILENAMES",
    "TEXT_SUFFIXES",
    "classify_public_safe_macro_import",
    "is_text_scan_candidate",
    "load_forbidden_classes",
    "normalize_secret_exclusion_scan",
    "public_relative_path",
    "scan_json_payload",
    "scan_paths",
    "scan_text",
]
